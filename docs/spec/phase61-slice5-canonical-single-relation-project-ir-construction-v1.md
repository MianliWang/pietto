# Phase 61 Slice 5 Canonical Single-relation Project IR Construction v1

## Answer And Exact Owner

Slice 5 implements exactly:

```text
one exact ProjectModuleRelationSemanticFacts subject
+ its exact ProjectModuleAttributionFactSet authority
+ one explicit ProjectIRAllocationState

-> one canonical single-relation Project IR fragment
```

The private production owner is:

```text
src/pietto/_project/project_ir_construction.py
```

It automatically constructs the published structural, property, and logical
stages. It does not construct an upstream relation, cross-relation edge,
Project-wide DAG, optimizer, verifier framework, inspection product, target
plan, SQL, or public output.

| Surface | Slice 5 result |
| --- | --- |
| Private canonical single-relation builder | `ADDED` |
| Explicit snapshot allocation continuation | `ADDED` |
| Current operators/rows/outputs/flow/properties/transfers | `CONSTRUCTED` |
| Cross-relation composition / Slice 6 | `0` |
| Parser/AST/SQL/CLI/public schema/Project Explain | `0` |
| Version | `0.1.0` |

## Starting Authority

| Fact | Value |
| --- | --- |
| Branch | `main` |
| HEAD | `1ac00344554967ba30f2e3bdff553ec63c2a4c12` |
| Tree | `c73d5c93c2c037f8258beab4ba5587e4873c3319` |
| Parent | `cce7709f143de4eb5f9989cbbbd804fe08e71d74` |
| Subject | `Add Project IR intra-relation dataflow readiness` |
| Natural exact-head CI | `33335654061`, `push`, attempt `1`, successful |
| Divergence | `0/0` |
| Version | `0.1.0` |

That exact publication completes both unnumbered Slice 5 prerequisites:

```text
output-identity authority readiness = COMPLETED
intra-relation dataflow readiness = COMPLETED
Slice 5 = NEXT / UNSTARTED
```

The live pre-write feasibility proof used real parsed/analyzed simple,
group/window, and full eight-stage relations. Exact INPUT, BASE_RESULT, FINAL
stage, final semantic output identities, stage-local scalar values, and all
adjacent operator-flow edges formed without final-schema borrowing or fake
semantic provenance. The clean focused baseline was `103 passed` under Python
3.13.

## Frozen Reader And Changed-path Closure

Fixed-point closure covered the new private builder and package discovery;
structural dense-coordinate formation; Slice 2–4 and both prerequisite
carriers/readers; lifecycle and readers of lifecycle; Phase 61 product-test
glob readers; exact Python source/test counts; and readers of those readers.

The frozen changed-path allowlist is exactly:

```text
docs/roadmap.md
docs/spec/phase61-slice5-canonical-single-relation-project-ir-construction-v1.md
docs/status.md
src/pietto/_project/project_ir.py
src/pietto/_project/project_ir_construction.py
tests/test_active_phase_lifecycle.py
tests/test_phase61_slice5_canonical_single_relation_project_ir_construction.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

This is `A3/M5/D0`. Existing workflow/read-acquisition tests discover the new
product test dynamically, and package smoke discovers the new private module.
`tests/test_active_phase_lifecycle.py` remains the sole direct reader of mutable
status/roadmap. A ninth path is `READER_CLOSURE_DRIFT`.

## Exact Builder Inputs And Allocation

`build_project_ir_single_relation_fragment` requires exact existing objects:

```text
ProjectModuleRelationSemanticFacts
ProjectModuleAttributionFactSet
ProjectIRAllocationState
```

The builder proves that the semantic fact is the one exact object retained by
the attribution authority. It does not repeat AST, name, type, aggregate,
window, SQL, or lineage analysis.

For table/query final fields it consumes only:

```text
ProjectModuleAttributionFactSet.find_relation_output_fields(...)
```

and reuses every exact identity, semantic-fact root, and `ProjectRowField`
object. Source final rows reuse the exact canonical source-field origins.

Freeze:

```text
final semantic field identity != intermediate plan-local field/value identity
```

`ProjectIRAllocationState` is a frozen, explicit cursor over one exact
`ProjectIRSnapshotScope` with independent next coordinates for plan nodes,
output values, input slots, and uses. Coordinates are non-negative integers;
there is no global state, registry, singleton, UUID, randomness, cwd/path/hash
identity, or implicit current project.

Every fragment uses a dense ordered interval in each ref domain beginning at
the caller-supplied coordinate. `ProjectIRStructuralStage` therefore accepts an
arbitrary starting coordinate while continuing to reject gaps, duplicates,
reordering, and foreign scope. A returned allocation may construct another
fragment in the same scope without changing any existing ref.

Non-concrete construction returns the exact same allocation object.

## Canonical Operator Row And Output Construction

The builder calls the existing exact semantic operator-kind derivation. The
caller supplies no kinds or order. The frozen current sequence remains:

```text
Relation Input
-> Row Filter?
-> Group/Aggregate?
-> Result Filter?
-> Window Evaluation?
-> Final Projection
-> Relation Ordering?
-> Limit?
```

Sources contain only Relation Input. Omitted stages allocate nothing. `let:`,
named-window declarations, frames, EXCLUDE, NULL treatment, FROM FIRST/LAST,
and aggregate-local ordering allocate no operator node. One node is allocated
per actual operator and the final node is the relation root.

Every operator first allocates exactly one relation-row output. Row shapes use
the prerequisite mapping without recomputation:

```text
Source Relation Input  -> source final semantic row
Derived Relation Input -> INPUT stage row
Row Filter             -> INPUT stage row
Group/Aggregate        -> BASE_RESULT stage row
Result Filter          -> BASE_RESULT stage row
Window Evaluation      -> FINAL stage row
Final Projection       -> final semantic row
Relation Ordering      -> final semantic row
Limit                  -> final semantic row
```

The root relation-row output is exposed directly by the concrete result.

After its row output, Window Evaluation allocates one
`ProjectIRStageScalarFieldOutput` for each exact current window-result fact in
semantic field order. These plan-local outputs have no
`ProjectModuleRowFieldIdentity`.

After its row output, Final Projection allocates one
`ProjectIRScalarFieldOutput` for every final table/query attribution in exact
field order. The exact attribution identity objects are reused. A window stage
scalar and its semantically equal final export remain different output
occurrences.

The deterministic per-operator allocation order is:

```text
relation-row output
-> required stage-local window scalars
-> Final Projection semantic exports
```

Sources have no Final Projection and expose no scalar export occurrences in
this single-relation fragment; their exact source fields remain present in the
root final row shape.

## Intra-relation Flow And Slice 6 Boundary

For every adjacent operator pair, the builder constructs exactly:

```text
Operator[i].relation-row output
-> ProjectIROperatorFlowUseOccurrence
-> Operator[i + 1] input slot 0
```

Input-slot refs follow consumer order and flow-use refs follow adjacent-edge
order. The first operator has no intra-relation slot. A source leaf has no flow
use. The existing logical-stage formation proves tuple/flow agreement.

Derived semantic facts retain their exact `from:` resolution and attribution
authority, but Slice 5 does not follow that relation. The fragment contains no
upstream subject, upstream output, semantic `ProjectIRUseOccurrence`, external
placeholder, required row-shape satisfaction, or cross-relation compatibility.

Freeze:

```text
intra-relation operator flow != future cross-relation semantic dependency edge
```

Slice 6 alone owns the real producer/use/input-slot composition across relation
fragments.

## Property Transfer Effect And Estimate Construction

The builder uses the existing Slice 3 carriers and Slice 4 transfer matrix; it
adds no second property engine.

Every relation-row output receives exact output shape, BAG multiplicity, and
closed bindings. Exact local group-key evidence is established at
Group/Aggregate and retained only across operators whose frozen matrix
preserves it. Relation Ordering establishes exact result order and Limit
preserves it when present. Limit establishes the exact static cardinality upper
bound.

Every stage/final scalar receives exact output shape. Each stage-local window
scalar also receives the exact existing evaluation policy. No property is
invented merely to complete a chain.

Every retained provided property has exactly one automatically constructed
established or preserved transfer. Preserved input authority is the exact row
output reached by the real operator-flow edge, never tuple adjacency alone.

The builder creates one effect carrier for every current output. All four axes
remain explicitly `UNKNOWN`. It infers no purity, determinism, no-error, or
evaluation-count-insensitive claim.

The estimate boundary is exactly empty. There is no SET, uniqueness, FD/key,
fanout, general grain comparison, statistic, estimator, or cost.

No required property or compatibility result is fabricated for the absent
upstream Project IR producer.

## Concrete And Non-concrete Results

`ProjectIRConcreteSingleRelationFragment` exposes directly:

```text
exact concrete semantic subject and attribution root
starting and ending allocation
shared structural/property/logical stages
root node
root relation-row output
ordered final semantic scalar exports
```

The stage objects retain exact object composition; callers perform no scan or
name lookup to rediscover the root or exports.

`ProjectIRNonConcreteSingleRelationFragment` preserves `UNKNOWN`, `DEFERRED`,
`BLOCKED`, or semantic `AMBIGUOUS` evidence as the existing typed terminal. It
contains no node, output, slot, use, operator, property, effect, root, or scalar
export, and its ending allocation is the exact starting object.

Malformed supposedly concrete semantic/attribution authority raises an
invariant error. It is never converted to semantic UNKNOWN and no fake plan
node is created.

## Determinism Canonicality And Privacy

All new carriers are frozen, slotted, and keyword-only. Exact collections are
tuples in semantic/allocation order. Construction neither sorts away authored
order nor deduplicates equal occurrences.

Freeze:

```text
same exact semantic/attribution authority + same explicit starting allocator
-> same snapshot-local coordinates and ordered construction
```

Different snapshot scopes remain occurrence-distinct. Two semantically equal
authored relation occurrences retain different semantic anchors and final field
identities. Canonical construction never selects first/latest/nearest/best and
never uses object repr/address, cwd, environment, or unordered iteration as
authority.

The module exports nothing through `__all__` and remains absent from public
Pietto, `pietto._project`, CLI, SQL, script `RelationIR`, and Project Explain.

## Focused Assurance

Positive tests use real parsed/analyzed Project semantic and attribution facts
as builder inputs. They do not hand-build the returned IR stages.

Focused assurance covers:

```text
source leaf
simple projection
where
group/aggregate
satisfying
window
order
limit
full eight-stage relation
let/named-window omission
INPUT / BASE_RESULT / FINAL fidelity
one row output per operator
exact output/slot/use allocation order
one flow edge per adjacent pair
stage scalar != final export
canonical final attribution identities
exact root and ordered exports
complete property/transfer formation through flow authority
unknown effects and empty estimates
non-concrete zero allocation
same-start determinism and same-scope continuation
different-snapshot and equal-semantics occurrence distinction
no upstream recursive construction or cross-relation edge
hash-seed/cwd independence
public/SQL/script RelationIR zero-delta
```

The tests retain xdist/serial compatibility through pytest-owned paths and
isolated subprocesses.

## Integration Boundaries And Non-goals

Slice 5 adds no cross-relation Project IR composition, upstream recursion,
Project-wide DAG, JOIN, grain comparison, fanout, nested/correlated plan,
optimizer, memo, rewrite, verifier framework, pass manager, inspection,
canonical serialization, estimator, cost model, target/physical plan,
parser/AST/grammar, diagnostic, SQL, CLI, JSON, public schema, Project Explain
field, backend behavior, persistent identity, Rust implementation, version
change, tag, Release, signing, or attestation.

It creates no new module-semantic field identity, synthetic final identity,
false lineage, final-schema placeholder, or fake semantic provenance.

## Slice 6 Handoff

After successful natural exact-head CI:

```text
Phase 61 route remains exactly 12 slices
Slices 1-5 = COMPLETED
both unnumbered Slice 5 prerequisites = COMPLETED
Slice 6 = NEXT / UNSTARTED
```

The only next owner is:

```text
Phase 61 Slice 6 — Cross-Module Relation Composition And Acyclic Project Plan DAG
```

Slice 6 may continue allocations in one scope and compose the retained exact
semantic resolutions with real producer/output/use/input-slot authority. Slice
5 builds no part of that cross-relation graph.

## Gate Lifecycle And Publication

Gate 2 uses focused tests, Ruff, and Pyright; performs one complete candidate
review; permits at most one same-root repair batch; performs a fresh rereview;
and runs exactly one authoritative validator:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Local package smoke is required because a packaged private module is added.
Generated and golden auxiliaries are not locally required because their inputs
do not change; natural CI still runs them.

Gate 3 rebinds the predecessor, stages exactly the sealed tree, makes one
ordinary commit, performs one fast-forward push, and observes the unique
natural exact-head CI without dispatch or rerun.

The exact commit subject is:

```text
Add Phase 61 single-relation Project IR builder
```

The published PASS title is:

```text
PASS — PHASE61_SLICE5_CANONICAL_SINGLE_RELATION_CONSTRUCTION_FROM_PROJECT_SEMANTIC_FACTS_END_TO_END
```

Successful natural exact-head CI completes Slice 5 without a status-only
follow-up commit. Slice 6 remains next / unstarted.
