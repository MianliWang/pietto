# Phase 50 Slice 6 Import / Module / Export Readiness v1

## Purpose And Slice Identity

Phase 50 Slice 6 is Import / Module / Export Readiness. It is
docs/spec/static-audit-only readiness work. It records an evidence-backed
future local-module direction without changing any accepted Pietto program,
project behavior, compiler output, or public contract.

Slice 6 implements no compiler or runtime behavior.

Slices 1 through 5 are complete. Slice 6 is current but incomplete in Gate 2.
Slices 7 through 11 remain pending and separately authorized. Phase 50 remains
in progress. Slice 6 completion requires a separately authorized Gate 3
commit, push, and exact natural CI success.

Phase 54 remains readiness-only and unstarted. Phase 55 remains unstarted.

## Authority And Evidence Hierarchy

Current source, grammar, AST, project source-selection and project-semantic
tests govern implemented behavior. Completed Phase 44-49 audits govern the
project path, catalog, resolution, graph, schema, dependency, lineage, and
privacy boundaries. The Phase 50 plan and Slice 2 inventory govern current
ownership and the finalized Phase 51-60 planning route.

The historical roadmap and Phase 29 register remain immutable history.
Repository-local Gate evidence records completed CI but is not a test runtime
dependency. Missing or conflicting evidence fails closed. A readiness decision
does not create implementation authorization.

This contract depends on no parent Git object, temporary evidence file,
network state, GitHub query, import execution, or dynamic code execution.

## Current Multi-file Project Model

The current implemented project path is:

1. establish one explicit project root;
2. load and validate pietto.toml schema version 1;
3. select configured project-relative .pietto inputs deterministically;
4. retain selected inputs in normalized project-relative path order;
5. read and parse each selected input;
6. retain ProjectParsedInput path and Script facts;
7. collect supported top-level definitions into one ProjectSemanticCatalog;
8. detect same-namespace duplicates;
9. resolve supported type, source-shape, and relation references;
10. build private relation graph, row schema/state, let, dependency, and
    lineage facts;
11. report project semantic diagnostics through project check; and
12. stop before project IR, project SQL, project emit-sql, and project explain.

All supported top-level definitions are collected before supported project
references are resolved. Supported cross-file references require no import.
Files are semantically transparent after discovery at currently supported
reference sites. Forward references are permitted by collect-before-resolve
behavior.

File and declaration order controls deterministic collection, first duplicate
ownership, and diagnostic order. It does not create file-local visibility.

## Current Namespace And Visibility Model

Current project semantics uses exactly three flat project-global namespaces:

| Namespace | Current members |
| --- | --- |
| TYPE | type aliases, enums, shapes |
| RELATION | sources, tables, queries |
| CALLABLE | constraints, derives |

Names must be unique project-wide within one namespace. Later same-namespace
duplicates fail closed. The same spelling may occur once in each different
namespace.

Current project symbols retain project-relative source paths, but project
references are not file-path-qualified. Current files have no module
visibility. Pietto currently has no module identity, module namespace, import
binding, export surface, public/private declaration visibility, re-export,
module graph, or module-cycle behavior.

Current project-global visibility is not an export contract, semantic-package
surface, public-metadata promise, or runtime-public contract.

The exact current posture is:

One deterministic selected project compile unit, three flat project-global
namespaces, file-transparent supported resolution, no import/export/module
visibility, and fail-closed same-namespace duplicates.

## Current Declaration-kind Matrix

