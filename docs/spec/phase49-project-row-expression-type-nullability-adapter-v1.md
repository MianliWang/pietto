# Phase 49 Project Row Expression Type/Nullability Adapter v1

## Purpose

This specification locks Phase 49 Slice 3: Type/nullability adapter for legal
row expressions. Slice 3 is the first private source step for adapting existing
legal row-level expression type/nullability facts into project-private row
expression schema results.

The adapter is private project plumbing. It consumes supplied semantic facts
such as `ValueType(resolved_type, nullability)` and maps them to private
project row expression schema results. It is not a new language feature and it
does not expand expression semantics.

Package version remains `0.1.0`.

## Non-goals

Slice 3 does not implement:

- public behavior or public project semantic API;
- Project JSON v2 row schema, origin, provenance, dependency, or lineage output;
- parser, grammar, or generated ANTLR changes;
- project explain;
- project IR;
- project SQL;
- project `emit-sql`;
- JOIN or relationship behavior;
- runtime or database execution;
- aggregate or grouped output schema;
- bridge/export/RAG/Arrow behavior;
- import/export or module behavior;
- package version, tag, release, publish, upload, signing, or attestation.

Slice 3 does not integrate the adapter into project check, existing project row
schema construction, CLI behavior, IR lowering, SQL generation, or Project JSON
v2 serialization.

## Adapter Boundary

The private adapter lives in `src/pietto/_project/row_expression_schema.py`.
It introduces private implementation helper names:

- `ProjectExpressionSchemaStatus`;
- `ProjectExpressionSchemaReason`;
- `ProjectExpressionSchemaOriginKind`;
- `ProjectExpressionSchemaResult`;
- `adapt_project_row_expression_schema`.

The adapter consumes existing supplied semantic facts. It must not call full
`semantic_api.analyze` in Slice 3. Slice 3 production code must not call
`infer_row_expression`. A future implementation may revisit
`infer_row_expression` only if project path boundaries are explicitly approved
in a later slice.

## Result Shape

The private result carries:

- adapter status;
- deterministic reason;
- output name;
- resolved project type when concrete;
- project row-field nullability when concrete;
- source-native `field_def` only when genuinely source-native;
- private origin/provenance kind;
- source location or fallback reference when available;
- inert dependency and lineage placeholder tuples.

The placeholder tuples do not implement a dependency graph or full lineage
carrier in Slice 3. Full dependency graph and full lineage behavior remain
later Phase 49 slices.

## Behavior

Direct field projections and renamed direct projections may return concrete
results when the field exists in the supplied private input row schema. They
preserve the source-native `field_def`.

Qualified direct projections may return concrete results only when the
qualified name uses the immediate upstream relation qualifier and the field
exists in the supplied private input row schema.

Computed expressions may return concrete results only when the exact expression
has a supplied known `ValueType`. Computed expression results use
`field_def=None`, private `DERIVED_EXPRESSION` origin, and do not synthesize a
derived `FieldDef`.

Bare `let` references may return concrete private adapter results when supplied
`let_value_types` contain a known value type. These results use
`field_def=None` and private `LET_DERIVED` origin. Slice 3 does not populate
project relation row schemas from these facts; selected `let`-derived output
schema remains Slice 7.

Missing or unknown type facts, null literal without a concrete supplied fact,
binary division when current semantic facts keep it unknown, unsupported
expressions, and unavailable project type conversions remain non-concrete.

Aggregate and grouped output schema remain deferred to Phase 50 or later.
Aggregate expressions return a deterministic deferred adapter result. Grouped
output schema remains outside Slice 3 and is represented by existing private
upstream deferred state when available.

Upstream `UNKNOWN`, `DEFERRED`, and `BLOCKED` relation row schema states
short-circuit deterministically to matching adapter statuses and reasons.

The adapter emits no diagnostics. Existing diagnostics and diagnostic ordering
remain owned by existing semantic and project paths and must not be replaced or
duplicated by Slice 3.

## Type Conversion

The adapter reuses existing private project type/nullability representations
from `src/pietto/_project/model.py`.

Builtin scalar semantic types already supported by the private project row
schema model may convert directly to `ProjectResolvedType`. Aliases, enums,
shapes, and other non-builtin symbols require supplied project symbols before
they can convert safely. If conversion cannot be performed safely, the adapter
returns a deterministic non-concrete unavailable-type result.

This conversion does not expand the public type system, public JSON shape,
Semantic Metadata Artifact v1, CLI JSON v1, Project JSON v2, IR, SQL, or public
API behavior.

## Privacy And Roadmap Relationship

Project JSON v2 privacy is preserved. Private adapter results, origins,
provenance, dependency placeholders, lineage placeholders, status, and reason
values are not serialized.

Slice 3 remains aligned with the Slice 2 helper contract:

- Phase 50 aggregate/grouped output row schema should reuse the richer helper
  shape, but no aggregate/grouped schema is implemented here.
- Phase 51 relationship/grain/fanout readiness depends on source-native versus
  derived-field distinctions, but no relationship behavior is implemented here.
- Phase 52 project explain / semantic metadata readiness may consume private
  origin/dependency/lineage facts later, but project explain is not implemented
  here.
- Phase 53 import/export and multi-file ergonomics remain deferred.
- Phase 54 JOIN readiness remains deferred.
- Phase 55 bridge/export/RAG/Arrow readiness remains deferred.

Row-level dependency cycle diagnostics remain readiness-only in Phase 49.
