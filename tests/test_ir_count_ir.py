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
    'source orders: Order is postgres.table("orders")\n'
)


@pytest.mark.parametrize("relation_kind", ["table", "query"])
def test_valid_count_projection_lowers_to_aggregate_call_ir(
    relation_kind: str,
) -> None:
    script = _parse_count_program(relation_kind)
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    relation_ir = _relation_ir(ir_result.ir)
    projection = relation_ir.projections[0]
    expression = projection.expression
    row_field = relation_ir.row_schema.fields[0]

    assert isinstance(expression, AggregateCallIR)
    assert not isinstance(expression, CallIR)
    assert expression.function == "count"
    assert expression.arguments == ()
    assert expression.value_type.canonical_name == "Int"
    assert expression.value_type.nullability is NullabilityIR.NON_NULL
    assert projection.name == "total"
    assert projection.type_ref is not None
    assert projection.type_ref.canonical_name == "Int"
    assert projection.type_ref.nullability is NullabilityIR.NON_NULL
    assert row_field.name == "total"
    assert row_field.type_ref.canonical_name == "Int"
    assert row_field.nullability is NullabilityIR.NON_NULL


def test_direct_lower_expr_for_valid_count_no_longer_uses_generic_call_ir() -> None:
    script = _parse_count_program("table")
    relation = _relation_ast(script)
    semantic_result = analyze(script)
    expression = relation.select_items[0].expression

    lowered = lower_expr(expression, semantic_result.model)

    assert lowered.diagnostics == ()
    assert isinstance(lowered.expression, AggregateCallIR)
    assert not isinstance(lowered.expression, CallIR)
    assert lowered.expression.function == "count"
    assert lowered.expression.arguments == ()


@pytest.mark.parametrize(
    ("source", "expected_code"),
    [
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        total = count(amount, status)\n",
            "PIE-S2309",
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    where count() > 0\n"
            "    select:\n"
            "        status\n",
            "PIE-S2308",
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        total = count() + 1\n",
            "PIE-S2310",
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        total = count(count())\n",
            "PIE-S2311",
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        total = count(lower(count()))\n",
            "PIE-S2311",
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        total = lower(count())\n",
            "PIE-S2310",
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n",
            "PIE-S2312",
        ),
    ],
)
def test_invalid_count_shapes_do_not_emit_aggregate_call_ir(
    source: str,
    expected_code: str,
) -> None:
    script = _parse(source)
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == [expected_code]
    if ir_result.ir is not None:
        assert _aggregate_expressions(ir_result.ir) == ()


@pytest.mark.parametrize(
    ("projection", "function"),
    [
        ("revenue = sum(amount)", "sum"),
        ("average = avg(amount)", "avg"),
    ],
)
def test_sum_and_avg_lower_to_aggregate_ir_after_count_mvp(
    projection: str,
    function: str,
) -> None:
    script = _parse(
        SOURCE_PREFIX + "table paid_order_stats:\n"
        "    from orders\n"
        "    select:\n"
        f"        {projection}\n"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    aggregates = _aggregate_expressions(ir_result.ir)
    assert len(aggregates) == 1
    assert aggregates[0].function == function
    assert len(aggregates[0].arguments) == 1


def test_count_sum_and_avg_are_still_absent_from_scalar_builtins() -> None:
    assert "count" not in BUILTIN_FUNCTIONS
    assert "sum" not in BUILTIN_FUNCTIONS
    assert "avg" not in BUILTIN_FUNCTIONS


def _parse_count_program(relation_kind: str) -> Script:
    return _parse(
        SOURCE_PREFIX + f"{relation_kind} paid_order_stats:\n"
        "    from orders\n"
        '    where status == "paid"\n'
        "    select:\n"
        "        total = count()\n"
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
