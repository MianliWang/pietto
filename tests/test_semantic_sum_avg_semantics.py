from __future__ import annotations

import pytest

from pietto.ast_nodes import QueryDef, Script, TableDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import EffectiveNullability, SemanticResult, TypeKind, analyze
from pietto.semantic.catalog import BUILTIN_FUNCTIONS

SOURCE_PREFIX = (
    "shape Order:\n"
    "    status: Text\n"
    "    amount: Int\n"
    "    score: Float\n"
    "    price: Decimal\n"
    'source orders: Order = postgres.table("orders")\n'
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
            "    amount: Int\n"
            "    positive_average = check(avg(amount) > 0)\n",
            (
                "PIE-S2308",
                "Aggregate avg() is not allowed in shape check; "
                "use it only as a direct aliased select projection",
            ),
        ),
        (
            "derive total(amount: Int) -> Int:\n    return sum(amount)\n",
            (
                "PIE-S2308",
                "Aggregate sum() is not allowed in derive body; "
                "use it only as a direct aliased select projection",
            ),
        ),
        (
            "shape Order:\n    amount: Int\n    total: Int derive avg(amount)\n",
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
            "        average = avg(1)\n",
            (
                "PIE-S2315",
                "Aggregate function avg requires a direct field argument; "
                "expression arguments are not supported yet",
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
            SOURCE_PREFIX
            + "table paid_order_stats:\n    from orders\n    select:\n        revenue = sum(amount) if True else 1\n",
            (
                "PIE-S2310",
                "Aggregate composition requires scalar calls or arithmetic over direct aggregates, group keys and literals; invalid composition around sum(); select the sum() under a name in one query, then compute with that name in another that reads it with `from`",
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
            "        mean_amount = mean(amount)\n",
            (
                "PIE-S2103",
                "Unknown function: mean; the available aggregates are avg, "
                "count, count_distinct, first, last, max, median, min, pstdev, "
                "pvariance, quantile, stddev, string_agg, sum and variance",
            ),
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
        "revenue = sum(1)",
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


def test_round_of_an_avg_names_the_two_query_route_that_is_accepted() -> None:
    grouped = (
        SOURCE_PREFIX + "query per_status:\n    from orders\n    group by status\n"
    )
    composed = analyze(
        _parse(grouped + "    select status, mean = round(avg(price), 2)\n")
    )
    assert composed.diagnostics == ()
    accepted = analyze(
        _parse(
            grouped + "    select status, mean = avg(price)\n"
            "query rounded:\n"
            "    from per_status\n"
            "    select status, mean = round(mean, 2)\n"
        )
    )
    assert accepted.diagnostics == ()


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


# The sample deviation and the sample and population variances and deviation
# share one argument and result rule.
SPREADS = ("stddev", "variance", "pvariance", "pstdev")


@pytest.mark.parametrize("function", SPREADS)
def test_stddev_of_an_int_or_float_field_is_a_nullable_float(function: str) -> None:
    """`stddev` is the sample deviation of an Int or Float direct field, an
    alias of either or a qualified field; below two values it is None.
    `variance`, `pvariance` and `pstdev` take the same arguments."""
    script = _parse(
        (
            SOURCE_PREFIX + "type Ratio = Float\n"
            "shape Reading:\n"
            "    ratio: Ratio\n"
            'source readings: Reading = postgres.table("readings")\n'
            "table by_status:\n"
            "    from orders\n"
            "    group by status\n"
            "    select:\n"
            "        status\n"
            "        spread = stddev(amount)\n"
            "        score_spread = stddev(orders.score)\n"
            "    qualify:\n"
            "        spread > 1.0\n"
            "table ratio_spread:\n"
            "    from readings\n"
            "    select:\n"
            "        spread = stddev(ratio)\n"
        ).replace("stddev(", f"{function}(")
    )
    result = analyze(script)

    assert _errors(result) == []
    grouped, plain = script.definitions[-2], script.definitions[-1]
    assert isinstance(grouped, (QueryDef, TableDef))
    assert isinstance(plain, (QueryDef, TableDef))
    for relation, names in (
        (grouped, ("spread", "score_spread")),
        (plain, ("spread",)),
    ):
        fields = result.model.relation_row_schemas[relation].fields
        for name in names:
            _assert_field(fields[name], "Float", EffectiveNullability.NULLABLE)


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (
            "    select:\n        x = stddev(price)\n",
            (
                "PIE-S2314",
                "Aggregate function stddev expects Int or Float field argument, "
                "got Decimal",
            ),
        ),
        (
            "    select:\n        x = stddev(status)\n",
            (
                "PIE-S2314",
                "Aggregate function stddev expects Int or Float field argument, "
                "got Text",
            ),
        ),
        (
            "    select:\n        x = stddev()\n",
            ("PIE-S2309", "Aggregate function stddev expects 1 arguments, got 0"),
        ),
        (
            "    select:\n        x = stddev(amount, score)\n",
            ("PIE-S2309", "Aggregate function stddev expects 1 arguments, got 2"),
        ),
        (
            "    select:\n        stddev(amount)\n",
            ("PIE-S2313", "Aggregate stddev() projection requires an explicit alias"),
        ),
        (
            "    select:\n        x = stddev(sum(amount))\n",
            ("PIE-S2311", "Nested aggregate sum() is not supported"),
        ),
        (
            "    select:\n        x = stddev(amount) if True else 1.0\n",
            (
                "PIE-S2310",
                "Aggregate composition requires scalar calls or arithmetic over direct aggregates, group keys and literals; invalid composition around stddev(); select the stddev() under a name in one query, then compute with that name in another that reads it with `from`",
            ),
        ),
        *(
            (
                body,
                (
                    "PIE-S2315",
                    "Aggregate function stddev requires a direct field argument; "
                    "expression arguments are not supported yet",
                ),
            )
            for body in (
                "    select:\n        x = stddev(amount + 1)\n",
                "    select:\n        x = stddev(1)\n",
                "    let w = amount\n    select:\n        x = stddev(w)\n",
            )
        ),
        *(
            (
                "    group by status\n    select:\n        status\n"
                f"        x = stddev(amount)\n    {clause}:\n"
                "        stddev(amount) > 1.0\n",
                (
                    "PIE-S2308",
                    f"Aggregate stddev() is not allowed in {clause} clause; use it "
                    "only as a direct aliased select projection",
                ),
            )
            for clause in ("having", "qualify")
        ),
    ],
)
@pytest.mark.parametrize("function", SPREADS)
def test_stddev_misuse_keeps_the_aggregate_diagnostics(
    body: str, expected: tuple[str, str], function: str
) -> None:
    """Each of `stddev`, `variance`, `pvariance` and `pstdev` refuses a
    Decimal, a misplaced or composed call, an expression and a `let` name with
    the diagnostics of every aggregate, under its own name."""
    body = body.replace("stddev(", f"{function}(")
    code, message = expected
    result = analyze(_parse(SOURCE_PREFIX + "table t:\n    from orders\n" + body))

    assert _errors(result) == [(code, message.replace("stddev", function))]


def test_median_and_quantile_of_an_int_or_float_field_are_a_nullable_float() -> None:
    """`median(x)` and `quantile(x, q)` interpolate the non-None Int or Float
    values (pandas `Series.median` and `Series.quantile`), None for no value."""
    script = _parse(
        SOURCE_PREFIX + "type Ratio = Float\n"
        "shape Reading:\n"
        "    ratio: Ratio\n"
        'source readings: Reading = postgres.table("readings")\n'
        "table by_status:\n"
        "    from orders\n"
        "    group by status\n"
        "    select:\n"
        "        status\n"
        "        middle = median(amount)\n"
        "        high = quantile(orders.score, 0.9)\n"
        "    having:\n"
        "        middle > 1.0\n"
        "table ratio_spread:\n"
        "    from readings\n"
        "    select:\n"
        "        low = quantile(ratio, 0.0)\n"
        "        top = quantile(ratio, 1.0)\n"
        "        middle = median(ratio)\n"
    )
    result = analyze(script)

    assert _errors(result) == []
    grouped, plain = script.definitions[-2], script.definitions[-1]
    assert isinstance(grouped, (QueryDef, TableDef))
    assert isinstance(plain, (QueryDef, TableDef))
    for relation, names in (
        (grouped, ("middle", "high")),
        (plain, ("low", "top", "middle")),
    ):
        fields = result.model.relation_row_schemas[relation].fields
        for name in names:
            _assert_field(fields[name], "Float", EffectiveNullability.NULLABLE)


_LITERAL_Q = (
    "PIE-S2104",
    "Invalid arguments for aggregate quantile: q must be a Float literal from "
    "0.0 to 1.0, written in the call, such as quantile(x, 0.9)",
)


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        *(
            (
                f"    select:\n        x = {call}\n",
                (
                    "PIE-S2314",
                    f"Aggregate function {call.split('(')[0]} expects Int or Float "
                    f"field argument, got {got}",
                ),
            )
            for call, got in (
                ("median(price)", "Decimal"),
                ("quantile(price, 0.5)", "Decimal"),
                ("median(status)", "Text"),
            )
        ),
        (
            "    select:\n        x = quantile(amount, 1.5)\n",
            (
                "PIE-S2104",
                "Invalid arguments for aggregate quantile: q 1.5 is outside 0.0 to "
                "1.0; write a fraction such as 0.9 for the 90th percentile",
            ),
        ),
        ("    select:\n        x = quantile(amount, 1)\n", _LITERAL_Q),
        ("    select:\n        x = quantile(amount, -0.5)\n", _LITERAL_Q),
        ("    select:\n        x = quantile(amount, score)\n", _LITERAL_Q),
        (
            "    let q = 0.5\n    group by status\n    select:\n        status\n"
            "        x = quantile(amount, q)\n",
            _LITERAL_Q,
        ),
        (
            "    select:\n        x = quantile(amount)\n",
            ("PIE-S2309", "Aggregate function quantile expects 2 arguments, got 1"),
        ),
        (
            "    select:\n        x = median(amount, 0.5)\n",
            ("PIE-S2309", "Aggregate function median expects 1 arguments, got 2"),
        ),
        *(
            (
                body,
                (
                    "PIE-S2315",
                    "Aggregate function median requires a direct field argument; "
                    "expression arguments are not supported yet",
                ),
            )
            for body in (
                "    select:\n        x = median(amount + 1)\n",
                "    let w = amount\n    select:\n        x = median(w)\n",
            )
        ),
        (
            "    select:\n        status\n        x = median(amount) "
            "window(partition by status)\n",
            (
                "PIE-S2103",
                "Aggregate window functions are not implemented: median; window "
                "aggregates are sum, count, avg, min and max",
            ),
        ),
    ],
)
def test_median_and_quantile_misuse_is_refused_with_a_hint(
    body: str, expected: tuple[str, str]
) -> None:
    result = analyze(_parse(SOURCE_PREFIX + "table t:\n    from orders\n" + body))

    assert _errors(result) == [expected]


def test_a_quantile_fraction_error_is_located_at_the_fraction() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table t:\n    from orders\n    select:\n"
            "        x = quantile(amount, 2.0)\n"
        )
    )

    [error] = result.diagnostics
    assert (error.location.line, error.location.column) == (10, 30)
    assert (error.location.end_line, error.location.end_column) == (10, 33)


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
