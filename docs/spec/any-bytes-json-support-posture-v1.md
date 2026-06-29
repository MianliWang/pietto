# Any / Bytes / Json Support Posture v1

## Boundary

Phase 36 Slice 7 selects Option B: tests-only hardening with a docs/spec
decision record. This slice documents and tests the current Any / Bytes / Json
support posture without changing compiler behavior.

Slice 7 does not implement new Any, Bytes, or Json behavior. It does not change
source syntax, grammar, generated ANTLR files, parser or AST behavior, semantic
behavior, IR or SQL behavior, CLI behavior, JSON v1, Project JSON v2, Semantic
Metadata Artifact v1 schema or output, fixtures, goldens, examples, package
metadata, package version, lockfiles, scripts, workflows, tags, release,
publish/upload, signing, or attestation.

## Current Any Facts

`Any` is in `BUILTIN_TYPE_NAMES`.

`Any` remains a top/deferred boundary type. It is a known builtin name for field
declarations, source facts, projection, aliases, and current generic shared
paths. It must not silently imply dynamic typing, runtime casts, permissive SQL
fallback, schema introspection, db pull, runtime/database behavior, or broad
operator compatibility.

There is no special carrier for Any in the semantic or IR model. Existing
semantic facts use the generic `ResolvedType` shape, and existing IR facts use
the generic `TypeRefIR` shape. Semantic Metadata Artifact v1 reports Any with
`support_posture="current"` because it is a known builtin boundary, not because
dynamic Any semantics are implemented.

## Current Bytes Facts

`Bytes` is in `BUILTIN_TYPE_NAMES`.

`Bytes` remains a deferred builtin behavior surface. It is a known builtin name
for field declarations, source facts, projection, aliases, and current generic
shared paths. It does not authorize binary literals, encoding policy, byte
functions or operators, native binary metadata, storage/DDL behavior, schema
introspection, db pull, runtime/database behavior, or SQL dialect-specific
binary semantics.

There is no special carrier for Bytes in the semantic or IR model. Existing
semantic facts use `ResolvedType`, and existing IR facts use `TypeRefIR`.
Semantic Metadata Artifact v1 reports Bytes with
`support_posture="deferred_builtin"`.

## Current Json Facts

`Json` is in `BUILTIN_TYPE_NAMES`.

`Json` remains a deferred builtin behavior surface. It is a known builtin name
for field declarations, source facts, projection, aliases, and current generic
shared paths. It does not authorize structural typing, JSON path extraction,
JSON operators or functions, object/array schema validation, native DB JSON
metadata, storage/DDL behavior, schema introspection, db pull, runtime/database
behavior, runtime JSON processing, or dialect-specific JSON semantics.

There is no special carrier for Json in the semantic or IR model. Existing
semantic facts use `ResolvedType`, and existing IR facts use `TypeRefIR`.
Semantic Metadata Artifact v1 reports Json with
`support_posture="deferred_builtin"`.

## Current Accepted Surfaces

Current accepted surfaces are narrow and generic:

- Any / Bytes / Json field declarations;
- source field facts;
- projection;
- aliases through the generic projection schema;
- Semantic Metadata Artifact v1 type facts using the current support posture
  values;
- direct `count(Bytes field)` and `count(Json field)` through the existing
  concrete non-Any `count(field)` posture;
- PostgreSQL and private MySQL SQL emission for direct `count(Bytes field)` and
  direct `count(Json field)` through existing generic SQL paths.

Bytes/Json field projection and direct `count(field)` remain current accepted
behavior. That fact does not make Bytes or Json fully stable scalar behavior
surfaces.

## Current Fail-closed Surfaces

The following aggregate surfaces remain rejected with existing diagnostic
`PIE-S2314`:

- `count(Any field)`;
- `count_distinct(Any field)`;
- `count_distinct(Bytes field)`;
- `count_distinct(Json field)`;
- `min(Any field)`, `max(Any field)`, `sum(Any field)`, and `avg(Any field)`;
- `min(Bytes field)`, `max(Bytes field)`, `sum(Bytes field)`, and
  `avg(Bytes field)`;
- `min(Json field)`, `max(Json field)`, `sum(Json field)`, and
  `avg(Json field)`.

These fail-closed surfaces are aggregate argument type boundaries, not new
Any/Bytes/Json semantics.

## Risky Generic Shared Surfaces

Comparison, ordering, `order by`, `group by`, and `satisfying` examples for
Any / Bytes / Json are current generic accepted/risky shared paths, not newly
authorized stable type-specific semantics.

These paths travel through shared expression, predicate, grouping, result
predicate, IR, and SQL emit behavior. Slice 7 records their current posture but
does not approve a compatibility guarantee for Any, Bytes, or Json comparison,
ordering, grouping, result predicates, SQL portability, runtime behavior, or
database execution.

## Unsupported And Closed Surfaces

Slice 7 keeps these surfaces closed:

- dynamic Any behavior;
- runtime casts;
- permissive SQL fallback;
- binary literals;
- binary encoding policy;
- byte functions and operators;
- JSON structural typing;
- JSON path extraction;
- JSON operators and functions;
- object/array schema validation;
- native binary metadata;
- native DB JSON metadata;
- storage/DDL behavior;
- schema introspection or db pull;
- runtime/database execution;
- runtime JSON processing;
- Any-specific, Bytes-specific, or Json-specific CLI output fields;
- Any-specific, Bytes-specific, or Json-specific JSON v1 fields;
- Any-specific, Bytes-specific, or Json-specific Project JSON v2 fields;
- Any-specific, Bytes-specific, or Json-specific Semantic Metadata Artifact v1
  schema or output fields;
- SQL golden byte changes;
- fixture or example changes;
- package, workflow, release, publish/upload, signing, or attestation changes.

## Future Prerequisites

Any future Any, Bytes, or Json implementation requires separately approved Gate
1 and Gate 2 decisions and must first define:

- Any dynamic behavior policy;
- Any runtime cast and fallback policy;
- Bytes encoding and binary literal policy;
- Bytes storage and native metadata policy;
- Json structural typing policy;
- Json path, operator, and function policy;
- Json object/array validation policy;
- comparison and ordering policy;
- group-key and satisfying/result predicate policy;
- aggregate matrix policy;
- PostgreSQL and private MySQL dialect portability policy;
- diagnostics and fail-closed policy;
- SQL output compatibility policy;
- public output compatibility policy for CLI text, JSON v1, Project JSON v2,
  and Semantic Metadata Artifact v1;
- validation proving no accidental literal, cast, function, native metadata,
  runtime, JSON, metadata, SQL, fixture, golden, package, or workflow
  expansion.

## Explicit Non-authorization

Slice 7 does not authorize behavior implementation. It does not authorize
dynamic Any behavior, runtime casts, permissive SQL fallback, binary literals,
encoding policy, byte functions or operators, structural Json typing, JSON path
extraction, JSON operators or functions, object/array schema validation, native
binary metadata, native DB JSON metadata, storage/DDL behavior, schema
introspection/db pull, runtime/database execution, runtime JSON processing,
SQL renderer changes, CLI/JSON schema changes, Project JSON v2 changes,
Semantic Metadata Artifact v1 schema or output changes, fixture/golden changes,
examples, package changes, workflow changes, tags, release, publish/upload,
signing, or attestation.
