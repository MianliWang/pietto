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
import pietto.semantic.extension_catalog_pg_trgm as pg_trgm_catalog
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
    PostgreSQLNullCallBehavior,
    PostgreSQLOperatorArity,
    PostgreSQLOperatorIdentity,
    PostgreSQLParallelSafety,
    PostgreSQLVolatility,
    _entry_family,
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
SPEC = REPO_ROOT / "docs/spec/phase57-pg-trgm-ltree-postgis-representability-v1.md"
ROADMAP = REPO_ROOT / "docs/roadmap.md"
STATUS = REPO_ROOT / "docs/status.md"
PACKAGE_SMOKE = REPO_ROOT / "scripts/package_smoke.py"
EXPECTED_POSTGRES_REVISION = "724edf9bde9d356724ad384a2e196edc3c9f80f7"
EXPECTED_CANONICAL_BYTES = 216386
EXPECTED_CONTENT_SHA256 = (
    "09eb10a0660a05ca180d43a23f1eda7aaf4b6198f5de249591317194cc9576b7"
)
EXPECTED_PGVECTOR_SHA256 = (
    "686e68fe9d60c20cb276e2b26007d310ff8877a5b4a8274e5c9194116fa74654"
)
EXPECTED_CORPUS_DIGEST = (
    "8453c3babda888b105f37f667f5fadf3a12aa68ca9a561bda98e5f6b6604a69e"
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


def _key(name: str, *, extension: str = "pg_trgm") -> CapabilityKey:
    return CapabilityKey(
        CapabilityDomain.EXTENSION_SIGNATURE,
        subject=f"pg_trgm {name}",
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
    target: ExtensionCatalogTarget | None = None,
) -> ExtensionCatalogSelectionResult:
    availability = DeclaredExtensionCatalogAvailability(
        (
            ExtensionCatalogAvailabilityDeclaration(
                ExtensionCatalogAvailabilityOwner.COMPILER,
                0,
                PG_TRGM_V16_POSTGRESQL18_CATALOG,
            ),
        )
    )
    return select_extension_catalog(
        availability,
        target or PG_TRGM_V16_POSTGRESQL18_CATALOG.metadata.target,
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
        for entry in PG_TRGM_V16_POSTGRESQL18_CATALOG.entries
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


def _source_spelling(type_use: ExtensionCatalogDeclarationTypeUse) -> str:
    if type_use.kind is ExtensionCatalogDeclarationTypeUseKind.UNMODELED:
        assert type_use.source_spelling is not None
        return type_use.source_spelling
    assert type_use.exact_type is not None
    assert type_use.exact_type.physical_name is not None
    return type_use.exact_type.physical_name


def test_pg_trgm_coordinate_target_and_six_sources_are_exact() -> None:
    catalog = PG_TRGM_V16_POSTGRESQL18_CATALOG
    assert type(catalog) is ConstructedExtensionCatalog
    assert (
        catalog.metadata.catalog.identity.namespace,
        catalog.metadata.catalog.identity.name,
        catalog.metadata.catalog.release,
    ) == ("pietto.postgresql", "pg_trgm", "1")
    target = catalog.metadata.target
    assert (
        target.database_family,
        target.database_release,
        target.extension_identity,
        target.extension_release,
    ) == ("PostgreSQL", "18", "pg_trgm", "1.6")
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
            "github.com/postgres/postgres",
            EXPECTED_POSTGRES_REVISION,
            "contrib/pg_trgm/pg_trgm.control",
            "extension identity and release metadata",
        ),
        (
            1,
            "github.com/postgres/postgres",
            EXPECTED_POSTGRES_REVISION,
            "doc/src/sgml/pgtrgm.sgml",
            "documented user-facing functions and operators",
        ),
        (
            2,
            "github.com/postgres/postgres",
            EXPECTED_POSTGRES_REVISION,
            "contrib/pg_trgm/pg_trgm--1.3.sql",
            "base install declarations",
        ),
        (
            3,
            "github.com/postgres/postgres",
            EXPECTED_POSTGRES_REVISION,
            "contrib/pg_trgm/pg_trgm--1.3--1.4.sql",
            "1.4 effective-surface additions and modifications",
        ),
        (
            4,
            "github.com/postgres/postgres",
            EXPECTED_POSTGRES_REVISION,
            "contrib/pg_trgm/pg_trgm--1.4--1.5.sql",
            "1.5 effective-surface additions and modifications",
        ),
        (
            5,
            "github.com/postgres/postgres",
            EXPECTED_POSTGRES_REVISION,
            "contrib/pg_trgm/pg_trgm--1.5--1.6.sql",
            "1.6 effective-surface additions and modifications",
        ),
    )


