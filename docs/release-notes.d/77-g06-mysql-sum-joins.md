### MySQL project `sum(Int)` over JOINs

- A MySQL project now also emits a query in the S02 cell that the
  [language page](../language.md#aggregates-and-grouping) states, as the
  G1 and G2 notes above widen it, that reads its rows through JOINs
  instead of one source: the FROM reads a source of the module by its own
  name, and one or more `inner`, `left` or `right` JOINs follow, each of a
  `let x = S` binding of a source of the module (the FROM's included, a
  self-join), before the query's value `let`s and WHERE. Each `on` is a
  conjunction of `==` equalities of an `Int` field of the joined input and
  one of an earlier input, in either order, one at least, and, in an
  `inner` or `left` JOIN, comparisons of a non-null `Int` field of the
  joined input by `>` or `>=` with an `Int` literal written in the `on`
  (`left join i on i.order_id == orders.id and i.units > 0`). A sum, the
  other aggregates and the keys read fields of any input, qualified by the
  input's name or bare where one input has the field, under G2's law; a
  source may declare fields that the query never reads. Parentheses, a
  `table` declaration and a `group by:` block count as before, a
  comparison chain in an `on` as its `and`s, and a relationship call there
  as its body for its linking equalities only.
- Each `sum` is the cell's guarded `SUM` over the JOIN stage's column, a
  nullable `Int` (`my_signed_int`): NULL for no or only NULL values, a row
  that an outer JOIN NULL-extends included, the exact sum in range, and
  error 1690 (SQLSTATE 22003) outside signed 64 bits, which fails the whole
  statement, never a clamped value; a row that a JOIN drops never reaches
  a sum. The JOIN stage, the keys, the other aggregates, WHERE and GROUP BY
  are the MySQL SQL of the same query with each `sum` written `max`, which
  MySQL already emits, and S03's JOIN forms J1 to J3 keep their SQL. Each
  R13 requirement of a `sum` carries the evidence
  `target_checked_signed64_narrowing`.
- PostgreSQL SQL and every other public PostgreSQL output are unchanged.
  Compiled bundles and live templates replay the same SQL. Emission derives
  the JOIN law from the plan and the written query, and plain verification
  re-derives emission's refusals; compiled replay derives it from its
  records and the pure boundary from its document, each with every JOIN's
  kind, inputs and `on`.
- The two-database qualification of these forms, the G6 campaign of the
  MySQL catch-up work package on PostgreSQL 18.6 and MySQL 8.4.12, has not
  run on this change.
- Every other MySQL project `sum(Int)` over a JOIN keeps the refusal it has
  without this note, object for object. Among them are a FULL JOIN
  (PIE-B1003 `mysql_full_join_approved_non_support`), a CROSS JOIN, an `on`
  with no linking equality (`on True`, an `or` at its top, a literal
  comparison alone), an `on` with another conjunct (a `Text` equality, an
  `is None` test, a literal comparison by another operator, of a nullable
  field or of an earlier input, with the literal first, negative, a `def`
  argument or in a relationship's body, or in a `right` JOIN, a `def`
  call), a JOIN of a query or table or with no `let`, a JOIN in an upstream
  definition, and HAVING, ORDER BY, LIMIT, DISTINCT, a relation alias, a
  header parameter or a bind-safe `?` over JOIN rows (PIE-B1004
  `sum_int_aggregate_range_proof_missing` where that is the blocker).
  Project semantics still refuses a `sum` of rows that a JOIN may repeat
  (PIE-B1003 `semantic_result_unsuccessful`) and a conditional sum over
  JOIN rows (PIE-S2334). R2 `save_recoverable` and `recover` refuse a MySQL
  query of these forms with PIE-R1004 (`detail`
  `PUBLIC_R2_UNQUALIFIED_FORM`), as for the other forms that MySQL opened
  after `0.1.11`.
- Under J12 (3), the MySQL project `sum` of an `Int` outside the forms
  that `0.1.12`, the G1 to G5 notes, this note and the G7 and G8 notes below open
  stays beyond the MySQL cadence, with the MySQL catch-up work package as
  its target.

Changed diagnostics: a MySQL statement whose only blockers in `0.2.1` were
PIE-B1004 `sum_int_aggregate_range_proof_missing` at sums of these forms is
now VERIFIED with those blockers gone, such as `from orders`, `let i =
items`, `inner join i on i.order_id == orders.id`, `group by orders.id`
selecting `orders.id`, `sum(i.qty)` and `sum(i.units)`, or S03's JOIN
neighbours with a LEFT JOIN of J1, J2's `on` reversed, two sums or a WHERE.
A statement still refused reports exactly the blockers it has without this
note, object for object: the same query with `on True` keeps both sums'
PIE-B1004.
