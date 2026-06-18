from __future__ import annotations

import pytest

from pietto.ast_nodes import CallExpr, QueryDef, Script, TableDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import EffectiveNullability, SemanticResult, TypeKind, analyze
from pietto.semantic.aggregates import (
    aggregate_call_name,
    semantic_aggregate_call_name,
    semantic_aggregate_result_value_type,
    semantic_projection_aggregate_result_value_type,
)
from pietto.semantic.catalog import BUILTIN_FUNCTIONS

SOURCE_PREFIX = (
    "shape Order:\n"
    "    status: Text not null\n"
    "    active: Bool not null\n"
    "    amount: Int not null\n"
    "    score: Float not null\n"
    "    price: Decimal not null\n"
    "    order_date: Date nullable\n"
    "    created_at: Timestamp not null\n"
    "    customer_id: UUID not null\n"
    "    raw: Bytes not null\n"
    "    payload: Json not null\n"
    "    anything: Any nullable\n"
    'source orders: Order is postgres.table("orders")\n'
)


@pytest.mark.parametrize("relation_kind", ["table", "query"])
def test_no_group_count_distinct_accepts_comparable_direct_field_types(
    relation_kind: str,
) -> None:
    projections = (
        ("unique_active", "active"),
        ("unique_amounts", "amount"),
        ("unique_scores", "score"),
        ("unique_prices", "price"),
        ("unique_statuses", "status"),
        ("unique_order_dates", "order_date"),
        ("unique_created_at", "created_at"),
        ("unique_customers", "customer_id"),
    )
    select_body = "".join(
        f"        {alias} = count_distinct({field_name})\n"
        for alias, field_name in projections
    )
    script = _parse(
        SOURCE_PREFIX + f"{relation_kind} unique_order_values:\n"
        "    from orders\n"
        "    select:\n"
        f"{select_body}"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    assert list(schema.fields) == [alias for alias, _ in projections]
    for item in relation.select_items:
        assert item.alias is not None
        field = schema.fields[item.alias]
        _assert_field(field, "Int", EffectiveNullability.NON_NULL)
        _assert_field_like_value(
            field,
            result.model.expression_value_types[item.expression],
        )


def test_no_group_qualified_count_distinct_field_is_accepted() -> None:
    script = _parse(
        SOURCE_PREFIX + "table unique_order_values:\n"
        "    from orders\n"
        "    select:\n"
        "        unique_customers = count_distinct(orders.customer_id)\n"
        "        unique_statuses = count_distinct(orders.status)\n"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    assert list(schema.fields) == ["unique_customers", "unique_statuses"]
    _assert_field(
        schema.fields["unique_customers"], "Int", EffectiveNullability.NON_NULL
    )
    _assert_field(
        schema.fields["unique_statuses"], "Int", EffectiveNullability.NON_NULL
    )


def test_grouped_count_distinct_projection_is_accepted() -> None:
    script = _parse(
        SOURCE_PREFIX + "table unique_customers_by_status:\n"
        "    from orders\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        unique_customers = count_distinct(customer_id)\n"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    assert list(schema.fields) == ["status", "unique_customers"]
    _assert_field(schema.fields["status"], "Text", EffectiveNullability.NON_NULL)
    _assert_field(
        schema.fields["unique_customers"], "Int", EffectiveNullability.NON_NULL
    )


def test_grouped_qualified_count_distinct_projection_is_accepted() -> None:
    script = _parse(
        SOURCE_PREFIX + "table unique_customers_by_status:\n"
        "    from orders\n"
        "    group by:\n"
        "        orders.status\n"
        "    select:\n"
        "        orders.status\n"
        "        unique_customers = count_distinct(orders.customer_id)\n"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    assert list(schema.fields) == ["status", "unique_customers"]
    _assert_field(schema.fields["status"], "Text", EffectiveNullability.NON_NULL)
    _assert_field(
        schema.fields["unique_customers"], "Int", EffectiveNullability.NON_NULL
    )


@pytest.mark.parametrize(
    ("field_name", "actual_type"),
    [
        ("raw", "Bytes"),
        ("payload", "Json"),
        ("anything", "Any"),
    ],
)
def test_count_distinct_rejects_unsupported_direct_field_argument_types(
    field_name: str,
    actual_type: str,
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table unique_order_values:\n"
            "    from orders\n"
            "    select:\n"
            f"        unique_values = count_distinct({field_name})\n"
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2314",
            "Aggregate function count_distinct expects Bool, Int, Float, "
            "Decimal, Text, Date, Timestamp, or UUID field argument, "
            f"got {actual_type}",
        )
    ]


def test_count_distinct_missing_field_uses_existing_unresolved_field_diagnostic_only() -> (
    None
):
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table unique_order_values:\n"
            "    from orders\n"
            "    select:\n"
            "        unique_missing = count_distinct(missing)\n"
        )
    )

    assert _errors(result) == [("PIE-S2102", "Unknown field: missing")]


def test_projection_alias_is_not_a_count_distinct_argument() -> None:
    script = _parse(
        SOURCE_PREFIX + "table unique_order_values:\n"
        "    from orders\n"
        "    select:\n"
        "        subtotal = amount + amount\n"
        "        unique_subtotals = count_distinct(subtotal)\n"
    )
    relation = _relation(script)

    result = analyze(script)
    field = result.model.relation_row_schemas[relation].fields["unique_subtotals"]

    assert _errors(result) == [("PIE-S2102", "Unknown field: subtotal")]
    assert field.resolved_type.kind is TypeKind.UNKNOWN
    assert field.nullability is EffectiveNullability.UNKNOWN


@pytest.mark.parametrize(
    ("projection", "expected"),
    [
        (
            "unique_values = count_distinct()",
            (
                "PIE-S2309",
                "Aggregate function count_distinct expects 1 arguments, got 0",
            ),
        ),
        (
            "unique_values = count_distinct(customer_id, status)",
            (
                "PIE-S2309",
                "Aggregate function count_distinct expects 1 arguments, got 2",
            ),
        ),
        (
            "unique_values = count_distinct(amount + amount)",
            (
                "PIE-S2315",
                "Aggregate function count_distinct requires a direct field "
                "argument; expression arguments are deferred",
            ),
        ),
        (
            "unique_values = count_distinct(lower(status))",
            (
                "PIE-S2315",
                "Aggregate function count_distinct requires a direct field "
                "argument; expression arguments are deferred",
            ),
        ),
        (
            "unique_values = count_distinct(count())",
            ("PIE-S2311", "Nested aggregate count() is not supported"),
        ),
        (
            "unique_values = count_distinct(customer_id) + 1",
            (
                "PIE-S2310",
                "Aggregate projection must be a direct aggregate call; "
                "composition around count_distinct() is deferred",
            ),
        ),
        (
            "count_distinct(customer_id)",
            (
                "PIE-S2313",
                "Aggregate count_distinct() projection requires an explicit alias",
            ),
        ),
    ],
)
def test_count_distinct_invalid_projection_shapes_use_existing_diagnostics(
    projection: str,
    expected: tuple[str, str],
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table unique_order_values:\n"
            "    from orders\n"
            "    select:\n"
            f"        {projection}\n"
        )
    )

    assert _errors(result) == [expected]


