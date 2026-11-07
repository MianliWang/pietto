# Phase73 handoff — Phase74 readiness

This handoff takes effect when Phase73 closes under its
[completion audit](completion-audit.md). The owner let the Phase74 lines
start on 2026-11-05, beside Phase73; their work replays onto the Phase73
heads. Check live `main`, its tree and its CI before acting on any hash here.

## What Phase74 receives

- `main` with all of Phase73: the two-level route and its PIE-S2381 hint,
  conditional count and sum in single files and `schema_version = 2`
  projects, nested GROUP BY and DISTINCT keys, `len`, `sum` and `any` over a
  collected list in PostgreSQL projects, the per-group detail route, single-file
  constants and `--set`, typed project parameters, `max(a, b)` and
  `min(a, b)`, `lpad`, `add_months`, window keys that name a computed `let`,
  `now()`, project aggregate windows, project aggregate parity on
  PostgreSQL, `median`, `quantile`, and `compile_query` with the whole
  contract, with the [worked example](../../worked-example.md) and one
  shared node walk per parsed script. The [release notes](../../release-notes.md) list every change,
  refusal and compatibility row under "Unreleased changes following 0.1.9".
- No release of its own: Phase73, Phase74 and Phase75 ship together as
  `0.1.10` after Phase75 closes, with separate approval (D73.15). Batches
  publish to `main` with natural CI and no tag in between.
- Compiled `VERSIONS` is `(7, 1, 7, 1)`; Phase73 changed it once (D73.16).
  A Phase74 compiled record change needs its own change of that value.
