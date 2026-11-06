# Pietto style

This page shows one way to write each thing. It is written for people who know
Python and only a little SQL. The [language reference](language.md) lists the
other accepted forms and every rule; you do not need them to start.
[A worked example](worked-example.md) puts these forms together in one
report.

Check a file in strict mode, which also refuses a source without a shape and
a computed output without a name:

```bash
pietto check --check-mode strict shop.pietto
```

Each example below is a complete file that you can copy and check. It passes
that check with no diagnostic, unless the text says that it shows one.

## Documentation examples

`tests/test_repo_docs_examples.py` checks every fenced `pietto` block of
`README.md`, `docs/language.md`, `docs/style.md` and `docs/worked-example.md`
as one complete file, as `pietto check --check-mode strict` checks it. A
block whose opening fence line is only the language word must report no
diagnostic. When an example shows
diagnostics, or uses a form that a single file refuses, such as a project-only
form, write the codes it reports after the language word, in report order:
`pietto PIE-S2105` on the fence line. A clause or grammar fragment that is not
a complete file uses a `text` fence. Renderers show only the language word, so
readers do not see the codes. Each example is also already formatted: `pietto
fmt` leaves it unchanged.

## A complete file

```pietto
# shop.pietto: the ten biggest paid orders from Europe
enum Status: pending, paid, shipped

shape Customer:
    id: Int
    name: Text
    region: Text | None

shape Order:
    id: Int
    customer_id: Int
    status: Status
    amount_cents: Int

source customers: Customer = postgres.table("shop.customers")

source orders: Order = postgres.table("shop.orders")

query big_paid_orders:
    from orders
    let customer = customers
    inner join customer on orders.customer_id == customer.id
    where orders.status == "paid" and customer.region == "EU"
    select order_id = orders.id, customer_name = customer.name, amount_cents
    order by amount_cents desc
    limit 10
```

A file reads top to bottom: `enum` and `shape` describe values and rows,
`source` connects a shape to a database table, and `query` computes a result
from sources. `pietto emit-sql shop.pietto --dialect postgres` prints the SQL.

## Names

| What | Style | Examples |
| --- | --- | --- |
| `type`, `shape`, `enum` | CapWords, singular | `Order`, `Status` |
| `source` | snake_case, like its table | `orders`, `customers` |
| `query`, `def`, `relationship` | snake_case | `big_paid_orders`, `line_total`, `order_customer` |
| fields, `let` names and outputs | snake_case | `amount_cents`, `customer_name` |
| enum labels | as the database stores them | `paid` |

Types read like Python classes and everything else like Python variables and
functions. Write `True`, `False` and `None` as in Python, and strings with
double quotes.

## Write `query`

Use `query` for every result. `table` is an older declaration with the same
clauses; it remains for existing files.

Do not start a file with the older header lines such as `pietto 1` or
`mode checked`; choose the check mode on the command line.

## None and nullable fields

A bare type never holds None. Add `| None` to a field whose column may be NULL:

```pietto
shape Customer:
    id: Int  # never None
    name: Text  # never None
    email: Text | None  # may be None

source customers: Customer = postgres.table("customers")

query customers_without_email:
    from customers
    where email is None
    select id, name
```

A bare type is a promise about your data, and Pietto relies on it, for example
to prove that a JOIN cannot repeat rows. Write a bare type only for a column
that the database declares `NOT NULL`; when in doubt, write `| None`.

Test for None with `is None` and `is not None`. `email == None` is an error
(PIE-S2105), because SQL's `= NULL` is never true. This example shows that
error:

```pietto PIE-S2105
shape Customer:
    id: Int
    email: Text | None

source customers: Customer = postgres.table("customers")

query customers_without_email:
    from customers
    where email == None
    select id
```

`coalesce(email, "none")` gives a default for None. Older files wrote
`Text not null` and `Text nullable`; `pietto migrate` rewrites them.

## Clause order and names

A query writes its clauses in this order. Only `from` and `select` are
required:

```text
from orders                       # the input rows
let customer = customers          # name another input,
inner join customer on ...        # then join it
let total = price * quantity      # name a value
where ...                         # keep some rows
group by ...                      # one row per group
select ...                        # the outputs
having ...                        # keep some groups
order by ...                      # sort
limit ...                         # keep the first rows
```

Names flow down. A `let` name can be read by every later line, and `select` may
list it as an output. `having` and `order by` may also read the names that
`select` gives its outputs. Every `let` goes after `from` and the joins and
before `where`; a named window such as `let newest_first = window(order by id desc)`
is a `let` too:

```pietto
shape OrderLine:
    id: Int
    price_cents: Int
    quantity: Int

source order_lines: OrderLine = postgres.table("order_lines")

query biggest_lines:
    from order_lines
    let total_cents = price_cents * quantity
    where total_cents > 10_000
    select id, total_cents
    order by total_cents desc
```

```pietto
shape Order:
    id: Int
    customer_id: Int
    amount_cents: Int

source orders: Order = postgres.table("orders")

query frequent_customers:
    from orders
    group by customer_id
    select customer_id, orders_count = count(), spent_cents = sum(amount_cents)
    having orders_count >= 3
    order by spent_cents desc
```

`select` names outputs without `let`: `total_cents = price_cents * quantity`.
Give every computed output a name. If an output takes the name of an input
field but holds another value, `order by` with that name could mean either, so
it is an error (PIE-S2102); give the output another name. This example shows
that error:

```pietto PIE-S2102
shape OrderLine:
    id: Int
    quantity: Int

source order_lines: OrderLine = postgres.table("order_lines")

query doubled:
    from order_lines
    select id, quantity = quantity * 2
    order by quantity desc
```

### Ranking by a computed key

A window key is a name: an input field or a `let`. To order or partition by a
computed value, give it a name with `let` first; the `let` may call a `def`:

```pietto
shape Member:
    id: Int
    group_id: Int
    kind: Text
    review_year: Int
    level: Int

source members: Member = postgres.table("members")

def size_band(level: Int) -> Int: return 1 if level <= 2 else 2

query review_order:
    from members
    let off_year = review_year != 2024
    let band = size_band(level)
    let by_review = window(partition by group_id order by off_year, band, id)
    select:
        id, group_id, kind
        sheet_no = row_number() window by_review
        band_rank = dense_rank() window(partition by band order by level)
```

The same `let` key works in `qualify`. A window value is a whole `select:`
item: select it as its own column and compute from it in a later table or
query.

Not this:

- `window(order by review_year != 2024, id)`, `window(partition by lower(t))`:
  bind the key with `let` and name it (PIE-S2103, whose message ends
  ``; compute it in a `let` and name that `let` in the window``).
- `window(order by size_band(level), id)`: a `def` call inside `window(...)`
  (PIE-S2397); bind it with `let` too.
- `let k = 3`, `let k = 1 + 2` as a key: it orders nothing (PIE-S2103).
- `row_number() window(order by id) + 1`, `1 if c else dense_rank() window w`:
  a window inside a larger expression (PIE-P1000).
- a computed `let` key in a grouped window or a window over JOIN rows: key by
  fields there (PIE-S2103); and one that reads a project query parameter
  (PIE-S2355).
- single-file MySQL, a key `let` of computed Text (`let s = lower(t)`): emit
  with `--dialect postgres` (PIE-B1000).

### Totals beside each row: aggregate windows

`sum`, `count`, `avg`, `min` or `max` followed by `window(...)` puts the value
of a partition beside each of its rows and keeps every row. With `order by` in
the window the value is a running one, up to the current row:

```pietto
shape Ride:
    id: Int
    member_id: Int
    fee_cents: Int

source rides: Ride = postgres.table("rides")

query member_fees:
    from rides
    select:
        id, member_id, fee_cents
        member_cents = sum(fee_cents) window(partition by member_id)
        running_cents = sum(fee_cents) window(partition by member_id order by id)
```

In a project the argument is a field of the input. To total a computed value,
select it in an earlier query and read that query.

Not this:

- `sum(fee_cents * 2) window(...)`, or `sum(doubled) window(...)` over
  `let doubled = fee_cents * 2`, in a project (PIE-S2103, `Unsupported window
  computation for function sum: argument must be a direct field in a project`).
- `sum(fee_cents) over (partition by member_id)` (PIE-P1000, ``Unexpected
  'over'. Write a window function as `rank() window(order by ...)` or `rank()
  window name`, not OVER (...).``).
- `sum(fee_cents) window(partition by member_id) + 1`: a window inside a larger
  expression (PIE-P1000).
- project MySQL: emit with `--dialect postgres` (PIE-B1003).

## One line or a block

Write a clause on one line when it fits. Otherwise end it with `:` and put one
item per line:

```pietto
shape Order:
    id: Int
    status: Text
    region: Text
    coupon_code: Text | None
    amount_cents: Int

source orders: Order = postgres.table("orders")

query plain_orders:
    from orders
    where:
        status == "paid"
        coupon_code is None
        (region == "EU"
            or region == "NA")
    select:
        id
        region
        amount_cents
```

The lines of a `where:` block are joined with `and`. There is no `or` between
lines: write `or` inside one condition, and use parentheses to continue that
condition on the next line.

## Joining another input

Name the input with `let`, then join it and write the match in `on`:

```pietto
shape Customer:
    id: Int
    name: Text

shape Order:
    id: Int
    customer_id: Int | None

source customers: Customer = postgres.table("customers")

source orders: Order = postgres.table("orders")

query orders_with_customer:
    from orders
    let customer = customers
    left join customer on orders.customer_id == customer.id
    select order_id = orders.id, customer_name = customer.name
```

`left join` keeps every order; `customer.name` is None for an order without a
customer. `inner join` keeps only orders that match. Write `orders.id` and
`customer.id` when more than one input has the field.

When several queries use the same match, name it once with a `relationship`
and call it in `on`:

```pietto
shape Customer:
    id: Int
    name: Text

shape Order:
    id: Int
    customer_id: Int

source customers: Customer = postgres.table("customers")

source orders: Order = postgres.table("orders")

relationship order_customer(order: Order, customer: Customer): order.customer_id == customer.id

query orders_with_customer:
    from orders
    let customer = customers
    inner join customer on order_customer(orders, customer)
    select order_id = orders.id, customer_name = customer.name
```

A relationship also takes the rows of a table or query whose columns match
its shape by name and type; the call is written as for a source:

```pietto
shape Order:
    id: Int
    customer_id: Int

shape Customer:
    id: Int
    region_id: Int

source orders: Order = postgres.table("shop.orders")

source customers: Customer = postgres.table("shop.customers")

relationship order_customer(order: Order, customer: Customer): order.customer_id == customer.id

query active_customers:
    from customers
    where customers.region_id > 0
    select id, region_id

query result:
    from orders
    let buyer = active_customers
    left join buyer on order_customer(orders, buyer)
    select order_id = orders.id, region_id = buyer.region_id
```

To pass a source of another shape, select its columns in a query and pass
the query.

Not this (each is PIE-S2604 at the argument):

- a query without a column the shape needs: ``Unavailable row argument for
  relationship order_customer parameter customer: no column region_id``.
- a column of another type: ``...: column region_id is Text, field region_id
  is Int``.
- a column of type `Int | None` for a field of type `Int`: ``...: column
  region_id is Int | None, field region_id is Int``.
- a computed column, such as `region_id = customers.region_id + 1`, for a
  field of type `Int` (``...: column region_id is Int of unknown nullability,
  field region_id is Int``): write `coalesce(customers.region_id + 1, 0)`, or
  declare the field `Int | None`.
- a source of another shape with the same fields: ``Relationship
  order_customer parameter customer requires declared shape Customer; the
  actual row has a different shape identity``.

### Latest earlier row: `asof`

To take, for each order, the latest price at or before it, as pandas
`merge_asof` does, name the price source with `let`, then write the whole
asof JOIN on one line: the keys first, each with the earlier input on the
left, then one time test with `>=`:

```pietto
shape Order:
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
```

`price_cents` is None for an order without an earlier price; `asof inner join`
drops those orders. Declare the `unique(...)` that makes the latest row one
row; without it Pietto refuses the JOIN (PIE-S2386) instead of picking one.
Only `emit-sql --dialect postgres` writes an asof JOIN; MySQL refuses it.

Not this (each is refused with a hint):

- `left asof join price ...` or `asof join price ...`: write `asof left join`
  or `asof inner join`.
- `asof left join prices as p on ...`: first `let p = prices`.
- `asof left join price by product_id on ...`: match the keys in `on`.
- `price.valid_from <= orders.ordered_at`: write the earlier input first,
  `orders.ordered_at >= price.valid_from`.
- `orders.ordered_at > price.valid_from`: write `>=`.
- the `on` in parentheses or over several lines: one line, no parentheses.

`pietto fmt` keeps the JOIN on its one line and does not rewrite a refused
form.

### Totals over a JOIN that repeats rows: two levels

A JOIN repeats each order once per matching item, so `sum(orders.amount)`
over it would count an order's amount once per item. Add the totals in two
queries: the first groups by the order's key and gives one row per order,
the second reads `from` the first and adds those rows up:

```pietto
shape Order:
    id: Int
    customer_id: Int
    amount: Int
    order_key = unique(id)

shape Item:
    id: Int
    order_id: Int

source orders: Order = postgres.table("orders")

source items: Item = postgres.table("items")

query per_order:
    from orders
    let item = items
    left join item on item.order_id == orders.id
    group by orders.id, orders.customer_id, orders.amount
    select:
        id = orders.id
        customer_id = orders.customer_id
        amount = orders.amount
        lines = count(item.id)

query per_customer:
    from per_order
    group by customer_id
    select customer_id, revenue = sum(amount), lines = sum(lines)
```

Declare the order's key (`order_key = unique(id)`) and group the first query
by it: then each group is one order, and `count(item.id)` counts that order's
items. Put every other order field you need in the same `group by`.
`left join` keeps an order without items, with `lines` 0.

Not this: one query that joins the items and adds up `orders.amount` per
customer. It is refused (PIE-S2381), and the message names the two-level
route:

```pietto PIE-S2381
shape Order:
    id: Int
    customer_id: Int
    amount: Int
    order_key = unique(id)

shape Item:
    id: Int
    order_id: Int

source orders: Order = postgres.table("orders")

source items: Item = postgres.table("items")

query per_customer:
    from orders
    let item = items
    left join item on item.order_id == orders.id
    group by orders.customer_id
    select customer_id = orders.customer_id, revenue = sum(orders.amount)
```

In a project the same query is PIE-S2333, whose message names the remedies
but not the route; write the same two levels there.

Not these either (each is refused with PIE-S2381 too):

- the first query without `order_key = unique(id)`: nothing then proves that
  a group is one order, so `count(item.id)` may count an item twice.
- a second JOIN that also repeats rows, such as each order's payments, in a
  query that averages the items' `qty`, even when it groups by `orders.id`:
  group a first query by the item's key instead, then average `qty` in a
  query `from` it.

There is no DISTINCT repair afterwards: write the two levels.

## Does a matching row exist?

`any(... for ... in ...)` reads like Python's `any`. It is True when at least
one row matches, and `not any(...)` is True when none does:

```pietto
shape Customer:
    id: Int
    name: Text

shape Order:
    id: Int
    customer_id: Int

source customers: Customer = postgres.table("customers")

source orders: Order = postgres.table("orders")

query customers_with_orders:
    from customers
    where any(o.customer_id == customers.id for o in orders)
    select id, name

query customers_without_orders:
    from customers
    where not any(o.customer_id == customers.id for o in orders)
    select id, name
```

`any` adds no rows and no columns, so a customer with many orders still
appears once. It takes the place of SQL's `EXISTS` and of the older
`semi join` and `anti join`, which `pietto migrate` rewrites.

## Counting the rows that match

To count, per customer, the orders that are paid, and to add up their
amounts, use a generator over `group`:

```pietto
shape Order:
    id: Int
    customer_id: Int | None
    amount_cents: Int
    paid: Bool
    status: Text | None

source orders: Order = postgres.table("shop.orders")

query customer_order_summary:
    from orders
    group by customer_id
    select:
        customer_id
        orders_count = count()
        paid_orders = sum(1 for o in group if o.paid)
        paid_cents = sum(o.amount_cents for o in group if o.paid)
        refunded_orders = sum(1 for o in group if o.status == "refunded")
```

