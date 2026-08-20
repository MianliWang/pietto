from __future__ import annotations

import pytest

from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import analyze

SOURCE_PREFIX = (
    "shape Order:\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    customer_id: Text\n"
    "    status: Text not null\n"
    "    region: Text not null\n"
    'source orders: Order is postgres.table("orders")\n'
)


def _errors(source: str) -> list[str]:
    parsed = parse_source(source, path="phase37-slice6-hardening.pietto")
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    result = analyze(parsed.ast)
    return [
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _aggregate_projection(projection: str) -> str:
    return (
        SOURCE_PREFIX + "table aggregate_hardening:\n"
        "    from orders\n"
        "    select:\n"
        f"        {projection}\n"
    )


@pytest.mark.parametrize(
    "projection",
    [
        "value = count(count())",
        "value = sum(avg(amount))",
        "value = avg(sum(amount))",
        "value = min(max(amount))",
        "value = max(min(amount))",
        "value = count_distinct(lower(avg(status)))",
    ],
)
def test_nested_aggregates_remain_rejected_with_existing_diagnostic(
    projection: str,
) -> None:
    assert _errors(_aggregate_projection(projection)) == ["PIE-S2311"]


@pytest.mark.parametrize(
    "projection",
    [
        "value = sum(amount) + 1",
        "value = count(amount) + 1",
        "value = count_distinct(customer_id) + 1",
        "value = min(amount) + 1",
        "value = lower(min(amount))",
    ],
)
def test_aggregate_projection_composition_remains_rejected(
    projection: str,
) -> None:
    assert _errors(_aggregate_projection(projection)) == ["PIE-S2310"]


def test_invalid_aggregate_contexts_keep_existing_diagnostics() -> None:
    where_source = (
        SOURCE_PREFIX + "table invalid_where:\n"
        "    from orders\n"
        "    where sum(amount) > 0\n"
        "    select:\n"
        "        amount\n"
    )
    satisfying_source = (
        SOURCE_PREFIX + "table invalid_satisfying:\n"
        "    from orders\n"
        "    select:\n"
        "        total = sum(amount)\n"
        "    satisfying:\n"
        "        sum(amount) > 0\n"
    )
    grouped_order_source = (
        SOURCE_PREFIX + "table invalid_grouped_order:\n"
        "    from orders\n"
        "    group by:\n"
        "        region\n"
        "    select:\n"
        "        region\n"
        "        total = sum(amount)\n"
        "    order by:\n"
        "        sum(amount)\n"
    )

    assert _errors(where_source) == ["PIE-S2308"]
    assert _errors(satisfying_source) == ["PIE-S2308"]
    assert _errors(grouped_order_source) == ["PIE-S2321"]


@pytest.mark.parametrize(
    "projection",
    [
        "count()",
        "sum(amount)",
        "avg(amount)",
        "count_distinct(customer_id)",
        "min(amount)",
        "max(amount)",
    ],
)
def test_direct_aggregate_projections_remain_alias_required(
    projection: str,
) -> None:
    assert _errors(_aggregate_projection(projection)) == ["PIE-S2313"]


@pytest.mark.parametrize(
    "projection",
    [
        "value = count(1)",
        "value = count_distinct(amount + tax)",
        "value = min(amount + tax)",
        "value = max(amount + tax)",
    ],
)
def test_phase37_expression_widening_candidates_remain_deferred(
    projection: str,
) -> None:
    assert _errors(_aggregate_projection(projection)) == ["PIE-S2315"]
