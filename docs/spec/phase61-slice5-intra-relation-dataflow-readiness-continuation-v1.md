# Phase 61 Slice 5 Intra-relation Dataflow Readiness Continuation v1

## Answer And Exact Owner

This unnumbered continuation resolves the second Slice 5 prerequisite blocker:

```text
INTRA_RELATION_PLAN_DATAFLOW_AUTHORITY_MISSING
```

with both observed manifestations:

```text
FINAL_RELATION_SCHEMA_OVERLOADED_AS_ALL_OPERATOR_ROW_SHAPES
SEMANTIC_PROVENANCE_USE_OVERLOADED_AS_ALL_PLAN_DATAFLOW_USES
```

It refines the existing private semantic, structural, property, and logical
owners:

```text
src/pietto/_project/module_semantic_fact_preservation.py
src/pietto/_project/project_ir.py
src/pietto/_project/project_ir_properties.py
src/pietto/_project/project_ir_operators.py
```

It adds no allocator, canonical single-relation builder, automatic operator or
property construction, cross-relation composition, route Slice, SQL, or public
surface. Phase 61 still has exactly 12 Slices and Slice 5 remains unstarted.

Freeze:

```text
final semantic row != intermediate stage row
final semantic field identity != intermediate plan-local value identity
semantic provenance edge != intra-relation operator-flow edge
operator tuple order != dataflow authority
```

## Starting Authority And Observed Blocker

| Fact | Value |
| --- | --- |
| Branch | `main` |
| HEAD | `cce7709f143de4eb5f9989cbbbd804fe08e71d74` |
| Tree | `e8bb0c2c2150d21692ac1da346d88b610eefa4fa` |
| Parent | `6359867c7e9c51d9b59bd23642d7bd2492b24862` |
| Subject | `Add complete Project relation output identities` |
| Natural exact-head CI | `33321099987`, `push`, attempt `1`, successful |
| Divergence | `0/0` |
| Version | `0.1.0` |

The output-identity continuation is the exact published predecessor. Its
successful CI completes the first Slice 5 prerequisite while leaving Slice 5
next / unstarted.

The second pre-write feasibility audit used real parsed/analyzed facts and
observed:

```text
simple projection:
    INPUT = id, amount, category
    FINAL = id, amount

group/window:
    INPUT       = id, amount, category
    BASE_RESULT = category, total
    FINAL       = category, total, ranking
```

The published final-only `ProjectIRRowShape` rejected the exact pre-window
schema, while semantic `from:` provenance rejected an attempted same-relation
operator edge because its target was the actual upstream relation. The clean
pre-write focused baseline was `150 passed` under Python 3.13.

## Frozen Reader And Changed-path Closure

Fixed-point closure covered semantic row construction and private authority
projections; Slice 2–4 production carriers and direct tests; the Slice 1 live
carrier-shape reader; output-attribution authority; lifecycle and readers of
lifecycle; Phase 61 product-test glob readers; exact Python source/test count;
package discovery; and readers of those readers.

The frozen changed-path allowlist is exactly:

```text
docs/roadmap.md
docs/spec/phase61-slice5-intra-relation-dataflow-readiness-continuation-v1.md
docs/status.md
src/pietto/_project/module_semantic_fact_preservation.py
src/pietto/_project/project_ir.py
src/pietto/_project/project_ir_operators.py
src/pietto/_project/project_ir_properties.py
tests/test_active_phase_lifecycle.py
tests/test_phase61_slice1_project_ir_architecture_source_audit_route_lock.py
tests/test_phase61_slice3_project_ir_row_output_properties_effects_estimate_boundary.py
tests/test_phase61_slice4_project_ir_current_logical_operator_algebra_exact_property_transfer.py
tests/test_phase61_slice5_intra_relation_dataflow_readiness_continuation.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

This is `A2/M11/D0`. No new production module is added. Existing product and
workflow readers discover the new test through `test_phase61_slice*.py` and
package smoke discovers the modified private modules dynamically.
`tests/test_active_phase_lifecycle.py` remains the sole direct reader of mutable
`docs/status.md` and `docs/roadmap.md`. A fourteenth changed path is
`READER_CLOSURE_DRIFT`.

## Exact Semantic Row Checkpoints

`ProjectModuleRelationSemanticFacts` now exposes the exact already-computed
semantic row checkpoints without rerunning semantic analysis:

```text
input_state
base_result_state
state  # existing FINAL authority
```

For one concrete derived relation:

```text
input_state
    is the exact resolved upstream ProjectModuleRelationSemanticFacts.state

base_result_state
    is the exact existing direct/grouped/aggregate state before window overlay

state
    remains the existing final relation state after window reduction
