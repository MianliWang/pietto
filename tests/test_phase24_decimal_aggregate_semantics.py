from __future__ import annotations

import pytest

from pietto.ast_nodes import QueryDef, Script, TableDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import EffectiveNullability, SemanticResult, TypeKind, analyze
from pietto.semantic.aggregates import semantic_aggregate_result_value_type

SOURCE_PREFIX = (
    "shape Order:\n"
    "    status: Text not null\n"
    "    active: Bool not null\n"
    "    amount: Decimal not null\n"
    "    quantity: Int not null\n"
    "    score: Float not null\n"
    "    order_date: Date nullable\n"
    "    created_at: Timestamp not null\n"
    "    raw: Bytes not null\n"
    "    payload: Json not null\n"
    "    id: UUID not null\n"
    "    anything: Any nullable\n"
    'source orders: Order is postgres.table("orders")\n'
)


@pytest.mark.parametrize("relation_kind", ["table", "query"])
def test_no_group_decimal_aggregates_are_accepted(relation_kind: str) -> None:
    script = _parse(
        SOURCE_PREFIX + f"{relation_kind} decimal_order_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        total_amount = sum(amount)\n"
        "        average_amount = avg(amount)\n"
        "        smallest_amount = min(amount)\n"
        "        largest_amount = max(amount)\n"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    assert list(schema.fields) == [
        "total_amount",
        "average_amount",
        "smallest_amount",
        "largest_amount",
    ]
    for item in relation.select_items:
        assert item.alias is not None
        _assert_field(
            schema.fields[item.alias], "Decimal", EffectiveNullability.NULLABLE
        )
        _assert_field_like_value(
            schema.fields[item.alias],
            result.model.expression_value_types[item.expression],
        )


def test_qualified_decimal_aggregate_arguments_are_accepted() -> None:
    script = _parse(
        SOURCE_PREFIX + "table decimal_order_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        total_amount = sum(orders.amount)\n"
        "        average_amount = avg(orders.amount)\n"
        "        smallest_amount = min(orders.amount)\n"
        "        largest_amount = max(orders.amount)\n"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    for field in schema.fields.values():
        _assert_field(field, "Decimal", EffectiveNullability.NULLABLE)


def test_grouped_decimal_aggregate_projections_are_accepted() -> None:
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
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    assert list(schema.fields) == [
        "status",
        "total_amount",
        "average_amount",
        "smallest_amount",
        "largest_amount",
    ]
    _assert_field(schema.fields["status"], "Text", EffectiveNullability.NON_NULL)
    for name in (
        "total_amount",
        "average_amount",
        "smallest_amount",
        "largest_amount",
    ):
        _assert_field(schema.fields[name], "Decimal", EffectiveNullability.NULLABLE)


@pytest.mark.parametrize(
    "projection",
    [
        "value = sum(amount * amount)",
        "value = avg(amount / amount)",
        "value = min(amount + amount)",
        "value = max(amount + amount)",
    ],
)
def test_decimal_aggregate_expression_arguments_remain_deferred(
    projection: str,
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table decimal_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            f"        {projection}\n"
        )
    )

    function_name = projection.split("(", maxsplit=1)[0].removeprefix("value = ")
    assert _errors(result) == [
        (
            "PIE-S2315",
            f"Aggregate function {function_name} requires a direct field argument; "
            "expression arguments are deferred",
        )
    ]


def test_decimal_multiplication_is_not_enabled_outside_aggregates() -> None:
    script = _parse(
        SOURCE_PREFIX + "table decimal_order_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        bad = amount * amount\n"
    )
    relation = _relation(script)

    result = analyze(script)
    field = result.model.relation_row_schemas[relation].fields["bad"]

    assert _errors(result) == [
        ("PIE-S2105", "Invalid operands for operator *: expected numeric operands")
    ]
    assert field.resolved_type.kind is TypeKind.UNKNOWN
    assert field.nullability is EffectiveNullability.UNKNOWN


@pytest.mark.parametrize(
    ("projection", "function_name"),
    [
        ("value = sum(1 + 2)", "sum"),
        ("value = avg(1.5 * 2)", "avg"),
        ("value = min(quantity + quantity)", "min"),
        ("value = max(score + score)", "max"),
        ("value = count_distinct(len(status))", "count_distinct"),
    ],
)
def test_existing_aggregate_expression_argument_diagnostics_remain_deferred(
    projection: str,
    function_name: str,
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table aggregate_stats:\n"
            "    from orders\n"
            "    select:\n"
            f"        {projection}\n"
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2315",
            f"Aggregate function {function_name} requires a direct field argument; "
            "expression arguments are deferred",
        )
    ]


