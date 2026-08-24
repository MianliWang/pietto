# Phase 58 Slice 5 Project Explain Extension Catalog Evidence v1

## Answer And Authority

Slice 5 implements the detached extension-catalog evidence section for the
future `Project Explain Artifact v1` with marker
`pietto.project-explain.v1`.

Its sole extension-catalog truth is exact existing
`ExtensionCatalogInspectionFactSet` / `pietto.extension-catalog-inspection.v1`
authority. The canonical producer consumes and validates the supplied Slice 3
package/request projection and Slice 4 requirement/target matrix. It performs
no catalog selection, provider invocation, capability lookup, checker call,
filesystem discovery, or runtime probing.

## Private Python Surface

Production ownership is exactly:

```text
src/pietto/_project_explain/extension_catalog_evidence_projection.py
```

The module and package retain empty `__all__`. Nothing is re-exported through a
public Python root.

## Package Target Slot Authority

`extension_catalog_facts` is an exact tuple in package order × target order.
For a non-empty denominator it has exactly `package_count * target_count`
slots.

- A non-`CHECKED` package-target evaluation requires `None`.
- A checked package with no `EXTENSION_SIGNATURE` request requires `None`.
- A checked package with extension-signature requests requires one exact fact
  set whose authority context is the same exact object retained by the matching
  `CapabilityCheckingTargetContext`.

For the explicit empty Slice 4 denominator, the tuple and Slice 5 projection
are both empty. There is no sorting, deduplication, intersection, fallback, or
winner selection.

## Closed Vocabularies

| Vocabulary | Exact values |
| --- | --- |
| Type-reference kind | `pietto_logical`, `postgres_builtin`, `extension_native` |
| Entry family | `native_type`, `scalar_function`, `aggregate`, `operator`, `cast` |
| Operator arity | `unary`, `binary` |
| Selection outcome | `undeclared`, `selected`, `ambiguous`, `conflict` |
| Availability owner | `compiler`, `project` |
| Matchability | `exact_matchable`, `cataloged_unmodeled` |
| Exposure | `direct_sql_surface`, `implementation_support`, `unclassified` |
| Exact-group state | `unique`, `consistent_duplicate`, `evidence_conflict` |
| Completeness state | `complete`, `incomplete`, `conflict` |
| Completeness claim | `complete`, `incomplete` |

Unmodeled reasons mirror the exact existing eight-member
`ExtensionCatalogUnmodeledReason` vocabulary. No alias, coercion, generic
substitution, default-argument matching, nearest match, or best match exists.

## Immutable Model Inventory

Every carrier is frozen, slotted, and keyword-only.

| Carrier | Exact field order |
| --- | --- |
| `ProjectExplainExtensionCatalogReference` | `namespace`, `name`, `release` |
| `ProjectExplainExtensionCatalogTarget` | `database_family`, `database_release`, `extension_identity`, `extension_release` |
| `ProjectExplainExtensionCatalogSourceOccurrence` | `position`, `source_authority`, `source_revision`, `source_locator`, `curation` |
| `ProjectExplainExtensionCatalogSummary` | `position`, `reference`, `target`, `content_sha256`, `canonical_byte_length`, `source_occurrences` |
| `ProjectExplainExtensionCatalogTypeReference` | `kind`, `logical_name`, `logical_kind`, `physical_name`, `extension_identity` |
| `ProjectExplainExtensionCatalogCallableIdentity` | `sql_name`, `input_types` |
| `ProjectExplainExtensionCatalogOperatorIdentity` | `operator_name`, `arity`, `operand_types` |
| `ProjectExplainExtensionCatalogCastIdentity` | `source_type`, `target_type` |
| `ProjectExplainExtensionCatalogSelector` | `family`, `identity` |
| `ProjectExplainExtensionCatalogAvailabilityDeclaration` | `position`, `owner_kind`, `project_path`, `catalog_position`, `reference`, `target`, `content_sha256` |
| `ProjectExplainExtensionCatalogSelectionCandidate` | `catalog_position`, `reference`, `target`, `content_sha256`, `declaration_positions` |
| `ProjectExplainExtensionCatalogSelection` | `requested_target`, `active_project_path`, `outcome`, `evidence_posture`, `availability`, `applicable_declaration_positions`, `excluded_project_declaration_positions`, `target_declaration_positions`, `candidates`, `selected_catalog_position` |
| `ProjectExplainExtensionCatalogEntryEvidence` | `entry_position`, `entry_family`, `matchability`, `exposure`, `unmodeled_reasons`, `source_positions` |
| `ProjectExplainExtensionCatalogExactGroupEvidence` | `position`, `state`, `entries` |
| `ProjectExplainExtensionCatalogCompletenessClaim` | `position`, `kind`, `source_positions` |
| `ProjectExplainExtensionCatalogCompletenessEvidence` | `position`, `state`, `claims` |
| `ProjectExplainExtensionRequirementEvidence` | `requirement_position`, `selector`, `bridged_database_family`, `selection`, `selected_catalog_position`, `exact_group`, `unmodeled_blockers`, `completeness` |
| `ProjectExplainExtensionCatalogContextEvidence` | `package_position`, `target_position`, `collection`, `catalogs`, `requirements` |
| `ProjectExplainExtensionCatalogEvidenceProjection` | `contexts` |

