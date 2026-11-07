### Scalar forms beside a JOIN in PostgreSQL projects

- `emit-sql --project --dialect postgres` now emits a statement with a JOIN
  whose other tables, queries and `let`s, those without a JOIN of their own,
  use a conditional (also a `def` that inlines to one, such as
  `length_band(minutes) == 2`), a comparison chain, `in`, a cast or a scalar
  call: a query the JOIN reads, a `let` with capture lines that a JOIN reads
  LATERAL, and a query that reads the JOIN's rows. Each renders as it does in
  a statement without the JOIN, the CTE of a query the JOIN reads byte for
  byte, and the compiled replay and the live template carry the same SQL. A
  computed column of such a query, a derived `Date` among them, may be an
  equality JOIN key. This closes the two-module example's limitation of
  `0.1.10`: a query whose WHERE calls a def that inlines to a conditional is
  no longer BLOCKED when another query JOINs it.
- Over JOIN rows an aggregate argument that holds a scalar call is emitted
  inside the aggregate, as over one input: `count(lower(r.label))`,
  `count_distinct(trim(r.label))`, `count(len(r.label))`,
  `count(lower(trim(r.label)))`.
- Kept refused: such a form at a joined site, in the joined query's own
  `let`, WHERE or `on` (`where band(r.id) == 2` after the JOIN, or
  `let t = lower(r.label)` with `count(t)`), keeps its `0.1.10` blockers.
- MySQL is unchanged: each of these statements keeps its `0.1.10` blockers
  until its own two-database run.

### `max(a, b)` and `min(a, b)` of two `Date` values in PostgreSQL projects

- On PostgreSQL a project conditional whose values are two `Date` values of
  one carrier is emitted as `CASE`, so `max(a, b)` and `min(a, b)` of two
  `Date` values are too, with compiled replay and the live template, as for
  two `Timestamp` values. MySQL keeps them refused (PIE-B1003
  `conditional_realization_not_admitted`); project `Bool` values stay refused
  on both targets.

Compatibility (PostgreSQL projects; MySQL output is unchanged):

| Input | Before (0.1.10) | Now |
| --- | --- | --- |
| A query whose WHERE calls `length_band(minutes) == 2`, read by another query's JOIN | BLOCKED PIE-B1003 `scalar_projection_requires_later_slice` at each SELECT item of the JOIN query, then `join_shape_not_admitted_in_slice7` | VERIFIED |
| `count(lower(r.label))` over the rows of a JOIN | BLOCKED PIE-B1003 `operator_not_implemented_in_slice6`, `join_shape_not_admitted_in_slice7` | VERIFIED |
| `max(a, b)`, `min(a, b)`, `a if c else b` of two `Date` values | BLOCKED PIE-B1003 `conditional_realization_not_admitted` | VERIFIED |

Changed diagnostics (PostgreSQL projects; no message text changed): a
statement with a JOIN that reads a table or query whose own form stays
refused is now refused at that form, with its own blocker and suggestion.

| Input | Before (0.1.10) | Now |
| --- | --- | --- |
| A query with `m = matches(label, "a.*")` read by another query's JOIN | BLOCKED PIE-B1003 `scalar_projection_requires_later_slice` at each SELECT item of the JOIN query, then `join_shape_not_admitted_in_slice7` (no location) | BLOCKED PIE-B1003 `scalar_call_signature_not_admitted` at the `matches` select item |
