# Phase 58 Slice 8 Project Explain JSON v1

## Answer And Scope

This Slice establishes the stable public machine representation for Project
Explain Artifact v1. The exact format marker is
`pietto.project-explain.v1`. The success payload is the existing Slice 7
`ProjectExplainPayload`; no JSON-only payload model exists.

The implementation is private in
`src/pietto/_project_explain/json_v1.py` and is not re-exported. It serializes
already composed detached values only. It performs no project discovery,
compilation, checking, catalog construction, filesystem access, network
access, database access, or private-authority reconstruction.

## Canonical Entry Points

There is one canonical JSON-value builder and one canonical byte serializer:

```text
project_explain_envelope_to_json_value(envelope) -> dict[str, object]
serialize_project_explain_json_document(envelope) -> bytes
```

The accepted value is an exact
`ProjectExplainEnvelope[ProjectExplainPayload]`. Before a success is
serialized, the implementation reconstructs the canonical Slice 7 value with
`_compose_project_explain_payload` from the supplied Slice 3–6 sections and
requires exact value equality. A failure has no payload and serializes no
partial facts.

## Closed Envelope

The exact top-level member order is:

```text
format ok diagnostics payload
```

`format` is the exact marker, `ok` is a JSON Boolean, `diagnostics` is the
ordered diagnostic array, and `payload` is the complete object on success or
JSON `null` on failure. A success may contain warning diagnostics but no error.
A failure contains at least one error diagnostic. No `artifact`,
`schema_version`, `command`, `metadata`, `error`, `cli_errors`, or alternate
envelope member is present.

## Explicit Carrier Inventory

The schema has exactly 49 serialized dataclass carriers. JSON member names are
the existing snake_case field names, and member order is the listed dataclass
field order.

| Carrier | Exact fields in order |
| --- | --- |
| `ProjectExplainLogicalPath` | `kind`, `value` |
| `ProjectExplainLocation` | `path`, `line`, `column`, `end_line`, `end_column` |
| `ProjectExplainDiagnostic` | `code`, `severity`, `message`, `location`, `suggestion` |
| `ProjectExplainEnvelope` | `format`, `ok`, `diagnostics`, `payload` |
| `ProjectExplainPackageCoordinate` | `namespace`, `name`, `release` |
| `ProjectExplainPackageAsset` | `position`, `kind`, `path` |
| `ProjectExplainDirectDependency` | `position`, `target_package_position`, `coordinate`, `content_digest_pin`, `locator_kind`, `project_path` |
| `ProjectExplainPackage` | `position`, `role`, `coordinate`, `project_path`, `content_digest`, `assets`, `dependencies` |
| `ProjectExplainRequirementCollectionIdentity` | `namespace`, `name` |
| `ProjectExplainCapabilityKey` | `domain`, `subject`, `operation`, `operands`, `context`, `dialect`, `extension` |
| `ProjectExplainRequirementCollection` | `declared_by`, `requested_by`, `package_role`, `identity`, `requirement_positions` |
| `ProjectExplainRequirementRequest` | `position`, `stage`, `declared_by`, `requested_by`, `package_role`, `collection`, `occurrence_position`, `key` |
| `ProjectExplainPackageRequirementProjection` | `root_package_position`, `packages`, `requirement_collections`, `requirements` |
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
| `ProjectExplainDefiniteGap` | `target_position`, `status` |
| `ProjectExplainRequirementPortability` | `requirement_position`, `classification`, `reason`, `definite_gaps` |
| `ProjectExplainProjectPortability` | `classification`, `reason`, `requirements_evaluated`, `requirements` |
| `ProjectExplainArtifactReference` | `kind`, `positions` |
| `ProjectExplainRequirementTargetExplanation` | `target`, `evaluation`, `matrix_cell`, `extension_evidence`, `source_evidence` |
| `ProjectExplainRequirementExplanation` | `request`, `declared_by`, `requested_by`, `targets`, `portability` |
| `ProjectExplainPayload` | `package_requirements`, `compatibility`, `extension_catalog_evidence`, `portability`, `requirement_explanations` |

Each carrier has a dedicated explicit mapping function. Production does not use
`dataclasses.asdict`, `dataclasses.fields`, `vars`, `__dict__`, `inspect`,
`repr`, `pickle`, `jsonpickle`, `default=str`, or generic recursive object
serialization. Tests use `dataclasses.fields` only to lock the inventory.

## Primitive Null And Array Rules

Existing enum values become their exact lowercase `.value` strings. Exact
strings, Booleans, and integers remain their JSON primitive types. `None`
becomes `null`. Every tuple becomes an array in exact tuple order. No float,
set, unordered mapping, object identity, hash, or allocation order is emitted.

