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
    FieldRefIR,
    IsNullIR,
    NullabilityIR,
    RelationIR,
    ScriptIR,
    UnaryIR,
    build_ir,
)
from pietto.ir.lowering import lower_expr
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, analyze
from pietto.semantic.catalog import BUILTIN_FUNCTIONS

SOURCE_PREFIX = (
    "shape Order:\n"
    "    status: Text not null\n"
    "    amount: Int not null\n"
    "    score: Float not null\n"
    "    price: Decimal not null\n"
    'source orders: Order is postgres.table("orders")\n'
)


@pytest.mark.parametrize("relation_kind", ["table", "query"])
def test_valid_sum_avg_projections_lower_to_aggregate_call_ir(
    relation_kind: str,
) -> None:
    script = _parse_sum_avg_program(relation_kind)
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    relation_ir = _relation_ir(ir_result.ir)
    projections = {
        projection.name: projection for projection in relation_ir.projections
    }

    total = projections["total"].expression
    revenue = projections["revenue"].expression
    score_total = projections["score_total"].expression
    average_amount = projections["average_amount"].expression
    average_score = projections["average_score"].expression

    _assert_aggregate(total, "count", "Int", NullabilityIR.NON_NULL, ())
    _assert_aggregate(revenue, "sum", "Int", NullabilityIR.NULLABLE, ("amount",))
    _assert_aggregate(
        score_total,
        "sum",
        "Float",
        NullabilityIR.NULLABLE,
        ("score",),
    )
    _assert_aggregate(
        average_amount,
        "avg",
        "Float",
        NullabilityIR.NULLABLE,
        ("amount",),
    )
    _assert_aggregate(
        average_score,
        "avg",
        "Float",
        NullabilityIR.NULLABLE,
        ("score",),
    )
    assert projections["revenue"].type_ref is not None
    assert projections["revenue"].type_ref.canonical_name == "Int"
    assert projections["revenue"].type_ref.nullability is NullabilityIR.NULLABLE
    assert relation_ir.row_schema.fields[1].name == "revenue"
    assert relation_ir.row_schema.fields[1].type_ref.canonical_name == "Int"
    assert relation_ir.row_schema.fields[1].nullability is NullabilityIR.NULLABLE


def test_qualified_sum_avg_arguments_lower_to_qualified_field_refs() -> None:
    script = _parse(
        SOURCE_PREFIX + "table paid_order_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        revenue = sum(orders.amount)\n"
        "        average = avg(orders.score)\n"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    relation_ir = _relation_ir(ir_result.ir)
    revenue = relation_ir.projections[0].expression
    average = relation_ir.projections[1].expression

    _assert_aggregate(
        revenue,
        "sum",
        "Int",
        NullabilityIR.NULLABLE,
        ("orders.amount",),
    )
    _assert_aggregate(
        average,
        "avg",
        "Float",
        NullabilityIR.NULLABLE,
        ("orders.score",),
    )


def test_direct_lower_expr_for_valid_sum_avg_no_longer_uses_generic_call_ir() -> None:
    script = _parse_sum_avg_program("table")
    relation = _relation_ast(script)
    semantic_result = analyze(script)

    lowered_sum = lower_expr(relation.select_items[1].expression, semantic_result.model)
    lowered_avg = lower_expr(relation.select_items[3].expression, semantic_result.model)

    assert lowered_sum.diagnostics == ()
    assert isinstance(lowered_sum.expression, AggregateCallIR)
    assert not isinstance(lowered_sum.expression, CallIR)
    assert lowered_sum.expression.function == "sum"
    assert len(lowered_sum.expression.arguments) == 1
    assert lowered_avg.diagnostics == ()
    assert isinstance(lowered_avg.expression, AggregateCallIR)
    assert not isinstance(lowered_avg.expression, CallIR)
    assert lowered_avg.expression.function == "avg"
    assert len(lowered_avg.expression.arguments) == 1


@pytest.mark.parametrize(
    ("source", "expected_code"),
    [
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        revenue = sum(status)\n",
            "PIE-S2314",
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        revenue = sum(amount + amount)\n",
            "PIE-S2315",
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        revenue = sum(avg(amount))\n",
            "PIE-S2311",
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        revenue = sum(amount) + 1\n",
            "PIE-S2310",
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        status\n"
            "        revenue = sum(amount)\n",
            "PIE-S2312",
        ),
    ],
)
def test_invalid_sum_avg_shapes_do_not_emit_aggregate_call_ir(
    source: str,
    expected_code: str,
) -> None:
    script = _parse(source)
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == [expected_code]
    if ir_result.ir is not None:
        assert _aggregate_expressions(ir_result.ir) == ()


def test_count_sum_and_avg_remain_absent_from_scalar_builtins() -> None:
    assert "count" not in BUILTIN_FUNCTIONS
    assert "sum" not in BUILTIN_FUNCTIONS
    assert "avg" not in BUILTIN_FUNCTIONS


def _parse_sum_avg_program(relation_kind: str) -> Script:
    return _parse(
        SOURCE_PREFIX + f"{relation_kind} paid_order_stats:\n"
        "    from orders\n"
        '    where status == "paid"\n'
        "    select:\n"
        "        total = count()\n"
        "        revenue = sum(amount)\n"
        "        score_total = sum(score)\n"
        "        average_amount = avg(amount)\n"
        "        average_score = avg(score)\n"
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


def _field_name(expression: ExpressionIR) -> str:
    assert isinstance(expression, FieldRefIR)
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


def _error_codes(result: SemanticResult) -> list[str]:
    return [
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]