| Declaration | Current namespace | Current cross-file visibility | Dependency / cycle posture | Current public/private posture | Initial import | Initial export |
| --- | --- | --- | --- | --- | --- | --- |
| type alias | TYPE | project-wide TypeExpr resolution | base-type resolution; project alias-cycle behavior not implemented | private project symbol/fact | eligible | eligible |
| enum | TYPE | project-wide type identity | no project enum-member graph | private project symbol/fact | eligible | eligible |
| shape | TYPE | project-wide field/source-shape resolution | field type dependencies; field cycles remain separate | private project symbol/schema | eligible | eligible |
| constraint | CALLABLE | catalog and signature type facts only | callable body/reference graph not evidenced | private project symbol | deferred | deferred |
| derive | CALLABLE | catalog and signature type facts only | callable body/reference graph not evidenced | private project symbol | deferred | deferred |
| source | RELATION | project-wide source-shape and relation resolution | shape dependency; not a relation-cycle node | private project symbol/schema | eligible | eligible |
| table | RELATION | project-wide relation resolution | table/query relation graph and PIE-S2302 | private project schema/graph/lineage | eligible | eligible |
| query | RELATION | project-wide relation resolution | table/query relation graph and PIE-S2302 | private project schema/graph/lineage | eligible | eligible |
| relationship metadata | separate metadata, not ProjectSymbol | no project module semantics | separate metadata rules | not project module/public output | excluded | excluded |

Fields, checks, unique/index items, let bindings, select items, clauses,
expressions, and headers are not top-level project declarations.

## Import / Export / Module Evidence Inventory

| Evidence | Classification | Current finding |
| --- | --- | --- |
| Pietto grammar | actual compiler syntax | no import, export, module, visibility, re-export, include, or use rule/token |
| AST | actual compiler model | no import/module/export node |
| project model | actual project behavior | flat TYPE, RELATION, CALLABLE catalog; no module carrier |
| Phase 44 | implemented project input behavior | deterministic file discovery/path identity, not module loading |
| Phase 45 | implemented limited semantics | flat implicit project package stepping stone; module behavior deferred |
| Phase 46 | implemented limited graph behavior | relation dependencies/cycles only; module cycles undefined |
| Phase 47-49 | private foundation | row facts, not module/export facts |
| Slice 2 inventory | current readiness authority | module identity/import/export visibility explicitly deferred to Phase 54 |
| Slice 1 package vocabulary | readiness-only | semantic packages are static and non-executable, distinct from local modules |

Python imports are implementation-language imports, not Pietto language
imports. Relation `from` is relation lookup and dependency, not a module
import. A source connector declaration is a static source
declaration, not a module import, semantic-package import, or runtime connector
load. Python distribution/package terminology and generic data-export wording
do not prove Pietto module behavior.

## Conceptual Vocabulary

- Project: the explicit root/config/selected-input compile unit.
- Project root: the filesystem root established before selection.
- Project input: one deterministically selected project-relative .pietto file.
- Source file: the physical readable file represented by a project input.
- Canonical file identity: the current normalized ProjectInput path plus
  current physical duplicate checks.
- Module: a future compiler-local visibility unit.
- Module identity: a future private identity for that unit.
- Declaration: one current top-level semantic Definition category.
- Local declaration: a declaration owned by one future module.
- Exported declaration: a future local declaration explicitly visible to an
  importing module.
- Private declaration: a future local declaration absent from its explicit
  export surface.
- Import: a future static compiler binding request.
- Imported binding: one local binding created from one explicitly exported
  declaration.
- Import alias: an optional local spelling for one imported binding.
- Qualified reference: a future declaration/module/package lookup form,
  distinct from field qualification.
- Module namespace: a future local-declaration and imported-binding
  environment.
- Project namespace: the current flat TYPE, RELATION, and CALLABLE maps.
- Re-export: making an imported binding visible through another module.
- Semantic package: a static declarative bundle of semantic assets, owned by
  Slice 7 and Phase 55.
- Runtime plugin: executable dynamically loaded code, excluded from this route.

This vocabulary creates no production enum, Python API, manifest field, JSON
schema, config key, or grammar token.

## Module-model Route Comparison

| Route | Compatibility | Encapsulation | Determinism | Package coupling | Complexity | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| A: preserve global declarations only | highest | weak | current stable | weak | low | not the final direction |
| B: mandatory file-as-module | breaking now | strong | strong | moderate | medium-high | future explicit-mode semantic shape |
| C: logical modules independent of files | low without new identity | strong | requires manifest/declaration | high | very high | deferred |
| D: hybrid compatibility | high | progressive | strong in explicit mode | bounded | medium | selected readiness direction |

Route D is the readiness direction only. Current flat project-global behavior
remains unchanged.

## Recommended Module Boundary

