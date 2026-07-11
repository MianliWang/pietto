# Phase 50 Slice 7 Semantic Package Model Readiness v1

## Purpose And Slice Identity

Phase 50 Slice 7 is docs/spec/static-audit-only readiness work. It locks a
bounded future semantic-package model without adding an accepted manifest,
package carrier, loader, resolver, public field, or package-manager operation.
Slices 1 through 6 are complete. Slice 7 is current but incomplete in Gate 2;
Slices 8 through 11 remain pending and separately authorized. Phase 50 remains
in progress.

Slice 7 implements no compiler or runtime behavior.

Completion requires a separately authorized Gate 3 commit, push, and exact
natural CI success. Nothing in this contract starts Slice 8, Phases 52 through
54, or Phase 55 implementation.

## Authority And Evidence Hierarchy

Authority is, in order: current grammar/source/tests for implemented facts;
completed Phase 44 through 49 audits and privacy locks; the Phase 50 plan and
finalized Slice 2 inventory; completed Slice 1 through 6 contracts; and this
approved readiness contract. The historical roadmap and Phase 29 register stay
historical and unchanged.

The trusted baseline is clean synchronized `main` at
`7c7f6976dd67ccc4628757f2d857b593f71f5e0f`, subject
`Add Phase 50 import module export readiness`, with parent
`d79c5c422cb7f54ae5e5587694e49389536419cb`. Slice 6 natural CI run
`29139545163` is documented as `CI / push`, `completed / success`, with exact
`headSha` match. Package version is `0.1.0`; no tag or exact-match tag exists at
the baseline.

## Current Package-Surface Evidence

Pietto currently has no semantic-package behavior. It has readiness vocabulary
only, separate from Python distribution packaging, project-local modules,
connector declarations, database extensions, and runtime package management.

There is no current semantic-package grammar, parser rule, AST node, project or
semantic carrier, asset inventory, export surface, dependency declaration,
package graph, capability/dialect/extension requirement, provenance/digest
field, IR, SQL, CLI command or option, Project JSON field, Semantic Metadata
Artifact field, filesystem loader, resolver, registry, fetch/install/cache
behavior, or runtime execution. Readiness vocabulary must not be described as
implemented behavior.

## Python Distribution And Semantic Package Separation

The Python distribution named `pietto`, version `0.1.0`, is not a Pietto
semantic package. Wheel/sdist metadata, Python dependencies, console entry
points, `importlib.metadata`, Python installation, and package smoke belong to
Python packaging only.

A Python wheel may contain executable Python and an entry point. A semantic
package under this contract is non-executable and is not a Python wheel, Python
package, runtime plugin, database extension, or registry artifact by
implication. Semantic-package identity and release version do not reuse the
Python distribution name or version.

## Conceptual Vocabulary

- A **semantic package** is a static declarative bundle of typed semantic and
  support assets.
- **Package identity** is a logical `(namespace, name)` tuple.
- **Package schema version** identifies the future manifest/asset schema.
- **Package release version** identifies an immutable release of one package.
- A **semantic asset** is a typed, package-local, potentially compiler-visible
  fact after separate integration authorization.
- A **support asset** is typed package content that never becomes a compiler
  binding.
- A **package export** is explicit semantic visibility for a locally owned
  semantic asset.
- A **package dependency** is an exact declarative reference to another package
  release, not authority to find or install it.
- A **requirement identity** names a future capability, dialect, or extension
  profile without providing or validating it.
- **Provenance** is descriptive origin information, not trust proof.

Package installation, registry resolution, lockfiles, and executable plugins
are package-manager/runtime concepts outside this model.

## Package-model Route Comparison

| Route | Posture | Reason |
| --- | --- | --- |
| Route A documentation-only bundle | rejected | insufficiently typed for deterministic semantic assets |
| Route B static semantic asset bundle | selected | static, declarative, reviewable, deterministic, non-executable |
| Route C source package | deferred | requires source/module parsing and integration |
| Route D hybrid source/catalog package | deferred | couples multiple unfinished schemas and module behavior |
| Route E executable plugin package | rejected | violates reproducibility and no-execution boundaries |

Route B is readiness-only. Neither Slice 7 nor Phase 55 readiness makes a
package automatically loadable.

## Recommended Semantic Package Boundary

A future semantic package is a strict package-specific manifest plus typed
semantic assets and typed support assets. It contains no arbitrary source file
or archive member, Python code, native library, hook, shell command, entry
point, lifecycle action, environment interpolation, remote include, database
connection, or executable behavior.

Package identity, schema version, release version, asset identity, exports,
dependency facts, requirements, and provenance are orthogonal. No production
package loader or package API is authorized or designed here.

