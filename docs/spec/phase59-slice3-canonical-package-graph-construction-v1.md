# Phase 59 Slice 3 Canonical Package Graph Construction v1

## Answer And Scope

Slice 3 adds one deterministic private construction adapter:

```text
PackageInspectionFactSet -> PackageGraphResult
```

The adapter consumes the exact inspection and its retained exact load-plan
authority. It does not locate, load, parse, resolve, inspect, reselect, or
reconstruct package authority.

| Surface | Slice 3 result |
| --- | --- |
| Production owner | `src/pietto/_project/package_graph.py` |
| Construction entry | `_build_package_graph` |
| Public behavior | `0` |
| Project Explain / CLI behavior | `0` |
| New installed module | `0` |
| Route count | `12` |
| Version | `0.1.0` |

## Exact Upstream Authority

`PackageInspectionFactSet` is the single input so inspection and plan
authority cannot be independently substituted. Construction requires the
fact-set inspection, canonical bytes, inspection `plan_result`, and private
authority roots to remain identity-coherent.

| Upstream fact | Construction use |
| --- | --- |
| `PackageInspection.outcome` | Select exact graph terminal |
| `PackageInspection.packages` | Authoritative package order and facts |
| `PackageInspectionPackage.position` | Graph-local package position |
| `coordinate`, `content_digest`, `role` | Attached semantic/release/content/role facts |
| `PackageInspectionPackage.dependencies` | Declaring-package then authored order |
| `target_package_position` | Exact resolved target occurrence |
| `dependency.edge.occurrence` | Exact authored dependency witness |
| `plan_result.blockers/errors/diagnostics` | Ordered rejected/error evidence |

Paths, filenames, display names, aliases, digest equality, coordinate matching,
or iteration accidents are never used to infer a resolved target.

## Successful Construction

For `PackageInspectionOutcome.SUCCESS`, construction creates one fresh
`PackageGraphScope`, maps every inspection package one-to-one in existing tuple
order, and creates one witnessed `PackageGraphDependency` for every inspection
dependency by package order and package-local authored order.

Package refs use exact inspection positions. Dependency refs use the declaring
package ref and exact authored position. Links retain the exact
`PackageDependencyOccurrence` object reached through the inspection edge and
target only `target_package_position`.

The completed `PackageGraphSnapshot` performs the Slice 2 scope, position,
endpoint, witness-coordinate, and digest-pin checks. Success retains exact
non-error upstream diagnostics and returns one complete snapshot.

No package or link is sorted, deduplicated, merged by coordinate/digest, or
selected as a winner. Parallel equal-endpoint declarations remain separate
links because their authored refs and witnesses remain separate.

## Rejected And Error Construction

| Inspection outcome | Graph outcome | Snapshot | Exact evidence |
| --- | --- | --- | --- |
| `REJECTED` | `REJECTED` | Absent | Same ordered `plan_result.blockers` and diagnostics |
| `ERROR` | `ERROR` | Absent | Same ordered `plan_result.errors` and diagnostics |

Neither terminal exposes a partial graph. No replacement node, partial
snapshot, or success-shaped fallback is created.

An exact fact set whose supposedly successful contents fail intrinsic Slice 2
model validation returns `ERROR` with one private existing
`ProjectDiscoveryError(PROJECT_RESOURCE, ...)`. This is a fail-closed adapter
error, not a fourth outcome or new planner diagnostic taxonomy.

## Determinism And Scope

Repeated construction from the same authority preserves package/dependency
positions, tuple order, attached facts, and exact witness objects. Each call
creates a fresh runtime scope, so refs across two independently constructed
snapshots remain unequal even when their deterministic local coordinates are
equal.

“Canonical” means deterministic construction from authoritative facts. Slice 3
adds no canonical bytes, marker, digest, UUID, persistent ID, or serialization.

## Non-goals

Slice 3 adds no resolver, loader, locator, filesystem/manifest traversal,
inspection builder, dependency solver, range, lockfile, requirement/selector,
capability/catalog provenance, module/declaration/field/lineage domain,
traversal, BFS/DFS, why path, reverse index, JSON, public graph API, Project
Explain field, CLI flag, semantic metadata behavior, SQL/type/aggregate/window
semantics, Rust, or Slice 4 behavior.

The existing Slice 2 model remains the only package/dependency graph model.
Construction adds no generic graph abstraction or duplicate identity carrier.

## Focused Assurance

Focused tests use real production location, loading, planning, and inspection
constructors. They cover root-only success, one and multiple dependencies,
upstream order, parallel authored declarations, exact witness/target retention,
scope separation across repeated construction, real cycle rejection, real
dependency-path error, structurally inconsistent success failure, no
sort/dedup, no loader/resolver call, and public/Project Explain/CLI zero-delta.

Slice 2 model tests continue to prove equal semantic/content facts remain
distinct graph occurrences where the model permits them; Slice 3 maps every
upstream package occurrence one-to-one and contains no merge operation.

## Reader And Packaging Closure

The implementation remains in the already installed
`pietto._project.package_graph` module. The existing exact package-manifest
consumer allowlist already names that module; adding construction creates no
new direct package-manifest consumer. No package inventory or smoke-owner edit
is required. Existing isolated package smoke still imports the changed module
and is required after validation because production code changed.

No public, Project Explain, CLI, generated, golden, package metadata, or
`__init__` path changes.

## Workflow And Lifecycle

Focused validation precedes one foreground Ponytail FULL review. At most one
causal review repair generation plus one fresh complete rereview is permitted.
Only a clean reviewed tree may start the Python 3.13 validator once. Production
change requires one installed-package smoke; generated/golden deltas remain
zero. Publication uses one commit, one normal push, and natural exact-head CI.

The candidate records Phase 59 active, Slices 1–2 completed, Slice 3 current,
Slice 4 next/unstarted, and the unchanged 12-slice route. Successful natural
CI completes Slice 3 without a status-only commit. Slice 4 remains unimplemented
and unauthorized.

## Publication Subject

The exact publication subject is:

```text
Construct canonical Phase 59 package graph
```
