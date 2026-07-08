# Phase 49 Computed/Let/Multi-hop Row Lineage v1

## Purpose

This specification locks Phase 49 Slice 11: Lineage for computed/let/multi-hop
fields.

Slice 11 extends the private project row lineage carrier to cover computed
aliases, selected `let`-derived outputs, concrete relation-local `let` binding
expression dependencies, and concrete multi-hop lineage expansion. The carrier
remains private project semantic state only.

Package version remains `0.1.0`.

## Non-goals

Slice 11 does not implement:

- public Project JSON v2 lineage, dependency, row schema, metadata, or explain
  output;
- project explain;
- project IR, project SQL, or project `emit-sql`;
- public diagnostics or diagnostic wording changes;
- public semantic API changes;
- parser, grammar, or generated ANTLR changes;
- JOIN or relationship behavior;
- aggregate or grouped output schema;
- aggregate or grouped lineage;
- expression-operation or literal lineage node kinds;
- synthetic derived `FieldDef` values;
- bridge, export, RAG, Arrow, import, or export behavior;
- runtime or database execution;
- package version, tag, release, publish, upload, signing, or attestation.

## Data Model Extensions

Slice 11 extends the private lineage model in
`src/pietto/_project/row_lineage.py`.

`ProjectRowLineageSegmentKind` adds:

- `LET_BINDING`.

`ProjectRowLineageFactKind` adds:

- `COMPUTED_EXPRESSION`;
- `LET_OUTPUT`;
- `LET_EXPRESSION`;
- `TRANSITIVE_DEPENDENCY`.

Slice 11 reuses existing private carriers:

- `ProjectRowLineageSegment`;
- `ProjectRowLineageFact`;
- `ProjectRelationRowLineage`.

Slice 11 does not add expression-operation or literal lineage segment kinds.
Dependency graph expression traversal remains private and field-oriented.

## Behavior

Direct and renamed facts from Slice 10 remain preserved. Source-backed direct
and renamed projections still use `SOURCE_FIELD` upstream segments.
Relation-backed direct and renamed projections still keep immediate
`UPSTREAM_FIELD` facts.

Computed alias lineage consumes private dependency graph
`COMPUTED_EXPRESSION` edges. For each concrete field dependency, the lineage
carrier records a `COMPUTED_EXPRESSION` fact from the output field segment to a
source-backed or relation-backed upstream field segment. Function call names,
operators, and literals are not lineage segments.

Selected `let` output lineage consumes private dependency graph `LET_OUTPUT`
edges. The selected output field records a `LET_OUTPUT` fact to a
`LET_BINDING` segment.

Concrete relation-local `let` binding expression lineage consumes private
dependency graph `LET_EXPRESSION` edges. A `LET_BINDING` segment may depend on
source-backed upstream fields, relation-backed upstream fields, or earlier
`LET_BINDING` segments. Earlier-let segments are preserved and are not
flattened away.

Concrete multi-hop expansion adds deterministic `TRANSITIVE_DEPENDENCY` facts
when an upstream relation lineage is concrete and has lineage facts for the
referenced upstream output field. Transitive expansion applies to direct,
renamed, computed, and `let` expression facts that depend on relation-backed
upstream fields. Selected `let` output facts may also gain transitive facts
through the referenced `LET_BINDING` segment.

Transitive expansion must not replace immediate facts. Immediate
`DIRECT_PROJECTION`, `RENAMED_PROJECTION`, `COMPUTED_EXPRESSION`,
`LET_OUTPUT`, and `LET_EXPRESSION` facts remain present.

Transitive expansion is cycle-safe and deterministic:

- relation-level cycles should already be blocked, but the lineage helper must
  still avoid infinite recursion;
- repeated facts are deduplicated deterministically;
- source order and dependency graph edge order remain the basis for tuple
  ordering.

Aggregate and grouped dependency or lineage remains absent/deferred in Slice
11.

## Non-concrete Behavior

If a relation row schema state or dependency graph state is `UNKNOWN`,
`DEFERRED`, or `BLOCKED`, Slice 11 preserves a deterministic non-concrete
private lineage state with empty facts.

Non-concrete lineage states emit no public diagnostics.

## Privacy

Project JSON v2 remains unchanged. It serializes no `relation_row_lineages`, no
`ProjectRelationRowLineage`, no `ProjectRowLineageSegment`, no
`ProjectRowLineageFact`, no lineage statuses or reasons, no lineage facts or
segments, no dependency graph facts, no row schema facts, no provenance facts,
and no `let` facts.

The same privacy boundary applies to CLI text, CLI JSON v1, Semantic Metadata
Artifact v1, IR, SQL, and future public APIs unless a later phase explicitly
changes it.

## Future Work

Project explain, export, public lineage output, and public metadata output
remain future work. Aggregate/grouped output schema and aggregate/grouped
lineage remain out of scope for Phase 49 Slice 11.
