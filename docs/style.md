# Pietto style

This page shows one way to write each thing. It is written for people who know
Python and only a little SQL. The [language reference](language.md) lists the
other accepted forms and every rule; you do not need them to start.

Check a file in strict mode, which also refuses a source without a shape and
a computed output without a name:

```bash
pietto check --check-mode strict shop.pietto
```

Each example below is a complete file that you can copy and check. It passes
that check with no diagnostic, unless the text says that it shows one.

## Documentation examples

`tests/test_repo_docs_examples.py` checks every fenced `pietto` block of
`README.md`, `docs/language.md` and `docs/style.md` as one complete file, as
`pietto check --check-mode strict` checks it. A block whose opening fence line
is only the language word must report no diagnostic. When an example shows
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
in `any(...)`, never the group. MySQL emits neither yet, and a project does
not take a generator yet.

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
```

`concat` joins Text values and is None when any of them is None, as SQL's
`||` is. `same_value(a, b)` is the `==` of Python for None: True when both are
None, False when only one is. Write a half-open range, such as one month, as
one chain `start <= ts < stop`. `stddev` is the sample standard deviation,
Python's `statistics.stdev`, and is None for fewer than two values.
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
