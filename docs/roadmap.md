# Roadmap

Pietto is a readable, typed, modular SQL authoring compiler. Future work must
be selected by current user/product need, not by an inherited phase number.
Every substantive slice begins by identifying its authority roots, current
invariants, compatibility boundary, and the smallest behavior that is actually
needed.

The active product direction is a typed, target-independent advanced-window
semantic model built on the existing Phase 53 window, Phase 56 capability, and
Phase 59 occurrence/lineage authorities. Project Explain v1 remains unchanged.
Pietto remains compiler-only: no package or catalog registry, dependency
solver, remote loading, database execution, runtime evaluation, installation
discovery, or implicit project discovery is authorized. Future work must
preserve established identity, complete collection, provenance, ordering,
trust, and diagnostic boundaries unless a new explicit product decision
changes them.

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

All 17 slices are completed. Phase 58 is complete.
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
| 15 | Reachability-aware real multi-target E2E plus structural and direct-owner assurance for currently unreachable generic states |
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

Slice 13 adds one private explicit-root Project Explain runtime builder. It
orchestrates the existing trusted project/package loaders, package requirements
and selectors, project capability environment, exact catalog selection/provider,
capability matrix/inspection, and Slice 3–7 projections. It generalizes the
private matrix and inspection authorities to preserve undeclared, declared-empty,
and declared requirements over an explicitly empty target denominator without
synthetic cells. It adds no CLI route, text renderer, public JSON field, default
target, installation inference, or second resolver/checker. The controlling
contract is
[Phase 58 Slice 13 Project Explain runtime builder](spec/phase58-slice13-project-explain-runtime-builder-v1.md).

Slice 14 exposes that private runtime through the existing `pietto explain`
command with explicit file-XOR-project parsing, deterministic human text, and
the unchanged Project Explain JSON v1 serializer. It maps the existing runtime
outcomes to exits 0/1/2, emits JSON success and failure envelopes on stdout,
keeps human failures on stderr, and preserves the existing single-file Semantic
Metadata Artifact v1 route byte-for-byte. It adds no runtime semantics,
projection algorithm, public JSON field, implicit project root, or broad
multi-target assurance. The controlling contract is
[Phase 58 Slice 14 Project Explain CLI text and JSON](spec/phase58-slice14-project-explain-cli-text-json-v1.md).

Slice 15 adds a real multi-package, multi-target authored-input assurance corpus
for every currently production-reachable requirement, checked-status, catalog,
portability, failure, JSON, and text behavior. It records `BLOCKED` and catalog
`AMBIGUOUS`/`CONFLICT` as generic representable states that current production
authority structurally prevents at the top-level authored runtime, and pairs
those proofs with direct tests at the actual checker and catalog-selector
owners. It adds no production path, authored catalog override, synthetic final
fact, new product semantics, or route expansion. The controlling contract is
[Phase 58 Slice 15 reachability-aware multi-target E2E assurance](spec/phase58-slice15-reachability-aware-multi-target-end-to-end-assurance-v1.md).

Slice 16 adds one bounded differential observation and common expectation
authority for the already-published Project Explain corpus. It proves exact
structured, JSON, text, exit, ordering, relocation, hash-seed, Python 3.12/3.13,
source-tree, and installed-wheel compatibility while reusing the central pure,
generated, golden, and package-smoke owners. It adds no production path,
product state, public field, normalization, version-specific expectation, or
new golden. The controlling contract is
[Phase 58 Slice 16 pure differential compatibility assurance](spec/phase58-slice16-pure-differential-compatibility-assurance-v1.md).

Slice 17 audits the complete 17-slice owner chain, reconciles every Phase
58-owned exit criterion to current source/tests/CI, records zero self-owned-open
subjects, and freezes the Phase 59 handoff plus Phase 60–70 readiness without
implementing later work. It adds no production semantics, public field,
release operation, or route expansion. The controlling closure is
[Phase 58 completion audit and Phase 59 handoff](spec/phase58-completion-audit-phase59-handoff-v1.md).

## Phase 59 route

Phase 59 and all 12 Phase 59 Slices are completed. The Validation/Test
Performance Optimization Interlude is also completed by successful natural
exact-head CI on its Slice 6 commit, which activates Phase 60. The published
Phase 59 route has exactly 12 slices.

The exact owner is **Local package graph, attribution, provenance, and lineage**.

| Slice | Owner |
| ---: | --- |
| 1 | Graph Domains, Identity Laws, And Route Lock |
| 2 | Private Package Graph Model And Snapshot Identity |
| 3 | Canonical Package Graph Construction |
| 4 | Requirement And Selector Attribution |
| 5 | Capability, Catalog, And Typed Negative Evidence Provenance |
| 6 | Direct, Transitive, And Why-Not Provenance |
| 7 | Package-to-Module Attribution Bridge |
| 8 | Semantic And Field-Lineage Integration |
| 9 | Private Graph Integrity, Inspection, Query, And Canonical Pure Boundary |
| 10 | Real Multi-Package Provenance And Lineage E2E |
| 11 | Differential Compatibility Assurance |
| 12 | Completion Audit And Phase 60 Handoff |

Slice 1 freezes graph-snapshot-scoped identity, separate typed domains,
occurrence/witness links, ordered and n-ary facts, sparse positive topology
with typed evidence, domain-specific cycle semantics, all-path provenance,
private canonical inspection readiness, and the exact route without production
implementation. The controlling contract is
[Phase 59 Slice 1 graph domains and identity laws](spec/phase59-graph-domains-identity-laws-route-lock-v1.md).

Slice 2 adds the immutable private package/dependency graph value model:
identity-equal runtime snapshot scopes, typed package and authored-dependency
refs, separate semantic/release/content/role facts, witnessed direct links,
ordered snapshot tuples, scope-enforced lookup, and exact successful/rejected/
error result invariants. It adds no builder, traversal, canonical serializer,
future-domain placeholder, Project Explain field, public export, or CLI. The
controlling model is
[Phase 59 Slice 2 private package graph model](spec/phase59-slice2-private-package-graph-model-snapshot-identity-v1.md).

Slice 3 constructs that model deterministically from one exact
`PackageInspectionFactSet` and its retained load-plan authority. It maps every
inspection package and authored dependency occurrence in existing order,
retains exact dependency witnesses and resolved target positions, creates one
fresh runtime scope per construction, and projects exact success/rejected/error
terminals without partial graphs. It adds no loader, resolver, traversal,
canonical serializer, public field, or CLI behavior. The controlling contract
is [Phase 59 Slice 3 canonical package graph construction](spec/phase59-slice3-canonical-package-graph-construction-v1.md).

