# Phase 58 Slice 3 Package And Requirement Provenance Projection v1

## Answer And Authority

Slice 3 implements the detached REQUEST-side package and capability-requirement
projection for the future `Project Explain Artifact v1`. It consumes exact
existing `PackageInspectionFactSet` and `CapabilityInspectionFactSet`
authorities without discovery, loading, planning, checking, or re-resolution.

The artifact marker remains `pietto.project-explain.v1`. The common Slice 2
model remains unchanged and private. Slice 3 adds no final payload, JSON, text,
or CLI behavior.

## Exact Private Authorities

Package truth comes only from:

```text
PackageInspectionFactSet
-> PackageInspection
-> pietto.package-inspection.v1
```

Capability requirement truth comes only from one ordered fact set per package:

```text
CapabilityInspectionFactSet
-> CapabilityInspection
-> PackageCapabilityCheckingMatrix.binding
-> CapabilityRequirementCollection
-> CapabilityRequirementOccurrence
```

Construction may use private object identity solely to verify that package and
capability facts retain the same exact loaded package. No private object
identity survives output.

## No Re-resolution Boundary

The projection does not read a manifest, discover a package, normalize an
authored dependency path, load content, rebuild a plan, select a profile,
construct a requirement, run a provider, check a requirement, or inspect a
matrix result.

It projects already-retained values and fails closed on missing, reordered,
foreign, duplicated, or grafted authority. It never sorts facts to recover an
invalid caller order.

## Private Python Surface

Production ownership is exactly:

```text
src/pietto/_project_explain/package_requirement_projection.py
```

The module and package retain empty `__all__`. Nothing is re-exported from
`pietto`, `pietto._project`, `pietto._metadata`, `pietto.semantic`, or another
public package root.

The Slice 3 model inventory is exactly:

- `ProjectExplainPackageRole`;
- `ProjectExplainPackageAssetKind`;
- `ProjectExplainDependencyLocatorKind`;
- `ProjectExplainPackageCoordinate`;
- `ProjectExplainPackageAsset`;
- `ProjectExplainDirectDependency`;
- `ProjectExplainPackage`;
- `ProjectExplainRequirementCollectionIdentity`;
- `ProjectExplainCapabilityKey`;
- `ProjectExplainRequirementCollection`;
- `ProjectExplainRequirementRequest`;
- `ProjectExplainPackageRequirementProjection`; and
- `_project_package_requirement_provenance`.

No Slice 2 symbol is moved or duplicated into this module.

## Closed Vocabularies

| Enum | Exact members and values |
| --- | --- |
| `ProjectExplainPackageRole` | `ROOT = "root"`; `DEPENDENCY = "dependency"` |
| `ProjectExplainPackageAssetKind` | `MODULE_SOURCE = "module_source"` |
| `ProjectExplainDependencyLocatorKind` | `LOCAL_DIRECTORY = "local_directory"` |

The vocabularies contain no workspace, transitive, optional, dev, peer,
runtime, remote, registry, or installation posture.

## Immutable Model Shapes

Every carrier is a frozen, slotted, keyword-only dataclass.

| Carrier | Exact field order |
| --- | --- |
| `ProjectExplainPackageCoordinate` | `namespace`, `name`, `release` |
| `ProjectExplainPackageAsset` | `position`, `kind`, `path` |
| `ProjectExplainDirectDependency` | `position`, `target_package_position`, `coordinate`, `content_digest_pin`, `locator_kind`, `project_path` |
| `ProjectExplainPackage` | `position`, `role`, `coordinate`, `project_path`, `content_digest`, `assets`, `dependencies` |
| `ProjectExplainRequirementCollectionIdentity` | `namespace`, `name` |
| `ProjectExplainCapabilityKey` | `domain`, `subject`, `operation`, `operands`, `context`, `dialect`, `extension` |
| `ProjectExplainRequirementCollection` | `declared_by`, `requested_by`, `package_role`, `identity`, `requirement_positions` |
| `ProjectExplainRequirementRequest` | `position`, `stage`, `declared_by`, `requested_by`, `package_role`, `collection`, `occurrence_position`, `key` |
| `ProjectExplainPackageRequirementProjection` | `root_package_position`, `packages`, `requirement_collections`, `requirements` |

