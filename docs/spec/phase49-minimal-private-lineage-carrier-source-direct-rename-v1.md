# Phase 49 Minimal Private Lineage Carrier Source/Direct/Rename v1

## Purpose

This specification locks Phase 49 Slice 10: Minimal private lineage carrier for
source/direct/rename.

Slice 10 introduces a private project row lineage carrier for immediate
source-backed direct projections, source-backed renamed projections, and
relation-backed direct or renamed projections. The carrier is private project
semantic state only. It prepares future full lineage work without exposing
lineage publicly.

Package version remains `0.1.0`.

## Non-goals

Slice 10 does not implement:

- computed alias lineage;
- `let`-derived lineage;
- full or transitive multi-hop lineage expansion;
- public Project JSON v2 row schema, dependency, lineage, metadata, or explain
  output;
- project explain;
- project IR;
- project SQL;
- project `emit-sql`;
- public diagnostics or diagnostic wording changes;
- parser, grammar, or generated ANTLR changes;
- JOIN or relationship behavior;
- aggregate or grouped output schema;
- bridge, export, RAG, Arrow, import, or export behavior;
- runtime or database execution;
- package version, tag, release, publish, upload, signing, or attestation.

## Data Model

Slice 10 introduces private project lineage carriers under
`src/pietto/_project/row_lineage.py`:

- `ProjectRowLineageStatus`;
- `ProjectRowLineageReason`;
- `ProjectRowLineageSegmentKind`;
- `ProjectRowLineageFactKind`;
- `ProjectRowLineageSegment`;
- `ProjectRowLineageFact`;
- `ProjectRelationRowLineage`.

The lineage status values are:

- `CONCRETE`;
- `UNKNOWN`;
- `DEFERRED`;
- `BLOCKED`.

Lineage reasons mirror current private row schema and row dependency graph
availability reasons where possible, including direct source concrete,
table/relation upstream concrete, unknown schema, duplicate output name,
deferred Phase 48 behavior, unresolved relation blocked, cycle blocked,
upstream unknown, upstream deferred, upstream blocked, missing row schema
state, missing row schema, and missing upstream schema. Slice 10 also allows a
deterministic private missing dependency graph reason.

Segment kinds are:

- `SOURCE_FIELD`;
- `UPSTREAM_FIELD`;
- `OUTPUT_FIELD`.

Fact kinds are:

- `DIRECT_PROJECTION`;
- `RENAMED_PROJECTION`.

Segments and facts are frozen private dataclasses. Relation lineage carriers
store deterministic tuples of facts.

## Storage

`ProjectSemanticModel` stores a private mapping named `relation_row_lineages`,
keyed by `TableDef | QueryDef`.

There are no top-level source lineage maps in Slice 10. Source fields appear as
lineage segments only when a relation output has source-backed direct or renamed
lineage.

The mapping is copied into a readonly mapping with other private project
semantic model facts. It is not a public semantic API.

## Behavior

Slice 10 builds row lineage after private relation row schemas, relation row
schema states, relation-local let scope facts, and relation row dependency
graphs are available.

For concrete relation row schemas and concrete row dependency graphs:

- a source-backed direct projection output records a `DIRECT_PROJECTION`
  lineage fact from the output field segment to a source field segment;
- a source-backed renamed projection output records a `RENAMED_PROJECTION`
  lineage fact from the output field segment to a source field segment;
- a relation-backed direct projection output records a `DIRECT_PROJECTION`
  lineage fact from the output field segment to the immediate upstream field
  segment;
- a relation-backed renamed projection output records a `RENAMED_PROJECTION`
  lineage fact from the output field segment to the immediate upstream field
  segment.

Relation-backed lineage is immediate-upstream only. Slice 10 must not expand a
relation-backed upstream field into a transitive source lineage path.

Computed aliases are omitted from Slice 10 lineage facts. Selected
`let`-derived outputs are omitted from Slice 10 lineage facts. Dependency graph
edges for computed expressions, selected `let` outputs, and `let` expressions
remain private dependency graph facts only.

## Non-concrete Behavior

If a relation row schema state is `UNKNOWN`, `DEFERRED`, or `BLOCKED`, Slice 10
creates a deterministic non-concrete private lineage state matching that status
and preserving the corresponding private reason.

If a relation row dependency graph is missing or non-concrete, Slice 10 creates
a deterministic non-concrete private lineage state with empty facts.

Non-concrete lineage states do not create public diagnostics.

## Relationship To Dependency Graph

Slice 10 may consume `relation_row_dependency_graphs` to identify direct and
renamed projection edges. The lineage carrier remains independent, simple, and
minimal. It does not mutate dependency graph carriers and does not define row
dependency cycles.

## Privacy

Project JSON v2 remains unchanged. It serializes no `relation_row_lineages`, no
`ProjectRelationRowLineage`, no `ProjectRowLineageSegment`, no
`ProjectRowLineageFact`, no lineage statuses or reasons, no lineage facts or
segments, no dependency facts, no row schema facts, no provenance facts, and no
let facts.

The same privacy boundary applies to CLI text, CLI JSON v1, Semantic Metadata
Artifact v1, IR, SQL, and future public APIs unless a later phase explicitly
changes it.

## Future Work

Computed alias lineage, selected `let` lineage, and full or transitive
multi-hop lineage expansion remain Slice 11 or later.
