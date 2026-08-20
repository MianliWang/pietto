from __future__ import annotations

import pytest

from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import analyze


SOURCE_PREFIX = (
    "shape Order:\n"
    "    amount: Int not null\n"
    'source orders: Order is postgres.table("orders")\n'
)


@pytest.mark.parametrize(
    "projection",
    (
        "value = sum(1)",
        "value = sum(1 + 2)",
        "value = avg(1)",
        "value = count(1)",
        "value = count_distinct(1)",
        "value = min(1)",
        "value = max(1)",
    ),
)
def test_literal_only_aggregate_arguments_currently_fail_closed(
    projection: str,
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table aggregate_stats:\n"
            "    from orders\n"
            "    select:\n"
            f"        {projection}\n"
        )
    )
    assert [
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ] == ["PIE-S2315"]


def _parse(source: str):
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast
