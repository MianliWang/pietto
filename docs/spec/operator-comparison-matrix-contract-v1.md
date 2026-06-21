# Operator And Comparison Matrix Contract v1

## Status

Phase 30 Slice 7 is complete as operator and comparison matrix contract,
static audit, and status work only.

This contract defines the current v0.2 operator and comparison matrix boundary
for Pietto compile-time scalar expression typing, operator result
nullability, comparison result nullability, unknown value type propagation,
and current diagnostic behavior.

Slice 7 does not change source implementation, grammar, generated files, type
resolution, expression typing, operator validation, comparison validation,
predicate validation, diagnostics, IR, SQL lowering, CLI behavior, JSON
behavior, public APIs, fixtures, goldens, package metadata, or CI.

## Trusted Baseline

Slice 7 starts from the completed Phase 30 Slice 6 baseline:

- HEAD: `da9394c1e9e0383e574a5c773d1414e7969ca7c0`;
- commit: `Document Decimal precision and scale contract`;
- CI run: `27889088949 success`.

Phase 30 Slice 1 is complete as candidate decision, type-system contract,
static audit, and status work only. Phase 30 Slice 2 is complete as canonical
scalar type registry contract, static audit, and status work only. Phase 30
Slice 3 is complete as nullability propagation contract, static audit, and
status work only. Phase 30 Slice 4 is complete as Bool and predicate semantics
contract, static audit, and status work only. Phase 30 Slice 5 is complete as
Date / Timestamp formalization contract, static audit, and status work only.
Phase 30 Slice 6 is complete as Decimal precision / scale contract, static
audit, and status work only. v0.2 is not complete yet. Phase 30, Phase 31,
and Phase 32 remain required before v0.2 stable completion.

## Candidate Decision

| Candidate | Fit | Risk | Decision |
|---|---:|---:|---|
| Slice 7 docs/spec/static-audit/status only | High | Low | Chosen. |
| Tests-only hardening | Medium | Medium | Rejected for Slice 7; current behavior tests already cover the relevant operator, comparison, Decimal, Bool, and unknown-propagation surfaces. |
| Minimal implementation artifact | Low | Medium | Rejected; no consumer requires a registry object, compatibility helper, matrix API, or diagnostic helper before the contract is accepted. |
| Broad behavior implementation | Low | High | Rejected; it could change semantic typing, diagnostics, predicate behavior, IR, SQL lowering, CLI/JSON, fixtures/goldens, aggregate behavior, and public API behavior. |

The selected Slice 7 direction is contract-first. It records current behavior
only and does not add operator compatibility validation, comparison
validation, casts, collation, temporal comparison rules, UUID comparison
guarantees, Enum comparison behavior, Bytes/Json comparison behavior,
diagnostic behavior, SQL lowering changes, or public API behavior.

## Matrix Status Vocabulary

Slice 7 uses five status labels:

- currently accepted behavior: current semantic typing accepts the expression
  and records a known result value type;
- currently rejected behavior with existing diagnostics: current semantic
  typing rejects known invalid operands through existing diagnostics such as
  `PIE-S2105`;
- currently deferred/unknown behavior: current semantic typing records
  `ValueTypeKind.UNKNOWN` and does not establish a v0.2 behavior contract;
- current generic behavior without pair-specific compatibility guarantee:
  current semantic typing accepts known child value types generically, but the
  contract does not promise a stable pair-specific semantic compatibility
  rule;
- explicitly out of v0.2 scope: behavior is not part of the v0.2 stable
  compiler scalar type contract.

These labels describe current compiler facts and contract boundaries. They do
not authorize implementation changes.

## Operator Result Matrix

Operator result `UNKNOWN` below means Pietto
`EffectiveNullability.UNKNOWN`: the value type is known, but compile-time
nullability is not proven. It is not SQL three-valued logic `UNKNOWN`.

