# Pietto Active Roadmap Phase 51–60 v1

## Status And Conditional Authority

This document is a PLANNED CHANGE during Phase 51 Slice 1 Gate 2. It is not
authoritative in Gate 2. The current authoritative lifecycle remains:

- Phase 50: COMPLETED;
- Phase 51: UNSTARTED;
- Phase 52–60: UNSTARTED.

This roadmap becomes authoritative only after the separately authorized Phase
51 Slice 1 Gate 3 creates the exact Slice 1 commit, performs one normal push,
and observes the natural `CI` push run complete successfully with `headSha`
exactly matching that commit. No future commit SHA, run ID, URL, or result is
preclaimed here.

After that complete condition, Phase 51 lifecycle becomes ACTIVE and Phase
52–60 remain UNSTARTED. ACTIVE identifies the current phase and planning
route; it does not authorize implementation. Every slice still requires its
own Gate 1, Gate 2, and Gate 3.

Slice 1 implements no compiler or runtime behavior.

## Historical Evidence Boundary

`docs/spec/pietto-roadmap-phase45-60-v1.md` is immutable historical evidence.
It must remain byte-for-byte unchanged. Its trusted SHA-256 is:

```text
26cc0ae4a68518223d6bf600ad3c4b0b226618aa7ef31b2ae1c25924d2655169
```

That historical snapshot records the route as it was adopted and completed
through Phase 50. This v1 active roadmap is the conditional current authority
for Phase 51–60 after the activation condition above. It does not rewrite or
reinterpret the historical file in place.

The trusted completed Phase 50 baseline is local `main` at
`5fc2f9d584d49f9d519b298f8205bd878aeb53cb`, equal to local `origin/main`,
with parent `9bc6ed82f3741e3c242981bb88edfb50c73fc586`, tree
`0a63f74fe65871567e9f7e4ea9dddc12d84c8b26`, and subject
`Complete Phase 50 semantic readiness consolidation audit`. Its package
version is `0.1.0`; it has no tag or exact-match tag; `tests/goldens` is
absent. Local Phase 50 Gate 3 evidence documents natural run `29189023482` as
`CI / push / main`, `completed / success`, with `headSha` exactly matching the
baseline: Python 3.12 recorded `5417 passed in 60.83s`, Python 3.13 recorded
`5417 passed in 33.31s`, generated validation recorded 8 tracked files,
golden validation recorded 37 fixtures (32 SQL and 5 JSON), and installed
package and CLI versions were both `0.1.0`. These CI facts are documented
local evidence, not a live GitHub lookup.

Current source and completed phase evidence take priority over stale roadmap
wording when they disagree. Such a disagreement must be recorded through the
append-only protocol in this document rather than by changing historical
evidence.

## Governance And Three Status Axes

Roadmap classification uses three independent axes. A value on one axis never
implies a value on another.

Lifecycle:

- `ACTIVE`: the current phase identity after its activation gate;
- `COMPLETED`: the phase has its own completion evidence and exact natural CI
  proof;
- `UNSTARTED`: no phase-start condition has been satisfied.

Delivery:

- `READINESS_CONTRACT_ONLY`: bounded specification, audit, or checkpoint work
  with no production foundation;
- `MINIMUM_PRODUCTION_FOUNDATION`: one bounded, deterministic, fail-closed
  production foundation, subject to separate slice authorization.

Feature disposition:

- `DEFERRED_WITH_OWNER`: unimplemented behavior with one exact future owner;
- `OUT_OF_SCOPE`: behavior excluded from the current product or roadmap
  boundary;
- `NOT_EVIDENCED`: support is not claimed until repository evidence exists.

`ACTIVE`, `COMPLETED`, and `UNSTARTED` are lifecycle values only.
`READINESS_CONTRACT_ONLY` and `MINIMUM_PRODUCTION_FOUNDATION` are delivery
values only. `DEFERRED_WITH_OWNER`, `OUT_OF_SCOPE`, and `NOT_EVIDENCED` are
feature-disposition values only.

