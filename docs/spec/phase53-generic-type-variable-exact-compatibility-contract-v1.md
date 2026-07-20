# Phase 53 Slice 4 Generic Type-variable, Constraint, And Exact Compatibility Foundation v1

## Status And Slice Identity

Phase 53 is `ACTIVE`; Slices 1 through 3 are `COMPLETED`; Slice 4 remains
`UNSTARTED` throughout Gate 2. This slice adds a private, standalone exact
generic-compatibility foundation plus its contract and tests. It does not
complete Slice 4, and it does not authorize Slice 5 or any behavior slice.

Gate 2 leaves the exact `A3/M49/D0` result unstaged and uncommitted with an
empty index. Only a separately authorized Gate 3 may publish the result and
mark Slice 4 `COMPLETED` after exact-head natural CI succeeds.

## Existing Logical-type And Evidence Authority

The current semantic carrier is `ResolvedType(name, kind, definition)`, where
the optional definition is source-owned. Generic compatibility therefore uses
a separate source-independent identity. Existing alias expansion remains
outside this module, `DecimalPrecisionScale` remains separate, and
`EffectiveNullability.UNKNOWN`, `TypeKind.UNKNOWN`, and SQL three-valued
`UNKNOWN` remain distinct.

The exact builtin names are `Any`, `Bool`, `Bytes`, `Date`, `Decimal`,
`Float`, `Int`, `Json`, `Text`, `Timestamp`, and `UUID`. Current scalar,
distinct-equality, extrema, and numeric-aggregate evidence establishes only
the explicit matrix in this document.

## Private Module And No-integration Boundary

The implementation lives only in
`src/pietto/semantic/generic_compatibility.py`. It declares
`__all__: tuple[str, ...] = ()`, has no mutable registry or cache, and imports
only the standard library and `TypeKind` from the existing semantic model.

It does not import or modify analyzer, catalog, capability, window, project,
IR, SQL, CLI, serializer, package, workflow, grammar, AST, parser, or generated
surfaces. It registers no callable and changes no accepted or rejected Pietto
program.

## Source-independent Logical-type Identity

`LogicalTypeIdentity(name, kind)` is frozen, slotted, keyword-only, immutable,
and hashable. Equality, hashing, and representation depend only on the exact
case-preserving `(name, kind)` pair. It contains no source definition, span,
nullability, Decimal precision/scale, backend type, or dialect fact.

Names use ASCII `[A-Za-z_][A-Za-z0-9_]*`. Kinds are limited to exact
`BUILTIN`, `ENUM`, and `SHAPE`. `TYPE_ALIAS` and `UNKNOWN` are rejected.
`BUILTIN` accepts only the eleven exact catalog names. Enum and shape names
remain source-independent declared identities. Alias expansion is a caller
responsibility and is not performed here.

## Exact Type-variable And Constraint Carriers

`TypeVariable(name, constraints)` preserves one ASCII identifier and an exact
ordered tuple of exact `TypeConstraint` members. Empty constraints are valid;
duplicates are rejected. Case and declared constraint order are preserved.

`TypeConstraint` is a `StrEnum` in exact order: `SCALAR = "scalar"`,
`COMPARABLE = "comparable"`, `ORDERABLE = "orderable"`, and
`NUMERIC = "numeric"`. The tags are independent. No hierarchy, trait system,
or implication is encoded.

## Complete Type-by-constraint Matrix

| identity | SCALAR | COMPARABLE | ORDERABLE | NUMERIC |
| --- | ---: | ---: | ---: | ---: |
| Any | true | false | false | false |
| Bool | true | true | false | false |
| Bytes | true | false | false | false |
| Date | true | true | true | false |
| Decimal | true | true | true | true |
| Float | true | true | true | true |
| Int | true | true | true | true |
| Json | true | false | false | false |
| Text | true | true | false | false |
| Timestamp | true | true | true | false |
| UUID | true | true | false | false |
| any ENUM | false | false | false | false |
| any SHAPE | false | false | false | false |
| unresolved `None` | false | false | false | false |

`supports_constraint(logical_type, constraint)` validates exact member types,
uses only this immutable matrix, and returns `False` for `None`. It does not
consult capability lookup, infer from type names, infer a hierarchy, or use a
backend or dialect.

## Signature Type-expression Carriers

`ConcreteTypeExpression(logical_type)` holds one exact
`LogicalTypeIdentity`. `VariableTypeExpression(name)` holds one validated
ASCII variable reference. `TypeExpression` is exactly their union and is used
for both parameters and results.

