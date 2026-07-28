# Phase 54 Slice 1 Scope, Authority, Phase-start Expansion Audit, Decisions, Activation, And Route Lock v1

## Purpose And Slice Identity

Phase 54 is **Local Import / Module / Export Foundation**. Slice 1 is **Scope,
Authority, Phase-start Expansion Audit, Decisions, Activation, And Route
Lock**. This specification freezes the authorized product and architecture
decisions, permanent governance rule, exact sixteen-slice route, later-owner
boundary, Gate contracts, and post-publication lifecycle.

Slice 1 is static authority/governance/documentation/testing work only. It
does not implement Phase 54 compiler behavior.

## Trusted Phase 53 Baseline And Binding Evidence

The trusted pre-Slice-1 baseline is
`af92f30c22e5d3df5219554a0663855a5b9f51a6`, tree
`5abfc0253ce999a4e7e5cbe3e3ca8c5cd64023ad`, parent
`3c1feab5bc70d407e9e4d7ccd0c5d489eec0ee68`, subject `Complete Phase 53
status and compatibility audit`.

The binding inputs are:

- Phase 54 grounding report SHA-256
  `8dda8437aa66be08130baf4480a4d894adff3980c5d4215697a78db7b1277ba5`;
- Phase 53 Slice 16 Gate 0/1 SHA-256
  `33faf77e603ac405ce478974dc960b38327d4e3e252d31d0d1fe614f86191d86`;
- Phase 53 Slice 16 Gate 2 SHA-256
  `1b8210d71133aaff33896deace46dee38b01de19f30aa91ea694d91bffdfbefe`;
- Phase 53 Slice 16 Gate 3 SHA-256
  `9a0cd5feb0500f6b27ec06acce85a086e33817503e26907e6a8cd19887320b81`;
  and
- Phase 54 Slice 1 Gate 0/1 plan SHA-256
  `5f6eefd516b9532e90ed89e439f12e78411ca6ceb3619fa91f2ea1886a9c6687`.

Phase 53 and its sixteen slices are complete. Phase 54 remains `UNSTARTED`
throughout Slice 1 Gate 2.

## Authority Hierarchy And Historical Readiness

The controlling end-to-end Slice Goal and live repository facts outrank this
document. `AGENTS.md` applies repository-wide. After the exact Gate 3
activation condition, `docs/spec/pietto-active-roadmap-phase53-70-v2.md` is
the sole current roadmap authority. The v1 roadmap and the Phase 50 import,
module, export readiness specification remain immutable historical evidence.

Historical readiness is evidence, not automatic current production authority.
The Phase 54 grounding recommendations became authority only through the
explicit reconciliation package in the controlling Slice Goal.

## Lifecycle And Conditional Activation

Gate 2 persistence does not start Phase 54. Phase 54 becomes `ACTIVE` and
Slice 1 becomes `COMPLETED` only when Gate 3 publishes the exact reviewed tree
on the required branch, creates exactly one commit and one normal branch push,
observes unique natural exact-head pull-request CI attempt 1 succeed, squash
merges the exact reviewed tree, observes unique natural exact-head `main` push
CI attempt 1 succeed, reconciles local `main` by fetch and ff-only update,
cleans the publication branch, and records immutable Gate 3 evidence.

That condition leaves Slices 2-16 `UNSTARTED` and sets
`next=PHASE54_SLICE2_GATE0_GATE1`. It does not authorize Slice 2.

## Static-only Slice 1 Boundary

Slice 1 may add one master plan, this scope lock, one permanent governance
specification with embedded template, one successor active roadmap, one
focused static test module, one concise `AGENTS.md` rule, and bounded executing
reader repairs.

It changes no grammar, generated ANTLR, AST, parser, project configuration or
loader implementation, semantic implementation, IR, SQL, CLI, serializer,
public API, diagnostic emission, fixture, golden, example, dependency,
lockfile, workflow, package version, runtime, network, release, signing,
attestation, or Rust source.

## Current Production Ledger

`CURRENT_PRODUCTION` is frozen as:

| ID | Verified current production |
| --- | --- |
| CP-01 | Project schema version 1 with `[sources]` include/exclude is the only accepted configuration schema. |
| CP-02 | Project discovery resolves one root, performs deterministic no-symlink traversal, and selects normalized project-relative `.pietto` paths. |
| CP-03 | Selected paths are physically deduplicated by device/inode during selection and parsed in source-path order. |
| CP-04 | Project parse/check reads selected files and preserves one `Script` per `ProjectParsedInput`. |
| CP-05 | Project semantic collection builds a flat project-wide catalog before relation resolution. |
| CP-06 | Existing type, enum, shape, source, table, query, row-schema, field-origin, aggregate, grouped, window, nullability, generic, result-role, capability, dependency, provenance, and lineage facts remain current. |
| CP-07 | CLI JSON v1, Semantic Metadata Artifact v1, and Project JSON v2 are distinct unchanged public families. |
| CP-08 | PostgreSQL is public, MySQL remains private, SQL is generated only, and package/CLI version is `0.1.0`. |

No row in this ledger implies module syntax, imports, exports, module identity,
module graph resolution, trusted descriptor loading, or package behavior.

## Current Readiness Ledger

`CURRENT_READINESS` is frozen as:

| ID | Existing readiness seam |
| --- | --- |
| CR-01 | Immutable project/path/config/input/parsed-input carriers exist. |
| CR-02 | Deterministic source selection, inside-root final-target checking, and physical dedup exist but are not a pinned descriptor loader. |
| CR-03 | Collect-before-resolve project semantics, deterministic dependency graphs, and structured diagnostics provide reusable private procedure seams. |
| CR-04 | Stable row schema, field origin, aggregate/grouped/window, generic/nullability, result-role, capability, provenance, and lineage facts can be made identity-safe. |
| CR-05 | Private serializer and metadata patterns demonstrate deterministic ordered output without authorizing a new public artifact. |
| CR-06 | Phase 50 records historical import/module/export and package readiness boundaries. |

Readiness is neither production acceptance nor public schema.

## Retained Later Ledger

`RETAINED_LATER` is frozen as:

| ID | Retained product boundary | Owner | Necessity |
| --- | --- | ---: | --- |
| RL-01 | final semantic-package manifest and typed asset schema | 55 | public package/schema publication needs separate authority |
| RL-02 | capability-profile language and declared-checking product | 56 | separately authorized language/schema boundary |
| RL-03 | PostgreSQL extension catalog content | 57 | evidence-backed catalog ownership is distinct from modules |
| RL-04 | public explain/portability/package inspection artifact v1 | 58 | independently versioned public serializer family |
| RL-05 | package-level local graph integration | 59 | package ownership follows the Phase 55 asset schema |
| RL-06 | advanced window frames and named windows | 60 | separate window product semantics |
| RL-07 | project IR composition | 61 | cross-module semantic facts do not imply project IR |
| RL-08 | relationship/JOIN/grain/fanout | 62 | distinct multi-relation product semantics |
| RL-09 | project emit-sql, multi-relation SQL, and QUALIFY | 63 | backend lowering needs project IR and separate dialect evidence |
| RL-10 | coercion, temporal, Decimal, native mapping | 64 | unresolved advanced type semantics |
| RL-11 | advanced aggregation/grouping | 65 | separate semantic ownership |
| RL-12 | wildcard/qualified/export-from and advanced package assets | 66 | separately authorized advanced module/package surface |
| RL-13 | registry/fetch/install/cache/trust | 67 | remote I/O and trust authority |
| RL-14 | ranges, solver, canonical lockfile, production Rust kernel | 68 | solver, lockfile, dependency, build, and supply-chain authority |
| RL-15 | extension lowering and additional dialect | 69 | additional dialect production ownership |
| RL-16 | public schema/lineage expansion and release readiness | 70 | public schema and release authority |

## Phase-start Expansion, Pull-forward, And Readiness Audit

Slice 1 applied the permanent audit in
`docs/spec/pietto-phase-start-expansion-pull-forward-readiness-governance-v1.md`.
It reverified live authority and architecture, challenged the older minimum
boundary, atomized Phase 55-70 work, separated production from private and
contract readiness, required necessity for every deferral, screened routes
8-16, and froze the three ledgers above.

The audit found that basic explicit named re-export is required for a coherent
local module facade and is stable enough for Phase 54 production ownership.
Advanced module/package facade behavior remains with Phase 66. It also found
that private inspection/serialization and Rust-ready differential hardening
have independent production/test/dependency surfaces, justifying separate
Slices 14 and 15 and therefore the exact sixteen-slice route.

## Exact Five Product Decisions

### P1 — Activation And Module Identity

Schema version 1 stays exact legacy-flat mode. Schema version 2 explicitly activates project-wide module mode.
Each selected `.pietto` file is one module identified by its exact normalized project-root-relative
selected-input path including suffix, with
case and Unicode preserved. No heuristic, mixed per-file mode, source-level
`module` declaration, or physical identity as semantic identity.

### P2 — Import / Export Syntax

