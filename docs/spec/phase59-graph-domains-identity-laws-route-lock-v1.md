# Phase 59 Graph Domains, Identity Laws, And Route Lock v1

## Answer And Exact Owner

Phase 59 owns exactly:

```text
Local package graph, attribution, provenance, and lineage
```

Slice 1 activates that owner and freezes the private architecture needed by
Slices 2–12. It is a documentation and static-contract slice: production
changes, public behavior changes, and public schema changes are all zero. It
does not implement a graph model, graph builder, query, serializer, or CLI.

| Slice 1 surface | Contract |
| --- | --- |
| Production changes | `0` |
| Public behavior changes | `0` |
| Public schema changes | `0` |
| Generated paths | `0` |
| Golden paths | `0` |
| Package/build metadata paths | `0` |
| Graph implementation | `FORBIDDEN` |
| Public graph or CLI | `FORBIDDEN` |
| Current version | `0.1.0` |

## Non-goals

Phase 59 does not own package resolver or loading reimplementation,
cross-package semantic import/export, remote registry or fetch, trust-policy
expansion, ranges, a solver, a lockfile, installation, new SQL/type/aggregate
or window-frame semantics, Project Explain v1 expansion, a public graph
artifact, CLI, persistent/public UUIDs, release work, or Rust implementation.

Packages remain separate compilation islands. Package dependency never implies
semantic import or namespace visibility. Unsupported or absent graph authority
must fail closed without inventing a partial successful graph.

## Existing Authority Inputs

| Existing authority | Exact live owner |
| --- | --- |
| Package semantic and exact release identity | `src/pietto/_project/package_manifest.py` |
| Trusted package bytes, content digest, loaded root package, and root modules | `src/pietto/_project/package_loader.py` |
| Loaded dependency packages, authored dependency occurrences, resolved edges, blockers, and exact load-plan order | `src/pietto/_project/package_load_plan.py` |
| Successful/rejected/error package inspection and canonical facts | `src/pietto/_project/package_inspection.py` |
| Capability key, requirement collection identity, and requirement occurrence position | `src/pietto/semantic/capability_facts.py`; `src/pietto/semantic/capability_profiles.py` |
| Package-owned typed selector occurrence | `src/pietto/_project/package_manifest.py`; `src/pietto/semantic/extension_signature_requirements.py` |
| Package requirement `declared_by` / `requested_by` projection | `src/pietto/_project_explain/package_requirement_projection.py` |
| Module, declaration, reference, field, attribution, and provenance occurrences | `src/pietto/_project/module_carrier.py`; `src/pietto/_project/module_attribution.py` |
| Relation row dependency, lineage, and field provenance states | `src/pietto/_project/row_dependency_graph.py`; `src/pietto/_project/row_lineage.py`; `src/pietto/_project/model.py` |
| Project Explain artifact-local positional references | `src/pietto/_project_explain/composition.py` |

Tests and test-only helper types are not architecture authority. Existing
production carriers remain owned by their current modules; Phase 59 integrates
them without reloading, replanning, rechecking, reselection, or reconstructing
them from public Project Explain output.

## Identity Categories

| Category | Current or Phase 59 meaning |
| --- | --- |
| Semantic identity | Logical meaning such as `PackageIdentity` or `CapabilityKey` |
| Release identity | One exact release such as `PackageCoordinate` |
| Authored occurrence identity | One source declaration/request occurrence and its owner/position |
| Resolved/loaded occurrence identity | One authoritative occurrence in the successful loaded plan |
| Content identity | A digest over exact trusted content |
| Graph-local occurrence identity | A reference meaningful only in one Phase 59 graph snapshot |
| Presentation-local identity | A position meaningful only in one projected artifact such as Project Explain v1 |
| Physical trust/location evidence | Resolved path, filesystem identity, containment, and symlink evidence |

These categories never silently collapse. A path, name, alias, digest, source
location, display string, runtime object, or public presentation position does
not become a graph occurrence merely because it is unique in one input.

## Eight Identity Laws

### Identity Law 1 — Every Identity Has An Explicit Scope

No identity is meaningful without its declared scope. Package semantic
identity is package-semantic scoped; requirement occurrences are
package/collection scoped; module occurrences are package scoped;
declaration/field occurrences are module-occurrence scoped; and Phase 59
references are graph-snapshot scoped. A bare integer, path, name, digest, or
display string is never globally meaningful graph identity.

Slice 2 must make a reference outside its owning snapshot rejectable or
semantically invalid. This requires no public UUID or random serialized scope.

