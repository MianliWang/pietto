# Phase 34 Semantic Readiness Contract v1

## Purpose

This specification records the Phase 34 Slice 5 Semantic Readiness Contract for
future relationship grain and narrow JOIN semantic validation/model integration.

Slice 5 is docs/spec/static-audit/status-only work. It documents current
relationship semantic facts, current validation behavior, current single-input
field lookup constraints, future semantic prerequisites, endpoint and field
ownership requirements, diagnostics readiness boundaries, preservation
requirements, and explicit non-goals.

This document does not implement JOIN, does not implement JOIN syntax, does not
implement grain syntax, does not implement grain semantic storage, does not
change the semantic model, does not add semantic validation, does not add
diagnostics, and does not change IR, SQL, CLI, JSON, project, runtime, or
database behavior.

## Relationship To Earlier Phase 34 Slices

Slice 1 established the Phase 34 boundary: relationship grain and narrow JOIN
are future work, narrow JOIN is later-slice only, and no JOIN implementation is
approved.

Slice 2 established relationship grain as a compile-time metadata contract
around endpoint row identity and cardinality expectations. Relationship grain
prerequisites remain required future inputs before any narrow JOIN acceptance.

Slice 3 established the future narrow JOIN source-shape and semantic contract:
one explicit relationship metadata edge, explicit query opt-in, one base
relation plus one joined endpoint, deterministic endpoint qualification,
required grain facts, PostgreSQL/MySQL parity, and fail-closed behavior. Final
JOIN syntax is deferred and requires a later approved slice.

Slice 4 established parser and AST readiness boundaries. Final token spelling,
grammar productions, AST class names/fields, parser behavior, and accepted
syntax remain deferred.

Slice 5 preserves those boundaries. It records semantic readiness requirements
for later separately approved implementation slices and does not authorize
implementation.

## Current Relationship Semantic Model Baseline

The current relationship semantic model baseline is:

- `RelationshipSemanticEndpointInfo(local_name, relation_name, relation)`;
- `RelationshipSemanticInfo(name, endpoints)`;
- `SemanticModel.relationships: tuple[RelationshipSemanticInfo, ...] = ()`;
- endpoint `relation` is resolved `SourceDef | TableDef | QueryDef`;
- there is no endpoint grain;
- there is no relationship-edge grain;
- there are no relation identity/key facts;
- there is no cardinality/fanout posture;
- there is no endpoint role ownership;
- there is no JOIN scope owner;
- there is no backend lowering capability fact.

Relationship semantic facts remain read-only metadata. They do not enter
relation, type, callable, or field lookup. They are not lowered to IR or SQL.

## Current Relationship Validation Baseline

The current relationship validation baseline is limited to:

- `PIE-S2601`: unknown endpoint relation;
- `PIE-S2602`: duplicate relationship metadata name;
- `PIE-S2603`: duplicate endpoint local name within one relationship.

Valid relationship metadata is stored in source order. Invalid relationships do
not enter `SemanticModel.relationships`. Duplicate relationship scenarios
preserve earlier valid metadata facts when the earlier metadata was valid.
Self-relationship is currently allowed if endpoint local names are distinct.

Slice 5 adds no additional validation. It adds no relationship selection
validation, endpoint ownership validation, field ownership validation, grain
validation, fanout/cardinality validation, backend capability validation, or
narrow JOIN semantic validation.

Slice 5 adds no narrow JOIN semantic validation.

## Current Single-input Semantic / Field Lookup Baseline

The current relation semantic baseline remains single-input:

- `resolve_relation_inputs` resolves one `from_clause.source_name`;
- field inference uses the current single input qualifier;
- two-part dotted field references only bind when the qualifier is the current
  input qualifier;
- unrelated relation names and relationship names do not participate in
  qualifier lookup;
- projection aliases do not enter same-relation `where` or input-scope
  `order by`.

Future endpoint qualification and field ownership cannot be treated as a
trivial extension of current single-input lookup. They require an explicit
scope model before implementation.

## Future Semantic Prerequisites

Before any narrow JOIN semantic implementation is approved, a later slice must
define at least:

- selected relationship edge binding;
- base endpoint ownership;
- joined endpoint ownership;
- endpoint role disambiguation, including self-relationship;
- endpoint schema visibility for multi-owner fields;
- endpoint grain;
- pairwise relationship-edge grain;
- fanout/cardinality posture;
- supported/unsupported semantic subset marker;
- backend lowering capability proof;
- deterministic fail-closed diagnostics for unknown/unsafe/ambiguous facts.

These are future prerequisites only. Slice 5 does not add fields, classes,
semantic facts, validators, diagnostics, IR shape, or SQL lowering.

## Future Endpoint Ownership / Field Ownership / Qualification

A later implementation slice must decide which endpoint owns each visible
field. It must decide how qualified fields select endpoint owner. Duplicate
field names must fail closed or resolve deterministically.

Self-relationship must use endpoint-local names or another explicit mechanism
to disambiguate endpoint ownership. Future `where`, `select`, and `order by`
visibility must be specified before implementation.

Endpoint ownership, field ownership, endpoint qualification,
self-relationship disambiguation, and duplicate field owner behavior are
future-only in Slice 5.

## Diagnostics Readiness Boundary

Slice 5 adds no diagnostic code additions.

Future diagnostic families may be needed for relationship selection, endpoint
ownership, field ownership, missing grain, unknown grain, unsafe grain,
contradictory grain, unsupported fanout/cardinality, backend capability, and
ambiguous scope.

Adding actual diagnostic codes, messages, severities, spans, ordering, and JSON
presentation is deferred to later approved implementation slices.

Diagnostics can affect CLI JSON v1, Project JSON v2, Semantic Metadata
Artifact v1, and stability audits. Slice 5 therefore records diagnostics as
future families only and adds no new codes.

The only diagnostic codes documented by Slice 5 as current relationship
metadata behavior are the existing `PIE-S2601`, `PIE-S2602`, and `PIE-S2603`.

## IR / SQL / CLI / JSON / Project Preservation

`RelationIR` remains single-source. Slice 5 adds no SQL JOIN lowering and no
backend lowering behavior.

Slice 5 changes no fixtures or goldens. CLI JSON v1 is unchanged. Project JSON
v2 remains project check root/config-only. Project emit-sql and project
explain remain rejected. Single-file explain JSON remains Semantic Metadata
Artifact v1.

Slice 5 adds no CLI behavior, no JSON v1 behavior, no Project JSON v2 behavior,
no Semantic Metadata Artifact v1 behavior, no project behavior, no runtime
behavior, and no database behavior.

## Phase 33 Project / JSON Preservation

Slice 5 preserves Phase 33 project/JSON boundaries:

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

Slice 5 does not implement or authorize:

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
- grain semantic storage;
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

No package version change is made by Slice 5. Package version remains `0.1.0`.
No tag/release/publish/upload/signing/attestation is performed by Slice 5.

## Implementation Boundary

This spec does not change grammar, generated files, AST, parser behavior,
semantic model, semantic validation, diagnostics, IR, SQL, CLI, JSON, fixtures,
goldens, scripts, package metadata, dependencies, workflows, public API,
project behavior, runtime behavior, or database behavior.

This spec does not define final JOIN syntax, final grain syntax, final AST
fields, new diagnostic codes, IR shape, SQL join kind, SQL alias generation, or
SQL lowering.
