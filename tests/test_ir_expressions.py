from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from typing import Callable

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import (
    CallExpr,
    Expression,
    Script,
    SourceDef,
    TableDef,
)
from pietto.errors import Severity
from pietto.ir import (
    BetweenIR,
    BinaryIR,
    CallIR,
    ComparisonIR,
    ExpressionIR,
    ExpressionLoweringResult,
    FieldId,
    FieldRefIR,
    IsNullIR,
    LiteralIR,
    NullabilityIR,
    SymbolId,
    SymbolNamespace,
    TypeKindIR,
    UnaryIR,
)
from pietto.ir.lowering import lower_expr
from pietto.parser_api import parse_source
from pietto.semantic import CheckMode, RowField, RowSchema, SemanticModel, analyze

SOURCE = (
    "shape User:\n"
    "    email: Text nullable\n"
    "    count: Int not null\n"
    'source users: User is postgres.table("public.users")\n'
)


@pytest.mark.parametrize(
    ("literal", "expected_value", "expected_type"),
    [
        ('"hello"', "hello", "Text"),
        ("42", 42, "Int"),
        ("1.5", 1.5, "Float"),
        ("true", True, "Bool"),
    ],
)
def test_literals_lower_with_canonical_value_types(
    literal: str,
    expected_value: object,
    expected_type: str,
) -> None:
    expression, model, _ = _table_expression(
        SOURCE + "table projected:\n"
        "    from users\n"
        "    select:\n"
        f"        value = {literal}\n"
    )

    result = lower_expr(expression, model)

    assert result.diagnostics == ()
    assert isinstance(result.expression, LiteralIR)
    assert result.expression.value == expected_value
    assert result.expression.value_type.canonical_name == expected_type
    assert result.expression.value_type.canonical_kind is TypeKindIR.BUILTIN
    assert result.expression.value_type.nullability is NullabilityIR.NON_NULL


def test_bare_field_lowers_with_stable_identity_and_alias_canonical_type() -> None:
    expression, model, table = _table_expression(
        "type Email = Text not null\n"
        "shape User:\n"
        "    email: Email nullable\n"
        'source users: User is postgres.table("public.users")\n'
        "table projected:\n"
        "    from users\n"
        "    select:\n"
        "        email\n"
    )
    fields, owner = _input_fields(model, table)

    result = lower_expr(
        expression,
        model,
        fields=fields,
        field_owner=owner,
    )

    assert isinstance(result.expression, FieldRefIR)
    assert result.expression.name == "email"
    assert result.expression.qualifier == ()
    assert result.expression.field == FieldId(owner=owner, name="email")
    assert result.expression.value_type.symbol == SymbolId(
        SymbolNamespace.TYPE,
        "Email",
    )
    assert result.expression.value_type.canonical_symbol == SymbolId(
        SymbolNamespace.TYPE,
        "Text",
    )
    assert result.expression.value_type.nullability is NullabilityIR.NULLABLE


def test_builtin_call_lowers_with_callable_symbol() -> None:
    expression, model, table = _table_expression(
        SOURCE + "table projected:\n"
        "    from users\n"
        "    select:\n"
        "        value = lower(email)\n"
    )
    fields, owner = _input_fields(model, table)

    result = lower_expr(expression, model, fields=fields, field_owner=owner)

    assert isinstance(result.expression, CallIR)
    assert result.expression.callee == "lower"
    assert result.expression.callee_symbol == SymbolId(
        SymbolNamespace.CALLABLE,
        "lower",
    )
    assert result.expression.value_type.canonical_name == "Text"
    argument = result.expression.arguments[0]
    assert isinstance(argument, FieldRefIR)
    assert argument.field == FieldId(owner=owner, name="email")


def test_nested_call_lowers_recursively() -> None:
    expression, model, table = _table_expression(
        SOURCE + "table projected:\n"
        "    from users\n"
        "    select:\n"
        "        value = lower(trim(email))\n"
    )
    fields, owner = _input_fields(model, table)

    result = lower_expr(expression, model, fields=fields, field_owner=owner)

    assert isinstance(result.expression, CallIR)
    inner = result.expression.arguments[0]
    assert isinstance(inner, CallIR)
    assert inner.callee == "trim"
    assert inner.value_type.canonical_name == "Text"
    assert isinstance(inner.arguments[0], FieldRefIR)