Future grammar uses contextual top-level
indentation blocks:

```pietto
import "models/customer.pietto":
    shape Customer
    query orders as imported_orders

export:
    shape Customer
    query imported_orders
```

Targets are exact selected project-relative `.pietto` strings. Eligible kinds
are `type`, `enum`, `shape`, `source`, `table`, and `query`. Alias direction is
`exported_name as local_name`; local references stay unqualified. There is no
dotted module reference, wildcard, side-effect import, brace form, package
target, or `export from` shorthand.

### P3 — Visibility, Eligibility, And Explicit Named Re-export

Explicit-module declarations are
private by default. Eligible local declarations and explicitly imported local
bindings may be named in `export`; the latter is explicit named re-export, and
every hop is explicit while the module graph is acyclic. Constraint,
derive, relationship metadata, future callables, wildcards, implicit
transitive exports, source-qualified forms, and package-aware facades remain
ineligible or later-owned.

### P4 — Collision, Cycles, Ordering, And Diagnostics

No local/import/alias/export
binding shadows another and no ambiguity receives a winner. Textual import
order does not affect meaning. Module cycles use a distinct fail-closed graph.
Issues are deterministic and source ordered. `PIE-S2701` through `PIE-S2707`
are reserved exactly as defined below but are not implemented or emitted here.

### P5 — Root, Symlink, Path, TOCTOU, Dedup, And Digest

Future production pins one canonical root, rejects config symlinks, preserves no-symlink traversal,
accepts a source symlink only if its final target remains inside the pinned
root and the opened descriptor matches selection, rejects retarget/escape/
mismatch/duplicates, digests exact opened bytes, and resolves only against an
immutable selected-input index without import-driven discovery.

## Exact Five Architecture Decisions

### A1 — Layered Immutable Identities

Keep distinct project/display path,
pinned root, selected physical source, module, declaration `(module,
namespace, declaration_kind, declared_name)`, importing binding, and source
snapshot/digest carriers. AST object identity and locations are not
cross-module identity.

### A2 — Selected-input Index And Trusted Local Loader

Build an immutable,
ordered exact module index only from validated selected inputs and trusted
snapshots. It is not a global/callback registry, filesystem walker,
excluded-file probe, package loader, or network registry.

### A3 — Pure Resolver Procedure And Diagnostic Adapter

Parse all modules, collect
local declarations, validate exports, validate the module graph, build import
environments, resolve type/relation facts, propagate facts to a deterministic
fixed point, return ordered structured issues, and adapt issues to diagnostics
separately. Preserve a distinct legacy-flat resolver; never flatten explicit
modules into it.

### A4 — Identity-safe Project-model Facts

Prefer focused private
`_project/module_*.py` sidecars and thread stable declaration identity through
all affected facts without changing public JSON or artifact families.

### A5 — Private Inspection, Canonical Serialization, And Rust-ready Seam

Use deterministic
private inspection facts, canonical private serialization, stable primitive
records, no Python-object identity or ambient callbacks across the pure
boundary, frozen differential vectors, and Python reference behavior. Add no
public schema, package manifest, Rust, Cargo, PyO3, maturin, native wheel,
dependency, version, release, or supply-chain behavior.

## Phase-start Route Comparison And Selection Record

The audit screened every route count from 8 through 16. Counts 8 and 9 fail a
hard gate because independently testable loader/security, grammar/AST,
identity/catalog, resolver, fact-preservation, and hardening surfaces would be
merged. Counts 10-12 remain qualified but overloaded. Counts 13-15 improve
cohesion, but the fifteen-slice form still combines private inspection and
canonical serialization with a downstream Rust-ready pure boundary,
differential vectors, and end-to-end hardening.

| Slices | Weighted score / 70 | Result |
| ---: | ---: | --- |
| 8 | hard-gate failure | independently unverifiable merged slices |
| 9 | hard-gate failure | loader/security and resolver/fact overload |
| 10 | 49 | qualified, overloaded |
| 11 | 53 | qualified, overloaded |
| 12 | 54 | qualified, redesign risk remains |
| 13 | 57 | qualified |
| 14 | 60 | qualified |
| 15 | 62 | qualified, one two-surface slice remains |
| 16 | 63 | selected |

Sixteen is selected because the Slice 14 producer surface and Slice 15
consumer/hardening surface satisfy all three exceptional-split tests:
independent production ownership, independent focused-test ownership, and a
real dependency boundary. The larger route is not chosen to maximize scope.

## Exact Sixteen-slice Route And Prerequisites

1. Scope, Authority, Phase-start Expansion Audit, Decisions, Activation, And Route Lock - Phase 53 completion
2. Schema-v2 Explicit-module Activation And Immutable Project / Module Carrier - 1
3. Module Identity, Selected-input Index, Trusted Local Loader, And Path / Symlink Boundary - 2
4. Import / Export Contextual Grammar, Generated Parser, And Immutable AST - 1
5. Module-qualified Nominal Declaration Identity And Per-module Catalogs - 2, 4
6. Local Export Eligibility, Visibility, Explicit Named Re-export, And Facade Semantics - 5
7. Named Imports, Aliases, Binding Environments, And Collision Rules - 6
8. Module Graph, Cycles, Diagnostics, And Deterministic Ordering - 7
9. Cross-module Type Alias, Enum, Shape, And Source Resolution - 8
10. Cross-module Table / Query / Relation Resolution, Row Facts, And Legacy Compatibility - 3, 8, 9
11. Module Attribution, Dependency, Origin, Provenance, And Lineage - 10
12. Generic-signature, Nullability, Aggregate, Grouped, Window, Result-role, And Capability-fact Preservation - 10
13. Package-neutral Identity Layering, Owner / Asset-compatible Carriers, Source Digest, And Loader Readiness - 3, 11, 12
14. Private Module Inspection And Canonical Serialization - 13
15. Rust-ready Pure Boundaries, Differential Vectors, And End-to-end Hardening - 8 through 14
16. Completion Audit, Status Lock, And Phase 55 Handoff - 1 through 15

No slice is automatically authorized by this route.

## Dependency Graph And Parallelism

The route is a directed acyclic graph. Slice 4 may proceed alongside Slices
2-3 after Slice 1. Slices 11 and 12 may proceed in parallel after Slice 10 when
their shared identity contracts are frozen and production/test ownership is
disjoint. Slice 13 joins their facts; Slice 14 produces the deterministic
inspection/serialization surface; Slice 15 consumes that surface for pure
boundary and differential hardening. Publication and Git operations remain
sequential.

## Maximum Safe Pull-forward Boundary

The maximum safe Phase 54 pull-forward is the union of `IMPLEMENT_NOW`,
`PRIVATE_READINESS_NOW`, and `CONTRACT_ONLY_NOW` rows in the ledger below.
It includes coherent local module production, identity-safe private facts,
trusted local-loader contracts, private inspection/serialization, pure
procedures, and differential seams. It excludes final package schemas, public
artifacts, remote operations, solver/lockfile behavior, production Rust,
additional dialects, and release/supply-chain behavior.

## No-unnecessary-deferral Ledger

| ID / owner | Atomic item | Classification | Minimum Phase 54 artifact | Retained owner / exact necessity |
| --- | --- | --- | --- | --- |
| 55A / P55 | package-neutral owner/asset identity seam | PRIVATE_READINESS_NOW | layered private owner/asset-compatible identities | P55 final package identity |
| 55B / P55 | final semantic-package manifest | DEFER_BY_NECESSITY | negative boundary contract | DEFERRED BY NECESSITY — schema depends on completed module identity and separate manifest product semantics |
| 55C / P55 | typed semantic/support asset schema | DEFER_BY_NECESSITY | package-neutral seam | DEFERRED BY NECESSITY — asset kinds, validation, and publication semantics are not stable before manifest authority |
| 55D / P55 | exact package dependency facts | DEFER_BY_NECESSITY | module import edges only | DEFERRED BY NECESSITY — package identity and manifest must exist before exact package dependency identity |
| 55E / P55 | deterministic local package loading | DEFER_BY_NECESSITY | selected-input module loader only | DEFERRED BY NECESSITY — package asset/schema validation is absent and modules cannot infer packages |
| 56A / P56 | preserve existing capability facts across module edges | IMPLEMENT_NOW | lossless private attribution/preservation adapter | P56 profile/checking product retained |
| 56B / P56 | private capability-profile schema/carrier | DEFER_BY_NECESSITY | contract seam | DEFERRED BY NECESSITY — typed package assets are a prerequisite |
| 56C / P56 | declared capability checking and mismatch diagnostics | DEFER_BY_NECESSITY | preserve current facts only | DEFERRED BY NECESSITY — no approved profile schema or package declaration exists |
| 56D / P56 | capability-profile language | DEFER_BY_NECESSITY | explicit exclusion | DEFERRED BY NECESSITY — user-visible language semantics require separate product authority |
| 56E / charter | server discovery/runtime fallback | OUT_OF_SCOPE | none | compiler charter forbids runtime/server discovery claims |
| 57A / P57 | extension-compatible identity preservation | PRIVATE_READINESS_NOW | extensible namespace/kind identities without content | P57 catalog retained |
| 57B / P57 | private extension catalog/schema | DEFER_BY_NECESSITY | boundary contract | DEFERRED BY NECESSITY — capability-profile separation is a prerequisite |
| 57C / P57 | exact extension generic matching | DEFER_BY_NECESSITY | preserve generic facts | DEFERRED BY NECESSITY — no approved catalog/signature corpus exists |
| 57D / P57 | PostgreSQL extension seed content | DEFER_BY_NECESSITY | no seeds | DEFERRED BY NECESSITY — content requires bounded external evidence and separate catalog authority |
| 57E / charter | extension discovery/install/introspection | OUT_OF_SCOPE | none | permanent runtime/database charter exclusion |
| 58A / P58 seam | private module inspection facts | PRIVATE_READINESS_NOW | ordered private DTO | P58 public artifact retained |
| 58B / P58 seam | canonical private serialization | PRIVATE_READINESS_NOW | deterministic internal bytes | P58 independently versioned public serializer retained |
| 58C / P58 | final public artifact schema | DEFER_BY_NECESSITY | privacy/separation contract | DEFERRED BY NECESSITY — public schema requires completed package/capability/catalog facts and independent versioning |
| 58D / P58 | public explain/portability/package inspection | DEFER_BY_NECESSITY | private facts only | DEFERRED BY NECESSITY — public behavior and compatibility are separately authorized product boundaries |
| 58E / route | mutate CLI JSON v1/Metadata v1/Project JSON v2 | OUT_OF_SCOPE | exact no-new-key tests | roadmap permanently separates the new public artifact family |
| 59A / P59 seam | module attribution/dependency/origin/provenance/lineage | IMPLEMENT_NOW | module-level identity-safe facts | P59 package-level graph/attribution retained |
| 59B / P59 seam | package-neutral attribution carrier | PRIVATE_READINESS_NOW | owner-kind seam without package ID | P59 package attribution retained |
| 59C / P59 | exact local package graph | DEFER_BY_NECESSITY | pure module graph only | DEFERRED BY NECESSITY — exact package identity/dependencies do not exist |
| 59D / P59 | package provenance/lineage integration | DEFER_BY_NECESSITY | module provenance only | DEFERRED BY NECESSITY — package facts and public-schema separation are prerequisites |
| 59E / P70 | broad public package graph | DEFER_BY_NECESSITY | private only | DEFERRED BY NECESSITY — public graph waits for completed public/private package facts |
| 60A / P60 seam | preserve existing window facts across modules | IMPLEMENT_NOW | lossless adapters and regressions | P60 new window behavior retained |
| 60B / P60 | frames/value functions/named windows/aggregate-as-window | DEFER_BY_NECESSITY | preservation tests only | DEFERRED BY NECESSITY — independent language, semantic, IR, SQL, and dialect product boundary |
| 60C / P60 | Phase 51-60 coherence/release checklist | CONTRACT_ONLY_NOW | retained-owner handoff checklist | P60 executes after Phase 51-59 exact evidence |
| 61A / P61 | Project IR handoff/canonicalization boundary | CONTRACT_ONLY_NOW | stable semantic identity handoff | P61 production IR retained |
| 61B / P61 | production Project IR | DEFER_BY_NECESSITY | no IR implementation | DEFERRED BY NECESSITY — stable module composition must complete and IR is a distinct compiler layer |
| 62A / P62 | relationship/module asset boundary | CONTRACT_ONLY_NOW | relationship imports/exports fail closed | P62/P66 production retained |
| 62B / P62 | relationship binding/JOIN/grain/fanout | DEFER_BY_NECESSITY | no behavior | DEFERRED BY NECESSITY — requires Project IR and unresolved multi-relation product semantics |
| 63A / P63 | multi-relation SQL/project emit-sql | DEFER_BY_NECESSITY | explicit exclusion | DEFERRED BY NECESSITY — requires Project IR and JOIN semantics; Phase 54 has no SQL ownership |
| 63B / P63 | QUALIFY lowering | DEFER_BY_NECESSITY | preserve window facts only | DEFERRED BY NECESSITY — requires project subquery/IR rewrite and advanced window surface |
| 64A / P64 seam | module-qualified private nominal type identity | PRIVATE_READINESS_NOW | stable private declaration type identity | P64 advanced type behavior retained |
| 64B / P64 | generics/coercion/temporal/Decimal/native mapping | DEFER_BY_NECESSITY | no semantic widening | DEFERRED BY NECESSITY — independent type semantics/backend mapping authority remains unresolved |
| 65A / P65 seam | preserve aggregate/grouped facts | IMPLEMENT_NOW | identity-safe propagation | P65 advanced aggregation retained |
| 65B / P65 | filters/order/modifiers/rollup/cube/grouping sets | DEFER_BY_NECESSITY | no accepted-form widening | DEFERRED BY NECESSITY — independent grammar, semantic, IR, SQL behavior and capability prerequisite |
| 66A / P66 seam | basic explicit named re-export and local facade | IMPLEMENT_NOW | export one imported local binding; every hop named and acyclic | P66 package-aware/advanced facade only |
| 66B / P66 | wildcard import/export, source-qualified forms, and export-from shorthand | DEFER_BY_NECESSITY | fail closed | DEFERRED BY NECESSITY — advanced visibility/cycle and package semantics require completed Phase 54/55 foundations |
| 66C / P66 | callable/constraint/derive/relationship module assets | DEFER_BY_NECESSITY | exclude from eligibility | DEFERRED BY NECESSITY — ownership semantics are not stable and need separate authorization |
| 66D / P66 | advanced semantic-package assets | DEFER_BY_NECESSITY | package-neutral seam only | DEFERRED BY NECESSITY — final typed asset schema and package-aware behavior are separately owned |
| 67A / P67 | registry/fetch/install/update/cache/trust | DEFER_BY_NECESSITY | no network code | DEFERRED BY NECESSITY — requires local package foundation and explicit threat model/remote-I/O authority |
| 67B / charter | executable package hooks/plugins | OUT_OF_SCOPE | none | permanent compiler-charter exclusion absent charter-changing authority |
| 68A / P68 seam | Rust-ready DTOs and differential vectors | PRIVATE_READINESS_NOW | Python reference corpus/value boundary | P68 production Rust retained |
| 68B / P68 | dependency ranges/solver/canonical lockfile | DEFER_BY_NECESSITY | pure local module graph only | DEFERRED BY NECESSITY — exact local package graph must exist before range/solver semantics |
| 68C / P68 | production Rust kernel | DEFER_BY_NECESSITY | no Rust/build dependency | DEFERRED BY NECESSITY — requires parity, fallback, benchmark, build, dependency, and supply-chain authority |
| 69A / P69 | extension-specific lowering | DEFER_BY_NECESSITY | preserve identity only | DEFERRED BY NECESSITY — requires catalog evidence and exact backend ownership |
| 69B / P69 | additional dialect backend | DEFER_BY_NECESSITY | no dialect code | DEFERRED BY NECESSITY — requires capability evidence and separately selected dialect production ownership |
| 70A / P70 seam | public expansion compatibility boundary | CONTRACT_ONLY_NOW | no-new-public-field tests | P70 exact public design retained |
| 70B / P70 | public schema/lineage/attribution expansion | DEFER_BY_NECESSITY | private facts only | DEFERRED BY NECESSITY — requires completed public/private facts and independent serializer authority |
| 70C / P70 | ecosystem audit/Rust migration decision | DEFER_BY_NECESSITY | handoff evidence only | DEFERRED BY NECESSITY — decision requires completed ecosystem evidence and benchmarks |
| 70D / P70 | v0.2 release readiness | DEFER_BY_NECESSITY | no version/release action | DEFERRED BY NECESSITY — release, signing, attestation, and supply-chain authority remain separate |
| RLS / separate | tag/release/publish/sign/attest | DEFER_BY_NECESSITY | explicit denial boundary | DEFERRED BY NECESSITY — only a separate Release Gate 3 may mutate irreversible public state |

The ledger has exactly 54 unique rows and classification totals:

```text
IMPLEMENT_NOW=5
PRIVATE_READINESS_NOW=7
CONTRACT_ONLY_NOW=4
DEFER_BY_NECESSITY=34
OUT_OF_SCOPE=4
```

Every row has exactly one classification. A phase number is never the sole
deferral reason.

## Retained Later-phase Ownership

Phase 54 owns basic local modules and explicit named re-export. Phases 55-70
retain RL-01 through RL-16. In particular Phase 66 retains wildcard import and
export, source-qualified forms, `export from` or equivalent advanced shorthand,
callable/constraint/derive/relationship module assets, package-aware advanced
facades, and other advanced module/package assets. No retained row is activated
or implemented by Slice 1.

## Legacy-flat And Schema-v2 Activation

`schema_version = 1` remains byte- and behavior-compatible legacy-flat mode.
Only `schema_version = 2` activates explicit modules project-wide. Mixed mode,
heuristics, filename conventions, and source-level module declarations are
forbidden. The explicit-module resolver is separate; it may reuse pure facts
but may not flatten its declarations into the legacy global catalog.

## Contextual Import Export And Alias Syntax

`import`, `export`, and `as` are contextual where compatibility permits. Both
forms are top-level colon-plus-indentation blocks. Import entries name one
eligible declaration kind and exported name, optionally followed by `as` and a
local name. Export entries name one eligible kind and local binding. All
references inside the module remain namespace-local and unqualified.

