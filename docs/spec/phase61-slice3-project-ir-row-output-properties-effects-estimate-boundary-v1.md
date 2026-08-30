# Phase 61 Slice 3 Project IR Property Model v1

## Answer And Exact Owner

Slice 3 adds exactly one private semantic-property layer over the published
Slice 2 structural stage:

```text
current row/output semantic model
+ exact provided semantic properties
+ required consumer input properties
+ conservative effect/evaluation evidence
+ strict empty estimate boundary
```

The new production owner is:

```text
src/pietto/_project/project_ir_properties.py
```

It composes with, but does not modify, `ProjectIRStructuralStage` in
`src/pietto/_project/project_ir.py`.

| Surface | Slice 3 result |
| --- | --- |
| Private row/output/property production | `ADDED` |
| Slice 2 identity/topology changes | `0` |
| Logical operators/property transfer | `0` |
| Semantic-facts -> Project IR builder | `0` |
| Cross-module DAG construction | `0` |
| Function effect catalog/estimator/cost model | `0` |
| Grain comparison/fanout/JOIN/nesting/correlation/recursion | `0` |
| Parser/AST/SQL/CLI/public schema/Project Explain | `0` |
| Version | `0.1.0` |

Keep these domains nominally and structurally distinct:

```text
plan node != output value != use != input slot
relation anchor != field anchor
exact semantic property != required property
effect evidence != estimated statistic
```

## Starting Authority

| Fact | Value |
| --- | --- |
| Branch | `main` |
| HEAD | `a9725d46b1c4c79d5e1c78d79a0e042522e1edd3` |
| Tree | `ef4db5396f1a1ce436d003454d99f314c2cfcae1` |
| Parent | `6445ac9e5a844f8ac5b71fb01ffc573f5bc35de2` |
| Subject | `Add Phase 61 Project IR structural model` |
| Natural exact-head CI | `33305962868`, `push`, attempt `1`, successful |
| Divergence | `0/0` |
| Version | `0.1.0` |
| Tag/signature/Release | no HEAD tag, unsigned commit, no GitHub Release |

The unique successful natural CI on that exact Slice 2 publication establishes:

```text
Phase 61 = ACTIVE
Slice 1 = COMPLETED
Slice 2 = COMPLETED
Slice 3 = NEXT / NOT IMPLEMENTED
```

Mutable lifecycle prose lagged that live fact by design and is advanced in this
candidate without a status-only predecessor commit.

## Frozen Reader And Changed-path Closure

Fixed-point closure covered the new private source, immutable controlling spec,
product-test glob readers, mutable lifecycle owner, changed-path inventories,
exact Python source/test count readers, package module discovery, and readers of
those readers. The frozen allowlist is exactly:

```text
docs/roadmap.md
docs/spec/phase61-slice3-project-ir-row-output-properties-effects-estimate-boundary-v1.md
docs/status.md
src/pietto/_project/project_ir_properties.py
tests/test_active_phase_lifecycle.py
tests/test_phase61_slice3_project_ir_row_output_properties_effects_estimate_boundary.py
tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py
```

This is `A3/M4/D0`. Existing Phase 61 product and workflow readers discover the
new test through `test_phase61_slice*.py`; package smoke discovers private
modules dynamically. `tests/test_active_phase_lifecycle.py` remains the sole
direct reader of mutable `docs/status.md` and `docs/roadmap.md`. An eighth path
is `READER_CLOSURE_DRIFT`.

The clean pre-write focused baseline was `57 passed`.

## Live Semantic Authority Audit

