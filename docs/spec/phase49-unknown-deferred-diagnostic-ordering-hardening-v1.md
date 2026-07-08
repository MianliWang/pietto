# Phase 49 Unknown/Deferred Diagnostic Ordering Hardening v1

## Purpose

This specification locks Phase 49 Slice 12: Unknown/deferred/diagnostic
ordering hardening.

Slice 12 hardens the current private project semantic behavior for
`UNKNOWN`, `DEFERRED`, and `BLOCKED` carrier states and public diagnostic
ordering across row schema, relation-local let facts, row dependency graph, and
row lineage carriers. It is docs/spec/tests-only hardening.

Package version remains `0.1.0`.

## Private Carrier Scope

Slice 12 covers these private `ProjectSemanticModel` carriers:

- `relation_row_schema_states`;
- `relation_let_scope_facts`;
- `relation_row_dependency_graphs`;
- `relation_row_lineages`.

The carriers remain private. They are not Project JSON v2 output, CLI output,
public semantic API output, project explain output, IR, SQL, or runtime state.

## Expected State Alignment

Missing field references preserve the existing public missing-field
diagnostic, such as `PIE-S2102`, and do not introduce downstream duplicate
diagnostics. The affected row schema state is `UNKNOWN` with
`UNKNOWN_SCHEMA`. Matching dependency graph and lineage carriers are private
`UNKNOWN` non-concrete states with deterministic reasons and empty graph or
lineage facts.

Unresolved relation inputs preserve the existing `PIE-S2301` diagnostic and
do not add row-schema, let, dependency, or lineage diagnostics. Applicable row
schema, dependency graph, and lineage carriers are `BLOCKED` with
`UNRESOLVED_RELATION_BLOCKED`. A relation-local `let:` clause in that relation
uses a private `BLOCKED` let fact with `UPSTREAM_BLOCKED`.

Relation cycles preserve the existing `PIE-S2302` diagnostic and do not emit
missing-field diagnostics from blocked cycle members. Applicable row schema,
dependency graph, and lineage carriers are `BLOCKED` with `CYCLE_BLOCKED`. A
relation-local `let:` clause in a cycle member uses a private `BLOCKED` let
fact with `UPSTREAM_BLOCKED`.

Duplicate output names remain private deterministic row schema availability
facts. The relation row schema state is `UNKNOWN` with `DUPLICATE_OUTPUT_NAME`,
and dependency graph and lineage carriers are non-concrete with empty facts.
Slice 12 does not add a public diagnostic for this current project-private
case.

Grouped and aggregate output schema remains deferred. Applicable row schema,
dependency graph, and lineage carriers use `DEFERRED` with
`DEFERRED_PHASE48_BEHAVIOR`. Slice 12 does not implement aggregate/grouped
output schema or aggregate/grouped lineage.

Invalid selected-let cases keep local semantic helper diagnostics suppressed
into private let facts. Those private facts use deterministic non-concrete
let status/reason values such as `UNKNOWN` with
`LET_DIAGNOSTICS_SUPPRESSED`. Public diagnostics remain the current
row-schema diagnostics, such as selected missing-field diagnostics, in stable
order.

## Diagnostic Ordering

Public diagnostics remain deterministic and ordered by existing project
semantic construction order. Slice 12 introduces no new diagnostic codes,
messages, wording, severity changes, or ordering changes.

Private carrier statuses and reasons must not replace, duplicate, or reorder
public diagnostics. Private missing-fact states remain private and do not emit
public diagnostics.

## Privacy

Project JSON v2 remains unchanged. It serializes no private carrier names,
private statuses, private reasons, dependency graph facts, lineage facts,
provenance, origin, row schema internals, or let fact internals.

In particular, Project JSON v2 must not expose:

- `relation_row_schema_states`;
- `relation_let_scope_facts`;
- `relation_row_dependency_graphs`;
- `relation_row_lineages`;
- `ProjectRelationRowSchemaState`;
- `ProjectRelationLetScopeFacts`;
- `ProjectRelationRowDependencyGraph`;
- `ProjectRelationRowLineage`;
- private reasons such as `UNKNOWN_SCHEMA`, `DEFERRED_PHASE48_BEHAVIOR`,
  `UNRESOLVED_RELATION_BLOCKED`, `CYCLE_BLOCKED`, `DUPLICATE_OUTPUT_NAME`, or
  `LET_DIAGNOSTICS_SUPPRESSED`;
- dependency, lineage, provenance, origin, row schema, or let fact internals.

The existing public Project JSON v2 input status field remains part of the
existing public JSON shape. Slice 12 does not reinterpret that public field as
a private carrier status.

## Non-goals

Slice 12 does not implement:

- production source changes;
- public metadata, explain, JSON, or API output;
- project explain;
- project IR, project SQL, or project `emit-sql`;
- parser, grammar, or generated ANTLR changes;
- JOIN or relationship behavior;
- aggregate or grouped output schema;
- aggregate or grouped lineage;
- CLI behavior changes;
- Project JSON serializer or public JSON shape changes;
- public diagnostics or diagnostic wording changes;
- workflow, fixture, golden, package metadata, lockfile, or validation script
  changes;
- bridge, export, RAG, Arrow, import, or export behavior;
- runtime or database behavior;
- package version, tag, release, publish, upload, signing, or attestation.
