### DuckDB Arrow route — filters, grouping, aggregates, `having`, `order by` and `limit`

A query or table over one `duckdb.arrow` source can now group its rows and
aggregate them on DuckDB. `group by` takes direct reads of the source's
`Int`, `Text`, `Bool` and `Float` fields, optional or not; NULL keys form one
group, and a `Float` key puts `-0.0` and `0.0` in one group. The selected
values are the keys and `count()`, `count(field)`, `sum` of an `Int` field
and `min` and `max` of an `Int` or `Float` field; an aggregate without
`group by` gives one row. A `having` filters the groups by their selected
outputs, as `where` filters rows (below).
`pietto emit-sql --project ... --dialect duckdb` writes them as `GROUP BY`
and `HAVING` over qualified capture columns, `sum` as
`CAST(sum(...) AS BIGINT)`, and `execute(route="duckdb_arrow")` runs them. A
`sum` outside signed 64 bits fails the statement with `PIE-R3003` instead of
returning a wrong value. Each aggregate's column in the emission document
names its `aggregate` and `function` and has its result's type and
nullability, and each key's column names its `group_key`.

Such a query or table can also order and limit its rows. Each `order by` key
is a direct read of a source field, or in a grouped query a selected output,
ascending or descending, and the `limit` is the static one the language
takes. `emit-sql` writes `ORDER BY` over qualified capture columns or the
restated aggregate, each key with `ASC NULLS LAST` or `DESC NULLS FIRST`, so
NULL sorts where PostgreSQL puts it, and the limit as `LIMIT <n>`. Rows that
tie on every key have no promised order, nor do the rows a `limit` keeps
among ties at its boundary or without `order by`.

