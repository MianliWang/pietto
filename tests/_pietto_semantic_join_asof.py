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
