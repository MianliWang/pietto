# Phase 48 Schema Availability State Carrier v1

This specification locks Phase 48 Slice 3 for the private schema availability
state carrier and propagation readiness scaffold.

## Scope

Phase 48 remains Query-to-query Row Schema Propagation. Slice 3 implements only
the private carrier shape needed by later propagation slices:

- private status vocabulary: `CONCRETE`, `UNKNOWN`, `DEFERRED`, `BLOCKED`;
- private reason vocabulary for direct-source readiness, unknown schema,
  duplicate output names, deferred Phase 48 behavior, unresolved relation
  blocking, cycle blocking, and upstream unknown/deferred/blocked readiness;
- private `ProjectRelationRowSchemaState`;
- private `ProjectSemanticModel.relation_row_schema_states`.

Slice 3 does not populate actual states from checker/build logic. The private
mapping defaults to empty so existing project semantic model callers do not
need to change in Slice 3.

## Carrier Contract

`ProjectRelationRowSchemaState` is project-private:

```text
ProjectRelationRowSchemaState
  status: CONCRETE | UNKNOWN | DEFERRED | BLOCKED
  schema: ProjectRowSchema | None
  reason: ProjectRelationRowSchemaReason
```

The carrier invariants are:

- `CONCRETE` requires a non-unknown `ProjectRowSchema`;
- `UNKNOWN` requires an unknown `ProjectRowSchema`;
- `DEFERRED` requires `schema` to be absent;
- `BLOCKED` requires `schema` to be absent;
- `reason` is always present.

`relation_row_schema_states` is a private semantic model field keyed like the
existing `relation_row_schemas` mapping: `TableDef | QueryDef` definition
identity. It is not a public relation-name map.

## Deferred Population

Slice 3 does not classify or populate state entries for:

- direct-source concrete schemas;
- direct-source unknown schemas;
- duplicate output names;
- computed aliases;
- `let` schema;
- aggregate projections;
- grouped outputs;
- table-to-table propagation;
- table-to-query propagation;
- query-to-query propagation;
- multi-hop propagation;
- unresolved relation blocking;
- relation cycle blocking.

Those facts remain later-slice work. Existing `relation_row_schemas` behavior
is unchanged in Slice 3.

## Diagnostics And Blocking

Slice 3 adds no diagnostic codes, no diagnostics, and no diagnostic wording or
ordering changes.

Unresolved relation semantics continue to rely on existing `PIE-S2301`.
Relation cycle semantics continue to rely on existing `PIE-S2302`. Slice 3 only
provides private `BLOCKED` vocabulary for later propagation slices; it does not
materialize blocked state entries.

## Project JSON v2 Privacy

Project JSON v2 top-level shape remains unchanged. Slice 3 adds no Project JSON
v2 keys and serializes no private row schema facts, no private schema
availability facts, no status values, and no reason values.

Project JSON v2 diagnostics continue to flow only through existing
`diagnostics[]`. `src/pietto/_project/json_v2.py` is unchanged in Slice 3.

## Non-goals

Slice 3 does not implement:

- propagation helper or topological traversal;
- table-to-table, table-to-query, query-to-query, or multi-hop propagation;
- state population from checker/build logic;
- computed alias schema;
- `let` schema;
- aggregate or grouped output schema;
- Project JSON v2 row schema output;
- CLI/check orchestration changes;
- project IR, project SQL emit, project `emit-sql`, or project `explain`;
- public project semantic API;
- parser, grammar, or generated parser changes;
- JOIN or relationship behavior;
- runtime or database behavior.
