# Phase77 route — LOCAL IMPLEMENTATION AUTHORIZED

The owner selected the complete 27-slice scope in D77.01 on 2026-11-08,
then approved local execution and validation under D77.02. Substantive numeric
and nested decisions below still precede their affected openings. The
maintenance/editor batch published under D77.04. Each later batch publishes
under D77.06 (Gate 2 and a clean batch audit, fast-forward only), and so does
a batch that changes only documentation or tools (D77.14). No release is
authorized; local development is not publication.

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

The complete S01–S27 route is selected. The alternative of separate flat and
nested work packages was not selected; these are dependency groups within the
same scope:

| Group | Product slices | Boundary |
| --- | --- | --- |
| A — flat MySQL adaptation | S01–S20 and S25 | Opens only selected flat forms; cannot close Phase77 while S21–S24 remain unresolved. |
| B — nested MySQL results | S21–S24 | Opens only the approved one-layer nested forms after its separate transport decision. |

S26/S27 are phase-wide acquisition/audit work: they run only after both
groups are complete or an owner decision records each retained exception.
Keeping S21–S24 numbered avoids treating unfinished nested work as resolved.

`C280/F850/D25000/S12` is the approved cumulative ceiling for the complete
27-slice route (D77.02, D raised by D77.03 and D77.05), not a target or a per-group allowance. No handoff or
lane resets it. Each lane reports its checks and repairs to the integrator.

Out of scope: `string_agg`, project FULL JOIN emulation, median/quantile
emulation, arbitrary-depth nesting, new syntax, general optimization, SQL
escapes, and PostgreSQL SQL rewrites. Existing refusals remain until a later
decision admits a specific form.

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
4. The selected scope includes `first`/`last` and the same-relation ASOF/FULL
   backlog. Preserve their existing order, tie and NULL rules. A proposed
   cadence exception or changed meaning, rather than a target proof, requires
   a new owner decision.
5. `ARCHITECTURE_DECISION`: before S21–S23, the MySQL nested transport seam:
   occurrence identity, order, empty/missing/NULL, exact leaf decode,
   resource lifetime, and live/compiled/Arrow/saved-reader closure.
   AD77.01 selects the versioned JSON envelope; AD77.02 publishes its carrier
   in project JSON v2 and keeps only the envelope layout private.

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
   compares with (D74.09).