Slice 4 attributes each package's exact undeclared/declared requirement
collection, authored requirement occurrences, and package-owned selector
occurrences into separate typed graph domains. It preserves package then local
occurrence order, equal keys across packages, exact requirement/selector
witnesses, schema-v2 unbound requirements, and schema-v3 position-based
coverage without checking, provider, catalog, or public behavior. The
controlling contract is [Phase 59 Slice 4 requirement and selector attribution](spec/phase59-slice4-requirement-selector-attribution-v1.md).

Slice 5 attaches existing Phase 58 capability checks, blockers, target
contexts, catalog selections, providers, catalogs, and source facts to exact
Slice 4 requirement and selector occurrences. Snapshot-scoped typed refs use
only package-local requirement/selector and target positions; exact upstream
fact sets remain the witnesses. Checked statuses, `BLOCKED`, catalog selection
outcomes, provider lookup states, source order, and multiplicity remain typed
and distinct without rechecking, reselection, catalog rebuilding, inferred
negative edges, or installation identity. The controlling contract is
[Phase 59 Slice 5 capability, catalog, and typed negative evidence provenance](spec/phase59-slice5-capability-catalog-typed-negative-evidence-provenance-v1.md).

Slice 6 projects existing dependency, requirement, selector, capability, and
catalog-evidence occurrences into closed-union typed direct steps retaining
their exact witnesses. A narrow private derivation enumerates every complete
path on demand in direct occurrence order without sorting, winner selection,
reverse indexes, caching, or snapshot closure. Why-not results pair each
positive path with its exact existing non-success capability check, blocker,
or catalog-provider evidence; missing edges and zero-target authority create
nothing. The controlling contract is
[Phase 59 Slice 6 direct, transitive, and why-not provenance](spec/phase59-slice6-direct-transitive-why-not-provenance-v1.md).

Slice 7 bridges every successful package occurrence to its exact trusted
loaded modules and source-ordered AST declarations. Module and declaration
refs are snapshot-scoped and package-qualified; their identity uses only
package/module/local positions, while exact loaded package, module, and
definition objects remain witnesses. Equal paths, names, source bytes, or
digests in different packages never merge. The bridge adds ownership only: it
does not construct semantic catalogs, grant visibility, create cross-package
imports, or extend Slice 6 traversal. The controlling contract is
[Phase 59 Slice 7 package-to-module attribution bridge](spec/phase59-slice7-package-to-module-attribution-bridge-v1.md).

Slice 8 joins each package occurrence to one exact existing package-neutral
module identity fact set, then projects package-qualified field and let
occurrences plus source, direct, renamed, computed, let, aggregate, and
current-window lineage. Exact input witnesses, roles, local positions, order,
multiplicity, and typed non-concrete statuses/reasons remain authoritative;
transitive paths remain on-demand. The integration adds no semantic inference,
cross-package visibility, eager closure, reverse index, frame semantics, public
artifact, or serializer. The controlling contract is
[Phase 59 Slice 8 semantic and field-lineage integration](spec/phase59-slice8-semantic-field-lineage-integration-v1.md).

Slice 9 revalidates every Slice 2–8 graph invariant and projects one private
canonical inspection with closed typed local coordinates, ordered direct
positive links, separate typed negative states, and no runtime scope token.
Pure evaluation rejects malformed ownership, domain, ordinal, dangling-ref,
and canonical-data shapes. Direct upstream/downstream and all-path/why queries
scan the same direct-link authority on demand; no reverse index, cache, eager
closure, sorting, deduplication, or winner is introduced. The controlling
contract is [Phase 59 Slice 9 private graph integrity, inspection, query, and canonical pure boundary](spec/phase59-slice9-private-graph-integrity-inspection-query-canonical-pure-boundary-v1.md).

Slice 10 proves the complete private graph from real temporary authored
schema-v4 project, root/dependency package manifests, package modules,
capability requirements/selectors, and per-package schema-v2 semantic
compilation. It follows existing discovery, loading, inspection, capability,
semantic, graph, integrity, canonical inspection, and query entry points. Equal
module/declaration/field spellings remain package-distinct; reachable source,
direct, renamed, computed, let, aggregate, and current-window lineage plus one
real typed why-not case are exercised without hand-building a final snapshot or
adding production behavior. The controlling contract is
[Phase 59 Slice 10 real multi-package provenance and lineage E2E](spec/phase59-slice10-real-multi-package-provenance-lineage-e2e-v1.md).

Slice 11 reuses that real authored corpus under Python 3.12/3.13, four fixed
hash seeds, distinct project and source roots, independent runtime scopes, and
an isolated installed wheel. One common test-local expectation compares the
complete ordered private inspection and query projection, exact canonical
bytes, typed why-not terminal, Project Explain/CLI checkpoints, and intentional
runtime-ref inequality without normalizing paths, order, or multiplicity. It
adds no production behavior, public artifact, golden file, workflow, or
performance optimization. The controlling contract is
[Phase 59 Slice 11 differential compatibility assurance](spec/phase59-slice11-differential-compatibility-assurance-v1.md).

Slice 12 audits all 12 route owners, all 22 exit criteria, the exact Slice
1–11 commit/tree/natural-CI chain, identity and provenance laws, private/public
boundaries, compatibility, zero self-owned-open subjects, and Phase 60–70
readiness. It adds no production behavior and binds the mandatory performance
interlude without beginning it or Phase 60. The controlling closure is
[Phase 59 completion audit and Phase 60 handoff](spec/phase59-completion-audit-phase60-handoff-v1.md).

Project Explain v1, existing CLI behavior, package loading, semantic lineage,
and all public schemas remain exact zero-delta. Successful natural exact-head
CI on the single Slice 12 commit established Phase 59 completion without a
status-only follow-up commit. The performance interlude then completed on its
own exact-head natural CI and activated Phase 60 without changing Phase 59.

## Validation/Test Performance Optimization Interlude

This mandatory owner is `COMPLETED` after Phase 59 completion:

```text
Phase 59 completion
-> Validation/Test Performance Optimization Interlude
-> Phase 60 activation
```

Its owner is evidence-backed optimization of Pietto's test/validation runtime
without weakening validation semantics or deterministic authority. It must
profile pytest and validator stages, measure repeated filesystem/source/AST/
import scans, identify duplicated historical readers, and consider an
immutable session-scoped repository test index only when profiling supports
it. Scanner consolidation must preserve policy; determinism and isolation must
be audited before any pytest-xdist benchmark, and parallel execution requires
measured safety and benefit.

| Slice | Owner |
| ---: | --- |
| 1 | Baseline Profiling, Cost Attribution, And Route Lock |
| 2 | Differential Probe Runtime Decomposition And Optimization |
| 3 | Repository Reader Acquisition Reuse |
| 4 | Validator Static-Analysis Stage Optimization Investigation |
| 5 | Current-Suite Isolation, Resource-Aware Xdist Scheduling, And CI Parallelism Decision |
| 6 | Completion Benchmark And Phase 60 Readiness Assurance |

