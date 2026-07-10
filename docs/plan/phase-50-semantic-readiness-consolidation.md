# Phase 50 - Post-v0.2 Semantic Readiness Consolidation

## Status

Phase 50 is an eleven-slice docs/spec/static-audit-only readiness consolidation
phase. It is planning and contract work, not implementation.

Phase 50 Slice 1 **Roadmap Reconciliation And Strategic Scope Lock** completed
at `85066d4a7088af82a308ca751763a4e6a10baa52`, with documented natural CI run
`29068556545` completing successfully for the exact commit.

Phase 50 Slice 2 **Post-v0.2 Deferred Inventory And Phase 50-60 Replan**
completed through original inventory commit
`d35ed9a58d3fc4b81febbea8fa3540707cbcfde0`, additive repair commit
`5c66b00d20200d943f0b6e1d0c02813fba18904b`, and documented natural recovery
CI run `29072890119` completing successfully for the exact repair commit. Its
finalized Phase 51-60 route is now effective as active planning only.

Phase 50 Slice 3 **Aggregate / Grouped Project Output-Schema Readiness**
completed at `7bd50022859a5e3d202c26d67bed1a723388048a`, with documented
natural CI run `29082580976` completing successfully for the exact commit.

Phase 50 Slice 4 **Type-System Gap And Capability Readiness** is the current
docs/spec/static-audit-only readiness slice. Slice 4 is not complete in Gate 2.
Its completion requires a separately authorized Gate 3 commit, push, and exact
natural CI success. Slices 5 through 11 remain pending and separately
authorized. Phase 50 remains in progress. Phase 51 and Phase 52 remain
unstarted.

Every Phase 50 slice is readiness-only. No slice automatically authorizes later
behavior or a later phase.

## Trusted Baseline

- Baseline branch: `main`.
- Baseline HEAD: `7bd50022859a5e3d202c26d67bed1a723388048a`.
- Baseline local `origin/main`:
  `7bd50022859a5e3d202c26d67bed1a723388048a`.
- Baseline subject: `Add Phase 50 aggregate grouped schema readiness`.
- Baseline parent/Slice 2 repair commit:
  `5c66b00d20200d943f0b6e1d0c02813fba18904b`.
- Documented natural Slice 3 CI run: `29082580976`, workflow/event `CI / push`,
  status/conclusion `completed / success`, with an exact `headSha` match.
- Package version remains `0.1.0`.
- No tag points at HEAD and there is no exact-match tag.

The CI facts above are repository-local documented evidence. Slice 4 Gate 2
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
v0.2 register. Slice 2 added a separate post-v0.2 readiness inventory after its
own authorization; that inventory does not rewrite historical Phase 29 meaning.

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

Slices 1 through 3 are complete. Slice 4 is current but incomplete. Slices 5
through 11 remain pending and separately authorized. Listing them is a route
lock, not implementation or completion.

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
  sequence, which became effective as planning-only direction after the
  successful Slice 2 repair Gate 3 and exact natural CI result.
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
- **Gate discipline:** the historical Slice 2 Gate 2 used the exact four-file
  allowlist, focused validation, and stop conditions recorded below. Slice 2
  later completed only through its separately authorized original Gate 3 and
  additive repair gates.

## Slice 3 Aggregate / Grouped Project Output-Schema Readiness

- **Objective:** contract future project-private aggregate output fields,
  group-key result fields, aliases, duplicate handling, schema availability,
  origin, dependencies, and lineage.
- **Artifact type:** the readiness contract at
  `docs/spec/phase50-aggregate-grouped-project-output-schema-readiness-v1.md`,
  decision matrices, and one focused static-audit test.
- **Prerequisites:** Phase 47 direct row schema, Phase 48 propagation states,
  Phase 49 row-expression/origin/dependency/lineage carriers, and Slice 2.
- **Completed-phase relationship:** reuses the completed private carrier
  vocabulary without changing existing single-file aggregate behavior.
- **Later handoff:** prepares Phase 51 Aggregate / Grouped Project Output-Schema
  Foundation as a future separately authorized private implementation phase.
- **Result-domain decision:** future source-ordered selected outputs keep their
  selected identity, current canonical type/nullability, immediate private
  provenance, and an orthogonal private `GROUP_KEY` or `AGGREGATE_RESULT`
  result role. No public schema or production class name is designed here.