### Identity Law 2 — Separate Identity Categories

The eight categories in `Identity Categories` are independent authorities.
`PackageIdentity` is semantic identity, `PackageCoordinate` is release
identity, package SHA-256 is content identity, a dependency declaration is an
authored occurrence, a plan entry is a loaded occurrence, a Phase 59 ref is a
graph-local occurrence reference, a Project Explain ref is presentation-local,
and resolved filesystem identity is private trust/location evidence.

### Identity Law 3 — Authored Request Is Not Resolved Occurrence

```text
AuthoredDependencyOccurrence != ResolvedLoadedPackageOccurrence
```

The authored occurrence retains declaring package, declaration occurrence and
source position, authored coordinate/declaration, digest pin and locator
authority where present, plus an explicit resolves-to link. The loaded package
occurrence remains separate even under today's exact one-to-one version
semantics. This leaves Phase 68 free to insert solver and lockfile resolution
without migrating Phase 59 identity; Phase 59 adds neither.

### Identity Law 4 — Content Identity Never Becomes Occurrence Identity

```text
same content != same occurrence
```

A package content digest is integrity/content evidence and never defines
package occurrence equality. A future graph content digest, if a named
cross-boundary consumer requires one, is likewise content/integrity evidence.
Phase 59 does not require or freeze a graph content digest.

### Identity Law 5 — Names, Aliases, Paths, And Display Syntax Are Not Occurrence Identity

A module path alone is not a package-qualified module occurrence; a field name
alone is not a field occurrence; a dependency/import/re-export alias is not
the underlying semantic identity; and human display syntax is not canonical
internal identity. Authored spelling, logical paths, aliases, and source
locations remain provenance evidence.

### Identity Law 6 — Mutable Or Expandable Facts Do Not Participate In Occurrence Equality

Type details, typmods, coercion evidence, lineage, source location,
backend/catalog evidence, installation evidence, and public presentation fields
do not participate in occurrence equality. Phases 60, 64, 67, and 69 may attach
new facts without changing existing Phase 59 occurrence identity.

### Identity Law 7 — Graph-local Reference And Canonical Coordinate Are Different Concepts

A runtime graph-scoped handle/reference and a deterministic graph-local
canonical coordinate are distinct. Private canonical inspection may use stable
snapshot-local positions without creating global identity. A stronger runtime
owner/scope mechanism may reject foreign references, but no owner token, object
identity, memory address, or random scope value may enter canonical bytes.

### Identity Law 8 — Content Addressing Is Optional Evidence, Not The Default Graph-ID Strategy

Phase 59 does not define `NodeId = sha256(node facts)` or any equivalent
content-addressed occurrence identity. Graph occurrences identify exact
authoritative occurrences, not content objects. Hashes remain optional
integrity/cache evidence owned by a named future consumer.

| Law | Exact short name |
| ---: | --- |
| 1 | Every Identity Has An Explicit Scope |
| 2 | Separate Identity Categories |
| 3 | Authored Request Is Not Resolved Occurrence |
| 4 | Content Identity Never Becomes Occurrence Identity |
| 5 | Names, Aliases, Paths, And Display Syntax Are Not Occurrence Identity |
| 6 | Mutable Or Expandable Facts Do Not Participate In Occurrence Equality |
| 7 | Graph-local Reference And Canonical Coordinate Are Different Concepts |
| 8 | Content Addressing Is Optional Evidence, Not The Default Graph-ID Strategy |

## Graph-snapshot Scope

One private Phase 59 graph snapshot owns all of its graph-local references.
Every interpretation is through that exact snapshot and exact typed domain.
Foreign-snapshot, dangling, wrong-domain, and invalid scope-crossing references
must fail closed. Canonical positions are deterministic inspection coordinates,
not persistent/global identities. Equality never depends on runtime owner
tokens or physical trust/location evidence.

## Private Graph Root And Domain Taxonomy

The private root contains separate typed domain sections. A shared mechanical
helper is allowed, but semantic authority must not become `Node[Any]`,
`Edge[Any]`, `kind: str`, or `dict[str, object]`.

| Domain | Exact authority |
| ---: | --- |
| 1 | Package occurrences and direct dependency occurrences |
| 2 | Requirement and selector attribution |
| 3 | Capability, catalog, and source provenance |
| 4 | Package-qualified module, declaration, and field occurrences |
| 5 | Semantic and field lineage |
| 6 | Direct why and derived transitive why/why-not |
| 7 | Typed rejection, blocker, error, and negative evidence |

## Typed Link Taxonomy