Slice 1 measured the serial suite and validator stages, attributed the dominant
cost to repeated cross-process differential probes, recorded historical
repository-reader duplication, and froze this six-Slice route without
implementing an optimization. A complete general-purpose repository test index
is only partially supported: immutable shared acquisition is justified for the
measured duplicate-reader slice, but repository scans are not the dominant wall
time. Its published evidence and success metrics are
[Interlude Slice 1 baseline profiling and route lock](spec/validation-performance-interlude-slice1-baseline-profiling-cost-attribution-route-lock-v1.md).

Slice 2 decomposed runtime inside the cross-process differential probes and
batched only JSON/text CLI startup for the same exact project variant. All 18
outer variants, 116 semantic CLI calls, and 20 independent Phase 59 graph
builds remain; fixture-owned subprocess launches fell from 142 to 84. Three-run
targeted wall median fell from 95.69s to 61.44s, materially beyond observed
noise. Its published evidence is
[Interlude Slice 2 differential probe runtime decomposition and optimization](spec/validation-performance-interlude-slice2-differential-probe-runtime-decomposition-optimization-v1.md).

Slice 3 caches exact text, literals, imports, identifiers, and top-level
structural names for paths explicitly selected by nine measured scanner owners
while leaving every path and policy selection owner-local.
Each owner retains its exact historical `glob`/`rglob` path universe and AST
node-class selection. Targeted text reads fall from 2,412 to 483 and AST parses
from 1,661 to 484; duplicate text acquisition falls to zero, duplicate AST
acquisition falls from 1,201 to one. The repaired three-run wall median is
6.31s against the 6.38s pre-optimization median; that 0.07s difference is
within observed noise, so no wall-time gain is claimed and no material
regression is established. The controlling evidence is
[Interlude Slice 3 repository reader acquisition reuse](spec/validation-performance-interlude-slice3-repository-reader-acquisition-reuse-v1.md).

Slice 4 preserves the exact 137-file
production and 358-file test typing authorities while retaining the published
two-stage Pyright validator. The investigated one-process candidate preserved
representative diagnostics, but its 52.94s median versus the legacy 53.13s
median improved by only 0.19s / 0.36%, within observed noise. The optimization
is not adopted; Slice 4 closes with `NO MATERIAL GAIN — CURRENT TWO-STAGE
AUTHORITY RETAINED`. The controlling evidence is
[Interlude Slice 4 validator static-analysis stage optimization](spec/validation-performance-interlude-slice4-validator-static-analysis-stage-optimization-v1.md).

Slice 5's isolation audit found no
shared-state blocker, and resource measurements select four `loadfile` workers
from usable CPU and effective available memory with a serial fallback. Two
full serial runs have a 130.30s median; two equivalent four-worker runs have a
61.00s median, a 53.2% reduction, with unchanged 10,348-test and subprocess
counts and safe RAM pressure. The same automatic policy runs inside both
existing GitHub Python jobs. The controlling evidence is
[Interlude Slice 5 resource-aware xdist and CI parallelism decision](spec/validation-performance-interlude-slice5-resource-aware-xdist-and-ci-parallelism-decision-v1.md).

Slice 6 completed the Interlude. Fresh collection is 2.99s for 10,352 tests.
Two current serial runs have a 135.21s median, while two resource-aware parallel
runs have a 74.60s median, a like-for-like 44.8% reduction. The six-Slice
scorecard closes adopted, structural, no-gain, and later-owned decisions with
`Interlude self-owned-open = 0`. The controlling evidence is
[Interlude Slice 6 completion benchmark and Phase 60 readiness](spec/validation-performance-interlude-slice6-completion-benchmark-phase60-readiness-v1.md).

Python 3.12/3.13, generated, golden, package-smoke, reader-closure, and failure
semantics remain mandatory. The Python suite is not rewritten in Rust merely
for speed, and the first Rust-kernel decision remains later-owned. Interlude
Slices 1–6 change no production or validation semantics. Natural CI retains
both Python jobs and uses the same resource-aware pytest policy as local
validation.

Successful natural exact-head CI on the single Slice 6 completion commit
completed the Interlude and handed off authority. Phase 60 subsequently
completed all 13 Slices on successful natural exact-head CI. Phase 61 is now
`ACTIVE`; Slices 1–5 and both unnumbered Slice 5 prerequisites are completed,
Slice 6 cross-module composition is current, and Slice 7 remains next /
unstarted.

## Phase 60 route

Phase 60 and all 13 Slices are completed by live Git and successful natural
exact-head CI. Phase 61 is active. The published Phase 60 route has exactly 13
slices.

The exact owner is **Advanced Windows And Phase 51–60 Readiness Checkpoint**.

| Slice | Owner |
| ---: | --- |
| 1 | Scope / Semantic Laws / Route Lock |
| 2 | Authored-To-Resolved Window And Frame Model |
| 3 | Structural Legality, Function-Frame Policy, Empty-Frame Classification, And Stage/Nesting Rules |
| 4 | ROWS Semantics And Lowering |
| 5 | RANGE Semantics, Direction-Aware Bounds, Structural ORDER BY/Type Seam, And Lowering |
| 6 | GROUPS And Peer-Group Semantics And Lowering |
| 7 | EXCLUDE Semantics Across All Units |
| 8 | Query-Local Named-Window Scope And DAG Inheritance |
| 9 | Value/Navigation Modifiers |
| 10 | Capability-Gated Lowering, Lineage, Determinism/Private Inspection, And Semantic-Equivalence Readiness |
| 11 | Real Authored Advanced-Window E2E |
| 12 | Differential Compatibility |
| 13 | Phase 51–60 Completion/Readiness Audit And Phase 61 Handoff |

Slice 1 freezes distinct authored/resolved/validated/target-lowerable stages,
typed lazy frame semantics, exact authorship/default provenance, unit-sensitive
`CURRENT ROW`, direction-aware RANGE bounds, post-clipping `EXCLUDE`, typed
function/frame/modifier policy, query-local monotonic named-window DAGs,
semantic equivalence without occurrence merging, capability-gated lowering,
Phase 59 lineage attachment, the later-owner ledger, the optimized future-test
contract, and the exact route without production implementation. The
controlling contract is
[Phase 60 Slice 1 advanced-window semantic laws and route lock](spec/phase60-advanced-windows-scope-semantic-laws-route-lock-v1.md).

