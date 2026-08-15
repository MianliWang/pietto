# Phase 55 — Semantic Package Asset Schema And Deterministic Local Loading

## Status And Slice 1 Lifecycle

Phase 54 and Slices 1 through 16 are `COMPLETED`. Phase 55 remains
`UNSTARTED`. Slice 1, **Scope, Authority, Phase-start Expansion Audit, Package
Decisions, Activation, And Route Lock**, is `IMPLEMENTED_UNPUBLISHED` only in
this Gate 2 candidate. The sole next token is `PHASE55_SLICE1_GATE3`.

Gate 3 exact reviewed-tree publication, natural exact-head pull-request CI,
exact-head review closure, protected squash with tree equality, natural
exact-head `main` CI, fast-forward-only reconciliation, and immutable
publication evidence are all required before Phase 55 becomes `ACTIVE` and
Slice 1 becomes `COMPLETED`. There is no post-CI status-flip commit.

## Trusted Phase 54 Baseline And Controlling Evidence

The exact baseline is commit `364296e69f7e289395661518031dafeb66a216cc`,
tree `4c9c784851c948bd535f8d3a6e12a936e0dd70bf`, parent
`2f0ea671d1325029d10ccb6694eef648e1d6c6ed`. Package and installed CLI version
remain `0.1.0`.

The controlling Phase 55 Slice 1 Gate 0/Gate 1 evidence is the create-once
file
`/home/mianliwang/.local/state/pietto/evidence/pietto-phase55-slice1-gate0-gate1-phase-start-expansion-readiness-and-route-audit.txt`
with SHA-256
`a18c4ed55b952889965df3484cd71ec3d26c32cea932cbbbaef5ad2ea07cbec9`.
The exact normative persistence of that audit is
`docs/spec/phase55-slice1-scope-authority-expansion-readiness-and-route-lock-v1.md`.

## Phase Identity Scope And Activation

Phase 55 creates the first deterministic local semantic-package product from
Phase 54 private readiness. It owns explicit schema-v3 activation, a strict
manifest, immutable package carrier, typed source/module assets, package
identity and exact version, exact local dependencies, trusted deterministic
local loading, package/module integration, package rejection behavior, private
inspection/serialization, and the pure/differential seams necessary to avoid
later redesign.

It owns no remote registry/fetch/install/cache/trust, dependency ranges or
solver, canonical lockfile, public package artifact, production Rust, Project
IR, JOIN/grain/project SQL, additional dialect, tag, Release, publish/upload,
signing, or attestation.

Package behavior is eventually activated only by `pietto.toml`
`schema_version = 3` with exactly one `[package]` table. Slice 1 freezes that
contract but implements no activation behavior.

## Current Production Readiness And Retained-later Freeze

The canonical `CURRENT_PRODUCTION` ledger has CP01 through CP09, the canonical
`CURRENT_READINESS` ledger has CR01 through CR08, and the canonical
`RETAINED_LATER` ledger has RL56 through RL70. Their complete rows live in the
Slice 1 specification. Current production includes exact schema-v1,
package-absent schema-v2, trusted module loading, module semantics and outputs,
and package version `0.1.0`; it includes no package loader. Current readiness
includes Phase 50 vocabulary and Phase 54 identity/trust/inspection/pure seams
but promotes none to product authority. Retained later work keeps its named
prerequisite or separate public, graph, remote, solver, dialect, or release
authority.

## Phase 54 Inheritance

The Slice 1 specification classifies all twenty relevant inherited seams as
`DIRECTLY_REUSABLE`, `REUSABLE_AFTER_PHASE55_EXTENSION`,
`READINESS_ONLY_NOT_PRODUCT`, `MISMATCHED_REQUIRES_PHASE55_REDESIGN`, or
`IRRELEVANT_TO_PHASE55`.

The core direct reuse is exact v1/v2 compatibility, inner
`ProjectModuleIdentity`, module semantics/algorithms, and preserved facts. The
trusted loader, selected-input index, source digest, canonical construction,
and pure procedure patterns require package-scoped extension. Local owner and
asset readiness does not become final package identity or taxonomy. SQL/IR and
goldens are irrelevant to this Phase 55 product.

## Phase-start Expansion Pull-forward And Readiness Audit

The canonical atomic ledger in the Slice 1 specification contains exactly 47
unique rows and exactly one classification per row:

```text
IMPLEMENT_NOW=11
PRIVATE_READINESS_NOW=9
CONTRACT_ONLY_NOW=8
DEFER_BY_NECESSITY=17
OUT_OF_SCOPE=2
```

Every `DEFER_BY_NECESSITY` row names a missing semantic, product, public-schema,
graph, remote/trust, solver, dialect, or release prerequisite. No phase number
alone is a reason. The maximum safe pull-forward is exactly the 28 rows
`I01-I11 + P01-P09 + C01-C08`; it stops before retained public, graph-product,
remote, solver, lockfile, production Rust, dialect, runtime, database, release,
and supply-chain ownership.

## Product Decisions P01 Through P14

