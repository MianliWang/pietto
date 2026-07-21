# Phase 53 Slice 5 Nullability Algebra And Signature Result-formula Foundation v1

## Status And Slice Identity

Phase 53 is active. Slices 1 through 4 are complete. Slice 5 remains
unstarted throughout Gate 2 and becomes complete only after a separately
authorized Gate 3 publishes this exact foundation and its exact-head natural
CI succeeds. This slice adds a private symbolic result-nullability foundation
without changing any accepted or rejected Pietto program.

## Existing Concrete Nullability Authority

The existing concrete authority remains exactly
`EffectiveNullability.NON_NULL`, `EffectiveNullability.NULLABLE`, and
`EffectiveNullability.UNKNOWN`. `ValueType` continues to own concrete
expression result facts. Unknown logical type, unknown nullability, nullable
value, SQL `NULL`, and SQL Boolean `UNKNOWN` remain distinct concepts. This
contract does not add a fourth concrete state or modify existing propagation.

## Existing Slice 4 Generic Signature Authority

`src/pietto/semantic/generic_compatibility.py` remains byte-identical. Its
`GenericSignature`, `SignatureParameter`, `ParameterDefault.OMITTED`, exact
binding, constraint checks, mismatch precedence, `SignatureMatch` omission
facts, and overload selection remain authoritative. Slice 5 consumes those
immutable values without rebinding types or changing overload behavior.

## Private Module Placement And No-integration Boundary

The foundation lives only in
`src/pietto/semantic/nullability_formulas.py`. The module has an empty
`__all__`, owns no mutable registry or cache, and imports no analyzer,
catalog, capability, window, project, IR, SQL, CLI, or serializer layer. No
current production module imports it in Slice 5.

## Signature-result Sibling-wrapper Architecture

`SignatureResultFormula(signature, nullability)` is a frozen, slotted,
keyword-only sibling wrapper. It preserves the exact immutable
`GenericSignature` value and performs construction-time formula bounds,
index, optional-parameter, and omitted-default validation. The existing
generic carrier and `OverloadSet` are unchanged; no callable or window
identity is stored.

## Formula Kind And Carrier Inventory

The exact ordered stable kinds are `non_null`, `nullable`, `same_as_arg`,
`any_nullable`, `always_nullable`, `nullable_if_default_omitted`, and
`any_of`. Separate frozen, slotted, keyword-only variants are
`NonNullFormula`, `NullableFormula`, `SameAsArgumentFormula`,
`AnyNullableFormula`, `AlwaysNullableFormula`,
`NullableIfDefaultOmittedFormula`, and `AnyOfFormula`. Each variant stores an
`init=False` kind field that participates in repr, equality, and hashing.

## NULLABLE And ALWAYS_NULLABLE Distinction

`NullableFormula` is an explicit literal nullable algebra factor.
`AlwaysNullableFormula` is a context-independent signature-result policy.
They remain different classes and kinds with distinct evidence provenance,
but both evaluate to `EffectiveNullability.NULLABLE`. Neither is collapsed,
aliased, canonicalized, or restricted away as a legal leaf.

## Argument Index And Ordered Collection Contract

Every index is an exact nonnegative `int`; `bool` is rejected. An
`AnyNullableFormula` stores an exact tuple of one or two indices. An
`AnyOfFormula` stores an exact tuple of two formula children. Lists, sets,
mappings, and other iterables are rejected. Declaration order and duplicates
are preserved; duplicate argument occurrences count independently toward the
global reference bound.

## SAME_AS_ARG Truth Table

For a supplied argument, `NON_NULL` maps to `NON_NULL`, `NULLABLE` maps to
`NULLABLE`, and `UNKNOWN` maps to `UNKNOWN`. A referenced omitted optional
argument returns structured `omitted_argument_referenced` evidence. An
out-of-range reference is rejected when the sibling wrapper is constructed.

## ANY_NULLABLE Truth Table

Every selected occurrence is evaluated in declared order. A supplied
argument contributes its exact concrete fact. An omitted optional position
contributes neutral `NON_NULL` with `supplied=False` and `value=None`; this is
not a claim about a runtime default. The join is `NULLABLE` if any contribution
is nullable, otherwise `UNKNOWN` if any is unknown, otherwise `NON_NULL`.
Evidence never short-circuits and duplicate rows remain visible.

## NULLABLE_IF_DEFAULT_OMITTED Contract

The formula stores one parameter position. The wrapper requires that
position to exist, be optional, and carry `ParameterDefault.OMITTED`. At
evaluation it contributes `NULLABLE` when omitted and `NON_NULL` when
supplied. No runtime default value is executed.

## ANY_OF Composition And Truth Table

`ANY_OF` is the only Boolean composition operator. It has exactly two ordered
children, evaluates both, and propagates the first structured unsupported
result in child order. Two matches use the same three-state join:
`NULLABLE` dominates `UNKNOWN`, `UNKNOWN` dominates `NON_NULL`, and two
`NON_NULL` children produce `NON_NULL`. `ALL_OF`, `NOT`, and arbitrary
operators do not exist.

## Exact Boundedness Contract

A leaf has depth one. Maximum formula depth is two, maximum node count is
three, composition arity and maximum child count are two, and maximum
argument-reference occurrences are two. A legal `ANY_OF` is one root with
two leaf children. Nested `ANY_OF` has depth three and is rejected. Default
omission references do not count as argument-nullability references.
Traversal is preorder: root, then children in declaration order.

## Evaluation Context Contract