Slice 4 owns future grammar/generated/AST implementation. Slice 1 records only
this contract and changes no accepted source.

## Visibility Eligibility Named Re-export And Facade Boundary

Declarations are private by default. Local eligible declarations and explicit
import bindings may be exported. Re-export is explicit at every hop and cannot
create or hide a cycle. No wildcard, implicit transitive export, package target,
source qualification, or advanced facade is accepted in Phase 54.

## Collision Cycle Ordering And PIE-S2701 Through PIE-S2707 Reservation

The reserved ownership is:

- `PIE-S2701`: invalid, unselected, or unresolved local module target;
- `PIE-S2702`: duplicate or conflicting module identity;
- `PIE-S2703`: module import cycle;
- `PIE-S2704`: duplicate, unknown, ineligible, or invalid export request;
- `PIE-S2705`: unknown, private, or non-exported imported declaration;
- `PIE-S2706`: local/import/alias/export binding collision; and
- `PIE-S2707`: unresolved explicit-module reference or unsupported advanced form.

Later owning slices must freeze exact messages, primary spans, canonical target
ordering, and cascade suppression. Slice 1 does not add these codes to the
diagnostic inventory or emit them. `PIE-S2001`, `PIE-S2002`, `PIE-S2301`, and
`PIE-S2302` are not repurposed.

## Pinned Root Symlink TOCTOU Dedup And Digest Boundary

One canonical root context is resolved and pinned once. Config symlinks are
rejected. Directory traversal does not follow symlinks. A final source symlink
may be accepted only after inside-root resolution and opened-descriptor identity
verification. Root retarget, source retarget, path escape, selected/opened
identity mismatch, and duplicate physical sources fail closed. Digest is over
the exact bounded opened bytes. Imports cannot trigger filesystem discovery.

## Layered Identity Selected-input Loader And Pure Resolver

Logical path, pinned root, physical source, module, declaration, local binding,
and snapshot/digest identities remain separate immutable carriers. The selected
index is ordered and exact. The resolver is deterministic and pure, returns
structured issues, and has a separate diagnostic adapter. Ambient callbacks,
global registries, package loaders, and object-identity coupling are forbidden.

## Fact Preservation Inspection Serialization And Rust-ready Boundary

Module identity must survive every private fact boundary listed in A4. Private
inspection and canonical serialization are independently testable production
surfaces from Rust-ready pure inputs/outputs, differential vectors, and
end-to-end hardening. This separation justifies Slices 14 and 15. Neither
surface exposes public fields or introduces Rust/build/package behavior.

## Historical Roadmap Preservation And Active v2 Authority

`docs/spec/pietto-active-roadmap-phase53-70-v1.md` remains byte-identical and
historical after publication. The v2 successor preserves the Phase 53-70
horizon, records Phase 53 completion, adopts permanent phase-start governance,
activates Phase 54 only under the exact Gate 3 condition, and uniquely owns the
Phase 54-70 route. Earlier roadmaps remain append-only evidence.

## Permanent Governance Persistence

`AGENTS.md` contains only a concise mandatory rule and normative link. The
complete procedure and reusable template live in the dedicated governance v1
specification. This module's focused tests lock vocabulary, route range,
scoring, hard gates, ledgers, necessity rules, and versioning. No redundant
standalone template file is created.

## Exact Gate 2 Allowlist And Dirty-state Contract

The original Gate 0/1 evidence froze `A5_M21_D0` and remains byte-identical
historical evidence. Corrective addendum 1 supersedes only the live allowlist
and freezes Gate 2 as exactly `A5_M32_D0`: the four new Markdown authority
files, one new test module, `AGENTS.md`, and thirty-one executing mechanical
reader tests. There are no deletions. The index stays empty. Every dirty path
must be on the literal allowlist. Reader closure must converge without skip,
xfail, deselection, masking, broad exception, or dirty overlay.