def test_matches_call_lowers_as_bool_expression() -> None:
    expression, model, table = _where_expression(
        SOURCE + "table projected:\n"
        "    from users\n"
        '    where matches(email, ".+@.+")\n'
        "    select:\n"
        "        email\n"
    )
    fields, owner = _input_fields(model, table)

    result = lower_expr(expression, model, fields=fields, field_owner=owner)

    assert isinstance(result.expression, CallIR)
    assert result.expression.callee == "matches"
    assert result.expression.value_type.canonical_name == "Bool"
    assert len(result.expression.arguments) == 2


def test_comparison_lowers_recursively() -> None:
    expression, model, table = _where_expression(
        SOURCE + "table projected:\n"
        "    from users\n"
        "    where count >= 1\n"
        "    select:\n"
        "        email\n"
    )
    fields, owner = _input_fields(model, table)

    result = lower_expr(expression, model, fields=fields, field_owner=owner)

    assert isinstance(result.expression, ComparisonIR)
    assert result.expression.operator == ">="
    assert isinstance(result.expression.left, FieldRefIR)
    assert isinstance(result.expression.right, LiteralIR)
    assert result.expression.value_type.canonical_name == "Bool"


@pytest.mark.parametrize(
    ("operator", "negated"),
    [("is null", False), ("is not null", True)],
)
def test_is_null_forms_lower_with_negation(
    operator: str,
    negated: bool,
) -> None:
    expression, model, table = _where_expression(
        SOURCE + "table projected:\n"
        "    from users\n"
        f"    where email {operator}\n"
        "    select:\n"
        "        email\n"
    )
    fields, owner = _input_fields(model, table)

    result = lower_expr(expression, model, fields=fields, field_owner=owner)

    assert isinstance(result.expression, IsNullIR)
    assert result.expression.negated is negated
    assert result.expression.value_type.canonical_name == "Bool"
    assert result.expression.value_type.nullability is NullabilityIR.NON_NULL


def test_current_opaque_expression_forms_lower_with_unknown_types() -> None:
    script, model = _analyzed(
        SOURCE + "table projected:\n"
        "    from users\n"
        "    where count between 1 and 5\n"
        "    select:\n"
        "        unary_value = -1\n"
        "        binary_value = 1 + 2\n"
    )
    table = _table(script)
    fields, owner = _input_fields(model, table)
    expressions = (
        table.select_items[0].expression,
        table.select_items[1].expression,
        table.where_clause.expression,
    )

    lowered = tuple(
        lower_expr(expression, model, fields=fields, field_owner=owner).expression
        for expression in expressions
    )

    assert isinstance(lowered[0], UnaryIR)
    assert isinstance(lowered[1], BinaryIR)
    assert isinstance(lowered[2], BetweenIR)
    assert all(
        expression is not None and expression.value_type.kind is TypeKindIR.UNKNOWN
        for expression in lowered
    )


def test_unknown_expression_value_type_lowers_without_crashing() -> None:
    expression, model, _ = _table_expression(
        'source raw is postgres.table("raw")\n'
        "table projected:\n"
        "    from raw\n"
        "    select:\n"
        "        missing\n",
        mode=CheckMode.LOOSE,
    )

    result = lower_expr(expression, model)

    assert result.diagnostics == ()
    assert isinstance(result.expression, FieldRefIR)
    assert result.expression.field is None
    assert result.expression.value_type.kind is TypeKindIR.UNKNOWN
    assert result.expression.value_type.nullability is NullabilityIR.UNKNOWN


def test_static_postgres_connector_call_lowers_without_execution() -> None:
    script, model = _analyzed('source users is postgres.table("public.users")\n')
    source = next(
        definition
        for definition in script.definitions
        if isinstance(definition, SourceDef)
    )
    assert isinstance(source.connector, CallExpr)

    result = lower_expr(source.connector, model)

    assert result.diagnostics == ()
    assert isinstance(result.expression, CallIR)
    assert result.expression.callee == "postgres.table"
    assert result.expression.callee_symbol is None
    assert result.expression.value_type.kind is TypeKindIR.UNKNOWN
    assert isinstance(result.expression.arguments[0], LiteralIR)


