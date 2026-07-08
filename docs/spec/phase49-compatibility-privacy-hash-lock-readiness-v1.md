# Phase 49 Compatibility/Privacy/Hash-lock Readiness v1

## Purpose

This contract defines Phase 49 Slice 13: Compatibility/privacy/hash-lock
readiness. Slice 13 is a docs/spec/tests-only readiness slice before the Phase
49 completion audit.

The goal is to verify that Phase 49 private row schema, let facts, dependency
graph, and lineage carriers stay private while public project surfaces remain
unchanged. Slice 13 also records that existing Phase 11/12 and Phase 33
hash/private-surface locks remain readiness checks for clean CI and should not
be refreshed in this slice.

## Public Surface Compatibility

Project JSON v2 remains unchanged. The public envelope stays limited to the
existing top-level keys:

- `schema_version`;
- `command`;
- `mode`;
- `ok`;
- `project`;
- `inputs`;
- `diagnostics`;
- `cli_errors`;
- `result`.

The existing public `inputs[].status` field remains allowed. No private
`status` or `reason` facts are added to Project JSON v2.

Public diagnostics remain unchanged. Slice 13 adds no public diagnostic code,
message wording, ordering rule, or diagnostic emission path. Existing public
diagnostics remain exposed only through the existing top-level
`diagnostics[]` Project JSON v2 field.

Parser, grammar, generated files, public semantic API, CLI behavior, IR
behavior, SQL behavior, package metadata, workflows, fixtures, goldens,
lockfiles, validation scripts, and runtime/database behavior remain unchanged.
Package version remains `0.1.0`.

No tag, release, publish, upload, signing, or attestation work is authorized by
Slice 13.

## Private Carrier Privacy

The following private project facts remain project-internal and must not be
serialized into Project JSON v2 or exposed through public API, public metadata,
project explain output, CLI output, IR, or SQL:

- `relation_row_schemas`;
- `relation_row_schema_states`;
- `relation_let_scope_facts`;
- `relation_row_dependency_graphs`;
- `relation_row_lineages`;
- `ProjectRowSchema`;
- `ProjectRelationRowSchemaState`;
- `ProjectRelationLetScopeFacts`;
- `ProjectRelationRowDependencyGraph`;
- `ProjectRelationRowLineage`;
- `ProjectRowField` provenance/origin facts;
- private dependency, lineage, status, reason, and private enum tokens.

Private token examples include `UNKNOWN_SCHEMA`,
`DEFERRED_PHASE48_BEHAVIOR`, `UNRESOLVED_RELATION_BLOCKED`, `CYCLE_BLOCKED`,
`DUPLICATE_OUTPUT_NAME`, `LET_DIAGNOSTICS_SUPPRESSED`, `let_derived`,
`derived_expression`, `computed_expression`, `let_output`, `let_expression`,
and `transitive_dependency`.

## Hash And Private-surface Readiness

Existing Phase 11/12 boundary locks should remain current in clean CI. Existing
Phase 33 `project_private` count and digest locks should remain current in
clean CI.

Slice 13 does not recompute, refresh, weaken, or update existing hash locks. If
a later approved validation or repair gate proves that a Phase 11/12 boundary
lock or Phase 33 private-surface lock is stale, that repair must be separately
scoped and reviewed.

## Dirty-path Readiness

Dirty Slice 13 Gate 2 validation should run only the new Slice 13 focused test.
Older dirty-path guards remain clean-tree/CI compatibility checks after a later
Gate 3 publish because their allowed dirty sets belong to their original
slices.

The Slice 13 dirty-path guard allows only a clean tree or the exact Slice 13
Gate 2 allowlist.

## Non-goals

Slice 13 does not authorize:

- production source changes;
- public JSON, public API, public metadata, or project explain output;
- Project JSON v2 schema or shape changes;
- project IR, project SQL, or project `emit-sql`;
- public diagnostics, diagnostic wording changes, or diagnostic ordering
  changes;
- parser, grammar, or generated-file changes;
- JOIN or relationship behavior;
- aggregate/grouped output schema or aggregate/grouped lineage;
- bridge, export, RAG, Arrow, import/export, or multi-file behavior;
- runtime or database behavior;
- workflow, package metadata, lockfile, fixture, golden, validation script, or
  existing hash-lock test changes;
- package version changes;
- tag, release, publish, upload, signing, or attestation operations.