## Package Identity Readiness

Conceptual identity is `(namespace, name)`, displayed as `namespace/name`.
Both components are canonical lowercase ASCII slug components and logically
case-sensitive after canonical validation; no alternate case-folded
equivalence exists.

This logical identity does not guarantee global registry uniqueness or
organization ownership. It is not a repository URL, project path, module path,
Python distribution name, connector name, source syntax, or public API.
Simple global names, repository-derived identity, project-local identity,
content digest as sole identity, and package-qualified module identity are not
selected. Reverse-DNS and organization/name alternatives remain deferred.
Phase 55 owns exact manifest keys and any validator.

## Package Version And Schema-version Readiness

Five version families remain independent:

1. Python distribution version remains `0.1.0`.
2. Semantic-package schema version is a required exact integer; the initial
   readiness candidate is `1`, with exact supported-schema matching only.
3. Semantic-package release version is a required exact SemVer string,
   immutable for one package release and compared by exact string equality
   initially. Prerelease and build metadata remain part of that string.
4. Current project `pietto.toml` schema version remains independent and
   unchanged.
5. Capability-profile and extension-catalog versions are later independent
   facts.

No SemVer parser, precedence selection, range, comparison API, update policy,
dependency solver, or lockfile behavior is added. An optional digest never
replaces package identity or release version.

## Package Asset Taxonomy

The exact conceptual initial semantic kinds are:

- `TYPE_ALIAS`
- `ENUM`
- `SHAPE`

The exact conceptual initial non-executable support kinds are:

- `DOCUMENTATION`
- `EXAMPLE`
- `STATIC_TEST_VECTOR`

These are readiness vocabulary only, not a production enum or schema
discriminator. Semantic assets have package-local identity, remain private by
default, and may become compiler-visible only after separate package
integration. Support assets never become compiler bindings or semantic
exports. No asset is currently loadable.

## Source-like Asset Readiness

Source files, local modules, module export surfaces, source connectors, tables,
queries, constraints, derives, relationship metadata, and source/package import
targets are not initial assets. They require Phase 54 module identity and
visibility readiness plus separate loader, resolution, resource, and
compatibility authority.

Current connector declarations remain compiler source facts, not package
assets, package-manager connectors, or installation instructions. Package
source locators are provenance facts only and authorize no retrieval.

## Declarative Catalog Asset Readiness

Type aliases, enums, and shapes are the only initial semantic asset candidates.
Function and aggregate signatures, capability profiles, dialect profiles,
extension profiles, and extension signature catalogs remain deferred to their
own phase owners. A package may later name exact requirement identities but
does not initially provide or embed any profile or catalog.

Relationship, grain, metric, constraint, derive, query-template, source,
module, table, query, callable, public semantic metadata, arbitrary fixture,
golden, binary, and migration assets remain excluded or deferred. Declarative
content never authorizes expression evaluation, dynamic loading, SQL execution,
or connector execution.

## Documentation And Support Asset Readiness

Documentation and examples are typed static support content. A
`STATIC_TEST_VECTOR` contains declared input and expected data only. It contains
or implies no runner, hook, command, shell script, environment access, network
access, database execution, or dynamic code execution.

Support content may be visible to future package inspection but is never a
semantic binding export. Arbitrary fixtures, goldens, binaries, archive
members, and migration scripts are not initial support assets.

## Package Public Surface And Visibility

Package semantic assets are private by default. The conceptual semantic public
surface is an explicit ordered list of locally owned semantic asset identities.
Only `TYPE_ALIAS`, `ENUM`, and `SHAPE` are initially export-eligible.
Support assets are package-visible support content, not semantic binding
exports. Imported or dependency-owned assets cannot be exported initially.

Wildcard export, export-all, implicit public-by-default behavior, export alias,
dependency re-export, imported-asset export, and transitive or registry-derived
visibility are prohibited initially. Package export remains separate from
project-local module export, Project JSON, explain/public metadata, registry
display, and runtime accessibility.

## Package Dependency Facts

Initial dependency facts contain exactly:

- target package `namespace/name`;
- exact target release version; and
- optional expected digest fact.

They are declarations with exact equality only. A future already-materialized
package set either contains the exact requested release or validation fails
closed. Duplicates or conflicts receive no semantic winner.

Version ranges, min/max or compatible-release syntax, aliases, required-asset
selectors, optional/development/peer dependencies, feature flags, activation
expressions, and transitive visibility are absent. There is no solving,
fetching, downloading, installation, caching, updating, registry lookup,
lockfile generation, or lockfile consumption. Capability, dialect, and
extension requirements are separate typed requirement facts.

