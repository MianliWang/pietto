from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import replace
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
from pietto.ir.model import aggregate_call_contract
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, analyze

EXPRESSION_ARGUMENT_SOURCE_PREFIX = (
    "shape Order:\n"
    "    status: Text\n"
    "    region: Text\n"
    "    amount: Int\n"
    "    tax: Int\n"
    "    score: Float\n"
    "    weight: Float\n"
    "    price: Decimal\n"
    "    active: Bool\n"
    'source orders: Order = postgres.table("orders")\n'
)

COUNT_EXPRESSION_SOURCE_PREFIX = (
    "shape Order:\n"
    "    region: Text\n"
    "    status: Text\n"
    "    active: Bool\n"
    "    amount: Int\n"
    "    tax: Int\n"
    "    score: Float\n"
    "    weight: Float\n"
    'source orders: Order = postgres.table("orders")\n'
)

COUNT_FIELD_SOURCE_PREFIX = (
    "shape Order:\n"
    "    status: Text\n"
    "    amount: Int\n"
    "    score: Float\n"
    "    created_at: Timestamp\n"
    "    anything: Any | None\n"
    'source orders: Order = postgres.table("orders")\n'
)

COUNT_SOURCE_PREFIX = (
    "shape Order:\n"
    "    status: Text\n"
    "    amount: Int\n"
    'source orders: Order = postgres.table("orders")\n'
)

DECIMAL_SOURCE_PREFIX = (
    "shape Order:\n"
    "    status: Text\n"
    "    amount: Decimal\n"
    'source orders: Order = postgres.table("orders")\n'
)

MIN_MAX_SOURCE_PREFIX = (
    "shape Order:\n"
    "    status: Text\n"
    "    amount: Int\n"
    "    score: Float\n"
    "    price: Decimal\n"
    "    order_date: Date | None\n"
    "    created_at: Timestamp\n"
    'source orders: Order = postgres.table("orders")\n'
)

NUMERIC_LITERAL_SOURCE_PREFIX = (
    "shape Order:\n"
    "    status: Text\n"
    "    region: Text\n"
    "    amount: Int\n"
    "    tax: Int\n"
    "    score: Float\n"
    "    weight: Float\n"
    "    price: Decimal\n"
    "    discount: Decimal\n"
    "    active: Bool\n"
    'source orders: Order = postgres.table("orders")\n'
)

SUM_AVG_SOURCE_PREFIX = (
    "shape Order:\n"
    "    status: Text\n"
    "    amount: Int\n"
    "    score: Float\n"
    "    price: Decimal\n"
    'source orders: Order = postgres.table("orders")\n'
)


