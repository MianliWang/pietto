# Phase 38 Type Capability Matrix Contract v1

## Status And Non-Behavior-Change Guardrail

Phase 38 Slice 3 is Type Capability Matrix Contract. Slice 3 is
docs/spec/static-audit/tests-only and authorizes no behavior change.

This document consolidates current type capability vocabulary for aggregate
readiness. It records repo-derived behavior and deferred boundaries only. It
does not add or change source/compiler behavior, grammar, generated ANTLR
files, parser behavior, AST behavior, semantic behavior, IR behavior, SQL
lowering, CLI behavior, JSON v1, Project JSON v2, Semantic Metadata Artifact
v1, diagnostic envelope shape, SQL golden bytes, fixtures/goldens, public
status docs, scripts, workflows, package metadata, lockfiles, package version,
release operations, tags, publish/upload, signing, or attestation.

Package version remains `0.1.0`.

## Current Repo-Derived Capability Inventory

The current capability inventory is grounded in existing docs, tests, and
source helpers:

| Capability area | Current repo evidence |
|---|---|
| Builtin scalar names | `src/pietto/semantic/catalog.py` defines `Any`, `Bool`, `Bytes`, `Date`, `Decimal`, `Float`, `Int`, `Json`, `Text`, `Timestamp`, and `UUID`. |
| Builtin text functions | `src/pietto/semantic/catalog.py` defines `lower(Text)`, `trim(Text)`, `len(Text)`, and `matches(Text, Text)`. |
| Semantic type facts | `src/pietto/semantic/model.py` defines `TypeKind`, `EffectiveNullability`, `ValueTypeKind`, `ResolvedType`, and `ValueType`. |
| Aggregate argument capabilities | `src/pietto/semantic/aggregates.py` defines direct field support, count support, count-distinct support, numeric aggregate support, extrema support, lower/trim Text-chain support, and bounded `sum` / `avg` expression support. |
| Scalar expression capabilities | `src/pietto/semantic/expressions.py` defines current unary, binary, comparison, between, literal, call, and aggregate projection expression typing. |
| Current matrix docs/tests | `docs/spec/expanded-scalar-operator-matrix-v1.md` and `tests/test_phase36_expanded_scalar_operator_matrix.py` lock the current scalar/operator/comparison/aggregate posture. |

Current meanings:

- `lowerable` / `projectable`: a value can flow through current semantic row
  schema, projection, IR/SQL, or locked aggregate SQL paths. This is not a
  native database storage, DDL, runtime, or schema-introspection guarantee.
- `null-checkable`: generic `is null` / `is not null` expression machinery is
  available and returns `Bool NON_NULL`; this is not a type-specific capability
  contract.
- `countable`: current direct `count(field)` accepts resolved direct fields
  except `Enum`, `Unknown`, and builtin `Any`.
- `numeric`: aggregate numeric direct fields are `Int`, `Float`, and
  `Decimal`; scalar `_is_numeric` is narrower and currently includes only
  `Int` and `Float`.
- `arithmetic-capable`: `Int` / `Float` support current `+`, `-`, and `*`;
  `%` is `Int` / `Int`; `/` remains unknown; `Decimal` supports only current
  `Decimal + Decimal` and `Decimal - Decimal`.
- `orderable` / `min-max-capable`: current direct `min` / `max` supports
  `Int`, `Float`, `Decimal`, `Date`, and `Timestamp`. Generic comparison and
  order paths exist, but they are not stable type-specific orderability
  contracts.
- `equality-comparable`: generic known-child comparison currently produces
  `Bool UNKNOWN`; it is not a pair-specific compatibility guarantee.
- `distinct-compatible`: current direct `count_distinct` supports `Bool`,
  `Int`, `Float`, `Decimal`, `Text`, `Date`, `Timestamp`, and `UUID`, plus
  the lower/trim `Text` chain subset.
- `collation-dependent`: Text distinct, ordering, folding, and normalization
  policy remains deferred.
- `serialization-dependent`: future broad distinct over expressions or opaque
  values requires equality, serialization, and dialect policy; current behavior
  does not grant this to `Any`, `Json`, or `Bytes`.
- `text-transform-capable`: current text functions are `lower`, `trim`, `len`,
  and `matches`; aggregate distinct transform support is narrower and allows
  only lower/trim chains over exactly one `Text` field leaf.
