# Phase73 route — 17 slices

Phase73 owns the Phase 73 row of the [roadmap](../../roadmap.md#future-roadmap-v6):
an explicit two-level aggregation route instead of automatic fan-out repair,
conditional aggregates, list aggregates, per-group detail lists, nested
GROUP BY and DISTINCT keys, small scalar features, and the owner's additions
of 2026-11-05 (project aggregate windows and aggregate parity, `median` and
`quantile`, `compile_query` contract trimming). Its Gate 0 binds `main` at
the `0.1.9` release commit `bca733bb` (tag `v0.1.9`), whose natural
exact-head CI `42090026718` attempt 1 accepted all 19 jobs. Its Gate 1 is
D73.01–D73.19 in the [decision record](../../decisions.md#phase73--owner-decisions-2026-11-05).
Phase73 ships in `0.1.10` together with Phase74 and Phase75, after Phase75
closes, with separate approval; its batches publish to `main` with no tag or
PyPI upload in between (D73.15).

This route is published by an unnumbered documentation-only commit, the first
Phase73 commit after the tag. Each slice binds its exact inputs, write set,
checks and acceptance when it is integrated; this table fixes coverage,
dependencies and batches only.

## Lines

| Line | Delivers | Not included |
| --- | --- | --- |
| T-A | The two-level route documented and witnessed, with a PIE-S2381 hint naming it; conditional count and sum of a group with the generator spelling | automatic fan-out repair, reaggregation, an aggregate-state contract |
| T-S | Single-file typed constants with `--set`; project parameter types `Decimal`, `Date`, `Timestamp`, `UUID`; `max(a, b)`/`min(a, b)`; `lpad`; `add_months`; window expressions; `now()` | grouping extensions (ROLLUP, CUBE, GROUPING SETS) |
| T-K | Nested values as GROUP BY and DISTINCT keys | nested `==`, ORDER BY and set-operation dedup |
| T-L | Per-parent `len`, `sum` and `any` over a collected field | list `avg`/`min`/`max`, nested generators |
| T-G | Per-group detail lists through the existing route with `same_value` | capture on a nested key, group capture without GROUP BY |

T-L, T-G and T-K need `schema_version = 2` projects and stay refused on MySQL
(Phase77). A new single-file form opens on MySQL only after a two-database
differential; a form that fails it stays refused on MySQL and moves to the
Phase74 MySQL catch-up.

## Slices

| Batch | Slice | Content | Depends on |
| --- | --- | --- | --- |
| B1 | S01 | Two-level route witnesses, PIE-S2381 hint, LIMIT 1 capture tie documented | route publication |
| B1 | S02 | Generator grammar, conditional count and sum of a group, `count(Bool)` warning | route publication |
| B1 | S03 | Nested GROUP BY and DISTINCT keys | route publication, `same_value` |
| B1 | S04 | `max(a, b)`, `min(a, b)` | route publication |
| B1 | S05 | `lpad`, `add_months` | S04 |
| — | midpoint | exit criteria below | B1 head CI |
| B2 | S06 | `len`, `sum`, `any` over a collected field | S02 |
| B2 | S07 | Per-group detail route: docs, tests, PIE-S2803 hint, `Float` key witness | S03, S06 |
| B2 | S08 | Single-file constants and `--set` | S02 (grammar order) |
| B2 | S09 | Project parameter types | route publication |
| B2 | S14 | Project aggregate windows | route publication |
| B2 | S15 | `compile_query` validates the whole contract, then keeps only the sources the query reads | route publication |
| B3 | S10 | Window expressions | route publication |
| B3 | S11 | `now()` | S05 (catalog order) |
| B3 | S16 | Project aggregate type and expression-argument parity with single files | S14 (shared project emission owners) |
| B3 | S17 | `median(x)`, `quantile(x, q)` | route publication |
| B4 | S12 | Closeout code: demo page, acquisition consolidation, version bump | B3 |
| B4 | S13 | Audit only: completion audit, Phase74 handoff, lessons | S12 |

Lean Gate v2 batch rules apply: one commit per slice; one authoritative
validation, one fast-forward push and natural exact-head CI per batch; a
failed head is kept and repaired by a child. The root integrates the lanes and
lands each slice's canonical forms in [style](../../style.md) with its batch.
The single compiled `VERSIONS` change of the phase rides on the first slice,
in commit order, that changes a compiled record (D73.16).

**Midpoint (after the B1 head CI).** Nested-key witnesses exist at three
layers on PostgreSQL; the generator grammar is on `main`; any compiled
`VERSIONS` change has landed once; the measured rate projects within the caps
including the reserve; CI health is read. B2 and later batches seal only
after the midpoint passes.

**Closure.** Phase73 closes when T-K and T-G are delivered, every acceptance
row has its emission, compiled and live witnesses where they apply, and the
S13 commit is on `main` with green natural exact-head CI.

## Budget

Cumulative repair caps (stop and ask at any cap): C180/F600/D2400/S11 for
S01–S13 (D73.18), plus the owner-approved S14 addition C15/F40/D260 and the
lane caps of S15 (C8/F20/D80), S16 (C12/F35/D200) and S17 (C10/F25/D120):
C225/F720/D3060/S11 in all.
