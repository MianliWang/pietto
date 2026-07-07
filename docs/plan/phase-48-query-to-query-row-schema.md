# Phase 48 - Query-to-query Row Schema Propagation

## Status

Phase 48 Slice 1 is Candidate/scope lock and route plan for:

**Query-to-query Row Schema Propagation**

Slice 1 is docs/spec/static-audit work only. It implements no production code,
no source/compiler behavior, no query-to-query propagation, no topological
propagation helper, no private schema availability carrier, no computed alias
schema, no `let` schema, no aggregate/grouped output schema, no new
diagnostics, no diagnostic code or message change, no Project JSON v2 shape
change, no private fact serialization, no CLI/check orchestration change, no
project IR, no project SQL emit, no project `emit-sql`, no project `explain`,
no public project semantic API, no parser/grammar/generated change, no
JOIN/relationship behavior, no runtime/database execution, no package version
change, and no tag, release, publish, upload, signing, or attestation.

Package version remains `0.1.0`.

## Trusted Baseline

- Baseline branch: `main`.
- Baseline HEAD: `e92f8763dbb97d031e71e3c9c57660802ade856c`.
- Baseline subject: `Complete Phase 47 direct row schema audit`.
- Baseline package version: `0.1.0`.
- Baseline worktree status: clean and equivalent to `## main...origin/main`.
- Baseline HEAD tag: none.
- Baseline exact-match tag: none.
- Natural CI: `CI` run `28882949450`, event `push`, branch `main`, headSha
  `e92f8763dbb97d031e71e3c9c57660802ade856c`, completed with success.

## Phase Identity And Prerequisites

Phase 48 is Query-to-query Row Schema Propagation. It builds on:

- Phase 46 relation dependency graph and cycle diagnostics;
- Phase 47 direct row schema carrier, source row schemas, and direct relation
  row schemas;
- `ProjectSemanticModel.source_row_schemas`;
- `ProjectSemanticModel.relation_row_schemas`;
- `relation_resolutions`;
- `relation_dependency_graph`;
- existing `PIE-S2301`, `PIE-S2302`, and `PIE-S2102` diagnostics.

## Full Phase 48 Slice Route

Phase 48 is a full ten-slice phase:

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

The older five- or six-slice Phase 48 route is superseded. Future Pietto
phases should default to eight to twelve slices unless an explicit later gate
approves a narrower route.

## Schema Availability State Design

Phase 48 selects schema availability design B as the target private design.
Slice 1 only locks the design and does not implement the carrier.
`ProjectRelationRowSchemaState` is the planned private carrier name.

```text
ProjectRelationRowSchemaState
  status: CONCRETE | UNKNOWN | DEFERRED | BLOCKED
  schema: ProjectRowSchema | None
  reason: private enum/string
```

State semantics:

- `CONCRETE`: complete row schema is available and can be propagated.
- `UNKNOWN`: relation participates in row schema flow, but fields cannot be
  safely determined, such as an unknown direct field, duplicate output name, or
  upstream unknown schema.
- `DEFERRED`: behavior is intentionally not inferred in this phase, such as a
  computed alias, `let` schema, aggregate projection, or grouped output schema.
- `BLOCKED`: existing relation-level errors block propagation, such as an
  unresolved relation through `PIE-S2301` or a relation cycle through
  `PIE-S2302`.

This state is project-private target design only. It is not Project JSON v2
output, not public API, and not implemented in Slice 1.

## Flat Relation Schema Model

Every table/query exposes a flat output schema. Downstream relations may
reference only the immediate upstream relation output fields. Original source
names are private provenance and future project explain metadata, not
downstream query paths.

For:

```pietto
query exported:
    from staged
    select:
        id
        staged.id
```

Both `id` and `staged.id` are valid direct field references when `staged` is
the immediate upstream relation.

For:

```pietto
query exported:
    from staged
    select:
        users.id
        staged.users.id
```

Both remain unsupported or invalid in Phase 48. `users.id` is invalid when
`from staged` because `users` is not the immediate upstream relation name.
`staged.users.id` is unsupported lineage-path syntax and must not be used to
solve ambiguity.

Duplicate output names remain private `UNKNOWN` schemas without diagnostics.
Multi-source same-name fields must be disambiguated by upstream aliases, for
example:

```pietto
table staged:
    from ...
    select:
        user_id = users.id
        event_id = events.id

query exported:
    from staged
    select:
        staged.user_id
        staged.event_id
```

Downstream relations use upstream output names, not `staged.users.id` lineage
selectors.

## Propagation And Provenance Defaults

Phase 48 should eventually allow acyclic `TableDef | QueryDef` definitions to
consume an upstream `TableDef | QueryDef` with an available row schema. The MVP
supports table-to-table propagation, table-to-query propagation,
query-to-query propagation, and multi-hop propagation.

Direct field projection over upstream table/query schemas should reuse the
existing direct projection forms:

