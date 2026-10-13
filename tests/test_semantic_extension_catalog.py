from __future__ import annotations

import ast
from collections import Counter
from dataclasses import fields
import hashlib
import inspect
from pathlib import Path

import _pietto_project_capability as capability_helpers
import _pietto_project_extension_differential as differential
import pietto
import pietto._project as project_package
import pietto._project.capability_checking as capability_checking
import pietto._project.capability_matrix as capability_matrix
import pietto._project.capability_pure_boundary as capability_pure
import pietto._project.extension_catalog_availability as catalog_availability
import pietto._project.extension_catalog_inspection as inspection_runtime
import pietto._project.extension_catalog_inspection_pure_boundary as inspection_pure
import pietto._project.extension_signature_provider as extension_provider
import pietto._project.package_inspection as package_inspection
import pietto._project.package_manifest as package_manifest
import pietto._project.package_pure_boundary as package_pure
import pietto.semantic as semantic_package
import pietto.semantic.capability_facts as capability_facts
import pietto.semantic.capability_providers as semantic_providers
import pietto.semantic.extension_catalog as catalog_runtime
import pietto.semantic.extension_catalog_pg_trgm as pg_trgm_module
import pietto.semantic.extension_catalog_pgvector as pgvector_module
import pietto.semantic.extension_catalog_pure_boundary as catalog_pure
import pietto.semantic.extension_signature_requirements as selectors
import _pietto_project_extension_inspection as slice11
from pietto._project.capability_checking import CapabilityRequirementStatus
from pietto._project.capability_inspection import (
    CapabilityInspectionFactSet,
    CapabilityInspectionFormat,
)
from pietto._project.capability_matrix import PackageCapabilityCheckingMatrix
from pietto._project.extension_catalog_availability import (
    ExtensionCatalogSelectionOutcome,
)
from pietto._project.extension_catalog_inspection import (
    ExtensionCatalogInspectionFactSet,
    ExtensionCatalogInspectionFormat,
)
from pietto._project.package_inspection import (
    PackageInspectionFactSet,
    PackageInspectionFormat,
)
from pietto.semantic.capability_facts import CapabilityKey
from pietto.semantic.extension_catalog import (
    ConstructedExtensionCatalog,
    ExtensionCatalogEntryFamily,
    ExtensionCatalogExactEntryGroupState,
    ExtensionCatalogExposure,
    ExtensionCatalogMatchability,
    _entry_family,
)
from pietto.semantic.extension_catalog_pg_trgm import (
    PG_TRGM_V16_POSTGRESQL18_CATALOG,
)
from pietto.semantic.extension_catalog_pgvector import (
    PGVECTOR_V086_POSTGRESQL18_CATALOG,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "docs/spec/phase57-completion-audit-phase58-handoff-v1.md"
PACKAGE_SMOKE = REPO_ROOT / "scripts/package_smoke.py"

EXPECTED_PHASE57_CORPUS_DIGEST = (
    "2cad48b2f2a1e8d55ae4b685408ffcf909fd01abe233068a5c5643d486976244"
)
EXPECTED_PHASE56_CORPUS_DIGEST = (
    "8453c3babda888b105f37f667f5fadf3a12aa68ca9a561bda98e5f6b6604a69e"
)
EXPECTED_PGVECTOR = (
    993469,
    "686e68fe9d60c20cb276e2b26007d310ff8877a5b4a8274e5c9194116fa74654",
)
EXPECTED_PG_TRGM = (
    216386,
    "09eb10a0660a05ca180d43a23f1eda7aaf4b6198f5de249591317194cc9576b7",
)
EXPECTED_INSPECTION = (
    540042,
    "7710033bd7b1b939bee3f3da1f4d354b7d53db385a36e61f538bc4aacf8fb4ce",
)

_PHASE57_PRODUCTION_PATHS = (
    "src/pietto/semantic/capability_facts.py",
    "src/pietto/semantic/extension_catalog.py",
    "src/pietto/semantic/extension_catalog_pgvector.py",
    "src/pietto/semantic/extension_catalog_pg_trgm.py",
    "src/pietto/semantic/extension_catalog_pure_boundary.py",
    "src/pietto/semantic/extension_signature_requirements.py",
    "src/pietto/_project/capability_checking.py",
    "src/pietto/_project/capability_matrix.py",
    "src/pietto/_project/capability_pure_boundary.py",
    "src/pietto/_project/extension_catalog_availability.py",
    "src/pietto/_project/extension_signature_provider.py",
    "src/pietto/_project/extension_catalog_inspection.py",
    "src/pietto/_project/extension_catalog_inspection_pure_boundary.py",
)

_PHASE57_MODULES = (
    capability_facts,
    catalog_runtime,
    pgvector_module,
    pg_trgm_module,
    catalog_pure,
    selectors,
    capability_checking,
    capability_matrix,
    capability_pure,
    catalog_availability,
    extension_provider,
    inspection_runtime,
    inspection_pure,
)


def _catalog_observation(catalog: ConstructedExtensionCatalog) -> tuple[object, ...]:
    return (
        Counter(_entry_family(entry) for entry in catalog.entries),
        Counter(entry.evidence.matchability for entry in catalog.entries),
        Counter(entry.evidence.exposure for entry in catalog.entries),
        Counter(group.state for group in catalog.exact_entry_groups),
        len(catalog.completeness_claims),
        len(catalog.completeness_groups),
        len(catalog.canonical_bytes),
        catalog.content_sha256,
        hashlib.sha256(catalog.canonical_bytes).hexdigest(),
    )


def test_phase57_modules_are_private_static_nonexecuting_and_not_public() -> None:
    assert all(module.__all__ == () for module in _PHASE57_MODULES)
    for name in (
        "ExtensionCatalogReference",
        "ConstructedExtensionCatalog",
        "PGVECTOR_V086_POSTGRESQL18_CATALOG",
        "PG_TRGM_V16_POSTGRESQL18_CATALOG",
        "ExtensionSignatureRequirementSelector",
        "DeclaredExtensionCatalogAvailability",
        "ExtensionSignatureProviderAuthority",
        "ExtensionCatalogInspection",
        "ExtensionCatalogPureDocument",
        "ExtensionCatalogInspectionPureDocument",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(semantic_package, name)
        assert not hasattr(project_package, name)

    phase57_specific = (
        *_PHASE57_PRODUCTION_PATHS[1:6],
        *_PHASE57_PRODUCTION_PATHS[9:],
    )
    for path in phase57_specific:
        source = (REPO_ROOT / path).read_text(encoding="utf-8")
        for forbidden in (
            "CREATE EXTENSION",
            "import requests",
            "import socket",
            "import subprocess",
            "psycopg",
            "sqlalchemy",
            "getcwd",
            "os.environ",
            "open(",
        ):
            assert forbidden not in source
    manifest_source = inspect.getsource(package_manifest)
    manifest_tree = ast.parse(manifest_source)
    assert tuple(
        (alias.name, alias.asname)
        for node in ast.walk(manifest_tree)
        if isinstance(node, ast.ImportFrom)
        and node.module == "pietto.semantic.extension_catalog"
        for alias in node.names
    ) == (
        ("ExtensionCatalogEntryFamily", None),
        ("ExtensionCatalogLookupScope", None),
        ("ExtensionCatalogTypeReference", None),
        ("ExtensionCatalogTypeReferenceKind", None),
        ("PostgreSQLCallableIdentity", None),
        ("PostgreSQLCastIdentity", None),
        ("PostgreSQLOperatorArity", None),
        ("PostgreSQLOperatorIdentity", None),
    )
    imported_modules = {
        node.module
        for node in ast.walk(manifest_tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    } | {
        alias.name
        for node in ast.walk(manifest_tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert imported_modules.isdisjoint(
        {
            "pietto._project.capability_checking",
            "pietto._project.capability_inspection",
            "pietto._project.capability_matrix",
            "pietto._project.extension_catalog_availability",
            "pietto._project.extension_catalog_inspection",
            "pietto._project.extension_signature_provider",
        }
    )
    assert "select_extension_catalog" not in manifest_source
    assert "ExtensionCatalogSelectionResult" not in manifest_source
    assert not (REPO_ROOT / "src/pietto/semantic/extension_catalog_ltree.py").exists()
    assert not (REPO_ROOT / "src/pietto/semantic/extension_catalog_postgis.py").exists()
    assert not (
        REPO_ROOT / "src/pietto/_project/extension_catalog_registry.py"
    ).exists()


def test_identity_selection_provider_checker_and_matrix_locks_are_exact() -> None:
    assert tuple(field.name for field in fields(CapabilityKey)) == (
        "domain",
        "subject",
        "operation",
        "operands",
        "context",
        "dialect",
        "extension",
    )
    assert tuple(ExtensionCatalogSelectionOutcome) == (
        ExtensionCatalogSelectionOutcome.UNDECLARED,
        ExtensionCatalogSelectionOutcome.SELECTED,
        ExtensionCatalogSelectionOutcome.AMBIGUOUS,
        ExtensionCatalogSelectionOutcome.CONFLICT,
    )
    bridge = selectors.extension_signature_dialect_family_bridge("postgresql")
    assert bridge is not None
    assert bridge.database_family == "PostgreSQL"
    assert selectors.extension_signature_dialect_family_bridge("PostgreSQL") is None
    assert "select_extension_catalog(" not in inspect.getsource(extension_provider)
    assert "select_extension_catalog(" not in inspect.getsource(inspection_runtime)
    assert "extension_catalog" not in inspect.getsource(semantic_providers)

    status_source = inspect.getsource(capability_checking._derive_requirement_status)
    assert tuple(
        status_source.index(f"CapabilityRequirementStatus.{status.name}")
        for status in (
            CapabilityRequirementStatus.CONFLICT,
            CapabilityRequirementStatus.UNSUPPORTED,
            CapabilityRequirementStatus.ABSENT,
            CapabilityRequirementStatus.UNKNOWN,
            CapabilityRequirementStatus.SATISFIED,
        )
    ) == tuple(
        sorted(
            status_source.index(f"CapabilityRequirementStatus.{status.name}")
            for status in (
                CapabilityRequirementStatus.CONFLICT,
                CapabilityRequirementStatus.UNSUPPORTED,
                CapabilityRequirementStatus.ABSENT,
                CapabilityRequirementStatus.UNKNOWN,
                CapabilityRequirementStatus.SATISFIED,
            )
        )
    )
    matrix_source = inspect.getsource(capability_matrix)
    for forbidden in ("best_target", "worst_status", "portability_classifier"):
        assert forbidden not in matrix_source


def test_both_production_catalogs_are_exact_current_runtime_objects() -> None:
    vector = PGVECTOR_V086_POSTGRESQL18_CATALOG
    assert (
        vector.metadata.catalog.identity.namespace,
        vector.metadata.catalog.identity.name,
        vector.metadata.catalog.release,
    ) == ("pietto.postgresql", "pgvector", "1")
    assert (
        vector.metadata.target.database_family,
        vector.metadata.target.database_release,
        vector.metadata.target.extension_identity,
        vector.metadata.target.extension_release,
    ) == ("PostgreSQL", "18", "vector", "0.8.6")
    assert len(vector.metadata.source_occurrences) == 4
    assert len(vector.entries) == 184
    assert _catalog_observation(vector) == (
        Counter(
            {
                ExtensionCatalogEntryFamily.NATIVE_TYPE: 3,
                ExtensionCatalogEntryFamily.SCALAR_FUNCTION: 114,
                ExtensionCatalogEntryFamily.AGGREGATE: 4,
                ExtensionCatalogEntryFamily.OPERATOR: 40,
                ExtensionCatalogEntryFamily.CAST: 23,
            }
        ),
        Counter(
            {
                ExtensionCatalogMatchability.EXACT_MATCHABLE: 131,
                ExtensionCatalogMatchability.CATALOGED_UNMODELED: 53,
            }
        ),
        Counter(
            {
                ExtensionCatalogExposure.DIRECT_SQL_SURFACE: 96,
                ExtensionCatalogExposure.IMPLEMENTATION_SUPPORT: 88,
            }
        ),
        Counter({ExtensionCatalogExactEntryGroupState.UNIQUE: 131}),
        0,
        0,
        EXPECTED_PGVECTOR[0],
        EXPECTED_PGVECTOR[1],
        EXPECTED_PGVECTOR[1],
    )

    trgm = PG_TRGM_V16_POSTGRESQL18_CATALOG
    assert (
        trgm.metadata.catalog.identity.namespace,
        trgm.metadata.catalog.identity.name,
        trgm.metadata.catalog.release,
    ) == ("pietto.postgresql", "pg_trgm", "1")
    assert (
        trgm.metadata.target.database_family,
        trgm.metadata.target.database_release,
        trgm.metadata.target.extension_identity,
        trgm.metadata.target.extension_release,
    ) == ("PostgreSQL", "18", "pg_trgm", "1.6")
    assert len(trgm.metadata.source_occurrences) == 6
    assert len(trgm.entries) == 42
    assert _catalog_observation(trgm) == (
        Counter(
            {
                ExtensionCatalogEntryFamily.NATIVE_TYPE: 1,
                ExtensionCatalogEntryFamily.SCALAR_FUNCTION: 31,
                ExtensionCatalogEntryFamily.OPERATOR: 10,
            }
        ),
        Counter(
            {
                ExtensionCatalogMatchability.EXACT_MATCHABLE: 26,
                ExtensionCatalogMatchability.CATALOGED_UNMODELED: 16,
            }
        ),
        Counter(
            {
                ExtensionCatalogExposure.DIRECT_SQL_SURFACE: 16,
                ExtensionCatalogExposure.IMPLEMENTATION_SUPPORT: 26,
            }
        ),
        Counter({ExtensionCatalogExactEntryGroupState.UNIQUE: 26}),
        0,
        0,
        EXPECTED_PG_TRGM[0],
        EXPECTED_PG_TRGM[1],
        EXPECTED_PG_TRGM[1],
    )


def test_inspection_pure_boundaries_and_both_corpora_are_zero_delta() -> None:
    fact_set = slice11._inspection(slice11._production_context())
    assert fact_set.inspection.format is (
        ExtensionCatalogInspectionFormat.EXTENSION_CATALOG_INSPECTION_V1
    )
    assert (
        len(fact_set.canonical_bytes),
        hashlib.sha256(fact_set.canonical_bytes).hexdigest(),
    ) == EXPECTED_INSPECTION

    for catalog in (
        PGVECTOR_V086_POSTGRESQL18_CATALOG,
        PG_TRGM_V16_POSTGRESQL18_CATALOG,
    ):
        outcome = catalog_pure.evaluate_extension_catalog_document(
            catalog_runtime._extension_catalog_pure_document(
                catalog.metadata,
                catalog.entries,
                catalog.exact_entry_groups,
                catalog.completeness_claims,
                catalog.completeness_groups,
            )
        )
        assert outcome.status is catalog_pure.ExtensionCatalogPureStatus.OK
        assert outcome.canonical_bytes == catalog.canonical_bytes
    inspection_outcome = inspection_pure.evaluate_extension_catalog_inspection_document(
        inspection_runtime._extension_catalog_inspection_pure_document(
            fact_set.inspection
        )
    )
    assert inspection_outcome.status is (
        inspection_pure.ExtensionCatalogInspectionPureStatus.OK
    )
    assert inspection_outcome.canonical_bytes == fact_set.canonical_bytes

    phase57_rows = differential._run_corpus()
    assert len(phase57_rows) == 47
    assert all(matched for *_coordinates, matched in phase57_rows)
    assert differential._corpus_digest() == EXPECTED_PHASE57_CORPUS_DIGEST
    phase57_corpus = differential.vectors.differential_vectors()
    assert Counter(vector.boundary.value for vector in phase57_corpus) == {
        "catalog": 19,
        "inspection": 28,
    }
    assert Counter(
        vector.expected_status.value == "ok" for vector in phase57_corpus
    ) == {True: 14, False: 33}
    assert {
        vector.expected_status
        for vector in phase57_corpus
        if vector.boundary.value == "catalog"
    } == set(catalog_pure.ExtensionCatalogPureStatus)
    assert {
        vector.expected_status
        for vector in phase57_corpus
        if vector.boundary.value == "inspection"
    } == set(inspection_pure.ExtensionCatalogInspectionPureStatus)
    assert differential._SUPPORTED_INTERPRETERS == ((3, 12), (3, 13))
    assert differential._SEEDS == (None, "0", "1", "4294967295")
    harness = inspect.getsource(differential._build_witness_matrix)
    for required in (
        "_available_supported_interpreters",
        "slice12-relocated-one",
        "slice12-relocated-two",
        "combined:python3.12:seed1:relocated-one",
        "combined:python3.13:seed4294967295:relocated-two",
    ):
        assert required in harness

    phase56_corpus = capability_helpers.vectors.differential_vectors()
    accepted = tuple(
        vector
        for vector in phase56_corpus
        if vector.expected_status is capability_pure.CapabilityPureStatus.OK
    )
    assert (
        len(phase56_corpus),
        len(accepted),
        len(phase56_corpus) - len(accepted),
    ) == (
        125,
        16,
        109,
    )
    assert capability_helpers._corpus_digest() == EXPECTED_PHASE56_CORPUS_DIGEST
    assert CapabilityInspectionFormat.CAPABILITY_INSPECTION_V1.value == (
        "pietto.capability-inspection.v1"
    )


def test_phase58_handoff_is_private_eligible_unstarted_and_non_circular() -> None:
    assert PackageInspectionFormat.PACKAGE_INSPECTION_V1.value == (
        "pietto.package-inspection.v1"
    )
    assert package_pure.PACKAGE_PURE_FORMAT_MARKER == "pietto.package-inspection.v1"
    assert tuple(field.name for field in fields(PackageInspectionFactSet)) == (
        "inspection",
        "canonical_bytes",
        "authority",
    )
    assert tuple(field.name for field in fields(CapabilityInspectionFactSet)) == (
        "inspection",
        "canonical_bytes",
        "authority",
    )
    assert tuple(field.name for field in fields(PackageCapabilityCheckingMatrix)) == (
        "package",
        "binding",
        "contexts",
        "columns",
        "rows",
    )
    assert tuple(field.name for field in fields(ExtensionCatalogInspectionFactSet)) == (
        "inspection",
        "canonical_bytes",
        "authority",
    )
    assert package_inspection.__all__ == package_pure.__all__ == ()
    package_smoke = PACKAGE_SMOKE.read_text(encoding="utf-8")
    for module_path in (
        "semantic/extension_catalog_pure_boundary.py",
        "_project/extension_catalog_inspection_pure_boundary.py",
    ):
        assert module_path in package_smoke

    document = SPEC.read_text(encoding="utf-8")
    for state in (
        "Phase 58: ELIGIBLE",
        "Phase 58: UNSTARTED",
        "Phase 58: NOT AUTHORIZED BY SLICE 13",
    ):
        assert state in document
    assert "No Phase 58 schema or production file is created here" in document
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"), filename=__file__)
    assert "_corpus_digest" not in {
        node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    }


def test_candidate_version_future_owner_and_history_are_exact() -> None:
    document = SPEC.read_text(encoding="utf-8")
    assert "Phase 57 Completion Audit And Phase 58 Handoff v1" in document
    assert "Release-aware PostgreSQL core builtin signature catalog" in document
    assert "generated/multi-source extension catalog assembly" in document
    for retained in (
        "32667331766",
        "77ce1c6967956f35cee33704330b99d2cd0a4dd3",
        "38b7e53c4478e82482d5a788335d8db34d673ccf",
    ):
        assert retained in document