The root context order is package order × target order. Empty provider contexts
are not emitted.

## Catalog Identity And Sources

Catalog positions preserve exact private inspection order. A summary retains
the exact catalog reference, database/extension target, lowercase content
SHA-256, canonical byte length, and ordered source occurrences.

Each source occurrence retains source authority, revision, curation, and one
`ProjectExplainLogicalPath(UPSTREAM_SOURCE_LOCATOR, ...)`. Host absolute paths,
cwd, home, temporary, venv, inode, and device identity are forbidden.

The projection does not publish unrelated catalog entries. Only entry evidence
referenced by one provider occurrence's exact group or unmodeled blockers is
detached.

## Typed Selector Contract

The typed physical selector remains a typed `family` plus a typed identity
carrier:

- native type → exact type reference;
- scalar function or aggregate → callable SQL name plus ordered input types;
- operator → name, exact unary/binary arity, ordered operand types;
- cast → exact source and target types.

Physical signatures are never flattened into strings. Semantic
`CapabilityKey` remains Slice 3 REQUEST authority and is not duplicated here.

## Selection Evidence

Selection retains the requested target, optional logical active project path,
all ordered availability declarations, applicable/excluded/target declaration
positions, ordered candidates, and optional selected catalog position.

Evidence posture is exact:

```text
SELECTED   -> DETERMINISTIC_DERIVATION
UNDECLARED -> UNAVAILABLE
AMBIGUOUS  -> CONFLICTING
CONFLICT   -> CONFLICTING
```

Ambiguous and conflicting results have no winner. There is no preferred,
latest, nearest, fallback, or arbitrary candidate.

## Relevant Entry Evidence

Relevant evidence retains entry position/family, exact matchability, exposure,
unmodeled reasons, and ordered selected-catalog source positions.

`CATALOGED_UNMODELED` remains cataloged-unmodeled. It never becomes `ABSENT` or
`UNSUPPORTED`. Exposure remains independently
`DIRECT_SQL_SURFACE`, `IMPLEMENTATION_SUPPORT`, or `UNCLASSIFIED`.

Exact groups retain their catalog group position, exact group state, and only
the group entries. Evidence conflict retains every conflicting entry in catalog
order.

## Completeness Evidence

A present completeness group retains its catalog position, exact
`COMPLETE`/`INCOMPLETE`/`CONFLICT` state, and ordered relevant claims. Each
claim retains its global catalog claim position, kind, and ordered source
positions.

Absence of a group represents unavailable completeness authority. No global
catalog-completeness statement is invented.

## Requirement Mapping And Slice 4 Agreement

Each provider occurrence maps its package-local requirement position through
Slice 3 `declared_by` plus `occurrence_position` to one global REQUEST position.
Collection identity, seven semantic key fields, typed selector occurrence, and
the frozen `postgresql` → `PostgreSQL` bridge must agree.

The corresponding Slice 4 cell must be `CHECKED`. The extension inspection,
private capability check, and detached Slice 4 generic provider evidence must
agree exactly on provider completeness, unknown reason, lookup variant, lookup
reason, and ordered support postures. This is consistency validation only and
does not recompute provider truth.

## Privacy And Detachment

Output contains only exact strings, bools, non-negative positions, tuples,
Project Explain carriers/enums, logical paths, and SHA-256 text. It retains no
inspection fact set, private inspection, provider context, selection result,
constructed catalog/entry, capability fact/evidence, private lookup,
`ProjectRoot`, filesystem `Path`, or runtime handle.

## Retained Later Ownership

Slice 6 retains every portability classification and derivation. Slice 7
retains final payload composition, generic artifact-local references, evidence
links, deduplication, and cross-section integrity. Slice 8 retains JSON schema,
field names, serializer, canonical UTF-8 bytes, and goldens. Slice 9 retains
text rendering, project explain CLI, exit codes, and streams.

Slice 5 adds none of those surfaces.

## Compatibility

Slice 5 leaves exact zero delta in Slice 2–4 production, package/capability/
catalog authorities, provider/checker/lookup behavior, Project JSON v2, project
check, Semantic Metadata Artifact v1, existing single-file explain, public
exports, grammar, generated parser, AST, semantics, IR, and SQL.

## Lifecycle And Slice 6 Handoff

Candidate documentation state is Phase 58 active, Slices 1–4 completed, Slice
5 current, and Slice 6 next/unstarted. Git plus successful natural exact-head
CI owns Slice 5 completion; no later status-only commit is required.

```text
PHASE58_SLICE5_SELF_OWNED_OPEN = 0
```

Slice 6 owns conservative requirement/project portability derivation.
Slice 6 remains `UNSTARTED / NOT AUTHORIZED`.
