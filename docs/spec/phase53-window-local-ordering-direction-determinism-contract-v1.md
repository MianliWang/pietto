# Phase 53 Window-local Ordering, Direction, Mandatory-order Policy, And Determinism Contract v1

## Status And Authority

This contract is the Phase 53 Slice 11 Gate 2 implementation boundary. Slice 11 remains UNSTARTED through Gate 2. `COMPLETED requires separately authorized Gate 3 and exact-head natural CI`. The trusted implementation base is the approved Slice 10 publication state, and this slice neither publishes nor changes lifecycle state.

## Exact Function And Source Subset

The source subset is exactly one direct selected, aliased window expression in an otherwise non-aggregate single-input table or query. Its local order accepts the existing direct-field forms described below. The completed identities and their unchanged result types are:

### row_number

`row_number()` returns non-null `Int` and remains peer-insensitive.

### rank

`rank()` returns non-null `Int` and uses every local-order expression as its peer key.

### dense_rank

`dense_rank()` returns non-null `Int` and uses every local-order expression as its peer key.

### percent_rank

`percent_rank()` returns non-null `Float` and uses every local-order expression as its peer key.

### cume_dist

`cume_dist()` returns non-null `Float` and uses every local-order expression as its peer key.

### ntile

`ntile(positive_integer_literal)` returns non-null `Int` and remains peer-insensitive.

## Multi-key Local-order Cardinality

Each identity accepts an `arbitrary non-empty source-ordered tuple` of local-order keys. One, two, three, and longer tuples use the same rule. Zero keys fail closed through the existing semantic diagnostic posture.

## Direct-field Binding And Visibility

Every key is exactly a bare field or an immediate-input-qualified field. Binding reuses the existing row-expression resolver exactly once per key, in source order. Computed expressions, literals, calls, nested window results, selected aliases, let names, aggregate results, original-source qualifiers through an upstream relation, and three-part names remain unavailable. No same-select or downstream visibility is introduced.

## Direction And Explicitness

The source direction is preserved as `None`, `asc`, or `desc`; `omitted direction is preserved and is effectively ascending`. A sibling binding records the derived effective direction without erasing whether direction was explicit. Field binding for the complete tuple precedes direction validation.

## Mandatory-order Policy

`all six completed identities require local order`. There is no identity-specific or backend-specific exception, and no implicit order is synthesized.

## Duplicate Keys And Source Order

Duplicates are legal and `duplicate local-order occurrences are preserved`. Semantic bindings and project occurrences retain source order, spans, directions, and distinct occurrence ordinals. Dependency edges alone continue to deduplicate by first `(role, target)` occurrence.

## Structural Determinism And Total-order Boundary

The compiler guarantees deterministic traversal, source-order preservation, first-error diagnostics, structural fact equality and hashing, and project occurrence order. `structural ordering does not prove runtime total order, uniqueness, or tie resolution`. Ties remain permitted; no key uniqueness analysis, hidden tie-breaker, primary-key append, or backend execution guarantee is added.

## Null Ordering And Collation

Concrete nullable direct fields remain structurally legal and retain their `ValueType`. `NULLS FIRST`, `NULLS LAST`, and collation syntax remain unsupported. Pietto defines no null-placement, locale, ICU, or backend collation default in this slice.

## Orderability And Capability Boundary

Current concrete direct-field acceptance is preserved without a new orderability matrix, coercion, promotion, or backend-dependent rule. `Phase 52 capability lookup remains descriptive rather than legality authority`.

## Peer And Distribution Semantics

`rank`, `dense_rank`, `percent_rank`, and `cume_dist` use every source-ordered local-order expression, including duplicates, as the peer key; direction is not part of peer equality. `row_number` and `ntile` remain peer-insensitive. Distribution structural order uses the same complete expression tuple. Partition keys never enter peer keys, and no runtime peer comparison is performed.

## Validation Order And Diagnostics

First-error validation is: exact identity; signature arity; alias and relation context; exactly one window output; partition shapes; partition schema and bindings; non-empty order; all order shapes; concrete order schema; all field bindings; all directions; `ntile` literal; result typing; then fact construction. Existing `PIE-S2103`, `PIE-S2104`, resolver-owned `PIE-S2102`, and IR-owned `PIE-I1000` remain the only applicable codes. No cascade diagnostic or new code is added.

## Project Dependencies Occurrences And Edges

Successful project occurrences are ordered `RELATION_INPUT`, then every `WINDOW_PARTITION`, then every `WINDOW_ORDER`. Global and per-role ordinals are contiguous. Each order occurrence uses its expression span; direction creates no node, occurrence, or edge. Edge order is the first occurrence of each `(role, target)` pair. Result identity and `DERIVED_EXPRESSION` provenance are unchanged.

## Private Order-binding Carrier And Composite Analysis

`WindowOrderFieldBinding` and `WindowOrderBindingFact` are private frozen, slotted, keyword-only, hashable sibling carriers in `semantic/window_semantics.py`. `semantic/window_order_analysis.py` owns only the private two-pass binding helper. `WindowExpressionAnalysis` appends an object-identical order sibling after its existing core, family, and partition fields. These modules publish no export, cache, callback, registry, IR dependency, or persistent model field.

## Slice 12 Reuse And Deferred Ownership

Slice 12 may later reuse the non-empty typed order tuple, source/effective direction, and project order occurrences only after separate authorization. `Slice 12 navigation behavior remains unimplemented`; this slice adds no `lag`, `lead`, offset, default, frame, navigation nullability, or execution behavior.

## Persistence Row-schema IR SQL And Public Boundaries

The new evidence is transient and private. It does not enter `SemanticModel`, `ProjectSemanticModel`, row schema, dependency graph persistence, lineage persistence, IR, PostgreSQL SQL, private MySQL SQL, CLI text, CLI JSON v1, Project JSON v2, Metadata Artifact v1, package exports, grammar, generated artifacts, fixtures, or goldens. Window expressions still fail IR lowering with `PIE-I1000` because no published expression value type exists.

## Reader Closure Validation And Publication

Gate 2 migrates the complete approved reader closure, runs exactly one write-mode formatter over the frozen manifest, and validates the exact focused and dirty-overlay selectors before broad repository gates. Gate 2 does not stage, commit, push, tag, release, or mutate CI. Gate 3 may use one literal staging operation, one commit with subject `Add Phase 53 window-local ordering and direction`, one normal push, and observation of exact-head natural CI only.

## Stop Conditions

Stop on authority or baseline drift, an allowlist escape, a required protected-surface change, a public or persistent model requirement, a new diagnostic requirement, a second write formatter, an unexpected collected-item count, any validation failure that cannot be repaired inside the approved same-goal loop, or any need to mutate Git/GitHub lifecycle state. No such condition may be silently reinterpreted as implementation authority.