No current file becomes a module merely because Slice 6 documents Route D.
Legacy/current projects continue using existing flat project-global behavior.

A future separately activated explicit-module mode may use one selected
.pietto file as one local module and follow Route B file-as-module semantics
inside that mode. Slice 6 selects no module declaration, project schema
version, compatibility flag, implicit root module, automatic import, migration
rewrite, or compatibility bridge.

No logical module spans multiple files initially. No directory automatically
becomes a module. No manifest is introduced, and no package identity is
inferred from local paths.

## Module Identity And Canonical Path Readiness

The private documentation-only identity candidate is the exact current
normalized project-relative selected input path, including the .pietto suffix.

This candidate:

- is not a source-language module name;
- is not a public Project JSON module identity;
- is not a semantic-package identity;
- is not a package-qualified name;
- preserves forward-slash project-relative paths;
- preserves current root containment and invalid-path rejection;
- preserves symlink/root-escape protection;
- preserves duplicate physical-file handling;
- does not strip .pietto; and
- does not infer identity from declaration names.

Path-without-extension, explicit logical, declaration-derived,
manifest-assigned, and package-qualified identities remain deferred. Case
folding, Unicode normalization, cross-platform case-collision rules, and
additional filesystem normalization also remain deferred.

Slice 6 changes no discovery, path, symlink, or filesystem behavior.

## Import Binding Readiness

The initial future explicit-mode direction is:

- explicit named imports only;
- optional local alias;
- one explicitly exported declaration creates one local imported binding;
- every imported binding must be unique;
- textual import ordering does not change meaning;
- no transitive visibility;
- no implicit re-export;
- no automatic import of legacy project-global declarations; and
- no silent duplicate-import deduplication.

Initial eligible targets are type aliases, enums, shapes, sources, tables, and
queries. Constraints and derives are deferred. Relationship metadata is
excluded.

Wildcard/star, namespace/module-object, side-effect, type-only, relation-only,
package-qualified, implicit, transitive, and module-qualified forms remain
rejected or deferred. No grammar spelling is reserved and no resolver is
implemented.

## Export And Visibility Readiness

In a future explicit-module mode, declarations are private by default.
Visibility is granted through an explicit export list. Initially only local
declarations may be exported.

Type aliases, enums, shapes, sources, tables, and queries are initially
export-eligible. Constraints and derives remain deferred. Relationship
metadata and imported bindings are excluded.

An export is a compiler visibility fact only. It does not imply Project JSON
serialization, semantic-package publication, public metadata, or runtime
access.

Implicit export-all, public-by-default, wildcard exports, export aliases,
re-exports, export of imported bindings, and transitive export visibility are
not initially allowed. Slice 6 adds no production visibility carrier or
enforcement.

## Reference And Qualification Readiness

Current reference behavior remains unchanged. A future local declaration and
future explicit imported binding are distinct lookup sources. A local import
alias creates a local unqualified binding. Collisions are validated before
lookup.

No local declaration shadows an imported binding. No imported binding shadows
a local declaration. No ambiguous reference receives a winner.

Declaration/module qualification, relation qualification, field
qualification, immediate-upstream field qualification, package qualification,
original-source provenance, and lineage paths remain distinct.

Current upstream.field or other dotted field syntax, original-source paths,
and lineage paths are not module selectors and are not evidence of module
qualification. Module-qualified, file-path-qualified, and package-qualified
source references remain deferred.

Future resolved facts may distinguish declared spelling, resolved project
symbol, module identity, optional package identity, and provenance. Slice 6
creates no production fact.

## Module Graph And Deterministic Ordering

The future static local module graph is documentation-only:

- candidate node: one canonical local module identity;
- initial candidate edge: one explicit named import.

It remains separate from relation dependency graphs, row dependency graphs,
row lineage, type-alias cycles, package dependency graphs, and backend
dependencies.

Deterministic readiness order is:

1. canonical project input order;
2. declaration source order per input;
3. import source order per future module;
4. canonical module order for traversal;
5. deterministic target order for equal-origin edges; and
6. deterministic diagnostic order.

Imported binding order never changes semantics. Slice 6 adds no graph carrier.

