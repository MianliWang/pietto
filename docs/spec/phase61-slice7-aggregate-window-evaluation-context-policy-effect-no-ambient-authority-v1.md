# Phase 61 Slice 7 Aggregate And Window Evaluation Context v1

## Answer And Exact Owner

Slice 7 adds one private, pure projection over the unchanged Slice 6
`ProjectIRProjectPlan`:

```text
ProjectIRProjectPlan
-> exact aggregate evaluation contexts
-> exact window operator and result evaluation contexts
```

The exact owner is:

```text
src/pietto/_project/project_ir_evaluation_context.py
```

An evaluation context records where evaluation occurs and which exact existing
semantic, row, policy, effect, and closed-binding objects authorize it.

```text
evaluation context != evaluator
evaluation context != optimizer analysis
evaluation context != physical execution context
```

The bounded continuation also repairs one predecessor formation defect in
`project_ir_construction.py`; it does not add a second Slice 7 owner.

## Starting Authority

| Fact | Value |
| --- | --- |
| Branch | `main` |
| HEAD | `21b478569029dbae43aa6cbddecfa0c3709abe5d` |
| Tree | `351a5ee5dfc709c9f46a7fecd4112f05a01c9c53` |
| Parent | `b9c9e38f809f911eb429e7284d377c2c205e548b` |
| Subject | `Add Phase 61 Project IR composition DAG` |
| Natural exact-head CI | `33340163436`, `push`, attempt `1`, successful |
| Divergence | `0/0` |
| Version | `0.1.0` |

That publication establishes Slices 1-6 as completed and Slice 7 as the only
next owner. The clean Python 3.13 focused baseline was `147 passed`.

The initial Slice 7 candidate retained two untracked files and passed Ruff and
Pyright, but its real Project-plan test stopped with eight setup failures. The
exact predecessor defect was frozen as:

```text
GLOBAL_AGGREGATE_LOCAL_GRAIN_OVERPUBLICATION
```

The continuation preserved that candidate, authorized two additional reader
paths, and consumed exactly one root-cause repair batch.

## Frozen Reader And Changed-path Closure

Fixed-point closure covers the Slice 3 property carrier and effect objects,
Slice 4 operator/property-transfer matrix, Slice 5 canonical construction,
Slice 6 Project-plan composition, semantic aggregate/window/let/named-window
facts, lifecycle readers, product-test discovery, package discovery, and exact
Python source/test counters.

The frozen allowlist is exactly:

```text
docs/roadmap.md
docs/spec/phase61-slice7-aggregate-window-evaluation-context-policy-effect-no-ambient-authority-v1.md
docs/status.md
src/pietto/_project/project_ir_construction.py
src/pietto/_project/project_ir_evaluation_context.py
tests/test_active_phase_lifecycle.py
tests/test_phase61_slice5_canonical_single_relation_project_ir_construction.py
tests/test_phase61_slice7_aggregate_window_evaluation_context_policy_effect_no_ambient_authority.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

This is `A3/M6/D0`. `tests/test_active_phase_lifecycle.py` remains the sole
direct mutable status/roadmap reader. Package and validation discovery include
the new private module and test without another manifest. A tenth changed path
is `READER_CLOSURE_DRIFT`.

## Aggregate Evaluation Context

Every concrete fragment containing exactly one `GROUP_AGGREGATE` produces
exactly one `ProjectIRAggregateEvaluationContext` in Project fragment and
operator order. It retains by object identity:

```text
concrete fragment and GROUP_AGGREGATE occurrence
incoming ProjectIROperatorFlowUseOccurrence and exact input row output
exact GROUP_AGGREGATE BASE_RESULT row output
ProjectModuleRelationSemanticFacts
aggregate_grouped_clause_readiness
group_key_occurrences and aggregate_result_facts
retained let-scope authority
input/result closed-binding and effect objects
```

The input is resolved through the exact flow use, never tuple adjacency. The
result row must retain the semantic `BASE_RESULT` checkpoint.

The predecessor boundary is:

```text
global aggregate group_keys=()
-> valid aggregate evaluation context
-> no positive LOCAL_GRAIN_EVIDENCE

