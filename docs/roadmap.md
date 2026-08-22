# Roadmap

Pietto is a readable, typed, modular SQL authoring compiler. Future work must
be selected by current user/product need, not by an inherited phase number.
Every substantive slice begins by identifying its authority roots, current
invariants, compatibility boundary, and the smallest behavior that is actually
needed.

The active package direction is deterministic local package assets and loading.
It remains compiler-only: no package registry, dependency solver, remote
loading, database execution, runtime evaluation, or implicit project discovery
is authorized by that direction. Future work must preserve the established
module/package identity, complete collection, provenance, lineage, trust, and
diagnostic boundaries unless a new explicit product decision changes them.

## Phase 55 route

All 12 slices are completed. Phase 55 is complete.

| Slice | Owner |
| ---: | --- |
| 4 | Package identity, exact version, and verified content digest |
| 5 | Closed typed asset model and asset catalog |
| 6 | Trusted local package locator and containment |
| 7 | Deterministic local manifest loading and module integration |
| 8 | Exact dependency declarations and deterministic local load plan |
| 9 | Collision, cycle, diamond, and rejection diagnostics |
| 10 | Private package inspection and canonical serialization |
| 11 | Pure package boundary, differential vectors, compatibility, and E2E hardening |
| 12 | Completion audit and Phase 56 handoff |

## Phase 56 route

All 10 slices are completed. Phase 56 is complete. These rows assign ownership
only; they do not authorize a later slice.

| Slice | Owner |
| ---: | --- |
| 1 | Profile/requirement identity, authority, static schema foundation, and route lock |
| 2 | Static profile and requirement contract hardening, target/release semantics, and structural validation |
| 3 | Canonical providers and scoped completeness authority |
| 4 | Base + additive-overlay composition, structural conflicts, and cycles |
| 5 | Declared profile availability and package/project/compiler ownership occurrences |
| 6 | Exact requirement checking and ordered profile-check results |
| 7 | Multi-target checking matrix and Phase 58/60 portability readiness |
| 8 | Private capability inspection and canonical representation |
| 9 | Pure boundary, differential vectors, compatibility, and E2E hardening |
| 10 | Completion audit and Phase 57 handoff |

Profiles describe one exact target; requirements are ordered positive exact-key
conjunctions. The private foundation reuses `CapabilityKey` and
`CapabilityFact`, keeps current support orthogonal to roadmap disposition, and
retains exact declaration occurrences. Effective targets may later combine one
immutable base with additive-only overlays: no override, winner, fallback, or
precedence semantics is authorized. Exact duplicate declarations fail closed,
while distinct same-key facts remain ordered key-local conflict evidence.

Static `BASE` profiles describe `DATABASE` targets, and static `OVERLAY`
profiles describe `EXTENSION` targets. Profile schema version, profile identity
and release, database family and release, and extension identity and release
remain separate exact values; releases are opaque nonblank text, not parsed
versions. Self and unresolved base references remain declaration data pending
Slice 4. Target identity is not normalized into `CapabilityKey`, and no
profile checking occurs here.

Completeness stays with scoped provider evidence; omission is not support
evidence, and `Absent` remains distinct from `Unknown`. Compiler acceptance,
dialect/backend lowering, installation state, roadmap ownership, and public
exposure remain separate authorities. The profile/requirement foundation stays
private and adds no project/package/Pietto syntax, public output, lookup,
composition, or checking behavior in Slices 1–2.

Canonical provider dispatch delegates to the existing family authorities and
preserves their exact-key-scoped completeness; profiles do not supply or infer
provider completeness.

Composition selects one exact base and ordered additive overlays, resolves an
exact-reference graph into deterministic dependency-first order, and fails
closed on structural blockers. Distinct same-key facts remain key-local evidence.

Compiler and project declarations make exact profiles selectable as additive
provenance without precedence. Package requirements remain separate consumer
demand; availability implies neither installation nor capability completeness.

Each exact requirement is checked independently against the selected effective
profile and canonical Pietto provider evidence. Profile omission remains
`UNKNOWN`, availability failures block checking, and outcomes are `SATISFIED`,
`UNSUPPORTED`, `ABSENT`, `UNKNOWN`, or `CONFLICT`.

Canonical single-target results are arranged into an ordered requirement-by-
target matrix that retains undeclared, blocked, and all five checked states.
It defines no final portability classification and remains private readiness
input for Phase 58 explain and the Phase 60 checkpoint.

One private canonical inspection is derived from the exact capability matrix.
It preserves package, requirement, target, availability, and checking evidence
plus deterministic canonical bytes without becoming a new checker or
portability classifier. Slice 9 owns the separate pure evaluator and
differential compatibility boundary.

Capability canonical serialization now flows through one private total pure
evaluator. A frozen accepted/rejected differential corpus proves byte-exact
compatibility plus interpreter and hash-seed stability. Public capability
exposure remains Phase 58 ownership; Slice 10 owns the completion audit and
Phase 57 handoff.

