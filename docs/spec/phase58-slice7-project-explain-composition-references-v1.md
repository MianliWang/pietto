# Phase 58 Slice 7 Project Explain Composition And References v1

## Answer And Authority

Slice 7 composes the already-detached Slice 3 through Slice 6 sections into the
final in-memory `ProjectExplainPayload` for `Project Explain Artifact v1`.
The machine marker remains `pietto.project-explain.v1`.

The four inputs remain independent authorities:

```text
Slice 3 ProjectExplainPackageRequirementProjection
Slice 4 ProjectExplainRequirementTargetMatrix
Slice 5 ProjectExplainExtensionCatalogEvidenceProjection
Slice 6 ProjectExplainProjectPortability
```

Composition retains those exact values. It neither copies their contents into
parallel tables nor reconstructs private package, capability, or catalog
authority.

## Private Python Surface

Production ownership is exactly:

```text
src/pietto/_project_explain/composition.py
```

The module and package retain empty `__all__`. No symbol is re-exported through
a public Python root.

The canonical pure entry points are:

```text
_compose_project_explain_payload(
    package_requirements,
    compatibility,
    extension_catalog_evidence,
    portability,
)

_resolve_project_explain_reference(payload, reference)
```

Both operate only on detached immutable values.

## Final Payload

`ProjectExplainPayload` is a frozen, slotted, keyword-only dataclass with exact
field order:

```text
package_requirements
compatibility
extension_catalog_evidence
portability
requirement_explanations
```

The first four fields retain the exact supplied Slice 3 through Slice 6 roots.
`requirement_explanations` is an exact tuple with one explanation per Slice 3
requirement in exact requirement order.

The existing generic `ProjectExplainEnvelope[ProjectExplainPayload]` is the
future success envelope. Slice 7 changes no Slice 2 envelope semantics.

## Artifact-Local Reference Vocabulary

References use deterministic artifact-local coordinates only.

| Kind | Value | Exact positions |
| --- | --- | --- |
| `PACKAGE` | `package` | `(package_position,)` |
| `REQUIREMENT` | `requirement` | `(requirement_position,)` |
| `TARGET` | `target` | `(target_position,)` |
| `PACKAGE_TARGET_EVALUATION` | `package_target_evaluation` | `(package_position, target_position)` |
| `MATRIX_CELL` | `matrix_cell` | `(requirement_position, target_position)` |
| `EXTENSION_CATALOG_CONTEXT` | `extension_catalog_context` | `(package_position, target_position)` |
| `EXTENSION_CATALOG` | `extension_catalog` | `(package_position, target_position, catalog_position)` |
| `EXTENSION_CATALOG_SOURCE` | `extension_catalog_source` | `(package_position, target_position, catalog_position, source_position)` |
| `EXTENSION_REQUIREMENT_EVIDENCE` | `extension_requirement_evidence` | `(package_position, target_position, requirement_position)` |
| `REQUIREMENT_PORTABILITY` | `requirement_portability` | `(requirement_position,)` |
| `PROJECT_PORTABILITY` | `project_portability` | `()` |

`ProjectExplainArtifactReference` has exact fields `kind`, `positions`.
Positions are exact non-negative integers with bool rejected. Each kind has one
exact arity.

References are not UUIDs, hashes, persistent/global IDs, database keys, object
identities, or graph nodes.

## Exact Reference Resolution

The resolver indexes package, requirement, target, matrix, and portability
tuples only by their exact positions. Package-target evaluation uses the
existing package-major by target-major tuple. Matrix cells use exact
requirement row by target cell positions.

Extension context resolution requires exactly one matching package/target
context. Catalogs and source occurrences resolve by their exact context-local
positions. Extension requirement evidence requires exactly one matching
global Slice 3 requirement position within the exact context.

Zero matches, multiple matches, wrong arity, malformed order, or out-of-range
coordinates fail closed. There is no semantic-key search, approximate match,
or fallback.

## Bounded Requirement Explanation

The public conceptual route remains:

```text
REQUEST -> RESOLUTION -> RESULT
```

`ProjectExplainRequirementTargetExplanation` has exact field order:

```text
target
evaluation
matrix_cell
extension_evidence
source_evidence
```

`ProjectExplainRequirementExplanation` has exact field order:

```text
request
declared_by
requested_by
targets
portability
```

