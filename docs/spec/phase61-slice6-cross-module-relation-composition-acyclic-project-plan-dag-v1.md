# Phase 61 Slice 6 Cross-module Relation Composition And Acyclic Project Plan DAG v1

## Answer And Exact Owner

Slice 6 implements exactly:

```text
all retained Project relation semantic subjects
-> same-snapshot Slice 5 fragments
-> exact resolved relation-row uses
-> one complete acyclic Project plan DAG
```

The private production owner is:

```text
src/pietto/_project/project_ir_composition.py
```

“Cross-module” covers every exact current relation dependency, including local,
imported, aliased, and re-exported targets. Locality and names never select a
producer.

| Surface | Slice 6 result |
| --- | --- |
| Complete same-snapshot fragment composition | `ADDED` |
| Exact cross-relation edge authority | `ADDED` |
| Cross-boundary row requirement/compatibility | `ADDED` |
| Actual-use DAG acyclicity | `ADDED` |
| Slice 7 evaluation context | `0` |
| JOIN/grain/fanout/optimizer/verifier/inspection | `0` |
| Parser/AST/SQL/CLI/public schema/Project Explain | `0` |
| Version | `0.1.0` |

## Starting Authority

| Fact | Value |
| --- | --- |
| Branch | `main` |
| HEAD | `b9c9e38f809f911eb429e7284d377c2c205e548b` |
| Tree | `4273b06c631db9e609d0915d3880bc6b4ea3aaa6` |
| Parent | `1ac00344554967ba30f2e3bdff553ec63c2a4c12` |
| Subject | `Add Phase 61 single-relation Project IR builder` |
| Natural exact-head CI | `33337635343`, `push`, attempt `1`, successful |
| Divergence | `0/0` |
| Version | `0.1.0` |

That exact publication establishes:

```text
Phase 61 = ACTIVE
Slices 1-5 = COMPLETED
both Slice 5 prerequisites = COMPLETED
Slice 6 = NEXT / UNSTARTED
```

The live pre-write proof used real same-module consumers and imported relation
facts. Exact resolved dependencies, producer root shapes, consumer INPUT state,
and row compatibility formed successfully. It also reproduced the only two
required structural refinements: two owners may each retain semantic
`RELATION_INPUT source_order = 0`, and dependency-environment order may be the
reverse of module-position order. The clean focused baseline was `191 passed`
under Python 3.13.

## Frozen Reader And Changed-path Closure

Fixed-point closure covered semantic dependency-environment and relation-fact
ordering; exact attribution dependency lookup; Slice 2 structural/use
formation; Slice 3 compatibility; Slice 5 construction and allocation;
package discovery; lifecycle and readers of lifecycle; Phase 61 product-test
glob readers; exact Python source/test counts; and readers of those readers.

The frozen changed-path allowlist is exactly:

```text
docs/roadmap.md
docs/spec/phase61-slice6-cross-module-relation-composition-acyclic-project-plan-dag-v1.md
docs/status.md
src/pietto/_project/project_ir.py
src/pietto/_project/project_ir_composition.py
tests/test_active_phase_lifecycle.py
tests/test_phase61_slice6_cross_module_relation_composition_acyclic_project_plan_dag.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

This is `A3/M5/D0`. Existing workflow/read-acquisition tests discover the new
product test dynamically, and package smoke discovers the private composition
module. `tests/test_active_phase_lifecycle.py` remains the sole direct mutable
status/roadmap reader. A ninth path is `READER_CLOSURE_DRIFT`.

## Canonical Fragment Order And Allocation

`build_project_ir_project_plan` consumes exact existing roots:

```text
ProjectModuleSemanticFactSet
ProjectModuleAttributionFactSet
ProjectIRAllocationState
```

The attribution authority must retain that exact semantic-fact root.

Exactly one Slice 5 fragment is constructed for every retained relation fact
using one snapshot scope and one allocation continuation. Canonical order is
the existing authority order:

```text
dependency-ordered environments -> source-ordered relation facts
```

No name sort or graph traversal changes that order. Non-concrete fragments
remain in the tuple and consume zero allocation.

Only after all fragments exist does composition allocate one external input
slot and one semantic use per concrete derived consumer, in canonical consumer
order. It allocates zero plan nodes and zero outputs. All fragment refs remain
unchanged. The final allocation advances only the slot/use domains by the edge
count.

`ProjectIRStructuralStage` continues to require unique subjects, while the
Project result proves their exact canonical semantic order. Structural subject
formation no longer mistakes module-position order for dependency authority.

## Exact Cross-relation Edge Authority

Every concrete table/query consumer has exactly one current `from:` edge.
Composition derives the exact Phase 59 reference occurrence from its exact
declaration owner and retrieves exactly one
`ProjectModuleDependencyFact(RELATION_REFERENCE)` through
`find_reference_dependencies`.

`ProjectIRResolvedRelationAnchor` retains the exact:

```text
ProjectResolvedModuleRelationReference
ProjectModuleDependencyFact
origin/provenance path
target declaration occurrence
consumer reference occurrence
```

The target declaration occurrence selects the producer fragment. Local names,
declared names, aliases, module locality, and first/nearest fallback are never
used.

For every edge, composition allocates exactly:

```text
producer.root_relation_output
-> ProjectIRUseOccurrence(role=RELATION_INPUT, source_order=0)
-> consumer Relation Input external slot(input_ordinal=0)
```

The edge is always attached to the exact Relation Input node and always uses
the producer relation-row output, never a scalar. Field dependency and lineage
facts remain semantic authority and do not create duplicate plan edges.

```text
direct use occurrence = authority
node adjacency = derived view
```

`ProjectIRCrossRelationEdge` retains producer/consumer concrete fragments,
resolved authority, external slot, semantic use, provided/required row shapes,
and compatibility. It validates all endpoints by object identity. The use is
the direct topology authority; no second node-adjacency carrier exists.

Semantic source order is owner-local for current relation inputs:

```text
global structural order = ProjectIRUseRef coordinate order
semantic source order = exact owner/container-local evidence
```

Different relations may each retain `source_order = 0`. Non-relation semantic
use ordering keeps its prior invariant; unrelated roles are not broadened or
globally renumbered.

## Cross-boundary Row Requirement And Compatibility

Each cross edge reuses the producer root's exact retained
`ProjectIRProvidedOutputShape`. The root row shape must be the exact final
`ProjectIRRowShape`.

The consumer external slot, producer final row shape, and resolved anchor form
one `ProjectIRRequiredRowShape`. They then form one
`ProjectIRRowShapeCompatibility`, which must be `SATISFIED`.

The edge additionally proves:

```text
consumer Relation Input row = INPUT stage checkpoint
consumer semantic input_state is producer semantic final state
checkpoint state is that same exact producer state object
```

No schema is rebuilt. Ordering, local grain, cardinality, effects, or estimates
are not propagated across the edge. The current cross-boundary requirement is
row shape only.

## Project Structural DAG Sharing And Acyclicity

The project structural stage reuses object-for-object every fragment node,
output, internal slot, internal operator-flow use, and subject, then appends the
new external slots and semantic uses in ref order.

It therefore retains both distinct use carriers:

```text
ProjectIROperatorFlowUseOccurrence
ProjectIRUseOccurrence
```

One producer may feed several consumers. Every consumer retains a distinct use
and slot even when the producer root output is shared. No semantic or
occurrence deduplication occurs.

Freeze:

```text
logical DAG sharing != materialization != execute once != cache identity
```

Construction derives actual graph edges only from retained uses:

```text
use.output.producer -> use.slot.consumer
```

A deterministic Kahn check accepts allocation-backward edges and disconnected
components but rejects any actual concrete cycle. Allocation/ref order is not
topological authority. Authored current relation cycles remain non-concrete
terminals and create no fake node or edge. This is local Slice 6 construction
integrity, not the general Slice 8 verifier framework and not recursion.

## Complete Concrete And Non-concrete Result

`ProjectIRProjectPlan` exposes directly:

```text
exact semantic-fact and attribution roots
starting and ending allocation
all Slice 5 fragments in canonical semantic order
project structural DAG
all exact cross-relation edges in canonical consumer order
```

Derived convenience views return all concrete fragments or all non-concrete
fragments without choosing a hidden root or winner. Disconnected components are
valid.

Non-concrete consumers retain their exact Slice 5 terminal, allocate no cross
slot/use, and create no compatibility. A blocked component does not erase an
independent concrete component. A concrete consumer with a missing, duplicate,
or non-concrete producer is an invariant failure rather than a fallback state.

## Determinism Immutability And Privacy

All Slice 6 carriers are frozen, slotted, and keyword-only. Collections are
exact tuples in existing semantic/ref order. Construction does not sort,
deduplicate, winner-select, or allocate from unordered iteration.

Freeze:

```text
direct relation use = authority
transitive dependency = derived
allocation order != topological order
semantic equivalence != occurrence identity
package/module/declaration identity != ProjectIR local ref
Project DAG != optimizer memo != target plan != physical execution graph
```

No hash/digest, name, path, object repr/address, cwd, environment, registry,
singleton, UUID, random value, or process-global state becomes graph identity.

The new owner exports nothing through `__all__` and remains absent from public
Pietto, `pietto._project`, CLI, SQL, script `RelationIR`, and Project Explain.

## Focused Assurance

Positive tests use real parsed/analyzed multi-relation and multi-module facts and
the real Slice 5 builder. They do not hand-build a positive Project result.

Focused assurance covers:

```text
source -> query and multi-hop query chains
same-module forward relation reference
cross-module import and multi-hop re-export
one producer -> two distinct consumer uses
two disconnected concrete components
exact producer root and consumer Relation Input endpoints
exact dependency/provenance authority
one relation-row cross edge per concrete derived consumer
no field-level duplicate edges
provided/required exact row shapes and SATISFIED compatibility
consumer INPUT state object identity
owner-local source_order=0 without global renumbering
fragment ref preservation and deterministic appended cross refs
same-start determinism
allocation-backward edge without topological-order assumption
actual-use acyclicity and concrete-cycle rejection
local authored cycle terminals with independent concrete component
fragment-local effects/estimates unchanged
hash-seed/cwd independence
public/SQL/script RelationIR zero-delta
```

Tests use pytest-owned paths and isolated subprocesses and remain xdist/serial
compatible.

## Integration Boundaries And Non-goals

Slice 6 adds no Slice 7 evaluation context, aggregate/window semantic change,
JOIN, grain comparison, fanout, field-level plan topology, recursion/fixpoint,
global property inference, optimizer, memo, rewrite, general verifier/pass
manager, inspection, canonical serialization, estimator, cost, target/physical
plan, parser/AST/grammar, diagnostic, SQL, CLI, JSON, public schema, Project
Explain field, backend behavior, persistent identity, materialization/execution
count, Rust implementation, version change, tag, Release, signing, or
attestation.

It changes neither the frozen eight-stage operator algebra nor any
module-semantic identity.

## Slice 7 Handoff

After successful natural exact-head CI:

```text
Phase 61 remains exactly 12 slices
Slices 1-6 = COMPLETED
Slice 7 = NEXT / UNSTARTED
```

The only next owner is:

```text
Phase 61 Slice 7 — Aggregate/Window Evaluation Context, Policy/Effect Preservation, And No-Ambient Authority
```

Slice 6 builds none of that evaluation-context product.

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
Add Phase 61 Project IR composition DAG
```

The published PASS title is:

```text
PASS — PHASE61_SLICE6_CROSS_MODULE_RELATION_COMPOSITION_ACYCLIC_PROJECT_PLAN_DAG_END_TO_END
```

Successful natural exact-head CI completes Slice 6 without a status-only
follow-up commit. Slice 7 remains next / unstarted.
