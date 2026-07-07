# Phase 48 Query-to-query Row Schema Scope Lock v1

## Purpose

This specification locks Phase 48 Slice 1 for Query-to-query Row Schema
Propagation. Slice 1 is docs/spec/static-audit only and does not implement
production behavior.

Phase 48 builds on:

- Phase 46 relation dependency graph and cycle diagnostics;
- Phase 47 direct row schema carrier, source row schemas, and direct relation
  row schemas;
- `ProjectSemanticModel.source_row_schemas`;
- `ProjectSemanticModel.relation_row_schemas`;
- `relation_resolutions`;
- `relation_dependency_graph`;
- existing `PIE-S2301`, `PIE-S2302`, and `PIE-S2102` diagnostics.

Package version remains `0.1.0`.

## Ten-slice Route

Phase 48 uses this ten-slice route:

1. Candidate/scope lock and route plan
2. Deterministic propagation order and cycle-blocking contract
3. Private schema availability state carrier and propagation readiness
4. Table-to-table / table-to-query propagation
5. Query-to-query and multi-hop propagation
6. Propagated field provenance / lineage hardening
7. Upstream unknown / absent / deferred / blocked schema propagation
8. Downstream diagnostics and deterministic ordering hardening
9. Project JSON/private-fact privacy plus future explain/bridge readiness
10. Completion audit/status lock

The older five- or six-slice route is not active. Future Pietto phases should
default to eight to twelve slices unless explicitly approved otherwise.

## Schema Availability State

Phase 48 selects schema availability design B as the target private design.
Slice 1 only locks this target design; it does not implement the carrier.
`ProjectRelationRowSchemaState` is the planned private carrier name.

```text
ProjectRelationRowSchemaState
  status: CONCRETE | UNKNOWN | DEFERRED | BLOCKED
  schema: ProjectRowSchema | None
  reason: private enum/string
```

`CONCRETE` means a complete row schema is available and can be propagated.
`UNKNOWN` means the relation participates in row schema flow, but fields cannot
be safely determined. `DEFERRED` means behavior is intentionally not inferred in
Phase 48. `BLOCKED` means existing relation-level errors block propagation.

Examples:

- `UNKNOWN`: unknown direct field, duplicate output name, upstream unknown
  schema.
- `DEFERRED`: computed alias, `let` schema, aggregate projection, grouped
  output schema.
- `BLOCKED`: unresolved relation through `PIE-S2301`, relation cycle through
  `PIE-S2302`.

This state is private target design only. It is not Project JSON v2 output and
not public project semantic API.

## Flat Relation Schema Model

Every table/query exposes a flat output schema. Downstream qualifiers only
match the immediate upstream relation name. Original source lineage is private
provenance / future project explain metadata, not a downstream query path.

When `from staged`, the direct field references `id` and `staged.id` are valid
because they reference the immediate upstream relation output schema.

When `from staged`, `users.id` is invalid because `users` is not the immediate
upstream relation name. `staged.users.id` is unsupported in Phase 48 and must
not become lineage-path selector syntax.

Duplicate output names remain private `UNKNOWN` schema without diagnostics.
Multi-source same-name fields must be disambiguated by upstream aliases such as
`user_id = users.id` and `event_id = events.id`. Downstream relations should
select `staged.user_id` and `staged.event_id`, not `staged.users.id`.

## Propagation Defaults

The Phase 48 MVP should eventually support acyclic `TableDef | QueryDef`
relations consuming an upstream `TableDef | QueryDef` with an available row
schema. It covers table-to-table propagation, table-to-query propagation,
query-to-query propagation, and multi-hop propagation.

Supported direct projection forms over upstream relation schemas are:

- `id`;
- `staged.id`;
- `user_id = id`;
- `user_id = staged.id`.

Propagation defaults:

- upstream `CONCRETE` -> downstream direct projection can produce a concrete
  schema;
- upstream `UNKNOWN` -> downstream `UNKNOWN` without new diagnostics;
- upstream `DEFERRED` -> downstream absent/deferred without new diagnostics;
- upstream `BLOCKED` -> downstream absent/blocked, relying on existing
  `PIE-S2301` / `PIE-S2302`;
