### DuckDB Arrow route — grouping, aggregates and `having`

A query or table over one `duckdb.arrow` source can now group its rows and
aggregate them on DuckDB. `group by` takes direct reads of the source's
`Int`, `Text`, `Bool` and `Float` fields, optional or not; NULL keys form one
group, and a `Float` key puts `-0.0` and `0.0` in one group. The selected
values are the keys and `count()`, `count(field)`, `sum` of an `Int` field
and `min` and `max` of an `Int` or `Float` field; an aggregate without
`group by` gives one row. A `having` may compare one selected `Int` output
with the query's one non-null `Int` parameter, as `where` compares an `Int`
field. `pietto emit-sql --project ... --dialect duckdb` writes them as
`GROUP BY` and `HAVING` over qualified capture columns, `sum` as
`CAST(sum(...) AS BIGINT)`, and `execute(route="duckdb_arrow")` runs them. A
`sum` outside signed 64 bits fails the statement with `PIE-R3003` instead of
returning a wrong value. Each aggregate's column in the emission document
names its `aggregate` and `function` and has its result's type and
nullability, and each key's column names its `group_key`. See the
[DuckDB Arrow route](../spec/duckdb-arrow-route-v1.md#admission). The example is
a module of an explicit-module project; checked as a single file it reports
PIE-S2346 for its header parameter.

```pietto PIE-S2346
shape Order:
    customer: Text
    amount: Int

source orders: Order = duckdb.arrow("orders")

query totals(min_total: Int):
    from orders
    group by customer
    select:
        customer
        n = count()
        total = sum(amount)
    having total >= min_total
```

- `avg`, `count_distinct`, `sum` of a `Float` and aggregates of computed
  values are refused with `PIE-B1003` `duckdb_aggregate_not_admitted` at the
  aggregate, and a computed `group by` key, which only a relation `let` can
  make, with `PIE-B1003` `duckdb_grouping_not_admitted` at the key, after
  the `let`'s `duckdb_relation_shape_not_admitted`. `order by` and `limit`
  stay refused with `duckdb_relation_shape_not_admitted`.
- A grouped or aggregated statement that was refused as a whole with
  `duckdb_relation_shape_not_admitted` now reports only the rules it
  breaks, or none.
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
  are not available on DuckDB` and `group by source fields, such as group by
  customer; computed keys are not available on DuckDB`. No DuckDB text says
  "yet" any more, and no PostgreSQL or MySQL text changes.
