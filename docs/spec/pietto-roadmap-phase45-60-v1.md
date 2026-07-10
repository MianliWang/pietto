# Pietto Roadmap Phase 45-60 v1

## Status And Guardrail

Maintenance Phase 2 Slice 2 locks the Phase 45-60 roadmap direction as
docs/spec/static-audit work only. It authorizes no source/compiler behavior,
grammar, generated ANTLR, parser, AST, semantic implementation, IR, SQL,
CLI, JSON v1, Project JSON v2, Semantic Metadata Artifact v1, diagnostic
shape, fixture/golden, script, workflow, dependency, package metadata,
package version, release, tag, publish, upload, signing, or attestation
change.

Package version remains `0.1.0`.

Phase 45 is `Project-wide Semantic Model Design And MVP`. A true
project-wide semantic model is mandatory, not optional. Phase 45 must not be
reduced to per-file semantic aggregation only.

## Roadmap Tree

The Phase 45-60 roadmap is a planning tree, not authorization to implement
all listed behavior in one pass. A phase may use up to 12 slices when needed.
Each behavior slice still requires its own bounded Gate 1 and Gate 2 approval.

| Phase | Direction | Locked intent |
| --- | --- | --- |
| 45 | Project-wide Semantic Model Design And MVP | build the first true project-wide semantic catalog/model across selected project files |
| 46 | Project Semantic Diagnostics And Recovery | stabilize duplicate, unresolved, ambiguous, and cascade diagnostics for project analysis |
| 47 | Project Semantic Metadata Artifact | expose project-wide semantic facts through a bounded metadata artifact without changing single-file output contracts |
| 48 | Project IR Readiness | design how project semantic facts feed future IR without adding project SQL lowering by accident |
| 49 | Project SQL Emission Readiness | prepare explicit `emit-sql --project` semantics, output ownership, and fail-closed unsupported cases |
| 50 | Import / Module / Export Readiness | design Python-like import/export direction before any import/module behavior is implemented |
| 51 | Project Visibility And Ambiguity Policy | refine visibility, ambiguous references, warnings, and strict-mode errors |
| 52 | Relationship / JOIN Semantic Readiness | reconnect relationship metadata with true project semantic facts before querying behavior |
| 53 | Grain And Fanout Safety Readiness | design grain, fanout, and aggregate safety rules before JOIN SQL expansion |
| 54 | Relationship Query MVP Candidate | evaluate the first narrow relationship-aware query behavior after readiness is complete |
| 55 | Project Explain Aggregation MVP | aggregate semantic metadata and explain output across a validated project model |
| 56 | Project SQL Compatibility Hardening | lock PostgreSQL/private MySQL portability for approved project SQL surfaces |
| 57 | Project Diagnostics / CLI / JSON Compatibility | harden CLI text, Project JSON v2, and metadata compatibility around project behavior |
| 58 | Docs / Examples / Package Smoke Readiness | verify examples, docs, package smoke, and validation entrypoints for project-mode surfaces |
| 59 | Public Surface Freeze And Release Readiness | lock package/release prerequisites without performing release operations |
| 60 | Completion Audit And Status Lock | complete the roadmap tranche with static audit and status proof only |

## Phase 45 Project-wide Semantic Model

Phase 45 targets a true project-wide semantic model. The minimum useful MVP
must analyze all selected, parsed project inputs as one project compile unit
before accepting project-level semantic success.

The model must be more than per-file semantic aggregation. It must own:

- one deterministic project catalog over selected top-level definitions;
- cross-file reference resolution over accepted project symbols;
- duplicate and ambiguous-name handling across selected files;
- deterministic source ordering and source-span ownership;
- project-level success/failure state that blocks later project IR/SQL when
  semantic analysis fails;
- compatibility boundaries for single-file semantic behavior.

Phase 45 does not by itself authorize project SQL emission, relationship/JOIN
querying, import/export syntax, module semantics, package visibility, database
execution, or runtime behavior.

## Namespace Preference

Pietto should use a hybrid namespace preference for project-wide semantics.

The type namespace includes:

- `shape`;
- future type aliases;
- future domain types.

The relation namespace includes:

- `source`;
- `table`;
- `query`.

Cross-file references should allow any selected project top-level symbol,
subject to the symbol's namespace and the current language rules for that
reference site.

The file/module model is not final. Phase 45 may use an implicit project
package model as an MVP stepping stone, but Python-like import/export remains
a required long-term target. Imports, modules, exports, aliases, visibility
rules, and qualified names require readiness work before behavior
implementation.

## Ambiguity And Same-name Policy

The long-term preference for same-name `source`, `table`, and `query`
definitions is:

- non-strict mode may report a warning when a same-name relation declaration
  is accepted by a future compatibility policy;
- strict mode should report an error;
- unqualified ambiguous references must fail closed.

Current fail-closed behavior may remain until warning infrastructure,
strict-mode policy, and ambiguity diagnostics are explicitly approved.

## Language Precedent Policy

Python, Go, Rust, and C++ namespace and module precedents are design context,
not implementation authority. Pietto should compare them to clarify tradeoffs:

- Python supports package/module import ergonomics but should not force Pietto
  to add executable import behavior;
- Go favors explicit package boundaries but should not force directory names
  into Pietto language semantics;
- Rust separates module visibility and name resolution but should not make
  Pietto adopt a large visibility system early;
- C++ demonstrates the risk of complex namespace and lookup rules that Pietto
  should avoid.

Pietto should keep the language readable, fail closed on unsupported or
ambiguous cases, and defer import/module/export behavior until readiness is
locked.

