# Phase 50 - Post-v0.2 Semantic Readiness Consolidation

## Status

Phase 50 is an eleven-slice docs/spec/static-audit-only readiness consolidation
phase. It is planning and contract work, not implementation.

Phase 50 Slice 1 **Roadmap Reconciliation And Strategic Scope Lock** completed
at `85066d4a7088af82a308ca751763a4e6a10baa52`, with documented natural CI run
`29068556545` completing successfully for the exact commit.

Phase 50 Slice 2 **Post-v0.2 Deferred Inventory And Phase 50-60 Replan** is the
current docs/spec/static-audit-only documentation slice. Slice 2 is not
complete in Gate 2. Its completion and the effectiveness of its finalized
active planning route require a separately authorized Gate 3 commit, push, and
exact natural CI success. Slices 3 through 11 remain pending and separately
authorized. Phase 50 remains in progress.

Every Phase 50 slice is readiness-only. No slice automatically authorizes later
behavior or a later phase.

## Trusted Baseline

- Baseline branch: `main`.
- Baseline HEAD: `85066d4a7088af82a308ca751763a4e6a10baa52`.
- Baseline local `origin/main`:
  `85066d4a7088af82a308ca751763a4e6a10baa52`.
- Baseline subject: `Add Phase 50 readiness consolidation scope lock`.
- Documented natural CI run: `29068556545`, workflow/event `CI / push`,
  status/conclusion `completed / success`, with an exact `headSha` match.
- Package version remains `0.1.0`.
- No tag points at HEAD and there is no exact-match tag.

The CI facts above are repository-local documented evidence. Slice 2 Gate 2
does not perform network access or independently query GitHub.

## Phase Identity And Approved Direction

Phase 50 consolidates post-v0.2 readiness across:

- aggregate and grouped project output schema;
- type-system gaps and capability vocabulary;
- window-function readiness;
- import, module, and export readiness;
- semantic package model readiness;
- PostgreSQL extension capability readiness;
- multi-dialect capability ecosystem readiness; and
- explain, public metadata, package attribution, and lineage integration
  boundaries.

Pietto remains a typed SQL authoring DSL and semantic compiler. Phase 50
implements no compiler or runtime behavior. It adds no parser, AST, semantic,
IR, SQL, CLI, JSON, diagnostic, backend, package-resolution, registry,
runtime, database, or public-surface behavior.

Package and extension terminology is static, declarative, reviewable metadata
vocabulary only. It is not executable package code, plugin loading, dependency
resolution, registry access, installation, database discovery, or server state.

## Evidence Hierarchy And Historical Roadmap Rule

Phase 50 uses this evidence order:

1. completed phase completion audits and status locks;
2. current phase-specific plans and contracts;
3. the historical Phase 45-60 roadmap snapshot;
4. the historical v0.2 deferred register;
5. static-audit tests and phrase locks; and
6. current separately approved planning proposals.

The table in `docs/spec/pietto-roadmap-phase45-60-v1.md` is an immutable
Maintenance Phase 2 planning snapshot. Its exact Phase 50
`Import / Module / Export Readiness` row and exact Phase 60
`Completion Audit And Status Lock` row remain preserved. Active sequencing is
reconciled append-only below that snapshot; historical rows are not rewritten,
deleted, or retroactively reassigned.

`docs/spec/v02-deferred-feature-register-v1.md` remains an unchanged historical
v0.2 register in Slice 1. Slice 2 may add a separate post-v0.2 readiness
inventory, but it does not gain authority from Slice 1 automatically.

## Eleven-slice Route

Phase 50 uses exactly this eleven-slice route:

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

Slices 2 through 11 remain pending and separately authorized. Listing them is a
route lock, not implementation or completion.

## Cross-slice Gate Discipline

Every slice must:

- begin with its own read-only Gate 1 against the then-current trusted baseline;
- define an exact Gate 2 allowlist before any edit;
- remain limited to plans, specifications, contracts, matrices, and focused
  static-audit tests;
- stop if production code, grammar, generated artifacts, public schemas,
  fixtures, goldens, dependencies, workflows, or release surfaces appear
  necessary;
- preserve Phase 49 project row schema, origin/provenance, dependency graph,
  and lineage carriers as private unless a later phase explicitly authorizes a
  public contract;
- perform only the validation explicitly approved for that slice; and
- require separate Gate 3 authorization for any commit, push, or natural CI
  observation.

