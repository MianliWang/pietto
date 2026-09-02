# Phase 62 Slice 13 Integrity Verifier, Analysis Invalidation, And Bounded BAG/NULL Semantic Oracle v1

## Starting Authority

Slice 13 starts from published commit
`47ee4caccc0686ca609791fb76447a1d1d634069`, tree
`4d5e1e42f22ec87bbf439982b68a486d32201de0`, and natural exact-head
`push/main` CI `33574693434`, attempt 1, success.

Phase 62 is active. Slices 1–12 are completed/published, Slice 13 is the sole
current publication candidate, and Slices 14–16 are not started.

## Exact Owners And Separation

Slice 13 adds exactly two private owners, both with `__all__ = ()`:

```text
src/pietto/_project/project_phase62_verification.py
src/pietto/_project/project_bag_null_oracle.py
```

```text
ProjectMultiFactAnalysis
-> independent Phase-62 verification
-> fresh detachable analyses
-> explicit invalidation
```

```text
bounded finite BAG inputs
+ exact INNER/LEFT equality specification
-> pure reference BAG/NULL oracle
```

```text
constructor validity != independent verification
verification result != semantic authority
verification != oracle proof

bounded oracle != verifier backend
bounded oracle != complete theorem prover
bounded oracle != runtime evaluator
bounded oracle != production engine
bounded oracle != SMT/proof certificate
```

The verifier neither imports nor invokes the oracle. The oracle imports only
the Python standard library and has no Project IR, relationship, multi-fact,
semantic-model, SQL/backend, parser, or execution adapter.

## Independent Phase-62 Verification

`verify_project_phase62(...)` accepts one exact `ProjectMultiFactAnalysis` and
freshly invokes the existing `verify_project_ir_stage(root.evaluation)`.
Invalid base Project IR makes the Phase-62 result invalid. Previous analysis
bundles, constructors, hashes, names, and cached topology are never authority.

The closed result status is:

```text
VERIFIED
INVALID
```

The fixed issue-pass order is:

```text
ROOT_COHERENCE
BASE_PROJECT_IR
JOIN_SCOPE_COORDINATE
JOIN_STRUCTURAL_ENDPOINT
JOIN_REGION_COMPLETENESS
JOIN_CONDITION_MAPPING
JOIN_EFFECT_NULLING
JOIN_PROPERTY_TRANSFER
JOIN_KEY_FD_GRAIN
MULTIFACT_CATALOG
MULTIFACT_LOCALITY
MULTIFACT_ALIGNMENT
CHASM_RISK
COMBINED_ACTUAL_USE_CYCLE
```

Each issue retains an exact Project ref or aggregate-fact identity when one is
available. `VERIFIED` has zero issues; `INVALID` has a non-empty canonical
tuple.

JOIN verification independently replays same-snapshot dense coordinates;
binary slot/use endpoints; accumulated-left and authored path-step order;
all-or-none region construction; condition/field mapping; INNER/LEFT effects;
nulling provenance and effective nullability; complete `NULL_EXTENSION`;
output fields/value classes; candidate-key and value-FD transfer; compiled FD
index; grain factor-use/nulling identity; directional dependencies; and the
exact grain witness. It never calls `build_project_ir_join_region(...)`.

Multi-fact verification independently replays the complete aggregate-result
catalog, stage/home mapping, home/JOIN locality ledger, carried fields,
contextual factors, grain determinations, actual candidate sets, complete
common-grain buckets, pair order/classification, fanout exposure, chasm
participants, multiplication risk, aggregate-algebra requirement, indexes,
and non-concrete blocker propagation. It never calls
`build_project_multifact_analysis(...)` and adds no aggregate-function safety
semantics.

The combined actual-use graph contains all base Project IR uses plus JOIN-input
uses. A fresh Kahn traversal proves acyclicity. Any cycle is invalid and never
recursion; no alternate JOIN order or optimization is produced.

## Fresh Detachable Analyses

Only a `VERIFIED` result may construct `ProjectPhase62AnalysisBundle`. Every
call rederives all five products from current objects:

```text
COMBINED_REVERSE_USE_INDEX
COMBINED_TOPOLOGICAL_ORDER
NULLING_PROVENANCE_INDEX
FACT_LOCALITY_INDEX
MULTIFACT_ALIGNMENT_INDEX
```

The reverse-use index covers every base/JOIN output once and retains exact
direct uses in combined structural order. Topology uses Project ref position
only as a tie-breaker among simultaneously ready nodes. Nulling entries use
exact output ref plus field position, never names. Fact-locality entries map
each exact fact identity to home then JOIN localities in authority order. The
alignment index retains every exact alignment, chasm, and risk bucket without
a winner. Bundle construction independently rederives and rejects same-scope
stale carriers. There is no mutable or process-global cache.

## Explicit Analysis Invalidation

Changed domains are non-empty, unique, typed, and enum-ordered:

```text
BASE_TOPOLOGY
BASE_SEMANTICS
RELATIONSHIP_USE_AUTHORITY
JOIN_TOPOLOGY
JOIN_SEMANTICS
JOIN_PROPERTIES
MULTIFACT_LOCALITY
MULTIFACT_ALIGNMENT
ESTIMATES
```

