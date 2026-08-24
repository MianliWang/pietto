# Phase 58 Slice 6 Project Explain Portability Derivation v1

## Answer And Authority

Slice 6 implements the conservative requirement and project portability
summary for the future `Project Explain Artifact v1`. The artifact marker
remains `pietto.project-explain.v1`.

The sole normative portability input is the already-detached Slice 4
`ProjectExplainRequirementTargetMatrix`. Slice 3 remains exact REQUEST
authority. Slice 5 remains explanatory catalog evidence and cannot alter a
classification.

## Private Python Surface

Production ownership is exactly:

```text
src/pietto/_project_explain/portability_projection.py
```

The module and package retain empty `__all__`. Nothing is re-exported through a
public Python root.

The canonical pure producer is:

```text
_derive_project_portability(
    package_projection,
    matrix_projection,
)
```

It consumes exact Slice 3 and Slice 4 detached values only. It performs no
filesystem, network, database, runtime, package, profile, provider, checker,
lookup, or catalog operation.

## Closed Vocabularies

Classification is exactly:

```text
PORTABLE = "portable"
NOT_PORTABLE = "not_portable"
INDETERMINATE = "indeterminate"
```

The only bounded reason is:

```text
NO_EVALUATED_TARGETS = "no-evaluated-targets"
```

There is no partial, mostly, conditional, best-target, worst-target, ranking,
recommendation, percentage, or score vocabulary.

## Immutable Model Inventory

Every carrier is a frozen, slotted, keyword-only dataclass.

| Carrier | Exact field order |
| --- | --- |
| `ProjectExplainDefiniteGap` | `target_position`, `status` |
| `ProjectExplainRequirementPortability` | `requirement_position`, `classification`, `reason`, `definite_gaps` |
| `ProjectExplainProjectPortability` | `classification`, `reason`, `requirements_evaluated`, `requirements` |

Positions and counts are exact non-negative integers with bool rejected.
Collections are exact tuples. Requirement positions are dense and ordered.
Gap positions retain strict target order.

## Definite Gaps

Only these checked statuses are definite gaps:

```text
CHECKED / UNSUPPORTED
CHECKED / ABSENT
```

`UNKNOWN`, `CONFLICT`, and `BLOCKED` are not gaps. An undeclared collection
produced no Slice 3 request and therefore no public requirement row.

Every gap retains exact target position and exact `UNSUPPORTED` or `ABSENT`
status. Gap order and multiplicity follow the target cells. Gaps are not
sorted, normalized, collapsed, or deduplicated.

## Requirement Algebra

For one requirement row over the exact evaluated target denominator:

1. an empty denominator is `INDETERMINATE / NO_EVALUATED_TARGETS`;
2. otherwise any definite gap makes the result `NOT_PORTABLE`;
3. otherwise all cells `CHECKED / SATISFIED` makes it `PORTABLE`;
4. otherwise it is `INDETERMINATE`.

Definite-gap precedence is exact. `UNSUPPORTED + UNKNOWN`,
`ABSENT + CONFLICT`, and `UNSUPPORTED + BLOCKED` remain `NOT_PORTABLE`.
Without a definite gap, `UNKNOWN`, `CONFLICT`, or `BLOCKED` remains
`INDETERMINATE`; no checked `UNKNOWN` is fabricated for a blocked cell.

## Project Algebra

An empty target denominator is always
`INDETERMINATE / NO_EVALUATED_TARGETS`, including when there are zero
requirements. This forbids vacuous portability over no evaluated target.

For a non-empty denominator, zero requirements is `PORTABLE` with
`requirements_evaluated == 0`. Otherwise aggregation is exact:

1. any `NOT_PORTABLE` requirement makes the project `NOT_PORTABLE`;
2. otherwise any `INDETERMINATE` requirement makes it `INDETERMINATE`;
3. otherwise the project is `PORTABLE`.

No averaging or scoring is performed.

## Cross-Slice Integrity

Before derivation, the producer requires exact Slice 3 and Slice 4 root types.
The row count must equal the Slice 3 requirement count. Each row position must
name the exact same-position Slice 3 request. Evaluated targets are dense, each
non-empty row has exactly one cell per target, and cell positions equal exact
target order.

The existing Slice 4 detached reference validation remains authoritative for
package-by-target coverage and declaring-package cell state. Slice 6 does not
reconstruct private package or capability authority and does not make a second
matrix copy.

## Model Integrity

The carriers reject inconsistent hand construction. `PORTABLE` forbids a
reason or gaps. `NOT_PORTABLE` requires at least one gap and forbids a reason.
`INDETERMINATE` forbids gaps. A no-target project requires matching
no-target indeterminate requirement rows. A normal project forbids reasoned
rows and must exactly aggregate its requirement classifications.

Denominator-dependent reason correctness is enforced by the canonical root:
empty-target results carry `NO_EVALUATED_TARGETS`; non-empty-target results do
not.

## Slice 5 Independence

The producer neither imports nor consumes
`ProjectExplainExtensionCatalogEvidenceProjection`. Catalog evidence can
explain an existing Slice 4 result but cannot upgrade or downgrade
`SATISFIED`, `UNSUPPORTED`, `ABSENT`, `UNKNOWN`, `CONFLICT`, or `BLOCKED`.

In particular, cataloged-unmodeled evidence can explain a normative Slice 4
`UNKNOWN`, while Slice 6 still derives only from that `UNKNOWN` cell.

## Retained Later Ownership

Slice 7 retains final payload composition, generic artifact-local references,
cross-section references and integrity, evidence links, ordering, and final
deduplication. Slice 8 retains public JSON v1 field names, schema, serializer,
canonical UTF-8 bytes, and goldens. Slice 9 retains text rendering, project
explain CLI behavior, exit codes, and stream routing.

Slice 6 defines none of those surfaces.

## Compatibility

Slice 6 leaves exact zero delta in Slice 2 through Slice 5 production,
package/capability/catalog authorities and behavior, public exports, Project
JSON v2 and project check, Semantic Metadata Artifact v1 and single-file
explain, grammar, generated parser, AST, semantics, IR, and SQL.

## Lifecycle And Slice 7 Handoff

Candidate lifecycle is Phase 58 active, Slices 1 through 5 completed, Slice 6
current, and Slice 7 next/unstarted. Git plus successful natural exact-head CI
owns Slice 6 completion; no later status-only commit is required.

```text
PHASE58_SLICE6_SELF_OWNED_OPEN = 0
```

Slice 7 owns final cross-section composition, generic artifact-local
references, integrity, ordering, authority separation, and evidence links.
Slice 7 remains `UNSTARTED / NOT AUTHORIZED`.
