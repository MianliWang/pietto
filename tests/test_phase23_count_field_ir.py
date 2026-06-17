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
    "    created_at: Timestamp not null\n"
    "    anything: Any nullable\n"
    'source orders: Order is postgres.table("orders")\n'
)


@pytest.mark.parametrize("relation_kind", ["table", "query"])
def test_count_star_still_lowers_to_zero_arg_aggregate_ir(
    relation_kind: str,
) -> None:
    script = _parse(
        SOURCE_PREFIX + f"{relation_kind} order_counts:\n"
        "    from orders\n"
        "    select:\n"
        "        total = count()\n"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    relation = _relation_ir(ir_result.ir)
    projection = relation.projections[0]

    _assert_aggregate(
        projection.expression,
        "count",
        "Int",
        NullabilityIR.NON_NULL,
        (),
    )
    assert projection.type_ref is not None
    assert projection.type_ref.canonical_name == "Int"
    assert projection.type_ref.nullability is NullabilityIR.NON_NULL
    assert [
        (field.name, field.type_ref.canonical_name, field.nullability)
        for field in relation.row_schema.fields
    ] == [("total", "Int", NullabilityIR.NON_NULL)]


@pytest.mark.parametrize("relation_kind", ["table", "query"])
def test_no_group_count_field_lowers_to_one_arg_aggregate_ir(
    relation_kind: str,
) -> None:
    script = _parse(
        SOURCE_PREFIX + f"{relation_kind} order_completeness:\n"
        "    from orders\n"
        "    select:\n"
        "        known_amounts = count(amount)\n"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    relation = _relation_ir(ir_result.ir)
    projection = relation.projections[0]

    _assert_aggregate(
        projection.expression,
        "count",
        "Int",
        NullabilityIR.NON_NULL,
        ("amount",),
    )
    assert projection.type_ref is not None
    assert projection.type_ref.canonical_name == "Int"
    assert projection.type_ref.nullability is NullabilityIR.NON_NULL
    assert [
        (field.name, field.type_ref.canonical_name, field.nullability)
        for field in relation.row_schema.fields
    ] == [("known_amounts", "Int", NullabilityIR.NON_NULL)]


def test_no_group_qualified_count_field_lowers_to_qualified_field_ref() -> None:
    script = _parse(
        SOURCE_PREFIX + "table order_completeness:\n"
        "    from orders\n"
        "    select:\n"
        "        known_scores = count(orders.score)\n"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    relation = _relation_ir(ir_result.ir)
    projection = relation.projections[0]

    _assert_aggregate(
        projection.expression,
        "count",
        "Int",
        NullabilityIR.NON_NULL,
        ("orders.score",),
    )
    assert projection.type_ref is not None
    assert projection.type_ref.canonical_name == "Int"
    assert projection.type_ref.nullability is NullabilityIR.NON_NULL


def test_grouped_count_field_lowers_with_group_keys_preserved() -> None:
    script = _parse(
        SOURCE_PREFIX + "table completeness_by_status:\n"
        "    from orders\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        known_amounts = count(amount)\n"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    relation = _relation_ir(ir_result.ir)
    projections = {projection.name: projection for projection in relation.projections}

    assert [key.name for key in relation.group_keys] == ["status"]
    assert [key.qualifier for key in relation.group_keys] == [()]
    assert [key.field for key in relation.group_keys] == [
        FieldId(owner=_orders_symbol(), name="status")
    ]
    _assert_aggregate(
        projections["known_amounts"].expression,
        "count",
        "Int",
        NullabilityIR.NON_NULL,
        ("amount",),
    )
    assert [
        (field.name, field.type_ref.canonical_name, field.nullability)
        for field in relation.row_schema.fields
    ] == [
        ("status", "Text", NullabilityIR.NON_NULL),
        ("known_amounts", "Int", NullabilityIR.NON_NULL),
    ]


def test_grouped_qualified_count_field_lowers_with_group_keys_preserved() -> None:
    script = _parse(
        SOURCE_PREFIX + "table completeness_by_status:\n"
        "    from orders\n"
        "    group by:\n"
        "        orders.status\n"
        "    select:\n"
        "        orders.status\n"
        "        known_scores = count(orders.score)\n"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    relation = _relation_ir(ir_result.ir)
    projections = {projection.name: projection for projection in relation.projections}

    assert [key.name for key in relation.group_keys] == ["status"]
    assert [key.qualifier for key in relation.group_keys] == [("orders",)]
    assert [key.field for key in relation.group_keys] == [
        FieldId(owner=_orders_symbol(), name="status")
    ]
    _assert_aggregate(
        projections["known_scores"].expression,
        "count",
        "Int",
        NullabilityIR.NON_NULL,
        ("orders.score",),
    )
    assert [
        (field.name, field.type_ref.canonical_name, field.nullability)
        for field in relation.row_schema.fields
    ] == [
        ("status", "Text", NullabilityIR.NON_NULL),
        ("known_scores", "Int", NullabilityIR.NON_NULL),
    ]


def test_direct_lower_expr_for_valid_count_field_uses_aggregate_call_ir() -> None:
    script = _parse(
        SOURCE_PREFIX + "table order_completeness:\n"
        "    from orders\n"
        "    select:\n"
        "        known_amounts = count(amount)\n"
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
    assert isinstance(lowered.expression, AggregateCallIR)
    assert not isinstance(lowered.expression, CallIR)
    _assert_aggregate(
        lowered.expression,
        "count",
        "Int",
        NullabilityIR.NON_NULL,
        ("amount",),
    )


@pytest.mark.parametrize(
    ("source", "expected_code"),
    [
        (
            SOURCE_PREFIX + "table order_completeness:\n"
            "    from orders\n"
            "    select:\n"
            "        known_values = count(amount, status)\n",
            "PIE-S2309",
        ),
        (
            SOURCE_PREFIX + "table order_completeness:\n"
            "    from orders\n"
            "    select:\n"
            "        known_values = count(amount + amount)\n",
            "PIE-S2315",
        ),
        (
            SOURCE_PREFIX + "table order_completeness:\n"
            "    from orders\n"
            "    select:\n"
            "        known_values = count(lower(status))\n",
            "PIE-S2315",
        ),
        (
            SOURCE_PREFIX + "table order_completeness:\n"
            "    from orders\n"
            "    select:\n"
            "        known_values = count(count())\n",
            "PIE-S2311",
        ),
        (
            SOURCE_PREFIX + "table order_completeness:\n"
            "    from orders\n"
            "    select:\n"
            "        known_values = count(amount) + 1\n",
            "PIE-S2310",
        ),
        (
            SOURCE_PREFIX + "table order_completeness:\n"
            "    from orders\n"
            "    select:\n"
            "        count(amount)\n",
            "PIE-S2313",
        ),
        (
            SOURCE_PREFIX + "table order_completeness:\n"
            "    from orders\n"
            "    select:\n"
            "        status\n"
            "        known_amounts = count(amount)\n",
            "PIE-S2312",
        ),
        (
            SOURCE_PREFIX + "table order_completeness:\n"
            "    from orders\n"
            "    where count(amount) > 0\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2308",
        ),
        (
            SOURCE_PREFIX + "table order_completeness:\n"
            "    from orders\n"
            "    select:\n"
            "        known_anything = count(anything)\n",
            "PIE-S2314",
        ),
    ],
)
def test_invalid_count_field_shapes_do_not_emit_aggregate_call_ir(
    source: str,
    expected_code: str,
) -> None:
    script = _parse(source)
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == [expected_code]
    if ir_result.ir is not None:
        assert _aggregate_expressions(ir_result.ir) == ()


def test_existing_count_sum_avg_min_max_ir_behavior_remains_unchanged() -> None:
    script = _parse(
        SOURCE_PREFIX + "table aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        total = count()\n"
        "        amount_total = sum(amount)\n"
        "        average_score = avg(score)\n"
        "        first_created = min(created_at)\n"
        "        latest_created = max(created_at)\n"
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
    _assert_aggregate(
        projections["first_created"].expression,
        "min",
        "Timestamp",
        NullabilityIR.NULLABLE,
        ("created_at",),
    )
    _assert_aggregate(
        projections["latest_created"].expression,
        "max",
        "Timestamp",
        NullabilityIR.NULLABLE,
        ("created_at",),
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