- `metadata-backed`: Enum is `metadata_only`; `UUID` is `limited_frozen`;
  `Bytes` and `Json` are deferred builtin behavior surfaces.
- `dialect-lowerable`: current PostgreSQL and private MySQL emitters lower the
  already accepted subset only. This does not imply backend execution or native
  database metadata.

## Capability Vocabulary Contract

Slice 3 defines vocabulary for future planning, not new compiler behavior:

- `lowerable`;
- `projectable`;
- `null-checkable`;
- `countable`;
- `numeric`;
- `arithmetic-capable`;
- `orderable`;
- `equality-comparable`;
- `distinct-compatible`;
- `text-transform-capable`;
- `collation-dependent`;
- `serialization-dependent`;
- `metadata-backed`;
- `dialect-lowerable`;
- `aggregate-compatible`.

The vocabulary deliberately avoids user-visible `hashable`. The current repo
supports `distinct-compatible` as the aggregate/equality planning term; it does
not define hash behavior, hash-based equality, or a hash portability contract.

`aggregate-compatible` means a type or expression satisfies the specific
aggregate's requirements. It is not one global capability. For example,
`count(field)` requires countability, `sum(field)` requires numeric aggregate
support, `min(field)` requires the current extrema subset, and
`count_distinct(field)` requires distinct compatibility.

## Current Scalar / Type Capability Matrix

This table records current behavior only:

| Type | Projection/output | `is null` / `is not null` | `count(field)` | `count_distinct(field)` | `sum/avg` | `min/max` | Arithmetic | Comparison/order | Text transform | Diagnostics / deferred boundary |
|---|---|---|---|---|---|---|---|---|---|---|
| `Bool` | current builtin projection | generic yes | yes | yes | no | no | Bool `and` / `or` only | generic comparison path, not pair-specific | no | unsupported aggregates use `PIE-S2314` |
| `Int` | current builtin projection | generic yes | yes | yes | yes; `avg(Int)` returns `Float` | yes | `+`, `-`, `*`, `%` with `Int` | generic comparison/order | no | `/` unknown |
| `Float` | current builtin projection | generic yes | yes | yes | yes | yes | `+`, `-`, `*` with numeric promotion | generic comparison/order; no Float-specific caveat found beyond general portability | no | no new Float policy |
| `Decimal` | current builtin projection | generic yes | yes | yes | yes | yes | current `Decimal + Decimal` and `Decimal - Decimal` only | generic comparison/order | no | internal precision-scale carrier implemented by Phase 41; literals, multiplication, division, mixed promotion, propagation, and public output fields remain deferred with named prerequisites |
| `Text` | current builtin projection | generic yes | yes | yes | no | no | no Text arithmetic | generic comparison/order; collation/order expansion deferred | `lower`, `trim`, `len`, `matches`; distinct chain only lower/trim | collation, Unicode, locale, and backend equality deferred |
| `Date` | current builtin temporal projection | generic yes | yes | yes | no | yes | no temporal arithmetic | generic comparison/order, not Date-specific matrix | no | temporal functions/casts deferred |
| `Timestamp` | current builtin temporal projection | generic yes | yes | yes | no | yes | no temporal arithmetic | generic comparison/order, not Timestamp-specific matrix | no | timezone, precision, and native metadata deferred |
| `DateTime` | no builtin | no resolved field | no | no | no | no | no | no | no | unsupported/deferred, `PIE-S2002` |
| `Time` | no builtin | no resolved field | no | no | no | no | no | no | no | unsupported/deferred, `PIE-S2002` |
| `Interval` | no builtin | no resolved field | no | no | no | no | no | no | no | unsupported/deferred, `PIE-S2002` |
| `UUID` | current `limited_frozen` projection | generic yes | yes | yes | no | no | no | generic risky shared path; stable ordering deferred | no | no UUID min/max/native behavior expansion |
| Enum | metadata/projection readiness only | generic expression machinery, no Enum-specific contract | no, `PIE-S2314` | no, `PIE-S2314` | no | no | no | generic risky shared path; SQL scalar ordering deferred | no | `metadata_only`, not builtin |
| `Json` | current deferred builtin projection | generic yes | yes | no | no | no | no | generic risky shared path, no stable Json ordering/equality | no | SQL `NULL` versus JSON literal `null` must stay explicit |
| `Bytes` | current deferred builtin projection | generic yes | yes | no | no | no | no | generic risky shared path, no stable Bytes ordering/equality | no | binary literals, encoding, functions, and native metadata deferred |
| `Any` | current top/deferred projection | generic yes | no, `PIE-S2314` | no | no | no | no | generic risky shared path, not dynamic typing | no | no implicit permissive capability |
| `Unknown` | not accepted as known capability | no stable capability | no | no | no | no | no | no | no | unresolved/unknown diagnostics and `ValueTypeKind.UNKNOWN` |