There are no union types, wildcards, callables, variadics, spans, nullability
payloads, backend payloads, or implicit aliases in these carriers.

## Ordered Parameter And Optional-default Contract

`SignatureParameter(position, type_expression, optional=False, default=None)`
is frozen, slotted, keyword-only, and hashable. Position is an exact
nonnegative `int`; `bool` is rejected. Type expression members are exact.
Optional is an exact `bool`.

`ParameterDefault` has the sole value `OMITTED = "omitted"`. A default marker
requires `optional=True`; an optional parameter with `default=None` is valid.
Parameters have no names, keyword binding, runtime values, or variadic form.
Omitted positions are represented as ascending zero-based positions.

## Generic Signature And Result Contract

`GenericSignature(type_variables, parameters, result)` preserves exact
tuples, declaration order, and one exact result expression. Type-variable
names are unique. Parameter positions are exactly `0..n-1`, and optional
parameters form one trailing suffix.

Every variable reference is declared, and every declared variable appears in
at least one parameter. A result-only variable is rejected. A variable used
only by an optional parameter and the result is valid at construction and can
produce `UnboundResult` when omitted. A zero-parameter concrete-result
signature is valid. No callable, catalog, nullability, stage, clause, dialect,
or backend identity is stored.

## Constructor Validation And Exception Policy

All data carriers use `@dataclass(frozen=True, slots=True, kw_only=True)`.
Wrong exact scalar, container, enum, union-member, or carrier member types
raise `TypeError`. Invalid names, duplicate declarations or constraints,
position gaps, optional-order violations, undeclared references, unused
variables, inconsistent mismatch evidence, and inconsistent selection
outcomes raise `ValueError`.

Valid carriers bound to incompatible arguments never raise for
incompatibility. They return structured mismatch evidence. Exact tuples are
not normalized from lists, sets, mappings, strings, or other iterables.

## Exact Same-type Binding Algorithm

`bind_signature(signature, arguments)` first validates an exact signature,
an exact argument tuple, and exact `LogicalTypeIdentity | None` members. It
then computes minimum and maximum arity and returns `ArityMismatch` when the
count is outside that range.

Supplied parameters are visited in ascending position. `None` returns
`UnresolvedArgument`. Concrete parameters require exact identity equality.
The first variable occurrence records its identity and position; repeated
occurrences require the same exact identity. Only after all supplied equality
checks succeed are constraints evaluated in first-bound variable order and
each variable's declared constraint order. The first false matrix entry
returns `ConstraintMismatch`.

The binder records omitted optional positions without fabricating a type.
A concrete result resolves directly. A variable result resolves from its
existing binding or returns `UnboundResult`. Success returns `SignatureMatch`.

## Binding Match And Mismatch Evidence

The immutable evidence family is `TypeVariableBinding`,
`ConstraintEvidence`, `ArityMismatch`, `UnresolvedArgument`,
`ConcreteTypeMismatch`, `RepeatedVariableMismatch`, `ConstraintMismatch`,
`UnboundResult`, `SignatureMatch`, and `SignatureUnsupported`.
`SignatureBindingResult` is exactly `SignatureMatch | SignatureUnsupported`.

Bindings use first-binding parameter order. Constraint evidence uses that
binding order and then declaration order. Omitted positions are unique and
ascending. A mismatch result contains the first failure selected by the exact
algorithm. All values are structural, immutable, hashable, and
source-independent.

## Ordered Overload Collection

`OverloadSet(signatures)` accepts one exact tuple of exact
`GenericSignature` members. It preserves declaration order, permits an empty
tuple, and deliberately permits structural duplicate rows. It performs no
deduplication or sorting and stores no callable name, namespace, priority,
cost, source, catalog, or backend fact.

## Match Unsupported And Ambiguous Selection

`OverloadOutcome` has exact values `MATCH = "match"`,
`UNSUPPORTED = "unsupported"`, and `AMBIGUOUS = "ambiguous"`.
`CandidateEvaluation(index, result)` records one candidate, and
`OverloadSelection(outcome, evaluations)` retains every ordered evaluation.

`select_overload(overloads, arguments)` evaluates every signature in declared
order. Zero matches yields `UNSUPPORTED`, one match yields `MATCH`, and more
than one yields `AMBIGUOUS`. Candidate indices remain continuous from zero.

## Capability-fact Non-authority

