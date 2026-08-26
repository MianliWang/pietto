# Phase 59 Slice 4 Requirement And Selector Attribution v1

## Answer And Scope

Slice 4 extends the private package graph with package-owned requirement
declaration, authored requirement occurrence, and selector occurrence
attribution. It reuses the exact Phase 58 adapters and performs no capability
checking, provider selection, catalog lookup, or Project Explain projection.

| Surface | Slice 4 result |
| --- | --- |
| Production owner | `src/pietto/_project/package_graph.py` |
| Public / Project Explain / CLI change | `0` |
| New installed module | `0` |
| Capability checking | `FORBIDDEN` |
| Route count | `12` |
| Version | `0.1.0` |

## Exact Upstream Authority

For each exact `PackageInspectionPackage.entry.package`, construction calls
the existing `_package_capability_requirement_binding` once and then the
existing `_package_extension_signature_requirement_selectors` once. These
adapters consume the already-loaded manifest and validate package ownership,
schema version, requirement identity/order, selector coverage, and selector
ownership without parsing or matching again.

| Upstream authority | Graph use |
| --- | --- |
| `PackageCapabilityRequirementBinding | None` | Declared/undeclared collection witness |
| `CapabilityRequirementOccurrence` | Exact authored requirement witness |
| `ExtensionSignatureRequirementSelectors | None` | Exact selector coverage authority |
| `ExtensionSignatureRequirementSelectorOccurrence` | Exact selector occurrence witness |

## Declaration State

`PackageGraphRequirementDeclaration` contains exactly `UNDECLARED` and
`DECLARED`. Every package occurrence receives one ordered
`PackageGraphRequirementCollection`.

| Upstream state | Graph collection | Requirement occurrences |
| --- | --- | --- |
| Binding absent | `UNDECLARED`, binding/selectors absent | Zero |
| Binding present with empty collection | `DECLARED`, exact binding retained | Zero |
| Binding present with occurrences | `DECLARED`, exact binding retained | One per exact authored occurrence |

Undeclared and declared-empty remain distinct even though both have zero
requirement occurrences. No synthetic requirement is created.

## Typed References And Carriers

| Type | Exact runtime coordinate / facts |
| --- | --- |
| `PackageGraphRequirementRef` | snapshot scope + owning package ref + package-local requirement position |
| `PackageGraphSelectorRef` | snapshot scope + owning package ref + package-local selector position |
| `PackageGraphRequirement` | ref + package ref + exact `CapabilityRequirementOccurrence` witness |
| `PackageGraphSelector` | ref + package ref + covered requirement ref + exact selector witness |

Requirement and selector refs are distinct Python types. `CapabilityKey`,
package coordinate, collection name, digest, serialized contents, or a bare
position never define occurrence identity. Equal keys in different package
occurrences remain distinct authored graph occurrences.

## Snapshot Attribution Sections

`PackageGraphSnapshot` adds ordered `requirement_collections`, `requirements`,
and `selectors` tuple sections. The first follows package order exactly. The
second flattens package order then package-local requirement order. The third
flattens package order then exact selector coverage order.

Snapshot validation requires:

* exactly one collection per package when attribution sections are present;
* collection package refs and exact binding/selector ownership to agree;
* requirement carriers to cover every binding occurrence one-to-one by object
  identity and order;
* selector carriers to cover every selector occurrence one-to-one by object
  identity and order;
* selector requirement refs to use `witness.requirement_position`, never key
  equality;
* all refs to share the snapshot scope and resolve in their typed domain.

Legacy direct Slice 2 snapshot construction remains source-compatible through
empty default attribution tuples. Canonical Slice 4 construction always emits
one collection per package, including undeclared packages.

## Selector Attribution

Schema-v3 selector authority maps each selector occurrence to the exact
requirement ref at its covered requirement position. Equal-looking selectors
remain distinct when their selector positions differ.

Schema-v2 `EXTENSION_SIGNATURE` requirements remain valid with a declared
requirement occurrence and no selector collection or graph selector. No
selector is invented. Package-owned selectors remain package-owned.

Impossible package ownership, binding identity, coverage, or occurrence order
fails closed through the existing adapter/model error path and returns graph
`ERROR` without a partial snapshot.

## Ordering And Determinism

No requirement or selector is sorted, deduplicated, merged by key, or selected
as a winner. Repeated equivalent construction preserves deterministic local
coordinates, declaration state, flattened order, and witness facts while each
snapshot receives a fresh runtime scope.

Slice 3 package/dependency occurrences and links are unchanged.

## Non-goals

Slice 4 adds no capability checker, provider, target/profile/matrix cell,
catalog availability/source provenance, synthetic status evidence,
package-module bridge, declaration/field/lineage domain, traversal, why path,
reverse index, serializer, digest, UUID, public graph, Project Explain/CLI
field, resolver/loader/inspection behavior, Rust, or Slice 5 behavior.

## Reader And Packaging Closure

All implementation remains in the installed `pietto._project.package_graph`
module. The package-manifest consumer allowlist already trusts that exact path;
no new module or package-smoke inventory entry is needed. The Slice 2 model
shape test is a genuine direct reader and is updated for the newly authorized
typed classes and additive snapshot fields.

Existing package-manifest/requirement/selector owner tests, package smoke,
Project Explain/CLI compatibility, and lifecycle policy remain focused readers
without content changes.

## Workflow And Lifecycle

Focused validation precedes one foreground Ponytail FULL review. At most one
causal repair generation and one fresh complete rereview are allowed. Only a
clean reviewed tree may start the Python 3.13 validator once. Changed production
code requires one installed-package smoke; generated/golden deltas remain zero.

The candidate records Phase 59 active, Slices 1–3 completed, Slice 4 current,
Slice 5 next/unstarted, and the unchanged 12-slice route. Successful natural
CI completes Slice 4 without a status-only commit. Slice 5 remains
unimplemented and unauthorized.

## Publication Subject

```text
Add Phase 59 requirement selector attribution
```