- Inputs: the Phase73 section of the
  [engineering lessons](../../references/engineering-lessons.md#phase73),
  the latest qualified CI health and the Phase 74 row of the
  [roadmap](../../roadmap.md#future-roadmap-v6).

## MySQL items for the Phase74 MySQL catch-up

| Item | On `main` | What opening needs |
| --- | --- | --- |
| Single-file conditional sum | PIE-B1000 (D73.01) | a two-database run |
| Project conditional count and sum | PIE-B1003 `conditional_count_not_admitted_on_target`, PIE-B1004 `sum_int_aggregate_range_proof_missing` | a project differential; the single-file count is open since batch 3 |
| Single-file constants and `--set` | PIE-B1000 per relation that reads a constant | its two-database run passed; route MySQL emission back to the plain emitter |
| `now()` | PIE-B1000 (single file), PIE-B1003 (project) | its database run passed; emit `UTC_TIMESTAMP(6)` |
| `max(a, b)` and `min(a, b)` of two `Bool` values | refused | MySQL returns an integer: a rule for the wire type of a computed `Bool` |
| Project `max(a, b)` and `min(a, b)` of `Date` or `UUID` | PIE-B1003 | a review of the MySQL result metadata |
| Project `lpad` and `add_months` | refused, as `concat` is | a project differential |
| Computed `Text` window key in a single file | PIE-B1000 | a run that covers a `Text` key and the connection collation |
| Typed project parameters | PIE-B1003 (D73.14) | a per-type differential |
| Project aggregate windows | PIE-B1003 | a database run; project `sum(Int)` also keeps PIE-B1004 |
| Project aggregate parity forms | their existing PIE-B1003 and PIE-B1004 details | a database run |

Not catch-up items: `median` and `quantile` stay refused on MySQL, which has
no interpolated percentile; nested keys, list operations and the detail
route wait for Phase77 (D71.05), and so does the project two-level route
behind project `sum(Int)`. The MySQL rows of the
[Phase72 completion audit](https://github.com/MianliWang/pietto/blob/8e7c43f1852b2c26318b3217268a1f7416f44965/docs/phases/phase-72/completion-audit.md#3-mysql) still
apply where Phase74 has not taken them.

## Deferred decision points

The table of the [Phase73 handoff](https://github.com/MianliWang/pietto/blob/8e7c43f1852b2c26318b3217268a1f7416f44965/docs/phases/phase-72/phase73-handoff.md#deferred-decision-points-carried-from-the-phase72-handoff)
stays as written; Phase73 changed none of its rows. Phase73 adds these:

| Item | Owner | Latest point |
| --- | --- | --- |
| Automatic fan-out repair or reaggregation | joined-aggregation semantic owner | the first Gate 1 that admits such a form; Phase82 freeze input |
| List `avg`, `min`, `max`; nested generators | aggregation semantic owner | the first Gate 1 that admits one |
| Grouping extensions (ROLLUP, CUBE, GROUPING SETS) | aggregation semantic owner | a named use case; Phase82 freeze input |
| A public aggregate state | aggregation semantic owner | a consumer; Phase82 freeze input |
| `Decimal` list sum and conditional sum (D73.04), `Decimal` constants (D73.07) | aggregation and constant owners | a compatible extension when asked |
| `Timestamp` `add_months` | builtin catalog owner | a named case and a time-of-day rule |
| An at-most-one grain fact for `LIMIT 1` lets (D73.12) | grain owner | a consumer that reads it |
| Nested `==`, ORDER BY and set-operation dedup (D73.06) | nested-value semantic owner | the first Gate 1 that admits one |
| Nullability v2 (D73.13) | Pietto lead, then the owner | after the lead's read-only review; before the Phase82 freeze |
| Text compared with `Date`, `Timestamp` or `UUID` (D73.08) | type owner | a Gate 1 that adds the check, with its compatibility rows |
| `len`, `sum` and `any` over a list in a table or query with JOIN inputs (refused with PIE-S2805 and the carry hint: select the list, read it in a later query) | nested-value semantic owner with the JOIN emission owner | when the JOIN emission path admits built-in calls in its WHERE and SELECT |
| A query header parameter, or a computed GROUP BY key, read in a project generator test (PIE-S2355; PIE-S2334 with the let hint) | aggregation semantic owner | when project aggregate arguments read parameters and lets inside an expression |

## Open follow-ups

| Follow-up | State and owner |
| --- | --- |
| Compiled replay and live analysis give different JOIN properties for a JOIN onto a grouped query: the grouped-key grain and the aggregate pair linkages, and for plain LEFT or INNER JOINs already the key and dependency signature (since `0.1.8`). The SQL bytes are equal. The compiled side matches every right-input key, grouped keys included; the live key matches do not reach GROUP BY keys | ARCHITECTURE_DECISION for the lead before any slice relies on either side |
| A window value inside a SELECT expression | needs a grammar owner, a project lowering design and a compiled-record answer; refused as a syntax error |
| Project window aggregates keep the `Int` domain while grouped aggregates gained the single-file types | opening them needs window emission, compiled and live witnesses |
| The PIE-S2388 `count(<Bool>)` warning in `check --project` | a new project warning; lead decision |
| `Decimal` `median` | USER_DECISION_REQUIRED: an exact form needs a design |
| `max(a, b)` of mixed numeric types is refused, as `coalesce` is | USER_DECISION_REQUIRED: a widening rule is compatible later; `Bool` operands are open only in single-file PostgreSQL |
| `max(a, b)` repeats its arguments in SQL, so nesting is bounded by PIE-S2399 | a flat guarded `GREATEST`/`LEAST` is the alternative if the bound is too tight |
| `lpad` width and `add_months` count outside `int4` when not literal; dates after 9999-12-31 (PostgreSQL gives a later date, MySQL `NULL`) | documented limits; a guard is a lead decision |
| The project PIE-S2333 cause does not name the two-level route | about 25 public cause texts; needs authority |
| `--set` also accepts `true` and `false`; a constant may shadow a column of a source without a shape | lead decisions on one obvious way |
| `Decimal(p, s)` as the canonical parameter spelling; a selected `Timestamp` or `UUID` parameter checks and emits but `execute` and `save` refuse it (PIE-R1004 `MEANING_OUTPUT`) | lead decisions; an emission blocker would move the refusal earlier |
| A bare `now` or `current_timestamp` has no hint; no live save, R1 and export cell for a `now()` query | saved rows keep the run's value and no path re-evaluates them; add the cell with the next database campaign |
| Text output prints no suggestion; a duplicate SQL label in the `Float` detail query | the first is a CLI text contract change |
| A compiled bundle may carry a PostgreSQL row-operation argument for every aggregate (a forged `median(id * 2)` loads with consistent SQL) | tighten if compiled input must mirror source exactly |
| The test decoder of public emission documents does not parse the project `lpad` and `add_months` spellings | extend it when a public-document witness needs it |
| Single-file MySQL `SUM(Int)` returns `DECIMAL`; for a `==` column of `select distinct` after a UNION the test decoder expects nullable `true` where the document says unknown | carried from Phase72; review with the MySQL catch-up |
| Asof JOIN in the project contexts its lowering does not cover | carried from Phase72; widen only with a new spike |
| Leftovers of the whole-tree test reorganization | the second whole-tree pass, due by the Phase75 close |
| The project JSON v2 aggregate `function` values `filtered_count` and `filtered_sum` are the single-file IR's internal names, now public with six additive range roles | USER_DECISION_REQUIRED before `0.1.10`: confirm or choose public names |
| A single-file top-level constant in a generator test (`if o.amount > cutoff`) is refused before constant substitution with ``Generator reads cutoff outside its member; write `o.cutoff` ``, a wrong hint | generator and constant owners |
| A relation with aggregates and no JOIN input that reads a `let` name or a query parameter in its SELECT items, GROUP BY, ORDER BY or HAVING reports its generator calls' errors as a single file does, but some of its other aggregate, grouping and ORDER BY errors, such as `sum(nope)`, are still the bare PIE-S2333 (as in 0.1.9), and go unreported beside a generator error. Without a generator test error a project keeps the 0.1.9 order of a relation's errors (an aggregate's PIE-S2314 before an earlier aggregate's PIE-S2102), and a later stage places a plain item's PIE-S2102 | aggregation semantic owner: check such relations over their `let` names and parameters, then order by position |

## Process inputs

- Lanes run at `nice -n 19` with `pytest -n 2` at most, one real-database
  run at a time and one container per lock hold. A lane delivers a diff
  identified by its sha256 and never commits; the lead integrates from each
  lane worktree in dependency order and runs one Gate 2 per batch head on
  the integration host.
- The owner pre-approved each Phase73–75 batch push after its Gate 2 passes,
  fast-forward only and with no tag or release (2026-11-05). Windows CI and
  the `0.1.10` release are asked separately.
