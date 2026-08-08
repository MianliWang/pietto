# Pietto Active Roadmap Phase 53–70 v2

## Status And Current Authority

This document is the governance-schema successor to
`docs/spec/pietto-active-roadmap-phase53-70-v1.md`. During Phase 54 Slice 1
Gate 2 it is an uncommitted planned successor: Phase 53 is `COMPLETED`, Phase
54 is `UNSTARTED`, and Phases 55-70 are `UNSTARTED`.

This v2 becomes the sole current roadmap authority only after the exact Phase
54 Slice 1 Gate 3 activation condition: the reviewed tree passes unique natural
exact-head pull-request CI attempt 1, squash-merges with exact tree equality,
passes unique natural exact-head `main` push CI attempt 1, reconciles local
`main` by fetch and ff-only update, safely cleans the publication branch, and
records immutable publication evidence. Only then is Phase 54 `ACTIVE` and
Slice 1 `COMPLETED`; Slices 2-16 and Phases 55-70 remain `UNSTARTED`, with
`next=PHASE54_SLICE2_GATE0_GATE1`.

Persistence alone activates nothing and authorizes no later slice.

## Activated Authority And Published Phase 54 Progress

The activation condition above was met. This document is the sole current
roadmap authority. Phase 54 is `ACTIVE`, Slices 1 through 12 are `COMPLETED`
after exact Gate 3 publication, and Slices 13 through 16 remain `UNSTARTED`.
The published Slice 12 tree is `b4691181f4d535ab10757e89d75dd881a37f418b` and
its squash commit is `bd6bdcf17361b11d3067beec534432d37ffe6f05`. The next
product lifecycle state is `PHASE54_SLICE13_GATE0_GATE1`.

One unnumbered mid-phase interlude, **Post-Slice-12 Workflow Hardening And
Mid-phase Route Reconciliation**, follows Slice 12 and precedes Slice 13. It is
workflow, governance, development tooling, and readiness work recorded in
`docs/plan/phase-54-post-slice12-workflow-hardening-and-midphase-route-reconciliation.md`
and governed by
`docs/spec/pietto-semantic-slice-convergence-governance-v1.md`. It is not a
Slice, it does not change the sixteen-slice route, the slice titles, the
prerequisites, or any retained later-phase ownership, and it authorizes no
Slice 13 behavior.

The paragraphs above are the original Slice 1 Gate 2 status text and are
retained as historical checkpoints. Where they describe Phase 54 as
`UNSTARTED`, this section supersedes them.

## Predecessor And Append-only Lineage

The authority lineage is ordered and immutable:

1. `docs/spec/pietto-roadmap-phase45-60-v1.md` is historical evidence through
   Phase 50.
2. `docs/spec/pietto-active-roadmap-phase51-60-v1.md` is historical evidence
   through its EOF Reconciliation 4.
3. `docs/spec/pietto-active-roadmap-phase53-70-v1.md` is the direct current
   predecessor with exact SHA-256
   `67c886a05234d4513d2083a12fc0f95ad550fdd892565a6ef7c52de9631743e3`.
4. This v2 preserves the Phase 53-70 horizon and changes version because the
   permanent phase-start classification and route-selection governance schema
   is new.

No predecessor byte is appended, edited, deleted, or silently reinterpreted.
Historical readiness remains evidence. Live source and completed-phase evidence
take priority when a historical description is stale.

## Lifecycle Delivery And Classification Vocabulary

Lifecycle values are `ACTIVE`, `COMPLETED`, and `UNSTARTED`. Lifecycle is
independent from implementation authority, delivery, readiness, and feature
disposition.

Every phase-start atomic item receives exactly one value:

```text
IMPLEMENT_NOW
PRIVATE_READINESS_NOW
CONTRACT_ONLY_NOW
DEFER_BY_NECESSITY
OUT_OF_SCOPE
```

Every Slice 1 freezes `CURRENT_PRODUCTION`, `CURRENT_READINESS`, and
`RETAINED_LATER`. A later phase number alone is never a sufficient deferral
reason.

## Permanent Phase-start Governance