| Operator area | Operand area | Current result / status |
|---|---|---|
| Unary `+` / `-` | `Int` | currently accepted; preserves `Int` and operand nullability |
| Unary `+` / `-` | `Float` | currently accepted; preserves `Float` and operand nullability |
| Unary `+` / `-` | `Decimal` | currently rejected with existing `PIE-S2105`; Decimal unary is not accepted |
| Unary `+` / `-` | `Text`, `Bool`, `Date`, `Timestamp`, `UUID`, `Bytes`, `Json`, `Any`, `Enum` | currently rejected with existing invalid numeric-operand behavior where the operand type is known; unknown or unsupported operands remain unknown |
| Binary `+` / `-` / `*` | `Int` / `Int` | currently accepted as `Int UNKNOWN` |
| Binary `+` / `-` / `*` | `Int` / `Float`, `Float` / `Int`, `Float` / `Float` | currently accepted as `Float UNKNOWN` |
| Binary `+` / `-` | `Decimal` / `Decimal` | currently accepted as `Decimal UNKNOWN` |
| Binary `*` | `Decimal` / `Decimal` | currently rejected with existing `PIE-S2105`; no Decimal multiplication |
| Binary `+` / `-` / `*` | `Decimal` mixed with `Int` or `Float` | currently rejected with existing `PIE-S2105`; no mixed Decimal promotion |
| Modulo `%` | `Int` / `Int` | currently accepted as `Int UNKNOWN` |
| Modulo `%` | all other known operand pairs | currently rejected with existing `PIE-S2105`; `%` requires Int operands |
| Division `/` | all operand pairs | currently deferred/unknown; current behavior records `ValueTypeKind.UNKNOWN` and does not emit `PIE-S2105` |
| Bool `and` / `or` | `Bool` / `Bool` | currently accepted as `Bool UNKNOWN` |
| Bool `and` / `or` | known non-Bool operands | currently rejected with existing `PIE-S2105`; Bool operators require Bool operands |
| Bool `and` / `or` | unknown operands | currently deferred/unknown without an extra invalid-operand cascade |

Text concatenation is not supported by Slice 7. `Text + Text` is not a string
concatenation operator and must remain rejected under current numeric-operand
rules.

Decimal boundaries remain those from Slice 6: no Decimal multiplication, no
Decimal division, no mixed Decimal/Int promotion, no mixed Decimal/Float
promotion, no Decimal literals, no casts, and no Decimal precision/scale
semantics.

## Comparison And Predicate Matrix

Current comparison behavior is generic known-child typing:

- a `ComparisonExpr` types its left and right child expressions;
- when child value types are known, current semantic typing records
  `Bool UNKNOWN`;
- known child value types currently produce `Bool UNKNOWN`;
- this is a current compiler behavior fact, not a final pair-specific
  semantic compatibility guarantee;
- Slice 7 does not add new comparison validation, casts, collation, temporal
  comparison rules, UUID comparison guarantees, Enum comparison behavior,
  Bytes/Json comparison behavior, or SQL lowering changes.

`BetweenExpr` has the same generic posture:

- it types value, lower, and upper child expressions;
- if all child value types are known, current semantic typing records
  `Bool UNKNOWN`;
- if any child value type is unknown, current semantic typing records
  `ValueTypeKind.UNKNOWN`;
- this is not a final pair-specific compatibility guarantee.

`is null` and `is not null` type the operand expression and currently return
`Bool NON_NULL`.

Date/Timestamp boundaries remain those from Slice 5: no Date/Timestamp-specific
comparison matrix, no DateTime primitive or alias, no Time or Interval
primitive, no timezone semantics, no temporal arithmetic, no date/time
functions, no temporal casts, no Date/Timestamp literals, and no timestamp
precision modeling.

UUID, Enum, Bytes, Json, and Any keep their Slice 2 boundaries:

- `UUID` remains a limited/frozen identifier scalar only for existing accepted
  behavior such as direct-field `count_distinct(UUID)`;
- Slice 7 adds no UUID comparison, cast, literal, storage, DDL, wider SQL, or
  public API behavior;
- `Enum` remains a non-builtin semantic type kind and has no SQL/comparison
  behavior in Slice 7;
- `Bytes` and `Json` remain deferred/unsupported behavior built-ins;
- `Any` must not hide unsupported behavior or create implicit compatibility.

## Scalar Function Boundary

Current scalar function calls remain exact built-ins:

| Function | Current signature |
|---|---|
| `lower` | `lower(Text) -> Text` |
| `trim` | `trim(Text) -> Text` |
| `len` | `len(Text) -> Int` |
| `matches` | `matches(Text, Text) -> Bool` |

