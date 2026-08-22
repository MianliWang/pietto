# Phase 57 Slice 1 PostgreSQL Extension Signature Catalog Scope Lock v1

## Purpose And Authority

Phase 57 owns the PostgreSQL Extension Signature Catalog. Slice 1 locks the
phase architecture, release-aware authority boundary, future-readiness
requirements, and initial route. It is architecture, documentation, and test
work only. It creates no production extension catalog and does not start Slice
2.

Phase 56 completion is owned by live `main` and its successful natural
exact-head CI. This document records current architecture, not a second
lifecycle authority.

## Phase Length Policy

- A normal phase has 8–12 slices.
- Phase 57 begins with exactly 12 route rows.
- Evidence may justify expansion up to 16 slices when genuinely independent
  ownership emerges.
- The route must never be padded, and independent semantic or compatibility
  responsibilities must not be compressed merely to remain at 12 slices.
- Expansion requires an explicit evidence-backed route update.
- Already published slice ownership must not be silently reordered.

Route rows assign ownership only. They do not authorize later slices.

## Catalog Owner And Non-owner Boundaries

The Phase 57 catalog remains static, declarative, strongly typed,
deterministic, immutable, reviewable, and non-executable.

Phase 57 does not own extension installation, `CREATE EXTENSION`, database or
server introspection, runtime discovery, SQL lowering, executable plugin
infrastructure, or public portability reporting.

## Exact Catalog Target

One concrete catalog describes exactly this four-part target:

1. `database_family`
2. `database_release`
3. `extension_identity`
4. `extension_release`

For Phase 57, `database_family` is PostgreSQL and remains explicit. One catalog
does not describe multiple PostgreSQL releases, an extension release range,
multiple extension releases, `latest`, compatible releases, or a server
installation. Compatibility between two exact catalog targets is never
inferred.

## Independent Identity And Release Dimensions

These dimensions remain independent:

1. capability-profile schema version;
2. profile identity;
3. profile release;
4. database family;
5. database release;
6. extension identity;
7. extension release;
8. extension-catalog schema version;
9. extension-catalog identity;
10. extension-catalog release.

Catalog release is not extension release or profile release. Extension release
is not the Pietto package version. No release is assumed to use SemVer. Releases
remain exact opaque nonblank text unless later authority proves a stronger
model is required.

## CapabilityKey Boundary

`CapabilityKey` answers what capability is requested. Exact catalog target
authority answers on which PostgreSQL and extension release target the
capability is answered.

Extension release remains outside `CapabilityKey`. It must not be encoded in
`CapabilityKey.extension`, `subject`, `operation`, `operands`, `context`,
`dialect`, or a synthetic text convention. `CapabilityKey` retains exactly:

1. `domain`
2. `subject`
3. `operation`
4. `operands`
5. `context`
6. `dialect`
7. `extension`

It contains neither `release` nor `backend`.

## Release-aware Provider Readiness

Phase 57 must eventually support target-scoped `EXTENSION_SIGNATURE` provider
evidence. Evidence may differ between PostgreSQL releases for one extension
release and between extension releases. Existing non-extension provider
domains may remain context-free; provider evidence is not globally assumed to
be permanently target-independent.

Slice 7 owns the smallest explicit private authority for exact catalog
selection and release-aware provider inputs. Slice 1 does not implement that
carrier. No global mutable registry, latest lookup, environment lookup, server
lookup, or filesystem discovery is authorized.

## Catalog Profile And Installation Separation

- A catalog is static signature evidence for one exact catalog target.
- A profile is a selected target capability declaration.
- An installation is runtime server state.

A catalog is not an `OVERLAY` profile. A profile does not prove catalog
presence. A catalog does not prove extension installation.

## Structured Type-reference Readiness

Slice 3 owns a private structured catalog type-reference model that can
distinguish at least:

1. `PIETTO_LOGICAL`
2. `POSTGRES_BUILTIN`
3. `EXTENSION_NATIVE`

An `EXTENSION_NATIVE` reference retains its exact owning extension identity.
Phase 57 creates no Pietto logical type and implements no native/logical
coercion. Phase 64 owns advanced type mapping and coercion semantics.

