# Phase 59 Slice 2 Private Package Graph Model And Snapshot Identity v1

## Answer And Scope

Slice 2 implements the private package/dependency value model frozen by Slice
1. It adds runtime graph-snapshot scope, typed package/dependency occurrence
references, immutable occurrence carriers, one ordered package-graph snapshot,
scope-enforced direct lookup, and exact `SUCCESS` / `REJECTED` / `ERROR`
results.

| Surface | Slice 2 result |
| --- | --- |
| Production module | `src/pietto/_project/package_graph.py` |
| Public behavior | `0` |
| Project Explain behavior | `0` |
| CLI behavior | `0` |
| Builder or real-plan adaptation | `FORBIDDEN` |
| Canonical/public serialization | `FORBIDDEN` |
| Version | `0.1.0` |

The graph builder remains Slice 3. Slice 2 performs no package location,
loading, dependency walking, resolution, inspection construction, parsing,
capability checking, traversal, or why derivation.

## Live Inputs And Reuse

| Fact | Exact reused authority | Slice 2 use |
| --- | --- | --- |
| Semantic and release identity | `PackageIdentity` through `PackageCoordinate` | Attached package fact only |
| Package content identity | Existing 64-lowercase-hex SHA-256 text | Attached package fact only |
| Root/dependency role | `PackageInspectionPackageRole` | Attached package fact only |
| Authored dependency occurrence | `PackageDependencyOccurrence` | Exact direct-link witness |
| Rejection blocker | `PackageLoadPlanBlocker` | Ordered `REJECTED` evidence |
| Project/package error | `ProjectDiscoveryError` | Ordered `ERROR` evidence |
| Parser diagnostic | `Diagnostic` / `Severity` | Ordered diagnostic evidence |

`LoadedRootPackage`, `LoadedDependencyPackage`, `PackageLoadPlanEntry`,
`PackageDependencyEdge`, `PackageInspectionPackage`, and
`PackageInspectionFactSet` remain upstream authority only. The model neither
imports nor constructs them. Physical/resolved package paths are omitted from
package occurrences; any such values retained by an exact witness or blocker
remain private evidence and never occurrence identity.

## Private Namespace

The exact namespace is `pietto._project.package_graph`. It is one installed
private module with `__all__ = ()`; no new package hierarchy and no
`__init__` re-export are added. Its owner is Phase 59 graph identity, not
package loading/resolution, Project Explain, semantic public API, or CLI.

## Runtime Scope

`PackageGraphScope` is an immutable, opaque, identity-equal runtime owner.
Every instance is distinct from every separately created instance even when
their local coordinates match. It contains no UUID, timestamp, global counter,
content digest, path, or public semantic identity. Its deterministic `repr`
is `PackageGraphScope()` and exposes no object address.

Scope participates in runtime ref equality/hash. It is not serialized and is
not part of future canonical private coordinates. Slice 2 implements no
canonical representation.

## Typed Runtime References

| Type | Exact fields | Runtime identity | Future local coordinate |
| --- | --- | --- | --- |
| `PackageGraphPackageRef` | `scope`, `position` | scope identity + non-negative package position | package position |
| `PackageGraphDependencyRef` | `scope`, `declaring_package`, `declaration_position` | scope identity + declaring package ref + non-negative authored position | declaring package position + authored position |

The two refs are distinct Python types. Coordinate, digest, logical/physical
path, role, and future evidence never enter ref equality. A dependency ref is
the authored dependency occurrence, not its resolved package. It is never
defined by endpoint pair or edge kind.

The runtime ref and future canonical coordinate are separate concepts. Slice 2
only leaves deterministic local positions available for Slice 9; it adds no
marker, global string ID, JSON, content digest, or canonical bytes.

## Occurrence Carriers

| Type | Exact fields | Identity authority |
| --- | --- | --- |
| `PackageGraphPackage` | `ref`, `coordinate`, `content_digest`, `role` | `ref` |
| `PackageGraphDependency` | `ref`, `declaring_package`, `resolved_package`, `witness` | `ref` |

`PackageGraphPackage.coordinate` reuses exact semantic/release identity;
`content_digest` is content evidence; `role` is a fact. Complete carrier value
equality may compare complete fields, but graph endpoint/lookup identity is
always the typed ref.

`PackageGraphDependency` represents one authored occurrence and its exact
resolves-to relationship as one coherent fact. Its `witness` is the exact
existing `PackageDependencyOccurrence`; witness position must equal the ref's
authored position. The ref's declaring package must equal the link's declaring
package. The witness is not replaced by a string, coordinate-only value, or
endpoint pair.

## Snapshot And Lookup

`PackageGraphSnapshot` contains exactly:

```text
scope
packages: tuple[PackageGraphPackage, ...]
dependencies: tuple[PackageGraphDependency, ...]
```

It requires at least one package. Package refs are dense in supplied tuple
order (`ref.position == tuple position`) and unique. Dependency refs are unique
but retain the supplied authoritative tuple order; the constructor performs no
sorting or deduplication. Equal package coordinates or content digests are
allowed at distinct refs.