No Phase 50 slice authorizes runtime/database execution, database connections,
schema introspection, db pull, extension discovery, extension installation,
`CREATE EXTENSION`, connector-name inference, server guessing, credentials, or
network behavior.

## Slice 1 Roadmap Reconciliation And Strategic Scope Lock

- **Objective:** reconcile the historical roadmap, completed Phase 47-49
  handoffs, and the post-maintenance semantic package/capability direction into
  one Phase 50 readiness route.
- **Artifact type:** this phase plan, an append-only roadmap reconciliation, a
  Slice 1 scope contract, and one focused static-audit test.
- **Prerequisites:** completed Phase 49; completed Maintenance Phases 3 and 4;
  trusted baseline `6d898559aaa244f3e4643488c111480e6933761b`.
- **Completed-phase relationship:** preserves Phase 47-49 private row-schema,
  state, origin, dependency, and lineage foundations without consuming or
  exposing them.
- **Later handoff:** establishes Slices 2-11 and a tentative Phase 51-60 route;
  Slice 2 must finalize the post-v0.2 inventory and later ordering.
- **Explicit non-goals and no-behavior boundary:** no compiler, parser, AST,
  semantic, IR, SQL, CLI, JSON, diagnostic, backend, package manifest,
  resolver, catalog, registry, public schema, runtime, or database behavior.
- **Gate discipline:** Gate 2 is limited to the exact four-file Slice 1
  allowlist below. Any fifth repository path is a stop condition.

## Slice 2 Post-v0.2 Deferred Inventory And Phase 50-60 Replan

- **Objective:** classify implemented, private-foundation, readiness-only,
  deferred, and not-yet-evidenced work after v0.2 and finalize Phase 51-60
  ownership.
- **Artifact type:** the current inventory contract at
  `docs/spec/phase50-post-v02-deferred-readiness-inventory-v1.md`, an additive
  route update, and one focused static-audit test.
- **Prerequisites:** Slice 1 evidence hierarchy and historical-snapshot rule.
- **Completed-phase relationship:** reconciles Phase 29 through Phase 49 facts
  without rewriting their completion records.
- **Later handoff:** documents the finalized Phase 51-60 active planning
  sequence, which becomes effective only after Slice 2 Gate 3 succeeds.
- **Status vocabulary:** `IMPLEMENTED_STABLE`, `IMPLEMENTED_LIMITED`,
  `PRIVATE_FOUNDATION`, `READINESS_CONTRACT_ONLY`, `EXPLICITLY_DEFERRED`,
  `OUT_OF_SCOPE`, and `NOT_EVIDENCED`. These tokens are inventory-local and do
  not replace existing Semantic Metadata Artifact `support_posture` values.
- **Historical boundary:**
  `docs/spec/v02-deferred-feature-register-v1.md` remains byte-for-byte
  unchanged. The new inventory supersedes it only for current post-v0.2
  classification, not for historical Phase 29 meaning.
- **Explicit non-goals and no-behavior boundary:** no deferred-feature
  implementation and no compiler, parser, AST, semantic, IR, SQL, CLI, JSON,
  diagnostic, backend, package-resolution, extension, runtime, database, or
  public-surface behavior.
- **Gate discipline:** Slice 2 is not complete in Gate 2. Its exact four-file
  allowlist, focused validation, and stop conditions are recorded below. A
  separate Gate 3 is required before completion or route effectiveness.

## Slice 3 Aggregate / Grouped Project Output-Schema Readiness

- **Objective:** contract future project-private aggregate output fields,
  group-key result fields, aliases, duplicate handling, schema availability,
  origin, dependencies, and lineage.
- **Artifact type:** readiness contract, matrix, and static-audit test.
- **Prerequisites:** Phase 47 direct row schema, Phase 48 propagation states,
  Phase 49 row-expression/origin/dependency/lineage carriers, and Slice 2.
- **Completed-phase relationship:** reuses the completed private carrier
  vocabulary without changing existing single-file aggregate behavior.
- **Later handoff:** prepares Phase 51 Aggregate / Grouped Project Output-Schema
  Foundation.
- **Explicit non-goals and no-behavior boundary:** no aggregate widening,
  project row-schema implementation, public JSON, IR, SQL, CLI, or diagnostics.
- **Gate discipline:** separate Gate 1/Gate 2; no private carrier is consumed or
  widened merely because this readiness slice exists.

## Slice 4 Type-System Gap And Capability Readiness

- **Objective:** reconcile temporal, UUID, Enum, Decimal precision/scale,
  Any/Bytes/Json, domain/refinement, operator, nullability, and native database
  type gaps into capability prerequisites.