| Subject | Existing exact authority | Slice 3 disposition |
| --- | --- | --- |
| Ordered row fields/types | `ProjectRowSchema`, `ProjectRowField`, `ProjectResolvedType`, `ProjectModuleRowFieldIdentity` | Compose exact identity plus typed field evidence; never rebuild from SQL or presentation output |
| Relation ownership/order | `ProjectDeclarationOccurrenceIdentity`; field owner and `field_position` | Require one relation owner and exact contiguous supplied order; never sort or deduplicate |
| Group/local grain evidence | concrete `ProjectModuleClauseDependencyFact(GROUP_KEY)` ledgers | Carry the exact source occurrences only; add no descriptor, comparison, FD, key, or fanout semantics |
| Relation-result ordering | concrete `ProjectModuleClauseDependencyFact(GROUPED_ORDER)` ledgers | Carry exact `OrderItem` occurrences only where this Project authority exists |
| Window-local ordering | `ProjectModuleWindowOutputFact` and `WindowExpressionAnalysis.order_binding_fact` | Retain as window evidence; never promote it to relation-result ordering |
| Evaluation policy | exact current `WindowFunctionFramePolicy` retained through `ProjectModuleWindowOutputFact` | Reuse that exact policy; create no second function-policy system |
| Exact cardinality bound | concrete retained aggregate/grouped clause readiness plus a semantically valid static `LIMIT` | Carry its exact integer upper bound; do not estimate |
| Multiplicity | published current relation law and absence of top-level `DISTINCT` | Current relation outputs carry BAG only |
| Free bindings | Slice 2 `free_outer_bindings = ()` | Carry an exact closed/empty property |
| Lineage/fact domains | Phase 59 relation/field occurrence lineage exists; no current fact-domain descriptor exists | Reserve the slot but do not invent a fact-domain value |
| Null extension | no current JOIN or outer-join operator | No positive null-extension carrier; explicit not-applicable is distinct from unknown |
| Effects | no target-independent Pietto determinism/may-error/side-effect/evaluation-count catalog | All current effect axes remain explicitly unknown |
| PostgreSQL volatility | backend/extension-catalog-specific authority | Do not import target-specific volatility into canonical Project IR |
| Estimates | no legitimate estimator, statistics provider, cost model, or memory model | Keep the current estimate boundary exactly empty |

No audit row requires a production owner outside this Slice. Therefore
`READER_CLOSURE_DRIFT` and `ARCHITECTURE_DECISION_REQUIRED` are not entered.

## Current Row And Output Model

`ProjectIRRowField` pairs one exact `ProjectIRFieldAnchor` with its existing
typed `ProjectRowField` evidence. Name agreement is checked, but the evidence
does not replace occurrence identity.

`ProjectIRRowShape` contains:

```text
one exact relation anchor
+ the exact concrete ProjectModuleRelationSemanticFacts authority
+ one exact ordered tuple of ProjectIRRowField
```

Every field must belong to that relation and retain its explicit
`field_position` order. Its field evidence must be the complete exact ordered
field collection retained by that concrete semantic authority. Formation does
not accept a caller-selected subset, sort, merge, or deduplicate. Two equal
semantic row shapes attached to two output occurrences remain two output
occurrences.

The current output sum has exactly two production variants:

| Variant | Current meaning |
| --- | --- |
| `ProjectIRScalarFieldOutput` | one current typed scalar field output |
| `ProjectIRRelationRowOutput` | one current BAG relation value plus exact row shape |

This avoids the permanent equation `Project output == ExpressionIR`. The union
is the typed future extension seam, but Slice 3 adds no `NestedRelationOutput`,
`RecordOutput`, or `CollectOutput` variant without a current producer.

Current Project IR remains closed:

```text
free_outer_bindings = ()
```

## Exact Provided Property Domain

`ProjectIRProvidedPropertySlot` defines separate slots for output shape,
cardinality bounds, multiplicity, relation-result ordering, local grain
evidence, fact domains, free bindings, null extension, and policy/evaluation.
Each provided carrier is owned by one typed current output occurrence.

Current positive carriers are:

| Carrier | Exact fact |
| --- | --- |
| `ProjectIRProvidedOutputShape` | the scalar or relation output's typed shape |
| `ProjectIRProvidedBagMultiplicity` | current relation multiplicity is BAG |
| `ProjectIRProvidedClosedBindings` | exact empty free bindings |
| `ProjectIRProvidedRelationOrdering` | complete grouped-order projection from the output's exact semantic authority |
| `ProjectIRProvidedLocalGrainEvidence` | complete group-key projection from the output's exact semantic authority |
| `ProjectIRProvidedCardinalityUpperBound` | exact retained static `LIMIT` upper bound |
| `ProjectIRProvidedEvaluationPolicy` | exact retained current window frame/evaluation policy |

`ProjectIRUnavailableProvidedProperty` carries an explicit `UNKNOWN` or
`NOT_APPLICABLE` state for a slot without manufacturing a positive fact.
Current typed outputs cannot claim unknown output shape.

The laws are:

```text
unknown != false
unknown != empty
unknown != estimate
not-applicable != unknown
BAG != SET
```

There is intentionally no SET carrier. No uniqueness or distinctness is
inferred from names, grouping appearance, semantic equality, or tuple order.

