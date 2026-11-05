"""Sources of the backward asof JOIN: the canonical example and its variants.

`CANONICAL` is the style example; `asof_query` builds one query over the
shared shapes, whose `price` input is `prices` unless `let` names another.
"""

from __future__ import annotations

CANONICAL = """shape Order:
    id: Int
    product_id: Int
    ordered_at: Timestamp

shape Price:
    product_id: Int
    valid_from: Timestamp
    amount_cents: Int
    price_key = unique(product_id, valid_from)

source orders: Order = postgres.table("shop.orders")

source prices: Price = postgres.table("shop.prices")

query order_prices:
    from orders
    let price = prices
    asof left join price on orders.product_id == price.product_id and orders.ordered_at >= price.valid_from
    select order_id = orders.id, price_cents = price.amount_cents
"""

SHAPES = """shape Order:
    id: Int
    product_id: Int
    region: Text
    ordered_at: Timestamp
    ordered_on: Date
    week_start: Timestamp
    score: Float
    amount: Int

shape Price:
    product_id: Int
    region: Text
    valid_from: Timestamp
    valid_to: Timestamp
    valid_on: Date
    amount_cents: Int
    score: Float
    price_key = unique(product_id, valid_from)

shape PriceOn:
    product_id: Int
    valid_on: Date
    valid_from: Timestamp
    amount_cents: Int
    on_key = unique(product_id, valid_on)

shape Price3:
    product_id: Int
    region: Text
    valid_from: Timestamp
    amount_cents: Int
    p3_key = unique(product_id, region, valid_from)

shape PriceId:
    id: Int
    product_id: Int
    valid_from: Timestamp
    id_key = unique(id)

shape PriceTwo:
    id: Int
    product_id: Int
    region: Text
    valid_from: Timestamp
    a_key = unique(id)
    b_key = unique(product_id, region, valid_from)

shape PriceNone:
    product_id: Int
    valid_from: Timestamp

shape Rate:
    valid_from: Timestamp
    amount_cents: Int
    rate_key = unique(valid_from)

shape PriceKeyed:
    id: Int
    product_id: Int
    valid_from: Timestamp
    price_key = unique(id)

relationship order_price(o: Order, p: Price):
    o.product_id == p.product_id

source orders: Order = {connector}.table("shop.orders")
source prices: Price = {connector}.table("shop.prices")
source prices_on: PriceOn = {connector}.table("shop.prices_on")
source prices3: Price3 = {connector}.table("shop.prices3")
source prices_id: PriceId = {connector}.table("shop.prices_id")
source prices_two: PriceTwo = {connector}.table("shop.prices_two")
source prices_none: PriceNone = {connector}.table("shop.prices_none")
source rates: Rate = {connector}.table("shop.rates")
source prices_keyed: PriceKeyed = {connector}.table("shop.prices_keyed")

table price_table:
    from prices
    select product_id = prices.product_id, valid_from = prices.valid_from
"""

KEY = "orders.product_id == price.product_id"
TIME = "orders.ordered_at >= price.valid_from"
# The line of the JOIN in `asof_query`.
JOIN_LINE = SHAPES.count("\n") + 5


def asof_query(
    join: str,
    *,
    select: str = "select order_id = orders.id, c = price.amount_cents",
    let: str = "let price = prices",
    after: str = "",
    connector: str = "postgres",
) -> str:
    """One query `q`: FROM orders, the `let`, the JOIN line, ``after`` lines,
    then ``select``."""

    return SHAPES.format(connector=connector) + (
        f"\nquery q:\n    from orders\n    {let}\n    {join}\n{after}    {select}\n"
    )


def project_contract(target: str = "postgres") -> str:
    """The emission contract of `CANONICAL`'s two sources, in schema ``shop``."""

    import json

    pg = target == "postgres"
    fields = {
        "orders": ("id", "product_id", "ordered_at"),
        "prices": ("product_id", "valid_from", "amount_cents"),
    }

    def representation(name: str) -> dict[str, object]:
        if name in {"ordered_at", "valid_from"}:
            return {
                "storage": {
                    "kind": "pg_timestamp" if pg else "my_datetime",
                    "fractional_seconds": 6,
                },
                "nullable": False,
                "domain": {"kind": "timestamp"},
            }
        return {
            "storage": {"kind": "pg_int8" if pg else "my_bigint"},
            "nullable": False,
            "domain": {"kind": "int_range", "min": "0", "max": "10000000"},
        }

    environment = {
        "client_encoding": "UTF8" if pg else "utf8mb4",
        "operator_environment": "builtin_only",
        "identifier_case": "quoted_exact" if pg else "lower_case_table_names=0",
    }
    return json.dumps(
        {
            "format": "pietto.emission-contract.v1",
            "target": {"family": target, "release": "18.6" if pg else "8.4.12"},
            "sources": [
                {
                    "selector": {"module": "main.pietto", "kind": "source", "name": n},
                    "relation": {"namespace": "shop", "name": n},
                    "scan": "relation_rows",
                    "fields": [
                        {
                            "ordinal": i,
                            "name": f,
                            "column": f,
                            "representation": representation(f),
                        }
                        for i, f in enumerate(names)
                    ],
                    "premises": [
                        {"key": "row_domain_matches", "scope": "source", "value": True},
                        {"key": "read_only_object", "scope": "source", "value": True},
                    ],
                }
                for n, names in fields.items()
            ],
            "environment": [
                {"key": key, "scope": "statement", "value": value}
                for key, value in environment.items()
            ],
        }
    )