Slice 2 adds the private frozen authored/resolved window-frame model in the
existing semantic owner. Closed frame units, bound tags, exclusions, authored
omission/shorthand/`BETWEEN`, component origins, typed frame applicability,
and pure default normalization reuse exact existing expression objects without
adding legality, named-window resolution, analysis integration, IR, SQL, or
public behavior. The controlling contract is
[Phase 60 Slice 2 authored/resolved window-frame model](spec/phase60-slice2-authored-resolved-window-frame-model-v1.md).

Slice 3 adds the private validated semantic stage, categorical bound legality,
complete typed rejection evidence, conservative frame-emptiness
classification, and exact function/frame policy derived from the existing
builtin identity metadata. It rejects explicit frames for frame-insensitive
functions and nested window inputs while preserving current same-stage scope
and aggregate-before-window behavior. It adds no grammar, unit-specific
membership/lowering, target capability, identity/lineage, IR, SQL, CLI, JSON,
or public behavior. The controlling contract is
[Phase 60 Slice 3 frame validation and function policy](spec/phase60-slice3-frame-validation-function-policy-v1.md).

Slice 4 adds the authored ROWS grammar/AST path, routes it through the Slice 2
and Slice 3 stages, and defines lazy physical-position interval/intersection
semantics plus the canonical ROWS lowering contract. All eight current
frame-insensitive functions reject explicit ROWS with function-policy evidence.
No frame IR, SQL renderer branch, legal frame-sensitive identity, capability,
lineage, or public schema is added. The architecture continuation keeps the
13-slice route unchanged: Slices 4-7 establish frame semantics/lowering
contracts, Slice 9 introduces the first legal frame-sensitive value-function
callers and activates SQL emission, Slice 10 owns capability gating, and Slice
11 owns broad real authored E2E. The controlling contract is
[Phase 60 Slice 4 ROWS semantics and lowering](spec/phase60-slice4-rows-semantics-lowering-v1.md).

Slice 5 adds authored RANGE to the shared frame grammar/AST and defines a lazy
ordering-domain request with explicit ASC/DESC offset orientation. Offset
frames require exactly one complete ordering key and emit unresolved Phase 64
type/arithmetic requirements; CURRENT ROW consumes an explicit Slice 6 peer
boundary seam without computing peers. Current functions continue rejecting
explicit RANGE. No peer algorithm, frame IR, SQL renderer, legal
frame-sensitive identity, capability, lineage, or public schema is added. The
controlling contract is
[Phase 60 Slice 5 RANGE semantics and lowering](spec/phase60-slice5-range-semantics-lowering-v1.md).

Slice 6 adds authored GROUPS and one canonical peer authority driven only by a
complete typed adjacent-row/composite-order comparison matrix. It builds
maximal contiguous lazy peer groups, implements group-index offsets/clipping,
and replaces Slice 5's temporary RANGE CURRENT ROW evidence with the same
group authority. Unresolved Phase 64 comparisons produce no partial groups;
no Python equality, EXCLUDE, frame IR, SQL renderer, legal frame-sensitive
identity, capability, lineage, or public schema is added. The controlling
contract is
[Phase 60 Slice 6 GROUPS and peer semantics](spec/phase60-slice6-groups-peer-semantics-v1.md).

Slice 7 adds authored EXCLUDE to ROWS, RANGE, and GROUPS and applies the four
closed modes through one lazy post-clipping physical-membership view. GROUP
and TIES consume the exact Slice 6 peer authority and propagate unresolved
comparison failure without partial exclusion; NO OTHERS and CURRENT ROW avoid
that dependency. Current functions still reject every explicit frame, and no
frame IR, SQL renderer, legal frame-sensitive identity, capability, lineage,
or public schema is added. The controlling contract is
[Phase 60 Slice 7 EXCLUDE semantics](spec/phase60-slice7-exclude-semantics-v1.md).

Slice 8 adds six exact query-local named-window forms, block-scoped occurrence
identity, collection-first exact namespaces, forward/backward single-base DAG
resolution, deterministic cycle/dangling/duplicate failure, and monotonic
PARTITION/ORDER/FRAME template and use composition. Defaults and function
frame applicability occur only after concrete use composition; inherited
explicit frames remain visible to existing function policy. The Slice is
semantic-only: no named IR, SQL, capability, inlining, lineage, inspection,
or public schema is added. The controlling contract is
[Phase 60 Slice 8 query-local named windows](spec/phase60-slice8-query-local-named-windows-v1.md).

Public syntax now recognizes ROWS, RANGE, GROUPS, EXCLUDE, and query-local
named-window declarations and uses. Slice 8 intentionally stopped named source
before IR pending the Slice 10 capability owner.
Live Git and natural exact-head CI own Slice 8 completion without a status-only
follow-up commit.

Slice 9 adds exact use-local NULL treatment and `nth_value` direction
authorship, frame-sensitive `first_value`/`last_value`/`nth_value` semantics,
post-EXCLUDE candidate selection, lag/lead IGNORE NULLS navigation, persisted
validated window analysis, target-neutral concrete frame IR, and the first
narrow inline advanced-window SQL activation. PostgreSQL and MySQL fixed
RESPECT/FROM FIRST behavior is used only for exact supported combinations;
unsupported target shapes fail closed. Named-window SQL and named Project/
lineage integration remain deferred. The controlling contract is
[Phase 60 Slice 9 value/navigation modifiers](spec/phase60-slice9-value-navigation-modifiers-v1.md).

Live Git and natural exact-head CI own Slice 9 completion without a status-only
follow-up commit.

Slice 10 integrates named-window target-neutral IR, exact four-state
PostgreSQL/MySQL capability decisions, native reachable `WINDOW` emission,
exact inline fallback, Project window-result facts, separate data lineage and
window semantic provenance, and Phase 59 package-graph private inspection.
Project Explain v1 and public schemas remain unchanged. The controlling
contract is [Phase 60 Slice 10 capability, lineage, and inspection integration](spec/phase60-slice10-capability-lineage-inspection-integration-v1.md).

Live Git and natural exact-head CI own Slice 10 completion without a
status-only follow-up commit.

Slice 11 proves the complete published advanced-window chain from a bounded
real authored corpus through parser, semantic analysis, IR, exact PostgreSQL
and MySQL SQL, the paired CLI path, Project semantic provenance/data lineage,
and Phase 59 package-graph private inspection. It covers native reorder,
native preserve, exact inline fallback, ROWS/RANGE/GROUPS, all four EXCLUDE
states, effective defaults, RESPECT NULLS, and FROM FIRST without constructing
final authority carriers or changing production/public behavior. The
controlling contract is [Phase 60 Slice 11 real authored advanced-window E2E](spec/phase60-slice11-real-authored-advanced-window-e2e-v1.md).

Live Git and natural exact-head CI own Slice 11 completion without a
status-only follow-up commit.

