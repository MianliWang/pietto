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

Phase 50 Slice 4 **Type-System Gap And Capability Readiness** completed at
`aaf30fcd2ec4b19f6d0c23783067c369a11cd27b`, with documented natural CI run
`29097916311` completing successfully for the exact commit.

Phase 50 Slice 5 **Window-Function Readiness** completed at
`d79c5c422cb7f54ae5e5587694e49389536419cb`, with documented natural CI run
`29115612846` completing successfully for the exact commit.

Phase 50 Slice 6 **Import / Module / Export Readiness** completed at
`7c7f6976dd67ccc4628757f2d857b593f71f5e0f`, with documented natural CI run
`29139545163` completing successfully for the exact commit.

Phase 50 Slice 7 **Semantic Package Model Readiness** completed at
`a5bc07855a0994343475ba546504e64b16fc7e63`, with documented natural CI run
`29141663534` completing successfully for the exact commit.

Phase 50 Slice 8 **PostgreSQL Extension Capability Readiness** completed at
`9e2c0f0ddcc2047e35985e6b97daa8bf29979914`, with documented natural CI run
`29157374991` completing successfully for the exact commit. Slice 8 completed
only after its separately authorized Gate 3 commit, push, and exact natural CI
success.

Phase 50 Slice 9 **Multi-dialect Capability Ecosystem Readiness** completed at
`f886589ac2f64eeb3770c914e7c049e2da105daa`, with documented natural CI run
`29170827348` completing successfully for the exact commit. Slice 9 completed
only after its separately authorized Gate 3 commit, push, and exact natural CI
success.

Phase 50 Slice 10 **Explain / Public Metadata / Package Integration Boundary**
completed at `9bc6ed82f3741e3c242981bb88edfb50c73fc586`, with documented
natural CI run `29179160024` completing successfully for the exact commit.
Slice 10 completed only after its separately authorized Gate 3 commit, push,
and exact natural CI success.

Phase 50 Slice 11 **Completion Audit And Status Lock** is the current
docs/spec/static-audit-only completion slice. Slice 11 is not complete in Gate
2. Phase 50 remains in progress through Gate 2. Phases 51 through 60 remain
unstarted and separately authorized. Phase 53 remains
`READINESS_CONTRACT_ONLY` under the current finalized route. Phase 54 remains
readiness-only and unstarted. Phase 55 remains `READINESS_CONTRACT_ONLY`,
readiness-only, and unstarted. Phase 56 remains unstarted. Phase 57 remains
`READINESS_CONTRACT_ONLY`, readiness-only, and unstarted. Phase 58 remains
readiness-only and unstarted. Phase 60 remains readiness-only and unstarted.

Phase 50 is complete only after Slice 11 Gate 3 commit, one normal push to
main, and exact natural CI success for the push run whose headSha exactly
matches the Slice 11 commit.

Every Phase 50 slice is readiness-only. No slice automatically authorizes later
behavior or a later phase.

## Trusted Baseline

- Baseline branch: `main`.
- Baseline HEAD: `9bc6ed82f3741e3c242981bb88edfb50c73fc586`.
- Baseline local `origin/main`:
  `9bc6ed82f3741e3c242981bb88edfb50c73fc586`.
- Baseline subject: `Add Phase 50 explain public metadata boundary`.
- Baseline parent/Slice 9 commit:
  `f886589ac2f64eeb3770c914e7c049e2da105daa`.
- Documented natural Slice 10 CI run: `29179160024`, workflow/event
  `CI / push`,
  status/conclusion `completed / success`, with an exact `headSha` match.
- Package version remains `0.1.0`.
- No tag points at HEAD and there is no exact-match tag.

The CI facts above are repository-local documented evidence. Slice 11 Gate 2
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

Slices 1 through 10 are complete. Slice 11 is current but incomplete in Gate
2. Phase 50 remains in progress through Gate 2. Listing the route does not
start Phase 51 or any later phase.

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
- **Gate discipline:** Slice 4 completed only after its separately authorized
  Gate 3 commit, push, and documented exact natural CI success at
  `aaf30fcd2ec4b19f6d0c23783067c369a11cd27b`. Its historical Gate 2 allowlist
  and validation record remain preserved below.

## Slice 5 Window-Function Readiness

- **Objective:** define the future decision surface for window expressions,
  ranking families, partitioning, window-local ordering, frames, clause
  placement, result typing/nullability, grouped interaction, private
  dependencies, diagnostics, dialect capability, and the bounded Phase 53
  handoff.
- **Artifact type:** this plan update, the readiness contract at
  `docs/spec/phase50-window-function-readiness-v1.md`, decision matrices, one
  focused static-audit test, and four narrow Phase 50 compatibility updates.
- **Prerequisites:** completed Slices 3 and 4, current aggregate/group/order/let
  evidence, Phase 47-49 private project facts, and the Slice 2 inventory.
- **Completed-phase relationship:** preserves current generic call parsing,
  generic unknown-function failure, ordinary aggregate behavior, final relation
  ordering, grouped `satisfying`/HAVING behavior, and all private carriers
  without describing any of them as window support.
- **Current evidence:** Pietto has no window grammar or dedicated token/rule, no
  `OVER` attachment point, partition syntax, window-local order syntax, frame
  syntax, named-window syntax, window AST, semantic catalog, type/nullability
  behavior, project carrier, Window IR, SQL `OVER` lowering, public metadata,
  window-specific diagnostic, or positive fixture/golden. Generic
  function-shaped calls may parse as ordinary calls, while SQL-like
  `sum(amount) over (region)` is parser-rejected. Generic call syntax is not
  window support. Ordinary aggregate support is not aggregate-as-window
  support.
- **Initial catalog decision:** exactly `row_number`, `rank`, and `dense_rank`
  are readiness candidates. Each has zero arguments and candidate logical
  `Int` / compiler `NON_NULL` result facts. They are not implemented, reserved,
  parsed as windows, typed, lowered, or exposed by Slice 5.
- **Deferred-family decision:** `percent_rank`, `cume_dist`, `ntile`, `lag`,
  `lead`, `first_value`, `last_value`, `nth_value`, aggregate-as-window,
  `count_distinct` as window, percentile/statistical functions,
  ordered-set/hypothetical-set functions, and dialect-specific analytics remain
  deferred.
- **Placement decision:** the initial candidate is an inline unnamed direct
  top-level `select` projection with an explicit alias and no default output
  name. `let`, `where`, group keys, aggregate arguments, `satisfying`, nested
  scalar expressions, another-window arguments, same-select alias reuse, final
  order window expressions/aliases, and QUALIFY-like filtering remain rejected
  or deferred as specified by the readiness contract.
- **Partition and ordering decision:** partitioning is optional and limited to
  one or more direct bare or current single-input-qualified fields in source
  order. Window-local ordering is mandatory for all three initial ranking
  candidates and is limited to those same direct-field forms with optional
  `asc` / `desc`. Computed expressions, lets, selected aliases, aggregates,
  windows, ordinals, null ordering, and collation controls are excluded.
- **Frame and naming decision:** no explicit frame syntax and no backend-default
  frame guarantee are adopted. Named windows, inheritance, frame exclusion,
  null ordering, and QUALIFY remain deferred. Slice 5 reserves no exact source
  spelling.
- **Query-phase decision:** readiness models input/lets, row `where`, grouping
  and ordinary aggregates, `satisfying`/HAVING, window calculation, final
  relation order, then `limit`. This is a future conceptual order, not current
  execution behavior. Initial ranking over ungrouped input is the only candidate;
  grouped ranking, aggregate-as-window, selected alias reuse, and let-bound
  partition/order remain deferred pending later evidence.
- **Output/dependency decision:** explicit aliases preserve selected source
  order and use documentation-only private `WINDOW_RESULT` vocabulary distinct
  from `GROUP_KEY` and `AGGREGATE_RESULT`. Candidate dependency vocabulary is
  `WINDOW_ARGUMENT`, `WINDOW_PARTITION`, `WINDOW_ORDER`, `WINDOW_FRAME`,
  `WINDOW_DEFAULT`, plus a relation-input dependency for argument-less ranking.
  These tokens commit to no production enum, class, field, serializer, Project
  JSON field, explain output, public metadata, or public API.
- **Capability and dialect decision:** Phase 52 remains unstarted and is only a
  future private capability prerequisite. PostgreSQL and private MySQL receive
  no current window-support claim; each exact feature requires direct evidence
  and must fail closed independently. Slice 5 reserves no diagnostic code.
- **Later handoff:** preserves Phase 53 **Window Function Syntax And Capability
  Contract** as `READINESS_CONTRACT_ONLY`. It may later lock exact syntax and
  matrices for the three candidates without production behavior. Concrete
  window implementation remains outside Phase 51-60 until an evidence-backed
  append-only replan separately authorizes it.
- **Explicit non-goals and no-behavior boundary:** Slice 5 implements no
  compiler or runtime behavior. It adds no grammar, generated parser, AST,
  semantic catalog/analysis, type/nullability behavior, project carrier,
  dependency/lineage carrier, IR, SQL, diagnostic, CLI, JSON, public metadata,
  capability profile, backend, fixture, golden, runtime, database, package,
  version, or release behavior.
- **Gate discipline:** Slice 5 is not complete in Gate 2. It uses the exact
  seven-file allowlist and focused validation below. Completion requires a
  separately authorized Gate 3 commit, push, and exact natural CI success.
  Slice 5 later completed only through that separately authorized Gate 3 at
  `d79c5c422cb7f54ae5e5587694e49389536419cb` and documented natural CI run
  `29115612846`.

## Slice 6 Import / Module / Export Readiness

- **Objective:** reconcile flat project namespaces with future module identity,
  imports, exports, visibility, qualified names, deterministic ordering, and
  cycle rules.
- **Artifact type:** this plan update, the readiness contract at
  `docs/spec/phase50-import-module-export-readiness-v1.md`, decision matrices,
  one focused static-audit test, and five narrow Phase 50 compatibility updates.
- **Prerequisites:** Phase 45-49 project semantic foundations and Slice 2.
- **Completed-phase relationship:** preserves current cross-file flat namespace
  behavior and the historical Phase 50 roadmap row as planning history.
- **Current architecture:** one deterministic selected project compile unit
  retains normalized project-relative `.pietto` inputs in path order,
  collects supported top-level definitions before resolution, and resolves
  currently supported cross-file references without imports. Files are
  semantically transparent at those reference sites. File/source order controls
  deterministic collection, duplicate ownership, and diagnostics, not
  visibility or forward-reference acceptance.
- **Current namespaces:** exactly three flat project-global namespaces:
  `TYPE` owns type aliases, enums, and shapes; `RELATION` owns sources,
  tables, and queries; `CALLABLE` owns constraints and derives. Same-name
  declarations fail closed within one namespace, while the same spelling may
  occur once across different namespaces.
- **Current absence:** Pietto currently has no module identity, module
  namespace, import binding, export surface, public/private declaration
  visibility, re-export, module graph, or module-cycle behavior. Project-global
  visibility is not an export, package-public, public-metadata, or runtime
  contract. Python imports, relation `from`, source connectors, field
  qualification, provenance, and lineage paths are not Pietto module imports.
- **Route D decision:** preserve current flat project-global behavior unchanged.
  A future separately activated explicit-module mode may use one selected
  `.pietto` file as one local module and follow the file-as-module semantic
  shape. No current file becomes a module, and no activation flag, schema
  version, root module, migration rewrite, automatic import, directory module,
  logical multi-file module, or manifest is selected.
- **Identity decision:** the private documentation-only candidate is the exact
  current normalized project-relative selected input path including the
  `.pietto` suffix. It is not source syntax, a Project JSON module identity, a
  semantic-package identity, or a package-qualified name. Current path,
  containment, symlink/root-escape, and duplicate-physical-file rules remain
  unchanged. Extension omission, logical/manifest/declaration/package identity,
  case folding, Unicode normalization, cross-platform collision rules, and
  extra filesystem normalization remain deferred.
- **Import decision:** a future explicit mode starts with explicit named imports
  and an optional local alias. One explicitly exported declaration creates one
  unique local binding. Import order has no semantic precedence, and there is
  no transitive visibility, implicit re-export, automatic legacy import, or
  silent duplicate deduplication. Wildcard, namespace/module-object,
  side-effect, type-only, relation-only, package-qualified, implicit,
  transitive, and module-qualified forms remain rejected or deferred.
- **Export/visibility decision:** declarations are private by default in a
  future explicit mode and become visible only through an explicit local
  declaration export list. Export is compiler visibility only, not Project JSON
  serialization, semantic-package publication, or runtime access. Export-all,
  public-by-default, wildcard, alias, re-export, imported-binding export, and
  transitive export remain deferred or excluded.
- **Declaration eligibility:** type aliases, enums, shapes, sources, tables, and
  queries are initial import/export candidates. Constraints and derives are
  deferred. Relationship metadata is excluded. Fields, clauses, lets, select
  items, expressions, and headers are not top-level declaration candidates.
- **Reference decision:** local declarations and imported bindings are future
  distinct lookup sources, with collision validation before lookup and no
  shadow winner. Declaration/module, relation, field, immediate-upstream,
  package, provenance, and lineage qualification remain separate. Module-,
  file-path-, and package-qualified references remain deferred.
- **Graph/order decision:** the future documentation-only local module graph has
  canonical local module nodes and explicit named-import edges. It remains
  separate from relation, row, lineage, type-alias, package, and backend graphs.
  Readiness ordering is canonical project input, declaration source order,
  import source order, canonical module traversal, deterministic equal-origin
  targets, then deterministic diagnostics.
- **Fail-closed decision:** module and later re-export cycles, duplicate module
  identity, duplicate local/export/import binding, local/import or alias
  collision, ambiguous reference, private-symbol access, missing export, and
  unresolved module all fail closed. No collision receives a semantic winner.
  There is no initial type-only cycle exception. Existing `PIE-S2302` is not
  reused and Slice 6 adds or reserves no diagnostic code.
- **Compatibility decision:** existing flat projects continue unchanged.
  Explicit-module behavior must be additive and separately activated. Slice 6
  selects no compatibility flag, project schema change, implicit root module,
  automated migration, compatibility bridge, or source rewrite.
- **Local-module/package boundary:** Slice 6 and Phase 54 own only project-local
  identity, bindings, visibility, graph, ordering, collision, cycle, and
  compatibility readiness. Slice 7 and Phase 55 own semantic package identity,
  version, assets, dependencies, capability/dialect attribution, provenance,
  and distribution boundaries. Registry, fetch, install, cache, solver,
  lockfile, executable code, plugins, hooks, lifecycle actions, and network
  behavior remain excluded.
- **Public/private boundary:** future module identities, bindings, export
  surfaces, visibility decisions, graph/cycle facts, and package attribution
  remain private initially. Slice 6 changes neither Project JSON v2 nor
  Semantic Metadata Artifact v1.
- **Later handoff:** prepares Phase 54 Import / Module / Export Readiness as an
  unstarted, separately authorized, readiness-only phase. The bounded handoff
  is vocabulary, Route D, private file-as-module identity, named imports,
  private-by-default explicit exports, declaration eligibility, deterministic
  graph/order and fail-closed matrices, current-flat compatibility,
  private-first metadata, and local-module/package separation only.
- **Explicit non-goals and no-behavior boundary:** Slice 6 implements no
  compiler or runtime behavior. It adds no grammar, exact source syntax,
  generated parser, AST, loader, resolver, filesystem discovery/loading,
  ProjectSemanticModel behavior/carrier, visibility enforcement, diagnostic,
  CLI, JSON, public metadata, manifest, package resolution, registry,
  installation, IR, SQL, runtime, database, dependency, workflow, fixture,
  golden, package version, or release behavior.
- **Gate discipline:** Slice 6 completed at
  `7c7f6976dd67ccc4628757f2d857b593f71f5e0f` only after its separately
  authorized Gate 3 commit, push, and exact natural CI success in run
  `29139545163`. Its historical Gate 2 allowlist and focused validation remain
  preserved below. The historical roadmap row does not authorize
  implementation.

## Slice 7 Semantic Package Model Readiness

- **Objective:** define static semantic asset identity, attribution,
  dependency, ordering, versioning questions, and the non-executable safety
  model.
- **Artifact type:** this plan update, the readiness contract at
  `docs/spec/phase50-semantic-package-model-readiness-v1.md`, decision
  matrices, one focused static-audit test, and six narrow Phase 50
  compatibility updates.
- **Prerequisites:** Slices 4 and 6 and Phase 49 private lineage foundations.
- **Completed-phase relationship:** treats current project/source facts and
  private lineage as possible prerequisites, not package objects or public
  output.
- **Current posture:** Pietto currently has no semantic-package behavior. It
  has readiness vocabulary only, separate from Python distribution packaging,
  project-local modules, connector declarations, database extensions, and
  runtime package management. There is no semantic-package grammar, parser,
  AST, project or semantic carrier, asset inventory, export surface,
  dependency declaration, graph, requirement, provenance/digest field, IR,
  SQL, CLI, JSON, loader, resolver, registry, fetch/install/cache behavior, or
  runtime execution.
- **Python distribution boundary:** the installable Python distribution
  `pietto` at version `0.1.0`, its wheel/sdist metadata, Python dependencies,
  console entry point, `importlib.metadata` lookup, installation, and package
  smoke are not Pietto semantic-package support.
- **Project-local module boundary:** current flat project namespaces and the
  future Route D local file-as-module direction remain distinct from semantic
  packages. A project path, module path, repository URL, connector name, or
  Python distribution name cannot supply semantic-package identity.
- **Route B decision:** select a static semantic asset bundle that is
  declarative, reviewable, deterministic, non-executable, and composed of typed
  semantic assets and typed support assets. Route A documentation-only bundles
  are insufficiently typed; Route C source packages and Route D hybrid
  source/catalog packages remain deferred; Route E executable plugins are
  rejected. Slice 7 and Phase 55 readiness do not make a package loadable.
- **Identity decision:** conceptual package identity is a logical
  `(namespace, name)` tuple displayed as `namespace/name`. Both components are
  canonical lowercase ASCII slugs, logically case-sensitive after canonical
  validation, with no alternate case-folded equivalence. This does not prove
  global registry uniqueness or organization ownership and is not a URL,
  project/module path, connector name, source syntax, Python distribution
  name, or public API. Exact manifest keys and validation remain future Phase
  55 work.
- **Version decision:** package schema version is a required exact integer with
  initial readiness candidate `1`; package release version is a required exact
  SemVer string whose prerelease/build metadata remains part of exact equality.
  They remain distinct from Python distribution version `0.1.0`, current
  project schema version, and later capability/extension catalog versions. No
  SemVer parser, precedence selection, range, solver, update, or lockfile
  behavior is added.
- **Asset taxonomy decision:** conceptual initial semantic asset kinds are
  `TYPE_ALIAS`, `ENUM`, and `SHAPE`. Conceptual non-executable support kinds are
  `DOCUMENTATION`, `EXAMPLE`, and `STATIC_TEST_VECTOR`. Support assets are not
  compiler bindings; static test vectors contain declared input and expected
  data only, never runners, hooks, commands, environment/network access,
  database execution, or dynamic code. These labels are readiness vocabulary,
  not production enums or schema discriminators.
- **Deferred asset decision:** source files, local modules, module export
  surfaces, connectors, tables, queries, constraints, derives, relationship
  metadata, function/aggregate signatures, capability/dialect/extension
  profiles, extension signature catalogs, public semantic metadata, arbitrary
  fixtures/goldens/binaries, and migrations are not initial assets. No asset is
  currently loadable.
- **Public-surface decision:** semantic assets are private by default. The
  conceptual public surface is an explicit ordered list of locally owned
  semantic asset identities; only `TYPE_ALIAS`, `ENUM`, and `SHAPE` are
  initially export-eligible. Support assets are not semantic exports, and
  imported/dependency-owned assets cannot be exported. Wildcard/export-all,
  public-by-default, aliases, re-export, dependency export, and transitive or
  registry-derived visibility are excluded.
- **Dependency decision:** initial dependency facts are exact target
  `namespace/name`, exact release version, and optional expected digest only.
  A future already-materialized package set must contain the exact release or
  validation fails closed. There are no ranges, aliases, asset selectors,
  optional/development/peer dependencies, features, activation expressions,
  solving, fetching, downloading, installation, caching, updating, registry
  lookup, lockfile generation, or lockfile consumption.
- **Graph/cycle decision:** future private package nodes are exact package
  releases with exact dependency edges; future asset nodes and references form
  a separate graph. Both remain separate from module, relation, row,
  type-alias, capability, extension, and provenance graphs. Duplicate package
  release/dependency/asset identity, unknown asset kinds, invalid exports,
  private access, missing/ambiguous references, package dependency cycles, and
  cross-asset cycles fail closed without a semantic winner. Slice 7 implements
  no graph and adds or reserves no diagnostic code.
- **Requirement decision:** a future package may declaratively name exact
  language/compiler, scalar/operator, aggregate, future window, dialect, and
  extension profile requirement identities. Requiring, providing, containing,
  and project availability remain separate facts. Initial packages neither
  provide nor embed profiles or extension signature catalogs, and Slice 7 or
  Phase 55 readiness validates none. Phases 56-57 own profile/catalog checking;
  Phase 58 owns public reporting.
- **Provenance/digest/trust decision:** required facts are package identity,
  release version, and schema version. Optional private descriptive facts may
  include a source repository locator, source revision, and externally supplied
  digest algorithm/value. They authorize no fetch, VCS verification,
  publisher authority, digest computation/verification, canonical-byte claim,
  signature, attestation, or trust policy. Public provenance remains deferred.
- **Deterministic ordering:** package releases order by `namespace/name` then
  exact version; dependency diagnostics preserve declaration order while graph
  traversal uses canonical target identity/version; assets preserve source
  order for diagnostics/display and use canonical kind then local name for
  equality/traversal; requirements use canonical identity. Duplicate facts
  fail before canonicalization can silently deduplicate them.
- **Manifest direction:** future authoring uses a package-specific strict TOML
  manifest, separate from current `pietto.toml`, with strict schema version,
  typed keys, unknown-key rejection, no interpolation, no remote include, and
  no code hook. Exact filename, keys, layout, parser, serializer, canonical
  bytes, digest algorithm, and project integration remain Phase 55 decisions.
- **Project/package integration:** a later project may be supplied an already
  materialized exact package set, but package assets do not become project
  bindings without a separately authorized integration contract.
  Package-qualified import syntax is not selected.
- **Public/private metadata boundary:** initial package facts remain private.
  Slice 7 adds no Project JSON v2, Semantic Metadata Artifact v1, explain,
  public metadata, registry display, portability, provenance, or lineage field.
- **Diagnostic boundary:** future invalid, duplicate, missing, ambiguous,
  private, cyclic, unsupported, or executable package facts fail closed, but
  Slice 7 selects no code, wording, severity, order, JSON shape, or public
  diagnostic category.
- **Package-manager boundary:** registry search, remote fetch, download, cache,
  installation, updates, version solving, range resolution, lockfiles,
  publishing, signing, verification, attestation, and trust policy remain
  `OUTSIDE_51_60`. Python/native plugins, entry points, hooks, lifecycle
  actions, scripts, arbitrary code, and database extension installation remain
  prohibited.
- **Later handoff:** prepares Phase 55 Semantic Package Asset Schema as
  `READINESS_CONTRACT_ONLY`, readiness-only, unstarted, and separately
  authorized. The bounded handoff is vocabulary, Route B, conceptual identity,
  orthogonal versions, the exact six initial asset kinds, private explicit
  exports, exact dependency facts, requirement identities, private provenance,
  deterministic fail-closed matrices, strict package-TOML direction, and the
  no-executable/no-package-manager boundary only.
- **Explicit non-goals and no-behavior boundary:** Slice 7 implements no
  compiler or runtime behavior. It adds no grammar, source package import,
  manifest parser, current `pietto.toml` change, production package model,
  loader, resolver, graph, solver, registry, network, installation, cache,
  lockfile, publisher, signature/trust behavior, arbitrary code, profile or
  catalog schema, diagnostic, IR, SQL, CLI, JSON, public metadata,
  runtime/database behavior, or Phase 56-59 implementation.
- **Gate discipline:** Slice 7 completed only after its exact nine-file Gate 2,
  separately authorized Gate 3 commit and push, and documented exact natural
  CI success at `a5bc07855a0994343475ba546504e64b16fc7e63` in run
  `29141663534`. Its historical Gate 2 allowlist and focused validation remain
  preserved below.

## Slice 8 PostgreSQL Extension Capability Readiness

- **Objective:** distinguish base PostgreSQL backend capability from static
  declared extension overlays and missing-capability failure.
- **Artifact type:** this plan update, the readiness contract at
  `docs/spec/phase50-postgresql-extension-capability-readiness-v1.md`, decision
  matrices, one focused static-audit test, and seven narrow Phase 50
  compatibility updates.
- **Prerequisites:** Slices 4 and 7 and the Phase 9 closed backend capability
  precedent.
- **Completed-phase relationship:** preserves current PostgreSQL and private
  MySQL dispatch/lowering behavior unchanged.
- **Current PostgreSQL posture:** Pietto has bounded PostgreSQL compilation and
  a static `postgres.table` connector contract. Current public PostgreSQL API,
  closed PostgreSQL/private MySQL CLI dispatch, exact connector validation,
  closed scalar/aggregate/operator/type catalogs, and reviewed PostgreSQL
  lowering remain unchanged.
- **Current extension posture:** extension-profile vocabulary is readiness-only;
  concrete support is explicitly deferred; a custom signature-catalog schema
  is not evidenced. There is no extension grammar, AST, semantic/project/
  requirement/availability/profile/catalog carrier, extension type/function/
  aggregate/operator/cast/table-function support, extension-aware lowering,
  installed-state detection, introspection, installation, or public field.
- **False-positive boundary:** `postgres.table` is connector identity, not
  extension availability; `--dialect postgres` is backend selection, not a
  server instance; PostgreSQL lowering or similar SQL spelling is not extension
  support; logical/native type, package requirement/installation, declared
  profile/server state, and catalog entry/database object remain distinct.
- **Route decision:** select Route B, a static, declarative, strongly typed,
  deterministic, reviewable, non-executable extension profile with typed
  signature catalog layered over an immutable PostgreSQL base profile. Reject
  coarse Route A, SQL-template Route C, introspected Route D, and executable
  plugin Route E.
- **Identity/version decision:** conceptual extension identity is
  `(postgresql_base_profile_identity, canonical_extension_name)` with a
  lowercase ASCII exact name. Extension release is an exact opaque string;
  profile/catalog schema versions are exact integers; profile/catalog releases
  are separate exact strings; optional server compatibility is declared only;
  optional supplied digest is neither identity nor verified.
- **Composition decision:** the base profile is immutable and overlays are
  additive-only. Equivalent duplicates, replacements, conflicting signatures,
  type identities, native mappings, emitted spellings, or lowering ownership
  fail closed. Textual or dependency order gives no semantic precedence.
- **Catalog taxonomy decision:** readiness includes extension-scoped logical/
  native type pairs, fixed typed scalar signatures, fixed typed aggregate
  signatures, existing-token unary/binary operator signatures, and explicit
  cast signatures. Window/table/relation/set-returning functions, special/new
  syntax, DDL, indexes/operator classes, planner/configuration/runtime actions,
  SQL templates/macros, and executable hooks are deferred, excluded, or
  rejected.
- **Type decision:** extension types are scoped opaque logical identities with
  explicit native spelling and no automatic comparison, ordering, grouping,
  arithmetic, aggregate, cast, IR, lowering, or public-metadata capability.
- **Signature decision:** scalar/aggregate/operator/cast facts use exact owner,
  fixed role/arity/ordered logical types, result/nullability, context,
  PostgreSQL emitted identity, and exact prerequisites. Matching is exact only;
  no aliases, variadics, defaults, polymorphism, generics, implicit coercion,
  ranking, best match, or ambiguity winner.
- **Requirement/dependency decision:** semantic-package requirement, explicit
  project availability, catalog description, approved backend lowering, and
  unknown actual server state are independent. Direct exact extension
  identity/version requirements validate an already-materialized declared set;
  no ranges/solver/install; missing facts and cycles fail closed.
- **Examples/ordering decision:** PostGIS, pgvector, pg_trgm, and TimescaleDB
  remain `NOT_EVIDENCED` matrix examples only. Source order is diagnostic/
  display order; canonical identity/signature order governs equality/traversal;
  no textual precedence exists.
- **Ownership/privacy decision:** Slice 8 owns only this contract; Phase 55
  retains its exact six initial assets; Phase 56 owns profile schemas/checking;
  Phase 57 owns catalog readiness; Phase 58 owns public reporting; Phase 59
  owns graph/provenance integration. All future extension facts remain private.
- **Provenance/trust decision:** optional private locator/revision, curator/
  generation description, and supplied digest facts imply no fetch,
  introspection, generation, computation, verification, publisher authority,
  signing, attestation, registry trust, or trust policy.
- **Later handoff:** prepares Phase 57 PostgreSQL Extension Signature-Catalog
  Readiness as `READINESS_CONTRACT_ONLY`, readiness-only, unstarted, and
  separately authorized. The handoff is vocabulary and matrices only, not a
  production carrier, concrete signature, behavior, or implementation-slice
  plan.
- **Explicit non-goals and no-behavior boundary:** Slice 8 implements no
  compiler or runtime behavior. It adds no grammar, parser, AST, production
  profile/catalog/package/capability carrier, semantic/type/operator/aggregate
  acceptance, IR, SQL, CLI, JSON, public metadata, diagnostic, connection,
  introspection, discovery, `CREATE EXTENSION`, installation, registry,
  network, runtime/database behavior, or Phase 56-59 implementation.
- **Gate discipline:** Slice 8 completed only after its exact ten-file Gate 2,
  separately authorized Gate 3 commit and push, and documented exact natural
  CI success at `9e2c0f0ddcc2047e35985e6b97daa8bf29979914` in run
  `29157374991`. Its historical Gate 2 allowlist and focused validation remain
  preserved below.

## Slice 9 Multi-dialect Capability Ecosystem Readiness

- **Objective:** distinguish dialect family, compiler backend, base capability
  profile, additive overlay, source connector, semantic-package requirement,
  declared project availability, actual server state, lowering ownership, and
  declared portability without conflating any of them.
- **Artifact type:** this plan update, a multi-dialect readiness contract,
  taxonomy and evidence matrices, one focused static-audit test, and eight
  narrow compatibility-test updates.
- **Prerequisites:** completed Slices 4, 7, and 8 and current closed
  PostgreSQL/MySQL backend and connector contracts.
- **Completed-phase relationship:** preserves PostgreSQL as the bounded public
  backend, MySQL as the bounded private backend, closed CLI selection, current
  connector validation, and fail-closed backend diagnostics. `postgres.table`
  and `mysql.table` are source connectors, not backend/profile/server
  selection, and their current validation details are not claimed identical.
- **Route decision:** select Route B: static, strongly typed, declarative,
  deterministic, reviewable, non-executable dialect profiles with explicit
  backend-lowering facts and immutable base profiles plus additive-only
  declared overlays. Reject scattered flags, least-common-denominator
  fallback, SQL-template/macro translation, runtime introspection, and
  executable plugin routes.
- **Identity/version decision:** use canonical exact lowercase dialect-family
  identities. Dialect family, profile schema version, profile release,
  compiler-backend identity/release, optional declared server requirement, and
  optional supplied digest are distinct facts. Initial comparison is exact
  equality only: no ranges, solver, precedence selection, or automatic version
  choice.
- **Composition/conflict decision:** base profiles are immutable and overlays
  are additive-only. Duplicate, replacement, conflict, ambiguity, missing
  capability, missing lowering, unsupported context, and backend/profile
  mismatch fail closed. Source order may stabilize diagnostic/display order
  only; it gives no semantic winner.
- **Portability decision:** future declared classification is exactly
  `SUPPORTED_IDENTICALLY`, `SUPPORTED_WITH_DIALECT_SPECIFIC_LOWERING`,
  `SUPPORTED_WITH_SEMANTIC_DIFFERENCES`, `UNSUPPORTED`,
  `UNKNOWN_OR_NOT_DECLARED`, and `BLOCKED_BY_MISSING_CAPABILITY`. No silent
  degradation, least-common-denominator fallback, best-effort rewriting, or
  unknown-as-supported behavior is authorized.
- **Evidence-scoped examples:** SQLite has rejection evidence only. DuckDB,
  BigQuery, Snowflake, and Trino are `NOT_EVIDENCED` examples only; none is an
  accepted CLI dialect, profile implementation, or backend promise.
- **Ownership/privacy decision:** Phase 55 retains semantic-package asset
  schema; Phase 56 retains capability/dialect/extension profile schema and
  checking; Phase 57 retains PostgreSQL extension signature-catalog readiness;
  Slice 10 and Phase 58 retain public explain/portability reporting; Phase 59
  retains package graph/provenance integration. All profile, overlay,
  portability, and server facts remain private future facts.
- **Later handoff:** prepares Phase 56 schema/checking readiness and the
  bounded Phase 60 Multi-dialect Capability Ecosystem Completion Checkpoint.
  Phase 60 remains readiness-only, unstarted, separately authorized, and not
  a backend, runtime, or release authority.
- **Explicit non-goals and no-behavior boundary:** Slice 9 implements no
  compiler or runtime behavior. It adds no dialect, backend, connector,
  grammar, parser, AST, semantic carrier, profile schema, profile loader,
  checker, type/function/operator/aggregate acceptance, IR, SQL lowering,
  CLI, JSON, public metadata, package asset, database connection,
  introspection, runtime translation, template, macro, plugin, registry,
  network, or server behavior.
- **Gate discipline:** Slice 9 completed only after its exact eleven-file Gate
  2 scope, separately authorized Gate 3 commit/push, and documented exact
  natural CI success at `f886589ac2f64eeb3770c914e7c049e2da105daa` in run
  `29170827348`. Its historical allowlist and focused validation record remain
  preserved below. Slice 10 later completed at
  `9bc6ed82f3741e3c242981bb88edfb50c73fc586`; Slice 11 is current but
  incomplete, and Phases 51-60 remain unstarted.

## Slice 10 Explain / Public Metadata / Package Integration Boundary

- **Objective:** contract a privacy-preserving future boundary between existing
  public artifacts, private project/package/profile facts, future project
  explain, portability reporting, package inspection, and later provenance/
  lineage integration.
- **Artifact type:** this plan update, one integration-boundary specification,
  one focused static audit, and nine narrow completed-Phase-50 compatibility
  updates.
- **Prerequisites:** completed Slices 3 and 7-9, completed Phase 45-49
  private-carrier privacy, current single-file explain/Artifact v1, and current
  Project JSON v2 check behavior.
- **Completed-phase relationship:** preserves CLI JSON v1, Semantic Metadata
  Artifact v1, the bounded single-file `pietto explain FILE` surface, Project
  JSON v2 check envelope, PostgreSQL public/MySQL private backend posture, and
  private Phase 45-49 row schema, origin, provenance, dependency graph, and
  lineage carriers.
- **Route decision:** select Route B: any later public fact is an explicit,
  independently versioned, deterministic, reviewable, fail-closed projection
  from an authorized private fact subset. Reject direct private-model exposure,
  one merged universal metadata document, indefinite-private-only Route A,
  runtime/introspected reporting, and plugin-generated reporting.
- **Artifact-separation decision:** CLI JSON v1, Semantic Metadata Artifact v1,
  Project JSON v2 check, future project explain, future portability report, and
  future package-inspection report remain distinct artifact families. No
  artifact inherits fields, semantics, or versioning from another artifact
  implicitly. A future cross-artifact reference requires explicit stable
  identity and version semantics.
- **Public/private decision:** package identity/release/schema, asset/export/
  requirement summaries, declared profile/extension/dialect requirements, and
  declared project availability are future descriptive projection candidates
  only. Resolved package/profile/catalog identity, package/asset graphs,
  private origin/provenance, row dependency graphs/lineage, supplied-digest
  trust/verification, and actual server/database/installation state remain
  private, deferred, or NOT_EVIDENCED as their owners require.
- **Portability decision:** a later report may project only the exact Slice 9
  classifications `SUPPORTED_IDENTICALLY`,
  `SUPPORTED_WITH_DIALECT_SPECIFIC_LOWERING`,
  `SUPPORTED_WITH_SEMANTIC_DIFFERENCES`, `UNSUPPORTED`,
  `UNKNOWN_OR_NOT_DECLARED`, and `BLOCKED_BY_MISSING_CAPABILITY`. It cannot
  claim runtime validation, fallback, silent degradation, best-effort rewrite,
  or automatic translation.
- **Versioning/ordering decision:** each future artifact owns a separate schema
  version. Removing, renaming, changing type/nullability/meaning/allowed
  values, or collapsing Artifact v1's failure metadata absence is breaking.
  Future arrays require explicit deterministic ordering; object-member order
  remains artifact-specific rather than universal. Unknown, absent, null,
  redacted, private-only, conflicting, and unavailable facts remain distinct.
- **Conflict/privacy decision:** missing, conflicting, private-only,
  unresolved, cyclic, unsupported, missing-lowering, or unavailable provenance
  facts fail closed with no fabricated value or winner. No new diagnostic code,
  message, severity, ordering, CLI error, JSON envelope, or runtime behavior is
  added.
- **Later handoff:** prepares only Phase 58 Project Explain / Portability /
  Public Metadata Readiness and informs Phase 59 Package Graph And Lineage /
  Provenance Integration. Phase 58 remains readiness-only, unstarted, and
  separately authorized. Slice 10 does not begin Phase 58 or 59.
- **Explicit non-goals and no-behavior boundary:** Slice 10 implements no
  compiler or runtime behavior. It adds no serializer, CLI command or option,
  CLI JSON v1 field, Project JSON v2 field, Semantic Metadata Artifact v1
  field, project explain output, portability report, package inspection output,
  public lineage/provenance, package/profile/catalog loader, capability
  checker, package graph, diagnostic, IR, SQL, runtime/database, network,
  registry, installation, introspection, plugin, or server behavior.
- **Gate discipline:** Slice 10 completed at
  `9bc6ed82f3741e3c242981bb88edfb50c73fc586` only after its exact
  twelve-file Gate 2 scope, separately authorized Gate 3 commit and normal
  push, and documented exact natural CI success in run `29179160024`. Its
  historical allowlist and validation record remain preserved below. No
  private fact becomes public by being named as a future input.

## Slice 11 Completion Audit And Status Lock

- **Objective:** audit the completed Phase 50 readiness contracts for internal
  consistency and prove that no behavior was implemented.
- **Artifact type:** this plan status update, the completion contract at
  `docs/spec/phase50-completion-audit-and-status-lock-v1.md`, one focused
  static-audit test, and ten narrow completed-Phase-50 compatibility updates.
- **Prerequisites:** separately completed and published Slices 1 through 10.
- **Completed-phase relationship:** records readiness decisions without
  rewriting earlier phase history, changing any historical allowlist, or
  promoting readiness vocabulary to implementation.
- **Later handoff:** freezes the finalized Phase 51-60 planning handoff for
  separate authorization. Phases 51-60 remain unstarted, and Phase 51 does not
  start merely because Phase 50 later completes.
- **Completion encoding:** conditional single-commit completion plus exact Gate
  3 natural-CI evidence. Phase 50 is complete only after Slice 11 Gate 3
  commit, one normal push to main, and exact natural CI success for the push
  run whose headSha exactly matches the Slice 11 commit. No post-CI repository
  status-flip commit is planned or required.
- **Gate 2 state:** Slices 1-10 are complete. Slice 11 is current but
  incomplete in Gate 2. Phase 50 remains in progress through Gate 2. Gate 2
  docs and tests must not pre-claim the Slice 11 commit, push, natural CI
  result, or Phase 50 completion.
- **Post-condition meaning:** Phase 50 is complete as an eleven-slice
  docs/spec/static-audit-only readiness consolidation phase. This completion
  authorizes no Phase 51-60 implementation.
- **Explicit non-goals and no-behavior boundary:** Slice 11 implements no
  compiler or runtime behavior. It adds no implementation, public surface,
  package version, workflow, dependency, release, or runtime change.
- **Gate discipline:** Slice 11 uses the exact thirteen-file allowlist and
  focused validation below. Gate 2 does not stage, commit, push, access CI, or
  prepare Gate 3. A later Gate 3 requires separate explicit authorization.

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

Slice 5 preserves every surface above, the roadmap, all completed Slice 1-4
specs, the historical Phase 29 register, every production/public/release
surface, and the finalized Phase 51-60 route. Its only existing-file
compatibility changes are the four Phase 50 tests named in the exact Slice 5
allowlist, limited to current status, completed/current scope separation, exact
dirty-set compatibility, and the protected-path exception required by that
exact set.

Slice 6 preserves every surface above, the roadmap, all completed Slice 1-5
specs, the historical Phase 29 register, all Phase 44-49 artifacts, every
production/public/release surface, and the finalized Phase 51-60 route. Its
only existing-file compatibility changes are the five Phase 50 tests named in
the exact Slice 6 allowlist, limited to current status, completed/current scope
separation, exact dirty-set compatibility, and exact protected-path exceptions.

Slice 7 preserves every surface above, the roadmap, all completed Slice 1-6
specs, the historical Phase 29 register, all Phase 44-49 artifacts, every
production/public/release surface, and the finalized Phase 51-60 route. Its
only existing-file compatibility changes are the six Phase 50 tests named in
the exact Slice 7 allowlist, limited to current status, completed/current scope
separation, exact dirty-set compatibility, and exact protected-path exceptions.
No production package, module, profile, catalog, manager, public metadata, or
runtime surface is approved.

Slice 8 preserves every surface above, the roadmap, all completed Slice 1-7
specs, the historical Phase 29 register, all Phase 44-49 artifacts, every
production/public/release surface, and the finalized Phase 51-60 route. Its
only existing-file compatibility changes are the seven Phase 50 tests named in
the exact Slice 8 allowlist, limited to mutable current status, completed/
current scope separation, exact dirty-set compatibility, exact protected-path
exceptions, and exact shared allowlist confirmation. No production extension,
profile, catalog, capability, package, public metadata, database, or runtime
surface is approved.

Slice 9 preserves every surface above, the roadmap, all completed Slice 1-8
specs, the historical Phase 29 register, all Phase 44-49 artifacts, every
production/public/release surface, and the finalized Phase 51-60 route. Its
only existing-file compatibility changes are the eight completed Phase 50
tests named in the exact Slice 9 allowlist, limited to current status, exact
eleven-file dirty-set compatibility, exact protected-path exceptions, and
shared allowlist confirmation. No profile, checker, backend, connector,
catalog, package, public metadata, database, or runtime surface is approved.

Slice 10 preserves every surface above, the roadmap, all completed Slice 1-9
specs, the historical Phase 29 register, all Phase 44-49 artifacts, every
production/public/release surface, and the finalized Phase 51-60 route. Its
only existing-file compatibility changes are the nine completed Phase 50 tests
named in the exact Slice 10 allowlist, limited to current status, exact
twelve-file dirty-set compatibility, exact protected-path exceptions, current
trusted-baseline facts, and shared allowlist confirmation. The new Slice 10
spec/test define no public surface and do not alter an existing public artifact.
No profile, catalog, package loader, checker, graph, public report, database,
or runtime surface is approved.

