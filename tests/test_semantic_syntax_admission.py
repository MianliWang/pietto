"""Parsed relation-block forms stop at the pre-admission gate of semantic analysis."""

from __future__ import annotations

from pathlib import Path

import pytest

from pietto._syntax_admission import (
    nested_relation_syntax_diagnostics,
    unadmitted_syntax_diagnostics,
)
from pietto.errors import Severity
from pietto.parser_api import _parse_legacy_source, parse_file, parse_source
from pietto.semantic import analyze
from pietto.semantic.model import CheckMode


REPO_ROOT = Path(__file__).resolve().parents[1]
GATE_CODES = {f"PIE-S{number}" for number in range(2345, 2353)}
LEGACY_JOIN = (
    "A JOIN with `as`, `from` or `via` is retired; name the input with "
    "`let alias = relation`, then write `inner join alias on predicate` or "
    "another JOIN kind."
)
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
    "collect_relation": (
        "PIE-S2801",
        "Collect relation reads are available only in EXPLICIT_MODULES "
        "projects (schema version 2). Put this file in a project whose "
        "pietto.toml sets `schema_version = 2` and check it with `pietto check "
        "--project`; `collect(relation)` is still an ordinary function call.",
        "query q:\n    from rows\n    select:\n        nested = collect children\n",
        (4, 18, 4, 34),
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
        LEGACY_JOIN,
        "query q:\n    from rows\n    inner join others as o: on o.id == rows.id\n"
        "    select:\n        id\n",
        (3, 5, 3, 47),
    ),
    "cross_join_without_from": (
        "PIE-S2378",
        LEGACY_JOIN,
        "query q:\n    from rows\n    cross join others as o\n    select:\n        id\n",
        (3, 5, 3, 27),
    ),
    "relationship_join_without_on": (
        "PIE-S2378",
        LEGACY_JOIN,
        "query q:\n    from rows\n    left join others as o\n    select:\n        id\n",
        (3, 5, 3, 26),
    ),
    "join_with_from_and_via": (
        "PIE-S2378",
        LEGACY_JOIN,
        "query q:\n    from rows\n    inner join others as o:\n        from rows\n"
        "        via link\n        on o.id == rows.id\n    select:\n        id\n",
        (3, 5, 6, 27),
    ),
    "relationship_metadata": (
        "PIE-S2378",
        "Source-bound relationship metadata is retired; declare a shape-typed "
        "`relationship Name(role: Shape, ...):` predicate and call it in a JOIN's "
        "`on`.",
        "relationship link: rows.id == others.id\n"
        "query q:\n    from rows\n    select:\n        id\n",
        (1, 1, 1, 40),
    ),
}
# PIE-S2378 refuses every retired relationship-JOIN form, which only the
# private legacy reader or a hand-built AST still carries; the modern parser
# refuses that spelling with PIE-P1000.
LEGACY_FAMILIES = frozenset(
    {
        "on_join_without_from",
        "cross_join_without_from",
        "relationship_join_without_on",
        "join_with_from_and_via",
        "relationship_metadata",
    }
)
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


_TO_EXPLICIT_MODULES = (
    "Put this file in a project whose pietto.toml sets `schema_version = 2` and "
    "check it with `pietto check --project`"
)


