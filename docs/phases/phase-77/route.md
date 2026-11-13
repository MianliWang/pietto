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
   text and NULL, errors and the stored bytes are unchanged.

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
| S09, S12 | Typed parameters, selected text/date/`now` forms | Per-form four-layer capability matrix and target qualification; S09 follows D77.13 with its material re-authored (D77.15). |
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
