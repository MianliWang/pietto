# Phase 61 Slice 8 Project IR Verification And Analysis v1

## Answer And Exact Owner

Slice 8 adds one private independent integrity and derived-analysis boundary
over the exact Slice 7 evaluation-context stage:

```text
ProjectIREvaluationContextStage
-> independent typed verification
-> fresh detachable analyses
-> explicit invalidation and rewrite-readiness assessment
```

The exact owner is:

```text
src/pietto/_project/project_ir_verification.py
```

Freeze:

```text
constructor validity != independent verification
verification result != semantic authority
```

The owner implements no optimizer, pass manager, rewrite engine, memo, target
plan, recursive relation, fixpoint, inspection, serialization, SQL, or public
API.

## Starting Authority

| Fact | Value |
| --- | --- |
| Branch | `main` |
| HEAD | `455629a9edc93622180788ff4cba8b76776c4e9f` |
| Tree | `6b9bfe44d00de3de112214515f3682131696967a` |
| Parent | `21b478569029dbae43aa6cbddecfa0c3709abe5d` |
| Subject | `Add Phase 61 Project IR evaluation contexts` |
| Natural exact-head CI | `33342737233`, `push`, attempt `1`, successful |
| Divergence | `0/0` |
| Version | `0.1.0` |

That publication establishes Slices 1-7 as completed and Slice 8 as the only
next owner. The clean pre-write Project IR/lifecycle focused baseline was
`123 passed`.

The live feasibility proof used real parsed/analyzed Projects and the real
Slice 6 and Slice 7 builders. One representative stage retained 8 fragments,
24 nodes, 40 outputs, 23 slots and uses, 6 cross-relation edges, 5 aggregate
contexts, 2 window contexts, and 3 window-result contexts.

## Frozen Reader And Changed-path Closure

Fixed-point closure covers all published Slice 1-7 and both Slice 5
prerequisite contracts; structural, property, operator, fragment, Project-plan,
and evaluation-context carriers; package and product-test discovery; lifecycle
readers; exact Python source/test counters; and readers of those readers.

The frozen allowlist is exactly:

```text
docs/roadmap.md
docs/spec/phase61-slice8-integrity-verifier-analysis-invalidation-semantic-equivalence-optimizer-recursion-readiness-v1.md
docs/status.md
src/pietto/_project/project_ir_verification.py
tests/test_active_phase_lifecycle.py
tests/test_phase61_slice8_integrity_verifier_analysis_invalidation_semantic_equivalence_optimizer_recursion_readiness.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

This is `A3/M4/D0`. Package discovery and Phase 61 product-test discovery are
dynamic. `tests/test_active_phase_lifecycle.py` remains the sole direct mutable
status/roadmap reader. An eighth changed path is `READER_CLOSURE_DRIFT`.

## Independent Verification Passes

`verify_project_ir_stage` retains the exact supplied
`ProjectIREvaluationContextStage` and derives every check fresh. It does not
call Slice 4's operator-kind derivation or Slice 6's acyclicity helper, and it
does not infer validity from any `__post_init__` having succeeded.

The fixed pass order independently checks:

```text
snapshot scope and ref-domain coordinates
node/output/use/input-slot endpoints and one-use-per-slot attachment
canonical semantic fragment and exact Project object composition
operator legality, row checkpoints, and canonical stage order
intra-relation flow adjacency
cross-relation exact resolution and endpoints
provided/required row compatibility
property attachment and independent transfer-matrix consistency
one exact unknown effect per output
non-concrete zero-IR terminals
aggregate/window/result evaluation-context completeness and bindings
fresh actual-use acyclicity
exact attribution dependency and provenance reachability
```

Checks use object identity for retained occurrences and authority objects.
Names, tuple adjacency, hashes, cached topology, previous verification, and
constructor exception strings are not authority.

## Typed Verification Result

`ProjectIRVerificationResult` has exactly two statuses:

```text
VERIFIED
INVALID
```

Issues use `ProjectIRVerificationIssueKind` plus an optional typed plan-node,
output, use, or slot ref. No public diagnostic is produced. Issue order is the
fixed pass order followed by canonical occurrence order within each pass.

A `VERIFIED` result has no issues; an `INVALID` result has a non-empty typed
issue tuple. The result retains the exact checked Slice 7 stage by object
identity and never becomes semantic authority.

## Fresh Derived Analyses

Only a `VERIFIED` result may form `ProjectIRAnalysisBundle`. Every call
recomputes all products from exact current objects:

```text
REVERSE_USE_INDEX
TOPOLOGICAL_ORDER
REACHABILITY
SEMANTIC_EQUIVALENCE_CANDIDATES
```

The complete reverse-use index has one entry per output and retains every exact
direct use in structural use order. Topological order is a fresh Kahn result;
ref order breaks ties only among simultaneously ready nodes, so
allocation-backward dependencies remain valid. Reachability is transitive and
derived solely from direct uses. Disconnected components remain deterministic.

Bundle formation rederives reverse uses, topology, reachability, and semantic
pair assessments before accepting supplied analysis carriers. Same snapshot
scope alone cannot validate stale analysis.

Derived analyses remain detachable products. They never become occurrence,
resolution, topology, provenance, or semantic identity.

## Analysis Invalidation And Preservation

`ProjectIRChangeDomain` distinguishes:

```text
TOPOLOGY
OPERATOR_SEMANTICS
OUTPUT_SEMANTICS
PROPERTIES
EFFECTS
EVALUATION_CONTEXT
PROVENANCE
ESTIMATES
```

Changed-domain declarations must be non-empty, unique, typed, and canonical.
There is no implicit preserve-all declaration.

The dependency matrix is:

```text
TOPOLOGY
-> invalidate reverse-use, topological-order, reachability,
   semantic-equivalence candidates

