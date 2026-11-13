### An asof JOIN beside a FULL JOIN in seven MySQL single files

Single-file `emit-sql --dialect mysql` now emits an asof JOIN in a relation
with a FULL JOIN, which MySQL emulates with UNION ALL, in a file that is,
byte for byte, one of seven forms of the Phase77 qualification pack, which
pairs PostgreSQL 18.6 with MySQL 8.4.12, with only its names changed. One of
them is:

```text
shape Order:
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

source orders: Order = mysql.table("shop.orders")
source prices: Price = mysql.table("shop.prices")
source prices_on: PriceOn = mysql.table("shop.prices_on")
source prices3: Price3 = mysql.table("shop.prices3")
source prices_id: PriceId = mysql.table("shop.prices_id")
source prices_two: PriceTwo = mysql.table("shop.prices_two")
source prices_none: PriceNone = mysql.table("shop.prices_none")
source rates: Rate = mysql.table("shop.rates")
source prices_keyed: PriceKeyed = mysql.table("shop.prices_keyed")

table price_table:
    from prices
    select product_id = prices.product_id, valid_from = prices.valid_from

query q:
    from orders
    let p2 = prices_id
    full join p2 on orders.id == p2.id
    let price = prices
    asof left join price on orders.product_id == price.product_id and orders.ordered_at >= price.valid_from
    let p3 = prices_id
    full join p3 on orders.id == p3.id
    select order_id = orders.id, c = price.amount_cents
```

- The other six files hold the same shapes, relationship, sources and
  table, and one query `q` that reads `from orders` and then has:
  - `let p2 = prices_id`, `full join p2 on orders.id == p2.id`,
    `let price = prices` and `asof left join price on orders.product_id ==
    price.product_id and orders.ordered_at >= price.valid_from`, or the
    same with `asof inner join`;
  - `let price = prices`, that asof left or inner join, `let p2 =
    prices_id` and `full join p2 on orders.id == p2.id`;
  - the FULL JOIN on `p2`, `let price = prices` and the asof inner join,
    then `select order_id = orders.id, full_id = p2.id, c =
    price.amount_cents`, or, with `let p3 = prices_id` and `full join p3 on
    orders.id == p3.id` after it, `select order_id = orders.id,
    first_full_id = p2.id, second_full_id = p3.id, c = price.amount_cents`.

  The other queries end with `select order_id = orders.id, c =
  price.amount_cents`.
- The SQL is the FULL JOIN emulation with the asof JOIN's `LATERAL` latest
  row: an asof JOIN after a FULL JOIN reads the `__pietto_full` derived-table
  ports, and an earlier one is written in each UNION ALL branch, whose
  right-only branch tests the row it reads for NULL. The branches choose the
  same latest row only while the source's declared unique holds. PostgreSQL
  SQL is unchanged.
- A name (of a shape, field, constraint, relationship or its parameter,
  source, table, query, binding or label, or a part of a `mysql.table`
  locator) is an ASCII identifier of at most 63 bytes that does not start
  with `__pietto` in any case. Two names are equal ignoring case exactly
  when the names they replace are, as `Price` and `price` are, and each
  locator is two names joined by a dot. Empty lines and the final newline do
  not count; a comment, a line of spaces, other spacing, a carriage return, a
  byte order mark, another clause or another definition does.
- Only single-file `emit-sql --dialect mysql`, with text or JSON output,
  pairs a file. Every other single file keeps PIE-B1000 with its whole
  `0.1.11` output, and so does a paired file whose emission does not give
  its form's SQL, names aside. A FULL JOIN whose `on` reads the asof JOIN's
  row, such as `full join p2 on price.product_id == p2.id` after it, stays
  refused.
- The native qualification passed on 2026-11-13: in one run of each half of
  the pack, PostgreSQL 18.6 and MySQL 8.4.12, the seven files and the asof
  JOIN alone, which `0.1.11` already emits, matched the expected rows on
  both databases, and the MySQL half's refusal control, that FULL JOIN whose
  `on` reads the asof row, kept its `0.1.11` refusal. The runs,
  PostgreSQL `20261113T141451Z-20218a248bc183f4b57d4402` (verdict `pass`
  true, no reason) and MySQL `wave-a-mysql-20261113T141451Z` (acceptance
  `pass` true, no reason), bound this change as first committed on the
  `0.1.11` release commit (tree `bc4c08f8`). D77.50 carries them to the
  commit that integrates this change: the documents both halves' compile
  steps export, the 83 forms of the PostgreSQL pack and the nine MySQL
  files, are byte-identical there (sha256, first 16 digits, the same on
  both sides: `b523f386dfc68ddd` and `93336282f3619e97`).

Changed diagnostics (programs refused in `0.1.11`; no accepted program
changes):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1000 | single file, `emit-sql --dialect mysql`, one of the seven files above with only its names changed | `MySQL SQL emission is not implemented for RelationIR: <name>. MySQL has no ASOF JOIN in a relation with a FULL JOIN yet; emit with --dialect postgres` | none: the file emits |