For requirement `r`, `request` is `REQUIREMENT(r)`, `declared_by` and
`requested_by` name the exact Slice 3 package positions, and `portability` is
`REQUIREMENT_PORTABILITY(r)`. This retains only the bounded root/project to
declaring package to requirement occurrence explanation.

For target `t`, the explanation names `TARGET(t)`, the declaring package's
`PACKAGE_TARGET_EVALUATION(declared_by, t)`, and `MATRIX_CELL(r, t)`. Matrix
cell state must agree with the already-authoritative Slice 4 package-target
evaluation. No capability check is rerun.

An empty target denominator retains request, package, and portability links
while `targets == ()`.

## Extension Evidence Completeness

Every Slice 5 context must name existing package and target positions, retain
strict package by target order, name the declaring package's exact Slice 3
collection, and contain only global `EXTENSION_SIGNATURE` requirements whose
Slice 4 cells are `CHECKED`.

Conversely, every checked Slice 3 extension-signature requirement by target
has exactly one matching Slice 5 requirement evidence record. A blocked
extension cell and every non-extension requirement have no extension evidence.
Missing, duplicate, reordered, foreign-package, foreign-target, blocked, or
non-extension evidence fails closed.

Slice 5 evidence explains Slice 4 results. It cannot upgrade, downgrade, or
otherwise change Slice 6 portability.

## Source Evidence And Reference Deduplication

For linked selected-catalog evidence, source positions come only from exact
group entries, unmodeled blocker entries, and completeness claims already
retained by Slice 5.

The composer determines referenced `(catalog_position, source_position)`
coordinates, then walks catalogs in catalog order and source occurrences in
source-occurrence order. It emits each coordinate once. This is
reference-level deduplication only.

Duplicate references collapse, while the underlying catalog source occurrences
retain their exact values, order, positions, and multiplicity. Packages,
requirements, targets, matrix cells, catalogs, and source occurrences are not
deduplicated. No set or dictionary iteration order is observable.

An unselected ambiguous or conflicting selection has no selected-catalog
source reference. No source evidence is fabricated.

## Portability Equality

Before composition, supplied portability must equal exactly:

```text
_derive_project_portability(package_requirements, compatibility)
```

This is a cross-section integrity check using the existing Slice 6 canonical
derivation, not a new portability algorithm. `PROJECT_PORTABILITY(())` resolves
to the retained project portability root.

## Authority Separation And Privacy

The payload keeps package/request, compatibility/matrix, extension catalog,
and portability sections distinct. Capability keys, evaluated profiles,
catalog targets, catalog coordinates, content digests, and source occurrences
remain separate identities. Reference equality does not merge them.

Composition retains no private inspection fact set, provider context, private
matrix, filesystem path object, runtime handle, database connection, network
authority, global graph identity, or installation claim. It performs no file,
network, database, package-loading, checking, provider, selection, or
serialization operation.

## Retained Later Ownership

Slice 8 retains public JSON v1 schema, exact field names, optional/required
policy, enum serialization, canonical UTF-8 bytes, success/failure JSON,
goldens, and schema-evolution locks. Slice 8 remains
`UNSTARTED / NOT AUTHORIZED`.

Slice 9 retains `pietto explain --project`, text rendering, `--format json`,
exit codes, stdout/stderr, and single-file explain compatibility. Slice 10
retains real multi-target E2E scenarios.

Phase 59 retains the provenance and lineage graph, cross-artifact attribution,
and global graph nodes/edges. Slice 7 references are not Phase 59 IDs.

## Compatibility

Slice 7 leaves Slice 2 through Slice 6 production values unchanged. It changes
no public export, JSON, text, CLI, parser, AST, semantics, IR, SQL, package or
catalog authority, provider/checker behavior, generated artifact, golden,
dependency, lockfile, version, workflow, tag, Release, signing, attestation, or
package-publication behavior.

## Lifecycle And Slice 8 Handoff

Candidate lifecycle is Phase 58 active, Slices 1 through 6 completed, Slice 7
current, and Slice 8 next/unstarted. Git plus successful natural exact-head CI
owns Slice 7 completion; no later status-only commit is required.

```text
PHASE58_SLICE7_SELF_OWNED_OPEN = 0
```

Slice 8 remains `UNSTARTED / NOT AUTHORIZED`.
