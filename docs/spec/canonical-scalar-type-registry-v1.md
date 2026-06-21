# Canonical Scalar Type Registry v1

## Status

Phase 30 Slice 2 is complete as canonical scalar type registry contract,
static audit, and status work only.

This contract defines the v0.2 canonical scalar registry vocabulary for
current built-in type names, concrete scalar core types, boundary types,
deferred behavior built-ins, limited/frozen identifier scalar behavior, and
the Enum distinction.

Slice 2 does not add a scalar registry object. It does not change source
implementation, type resolution, expression typing, aggregate validation,
diagnostics, IR, SQL lowering, CLI behavior, JSON behavior, public APIs,
fixtures, goldens, package metadata, or CI.

## Trusted Baseline

Slice 2 starts from the completed Phase 30 Slice 1 baseline:

- HEAD: `374698aec9b9774f1df1c1c3aa7132159f7f65a0`;
- commit: `Plan Phase 30 core type system stabilization`;
- CI run: `27885002942 success`.

Phase 30 Slice 1 is complete as candidate decision, type-system contract,
static audit, and status work only. v0.2 is not complete yet. Phase 30, Phase
31, and Phase 32 remain required before v0.2 stable completion.

## Candidate Decision

| Candidate | Fit | Risk | Decision |
|---|---:|---:|---|
| Slice 2 docs/spec/static-audit/status only | High | Low | Chosen. |
| Minimal scalar registry implementation artifact | Medium | Medium | Rejected for Slice 2; no current consumer requires it, and trait shape depends on later nullability, predicate, temporal, Decimal, operator, and comparison contracts. |
| Broad type-system behavior implementation | Low | High | Rejected; it could change semantic, diagnostic, IR, SQL, CLI, JSON, aggregate, fixture, golden, and public API behavior. |

The selected Slice 2 direction is contract-first. The registry vocabulary is a
documentation and static-audit contract only.

## Current Repo Facts

Slice 2 grounds the registry contract in current implementation facts:

- built-in type names are string entries in `BUILTIN_TYPE_NAMES`;
- current built-in names are `Any`, `Bool`, `Bytes`, `Date`, `Decimal`,
  `Float`, `Int`, `Json`, `Text`, `Timestamp`, and `UUID`;
- `Enum` is represented through enum/type-definition support and semantic type
  kinds, not as a normal built-in scalar name;
- `ResolvedType` carries `name`, `kind`, and optional `definition`;
- `ValueType` carries `resolved_type`, `nullability`, and `kind`;
- `count_distinct(field)` currently accepts direct fields of type `Bool`,
  `Int`, `Float`, `Decimal`, `Text`, `Date`, `Timestamp`, and `UUID`;
- the Phase 29 aggregate surface freeze preserves the current direct-field
  `count_distinct(field)` and `count_distinct(source.field)` behavior;
- no scalar registry object, trait enum, registry API, or Decimal
  precision/scale carrier exists.

## Canonical Registry Classification

The current built-in scalar names are:

- `Any`;
- `Bool`;
- `Bytes`;
- `Date`;
- `Decimal`;
- `Float`;
- `Int`;
- `Json`;
- `Text`;
- `Timestamp`;
- `UUID`.

The v0.2 concrete scalar core is:

- `Bool`;
- `Int`;
- `Float`;
- `Decimal`;
- `Text`;
- `Date`;
- `Timestamp`.

`Any` is the boundary/top scalar classification. `Any` must not hide
unsupported behavior. Specific acceptance or rejection of `Any` remains owned
by current semantic checks and later contracts.

`Bytes` and `Json` are deferred/unsupported behavior built-ins for v0.2. Slice
2 does not expand binary or JSON operator, comparison, aggregate, SQL lowering,
literal, cast, function, dialect, JSON, CLI, diagnostic, or public API
behavior.

`UUID` is a limited/frozen identifier scalar:

- `UUID` is a current built-in name;
- `UUID` is accepted only where existing frozen behavior already accepts it,
  especially direct-field `count_distinct(UUID)` and
  `count_distinct(source.uuid_field)`;
