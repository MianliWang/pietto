# Phase 50 Slice 8 PostgreSQL Extension Capability Readiness v1

## Purpose And Slice Identity

Phase 50 Slice 8 is PostgreSQL Extension Capability Readiness. It is
docs/spec/static-audit-only readiness work that separates current bounded
PostgreSQL compiler behavior from future declared extension capability facts.

Slice 8 implements no compiler or runtime behavior.

Slices 1 through 7 are complete. Slice 8 is current but incomplete in Gate 2.
Slices 9 through 11 remain pending and separately authorized. Phase 50 remains
in progress. Phase 57 remains `READINESS_CONTRACT_ONLY`, readiness-only,
unstarted, and separately authorized. This contract starts no later phase and
designs no production extension API.

## Authority And Evidence Hierarchy

Current source, grammar, IR, SQL, CLI, JSON, and behavior tests govern claims
about implemented behavior. Completed phase audits and status locks govern
historical boundaries. The Phase 50 plan, Slice 2 inventory, and completed
Slice 4 and Slice 7 contracts govern capability, package, and extension
ownership. The historical roadmap and Phase 29 register remain immutable
history.

Repository-local Gate evidence records completed Slice 7 commit and CI facts
but is not a runtime test dependency. External PostgreSQL conventions are not
repository evidence. Missing or conflicting evidence fails closed.

## Current PostgreSQL Base Behavior

Pietto has bounded PostgreSQL compilation and a static `postgres.table`
connector contract, but no implemented PostgreSQL extension behavior,
extension-profile carrier, signature catalog, discovery, installation,
introspection, or extension-aware lowering.

The current bounded base posture is:

- the handwritten PostgreSQL backend emits the existing reviewed IR surface;
- the current public SQL API includes the bounded PostgreSQL emitter;
- CLI dispatch is closed to the existing PostgreSQL and private MySQL routes;
- `postgres.table(Text)` is a statically validated physical-source connector;
- the connector carries static metadata and performs no connection,
  discovery, introspection, schema inspection, or database execution;
- current scalar functions remain the closed `lower`, `trim`, `len`, and
  `matches` catalog;
- current aggregates remain the bounded count, count_distinct, sum, avg, min,
  and max families;
- current operators, type pairs, and logical types remain bounded by existing
  contracts; and
- PostgreSQL lowering proves only the reviewed compiler surface.

## Current Extension-Surface Evidence

Extension-profile vocabulary is readiness-only. Concrete PostgreSQL extension
support is explicitly deferred, and a custom extension signature-catalog
schema is not evidenced.

There is no current extension grammar, AST, semantic carrier, project
availability carrier, requirement carrier, profile, catalog, extension-defined
logical type, scalar function, aggregate, operator, cast, table function,
extension-aware lowering, installed-extension detection, server introspection,
catalog query, `CREATE EXTENSION`, installation, upgrade, execution, Project
JSON field, or public metadata field.

`postgres.table` is not extension availability. `--dialect postgres` selects a
compiler backend, not a server instance. PostgreSQL lowering is not extension
support. SQL spelling similarity is not semantic capability. A Pietto logical
type is not automatically a PostgreSQL native type, and an extension-native
type is not automatically a Pietto builtin. A package requirement is not an
installation request. A catalog entry is not a database object.

No connector name, SQL function name, operator spelling, or backend identity
may infer extension availability.

## Conceptual Vocabulary

- A PostgreSQL base profile is an immutable declared capability set for one
  bounded compiler target contract, not a server scan.
- A PostgreSQL extension is a conceptual owner of optional capabilities; this
  contract does not prove its runtime contents.
- Extension identity is the tuple
  `(postgresql_base_profile_identity, canonical_extension_name)`.
- An extension profile is a static declared overlay describing capabilities
  for one exact extension release.
- A signature catalog is a static typed declaration of extension-owned type,
  scalar, aggregate, operator, and cast readiness entries.
- An extension requirement is an exact required profile identity/version.
- Declared availability is an explicit project/compiler-input fact naming an
  already-materialized exact profile and catalog.
- Server installation state is the actual database state and remains unknown
  to Pietto.
