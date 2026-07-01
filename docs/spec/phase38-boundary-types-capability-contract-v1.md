# Phase 38 Boundary Types Capability Contract v1

## Status And Non-Behavior-Change Guardrail

Phase 38 Slice 4 is Any / Json / Bytes / Enum / UUID Capability Boundary. Slice
4 is docs/spec/static-audit/tests-only and authorizes no behavior change.

This document records the current repo-derived posture for boundary types that
are easy to over-expand by analogy with ordinary scalar types. It does not add
or change source/compiler behavior, grammar, generated ANTLR files, parser
behavior, AST behavior, semantic behavior, IR behavior, SQL lowering, CLI
behavior, JSON v1, Project JSON v2, Semantic Metadata Artifact v1, diagnostic
envelope shape, SQL golden bytes, fixtures/goldens, public status docs,
scripts, workflows, package metadata, lockfiles, package version, release
operations, tags, publish/upload, signing, or attestation.

Package version remains `0.1.0`.

## Current Repo-Derived Boundary Type Posture

The current boundary posture is grounded in existing specs, tests, and source
helpers:

| Type | Current repo-derived posture |
|---|---|
| `Any` | Builtin name in `BUILTIN_TYPE_NAMES`; top/deferred boundary. Field declaration, source facts, projection, aliases, and generic shared paths exist. `count(Any field)`, `count_distinct(Any)`, `sum/avg`, and `min/max` reject with `PIE-S2314`. Not dynamic typing, runtime casts, permissive SQL fallback, native metadata, storage/DDL, or runtime behavior. |
| `Json` | Builtin name; deferred builtin behavior surface. Field declaration, source facts, projection, aliases, and generic shared paths exist. Direct `count(Json field)` is accepted and SQL-emitting. `count_distinct(Json)`, `sum/avg`, and `min/max` reject with `PIE-S2314`. No JSON literal syntax, JSON path extraction, structural typing, operators/functions, native metadata, storage/DDL, or runtime JSON behavior. |
| `Bytes` | Builtin name; deferred builtin behavior surface. Field declaration, source facts, projection, aliases, and generic shared paths exist. Direct `count(Bytes field)` is accepted and SQL-emitting. `count_distinct(Bytes)`, `sum/avg`, and `min/max` reject with `PIE-S2314`. No binary literal, encoding policy, byte operators/functions, native metadata, storage/DDL, or runtime behavior. |
| Enum | Not builtin. Semantic `TypeKind.ENUM`, IR `EnumIR`, and metadata posture `metadata_only` exist. Field/projection/readiness facts exist. All aggregate rows including `count(Enum field)`, `count_distinct(Enum)`, `sum/avg`, and `min/max` reject with `PIE-S2314`. No literals, member references, casts, native DB enum metadata, DDL/storage, or runtime behavior. |
| `UUID` | Builtin name; `limited_frozen` support posture. Field declaration, source facts, projection, aliases, direct `count(UUID field)`, and direct `count_distinct(UUID field)` are current. `sum/avg` and `min/max(UUID)` remain closed/deferred. UUID comparison/order/group/satisfying are risky generic shared paths, not stable UUID semantics. No literals, casts, native metadata, storage/DDL, or runtime behavior. |

Evidence anchors include `docs/spec/any-bytes-json-support-posture-v1.md`,
`docs/spec/enum-support-resolution-v1.md`,
`docs/spec/uuid-support-completion-v1.md`,
`docs/spec/phase38-type-capability-matrix-contract-v1.md`,
`src/pietto/semantic/catalog.py`, `src/pietto/semantic/aggregates.py`,
`tests/test_phase36_any_bytes_json_support_posture.py`,
`tests/test_phase36_enum_support_resolution.py`, and
`tests/test_phase36_uuid_support_completion.py`.

## `Any` Boundary

`Any` remains an opaque top/deferred boundary type, not dynamic typing.

Current accepted `Any` surfaces are limited to the generic paths already
present for known field types:

- field declarations;
- source facts;
- projection;
- aliases through the generic projection schema;
- generic shared paths where they already exist.

Those current paths do not grant broad scalar semantics. `Any` is projectable
and lowerable only through current generic field/projection paths. It does not
authorize runtime casts, permissive SQL fallback, dynamic operator dispatch,
native metadata, storage/DDL behavior, schema introspection, db pull,
runtime/database execution, or package/release behavior.

`count(Any field)` remains rejected with `PIE-S2314`. Future `Any`
countability requires explicit lowerable-count policy, refinement, or metadata.
It must not be introduced as accidental dynamic typing.

## `Json` Boundary

`Json` remains a deferred builtin behavior surface.

Current accepted Json surfaces include field declarations, source facts,
projection, aliases through the generic projection schema, and direct
`count(Json field)` through the existing count path. PostgreSQL and private
MySQL SQL emit direct `COUNT(field)` for the currently accepted direct-count
shape.

