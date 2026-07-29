# Phase 54 — Local Import / Module / Export Foundation

## Status And Slice 2 Lifecycle

Phase 53 and Slices 1-16 are `COMPLETED`. Phase 54 is `ACTIVE`, Slice 1 is
`COMPLETED`, and the trusted Slice 2 base is
`53d8767fc3bdbe5e3f631178652222bbe51f6a33`. During Slice 2 Gate 2, Slice 2
remains incomplete and Slices 3-16 remain `UNSTARTED`.

Slice 2 becomes `COMPLETED` only after the exact
reviewed tree passes natural exact-head PR CI attempt 1, squash-merges with
tree equality, passes natural exact-head `main` CI attempt 1, reconciles local
`main` by fetch and ff-only update, cleans the publication branch, and records
immutable Gate 3 evidence. Slices 3-16 then remain `UNSTARTED`; the next state
is `PHASE54_SLICE3_GATE0_GATE1`, and Slice 3 does not begin in Slice 2.

## Trusted Phase 53 Baseline And Controlling Evidence

The trusted commit has tree `5abfc0253ce999a4e7e5cbe3e3ca8c5cd64023ad`,
parent `3c1feab5bc70d407e9e4d7ccd0c5d489eec0ee68`, and subject `Complete
Phase 53 status and compatibility audit`. The controlling evidence chain is
the immutable Phase 54 grounding report, the three immutable Phase 53 Slice 16
Gate reports, the Phase 54 Slice 1 end-to-end Goal, and the immutable Phase 54
Slice 1 Gate 0/1 plan. Live source and completed-phase evidence take priority
over stale historical descriptions.

The binding Slice 1 completion evidence fixes Slice 2 base tree
`475643a9a9c2a5643aef21a9bffe6a3a4232d4ff`, PR 34, natural PR CI run
30401411137, natural `main` CI run 30401723363, and next state
`PHASE54_SLICE2_GATE0_GATE1`.

## Phase Identity, Minimum Production Boundary, And Activation

Phase 54 owns a local explicit-module foundation: explicit schema-v2
activation, one selected file per module, contextual named imports/exports,
private-by-default visibility, basic explicit named re-export, deterministic
module graphs and resolution, cross-module type/relation facts, identity-safe
project facts, trusted local loading, exact schema-v1 legacy-flat
compatibility, and private inspection/serialization/pure-boundary hardening.

It owns no remote registry, package solver, final package manifest, public
inspection artifact, production Rust component, new dialect, release, or
supply-chain behavior.

## Current Production, Readiness, And Retained-later Freeze

The normative `CURRENT_PRODUCTION`, `CURRENT_READINESS`, and
`RETAINED_LATER` ledgers are in
`docs/spec/phase54-slice1-scope-authority-expansion-readiness-and-route-lock-v1.md`.
Current production is schema-v1 flat project parsing and semantic facts.
Current readiness is the private immutable project/fact/graph/serializer seams.
Retained-later is the named Phase 55-70 product and release boundary. No ledger
implies another.

## Phase-start Expansion, Pull-forward, And Readiness Audit

Slice 1 applies the permanent governance audit in
`docs/spec/pietto-phase-start-expansion-pull-forward-readiness-governance-v1.md`.
It independently verifies live authority and production, challenges the old
minimum, atomizes later work, assigns exactly one of the five classifications,
requires necessity for deferral, screens 8-16 slices, and freezes production,
readiness, and retained-later boundaries.

The audit pulls basic explicit named re-export from Phase 66 into Phase 54
because a usable local facade requires it and every hop remains explicit and
acyclic. It pulls private package-neutral/Rust-ready seams without moving final
package, public, remote, solver, dialect, Rust-build, release, or supply-chain
products.

## Product Decisions P1 Through P5

P1 freezes schema-v1 legacy-flat compatibility and exact schema-v2 explicit
activation, one selected file per module, path semantic identity, and no
source-level `module` declaration.

P2 freezes contextual indentation-block `import`, `export`, and `as`, exact
selected path targets, eligible declaration kinds, and
`exported_name as local_name`; it forbids dotted, wildcard, side-effect,
brace, package-target, and `export from` forms.

P3 freezes private-by-default declarations, eligible local/imported binding
exports, and explicit named re-export at every acyclic hop. Advanced forms
remain Phase 66.

P4 freezes no-winner collision/ambiguity, order-independent meaning, a
distinct module cycle graph, deterministic issues, and reserved ownership of
`PIE-S2701` through `PIE-S2707` without Slice 1 implementation or emission.

P5 freezes a pinned canonical root, rejected config symlinks, no-symlink
traversal, inside-root final-source symlinks with opened-identity validation,
retarget/escape/mismatch/duplicate rejection, exact-byte digest, and
selected-index-only imports.