def test_pg_trgm_effective_inventory_and_production_counts_are_exact() -> None:
    catalog = PG_TRGM_V16_POSTGRESQL18_CATALOG
    assert len(catalog.entries) == 42
    family_counts = Counter(_entry_family(entry) for entry in catalog.entries)
    assert family_counts == {
        ExtensionCatalogEntryFamily.NATIVE_TYPE: 1,
        ExtensionCatalogEntryFamily.SCALAR_FUNCTION: 31,
        ExtensionCatalogEntryFamily.OPERATOR: 10,
    }
    assert family_counts[ExtensionCatalogEntryFamily.AGGREGATE] == 0
    assert family_counts[ExtensionCatalogEntryFamily.CAST] == 0
    assert Counter(entry.evidence.matchability for entry in catalog.entries) == {
        ExtensionCatalogMatchability.EXACT_MATCHABLE: 26,
        ExtensionCatalogMatchability.CATALOGED_UNMODELED: 16,
    }
    assert Counter(entry.evidence.exposure for entry in catalog.entries) == {
        ExtensionCatalogExposure.DIRECT_SQL_SURFACE: 16,
        ExtensionCatalogExposure.IMPLEMENTATION_SUPPORT: 26,
    }
    assert Counter(
        reason
        for entry in catalog.entries
        for reason in set(entry.evidence.unmodeled_reasons)
    ) == {
        ExtensionCatalogUnmodeledReason.UNSUPPORTED_TYPE_FORM: 1,
        ExtensionCatalogUnmodeledReason.POLYMORPHIC_OR_PSEUDO_TYPE: 15,
    }
    assert catalog.completeness_claims == catalog.completeness_groups == ()
    assert len(catalog.exact_entry_groups) == 26
    assert Counter(group.state for group in catalog.exact_entry_groups) == {
        ExtensionCatalogExactEntryGroupState.UNIQUE: 26,
    }