def test_mixed_no_group_count_distinct_projection_remains_rejected() -> None:
    script = _parse(
        SOURCE_PREFIX + "table unique_order_values:\n"
        "    from orders\n"
        "    select:\n"
        "        status\n"
        "        unique_customers = count_distinct(customer_id)\n"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == [
        (
            "PIE-S2312",
            "Aggregate projections cannot be mixed with non-aggregate "
            "projections without GROUP BY",
        )
    ]
    assert schema.fields["status"].resolved_type.name == "Text"
    assert schema.fields["unique_customers"].resolved_type.kind is TypeKind.UNKNOWN
    assert schema.fields["unique_customers"].nullability is EffectiveNullability.UNKNOWN


def test_count_distinct_in_invalid_context_remains_rejected() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table unique_order_values:\n"
            "    from orders\n"
            "    where count_distinct(customer_id) > 0\n"
            "    select:\n"
            "        customer_id\n"
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2308",
            "Aggregate count_distinct() is not allowed in where clause; "
            "use it only as a direct aliased select projection",
        )
    ]


def test_count_distinct_is_semantic_only_until_ir_slice() -> None:
    script = _parse(
        SOURCE_PREFIX + "table unique_order_values:\n"
        "    from orders\n"
        "    select:\n"
        "        unique_customers = count_distinct(customer_id)\n"
    )
    relation = _relation(script)
    expression = relation.select_items[0].expression
    assert isinstance(expression, CallExpr)

    result = analyze(script)
    argument_type = result.model.expression_value_types[expression.arguments[0]]
    projection_type = semantic_projection_aggregate_result_value_type(
        "count_distinct",
        argument_type,
    )

    assert _errors(result) == []
    assert "count_distinct" not in BUILTIN_FUNCTIONS
    assert aggregate_call_name(expression) is None
    assert semantic_aggregate_call_name(expression) == "count_distinct"
    assert semantic_aggregate_result_value_type("count_distinct", argument_type) is None
    assert projection_type is not None
    assert projection_type.resolved_type.name == "Int"
    assert projection_type.nullability is EffectiveNullability.NON_NULL


def _parse(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _relation(script: Script) -> TableDef | QueryDef:
    relation = script.definitions[-1]
    assert isinstance(relation, (TableDef, QueryDef))
    return relation


def _errors(result: SemanticResult) -> list[tuple[str, str]]:
    return [
        (diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _assert_field(
    field: object,
    expected_type: str,
    expected_nullability: EffectiveNullability,
) -> None:
    assert getattr(field, "resolved_type").kind is TypeKind.BUILTIN
    assert getattr(field, "resolved_type").name == expected_type
    assert getattr(field, "nullability") is expected_nullability


def _assert_field_like_value(field: object, value_type: object) -> None:
    assert (
        getattr(field, "resolved_type").name
        == getattr(
            value_type,
            "resolved_type",
        ).name
    )
    assert getattr(field, "nullability") is getattr(value_type, "nullability")
