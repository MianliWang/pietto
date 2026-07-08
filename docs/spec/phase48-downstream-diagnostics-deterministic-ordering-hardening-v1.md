# Phase 48 Downstream Diagnostics And Deterministic Ordering Hardening v1

## Purpose

This contract locks Phase 48 Slice 8: Downstream diagnostics and deterministic
ordering hardening.

Slice 8 is docs/spec/tests-only. It records and tests the current downstream
diagnostic and private ordering behavior after Slices 4 through 7. Slice 8
changes no production code and implements no new compiler behavior.

## Diagnostics Contract

Downstream row schema diagnostics use existing diagnostic families only.

`PIE-S2102` is emitted only for direct projection validation over a concrete
upstream schema. That concrete upstream may be a direct source row schema or a
previously propagated concrete table/query row schema.

`PIE-S2102` ordering is deterministic:

- project input order is considered first;
- definition order and dependency-first propagation order determine relation
  processing;
- select-item order determines diagnostics within one relation;
- canonical parsed input order and definition order break ties.

Unknown, deferred, and blocked propagation stays diagnostic-silent beyond any
existing upstream diagnostic:

- downstream from `UNKNOWN` receives private `UNKNOWN` state/schema without
  validating fields against an unknown upstream;
- downstream from `DEFERRED` receives private `DEFERRED` state without schema
  inference;
- downstream from `BLOCKED` receives private `BLOCKED` state without extra row
  schema diagnostics.

`PIE-S2301` remains authoritative for unresolved relation roots. An unresolved
root produces `PIE-S2301` only, and downstream blocked propagation does not add
`PIE-S2102`.

`PIE-S2302` remains authoritative for relation cycles. Cycle members are
blocked before concrete field projection is attempted, so cycle members do not
also emit `PIE-S2102`.

Duplicate output names remain diagnostic-free. They may produce private
`UNKNOWN` row schemas and private `UNKNOWN` states, but they do not introduce a
new diagnostic family and do not reuse `PIE-S2102`.

Slice 8 adds no new diagnostic family and changes no diagnostic wording,
severity, location policy, or ordering behavior.

## Ordering Contract

`relation_row_schemas` ordering remains deterministic.

Concrete schemas follow dependency-first propagation order. Direct-source
relations are seeds. A relation depending on another table/query is recorded
only after the immediate upstream schema is available. When multiple relations
are ready, canonical parsed input order and definition order break ties.

`relation_row_schema_states` ordering remains deterministic. The current
private contract is:

- pre-blocked roots and cycle members are recorded deterministically before
  concrete propagation;
- direct-source concrete or unknown states follow canonical input and
  definition order;
- propagated concrete, unknown, deferred, and blocked states follow
  dependency-first availability;
- ties use canonical parsed input order and definition order.

Out-of-order definitions must still produce deterministic dependency-first
private result ordering for propagated schemas. Independent relations keep
canonical definition order as the tie-breaker.

Multi-file project source selection remains deterministic under the current
source-selection implementation: selected project inputs are processed by
sorted project-relative paths, then by definition order within each parsed
input.

The current private relation dependency graph edge direction remains:

```text
dependent relation -> dependency relation
```

Propagation must continue to account for that direction before deriving
dependency-first order.

## Project JSON v2 Privacy

Project JSON v2 top-level shape remains unchanged.

Slice 8 serializes no private row schema facts, no
`relation_row_schema_states`, no status or reason values, no
`ProjectRelationRowSchemaState`, no `ProjectRowSchema`, no private provenance,
no relation dependency graph facts, no cycle facts, and no private ordering
metadata.

Project JSON v2 diagnostics continue to flow only through the existing
`diagnostics[]` field. This contract does not forbid legitimate public JSON
keys such as input `status`; it forbids leaking private row schema and ordering
facts.

Slice 8 adds no public JSON key, no public project semantic API, no CLI
behavior, and no Project JSON v2 shape change.

## Non-goals

Slice 8 does not implement:

- production source changes;
- diagnostic code, wording, severity, location, or behavior changes;
- private fact serialization;
- Project JSON v2 public shape changes;
- computed alias schema;
- `let` expression schema;
- aggregate schema;
- grouped output schema;
- arbitrary expression schema propagation;
- project explain or metadata export;
- project IR;
- project SQL emit;
- project `emit-sql`;
- JOIN or relationship behavior;
- parser, grammar, or generated parser artifact changes;
- CLI behavior changes;
- runtime or database execution behavior;
- hash-lock changes;
- package version, tag, release, publish, upload, signing, or attestation
  behavior.