`NullabilityEvaluationContext` stores an exact tuple of supplied-prefix
`EffectiveNullability` facts and an exact tuple of strictly ascending unique
nonnegative omitted positions. It stores no signature, values, runtime
defaults, logical bindings, AST, spans, or backend state. The evaluator
requires omissions to equal the exact trailing suffix implied by the wrapper
signature and supplied-prefix length.

## Evaluation Result And Evidence Contract

Evaluation returns either `NullabilityEvaluationMatch(value, evidence)` or
`NullabilityEvaluationUnsupported(reason, parameter_position)`. Recursive
evidence preserves exact formula kind, final value, ordered argument rows,
one optional default row, and ordered child evidence. Evidence carriers are
frozen, slotted, keyword-only, structurally hashable, and contain no public
diagnostic or source location.

## UNKNOWN Preservation Contract

`SAME_AS_ARG` preserves unknown. `ANY_NULLABLE` and `ANY_OF` produce unknown
only when no selected contribution is nullable and at least one is unknown.
`NON_NULL` never erases unknown; a definite nullable factor may dominate it.
No formula converts unknown alone to a definite state. Concrete nullability
unknown remains distinct from SQL `NULL` and SQL Boolean `UNKNOWN`.

## Optional/default And Signature Cross-validation

The supplied facts are a positional prefix. Omitted positions must be the
remaining suffix. Required omission, a missing suffix fact, an out-of-range
or supplied omission, and another inconsistent suffix shape have distinct
structured failure reasons. A default-reference formula may target only an
optional parameter whose marker is exactly `ParameterDefault.OMITTED`.

## Constructor And Evaluation Failure Boundary

Malformed carrier, container, or member types raise `TypeError`. Well-typed
invariant violations raise `ValueError`. A valid wrapper evaluated against an
incompatible context returns structured unsupported evidence. Ordinary
compatibility failure does not create a public diagnostic and does not throw
an evaluation exception.

## lag And lead Readiness Proof

The readiness-only shape has required value `T`, optional offset `Int`,
optional default `T` with `ParameterDefault.OMITTED`, and result `T`. Its
unified formula is `ANY_OF(ANY_NULLABLE((0, 2)),
NULLABLE_IF_DEFAULT_OMITTED(2))`. Omitted default makes the result nullable;
supplied default joins value and default nullability. Offset nullability does
not contribute. No `lag` or `lead` registration or behavior is added.

## Current Semantic And Project Non-integration

The current analyzer, type resolution, expression and aggregate inference,
let and relation schemas, window fail-closed behavior, catalog, diagnostics,
project schemas, result roles, dependencies, and lineage remain unchanged.
No current production consumer imports or evaluates the new formulas.

## Phase 64 Exclusions

Type coercion, promotion, subtyping, least-upper-bound selection, Decimal
fusion, temporal conversion, alias expansion, native database mapping, and
backend conversion remain owned by Phase 64 or another separately authorized
future phase. The formula foundation cannot claim those capabilities.

## Public Privacy And Serialization Boundary

There is no package-root or semantic-package export, public API, diagnostic
code, CLI field, JSON v1/v2 field, metadata or explain field, project output,
fixture, golden, package, dependency, lockfile, workflow, version, runtime,
database, tag, or release change. Package version remains `0.1.0`.

## Positive Formula Matrix

Focused tests cover all constants, distinct nullable provenance, every
three-state `SAME_AS_ARG` row, ordered and duplicate `ANY_NULLABLE` cases,
the complete binary join, supplied and omitted default factors, complete
`ANY_OF`, legal maximum bounds, wrapper validation, deterministic evidence,
equality/hash/repr stability, and omitted/supplied lag/lead readiness.

## Negative And Fail-closed Matrix

Focused tests reject wrong, Boolean, and negative indices; invalid tuple
containers and cardinalities; wrong children; excessive depth, nodes, or
references; range overflow; invalid default references; malformed evidence;
required omissions; missing facts; and inconsistent omission suffixes. They
also lock unknown preservation and all no-integration boundaries.

## Grammar AST Generic Generated And Behavior Immutability

Grammar, AST nodes, AST builder, parser API, private window identity, all
eight generated files, `generic_compatibility.py`, concrete semantic model,
analyzer behavior, capability facts, project, IR, SQL, CLI, serializers,
fixtures, goldens, package metadata, lockfile, and workflow remain
byte-identical. No ANTLR generation occurs.

## Reader Hash Inventory And Repository-state Closure

The new private source extends the compiler, semantic, and Phase 15 subset
digests from 83/28/25 files to 84/29/26. The new source, specification, and
test update exact tracked/Python/Markdown/test/function/item inventories.
All direct, raw, nested, selector, dirty-state, clean-state, and depth-one
reader edges terminate inside exact `A3/M50/D0`; assertions remain exact.

## Validation Depth-one CI And Gate 3 Publication

Gate 2 uses one exact 51-path Ruff write invocation, then lock, repository
format, lint, production typing, test typing, 607 focused items, the exact
dirty suite with 6528 passes and 183 deselections, generated-byte checking,
and diff checking. Clean depth-one CI projects 6711 passes per Python job,
eight generated files, 37 goldens, package smoke PASS, and CLI `0.1.0`.
Gate 2 remains unstaged and uncommitted.

## Deferred Ownership And Stop Conditions

Slice 6 retains window semantic carriers, stage, dependency, lineage, and
result roles; later Phase 53 slices retain window behavior and lowering. STOP
on allowlist escape, changed formula inventory or bounds, second formatter,
generic or concrete semantic change, analyzer/window integration, grammar or
generated need, project/IR/SQL/public widening, arithmetic drift, staging,
publication, or unresolved product choice.
