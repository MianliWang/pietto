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
from pietto.semantic import CheckMode, SemanticResult, analyze

SOURCE = 'shape Row:\n    id: UUID\nsource rows: Row = postgres.table("rows")\n'


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
            "    id: UUID\n"
            'source rows: Row = postgres.table("rows")\n'
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
    # The query's single-file read of the table `projected` warns, nothing else.
    assert [
        (d.code, d.severity, d.location.line, d.location.column)
        for d in result.diagnostics
    ] == [("PIE-S2382", Severity.WARNING, 2, 5)]


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
    path = Path("examples/semantic/unknown-relation.pietto")
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
    assert [diagnostic.code for diagnostic in result.diagnostics] == [
        "PIE-S2382",
        "PIE-S2302",
        "PIE-S2382",
    ]


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


def test_unknown_definition_has_syntax_availability_diagnostic() -> None:
    from typing import Any, cast

    from pietto import ast_nodes as ast
    from pietto._flat_relational_admission import (
        syntax_diagnostics,
        availability_diagnostic,
    )

    class UnknownDefinition(ast.Node):
        pass

    span = ast.Span(path=None, line=1, column=1, end_line=1, end_column=2)
    unknown = UnknownDefinition(span=span)
    assert syntax_diagnostics(cast(Any, unknown)) == (
        availability_diagnostic(span, "Definition semantics are not implemented."),
    )


def test_unknown_definition_has_one_availability_diagnostic() -> None:
    from typing import Any, cast

    from pietto import ast_nodes as ast
    from pietto.semantic.relations import resolve_relation_inputs
    from pietto._flat_relational_admission import (
        availability_diagnostic,
        syntax_diagnostics,
    )

    class UnknownDefinition(ast.Node):
        pass

    span = ast.Span(path=None, line=1, column=1, end_line=1, end_column=2)
    unknown = cast(Any, UnknownDefinition(span=span))
    script = ast.Script(span=span, header=None, definitions=(unknown,))
    resolutions, relation_diagnostics = resolve_relation_inputs(script, {})
    # The analyzer concatenates both passes; only syntax_diagnostics reports.
    assert resolutions == {}
    assert [*relation_diagnostics, *syntax_diagnostics(unknown)] == [
        availability_diagnostic(span, "Definition semantics are not implemented.")
    ]


def test_single_file_select_distinct_names_the_project_that_completes_it() -> None:
    result = analyze(
        _parse(
            'shape Row:\n    id: Int\nsource rows: Row = postgres.table("rows")\n'
            "query d:\n    from rows\n    select distinct:\n        id\n"
        )
    )

    assert [
        (d.code, d.severity, d.location.line, d.location.column, d.message)
        for d in result.diagnostics
    ] == [
        (
            "PIE-S2334",
            Severity.ERROR,
            6,
            12,
            "SELECT DISTINCT is available only when an EXPLICIT_MODULES project "
            "(schema version 2) completes it.",
        )
    ]


_READS = (
    'shape Row:\n    id: UUID\nsource rows: Row = postgres.table("rows")\n'
    "table kept:\n    from rows\n    select id\n"
    "query from_table:\n    from kept\n    select id\n"
    "query from_query:\n    from from_table\n    select id\n"
    "query joined:\n    from rows\n    let k = kept\n"
    "    inner join k on k.id == rows.id\n    select rows.id\n"
    "query tested:\n    from rows\n"
    "    where any(k.id == rows.id for k in kept)\n    select id\n"
    "query filtered:\n    from rows\n"
    "    where any(k.id == rows.id for k in kept)\n"
    "    let other = rows\n    left join other on other.id == rows.id\n"
    "    select rows.id\n"
)


@pytest.mark.parametrize("mode", list(CheckMode))
def test_each_read_of_a_relation_of_the_file_warns_that_sql_reads_it_by_name(
    mode: CheckMode,
) -> None:
    """Single-file SQL reads a table or query of the file by its name, so a
    FROM and a JOIN of one warn where PIE-S2301 reports an unknown name, and
    an ANY before a later JOIN at its relation. Any other ANY does not warn:
    its reader's SQL defines the relation as a CTE."""

    def message(name: str, kind: str) -> str:
        return (
            f"`{name}` is a {kind} of this file; single-file SQL reads it by name, "
            "so the SQL runs only where the database already has a relation "
            f"named {name} (an EXPLICIT_MODULES project emits it as a CTE)"
        )

    result = analyze(_parse(_READS), mode_override=mode)

    assert [
        (
            d.code,
            d.severity,
            d.message,
            d.location.line,
            d.location.column,
            d.location.end_line,
            d.location.end_column,
        )
        for d in result.diagnostics
    ] == [
        ("PIE-S2382", Severity.WARNING, message("kept", "table"), 8, 5, 8, 14),
        ("PIE-S2382", Severity.WARNING, message("from_table", "query"), 11, 5, 11, 20),
        ("PIE-S2382", Severity.WARNING, message("kept", "table"), 16, 5, 16, 36),
        ("PIE-S2382", Severity.WARNING, message("kept", "table"), 24, 40, 24, 44),
    ]


def test_reads_of_sources_and_project_reads_do_not_warn() -> None:
    from pietto.semantic.analyzer import analyze_project_namespace

    sources = analyze(
        _parse(
            'shape Row:\n    id: UUID\nsource rows: Row = postgres.table("rows")\n'
            "query q:\n    from rows\n    let r = rows\n"
            "    inner join r on r.id == rows.id\n"
            "    where any(x.id == rows.id for x in rows)\n    select rows.id\n"
        )
    )
    # A LEGACY_FLAT project emits no SQL, so its reads are no SQL premise.
    project = analyze_project_namespace(_parse(_READS))

    assert sources.diagnostics == ()
    assert [d.code for d in project.diagnostics if d.code == "PIE-S2382"] == []