- **Artifact type:** type/capability readiness matrix and static-audit test.
- **Prerequisites:** Phase 30, Phase 36, Phase 41, Phase 42, and Slice 2
  contracts.
- **Completed-phase relationship:** preserves current supported, limited,
  metadata-only, private, and fail-closed type postures.
- **Later handoff:** prepares Phase 52 Core Type-System Capability Foundation
  and later capability profile work.
- **Explicit non-goals and no-behavior boundary:** no new type, literal, cast,
  operator, promotion, native metadata, SQL, or public schema behavior.
- **Gate discipline:** separate Gate 1/Gate 2 with no type-system implementation
  file implied by the matrix.

## Slice 5 Window-Function Readiness

- **Objective:** define the future decision surface for `OVER`, partitioning,
  window ordering, frames, ranking, offset/value functions, aggregate-as-window,
  result typing/nullability, grouped interaction, and dialect portability.
- **Artifact type:** window readiness and syntax-decision contract plus static
  audit.
- **Prerequisites:** Slices 3 and 4 and existing aggregate/dialect contracts.
- **Completed-phase relationship:** preserves the existing blanket window
  deferral and current grouped aggregate behavior.
- **Later handoff:** prepares Phase 53 Window Function Syntax And Capability
  Contract.
- **Explicit non-goals and no-behavior boundary:** no grammar, parser, AST,
  semantic, IR, SQL, function catalog, fixture, or golden change.
- **Gate discipline:** separate Gate 1/Gate 2; no syntax spelling is reserved by
  Slice 1.

## Slice 6 Import / Module / Export Readiness

- **Objective:** reconcile flat project namespaces with future module identity,
  imports, exports, visibility, qualified names, deterministic ordering, and
  cycle rules.
- **Artifact type:** import/module/export readiness contract and static audit.
- **Prerequisites:** Phase 45-49 project semantic foundations and Slice 2.
- **Completed-phase relationship:** preserves current cross-file flat namespace
  behavior and the historical Phase 50 roadmap row as planning history.
- **Later handoff:** prepares Phase 54 Import / Module / Export Readiness.
- **Explicit non-goals and no-behavior boundary:** no grammar, loader, resolver,
  executable import, filesystem discovery, network, or visibility behavior.
- **Gate discipline:** separate Gate 1/Gate 2; the historical row does not
  authorize implementation.

## Slice 7 Semantic Package Model Readiness

- **Objective:** define static semantic asset identity, attribution,
  dependency, ordering, versioning questions, and the non-executable safety
  model.
- **Artifact type:** semantic package model readiness contract and static audit.
- **Prerequisites:** Slices 4 and 6 and Phase 49 private lineage foundations.
- **Completed-phase relationship:** treats current project/source facts and
  private lineage as possible prerequisites, not package objects or public
  output.
- **Later handoff:** prepares Phase 55 Semantic Package Asset Schema.
- **Explicit non-goals and no-behavior boundary:** no manifest syntax, resolver,
  package graph implementation, dependency resolution, registry, lockfile,
  install, cache, publish, plugin, hook, or arbitrary code execution.
- **Gate discipline:** separate Gate 1/Gate 2; candidate asset categories do not
  become schemas automatically.

## Slice 8 PostgreSQL Extension Capability Readiness

- **Objective:** distinguish base PostgreSQL backend capability from static
  declared extension overlays and missing-capability failure.
- **Artifact type:** extension capability readiness contract and static audit.
- **Prerequisites:** Slices 4 and 7 and the Phase 9 closed backend capability
  precedent.
- **Completed-phase relationship:** preserves current PostgreSQL and private
  MySQL dispatch/lowering behavior unchanged.
- **Later handoff:** prepares Phase 57 PostgreSQL Extension Signature-Catalog
  Readiness.
- **Explicit non-goals and no-behavior boundary:** no PostGIS, pgvector,
  pg_trgm, or TimescaleDB signatures, types, operators, lowering, diagnostics,
  discovery, connection, installation, or `CREATE EXTENSION`.
- **Gate discipline:** separate Gate 1/Gate 2; named extensions remain examples
  until explicitly approved.

## Slice 9 Multi-dialect Capability Ecosystem Readiness

- **Objective:** distinguish dialect identity, backend support, semantic
  capability, extension overlay, portability, and unknown-target failure.
