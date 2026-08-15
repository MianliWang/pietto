# Phase 55 Slice 1 Scope, Authority, Phase-start Expansion Audit, Package Decisions, Activation, And Route Lock v1

## Purpose And Slice Identity

Phase 55 is **Semantic Package Asset Schema And Deterministic Local Loading**.
Slice 1 is **Scope, Authority, Phase-start Expansion Audit, Package Decisions,
Activation, And Route Lock**. This specification persists the Phase-start
audit, the exact package product and architecture decisions, the selected
twelve-slice route, the later-owner boundary, and the publication lifecycle.

Slice 1 is authority, documentation, active-Gate, and static-contract work
only. It implements no Phase 55 package behavior.

## Trusted Baseline And Binding Evidence

The exact pre-Slice-1 baseline is commit
`364296e69f7e289395661518031dafeb66a216cc`, tree
`4c9c784851c948bd535f8d3a6e12a936e0dd70bf`, and parent
`2f0ea671d1325029d10ccb6694eef648e1d6c6ed`. Phase 54 and Slices 1 through 16
are `COMPLETED`; Phase 55 is `UNSTARTED`; package and installed CLI version
remain `0.1.0`.

The controlling immutable Gate 0/Gate 1 evidence is
`/home/mianliwang/.local/state/pietto/evidence/pietto-phase55-slice1-gate0-gate1-phase-start-expansion-readiness-and-route-audit.txt`
with SHA-256
`a18c4ed55b952889965df3484cd71ec3d26c32cea932cbbbaef5ad2ea07cbec9`.
Its 14 product decisions, 11 architecture decisions, 47-row classification
ledger, three current-state ledgers, selected route, allowlist projection, and
Gate workflow are binding.

## Authority Hierarchy And Historical Dispositions

Conflicts are resolved in this order:

```text
AGENTS.md
> live Git and repository state
> active roadmap and current phase authorities
> immutable evidence
> live GitHub and CI
> initiating request
> historical summaries and runtime journals
```

Historical prose is not promoted over live authority. The prior maintenance
wheel discrepancy is `NON_LOAD_BEARING_HISTORICAL_RECORD_ERROR`; its immutable
record is not rewritten. The stray synthetic remote-tracking ref is a
`one-run fixture setup error`; it creates no topology-tool repair in this
Slice.

## Gate 2 Lifecycle And Conditional Activation

Throughout Gate 2, Phase 54 is `COMPLETED`, Phase 55 is `UNSTARTED`, and Slice
1 is `IMPLEMENTED_UNPUBLISHED`. The candidate remains a dirty overlay on
`main` with an empty real index. Gate 2 creates no branch, commit, push, PR, or
CI state.

Persistence alone activates nothing. The activation chain is exactly:

```text
Gate 2 candidate
-> Gate 3 exact reviewed-tree publication
-> natural exact-head pull-request CI attempt 1
-> exact-head review closure
-> protected squash with tree equality
-> natural exact-head main CI attempt 1
-> fetch and fast-forward-only reconciliation
-> immutable publication evidence
-> Phase 55 ACTIVE / Slice 1 COMPLETED
```

Only that full condition leaves Slices 2 through 12 `UNSTARTED` and sets
`next=PHASE55_SLICE2_GATE0_GATE1`. Until then the sole next token is
`PHASE55_SLICE1_GATE3`.

## Static-only Slice 1 Boundary

Slice 1 adds this specification, the Phase 55 plan, one focused static test,
and bounded current-status and active-Gate projections. It adds no schema-v3
parser, `pietto-package.toml` parser, package carrier, identity, SemVer
processor, asset catalog, dependency loader, diagnostic, load plan, package
inspection, serializer, pure evaluator, differential vector, or other Phase
55 production behavior.

No production source, grammar, generated parser, fixture, golden, dependency,
lockfile, workflow, public serializer, SQL, IR, CLI, package metadata, version,
tag, Release, publish/upload, signing, or attestation surface changes.

## Current Production Ledger

- CP01 — schema-v1 exact legacy-flat project discovery, parsing, checking, and output.
- CP02 — schema-v2 explicit local modules; schema-v2 is not package activation.
- CP03 — strict `pietto.toml` loading, deterministic selected-input order, and one project root.
- CP04 — pinned-root, containment, no-follow, opened-identity, TOCTOU, byte-limit, and source-digest loading.
- CP05 — contextual local module imports/exports/aliases and immutable parser-owned module AST.
- CP06 — per-module catalogs, facades, binding environments, graph, resolution, and `PIE-S2701` through `PIE-S2707` diagnostics.
- CP07 — complete module attribution/dependency/origin/provenance/lineage and semantic-fact preservation.
- CP08 — current CLI, Project JSON v2, Semantic Metadata Artifact v1, SQL, public exports, and package smoke behavior.
- CP09 — Python package `0.1.0` with one runtime dependency and no semantic package manifest or loader.

## Current Readiness Ledger

- CR01 — historical Phase 50 strict-TOML, namespace/name, exact-version, and exact-dependency vocabulary as non-product evidence.
- CR02 — stable root-relative `ProjectModuleIdentity`, selected order, module graphs, and complete no-winner buckets.
- CR03 — per-opened-source SHA-256 and filesystem identity facts.
- CR04 — package-neutral local owner/asset/digest seams, explicitly not package authority.
- CR05 — fail-closed loader-readiness facts, explicitly not a loader.
- CR06 — one private module inspection projection and canonical serialization pattern.
- CR07 — one pure total evaluator, closed normalized rejection pattern, frozen vectors, and Python reference harness.
- CR08 — Phase 54 fact preservation sufficient to carry existing capability/window/type/aggregate facts losslessly through future package validation.

