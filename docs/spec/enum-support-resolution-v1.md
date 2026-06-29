# Enum Support Resolution v1

## Boundary

Phase 36 Slice 5 resolves one unsafe Enum path. It does not make `Enum` a
builtin scalar, and it does not implement broad Enum SQL behavior.

The approved behavior change is narrow: direct `count(Enum field)` now fails in
semantic aggregate validation with existing diagnostic `PIE-S2314`. It no
longer reaches IR and PostgreSQL/private MySQL SQL backend fail-closed output as
`PIE-B1000`.

Slice 5 does not change grammar, generated ANTLR files, parser or AST behavior,
IR model shape, SQL renderers, CLI behavior, JSON v1, Project JSON v2, Semantic
Metadata Artifact v1 schema or output, fixtures, goldens, examples, scripts,
package metadata, package version, lockfiles, workflows, tags, release,
publish/upload, signing, or attestation.

## Current Enum Facts

- `Enum` is not in `BUILTIN_TYPE_NAMES`.
- Enum definitions exist in the source language.
- The semantic model has `TypeKind.ENUM`.
- The IR model has `TypeKindIR.ENUM` and `EnumIR` metadata.
- Metadata/explain reports enum fields as metadata/readiness with
  `support_posture="metadata_only"`.
- There are no Enum literals.
- There are no Enum member references.
- There are no Enum casts.
- There is no native DB enum metadata.
- There is no Enum DDL or storage behavior.
- There is no Enum runtime/database execution behavior.

These facts make Enum a metadata/readiness surface, not a fully stable SQL
scalar.

## Problem

Before Slice 5, direct `count(Enum field)` was accepted by semantic aggregate
validation and lowered into IR. PostgreSQL and private MySQL SQL emit then
failed closed with backend diagnostic `PIE-B1000`.

That was an unsafe accepted-to-backend-failure path. The source program looked
semantically valid, but the backend could not emit stable SQL for the accepted
Enum aggregate.

## Decision

Direct `count(Enum field)` must fail closed in semantic aggregate validation
using existing diagnostic `PIE-S2314`.

This decision keeps the current aggregate boundaries:

- `count(Enum field)` is rejected with `PIE-S2314`.
- `count_distinct(Enum field)` remains rejected with `PIE-S2314`.
- `min(Enum field)` remains rejected with `PIE-S2314`.
- `max(Enum field)` remains rejected with `PIE-S2314`.
- `sum(Enum field)` remains rejected with `PIE-S2314`.
- `avg(Enum field)` remains rejected with `PIE-S2314`.

Broader generic paths remain unresolved and deferred. Slice 5 does not define a
final Enum comparison matrix, ordering policy, group-key policy, or
`satisfying`/result predicate policy.

## Explicit Non-goals

Slice 5 does not authorize:

- enum literals;
- enum member references;
- casts;
- native DB enum metadata;
- DDL/storage behavior;
- runtime/database execution behavior;
- schema introspection or db pull;
- broad enum comparison, ordering, group-key, or `satisfying` policy;
- broad SQL behavior;
- SQL golden byte updates;
- CLI behavior changes;
- JSON v1 schema changes;
- Project JSON v2 schema changes;
- Semantic Metadata Artifact v1 schema or output changes;
- package, workflow, or release changes.

## Future Prerequisites

Any future Enum behavior work requires separately approved Gate 1 and Gate 2
decisions and must first define:

- enum comparison policy;
- enum ordering policy;
- enum group-key policy;
- enum satisfying/result predicate policy;
- enum aggregate matrix policy;
- PostgreSQL/private MySQL portability policy;
- public output compatibility policy;
- diagnostics policy;
- validation proving no accidental literal, cast, native metadata, runtime,
  JSON, metadata, or SQL expansion.