Phase 52 capability facts, inventory, signatures, contexts, aggregate facts,
and four-result lookup remain private descriptive evidence.
They are not compatibility or compiler-acceptance authority. This module does
not import them. `Found`, `Absent`, `Unknown`, `Conflict`, backend disposition,
and capability-key order cannot decide matrix membership, binding, or overload
selection. The binder does not consult capability lookup.

## Nullability And Phase 5 Boundary

No Slice 4 carrier contains nullability, and nullability does not participate
in identity equality, constraint checks, binding, mismatch selection, or
result resolution. Unknown nullability is not an unresolved logical type.
Phase 53 Slice 5 exclusively owns symbolic generic result-nullability formulas
and requires a separate gate.

## Phase 64 Exclusions

Slice 4 implements no coercion, promotion, subtyping, common-supertype or LUB
search, Decimal precision/scale fusion, temporal conversion, nullable lifting,
backend conversion, native mapping, row polymorphism, advanced generic type,
or runtime default-value typing. Phase 64 retains those owners. Exact
same-type binding is not a partial implementation of those behaviors.

## Positive Compatibility Matrix

Positive evidence covers all true cells in the complete matrix, exact
unconstrained and constrained bindings, repeated exact identities, concrete
and variable results, independent variables, optional omission, immutable
evidence, empty and ordered overload collections, one unique match, and
ordered duplicate-preserving ambiguity.

## Negative And Fail-closed Matrix

Negative evidence covers every false matrix cell; alias, unknown, and deferred
builtin rejection; case and kind mismatches; wrong arity; unresolved
arguments; concrete, repeated, and constraint mismatches; optional-result
unbinding; malformed constructors; duplicates where forbidden; and ambiguity
where duplicate overload rows are valid. No first-match or hidden conversion
rescues a failure.

## Grammar AST Generated And Behavior Immutability

Grammar, all eight generated artifacts, AST nodes, AST builder, parser API,
window identity, current semantic analyzer and expression procedures remain
byte-identical. The new module is standalone. Existing window calls continue
to fail closed through the existing diagnostic/no-fact path, and no current
accepted or rejected program changes.

## Privacy Public Project IR SQL Boundary

Public package exports, semantic exports, IR exports, SQL exports, CLI text,
CLI JSON v1, Project JSON v2, Semantic Metadata Artifact v1, project facts,
IR, PostgreSQL/private-MySQL lowering, serializers, package metadata,
dependencies, lockfile, workflow, runtime, and database behavior remain
unchanged. The module is private by path and empty `__all__`.

## Reader Hash Inventory And Repository-state Closure

Adding the module changes the compiler boundary from 82 to 83 files, the
semantic boundary from 27 to 28, and the Phase 15 semantic subset from 24 to
25. Project, IR, SQL, generated, and golden inventories remain unchanged.
Direct, nested, inventory, selector, and dirty-state readers migrate without
weakening equality and terminate inside the exact `A3/M49/D0` allowlist.

The Gate 2 dirty state is exact M49 tracked modifications plus exact A3
untracked additions, no deletion or rename, and an empty index at base
`ee0cb021160ead5ea6c0bcc80e569f4fdfef67a3`. Clean synchronized and clean
detached/depth-one states remain accepted without permanent base, parent,
remote, historical-object, network, or `/tmp` dependencies.

## Validation Depth-one CI And Gate 3 Publication

Gate 2 uses one exact 50-path write formatter, then lock, format-check, lint,
production Pyright, test Pyright, the immutable 82-operand focused selector,
the immutable 183-node dirty overlay, generated byte check, and
`git diff --check`. Expected results are 427 focused passes, 6566 total items,
6383 broad passes with 183 deselected, eight generated artifacts, and 37
goldens.

Gate 2 remains unstaged and uncommitted. A later exact Gate 3 alone may stage
52 paths, commit `Add Phase 53 exact generic compatibility foundation`, push
once, and observe the unique natural exact-head CI. Clean CI projects 6566
passes per Python job and package version `0.1.0`.

## Deferred Ownership And Stop Conditions

Slice 5 retains nullability algebra; Slice 6 retains private window semantic
stage, dependency, lineage, and result roles; later Phase 53 slices retain
window behavior and lowering; Phase 64 retains coercion and advanced generic
types. No later slice is automatically authorized.

STOP on allowlist escape, a changed matrix, capability lookup authority,
current analyzer integration, grammar/AST/parser/generated mutation,
nullability or Phase 64 behavior, project/IR/SQL/public widening, a second
formatter, changed `31/190/6566` arithmetic, selector drift, nonempty index,
publication during Gate 2, or an unresolved product decision.
