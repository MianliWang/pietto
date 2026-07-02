# Expanded Scalar / Operator Matrix v1

## Boundary

Phase 36 Slice 9 is tests-only hardening with a docs/spec decision record.
Slice 9 consolidates the current scalar/operator/comparison/aggregate posture
across Phase 30/31 contracts and Phase 36 Slices 3 through 8.

Slice 9 makes no behavior change. It does not change source/compiler behavior,
grammar, generated ANTLR files, parser or AST behavior, semantic behavior, IR
or SQL behavior, CLI behavior, JSON v1, Project JSON v2, Semantic Metadata
Artifact v1 schema or output, fixtures, goldens, examples, scripts, package
metadata, package version, workflows, tags, release, publish/upload, signing,
or attestation.

The matrix below documents current supported, fail-closed, risky generic
shared, and deferred surfaces. It does not promote current generic shared
behavior into a stable type-specific compatibility guarantee.

## Scalar Posture Inventory

| Surface | Current posture | Notes |
|---|---|---|
| `Bool` | current builtin | Current predicate and Bool operator behavior remains unchanged. |
| `Int` | current builtin numeric | Current numeric arithmetic, aggregate, and literal behavior remains unchanged. |
| `Float` | current builtin numeric | Current numeric promotion with `Int` remains unchanged. |
| `Decimal` | current logical exact numeric builtin | `Decimal + Decimal` and `Decimal - Decimal` remain accepted; Phase 41 adds internal precision-scale validation and private semantic facts only. |
| `Text` | current builtin | Current string literal, projection, and lower/trim/len/matches support remains unchanged. |
| `Date` | current builtin temporal | Current direct-field aggregate and generic comparison behavior remains unchanged. |
| `Timestamp` | current builtin temporal | Current direct-field aggregate and generic comparison behavior remains unchanged. |
| `UUID` | `limited_frozen` builtin | Not a fully stable UUID scalar; broader UUID comparison/order/group/satisfying/native behavior remains deferred. |
| Enum | `metadata_only` semantic/IR kind | Enum is not a builtin scalar; `count(Enum field)` remains semantic `PIE-S2314`. |
| `DateTime` / `Time` / `Interval` | unsupported/deferred | These names are not builtins and fail semantic type resolution with `PIE-S2002`. |
| `Any` | current builtin top/deferred boundary | Not dynamic typing and not permissive SQL fallback; `count(Any field)` remains `PIE-S2314`. |
| `Bytes` / `Json` | `deferred_builtin` behavior surfaces | Field facts and projection remain generic; direct `count(field)` remains current accepted behavior. |
| Type aliases | current alias behavior | Aliases preserve declared and canonical facts; domain refinement remains deferred. |
| Unknown names | unknown/unresolved | Unknown type names fail with diagnostics such as `PIE-S2002`. |
| Currency/Money | deferred | Not implemented as primitives, aliases, domains, or metadata carriers. |
| native DB metadata | deferred | No native type metadata, storage, DDL, schema introspection, or db pull behavior is added. |

## Arithmetic Posture

`Int` / `Float` arithmetic remains current per existing contracts:

- unary `+` / `-` accepts `Int` and `Float` and preserves operand type and
  nullability;
- binary `+`, `-`, and `*` accepts `Int` / `Float` combinations and returns
  `Int` or `Float` under the current promotion rules;
- modulo `%` remains `Int` / `Int` only;
- division `/` remains deferred/unknown without becoming a specified division
  behavior.

`Decimal + Decimal` and `Decimal - Decimal` remain the current accepted Decimal
behavior. Decimal multiplication remains rejected with `PIE-S2105`. Decimal
division remains deferred/unsupported as currently documented. Mixed Decimal
promotion remains closed/deferred as currently documented.

No new arithmetic behavior is authorized.

Phase 41 Decimal precision-scale validation and private `DecimalPrecisionScale`
facts do not change this arithmetic matrix. Decimal literal typing remains
owned by Phase 42 numeric/literal work, the Int/Float/Decimal promotion matrix
and Float/Decimal mixing remain owned by Phase 42 numeric promotion decisions,
Decimal multiplication/division remains owned by Phase 42 or later numeric
operator matrix work, aggregate precision propagation remains owned by a future
aggregate/type propagation phase, SQL `DECIMAL(p,s)` / `NUMERIC(p,s)` output
remains owned by native SQL type/DDL/dialect contracts, DDL/native DB metadata
remains owned by native DB metadata prerequisites, public JSON precision-scale
fields remain owned by schema-versioned public output contracts, and
metadata/explain precision-scale display remains owned by Artifact v2/display
contracts.

## Comparison And Bool Predicate Posture

The existing operator/comparison matrix remains current. Bool predicate and
`where` behavior remain current. Generic known-child comparison behavior remains
current where already implemented and produces a `Bool` value with unknown
nullability; it is not a pair-specific compatibility guarantee.

UUID / Enum / Any / Bytes / Json comparison and ordering are risky generic
shared paths, not stable type-specific compatibility guarantees. Slice 9 does
not authorize UUID-stable comparison, Enum SQL scalar semantics, Any dynamic
typing, Bytes binary ordering, Json structural ordering, or domain-refinement
comparison semantics.