Slice 12 proves one reviewed advanced-window observation across four fixed
hash seeds, all available Python 3.12/3.13 interpreters, independent project
roots, source relocation, unrelated CWD/ambient state, command-order reversal,
and an isolated installed wheel. It preserves native reorder, native preserve,
exact inline fallback, frame/modifier semantics, Project provenance/data
lineage, and private inspection while requiring exact fail-closed PostgreSQL
and MySQL backend-negative terminals. It adds no production, public schema,
backend support, or semantic law. The controlling contract is [Phase 60 Slice 12 differential compatibility](spec/phase60-slice12-differential-compatibility-v1.md).

Live Git and natural exact-head CI own Slice 12 completion without a
status-only follow-up commit.

Slice 13 binds all 13 owners, the exact Slice 1–12 first-parent publication
chain, the complete advanced-window exit ledger, zero Phase-60 self-owned-open
subjects, the Phase 51–60 checkpoint, exact deferred ownership, and the Phase 61
readiness boundary. It adds documentation/static assurance only. The
controlling contract is [Phase 60 completion/readiness audit and Phase 61
handoff](spec/phase60-completion-readiness-audit-phase61-handoff-v1.md).

Successful natural exact-head CI on the single Slice 13 commit completed Phase
60 without a status-only follow-up commit. Slice 13 did not start Phase 61.

### Phase 61 readiness boundary

The exact handed-off owner was **Phase 61 — Project IR And Semantic
Composition**. Slice 1 has now performed the required fresh architecture/source
audit and frozen the current route without changing Phase 60 production or
historical authority.

## Phase 61 route

Phase 61 and all 12 numbered Slices are completed by live Git and successful
natural exact-head CI. Both unnumbered Slice 5 prerequisites are also
completed. Phase 62 is active, its Slice 1 route-lock publication candidate is
current, and the completed Phase 61 route remains exactly 12 numbered slices.

The exact owner is **Private target-independent Project Logical IR, exact
semantic composition, and verifiable analysis boundary**.

| Slice | Owner |
| ---: | --- |
| 1 | Architecture, Mature-Source Audit, Semantic Laws, And Route Lock |
| 2 | Scope, Stages, Plan/Value/Use Occurrences, Anchors, And Construction States |
| 3 | Row/Output Model, Provided/Required Properties, Effects, And Estimate Boundary |
| 4 | Current Logical Operator Algebra And Exact Property Transfer |
| 5 | Canonical Single-Relation Construction From Existing Project Semantic Facts |
| 6 | Cross-Module Relation Composition And Acyclic Project Plan DAG |
| 7 | Aggregate/Window Evaluation Context, Policy/Effect Preservation, And No-Ambient Authority |
| 8 | Integrity, Verifier, Analysis Invalidation, Semantic Equivalence, And Optimizer/Recursion Readiness |
| 9 | Private Inspection, Query, Canonical Serialization, And Pure Boundary |
| 10 | Real Authored Multi-Module Project IR E2E |
| 11 | Differential Compatibility |
| 12 | Completion Audit And Phase 62 Handoff |

Slice 1 preserves the existing script-level `RelationIR`, consumes current
Project semantic facts without turning them into plan nodes, separates node,
output, use, input-slot, occurrence, snapshot, and future cache identities,
freezes bag semantics and the current logical stage order, and keeps exact
provided properties, required input properties, estimates, and effects in
separate domains. It adopts verifier and explicit-use lessons from mature
compiler/query sources without importing their pass frameworks, memos, physical
plans, wire formats, persistent IDs, or recursive runtime machinery. The
controlling contract is [Phase 61 Slice 1 Project IR architecture and source
audit route lock](spec/phase61-project-ir-architecture-source-audit-route-lock-v1.md).

Slice 1 adds documentation/static assurance only. It creates no Project IR
production carrier, grammar, public schema, optimizer, recursion, correlation,
nested result, new SQL lowering, backend, or Rust implementation. Successful
natural exact-head CI on its single publication commit completed Slice 1
without a status-only follow-up commit.

Slice 2 adds the first private Project IR structural model in
`src/pietto/_project/project_ir.py`: one opaque snapshot scope, four nominally
distinct local ref domains, exact existing declaration/resolution/field anchor
seams, stage-specific plan/output/use/input-slot occurrence composition, and a
constrained concrete/non-concrete relation-subject sum over all five published
construction states. It adds no operator kind, semantic-facts builder,
row/output property, cross-module plan DAG, verifier, inspection, correlation,
recursion, optimizer, SQL/public behavior, or persistent identity. The
controlling contract is [Phase 61 Slice 2 Project IR structural
model](spec/phase61-slice2-project-ir-scope-stages-occurrences-anchors-construction-states-v1.md).

Successful natural exact-head CI on the single Slice 2 publication commit
completed Slice 2 without a status-only follow-up commit.

Slice 3 adds a separate private semantic-property layer in
`src/pietto/_project/project_ir_properties.py`. It composes with exactly one
unchanged Slice 2 structural stage and adds exact ordered row/field evidence,
current scalar and BAG relation-row outputs, separate provided and consumer-side
required properties, exact current grouped-order/local-grain/static-limit and
window-policy evidence, conservative unknown effects, and an empty estimate
boundary.
It adds no operator, property transfer, semantic-facts builder, graph
construction, function-effect catalog, grain comparison/fanout, estimator,
optimizer, SQL, or public behavior. The controlling contract is [Phase 61
Slice 3 Project IR property model](spec/phase61-slice3-project-ir-row-output-properties-effects-estimate-boundary-v1.md).

Successful natural exact-head CI on the single Slice 3 publication commit
completed Slice 3 without a status-only follow-up commit.

Slice 4 adds the exact eight-kind current logical operator algebra in
`src/pietto/_project/project_ir_operators.py`, attaches each kind to an existing
Slice 2 plan-node occurrence, validates complete caller-supplied stage order,
and adds conservative exact preservation/establishment transfer proofs plus a
narrow consumer-side row-shape compatibility result. It reuses the unchanged
structural snapshot and the separate Slice 3 provided/required/effect/estimate
domains. It adds no canonical builder, ref allocation, cross-module DAG,
aggregate/window evaluation context, optimizer, verifier, estimator, JOIN,
grain comparison/fanout, SQL, or public behavior. The controlling contract is
[Phase 61 Slice 4 current operator algebra and exact property
transfer](spec/phase61-slice4-project-ir-current-logical-operator-algebra-exact-property-transfer-v1.md).

Successful natural exact-head CI on the single Slice 4 publication commit
completed Slice 4 without a status-only follow-up commit.

