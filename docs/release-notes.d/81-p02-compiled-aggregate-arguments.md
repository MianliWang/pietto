### Bundles with an aggregate argument `compile_query` refuses

`pietto.execution.load_bundle` now refuses with `PIE-R1004`
(`COMPILED_AGGREGATE_ARGUMENT`) a bundle whose aggregate argument is itself
a row operation in a form that `compile_query` refuses for that aggregate,
or reads a query parameter, which `compile_query` refuses in every
aggregate argument (`PIE-S2355`). `compile_query` never exports one, so
only an edited bundle holds it: for example a `median`, `stddev`, `min` or
`max` of `value + 1`, a `count_distinct` of anything but a `Text` field's
`lower` and `trim` chain, a `count` of `upper(label)`, `sum(value % 2)`, or,
with a header parameter `low`, `sum(id * low)` or
`sum(1 for o in group if o.id > low)`.

A `let:` name that is the whole argument is judged by the value it holds.
`min` and `max` read the name as a field, whatever its value; every other
aggregate refuses a value outside its law, such as `sum(t)` with
`let t = value % 2` or `median(t)` with `let t = value * 2`. A value that
reads a query parameter is read only as the whole argument of `count`,
`avg`, `min` or `max`, so `sum(t)` with `let t = id * low` is refused too.
A `let:` name with a computed value is refused, whatever that value, inside
an argument that is itself an operation and as the `order by` key of
`first`, `last` or `string_agg`, where `compile_query` refuses it
(`PIE-S2333`, `PIE-S2104`): for example `sum(d + 1)` or `avg(d * 2)` with
`let d = value * 2`, `count_distinct(lower(d))` with `let d = trim(label)`,
or `first(value, order by t)` with `let t = value % 2`. A window function
whose value argument reads a `let:` name with a computed value, such as
`sum(t)` or `lag(t)` over `window(order by rid)` with `let t = value % 2`,
which `compile_query` refuses (`PIE-S2103`, `PIE-S2104`), is refused with
`PIE-R1004` (`COMPILED_WINDOW_ARGUMENT`). A `let:` name that only renames
a field, such as `let d = value`, reads as that field, so an edited bundle
that reads it where `compile_query` refuses the name, such as `sum(d + 1)`,
an `order by` key or the value of a `min` or `max` window, still loads: it
means what the field form that `compile_query` writes, such as
`sum(value + 1)`, means, with equivalent SQL, a known equivalence.
Bundles that `compile_query` exports load and replay as before, with the
same SQL.

Changed diagnostics (bundles `0.2.1` refused; no accepted program changes):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-R1004 | `load_bundle` of a bundle described above that `0.2.1` refused at a replay check that runs after this one, such as a `sum` of `value * 2` renamed `median`, or `min(t)` with `let t = value % 2` renamed `median` | that check's detail, such as `COMPILED_AGGREGATE_TYPE` | `COMPILED_AGGREGATE_ARGUMENT`, or `COMPILED_WINDOW_ARGUMENT` for a window |

New refusals (bundles `0.2.1` loaded, which none of its emissions wrote):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-R1004 | `load_bundle` of a bundle described above | loaded | `COMPILED_AGGREGATE_ARGUMENT`, or `COMPILED_WINDOW_ARGUMENT` for a window |

No PIE code or detail name is added. What `compile_query`, `export_bundle`
and `emit-sql` produce, its SQL bytes included, is unchanged, and so are CLI
JSON v1, project JSON v2 and the Python API shapes.
