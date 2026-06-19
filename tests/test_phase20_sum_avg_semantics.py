from __future__ import annotations

import pytest

from pietto.ast_nodes import QueryDef, Script, TableDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import EffectiveNullability, SemanticResult, TypeKind, analyze
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
def test_direct_aliased_sum_avg_projections_are_semantically_accepted(
    relation_kind: str,
) -> None:
    script = _parse(
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
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    assert list(schema.fields) == [
        "total",
        "revenue",
        "score_total",
        "average_amount",
        "average_score",
    ]
    _assert_field(schema.fields["total"], "Int", EffectiveNullability.NON_NULL)
    _assert_field(schema.fields["revenue"], "Int", EffectiveNullability.NULLABLE)
    _assert_field(schema.fields["score_total"], "Float", EffectiveNullability.NULLABLE)
    _assert_field(
        schema.fields["average_amount"],
        "Float",
        EffectiveNullability.NULLABLE,
    )
    _assert_field(
        schema.fields["average_score"],
        "Float",
        EffectiveNullability.NULLABLE,
    )

    for item in relation.select_items:
        value_type = result.model.expression_value_types[item.expression]
        _assert_field_like_value(schema.fields[item.alias or ""], value_type)


def test_qualified_sum_avg_field_arguments_are_semantically_accepted() -> None:
    script = _parse(
        SOURCE_PREFIX + "table paid_order_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        revenue = sum(orders.amount)\n"
        "        average = avg(orders.score)\n"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    _assert_field(schema.fields["revenue"], "Int", EffectiveNullability.NULLABLE)
    _assert_field(schema.fields["average"], "Float", EffectiveNullability.NULLABLE)


def test_count_sum_and_avg_are_not_scalar_builtin_functions() -> None:
    assert "count" not in BUILTIN_FUNCTIONS
    assert "sum" not in BUILTIN_FUNCTIONS
    assert "avg" not in BUILTIN_FUNCTIONS


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    where sum(amount) > 0\n"
            "    select:\n"
            "        total = count()\n",
            (
                "PIE-S2308",
                "Aggregate sum() is not allowed in where clause; "
                "use it only as a direct aliased select projection",
            ),
        ),
        (
            "shape Order:\n"
            "    amount: Int not null\n"
            "    check positive_average:\n"
            "        avg(amount) > 0\n",
            (
                "PIE-S2308",
                "Aggregate avg() is not allowed in shape check; "
                "use it only as a direct aliased select projection",
            ),
        ),
        (
            "derive total(amount: Int not null) -> Int not null:\n    sum(amount)\n",
            (
                "PIE-S2308",
                "Aggregate sum() is not allowed in derive body; "
                "use it only as a direct aliased select projection",
            ),
        ),
        (
            "shape Order:\n"
            "    amount: Int not null\n"
            "    total: Int not null derive avg(amount)\n",
            (
                "PIE-S2308",
                "Aggregate avg() is not allowed in field derive body; "
                "use it only as a direct aliased select projection",
            ),
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        total = count()\n"
            "    order by:\n"
            "        sum(amount)\n",
            (
                "PIE-S2308",
                "Aggregate sum() is not allowed in order by; "
                "use it only as a direct aliased select projection",
            ),
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        revenue = sum()\n",
            (
                "PIE-S2309",
                "Aggregate function sum expects 1 arguments, got 0",
            ),
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        average = avg(amount, score)\n",
            (
                "PIE-S2309",
                "Aggregate function avg expects 1 arguments, got 2",
            ),
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        revenue = sum(status)\n",
            (
                "PIE-S2314",
                "Aggregate function sum expects Int, Float, or Decimal field "
                "argument, got Text",
            ),
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        average = avg(status)\n",
            (
                "PIE-S2314",
                "Aggregate function avg expects Int, Float, or Decimal field "
                "argument, got Text",
            ),
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        revenue = sum(amount + 1)\n",
            (
                "PIE-S2315",
                "Aggregate function sum requires a direct field argument; "
                "expression arguments are deferred",
            ),
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        average = avg(1)\n",
            (
                "PIE-S2315",
                "Aggregate function avg requires a direct field argument; "
                "expression arguments are deferred",
            ),
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        revenue = sum(avg(amount))\n",
            ("PIE-S2311", "Nested aggregate avg() is not supported"),
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        revenue = sum(lower(avg(amount)))\n",
            ("PIE-S2311", "Nested aggregate avg() is not supported"),
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        revenue = sum(amount) + 1\n",
            (
                "PIE-S2310",
                "Aggregate projection must be a direct aggregate call; "
                "composition around sum() is deferred",
            ),
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        avg(amount)\n",
            (
                "PIE-S2313",
                "Aggregate avg() projection requires an explicit alias",
            ),
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        status\n"
            "        revenue = sum(amount)\n",
            (
                "PIE-S2312",
                "Aggregate projections cannot be mixed with non-aggregate "
                "projections without GROUP BY",
            ),
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        median_amount = median(amount)\n",
            ("PIE-S2103", "Unknown function: median"),
        ),
    ],
)
def test_sum_avg_aggregate_diagnostics(
    source: str,
    expected: tuple[str, str],
) -> None:
    result = analyze(_parse(source))

    assert _errors(result) == [expected]


@pytest.mark.parametrize(
    "projection",
    [
        "revenue = sum(status)",
        "revenue = sum(amount + 1)",
        "revenue = sum(avg(amount))",
    ],
)
def test_invalid_sum_avg_projection_aliases_keep_unknown_schema(
    projection: str,
) -> None:
    script = _parse(
        SOURCE_PREFIX + "table paid_order_stats:\n"
        "    from orders\n"
        "    select:\n"
        f"        {projection}\n"
    )
    relation = _relation(script)

    result = analyze(script)
    field = result.model.relation_row_schemas[relation].fields["revenue"]

    assert field.resolved_type.kind is TypeKind.UNKNOWN
    assert field.nullability is EffectiveNullability.UNKNOWN


def test_mixed_sum_projection_does_not_publish_precise_sum_schema() -> None:
    script = _parse(
        SOURCE_PREFIX + "table paid_order_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        status\n"
        "        revenue = sum(amount)\n"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert schema.fields["status"].resolved_type.name == "Text"
    assert schema.fields["revenue"].resolved_type.kind is TypeKind.UNKNOWN
    assert schema.fields["revenue"].nullability is EffectiveNullability.UNKNOWN


@pytest.mark.parametrize(
    ("projection", "expected"),
    [
        ("revenue = sum(missing)", ("PIE-S2102", "Unknown field: missing")),
        (
            "average = avg(payments.amount)",
            ("PIE-S2102", "Unknown field: payments.amount"),
        ),
    ],
)
def test_sum_avg_unknown_field_suppresses_aggregate_cascade(
    projection: str,
    expected: tuple[str, str],
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table paid_order_stats:\n"
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