## No Automatic Phase Start Rule

No roadmap row, prerequisite completion, owner assignment, title, delivery
target, or end-state description starts or completes a phase. In particular:

- listing Phase 51 does not authorize Slice 2 or any production carrier;
- completing one slice does not authorize the next slice;
- completing Phase 51 does not start Phase 52;
- a post-Phase-60 owner slot is not a Phase 61+ authorization or fixed phase
  number;
- a readiness contract does not imply implemented behavior;
- a catalog or capability fact does not imply backend lowering or runtime
  availability.

Every slice requires a read-only Gate 1, an exact-allowlist Gate 2, and a
separately authorized Gate 3. Phase completion requires that phase's own
completion gate and exact natural CI evidence. A roadmap row cannot supply
either condition.

## Base Active Route Identity

The base route retains these stable phase identities and exact delivery
classes:

| Phase | Stable phase name | Delivery |
| ---: | --- | --- |
| 51 | Aggregate / Grouped Project Output-Schema Foundation | `MINIMUM_PRODUCTION_FOUNDATION` |
| 52 | Core Type-System Capability Foundation | `MINIMUM_PRODUCTION_FOUNDATION` |
| 53 | Window Function Syntax And Capability Contract | `MINIMUM_PRODUCTION_FOUNDATION` |
| 54 | Import / Module / Export Readiness | `MINIMUM_PRODUCTION_FOUNDATION` |
| 55 | Semantic Package Asset Schema | `MINIMUM_PRODUCTION_FOUNDATION` |
| 56 | Capability Profile Static Schema And Declared Checking | `MINIMUM_PRODUCTION_FOUNDATION` |
| 57 | PostgreSQL Extension Signature-Catalog Readiness | `MINIMUM_PRODUCTION_FOUNDATION` |
| 58 | Project Explain / Portability / Public Metadata Readiness | `MINIMUM_PRODUCTION_FOUNDATION` |
| 59 | Package Graph And Lineage / Provenance Integration | `MINIMUM_PRODUCTION_FOUNDATION` |
| 60 | Multi-dialect Capability Ecosystem Completion Checkpoint | `READINESS_CONTRACT_ONLY` |

Titles containing Readiness or Contract retain historical identity. The
delivery column is normative and records whether the planned end state is a
bounded production foundation or a readiness-only checkpoint.

## Phase 51–60 Normative End-state Table

| Phase | Normative end state | Residual owner boundary |
| ---: | --- | --- |
| 51 | Current legal private aggregate/grouped schema, `ProjectRowResultRole` direction, bounded aggregate-result facts, exactly four-state availability, dependency, lineage, and concrete downstream propagation for `TableDef` and `QueryDef`. | Advanced aggregate/grouping behavior remains `POST60_ADVANCED_AGGREGATION_GROUPING`; public projection remains Phase 58. |
| 52 | Private immutable deterministic exact-current capability facts and fail-closed lookup, without type-system widening or public schema. | Advanced temporal, coercion, Decimal, domain, and native-mapping work remains `POST60_ADVANCED_TYPE_NATIVE_MAPPING`. |
| 53 | A bounded ranking-window production foundation for `row_number`, `rank`, and `dense_rank`. | Navigation/value windows, aggregate-as-window, frames, named windows, `QUALIFY`, and advanced expressions remain `POST60_ADVANCED_WINDOWS`. |
| 54 | Local file-as-module plus explicit named import/export minimum while preserving legacy flat-project compatibility. | Advanced module/package assets remain `POST60_ADVANCED_MODULE_PACKAGE_ASSETS`. |
| 55 | Strict local semantic-package manifest, typed assets, deterministic local loading, and exact dependency facts; no registry or solver. | Remote package management and dependency solving remain separate post-60 owners. |
| 56 | Private profile carrier and declared capability checking. | Runtime server detection stays out of scope; public reporting remains Phase 58. |
| 57 | Private static PostgreSQL extension catalog carrier, exact signature matching, and bounded evidence-backed seed signatures. | Extension-specific lowering remains `POST60_EXTENSION_LOWERING`; server introspection and installation stay out of scope. |
| 58 | One new independently versioned minimal public projection family for bounded project schema/lineage, portability, and package inspection while preserving CLI JSON v1, Semantic Metadata Artifact v1, and Project JSON v2. | Wider public schema, lineage, attribution, and graph exposure remains `POST60_PUBLIC_PROJECT_SCHEMA_LINEAGE_EXPANSION`. |
| 59 | Local exact dependency graph plus private package attribution, provenance, and lineage integration. | Public package graph expansion remains post-60; remote resolution is excluded. |
| 60 | Ecosystem coherence and residual-owner completeness audit across Phases 51–59. | No backend, release, runtime, or production implementation is part of this checkpoint. |

