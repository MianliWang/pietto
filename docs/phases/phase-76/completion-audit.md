# Phase76 completion audit

Phase76 implements the twelve-slice scope of the [route](route.md) and
D76.01–D76.18 in the [decision record](../../decisions.md#phase76--owner-decisions-2026-11-07).
This audit records implementation and database acceptance. The final Gate 2
seal and the natural exact-head CI of the B2 publication determine phase
completion; this document does not certify its own publication. The required
profile consumes that final CI's health after publication.

## Baseline and publication boundary

The phase starts at the released `0.1.10` commit
`8e7c43f1852b2c26318b3217268a1f7416f44965`, tree
`dceca22cc2ae0c1a5dabfb7d047d59d283912996`.
B1 published the four documentation steps and S01/S02/S03/S06/S07 at
`87668dc1946986cc84cf60fcccab68abf8bc5418`, tree
`c10c5d016f19957c1c34e1d21c462e6d0c9a1bd2`.
Its authoritative Python 3.13.13 run passed 27,158 tests with 41 skips;
[natural CI 42422096727](https://github.com/MianliWang/pietto/actions/runs/42422096727)
accepted all 21 jobs. Interior batch commits inherit the batch-head result.

B2 contains S04/S05/S08/S09/S10/S11/S12, one ordinary commit per slice and
one final-tree validation/publication. The database campaign used source tree
`a4c3ed7005a357e51cb8f2120233ba637d1f263e`. Later metadata and primitive-fact
reader repairs are bound to `e5c9ce567601401016d5b35f1e6fb0ece0734adf`:
all 88 SQL/execution contracts and the 26 legacy documents were re-emitted and
matched, with only the registered material-root change in two diagnostic
paths. The fresh complete corpus also matches the prior 1,727 outputs exactly;
these source-adoption records preserve the original database run as original. Operational seals, immutable
snapshots, raw reports and failed predecessors remain in the external
`phase76/codex-recovery` ledger. Git and natural CI own the publication state.
No tag or package release is part of these batches. Phase76 and Phase77 are
planned together for core `0.1.11`, with separate release approval; PyPI is
uploaded by the owner.

**Publication follow-up, 2026-11-08.** B2 is published at
`f8ccd2c44a2d9adf431a496bd9bbae037783176f`, tree
`460e3e135d1dcb0b926928bc2632a889410f258a`. Its final Python 3.13 Gate 2
passed 27,593 tests with 41 skips, plus golden and package checks. Natural
[CI 42489408515](https://github.com/MianliWang/pietto/actions/runs/42489408515),
push/main attempt 1, accepted all 21 jobs. The ten final-CI profile nodes
passed individually; their analysis and independent review closed in the
external ledger on the same day. Per-node monotonic durations and the UTC
window disagree, so the profile supports no precise total-time or speedup
claim. The retained plan/emission, pure-boundary, consumer-memo and repository
fact-acquisition follow-ups transfer to Phase77 planning without authorizing
cache, verifier or scheduler changes. Phase76 is complete and published;
the combined core release remains separate.

## Accepted scope

The release-note fragments linked below contain the precise public forms and
retained diagnostics. A passing target primitive is not, by itself, an emitted
product statement or an execution qualification.

| Slice / line | Delivered behavior and limits | Acceptance |
| --- | --- | --- |
| [S01](../../release-notes.d/76-s01-join-port-admission.md), E1/H | JOIN admission follows the ports actually read; unread temporal/UUID fields no longer reject the whole qualified JOIN. PostgreSQL count-distinct member and MySQL reopened min/max composition witnesses remain bounded to their recorded forms. MySQL FULL JOIN stays refused. | Published B1, including the two-engine CROSS/composition campaign. |
| [S02](../../release-notes.d/76-s02-joined-expressions.md), E2/E3 | PostgreSQL project joined WHERE can consume the admitted inlined conditional def, and aggregate arguments retain the qualified scalar, grain and input-port proofs. Two-argument Date min/max is included in the recorded PostgreSQL witness. | Published B1; the Date witness is delivered, not automatically deferred again. |
| [S03](../../release-notes.d/76-s03-float-arithmetic-and-keys.md), E4/E6 | Qualified PostgreSQL Float arithmetic/sign and window/FULL JOIN/distribution keys, with finite-binary64 and overflow/underflow premises. | Published B1; MySQL retained refusals and already-successful SQL are preserved. |
| [S04](../../release-notes.d/76-s04-project-expression.md), E5/E7 | Qualified PostgreSQL project Int/Float division, Int remainder, exact simulated Float remainder, and Text literal navigation defaults. Int division truncates toward zero; Int remainder follows the dividend. | Product run2: 17 cases including 8 expected errors; primitive Float evidence is separate. Final re-emission preserves all 19 registered positive/refusal documents and execution metadata. |
| [S05](../../release-notes.d/76-s05-decimal-project.md), E8–E10 | PostgreSQL exact Decimal/Int and different-scale Decimal addition/subtraction, plus qualified Decimal SUM. E8's exact-decimal-literal premise is absent, so that form stays refused. | Product run4: 7 product frames; all final statements and execution metadata match the qualified originals. The separate 22003 cast control is not a source-cardinality proof. |
| [S06](../../release-notes.d/76-s06-postgres-ca.md), T1/T2 | Optional caller `ca_file` makes both PostgreSQL routes verify chain and hostname or refuse before connection; the existing bounded-read contract is documented. Ambient/default CAs do not replace caller authority. | Published B1; TLS campaign 18 positive/negative checks, with old no-CA behavior retained. |
| [S07](../../release-notes.d/76-s07-mysql-constants-and-now.md), M | MySQL single-file constants, `--set` and `now()` using `UTC_TIMESTAMP(6)`; the capability rows for string aggregation and typed project parameters. | Published B1 and its accepted two-engine/timezone evidence. MySQL project `now()` does not open. |
| [S08](../../release-notes.d/76-s08-decimal-multiply-sign.md), N1 | Decimal times Int in either order and unary Decimal signs; each operation retains its own precision/scale proof. | Final B2 campaign: PostgreSQL/MySQL single-file and PostgreSQL project forms; legacy different-scale Decimal multiplication SQL remains unchanged. |
| [S09](../../release-notes.d/76-s09-computed-let-grouping.md), D1 | Single-file GROUP BY and SELECT share the same computed-let binding. A different binding with equal-looking syntax is not substituted. | Final B2 two-engine one/two-query, duplicate, NULL and binding controls. |
| [S10](../../release-notes.d/76-s10-aggregate-composition.md), D2 | Scalar calls/arithmetic over direct aggregates, with real ordered leaf occurrences, independent outer type/nullability, qualified group keys, original JOIN ports and checked carriers. Grouped zero-leaf outputs require another real SELECT aggregate; HAVING/ORDER retain their existing namespaces. | Final B2 single-file two-engine and PostgreSQL project campaigns; live, compiled, portable/pure and public-consumer repairs independently reviewed. MySQL project composition stays refused. |
| [S11](../../release-notes.d/76-s11-header-and-formatting.md), H1/fmt/acquisition | Hand-built Header.mode no longer controls analysis. Grammar/tokens remain under the migration/hint compatibility fallback. Supported dirfd platforms retain the trusted parent from source read through replacement; fallback platforms keep their explicitly narrower guarantee. Tests use the owner of the deepest observed product layer. | Header/fmt independent reviews; final owner migrations and source/typing checks. No grammar/catalog change or extension sync is implied. |
| S12 | This audit, engineering lessons, the Phase77 handoff and Phase82 freeze inputs. | Audit-only; no new product semantics or next-phase implementation is introduced here. |

## Final database and byte evidence

The B2 campaign `phase76-b2-20261108t100154z-codex` runs 183 preregistered
cells: PostgreSQL 122 across 17 fixtures and MySQL 61 across 9 fixtures.
Both strict judges and the independent raw audit accept the exact final
source snapshots, 88 public-CLI recipes, SQL/parameters, seed/catalog and
whole-source readbacks, 4 expected runtime errors, 6 ordered comparisons,
and bag multiplicity elsewhere. Each engine uses its fixed local image,
`--pull=never --network none`, its own flock, bounded runtime and owned cleanup.
No receipt-only claim substitutes for the recorded wrapper invocation or raw
output. The 26 S04/S05 final re-emissions are byte/metadata identical to their
registered originals and adopt those existing runs rather than pretending to
be new database executions.

The three relations in
[`aggregate_composition.pietto`](../../../examples/queries/aggregate_composition.pietto)
are the exact bytes of the executed PostgreSQL grouped fixture. All three
run over mixed/duplicate, all-NULL, empty, cross-NULL, rounding-tie and
negative/wide-integer datasets: 21 actual cells. Its public check and emit
commands also succeed. The separate JOIN witness proves the qualified
composition values `(9, 6, 5)`; same-row alias identity is additionally tested
by independent live/compiled/pure mutations, not claimed from numerically
identical aliases alone.

The final full Gate 0 corpus contains 1,727 entries: 1,713 are byte-identical
and all 14 changes have a complete independent disposition. Two retained MySQL worked-example refusals update diagnostic messages and ten
retained Float-set refusals update suggestions; PostgreSQL Float
arithmetic and Int remainder are authorized openings. No formerly successful
SQL changes without explanation. The earlier d6 attempt timed out at 1,200
seconds and has no adoptable partial result. The successful final comparison
uses eight processes and preserves the frozen corpus/input/source identities.
Generated-parser inputs are unchanged; their accepted B1 result is reused only
with that closure. Golden and fresh-package checks accompany the final seal.

## Retained boundaries

- Float remainder is qualified for PostgreSQL projects; single files retain
  PIE-B1000 and MySQL projects retain PIE-B1003 `binary_operator_not_admitted`.
  Unqualified navigation default fields/parameters do not open.
- Decimal literal comparison does not recover exact digits from an already
  Float literal. Project Decimal division/AVG, Decimal/Float operations,
  project `matches`, Float beside an Int literal, the other D76.03 rows and
  MySQL project N1 keep their documented refusals.
- SUM's checked `numeric(p+19,s)` result cast has its own 65/30 bounds and
  runtime overflow behavior. It proves neither source cardinality nor the
  multiplication bound.
- Nested aggregates, raw non-key outer reads, same-SELECT alias/self/forward
  reads, constructors, conditionals/comparisons, windows or generators around
  aggregates remain outside the first version. Project Decimal AVG remains
  refused; the Decimal AVG/round example is single-file.
- Global standalone literals beside an aggregate retain PIE-S2312; the
  no-aggregate grouped-query refusal remains. Single-file literal ORDER keeps
  PIE-S2380, while project projected ports use their existing rules.
  Aggregate SELECT parameter positions retain PIE-S2355. Existing WHERE
  parameters remain legal; parameterized observation export keeps its
  existing OUTSIDE_SCHEMA boundary.
- MySQL project compositions report PIE-B1003
  `aggregate_composition_not_admitted_on_target` for every authored outer
  expression in source order. Existing two-query and retained logical-only
  contexts do not grant a new execution capability.
- Matching a contract relation to the source table string is still D76.06's
  separate decision. Fixture-source checks used for database qualification
  do not silently add that product contract.
- Formatting is atomic per file, not per project. The held-parent guarantee
  begins at trusted read; discovery and native Windows/fallback races are not
  declared universally solved. Header grammar retirement is not claimed.

## Compiled compatibility

The compiled marks move once from `(7, 1, 7, 1)` to `(8, 1, 8, 1)` in S04;
subsequent slices share that change. The pre-1.0 upgrade actions stay separate:

1. Recompile from source/contracts/parameters in the matching new environment;
   no old bundle or saved job is silently migrated or rewritten.
2. Read old results according to their own format, code-identity and trust
   contract, using the exact previous `pietto==0.1.10` environment when needed.
3. Run again only as a separate database execution against its then-current
   data. Neither recompilation nor reading historical bytes requests a rerun.

## Acquisition, failures and final profile

The phase-end review covers changed tests/helpers and their direct consumers.
The first twelve owner migrations preserve 96 parameter instances and the
final twelve preserve 62; these are observations, not count locks. Entire
compiled closures move to existing execution owners, with strict acquisition,
all assertions, source order and fresh mutation/process/installed witnesses
preserved. The final integrated focused run passed 697 cases and exposed 22
old window-parameter behaviors affected by a missed verifier caller during
the NativeUse interface change. That shared caller was repaired without
changing assertions: the writer's complete parameter/aggregate run passes
196 cases and an independent old-window/identity run passes 36.

The first final collection also exposed two obsolete fixed example counts.
The repaired example consumers discover the nonempty current corpus and use
the documented analyzed script paired with its semantic model, retaining
original definition identity assertions and all three new example artifacts.
These six owners pass 143 cases. Global typing then found the metadata
field-leaf and per-primitive inspection readers; their complete repair keeps
old direct records/bytes, binds real leaf analyses and alignment ownership,
and passes both global type gates plus 628 related behavior checks. The
failed collection/type-check candidates remain separate; neither ran the
complete authoritative pytest gate.

All earlier failing trees, commands, timeouts, fixtures and receipts remain in
the ledger. The cumulative limits are C150/F450/D10000/S12; neither a handoff
nor a new lane resets prior costs or historical unknowns. Focused checks,
local/Teach results, database qualification, Gate 2, natural CI and release
remain distinct evidence layers.

The required final-CI profile is performed after publication: select the ten
slowest in-process nodes from that exact CI's qualified health, run each alone
under the reviewed cProfile driver on a quiet host, and fix, assign debt or
record a reason for each finding. B1 timing preparation is not this result.
Small repeated zero-leaf and plan-portability acquisitions are retained with
explicit owners/reasons pending that evidence; fresh trust witnesses are not
merged merely to reduce counts. This audit changes no scheduler or topology.

## Phase77 handoff and Phase82 inputs

Phase77 receives the exact remaining MySQL E/N/D forms, including project
aggregate composition, checked Int arithmetic, SUM/STDDEV(Int) cadence
exceptions and the separately scoped nested results work. Gate 1 binds its
own scope/budget, target qualification and Float merged-zero contract.
First/last order-key let maps, diagnostics beside refused lets or failing
generators, and the remaining explicitly deferred follow-ups keep their
owners; the already-qualified Date min/max witness is not reclassified as
unfinished. The deferred dependency maintenance window precedes formal
Phase77 Gate 0. The owner's later parallel-work authorization permits
independent preparation and the separate editor feature candidate; it does
not add those changes to Phase76 or assert their publication.

The [Phase82 ledger](../../roadmap.md#phase82-freeze-ledger) retains the header
rule/tokens, compiled and saved-state compatibility, public editor facts and
entry-point decisions, formatter/platform support, extension/function SPI,
array/JSON and nested ADBC decisions, and the prior compiled/live JOIN-grain
and forged-compiled-admission trust inputs. They must be decided before their
first new consumer or their stated latest gate. Core `0.1.11`, future backend
phases and the separately versioned VS Code extension retain their own gates.