Local group-key evidence is not a general grain system:

```text
grain occurrence/evidence != grain descriptor
grain occurrence/evidence != required grain
grain occurrence/evidence != estimated cardinality
```

Slice 3 performs no Phase 62 grain comparison, FD/key reasoning, fanout, JOIN
cardinality, or multi-fact alignment.

Relation ordering and local-grain evidence reuse the same exact
`ProjectModuleRelationSemanticFacts` object owned by the output row shape, then
project the complete matching role collection. A caller-selected or rebuilt
partial fact tuple is not authority. Relation ordering accepts only the current
concrete grouped-order Project fact role. Freeze:

```text
window-local ordering != relation-result ordering
```

Source declaration order, tuple storage, hash iteration, and window-local
`ORDER BY` do not become a relation-result ordering property.

## Required Consumer Input Properties

Freeze:

```text
ProvidedProperties != RequiredInputProperties
```

`ProjectIRRequiredPropertySlot` reserves row shape, ordering, and local-grain
requirement domains. The only current concrete requirement carrier is
`ProjectIRRequiredRowShape`, because exact relation resolution already proves a
consumer input slot's target relation and row authority.

The carrier owns:

```text
exact consumer ProjectIRInputSlotOccurrence
+ exact required ProjectIRRowShape
+ exact ProjectIRResolvedRelationAnchor authority
```

Property-stage formation requires the same retained structural use and
consumer-side resolution authority. It does not compare the requirement with a
producer property, declare it satisfied, or transfer anything. Required
ordering and required local grain remain typed reserved slots with no current
carrier until Slice 4 establishes an operator requirement.

## Effect And Evaluation Evidence

`ProjectIREffectEvidence` is a separate carrier associated with one current
output. Its four nominal axes are:

```text
determinism / volatility
may-error behavior
side effects
evaluation-count sensitivity
```

Each axis has an explicit `UNKNOWN` state distinct from positive and negative
claims. Because live target-independent Pietto authority does not classify a
current expression on these axes, Slice 3 formation accepts only the four
explicit unknown values. It rejects attempts to assert deterministic,
non-volatile, cannot-error, side-effect-free, or evaluation-count-insensitive
without new authority.

The existing window frame policy is evaluation evidence, not an effect
classification. `ProjectIRProvidedEvaluationPolicy` retains it exactly without
creating a general function-policy catalog.

Freeze:

```text
effect evidence != exact provided property
effect evidence != occurrence identity
effects != estimates
```

Adding or omitting effect evidence cannot change a node, output, use, or slot
reference and does not define semantic equivalence.

## Strict Empty Estimate Boundary

`ProjectIREstimateBoundary` belongs to one exact snapshot scope and has a typed
statistics tuple. Current formation requires:

```text
Current estimate entries = 0
```

A non-empty tuple fails closed because Pietto has no legitimate current
estimate producer. The boundary may later be extended with separate typed
estimated row-count, selectivity, NDV, cost, and memory carriers; Slice 3 adds
none of them and avoids one object with unrelated optional statistic fields.

An estimate boundary is not accepted in the provided-property collection. No
estimate can participate in occurrence identity, exact property equality,
construction state, canonical semantic bytes, operator legality, or semantic
formation. The property-stage estimate field is explicitly excluded from
dataclass comparison and hashing.

## Property-stage Formation Laws

`ProjectIRPropertyStage` contains exactly:

```text
one exact ProjectIRStructuralStage
+ one same-scope ProjectIREstimateBoundary
+ exact ordered current output models
+ exact ordered provided properties
+ exact ordered required input properties
+ exact ordered effect evidence
```

Its output models must correspond one-for-one and by object identity with the
structural output tuple. Every modeled output must reuse the exact concrete
semantic evidence and root retained by its structural relation subject. It
holds no independent node/use/slot topology.

Formation fails closed on:

```text
foreign snapshot scope
wrong occurrence or carrier domain
property attached to a missing structural occurrence
detached, rebuilt, or partial semantic evidence
duplicate authority for one provided or required slot
reordered structural output/property coordinates
provided property presented as a requirement
requirement presented as a provided fact
estimate presented as exact evidence
invalid row or output ownership
required input without its exact retained structural use authority
duplicate or reordered effect attachment
```

Formation does not add, remove, reorder, or deduplicate plan nodes, outputs,
uses, or slots. It derives no reachability, selects no semantic winner,
constructs no operator, and implements no requirement satisfaction or transfer.

