### A `let` that renames a grouped field can be selected

A relation with `group by` can now select a `let` that renames a field it
groups by, whether `group by` writes the field (`group by status`) or the
`let` name (`group by state`): by its name (`state`), as another output's
whole value (`label = state`), and `order by` and `having` read that
output, except a project's `order by` of the name itself with JOIN inputs
(below). It selects that field's key, as selecting the field does. The
query below checks and emits in a single file on PostgreSQL and MySQL, and
an explicit-module project and a LEGACY_FLAT project check accept it. Over
the published `BIGINT` contract, `pietto emit-sql --project`, `compile_sql`
and `compile_query` accept `k` after `let k = key` and `group by k` on both
targets. A project keeps such a `let` as a column of its row stage, so on
MySQL the guarded `sum` of an `Int` field (PIE-B1004
`sum_int_aggregate_range_proof_missing`), the `count` of the sign of a
nullable `Float` field (PIE-B1003 `unary_sign_requires_int_operand`) and a
`Float` group key (PIE-B1003
`group_key_type_outside_reviewed_comparison_domain`) keep their blockers
beside it, where the field-spelled query emits.
A single file emits for the query below the SQL of `state = status` under
`group by status`, on PostgreSQL and MySQL, and a SQLite single file emits
`a` after `let a = amount` and `group by a` as `a = amount` under
`group by amount`. SQLite and DuckDB explicit-module projects now pass
`pietto check --project` for `a` after `let a = amount` and
`group by amount`, and refuse it at emission with PIE-B1003
`sqlite_relation_shape_not_admitted` or `duckdb_relation_shape_not_admitted`
at the `let`, where `a = amount` emits.

```pietto
shape Order:
    id: Int
    status: Text

source orders: Order = postgres.table("orders")

query by_status:
    from orders
    let state = status
    group by state
    select:
        state
        n = count()
    order by state
```

Compatibility: these outputs change, each for a program that was refused
before:

| Code or output | Case | Before | After |
| --- | --- | --- | --- |
| PIE-S2329 | a single file selects such a `let` by its name, as `state` above | ``Let binding conflicts with projection output name: state; a query with GROUP BY cannot select a `let` name here yet: write status in place of state`` | none: the query checks and emits |
| PIE-S2102 | a single file projects it, as `label = state`, or a LEGACY_FLAT check does when `group by` writes the field | ``Unknown field: state; a query with GROUP BY cannot select a `let` name here yet: write status in place of state`` | none |
| PIE-S2321 | `order by state` beside such a refused selection | `Unsupported grouped ORDER BY item; expected a supported select output name` | none |
| PIE-S2333 | an explicit-module project relation without JOIN inputs that selects or projects such a `let` | `Project relation semantic completion is unavailable: <relation>` at `check --project`, and `emit-sql --project` BLOCKED with it | none: VERIFIED on PostgreSQL, and on MySQL but beside the three MySQL cells above, which keep their blockers; `n = sum(nope)` reports PIE-S2102, as in a single file |
| PIE-S2333 | the same relation in a SQLite or DuckDB explicit-module project | as above | `check --project` passes, and the artifact is BLOCKED with PIE-B1003 `sqlite_relation_shape_not_admitted` or `duckdb_relation_shape_not_admitted` |
| PIE-S2102 | without JOIN inputs, a grouped window beside such a selection orders by the `let`, as `r = row_number() window(order by state)` | `Unknown field: state` at the window, in such a project in place of the PIE-S2333 above and in a single file beside the PIE-S2102 of a projection such as `label = state` | none beside `state`, `label2 = state` or `status = state`; beside `label = state` alone, over a field `label`, a single file and such a project still report `Unknown field: state` at the window |
| PIE-S2326 | `having` reads such an output, as `having label == "open"`, or, without JOIN inputs, the field selected under `group by state`, as `having status == "open"` | `Having output is not a group-key or direct aggregate projection: <output>` in a single file; for `having status == "open"` also in such a project, where `having label == "open"` reported the bare PIE-S2333 above; with JOIN inputs, in a single file | none |
| PIE-S2329, PIE-S2102 | a single file over a source without a shape selects such a `let` by its name or projects it | `Let binding conflicts with projection output name: state` without a hint, or the second row's PIE-S2102 with its hint | none: `check` reports only PIE-S2303 and `emit-sql` refuses it with PIE-B1000, as with the field |
| PIE-S2317 | `group by state, status` with `state` selected | the PIE-S2329 above in a single file, PIE-S2333 in a project | `Duplicate GROUP BY key: status`, as for `group by status, status` |
| other errors | a single file's other SELECT items beside such a `let` and an aggregate, such as `status` (PIE-S2318) or `next = lower(state)` (PIE-S2319) | reported beside the PIE-S2329 | none: they read the key |
| PIE-S2329, PIE-S2102 | a single file's query without aggregates that computes an output from such a `let`, as `next = lower(state)` beside `state` or `status`, and a LEGACY_FLAT check of it when `group by` writes the field; also a single file's item without an alias that reads such a `let` beside an aggregate or is one, as `lower(state)` beside `n = count()`, or `sum(m)` after `let m = qty` and `group by m` | PIE-S2319 beside the PIE-S2329 above for `state`, beside `Unknown field: state` for `status` and in the LEGACY_FLAT check; for the item without an alias, its PIE-S2319 or PIE-S2313 beside `Unknown field: state` or `Unknown field: m` | PIE-S2319 alone, with the output's own errors, as for `next = lower(status)`; for the item without an alias, its PIE-S2319 or PIE-S2313 alone |

The hint ``a query with GROUP BY cannot select a `let` name here yet: write
<field> in place of <name>`` no longer appears; scripts that match it must
follow. These stay refused, with their codes and texts:

- a `let` that is no GROUP BY key, as `let state = status` beside
  `group by id`: in a single file PIE-S2329 for `state` and PIE-S2102 for
  `label = state`, each with the hint `state is not a GROUP BY key`, and in an
  explicit-module project PIE-S2333;
- with JOIN inputs, an explicit-module project's `order by` of such a
  `let` that it selects by its name, as `state` then `order by state`:
  PIE-S2321 at `pietto check --project`, as before, with the text
  `Unsupported grouped ORDER BY item; expected a supported select output
  name`; `label = state` then `order by label` is accepted, and a single
  file accepts both;
- a `let` that names a computed `let`, as `let state = trimmed` beside
  `let trimmed = lower(status)` and `group by state`, with its two-query
  hint.
