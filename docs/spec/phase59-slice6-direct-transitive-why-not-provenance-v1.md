# Phase 59 Slice 6 Direct, Transitive, And Why-Not Provenance v1

## Answer And Owner

Slice 6 adds narrow private provenance derivation over the exact Slice 2–5
package graph. Direct links remain authority. Transitive paths are pure derived
results created only when requested. Why-not is exactly:

```text
positive provenance path
+
exact typed terminal non-success evidence
```

No path corpus, closure, index, serializer, public projection, or CLI is added.

## Direct Witness Authority

`PackageGraphDirectProvenanceStep` contains one closed-union `witness`. The
allowed exact witness carriers are:

| Witness | Direct source | Direct target |
| --- | --- | --- |
| `PackageGraphDependency` | declaring package ref | resolved package ref |
| `PackageGraphRequirement` | owning package ref | requirement ref |
| `PackageGraphSelector` | covered requirement ref | selector ref |
| `PackageGraphCapabilityEvaluation` | selector ref when bound, otherwise requirement ref | capability-evaluation ref |
| `PackageGraphCatalogEvidence` | capability-evaluation ref | catalog-evidence ref |

The step retains the exact existing carrier and therefore its exact authored,
checking, blocker, provider, catalog, and source witness. There is no generic
node, edge, `kind: str`, payload dictionary, name lookup, key lookup, digest
lookup, path lookup, or display-string lookup.

Direct steps are projected in existing snapshot tuple order by domain:
dependencies, requirements, selectors, capability evaluations, then catalog
evidence. Within each source occurrence, authored and evidence order remains
unchanged. No sorting or deduplication occurs.

## Typed Paths

`PackageGraphProvenancePath` contains:

```text
start: PackageGraphPackageRef
end: closed typed provenance ref
steps: tuple[PackageGraphDirectProvenanceStep, ...]
```

The closed endpoint union contains only package, requirement, selector,
capability-evaluation, and catalog-evidence refs. Paths require one snapshot
scope, non-empty exact steps, exact start/end agreement, and contiguous typed
endpoints. Dependency refs remain direct witnesses rather than graph nodes.

Foreign-snapshot endpoints, dangling refs, wrong-domain starts/ends, malformed
steps, and non-contiguous paths fail closed.

## On-Demand All-Path Derivation

`_derive_package_graph_provenance_paths` accepts one exact snapshot, one package
start ref, and one closed typed end ref. It projects direct steps for that call
and recursively extends them in existing occurrence order.

Every complete authoritative path is returned. Parallel declarations and
different routes remain occurrence-distinct. A direct shorter route does not
suppress a longer route to the same end. There is no first, shortest, longest,
preferred, best, alphabetical, ranked, or canonical winner.

The narrow derivation uses a path-local visited tuple only to prevent malformed
same-path repetition. It creates no new cycle classification. Successful
package graphs remain governed by existing load-plan cycle rejection.

Equivalent reconstruction preserves normalized local path order while using a
fresh runtime snapshot scope.

## Why-Not Terminals

`PackageGraphWhyNot` contains one exact positive path plus one exact existing
terminal carrier:

```text
CapabilityRequirementCheck
PackageCapabilityRequirementsBlocked
ExtensionCatalogInspectionProviderOccurrence
```

`_derive_package_graph_why_not` returns one result per positive path only when
the exact end evidence is non-success:

* checked `UNSUPPORTED`, `ABSENT`, `UNKNOWN`, or `CONFLICT` retains the exact
  `CapabilityRequirementCheck`;
* `BLOCKED` retains the exact
  `PackageCapabilityRequirementsBlocked`;
* catalog selection without a selected catalog, or selected provider lookup
  other than `FOUND`, retains the exact provider occurrence.

`SATISFIED` and selected-`FOUND` evidence produce no why-not result. Missing
positive edges, missing typed evidence, non-applicable catalog slots, and
zero-target authority also produce no why-not result. No negative node or fake
negative edge is created.

The distinctions remain exact:

```text
UNKNOWN != ABSENT
omission != UNSUPPORTED
BLOCKED != checked UNKNOWN
CONFLICT remains CONFLICT
unavailable remains unavailable
```

Rejected/error package-graph results retain their existing typed root terminal
and no successful snapshot; Slice 6 fabricates no path for them.

## Snapshot And Later-Slice Boundary

`PackageGraphSnapshot` gains no field. In particular it stores no `all_paths`,
`transitive_closure`, `all_why`, `all_why_not`, cache, reverse index, or path
identifier.

Slice 6 adds no generalized upstream/downstream query API, graph-search
framework, integrity subsystem, canonical bytes, public inspection, Project
Explain field, CLI behavior, module/declaration/field occurrence, semantic or
field lineage, cross-package semantic import, capability/catalog evaluation,
package loading/resolution, cycle semantics, or Rust.

Slice 7 owns package-to-module attribution. Slice 8 owns semantic and field
lineage. Slice 9 owns general private queries, indexes, integrity, inspection,
and the canonical pure boundary.

Project Explain v1 and existing CLI remain zero-delta.

## Evidence And Lifecycle

Focused evidence covers direct dependency/requirement/selector/evidence steps,
multi-hop paths, multiple routes, shorter-plus-longer routes, parallel authored
occurrences, exact occurrence ordering, equivalent reconstruction, foreign and
wrong-domain refs, checked and blocked why-not distinctions, catalog terminal
states, missing-edge behavior, zero targets, snapshot-field absence, privacy,
and Slice 7–9 deferrals.

Phase 59 remains active. Slices 1–5 are completed, Slice 6 current, and Slice 7
next/unstarted. Natural exact-head CI owns published completion; no status-only
follow-up commit is required. This Slice does not authorize Slice 7.

The publication subject is:

```text
Add Phase 59 direct and why-not provenance
```