Slice 7 records these functions only as current expression-typing facts that
can feed operator and comparison operands. It does not add scalar functions,
function overloads, casts, collation behavior, Text comparison guarantees,
Text concatenation, SQL lowering changes, CLI/JSON behavior, or public API
behavior.

## Unknown And Diagnostic Boundaries

`EffectiveNullability.UNKNOWN` is a nullability fact on a known value type.
For example, `Bool UNKNOWN` means the value type is known to be `Bool`, but
compile-time nullability is not proven.

`ValueTypeKind.UNKNOWN` means the value type itself is unknown, unsupported,
or deferred under current semantics.

SQL three-valued logic `UNKNOWN` is a runtime SQL predicate truth value. It is
not a Pietto compile-time nullability fact and is not a `ValueTypeKind`.

Current diagnostic behavior is preserved exactly:

- invalid known operator operands use existing `PIE-S2105` only where current
  repo behavior already emits it;
- division `/` remains deferred/unknown and does not become a new diagnostic
  behavior;
- unknown child value types suppress invalid-operator cascades under current
  behavior;
- predicate diagnostics remain owned by the existing predicate paths and the
  Slice 4 Bool/predicate contract;
- Slice 7 introduces no new diagnostic code, no renamed diagnostic, no
  reordered diagnostic, no reworded diagnostic, and no span or severity
  change.

## Handoff

Slice 8 Completion Audit And Status Lock is complete as completion audit and
status lock work only. It verifies the complete Phase 30 contract set,
unchanged forbidden surfaces, validation commands, public API stability,
CLI/JSON stability, SQL/golden/generated/package validation boundaries,
aggregate freeze preservation, deferred register preservation, status
documentation, and the Phase 31/32 handoff.

Phase 30 is complete as docs/spec/static-audit/status work only. v0.2 is not
complete yet. Phase 31 Core Type System Stabilization II And Dialect Matrix
Hardening is the next mainline and may separately harden numeric/Decimal
boundaries, UUID/Enum readiness, Date/Timestamp SQL compatibility, diagnostic
boundaries, and CLI/JSON hardening after Phase 30 contracts are accepted.

Phase 31 and Phase 32 remain required before v0.2 stable completion.

## Explicit Non-Goals

Slice 7 does not authorize:

- source implementation changes;
- grammar, generated ANTLR, AST, or parser changes;
- semantic implementation or semantic behavior changes;
- type-system behavior changes;
- diagnostic behavior changes;
- predicate behavior changes;
- IR implementation or IR model changes;
- SQL backend or SQL lowering changes;
- SQL three-valued logic lowering changes;
- CLI behavior, command, option, help, exit-code, or output changes;
- JSON v1 changes or JSON v2 implementation;
- public API changes or public MySQL API expansion;
- aggregate expansion or aggregate behavior changes;
- fixture, golden, script, dependency, lockfile, package metadata, CI, or
  package version changes;
- release tags, release artifacts, publishing, upload, signing, or
  attestation;
- project or multi-file implementation;
- schema introspection, database pull, SQL execution, connector execution, or
  runtime/database behavior;
- relationship or JOIN implementation;
- Text concatenation;
- new scalar functions, function overloads, casts, or collation behavior;
- new comparison validation or pair-specific compatibility guarantees;
- DateTime primitive or alias;
- TimestampTZ, Instant, Time, or Interval primitives;
- timezone semantics;
- temporal arithmetic, date/time functions, extraction, or truncation;
- Date/Timestamp literal syntax, Date/Timestamp casts, timestamp precision
  modeling, native database type metadata, physical storage guarantees, or
  runtime timezone interpretation;
- Decimal precision/scale syntax semantics, carrier, propagation, validation,
  SQL precision guarantees, JSON/API exposure, native database metadata, or
  public contract;
- Decimal literal syntax, Decimal multiplication or division expansion, mixed
  Decimal promotion expansion, or casts;
- Money or Currency primitives;
- exchange-rate, accounting, rounding, or minor-unit semantics;
- semantic annotation syntax;
- UUID implementation or broader UUID behavior;
- UUID comparison, cast, literal, storage, DDL, wider SQL, or public API
  behavior;
- Enum implementation or broader Enum behavior;
- Enum SQL or comparison behavior;
- Bytes or Json behavior expansion;
- native database type metadata.
