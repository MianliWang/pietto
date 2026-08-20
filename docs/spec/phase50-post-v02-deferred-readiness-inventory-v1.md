# Phase 50 Slice 2 Post-v0.2 Deferred Readiness Inventory And Phase 51-60 Route v1

## Purpose And Authority

Phase 50 Slice 2 is **Post-v0.2 Deferred Inventory And Phase 50-60 Replan**.
Slice 2 is classificatory and sequencing-only. It records current post-v0.2
evidence and finalizes the active planning order for future gates.

Slice 2 implements no compiler or runtime behavior. It adds no parser, AST,
semantic, IR, SQL, CLI, JSON, diagnostic, backend, package-resolution,
extension, public-surface, runtime, or database behavior.

Slice 2 is not complete until a separately authorized Gate 3 commits and pushes
the exact Slice 2 files and the exact natural CI run succeeds. The finalized
active planning route becomes effective only after Slice 2 Gate 3. Listing a
capability or phase is not implementation authorization, automatic phase start,
automatic completion, an irreversible product commitment, a public API promise,
a release commitment, or runtime/database authorization. Every later phase
requires separate authorization.

## Trusted Baseline

The trusted Slice 2 baseline is:

- branch `main`;
- HEAD and local `origin/main`
  `85066d4a7088af82a308ca751763a4e6a10baa52`;
- subject `Add Phase 50 readiness consolidation scope lock`;
- documented natural CI run `29068556545`;
- workflow/event `CI / push`;
- documented status/conclusion `completed / success`;
- documented CI `headSha` exactly matching the baseline;
- package version `0.1.0`; and
- no tag at HEAD and no exact-match tag.

The CI facts are local Gate evidence. Gate 2 performs no network or GitHub
query.

## Historical v0.2 Register Boundary

`docs/roadmap.md` is the historical Phase 29 v0.2
boundary register. The historical Phase 29 register remains byte-for-byte
unchanged.

This inventory supersedes the historical register only for current post-v0.2
classification, not for historical Phase 29 meaning. Broad historical rows may
split into layer-specific entries because later phases implemented bounded
subsets while preserving other deferrals. The historical row, target, and
allowed-before-v0.2 decision remain historical evidence.

The historical Roadmap Tree in
`docs/roadmap.md` remains preserved. Slice 2 adds an
append-only active-route reconciliation and does not retroactively rewrite the
completed Slice 1 tentative route.

## Status Vocabulary

These seven tokens are local to this inventory. They do not replace, rename, or
reinterpret existing Semantic Metadata Artifact `support_posture` values such
as `current`, `limited_frozen`, `deferred_builtin`, `metadata_only`, or
`unknown`.

### IMPLEMENTED_STABLE

The precisely named public or compiler surface is implemented and locked as a
stable current contract. It does not imply adjacent capabilities are stable.

### IMPLEMENTED_LIMITED

Behavior exists only for an explicitly bounded subset, layer, dialect, command,
or type surface. Every use must state the exact limit.

### PRIVATE_FOUNDATION

Internal implementation or tested carriers exist, but they are not public API,
public JSON, project explain, metadata export, IR/SQL behavior, runtime, or
database behavior.

### READINESS_CONTRACT_ONLY

Plans, specifications, matrices, or static tests exist, but corresponding
implementation behavior was not authorized.

### EXPLICITLY_DEFERRED

Current authoritative evidence explicitly defers the named capability or
remaining layer.

### OUT_OF_SCOPE

The capability is outside Phase 50 and the finalized Phase 51-60 route, or is a
current Pietto non-goal absent separate explicit authorization.

### NOT_EVIDENCED

No authoritative repository evidence was found for the precise proposed
capability. This does not mean it can never exist.

## Evidence Rules

Use this evidence hierarchy:

1. completed phase completion audits and final status locks;
2. completed implementation tests and current source facts referenced by them;
3. current phase-specific scope locks, matrices, and contracts;
4. Phase 50 Slice 1 artifacts;
5. historical Phase 29 register and historical roadmap;
6. local Gate evidence;
7. approved current strategy; and
8. planning inference.

Completion audits override old candidate plans. Current source may prove an
implementation layer but does not widen a public contract. Private carriers
must never be described as public output. Readiness contracts must never be
described as behavior. A bounded implemented surface must not be described as
wholly unimplemented merely because adjacent work remains deferred.