The unnumbered Slice 5 output-identity readiness continuation decouples exact
relation-output field occurrence identity from legacy row-lineage availability.
It keeps `ProjectModuleRowFieldIdentity` as the sole row-field identity domain,
adds complete semantic relation-output attribution to the existing module
attribution fact set, reuses existing direct/renamed lineage identity objects,
and permits grouped/aggregate/window lineage to remain deferred while their
final semantic output identities are complete. It adds no Project IR builder,
new identity domain, fake lineage hop, route slice, SQL, or public behavior. The
controlling contract is [Phase 61 Slice 5 output-identity authority readiness
continuation](spec/phase61-slice5-output-identity-authority-readiness-continuation-v1.md).

Successful natural exact-head CI on that continuation publication completed
the output-identity prerequisite without a status-only follow-up commit.

The unnumbered intra-relation dataflow readiness continuation retains exact
semantic `INPUT`, `BASE_RESULT`, and `FINAL` row checkpoints; separates
plan-local stage fields/scalars from final module-semantic field identities;
and adds exact operator-flow uses over the existing output/use/input-slot ref
domains. Logical-stage formation now proves that operator tuple order agrees
with one exact row-stream flow edge per adjacent operator pair, and preserved
property transfers consume the exact predecessor reached through that flow.
Semantic uses retain their separate provenance and source-order authority. It
adds no allocator, canonical builder, upstream Project IR, cross-relation DAG,
new module-semantic identity, route Slice, SQL, or public behavior. The
controlling contract is [Phase 61 Slice 5 intra-relation dataflow readiness
continuation](spec/phase61-slice5-intra-relation-dataflow-readiness-continuation-v1.md).

Successful natural exact-head CI on that continuation publication completed
the second prerequisite without a status-only follow-up commit.

Slice 5 adds canonical construction of one exact Project semantic relation
subject in `src/pietto/_project/project_ir_construction.py`. It consumes exact
semantic and attribution roots plus an explicit immutable snapshot allocation
state, derives the frozen current operator sequence, maps exact
`INPUT`/`BASE_RESULT`/`FINAL` checkpoints to one row output per operator,
allocates stage-local window scalars and exact final semantic exports, and
constructs every adjacent operator-flow edge, exact provided property and
transfer, unknown effect, and empty estimate boundary. Non-concrete relations
retain typed zero-allocation terminals. The returned allocation can continue
another fragment in the same scope without remapping prior refs. It builds no
upstream relation, semantic cross-relation edge, Project-wide DAG, JOIN,
optimizer, verifier framework, SQL, or public behavior. The controlling
contract is [Phase 61 Slice 5 canonical single-relation Project IR
construction](spec/phase61-slice5-canonical-single-relation-project-ir-construction-v1.md).

Successful natural exact-head CI on the single Slice 5 publication commit
completed Slice 5 without a status-only follow-up commit.

Slice 6 composes every retained relation semantic fact into same-snapshot Slice
5 fragments in exact dependency-environment/source order, then appends one
exact resolved relation-row use for every concrete derived consumer. The new
private `src/pietto/_project/project_ir_composition.py` retains exact
resolution/dependency/provenance authority, producer root and consumer Relation
Input endpoints, owner-local semantic source order, provided/required row
shapes, and `SATISFIED` compatibility. Its complete Project result preserves
all concrete and non-concrete fragments, shared-producer distinct uses,
disconnected components, and the final allocation continuation. The project
structural stage reuses fragment objects and derives acyclicity only from actual
uses; allocation order is not topological authority. Slice 6 adds no
field-level duplicate edges, JOIN/grain/fanout, recursion, optimizer, verifier
framework, inspection, SQL, or public behavior. The controlling contract is
[Phase 61 Slice 6 cross-module relation composition and acyclic Project plan
DAG](spec/phase61-slice6-cross-module-relation-composition-acyclic-project-plan-dag-v1.md).

Successful natural exact-head CI on the single Slice 6 publication commit
completed Slice 6 without a status-only follow-up commit.

Slice 7 adds a private immutable evaluation-context projection in
`src/pietto/_project/project_ir_evaluation_context.py` over the exact unchanged
Slice 6 `ProjectIRProjectPlan`. One context per concrete
`GROUP_AGGREGATE` retains its exact flow predecessor, `BASE_RESULT` row,
aggregate/grouped readiness, group-key and aggregate-result facts, let scope,
closed bindings, and effects. One context per `WINDOW_EVALUATION` separately
retains the exact stream input and semantic `BASE_RESULT` checkpoint, plus let
and named-window authority. One result context per exact window output reuses
the existing stage-local scalar, window policy, and effect objects while keeping
that stage value distinct from its final projection export.

The authorized predecessor repair makes the Slice 5 builder publish positive
`LOCAL_GRAIN_EVIDENCE` only for a non-empty exact semantic group-key tuple.
Global aggregates remain valid evaluation contexts with `group_keys=()` and no
positive local-grain property; grouped aggregates retain and preserve their
exact positive evidence. The property carrier, operator matrix, Slice 6 plan,
public/SQL behavior, and allocation remain unchanged. Slice 7 adds no evaluator,
aggregate/window algebra, frame materialization, ambient scope, correlation,
optimizer, or verifier. The controlling contract is [Phase 61 Slice 7 aggregate
and window evaluation context](spec/phase61-slice7-aggregate-window-evaluation-context-policy-effect-no-ambient-authority-v1.md).

Successful natural exact-head CI on the single Slice 7 publication commit
completed Slice 7 without a status-only follow-up commit.

Slice 8 adds an independent private verifier and detachable analysis boundary
in `src/pietto/_project/project_ir_verification.py` over the exact Slice 7
stage. It rederives snapshot/ref integrity, structural endpoints, fragment and
operator/flow composition, cross-relation resolution/provenance and row
compatibility, properties/transfers/effects, non-concrete zero-IR terminals,
evaluation contexts, and actual-use acyclicity into one typed `VERIFIED` or
`INVALID` result. Constructor validity and previous analysis are not accepted
as verification authority.

Only a verified stage produces fresh complete reverse-use, deterministic
topological-order, transitive-reachability, and semantic-equivalence candidate
analyses. Explicit topology, operator/output/property/effect/evaluation-context,
provenance, and estimate change domains derive preserved/invalidated analysis
tuples; verification always requires rerun. Equivalence assesses schema/types,
values, BAG multiplicity, null/empty behavior, cardinality, ordering,
effects/errors, evaluation count, policy, capabilities, and provenance without
merging occurrences. Unknown current evidence blocks rewrite readiness.
Ordinary cycles remain invalid and do not become recursion. Slice 8 adds no
optimizer, memo, transform, rewrite, cost/physical plan, fixpoint, inspection,
serialization, SQL, or public behavior. The controlling contract is [Phase 61
Slice 8 integrity verifier and analysis readiness](spec/phase61-slice8-integrity-verifier-analysis-invalidation-semantic-equivalence-optimizer-recursion-readiness-v1.md).