| Typed relationship | Canonical direction | Required direct witness |
| --- | --- | --- |
| Dependency resolution | Authored dependency occurrence -> loaded package occurrence | Exact dependency declaration occurrence and load-plan edge |
| Requirement ownership | Package occurrence -> collection -> requirement occurrence -> selector occurrence | Exact package declaration and occurrence positions |
| Capability/catalog provenance | Requirement or selector evaluation -> typed capability/catalog/source evidence | Existing checker, selection, catalog, and source facts |
| Package-to-module bridge | Package occurrence -> package-qualified module -> declaration/field occurrence | Loaded package module and existing attribution authority |
| Semantic dependency | Reference occurrence -> declaration or field occurrence | Existing typed reference/dependency fact and origin path |
| Field lineage | Output occurrence -> typed ordered input occurrence | Existing lineage fact, role, and input/operand position |

Each relationship has one canonical authority direction. Reverse/downstream
views are derived indexes, never duplicate semantic authority.

## Direct-link Occurrence And Witness Law

A direct link is an occurrence, not merely `(source_ref, target_ref, kind)`.
Parallel authoritative declarations with identical endpoints remain distinct.
Every direct link retains an exact typed witness or deterministic reference to
the existing fact that authorized it: dependency declaration, import/reference,
requirement, selector, or lineage input occurrence. Inference alone cannot
create direct authority. Derived paths reference direct steps and never replace
them.

## Ordered And N-ary Fact Law

Ordered or n-ary facts are not flattened into unordered binary adjacency.
Computed expressions, aggregate arguments, window inputs, let expressions, and
multi-input lineage preserve every available role, operand/input/source
position, segment kind, and occurrence order. A binary typed link is allowed
only when those facts remain explicit.

## Package And Semantic Lineage Separation

Package provenance covers packages, dependencies, requirements, selectors,
capability/catalog/source evidence, and package-level why. Semantic lineage
covers modules, declarations, fields, expressions, and current
computed/let/aggregate/window lineage. Typed package-to-module and
module-to-semantic links connect the submodels. Package dependency does not
grant cross-package semantic imports or namespace visibility.

## Positive Topology And Typed Evidence

The architecture is sparse positive topology plus typed evidence sidecars.
Actual authoritative relationships form graph topology. `UNDECLARED`,
`UNKNOWN`, `ABSENT`, `UNSUPPORTED`, `CONFLICT`, `BLOCKED`, unavailable,
rejected, resource error, and not-applicable states remain typed evidence on
their owning evaluation/occurrence. They do not become generic negative nodes,
and absence of an edge implies no specific negative state.

## Root Outcomes And Domain-specific Cycles

| Root outcome | Contract |
| --- | --- |
| Successful complete graph | Contains one complete successful graph authority |
| Rejected graph authority | Contains ordered blockers and no successful graph |
| Error authority | Contains ordered errors/diagnostics and no successful graph |

| Domain | Cycle or failure semantics |
| --- | --- |
| Package dependency | Load-plan rejection; no successful partial package graph |
| Package loading/trust | Error outcome; no invented node |
| Module import | Preserve existing SCC/component and diagnostic-witness semantics |
| Relation dependency | Preserve existing blocked/cycle facts and diagnostics |
| Row/let lineage | Preserve non-concrete status/reason; no fabricated concrete subset |
| Requirement attribution | Acyclic by construction |

No universal `graph.has_cycle -> INVALID` state is authorized.

## Ordering And Multiplicity

| Authority | Required order |
| --- | --- |
| Package occurrences | Existing package inspection/load-plan order |
| Dependency links | Origin package order, then authored dependency occurrence order |
| Requirements | Package inspection order, then package-local occurrence order |
| Selectors | Exact requirement-coverage order |
| Capability evidence | Existing requirement x target order |
| Catalog/source evidence | Existing catalog/source authority order |
| Modules/declarations | Existing selected/module/source order |
| Lineage | Existing output/fact/input order |

Determinism comes from authority order, not sorting. Authoritative occurrences,
multiplicity, and equal-endpoint parallel links are never deduplicated.

## Direct And Transitive Why

Direct typed links are authority. Transitive why paths are pure derived facts
or query results. Every authoritative path and duplicate occurrence path is
preserved in direct-link traversal order. There is no shortest, preferred,
best, alphabetical, fallback, or hidden canonical winner.

## Path-materialization Law

All authoritative paths are preserved semantically, but the graph root need
not eagerly store every transitive path. Direct typed links plus typed evidence
remain canonical authority. Slice 6 may enumerate every requested path
deterministically; any optimization must preserve completeness and exact order
without making an eager exponential path corpus the primary representation.