No new comparison, ordering, or Bool predicate behavior is authorized.

## Projection / Alias / Order By / Group By / Satisfying Posture

Projection and aliases continue to use current row-schema propagation. Type
aliases participate through the current declared/canonical type paths where
already implemented, but alias participation does not imply domain constraints,
units, validation, casts, coercions, runtime checks, native DB domains, or
output schema expansion.

Current generic `order by`, `group by`, and `satisfying` paths are documented as
shared behavior where already implemented. For `UUID`, Enum, `Any`, `Bytes`,
`Json`, and aliases over those targets, these paths remain risky generic shared
paths. They are not stable type-specific compatibility guarantees and are not
newly authorized behavior.

## Aggregate Posture

`count()` remains current `Int NON_NULL` behavior.

`count(field)` remains current for supported concrete non-Any fields except the
Enum and Unknown boundaries as currently implemented. `count(Enum field)`
remains semantic `PIE-S2314`. `count(Any field)` remains semantic `PIE-S2314`.
`Bytes` / `Json` direct `count(field)` remains current accepted behavior.

`count_distinct` supported direct-field rows remain current for `Bool`, `Int`,
`Float`, `Decimal`, `Text`, `Date`, `Timestamp`, and `UUID`.
`count_distinct` over `Any`, `Bytes`, `Json`, and Enum remains `PIE-S2314`.
Current lower/trim Text transform chains remain unchanged.

`min` / `max` supported direct-field rows remain current for `Int`, `Float`,
`Decimal`, `Date`, and `Timestamp`.

`sum` / `avg` supported rows remain current for `Int`, `Float`, and `Decimal`,
including the existing bounded numeric expression argument rules.

Unsupported aggregate arguments remain semantic `PIE-S2314`. No new aggregate
behavior is authorized.

## Public Output Posture

Public output surfaces remain unchanged:

- CLI text output unchanged;
- CLI JSON v1 unchanged;
- Project JSON v2 unchanged;
- Semantic Metadata Artifact v1 schema/output unchanged;
- SQL output and goldens unchanged;
- fixtures and examples unchanged;
- package, workflow, release, publish/upload, signing, and attestation surfaces
  unchanged.

No matrix-specific output schema fields are added for operator matrices,
comparison matrices, aggregate matrices, ordering policy, group-key policy,
native type metadata, domain refinement, Decimal precision/scale, UUID native
semantics, Enum SQL semantics, Any dynamic typing, Bytes encoding, or Json
structure.

## Risky Generic Shared Paths

These paths remain documented as risky, not stable guarantees:

- comparison/order/group/satisfying for `UUID`;
- comparison/order/group/satisfying for Enum;
- comparison/order/group/satisfying for `Any` / `Bytes` / `Json`;
- alias participation through canonical type paths where currently implemented;
- generic SQL rendering for shared operators where a source program is already
  semantically accepted.

Slice 9 does not identify a small accepted-to-backend `PIE-B1000` path that can
be safely resolved inside this tests-only hardening slice. Forcing later
pipeline stages after semantic errors is not an accepted semantic path.

## Deferred And Unsupported Surfaces

The following surfaces remain deferred or closed:

- Decimal precision/scale carrier;
- DateTime / Time / Interval behavior;
- UUID stable/native behavior;
- Enum SQL scalar semantics;
- Any dynamic typing;
- Bytes binary literals, encoding, functions, operators, native storage, or
  native metadata;
- Json path operators, structural typing, object/array schema validation,
  functions, native storage, or native metadata;
- domain refinement;
- Currency/Money;
- native DB metadata;
- DDL/storage/runtime execution;
- schema introspection/db pull;
- SQL golden output changes;
- CLI/JSON/schema output expansion;
- package/workflow/release behavior.

## Future Prerequisites

Future operator or matrix behavior work requires separately approved Gate 1 and
Gate 2 decisions. That work must first define explicit policy for:

- operator compatibility and result typing;
- comparison compatibility and pair-specific diagnostics;
- ordering compatibility;
- group-key compatibility;
- `satisfying` result predicate compatibility;
- aggregate result and argument compatibility;
- Decimal precision/scale carrier ownership and propagation;
- UUID and Enum SQL portability;
- Any / Bytes / Json behavior;
- temporal candidates and timezone/precision/duration rules;
- type alias and domain refinement participation;
- native DB metadata;
- public output compatibility;
- diagnostics and fail-closed behavior;
- validation proving no accidental SQL, JSON, metadata, runtime, or package
  expansion.

## Explicit Non-authorization

Slice 9 does not authorize implementation behavior. It does not authorize new
arithmetic behavior, comparison behavior, ordering behavior, aggregate
behavior, Bool predicate behavior, Decimal precision/scale carrier work,
DateTime / Time / Interval behavior, domain refinement behavior,
Currency/Money behavior, native DB metadata, DDL/storage behavior,
runtime/database execution, schema introspection/db pull, SQL golden output
changes, CLI output changes, JSON schema changes, Semantic Metadata Artifact v1
schema or output changes, fixture/golden updates, package/workflow/release
changes, tags, publish/upload, signing, or attestation.
