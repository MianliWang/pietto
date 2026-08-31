# Phase 61 Slice 10 Real-authored Multi-module Project IR E2E v1

## Answer And Exact Owner

Slice 10 adds one narrow private orchestration boundary:

```text
exact existing ProjectSemanticResult
+ explicit ProjectIRAllocationState
-> published Slice 6 Project plan
-> published Slice 7 evaluation contexts
-> published Slice 8 independent verification
-> published Slice 8 fresh analyses
-> published Slice 9 private inspection
-> published Slice 9 canonical bytes
```

The exact owner is:

```text
src/pietto/_project/project_ir_pipeline.py
```

It calls existing builders only. It does not rediscover a Project, reload a
file, parse syntax, resolve a name, analyze an expression, reconstruct
attribution, build a second IR, verify by constructor success, or encode a
second byte format.

| Surface | Slice 10 result |
| --- | --- |
| Private Slice 6-9 orchestration | `ADDED` |
| Real-authored multi-module E2E assurance | `ADDED` |
| Existing Project semantic ownership | `UNCHANGED` |
| Existing Project IR stages and laws | `UNCHANGED` |
| Public/CLI/JSON/SQL/script `RelationIR` behavior | `0` |
| Slice 11 differential matrix | `0` |
| Version | `0.1.0` |

## Starting Authority

| Fact | Value |
| --- | --- |
| Branch | `main` |
| HEAD | `edf68678b2a766302e654202f3fe0798c3386ffd` |
| Tree | `71002ac6c2836805e544340eb7052c76f249620a` |
| Parent | `577511b9dd6dbf14dbd5dc3710bee0a3d86b92be` |
| Subject | `Add Phase 61 Project IR inspection` |
| Natural exact-head CI | `33353818947`, `push`, attempt `1`, successful |
| Divergence | `0/0` |
| Version | `0.1.0` |

The unique successful natural CI on that exact Slice 9 publication establishes:

```text
Phase 61 = ACTIVE
Slices 1-9 = COMPLETED
both Slice 5 prerequisites = COMPLETED
Slice 10 = NEXT / UNSTARTED
```

The clean pre-write Slice 6-9, lifecycle, and fixed-point-reader baseline was
`108 passed` under Python 3.13.

## Frozen Reader And Changed-path Closure

Fixed-point closure covers the new private owner, all published Slice 1-9 and
both Slice 5 prerequisite contracts, the real Project semantic entry and
`ProjectSemanticResult`, the exact Slice 6-9 builder chain, package and product
test discovery, mutable lifecycle, exact Python source/test counters, and
readers of those readers.

The frozen changed-path allowlist is exactly:

```text
docs/roadmap.md
docs/spec/phase61-slice10-real-authored-multi-module-project-ir-e2e-v1.md
docs/status.md
src/pietto/_project/project_ir_pipeline.py
tests/test_active_phase_lifecycle.py
tests/test_phase61_slice10_real_authored_multi_module_project_ir_e2e.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

This is `A3/M4/D0`. Package discovery and Phase 61 product-test discovery are
dynamic. `tests/test_active_phase_lifecycle.py` remains the sole direct mutable
status/roadmap reader. An eighth path is `READER_CLOSURE_DRIFT`.

## Real-authored Semantic Entry And Exact Roots

Positive assurance begins with pytest-owned authored files and the current
entry sequence:

```text
pietto.toml + *.pietto
-> check_project_parse_only
-> trusted selected sources and parsed logical modules
-> build_empty_project_semantic_result
-> exact existing ProjectSemanticResult
```

The E2E pipeline begins only after that existing path has produced the semantic
result. Positive tests do not construct a
`ProjectModuleSemanticFactSet`, `ProjectModuleAttributionFactSet`,
`ProjectModuleRelationSemanticFacts`, Project IR fragment, or
`ProjectIRProjectPlan`.

The current `ProjectSemanticResult` already retains both required roots:

```text
module_semantic_facts
module_attribution_facts
```

Its existing integrity law proves:

```text
module_attribution_facts._authority.semantic_facts
    is module_semantic_facts