## Architecture Decisions A1 Through A5

A1 uses distinct immutable display-path, root, physical source, module,
declaration, importing-binding, and snapshot/digest identities.

A2 uses one immutable ordered selected-input index and trusted local loader,
never an ambient/callback/package/network registry or import-driven walker.

A3 uses a pure staged resolver returning structured issues, a separate
diagnostic adapter, and a distinct legacy-flat resolver.

A4 threads stable declaration identity through focused private project sidecars
for relation, row, dependency, origin, provenance, lineage, aggregate,
grouped, window, generic, nullability, result-role, and capability facts.

A5 provides private deterministic inspection, canonical serialization,
primitive immutable pure-boundary values, differential vectors, and Python
reference behavior without public schema or Rust/build/package/release change.

## Phase-start Route Comparison From Eight Through Sixteen

All route counts 8-16 were screened using the permanent weighted 1-5 scoring
model and hard gates. Counts 8 and 9 fail because they merge independently
testable grammar, identity, resolution, fact-preservation, and hardening
surfaces. Counts 10-12 remain feasible but overload security/loader and
cross-module preservation surfaces. Counts 13-15 improve cohesion but still
combine private inspection/serialization with a consumer-side pure-boundary
and differential-hardening surface.

| Slices | Weighted score / 70 | Disposition |
| ---: | ---: | --- |
| 8 | hard-gate failure | independently unverifiable merged slices |
| 9 | hard-gate failure | loader/security and resolver/fact ownership overloaded |
| 10 | 49 | qualified but overloaded |
| 11 | 53 | qualified but overloaded |
| 12 | 54 | qualified but foreseeable redesign remains |
| 13 | 57 | qualified |
| 14 | 60 | qualified |
| 15 | 62 | qualified but Slice 14 contains two surfaces |
| 16 | 63 | selected |

Sixteen is selected because Slices 14 and 15 have independent production
ownership, independent focused-test ownership, and a dependency boundary:
canonical private serialization produces deterministic values consumed by
pure-boundary differential and end-to-end hardening. This is not docs-only
padding or scope maximization.

## Exact Sixteen-slice Route And Prerequisites

The exact titles and prerequisites are the numbered Slice headings below and
the canonical route table in the Slice 1 scope specification. The route is
fixed at sixteen; recording it does not authorize a later slice.

## Slice Objectives, Delivery Classes, And Ownership

Slice 1 is static authority/governance. Slices 2-15 are separately gated
bounded production or private-hardening slices. Slice 16 is static completion
audit/status lock. Every slice owns a cohesive production/test/evidence
surface and preserves retained later ownership.

## Dependency Graph And Safe Parallelism

The critical chain is `1 -> 2 -> 3`, `1 -> 4`, `2 + 4 -> 5 -> 6 -> 7 -> 8
-> 9`, `3 + 8 + 9 -> 10`, `10 -> 11` and `10 -> 12`, `3 + 11 + 12 -> 13
-> 14`, `8 through 14 -> 15`, and `1 through 15 -> 16`.

Slice 4 may be developed alongside Slices 2-3 after interface freeze. Slices
11 and 12 may run in parallel after Slice 10 with disjoint production/test
ownership. Git and publication remain sequential.

## Maximum Safe Pull-forward Boundary

The maximum is exactly `IMPLEMENT_NOW + PRIVATE_READINESS_NOW +
CONTRACT_ONLY_NOW` from the normative ledger. It ends before final package
schemas/loading, capability-profile language, extension catalog content,
public artifact publication, package remote graph, registry operations,
ranges/solver/lockfile, production Rust, extension lowering/new dialect, and
tag/release/publish/sign/attest.

## No-unnecessary-deferral Ledger

The canonical 54-row atomic ledger is in the Slice 1 scope specification. Its
authorized classification totals are:

```text
IMPLEMENT_NOW=5
PRIVATE_READINESS_NOW=7
CONTRACT_ONLY_NOW=4
DEFER_BY_NECESSITY=34
OUT_OF_SCOPE=4
```

Basic named re-export is `IMPLEMENT_NOW`. Every `DEFER_BY_NECESSITY` row names
a real semantic, public-schema, remote, solver, dialect, runtime, release, or
supply-chain necessity; no row cites only a phase number.

## Retained Later-phase Ownership

Phases 55-70 retain final package, profile, extension-catalog, public-artifact,
package-graph, advanced-window, Project IR, JOIN/grain, project-SQL, advanced
type, advanced aggregate, advanced module/package, remote registry, solver/
lockfile/production-Rust, extension-lowering/new-dialect, public-expansion,
ecosystem, Rust-decision, and release-readiness products. Separate Release
Gate 3 retains irreversible tag/publish/sign/attest operations.