- `id`;
- `staged.id`;
- `user_id = id`;
- `user_id = staged.id`.

Propagation defaults:

- upstream `CONCRETE`: downstream direct field projection can produce a
  concrete schema, and missing downstream fields use existing `PIE-S2102`;
- upstream `UNKNOWN`: downstream propagates `UNKNOWN` without new diagnostics;
- upstream `DEFERRED`: downstream schema remains absent/deferred without new
  diagnostics;
- upstream `BLOCKED`: downstream schema remains absent/blocked and relies on
  existing `PIE-S2301` or `PIE-S2302`;
- unresolved relation: existing `PIE-S2301` only, with no extra row-schema
  diagnostic;
- cycle: existing `PIE-S2302` only, and cycle members do not propagate schemas;
- duplicate output names: private `UNKNOWN` schema without `PIE-S2305` and
  without `PIE-S2102`.

`field_def` preserves the original source shape `FieldDef` when available.
`resolved_type` and `nullability` propagate through relation chains.
`ProjectRowFieldProvenanceKind.DIRECT_PROJECTION` remains sufficient for Phase
48 direct projection propagation. `provenance.symbol` should point to the
immediate upstream source/table/query symbol, and `location` should point to
the current select expression. A full lineage chain can be added later for
Project Explain / Project Semantic Metadata Readiness, but Phase 48 does not
implement a full lineage chain.

## Deterministic Ordering

Parsed input order and definition order are canonical relation order.
Propagation should be dependency-first. The current graph edge direction is
dependent relation -> dependency relation. Topological traversal must use
canonical parsed input and definition order for tie-breaking.

Direct field diagnostics preserve parsed input order, definition order, and
select item order. Implementation must avoid relying on incidental dict order
unless maps are built from canonical ordered facts and locked by tests.

## Downstream Phase 51-55 Readiness

Phase 48 prepares private facts for later phases without implementing those
behaviors:

- Phase 51 relationship/grain/fanout readiness: field existence,
  type/nullability, origin `FieldDef`, immediate upstream provenance, and schema
  availability state.
- Phase 52 Project Explain / Project Semantic Metadata Readiness: deterministic
  propagation order, schema availability state, diagnostics order, and private
  provenance/lineage readiness. This is distinct from existing single-file
  explain. Phase 48 does not implement project explain.
- Phase 53 import/export and multi-file ergonomics: cross-file deterministic
  propagation, parsed input order, definition order, and namespace-stable
  relation references.
- Phase 54 JOIN candidate / narrow JOIN readiness: private relation output
  field checks, type/nullability compatibility prerequisites, and fail-closed
  unknown/blocked schemas.
- Phase 55 external bridge / metadata export / RAG / Arrow readiness:
  propagated private relation schema facts as a future export source.

Phase 48 does not implement relationship behavior, grain/fanout diagnostics,
Project explain output, project semantic metadata artifact output,
import/export syntax, JOIN behavior, external metadata export, RAG bridge,
Arrow/PyArrow bridge, or public project semantic API.

## Deferred Boundaries

The following remain outside Phase 48 Slice 1 and outside the Phase 48 MVP
unless a later phase/slice explicitly approves them:

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

Phase 48 must preserve Project JSON v2 top-level shape. Private row schema
facts, schema availability state facts, and relation graph private facts must
not be serialized. Diagnostics flow only through existing `diagnostics[]`. No
CLI/check orchestration change is authorized unless a later slice explicitly
approves it.

## Slice 1 Gate 2 Allowlist

Phase 48 Slice 1 Gate 2 is limited to:

- `docs/plan/phase-48-query-to-query-row-schema.md`
- `docs/spec/phase48-query-to-query-row-schema-scope-lock-v1.md`
- `tests/test_phase48_query_to_query_row_schema_scope_lock.py`

No other file is approved in Slice 1 Gate 2.

## Focused Validation

The focused Slice 1 Gate 2 validation commands are:

```bash
git diff --check
git diff --no-index --check -- /dev/null tests/test_phase48_query_to_query_row_schema_scope_lock.py || true
uv run ruff format --check tests/test_phase48_query_to_query_row_schema_scope_lock.py
uv run ruff check tests/test_phase48_query_to_query_row_schema_scope_lock.py
uv run pyright --project pyrightconfig.tests.json
uv run pytest tests/test_phase48_query_to_query_row_schema_scope_lock.py
```

Do not run hash-lock tests, full pytest, `scripts/validate.py`, or CI in dirty
Gate 2.

## Stop Conditions

Stop immediately if implementation would require files outside the Slice 1
allowlist, production code, schema carrier implementation, parser/generated
files, Project JSON v2/CLI/check changes, new diagnostics, diagnostic wording
changes, computed alias schema, `let` schema, aggregate/grouped schema,
JOIN/relationship behavior, project IR/SQL/emit/explain, public API, Phase
51-55 behavior implementation, package version changes, release actions, docs
outside the allowlist, or hash-lock churn.
