"""Parsed relation-block forms stop at the pre-admission gate of semantic analysis."""

from __future__ import annotations

from pathlib import Path

import pytest

from pietto._syntax_admission import unadmitted_syntax_diagnostics
from pietto.errors import Severity
from pietto.parser_api import parse_file, parse_source
from pietto.semantic import analyze
from pietto.semantic.model import CheckMode


REPO_ROOT = Path(__file__).resolve().parents[1]
GATE_CODES = {f"PIE-S{number}" for number in range(2345, 2353)}
FAMILIES = {
    "let_relation": (
        "PIE-S2345",
        "Let relation declaration semantics are not implemented.",
        "query q:\n    let l:\n        from rows\n        select:\n"
        "            id\n    from l\n    select:\n        id\n",
        (2, 5, 5, 15),
    ),
    "query_parameter": (
        "PIE-S2346",
        "Query header parameter semantics are not implemented.",
        "query q(a: Int not null):\n    from rows\n    select:\n        id\n",
        (1, 9, 1, 24),
    ),
    "values_body": (
        "PIE-S2347",
        "VALUES body semantics are not implemented.",
        "query q:\n    values(id: Int not null)\n",
        (2, 5, 2, 29),
    ),
    "scalar_read": (
        "PIE-S2348",
        "Scalar relation read semantics are not implemented.",
        "query q:\n    from rows\n    where id == scalar t.c\n    select:\n        id\n",
        (3, 17, 3, 27),
    ),
    "exists_reference": (
        "PIE-S2349",
        "EXISTS relation reference semantics are not implemented.",
        "query q:\n    from rows\n    where exists t\n    select:\n        id\n",
        (3, 11, 3, 19),
    ),
    "in_reference": (
        "PIE-S2350",
        "IN relation reference semantics are not implemented.",
        "query q:\n    from rows\n    where id not in t\n    select:\n        id\n",
        (3, 11, 3, 22),
    ),
    "table_function_from": (
        "PIE-S2352",
        "Table-function FROM input semantics are not implemented.",
        "query q:\n    from generate_series(1, 31, 1) as n\n    select:\n        n\n",
        (2, 5, 2, 40),
    ),
    "scalar_read_in_window_frame_bound": (
        "PIE-S2348",
        "Scalar relation read semantics are not implemented.",
        "query q:\n    from rows\n    select:\n        total = sum(id) window:\n"
        "            order by:\n                id\n"
        "            rows between scalar t.c preceding and current row\n",
        (7, 26, 7, 36),
    ),
}
NESTED = (
    "query q(a: Int not null):\n"
    "    let l:\n"
    "        capture rows\n"
    "        from generate_series(1, 2, 1) as n\n"
    "        select:\n"
    "            n\n"
    "    let inner:\n"
    "        values(id: Int not null)\n"
    "    from rows\n"
    "    where scalar l.n in l and exists inner\n"
    "    select:\n"
    "        id\n"
    "    qualify:\n"
    "        id not in l\n"
)
NESTED_EXPECTED = [
    ("PIE-S2346", 1, 9),
    ("PIE-S2345", 2, 5),
    ("PIE-S2351", 3, 9),
    ("PIE-S2352", 4, 9),
    ("PIE-S2345", 7, 5),
    ("PIE-S2347", 8, 9),
    ("PIE-S2348", 10, 11),
    ("PIE-S2350", 10, 11),
    ("PIE-S2349", 10, 31),
    ("PIE-S2350", 14, 9),
]


def _analyzed(source: str, **options: CheckMode):
    parsed = parse_source(source, path="gate.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None
    return analyze(parsed.ast, **options)


def _located(diagnostics) -> list[tuple[str, int, int]]:
    return [(d.code, d.location.line, d.location.column) for d in diagnostics]


@pytest.mark.parametrize(
    ("code", "message", "source", "span"),
    FAMILIES.values(),
    ids=FAMILIES,
)
def test_each_family_reports_its_own_code_at_its_authored_span(
    code: str, message: str, source: str, span: tuple[int, int, int, int]
) -> None:
    (diagnostic,) = _analyzed(source).diagnostics

    assert (diagnostic.code, diagnostic.message) == (code, message)
    assert diagnostic.severity is Severity.ERROR
    location = diagnostic.location
    assert location.path == "gate.pietto"
    assert (
        location.line,
        location.column,
        location.end_line,
        location.end_column,
    ) == span


@pytest.mark.parametrize("mode", [None, *CheckMode])
def test_every_nested_occurrence_is_an_error_in_source_order(
    mode: CheckMode | None,
) -> None:
    options = {} if mode is None else {"mode_override": mode}
    result = _analyzed(NESTED, **options)

    assert _located(result.diagnostics) == NESTED_EXPECTED
    capture = result.diagnostics[2].location
    assert (capture.line, capture.column, capture.end_line, capture.end_column) == (
        3,
        9,
        3,
        21,
    )
    assert {d.severity for d in result.diagnostics} == {Severity.ERROR}
    assert result.model.mode is (mode or CheckMode.CHECKED)
    loose = _analyzed("mode loose\n" + NESTED)
    assert [d.code for d in loose.diagnostics] == [c for c, _, _ in NESTED_EXPECTED]


def test_existing_sources_and_lookalike_forms_pass_the_gate() -> None:
    fixtures = sorted(
        path
        for directory in ("examples", "tests/fixtures")
        for path in (REPO_ROOT / directory).rglob("*.pietto")
    )
    assert fixtures
    for path in fixtures:
        parsed = parse_file(path)
        assert parsed.ast is not None, path
        assert unadmitted_syntax_diagnostics(parsed.ast) == (), path
    lookalikes = _analyzed(
        "query q:\n"
        "    from rows\n"
        "    where id in (vip) and exists(recent)\n"
        "    select:\n"
        "        values = scalar(total)\n"
    )
    assert GATE_CODES.isdisjoint(d.code for d in lookalikes.diagnostics)


def test_deep_expressions_are_walked_without_recursion() -> None:
    deep = " + ".join(["1"] * 1200)
    plain = parse_source(f"derive total() -> Int not null:\n    {deep}\n")
    assert plain.ast is not None
    assert unadmitted_syntax_diagnostics(plain.ast) == ()

    gated = _analyzed(
        f"query q:\n    from rows\n    where {deep} + scalar t.c > 0\n"
        "    select:\n        id\n"
    )
    assert [d.code for d in gated.diagnostics] == ["PIE-S2348"]