## Legacy-flat Compatibility And Explicit-module Activation

Schema v1 remains exact flat mode. Schema v2 alone activates explicit modules
project-wide. There is no mixed or heuristic mode. Explicit modules use a
separate resolver and must not be flattened into the existing global catalog.

## Import, Export, Visibility, Re-export, And Diagnostic Contract

The normative syntax is the exact P2 example in the Slice 1 scope
specification. Declarations are private by default. Re-export of an imported
local binding is explicit, named, and acyclic. The seven module diagnostics are
reserved with deterministic policy, but no code is added or emitted in Slice 1.

## Root, Path, Symlink, TOCTOU, Dedup, And Digest Contract

The future trusted loader binds selection to opened descriptor identity under
one pinned root and hashes exact bounded opened bytes. Imports consult only the
immutable index. Path escape, root/source retarget, identity mismatch, and
duplicate physical input fail closed.

## Private Identity, Fact, Inspection, Serialization, And Rust-ready Boundaries

All new facts remain package-neutral and private. Identity-safe facts survive
module edges. Canonical private inspection/serialization is produced before
pure-boundary/differential consumers. No Python object identity or ambient
callback crosses the seam. Public serializers and Rust/build/package surfaces
remain unchanged.

## Public Compatibility And No-behavior Slice 1 Boundary

Slice 1 changes no accepted source, parser/AST/compiler behavior, diagnostic
emission, public API or serializer, SQL, CLI, runtime, dependency, workflow,
version, fixture, golden, generated file, or package/release state.

## Permanent Governance Persistence

The permanent audit is persisted by a concise mandatory `AGENTS.md` rule and
normative link, one dedicated governance specification containing the reusable
template, and focused static tests. No unnecessary standalone template is
created.

## Active-roadmap v2 Authority And Historical Lineage

`pietto-active-roadmap-phase53-70-v1.md` remains byte-identical historical
authority. The governance-schema successor
`pietto-active-roadmap-phase53-70-v2.md` becomes sole current authority only
after the exact Gate 3 activation condition. It preserves the horizon, records
Phase 53 completion, and owns the Phase 54-70 route without rewriting history.

## Slice 1 Exact Gate 2 Scope And Allowlist

The original Gate 0/1 record froze `A5_M21_D0` and remains immutable historical
evidence. The authorized corrective addendum supersedes only that live
allowlist and freezes Gate 2 as exactly `A5_M32_D0`: four new Markdown authority
files, one new 14-test module, `AGENTS.md`, and thirty-one bounded executing
reader tests. No deletions, source, workflow, dependency, lockfile, version,
generated, golden, or fixture changes are permitted. The index remains empty.
The binding correction record is
`/home/mianliwang/.local/state/pietto/evidence/phase54-slice1/gate0-gate1-plan-correction-1.txt`.

## Gate Workflow, Evidence, Publication, And Activation Conditions

One end-to-end Goal covers Gate 0/1, Gate 2, bounded mechanical reader closure,
exclusive evidence, exact branch/stage/commit/push/PR, natural exact-head CI,
squash merge, natural exact-head main CI, fetch/ff-only reconciliation,
cleanup, and final evidence. Logical gates remain independently verified; no
routine user pause is required.

## Validation And Clean-CI Contract

Slice 2 requires 16 new non-parametrized primary tests, forty-eight exact
mechanical readers, a zero-addition SCC fixed point, one write-mode Ruff
format invocation over fifty-five literal Python paths, check-only formatting
afterward, Ruff lint, production/test Pyright, clean committed synthetic
collection and full suite at 10,830, generated 8, goldens 37, package smoke
PASS, installed CLI 0.1.0, and existing topology negatives. No dirty overlay,
skip, xfail, deselection, or masking is allowed. Every `uv` invocation is
offline, and authoritative validation starts again from the lockfile gate
after any environment or projection repair.

## Package Version, Release, Supply-chain, And Remote Boundary

Package and CLI version remain `0.1.0`. This phase plan adds no dependency,
lockfile, workflow, network code, remote operation, Rust/native build, tag,
Release, upload, publication, signing, attestation, or supply-chain behavior.

## Stop Conditions

Stop for baseline/evidence drift, unresolved public syntax/semantics, material
architecture/public-schema choice, workflow/dependency/lockfile/version/
release/supply-chain change, scope expansion, unsafe remote ambiguity,
non-converging reader closure, a second formatter write, non-mechanical
validation failure, CI failure/ambiguity/wrong head/attempt, tree mismatch,
publication/reconciliation/cleanup ambiguity, or expanded permission. Bounded
reader/hash/manifest/inventory/heading/formatter/topology/evidence repairs do
not require a routine pause.