Every future Pietto phase must perform the **Phase-start Expansion,
Pull-forward, And Readiness Audit** before freezing its Slice 1 route. The
normative procedure and reusable template are in
`docs/spec/pietto-phase-start-expansion-pull-forward-readiness-governance-v1.md`.

The audit verifies live authority and production, challenges a stale title or
minimum boundary, atomizes later work, distinguishes production/private/
contract readiness, requires necessity-based deferral, screens every route
from 8 through 16, and freezes the three ledgers. Readiness cannot implicitly
publish schema, add a dependency/workflow/version, operate remotely, add a
dialect/Rust build, or perform a release/supply-chain action.

## Phase 54 Scope Product And Architecture Authority

Phase 54 is **Local Import / Module / Export Foundation**. It owns schema-v2
explicit-module activation with schema-v1 exact legacy compatibility; exact
selected-path module identity; contextual named import/export/alias syntax;
private-by-default visibility; eligible exports and basic explicit named
re-export; deterministic binding, collisions, module graph, cycles, and
`PIE-S2701`-`PIE-S2707`; cross-module type/relation facts; identity-safe
project facts; trusted local loading; private inspection/serialization; pure
procedures; differential vectors; and end-to-end hardening.

The five product decisions P1-P5 and five architecture decisions A1-A5 are
normative in the Phase 54 Slice 1 scope specification and master plan. Slice 1
freezes them but implements or emits none of their future syntax, carriers,
resolvers, or diagnostics.

## Phase 54 Sixteen-slice Route And Prerequisites

| Slice | Exact title | Prerequisite |
| ---: | --- | --- |
| 1 | Scope, Authority, Phase-start Expansion Audit, Decisions, Activation, And Route Lock | Phase 53 completion |
| 2 | Schema-v2 Explicit-module Activation And Immutable Project / Module Carrier | 1 |
| 3 | Module Identity, Selected-input Index, Trusted Local Loader, And Path / Symlink Boundary | 2 |
| 4 | Import / Export Contextual Grammar, Generated Parser, And Immutable AST | 1 |
| 5 | Module-qualified Nominal Declaration Identity And Per-module Catalogs | 2, 4 |
| 6 | Local Export Eligibility, Visibility, Explicit Named Re-export, And Facade Semantics | 5 |
| 7 | Named Imports, Aliases, Binding Environments, And Collision Rules | 6 |
| 8 | Module Graph, Cycles, Diagnostics, And Deterministic Ordering | 7 |
| 9 | Cross-module Type Alias, Enum, Shape, And Source Resolution | 8 |
| 10 | Cross-module Table / Query / Relation Resolution, Row Facts, And Legacy Compatibility | 3, 8, 9 |
| 11 | Module Attribution, Dependency, Origin, Provenance, And Lineage | 10 |
| 12 | Generic-signature, Nullability, Aggregate, Grouped, Window, Result-role, And Capability-fact Preservation | 10 |
| 13 | Package-neutral Identity Layering, Owner / Asset-compatible Carriers, Source Digest, And Loader Readiness | 3, 11, 12 |
| 14 | Private Module Inspection And Canonical Serialization | 13 |
| 15 | Rust-ready Pure Boundaries, Differential Vectors, And End-to-end Hardening | 8 through 14 |
| 16 | Completion Audit, Status Lock, And Phase 55 Handoff | 1 through 15 |

Slice 4 may proceed alongside Slices 2-3 after interfaces freeze. Slices 11
and 12 may proceed in parallel after Slice 10 with disjoint ownership. Git and
publication operations remain sequential. Each later slice requires separate
Gate authority.

## Phase 54 Current Production Readiness And Retained-later Freeze

`CURRENT_PRODUCTION` is schema-v1 flat project selection, parse/check,
collect-before-resolve semantics, current private project facts, stable public
serializer separation, SQL-generation-only behavior, and package version
`0.1.0`.

`CURRENT_READINESS` is the immutable project carriers, deterministic selection
and graph procedures, identity-preservable semantic/project facts, private
serializer patterns, and historical Phase 50 module/package readiness seams.