5. **S23 compiled records** (D77.12). By default S23 only admits MySQL at the
   three compiled verifier gates `LIST_TARGET`, `UNNEST_ROUTE` and
   `COLLECT_TARGET` and changes no compiled record. Only if a record change is
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
| 1 | Before a Project SQL reader changes (live, compiled, pure, public decoder, and S23's saved and source-free readers), operation, root and object identity are shown to be preserved. | The changed reader functions are listed; the complete `tests/test_project_verification_scope.py` passes on the bound tree; value-equal roots that are distinct objects are each verified; a value-equal record swapped in between two calls reports `COMPILED_INPUT_CHANGED`; PostgreSQL bytes are unchanged. |
| 2 | Before public or pure emission changes, input scale is measured. | Operation counts, not wall time; a bounded before/after comparison only for an open question; a superlinear finding is fixed and gains an operation-count test; the PIE-B1007 generated-node limit of 32768 is unchanged. |
| 3 | Before memo behavior is inferred, the exact document and mutation identity are bound. | The memo key and the object it keys are named; the call-scoped `once` identity marker is not a memo; no production memo is added. |
| 4 | The independent repository-fact oracle is retained or replaced. | Its corpus stays every `*.py` under `src/pietto` plus its three named test files, and it is not deleted without an equivalent replacement. The maintenance/editor batch changes neither the oracle nor `tests/_pietto_repo_facts.py`, so it is retained unchanged. |

| Slice | PERF |
| --- | --- |
| S08, S11 | 1 and 2; 3 when it infers memo behavior or extends the memo or receipt tests |
| S09, S10, S12, S16, S17–S19, S21, S22, S24 | 1 and 2 |
| S23 | 1 and 2; 3 under the S08 condition |
| S01, S02, S04, S05, S13, S15, S20 | 2; 1 when a reader changes |
| S03, S06, S07 | 2 when public or pure emission changes |
| S14 | 2 only when a public document shape changes; otherwise its exemption reason is recorded |
| S25 | none; it changes only `src/pietto/sql/joins.py` |
| S26 | 4 when a later change touches the oracle; collects 2; 3 when it reads the verifier runs per top-level call of the slowest-node profile |
| S27 | records the final disposition of all four |

Only a new production memo or cache, a change to the PIE-B1007 limit or to
PostgreSQL bytes, or deleting the oracle without an equivalent replacement
goes to the owner.

The residual matrix binds the Phase76 MySQL E/N/D residuals. Only S15 is
named by the route text above; the other slots follow the recovered
candidates, and S20, which has none, takes D2 by the lead's binding.

| Slice | Forms | Current MySQL project refusal | Before it opens |
| --- | --- | --- | --- |
| S14 | E2: a `def` that inlines to a conditional in a query a JOIN reads; E3: a scalar call in an aggregate argument over JOIN rows | PIE-B1003 `scalar_projection_requires_later_slice` (E2) or `operator_not_implemented_in_slice6` (E3), then `join_shape_not_admitted_in_slice7` | An E2 cell; BETWEEN, `in`, cast, scalar call and LATERAL each get a cell or are listed as retained; the PostgreSQL and MySQL flat parents. |
| S15 | E5: `Int /` (`DIV`), `Int %`, `Float /` | PIE-B1003 `binary_operator_not_admitted` (`Int`); `Float /` computes `float_division_not_realized`, but on `ab972f36` `emit-sql --project` stops with `ValueError: unclassified blocker suggestion` instead of returning it | Attaches to S01's numeric child; a zero divisor returns NULL and the result is nullable; `INT64_MIN / -1` and `INT64_MIN % -1` are preregistered as unobserved, not as pass criteria, and a PostgreSQL/MySQL difference escalates under the second prerequisite above; Float `/` and `%` cells; a PostgreSQL differential. |
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
| `Float % Float` | computes PIE-B1003 `float_remainder_exact_binary64_not_realized`, but on `ab972f36` `emit-sql --project` stops with `ValueError: unclassified blocker suggestion` instead of returning it | S15 |
| E6: `Float` window keys and `percent_rank`/`cume_dist` result keys | PIE-B1002 `window_partition_comparison_domain_unsupported`, `window_order_comparison_domain_unsupported`; PIE-B1003 `group_key_type_outside_reviewed_comparison_domain` | S06/S07 |
| `max(a, b)`, `min(a, b)` of two `Date` values | PIE-B1003 `conditional_realization_not_admitted` | S14; the delivered PostgreSQL form is not reclassified as unfinished |

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
| S08–S12 | Aggregate windows, typed parameters, conditional count/`any`/`all`, multi-column `count_distinct`, selected text/date/`now` forms | Per-form four-layer capability matrix and target qualification; S08 follows D77.11, and S09 follows D77.13 with its material re-authored (D77.15). |
| S13 | Ordered `first`/`last` | Selected order/tie/NULL contract and refusal controls. |
| S14–S20 | Phase76 MySQL E/N/D residuals | The Gate 1 residual matrix (D77.10) on the Gate 0 head; do not reimplement completed PostgreSQL forms. |
| S21–S24 | One-layer Collect, Unnest, decoder/Arrow/saved readers, selected list/group/detail forms | Separate nested decision and finite matrix; S23 follows Gate 1 item 5 (D77.12); dependency order S21 → S22 → S23 → S24. |
| S25 | Single-file same-relation ASOF with existing FULL emulation | Existing ASOF/FULL limits, PostgreSQL differential, and no project-FULL claim. |
| S26–S27 | Acquisition/capability/lag/package closure; audit/handoff | All selected product slices plus every retained-debt/deferral disposition. |

Every selected target cell records exact source/configuration/SQL/parameters,
catalog/physical metadata/raw result and an independent oracle. PostgreSQL and
MySQL campaigns may run one owned container each under the existing engine
locks, fixed local images, `--pull=never --network none`, owned cleanup and a
two-hour ceiling (D77.02). A failing cell keeps its
deterministic refusal; no target-specific fallback is invented.

## Initiation-gate checklist

| Fields | Proposed answer or Gate 1 blocker |
| --- | --- |
| 1–2: authority and outcome | Gate 0 is bound to `ab972f36` with natural CI `42831340276`; each later batch rebinds exact live evidence; selected MySQL parity only, never blanket parity. |
| 3–6: semantics, identity, states, proof | Existing type/NULL/bag/order/aggregate/nested contracts remain authority; preserve authored occurrence, module, relation, target, parameter and reader identity; distinguish planned, observed, qualified, Gate 2, CI and release claims. |
| 7–11: ownership, dependencies, versioning, capabilities, interchange | Semantics/IR remain neutral; MySQL owns realization, readers own decoded facts; no implicit migration; four-layer states distinguish unsupported/unknown/unqualified; nested interchange is blocked pending S21–S23. |
| 12–16: execution, lifecycle, trust, algorithms, complexity | Execution remains explicit/read-only; pinned target/config/raw evidence are trust inputs; lifecycle and complexity ceilings require Gate 1, especially nested rows/children. |
| 17–21: invalidation, cache, concurrency, diagnostics, inspection | Re-evaluate actual compiled/public/pure/reader consumers; no new global cache; engine locks preserve isolation; diagnostic order/location remain stable; inspection cannot open a form. |
| 22–27: UX, conformance, fuzz, packaging, support, release | Canonical source/formatter spelling remains; each form needs a PG/MySQL differential, an independent value/error oracle and finite NULL/boundary/permutation controls. Reuse existing conformance and forged-input owners; no new fuzz framework. Maintenance binds dependency identity; platform support is not expanded; `0.1.11` needs separate release approval. |
| 28–30: readiness, route, repairs | Full scope, C/F/D/S ceiling and local validation are approved. Maintenance qualification has passed and AD77.01 and AD77.02 select the nested transport and its public carrier; Gate 1 assigns P76-PERF-1 to P76-PERF-4 and binds the S14–S20 residual matrix, and each slice's exact per-form matrix precedes its acceptance. Stop for a budget cap, unproved input/evidence identity, trust regression, or a required change of product law. Preserve failed candidates. Later batches publish under D77.06, and a documentation-only or tool-only batch under its conditions (D77.14); while the owner is away, a new owner-level question takes the fail-closed default (D77.16); no release is authorized. |

## Activation record

The owner approved local implementation and its validation in D77.02. The
integrator binds the maintenance-qualified candidate, each slice's exact forms,
write set and differential matrix before opening that slice. A new numeric law
or nested transport decision is resolved before its first consumer. Local
candidate work does not certify Gate 2, publication or phase completion.

The S04, S05 and S09 materials and the numeric R4 and Phase72 B10 baselines
that the recovered records no longer hold are re-authored and re-run now, at
Phase77's cost (D77.15). The lost raw evidence stays recorded as lost; a
re-run is new evidence and never stands in for it. While the owner is away, a
new owner-level question takes the fail-closed default: the refusal stays, the
item is deferred and no public contract changes, and the question enters the
D77.07 packet (D77.16).
