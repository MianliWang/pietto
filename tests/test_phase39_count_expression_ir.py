from __future__ import annotations

from collections.abc import Iterable
from typing import cast

import pytest

from pietto.ast_nodes import QueryDef, Script, TableDef
from pietto.errors import Severity
from pietto.ir import (
    AggregateCallIR,
    BetweenIR,
    BinaryIR,
    CallIR,
    ComparisonIR,
    ExpressionIR,
    FieldId,
    FieldRefIR,
    IsNullIR,
    LiteralIR,
    NullabilityIR,
    ProjectionIR,
    RelationIR,
    ScriptIR,
    SymbolId,
    SymbolNamespace,
    UnaryIR,
    build_ir,
)
from pietto.ir.lowering import lower_expr
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.sql.expressions import render_expression_sql
from pietto.sql.mysql_expressions import render_mysql_expression
from pietto.sql.mysql_render import MySqlRenderError

SOURCE_PREFIX = (
    "shape Order:\n"
    "    region: Text not null\n"
    "    status: Text not null\n"
    "    active: Bool not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    score: Float not null\n"
    "    weight: Float not null\n"
    'source orders: Order is postgres.table("orders")\n'
)


def test_no_group_count_expression_arguments_lower_to_aggregate_call_ir() -> None:
    relation = _compile_relation(
        SOURCE_PREFIX + "table order_counts:\n"
        "    from orders\n"
        "    select:\n"
        "        amount_tax = count(amount + tax)\n"
        "        amount_one = count(amount + 1)\n"
        "        positive_amount = count(+amount)\n"
        "        modulo_amount = count(amount % tax)\n"
        "        weighted = count(score * weight)\n"
        "        lowered = count(lower(status))\n"
        "        trimmed = count(trim(status))\n"
        "        length_status = count(len(status))\n"
        "        active_count = count(active and true)\n"
    )
    projections = _projections(relation)

    _assert_binary_count(
        projections["amount_tax"].expression,
        operator="+",
        argument_type="Int",
        left="amount",
        right="tax",
    )
    _assert_binary_count(
        projections["amount_one"].expression,
        operator="+",
        argument_type="Int",
        left="amount",
        right=1,
    )
    positive_amount = _assert_count_aggregate(
        projections["positive_amount"].expression,
    ).arguments[0]
    assert isinstance(positive_amount, UnaryIR)
    assert positive_amount.operator == "+"
    _assert_field(positive_amount.operand, "amount")
    _assert_binary_count(
        projections["modulo_amount"].expression,
        operator="%",
        argument_type="Int",
        left="amount",
        right="tax",
    )
    _assert_binary_count(
        projections["weighted"].expression,
        operator="*",
        argument_type="Float",
        left="score",
        right="weight",
    )
    _assert_call_count(projections["lowered"].expression, "lower", "status")
    _assert_call_count(projections["trimmed"].expression, "trim", "status")
    _assert_call_count(
        projections["length_status"].expression,
        "len",
        "status",
        argument_type="Int",
    )
    _assert_binary_count(
        projections["active_count"].expression,
        operator="and",
        argument_type="Bool",
        left="active",
        right=True,
    )

    assert [
        (field.name, field.type_ref.canonical_name, field.nullability)
        for field in relation.row_schema.fields
    ] == [
        ("amount_tax", "Int", NullabilityIR.NON_NULL),
        ("amount_one", "Int", NullabilityIR.NON_NULL),
        ("positive_amount", "Int", NullabilityIR.NON_NULL),
        ("modulo_amount", "Int", NullabilityIR.NON_NULL),
        ("weighted", "Int", NullabilityIR.NON_NULL),
        ("lowered", "Int", NullabilityIR.NON_NULL),
        ("trimmed", "Int", NullabilityIR.NON_NULL),
        ("length_status", "Int", NullabilityIR.NON_NULL),
        ("active_count", "Int", NullabilityIR.NON_NULL),
    ]


def test_grouped_count_expression_ir_preserves_group_keys_and_projection_shape() -> (
    None
):
    relation = _compile_relation(
        SOURCE_PREFIX + "table order_counts_by_region:\n"
        "    from orders\n"
        "    group by:\n"
        "        region\n"
        "    select:\n"
        "        region\n"
        "        amount_tax = count(amount + tax)\n"
        "        lowered = count(lower(status))\n"
    )
    projections = _projections(relation)

    assert [key.name for key in relation.group_keys] == ["region"]
    assert [key.qualifier for key in relation.group_keys] == [()]
    assert [key.field for key in relation.group_keys] == [
        FieldId(owner=_orders_symbol(), name="region")
    ]
    _assert_field(projections["region"].expression, "region")
    _assert_binary_count(
        projections["amount_tax"].expression,
        operator="+",
        argument_type="Int",
        left="amount",
        right="tax",
    )
    _assert_call_count(projections["lowered"].expression, "lower", "status")