`RETAINED_LATER` is the exact Phase 55-70 and separate Release ownership below.
The canonical row-level ledgers are in the Phase 54 Slice 1 scope
specification.

## Phase 54 Maximum Safe Pull-forward Boundary

The maximum safe boundary is exactly `IMPLEMENT_NOW + PRIVATE_READINESS_NOW +
CONTRACT_ONLY_NOW`. It includes basic named re-export, local module identity
and resolution, trusted local loader security, identity-safe existing facts,
package-neutral private owner/asset seams, private inspection/serialization,
pure procedures, Rust-ready values/vectors, and legacy-flat hardening.

It excludes final package schemas/loading, capability-profile language,
extension catalog content, public artifact publication, package remote graph,
registry operations, ranges/solver/lockfile, production Rust, extension
lowering/new dialect, and tag/release/publish/sign/attest.

## Phase 55–60 Ownership Route

| Phase | Unique current title | Retained product boundary |
| ---: | --- | --- |
| 55 | Semantic Package Asset Schema And Deterministic Local Loading | final manifest, typed assets, package identities/dependencies/loading |
| 56 | Capability Profile Static Schema And Declared Checking | profile language/schema and checker |
| 57 | PostgreSQL Extension Signature Catalog Foundation | catalog schema/content and evidence-backed matching |
| 58 | Public Explain / Portability / Package Inspection Artifact v1 | independently versioned public artifact |
| 59 | Local Package Graph, Attribution, Provenance, And Lineage | package-level graph and attribution integration |
| 60 | Advanced Window Frames And Phase 51–60 Ecosystem / Release Readiness Checkpoint | advanced windows and checkpoint; no tag/publication |

## Phase 61–70 Ownership Route

| Phase | Unique current title | Retained product boundary |
| ---: | --- | --- |
| 61 | Project IR And Semantic Composition Foundation | production Project IR |
| 62 | Relationship, JOIN, Grain, And Fanout-safe Semantics | relationship and multi-relation semantics |
| 63 | Multi-relation SQL Artifacts, Project Emit-SQL, And QUALIFY Lowering | project SQL and QUALIFY |
| 64 | Advanced Generic Types, Coercion, Temporal, Decimal, And Native Mapping | advanced type semantics/mapping |
| 65 | Advanced Aggregation And Grouping | advanced aggregate/group behavior |
| 66 | Advanced Module And Semantic-package Assets | wildcard/qualified/export-from, callable/constraint/derive/relationship assets, package-aware advanced facade; basic named re-export is Phase 54 |
| 67 | Remote Package Manager, Registry, Fetch, Install, Cache, And Trust Boundary | remote I/O and trust |
| 68 | Dependency Ranges, Version Solver, Canonical Lockfile, And First Rust Kernel | solver/lockfile and production Rust |
| 69 | Extension-specific Lowering And Additional Dialect Backend Foundation | extension lowering and new dialect |
| 70 | Public Schema / Lineage / Attribution Expansion, Ecosystem Completion Audit, Rust Migration Decision, And v0.2 Release Readiness | public expansion, ecosystem/Rust/release decisions |

These are owners, not automatic implementation authority.

## No-unnecessary-deferral And Retained-owner Reconciliation

The canonical 54-row ledger in the Phase 54 Slice 1 scope specification has
classification totals `5 / 7 / 4 / 34 / 4` in the exact vocabulary order.
Basic explicit named re-export is `IMPLEMENT_NOW`. Phase 66 retains wildcard
import/export, source-qualified forms, `export from` or equivalent shorthand,
callable/constraint/derive/relationship module assets, package-aware advanced
facades, and other advanced module/package assets.

Every `DEFER_BY_NECESSITY` row identifies unstable semantics, prerequisite
absence, public-schema authority, remote/trust I/O, solver/lockfile semantics,
dialect ownership, runtime exclusion, Rust/build policy, or release/
supply-chain authority. No phase number is the reason.

## POST60 Owner-slot Reconciliation

