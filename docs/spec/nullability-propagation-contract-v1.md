# Nullability Propagation Contract v1

## Status

Phase 30 Slice 3 is complete as nullability propagation contract, static
audit, and status work only.

This contract defines the current v0.2 nullability propagation boundary for
source fields, expressions, predicates, scalar functions, aggregate results,
unknown value types, and SQL three-valued logic handoff.

Slice 3 does not change source implementation, type inference, nullability
inference, predicate validation, aggregate validation, diagnostics, IR, SQL
lowering, CLI behavior, JSON behavior, public APIs, fixtures, goldens,
package metadata, or CI.

## Trusted Baseline

Slice 3 starts from the completed Phase 30 Slice 2 baseline:

- HEAD: `1ab91bb972c928e92e22fc34e945f871454af9bd`;
- commit: `Document canonical scalar type registry`;
- CI run: `27885698694 success`.

Phase 30 Slice 1 is complete as candidate decision, type-system contract,
static audit, and status work only. Phase 30 Slice 2 is complete as canonical
scalar type registry contract, static audit, and status work only. v0.2 is not
complete yet. Phase 30, Phase 31, and Phase 32 remain required before v0.2
stable completion.

Phase 30 Slice 4 is complete as Bool and predicate semantics contract, static
audit, and status work only. The Slice 4 contract is
`docs/spec/bool-predicate-semantics-contract-v1.md`.

Phase 30 Slice 5 is complete as Date / Timestamp formalization contract,
static audit, and status work only. The Slice 5 contract is
`docs/spec/date-timestamp-formalization-contract-v1.md`.

Phase 30 Slice 6 is complete as Decimal precision / scale contract, static
audit, and status work only. The Slice 6 contract is
`docs/spec/decimal-precision-scale-contract-v1.md`.

Phase 30 Slice 7 is complete as operator and comparison matrix contract,
static audit, and status work only. The Slice 7 contract is
`docs/spec/operator-comparison-matrix-contract-v1.md`.

## Candidate Decision

| Candidate | Fit | Risk | Decision |
|---|---:|---:|---|
| Slice 3 docs/spec/static-audit/status only | High | Low | Chosen. |
| Tests-only hardening | Medium | Medium | Rejected for Slice 3; behavior tests would imply a hardening pass before the contract is accepted. Static audit coverage is enough. |
| Minimal implementation artifact | Low | Medium | Rejected; no current consumer requires a new helper, enum, registry, or propagation function. |
| Broad behavior implementation | Low | High | Rejected; it could change semantic, diagnostic, IR, SQL, CLI, JSON, aggregate, fixture, golden, and public API behavior. |

The selected Slice 3 direction is contract-first. Slice 3 locks current
behavior only and does not broaden nullability inference.

## Three Distinct Unknown Concepts

Slice 3 explicitly distinguishes three different concepts.

`EffectiveNullability.UNKNOWN` is a nullability fact on a known value type. It
means the expression or value has a known type, but Pietto does not have a
stable proof that the value is non-null or nullable.

`ValueTypeKind.UNKNOWN` / unknown value type is not merely unknown
nullability. It means Pietto cannot determine the value type itself, or the
expression is unsupported or unknown under current semantics.

SQL three-valued logic `UNKNOWN` is a runtime predicate truth value. It is
distinct from Pietto compile-time nullability facts and distinct from an
unknown Pietto value type.

This contract does not conflate these concepts. Pietto
`EffectiveNullability.UNKNOWN` is not SQL three-valued logic `UNKNOWN`, and an
unknown value type is not a known type with unknown nullability.

## Current Repo Facts

Slice 3 grounds the nullability contract in current implementation facts:

- `EffectiveNullability` has exactly `NON_NULL`, `NULLABLE`, and `UNKNOWN`;
- `ValueType` carries `resolved_type`, `nullability`, and `kind`;
- `ValueTypeKind` has `KNOWN` and `UNKNOWN`;
- `TypeExpr` nullability maps `nullable` to `EffectiveNullability.NULLABLE`,
  `not null` to `EffectiveNullability.NON_NULL`, and implicit nullability to
  `EffectiveNullability.UNKNOWN`;
- source, shape, and callable fields inherit `TypeExpr` effective
  nullability;
- row fields and expression value types preserve nullability where the type is
  known;
- unknown schemas, unknown fields, unsupported expression forms, and unknown
  value types publish `ValueTypeKind.UNKNOWN` or unknown row fields with
  `EffectiveNullability.UNKNOWN` under current semantics;
- no scalar registry object stores nullability facts;
- no Decimal precision/scale carrier exists;
- no SQL runtime truth value is represented in `ValueType.nullability`.

## Propagation Rules

The current v0.2 nullability rules are:

| Surface | Current nullability rule |
|---|---|
| Declared `nullable` type expression | `EffectiveNullability.NULLABLE` |
| Declared `not null` type expression | `EffectiveNullability.NON_NULL` |
| Implicit type-expression nullability | `EffectiveNullability.UNKNOWN` |
| Source, shape, and callable field | Inherits the field or parameter `TypeExpr` effective nullability |
| Bare field reference | Preserves the resolved `RowField.nullability` |
| Supported single-input qualified field reference | Preserves the resolved `RowField.nullability` |
| Bool literal | `Bool NON_NULL` |
| Text literal | `Text NON_NULL` |
| Int literal | `Int NON_NULL` |
| Float literal | `Float NON_NULL` |
| Unary numeric `+` / `-` | Preserves operand type and operand nullability |
| Binary arithmetic `+`, `-`, `*`, `%` | Uses the current result type rules and returns conservative `EffectiveNullability.UNKNOWN` |
| Bool `and` / `or` expression | Requires known Bool operands and returns `Bool UNKNOWN` |
| Comparison expression | Types children and returns `Bool UNKNOWN` when children are known |
| `between` expression | Types children and returns `Bool UNKNOWN` when children are known |
| `is null` / `is not null` expression | Returns `Bool NON_NULL` |
| Scalar function call | Uses the current exact built-in signature and returns conservative `EffectiveNullability.UNKNOWN` |
| Computed projection alias | Preserves known expression `ValueType` nullability or publishes unknown output field facts |
| Group-key projection output | Preserves input field nullability |
| Direct aggregate projection output | Preserves the aggregate helper result nullability |
| Unknown schema, unknown field, unsupported expression, or unsupported output | Publishes unknown type facts and `EffectiveNullability.UNKNOWN` where a row field is still exposed |

These rules describe current behavior only. Slice 3 does not add a broader
nullability solver and does not infer non-null results from operators,
predicates, functions, aggregate inputs, `where`, or `satisfying:`.

## Aggregate Result Nullability Matrix

Current aggregate result nullability is owned by aggregate semantic helpers
and remains aligned with the Phase 29 aggregate surface freeze.

| Aggregate | Current result |
|---|---|
| `count()` | `Int NON_NULL` |
| `count(field)` | `Int NON_NULL` |
| `count(source.field)` | `Int NON_NULL` |
| `count_distinct(field)` | `Int NON_NULL` |
| `count_distinct(source.field)` | `Int NON_NULL` |
| `sum(Int)` | `Int NULLABLE` |
| `sum(Float)` | `Float NULLABLE` |
| `sum(Decimal)` | `Decimal NULLABLE` |
| `avg(Int)` | `Float NULLABLE` |
| `avg(Float)` | `Float NULLABLE` |
| `avg(Decimal)` | `Decimal NULLABLE` |
| `min(Int)` / `max(Int)` | `Int NULLABLE` |
| `min(Float)` / `max(Float)` | `Float NULLABLE` |
| `min(Decimal)` / `max(Decimal)` | `Decimal NULLABLE` |
| `min(Date)` / `max(Date)` | `Date NULLABLE` |
| `min(Timestamp)` / `max(Timestamp)` | `Timestamp NULLABLE` |

Aggregate argument acceptance remains unchanged. Slice 3 does not expand
aggregate names, aggregate argument shapes, aggregate argument types,
aggregate result types, or aggregate SQL lowering.

## Predicate Boundaries

Row-level `where` consumes known Bool predicates under current behavior. If a
predicate expression has a known non-Bool value type, Pietto reports the
existing predicate diagnostic. If the predicate value type is unknown,
existing unknown-type, unknown-field, unsupported-expression, and deferred
diagnostic paths remain responsible for fail-closed behavior.

Result-level `satisfying:` consumes known Bool predicates over supported
output names under current behavior. It has its own result-predicate typing
path, requires GROUP BY in the current MVP, rejects unsupported output
references, and records predicate facts only when the result predicate is
supported and typed as Bool.

This predicate boundary is a compile-time Pietto contract. It is not a SQL
runtime truth-table contract. Slice 4 Bool And Predicate Semantics owns the
fuller Bool/predicate contract and the SQL three-valued logic boundary.

## Later Slice Handoff

Slice 3 feeds later Phase 30 slices without implementing them:

- Slice 4 Bool And Predicate Semantics uses the distinction between Pietto
  nullability facts, unknown value types, and SQL three-valued logic
  `UNKNOWN`;
- Slice 7 Operator And Comparison Matrix uses the current result-nullability
  facts for unary, binary, Bool, comparison, and `between` expressions.

Slice 4 is complete as Bool and predicate semantics contract, static audit,
and status work only. Slice 5 Date / Timestamp Formalization is complete as
Date / Timestamp formalization contract, static audit, and status work only.
Slice 6 Decimal Precision / Scale Contract is complete as Decimal precision /
scale contract, static audit, and status work only. Slice 7 Operator And
Comparison Matrix is complete as operator and comparison matrix contract,
static audit, and status work only. Slice 8 remains planned only and requires
separate explicit approval.

## Explicit Non-Goals

Slice 3 does not authorize:

- source implementation changes;
- grammar, generated ANTLR, AST, or parser changes;
- semantic implementation or semantic behavior changes;
- type-system behavior changes;
- diagnostic behavior changes;
- IR implementation or IR model changes;
- SQL backend or SQL lowering changes;
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
- DateTime, Time, timezone, or Interval primitives;
- Currency or Money primitives;
- semantic annotation syntax;
- UUID implementation or broader UUID behavior;
- Enum implementation or broader Enum behavior;
- Bytes or Json behavior expansion;
- native database type metadata;
- broader nullability inference;
- predicate rewrite behavior;
- SQL three-valued logic lowering changes.
