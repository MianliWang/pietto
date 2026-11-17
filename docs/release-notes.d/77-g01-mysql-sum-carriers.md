### MySQL project `sum(Int)` of an `INT` field, a non-null field and a `let`

- A MySQL project now also emits, in the S02 cell that the [language
  page](../language.md#aggregates-and-grouping) states, a `sum` of a
  non-null `BIGINT` field or of a nullable or non-null `INT` field, and a
  `sum` whose argument is the name of a value `let` of the query whose
  value, as written, reads one `BIGINT` or `INT` field, nullable or not
  (`let t = n`, then `sum(t)`). Every `let` of the query must be such a
  binding, read at least once, and only as the whole argument of a `sum`;
  more than one is allowed. A read qualified by its source's name,
  parentheses and an identity `def`, in the `sum`, in its `let` or around
  the `let`'s name, count as before.
- The `sum` is the cell's guarded `SUM` over the field, a nullable `Int`
  (`my_signed_int`) whatever the field's width: NULL for no or only NULL
  values, the exact sum in range, and error 1690 (SQLSTATE 22003) outside
  signed 64 bits, never a clamped value. A `let` is read through its own
  stage, as the PostgreSQL SQL of the same query reads it. Each R13
  requirement carries the evidence `target_checked_signed64_narrowing`.
- PostgreSQL SQL and every other public PostgreSQL output are unchanged.
  Compiled bundles and live templates replay the same SQL. Emission derives
  the cell from the plan and the written query, and plain verification
  re-derives emission's refusals; compiled replay derives it from its
  records, with the `let` stages and the `BIGINT` or `INT` carrier.
- The two-database qualification of these forms, the G1 campaign of the
  MySQL catch-up work package on PostgreSQL 18.6 and MySQL 8.4.12, has not
  run on this change.
- Every other MySQL project `sum(Int)` keeps the refusal it has without
  this note, object for object (PIE-B1004
  `sum_int_aggregate_range_proof_missing` where that is its blocker). Among
  them are a `SMALLINT` field, a `let` chain (`let u = t` over `let t = n`),
  a `let` whose value is anything but one field read, a `let` read in a
  WHERE, as the GROUP BY key, in a `count`, a `min` or anywhere else
  outside a `sum` argument, a value `let` that nothing reads, a relation
  alias, and shapes that the S02 cell excludes, such as ORDER BY, a header
  parameter, a bind-safe `?`, an aggregate beside the `sum` other than
  those the G2 note below opens, and a `sum` outside every cell beside it.
  R2 `save_recoverable` and `recover` refuse a MySQL query of these forms
  with PIE-R1004 (`detail` `PUBLIC_R2_UNQUALIFIED_FORM`), as for the other
  forms that MySQL opened after `0.1.11`.
- Under J12 (3), the MySQL project `sum` of an `Int` outside the forms
  that `0.1.12`, this note and the G2 note below open stays beyond the
  MySQL cadence, with the MySQL catch-up work package as its target.

Changed diagnostics: a MySQL statement whose only blockers in `0.2.1` were
PIE-B1004 `sum_int_aggregate_range_proof_missing` at sums of these forms is
now VERIFIED with those blockers gone. A statement still refused reports
exactly the blockers it has without this note, object for object, such a
sum's own included: a sum of a non-null `BIGINT` field beside
`y = sum(a + b)` keeps its PIE-B1004 and the PIE-B1002
`arithmetic_outside_physical_range` of `a + b` that `0.2.1` reports.