## Slice 2 Exact Production Boundary And Gate Contract

The normative contract is
`docs/spec/phase54-slice2-schema-v2-explicit-module-activation-and-immutable-carrier-v1.md`.
Schema v1 remains legacy-flat; schema v2 alone activates explicit modules.
Private immutable compilation-mode and logical-module carriers are derived
from validated configuration and retained through selection, parse/check, and
the semantic result boundary. Explicit mode returns before legacy flat-catalog
collection. It emits no new diagnostic and changes no public serializer.

The exact Gate 2 authority is `A3_M54_D0`: one contract, one private carrier
sidecar, one sixteen-test module, six core/status modifications, and
forty-eight mechanical reader modifications. The index remains empty. Gate 2
is fully offline. Gate 3 alone owns branch, stage, commit, push, ready PR,
natural exact-head CI, exact-tree squash, reconciliation, cleanup, and final
immutable evidence.

## Slice 2 — Schema-v2 Explicit-module Activation And Immutable Project / Module Carrier

Accept exact integer schema versions 1 and 2 only. Version 1 keeps the legacy
flat semantic path. Version 2 activates project-wide explicit-module mode and
cannot enter the legacy flat catalog. Add only private immutable project-mode
and ordered logical-module carriers using current selected and parsed input
facts; retain them through current project result boundaries. Public JSON,
CLI syntax, Pietto grammar/AST, module resolution, diagnostics, SQL,
dependencies, version, generated files, fixtures, goldens, release, and Rust
remain unchanged. Prerequisite: Slice 1.

## Slice 3 — Module Identity, Selected-input Index, Trusted Local Loader, And Path / Symlink Boundary

Separately gate immutable selected-module indexing, pinned-root descriptor
loading, containment, identity, digest, and dedup. Prerequisite: Slice 2.

## Slice 4 — Import / Export Contextual Grammar, Generated Parser, And Immutable AST

Separately gate the exact P2 source form, generated ANTLR, and immutable AST.
Prerequisite: Slice 1.

## Slice 5 — Module-qualified Nominal Declaration Identity And Per-module Catalogs

Separately gate declaration identity and isolated per-module catalogs.
Prerequisites: Slices 2 and 4.

## Slice 6 — Local Export Eligibility, Visibility, Explicit Named Re-export, And Facade Semantics

Separately gate private visibility, eligible exports, and basic explicit named
re-export. Prerequisite: Slice 5.

## Slice 7 — Named Imports, Aliases, Binding Environments, And Collision Rules

Separately gate deterministic named imports, local aliases, environments, and
no-winner collisions. Prerequisite: Slice 6.

## Slice 8 — Module Graph, Cycles, Diagnostics, And Deterministic Ordering

Separately gate the distinct module graph, cycle failures, PIE-S2701 through PIE-S2707
emission policy, and deterministic issues. Prerequisite: Slice 7.

## Slice 9 — Cross-module Type Alias, Enum, Shape, And Source Resolution

Separately gate cross-module type-namespace and source resolution.
Prerequisite: Slice 8.

## Slice 10 — Cross-module Table / Query / Relation Resolution, Row Facts, And Legacy Compatibility

Separately gate relation resolution, row facts, and exact legacy behavior.
Prerequisites: Slices 3, 8, and 9.

## Slice 11 — Module Attribution, Dependency, Origin, Provenance, And Lineage

Separately gate identity-safe module attribution and graph facts.
Prerequisite: Slice 10.

## Slice 12 — Generic-signature, Nullability, Aggregate, Grouped, Window, Result-role, And Capability-fact Preservation

Separately gate lossless preservation of existing semantic/project facts.
Prerequisite: Slice 10.

## Slice 13 — Package-neutral Identity Layering, Owner / Asset-compatible Carriers, Source Digest, And Loader Readiness

Separately gate package-neutral private seams without package product fields.
Prerequisites: Slices 3, 11, and 12.

## Slice 14 — Private Module Inspection And Canonical Serialization

Separately gate deterministic private inspection facts and serialization.
Prerequisite: Slice 13.

## Slice 15 — Rust-ready Pure Boundaries, Differential Vectors, And End-to-end Hardening

Separately gate pure DTO/procedure boundaries, frozen differential vectors,
Python reference behavior, and full compatibility hardening. Prerequisites:
Slices 8 through 14.

## Slice 16 — Completion Audit, Status Lock, And Phase 55 Handoff

Separately gate final completion evidence, lifecycle/status lock, retained-owner
audit, and Phase 55 handoff. Prerequisites: Slices 1 through 15.
