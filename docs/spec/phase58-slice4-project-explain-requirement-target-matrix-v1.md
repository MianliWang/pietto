# Phase 58 Slice 4 Project Explain Requirement Target Matrix v1

## Answer And Authority

Slice 4 implements the detached public-model projection of the existing private
multi-target capability matrix for the future `Project Explain Artifact v1`.
The artifact marker remains `pietto.project-explain.v1`.

The exact authority is the supplied Slice 3 package/requirement projection plus
the already-built `PackageInspectionFactSet` and one exactly package-ordered
`CapabilityInspectionFactSet` per package. The canonical private matrix remains
`PackageCapabilityCheckingMatrix`. Slice 4 projects that authority; it is no
second checker and performs no lookup, provider call, profile composition,
package resolution, or catalog selection.

## Private Python Surface

Production ownership is exactly:

```text
src/pietto/_project_explain/compatibility_matrix_projection.py
```

The module and package keep empty `__all__`. No symbol is re-exported from a
public Python root.

## Explicit Evaluated Target Denominator

For a non-empty denominator, the root package matrix's exact caller-ordered
`CapabilityCheckingTargetContext` objects are authoritative. At every target
position, every other package matrix must retain the same exact context object.
Equal-looking foreign context authority, count drift, reordering, intersection,
union, sorting, deduplication, nearest-target matching, and range expansion all
fail closed.

Object identity validates the common private authority only. It never survives
the detached output. Public target positions are dense and preserve exact
caller order. Equal public target values at distinct authoritative positions
remain distinct.

## Explicit Empty Denominator

`_project_empty_requirement_target_matrix(package_projection)` represents an
explicitly empty evaluated target denominator as:

```text
targets = ()
package_target_evaluations = ()
one row per Slice 3 request
every row cells = ()
```

This means no target was evaluated. It does not mean undeclared, blocked,
checked, unsupported, unknown, or failed. The constructor consumes detached
Slice 3 values only and performs no filesystem, profile, provider, catalog,
database, or network operation. Slice 6 retains the
`INDETERMINATE / no-evaluated-targets` consequence.

## Closed Vocabularies

Evaluation state is exactly:

```text
UNDECLARED = "undeclared"
BLOCKED = "blocked"
CHECKED = "checked"
```

Checked status is exactly:

```text
SATISFIED = "satisfied"
UNSUPPORTED = "unsupported"
ABSENT = "absent"
UNKNOWN = "unknown"
CONFLICT = "conflict"
```

Profile kind is `BASE = "base"` or `OVERLAY = "overlay"`. Profile target kind
is `DATABASE = "database"` or `EXTENSION = "extension"`. Availability owner is
`COMPILER = "compiler"` or `PROJECT = "project"`.

Matrix blocker kind is exactly
`PROFILE_NOT_DECLARED_AVAILABLE = "profile_not_declared_available"` or
`PROFILE_AUTHORITY_MISMATCH = "profile_authority_mismatch"`. Lookup variant is
`FOUND`, `ABSENT`, `UNKNOWN`, or `CONFLICT` with their lowercase values.
Capability support is `SUPPORTED = "supported"` or
`EXPLICITLY_UNSUPPORTED = "explicitly_unsupported"`.

No vocabulary adds partial, skipped, failed, installed, runtime, or portability
states.

## Immutable Model Inventory And Field Order

Every carrier is a frozen, slotted, keyword-only dataclass.

| Carrier | Exact field order |
| --- | --- |
| `ProjectExplainCapabilityProfile` | `namespace`, `name`, `profile_release`, `kind`, `target_kind`, `database_family`, `target_release`, `extension_identity`, `extension_release` |
| `ProjectExplainEvaluatedTarget` | `position`, `database_family`, `database_release`, `base_profile`, `supplied_overlays`, `dependency_order` |
| `ProjectExplainAvailabilityOccurrence` | `owner_kind`, `owner_position`, `project_path`, `profile` |
| `ProjectExplainMatrixBlocker` | `kind`, `selected_profile`, `bucket_profile`, `bucket_occurrences` |
| `ProjectExplainPackageTargetEvaluation` | `package_position`, `target_position`, `state`, `evidence_posture`, `availability`, `blockers` |
| `ProjectExplainLookupSummary` | `variant`, `reason`, `supports` |
| `ProjectExplainCheckedEvidence` | `target_lookup`, `provider_domain_complete`, `provider_unknown_reason`, `provider_lookup` |
| `ProjectExplainMatrixCell` | `target_position`, `state`, `checked_status`, `evidence_posture`, `checked_evidence` |
| `ProjectExplainMatrixRow` | `requirement_position`, `cells` |
| `ProjectExplainRequirementTargetMatrix` | `targets`, `package_target_evaluations`, `rows` |