## Retained Later Ledger

- RL56 — capability-profile language/schema/checker; missing approved profile identity, syntax, and checking semantics.
- RL57 — PostgreSQL extension catalog schema/content/matching; missing evidence-backed corpus and profile contract.
- RL58 — independently versioned public explain/portability/package-inspection artifact; requires separate public schema/privacy authority.
- RL59 — package graph, attribution, provenance, and lineage product; requires a stable package loading relation and independent causal-product authority.
- RL60 — advanced window frames and ecosystem checkpoint; requires language/semantic/IR/dialect work and completed Phase 51-59 evidence.
- RL61 — production Project IR; requires settled package/project composition and independent IR authority.
- RL62 — relationship/JOIN/grain/fanout semantics; requires Project IR and unresolved multi-relation semantic contracts.
- RL63 — multi-relation SQL, project emit-SQL, and QUALIFY; requires Phase 61/62 semantic and IR products.
- RL64 — advanced generic/coercion/temporal/Decimal/native mapping; requires unresolved type matrices and backend contracts.
- RL65 — advanced aggregation/grouping; requires separate grammar/semantic/IR/SQL decisions.
- RL66 — wildcard/qualified/export-from/callable/constraint/derive/relationship assets and package-aware advanced facades; semantics are not yet stable.
- RL67 — remote registry/fetch/install/cache/trust; requires remote threat model, network, persistence, and trust authority.
- RL68 — ranges/solver/canonical lockfile/production Rust; requires exact graph evidence, solving policy, parity, build, and supply-chain authority.
- RL69 — extension lowering and additional dialects; requires catalog and backend ownership.
- RL70 — public schema/lineage/attribution expansion, ecosystem completion, Rust migration decision, and release readiness; requires public schema, completion evidence, and Release Gate authority.

The three ledgers are disjoint: readiness is not production and retained-later
work is not silently authorized.

## Phase 54 Inherited-asset Dispositions

| ID | Inherited seam | Disposition |
| ---: | --- | --- |
| 01 | schema-v1 exact legacy-flat boundary | `DIRECTLY_REUSABLE` |
| 02 | schema-v2 explicit-module and package-absent boundary | `DIRECTLY_REUSABLE` |
| 03 | project config/root carrier | `REUSABLE_AFTER_PHASE55_EXTENSION` |
| 04 | `ProjectModuleIdentity` path-only identity inside one pinned compilation root | `DIRECTLY_REUSABLE` |
| 05 | cross-package `PackageModuleIdentity` composition | `REUSABLE_AFTER_PHASE55_EXTENSION` |
| 06 | ordered selected-input index | `REUSABLE_AFTER_PHASE55_EXTENSION` |
| 07 | pinned-root/opened-descriptor trusted loader sequence | `REUSABLE_AFTER_PHASE55_EXTENSION` |
| 08 | module import/export/catalog/binding/facade semantics | `DIRECTLY_REUSABLE` |
| 09 | module graph/cycle/resolution algorithms inside one package island | `DIRECTLY_REUSABLE` |
| 10 | module attribution/origin/provenance/lineage as package-graph product | `READINESS_ONLY_NOT_PRODUCT` |
| 11 | preserved generic/nullability/computed/aggregate/grouped/window/result-role/capability facts | `DIRECTLY_REUSABLE` |
| 12 | `ProjectLayeredOwnerIdentity` with reserved empty namespace | `MISMATCHED_REQUIRES_PHASE55_REDESIGN` |
| 13 | `ProjectLayeredAssetKind` `MODULE_SOURCE`/`NOMINAL_DECLARATION` carrier as final package taxonomy | `MISMATCHED_REQUIRES_PHASE55_REDESIGN` |
| 14 | opened-source SHA-256 fact | `REUSABLE_AFTER_PHASE55_EXTENSION` |
| 15 | `ProjectLayeredLoaderReadiness` | `READINESS_ONLY_NOT_PRODUCT` |
| 16 | Slice 14 inspection record schema/public meaning | `READINESS_ONLY_NOT_PRODUCT` |
| 17 | canonical projection/serialization construction discipline | `REUSABLE_AFTER_PHASE55_EXTENSION` |
| 18 | Slice 15 pure value/evaluator/rejection pattern | `REUSABLE_AFTER_PHASE55_EXTENSION` |
| 19 | Slice 15 module differential vectors as package vectors | `READINESS_ONLY_NOT_PRODUCT` |
| 20 | existing SQL/IR/golden implementation as Phase 55 production | `IRRELEVANT_TO_PHASE55` |

No value-equal carrier, lookup, map, digest, serialization, or physical locator
becomes an independent identity authority.

## Phase-start Expansion Pull-forward And Readiness Audit

Each of the 47 atomic rows below has exactly one of these values:

```text
IMPLEMENT_NOW
PRIVATE_READINESS_NOW
CONTRACT_ONLY_NOW
DEFER_BY_NECESSITY
OUT_OF_SCOPE
```