## Determinism Immutability And Privacy

All Slice 3 carriers are frozen, slotted, keyword-only dataclasses. Collections
are exact tuples supplied in explicit structural order. Formation does not use
unordered iteration to allocate identity and introduces no registry, singleton,
counter, UUID, random value, cwd lookup, hash identity, implicit current
project, resolver, or fallback.

The same explicit property stage has deterministic representation across hash
seeds and unrelated working directories. Snapshot scope keeps the stable
address-free representation established by Slice 2.

The module exports nothing through `__all__` and is not imported by `pietto`,
`pietto._project`, CLI, script IR, SQL emitters, or Project Explain.

## Focused Assurance Contract

Focused tests directly construct the Slice 2 and Slice 3 private carriers. They
are not authored Project IR E2E and invoke no Project IR builder.

They prove:

```text
exact ordered row fields retain identities and typed evidence
equal semantic row shape does not merge distinct output occurrences
current scalar and relation outputs are typed without speculative variants
BAG is explicit and no SET carrier exists
provided and required properties are nominally separate
required row shape is consumer-slot authority
unknown, not-applicable, and exact empty remain distinct
window-local order cannot form relation-result ordering
local grain evidence creates no descriptor/comparison/fanout
exact static LIMIT is not an estimate
the empty estimate boundary is legal and non-empty estimates fail closed
window evaluation policy reuses exact existing evidence
effect unknown cannot become purity or determinism
effects and estimates do not alter occurrence identity
foreign scope, missing attachment, duplicates, reorder, and invalid ownership fail closed
property composition leaves structural topology unchanged
hash seed and cwd do not affect formation
public, SQL, and script-level RelationIR behavior remain unchanged
```

Temporary paths are pytest-owned and subprocess environments are isolated.
There is no shared fixed path, persistent cache, global state, or execution-order
dependency; tests remain xdist/serial compatible.

## Integration Boundary And Non-goals

The following owners remain unchanged and authoritative:

```text
ProjectIRStructuralStage and all Slice 2 refs/anchors/occurrences/states
ProjectModuleRelationSemanticFacts
ProjectRowSchema and ProjectRowField
ProjectModuleRowFieldIdentity
ProjectModuleClauseDependencyFact
ProjectModuleWindowOutputFact and WindowFunctionFramePolicy
Phase 59 attribution and lineage
src/pietto/ir/model.py::RelationIR
```

No authored project automatically constructs any Slice 3 carrier. Slice 5
still owns canonical construction from semantic facts.

Slice 3 adds no logical operator, property transfer, compatibility/satisfaction
rule, builder, cross-module plan DAG, aggregate/window evaluation-context
construction, verifier, pass manager, inspection, canonical serializer, JOIN,
grain comparison, fanout, nesting, correlation, recursion, optimizer memo,
rewrite, costing, estimator, target plan, physical plan, parser/AST/grammar,
SQL, diagnostic, CLI, JSON, public schema, Project Explain field, package-graph
behavior, persistent identity, backend, Rust implementation, tag, Release,
signing, or attestation.

## Slice 4 Handoff

The only next owner is:

```text
Phase 61 Slice 4 — Current Logical Operator Algebra And Exact Property Transfer
```

Slice 4 may consume the separate structural, output, provided, required, effect,
and estimate domains. It must not merge them or retroactively replace exact
Slice 2 identity. Slice 4 remains next / unstarted and is not implemented by
this contract.

## Gate Lifecycle And Publication

Gate 2 uses focused tests, Ruff, and Pyright, performs one complete candidate
review, permits at most one same-root repair batch, performs a fresh rereview,
and runs exactly one authoritative validator:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Package smoke is locally required because the private packaged module set
changes. Generated and golden auxiliaries are not locally required because no
input surface changes; natural CI still runs them.

Gate 3 rebinds the predecessor, stages exactly the sealed tree, makes one
ordinary commit, performs one fast-forward push, and observes the unique
natural exact-head CI without dispatch or rerun.

The exact commit subject is:

```text
Add Phase 61 Project IR property model
```

The published PASS title is:

```text
PASS — PHASE61_SLICE3_PROJECT_IR_ROW_OUTPUT_PROPERTIES_EFFECTS_ESTIMATE_BOUNDARY_END_TO_END
```

Successful natural exact-head CI completes Slice 3 without a status-only
follow-up commit. Slice 4 remains next / unstarted.