Broad historical rows may split into layer-specific current rows. User strategy
without repository evidence receives the no-evidence classification. An absence
search proves only that current evidence was not found.

Evidence strength uses `COMPLETION_AUDIT`, `IMPLEMENTATION_TEST`,
`CURRENT_SOURCE`, `CONTRACT`, `HISTORICAL`, and `USER_STRATEGY_ONLY`. This
document is Markdown evidence, not a machine-readable schema.

## Aggregate And Grouped Schema Inventory

Current aggregate behavior is bounded single-file compiler behavior. Project row
facts are private. Aggregate/grouped project output ownership is a future
private foundation, not current public metadata or SQL behavior.

| Feature / exact layer | Status | Strongest evidence | Boundary and remaining work | Prerequisite | Owner | Owner mode | Explicit exclusions | Strength |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Current single-file aggregate surface | IMPLEMENTED_LIMITED | `tests/test_phase37_completion_audit.py` | Frozen accepted count, count_distinct, sum, avg, min, max, grouped, satisfying, and grouped-order subsets | Existing semantic/IR/SQL matrix | completed | bounded behavior | No project schema claim | COMPLETION_AUDIT |
| Narrow field-bearing `count(expression)` | IMPLEMENTED_LIMITED | `tests/test_phase39_completion_audit.py` | Supported field-bearing expressions only; literal-only count and count_if remain absent | Current expression typing | completed | bounded behavior | No generic constant count | COMPLETION_AUDIT |
| Selected row-let aggregate/group interactions | IMPLEMENTED_LIMITED | `tests/test_phase43_completion_audit.py` | Direct approved aggregate, group-key, grouped-order, and satisfying forms only | Phase 40 row lets | completed | bounded behavior | No arbitrary expressions, min/max, or limit-let | COMPLETION_AUDIT |
| Phase 47-49 direct, propagated, computed, and let project row facts | PRIVATE_FOUNDATION | `docs/project-package.md` | Private schemas, states, dependencies, origin, and lineage; aggregate/grouped facts absent | Completed Phase 47-49 carriers | Phase 51 input | private prerequisite | No Project JSON or public API | COMPLETION_AUDIT |
| Aggregate/grouped project output schema | EXPLICITLY_DEFERRED | `tests/test_phase47_completion_audit.py` | Add bounded private group-key and aggregate output facts | Current canonical expression types | Phase 51 | bounded candidate | No type widening, public JSON, IR, SQL, or CLI | COMPLETION_AUDIT |
| Aggregate/grouped origin and lineage | EXPLICITLY_DEFERRED | `docs/project-package.md` | Add private origin, dependency, and lineage after schema ownership | Aggregate/grouped schema facts | Phase 51 | private candidate | No public lineage/export | COMPLETION_AUDIT |
| Aggregate/grouped duplicate output plus satisfying/order/limit schema effects | EXPLICITLY_DEFERRED | `tests/test_phase47_completion_audit.py` | Define fail-closed private states and deterministic ownership | Phase 48 state vocabulary | Phase 51 | contract then private candidate | No new diagnostics or aggregate behavior | COMPLETION_AUDIT |
| `count_if`, aggregate filters, and ordered aggregates | EXPLICITLY_DEFERRED | `docs/spec/phase37-aggregate-filter-distinct-modifier-deferral-v1.md` | Requires separate syntax, typing, IR, dialect, and compatibility contracts | Later aggregate decision | OUTSIDE_51_60 | future replan | No FILTER or WITHIN GROUP inference | CONTRACT |
| Generic DISTINCT and broad aggregate expression widening | EXPLICITLY_DEFERRED | `tests/test_phase37_completion_audit.py` | Existing direct/lower-trim and bounded expression forms only | Aggregate capability decisions | OUTSIDE_51_60 | future replan | No generic modifier syntax | COMPLETION_AUDIT |
| Rollup, cube, and grouping sets | EXPLICITLY_DEFERRED | `docs/spec/v02-aggregate-surface-freeze-v1.md` | No current compiler surface | Later grouped model | OUTSIDE_51_60 | future replan | No automatic SQL adoption | CONTRACT |

## Type-System Inventory

Current type behavior combines bounded postures, private precision facts, and
readiness matrices. Each row names its exact layer.