def test_existing_count_star_and_direct_count_field_ir_remain_shape_compatible() -> (
    None
):
    relation = _compile_relation(
        SOURCE_PREFIX + "table order_counts:\n"
        "    from orders\n"
        "    select:\n"
        "        total = count()\n"
        "        known_amounts = count(amount)\n"
        "        qualified_statuses = count(orders.status)\n"
    )
    projections = _projections(relation)

    total = _assert_count_aggregate(projections["total"].expression)
    assert total.arguments == ()

    known_amounts = _assert_count_aggregate(
        projections["known_amounts"].expression,
    )
    assert len(known_amounts.arguments) == 1
    _assert_field(known_amounts.arguments[0], "amount")

    qualified_statuses = _assert_count_aggregate(
        projections["qualified_statuses"].expression,
    )
    assert len(qualified_statuses.arguments) == 1
    _assert_field(qualified_statuses.arguments[0], "orders.status")


def test_direct_lower_expr_for_count_expression_uses_aggregate_call_ir() -> None:
    script = _parse(
        SOURCE_PREFIX + "table order_counts:\n"
        "    from orders\n"
        "    select:\n"
        "        amount_tax = count(amount + tax)\n"
    )
    relation = _relation_ast(script)
    semantic_result = analyze(script)
    input_schema = next(iter(semantic_result.model.source_row_schemas.values()))

    lowered = lower_expr(
        relation.select_items[0].expression,
        semantic_result.model,
        fields=input_schema.fields,
        field_owner=_orders_symbol(),
        field_qualifier="orders",
    )

    assert _error_codes(semantic_result) == []
    assert lowered.diagnostics == ()
    _assert_binary_count(
        cast(ExpressionIR, lowered.expression),
        operator="+",
        argument_type="Int",
        left="amount",
        right="tax",
    )