In a grouped query, `group` is the rows of the current group: the rows that
`from` and `where` keep and that have this key, each as often as it occurs,
the rows `count()` counts. `sum(1 for o in group if test)` counts the rows
whose test is True, and `sum(o.amount_cents for o in group if test)` adds
their `amount_cents`, an `Int` field. Both are 0, never None, when no row
matches; a test that is None is no match, and a None value adds nothing. Read
a field of the row as `o.paid`; besides `o`, the test reads only the
`group by` keys. A query with aggregates and no `group by` reads its whole
input as one group. `for o in orders` always means every row of `orders`, as
in `any(...)`, never the group. A `schema_version = 2` project takes both
too. A MySQL single file emits the count; MySQL emits no conditional sum
yet, and no project conditional count or sum.

Not this (each is refused with a hint):

- `sum(1 if paid else 0)`, `count_if(paid)`: write
  `sum(1 for o in group if o.paid)`.
- `sum(1 for o in orders if o.paid)` in a grouped query: `orders` is every
  row of `orders`; write `for o in group`.
- `count(1 for o in group if o.paid)`, `len(...)` or `max(...)` with a
  generator: only `sum` takes one.
- `sum(1 for o in group)` without `if`: write `count()`; and
  `sum(o.amount_cents for o in group)`: write `sum(amount_cents)`.
- `sum(amount_cents for o in group if paid)`: read the row's fields as
  `o.amount_cents` and `o.paid`.
- `any(o.paid for o in group)`: select `n = sum(1 for o in group if o.paid)`
  and test `n > 0` in `having`.
- a group generator over JOIN rows: join in one query, then group it in
  another that reads it with `from`.
- a `let` of the query in the test, a computed GROUP BY key included
  (`let k = id + 1` ... `if k > 2`): write the let's expression with member
  fields, `if o.id + 1 > 2`.

A test that reads no field, such as `if True`, is the same for every row:
test a member field. A single file checks and emits it, but project SQL
refuses it (PIE-B1003 `conditional_test_reads_no_field`).

`count(paid)` of a `Bool` field still counts every row whose `paid` is not
None, False included, and warns (PIE-S2388).

## Grouping by a collected list

In a `schema_version = 2` project on PostgreSQL, a collected list may be a
`group by` key, or a `select distinct` field, in a query that reads it with
`from` and has no JOIN, window or QUALIFY. Two lists are one key when
they have the same length and their children are equal in order, compared as
values (`1.0` and `1.00` are one key, so are `-0.0` and `0.0`); an empty list,
a list with one None child and a missing list are three different keys. The
collected let must end its `order by` in the fields of a `unique(...)` key of
its source, so that its rows never tie. A single file refuses this project form
(PIE-S2345, PIE-S2351, PIE-S2801):

```pietto PIE-S2345 PIE-S2351 PIE-S2801
shape Customer:
    id: Int

shape Order:
    id: Int
    customer_id: Int
    total: Int
    order_key = unique(id)

source customers: Customer = postgres.table("customers")

source orders: Order = postgres.table("orders")

query customer_baskets:
    let basket:
        capture customers
        from orders
        where orders.customer_id == customers.id
        select:
            total
        order by id
    from customers
    select:
        id
        totals = collect basket

query basket_counts:
    from customer_baskets
    group by totals
    select:
        totals
        customers = count()
```

Not this (each is refused with PIE-S2805):

- the same with `order by total`, whose rows may tie, or with a key whose
  fields may be None: rows that tie have no promised order, so the list
  would not be one value.
- `group by totals` or `select distinct` of `totals` beside a JOIN, a window
  or `qualify`: group in a query of its own that reads the list with `from`.
- `where totals == other`, `order by totals` or a set operation over
  `totals`: a list has no comparison or order.
- `select distinct` in the query that collects `totals = collect basket`:
  deduplicate in a later query.

MySQL refuses every collected list (PIE-B1003).

## Reading a row's collected list: `len`, `sum`, `any`

In a `schema_version = 2` project, a table or query that reads a relation
with a collected field (`name = collect r`) computes one value per row from
that row's own list. A single file refuses this project form, so the block
shows its codes:

```pietto PIE-S2345 PIE-S2351 PIE-S2801 PIE-S2334 PIE-S2334 PIE-S2334 PIE-S2334
shape Order:
    id: Int
    customer_id: Int | None
    amount_cents: Int
    paid: Bool

shape Customer:
    id: Int
    name: Text

source orders: Order = postgres.table("shop.orders")

source customers: Customer = postgres.table("shop.customers")

query customer_orders:
    let customer_order_rows:
        capture customers
        from orders
        where orders.customer_id == customers.id
        select id, amount_cents, paid
        order by id
    from customers
    select id, name, order_list = collect customer_order_rows

query customer_order_stats:
    from customer_orders
    select:
        id
        order_count = len(customer_orders.order_list)
        paid_count = sum(1 for o in customer_orders.order_list if o.paid)
        total_cents = sum(o.amount_cents for o in customer_orders.order_list)
        paid_cents = sum(o.amount_cents for o in customer_orders.order_list if o.paid)
        has_paid = any(o.paid for o in customer_orders.order_list)
```

- `len(c.xs)` is the number of elements. `sum(o.f for o in c.xs)` adds the
  `Int` field `f` of each element, and with `if TEST` only of the elements
  whose test is True; `sum(1 for o in c.xs if TEST)` counts those elements;
  `any(TEST for o in c.xs)` is whether some element's test is True.
- `for o in c.xs` always means the elements of this row's list `c.xs`; the
  body and the `if` test read only `o.field` and literals (a query parameter
  there is PIE-S2355). A single name after `in` is a relation or `group`,
  never a list, and `len` reads the list through its row too: write
  `len(c.xs)`, never `len(xs)`.
- A row with no list (after an outer JOIN) gives None for all of them; `[]`
  gives `0`, `0`, `False`; an element whose value or test is None adds
  nothing and matches nothing; a sum past 64 bits is an error.
