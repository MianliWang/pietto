# Roadmap

Pietto is a readable, typed, modular SQL authoring compiler. Future work must
be selected by current user/product need, not by an inherited phase number.
Every substantive slice begins by identifying its authority roots, current
invariants, compatibility boundary, and the smallest behavior that is actually
needed.

The active product direction is a deterministic public project-explain
artifact composed from existing private package, capability, and extension-
catalog authorities. It remains compiler-only: no package or catalog registry,
dependency solver, remote loading, database execution, runtime evaluation,
installation discovery, or implicit project discovery is authorized. Future
work must preserve established identity, complete collection, provenance,
ordering, trust, and diagnostic boundaries unless a new explicit product
decision changes them.

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

All 13 slices are completed. Phase 57 is complete. The revised route has
exactly 13 slices. The independent typed requirement-selector authority proven
at Slice 7 expanded the original 12-slice route without padding. These rows
record completed ownership; they do not authorize later work.

| Slice | Owner |
| ---: | --- |
| 1 | Phase architecture, release-aware authority, readiness decisions, and route lock |
| 2 | Catalog schema/version/identity/release, exact target coordinate, and source provenance |
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

One catalog describes exactly one PostgreSQL database release and one exact
extension identity/release target. Catalog, profile, and installation authority
remain distinct. Release remains outside `CapabilityKey`; Slice 6 owns exact
catalog availability and selection, Slice 7 owns typed requirement selectors,
and Slice 8 owns the smallest later private release-aware provider authority.

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

Slice 6 declares constructed catalogs available under exact compiler or
logical-project authority, filters project applicability by exact `ProjectRoot`
equality, and selects one exact target as `UNDECLARED`, `SELECTED`, `AMBIGUOUS`,
or `CONFLICT`. Candidate identity retains catalog reference, target, and
content SHA-256; all declaration provenance remains additive with no owner or
release precedence. It adds no provider, lookup, profile, package,
installation, runtime, inspection, or lowering behavior. The controlling
contract is [Phase 57 Slice 6 declaration, availability, and selection](spec/phase57-extension-catalog-declaration-availability-selection-v1.md).

Slice 7 keeps semantic `CapabilityKey` identity separate from typed physical
catalog lookup identity. One complete sidecar binds exact requirement positions
to existing five-family `ExtensionCatalogLookupScope` values, validates exact
extension-native ownership, and uses a closed typed correspondence from key
dialect `postgresql` to catalog family `PostgreSQL` without changing either
stored vocabulary. Provider/checker/matrix integration remains Slice 8. The
controlling contract is [Phase 57 Slice 7 extension-signature requirement selectors](spec/phase57-extension-signature-requirement-selector-v1.md).

Slice 8 consumes those typed selectors plus precomputed Slice 6 selections in
one target-scoped private provider context. Exact catalog groups, conservative
cataloged-unmodeled relevance, and lookup-scoped completeness project through
the existing capability lookup and checker algebra. Matrix columns retain
independent multi-requirement provider contexts without re-selection or
cross-target aggregation. The controlling contract is
[Phase 57 Slice 8 extension-signature provider and checking integration](spec/phase57-extension-signature-provider-checking-integration-v1.md).

Slice 9 adds the first evidence-backed production catalog: pgvector `0.8.6`
for the exact PostgreSQL `18` and extension `vector` target. It accounts for
every pinned five-family declaration, retains arrays and pseudo-types as
cataloged-unmodeled evidence, claims no completeness, and exercises the frozen
Slice 6–8 provider/checker chain without auto-availability. The controlling
contract is [Phase 57 Slice 9 pgvector catalog](spec/phase57-pgvector-v086-postgresql18-catalog-v1.md).

Slice 10 adds the second production catalog, PostgreSQL `pg_trgm` 1.6 for the
exact PostgreSQL 18 target. It also records a non-production ltree 1.3
multi-native/array representability probe and a bounded PostGIS 3.6.4 core
stress audit. Unsupported shapes remain cataloged-unmodeled, no generic schema
changes, ltree/PostGIS catalogs, or support claims are introduced, and
completeness remains empty. The controlling contract is
[Phase 57 Slice 10 pg_trgm and representability audits](spec/phase57-pg-trgm-ltree-postgis-representability-v1.md).

Slice 11 derives one separate private extension-catalog inspection from exact
Slice 8 provider contexts. It retains both production catalog artifacts,
source/entry/group/completeness evidence, typed selectors, precomputed
availability and selection provenance, provider inputs/results, and separately
frozen canonical inspection bytes without re-selection or provider-algebra
duplication. It adds no registry, public output, runtime I/O, ltree/PostGIS
production catalog, or capability-inspection change. The controlling contract
is [Phase 57 Slice 11 extension-catalog inspection](spec/phase57-extension-catalog-inspection-v1.md).

