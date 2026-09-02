# Phase 62 Slice 12 Per-Aggregate Fact Locality, Chasm Detection, And Multi-Fact Alignment v1

## Starting Authority

Slice 12 starts from published commit
`f47d33dc3dfd74315a76ef62496953c804a6515c`, tree
`292a20a6697856b187f92da6e67086ecbfc11c51`, and natural exact-head
`push/main` CI `33569455067`, attempt 1, success. The preserved failed Slice-11
parent `afca8aacc22d735a678721cb9e4b3348eb505988` and CI `33568043743`
remain historical authority only.

Phase 62 is active. Slices 1–11 are completed/published, Slice 12 is the sole
current publication candidate, and Slices 13–16 are not started.

## Exact Owner And Architecture

The sole production addition is private
`src/pietto/_project/project_multifact.py` with `__all__ = ()`.

```text
base Project IR aggregate evaluation contexts
+ base relational properties
+ Slice-11 binary JOIN regions/properties
-> aggregate fact catalog
-> occurrence-specific JOIN localities
-> actual common-grain candidates and chasm evidence
-> useful pairwise multi-fact alignment
```

Slice 12 analyzes existing aggregate results. It does not construct an
aggregate over a JOIN-bearing relation. The Slice-10 barrier remains exact:

```text
JOIN-bearing ProjectModuleRelationSemanticFacts
= AUTHORED_JOIN_DEFERRED
```

No joined scalar namespace or unary tail is added.

## Fact Identity And Complete Catalog

```text
aggregate result occurrence != aggregate relation declaration
aggregate result occurrence != output field name
aggregate result occurrence != fact locality
aggregate result occurrence != JOIN binding
aggregate result occurrence != grain factor
```

One `ProjectAggregateFactOccurrence` is identified by the exact
`GROUP_AGGREGATE` plan-node ref plus aggregate-result position in its exact
evaluation context. Construction follows aggregate-context order and then
aggregate-result order. Every concrete aggregate result appears once;
non-aggregate select values, window results, relation declarations, and
JOIN-deferred aggregate-looking source text do not become facts.

Each fact retains its exact aggregate context/result/select occurrence and
selected ordinal, its distinct GROUP-stage and final/home field authorities,
the final scalar export and home value class, input/result/home relational
properties, and source/result intrinsic grain. Names and aliases never resolve
identity.

## Home And JOIN Locality

Every fact has one exact home locality at its final standalone relation output.
It retains the fact result grain and has no relationship entry path,
introduction use, or JOIN occurrence.

For each concrete JOIN region, a fact receives one JOIN locality for every
exact `ProjectIRJoinInputUseOccurrence` that consumes its standalone home
output. The same fact introduced twice therefore has two localities.

```text
fact occurrence != fact locality
```

A JOIN locality retains the concrete region, introduction JOIN/use and side,
the right-side path step when present, every later carried field instance, the
final region field, the exact contextual factor-use set, final-grain
comparison, and every causative multiplicity exposure. Intermediate multi-hop
inputs are eligible. Field mapping uses original semantic-field evidence plus
exact introduction use; no field, alias, or relation-name winner exists.

Each active home factor maps to the exact
`ProjectJoinGrainFactorIdentity(base, introduction_use, nulling_joins)` already
published by Slice 11. GLOBAL remains explicit with zero active factors.

## Grain Comparison And Actual Common Grain

Slice 12 reuses the Slice-6 typed factor universe, compiled dependency index,
and indexed worklist closure. It adds no closure algorithm, factor-subset
enumeration, or persistent cache. Each directional result retains its seed,
requested set, closure, and exact dependency index so the determination
replays.

```text
A reaches B and B reaches A -> EQUAL
A reaches B only             -> A FINER
B reaches A only             -> B FINER
neither                       -> INCOMPARABLE
```

Common-grain candidates come only from retained fact contextual grains,
standalone JOIN inputs, exact binding/source slices, and actual JOIN outputs.
An empty candidate exists only with retained GLOBAL authority. Candidate
construction never invents arbitrary factor subsets.

The winner-free result is exactly:

```text
UNIQUE
AMBIGUOUS
NONE
UNKNOWN
CONFLICT
```

Only common candidates reached by both facts are considered. Strictly coarser
dominated candidates are removed; every non-dominated finest actual candidate
remains in authority order. There is no first, shortest, smallest, or
lexicographic winner.

## Structural Alignment, Risk, And Requirements

The structural axis is exactly:

```text
EXACTLY_ALIGNED
STRUCTURALLY_ALIGNABLE
REAGGREGATION_REQUIRED
AMBIGUOUS_PATH
INSUFFICIENT_EVIDENCE
INCOMPATIBLE
```

Exact state plus exact ordered factor-use identities is `EXACTLY_ALIGNED`.
Different identities with mutual dependency proof are
`STRUCTURALLY_ALIGNABLE`. A strict finer/coarser result, or incomparable facts
with an actual common coarser candidate, is `REAGGREGATION_REQUIRED`.
Incomparable concrete facts without an actual common candidate are
`INCOMPATIBLE`.

