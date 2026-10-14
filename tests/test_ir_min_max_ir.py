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
    "    amount: Int not null\n"
    "    score: Float not null\n"
    "    price: Decimal not null\n"
    "    order_date: Date nullable\n"
    "    created_at: Timestamp not null\n"
    'source orders: Order is postgres.table("orders")\n'
)


@pytest.mark.parametrize("relation_kind", ["table", "query"])
def test_no_group_min_max_projections_lower_to_aggregate_call_ir(
    relation_kind: str,
) -> None:
    script = _parse(
        SOURCE_PREFIX + f"{relation_kind} order_extremes:\n"
        "    from orders\n"
        "    select:\n"
        "        smallest_amount = min(amount)\n"
        "        latest_created_at = max(created_at)\n"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    relation = _relation_ir(ir_result.ir)
    projections = {projection.name: projection for projection in relation.projections}

    _assert_aggregate(
        projections["smallest_amount"].expression,
        "min",
        "Int",
        NullabilityIR.NULLABLE,
        ("amount",),
    )
    _assert_aggregate(
        projections["latest_created_at"].expression,
        "max",
        "Timestamp",
        NullabilityIR.NULLABLE,
        ("created_at",),
    )
    assert projections["smallest_amount"].type_ref is not None
    assert projections["smallest_amount"].type_ref.canonical_name == "Int"
    assert projections["smallest_amount"].type_ref.nullability is (
        NullabilityIR.NULLABLE
    )
    assert [
        (field.name, field.type_ref.canonical_name, field.nullability)
        for field in relation.row_schema.fields
    ] == [
        ("smallest_amount", "Int", NullabilityIR.NULLABLE),
        ("latest_created_at", "Timestamp", NullabilityIR.NULLABLE),
    ]


def test_qualified_min_max_arguments_lower_to_qualified_field_refs() -> None:
    script = _parse(
        SOURCE_PREFIX + "table order_extremes:\n"
        "    from orders\n"
        "    select:\n"
        "        first_order_date = min(orders.order_date)\n"
        "        highest_score = max(orders.score)\n"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    relation = _relation_ir(ir_result.ir)
    projections = {projection.name: projection for projection in relation.projections}

    _assert_aggregate(
        projections["first_order_date"].expression,
        "min",
        "Date",
        NullabilityIR.NULLABLE,
        ("orders.order_date",),
    )
    _assert_aggregate(
        projections["highest_score"].expression,
        "max",
        "Float",
        NullabilityIR.NULLABLE,
        ("orders.score",),
    )


def test_grouped_min_max_projections_lower_to_aggregate_call_ir() -> None:
    script = _parse(
        SOURCE_PREFIX + "table grouped_order_extremes:\n"
        "    from orders\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        smallest_amount = min(amount)\n"
        "        latest_created_at = max(created_at)\n"
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
    _assert_aggregate(
        projections["smallest_amount"].expression,
        "min",
        "Int",
        NullabilityIR.NULLABLE,
        ("amount",),
    )
    _assert_aggregate(
        projections["latest_created_at"].expression,
        "max",
        "Timestamp",
        NullabilityIR.NULLABLE,
        ("created_at",),
    )


def test_direct_lower_expr_for_valid_min_max_uses_aggregate_call_ir() -> None:
    script = _parse(
        SOURCE_PREFIX + "table order_extremes:\n"
        "    from orders\n"
        "    select:\n"
        "        smallest_amount = min(amount)\n"
        "        latest_created_at = max(created_at)\n"
    )
    relation = _relation_ast(script)
    semantic_result = analyze(script)

    lowered_min = lower_expr(relation.select_items[0].expression, semantic_result.model)
    lowered_max = lower_expr(relation.select_items[1].expression, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert lowered_min.diagnostics == ()
    assert isinstance(lowered_min.expression, AggregateCallIR)
    assert not isinstance(lowered_min.expression, CallIR)
    assert lowered_min.expression.function == "min"
    assert lowered_min.expression.value_type.canonical_name == "Int"
    assert lowered_min.expression.value_type.nullability is NullabilityIR.NULLABLE
    assert lowered_max.diagnostics == ()
    assert isinstance(lowered_max.expression, AggregateCallIR)
    assert not isinstance(lowered_max.expression, CallIR)
    assert lowered_max.expression.function == "max"
    assert lowered_max.expression.value_type.canonical_name == "Timestamp"
    assert lowered_max.expression.value_type.nullability is NullabilityIR.NULLABLE


@pytest.mark.parametrize(
    ("select_body", "expected_code"),
    [
        ("        value = min()\n", "PIE-S2309"),
        ("        value = max(amount, score)\n", "PIE-S2309"),
        ("        value = min(amount + amount)\n", "PIE-S2315"),
        (
            "        subtotal = amount + amount\n        value = min(subtotal)\n",
            "PIE-S2102",
        ),
        ("        value = min(max(amount))\n", "PIE-S2311"),
        ("        value = min(status)\n", "PIE-S2314"),
        ("        min(amount)\n", "PIE-S2313"),
        ("        value = min(amount) + 1\n", "PIE-S2310"),
        ("        value = lower(min(amount))\n", "PIE-S2310"),
    ],
)
def test_invalid_min_max_projection_shapes_do_not_emit_aggregate_call_ir(
    select_body: str,
    expected_code: str,
) -> None:
    script = _parse(
        SOURCE_PREFIX + "table order_extremes:\n"
        "    from orders\n"
        "    select:\n"
        f"{select_body}"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == [expected_code]
    if ir_result.ir is not None:
        assert _aggregate_expressions(ir_result.ir) == ()


def test_min_max_in_where_context_does_not_emit_aggregate_call_ir() -> None:
    script = _parse(
        SOURCE_PREFIX + "table order_extremes:\n"
        "    from orders\n"
        "    where min(amount) > 0\n"
        "    select:\n"
        "        amount\n"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == ["PIE-S2308"]
    if ir_result.ir is not None:
        assert _aggregate_expressions(ir_result.ir) == ()


def test_count_sum_avg_ir_behavior_remains_unchanged() -> None:
    script = _parse(
        SOURCE_PREFIX + "table order_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        total = count()\n"
        "        amount_total = sum(amount)\n"
        "        average_score = avg(score)\n"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    relation = _relation_ir(ir_result.ir)
    projections = {projection.name: projection for projection in relation.projections}

    _assert_aggregate(
        projections["total"].expression,
        "count",
        "Int",
        NullabilityIR.NON_NULL,
        (),
    )
    _assert_aggregate(
        projections["amount_total"].expression,
        "sum",
        "Int",
        NullabilityIR.NULLABLE,
        ("amount",),
    )
    _assert_aggregate(
        projections["average_score"].expression,
        "avg",
        "Float",
        NullabilityIR.NULLABLE,
        ("score",),
    )


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
    expected_type: str,
    expected_nullability: NullabilityIR,
    expected_arguments: tuple[str, ...],
) -> None:
    assert isinstance(expression, AggregateCallIR)
    assert not isinstance(expression, CallIR)
    assert expression.function == function
    assert expression.value_type.canonical_name == expected_type
    assert expression.value_type.nullability is expected_nullability
    assert tuple(_field_name(argument) for argument in expression.arguments) == (
        expected_arguments
    )
    for argument, expected in zip(
        expression.arguments,
        expected_arguments,
        strict=True,
    ):
        _assert_field_identity(argument, expected)


def _field_name(expression: ExpressionIR) -> str:
    assert isinstance(expression, FieldRefIR)
    return ".".join((*expression.qualifier, expression.name))


def _assert_field_identity(expression: ExpressionIR, expected_name: str) -> None:
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


def _error_codes(result: SemanticResult) -> list[str]:
    return [
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]