Slice 12 routes both frozen catalog and inspection canonical serialization
through separate layer-correct total pure evaluators. One reviewed 47-vector
corpus plus Python 3.12/3.13, hash-seed, relocation, combined, and installed-
wheel evidence freezes portability without changing catalog or inspection
semantics. It adds no registry, runtime discovery, public output, or package
asset. The controlling contract is
[Phase 57 Slice 12 catalog pure-boundary hardening](spec/phase57-extension-catalog-pure-boundary-differential-e2e-v1.md).

Slice 13 audits the complete existing chain, reconciles every material deferred
subject to one terminal disposition, assigns release-aware PostgreSQL core and
generated/multi-source extension catalog assembly to Phase 69, and freezes the
private Phase 58 handoff without implementing it. It adds no product semantics.
The controlling closure is
[Phase 57 Slice 13 completion audit and Phase 58 handoff](spec/phase57-completion-audit-phase58-handoff-v1.md).

## Phase 58 route

Phase 58 is active, Slices 1–11 are completed, Slice 12 is current, and Slice 13 is next / unstarted.
The original route had exactly 12 slices. After published Slice 8, a read-only
runtime-builder authority audit proved an independent missing lifecycle, so
the route expanded to 16 slices. After published Slice 11, production tracing
proved the package requirement-to-typed-physical-selector edge was still
absent, so the current route has exactly 17 slices. Published Slices 1–11 are
unchanged. These rows assign ownership only; they do not authorize a later
slice.

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
| 12 | Package-owned extension-signature typed physical selector authority |
| 13 | Project Explain runtime authority builder and zero-context adaptation |
| 14 | `pietto explain --project` text/JSON integration; existing single-file explain zero-delta |
| 15 | Real multi-target E2E scenarios spanning package, capability, catalog, all evaluation states, and all checked result classes |
| 16 | Public pure/differential compatibility boundary; goldens; Python 3.12/3.13; hash seed; relocation; installed wheel |
| 17 | Completion audit; Phase 59 handoff; Phase 60/64/67/69 readiness reconciliation |

The human-readable direction is `Project Explain Artifact v1`, with public
marker `pietto.project-explain.v1` and future additive commands
`pietto explain --project <root>` and
`pietto explain --project <root> --format json`. Existing single-file
`Semantic Metadata Artifact v1` remains exact zero-delta.

Project explain is one deterministic compiler-analysis snapshot, not installed
or runtime state. It composes bounded public projections from the independent
private package, capability, and extension-catalog inspection authorities. Its
portability denominator is one explicit ordered evaluated target set; the raw
requirement-by-target matrix remains normative, and only `UNSUPPORTED` or
`ABSENT` is a definite gap. The public classification is exactly `PORTABLE`,
`NOT_PORTABLE`, or `INDETERMINATE`.

The controlling architecture is
[Phase 58 Slice 1 project explain and portability scope lock](spec/phase58-project-explain-portability-scope-lock-v1.md).

Slice 2 adds only the private common model: exact artifact identity, closed
evidence and requirement-stage vocabularies, relocation-stable logical paths,
detached locations/diagnostics, and a payload-generic success/failure envelope.
It adds no package, requirement, target, matrix, catalog, portability,
artifact-local reference, JSON, text, or CLI behavior. The controlling
foundation is
[Phase 58 Slice 2 common model and envelope](spec/phase58-slice2-project-explain-common-model-envelope-v1.md).

Slice 3 projects the existing successful package inspection and one exactly
package-ordered capability inspection per package into detached package,
asset, direct-dependency, declared requirement collection, and REQUEST records.
It preserves dependency-first package order, source occurrence multiplicity,
`declared_by`, root-scoped `requested_by`, and the bounded root-to-declaring-
package-to-occurrence why chain without re-resolving or re-checking. It adds no
target, matrix, catalog, portability, generic reference, JSON, text, or CLI
behavior. The controlling projection is
[Phase 58 Slice 3 package and requirement provenance](spec/phase58-slice3-project-explain-package-requirement-provenance-v1.md).

Slice 4 projects the exact root-owned evaluated target denominator shared by
every package matrix, detached target/profile authority, package-by-target
`UNDECLARED`/`BLOCKED`/`CHECKED` state, availability and blocker evidence, and
requirement-by-target cells with all five checked statuses and bounded lookup
reasons/supports. It validates the existing closed checker algebra without
rerunning checking or lookup, represents an explicitly empty denominator
without synthetic results, and adds no catalog-specific evidence, portability,
generic reference, JSON, text, or CLI behavior. The controlling matrix is
[Phase 58 Slice 4 requirement target matrix](spec/phase58-slice4-project-explain-requirement-target-matrix-v1.md).

