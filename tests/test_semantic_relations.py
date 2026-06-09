from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import fields, is_dataclass
from pathlib import Path

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import QueryDef, Script, SourceDef, TableDef
from pietto.errors import Diagnostic, Severity
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, analyze

SOURCE = (
    'shape Row:\n    id: UUID not null\nsource rows: Row is postgres.table("rows")\n'
)


def test_table_from_source_resolves_to_source() -> None:
    result = analyze(
        _parse(SOURCE + "table projected:\n    from rows\n    select:\n        id\n")
    )
    table = _relation(result, "projected", TableDef)

    assert result.model.from_resolutions[table.from_clause] is _relation(
        result,
        "rows",
        SourceDef,
    )
    assert result.diagnostics == ()


def test_query_from_source_resolves_to_source() -> None:
    result = analyze(
        _parse(SOURCE + "query output:\n    from rows\n    select:\n        id\n")
    )
    query = _relation(result, "output", QueryDef)

    assert result.model.from_resolutions[query.from_clause] is _relation(
        result,
        "rows",
        SourceDef,
    )


def test_query_from_table_resolves_to_table() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from rows\n"
            "    select:\n"
            "        id\n"
            "query output:\n"
            "    from projected\n"
            "    select:\n"
            "        id\n"
        )
    )
    query = _relation(result, "output", QueryDef)

    assert result.model.from_resolutions[query.from_clause] is _relation(
        result,
        "projected",
        TableDef,
    )


def test_table_from_query_resolves_to_query() -> None:
    result = analyze(
        _parse(
            SOURCE + "query projected:\n"
            "    from rows\n"
            "    select:\n"
            "        id\n"
            "table materialized:\n"
            "    from projected\n"
            "    select:\n"
            "        id\n"
        )
    )
    table = _relation(result, "materialized", TableDef)

    assert result.model.from_resolutions[table.from_clause] is _relation(
        result,
        "projected",
        QueryDef,
    )


def test_forward_relation_references_resolve() -> None:
    result = analyze(
        _parse(
            "query output:\n"
            "    from projected\n"
            "    select:\n"
            "        id\n"
            "table projected:\n"
            "    from rows\n"
            "    select:\n"
            "        id\n"
            "shape Row:\n"
            "    id: UUID not null\n"
            'source rows: Row is postgres.table("rows")\n'
        )
    )
    query = _relation(result, "output", QueryDef)
    table = _relation(result, "projected", TableDef)

    assert result.model.from_resolutions[query.from_clause] is table
    assert result.model.from_resolutions[table.from_clause] is _relation(
        result,
        "rows",
        SourceDef,
    )
    assert result.diagnostics == ()


def test_unknown_relation_reports_p2301() -> None:
    result = analyze(
        _parse("table projected:\n    from missing\n    select:\n        id\n")
    )
    table = _relation(result, "projected", TableDef)

    assert [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in result.diagnostics
    ] == [("PIE-S2301", Severity.ERROR, "Unknown relation: missing")]
    assert table.from_clause not in result.model.from_resolutions


def test_unknown_relation_diagnostic_uses_from_clause_span() -> None:
    path = Path("examples/semantic/unknown-relation.pie")
    script = _parse(
        "query output:\n    from missing\n    select:\n        id\n",
        path=path,
    )
    query = script.definitions[0]
    assert isinstance(query, QueryDef)

    diagnostic = analyze(script).diagnostics[0]

    _assert_location_matches(diagnostic, query)


def test_relation_resolution_continues_after_unknown_target() -> None:
    result = analyze(
        _parse(
            SOURCE + "table broken:\n"
            "    from missing\n"
            "    select:\n"
            "        id\n"
            "query output:\n"
            "    from rows\n"
            "    select:\n"
            "        id\n"
        )
    )
    broken = _relation(result, "broken", TableDef)
    output = _relation(result, "output", QueryDef)

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2301"]
    assert broken.from_clause not in result.model.from_resolutions
    assert result.model.from_resolutions[output.from_clause] is _relation(
        result,
        "rows",
        SourceDef,
    )


def test_missing_call_arguments_report_fields_without_call_cascades() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from rows\n"
            "    where unknown_predicate(missing_field)\n"
            "    select:\n"
            "        missing_field\n"
            "        computed = unknown_call(missing_field)\n"
        )
    )

    assert [diagnostic.code for diagnostic in result.diagnostics] == [
        "PIE-S2102",
        "PIE-S2102",
        "PIE-S2102",
    ]


def test_duplicate_relation_uses_first_binding_for_from_resolution() -> None:
    result = analyze(
        _parse(
            SOURCE + "table rows:\n"
            "    from rows\n"
            "    select:\n"
            "        id\n"
            "query output:\n"
            "    from rows\n"
            "    select:\n"
            "        id\n"
        )
    )
    output = _relation(result, "output", QueryDef)

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2001"]
    assert result.model.from_resolutions[output.from_clause] is _relation(
        result,
        "rows",
        SourceDef,
    )


def test_relation_cycles_are_resolved_and_diagnosed() -> None:
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
    first = _relation(result, "first", TableDef)
    second = _relation(result, "second", TableDef)

    assert result.model.from_resolutions[first.from_clause] is second
    assert result.model.from_resolutions[second.from_clause] is first
    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2302"]


def test_from_resolutions_mapping_is_readonly() -> None:
    result = analyze(
        _parse(SOURCE + "table projected:\n    from rows\n    select:\n        id\n")
    )
    table = _relation(result, "projected", TableDef)

    with pytest.raises(TypeError):
        result.model.from_resolutions[table.from_clause] = _relation(  # type: ignore[index]
            result,
            "rows",
            SourceDef,
        )


def test_relation_resolution_does_not_mutate_input_ast() -> None:
    script = _parse(
        SOURCE + "table projected:\n    from rows\n    select:\n        id\n"
    )
    original = deepcopy(script)

    analyze(script)

    assert script == original


def test_relation_semantic_results_do_not_expose_antlr_nodes() -> None:
    result = analyze(
        _parse(
            SOURCE + "table broken:\n"
            "    from missing\n"
            "    select:\n"
            "        id\n"
            "query output:\n"
            "    from rows\n"
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