Generic null-checking is intentionally separated from type-specific
capability. `is null` / `is not null` being typeable does not make a type
numeric, orderable, distinct-compatible, or runtime-lowerable beyond the
current accepted source subset.

## Aggregate Requirement Matrix

| Aggregate surface | Current/future requirement |
|---|---|
| `count()` | Current row-count aggregate, no argument, SQL `COUNT(*)`, result `Int not null`, empty input returns `0`. |
| `count(field)` / `count(source.field)` | Current direct-field countability; resolved type must not be `Enum`, `Unknown`, or builtin `Any`; counts SQL non-null field values. |
| future `count(expression)` | Future only; should require dialect-lowerable expression and explicit SQL nullness semantics, not numeric, orderable, or distinct capability. |
| future `count_if(predicate)` | Future only; predicate must be `Bool` or nullable `Bool`; only `TRUE` counts; `FALSE`, SQL `NULL`, and SQL `UNKNOWN` do not count. |
| `sum/avg(field)` | Current direct numeric aggregate fields: `Int`, `Float`, `Decimal`. |
| bounded `sum/avg(expression)` | Current bounded numeric expression support; field leaf required; scalar rules current; Int/Float numeric literal leaves allowed only in approved non-literal-only forms; Decimal only through current `+` / `-`. |
| future broad `sum/avg(expression)` | Future only; needs numeric capability, arithmetic capability, field-leaf policy, nullability, and dialect-lowerable expression policy. |
| `min/max(field)` | Current direct extrema subset: `Int`, `Float`, `Decimal`, `Date`, `Timestamp`; nullable same-type result. |
| future `min/max(expression)` | Future only; needs known concrete orderable result type, field leaf, nullable result policy, and SQL portability policy. |
| `count_distinct(field)` | Current distinct-compatible subset: `Bool`, `Int`, `Float`, `Decimal`, `Text`, `Date`, `Timestamp`, `UUID`. |
| `count_distinct(lower/trim Text chain)` | Current bounded transform chain over exactly one `Text` field leaf. |
| future broad `count_distinct(expression)` | Future only; needs equality/distinct, collation/normalization, serialization, deterministic transform, and dialect-portability policy. |

## Countability Versus Numeric / Orderable / Distinct Compatibility

Countability is weaker than numeric, orderable, and distinct compatibility.

Current direct `count(field)` counts SQL non-null values for the supported
direct field subset. It does not imply:

- arithmetic support for `sum` / `avg`;
- orderability or `min` / `max`;
- equality and distinct compatibility for `count_distinct`;
- stable group-key or `satisfying` semantics;
- native database metadata, runtime behavior, schema introspection, storage, or
  DDL behavior.

This distinction matters most for `Json`, `Bytes`, and `UUID`, where current
direct count support exists but broader semantics remain deferred.

## Any / Json / Bytes / Enum / UUID Boundary

Slice 3 preserves the current boundary:

- `Any`: keep non-countable, non-arithmetic, non-orderable, and
  non-distinct-compatible by default. Future countability must be explicit
  lowerable-count policy, not dynamic typing.
- `Json`: keep direct `count(Json field)` accepted. Document SQL field
  nullness separately from JSON literal `null`. Do not grant Json distinct,
  order, comparison, path, structural, native metadata, storage, or runtime
  semantics.
- `Bytes`: keep direct `count(Bytes field)` accepted. Do not add binary
  literal, encoding, comparison, distinct, ordering, native metadata, storage,
  DDL, or runtime policy.
- Enum: keep `metadata_only`; `count(Enum field)` remains semantic
  `PIE-S2314`. Future aggregate acceptance requires Enum scalar and SQL
  portability policy first.
- `UUID`: keep `limited_frozen`; projection, direct `count(UUID field)`, and
  direct `count_distinct(UUID field)` remain current. Do not add UUID ordering,
  `min/max`, native behavior, literal, cast, storage, or dialect-specific UUID
  treatment in Slice 3.