- P01 — only schema v3 with one `[package]` activates one root package.
- P02 — schema v1 remains exact legacy; schema v2 remains package-absent; no heuristic or mixed mode.
- P03 — root activation pins `path`, `namespace`, `name`, `version`, and `sha256`.
- P04 — `pietto-package.toml` v1 is strict UTF-8 TOML with ordered assets/dependencies and a 1048576-byte limit.
- P05 — namespace/name are canonical slugs; version is exact canonical SemVer 2.0.0 text; unknown future input fails closed.
- P06 — package/release identity, locator, inode, and digest remain orthogonal; release identity survives relocation.
- P07 — one package owns one or more module sources; outer `PackageModuleIdentity` composes an unchanged inner `ProjectModuleIdentity`.
- P08 — Phase 55 v1 has the closed `{module_source}` / `MODULE_SOURCE` asset set; declarations are derived module facts.
- P09 — every dependency is an ordered exact release/digest/local-path occurrence with retained multiplicity and no ranges or solver.
- P10 — the only locator kind is `LOCAL_DIRECTORY`; root, dependency, and asset paths have distinct contained relative bases.
- P11 — loading composes Phase 54 descriptor trust, rechecks identity, validates pins, and yields no partial package.
- P12 — iterative closure/SCC and deterministic dependency-first ordering preserve every edge and select no collision winner.
- P13 — no new `PIE-*` range is selected; module diagnostic meanings remain; detailed package rejections stay private.
- P14 — config/manifest are user-authored input schemas; carriers, digests, load plans, inspection, rejection, and vectors remain private.

The Slice 1 specification is normative when this summary omits a field or
boundary.

## Architecture Decisions A01 Through A11

- A01 — the accepted manifest plus opened asset snapshots is the single authority root; all indexes/digests/views are derived.
- A02 — project, package release, inner module, outer package-module, selected input, owner, asset, locator, version, and digest identities do not alias.
- A03 — every package is an isolated pinned Phase 54 compilation island; only root package yields the project result.
- A04 — content digest is domain-separated, length-framed, ordered, relocation-neutral, and non-self-referential.
- A05 — authority collections are ordered tuples with multiplicity; duplicate buckets are complete.
- A06 — closure, SCC, and Kahn procedures are iterative and never expose dict/set order.
- A07 — duplicate, cycle, digest, release, and physical-root conflicts have no winner.
- A08 — the private rejection algebra is the exact closed 27-value set in the Slice 1 specification.
- A09 — one private root-derived inspection/serialization family is neither a public artifact nor a manifest reserializer.
- A10 — one total pure evaluator and frozen differential dimensions introduce no Rust/Cargo/FFI production.
- A11 — Gate 2 is dirty `main` with an empty index and no branch/publication; Gate 3 alone creates the topic branch.

## Package Manifest Asset Identity And Loading Boundary

The user-authored manifest is a strict input schema, not the Phase 58 public
inspection artifact. Manifest order and multiplicity are authority facts;
lookup maps, canonical bytes, and digests are projections. The only Phase 55
v1 asset is one module source identified by package release plus normalized
package-relative path. Existing declaration catalogs remain module-derived
facts, not a second package asset authority.

`PackageIdentity=(namespace,name)` and
`PackageReleaseIdentity=(PackageIdentity,exact_version)` provide nominal
identity. The locator provides controlled access and the digest detects
substitution; neither replaces identity. A package may own multiple modules,
and the same inner module path may exist in two package releases without
collision.

The root locator is project-relative; dependency locators are
manifest-directory-relative but must remain inside the pinned project root;
asset paths are package-root-relative and cannot escape. No network, ambient
discovery, callbacks, plugins, executable hooks, database access, absolute
path, URI, or unchecked symlink is accepted.

## Phase 55 Versus Phase 59 67 And 68

Phase 55 owns exact local declarations, direct occurrence evidence, trusted
local closure, a deterministic private operational load order, and rejection.
Phase 59 owns the queryable package graph, multi-hop path product, attribution,
provenance, origin, and lineage. Phase 67 owns remote location, registry,
network, install/cache/update/trust/signature behavior. Phase 68 owns ranges,
solver policy, preferred versions, canonical lockfile, and production Rust.

Exact pins and a private `PackageLoadPlan` do not move those later products.

## Phase 56 Through 70 Readiness Boundary

Phase 55 preserves existing capability/window/generic/nullability/aggregate/
grouped facts and freezes only future manifest-schema attachment barriers. It
pulls private inspection, direct dependency evidence, a local-only locator
kind, a stable closed asset discriminator, exact-pin values, and pure/vector
seams. It does not implement capability profiles, extension catalog,
public package artifact, package graph product, new language/IR/SQL, advanced
assets, remote behavior, solver/lockfile/Rust, dialect lowering, public
lineage/schema, ecosystem, or release work.

## Route Screen Eight Through Sixteen

All counts were screened using the permanent weighted model and hard gates.