- broader UUID behavior remains deferred, including literals, casts,
  functions, storage semantics, DDL, general comparison guarantees, wider SQL
  behavior, dialect compatibility, and public API exposure;
- Phase 31 must make the UUID readiness or narrow-MVP decision before broader
  UUID behavior can be stabilized.

The `identifier` label is only a registry classification label. It does not
imply primary-key semantics, foreign-key semantics, relationship semantics,
cardinality, grain, row identity, business ID validation, general comparison
behavior, cast behavior, SQL storage behavior, or public API behavior.

`Enum` is a non-builtin semantic type kind:

- `Enum` is not in `BUILTIN_TYPE_NAMES`;
- enum declarations are represented through enum/type-definition support and
  `TypeKind.ENUM`;
- broader Enum SQL behavior remains deferred to Phase 31 readiness,
  narrow-MVP, or explicit deferral decision;
- Slice 2 does not implement an Enum primitive, Enum scalar registry entry,
  Enum SQL lowering, Enum DDL, Enum runtime mapping, Enum value validation
  changes, or public API behavior.

## Trait Vocabulary

The registry contract records these trait labels for later contracts:

| Trait | Scalars |
|---|---|
| numeric | `Int`, `Float`, `Decimal` |
| exact numeric | `Int`, `Decimal` |
| approximate numeric | `Float` |
| text | `Text` |
| boolean | `Bool` |
| temporal | `Date`, `Timestamp` |
| binary | `Bytes` |
| json | `Json` |
| identifier | `UUID` |
| boundary/top | `Any` |
| deferred/unsupported-before-v0.2 | `Bytes`, `Json`, broader `UUID` behavior, broader Enum behavior |

These traits are contract vocabulary only in Slice 2. They do not authorize
new operators, comparisons, aggregate forms, SQL lowering behavior,
diagnostics, JSON behavior, CLI behavior, public API behavior, type-system
behavior, or runtime behavior.

## Registry Facts Versus Expression Facts

Future scalar registry facts may include:

- canonical scalar identity;
- category or trait labels;
- concrete-core, boundary, limited/frozen, or deferred status;
- later-slice handoff notes;
- restrictions that prevent accidental behavior expansion.

Expression value facts remain outside the registry:

- `ResolvedType.name`;
- `ResolvedType.kind`;
- `ResolvedType.definition`;
- `ValueType.resolved_type`;
- `ValueType.nullability`;
- `ValueType.kind`.

Slice 2 does not add carriers for Decimal precision/scale, dialect physical
metadata, native database type metadata, semantic annotations, source
constraints, aggregate result metadata, runtime state, relationship metadata,
or public API fields.

## Later Slice Handoff

Slice 2 feeds later Phase 30 slices without implementing them:

- Slice 3 Nullability Propagation Contract uses registry identity without
  storing nullability in registry facts;
- Slice 4 Bool And Predicate Semantics uses the `boolean` trait and keeps SQL
  three-valued logic separate from `ValueType.nullability`;
- Slice 5 Date / Timestamp Formalization uses the `temporal` trait and keeps
  DateTime, Time, Interval, and timezone behavior deferred;
- Slice 6 Decimal Precision / Scale Contract uses `numeric` and
  `exact numeric` vocabulary without adding precision/scale carriers now;
- Slice 7 Operator And Comparison Matrix uses concrete-core, limited/frozen,
  boundary, and deferred classifications to state supported, rejected, and
  deferred pairs.

Slice 3 is complete as nullability propagation contract, static audit, and
status work only. Slice 4 is complete as Bool and predicate semantics
contract, static audit, and status work only. Slice 5 is complete as Date /
Timestamp formalization contract, static audit, and status work only. Slice 6
is complete as Decimal precision / scale contract, static audit, and status
work only. Slice 7 is complete as operator and comparison matrix contract,
static audit, and status work only. Slice 8 remains planned only and requires
separate explicit approval.

## Explicit Non-Goals

Slice 2 does not authorize:

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
- native database type metadata.
