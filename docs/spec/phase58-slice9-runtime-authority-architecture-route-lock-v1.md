# Phase 58 Slice 9 Runtime Authority Architecture And Route Lock v1

## Answer And Evidence

Published Phase 58 Slices 1–8 define the public Project Explain model,
projections, matrix semantics, extension evidence, portability, composition,
references, and JSON v1. A subsequent read-only production audit proved that
the live repository has no successful authority chain from a project root to
`ProjectExplainEnvelope[ProjectExplainPayload]`.

The first missing production edge is:

```text
PackageInspectionFactSet
-> authoritative per-package capability requirement declaration/binding
-> PackageCapabilityCheckingMatrix
-> CapabilityInspectionFactSet
```

Concrete capability-profile authority, an ordered evaluated-target
denominator, profile availability, extension-catalog availability/selection
orchestration, and `ExtensionSignatureProviderContext` producers are also
absent. Current private capability matrices and inspections reject zero target
contexts, so the public Slice 4 empty-denominator value is not an upstream
authority workaround.

This is the independent evidence required by the Phase 58 expansion rule.
Slice 9 freezes architecture, ownership, route, and later-slice boundaries. It
adds no production behavior.

## Historical Route And Expansion

The original Phase 58 route contained exactly 12 slices. Slices 1–8 were
published under that route and remain unchanged completed history.

After published Slice 8, the runtime-builder readiness audit proved an
independent missing lifecycle. The current route therefore expands from 12 to
exactly 16 slices. Published Slices 1–8 are not renumbered. Original planned
Slices 9–12 move to current Slices 13–16.

There is no named pseudo-slice. Current expansion candidate after Slice 9:
`NONE`. Any further expansion requires new independent evidence.

## Current 16-Slice Route

| Slice | Owner |
| ---: | --- |
| 1 | Architecture/scope/route lock; artifact identity; target denominator; single-file explain compatibility |
| 2 | Public common model and success/failure envelope; logical paths; evidence posture; request/resolution/result vocabulary |
| 3 | Package and requirement provenance projection; `declared_by`/`requested_by` |
| 4 | Public requirement/target compatibility matrix; evaluation states; five checked statuses and reasons |
| 5 | Public extension-catalog evidence projection; catalog coordinate/target/digest; selection; matchability/exposure; bounded provenance |
| 6 | Conservative requirement/project portability derivation |
| 7 | Cross-section composition; artifact-local references; integrity; deterministic ordering; authority separation |
| 8 | Public JSON v1 schema; deterministic serialization; success/failure envelopes; privacy and schema-evolution locks |
| 9 | Runtime authority architecture and evidence-backed route expansion lock |
| 10 | Package-owned capability requirement declaration authority |
| 11 | Project-owned evaluated-target, profile, and catalog-availability authority |
| 12 | Project Explain runtime authority builder and exact orchestration |
| 13 | `pietto explain --project` text/JSON integration; existing single-file explain zero-delta |
| 14 | Real multi-target E2E scenarios spanning package, capability, catalog, all evaluation states, and all checked result classes |
| 15 | Public pure/differential compatibility boundary; goldens; Python 3.12/3.13; hash seed; relocation; installed wheel |
| 16 | Completion audit; Phase 59 handoff; Phase 60/64/67/69 readiness reconciliation |

## Frozen Ownership Split

| Authority | Exact owner | Forbidden transfer |
| --- | --- | --- |
| Capability requirement declaration, collection identity, ordered occurrences, exact `CapabilityKey` | Declaring package | Project override or synthesis for a dependency package |
| Ordered evaluated-target denominator, project-provided profiles, target-to-profile selection, supplied overlays | Project | Package-selected project denominator |
| Exact availability declarations for existing bundled extension catalogs | Compiler/catalog boundary | Availability treated as selection, installation, preference, or default target |

Availability and selection remain distinct. A bundled catalog object is not an
availability declaration; an availability declaration is not a selected
catalog; selection proves neither installation nor live database state.

## Slice 10 Package Requirement Authority

Slice 10 owns the minimum package-authority extension needed to construct an
exact `CapabilityRequirementCollection` and
`PackageCapabilityRequirementBinding | None` for every loaded package.

Existing `pietto-package.toml` schema version 1 remains exact zero-delta.
Slice 10 introduces schema version 2 for capability-requirement declarations.
The semantics distinguish:

```text
declaration absent -> UNDECLARED
declaration present, zero entries -> DECLARED EMPTY
declaration present, entries -> DECLARED WITH ORDERED OCCURRENCES
```

Schema v1 is not reinterpreted as a declared-empty collection. Each package
owns only its own requirements. Requirement order and multiplicity remain
authored order. Each requirement preserves the existing seven-field
`CapabilityKey`: `domain`, `subject`, `operation`, `operands`, `context`,
`dialect`, and `extension`. Target release, profile, catalog, selection, and
runtime state remain outside requirement identity.

Slice 10 owns exact additive TOML spelling and compatibility tests. Slice 9
does not freeze those future field names.

## Slice 11 Project Target Profile And Catalog Authority

Existing project configuration schemas 1, 2, and 3 remain exact zero-delta.
Slice 11 introduces project schema version 4, retaining package-root activation
and adding an explicit capability environment.

The project declares one exact ordered evaluated-target sequence. Declaration
order is semantic. There is no sorting, deduplication, implicit target,
`latest`, nearest, default PostgreSQL, installed-target discovery, best target,
or fallback target.

Every non-empty target materializes exact database family/release, one exact
base profile, and ordered supplied overlays. Schema-v4 project authority
supplies the exact static BASE/OVERLAY profiles referenced by those targets and
maps them into the existing `StaticCapabilityProfile`,
`CapabilityProfileReference`, and `CapabilityProfileTarget` model. Every
reference resolves exactly; there is no registry, network lookup, version
range, nearest release, or fallback.