def test_missing_expression_value_type_returns_pie_i1000() -> None:
    expression, model, _ = _table_expression(
        SOURCE + "table projected:\n    from users\n    select:\n        email\n"
    )
    incomplete_model = replace(model, expression_value_types={})

    result = lower_expr(expression, incomplete_model)

    assert result.expression is None
    assert [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in result.diagnostics
    ] == [
        (
            "PIE-I1000",
            Severity.ERROR,
            "Missing semantic fact required for IR lowering: expression value type",
        )
    ]


def test_expression_ir_models_and_result_are_frozen() -> None:
    expression, model, _ = _table_expression(
        SOURCE + "table projected:\n    from users\n    select:\n        email\n"
    )
    result = lower_expr(expression, model)
    assert isinstance(result, ExpressionLoweringResult)
    assert isinstance(result.expression, ExpressionIR)

    with pytest.raises(FrozenInstanceError):
        result.diagnostics = ()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.expression.span = result.expression.span  # type: ignore[misc]


def test_expression_ir_exposes_neither_parser_ast_nor_antlr_objects() -> None:
    expression, model, table = _table_expression(
        SOURCE + "table projected:\n"
        "    from users\n"
        "    select:\n"
        "        value = lower(trim(email))\n"
    )
    fields, owner = _input_fields(model, table)

    result = lower_expr(expression, model, fields=fields, field_owner=owner)

    _assert_no_parser_or_antlr_objects(result)


def test_expression_lowering_does_not_mutate_inputs() -> None:
    expression, model, table = _table_expression(
        SOURCE + "table projected:\n"
        "    from users\n"
        "    select:\n"
        "        value = lower(email)\n"
    )
    fields, owner = _input_fields(model, table)
    original_expression = deepcopy(expression)
    original_model = _semantic_snapshot(model)

    lower_expr(expression, model, fields=fields, field_owner=owner)

    assert expression == original_expression
    assert _semantic_snapshot(model) == original_model


def _table_expression(
    source: str,
    *,
    mode: CheckMode | None = None,
) -> tuple[Expression, SemanticModel, TableDef]:
    script, model = _analyzed(source, mode=mode)
    table = _table(script)
    return table.select_items[0].expression, model, table


def _where_expression(source: str) -> tuple[Expression, SemanticModel, TableDef]:
    script, model = _analyzed(source)
    table = _table(script)
    assert table.where_clause is not None
    return table.where_clause.expression, model, table


def _analyzed(
    source: str,
    *,
    mode: CheckMode | None = None,
) -> tuple[Script, SemanticModel]:
    parse_result = parse_source(source)
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast, mode_override=mode)
    assert all(
        diagnostic.severity is not Severity.ERROR
        for diagnostic in semantic_result.diagnostics
    )
    return parse_result.ast, semantic_result.model


def _table(script: Script) -> TableDef:
    return next(
        definition
        for definition in script.definitions
        if isinstance(definition, TableDef)
    )


def _input_fields(
    model: SemanticModel,
    table: TableDef,
) -> tuple[Mapping[str, RowField], SymbolId]:
    target = model.from_resolutions[table.from_clause]
    assert isinstance(target, SourceDef)
    schema: RowSchema = model.source_row_schemas[target]
    return schema.fields, SymbolId(SymbolNamespace.RELATION, target.name)


def _semantic_snapshot(model: SemanticModel) -> tuple[tuple[str, object], ...]:
    snapshot: list[tuple[str, object]] = []
    for field in fields(model):
        value = getattr(model, field.name)
        if isinstance(value, Mapping):
            value = tuple(value.items())
        snapshot.append((field.name, value))
    return tuple(snapshot)


def _assert_no_parser_or_antlr_objects(value: object) -> None:
    assert not isinstance(value, ParserRuleContext)
    assert not isinstance(value, Token)
    assert not type(value).__module__.startswith("pietto.generated")
    assert not type(value).__module__.startswith("pietto.ast_nodes")
    _walk_public_values(value, _assert_no_parser_or_antlr_objects)


def _walk_public_values(
    value: object,
    assertion: Callable[[object], None],
) -> None:
    if is_dataclass(value):
        for field in fields(value):
            assertion(getattr(value, field.name))
    elif isinstance(value, Mapping):
        for key, item in value.items():
            assertion(key)
            assertion(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            assertion(item)
