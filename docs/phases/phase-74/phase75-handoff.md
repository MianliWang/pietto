# Phase74 handoff — Phase75 readiness

This handoff takes effect when Phase74 closes under its
[completion audit](completion-audit.md). The owner let the Phase75 lines
start on 2026-11-05, beside Phase73 and Phase74; their work replays onto the
Phase74 heads, and Phase75 publishes under its own route after Phase74
(D74.13). Check live `main`, its tree and its CI before acting on any hash
here.

## What Phase75 receives

- `main` with all of Phase74: `def` and `relationship` items in the import
  and export lists of `schema_version = 2` projects, with PIE-S2103 hints
  that name the export or import to write; relationship parameters that take
  the rows of a table or query, matched by field name and type; the MySQL
  catch-up (project UUID ordering and UUID `max`/`min`, project aggregates
  of `Text`, `Bool`, `Float` and `Decimal` values and over row expressions,
  `order by` a finite `Float`, single-file `max`/`min` of two `Bool` values,
  project `min`/`max` of a `Timestamp` or `Date`); the backward asof JOIN on MySQL; `variance`,
  `pvariance` and `pstdev`; `count_distinct(a, b, ...)`; `all` and `any`
  over a group; `first` and `last` on PostgreSQL; and a two-module part of
  the [worked example](../../worked-example.md). The
  [release notes](../../release-notes.md) list every change, refusal and
  compatibility row under "Unreleased changes following 0.1.9".
- No release of its own: Phase73, Phase74 and Phase75 ship together as
  `0.1.10` after Phase75 closes, with separate approval (D74.14). Batches
  publish to `main` with natural CI and no tag in between.
- Compiled `VERSIONS` is `(7, 1, 7, 1)`, unchanged in Phase74: the new
  aggregate values ride it because no release carries it (D74.15). A
  Phase75 compiled record change rides it on the same terms until `0.1.10`
  is cut; after that it needs its own change of that value.
