from __future__ import annotations

import ast
from collections import Counter
from dataclasses import fields
import hashlib
import inspect
from pathlib import Path
import re

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
import test_phase56_slice10_completion_audit_phase57_handoff as phase56
import test_phase57_slice1_postgresql_extension_signature_catalog_scope_lock as slice1
import test_phase57_slice10_pg_trgm_ltree_postgis_representability as slice10
import test_phase57_slice11_extension_catalog_inspection as slice11
import test_phase57_slice12_extension_catalog_pure_boundary_differential_and_e2e as slice12
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
ROADMAP = REPO_ROOT / "docs/roadmap.md"
STATUS = REPO_ROOT / "docs/status.md"
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

_SLICE_AUTHORITIES = (
    (
        "1",
        "docs/spec/phase57-postgresql-extension-signature-catalog-scope-lock-v1.md",
        "tests/test_phase57_slice1_postgresql_extension_signature_catalog_scope_lock.py",
    ),
    (
        "2",
        "docs/spec/phase57-extension-catalog-schema-identity-target-source-provenance-v1.md",
        "tests/test_phase57_slice2_extension_catalog_schema_identity_target_source_provenance.py",
    ),
    (
        "3",
        "docs/spec/phase57-extension-catalog-structured-type-physical-identity-v1.md",
        "tests/test_phase57_slice3_extension_catalog_structured_type_physical_identity.py",
    ),
    (
        "4",
        "docs/spec/phase57-extension-catalog-entry-matchability-contract-v1.md",
        "tests/test_phase57_slice4_extension_catalog_entry_matchability_contract.py",
    ),
    (
        "5",
        "docs/spec/phase57-extension-catalog-construction-completeness-canonical-v1.md",
        "tests/test_phase57_slice5_extension_catalog_construction_completeness_canonical.py",
    ),
    (
        "6",
        "docs/spec/phase57-extension-catalog-declaration-availability-selection-v1.md",
        "tests/test_phase57_slice6_extension_catalog_declaration_availability_selection.py",
    ),
    (
        "7",
        "docs/spec/phase57-extension-signature-requirement-selector-v1.md",
        "tests/test_phase57_slice7_extension_signature_requirement_selector.py",
    ),
    (
        "8",
        "docs/spec/phase57-extension-signature-provider-checking-integration-v1.md",
        "tests/test_phase57_slice8_extension_signature_provider_checking_integration.py",
    ),
    (
        "9",
        "docs/spec/phase57-pgvector-v086-postgresql18-catalog-v1.md",
        "tests/test_phase57_slice9_pgvector_v086_postgresql18_catalog.py",
    ),
    (
        "10",
        "docs/spec/phase57-pg-trgm-ltree-postgis-representability-v1.md",
        "tests/test_phase57_slice10_pg_trgm_ltree_postgis_representability.py",
    ),
    (
        "11",
        "docs/spec/phase57-extension-catalog-inspection-v1.md",
        "tests/test_phase57_slice11_extension_catalog_inspection.py",
    ),
    (
        "12",
        "docs/spec/phase57-extension-catalog-pure-boundary-differential-e2e-v1.md",
        "tests/test_phase57_slice12_extension_catalog_pure_boundary_differential_and_e2e.py",
    ),
    (
        "13",
        "docs/spec/phase57-completion-audit-phase58-handoff-v1.md",
        "tests/test_phase57_slice13_completion_audit_phase58_handoff.py",
    ),
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

_CLOSED_SUBJECTS = frozenset(
    (
        "Extension catalog schema, target, and source provenance",
        "Structured physical type and object identity",
        "Five catalog entry families",
        "Exact versus unmodeled declaration preservation",
        "Exposure classification",
        "Deterministic catalog construction",
        "Entry conflict",
        "Lookup-scoped completeness",
        "Canonical bytes and content SHA-256",
        "Compiler and project availability",
        "Exact catalog selection",
        "Typed extension-signature requirement selector",
        "Target-scoped catalog provider",
        "Checker and matrix integration",
        "pgvector production catalog",
        "pg_trgm production catalog",
        "ltree representability audit",
        "PostGIS bounded stress audit",
        "Extension-catalog inspection",
        "Catalog and inspection pure boundaries",
        "Differential corpus",
        "Python 3.12 and 3.13 parity",
        "Hash-seed invariance",
        "Relocation invariance",
        "Combined version, seed, and relocation branches",
        "Installed-wheel pure evaluation",
    )
)

_TRANSFERRED_SUBJECTS = {
    "Public explain artifact": "Phase 58",
    "Public portability representation and classification": "Phase 58",
    "Public package-inspection-facing capability metadata projection": "Phase 58",
    "Local package graph": "Phase 59",
    "Cross-artifact attribution": "Phase 59",
    "Full provenance and lineage graph from retained positions": "Phase 59",
    "Array type semantics": "Phase 64",
    "Typmods and parameterized PostgreSQL type semantics": "Phase 64",
    "Composite and table-return type semantics": "Phase 64",
    "Advanced coercion and promotion": "Phase 64",
    "Temporal, Decimal, and native mapping": "Phase 64",
    "Advanced physical and logical type compatibility": "Phase 64",
    "Extension catalogs as possible advanced semantic-package assets": "Phase 66",
    "Remote catalog/package acquisition and trust": "Phase 67",
    "Dependency solving and canonical lockfile interaction": "Phase 68",
    "Release-aware PostgreSQL core builtin signature catalog": "Phase 69",
    "Backend-specific core catalog foundation beyond Phase 57 extensions": "Phase 69",
    "Extension-specific SQL lowering": "Phase 69",
    "Generated and multi-source catalog assembly for any future full PostGIS catalog": "Phase 69",
    "Additional dialect extension and plugin foundations": "Phase 69",
}

_OUT_OF_SCOPE_SUBJECTS = frozenset(
    (
        "Live database probing",
        "Installation detection",
        "CREATE EXTENSION execution",
        "Server OID and runtime identity discovery",
        "Runtime extension verification",
    )
)

_NOT_REQUIRED_SUBJECTS = frozenset(
    (
        "Production ltree catalog",
        "Full PostGIS production catalog",
        "TimescaleDB catalog",
    )
)

_EXIT_CRITERIA = tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + (
    "AA",
    "AB",
    "AC",
    "AD",
    "AE",
    "AF",
)


def _table(section: str) -> tuple[tuple[str, ...], ...]:
    return slice1._table_rows(section)[1:]


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


def test_all_13_slice_owners_have_independent_spec_source_and_test_authority() -> None:
    document = SPEC.read_text(encoding="utf-8")
    rows = _table(slice1._section(document, "13-slice Completion Matrix"))
    assert len(rows) == len(_SLICE_AUTHORITIES) == 13
    assert tuple((row[0], row[1].replace("`", "")) for row in rows) == (
        slice1.EXPECTED_ROUTE
    )
    for row, (position, spec, test) in zip(rows, _SLICE_AUTHORITIES, strict=True):
        assert row[0] == position
        assert row[2] == f"`{spec}`"
        assert row[4] == f"`{test}`"
        assert row[3] and row[5]
        assert row[6] in {"`EVIDENCED`", "`EVIDENCED_PENDING_NATURAL_CI`"}
        assert (REPO_ROOT / spec).is_file()
        assert (REPO_ROOT / test).is_file()
    assert {path.name for path in (REPO_ROOT / "docs/spec").glob("phase57-*.md")} == {
        Path(spec).name for _, spec, _ in _SLICE_AUTHORITIES
    }
    assert all((REPO_ROOT / path).is_file() for path in _PHASE57_PRODUCTION_PATHS)
    assert "ownership obligations evidenced: 13 / 13" in document


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
    assert "extension_catalog" not in inspect.getsource(package_manifest)
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


def test_representability_audits_are_frozen_without_production_claims() -> None:
    authority = slice10.SPEC.read_text(encoding="utf-8")
    for literal in (
        "| **Five-family total** | **133** |",
        "| `REPRESENTABLE_EXACT` | 61 |",
        "| `REPRESENTABLE_UNMODELED` | 72 |",
        "| `OUT_OF_SCOPE_BY_PHASE57` | 50 |",
        "| `SCHEMA_GAP` | 0 |",
        "94d984bd083635c1d253db0f87cf80b32548e406",
        "| **Raw five-family declarations** | **824** |",
        "| **Bounded corpus total** | **36** |",
        "| **Five-family subtotal** | **20** | **12** | **32** |",
        "| **`OUT_OF_SCOPE_BY_PHASE57` subtotal** | **4** |",
        "`SCHEMA_GAP` is zero",
    ):
        assert literal in authority
    assert "full PostGIS support" not in authority


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

    phase57_rows = slice12._run_corpus()
    assert len(phase57_rows) == 47
    assert all(matched for *_coordinates, matched in phase57_rows)
    assert slice12._corpus_digest() == EXPECTED_PHASE57_CORPUS_DIGEST
    phase57_corpus = slice12.vectors.differential_vectors()
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
    assert slice12._SUPPORTED_INTERPRETERS == ((3, 12), (3, 13))
    assert slice12._SEEDS == (None, "0", "1", "4294967295")
    harness = inspect.getsource(slice12._build_witness_matrix)
    for required in (
        "_available_supported_interpreters",
        "slice12-relocated-one",
        "slice12-relocated-two",
        "combined:python3.12:seed1:relocated-one",
        "combined:python3.13:seed4294967295:relocated-two",
    ):
        assert required in harness

    phase56_corpus = phase56.vectors.differential_vectors()
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
    assert phase56._corpus_digest() == EXPECTED_PHASE56_CORPUS_DIGEST
    assert CapabilityInspectionFormat.CAPABILITY_INSPECTION_V1.value == (
        "pietto.capability-inspection.v1"
    )


def test_deferred_subject_ledger_is_complete_terminal_and_owner_exact() -> None:
    document = SPEC.read_text(encoding="utf-8")
    rows = _table(slice1._section(document, "Deferred-subject Ledger"))
    assert len({row[0] for row in rows}) == len(rows)
    by_disposition: dict[str, set[str]] = {}
    for subject, disposition, owner in rows:
        by_disposition.setdefault(disposition.strip("`"), set()).add(subject)
        assert owner
    assert set(by_disposition) == {
        "CLOSED",
        "TRANSFERRED_TO_EXACT_LATER_OWNER",
        "INTENTIONALLY_OUT_OF_SCOPE",
        "INTENTIONALLY_NOT_REQUIRED",
    }
    assert by_disposition["CLOSED"] == _CLOSED_SUBJECTS
    assert by_disposition["INTENTIONALLY_OUT_OF_SCOPE"] == _OUT_OF_SCOPE_SUBJECTS
    assert by_disposition["INTENTIONALLY_NOT_REQUIRED"] == _NOT_REQUIRED_SUBJECTS
    transferred = {
        subject: next(row[2] for row in rows if row[0] == subject)
        for subject in by_disposition["TRANSFERRED_TO_EXACT_LATER_OWNER"]
    }
    assert set(transferred) == set(_TRANSFERRED_SUBJECTS)
    assert all(
        owner in transferred[subject]
        for subject, owner in _TRANSFERRED_SUBJECTS.items()
    )
    assert "PHASE57_SELF_OWNED_OPEN = 0" in document
    assert not {
        "OPEN",
        "UNASSIGNED",
        "TBD",
        "UNKNOWN_OWNER",
        "PHASE57_DEFERRED",
    } & set(by_disposition)


def test_non_generalizations_and_all_32_exit_criteria_are_locked() -> None:
    document = SPEC.read_text(encoding="utf-8")
    non_generalizations = slice1._section(document, "Non-generalizations")
    assert len(re.findall(r"^\d+\. ", non_generalizations, flags=re.MULTILINE)) == 24
    for required in (
        "Catalog existence does not prove declaration availability",
        "Declaration availability does not prove installation",
        "Catalog selection does not prove server or runtime presence",
        "Catalog completeness is lookup-scoped",
        "Catalog omission is not explicit unsupported evidence",
        "CATALOGED_UNMODELED",
        "DIRECT_SQL_SURFACE",
        "IMPLEMENTATION_SUPPORT",
        "A selected catalog does not create target-profile support",
        "CapabilityKey",
        "closed typed bridge",
        "pgvector support does not imply",
        "pg_trgm support does not imply",
        "ltree audit does not constitute",
        "PostGIS stress representability does not constitute",
        "PostgreSQL 18 catalog targets do not imply compatibility ranges",
        "not signing or attestation",
        "not catalog content identity",
        "not public explain output",
        "not decided by the Phase 57 matrix",
        "no SQL lowering",
        "no database runtime or installation authority",
        "not package assets or registry entries",
        "No future roadmap owner is implementation authorization",
    ):
        assert required in non_generalizations

    rows = _table(slice1._section(document, "Exit-criteria Matrix"))
    assert tuple(row[0] for row in rows) == _EXIT_CRITERIA
    assert all(row[1] == "`PASS`" and row[2] for row in rows)
    assert "passed criteria: 32" in document
    assert "total criteria: 32" in document


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


def test_candidate_lifecycle_version_future_owner_and_history_are_exact() -> None:
    roadmap = ROADMAP.read_text(encoding="utf-8")
    status = STATUS.read_text(encoding="utf-8")
    document = SPEC.read_text(encoding="utf-8")
    assert (
        "Phase 58 is active, Slices 1–2 are completed, Slice 3 is current, and Slice 4 is next / unstarted"
        in (roadmap)
    )
    assert "Phase 57 Slice 13 completion audit" in roadmap
    assert "Release-aware PostgreSQL core builtin signature catalog" in roadmap
    assert "generated/multi-source extension catalog assembly" in roadmap
    assert "| Phase 57 | `COMPLETED` |" in status
    assert "| Phase 58 | `ACTIVE` |" in status
    assert "| Slice 1 | `COMPLETED` |" in status
    assert "| Slice 2 | `COMPLETED` |" in status
    assert "| Slice 3 | `CURRENT` |" in status
    assert "| Slice 4 | `NEXT / UNSTARTED` |" in status
    assert "| Next | `PHASE58_SLICE4_END_TO_END` |" in status
    assert "does not authorize Slice 4" in " ".join(status.split())
    assert 'version = "0.1.0"' in (REPO_ROOT / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    for retained in (
        "32667331766",
        "77ce1c6967956f35cee33704330b99d2cd0a4dd3",
        "38b7e53c4478e82482d5a788335d8db34d673ccf",
    ):
        assert retained in document