`BASE_TOPOLOGY` or `JOIN_TOPOLOGY` invalidates all five analyses.
`RELATIONSHIP_USE_AUTHORITY`, `JOIN_SEMANTICS`, or `JOIN_PROPERTIES` preserves
only the two combined-topology products. `BASE_SEMANTICS` or
`MULTIFACT_LOCALITY` invalidates fact-locality and multi-fact alignment.
`MULTIFACT_ALIGNMENT` invalidates only its own index. `ESTIMATES` alone
preserves all five. Multiple domains take the conservative union.

Verification is never preservable:

```text
verification = RERUN_REQUIRED
```

No transform or rewrite engine is added.

## Pure Bounded BAG/NULL Oracle

The immutable reference model has exact truth, INNER/LEFT kind,
NULL/BOOL/INT/TEXT scalar, ordered row, positive-multiplicity bag entry,
ordered distinct-row finite bag, equality correspondence, and JOIN
specification carriers. Small hard bounds apply to input row width, distinct
input rows, input multiplicity, and correspondence count. These are assurance
scope, not Pietto language limits.

Exact non-NULL equality requires the same scalar kind and value. Any NULL
operand yields `UNKNOWN`; incompatible kinds or unequal values yield `FALSE`.
For conjunction, `FALSE` dominates `UNKNOWN`; otherwise any `UNKNOWN` yields
`UNKNOWN`; only all-TRUE matches.

INNER contributes:

```text
left multiplicity * right multiplicity
```

for each TRUE pair. LEFT has identical matched contributions and emits each
unmatched left tuple null-extended by the right width with exactly its left
multiplicity. FALSE/UNKNOWN never match. Multiplicities are accumulated as a
BAG and never collapsed to SET. Output iteration follows first production,
while assurance compares row-to-multiplicity content.

The oracle adds no expression evaluator, WHERE/GROUP/aggregate/window,
RIGHT/FULL/SEMI/ANTI/MARK/SINGLE JOIN, null-safe equality, parser/SQL/backend,
catalog, SAT/SMT, general proof, or unbounded enumeration.

## Reader Closure And Assurance

The complete changed-path closure is:

```text
docs/roadmap.md
docs/spec/phase62-slice13-integrity-verifier-analysis-invalidation-bounded-bag-null-semantic-oracle-v1.md
docs/status.md
src/pietto/_project/project_phase62_verification.py
src/pietto/_project/project_bag_null_oracle.py
tests/test_active_phase_lifecycle.py
tests/test_phase62_slice1_relationship_join_keys_fd_grain_fanout_multifact_architecture_source_audit_route_lock.py
tests/test_phase62_slice13_integrity_verifier_analysis_invalidation_bounded_bag_null_semantic_oracle.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

This is `A4/M5/D0`. A tenth path is `READER_CLOSURE_DRIFT`.

Focused assurance uses real Slice-11/12 roots and independent unsafe-carrier
corruption for foreign/gapped refs, detached/wrong inputs, accumulated-left,
partial regions, condition, nulling/nullability, property/key/FD/grain,
fact catalog/locality/contextual grain, common-candidate winner loss, chasm
participants, multiplication risk, and combined cycles. It proves fixed issue
order, VERIFIED-only bundles, stale rejection, exact invalidation, verifier/
oracle separation, and hash-seed/cwd/operation-order stability.

Oracle assurance covers NULL/TRUE/FALSE conjunctions, BAG multiplication,
SET-dedup counterexample, matched/unmatched LEFT behavior, UNKNOWN-only
unmatched rows, left/right scaling, input order, INNER swap permutation,
non-commutative LEFT, and hard input bounds. Passing bounded cases proves no
general rewrite theorem. Tests remain xdist-compatible with serial fallback.

## Frozen Boundaries

Slice 13 changes no Slice 2–12 production owner and adds no grammar/AST,
joined scalar namespace, aggregate-over-JOIN semantics, reaggregation,
aggregate algebra, Script IR/SQL, public schema, CLI/JSON/Project Explain,
optimizer/rewrite, persistent cache, recursion, package, dependency, workflow,
version, generated, fixture, or golden behavior.

Slice 14 owns private inspection, winner-free query, and pure canonical
boundary. Slice 15 owns real authored E2E/differential/metamorphic JOIN
assurance.

## Review, Publication, And Handoff

Slice 13 allows at most one bounded repair batch after the complete finding set
is frozen. A second root/repair, additional production owner, verifier/oracle
coupling, general evaluator, optimizer, or Slice-14 work is terminal.

The complete review froze and repaired the single root
`INDEPENDENT_VERIFIER_REPLAY_DOES_NOT_CLOSE_EXACT_IDENTITY_AND_INDEX_EVIDENCE`.
The repair makes endpoint/value-class replay identity-exact; closes
non-concrete path classification, actual-candidate authorities and fact
buckets, contextual comparison roots, and complete chasm evidence; and makes
corrupt catalog indexes return typed INVALID instead of escaping verification.

```text
Slice 13 repair batches: 1/1
```

After fresh complete rereview, start exactly once:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Gate 3 uses one ordinary commit, one fast-forward push, and the unique natural
exact-head `push/main` run without dispatch, rerun, or cancellation.

```text
Add Phase 62 JOIN verification and BAG oracle
```

```text
PASS — PHASE62_SLICE13_INTEGRITY_VERIFIER_ANALYSIS_INVALIDATION_BOUNDED_BAG_NULL_SEMANTIC_ORACLE_END_TO_END
```

Successful natural exact-head CI completes/publishes Slices 1–13 and leaves:

```text
Phase 62 Slice 14 = NEXT / NOT IMPLEMENTED
```

Do not begin Slice 14.