Json direct count support does not imply structural typing, JSON literal
syntax, JSON path extraction, JSON operators, JSON functions, object/array
schema validation, native DB JSON metadata, storage/DDL behavior, schema
introspection, db pull, runtime JSON processing, runtime/database execution, or
dialect-specific JSON semantics.

`count_distinct(Json field)`, `min(Json field)`, `max(Json field)`,
`sum(Json field)`, and `avg(Json field)` remain rejected with `PIE-S2314`.

## SQL `NULL` Versus JSON Literal `null`

For `count(Json field)`, the relevant nullness is SQL nullness of the field.

- `count(Json field)` counts SQL non-`NULL` field values.
- A JSON literal `null` stored in a non-`NULL` JSON value is counted.
- A SQL `NULL` field value is not counted.

Slice 4 introduces no JSON literal syntax, JSON path extraction, runtime JSON
processing, JSON native metadata, storage/DDL behavior, or dialect-specific
JSON semantics. Future Json behavior changes must define SQL `NULL` versus
JSON literal `null` policy explicitly.

## `Bytes` Boundary

`Bytes` remains a deferred builtin behavior surface.

Current accepted Bytes surfaces include field declarations, source facts,
projection, aliases through the generic projection schema, and direct
`count(Bytes field)` through the existing count path. PostgreSQL and private
MySQL SQL emit direct `COUNT(field)` for the currently accepted direct-count
shape.

Bytes direct count support does not imply binary literal syntax, encoding
policy, byte operators, byte functions, native binary metadata, storage/DDL
behavior, schema introspection, db pull, runtime/database execution, or
dialect-specific binary semantics.

`count_distinct(Bytes field)`, `min(Bytes field)`, `max(Bytes field)`,
`sum(Bytes field)`, and `avg(Bytes field)` remain rejected with `PIE-S2314`.

## Enum Boundary

Enum remains `metadata_only`, not a builtin scalar.

Current Enum surfaces include enum definitions, `TypeKind.ENUM`,
`TypeKindIR.ENUM`, `EnumIR` metadata, enum field facts, projection/readiness
facts, and Semantic Metadata Artifact v1 posture reporting. These are metadata
readiness facts, not stable SQL scalar behavior.

All current Enum aggregate rows fail closed with `PIE-S2314`:

- `count(Enum field)`;
- `count_distinct(Enum field)`;
- `min(Enum field)`;
- `max(Enum field)`;
- `sum(Enum field)`;
- `avg(Enum field)`.

Enum has no literals, member references, casts, native DB enum metadata,
DDL/storage behavior, schema introspection, db pull, runtime/database execution,
or broad SQL behavior.

Future Enum count, order, min/max, distinct, group-key, or satisfying behavior
requires an Enum scalar and SQL portability policy first. Enum ordering must
require explicit order metadata before `min/max` or stable ordering can be
implemented.

## `UUID` Boundary

`UUID` remains `limited_frozen`.

Current UUID surfaces include field declarations, source facts, projection,
aliases through the generic projection schema, direct `count(UUID field)`, and
direct `count_distinct(UUID field)`. These current paths do not imply stable
UUID ordering, native UUID storage, dialect-specific UUID behavior, or runtime
UUID behavior.

`min(UUID field)` and `max(UUID field)` remain rejected/deferred. `sum(UUID
field)` and `avg(UUID field)` remain rejected/deferred. UUID
comparison/order/group/satisfying paths are risky generic shared paths, not
stable UUID semantics.

UUID has no literal syntax, casts, native metadata, storage/DDL behavior,
schema introspection, db pull, runtime/database execution, or public output
schema expansion.

UUID ordering or `min/max` requires explicit metadata or a
warning/fail-closed policy before implementation.

## Metadata Vocabulary Without Implementation

Slice 4 documents metadata vocabulary only. It does not implement metadata
syntax, metadata schema fields, semantic carriers, public JSON fields, SQL
behavior, runtime behavior, native DB metadata pull, storage/DDL behavior, or
schema introspection.

Potential Enum order sources:

- Pietto declaration order;
- imported native DB enum order;
- explicit lexical order;
- custom order.

Potential UUID metadata:

- `uuid_version`;
- `uuid_ordering`;
- `native` ordering;
- `lexical` ordering;
- `binary` ordering;
- `time` ordering;
- `custom` ordering.

Potential `Any` metadata/refinement:

- explicit refinement;
- native metadata;
- operator-constrained capability.

Potential Json and Bytes native metadata:

- JSON native type metadata remains deferred;
- JSON shape metadata remains deferred;
- Bytes native storage metadata remains deferred;
- Bytes encoding metadata remains deferred.

## Capability Interaction Matrix

Slice 4 aligns boundary types with the Slice 3 capability vocabulary:

| Capability term | Boundary-type meaning |
|---|---|
| `lowerable` | Only current accepted field/projection/aggregate SQL paths are lowerable. |
| `projectable` | Generic field projection exists; it is not full scalar semantics. |
| `null-checkable` | Generic expression machinery exists; it is not a type-specific capability contract. |
| `countable` | Current direct-count matrix: `Json`, `Bytes`, and `UUID` yes; `Any` and Enum no. |
| `orderable` | Not granted to these boundary types by generic comparisons or order-by paths. |
| `distinct-compatible` | Only `UUID` among these five has direct `count_distinct`. |
| `metadata-backed` | Enum and `UUID` have metadata/support postures; this is not native DB behavior. |
| `dialect-lowerable` | Accepted PostgreSQL/private MySQL emit paths only. |
| `serialization-dependent` | Future broad distinct or opaque comparisons must define serialization and equality first. |
| `collation-dependent` | Text and Enum ordering must not expand by analogy without explicit policy. |

This contract avoids user-visible `hashable`; current repo vocabulary supports
`distinct-compatible`, not hash behavior.

## Aggregate Behavior Preservation Matrix

Slice 4 preserves this current aggregate behavior:

| Type | `count(field)` | `count_distinct(field)` | `min/max(field)` | `sum/avg(field)` |
|---|---|---|---|---|
| `Any` | rejected with `PIE-S2314` | rejected with `PIE-S2314` | rejected with `PIE-S2314` | rejected with `PIE-S2314` |
| `Json` | accepted; PostgreSQL/MySQL SQL emits `COUNT(field)` | rejected with `PIE-S2314` | rejected with `PIE-S2314` | rejected with `PIE-S2314` |
| `Bytes` | accepted; PostgreSQL/MySQL SQL emits `COUNT(field)` | rejected with `PIE-S2314` | rejected with `PIE-S2314` | rejected with `PIE-S2314` |
| Enum | rejected with `PIE-S2314`; no longer reaches backend `PIE-B1000` | rejected with `PIE-S2314` | rejected with `PIE-S2314` | rejected with `PIE-S2314` |
| `UUID` | accepted | accepted; result `Int not null` | rejected/deferred; no current support | rejected/deferred; no current support |

This matrix is preservation only. It does not widen `count(expression)`,
`count_distinct(expression)`, `min/max(expression)`, aggregate filters, grouped
behavior, result predicates, SQL lowering, or public output behavior.

## Deferred And Prohibited Surfaces

Slice 4 does not implement:

- `count(Any field)` behavior change;
- `count(Enum field)` behavior change;
- broad `count(expression)`;
- `count_if(predicate)`;
- broad `count_distinct(expression)`;
- `count_distinct(Json/Bytes/Any/Enum)`;
- `min/max(UUID)`;
- `min/max(Enum)`;
- `min/max(Json/Bytes/Any)`;
- Enum ordering metadata implementation;
- UUID ordering metadata implementation;
- `Any` refinement;
- Json path/type semantics;
- Bytes operators/literals/encoding;
- native DB metadata pull;
- storage/DDL/runtime behavior;
- parser/AST/grammar/generated changes;
- semantic/IR/SQL/CLI/JSON behavior changes;
- fixtures/goldens changes;
- scripts/workflows/package/release changes.

## Future Implementation Prerequisites

Any later behavior implementation requires a separate Gate 1 and Gate 2 with
approved implementation files, validation commands, SQL portability proof,
fixture/golden policy, public output compatibility, diagnostic policy, and
release non-authorization.

Future boundary-type work must define explicit policy for:

- SQL nullness versus type-level nullability;
- SQL `NULL` versus JSON literal `null`;
- lowerability and dialect portability;
- equality and distinct compatibility;
- ordering, collation, normalization, serialization, and metadata ownership;
- Enum scalar behavior and order metadata;
- UUID ordering metadata and fail-closed/warning policy;
- `Any` refinement and capability ownership;
- Json path/type behavior;
- Bytes literal, encoding, and operator behavior;
- native database metadata boundaries;
- public output compatibility;
- fail-closed diagnostics;
- validation proving no accidental syntax, semantic, IR, SQL, JSON, metadata,
  fixture/golden, package, workflow, or release expansion.

## Public Surface And Release Non-Authorization

Slice 4 keeps public surfaces unchanged:

- source/compiler behavior unchanged;
- grammar and generated parser inventory unchanged;
- parser and AST behavior unchanged;
- semantic behavior unchanged;
- IR behavior unchanged;
- SQL behavior unchanged;
- CLI text output unchanged;
- CLI JSON v1 unchanged;
- Project JSON v2 unchanged;
- Semantic Metadata Artifact v1 unchanged;
- diagnostic envelope unchanged;
- SQL golden bytes unchanged;
- fixtures/goldens unchanged;
- scripts/workflows unchanged;
- package metadata unchanged;
- package version remains `0.1.0`;
- no package/workflow/release metadata change;
- no tag/release/publish/upload/signing/attestation.
