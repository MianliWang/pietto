# Phase 48 Deterministic Propagation Order And Cycle Blocking Contract v1

## Purpose

This specification locks Phase 48 Slice 2 for deterministic propagation order
and cycle-blocking behavior. Slice 2 is docs/spec/static-audit work only. It
does not implement production behavior.

Phase 48 remains Query-to-query Row Schema Propagation. Slice 2 prepares the
contract that later slices must follow before adding the private schema
availability carrier or propagation behavior.

Package version remains `0.1.0`.

## Canonical Relation Order

Canonical relation order is the parsed project input order followed by
definition order within each parsed input.

Future private propagation helpers must use canonical relation order for:

- tie-breaking among independent relations;
- private relation fact ordering;
- deterministic diagnostics;
- stable tests and future private metadata readiness.

Implementations must not rely on incidental dictionary order unless the mapping
was built from canonical ordered facts and the ordering is locked by tests.

## Dependency-first Propagation

Future propagation is dependency-first for acyclic `TableDef | QueryDef`
relations.

Source-backed direct-source relations are propagation seeds because their
schemas come from already resolved source row schemas. A relation that depends
on another table/query may be considered only after the upstream relation's
schema availability is known.

Multi-hop propagation must preserve upstream-before-downstream ordering. For a
chain such as:

```text
source rows -> table staged -> query exported -> query published
```

the future propagation order is `staged`, then `exported`, then `published`,
assuming no relation is unresolved, deferred, unknown, or blocked.

When multiple acyclic relations become available at the same time, canonical
relation order is the tie-breaker.

## Current Graph Edge Direction

The current private relation dependency graph uses edges in this direction:

```text
dependent relation -> dependency relation
```

Future propagation must invert that direction or account for it explicitly
before deriving dependency-first traversal. The existing graph direction is
correct for dependency facts and cycle detection, but it is not itself a
ready-to-use propagation order.

## Cycle Blocking

Existing cycle diagnostics remain authoritative. Relation dependency cycles use
existing `PIE-S2302`.

Cycle members become future private `BLOCKED` schema availability states. A
future propagation implementation must mark the cycle members as blocked before
attempting to propagate concrete schemas. Concrete schemas must not be
propagated for cycle members.

Slice 2 adds no new diagnostic code, diagnostic message, or diagnostic location
policy for cycles.

## Unresolved Relation Blocking

Existing unresolved relation diagnostics remain authoritative. Unresolved
`from` references use existing `PIE-S2301`.

Relations with unresolved inputs become future private `BLOCKED` schema
availability states. Slice 2 adds no new diagnostics for unresolved relations
and does not change Project JSON v2 diagnostic shape.

## Availability Vocabulary

Phase 48 keeps the planned private availability vocabulary:

- `CONCRETE`: complete row schema is available and can be propagated.
- `UNKNOWN`: relation participates in row schema flow, but fields cannot be
  safely determined.
- `DEFERRED`: behavior is intentionally not inferred in Phase 48.
- `BLOCKED`: existing relation-level errors block propagation.

`ProjectRelationRowSchemaState` remains planned private vocabulary only in
Slice 2:

```text
ProjectRelationRowSchemaState
  status: CONCRETE | UNKNOWN | DEFERRED | BLOCKED
  schema: ProjectRowSchema | None
  reason: private enum/string
```

The actual private carrier implementation belongs to Slice 3, not Slice 2.

## Deterministic Fact And Diagnostic Ordering

Future private schema availability facts must be ordered by canonical relation
order unless a dependency-first result order is explicitly required. When
dependency-first result order is required, all ties use canonical relation
order.

Diagnostics remain ordered by the existing project semantic diagnostic path.
Slice 2 does not add diagnostics. Existing `PIE-S2301`, `PIE-S2302`, and
direct-field diagnostics remain the authoritative diagnostic surfaces.

## Privacy And Public Surface

Slice 2 changes no public surface.

Project JSON v2 top-level shape remains unchanged. Slice 2 adds no public
Project JSON v2 keys. Private row schema facts, private schema availability
facts, private relation graph facts, private cycle facts, and private
provenance facts must not be serialized.

Slice 2 adds no parser, grammar, generated parser artifact, CLI behavior,
Project JSON v2 behavior, project IR, project SQL emit, project `emit-sql`,
project `explain`, public project semantic API, JOIN behavior, relationship
behavior, runtime/database behavior, package version change, tag, release,
publish, upload, signing, or attestation.

## Explicit Deferrals

The following remain outside Slice 2:

- private `ProjectRelationRowSchemaState` carrier implementation;
- topological propagation helper implementation;
- table-to-table or table-to-query propagation behavior;
- query-to-query or multi-hop propagation behavior;
- computed alias schema;
- `let` schema;
- aggregate or grouped output schema;
- Project JSON v2 row schema output;
- private fact serialization;
- project IR or SQL lowering;
- project explain;
- JOIN or relationship behavior.
