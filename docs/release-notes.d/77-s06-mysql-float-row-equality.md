### Float equality of two row reads in MySQL projects

- `emit-sql --project --dialect mysql` now emits a `Float` comparison whose
  two operands both read rows, in the forms the Phase77 S06 native
  qualification matched on MySQL 8.4.12 and nothing else:
  - `a == b`, `a != b`, `not (a != b)`, `same_value(a, b)` or
    `not same_value(a, b)` of two different nullable `Float` fields of the
    one source a query reads, as the whole value of one SELECT item
    (`r = f1 == f2`) or as its whole WHERE (`where f1 != f2`);
  - an INNER JOIN on `==` or `not (!=)`, or a LEFT JOIN on `==`, of a
    nullable `Float` field of each of two sources over different tables, as
    the whole `on` or followed by `and` one `==` of a NOT NULL binary-collation
    `Text` key of width 64 or 1000 on each side
    (`inner join i on i.v == o.v and i.k == o.k`).

  The query has no other expression, clause, JOIN or header parameter,
  reads no other query, declares no `let` (a relation alias such as
  `let i = items` included, read or not) and no named window, and none of
  its expressions is a `def` call. Its other SELECT items read a non-null
  `Int` (BIGINT) field, and beside a WHERE or a JOIN also a nullable `Float`
  field. Its sources have, selected or not (the CTE of a WHERE or a JOIN
  writes them all), exactly the fields of the qualification's tables in
  their order: a non-null `Int` (BIGINT) and two nullable `Float` fields for
  a same-row form; a non-null `Int` (BIGINT), a nullable `Float` and NOT
  NULL binary `Text` fields of width 64 and 1000 for each JOIN input.
  Operands and keys may be written in either order and the `Float`
  comparison comes first in the `on`. The statement is the PostgreSQL one
  in MySQL spelling, with `<=>` for `same_value`, and compiled replay and
  the live template carry the same SQL.
- The forms keep the existing [Float values](../language.md#float-values)
  contract (`-0.0 == 0.0`, stored bits kept, joins keep bag multiplicity),
  which the raw MySQL statements matched under the default, hash and
  nested-loop JOIN strategies, beside a 64- and a 1000-character key.
  PostgreSQL output is unchanged.
- R2 `save_recoverable` and `recover` refuse a query of these forms with
  PIE-R1004 (`detail` `PUBLIC_R2_UNQUALIFIED_FORM`) before any workspace
  access or connection, since no native qualification has run its refined
  statement (see the [R2 boundary](../execution.md#known-limitations)).
- The candidate emission experiment passed on 2026-11-13: one run per
  database, PostgreSQL 18.6 (`postgres-20261113T160609Z-6419e80a65ff82e4`)
  and MySQL 8.4.12 (`mysql-20261113T160609Z-263ec360bd590fc7`), each judged
  its 25 forms MATCHED with no reason against, and the pair judgment found
  the 25 forms and 21 cells `CANDIDATE_EMISSION_QUALIFIED` with no reason
  against. The runs bound this change as first committed on the `0.1.11`
  release commit (tree `ae0bce0a`). D77.50 carries them to the commit that
  integrates this change: the experiment's projects, emitted SQL and
  refusal controls are byte-identical there (sha256, first 16 digits, the
  same on both sides: `sql.json` `618237d3cc7d2984`, `controls.json`
  `8415451073599485`).
- Kept refused on MySQL with PIE-B1003 `comparison_type_pair_not_admitted`,
  as in `0.1.11`: every other `Float` `==`, `!=` or `same_value` of two row
  reads. That includes `any(z.v == o.v for z in z)` and
  `any(not (z.v != o.v) for z in z)`, which returned outer rows twice through
  a materialized semijoin beside a 1000-character key (the Phase72 B10
  class), and `any(z.v != o.v for z in z)`, which matched but stays refused
  (D77.29); `not any(z.v == o.v for z in z)` emits in the forms of
  [Float NOT EXISTS](77-r02-mysql-float-anti-exists.md). It also includes a RIGHT
  JOIN, an INNER `!=`, a LEFT `not (!=)`, a key that is not such a `Text` key
  of one width on both sides or comes first, the same field or table on both
  sides, a non-null `Float` field, any other SELECT item, and the comparison
  beside or under anything else (`not (a == b)`, `or`, a second comparison,
  ORDER BY, LIMIT, DISTINCT, a window, a WHERE after the JOIN, a second
  JOIN, an upstream query, a `union all` operand), a query that declares a
  header parameter, a `let` (also a relation alias, a chain of them or one
  the query never reads) or a named window, or that calls a `def`, and a
  query whose source has other fields, read or not, or the same fields in
  another order (a `Decimal`, a `Text` of width 255 or 4000, a third
  `Float`, a nullable key, or the same-row table as a JOIN input).
  `same_value` in an `on` has no form on either target. A statement of the
  forms above that emission refuses for another reason, such as an output
  label past 256 characters, reports the `0.1.11` blockers, this PIE-B1003
  included.

Changed diagnostics (programs refused in `0.1.11`; no accepted program
changes; MySQL projects, no message text changed):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | `r = f1 == f2` (also `!=`, `not (!=)`, `same_value`, `not same_value`) as a SELECT item, or as the WHERE, of two nullable `Float` fields of one source | `comparison_type_pair_not_admitted` at the SELECT item or the `where` | none: the statement emits |
| PIE-B1003 | `inner join i on i.v == o.v` (also `not (!=)`, and `left join` on `==`), alone or followed by `and i.k == o.k` of a NOT NULL binary `Text` key of width 64 or 1000 | `comparison_type_pair_not_admitted` at the `on` | none: the statement emits |
