### R2 refuses the MySQL forms that `0.1.11` refused

On MySQL, `save_recoverable` and `recover` refuse a query in a form that
`0.1.11` refused, one of the forms this release opens on MySQL, with
`PIE-R1004` (`detail` `PUBLIC_R2_UNQUALIFIED_FORM`) before any workspace
access or connection: no native qualification has run R2's refined
statement of any of them. This check does not apply to `execute()`,
`save()` or bundles, and R2 of a PostgreSQL query or of a MySQL query that
`0.1.11` compiled does not change.

The check is R2's last, so a query that another R2 check refuses keeps
that refusal: a paired form (`PUBLIC_R2_PAIRED_FORM`), a query that reads
`now()` (`PUBLIC_R2_STATEMENT_SNAPSHOT`), a `Float` GROUP BY key form
(`REFINEMENT_COMPARISON_DOMAIN`) when R2 prepares it, and a `Timestamp`
parameter selected as an output (`MEANING_OUTPUT`, as in `save()`) when
its values and parameters bind. `recover` makes the check also when its
restated values or parameters cannot bind (see the
[R2 boundary](../execution.md#known-limitations)).

Changed diagnostics (programs refused in `0.1.11`; no accepted program
changes):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-R1004 | R2 `save_recoverable` or `recover` of a MySQL query in a form this release opens: [`Float` statistics](77-s05-mysql-float-statistics.md), [`Float` row equality](77-s06-mysql-float-row-equality.md), [typed header parameters](77-s09-mysql-typed-parameters.md), [`lpad`](77-s12-mysql-lpad-and-now.md), [`first` and `last`](77-s13-mysql-first-and-last.md), [checked `Int` and `sum(Int)`](77-s01-mysql-checked-int-and-sum.md), [conditionals, JOINs and two-level sums](77-s03-mysql-conditional-join-two-level-sums.md), [`%`](77-s15-mysql-remainder.md), [`Float` `not any`](77-r02-mysql-float-anti-exists.md) and [`same_value` in a JOIN `on`](77-s06-nullsafe-join.md) | not reachable: the query did not compile | `PUBLIC_R2_UNQUALIFIED_FORM` |
| PIE-R1004 | R2 `recover`, with restated values or parameters that cannot bind, of a MySQL query with [`Float` GROUP BY keys](77-s07-mysql-float-keys.md) or a `Timestamp` [header parameter](77-s09-mysql-typed-parameters.md) selected as an output | not reachable: the query did not compile | `PUBLIC_R2_UNQUALIFIED_FORM` |