def test_collect_and_unnest_gate_in_source_order_and_explain_their_context() -> None:
    source = (
        "query q:\n"
        "    from rows\n"
        "    let expanded = unnest(rows.children)\n"
        "    cross join expanded\n"
        "    select:\n"
        "        nested = collect children\n"
    )
    parsed = parse_source(source, path="gate.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None

    legacy = unadmitted_syntax_diagnostics(parsed.ast)
    assert _located(legacy) == [("PIE-S2801", 3, 5), ("PIE-S2801", 6, 18)]
    unnest = (
        f"{_TO_EXPLICIT_MODULES}; a module that defines its own `unnest` keeps "
        "an ordinary function call."
    )
    collect = f"{_TO_EXPLICIT_MODULES}; `collect(relation)` is still an ordinary function call."
    # Text output prints only the message, so it ends with the suggestion.
    assert [(d.message, d.suggestion) for d in legacy] == [
        (
            "Unnest is available only in EXPLICIT_MODULES projects (schema version "
            f"2). {unnest}",
            unnest,
        ),
        (
            "Collect relation reads are available only in EXPLICIT_MODULES projects "
            f"(schema version 2). {collect}",
            collect,
        ),
    ]
    assert nested_relation_syntax_diagnostics(parsed.ast) == legacy
    assert unadmitted_syntax_diagnostics(parsed.ast, explicit_modules=True) == ()


@pytest.mark.parametrize(
    "lines",
    [
        # D71.02: only a let that a later JOIN of its body reads is Unnest.
        ("    let expanded = unnest(rows.children)\n",),
        ("    cross join expanded\n", "    let expanded = unnest(rows.children)\n"),
        # A module that defines `unnest` keeps the ordinary call.
        (
            "    let expanded = unnest(rows.children)\n",
            "    cross join expanded\n",
            "def unnest(value: Int) -> Int: return value\n",
        ),
        # A name the body declares twice is no Unnest let: no candidate wins.
        (
            "    let expanded = unnest(rows.children)\n",
            "    let expanded = unnest(rows.children)\n",
            "    cross join expanded\n",
        ),
        (
            "    let expanded = unnest(rows.children)\n",
            "    cross join expanded\n",
            "    let expanded = window(order by id)\n",
        ),
    ],
    ids=["no-join", "join-before-let", "local-def", "let-twice", "window-of-the-name"],
)
def test_an_ordinary_unnest_call_is_not_gated(lines: tuple[str, ...]) -> None:
    body = "".join(line for line in lines if line.startswith("    "))
    definitions = "".join(line for line in lines if not line.startswith("    "))
    parsed = parse_source(
        f"{definitions}query q:\n    from rows\n{body}    select:\n        id\n",
        path="gate.pietto",
    )
    assert parsed.diagnostics == () and parsed.ast is not None

    assert nested_relation_syntax_diagnostics(parsed.ast) == ()
    assert unadmitted_syntax_diagnostics(parsed.ast, single_file=True) == ()


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
    """Every legacy relationship JOIN (read by the private legacy reader, in
    its spelling) is refused in every entry, with or without `from`, `via` or
    `on`. Single files and EXPLICIT_MODULES projects inline def calls;
    LEGACY_FLAT and PACKAGE_ROOT projects keep every def gated."""
    parsed = _parse_legacy_source(
        "def f(x: Int not null) -> Int not null:\n    return x\n"
        "query q:\n    from rows\n    inner join others as o: via link\n"
        "    left join others as p\n"
        "    left join others as q: on q.id == rows.id\n"
        "    cross join others as x\n    select:\n        id\n",
        path="gate.pietto",
    )
    assert parsed.diagnostics == () and parsed.ast is not None
    joins = [("PIE-S2378", line, 5) for line in (5, 6, 7, 8)]
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


def test_public_analyze_refuses_a_legacy_via_join_instead_of_dropping_its_match() -> (
    None
):
    """pietto.semantic.analyze once read this hand-built (legacy reader) JOIN by
    its `on` alone, dropping the relationship's equality from the SQL; every
    retired form is now refused before any reader sees it."""
    parsed = _parse_legacy_source(
        "shape Order:\n    id: Int not null\n    customer_id: Int nullable\n"
        "shape Customer:\n    id: Int not null\n    name: Text not null\n"
        "    unique customer_key on id\n"
        'source orders: Order is postgres.table("shop.orders")\n'
        'source customers: Customer is postgres.table("shop.customers")\n'
        "relationship order_customer: orders.customer_id == customers.id\n"
        "query q:\n    from orders\n    left join customers as customer:\n"
        "        from orders\n        via order_customer\n"
        '        on customer.name != "x"\n'
        "    select:\n        order_id = orders.id\n",
        path="gate.pietto",
    )
    assert parsed.diagnostics == () and parsed.ast is not None

    result = analyze(parsed.ast)

    assert _located(result.diagnostics) == [("PIE-S2378", 10, 1), ("PIE-S2378", 13, 5)]
    assert result.diagnostics[1].message == LEGACY_JOIN
    assert result.model.relation_joins == {}