| Feature / exact layer | Status | Strongest evidence | Boundary and remaining work | Prerequisite | Owner | Owner mode | Explicit exclusions | Strength |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| UUID | IMPLEMENTED_LIMITED | `docs/spec/uuid-support-completion-v1.md` | `limited_frozen` fields, projection, aliases, direct count, and direct count_distinct; literals/casts/native mapping absent | Capability decisions | Phase 52 | readiness | No full UUID scalar claim | CONTRACT |
| Enum | IMPLEMENTED_LIMITED | `tests/test_phase36_completion_audit.py` | Metadata/readiness exists; aggregates including count(Enum field) fail closed with PIE-S2314 | Enum capability contract | Phase 52 | readiness | No builtin-scalar or SQL claim | COMPLETION_AUDIT |
| Decimal(p,s) semantic validation | IMPLEMENTED_LIMITED | `tests/test_phase41_decimal_precision_scale_completion_audit.py` | PIE-S2004 validates supported type sites; public/native SQL precision absent | Phase 41 MVP | completed foundation | bounded semantics | No SQL DECIMAL(p,s) promise | COMPLETION_AUDIT |
| Private Decimal precision/scale facts | PRIVATE_FOUNDATION | `tests/test_phase42_completion_audit.py` | Private type-expression, alias, and direct-field facts; computed/aggregate fusion absent | Current Decimal carriers | Phase 52 | private foundation | No public fields or IR precision | COMPLETION_AUDIT |
| DateTime, Time, Interval, and timezone model | EXPLICITLY_DEFERRED | `tests/test_phase36_completion_audit.py` | Date and Timestamp remain current; portable primitives/arithmetic/timezone rules absent | Temporal contract | Phase 52 | readiness | No inferred aliases or SQL behavior | COMPLETION_AUDIT |
| Currency/Money and domain refinement | EXPLICITLY_DEFERRED | `tests/test_phase36_completion_audit.py` | Current aliases do not create refinement semantics | Type and syntax decisions | Phase 52 | readiness | No new primitive or annotation syntax | COMPLETION_AUDIT |
| Any, Bytes, and Json | IMPLEMENTED_LIMITED | `docs/spec/phase38-boundary-types-capability-contract-v1.md` | Field/projection and bounded shared/count paths; unsupported aggregates fail closed | Pair-specific capability contract | Phase 52 | readiness | No dynamic typing or runtime value model | CONTRACT |
| Current nullability propagation | IMPLEMENTED_LIMITED | `docs/spec/nullability-propagation-contract-v1.md` | Current semantic and private project facts only | Existing value/project carriers | Phase 52 | capability foundation | No runtime non-null proof | CONTRACT |
| Expanded pair-specific operator/capability matrix | READINESS_CONTRACT_ONLY | `docs/spec/operator-comparison-matrix-contract-v1.md` | Documents current, risky, and deferred pairs without adding behavior | Current operator behavior | Phase 52 | readiness contract | No operators, casts, or promotion widening | CONTRACT |
| Decimal computed/aggregate precision propagation | EXPLICITLY_DEFERRED | `tests/test_phase41_decimal_precision_scale_completion_audit.py` | Direct/private facts do not fuse through computed aggregates | Private Decimal facts | Phase 52 or later | bounded candidate | No implicit public precision | COMPLETION_AUDIT |
| Native database type mapping | EXPLICITLY_DEFERRED | `docs/roadmap.md` | No physical binding or native metadata | Stable capability profiles | OUTSIDE_51_60 | future replan | No introspection, DDL, or connector inference | HISTORICAL |

## Window-Function Inventory

The repository explicitly defers window functions. Slice 2 selects neither
syntax nor a function catalog.

| Feature / exact layer | Status | Strongest evidence | Boundary and remaining work | Prerequisite | Owner | Owner mode | Explicit exclusions | Strength |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| General window syntax and semantic surface | EXPLICITLY_DEFERRED | `tests/test_phase37_completion_audit.py` | Syntax, AST, typing, IR, SQL, diagnostics, and compatibility absent | Aggregate/type readiness | Phase 53 | readiness contract | No accepted window syntax | COMPLETION_AUDIT |
| OVER, PARTITION BY, window order, frames, and aggregate-as-window | EXPLICITLY_DEFERRED | `docs/roadmap.md` | Decision surface only | Phase 51-52 evidence | Phase 53 | readiness contract | No spelling reservation or lowering | CONTRACT |
| Window result type/nullability and grouped interaction | EXPLICITLY_DEFERRED | `docs/roadmap.md` | No current matrix | Phase 51-52 facts | Phase 53 | readiness contract | No result-schema behavior | CONTRACT |
| Window dialect capability and lowering | EXPLICITLY_DEFERRED | `docs/roadmap.md` | Backend support is not inferred | Phase 56 capability schema | Phase 53 and later | readiness contract | No best-effort SQL | CONTRACT |
| Exact catalog: row_number, rank, dense_rank, lag, lead, first_value, last_value | NOT_EVIDENCED | Slice 2 Gate 1 exact-term search | No authoritative exact catalog contract was found | Phase 53 evidence | Phase 53 | decision candidate | No catalog inferred from SQL familiarity | USER_STRATEGY_ONLY |
| Phase 53 implementation posture | READINESS_CONTRACT_ONLY | `docs/roadmap.md` | Syntax and capability contract only | Completed Phase 50 readiness | Phase 53 | readiness phase | No parser, AST, semantic, IR, or SQL change implied | CONTRACT |