- Write them in a SELECT item, a row `let` or the WHERE of a table or query
  without JOIN, GROUP BY, an aggregate, DISTINCT, a window or QUALIFY, and
  order or group by the output in a later table or query that reads it with
  `from`. A JOIN query selects the list as it is (`xs = p.xs`) for a later
  query to read; after a LEFT JOIN a row without a match has no list (None).

PostgreSQL emits them; MySQL refuses the `collect` they read (PIE-B1003).

Not this (each is refused with a hint):

- `count(c.xs)`, `len(o for o in c.xs)` or `sum(1 for o in c.xs)`: write
  `len(c.xs)`.
- `count(1 for o in c.xs if o.paid)`: write `sum(1 for o in c.xs if o.paid)`.
- `max(o.f for o in c.xs)` (also `min`, `avg`, `stddev`, `count_distinct`
  and `string_agg`) or another call with a list generator: only `sum` and
  `any` take one.
- `any(p for o in c.xs if q)`: write `any(p and q for o in c.xs)`.
- `sum(o.a + 1 for o in c.xs)` or `sum(o.a if o.p else 0 for o in c.xs)`:
  a list `sum` adds `1` or one field `o.f`; filter with `if` after the
  source.
- `sum(amount for o in c.xs)`, or a test such as `if id > 1` or
  `if c.id > 1`: the body and test read the element's fields as `o.amount`;
  test the row's own values outside the generator.
- `sum(o.paid for o in c.xs)` of a `Bool` field: count with
  `sum(1 for o in c.xs if o.paid)`; a list `sum` adds `Int` fields only.
- `len(xs)` or `for o in xs`: read the list through its row, `c.xs`.
- `len(c.xs)` in a JOIN query, a grouped or DISTINCT query, beside a window
  or QUALIFY, or in `order by` (PIE-S2805, whose suggestion names the route
  above).
- `len([o for o in c.xs])`: write the generator without brackets.

The exact texts are in the PIE-S2334, PIE-S2315, PIE-S2314, PIE-S2202,
PIE-S2301 and PIE-S2805 rows of [diagnostics](spec/diagnostics.md).

## Naming a fixed value: top-level constants

A single file names a fixed value once, at the top level, with its type:

```pietto
cutoff: Date = "2024-01-31"

min_amount: Float = 10.0

region: Text = "EU"
```

- One literal of the declared type: `True`/`False`, `10`/`-10`, `1.5`/`-1.5`,
  `"text"`; a `Date` is the Text literal `"YYYY-MM-DD"`, a `Timestamp` the Text
  literal `"YYYY-MM-DD HH:MM:SS"` (up to six fractional digits).
- Read it by its bare name like any value: `where created >= cutoff`,
  `as_of = cutoff`, `limit max_rows`.
- Change it without editing the file: `pietto emit-sql --dialect postgres
  --set cutoff=2024-02-29 orders.pietto` (also `check` and `explain`). The value
  is read as a literal of the declared type and emits the same SQL as writing
  it in the file. MySQL does not emit constants yet.
- `pietto fmt` keeps one blank line between top-level declarations, constants
  included.

Not this (each is refused with a hint or a diagnostic):

- `let cutoff = "2024-01-31"`, `const cutoff: Date = ...`, `cutoff = "..."`:
  write `cutoff: Date = "2024-01-31"` (PIE-P1000).
- `cutoff: Date = date("2024-01-31")`, `x: Float = Float(1)`, `x: Int = 1 + 2`,
  `x: Bool = None`: one literal of the type (PIE-S2391).
- `x: Decimal = 1`, `x: Int | None = 1`: a constant is `Bool`, `Int`, `Float`,
  `Text`, `Date` or `Timestamp`, without `| None` (PIE-S2391).
- a constant named like a field, let, output, def, parameter, relation or
  built-in function (`lower: Text = "x"`): give it a name of its own
  (PIE-S2391).
- `postgres.table(table_name)` with a constant `table_name`: a source names
  what it reads with a literal written there (PIE-S2391).
- `group by cutoff`, `order by cutoff`, an unnamed `select: cutoff`: a key reads
  a field or an output, and a SELECT item that only reads a constant names its
  output, `as_of = cutoff` (PIE-S2391).
- a constant in a project: give the query a header parameter (PIE-S2392); and
  `query q(cutoff: Date):` in a single file: write a constant (PIE-S2346).

## A project query's parameters

A project query parameter is declared with the type of the field it is
compared with; a Decimal one with that field's precision and scale (this
example is a project form, so a single file reports PIE-S2346 for each
parameter):

```pietto PIE-S2346 PIE-S2346 PIE-S2346
query recent(since: Timestamp, day: Date | None, floor: Decimal(9, 2)):
    from orders
    where since <= placed_at and order_day == day and amount >= floor
    select:
        id
```

The caller passes `datetime.datetime` (naive), `datetime.date`, `uuid.UUID`
and `decimal.Decimal` values: `parameters={"since": datetime(2024, 1, 1),
"day": date(2024, 1, 31), "floor": Decimal("10.00")}`.

Not this:

- `floor: Decimal`, `Decimal(9)`, `Decimal(2, 3)`, `Decimal(40, 35)`,
  `Decimal(p=9, s=2)`: write `Decimal(9, 2)`, the compared field's precision
  and scale (PIE-S2353).
- `day: Date(1)`, `name: Text(20)`, `doc: Json`: a bare `Date` or `Text`; Json
  has no parameter (PIE-S2353).
