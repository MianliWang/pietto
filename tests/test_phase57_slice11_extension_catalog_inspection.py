from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
import hashlib
import inspect
from pathlib import Path
from typing import Any, cast

import pytest

import _pietto_capability_differential_vectors as vectors
import pietto
import pietto._project as project_package
import pietto._project.capability_inspection as capability_inspection
import pietto._project.extension_catalog_inspection as inspection_module
import pietto._project.package_inspection as package_inspection
import pietto.semantic as semantic_package
import test_phase57_slice5_extension_catalog_construction_completeness_canonical as slice5
import test_phase57_slice6_extension_catalog_declaration_availability_selection as slice6
import test_phase57_slice8_extension_signature_provider_checking_integration as slice8
from pietto._project.capability_inspection import CapabilityInspectionFormat
from pietto._project.capability_pure_boundary import CapabilityPureStatus
from pietto._project.extension_catalog_availability import (
    DeclaredExtensionCatalogAvailability,
    ExtensionCatalogAvailabilityOwner,
    ExtensionCatalogSelectionOutcome,
    ExtensionCatalogSelectionResult,
    select_extension_catalog,
)
from pietto._project.extension_catalog_inspection import (
    ExtensionCatalogInspection,
    ExtensionCatalogInspectionAggregateEntry,
    ExtensionCatalogInspectionCatalog,
    ExtensionCatalogInspectionCastEntry,
    ExtensionCatalogInspectionFactSet,
    ExtensionCatalogInspectionFormat,
    ExtensionCatalogInspectionLookupVariant,
    ExtensionCatalogInspectionNativeTypeEntry,
    ExtensionCatalogInspectionOperatorEntry,
    ExtensionCatalogInspectionScalarFunctionEntry,
    build_extension_catalog_inspection,
)
from pietto._project.extension_signature_provider import (
    ExtensionSignatureProviderContext,
    ExtensionSignatureProviderSelectionOccurrence,
)
from pietto._project.model import ProjectRoot
from pietto._project.package_inspection import PackageInspectionFormat
from pietto.semantic.capability_facts import (
    CapabilityDomain,
    CapabilityReasonCode,
    CapabilitySupport,
    CapabilityKey,
)
from pietto.semantic.capability_profiles import (
    CapabilityRequirementCollection,
    CapabilityRequirementCollectionIdentity,
    CapabilityRequirementOccurrence,
)
from pietto.semantic.extension_catalog import (
    ConstructedExtensionCatalog,
    ExtensionCatalogCompletenessClaim,
    ExtensionCatalogCompletenessClaimKind,
    ExtensionCatalogCompletenessState,
    ExtensionCatalogDeclarationTypeUseKind,
    ExtensionCatalogEntryFamily,
    ExtensionCatalogExactEntryGroupState,
    ExtensionCatalogExposure,
    ExtensionCatalogLookupScope,
    ExtensionCatalogMatchability,
    ExtensionCatalogTypeReference,
    ExtensionCatalogTypeReferenceKind,
    ExtensionCatalogUnmodeledReason,
    PostgreSQLCallableIdentity,
)
from pietto.semantic.extension_catalog_pg_trgm import (
    PG_TRGM_V16_POSTGRESQL18_CATALOG,
)
from pietto.semantic.extension_catalog_pgvector import (
    PGVECTOR_V086_POSTGRESQL18_CATALOG,
)
from pietto.semantic.extension_signature_requirements import (
    ExtensionSignatureRequirementSelector,
    ExtensionSignatureRequirementSelectorOccurrence,
    ExtensionSignatureRequirementSelectors,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "docs/spec/phase57-extension-catalog-inspection-v1.md"
ROADMAP = REPO_ROOT / "docs/roadmap.md"
STATUS = REPO_ROOT / "docs/status.md"
PACKAGE_SMOKE = REPO_ROOT / "scripts/package_smoke.py"
EXPECTED_INSPECTION_BYTES = 540042
EXPECTED_INSPECTION_SHA256 = (
    "7710033bd7b1b939bee3f3da1f4d354b7d53db385a36e61f538bc4aacf8fb4ce"
)
EXPECTED_PGVECTOR_SHA256 = (
    "686e68fe9d60c20cb276e2b26007d310ff8877a5b4a8274e5c9194116fa74654"
)
EXPECTED_PG_TRGM_SHA256 = (
    "09eb10a0660a05ca180d43a23f1eda7aaf4b6198f5de249591317194cc9576b7"
)
EXPECTED_CORPUS_DIGEST = (
    "8453c3babda888b105f37f667f5fadf3a12aa68ca9a561bda98e5f6b6604a69e"
)


def _builtin(name: str) -> ExtensionCatalogTypeReference:
    return ExtensionCatalogTypeReference(
        ExtensionCatalogTypeReferenceKind.POSTGRES_BUILTIN,
        physical_name=name,
    )


def _native(name: str, owner: str) -> ExtensionCatalogTypeReference:
    return ExtensionCatalogTypeReference(
        ExtensionCatalogTypeReferenceKind.EXTENSION_NATIVE,
        physical_name=name,
        extension_identity=owner,
    )


def _scalar_scope(
    name: str,
    *inputs: ExtensionCatalogTypeReference,
) -> ExtensionCatalogLookupScope:
    return ExtensionCatalogLookupScope(
        ExtensionCatalogEntryFamily.SCALAR_FUNCTION,
        PostgreSQLCallableIdentity(name, inputs),
    )


def _key(
    name: str,
    *,
    extension: str,
    operation: str = "exact signature",
) -> CapabilityKey:
    return CapabilityKey(
        CapabilityDomain.EXTENSION_SIGNATURE,
        subject=name,
        operation=operation,
        operands=("semantic", "text", "only"),
        context="typed selector is separate",
        dialect="postgresql",
        extension=extension,
    )


def _requirements(
    *keys: CapabilityKey,
    name: str = "slice11",
) -> CapabilityRequirementCollection:
    identity = CapabilityRequirementCollectionIdentity("consumer", name)
    return CapabilityRequirementCollection(
        identity,
        tuple(
            CapabilityRequirementOccurrence(identity, position, key)
            for position, key in enumerate(keys)
        ),
    )


def _context(
    requirements: CapabilityRequirementCollection,
    *bindings: tuple[
        int,
        ExtensionCatalogLookupScope,
        ExtensionCatalogSelectionResult,
    ],
) -> ExtensionSignatureProviderContext:
    return ExtensionSignatureProviderContext(
        ExtensionSignatureRequirementSelectors(
            requirements,
            tuple(
                ExtensionSignatureRequirementSelectorOccurrence(
                    position,
                    ExtensionSignatureRequirementSelector(scope),
                )
                for position, scope, _selection in bindings
            ),
        ),
        tuple(
            ExtensionSignatureProviderSelectionOccurrence(position, selection)
            for position, _scope, selection in bindings
        ),
    )


def _production_context(
    *,
    rebuild: bool = False,
    reverse_allocation: bool = False,
) -> ExtensionSignatureProviderContext:
    if rebuild and reverse_allocation:
        pg_trgm = inspection_module_for_test_pg_trgm()
        pgvector = inspection_module_for_test_pgvector()
    elif rebuild:
        pgvector = inspection_module_for_test_pgvector()
        pg_trgm = inspection_module_for_test_pg_trgm()
    else:
        pgvector = PGVECTOR_V086_POSTGRESQL18_CATALOG
        pg_trgm = PG_TRGM_V16_POSTGRESQL18_CATALOG
    availability = slice6._availability(
        (ExtensionCatalogAvailabilityOwner.COMPILER, pgvector, None),
        (ExtensionCatalogAvailabilityOwner.COMPILER, pg_trgm, None),
    )
    vector_selection = select_extension_catalog(availability, pgvector.metadata.target)
    trgm_selection = select_extension_catalog(availability, pg_trgm.metadata.target)
    requirements = _requirements(
        _key("pgvector direct", extension="vector"),
        _key("pg_trgm direct", extension="pg_trgm"),
        _key("pg_trgm unmodeled", extension="pg_trgm"),
        _key("pg_trgm support", extension="pg_trgm"),
        name="production-golden",
    )
    vector = _native("vector", "vector")
    text = _builtin("text")
    return _context(
        requirements,
        (
            0,
            _scalar_scope("l2_distance", vector, vector),
            vector_selection,
        ),
        (1, _scalar_scope("similarity", text, text), trgm_selection),
        (2, _scalar_scope("show_trgm", text), trgm_selection),
        (3, _scalar_scope("similarity_op", text, text), trgm_selection),
    )


def inspection_module_for_test_pgvector() -> ConstructedExtensionCatalog:
    import pietto.semantic.extension_catalog_pgvector as module

    return module._build_pgvector_catalog()


def inspection_module_for_test_pg_trgm() -> ConstructedExtensionCatalog:
    import pietto.semantic.extension_catalog_pg_trgm as module

    return module._build_pg_trgm_catalog()


def _inspection(
    context: ExtensionSignatureProviderContext,
) -> ExtensionCatalogInspectionFactSet:
    return build_extension_catalog_inspection(context)


def _catalog(
    inspection: ExtensionCatalogInspection,
    extension: str,
) -> ExtensionCatalogInspectionCatalog:
    return next(
        catalog
        for catalog in inspection.catalogs
        if catalog.target.extension_identity == extension
    )


def _corpus_digest() -> str:
    return slice5._corpus_digest()


def test_format_root_authority_and_two_production_catalogs_are_exact() -> None:
    fact_set = _inspection(_production_context())
    inspected = fact_set.inspection
    assert inspected.format is (
        ExtensionCatalogInspectionFormat.EXTENSION_CATALOG_INSPECTION_V1
    )
    assert inspected.format.value == "pietto.extension-catalog-inspection.v1"
    assert CapabilityInspectionFormat.CAPABILITY_INSPECTION_V1.value == (
        "pietto.capability-inspection.v1"
    )
    assert PackageInspectionFormat.PACKAGE_INSPECTION_V1.value == (
        "pietto.package-inspection.v1"
    )
    assert (inspected.requirement_namespace, inspected.requirement_name) == (
        "consumer",
        "production-golden",
    )
    assert tuple(
        (catalog.reference.name, catalog.target.extension_identity)
        for catalog in inspected.catalogs
    ) == (("pg_trgm", "pg_trgm"), ("pgvector", "vector"))
    assert len(inspected.provider_occurrences) == 4
    assert inspected.context is fact_set.authority.context


def test_catalog_artifacts_sources_entries_groups_and_completeness_are_lossless() -> (
    None
):
    inspected = _inspection(_production_context()).inspection
    vector = _catalog(inspected, "vector")
    trgm = _catalog(inspected, "pg_trgm")
    assert (
        vector.reference.namespace,
        vector.reference.name,
        vector.reference.release,
        vector.target.database_family,
        vector.target.database_release,
        vector.target.extension_identity,
        vector.target.extension_release,
        vector.content_sha256,
        vector.canonical_byte_length,
        len(vector.source_occurrences),
        len(vector.entries),
        len(vector.exact_entry_groups),
        len(vector.completeness_claims),
        len(vector.completeness_groups),
    ) == (
        "pietto.postgresql",
        "pgvector",
        "1",
        "PostgreSQL",
        "18",
        "vector",
        "0.8.6",
        EXPECTED_PGVECTOR_SHA256,
        993469,
        4,
        184,
        131,
        0,
        0,
    )
    assert (
        trgm.reference.namespace,
        trgm.reference.name,
        trgm.reference.release,
        trgm.target.database_family,
        trgm.target.database_release,
        trgm.target.extension_identity,
        trgm.target.extension_release,
        trgm.content_sha256,
        trgm.canonical_byte_length,
        len(trgm.source_occurrences),
        len(trgm.entries),
        len(trgm.exact_entry_groups),
        len(trgm.completeness_claims),
        len(trgm.completeness_groups),
    ) == (
        "pietto.postgresql",
        "pg_trgm",
        "1",
        "PostgreSQL",
        "18",
        "pg_trgm",
        "1.6",
        EXPECTED_PG_TRGM_SHA256,
        216386,
        6,
        42,
        26,
        0,
        0,
    )
    assert tuple(source.position for source in vector.source_occurrences) == tuple(
        range(4)
    )
    assert tuple(source.position for source in trgm.source_occurrences) == tuple(
        range(6)
    )
    assert all(
        source.source_revision
        for source in (*vector.source_occurrences, *trgm.source_occurrences)
    )
    assert tuple(entry.position for entry in vector.entries) == tuple(range(184))
    assert tuple(group.position for group in vector.exact_entry_groups) == tuple(
        range(131)
    )


def test_all_five_entry_families_and_structured_type_uses_are_retained() -> None:
    vector = _catalog(_inspection(_production_context()).inspection, "vector")
    assert {type(entry) for entry in vector.entries} == {
        ExtensionCatalogInspectionNativeTypeEntry,
        ExtensionCatalogInspectionScalarFunctionEntry,
        ExtensionCatalogInspectionAggregateEntry,
        ExtensionCatalogInspectionOperatorEntry,
        ExtensionCatalogInspectionCastEntry,
    }
    assert all(entry.evidence.source_positions for entry in vector.entries)
    assert {entry.evidence.matchability for entry in vector.entries} == {
        ExtensionCatalogMatchability.EXACT_MATCHABLE,
        ExtensionCatalogMatchability.CATALOGED_UNMODELED,
    }
    assert {entry.evidence.exposure for entry in vector.entries} == {
        ExtensionCatalogExposure.DIRECT_SQL_SURFACE,
        ExtensionCatalogExposure.IMPLEMENTATION_SUPPORT,
    }
    native = next(
        entry
        for entry in vector.entries
        if isinstance(entry, ExtensionCatalogInspectionNativeTypeEntry)
        and entry.type_identity.physical_name == "vector"
    )
    assert (
        native.type_identity.kind,
        native.type_identity.extension_identity,
        native.logical_mapping,
    ) == (ExtensionCatalogTypeReferenceKind.EXTENSION_NATIVE, "vector", None)


def test_inspection_carrier_fields_cover_every_retained_semantic_axis() -> None:
    expected = {
        inspection_module.ExtensionCatalogInspectionCatalogReference: (
            "namespace",
            "name",
            "release",
        ),
        inspection_module.ExtensionCatalogInspectionTarget: (
            "database_family",
            "database_release",
            "extension_identity",
            "extension_release",
        ),
        inspection_module.ExtensionCatalogInspectionTypeReference: (
            "kind",
            "logical_name",
            "logical_kind",
            "physical_name",
            "extension_identity",
        ),
        inspection_module.ExtensionCatalogInspectionTypeUse: (
            "kind",
            "exact_type",
            "source_spelling",
            "unmodeled_reasons",
        ),
        inspection_module.ExtensionCatalogInspectionCallableIdentity: (
            "sql_name",
            "input_types",
        ),
        inspection_module.ExtensionCatalogInspectionOperatorIdentity: (
            "operator_name",
            "arity",
            "operand_types",
        ),
        inspection_module.ExtensionCatalogInspectionCastIdentity: (
            "source_type",
            "target_type",
        ),
        inspection_module.ExtensionCatalogInspectionLookupScope: (
            "family",
            "identity",
        ),
        inspection_module.ExtensionCatalogInspectionCallableDeclaration: (
            "sql_name",
            "input_types",
            "identity",
        ),
        inspection_module.ExtensionCatalogInspectionEntryEvidence: (
            "matchability",
            "exposure",
            "unmodeled_reasons",
            "source_positions",
        ),
        inspection_module.ExtensionCatalogInspectionNativeTypeEntry: (
            "position",
            "type_identity",
            "logical_mapping",
            "evidence",
        ),
        inspection_module.ExtensionCatalogInspectionScalarFunctionEntry: (
            "position",
            "declaration",
            "result_type",
            "null_call_behavior",
            "volatility",
            "parallel_safety",
            "has_default_arguments",
            "is_variadic",
            "returns_set",
            "has_polymorphic_or_pseudo_types",
            "evidence",
        ),
        inspection_module.ExtensionCatalogInspectionAggregateEntry: (
            "position",
            "kind",
            "declaration",
            "result_type",
            "parallel_safety",
            "has_direct_arguments",
            "is_variadic",
            "evidence",
        ),
        inspection_module.ExtensionCatalogInspectionOperatorEntry: (
            "position",
            "operator_name",
            "arity",
            "operand_types",
            "identity",
            "result_type",
            "evidence",
        ),
        inspection_module.ExtensionCatalogInspectionCastEntry: (
            "position",
            "source_type",
            "target_type",
            "identity",
            "context",
            "method",
            "evidence",
        ),
        inspection_module.ExtensionCatalogInspectionSourceOccurrence: (
            "position",
            "source_authority",
            "source_revision",
            "source_locator",
            "curation",
        ),
        inspection_module.ExtensionCatalogInspectionExactEntryGroup: (
            "position",
            "scope",
            "state",
            "entry_positions",
        ),
        inspection_module.ExtensionCatalogInspectionCompletenessClaim: (
            "position",
            "scope",
            "kind",
            "source_positions",
        ),
        inspection_module.ExtensionCatalogInspectionCompletenessGroup: (
            "position",
            "scope",
            "state",
            "claim_positions",
        ),
        inspection_module.ExtensionCatalogInspectionCatalog: (
            "position",
            "reference",
            "target",
            "content_sha256",
            "canonical_byte_length",
            "source_occurrences",
            "entries",
            "exact_entry_groups",
            "completeness_claims",
            "completeness_groups",
        ),
        inspection_module.ExtensionCatalogInspectionKey: (
            "domain",
            "subject",
            "operation",
            "operands",
            "context",
            "dialect",
            "extension",
        ),
        inspection_module.ExtensionCatalogInspectionCapabilityEvidence: (
            "source",
            "source_path",
            "source_reference",
            "reason",
            "dialect",
            "backend",
            "extension",
        ),
        inspection_module.ExtensionCatalogInspectionCapabilityFact: (
            "key",
            "support",
            "disposition_kind",
            "disposition_owner",
            "disposition_reason",
            "evidence",
        ),
        inspection_module.ExtensionCatalogInspectionAvailabilityDeclaration: (
            "position",
            "owner",
            "project_path",
            "catalog_position",
            "reference",
            "target",
            "content_sha256",
        ),
        inspection_module.ExtensionCatalogInspectionSelectionCandidate: (
            "catalog_position",
            "reference",
            "target",
            "content_sha256",
            "declaration_positions",
        ),
        inspection_module.ExtensionCatalogInspectionSelection: (
            "requested_target",
            "active_project_path",
            "outcome",
            "availability",
            "applicable_declaration_positions",
            "excluded_project_declaration_positions",
            "target_declaration_positions",
            "candidates",
            "selected_catalog_position",
        ),
        inspection_module.ExtensionCatalogInspectionProviderInputs: (
            "key",
            "domain_complete",
            "unknown_reason",
            "facts",
        ),
        inspection_module.ExtensionCatalogInspectionLookup: (
            "variant",
            "reason",
            "facts",
        ),
        inspection_module.ExtensionCatalogInspectionProviderOccurrence: (
            "requirement_position",
            "key",
            "selector_scope",
            "bridged_database_family",
            "selection",
            "selected_catalog_position",
            "exact_group_position",
            "unmodeled_blocker_entry_positions",
            "completeness_group_position",
            "provider_inputs",
            "lookup",
        ),
    }
    assert all(
        tuple(field.name for field in fields(carrier)) == names
        for carrier, names in expected.items()
    )


def test_repeated_entry_and_claim_objects_keep_distinct_member_positions() -> None:
    entry = slice5._scalar_entry((0,))
    completeness_scope = slice5._scope(name="missing")
    claim = ExtensionCatalogCompletenessClaim(
        completeness_scope,
        ExtensionCatalogCompletenessClaimKind.COMPLETE,
        (0,),
    )
    catalog = slice8._catalog(
        (entry, entry),
        (claim, claim),
        source_count=1,
    )
    inspected = _inspection(
        _synthetic_context(
            catalog,
            catalog.exact_entry_groups[0].scope,
            name="repeated-members",
        )
    ).inspection
    projected = _catalog(inspected, "example_extension")
    assert projected.exact_entry_groups[0].entry_positions == (0, 1)
    assert projected.completeness_groups[0].claim_positions == (0, 1)
    assert tuple(entry.position for entry in projected.entries) == (0, 1)
    assert tuple(claim.position for claim in projected.completeness_claims) == (0, 1)


def test_real_unmodeled_and_implementation_support_paths_are_exact() -> None:
    inspected = _inspection(_production_context()).inspection
    trgm = _catalog(inspected, "pg_trgm")
    show = next(
        entry
        for entry in trgm.entries
        if isinstance(entry, ExtensionCatalogInspectionScalarFunctionEntry)
        and entry.declaration.sql_name == "show_trgm"
    )
    assert show.result_type.kind is ExtensionCatalogDeclarationTypeUseKind.UNMODELED
    assert show.result_type.source_spelling == "_text"
    assert show.result_type.unmodeled_reasons == (
        ExtensionCatalogUnmodeledReason.UNSUPPORTED_TYPE_FORM,
    )
    assert show.evidence.matchability is (
        ExtensionCatalogMatchability.CATALOGED_UNMODELED
    )
    assert show.evidence.exposure is ExtensionCatalogExposure.DIRECT_SQL_SURFACE
    assert show.evidence.source_positions == (1, 2)
    unmodeled = inspected.provider_occurrences[2]
    assert unmodeled.exact_group_position is None
    assert unmodeled.unmodeled_blocker_entry_positions == (show.position,)
    assert unmodeled.lookup.variant is ExtensionCatalogInspectionLookupVariant.UNKNOWN
    assert unmodeled.lookup.reason is CapabilityReasonCode.EXTENSION_CATALOGED_UNMODELED

    support = next(
        entry
        for entry in trgm.entries
        if isinstance(entry, ExtensionCatalogInspectionScalarFunctionEntry)
        and entry.declaration.sql_name == "similarity_op"
    )
    assert support.evidence.exposure is ExtensionCatalogExposure.IMPLEMENTATION_SUPPORT
    support_occurrence = inspected.provider_occurrences[3]
    assert support_occurrence.exact_group_position is not None
    assert (
        support_occurrence.lookup.variant
        is ExtensionCatalogInspectionLookupVariant.UNKNOWN
    )
    assert support_occurrence.lookup.reason is (
        CapabilityReasonCode.EXTENSION_CATALOG_NOT_PROVIDER_ELIGIBLE
    )
    assert support.evidence.source_positions == (2,)


def test_semantic_key_selector_and_real_exact_provenance_trace_are_separate() -> None:
    inspected = _inspection(_production_context()).inspection
    occurrence = inspected.provider_occurrences[1]
    assert (
        occurrence.requirement_position,
        occurrence.key.domain,
        occurrence.key.subject,
        occurrence.key.operation,
        occurrence.key.operands,
        occurrence.key.context,
        occurrence.key.dialect,
        occurrence.key.extension,
    ) == (
        1,
        CapabilityDomain.EXTENSION_SIGNATURE,
        "pg_trgm direct",
        "exact signature",
        ("semantic", "text", "only"),
        "typed selector is separate",
        "postgresql",
        "pg_trgm",
    )
    assert occurrence.bridged_database_family == "PostgreSQL"
    assert (
        occurrence.selector_scope.family is ExtensionCatalogEntryFamily.SCALAR_FUNCTION
    )
    selector = cast(Any, occurrence.selector_scope.identity)
    assert selector.sql_name == "similarity"
    assert tuple(item.physical_name for item in selector.input_types) == (
        "text",
        "text",
    )
    assert "similarity" not in occurrence.key.operands
    assert occurrence.selection.outcome is ExtensionCatalogSelectionOutcome.SELECTED
    assert occurrence.selected_catalog_position is not None
    assert occurrence.exact_group_position is not None
    assert occurrence.lookup.variant is ExtensionCatalogInspectionLookupVariant.FOUND
    assert occurrence.lookup.reason is None
    assert len(occurrence.lookup.facts) == 1
    fact = occurrence.lookup.facts[0]
    assert fact.support is CapabilitySupport.SUPPORTED
    assert fact.key == occurrence.key

    catalog = inspected.catalogs[occurrence.selected_catalog_position]
    group = catalog.exact_entry_groups[occurrence.exact_group_position]
    assert group.state is ExtensionCatalogExactEntryGroupState.UNIQUE
    entry = catalog.entries[group.entry_positions[0]]
    assert entry.evidence.source_positions == (1, 2)
    sources = tuple(
        catalog.source_occurrences[position]
        for position in entry.evidence.source_positions
    )
    assert tuple(source.source_locator for source in sources) == (
        "doc/src/sgml/pgtrgm.sgml",
        "contrib/pg_trgm/pg_trgm--1.3.sql",
    )
    assert all(
        source.source_revision == "724edf9bde9d356724ad384a2e196edc3c9f80f7"
        for source in sources
    )
    assert tuple(evidence.source_path for evidence in fact.evidence) == (
        "doc/src/sgml/pgtrgm.sgml",
        "contrib/pg_trgm/pg_trgm--1.3.sql",
    )


def test_only_selector_bound_extension_requirements_are_inspected() -> None:
    semantic = CapabilityKey(CapabilityDomain.LOGICAL_TYPE, subject="Int")
    extension = _key("selected", extension="pg_trgm")
    requirements = _requirements(semantic, extension, name="mixed")
    selection = select_extension_catalog(
        slice6._availability(
            (
                ExtensionCatalogAvailabilityOwner.COMPILER,
                PG_TRGM_V16_POSTGRESQL18_CATALOG,
                None,
            ),
        ),
        PG_TRGM_V16_POSTGRESQL18_CATALOG.metadata.target,
    )
    context = _context(
        requirements,
        (1, _scalar_scope("similarity", _builtin("text"), _builtin("text")), selection),
    )
    inspected = _inspection(context).inspection
    assert tuple(
        item.requirement_position for item in inspected.provider_occurrences
    ) == (1,)
    assert inspected.provider_occurrences[0].key.domain is (
        CapabilityDomain.EXTENSION_SIGNATURE
    )


def test_availability_project_provenance_retains_multiplicity_without_precedence() -> (
    None
):
    active = ProjectRoot("projects/current")
    foreign = ProjectRoot("projects/foreign")
    catalog = PG_TRGM_V16_POSTGRESQL18_CATALOG
    availability = slice6._availability(
        (ExtensionCatalogAvailabilityOwner.COMPILER, catalog, None),
        (ExtensionCatalogAvailabilityOwner.PROJECT, catalog, active),
        (ExtensionCatalogAvailabilityOwner.PROJECT, catalog, foreign),
    )
    selection = select_extension_catalog(availability, catalog.metadata.target, active)
    requirements = _requirements(_key("project provenance", extension="pg_trgm"))
    inspected = _inspection(
        _context(
            requirements,
            (
                0,
                _scalar_scope("similarity", _builtin("text"), _builtin("text")),
                selection,
            ),
        )
    ).inspection
    projected = inspected.provider_occurrences[0].selection
    assert projected.outcome is ExtensionCatalogSelectionOutcome.SELECTED
    assert projected.active_project_path == "projects/current"
    assert tuple(
        (item.position, item.owner, item.project_path, item.catalog_position)
        for item in projected.availability
    ) == (
        (0, ExtensionCatalogAvailabilityOwner.COMPILER, None, 0),
        (
            1,
            ExtensionCatalogAvailabilityOwner.PROJECT,
            "projects/current",
            0,
        ),
        (
            2,
            ExtensionCatalogAvailabilityOwner.PROJECT,
            "projects/foreign",
            0,
        ),
    )
    assert projected.applicable_declaration_positions == (0, 1)
    assert projected.excluded_project_declaration_positions == (2,)
    assert projected.target_declaration_positions == (0, 1)
    assert len(projected.candidates) == 1
    assert projected.candidates[0].declaration_positions == (0, 1)
    assert projected.selected_catalog_position == 0


def _synthetic_context(
    catalog: ConstructedExtensionCatalog | None,
    scope: ExtensionCatalogLookupScope,
    *,
    key: CapabilityKey | None = None,
    selection: ExtensionCatalogSelectionResult | None = None,
    name: str = "synthetic",
) -> ExtensionSignatureProviderContext:
    requirement_key = key or _key("synthetic", extension="example_extension")
    requirements = _requirements(requirement_key, name=name)
    resolved = selection
    if resolved is None:
        assert catalog is not None
        resolved = select_extension_catalog(
            slice6._availability(
                (ExtensionCatalogAvailabilityOwner.COMPILER, catalog, None),
            ),
            catalog.metadata.target,
        )
    return _context(requirements, (0, scope, resolved))


def _synthetic_scope(name: str = "shared") -> ExtensionCatalogLookupScope:
    return _scalar_scope(name, _builtin("text"))


def test_selection_undeclared_ambiguous_and_conflict_remain_distinct() -> None:
    target = slice6._target()
    scope = _synthetic_scope("missing")
    undeclared = select_extension_catalog(
        DeclaredExtensionCatalogAvailability(()), target
    )
    undeclared_inspection = _inspection(
        _synthetic_context(None, scope, selection=undeclared, name="undeclared")
    ).inspection.provider_occurrences[0]
    assert undeclared_inspection.selection.outcome is (
        ExtensionCatalogSelectionOutcome.UNDECLARED
    )
    assert undeclared_inspection.selection.candidates == ()
    assert undeclared_inspection.lookup.variant is (
        ExtensionCatalogInspectionLookupVariant.UNKNOWN
    )
    assert undeclared_inspection.lookup.reason is (
        CapabilityReasonCode.EXTENSION_CATALOG_UNDECLARED
    )

    first = slice6._artifact(reference=slice6._reference("first"), target=target)
    second = slice6._artifact(reference=slice6._reference("second"), target=target)
    ambiguous_selection = select_extension_catalog(
        slice6._availability(
            (ExtensionCatalogAvailabilityOwner.COMPILER, first, None),
            (ExtensionCatalogAvailabilityOwner.COMPILER, second, None),
        ),
        target,
    )
    ambiguous = _inspection(
        _synthetic_context(
            None,
            scope,
            selection=ambiguous_selection,
            name="ambiguous",
        )
    ).inspection.provider_occurrences[0]
    assert ambiguous.selection.outcome is ExtensionCatalogSelectionOutcome.AMBIGUOUS
    assert len(ambiguous.selection.candidates) == 2
    assert ambiguous.selection.selected_catalog_position is None
    assert ambiguous.lookup.reason is (
        CapabilityReasonCode.EXTENSION_CATALOG_SELECTION_AMBIGUOUS
    )

    reference = slice6._reference("conflict")
    one = slice6._artifact(
        reference=reference,
        target=target,
        source_labels=("one",),
    )
    two = slice6._artifact(
        reference=reference,
        target=target,
        source_labels=("two",),
    )
    conflict_selection = select_extension_catalog(
        slice6._availability(
            (ExtensionCatalogAvailabilityOwner.COMPILER, one, None),
            (ExtensionCatalogAvailabilityOwner.COMPILER, two, None),
        ),
        target,
    )
    conflict = _inspection(
        _synthetic_context(
            None,
            scope,
            selection=conflict_selection,
            name="selection-conflict",
        )
    ).inspection.provider_occurrences[0]
    assert conflict.selection.outcome is ExtensionCatalogSelectionOutcome.CONFLICT
    assert len(conflict.selection.candidates) == 2
    assert (
        len({candidate.content_sha256 for candidate in conflict.selection.candidates})
        == 2
    )
    assert conflict.lookup.reason is (
        CapabilityReasonCode.EXTENSION_CATALOG_SELECTION_CONFLICT
    )


def test_exact_duplicate_conflict_and_complete_incomplete_conflict_paths_are_exact() -> (
    None
):
    duplicate_catalog = slice8._catalog(
        (
            slice5._scalar_entry((0,)),
            slice5._scalar_entry((1,)),
        ),
        source_count=2,
    )
    duplicate = _inspection(
        _synthetic_context(
            duplicate_catalog,
            duplicate_catalog.exact_entry_groups[0].scope,
            name="duplicate",
        )
    ).inspection.provider_occurrences[0]
    duplicate_projected_catalog = _catalog(
        _inspection(
            _synthetic_context(
                duplicate_catalog,
                duplicate_catalog.exact_entry_groups[0].scope,
                name="duplicate-catalog",
            )
        ).inspection,
        "example_extension",
    )
    assert duplicate.lookup.variant is ExtensionCatalogInspectionLookupVariant.FOUND
    assert duplicate.exact_group_position is not None
    assert (
        duplicate_projected_catalog.exact_entry_groups[
            duplicate.exact_group_position
        ].state
        is ExtensionCatalogExactEntryGroupState.CONSISTENT_DUPLICATE
    )

    conflict_catalog = slice8._catalog(
        (
            slice5._scalar_entry((0,), result="text"),
            slice5._scalar_entry((1,), result="int4"),
        ),
        source_count=2,
    )
    conflict_fact_set = _inspection(
        _synthetic_context(
            conflict_catalog,
            conflict_catalog.exact_entry_groups[0].scope,
            name="evidence-conflict",
        )
    )
    conflict = conflict_fact_set.inspection.provider_occurrences[0]
    conflict_projected_catalog = _catalog(
        conflict_fact_set.inspection,
        "example_extension",
    )
    assert conflict.lookup.variant is ExtensionCatalogInspectionLookupVariant.CONFLICT
    assert conflict.lookup.reason is CapabilityReasonCode.CONFLICTING_EVIDENCE
    assert len(conflict.lookup.facts) == 2
    assert conflict.exact_group_position is not None
    conflict_group = conflict_projected_catalog.exact_entry_groups[
        conflict.exact_group_position
    ]
    assert (
        conflict_group.state is ExtensionCatalogExactEntryGroupState.EVIDENCE_CONFLICT
    )
    assert len(conflict_group.entry_positions) == 2
    assert tuple(
        conflict_projected_catalog.entries[position].evidence.source_positions
        for position in conflict_group.entry_positions
    ) == tuple(
        entry.evidence.source_positions
        for entry in conflict_catalog.exact_entry_groups[0].entries
    )

    scope = slice5._scope(name="missing")
    complete_claim = ExtensionCatalogCompletenessClaim(
        scope,
        ExtensionCatalogCompletenessClaimKind.COMPLETE,
        (0,),
    )
    incomplete_claim = ExtensionCatalogCompletenessClaim(
        scope,
        ExtensionCatalogCompletenessClaimKind.INCOMPLETE,
        (1,),
    )
    cases = (
        (
            "complete",
            (complete_claim,),
            1,
            ExtensionCatalogCompletenessState.COMPLETE,
            ExtensionCatalogInspectionLookupVariant.ABSENT,
            CapabilityReasonCode.NO_CATALOG_ENTRY,
        ),
        (
            "incomplete",
            (
                ExtensionCatalogCompletenessClaim(
                    scope,
                    ExtensionCatalogCompletenessClaimKind.INCOMPLETE,
                    (0,),
                ),
            ),
            1,
            ExtensionCatalogCompletenessState.INCOMPLETE,
            ExtensionCatalogInspectionLookupVariant.UNKNOWN,
            CapabilityReasonCode.EXTENSION_CATALOG_COMPLETENESS_INCOMPLETE,
        ),
        (
            "completeness-conflict",
            (complete_claim, incomplete_claim),
            2,
            ExtensionCatalogCompletenessState.CONFLICT,
            ExtensionCatalogInspectionLookupVariant.UNKNOWN,
            CapabilityReasonCode.EXTENSION_CATALOG_COMPLETENESS_CONFLICT,
        ),
    )
    for name, claims, source_count, state, variant, reason in cases:
        catalog = slice8._catalog(claims=claims, source_count=source_count)
        fact_set = _inspection(_synthetic_context(catalog, scope, name=name))
        occurrence = fact_set.inspection.provider_occurrences[0]
        projected_catalog = _catalog(fact_set.inspection, "example_extension")
        assert occurrence.completeness_group_position == 0
        assert projected_catalog.completeness_groups[0].state is state
        assert tuple(
            claim.source_positions for claim in projected_catalog.completeness_claims
        ) == tuple(claim.source_positions for claim in catalog.completeness_claims)
        assert occurrence.lookup.variant is variant
        assert occurrence.lookup.reason is reason


def test_target_mismatch_and_missing_completeness_authority_remain_bounded() -> None:
    catalog = _direct_catalog()
    mismatch = _inspection(
        _synthetic_context(
            catalog,
            catalog.exact_entry_groups[0].scope,
            key=_key("target mismatch", extension="wrong_extension"),
            name="target-mismatch",
        )
    ).inspection.provider_occurrences[0]
    assert mismatch.selection.outcome is ExtensionCatalogSelectionOutcome.SELECTED
    assert mismatch.selected_catalog_position is not None
    assert mismatch.exact_group_position is None
    assert mismatch.lookup.variant is ExtensionCatalogInspectionLookupVariant.UNKNOWN
    assert (
        mismatch.lookup.reason is CapabilityReasonCode.EXTENSION_CATALOG_TARGET_MISMATCH
    )

    missing = _inspection(
        _synthetic_context(
            catalog,
            _synthetic_scope("missing"),
            name="missing-completeness",
        )
    ).inspection.provider_occurrences[0]
    assert missing.exact_group_position is None
    assert missing.unmodeled_blocker_entry_positions == ()
    assert missing.completeness_group_position is None
    assert missing.provider_inputs.domain_complete is False
    assert missing.provider_inputs.unknown_reason is (
        CapabilityReasonCode.EXTENSION_CATALOG_COMPLETENESS_UNAVAILABLE
    )
    assert missing.lookup.variant is ExtensionCatalogInspectionLookupVariant.UNKNOWN
    assert missing.lookup.reason is (
        CapabilityReasonCode.EXTENSION_CATALOG_COMPLETENESS_UNAVAILABLE
    )


def _direct_catalog(
    *,
    reference_name: str = "direct",
    database_release: str = "17.4",
    result: str = "text",
    exposure: ExtensionCatalogExposure = ExtensionCatalogExposure.DIRECT_SQL_SURFACE,
) -> ConstructedExtensionCatalog:
    return slice8._catalog(
        (slice5._scalar_entry((0,), result=result, exposure=exposure),),
        target=slice6._target(database_release=database_release),
        reference=slice6._reference(reference_name),
        source_count=1,
    )


def _bytes_for_catalog(
    catalog: ConstructedExtensionCatalog,
    *,
    key: CapabilityKey | None = None,
    scope: ExtensionCatalogLookupScope | None = None,
    name: str = "mutation",
) -> bytes:
    return _inspection(
        _synthetic_context(
            catalog,
            scope or catalog.exact_entry_groups[0].scope,
            key=key,
            name=name,
        )
    ).canonical_bytes


def test_canonical_bytes_are_rebuild_allocation_and_table_order_invariant() -> None:
    first = _inspection(_production_context(rebuild=True))
    second = _inspection(_production_context(rebuild=True, reverse_allocation=True))
    assert first.inspection is not second.inspection
    assert first.inspection.context is not second.inspection.context
    assert all(
        left is not right
        for left, right in zip(
            first.inspection.catalogs,
            second.inspection.catalogs,
            strict=True,
        )
    )
    assert first.inspection == second.inspection
    assert first.canonical_bytes == second.canonical_bytes
    assert tuple(
        (
            catalog.reference.namespace,
            catalog.reference.name,
            catalog.reference.release,
            catalog.target.database_family,
            catalog.target.database_release,
            catalog.target.extension_identity,
            catalog.target.extension_release,
            catalog.content_sha256,
        )
        for catalog in first.inspection.catalogs
    ) == tuple(
        sorted(
            (
                catalog.reference.namespace,
                catalog.reference.name,
                catalog.reference.release,
                catalog.target.database_family,
                catalog.target.database_release,
                catalog.target.extension_identity,
                catalog.target.extension_release,
                catalog.content_sha256,
            )
            for catalog in first.inspection.catalogs
        )
    )


def test_canonical_bytes_change_on_every_required_major_semantic_axis() -> None:
    base_catalog = _direct_catalog()
    base = _bytes_for_catalog(base_catalog)
    key_mutation = _bytes_for_catalog(
        base_catalog,
        key=_key(
            "changed semantic key",
            extension="example_extension",
            operation="changed operation",
        ),
    )
    selector_mutation = _bytes_for_catalog(
        base_catalog,
        scope=_synthetic_scope("missing"),
    )
    coordinate_mutation = _bytes_for_catalog(
        _direct_catalog(reference_name="changed-coordinate")
    )
    target_mutation = _bytes_for_catalog(_direct_catalog(database_release="18"))
    digest_mutation = _bytes_for_catalog(_direct_catalog(result="int4"))
    source_mutation = _bytes_for_catalog(
        slice8._catalog(
            (slice5._scalar_entry((0,)),),
            reference=slice6._reference("direct"),
            target=slice6._target(),
            source_count=2,
        )
    )
    exposure_mutation = _bytes_for_catalog(
        _direct_catalog(exposure=ExtensionCatalogExposure.IMPLEMENTATION_SUPPORT)
    )
    assert all(
        value != base
        for value in (
            key_mutation,
            selector_mutation,
            coordinate_mutation,
            target_mutation,
            digest_mutation,
            source_mutation,
            exposure_mutation,
        )
    )

    first_unmodeled = slice8._catalog(
        (
            slice5._unmodeled_entry(
                "opaque[]",
                ExtensionCatalogUnmodeledReason.UNSUPPORTED_TYPE_FORM,
            ),
        )
    )
    second_unmodeled = slice8._catalog(
        (
            slice5._unmodeled_entry(
                "internal",
                ExtensionCatalogUnmodeledReason.POLYMORPHIC_OR_PSEUDO_TYPE,
            ),
        )
    )
    unmodeled_scope = _synthetic_scope("complex")
    assert _bytes_for_catalog(
        first_unmodeled,
        scope=unmodeled_scope,
    ) != _bytes_for_catalog(second_unmodeled, scope=unmodeled_scope)

    ambiguous_target = slice6._target()
    ambiguous_selection = select_extension_catalog(
        slice6._availability(
            (
                ExtensionCatalogAvailabilityOwner.COMPILER,
                slice6._artifact(
                    reference=slice6._reference("first"),
                    target=ambiguous_target,
                ),
                None,
            ),
            (
                ExtensionCatalogAvailabilityOwner.COMPILER,
                slice6._artifact(
                    reference=slice6._reference("second"),
                    target=ambiguous_target,
                ),
                None,
            ),
        ),
        ambiguous_target,
    )
    ambiguous_bytes = _inspection(
        _synthetic_context(
            None,
            _synthetic_scope("missing"),
            selection=ambiguous_selection,
        )
    ).canonical_bytes
    assert ambiguous_bytes != base

    complete_scope = slice5._scope(name="missing")
    complete = slice8._catalog(
        claims=(
            ExtensionCatalogCompletenessClaim(
                complete_scope,
                ExtensionCatalogCompletenessClaimKind.COMPLETE,
                (0,),
            ),
        )
    )
    incomplete = slice8._catalog(
        claims=(
            ExtensionCatalogCompletenessClaim(
                complete_scope,
                ExtensionCatalogCompletenessClaimKind.INCOMPLETE,
                (0,),
            ),
        )
    )
    assert _bytes_for_catalog(complete, scope=complete_scope) != _bytes_for_catalog(
        incomplete,
        scope=complete_scope,
    )


def test_two_catalog_golden_inspection_bytes_and_digest_are_literal() -> None:
    canonical = _inspection(_production_context()).canonical_bytes
    assert len(canonical) == EXPECTED_INSPECTION_BYTES
    assert hashlib.sha256(canonical).hexdigest() == EXPECTED_INSPECTION_SHA256
    assert EXPECTED_INSPECTION_SHA256 not in {
        EXPECTED_PGVECTOR_SHA256,
        EXPECTED_PG_TRGM_SHA256,
    }


def test_constructor_closure_rejects_grafts_and_records_are_immutable() -> None:
    first = _inspection(_production_context())
    second = _inspection(_production_context(rebuild=True))
    with pytest.raises(ValueError, match="grafted projection"):
        ExtensionCatalogInspectionFactSet(
            inspection=second.inspection,
            canonical_bytes=first.canonical_bytes,
            authority=first.authority,
        )
    with pytest.raises(ValueError, match="grafted bytes"):
        ExtensionCatalogInspectionFactSet(
            inspection=first.inspection,
            canonical_bytes=bytes(bytearray(first.canonical_bytes)),
            authority=first.authority,
        )
    for carrier in (
        ExtensionCatalogInspection,
        ExtensionCatalogInspectionCatalog,
        ExtensionCatalogInspectionScalarFunctionEntry,
    ):
        with pytest.raises(TypeError, match="require derivation"):
            carrier()
    assert not hasattr(first.inspection, "__dict__")
    with pytest.raises(FrozenInstanceError):
        cast(
            Any, first.inspection
        ).format = ExtensionCatalogInspectionFormat.EXTENSION_CATALOG_INSPECTION_V1
    assert tuple(field.name for field in fields(ExtensionCatalogInspection)) == (
        "format",
        "requirement_namespace",
        "requirement_name",
        "catalogs",
        "provider_occurrences",
        "context",
    )


def test_inspection_calls_canonical_provider_authority_without_reselection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authority_calls: list[int] = []
    input_calls: list[int] = []
    original_authority = inspection_module.extension_signature_provider_authority
    original_inputs = inspection_module.extension_signature_provider_inputs

    def authority_wrapper(
        context: ExtensionSignatureProviderContext,
        requirement: CapabilityRequirementOccurrence,
    ) -> Any:
        authority_calls.append(requirement.position)
        return original_authority(context, requirement)

    def inputs_wrapper(authority: Any) -> Any:
        input_calls.append(authority.requirement.position)
        return original_inputs(authority)

    monkeypatch.setattr(
        inspection_module,
        "extension_signature_provider_authority",
        authority_wrapper,
    )
    monkeypatch.setattr(
        inspection_module,
        "extension_signature_provider_inputs",
        inputs_wrapper,
    )
    _inspection(_production_context())
    assert authority_calls == [0, 1, 2, 3]
    assert input_calls == [0, 1, 2, 3]
    source = inspect.getsource(inspection_module)
    assert "select_extension_catalog" not in source
    assert "_unmodeled_entry_is_relevant" not in source
    assert "_matching_group" not in source
    assert "EXTENSION_CATALOGED_UNMODELED" not in source
    assert "EXTENSION_CATALOG_COMPLETENESS_INCOMPLETE" not in source
    assert "extension_signature_provider_authority" in source
    assert "extension_signature_provider_inputs" in source
    assert "lookup_capability" in source


def test_private_isolation_predecessor_bytes_and_readiness_boundaries_are_exact() -> (
    None
):
    assert inspection_module.__all__ == ()
    for module in (pietto, semantic_package, project_package):
        for name in (
            "ExtensionCatalogInspection",
            "ExtensionCatalogInspectionFactSet",
            "build_extension_catalog_inspection",
        ):
            assert not hasattr(module, name)
    source = inspect.getsource(inspection_module).lower()
    for forbidden in (
        "import os",
        "pathlib",
        "subprocess",
        "requests",
        "urllib",
        "socket",
        "open(",
        "getcwd",
        "environ",
        "registry",
        "create extension",
        "extension_catalog_ltree",
        "extension_catalog_postgis",
    ):
        assert forbidden not in source
    assert "extension_catalog_inspection" not in inspect.getsource(
        capability_inspection
    )
    assert "extension_catalog_inspection" not in inspect.getsource(package_inspection)
    assert CapabilityInspectionFormat.CAPABILITY_INSPECTION_V1.value == (
        "pietto.capability-inspection.v1"
    )
    assert PGVECTOR_V086_POSTGRESQL18_CATALOG.content_sha256 == (
        EXPECTED_PGVECTOR_SHA256
    )
    assert PG_TRGM_V16_POSTGRESQL18_CATALOG.content_sha256 == (EXPECTED_PG_TRGM_SHA256)
    assert len(PGVECTOR_V086_POSTGRESQL18_CATALOG.canonical_bytes) == 993469
    assert len(PG_TRGM_V16_POSTGRESQL18_CATALOG.canonical_bytes) == 216386
    corpus = vectors.differential_vectors()
    accepted = tuple(
        vector for vector in corpus if vector.expected_status is CapabilityPureStatus.OK
    )
    assert (len(corpus), len(accepted), len(corpus) - len(accepted)) == (125, 16, 109)
    assert _corpus_digest() == EXPECTED_CORPUS_DIGEST
    inspected_names = {
        catalog.target.extension_identity
        for catalog in _inspection(_production_context()).inspection.catalogs
    }
    assert inspected_names == {"vector", "pg_trgm"}
    assert not (REPO_ROOT / "src/pietto/semantic/extension_catalog_ltree.py").exists()
    assert not (REPO_ROOT / "src/pietto/semantic/extension_catalog_postgis.py").exists()
    assert 'version = "0.1.0"' in (REPO_ROOT / "pyproject.toml").read_text(
        encoding="utf-8"
    )


def test_spec_lifecycle_reader_closure_and_package_smoke_are_exact() -> None:
    spec = SPEC.read_text(encoding="utf-8")
    for value in (
        "pietto.extension-catalog-inspection.v1",
        "ExtensionSignatureProviderContext",
        "ExtensionCatalogInspectionFactSet",
        "exact catalog reference + target + content_sha256",
        "DIRECT_SQL_SURFACE",
        "CATALOGED_UNMODELED",
        '"_text"',
        "UNDECLARED",
        "AMBIGUOUS",
        "CONFLICT",
        "EVIDENCE_CONFLICT",
        "COMPLETE",
        "INCOMPLETE",
        "canonical byte length",
        "SHA-256(canonical inspection bytes)",
        str(EXPECTED_INSPECTION_BYTES),
        EXPECTED_INSPECTION_SHA256,
        "Slice 12 remains unstarted and unauthorized",
        "generated/multi-source SQL assembly authority",
    ):
        assert value in spec
    roadmap = ROADMAP.read_text(encoding="utf-8")
    status = STATUS.read_text(encoding="utf-8")
    assert "Phase 57 is active, Slices 1–11 are completed, and Slice 12 is current" in (
        roadmap
    )
    assert "| Slices 1–11 | `COMPLETED` |" in status
    assert "| Slice 12 | `CURRENT` |" in status
    assert "| Next | `PHASE57_SLICE12_END_TO_END` |" in status
    assert "does not authorize Slice 13" in " ".join(status.split())
    package_smoke = PACKAGE_SMOKE.read_text(encoding="utf-8")
    assert 'f"{prefix}/_project/extension_catalog_inspection.py"' in package_smoke
    assert '"import pietto._project.extension_catalog_inspection"' in package_smoke