@pytest.mark.parametrize(
    ("function_name", "field_name", "actual_type", "expected"),
    [
        ("sum", "active", "Bool", "Int, Float, or Decimal"),
        ("avg", "status", "Text", "Int, Float, or Decimal"),
        ("sum", "order_date", "Date", "Int, Float, or Decimal"),
        ("avg", "created_at", "Timestamp", "Int, Float, or Decimal"),
        ("sum", "raw", "Bytes", "Int, Float, or Decimal"),
        ("avg", "payload", "Json", "Int, Float, or Decimal"),
        ("sum", "id", "UUID", "Int, Float, or Decimal"),
        ("avg", "anything", "Any", "Int, Float, or Decimal"),
        ("min", "active", "Bool", "Int, Float, Decimal, Date, or Timestamp"),
        ("max", "status", "Text", "Int, Float, Decimal, Date, or Timestamp"),
        ("min", "raw", "Bytes", "Int, Float, Decimal, Date, or Timestamp"),
        ("max", "payload", "Json", "Int, Float, Decimal, Date, or Timestamp"),
        ("min", "id", "UUID", "Int, Float, Decimal, Date, or Timestamp"),
        ("max", "anything", "Any", "Int, Float, Decimal, Date, or Timestamp"),
    ],
)
def test_decimal_aggregate_slice_preserves_unsupported_direct_field_types(
    function_name: str,
    field_name: str,
    actual_type: str,
    expected: str,
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table decimal_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            f"        value = {function_name}({field_name})\n"
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2314",
            f"Aggregate function {function_name} expects {expected} field "
            f"argument, got {actual_type}",
        )
    ]


@pytest.mark.parametrize(
    ("projection", "expected"),
    [
        (
            "value = sum(avg(amount))",
            ("PIE-S2311", "Nested aggregate avg() is not supported"),
        ),
        (
            "value = sum(amount) + 1",
            (
                "PIE-S2310",
                "Aggregate projection must be a direct aggregate call; "
                "composition around sum() is deferred",
            ),
        ),
        (
            "sum(amount)",
            ("PIE-S2313", "Aggregate sum() projection requires an explicit alias"),
        ),
        (
            "status\n        value = sum(amount)",
            (
                "PIE-S2312",
                "Aggregate projections cannot be mixed with non-aggregate "
                "projections without GROUP BY",
            ),
        ),
    ],
)
def test_existing_decimal_aggregate_invalid_shapes_keep_existing_diagnostics(
    projection: str,
    expected: tuple[str, str],
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table decimal_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            f"        {projection}\n"
        )
    )

    assert _errors(result) == [expected]


def test_decimal_aggregate_in_invalid_context_remains_rejected() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table decimal_order_stats:\n"
            "    from orders\n"
            "    where sum(amount) > 0\n"
            "    select:\n"
            "        amount\n"
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2308",
            "Aggregate sum() is not allowed in where clause; "
            "use it only as a direct aliased select projection",
        )
    ]


def test_decimal_aggregate_missing_field_uses_unresolved_field_diagnostic_only() -> (
    None
):
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table decimal_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        value = sum(missing)\n"
        )
    )

    assert _errors(result) == [("PIE-S2102", "Unknown field: missing")]


def test_projection_alias_is_not_a_decimal_aggregate_argument() -> None:
    script = _parse(
        SOURCE_PREFIX + "table decimal_order_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        subtotal = quantity + quantity\n"
        "        value = sum(subtotal)\n"
    )
    relation = _relation(script)

    result = analyze(script)
    field = result.model.relation_row_schemas[relation].fields["value"]

    assert _errors(result) == [("PIE-S2102", "Unknown field: subtotal")]
    assert field.resolved_type.kind is TypeKind.UNKNOWN
    assert field.nullability is EffectiveNullability.UNKNOWN


def test_decimal_aggregate_result_helper_returns_decimal_nullable() -> None:
    script = _parse(
        SOURCE_PREFIX + "table decimal_order_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        value = sum(amount)\n"
    )
    relation = _relation(script)
    result = analyze(script)
    expression = relation.select_items[0].expression
    argument = getattr(expression, "arguments")[0]
    argument_type = result.model.expression_value_types[argument]

    assert _errors(result) == []
    for function_name in ("sum", "avg", "min", "max"):
        value_type = semantic_aggregate_result_value_type(function_name, argument_type)
        assert value_type is not None
        _assert_field(value_type, "Decimal", EffectiveNullability.NULLABLE)


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
        == getattr(value_type, "resolved_type").name
    )
    assert getattr(field, "nullability") is getattr(value_type, "nullability")