- `day: Text` compared with a `Date` field: declare `day: Date` (PIE-S2105).
- `floor: Decimal(10, 2)` compared with a `Decimal(9, 2)` field: the same
  precision and scale (PIE-B1005 at `emit-sql`); and `amount + floor`: compare,
  do not compute (PIE-B1003).
- a Decimal, Date, Timestamp or UUID parameter on MySQL: emit with
  `--dialect postgres` (PIE-B1003 at each declaration).
- `parameters={"day": "2024-01-31"}`, `date(999, 12, 31)`, a `date` for a
  `Timestamp`, an aware `datetime`, `Decimal("10.001")` for `Decimal(9, 2)`,
  `Decimal("NaN")`, `10`, a UUID's text: pass the exact Python type within
  its range, never rounded (PIE-R1006).

## Reusing an expression: `def`

```pietto
shape OrderLine:
    id: Int
    price_cents: Int
    quantity: Int

source order_lines: OrderLine = postgres.table("order_lines")

def line_total(price_cents: Int, quantity: Int) -> Int: return price_cents * quantity

query line_totals:
    from order_lines
    select id, total_cents = line_total(price_cents, quantity)
```

Each call is replaced by the body, so the SQL is the expression written out; no
database function is created. Parameters and the result follow the same None
rule as fields. Use a `def` when several queries share an expression; inside
one query, a `let` is enough.

### A def from another module

In a project, export the def where it is declared and import it where it is
called, with its kind, like a source:

```text
# models/a.pietto
export def pos, source rows
shape Row:
    id: Int
    amount: Int
source rows: Row = postgres.table("rows")
def pos(x: Int) -> Bool:
    return x > 0

# models/b.pietto
from "models/a.pietto" import def pos, source rows
query q:
    from rows
    where pos(amount)
    select:
        id
```

With many items, use the parenthesized list, one item per line with a
trailing comma:

```text
from "models/a.pietto" import (
    def pos as p,
    source rows,
)
```

The SQL is the same as for a def declared in the calling module.

Not this:

- `from "models/a.pietto" import def *`: name each item (PIE-P1000 at the
  `*`).
- `export constraint valid`, `import derive d`: a constraint or derive stays in
  its module (PIE-P1000).
- `export (pos)`: write the kind, `export (def pos)` (PIE-P1000).
- `import def pos` beside a local `def`, `constraint`, `derive` or relationship
  named `pos`, or two imports of `pos`: import it under another name,
  `def pos as p` (PIE-S2706).
- `import def pos as concat` (also `Float`, `Text`, `round`): a def cannot take
  a built-in name (PIE-S2398).
- a def or relationship item in a package module: package modules do not
  support them yet (PIE-S2707).
- calling `pos` without importing it: PIE-S2103 names the export and import to
  write.
- `a.pos(x)`: import `pos` and call `pos(x)` (PIE-S2103 says so).

### A relationship from another module

A relationship is exported and imported the same way; the importer does not
import its parameter shapes to call it:

```text
# models/a.pietto
export shape Order, shape Customer, source orders, source customers, relationship OrderCustomer
shape Order:
    id: Int
    customer_id: Int
shape Customer:
    id: Int
    status: Text | None
source orders: Order = postgres.table("shop.orders")
source customers: Customer = postgres.table("shop.customers")
relationship OrderCustomer(order: Order, customer: Customer):
    order.customer_id == customer.id

# models/b.pietto
from "models/a.pietto" import source orders, source customers, relationship OrderCustomer
query order_customers:
    from orders
    let buyer = customers
    left join buyer on OrderCustomer(orders, buyer)
    select:
        order_id = orders.id
        customer_id = buyer.id
```

Not this:

- `import relationship OrderCustomer` beside a local declaration of
  `OrderCustomer` of any kind, or two imports binding one name: import it as
  another name, `relationship OrderCustomer as oc` (PIE-S2706).
- `relationship OrderCustomer as concat` (also `Float`, `Text`, `round`): a
  relationship cannot take a built-in name (PIE-S2398).
- `import def OrderCustomer` for a relationship: write
  `relationship OrderCustomer` (PIE-S2705 names the kind).
- calling a relationship the other module does not export, or that this
  module does not import: PIE-S2103 names the export and import to write.
  When only a module that imports this one declares it, or this module
  already has the name, declare the relationship here.
- a row of a shape that the importer declares itself: pass a row of the
  declaring module's shape, for example a source of it (PIE-S2604).

## Text, None-safe equality, ranges and spread

```pietto
shape Visit:
    id: Int
    first_name: Text
    last_name: Text | None
    badge: Text | None
    guest_badge: Text | None
    seen_at: Timestamp
    minutes: Float
    late_minutes: Float | None

source visits: Visit = postgres.table("visits")

query march_visits:
    from visits
    where "2026-03-01 00:00:00" <= seen_at < "2026-04-01 00:00:00"
    select:
        id
        full_name = concat(first_name, " ", last_name)
        same_badge = same_value(badge, guest_badge)
        longest = max(minutes, late_minutes)

query visit_spread:
    from visits
    group by first_name
    select first_name, minutes_spread = stddev(minutes)

query visit_minutes:
    from visits
    group by first_name
    select first_name, typical = median(minutes), slow = quantile(minutes, 0.9)
```