@pytest.mark.parametrize(
    ("projection", "expected_code"),
    [
        ("value = count(1)", "PIE-S2315"),
        ('value = count("x")', "PIE-S2315"),
        ("value = count(true)", "PIE-S2315"),
        ("value = count(1 + 2)", "PIE-S2315"),
        ("value = count(amount > 1)", "PIE-S2315"),
        ("value = count(amount between 1 and 10)", "PIE-S2315"),
        ("value = count(amount is null)", "PIE-S2315"),
        ('value = count(matches(status, "active"))', "PIE-S2315"),
        ("value = count_distinct(amount + tax)", "PIE-S2315"),
        ("value = min(amount + tax)", "PIE-S2315"),
        ("value = max(amount + tax)", "PIE-S2315"),
        ("value = count(count())", "PIE-S2311"),
        ("value = count(amount) + 1", "PIE-S2310"),
        ("value = count_if(active)", "PIE-S2103"),
    ],
)
def test_deferred_count_expression_shapes_stop_before_meaningful_aggregate_ir(
    projection: str,
    expected_code: str,
) -> None:
    script = _parse(
        SOURCE_PREFIX + "table order_counts:\n"
        "    from orders\n"
        "    select:\n"
        f"        {projection}\n"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == [expected_code]
    if ir_result.ir is not None:
        assert _aggregate_expressions(ir_result.ir) == ()


def test_sql_renderers_still_fail_closed_for_count_expression_ir_until_slice5() -> None:
    relation = _compile_relation(
        SOURCE_PREFIX + "table order_counts:\n"
        "    from orders\n"
        "    select:\n"
        "        amount_tax = count(amount + tax)\n"
    )
    aggregate = _assert_count_aggregate(
        _projections(relation)["amount_tax"].expression,
    )
    assert isinstance(aggregate.arguments[0], BinaryIR)

    with pytest.raises(
        ValueError,
        match="PostgreSQL aggregate count expects a direct field argument",
    ):
        render_expression_sql(aggregate)
    with pytest.raises(
        MySqlRenderError,
        match="MySQL aggregate count expects a direct field argument",
    ):
        render_mysql_expression(aggregate)


def _compile_relation(source: str) -> RelationIR:
    script = _parse(source)
    semantic_result = analyze(script)
    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return _relation_ir(ir_result.ir)


def _parse(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _relation_ast(script: Script) -> TableDef | QueryDef:
    relation = script.definitions[-1]
    assert isinstance(relation, (TableDef, QueryDef))
    return relation


def _relation_ir(script_ir: ScriptIR) -> RelationIR:
    relations = [
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR)
    ]
    assert len(relations) == 1
    return relations[0]


def _projections(relation: RelationIR) -> dict[str, ProjectionIR]:
    return {str(projection.name): projection for projection in relation.projections}


def _assert_count_aggregate(expression: ExpressionIR) -> AggregateCallIR:
    assert isinstance(expression, AggregateCallIR)
    assert not isinstance(expression, CallIR)
    assert expression.function == "count"
    assert expression.value_type.canonical_name == "Int"
    assert expression.value_type.nullability is NullabilityIR.NON_NULL
    return expression


def _assert_binary_count(
    expression: ExpressionIR,
    *,
    operator: str,
    argument_type: str,
    left: str | int | bool,
    right: str | int | bool,
) -> BinaryIR:
    aggregate = _assert_count_aggregate(expression)
    assert len(aggregate.arguments) == 1
    argument = aggregate.arguments[0]
    assert isinstance(argument, BinaryIR)
    assert argument.operator == operator
    assert argument.value_type.canonical_name == argument_type
    _assert_operand(argument.left, left)
    _assert_operand(argument.right, right)
    return argument


def _assert_call_count(
    expression: ExpressionIR,
    callee: str,
    field_name: str,
    *,
    argument_type: str = "Text",
) -> CallIR:
    aggregate = _assert_count_aggregate(expression)
    assert len(aggregate.arguments) == 1
    argument = aggregate.arguments[0]
    assert isinstance(argument, CallIR)
    assert argument.callee == callee
    assert argument.value_type.canonical_name == argument_type
    assert len(argument.arguments) == 1
    _assert_field(argument.arguments[0], field_name)
    return argument


def _assert_operand(
    expression: ExpressionIR,
    expected: str | int | bool,
) -> None:
    if isinstance(expected, str):
        _assert_field(expression, expected)
        return
    assert isinstance(expression, LiteralIR)
    assert expression.value == expected
    if type(expected) is bool:
        assert expression.value_type.canonical_name == "Bool"
    else:
        assert type(expected) is int
        assert expression.value_type.canonical_name == "Int"


def _assert_field(expression: ExpressionIR, expected_name: str) -> None:
    assert isinstance(expression, FieldRefIR)
    parts = expected_name.split(".")
    assert expression.name == parts[-1]
    assert expression.qualifier == tuple(parts[:-1])
    assert expression.field == FieldId(owner=_orders_symbol(), name=parts[-1])


def _orders_symbol() -> SymbolId:
    return SymbolId(SymbolNamespace.RELATION, "orders")


def _aggregate_expressions(script_ir: ScriptIR) -> tuple[AggregateCallIR, ...]:
    aggregates: list[AggregateCallIR] = []
    for definition in script_ir.definitions:
        if not isinstance(definition, RelationIR):
            continue
        for projection in definition.projections:
            aggregates.extend(_walk_aggregates(projection.expression))
    return tuple(aggregates)


def _walk_aggregates(expression: ExpressionIR) -> Iterable[AggregateCallIR]:
    if isinstance(expression, AggregateCallIR):
        yield expression
    for child in _expression_children(expression):
        yield from _walk_aggregates(child)


def _expression_children(expression: ExpressionIR) -> tuple[ExpressionIR, ...]:
    if isinstance(expression, AggregateCallIR):
        return expression.arguments
    if isinstance(expression, CallIR):
        return expression.arguments
    if isinstance(expression, UnaryIR):
        return (expression.operand,)
    if isinstance(expression, BinaryIR):
        return (expression.left, expression.right)
    if isinstance(expression, ComparisonIR):
        return (expression.left, expression.right)
    if isinstance(expression, BetweenIR):
        return (expression.value, expression.lower, expression.upper)
    if isinstance(expression, IsNullIR):
        return (expression.value,)
    return ()


def _error_codes(result: object) -> list[str]:
    diagnostics = getattr(result, "diagnostics")
    return [
        diagnostic.code
        for diagnostic in diagnostics
        if diagnostic.severity is Severity.ERROR
    ]