The single write-mode Ruff invocation was already consumed on exactly the new
test plus the original twenty reader tests. The eleven corrective reader paths
are formatting-neutral. From corrective freeze onward, Ruff formatting runs in
check mode only over the corrected exact thirty-two Python paths; Markdown and
`AGENTS.md` are not formatter operands.

## Validation Clean-CI Gate 3 And Evidence Contract

Gate 2 requires the 14 primary tests, all reader/SCC families, fixed-point zero
addition, Ruff format/lint, production/test Pyright, clean committed synthetic
projection collection and full suite at exactly 10,814, generated inventory 8,
goldens 37 (32 SQL, 5 JSON), package smoke PASS, installed CLI `0.1.0`, and
existing topology negatives. Gate 2 evidence is exclusive and immutable.

The four exact external evidence targets are:

```text
/home/mianliwang/.local/state/pietto/evidence/phase54-slice1/gate0-gate1-plan.txt
/home/mianliwang/.local/state/pietto/evidence/phase54-slice1/gate0-gate1-plan-correction-1.txt
/home/mianliwang/.local/state/pietto/evidence/phase54-slice1/gate2-evidence-and-diff.txt
/home/mianliwang/.local/state/pietto/evidence/phase54-slice1/gate3-publication-evidence.txt
```

Each target is created once as a regular non-symlink file with
`O_CREAT | O_EXCL | O_NOFOLLOW` and mode `0644`, then remains immutable. The
The immutable original Gate 0/1 terminal is exactly:

```text
PHASE54_SLICE1_GATE0_GATE1_PASS base=af92f30c22e5d3df5219554a0663855a5b9f51a6 allowlist=A5_M21_D0 readers=20 candidates=classified tests=14 clean=10814 focused=14 formatter_paths=21 report=/home/mianliwang/.local/state/pietto/evidence/phase54-slice1/gate0-gate1-plan.txt next=GATE2
```

The corrective addendum terminal is exactly:

```text
PHASE54_SLICE1_GATE0_GATE1_CORRECTION_PASS base=af92f30c22e5d3df5219554a0663855a5b9f51a6 original_allowlist=A5_M21_D0 corrected_allowlist=A5_M32_D0 readers=31 candidates=classified tests=14 clean=10814 focused=14 formatter_paths=32 report=/home/mianliwang/.local/state/pietto/evidence/phase54-slice1/gate0-gate1-plan-correction-1.txt next=GATE2_RESUME_OFFLINE
```

The Gate 2 terminal uses `allowlist=A5_M32_D0`, `focused=14_passed`,
`clean=10814_passed`, `generated=8`, `goldens=37`, `package_smoke=PASS`, and
`next=GATE3`. The Gate 3 terminal records old/new HEAD, `A5_M32_D0`, tests 14,
clean 10814, PR and both CI run IDs, all four evidence paths,
`phase54=ACTIVE`, `slice1=COMPLETED`, and
`next=PHASE54_SLICE2_GATE0_GATE1`.

Gate 3 uses branch `phase54/slice1-scope-authority-expansion-route-lock`, one
literal staging operation, one commit `Add Phase 54 scope authority and expansion route lock`, one normal branch push, one ready PR, natural exact-head
PR CI attempt 1, squash merge with exact tree equality, natural exact-head main
CI attempt 1, fetch/ff-only reconciliation, safe branch cleanup, and exclusive
Gate 3 evidence. No manual CI or alternate publication path is allowed.

## No Grammar Source Runtime Public Schema Dependency Version Or Release Change

Slice 1 changes no source program behavior, production Python, grammar,
generated files, AST, semantics, IR, SQL bytes, CLI, JSON/artifact schema,
public exports, fixtures, goldens, examples, scripts, workflow, dependency,
lockfile, package metadata/version, tag, Release, publish/upload, signing,
attestation, remote operation, production Rust, or native build.

## Stop Conditions

Stop for baseline/evidence drift, unresolved user-visible semantics, material
architecture conflict, public API/serializer change, workflow/dependency/
lockfile/version/release/supply-chain change, production behavior required,
scope expansion, unsafe remote/roadmap ambiguity, non-converging reader closure,
a required second formatter write, non-mechanical validation failure, CI
failure/ambiguity/wrong head/attempt, tree mismatch, publication/reconciliation/
cleanup ambiguity, permission expansion, or any need for amend, rebase,
force-push, direct-main push, manual CI, destructive cleanup, tag, Release,
publication, signing, or attestation.

Mechanical hash, manifest, inventory, heading, phrase, formatter, topology,
evidence, and lifecycle-accounting repairs inside the frozen allowlist continue
without a routine user pause.