`concat` joins Text values and is None when any of them is None, as SQL's
`||` is. `same_value(a, b)` is the `==` of Python for None: True when both are
None, False when only one is. Write a half-open range, such as one month, as
one chain `start <= ts < stop`. `stddev` is the sample standard deviation,
Python's `statistics.stdev`, and is None for fewer than two values.
`median(x)` and `quantile(x, q)` are the interpolated median and quantile, as
pandas' `Series.median()` and `Series.quantile(q)`: the values are taken as
Float, None values are skipped, and the result is a Float, None when no value
is left. `q` is a Float literal from 0.0 to 1.0 written in the call, such as
`0.9` for the 90th percentile. They take an `Int` or `Float` field and emit on
PostgreSQL only; MySQL has no interpolated percentile.
`max(a, b)` and `min(a, b)` are Python's larger and smaller of two values and
are None when either value is None, where SQL's `GREATEST` and `LEAST` skip a
None on PostgreSQL. Nest them for more values: `max(a, max(b, c))`; a nest of
up to five fields this way fits (PIE-S2399 past that).
`lpad(code, 5, "0")` pads a Text on the left to 5 characters with the one
character `"0"`, written in the call, and never shortens it: a longer `code` is
kept, as Python's `code.rjust(5, "0")` keeps it, where SQL `LPAD` cuts it.
`add_months(due, 1)` moves a Date by whole months and puts the day at the end
of a shorter month: one month after 2024-01-31 is 2024-02-29, and one month
after 2024-02-29 is 2024-03-29, not the end of March. Both are None when any
argument is None.

```pietto
shape Offer:
    id: Int
    starts_at: Timestamp
    ends_at: Timestamp | None

source offers: Offer = postgres.table("offers")

query current_offers:
    from offers
    where starts_at <= now() < ends_at
    select:
        id
        checked_at = now()
        checked_on = date_of(now())
```

`now()` is the time the query runs, in UTC and without a time zone, as Python's
`datetime.now(timezone.utc).replace(tzinfo=None)`; it is not `datetime.now()`,
which is local time. Every `now()` of one run is the same value, and a new run
reads a new one; saved results keep the value of the run that saved them.
`date_of(now())` is today's UTC date. Write `now()` in a SELECT item or a WHERE
comparison; elsewhere, such as a GROUP BY or ORDER BY key, a JOIN `on`, a field
`derive`, another `let`, HAVING, QUALIFY, a window, LIMIT or a `def` body, it
is refused (PIE-S2387). If a column holds local time, comparing it with
`now()` is off by the local offset from UTC. MySQL does not emit `now()` yet.

## The rows of each group: group, then collect

To list each group's rows beside its count, group in one query and collect in
a second query that reads the first. This is a project form (PostgreSQL, a
`schema_version = 2` project); a single file refuses it, so the block shows
its codes:

```pietto PIE-S2345 PIE-S2351 PIE-S2801
shape Order:
    id: Int
    region: Text | None
    amount: Int

source orders: Order = postgres.table("orders")

query per_region:
    from orders
    group by region
    select region, n = count()

query region_orders:
    let members:
        capture per_region
        from orders
        where same_value(orders.region, per_region.region)
        select:
            id
            amount
        order by id
    from per_region
    select:
        region
        n
        items = collect members
```

`per_region` has one row per region, and the orders without a region are a
group of their own. The let `members` captures that row and keeps the orders
of its group: `same_value` is also True when both regions are None, so every
group, the None one included, gets its own `n` orders in `items`. Read the
same input in the let as in the grouped query. When the groups count only
some rows, write that filter in a query of its own, such as `paid_orders`
with `where paid`, and read `paid_orders` in both places. End the let's
`order by` with a unique field, such as `id`.

Not this:

- `items = collect members` in the query with `group by`: group in one query,
  collect in another that reads it (PIE-S2803, whose JSON `suggestion` shows
  this route).
- `where orders.region == per_region.region`: write
  `where same_value(orders.region, per_region.region)`; `==` is never True for
  None, so the None group gets `[]` although its `n` is not 0.
- a let that reads `orders` beside a grouped query that reads `paid_orders`:
  read `paid_orders` in both; otherwise `items` lists the unpaid orders too.
- a let whose `where` matches a group key that is a nested field (the output
  of a `collect`): not available (PIE-S2805, with `same_value` as with `==`).
- a let that matches a `Bool` group key: not available yet (`emit-sql
  --project` refuses a `Bool` `same_value`, PIE-B1003
  `comparison_type_pair_not_admitted`).

## Comments

Comments start with `#`, as in Python. `--` does not start a comment:
`amount > 100 -- 50` means `amount > 100 - (-50)`, that is `amount > 150`.

## Python habits that differ