Successful natural exact-head CI on the single Slice 8 publication commit
completed Slice 8 without a status-only follow-up commit.

Slice 9 adds a verified-only private inspection and typed query owner in
`src/pietto/_project/project_ir_inspection.py` plus a portable total evaluator
and sole canonical encoder in
`src/pietto/_project/project_ir_pure_boundary.py`. Inspection retains the exact
Slice 8 bundle, complete direct Project sections, evaluation contexts, and
derived analyses without sorting, deduplication, mutation, or ref allocation.
Queries accept typed runtime refs or declaration occurrence identities and
return complete ordered buckets without a name resolver or winner.

Portable records use four nominal ref domains plus explicit semantic identity
components, preserve direct and derived section order separately, and carry no
runtime scope, object representation, or digest. The pure evaluator validates
the closed header/fragment/topology/property/effect/context/analysis document
and returns normalized rejection coordinates or the one canonical payload.
Equal bytes remain distinct from occurrence identity, semantic equivalence,
rewrite readiness, persistent identity, and content identity. Slice 9 adds no
public schema, JSON/CLI/API, deserializer, expression serializer, cache,
optimizer, recursion, SQL, or backend behavior. The controlling contract is
[Phase 61 Slice 9 private Project IR inspection](spec/phase61-slice9-private-inspection-query-canonical-serialization-pure-boundary-v1.md).

Successful natural exact-head CI on the single Slice 9 publication commit
completed Slice 9 without a status-only follow-up commit.

Slice 10 adds one private `src/pietto/_project/project_ir_pipeline.py`
orchestration boundary. It consumes the exact existing `ProjectSemanticResult`
and one explicit `ProjectIRAllocationState`, reuses the semantic and attribution
roots object-for-object, and calls the published Slice 6 Project plan, Slice 7
evaluation context, Slice 8 independent verifier and fresh analysis, and Slice
9 inspection and canonical serializer in one direction. `INVALID` stops before
analysis or observation; the immutable result retains every stage plus exact
starting/ending allocation and canonical private bytes.

Positive assurance begins with real pytest-owned multi-module authored files
through existing discovery, trust, parsing, module resolution, semantics, and
attribution. It covers a two-hop re-export route, shared producer uses, a
multi-hop consumer, the full current eight-stage relation path, exact
aggregate/window contexts, a genuine non-concrete terminal beside an
independent concrete component, and fresh-scope runtime-ref distinction with
byte-equal canonical observation. It constructs no semantic fact root or
Project IR fragment manually and changes no public, SQL, CLI, JSON, script
`RelationIR`, optimizer, or recursion behavior. The controlling contract is
[Phase 61 Slice 10 real-authored multi-module Project IR E2E](spec/phase61-slice10-real-authored-multi-module-project-ir-e2e-v1.md).

Successful natural exact-head CI on the single Slice 10 publication commit
completed Slice 10 without a status-only follow-up commit.

Slice 11 adds no production behavior. Its private
`tests/_pietto_phase61_project_ir_differential_probe.py` probe reuses the exact
Slice 10 authored Project IR entry and the established Phase 58–60 interpreter,
relocation, fresh-cache wheel, and batched differential harnesses. One reviewed
common manifest binds exact semantic relation/field identities and states,
typed Project IR coordinates, operators, direct cross edges and compatibility,
aggregate/window contexts, verification, topology/reachability,
equivalence/rewrite readiness, winner-free queries, package version, and exact
`pietto.project-ir-inspection.v1` bytes.

The matrix covers Python 3.12/3.13, four fixed hash seeds, unrelated Project and
source roots, normal/reverse file creation, opposite construction/query order,
unrelated cwd/ambient values, and an isolated installed wheel. Runtime scopes
remain distinct from portable equality, shifted starting coordinates remain
observable, and real missing-field plus cycle-blocked semantic terminals remain
stable beside concrete components. One controlled verifier corruption and six
high-value pure-boundary malformed documents retain typed normalized negative
outcomes. The probe batches each environment without sorting, persistent cache,
or nested subprocess harness. The controlling contract is [Phase 61 Slice 11
differential compatibility](spec/phase61-slice11-differential-compatibility-v1.md).

Successful natural exact-head CI on the single Slice 11 publication commit
completed Slice 11 without a status-only follow-up commit.

Slice 12 is documentation/static assurance only. It audits the 13 already
published Phase 61 units as one exact first-parent chain with unique natural
push CI and successful Python 3.12/3.13 jobs; reconciles the Slice 1 architecture
laws, complete private product inventory, real E2E/differential evidence,
public zero-delta boundary, 13/13 exit ledger, all later-owner subjects, and
`Phase61 self-owned-open = 0`; and records Phase 62 readiness without beginning
its route or implementation. The controlling contract is [Phase 61 completion
audit and Phase 62 handoff](spec/phase61-completion-audit-phase62-handoff-v1.md).

Successful natural exact-head CI on the single Slice 12 publication commit
completed Phase 61 and all 12 numbered Slices without a status-only follow-up
commit. That publication handed off **Phase 62 — Relationships/JOIN, key/FD
evidence, grain comparison, fanout/multiplicity, and multi-fact alignment** as
`NEXT / NOT IMPLEMENTED`; Phase 62 Slice 1 has now rebound that authority and
frozen its route without changing Phase-61 production behavior.

## Phase 62 route

Phase 62 is active. Slices 1–3 are completed by successful natural exact-head
CI, Slice 4 is the current publication candidate, Slices 5–16 are not started,
and the frozen route has exactly 16 numbered slices.

The exact owner is **Private occurrence-safe relationships and INNER/LEFT
logical JOIN, typed key/FD/coverage evidence, factorized intrinsic grain,
directional fanout, and multi-fact alignment analysis**.

| Slice | Exact owner |
| ---: | --- |
| 1 | Architecture, current/mature-source audit, formal BAG/NULL semantics, semantic laws, and route lock |
| 2 | Relationship declaration identity, endpoint roles, module-local resolution, and construction states |
| 3 | Exact field correspondences, ON/WHERE separation, equality/null behavior, and constraint-scope boundary |
| 4 | UNIQUE null policy, evidence trust, strict/lax row uniqueness, and candidate keys |
| 5 | Strict/lax value-FD basis, compact indexes, and targeted closure |
| 6 | Factorized intrinsic grain basis, grain dependencies, optional factors, and GLOBAL grain |
| 7 | Existing-operator key/FD/grain transfer and grain comparison |
| 8 | Referential coverage, MATCH SIMPLE/FULL, and directional match guarantees |
| 9 | Explicit relationship paths, fanout/survival/null effects, and join-shape analysis |
| 10 | Authored JOIN/traversal syntax and semantic uses |
| 11 | Project IR binary JOIN region, multi-input topology, null extension, and property transfer |
| 12 | Per-aggregate fact locality, chasm detection, and multi-fact alignment |
| 13 | Integrity/verifier, analysis invalidation, and bounded BAG/NULL semantic oracle |
| 14 | Private inspection, winner-free query, and pure canonical boundary |
| 15 | Real authored E2E, Python differential compatibility, and metamorphic JOIN assurance |
| 16 | Completion audit and Phase 63 handoff |