An explicitly declared empty target sequence is valid and means exactly zero
evaluated targets. It is not missing configuration. Its eventual public result
is `INDETERMINATE / no-evaluated-targets`.

Phase 58 creates no compiler default profile or target. The compiler profile
availability ledger may remain empty. Phase 69 may later add exact
release-aware compiler/backend profiles additively.

Slice 11 must inspect current bundled pgvector and pg_trgm catalog artifacts.
It may create exact compiler-owned availability declarations for those
existing artifacts. It does not select a catalog. Existing Phase 57 exact
target selection remains authoritative. Remote/project catalog acquisition and
live database probing remain out of scope.

Slice 11 owns schema-v4 TOML spelling for profiles, targets, and any strictly
necessary local declarations. Slice 9 freezes only semantics and ownership.

## Slice 12 Runtime Authority Builder

Slice 12 owns one canonical production orchestration:

```text
project root
-> project config/root-package authority
-> trusted package location and loading
-> package load plan
-> PackageInspectionFactSet
-> Slice 10 package requirement bindings
-> Slice 11 target/profile/catalog authority
-> PackageCapabilityCheckingMatrix per package
-> CapabilityInspectionFactSet per package
-> ExtensionSignatureProviderContext where required
-> ExtensionCatalogInspectionFactSet where required
-> Slices 3, 4, 5, 6, and 7
-> ProjectExplainEnvelope[ProjectExplainPayload]
```

It composes existing owners and adds no second package loader, dependency
planner, capability checker, provider, catalog selector, portability
algorithm, or JSON serializer.

### Zero-context compatibility extension

Slice 12 owns the minimum private compatibility extension needed to retain
known package requirement declaration state with zero target contexts.

For an undeclared package:

```text
contexts = ()
columns = ()
rows = ()
```

For a declared package:

```text
contexts = ()
columns = ()
one row per requirement
every row.cells = ()
```

Capability inspection must retain exact binding/declaration authority in both
cases. Existing non-empty Phase 56 behavior remains exact zero-delta. No
`UNKNOWN` cell, dummy target, hidden profile, or Slice 3 bypass is allowed.

### Build result and failure

Slice 12 owns a private build result separating the public envelope from CLI
exit-category information. The exact private categories are:

```text
SUCCESS
DIAGNOSTIC_ERROR
USAGE_OR_RESOURCE_ERROR
```

They later map to exits 0, 1, and 2 respectively. Project Explain JSON v1 does
not gain an exit-code field. Failure uses the published envelope with
`ok = False`, `payload = None`, and at least one detached error diagnostic. No
partial payload or host path is allowed.

## Slice 13 CLI And Text

Slice 13 owns `pietto explain --project <root>` in text and JSON formats and
consumes only the Slice 12 build result. Existing `pietto explain <file>`
remains exact zero-delta.

The parser requires positional `path` XOR `--project`; neither or both is a
usage error with exit 2. Project JSON uses only
`serialize_project_explain_json_document`. Text consumes the exact envelope
and remains a human, non-machine compatibility surface.

Slice 13 maps the Slice 12 categories exactly: success to exit 0, diagnostic
failure to exit 1, and usage/resource failure to exit 2. JSON success/failure
is exactly one stdout document; human success is stdout; parser usage and
human failure diagnostics are stderr.

## Shifted Assurance And Completion Owners

Slice 14 owns real full-chain multi-package and multi-target E2E scenarios,
including every checked status, blocked/undeclared/declared-empty requirements,
the empty target denominator, and selected/ambiguous/conflicting/unavailable
extension catalog evidence.

Slice 15 owns public pure/differential compatibility, JSON/text goldens where
appropriate, Python 3.12/3.13 parity, hash-seed and relocation stability,
installed-wheel assurance, and the new Slice 10–13 runtime path.

Slice 16 owns Phase 58 completion, self-owned-open reconciliation, Phase 59
handoff, and Phase 60/64/67/69 readiness including package manifest v2,
project config v4, runtime building, and project explain CLI.

## Later Phase Boundaries

Phase 59 may represent package-owned requirement declarations as package
facts/nodes. Project targets/profiles remain environment authority, and
artifact-local references remain non-global IDs.

Phase 67 may transport package manifest v2 without rewriting requirement
declarations. Phase 58 adds no solver, lockfile, range, registry, or remote
fetching behavior.

Phase 69 may add release-aware PostgreSQL builtin catalogs, backend-specific
compiler profiles, generated/multi-source extension catalog assembly,
extension lowering, and additional dialect foundations. It may not weaken
exact target identity, explicit selection, no-fallback semantics, or the
separation of request, resolution, availability, selection, and installation.

## Compatibility And Non-goals

Slice 9 changes documentation and static tests only. It changes no production
source, package/project parser, matrix, inspection, provider, catalog,
Project Explain model, JSON, text, CLI, public export, package behavior,
generated artifact, golden, dependency, lockfile, workflow, or version.

It does not authorize database connections, installed-extension probing,
`CREATE EXTENSION`, server OIDs, remote profile/catalog loading, registry
access, solvers, lockfiles, version ranges, best/latest/nearest targets,
recommendations, public provenance graphs, SQL lowering, Phase 69 backend
catalog work, Rust refactoring, tags, Releases, package publication, signing,
or attestation.

## Lifecycle And Slice 10 Handoff

Candidate presentation is Phase 58 active, Slices 1–8 completed, Slice 9
current, and Slice 10 next/unstarted. Git plus successful natural exact-head CI
owns Slice 9 completion; no status-only follow-up commit is required.

```text
PHASE58_SLICE9_SELF_OWNED_OPEN = 0
```

Slice 10 remains unstarted and unauthorized.
