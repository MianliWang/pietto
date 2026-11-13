### Float GROUP BY keys in MySQL projects

- `emit-sql --project --dialect mysql` now emits a `Float` GROUP BY key in
  the forms the Phase77 S07 native qualification judged ready on MySQL
  8.4.12, and nothing else: a query over one source read directly that
  groups by the keys and selects exactly those keys in that order and then
  `count()` (`group by: price` / `select: price, n = count()`).

  The keys are different fields, as `x`, `x, y` or `x, k, y`, where `x` and
  `y` are `Float` fields both non-null or both nullable and `k` is a NOT NULL
  binary-collation `Text` field of width 64. The statement holds no other
  select item, aggregate, clause, JOIN, upstream query or header parameter,
  declares no `let` (a relation alias such as `let s = items` included, read
  or not) and no named window, and calls no `def`. Fields the statement does
  not read and the source's unique keys do not matter, and a table or query
  declaration and any output or field names give the same statement. The
  statement is the PostgreSQL one in MySQL spelling, and compiled replay and
  the live template carry the same SQL.
- The forms keep the existing [Float values](../language.md#float-values)
  contract (`-0.0 == 0.0`, each group one member's value). PostgreSQL
  output is unchanged.
- The candidate emission experiment passed on 2026-11-13: one run per
  database, PostgreSQL 18.6 (`postgres-20261113T170618Z-f4eb8fe512b2c208`)
  and MySQL 8.4.12 (`mysql-20261113T170618Z-e0b38b159641d81d`), each
  judged its 8 forms MATCHED with no reason against, and the pair judgment
  found the 8 forms and 6 cells `CANDIDATE_EMISSION_QUALIFIED` with no
  reason against. The runs bound this change as first committed on the S06
  change (tree `3e8a3a92`). D77.50 carries them to the commit that
  integrates this change: the experiment's projects, emitted SQL, refusal
  controls and both runs' compile records are byte-identical there (sha256,
  first 16 digits, the same on both sides: `sql.json` `7861de97a43d65cd`,
  `controls.json` `3efcb9977df291ac`, the PostgreSQL compile record
  `ebb510d9d3a33587` and the MySQL one `bb7e9f753fccd6b3`).
- Kept refused on MySQL as in `0.1.11`, with PIE-B1003
  `group_key_type_outside_reviewed_comparison_domain`: a `Text` key of width
  1000 (the MySQL 8.4.12 deduplication kept `-0.0` and `0.0` apart beside
  it), 255 or 32, or a nullable one; a non-null and a nullable `Float`
  together, the `Text` key first or last, four keys, an `Int` key; another
  aggregate, a `count` with an argument, a key not selected or selected in
  another order, `count()` before the keys; a WHERE, ORDER BY or LIMIT, a
  JOIN, an upstream query, a header parameter, a `let`, a relation alias, a
  named window or a `def` call; and a window `percent_rank` or `cume_dist`
  result as a key. A MySQL `Float` DISTINCT
  (`distinct_field_comparison_domain_unsupported`) and UNION DISTINCT
  (`set_row_equivalence_domain_unsupported`), whose native qualification
  witnessed no on-disk deduplication, `Float` INTERSECT and EXCEPT, a
  `count_distinct` of a `Float`
  (`count_distinct_argument_outside_reviewed_int_domain`) and a `Float`
  window key stay refused as well. A refused statement, one of the forms
  above refused for another reason (an unreviewed target release, say)
  included, reports the blockers `0.1.11` reports.

Changed diagnostics (programs refused in `0.1.11`; no accepted program
changes; MySQL projects, no message text changed):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | `group by` one to three keys of the forms above, selected in order and then `count()` | `group_key_type_outside_reviewed_comparison_domain` at the GROUP BY item | none: the statement emits |