## Why-not Provenance

Slice 6 derives why-not as a positive authoritative provenance path followed
by typed terminal negative, blocker, or error evidence. This supports questions
such as why capability is `UNKNOWN`, portability is `NOT_PORTABLE`, a package
graph is rejected, or lineage is `BLOCKED`. It creates no fake negative edge.

## Reverse Queries And Indexes

Derived indexes such as `by_coordinate`, `requirements_by_key`, and
`downstream_by_field` may accelerate pure queries. They are not graph authority
and cannot diverge from canonical forward links. Slice 9 owns exact private
direct-origin, upstream, downstream, direct-why, and transitive why/why-not
query APIs; no public/CLI query API is authorized.

## Referential Integrity

Slice 9 must validate every referenced occurrence exists, belongs to the right
typed domain and owning snapshot, and crosses only valid package/module scopes.
It must reject dangling, wrong-domain, foreign-snapshot, malformed, and grafted
private inspection input. Requirement-to-selector links target the exact
package-owned requirement occurrence; module/field links remain
package-qualified; lineage inputs resolve to valid semantic occurrences.

## Physical And Logical Privacy Boundary

Resolved paths, physical filesystem identities, containment/symlink facts, and
equivalent loader evidence remain private trust/location evidence. They do not
participate in graph equality. Logical package/module/source provenance remains
separate. Phase 70 cannot publish physical trust data by serializing the Phase
59 graph wholesale.

## Private Canonical And Public Boundary

Slice 9 owns one explicit, deterministic, private inspection/canonical
representation that preserves typed domains, order, multiplicity, and enough
information for integrity checking. It contains no runtime address/scope token
and creates no public compatibility commitment. Slice 1 freezes neither a
content digest, public marker, nor final field inventory. Phase 59 remains
private-first; public lineage projection remains Phase 70 ownership.

## Project Explain v1 Zero-delta

Existing package/load/module/requirement/catalog/lineage authorities feed
Project Explain v1 and the Phase 59 private graph as sibling consumers. Phase
59 is not reconstructed from Project Explain JSON. It changes no
`pietto.project-explain.v1` marker, field, artifact-local reference, CLI, or
Semantic Metadata Artifact v1 behavior.

## First Missing Production Edge

The first future production edge remains:

```text
PackageInspectionFactSet
+ exact PackageLoadPlan authority
+ package-owned loaded-module authority
-> package-aware private Phase 59 graph root
```

Slice 2 owns only the private root/result/reference carriers. Slice 3 owns the
first construction of this edge. Slice 1 implements neither.

## Exact 12-slice Route

| Slice | Owner | Boundary |
| ---: | --- | --- |
| 1 | Graph Domains, Identity Laws, And Route Lock | Docs/static architecture contract; no production |
| 2 | Private Package Graph Model And Snapshot Identity | Immutable private root/results, typed refs, package/dependency occurrences, and runtime snapshot-scope enforcement; no builder |
| 3 | Canonical Package Graph Construction | Construct package occurrences and witnessed direct dependency links from existing plan/inspection authority; no loader/resolver duplication |
| 4 | Requirement And Selector Attribution | Preserve package ownership, exact occurrence order, undeclared vs declared-empty, and parallel equal semantic keys; no capability checking |
| 5 | Capability, Catalog, And Typed Negative Evidence Provenance | Attach existing evidence without rechecking or reselection |
| 6 | Direct, Transitive, And Why-Not Provenance | Deterministic all-path derivation; no eager path corpus or winner |
| 7 | Package-to-Module Attribution Bridge | Package-qualified module/declaration occurrences; the same module path in different packages remains distinct; no cross-package semantic import |
| 8 | Semantic And Field-Lineage Integration | Integrate existing computed/let/aggregate/current-window lineage, ordered inputs, and non-concrete states; no new semantics or frames |
| 9 | Private Graph Integrity, Inspection, Query, And Canonical Pure Boundary | Referential integrity, pure queries, private canonical representation; no public artifact |
| 10 | Real Multi-Package Provenance And Lineage E2E | Real authored production inputs; no hand-built final graph |
| 11 | Differential Compatibility Assurance | Python 3.12/3.13, hash seed, relocation, wheel, and Project Explain/CLI zero-delta |
| 12 | Completion Audit And Phase 60 Handoff | Exit/readiness closure; no Phase 60 implementation |

## Route Expansion Rule

