# UUID Support Completion v1

## Boundary

Phase 36 Slice 4 is docs/spec/static-audit only. It documents the current UUID
support boundary and does not change behavior.

Slice 4 does not change source/compiler behavior, source implementation,
grammar, generated ANTLR files, parser or AST behavior, semantic behavior, IR or
SQL behavior, CLI behavior, JSON v1, Project JSON v2, Semantic Metadata
Artifact v1 schema or output, fixtures, goldens, examples, scripts, package
metadata, package version, lockfiles, workflows, tags, release, publish/upload,
signing, or attestation.

Slice 4 does not make `UUID` a fully stable UUID scalar. `UUID` remains
limited/frozen until a later approved slice defines the missing behavior and
public output policies.

## Current UUID Facts

- `UUID` is a built-in scalar name.
- `UUID` has limited/frozen support posture.
- `UUID` has generic semantic type facts through the existing `ResolvedType`
  and `ValueType` model.
- `UUID` has generic IR type identity through `TypeRefIR`.
- Semantic Metadata Artifact v1 reports UUID type facts with
  `support_posture="limited_frozen"`.
- There is no UUID-specific carrier.
- There is no native DB metadata for UUID.
- There is no UUID storage or DDL behavior.
- There is no UUID runtime/database execution behavior.
- There is no UUID literal syntax.
- There are no UUID casts.

## Supported Current Surfaces

The current safe documented UUID support surfaces are:

- field declaration and shape facts;
- source field facts;
- projection;
- aliases through the generic projection schema;
- direct `count(UUID field)`;
- direct `count_distinct(UUID field)`;
- metadata/explain `support_posture="limited_frozen"`;
- generic CLI, JSON, and SQL paths where already covered by existing tests.

These supported surfaces do not imply native UUID storage semantics, stable UUID
comparison semantics, stable UUID ordering semantics, dialect-specific UUID
treatment, or broader SQL behavior.

## Risky Generic Surfaces

The following UUID-adjacent behavior can pass through shared generic paths and
therefore remains risky until a later approved slice defines exact policy:

- equality comparisons;
- inequality comparisons;
- ordering comparisons;
- `order by UUID` field;
- `group by UUID` field;
- `satisfying` predicates involving UUID;
- SQL portability for PostgreSQL and private MySQL;
- UUID `min` and `max` boundary;
- any behavior that could imply stable UUID ordering;
- any behavior that could imply native UUID semantics;
- any behavior that could imply dialect-specific UUID treatment.

Slice 4 documents these risks only. It does not add fail-closed diagnostics and
does not widen or narrow the shared semantic, IR, SQL, CLI, JSON, or metadata
behavior paths.

## Unsupported And Closed Surfaces

The following surfaces remain unsupported or closed in Slice 4:

- UUID literals;
- UUID casts;
- native DB metadata;
- DDL/storage behavior;
- schema introspection or db pull;
- runtime/database execution;
- UUID-specific JSON/API/schema fields;
- UUID-specific Semantic Metadata Artifact v1 schema or output fields;
- broad SQL behavior expansion;
- UUID `min` or `max` support unless separately approved;
- UUID `sum` or `avg`;
- package, workflow, or release behavior.

Closed surfaces also include grammar changes, generated parser changes, parser
or AST behavior changes, fixture changes, golden SQL byte changes, CLI output
changes, JSON v1 schema changes, Project JSON v2 schema changes, Semantic
Metadata Artifact v1 schema/output changes, package version changes, tags,
release, publish/upload, signing, and attestation.

## Future Prerequisites

Any future UUID behavior work requires separately approved Gate 1 and Gate 2
decisions and must first define:

- precise comparison policy;
- ordering policy;
- group-key policy;
- satisfying/result predicate policy;
- aggregate matrix policy for `min`, `max`, `count`, and `count_distinct`;
- dialect portability policy for PostgreSQL and private MySQL;
- public output compatibility policy;
- diagnostics/fail-closed policy;
- validation proving no accidental literal, cast, native metadata, runtime,
  JSON, metadata, or SQL expansion.

## Explicit Non-authorization

Slice 4 does not implement UUID behavior changes. Slice 4 does not add
fail-closed diagnostics.

Slice 4 does not approve UUID literals, casts, native metadata, DDL, runtime,
storage, SQL golden updates, JSON/schema updates, Project JSON v2 schema
updates, Semantic Metadata Artifact v1 schema/output changes, CLI output
changes, package metadata changes, package version changes, workflow changes,
release, publish/upload, signing, or attestation.
