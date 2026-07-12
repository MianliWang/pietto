# Phase 50 Slice 10 Explain / Public Metadata / Package Integration Boundary v1

## Purpose And Slice Identity

Phase 50 Slice 10 is Explain / Public Metadata / Package Integration Boundary.
It is docs/spec/static-audit-only readiness work after completed Slices 1-9.
Slice 10 is current but incomplete. Slice 11 remains pending. Phase 50 remains
in progress.

Slice 10 implements no compiler or runtime behavior.

It defines no serializer, CLI command or option, CLI JSON v1 field, Project
JSON v2 field, Semantic Metadata Artifact v1 field, project explain output,
portability report, package-inspection report, public lineage/provenance,
package/profile/catalog loader, capability checker, package graph, diagnostic,
runtime/database, network, registry, installation, introspection, plugin, or
server behavior.

## Authority And Evidence Hierarchy

Authority is ordered as follows:

1. completed phase status locks and current implemented source/test behavior;
2. current Phase 50 plan and completed Slice 3, 7, 8, and 9 contracts;
3. Phase 45-49 private-carrier privacy contracts;
4. existing public artifact contracts and compatibility tests;
5. the historical Phase 45-60 roadmap and v0.2 register; and
6. this separately authorized readiness contract.

Historical planning-only documents do not override current implemented limited
Project JSON v2 check behavior. No external, vendor, runtime, database, server,
registry, or network evidence is used by this contract.

## Current Public Artifact Inventory

The following artifact families are distinct:

| Artifact family | Current posture | Boundary |
| --- | --- | --- |
| CLI JSON v1 | IMPLEMENTED_STABLE | single-file check and emit-sql only |
| Semantic Metadata Artifact v1 | IMPLEMENTED_STABLE | single-file explain artifact |
| Project JSON v2 check envelope | IMPLEMENTED_LIMITED | project check only |
| Future project explain | EXPLICITLY_DEFERRED | no Slice 10 command/report/schema |
| Future portability report | READINESS_CONTRACT_ONLY | no current report |
| Future package-inspection report | READINESS_CONTRACT_ONLY | no current report |

The single-file pietto explain command is the producer of Semantic Metadata
Artifact v1; it is not a seventh public schema family. PostgreSQL remains the
bounded public backend and MySQL remains the bounded private backend. Neither
existing backend fact establishes a profile, extension, connector, package, or
server fact.

## Current Private Fact Inventory

Project row schemas, fields, availability states/reasons, project semantic
catalog/model facts, origin/provenance, relation dependency graphs, row
lineage, computed-let lineage, cycle facts, and private deterministic ordering
facts remain PRIVATE_FOUNDATION carriers.

They are not Project JSON v2 fields, Semantic Metadata Artifact v1 fields, CLI
text, CLI JSON, public Python API, IR, or SQL facts. Existing Artifact v1
direct single-file field-leaf lineage remains a bounded public artifact fact;
it is not project graph, multi-file lineage, runtime lineage, or a public
projection of private carriers.

## Conceptual Vocabulary

A public projection is an artifact-specific normalized public view over an
explicitly authorized subset of private facts. A private fact is an internal
carrier fact with no automatic public exposure. A declared fact is static input
vocabulary and is not a resolved, installed, verified, runtime, or server fact.

A resolved fact identifies an actual selected package/profile/catalog result.
A runtime/server fact describes actual database, extension, connector, or
installation state. Neither is created or inferred here.

Artifact identity and artifact schema version are separate stable facts. A
cross-artifact reference is an explicit relation between named artifact
identities and versions; it is not payload embedding or implicit field
inheritance.

Unknown, absent, null, redacted, private-only, conflicting, unresolved, and
unavailable are distinct states. None authorizes fabrication.

## Exposure-route Comparison

| Route | Decision | Reason |
| --- | --- | --- |
| Route A: keep all future facts private indefinitely | rejected | does not provide a bounded future reporting handoff |
| Route B: explicit independently versioned public projections | selected | allows privacy-preserving, deterministic, reviewable, fail-closed reports |
| Route C: expose private models directly | rejected | leaks private carriers and couples public compatibility to internals |
| Route D: one universal metadata document | rejected | conflates independent artifact/version domains |
| Route E: runtime, introspected, or plugin-generated reports | rejected/out of scope | depends on execution, environment, trust, or network authority |