The published initial route has exactly 12 slices. Expansion requires a
genuinely independent Phase 59-owned production/compatibility authority that
is required by the exact owner, cannot fit an existing Slice, is not later-
phase-owned, and has an independent compatibility surface.

Reader omissions, review repairs, validator failures, fixture complexity,
performance tuning, external infrastructure failure, optional public output,
and speculative persistence do not justify route expansion.

## Exit-criterion Ledger

| Criterion | Eventual proof | Planned Slice |
| ---: | --- | ---: |
| 1 | Typed private root/domain model | 2 |
| 2 | Scoped graph-local occurrence identity | 2 |
| 3 | Authored dependency occurrence distinct from loaded occurrence | 2 |
| 4 | One package occurrence per successful plan entry | 3 |
| 5 | One dependency link per authored dependency occurrence | 3 |
| 6 | Parallel identical-endpoint links retain distinct witness identity | 3 |
| 7 | Requirement/selector package attribution | 4 |
| 8 | Capability/catalog/negative evidence provenance | 5 |
| 9 | Direct why authority | 6 |
| 10 | Complete deterministic transitive why/why-not derivation | 6 |
| 11 | Package-qualified module/declaration/field occurrence authority | 7 |
| 12 | Complete integration of existing computed/let/aggregate/window lineage | 8 |
| 13 | N-ary/ordered lineage semantics preserved | 8 |
| 14 | Domain-specific cycles and rejection semantics preserved | 9 |
| 15 | Referential integrity and wrong-domain/graft rejection | 9 |
| 16 | Pure derived query/index boundary | 9 |
| 17 | Deterministic private canonical inspection | 9 |
| 18 | Project Explain v1 zero-delta | 11 |
| 19 | Existing CLI zero-delta | 11 |
| 20 | Real authored-input E2E | 10 |
| 21 | Python/seed/relocation/wheel differential compatibility | 11 |
| 22 | Completion/handoff closure | 12 |

Completion is not repository-wide absence of TODOs.

## Phase 60–70 Readiness

| Phase | Frozen readiness boundary |
| ---: | --- |
| 60 | Current window occurrence identity and lineage accept later frame evidence without identity migration; no frames now |
| 61 | Phase 59 semantic occurrences remain IR-independent; future IR nodes may link to them, but IR identity never becomes graph identity |
| 62 | Preserve relation/field provenance without inferring JOIN, grain, cardinality, or fanout |
| 63 | Preserve source-mapping seams; no SQL lowering now |
| 64 | Type/coercion/typmod/temporal/native facts attach as evidence, not equality |
| 65 | Integrate only existing aggregate lineage; advanced grouping remains later-owned |
| 66 | Future typed package assets remain addable without redefining package occurrence identity |
| 67 | Logical identity, coordinate, declaration, digest, and physical location remain independent |
| 68 | Authored occurrence != solver resolution != lockfile resolution != loaded occurrence; only current endpoints now |
| 69 | Availability, candidate, selection, coordinate, digest, source, and installation stay distinct |
| 70 | Private deterministic inspection is suitable for explicit future public projection without promising public identity |

## Release And Rust Boundary

Phase 59 owns no version bump, tag, GitHub Release, package publication,
signing, attestation, or Rust implementation. Version remains `0.1.0`. Phase
68 retains the first Rust-kernel decision and Phase 70 retains release
readiness.

## Gate And Workflow Contract

Gate 0 rebinds clean synchronized `main`; Gate 1 reconstructs live authority,
closes direct readers, and freezes the exact changed-path allowlist. Gate 2
changes documentation/static tests only, runs the lean focused stage, performs
one foreground Ponytail FULL review, permits at most one causal repair
generation plus a fresh rereview, then starts exactly once:

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

A validator failure is terminal for the candidate. Generated, golden, and
package-smoke auxiliaries run only when a changed path enters their central
input surface. A clean review/validation candidate is sealed through two
independent temporary indexes, staged exactly, committed once, pushed once by
normal fast-forward, and proven by natural exact-head push CI attempt 1 on
Python 3.12 and 3.13. No rerun, dispatch, amend, rebase, squash, force push, or
status-only follow-up commit is authorized.

## Lifecycle Candidate And Publication Subject

The candidate records Phase 58 as completed, Phase 59 as active, Slice 1 as
current, and Slice 2 as next/unstarted. Successful natural exact-head CI makes
Slice 1 completed and leaves Slice 2 next/unstarted without a status-only
commit. Slice 2 remains unimplemented and unauthorized by this Slice.

The exact publication subject is:

```text
Add Phase 59 graph identity route lock
```
