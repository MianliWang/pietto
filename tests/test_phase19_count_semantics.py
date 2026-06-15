from __future__ import annotations

import pytest

from pietto.ast_nodes import QueryDef, Script, TableDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import (
    EffectiveNullability,
    SemanticResult,
    TypeKind,
    analyze,
)
from pietto.semantic.catalog import BUILTIN_FUNCTIONS

SOURCE_PREFIX = (
    "shape Order:\n"
    "    status: Text not null\n"
    "    amount: Int not null\n"
    'source orders: Order is postgres.table("orders")\n'
)


@pytest.mark.parametrize("relation_kind", ["table", "query"])
def test_direct_aliased_count_projection_is_semantically_accepted(
    relation_kind: str,
) -> None:
    script = _parse(
        SOURCE_PREFIX + f"{relation_kind} paid_order_stats:\n"
        "    from orders\n"
        '    where status == "paid"\n'
        "    select:\n"
        "        total = count()\n"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]
    field = schema.fields["total"]
    expression = relation.select_items[0].expression
    value_type = result.model.expression_value_types[expression]

    assert _errors(result) == []
    assert list(schema.fields) == ["total"]
    assert field.resolved_type.kind is TypeKind.BUILTIN
    assert field.resolved_type.name == "Int"
    assert field.nullability is EffectiveNullability.NON_NULL
    assert value_type.resolved_type.name == "Int"
    assert value_type.nullability is EffectiveNullability.NON_NULL


def test_count_sum_and_avg_are_not_scalar_builtin_functions() -> None:
    assert "count" not in BUILTIN_FUNCTIONS
    assert "sum" not in BUILTIN_FUNCTIONS
    assert "avg" not in BUILTIN_FUNCTIONS


@pytest.mark.parametrize(
    ("projection", "expected_message"),
    [
        ("revenue = sum(amount)", "Unknown function: sum"),
        ("average = avg(amount)", "Unknown function: avg"),
    ],
)
def test_sum_and_avg_remain_unknown_functions(
    projection: str,
    expected_message: str,
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            f"        {projection}\n"
        )
    )

    assert _errors(result) == [("PIE-S2103", expected_message)]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        total = count(amount)\n",
            (
                "PIE-S2309",
                "Aggregate function count expects 0 arguments, got 1",
            ),
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    where count() > 0\n"
            "    select:\n"
            "        status\n",
            (
                "PIE-S2308",
                "Aggregate count() is not allowed in where clause; "
                "use it only as a direct aliased select projection",
            ),
        ),
        (
            "shape Order:\n"
            "    amount: Int not null\n"
            "    check has_rows:\n"
            "        count() > 0\n",
            (
                "PIE-S2308",
                "Aggregate count() is not allowed in shape check; "
                "use it only as a direct aliased select projection",
            ),
        ),
        (
            "derive total() -> Int not null:\n    count()\n",
            (
                "PIE-S2308",
                "Aggregate count() is not allowed in derive body; "
                "use it only as a direct aliased select projection",
            ),
        ),
        (
            "shape Order:\n    total: Int not null derive count()\n",
            (
                "PIE-S2308",
                "Aggregate count() is not allowed in field derive body; "
                "use it only as a direct aliased select projection",
            ),
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        status\n"
            "    order by:\n"
            "        count()\n",
            (
                "PIE-S2308",
                "Aggregate count() is not allowed in order by; "
                "use it only as a direct aliased select projection",
            ),
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        total = count() + 1\n",
            (
                "PIE-S2310",
                "Aggregate projection must be a direct aggregate call; "
                "composition around count() is deferred",
            ),
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        total = count(count())\n",
            ("PIE-S2311", "Nested aggregate count() is not supported"),
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        total = count(lower(count()))\n",
            ("PIE-S2311", "Nested aggregate count() is not supported"),
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        total = lower(count())\n",
            (
                "PIE-S2310",
                "Aggregate projection must be a direct aggregate call; "
                "composition around count() is deferred",
            ),
        ),
        (
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n",
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
            "        count()\n",
            (
                "PIE-S2313",
                "Aggregate count() projection requires an explicit alias",
            ),
        ),
    ],
)
def test_count_aggregate_diagnostics(
    source: str,
    expected: tuple[str, str],
) -> None:
    result = analyze(_parse(source))

    assert _errors(result) == [expected]


@pytest.mark.parametrize(
    "projection",
    [
        "total = count(amount)",
        "total = count() + 1",
        "total = count(count())",
    ],
)
def test_invalid_count_projection_aliases_keep_unknown_schema(
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
    field = result.model.relation_row_schemas[relation].fields["total"]

    assert field.resolved_type.kind is TypeKind.UNKNOWN
    assert field.nullability is EffectiveNullability.UNKNOWN


def test_mixed_count_projection_does_not_publish_precise_count_schema() -> None:
    script = _parse(
        SOURCE_PREFIX + "table paid_order_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert schema.fields["status"].resolved_type.name == "Text"
    assert schema.fields["total"].resolved_type.kind is TypeKind.UNKNOWN
    assert schema.fields["total"].nullability is EffectiveNullability.UNKNOWN


def test_count_with_unknown_argument_suppresses_wrong_arity_cascade() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table paid_order_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        total = count(missing)\n"
        )
    )

    assert _errors(result) == [("PIE-S2102", "Unknown field: missing")]


def _parse(source: str, *, path: str | None = None) -> Script:
    result = parse_source(source, path=path)
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
