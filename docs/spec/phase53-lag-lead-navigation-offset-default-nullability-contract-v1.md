# Phase 53 lag / lead Navigation, Offset, Default, And Nullability Contract v1

## Status And Authority

Phase 53 Slice 12 is the bounded semantic and private-project implementation
slice for `lag` and `lead`. The final Gate 0/Gate 1 report and its immutable
full plan are the design authority. This document records that selected
contract without widening it.

Slice 12 remains unpublished until a separately authorized Gate 3 commit,
normal push, and exact-head natural CI success. Gate 2 does not stage, commit,
push, tag, release, or mutate CI.

## Exact Function Identities

Only exact lowercase unqualified `NameExpr` identities `lag` and `lead` are
recognized. Their namespace is empty and their role remains the private
`WINDOW_FUNCTION` role already carried by `WindowExpr`.

Dotted identities, differently cased spellings, aliases, normalization,
registries, caches, callbacks, and public identity hierarchies are not added.
Unsupported identity spellings retain `PIE-S2103` at the call span.

## Exact Arity And Positional Shape

The accepted calls are exactly:

```pietto
lag(value)
lag(value, offset)
lag(value, offset, default)
lead(value)
lead(value, offset)
lead(value, offset, default)
```

Zero arguments and more than three arguments fail with `PIE-S2104` at the call
span. The syntax is positional: a supplied default cannot omit the offset.

## Value Expression Subset

The first argument accepts one bare direct input field, one immediate
two-component input-qualified field, or one `Bool`, `Text`, `Int`, `Float`, or
`NULL` literal. The existing row-expression resolver infers each admitted
non-`NULL` expression exactly once.

Original or transitive qualifiers, let or selected aliases, aggregates,
windows, calls, unary and binary expressions, comparisons, `between`,
`is null`, parameters, and computed expressions are outside this subset.
Unknown fields retain `PIE-S2102` at the field span; unsupported shapes and
nonconcrete value facts use `PIE-S2104` at the call span.

Concrete `BUILTIN`, `ENUM`, and `SHAPE` field identities are admitted. Unknown
type, unknown effective nullability, and `TYPE_ALIAS` values fail closed.

## Offset Semantics

An omitted offset has effective value `1`. A supplied offset must be an exact
nonnegative `Int` literal. Offset `0` is legal and denotes the current row.
Positive offsets have no additional semantic maximum beyond the existing
4096-character numeric-literal boundary and Python integer representation.

Negative unary integers, `Bool`, `Float`, `Text`, `NULL`, fields, parameters,
calls, and every nonliteral offset shape fail with `PIE-S2104`. Offset
validation precedes default analysis. The offset neither binds generic `T`,
contributes result nullability, nor creates a project dependency.

## Default Expression Subset

The optional third argument accepts exactly the same bounded field and scalar
literal subset as the value. A direct field uses project dependency role
`WINDOW_DEFAULT`; literals and `NULL` are dependency-free. Backend evaluation
timing is not specified in this slice.

## Exact Generic Compatibility

Both functions use one private `GenericSignature` with unconstrained type
variable `T`: required `T` value, optional `Int` offset with omitted default,
optional `T` default with omitted default, and result `T`.

Compatibility is exact logical name plus exact `TypeKind`. There is no
coercion, numeric promotion, least-upper-bound selection, alias expansion, or
backend conversion. `NULL` is nonbinding: one concrete value or default binds
`T`; a concrete peer makes `NULL` compatible. A `NULL` value with omitted
default and every all-`NULL` supplied pair leave `T` unbound and fail with
`PIE-S2104`.

## Complete Result Nullability

For omitted or positive offsets, boundary rows can exist. The formula is the
existing `AnyOfFormula` of `AnyNullableFormula((0, 2))` and
`NullableIfDefaultOmittedFormula(2)`.

For offset zero, a concrete value uses `SameAsArgumentFormula(0)`. An always
`NULL` value whose `T` is bound by a concrete default uses
`AlwaysNullableFormula`; the default is not selected at offset zero.

The complete table uses `N` for non-null, `Q` for nullable, `A` for always
`NULL`, `O` for omitted, and `R` for rejected unbound `T`:

| offset | value | default | result |
|---|---|---|---|
| omitted | N | O | Q |
| omitted | Q | O | Q |
| omitted | A | O | R |
| zero | N | O | N |
| zero | Q | O | Q |
| zero | A | O | R |
| zero | N | N | N |
| zero | N | Q | N |
| zero | N | A | N |
| zero | Q | N | Q |
| zero | Q | Q | Q |
| zero | Q | A | Q |
| zero | A | N | Q |
| zero | A | Q | Q |
| zero | A | A | R |
| positive | N | O | Q |
| positive | Q | O | Q |
| positive | A | O | R |
| positive | N | N | N |
| positive | N | Q | Q |
| positive | N | A | Q |
| positive | Q | N | Q |
| positive | Q | Q | Q |
| positive | Q | A | Q |
| positive | A | N | Q |
| positive | A | Q | Q |
| positive | A | A | R |

