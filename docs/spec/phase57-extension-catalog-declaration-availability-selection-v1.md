# Phase 57 Slice 6 Extension-catalog Declaration Availability And Selection v1

## Purpose And Authority

Phase 57 Slice 6 establishes private compiler/project declarations that make an
already-constructed Slice 5 catalog available to one compilation context, then
selects authority for one exact `ExtensionCatalogTarget`.

The authority flow is:

```text
ConstructedExtensionCatalog
-> explicit availability declaration
-> compilation/project applicability
-> exact target declarations
-> deterministic candidate grouping
-> structured selection result
```

Catalog existence alone creates no availability. Slice 6 adds no registry,
discovery, provider lookup, capability facts, installation evidence, or SQL
behavior.

## Declaration Authority

`ExtensionCatalogAvailabilityOwner` contains exactly:

- `COMPILER`
- `PROJECT`

There is no package, installation, server, or registry owner.

`ExtensionCatalogAvailabilityDeclaration` contains:

1. exact owner;
2. dense declaration `position`;
3. exact `ConstructedExtensionCatalog`; and
4. an optional exact logical `ProjectRoot`.

Compiler declarations forbid a project root. Project declarations require the
existing `pietto._project.model.ProjectRoot` carrier. No second project
identity, host absolute path, cwd, resolved filesystem identity, inode, or
device authority is introduced.

The declaration exposes catalog reference, target, and `content_sha256`
through its exact artifact. It cannot mutate or override artifact metadata.
Availability means only that this exact constructed artifact is explicitly
declared under this authority.

## Declaration Collection And Provenance

`DeclaredExtensionCatalogAvailability` freezes one ordered declaration tuple
and requires dense positions beginning at zero. Empty availability is valid.

Declaration order and multiplicity remain provenance. Repeated declarations
are retained. Compiler and project authorities are additive; neither has
precedence, override, shadowing, first-wins, or last-wins behavior.

Selection outcome and candidate ordering are independent of declaration input
order. Each candidate nevertheless retains its declarations in collection
order so later inspection can reproduce exact provenance.

## Project Applicability

With no active project root, only `COMPILER` declarations are applicable.

With an exact active logical `ProjectRoot`:

- every compiler declaration is applicable; and
- a project declaration is applicable only when its project root is exactly
  value-equal to the active root.

Other project declarations are retained separately as excluded-by-project-
scope provenance. Applicability uses no path normalization, ancestry,
parent-project fallback, name similarity, cwd, or filesystem resolution.

Applicability is determined before exact target filtering. The selection
result separately retains all scope-applicable declarations, project-excluded
declarations, and the exact-target subset.

## Exact Target Selection

Selection requires one exact `ExtensionCatalogTarget` and compares all four
fields by exact equality:

1. `database_family`
2. `database_release`
3. `extension_identity`
4. `extension_release`

There is no parsing, range, latest, nearest, compatibility, alias, family, or
release fallback. Catalog and extension releases remain distinct. Release does
not enter `CapabilityKey`.

## Exact Candidate Identity

`ExtensionCatalogSelectionCandidateIdentity` contains independently:

1. exact `ExtensionCatalogReference`;
2. exact `ExtensionCatalogTarget`; and
3. exact lowercase 64-character `content_sha256`.

This identity groups repeated declarations and independently reconstructed
equal artifacts into one candidate. Different references never collapse
because their digest is equal. Different targets never collapse. Catalog
release is not extension release.

`ExtensionCatalogSelectionCandidate` retains one exact artifact authority and
all applicable exact-target declarations assigned to that candidate. Candidate
ordering uses exact reference, target, and digest text only as deterministic
representation order, never as preference or ranking.

## Selection Result

`ExtensionCatalogSelectionResult` retains:

- outcome;
- requested exact target;
- active logical project root, if any;
- exact declared-availability collection;
- all scope-applicable declarations;
- all project-scope-excluded declarations;
- applicable declarations matching the exact target;
- every deterministic artifact candidate; and
- the exact selected catalog only for `SELECTED`.