## Project / Module / Package Inventory

The current project model is bounded project-check behavior with private
semantic facts and a flat cross-file namespace. Package terminology is static
and non-executable.

| Feature / exact layer | Status | Strongest evidence | Boundary and remaining work | Prerequisite | Owner | Owner mode | Explicit exclusions | Strength |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Multi-file project check, config, source selection, and flat namespaces | IMPLEMENTED_LIMITED | `tests/test_phase45_completion_audit.py` | Bounded project check and cross-file type/relation semantics; no project emit/explain/IR/SQL | Completed Phase 44-45 | completed foundation | bounded behavior | No general project compilation claim | COMPLETION_AUDIT |
| Deterministic project order and relation cycle diagnostics | IMPLEMENTED_LIMITED | `tests/test_phase46_completion_audit.py` | Deterministic input/symbol order and PIE-S2302 relation cycles; module cycles undefined | Private relation graph | completed foundation | bounded behavior | No module visibility behavior | COMPLETION_AUDIT |
| Private project catalog, graph, row schemas/states, dependencies, and lineage | PRIVATE_FOUNDATION | `docs/project-package.md` | Tested ProjectSemanticModel facts; package attribution/public metadata absent | Completed Phase 45-49 | Phase 51/59 input | private prerequisite | No public JSON, explain, IR, or SQL | COMPLETION_AUDIT |
| Import, module identity, export/private visibility, and qualified project names | EXPLICITLY_DEFERRED | `docs/project-package.md` | Current namespace remains flat | Current project catalog | Phase 54 | readiness | No executable import or loader widening | CONTRACT |
| Semantic package vocabulary and candidate assets | READINESS_CONTRACT_ONLY | `docs/project-package.md` | Static, declarative, reviewable, non-executable concepts only | Type/module readiness | Phase 55 | readiness contract | No manifest, resolver, or execution | CONTRACT |
| Semantic package asset schema | EXPLICITLY_DEFERRED | `docs/roadmap.md` | Candidate families are not schemas | Phase 52 and 54 | Phase 55 | schema contract | No loader or registry | CONTRACT |
| Package manifest, dependency graph, attribution integration, and versioning semantics | EXPLICITLY_DEFERRED | `docs/roadmap.md` | No manifest or package graph exists | Phase 55 asset schema | Phase 55/59 | readiness then private integration | No remote resolution or public export | CONTRACT |
| Registry, remote install, publishing, executable plugins/hooks, and arbitrary package code | OUT_OF_SCOPE | `docs/project-package.md` | Forbidden by current non-executable boundary | New safety authorization | OUTSIDE_51_60 | excluded | No network, install, hook, or code execution | CONTRACT |

## Extension And Dialect Capability Inventory

Backend support is not target-server extension capability. Existing backends
remain closed and explicit.

