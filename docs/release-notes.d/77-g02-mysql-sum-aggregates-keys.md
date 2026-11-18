### MySQL project `sum(Int)` beside other aggregates and by more keys

- A MySQL project now also emits, in the S02 cell that the [language
  page](../language.md#aggregates-and-grouping) states as the G1 note above
  widens it, a query whose aggregation holds any number of `sum`s (one
  argument summed twice included) and beside them any `count_distinct` of
  a `BIGINT`, `INT` or `VARCHAR` field and any `max` or `avg` of a
  `BIGINT` or `INT` field, each a direct read and the whole value of a
  SELECT item, beside `count`, `count()` and `min` as before. It may group
  by any number of `BIGINT`, `INT` or `VARCHAR` fields, nullable or not,
  each selected under any names, more than once, or not at all; the S02
  cell's own key, one non-null `Int` field of any storage beside sums,
  counts and mins only, stays as before. A read qualified by its source's
  name, parentheses and an identity `def` count as before.
- Each `sum` is the cell's guarded `SUM`, a nullable `Int`
  (`my_signed_int`): NULL for no or only NULL values, the exact sum in
  range, and error 1690 (SQLSTATE 22003) outside signed 64 bits, which
  fails the whole statement, never a clamped value. The keys, the other
  aggregates, FROM, WHERE and GROUP BY are the MySQL SQL of the same query
  with each `sum` written `max`, which MySQL already emits; a `let` is read
  through its own stage as G1 reads it. Each R13 requirement of a `sum`
  carries the evidence `target_checked_signed64_narrowing`.
- PostgreSQL SQL and every other public PostgreSQL output are unchanged.
  Compiled bundles and live templates replay the same SQL. Emission derives
  the cell from the plan and the written query, and plain verification
  re-derives emission's refusals; compiled replay derives it from its
  records, each with the keys' and the other aggregates' field storages.
- The two-database qualification of these forms, the G2 campaign of the
  MySQL catch-up work package on PostgreSQL 18.6 and MySQL 8.4.12, has not
  run on this change.
- Every other MySQL project `sum(Int)` keeps the refusal it has without
  this note, object for object (PIE-B1004
  `sum_int_aggregate_range_proof_missing` where that is its blocker). Among
  them are another aggregate beside a `sum` (`stddev`, `variance`,
  `pvariance`, `pstdev`, `median`, `quantile`, `string_agg`, a conditional
  `sum` or count, `any`, `all`, a `count_distinct` of two fields), a `max`,
  `avg` or `count_distinct` of an expression (`avg(k * 2)`), of a `let`
  name or of a field of another storage, a GROUP BY key of another storage
  (a `Bool` included), HAVING, ORDER BY, LIMIT and DISTINCT other than
  the G3 note below opens, a relation alias other than the G4 note below
  opens, and a header parameter and a bind-safe `?` other than the G5
  note below opens. R2
  `save_recoverable` and
  `recover` refuse a MySQL query of these forms with PIE-R1004 (`detail`
  `PUBLIC_R2_UNQUALIFIED_FORM`), as for the other forms that MySQL opened
  after `0.1.11`.
- Under J12 (3), the MySQL project `sum` of an `Int` outside the forms
  that `0.1.12`, the G1 note, this note and the G3 to G5 notes below open
  stays beyond the MySQL cadence, with the MySQL catch-up work package as
  its target.

Changed diagnostics: a MySQL statement whose only blockers in `0.2.1` were
PIE-B1004 `sum_int_aggregate_range_proof_missing` at sums of these forms is
now VERIFIED with those blockers gone, such as `group by k` selecting `k`,
`sum(a)` and `avg(a)`, `group by a` selecting `a` and `sum(b)`, and
`group by k, id`. A statement still refused reports exactly the blockers
it has without this note, object for object: `group by tag` selecting
`tag`, `sum(n)`, `sum(a + b)` and `avg(c)` keeps the first sum's PIE-B1004
and the PIE-B1002 `arithmetic_outside_physical_range` of `a + b`.
