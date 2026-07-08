# Phase 48 Upstream Non-concrete Schema Propagation v1

## Purpose

This contract locks Phase 48 Slice 7: Upstream unknown / absent / deferred /
blocked schema propagation.

Slice 7 implements private schema availability state propagation for
non-concrete upstream relation schemas. It does not change any public compiler
surface.

## Scope

Slice 7 continues the concrete propagation behavior from Slices 4 and 5. It
adds private availability state population for relation schemas that cannot be
made concrete:

- `UNKNOWN` for unknown direct field schemas, duplicate output names, and
  downstream relations that depend on an unknown upstream schema;
- `DEFERRED` for Phase 48-deferred schema surfaces and downstream relations
  that depend on a deferred upstream schema;
- `BLOCKED` for unresolved relation references, cycle members, and downstream
  relations that depend on a blocked upstream relation.

The private carrier remains `ProjectRelationRowSchemaState` through
`ProjectSemanticModel.relation_row_schema_states`.

## Unknown Propagation

Direct missing fields over a concrete source or relation upstream continue to
use existing `PIE-S2102` only. The affected relation receives
`ProjectRowSchema(is_unknown=True)` and an `UNKNOWN` availability state.

Duplicate output names also receive `ProjectRowSchema(is_unknown=True)` and an
`UNKNOWN` state, but no diagnostics.

When an immediate upstream relation is `UNKNOWN`, the downstream relation may
receive `ProjectRowSchema(is_unknown=True)` and an `UNKNOWN` state without
validating field names against that unknown upstream schema. This adds no
diagnostics beyond any existing upstream diagnostic.

## Deferred Propagation

Computed alias schema, `let` expression schema, aggregate projection schema,
and grouped output schema remain deferred. Slice 7 does not infer those
schemas.

Relations whose own select surface is deferred receive a `DEFERRED` state with
no concrete schema. A downstream relation whose immediate upstream is
`DEFERRED` also receives a `DEFERRED` state with no concrete schema.

Slice 7 preserves the current `let` nuance: a relation with a `let` block may
still produce a concrete schema for direct selected fields when the selected
fields are already supported direct projections. The `let` expression itself
does not become an output schema field.

## Blocked Propagation

Unresolved relation references continue to rely on existing `PIE-S2301`.
Relations with unresolved inputs receive a private `BLOCKED` state with no
concrete schema.

Relation cycles continue to rely on existing `PIE-S2302`. Cycle members receive
private `BLOCKED` states with no concrete schemas. Cycle members never get
concrete schemas before cycle blocking is applied.

A downstream relation whose immediate upstream is `BLOCKED` receives a private
`BLOCKED` state with no concrete schema and no new diagnostics.

## Determinism

`relation_row_schemas` ordering remains deterministic. Concrete and unknown
schemas are still materialized only from deterministic project input order,
definition order, and dependency-first propagation with canonical tie-breaking.

`relation_row_schema_states` ordering remains deterministic. Propagated
non-concrete states are added only after the immediate upstream state is known.
Cycle members are blocked before concrete propagation.

## Diagnostics

Slice 7 adds no new diagnostics and changes no diagnostic wording or ordering.

Existing diagnostics remain authoritative:

- `PIE-S2102` for concrete upstream direct-field validation failures;
- `PIE-S2301` for unresolved relation references;
- `PIE-S2302` for relation dependency cycles.

Unknown, deferred, and blocked propagation does not add diagnostics.

## Project JSON v2 Privacy

Project JSON v2 top-level shape remains unchanged.

Slice 7 serializes no private row schema facts, no
`relation_row_schema_states`, no private status values, no private reason
values, no `ProjectRelationRowSchemaState`, no `ProjectRowSchema`, no
provenance facts, no relation graph facts, and no cycle facts.

The private availability states are still private implementation facts. They
are not a public Project JSON v2 contract and are not a public project semantic
API.

## Non-goals

Slice 7 does not implement:

- new diagnostics;
- diagnostic wording or ordering changes;
- Project JSON v2 shape changes;
- private fact serialization;
- computed alias schema;
- `let` expression schema;
- aggregate schema;
- grouped output schema;
- arbitrary expression schema propagation;
- JOIN or relationship behavior;
- project IR;
- project SQL emit;
- project `emit-sql`;
- project `explain`;
- public project semantic API;
- parser, grammar, or generated parser artifact changes;
- CLI behavior changes;
- runtime or database execution behavior;
- package version, tag, release, publish, upload, signing, or attestation
  behavior.
