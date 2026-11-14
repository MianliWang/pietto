### Float NOT EXISTS in MySQL projects

- `emit-sql --project --dialect mysql` now emits a `Float` `==` of two row
  reads inside `not any(...)` in the forms the Phase77 R02 candidate
  emission experiment covers on MySQL 8.4.12 and nothing else: the whole
  WHERE of a query over one source `o` is `not any(z.v == o.v for z in i)`,
  or `not any(z.v == o.v and z.k == o.k for z in i)`, where `v` is a
  nullable `Float` field of `o` and of a source `i` over another table and
  `k` a NOT NULL binary-collation `Text` key of width 64 or 1000 on each
  side, after the `Float` `==`; each `==` may have its operands in either
  order. The query has no other expression, clause, JOIN or header
  parameter, reads no other query, declares no named window and no `let`
  except one relation alias of `i` that the `any(...)` reads
  (`let z = i` with `for z in z`), calls no `def`, and selects only `o`'s
  non-null `Int` (BIGINT) and nullable `Float` fields. `o` has, selected or
  not (the WHERE's CTE writes them all), exactly a non-null `Int`
  (BIGINT), a nullable `Float` and NOT NULL binary `Text` fields of width 64
  and 1000, in any order; `i`'s other fields never reach the SQL. The
  statement is the PostgreSQL one in MySQL spelling, one
  `NOT EXISTS (SELECT 1 FROM ...)`, and compiled replay and the live
  template carry the same SQL.
- The form keeps the [Float values](../language.md#float-values) contract:
  an outer row is kept exactly when no inner row makes the condition true,
  once, `-0.0 == 0.0`, a NULL `v` keeps its row, and stored bits are kept.
  The opening rests on the 2026-11-11 Phase77 `s06-float-b10` matrix, where
  `anti_not_exists` matched 90 of 90 cells with the wide-key semijoin
  materialization witnessed in EXPLAIN, and on the R02 candidate emission
  experiment over Pietto's own statements. The lost Phase72 B10 record was
  not reconstructed or replayed. PostgreSQL output is unchanged.
- R2 `save_recoverable` and `recover` refine a query of these forms as any
  other query: the refined statement reads the outer and the tested source
  each through its own refined input and compares the `Float` and the keys
  there. No native qualification, the candidate emission experiment
  included, has run those refined statements; in the lead's survey on
  MySQL 8.4.12 on 2026-11-14, over the experiment's fixture and four
  variants of it, each such attempt completed with the rows `execute()`
  returns (see the [R2 boundary](../execution.md#known-limitations)).
- The candidate emission experiment passed on 2026-11-14 in its eighth
  freeze, one run per database, each judged `QUALIFIED` with no reason
  against: PostgreSQL 18.6
  `r02-pg-20261114T015508Z-60cf4c2ca867beefd88ddd59` and MySQL 8.4.12
  `r02-my-20261114T015508Z-0ff6ea11ac361c2ba8fe8910`. The four forms
  matched, the PostgreSQL reference matched, and the pair judgment
  accepted the three templates (the bare `Float` `==` and the 64- and
  1000-character keys) for opening. The seventh freeze's run is void and
  carries nothing: its harness wrote each record in sorted key order,
  which its judge read as the execution order, so no run of it could
  qualify. The runs bound this change as first committed on the head of
  the first `0.1.12` batch (tree `299b8225`). D77.50 carries them to the
  commit that integrates this change: the experiment's projects, emitted
  SQL and compile-only observations are byte-identical there, and both
  halves' compile records are identical apart from the harness's install
  identity (sha256, first 16 digits, the same on both sides: `sql.json`
  `2559a63fe3378b44`, `compile-check.json` `bfe31e92338b5416`, compile
  records as sorted-key JSON without their `identity` field PostgreSQL
  `47273b5ec14413f7` and MySQL `ea93a59401231227`).
- Kept refused on MySQL with PIE-B1003 `comparison_type_pair_not_admitted`:
  every other `Float` comparison of two row reads inside `any(...)` or
  `not any(...)`, such as `any(...)` itself, `!=`, `not (!=)` or
  `same_value` inside it, a key before the `Float` `==` or a second key, a
  key of another width or of two widths, a nullable or `Int` key, a
  non-null `Float` operand, another test inside or beside the
  `not any(...)`, `not any(...)` as a SELECT value, beside a JOIN or over an
  upstream query, `i` over `o`'s table, an outer source with any other
  field, and a query that declares another `let` (also one it never reads)
  or a named window or calls a `def`. A statement of the forms above that
  emission refuses for another reason, such as an output label past 256
  characters, reports the earlier blockers, this PIE-B1003 included.

Changed diagnostics (programs refused before; no accepted program changes;
MySQL projects, no message text changed):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | `where not any(z.v == o.v for z in i)`, alone or with `and z.k == o.k` of a NOT NULL binary `Text` key of width 64 or 1000, over an outer source of exactly an `Int`, a nullable `Float` and those two keys | `comparison_type_pair_not_admitted` at the `where` | none: the statement emits |
