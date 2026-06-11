from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import fields, is_dataclass

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import CallExpr, Expression, Script, TableDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import (
    EffectiveNullability,
    SemanticResult,
    TypeKind,
    ValueTypeKind,
    analyze,
)

SOURCE = (
    "shape User:\n"
    "    email: Text nullable\n"
    "    count: Int not null\n"
    'source users: User is postgres.table("users")\n'
)


@pytest.mark.parametrize("function_name", ["lower", "trim"])
def test_text_transform_function_returns_text(function_name: str) -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            f"        value = {function_name}(email)\n"
        )
    )
    expression = _call(result)
    value_type = result.model.expression_value_types[expression]

    assert result.diagnostics == ()
    assert value_type.kind is ValueTypeKind.KNOWN
    assert value_type.resolved_type.kind is TypeKind.BUILTIN
    assert value_type.resolved_type.name == "Text"
    assert value_type.nullability is EffectiveNullability.UNKNOWN


def test_nested_lower_trim_returns_text_and_records_inner_call() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        value = lower(trim(email))\n"
        )
    )
    expression = _call(result)
    inner = expression.arguments[0]
    assert isinstance(inner, CallExpr)

    assert result.diagnostics == ()
    assert result.model.expression_value_types[expression].resolved_type.name == "Text"
    assert result.model.expression_value_types[inner].resolved_type.name == "Text"


def test_len_returns_int() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        length = len(email)\n"
        )
    )
    expression = _call(result)

    assert result.diagnostics == ()
    assert result.model.expression_value_types[expression].resolved_type.name == "Int"


def test_matches_returns_bool_and_is_valid_where_predicate() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            '    where matches(email, "^[a-z]+$")\n'
            "    select:\n"
            "        email\n"
        )
    )
    expression = _where_expression(result)
    assert isinstance(expression, CallExpr)

    assert result.diagnostics == ()
    assert result.model.expression_value_types[expression].resolved_type.name == "Bool"


def test_unknown_function_reports_pie_s2103() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        value = normalize(email)\n"
        )
    )
    expression = _call(result)

    assert [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in result.diagnostics
    ] == [("PIE-S2103", Severity.ERROR, "Unknown function: normalize")]
    assert result.model.expression_value_types[expression].kind is ValueTypeKind.UNKNOWN


def test_wrong_argument_count_reports_pie_s2104() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        value = lower(email, email)\n"
        )
    )

    assert [
        (diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics
    ] == [
        (
            "PIE-S2104",
            "Invalid arguments for function lower: expected 1, got 2",
        )
    ]


def test_wrong_argument_type_reports_pie_s2104() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        value = lower(count)\n"
        )
    )

    assert [
        (diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics
    ] == [
        (
            "PIE-S2104",
            "Invalid argument type for function lower at position 1: "
            "expected Text, got Int",
        )
    ]


def test_unknown_argument_suppresses_call_diagnostic() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        value = lower(missing)\n"
        )
    )
    expression = _call(result)

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2102"]
    assert result.model.expression_value_types[expression].kind is ValueTypeKind.UNKNOWN
    assert (
        result.model.expression_value_types[expression.arguments[0]].kind
        is ValueTypeKind.UNKNOWN
    )


def test_call_diagnostic_uses_call_span() -> None:
    script = _parse(
        SOURCE + "table projected:\n"
        "    from users\n"
        "    select:\n"
        "        value = normalize(email)\n",
        path="functions.pietto",
    )
    result = analyze(script)
    expression = _call(result)
    diagnostic = result.diagnostics[0]

    assert diagnostic.code == "PIE-S2103"
    assert diagnostic.location.path == expression.span.path == "functions.pietto"
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


def test_function_typing_does_not_mutate_input_ast() -> None:
    script = _parse(
        SOURCE + "table projected:\n"
        "    from users\n"
        "    select:\n"
        "        value = lower(email)\n"
    )
    original = deepcopy(script)

    analyze(script)

    assert script == original


def test_function_semantic_results_do_not_expose_antlr_nodes() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        value = lower(trim(email))\n"
        )
    )

    _assert_no_antlr_nodes(result)


def _parse(source: str, *, path: str | None = None) -> Script:
    result = parse_source(source, path=path)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _table(result: SemanticResult) -> TableDef:
    definition = result.model.relation_symbols["projected"]
    assert isinstance(definition, TableDef)
    return definition


def _where_expression(result: SemanticResult) -> Expression:
    table = _table(result)
    assert table.where_clause is not None
    return table.where_clause.expression


def _call(result: SemanticResult) -> CallExpr:
    expression = _table(result).select_items[0].expression
    assert isinstance(expression, CallExpr)
    return expression


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
