### MySQL project conditional `sum` with compound tests, beside other aggregates

- A MySQL project now also emits a conditional sum `sum(o.f for o in group
  if TEST)` in the S02 cell that the [language
  page](../language.md#aggregates-and-grouping) states as the G1 and G2
  notes above widen it, where it counts as a `sum`: beside any number of
  sums, conditional sums, `count`, `count()`, `min`, `count_distinct`,
  `max` and `avg`, under G2's keys, a WHERE and G1's `let`s. Its `f` is a
  `BIGINT` or `INT` field, nullable or not, read through the generator's
  variable (any name), and it is the whole value of a SELECT item. Its
  TEST is `not`, `and`, `or` and parentheses, to any depth, over a read of
  a `Bool` field, that read's `is None`, and a `BIGINT` or `INT` field, or a
  GROUP BY key of one read by its own name, `>` an `Int` literal written
  `N` or `-N`. A `def` call in TEST counts as what it inlines to, with or
  without arguments, and a read qualified by its source's name counts as
  before, so S03's C1 to C4 written with parentheses, a qualified key or a
  `def` are in the cell too. Under `bind_safe_literals` a literal in TEST
  stays in the SQL, as an aggregate argument's does, so C3 and every such
  statement without another literal emit their `preserve_literals` SQL.
- Each conditional sum is S03's `COALESCE(` guarded `SUM` of `CASE WHEN TEST
  THEN x END` `, 0)`, a non-null `Int` (`my_signed_int`): 0 when no row's
  test is True (over no rows too), the exact sum in range, and error 1690
  (SQLSTATE 22003) outside signed 64 bits, which fails the whole statement,
  never a clamped value. TEST is read with SQL's three-valued logic, as on
  PostgreSQL, so a NULL test adds nothing. Every other part of the
  statement is the MySQL spelling of the PostgreSQL SQL of the same query.
  Each R13 requirement of a conditional sum carries the evidence
  `target_checked_signed64_narrowing`.
- PostgreSQL SQL and every other public PostgreSQL output are unchanged.
  Compiled bundles and live templates replay the same SQL. Emission derives
  the cell from the plan with every `def` call inlined, not from the
  written spans, and plain verification re-derives emission's refusals;
  compiled replay derives it from its records and the pure boundary from
  its document, each with the test's operators, literals and field
  storages.
- The two-database qualification of these forms, the G7 campaign of the
  MySQL catch-up work package on PostgreSQL 18.6 and MySQL 8.4.12, has not
  run on this change.
- Every other MySQL project conditional `sum` keeps the refusal it has
  without this note, object for object (PIE-B1004
  `sum_int_aggregate_range_proof_missing` where that is its blocker). Among
  them are another comparison operator (`>=`, `<`, `<=`, `==`, `!=`), `is
  None` of an `Int` field, `is not None`, two fields compared, a literal on
  the left, a literal written `+N` or `-(-N)`, literal arithmetic, a
  comparison with a `Bool` literal, a `SMALLINT` field compared or summed
  or a `SMALLINT` key read in TEST, S02's own `SMALLINT` reads (its
  `SMALLINT` key, or a `count` or `min` of a `SMALLINT` field) beside a
  conditional sum of any supported field, an argument that
  is an expression or a `def` call, the conditional count, a conditional
  sum inside an
  expression or over JOIN rows, and, in a statement with a conditional
  sum, HAVING, ORDER BY, LIMIT, DISTINCT, a header parameter, a bind-safe
  `?`, a relation alias, an unread window, an upstream query, an imported
  source and a JOIN, which the G3 to G6 notes above open beside other sums
  only. R2 `save_recoverable` and `recover` refuse a MySQL
  query of these forms with PIE-R1004 (`detail`
  `PUBLIC_R2_UNQUALIFIED_FORM`), as for the other forms that MySQL opened
  after `0.1.11`.

Changed diagnostics: a MySQL statement whose only blockers in `0.2.1` were
PIE-B1004 `sum_int_aggregate_range_proof_missing` at sums of these forms is
now VERIFIED with those blockers gone, such as `group by customer` selecting
`customer` and `sum(o.amount for o in group if o.flag and o.id > 3)`, or S03's
C3 under `bind_safe_literals`. A statement still refused reports exactly the
blockers it has without this note, object for object: C1 beside
`n = sum(1 for o in group if o.flag)` keeps the sum's PIE-B1004 and the
count's PIE-B1003 `conditional_count_not_admitted_on_target`.