The complete private Phase 56 chain is closed through the pure differential
boundary, and Slice 10 adds no semantics. Live Git and natural exact-head CI
own its completion. `EXTENSION_SIGNATURE` remains intentionally unpopulated and
fail closed at the Phase 57 Slice 1 baseline.

## Phase 57 route

Phase 57 is active, Slices 1–4 are completed, and Slice 5 is current. The
initial route has 12 slices. Evidence may expand it up to 16 slices only through
an explicit evidence-backed route update when genuinely independent ownership
emerges. Never pad the route, compress independent responsibilities to remain
at 12, or silently reorder published ownership. These rows assign ownership
only; they do not authorize a later slice.

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

One catalog describes exactly one PostgreSQL database release and one exact
extension identity/release target. Catalog, profile, and installation authority
remain distinct. Release remains outside `CapabilityKey`; Slice 7 owns the
smallest later private release-aware provider/catalog-selection authority.

Phase 57 is static, declarative, strongly typed, deterministic, immutable,
reviewable, and non-executable. It adds no installation, introspection,
runtime discovery, SQL lowering, public portability output, package asset,
remote transport, solver, lockfile, tag, Release, or package publication.
The controlling architecture is
[Phase 57 Slice 1 scope lock](spec/phase57-postgresql-extension-signature-catalog-scope-lock-v1.md).

Slice 2 establishes the separate private extension-catalog schema marker,
catalog identity/release reference, exact four-part target, source provenance,
ordered source occurrences, and metadata header. It adds no type reference,
entry, construction, completeness, selection, provider, inspection, package
asset, public, runtime, or SQL behavior. The controlling foundation is
[Phase 57 Slice 2 identity and provenance](spec/phase57-extension-catalog-schema-identity-target-source-provenance-v1.md).

Slice 3 adds three-domain atomic type references, reuses the canonical private
Pietto logical-type identity, and defines installation-independent PostgreSQL
callable, unary/binary operator, cast, and extension-native type identities.
Arrays, modifiers, compound types, entries, matching, coercion, construction,
provider integration, runtime installation identity, and lowering remain later
ownership. The controlling foundation is
[Phase 57 Slice 3 structured type and physical identity](spec/phase57-extension-catalog-structured-type-physical-identity-v1.md).

Slice 4 adds exact/unmodeled declaration type use, orthogonal matchability and
exposure, ordered source-position evidence, five private typed entry families,
and static function/aggregate/cast declaration metadata. It preserves complex
source declarations without making them matchable, executable, absent, or
invalid. Construction, conflicts, completeness, canonical bytes/digest,
provider integration, coercion, runtime identity, and lowering remain later
ownership. The controlling contract is
[Phase 57 Slice 4 entries and matchability](spec/phase57-extension-catalog-entry-matchability-contract-v1.md).

Slice 5 constructs one deterministic private catalog artifact from the Slice
2–4 authorities. It validates source binding by semantic catalog coordinate,
retains structural failures separately from exact-signature evidence conflict,
groups all five families without a winner, records exact lookup-scoped
completeness, and derives unambiguous length-framed canonical bytes plus their
SHA-256 content identity. It adds no selection, provider, concrete extension,
inspection, runtime, package, or lowering behavior. The controlling contract
is [Phase 57 Slice 5 construction, completeness, and canonical identity](spec/phase57-extension-catalog-construction-completeness-canonical-v1.md).

## Retained later ownership

| Phase | Owner |
| ---: | --- |
| 58 | Public explain, portability, and package-inspection artifact |
| 59 | Local package graph, attribution, provenance, and lineage |
| 60 | Advanced windows and Phase 51–60 readiness checkpoint |
| 61 | Project IR and semantic composition |
| 62 | Relationship, JOIN, grain, and fanout-safe semantics |
| 63 | Multi-relation SQL, project emit-SQL, and QUALIFY lowering |
| 64 | Advanced types, coercion, temporal, Decimal, and native mapping |
| 65 | Advanced aggregation and grouping |
| 66 | Advanced module and semantic-package assets |
| 67 | Remote package manager and trust boundary |
| 68 | Dependency solver, canonical lockfile, and first Rust kernel decision |
| 69 | Extension-specific lowering and additional dialect foundations |
| 70 | Public schema/lineage expansion and v0.2 release-readiness decision |

Phase 57 begins from the complete private Phase 56 capability chain.
`CapabilityKey` remains release-free, exact profile targets retain database and
extension releases separately, and current `EXTENSION_SIGNATURE` provider
evidence remains empty and incomplete. `CONVERSION` remains reserved for later
advanced-type work.

Compiler acceptance, private capability facts, backend support, database
installation, public exposure, local graph behavior, remote I/O, solving, and
release operations remain separate authorities. No phase or roadmap row
implicitly grants a tag, release, package publication, signing, or attestation.

Use the current source, tests, retained normative contracts, Git state, and
natural CI as authority. Git history contains completed planning and delivery
history; it is not duplicated as a second current roadmap.
