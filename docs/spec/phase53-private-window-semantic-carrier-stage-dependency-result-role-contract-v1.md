# Phase 53 Slice 6 Private Window Semantic Carrier, WINDOW Stage, Dependency, And Result Roles v1

## Status And Slice Identity

This contract defines the private, inert carrier foundation for Phase 53 Slice
6. Phase 53 remains active and Slice 6 remains unstarted until a separately
authorized Gate 3 commit, normal push, and exact-head natural CI success.

The implementation owns no accepted language behavior. It preserves all
current accepted and rejected programs, diagnostics, output bytes, public
schemas, runtime behavior, and database behavior.

## Existing Window AST And Identity Authority

The existing frozen `WindowExpr`, `WindowSpec`, `OrderItem`, `CallExpr`, and
private `WindowFunctionIdentity` remain authoritative and byte-identical.
`WindowSpec` preserves source order for partition and order expressions, and
`SelectItem` continues to own the explicit output alias.

Slice 6 does not change grammar, generated files, AST construction, parser
behavior, or the current fail-closed handling of window expressions.

## Existing Generic And Nullability Authority

The existing generic compatibility and signature-result nullability modules
remain the only owners of binding and formula evaluation. Slice 6 may carry an
already resolved `ValueType`; it neither binds a generic signature nor
evaluates a nullability formula.

`EffectiveNullability.UNKNOWN`, `ValueTypeKind.UNKNOWN`, and SQL three-valued
logic remain distinct. An unknown result is not converted to nullable.

## Private Module Placement And Layering

`pietto.semantic.window_semantics` owns only language-semantic occurrence,
stage, identity, availability, and unsupported evidence.

`pietto._project.window_semantics` owns only project result identity,
dependency occurrence and edge evidence, immediate provenance, and their
atomic project fact.

The semantic module imports no `_project` module. Neither module changes a
package `__init__`, and both define an empty `__all__`.

## Semantic Carrier Architecture

The exact semantic inventory is:

```text
WindowExpressionStage
WindowOccurrenceIdentity
WindowResultAvailabilityKind
WindowResultAvailability
WindowExpressionSemanticFact
WindowExpressionUnsupported
```

Every dataclass is frozen, slotted, and keyword-only. The module owns no
registry, cache, callback, process counter, evaluator, or integration hook.

## WINDOW Stage Contract

`WindowExpressionStage` contains only `WINDOW = "WINDOW"`.
`WindowExpressionSemanticFact.stage` is fixed to that value. The stage is a
standalone private description: it is not a Phase 52 capability stage, an
analyzer inference result, or a legality decision.

## Result Availability And Type-nullability Posture

`WindowResultAvailabilityKind` has exact stable values `concrete`, `unknown`,
`deferred`, and `blocked`.

A concrete availability carries an exact existing `ValueType` in
`value_type`. Its kind must be `KNOWN`, its nullability must be `NON_NULL` or
`NULLABLE`, and it carries no reason.

Every non-concrete availability carries no value and requires a nonblank
private reason. No availability creates a type, binds a generic, evaluates a
formula, or changes current compiler inference.

## Stable Window Occurrence Identity

`WindowOccurrenceIdentity` carries exactly `source_id`, `relation_name`,
`selected_output_ordinal`, and `span`.

The two names are exact nonblank strings. The ordinal is an exact nonnegative
integer and rejects `bool`. The span is an exact existing `Span`; when its path
is present it equals `source_id`. Equality and hashing use the complete
structure. UUIDs, object identity, randomness, registries, and global counters
are forbidden.

## Project Result Identity And Output Alias Contract

`WindowResultIdentity` carries exactly an owning `TableDef | QueryDef`, an
explicit nonblank `output_name`, the semantic occurrence, and the fixed
`ProjectRowResultRole.WINDOW_RESULT` role.

The definition name equals the occurrence relation name. Output order is the
occurrence selected-output ordinal. No implicit alias, schema insertion,
final-order visibility, legality, or lowering follows from this identity.

## Result-role Architecture

The unique existing `ProjectRowResultRole` appends only:

```text
WINDOW_RESULT = "window_result"
```

Existing members and order remain unchanged. No current builder assigns the
new role, and no public serializer exposes it.

## Dependency-role Inventory

The exact ordered private inventory is:

```text
RELATION_INPUT = "relation_input"
WINDOW_ARGUMENT = "window_argument"
WINDOW_DEFAULT = "window_default"
WINDOW_PARTITION = "window_partition"
WINDOW_ORDER = "window_order"
```

`WINDOW_FRAME` is Phase 60-owned and absent. `RESULT_ROLE` is represented by
the result identity and is not a dependency role.

## Occurrence Evidence And Deduplicated Edge Contract

`WindowDependencyOccurrence` carries `global_ordinal`, `role_ordinal`, `role`,
an existing `ProjectRowDependencyNode` target, and an exact `SourceLocation`.
The containing input is an exact tuple. Global and role-local ordinals are
zero-based and contiguous.

