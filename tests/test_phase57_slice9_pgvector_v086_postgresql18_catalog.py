from __future__ import annotations

from collections import Counter
import inspect
from pathlib import Path

import _pietto_capability_differential_vectors as vectors
import pietto
import pietto._project as project_package
import pietto._project.capability_inspection as capability_inspection
import pietto._project.capability_pure_boundary as pure_boundary
import pietto._project.extension_catalog_availability as catalog_availability
import pietto.semantic as semantic_package
import pietto.semantic.capability_providers as semantic_providers
import pietto.semantic.extension_catalog as extension_catalog
import pietto.semantic.extension_catalog_pgvector as pgvector_catalog
import test_phase56_slice6_exact_capability_requirement_checking as phase56
import test_phase57_slice5_extension_catalog_construction_completeness_canonical as slice5
from pietto._project.capability_availability import PackageCapabilityRequirementBinding
from pietto._project.capability_checking import (
    CapabilityRequirementStatus,
    PackageCapabilityRequirementsChecked,
    check_package_capability_requirements,
)
from pietto._project.extension_catalog_availability import (
    DeclaredExtensionCatalogAvailability,
    ExtensionCatalogAvailabilityDeclaration,
    ExtensionCatalogAvailabilityOwner,
    ExtensionCatalogSelectionOutcome,
    ExtensionCatalogSelectionResult,
    select_extension_catalog,
)
from pietto._project.extension_signature_provider import (
    ExtensionSignatureProviderContext,
    ExtensionSignatureProviderSelectionOccurrence,
    extension_signature_provider_authority,
)
from pietto.semantic.capability_facts import (
    CapabilityDomain,
    CapabilityKey,
    CapabilityReasonCode,
    CapabilitySupport,
)
from pietto.semantic.capability_lookup import Found, Unknown, lookup_capability
from pietto.semantic.capability_profiles import (
    CapabilityRequirementCollection,
    CapabilityRequirementCollectionIdentity,
    CapabilityRequirementOccurrence,
)
from pietto.semantic.extension_catalog import (
    ConstructedExtensionCatalog,
    ExtensionAggregateCatalogEntry,
    ExtensionCastCatalogEntry,
    ExtensionCatalogDeclarationTypeUse,
    ExtensionCatalogDeclarationTypeUseKind,
    ExtensionCatalogEntryFamily,
    ExtensionCatalogExactEntryGroupState,
    ExtensionCatalogExposure,
    ExtensionCatalogLookupScope,
    ExtensionCatalogMatchability,
    ExtensionCatalogTarget,
    ExtensionCatalogTypeReference,
    ExtensionCatalogTypeReferenceKind,
    ExtensionCatalogUnmodeledReason,
    ExtensionNativeTypeCatalogEntry,
    ExtensionOperatorCatalogEntry,
    ExtensionScalarFunctionCatalogEntry,
    PostgreSQLCallableIdentity,
    PostgreSQLCastContext,
    PostgreSQLCastIdentity,
    PostgreSQLCastMethod,
    PostgreSQLNullCallBehavior,
    PostgreSQLOperatorArity,
    PostgreSQLOperatorIdentity,
    PostgreSQLParallelSafety,
    PostgreSQLVolatility,
    _entry_family,
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
SPEC = REPO_ROOT / "docs/spec/phase57-pgvector-v086-postgresql18-catalog-v1.md"
ROADMAP = REPO_ROOT / "docs/roadmap.md"
STATUS = REPO_ROOT / "docs/status.md"
PACKAGE_SMOKE = REPO_ROOT / "scripts/package_smoke.py"
EXPECTED_SOURCE_REVISION = "8ee86c96f0fd72390f890aa8a336fda6d3ab4c6c"
EXPECTED_CANONICAL_BYTES = 993469
EXPECTED_CONTENT_SHA256 = (
    "686e68fe9d60c20cb276e2b26007d310ff8877a5b4a8274e5c9194116fa74654"
)
EXPECTED_CORPUS_DIGEST = (
    "8453c3babda888b105f37f667f5fadf3a12aa68ca9a561bda98e5f6b6604a69e"
)


def _native(name: str) -> ExtensionCatalogTypeReference:
    return ExtensionCatalogTypeReference(
        ExtensionCatalogTypeReferenceKind.EXTENSION_NATIVE,
        physical_name=name,
        extension_identity="vector",
    )


def _builtin(name: str) -> ExtensionCatalogTypeReference:
    return ExtensionCatalogTypeReference(
        ExtensionCatalogTypeReferenceKind.POSTGRES_BUILTIN,
        physical_name=name,
    )


def _scalar_scope(
    name: str,
    *inputs: ExtensionCatalogTypeReference,
) -> ExtensionCatalogLookupScope:
    return ExtensionCatalogLookupScope(
        ExtensionCatalogEntryFamily.SCALAR_FUNCTION,
        PostgreSQLCallableIdentity(name, inputs),
    )


def _key(name: str, *, extension: str = "vector") -> CapabilityKey:
    return CapabilityKey(
        CapabilityDomain.EXTENSION_SIGNATURE,
        subject=f"pgvector {name}",
        operation="exact signature",
        dialect="postgresql",
        extension=extension,
    )


def _requirements(key: CapabilityKey) -> CapabilityRequirementCollection:
    identity = CapabilityRequirementCollectionIdentity("consumer", key.subject or "key")
    return CapabilityRequirementCollection(
        identity,
        (CapabilityRequirementOccurrence(identity, 0, key),),
    )


def _selection(
    requested_target: ExtensionCatalogTarget | None = None,
) -> ExtensionCatalogSelectionResult:
    availability = DeclaredExtensionCatalogAvailability(
        (
            ExtensionCatalogAvailabilityDeclaration(
                ExtensionCatalogAvailabilityOwner.COMPILER,
                0,
                PGVECTOR_V086_POSTGRESQL18_CATALOG,
            ),
        )
    )
    return select_extension_catalog(
        availability,
        requested_target or PGVECTOR_V086_POSTGRESQL18_CATALOG.metadata.target,
    )


def _context(
    requirements: CapabilityRequirementCollection,
    scope: ExtensionCatalogLookupScope,
    selection: ExtensionCatalogSelectionResult,
) -> ExtensionSignatureProviderContext:
    selectors = ExtensionSignatureRequirementSelectors(
        requirements,
        (
            ExtensionSignatureRequirementSelectorOccurrence(
                0,
                ExtensionSignatureRequirementSelector(scope),
            ),
        ),
    )
    return ExtensionSignatureProviderContext(
        selectors,
        (ExtensionSignatureProviderSelectionOccurrence(0, selection),),
    )


def _provider_result(
    key: CapabilityKey,
    scope: ExtensionCatalogLookupScope,
    selection: ExtensionCatalogSelectionResult | None = None,
) -> Found | Unknown:
    requirements = _requirements(key)
    authority = extension_signature_provider_authority(
        _context(requirements, scope, selection or _selection()),
        requirements.occurrences[0],
    )
    inputs = authority.provider_inputs
    result = lookup_capability(
        inputs.key,
        inputs.facts,
        domain_complete=inputs.domain_complete,
        unknown_reason=inputs.unknown_reason,
    )
    assert isinstance(result, (Found, Unknown))
    return result


def _scalar_entry(
    name: str,
    inputs: tuple[str, ...] | None = None,
) -> ExtensionScalarFunctionCatalogEntry:
    candidates = tuple(
        entry
        for entry in PGVECTOR_V086_POSTGRESQL18_CATALOG.entries
        if isinstance(entry, ExtensionScalarFunctionCatalogEntry)
        and entry.declaration.sql_name == name
    )
    if inputs is None:
        assert len(candidates) == 1
        return candidates[0]
    for entry in candidates:
        if (
            entry.declaration.identity is not None
            and tuple(
                reference.physical_name
                for reference in entry.declaration.identity.input_types
            )
            == inputs
        ):
            return entry
    raise AssertionError(f"missing exact scalar function {name}{inputs}")


def _exact_physical_names() -> tuple[str, ...]:
    names: list[str] = []

    def retain(type_use: ExtensionCatalogDeclarationTypeUse) -> None:
        if type_use.kind is ExtensionCatalogDeclarationTypeUseKind.EXACT:
            assert type_use.exact_type is not None
            assert type_use.exact_type.physical_name is not None
            names.append(type_use.exact_type.physical_name)

    for entry in PGVECTOR_V086_POSTGRESQL18_CATALOG.entries:
        if isinstance(entry, ExtensionNativeTypeCatalogEntry):
            assert entry.type_identity.physical_name is not None
            names.append(entry.type_identity.physical_name)
        elif isinstance(entry, ExtensionScalarFunctionCatalogEntry):
            for type_use in entry.declaration.input_types:
                retain(type_use)
            retain(entry.result_type)
        elif isinstance(entry, ExtensionAggregateCatalogEntry):
            for type_use in entry.declaration.input_types:
                retain(type_use)
            retain(entry.result_type)
        elif isinstance(entry, ExtensionOperatorCatalogEntry):
            for type_use in entry.operand_types:
                retain(type_use)
            retain(entry.result_type)
        else:
            assert isinstance(entry, ExtensionCastCatalogEntry)
            retain(entry.source_type)
            retain(entry.target_type)
    return tuple(names)


def test_catalog_coordinate_target_and_four_source_occurrences_are_exact() -> None:
    catalog = PGVECTOR_V086_POSTGRESQL18_CATALOG
    assert type(catalog) is ConstructedExtensionCatalog
    assert (
        catalog.metadata.catalog.identity.namespace,
        catalog.metadata.catalog.identity.name,
        catalog.metadata.catalog.release,
    ) == ("pietto.postgresql", "pgvector", "1")
    target = catalog.metadata.target
    assert (
        target.database_family,
        target.database_release,
        target.extension_identity,
        target.extension_release,
    ) == ("PostgreSQL", "18", "vector", "0.8.6")
    assert tuple(
        (
            occurrence.position,
            occurrence.provenance.source_authority,
            occurrence.provenance.source_revision,
            occurrence.provenance.source_locator,
            occurrence.provenance.curation,
        )
        for occurrence in catalog.metadata.source_occurrences
    ) == (
        (
            0,
            "github.com/pgvector/pgvector",
            EXPECTED_SOURCE_REVISION,
            "vector.control",
            "extension identity and release metadata",
        ),
        (
            1,
            "github.com/pgvector/pgvector",
            EXPECTED_SOURCE_REVISION,
            "CHANGELOG.md",
            "release history",
        ),
        (
            2,
            "github.com/pgvector/pgvector",
            EXPECTED_SOURCE_REVISION,
            "README.md",
            "PostgreSQL support and user-facing surface",
        ),
        (
            3,
            "github.com/pgvector/pgvector",
            EXPECTED_SOURCE_REVISION,
            "sql/vector.sql",
            "extension SQL declarations",
        ),
    )


def test_complete_reviewed_inventory_counts_have_zero_unexplained_delta() -> None:
    catalog = PGVECTOR_V086_POSTGRESQL18_CATALOG
    assert len(catalog.entries) == 184
    assert Counter(_entry_family(entry) for entry in catalog.entries) == {
        ExtensionCatalogEntryFamily.NATIVE_TYPE: 3,
        ExtensionCatalogEntryFamily.SCALAR_FUNCTION: 114,
        ExtensionCatalogEntryFamily.AGGREGATE: 4,
        ExtensionCatalogEntryFamily.OPERATOR: 40,
        ExtensionCatalogEntryFamily.CAST: 23,
    }
    assert Counter(entry.evidence.matchability for entry in catalog.entries) == {
        ExtensionCatalogMatchability.EXACT_MATCHABLE: 131,
        ExtensionCatalogMatchability.CATALOGED_UNMODELED: 53,
    }
    assert Counter(entry.evidence.exposure for entry in catalog.entries) == {
        ExtensionCatalogExposure.DIRECT_SQL_SURFACE: 96,
        ExtensionCatalogExposure.IMPLEMENTATION_SUPPORT: 88,
    }
    assert Counter(
        reason
        for entry in catalog.entries
        for reason in set(entry.evidence.unmodeled_reasons)
    ) == {
        ExtensionCatalogUnmodeledReason.UNSUPPORTED_TYPE_FORM: 37,
        ExtensionCatalogUnmodeledReason.POLYMORPHIC_OR_PSEUDO_TYPE: 19,
    }
    assert catalog.completeness_claims == catalog.completeness_groups == ()
    assert len(catalog.exact_entry_groups) == 131
    assert Counter(group.state for group in catalog.exact_entry_groups) == {
        ExtensionCatalogExactEntryGroupState.UNIQUE: 131,
    }
    assert all(3 in entry.evidence.source_positions for entry in catalog.entries)


def test_native_types_owner_mappings_spelling_and_typmod_boundary_are_exact() -> None:
    native_entries = tuple(
        entry
        for entry in PGVECTOR_V086_POSTGRESQL18_CATALOG.entries
        if isinstance(entry, ExtensionNativeTypeCatalogEntry)
    )
    assert {
        (entry.type_identity.physical_name, entry.type_identity.extension_identity)
        for entry in native_entries
    } == {("vector", "vector"), ("halfvec", "vector"), ("sparsevec", "vector")}
    assert all(entry.logical_mapping is None for entry in native_entries)
    exact_names = set(_exact_physical_names())
    assert {
        "bit",
        "bool",
        "boolean",
        "bytea",
        "float8",
        "int",
        "int4",
        "integer",
        "oid",
        "vector",
        "halfvec",
        "sparsevec",
    } <= exact_names
    assert "vector(3)" not in exact_names
    assert not any(name.endswith("[]") for name in exact_names)
    assert not any("pgvector" == name for name in exact_names)


def test_representative_five_family_entries_and_metadata_are_exact() -> None:
    vector = _native("vector")
    halfvec = _native("halfvec")
    l2 = _scalar_entry("l2_distance", ("vector", "vector"))
    assert l2.result_type.exact_type == _builtin("float8")
    assert l2.evidence.exposure is ExtensionCatalogExposure.DIRECT_SQL_SURFACE
    assert l2.evidence.source_positions == (2, 3)
    assert l2.null_call_behavior is PostgreSQLNullCallBehavior.STRICT
    assert l2.volatility is PostgreSQLVolatility.IMMUTABLE
    assert l2.parallel_safety is PostgreSQLParallelSafety.SAFE

    average = next(
        entry
        for entry in PGVECTOR_V086_POSTGRESQL18_CATALOG.entries
        if isinstance(entry, ExtensionAggregateCatalogEntry)
        and entry.declaration.identity == PostgreSQLCallableIdentity("avg", (vector,))
    )
    assert average.result_type.exact_type == vector

    operator = next(
        entry
        for entry in PGVECTOR_V086_POSTGRESQL18_CATALOG.entries
        if isinstance(entry, ExtensionOperatorCatalogEntry)
        and entry.identity
        == PostgreSQLOperatorIdentity(
            "<->",
            PostgreSQLOperatorArity.BINARY,
            (vector, vector),
        )
    )
    assert operator.result_type.exact_type == _builtin("float8")

    cross_native_cast = next(
        entry
        for entry in PGVECTOR_V086_POSTGRESQL18_CATALOG.entries
        if isinstance(entry, ExtensionCastCatalogEntry)
        and entry.identity == PostgreSQLCastIdentity(vector, halfvec)
    )
    assert cross_native_cast.context is PostgreSQLCastContext.IMPLICIT
    assert cross_native_cast.method is PostgreSQLCastMethod.FUNCTION


def test_exposure_and_unmodeled_representatives_preserve_exact_source_evidence() -> (
    None
):
    support = _scalar_entry("vector_add", ("vector", "vector"))
    assert support.evidence.exposure is ExtensionCatalogExposure.IMPLEMENTATION_SUPPORT
    assert support.evidence.matchability is ExtensionCatalogMatchability.EXACT_MATCHABLE
    assert support.evidence.source_positions == (3,)

    array_entry = next(
        entry
        for entry in PGVECTOR_V086_POSTGRESQL18_CATALOG.entries
        if isinstance(entry, ExtensionScalarFunctionCatalogEntry)
        and entry.declaration.sql_name == "array_to_vector"
        and entry.declaration.input_types[0].source_spelling == "integer[]"
    )
    assert array_entry.evidence.matchability is (
        ExtensionCatalogMatchability.CATALOGED_UNMODELED
    )
    assert array_entry.declaration.input_types[0].unmodeled_reasons == (
        ExtensionCatalogUnmodeledReason.UNSUPPORTED_TYPE_FORM,
    )

    pseudo_entry = next(
        entry
        for entry in PGVECTOR_V086_POSTGRESQL18_CATALOG.entries
        if isinstance(entry, ExtensionScalarFunctionCatalogEntry)
        and entry.declaration.sql_name == "vector_in"
    )
    assert pseudo_entry.declaration.input_types[0].source_spelling == "cstring"
    assert pseudo_entry.has_polymorphic_or_pseudo_types is True
    assert ExtensionCatalogUnmodeledReason.POLYMORPHIC_OR_PSEUDO_TYPE in (
        pseudo_entry.evidence.unmodeled_reasons
    )

    combined = next(
        entry
        for entry in PGVECTOR_V086_POSTGRESQL18_CATALOG.entries
        if isinstance(entry, ExtensionScalarFunctionCatalogEntry)
        and entry.declaration.sql_name == "vector_typmod_in"
    )
    assert combined.declaration.input_types[0].source_spelling == "cstring[]"
    assert combined.declaration.input_types[0].unmodeled_reasons == (
        ExtensionCatalogUnmodeledReason.UNSUPPORTED_TYPE_FORM,
        ExtensionCatalogUnmodeledReason.POLYMORPHIC_OR_PSEUDO_TYPE,
    )

    handler = _scalar_entry("ivfflathandler")
    assert handler.null_call_behavior is PostgreSQLNullCallBehavior.UNKNOWN
    assert handler.volatility is PostgreSQLVolatility.UNKNOWN
    assert handler.parallel_safety is PostgreSQLParallelSafety.UNKNOWN
    assert not any(
        entry.evidence.exposure is ExtensionCatalogExposure.UNCLASSIFIED
        for entry in PGVECTOR_V086_POSTGRESQL18_CATALOG.entries
    )


def test_canonical_artifact_identity_is_literal_and_reconstructible() -> None:
    catalog = PGVECTOR_V086_POSTGRESQL18_CATALOG
    assert len(catalog.canonical_bytes) == EXPECTED_CANONICAL_BYTES
    assert catalog.content_sha256 == EXPECTED_CONTENT_SHA256
    rebuilt = pgvector_catalog._build_pgvector_catalog()
    assert rebuilt is not catalog
    assert rebuilt.canonical_bytes == catalog.canonical_bytes
    assert rebuilt.content_sha256 == catalog.content_sha256


def test_real_catalog_direct_surface_reaches_checker_satisfied(tmp_path: Path) -> None:
    scope = _scalar_scope("l2_distance", _native("vector"), _native("vector"))
    key = _key("l2 distance")
    requirements = _requirements(key)
    selection = _selection()
    assert selection.outcome is ExtensionCatalogSelectionOutcome.SELECTED
    package, _dependency = phase56.slice5._loaded_packages(tmp_path)
    composition = phase56._composition(phase56._target_fact(key))
    result = check_package_capability_requirements(
        package,
        PackageCapabilityRequirementBinding(package, requirements),
        composition,
        phase56._availability(composition),
        _context(requirements, scope, selection),
    )
    assert isinstance(result, PackageCapabilityRequirementsChecked)
    check = result.checks[0]
    assert check.status is CapabilityRequirementStatus.SATISFIED
    assert isinstance(check.provider_result, Found)
    assert check.provider_result.fact.support is CapabilitySupport.SUPPORTED


def test_real_catalog_fail_closed_provider_cases_are_exact() -> None:
    support = _provider_result(
        _key("private vector add"),
        _scalar_scope("vector_add", _native("vector"), _native("vector")),
    )
    assert support == Unknown(
        CapabilityReasonCode.EXTENSION_CATALOG_NOT_PROVIDER_ELIGIBLE
    )

    unmodeled = _provider_result(
        _key("array conversion"),
        _scalar_scope(
            "array_to_vector",
            _builtin("integer"),
            _builtin("integer"),
            _builtin("boolean"),
        ),
    )
    assert unmodeled == Unknown(CapabilityReasonCode.EXTENSION_CATALOGED_UNMODELED)

    missing_scope = _scalar_scope("not_declared", _builtin("integer"))
    missing = _provider_result(_key("missing"), missing_scope)
    assert missing == Unknown(
        CapabilityReasonCode.EXTENSION_CATALOG_COMPLETENESS_UNAVAILABLE
    )

    alias = _provider_result(_key("alias", extension="pgvector"), missing_scope)
    assert alias == Unknown(CapabilityReasonCode.EXTENSION_CATALOG_TARGET_MISMATCH)

    wrong_target = ExtensionCatalogTarget("PostgreSQL", "17", "vector", "0.8.6")
    wrong_selection = _selection(wrong_target)
    assert wrong_selection.outcome is ExtensionCatalogSelectionOutcome.UNDECLARED
    wrong_release = _provider_result(
        _key("wrong PostgreSQL release"),
        _scalar_scope("l2_distance", _native("vector"), _native("vector")),
        wrong_selection,
    )
    assert wrong_release == Unknown(CapabilityReasonCode.EXTENSION_CATALOG_UNDECLARED)


def test_catalog_is_private_offline_not_available_and_not_a_package_asset() -> None:
    assert pgvector_catalog.__all__ == ()
    for module in (pietto, semantic_package, project_package):
        assert not hasattr(module, "PGVECTOR_V086_POSTGRESQL18_CATALOG")
    assert "extension_catalog_pgvector" not in inspect.getsource(catalog_availability)
    assert "extension_catalog_pgvector" not in inspect.getsource(semantic_providers)
    assert "extension_catalog_pgvector" not in inspect.getsource(capability_inspection)
    assert not (REPO_ROOT / "pietto-package.toml").exists()
    source = inspect.getsource(pgvector_catalog).lower()
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
        "select_extension_catalog",
        "declaredextensioncatalogavailability",
        "registry",
        "create extension",
    ):
        assert forbidden not in source
    assert extension_catalog.__all__ == ()
    assert "pgvector" not in inspect.getsource(extension_catalog).lower()


