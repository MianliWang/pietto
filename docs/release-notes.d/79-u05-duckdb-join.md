### DuckDB Arrow route — several sources and their JOINs

A query or table can now read several `duckdb.arrow` sources on DuckDB,
joining each to the rows so far with `inner join` or `left join` on one
`==`, or an `and` of several, between a field of the joined source read
and a field of an earlier one, both of one type other than `Decimal`; a `Float`
key matches `-0.0` with `0.0`. The rest of the statement takes the forms
that one source takes, arithmetic included, its fields from any source
read, and a `left join` makes the fields of its joined read nullable in
the result, and so an arithmetic value with an operand among them.
`pietto emit-sql --project ... --dialect duckdb` writes the JOINs as
`INNER JOIN` and `LEFT JOIN` of one registered name for each source read,
`pietto_arrow_0`, `pietto_arrow_1` and so on, with its fields numbered across
the source reads (`"c0"` onward); the emission document names each column's
source and its field there. A source read twice through a row-input alias,
such as `let parent = orders`, then `left join parent on parent.id ==
orders.amount`, is two reads, each with its own registered name and fields.
See [Admission](../spec/duckdb-arrow-route-v1.md#admission). These forms are
qualified with `duckdb` `2.0.0` and `pyarrow` `26.0.1` on CPython 3.12 and
3.13, Linux x86-64 with glibc 2.28 or later.

```pietto PIE-S2346
shape Order:
    id: Int
    customer: Int
    amount: Int

shape Customer:
    id: Int
    name: Text
    key = unique(id)

source orders: Order = duckdb.arrow("orders")

source customers: Customer = duckdb.arrow("customers")

query totals(least: Int):
    from orders
    inner join customers on orders.customer == customers.id
    group by customers.name
    select:
        name = customers.name
        total = sum(orders.amount)
    having total >= least
```

`execute(route="duckdb_arrow")` takes, as `access`, a `DuckDBArrowInput` or
a tuple of them, one for each key that the query reads, in any order, such
as `(DuckDBArrowInput("orders", orders), DuckDBArrowInput("customers",
customers))`. Two sources declared with one key, or two reads of one
source, read one input, which is checked against each read and copied
once. See [Execute API](../spec/duckdb-arrow-route-v1.md#execute-api).

- A tuple whose names repeat, miss a key that the query reads or add one it
  does not is refused with `PIE-R1002` `DUCKDB_ARROW_SCHEMA`; a tuple with
  another element, or a list, with `PIE-R1002` `PUBLIC_ACCESS_TYPE`.
- The capture limits count rows for each input, at most 1,048,576, and the
  selected columns' bytes over all inputs together, at most 256 MiB.
- When the query aggregates JOIN rows, the capture also refuses with
  `PIE-R1002` `DUCKDB_ARROW_SCHEMA` an input in which two rows break any
  `unique(...)` key that its shape declares, compared as Pietto's `==` does,
  `-0.0` equal to `0.0`, and leaving out rows with a NULL in the key, since
  the language proves that such an aggregate reads no repeated row from
  those keys.
- A `right`, `full` or `cross` JOIN, any other `on`, such as one between
  an `Int` and a `Float` field, and a `Decimal` key are refused with
  `PIE-B1003` `duckdb_relation_shape_not_admitted` at the JOIN. A field read
  through any JOIN is now a direct read of its source's field, so such a statement
  reports that blocker without the `duckdb_source_count_not_admitted`,
  `duckdb_projection_not_admitted`, `duckdb_aggregate_not_admitted`,
  `duckdb_grouping_not_admitted` or `duckdb_filter_not_admitted` that its
  JOIN brought before, beside any blocker of another cause, such as
  `PIE-B1006` `original_enforcement_not_fulfilled` for an unfulfilled
  single-match obligation, or `duckdb_parameter_not_admitted` for a
  parameter that its `on` reads: its `blockers` list is shorter.
  `duckdb_source_count_not_admitted` now refuses only a statement that reads
  no source.
- The suggestions of three refusals change, and scripts that match their
  text must follow. `duckdb_relation_shape_not_admitted` now reads `DuckDB
  emission admits duckdb.arrow source reads joined by inner or left joins
  on equalities of fields of one type, such as inner join customers on
  orders.customer_id == customers.id, then where, group by, having, select,
  order by and limit; right, full and cross joins, other on conditions,
  Decimal join keys, windows, qualify, distinct, set operations, relation
  lets and derived sources are not available on DuckDB`;
  `duckdb_source_count_not_admitted` `read one or more duckdb.arrow sources;
  the DuckDB route runs one query over the Arrow tables passed to
  execute()`; and `source_identifier_unrepresentable` `use the relation
  namespace "arrow"; the DuckDB route reads registered Arrow tables`.