Slice 5 projects exact extension-catalog inspection authority for checked
`EXTENSION_SIGNATURE` requests into typed selectors, catalog identities and
targets, selection outcomes, bounded relevant entry/source evidence, and
completeness evidence. It preserves ambiguity, conflict, unmodeled evidence,
package/target order, and exact Slice 4 provider-result agreement without
selection, provider, lookup, portability, JSON, text, or CLI work. The
controlling projection is
[Phase 58 Slice 5 extension-catalog evidence](spec/phase58-slice5-project-explain-extension-catalog-evidence-v1.md).

Slice 6 derives conservative requirement and project portability solely from
the exact Slice 4 matrix. It preserves target and requirement order, treats
only `UNSUPPORTED` and `ABSENT` as definite gaps, gives those gaps precedence
over indeterminate evidence, and keeps an empty denominator indeterminate
while allowing zero requirements over a non-empty denominator to be portable.
It adds no Slice 5-dependent classification, target ranking, score,
recommendation, final payload, generic reference, JSON, text, or CLI behavior.
The controlling derivation is
[Phase 58 Slice 6 portability derivation](spec/phase58-slice6-project-explain-portability-derivation-v1.md).

Slice 7 composes the exact Slice 3–6 detached sections into the final in-memory
payload and adds positional artifact-local references for bounded
REQUEST-to-RESOLUTION-to-RESULT explanations. It validates cross-section
completeness, preserves section authority and ordering, and deduplicates only
repeated source-reference coordinates without collapsing source occurrences.
It adds no graph/global IDs, JSON, text, CLI, private authority reconstruction,
or new portability semantics. The controlling composition is
[Phase 58 Slice 7 composition and references](spec/phase58-slice7-project-explain-composition-references-v1.md).

Slice 8 serializes that exact final payload into the stable public Project
Explain JSON v1 machine contract. It owns the closed four-field envelope,
explicit carrier mappings, typed selector identities, artifact-local
references, null and array rules, compact deterministic UTF-8 bytes, logical-
path privacy, byte-exact success/failure goldens, and schema-evolution locks.
It adds no CLI route, text renderer, project discovery, compilation, or new
payload model. The controlling contract is
[Phase 58 Slice 8 Project Explain JSON v1](spec/phase58-slice8-project-explain-json-v1.md).

Slice 9 records the production audit that found the first missing runtime edge
after `PackageInspectionFactSet`, freezes package ownership of requirement
declarations, project ownership of ordered targets/profiles, and compiler
ownership of exact bundled-catalog availability without selection, and expands
the route from the historical 12 slices to the then-current 16. Slice 10 owns
package manifest v2 requirement authority, Slice 11 owns project config v4
target/profile/catalog authority, and the post-Slice-11 amendment moves exact
orchestration plus the minimum zero-context compatibility extension to Slice
13. It adds no
production, config, manifest, matrix, JSON, text, CLI, package, golden, or
generated behavior. The controlling lock is
[Phase 58 Slice 9 runtime authority architecture](spec/phase58-slice9-runtime-authority-architecture-route-lock-v1.md).

Slice 10 adds package manifest schema v2 with an optional, package-owned,
source-proven capability requirement declaration. It reuses exact current
`CapabilityKey` values, preserves authored occurrence order, distinguishes
undeclared from declared-empty, binds each loaded package only to its own
declaration, and relies on the existing full package-content digest. It adds no
target, profile, checker, provider, catalog-selection, Project Explain, CLI,
public, generated, or golden behavior. The controlling contract is
[Phase 58 Slice 10 package capability requirement declaration](spec/phase58-slice10-package-capability-requirement-declaration-v1.md).

Slice 11 adds project configuration schema v4 with one mandatory explicit
capability environment. It materializes project-authored static profiles and
PROJECT evidence, retains an ordered evaluated-target denominator and ordered
overlay selections, reuses exact existing profile composition and availability,
and declares only the bundled pgvector and pg_trgm catalogs as compiler
availability. It adds no default target/profile, catalog selection, provider,
checking, Project Explain, or CLI behavior. The controlling contract is
[Phase 58 Slice 11 project capability environment authority](spec/phase58-slice11-project-capability-environment-authority-v1.md).

Slice 12 adds package manifest schema v3 with a package-owned typed physical
selector sidecar for every `EXTENSION_SIGNATURE` requirement. It reuses the
existing five-family `ExtensionCatalogLookupScope` authority, preserves exact
coverage/order and extension ownership, leaves schema-v2 extension requirements
valid but unbound, and relies on the existing whole-package digest. It performs
no catalog selection, provider construction, checking, Project Explain, or CLI
work. The controlling contract is
[Phase 58 Slice 12 package extension-signature selector authority](spec/phase58-slice12-package-extension-signature-selector-authority-v1.md).

## Retained later ownership

| Phase | Owner |
| ---: | --- |
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
| 69 | Release-aware PostgreSQL core builtin signature catalog, backend-specific core catalog foundations, generated/multi-source extension catalog assembly, extension-specific lowering, and additional dialect foundations |
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