The result is frozen, slotted, constructor-closed, and sufficient for Slice 7
to consume a selected artifact without selecting again.

## Selection Algebra

`ExtensionCatalogSelectionOutcome` contains exactly:

- `UNDECLARED`
- `SELECTED`
- `AMBIGUOUS`
- `CONFLICT`

### `UNDECLARED`

No scope-applicable declaration matches the requested exact target. This says
only that this selection context has no declared catalog authority. It says
nothing about global catalog existence, support, installation, `Absent`, or
`Unknown`.

### `SELECTED`

Every applicable exact-target declaration groups to one candidate identity.
Repeated declarations, compiler plus matching-project declarations, and
separately reconstructed equal artifacts remain one candidate with all
provenance retained.

The result retains the exact selected `ConstructedExtensionCatalog` and never
uses completeness or catalog entry state to select it.

### `AMBIGUOUS`

The requested exact target has multiple candidates with distinct catalog
references and no coordinate/content conflict. All candidates and declarations
are retained. Equal digest does not alias distinct catalog references.

No newer-looking release, larger catalog, project owner, compiler owner, or
source order wins.

### `CONFLICT`

At least one exact `(ExtensionCatalogReference, ExtensionCatalogTarget)`
coordinate has multiple declared `content_sha256` values. Every conflicting
and additional ambiguous candidate remains retained. Coordinate/content
conflict is fail-closed and stronger than ordinary ambiguity.

No digest, project authority, compiler authority, or later declaration wins;
catalogs are neither merged nor rewritten.

## No-winner And Separation Boundaries

Selection never reads or ranks:

- entry count or family coverage;
- matchability or exposure;
- entry evidence conflicts;
- completeness state or conflicts;
- source count or source order; or
- catalog release as an ordered version.

A structurally valid catalog containing evidence conflicts, completeness
conflicts, or cataloged-unmodeled declarations remains selectable.

Catalog availability and selection remain separate from capability-profile
availability/composition/checking, package demand, extension installation,
database/server existence, and runtime signatures.

## Privacy And Non-executable Boundary

Slice 6 is implemented in the private
`pietto._project.extension_catalog_availability` module because `ProjectRoot`
is project-layer authority. The semantic catalog module does not acquire a
reverse `_project` dependency.

The module is frozen-data-only, stdlib-only apart from existing private
authorities, has `__all__ = ()`, and is not re-exported from `pietto`,
`pietto.semantic`, or `pietto._project`.

It performs no filesystem, environment, network, database, Git, installation,
registry, package, callback, dynamic import, parser, IR, SQL, diagnostic,
provider, checking, matrix, inspection, or public-output behavior.

## Predecessor Compatibility

All Slice 2–5 identities, declarations, groups, completeness authority,
canonical bytes, and SHA-256 semantics remain unchanged. Selection retains an
exact constructed artifact and never rebuilds or mutates it.

`CapabilityKey`, provider routing, empty/incomplete `EXTENSION_SIGNATURE`,
`Unknown(NOT_EVIDENCED)`, profile omission, checking/matrix behavior, and
`pietto.capability-inspection.v1` remain unchanged.

The Phase 56 corpus remains 125 total, 16 accepted, and 109 rejected, with
digest
`8453c3babda888b105f37f667f5fadf3a12aa68ca9a561bda98e5f6b6604a69e`.

## Slice 7 Handoff

Slice 7 may consume `ExtensionCatalogSelectionResult.selected_catalog` only
when the outcome is `SELECTED`. It also receives the exact requested target,
active project scope, candidate identity, and declaration provenance without
re-running selection.

Slice 7 owns provider eligibility, exact catalog lookup, completeness-driven
`Absent` versus `Unknown`, entry-conflict propagation, checking, and matrix
integration. Slice 6 implements none of that behavior.

Slice 7 remains unstarted and unauthorized by this contract.

## Release And Lifecycle Boundary

The package and CLI version remains `0.1.0`. Live Git plus successful natural
exact-head CI owns Slice 6 completion. The candidate lifecycle keeps Slice 6
current and Slice 7 unstarted; no post-CI status-flip commit is planned or
required.