Slice 3 also audits extension-native parameter or modifier information where
relevant. Arrays or compound references are added only if concrete evidence
requires them; no speculative generalization is authorized.

## Physical SQL Identity And Lowering Separation

Catalog entries may retain the physical PostgreSQL object identity needed to
identify an existing server-side object: function SQL name, operator token or
name, cast source and target identity, or native type name. This is static
identity.

Phase 57 records what exact PostgreSQL object or signature exists. It stores no
SQL-lowering template and changes no SQL emitter. Phase 69 owns how Pietto
lowers or uses an extension-specific object.

## Five Entry Families

The initial matchable catalog entry families are exactly:

1. extension-native type declaration / native-type mapping;
2. scalar function;
3. aggregate;
4. operator;
5. cast.

There is no sixth matchable family in Slice 1. Window functions, table or
set-returning functions, procedures, DDL, index or operator-class behavior,
GUC/configuration, planner hooks, and extension installation remain outside
the current exact matcher.

## Complex Signatures And Matchability

Real declarations must not disappear merely because the current matcher cannot
consume them. Later catalog schema work must be able to record evidenced
default arguments, variadic arguments, polymorphic or pseudo-type signatures,
set-returning posture, and other characteristics required to distinguish a
real declaration from absence.

The private catalog must distinguish:

- exact-matchable now; and
- declared or evidenced, but not representable by the current exact matcher.

Exact enum names remain later implementation freedom. A declaration in the
second posture must not satisfy a requirement. Catalog omission remains
distinct from catalog evidence that the current Pietto matcher cannot model.

## Semantic Metadata Readiness

Slices 3–4 audit stable PostgreSQL signature properties that may later affect
semantic correctness, especially null-input and result posture. Metadata is
recorded only when it is static catalog evidence with an evidenced future
consumer. Phase 57 changes no Pietto nullability semantics and does not turn
volatility or planner metadata into requirements without concrete need.

## Exact Matching Policy

The Phase 57 matcher is conservative and uses exact identity, exact arity,
exact ordered argument types, and the exact result or type relation where
relevant. Declaration order is provenance only.

It performs no:

- aliases;
- variadic expansion;
- default-argument omission;
- polymorphic inference;
- generic substitution;
- implicit coercion;
- cast-assisted overload selection;
- best-match ranking;
- score-based ranking;
- winner selection.

## Scoped Completeness

There is no global `catalog_complete = true`. Completeness is scoped to the
exact catalog target, entry or signature family, and relevant lookup scope.
Omission is definitive absence only where that exact completeness authority
allows it; otherwise omission remains unknown and not evidenced. Slices 4–5
own the concrete completeness carrier and construction design.

## Conflict Boundaries

Construction must fail closed on structural catalog ambiguity and has no
winner or precedence semantics. These remain distinct:

- structural catalog conflict;
- same-signature evidence conflict;
- catalog omission; and
- an unmodeled signature form.

## Canonical Artifact And Trust Readiness

Phase 57 establishes deterministic canonical catalog bytes and one exact
SHA-256 content digest in Slice 5. That digest is artifact and trust identity,
not governance evidence hashing. Phase 67 may later verify it during remote
transport, and Phase 68 may later pin catalog coordinate plus digest. Phase 57
implements neither transport nor lockfiles.

## Phase 56 Representation Compatibility

`pietto.capability-inspection.v1` and the frozen Phase 56 differential corpus
remain unchanged. The corpus is exactly 125 vectors: 16 accepted and 109
rejected, with digest
`8453c3babda888b105f37f667f5fadf3a12aa68ca9a561bda98e5f6b6604a69e`.

Slice 10 owns a separate private extension-catalog inspection and canonical
representation. Catalog provenance must not be forced into the Phase 56 v1
format. Phase 58 may later project capability inspection plus extension-catalog
inspection into public explain output; no public projection exists now.

## Package Asset Boundary

