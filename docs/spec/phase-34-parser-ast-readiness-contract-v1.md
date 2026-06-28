# Phase 34 Parser / AST Readiness Contract v1

## Purpose

This specification records the Phase 34 Slice 4 Parser / AST readiness contract
for future narrow JOIN work.

Slice 4 is docs/spec/static-audit/status-only work. It defines current
grammar/generated/AST constraints, future parser and AST readiness
requirements, generated-file implications, preservation boundaries, and
explicit non-goals.

This document does not implement JOIN, does not implement JOIN syntax, does not
implement grain syntax, does not implement parser behavior, and does not define
accepted Pietto syntax.

## Relationship To Earlier Phase 34 Slices

Slice 1 established the Phase 34 candidate boundary: relationship grain and
narrow JOIN are future work, and narrow JOIN is later-slice only.

Slice 2 established relationship grain as a compile-time metadata contract
around endpoint row identity and cardinality expectations. Relationship grain
prerequisites remain required future inputs before any narrow JOIN acceptance.
In Slice 4, relationship grain prerequisites remain required future inputs
before any narrow JOIN acceptance.

Slice 3 established the future narrow JOIN source-shape and semantic contract:
one explicit relationship metadata edge, explicit query opt-in, one base
relation plus one joined endpoint, deterministic endpoint qualification,
required grain facts, PostgreSQL/MySQL parity, and fail-closed behavior.

Slice 4 preserves those boundaries. It only records parser and AST readiness
requirements for later separately approved implementation slices.

## Current Grammar Baseline

The current grammar baseline is:

- `script` accepts top-level `definition` and `relationshipDefinition` entries;
- `relationshipDefinition` is top-level relationship metadata;
- relationship metadata currently has exactly two endpoints;
- endpoint syntax currently records a local endpoint name and a relation name;
- relation body currently has one `fromClause`;
- `fromClause` is single-input;
- Pietto blocks use colon, newline, indentation, and dedentation;
- there is no accepted join production;
- there is no accepted grain syntax.

Slice 4 does not modify `grammar/Pietto.g4`, does not introduce accepted
keywords, and does not add parser behavior.

## Current Generated-file Baseline

Changes to `grammar/Pietto.g4` require regenerating the tracked ANTLR outputs
under `src/pietto/generated/`.

The `src/pietto/generated/` inventory must remain byte-for-byte verified by
`scripts/check_generated.py`.

Slice 4 does not modify grammar or generated files.

## Current AST And Builder Baseline

The current AST and builder baseline is:

- `RelationshipMetadata`;
- `RelationshipEndpoint`;
- `FromClause(source_name)`;
- `TableDef` has one `from_clause`;
- `QueryDef` has one `from_clause`;
- there is no AST node for a join list;
- there is no AST node for endpoint scope;
- there is no AST node for relationship edge selection;
- there is no AST node for a grain carrier;
- there is no AST behavior for a multi-input field owner.

Slice 4 does not modify `src/pietto/ast_nodes.py` or
`src/pietto/ast_builder.py`.

## Future Parser / AST Readiness Requirements

Future parser and AST implementation remains deferred. Before any
implementation slice changes grammar, generated files, parser behavior, or AST
nodes, that later slice must make these decisions explicitly:

- final token spelling is deferred;
- final grammar productions are deferred;
- final AST class names/fields are deferred;
- the future AST/source shape must represent the selected relationship edge;
- the future AST/source shape must represent one base relation or endpoint
  owner;
- the future AST/source shape must represent exactly one joined endpoint;
- the future AST/source shape must represent deterministic endpoint
  qualification;
- the future AST/source shape must leave room for field ownership;
- the future AST/source shape must leave room for grain prerequisite references
  or semantic binding;
- the future AST/source shape must handle self-relationship disambiguation;
- the future AST/source shape must preserve single-input compatibility until an
  implementation slice explicitly changes it.

These requirements do not define final syntax, do not define final class names,
and do not approve implementation.

## Semantic Readiness Boundary

Slice 4 adds no semantic validation and no diagnostic codes.

Later semantic work must separately decide relationship selection, endpoint
ownership, field ownership, grain requirements, unsupported fanout/cardinality
behavior, backend capability handling, and fail-closed diagnostics.

Relationship metadata remains outside relation, type, callable, and field
lookup. Relationship grain prerequisites remain future compile-time metadata
requirements, not runtime enforcement, not database constraint introspection,
not authorization, not optimization proof, and not a security guarantee.

## IR / SQL / CLI / JSON / Project Preservation

Slice 4 changes no `RelationIR` shape and adds no SQL JOIN lowering.

Slice 4 changes no fixtures or goldens, no CLI behavior, no JSON v1 behavior,
no Project JSON v2 behavior, and no Semantic Metadata Artifact v1 behavior.

Slice 4 preserves Phase 33 project/JSON boundaries:

- `pietto check --project ROOT` remains root/config-only;
- project source selection remains deferred;
- TOML schema parsing remains deferred;
- glob expansion remains deferred;
- project source parsing remains deferred;
- multi-file semantic analysis remains deferred;
- project JSON v2 remains check root/config-only;
- project emit-sql remains rejected;
- project explain remains rejected;
- project metadata aggregation remains deferred;
- single-file `pietto check --format json` remains JSON v1;
- single-file `pietto emit-sql --format json` remains JSON v1;
- single-file `pietto explain --format json` remains Semantic Metadata
  Artifact v1.

## Explicit Non-goals

Slice 4 does not implement or authorize:

- grammar changes;
- generated parser changes;
- AST changes;
- parser behavior changes;
- semantic model changes;
- semantic validation;
- diagnostic code additions;
- IR changes;
- SQL backend changes;
- CLI behavior changes;
- JSON v1 or JSON v2 behavior changes;
- Semantic Metadata Artifact v1 changes;
- fixtures/goldens changes;
- scripts changes;
- package metadata, package version, dependency, or workflow changes;
- JOIN implementation;
- JOIN syntax implementation;
- grain syntax implementation;
- relationship graph traversal;
- relationship chaining;
- automatic join inference;
- SQL execution;
- runtime security;
- runtime behavior;
- database/schema introspection or db pull;
- project source selection;
- TOML schema parsing;
- glob expansion;
- multi-file semantic analysis;
- project emit-sql;
- project explain;
- project metadata aggregation;
- graph/ERD/AI metadata export;
- release/tag/publish/upload/signing/attestation behavior.

No package version change is made by Slice 4. Package version remains `0.1.0`.
No tag/release/publish/upload/signing/attestation is performed by Slice 4.

## Implementation Boundary

This spec does not change grammar, generated files, AST, parser behavior,
semantic model, IR, SQL, CLI, JSON, fixtures, goldens, scripts, package
metadata, dependencies, workflows, public API, project behavior, runtime
behavior, or database behavior.
