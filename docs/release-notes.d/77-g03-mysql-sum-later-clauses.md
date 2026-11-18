### MySQL project `sum(Int)` with HAVING, ORDER BY, LIMIT and DISTINCT

- A MySQL project now also emits, in the S02 cell that the [language
  page](../language.md#aggregates-and-grouping) states as the G1 and G2
  notes above widen it, a query with at least one GROUP BY key that also
  holds HAVING, ORDER BY, LIMIT or DISTINCT. Each HAVING line compares one
  selected output, named alone, with an unsigned `Int` literal (`==`, `!=`,
  `<`, `<=`, `>`, `>=`), the lines joined by `and`; the output is a
  `BIGINT` or `INT` key or an aggregate other than `avg`, and a line that
  reads a `sum` is its block's only line. Each ORDER BY key is a selected
  output named alone, ascending or `desc`: a `BIGINT`, `INT` or `VARCHAR`
  key or an aggregate other than `avg`. A `limit n` of 1 or more follows
  an ORDER BY whose first key is an aggregate, and `select distinct:`
  stands beside no `avg`. `order by x desc` on one line, `asc` written out,
  a `table` declaration, a `def` call in place of the HAVING literal it
  returns and the spellings the notes above take count as before.
- Each `sum` is the cell's guarded `SUM` inside the aggregation stage, a
  nullable `Int` (`my_signed_int`): NULL for no or only NULL values, the
  exact sum in range, and error 1690 (SQLSTATE 22003) outside signed 64
  bits, which fails the whole statement, never a clamped value. HAVING,
  ORDER BY, LIMIT and DISTINCT read the sum's column of that stage, as the
  PostgreSQL SQL of the same query reads its checked sum; they, the keys,
  the other aggregates, FROM, WHERE and GROUP BY are the MySQL SQL of the
  same query with each `sum` written `max`, which MySQL already emits. A
  HAVING line that reads a `sum` reads it in every group, so an
  out-of-range sum fails the statement even where the line would drop that
  group, and every group that HAVING keeps is computed whether or not the
  LIMIT returns it. Each R13 requirement of a `sum` carries the evidence
  `target_checked_signed64_narrowing`.
- PostgreSQL SQL and every other public PostgreSQL output are unchanged.
  Compiled bundles and live templates replay the same SQL. Emission derives
  the clauses' law from the plan and the written query, and plain
  verification re-derives emission's refusals; compiled replay derives it
  from its records, following each clause's reads to the aggregate's keys
  and values.
- The two-database qualification of these forms, the G3 campaign of the
  MySQL catch-up work package on PostgreSQL 18.6 and MySQL 8.4.12, has not
  run on this change.
- Every other MySQL project `sum(Int)` keeps the refusal it has without
  this note, object for object (PIE-B1004
  `sum_int_aggregate_range_proof_missing` where that is its blocker). Among
  them are a HAVING line that reads a `sum` beside another line, one that
  compares two outputs, uses `or`, reads a `Text` key or an `avg`, a LIMIT
  with no ORDER BY, after an ORDER BY of keys only or of a key first,
  `limit 0`, an ORDER BY key that is an `avg` or S02's own `SMALLINT` key,
  DISTINCT beside an `avg`, any of these clauses with no GROUP BY key, and
  a header parameter, a bind-safe `?` and a relation alias as before. R2
  `save_recoverable` and `recover` refuse a MySQL query of these forms
  with PIE-R1004 (`detail` `PUBLIC_R2_UNQUALIFIED_FORM`), as for the other
  forms that MySQL opened after `0.1.11`.
- Under J12 (3), the MySQL project `sum` of an `Int` outside the forms
  that `0.1.12`, the G1 and G2 notes and this note open stays beyond the
  MySQL cadence, with the MySQL catch-up work package as its target.

Changed diagnostics: a MySQL statement whose only blockers in `0.2.1` were
PIE-B1004 `sum_int_aggregate_range_proof_missing` at sums of these forms is
now VERIFIED with those blockers gone, such as `group by k` selecting `k`
and `sum(a)` with `having:` `x > 1`, or with `order by:` `k`, and the
[language page](../language.md#mysql-project-sumint-forms)'s
`query totals` with `order by customer`. A statement still refused reports
exactly the blockers it has without this note, object for object: that
query with `limit 2` after its ORDER BY keeps its one PIE-B1004.