No phase is started or implemented by this table.

## Phase-by-phase Prerequisites And Non-goals

| Phase | Prerequisites | Explicit non-goals |
| ---: | --- | --- |
| 51 | Completed Phase 47–50 private schema, state, dependency, lineage, and readiness evidence. | No new aggregate language, grammar, AST, single-file semantic/IR/SQL, diagnostic, public schema, CLI/JSON, project IR/SQL, JOIN, runtime, dependency, workflow, version, or release behavior. |
| 52 | Phase 30/36 canonical type boundaries, Phase 41/42 Decimal evidence, and Phase 51 generic private schema. | No new type, literal, cast, operator, coercion, promotion, precision fusion, native mapping, or public field. |
| 53 | Phase 51 result-role separation and Phase 52 exact capability facts. | No navigation/value functions, aggregate-as-window, frames, named windows, `QUALIFY`, or broad partition/order expressions. |
| 54 | Deterministic current project catalog and legacy flat-project compatibility. | No remote package, wildcard import, re-export, runtime import, or executable module code. |
| 55 | Phase 52 capability boundary and Phase 54 local module identity. | No registry, remote fetch/install/update/cache, ranges, solver, lockfile, publication, or executable hooks/plugins. |
| 56 | Phase 52 exact facts and Phase 55 strict local assets. | No actual server detection, fallback, public schema, network, credentials, or runtime claims. |
| 57 | Phase 56 private profile/schema separation. | No introspection, installation, `CREATE EXTENSION`, runtime proof, or implied compiler lowering. |
| 58 | Phase 51 private schema, Phase 55 package facts, and Phase 56–57 capability/catalog facts. | No mutation of CLI JSON v1, Semantic Metadata Artifact v1, or Project JSON v2; no public package graph before Phase 59. |
| 59 | Phase 49 lineage, Phase 55 package identity/assets, and Phase 58 schema-family separation. | No remote resolution, public graph expansion, package execution, or runtime loading. |
| 60 | Separately completed and CI-proven Phases 51–59. | No new backend, compiler behavior, release, runtime, network, database, or implementation foundation. |

The prerequisites are planning dependencies only. They do not authorize a
phase or a slice.

## Readiness-to-minimum-foundation Policy

Phase 52 onward normally ends with exactly one of:

1. one bounded `MINIMUM_PRODUCTION_FOUNDATION`; or
2. one exact `DEFERRED_WITH_OWNER` entry.

`READINESS_CONTRACT_ONLY` is allowed only for a checkpoint or audit such as
Phase 60, or when the phase records one unique future implementation owner. It
must not leave anonymous "later work."

Every minimum production foundation must:

- be deterministic and fail closed;
- state its exact private/public boundary;
- preserve current compatibility;
- enumerate unsupported families;
- assign every residual item exactly once;
- avoid runtime or backend claims unsupported by evidence;
- pass its own completion Gate 3 with exact natural CI `headSha` proof.

A readiness artifact, capability name, signature description, profile, or
owner slot is not production behavior by itself.

## Local-first Package Ecosystem Policy

The selected Phase 55–59 direction is local-first and static:

- a local package-specific manifest;
- typed semantic and support asset schemas;
- deterministic local loading;
- exact declared dependencies only;
- a private capability profile carrier and checking;
- static PostgreSQL extension catalogs;
- a local exact package graph;
- private package attribution, provenance, and lineage;
- independently versioned public projections only after privacy contracts.

The Phase 55–59 route explicitly excludes:

- registry search;
- remote fetch, download, install, update, or cache;
- dependency ranges, solving, version selection, or lockfiles;
- package publish, signing, trust, or attestation;
- executable package code, hooks, or plugins;
- actual server extension discovery or installation.

Remote management and dependency solving have distinct post-60 owners because
deterministic exact local loading is useful without network resolution, and a
registry does not imply a solver.

## Deferred-owner Matrix

Every major Phase 50 deferral has one unique phase owner, stable post-60 owner
slot, or permanent charter disposition. `NOT_EVIDENCED` items remain fail
closed until their owner obtains evidence.

### Phase owner definitions

| Owner ID | Unique ownership | Prerequisites |
| --- | --- | --- |
| `PHASE_51` | Current legal aggregate/grouped private project schema, roles, facts, states, dependency, lineage, and propagation. | Phase 47–50 private carriers and readiness. |
| `PHASE_52` | Private immutable exact-current capability facts and fail-closed lookup only. | Phase 30/36/41/42 and Phase 51 generic schema. |
| `PHASE_53` | Bounded ranking-window minimum production foundation. | Phase 51 roles and Phase 52 capabilities. |
| `PHASE_54` | Local file-as-module and explicit named import/export minimum. | Deterministic project catalog. |
| `PHASE_55` | Strict local semantic-package manifest, asset schema, and loading. | Phase 52 and Phase 54. |
| `PHASE_56` | Private profile carrier and declared capability checking. | Phase 52 and Phase 55. |
| `PHASE_57` | Private static PostgreSQL extension catalog, exact matching, and bounded evidence-backed seed signatures. | Phase 56. |
| `PHASE_58` | One independently versioned minimal public project/portability/package-inspection projection family. | Phase 51 and Phase 55–57. |
| `PHASE_59` | Local exact package graph and private package attribution/provenance/lineage. | Phase 49, Phase 55, and Phase 58 schema separation. |
| `PHASE_60` | Ecosystem audit and owner-completeness checkpoint. | Completed Phases 51–59. |

### Aggregate/grouped deferrals

| ID | Deferred item | Current disposition | Unique owner |
| --- | --- | --- | --- |
| A01 | grouped project output schema | `DEFERRED_WITH_OWNER` | `PHASE_51` |
| A02 | aggregate-only project output schema | `DEFERRED_WITH_OWNER` | `PHASE_51` |
| A03 | selected-let aggregate schema | `DEFERRED_WITH_OWNER` | `PHASE_51` |
| A04 | computed aggregate argument schema | `DEFERRED_WITH_OWNER` | `PHASE_51` |
| A05 | aggregate origin and result role | `DEFERRED_WITH_OWNER` | `PHASE_51` |
| A06 | aggregate dependency and lineage | `DEFERRED_WITH_OWNER` | `PHASE_51` |
| A07 | aggregate/grouped downstream propagation | `DEFERRED_WITH_OWNER` | `PHASE_51` |
| A08 | duplicate output handling | `DEFERRED_WITH_OWNER` | `PHASE_51` |
| A09 | aggregate filters | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_AGGREGATION_GROUPING` |
| A10 | aggregate-internal ordering | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_AGGREGATION_GROUPING` |
| A11 | aggregate modifiers and generic DISTINCT forms | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_AGGREGATION_GROUPING` |
| A12 | `count_if` | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_AGGREGATION_GROUPING` |
| A13 | broad `count_distinct(expression)` | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_AGGREGATION_GROUPING` |
| A14 | `min/max(expression)` | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_AGGREGATION_GROUPING` |
| A15 | pure grouping | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_AGGREGATION_GROUPING` |
| A16 | rollup | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_AGGREGATION_GROUPING` |
| A17 | cube | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_AGGREGATION_GROUPING` |
| A18 | grouping sets | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_AGGREGATION_GROUPING` |
| A19 | Decimal aggregate precision/scale | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| A20 | relationship/fanout-aware aggregate semantics | `DEFERRED_WITH_OWNER` | `POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT` |