```

The pipeline reuses both objects. It adds no accessor and does not change
`ProjectSemanticResult`. Missing roots or grafted attribution fail closed; no
root is rebuilt and no declaration/reference is re-resolved.

## Explicit Allocation And One-way Pipeline

`build_project_ir_pipeline` requires one caller-supplied exact
`ProjectIRAllocationState`. There is no current/global snapshot state. The
caller continues to own the snapshot scope and initial coordinates.

The implementation calls the published functions in exactly this order:

```text
build_project_ir_project_plan
build_project_ir_evaluation_context_stage
verify_project_ir_stage
build_project_ir_analysis_bundle
build_project_ir_inspection
serialize_project_ir_inspection
```

It copies none of their algorithms. Freeze:

```text
Project semantic result != Project IR snapshot identity
authored Project semantics -> canonical Project IR -> verified observation
```

There is no AST visitor, lookup, type inference, aggregate/window analyzer,
module graph builder, attribution projection, verifier pass, inspection
projection, or byte encoder in the pipeline owner.

## Mandatory Independent Verification

The exact fresh Slice 7 stage is passed to `verify_project_ir_stage`.
Construction proceeds only when:

```text
verification.status == VERIFIED
verification.issues == ()
```

An `INVALID` result raises an internal Project IR integrity failure before
analysis, inspection, or serialization. It is not converted to semantic
`UNKNOWN`, an empty analysis bundle, or a partial portable document. A prior
verification is never accepted as an input.

## Complete E2E Result And Authority Continuity

`ProjectIRPipelineResult` is frozen, slotted, keyword-only, and private. It
retains directly:

```text
exact ProjectSemanticResult
exact starting and ending ProjectIRAllocationState
ProjectIRProjectPlan
ProjectIREvaluationContextStage
ProjectIRVerificationResult
ProjectIRAnalysisBundle
ProjectIRInspectionProduct and its exact ProjectIRInspection
canonical private bytes
```

Formation proves object-for-object continuity:

```text
plan.semantic_facts is semantic_result.module_semantic_facts
plan.attribution is semantic_result.module_attribution_facts
plan.starting_allocation is result.starting_allocation
plan.ending_allocation is result.ending_allocation
evaluation_stage.project_plan is plan
verification.stage is evaluation_stage
analysis_bundle.verification is verification
inspection.analysis_bundle is analysis_bundle
canonical_bytes == inspection_product.canonical_bytes
```

The plan already proves each fragment retains the exact corresponding semantic
fact; every cross edge retains exact resolution, dependency, origin path,
producer output, consumer slot/use, required row shape, and compatibility.
Evaluation contexts retain exact fragment/operator/flow/row/property/effect
objects. The pipeline does not add a second continuity carrier.

## Real Multi-module Assurance Corpus

The focused corpus contains four real modules. It exercises:

```text
c.pietto source -> projected table
-> b.pietto imported alias + explicit re-export
-> a.pietto imported alias
-> shared consumers
-> downstream local consumer