- Extension discovery and installation are runtime/database actions outside
  the current route.
- Extension provenance is private descriptive attribution, not trust proof.

## Extension-model Route Comparison

| Route | Precision | Determinism | Security/reviewability | Decision |
| --- | --- | --- | --- | --- |
| Route A — named capability flags | coarse | high | static but insufficiently typed | rejected as insufficient |
| Route B — static typed profile/catalog | exact typed facts | high | static, declarative, reviewable, non-executable | selected |
| Route C — SQL-template macro catalog | weak semantic boundary | medium | may bypass typing | rejected |
| Route D — database-introspected model | environment dependent | low | connection/credential/runtime risk | rejected/out of scope |
| Route E — executable extension plugin | arbitrary | plugin dependent | executable-code risk | rejected/out of scope |

Route B is the selected readiness-only direction. It is strongly typed,
deterministic, layered over the PostgreSQL base profile, independent of server
inspection, and independent of installation/runtime state. It adds no arbitrary
SQL template, Python/native hook, loader, or executable plugin.

## Recommended PostgreSQL Extension Boundary

The future conceptual composition is:

`immutable PostgreSQL base profile + zero or more explicitly declared exact extension overlays -> effective declared capability set`

Composition is pure static validation over explicit declared facts. It neither
connects to a server nor proves installation. An absent, conflicting,
context-ineligible, or lowering-incomplete capability is unsupported and must
fail closed.

## Extension Identity Readiness

Conceptual identity is exactly
`(postgresql_base_profile_identity, canonical_extension_name)`. The canonical
extension-name component is lowercase ASCII, exact after validation, and
logically case-sensitive after canonical validation without alternate
case-folded equivalence.

It is not a semantic-package identity, connector identity, repository URL,
runtime-discovered server object, installation proof, source syntax, or public
API. A content digest and a catalog identity are separate facts, not extension
identity.

## Extension And Catalog Version Readiness

These facts remain separate:

| Fact | Initial readiness posture |
| --- | --- |
| PostgreSQL extension release | required exact opaque normalized string; exact equality only |
| extension-profile schema | required exact integer |
| extension-profile release | required exact opaque string |
| signature-catalog schema | required exact integer |
| signature-catalog release | required exact opaque string |
| PostgreSQL server compatibility | optional declared exact/minimum fact; no detection |
| catalog digest | optional externally supplied algorithm/value; not identity |

There is no SemVer assumption for extension releases, version range,
precedence selection, solver, update, lockfile, unversioned declaration,
server detection, digest computation, or digest verification. These versions
also remain distinct from Pietto distribution version `0.1.0`, semantic-package
version, project schema version, and capability-profile version.

## PostgreSQL Base And Extension Overlay

The base profile is immutable. An extension overlay may add only explicitly
typed capabilities. It may not replace a base capability or another extension
capability. Equivalent duplicate declarations are rejected initially rather
than deduplicated.

Conflicting signatures, type identities, native mappings, emitted spellings,
or lowering ownership fail closed. Extension textual order and dependency
order provide no semantic precedence or winner. A missing required extension
or unsupported exact version fails closed. No duplicate or conflict receives a
semantic winner, and Slice 8 implements no composition carrier or behavior.

## Signature-Catalog Entry Taxonomy

| Entry family | Initial posture | Boundary |
| --- | --- | --- |
| extension-scoped logical/native type pair | include readiness | grants no operation automatically |
| fixed typed scalar function signature | include readiness | no concrete signature |
| fixed typed aggregate signature | include readiness | no concrete signature |
| unary/binary operator typed signature | include readiness | existing parsed Pietto operator identity only |
| explicit cast signature | include readiness | explicit-only; no syntax or implementation |
| window function | defer | Phase 53 contract prerequisite |
| table/set/relation-producing function | exclude initially | relation/IR/runtime complexity |
| special syntax/new operator token | exclude | grammar/parser ownership |
| DDL/index/operator class/planner hint/configuration | exclude | storage/planner/runtime concern |
| SQL template/macro | reject | bypasses typed semantic contract |
| executable hook/lifecycle action | reject | violates non-executable boundary |