- Inputs: the Phase74 section of the
  [engineering lessons](../../references/engineering-lessons.md#phase74),
  the latest qualified CI health and the Phase 75 row of the
  [roadmap](../../roadmap.md#future-roadmap-v6).
- The second whole-tree test pass is due by the Phase75 close (the leftovers
  row of the [Phase74 handoff](../phase-73/phase74-handoff.md#open-follow-ups)).

## MySQL items after Phase74

These rows of the [Phase74 handoff](../phase-73/phase74-handoff.md#mysql-items-for-the-phase74-mysql-catch-up)
and of the Phase74 aggregates were not opened; each keeps its refusal and is
listed in the release notes. They wait for the MySQL catch-up of
Phase76/77; no Phase74 slice took them, and a new slice would have exceeded
the scope cap S12.

| Item | On `main` | What opening needs |
| --- | --- | --- |
| Single-file conditional sum | PIE-B1000 (D73.01) | a two-database run; it rests on `sum(Int)` (Phase77) |
| Project conditional count and sum | PIE-B1003 `conditional_count_not_admitted_on_target`, PIE-B1004 `sum_int_aggregate_range_proof_missing` | a project differential; the sum waits for project `sum(Int)` |
| Single-file constants and `--set` | PIE-B1000 per relation that reads a constant | its database run passed (18 of 18 flags): route MySQL emission back to the plain emitter |
| `now()` | PIE-B1000 (single file), PIE-B1003 (project) | its database run passed (33 checks): emit `UTC_TIMESTAMP(6)` |
| Project `lpad` and `add_months` | PIE-B1003 `scalar_call_signature_not_admitted`, as `concat` | a project differential |
| Computed `Text` window key in a single file | PIE-B1000 | a run that covers a `Text` key and the connection collation |
| Typed project parameters | PIE-B1003 `query_parameter_type_not_admitted_on_target` (D73.14) | a per-type differential |
| Project aggregate windows | PIE-B1003 `window_aggregate_approved_non_support_on_mysql` | a database run; project `sum(Int)` also keeps PIE-B1004 |
| Checked `Int` arithmetic not proved to fit signed 64 bits | PIE-B1002 `arithmetic_outside_physical_range` (and the unary and `abs` details) | MySQL raised error 1690 for a product of -2^63, which fits signed 64 bits; a guard or a narrower bound |
| Project `count_distinct` of a `Float` (a single file emits it); `Float` DISTINCT, GROUP BY, set operations and `==` of two row reads | PIE-B1003 | a decision on the `Float` value contract for a merged zero (USER_DECISION_REQUIRED), then a differential |
| Project `sum`, `avg` and `stddev` of a `Float` (a single file emits them; the rest of the Phase73 "Project aggregate parity forms" row) | PIE-B1004 `float_aggregate_finite_result_proof_missing` | a database run, as the Phase73 row says, or the finite-result proof its detail names |
| `string_agg` | PIE-B1000 (single file), PIE-B1003 (project) | a premise design against silent `GROUP_CONCAT` truncation (a separate decision) |
| `variance`, `pvariance`, `pstdev` of an `Int`, and in projects | single-file `Int` PIE-B1000; project PIE-B1003 `variance_int_not_admitted_on_target` (`pvariance_`, `pstdev_` alike) for an `Int`, PIE-B1004 `float_aggregate_finite_result_proof_missing` for a `Float` | a run over the `Int` domain and a project differential |
| `count_distinct(a, b, ...)` in projects | PIE-B1003 `count_distinct_tuple_not_admitted_on_target` | the native `COUNT(DISTINCT a, b)` in the project emitter and a project differential |
| `all` and `any` over a group in projects | PIE-B1003 `group_test_not_admitted_on_target` | a project differential |
| `first` and `last` | refused in the first version (D74.11): PIE-B1000 (single file), PIE-B1003 `first_last_not_admitted_on_target` (project) | an ordered-value form for MySQL 8.4 and a differential |

Not catch-up items: `median` and `quantile` stay refused on MySQL, which has
no interpolated percentile; project `sum(Int)` and `stddev` of an `Int`,
nested values, list operations and the detail route wait for Phase77
(D71.05).

## Deferred decision points

The tables of the [Phase74 handoff](../phase-73/phase74-handoff.md#deferred-decision-points)
and the Phase73 handoff stay as written; Phase74 changed none of their rows.
Phase74 adds these:

| Item | Owner | Latest point |
| --- | --- | --- |
| Def and relationship items in a PACKAGE_ROOT package module (PIE-S2707, D74.07) | package and project owner | a named package case; Phase82 freeze input |
| Wildcard imports, `constraint` and `derive` exports, qualified calls such as `a.pos(x)` (D74.12) | module owner | a Gate 1 that admits one; each stays refused with a negative test |
| Measure and metric definitions (D74.12) | Pietto lead, then the owner | unscheduled |
| User-written table functions, the function/plugin SPI, PostgreSQL extension functions (D74.12) | Phase76 Gate 1 | Phase76 Gate 1 takes or reroutes them |
| A new built-in table function (D74.12) | the first Gate 1 that names a case | Phase82 freeze input |
| Cube/dbt export; the scalar-function effect catalog (D70.06) | roadmap | Phase84; Phase88 |
| Window forms of `variance`, `pvariance`, `pstdev`, `count_distinct(a, b, ...)`, `all`, `any`, `first` and `last`; `all`, `any`, `first` and `last` in a grouped query with a JOIN (route 74-G) | aggregation semantic owner | the first Gate 1 that admits one |
| Positional matching and inferred paths for relationship rows; field-name matching for source rows (route 74-B) | relationship semantic owner | the first Gate 1 that admits one |

## Open follow-ups

The open follow-ups of the [Phase74 handoff](../phase-73/phase74-handoff.md#open-follow-ups)
stay open except where this table says otherwise.

| Follow-up | State and owner |
| --- | --- |
| `max(a, b)` of two `Bool` values (a Phase74 handoff row said single-file PostgreSQL only) | single-file MySQL opened in Phase74 (S05); project `Bool` operands unchanged |
| A relation with aggregates and no JOIN input that reads a `let` name or a query parameter still reports some aggregate, grouping and ORDER BY errors as the bare PIE-S2333 (as in `0.1.9`) and drops them beside a generator error; the verified residuals are `sum(o.nope for o in group if ...)` losing PIE-S2102, no GROUP BY with `limit -1` losing PIE-S2307, and `count(nope)` losing PIE-S2102 | not taken by Phase74; aggregation semantic owner: check such relations over their `let` names and parameters, then order by position |
| The project JSON v2 aggregate `function` values: `filtered_count` and `filtered_sum` (Phase73) and the Phase74 values `count_distinct_tuple`, `group_any` and `group_all`, internal names that differ from the written call and that compiled bundles carry too | USER_DECISION_REQUIRED before `0.1.10`: confirm or choose public names |
| A query whose WHERE calls a def that inlines to a conditional (`length_band(minutes) == 2`) cannot be read through a JOIN by another project query: the JOIN query is BLOCKED (PIE-B1003 `operator_not_implemented_in_slice6`, `scalar_projection_requires_later_slice`, `join_shape_not_admitted_in_slice7`) on PostgreSQL; the same query read with `from` alone, or the def in a query no JOIN reads, emits. Found while writing the two-module example | project JOIN emission owner: a conditional in a joined query's predicate |
| In a project, `any(R(x, c) for c in q)` over a query `q` with a JOIN keeps the plain PIE-S2604, because the output row of `q` is not known where the call is bound (D74.08); the written `on` works | relationship and completion owners: completed outputs at bind time |
| A `table` with a set-operation or VALUES body is not a table or query row for a relationship parameter (`Unavailable row argument ...`) | relationship semantic owner; extend with a named case |
| Wording questions the lanes left: the PIE-S2604 prefix `Unavailable row argument` for a present but mismatched row; PIE-S2398 `a def cannot shadow one` and `a relationship cannot shadow one` for an import binding (an import cannot shadow one); the qualified-call hint ends `then call pos(...)`; a name declared as a relationship and a def elsewhere gets only the relationship hint; a colliding local def still checks its own calls after PIE-S2706; in a project with def items, a module diagnostic on the stop path may name the def (`Unknown export binding: table pos; pos is a def`) | lead decisions; each changes public text only |
| `Decimal` precision and scale are not compared when a column binds a relationship field (D74.08) | relationship semantic owner: a refusal of a `Decimal(p, s)` field without a proven equal column if asked |
| `pietto fmt` keeps the gaps between tokens of a line as written, and a comment paragraph at the head of a file attaches to the first declaration when a blank line follows it | formatter owner: the Phase75 formatter follow-ups |
| On MySQL, forms that read a reopened `Timestamp` or `Date` `min` or `max` (a `let` of it, `order by` it, a window `order by` it, `select distinct` of it) are VERIFIED without a statement of their own in the differential; each composed form was opened by its own run over the same carriers | lead: a delta differential if wanted |
| Aggregate wording and design questions the lanes left: the MySQL project `Float` variance keeps the generic PIE-B1004 suggestion; the single-file PIE-B1000 refusals and the shared window PIE-S2103 carry their hints in the message only, with no JSON `suggestion`; the check text `ANY/ALL predicate requires a known Bool expression.` is unreachable; a project `first` or `last` over JOIN rows is refused before its key refusals; the role name `aggregate_order_reversed_direction`; a project `let` name as an order key shares PIE-S2333 with `string_agg`; `first(x, order by id, id)` is accepted | lead decisions; each changes public text or one rule |
| PostgreSQL live witnesses of `-0.0`, UUID, `Timestamp` and `Date` members of `count_distinct(a, b, ...)` | aggregation emission owner, with the next database run |
| The release notes' "Kept refused on MySQL" bullet lists no refusal of the new aggregates; each aggregate subsection lists its own | release-notes owner: one list in the `0.1.10` release preparation if wanted |
| Comments in `src/pietto/sql/mysql_expressions.py` name the database packages `ba` and `cd` | mechanical, at the next change of that module |

## Acquisition debt

- The `_check` helper is a 25-line copy in `tests/test_project_def_imports.py`
  and `tests/test_project_relationship_imports.py`, as about a dozen project
  owners keep their own; it joins the Phase72 prelude debt list for the
  second whole-tree pass (Phase75 close at the latest).
- The Phase72 F1, F2 and F4 product and test-side debts stand as recorded;
  the ten-slowest profile of the batch-1 head's health found no new one: the
  same ten nodes, the same verifier runs per build, and no Phase74 test
  acquisition in their top frames.

## Process inputs

- Lanes run at `nice -n 19` with `pytest -n 2` at most, one real-database
  run at a time and one container per lock hold; the lead raised the lane
  cap to 20 on 2026-11-06. A lane delivers a diff identified by its sha256
  and never commits; the lead integrates from each lane worktree in
  dependency order and runs one Gate 2 per batch head on the integration
  host, with 12 pytest workers (owner, 2026-11-06).
- The owner pre-approved each Phase73–75 batch push after its Gate 2
  passes, fast-forward only and with no tag or release (2026-11-05). The
  `0.1.10` release is asked separately.
- The lead placed the diagnostic-hint lane that rewrites the PIE-P1000,
  PIE-S2102, PIE-S2104, PIE-S2310, PIE-S2329 and PIE-B1004 texts in the
  Phase75 polish; it merges with the Phase74 PIE-P1000 hint change.