Slice 11 preserves every surface above, the roadmap, historical Phase 29
register, every completed Slice 1-10 specification, all Phase 44-49 artifacts,
every production/public/release surface, and the finalized Phase 51-60 route.
Its only existing-file compatibility changes are the ten completed Phase 50
tests named in the exact Slice 11 allowlist. They are limited to current
status, exact thirteen-file dirty-set compatibility, exact protected-path
exceptions, and shared allowlist confirmation while preserving every
historical Slice 1-10 allowlist. The new Slice 11 spec/test add no compiler,
runtime, public artifact, package, release, or later-phase behavior.

## Package, Version, And Release Boundary

Package version remains `0.1.0`. Slices 1 through 10 performed no package
version change, tag, release, publish, upload, signing, or attestation. Slice
11 Gate 2 performs no package version change, tag, release, publish, upload,
signing, attestation, CI trigger, CI rerun, CI watch, or CI cancellation. Gate
2 does not stage, commit, push, or prepare Gate 3. CLI JSON, Artifact, Project
JSON, future project-explain, portability-report, package-inspection, dialect,
profile, overlay, backend, catalog, semantic-package, server, and schema
versions are distinct facts and do not change the Python distribution version.

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

## Slice 5 Gate 2 Allowlist

Phase 50 Slice 5 Gate 2 is limited to exactly:

- `docs/plan/phase-50-semantic-readiness-consolidation.md`;
- `docs/spec/phase50-window-function-readiness-v1.md`;
- `tests/test_phase50_window_function_readiness.py`;
- `tests/test_phase50_semantic_package_extension_capability_scope_lock.py`;
- `tests/test_phase50_post_v02_deferred_readiness_inventory.py`;
- `tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py`;
- `tests/test_phase50_type_system_gap_capability_readiness.py`.

The final four paths are approved only for narrow current-status,
completed/current scope separation, exact dirty-set compatibility, and the
protected-path exception required by this exact Slice 5 dirty set. No eighth
repository path is approved. Nothing may be staged, committed, pushed, or
operated through CI in Gate 2.

## Slice 5 Focused Validation

Slice 5 Gate 2 validation is limited to:

- exact baseline, seven-file dirty-set, staged-set, and whitespace checks;
- no-index whitespace checks for the two new files;
- Ruff format/check and lint for all five changed Python tests;
- test-project Pyright;
- the focused Slice 5 static test;
- complete execution of all five Phase 50 test files;
- the exact parser/window-absence and aggregate/group/order/let evidence nodes;
- the historical Phase 29 register and exact selected Phase 30, 36, 38, 41,
  and 42 type/capability evidence nodes;
- the exact selected Phase 47-49 project schema/dependency/lineage nodes;
- history-independence, protected-surface, version, tag, and staged-set checks;
  and
- `/tmp/phase50-slice5-gate2-evidence-and-diff.txt` with complete tracked and
  no-index diffs and full changed Python test contents.

Do not run full pytest, `scripts/validate.py`, generated checks, golden checks,
package smoke, builds, benchmarks, dependency operations, network commands,
GitHub CLI, or CI. Once the first Ruff formatting command begins, a failure is
a stop condition and does not authorize repair.

## Slice 5 Stop Conditions

Stop without repair or scope expansion if:

- the completed Slice 4 baseline or exact seven-file dirty set differs;
- any eighth repository path changes;
- the roadmap, Phase 29 register, completed Slice 1-4 specs, finalized route,
  production/public surface, or release surface changes;
- generic call syntax would need to be described as window support;
- ordinary aggregate behavior would need to be described as
  aggregate-as-window support;
- a production window carrier, new diagnostic, concrete Phase 53
  implementation, or finalized-route change appears necessary;
- a compatibility edit weakens a meaningful historical lock or requires parent
  history, runtime `/tmp` evidence, network, GitHub, or executed-source access;
- Slice 6, Phase 52, or Phase 53 work appears necessary;
- a no-index check emits a whitespace diagnostic; or
- Ruff, Pyright, focused Slice 5 pytest, complete Phase 50 pytest, or an exact
  evidence node fails.

## Slice 6 Gate 2 Allowlist

Phase 50 Slice 6 Gate 2 is limited to exactly:

- `docs/plan/phase-50-semantic-readiness-consolidation.md`;
- `docs/spec/phase50-import-module-export-readiness-v1.md`;
- `tests/test_phase50_import_module_export_readiness.py`;
- `tests/test_phase50_semantic_package_extension_capability_scope_lock.py`;
- `tests/test_phase50_post_v02_deferred_readiness_inventory.py`;
- `tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py`;
- `tests/test_phase50_type_system_gap_capability_readiness.py`;
- `tests/test_phase50_window_function_readiness.py`.

The final five paths are approved only for narrow current-status,
completed/current scope separation, exact dirty-set compatibility, and exact
protected-path exceptions required by this eight-file dirty set. No ninth
repository path is approved. Nothing may be staged, committed, pushed, or
operated through CI in Gate 2.

## Slice 6 Focused Validation

Slice 6 Gate 2 validation is limited to:

- exact baseline, eight-file dirty-set, staged-set, and whitespace checks;
- no-index whitespace checks for the two new files;
- Ruff format/check and lint for all six changed Python tests;
- test-project Pyright;
- the focused Slice 6 static test;
- complete execution of all six Phase 50 test files;
- the exact Phase 44 project input/path evidence nodes;
- the exact Phase 45 namespace/resolution/diagnostic evidence nodes;
- the exact Phase 46 graph/cycle evidence nodes;
- the exact Phase 47-49 privacy and historical-deferral evidence nodes;
- history/network/import-execution, protected-surface, Phase 44-49, version,
  tag, and staged-set checks; and
- `/tmp/phase50-slice6-gate2-evidence-and-diff.txt` with complete tracked and
  no-index diffs and full changed Python test contents.

Do not run full pytest, `scripts/validate.py`, generated checks, golden checks,
package smoke, builds, benchmarks, dependency operations, network commands,
GitHub CLI, or CI. Once the first Ruff formatting command begins, a failure is
a stop condition and does not authorize repair.

## Slice 6 Stop Conditions

Stop without repair or scope expansion if:

- the completed Slice 5 baseline or exact eight-file dirty set differs;
- any ninth repository path changes;
- the roadmap, Phase 29 register, completed Slice 1-5 specs, Phase 44-49
  artifacts, finalized route, production/public surface, or release surface
  changes;
- current flat/global behavior would need to change or a current file would
  need to become a module;
- Route D cannot remain readiness-only and additive;
- a grammar, AST, resolver, carrier, filesystem change, visibility behavior,
  diagnostic, public metadata field, package identity/resolution, or Phase 54
  implementation appears necessary;
- a compatibility edit weakens a meaningful historical lock or requires parent
  history, runtime `/tmp` evidence, network, GitHub, import execution,
  `exec`, or `eval`;
- Slice 7 or Phase 52-55 work appears necessary;
- a no-index check emits a whitespace diagnostic; or
- Ruff, Pyright, focused Slice 6 pytest, complete Phase 50 pytest, or an exact
  evidence node fails.

## Slice 7 Gate 2 Allowlist

Phase 50 Slice 7 Gate 2 is limited to exactly:

- `docs/plan/phase-50-semantic-readiness-consolidation.md`;
- `docs/spec/phase50-semantic-package-model-readiness-v1.md`;
- `tests/test_phase50_semantic_package_model_readiness.py`;
- `tests/test_phase50_semantic_package_extension_capability_scope_lock.py`;
- `tests/test_phase50_post_v02_deferred_readiness_inventory.py`;
- `tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py`;
- `tests/test_phase50_type_system_gap_capability_readiness.py`;
- `tests/test_phase50_window_function_readiness.py`;
- `tests/test_phase50_import_module_export_readiness.py`.

The six completed Phase 50 tests are approved only for narrow current-status,
completed/current scope separation, exact dirty-set compatibility, and exact
protected-path exceptions required by this nine-file dirty set. No tenth
repository path is approved. Nothing may be staged, committed, pushed, or
operated through CI in Gate 2.

## Slice 7 Focused Validation

Slice 7 Gate 2 validation is limited to:

- exact baseline, nine-file dirty-set, staged-set, and whitespace checks;
- no-index whitespace checks for the two new files;
- Ruff format/check and lint for all seven changed Python tests;
- test-project Pyright;
- the focused Slice 7 static test;
- complete execution of all seven Phase 50 test files;
- the exact package/module/capability evidence nodes;
- the exact dependency/provenance/lineage/privacy and historical-deferral
  evidence nodes;
- history/network/import-execution, protected-surface, Phase 44-49, version,
  tag, and staged-set checks; and
- `/tmp/phase50-slice7-gate2-evidence-and-diff.txt` with complete tracked and
  no-index diffs and full changed Python test contents.