def test_sum_avg_numeric_expression_arguments_lower_to_aggregate_call_ir() -> None:
    script = _parse(
        EXPRESSION_ARGUMENT_SOURCE_PREFIX + "table aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        total = sum(amount + tax)\n"
        "        weighted = avg(score * weight)\n"
        "        decimal_total = sum(price + price)\n"
        "        decimal_average = avg(price - price)\n"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    projections = _projections(_relation_ir(ir_result.ir))

    _assert_binary_aggregate(
        projections["total"].expression,
        function="sum",
        result_type="Int",
        operator="+",
        left_name="amount",
        right_name="tax",
        argument_type="Int",
    )
    _assert_binary_aggregate(
        projections["weighted"].expression,
        function="avg",
        result_type="Float",
        operator="*",
        left_name="score",
        right_name="weight",
        argument_type="Float",
    )
    _assert_binary_aggregate(
        projections["decimal_total"].expression,
        function="sum",
        result_type="Decimal",
        operator="+",
        left_name="price",
        right_name="price",
        argument_type="Decimal",
    )
    _assert_binary_aggregate(
        projections["decimal_average"].expression,
        function="avg",
        result_type="Decimal",
        operator="-",
        left_name="price",
        right_name="price",
        argument_type="Decimal",
    )


def test_count_distinct_transform_arguments_lower_to_aggregate_call_ir() -> None:
    script = _parse(
        EXPRESSION_ARGUMENT_SOURCE_PREFIX + "table status_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        normalized = count_distinct(lower(status))\n"
        "        trimmed = count_distinct(trim(status))\n"
        "        normalized_trimmed = count_distinct(lower(trim(status)))\n"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    projections = _projections(_relation_ir(ir_result.ir))

    _assert_transform_aggregate(
        projections["normalized"].expression,
        callees=("lower",),
        field_name="status",
    )
    _assert_transform_aggregate(
        projections["trimmed"].expression,
        callees=("trim",),
        field_name="status",
    )
    _assert_transform_aggregate(
        projections["normalized_trimmed"].expression,
        callees=("lower", "trim"),
        field_name="status",
    )


def test_qualified_expression_leaves_preserve_field_identity() -> None:
    script = _parse(
        EXPRESSION_ARGUMENT_SOURCE_PREFIX + "table aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        total = sum(orders.amount + orders.tax)\n"
        "        normalized = count_distinct(lower(orders.status))\n"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    projections = _projections(_relation_ir(ir_result.ir))

    _assert_binary_aggregate(
        projections["total"].expression,
        function="sum",
        result_type="Int",
        operator="+",
        left_name="orders.amount",
        right_name="orders.tax",
        argument_type="Int",
    )
    _assert_transform_aggregate(
        projections["normalized"].expression,
        callees=("lower",),
        field_name="orders.status",
    )


def test_grouped_expression_argument_aggregates_preserve_group_keys() -> None:
    script = _parse(
        EXPRESSION_ARGUMENT_SOURCE_PREFIX + "table aggregate_stats_by_region:\n"
        "    from orders\n"
        "    group by:\n"
        "        region\n"
        "    select:\n"
        "        region\n"
        "        total = sum(amount + tax)\n"
        "        normalized = count_distinct(lower(status))\n"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    relation = _relation_ir(ir_result.ir)
    projections = _projections(relation)

    (key,) = relation.group_keys
    assert isinstance(key, FieldRefIR)
    assert key.name == "region"
    assert key.qualifier == ()
    assert key.field == FieldId(owner=_orders_symbol(), name="region")
    _assert_binary_aggregate(
        projections["total"].expression,
        function="sum",
        result_type="Int",
        operator="+",
        left_name="amount",
        right_name="tax",
        argument_type="Int",
    )
    _assert_transform_aggregate(
        projections["normalized"].expression,
        callees=("lower",),
        field_name="status",
    )


def test_direct_lower_expr_for_valid_expression_arguments_uses_aggregate_call_ir() -> (
    None
):
    script = _parse(
        EXPRESSION_ARGUMENT_SOURCE_PREFIX + "table aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        total = sum(amount + tax)\n"
        "        normalized = count_distinct(lower(status))\n"
    )
    relation = _relation_ast(script)
    semantic_result = analyze(script)
    input_schema = next(iter(semantic_result.model.source_row_schemas.values()))

    lowered_sum = lower_expr(
        relation.select_items[0].expression,
        semantic_result.model,
        fields=input_schema.fields,
        field_owner=_orders_symbol(),
        field_qualifier="orders",
    )
    lowered_count_distinct = lower_expr(
        relation.select_items[1].expression,
        semantic_result.model,
        fields=input_schema.fields,
        field_owner=_orders_symbol(),
        field_qualifier="orders",
    )

    assert _error_codes(semantic_result) == []
    assert lowered_sum.diagnostics == ()
    assert isinstance(lowered_sum.expression, AggregateCallIR)
    assert not isinstance(lowered_sum.expression, CallIR)
    assert isinstance(lowered_sum.expression.arguments[0], BinaryIR)
    assert lowered_count_distinct.diagnostics == ()
    assert isinstance(lowered_count_distinct.expression, AggregateCallIR)
    assert not isinstance(lowered_count_distinct.expression, CallIR)
    assert isinstance(lowered_count_distinct.expression.arguments[0], CallIR)


def test_direct_field_aggregate_lowering_remains_unchanged() -> None:
    script = _parse(
        EXPRESSION_ARGUMENT_SOURCE_PREFIX + "table aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        total = count()\n"
        "        known_statuses = count(status)\n"
        "        unique_statuses = count_distinct(status)\n"
        "        amount_total = sum(amount)\n"
        "        average_score = avg(score)\n"
        "        smallest_amount = min(amount)\n"
        "        largest_score = max(score)\n"
        "        amount_spread = stddev(amount)\n"
        "        score_spread = stddev(score)\n"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    projections = _projections(_relation_ir(ir_result.ir))

    _assert_direct_aggregate(
        projections["total"].expression,
        "count",
        "Int",
        NullabilityIR.NON_NULL,
        (),
    )
    _assert_direct_aggregate(
        projections["known_statuses"].expression,
        "count",
        "Int",
        NullabilityIR.NON_NULL,
        ("status",),
    )
    _assert_direct_aggregate(
        projections["unique_statuses"].expression,
        "count_distinct",
        "Int",
        NullabilityIR.NON_NULL,
        ("status",),
    )
    _assert_direct_aggregate(
        projections["amount_total"].expression,
        "sum",
        "Int",
        NullabilityIR.NULLABLE,
        ("amount",),
    )
    _assert_direct_aggregate(
        projections["average_score"].expression,
        "avg",
        "Float",
        NullabilityIR.NULLABLE,
        ("score",),
    )
    _assert_direct_aggregate(
        projections["smallest_amount"].expression,
        "min",
        "Int",
        NullabilityIR.NULLABLE,
        ("amount",),
    )
    _assert_direct_aggregate(
        projections["largest_score"].expression,
        "max",
        "Float",
        NullabilityIR.NULLABLE,
        ("score",),
    )
    for name, field in (("amount_spread", "amount"), ("score_spread", "score")):
        _assert_direct_aggregate(
            projections[name].expression,
            "stddev",
            "Float",
            NullabilityIR.NULLABLE,
            (field,),
        )


@pytest.mark.parametrize("function", ("stddev", "variance", "pvariance", "pstdev"))
def test_stddev_aggregate_call_contract_is_one_int_or_float_field(
    function: str,
) -> None:
    """The IR contract admits `stddev`, `variance`, `pvariance` and `pstdev`
    of one Int or Float field with a nullable Float result, and nothing a
    renderer could be handed besides."""
    script = _parse(
        EXPRESSION_ARGUMENT_SOURCE_PREFIX + "table spreads:\n"
        "    from orders\n"
        "    select:\n"
        f"        amount_spread = {function}(amount)\n"
        "        price_low = min(price)\n"
        "        total = sum(amount)\n"
    )
    ir_result = build_ir(script, analyze(script).model)
    assert ir_result.ir is not None
    projections = _projections(_relation_ir(ir_result.ir))
    call = cast(AggregateCallIR, projections["amount_spread"].expression)
    price = cast(AggregateCallIR, projections["price_low"].expression).arguments[0]
    total = cast(AggregateCallIR, projections["total"].expression)
    float_result = call.value_type

    assert call.function == function
    assert aggregate_call_contract(function, call.arguments, float_result)
    for arguments, value_type in (
        ((), float_result),
        ((*call.arguments, *call.arguments), float_result),
        ((price,), float_result),
        ((total,), float_result),
        (call.arguments, replace(float_result, nullability=NullabilityIR.NON_NULL)),
        (call.arguments, total.value_type),
    ):
        assert not aggregate_call_contract(function, arguments, value_type)


def test_group_generators_lower_to_the_filtered_aggregate_identities() -> None:
    """`sum(1 for o in group if TEST)` lowers to `filtered_count(TEST)` and
    `sum(o.f for o in group if TEST)` to `filtered_sum(f, TEST)`: the member
    row is the input row, and both are a non-None Int. The contract admits
    only a Bool test after at most one Int field."""
    script = _parse(
        EXPRESSION_ARGUMENT_SOURCE_PREFIX + "table conditional:\n"
        "    from orders\n"
        "    group by region\n"
        "    select:\n"
        "        region\n"
        "        active_orders = sum(1 for o in group if o.active)\n"
        "        active_amount = sum(o.amount for o in group if o.active)\n"
        "        total = sum(amount)\n"
    )
    # Analysis reads each member field `o.f` as the input row's field `f`.
    semantic = analyze(script)
    assert semantic.script is not None
    ir_result = build_ir(semantic.script, semantic.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    projections = _projections(_relation_ir(ir_result.ir))
    counted = cast(AggregateCallIR, projections["active_orders"].expression)
    summed = cast(AggregateCallIR, projections["active_amount"].expression)
    total = cast(AggregateCallIR, projections["total"].expression)

    assert (counted.function, summed.function) == ("filtered_count", "filtered_sum")
    test = counted.arguments[0]
    assert type(test) is FieldRefIR and test.name == "active"
    assert type(summed.arguments[1]) is FieldRefIR
    assert summed.arguments[1].name == "active"
    amount = summed.arguments[0]
    assert type(amount) is FieldRefIR and amount.name == "amount"
    for call in (counted, summed):
        assert call.value_type.canonical_name == "Int"
        assert call.value_type.nullability is NullabilityIR.NON_NULL
        assert aggregate_call_contract(call.function, call.arguments, call.value_type)
    result = counted.value_type
    for function, arguments, value_type in (
        ("filtered_count", (), result),
        ("filtered_count", (amount,), result),
        ("filtered_count", (test, test), result),
        ("filtered_sum", (test,), result),
        ("filtered_sum", (test, test), result),
        ("filtered_sum", (total, test), result),
        ("filtered_sum", (amount, test), total.value_type),
    ):
        assert not aggregate_call_contract(function, arguments, value_type)


@pytest.mark.parametrize(
    ("projection", "expected_code"),
    [
        ("value = sum(amount / tax)", "PIE-S2315"),
        ("value = sum(amount % tax)", "PIE-S2315"),
        ("value = count_distinct(len(status))", "PIE-S2315"),
        ("value = count_distinct(lower(amount))", "PIE-S2315"),
        # Phase 39 Slice 3 accepts "value = count(amount + tax)" semantically.
        ("value = count(1)", "PIE-S2315"),
        ("value = min(amount + tax)", "PIE-S2315"),
        ("value = max(score * weight)", "PIE-S2315"),
        ("value = sum(avg(amount))", "PIE-S2311"),
        ("value = sum(amount) if True else 1", "PIE-S2310"),
    ],
)
def test_unsupported_aggregate_expression_shapes_remain_before_ir(
    projection: str,
    expected_code: str,
) -> None:
    script = _parse(
        EXPRESSION_ARGUMENT_SOURCE_PREFIX + "table aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        f"        {projection}\n"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == [expected_code]
    if ir_result.ir is not None:
        assert _aggregate_expressions(ir_result.ir) == ()


def test_direct_aggregate_inside_satisfying_remains_semantic_error() -> None:
    script = _parse(
        EXPRESSION_ARGUMENT_SOURCE_PREFIX + "table aggregate_stats_by_region:\n"
        "    from orders\n"
        "    group by:\n"
        "        region\n"
        "    select:\n"
        "        region\n"
        "        total = sum(amount + tax)\n"
        "    having:\n"
        "        sum(amount + tax) > 10\n"
    )
    semantic_result = analyze(script)

    assert _error_codes(semantic_result) == ["PIE-S2308"]


def test_no_group_count_expression_arguments_lower_to_aggregate_call_ir() -> None:
    relation = _compile_relation(
        COUNT_EXPRESSION_SOURCE_PREFIX + "table order_counts:\n"
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
        "        active_count = count(active and True)\n"
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
        COUNT_EXPRESSION_SOURCE_PREFIX + "table order_counts_by_region:\n"
        "    from orders\n"
        "    group by:\n"
        "        region\n"
        "    select:\n"
        "        region\n"
        "        amount_tax = count(amount + tax)\n"
        "        lowered = count(lower(status))\n"
    )
    projections = _projections(relation)

    (key,) = relation.group_keys
    assert isinstance(key, FieldRefIR)
    assert key.name == "region"
    assert key.qualifier == ()
    assert key.field == FieldId(owner=_orders_symbol(), name="region")
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
        COUNT_EXPRESSION_SOURCE_PREFIX + "table order_counts:\n"
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
        COUNT_EXPRESSION_SOURCE_PREFIX + "table order_counts:\n"
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
        ("value = count(True)", "PIE-S2315"),
        ("value = count(1 + 2)", "PIE-S2315"),
        ("value = count(amount > 1)", "PIE-S2315"),
        ("value = count(1 <= amount <= 10)", "PIE-S2315"),
        ("value = count(amount is None)", "PIE-S2315"),
        ('value = count(matches(status, "active"))', "PIE-S2315"),
        ("value = count_distinct(amount + tax)", "PIE-S2315"),
        ("value = min(amount + tax)", "PIE-S2315"),
        ("value = max(amount + tax)", "PIE-S2315"),
        ("value = count(count())", "PIE-S2311"),
        ("value = count(amount) if True else 1", "PIE-S2310"),
        ("value = count_if(active)", "PIE-S2103"),
    ],
)
def test_deferred_count_expression_shapes_stop_before_meaningful_aggregate_ir(
    projection: str,
    expected_code: str,
) -> None:
    script = _parse(
        COUNT_EXPRESSION_SOURCE_PREFIX + "table order_counts:\n"
        "    from orders\n"
        "    select:\n"
        f"        {projection}\n"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == [expected_code]
    if ir_result.ir is not None:
        assert _aggregate_expressions(ir_result.ir) == ()


@pytest.mark.parametrize("relation_kind", ["table", "query"])
def test_count_star_still_lowers_to_zero_arg_aggregate_ir(
    relation_kind: str,
) -> None:
    script = _parse(
        COUNT_FIELD_SOURCE_PREFIX + f"{relation_kind} order_counts:\n"
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
        COUNT_FIELD_SOURCE_PREFIX + f"{relation_kind} order_completeness:\n"
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
        COUNT_FIELD_SOURCE_PREFIX + "table order_completeness:\n"
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
        COUNT_FIELD_SOURCE_PREFIX + "table completeness_by_status:\n"
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

    (key,) = relation.group_keys
    assert isinstance(key, FieldRefIR)
    assert key.name == "status"
    assert key.qualifier == ()
    assert key.field == FieldId(owner=_orders_symbol(), name="status")
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
        COUNT_FIELD_SOURCE_PREFIX + "table completeness_by_status:\n"
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

    (key,) = relation.group_keys
    assert isinstance(key, FieldRefIR)
    assert key.name == "status"
    assert key.qualifier == ("orders",)
    assert key.field == FieldId(owner=_orders_symbol(), name="status")
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
        COUNT_FIELD_SOURCE_PREFIX + "table order_completeness:\n"
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
            COUNT_FIELD_SOURCE_PREFIX + "table order_completeness:\n"
            "    from orders\n"
            "    select:\n"
            "        known_values = count(amount, status)\n",
            "PIE-S2309",
        ),
        (
            COUNT_FIELD_SOURCE_PREFIX + "table order_completeness:\n"
            "    from orders\n"
            "    select:\n"
            "        known_values = count(1)\n",
            "PIE-S2315",
        ),
        (
            COUNT_FIELD_SOURCE_PREFIX + "table order_completeness:\n"
            "    from orders\n"
            "    select:\n"
            '        known_values = count("x")\n',
            "PIE-S2315",
        ),
        (
            COUNT_FIELD_SOURCE_PREFIX + "table order_completeness:\n"
            "    from orders\n"
            "    select:\n"
            "        known_values = count(count())\n",
            "PIE-S2311",
        ),
        (
            COUNT_FIELD_SOURCE_PREFIX
            + "table order_completeness:\n    from orders\n    select:\n        known_values = count(amount) if True else 1\n",
            "PIE-S2310",
        ),
        (
            COUNT_FIELD_SOURCE_PREFIX + "table order_completeness:\n"
            "    from orders\n"
            "    select:\n"
            "        count(amount)\n",
            "PIE-S2313",
        ),
        (
            COUNT_FIELD_SOURCE_PREFIX + "table order_completeness:\n"
            "    from orders\n"
            "    select:\n"
            "        status\n"
            "        known_amounts = count(amount)\n",
            "PIE-S2312",
        ),
        (
            COUNT_FIELD_SOURCE_PREFIX + "table order_completeness:\n"
            "    from orders\n"
            "    where count(amount) > 0\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2308",
        ),
        (
            COUNT_FIELD_SOURCE_PREFIX + "table order_completeness:\n"
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
        COUNT_FIELD_SOURCE_PREFIX + "table aggregate_stats:\n"
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
            COUNT_SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        total = count(amount, status)\n",
            "PIE-S2309",
        ),
        (
            COUNT_SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    where count() > 0\n"
            "    select:\n"
            "        status\n",
            "PIE-S2308",
        ),
        (
            COUNT_SOURCE_PREFIX
            + "table paid_order_stats:\n    from orders\n    select:\n        total = count() if True else 1\n",
            "PIE-S2310",
        ),
        (
            COUNT_SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        total = count(count())\n",
            "PIE-S2311",
        ),
        (
            COUNT_SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        total = count(lower(count()))\n",
            "PIE-S2311",
        ),
        (
            COUNT_SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        total = lower(count())\n",
            "PIE-S2104",
        ),
        (
            COUNT_SOURCE_PREFIX + "table paid_order_stats:\n"
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


@pytest.mark.parametrize("relation_kind", ["table", "query"])
def test_no_group_decimal_aggregates_lower_to_existing_aggregate_call_ir(
    relation_kind: str,
) -> None:
    script = _parse(
        DECIMAL_SOURCE_PREFIX + f"{relation_kind} decimal_order_stats:\n"
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

    _assert_decimal_aggregate(
        projections["total_amount"].expression,
        "sum",
        ("amount",),
    )
    _assert_decimal_aggregate(
        projections["average_amount"].expression,
        "avg",
        ("amount",),
    )
    _assert_decimal_aggregate(
        projections["smallest_amount"].expression,
        "min",
        ("amount",),
    )
    _assert_decimal_aggregate(
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
        DECIMAL_SOURCE_PREFIX + "table decimal_order_stats:\n"
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
        _assert_decimal_aggregate(
            projections[name].expression,
            function,
            ("orders.amount",),
        )


def test_grouped_decimal_aggregates_lower_with_group_keys_preserved() -> None:
    script = _parse(
        DECIMAL_SOURCE_PREFIX + "table decimal_order_stats_by_status:\n"
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

    (key,) = relation.group_keys
    assert isinstance(key, FieldRefIR)
    assert key.name == "status"
    assert key.field == FieldId(owner=_orders_symbol(), name="status")
    for name, function, expected_arguments in (
        ("total_amount", "sum", ("amount",)),
        ("average_amount", "avg", ("amount",)),
        ("smallest_amount", "min", ("amount",)),
        ("largest_amount", "max", ("orders.amount",)),
    ):
        _assert_decimal_aggregate(
            projections[name].expression, function, expected_arguments
        )


def test_direct_lower_expr_for_decimal_aggregate_uses_aggregate_call_ir() -> None:
    script = _parse(
        DECIMAL_SOURCE_PREFIX + "table decimal_order_stats:\n"
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
    _assert_decimal_aggregate(lowered.expression, "sum", ("amount",))


@pytest.mark.parametrize(
    ("select_body", "expected_code"),
    [
        ("        value = avg(amount / amount)\n", "PIE-S2315"),
        ("        value = min(amount + amount)\n", "PIE-S2315"),
        ("        value = max(amount + amount)\n", "PIE-S2315"),
        ("        value = sum(avg(amount))\n", "PIE-S2311"),
        ("        value = sum(amount) if True else 1\n", "PIE-S2310"),
        ("        sum(amount)\n", "PIE-S2313"),
        ("        status\n        value = sum(amount)\n", "PIE-S2312"),
    ],
)
def test_invalid_decimal_aggregate_shapes_do_not_emit_aggregate_call_ir(
    select_body: str,
    expected_code: str,
) -> None:
    script = _parse(
        DECIMAL_SOURCE_PREFIX + "table decimal_order_stats:\n"
        "    from orders\n"
        "    select:\n"
        f"{select_body}"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == [expected_code]
    if ir_result.ir is not None:
        assert _aggregate_expressions(ir_result.ir) == ()


def test_decimal_multiplication_aggregate_lowers_to_a_binary_argument() -> None:
    script = _parse(
        DECIMAL_SOURCE_PREFIX + "table decimal_order_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        value = sum(amount * amount)\n"
    )
    semantic_result = analyze(script)
    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    expression = _relation_ir(ir_result.ir).projections[0].expression
    assert isinstance(expression, AggregateCallIR)
    assert expression.function == "sum"
    assert len(expression.arguments) == 1
    assert isinstance(expression.arguments[0], BinaryIR)
    assert expression.arguments[0].operator == "*"


@pytest.mark.parametrize("relation_kind", ["table", "query"])
def test_no_group_min_max_projections_lower_to_aggregate_call_ir(
    relation_kind: str,
) -> None:
    script = _parse(
        MIN_MAX_SOURCE_PREFIX + f"{relation_kind} order_extremes:\n"
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
        MIN_MAX_SOURCE_PREFIX + "table order_extremes:\n"
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
        MIN_MAX_SOURCE_PREFIX + "table grouped_order_extremes:\n"
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

    (key,) = relation.group_keys
    assert isinstance(key, FieldRefIR)
    assert key.name == "status"
    assert key.field == FieldId(owner=_orders_symbol(), name="status")
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
        MIN_MAX_SOURCE_PREFIX + "table order_extremes:\n"
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
        ("        value = max(amount, score, amount)\n", "PIE-S2309"),
        ("        value = min(amount + amount)\n", "PIE-S2315"),
        (
            "        subtotal = amount + amount\n        value = min(subtotal)\n",
            "PIE-S2102",
        ),
        ("        value = min(max(amount))\n", "PIE-S2311"),
        ("        value = min(status)\n", "PIE-S2314"),
        ("        min(amount)\n", "PIE-S2313"),
        ("        value = min(amount) if True else 1\n", "PIE-S2310"),
        ("        value = lower(min(amount))\n", "PIE-S2104"),
    ],
)
def test_invalid_min_max_projection_shapes_do_not_emit_aggregate_call_ir(
    select_body: str,
    expected_code: str,
) -> None:
    script = _parse(
        MIN_MAX_SOURCE_PREFIX + "table order_extremes:\n"
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
        MIN_MAX_SOURCE_PREFIX + "table order_extremes:\n"
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
        MIN_MAX_SOURCE_PREFIX + "table order_stats:\n"
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


def test_numeric_literal_aggregate_arguments_lower_to_existing_ir_nodes() -> None:
    relation = _compile_relation(
        NUMERIC_LITERAL_SOURCE_PREFIX + "table aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        plus_total = sum(amount + 1)\n"
        "        left_literal_total = sum(1 + amount)\n"
        "        minus_total = sum(amount - 1)\n"
        "        multiplied_total = sum(amount * 2)\n"
        "        weighted_average = avg(score * 2)\n"
        "        adjusted_average = avg(score + 1.5)\n"
    )
    projections = _projections(relation)

    _assert_literal_binary_aggregate(
        projections["plus_total"].expression,
        function="sum",
        result_type="Int",
        operator="+",
        argument_type="Int",
        left="amount",
        right=1,
    )
    _assert_literal_binary_aggregate(
        projections["left_literal_total"].expression,
        function="sum",
        result_type="Int",
        operator="+",
        argument_type="Int",
        left=1,
        right="amount",
    )
    _assert_literal_binary_aggregate(
        projections["minus_total"].expression,
        function="sum",
        result_type="Int",
        operator="-",
        argument_type="Int",
        left="amount",
        right=1,
    )
    _assert_literal_binary_aggregate(
        projections["multiplied_total"].expression,
        function="sum",
        result_type="Int",
        operator="*",
        argument_type="Int",
        left="amount",
        right=2,
    )
    _assert_literal_binary_aggregate(
        projections["weighted_average"].expression,
        function="avg",
        result_type="Float",
        operator="*",
        argument_type="Float",
        left="score",
        right=2,
    )
    _assert_literal_binary_aggregate(
        projections["adjusted_average"].expression,
        function="avg",
        result_type="Float",
        operator="+",
        argument_type="Float",
        left="score",
        right=1.5,
    )


def test_qualified_field_and_unary_leaves_lower_inside_aggregate_arguments() -> None:
    relation = _compile_relation(
        NUMERIC_LITERAL_SOURCE_PREFIX + "table aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        total = sum(+orders.amount + 1)\n"
        "        average = avg(-orders.score + 1.5)\n"
    )
    projections = _projections(relation)

    total = _assert_literal_binary_aggregate(
        projections["total"].expression,
        function="sum",
        result_type="Int",
        operator="+",
        argument_type="Int",
        left=None,
        right=1,
    )
    _assert_unary_operand(total.left, "+", "orders.amount")

    average = _assert_literal_binary_aggregate(
        projections["average"].expression,
        function="avg",
        result_type="Float",
        operator="+",
        argument_type="Float",
        left=None,
        right=1.5,
    )
    _assert_unary_operand(average.left, "-", "orders.score")


def test_grouped_numeric_literal_aggregates_lower_with_group_keys() -> None:
    relation = _compile_relation(
        NUMERIC_LITERAL_SOURCE_PREFIX + "table aggregate_stats_by_status:\n"
        "    from orders\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total = sum(amount + 1)\n"
        "        average = avg(score * 2)\n"
    )
    projections = _projections(relation)

    (key,) = relation.group_keys
    assert isinstance(key, FieldRefIR)
    assert key.name == "status"
    assert key.qualifier == ()
    assert key.field == FieldId(owner=_orders_symbol(), name="status")
    _assert_field(projections["status"].expression, "status")
    _assert_literal_binary_aggregate(
        projections["total"].expression,
        function="sum",
        result_type="Int",
        operator="+",
        argument_type="Int",
        left="amount",
        right=1,
    )
    _assert_literal_binary_aggregate(
        projections["average"].expression,
        function="avg",
        result_type="Float",
        operator="*",
        argument_type="Float",
        left="score",
        right=2,
    )


def test_direct_lower_expr_for_numeric_literal_aggregate_uses_aggregate_call_ir() -> (
    None
):
    script = _parse(
        NUMERIC_LITERAL_SOURCE_PREFIX + "table aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        total = sum(amount + 1)\n"
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
    _assert_literal_binary_aggregate(
        cast(ExpressionIR, lowered.expression),
        function="sum",
        result_type="Int",
        operator="+",
        argument_type="Int",
        left="amount",
        right=1,
    )


def test_field_only_expression_aggregate_arguments_still_lower() -> None:
    relation = _compile_relation(
        NUMERIC_LITERAL_SOURCE_PREFIX + "table aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        total = sum(amount + tax)\n"
        "        weighted = avg(score * weight)\n"
        "        decimal_total = sum(price + discount)\n"
        "        decimal_average = avg(price - discount)\n"
        "        decimal_product = sum(price * discount)\n"
    )
    projections = _projections(relation)

    _assert_literal_binary_aggregate(
        projections["total"].expression,
        function="sum",
        result_type="Int",
        operator="+",
        argument_type="Int",
        left="amount",
        right="tax",
    )
    _assert_literal_binary_aggregate(
        projections["weighted"].expression,
        function="avg",
        result_type="Float",
        operator="*",
        argument_type="Float",
        left="score",
        right="weight",
    )
    _assert_literal_binary_aggregate(
        projections["decimal_total"].expression,
        function="sum",
        result_type="Decimal",
        operator="+",
        argument_type="Decimal",
        left="price",
        right="discount",
    )
    _assert_literal_binary_aggregate(
        projections["decimal_average"].expression,
        function="avg",
        result_type="Decimal",
        operator="-",
        argument_type="Decimal",
        left="price",
        right="discount",
    )
    _assert_literal_binary_aggregate(
        projections["decimal_product"].expression,
        function="sum",
        result_type="Decimal",
        operator="*",
        argument_type="Decimal",
        left="price",
        right="discount",
    )


@pytest.mark.parametrize(
    ("projection", "expected_code"),
    [
        ("value = sum(1)", "PIE-S2315"),
        ("value = avg(1)", "PIE-S2315"),
        ("value = sum(1 + 2)", "PIE-S2315"),
        ("value = avg(1.5 * 2)", "PIE-S2315"),
        ("value = sum(amount / tax)", "PIE-S2315"),
        ("value = sum(amount % tax)", "PIE-S2315"),
        ("value = sum(amount + len(status))", "PIE-S2315"),
        ("value = sum(avg(amount))", "PIE-S2311"),
        ("value = sum(amount) if True else 1", "PIE-S2310"),
        ("value = count(1)", "PIE-S2315"),
        ("value = min(amount + 1)", "PIE-S2315"),
        ("value = max(score * 2)", "PIE-S2315"),
        ("value = count_distinct(len(status))", "PIE-S2315"),
        ("value = sum(price + 1)", "PIE-S2315"),
        ("value = sum(price + 1.5)", "PIE-S2315"),
    ],
)
def test_unsupported_numeric_literal_aggregate_shapes_remain_before_ir(
    projection: str,
    expected_code: str,
) -> None:
    script = _parse(
        NUMERIC_LITERAL_SOURCE_PREFIX + "table aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        f"        {projection}\n"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == [expected_code]
    if ir_result.ir is not None:
        assert _aggregate_expressions(ir_result.ir) == ()


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

    _assert_sum_avg_aggregate(total, "count", "Int", NullabilityIR.NON_NULL, ())
    _assert_sum_avg_aggregate(
        revenue, "sum", "Int", NullabilityIR.NULLABLE, ("amount",)
    )
    _assert_sum_avg_aggregate(
        score_total,
        "sum",
        "Float",
        NullabilityIR.NULLABLE,
        ("score",),
    )
    _assert_sum_avg_aggregate(
        average_amount,
        "avg",
        "Float",
        NullabilityIR.NULLABLE,
        ("amount",),
    )
    _assert_sum_avg_aggregate(
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
        SUM_AVG_SOURCE_PREFIX + "table paid_order_stats:\n"
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

    _assert_sum_avg_aggregate(
        revenue,
        "sum",
        "Int",
        NullabilityIR.NULLABLE,
        ("orders.amount",),
    )
    _assert_sum_avg_aggregate(
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
            SUM_AVG_SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        revenue = sum(status)\n",
            "PIE-S2314",
        ),
        (
            SUM_AVG_SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        revenue = sum(1)\n",
            "PIE-S2315",
        ),
        (
            SUM_AVG_SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        revenue = sum(avg(amount))\n",
            "PIE-S2311",
        ),
        (
            SUM_AVG_SOURCE_PREFIX
            + "table paid_order_stats:\n    from orders\n    select:\n        revenue = sum(amount) if True else 1\n",
            "PIE-S2310",
        ),
        (
            SUM_AVG_SOURCE_PREFIX + "table paid_order_stats:\n"
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


def _assert_binary_aggregate(
    expression: ExpressionIR,
    *,
    function: str,
    result_type: str,
    operator: str,
    left_name: str,
    right_name: str,
    argument_type: str,
) -> None:
    assert isinstance(expression, AggregateCallIR)
    assert not isinstance(expression, CallIR)
    assert expression.function == function
    assert expression.value_type.canonical_name == result_type
    assert expression.value_type.nullability is NullabilityIR.NULLABLE
    assert len(expression.arguments) == 1
    argument = expression.arguments[0]
    assert isinstance(argument, BinaryIR)
    assert argument.operator == operator
    assert argument.value_type.canonical_name == argument_type
    _assert_field(argument.left, left_name)
    _assert_field(argument.right, right_name)


def _assert_transform_aggregate(
    expression: ExpressionIR,
    *,
    callees: Sequence[str],
    field_name: str,
) -> None:
    assert isinstance(expression, AggregateCallIR)
    assert not isinstance(expression, CallIR)
    assert expression.function == "count_distinct"
    assert expression.value_type.canonical_name == "Int"
    assert expression.value_type.nullability is NullabilityIR.NON_NULL
    assert len(expression.arguments) == 1
    current = expression.arguments[0]
    for callee in callees:
        assert isinstance(current, CallIR)
        assert current.callee == callee
        assert len(current.arguments) == 1
        current = current.arguments[0]
    _assert_field(current, field_name)


def _assert_direct_aggregate(
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
    assert len(expression.arguments) == len(expected_arguments)
    for argument, expected_argument in zip(
        expression.arguments,
        expected_arguments,
        strict=True,
    ):
        _assert_field(argument, expected_argument)


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


def _compile_relation(source: str) -> RelationIR:
    script = _parse(source)
    semantic_result = analyze(script)
    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return _relation_ir(ir_result.ir)


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
    _assert_count_operand(argument.left, left)
    _assert_count_operand(argument.right, right)
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


def _assert_count_operand(
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


def _parse_count_program(relation_kind: str) -> Script:
    return _parse(
        COUNT_SOURCE_PREFIX + f"{relation_kind} paid_order_stats:\n"
        "    from orders\n"
        '    where status == "paid"\n'
        "    select:\n"
        "        total = count()\n"
    )


def _assert_decimal_aggregate(
    expression: ExpressionIR,
    function: str,
    expected_arguments: tuple[str, ...],
) -> None:
    assert isinstance(expression, AggregateCallIR)
    assert not isinstance(expression, CallIR)
    assert expression.function == function
    assert expression.value_type.canonical_name == "Decimal"
    assert expression.value_type.nullability is NullabilityIR.NULLABLE
    assert tuple(
        _decimal_field_name(argument) for argument in expression.arguments
    ) == (expected_arguments)


def _decimal_field_name(expression: ExpressionIR) -> str:
    assert isinstance(expression, FieldRefIR)
    assert expression.value_type.canonical_name == "Decimal"
    return ".".join((*expression.qualifier, expression.name))


def _assert_literal_binary_aggregate(
    expression: ExpressionIR,
    *,
    function: str,
    result_type: str,
    operator: str,
    argument_type: str,
    left: str | int | float | None,
    right: str | int | float | None,
) -> BinaryIR:
    assert isinstance(expression, AggregateCallIR)
    assert not isinstance(expression, CallIR)
    assert expression.function == function
    assert expression.value_type.canonical_name == result_type
    assert expression.value_type.nullability is NullabilityIR.NULLABLE
    assert len(expression.arguments) == 1
    argument = expression.arguments[0]
    assert isinstance(argument, BinaryIR)
    assert argument.operator == operator
    assert argument.value_type.canonical_name == argument_type
    if left is not None:
        _assert_literal_operand(argument.left, left)
    if right is not None:
        _assert_literal_operand(argument.right, right)
    return argument


def _assert_literal_operand(
    expression: ExpressionIR,
    expected: str | int | float,
) -> None:
    if isinstance(expected, str):
        _assert_field(expression, expected)
        return
    _assert_literal(expression, expected)


def _assert_literal(expression: ExpressionIR, expected_value: int | float) -> None:
    assert isinstance(expression, LiteralIR)
    assert expression.value == expected_value
    if type(expected_value) is int:
        assert expression.value_type.canonical_name == "Int"
    else:
        assert type(expected_value) is float
        assert expression.value_type.canonical_name == "Float"


def _assert_unary_operand(
    expression: ExpressionIR,
    expected_operator: str,
    expected_operand: str,
) -> None:
    assert isinstance(expression, UnaryIR)
    assert expression.operator == expected_operator
    _assert_field(expression.operand, expected_operand)


def _parse_sum_avg_program(relation_kind: str) -> Script:
    return _parse(
        SUM_AVG_SOURCE_PREFIX + f"{relation_kind} paid_order_stats:\n"
        "    from orders\n"
        '    where status == "paid"\n'
        "    select:\n"
        "        total = count()\n"
        "        revenue = sum(amount)\n"
        "        score_total = sum(score)\n"
        "        average_amount = avg(amount)\n"
        "        average_score = avg(score)\n"
    )


def _assert_sum_avg_aggregate(
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
