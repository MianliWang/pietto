# Phase 49 Private Row-level Dependency Graph Scaffold v1

## Purpose

This specification locks Phase 49 Slice 9: Private row-level dependency graph
scaffold.

Slice 9 adds private project semantic facts that describe immediate row-level
dependencies for supported project relation outputs. The scaffold prepares
future semantic dependency/cycle analysis and full lineage work without
exposing dependency facts publicly and without implementing full lineage.

Package version remains `0.1.0`.

## Non-goals

Slice 9 does not implement:

- full lineage carrier behavior;
- public Project JSON v2 row schema, dependency, lineage, metadata, or explain
  output;
- public project semantic API behavior;
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

Slice 9 introduces private project dependency graph carriers under
`src/pietto/_project/row_dependency_graph.py`:

- `ProjectRowDependencyGraphStatus`;
- `ProjectRowDependencyGraphReason`;
- `ProjectRowDependencyNodeKind`;
- `ProjectRowDependencyEdgeKind`;
- `ProjectRowDependencyNode`;
- `ProjectRowDependencyEdge`;
- `ProjectRelationRowDependencyGraph`.

The graph status values are:

- `CONCRETE`;
- `UNKNOWN`;
- `DEFERRED`;
- `BLOCKED`.

Graph reasons mirror current private row schema availability reasons where
possible, including direct source concrete, table/relation upstream concrete,
unknown schema, duplicate output name, deferred Phase 48 behavior, unresolved
relation blocked, cycle blocked, upstream unknown, upstream deferred, and
upstream blocked. Slice 9 also allows deterministic private missing-fact
reasons such as missing row schema state, missing row schema, and missing
upstream schema.

Node kinds are:

- `OUTPUT_FIELD`;
- `UPSTREAM_FIELD`;
- `LET_BINDING`.

Edge kinds are:

- `DIRECT_PROJECTION`;
- `RENAMED_PROJECTION`;
- `COMPUTED_EXPRESSION`;
- `LET_OUTPUT`;
- `LET_EXPRESSION`.

Nodes and edges are frozen private dataclasses. Graphs store deterministic
tuples of nodes and edges.

## Storage

`ProjectSemanticModel` stores a private mapping named
`relation_row_dependency_graphs`, keyed by `TableDef | QueryDef`.

There are no source-level top-level row dependency graphs. Source fields appear
as immediate upstream field nodes when a relation output depends on them.

The mapping is copied into a readonly mapping with the other private project
semantic model facts. It is not a public semantic API.

## Behavior

Slice 9 builds row dependency graphs after private relation row schemas,
relation row schema states, and relation-local let scope facts are available.

For concrete relation row schemas:

- a direct projection output depends on the immediate upstream field through a
  `DIRECT_PROJECTION` edge;
- a renamed projection output depends on the immediate upstream field through a
  `RENAMED_PROJECTION` edge;
- a computed alias output depends on direct input fields and admitted
  relation-local let leaves used by its expression through
  `COMPUTED_EXPRESSION` edges;
- a selected let-derived output depends on the selected relation-local let
  binding through a `LET_OUTPUT` edge;
- each concrete let binding gets `LET_EXPRESSION` edges to direct input fields
  and earlier admitted let bindings used by the binding expression.

Multi-hop propagation remains immediate-upstream only. Slice 9 records that the
current relation output depends on the immediately selected upstream field. It
does not expand that edge into a full source lineage chain.

Dependency extraction is limited to row-level expression forms already used by
Phase 49 Slices 3 through 8. `NameExpr` dependencies resolve first to input
fields and then to admitted let bindings. Two-part `DottedNameExpr`
dependencies resolve only to immediate upstream fields when the qualifier
matches the relation input qualifier. Qualified let references are not let
dependencies.

`CallExpr` extraction traverses call arguments. It must not treat callee or
function names such as `lower`, `trim`, `len`, or `matches` as row fields.

Aggregate and grouped output schema remain out of scope. Aggregate/grouped
dependency extraction is not implemented in Slice 9.

## Non-concrete Behavior

If a relation row schema state is `UNKNOWN`, `DEFERRED`, or `BLOCKED`, Slice 9
creates a deterministic non-concrete private dependency graph state matching
that status and preserving the corresponding private reason.

Missing private facts create deterministic private non-concrete graph states.
They do not create public diagnostics.

If relation-local let facts are unknown, deferred, blocked, or absent, Slice 9
may still build output dependencies that are available from the concrete row
schema and current select expressions. It omits let expression edges that
require unavailable concrete let value facts.

## Privacy

Project JSON v2 remains unchanged. It serializes no
`relation_row_dependency_graphs`, no `ProjectRelationRowDependencyGraph`, no
`ProjectRowDependencyNode`, no `ProjectRowDependencyEdge`, no dependency graph
nodes or edges, no private dependency graph statuses or reasons, and no
dependency, lineage, provenance, row schema, or let fact internals.

The same privacy boundary applies to CLI text, CLI JSON v1, Semantic Metadata
Artifact v1, IR, SQL, and future public APIs unless a later phase explicitly
changes it.

## Future Work

Semantic row dependency/cycle analysis remains future work unless existing
private behavior already supports a case. Slice 9 adds no row-level cycle
diagnostic.

Full lineage remains Slices 10 and 11. Future lineage work may consume the
private row dependency graph, but Slice 9 does not implement lineage carrier
nodes, lineage paths, transitive expansion, project explain output, or export
behavior.