def test_pg_trgm_curation_representatives_and_spelling_are_exact() -> None:
    similarity = _scalar_entry("similarity", ("text", "text"))
    assert _source_spelling(similarity.result_type) == "float4"
    assert similarity.evidence.exposure is ExtensionCatalogExposure.DIRECT_SQL_SURFACE
    assert similarity.evidence.source_positions == (1, 2)

    deprecated = _scalar_entry("set_limit", ("float4",))
    assert deprecated.evidence.exposure is ExtensionCatalogExposure.DIRECT_SQL_SURFACE
    assert deprecated.volatility is PostgreSQLVolatility.VOLATILE
    assert deprecated.parallel_safety is PostgreSQLParallelSafety.UNSAFE

    show_trgm = _scalar_entry("show_trgm", ("text",))
    assert show_trgm.result_type.source_spelling == "_text"
    assert show_trgm.evidence.exposure is ExtensionCatalogExposure.DIRECT_SQL_SURFACE
    assert (
        show_trgm.evidence.matchability
        is ExtensionCatalogMatchability.CATALOGED_UNMODELED
    )
    assert show_trgm.evidence.unmodeled_reasons == (
        ExtensionCatalogUnmodeledReason.UNSUPPORTED_TYPE_FORM,
    )

    support = _scalar_entry("similarity_op", ("text", "text"))
    assert support.evidence.exposure is ExtensionCatalogExposure.IMPLEMENTATION_SUPPORT
    assert support.evidence.matchability is ExtensionCatalogMatchability.EXACT_MATCHABLE
    assert support.volatility is PostgreSQLVolatility.STABLE

    pseudo = _scalar_entry("gtrgm_in")
    assert pseudo.declaration.input_types[0].source_spelling == "cstring"
    assert pseudo.has_polymorphic_or_pseudo_types is True

    options = _scalar_entry("gtrgm_options")
    assert options.result_type.source_spelling == "void"
    assert options.null_call_behavior is PostgreSQLNullCallBehavior.UNKNOWN

    native = next(
        entry
        for entry in PG_TRGM_V16_POSTGRESQL18_CATALOG.entries
        if isinstance(entry, ExtensionNativeTypeCatalogEntry)
    )
    assert (
        native.type_identity.physical_name,
        native.type_identity.extension_identity,
        native.logical_mapping,
        native.evidence.exposure,
    ) == ("gtrgm", "pg_trgm", None, ExtensionCatalogExposure.IMPLEMENTATION_SUPPORT)

    operator = next(
        entry
        for entry in PG_TRGM_V16_POSTGRESQL18_CATALOG.entries
        if isinstance(entry, ExtensionOperatorCatalogEntry)
        and entry.identity
        == PostgreSQLOperatorIdentity(
            "%",
            PostgreSQLOperatorArity.BINARY,
            (_builtin("text"), _builtin("text")),
        )
    )
    assert _source_spelling(operator.result_type) == "bool"
    assert operator.evidence.exposure is ExtensionCatalogExposure.DIRECT_SQL_SURFACE
    assert operator.evidence.source_positions == (1, 2)

    exact_spellings = {
        _source_spelling(type_use)
        for entry in PG_TRGM_V16_POSTGRESQL18_CATALOG.entries
        if isinstance(entry, ExtensionScalarFunctionCatalogEntry)
        for type_use in (*entry.declaration.input_types, entry.result_type)
        if type_use.kind is ExtensionCatalogDeclarationTypeUseKind.EXACT
    }
    assert {"float4", "float8", "smallint", "int2", "int4", '"char"'} <= exact_spellings
    assert "real" not in exact_spellings


def test_pg_trgm_canonical_identity_and_reconstruction_are_exact() -> None:
    catalog = PG_TRGM_V16_POSTGRESQL18_CATALOG
    assert len(catalog.canonical_bytes) == EXPECTED_CANONICAL_BYTES
    assert catalog.content_sha256 == EXPECTED_CONTENT_SHA256
    rebuilt = pg_trgm_catalog._build_pg_trgm_catalog()
    assert rebuilt is not catalog
    assert rebuilt.canonical_bytes == catalog.canonical_bytes
    assert rebuilt.content_sha256 == catalog.content_sha256


def test_real_pg_trgm_direct_surface_reaches_checker_satisfied(tmp_path: Path) -> None:
    scope = _scalar_scope("similarity", _builtin("text"), _builtin("text"))
    key = _key("similarity")
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
    assert result.checks[0].status is CapabilityRequirementStatus.SATISFIED
    assert isinstance(result.checks[0].provider_result, Found)
    assert result.checks[0].provider_result.fact.support is CapabilitySupport.SUPPORTED