- **Artifact type:** multi-dialect capability ecosystem matrix and static audit.
- **Prerequisites:** Slices 4, 7, and 8 and existing PostgreSQL/MySQL contracts.
- **Completed-phase relationship:** keeps explicit closed PostgreSQL/MySQL
  dispatch and fail-closed backend diagnostics authoritative.
- **Later handoff:** prepares Phase 56 Capability Profile Static Schema And
  Declared Checking and the Phase 60 checkpoint.
- **Explicit non-goals and no-behavior boundary:** no new dialect, backend,
  connector, generic emitter, public registry, plugin discovery, or SQL output.
- **Gate discipline:** separate Gate 1/Gate 2; future dialect names are examples,
  not accepted CLI values.

## Slice 10 Explain / Public Metadata / Package Integration Boundary

- **Objective:** contract future project explain, portability reports, public
  lineage, capability diagnostics, Project JSON v2, and package attribution
  boundaries while preserving privacy.
- **Artifact type:** integration-boundary contract and static privacy audit.
- **Prerequisites:** Slices 3 and 7-9 and Phase 49 private-carrier privacy.
- **Completed-phase relationship:** preserves single-file explain and current
  Project JSON v2 while leaving project explain/public metadata deferred.
- **Later handoff:** prepares Phase 58 Project Explain / Portability / Public
  Metadata Readiness and Phase 59 Package Graph And Lineage / Provenance
  Integration.
- **Explicit non-goals and no-behavior boundary:** no serializer, CLI command,
  Project JSON v2 field, public lineage, portability report, or new diagnostic.
- **Gate discipline:** separate Gate 1/Gate 2; no private fact becomes public by
  being named as a future input.

## Slice 11 Completion Audit And Status Lock

- **Objective:** audit the completed Phase 50 readiness contracts for internal
  consistency and prove that no behavior was implemented.
- **Artifact type:** completion contract, plan status update, and static-audit
  test.
- **Prerequisites:** separately completed and published Slices 1 through 10.
- **Completed-phase relationship:** records readiness decisions without
  rewriting earlier phase history.
- **Later handoff:** freezes the finalized Phase 51-60 planning handoff for
  separate authorization.
- **Explicit non-goals and no-behavior boundary:** no implementation, public
  surface, package version, workflow, dependency, release, or runtime change.
- **Gate discipline:** separate Gate 1/Gate 2 and later Gate 3; Slice 11 cannot
  pre-claim its commit, push, CI, or Phase 50 completion.

## Tentative Phase 51-60 Active Planning Route

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

This sequence remains tentative until Slice 2 reconciles the post-v0.2 deferred
inventory and finalizes active ordering. It is not automatic
behavior authorization, and every later phase requires separate approval.

## Slice 2 Finalized Phase 51-60 Active Planning Route

Slice 2 preserves the Slice 1 tentative route above as completed historical
evidence and finalizes the same order for current planning:

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

This is the finalized active planning route: the current authoritative sequence
used to begin future read-only Gate 1 work only. It is active planning only and
becomes effective only after Slice 2 Gate 3 succeeds with the exact commit,
push, and natural CI result. It causes no automatic phase start or completion,
and it provides no implementation authorization, public API or release promise,
or runtime/database authorization. Every later phase requires separate
authorization. Stronger future evidence may supersede this sequence only
through an evidence-backed append-only replan that preserves historical rows.

Phase 51 is first because it consumes the strongest Phase 47-49 private-carrier
handoff. It is limited to private aggregate/grouped project schema foundation
using currently implemented canonical expression types and introduces no new
scalar type or type semantics. Phase 52 owns later type/capability foundations.
Phase 53 remains readiness-only. Phase 54 rehomes the historical import/module/
export direction. Phase 55 defines static asset schema before package graph
behavior. Phase 56 defines capability schema before extension catalogs. Phase
57 is catalog readiness, not extension lowering. Phase 58 remains readiness and
privacy-contract work. Phase 59 keeps integration private before public export.
Phase 60 is a checkpoint, not a release or backend implementation phase.

## Protected And Forbidden Surfaces

Slice 1 must not change:

- `README.md` or `AGENTS.md`;
- `docs/spec/pietto-v0.9.md`;
- `docs/spec/v02-deferred-feature-register-v1.md`;
- any completed Phase 47-49 artifact;
- `src/**`, `grammar/**`, or generated parser artifacts;
- `scripts/**` or `.github/**`;
- `pyproject.toml`, `uv.lock`, dependencies, or package metadata;
- fixtures, goldens, examples, or public schemas; or
- package version, tag, release, publish, upload, signing, or attestation
  surfaces.

