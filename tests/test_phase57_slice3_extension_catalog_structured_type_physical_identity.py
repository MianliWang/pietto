from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
import hashlib
import inspect
from pathlib import Path
from typing import Any, cast
import unicodedata

import pytest

import _pietto_capability_differential_vectors as vectors
import pietto
import pietto._project as project_package
import pietto._project.capability_inspection as inspection
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
from pietto.semantic.extension_catalog import (
    ExtensionCatalogIdentity,
    ExtensionCatalogMetadata,
    ExtensionCatalogReference,
    ExtensionCatalogSchemaVersion,
    ExtensionCatalogSourceOccurrence,
    ExtensionCatalogSourceProvenance,
    ExtensionCatalogTarget,
    ExtensionCatalogTypeReference,
    ExtensionCatalogTypeReferenceKind,
    PostgreSQLCallableIdentity,
    PostgreSQLCastIdentity,
    PostgreSQLOperatorArity,
    PostgreSQLOperatorIdentity,
)
from pietto.semantic.generic_compatibility import LogicalTypeIdentity
from pietto.semantic.model import TypeKind


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase57-extension-catalog-structured-type-physical-identity-v1.md"
)
ROADMAP = REPO_ROOT / "docs/roadmap.md"
STATUS = REPO_ROOT / "docs/status.md"
PACKAGE_SMOKE = REPO_ROOT / "scripts/package_smoke.py"
EXPECTED_CORPUS_DIGEST = (
    "8453c3babda888b105f37f667f5fadf3a12aa68ca9a561bda98e5f6b6604a69e"
)
EXPECTED_RETAINED_ROUTE = (
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


def _logical(name: str = "Text") -> ExtensionCatalogTypeReference:
    return ExtensionCatalogTypeReference(
        ExtensionCatalogTypeReferenceKind.PIETTO_LOGICAL,
        logical_type=LogicalTypeIdentity(name=name, kind=TypeKind.BUILTIN),
    )


def _builtin(name: str = "text") -> ExtensionCatalogTypeReference:
    return ExtensionCatalogTypeReference(
        ExtensionCatalogTypeReferenceKind.POSTGRES_BUILTIN,
        physical_name=name,
    )


def _native(
    name: str = "native_type",
    extension_identity: str = "example_extension",
) -> ExtensionCatalogTypeReference:
    return ExtensionCatalogTypeReference(
        ExtensionCatalogTypeReferenceKind.EXTENSION_NATIVE,
        physical_name=name,
        extension_identity=extension_identity,
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


def test_three_type_domains_are_exact_distinct_and_reuse_logical_authority() -> None:
    assert tuple(ExtensionCatalogTypeReferenceKind) == (
        ExtensionCatalogTypeReferenceKind.PIETTO_LOGICAL,
        ExtensionCatalogTypeReferenceKind.POSTGRES_BUILTIN,
        ExtensionCatalogTypeReferenceKind.EXTENSION_NATIVE,
    )
    assert tuple(field.name for field in fields(ExtensionCatalogTypeReference)) == (
        "kind",
        "logical_type",
        "physical_name",
        "extension_identity",
    )

    logical_authority = LogicalTypeIdentity(name="Text", kind=TypeKind.BUILTIN)
    logical = ExtensionCatalogTypeReference(
        ExtensionCatalogTypeReferenceKind.PIETTO_LOGICAL,
        logical_type=logical_authority,
    )
    builtin = _builtin("Text")
    native = _native("Text")
    assert logical.logical_type is logical_authority
    assert logical != builtin != native
    assert logical != native
    with pytest.raises(ValueError, match="exact authority"):
        ExtensionCatalogTypeReference(
            ExtensionCatalogTypeReferenceKind.PIETTO_LOGICAL,
        )
    with pytest.raises(ValueError, match="forbids physical identity"):
        ExtensionCatalogTypeReference(
            ExtensionCatalogTypeReferenceKind.PIETTO_LOGICAL,
            logical_type=logical_authority,
            physical_name="Text",
        )
    with pytest.raises(ValueError, match="forbids logical authority"):
        ExtensionCatalogTypeReference(
            ExtensionCatalogTypeReferenceKind.POSTGRES_BUILTIN,
            logical_type=logical_authority,
            physical_name="text",
        )
    with pytest.raises(ValueError, match="forbids extension owner"):
        ExtensionCatalogTypeReference(
            ExtensionCatalogTypeReferenceKind.POSTGRES_BUILTIN,
            physical_name="text",
            extension_identity="extension",
        )
    with pytest.raises(ValueError, match="extension identity"):
        ExtensionCatalogTypeReference(
            ExtensionCatalogTypeReferenceKind.EXTENSION_NATIVE,
            physical_name="native_type",
        )
    with pytest.raises(ValueError, match="exact kind"):
        ExtensionCatalogTypeReference(cast(Any, "postgres_builtin"))


def test_physical_type_text_and_extension_ownership_are_exact() -> None:
    composed = "téxt"
    decomposed = unicodedata.normalize("NFD", composed)
    assert _builtin(" int4 ").physical_name == " int4 "
    assert _builtin("integer") != _builtin("int4")
    assert _builtin("character varying") != _builtin("varchar")
    assert _builtin("Text") != _builtin("text")
    assert _builtin(composed) != _builtin(decomposed)
    assert _native("vector", "extension-A") != _native("vector", "extension-B")

    target = ExtensionCatalogTarget(
        "PostgreSQL",
        "17",
        "extension-A",
        "release-1",
    )
    native = _native("vector", target.extension_identity)
    assert native.extension_identity == target.extension_identity
    assert native.physical_name == "vector"

    class TextSubclass(str):
        pass

    for invalid in ("", " \t\n", None, 1, b"text", TextSubclass("text")):
        with pytest.raises(ValueError, match="exact nonblank text"):
            _builtin(cast(Any, invalid))
        with pytest.raises(ValueError, match="exact nonblank text"):
            _native("native_type", cast(Any, invalid))


def test_callable_identity_is_name_plus_ordered_physical_inputs_only() -> None:
    text = _builtin("text")
    native = _native("vector")
    identity = PostgreSQLCallableIdentity(
        " distance ",
        cast(Any, (item for item in (native, text))),
    )
    assert tuple(field.name for field in fields(PostgreSQLCallableIdentity)) == (
        "sql_name",
        "input_types",
    )
    assert identity.sql_name == " distance "
    assert identity.input_types == (native, text)
    assert identity != PostgreSQLCallableIdentity(" distance ", (text, native))
    assert identity == PostgreSQLCallableIdentity(" distance ", (native, text))
    assert PostgreSQLCallableIdentity("zero", ()).input_types == ()
    for forbidden in (
        "return_type",
        "out_arguments",
        "defaults",
        "variadic",
        "schema",
        "oid",
    ):
        assert not hasattr(identity, forbidden)
    with pytest.raises(ValueError, match="PostgreSQL-side"):
        PostgreSQLCallableIdentity("logical", (_logical(),))
    with pytest.raises(ValueError, match="ordered iterable"):
        PostgreSQLCallableIdentity("unordered", cast(Any, {text, native}))


def test_operator_identity_retains_arity_order_and_physical_overload_shape() -> None:
    text = _builtin("text")
    native = _native("vector")
    unary = PostgreSQLOperatorIdentity(
        " - ",
        PostgreSQLOperatorArity.UNARY,
        (native,),
    )
    binary = PostgreSQLOperatorIdentity(
        " <-> ",
        PostgreSQLOperatorArity.BINARY,
        (native, text),
    )
    assert tuple(PostgreSQLOperatorArity) == (
        PostgreSQLOperatorArity.UNARY,
        PostgreSQLOperatorArity.BINARY,
    )
    assert tuple(field.name for field in fields(PostgreSQLOperatorIdentity)) == (
        "operator_name",
        "arity",
        "operand_types",
    )
    assert unary.operand_types == (native,)
    assert binary.operand_types == (native, text)
    assert binary != PostgreSQLOperatorIdentity(
        " <-> ",
        PostgreSQLOperatorArity.BINARY,
        (text, native),
    )
    for forbidden in ("result_type", "commutator", "negator", "operator_class"):
        assert not hasattr(binary, forbidden)
    with pytest.raises(ValueError, match="arity must match"):
        PostgreSQLOperatorIdentity(
            "+",
            PostgreSQLOperatorArity.UNARY,
            (text, native),
        )
    with pytest.raises(ValueError, match="PostgreSQL-side"):
        PostgreSQLOperatorIdentity(
            "+",
            PostgreSQLOperatorArity.UNARY,
            (_logical(),),
        )


def test_cast_identity_is_directional_and_postgresql_side_only() -> None:
    source = _builtin("text")
    target = _native("vector")
    forward = PostgreSQLCastIdentity(source, target)
    reverse = PostgreSQLCastIdentity(target, source)
    assert tuple(field.name for field in fields(PostgreSQLCastIdentity)) == (
        "source_type",
        "target_type",
    )
    assert forward.source_type is source
    assert forward.target_type is target
    assert forward != reverse
    for forbidden in (
        "implicit",
        "assignment",
        "binary_coercible",
        "function",
        "reverse",
    ):
        assert not hasattr(forward, forbidden)
    with pytest.raises(ValueError, match="PostgreSQL-side"):
        PostgreSQLCastIdentity(_logical(), target)
    with pytest.raises(ValueError, match="PostgreSQL-side"):
        PostgreSQLCastIdentity(source, _logical())


def test_new_identity_carriers_are_private_immutable_and_atomic_only() -> None:
    carriers = (
        ExtensionCatalogTypeReference,
        PostgreSQLCallableIdentity,
        PostgreSQLOperatorIdentity,
        PostgreSQLCastIdentity,
    )
    for carrier in carriers:
        assert is_dataclass(carrier)
        assert getattr(carrier, "__dataclass_params__").frozen
        assert "__dict__" not in carrier.__slots__
    reference = _builtin()
    with pytest.raises(FrozenInstanceError):
        reference.physical_name = "other"  # pyright: ignore[reportAttributeAccessIssue]
    for forbidden in (
        "array",
        "modifier",
        "precision",
        "scale",
        "collation",
        "compound",
        "composite",
    ):
        assert not hasattr(reference, forbidden)

    symbols = (
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


def test_module_has_no_provider_runtime_or_lowering() -> None:
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
        "pietto.semantic.extension_catalog_pure_boundary",
        "pietto.semantic.generic_compatibility",
    }
    for forbidden in (
        "server_oid",
        "database_oid",
        "regproc",
        "regoperator",
        "search_path",
        "current_schema",
        "connection_identity",
        "installation_schema",
        "runtime lookup",
        "create extension",
        "subprocess",
        "requests",
        "socket",
        "getcwd",
        "environ",
        "overloadselection",
        "lowering_template",
        "sql_snippet",
        "emitter",
        "renderer",
        "pgvector",
        "pg_trgm",
        "postgis",
        "timescaledb",
    ):
        assert forbidden not in source.lower()
    for path in (
        REPO_ROOT / "src/pietto/__init__.py",
        REPO_ROOT / "src/pietto/semantic/__init__.py",
        REPO_ROOT / "src/pietto/_project/__init__.py",
    ):
        assert "extension_catalog" not in _read(path)
    assert "extension_catalog" not in inspect.getsource(providers)
    assert "extension_catalog" not in inspect.getsource(inspection)
    assert "extension_catalog" not in inspect.getsource(package_manifest)


def test_slice2_and_phase56_predecessor_contracts_remain_exact() -> None:
    assert tuple(field.name for field in fields(ExtensionCatalogMetadata)) == (
        "schema_version",
        "catalog",
        "target",
        "source_occurrences",
    )
    assert ExtensionCatalogSchemaVersion.EXTENSION_CATALOG_V1.value == (
        "pietto.extension-catalog.v1"
    )
    owner = ExtensionCatalogReference(
        ExtensionCatalogIdentity("namespace", "name"),
        "release",
    )
    provenance = ExtensionCatalogSourceProvenance(
        "authority",
        "revision",
        "path/source.sql:1",
        "curated",
    )
    occurrence = ExtensionCatalogSourceOccurrence(owner, 0, provenance)
    metadata = ExtensionCatalogMetadata(
        ExtensionCatalogSchemaVersion.EXTENSION_CATALOG_V1,
        owner,
        ExtensionCatalogTarget("PostgreSQL", "17", "extension", "1"),
        (occurrence,),
    )
    assert metadata.source_occurrences == (occurrence,)

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
    assert not any(
        fact.key.domain is CapabilityDomain.EXTENSION_SIGNATURE for fact in facts
    )
    key = CapabilityKey(
        CapabilityDomain.EXTENSION_SIGNATURE,
        subject="synthetic",
        operation="signature",
    )
    provider = providers.canonical_capability_provider_inputs(key)
    assert provider.facts == ()
    assert provider.domain_complete is False
    assert lookup_capability(
        key,
        provider.facts,
        domain_complete=provider.domain_complete,
        unknown_reason=provider.unknown_reason,
    ) == Unknown(CapabilityReasonCode.NOT_EVIDENCED)
    assert CapabilityInspectionFormat.CAPABILITY_INSPECTION_V1.value == (
        "pietto.capability-inspection.v1"
    )

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
    assert 'version = "0.1.0"' in _read(REPO_ROOT / "pyproject.toml")


def test_spec_lifecycle_route_deferred_shapes_and_package_smoke_are_exact() -> None:
    spec = _read(SPEC)
    domains = _section(spec, "Structured Type-reference Domains")
    assert all(
        f"{position}. `{name}`" in domains
        for position, name in enumerate(
            ("PIETTO_LOGICAL", "POSTGRES_BUILTIN", "EXTENSION_NATIVE"),
            start=1,
        )
    )
    assert "`LogicalTypeIdentity`" in domains
    assert _table_rows(_section(spec, "Retained Slice Ownership"))[1:] == (
        EXPECTED_RETAINED_ROUTE
    )
    deferred = " ".join(_section(spec, "Evidence-driven Deferrals").split())
    for term in ("arrays", "modifiers", "compound/composite"):
        assert term in deferred
    boundaries = " ".join(_section(spec, "Exact Non-scope").split())
    for term in (
        "entry families",
        "return/result declarations",
        "matchability",
        "coercion",
        "catalog construction",
        "provider routing",
        "installation",
        "lowering",
        "public output",
    ):
        assert term in boundaries

    roadmap = _read(ROADMAP)
    assert (
        "Phase 58 is active, Slice 1 is completed, Slice 2 is current, and Slice 3 is next / unstarted"
        in (roadmap)
    )
    status_rows = _table_rows(_read(STATUS))[1:]
    assert status_rows == (
        ("Package and CLI", "`0.1.0`"),
        ("Phase 55", "`COMPLETED`"),
        ("Phase 56", "`COMPLETED`"),
        ("Phase 57", "`COMPLETED`"),
        ("Phase 58", "`ACTIVE`"),
        ("Slice 1", "`COMPLETED`"),
        ("Slice 2", "`CURRENT`"),
        ("Slice 3", "`NEXT / UNSTARTED`"),
        ("Next", "`PHASE58_SLICE3_END_TO_END`"),
    )
    status = _read(STATUS)
    normalized_status = " ".join(status.split())
    assert "Live Git and natural exact-head CI own Phase 58 Slice 2 completion" in (
        normalized_status
    )
    assert "does not authorize Slice 3" in normalized_status
    package_smoke = _read(PACKAGE_SMOKE)
    assert 'f"{prefix}/semantic/extension_catalog.py"' in package_smoke
    assert '"import pietto.semantic.extension_catalog"' in package_smoke
