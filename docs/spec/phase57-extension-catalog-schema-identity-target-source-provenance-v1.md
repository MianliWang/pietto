# Phase 57 Slice 2 Extension-catalog Schema Identity Target And Source Provenance v1

## Purpose And Authority

Phase 57 Slice 2 establishes the private, immutable, data-only foundation for
extension-catalog schema identity, catalog identity and release, one exact
target coordinate, source provenance, ordered source occurrences, and a
metadata header joining those authorities.

This foundation is not a populated catalog. It adds no type reference, entry,
construction, completeness, selection, provider, inspection, public, runtime,
or SQL behavior. Slice 3 and every later slice require separate authorization.

## Schema Marker

The exact private v1 marker is:

```text
pietto.extension-catalog.v1
```

`ExtensionCatalogSchemaVersion.EXTENSION_CATALOG_V1` owns this marker.
`pietto.capability-inspection.v1` remains unchanged. Canonical catalog bytes
and a catalog content digest remain Slice 5 ownership.

## Catalog Identity And Release

`ExtensionCatalogIdentity` retains exact independent `namespace` and `name`
text. `ExtensionCatalogReference` combines one exact catalog identity with one
opaque exact nonblank catalog `release`.

Catalog release is not extension release, profile release, database release,
or the Pietto package version. The schema performs no SemVer parsing, version
range handling, compatibility calculation, latest lookup, fallback, nearest
match, or release ordering. Profile identity and `CapabilityProfileTarget` are
not reused.

## Exact Target

`ExtensionCatalogTarget` contains exactly these semantic dimensions in order:

1. `database_family`
2. `database_release`
3. `extension_identity`
4. `extension_release`

All four values are required and explicit. PostgreSQL is not encoded as an
implicit constant. Changing any one value creates a different target, and the
schema infers no compatibility between targets.

The target contains no catalog or profile coordinate, installation state,
connection state, server identity, or `CapabilityKey`.

## Exact Text

Every identity, release, target, and provenance text field requires an exact
`str`, rejects empty or whitespace-only values, and preserves every otherwise
valid value exactly as supplied. The schema performs no trimming, lowercasing,
casefolding, Unicode normalization, release parsing, component reordering, or
alias inference.

Case differences and composed/decomposed Unicode forms remain distinct.
Leading or trailing whitespace in an otherwise nonblank value remains
preserved.

## Source Provenance

`ExtensionCatalogSourceProvenance` retains four separately inspectable values:

1. `source_authority`
2. `source_revision`
3. `source_locator`
4. `curation`

The locator is exact upstream logical provenance, not a resolved host path.
The carrier performs no network access, URL dereference, filesystem read, Git
inspection, database query, installation discovery, or ambient lookup. It has
no cwd, device/inode identity, host absolute-path field, timestamp, or digest.

## Ordered Source Occurrences

`ExtensionCatalogSourceOccurrence` retains one exact catalog `owner`, one
non-negative `position`, and one exact source `provenance` record.

`ExtensionCatalogMetadata` freezes accepted source input into an immutable
tuple and requires dense caller order beginning at zero. It does not sort,
deduplicate, select, rank, override, or define precedence. Equal provenance may
appear at distinct ordered positions. An empty occurrence tuple is valid in
this schema; Slice 5 owns any later construction-level source requirement.

Every occurrence must retain a catalog reference equal to the exact metadata
catalog coordinate. Separately reconstructed equal namespace, name, and
release values are valid owner authority; Python object identity is not
semantic authority. The immutable supplied owner value remains retained.

## Metadata Boundary

`ExtensionCatalogMetadata` contains exactly:

1. `schema_version`
2. `catalog`
3. `target`
4. `source_occurrences`

It enforces exact carrier types, dense source positions, and exact owner
authority. It intentionally contains no entry collection and is not named or
treated as a complete populated catalog.

## Privacy And Non-executable Boundary

The foundation is private, frozen, slotted, stdlib-only, deterministic,
declarative, strongly typed, immutable, non-executable, and data-only. The
module has an empty `__all__` and is not re-exported from `pietto`,
`pietto.semantic`, or `pietto._project`.

The module has no ambient I/O, callback, registry, plugin, mutable global, or
runtime discovery behavior. It does not use or modify the unrelated built-in
semantic catalog in `src/pietto/semantic/catalog.py`.

## Profile Catalog And Installation Separation

- Catalog metadata identifies one catalog artifact coordinate and exact target.
- A capability profile declares selected target capabilities.
- Installation is mutable runtime server state.

The catalog target does not reuse `CapabilityProfileTarget`. A profile does
not prove catalog presence, and catalog metadata does not prove installation.

## Retained Slice Ownership

| Slice | Owner |
| ---: | --- |
| 3 | PostgreSQL builtin and extension-native type references, physical SQL object identity, and Phase 64/69 readiness |
| 4 | Five typed catalog entry families, complex-signature metadata, and exact-matchability contracts |
| 5 | Deterministic catalog construction, ordering/conflicts, scoped completeness, canonical bytes, and content SHA-256 |
| 6 | Compiler/project catalog declaration and availability, exact PostgreSQL-release × extension-release selection |
| 7 | Structured EXTENSION_SIGNATURE requirement selector authority |
| 8 | EXTENSION_SIGNATURE provider integration using typed selectors, target-scoped catalog lookup, exact checking propagation, and matrix compatibility |
| 9 | First concrete production catalog: pgvector |
| 10 | Second concrete production catalog: pg_trgm, plus ltree lightweight representability probe and PostGIS representability/stress audit without full-support claims |
| 11 | Separate private extension-catalog inspection/canonical representation and Phase 58/59 provenance readiness |
| 12 | Extension-catalog pure boundary, differential vectors, Python 3.12/3.13, hash-seed, relocation, and E2E hardening |
| 13 | Completion audit and Phase 58 handoff |

These rows preserve ownership only and authorize none of those slices.

## Exact Non-scope

Slice 2 adds no type references, type modifiers, arrays, compound types,
physical PostgreSQL object identity, entry families, signatures, aggregate,
operator, cast, complex-signature metadata, matching, coercion, ranking,
catalog construction, merge, conflict resolution, scoped completeness,
canonical bytes, content digest, declaration, availability, selection,
release-aware provider inputs, provider integration, capability checking,
matrix behavior, inspection, pure boundary, concrete extension entries, public
output, package assets, registry, remote transport, solver, lockfile,
installation or `CREATE EXTENSION`, database/server introspection, filesystem
discovery, SQL lowering, parser, AST, IR, diagnostics, CLI, JSON, generated
artifacts, or golden fixtures.

Synthetic focused-test values are not concrete upstream extension facts.

## Predecessor Compatibility

The seven `CapabilityKey` fields, release-free key identity, existing provider
routing, empty/incomplete `EXTENSION_SIGNATURE` posture,
`Unknown(NOT_EVIDENCED)`, profile omission semantics, support/disposition
orthogonality, single-target checking, matrix delegation,
`pietto.capability-inspection.v1`, and the frozen Phase 56 differential corpus
remain unchanged.

The corpus remains 125 vectors: 16 accepted and 109 rejected, with digest
`8453c3babda888b105f37f667f5fadf3a12aa68ca9a561bda98e5f6b6604a69e`.

## Release And Publication Boundary

The package and CLI version remains `0.1.0`. Slice 2 changes no dependency,
lockfile, package manifest, workflow, public contract, tag, Release, package
publication, signing, or attestation behavior.

Live Git plus successful natural exact-head CI owns Slice 2 completion. The
candidate lifecycle keeps Slice 2 current and Slice 3 unstarted; no post-CI
status-flip commit is planned or required.
