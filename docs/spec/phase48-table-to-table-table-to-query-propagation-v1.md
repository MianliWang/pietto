# Phase 48 Table-to-table / Table-to-query Propagation v1

This specification locks Phase 48 Slice 4 for one-hop table-upstream row
schema propagation.

## Scope

Phase 48 remains Query-to-query Row Schema Propagation. Slice 4 implements only
one-hop table-upstream propagation:

- existing direct-source relation row schemas from Phase 47 remain supported;
- a downstream `TableDef` may receive a private concrete row schema from an
  upstream `TableDef`;
- a downstream `QueryDef` may receive a private concrete row schema from an
  upstream `TableDef`;
- the upstream table must be a direct-source concrete table schema seed;
- the downstream select list must use only direct field projections supported
  by the flat relation schema model.

Do not use a schema newly propagated in Slice 4 as an upstream seed. That would
be multi-hop propagation and remains deferred.

## Supported Projection Forms

For a downstream relation whose immediate upstream table is `staged`, Slice 4
supports these projection forms:

- bare field: `id`;
- immediate-upstream-qualified field: `staged.id`;
- renamed bare field: `user_id = id`;
- renamed immediate-upstream-qualified field: `user_id = staged.id`.

The output schema preserves select order, output alias names, resolved project
type facts, nullability, and the original `FieldDef` where available.

## Flat Relation Schema Model

Downstream relations consume only the flat output schema of the immediate
upstream table. Original source names remain private provenance and future
explain metadata; they are not downstream query paths.

When `from staged`, `id` and `staged.id` may reference the immediate upstream
table output field. `users.id` remains invalid when `users` is only the
original source behind `staged`. `staged.users.id` remains unsupported
lineage-path syntax.

## Schema Availability State Population

Slice 4 populates `ProjectSemanticModel.relation_row_schema_states` narrowly:

- direct-source concrete table schemas may become `CONCRETE` states with
  `DIRECT_SOURCE_CONCRETE`;
- one-hop concrete downstream table/query schemas may become `CONCRETE` states
  with `TABLE_UPSTREAM_CONCRETE`.

Slice 4 does not broadly populate `UNKNOWN`, `DEFERRED`, or `BLOCKED` states.
Broad upstream unknown, absent, deferred, and blocked handling remains Slice 7.

Direct-source query schemas remain existing private relation row schemas, but
they are not table seeds for Slice 4 propagation.

## Diagnostics

Slice 4 adds no diagnostic family, no diagnostic code, and no diagnostic
wording change.

Existing `PIE-S2102` remains the diagnostic for missing fields, wrong immediate
qualifiers, original-source qualifiers, and unsupported multi-part dotted
direct fields when checking direct projections over a concrete upstream schema.

Existing `PIE-S2301` remains authoritative for unresolved relation references.
Existing `PIE-S2302` remains authoritative for relation cycles.

## Privacy And Public Surface

Project JSON v2 top-level shape remains unchanged. Slice 4 serializes no
private row schema facts, no private schema availability state facts, no
private status values, and no private reason values.

Slice 4 adds no public project semantic API and does not change CLI/check
orchestration.

## Explicit Non-goals

Slice 4 does not implement:

- query-to-query propagation;
- table-from-query propagation;
- multi-hop propagation;
- propagation from propagated table schemas;
- computed alias schema;
- `let` schema;
- aggregate schema;
- grouped output schema;
- project IR;
- project SQL emit;
- project `emit-sql`;
- project `explain`;
- public project semantic API;
- Project JSON v2 public shape changes;
- private fact serialization;
- parser, grammar, or generated parser changes;
- JOIN or relationship behavior;
- runtime or database execution;
- package version, tag, release, publish, upload, signing, or attestation.

In short: No query-to-query propagation. No table-from-query propagation. No
multi-hop propagation.