| Feature / exact layer | Status | Strongest evidence | Boundary and remaining work | Prerequisite | Owner | Owner mode | Explicit exclusions | Strength |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Handwritten PostgreSQL backend | IMPLEMENTED_STABLE | `tests/test_phase9_completion_audit.py` | Byte-exact current supported compiler surface | Existing backend contracts | completed | stable backend | No server-extension inference | COMPLETION_AUDIT |
| Closed private MySQL backend | IMPLEMENTED_LIMITED | `tests/test_phase10_completion_audit.py` | Private fail-closed emitter and bounded CLI selection | Existing closed matrix | completed | bounded backend | No generic public emitter | COMPLETION_AUDIT |
| SQLite, DuckDB, BigQuery, Snowflake, and Trino concrete backends | EXPLICITLY_DEFERRED | `docs/project-package.md` | Future examples only | Capability schema | OUTSIDE_51_60 | future replan | No accepted CLI dialect value | CONTRACT |
| Capability-profile and extension-overlay vocabulary | READINESS_CONTRACT_ONLY | `docs/project-package.md` | Static declared concepts only | Type/package readiness | Phase 56 | readiness contract | No server discovery or proof | CONTRACT |
| Declared capability checking | EXPLICITLY_DEFERRED | `docs/roadmap.md` | Conceptual pipeline only | Phase 56 static schema | Phase 56 | bounded candidate | No connector-name inference | CONTRACT |
| PostGIS, pgvector, pg_trgm, and TimescaleDB concrete support | EXPLICITLY_DEFERRED | `docs/project-package.md` | Catalog examples only | Phase 56 schema | Phase 57 | catalog readiness | No discovery, install, CREATE EXTENSION, or SQL behavior | CONTRACT |
| Custom extension signature schema | NOT_EVIDENCED | Slice 2 Gate 1 exact-term search | No authoritative exact schema contract was found | Phase 56-57 evidence | Phase 57 | decision candidate | No arbitrary user code or dynamic loading | USER_STRATEGY_ONLY |
| Portability diagnostics and capability mismatch output | EXPLICITLY_DEFERRED | `docs/roadmap.md` | Future reporting concepts only | Phase 56-57 contracts | Phase 58 | readiness/privacy contract | No new diagnostic in Phase 50 | CONTRACT |
| Phase 57 catalog posture | READINESS_CONTRACT_ONLY | `docs/roadmap.md` | Signature-catalog readiness only | Phase 56 | Phase 57 | readiness phase | No lowering or installation | CONTRACT |
| Phase 60 ecosystem posture | READINESS_CONTRACT_ONLY | `docs/roadmap.md` | Completion checkpoint only | Phases 51-59 | Phase 60 | checkpoint | No release or backend implementation | CONTRACT |

## Explain / Metadata / Lineage Inventory

Single-file explain is public at its exact v1 contract. Project metadata carriers
remain private.

| Feature / exact layer | Status | Strongest evidence | Boundary and remaining work | Prerequisite | Owner | Owner mode | Explicit exclusions | Strength |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Single-file `pietto explain` and Semantic Metadata Artifact v1 | IMPLEMENTED_STABLE | `tests/test_phase32_completion_audit.py` | Exact current text/JSON contract; project aggregation separate | Completed Phase 32 | completed | stable public command | No project metadata claim | COMPLETION_AUDIT |
| Project JSON v2 and project-check envelope | IMPLEMENTED_LIMITED | `tests/test_phase33_completion_audit.py` | Inputs, counters, diagnostics, cli_errors, and check result only | Completed Phase 33-46 | completed foundation | bounded public envelope | No private carrier serialization | COMPLETION_AUDIT |
| Project origin/provenance, dependency graphs, schema states, and multi-hop lineage | PRIVATE_FOUNDATION | `docs/project-package.md` | ProjectSemanticModel facts only | Completed Phase 46-49 | Phase 59 input | private prerequisite | No Project JSON or explain output | COMPLETION_AUDIT |
| Project explain, public project metadata, and public row schema | EXPLICITLY_DEFERRED | `docs/project-package.md` | Project explain unsupported and private schemas un-serialized | Phase 51 and 55-57 | Phase 58 | readiness/privacy contract | No immediate serializer or CLI behavior | COMPLETION_AUDIT |
| Public lineage/export and package attribution output | EXPLICITLY_DEFERRED | `docs/project-package.md` | Private lineage is not an export contract | Phase 59 private integration | Phase 58/59 | readiness then future replan | No bridge or public graph | COMPLETION_AUDIT |
| Portability report and capability mismatch metadata | EXPLICITLY_DEFERRED | `docs/roadmap.md` | Future reporting concepts only | Phase 56-57 | Phase 58 | readiness/privacy contract | No current output or diagnostic | CONTRACT |

## Relationship / Composition Inventory

Relationship metadata is bounded metadata. Query composition and project SQL
remain separate deferred surfaces.

