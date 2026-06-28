# Phase 34 Narrow JOIN Syntax And Semantic Contract v1

## Purpose

This specification records the Phase 34 Slice 3 narrow JOIN syntax and
semantic contract. Slice 3 is docs/spec/static-audit/status-only work.

This document defines future source-shape requirements, future semantic
preconditions, fail-closed cases, SQL parity expectations, and preservation
boundaries for a later explicitly approved narrow JOIN implementation slice.
It does not implement JOIN, does not implement JOIN syntax, and does not define
accepted Pietto syntax.

Final token spelling and grammar remain deferred to a later explicitly approved
implementation slice.

## Relationship To Earlier Phase 34 Slices

Slice 1 established the Phase 34 candidate decision, the relationship
grain/narrow JOIN future boundary, and the Phase 33 project-mode handoff.

Slice 2 established relationship grain as a compile-time metadata contract
around endpoint row identity and cardinality expectations. Slice 2 also
recorded that endpoint and pairwise relationship-edge grain facts are future
prerequisites for narrow JOIN acceptance.

Slice 3 depends on those boundaries. It does not widen them and does not
authorize implementation.

## Current Implementation Baseline

Current relationship metadata is metadata-only. It is validated and stored as
read-only semantic facts, but it does not enter relation, type, callable, or
field lookup.

Relationship metadata is not lowered to Semantic IR, PostgreSQL SQL, MySQL SQL,
CLI text, JSON v1, Project JSON v2, Semantic Metadata Artifact v1, project
outputs, or runtime behavior.

Current relation bodies remain single-input. Current `from` behavior remains
unchanged: one relation body names one existing relation input through the
existing `from` model.

Current qualified field lookup remains single-input only. A two-part field
reference is accepted only when its qualifier is the current relation input
qualifier, and relationship metadata does not participate in qualified field
lookup.

## Future Narrow JOIN Source-shape Contract

Every source-shape term in this section is a future contract term only. These
terms are not accepted Pietto syntax, do not introduce accepted keywords, and
do not imply grammar approval.

A later narrow JOIN implementation must require:

- explicit query opt-in;
- exactly one declared relationship metadata edge;
- one existing base relation;
- exactly one joined endpoint;
- deterministic endpoint names;
- deterministic endpoint ownership;
- deterministic field ownership;
- required grain facts before acceptance;
- no automatic relationship inference;
- no graph traversal;
- no relationship chaining;
- no arbitrary SQL-like freeform JOIN;
- no project-mode multi-file relationship resolution.

The future source shape must make the selected relationship edge, base relation,
joined endpoint, endpoint ownership, and field ownership explicit enough that
semantic analysis can fail closed before IR or SQL lowering.

## Future Semantic Preconditions

Before any future narrow JOIN source shape is accepted, all of these
preconditions must hold:

- selected relationship metadata exists and is semantically valid;
- selected relationship has exactly two validated endpoints;
- base relation is statically known and matches exactly one selected endpoint;
- joined endpoint is explicitly selected and statically known;
- endpoint schemas are statically known;
- endpoint and pairwise relationship-edge grain facts are statically known;
- supported cardinality/fanout posture is known;
- endpoint qualification makes every field owner deterministic;
- scope visibility for future `where`, `select`, and `order by` is defined
  before implementation;
- PostgreSQL/MySQL can faithfully lower the same accepted semantic subset.

These preconditions are requirements for a later implementation slice. Slice 3
does not add semantic validation, diagnostics, Semantic IR fields, or SQL
lowering.

## Fail-closed Cases

Future narrow JOIN work must fail closed when any of these cases applies:

- unknown relationship;
- duplicate relationship;
- ambiguous relationship selection;
- base relation not matching selected relationship endpoint;
- ambiguous endpoint owner;
- self-relationship without explicit disambiguation;
- ambiguous field qualification;
- duplicate visible field owner;
- missing grain;
- unknown grain;
- contradictory grain;
- unsupported cardinality;
- unsupported `many-to-many`;
- unsupported fanout-producing posture;
- unknown endpoint schema;
- backend cannot preserve semantic ownership, qualification,
  grain/cardinality, or join shape;
- any request for graph traversal, chaining, inference, project aggregation,
  DB introspection, runtime execution, or security behavior.

Fail closed means deterministic compiler diagnostics and no approximate SQL. It
does not mean runtime denial enforcement and must not be described as a
security control.

## PostgreSQL/MySQL Parity Contract

A later SQL implementation must lower only an explicitly accepted semantic
subset. PostgreSQL and MySQL must either both accept and faithfully lower the
same subset or both fail closed with deterministic diagnostics.

Future lowering must preserve endpoint ownership and field qualification in
deterministic SQL aliases, keep deterministic SQL artifact bytes, and preserve
the semantic relationship/grain decisions made before backend rendering.

Future lowering must not use hidden runtime row combination, in-memory JOIN
fallback, connector execution, DB schema introspection, or backend-specific
approximation.

The exact SQL join kind and alias generation are deferred to a later explicitly
approved implementation slice.

## Phase 33 Project And JSON Preservation

Slice 3 preserves the Phase 33 project-mode and JSON boundaries:

- `pietto check --project ROOT` remains root/config-only;
- project source selection remains deferred;
- project JSON v2 remains check root/config-only;
- project emit-sql remains rejected;
- project explain remains rejected;
- single-file `pietto check --format json` remains JSON v1;
- single-file `pietto emit-sql --format json` remains JSON v1;
- single-file `pietto explain --format json` remains Semantic Metadata
  Artifact v1.

Slice 3 adds no project source selection, TOML schema parsing, glob expansion,
project source parsing, multi-file semantic analysis, project SQL, project
explain, project metadata aggregation, JSON v1 schema change, Project JSON v2
schema change, or Semantic Metadata Artifact v1 schema change.

## Explicit Non-goals

Slice 3 does not implement or authorize:

- grammar changes;
- generated parser changes;
- AST changes;
- semantic model changes;
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
- semantic validation;
- IR or SQL lowering;
- CLI/JSON/project/runtime behavior;
- relationship graph traversal;
- relationship chaining;
- automatic join inference;
- arbitrary SQL-like freeform JOIN;
- project-mode multi-file relationship resolution;
- SQL execution;
- runtime security;
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

No package version change is made by Slice 3. Package version remains `0.1.0`.
No tag/release/publish/upload/signing/attestation is performed by Slice 3.

## Slice 3 Implementation Boundary

Slice 3 adds this contract, a Phase 34 plan status update, and focused static
audit tests only.

This spec does not change grammar, generated files, AST, semantic model, IR,
SQL, CLI, JSON, fixtures, goldens, scripts, package metadata, dependencies,
workflows, public API, project behavior, runtime behavior, or database
behavior.