Slice 1 audits current Pietto relationship and authored `UNIQUE` authority,
binds current mature implementations/specifications/research, freezes one
target-independent finite-BAG and SQL-NULL reference model, separates
relationship/endpoint/traversal/path/JOIN identity, and separates value FDs,
row uniqueness/keys, grain dependencies, referential coverage, directional
match guarantees, fanout, and multi-fact alignment. Its controlling contract is
[Phase 62 relationship/JOIN/key/FD/grain/fanout/multi-fact architecture and
source-audit route lock](spec/phase62-relationship-join-keys-fd-grain-fanout-multifact-architecture-source-audit-route-lock-v1.md).

Slice 1 adds documentation/static assurance only. It changes no grammar, AST,
semantic admission, Project semantic facts, Project IR operator, SQL, CLI,
public JSON/schema, Project Explain, package/dependency/workflow, or version.
Successful natural exact-head CI on its portability-repair child completed
Slice 1 without a status-only follow-up commit.

Slice 2 adds one standalone private
`src/pietto/_project/project_relationships.py` owner. It consumes the exact
existing `ProjectSemanticResult`, declaring-module relation-resolution
environment, authored `RelationshipMetadata`, and existing
`check_relationship_metadata` semantic owner to construct complete
module/source-ordered relationship subjects. Declaration and endpoint identity
remain nominally distinct; endpoint roles are retained without cardinality or
direction inference; self/same-target relationships do not collapse; and
UNKNOWN/BLOCKED/AMBIGUOUS terminals retain exact evidence without fake
concrete facts. The controlling contract is [Phase 62 Slice 2 relationship
declaration identity and module-local resolution](spec/phase62-slice2-relationship-declaration-identity-endpoint-roles-module-local-resolution-construction-states-v1.md).

Slice 2 adds no grammar, public `SemanticModel`, Project semantic result field,
script IR/SQL, Project IR operator, condition, key/FD, grain, cardinality,
fanout, path, JOIN, multi-fact, package, workflow, or version behavior.
Successful natural exact-head CI on its single publication commit completes
Slice 2 without a status-only follow-up commit.

Slice 3 adds one optional authored relationship `on` clause over Pietto's
existing expression AST and one standalone private
`src/pietto/_project/project_relationship_conditions.py` owner. It retains
condition/conjunct/operand occurrence identities, exact local/imported Project
field and final-row-output authority, ordered standard-equality
correspondences, TRUE-only/NULL-rejecting semantics, independent condition
states, and distinct condition/constraint scopes. Unsupported, unknown, or
incompatible conditions publish no partial correspondence facts. The
controlling contract is [Phase 62 Slice 3 exact field correspondences and
scope boundaries](spec/phase62-slice3-exact-field-correspondences-on-where-equality-null-behavior-constraint-scope-boundary-v1.md).

Slice 3 adds no public relationship semantic field, key/FD, grain,
cardinality, path, fanout, authored JOIN use, Project IR JOIN, SQL, CLI/JSON,
package, workflow, or version behavior. Successful natural exact-head CI on
its single publication commit completes Slice 3 without a status-only
follow-up commit.

Slice 4 adds one standalone private
`src/pietto/_project/project_row_keys.py` owner. It consumes existing Shape
UNIQUE diagnostics, exact source-to-Shape resolution, concrete source semantic
rows, source-field attribution, and Slice-3 exact-row-output scope. Current
authored UNIQUE is a trusted `NULLS_DISTINCT` Pietto model contract; exact
all-`NON_NULL` determinants produce STRICT evidence and nullable/unknown
determinants remain LAX. Distinct Shape declarations/applications/evidence and
derived candidate facts do not collapse. The candidate frontier is the
complete non-dominated antichain built only from direct trusted evidence, with
all support occurrences retained. The controlling contract is [Phase 62 Slice
4 UNIQUE null policy, row uniqueness, and candidate
keys](spec/phase62-slice4-unique-null-policy-evidence-trust-strict-lax-row-uniqueness-candidate-keys-v1.md).

Slice 4 adds no grammar, public semantic field, FD, grain, operator key
transfer, cardinality, fanout, path, JOIN, Project IR, SQL, CLI/JSON, package,
workflow, or version behavior. Successful natural exact-head CI on its single
publication commit completes Slice 4 without a status-only follow-up commit.
The only next owner is **Phase 62 Slice 5 — Strict/Lax Value-FD Basis, Compact
Indexes, And Targeted Closure**; Slice 5 is not implemented here.

## Retained later ownership

| Phase | Owner |
| ---: | --- |
| 63 | Additional logical JOIN forms and single-match enforcement; multi-relation SQL; correlation, nested results, open plans/outer bindings, Collect/Unnest, LATERAL/decorrelation, and QUALIFY |
| 64 | Null-safe/collation/NaN/coercive equality; temporal/range/as-of relationships; advanced types, Decimal/time/interval comparison, record/container typing, and nullability |
| 65 | Aggregate algebra/state, symmetric/fanout-safe aggregates, aggregate-as-window, multi-stage aggregation/reaggregation, automatic aggregate/grain repair, and first_value(aggregate_output_alias) |
| 66 | Relationship import/export; reusable relationship/key/FD/grain declarations and libraries; reusable relation/nested semantic assets |
| 67 | Remote packages/assets, transport, registry, and trust |
| 68 | Dependency solver, canonical lockfile, and first profiling-driven Python-to-Rust kernel decision |
| 69 | Catalog constraints and statistics; optimizer memo, join-order/hypergraph search, outer-join reordering, predicate transfer/factorized/WCOJ execution, physical join strategies, and broad backend/catalog capabilities |
| 70 | Public relationship/key/FD/grain/fanout/alignment and Project-IR/nested/lineage schemas, versioned representation, and release readiness |

Recursive relations, fixpoints, iterative planning, and bounded recursive
provenance remain a dedicated later owner with no phase number assigned here.
Persistent incremental-cache identity likewise remains separate from
snapshot-local Project IR identity and has no Phase 61 implementation.
Incremental/differential Project IR, formal rewrite certification, runtime
data-quality discovery, and general constraint/chase reasoning also remain
separate dedicated later owners; the Phase 62 Slice 1 contract freezes their
exact boundaries.

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
