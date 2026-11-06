"""SQL of the conditional count and sum of a group (Phase73 S02):
`sum(1 for o in group if TEST)` and `sum(o.f for o in group if TEST)`."""

from __future__ import annotations

import pytest

from pietto.ir import build_ir
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.sql import SqlResult, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

SOURCE = """shape Order:
    id: Int
    customer_id: Int | None
    amount: Int
    paid: Bool | None
    status: Text | None
source orders: Order = {target}.table("shop.orders")
query paid_per_customer:
    from orders
    group by customer_id
    select:
        customer_id
        paid_orders = {call}
    having:
        paid_orders > 1
    order by paid_orders desc
query paid_overall:
    from orders
    select:
        paid_orders = {call}
"""
COUNT = "sum(1 for o in group if o.paid)"
SUM = 'sum(o.amount for o in group if o.status == "refunded" or o.amount > 10)'


def _emit(target: str, call: str) -> SqlResult:
    parsed = parse_source(SOURCE.format(target=target, call=call))
    assert parsed.ast is not None and parsed.diagnostics == ()
    semantic = analyze(parsed.ast)
    assert semantic.diagnostics == () and semantic.script is not None
    lowered = build_ir(semantic.script, semantic.model)
    assert lowered.ir is not None, lowered.diagnostics
    emit = emit_postgres_sql if target == "postgres" else emit_mysql_sql
    return emit(lowered.ir)


@pytest.mark.parametrize(
    ("call", "value"),
    [
        (COUNT, 'COUNT(CASE WHEN "paid" THEN 1 END)'),
        (
            SUM,
            "COALESCE(CAST(SUM(CASE WHEN (\"status\" = 'refunded') OR "
            '("amount" > 10) THEN CAST("amount" AS pg_catalog.int8) END) AS '
            "pg_catalog.int8), 0)",
        ),
    ],
)
def test_postgres_counts_and_adds_the_rows_whose_test_is_true(
    call: str, value: str
) -> None:
    """The count counts the rows whose test is True; the sum adds their
    non-None values exactly, narrowed to bigint by the checked CAST, 0 for no
    such row. A None test takes no CASE branch. HAVING and ORDER BY restate
    the aggregate, as for every grouped output."""
    result = _emit("postgres", call)

    assert result.diagnostics == ()
    assert [artifact.sql for artifact in result.artifacts] == [
        'SELECT\n    "customer_id" AS "customer_id",\n'
        f'    {value} AS "paid_orders"\n'
        'FROM "shop"."orders"\nGROUP BY\n    "customer_id"\n'
        f"HAVING\n    {value} > 1\nORDER BY\n    {value} DESC",
        f'SELECT\n    {value} AS "paid_orders"\nFROM "shop"."orders"',
    ]


def test_mysql_refuses_the_conditional_count() -> None:
    """The Phase74 MySQL catch-up owns the conditional count."""
    result = _emit("mysql", COUNT)

    assert result.artifacts == ()
    assert [(item.code, item.message) for item in result.diagnostics] == [
        (
            "PIE-B1000",
            f"MySQL SQL emission is not implemented for RelationIR: {name}. "
            "MySQL has no conditional count yet; emit with --dialect postgres",
        )
        for name in ("paid_per_customer", "paid_overall")
    ]


def test_mysql_refuses_the_conditional_sum() -> None:
    """MySQL SUM of an Int is DECIMAL, not a checked bigint (Phase74 MySQL catch-up)."""
    result = _emit("mysql", SUM)

    assert result.artifacts == ()
    assert [(item.code, item.message) for item in result.diagnostics] == [
        (
            "PIE-B1000",
            f"MySQL SQL emission is not implemented for RelationIR: {name}. "
            "MySQL conditional sum of an Int argument is not supported",
        )
        for name in ("paid_per_customer", "paid_overall")
    ]
