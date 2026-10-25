from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import fields, is_dataclass
from pathlib import Path

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import (
    FromClause,
    JoinClause,
    QueryDef,
    Script,
    SourceDef,
    TableDef,
)
from pietto.errors import Diagnostic, Severity
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, analyze
from pietto.semantic.analyzer import analyze_project_namespace
from pietto.semantic.relation_cycles import check_relation_cycles

SOURCE = 'shape Row:\n    id: UUID\nsource rows: Row = postgres.table("rows")\n'


def _same_file_read(name: str, kind: str = "table") -> str:
    """The PIE-S2382 warning at a read of a table or query of the file."""
    return (
        f"`{name}` is a {kind} of this file; single-file SQL reads it by name, so "
        "the SQL runs only where the database already has a relation named "
        f"{name} (an EXPLICIT_MODULES project emits it as a CTE)"
    )


def test_table_self_cycle_reports_p2302() -> None:
    result = analyze(_parse("table loop:\n    from loop\n    select:\n        id\n"))

    assert _diagnostics(result) == [
        ("PIE-S2302", Severity.ERROR, "Relation cycle detected: loop -> loop"),
        ("PIE-S2382", Severity.WARNING, _same_file_read("loop")),
    ]


def test_table_table_cycle_reports_one_p2302() -> None:
    result = analyze(
        _parse(
            "table first:\n"
            "    from second\n"
            "    select:\n"
            "        id\n"
            "table second:\n"
            "    from first\n"
            "    select:\n"
            "        id\n"
        )
    )

    assert _diagnostics(result) == [
        ("PIE-S2382", Severity.WARNING, _same_file_read("second")),
        (
            "PIE-S2302",
            Severity.ERROR,
            "Relation cycle detected: first -> second -> first",
        ),
        ("PIE-S2382", Severity.WARNING, _same_file_read("first")),
    ]


def test_query_table_mixed_cycle_reports_p2302() -> None:
    result = analyze(
        _parse(
            "query output:\n"
            "    from projected\n"
            "    select:\n"
            "        id\n"
            "table projected:\n"
            "    from output\n"
            "    select:\n"
            "        id\n"
        )
    )

    assert _diagnostics(result) == [
        ("PIE-S2382", Severity.WARNING, _same_file_read("projected")),
        (
            "PIE-S2302",
            Severity.ERROR,
            "Relation cycle detected: output -> projected -> output",
        ),
        ("PIE-S2382", Severity.WARNING, _same_file_read("output", "query")),
    ]


def test_source_dependency_is_not_a_cycle() -> None:
    result = analyze(
        _parse(SOURCE + "table projected:\n    from rows\n    select:\n        id\n")
    )

    assert not any(diagnostic.code == "PIE-S2302" for diagnostic in result.diagnostics)


def test_acyclic_relation_chain_has_no_cycle_diagnostic() -> None:
    result = analyze(
        _parse(
            SOURCE + "table first:\n"
            "    from rows\n"
            "    select:\n"
            "        id\n"
            "query second:\n"
            "    from first\n"
            "    select:\n"
            "        id\n"
            "table third:\n"
            "    from second\n"
            "    select:\n"
            "        id\n"
        )
    )

    assert _diagnostics(result) == [
        ("PIE-S2382", Severity.WARNING, _same_file_read("first")),
        ("PIE-S2382", Severity.WARNING, _same_file_read("second", "query")),
    ]


def test_cyclic_relations_have_unknown_row_schemas() -> None:
    result = analyze(
        _parse(
            "table first:\n"
            "    from second\n"
            "    select:\n"
            "        id\n"
            "query second:\n"
            "    from first\n"
            "    select:\n"
            "        id\n"
        )
    )
    first = _relation(result, "first", TableDef)
    second = _relation(result, "second", QueryDef)

    assert result.model.relation_row_schemas[first].is_unknown
    assert result.model.relation_row_schemas[second].is_unknown


