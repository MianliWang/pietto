# Phase77 route — LOCAL IMPLEMENTATION AUTHORIZED

The owner selected the complete 27-slice scope in D77.01 on 2026-11-08,
then approved local execution and validation under D77.02. Substantive numeric
and nested decisions below still precede their affected openings. Batches
publish under D77.06 (Gate 2 and a clean batch audit, fast-forward only), and
no release is authorized; local development is not publication.

## Starting point and outcome

The proposed baseline is published `main` at
`f8ccd2c44a2d9adf431a496bd9bbae037783176f`, tree
`460e3e135d1dcb0b926928bc2632a889410f258a`. Its exact-head push workflow
`42489408515`, attempt 1, accepted 21 jobs. Before Gate 1, Gate 0 must
rebind the live branch/tree/remote/CI, Phase76 completion audit, dependency
inputs, and PostgreSQL/MySQL image and session identities. The Phase76 handoff
rather than this draft determines exact residual MySQL forms.

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

Gate 1 also must assign P76-PERF-1 through P76-PERF-4: preserve operation,
root and object identity before changing Project SQL readers; measure input
scale before public/pure emission changes; bind exact document/mutation
identity before inferring memo behavior; and retain or replace the independent
repository-fact oracle at maintenance triage. These are bounded follow-ups,
not authority for a global cache or deleted verification.

## Proposed ordered work

| Slice(s) | Proposed result | Required acceptance before it opens |
| --- | --- | --- |
| S01–S03 | Checked `Int`, `sum(Int)`, conditional/JOIN/two-level sums | Signed-64 decision; literal and parameter boundary probes; independent result reader. |
| S04–S05 | `Int` statistics and finite Float aggregates | Per-operation type/NULL/extreme oracle. |
| S06–S07 | Float row equality, `same_value`, grouping, DISTINCT, sets and `count_distinct` | Merged-zero decision and bag/multiplicity controls. |
| S08–S12 | Aggregate windows, typed parameters, conditional count/`any`/`all`, multi-column `count_distinct`, selected text/date/`now` forms | Per-form four-layer capability matrix and target qualification. |
| S13 | Ordered `first`/`last` | Selected order/tie/NULL contract and refusal controls. |
| S14–S20 | Phase76 MySQL E/N/D residuals | Gate-0 residual matrix; do not reimplement completed PostgreSQL forms. |
| S21–S24 | One-layer Collect, Unnest, decoder/Arrow/saved readers, selected list/group/detail forms | Separate nested decision and finite matrix; dependency order S21 → S22 → S23 → S24. |
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
| 1–2: authority and outcome | Rebind exact live evidence; selected MySQL parity only, never blanket parity. |
| 3–6: semantics, identity, states, proof | Existing type/NULL/bag/order/aggregate/nested contracts remain authority; preserve authored occurrence, module, relation, target, parameter and reader identity; distinguish planned, observed, qualified, Gate 2, CI and release claims. |
| 7–11: ownership, dependencies, versioning, capabilities, interchange | Semantics/IR remain neutral; MySQL owns realization, readers own decoded facts; no implicit migration; four-layer states distinguish unsupported/unknown/unqualified; nested interchange is blocked pending S21–S23. |
| 12–16: execution, lifecycle, trust, algorithms, complexity | Execution remains explicit/read-only; pinned target/config/raw evidence are trust inputs; lifecycle and complexity ceilings require Gate 1, especially nested rows/children. |
| 17–21: invalidation, cache, concurrency, diagnostics, inspection | Re-evaluate actual compiled/public/pure/reader consumers; no new global cache; engine locks preserve isolation; diagnostic order/location remain stable; inspection cannot open a form. |
| 22–27: UX, conformance, fuzz, packaging, support, release | Canonical source/formatter spelling remains; each form needs a PG/MySQL differential, an independent value/error oracle and finite NULL/boundary/permutation controls. Reuse existing conformance and forged-input owners; no new fuzz framework. Maintenance binds dependency identity; platform support is not expanded; `0.1.11` needs separate release approval. |
| 28–30: readiness, route, repairs | Full scope, C/F/D/S ceiling and local validation are approved. Maintenance qualification has passed and AD77.01 and AD77.02 select the nested transport and its public carrier; the exact per-form matrix and the P76-PERF disposition precede their affected acceptance. Stop for a budget cap, unproved input/evidence identity, trust regression, or a required change of product law. Preserve failed candidates. Batches publish under D77.06; no release is authorized. |

## Activation record

The owner approved local implementation and its validation in D77.02. The
integrator binds the maintenance-qualified candidate, each slice's exact forms,
write set and differential matrix before opening that slice. A new numeric law
or nested transport decision is resolved before its first consumer. Local
candidate work does not certify Gate 2, publication or phase completion.
