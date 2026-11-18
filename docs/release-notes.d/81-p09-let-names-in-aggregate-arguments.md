### `let` names inside aggregate arguments

An aggregate reads a `let` name inside its expression argument as the
name's value, as it already read a `let` name that is its whole argument
(PL.48 (1)). In a single file and in an EXPLICIT_MODULES project, `s` below
is accepted, as `sum(qty * 2 + 1)` is, and the single file's SQL on
PostgreSQL and on MySQL is that of `sum(qty * 2 + 1)`:

```pietto
query totals:
    from orders
    let d = qty * 2
    select:
        s = sum(d + 1)
```

A single file inlines the value. An EXPLICIT_MODULES project reads the `let`
column of its row stage, also over JOIN rows, and its compiled bundle replays
and loads as the emitted query does. A `schema_version = 1` project reads
such a name as its value in a relation without GROUP BY.

- Over a source with a shape, a single file reported PIE-S2102
  `Unknown field` for `sum(d + 1)`, `avg(d + 1)` and `count(d + 1)` after
  `let d = qty * 2` and for `count_distinct(lower(l))` after
  `let l = label`, which it now accepts, and for
  `first(d + 1, order by id)` after `let d = qty`, `count_distinct(len(l))`
  after `let l = status` and, after `let d = qty % 2`, `sum(d + 1)`, which
  are now PIE-S2315, as their values written in place are. `min(d + 1)`,
  `max(abs(d))` and `median(d * 2.0)` keep PIE-S2315 there.
- Over a source without a shape, where `sum(d + 1)`, `min(d + 1)` and
  `median(d * 2.0)` after `let d = x` reported PIE-S2102, the name is read
  as its value too: `sum(d + 1)` is accepted, and `min(d + 1)` and
  `median(d * 2.0)` are PIE-S2315, as their values written in place are.
  `min(d)`, `max(d)`, `median(d)`, `quantile(d, 0.5)` and `stddev(d)` still
  report PIE-S2102 there.
- An EXPLICIT_MODULES project without JOIN inputs reported the bare
  PIE-S2333 for `sum(d + 1)` after `let d = qty * 2`, which it now accepts,
  and for `min(d + 1)` after `let d = qty`, which is now PIE-S2315, as
  `min(qty + 1)` is. With the JOIN input
  `inner join c on c.id == orders.id`, which matches the unique key of
  `customers`, it reported PIE-S2315 for `sum(d + 1)`, `avg(d + 1)` and
  `count(d + 1)` after `let d = orders.qty * 2` and for
  `count_distinct(lower(l))` and
  `string_agg(lower(l), ",", order by orders.id)` after
  `let l = orders.label`, which it now accepts, as their values written in
  place. Read from `customers` with `inner join o on o.qty == customers.id`,
  which may repeat the rows of `customers`, `sum(d + 1)` after
  `let d = customers.id` reported PIE-S2315 and now reports PIE-S2333 at
  the relation, as `sum(customers.id + 1)` does.
- A SQLite or DuckDB EXPLICIT_MODULES project, which admits no relation
  `let` stage, reported the bare PIE-S2333 for `n = count(d + 1)` after
  `let d = id`, and PIE-S2315 for it after `let d = orders.id` over
  `inner join c on c.id == orders.id`. It now passes
  `pietto check --project` for both, as for `count(id + 1)` and
  `count(orders.id + 1)`, and its emission is BLOCKED with PIE-B1003
  `sqlite_relation_shape_not_admitted` or
  `duckdb_relation_shape_not_admitted` at the `let`.
- A MySQL project keeps such a `let` as a column of its row stage: with
  `x` a nullable `Float` field, `count(-t)` after `let t = x`, which
  reported the bare PIE-S2333, passes `pietto check --project` and is
  BLOCKED with PIE-B1003 `unary_sign_requires_int_operand`, as
  `let t = -x` with `count(t)` is, while `count(-x)` emits.
- A `let` name passed to a `def` inside the argument must fit its parameter
  as the value written in place must: for `sum(nn(d) + 1)`, where `d` may be
  None and `nn` takes an `Int`, an EXPLICIT_MODULES project without JOIN
  inputs reports the bare PIE-S2333, and one with JOIN inputs or a single
  file PIE-S2395; a single file's says `got null` for a `let` bound to
  `None`.
- `string_agg(lower(d), ",", order by id)` after `let d = None` keeps the
  bare PIE-S2333 in an EXPLICIT_MODULES project, with and without JOIN
  inputs, where a single file accepts it; without JOIN inputs such a
  project accepts `string_agg(lower(None), ",", order by id)`.

In `0.2.2`, `load_bundle` refused with `PIE-R1004`
(`COMPILED_AGGREGATE_ARGUMENT`) a bundle whose aggregate argument, or
`string_agg` delimiter, is an operation that reads a `let:` name with a
computed value. The compiled replay and its independent verifier now read
such a name as its value and judge the value written in place by the same
argument law: the bundle that `compile_query` exports for `s` above loads
and renders its SQL, while one edited to read `let d = qty % 2`, or renamed
to `min(d + 1)`, is still refused, as `compile_query` refuses those sources
(`PIE-S2315`). A computed `let:` value read in a generator, as an
`order by` key or in a window's value, and a query parameter read through a
`let:` name inside an argument (`PIE-S2355`), are refused as before.

Changed diagnostics (bundles that `0.2.2` refused):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-R1004 | `load_bundle` of a bundle whose aggregate argument is an operation that reads a computed `let:` value the aggregate admits written in place, such as `sum(d + 1)` with `let d = qty * 2` | `COMPILED_AGGREGATE_ARGUMENT` | loads |