Every schema field is present. An absent optional scalar or object is `null`,
an empty tuple is `[]`, and an empty string remains an empty string when the
carrier permits one. Optional keys are never omitted.

## Typed Selectors

`ProjectExplainExtensionCatalogSelector` remains an object with `family` then
`identity`. The family is the discriminator. The identity is the exact field
object of the existing native-type, callable, operator, or cast carrier.
Scalar-function and aggregate families use the callable identity shape. No
Python class name, `type` member, stringification, or flattened selector is
emitted.

## Artifact-local References

Every `ProjectExplainArtifactReference` has `kind` then `positions`. Kinds use
the exact lowercase enum values. Position arities in kind order are
`1, 1, 1, 2, 2, 2, 3, 4, 3, 1, 0`; `project_portability` therefore emits
`positions: []`. References are not JSON Pointers, URLs, UUIDs, hashes, or
graph IDs.

## Diagnostics And Logical Paths

A diagnostic has `code`, `severity`, `message`, `location`, and `suggestion`.
A location is `null` or an object with `path`, `line`, `column`, `end_line`, and
`end_column`. A present path is the full `kind` plus `value` logical-path
object, retaining `project_relative`, `package_relative`, or
`upstream_source_locator` identity.

Host absolute paths, cwd, home and temporary directories, virtual
environments, symlink-resolved identity, and device/inode identity cannot
enter through the logical-path models. Serialization performs no path
normalization or filesystem access.

## Ordering

Arrays retain the already composed semantic order: package order, requirement
order, evaluated-target order, package by target evaluation order, matrix-cell
target order, catalog and source order, explanation order, and Slice 7
source-reference dedup order. Slice 8 performs no sorting or deduplication.

## Deterministic UTF-8 Bytes

The standard-library encoder uses exactly:

```text
ensure_ascii=False
allow_nan=False
sort_keys=False
separators=(",", ":")
```

Explicit dict construction owns object-member order. The serializer appends
one final LF and encodes once as UTF-8, with no BOM, indentation, extra
whitespace, or second document. Unicode is not normalized or case-folded;
precomposed and decomposed strings remain distinct. A lone surrogate or any
other value that cannot form UTF-8 fails closed without replacement.

## Validation And Failure

Serialization rejects a non-exact envelope, the wrong marker, a non-exact
success payload, a noncanonical Slice 7 composition, a success without a
payload, a failure with a payload, an error-bearing success, an error-free
failure, an unexpected carrier subclass or private authority, a selector
family/identity disagreement, and invalid UTF-8. No exception becomes fallback
JSON and no missing field or diagnostic is fabricated.

## Byte-exact Goldens

The manually reviewed fixtures are:

```text
tests/fixtures/golden/project_explain_v1_success.json
tests/fixtures/golden/project_explain_v1_failure.json
```

The success fixture contains a composed extension-signature payload, ordered
catalog/source evidence, artifact-local references, a warning, logical-path
location, and distinct Unicode spellings. The failure fixture contains one
test-owned error diagnostic and `payload: null`.

`scripts/check_goldens.py` classifies exactly these two files in
`MODEL_JSON_FIXTURES`, a strict subset of `JSON_FIXTURES`. Only that bounded
category is exempt from `FIXTURE_INPUTS`; all existing input-derived fixtures
retain their mappings. The owning Slice 8 test is in `REFERENCE_TESTS`, and
missing, orphaned, unclassified, invalid-JSON, and unexpected input-mapping
checks remain fail closed.

## Schema Evolution

Within v1, field removal or rename, field type change, required-field addition,
enum or semantic change, null/object/array change, array-order change,
reference-kind or arity change, and existing-field repurposing are breaking.
A breaking change requires a new explicit marker. No optional field or numeric
schema version is added in this Slice. The normative schema is this contract,
the explicit serializer, executable tests, and the two byte-exact goldens; no
JSON Schema Draft file is introduced.

## Compatibility And Retained Ownership

Slices 2–7 carriers and behavior remain unchanged. Existing CLI JSON v1,
Semantic Metadata Artifact v1, Project JSON v2, project check, single-file
explain, package/capability/catalog authorities, parser, AST, semantics, IR,
SQL, public Python exports, routing, stderr/stdout, and exit codes remain exact
zero-delta.

Slice 9 remains unstarted and retains CLI integration, text rendering,
stdout/stderr, and exit-code ownership. Slice 10 retains real multi-target E2E,
Slice 11 retains the pure/differential and version/hash-seed/relocation/wheel
boundary, and Phase 59 retains provenance graphs.

`PHASE58_SLICE8_SELF_OWNED_OPEN = 0`.
