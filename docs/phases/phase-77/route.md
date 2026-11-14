# Phase77 route — LOCAL IMPLEMENTATION AUTHORIZED

The owner selected the complete 27-slice scope in D77.01 on 2026-11-08,
then approved local execution and validation under D77.02. On 2026-11-12
S21–S24 left Phase77 for a separate nested work package (D77.26, D77.32),
and on 2026-11-13 the Wave A slices S08, S10, S11, S14, S16, S17, S18 and
S25 left for a separate Wave A work package (D77.35), which redoes them now,
one slice at a time (D77.36). Substantive numeric
decisions below still precede their affected openings. The
maintenance/editor batch published under D77.04. Each later batch publishes
under D77.06 (Gate 2 and a clean batch audit, fast-forward only), and so does
a batch that changes only documentation or tools (D77.14). Phase77 authorizes
no release: `0.1.11` ships before it completes, and its remaining slices
continue into `0.1.12` (PL.21); local development is not publication.

## Starting point and outcome

Gate 0 is bound to the published head of the maintenance/editor batch
(D77.04): `main` at `ab972f362c433b234a74f542c5d274d22c8cdeae`, tree
`821be1ccf7bb6f3e14b8d00d80f1f30d3cc087fe`, whose
[natural exact-head CI `42831340276`](https://github.com/MianliWang/pietto/actions/runs/42831340276),
push/main attempt 1, passed all 21 jobs. It binds that head's branch, tree,
remote and CI run, the Phase76
[completion audit](../phase-76/completion-audit.md), the dependency inputs,
and the PostgreSQL/MySQL image and session identities. The batch's parent is
Phase76's published `main` at `f8ccd2c44a2d9adf431a496bd9bbae037783176f`,
tree `460e3e135d1dcb0b926928bc2632a889410f258a`, whose exact-head push
workflow `42489408515`, attempt 1, accepted 21 jobs. The Phase76
[handoff](../phase-76/completion-audit.md#phase77-handoff-and-phase82-inputs),
a section of that audit, names the residual MySQL forms, and the
[Gate 1 record](#gate-1-record) binds them to slices. Gate 1 cites the
refusals and gates of the batch tree, which is the tree Gate 0 binds; a record
that a later head contradicts is reopened before its first affected slice.

The outcome is selected existing Pietto forms on MySQL, each with current
PostgreSQL/MySQL differential evidence and the real semantic, emission,
execution, and reader closure. A raw MySQL success does not change Pietto
semantics or open a compiler form. Phase76 PostgreSQL openings and formatter
work are regression inputs, not Phase77 deliverables.

## Selected scope

The route is S01–S07, S09, S12, S13, S15, S19, S20, S26 and S27. D77.01 kept
every slice in this scope; D77.26 and D77.32 moved S21–S24 to a separate
nested work package with its own Gate 1, and D77.35 moved the Wave A slices
to a separate Wave A work package, which redoes them now, one slice at a time
in the narrowest form (D77.36). The groups are:

| Group | Product slices | Boundary |
| --- | --- | --- |
| A — flat MySQL adaptation | S01–S07, S09, S12, S13, S15, S19 and S20 | Opens only selected flat forms. |
| Wave A | S08, S10, S11, S14, S16, S17, S18 and S25 | Moved to the separate Wave A work package (D77.35), which redoes them one slice at a time (D77.36); each form keeps `main`'s refusal until that package opens it. |
| B — nested MySQL results | S21–S24 | Moved to the separate nested work package (D77.32); every MySQL nested shape keeps `main`'s refusal until that package opens a form. |

S26/S27 are phase-wide acquisition/audit work: they run only after the group
A slices are complete or an owner decision records each retained exception.
The slices that left keep their numbers and are not renumbered.

`C560/F1700/D70000/S24` is the approved cumulative ceiling for the Phase77
route (D77.02, D raised by D77.03, D77.05 and D77.18, then every figure
doubled by PL.09; unchanged when S21–S24 and Wave A left, lead), not a target
or a per-group allowance. No handoff or lane resets it. Each lane reports its
checks and repairs to the integrator.

Out of scope: `string_agg`, project FULL JOIN emulation, median/quantile
emulation, MySQL nested results (S21–S24, moved to a separate work package by
D77.32), the Wave A forms (moved to the Wave A work package, D77.35 and D77.36),
arbitrary-depth nesting, new syntax, general optimization, SQL escapes, and
PostgreSQL SQL rewrites. Existing refusals remain until a later decision
admits a specific form.

## Existing semantics and qualification prerequisites

1. The [Float value contract](../../language.md) already makes `-0.0` and
   `0.0` two encodings of one value. Equality, grouping, DISTINCT, sets and
   unique keys share that equivalence; ordering ties them. A merged class may
   return any member's encoding, while transport and UNION ALL preserve bits.
   S06/S07 prove this law and bag multiplicity for each admitted MySQL shape;
   they do not introduce another zero policy or a canonical `+0.0` rewrite.
2. `IMPLEMENTATION_FREEDOM`: prove that MySQL `1690`/`22003` and the emitted
   operations preserve the existing signed-64 checked-`Int` outcome. A changed
   observable value/error contract is `USER_DECISION_REQUIRED`; a failed proof
   retains the refusal. Decimal, unsigned and Float substitutions are excluded.
3. `ARCHITECTURE_DECISION`, escalating if observable behavior changes: a
   `sum(Int)` strategy that preserves signed-64 value, NULL and overflow
   behavior. Exact MySQL `DECIMAL` accumulation is not itself a Pietto `Int`.
4. The selected scope includes `first`/`last`; the same-relation ASOF/FULL
   backlog (S25) left with Wave A (D77.35). Preserve their existing order, tie
   and NULL rules. A proposed cadence exception or changed meaning, rather than
   a target proof, requires a new owner decision.
5. `ARCHITECTURE_DECISION`: before S21–S23, the MySQL nested transport seam:
   occurrence identity, order, empty/missing/NULL, exact leaf decode,
   resource lifetime, and live/compiled/Arrow/saved-reader closure.
   AD77.01 selects the versioned JSON envelope; AD77.02 publishes its carrier
   in project JSON v2 and keeps only the envelope layout private.
   S21–S23 left Phase77 (D77.32), so no Phase77 slice consumes this
   decision; AD77.01 and AD77.02 stand until the nested work package's
   Gate 1 (lead).

D76.02 already distinguishes zero divisors by target: PostgreSQL raises
`22012`, while MySQL `/`, `DIV` and `%` return NULL. S15 preserves this
documented difference and its result nullability; it does not normalize MySQL
errors to PostgreSQL errors. A native MySQL overflow remains a native target
failure, not a new portable `PIE-*` exception promise. No statistical precision
or tolerance is relaxed merely to pass a differential cell.

The separately scoped dependency maintenance (M77.01) is delivered in the
maintenance/editor batch. It adopts the open `pyarrow 26.0.1` proposal and
retargets the `psycopg[binary] 3.3.7` proposal at `3.3.8`, whose
[upstream release notes](https://www.psycopg.org/psycopg3/docs/news.html#psycopg-3-3-8)
revert `3.3.7`'s system SSL-directory change; fresh PostgreSQL TLS, remaining
PostgreSQL and MySQL runs passed with the new pins. Maintenance is not a
Phase77 slice and uses the explicitly approved D77.02 validation envelope.

## Gate 1 record

On 2026-11-10 the lead named these items to the owner only by topic, and the
owner has not answered them. They are the lead's decisions within the
owner-approved Phase77 scope (D77.02), stated as inform, and the
[decision record](../../decisions.md#phase77-continuation--owner-decisions-2026-11-10)
keeps them as D77.08–D77.13; the owner can still object to each before the
slice its row names. A slice that changes a public detail (D77.11) or the
compiled `VERSIONS` (D77.12) does not push before the owner confirms it,
which is D77.16's fail-closed default. Each applies an existing contract or
decision and adds no product law; a change to one goes back to the owner.

1. **Merged zero (S06, S07; D77.08).** The existing
   [Float value contract](../../language.md#float-values) governs, as the first
   prerequisite above states, and Gate 1 adds no zero policy. This settles the
   merged-zero item that the Phase76 handoff and the roadmap's MySQL cadence
   put on this Gate 1. The MySQL shapes observed to split the two zeros beside a
   wide `Text` key, and Float INTERSECT and EXCEPT, where MySQL compares them as
   different values, stay refused. No canonical `+0.0` rewrite is made: a
   class whose members share one sign shows that sign.
2. **P76-PERF-1 to P76-PERF-4** (D77.09) are assigned below. They are
   bounded follow-ups, not authority for a global cache or deleted
   verification, and each is met before the acceptance it affects.
3. **The S14–S20 residual matrix** (D77.10) is bound below.
4. **S08 narrowing** (D77.11, `IMPLEMENTATION_FREEDOM`). A MySQL aggregate
   window keeps the `Int` domain that PostgreSQL's was reviewed with: `count`
   of a `Text`, `Bool`, `Float` or `Decimal` field and `min`/`max` of a
   `Float` or `Decimal` field keep their refusal. PostgreSQL keeps PIE-B1003
   `<function>_argument_outside_reviewed_int_domain`. On MySQL, where every
   aggregate window is PIE-B1003
   `window_aggregate_approved_non_support_on_mysql` today, S08 refuses them
   with that same `<function>_argument_outside_reviewed_int_domain` detail,
   and its release-note fragment lists the changed detail. Opening them on
   MySQL alone would put MySQL ahead of the PostgreSQL forms its differential
   compares with (D74.09). S08 left Phase77 with Wave A (D77.35), which takes
   this item with it.
5. **S23 compiled records** (D77.12). S23 left Phase77 with the nested work
   package (D77.32), which takes this item with it. D77.22's rule still binds
   every Phase77 slice: a proven compiled-record change moves `VERSIONS` once
   to `(9, 1, 9, 1)` in the first slice that changes a record.
   Before S23 left, its default was to admit MySQL only at the
   three compiled verifier gates `LIST_TARGET`, `UNNEST_ROUTE` and
   `COLLECT_TARGET` and to change no compiled record. Only if a record change is
   proven necessary does the first Phase77 slice that changes a compiled
   record move `VERSIONS` once from the Phase76 mark `(8, 1, 8, 1)` to
   `(9, 1, 9, 1)`, which later Phase77 slices ride (D73.16). Keeping
   `(8, 1, 8, 1)` for a changed record would let a bundle compiled on `main`
   during Phase76 reach the changed reader without the typed refusal. Opening
   only the live route, without the compiled readers, needs an owner decision.
6. **S09 UUID** (D77.13, `IMPLEMENTATION_FREEDOM`). How a MySQL UUID header
   parameter reaches the existing `my_uuid_bytes` carrier is the lead's
   choice, provided the public typed value stays canonical lower-case UUID
   text and NULL, errors and the stored bytes are unchanged. (Revised by
   D77.57: MySQL `UUID` header parameters are withdrawn.)

| PERF | Requirement | Evidence |
| --- | --- | --- |
| 1 | Before a Project SQL reader changes (live, compiled, pure, public decoder, saved and source-free readers), operation, root and object identity are shown to be preserved. | The changed reader functions are listed; the complete `tests/test_project_verification_scope.py` passes on the bound tree; value-equal roots that are distinct objects are each verified; a value-equal record swapped in between two calls reports `COMPILED_INPUT_CHANGED`; PostgreSQL bytes are unchanged. |
| 2 | Before public or pure emission changes, input scale is measured. | Operation counts, not wall time; a bounded before/after comparison only for an open question; a superlinear finding is fixed and gains an operation-count test; the PIE-B1007 generated-node limit of 32768 is unchanged. |
| 3 | Before memo behavior is inferred, the exact document and mutation identity are bound. | The memo key and the object it keys are named; the call-scoped `once` identity marker is not a memo; no production memo is added. |
| 4 | The independent repository-fact oracle is retained or replaced. | Its corpus stays every `*.py` under `src/pietto` plus its three named test files, and it is not deleted without an equivalent replacement. The maintenance/editor batch changes neither the oracle nor `tests/_pietto_repo_facts.py`, so it is retained unchanged. |

| Slice | PERF |
| --- | --- |
| S09, S12, S19 | 1 and 2 |
| S01, S02, S04, S05, S13, S15, S20 | 2; 1 when a reader changes |
| S03, S06, S07 | 2 when public or pure emission changes |
| S26 | 4 when a later change touches the oracle; collects 2; 3 when it reads the verifier runs per top-level call of the slowest-node profile |
| S27 | records the final disposition of all four |

The slices that left Phase77 (D77.32, D77.35) have no row.

Only a new production memo or cache, a change to the PIE-B1007 limit or to
PostgreSQL bytes, or deleting the oracle without an equivalent replacement
goes to the owner.

The residual matrix binds the Phase76 MySQL E/N/D residuals. Only S15 is
named by the route text above; the other slots follow the recovered
candidates, and S20, which has none, takes D2 by the lead's binding.
S14, S16, S17 and S18 left Phase77 with Wave A (D77.35): their rows below and
the two-`Date` residual bound to S14 go with that package, and their forms
keep the refusal shown.

| Slice | Forms | Current MySQL project refusal | Before it opens |
| --- | --- | --- | --- |
| S14 | E2: a `def` that inlines to a conditional in a query a JOIN reads; E3: a scalar call in an aggregate argument over JOIN rows | PIE-B1003 `scalar_projection_requires_later_slice` (E2) or `operator_not_implemented_in_slice6` (E3), then `join_shape_not_admitted_in_slice7` | An E2 cell; BETWEEN, `in`, cast, scalar call and LATERAL each get a cell or are listed as retained; the PostgreSQL and MySQL flat parents. |
| S15 | E5: `Int /` (`DIV`), `Int %`, `Float /` | PIE-B1003 `binary_operator_not_admitted` (`Int`), `float_division_not_realized` (`ab972f36` computed it, but `emit-sql --project` stopped with `ValueError: unclassified blocker suggestion` instead of returning it) | Attaches to S01's numeric child; a zero divisor returns NULL and the result is nullable; `INT64_MIN / -1` and `INT64_MIN % -1` are preregistered as unobserved, not as pass criteria, and a PostgreSQL/MySQL difference escalates under the second prerequisite above; Float `/` and `%` cells; a PostgreSQL differential. |
| S16 | E7: a `Text` literal default of `lag` or `lead` | PIE-B1003 `window_default_literal_kind_not_realized_yet` | The default's metadata is `Text` without the binary flag; a field default stays refused, with its control. |
| S17 | E9: `Decimal ± Int` and `Decimal ± Decimal` of different scales | PIE-B1003 `arithmetic_requires_signed_int_operands`, `decimal_scale_mismatch` | Split from the shared Decimal candidate; closed-form precision (D76.02); a PostgreSQL differential. |
| S18 | N1: `Decimal * Int` in either order and a unary sign on a `Decimal` | PIE-B1003 `binary_operator_not_admitted`, `unary_sign_requires_int_operand` | The 65/30 bounds; a result beyond 65 digits is refused at compile time (D76.04). |
| S19 | E10: direct `sum(Decimal)` | PIE-B1004 `decimal_aggregate_range_proof_missing` | Opens with a proof; a retained refusal enters the D77.07 packet. |
| S20 | D2: a scalar call or arithmetic over direct aggregates | PIE-B1003 `aggregate_composition_not_admitted_on_target` | Depends on S01/S02, S15 and S17–S19, not on S10, S14 or S16 (a generator-form leaf is PIE-S2310 on both targets, so S10 is neither a dependency nor a vector); the J16 two-query route is the oracle (D76.05). |

The unassigned residuals are bound as follows; one that its slice does not
open enters the D77.07 packet.

| Residual | Current MySQL project refusal | Bound to |
| --- | --- | --- |
| E4: `Float` `+`, `-`, `*` and sign on a field | PIE-B1003 `float_literal_operands_required`, `unary_sign_requires_int_operand` | S15, after S05 settles MySQL Float overflow |
| `Float % Float` | PIE-B1003 `float_remainder_exact_binary64_not_realized` (`ab972f36` computed it, but `emit-sql --project` stopped with `ValueError: unclassified blocker suggestion` instead of returning it) | S15 |
| E6: `Float` window keys and `percent_rank`/`cume_dist` result keys | PIE-B1002 `window_partition_comparison_domain_unsupported`, `window_order_comparison_domain_unsupported`; PIE-B1003 `group_key_type_outside_reviewed_comparison_domain` | S06/S07 |
| `max(a, b)`, `min(a, b)` of two `Date` values | PIE-B1003 `conditional_realization_not_admitted` | S14; the delivered PostgreSQL form is not reclassified as unfinished |

The lead rules (inform; stated to the owner on 2026-11-10) that repairing the
crash on S15's `Float /` and on the `Float %` bound to S15 is Phase77 work:
the Phase77 batch that publishes this matrix carries the repair under D77.06
and counts it on Phase77's ledger (D77.05), and an owner objection changes
later batches only. The repair returns PIE-B1003 BLOCKED documents for MySQL
project `Float /` and `Float %`, for a PostgreSQL one with a `None` operand,
and for a project `/` or `%` over a `percent_rank` or `cume_dist` result read
from another relation on either target, all of which raised the same
`ValueError` on `ab972f36`. It also gives a suggestion to
eleven more details that project emission can state but that no ordinary
source reaches today. It opens no form, and S15 keeps both MySQL forms.

E1, E8 and D1 have no S14–S20 work: the MySQL CROSS JOIN of E1 is open and
FULL JOIN stays approved non-support, E8's exact-decimal-literal premise is
absent, and D1 is open on MySQL projects. The E6 `Float` FULL JOIN key and
the `Float` order key of `string_agg` are out of scope with project FULL JOIN
emulation and `string_agg`.

## Proposed ordered work

| Slice(s) | Proposed result | Required acceptance before it opens |
| --- | --- | --- |
| S01–S03 | Checked `Int`, `sum(Int)`, conditional/JOIN/two-level sums | Signed-64 decision; literal and parameter boundary probes; independent result reader; the re-run numeric R4 PostgreSQL reference (D77.15). |
| S04–S05 | `Int` statistics and finite Float aggregates | Per-operation type/NULL/extreme oracle; their material is re-authored (D77.15). |
| S06–S07 | Float row equality, `same_value`, grouping, DISTINCT, sets and `count_distinct` | The existing Float contract (Gate 1 item 1, D77.08; no new zero policy) and bag/multiplicity controls. |
| S09, S12 | Typed parameters, selected text/date/`now` forms | Per-form four-layer capability matrix and target qualification; S09 follows D77.13 (revised by D77.57: MySQL `UUID` header parameters withdrawn) with its material re-authored (D77.15). S12's PostgreSQL half waits for the `0.1.12` slice in which `now()` outputs execute (D77.42), and MySQL `now()` opens only when the Pietto `mysql_rows` reader witness of S12's MySQL preregistration passes (D77.44). |
| S13 | Ordered `first`/`last` | Selected order/tie/NULL contract and refusal controls. |
| S15, S19, S20 | Phase76 MySQL E/N/D residuals | The Gate 1 residual matrix (D77.10) on the Gate 0 head; do not reimplement completed PostgreSQL forms. |
| S21–S24 | Moved to the separate nested work package (D77.32) | Not Phase77 work; that package's Gate 1 sets its matrix and order. |
| S08, S10, S11, S14, S16–S18, S25 | Moved to the separate Wave A work package (D77.35) | Not Phase77 work; that package redoes them one slice at a time, S25 and S16 first (D77.36). |
| S26–S27 | Acquisition/capability/lag/package closure; audit/handoff | All selected product slices plus every retained-debt/deferral disposition. |

Every selected target cell records exact source/configuration/SQL/parameters,
catalog/physical metadata/raw result and an independent oracle. Each PostgreSQL or
MySQL campaign owns at most one container per engine under one of that
engine's three slot locks (D77.02, PL.14), with fixed local images,
`--pull=never --network none`, owned cleanup and a two-hour ceiling. A failing cell keeps its
deterministic refusal; no target-specific fallback is invented.

## Initiation-gate checklist

| Fields | Proposed answer or Gate 1 blocker |
| --- | --- |
| 1–2: authority and outcome | Gate 0 is bound to `ab972f36` with natural CI `42831340276`; each later batch rebinds exact live evidence; selected MySQL parity only, never blanket parity. |
| 3–6: semantics, identity, states, proof | Existing type/NULL/bag/order/aggregate/nested contracts remain authority; preserve authored occurrence, module, relation, target, parameter and reader identity; distinguish planned, observed, qualified, Gate 2, CI and release claims. |
| 7–11: ownership, dependencies, versioning, capabilities, interchange | Semantics/IR remain neutral; MySQL owns realization, readers own decoded facts; no implicit migration; four-layer states distinguish unsupported/unknown/unqualified; nested interchange stays refused on MySQL, and the nested work package owns it (D77.32). |
| 12–16: execution, lifecycle, trust, algorithms, complexity | Execution remains explicit/read-only; pinned target/config/raw evidence are trust inputs; lifecycle and complexity ceilings require Gate 1, especially nested rows/children. |
| 17–21: invalidation, cache, concurrency, diagnostics, inspection | Re-evaluate actual compiled/public/pure/reader consumers; no new global cache; engine locks preserve isolation; diagnostic order/location remain stable; inspection cannot open a form. |
| 22–27: UX, conformance, fuzz, packaging, support, release | Canonical source/formatter spelling remains; each form needs a PG/MySQL differential, an independent value/error oracle and finite NULL/boundary/permutation controls. Reuse existing conformance and forged-input owners; no new fuzz framework. Maintenance binds dependency identity; platform support is not expanded; `0.1.11` publishes under PL.21 and PL.22. |
| 28–30: readiness, route, repairs | The scope after D77.32 and D77.35, the C/F/D/S ceiling and local validation are approved. Maintenance qualification has passed; AD77.01 and AD77.02, which select the nested transport and its public carrier, pass to the nested work package (D77.32); Gate 1 assigns P76-PERF-1 to P76-PERF-4 and binds the S14–S20 residual matrix, and each slice's exact per-form matrix precedes its acceptance. Stop for a budget cap, unproved input/evidence identity, trust regression, or a required change of product law. Preserve failed candidates. Later batches publish under D77.06, and a documentation-only or tool-only batch under its conditions (D77.14); while the owner is away, a new owner-level question takes the fail-closed default (D77.16); Phase77 authorizes no release, and `0.1.11` publishes under PL.21 and PL.22. |

## Activation record

The owner approved local implementation and its validation in D77.02. The
integrator binds the maintenance-qualified candidate, each slice's exact forms,
write set and differential matrix before opening that slice. A new numeric law
is resolved before its first consumer; the nested transport decision belongs
to the nested work package (D77.32). Local
candidate work does not certify Gate 2, publication or phase completion.

The S04, S05 and S09 materials and the numeric R4 and Phase72 B10 baselines
that the recovered records no longer hold are re-authored and re-run now, at
Phase77's cost (D77.15). The lost raw evidence stays recorded as lost; a
re-run is new evidence and never stands in for it. While the owner is away, a
new owner-level question takes the fail-closed default: the refusal stays, the
item is deferred and no public contract changes, and the question enters the
D77.07 packet (D77.16).

## S26 closure record

S26 ran on 2026-11-14 on the published head of the fourth `0.1.12` batch,
`e18d3673a4d4151d0bb73eafdfe8c68fe24745f8` (tree
`9b7bc006fad6a2f9cff43e0bb91cee01c245a2e9`), whose natural CI had not
finished, against the Phase baseline `f8ccd2c4`, the parent of the Gate 0
batch. That head holds every Phase77 product slice that opens a form,
S06's `same_value` in a JOIN `on` (D77.52) and every Wave A slice. S26
changes only documentation: it opens no form and changes no refusal.
Phase77 delivers no form of S04, S19 or S20, and the forms each slice left
refused are listed below. Premise 3's `ARCHITECTURE_DECISION`, the
`sum(Int)` strategy that S01 implemented as a guarded `SUM`, has no AD row
yet; the lead records it, with the alternatives and premises considered,
before S27's audit boundary.

### Acquisition

The review covers `f8ccd2c4..e18d3673` (74 commits, 57 of them changing
tests, scripts or `src`) by the
[phase-end acquisition consolidation](../../development.md#phase-end-acquisition-consolidation).
Tests changed in 186 files (48,440 lines added, 832 removed); 12 of those
files, about 24,400 lines today, are the test-only modules that PL.23's
audit finding 19 moved out of the wheel (`3458ee3b`).

- **New shared helpers.** Three, each the one owner of its slice's cells
  and probe world, built in process in a test's own temporary directory,
  with no process, database or state shared between tests:
  `tests/_pietto_sql_float_cells.py` (S06 and R01's `Float` row-comparison
  cells, read by seven test owners), `tests/_pietto_sql_nullsafe_cells.py`
  (S06's JOIN `on` cells, four owners) and `tests/_pietto_sql_paired.py`
  (Wave A's paired forms, two owners). Kept.
- **Moved helpers.** The twelve modules of `3458ee3b` are a move, not new
  acquisition. The move also changed thirteen native probe children in nine
  `tests/_pietto_execution_*_probe.py` helpers, which now load
  `verify_store` through `STORE_VERIFIER`; its message states that the
  native jobs campaigns that run them did not run, Git records none since,
  and natural CI does not run them. Recorded as not observed natively:
  owner, those nine helpers; latest point, the next native jobs campaign,
  which runs them before its result counts.
- **New module fixtures.** Four, each building one project or template
  under `tmp_path_factory` per worker, offline: `clocked`
  (`tests/test_results_timestamp_uuid.py`), `refinements`
  (`tests/test_execution_refinement_jit.py`), `now_built`
  (`tests/test_jobs_recovery.py`) and `mysql_typed`
  (`tests/test_execution_binding.py`). Their consumers only read what they
  built. Kept.
- **Processes and resources.** Three new `run_process` uses in
  `tests/test_cli_lsp.py`, which the
  [E-C audit](../../editor/ed03-completion-audit.md) reviewed; no other new
  subprocess, database, container or `ci_workload` declaration.
- **Repeated preparation.** Two low-value repetitions stay with their
  reasons: the formatting corpus of `tests/test_cli_lsp.py` and
  `tests/test_parser_format.py` (different oracles, and tests do not import
  test modules), and the `Float` refusal inputs shared by the `emit-sql`
  and compile API tests (independent consumers).
- **Result.** No significant repeated acquisition: no consolidation and no
  structural or wall-time gain (no gain).

P76-PERF-4: the oracle `tests/test_repo_reader_acquisition.py` and
`tests/_pietto_repo_facts.py` are unchanged since `f8ccd2c4`. Its corpus is
every `*.py` under `src/pietto` plus its three named test files,
`tests/test_repo_test_layout.py`,
`tests/test_semantic_fail_closed_capability_lookup.py` and
`tests/test_semantic_capability_facts.py`, which are unchanged since
`f8ccd2c4`; the `src/pietto` files went from 349 at `f8ccd2c4` to 351 at
`0.1.11` (two editor modules) and 342 at `e18d3673` (the twelve moved
modules out; `project_sql_emission_paired.py`,
`project_sql_emission_sum_forms.py` and `sql/mysql_paired.py` in). S26
treats `3458ee3b` as a later change that touches the oracle: the corpus rule
and the assertions are unchanged, the oracle finds the files itself, and it
passed in the Gate 2 of every later batch. It is retained.

P76-PERF-2, collected from the commits, fragments and decision rows:

| Slice | Recorded |
| --- | --- |
| S01 (`65f75708`) | The S02 query fact is asked once per aggregation stage, the compiled cells once per stage or verification, and the pure law stops at a fourth body: linear in the sums. |
| S03 (`adff0bce`) | Emission asks once per aggregation stage; compiled replay and the pure boundary derive the form a fixed number of times per reading. |
| S09 (`271c6c14`) | Each law walks the WHERE's `and`/`or` nodes once: linear in the chain. |
| S12 (`b768d63d`) | Emission's scan of a plan is counted once per plan. |
| S15 (`2a6159b3`), R08 (`d0ea1db6`) | Emission derives the cells once per projection. |
| R2's refusal (`75d658d1`) | A second derivation of a VERIFIED MySQL statement in `compile_query`: 16 to 33 percent of its time and up to 1.5 times its peak memory, accepted (D77.73). |
| S05, S06, S07, S13, R01, R02, S06's JOIN `on`, the stages over rows without fields, the `now()` slices | No operation count or input-scale measure is recorded. S26 collects and does not measure for them. |

The PIE-B1007 node limit stays 32768 and the compiled `VERSIONS` stay
`(8, 1, 8, 1)`. The caches that Phase77 added are call-scoped, with one
exception: S12 put `functools.lru_cache(maxsize=1)` on
`_reads_captured_field(plan)` in `_project/project_sql_emission_rows.py`.
The plan compares by identity and the cache holds the last plan, so the
answer is the one computed without it, and the last plan stays alive. A new
production cache goes to the owner (above); S26 refers it there and changes
no code. P76-PERF-3 applies when the profile below reads verifier runs per
top-level call.

The ten-node profile of the development rules has not run: the fourth
batch is Phase77's last product batch, and its natural CI had not finished.
S27 runs it on that CI's health before its audit boundary, reuses the E-C
review for nodes that did not change, and records the profile as not
observed if the health cannot be read. The E-C audit's debt, a
`verify_project_sql_plan` that is not memoized and runs 4 to 29 times per
case, stays debt: a memo is a new production memo, which goes to the
owner, and handing the verified plan to the five callers in
`emit_project_sql` changes the path of every Phase77 cell after the
product slices. Owner, `_project/project_sql_plan_verification.py` and its
emission callers; latest point, the phase-end acquisition consolidation of
the next phase that changes project SQL emission, which S27's handoff
names.

### Capabilities and cadence

S26 ran one plain example of each form below through `check` and `emit-sql`,
single file and project, PostgreSQL and MySQL, at `e18d3673`, and wrote the
[capability page](../../capabilities.md) rows that were missing: `Float /`,
`stddev` of an `Int`, `sum` and `avg` of a `Float`, `count_distinct` of a
`Float`, `lpad` and `now()`, `add_months`, `concat`, `round` with digits
and `date_trunc`, `Text(x)` of an `Int`, and a `Float` literal list over
two row reads; it qualified the `avg`, `select distinct` and set-operation
rows. Its checks of the `Float` arithmetic and sign, `sum(Decimal)`,
`variance` of an `Int`, `string_agg`, `Float` window key,
`count_distinct(a, b)`, aggregate window, `Decimal + Int`, `sum(Int)`,
`values` and `generate_series` rows agreed with the page.

Under the [MySQL cadence](../../roadmap.md#mysql-cadence) the `0.1.12`
release request lists, under J12 (3), every MySQL refusal below (D76.09).
S26 counts no phases per row: listing them all is the broad default. The
approved exceptions are project `sum(Int)`, whose target Phase77 is met only
in the S01 and S03 forms, `stddev` of an `Int`, which has no target
(D77.34), and nested results, which belong to the nested work package
(D77.32). No decision sets a target for the other `sum(Int)` forms, so they
take the fail-closed default (D77.16): they stay refused, each release lists
them under J12 (3) as an approved exception not yet met, and they have no
new target phase until the owner answers. That question enters the D77.07
packet. So does D77.52's O7, the separate decision on a MySQL `Float`
`same_value` in a JOIN `on` after S06's publication, which has not been
taken, so that form keeps its refusal by the same default. C04's E4 and
C06's `UUID` enter the packet with their default, the refusal (D77.29). S26
reports all four here.

| MySQL project form | Code and detail | Disposition | Decisions |
| --- | --- | --- | --- |
| `Int` arithmetic not proved to fit 64 bits, outside S01's cell | PIE-B1002 `arithmetic_outside_physical_range` | S01 opened its cell; the rest kept | D77.29 (C02), D77.48 |
| `sum` of an `Int` outside the S01 and S03 forms | PIE-B1004 `sum_int_aggregate_range_proof_missing` | approved exception, met only in the S01 and S03 forms; the rest kept by the default, with no target until the owner answers (D77.07 packet) | D77.16, D77.34, D77.53 |
| `stddev`, `variance`, `pvariance`, `pstdev` of an `Int` (single files: PIE-B1000) | PIE-B1003 `<function>_int_not_admitted_on_target` | S04 kept whole (R04) | D77.29, D77.34 |
| `sum`, `avg` of a `Float`; `stddev`, `variance`, `pvariance`, `pstdev` of a `Float` outside S05's shape | PIE-B1004 `float_aggregate_finite_result_proof_missing` | kept (R05, C03) | D77.29, D77.45 |
| `==`, `!=` or `same_value` of two `Float` row reads outside S06's forms; such a test in `any(...)`, or in `not any(...)` outside R02's forms | PIE-B1003 `comparison_type_pair_not_admitted` | kept (R01, R03) | D77.29, D77.30, D77.47 |
| A `Float` `x in name` or `x not in name` in a WHERE over a `let` with `capture` lines | PIE-B1003 `membership_type_pair_not_admitted` | refused by R01's repair | D77.28, D77.62 |
| `same_value` in a JOIN `on` outside S06's cells, a MySQL `Float` among them | PIE-B1003 `match_condition_not_in_row_domain`, with the `0.1.11` list | kept (O6); `Float`: O7's separate decision not taken, kept by the default (D77.07 packet) | D77.16, D77.52, D77.71 |
| A `Float` GROUP BY key outside S07's forms, or a `percent_rank` or `cume_dist` result as a key; `select distinct` of a `Float`; `union distinct`, `intersect`, `except` over `Float` rows | PIE-B1003 `group_key_type_outside_reviewed_comparison_domain`, `distinct_field_comparison_domain_unsupported`, `set_row_equivalence_domain_unsupported` | kept (R16) | D77.08, D77.29, D77.39 |
| `count_distinct` of a `Float`; a `Float` window key | PIE-B1003 `count_distinct_argument_outside_reviewed_int_domain`; PIE-B1002 `window_partition_comparison_domain_unsupported`, `window_order_comparison_domain_unsupported` | kept even when qualified | D77.39 |
| `Decimal(p, s)`, `Date`, `Timestamp` header parameters outside S09's cells; a `UUID` one, and every typed one in a query that declares a `UUID` | PIE-B1003 `query_parameter_type_not_admitted_on_target` | `UUID` withdrawn (C06); reopening needs a new preregistered run and an owner decision on its carrier | D77.29, D77.57 |
| `lpad`, `now()` outside S12's position; `add_months`; `concat` | PIE-B1003 `scalar_call_signature_not_admitted` | kept (R11, R12, R14) | D77.29, D77.44, D77.56 |
| `lpad` with a native parameter as its text or width (both targets) | PIE-S2355; PostgreSQL PIE-B1008 through an inline scalar | kept (R13) | D77.23, D77.29 |
| `first`, `last` of a `Bool`, `UUID`, `Date` or `Timestamp`, by another key than an `Int` or `Text`, or outside S13's forms (single files: PIE-B1000) | PIE-B1003 `first_last_not_admitted_on_target` | kept (R06, R07) | D77.29, D77.40, D77.58 |
| `Int /` outside R08's literal-proved forms | PIE-B1003 `binary_operator_not_admitted` | kept (R08) | D77.31, D77.33, D77.75 |
| `Int %`, `Float %` outside S15's cell | PIE-B1003 `binary_operator_not_admitted`, `float_remainder_exact_binary64_not_realized` | kept (C04) | D77.29, D77.38 |
| `Float /` | PIE-B1003 `float_division_not_realized` | kept | D77.38 |
| `Float` arithmetic other than between two literals; a sign on a `Float` (E4) | PIE-B1003 `float_literal_operands_required`, `unary_sign_requires_int_operand` | kept by C04's default: S15 took no E4 cell to a run | D77.29 |
| Direct `sum(Decimal)` (S19) | PIE-B1004 `decimal_aggregate_range_proof_missing` | S19 kept whole (R17) | D77.29 |
| Scalar calls or arithmetic over direct aggregates (S20) | PIE-B1003 `aggregate_composition_not_admitted_on_target` | S20 kept whole (R09) | D77.29 |
| Nested results: `collect`, `unnest`, lists of one row | PIE-B1003 `collect_not_admitted_on_target` | approved exception, nested work package | D77.32 |
| Wave A forms outside their paired forms: the conditional count, `any` and `all` over a group, `count_distinct(a, b, ...)`, aggregate windows, a `Text` literal default of `lag` or `lead`, `Decimal` arithmetic and sign, the forms beside or over JOIN rows, `max` and `min` of two `Date` values, and a single-file asof JOIN beside a FULL JOIN (PIE-B1000) | `main`'s, as the capability page gives them | Wave A opened only its paired forms; no target | D77.29 (R18), D77.35, D77.36, D77.55 |
| Typed `values(...)`; `generate_series` | PIE-B1003 `zero_physical_source_not_admitted_on_target`; `table_function_not_admitted_on_target` | no Phase77 slice | — |
| `Text(x)` of an `Int`; `round` with digits; `date_trunc` | PIE-B1003 `cast_realization_not_admitted`; `scalar_call_signature_not_admitted` | no Phase77 slice | — |
| A `Float` literal list whose value and an option both read rows | PIE-B1003 `membership_type_pair_not_admitted` | no Phase77 slice | — |
| `string_agg`; `median` and `quantile` (single files: PIE-B1000) | PIE-B1003 `aggregate_function_not_promised_in_slice8`; `quantile_not_admitted_on_target` | out of scope | the route |
| FULL JOIN on `Int` keys; on a `Float` equality | PIE-B1003 `mysql_full_join_approved_non_support`; `comparison_type_pair_not_admitted` | approved non-support, out of scope | the route |
| A GROUPS frame with an offset bound; EXCLUDE CURRENT ROW, GROUP or TIES (single files: PIE-B1000) | PIE-B1003 `window_frame_groups_approved_non_support_on_mysql`; `window_frame_exclusion_approved_non_support_on_mysql` | approved non-support, out of scope | [language](../../language.md#single-files-and-projects) |

The other single-file MySQL refusals of `0.1.11` (PIE-B1000) stay: the
conditional sum and a window key that names a computed `Text` `let`.
Beside these, the release lists as known limitations: R2 on MySQL refuses
every form that `0.1.11` refused, with PIE-R1004 `PUBLIC_R2_UNQUALIFIED_FORM`
or its earlier detail (D77.67, D77.68), and a MySQL query that reads `now()`
with `PUBLIC_R2_STATEMENT_SNAPSHOT` (D77.49); on both targets a `now()`
inside a computed output and a `Timestamp` or `UUID` parameter output are
refused at execution with PIE-R1004 `MEANING_OUTPUT` (D77.42); MySQL
`lower`, `upper` and `replace` give NULL past `max_allowed_packet` (R15,
D77.29); and single-file MySQL fails `INT64_MIN DIV 1` with error 1690
where PostgreSQL returns the value, while
[language](../../language.md#expressions) names only the overflow of
dividing by -1 (D77.55 (14)). The
[execution limits](../../execution.md#known-limitations) and the fragments
give their details.

### Package closure

At `e18d3673`, with Python 3.13.13 and no network, `uv lock --check`
resolved 23 packages, and `uv build` made the wheel (sha256
`5c1bf73f0f8ac37b86465f664a551be1eb2c90a935ea0cda10233fc1ef0fef74`) and
the sdist (`6efb80d3d02df433165a6933a3e3597337ca74fbfbb2e29a530466e13d6318f8`),
both still versioned `0.1.11`. `scripts/package_smoke.py`'s wheel and sdist
inspections pass on them. The wheel holds the 346 tracked files under
`src/pietto` and nothing else beside its metadata; the sdist's 369 members
hold no tests or documentation. Since `0.1.11` the wheel lost the twelve
test-only modules and gained the three modules named above. Since
`f8ccd2c4` the grammar and `src/pietto/generated` are unchanged, and the
dependencies changed only by M77.01's pins and the locked development
`ruff`. The Gate 2 of each `0.1.12` batch ran the installed package smoke; the
release commit's Gate 2 runs it on the `0.1.12` version.