OPERATOR_SEMANTICS / OUTPUT_SEMANTICS / PROPERTIES / EFFECTS /
EVALUATION_CONTEXT / PROVENANCE
-> invalidate semantic-equivalence candidates

ESTIMATES only
-> preserve all four current analyses
```

`ProjectIRAnalysisInvalidation` derives both invalidated and preserved tuples in
analysis-kind order. Verification is absent from the preservable analysis enum:

```text
verification itself is never preservable
verification = RERUN_REQUIRED
```

No transform or mutable analysis cache is implemented.

## Semantic Equivalence And Rewrite Readiness

Concrete fragments are assessed in canonical pair order while remaining exact
distinct occurrences. `ProjectIRSemanticEquivalenceStatus` distinguishes:

```text
KNOWN_INCOMPATIBLE
CANDIDATE_NOT_DISPROVEN
REWRITE_EQUIVALENCE_PROVEN
```

Every pair retains an explicit `EVIDENCED`, `INCOMPATIBLE`, or `NOT_PROVEN`
assessment for:

```text
schema/types
values
BAG multiplicity
null/empty behavior
cardinality guarantees
ordering
effects/error behavior
evaluation count
policy context
required capabilities
provenance traceability
```

Estimates are excluded. Matching schemas, operator families, or output names do
not prove values. Current unknown effect/evaluation evidence remains
`NOT_PROVEN`. Distinct occurrences have no rewrite witness, so provenance
traceability remains `NOT_PROVEN`.

Known schema, operator, cardinality, ordering, policy, BAG, or effect conflict
prevents candidacy. Invalid BAG/effect corruption is rejected by verification
before equivalence analysis.

`ProjectIRRewriteReadiness` is pure assessment. A nontrivial pair is admissible
only when every dimension is `EVIDENCED` and equivalence is proven. Current
candidates are therefore blocked.

```text
semantic-equivalence candidate != rewrite proof != rewrite
```

No source, node, output, use, slot, provenance, or lineage occurrence is merged
or allocated.

## Optimizer And Recursion Readiness Boundaries

Freeze:

```text
CanonicalProjectIR != OptimizationMemo != ChosenTargetPlan
```

Verified canonical IR and detachable analyses may be future optimizer inputs,
but Slice 8 adds no rules, memo groups, cost, search, physical alternatives,
target capability selection, or pass scheduling.

Ordinary current Project IR remains acyclic. Any actual-use cycle is `INVALID`;
reachability or cycle detection grants no recursion semantics.

```text
future recursion = explicit scoped fixpoint/recursive region
```

A later owner must define seed, iterative body, recursive binder, BAG/SET mode,
row compatibility, progress/termination, ordering, and cycle handling. Slice 8
adds no `Fixpoint`, `RecursiveRelation`, `WorkingTable`, `DeltaRelation`, or
`SemiNaive` production type.

## Determinism Immutability And Privacy

All result, issue, analysis, equivalence, readiness, and invalidation carriers
are frozen, slotted, keyword-only dataclasses. Collections are exact tuples in
canonical Project/ref/pass order.

Verification and analysis use no cwd, environment, registry, singleton, UUID,
randomness, content hash, object address, ambient current project, mutable
cache, name sort, nearest lookup, or winner selection. Hash seed and unrelated
cwd do not alter statuses or Project coordinates.

The owner exports nothing through `__all__` and remains absent from public
Pietto, `pietto._project`, CLI, SQL, Project Explain, and script `RelationIR`.

## Focused Assurance

Positive tests use real parsed/analyzed Projects and the real Slice 6/7
builders. Controlled corruption uses copied frozen carriers plus test-only
`object.__setattr__`; no production constructor is weakened.

Assurance covers:

```text
valid Project stages verify with zero issues
foreign snapshot ref and duplicate/gapped coordinates
missing producer output and bad/duplicate slot-use endpoints
wrong operator order and operator-flow adjacency
wrong cross-relation endpoint and detached provenance
broken row compatibility
missing property and transfer; wrong effect attachment
missing and duplicate evaluation contexts
non-concrete terminal containing IR
actual-use cycle rejected as invalid, never recursion
fixed issue pass order
fresh complete reverse-use index
allocation-backward topological order
transitive reachability and deterministic disconnected components
same-scope stale analysis rejection
exact topology/semantic/estimate invalidation matrix
distinct matching occurrences remain candidate-only and unmerged
ordering and policy conflicts are incompatible
unknown effects/evaluation/capabilities/provenance block rewrite readiness
invalid BAG/effect evidence stops before equivalence analysis
no optimizer/memo/fixpoint production type
hash-seed/cwd independence
public/SQL/script RelationIR zero-delta
```

The complete Slice 8 file passed as `29 passed` after the bounded review repair.
Tests use pytest-owned paths and isolated subprocesses and remain xdist/serial
compatible.

## Integration Boundaries And Non-goals

Slice 8 changes none of the Slice 2–7 production carriers or constructor laws.
It adds no authored semantics, operator kind, module-semantic identity,
allocation, transform, rewrite witness, optimizer, pass manager, memo, cost,
physical/target plan, recursion/fixpoint semantics, persistent cache identity,
JOIN/grain/fanout, aggregate state, nested/correlated plan, inspection,
serialization, parser/AST/grammar, diagnostic, SQL, CLI, JSON, public schema,
Project Explain field, backend behavior, version change, tag, Release, signing,
or attestation.

The strict empty estimate boundary remains unchanged. Analysis-invalidation
support does not create an estimate producer or mutable analysis cache.

## Slice 9 Handoff

After successful natural exact-head CI:

```text
Phase 61 remains exactly 12 slices
Slices 1-8 = COMPLETED
Slice 9 = NEXT / UNSTARTED
```

The only next owner is:

```text
Phase 61 Slice 9 — Private Inspection, Query, Canonical Serialization, And Pure Boundary
```

Slice 8 implements none of that observation or serialization product.

## Gate Lifecycle And Publication

Gate 2 uses focused tests, Ruff, and Pyright; freezes the complete finding set;
permits at most one same-root repair batch; performs a fresh rereview; and
starts exactly one authoritative validator:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Local package smoke is required because a packaged private module is added.
Generated and golden inputs do not change; natural CI still checks them.

Gate 3 rebinds the predecessor, stages exactly the sealed seven-path tree,
makes one ordinary commit, performs one fast-forward push, and observes the
unique natural exact-head CI without dispatch, cancel, or rerun.

The exact commit subject is:

```text
Add Phase 61 Project IR verifier
```

The published PASS title is:

```text
PASS — PHASE61_SLICE8_INTEGRITY_VERIFIER_ANALYSIS_INVALIDATION_SEMANTIC_EQUIVALENCE_OPTIMIZER_RECURSION_READINESS_END_TO_END
```

Successful natural exact-head CI completes Slice 8 without a status-only
follow-up commit. Slice 9 remains next / unstarted.