The taxonomy is documentation vocabulary only, not a production enum, schema,
catalog entry, or accepted extension signature.

## Extension Type And Native-mapping Readiness

The selected type posture is an extension-scoped opaque logical type identity
with exact extension ownership and explicit native PostgreSQL spelling.
Declared and canonical identities and nullability remain explicit where later
applicable.

An extension type is not a new Pietto builtin and is not automatically
comparable, orderable, groupable, arithmetic, aggregate-capable, castable,
IR-representable, lowerable, or public metadata. Every operation needs a
separate exact catalog entry and later implementation authority. An explicit
mapping to an existing Pietto logical type grants no adjacent capability.
Native spelling is static catalog metadata only, not DDL, storage proof,
schema inspection, or server compatibility proof.

## Scalar Function Signature Readiness

Initial scalar readiness facts are canonical semantic identity, exact
extension owner, fixed arity, ordered exact logical argument types, exact
logical result type, result nullability, scalar role, exact PostgreSQL emitted
identifier, supported context, exact profile/catalog prerequisite, and an
unsupported-context reason.

Semantic identity, emitted spelling, extension ownership, semantic-package
asset identity, and server installation state remain separate. No concrete
scalar signature is defined or accepted.

## Aggregate Signature Readiness

Initial aggregate readiness facts are canonical semantic identity, exact
extension owner, aggregate role, fixed argument shape, ordered exact logical
argument types, result logical type, result nullability, grouping eligibility,
context restrictions, exact PostgreSQL emitted identifier, exact
profile/catalog prerequisite, and an unsupported-context reason.

Aggregate-as-window eligibility and window-specific runtime/nullability
behavior remain deferred. No concrete aggregate signature is defined or
accepted.

## Operator Signature Readiness

Initial operator readiness facts are unary/binary role, exact already-parsed
Pietto operator identity, exact left and optional right logical types, exact
result logical type, exact PostgreSQL operator spelling, result nullability,
extension ownership, supported context, and an unsupported-context reason.

A catalog cannot define a new token, precedence, associativity, parser
behavior, commutator/negator behavior, index support, or operator class. No
operator is implemented.

## Cast Readiness

Initial cast readiness facts are exact source/target logical types,
explicit-only posture, result nullability, semantic safety/lossiness
classification, exact PostgreSQL emitted cast identity/spelling, extension
ownership, and supported context.

Implicit casts, PostgreSQL coercion inheritance, implicit overload
participation, cast-graph traversal, and new cast syntax are rejected or
deferred. No cast is implemented.

## Overload And Conflict Posture

Initial matching uses exact typed signatures only. Aliases during selection,
variadics, default arguments, polymorphism, generics, `anyelement`-like
signatures, implicit coercion, extension-native ranking, best-match selection,
and textual-order selection are unsupported.

Missing, duplicate, or ambiguous signature; base/extension or extension/
extension collision; unsupported type/context/version; and conflicting result
type, nullability, or emitted spelling all fail closed. No ambiguity or
conflict receives a winner. Slice 8 adds or reserves no diagnostic code.

## Extension Requirement And Availability

These five facts are independent:

1. a semantic package requires an exact extension-profile identity/version;
2. project/compiler input explicitly declares an exact profile and catalog
   available;
3. a signature catalog describes exact typed capabilities;
4. the PostgreSQL backend has separately approved lowering for the exact
   signature; and
5. actual PostgreSQL server installation state is unknown to Pietto.

Future validation may trust only explicit declared facts. Missing requirement,
conflicting declaration, profile/catalog mismatch, missing exact signature,
missing lowering, or unsupported exact version fails closed. Availability is
never inferred from `postgres.table`, backend selection, emitted SQL, an
extension name, database convention, or an installed database.

## Extension Dependency Readiness

Initial readiness may record an exact dependent extension identity, exact
dependent extension release, exact PostgreSQL base-profile requirement, and an
optional declared exact/minimum server-compatibility fact.

Only direct exact requirements are authored initially. A future already-
materialized declared set is validated with deterministic transitive traversal.
Missing exact dependencies and cycles fail closed. Version ranges, optional/
development/peer dependencies, features, activation conditions, solving,
installation, version selection, and automatic transitive visibility are
excluded. Extension dependencies remain distinct from semantic-package
dependencies.