Route B in this Slice 10 contract is a public-projection policy. It is not a
new shared package/profile/catalog implementation model and does not alter the
separate static readiness Route B vocabulary in Slices 7-9.

## Recommended Public Projection Boundary

Route B is explicit independently versioned public projections from private facts.

An eventual projection requires a named artifact identity, an independent schema
version, authorized source facts and field meanings, deterministic ordering and
reference rules, unknown/absent/null/redaction semantics, a fail-closed policy,
a compatibility/static-audit contract, and separate implementation
authorization.

No private fact becomes public by being named as a future input. No raw private
model, dataclass, graph, private reason, or private ordering carrier may be
serialized directly.

## Artifact Separation And Ownership

CLI JSON v1, Semantic Metadata Artifact v1, Project JSON v2 check, future
project explain, future portability report, and future package-inspection report
remain separate artifact families. No universal metadata document is selected.

The existing three public artifacts stay unchanged. Future project explain,
portability, and package inspection each require an independent future artifact
identity and schema-version contract. A future transport envelope cannot merge
their identities, compatibility rules, or ownership.

Phase 55 owns semantic-package asset schema. Phase 56 owns capability/dialect/
extension profile schema and declared checking. Phase 57 owns PostgreSQL
extension signature-catalog readiness. Phase 58 owns explain, portability, and
public metadata readiness. Phase 59 owns package graph and lineage/provenance
integration.

## Single-file Explain Boundary

Existing pietto explain FILE with text or JSON format remains a bounded
single-file command. Semantic Metadata Artifact v1 remains its independent
artifact domain and remains unchanged.

Slice 10 does not make single-file explain into project explain. It does not
aggregate per-file artifacts, embed them, reference them, summarize them, or
choose among those future aggregation shapes. It does not add package,
profile, extension, portability, project graph, or runtime facts to the
single-file artifact.

## Project JSON v2 Boundary

Current Project JSON v2 remains the implemented limited project check envelope.
Its existing nine-key check shape, current check-only command/mode posture, and
existing public diagnostics boundary remain unchanged.

Project JSON v2 does not gain project explain, package inspection, portability,
public lineage/provenance, package/profile/catalog facts, private row schemas,
private reasons/states, dependency graphs, or Artifact v1 fields. A future
project explain may not be placed into the current result.check shape or a
top-level metadata field by implication.

## Semantic Metadata Artifact v1 Boundary

Semantic Metadata Artifact v1 remains independent from CLI JSON v1 and Project
JSON v2. Its success envelope includes metadata. Its failure envelope omits
metadata rather than serializing a null metadata value.

Slice 10 changes no Artifact v1 identity, schema version, field, envelope,
ordering rule, direct field-leaf lineage boundary, diagnostic reuse, or
compatibility rule. Artifact v1 does not implicitly become a project,
package-inspection, portability, graph, or provenance artifact.

## Future Project Explain Readiness

Future project explain is separately deferred and requires a future named
artifact/command contract after its own authorization. Slice 10 assigns no
future schema identifier, field name, serializer, text layout, aggregation
format, artifact embedding, reference generation, or summary generation.

Any future project explain must preserve the private carrier boundary and must
not publish partial metadata after a blocking failure. Its public facts must be
selected explicitly under Route B.

## Package Identity And Asset Exposure

Semantic package identity, exact release, schema version, asset identity, and
explicit exports are declared readiness facts. They are not the Python
distribution identity/version, project path, module identity, connector name,
repository URL, registry ownership, resolved package result, or runtime
installation state.

An eventual package-inspection projection may only describe authorized declared
facts. It may not expose raw assets, compiler-visible bindings, wildcard
visibility, dependency re-exports, registry ownership, or an unverified
publisher/trust claim.

## Package Requirement And Availability Exposure

Exact declared package requirements, declared capability/dialect/extension
requirements, and declared project availability are distinct facts. Requiring,
providing, containing a profile, and declaring project availability remain
separate.

No current package resolver, package set, solver, range selection, loader,
fetch, download, cache, installation, update, registry lookup, lockfile,
availability proof, or dependency graph exists here. Declared facts must never
be presented as resolved, installed, or runtime-proven facts.

## Capability Profile And Extension Exposure

Package/profile/extension/dialect facts are declared readiness facts, not current public or runtime facts.