## Malloy And Cube Borrowing Policy

Malloy and Cube may be studied for concepts, but they must not be copied as
frameworks or treated as behavior contracts.

Useful concept areas include:

- semantic modeling units;
- reusable measures and dimensions;
- relationship and join modeling;
- project-level model organization;
- metadata and documentation output.

Pietto must keep its own Python-style indentation language, semantic SQL
authoring focus, compiler pipeline, explicit dialect posture, and fail-closed
unsupported behavior.

## Release Posture

This roadmap document performs no release operation. Maintenance Phase 2 Slice
2 authorizes no package version change, tag, release, publish, upload, signing,
or attestation.

## Post-maintenance Phase 50 Reconciliation

### Historical Maintenance Phase 2 Snapshot

The Roadmap Tree above remains a historical Maintenance Phase 2 roadmap
snapshot. Its historical Phase 50 row,
`Import / Module / Export Readiness`, is preserved as planning history.
That label remains historical, superseded for active sequencing, and deferred.
It is not behavior authorization. The historical table, including its exact
Phase 50 and Phase 60 rows, is retained as evidence and is not deleted,
retroactively rewritten, or reassigned.

Phase 47 through Phase 49 later phase-specific planning treated the old
roadmap table as historical/superseded for active sequencing.

### Current Phase 50 Readiness-Consolidation Route

Phase 50 now reconciles the roadmap after completed Phase 49 and completed
Maintenance Phases 3-4. The authoritative current Phase 50 route is:

`Phase 50 - Post-v0.2 Semantic Readiness Consolidation`

Phase 50 is an eleven-slice docs/spec/static-audit-only readiness consolidation
phase. It defines plans, contracts, matrices, vocabulary, ordering, safety
boundaries, and explicit non-goals only. Phase 50 implements no compiler or
runtime behavior. Every slice requires separate authorization and no slice
automatically authorizes later implementation.

Pietto remains a typed SQL authoring DSL and semantic compiler.

### Current Slice 1 Purpose

Phase 50 Slice 1 is `Roadmap Reconciliation And Strategic Scope Lock`. It is
only the entry documentation slice for the wider Phase 50 route. Slice 1 locks
the roadmap relationship, semantic package and capability vocabulary, safety
boundaries, and later slice ownership. Slices 2 through 11 remain pending and
separately authorized.

The earlier aggregate/grouped project output-schema candidate remains deferred
to Slice 3 readiness and tentative Phase 51 foundation work.
Import/module/export behavior remains deferred to Slice 6 readiness and
tentative Phase 54 planning. project explain/public metadata remains deferred
to Slice 10 boundary work and tentative Phase 58 readiness. Public
lineage/export, project IR/SQL, JOIN/relationship/grain/fanout, and
runtime/database work remain deferred. None of these planning assignments
implements behavior in Slice 1.

### Eleven-slice Phase 50 Plan

The dedicated plan is
`docs/plan/phase-50-semantic-readiness-consolidation.md`. It locks exactly:

1. Roadmap Reconciliation And Strategic Scope Lock
2. Post-v0.2 Deferred Inventory And Phase 50-60 Replan
3. Aggregate / Grouped Project Output-Schema Readiness
4. Type-System Gap And Capability Readiness
5. Window-Function Readiness
6. Import / Module / Export Readiness
7. Semantic Package Model Readiness
8. PostgreSQL Extension Capability Readiness
9. Multi-dialect Capability Ecosystem Readiness
10. Explain / Public Metadata / Package Integration Boundary
11. Completion Audit And Status Lock

Only Slice 1 is the current documentation slice. Listing Slices 2 through 11
does not start or complete them.

### Tentative Phase 51-60 Active Planning Route

The current planning-only sequence is:

- Phase 51: Aggregate / Grouped Project Output-Schema Foundation
- Phase 52: Core Type-System Capability Foundation
- Phase 53: Window Function Syntax And Capability Contract
- Phase 54: Import / Module / Export Readiness
- Phase 55: Semantic Package Asset Schema
- Phase 56: Capability Profile Static Schema And Declared Checking
- Phase 57: PostgreSQL Extension Signature-Catalog Readiness
- Phase 58: Project Explain / Portability / Public Metadata Readiness
- Phase 59: Package Graph And Lineage / Provenance Integration
- Phase 60: Multi-dialect Capability Ecosystem Completion Checkpoint

This route remains tentative until Slice 2 reconciles the post-v0.2 deferred
inventory and finalizes active ordering. It is not automatic behavior
authorization, and every later phase requires separate approval.

### Strategic Vocabulary And Safety Boundary

The current strategic vocabulary is:

- A semantic package is a static, declarative, reviewable bundle of semantic
  assets. It is not an executable package or runtime service.
- A dialect is a SQL syntax/lowering family.
- A capability profile declares the semantic abilities of a compilation
  target.
- A PostgreSQL extension capability profile is a static declared overlay on a
  PostgreSQL base capability profile.
- A missing or undeclared capability must fail closed. There is no
  best-effort lowering or implicit fallback.

Slice 1 authorizes no package manifest, resolver, dependency solver, package
graph, catalog, signature schema, lowering, diagnostic, public schema, CLI or
JSON surface, auto-install, `CREATE EXTENSION`, database or schema
introspection, arbitrary package code execution, plugin, hook, network, or
registry behavior. Phase 49 private carriers remain private and are not
consumed or exposed. Concrete extension signatures and lowering remain later,
separately approved work.