Every integer position is an exact non-negative int; bool is rejected. Exact
tuples preserve order and multiplicity without mutable collection leakage.

## Package Coordinate And Digest Contract

`ProjectExplainPackageCoordinate` detaches exact non-empty namespace, name, and
release spelling from private `PackageCoordinate`. Release is the exact private
package version and is not normalized or reparsed.

Package `content_digest` and dependency `content_digest_pin` are exact 64-byte
lowercase hexadecimal SHA-256 text. They are package content identity, not Git
identity, signing, or attestation.

## Package Ordering And Root Position

`packages` preserves existing package-inspection order, which is dependency-
first declaration-order DFS postorder. Positions are dense and retained
exactly. The projection neither assumes nor rewrites the root position.

Exactly one package has role `ROOT`. Its actual position is retained in
`root_package_position`; every other package has role `DEPENDENCY`.

## Package Paths Assets And Dependencies

Package `project_path` and dependency `project_path` use
`ProjectExplainLogicalPathKind.PROJECT_RELATIVE`. Asset paths use
`ProjectExplainLogicalPathKind.PACKAGE_RELATIVE`.

No authored host path, canonical `Path`, symlink-resolved path, cwd, home,
temporary, venv, inode/device, or loader object is retained.

Assets preserve private/source order. Positions are dense within each package,
and the only v1 asset kind is `MODULE_SOURCE`.

Direct dependencies preserve declaration/source order. Each retains:

- exact source position;
- exact target package-table position;
- detached declared/selected coordinate;
- exact content digest pin;
- `LOCAL_DIRECTORY` locator posture; and
- resolved project-relative logical path.

The target position must name an earlier dependency-first package whose exact
coordinate and content digest equal the dependency coordinate and digest pin.
Disagreement fails closed and is never repaired.

## Requirement Collection Contract

`ProjectExplainRequirementCollectionIdentity` detaches exact non-empty
namespace and name values.

For each package:

- private `UNDECLARED` emits no collection and no request;
- private `DECLARED` emits exactly one collection;
- a declared collection with zero occurrences emits one collection with an
  empty `requirement_positions` tuple; and
- source occurrence order and multiplicity are preserved.

Therefore:

```text
undeclared
!=
declared empty collection
```

Collections appear in package-inspection order, skipping undeclared packages.

## Detached Capability Key

`ProjectExplainCapabilityKey` preserves the exact existing seven-field
semantic identity in this order:

```text
domain
subject
operation
operands
context
dialect
extension
```

`domain` remains the exact existing `CapabilityDomain`. The carrier retains no
private `CapabilityKey` object and adds no release, profile, target, catalog,
physical signature, provider result, checked status, or installation state.
Future capability domains such as `WINDOW_FUNCTION` require no carrier change.

## Requirement REQUEST Contract

Each `ProjectExplainRequirementRequest` has stage exactly
`ProjectExplainRequirementStage.REQUEST` and retains:

- dense project-wide position;
- declaring package position in `declared_by`;
- root/project package position in `requested_by`;
- declaring package role;
- detached collection identity;
- exact source occurrence position; and
- detached exact capability key.

Project-wide request ordering is concrete and deterministic:

```text
package-inspection order
then
source occurrence order within the package
```

This is package-major × source-occurrence order. Equal values from distinct
private occurrences remain distinct records where private authority permits
them. No sorting or deduplication is allowed.

## Bounded Provenance Semantics

For every collection and request:

```text
requested_by = root_package_position
```

For a root-package request:

```text
declared_by = requested_by = root_package_position
```

For a dependency-package request:

```text
requested_by = root_package_position
declared_by = dependency package position
```

The bounded explanation is:

```text
root/project package
-> declaring package
-> requirement occurrence
```

It does not infer an immediate parent edge or construct the Phase 59 transitive
package/provenance graph.

## Projection Integrity

`ProjectExplainPackageRequirementProjection` contains exact field order:

```text
root_package_position
packages
requirement_collections
requirements
```

It requires:

- dense packages and requests;
- one exact root;
- valid dependency targets and pins;
- one collection at most per declaring package;
- collection role matching its package;
- every `requested_by` naming the root;
- every request belonging to exactly one same-package collection;
- exact collection-to-request positions;
- dense occurrence positions within each collection;
- no unreferenced or multiply-owned request.

This is a Slice-local detached projection, not the final Project Explain
payload or a generic cross-section reference system.

## Canonical Construction

The single canonical entry point is:

```text
_project_package_requirement_provenance(
    package_facts: PackageInspectionFactSet,
    capability_facts: tuple[CapabilityInspectionFactSet, ...],
) -> ProjectExplainPackageRequirementProjection
```

Package inspection must be exact `SUCCESS` with a complete load plan. `ERROR`,
`REJECTED`, failed plans, discovery failures, and cycle/conflict/diamond
rejections fail before a projection is returned.

Capability facts must be an exact tuple with exactly one exact fact set per
package, in exact package-inspection order. Each fact set must retain the same
loaded package object and matching role, namespace, name, release, and content
digest. Missing, duplicate, reordered, foreign, or grafted facts fail closed.

Declared rows must retain the exact private binding, collection identity,
occurrence objects, source positions, and detached key facts. No requirement is
manufactured and no matrix cell is consulted for output.

## Privacy And Detachment

Output values contain only exact text, SHA-256 text, logical paths, enums,
integer positions, tuples, and detached capability-key values.

Output retains no `LoadedPackage`, `PackageInspectionFactSet`,
`CapabilityInspectionFactSet`, `PackageLoadPlan`, plan entry, dependency edge,
private requirement collection/occurrence, matrix, AST, filesystem `Path`,
private inspection, object ID, file descriptor, resolver, or checker.

Construction performs no filesystem or network access.

## Retained Later Ownership

| Slice | Retained owner |
| ---: | --- |
| 4 | Explicit evaluated targets, target columns, `UNDECLARED`/`BLOCKED`/`CHECKED`, five checked statuses, reasons, and bounded matrix evidence |
| 5 | Catalog coordinate/target/digest, selection, physical selector, matchability, exposure, and source provenance |
| 6 | `PORTABLE`, `NOT_PORTABLE`, `INDETERMINATE`, definite gaps, no-target, and zero-requirement classification |
| 7 | Final cross-section composition, generic artifact-local references, integrity, deduplication, and why links |
| 8 | Public JSON schema, dictionaries, serializer, canonical UTF-8 bytes, and goldens |
| 9 | Text renderer, future project explain CLI routing, exit codes, and streams |

Slice 3 adds no target/matrix carrier, checked-status enum, catalog projection,
portability enum, generic reference vocabulary, `ProjectExplainPayload`, JSON,
serializer, text renderer, or CLI behavior.

## Compatibility

Slice 3 leaves exact zero delta in:

- Slice 2 common model;
- package manifest/loading/planning/inspection;
- capability binding/checking/matrix/inspection;
- package/capability/catalog pure boundaries;
- extension catalog and inspection;
- Project JSON v2 and project check;
- Semantic Metadata Artifact v1 and `pietto explain <file>`;
- public Python exports; and
- grammar, generated parser, AST, semantics, IR, and SQL.

## Lifecycle And Slice 4 Handoff

Candidate lifecycle is:

```text
Phase 55: COMPLETED
Phase 56: COMPLETED
Phase 57: COMPLETED
Phase 58: ACTIVE
Slice 1: COMPLETED
Slice 2: COMPLETED
Slice 3: CURRENT
Slice 4: NEXT / UNSTARTED
```

Git plus successful natural exact-head CI owns Slice 3 completion. No later
status-only commit is required.

```text
PHASE58_SLICE3_SELF_OWNED_OPEN = 0
```

Slice 4 owner is the Public requirement/target compatibility matrix, explicit
evaluated targets, `UNDECLARED`/`BLOCKED`/`CHECKED`,
`SATISFIED`/`UNSUPPORTED`/`ABSENT`/`UNKNOWN`/`CONFLICT`, reasons, and bounded
matrix evidence.

Slice 4 remains `UNSTARTED / NOT AUTHORIZED`.
