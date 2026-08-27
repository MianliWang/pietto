# Roadmap

Pietto is a readable, typed, modular SQL authoring compiler. Future work must
be selected by current user/product need, not by an inherited phase number.
Every substantive slice begins by identifying its authority roots, current
invariants, compatibility boundary, and the smallest behavior that is actually
needed.

The active product direction is a private typed local-package graph integrating
existing package, module, requirement, capability, catalog, provenance, and
lineage authorities. Project Explain v1 remains unchanged. Pietto remains
compiler-only: no package or catalog registry, dependency solver, remote
loading, database execution, runtime evaluation, installation discovery, or
implicit project discovery is authorized. Future work must preserve established
identity, complete collection, provenance, ordering, trust, and diagnostic
boundaries unless a new explicit product decision changes them.

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

Phase 59 is completed, all 12 Slices are completed, the Validation/Test
Performance Optimization Interlude is active with Slice 1 as its current
publication candidate, and Phase 60 is blocked / not activated. The published
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
status-only follow-up commit, activated the performance interlude as the next
owner, and left Phase 60 not activated.

## Validation/Test Performance Optimization Interlude

This mandatory owner is `ACTIVE` after Phase 59 completion:

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
| 4 | Validator Static-Analysis Stage Optimization |
| 5 | Current-Suite Isolation Audit And Xdist Decision |
| 6 | Completion Benchmark And Phase 60 Readiness Assurance |

Slice 1 measures the current serial suite and validator stages, attributes the
dominant cost to repeated cross-process differential probes, records historical
repository-reader duplication, and freezes this six-Slice route without
implementing an optimization. A complete general-purpose repository test index
is only partially supported: immutable shared acquisition is justified for the
measured duplicate-reader slice, but repository scans are not the dominant wall
time. The controlling evidence and success metrics are
[Interlude Slice 1 baseline profiling and route lock](spec/validation-performance-interlude-slice1-baseline-profiling-cost-attribution-route-lock-v1.md).

Slice 2 first decomposes runtime inside the cross-process differential probes,
then optimizes only measured internal cost while preserving every seed,
interpreter, relocation, installed-wheel, failure, order, multiplicity, and
byte-exact witness. Slice 3 owns the smallest immutable shared repository-reader
acquisition supported by the measured duplication; it does not presuppose a
monolithic index. Slice 4 owns the separately measured production/test Pyright
stage cost. Slice 5 must audit the current suite's mutable state, filesystem
isolation, caches, cwd/environment changes, build paths, and ordering before any
controlled xdist comparison or CI decision. Slice 6 owns same-method completion
measurement and readiness assurance; it does not activate Phase 60.

Python 3.12/3.13, generated, golden, package-smoke, reader-closure, and failure
semantics remain mandatory. The Python suite is not rewritten in Rust merely
for speed, and the first Rust-kernel decision remains later-owned. Interlude
Slice 1 changes no production or validation semantics. Natural CI and the
authoritative local validator remain serial through Slice 1; installed xdist
tooling grants no current-suite safety or performance authority.

Phase 60 is `BLOCKED / NOT ACTIVATED` until this interlude is completed by its
own later live authority.

## Retained later ownership

| Phase | Owner |
| ---: | --- |
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