Extension catalogs are not current package assets. Phase 57 does not modify
`pietto-package.toml` or add `extension_catalog` to the package asset schema.
Catalog schema marker, exact coordinate, canonical bytes, digest, and immutable
declarative structure must remain ready for a later Phase 66 or 67 distribution
wrapper without changing internal semantics.

## First Concrete Catalog Direction

The approved extension identity order is:

1. `pgvector` — first concrete production catalog;
2. `pg_trgm` — second diversity catalog;
3. `PostGIS` — representability and stress audit, without a full-support claim.

`TimescaleDB` remains deferred. Exact extension release coverage requires
concrete upstream evidence in the population slice. Slice 1 adds no concrete
entry and invents no release range.

## Exact Initial Route

| Slice | Owner |
| ---: | --- |
| 1 | Phase architecture, release-aware authority, readiness decisions, and route lock |
| 2 | Catalog schema/version/identity/release, exact target coordinate, and source provenance |
| 3 | PostgreSQL builtin and extension-native type references, physical SQL object identity, and Phase 64/69 readiness |
| 4 | Five typed catalog entry families, complex-signature metadata, and exact-matchability contracts |
| 5 | Deterministic catalog construction, ordering/conflicts, scoped completeness, canonical bytes, and content SHA-256 |
| 6 | Compiler/project catalog declaration and availability, exact PostgreSQL-release × extension-release selection |
| 7 | EXTENSION_SIGNATURE provider integration, exact checking propagation, target-scoped provider authority, and matrix compatibility |
| 8 | First concrete production catalog: pgvector |
| 9 | Second diversity catalog: pg_trgm, plus PostGIS representability/stress audit without a full-support claim |
| 10 | Separate private extension-catalog inspection/canonical representation and Phase 58/59 provenance readiness |
| 11 | Extension-catalog pure boundary, differential vectors, Python 3.12/3.13, hash-seed, relocation, and E2E hardening |
| 12 | Completion audit and Phase 58 handoff |

Evidence-backed expansion triggers may include an independent type-reference
problem, a complex-signature family that cannot safely share Slice 4, a
distinct provider-authority migration, concrete-catalog evidence large enough
to separate, a genuine PostGIS schema gap, or independently large inspection
or pure-boundary work. Implementation inconvenience alone is not evidence.

## Future-readiness Ownership

| Phase | Retained readiness |
| ---: | --- |
| 58 | Explain PostgreSQL release, extension and catalog coordinates, digest, declarations, matchability, source provenance, completeness, selection, lookup outcome, conflict, and omission without creating that public projection now |
| 59 | Connect exact package requirement occurrences through target profiles and selected catalogs to declaration evidence without constructing the graph now |
| 60 | Distinguish cataloged, uncataloged, complete, incomplete, exact-matchable, unmodeled, absent, conflicting, and target-specific outcomes without a binary ecosystem flag |
| 64 | Map structured native and logical types later without rewriting concrete catalogs; no coercion now |
| 66 | Add advanced package asset wrapping later; catalogs are not assets now |
| 67 | Transport and verify immutable catalog artifacts later; no remote I/O now |
| 68 | Pin exact catalog coordinates and digests later; no solver or lockfile now |
| 69 | Use retained physical PostgreSQL identities for extension-specific lowering later; no templates or emitter behavior now |

Exact identities and occurrence ordering remain available for future
provenance. No future phase is started or authorized by this readiness table.

## Slice 1 Change And Release Boundary

Slice 1 changes only this scope lock, its focused test, lifecycle documentation,
and exact mechanical readers caused by those paths. It changes no production
source, parser, AST, semantic behavior, IR, SQL, diagnostics, CLI, JSON, public
API, package asset, dependency, workflow, generated artifact, or golden fixture.

The package and CLI version remains `0.1.0`. Slice 1 authorizes one ordinary
non-amend commit and one ordinary fast-forward push only after the sealed Gate
2 tree succeeds. It authorizes no tag, Release, package publication, signing,
or attestation.

After that exact commit receives successful natural exact-head `CI / push`
attempt 1, Phase 56 is completed, Phase 57 remains active, Slice 1 is completed,
and Slice 2 remains unstarted. No post-CI status-flip commit is planned or
required.
