# Phase 34 Re-scope / Completion Candidate Decision v1

## Purpose

This specification records the Phase 34 Slice 7 re-scope / completion candidate
decision.

Slice 7 is docs/spec/static-audit/status-only work. It defines how Phase 34 can
later complete as a conservative relationship grain and narrow JOIN
readiness/contracts foundation, not as a behavior MVP. It also preserves the
implementation deferral locked by Slice 1 through Slice 6.

This document does not complete Phase 34 yet. A later completion audit/status
lock slice may complete Phase 34 if separately approved.

## Relationship To Earlier Phase 34 Slices

Slice 1 established the Phase 34 boundary: relationship grain and narrow JOIN
are future work, narrow JOIN is later-slice only, and no JOIN implementation is
approved.

Slice 2 established relationship grain as a compile-time metadata contract
around endpoint row identity and cardinality expectations. It did not implement
grain syntax, grain semantic storage, or JOIN behavior.

Slice 3 established the future narrow JOIN source-shape and semantic contract:
one explicit relationship metadata edge, explicit query opt-in, one base
relation plus one joined endpoint, deterministic endpoint qualification,
required grain facts, PostgreSQL/MySQL parity, and fail-closed behavior. Final
JOIN syntax remains deferred.

Slice 4 established parser and AST readiness boundaries. Final token spelling,
grammar productions, AST class names/fields, parser behavior, and accepted
syntax remain deferred.

Slice 5 established semantic readiness boundaries. Future semantic work must
define relationship selection, endpoint ownership, field ownership, grain
requirements, unsupported fanout/cardinality behavior, backend capability
handling, and deterministic fail-closed diagnostics before implementation.

Slice 6 established the first implementation candidate decision: actual narrow
JOIN parser/AST implementation is not approved yet. No safe implementation
path exists after Slice 6 because final syntax/AST shape remains deferred and
parser acceptance would require semantic fail-closed behavior that is not
approved.

Slice 7 preserves those boundaries and re-scopes future completion language.

## Slice 1 Through Slice 6 Delivery Summary

Phase 34 Slice 1 delivered the master plan, candidate decision,
relationship/grain/JOIN boundary, Phase 33 handoff audit, and focused static
tests.

Phase 34 Slice 2 delivered the relationship grain contract vocabulary and
future acceptance prerequisites.

Phase 34 Slice 3 delivered the narrow JOIN source-shape and semantic contract
for future work.

Phase 34 Slice 4 delivered parser/AST readiness requirements without accepted
syntax.

Phase 34 Slice 5 delivered semantic readiness requirements without semantic
model changes, validation, diagnostics, IR, or SQL.

Phase 34 Slice 6 delivered the first implementation candidate decision and
decided that actual parser/AST implementation is not approved yet.

Together, Slice 1 through Slice 6 delivered a readiness/contracts foundation,
not implemented JOIN or grain behavior.

## Re-scope Candidate Decision

Phase 34 should be completed later as a relationship grain and narrow JOIN
readiness/contracts foundation. Phase 34 should not claim implemented JOIN or
grain behavior.

The original behavior MVP remains future implementation deferred. Actual
implementation remains deferred because Slice 6 found no safe parser/AST
implementation path.

Actual relationship grain syntax, JOIN syntax, parser/AST behavior, semantic
validation, IR/SQL lowering, CLI/JSON/project behavior, runtime/database
behavior, and release operations remain deferred to later separately approved
phases/slices.

Least misleading completion statement:

```text
Phase 34 Relationship Grain And Narrow JOIN readiness foundation is complete as docs/spec/static-audit/status-only work. The original behavior MVP remains future implementation deferred.
```

Slice 7 does not complete Phase 34 yet.

## Expected Later Completion Audit Scope

A later completion audit/status lock slice may verify:

- all Slice 1 through Slice 7 docs/spec/tests;
- no compiler behavior changed;
- forbidden surfaces remain untouched;
- package version remains `0.1.0`;
- no tag/release/publish/upload/signing/attestation occurred;
- stale README, AGENTS, or `docs/spec/pietto-v0.9.md` status is documented only
  if separately approved.

README, AGENTS, and `docs/spec/pietto-v0.9.md` updates are deferred unless
separately approved.

## Current Behavior Preservation

Unsupported join-like syntax remains unsupported. Relationship metadata remains
metadata-only. Relationship metadata is not lowered to Semantic IR or SQL.

Current single-input relation behavior remains unchanged. `RelationIR` remains
single-source. PostgreSQL/MySQL render one `FROM` input.

CLI JSON v1 is unchanged. Project JSON v2 is unchanged. Semantic Metadata
Artifact v1 is unchanged.

## Phase 33 Project / JSON Preservation

Slice 7 preserves Phase 33 project/JSON boundaries:

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
- single-file `pietto explain --format json` remains Semantic Metadata Artifact
  v1.

## Explicit Deferred Implementation Surfaces

The following surfaces remain deferred:

- actual relationship grain syntax;
- JOIN syntax;
- parser behavior;
- AST nodes;
- semantic model changes;
- semantic validation;
- diagnostic codes;
- IR/SQL lowering;
- CLI/JSON/project behavior;
- runtime/database behavior;
- relationship graph traversal;
- relationship chaining;
- automatic join inference;
- DB introspection/schema pull;
- graph/ERD/AI metadata export.

## Explicit Non-goals

Slice 7 does not implement or authorize:

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
- package metadata/dependency/workflow changes;
- JOIN implementation;
- JOIN syntax implementation;
- grain syntax implementation;
- grain semantic storage;
- release/tag/publish/upload/signing/attestation.

## Implementation Boundary

This spec does not change grammar, generated files, AST, parser behavior,
semantic model, semantic validation, diagnostics, IR, SQL, CLI, JSON, fixtures,
goldens, scripts, package metadata, dependencies, workflows, public API,
project behavior, runtime behavior, or database behavior.

This spec does not define final JOIN syntax, final grain syntax, final AST
fields/classes, diagnostic codes, IR shape, or SQL lowering.