Capability profile, dialect profile, overlay, extension catalog, and extension
signature facts remain static declared readiness vocabulary. They are not
current public schema/output facts, a checker result, a selected compiler
target, a connector result, an installed extension, or a server observation.

PostgreSQL public-backend and MySQL private-backend facts remain bounded current
facts only. SQLite has rejection evidence only. DuckDB, BigQuery, Snowflake,
and Trino remain NOT_EVIDENCED examples. No current fact establishes a public
profile, overlay, catalog, or extension report.

## Portability Report Readiness

The only future declared portability classifications are:

| Classification | Declared meaning |
| --- | --- |
| SUPPORTED_IDENTICALLY | declared targets share the same bounded fact/lowering |
| SUPPORTED_WITH_DIALECT_SPECIFIC_LOWERING | declared targets use explicitly different lowering |
| SUPPORTED_WITH_SEMANTIC_DIFFERENCES | declared target semantics differ |
| UNSUPPORTED | a declared target lacks the capability |
| UNKNOWN_OR_NOT_DECLARED | exact declared facts are insufficient |
| BLOCKED_BY_MISSING_CAPABILITY | a required dependent capability is absent |

Portability reporting must not imply runtime validation, fallback, degradation, or automatic translation.

A future portability report may project only complete authorized declared facts.
It may not infer server support, select a lowerer, erase a semantic difference,
use least-common-denominator fallback, or perform best-effort rewriting.

## Lineage Origin And Provenance Exposure

Phase 45-49 project row schema, origin, provenance, dependency, and lineage
carriers remain private. Phase 59 owns their later package graph and
lineage/provenance integration. Slice 10 does not consume, rename, widen,
serialize, or expose them.

An optional package source locator, revision, or supplied digest remains a
private descriptive fact by default. It is not identity, verification,
publisher authority, trust, signature, attestation, canonical bytes, fetch
authority, or network permission.

## Package Graph And Dependency Exposure

Package graphs, asset graphs, dependency traversal, dependency cycles,
conflicts, resolved package sets, and package attribution are not implemented
or publicly projected by Slice 10. Phase 59 owns later private integration.

An unresolved dependency, duplicate/conflicting declaration, missing exact
identity, missing capability, missing lowering, ambiguity, or cycle receives no
winner. It must fail closed rather than be inferred, deduplicated, or silently
resolved.

## Public Identity And Reference Rules

An eventual public artifact may reference another artifact only through explicit
stable artifact identity, schema version, and documented relationship semantics.
It must not embed a payload, inherit fields, equate independent version domains,
or rely on an implementation-object identity.

Package semantic release is an exact SemVer readiness fact. Extension/profile/
overlay release facts are exact opaque readiness identifiers. Each remains
distinct from the Python distribution version 0.1.0 and from every public
artifact schema version.

## Deterministic Ordering

Existing artifact-specific ordering remains unchanged. CLI JSON v1 diagnostics
retain compiler order. Artifact v1 arrays retain their documented single-file
source/IR/projection/first-encounter ordering. Project JSON v2 retains its
current deterministic project-input and envelope posture.

Future equality/traversal uses the owner’s canonical exact identity. Source or
declaration order may stabilize display/diagnostic order only after a
fail-closed result; it supplies no semantic winner. No future report may rely
on map, hash, filesystem, locale, or object-member order. Object-member order
is an artifact-specific decision, not a universal compatibility promise.

## Schema Versioning And Compatibility

Future artifact schemas remain independently versioned.

CLI JSON v1, Semantic Metadata Artifact v1, and Project JSON v2 remain
unchanged. Removing, renaming, changing a type, nullability, meaning, or
allowed value is a breaking change owned by the affected future artifact schema
contract. Collapsing Artifact v1 failure metadata absence into a null value is
also breaking.

Slice 10 assigns no future schema identifier, field name, serialization format,
object ordering, or additive-field policy. A future owning contract must define
its own compatibility policy and cannot silently mutate an existing artifact.

## Unknown Absent Null And Redaction Posture

Unknown means a recognized fact domain lacks sufficient exact declared
information. Absent means an artifact does not expose a fact or a fail-closed
fact is unavailable. Null is used only where an owning existing/future artifact
explicitly defines nullability. Redacted means a fact exists but an explicit
future public policy omits it.

Private-only facts remain omitted. Conflicting, unresolved, unsupported, and
unavailable facts must not become fabricated values, fake nulls, or assumed
unknowns. Existing Artifact v1 failure metadata remains absent, not null.