## Example Extension-family Matrix

| Example | Conceptual matrix use | Status/boundary |
| --- | --- | --- |
| PostGIS | type/function/operator complexity | `NOT_EVIDENCED`; no geometry/geography builtin or signature |
| pgvector | extension type/operator complexity | `NOT_EVIDENCED`; no vector builtin, operator, or index |
| pg_trgm | extension-owned operation over current Text identity | `NOT_EVIDENCED`; no function/operator/configuration |
| TimescaleDB | illustrates why DDL/relation/configuration/runtime is excluded | `NOT_EVIDENCED`; no time_bucket, hypertable, or continuous aggregate |

These names are examples only. The matrix claims neither their actual contents
nor Pietto support. Slice 8 performs no web research, database research, or
extension execution.

## Deterministic Ordering

Extension declarations, catalog entries, dependencies, and requirements retain
source/declaration order for diagnostics and display. Canonical exact identity,
entry-family, and signature keys govern equality and traversal. Argument order
is semantic. Effective capability composition uses canonical capability-key
order. Duplicate/conflicting facts fail before composition. Textual order has
no semantic precedence.

## Package Profile And Catalog Integration

Ownership remains exact:

- Slice 8 owns the extension readiness contract only.
- Phase 55 owns the generic semantic-package asset schema; its initial six
  asset kinds remain unchanged and receive no profile/catalog asset here.
- Phase 56 owns capability/dialect/extension profile schemas and declared
  checking.
- Phase 57 owns PostgreSQL extension signature-catalog readiness.
- Phase 58 owns explain, portability, compatibility, and public reporting.
- Phase 59 owns package graph, attribution, provenance, and lineage
  integration.

Slice 8 locks only future exact package requirement identity and catalog
attribution boundaries. It defines no Phase 55 asset, Phase 56 schema, Phase 57
carrier, public report, or package-graph integration.

## Provenance Digest And Trust Boundary

Future private descriptive facts may include extension identity/release;
profile and catalog identities, schema versions, and release versions; source
repository locator; source revision; curator/generation-description text;
optional externally supplied digest algorithm/value; and a descriptive origin
such as manually curated, generated from upstream documentation, or generated
from a PostgreSQL catalog.

These facts authorize or prove no network access, repository fetch, server
introspection, catalog generation, digest computation/verification, publisher
authority, signing, attestation, registry trust, or trust policy. Slice 8
implements no provenance carrier or trust behavior.

## Public And Private Metadata Boundary

Declared extension availability, requirements, profile/catalog identities,
catalog entries, signature ownership, effective capability composition,
conflicts, dependencies, and provenance remain private future facts. Slice 8
adds no Project JSON v2, Semantic Metadata Artifact v1, single-file explain,
project check, CLI JSON, public metadata, public lineage, or public API field.

Project explain, portability reports, package inspection, missing-capability
diagnostics, and extension compatibility reporting require Slice 10, Phase 58,
or later separate authorization.

## Diagnostic And Fail-closed Matrix

| Future invalid condition | Validation owner/category | Posture |
| --- | --- | --- |
| invalid identity/profile/catalog schema | Phase 56/57 schema validation | fail closed; no code selected |
| missing/duplicate/conflicting declaration | project/capability validation | fail closed |
| profile/catalog mismatch | profile/catalog validation | fail closed |
| duplicate/conflicting/ambiguous signature | semantic signature validation | fail closed; no winner |
| unsupported logical/native type | type/catalog validation | fail closed |
| missing lowering/unsupported context | backend validation | fail closed |
| dependency cycle/version mismatch | catalog/project validation | fail closed |
| server installation unknown | runtime/install concern | never inferred |
| discovery/install request | prohibited runtime/database concern | out of scope |

Slice 8 adds no diagnostic code, message, severity, category, ordering
contract, or JSON shape.

## Cross-phase Dependencies

- Phase 51 is an optional consumer integration for aggregate project outputs,
  not a core catalog prerequisite.