def test_cycle_diagnostics_are_deterministic_and_use_closing_from_spans() -> None:
    path = Path("examples/semantic/relation-cycles.pietto")
    script = _parse(
        "table first:\n"
        "    from second\n"
        "    select:\n"
        "        id\n"
        "table second:\n"
        "    from first\n"
        "    select:\n"
        "        id\n"
        "query self_cycle:\n"
        "    from self_cycle\n"
        "    select:\n"
        "        id\n",
        path=path,
    )
    first_cycle_closer = script.definitions[1]
    second_cycle_closer = script.definitions[2]
    assert isinstance(first_cycle_closer, TableDef)
    assert isinstance(second_cycle_closer, QueryDef)

    diagnostics = analyze(script).diagnostics

    assert [
        (diagnostic.location.line, diagnostic.code, diagnostic.message)
        for diagnostic in diagnostics
    ] == [
        (2, "PIE-S2382", _same_file_read("second")),
        (6, "PIE-S2302", "Relation cycle detected: first -> second -> first"),
        (6, "PIE-S2382", _same_file_read("first")),
        (10, "PIE-S2302", "Relation cycle detected: self_cycle -> self_cycle"),
        (10, "PIE-S2382", _same_file_read("self_cycle", "query")),
    ]
    _assert_location_matches(diagnostics[1], first_cycle_closer)
    _assert_location_matches(diagnostics[3], second_cycle_closer)


def test_unknown_relation_still_reports_only_p2301() -> None:
    result = analyze(
        _parse("table projected:\n    from missing\n    select:\n        id\n")
    )

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2301"]


def test_cycle_suppresses_field_diagnostics_but_not_an_unknown_function() -> None:
    result = analyze(
        _parse(
            "table first:\n"
            "    from second\n"
            "    where unknown_predicate(missing_where)\n"
            "    select:\n"
            "        missing_first\n"
            "table second:\n"
            "    from first\n"
            "    select:\n"
            "        missing_second\n"
        )
    )

    # The cycle explains the unknown fields; a function name reads none of them.
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in result.diagnostics
    ] == [
        ("PIE-S2382", _same_file_read("second"), 2, 5),
        ("PIE-S2103", "Unknown function: unknown_predicate", 3, 11),
        ("PIE-S2302", "Relation cycle detected: first -> second -> first", 7, 5),
        ("PIE-S2382", _same_file_read("first"), 7, 5),
    ]


def test_relation_cycle_analysis_does_not_mutate_input_ast() -> None:
    script = _parse("table loop:\n    from loop\n    select:\n        id\n")
    original = deepcopy(script)

    analyze(script)

    assert script == original


def test_relation_cycle_results_do_not_expose_antlr_nodes() -> None:
    result = analyze(
        _parse(
            "table first:\n"
            "    from second\n"
            "    select:\n"
            "        id\n"
            "query second:\n"
            "    from first\n"
            "    select:\n"
            "        id\n"
        )
    )

    _assert_no_antlr_nodes(result)


def _parse(source: str, *, path: Path | None = None) -> Script:
    result = parse_source(source, path=path)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _named(source: str) -> Script:
    """The script with each `let name = relation` JOIN target resolved to its
    relation, as the analyzer checks cycles over it."""

    script = analyze(_parse(source)).script
    assert script is not None
    return script


def _relation[RelationT: (SourceDef, TableDef, QueryDef)](
    result: SemanticResult,
    name: str,
    expected_type: type[RelationT],
) -> RelationT:
    definition = result.model.relation_symbols[name]
    assert isinstance(definition, expected_type)
    return definition


def _diagnostics(
    result: SemanticResult,
) -> list[tuple[str, Severity, str]]:
    return [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in result.diagnostics
    ]


def _assert_location_matches(
    diagnostic: Diagnostic,
    definition: TableDef | QueryDef,
) -> None:
    span = definition.from_clause.span
    assert diagnostic.location.path == span.path
    assert diagnostic.location.line == span.line
    assert diagnostic.location.column == span.column
    assert diagnostic.location.end_line == span.end_line
    assert diagnostic.location.end_column == span.end_column