Role blocks occur only in enum order. Repeated source occurrences remain in
the occurrence tuple. `deduplicate_window_dependency_edges` traverses that
tuple once and returns the first `(role, target)` occurrence of each pair.
The same target under different roles remains distinct. No set or mapping
iteration controls output order.

## Relation-input And Zero-argument Readiness

`RELATION_INPUT` requires an existing relation-input dependency node. A
zero-argument window call requires exactly one relation-input occurrence and
edge; partition and order dependencies may coexist.

A nonzero-argument call forbids relation-input occurrences and edges. These
rules are construction readiness only and do not register a ranking function.

## Nested And Same-select Non-representability

All non-relation roles accept only existing `UPSTREAM_FIELD` or `LET_BINDING`
targets. `OUTPUT_FIELD` is forbidden. Consequently, same-select result
dependencies and nested-window dependencies cannot be represented by these
carriers and fail closed.

## Provenance And Derived-origin Contract

Window result facts reuse only
`ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION`. The provenance location
equals the occurrence span converted without normalization to an existing
`SourceLocation`. An immediate `ProjectSymbol` may be retained when supplied.

No new provenance kind or full lineage carrier is introduced.

## Project Fact Composition And Ordering

`WindowResultProjectFact` carries exactly `semantic_fact`, `result_identity`,
`dependency_occurrences`, `dependency_edges`, and `provenance`.

It requires matching semantic and output occurrences, consistent relation
identity, exact tuple/member types, contiguous source ordering, exact
first-occurrence edge derivation, the relation-input readiness rule, and
derived-expression provenance at the occurrence location.

## Constructor And Failure Boundary

Malformed member or container types raise `TypeError`. Well-typed invariant
conflicts raise `ValueError`. A structurally valid but unavailable semantic
state uses `WindowExpressionUnsupported` or a non-concrete availability.

No constructor emits, catches, replaces, or reorders a public diagnostic.

## Current Analyzer Catalog And Capability Non-integration

Slice 6 adds no analyzer branch, catalog entry, capability domain, support
fact, disposition, signature, lookup behavior, or current stage inference.
It does not register `row_number` or any other window function and does not
traverse partition or order expressions for legality.

Current unknown-function behavior and diagnostic order remain unchanged.

## Project-model Non-integration

No field or mapping is added to `ProjectSemanticModel`. Project checking,
schema propagation, dependency graph population, lineage population, and
Project JSON v2 remain unchanged. The project carrier module is standalone
ownership infrastructure only.

## Public Privacy And Serialization Boundary

The new modules export nothing through package roots. CLI JSON v1, Project
JSON v2, Semantic Metadata Artifact v1, explain output, public SQL APIs, and
the public Python API gain no symbol or field.

No package version, dependency, lockfile, workflow, fixture, golden, tag, or
Release changes.

## Positive Carrier Matrix

Coverage includes carrier shapes, exact enum values, structural identity,
hashing and repeatability, concrete and non-concrete availability, fixed
WINDOW stage, explicit result aliases, every dependency role, preserved
duplicate occurrences, first-edge deduplication, cross-role distinction,
zero-argument relation input, derived provenance, and future Slice 7/Slice 12
construction readiness.

## Negative And Fail-closed Matrix

Coverage rejects wrong types, blank text, bool or negative ordinals, span and
identity mismatch, substituted fixed stage or result role, invalid role-target
pairs, noncontiguous or reordered occurrences, incorrect edges, missing or
extra relation input, output-field dependencies, nested/same-select attempts,
invalid provenance, unknown-as-nullable substitution, and public integration.

## Grammar AST Generated Generic Nullability IR SQL And Behavior Immutability

Required mutation counts are zero for grammar, generated artifacts, AST,
builder, parser API, window identity, generic compatibility, nullability
formulas, existing window behavior, IR, SQL, CLI, and public serializers.

No ANTLR or golden regeneration is authorized.

## Reader Hash Inventory And Repository-state Closure

The Gate 2 state is exactly `A4/M54/D0`: 54 tracked modifications and four
authorized untracked additions, with no deletion, rename, outside path, or
staged file. Reader hashes, aggregate digests, inventories, selector identity,
and lifecycle literals migrate without weakening equality assertions.

The escaping Slice 5 nullability reader remains a 38-function, 145-item whole
module in the focused selector.

## Validation Depth-one CI And Gate 3 Publication

Gate 2 validates 775 focused items and a dirty broad suite of 6682 passed with
185 clean-only nodes deselected. Clean depth-one CI projects 6867 passed on
each Python job, eight generated files byte-exact, and 37 goldens.

Gate 2 leaves all files unstaged and uncommitted. Gate 3 alone may stage the
exact 58 paths once, create one commit, push once, and observe exact-head
natural CI.

## Deferred Ownership And Stop Conditions

Window function registration and semantic binding remain future slices.
Frames remain Phase 60-owned. Full lineage, project-model population, IR/SQL
lowering, public output, runtime, and database behavior remain deferred.

STOP is required if implementation needs another repository path, another
stage/result/dependency/provenance kind, changed occurrence identity, public
or compiler integration, changed test arithmetic, changed focused/overlay
identity, or a second write formatter.