- **Origin/provenance decision:** selected group keys preserve current direct
  projection provenance; aggregate results use the existing private
  `AGGREGATE` origin vocabulary. Let/expression structure belongs to future
  dependency/lineage facts rather than new provenance subtypes.
- **Availability decision:** future work reuses exactly `CONCRETE`, `UNKNOWN`,
  `DEFERRED`, and `BLOCKED`. Duplicate selected output names remain private
  `UNKNOWN / DUPLICATE_OUTPUT_NAME`; Slice 3 adds no diagnostic.
- **Clause and qualification decision:** `satisfying:` and grouped `order by:`
  consume result-domain facts without changing output schema; static `limit`
  has no field dependency. Downstream resolution remains flat: bare selected
  output or the immediate upstream relation qualifier only.
- **Bounded Phase 51 handoff:** current accepted aggregate/grouped forms and
  current canonical expression types only; bounded private result role,
  provenance, aggregate-argument dependency/lineage, and concrete downstream
  propagation only. Phase 51 remains unstarted.
- **Explicit non-goals and no-behavior boundary:** no aggregate widening,
  project row-schema implementation, public JSON, IR, SQL, CLI, or diagnostics.
- **Gate discipline:** Slice 3 completed only after its separately authorized
  Gate 3 commit, push, and exact natural CI success. No private carrier was
  consumed or widened merely because this readiness slice completed.

## Slice 4 Type-System Gap And Capability Readiness

- **Objective:** reconcile temporal, UUID, Enum, Decimal precision/scale,
  Any/Bytes/Json, alias/domain/refinement, operator/type-pair, aggregate,
  nullability, IR/backend, and native database type gaps into exact capability
  prerequisites.
- **Artifact type:** this plan update, the readiness contract at
  `docs/spec/phase50-type-system-gap-capability-readiness-v1.md`, layered
  decision matrices, one focused static-audit test, and three narrow Phase 50
  compatibility updates.
- **Prerequisites:** completed Phase 30, Phase 36, Phase 41, Phase 42, Phase
  47-49 private row facts, Slice 2 inventory, and completed Slice 3.
- **Completed-phase relationship:** preserves the exact 11-name builtin
  registry (`Any`, `Bool`, `Bytes`, `Date`, `Decimal`, `Float`, `Int`, `Json`,
  `Text`, `Timestamp`, `UUID`), declaration-backed non-builtin Enum, declared
  and canonical alias identity, shape definitions, unknown sentinels, current
  operation/aggregate behavior, and private project/type facts.
- **Layered-support decision:** identity/resolution, declaration, literal,
  projection/reference, operator/scalar-function, aggregate, semantic/IR,
  private project, public metadata, backend expression lowering, and native
  mapping are independent. A resolving type is not globally implemented.
- **Capability-dimension decision:** readiness uses exactly 19 orthogonal
  dimensions: identity/classification; declaration/resolution; literal
  construction; cast/coercion; projection/reference; null-check behavior;
  equality/comparison; ordering/grouping; arithmetic; scalar function;
  aggregate argument; aggregate result; general nullability propagation;
  window readiness; private project representation; IR representability;
  backend expression lowering; public metadata posture; and native database
  mapping.
- **Fail-closed decision:** missing or conflicting capability evidence fails
  closed. Type identity does not imply operation support, backend expression
  success does not imply native storage support, and no universal
  `supports_type` boolean is designed.
- **Decimal decision:** logical Decimal behavior, private validated
  `Decimal(p,s)`/direct-field facts, and absent computed/aggregate/public/IR/SQL
  precision guarantees remain distinct. No fusion, overflow, rounding, or
  backend-native formula is promised.
- **Temporal decision:** Date and Timestamp keep current bounded projection,
  generic comparison, count/count_distinct, and min/max surfaces. DateTime,
  Time, Interval, typed temporal literals, arithmetic, timezone, precision,
  interval algebra, and native mapping remain unsupported or deferred.
- **Boundary-type decision:** UUID remains `limited_frozen`; Enum remains
  declaration-backed `metadata_only` and non-builtin; Bytes and Json remain
  `deferred_builtin` with bounded direct-count behavior; Any is not runtime
  dynamic typing. Existing public `support_posture` vocabulary is unchanged.