| ID | Owner | Classification | Atomic item / exact artifact or necessity |
| --- | --- | --- | --- |
| I01 | 55 | `IMPLEMENT_NOW` | explicit schema-v3 package activation and v1/v2 absence compatibility; exclusive project config contract |
| I02 | 55 | `IMPLEMENT_NOW` | immutable normalized package authority carrier; frozen dataclasses rooted only in accepted manifest content |
| I03 | 55 | `IMPLEMENT_NOW` | strict manifest parse and canonical normalization; `pietto-package.toml` v1 parser/validator |
| I04 | 55 | `IMPLEMENT_NOW` | package identity, schema version, exact release version, and content-digest facts; orthogonal value types |
| I05 | 55 | `IMPLEMENT_NOW` | closed typed asset set; `MODULE_SOURCE`-only discriminator/catalog |
| I06 | 55 | `IMPLEMENT_NOW` | one-package-to-many-modules and package/module integration; outer `PackageModuleIdentity` plus per-package module island |
| I07 | 55 | `IMPLEMENT_NOW` | trusted local locators, containment, and substitution checks; package-root/manifest/asset trusted loader |
| I08 | 55 | `IMPLEMENT_NOW` | exact dependency declarations; ordered occurrence ledger with exact release/digest/local locator |
| I09 | 55 | `IMPLEMENT_NOW` | deterministic local loading relation; private dependency-first `PackageLoadPlan` |
| I10 | 55 | `IMPLEMENT_NOW` | package diagnostics and normalized rejection behavior; root-cause-first adapter plus closed private algebra |
| I11 | 66 | `IMPLEMENT_NOW` | stable asset-kind discriminator and fail-closed versioned extensibility; v1 closed enum and schema-upgrade rule retained by Phase 66 for new kinds |
| P01 | 55 | `PRIVATE_READINESS_NOW` | private package inspection/canonical bytes; one root-derived private projection and serializer |
| P02 | 55 | `PRIVATE_READINESS_NOW` | pure package document/evaluator/differential vectors; total value procedure and Python reference vectors |
| P03 | 56 | `PRIVATE_READINESS_NOW` | lossless existing capability-fact preservation; unchanged opaque facts only, no profile field/language/checking |
| P04 | 59 | `PRIVATE_READINESS_NOW` | raw ordered direct dependency-occurrence evidence; loader ledger only, no graph product or multihop facts |
| P05 | 60 | `PRIVATE_READINESS_NOW` | lossless existing window-fact preservation; unchanged module facts only |
| P06 | 64 | `PRIVATE_READINESS_NOW` | lossless existing generic/nullability preservation; unchanged module facts only |
| P07 | 65 | `PRIVATE_READINESS_NOW` | lossless existing aggregate/grouped preservation; unchanged module facts only |
| P08 | 67 | `PRIVATE_READINESS_NOW` | local-only locator/source-identity seam; private `LOCAL_DIRECTORY` locator kind with no remote behavior |
| P09 | 68 | `PRIVATE_READINESS_NOW` | normalized exact-pin and pure handoff/vector seam; exact release/digest values only, no ranges/solver/lockfile/Rust |
| C01 | 56 | `CONTRACT_ONLY_NOW` | capability requirement attachment boundary; future manifest schema upgrade only, v1 accepts no requirement language |
| C02 | 57 | `CONTRACT_ONLY_NOW` | backend-neutral extension requirement boundary; future manifest schema upgrade only, v1 accepts no catalog/reference field |
| C03 | 61 | `CONTRACT_ONLY_NOW` | package carrier is not Project IR; explicit type/ownership barrier |
| C04 | 62 | `CONTRACT_ONLY_NOW` | relationship/advanced semantic asset boundary; `MODULE_SOURCE`-only v1 and Phase 66 schema-upgrade requirement |
| C05 | 63 | `CONTRACT_ONLY_NOW` | package loading does not trigger project SQL/IR emission; orchestration boundary |
| C06 | 68 | `CONTRACT_ONLY_NOW` | future solver-result handoff; an already-exact local package set may feed the loader without changing exact-pin semantics |
| C07 | 69 | `CONTRACT_ONLY_NOW` | package identity/reference remains backend/dialect neutral; no dialect field or lowering hook |
| C08 | 70 | `CONTRACT_ONLY_NOW` | private/public compatibility barrier; no Project JSON v2, Artifact v1, explain, or public package serializer field |
| D01 | 56 | `DEFER_BY_NECESSITY` | profile schema/language/checker: missing approved profile identity, input schema, and checking semantics |
| D02 | 57 | `DEFER_BY_NECESSITY` | extension catalog schema/content/matching: missing Phase 56 profile contract and evidence-backed catalog corpus |
| D03 | 58 | `DEFER_BY_NECESSITY` | public package inspection artifact: requires independently versioned public schema/privacy authority |
| D04 | 59 | `DEFER_BY_NECESSITY` | package graph/attribution/provenance/lineage product: requires stable Phase 55 loader output and separate causal-product semantics |
| D05 | 60 | `DEFER_BY_NECESSITY` | advanced window frames: requires new language, semantic, IR, and dialect authority |
| D06 | 60 | `DEFER_BY_NECESSITY` | ecosystem checkpoint: requires completed Phase 51-59 evidence and separate checkpoint authority |
| D07 | 61 | `DEFER_BY_NECESSITY` | Project IR: requires settled package/project composition and independent production IR contract |
| D08 | 62 | `DEFER_BY_NECESSITY` | relationship/JOIN/grain/fanout: requires Project IR and unresolved multi-relation semantics |
| D09 | 63 | `DEFER_BY_NECESSITY` | multi-relation SQL/project emit-SQL/QUALIFY: requires Phase 61/62 semantics and IR |
| D10 | 64 | `DEFER_BY_NECESSITY` | advanced types/native mapping: type/coercion/precision/backend matrices remain unresolved |
| D11 | 65 | `DEFER_BY_NECESSITY` | advanced aggregation/grouping: requires separate grammar/semantic/IR/SQL decisions |
| D12 | 66 | `DEFER_BY_NECESSITY` | advanced assets/facades: callable/constraint/derive/relationship and wildcard/qualified/export-from semantics remain unresolved |
| D13 | 67 | `DEFER_BY_NECESSITY` | remote registry/fetch/install/cache/trust: requires network, persistence, threat-model, and trust authority |
| D14 | 68 | `DEFER_BY_NECESSITY` | ranges/solver/canonical lockfile: requires solving policy, conflict objectives, reproducibility schema, and lockfile authority |
| D15 | 68 | `DEFER_BY_NECESSITY` | production Rust kernel: requires stable pure parity evidence plus build/FFI/supply-chain authority |
| D16 | 69 | `DEFER_BY_NECESSITY` | extension lowering/additional dialect: requires Phase 57 catalog and independent backend ownership |
| D17 | 70 | `DEFER_BY_NECESSITY` | public expansion/ecosystem completion/release decisions: requires public schema, completion evidence, migration decision, and Release Gate authority |
| O01 | 57 | `OUT_OF_SCOPE` | database/server discovery, installation, introspection, or execution violates the static compiler/package boundary |
| O02 | 67 | `OUT_OF_SCOPE` | executable hooks, plugins, ambient callbacks, or arbitrary code violate the project charter and non-executable package boundary |