```

The existing private pre-window projection and the published
`base_result_state` retain the same exact state object. For a non-window derived
relation, `base_result_state is state` when the existing implementation truly
uses one object. Group/window relations retain the exact aggregate/grouped
finalization state as `base_result_state` and the exact window-reduced state as
`state`.

Source declarations retain only their existing final state:

```text
input_state = None
base_result_state = None
state is base_row_fact.state
```

Non-concrete derived states are retained without inventing a concrete schema.
An unavailable cyclic input checkpoint remains absent rather than selecting a
guessed upstream winner.

The exact current operator mapping is:

```text
Source Relation Input  -> source FINAL
Derived Relation Input -> INPUT
Row Filter             -> INPUT
Group/Aggregate        -> BASE_RESULT
Result Filter          -> BASE_RESULT
Window Evaluation      -> FINAL stage row
Final Projection       -> final semantic row
Relation Ordering      -> final semantic row
Limit                  -> final semantic row
```

Only present operators instantiate a mapping. The eight operator kinds and
their order are unchanged.

## Stage Row And Scalar Value Authority

The final externally visible semantic row remains `ProjectIRRowShape` with
exact `ProjectIRFieldAnchor(ProjectModuleRowFieldIdentity)` fields. Its complete
final-schema and exact-identity invariants are unchanged.

Intermediate row authority is nominally separate:

| Carrier | Exact authority |
| --- | --- |
| `ProjectIRStageRowCheckpoint` | relation anchor, exact semantic fact object, `INPUT` / `BASE_RESULT` / `FINAL`, and its exact existing row state |
| `ProjectIRStageRowField` | exact checkpoint object, field position, and exact `ProjectRowField` object |
| `ProjectIRStageRowShape` | one exact checkpoint plus its complete ordered stage fields |

`ProjectIRStageRowCheckpointKind` has exactly three values and does not copy the
eight logical operator kinds into semantics.

Freeze:

```text
ProjectIRStageRowField != ProjectModuleRowFieldIdentity
stage-row field descriptor != output-value occurrence identity
```

Stage fields have no name-derived, hash-derived, path-derived, SQL-derived, or
final-field identity. Their plan-local value occurrence remains the existing
`ProjectIROutputValueRef` in one snapshot scope.

`ProjectIRStageFieldAnchor` proves only the exact producer node and field
position; owning relation follows from that producer. It is not a
`ProjectIRFieldAnchor`. `ProjectIRStageScalarFieldOutput` composes that seam
with an exact stage row field. `ProjectIRScalarFieldOutput` remains the distinct
final semantic export carrier backed by canonical output-attribution identity.

`ProjectIRRelationRowOutput` accepts the nominal union of an exact stage row
shape or final semantic row shape. It never weakens final semantic row
validation. Every current logical operator owns exactly one relation-row output
with the mapped actual post-operator shape.

Current window evaluation policy may attach to a stage-local scalar without
claiming that the value is already the final semantic field export. Existing
final scalar policy formation remains compatible.

## Semantic Use And Operator-flow Use Separation

`ProjectIRUseOccurrence` retains its existing semantic role, semantic
`source_order`, and exact resolved relation/field provenance laws. Its behavior
is unchanged for actual semantic dependencies.

`ProjectIROperatorFlowUseOccurrence` is a distinct carrier over the same
`ProjectIRUseRef` domain:

```text
exact producer relation-row output
-> exact operator-flow use ref
-> exact consumer input slot
```

It retains no semantic role, source order, resolution, dependency, or
provenance anchor. Formation requires one snapshot scope, one relation owner,
distinct producer and consumer nodes, a relation-row structural output, and
input ordinal `0`.

Freeze:

```text
semantic use != operator-flow use
use-ref structural order != semantic source order
```

`ProjectIRStructuralStage.uses` retains both exact carrier variants in use-ref
coordinate order. Semantic source order is validated only over semantic uses
and is neither fabricated nor normalized for flow uses. One use ref still owns
one occurrence and one input slot still admits at most one selected incoming
use.

## Exact Intra-relation Topology

For every concrete current relation pipeline, the logical stage now requires:

```text
Operator[i] relation-row output
-> exactly one ProjectIROperatorFlowUseOccurrence
-> Operator[i + 1] input slot
```

Every operator has exactly one relation-row output. Every non-first operator
has exactly one intra-relation input slot at ordinal `0`. The first operator has
no flow predecessor. Each flow connects the immediately adjacent operators in
the same relation; missing, duplicate, skipped, rewired, cross-relation, or
extra flow fails closed. A source single-leaf pipeline has no intra-relation
flow use.

The future upstream-to-derived-`Relation Input` edge remains Slice 6-owned. No
placeholder cross-relation edge or upstream Project IR fragment is created.

`ProjectIRLogicalOperatorStage` still validates the exact canonical operator
tuple, but it also proves that tuple order and exact flow topology agree. Tuple
order is presentation/formation order and no longer serves as the only
predecessor authority.

## Property Transfer Through Flow Authority

The published property slots and transfer matrix are unchanged. Every retained
provided property still requires exactly one existing transfer proof.

For `ProjectIRPreservedPropertyTransfer`, the logical stage now resolves the
receiving operator's exact incoming operator-flow use and requires the input
property to belong to that exact relation-row output model. Merely finding the
previous operator in a tuple, or using another property owned by the same node,
is insufficient.

Freeze:

```text
property input producer = exact producer reached through flow authority
presentation order != dataflow edge authority
```

Provided properties, required properties, effects, and estimates remain
separate. Effects stay explicitly unknown and the estimate boundary stays
exactly empty. This continuation adds no new property, estimate, cost, grain,
key, FD, uniqueness, or fanout fact.

## Feasibility Proof

Focused assurance uses real parsed/analyzed Project facts, while directly
constructing only the refined carriers. It invokes no canonical builder.

The simple projection proof retains:

```text
Relation Input: INPUT(id, amount, category)
-> exact flow
Final Projection: FINAL(id, amount)
```

The grouped/window proof retains:

```text
Relation Input: INPUT(id, amount, category)
-> Group/Aggregate: BASE_RESULT(category, total)
-> Window Evaluation: FINAL stage row(category, total, ranking)
-> Final Projection: final semantic row(category, total, ranking)
```

The full eight-stage proof has eight relation-row outputs and seven exact flow
uses. Regression assurance additionally proves:

```text
no final-schema borrowing for Relation Input or Group/Aggregate
no ProjectModuleRowFieldIdentity on stage fields
canonical attribution identities survive on final exposed fields
stage scalar != final scalar export
semantic use still requires exact provenance
operator-flow use has no fabricated semantic evidence/source order
missing/skipped/rewired/cross-relation flow fails closed
tuple/flow disagreement fails closed
property preservation follows the exact flow predecessor
source leaf has zero flow uses
hash-seed/cwd independence
SQL/CLI/public/RelationIR zero-delta
```

Tests use pytest-owned temporary paths and isolated subprocesses and remain
xdist/serial compatible.

## Determinism Immutability And Privacy

All new carriers are frozen, slotted, and keyword-only. Exact collections are
tuples and supplied coordinates are validated rather than sorted, deduplicated,
or winner-selected.

Formation uses no registry, singleton, global counter, UUID, random value, cwd,
hash/content/path identity, implicit current project, SQL, fallback resolver,
or persistent identity. Equal semantic rows remain occurrence-distinct through
their exact snapshot-local output refs.

The refined modules export nothing through `__all__` and remain absent from
`pietto`, `pietto._project`, CLI, script `RelationIR`, SQL renderers, and Project
Explain.

## Integration Boundaries And Non-goals

This continuation adds no canonical snapshot allocator, single-relation
builder, automatic operator allocation, automatic property/transfer
construction, or Project IR construction result.

It adds no upstream Project IR construction, cross-relation producer/use edge,
cross-module DAG, cross-relation compatibility, JOIN, grain/fanout, cycle or
reachability analysis, optimizer, verifier framework, inspection, serializer,
estimator, cost, target/physical plan, parser/AST/grammar, diagnostic, SQL, CLI,
JSON, public schema, Project Explain field, backend change, persistent identity,
Rust implementation, version change, tag, Release, signing, or attestation.

`ProjectModuleRowFieldIdentity` remains the sole module-semantic row-field
identity domain. No intermediate stage field pretends to be a final semantic
field and no operator-flow use pretends to be semantic provenance.

## Slice 5 Resume Handoff

After successful natural exact-head CI:

```text
Phase 61 route remains 12 slices
Slices 1-4 remain completed
output-identity prerequisite = COMPLETED
intra-relation dataflow prerequisite = COMPLETED
Slice 5 remains next / unstarted
```

The only next owner is again:

```text
Phase 61 Slice 5 — Canonical Single-Relation Construction From Existing Project Semantic Facts
```

Slice 5 may consume these exact checkpoints, stage rows, final attribution
identities, and flow carriers. It may not reconstruct them. The builder is not
begun here, and Slice 6 remains unauthorized.

## Gate Lifecycle And Publication

Gate 2 uses focused tests, Ruff, and Pyright; performs one complete candidate
review; permits at most one same-root repair batch; performs a fresh rereview;
and runs exactly one authoritative validator:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Local package smoke is required because packaged private production source
changes. Generated and golden auxiliaries are not locally required because no
input surface changes; natural CI still runs them.

Gate 3 rebinds the predecessor, stages exactly the sealed tree, makes one
ordinary commit, performs one fast-forward push, and observes the unique
natural exact-head CI without dispatch or rerun.

The exact commit subject is:

```text
Add Project IR intra-relation dataflow readiness
```

The published PASS title is:

```text
PASS — PHASE61_SLICE5_INTRA_RELATION_DATAFLOW_READINESS_CONTINUATION_END_TO_END
```

Successful natural exact-head CI completes only this prerequisite continuation
without a status-only follow-up commit. Slice 5 remains next / unstarted.
