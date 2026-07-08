# Phase 48 Query-to-query Multi-hop Propagation Contract v1

## Purpose

This contract locks Phase 48 Slice 5: Query-to-query and multi-hop
propagation.

Slice 5 implements concrete-only relation-to-relation propagation for private
project row schemas. It extends the Phase 48 private scaffold from one-hop
table-upstream propagation to acyclic chains where both the downstream and the
immediate upstream may be `TableDef | QueryDef`.

## Scope

Slice 5 supports a downstream `TableDef | QueryDef` whose `from` relation
resolves to an immediate upstream `TableDef | QueryDef` with an already
concrete private row schema.

The concrete upstream schema may come from:

- a direct-source table or query relation;
- a table/query schema propagated earlier in dependency-first order.

Supported projection forms remain flat direct field projections:

- `id`;
- `upstream.id`;
- `alias = id`;
- `alias = upstream.id`.

The propagation surface includes:

- query-to-query propagation;
- table-from-query propagation;
- query from propagated query;
- table from propagated table;
- mixed table/query multi-hop acyclic chains.

## Deterministic Order

Propagation is dependency-first over acyclic table/query relations. Canonical
relation order comes from parsed project input order and definition order, and
is the deterministic tie-breaker when more than one relation is ready.

The current private relation dependency graph edge direction is dependent
relation -> dependency relation. Any propagation helper that consumes graph
facts must invert that direction or otherwise account for it explicitly before
using the graph as dependency-first traversal input.

## Private State

Slice 5 may populate private concrete `relation_row_schema_states` only:

- direct-source concrete relation schemas use `DIRECT_SOURCE_CONCRETE`;
- propagated concrete relation schemas use `RELATION_UPSTREAM_CONCRETE`.

`RELATION_UPSTREAM_CONCRETE` covers concrete propagation from an immediate
table or query upstream. It intentionally does not encode the historical source
kind, because the downstream contract consumes the immediate relation output
schema.

No non-concrete upstream propagation until Slice 7. Slice 5 does not broadly
populate `UNKNOWN`, `DEFERRED`, or `BLOCKED` states. If an upstream schema is
absent, unknown, deferred, blocked, grouped, unresolved, or a cycle member,
Slice 5 does not propagate a concrete downstream schema from it.

## Flat Relation Schema Model

Slice 5 preserves the flat relation schema model. A downstream relation sees
only the immediate upstream output fields. Original source names, earlier
lineage names, and multi-part lineage paths are not downstream field paths.

For example, after:

```pietto
query seed:
    from users
    select:
        id

query exported:
    from seed
    select:
        id
```

`exported` may refer to `id` or `seed.id`. It may not refer to `users.id` or
`seed.users.id`.

## Diagnostics

Slice 5 adds no diagnostics and changes no diagnostic ordering.

Existing diagnostics remain authoritative:

- `PIE-S2102` for missing fields, invalid immediate qualifiers, original-source
  qualifiers, and unsupported multi-part dotted field paths over a concrete
  upstream schema;
- `PIE-S2301` for unresolved relation references;
- `PIE-S2302` for relation dependency cycles.

Cycle members remain blocked from concrete propagation. Slice 5 must not compute
or attach concrete row schemas for cycle members before applying the
cycle-blocking contract.

## Project JSON v2 Privacy

Project JSON v2 top-level shape remains unchanged.

Slice 5 serializes no private row schema facts, no
`relation_row_schema_states`, no private status/reason values, no provenance
facts, no relation graph facts, and no cycle facts.

## Non-goals

Slice 5 does not implement:

- broad `UNKNOWN`, `DEFERRED`, or `BLOCKED` state population;
- propagation from unknown, deferred, blocked, grouped, unresolved, or cyclic
  upstreams;
- computed alias schema;
- `let` schema;
- aggregate or grouped output schema;
- arbitrary expression schema propagation;
- relationship or JOIN behavior;
- project IR, project SQL, project `emit-sql`, or project `explain`;
- public project semantic API;
- parser, grammar, or generated artifact changes;
- public JSON shape changes;
- CLI behavior changes;
- runtime or database execution behavior;
- package version, tag, release, publish, upload, signing, or attestation
  behavior.
