### MySQL project `sum(Int)` with header parameters and bind-safe literals

- A MySQL project now also emits a `sum` of an `Int` in the S02 cell that
  the [language page](../language.md#aggregates-and-grouping) states, as
  the G1 to G4 notes above widen it, when the statement holds placeholders.
  The selected query may declare header parameters of type `Bool`, `Int`,
  `Float` or `Text`, nullable or not (`query result(lo: Int):`), read or
  not. A parameter is read only in the query's own WHERE, over its source
  or a plain upstream, where every operation over the read up to the
  WHERE's predicate has a `Bool` result (such as a comparison, `is None`,
  `not`, `and` or `or`; a `Bool` read may also stand alone), so no check of
  the statement waits for a bound value; or as the right side of a HAVING
  line that reads a `sum` and is its block's only line, the parameter a
  non-null `Int` (`x > lo`). Under `bind-safe` a WHERE literal of the
  query or of a plain upstream is a placeholder bound with its value, a
  negative literal a minus over its magnitude's, where the MySQL SQL binds
  one; a literal it keeps inline, such as a `coalesce` default, a
  `contains` needle, a HAVING literal or a LIMIT, stays inline
  (`where coalesce(a, 0) > 3` binds the 3 alone).
- Each `sum` is the cell's guarded `SUM`, a nullable `Int`
  (`my_signed_int`): NULL for no or only NULL values, the exact sum in
  range, and error 1690 (SQLSTATE 22003) outside signed 64 bits, which
  fails the whole statement, never a clamped value. Everything else is the
  MySQL SQL of the same statement under the same header and policy with
  each `sum` written `max`, which MySQL already emits: every placeholder,
  its cast, owner, physical type and server index, and every fixed value.
  A parameter that nothing reads puts nothing in the SQL; `execute()`
  still takes its value. The emission document lists no
  `binding_obligations`. Each R13 requirement of a `sum` carries the
  evidence `target_checked_signed64_narrowing`.
- PostgreSQL SQL and every other public PostgreSQL output are unchanged.
  Compiled bundles and live templates replay the same SQL, and a compiled
  template re-derives the statement for each binding with the same bytes.
  Emission derives the placeholders' law from the plan and the written
  definitions, and plain verification re-derives emission's refusals;
  compiled replay derives it from its records and the pure boundary, whose
  schema holds no header parameter, from its document's bind-safe
  parameters.
- The two-database qualification of these forms, the G5 campaign of the
  MySQL catch-up work package on PostgreSQL 18.6 and MySQL 8.4.12 over the
  public, raw prepared and text routes, has not run on this change. That
  the G3 note's evaluation rules hold with a bound value in place of each
  literal, under prepared execution too, is expected from the SQL, not
  observed.
- Every other MySQL project `sum(Int)` keeps the refusal it has without
  this note, object for object (PIE-B1004
  `sum_int_aggregate_range_proof_missing` where that is its blocker). Among
  them are a `Decimal(p, s)`, `Date`, `Timestamp` or `UUID` parameter,
  read or not, which keeps its PIE-B1003
  `query_parameter_type_not_admitted_on_target` alone, a `Float` parameter
  that is read, a read under a minus or `Int` arithmetic in the WHERE
  (`id > -lo`, `id > lo + 1`, which leave a binding obligation), a
  parameter or a placeholder beside a HAVING line that reads no `sum`, a
  nullable parameter on a HAVING line, and a bind-safe literal in an
  aggregating upstream's WHERE or in a conditional `sum`. R2
  `save_recoverable` and `recover` refuse a MySQL query of these forms with
  PIE-R1004 (`detail` `PUBLIC_R2_UNQUALIFIED_FORM`), as for the other forms
  that MySQL opened after `0.1.11`.
- Under J12 (3), the MySQL project `sum` of an `Int` outside the forms
  that `0.1.12`, the G1 to G4 notes, this note and the G6 to G8 notes
  below open stays beyond the MySQL cadence, with the MySQL catch-up work package as
  its target.

Changed diagnostics: a MySQL statement whose only blockers in `0.2.1` were
PIE-B1004 `sum_int_aggregate_range_proof_missing` at sums of these forms is
now VERIFIED with those blockers gone, such as `query result(lo: Int):`
with `where id > lo`, `group by k` selecting `k` and `sum(a)`, or the same
statement with no parameter and `where id > 3` under `bind-safe`. A
statement still refused reports exactly the blockers it has without this
note, object for object: `where id > -lo` keeps its one PIE-B1004.
