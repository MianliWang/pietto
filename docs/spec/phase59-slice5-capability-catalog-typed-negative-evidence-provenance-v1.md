# Phase 59 Slice 5 Capability, Catalog, And Typed Negative Evidence Provenance v1

## Answer And Owner

Slice 5 extends the private Phase 59 package graph with exact Phase 58
capability, catalog, provider, source, and typed-negative-evidence provenance.
It is provenance attachment, not capability evaluation.

The occurrence chain is exactly:

```text
package -> requirement -> selector when applicable -> target/context
```

Every attachment retains the exact existing Phase 58 fact set and cell or
provider occurrence that authorized it. No public schema or runtime behavior
is added.

## Existing Authority Inputs

| Input | Existing owner | Slice 5 use |
| --- | --- | --- |
| Package, requirement, and selector occurrences | `src/pietto/_project/package_graph.py` | Exact Slice 4 graph refs |
| Target context, matrix row/cell, checked result, and blocker | `src/pietto/_project/capability_matrix.py`; `src/pietto/_project/capability_checking.py` | Exact retained evaluation witness |
| Capability inspection authority | `src/pietto/_project/capability_inspection.py` | Anti-graft fact-set root |
| Catalog availability and selection | `src/pietto/_project/extension_catalog_availability.py` | Existing typed selection outcome only |
| Provider authority and input/result evidence | `src/pietto/_project/extension_signature_provider.py` | Existing selector-bound provider witness only |
| Catalogs, digests, candidates, sources, entries, groups, and provider occurrences | `src/pietto/_project/extension_catalog_inspection.py` | Exact retained catalog fact-set root |

Production carriers remain owned by those modules. Slice 5 neither copies
their state machines nor reconstructs facts from Project Explain output.

## Typed Snapshot Coordinates

| Ref | Deterministic local coordinate | Domain |
| --- | --- | --- |
| `PackageGraphCapabilityEvaluationRef` | snapshot scope + exact requirement ref + target position | Requirement-target evaluation |
| `PackageGraphCatalogEvidenceRef` | snapshot scope + exact selector ref + target position | Selector-target catalog evidence |

Both refs reject foreign snapshots, negative positions, and wrong-domain
lookups. Their identity excludes `CapabilityKey`, catalog coordinate, digest,
path, display syntax, provider value, source locator, and installation state.
Those values remain evidence, never graph occurrence identity.

## Attachment Carriers

`PackageGraphCapabilityEvaluation` retains:

* one exact capability-evaluation ref;
* the exact selector ref when Slice 4 supplied one, otherwise `None`;
* the exact `CapabilityInspectionFactSet`;
* the exact matrix cell;
* either its exact `CapabilityRequirementCheck` or its exact
  `PackageCapabilityRequirementsBlocked` evidence.

`PackageGraphCatalogEvidence` retains:

* one exact catalog-evidence ref;
* the exact capability-evaluation ref it qualifies;
* the exact `ExtensionCatalogInspectionFactSet`;
* the exact `ExtensionCatalogInspectionProviderOccurrence`.

The retained catalog inspection keeps catalog coordinate, target, digest,
availability declarations, candidates, selected catalog, provider input and
lookup, catalog entries/groups, source occurrences, source positions, order,
and multiplicity separate. No field is collapsed into a provider/catalog ID.

## Typed State Preservation

Existing typed meanings remain exact:

```text
SATISFIED
UNSUPPORTED
ABSENT
UNKNOWN
CONFLICT
BLOCKED
UNDECLARED / SELECTED / AMBIGUOUS / CONFLICT catalog selection
FOUND / ABSENT / UNKNOWN / CONFLICT provider lookup
```

The required distinctions include:

```text
UNKNOWN != ABSENT
omission != UNSUPPORTED
BLOCKED != checked UNKNOWN
undeclared != declared empty
availability != selection
selection != installation
catalog existence != availability
```

Selection-unavailable, ambiguous, conflicting, completeness, unmodeled,
exposure, rejection, and resource-error meanings remain owned by their exact
upstream carriers. Slice 5 introduces no generic failure enum and derives no
negative meaning from an absent positive edge.

## Sparse Positive Topology

Sparse positive topology remains the graph rule. Evaluated
requirement-target and selector-target relationships are stored as occurrence
attachments. Negative and blocker states stay in the typed evidence carried by
those attachments. There are no generic `UNKNOWN`, missing-provider, blocker,
or error nodes and no fake negative edges.

Schema-v2 selector-unbound requirements remain representable with a capability
evaluation and no invented selector/catalog evidence. Non-extension and
blocked cells retain their exact capability evidence and add no not-applicable
catalog record. Package rejection/error outcomes remain root terminals with no
partial successful snapshot.

## Construction And Exact Mapping

The existing `_build_package_graph` entry accepts an optional explicit pair:

```text
capability_facts: tuple[CapabilityInspectionFactSet, ...]
extension_catalog_facts: tuple[ExtensionCatalogInspectionFactSet | None, ...]
```

Omitting both retains the earlier Slice 2–4 topology without implying any
negative state. Supplying provenance requires one capability fact set per
package and one catalog slot per package-target context.

Mapping uses exact package occurrence order, requirement collection identity,
requirement position, selector coverage position, and target position. It does
not use a bare semantic key and never chooses a first, nearest, equal-key, or
best match. Equal-key requirements in different packages remain distinct.
Impossible, ambiguous, grafted, foreign-package, foreign-context, missing-slot,
and extra-slot successful inputs return the existing package-graph
`PROJECT_RESOURCE` error terminal without a partial snapshot.

Capability attachment order is package, requirement, then target. Catalog
attachment order is package, target, then selector. Existing matrix,
catalog/provider, and source tuple order and multiplicity remain unchanged;
there is no sorting or deduplication in graph construction.

Explicit zero-target input retains requirements/selectors but creates no
target, provider, catalog, capability-evaluation, or negative-evidence
occurrence.

## Non-goals And Deferrals

No checking, provider reselection, catalog rebuilding, or inference is added.
Slice 5 also adds no loader/resolver change, catalog lookup policy, target or
profile semantics, installation probing, package-to-module attribution,
semantic/field lineage, traversal, direct/transitive why, why-not derivation,
reverse index, serializer, canonical graph bytes, public artifact, Project
Explain field, CLI behavior, Rust, or Slice 6 behavior.

Project Explain v1 and existing CLI remain zero-delta.

## Evidence And Lifecycle

Focused evidence covers occurrence-scoped equal keys, checked states and exact
witnesses, selector-bound and selector-unbound requirements, target ordering,
typed blocker separation, catalog selection outcomes, provider lookup facts,
catalog/source order and multiplicity, zero targets, identity exclusions,
foreign/wrong-domain/graft rejection, impossible mapping, repeated fresh-scope
construction, Slice 2–4 topology regression, and public compatibility.

Phase 59 remains active. Slices 1–4 are completed, Slice 5 current, and Slice 6
next/unstarted. Natural exact-head CI owns published completion; no status-only
follow-up commit is required. This Slice does not authorize Slice 6.

The publication subject is:

```text
Attach Phase 59 capability catalog provenance
```
