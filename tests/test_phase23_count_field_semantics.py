from __future__ import annotations

import pytest

from pietto.ast_nodes import QueryDef, Script, TableDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import EffectiveNullability, SemanticResult, TypeKind, analyze

SOURCE_PREFIX = (
    "shape Order:\n"
    "    status: Text not null\n"
    "    active: Bool not null\n"
    "    amount: Int not null\n"
    "    score: Float not null\n"
    "    price: Decimal not null\n"
    "    order_date: Date nullable\n"
    "    created_at: Timestamp not null\n"
    "    raw: Bytes not null\n"
    "    payload: Json not null\n"
    "    id: UUID not null\n"
    "    anything: Any nullable\n"
    'source orders: Order is postgres.table("orders")\n'
)


def test_count_star_remains_valid_int_non_null() -> None:
    script = _parse(
        SOURCE_PREFIX + "table order_counts:\n"
        "    from orders\n"
        "    select:\n"
        "        total = count()\n"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    assert list(schema.fields) == ["total"]
    _assert_field(schema.fields["total"], "Int", EffectiveNullability.NON_NULL)
    _assert_field_like_value(
        schema.fields["total"],
        result.model.expression_value_types[relation.select_items[0].expression],
    )


@pytest.mark.parametrize("relation_kind", ["table", "query"])
def test_no_group_count_field_accepts_concrete_bound_field_types(
    relation_kind: str,
) -> None:
    projections = (
        ("known_statuses", "status"),
        ("known_active", "active"),
        ("known_amounts", "amount"),
        ("known_scores", "score"),
        ("known_prices", "price"),
        ("known_order_dates", "order_date"),
        ("known_created_at", "created_at"),
        ("known_raw", "raw"),
        ("known_payloads", "payload"),
        ("known_ids", "id"),
    )
    select_body = "".join(
        f"        {alias} = count({field_name})\n" for alias, field_name in projections
    )
    script = _parse(
        SOURCE_PREFIX + f"{relation_kind} order_completeness:\n"
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


def test_no_group_qualified_count_field_is_accepted() -> None:
    script = _parse(
        SOURCE_PREFIX + "table order_completeness:\n"
        "    from orders\n"
        "    select:\n"
        "        known_amounts = count(orders.amount)\n"
        "        known_created_at = count(orders.created_at)\n"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    assert list(schema.fields) == ["known_amounts", "known_created_at"]
    _assert_field(schema.fields["known_amounts"], "Int", EffectiveNullability.NON_NULL)
    _assert_field(
        schema.fields["known_created_at"],
        "Int",
        EffectiveNullability.NON_NULL,
    )


def test_grouped_count_field_projection_is_accepted() -> None:
    script = _parse(
        SOURCE_PREFIX + "table order_completeness_by_status:\n"
        "    from orders\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        known_amounts = count(amount)\n"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    assert list(schema.fields) == ["status", "known_amounts"]
    _assert_field(schema.fields["status"], "Text", EffectiveNullability.NON_NULL)
    _assert_field(schema.fields["known_amounts"], "Int", EffectiveNullability.NON_NULL)


def test_grouped_qualified_count_field_projection_is_accepted() -> None:
    script = _parse(
        SOURCE_PREFIX + "table order_completeness_by_status:\n"
        "    from orders\n"
        "    group by:\n"
        "        orders.status\n"
        "    select:\n"
        "        orders.status\n"
        "        known_scores = count(orders.score)\n"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    assert list(schema.fields) == ["status", "known_scores"]
    _assert_field(schema.fields["status"], "Text", EffectiveNullability.NON_NULL)
    _assert_field(schema.fields["known_scores"], "Int", EffectiveNullability.NON_NULL)


def test_count_any_field_is_rejected_with_existing_unsupported_type_diagnostic() -> (
    None
):
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table order_completeness:\n"
            "    from orders\n"
            "    select:\n"
            "        known_anything = count(anything)\n"
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2314",
            "Aggregate function count expects concrete non-Any field argument, got Any",
        )
    ]


def test_count_missing_field_uses_existing_unresolved_field_diagnostic_only() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table order_completeness:\n"
            "    from orders\n"
            "    select:\n"
            "        known_missing = count(missing)\n"
        )
    )

    assert _errors(result) == [("PIE-S2102", "Unknown field: missing")]


@pytest.mark.parametrize(
    ("projection", "expected"),
    [
        (
            "known_values = count(amount, status)",
            (
                "PIE-S2309",
                "Aggregate function count expects 0 or 1 arguments, got 2",
            ),
        ),
        (
            "known_values = count(amount + amount)",
            (
                "PIE-S2315",
                "Aggregate function count requires a direct field argument; "
                "expression arguments are deferred",
            ),
        ),
        (
            "known_values = count(lower(status))",
            (
                "PIE-S2315",
                "Aggregate function count requires a direct field argument; "
                "expression arguments are deferred",
            ),
        ),
        (
            "known_values = count(count())",
            ("PIE-S2311", "Nested aggregate count() is not supported"),
        ),
        (
            "known_values = count(amount) + 1",
            (
                "PIE-S2310",
                "Aggregate projection must be a direct aggregate call; "
                "composition around count() is deferred",
            ),
        ),
        (
            "count(amount)",
            ("PIE-S2313", "Aggregate count() projection requires an explicit alias"),
        ),
    ],
)
def test_count_field_invalid_projection_shapes_use_existing_diagnostics(
    projection: str,
    expected: tuple[str, str],
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table order_completeness:\n"
            "    from orders\n"
            "    select:\n"
            f"        {projection}\n"
        )
    )

    assert _errors(result) == [expected]