The totals are exactly:

```text
IMPLEMENT_NOW=11
PRIVATE_READINESS_NOW=9
CONTRACT_ONLY_NOW=8
DEFER_BY_NECESSITY=17
OUT_OF_SCOPE=2
```

## Maximum Safe Pull-forward Boundary

The maximum safe pull-forward boundary is exactly 28 rows:
`I01-I11 + P01-P09 + C01-C08`. It includes the complete static local Phase 55
package product plus private preservation, pure/vector, local-locator,
exact-pin, and contract barriers needed to avoid redesign. It stops before
every retained public artifact, package graph product, remote operation,
solver, lockfile, production Rust, dialect, runtime, database, release, or
supply-chain owner.

## Exact Fourteen Product Decisions

### P01 — Explicit Activation

`pietto.toml` `schema_version = 3` is the sole package activation. It contains
exactly one `[package]` table and activates exactly one root package. A
multi-root set is not selected because the live `ProjectSemanticModel` has one
root and one compilation mode with no authorized aggregation, visibility, or
output-selection semantics.

### P02 — Compatibility

Schema v1 remains exact legacy-flat. Schema v2 remains exact explicit-modules
and never looks for a package manifest. Schema v3 rejects `[sources]`; schema
v1/v2 reject package keys. A manifest present without schema v3 is ignored,
not discovered. Schema v3 with a missing manifest fails. Heuristic, ambient,
directory, and mixed activation are forbidden.

### P03 — Root Activation Form

Strict schema-v3 `[package]` keys are `path`, `namespace`, `name`, `version`,
and `sha256`. `path` is a project-root-relative local package directory; the
other fields are expected manifest identity/version/content pins.

### P04 — Manifest Form

The fixed filename is `pietto-package.toml`: strict UTF-8 TOML, exact
`schema_version = 1`, scalar keys `schema_version`, `namespace`, `name`, and
`version`, ordered `[[assets]]` entries with only `kind`/`path`, and ordered
`[[dependencies]]` entries with `namespace`/`name`/`version`/`sha256`/`path`.
Assets are non-empty; dependencies may be empty. Duplicate TOML keys,
duplicate semantic entries, missing fields, type mismatches, unknown fields or
tables, and unsupported schema versions fail closed. The exact manifest input
limit is 1048576 bytes; no extra item-count limit is added.

### P05 — Normalization

Authoritative collections remain ordered immutable tuples. Namespace/name are
lowercase ASCII slugs matching `[a-z0-9]+(?:-[a-z0-9]+)*`. Version is one
canonical SemVer 2.0.0 string, retained and compared by exact string including
prerelease/build text. There is no precedence, range, preferred version, or
normalization alias. Unknown future fields/kinds fail closed and require a new
supported manifest schema. Lookup maps, sorted views, canonical bytes, and
digests are derived.

### P06 — Package Identity

`PackageIdentity = (namespace, name)` and `PackageReleaseIdentity =
(PackageIdentity, exact_version)`. Project, package, locator, version, inode,
and digest remain orthogonal. Locator/physical inode and digest never become
logical identity. `PackageReleaseIdentity` survives relocation.

### P07 — Module Ownership And Identity

One package owns one through many module-source assets. Each package is a
separately pinned compilation root. Existing `ProjectModuleIdentity` remains
path-only and root-relative within that package; it is not rewritten.
`PackageModuleIdentity = (PackageReleaseIdentity, ProjectModuleIdentity)` is
the outer composition. Two packages may each own `a.pietto`, and relocation of
the package directory preserves module identity.

### P08 — Closed Typed Assets

The exact Phase 55 v1 closed kind set is `{module_source}` (`MODULE_SOURCE`).
`PackageAssetIdentity` is `(PackageReleaseIdentity, normalized
package-relative path)`; kind is an authoritative discriminator, not a second
identity. Packaging is source/module level. Type aliases, enums, shapes,
declarations, and resources are derived module facts, not parallel assets.
Duplicate normalized paths, missing source, unsupported or unknown kind, and
present/future cross-kind reuse of one path fail closed. Phase 66 may add kinds
only through a new manifest schema.

### P09 — Exact Dependencies

Every occurrence retains source release, declaration ordinal, exact target
namespace/name/version, required lowercase SHA-256 package content pin, and
required local path. Source order and multiplicity are retained before
validation. There are no aliases, optional/dev/peer roles, ranges, feature
flags, asset selectors, solving, lockfile, or preferred-version selection.

