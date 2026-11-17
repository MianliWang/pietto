### A `let` that renames a grouped field can be selected

A relation with `group by` can now select a `let` that renames a field it
groups by, whether `group by` writes the field (`group by status`) or the
`let` name (`group by state`): by its name (`state`), as another output's
whole value (`label = state`), and `order by` and `having` read that
output. It selects that field's key, as selecting the field does. This
holds in single files, on PostgreSQL and MySQL, in explicit-module
projects, where `pietto check --project`, `pietto emit-sql --project`,
`compile_sql` and `compile_query` accept it on both, and in LEGACY_FLAT
project checks. The SQL of a single file is the SQL of the same query with
the field written in place of the `let` name. Each form ran on PostgreSQL
18.6 and MySQL 8.4.12, in single files and in projects, with the same rows
as that field-spelled query.

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

Compatibility: only programs that were refused before change. These outputs
change:

| Code or output | Case | Before | After |
| --- | --- | --- | --- |
| PIE-S2329 | a single file selects such a `let` by its name, as `state` above | ``Let binding conflicts with projection output name: state; a query with GROUP BY cannot select a `let` name here yet: write status in place of state`` | none: the query checks and emits |
| PIE-S2102 | a single file projects it, as `label = state`, or a LEGACY_FLAT check does when `group by` writes the field | ``Unknown field: state; a query with GROUP BY cannot select a `let` name here yet: write status in place of state`` | none |
| PIE-S2321 | `order by state` beside such a refused selection | `Unsupported grouped ORDER BY item; expected a supported select output name` | none |
| PIE-S2333 | an explicit-module project relation without JOIN inputs that selects or projects such a `let` | `Project relation semantic completion is unavailable: <relation>` at `check --project`, and `emit-sql --project` BLOCKED with it | none: VERIFIED; a relation with another error reports it as a single file does, such as PIE-S2102 for `sum(nope)` |
| PIE-S2102 | a grouped window beside such a selection orders by the `let`, as `r = row_number() window(order by state)` | `Unknown field: state` at the window, in such a project in place of the PIE-S2333 above and in a single file beside its refusal | none |
| PIE-S2326 | `having` reads such an output, as `having label == "open"`, or, without JOIN inputs, the field selected under `group by state`, as `having status == "open"` | `Having output is not a group-key or direct aggregate projection: <output>` in a single file and in such a project, and with JOIN inputs in a single file | none |
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
- a `let` that names a computed `let`, as `let state = trimmed` beside
  `let trimmed = lower(status)`, with its two-query hint.