- **Alias/domain decision:** aliases preserve declared and canonical identity;
  canonical expansion does not grant every operation. Parsed `ensure` is not a
  domain system. Domains, refinements, Money/Currency/units, native domains,
  validation execution, and coercion behavior remain outside the active route
  absent replan.
- **Native-mapping decision:** semantic identity, IR representability, backend
  expression lowering, and native physical mapping are separate. No DDL/type
  catalog, introspection, db pull, driver conversion, storage precision,
  collation, timezone, extension discovery, or runtime conversion is added.
- **Bounded Phase 52 handoff:** a later separately authorized Phase 52 may start
  with private immutable deterministic current-behavior-only capability facts
  and fail-closed lookup. It may not add a builtin, syntax, literal, cast,
  operator, Decimal fusion, UUID/Enum widening, native mapping, public metadata,
  CLI/JSON, package/extension schema, backend, runtime, database, or release
  behavior. Phase 52 remains unstarted and its slices are not finalized here.
- **Explicit non-goals and no-behavior boundary:** Slice 4 implements no
  compiler or runtime behavior. It adds no type, literal, cast, operator,
  promotion, aggregate behavior, nullability behavior, production capability
  carrier/API, native metadata, SQL, public schema, package version, or release
  behavior.
- **Gate discipline:** Slice 4 is not complete in Gate 2. It uses the exact
  six-file allowlist and focused validation below. Completion requires a
  separately authorized Gate 3 commit, push, and exact natural CI success.

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

The Slice 1 tentative planning-only sequence was:

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

This sequence remained tentative until Slice 2 reconciled the post-v0.2
deferred inventory and finalized active ordering. This section is preserved as
historical Slice 1 planning evidence. It is not automatic behavior authorization,
and every later phase still requires separate approval.

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
used to begin future read-only Gate 1 work only. It became effective as active
planning after Slice 2's original commit, additive repair commit, and exact
natural recovery CI success. It causes no automatic phase start or completion,
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

Slice 3 preserves every production, public, historical, and release surface
above. Its only existing-file compatibility changes are the Phase 50 Slice 1
and Slice 2 static tests named in the exact Slice 3 allowlist. Their historical
locks remain intact.

Slice 4 preserves every surface above, the roadmap, all completed Slice 1-3
specs, the historical Phase 29 register, and every production/public/release
surface. Its only existing-file compatibility changes are the three Phase 50
tests named in the exact Slice 4 allowlist, limited to current status and exact
dirty-set compatibility while preserving their historical locks.

## Package, Version, And Release Boundary

Package version remains `0.1.0`. Slices 1 through 3 performed no package
version change, tag, release, publish, upload, signing, or attestation. Slice 4
Gate 2 performs no package version change, tag, release, publish, upload,
signing, attestation, CI trigger, CI rerun, CI watch, or CI cancellation. Gate
2 does not stage, commit, push, or prepare Gate 3.

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

## Slice 3 Gate 2 Allowlist

Phase 50 Slice 3 Gate 2 is limited to exactly:

- `docs/plan/phase-50-semantic-readiness-consolidation.md`;
- `docs/spec/phase50-aggregate-grouped-project-output-schema-readiness-v1.md`;
- `tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py`;
- `tests/test_phase50_semantic_package_extension_capability_scope_lock.py`;
- `tests/test_phase50_post_v02_deferred_readiness_inventory.py`.

The final two paths are approved only for narrow mutable-current status and
exact dirty-set compatibility. No sixth repository path is approved. Nothing
may be staged, committed, pushed, or operated through CI in Gate 2.

## Slice 3 Focused Validation

Slice 3 Gate 2 validation is limited to:

- exact baseline, five-file dirty-set, cached-diff, and whitespace checks;
- no-index whitespace checks for the two new files;
- Ruff format/check and lint for all three changed Python tests;
- test-project Pyright;
- complete execution of the Slice 1, Slice 2, and Slice 3 Phase 50 tests;
- the historical Phase 29 register test;
- the exact selected Phase 21, 27, 37, 39, 42, and 43 aggregate/grouped nodes;
- the exact selected Phase 47-49 schema/state/provenance/dependency/lineage
  nodes;