### P10 — Local Locators

The internal locator kind is `LOCAL_DIRECTORY` only. Root package path is
project-relative. A dependency path is manifest-directory-relative and may
contain parent steps only when the normalized target remains within the
once-pinned project root. Asset paths are package-root-relative and cannot
escape. Absolute paths, URIs, environment interpolation, ambient discovery,
unchecked symlinks, network, callbacks, plugins, database access, and
executable hooks are rejected.

### P11 — Trusted Loading

Pin the project root and then each package directory; open a regular
non-symlink manifest and assets with no-follow descriptor traversal; compare
inspected/opened/final fstat facts; enforce containment and byte limits;
reverify roots and leaves; validate expected release and content digest before
acceptance. Compose the Phase 54 trust operations rather than duplicating
them. Malformed, missing, retargeted, replaced, changed, or substituted input
produces no partial accepted package.

### P12 — Dependency Closure Ordering And Conflicts

Discovery uses a finite iterative worklist and retains every ingress
occurrence. SCC analysis is iterative. Successful load order is
dependency-first topological order with independent-ready tie by
`(namespace, name, exact_version)`; diagnostics retain root/dependency
declaration order. Same-source duplicate exact edges are rejected with the
full bucket. One exact release/digest/physical root reached by a diamond loads
once and retains every edge. Same release with conflicting digest, or the same
release/digest at different physical roots, fails with no winner. Different
exact versions are distinct and may coexist. Multiple locators to the same
verified physical release coalesce only operationally while retaining all
ingress. Self and multi-node cycles block every SCC member without a cascading
winner.

### P13 — Diagnostics And Rejections

No new `PIE-*` range is created by this decision. `PIE-S2701` through
`PIE-S2707` retain their exact module meanings after a package is structurally
accepted. Package failures use Phase 55-owned messages/path facts through the
existing `ProjectDiscoveryError` and Project JSON v2 error envelope without
changing its shape or existing kind meanings. Detailed `PackageLoadRejection`
values remain private. Manifest/root causes precede asset/dependency causes;
independently observable roots are preserved and derived missing/blocked
cascades are suppressed.

### P14 — Public Private And Later Ownership

Schema-v3 `[package]` and `pietto-package.toml` v1 are user-authored input
schemas. Existing project-check entrypoints may consume them only in later
Phase 55 slices. Normalized carriers, pinned roots, occurrence ledgers,
indexes, content digests, load plans, inspection bytes, rejection values, and
vectors remain private. Slice 1 adds no Project JSON v2 field, Artifact v1
field, explain/package artifact, public export, package version, dependency,
workflow, tag, Release, publish, sign, attest, remote, solver, lockfile, Rust,
dialect, Project IR, JOIN, or SQL behavior.

## Exact Eleven Architecture Decisions

### A01 — One Authority Root And Derived Projections

The accepted manifest document plus exact opened asset snapshots is the
package authority root. The normalized carrier is its immutable
representation; indexes, maps, digests, inspection, serialization, and load
plans are one canonical root-derived family, never independent authorities.

### A02 — Layered Identities

Project root identifies activation context; `PackageReleaseIdentity` scopes a
package; `ProjectModuleIdentity` remains inner root-relative identity; and
`PackageModuleIdentity` composes them. Selected input is an ordered loading
fact. Owner, asset, locator, version, and digest never alias one another.

### A03 — Package Compilation Islands

Each accepted package runs the existing Phase 54 module pipeline inside its
own pinned root. Dependency packages are loaded and validated but do not
become package-qualified bindings, re-exports, Project IR, SQL, or Phase 59
attribution. The root-package output remains the only project result.

### A04 — Domain-separated Content Digest

Every manifest and asset retains exact opened-byte SHA-256. Package content
SHA-256 covers domain tag `pietto.package.content.v1` and length-framed
canonical normalized manifest schema, identity/version, ordered asset
ordinal/kind/path/byte-count/source-digest, and ordered dependency
ordinal/target identity/version/pin fields. Absolute paths, inode/device facts,
and locator transport strings are excluded so relocation does not change
content identity. A package never embeds its own digest.

### A05 — Collection Algebra

Authority collections are tuples preserving exact order and multiplicity.
Maps/sets are membership or lookup conveniences only. Duplicate validation
precedes canonical traversal and records complete buckets; value-equal foreign
or root-mixed products are rejected.

### A06 — Iterative Deterministic Closure

Closure uses an iterative worklist, iterative SCC, and deterministic Kahn
ordering. Dependency DFS is not recursive at unbounded local depth, and
dict/set iteration is never observable order. Canonical cycle witnesses are
derived views and do not replace complete SCC/edge evidence.

### A07 — No-winner Conflict Algebra

Duplicate, cycle, digest, identity, and physical-root conflicts have no
preferred package, locator, version, or edge. Same-node diamonds preserve all
direct edges; different versions coexist as distinct exact nodes.

### A08 — Closed Private Rejection Algebra

The exact 27 values are:

```text
ACTIVATION_SCHEMA
MANIFEST_MISSING
MANIFEST_NOT_REGULAR
MANIFEST_CHANGED
MANIFEST_TOO_LARGE
MANIFEST_INVALID_UTF8
MANIFEST_INVALID_TOML
MANIFEST_SCHEMA
PACKAGE_IDENTITY
PACKAGE_VERSION
ASSET_SCHEMA
ASSET_UNKNOWN_KIND
ASSET_DUPLICATE
ASSET_MISSING
LOCATOR_INVALID
LOCATOR_ESCAPE
ROOT_OR_LOCATOR_MUTATED
OPENED_IDENTITY_MISMATCH
ASSET_CHANGED
PACKAGE_DIGEST_MISMATCH
DEPENDENCY_DUPLICATE
DEPENDENCY_PIN_CONFLICT
DEPENDENCY_MISSING
RELEASE_PHYSICAL_CONFLICT
DEPENDENCY_CYCLE
DEPENDENCY_BLOCKED
MODULE_REJECTED
```