## Cycle Taxonomy And Fail-closed Posture

| Cycle kind | Current behavior | Future readiness posture |
| --- | --- | --- |
| module import | none | fail closed initially |
| re-export | none; feature deferred | fail closed if later introduced |
| project type alias | no project expansion/cycle behavior | separate future type policy |
| single-file type alias | existing type-cycle behavior | unchanged and separate |
| relation dependency | existing PIE-S2302 | unchanged and separate |
| row/field expression | existing/deferred separate behavior | unchanged and separate |
| package dependency | none | Phase 55/59 separate policy |

There is no initial type-only module-cycle exception. A future implementation
may evaluate deterministic strongly connected components, but Slice 6 selects
no production algorithm or API. PIE-S2302 is not reused for module cycles.
Slice 6 adds or reserves no diagnostic code.

## Duplicate Ambiguity And Shadowing

The following future conditions fail closed:

- duplicate module identity;
- duplicate local declaration within one namespace;
- duplicate export;
- duplicate imported binding;
- local/import collision;
- two imports exposing one local name;
- alias collision;
- ambiguous unqualified reference;
- private-symbol access;
- missing export; and
- unresolved module.

There is no semantic winner after a collision. Deterministic ordering exists
for evidence and diagnostics, not winner selection. Local declarations and
imported bindings do not shadow each other.

Current same-namespace PIE-S2001 behavior is evidence for fail-closed project
duplicates but does not automatically assign a future module diagnostic code.

## Legacy Project Compatibility

Mandatory explicit modules would break current cross-file type, shape, source,
table, and query references because current projects require no imports.
Current projects may also use collect-before-resolve forward references and
file-transparent global names.

Route D preserves current flat behavior. A future explicit-module mode must be
additive and separately activated. Slice 6 selects no compatibility mode flag,
project schema version, implicit root module, automated migration, automatic
legacy import, or source rewrite.

Any later compatibility bridge must be separately designed, deterministic,
reviewable, and authorized.

## Local Module And Semantic Package Boundary

Slice 6 and Phase 54 local-module concerns are project-local file/module
identity, imports, exports, visibility, imported bindings, local graph,
deterministic resolution, collisions, cycles, and flat-project compatibility.

Slice 7 and Phase 55 semantic-package concerns are package identity, package
version, asset kinds/schema, declared package dependencies, capability
requirements, dialect/extension attribution, provenance, and distribution
boundaries.

Registry access, remote fetch, installation, cache management, dependency
solving, lockfiles, executable package code, Python plugins, hooks, lifecycle
actions, and network behavior remain excluded.

A future local import may gain a package-qualified target only after package
identity and asset resolution are separately defined. Slice 6 defines no
package target grammar or package resolver.

## Public And Private Metadata Boundary

Project JSON v2 currently exposes project root/config facts, input paths and
read/parse statuses, diagnostics, cli_errors, and read/parse counters. It
exposes no project catalog, module identity, import binding, export surface,
visibility decision, module graph, cycle fact, package attribution, row schema,
dependency, or lineage fact.

Future module facts remain private initially. Phase 58 is the public-exposure
prerequisite for project explain, portability, or public metadata decisions.
Phase 59 owns later private package graph/lineage/provenance integration.

Slice 6 adds no Project JSON field, Semantic Metadata Artifact field, CLI
output, public metadata, public module identity, or public API.

## Diagnostic And Fail-closed Matrix

| Future condition | Readiness posture |
| --- | --- |
| unresolved module | fail closed; no code reserved |
| invalid/root-escaping module path | fail closed; preserve current path boundary |
| duplicate module identity | fail closed; no winner |
| module import/re-export cycle | fail closed; separate from PIE-S2302 |
| unknown export/private symbol access | fail closed |
| duplicate imported binding/local collision | fail closed; no shadowing |
| ambiguous reference | fail closed; no winner |
| unsupported declaration export | fail closed |
| package import without package contract | fail closed/deferred |
| wildcard/re-export form | rejected or deferred |
| future case/Unicode collision | deferred pending portability policy |

