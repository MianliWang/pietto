# Phase 49 Completion Audit Status Lock v1

This contract locks Phase 49 Slice 14: Completion audit/status lock.

Slice 14 is docs/spec/tests-only. It adds no production code and changes no
Project JSON v2 serializer, project check orchestration, parser, generated
artifact, CLI behavior, public JSON shape, public semantic API, diagnostic
code, diagnostic wording, diagnostic ordering, IR, SQL, workflow, fixture,
golden, package metadata, lockfile, validation script, runtime behavior, or
release surface.

Package version remains `0.1.0`.

## Completion Statement

Phase 49 is Row-level Computed Alias, Let Schema, Origin, Dependency, and
Lineage. Phase 49 completes the private row-level computed/let schema,
dependency, and lineage foundation once Slice 14 Gate 3 commit, push, and
natural CI pass.

Gate 2 docs must not pre-claim the Slice 14 commit, push, or natural CI result.

## Delivered Scope

Phase 49 uses this completed fourteen-slice route:

1. Candidate decision / scope lock
2. Project row expression schema helper contract
3. Type/nullability adapter for legal row expressions
4. Computed alias project row schema MVP
5. Computed alias origin/provenance privacy
6. Project let scope/value facts
7. Selected let-derived output schema
8. Let visibility/order/shadowing hardening
9. Private row-level dependency graph scaffold
10. Minimal private lineage carrier for source/direct/rename
11. Lineage for computed/let/multi-hop fields
12. Unknown/deferred/diagnostic ordering hardening
13. Compatibility/privacy/hash-lock readiness
14. Completion audit/status lock

Phase 49 delivered private project row-level computed/let schema, dependency,
and lineage foundations. It mapped existing legal row-level expression
type/nullability facts into private project row schema facts for supported
computed aliases, captured selected relation-local `let` outputs, hardened
let visibility/order/shadowing boundaries, recorded private immediate row-level
dependencies, and recorded private row lineage including computed, let, and
multi-hop facts.

Phase 49 did not expand the expression language. Aggregate/grouped output
schema and aggregate/grouped lineage remain deferred.

## Private Carriers

The completed private carrier inventory includes:

- `relation_row_schemas`;
- `relation_row_schema_states`;
- `relation_let_scope_facts`;
- `relation_row_dependency_graphs`;
- `relation_row_lineages`.

These carriers are private project semantic model facts. They are not Project
JSON v2 output, public semantic API output, CLI output, project explain output,
public metadata output, IR, SQL, runtime state, or database behavior.

## Public Surface Preservation

Project JSON v2 remains unchanged. The public Project JSON v2 envelope remains:

- `schema_version`;
- `command`;
- `mode`;
- `ok`;
- `project`;
- `inputs`;
- `diagnostics`;
- `cli_errors`;
- `result`.

The public semantic API remains unchanged. CLI behavior, IR behavior, SQL
behavior, parser behavior, grammar files, generated files, workflows, fixtures,
goldens, package metadata, lockfile, and validation scripts remain unchanged.

Public diagnostics remain unchanged except for existing behavior. Slice 14 adds
no public diagnostic code, message wording, ordering rule, or diagnostic
emission path.

Package version remains `0.1.0`. Phase 49 performs no package version change,
tag, release, publish, upload, signing, or attestation.

## Privacy

No private row schema, let fact, dependency graph, lineage, status, reason,
provenance, or origin fact is public.

Project JSON v2 serializes no:

- `relation_row_schemas`;
- `relation_row_schema_states`;
- `relation_let_scope_facts`;
- `relation_row_dependency_graphs`;
- `relation_row_lineages`;
- private row field provenance/origin facts;
- private row dependency graph facts;
- private row lineage facts;
- private status values;
- private reason values.

The existing public `inputs[].status` field remains part of the public Project
JSON v2 input envelope. It is not a private carrier status.

## Hash And Private-surface Readiness

Phase 11/12 boundary locks and the Phase 33 `project_private` lock remain
clean-CI checks. Slice 14 does not refresh existing hash locks.

If a future validation or repair gate proves a stale hash/private-surface lock,
that repair must be separately scoped and must not be folded into Slice 14
without explicit approval.

## Deferred Work

The following remain deferred to Phase 50 or later:

- aggregate/grouped output schema;
- aggregate/grouped lineage;
- project explain/public metadata;
- public lineage/export;
- project IR/SQL/emit-sql;
- JOIN/relationship/grain/fanout;
- bridge/export/RAG/Arrow;
- runtime/database behavior;
- package release/version work.

## Non-goals

Slice 14 does not include:

- production source changes;
- Project JSON v2 schema or serializer changes;
- public JSON, public API, public metadata, or project explain output;
- project IR, project SQL, or project `emit-sql`;
- public diagnostics or diagnostic wording changes;
- parser/grammar/generated changes;
- JOIN/relationship behavior;
- aggregate/grouped output schema or aggregate/grouped lineage;
- bridge/export/RAG/Arrow behavior;
- import/export or multi-file behavior;
- runtime/database behavior;
- workflow, package metadata, lockfile, fixture, golden, or validation script
  changes;
- README, AGENTS, global roadmap, or `docs/spec/pietto-v0.9.md` changes;
- package version, tag, release, publish, upload, signing, or attestation.

## Gate 2 Scope

Phase 49 Slice 14 Gate 2 is limited to:

- `docs/plan/phase-49-row-level-computed-let-schema-lineage.md`;
- `docs/spec/phase49-completion-audit-status-lock-v1.md`;
- `tests/test_phase49_completion_audit_status_lock.py`.

No other file is approved in Slice 14 Gate 2.