## Privacy And Trust Boundary

No private fact becomes public by naming it. No raw private model, row schema,
state/reason, origin/provenance, dependency graph, lineage, private ordering
metadata, resolved package/profile/catalog result, or actual server state is a
public Slice 10 fact.

Supplied digests, locators, revisions, author text, and curator descriptions
are descriptive only if later authorized. They provide no verification,
signature, attestation, publisher authority, trust policy, registry authority,
installation proof, server proof, database connection, or network permission.

## Diagnostic And Fail-closed Matrix

| Future invalid/unavailable condition | Owner/category | Required posture |
| --- | --- | --- |
| unsupported public schema version | future owning artifact | fail closed |
| missing declared fact | future package/profile/report owner | fail closed |
| duplicate, conflict, or ambiguity | future validation owner | no winner |
| private-only or redacted fact request | future projection owner | no leak/fabrication |
| unresolved dependency or cycle | Phase 59 integration owner | fail closed |
| missing lowering or unsupported context | capability/backend owner | fail closed |
| portability semantic difference | future portability report | surface difference, no rewrite |
| unavailable provenance | future provenance owner | no trust inference |
| runtime/server/install request | runtime/database boundary | out of scope |

Slice 10 assigns no diagnostic code, message, severity, ordering change, CLI
error shape, or runtime diagnostic behavior.

## CLI JSON And Artifact Separation

CLI JSON v1 is not Semantic Metadata Artifact v1. Semantic Metadata Artifact
v1 is not Project JSON v2. Project JSON v2 is not future project explain,
portability, or package inspection.

All current artifact families remain unmodified. No field, payload, version,
diagnostic, path, ordering, or privacy rule is inherited across them by
implication.

## Cross-phase Dependencies

Phase 55 owns semantic-package asset schema. Phase 56 owns capability/dialect/
extension profile schema and declared checking. Phase 57 owns PostgreSQL
extension signature-catalog readiness. Phase 58 owns explain, portability, and
public metadata readiness. Phase 59 owns package graph and lineage/provenance
integration. Phase 60 is the ecosystem completion checkpoint.

None of these ownership statements starts, completes, implements, or authorizes
another phase. Slice 10 adds no Phase 55-60 behavior.

## Bounded Phase 58 Handoff

The bounded Phase 58 handoff is Route B, separate artifact families, explicit
privacy, descriptive declared-only package/profile/extension facts, the exact
six portability classifications, deterministic ordering, independent version
domains, unknown/absent/null/redaction distinctions, and fail-closed behavior.

Phase 58 remains readiness-only, unstarted, and separately authorized.

This handoff authorizes no report implementation, public field, command,
serializer, package manager, resolver, checker, graph, diagnostic,
runtime/database, network, or release behavior.

## Explicit Deferrals And Non-goals

Deferred or excluded work includes a new CLI command or option; existing CLI
JSON v1, Artifact v1, or Project JSON v2 mutation; project explain output;
portability output; package-inspection output; package manifest parser; loader;
resolver; package/profile/catalog schema or checker; package/asset graph;
public lineage/provenance; public API; diagnostic; grammar; parser; AST;
semantic carrier; IR; SQL; backend; fixture; golden; example; dependency;
workflow; runtime/database; connection; introspection; network; registry;
installation; plugin; signing; attestation; and release behavior.

Slice 10 does not begin Slice 11 or Phases 52-60.

## Package Version And Release Boundary

Package version remains 0.1.0. Slice 10 changes no Python dependency, package
metadata, lockfile, build, workflow, fixture, golden, example, package, or
release surface. It authorizes no package version bump, tag, release, publish,
upload, signing, or attestation.

Semantic package, profile, overlay, catalog, future artifact, and report
versions remain distinct readiness facts. None is a Python distribution release.

## Separate Authorization And Stop Conditions

Any later artifact implementation, public schema, command, serializer,
projection, package/profile/catalog behavior, graph, lineage/provenance
integration, diagnostic, runtime/database behavior, or release operation
requires separate authorization.

Stop without repair or scope expansion if the exact twelve-file Slice 10
allowlist cannot remain sufficient; a protected surface changes; Route B,
artifact separation, independent versioning, private-carrier privacy,
deterministic ordering, fail-closed posture, or no-behavior boundary cannot
remain accurate; or implementation becomes necessary.