Existing PIE-S2001, PIE-S2002, PIE-S2301, and PIE-S2302 categories are not
automatically reused. Slice 6 adds no diagnostic and changes no diagnostic
wording, severity, shape, or ordering.

## Cross-phase Dependencies

- Phase 51 is unrelated to core module identity; its future relation output
  facts are optional later integration.
- Phase 52 is unrelated to local binding behavior and remains unstarted.
- Phase 53 is unrelated to local module resolution, remains unstarted, and
  remains `READINESS_CONTRACT_ONLY`.
- Phase 54 receives this bounded readiness handoff and remains unstarted.
- Phase 55 owns semantic package assets and remains unstarted.
- Phase 56 capability profiles are optional later integration.
- Phase 57 extension catalogs are unrelated to local resolution.
- Phase 58 is prerequisite to any public module/explain/metadata contract.
- Phase 59 owns future private package graph and lineage integration.
- Phase 60 may audit consistency but starts no implementation.

No dependency starts or authorizes another phase.

## Bounded Phase 54 Handoff

Phase 54 — Import / Module / Export Readiness remains readiness-only and
unstarted. It is separately authorized.

Its bounded handoff contains only:

1. exact project/module/package vocabulary;
2. Route D compatibility direction;
3. private file-as-module identity candidate;
4. explicit named imports plus optional aliases;
5. explicit private-by-default export lists;
6. exact declaration eligibility;
7. deterministic graph and ordering contract;
8. fail-closed cycle, collision, ambiguity, and privacy matrices;
9. current flat-project compatibility boundary;
10. private-first metadata posture; and
11. local-module versus semantic-package separation.

The handoff excludes grammar, exact source syntax, generated parser changes,
AST, production carriers, resolver behavior, discovery/loading changes,
ProjectSemanticModel behavior, diagnostics/codes, CLI, JSON, public metadata,
package manifest/resolution/registry/installation, IR, SQL, runtime, and
database behavior.

Slice 6 does not finalize Phase 54 implementation slices and does not upgrade
Phase 54 into an implementation phase.

## Explicit Deferrals And Non-goals

Explicitly deferred are exact syntax, activation/migration mechanism,
path-without-extension identity, logical/manifest/package identity, case and
Unicode normalization, module-qualified references, namespace/wildcard/
side-effect/type-only/relation-only/package imports, import precedence,
transitive visibility, export aliases, re-exports, wildcard exports, callable
imports/exports, relationship metadata imports/exports, production carriers,
diagnostics, and public module metadata.

Slice 6 adds no grammar, generated parser, AST, project discovery/loading,
namespace behavior, semantic resolution, module graph behavior, visibility
behavior, filesystem behavior, ProjectSemanticModel fact, private production
carrier, diagnostic, IR, SQL, CLI, JSON, public metadata, package manifest,
package identity, resolver, registry, installation, runtime, database,
dependency, workflow, fixture, golden, or example behavior.

Runtime imports, dynamic loading, Python plugins, hooks, arbitrary code,
network, database object imports, project IR/SQL/emit-sql, and package-manager
behavior remain outside current authorization.

## Package Version And Release Boundary

Package version remains `0.1.0`. Slice 6 changes no dependency, package metadata,
lockfile, build, workflow, or release surface.

No tag, release, publish, upload, signing, or attestation is authorized. Gate 2
does not stage, commit, push, trigger/rerun/watch/cancel CI, or prepare Gate 3.

## Separate Authorization And Stop Conditions

Every future compiler, module, package, or public-surface change requires
separate authorization. Phase 54 remains readiness-only and unstarted. Phase 55
remains unstarted. Slices 7 through 11 remain pending. No production module API
is designed.

Stop without repair or scope expansion if the exact eight-file allowlist cannot
hold; a ninth path changes; the roadmap, completed Slice 1-5 specs, Phase
44-49 artifacts, source, grammar, generated, public schema, or release surface
would change; current flat behavior would need to change; a current file would
need to become a module; a production grammar, AST, resolver, carrier,
filesystem change, diagnostic, package identity/resolver, public metadata
field, or Phase 54 implementation appears necessary; validation fails; or
Slice 7 or Phase 52-55 work appears necessary.