Every stored ref must belong to the exact snapshot scope. Every dependency's
declaring and resolved package refs must resolve in the snapshot. Its exact
witness coordinate and digest pin must match the resolved package facts.
Parallel links with equal endpoints remain distinct when authored refs differ.

`package(ref)` and `dependency(ref)` are the only Slice 2 lookup operations.
They reject wrong typed refs, foreign scope, invalid coordinates, and missing
occurrences. They add no traversal or derived index; dependency lookup is a
bounded linear scan until Slice 9 owns derived indexes.

## Outcome Model

`PackageGraphOutcome` has exactly `SUCCESS`, `REJECTED`, and `ERROR`.
`PackageGraphResult` has exactly `outcome`, `snapshot`, `blockers`, `errors`,
and `diagnostics`, all immutable and ordered.

| Outcome | Snapshot | Blockers | Errors / diagnostics |
| --- | --- | --- | --- |
| `SUCCESS` | Required | Empty | No `ProjectDiscoveryError` or error-severity diagnostic; warnings allowed |
| `REJECTED` | Forbidden | One or more exact ordered `PackageLoadPlanBlocker` facts | No competing error authority; non-error diagnostics allowed |
| `ERROR` | Forbidden | Empty | One or more `ProjectDiscoveryError` or error-severity diagnostic facts |

Impossible combinations fail closed. `REJECTED` and `ERROR` never expose a
partial snapshot as successful graph authority.

## Intrinsic Integrity Boundary

Slice 2 validates only package-domain invariants intrinsic to its value model:
exact types and tuples, non-negative coordinates, scope agreement, dense
package positions, unique package/dependency refs, resolvable direct endpoints,
and witness-to-target coordinate/digest agreement.

Slice 9 retains comprehensive cross-domain referential integrity, canonical
input graft rejection, requirement-selector integrity, module-field integrity,
lineage integrity, and derived query/index authority.

## Non-goals And Deferred Ownership

The module defines no generic node/edge base, string kind, metadata dictionary,
future requirement/selector/evidence/module/declaration/field/lineage ref,
builder, resolver, loader, planner, parser, capability checker, BFS/DFS,
ancestor/descendant query, why path, shortest path, upstream/downstream index,
JSON, canonical bytes, graph digest, persistent/public ID, Project Explain
projection, FFI, ABI, or Rust code.

Slice 3 owns construction from `PackageLoadPlan` and
`PackageInspectionFactSet`. Slice 6 owns why/why-not. Slice 9 owns private
canonical inspection and pure query/index boundaries. Phase 70 owns any public
projection.

## Readiness

Phase 67 may relocate or transport packages without changing graph occurrence
identity because refs contain no physical/install/repository path. Exact paths
inside existing witnesses remain evidence only.

Phase 68 may later insert solver and lockfile resolution between the preserved
authored dependency occurrence and loaded package occurrence. Slice 2 adds no
ranges, solver result, or lockfile entry.

The model is Rust-ready only in shape: frozen slotted values, explicit enum,
typed refs, tuples, and no `Any`, mutable global registry, closure facts, or
object-address serialization. No Rust implementation decision is made.

## Project Explain And Packaging Zero-delta

No public or Project Explain module imports `pietto._project.package_graph`.
`pietto.project-explain.v1`, field inventory, serializer, CLI, and Semantic
Metadata Artifact v1 remain unchanged. No public golden is added.

The central package smoke inventory includes the new private module and proves
its isolated wheel import while retaining version `0.1.0`, single-file explain,
and project-explain smoke behavior.

## Focused Assurance

The Slice 2 test owns runtime scope isolation, same-scope equality/hash,
attached-fact independence, same-content distinct occurrences, package
positions, authored-vs-resolved typing, parallel links, exact witness retention,
tuple order, foreign/wrong-domain lookup rejection, intrinsic validation,
result invariants, no partial rejected/error graph, private import boundaries,
and the absence of builder/serializer/future-domain scaffolding.

Focused validation also runs direct Phase 55 identity/load-plan/inspection
tests, Phase 59 Slice 1, package-smoke policy, active/workflow lifecycle, and
exact Project Explain/CLI readers. Full pytest remains reserved for the one
authoritative validator.

## Workflow And Lifecycle

After focused validation, one foreground Ponytail FULL review may produce at
most one causal repair generation followed by a fresh complete rereview. Only
then may the Python 3.13 validator start once. Generated and golden auxiliaries
are not required unless their surfaces change; installed-package smoke is
required once because one installed private production module is added.

The candidate records Phase 59 active, Slice 2 current, Slice 3 next/unstarted,
and the unchanged 12-slice route. Successful natural exact-head CI makes Slice
2 completed and leaves Slice 3 next/unstarted without a status-only commit.
Slice 3 remains unimplemented and unauthorized by this Slice.

## Publication Subject

The exact publication subject is:

```text
Add private Phase 59 package graph model
```