Positions are exact non-negative integers with bool rejected. Collections are
exact tuples. Each root validates dense positions, target order, package by
target evaluation order, row order, cell target order, and all state-local
shape invariants.

## Detached Target And Profile Identity

A detached profile retains exact namespace, name, profile release, kind,
target kind, database family, target release, and optional extension identity
and release. Text is retained without normalization.

A base profile is `BASE / DATABASE` and has no extension identity. An overlay
is `OVERLAY / EXTENSION` and has exact non-empty extension identity and release.

An evaluated target retains its dense position, database family and release,
one matching base profile, supplied overlays in caller order, and the exact
private composition dependency order. Neither collection is sorted or
deduplicated. The target is a compiler-analysis context, not an installed
server or current connection.

## Availability And Blocker Evidence

Availability occurrences preserve private order and multiplicity. Compiler
owners have no project path. Project owners carry exactly one
`ProjectExplainLogicalPath(PROJECT_RELATIVE, ...)`; no host path survives.

`PROFILE_NOT_DECLARED_AVAILABLE` retains the selected profile and has no bucket
profile or occurrence. `PROFILE_AUTHORITY_MISMATCH` retains the selected
profile, the same-reference bucket profile, and the non-empty ordered bucket
occurrences. No authority winner is inferred.

## Package Target Evaluation State

Package-target evaluations are ordered package order by target order.

| State | Required evidence posture and shape |
| --- | --- |
| `UNDECLARED` | `UNAVAILABLE`; no blockers; the package has no declared requirement collection |
| `BLOCKED` | non-empty blockers; `CONFLICTING` when any blocker is an authority mismatch, otherwise `UNAVAILABLE` |
| `CHECKED` | `DETERMINISTIC_DERIVATION`; no blockers |

Package-target evaluations have no checked status. A checked status belongs
only to a checked requirement cell.

## Lookup Summaries And Reasons

A lookup summary contains only variant, exact reason-code text or `None`, and
ordered detached support postures.

| Variant | Exact shape |
| --- | --- |
| `FOUND` | no reason and exactly one support |
| `ABSENT` | reason `no_catalog_entry` and no support |
| `UNKNOWN` | exact non-empty reason text and no support |
| `CONFLICT` | reason `conflicting_evidence` and at least two ordered supports |

`ProjectExplainCheckedEvidence` retains target lookup, exact provider-domain
completeness, optional provider unknown reason text, and provider lookup. It
does not retain private facts, evidence objects, `source_reference`, catalog
coordinate, catalog digest, source revision, or source locator.

## Checked Status Consistency Algebra

The projected status comes directly from the inspected private
`CapabilityRequirementStatus`. Detached evidence then cross-validates it with
the already-established closed algebra:

1. either lookup `CONFLICT` -> `CONFLICT`;
2. otherwise either found support explicitly unsupported -> `UNSUPPORTED`;
3. otherwise provider lookup `ABSENT` -> `ABSENT`;
4. otherwise either lookup `UNKNOWN` -> `UNKNOWN`;
5. otherwise both lookups found supported -> `SATISFIED`;
6. otherwise reject.

This validation does not call `lookup_capability`, invoke a provider, or call
`check_package_capability_requirements`.

## Matrix Rows Cells And Ordering

Rows are dense in exact Slice 3 request order. A row repeats no capability key;
its `requirement_position` refers to the Slice 3 REQUEST authority. With a
non-empty denominator, every row has exactly one cell per target in target
order. With an empty denominator, every row has no cells.