| You might write | Write instead | Why |
| --- | --- | --- |
| `a / b` for a fraction | `Float(a) / b` | `Int / Int` truncates toward zero, as SQL does: `7 / 2` is `3` and `-7 / 2` is `-3` |
| `a // b` | `a / b` | there is no `//`; `Int / Int` drops the fraction toward zero, so `-7 / 2` is `-3` where Python's `-7 // 2` is `-4` |
| `x == None` | `x is None` | a comparison with None is never true (PIE-S2105) |
| `x in ("a", None)` | `x == "a" or x is None` | an `in` list never matches None |
| `x not in (1, 2)` when `x` may be None | `x is None or x not in (1, 2)` | for a None `x` the test is not true, so its row is dropped |
| `first + " " + last` | `concat(first, " ", last)` | `+` does not join text (PIE-S2105); `concat` is None when any argument is None |
| `email.lower()` | `lower(email)` | functions take the value as an argument; there are no methods |
| `round(x)` expecting Python's tie rule | `round(x)`, with `round(2.5)` being `3` | a tie rounds away from zero for Float and Decimal, as PostgreSQL rounds a `numeric` (`round(-2.5)` is `-3`); Python rounds a tie to even, so its `round(2.5)` is `2` |
| `case when ... end` | `a if condition else b` | the conditional is Python's |
| `&&`, `\|\|`, `!` | `and`, `or`, `not` | `\|\|` does not join text either: write `concat(a, b)` |
| `a == b` where both may be None | `same_value(a, b)` | `==` is never true when an operand is None; `same_value` is True when both are None |
| `same_value(x, None)` | `x is None` | a `None` operand of `same_value` is an error (PIE-S2104) |
| `start <= ts and ts < stop` | `start <= ts < stop` | one chain for a half-open range: `start` is in it, `stop` is not |
| `statistics.stdev(xs)`, `stddev_samp(x)` | `stddev(x)` | one name, the sample deviation; None below two values, where Python raises |
| `statistics.pstdev(xs)`, `stddev_pop(x)`, `std(x)` | not available | the population deviation; MySQL `STD`/`STDDEV` and numpy `std` mean population; Pietto never emits them |
| `statistics.median(xs)`, `percentile_cont(0.5) within group (order by x)` | `median(x)` | one name; values are taken as Float, None values are skipped, and an empty group is None, where Python raises |
| `df.x.quantile(0.9)`, `percentile_cont(0.9) within group (order by x)`, `approx_percentile(x, 0.9)` | `quantile(x, 0.9)` | `q` is a Float literal from 0.0 to 1.0 written in the call; `90` or a field is refused (PIE-S2104) |
| `percentile_disc(0.9) within group (order by x)` | not available | the discrete percentile picks one value; `quantile` interpolates between the two nearest |
| `median(x) window(...)`, `median(x) over (...)` | not available | a running or partitioned median is not a window aggregate (PIE-S2103) |
| `datetime.now()`, `datetime.utcnow()`, `current_timestamp`, `utcnow()`, `utc_now()` | `now()` | one name, the UTC time when the query runs, without a time zone (PIE-S2103 hint for the calls `datetime.now`, `datetime.utcnow`, `current_timestamp`, `utcnow`, `utc_now`, any letter case) |
| `date.today()`, `today()` | `date_of(now())` | the UTC date when the query runs (PIE-S2103 hint for `date.today`, `today`) |
| `NOW()` | `now()` | functions are lowercase (PIE-S2103 hint) |
| `sum(1 if paid else 0)`, `count_if(paid)`, `sum(x) filter (where paid)` | `sum(1 for o in group if o.paid)` | one way to count the rows that match; a conditional argument is refused (PIE-S2315, PIE-S2103, PIE-P1000) |
| `sum(amount if paid else 0)` | `sum(o.amount for o in group if o.paid)` | the test follows the source, as in Python; 0 when no row matches |
| `count(paid)` to count the True values | `sum(1 for o in group if o.paid)` | `count(paid)` counts every row whose `paid` is not None, False included (warning PIE-S2388) |
| `sum(paid)` | `sum(1 for o in group if o.paid)` | `sum` adds numbers; a Bool is no number (PIE-S2314) |
| `sum(1 for o in orders if o.paid)` in a grouped query | `sum(1 for o in group if o.paid)` | `orders` is every row of `orders`, never this group (PIE-S2334) |
| `any(o.paid for o in group)` | `n = sum(1 for o in group if o.paid)`, then `n > 0` in `having` | a test of the group is not available yet (PIE-S2301) |
| `max(a, b, c)` | `max(a, max(b, c))` | `max` and `min` take one value (the aggregate) or two; more is an error (PIE-S2309) that says to nest |
| `greatest(a, b)`, `least(a, b)` | `max(a, b)`, `min(a, b)` | there is no `greatest` or `least` (PIE-S2103); `max` and `min` are None when either value is, where PostgreSQL `GREATEST` skips a NULL |
| `max(a, None)` | `None`, or drop the call | a `None` argument is an error (PIE-S2104): the result would always be None |
| `max(n, 1.5)` with an `Int` `n` | `max(Float(n), 1.5)` | both values need one type, as for `coalesce` and a conditional's branches (PIE-S2104) |
| `b if a < b else a` for the larger value | `max(a, b)` | the conditional gives `a` when only `b` is None; `max(a, b)` gives None there |
| `code.rjust(5, "0")`, `rjust(code, 5, "0")` | `lpad(code, 5, "0")` | functions take the value as an argument (PIE-S2103 hints `lpad`); like `rjust`, `lpad` never shortens `code` |
| `lpad(code, 5)` | `lpad(code, 5, " ")` | there is no default fill; the fill is one character written in the call (PIE-S2104) |
| `LPAD(code, 5, " ")`, `ADD_MONTHS(d, 1)` | `lpad(code, 5, " ")`, `add_months(d, 1)` | built-in names are lowercase (PIE-S2103 `Unknown function: LPAD`) |
| `d + relativedelta(months=1)`, `DATE_ADD(d, INTERVAL 1 MONTH)` | `add_months(d, 1)` | the day moves to the end of a shorter month, and a month end does not stay one: `add_months(d, 1)` of 2024-02-29 is 2024-03-29 |
| `add_months(ts, 1)` for a Timestamp | `add_months(date_of(ts), 1)` | `add_months` takes a Date (PIE-S2104) |
| `true`, `null` | `True`, `None` | |
| `-- note` | `# note` | `--` is a minus sign followed by another |

After a `left join`, a `where` test on the joined input, such as
`customer.region == "EU"`, is not true for an order that found no customer, so
it removes those orders and gives the result of an inner join. To keep them,
write the test in `on`:

```pietto
shape Customer:
    id: Int
    region: Text

shape Order:
    id: Int
    customer_id: Int

source customers: Customer = postgres.table("customers")

source orders: Order = postgres.table("orders")

query orders_with_european_customer:
    from orders
    let customer = customers
    left join customer on orders.customer_id == customer.id and customer.region == "EU"
    select order_id = orders.id, customer_region = customer.region
```
