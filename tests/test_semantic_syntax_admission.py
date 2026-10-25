"""Parsed relation-block forms stop at the pre-admission gate of semantic analysis."""

from __future__ import annotations

from pathlib import Path

import pytest

from pietto._syntax_admission import unadmitted_syntax_diagnostics
from pietto.errors import Severity
from pietto.parser_api import _parse_legacy_source, parse_file, parse_source
from pietto.semantic import analyze
from pietto.semantic.model import CheckMode


REPO_ROOT = Path(__file__).resolve().parents[1]
GATE_CODES = {f"PIE-S{number}" for number in range(2345, 2353)}
FAMILIES = {
    "let_relation": (
        "PIE-S2345",
        "Relation let declarations are available only in "
        "EXPLICIT_MODULES projects (schema version 2).",
        "query q:\n    let l:\n        from rows\n        select:\n"
        "            id\n    from l\n    select:\n        id\n",
        (2, 5, 5, 15),
    ),
    "query_parameter": (
        "PIE-S2346",
        "Query header parameters are available only in EXPLICIT_MODULES "
        "projects (schema version 2), on a query that reads a relation "
        "with FROM and has no relation let reading a table function.",
        "query q(a: Int):\n    from rows\n    select:\n        id\n",
        (1, 9, 1, 15),
    ),
    "values_body": (
        "PIE-S2347",
        "Typed VALUES bodies are available only in EXPLICIT_MODULES "
        "projects (schema version 2).",
        "query q:\n    values(id: Int)\n",
        (2, 5, 2, 20),
    ),
    "scalar_read": (
        "PIE-S2348",
        "Scalar relation reads are available only inside a FROM-based "
        "relation body in EXPLICIT_MODULES projects (schema version 2).",
        "query q:\n    from rows\n    where id == scalar t.c\n    select:\n        id\n",
        (3, 17, 3, 27),
    ),
    "exists_reference": (
        "PIE-S2349",
        "EXISTS relation reads are available only inside a FROM-based "
        "relation body in EXPLICIT_MODULES projects (schema version 2).",
        "query q:\n    from rows\n    where exists t\n    select:\n        id\n",
        (3, 11, 3, 19),
    ),
    "in_reference": (
        "PIE-S2350",
        "IN relation reads are available only inside a FROM-based "
        "relation body in EXPLICIT_MODULES projects (schema version 2).",
        "query q:\n    from rows\n    where id not in t\n    select:\n        id\n",
        (3, 11, 3, 22),
    ),
    "table_function_from": (
        "PIE-S2352",
        "Table-function FROM inputs are available only in "
        "EXPLICIT_MODULES projects (schema version 2).",
        "query q:\n    from generate_series(1, 31, 1) as n\n    select:\n        n\n",
        (2, 5, 2, 40),
    ),
    "scalar_read_in_window_frame_bound": (
        "PIE-S2348",
        "Scalar relation reads are available only inside a FROM-based "
        "relation body in EXPLICIT_MODULES projects (schema version 2).",
        "query q:\n    from rows\n    select:\n"
        "        total = sum(id) window(order by id rows between "
        "scalar t.c preceding and current row)\n",
        (4, 57, 4, 67),
    ),
    "on_join_without_from": (
        "PIE-S2378",
        "A JOIN with `on`, or a CROSS JOIN, must name its source binding with `from`.",
        "query q:\n    from rows\n    inner join others as o: on o.id == rows.id\n"
        "    select:\n        id\n",
        (3, 5, 3, 47),
    ),
    "cross_join_without_from": (
        "PIE-S2378",
        "A JOIN with `on`, or a CROSS JOIN, must name its source binding with `from`.",
        "query q:\n    from rows\n    cross join others as o\n    select:\n        id\n",
        (3, 5, 3, 27),
    ),
}
# PIE-S2378 guards the legacy JOIN spelling, which only the private legacy
# reader still builds; the modern parser refuses that spelling with PIE-P1000.
LEGACY_FAMILIES = frozenset({"on_join_without_from", "cross_join_without_from"})
NESTED = (
    "query q(a: Int):\n"
    "    let l:\n"
    "        capture rows\n"
    "        from generate_series(1, 2, 1) as n\n"
    "        select:\n"
    "            n\n"
    "    let inner:\n"
    "        values(id: Int)\n"
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


def _analyzed(source: str, *, legacy: bool = False, **options: CheckMode):
    parsed = (_parse_legacy_source if legacy else parse_source)(
        source, path="gate.pietto"
    )
    assert parsed.diagnostics == () and parsed.ast is not None
    return analyze(parsed.ast, **options)


def _located(diagnostics) -> list[tuple[str, int, int]]:
    return [(d.code, d.location.line, d.location.column) for d in diagnostics]


@pytest.mark.parametrize(
    ("family", "code", "message", "source", "span"),
    [(name, *values) for name, values in FAMILIES.items()],
    ids=FAMILIES,
)
def test_each_family_reports_its_own_code_at_its_authored_span(
    family: str, code: str, message: str, source: str, span: tuple[int, int, int, int]
) -> None:
    (diagnostic,) = _analyzed(source, legacy=family in LEGACY_FAMILIES).diagnostics

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
    result = (
        _analyzed(NESTED) if mode is None else _analyzed(NESTED, mode_override=mode)
    )

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
    plain = parse_source(f"derive total() -> Int:\n    return {deep}\n")
    assert plain.ast is not None
    assert unadmitted_syntax_diagnostics(plain.ast) == ()

    gated = _analyzed(
        f"query q:\n    from rows\n    where {deep} + scalar t.c > 0\n"
        "    select:\n        id\n"
    )
    assert [d.code for d in gated.diagnostics] == ["PIE-S2348"]


def test_explicit_modules_admit_relation_reads_only_inside_a_relation_body() -> None:
    """A type rule, a shape check or a type argument keeps the gate diagnostic;
    single-file and LEGACY_FLAT callers keep every occurrence gated."""
    source = (
        "type Age = Int:\n"
        "    ensure self > scalar t.c and exists t\n"
        "shape S:\n"
        "    id: Int\n"
        "    extra: Decimal(exists t, scalar t.c)\n"
        "    c = check(id > scalar t.c and exists t)\n"
        "query q:\n"
        "    let l:\n"
        "        from rows\n"
        "        where exists t and id == scalar t.c\n"
        "        select:\n"
        "            id\n"
        "    from l\n"
        "    where exists t and id == scalar t.c\n"
        "    select:\n"
        "        id\n"
    )
    parsed = parse_source(source, path="gate.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None
    exists = FAMILIES["exists_reference"][1]
    scalar = FAMILIES["scalar_read"][1]
    gated = [
        ("PIE-S2348", scalar, 2, 19),
        ("PIE-S2349", exists, 2, 34),
        ("PIE-S2349", exists, 5, 20),
        ("PIE-S2348", scalar, 5, 30),
        ("PIE-S2348", scalar, 6, 20),
        ("PIE-S2349", exists, 6, 35),
    ]

    def described(diagnostics):
        return [
            (d.code, d.message, d.location.line, d.location.column) for d in diagnostics
        ]

    assert (
        described(unadmitted_syntax_diagnostics(parsed.ast, explicit_modules=True))
        == gated
    )
    assert described(unadmitted_syntax_diagnostics(parsed.ast)) == sorted(
        [
            *gated,
            ("PIE-S2345", FAMILIES["let_relation"][1], 8, 5),
            ("PIE-S2349", exists, 10, 15),
            ("PIE-S2348", scalar, 10, 34),
            ("PIE-S2349", exists, 14, 11),
            ("PIE-S2348", scalar, 14, 30),
        ],
        key=lambda item: (item[2], item[3]),
    )


def test_an_admitted_query_header_still_gates_a_read_in_a_parameter_type() -> None:
    """EXPLICIT_MODULES admits an entry-query header, not a form in its types."""
    parsed = parse_source(
        "query q(a: Int(exists t), b: Text | None):\n"
        "    from rows\n    select:\n        id\n",
        path="gate.pietto",
    )
    assert parsed.diagnostics == () and parsed.ast is not None
    exists = FAMILIES["exists_reference"][1]
    header = FAMILIES["query_parameter"][1]

    def described(diagnostics):
        return [
            (d.code, d.message, d.location.line, d.location.column) for d in diagnostics
        ]

    assert described(
        unadmitted_syntax_diagnostics(parsed.ast, explicit_modules=True)
    ) == [("PIE-S2349", exists, 1, 16)]
    assert described(unadmitted_syntax_diagnostics(parsed.ast)) == [
        ("PIE-S2346", header, 1, 9),
        ("PIE-S2349", exists, 1, 16),
        ("PIE-S2346", header, 1, 27),
    ]


def test_explicit_modules_admit_capture_lines() -> None:
    """Capture lines pass the gate only in EXPLICIT_MODULES; their structure is
    checked by the project capture rules, not by the gate."""
    parsed = parse_source(
        "query q:\n    let l:\n        capture rows\n        from tags\n"
        "        where tags.id == rows.id\n        select:\n            id\n"
        "    from rows\n    select:\n        id\n",
        path="gate.pietto",
    )
    assert parsed.diagnostics == () and parsed.ast is not None
    assert unadmitted_syntax_diagnostics(parsed.ast, explicit_modules=True) == ()
    assert _located(unadmitted_syntax_diagnostics(parsed.ast)) == [
        ("PIE-S2345", 2, 5),
        ("PIE-S2351", 3, 9),
    ]


def test_on_and_cross_joins_without_from_stay_gated_and_def_only_where_inlined() -> (
    None
):
    """Only a legacy relationship JOIN infers an omitted `from` or VIA roles
    (read by the private legacy reader, in its spelling). Single files and
    EXPLICIT_MODULES projects inline def calls; LEGACY_FLAT and PACKAGE_ROOT
    projects keep every def gated."""
    parsed = _parse_legacy_source(
        "def f(x: Int not null) -> Int not null:\n    return x\n"
        "query q:\n    from rows\n    inner join others as o: via link\n"
        "    left join others as p\n"
        "    left join others as q: on q.id == rows.id\n"
        "    cross join others as x\n    select:\n        id\n",
        path="gate.pietto",
    )
    assert parsed.diagnostics == () and parsed.ast is not None
    joins = [("PIE-S2378", 7, 5), ("PIE-S2378", 8, 5)]
    gated = unadmitted_syntax_diagnostics(parsed.ast)
    assert _located(gated) == [("PIE-S2379", 1, 1), *joins]
    assert gated[0].message == (
        "Inline `def` functions are available only in single files and "
        "EXPLICIT_MODULES projects (schema version 2)."
    )
    location = gated[0].location
    assert (location.end_line, location.end_column) == (2, 13)
    for options in ({"explicit_modules": True}, {"single_file": True}):
        assert _located(unadmitted_syntax_diagnostics(parsed.ast, **options)) == joins