## Mandatory Local Order

Both identities require a nonempty local `order by:` block. They reuse the
completed direct-field order binder, source order, duplicate preservation,
nullable-field acceptance, omitted or explicit `asc`/`desc`, and effective
direction derivation. No frame syntax or behavior is added.

## Partition And Direction Reuse

Partition remains optional and reuses the completed direct-field partition
binder. Multiple partition and order keys preserve source order and duplicate
occurrences. The complete partition tuple is validated before mandatory local
order, and order is validated before value, offset, and default arguments.

## Peer-insensitive Navigation

Navigation is peer-insensitive. It records no peer key and claims no runtime
peer comparison, partition size, boundary count, uniqueness, total-order
proof, hidden tie-breaker, automatic primary-key append, collation behavior,
or null-order behavior.

## Validation And First-error Order

The deterministic validation order is:

1. identity;
2. arity;
3. selected alias and placement;
4. relation context;
5. exactly one window output;
6. partition shape and binding;
7. mandatory local order;
8. order shape and binding;
9. direction;
10. value shape and inference;
11. offset shape, type, and value;
12. default shape and inference;
13. exact generic compatibility or unbound `T`;
14. nullability;
15. semantic fact;
16. project fact.

No diagnostic code is added. `PIE-S2102`, `PIE-S2103`, `PIE-S2104`, and the
existing `PIE-I1000` boundary are sufficient.

## Private Semantic Carriers

`NavigationDirection`, `NavigationOffsetFact`, `NavigationDefaultFact`, and
`NavigationWindowSemanticFact` are private, immutable, slotted, keyword-only,
hashable carriers. The navigation fact retains the exact value expression and
type, always-`NULL` evidence, offset/default facts, `SignatureMatch`,
`NullabilityEvaluationMatch`, and source spans.

`WindowExpressionAnalysis` appends one optional navigation sibling while
preserving the existing ranking and distribution family shapes. Every family
fact shares the exact same semantic core.

## Private Navigation Analysis

`pietto.semantic.window_navigation_analysis` owns exact identity recognition,
bounded argument inference, offset validation, generic binding, and
nullability evaluation. The common analyzer continues to own alias, relation,
single-window, partition, and order validation. The modules remain acyclic,
stateless, unexported, and free of persistent caches.

## Project Dependency Roles

Project occurrences retain exact role-block order:

1. `RELATION_INPUT`;
2. `WINDOW_ARGUMENT`;
3. `WINDOW_DEFAULT`;
4. `WINDOW_PARTITION`;
5. `WINDOW_ORDER`.

Direct value and default fields create their corresponding occurrences.
Literals, `NULL`, and offsets create none. Occurrences preserve spans,
duplicates, source order, contiguous global ordinals, and contiguous
role-local ordinals. Edges deduplicate only the first identical `(role,
target)` pair.

Any argument or default field suppresses `RELATION_INPUT`. A navigation call
with dependency-free value/default expressions receives exactly one fallback
relation-input occurrence and edge.

## Persistence And Row-schema Boundary

Navigation facts remain transient. Neither `SemanticModel` nor
`ProjectSemanticModel` persists them. No row schema, selected-output alias,
downstream visibility, persistent graph, lineage, metadata, serializer, CLI,
or public API is changed.

## IR SQL And Backend Boundary

Slice 12 adds no IR, SQL, backend, fixture, or golden behavior. Window lowering
continues to fail closed through `PIE-I1000`; PostgreSQL and private MySQL
renderers remain unreachable for navigation windows. Backend offset/default
evaluation details are deferred.

## Frontend Package And Release Boundary

Grammar, generated parser files, AST, parser, builder, dependencies,
`pyproject.toml`, lockfiles, workflows, package version `0.1.0`, tags, releases,
and publication operations are unchanged.

## Later Slice Boundary

Slice 13 retains `first_value` and `last_value`. Slice 14 retains bounded
`nth_value`, value families, and frame interaction. Slice 15 retains IR and
independent backend lowering. Slice 16 retains hardening and completion lock.
None is activated by Slice 12.

## Gate 2 Validation Contract

Gate 2 is exactly `A3/M62/D0`, one write-mode Ruff invocation over 63 paths,
381 new items, 3488 focused items, 9395 dirty passes with 185 deselections,
9580 clean passes, 8 generated files, and 37 goldens. Validation uses the
audited two-wheel offline wheelhouse and a fresh external cache.

## Stop Conditions

STOP on authority or baseline drift, any path outside the allowlist, deletion,
new diagnostic code, product or architecture redesign, inventory or selector
drift, a second write formatter, online fallback, persistent/public/IR/SQL
widening, nonempty source index, or any staging, commit, push, tag, release,
PR, merge, or CI mutation.