def test_real_pg_trgm_fail_closed_provider_cases_are_exact() -> None:
    unmodeled = _provider_result(
        _key("show trgm"),
        _scalar_scope("show_trgm", _builtin("text")),
    )
    assert unmodeled == Unknown(CapabilityReasonCode.EXTENSION_CATALOGED_UNMODELED)

    support = _provider_result(
        _key("similarity operator implementation"),
        _scalar_scope("similarity_op", _builtin("text"), _builtin("text")),
    )
    assert support == Unknown(
        CapabilityReasonCode.EXTENSION_CATALOG_NOT_PROVIDER_ELIGIBLE
    )

    missing_scope = _scalar_scope("not_declared", _builtin("text"))
    missing = _provider_result(_key("missing"), missing_scope)
    assert missing == Unknown(
        CapabilityReasonCode.EXTENSION_CATALOG_COMPLETENESS_UNAVAILABLE
    )

    alias = _provider_result(
        _key("wrong extension", extension="trgm"),
        missing_scope,
    )
    assert alias == Unknown(CapabilityReasonCode.EXTENSION_CATALOG_TARGET_MISMATCH)

    wrong_target = ExtensionCatalogTarget("PostgreSQL", "17", "pg_trgm", "1.6")
    wrong_selection = _selection(wrong_target)
    assert wrong_selection.outcome is ExtensionCatalogSelectionOutcome.UNDECLARED
    wrong_release = _provider_result(
        _key("wrong PostgreSQL release"),
        _scalar_scope("similarity", _builtin("text"), _builtin("text")),
        wrong_selection,
    )
    assert wrong_release == Unknown(CapabilityReasonCode.EXTENSION_CATALOG_UNDECLARED)


def test_ltree_probe_is_frozen_nonproduction_and_has_no_schema_gap() -> None:
    spec = SPEC.read_text(encoding="utf-8")
    for value in (
        "c2cbeda96c73439b3033bcb00547fcd9bca8cd5f",
        "1c3543303f0ab96d2bdb1832f9ad6d43699cae75",
        "d46f5fcd02eb6a4ecec6d07fb8356c3f29c6b7b7",
        "e38e76b31e2defa6a26ca588c7043745d31cd574",
        "bc9a34dd591d1e4aba702cf8d0259dbb02c6b6be",
        "| Source tag | `REL_18_6` |",
        "| Extension release | `1.3` |",
        "| `NATIVE_TYPE` | 4 |",
        "| `SCALAR_FUNCTION` | 80 |",
        "| `OPERATOR` | 49 |",
        "| **Five-family total** | **133** |",
        "| `REPRESENTABLE_EXACT` | 61 |",
        "| `REPRESENTABLE_UNMODELED` | 72 |",
        "| `OUT_OF_SCOPE_BY_PHASE57` | 50 |",
        "| `SCHEMA_GAP` | 0 |",
        "ltree_gist",
        "_ltree",
        "_lquery",
        "native/native operators",
        "native-array/native-array combinations",
    ):
        assert value in spec
    assert not (REPO_ROOT / "src/pietto/semantic/extension_catalog_ltree.py").exists()


def test_postgis_bounded_audit_is_frozen_nonproduction_and_has_no_schema_gap() -> None:
    spec = SPEC.read_text(encoding="utf-8")
    for value in (
        "e174f9c3c7576f6a4eba6f98f5f7cf0f13cfeb3a",
        "94d984bd083635c1d253db0f87cf80b32548e406",
        "554b990454bcf7f30016b3ee70c41c6adc4d82f6",
        "3e679906b409d0fc99c2981026f83c2ecafb59c0",
        "88ef35afdf61d1889b4a9be5d247271871902985",
        "710c24e4254ca090b653404a0b76507fd44f85c2",
        "ced61b8c74e6345a956d8b6f730a62c80adb6761",
        "9009a74202c481d4101efb709656f93cdfc90bdf",
        "d8bbfa312c796746b648da289fa7c79638a78553",
        "release date: 2026-06-08",
        "| **Raw five-family declarations** | **824** |",
        "| **Five-family subtotal** | **20** | **12** | **32** |",
        "| **`OUT_OF_SCOPE_BY_PHASE57` subtotal** | **4** |",
        "| **Bounded corpus total** | **36** |",
        "`SCHEMA_GAP` is zero",
        "ST_Dump(geometry) RETURNS SETOF geometry_dump",
        "ST_AsMVT(anyelement)",
        "No `VARIADIC` declaration occurs",
        "SUPPORT postgis_index_supportfn",
        "generated/multi-source SQL assembly authority",
    ):
        assert value in spec
    assert "did not run SQLPP, Perl, Make, PostgreSQL, extension installation" in (
        " ".join(spec.split())
    )
    assert not (REPO_ROOT / "src/pietto/semantic/extension_catalog_postgis.py").exists()
    assert "full PostGIS support" not in spec


