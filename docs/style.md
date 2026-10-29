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
readers do not see the codes.

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
    id: Int                # never None
    name: Text             # never None
    email: Text | None     # may be None

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
| `first + " " + last` | not available yet | `+` does not join text (PIE-S2105) |
| `email.lower()` | `lower(email)` | functions take the value as an argument; there are no methods |
| `round(x)` expecting Python's tie rule | `round(x)`, with `round(2.5)` being `3` | a tie rounds away from zero for Float and Decimal, as PostgreSQL rounds a `numeric` (`round(-2.5)` is `-3`); Python rounds a tie to even, so its `round(2.5)` is `2` |
| `case when ... end` | `a if condition else b` | the conditional is Python's |
| `&&`, `\|\|`, `!` | `and`, `or`, `not` | |
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