Multiplicity risk is a separate optional axis:

```text
FANOUT_RISK
CROSS_FACT_MULTIPLICATION
```

The final region being strictly finer than a fact establishes structural
`FANOUT_RISK` and retains the causative later JOIN/factor additions. It does
not prove that runtime data contains duplicate rows.

A chasm requires at least two co-present, mutually incomparable fact
localities that both determine the same retained actual common coarser grain,
while the final region retains their independent factor uses. The candidate
retains all participating localities, introduction JOIN/path occurrences,
contextual factor sets, common determinations, and pairwise directional
evidence. A qualifying pair receives `CROSS_FACT_MULTIPLICATION`; this states
logical multiplicative possibility, not observed row counts.

`AGGREGATE_ALGEBRA_REQUIRED` is an independent later requirement whenever
reaggregation or either multiplicity risk is present. Aggregate function text
is metadata only. Slice 12 contains no SUM/MIN/MAX/COUNT/AVG/DISTINCT safety
rules, no reaggregation, no symmetric aggregate, and no automatic fanout
repair.

## Pair Scope And Non-Concrete Regions

Pairwise alignments are materialized only for distinct facts sharing one home
aggregate context or fact localities co-present in one concrete JOIN region,
using deterministic locality order and `i < j`. A typed on-demand query handles
two exact localities; unrelated localities return `INCOMPATIBLE` without a
global pair table.

Every non-concrete Slice-11 region produces one typed subject with all exact
blockers and no partial concrete locality prefix. An identifiable
aggregate-bearing target plus relationship/path ambiguity is `AMBIGUOUS_PATH`;
other missing or blocked evidence is `INSUFFICIENT_EVIDENCE`. Independent
concrete regions remain analyzable.

## Determinism, Complexity, And Frozen Boundaries

Construction uses direct indexes for context facts, home outputs,
introduction uses, region localities, local factor positions, and actual
candidate buckets. Complexity is linear construction plus pairwise work only
inside useful actual contexts. Python `int` masks remain arbitrary width.

Slice 12 adds no grammar/AST, aggregate semantics, joined scalar namespace,
JOIN unary tail, Script IR/SQL, public schema, CLI/JSON/Project Explain,
optimizer, catalog evidence, package/workflow/dependency/version behavior, or
Slice-13 verifier/oracle behavior.

## Reader Closure And Assurance

The complete fixed changed-path closure is:

```text
docs/roadmap.md
docs/spec/phase62-slice12-per-aggregate-fact-locality-chasm-detection-multi-fact-alignment-v1.md
docs/status.md
src/pietto/_project/project_multifact.py
tests/test_active_phase_lifecycle.py
tests/test_phase62_slice1_relationship_join_keys_fd_grain_fanout_multifact_architecture_source_audit_route_lock.py
tests/test_phase62_slice12_per_aggregate_fact_locality_chasm_detection_multi_fact_alignment.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

This is `A3/M5/D0`. A ninth path is `READER_CLOSURE_DRIFT`.

Focused assurance covers complete fact occurrence construction; non-aggregate,
window, and JOIN-deferred exclusions; exact stage/home mapping; same-context
facts; repeated, self/role, and intermediate path localities; GLOBAL; exact and
mutual-dependency alignment; strict grain ordering; chain-versus-chasm;
fanout/cross-fact risk; actual UNIQUE and AMBIGUOUS common-grain buckets;
72-factor masks; unrelated queries; ambiguous paths; missing evidence; and
detached-carrier rejection. Tests remain xdist-compatible with serial fallback.

## Review, Publication, And Handoff

Slice 12 permits at most one bounded repair batch after the complete finding
set is frozen. A second root/repair, additional production owner, joined
aggregate semantics, automatic reaggregation, or aggregate algebra is
terminal.

The complete review froze and repaired the single root
`MULTIFACT_ANALYSIS_RESCANS_RETAINED_AUTHORITY_INSTEAD_OF_REUSING_TYPED_INDEXES`.
The repair compiles snapshot-local base/JOIN property, fact-locality,
candidate-reach, candidate-dominance, and candidate-to-fact indexes once;
reuses the existing grain-direction enum; and removes one-call/test-only
wrappers without changing classification semantics.

```text
Slice 12 repair batches: 1/1
```

After fresh complete rereview, start exactly once:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Gate 3 uses one ordinary commit, one fast-forward push, and the unique natural
exact-head `push/main` run without dispatch, rerun, or cancellation.

```text
Add Phase 62 multi-fact alignment analysis
```

```text
PASS — PHASE62_SLICE12_PER_AGGREGATE_FACT_LOCALITY_CHASM_DETECTION_MULTI_FACT_ALIGNMENT_END_TO_END
```

Successful natural exact-head CI completes/publishes Slices 1–12 and leaves:

```text
Slice 13 = NEXT / NOT IMPLEMENTED
```

Do not begin Slice 13.