def test_mixed_no_group_count_field_projection_remains_rejected() -> None:
    script = _parse(
        SOURCE_PREFIX + "table order_completeness:\n"
        "    from orders\n"
        "    select:\n"
        "        status\n"
        "        known_amounts = count(amount)\n"
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
    assert schema.fields["known_amounts"].resolved_type.kind is TypeKind.UNKNOWN
    assert schema.fields["known_amounts"].nullability is EffectiveNullability.UNKNOWN


def test_count_field_in_invalid_context_remains_rejected() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table order_completeness:\n"
            "    from orders\n"
            "    where count(amount) > 0\n"
            "    select:\n"
            "        amount\n"
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2308",
            "Aggregate count() is not allowed in where clause; "
            "use it only as a direct aliased select projection",
        )
    ]


def test_existing_sum_avg_min_max_semantics_remain_unchanged() -> None:
    script = _parse(
        SOURCE_PREFIX + "table aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        total = count()\n"
        "        revenue = sum(amount)\n"
        "        average_score = avg(score)\n"
        "        first_order_date = min(order_date)\n"
        "        latest_created_at = max(created_at)\n"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    _assert_field(schema.fields["total"], "Int", EffectiveNullability.NON_NULL)
    _assert_field(schema.fields["revenue"], "Int", EffectiveNullability.NULLABLE)
    _assert_field(
        schema.fields["average_score"],
        "Float",
        EffectiveNullability.NULLABLE,
    )
    _assert_field(
        schema.fields["first_order_date"], "Date", EffectiveNullability.NULLABLE
    )
    _assert_field(
        schema.fields["latest_created_at"],
        "Timestamp",
        EffectiveNullability.NULLABLE,
    )


@pytest.mark.parametrize(
    ("projection", "expected"),
    [
        (
            "value = sum(status)",
            (
                "PIE-S2314",
                "Aggregate function sum expects Int or Float field argument, got Text",
            ),
        ),
        (
            "value = avg(price)",
            (
                "PIE-S2314",
                "Aggregate function avg expects Int or Float field argument, got Decimal",
            ),
        ),
        (
            "value = min(status)",
            (
                "PIE-S2314",
                "Aggregate function min expects Int, Float, Date, or Timestamp "
                "field argument, got Text",
            ),
        ),
        (
            "value = max(active)",
            (
                "PIE-S2314",
                "Aggregate function max expects Int, Float, Date, or Timestamp "
                "field argument, got Bool",
            ),
        ),
    ],
)
def test_existing_sum_avg_min_max_diagnostics_remain_unchanged(
    projection: str,
    expected: tuple[str, str],
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table aggregate_stats:\n"
            "    from orders\n"
            "    select:\n"
            f"        {projection}\n"
        )
    )

    assert _errors(result) == [expected]


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