Slice 2 preserves every surface above and additionally keeps the completed
Slice 1 scope spec/test and every completed Phase 30-49 artifact unchanged.
No `src/**`, grammar/generated, script, workflow, dependency, package metadata,
fixture, golden, example, public schema, or release surface is approved.

## Package, Version, And Release Boundary

Package version remains `0.1.0`. Slice 1 performed no package version change,
tag, release, publish, upload, signing, or attestation. Slice 2 Gate 2 performs
no package version change, tag, release, publish, upload, signing, attestation,
CI trigger, CI rerun, CI watch, or CI cancellation. Gate 2 must not prepare
Gate 3.

## Slice 1 Gate 2 Allowlist

Phase 50 Slice 1 Gate 2 is limited to exactly:

- `docs/spec/pietto-roadmap-phase45-60-v1.md`;
- `docs/plan/phase-50-semantic-readiness-consolidation.md`;
- `docs/spec/phase50-semantic-package-extension-capability-scope-lock-v1.md`;
- `tests/test_phase50_semantic_package_extension_capability_scope_lock.py`.

No other repository path is approved.

## Slice 1 Focused Validation

Slice 1 Gate 2 validation is limited to:

- exact dirty-set and four-file diff inspection;
- tracked and untracked whitespace checks;
- Ruff format/check and lint for the changed test;
- test-project Pyright;
- the focused Slice 1 static test;
- selected dirty-tree-safe historical roadmap, deferred-register, and Phase
  47-49 handoff test nodes;
- protected-surface, version, and tag checks; and
- a new `/tmp/phase50-slice1-gate2-evidence-and-diff.txt` evidence packet.

Do not overwrite `/tmp/phase50-gate2-evidence-and-diff.txt`. Do not run full
pytest, `scripts/validate.py`, generated checks, golden checks, package smoke,
builds, benchmarks, network commands, GitHub CLI, or CI in Slice 1 Gate 2.

## Slice 2 Gate 2 Allowlist

Phase 50 Slice 2 Gate 2 is limited to exactly:

- `docs/plan/phase-50-semantic-readiness-consolidation.md`;
- `docs/spec/pietto-roadmap-phase45-60-v1.md`;
- `docs/spec/phase50-post-v02-deferred-readiness-inventory-v1.md`;
- `tests/test_phase50_post_v02_deferred_readiness_inventory.py`.

No fifth repository path is approved. Nothing may be staged, committed, or
pushed in Gate 2.

## Slice 2 Focused Validation

Slice 2 Gate 2 validation is limited to:

- exact dirty-set and four-file diff inspection;
- tracked and no-index whitespace checks;
- Ruff format/check and lint for the new focused test only;
- test-project Pyright;
- the focused Slice 2 static test;
- the historical Phase 29 register test and selected dirty-tree-safe Slice 1
  compatibility nodes;
- the explicitly approved Phase 30-49 evidence nodes;
- historical-register byte comparison against the Slice 1 baseline;
- protected-surface, version, and tag checks; and
- `/tmp/phase50-slice2-gate2-evidence-and-diff.txt` with complete diffs.

Do not run full pytest, `scripts/validate.py`, generated checks, golden checks,
package smoke, builds, benchmarks, dependency operations, network commands,
GitHub CLI, or CI. Once formatting starts, a failure is a stop condition and
does not authorize repair.

## Slice 2 Stop Conditions

Stop without repair or scope expansion if:

- the Slice 1 baseline or exact four-file dirty set differs;
- any fifth repository path changes;
- the historical Phase 29 register, completed Slice 1 scope spec/test, or any
  protected production/public/release surface changes;
- a table row cannot use exactly one inventory status token;
- a private foundation is described as public behavior;
- readiness wording implies implementation or a later phase start;
- Slice 2 or the finalized route is called complete/effective before Gate 3;
- a no-index check emits a whitespace diagnostic; or
- Ruff, Pyright, focused pytest, compatibility pytest, or an evidence node
  fails.

## Stop Conditions

Stop without repair or scope expansion if:

- the baseline or exact four-file dirty set differs;
- any fifth repository path changes;
- the historical roadmap table or v0.2 register requires modification;
- any production/public/release surface appears necessary;
- a no-index check emits a whitespace diagnostic;
- Ruff, Pyright, focused pytest, or compatibility pytest fails; or
- the final diff cannot prove the Slice 1 no-behavior boundary.
