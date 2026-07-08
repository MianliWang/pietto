# Phase 48 Propagated Field Provenance / Lineage Hardening v1

## Purpose

This contract locks Phase 48 Slice 6: Propagated field provenance / lineage
hardening.

Slice 6 is docs/spec/tests-only. It does not change production model code. It
records and tests the current private provenance behavior for propagated direct
field projections, and it keeps full lineage chains deferred for future
explain/export work.

## Provenance And Lineage

Provenance means immediate semantic projection metadata used by compiler
internals. For direct projections, current private provenance identifies the
current projection step: the projection kind, the immediate upstream
source/table/query symbol, and the downstream projection expression location.

Lineage means a future explain/export chain that can describe a complete path
through prior relations. Lineage is not implemented in Slice 6. Slice 6 adds no
private lineage carrier, no lineage path model, and no public lineage output.

`ProjectRowFieldProvenance` remains private. It is not serialized and is not a
public semantic API.

## Propagated Field Invariants

For propagated direct projections:

- `ProjectRowField.resolved_type` is preserved from the upstream field;
- `ProjectRowField.nullability` is preserved from the upstream field;
- `ProjectRowField.field_def` preserves the originating source `FieldDef` when
  available;
- `ProjectRowField.name` is the downstream output name or alias;
- `ProjectRowField.provenance.kind` is `DIRECT_PROJECTION`;
- `ProjectRowField.provenance.symbol` is the immediate upstream source/table/query
  symbol used by the current `from` clause;
- `ProjectRowField.provenance.location` is the current downstream projection
  expression location.

Across multi-hop propagation, the originating field facts continue to flow
through the concrete row schema. Provenance remains immediate to the current
projection step and must not become a full source lineage path.

## Renames

Renamed bare projections and renamed qualified projections preserve the
originating `FieldDef`, type, and nullability facts. The downstream field name
is the output alias. Provenance still points at the immediate upstream
source/table/query symbol and the downstream projection expression location.

## Flat Selector Model

Slice 6 preserves the flat relation schema model. Downstream selectors may use
only the immediate upstream relation qualifier. Original source qualifiers and
multi-part lineage selectors do not become valid selector syntax.

Existing `PIE-S2102` remains authoritative for original-source qualifiers and
multi-part lineage selectors over concrete upstream schemas. Slice 6 adds no
new diagnostics and changes no diagnostic wording or ordering.

## Project JSON v2 Privacy

Project JSON v2 top-level shape remains unchanged.

Slice 6 serializes no row schema facts, no `relation_row_schema_states`, no
provenance facts, no lineage facts, no `ProjectRowSchema`, no
`ProjectRowField`, no `ProjectRowFieldProvenance`, and no private provenance
kind values.

## Non-goals

Slice 6 does not implement:

- production model code changes;
- a private lineage carrier;
- Project JSON v2 output changes;
- public project semantic API;
- selector syntax expansion;
- computed alias schema;
- `let` schema;
- aggregate or grouped output schema;
- non-concrete upstream propagation;
- project explain;
- metadata export;
- Arrow or RAG bridge behavior;
- relationship or JOIN behavior;
- project IR, project SQL, project `emit-sql`, or project `explain`;
- parser, grammar, or generated artifact changes;
- new diagnostics;
- package version, tag, release, publish, upload, signing, or attestation
  behavior.
