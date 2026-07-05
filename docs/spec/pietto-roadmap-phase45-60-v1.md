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