d.pietto disconnected source -> query component
```

One representative authored relation exercises every currently published
operator stage:

```text
Relation Input
-> Row Filter
-> Group/Aggregate
-> Result Filter
-> Window Evaluation
-> Final Projection
-> Relation Ordering
-> Limit
```

It uses only current syntax: `let`, `where`, grouped aggregate, `satisfying`, a
named window, projection, relation order, and static limit. Exact cross-relation
uses prove the two-hop re-export route, shared producer with distinct use/slot
occurrences, row-shape compatibility, and a multi-hop consumer chain.

Authored declaration, field, and reference occurrences remain module-semantic
identities. Plan node, output, use, and input-slot refs remain separate
snapshot-local domains. Equal selected field names in two consumers keep
distinct authored field identities and distinct Project IR output refs.

## Mixed Concrete And Non-concrete Project

The same real Project contains a currently supported genuine non-concrete query:
its selected field is absent from the resolved input row. Its semantic terminal
survives into the complete Project plan while the disconnected concrete
component remains present.

The terminal allocates no node, output, slot, use, operator, property, or fake
cross edge. Independent verification still returns `VERIFIED` for the complete
representable product, and the existing typed inspection query returns the
exact why-not fragment.

```text
non-concrete evidence != invalid Project IR
non-concrete terminal != fake plan node
```

## Canonical Observation And Bounded Determinism

The positive path reaches the only published private encoder without manually
constructing a portable document:

```text
real authored Project
-> exact semantic result
-> canonical Project IR
-> VERIFIED
-> fresh analyses
-> inspection
-> pietto.project-ir-inspection.v1 bytes
```

Two builds from the same exact authored semantic result and equal starting
coordinates in fresh snapshot scopes have unequal runtime refs and byte-equal
canonical observations. A bounded two-run subprocess check varies only
`PYTHONHASHSEED` and unrelated cwd and compares the complete bytes.

Freeze:

```text
bytes != occurrence identity
bytes != semantic authority
bytes != semantic equivalence
bytes != persistent identity
```

Slice 10 adds no digest or bytes-derived lookup.

## Privacy Compatibility And Non-goals

The module exports nothing through `__all__` and is not re-exported by
`pietto` or `pietto._project`. Existing public commands do not call it.

Slice 10 changes no grammar, AST, semantic admission, diagnostic, Project
discovery/trust rule, import/export/resolution rule, semantic identity, Slice
2-9 carrier law, script `RelationIR`, SQL, backend, CLI, JSON/schema, Project
Explain field, optimizer, rewrite, recursion/fixpoint, JOIN/grain/fanout,
physical plan, cache identity, package format, version, tag, Release, signing,
or attestation.

It adds no alternate Project compiler and no fallback to authored syntax when
a retained downstream authority is missing.

## Focused Assurance

Focused tests prove:

```text
real trusted multi-module Project semantic entry
real imported alias and two-hop re-export route
multi-hop relation chain and shared producer uses
exact semantic-root and attribution continuity
all eight current operator stages
cross-relation compatibility and occurrence preservation
aggregate/window evaluation contexts
mandatory fresh VERIFIED result
fresh analysis bundle and exact inspection
canonical serialization without manual portable construction
mixed concrete/non-concrete complete Project result
same authored Project + fresh scope -> unequal refs + equal bytes
bounded hash-seed/cwd independence
INVALID stops before analysis
missing semantic roots fail closed
private/public/SQL/script RelationIR zero-delta
```

Temporary files are pytest-owned and subprocesses are isolated. Tests remain
xdist/serial compatible.

## Slice 11 Handoff

After successful natural exact-head CI:

```text
Phase 61 remains exactly 12 slices
Slices 1-10 = COMPLETED
Slice 11 = NEXT / UNSTARTED
```

The only next owner is:

```text
Phase 61 Slice 11 — Differential Compatibility
```

Slice 11 owns the broad Python 3.12/3.13, relocation, wheel/install,
hash/order/environment, and negative-state differential matrix. Slice 10 does
not begin that work.

## Gate Lifecycle And Publication

Gate 2 uses focused tests, Ruff, and Pyright; freezes the complete finding set;
permits at most one same-root repair batch; performs a fresh rereview; and
starts exactly one authoritative validator:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Local package smoke is required because one packaged private module is added.
Generated and public golden inputs do not change; natural CI still checks them.

Gate 3 rebinds the predecessor, stages exactly the sealed seven-path tree,
makes one ordinary commit, performs one fast-forward push, and observes the
unique natural exact-head CI without dispatch, cancel, or rerun.

The exact commit subject is:

```text
Add Phase 61 Project IR end-to-end pipeline
```

The published PASS title is:

```text
PASS — PHASE61_SLICE10_REAL_AUTHORED_MULTI_MODULE_PROJECT_IR_END_TO_END
```

Successful natural exact-head CI completes Slice 10 without a status-only
follow-up commit. Slice 11 remains next / unstarted.