## Decimal / Float / Text Readiness Caveats

Phase 41 implements Decimal precision-scale semantic validation and a private
internal carrier. `Decimal(12, 2)` now validates as a logical Decimal type form
with internal `DecimalPrecisionScale` facts; `Decimal()` remains compatible
because the current AST cannot distinguish it from no-argument `Decimal`.
Non-Decimal type arguments remain the current compatibility surface.

Decimal literals, multiplication, division, mixed Decimal promotion, precision
propagation, SQL precision guarantees, public JSON precision-scale fields,
metadata/explain precision-scale display, casts, and native DB metadata remain
future work with named prerequisites.

Float currently participates in direct `count_distinct(Float)` and direct
`min/max(Float)`. Slice 3 found no Float-specific distinct/order caveat beyond
the general portability and future-policy boundaries already documented by the
repo.

Text currently participates in direct `count_distinct(Text)` and the
lower/trim Text-chain subset. Text collation, Unicode normalization,
locale-sensitive folding, Text ordering expansion, and backend-specific
equality rules remain deferred.

## Generic Comparison / Ordering Caveat

Generic known-child comparison behavior currently produces `Bool UNKNOWN`.
Current generic `order by`, `group by`, and `satisfying` paths exist where
already implemented, but they are risky shared paths for `UUID`, Enum, `Any`,
`Bytes`, `Json`, and aliases over those targets. They are not stable
type-specific compatibility guarantees.

Slice 3 does not promote those generic paths into stable UUID comparison,
Enum SQL scalar comparison, Any dynamic typing, Bytes ordering, Json ordering,
collation policy, normalization policy, or pair-specific diagnostics.

## Dialect-Lowerability And Metadata Boundaries

Dialect-lowerability means an already accepted Pietto expression or aggregate
surface has deterministic SQL lowering in the current PostgreSQL and private
MySQL emitters. It does not mean:

- backend execution;
- runtime checks;
- schema introspection;
- native DB metadata;
- storage or DDL behavior;
- public MySQL API expansion;
- package or release behavior.

Metadata-backed types remain distinct from native database behavior. Enum
metadata and UUID support posture do not imply SQL enum DDL, native UUID
storage, casts, literals, runtime validation, or backend-specific comparison.

## Deferred And Prohibited Surfaces

Slice 3 does not implement:

- new type capabilities or changed aggregate acceptance;
- `count(expression)`, `count(constant)`, `count(1)`, or
  `count_if(predicate)`;
- `row_count()` / `count_row()`;
- `count(distinct field)` or generic aggregate modifiers;
- broad `count_distinct(expression)`;
- broad `sum/avg(expression)` beyond current bounded behavior;
- `min/max(expression)`;
- generic aggregate filters;
- window functions;
- nested aggregates;
- aggregate projection composition;
- new collation, normalization, serialization, native DB metadata, Decimal
  carrier, UUID ordering, or Enum SQL scalar behavior;
- parser/AST/grammar/generated behavior changes;
- semantic, IR, SQL, CLI/JSON, fixture/golden, scripts/workflows/package, or
  release behavior changes.

## Future Implementation Prerequisites

Any later behavior implementation requires a separate Gate 1 and Gate 2 that
names implementation files, validation commands, SQL portability proof,
fixture/golden policy, public output compatibility, diagnostic policy, and
release non-authorization.

Future capability work must define explicit policy for:

- countability and SQL nullness;
- arithmetic and numeric promotion;
- Decimal precision/scale ownership and propagation;
- orderability and pair-specific comparison compatibility;
- distinct compatibility, collation, normalization, and serialization;
- text transform determinism;
- `Any`, `Json`, `Bytes`, Enum, and `UUID` capability expansion;
- native database metadata boundaries;
- public output compatibility;
- fail-closed diagnostics;
- validation proving no accidental SQL, JSON, metadata, runtime, package, or
  release expansion.

## Public Surface And Release Non-Authorization

Slice 3 keeps public surfaces unchanged:

- CLI text output unchanged;
- CLI JSON v1 unchanged;
- Project JSON v2 unchanged;
- Semantic Metadata Artifact v1 unchanged;
- diagnostic envelope unchanged;
- SQL golden bytes unchanged;
- fixtures/goldens unchanged;
- generated parser inventory unchanged;
- package version remains `0.1.0`;
- no package/workflow/release metadata change;
- no tag/release/publish/upload/signing/attestation.
