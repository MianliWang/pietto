### MySQL project conditional, JOIN and two-level `sum(Int)`

- A MySQL project now emits each `sum` of an `Int` of a statement that is,
  names aside, one of the nine forms that the [language
  page](../language.md) states: the conditional sums C1 to C4
  (`sum(o.amount for o in group if o.flag)` per `INT` key over a nullable
  or a non-null `BIGINT`, `if not o.flag` and `if o.flag is None` without a
  key, and `if o.id > L` for an `Int` literal `L` of 0 or more under
  `preserve_literals`), the sums over one JOIN J1 to J3 (an INNER JOIN
  grouped by an `INT` field of the joined side summing a FROM field, a LEFT
  JOIN grouped by the FROM side's unique key, and an `INT` field for J3,
  summing a joined field) and the two-level route T1 and T2 (per order,
  then per customer). The selected definition's SELECT items are a subset
  of its form's with one sum at least, and T1's or T2's `per_order` selects
  exactly its form's items; each is in any order, under any names, in a
  `query` or a `table`.
- A `sum` there is the guarded `SUM` of the S02 cell, a nullable `Int`
  (`my_signed_int`): `CASE WHEN SUM(x) > 9223372036854775807 THEN
  CAST(9223372036854775807 AS SIGNED) + CAST(1 AS SIGNED) WHEN SUM(x) <
  -9223372036854775808 THEN CAST(-9223372036854775808 AS SIGNED) - CAST(1 AS
  SIGNED) ELSE CAST(SUM(x) AS SIGNED) END`. A conditional sum is
  `COALESCE(` that guard over `CASE WHEN TEST THEN x END`, `, 0)`, a non-null
  `Int`, 0 when no row's test is True. In range each is the exact sum;
  outside it the `BIGINT` arithmetic of its branch raises error 1690
  (SQLSTATE 22003), never a clamped value. Each R13 requirement carries the
  evidence `target_checked_signed64_narrowing`.
- PostgreSQL SQL and every other public PostgreSQL output are unchanged.
  Compiled bundles and live templates replay the same SQL. Emission reduces
  the statement as written over its bound contract to the form, and plain
  verification re-derives emission's refusals; compiled replay reduces its
  records to the same form law. A relation alias, an imported source, a
  read qualified by its source's name and parentheses leave the form's
  records apart from source positions and the source digest, so only
  emission and plain verification refuse them.
- R2 `save_recoverable` and `recover` refuse a query of these forms with
  PIE-R1004 (`detail` `PUBLIC_R2_UNQUALIFIED_FORM`) before any workspace
  access or connection, since no native qualification has run its refined
  statement (see the [R2 boundary](../execution.md#known-limitations)).
- The raw MySQL 8.4.12 primitives behind these forms, each form's guarded
  statement over its own seeded tables, matched the signed 64-bit `Int`
  outcome beside PostgreSQL 18.6. The candidate emission experiment then
  ran the emitted SQL of the nine forms on both databases and passed on
  2026-11-14 in its second freeze: run
  `20261114T004403Z-5079c228d8f801082cb39673` judged every form
  `EMITTED_FORM_MATCHED`, both its safe and its overflow half included,
  with no receipt problem, the conditional, JOIN and two-level families
  matched, and the verdict was `MATCHED`. The run bound this change as
  stacked on S01's (tree `69d42812`). D77.50 carries it to the commit that
  integrates this change: the experiment's projects and emitted SQL are
  byte-identical there (`sql.json` sha256, first 16 digits,
  `76be71ac71ae8a02`), and its compile record is identical apart from the
  harness's install identity (the sha256 of the record as sorted-key JSON
  without its `identity` field, first 16 digits, the same on both sides:
  `9539a21293f93a07`).
- Every other MySQL project `sum(Int)` keeps the refusal it has without this
  note, object for object (PIE-B1004 `sum_int_aggregate_range_proof_missing`
  where that is its blocker). Among them are a test other than `F`,
  `not F`, `F is None` and `I > L`, a compound test, a negative literal,
  C3 under `bind_safe_literals`, an `INT` argument, a conditional sum beside
  `count()` or a direct sum, WHERE, ORDER BY, HAVING, LIMIT, DISTINCT, a
  header parameter, a relation alias, an imported source, a read qualified
  by its source's name in C1 to C4, parentheses, a JOIN of another kind,
  key, carrier or ON order, two sums over a JOIN, a JOIN or two-level form
  over a source with any field beyond the language page's two tables (the
  JOIN carries every field), an upstream query that is not T1's or T2's
  own, a third level, and the [style page](../style.md)'s two-level example,
  whose `amount` is non-null.

Changed diagnostics: a MySQL statement whose only blockers in `0.1.11` were
PIE-B1004 `sum_int_aggregate_range_proof_missing` at sums of these forms
is now VERIFIED with those blockers gone. A statement still refused
reports exactly the blockers it has without this note, object for object,
such a sum's own included: a form beside `extra = sum(amount) + 1` keeps
the one PIE-B1003 `aggregate_composition_not_admitted_on_target` that
`0.1.11` reports.
