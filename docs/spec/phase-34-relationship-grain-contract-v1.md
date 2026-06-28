# Phase 34 Relationship Grain Contract v1

## Purpose

This specification records the Phase 34 Slice 2 relationship grain contract.
Slice 2 is docs/spec/static-audit/status-only work.

This document defines terminology, future acceptance prerequisites, and
fail-closed boundaries for relationship grain. It does not implement JOIN,
does not define final JOIN syntax, does not define final grain syntax, and
does not approve grammar, generated parser, AST, semantic model, IR, SQL, CLI,
JSON, project, runtime, database, fixture, golden, script, package,
dependency, workflow, release, or public API behavior.

Phase 34 is not complete after Slice 2.

## Relationship Grain Definition

Relationship grain is a compile-time metadata contract around endpoint row
identity and cardinality expectations. It may later constrain whether a
relationship edge is safe for narrow JOIN acceptance.

Relationship grain is compile-time metadata describing expected row
identity/cardinality behavior around relationship endpoints.

Relationship grain is not runtime enforcement, not database constraint
introspection, not authorization, not optimization proof, and not a security
guarantee.

Relationship grain is a contract vocabulary for future relationship-aware query
composition. Slice 2 does not add a metadata carrier, source syntax, semantic
validation, diagnostic code, IR field, SQL rendering, CLI output, JSON field,
project output, or runtime behavior for grain.

## Current Relationship Metadata Handoff

Phase 14 added relationship metadata syntax as parse-only and AST-only source
metadata. Current source metadata is limited to a relationship name and
relationship-local endpoints. Each endpoint records a local endpoint name and a
referenced relation name.

Phase 15 added semantic validation and read-only semantic storage for validated
relationship metadata. Current semantic endpoint facts are limited to:

- local endpoint metadata name;
- referenced relation name;
- resolved existing `SourceDef`, `TableDef`, or `QueryDef`.

Current relationship metadata does not carry grain, cardinality, fanout,
optionality, multiplicity, identity, key, provenance, trust, or validation
facts.

Relationship metadata remains outside relation, type, callable, and field
lookup. It is not lowered to Semantic IR, PostgreSQL SQL, MySQL SQL, CLI text,
JSON v1, Project JSON v2, or Semantic Metadata Artifact v1.

## Grain Levels

Every grain level in this section is a contract term only. These terms are not
Pietto source syntax and do not add AST, semantic model, IR, SQL, CLI, or JSON
behavior.

| Term | Contract meaning |
|---|---|
| Endpoint grain | Future compile-time metadata for one relationship endpoint's expected row identity, optionality, and multiplicity posture. |
| Relationship-edge grain | Future compile-time metadata for the pairwise cardinality and fanout posture across two endpoints in one relationship metadata edge. |
| Relation grain | Future relation identity/schema prerequisite that may be needed to justify endpoint grain; Slice 2 does not add a relation metadata carrier. |
| One-row-per endpoint expectation | Future assertion that one endpoint contributes at most one matching row for each qualifying row owned by the other endpoint under the accepted edge direction. |
| Fanout risk | The possibility that future composition multiplies rows, duplicates rows, or changes aggregate, ordering, limit, or downstream row semantics. |

Slice 2 recommends contract separation between endpoint grain,
relationship-edge grain, and relation grain. It does not choose final syntax or
storage for any of them.

## Cardinality And Fanout Vocabulary

The following labels are contract vocabulary only. They are not accepted Pietto
syntax, not reserved keywords, not enum values in the semantic model, and not
diagnostic codes.

Endpoint-side vocabulary:

- `one`;
- `zero-or-one`;
- `many`.

Relationship-edge cardinality vocabulary:

- `one-to-one`;
- `many-to-one`;
- `one-to-many`;
- `many-to-many`.

Fanout posture vocabulary:

- `fanout-free`;
- `fanout-producing`;
- `unknown`;
- `unsafe`;
- `ambiguous`.

Row-shape posture vocabulary:

- `cardinality-preserving`;
- `optional-match`;
- `required-match`.

Future slices may refine, rename, or reject these labels before implementation.
Slice 2 only locks the concepts that future work must address.