def _assert_no_antlr_nodes(value: object) -> None:
    assert not isinstance(value, ParserRuleContext)
    assert not isinstance(value, Token)
    assert not type(value).__module__.startswith("pietto.generated")
    if is_dataclass(value):
        for field in fields(value):
            _assert_no_antlr_nodes(getattr(value, field.name))
    elif isinstance(value, Mapping):
        for key, item in value.items():
            _assert_no_antlr_nodes(key)
            _assert_no_antlr_nodes(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _assert_no_antlr_nodes(item)


def test_a_join_target_closes_a_cycle_at_the_join_only_with_join_edges() -> None:
    script = _named(
        SOURCE + "table second:\n"
        "    from first\n"
        "    select:\n"
        "        id\n"
        "table first:\n"
        "    from rows\n"
        "    let peer = second\n"
        "    inner join peer on peer.id == rows.id\n"
        "    select:\n"
        "        id\n"
    )
    from_resolutions, join_resolutions = _resolutions(script)

    assert check_relation_cycles(script, from_resolutions) == (set(), [])
    cyclic, diagnostics = check_relation_cycles(
        script, from_resolutions, join_resolutions=join_resolutions
    )

    assert cyclic == set(script.definitions[2:])
    assert _located(diagnostics) == [
        (
            "PIE-S2302",
            Severity.ERROR,
            "Relation cycle detected: second -> first -> second",
            (11, 5, 11, 42),
        )
    ]


def test_every_join_that_closes_a_cycle_reports_it_in_join_order() -> None:
    script = _named(
        SOURCE + "table loop:\n"
        "    from rows\n"
        "    let again = loop\n"
        "    inner join again on rows.id == again.id\n"
        "    let other = rows\n"
        "    left join other on other.id == rows.id\n"
        "    cross join missing\n"
        "    let twice = loop\n"
        "    left join twice on twice.id == rows.id\n"
        "    select:\n"
        "        id\n"
    )
    from_resolutions, join_resolutions = _resolutions(script)

    cyclic, diagnostics = check_relation_cycles(
        script, from_resolutions, join_resolutions=join_resolutions
    )

    # A source target and an unresolved target are no dependency edges.
    assert cyclic == {script.definitions[2]}
    assert _located(diagnostics) == [
        ("PIE-S2302", Severity.ERROR, "Relation cycle detected: loop -> loop", span)
        for span in ((7, 5, 7, 44), (12, 5, 12, 43))
    ]


def test_join_edges_are_followed_after_the_from_edge() -> None:
    script = _named(
        SOURCE + "table hub:\n"
        "    from back_from\n"
        "    let peer = back_join\n"
        "    inner join peer on peer.id == back_from.id\n"
        "    select:\n"
        "        id\n"
        "table back_from:\n"
        "    from hub\n"
        "    select:\n"
        "        id\n"
        "table back_join:\n"
        "    from hub\n"
        "    select:\n"
        "        id\n"
    )
    from_resolutions, join_resolutions = _resolutions(script)

    cyclic, diagnostics = check_relation_cycles(
        script, from_resolutions, join_resolutions=join_resolutions
    )

    assert cyclic == set(script.definitions[2:])
    assert _located(diagnostics) == [
        (
            "PIE-S2302",
            Severity.ERROR,
            "Relation cycle detected: hub -> back_from -> hub",
            (11, 5, 11, 13),
        ),
        (
            "PIE-S2302",
            Severity.ERROR,
            "Relation cycle detected: hub -> back_join -> hub",
            (15, 5, 15, 13),
        ),
    ]


FIGURE_EIGHT = {
    "a": "table a:\n    from b\n    let x = c\n    cross join x\n    select:\n        id\n",
    "b": "table b:\n    from a\n    select:\n        id\n",
    "c": "query c:\n    from rows\n    let y = b\n    cross join y\n"
    "    select:\n        id\n",
    "d": "table d:\n    from c\n    select:\n        id\n",
}


@pytest.mark.parametrize(
    ("order", "cycles"),
    [
        ("abcd", [("a -> b -> a", (11, 5, 11, 11))]),
        (
            "cabd",
            [("b -> a -> b", (11, 5, 11, 11)), ("c -> b -> a -> c", (13, 5, 13, 17))],
        ),
    ],
)
def test_every_relation_on_a_cycle_is_cyclic_whatever_the_definition_order(
    order: str, cycles: list[tuple[str, tuple[int, int, int, int]]]
) -> None:
    script = _named(SOURCE + "".join(FIGURE_EIGHT[name] for name in order))
    from_resolutions, join_resolutions = _resolutions(script)

    cyclic, diagnostics = check_relation_cycles(
        script, from_resolutions, join_resolutions=join_resolutions
    )

    # Query c is on the cycle a -> c -> b -> a, which no report names when a
    # is written first; d only reads the cycle.
    assert {definition.name for definition in cyclic} == {"a", "b", "c"}
    assert _located(diagnostics) == [
        ("PIE-S2302", Severity.ERROR, f"Relation cycle detected: {path}", span)
        for path, span in cycles
    ]


@pytest.mark.parametrize(
    ("order", "path", "span"),
    [
        ("abcd", "a -> b -> a", (11, 5, 11, 11)),
        ("cabd", "a -> b -> a", (17, 5, 17, 11)),
        ("dcba", "b -> a -> b", (19, 5, 19, 11)),
    ],
)
def test_without_join_edges_every_cycle_is_reported_with_all_its_relations(
    order: str, path: str, span: tuple[int, int, int, int]
) -> None:
    script = _named(SOURCE + "".join(FIGURE_EIGHT[name] for name in order))
    from_resolutions, _ = _resolutions(script)

    cyclic, diagnostics = check_relation_cycles(script, from_resolutions)

    # Without JOIN edges, as a project namespace analysis calls it, every
    # relation reads one input: the one cycle is reported, names all of its
    # relations, and c and d are not cyclic, whatever the order.
    assert {definition.name for definition in cyclic} == {"a", "b"}
    assert _located(diagnostics) == [
        ("PIE-S2302", Severity.ERROR, f"Relation cycle detected: {path}", span)
    ]


INNER_EIGHT = {
    "a": "table a:\n    from b\n    let x = c\n    inner join x\n    select:\n        id\n",
    "b": "table b:\n    from a\n    select:\n        id\n",
    "c": "query c:\n    from rows\n    let y = b\n    inner join y\n"
    "    select:\n        id\n",
}


@pytest.mark.parametrize(
    ("order", "span"), [("abc", (11, 5, 11, 11)), ("cab", (17, 5, 17, 11))]
)
def test_a_project_namespace_analysis_reports_only_the_from_cycle(
    order: str, span: tuple[int, int, int, int]
) -> None:
    script = _parse(SOURCE + "".join(INNER_EIGHT[name] for name in order))

    # A LEGACY_FLAT check passes no JOIN edges, so of the cycles a -> b -> a
    # and a -> c -> b -> a it reports only the one that FROM closes; the
    # project model refuses each JOIN, as that project mode has none.
    assert _located(list(analyze_project_namespace(script).diagnostics)) == [
        ("PIE-S2302", Severity.ERROR, "Relation cycle detected: a -> b -> a", span)
    ]


def _resolutions(
    script: Script,
) -> tuple[
    dict[FromClause, SourceDef | TableDef | QueryDef],
    dict[JoinClause, SourceDef | TableDef | QueryDef],
]:
    relations = {
        definition.name: definition
        for definition in script.definitions
        if isinstance(definition, (SourceDef, TableDef, QueryDef))
    }
    derived = [
        definition
        for definition in script.definitions
        if isinstance(definition, (TableDef, QueryDef))
    ]
    return (
        {
            definition.from_clause: relations[definition.from_clause.source_name]
            for definition in derived
            if definition.from_clause.source_name in relations
        },
        {
            clause: relations[clause.target_relation_name]
            for definition in derived
            for clause in definition.join_clauses
            if clause.target_relation_name in relations
        },
    )


def _located(
    diagnostics: list[Diagnostic],
) -> list[tuple[str, Severity, str, tuple[int, int, int | None, int | None]]]:
    return [
        (
            diagnostic.code,
            diagnostic.severity,
            diagnostic.message,
            (
                diagnostic.location.line,
                diagnostic.location.column,
                diagnostic.location.end_line,
                diagnostic.location.end_column,
            ),
        )
        for diagnostic in diagnostics
    ]