Pure normalized results contain no host path, inode, exception, locale,
timestamp, or rendered diagnostic payload.

### A09 — One Private Inspection Family

Exactly one deterministic package projection/serializer consumes the accepted
root and operational load plan. It is neither the Phase 58 public artifact nor
a manifest reserializer.

### A10 — Pure And Differential Boundary

One total pure evaluator consumes portable values and returns success or one
normalized rejection family. Vectors cover hash-seed/process/order,
cardinality, overlap, cycle, diamond, conflict, relocation, and substitution.
No Rust, Cargo, or FFI production exists.

### A11 — Active Gate And Publication Workflow

Gate 2 remains dirty `main`, empty real index, unstaged, and offline with no
branch/commit/push/CI. Gate 3 alone owns the topic branch and publication. The
moving active-Gate carrier remains
`tests/_phase54_active_gate2_manifest.py`; every frozen Phase 54 historical
projection remains unchanged. Existing topology code obtains the moving branch
from that carrier. Slice 1 changes no workflow or topology implementation.

## Phase 55 Versus Phase 59 67 And 68

Phase 55 owns exact user-authored local declarations, trusted local loading,
complete direct occurrence evidence, deterministic operational closure/load
order, rejection, and private validation/inspection.

Phase 59 retains a queryable package graph, multi-hop path product,
package-level attribution, provenance, origin, and lineage. A private Phase 55
`PackageLoadPlan` is not that product.

Phase 67 retains registry, remote locator resolution, network fetch,
installation, cache/update, trust policy, signatures, and remote I/O.
`LOCAL_DIRECTORY` is the only Phase 55 locator kind.

Phase 68 retains ranges, compatibility selection, solver objectives, preferred
versions, canonical lockfile generation/consumption, and production Rust.
Exact release/digest pins and a future exact-result handoff do not solve.

## Phase 56 Through 70 Readiness Pulled Forward

- Phase 56: preserve capability facts and only a future schema-upgrade boundary; no profile/checker.
- Phase 57: backend-neutral future requirement boundary; no catalog/reference field or database action.
- Phase 58: private deterministic inspection/serialization only; no public artifact.
- Phase 59: direct ordered occurrences and operational load plan only; no graph/attribution/provenance/lineage product.
- Phases 60-65: preserve current window/generic/nullability/aggregate/grouped facts; no new semantics/IR/SQL.
- Phase 66: stable `MODULE_SOURCE`, closed v1 set, schema-versioned extensibility, and unknown-kind rejection; no advanced assets/facades.
- Phase 67: local-directory locator/source-identity seam only; no remote behavior.
- Phase 68: exact pins, pure procedures/vectors, exact-result handoff only; no ranges/solver/lockfile/Rust.
- Phases 69-70: backend-neutral identity and private/public separation only; no lowering, dialect, public lineage/schema, ecosystem, or release product.

## Route Screen Eight Through Sixteen

The scoring vector is semantic completeness / redesign avoidance / later
ownership / cohesion / dependency+parallelism / risk containment / reader
burden / CI efficiency / public-boundary containment. The first four and last
criteria have weight 2; the others have weight 1; maximum is 70.

| Slices | Disposition | Score / vector | Reason |
| ---: | --- | --- | --- |
| 8 | `REJECTED_HARD_GATE` | not scored | over-merges activation/manifest and dependency/trust/conflict owners |
| 9 | `QUALIFIED` | 48; `4/3/4/3/3/3/3/3/4` | merges identity/assets and loader/load-plan owners |
| 10 | `QUALIFIED` | 54; `4/4/4/4/3/4/3/4/4` | merges dependency declaration with conflict/cycle diagnostics |
| 11 | `QUALIFIED` | 60; `4/4/5/4/4/4/4/4/5` | merges inspection with pure/differential/compatibility hardening |
| 12 | `QUALIFIED_SELECTED` | 67; `5/5/5/5/4/5/4/4/5` | every authority root has a coherent production/test boundary |
| 13 | `QUALIFIED_EXCEPTIONAL` | 65; `5/5/5/5/4/5/3/3/5` | valid loader/module split adds reader/CI cost without improvement |
| 14 | `QUALIFIED_EXCEPTIONAL` | 64; `5/5/5/5/4/5/3/2/5` | valid dependency/traversal split adds an unjustified publication boundary |
| 15 | `REJECTED_HARD_GATE` | not scored | splits one rejection algebra into an unverifiable slice |
| 16 | `REJECTED_HARD_GATE` | not scored | divides one asset authority root as padding |

The highest qualified score selects twelve slices; no tie rule is needed.

## Exact Twelve-slice Route Ownership And Prerequisites

