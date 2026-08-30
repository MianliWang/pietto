# Phase 61 Slice 2 Project IR Structural Model v1

## Answer And Exact Owner

Slice 2 implements exactly the first private Project IR structural foundation:

```text
Project IR snapshot scope
+ explicit structural stage boundary
+ typed plan/output/use/input-slot occurrence domains
+ exact relation/field anchor seams
+ typed relation construction states
```

The production owner is:

```text
src/pietto/_project/project_ir.py
```

It is private and unexported. Slice 2 constructs no logical operator and no
Project IR from authored or semantic Project inputs.

| Surface | Slice 2 result |
| --- | --- |
| Private structural production | `ADDED` |
| Logical operator kinds/construction | `0` |
| Project semantic-facts -> Project IR builder | `0` |
| Row/output/property/effect/estimate semantics | `0` |
| Cross-module plan DAG construction | `0` |
| Verifier/pass manager/optimizer | `0` |
| Correlation/nesting/recursion/JOIN/grain | `0` |
| Parser/AST/SQL/CLI/public schema/Project Explain | `0` |
| Version | `0.1.0` |

## Starting Authority

| Fact | Value |
| --- | --- |
| Branch | `main` |
| HEAD | `6445ac9e5a844f8ac5b71fb01ffc573f5bc35de2` |
| Tree | `c82cfb9e4c5ab7549619b6c1505be6d2fad6bd71` |
| Parent | `bf4eeb06507f84374b9d97070423face3e54d929` |
| Subject | `Add Phase 61 Project IR route lock` |
| Natural exact-head CI | `33303992201`, `push`, attempt `1`, successful |
| Divergence | `0/0` |
| Version | `0.1.0` |
| Tag/signature/Release | no HEAD tag, unsigned commit, no GitHub Release |

Successful natural exact-head CI on that exact Slice 1 publication establishes:

```text
Phase 61 = ACTIVE
Slice 1 = COMPLETED
Slice 2 = NEXT / NOT IMPLEMENTED
```

Slice 2 rebinds live Git and CI rather than inferring completion from mutable
documentation.

## Frozen Reader And Changed-path Closure

Fixed-point closure covered Phase 61 state/next-owner strings, the route,
controlling-contract readers, changed-path inventories, the mutable lifecycle
owner, product-test glob readers, and exact Python source/test count readers.
The frozen allowlist is exactly:

```text
docs/roadmap.md
docs/spec/phase61-slice2-project-ir-scope-stages-occurrences-anchors-construction-states-v1.md
docs/status.md
src/pietto/_project/project_ir.py
tests/test_active_phase_lifecycle.py
tests/test_phase61_slice2_project_ir_scope_stages_occurrences_anchors_construction_states.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

This is `A3/M4/D0`. The existing Phase 61 product glob already includes Slice
2, and package/build inventories discover private package modules dynamically.
`tests/test_active_phase_lifecycle.py` remains the sole direct reader of
mutable `docs/status.md` and `docs/roadmap.md`. An eighth changed path is
`READER_CLOSURE_DRIFT`.

## Snapshot Scope And Typed Ref Domains

`ProjectIRSnapshotScope` is an opaque runtime identity token. Equality is
object identity, while its representation is the stable text
`ProjectIRSnapshotScope()` and leaks no address or random token.

Every local ref contains exactly:

```text
exact ProjectIRSnapshotScope
+ exact nominal ref class/domain
+ non-negative local position
```

The four nominal domains are:

| Domain | Carrier |
| --- | --- |
| Plan-node occurrence | `ProjectIRPlanNodeRef` |
| Output-value occurrence | `ProjectIROutputValueRef` |
| Relation/value-use occurrence | `ProjectIRUseRef` |
| Consumer input-slot occurrence | `ProjectIRInputSlotRef` |

They are separate frozen classes, not a domain enum plus one generic ref.
The same local position under two scope objects is unequal; the same scope and
position under two ref classes is also unequal. `bool`, strings, paths, hashes,
UUIDs, cwd, process counters, or source bytes are not coordinates.

Snapshot-local identity remains separate from future persistent cache identity.

## Exact Relation Resolution And Field Anchors

Slice 2 creates no name resolver and no semantic identity replacement.

`ProjectIRRelationAnchor` wraps one exact existing
`ProjectDeclarationOccurrenceIdentity` and accepts only relation-namespace
`SOURCE`, `TABLE`, or `QUERY` declarations.

`ProjectIRResolvedRelationAnchor` wraps one exact existing
`ProjectResolvedModuleRelationReference` together with its exact existing
`ProjectModuleDependencyFact`. It derives and exposes the typed
`ProjectModuleReferenceOccurrenceIdentity(RELATION_FROM)` and exact target
`ProjectDeclarationOccurrenceIdentity`; the resolution/dependency witnesses
and Phase 59 `origin_path` remain retained but do not become second equality
authorities.

`ProjectIRFieldAnchor` wraps one exact existing
`ProjectModuleRowFieldIdentity` for a produced field.

`ProjectIRResolvedFieldAnchor` wraps one exact existing row-field
`ProjectModuleDependencyFact` and exposes its exact
`ProjectModuleReferenceOccurrenceIdentity(ROW_FIELD)`, target
`ProjectModuleRowFieldIdentity`, and retained Phase 59 `origin_path` for a use.

No anchor is formed from a bare name, logical path, nearest scope, lexical
distance, SQL, source text, or content hash. Current structural stages expose:

```text
free_outer_bindings = ()
```

No outer/correlation or relationship-traversal anchor exists.

## Explicit Structural Stage

`ProjectIRStructuralStage` is the only Slice 2 stage carrier. Its type, rather
than a mutable enum and optional future fields, establishes that it contains
only:

```text
snapshot scope
ordered structural plan-node occurrences
ordered structural output-value occurrences
ordered consumer input-slot occurrences
ordered use occurrences
ordered relation construction subjects
```

It has no logical operator kind, row/output property, effect, estimate,
optimizer alternative, target plan, physical plan, verifier result, or
serialization state.

Each occurrence collection is an exact tuple. Its typed local positions must
be the explicit contiguous order `0..n-1`; the stage rejects duplicate,
reordered, foreign-scope, or missing retained compositions rather than sorting,
deduplicating, or choosing a winner.

The stage performs only local formation checks. It does not traverse a graph,
check cycles, derive reachability, invalidate analyses, or implement the Slice
8 verifier.

## Plan Output Use And Input-slot Occurrences

The structural occurrence carriers are:

| Carrier | Owned facts |
| --- | --- |
| `ProjectIRPlanNodeOccurrence` | plan ref plus exact relation anchor; no operator kind |
| `ProjectIROutputValueOccurrence` | output ref, exact producer node, exact relation/field anchor |
| `ProjectIRInputSlotOccurrence` | slot ref, exact consumer node, one input ordinal |
| `ProjectIRUseOccurrence` | use ref, exact output, exact slot, existing semantic role, source order, exact relation/field dependency provenance anchor |

The dependency shape is exact composition:

```text
ProjectIROutputValueOccurrence
-> ProjectIRUseOccurrence
-> ProjectIRInputSlotOccurrence
```

The input ordinal is owned only by `ProjectIRInputSlotOccurrence` and exposed by
the use through a property. The role and source order are owned only by the use.
The ref position is the occurrence coordinate, not a replacement semantic
ordinal.

Relation uses require the existing `RELATION_INPUT` role and an exact resolved
relation/dependency anchor whose target is the producer and whose reference
owner is the consumer. Field uses require an exact resolved row-field
dependency anchor whose target is the output field and whose reference owner is
the consumer; they cannot claim `RELATION_INPUT`.

Two uses may consume the same producer output while keeping separate use refs,
source orders, and consumer slots. One slot cannot select among multiple uses.

## Construction-state Sum Boundary

`ProjectIRRelationConstructionState` contains exactly:

```text
CONCRETE
UNKNOWN
DEFERRED
BLOCKED
AMBIGUOUS
```

The carrier is a constrained sum, not one object with optional root/reason
fields:

| Variant | Required payload | Forbidden payload |
| --- | --- | --- |
| `ProjectIRConcreteRelationSubject` | relation anchor, exact concrete `ProjectModuleRelationSemanticFacts`, structural root node | state/reason optionals |
| `ProjectIRNonConcreteRelationSubject` | relation anchor, one non-concrete state, exact matching semantic-fact or ambiguity-issue evidence | plan root/reason optional |

Concrete evidence must retain the existing `CONCRETE` row-schema state and the
root must retain the same relation anchor. `UNKNOWN`, `DEFERRED`, and `BLOCKED`
terminals must match the existing semantic row-state evidence. `AMBIGUOUS`
requires exact ambiguous candidate evidence or the existing
`AMBIGUOUS_LOCAL_RELATION_NAME` issue.

No `UnknownPlanNode`, `DeferredPlanNode`, `BlockedPlanNode`, or
`AmbiguousPlanNode` exists. A structural stage may contain an independently
concrete subject and independently non-concrete terminal together; only the
concrete subject owns a root node.

## Determinism Immutability And Privacy

All Slice 2 carriers are frozen, slotted, keyword-only dataclasses. Semantic
collections are exact ordered tuples. Formation validates supplied order and
never allocates identity from unordered iteration.

There is no mutable registry, ambient singleton, module-global counter, cwd
lookup, UUID, random value, hash/content identity, fallback lookup, semantic
auto-deduplication, or current-project/current-module ambient state.

The same explicit structural observation is stable across hash seeds and
unrelated working directories. Semantically equal occurrences remain distinct
unless the same existing exact identity and the same typed snapshot ref say
otherwise.

The private module exports nothing through `__all__`. It is not imported by
`pietto`, `pietto._project`, CLI, script IR, SQL renderers, or Project Explain.

## Focused Assurance Contract

The focused Slice 2 tests construct only the new structural carriers directly.
They are not authored Project IR E2E and invoke no Project IR builder.

They prove:

```text
cross-snapshot coordinate inequality
nominal ref-domain inequality
foreign-scope rejection
plan/output/use/input-slot separation
repeated producer uses remain repeated occurrences
role/source-order/input-ordinal ownership and survival
exact declaration/resolution/field anchors
duplicate/reordered coordinate rejection
concrete/non-concrete sum invariants
all five construction states with exact evidence
no fake non-concrete plan nodes
independent concrete/non-concrete coexistence
hash-seed and cwd independence
private/public/SQL/script RelationIR zero-delta
```

Tests use pytest-owned temporary directories and isolated subprocess
environments. They create no shared fixed path, persistent cache, global state,
or execution-order dependency and remain xdist/serial compatible.

## Integration Boundary And Non-goals

The following existing owners remain unchanged and authoritative:

```text
src/pietto/ir/model.py::RelationIR
ProjectModuleRelationSemanticFacts
ProjectResolvedModuleRelationReference
ProjectModuleDependencyFact
ProjectDeclarationOccurrenceIdentity
ProjectModuleRowFieldIdentity
aggregate/grouped facts
window semantic provenance
Phase 59 attribution/lineage identities
```

No authored project automatically produces any Slice 2 carrier. Slice 5 owns
canonical construction from existing Project semantic facts.

Slice 2 adds no operator algebra, cross-module plan construction, property
transfer, output model, grain/fanout, aggregate/window evaluation context,
verifier, pass manager, inspection, canonical bytes, JOIN, nested result,
correlation, recursion, optimizer, cost, physical planning, syntax, SQL,
diagnostic, CLI, JSON, public schema, Project Explain field, package-graph
behavior, persistent cache identity, backend, Rust implementation, release,
tag, signing, or attestation.

## Slice 3 Handoff

The exact next owner is:

```text
Phase 61 Slice 3 — Row/Output Model, Provided/Required Properties, Effects, And Estimate Boundary
```

Slice 3 may compose with the structural stage but must not collapse node,
output, use, slot, relation anchor, field anchor, exact property, estimate, or
effect domains. Slice 2 implements none of Slice 3.

## Gate Lifecycle And Publication

Gate 2 uses focused tests/Ruff/Pyright, one complete candidate review, at most
one same-root repair batch, one fresh rereview, the authoritative Python 3.13
validator, and package smoke because the private packaged module set changes.
Generated/golden auxiliaries are not locally required because their input
surfaces do not change.

Gate 3 rebinds the predecessor, stages exactly the sealed tree, makes one
ordinary commit, performs one fast-forward push, and observes the unique
natural exact-head CI without rerun or dispatch.

The exact commit subject is:

```text
Add Phase 61 Project IR structural model
```

The published PASS title is:

```text
PASS — PHASE61_SLICE2_PROJECT_IR_SCOPE_STAGES_OCCURRENCES_ANCHORS_CONSTRUCTION_STATES_END_TO_END
```

Successful natural exact-head CI completes Slice 2 without a status-only
follow-up commit. Slice 3 remains next / unstarted and is not authorized here.