| Slices | Disposition | Score |
| ---: | --- | ---: |
| 8 | hard-gate rejected | — |
| 9 | qualified | 48 |
| 10 | qualified | 54 |
| 11 | qualified | 60 |
| 12 | qualified and selected | 67 |
| 13 | qualified exceptional | 65 |
| 14 | qualified exceptional | 64 |
| 15 | hard-gate rejected | — |
| 16 | hard-gate rejected | — |

Twelve is the highest-scoring qualified route. Thirteen and fourteen satisfy
exceptional-route criteria but add reader/CI/publication cost without a better
authority split; fifteen and sixteen divide one semantic root or add padding.

## Exact Twelve-slice Route

1. Scope, Authority, Phase-start Expansion Audit, Package Decisions, Activation, And Route Lock
2. Explicit Package Activation, Compatibility, And Immutable Package Carrier
3. Package Manifest Input Schema And Canonical Normalization
4. Package Identity, Exact Version, And Content Digest
5. Closed Typed Asset Model And Asset Catalog
6. Trusted Local Package Locator And Containment Boundary
7. Deterministic Local Manifest Loading And Package/Module Integration
8. Exact Dependency Declarations And Deterministic Local Load Plan
9. Dependency Collision, Cycle, Diamond, And Rejection Diagnostics
10. Private Package Inspection And Canonical Serialization
11. Pure Package Boundary, Differential Vectors, Compatibility, And E2E Hardening
12. Completion Audit, Status Lock, And Phase56 Handoff

The canonical prerequisites, production/test owners, safe parallelism, and
completion conditions are the exact table in the Slice 1 specification.
Publication is sequential even where Slices 4/6, 5/6, or Slice 11 vector
authoring may safely overlap after shared interfaces freeze.

## Three-round Risk-adaptive Gate Workflow

Slices 1 through 10 use three rounds. Slices 11 and 12 are risk-adaptive but
retain all logical Gates and exact-tree publication; they use three separate
rounds whenever production, active-Gate, reader/topology, or public
compatibility facts move. A purely test/docs hardening or completion tree may
combine Round 1 planning with the separately verified offline Gate 2 only when
that Slice's own Gate 1 explicitly authorizes the combination. Every
publication remains sequential.

Gate 2 stays on `main`, keeps the real index empty, performs no branch/stage/
commit/push/PR/CI action, and identifies the candidate by baseline, A/M/D,
canonical patch, identity manifest, and reconstructible tree. Gate 3 creates
`phase55/slice1-scope-authority-expansion-readiness-route-lock` and uses
`Add Phase 55 scope authority and route lock`.

## Slice 1 Exact Gate 2 Scope And Allowlist

Gate 1 Corrective Addendum 1 freezes exactly `A3_M52_D0`: the plan, normative Slice 1
specification, and focused static test are added; README, active roadmap,
language-status specification, moving active-Gate manifest, Phase 54 handoff
reader, and exactly 47 frozen mechanical readers are modified. There are no
deletions. The complete literal path set is normative in the Slice 1
specification and active-Gate manifest. `AGENTS.md` remains unchanged.

No production source, grammar, generated, fixture, golden, dependency,
lockfile, workflow, public serializer, SQL, IR, or CLI implementation path is
allowed. Discovery must converge to the frozen reader set and prove
`reader additions = 0` and `hash/digest delta = 0`.

## Validation Evidence Publication And Activation

Gate 2 runs focused and all reader tests, Python 3.12/3.13 full suites, Ruff
format check-only and lint, both Pyright configurations, reader/hash closure,
all seven topology projections, generated and golden checks, `uv lock
--check`, offline package smoke, installed CLI `0.1.0`, schema-v1 and
package-absent schema-v2 compatibility, scope fingerprints, canonical patch
identity, full path identity manifest, and independent reconstruction.

The controlling Gate 2 evidence target is
`/home/mianliwang/.local/state/pietto/evidence/pietto-phase55-slice1-gate2-scope-authority-expansion-readiness-and-route-lock.txt`.
The Gate 3 target is
`/home/mianliwang/.local/state/pietto/evidence/pietto-phase55-slice1-gate3-publication-reconciliation.txt`.
Both follow regular non-symlink mode `0644`, exclusive no-follow create-once,
no overwrite/append/rename-over/chmod replacement, and one EOF terminal.

## Package Version Release Supply-chain And Remote Boundary

Package and CLI stay `0.1.0`; the sole runtime dependency stays
`antlr4-python3-runtime>=4.13.2`; the sole workflow stays `ci.yml`; generated
and golden inventories stay 8 and 37. Slice 1 adds no network code, remote
operation, Rust/native build, package publication, tag, Release, signing,
attestation, or supply-chain behavior.

## Stop Conditions

Stop for baseline/evidence drift, higher-authority contradiction, material
product or architecture change, non-mechanical allowlist expansion,
non-converging reader closure, compatibility or product behavior change,
dependency/workflow/version/public/release need, tree mismatch, or unsafe
immutable-evidence creation. Mechanical reader/hash/formatting corrections
inside the frozen authority continue without a routine pause.