def test_private_offline_boundaries_package_and_predecessors_are_unchanged() -> None:
    assert pg_trgm_catalog.__all__ == ()
    for module in (pietto, semantic_package, project_package):
        assert not hasattr(module, "PG_TRGM_V16_POSTGRESQL18_CATALOG")
    assert "extension_catalog_pg_trgm" not in inspect.getsource(catalog_availability)
    assert "extension_catalog_pg_trgm" not in inspect.getsource(semantic_providers)
    assert "extension_catalog_pg_trgm" not in inspect.getsource(capability_inspection)
    source = inspect.getsource(pg_trgm_catalog).lower()
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
        "select_extension_catalog",
        "declaredextensioncatalogavailability",
        "create extension",
    ):
        assert forbidden not in source
    assert extension_catalog.__all__ == ()
    assert PGVECTOR_V086_POSTGRESQL18_CATALOG.content_sha256 == EXPECTED_PGVECTOR_SHA256
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
    assert 'version = "0.1.0"' in (REPO_ROOT / "pyproject.toml").read_text(
        encoding="utf-8"
    )


def test_spec_lifecycle_reader_closure_and_package_smoke_are_exact() -> None:
    spec = SPEC.read_text(encoding="utf-8")
    for heading in (
        "# A. pg_trgm Production Catalog",
        "# B. ltree 1.3 Representability Probe",
        "# C. PostGIS 3.6.4 Bounded Stress Audit",
    ):
        assert heading in spec
    for value in (
        EXPECTED_POSTGRES_REVISION,
        "1d6a9ddf259944cff08191edad2f2b44d399352f",
        "07bfcac93191ed91822e24e7a746e87ac3e9d0df",
        "4c6edf8c245143ef6412fecddd14f8a9e497444a",
        "64a0c219b5cbbd9ee01c53a254769c2744ddb9b0",
        "db122fce0ffcc32f4c34c15d6f37b5343d7e8cae",
        "9e74684eaddbebecb937350d86676a8d57671f0b",
        "| **Total** | **42** | **42** |",
        "| Matchability | `EXACT_MATCHABLE` | 26 |",
        "| Matchability | `CATALOGED_UNMODELED` | 16 |",
        "canonical byte length: 216386",
        EXPECTED_CONTENT_SHA256,
    ):
        assert value in spec
    roadmap = ROADMAP.read_text(encoding="utf-8")
    status = STATUS.read_text(encoding="utf-8")
    assert "Phase 57 is active, Slices 1–12 are completed, and Slice 13 is current" in (
        roadmap
    )
    assert "| Slices 1–12 | `COMPLETED` |" in status
    assert "| Slice 13 | `CURRENT` |" in status
    assert "| Phase 58 | `UNSTARTED / NOT AUTHORIZED` |" in status
    assert "| Next | `PHASE57_SLICE13_END_TO_END` |" in status
    assert "does not authorize Phase 58" in " ".join(status.split())
    package_smoke = PACKAGE_SMOKE.read_text(encoding="utf-8")
    assert 'f"{prefix}/semantic/extension_catalog_pg_trgm.py"' in package_smoke
    assert '"import pietto.semantic.extension_catalog_pg_trgm"' in package_smoke