| Feature / exact layer | Status | Strongest evidence | Boundary and remaining work | Prerequisite | Owner | Owner mode | Explicit exclusions | Strength |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Relationship metadata syntax, AST, semantic validation, and immutable storage | IMPLEMENTED_LIMITED | `tests/test_phase15_completion_audit.py` | Separate metadata namespace; no relation lookup, IR, or SQL participation | Completed Phase 14-15 | completed foundation | bounded metadata | No JOIN or endpoint-qualified lookup | COMPLETION_AUDIT |
| Grain and narrow JOIN contracts | READINESS_CONTRACT_ONLY | `tests/test_phase34_completion_audit.py` | Documentation/static-audit foundation only | Project/relationship evidence | OUTSIDE_51_60 | future replan | No JOIN implementation | COMPLETION_AUDIT |
| JOIN and relationship-driven query behavior | EXPLICITLY_DEFERRED | `tests/test_phase34_completion_audit.py` | No current query composition | Future relationship replan | OUTSIDE_51_60 | future replan | No automatic join inference | COMPLETION_AUDIT |
| Grain behavior, fanout diagnostics, and relationship-aware aggregate rewrites | EXPLICITLY_DEFERRED | `docs/language.md` | Readiness concepts only | JOIN semantics | OUTSIDE_51_60 | future replan | No BI-style inference | CONTRACT |
| Nested queries, derived tables, and CTE lowering | EXPLICITLY_DEFERRED | `docs/roadmap.md` | No hidden relation layer or subquery lowering | Future composition plan | OUTSIDE_51_60 | future replan | No hidden CTE insertion | HISTORICAL |
| Project IR, project SQL, and project emit-sql | EXPLICITLY_DEFERRED | `docs/project-package.md` | Project semantic facts do not feed IR/SQL | Private schema/composition readiness | OUTSIDE_51_60 | future replan | No runtime/database execution | COMPLETION_AUDIT |

## Runtime / Database / Integration Inventory

Pietto remains a SQL authoring compiler, not a database runtime, connector
service, package installer, or data materialization system.

| Feature / exact layer | Status | Strongest evidence | Boundary and remaining work | Prerequisite | Owner | Owner mode | Explicit exclusions | Strength |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Database execution, connections, credentials, transactions, and connector runtime | OUT_OF_SCOPE | `docs/roadmap.md` | Compiler emits SQL but does not execute it | Separate runtime/security/resource authorization | OUTSIDE_51_60 | excluded | No database access or runtime service | HISTORICAL |
| Schema introspection, db pull, and extension discovery | OUT_OF_SCOPE | `docs/roadmap.md` | No connection or physical schema binding | Separate connector/auth/threat contract | OUTSIDE_51_60 | excluded | No credentials, discovery, or server guessing | HISTORICAL |
| Registry access and remote semantic-package installation | OUT_OF_SCOPE | `docs/project-package.md` | Static non-executable package boundary | New safety authorization | OUTSIDE_51_60 | excluded | No network, install, cache, or code execution | CONTRACT |
| Prisma bridge | EXPLICITLY_DEFERRED | `docs/roadmap.md` | No dependency, conversion, generation, or CLI bridge | Future integration plan | OUTSIDE_51_60 | future replan | No Prisma dependency | HISTORICAL |
| Arrow/PyArrow and dataframe materialization/export | EXPLICITLY_DEFERRED | `docs/roadmap.md` | No data materialization or dependency | Future integration plan | OUTSIDE_51_60 | future replan | No execution or dataframe API | HISTORICAL |
| RAG, semantic graph, ERD, or AI bridge/export | EXPLICITLY_DEFERRED | `docs/project-package.md` | Private lineage is not an external bridge | Future integration plan | OUTSIDE_51_60 | future replan | No network or model integration | COMPLETION_AUDIT |
| LSP and UI/playground | EXPLICITLY_DEFERRED | `docs/roadmap.md` | No editor server, watcher, or web UI | Future tooling plan | OUTSIDE_51_60 | future replan | No server or file watching | HISTORICAL |
| Concrete dataframe export implementation | NOT_EVIDENCED | Slice 2 Gate 1 exact-term search | No exact implementation contract was found | Future evidence | OUTSIDE_51_60 | decision candidate | No inference from Arrow vocabulary | USER_STRATEGY_ONLY |
| Concrete remote semantic-package installation implementation | NOT_EVIDENCED | Slice 2 Gate 1 exact-term search | No exact implementation contract was found | Future evidence | OUTSIDE_51_60 | decision candidate | No inference from package vocabulary | USER_STRATEGY_ONLY |

## Finalized Phase 51-60 Active Planning Route

The finalized active planning route is:

1. Phase 51: Aggregate / Grouped Project Output-Schema Foundation
2. Phase 52: Core Type-System Capability Foundation
3. Phase 53: Window Function Syntax And Capability Contract
4. Phase 54: Import / Module / Export Readiness
5. Phase 55: Semantic Package Asset Schema
6. Phase 56: Capability Profile Static Schema And Declared Checking
7. Phase 57: PostgreSQL Extension Signature-Catalog Readiness
8. Phase 58: Project Explain / Portability / Public Metadata Readiness
9. Phase 59: Package Graph And Lineage / Provenance Integration
10. Phase 60: Multi-dialect Capability Ecosystem Completion Checkpoint

This is active planning only and the current authoritative sequence for future
read-only Gate 1 work. It is effective only after Slice 2 Gate 3 succeeds. It
causes no automatic phase start or completion and provides no implementation
authorization. Every later phase requires separate authorization. A later
change requires stronger evidence and an evidence-backed append-only replan
that preserves historical records.

Phase 51 uses current canonical expression types and private Phase 47-49
carriers only. It does not add new scalar types or type semantics. Phase 52
supplies later type/capability foundations. Phase 53 remains readiness-only.
Phase 54 rehomes the historical import/module/export direction. Phase 55
defines static asset schema before package graph behavior. Phase 56 defines
capability schema before extension catalogs. Phase 57 is catalog readiness, not
extension lowering. Phase 58 remains readiness/privacy-contract work. Phase 59
keeps integration private before public export. Phase 60 is a checkpoint, not a
release or backend implementation phase.

## Cross-phase Prerequisites

- Phase 51 requires completed Phase 47-49 private carriers and existing
  canonical expression type/nullability behavior.
- Phase 52 requires the Phase 30, 36, 41, and 42 matrices.
- Phase 53 requires Phase 51 output ownership and Phase 52 capability facts.
- Phase 54 requires the deterministic flat project catalog.
- Phase 55 requires type/module readiness and the non-executable boundary.
- Phase 56 requires type and package schemas before any declared checker.
- Phase 57 requires the Phase 56 capability schema.
- Phase 58 requires private project schema, package, capability, and extension
  boundaries before any public contract.
- Phase 59 requires Phase 55 asset identity plus Phase 49 private dependency
  and lineage carriers.
- Phase 60 audits Phases 51-59 and starts no backend or release work.

No prerequisite automatically authorizes its dependent phase.

## Items Outside Phase 51-60

The current route assigns no Phase 51-60 owner to:

- JOIN implementation and relationship-driven queries;
- grain behavior and fanout diagnostics;
- nested queries, derived tables, and CTE lowering;
- project IR, project SQL, and project emit-sql;
- concrete new dialect/backend implementations;
- concrete window implementation after Phase 53 readiness;
- database connection, execution, introspection, or db pull;
- Prisma;
- Arrow/dataframe materialization or export;
- RAG/semantic graph bridges;
- LSP, UI, or playground;
- package registry, remote install, or publish;
- executable plugins or hooks; and
- package release or version changes.

Do not assign placeholder phases after Phase 60. Any later assignment requires
an evidence-backed append-only replan and separate authorization.

## Explicit Non-goals

Slice 2 adds no:

- grammar, parser, AST, or generated artifact;
- semantic, IR, SQL, CLI, JSON, diagnostic, or backend behavior;
- aggregate, type, window, module, package, capability, extension, explain,
  metadata, lineage, relationship, or integration behavior;
- public project schema, API, explain, lineage, or export;
- package manifest, resolver, dependency solver, registry, lockfile, installer,
  cache, publisher, plugin, hook, or arbitrary code execution;
- database connection, SQL execution, introspection, discovery, credential, or
  runtime service;
- production source, dependency, package metadata, workflow, fixture, golden,
  example, script, or validation behavior;
- automatic phase start, completion, implementation authorization, public API
  promise, release commitment, or runtime/database authorization; or
- Gate 3, Slice 3, or later-phase preparation.

Private foundations are not public output. Readiness contracts are not
implemented behavior. Current bounded implementations are not wholly
unimplemented merely because adjacent work is deferred.

## Version And Release Boundary

Package version remains `0.1.0`.

Slice 2 authorizes no package version change, tag, release, publish, upload,
signing, attestation, dependency operation, CI trigger, CI rerun, CI watch, or
CI cancellation. Gate 2 does not stage, commit, push, or prepare Gate 3.
