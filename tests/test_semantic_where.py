from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import fields, is_dataclass

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import QueryDef, Script, TableDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import CheckMode, SemanticResult, ValueTypeKind, analyze

SOURCE = (
    "shape Row:\n"
    "    text: Text not null\n"
    "    count: Int not null\n"
    "    optional_text: Text nullable\n"
    'source rows: Row is postgres.table("rows")\n'
)


@pytest.mark.parametrize("operator", ["is null", "is not null"])
def test_is_null_where_expression_is_bool(operator: str) -> None:
    result = analyze(
        _parse(
            SOURCE + "table filtered:\n"
            "    from rows\n"
            f"    where optional_text {operator}\n"
            "    select:\n"
            "        text\n"
        )
    )
    expression = _table(result).where_clause.expression

    assert result.diagnostics == ()
    assert result.model.expression_value_types[expression].resolved_type.name == "Bool"


def test_simple_comparison_where_expression_is_bool() -> None:
    result = analyze(
        _parse(
            SOURCE + "table filtered:\n"
            "    from rows\n"
            "    where count >= 1\n"
            "    select:\n"
            "        text\n"
        )
    )
    expression = _table(result).where_clause.expression

    assert result.diagnostics == ()
    assert result.model.expression_value_types[expression].resolved_type.name == "Bool"


@pytest.mark.parametrize(
    ("field_name", "type_name"), [("text", "Text"), ("count", "Int")]
)
def test_known_non_bool_table_where_reports_pie_s2202(
    field_name: str,
    type_name: str,
) -> None:
    result = analyze(
        _parse(
            SOURCE + "table filtered:\n"
            "    from rows\n"
            f"    where {field_name}\n"
            "    select:\n"
            "        text\n"
        )
    )
    expression = _table(result).where_clause.expression

    assert [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in result.diagnostics
    ] == [
        (
            "PIE-S2202",
            Severity.ERROR,
            "Expected Bool expression in where clause",
        )
    ]
    assert (
        result.model.expression_value_types[expression].resolved_type.name == type_name
    )


def test_non_bool_where_diagnostic_uses_expression_span() -> None:
    script = _parse(
        SOURCE + "table filtered:\n"
        "    from rows\n"
        "    where text\n"
        "    select:\n"
        "        text\n",
        path="where.pie",
    )
    result = analyze(script)
    expression = _table(result).where_clause.expression
    diagnostic = result.diagnostics[0]

    assert diagnostic.code == "PIE-S2202"
    assert diagnostic.location.path == expression.span.path == "where.pie"
    assert (
        diagnostic.location.line,
        diagnostic.location.column,
        diagnostic.location.end_line,
        diagnostic.location.end_column,
    ) == (
        expression.span.line,
        expression.span.column,
        expression.span.end_line,
        expression.span.end_column,
    )


def test_unknown_field_suppresses_bool_cascade() -> None:
    result = analyze(
        _parse(
            SOURCE + "table filtered:\n"
            "    from rows\n"
            "    where missing\n"
            "    select:\n"
            "        text\n"
        )
    )
    expression = _table(result).where_clause.expression

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2102"]
    assert result.model.expression_value_types[expression].kind is ValueTypeKind.UNKNOWN


def test_unknown_input_schema_suppresses_field_and_bool_diagnostics() -> None:
    result = analyze(
        _parse(
            'source raw is postgres.table("raw")\n'
            "table filtered:\n"
            "    from raw\n"
            "    where missing\n"
            "    select:\n"
            "        missing\n"
        ),
        mode_override=CheckMode.LOOSE,
    )
    expression = _table(result).where_clause.expression

    assert result.diagnostics == ()
    assert result.model.expression_value_types[expression].kind is ValueTypeKind.UNKNOWN


def test_known_non_bool_query_where_reports_pie_s2202() -> None:
    result = analyze(
        _parse(
            SOURCE + "query filtered:\n"
            "    from rows\n"
            "    where text\n"
            "    select:\n"
            "        text\n"
        )
    )
    expression = _query(result).where_clause.expression

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2202"]
    assert result.model.expression_value_types[expression].resolved_type.name == "Text"


def test_unknown_function_suppresses_bool_diagnostic() -> None:
    result = analyze(
        _parse(
            SOURCE + "table filtered:\n"
            "    from rows\n"
            "    where unknown_call(text)\n"
            "    select:\n"
            "        text\n"
        )
    )
    expression = _table(result).where_clause.expression

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2103"]
    assert result.model.expression_value_types[expression].kind is ValueTypeKind.UNKNOWN


def test_where_validation_does_not_mutate_input_ast() -> None:
    script = _parse(
        SOURCE + "table filtered:\n"
        "    from rows\n"
        "    where text\n"
        "    select:\n"
        "        text\n"
    )
    original = deepcopy(script)

    analyze(script)

    assert script == original


def test_where_semantic_results_do_not_expose_antlr_nodes() -> None:
    result = analyze(
        _parse(
            SOURCE + "query filtered:\n"
            "    from rows\n"
            "    where text\n"
            "    select:\n"
            "        text\n"
        )
    )

    _assert_no_antlr_nodes(result)


def _parse(source: str, *, path: str | None = None) -> Script:
    result = parse_source(source, path=path)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _table(result: SemanticResult) -> TableDef:
    definition = result.model.relation_symbols["filtered"]
    assert isinstance(definition, TableDef)
    assert definition.where_clause is not None
    return definition


def _query(result: SemanticResult) -> QueryDef:
    definition = result.model.relation_symbols["filtered"]
    assert isinstance(definition, QueryDef)
    assert definition.where_clause is not None
    return definition


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
