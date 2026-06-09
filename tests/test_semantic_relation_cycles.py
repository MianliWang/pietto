from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import fields, is_dataclass
from pathlib import Path

from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import QueryDef, Script, SourceDef, TableDef
from pietto.errors import Diagnostic, Severity
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, analyze

SOURCE = (
    'shape Row:\n    id: UUID not null\nsource rows: Row is postgres.table("rows")\n'
)


def test_table_self_cycle_reports_p2302() -> None:
    result = analyze(_parse("table loop:\n    from loop\n    select:\n        id\n"))

    assert _diagnostics(result) == [
        ("PIE-S2302", Severity.ERROR, "Relation cycle detected: loop -> loop")
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
        (
            "PIE-S2302",
            Severity.ERROR,
            "Relation cycle detected: first -> second -> first",
        )
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

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2302"]
    assert result.diagnostics[0].message == (
        "Relation cycle detected: output -> projected -> output"
    )


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

    assert result.diagnostics == ()


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
    path = Path("examples/semantic/relation-cycles.pie")
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
        (6, "PIE-S2302", "Relation cycle detected: first -> second -> first"),
        (10, "PIE-S2302", "Relation cycle detected: self_cycle -> self_cycle"),
    ]
    _assert_location_matches(diagnostics[0], first_cycle_closer)
    _assert_location_matches(diagnostics[1], second_cycle_closer)


def test_unknown_relation_still_reports_only_p2301() -> None:
    result = analyze(
        _parse("table projected:\n    from missing\n    select:\n        id\n")
    )

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2301"]


def test_cycle_suppresses_field_and_expression_diagnostics() -> None:
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

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2302"]


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
