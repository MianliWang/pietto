# Phase 48 Project JSON Private Fact Privacy Readiness v1

This contract locks Phase 48 Slice 9: Project JSON/private-fact privacy plus
future explain/bridge readiness.

Slice 9 is docs/spec/tests-only. It adds no production code and changes no
Project JSON v2 serializer, project check orchestration, parser, generated
artifact, CLI behavior, public JSON shape, diagnostic code, diagnostic wording,
or diagnostic ordering.

## Project JSON v2 Shape

Project JSON v2 top-level shape remains unchanged. The public key order remains:

1. `schema_version`
2. `command`
3. `mode`
4. `ok`
5. `project`
6. `inputs`
7. `diagnostics`
8. `cli_errors`
9. `result`

No public Project JSON v2 row schema output is approved in Phase 48. Slice 9
adds no Project JSON v2 keys and removes no Project JSON v2 keys.

## Public Diagnostics Boundary

Diagnostics remain public only through the existing top-level `diagnostics[]`
field. Slice 9 does not add diagnostics and does not change diagnostic code,
message, severity, location, suggestion, related-location, or ordering policy.

Project/config/source-read failures remain in `cli_errors[]` according to the
existing Project JSON v2 contract. Slice 9 does not move private semantic facts
into `diagnostics[]`, `cli_errors[]`, `inputs[]`, `project`, or `result`.

## Private Facts

The following facts remain project-private implementation details and must not
be serialized into Project JSON v2:

- `source_row_schemas`;
- `relation_row_schemas`;
- `relation_row_schema_states`;
- `ProjectRowSchema`;
- `ProjectRowField`;
- `ProjectRelationRowSchemaState`;
- `ProjectRelationRowSchemaStatus`;
- `ProjectRelationRowSchemaReason`;
- `ProjectRelationDependencyGraph`;
- source row schema facts;
- relation row schema facts;
- relation schema availability state facts;
- private status values;
- private reason values;
- provenance facts;
- lineage facts;
- relation graph facts;
- cycle facts;
- private deterministic ordering metadata.

The private schema availability reason values remain private:

- `direct_source_concrete`;
- `table_upstream_concrete`;
- `relation_upstream_concrete`;
- `unknown_schema`;
- `duplicate_output_name`;
- `deferred_phase48_behavior`;
- `unresolved_relation_blocked`;
- `cycle_blocked`;
- `upstream_unknown`;
- `upstream_deferred`;
- `upstream_blocked`.

This privacy rule does not forbid legitimate public keys such as the existing
input `status` key. It forbids leaking private row schema, availability,
provenance, dependency graph, cycle, ordering, and reason facts.

## Future Explain And Bridge Readiness

The private facts locked by Phase 48 may support future project explain,
project semantic metadata, bridge/export, RAG, or Arrow readiness in later
phases. Slice 9 exposes none of those facts.

Existing single-file `pietto explain` is not project explain. It remains the
single-file Semantic Metadata Artifact v1 path and is not changed by Slice 9.

Phase 52 remains the later Project Explain / Project Semantic Metadata
Readiness direction. Phase 48 Slice 9 does not implement Phase 52 behavior and
does not assign a public schema to future project explain output.

## Non-goals

Slice 9 does not implement:

- production code changes;
- Project JSON v2 public shape changes;
- private fact serialization;
- public Project JSON v2 row schema output;
- public project semantic API;
- project explain;
- semantic metadata export;
- bridge/export/RAG/Arrow behavior;
- project IR;
- project SQL;
- project `emit-sql`;
- computed alias schema;
- `let` expression schema;
- aggregate schema;
- grouped output schema;
- JOIN behavior;
- relationship behavior;
- parser/grammar/generated changes;
- new diagnostics;
- diagnostic wording changes;
- diagnostic ordering changes;
- hash-lock updates;
- package version changes;
- tag, release, publish, upload, signing, or attestation.

## Gate 2 Scope

Phase 48 Slice 9 Gate 2 is limited to:

- `docs/plan/phase-48-query-to-query-row-schema.md`;
- `docs/spec/phase48-project-json-private-fact-privacy-readiness-v1.md`;
- `tests/test_phase48_project_json_private_fact_privacy_readiness.py`.

No other file is approved in Slice 9 Gate 2.