grouped aggregate group_keys!=()
-> positive LOCAL_GRAIN_EVIDENCE permitted
```

`LOCAL_GRAIN_EVIDENCE` continues to mean non-empty exact group-key evidence.
The Slice 5 builder now creates it for `GROUP_AGGREGATE` only when the exact
retained semantic group-key tuple is non-empty. Downstream operators preserve
the slot only when their exact predecessor already has it. The carrier still
rejects empty evidence.

```text
global aggregate != grouped aggregate with an empty synthetic key list
aggregate evaluation context != LOCAL_GRAIN_EVIDENCE
```

No aggregate policy, global-grain descriptor, aggregation state, partial
aggregation, or reaggregation model is introduced.

## Window Operator And Result Contexts

Every concrete `WINDOW_EVALUATION` produces exactly one
`ProjectIRWindowOperatorEvaluationContext`. It retains the exact fragment,
operator, incoming flow, stream input row, semantic `BASE_RESULT` checkpoint,
window result row, relation facts, let scope, named-window authority,
closed-binding properties, and row effects.

Freeze:

```text
stream input row != semantic BASE_RESULT row
```

Equality is retained when their exact semantic state objects match; inequality
is retained explicitly without inserting a logical operator. The checkpoint is
semantic authority and allocates no Project IR ref.

Every concrete `ProjectModuleWindowOutputFact` then produces one
`ProjectIRWindowResultEvaluationContext` in exact semantic output order. It
binds the exact `WindowResultProjectFact`, stage-local
`ProjectIRStageScalarFieldOutput`, existing
`ProjectIRProvidedEvaluationPolicy`, and existing `ProjectIREffectEvidence`.
Matching uses retained occurrence, ordinal, producer, and evidence identity,
never a name-only lookup.

```text
window stage value != final projection export
```

## Policy Effect And Closed-binding Preservation

Window policy is the exact Slice 5 property object. It is not recomputed from a
function name and is not interpreted as effect purity, evaluation count,
ordering, frame membership, or physical strategy.

```text
window policy != effect classification
```

Aggregate and window contexts reuse exact Slice 5 effect objects. The current
four effect axes remain `UNKNOWN`; logical category, frame policy, and DAG
fanout provide no stronger evidence.

```text
logical DAG sharing != evaluate once
```

Every retained evaluation row reuses its exact
`ProjectIRProvidedClosedBindings`; current free outer bindings remain `()`.
Let, relation, expression, field, and named-window names are not resolved in
Slice 7. No ambient current relation, project, cwd, environment, registry,
scope stack, or global mutable state supplies authority.

## Completeness Uniqueness And Zero Mutation

`ProjectIREvaluationContextStage` retains the exact Project plan plus canonical
aggregate, window-operator, and window-result tuples.

Canonical order is:

```text
Project plan fragment order
-> operator order
-> semantic window-result occurrence order
```

Formation fails closed for missing, duplicate, foreign, or wrongly bound
contexts and for rebuilt equivalent semantic, policy, or effect objects. Every
retained concrete aggregate/window operator and window fact has exactly one
context. Non-concrete fragments have zero contexts.

Formation allocates no node, output, slot, or use ref. The Project structural
DAG and starting/ending allocation are reused object-for-object.

## Determinism Immutability And No-ambient Authority

All carriers are frozen, slotted, keyword-only, and private. Collections are
exact tuples in retained authority order. Formation performs no name/hash sort,
deduplication, winner selection, semantic re-analysis, I/O, or mutation.

The same Project plan produces the same context coordinates under different
hash seeds and unrelated cwd values. Paths, repr/object addresses, environment,
UUIDs, randomness, and process-global state never become identity.

The owner exports nothing through `__all__` and remains absent from Pietto's
public package, `pietto._project`, CLI, SQL, Project Explain, and script
`RelationIR` surfaces.

## Focused Assurance

Tests use real parsed/analyzed Project facts and the real Slice 5 and Slice 6
builders. They prove:

```text
global aggregate is CONCRETE with group_keys=() and non-empty aggregate results
global aggregate builds and publishes no LOCAL_GRAIN_EVIDENCE
grouped aggregate publishes exact positive local-grain evidence
preserving grouped downstream operators retain that exact positive evidence
every provided property has exactly one transfer proof
aggregate-only, grouped, where->group, group->satisfying, and full paths
one context per aggregate and window operator
one result context per concrete window output
multiple inline windows and named-window use
aggregate let authority retained through the supported aggregate-let form
exact aggregate and window flow predecessors
explicit semantic BASE_RESULT authority with stream/base equality or inequality
exact stage scalar, policy, effect, and distinct final export
unknown effects remain unknown and no aggregate policy is invented
rebuilt equivalent semantic/policy/effect objects are rejected
non-concrete fragments produce zero contexts
Project-plan structure and allocation are unchanged
hash-seed/cwd independence and public/SQL/script RelationIR zero-delta
```

The root-cause checks passed as `2 passed`, the complete Slice 5 canonical
builder file passed as `18 passed`, and the Slice 7 implementation checks passed
as `8 passed, 1 deselected` before the controlling document existed. Tests use
pytest-owned paths and isolated subprocesses and remain xdist/serial compatible.

## Integration Boundaries And Non-goals

Slice 7 adds no expression execution, row aggregation, frame materialization,
aggregate/window algebra, aggregate-as-window admission, physical evaluation
count, `GlobalGrain`, `SingleGroupGrain`, keys/FDs/fanout, correlation, JOIN,
optimizer/memo/rewrite, general verifier, invalidation, inspection,
serialization, parser/AST/grammar, diagnostic, SQL, CLI, JSON, public schema,
Project Explain field, backend change, version change, tag, Release, signing,
or attestation.

The frozen eight-stage operator algebra, Slice 6 composition, and
`ProjectIRProvidedLocalGrainEvidence` meaning are unchanged. Existing
unsupported global-aggregate satisfying/window combinations are not admitted
by the predecessor repair.

## Slice 8 Handoff

After successful natural exact-head CI:

```text
Phase 61 remains exactly 12 slices
Slices 1-7 = COMPLETED
Slice 8 = NEXT / UNSTARTED
```

The only next owner is:

```text
Phase 61 Slice 8 — Integrity, Verifier, Analysis Invalidation, Semantic Equivalence, And Optimizer/Recursion Readiness
```

Slice 7 implements none of that owner.

## Gate Lifecycle And Publication

The explicit reader-closure continuation consumes `repair batches = 1` for
`GLOBAL_AGGREGATE_LOCAL_GRAIN_OVERPUBLICATION`. No second repair batch is
available. Complete review and fresh rereview precede exactly one authoritative
validator start:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Local package smoke follows because a packaged private module is added.
Generated and golden inputs do not change; natural CI still checks them.

Gate 3 rebinds the predecessor, stages exactly the sealed nine-path tree, makes
one ordinary commit, performs one fast-forward push, and observes the unique
natural exact-head CI without dispatch, cancel, or rerun.

The exact commit subject is:

```text
Add Phase 61 Project IR evaluation contexts
```

The published PASS title is:

```text
PASS — PHASE61_SLICE7_AGGREGATE_WINDOW_EVALUATION_CONTEXT_POLICY_EFFECT_NO_AMBIENT_AUTHORITY_END_TO_END
```

Successful natural exact-head CI completes Slice 7 without a status-only
follow-up commit. Slice 8 remains next / unstarted.
