from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
import hashlib
import inspect
from pathlib import Path
from typing import Any, cast
import unicodedata

import pytest

import _pietto_capability_differential_vectors as vectors
import pietto
import pietto._project as project_package
import pietto._project.capability_checking as checking
import pietto._project.capability_inspection as inspection
import pietto._project.capability_matrix as matrix
import pietto._project.capability_pure_boundary as pure_boundary
import pietto._project.package_manifest as package_manifest
import pietto.semantic as semantic_package
import pietto.semantic.capability_aggregates as aggregates
import pietto.semantic.capability_contexts as contexts
import pietto.semantic.capability_inventory as inventory
import pietto.semantic.capability_providers as providers
import pietto.semantic.capability_signatures as signatures
import pietto.semantic.capability_windows as windows
import pietto.semantic.extension_catalog as extension_catalog
from pietto._project.capability_inspection import CapabilityInspectionFormat
from pietto.semantic.capability_facts import (
    CapabilityDomain,
    CapabilityFact,
    CapabilityKey,
    CapabilityReasonCode,
)
from pietto.semantic.capability_lookup import Unknown, lookup_capability
from pietto.semantic.capability_profiles import CapabilityProfileTarget
from pietto.semantic.extension_catalog import (
    ExtensionCatalogIdentity,
    ExtensionCatalogMetadata,
    ExtensionCatalogReference,
    ExtensionCatalogSchemaVersion,
    ExtensionCatalogSourceOccurrence,
    ExtensionCatalogSourceProvenance,
    ExtensionCatalogTarget,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase57-extension-catalog-schema-identity-target-source-provenance-v1.md"
)
ROADMAP = REPO_ROOT / "docs/roadmap.md"
STATUS = REPO_ROOT / "docs/status.md"
PACKAGE_SMOKE = REPO_ROOT / "scripts/package_smoke.py"
EXPECTED_CORPUS_DIGEST = (
    "8453c3babda888b105f37f667f5fadf3a12aa68ca9a561bda98e5f6b6604a69e"
)
EXPECTED_RETAINED_ROUTE = (
    (
        "3",
        "PostgreSQL builtin and extension-native type references, physical SQL object identity, and Phase 64/69 readiness",
    ),
    (
        "4",
        "Five typed catalog entry families, complex-signature metadata, and exact-matchability contracts",
    ),
    (
        "5",
        "Deterministic catalog construction, ordering/conflicts, scoped completeness, canonical bytes, and content SHA-256",
    ),
    (
        "6",
        "Compiler/project catalog declaration and availability, exact PostgreSQL-release × extension-release selection",
    ),
    (
        "7",
        "Structured EXTENSION_SIGNATURE requirement selector authority",
    ),
    (
        "8",
        "EXTENSION_SIGNATURE provider integration using typed selectors, target-scoped catalog lookup, exact checking propagation, and matrix compatibility",
    ),
    ("9", "First concrete production catalog: pgvector"),
    (
        "10",
        "Second concrete production catalog: pg_trgm, plus ltree lightweight representability probe and PostGIS representability/stress audit without full-support claims",
    ),
    (
        "11",
        "Separate private extension-catalog inspection/canonical representation and Phase 58/59 provenance readiness",
    ),
    (
        "12",
        "Extension-catalog pure boundary, differential vectors, Python 3.12/3.13, hash-seed, relocation, and E2E hardening",
    ),
    ("13", "Completion audit and Phase 58 handoff"),
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _section(document: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert document.count(marker) == 1
    start = document.index(marker) + len(marker)
    end = document.find("\n## ", start)
    return document[start:] if end == -1 else document[start:end]


def _table_rows(section: str) -> tuple[tuple[str, ...], ...]:
    return tuple(
        tuple(cell.strip() for cell in line.strip("|").split("|"))
        for line in section.splitlines()
        if line.startswith("| ") and not line.startswith("| ---")
    )


def _reference(
    namespace: str = "org.example.catalogs",
    name: str = "vector",
    release: str = "catalog release 1",
) -> ExtensionCatalogReference:
    return ExtensionCatalogReference(
        ExtensionCatalogIdentity(namespace, name),
        release,
    )


def _target() -> ExtensionCatalogTarget:
    return ExtensionCatalogTarget(
        "PostgreSQL",
        "17.4 vendor build",
        "example_extension",
        "extension release 2",
    )


def _provenance(
    locator: str = "sql/example--2.sql:declaration-7",
) -> ExtensionCatalogSourceProvenance:
    return ExtensionCatalogSourceProvenance(
        "example/upstream",
        "refs/tags/release-2",
        locator,
        "Curated from the upstream declaration without execution",
    )


def _provider_families() -> tuple[tuple[CapabilityFact, ...], ...]:
    return (
        inventory._CAPABILITY_FACTS,
        signatures._CAPABILITY_SIGNATURE_FACTS,
        contexts._CAPABILITY_CONTEXT_FACTS,
        aggregates._AGGREGATE_CAPABILITY_FACTS,
        windows._WINDOW_CAPABILITY_FACTS,
    )


def _corpus_digest() -> str:
    rows: list[str] = []
    for vector in vectors.differential_vectors():
        outcome = pure_boundary.evaluate_capability_document(vector.document)
        matched = (
            outcome.status is vector.expected_status
            and outcome.record_position == vector.expected_record_position
            and outcome.field_position == vector.expected_field_position
            and outcome.canonical_bytes == vector.expected_bytes
        )
        record = outcome.record_position if outcome.record_position is not None else "-"
        field = outcome.field_position if outcome.field_position is not None else "-"
        rows.append(
            f"{vector.vector_id}:{outcome.status.value}:{record}:{field}:{matched}"
        )
    return hashlib.sha256("\n".join(rows).encode()).hexdigest()


def test_schema_identity_reference_and_target_shapes_are_exact() -> None:
    assert tuple(ExtensionCatalogSchemaVersion) == (
        ExtensionCatalogSchemaVersion.EXTENSION_CATALOG_V1,
    )
    assert ExtensionCatalogSchemaVersion.EXTENSION_CATALOG_V1.value == (
        "pietto.extension-catalog.v1"
    )
    assert tuple(field.name for field in fields(ExtensionCatalogIdentity)) == (
        "namespace",
        "name",
    )
    assert tuple(field.name for field in fields(ExtensionCatalogReference)) == (
        "identity",
        "release",
    )
    assert tuple(field.name for field in fields(ExtensionCatalogTarget)) == (
        "database_family",
        "database_release",
        "extension_identity",
        "extension_release",
    )
    assert tuple(field.name for field in fields(CapabilityProfileTarget)) != tuple(
        field.name for field in fields(ExtensionCatalogTarget)
    )

    reference = _reference()
    target = _target()
    assert reference.release != target.database_release
    assert reference.release != target.extension_release
    for field_name, replacement in (
        ("database_family", "postgresql"),
        ("database_release", "17.5 vendor build"),
        ("extension_identity", "other_extension"),
        ("extension_release", "extension release 3"),
    ):
        assert replace(target, **{field_name: replacement}) != target
    for forbidden in (
        "catalog",
        "profile",
        "installed",
        "connection",
        "server",
        "key",
    ):
        assert not hasattr(target, forbidden)


def test_every_text_dimension_is_exact_nonblank_and_unnormalized() -> None:
    composed = "Café"
    decomposed = unicodedata.normalize("NFD", composed)
    identity = ExtensionCatalogIdentity(" Namespace ", composed)
    reference = ExtensionCatalogReference(identity, " release RC ")
    target = ExtensionCatalogTarget(
        " PostgreSQL ",
        " 17 RC ",
        " Example_Extension ",
        " 2 RC ",
    )
    provenance = ExtensionCatalogSourceProvenance(
        " Upstream/Repo ",
        " Revision ",
        " path/É.sql:7 ",
        " Curated exactly ",
    )

    assert identity.namespace == " Namespace "
    assert identity.name == composed
    assert reference.release == " release RC "
    assert tuple(getattr(target, field.name) for field in fields(target)) == (
        " PostgreSQL ",
        " 17 RC ",
        " Example_Extension ",
        " 2 RC ",
    )
    assert tuple(getattr(provenance, field.name) for field in fields(provenance)) == (
        " Upstream/Repo ",
        " Revision ",
        " path/É.sql:7 ",
        " Curated exactly ",
    )
    assert identity != ExtensionCatalogIdentity(" Namespace ", decomposed)
    assert identity != ExtensionCatalogIdentity(" namespace ", composed)
    assert target != replace(target, extension_identity=" example_extension ")
    assert (
        _provenance("https://example.test/upstream/catalog.sql").source_locator
        == "https://example.test/upstream/catalog.sql"
    )

    for absolute_locator in (
        "/home/user/catalog.sql",
        r"C:\Users\user\catalog.sql",
        r"\\server\share\catalog.sql",
        r"\rooted\catalog.sql",
    ):
        with pytest.raises(ValueError, match="host absolute path"):
            _provenance(absolute_locator)

    class TextSubclass(str):
        pass

    for invalid in ("", " \t\n", None, 1, b"text", TextSubclass("text")):
        with pytest.raises(ValueError, match="exact nonblank text"):
            ExtensionCatalogIdentity(cast(Any, invalid), "name")
        with pytest.raises(ValueError, match="exact nonblank text"):
            ExtensionCatalogReference(identity, cast(Any, invalid))
        with pytest.raises(ValueError, match="exact nonblank text"):
            replace(target, database_release=cast(Any, invalid))
        with pytest.raises(ValueError, match="exact nonblank text"):
            replace(provenance, source_locator=cast(Any, invalid))


def test_source_provenance_and_occurrences_preserve_complete_ordered_authority() -> (
    None
):
    owner = _reference()
    provenance = _provenance()
    first = ExtensionCatalogSourceOccurrence(owner, 0, provenance)
    second = ExtensionCatalogSourceOccurrence(owner, 1, provenance)
    metadata = ExtensionCatalogMetadata(
        ExtensionCatalogSchemaVersion.EXTENSION_CATALOG_V1,
        owner,
        _target(),
        cast(Any, (item for item in (first, second))),
    )

    assert tuple(field.name for field in fields(ExtensionCatalogSourceProvenance)) == (
        "source_authority",
        "source_revision",
        "source_locator",
        "curation",
    )
    assert tuple(field.name for field in fields(ExtensionCatalogSourceOccurrence)) == (
        "owner",
        "position",
        "provenance",
    )
    assert metadata.source_occurrences == (first, second)
    assert metadata.source_occurrences[0].provenance is provenance
    assert metadata.source_occurrences[1].provenance is provenance
    assert metadata.source_occurrences[0].owner is owner
    assert metadata.source_occurrences[1].owner is owner

    empty = ExtensionCatalogMetadata(
        ExtensionCatalogSchemaVersion.EXTENSION_CATALOG_V1,
        owner,
        _target(),
        (),
    )
    assert empty.source_occurrences == ()
    with pytest.raises(ValueError, match="non-negative position"):
        ExtensionCatalogSourceOccurrence(owner, True, provenance)
    with pytest.raises(ValueError, match="dense and source ordered"):
        ExtensionCatalogMetadata(
            ExtensionCatalogSchemaVersion.EXTENSION_CATALOG_V1,
            owner,
            _target(),
            (second, first),
        )
    with pytest.raises(ValueError, match="dense and source ordered"):
        ExtensionCatalogMetadata(
            ExtensionCatalogSchemaVersion.EXTENSION_CATALOG_V1,
            owner,
            _target(),
            (ExtensionCatalogSourceOccurrence(owner, 2, provenance),),
        )
    for unordered in ({first, second}, {0: first, 1: second}):
        with pytest.raises(ValueError, match="ordered iterable"):
            ExtensionCatalogMetadata(
                ExtensionCatalogSchemaVersion.EXTENSION_CATALOG_V1,
                owner,
                _target(),
                cast(Any, unordered),
            )

    equal_foreign_owner = _reference()
    assert equal_foreign_owner == owner and equal_foreign_owner is not owner
    reconstructed = ExtensionCatalogMetadata(
        ExtensionCatalogSchemaVersion.EXTENSION_CATALOG_V1,
        owner,
        _target(),
        (
            ExtensionCatalogSourceOccurrence(
                equal_foreign_owner,
                0,
                provenance,
            ),
        ),
    )
    assert reconstructed.source_occurrences[0].owner == owner
    assert reconstructed.source_occurrences[0].owner is equal_foreign_owner


def test_metadata_is_exact_immutable_private_and_not_a_populated_catalog() -> None:
    owner = _reference()
    metadata = ExtensionCatalogMetadata(
        ExtensionCatalogSchemaVersion.EXTENSION_CATALOG_V1,
        owner,
        _target(),
        (),
    )
    assert tuple(field.name for field in fields(ExtensionCatalogMetadata)) == (
        "schema_version",
        "catalog",
        "target",
        "source_occurrences",
    )
    for carrier in (
        ExtensionCatalogIdentity,
        ExtensionCatalogReference,
        ExtensionCatalogTarget,
        ExtensionCatalogSourceProvenance,
        ExtensionCatalogSourceOccurrence,
        ExtensionCatalogMetadata,
    ):
        assert is_dataclass(carrier)
        assert "__dict__" not in carrier.__slots__
    with pytest.raises(FrozenInstanceError):
        metadata.catalog = _reference("other")  # pyright: ignore[reportAttributeAccessIssue]
    with pytest.raises(ValueError, match="exact schema version"):
        ExtensionCatalogMetadata(cast(Any, "v1"), owner, _target(), ())
    with pytest.raises(ValueError, match="exact catalog reference"):
        ExtensionCatalogMetadata(
            ExtensionCatalogSchemaVersion.EXTENSION_CATALOG_V1,
            cast(Any, object()),
            _target(),
            (),
        )
    with pytest.raises(ValueError, match="exact target"):
        ExtensionCatalogMetadata(
            ExtensionCatalogSchemaVersion.EXTENSION_CATALOG_V1,
            owner,
            cast(Any, CapabilityProfileTarget),
            (),
        )
    for forbidden in (
        "entries",
        "complete",
        "canonical_bytes",
        "content_digest",
    ):
        assert not hasattr(metadata, forbidden)


def test_module_remains_stdlib_only_data_only_and_non_executable() -> None:
    source = inspect.getsource(extension_catalog)
    tree = ast.parse(source)
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert imported_modules == {
        "__future__",
        "collections.abc",
        "dataclasses",
        "enum",
        "pathlib",
        "pietto.semantic.generic_compatibility",
    }
    assert "from pathlib import PurePosixPath, PureWindowsPath" in source
    assert extension_catalog.__all__ == ()
    for forbidden in (
        "import os",
        "subprocess",
        "requests",
        "urllib",
        "socket",
        "open(",
        "getcwd",
        "environ",
        "datetime",
        "timestamp",
        "lookup_capability",
        "domain_complete",
        "provider",
        "installation",
        "connection",
        "create extension",
        "pgvector",
        "pg_trgm",
        "postgis",
        "timescaledb",
        ".open(",
        ".read_text(",
        ".read_bytes(",
        ".resolve(",
        ".stat(",
        ".lstat(",
    ):
        assert forbidden not in source.lower()
    for forbidden in ("winner", "precedence", "override", "dedup"):
        assert forbidden not in source.lower()
    assert "object.__setattr__" in source


def test_capability_provider_profile_inspection_and_corpus_are_unchanged() -> None:
    facts = tuple(fact for family in _provider_families() for fact in family)
    assert tuple(field.name for field in fields(CapabilityKey)) == (
        "domain",
        "subject",
        "operation",
        "operands",
        "context",
        "dialect",
        "extension",
    )
    assert "release" not in {field.name for field in fields(CapabilityKey)}
    assert not any(
        fact.key.domain is CapabilityDomain.EXTENSION_SIGNATURE for fact in facts
    )
    key = CapabilityKey(
        CapabilityDomain.EXTENSION_SIGNATURE,
        subject="synthetic",
        operation="signature",
        dialect="postgresql",
        extension="synthetic_extension",
    )
    provider = providers.canonical_capability_provider_inputs(key)
    assert provider.facts == ()
    assert provider.domain_complete is False
    assert provider.unknown_reason is None
    assert lookup_capability(
        key,
        provider.facts,
        domain_complete=provider.domain_complete,
        unknown_reason=provider.unknown_reason,
    ) == Unknown(CapabilityReasonCode.NOT_EVIDENCED)
    assert lookup_capability(key, (), domain_complete=False) == Unknown(
        CapabilityReasonCode.NOT_EVIDENCED
    )
    assert "extension_catalog" not in inspect.getsource(providers)
    assert tuple(
        inspect.signature(checking.check_package_capability_requirements).parameters
    ) == (
        "package",
        "binding",
        "composition",
        "availability",
        "extension_signature_provider_context",
    )
    assert tuple(
        inspect.signature(matrix.build_package_capability_checking_matrix).parameters
    ) == ("package", "binding", "contexts")
    assert CapabilityInspectionFormat.CAPABILITY_INSPECTION_V1.value == (
        "pietto.capability-inspection.v1"
    )
    assert "extension_catalog" not in inspect.getsource(inspection)

    corpus = vectors.differential_vectors()
    accepted = tuple(
        vector
        for vector in corpus
        if vector.expected_status is pure_boundary.CapabilityPureStatus.OK
    )
    assert (len(corpus), len(accepted), len(corpus) - len(accepted)) == (
        125,
        16,
        109,
    )
    assert _corpus_digest() == EXPECTED_CORPUS_DIGEST


def test_no_public_export_package_asset_concrete_fact_or_version_change() -> None:
    symbols = (
        "ExtensionCatalogSchemaVersion",
        "ExtensionCatalogIdentity",
        "ExtensionCatalogReference",
        "ExtensionCatalogTarget",
        "ExtensionCatalogSourceProvenance",
        "ExtensionCatalogSourceOccurrence",
        "ExtensionCatalogMetadata",
        "ExtensionCatalogTypeReferenceKind",
        "ExtensionCatalogTypeReference",
        "PostgreSQLCallableIdentity",
        "PostgreSQLOperatorArity",
        "PostgreSQLOperatorIdentity",
        "PostgreSQLCastIdentity",
        "ExtensionCatalogDeclarationTypeUse",
        "ExtensionCatalogEntryEvidence",
        "ExtensionNativeTypeCatalogEntry",
        "ExtensionScalarFunctionCatalogEntry",
        "ExtensionAggregateCatalogEntry",
        "ExtensionOperatorCatalogEntry",
        "ExtensionCastCatalogEntry",
    )
    for module in (pietto, semantic_package, project_package):
        assert all(not hasattr(module, symbol) for symbol in symbols)
    for path in (
        REPO_ROOT / "src/pietto/__init__.py",
        REPO_ROOT / "src/pietto/semantic/__init__.py",
        REPO_ROOT / "src/pietto/_project/__init__.py",
    ):
        assert "extension_catalog" not in _read(path)
    assert "extension_catalog" not in inspect.getsource(package_manifest)
    source = inspect.getsource(extension_catalog).lower()
    assert all(
        name not in source for name in ("pgvector", "pg_trgm", "postgis", "timescaledb")
    )
    assert 'version = "0.1.0"' in _read(REPO_ROOT / "pyproject.toml")


def test_spec_lifecycle_route_and_installed_package_smoke_are_exact() -> None:
    spec = _read(SPEC)
    assert "\npietto.extension-catalog.v1\n" in _section(spec, "Schema Marker")
    assert tuple(
        line
        for line in _section(spec, "Exact Target").splitlines()
        if line[:3] in {"1. ", "2. ", "3. ", "4. "}
    ) == (
        "1. `database_family`",
        "2. `database_release`",
        "3. `extension_identity`",
        "4. `extension_release`",
    )
    assert _table_rows(_section(spec, "Retained Slice Ownership"))[1:] == (
        EXPECTED_RETAINED_ROUTE
    )
    non_scope = " ".join(_section(spec, "Exact Non-scope").split())
    for term in (
        "type references",
        "entry families",
        "catalog construction",
        "scoped completeness",
        "canonical bytes",
        "content digest",
        "provider integration",
        "concrete extension entries",
        "public output",
        "package assets",
        "installation",
        "SQL lowering",
    ):
        assert term in non_scope

    roadmap = _read(ROADMAP)
    assert "Phase 57 is active, Slices 1–7 are completed, and Slice 8 is current" in (
        roadmap
    )
    status_rows = _table_rows(_read(STATUS))[1:]
    assert status_rows == (
        ("Package and CLI", "`0.1.0`"),
        ("Phase 55", "`COMPLETED`"),
        ("Phase 56", "`COMPLETED`"),
        ("Phase 57", "`ACTIVE`"),
        ("Slices 1–7", "`COMPLETED`"),
        ("Slice 8", "`CURRENT`"),
        ("Next", "`PHASE57_SLICE8_END_TO_END`"),
    )
    status = _read(STATUS)
    assert "Live Git and natural exact-head CI own\nSlice 8 completion" in status
    assert "does\nnot authorize Slice 9" in status

    package_smoke = _read(PACKAGE_SMOKE)
    assert 'f"{prefix}/semantic/extension_catalog.py"' in package_smoke
    assert '"installed private extension catalog import"' in package_smoke
    assert '"import pietto.semantic.extension_catalog"' in package_smoke