| Slice | Exact title | Prerequisites | Production owner | Test owner | Safe parallelism | Completion condition |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | Scope, Authority, Phase-start Expansion Audit, Package Decisions, Activation, And Route Lock | verified Phase 54 completion and maintenance baseline | authority plan/spec/roadmap/active-Gate contract only; no product code | focused static Slice 1 audit plus reader/hash/topology closure | none | Gate 3 exact reviewed-tree publication makes Phase 55 `ACTIVE` and Slice 1 `COMPLETED` |
| 2 | Explicit Package Activation, Compatibility, And Immutable Package Carrier | S01 | project config/model/carrier | schema1/schema2/schema3 activation and immutable carrier tests | none before public input boundary is frozen | exclusive activation and exact legacy/package-absent compatibility pass |
| 3 | Package Manifest Input Schema And Canonical Normalization | S02 | manifest parser/validator/normalized document | strict TOML, field, ordering, multiplicity, size, and forward-compatibility tests | none | one strict v1 authority document is accepted/rejected deterministically |
| 4 | Package Identity, Exact Version, And Content Digest | S03 | identity/version/digest values and canonical framing | slug/SemVer/relocation/substitution/foreign-root property tests | may proceed in parallel with S06 after S03 interfaces freeze; publication sequential | orthogonal release identity and derived digest invariants pass |
| 5 | Closed Typed Asset Model And Asset Catalog | S04 | `MODULE_SOURCE` asset identity/catalog | cardinality/duplicate/missing/unknown/cross-kind property tests | may overlap late S06 with disjoint files after shared path/identity types freeze; publication sequential | source/module-level closed set and Phase 66 extension rule pass |
| 6 | Trusted Local Package Locator And Containment Boundary | S03 | local locator and trusted package-root/manifest open procedures | escape/symlink/retarget/replacement/TOCTOU/duplicate-physical tests | may run beside S04/S05 after manifest path interface freezes; publication sequential | every accepted locator is pinned, contained, stable, and local-only |
| 7 | Deterministic Local Manifest Loading And Package/Module Integration | S02-S06 | package loader, per-package selected inputs, module-island orchestration | manifest-to-module loading, multi-module, same-inner-path, compatibility tests | none | one root package and its exact local assets load without rewriting module identity |
| 8 | Exact Dependency Declarations And Deterministic Local Load Plan | S04,S06,S07 | dependency occurrence ledger, closure, SCC, dependency-first plan | 0/1/N/direct/multihop/order/hash-seed/termination tests | none | exact local closure/load order is complete, deterministic, and private |
| 9 | Dependency Collision, Cycle, Diamond, And Rejection Diagnostics | S08 | conflict/cycle/rejection/cascade adapter | duplicate/pin/physical/self-cycle/multi-cycle/diamond/blocker-root tests | none | no-winner algebra and existing module diagnostic compatibility pass |
| 10 | Private Package Inspection And Canonical Serialization | S05,S08,S09 | single package inspection projection/serializer | canonical bytes/root-mixing/order/multiplicity/privacy tests | none | one deterministic private root-derived representation passes |
| 11 | Pure Package Boundary, Differential Vectors, Compatibility, And E2E Hardening | S02-S10 | pure value/evaluator/reference harness and integration hardening | differential/property/schema1/schema2/E2E/package-smoke tests | vector authoring may parallelize by disjoint dimensions after interfaces freeze; merge/publication sequential | all behavioral matrices and compatibility locks converge on one exact tree |
| 12 | Completion Audit, Status Lock, And Phase56 Handoff | S01-S11 completed | status/completion/handoff authority only | completion, inventory, privacy, retained-owner, reader/hash/topology audit | none | exact reviewed publication proves Phase 55 `COMPLETED` and next Phase 56 Gate 0/Gate 1 |

The route is fixed. Publication is sequential even where implementation work
may safely overlap.

## Three-round Risk-adaptive Workflow

Slices 1 through 10 use three rounds because they freeze or implement input
schema, identity, trust, dependency, loading, diagnostics, or canonical facts.
Slices 11 and 12 remain risk-adaptive while retaining every logical Gate and
exact-tree publication; any production, active-Gate, reader/topology, or public
compatibility movement uses three separate rounds. Publication is sequential
for every Slice. A purely test/docs hardening or completion tree may combine
Round 1 planning with the separately verified offline Gate 2 only when that
Slice's own Gate 1 explicitly authorizes the combination.

Gate 2 is dirty `main`, not an unpushed topic branch: no branch, staging,
commit, push, PR, or CI. Candidate identity is the baseline, exact A/M/D set,
empty real index, canonical patch, identity manifest, and reconstructible
reviewed tree. Gate 3 creates
`phase55/slice1-scope-authority-expansion-readiness-route-lock` and uses subject
`Add Phase 55 scope authority and route lock`.

## Exact Gate 2 Allowlist And Reader Closure

Gate 1 Corrective Addendum 1 supersedes the projected allowlist only: it is
`A3_M52_D0` with 47 mechanical readers. Final counts are sealed-tree facts.

Added paths:

```text
docs/plan/phase-55-semantic-package-asset-schema-and-deterministic-local-loading.md
docs/spec/phase55-slice1-scope-authority-expansion-readiness-and-route-lock-v1.md
tests/test_phase55_slice1_scope_authority_expansion_readiness_and_route_lock.py
```

Directly modified authority/state paths:

```text
README.md
docs/spec/pietto-active-roadmap-phase53-70-v2.md
docs/spec/pietto-v0.9.md
tests/_phase54_active_gate2_manifest.py
tests/test_phase54_completion_audit_status_lock_and_phase55_handoff.py
```

The 47 corrected mechanical readers are exactly:

```text
tests/test_phase21_group_by_hardening_audit.py
tests/test_phase24_aggregate_expression_arguments_readiness.py
tests/test_phase24_cli_json_output_hardening.py
tests/test_phase24_completion_audit.py
tests/test_phase26_completion_audit.py
tests/test_phase27_completion_audit.py
tests/test_phase28_completion_audit.py
tests/test_phase29_completion_audit.py
tests/test_phase30_completion_audit.py
tests/test_phase33_completion_audit.py
tests/test_phase51_aggregate_grouped_downstream_propagation.py
tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py
tests/test_phase51_completion_audit_and_status_lock.py
tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py
tests/test_phase52_aggregate_signature_algebra_facts.py
tests/test_phase52_completion_audit_and_status_lock.py
tests/test_phase52_expression_stage_clause_capability_facts.py
tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py
tests/test_phase52_scalar_function_operator_signature_facts.py
tests/test_phase53_completion_audit_and_status_lock.py
tests/test_phase53_generic_type_variable_exact_compatibility_contract.py
tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py
tests/test_phase53_multiple_window_outputs_final_order_alias_downstream_schema_lineage_contract.py
tests/test_phase53_nullability_algebra_signature_result_formula_contract.py
tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py
tests/test_phase53_percent_rank_cume_dist_ntile_contract.py
tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py
tests/test_phase53_rank_dense_rank_peer_semantics_contract.py
tests/test_phase53_row_number_direct_field_mvp_contract.py
tests/test_phase53_window_generic_nullability_foundation_scope_lock.py
tests/test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py
tests/test_phase53_window_local_ordering_direction_determinism_contract.py
tests/test_phase53_window_spec_function_identity_ast_contract.py
tests/test_phase53_window_syntax_contextual_grammar_contract.py
tests/test_phase54_cross_module_table_query_relation_resolution_row_facts_legacy_compatibility.py
tests/test_phase54_cross_module_type_alias_enum_shape_source_resolution.py
tests/test_phase54_import_export_contextual_grammar_ast.py
tests/test_phase54_local_export_visibility_module_facades.py
tests/test_phase54_local_import_module_export_foundation_scope_lock.py
tests/test_phase54_module_attribution_dependency_origin_provenance_lineage.py
tests/test_phase54_module_graph_cycles_diagnostics_deterministic_ordering.py
tests/test_phase54_module_identity_selected_input_index_trusted_local_loader.py
tests/test_phase54_named_import_alias_binding_environments_collision_rules.py
tests/test_phase54_package_neutral_identity_layering.py
tests/test_phase54_rust_ready_pure_boundaries_differential_vectors.py
tests/test_phase54_schema_v2_explicit_module_carrier.py
tests/test_phase54_semantic_fact_preservation.py
```

There are no deletions. `AGENTS.md` remains unchanged. Discovery is read-only;
reader/hash replacements are dependency-first and occurrence-counted. Closure
requires independent `reader additions = 0` and `hash/digest delta = 0`.

## Property And Validation Contract

The declarative property matrix covers cardinality 0/1/2/3; identity
duplicates; value-equal foreign and overlapping roots; direct/renamed/
multi-hop/multi-path identity; manifest order/field/schema/kind failures;
locator escape/symlink/retarget/replacement/TOCTOU; direct/multihop/cycle/
diamond/version/digest/physical dependency cases; complete occurrence buckets;
no first-match, single-winner, partial-scan, or lossy dedup; mapping/hash-seed/
process permutations; exact availability-state preservation; schema-v1 and
package-absent schema-v2 compatibility; and public/privacy/export/JSON/
Artifact/SQL/dependency/workflow/version/release negative locks.

Gate 2 validates the focused Slice 1 module; every discovered reader; Python
3.12 and 3.13 full suites; Ruff format check-only and lint; production and test
Pyright; fixed-point reader/hash closure; all publication topology projections;
generated inventory 8; goldens 37; `uv lock --check`; offline package smoke;
installed CLI `pietto 0.1.0`; schema-v1 and package-absent schema-v2
compatibility; exact scope; canonical patch; identity manifest; and independent
reviewed-tree reconstruction.

## Evidence And Gate 3 Contract

The controlling evidence targets are:

```text
/home/mianliwang/.local/state/pietto/evidence/pietto-phase55-slice1-gate2-scope-authority-expansion-readiness-and-route-lock.txt
/home/mianliwang/.local/state/pietto/evidence/pietto-phase55-slice1-gate3-publication-reconciliation.txt
```

Each is a regular non-symlink mode `0644` file created once with
`O_CREAT | O_EXCL | O_NOFOLLOW`, never overwritten, appended, renamed over, or
chmod-replaced, and contains exactly one terminal at EOF.

Gate 3 requires the exact reviewed tree, one non-amend history, natural
exact-head pull-request CI attempt 1, complete exact-head review settlement,
reviewed-tree identity, squash parent equal to the frozen baseline, squash
tree equal to the reviewed tree, natural exact-head `main` push CI attempt 1,
minimum-safe fetch and fast-forward-only reconciliation, clean worktree/index,
topic cleanup, and immutable Gate 3 evidence.

## Package Workflow Version And Release Guards

Package and installed CLI version remain `0.1.0`; runtime dependency remains
only `antlr4-python3-runtime>=4.13.2`; workflow remains only `ci.yml`;
generated inventory remains 8 and goldens remain 37. Slice 1 adds no package
manifest behavior, production source, public field, dependency, lockfile,
workflow, version, tag, Release, publish/upload, signing, or attestation.

## Stop Conditions

Stop for baseline or evidence drift, contradiction with higher authority,
material product/architecture change, substantive non-mechanical path outside
the allowlist, reader closure that does not converge, behavioral or
compatibility failure, dependency/workflow/version/public/release authority,
tree mismatch, or inability to create immutable evidence safely. Newly
expected hash cascades and formatting/static-reader corrections inside the
frozen authority remain mechanical.