`where` and `having` now compare fields and selected outputs with literals
and with query parameters of the same type, `Int`, `Text`, `Bool` or
`Float`, and join the tests with `and` and `or`; a `where` also tests fields
with `is None` and `is not None` and uses `not`. The language refuses those
tests, `not` and a `-` before a number in a `having` (`PIE-S2327`), so a
negative bound there is a parameter. A query may declare any number of
non-null parameters of those four types and read each one in such
comparisons, as often as it needs; `execute(parameters=...)` still checks
each value's exact type before DuckDB sees it (`PIE-R1006`). `emit-sql`
writes an `Int` literal as `CAST(<n> AS BIGINT)`, a `Float` literal as
`CAST('<r>' AS DOUBLE)` with `<r>` its shortest decimal, so `-0.0` stays a
negative zero, a `Text` literal quoted with each `'` doubled, a `Bool`
literal as `TRUE` or `FALSE`, and each parameter read as
`CAST($n AS <type>)`, numbered in the order of first reads; in a `where`, a
`-` before a number literal is part of the literal. The emission
document's `parameter_uses` has one entry per read with its parameter's
`server_index`, and `physical_type` may now also be `duckdb_double`,
`duckdb_varchar` or `duckdb_boolean`. See the
[DuckDB Arrow route](../spec/duckdb-arrow-route-v1.md#admission), the
[DuckDB local path](../capabilities.md#duckdb-local-path) and the route's
[execution guide](../execution.md#duckdb-arrow-route). These forms are
qualified as the projection is, with `duckdb` `2.0.0` and `pyarrow` `26.0.1`
on CPython 3.12 and 3.13, Linux x86-64 with glibc 2.28 or later. The example
is a module of an explicit-module project; checked as a single file it reports
PIE-S2346 for its header parameter.

```pietto PIE-S2346
shape Order:
    customer: Text
    amount: Int

source orders: Order = duckdb.arrow("orders")

query totals(min_total: Int):
    from orders
    where customer != "test" and amount > -5
    group by customer
    select:
        customer
        n = count()
        total = sum(amount)
    having total >= min_total
    order by:
        total desc
    limit 10
```

- `avg`, `count_distinct`, `sum` of a `Float` and aggregates of computed
  values are refused with `PIE-B1003` `duckdb_aggregate_not_admitted` at the
  aggregate, and a computed `group by` key, which only a relation `let` can
  make, with `PIE-B1003` `duckdb_grouping_not_admitted` at the key, after
  the `let`'s `duckdb_relation_shape_not_admitted`. A computed `order by`
  key, such as `order by -amount`, is refused with `PIE-B1003`
  `duckdb_order_not_admitted` at the key. In a query without `group by`, a
  key that names an output other than the source field of that name, such
  as `order by label` after `label = note` or `order by more` after
  `more = amount + 1`, leaves the plan unavailable and is refused with
  `duckdb_relation_shape_not_admitted` at the `order by`.
- A grouped, aggregated, ordered or limited statement that was refused as a
  whole with `duckdb_relation_shape_not_admitted` now reports only the rules
  it breaks, or none, and so does a filter with literals, several parameters
  or `and`, `or` and `not` that reported `duckdb_filter_not_admitted` and
  `duckdb_parameter_not_admitted`.
- A comparison of two reads or of an `Int` with a `Float`, a bare `Bool`
  field used as a test (write `flag == True`), a computed side such as
  `-amount` or `+5`, and a parameter tested with `is None` are still refused
  with `duckdb_filter_not_admitted`. A parameter that is optional, of
  another type, read nowhere or read outside a `where` or `having`
  comparison is refused with `duckdb_parameter_not_admitted`, at the
  declaration of the first such parameter or at the statement. A `Text`
  literal that holds NUL is refused with the new detail
  `duckdb_text_literal_nul_not_admitted` at the literal, with the suggestion
  `remove NUL from the Text literal; DuckDB emission writes no NUL into SQL
  text`.
- The suggestions of five DuckDB refusals change, and scripts that match
  their text must follow. `duckdb_relation_shape_not_admitted` now reads
  `DuckDB emission admits one source read with where, group by, having,
  select, order by and limit; JOIN, windows, qualify, distinct, set
  operations, relation lets and derived sources are not available on
  DuckDB`; `duckdb_projection_not_admitted` `select source fields directly,
  or group by keys and aggregates of fields, such as select: customer, total
  = sum(amount); computed values are not available on DuckDB`;
  `duckdb_filter_not_admitted` `compare fields or selected outputs with
  literals or query parameters of the same type, and join the tests with
  and, or and not, such as where amount >= min_amount and note is not
  None`; `duckdb_parameter_not_admitted` `declare non-null Int, Text, Bool
  or Float parameters and read each one in a where or having comparison`;
  and `duckdb_field_type_not_admitted` `DuckDB emission reads Int, Text,
  Bool and Float fields`. The new details have the suggestions `use count(),
  count(field), sum of an Int field, or min or max of an Int or Float field;
  other aggregates, sum or avg of a Float and aggregates of computed values
  are not available on DuckDB`, `group by source fields, such as group by
  customer; computed keys are not available on DuckDB` and `order by source
  fields or selected outputs, such as order by total desc; computed keys are
  not available on DuckDB`. No DuckDB text says "yet" any more, and no
  PostgreSQL or MySQL text changes.
- The capture limits rise from 65,536 rows and 16 MiB of the whole table to
  1,048,576 rows and 256 MiB of the selected columns, the table fields that
  the source's fields name, measured as the sum of their PyArrow `nbytes`; a
  table field that no source field names no longer counts. The capture now
  checks the rows, then the schema, then the bytes, so a table over a byte
  limit whose schema also fails reports `DUCKDB_ARROW_SCHEMA` instead of
  `DUCKDB_ARROW_CAPTURE_LIMIT`. DuckDB's `memory_limit` is 1 GiB in place
  of 256 MiB, a statement beyond it still fails with `PIE-R3003`, and the
  session also checks that `default_collation` is the empty string
  (`PIE-R2006` `DUCKDB_SESSION_CONTEXT` otherwise). Besides the caller's
  table, one `execute()` can hold about 1.5 GiB at its peak while its
  result is no larger than those columns, and a result beyond
  `ExecutionLimits.max_bytes` (64 MiB by default) is refused with
  `PIE-R3004` only after DuckDB has read it whole, so a larger result can
  exhaust a small host's memory first.
