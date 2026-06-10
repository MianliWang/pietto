from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import fields, is_dataclass

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import (
    CallExpr,
    ComparisonExpr,
    IsNullExpr,
    LiteralExpr,
    NameExpr,
    Script,
    TableDef,
)
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import (
    CheckMode,
    EffectiveNullability,
    SemanticResult,
    TypeKind,
    ValueTypeKind,
    analyze,
)

SOURCE = (
    "shape User:\n"
    "    id: UUID not null\n"
    "    email: Text nullable\n"
    'source users: User is postgres.table("users")\n'
)


@pytest.mark.parametrize(
    ("literal", "python_type", "type_name"),
    [
        ('"hello"', str, "Text"),
        ("42", int, "Int"),
        ("1.5", float, "Float"),
        ("true", bool, "Bool"),
    ],
)
def test_literal_expression_maps_to_builtin_type(
    literal: str,
    python_type: type[object],
    type_name: str,
) -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            f"    where {literal}\n"
            "    select:\n"
            "        id\n"
        )
    )
    expression = _table(result).where_clause.expression
    assert isinstance(expression, LiteralExpr)
    assert isinstance(expression.value, python_type)

    value_type = result.model.expression_value_types[expression]

    assert value_type.kind is ValueTypeKind.KNOWN
    assert value_type.resolved_type.kind is TypeKind.BUILTIN
    assert value_type.resolved_type.name == type_name
    assert value_type.nullability is EffectiveNullability.NON_NULL


def test_bare_field_uses_row_field_type_and_nullability() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n    from users\n    select:\n        email\n"
        )
    )
    table = _table(result)
    expression = table.select_items[0].expression
    assert isinstance(expression, NameExpr)
    row_field = result.model.relation_row_schemas[table].fields["email"]

    value_type = result.model.expression_value_types[expression]

    assert value_type.resolved_type is row_field.resolved_type
    assert value_type.nullability is EffectiveNullability.NULLABLE
    assert value_type.kind is ValueTypeKind.KNOWN


def test_unknown_bare_field_reports_pie_s2102_and_records_unknown() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n    from users\n    select:\n        missing\n"
        )
    )
    expression = _table(result).select_items[0].expression

    assert [
        (diagnostic.code, diagnostic.severity) for diagnostic in result.diagnostics
    ] == [("PIE-S2102", Severity.ERROR)]
    assert result.model.expression_value_types[expression].kind is ValueTypeKind.UNKNOWN


def test_unknown_input_schema_suppresses_unknown_field_diagnostic() -> None:
    result = analyze(
        _parse(
            'source raw is postgres.table("raw")\n'
            "table projected:\n"
            "    from raw\n"
            "    select:\n"
            "        missing\n"
        ),
        mode_override=CheckMode.LOOSE,
    )
    expression = _table(result).select_items[0].expression

    assert result.diagnostics == ()
    assert result.model.expression_value_types[expression].kind is ValueTypeKind.UNKNOWN


@pytest.mark.parametrize("operator", ["is null", "is not null"])
def test_is_null_expression_maps_to_non_null_bool(operator: str) -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            f"    where email {operator}\n"
            "    select:\n"
            "        id\n"
        )
    )
    expression = _table(result).where_clause.expression
    assert isinstance(expression, IsNullExpr)

    value_type = result.model.expression_value_types[expression]

    assert value_type.resolved_type.name == "Bool"
    assert value_type.nullability is EffectiveNullability.NON_NULL
    assert value_type.kind is ValueTypeKind.KNOWN


def test_simple_comparison_maps_to_bool_and_types_operands() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    where id >= 1\n"
            "    select:\n"
            "        id\n"
        )
    )
    expression = _table(result).where_clause.expression
    assert isinstance(expression, ComparisonExpr)

    value_type = result.model.expression_value_types[expression]

    assert value_type.resolved_type.name == "Bool"
    assert value_type.kind is ValueTypeKind.KNOWN
    assert result.model.expression_value_types[expression.left].resolved_type.name == (
        "UUID"
    )
    assert result.model.expression_value_types[expression.right].resolved_type.name == (
        "Int"
    )


def test_unknown_call_argument_suppresses_dependent_call_diagnostic() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    where unknown_call(missing) >= 1\n"
            "    select:\n"
            "        id\n"
        )
    )
    expression = _table(result).where_clause.expression
    assert isinstance(expression, ComparisonExpr)
    assert isinstance(expression.left, CallExpr)

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2102"]
    assert (
        result.model.expression_value_types[expression.left].kind
        is ValueTypeKind.UNKNOWN
    )
    assert result.model.expression_value_types[expression].resolved_type.name == "Bool"
    assert (
        result.model.expression_value_types[expression.left.arguments[0]].kind
        is ValueTypeKind.UNKNOWN
    )


def test_deep_binary_expression_returns_semantic_recursion_diagnostic() -> None:
    expression = " + ".join(["1"] * 1200)
    script = _parse(f"derive total() -> Int not null:\n    {expression}\n")

    result = analyze(script)

    assert result.model.mode is CheckMode.CHECKED
    assert result.model.expression_value_types == {}
    assert len(result.diagnostics) == 1
    diagnostic = result.diagnostics[0]
    assert diagnostic.code == "PIE-S2006"
    assert diagnostic.severity is Severity.ERROR
    assert "recursion limit" in diagnostic.message


def test_expression_value_types_mapping_is_readonly() -> None:
    result = analyze(
        _parse(SOURCE + "table projected:\n    from users\n    select:\n        id\n")
    )
    expression = _table(result).select_items[0].expression

    with pytest.raises(TypeError):
        result.model.expression_value_types[expression] = (
            result.model.expression_value_types[  # type: ignore[index]
                expression
            ]
        )


def test_expression_typing_does_not_mutate_input_ast() -> None:
    script = _parse(
        SOURCE + "table projected:\n"
        "    from users\n"
        "    where email is not null\n"
        "    select:\n"
        "        email\n"
    )
    original = deepcopy(script)

    analyze(script)

    assert script == original


def test_expression_semantic_results_do_not_expose_antlr_nodes() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    where email is null\n"
            "    select:\n"
            "        email\n"
        )
    )

    _assert_no_antlr_nodes(result)


def _parse(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _table(result: SemanticResult) -> TableDef:
    definition = result.model.relation_symbols["projected"]
    assert isinstance(definition, TableDef)
    assert definition.where_clause is not None or definition.select_items
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
