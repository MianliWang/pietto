from __future__ import annotations

from collections.abc import Iterable

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
    NullabilityIR,
    RelationIR,
    ScriptIR,
    SymbolId,
    SymbolNamespace,
    UnaryIR,
    build_ir,
)
from pietto.ir.lowering import lower_expr
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, analyze

SOURCE_PREFIX = (
    "shape Order:\n"
    "    status: Text not null\n"
    "    amount: Decimal not null\n"
    'source orders: Order is postgres.table("orders")\n'
)


@pytest.mark.parametrize("relation_kind", ["table", "query"])
def test_no_group_decimal_aggregates_lower_to_existing_aggregate_call_ir(
    relation_kind: str,
) -> None:
    script = _parse(
        SOURCE_PREFIX + f"{relation_kind} decimal_order_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        total_amount = sum(amount)\n"
        "        average_amount = avg(amount)\n"
        "        smallest_amount = min(amount)\n"
        "        largest_amount = max(amount)\n"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    relation = _relation_ir(ir_result.ir)
    projections = {projection.name: projection for projection in relation.projections}

    _assert_aggregate(
        projections["total_amount"].expression,
        "sum",
        ("amount",),
    )
    _assert_aggregate(
        projections["average_amount"].expression,
        "avg",
        ("amount",),
    )
    _assert_aggregate(
        projections["smallest_amount"].expression,
        "min",
        ("amount",),
    )
    _assert_aggregate(
        projections["largest_amount"].expression,
        "max",
        ("amount",),
    )
    assert [
        (field.name, field.type_ref.canonical_name, field.nullability)
        for field in relation.row_schema.fields
    ] == [
        ("total_amount", "Decimal", NullabilityIR.NULLABLE),
        ("average_amount", "Decimal", NullabilityIR.NULLABLE),
        ("smallest_amount", "Decimal", NullabilityIR.NULLABLE),
        ("largest_amount", "Decimal", NullabilityIR.NULLABLE),
    ]


def test_qualified_decimal_aggregates_lower_to_qualified_field_refs() -> None:
    script = _parse(
        SOURCE_PREFIX + "table decimal_order_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        total_amount = sum(orders.amount)\n"
        "        average_amount = avg(orders.amount)\n"
        "        smallest_amount = min(orders.amount)\n"
        "        largest_amount = max(orders.amount)\n"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    relation = _relation_ir(ir_result.ir)
    projections = {projection.name: projection for projection in relation.projections}

    for name, function in (
        ("total_amount", "sum"),
        ("average_amount", "avg"),
        ("smallest_amount", "min"),
        ("largest_amount", "max"),
    ):
        _assert_aggregate(
            projections[name].expression,
            function,
            ("orders.amount",),
        )


def test_grouped_decimal_aggregates_lower_with_group_keys_preserved() -> None:
    script = _parse(
        SOURCE_PREFIX + "table decimal_order_stats_by_status:\n"
        "    from orders\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total_amount = sum(amount)\n"
        "        average_amount = avg(amount)\n"
        "        smallest_amount = min(amount)\n"
        "        largest_amount = max(orders.amount)\n"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    relation = _relation_ir(ir_result.ir)
    projections = {projection.name: projection for projection in relation.projections}

    assert [key.name for key in relation.group_keys] == ["status"]
    assert [key.field for key in relation.group_keys] == [
        FieldId(owner=_orders_symbol(), name="status")
    ]
    for name, function, expected_arguments in (
        ("total_amount", "sum", ("amount",)),
        ("average_amount", "avg", ("amount",)),
        ("smallest_amount", "min", ("amount",)),
        ("largest_amount", "max", ("orders.amount",)),
    ):
        _assert_aggregate(projections[name].expression, function, expected_arguments)


def test_direct_lower_expr_for_decimal_aggregate_uses_aggregate_call_ir() -> None:
    script = _parse(
        SOURCE_PREFIX + "table decimal_order_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        total_amount = sum(amount)\n"
    )
    relation = _relation_ast(script)
    semantic_result = analyze(script)

    lowered = lower_expr(relation.select_items[0].expression, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert lowered.diagnostics == ()
    assert isinstance(lowered.expression, AggregateCallIR)
    assert not isinstance(lowered.expression, CallIR)
    _assert_aggregate(lowered.expression, "sum", ("amount",))


@pytest.mark.parametrize(
    ("select_body", "expected_code"),
    [
        ("        value = sum(amount + amount)\n", "PIE-S2315"),
        ("        value = avg(amount + amount)\n", "PIE-S2315"),
        ("        value = min(amount + amount)\n", "PIE-S2315"),
        ("        value = max(amount + amount)\n", "PIE-S2315"),
        ("        value = sum(avg(amount))\n", "PIE-S2311"),
        ("        value = sum(amount) + 1\n", "PIE-S2310"),
        ("        sum(amount)\n", "PIE-S2313"),
        ("        status\n        value = sum(amount)\n", "PIE-S2312"),
    ],
)
def test_invalid_decimal_aggregate_shapes_do_not_emit_aggregate_call_ir(
    select_body: str,
    expected_code: str,
) -> None:
    script = _parse(
        SOURCE_PREFIX + "table decimal_order_stats:\n"
        "    from orders\n"
        "    select:\n"
        f"{select_body}"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == [expected_code]
    if ir_result.ir is not None:
        assert _aggregate_expressions(ir_result.ir) == ()


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


def _assert_aggregate(
    expression: ExpressionIR,
    function: str,
    expected_arguments: tuple[str, ...],
) -> None:
    assert isinstance(expression, AggregateCallIR)
    assert not isinstance(expression, CallIR)
    assert expression.function == function
    assert expression.value_type.canonical_name == "Decimal"
    assert expression.value_type.nullability is NullabilityIR.NULLABLE
    assert tuple(_field_name(argument) for argument in expression.arguments) == (
        expected_arguments
    )


def _field_name(expression: ExpressionIR) -> str:
    assert isinstance(expression, FieldRefIR)
    assert expression.value_type.canonical_name == "Decimal"
    return ".".join((*expression.qualifier, expression.name))


def _aggregate_expressions(script_ir: ScriptIR) -> tuple[AggregateCallIR, ...]:
    aggregates: list[AggregateCallIR] = []
    for definition in script_ir.definitions:
        if not isinstance(definition, RelationIR):
            continue
        if definition.filter is not None:
            aggregates.extend(_walk_aggregates(definition.filter.expression))
        for projection in definition.projections:
            aggregates.extend(_walk_aggregates(projection.expression))
        for order_item in definition.order_by:
            aggregates.extend(_walk_aggregates(order_item.expression))
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


def _orders_symbol() -> SymbolId:
    return SymbolId(SymbolNamespace.RELATION, "orders")


def _error_codes(result: SemanticResult) -> list[str]:
    return [
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]