## Package Graph And Cycle Posture

A future private package graph uses one exact semantic-package release as a
node and one exact declared package dependency as an edge. A separate future
asset graph uses a package-local typed asset as a node and a future asset
reference as an edge.

These graphs remain separate from project-local module, relation dependency,
row dependency/lineage, type-alias, capability-profile, extension-overlay, and
provenance graphs. Duplicate release identity, duplicate dependency, package
dependency cycle, duplicate asset identity, unknown asset kind, invalid export,
private access, missing/ambiguous reference, and cross-asset cycle all fail
closed with no semantic winner. No package or asset graph is implemented.

## Capability Requirement Readiness

A future package may declaratively name exact language/compiler,
scalar/operator, aggregate, and future window capability profile identities.
`requires`, `provides`, `contains a profile`, and `active project declares
available` are distinct facts.

Initial packages do not provide or embed capability profiles. Slice 7 and
Phase 55 readiness do not validate requirements. Phase 56 owns profile schema
and declared checking, using Phase 52 and Phase 53 facts where separately
authorized.

## Dialect And Extension Requirement Readiness

A future package may name exact dialect-profile and extension-profile
requirement identities. It does not provide or embed those profiles and does
not contain extension signature catalogs initially. Phase 56 owns
capability/dialect profile checking; Phase 57 owns PostgreSQL extension
signature catalogs; Phase 58 owns public portability/reporting.

No requirement is inferred from connector names, SQL spelling, backend
familiarity, database server state, or extension installation state. No
connection, introspection, discovery, installation, `CREATE EXTENSION`, or SQL
execution is authorized.

## Provenance Digest And Trust Boundary

Required identity facts are package identity, release version, and schema
version. Optional private descriptive provenance may include a source
repository locator, source revision, and an externally supplied package digest
with algorithm identity and digest value.

A repository locator authorizes no network fetch. A revision is not VCS
verification. Author or publisher text is not verified authority. A digest is
not package identity, is neither computed nor verified here, and cannot imply
canonical package bytes because those bytes are not defined. Asset digests,
signatures, attestations, verification, signing, registry trust, executable
code trust, and trust policy remain excluded. Phase 59 may later consume
private provenance facts; public provenance remains deferred.

## Deterministic Ordering

- Package releases order by `namespace/name`, then exact release version.
- Dependency diagnostics retain declaration/source order; traversal uses
  canonical target identity/version.
- Assets retain source order for diagnostics/display and use canonical kind,
  then local name, for equality/traversal.
- Exports retain explicit list order for diagnostics/display and set semantics
  for visibility.
- Requirements order by canonical requirement identity.
- Future diagnostics order by source location, then future category/code.

Duplicate validation occurs before canonicalization; canonical order never
silently deduplicates facts or creates semantic precedence. Public
serialization and digest-byte ordering remain deferred.

## Manifest And Representation Readiness

The selected readiness direction is a future package-specific strict TOML
manifest, separate from current project `pietto.toml`. It has a strict schema
version, strict typed keys, unknown-key rejection, no executable interpolation,
no remote include, and no code hooks.

Slice 7 does not select the filename, exact key spelling, table layout, parser,
serializer, canonical byte format, digest algorithm, or project-config
integration. Extending current `pietto.toml`, YAML, Pietto source declarations,
directory convention without a manifest, and generated-only authoring metadata
are rejected initially. JSON remains only a possible future machine form.

## Project Module And Package Integration

Current project behavior remains flat, package-free, and unchanged. Future
project-local modules use local module identity and explicit imports/exports;
semantic packages use independent `namespace/name`, release, asset, export,
dependency, and requirement facts. Neither is the other.

A future project may be supplied an already-materialized exact package set.
Validation of that set is separate from finding or installing it. Package
assets do not become project-visible bindings until a separate integration
contract exists. No package-qualified import syntax, package alias, module
bridge, project config key, filesystem loader, or resolver is selected.

## Public And Private Metadata Boundary

Current Project JSON v2 and Semantic Metadata Artifact v1 contain no package
identity, release, asset, export, dependency, requirement, provenance, digest,
or graph field. Phase 45 through 49 carriers remain private and package-neutral.

Initial future package facts remain private. Slice 7 adds no Project JSON or
public metadata field. Project explain, package inspection, portability,
registry display, public provenance, and public lineage require Slice 10,
Phase 58, or later separate authorization.

## Diagnostic And Fail-closed Matrix

