# Phase 49 Computed Alias Project Row Schema MVP v1

## Purpose

This contract defines the Phase 49 Slice 4 MVP for private project row schema
facts for computed aliases.

The purpose is narrow: when a project relation has a concrete upstream row
schema and selects an aliased row-level expression that existing Pietto
row-expression semantics can type, project semantic construction may record a
private concrete `ProjectRowField` for that alias.

## Scope

Slice 4 supports only existing legal row-level typed expressions. It does not
expand the expression language.

Supported expression type and nullability facts come from the existing
`ValueType(resolved_type, nullability)` model. Field references, qualified
field references, literals, supported unary and binary operators, comparisons,
`between`, `is null` / `is not null`, and supported built-in scalar calls are
eligible only to the extent the existing semantic row-expression inference
already produces a known `ValueType`.

Computed alias fields are project-private row schema facts. They use
`field_def=None` and must not synthesize a derived `FieldDef`.

## Integration Boundary

Project row schema construction may use a private helper module and the Slice 3
private adapter. The helper is allowed to make a narrow `infer_row_expression`
call only to obtain `ValueType` facts for selected computed alias expressions
from a concrete input row schema.

The implementation must not call full `semantic_api.analyze` or the full
semantic analyzer. Direct `pietto.semantic` imports must not be added to
`src/pietto/_project/model.py`; semantic imports remain isolated in the private
helper module.

Project JSON v2 remains private and unchanged. No row schema, origin,
provenance, dependency, lineage, or adapter facts are serialized.

## Behavior

When the upstream row schema is concrete and a computed alias expression has a
known `ValueType`, project row schema construction records a concrete
`ProjectRowField` with:

- the adapter-provided resolved type;
- the adapter-provided nullability;
- `field_def=None`;
- private expression provenance only.

Direct projections and renamed direct projections keep their existing behavior
and preserve the source-native `field_def`.

Missing or unknown `ValueType` facts, `null` literal without a concrete supplied
fact, division when current semantic facts keep `/` unknown, unsupported
expressions, and unavailable project type conversion remain non-concrete using
existing private availability behavior.

Aggregate and grouped output schema remain deferred. Selected `let`-derived
output schema remains deferred until Slice 7.

## Diagnostics

Slice 4 adds no public diagnostics. Existing project diagnostics and diagnostic
ordering are preserved.

The narrow helper may use a local diagnostics list to satisfy the existing
`infer_row_expression` API, but those diagnostics are not emitted from project
semantic construction.

## Privacy

Project JSON v2 does not expose project row schema, origin, provenance,
dependency, lineage, or adapter facts. JSON v2 top-level shape and key order
remain unchanged.

## Future Work

Origin/provenance hardening remains Slice 5. Project `let` facts remain Slice 6.
Selected `let` schema remains Slice 7. The private row-level dependency graph
remains Slice 9. Lineage remains Slices 10 and 11. Aggregate and grouped output
schema remain Phase 50 or later.

No project explain, project IR, project SQL, project `emit-sql`,
JOIN/relationship behavior, bridge/export/RAG/Arrow behavior, import/export,
multi-file behavior, runtime/database execution, parser/grammar/generated
change, package version change, or release operation is included in Slice 4.