- protected-surface, version, and tag checks; and
- `/tmp/phase50-slice3-gate2-evidence-and-diff.txt` with complete tracked and
  no-index diffs and full changed Python test contents.

Do not run full pytest, `scripts/validate.py`, generated checks, golden checks,
package smoke, builds, benchmarks, dependency operations, network commands,
GitHub CLI, or CI. Once the first Ruff formatting command begins, a failure is
a stop condition and does not authorize repair.

## Slice 3 Stop Conditions

Stop without repair or scope expansion if:

- the repair baseline or exact five-file dirty set differs;
- any sixth repository path changes;
- the roadmap, historical Phase 29 register, Slice 1 scope spec, Slice 2
  inventory spec, production/public surface, or release surface changes;
- the four-state matrix proves insufficient;
- current implemented aggregate behavior is described as absent or widened;
- private readiness wording implies public behavior or Phase 51 implementation;
- a compatibility edit weakens a meaningful historical lock or requires
  non-shallow Git history;
- a no-index check emits a whitespace diagnostic; or
- Ruff, Pyright, complete Phase 50 pytest, or an exact evidence node fails.

## Slice 4 Gate 2 Allowlist

Phase 50 Slice 4 Gate 2 is limited to exactly:

- `docs/plan/phase-50-semantic-readiness-consolidation.md`;
- `docs/spec/phase50-type-system-gap-capability-readiness-v1.md`;
- `tests/test_phase50_type_system_gap_capability_readiness.py`;
- `tests/test_phase50_semantic_package_extension_capability_scope_lock.py`;
- `tests/test_phase50_post_v02_deferred_readiness_inventory.py`;
- `tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py`.

The final three paths are approved only for narrow current-status,
historical/current scope separation, exact dirty-set compatibility, and the
protected-path exception required by this exact Slice 4 dirty set. No seventh
repository path is approved. Nothing may be staged, committed, pushed, or
operated through CI in Gate 2.

## Slice 4 Focused Validation

Slice 4 Gate 2 validation is limited to:

- exact baseline, six-file dirty-set, staged-set, and whitespace checks;
- no-index whitespace checks for the two new files;
- Ruff format/check and lint for all four changed Python tests;
- test-project Pyright;
- the focused Slice 4 static test;
- complete execution of the Slice 1, Slice 2, Slice 3, and Slice 4 Phase 50
  test files;
- the historical Phase 29 register test and exact selected Phase 30, 36, 38,
  41, 42, 43, 47, and 49 type/nullability/privacy evidence nodes;
- history-independence, protected-surface, version, tag, and staged-set checks;
  and
- `/tmp/phase50-slice4-gate2-evidence-and-diff.txt` with complete tracked and
  no-index diffs and full changed Python test contents.

Do not run full pytest, `scripts/validate.py`, generated checks, golden checks,
package smoke, builds, benchmarks, dependency operations, network commands,
GitHub CLI, or CI. Once the first Ruff formatting command begins, a failure is
a stop condition and does not authorize repair.

## Slice 4 Stop Conditions

Stop without repair or scope expansion if:

- the completed Slice 3 baseline or exact six-file dirty set differs;
- any seventh repository path changes;
- the roadmap, Phase 29 register, completed Slice 1-3 specs, production/public
  surface, or release surface changes;
- the exact 11-name builtin inventory cannot be preserved or Enum would need
  to become a builtin;
- a production capability carrier, new behavior, or public schema appears
  necessary;
- a compatibility edit weakens a meaningful historical lock or requires
  parent history, runtime `/tmp` evidence, or network access;
- Slice 5 or Phase 52 work appears necessary;
- a no-index check emits a whitespace diagnostic; or
- Ruff, Pyright, focused Slice 4 pytest, complete Phase 50 pytest, or an exact
  evidence node fails.

## Stop Conditions

Stop without repair or scope expansion if:

- the current Slice 4 baseline or exact six-file dirty set differs;
- any seventh repository path changes;
- the historical roadmap table or v0.2 register requires modification;
- any production/public/release surface appears necessary;
- a no-index check emits a whitespace diagnostic;
- Ruff, Pyright, focused pytest, or compatibility pytest fails; or
- the final diff cannot prove the Slice 4 no-behavior boundary.