### Type-system deferrals

| ID | Deferred item | Current disposition | Unique owner |
| --- | --- | --- | --- |
| B01 | DateTime | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| B02 | Time | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| B03 | Interval | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| B04 | temporal literals | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| B05 | temporal arithmetic/functions | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| B06 | coercion and promotion | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| B07 | Decimal fusion | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| B08 | Decimal overflow/rounding formulas | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| B09 | native database type mappings | `OUT_OF_SCOPE` within 51–60; future slot only | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| B10 | Money | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| B11 | Currency | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| B12 | units | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| B13 | domains | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| B14 | refinements | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |

Phase 52 owns only the exact-current capability carrier and fail-closed lookup;
it does not implement B01–B14.

### Window deferrals

| ID | Deferred item | Current disposition | Unique owner |
| --- | --- | --- | --- |
| C01 | initial window syntax/grammar | `DEFERRED_WITH_OWNER` | `PHASE_53` |
| C02 | initial window AST | `DEFERRED_WITH_OWNER` | `PHASE_53` |
| C03 | initial semantic catalog | `READINESS_CONTRACT_ONLY` pending Phase 53 | `PHASE_53` |
| C04 | `row_number`/`rank`/`dense_rank` implementation | `DEFERRED_WITH_OWNER` | `PHASE_53` |
| C05 | navigation/value functions | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_WINDOWS` |
| C06 | aggregate-as-window | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_WINDOWS` |
| C07 | frames | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_WINDOWS` |
| C08 | named windows/inheritance | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_WINDOWS` |
| C09 | QUALIFY-like behavior | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_WINDOWS` |
| C10 | advanced partition/order expressions | `DEFERRED_WITH_OWNER` | `POST60_ADVANCED_WINDOWS` |

### Module/package deferrals

| ID | Deferred item | Current disposition | Unique owner |
| --- | --- | --- | --- |
| D01 | import/export/module syntax | `DEFERRED_WITH_OWNER` | `PHASE_54` |
| D02 | local module loader/resolver | `DEFERRED_WITH_OWNER` | `PHASE_54` |
| D03 | semantic-package manifest | `DEFERRED_WITH_OWNER` | `PHASE_55` |
| D04 | package asset loader | `DEFERRED_WITH_OWNER` | `PHASE_55` |
| D05 | local exact dependency graph | `DEFERRED_WITH_OWNER` | `PHASE_59` |
| D06 | remote registry | `OUT_OF_SCOPE` within 51–60 | `POST60_REMOTE_PACKAGE_MANAGER` |
| D07 | fetch/install/update/cache | `OUT_OF_SCOPE` within 51–60 | `POST60_REMOTE_PACKAGE_MANAGER` |
| D08 | dependency ranges/version solving | `OUT_OF_SCOPE` within 51–60 | `POST60_DEPENDENCY_SOLVER_LOCKFILE` |
| D09 | lockfile | `OUT_OF_SCOPE` within 51–60 | `POST60_DEPENDENCY_SOLVER_LOCKFILE` |
| D10 | executable package code/hooks/plugins | `OUT_OF_SCOPE` | `OUT_OF_SCOPE_CHARTER` |

### Capability/extension/dialect deferrals

| ID | Deferred item | Current disposition | Unique owner |
| --- | --- | --- | --- |
| E01 | capability profile production carrier | `DEFERRED_WITH_OWNER` | `PHASE_56` |
| E02 | declared capability checking | `DEFERRED_WITH_OWNER` | `PHASE_56` |
| E03 | extension catalog carrier | `DEFERRED_WITH_OWNER` | `PHASE_57` |
| E04 | exact signature matching | `READINESS_CONTRACT_ONLY` pending Phase 57 | `PHASE_57` |
| E05 | bounded concrete PostgreSQL extension signatures | `NOT_EVIDENCED` | `PHASE_57` |
| E06 | extension backend-lowering implementation | `DEFERRED_WITH_OWNER` | `POST60_EXTENSION_LOWERING` |
| E07 | portability computation/report | `DEFERRED_WITH_OWNER` | `PHASE_58` |
| E08 | new production SQL dialect backend | `DEFERRED_WITH_OWNER` | `POST60_ADDITIONAL_DIALECT_BACKENDS` |
| E09 | actual server installation state | `OUT_OF_SCOPE` | `OUT_OF_SCOPE_CHARTER` |

Signature description and compiler-lowering ownership remain separate. No
Phase 57 catalog entry implies `POST60_EXTENSION_LOWERING` behavior.

### Public/project deferrals

| ID | Deferred item | Current disposition | Unique owner |
| --- | --- | --- | --- |
| F01 | project explain | `DEFERRED_WITH_OWNER` | `PHASE_58` |
| F02 | bounded public project row schema v1 | `DEFERRED_WITH_OWNER` | `PHASE_58` |
| F03 | bounded public project lineage v1 | `DEFERRED_WITH_OWNER` | `PHASE_58` |
| F04 | portability report output | `DEFERRED_WITH_OWNER` | `PHASE_58` |
| F05 | package inspection report | `DEFERRED_WITH_OWNER` | `PHASE_58` |
| F06 | public package graph/attribution exposure | `DEFERRED_WITH_OWNER` | `POST60_PUBLIC_PROJECT_SCHEMA_LINEAGE_EXPANSION` |
| F07 | project-level IR | `DEFERRED_WITH_OWNER` | `POST60_PROJECT_IR` |
| F08 | multi-relation SQL artifacts/project emit-sql | `DEFERRED_WITH_OWNER` | `POST60_MULTI_RELATION_SQL` |

Phase 58 must use a new independently versioned artifact family. It must not
mutate CLI JSON v1, Semantic Metadata Artifact v1, or Project JSON v2.

### Relationship/runtime deferrals

| ID | Deferred item | Current disposition | Unique owner |
| --- | --- | --- | --- |
| G01 | JOIN implementation | `DEFERRED_WITH_OWNER` | `POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT` |
| G02 | relationship-driven query behavior | `DEFERRED_WITH_OWNER` | `POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT` |
| G03 | grain | `READINESS_CONTRACT_ONLY` | `POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT` |
| G04 | fanout diagnostics/semantics | `READINESS_CONTRACT_ONLY` | `POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT` |
| G05 | database connections/credentials | `OUT_OF_SCOPE` | `OUT_OF_SCOPE_CHARTER` |
| G06 | SQL execution/transactions | `OUT_OF_SCOPE` | `OUT_OF_SCOPE_CHARTER` |
| G07 | schema introspection/db pull | `OUT_OF_SCOPE` | `OUT_OF_SCOPE_CHARTER` |
| G08 | extension discovery/install state | `OUT_OF_SCOPE` | `OUT_OF_SCOPE_CHARTER` |
| G09 | runtime validation against server | `OUT_OF_SCOPE` | `OUT_OF_SCOPE_CHARTER` |

No item in this matrix authorizes its owner. A future owner may reject an item,
but it must record that disposition through append-only reconciliation.

## Post-Phase-60 Stable Owner Slots

These identifiers are stable future owner slots, not Phase 61+ authorizations
or fixed phase numbers.

| Owner slot | Scope | Prerequisites | Exclusions until mapped |
| --- | --- | --- | --- |
| `POST60_ADVANCED_AGGREGATION_GROUPING` | Aggregate filters/order/modifiers, `count_if`, broad expressions, pure grouping, rollup, cube, and grouping sets. | Phase 51, Phase 52, and Phase 56. | No automatic syntax or accepted-form widening. |
| `POST60_ADVANCED_TYPE_NATIVE_MAPPING` | Temporal types/operations, coercion/promotion, Decimal fusion/overflow/rounding, Money/Currency/units/domains/refinements, and native mappings. | Phase 52 and Phase 56. | No runtime introspection or implicit storage guarantee. |
| `POST60_ADVANCED_WINDOWS` | Navigation/value functions, aggregate-as-window, frames, named windows/inheritance, `QUALIFY`, and advanced window expressions. | Phase 53 and Phase 56. | No implicit backend support or ordinary-aggregate conflation. |
| `POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT` | Relationship query lookup, narrow JOIN semantic/IR/SQL, grain, fanout diagnostics, and fanout-safe aggregate semantics. | Project-IR prerequisites plus completed relationship metadata foundations. | No runtime database execution and no aggregate-safety inference from schema alone. |
| `POST60_PROJECT_IR` | Project-level IR, semantic-to-IR handoff, and nested/derived/CTE representation ownership. | Stable private project schema and composition facts. | No SQL emission. |
| `POST60_MULTI_RELATION_SQL` | Project SQL artifact identity, dependency ordering, project emit-sql, and multi-relation PostgreSQL/private MySQL lowering. | `POST60_PROJECT_IR`. | No database execution. |
| `POST60_PUBLIC_PROJECT_SCHEMA_LINEAGE_EXPANSION` | Public transitive schema/lineage, package graph, attribution/provenance, and cross-artifact references beyond Phase 58 minimum. | Phase 58 and Phase 59. | No mutation of current public artifact families. |
| `POST60_ADVANCED_MODULE_PACKAGE_ASSETS` | Wildcard/re-export/qualified imports and advanced callable/relationship/package assets. | Phase 54 and Phase 55. | No remote behavior or executable package code. |
| `POST60_REMOTE_PACKAGE_MANAGER` | Registry, fetch, install, update, and cache. | Local package foundation plus an explicit threat model. | No arbitrary code execution or implicit solver. |
| `POST60_DEPENDENCY_SOLVER_LOCKFILE` | Dependency ranges, version selection, solver, and canonical lockfile. | Local exact dependency graph. | No network implication. |
| `POST60_ADDITIONAL_DIALECT_BACKENDS` | One separately selected production SQL dialect backend per reconciliation. | Phase 56 capability facts and Phase 60 audit. | No generic fallback or unproven support claim. |
| `POST60_EXTENSION_LOWERING` | Evidence-backed extension-specific compiler lowering. | Phase 57 catalog and exact backend ownership. | No installation, discovery, or introspection. |
| `OUT_OF_SCOPE_CHARTER` | Permanent compiler-charter exclusions described below. | A product-charter-changing reconciliation before any mapping. | No implementation under this roadmap. |

Every stable slot must be mapped to a concrete future phase only by an
append-only reconciliation entry and that future phase's separate gates.

## Permanent Out-of-scope Charter Boundary

`OUT_OF_SCOPE_CHARTER` is the sole disposition for:

- database connections, credentials, or secret handling;
- SQL execution, transactions, locks, or runtime scheduling;
- schema or server introspection and `db pull`;
- runtime validation against a database server;
- extension discovery, installation state, or `CREATE EXTENSION`;
- executable package code, hooks, scanners, or plugins;
- unrelated RAG, web UI, orchestration, or runtime product surfaces.

These items cannot be assigned to a phase by ordinary route maintenance. They
require a product-charter-changing append-only replan, a new threat and trust
boundary, and separate authorization. Their presence in the owner matrix is a
denial boundary, not deferred implementation approval.

## Append-only Reconciliation Protocol

The base route and ledger entries in this v1 file are append-only after the
roadmap becomes authoritative. Future route changes must append a new
`Reconciliation N` entry at EOF. Each entry must record:

1. the previous reconciliation entry or base route;
2. exact repository evidence;
3. the old route and new route;
4. every owner addition, removal, or transfer;
5. lifecycle, delivery, and feature-disposition effects;
6. why no deferral becomes anonymous;
7. explicit non-authorization boundaries;
8. its own Gate 3 activation condition and exact natural CI proof.

Earlier route text and earlier ledger entries must not be edited, deleted,
reordered, or reinterpreted in place. A change to the governance schema,
status axes, or reconciliation protocol requires a new
`pietto-active-roadmap-phase51-60-v2.md`; v1 remains byte-for-byte history.

## Version Package And Release Boundary

The trusted Phase 50 baseline package version is `0.1.0`. The internal phase
route, lifecycle labels, and delivery targets are not package-version claims.

Slice 1 and this roadmap authorize no change to `pyproject.toml`, `uv.lock`,
dependencies, package metadata, workflows, fixtures, goldens, examples, or
release surfaces. They authorize no version bump, tag, release, publish,
upload, signing, attestation, package registry action, or CI operation. The
trusted baseline has no tag or exact-match tag, and `tests/goldens` is absent.

Any later version or release operation requires a separate explicit plan,
allowlist, validation, publish authorization, and exact natural CI evidence.

## Stop Conditions

Stop and return to a new read-only Gate 1 if work requires any of the
following without a separately approved gate:

- editing the immutable historical roadmap or another completed Phase 44–50
  artifact;
- changing a fifth Slice 1 repository path;
- adding or modifying production source, grammar, generated files, AST,
  semantic analysis, IR, SQL, diagnostics, CLI, JSON, or public API behavior;
- adding a new aggregate form, type-system behavior, window, JOIN, grain,
  fanout, project IR/SQL, module, package, profile, catalog, backend, runtime,
  database, network, or plugin behavior;
- mutating dependencies, workflows, package metadata, version, tag, release,
  publication, signing, or attestation surfaces;
- staging, committing, pushing, fetching, or operating CI during Gate 2;
- starting Slice 2, Phase 52, or any later phase;
- leaving a deferred item without one exact owner;
- needing to rewrite the base route instead of appending reconciliation;
- changing the governance schema without creating v2;
- fabricating a future commit SHA, CI run, URL, or success result.

## Reconciliation Ledger

No reconciliation entries exist. This is the initial base route. Future valid
entries may only be appended at EOF under the protocol above.

### Reconciliation 1 — Phase 51 Conditional Completion And Phase 52 Handoff

1. The previous entry is the initial base route; no reconciliation entry
   preceded this first append-only reconciliation.
2. Trusted repository evidence through Slice 11 is HEAD
   `5138d28ee2d0a258076a68a6f98c74ce15a93bf8` and natural CI run
   `29371109641`, which completed successfully for that exact `headSha`, with
   real `CPython 3.12.13` and `CPython 3.13.14` jobs each reporting
   `5739 passed`.
3. The old and new Phase 51 names, routes, exact 12-slice count, owners, and
   delivery classes are identical.
4. Owner additions, owner removals, and owner transfers are all none.
5. Before activation, Phase 51 remains ACTIVE and incomplete, and Phase 52–60
   remain UNSTARTED.
6. Activation requires the exact Slice 12 commit, one normal push to `main`,
   and the natural CI run to be `completed / success` with `headSha` exactly
   matching that commit.
7. After and only after activation, Phase 51 is COMPLETED and Phase 52–60
   remain UNSTARTED.
8. No deferral becomes anonymous, and this reconciliation authorizes no Phase
   52 implementation and no compiler, public, runtime, database, version, tag,
   release, publish, upload, signing, or attestation activity.

The exact future Slice 12 commit SHA and natural CI run ID belong only in Gate
3 evidence. No post-CI repository status-flip commit is planned or required.
Phase 52 is the next planned phase but remains UNSTARTED; its exact next gate is
Phase 52 Slice 1 Gate 0 and Gate 1.