A blocked cell has no checked status or evidence and uses its declaring
package-target evaluation's blocked posture. A checked cell has exact checked
status and evidence. Its posture is `CONFLICTING` for conflict, `UNAVAILABLE`
for unknown, and `DETERMINISTIC_DERIVATION` for satisfied, unsupported, or
absent.

An existing request row can never contain `UNDECLARED`. An undeclared private
collection created no Slice 3 request. Therefore:

```text
undeclared collection
!= declared empty collection
!= checked unknown result
```

## Declared Empty And Undeclared Packages

Every undeclared package still has one `UNDECLARED` package-target evaluation
per non-empty target and no rows. A declared zero-requirement package retains
its actual `BLOCKED` or `CHECKED` package-target evaluation and has no rows.
The two forms never collapse.

## Canonical Non-empty Projection

The canonical entry point is:

```text
_project_requirement_target_matrix(
    package_projection,
    package_facts,
    capability_facts,
)
```

It first reconstructs Slice 3 using
`_project_package_requirement_provenance(package_facts, capability_facts)` and
requires exact value equality with the supplied projection. It then validates
one fact set per package, the root-owned denominator, exact common context
identity, inspected target/profile agreement, and package by target state.

For each Slice 3 request, `declared_by` selects the exact package fact set and
`occurrence_position` selects the exact local inspected row. Collection
identity, the seven-field capability key, private row/cell positions, and the
declaring package's evaluation state must agree. No approximate text lookup,
sorting, deduplication, or fallback is used.

## Privacy And Detachment

Output retains only exact text, integers, bool, tuples, Project Explain enums,
logical paths, the Slice 3 detached references, and Slice 4 detached carriers.
It retains no inspection fact set or inspection, private matrix/context/column/
row/cell, requirement check, static profile, capability fact/evidence, lookup
result object, filesystem `Path`, AST, provider authority, or catalog authority.

Private object identity is consulted only during construction-time authority
validation. Construction performs no filesystem, network, database, runtime,
or installation operation.

## Retained Slice 5 Through 9 Ownership

| Slice | Retained owner |
| ---: | --- |
| 5 | Public extension-catalog evidence projection: catalog coordinate, target, content digest, selection, typed physical selector, matchability/exposure, and bounded source provenance |
| 6 | `PORTABLE`, `NOT_PORTABLE`, `INDETERMINATE`, definite gaps, requirement/project classification, no-target, and zero-requirement classification |
| 7 | Final payload composition, generic artifact-local cross-section references, integrity, deduplication, and cross-section ordering |
| 8 | Public JSON schema, field names, serializer, canonical UTF-8 bytes, and JSON goldens |
| 9 | Text output, project explain CLI, exit codes, and stream routing |

Slice 4 defines no public JSON key, catalog identity/digest/source projection,
portability result, generic cross-section reference, final
`ProjectExplainPayload`, serializer, renderer, text, or CLI route.

## Compatibility

Slice 4 leaves exact zero delta in Slice 2 and Slice 3 production; package
inspection; capability profiles, availability, checking, matrix, inspection,
and pure boundary; extension providers and catalogs; catalog inspection and
pure boundary; package pure boundary; Project JSON v2 and project check;
Semantic Metadata Artifact v1 and `pietto explain <file>`; public exports;
grammar, generated parser, AST, semantic model, IR, and SQL.

## Lifecycle And Slice 5 Handoff

Candidate lifecycle is:

```text
Phase 55: COMPLETED
Phase 56: COMPLETED
Phase 57: COMPLETED
Phase 58: ACTIVE
Slice 1: COMPLETED
Slice 2: COMPLETED
Slice 3: COMPLETED
Slice 4: CURRENT
Slice 5: NEXT / UNSTARTED
```

Git plus successful natural exact-head CI owns Slice 4 completion. No later
status-only commit is required.

```text
PHASE58_SLICE4_SELF_OWNED_OPEN = 0
```

Slice 5 owner is public extension-catalog evidence projection: catalog
coordinate, target, content digest, selection, typed physical selector,
matchability/exposure, and bounded source provenance.

Slice 5 remains `UNSTARTED / NOT AUTHORIZED`.