Do not run full pytest, `scripts/validate.py`, generated checks, golden checks,
package smoke, builds, benchmarks, dependency operations, network commands,
GitHub CLI, or CI. Once the first Ruff formatting command begins, a failure is
a stop condition and does not authorize repair.

## Slice 7 Stop Conditions

Stop without repair or scope expansion if:

- the completed Slice 6 baseline or exact nine-file dirty set differs;
- any tenth repository path changes;
- the roadmap, Phase 29 register, completed Slice 1-6 specs, Phase 44-49
  artifacts, finalized route, production/public surface, or release surface
  changes;
- current semantic-package absence, Python distribution separation, or
  project-local module separation cannot remain accurate;
- Route B cannot remain readiness-only, static, deterministic, declarative,
  and non-executable;
- a grammar, AST, parser, loader, resolver, carrier, graph, diagnostic, public
  field, project/module behavior change, profile/catalog schema, package
  manager, or Phase 55 implementation appears necessary;
- a compatibility edit weakens a meaningful historical lock or requires parent
  history, runtime `/tmp` evidence, network, GitHub, import execution, `exec`,
  or `eval`;
- Slice 8 or Phase 52-55 implementation appears necessary;
- a no-index check emits a whitespace diagnostic; or
- Ruff, Pyright, focused Slice 7 pytest, complete Phase 50 pytest, or an exact
  evidence node fails.

## Slice 8 Gate 2 Allowlist

Phase 50 Slice 8 Gate 2 is limited to exactly:

- `docs/plan/phase-50-semantic-readiness-consolidation.md`;
- `docs/spec/phase50-postgresql-extension-capability-readiness-v1.md`;
- `tests/test_phase50_postgresql_extension_capability_readiness.py`;
- `tests/test_phase50_semantic_package_extension_capability_scope_lock.py`;
- `tests/test_phase50_post_v02_deferred_readiness_inventory.py`;
- `tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py`;
- `tests/test_phase50_type_system_gap_capability_readiness.py`;
- `tests/test_phase50_window_function_readiness.py`;
- `tests/test_phase50_import_module_export_readiness.py`;
- `tests/test_phase50_semantic_package_model_readiness.py`.

The seven completed Phase 50 tests are approved only for narrow mutable
current-status, completed/current scope separation, exact dirty-set
compatibility, exact protected-path exceptions, and exact Slice 8 allowlist
confirmation. No eleventh repository path is approved. Nothing may be staged,
committed, pushed, or operated through CI in Gate 2.

## Slice 8 Focused Validation

Slice 8 Gate 2 validation is limited to:

- exact baseline, ten-file dirty-set, staged-set, and whitespace checks;
- no-index whitespace checks for the two new files;
- Ruff format/check and lint for all eight changed Python tests;
- test-project Pyright;
- the focused Slice 8 static test;
- complete execution of all eight Phase 50 test files;
- the exact approved Phase 9 PostgreSQL connector/backend contract nodes;
- the exact approved Phase 30/42 type/operator/aggregate nodes;
- the exact approved Phase 36/47/49 public-schema/privacy nodes;
- history/network/database/import-execution zero-match scans;
- protected-surface, Phase 44-49, version, tag, and staged-set checks; and
- `/tmp/phase50-slice8-gate2-evidence-and-diff.txt` with complete tracked and
  no-index diffs and full contents of all eight changed Python tests.

Do not run full pytest, `scripts/validate.py`, generated checks, golden checks,
package smoke, builds, benchmarks, dependency operations, network commands,
GitHub CLI, PostgreSQL, database commands, or CI. Once the first Ruff
formatting command begins, a failure is a stop condition and does not authorize
repair.

## Slice 8 Stop Conditions

Stop without repair or scope expansion if:

- the completed Slice 7 baseline or exact ten-file dirty set differs;
- any eleventh repository path changes;
- the roadmap, Phase 29 register, completed Slice 1-7 specs, Phase 44-49
  artifacts, finalized route, production/public surface, or release surface
  changes;
- current bounded PostgreSQL behavior or extension absence cannot remain
  accurate;
- Route B cannot remain static, strongly typed, deterministic, reviewable, and
  non-executable;
- the base profile cannot remain immutable or an overlay must replace another
  capability;
- a concrete signature, production profile/catalog/capability carrier,
  diagnostic, public field, connection, introspection, discovery, installation,
  runtime/database behavior, or Phase 57 implementation appears necessary;
- a compatibility edit weakens a meaningful historical lock or requires parent
  history, runtime `/tmp` evidence, network, GitHub, PostgreSQL, database,
  import execution, `exec`, or `eval`;
- Slice 9 or Phase 52-57 implementation appears necessary;
- a no-index check emits a whitespace diagnostic; or
- Ruff, Pyright, focused Slice 8 pytest, complete Phase 50 pytest, or an exact
  evidence node fails.

## Slice 9 Gate 2 Allowlist

Phase 50 Slice 9 Gate 2 is limited to exactly:

- `docs/plan/phase-50-semantic-readiness-consolidation.md`;
- `docs/spec/phase50-multi-dialect-capability-ecosystem-readiness-v1.md`;
- `tests/test_phase50_multi_dialect_capability_ecosystem_readiness.py`;
- `tests/test_phase50_semantic_package_extension_capability_scope_lock.py`;
- `tests/test_phase50_post_v02_deferred_readiness_inventory.py`;
- `tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py`;
- `tests/test_phase50_type_system_gap_capability_readiness.py`;
- `tests/test_phase50_window_function_readiness.py`;
- `tests/test_phase50_import_module_export_readiness.py`;
- `tests/test_phase50_semantic_package_model_readiness.py`; and
- `tests/test_phase50_postgresql_extension_capability_readiness.py`.

The eight completed Phase 50 tests are approved only for narrow mutable plan
status, historical/current scope separation, exact eleven-file dirty-set
compatibility, exact protected-path exceptions, and exact shared allowlist
confirmation. No twelfth repository path is approved. Nothing may be staged,
committed, pushed, or operated through CI in Gate 2.

## Slice 9 Focused Validation

Slice 9 Gate 2 validation is limited to:

- exact baseline, eleven-file dirty-set, staged-set, diff, and whitespace
  checks;
- no-index whitespace checks for the two new files;
- Ruff format/check and lint for all nine changed Python tests;
- test-project Pyright;
- the focused Slice 9 static test and complete nine-file Phase 50 static-audit
  bundle;
- the exact extension/profile/package/route, PostgreSQL/MySQL backend,
  dispatch, connector, fail-closed, type/function/aggregate/operator, JSON,
  and privacy evidence nodes recorded in the Slice 9 Gate 1 report;
- prohibited history/network/database/import-execution zero-match scans;
- protected-surface, Phase 44-49, version, tag, tests/goldens, and staged-set
  checks; and
- `/tmp/phase50-slice9-gate2-evidence-and-diff.txt` with complete tracked and
  no-index diffs and full contents of all nine changed Python tests.

Do not run full pytest, `scripts/validate.py`, generated checks, golden checks,
package smoke, builds, benchmarks, dependency operations, network commands,
GitHub CLI, database commands, or CI. Once the first Ruff formatting command
begins, a failure is a stop condition and does not authorize repair.

## Slice 9 Stop Conditions

Stop without repair or scope expansion if:

- the completed Slice 8 baseline or exact eleven-file dirty set differs;
- any twelfth repository path changes;
- the roadmap, Phase 29 register, completed Slice 1-8 specs, Phase 44-49
  artifacts, finalized route, production/public surface, or release surface
  changes;
- current bounded PostgreSQL/MySQL behavior, SQLite rejection posture, or
  NOT_EVIDENCED example boundary cannot remain accurate;
- Route B cannot remain static, strongly typed, deterministic, reviewable,
  declarative, and non-executable;
- a profile schema/checker, carrier, backend, connector, catalog, diagnostic,
  public field, connection, introspection, template, plugin, runtime/database
  behavior, Phase 56 implementation, or Phase 60 behavior appears necessary;
- a compatibility edit weakens a meaningful historical lock or requires parent
  history, runtime evidence, network, GitHub, database, import execution,
  `exec`, or `eval`;
- a no-index check emits a whitespace diagnostic; or
- Ruff, Pyright, focused Slice 9 pytest, complete Phase 50 pytest, or an exact
  evidence node fails.

## Slice 10 Gate 2 Allowlist

Phase 50 Slice 10 Gate 2 is limited to exactly:

- `docs/plan/phase-50-semantic-readiness-consolidation.md`;
- `docs/spec/phase50-explain-public-metadata-package-integration-boundary-v1.md`;
- `tests/test_phase50_explain_public_metadata_package_integration_boundary.py`;
- `tests/test_phase50_semantic_package_extension_capability_scope_lock.py`;
- `tests/test_phase50_post_v02_deferred_readiness_inventory.py`;
- `tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py`;
- `tests/test_phase50_type_system_gap_capability_readiness.py`;
- `tests/test_phase50_window_function_readiness.py`;
- `tests/test_phase50_import_module_export_readiness.py`;
- `tests/test_phase50_semantic_package_model_readiness.py`;
- `tests/test_phase50_postgresql_extension_capability_readiness.py`; and
- `tests/test_phase50_multi_dialect_capability_ecosystem_readiness.py`.

The nine completed Phase 50 tests are approved only for narrow mutable plan
status, current trusted-baseline facts, historical/current scope separation,
exact twelve-file dirty-set compatibility, exact protected-path exceptions, and
exact shared allowlist confirmation. Every historical Slice 1-9 allowlist
remains exact. No thirteenth repository path is approved. Nothing may be
staged, committed, pushed, or operated through CI in Gate 2.

## Slice 10 Focused Validation

Slice 10 Gate 2 validation is limited to:

- exact Slice 9 baseline, twelve-file dirty-set, cached-diff, staged-set,
  diff, and whitespace checks;
- no-index whitespace checks for the two new files;
- Ruff format/check and lint for the ten changed Python tests;
- test-project Pyright;
- the focused Slice 10 static test and complete ten-file Phase 50 static-audit
  bundle;
- the exact CLI JSON v1, single-file explain, Semantic Metadata Artifact v1,
  Project JSON v2, Phase 45-49 privacy/lineage, and
  package/profile/extension/dialect readiness nodes recorded in the Slice 10
  Gate 1 plan;
- the corrected no-history/no-network/no-database/no-import-execution scan and
  the two Git-mutation zero-match scans recorded in the Slice 10 Gate 1
  addendum;
- protected-surface, Phase 44-49, version, tag, tests/goldens, and staged-set
  checks; and
- `/tmp/phase50-slice10-gate2-evidence-and-diff.txt` with complete tracked and
  no-index diffs and full contents of all ten changed Python tests.

The focused static test may use `subprocess.run(["git", *args], ...)` only for
the local read-only `status`, `diff`, cached-diff, and
`tag --points-at HEAD` operations locked by the Slice 10 Gate 1 addendum. It
must not use parent/history-dependent Git commands, shell execution, mutation,
network/GitHub, database, `/tmp` evidence, or production-module execution.

Do not run full pytest, `scripts/validate.py`, generated checks, golden checks,
package smoke, builds, benchmarks, dependency operations, network commands,
GitHub CLI, database commands, or CI. Once the first Ruff formatting command
begins, a failure is a stop condition and does not authorize repair.

## Slice 10 Stop Conditions

Stop without repair or scope expansion if:

- the completed Slice 9 baseline or exact twelve-file dirty set differs;
- any thirteenth repository path changes;
- the roadmap, Phase 29 register, completed Slice 1-9 specs, Phase 44-49
  artifacts, finalized route, production/public surface, or release surface
  changes;
- CLI JSON v1, Semantic Metadata Artifact v1, Project JSON v2 check, current
  single-file explain, or bounded PostgreSQL/MySQL posture cannot remain
  accurate;
- Route B, artifact separation, private-carrier privacy, independent schema
  versioning, deterministic ordering, or fail-closed posture cannot remain
  accurate;
- a serializer, CLI option, public field, package/profile/catalog loader,
  checker, graph, diagnostic, backend, connection, introspection, plugin,
  runtime/database behavior, Phase 58/59 implementation, or release action
  appears necessary;
- a compatibility edit weakens a meaningful historical lock or requires parent
  history, runtime evidence, network, GitHub, database, import execution,
  `exec`, or `eval`;
- a no-index check emits a whitespace diagnostic; or
- Ruff, Pyright, focused Slice 10 pytest, complete Phase 50 pytest, or an
  exact evidence node fails.

## Slice 11 Gate 2 Allowlist

Phase 50 Slice 11 Gate 2 is limited to exactly:

- `docs/plan/phase-50-semantic-readiness-consolidation.md`;
- `docs/spec/phase50-completion-audit-and-status-lock-v1.md`;
- `tests/test_phase50_completion_audit_and_status_lock.py`;
- `tests/test_phase50_semantic_package_extension_capability_scope_lock.py`;
- `tests/test_phase50_post_v02_deferred_readiness_inventory.py`;
- `tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py`;
- `tests/test_phase50_type_system_gap_capability_readiness.py`;
- `tests/test_phase50_window_function_readiness.py`;
- `tests/test_phase50_import_module_export_readiness.py`;
- `tests/test_phase50_semantic_package_model_readiness.py`;
- `tests/test_phase50_postgresql_extension_capability_readiness.py`;
- `tests/test_phase50_multi_dialect_capability_ecosystem_readiness.py`; and
- `tests/test_phase50_explain_public_metadata_package_integration_boundary.py`.

The ten completed Phase 50 tests are approved only for narrow current-status,
exact thirteen-file dirty-set compatibility, exact protected-path exceptions,
and shared Slice 11 allowlist confirmation. Every historical Slice 1-10
allowlist remains exact. No fourteenth repository path is approved. Nothing
may be staged, committed, pushed, or operated through CI in Gate 2.

## Slice 11 Focused Validation

Slice 11 Gate 2 validation is limited to:

- exact Slice 10 baseline, thirteen-file dirty set, empty staged set, diff,
  stat, numstat, and whitespace checks;
- no-index whitespace checks for the two new files;
- Ruff format/check and lint for all eleven changed Python tests;
- test-project Pyright;
- the focused Slice 11 static test and complete eleven-file Phase 50
  static-audit bundle;
- exact Slice 1-10 ledger, route, historical-allowlist, aggregate, type,
  window, module, package, profile, extension, dialect, public-artifact,
  Phase 45-49 privacy/lineage, completion-encoding, future-phase, package,
  release, and CI-policy nodes recorded in the Slice 11 Gate 1 plan;
- the prohibited history/network/database/import-execution scan and both
  Git-mutation zero-match scans;
- protected production/public/release, Phase 44-49, completed Slice 1-10
  specification, public-artifact, version, tag, tests/goldens, and staged-set
  checks; and
- `/tmp/phase50-slice11-gate2-evidence-and-diff.txt` with raw outputs,
  complete tracked and no-index diffs, and full contents of all eleven changed
  Python tests.

The focused static test may use `subprocess.run(["git", *args], ...)` only
for local read-only `status --porcelain --untracked-files=all`, protected-path
`diff`, cached-diff, and `tag --points-at HEAD` operations. It must not use
parent/history-dependent Git, shell execution, mutation, network/GitHub, CI,
database, `/tmp` evidence, or production-module execution.

Do not run full pytest, `scripts/validate.py`, generated checks, golden
checks, package smoke, builds, benchmarks, dependency operations, network
commands, GitHub CLI, database commands, or CI. Once the first Ruff formatting
command begins, a failure is a stop condition and does not authorize repair.

## Slice 11 Stop Conditions

Stop without repair or scope expansion if:

- the completed Slice 10 baseline or exact thirteen-file dirty set differs;
- any fourteenth repository path changes;
- a historical Slice 1-10 allowlist changes;
- the roadmap, Phase 29 register, completed Slice 1-10 specifications, Phase
  44-49 artifacts, finalized route, production/public surface, or release
  surface changes;
- the conditional single-commit completion model cannot remain exact;
- Gate 2 text pre-claims a Slice 11 SHA, push, natural CI run/result, or Phase
  50 completion;
- CLI JSON v1, Semantic Metadata Artifact v1, Project JSON v2, current
  single-file explain, PostgreSQL public/MySQL private posture, or private
  carrier privacy cannot remain unchanged;
- a compiler/runtime behavior, public field, package/profile/catalog loader,
  checker, graph, diagnostic, backend, connection, introspection, plugin,
  runtime/database behavior, release action, or Phase 51-60 implementation
  appears necessary;
- a compatibility edit weakens a historical lock or requires parent history,
  runtime evidence, network, GitHub, database, import execution, `exec`, or
  `eval`;
- a no-index check emits a whitespace diagnostic;
- Ruff, Pyright, focused Slice 11 pytest, complete Phase 50 pytest, named
  compatibility pytest, or a zero-match scan fails;
- the cached diff becomes non-empty, package version differs from `0.1.0`, a
  tag appears, or `tests/goldens` appears; or
- complete evidence cannot be captured without widening scope.

## Stop Conditions

Stop without repair or scope expansion if:

- the completed Slice 10 baseline or exact thirteen-file Slice 11 dirty set
  differs;
- any fourteenth repository path changes;
- the historical roadmap table or v0.2 register requires modification;
- any production/public/release surface appears necessary;
- a no-index check emits a whitespace diagnostic;
- Ruff, Pyright, focused pytest, or compatibility pytest fails; or
- the final diff cannot prove the Slice 11 no-behavior and conditional
  completion boundaries.
