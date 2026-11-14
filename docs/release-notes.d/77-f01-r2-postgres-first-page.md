### PostgreSQL R2 refuses a first page it does not read

On PostgreSQL, on both routes, `save_recoverable` and `recover` now render
the bound query's first page when they prepare it, and refuse a query whose
SQL R2 does not read with `PIE-R1004` (`detail` `REFINEMENT_NATIVE_SQL`)
before any workspace access or connection. Such a query was prepared as any
other: its job and generation were registered, R2 connected, and the
attempt failed closed at its first page. Such forms include those of the
[R2 boundary](../execution.md#known-limitations): conditional CASE, BETWEEN,
literal-list IN, CAST, scalar calls other than `now()` and NOT, an ordered
`first` or `last`, the null-safe comparison of `same_value` wherever it
appears, in a SELECT item, WHERE, a `let` or
[a JOIN `on`](../release-notes.md#null-safe-same_value-in-a-project-join-on),
and a window function argument that reads a header parameter, as
`lag(id, k, f)` does with header parameters `k` and `f`, whose first page R2
could not render.

The check is the last of R2's preparation checks, so a query that another
of them refuses keeps that refusal, and a query that reads `now()` keeps
`PUBLIC_R2_STATEMENT_SNAPSHOT`. It comes before `recover`'s trust check, so
`recover` of such a query with trust records that do not match now reports
`REFINEMENT_NATIVE_SQL` where it reported `PIE-R1008` (`PUBLIC_R2_TRUST`).
It renders the bound query, so `recover` makes it only when its restated
values and parameters bind; otherwise the workspace refuses the
restatement, as before. On MySQL, the refusal of the forms that `0.1.11`
refused (`PUBLIC_R2_UNQUALIFIED_FORM`) does not change, and an R2 attempt
of a query that `0.1.11` compiled and whose SQL R2 does not read still
fails closed at its first page.

Before (measured at `ab594829`, 0.1.12, on Linux with CPython 3.13.13,
without a database, over a workspace that cannot be opened):
`save_recoverable` and `recover` of a PostgreSQL query with
`inner join rhs on same_value(lhs.v, rhs.v)`, or of one that selects
`u = upper(text)`, went on to the workspace, which refused them with
`PIE-R1009` (`WORKSPACE_PARENT`). After: both refuse them with `PIE-R1004`
(`REFINEMENT_NATIVE_SQL`), with or without a `job`; the same JOIN on
`lhs.v == rhs.v` still goes on to the workspace.

Changed diagnostics (no accepted program changes; an R2 attempt that failed
at its first page is refused before it starts):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-R1004 | R2 `save_recoverable` or `recover`, with values and parameters that bind, of a PostgreSQL query whose SQL R2 does not read and that does not read `now()` | the attempt failed closed at its first page | `REFINEMENT_NATIVE_SQL` |
| PIE-R1004 | R2 `recover`, with values and parameters that bind and trust records that do not match, of a PostgreSQL query whose SQL R2 does not read and that does not read `now()` | `PIE-R1008` `PUBLIC_R2_TRUST` | `REFINEMENT_NATIVE_SQL` |

No PIE code or detail name is added: `REFINEMENT_NATIVE_SQL` is the word
R2's page reader already used, and it now reaches callers. Emitted SQL, CLI
JSON v1, project JSON v2, the Python API and the format and records of
compiled bundles are unchanged.