| Stable owner slot | Exact current owner |
| --- | --- |
| `POST60_ADVANCED_AGGREGATION_GROUPING` | Phase 65 |
| `POST60_ADVANCED_TYPE_NATIVE_MAPPING` | Phase 64 |
| `POST60_ADVANCED_WINDOWS` | Phase 53 bounded windows; Phase 60 advanced windows; Phase 63 QUALIFY |
| `POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT` | Phase 62 |
| `POST60_PROJECT_IR` | Phase 61 |
| `POST60_MULTI_RELATION_SQL` | Phase 63 |
| `POST60_PUBLIC_PROJECT_SCHEMA_LINEAGE_EXPANSION` | Phase 70 |
| `POST60_ADVANCED_MODULE_PACKAGE_ASSETS` | Phase 54 basic named re-export; Phase 66 advanced forms |
| `POST60_REMOTE_PACKAGE_MANAGER` | Phase 67 |
| `POST60_DEPENDENCY_SOLVER_LOCKFILE` | Phase 68 |
| `POST60_ADDITIONAL_DIALECT_BACKENDS` | Phase 69 |
| `POST60_EXTENSION_LOWERING` | Phase 69 |

Compiler acceptance, capability facts, backend support, server installation,
private facts, public exposure, local graph, remote fetch, and solver behavior
remain separate authorities.

## Release Train

No phase gate implicitly publishes. Package/CLI version remains `0.1.0` until
a separate release authority changes it. Any optional preview after Phase 58
requires a separate workflow. Phase 60 Gate 3 must not tag or publish. A
separate Release 0.1.0 workflow follows Phase 60. Phase 70 is v0.2.0 ecosystem
beta readiness, not publication or v1.0 readiness.

Only Release Gate 3 may own irreversible tag, GitHub Release, PyPI publication,
signature, and attestation operations. This roadmap creates none.

## Rust Migration Track

There is no big-bang rewrite. Phases 54-60 may create private immutable
carriers, stable primitive identities, deterministic serialization, explicit
pure procedures, no ambient callbacks or Python-object identity across the
boundary, and differential-testable inputs/outputs. They add no production
Rust or native build by implication.

Phase 68 remains the preferred first production Rust solver/graph component,
and it requires Python reference behavior or a frozen corpus, deterministic
parity, fallback policy, benchmarks, build/package/security authority, and no
silent divergence.

## Public Compatibility And Non-goals

Phase 54 Slice 1 changes no grammar, accepted source, generated artifact, AST,
compiler/semantic/project/IR/SQL behavior, diagnostic emission, CLI, CLI JSON
v1, Semantic Metadata Artifact v1, Project JSON v2, public Python API,
dependency, lockfile, workflow, version, fixture, golden, example, runtime,
database, remote operation, Rust/native build, tag, Release, publication,
signing, or attestation.

Permanent non-goals remain database execution/connections/transactions,
server/schema introspection, executable package hooks/plugins, arbitrary Python
evaluation, concurrency/scheduling/distributed execution, optimizer
replacement, and web UI.

## Validation Publication And Stop Conditions

The immutable original Gate 0/1 evidence records `A5_M21_D0`; corrective
addendum 1 freezes the live Phase 54 Slice 1 Gate 2 allowlist as exactly
`A5_M32_D0`. Slice 1 adds 14 top-level tests and projects 886 tracked files, 543
Python files, 247 Markdown files, 450 test modules, 4,866 top-level tests, and
10,814 clean collected/passed items. Generated inventory remains 8, goldens
remain 37, package smoke must pass, and installed CLI remains `0.1.0`.
The binding correction record is
`/home/mianliwang/.local/state/pietto/evidence/phase54-slice1/gate0-gate1-plan-correction-1.txt`.

The end-to-end Gate profile, four exclusive evidence paths, the already
consumed formatter write on the original twenty-one Python paths, check-only
formatting on the corrected thirty-two Python paths, one branch/stage/commit/
push/ready PR, exact-head natural CI, squash-tree equality, ff-only
reconciliation, cleanup, and substantive STOP conditions are normative in the
Phase 54 Slice 1 scope specification and controlling Goal.
Mechanical reader/hash/manifest/inventory/heading/formatter/topology/evidence
repairs inside the frozen authority do not require a routine user pause.
