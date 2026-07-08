# Phase 49 Computed Alias Origin/Provenance Privacy v1

## Purpose

This contract defines Phase 49 Slice 5: Computed alias origin/provenance
privacy.

Slice 5 hardens private project row field provenance for computed aliases. It
does not change public behavior. It does not expand expression semantics,
Project JSON v2, CLI behavior, IR, SQL, diagnostics, parser/grammar/generated
files, runtime behavior, package metadata, or release state.

Package version remains `0.1.0`.

## Slice 4 Reality

Phase 49 Slice 4 made legal computed aliases concrete as private project row
schema fields when the upstream row schema is concrete and current row-level
expression inference supplies a known `ValueType`.

Slice 4 used `ProjectRowFieldProvenanceKind.EXPRESSION` for those computed
alias fields. That was private, but too vague for the Slice 2 and Slice 3
origin vocabulary. The adapter already distinguishes computed expressions as
`DERIVED_EXPRESSION`, while future `LET_DERIVED`, `AGGREGATE`, and `UNKNOWN`
origins have separate meanings.

## Required Private Vocabulary Alignment

Computed alias project row schema fields use private
`ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION`.

Direct projections keep their existing private projection provenance behavior.
Renamed direct projections also keep the existing repository behavior, which is
the direct projection provenance category while preserving the output alias
name and source-native field facts. Slice 5 does not force a broader rename
provenance refactor.

`EXPRESSION` may remain as a private legacy vocabulary value for compatibility,
but Slice 5 computed alias fields must not use it.

Future `LET_DERIVED`, `AGGREGATE`, and `UNKNOWN` provenance/origin behavior
remains private readiness unless already present in lower-level adapter results.
Slice 5 does not populate project relation row schemas from selected `let`
references and does not implement aggregate/grouped output schema.

## field_def Boundary

`field_def` remains source-native only. A non-`None` project row field
`field_def` points to an original shape/source `FieldDef`.

Computed alias fields are derived fields. They use `field_def=None` and must
not synthesize a derived `FieldDef`. Derived fields must not look
source-native.

Direct, renamed, and multi-hop direct projections may preserve source-native
`field_def` when the projected field is genuinely source-native. Propagating a
computed alias through later direct projections keeps `field_def=None`.

## Symbol And Location

Computed alias provenance keeps the immediate upstream relation symbol. This
records the private source of the row expression scope without claiming full
dependency or lineage behavior.

Computed alias provenance keeps the current source-location semantics supplied
by the Slice 4 adapter result. Slice 5 does not introduce a new location model,
select-item carrier, dependency graph, or full lineage carrier.

## Privacy

Project JSON v2 remains unchanged. It serializes no private row schema facts,
no origin/provenance facts, no adapter facts, no dependency facts, no lineage
facts, no relation row schema state facts, and no private reason/status values.

Private provenance is not public project semantic API, not selector syntax, not
project explain output, and not Semantic Metadata Artifact output.

Slice 5 adds no public diagnostics and preserves existing diagnostic ordering.

## Future Relationship

Project `let` facts remain Slice 6.

Selected `let`-derived output schema remains Slice 7.

Private row-level dependency graph remains Slice 9.

Minimal private lineage carrier work remains Slices 10 and 11.

Aggregate and grouped output schema remain Phase 50 or later.

## Explicit Non-goals

Slice 5 does not implement:

- project `let` scope/value facts;
- selected `let`-derived output schema;
- private dependency graph;
- full lineage carrier;
- aggregate/grouped output schema;
- Project JSON v2 row schema, origin, provenance, dependency, or lineage
  output;
- public project semantic API;
- public diagnostics;
- parser, grammar, or generated ANTLR changes;
- project explain;
- project IR;
- project SQL;
- project `emit-sql`;
- JOIN or relationship behavior;
- bridge/export/RAG/Arrow behavior;
- import/export or module behavior;
- multi-file semantic behavior expansion;
- runtime or database execution;
- package version, tag, release, publish, upload, signing, or attestation.