- missing downstream field over concrete upstream schema uses existing
  `PIE-S2102`;
- unresolved relation uses existing `PIE-S2301` only;
- cycle uses existing `PIE-S2302` only and cycle members do not propagate
  schemas;
- duplicate output names remain private `UNKNOWN` schema without `PIE-S2305`
  and without `PIE-S2102`.

`field_def` preserves the original source shape `FieldDef` when available.
`resolved_type` and `nullability` propagate through relation chains.
`ProjectRowFieldProvenanceKind.DIRECT_PROJECTION` remains sufficient for Phase
48 direct projection propagation. `provenance.symbol` points to the immediate
upstream source/table/query symbol, and `location` points to the current select
expression.

## Deterministic Ordering

Parsed input order and definition order are canonical relation order.
Propagation is dependency-first. The current relation graph edge direction is
dependent relation -> dependency relation. Topological traversal must use
canonical parsed input and definition order for tie-breaking.

Direct field diagnostics preserve parsed input order, definition order, and
select item order. Implementations must avoid relying on incidental dict order
unless maps are built from canonical ordered facts and locked by tests.

## Downstream Phase 51-55 Readiness

Phase 48 prepares private facts for later phases:

- Phase 51 relationship/grain/fanout readiness: field existence,
  type/nullability, origin `FieldDef`, immediate upstream provenance, and schema
  availability state.
- Phase 52 Project Explain / Project Semantic Metadata Readiness: deterministic
  propagation order, schema availability state, diagnostics order, and private
  provenance/lineage readiness. This is distinct from existing single-file
  explain, and Phase 48 does not implement project explain.
- Phase 53 import/export and multi-file ergonomics: cross-file deterministic
  propagation, parsed input order, definition order, and namespace-stable
  relation references.
- Phase 54 JOIN candidate / narrow JOIN readiness: private relation output
  field checks, type/nullability compatibility prerequisites, and fail-closed
  unknown/blocked schemas.
- Phase 55 external bridge / metadata export / RAG / Arrow readiness:
  propagated private relation schema facts as future export source.

Phase 48 does not implement relationship behavior, grain/fanout diagnostics,
Project explain output, project semantic metadata artifact output,
import/export syntax, JOIN behavior, external metadata export, RAG bridge,
Arrow/PyArrow bridge, or public project semantic API.

## Deferred Boundaries

Phase 48 Slice 1 and the Phase 48 MVP keep these out of scope unless a later
phase/slice explicitly approves them:

- computed alias schema;
- `let` schema;
- aggregate/grouped output schema;
- project IR;
- project SQL emit;
- project `emit-sql`;
- project `explain`;
- public project semantic API;
- Project JSON v2 row schema output;
- private fact serialization;
- parser/grammar/generated changes;
- JOIN/relationship behavior;
- runtime/database execution;
- package version, tag, release, publish, upload, signing, or attestation.

## Privacy And Compatibility

Project JSON v2 top-level shape remains unchanged. Private row schema facts,
private schema availability facts, private relation graph facts, and private
cycle facts remain un-serialized. Diagnostics flow only through existing
`diagnostics[]`. CLI/check orchestration remains unchanged unless later
explicitly approved.

## Slice 1 Gate 2 Contract

Slice 1 Gate 2 is limited to:

- `docs/plan/phase-48-query-to-query-row-schema.md`
- `docs/spec/phase48-query-to-query-row-schema-scope-lock-v1.md`
- `tests/test_phase48_query_to_query_row_schema_scope_lock.py`

Focused validation:

```bash
git diff --check
git diff --no-index --check -- /dev/null tests/test_phase48_query_to_query_row_schema_scope_lock.py || true
uv run ruff format --check tests/test_phase48_query_to_query_row_schema_scope_lock.py
uv run ruff check tests/test_phase48_query_to_query_row_schema_scope_lock.py
uv run pyright --project pyrightconfig.tests.json
uv run pytest tests/test_phase48_query_to_query_row_schema_scope_lock.py
```

Slice 1 must not stage, commit, push, trigger CI, rerun CI, cancel CI, create a
tag, create a release, publish, upload, sign, or attest artifacts.