| Invalid future condition | Posture |
| --- | --- |
| invalid identity/version/schema or unknown key | fail closed |
| duplicate/unknown asset or invalid export target | fail closed |
| private access, missing/ambiguous reference, or asset cycle | fail closed |
| unresolved exact package, duplicate dependency, or package cycle | fail closed |
| missing capability/dialect/extension requirement | fail closed in its owner phase |
| executable asset, plugin, or hook | schema rejection |
| registry/fetch/install/lockfile/trust failure | outside Phase 51-60 |

No failure receives a semantic winner. Slice 7 adds or reserves no existing or
new Pietto diagnostic code, message, severity, category, ordering contract, or
JSON shape.

## Package-manager Boundary

The semantic-package model may define identity, release/schema versions, typed
assets, explicit exports, exact dependency facts, requirement identities,
private provenance, and deterministic graph readiness only.

Registry search, remote fetch, download, cache, installation, updates, version
solving, ranges, lockfile generation/management, publishing, signing,
verification, attestation, and trust policy remain `OUTSIDE_51_60`. Python
plugins, entry points, hooks, lifecycle actions, arbitrary code, native
libraries, scripts, and database extension installation remain prohibited.
Phase 55 requires no package manager.

## Cross-phase Dependencies

- Phase 51 may later supply aggregate/grouped output metadata facts.
- Phase 52 owns core type-system capability foundations.
- Phase 53 remains `READINESS_CONTRACT_ONLY` and supplies no implementation.
- Phase 54 remains readiness-only and unstarted; it owns local module/import/
  export readiness.
- Phase 55 remains `READINESS_CONTRACT_ONLY`, readiness-only, unstarted, and
  separately authorized.
- Phase 56 owns capability/dialect profile schemas and checking.
- Phase 57 owns PostgreSQL extension signature-catalog readiness.
- Phase 58 owns explain/portability/public metadata.
- Phase 59 owns private package graph and lineage/provenance integration.

No dependency starts, completes, or upgrades another phase.

## Bounded Phase 55 Handoff

Phase 55 — Semantic Package Asset Schema remains
`READINESS_CONTRACT_ONLY`, readiness-only, unstarted, and separately
authorized. Its bounded handoff contains only:

1. exact semantic-package/project-module/Python-distribution vocabulary;
2. Route B static non-executable bundle;
3. conceptual lowercase `namespace/name` identity;
4. distinct integer schema version and exact SemVer release version;
5. `TYPE_ALIAS`, `ENUM`, and `SHAPE` semantic assets;
6. `DOCUMENTATION`, `EXAMPLE`, and `STATIC_TEST_VECTOR` support assets;
7. private-by-default explicit local semantic exports;
8. exact dependency facts without solving or fetching;
9. declarative capability/dialect/extension requirement identities;
10. minimal private provenance and optional digest facts;
11. deterministic ordering and fail-closed matrices;
12. package-specific strict TOML direction;
13. project/module/package integration and public/private boundaries; and
14. explicit non-executable and no-package-manager boundaries.

This handoff does not define production implementation slices or authorize
behavior.

## Explicit Deferrals And Non-goals

Deferred or excluded work includes grammar, source/package import syntax,
manifest parser, current `pietto.toml` changes, production package model,
loader, resolver, package graph, solver, registry, network, fetch, install,
cache, update, lockfile, publishing, signing, verification, attestation, trust
policy, arbitrary code, plugins, hooks, source/module/table/query/callable
assets, profile/catalog assets, extension signature assets, diagnostics, IR,
SQL, CLI, JSON, public metadata, runtime/database behavior, and Phase 56
through 59 implementation.

Slice 8 is not begun. Phases 52, 53, and 54 are not begun or modified. Phase
55 implementation is not begun. No production package API is designed.

## Package Version And Release Boundary

Package version remains `0.1.0`. Slice 7 changes no Python dependency, package
metadata, lockfile, build, workflow, fixture, golden, example, or release
surface. No package version bump, tag, release, publish, upload, signing, or
attestation is authorized. Semantic-package schema/release readiness facts do
not constitute a Pietto Python package release.

## Separate Authorization And Stop Conditions

Slice 7 is not complete in Gate 2. Gate 3 requires separate authorization and
exact natural CI success. Slices 8 through 11 remain pending. Phase 50 remains
in progress, and Phase 55 remains readiness-only and unstarted.

Stop without repair or scope expansion if the exact nine-file allowlist cannot
be preserved; a completed spec, roadmap, Phase 44 through 49 artifact,
production/public/release surface, or package version changes; Route B cannot
remain static and non-executable; a grammar, parser, AST, carrier, loader,
resolver, graph, diagnostic, public field, package-manager behavior, or Phase
55 implementation appears necessary; or focused validation fails.