- Phase 52 is prerequisite to exact logical/type-pair capability facts and
  remains unstarted.
- Phase 53 is relevant only if window entries are later reconsidered; window
  entries remain excluded and Phase 53 remains readiness-only/unstarted.
- Phase 54 is optional local-module integration and remains unstarted.
- Phase 55 is a package-integration dependency only if profiles/catalogs later
  become assets; it remains readiness-only/unstarted.
- Phase 56 is prerequisite and owner for profile schema/declared checking; it
  remains unstarted.
- Phase 57 owns catalog readiness and remains readiness-only/unstarted.
- Phase 58 is prerequisite to public exposure.
- Phase 59 owns future package/provenance integration.
- Phase 60 is a consistency checkpoint, not behavior authority.

No dependency starts, completes, or authorizes another phase.

## Bounded Phase 57 Handoff

Phase 57 — PostgreSQL Extension Signature-Catalog Readiness remains
`READINESS_CONTRACT_ONLY`, readiness-only, unstarted, separately authorized.

Its bounded handoff contains only exact base/extension vocabulary; Route B;
identity/version posture; immutable-base/additive-overlay contract; initial
taxonomy; opaque type readiness; exact scalar/aggregate/operator/cast facts;
exact matching/conflict policy; requirement/availability/catalog/lowering/
server-state separation; exact direct dependencies; deterministic ordering;
private provenance/optional supplied digest readiness; ownership boundaries;
and no-introspection/install/runtime matrices.

It excludes production profile/catalog carriers, concrete signatures,
generated ingestion, grammar, parser, AST, semantic/type/operator/aggregate
acceptance changes, IR, SQL lowering, CLI, JSON, public metadata, diagnostics,
connections, introspection, discovery, `CREATE EXTENSION`, installation,
registry, network, runtime/database behavior, and Phase 56/58/59
implementation. Slice 8 does not finalize Phase 57 implementation slices.

## Explicit Deferrals And Non-goals

Deferred or excluded are production capability/profile/catalog schemas and
carriers; concrete extension types/functions/aggregates/operators/casts;
window/table/relation/set-returning functions; special syntax; new tokens,
precedence, or associativity; variadics/defaults/polymorphism/generics;
implicit coercion/casts; SQL templates/macros; DDL, indexes/operator classes,
planner hints, hypertable/configuration actions; public metadata/reporting;
package/profile/catalog assets; package graph/provenance integration;
connections; server/database/schema introspection; discovery;
`CREATE EXTENSION`; install/upgrade/enable/disable; registry/fetch/cache/solver;
SQL execution; runtime plugins/hooks; signing; attestation; and trust policy.

Slice 8 adds no grammar, generated artifact, parser, AST, source, semantic
behavior, type behavior, aggregate behavior, operator behavior, project
behavior, IR, SQL, CLI, JSON, diagnostic, fixture, golden, example, dependency,
workflow, package metadata, version, release, runtime, or database behavior. It
does not begin Slice 9 or Phases 52 through 57.

## Package Version And Release Boundary

Package version remains `0.1.0`. Slice 8 changes no Python dependency, package
metadata, lockfile, build, workflow, fixture, golden, example, or release
surface. No package version bump, tag, release, publish, upload, signing, or
attestation is authorized. Gate 2 does not stage, commit, push, trigger, rerun,
watch, or cancel CI.

## Separate Authorization And Stop Conditions

Slice 8 is current but incomplete in Gate 2. Completion requires a separately
authorized Gate 3 commit, push, and exact natural CI success. Slices 9 through
11 remain pending. Phase 50 remains in progress. Phases 52 through 57 remain
unstarted, and Phase 57 remains readiness-only.

Stop without repair or scope expansion if the exact ten-file allowlist cannot
hold; a roadmap/completed spec/Phase 44–49/production/public/release surface
changes; Route B cannot remain static, typed, deterministic, and
non-executable; the base cannot remain immutable; an overlay must replace a
capability; a concrete signature, production carrier/schema, diagnostic,
public field, connection, introspection, install action, runtime behavior, or
Phase 57 implementation appears necessary; or focused validation fails.