def test_predecessor_inspection_corpus_legacy_provider_and_version_are_unchanged() -> (
    None
):
    assert (
        capability_inspection.CapabilityInspectionFormat.CAPABILITY_INSPECTION_V1.value
        == ("pietto.capability-inspection.v1")
    )
    corpus = vectors.differential_vectors()
    accepted = tuple(
        vector
        for vector in corpus
        if vector.expected_status is pure_boundary.CapabilityPureStatus.OK
    )
    assert (len(corpus), len(accepted), len(corpus) - len(accepted)) == (125, 16, 109)
    assert slice5._corpus_digest() == EXPECTED_CORPUS_DIGEST
    legacy_key = _key("legacy")
    inputs = semantic_providers.canonical_capability_provider_inputs(legacy_key)
    assert inputs.facts == () and inputs.domain_complete is False
    assert lookup_capability(
        inputs.key,
        inputs.facts,
        domain_complete=inputs.domain_complete,
        unknown_reason=inputs.unknown_reason,
    ) == Unknown(CapabilityReasonCode.NOT_EVIDENCED)
    assert 'version = "0.1.0"' in (REPO_ROOT / "pyproject.toml").read_text(
        encoding="utf-8"
    )


def test_spec_upstream_inventory_lifecycle_and_package_smoke_are_exact() -> None:
    spec = SPEC.read_text(encoding="utf-8")
    for value in (
        EXPECTED_SOURCE_REVISION,
        "02e761f5e06ef1f951418d405bdadc78963146ae",
        "9b955419f06891536da3c067e747951f70463bb2",
        "a7d4855c4f35cc3722b0248570f5f0cbc9936ce4",
        "7fc36712b31dc3b58d6c0c5caa8fa6097f30471d",
        "114",
        "184",
        "131",
        "53",
        "993469",
        EXPECTED_CONTENT_SHA256,
    ):
        assert value in spec
    for excluded in (
        "24 operator classes",
        "2 access methods",
        "2 COMMENT statements",
        "psql load guard",
    ):
        assert excluded in spec
    roadmap = ROADMAP.read_text(encoding="utf-8")
    status = STATUS.read_text(encoding="utf-8")
    assert "Phase 57 is active, Slices 1–10 are completed, and Slice 11 is current" in (
        roadmap
    )
    assert "| Slices 1–10 | `COMPLETED` |" in status
    assert "| Slice 11 | `CURRENT` |" in status
    assert "| Next | `PHASE57_SLICE11_END_TO_END` |" in status
    assert "does\nnot authorize Slice 12" in status
    package_smoke = PACKAGE_SMOKE.read_text(encoding="utf-8")
    assert 'f"{prefix}/semantic/extension_catalog_pgvector.py"' in package_smoke
    assert '"import pietto.semantic.extension_catalog_pgvector"' in package_smoke
