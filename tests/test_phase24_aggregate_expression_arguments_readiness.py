from __future__ import annotations

from pietto.parser_api import parse_source
from pietto.semantic import analyze

SOURCE_PREFIX = (
    "shape Order:\n"
    "    amount: Decimal not null\n"
    "    score: Float not null\n"
    "    customer_id: UUID not null\n"
    'source orders: Order is postgres.table("orders")\n'
)


def test_aggregate_expression_arguments_remain_accepted() -> None:
    result = _analyze("total = sum(amount + amount)")

    assert [diagnostic.code for diagnostic in result.diagnostics] == []


def test_direct_field_aggregate_vocabulary_remains_accepted() -> None:
    result = _analyze("total = sum(amount)")

    assert [diagnostic.code for diagnostic in result.diagnostics] == []


def _analyze(projections: str):
    parsed = parse_source(
        SOURCE_PREFIX
        + "table totals:\n    from orders\n    select:\n        "
        + projections.replace("\n", "\n        ")
        + "\n"
    )
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    return analyze(parsed.ast)