## Future Narrow JOIN Grain Prerequisites

Before any later narrow JOIN slice accepts relationship-aware composition, the
accepted source must have statically known grain facts sufficient to decide the
supported row-shape and fanout posture.

A future narrow JOIN acceptance decision must require:

- a single validated relationship metadata edge;
- explicit query opt-in;
- exactly one base relation plus one joined endpoint;
- deterministic endpoint role and endpoint name ownership;
- deterministic endpoint qualification for fields and scopes;
- statically known endpoint schemas;
- endpoint and pairwise edge grain facts statically known;
- endpoint grain facts for both participating endpoints;
- relationship-edge grain facts for the selected pair of endpoints;
- a declared, validated, or otherwise explicitly trusted basis for the grain
  facts;
- fanout posture within the later approved MVP support boundary;
- a supported cardinality and fanout posture for the MVP subset;
- PostgreSQL/MySQL lowering capability for the same accepted semantic subset.

Unsupported, missing, contradictory, unsafe, or ambiguous grain facts must fail
closed before SQL is emitted.

## Fail-closed Grain Cases

Future relationship grain and narrow JOIN work must fail closed when:

- the selected relationship metadata edge is missing, unknown, duplicated, or
  ambiguous;
- missing grain;
- unknown grain;
- contradictory grain;
- ambiguous endpoint ownership;
- ambiguous qualification;
- unsafe fanout;
- unsupported cardinality;
- unknown endpoint schema;
- backend lowering cannot preserve semantics;
- an endpoint name or endpoint owner is ambiguous;
- endpoint qualification is absent where required;
- either endpoint schema is unknown;
- endpoint grain is missing for either endpoint;
- relationship-edge grain is missing;
- relation identity prerequisites are missing where the future contract
  requires them;
- grain facts conflict with each other;
- grain provenance, validation, or trust assumptions are unavailable where the
  future contract requires them;
- the cardinality posture is `many-to-many`, `unknown`, `unsafe`, or
  `ambiguous` unless a later approved slice explicitly accepts that posture;
- fanout is possible but not explicitly accepted by the later approved slice;
- the query shape would require arbitrary multi-hop traversal, relationship
  chaining, relationship graph traversal, or automatic join inference;
- PostgreSQL or MySQL cannot faithfully lower the accepted semantic facts.

Fail closed means deterministic compiler diagnostics and no approximate SQL. It
does not mean runtime denial enforcement and must not be described as a
security control.

## Phase 33 Project And JSON Preservation

Slice 2 preserves the Phase 33 project-mode and JSON boundaries:

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

Slice 2 adds no project source selection, project parsing, project semantic
analysis, project SQL, project explain, project metadata aggregation, JSON v1
schema change, Project JSON v2 schema change, or Semantic Metadata Artifact v1
schema change.

## Explicit Non-goals

Slice 2 does not implement or authorize:

- grammar changes;
- generated parser changes;
- AST changes;
- semantic model changes;
- IR changes;
- SQL backend changes;
- CLI behavior changes;
- JSON v1 or JSON v2 behavior changes;
- Semantic Metadata Artifact v1 behavior changes;
- fixture or golden changes;
- script changes;
- package metadata, package version, dependency, or workflow changes;
- JOIN implementation;
- JOIN syntax;
- relationship grain syntax;
- relationship grain semantic validation;
- endpoint grain storage;
- relationship-edge grain storage;
- relation grain storage;
- endpoint role enforcement;
- cardinality validation;
- fanout validation;
- relationship graph traversal;
- arbitrary multi-hop traversal;
- relationship chaining;
- automatic join inference;
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

No package version change is made by Slice 2. Package version remains `0.1.0`.
No tag/release/publish/upload/signing/attestation is performed by Slice 2.

## Slice 2 Implementation Boundary

Slice 2 adds this contract, a Phase 34 plan status update, and focused static
audit tests only.

This contract does not change grammar, generated files, AST, semantic model,
IR, SQL, CLI, JSON, fixtures, goldens, scripts, package metadata,
dependencies, workflows, public API, runtime behavior, database behavior, or
project behavior.
