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


def _parser_codes(source: str) -> list[str]:
    result = parse_source(source, path="phase37-slice7-deferral.pietto")
    return [diagnostic.code for diagnostic in result.diagnostics]


def _semantic_error_codes(source: str) -> list[str]:
    parsed = parse_source(source, path="phase37-slice7-deferral.pietto")
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
        SOURCE_PREFIX + "table aggregate_modifier_deferral:\n"
        "    from orders\n"
        "    select:\n"
        f"        {projection}\n"
    )


@pytest.mark.parametrize(
    "projection",
    [
        "value = count(distinct customer_id)",
        "value = sum(amount) filter where amount > 0",
        "value = sum(amount) FILTER (WHERE amount > 0)",
        "value = sum(amount) over (region)",
        "value = sum(amount) within group (order by amount)",
        "value = count(*)",
    ],
)
def test_sql_like_aggregate_modifier_syntax_remains_parser_rejected(
    projection: str,
) -> None:
    codes = _parser_codes(_aggregate_projection(projection))

    assert "PIE-P1000" in codes


def test_semantic_context_and_modifier_like_argument_boundaries_are_locked() -> None:
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

    assert _semantic_error_codes(satisfying_source) == ["PIE-S2308"]
    assert _semantic_error_codes(grouped_order_source) == ["PIE-S2321"]
    assert _semantic_error_codes(_aggregate_projection("value = sum(amount, tax)")) == [
        "PIE-S2309"
    ]
    assert _semantic_error_codes(
        _aggregate_projection("value = count_distinct(customer_id, status)")
    ) == ["PIE-S2309"]
