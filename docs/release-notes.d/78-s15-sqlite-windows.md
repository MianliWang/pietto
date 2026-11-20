### Windows in SQLite projects (alpha)

`pietto emit-sql --project ... --dialect sqlite`, `compile_sql`,
`compile_all_sql` and `compile_query(dialect="sqlite")` now write windows
over one `sqlite.table` source read without `group by` or an aggregate,
and the `sqlite_file` route runs them. See
[SQLite project mode](../spec/sqlite-project-v1.md#admission).

- `row_number`, `rank` and `dense_rank`; `count()`; and `count`, `min` and
  `max` of an `Int` or `Float` field, keyed by fields of the source, in a
  `rows`, `range` or `groups` frame. `count()` with no partition or order
  key takes only the default frame, where it counts every row, since
  another frame counts rows in the order SQLite scans them.
- `sum` of an `Int` field whose contract `int_range` lies on one side of
  zero, in a frame from `unbounded preceding` to `current row` or
  `unbounded following`, the omitted frame included. It fails with
  SQLite's `integer overflow` exactly where PostgreSQL's exact sum raises
  SQLSTATE 22003, except that under a `limit` without an `order by` a
  partial sum that no delivered row needs may overflow with no error.
- Each window is written inline as `OVER (...)`, with `COLLATE BINARY` at
  each `Text` key, a NULLS clause at each order key and the frame the plan
  resolves written out; `exclude no others`, which excludes nothing, is
  left out.

New refusals, each BLOCKED with PIE-B1003: `sqlite_window_not_admitted` for
any other window, a named window, a window over grouped rows, a `range`
offset, `count()` with no key in another frame, or an `exclude` other than
`exclude no others`, which SQLite computes again for every row; and
`sqlite_window_sum_frame_not_admitted` for a window `sum` in another frame,
which SQLite can fail where every frame's sum fits. A window `sum` over a
mixed-sign `int_range` is PIE-B1004 `sum_int_aggregate_range_proof_missing`.

Compatibility: PostgreSQL, MySQL and DuckDB SQL bytes, contracts and
diagnostics are unchanged. Against `0.2.2`, which refused every window over
a `sqlite.table` source, these outputs change:

- A statement with windows that `0.2.2` refused as a whole with
  `sqlite_relation_shape_not_admitted` is now emitted, or reports only the
  rules it breaks, such as `sqlite_window_not_admitted` or
  `sqlite_window_sum_frame_not_admitted` at the window, or
  `sum_int_aggregate_range_proof_missing` at a window `sum`. A window over
  grouped rows still reports `sqlite_relation_shape_not_admitted`, now
  beside `sqlite_window_not_admitted` at the window.
- The suggestion of `sqlite_relation_shape_not_admitted` changes for every
  statement it refuses, a JOIN or `distinct` included, and scripts that
  match its text must follow. It now reads `SQLite emission admits one
  source read, or INNER and LEFT JOINs of sources, with where, group by,
  having, order by, limit and select, and windows over one source read
  without group by; qualify, distinct, set operations, relation lets and
  reads of another table or query are not available on SQLite`.
- The `sqlite_file` route's authorizer also allows the functions
  `row_number`, `rank` and `dense_rank`.

Known limitations:

- These forms are qualified on the measured SQLite library of the first
  tier, release `3.53.1` with its source id and compile options, under
  CPython 3.13.13 and 3.12.13 on Linux x86-64, by native cells and a
  PostgreSQL replay of their bytes; no other build or platform is
  qualified.
- A window `count`, `min` or `max` of a `Float` and `count()` over a window
  with no partition or order key have native cells only, since PostgreSQL
  project emission does not write them.
- `qualify`, `lag`, `lead`, `ntile`, `first_value`, `last_value`,
  `nth_value`, `percent_rank`, `cume_dist`, a window `avg` and windows over
  joined rows are not available on SQLite.
