from __future__ import annotations

import ast
from collections import Counter
from dataclasses import fields, replace
import hashlib
import inspect
import os
from pathlib import Path
import shutil
import sys

import pytest

import _pietto_extension_catalog_differential_vectors as vectors
import _pietto_project_extension_differential as differential
import pietto
import pietto._project as project_package
import pietto._project.extension_catalog_inspection as inspection_runtime
import pietto._project.extension_catalog_inspection_pure_boundary as inspection_pure
import pietto._project.package_pure_boundary as package_pure
import pietto.semantic as semantic_package
import pietto.semantic.extension_catalog as catalog_runtime
import pietto.semantic.extension_catalog_pure_boundary as catalog_pure
import _pietto_project_extension_inspection as slice11
from pietto._project.capability_inspection import CapabilityInspectionFormat
from pietto._project.extension_catalog_inspection import (
    _extension_catalog_inspection_pure_document,
)
from pietto._project.extension_catalog_inspection_pure_boundary import (
    ExtensionCatalogInspectionPureOutcome,
    ExtensionCatalogInspectionPureStatus,
    ExtensionCatalogInspectionPureValue,
    evaluate_extension_catalog_inspection_document,
)
from pietto.semantic.extension_catalog import _extension_catalog_pure_document
from pietto.semantic.extension_catalog_pg_trgm import (
    PG_TRGM_V16_POSTGRESQL18_CATALOG,
)
from pietto.semantic.extension_catalog_pgvector import (
    PGVECTOR_V086_POSTGRESQL18_CATALOG,
)
from pietto.semantic.extension_catalog_pure_boundary import (
    ExtensionCatalogPureDocument,
    ExtensionCatalogPureOutcome,
    ExtensionCatalogPureStatus,
    ExtensionCatalogPureValue,
    evaluate_extension_catalog_document,
    extension_catalog_pure_text,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
VECTOR_REL = "tests/_pietto_extension_catalog_differential_vectors.py"
CATALOG_SOURCE_REL = "src/pietto/semantic/extension_catalog_pure_boundary.py"
INSPECTION_SOURCE_REL = (
    "src/pietto/_project/extension_catalog_inspection_pure_boundary.py"
)
SPEC = (
    REPO_ROOT
    / "docs/spec/phase57-extension-catalog-pure-boundary-differential-e2e-v1.md"
)
PACKAGE_SMOKE = REPO_ROOT / "scripts/package_smoke.py"
EXPECTED_CORPUS_DIGEST = (
    "2cad48b2f2a1e8d55ae4b685408ffcf909fd01abe233068a5c5643d486976244"
)
EXPECTED_CAPABILITY_CORPUS_DIGEST = (
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
EXPECTED_WITNESS = (
    f"{EXPECTED_CORPUS_DIGEST}|"
    f"{EXPECTED_PGVECTOR[0]}:{EXPECTED_PGVECTOR[1]}|"
    f"{EXPECTED_PG_TRGM[0]}:{EXPECTED_PG_TRGM[1]}|"
    f"{EXPECTED_INSPECTION[0]}:{EXPECTED_INSPECTION[1]}"
)


@pytest.fixture(scope="module")
def witness_matrix(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    return differential._build_witness_matrix(tmp_path_factory)


def test_pure_boundaries_are_private_stdlib_only_explicit_and_total() -> None:
    assert catalog_pure.__all__ == inspection_pure.__all__ == ()
    assert catalog_pure.EXTENSION_CATALOG_PURE_FORMAT_MARKER == (
        "pietto.extension-catalog.v1"
    )
    assert inspection_pure.EXTENSION_CATALOG_INSPECTION_PURE_FORMAT_MARKER == (
        "pietto.extension-catalog-inspection.v1"
    )
    assert tuple(catalog_pure.ExtensionCatalogPureStatus) == tuple(
        catalog_pure.ExtensionCatalogPureStatus
    )
    assert tuple(inspection_pure.ExtensionCatalogInspectionPureStatus) == tuple(
        inspection_pure.ExtensionCatalogInspectionPureStatus
    )
    for relative, allowed in (
        (
            CATALOG_SOURCE_REL,
            {"__future__", "collections", "dataclasses", "enum", "types", "typing"},
        ),
        (
            INSPECTION_SOURCE_REL,
            {"__future__", "dataclasses", "enum", "types", "typing"},
        ),
    ):
        source = (REPO_ROOT / relative).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=relative)
        imported_roots = {
            node.module.split(".")[0]
            for node in tree.body
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }
        assert imported_roots <= allowed
        for forbidden in (
            "pathlib",
            "import os",
            "subprocess",
            "socket",
            "requests",
            "urllib",
            "open(",
            "getcwd",
            "environ",
            "random",
            "threading",
            "time.",
            "repr(",
            "id(",
            "hash(",
            "pickle",
        ):
            assert forbidden not in source
    catalog_source = (REPO_ROOT / CATALOG_SOURCE_REL).read_text(encoding="utf-8")
    inspection_source = (REPO_ROOT / INSPECTION_SOURCE_REL).read_text(encoding="utf-8")
    assert "pietto.semantic.extension_catalog" not in catalog_source
    assert "pietto._project" not in catalog_source
    for forbidden in (
        "import pietto._project.extension_catalog_inspection",
        "import pietto._project.extension_signature_provider",
        "import pietto._project.extension_catalog_availability",
        "import pietto.semantic.extension_catalog",
    ):
        assert forbidden not in inspection_source
    with pytest.raises(TypeError):
        evaluate_extension_catalog_document(object())  # pyright: ignore[reportArgumentType]
    with pytest.raises(TypeError):
        evaluate_extension_catalog_inspection_document(
            object()  # pyright: ignore[reportArgumentType]
        )


def test_portable_carriers_and_outcome_invariants_are_exact() -> None:
    assert tuple(field.name for field in fields(ExtensionCatalogPureValue)) == (
        "tag",
        "text",
        "integer",
        "boolean",
        "enum_type",
        "enum_value",
        "items",
        "record_kind",
        "fields",
    )
    assert tuple(field.name for field in fields(ExtensionCatalogPureDocument)) == (
        "root",
    )
    assert tuple(field.name for field in fields(ExtensionCatalogPureOutcome)) == (
        "status",
        "canonical_bytes",
        "item_position",
        "field_position",
    )
    assert tuple(
        field.name for field in fields(ExtensionCatalogInspectionPureValue)
    ) == (
        "tag",
        "text",
        "integer",
        "boolean",
        "enum_type",
        "enum_value",
        "items",
    )
    assert tuple(
        field.name for field in fields(ExtensionCatalogInspectionPureOutcome)
    ) == (
        "status",
        "canonical_bytes",
        "item_position",
        "field_position",
    )
    with pytest.raises(ValueError):
        ExtensionCatalogPureOutcome(status=ExtensionCatalogPureStatus.OK)
    with pytest.raises(ValueError):
        ExtensionCatalogInspectionPureOutcome(
            status=ExtensionCatalogInspectionPureStatus.MISSING_ROOT,
            canonical_bytes=b"forged",
        )


def test_catalog_and_inspection_have_one_pure_canonical_path() -> None:
    catalog_construction = inspect.getsource(
        catalog_runtime._construct_extension_catalog
    )
    catalog_projection = inspect.getsource(
        catalog_runtime._extension_catalog_pure_document
    )
    catalog_fragment = inspect.getsource(catalog_runtime._encode_catalog_value)
    catalog_source = inspect.getsource(catalog_runtime)
    assert "evaluate_extension_catalog_document" in catalog_construction
    assert "_extension_catalog_pure_document" in catalog_construction
    assert "ExtensionCatalogPureDocument" in catalog_projection
    assert "encode_extension_catalog_pure_value" in catalog_fragment
    assert "def _frame" not in catalog_source

    inspection_serializer = inspect.getsource(
        inspection_runtime._serialize_extension_catalog_inspection
    )
    inspection_projection = inspect.getsource(
        inspection_runtime._extension_catalog_inspection_pure_document
    )
    inspection_source = inspect.getsource(inspection_runtime)
    assert "evaluate_extension_catalog_inspection_document" in inspection_serializer
    assert "_extension_catalog_inspection_pure_document" in inspection_serializer
    assert "ExtensionCatalogInspectionPureDocument" in inspection_projection
    assert "def _encode_inspection_value" not in inspection_source
    assert "def _frame" not in inspection_source


def test_frozen_runtime_artifacts_reproduce_exactly_through_pure_evaluators() -> None:
    for catalog, expected in (
        (PGVECTOR_V086_POSTGRESQL18_CATALOG, EXPECTED_PGVECTOR),
        (PG_TRGM_V16_POSTGRESQL18_CATALOG, EXPECTED_PG_TRGM),
    ):
        outcome = evaluate_extension_catalog_document(
            _extension_catalog_pure_document(
                catalog.metadata,
                catalog.entries,
                catalog.exact_entry_groups,
                catalog.completeness_claims,
                catalog.completeness_groups,
            )
        )
        assert outcome.status is ExtensionCatalogPureStatus.OK
        assert outcome.canonical_bytes == catalog.canonical_bytes
        assert (
            len(catalog.canonical_bytes),
            hashlib.sha256(catalog.canonical_bytes).hexdigest(),
        ) == expected
        assert catalog.content_sha256 == expected[1]
    fact_set = slice11._inspection(slice11._production_context())
    outcome = evaluate_extension_catalog_inspection_document(
        _extension_catalog_inspection_pure_document(fact_set.inspection)
    )
    assert outcome.status is ExtensionCatalogInspectionPureStatus.OK
    assert outcome.canonical_bytes == fact_set.canonical_bytes
    assert (
        len(fact_set.canonical_bytes),
        hashlib.sha256(fact_set.canonical_bytes).hexdigest(),
    ) == EXPECTED_INSPECTION


def test_differential_corpus_counts_histogram_oracles_and_digest_are_frozen() -> None:
    corpus = vectors.differential_vectors()
    rows = differential._run_corpus()
    assert len(corpus) == len(rows) == 47
    assert all(matched for *_coordinates, matched in rows)
    accepted = tuple(
        vector for vector in corpus if vector.expected_status.value == "ok"
    )
    rejected = tuple(
        vector for vector in corpus if vector.expected_status.value != "ok"
    )
    assert (len(accepted), len(rejected)) == (14, 33)
    assert Counter(vector.boundary for vector in corpus) == {
        vectors.ExtensionCatalogDifferentialBoundary.CATALOG: 19,
        vectors.ExtensionCatalogDifferentialBoundary.INSPECTION: 28,
    }
    assert Counter(vector.expected_status.value for vector in corpus) == {
        "ok": 14,
        "missing_root": 2,
        "unknown_format_marker": 2,
        "unknown_value_tag": 2,
        "value_shape_mismatch": 2,
        "integer_out_of_range": 2,
        "unknown_enumeration": 2,
        "section_order_violation": 2,
        "ordinal_sequence_violation": 2,
        "child_count_mismatch": 2,
        "inconsistent_family_identity": 2,
        "inconsistent_entry_group": 2,
        "inconsistent_completeness_link": 2,
        "trailing_item": 2,
        "record_schema_mismatch": 1,
        "missing_required_section": 1,
        "tuple_schema_mismatch": 1,
        "invalid_sha256": 1,
        "dangling_positional_link": 1,
        "inconsistent_selection_link": 1,
        "inconsistent_provider_result": 1,
    }
    assert differential._corpus_digest() == EXPECTED_CORPUS_DIGEST
    assert {
        vector.expected_status
        for vector in corpus
        if vector.boundary.value == "catalog"
    } == set(ExtensionCatalogPureStatus)
    assert {
        vector.expected_status
        for vector in corpus
        if vector.boundary.value == "inspection"
    } == set(ExtensionCatalogInspectionPureStatus)


def test_vector_expected_results_are_static_and_runtime_independent() -> None:
    source = (REPO_ROOT / VECTOR_REL).read_text(encoding="utf-8")
    for forbidden in (
        "evaluate_extension_catalog_document",
        "evaluate_extension_catalog_inspection_document",
        "extension_catalog_pgvector",
        "extension_catalog_pg_trgm",
        "test_phase57",
    ):
        assert forbidden not in source
    tree = ast.parse(source, filename=VECTOR_REL)
    imports = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert imports <= {
        "__future__",
        "dataclasses",
        "enum",
        "pietto.semantic.extension_catalog_pure_boundary",
        "pietto._project.extension_catalog_inspection_pure_boundary",
    }
    witness_assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "_EXPECTED_ACCEPTED_WITNESSES"
    )
    assert isinstance(witness_assignment.value, ast.Dict)
    assert len(witness_assignment.value.keys) == 14
    assert all(isinstance(key, ast.Constant) for key in witness_assignment.value.keys)
    assert all(
        isinstance(value, ast.Tuple) for value in witness_assignment.value.values
    )


def test_rejections_are_bounded_and_carry_no_bytes() -> None:
    for vector in vectors.differential_vectors():
        outcome = differential._evaluate(vector)
        if outcome.status.value == "ok":
            continue
        assert outcome.canonical_bytes is None
        rendered = (
            f"{outcome.status.value}|{outcome.item_position}|{outcome.field_position}"
        )
        assert "pietto." not in rendered
        assert "/" not in rendered


def test_pure_evaluators_use_no_ambient_state(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*arguments: object, **keywords: object) -> object:
        del arguments, keywords
        raise AssertionError("pure evaluation used ambient state")

    monkeypatch.setattr("builtins.open", refuse)
    monkeypatch.setattr(Path, "open", refuse)
    monkeypatch.setattr(Path, "read_text", refuse)
    monkeypatch.setattr(Path, "read_bytes", refuse)
    monkeypatch.setattr(os, "getcwd", refuse)
    monkeypatch.setattr(os, "listdir", refuse)
    monkeypatch.setattr(os, "urandom", refuse)
    assert all(matched for *_coordinates, matched in differential._run_corpus())


def test_nested_catalog_schema_errors_are_bounded_not_exceptions() -> None:
    document = vectors._accepted_catalog_documents()[0][2]
    assert document.root is not None
    metadata = document.root.items[1]
    malformed_metadata = replace(
        metadata,
        fields=tuple(
            replace(field, value=extension_catalog_pure_text("not-a-reference"))
            if field.key == "catalog"
            else field
            for field in metadata.fields
        ),
    )
    malformed = replace(
        document,
        root=replace(
            document.root,
            items=(
                document.root.items[0],
                malformed_metadata,
                *document.root.items[2:],
            ),
        ),
    )
    outcome = evaluate_extension_catalog_document(malformed)
    assert outcome.status is ExtensionCatalogPureStatus.RECORD_SCHEMA_MISMATCH
    assert outcome.canonical_bytes is None


def test_semantic_operand_equal_to_node_label_has_no_hidden_grammar() -> None:
    key = slice11.CapabilityKey(
        slice11.CapabilityDomain.EXTENSION_SIGNATURE,
        subject="node-label operand",
        operation="exact signature",
        operands=("reference",),
        context="portable",
        dialect="postgresql",
        extension="pg_trgm",
    )
    requirements = slice11._requirements(key, name="node-label-operand")
    catalog = slice11.PG_TRGM_V16_POSTGRESQL18_CATALOG
    availability = slice11.slice6._availability(
        (slice11.ExtensionCatalogAvailabilityOwner.COMPILER, catalog, None),
    )
    selection = slice11.select_extension_catalog(
        availability,
        catalog.metadata.target,
    )
    context = slice11._context(
        requirements,
        (
            0,
            slice11._scalar_scope(
                "similarity",
                slice11._builtin("text"),
                slice11._builtin("text"),
            ),
            selection,
        ),
    )
    fact_set = slice11._inspection(context)
    outcome = evaluate_extension_catalog_inspection_document(
        _extension_catalog_inspection_pure_document(fact_set.inspection)
    )
    assert outcome.status is ExtensionCatalogInspectionPureStatus.OK
    assert outcome.canonical_bytes == fact_set.canonical_bytes


def test_python_312_313_witnesses_are_byte_identical(
    witness_matrix: dict[str, str],
) -> None:
    """The matrix's only consumer, so each runtime builds it once: interpreters,
    hash seeds, both relocated roots and the combined branches."""
    current = sys.version_info[:2]
    assert current in differential._SUPPORTED_INTERPRETERS
    assert witness_matrix["current:default"] == EXPECTED_WITNESS
    assert witness_matrix[f"python{current[0]}.{current[1]}:0"] == EXPECTED_WITNESS
    for version in differential._SUPPORTED_INTERPRETERS:
        key = f"python{version[0]}.{version[1]}:0"
        if key in witness_matrix:
            assert witness_matrix[key] == EXPECTED_WITNESS
    if "python3.12:0" in witness_matrix and "python3.13:0" in witness_matrix:
        assert witness_matrix["python3.12:0"] == witness_matrix["python3.13:0"]
    assert {
        witness_matrix[f"current:{seed if seed is not None else 'default'}"]
        for seed in differential._SEEDS
    } == {EXPECTED_WITNESS}
    assert witness_matrix["relocated-one:default"] == EXPECTED_WITNESS
    assert witness_matrix["relocated-two:default"] == EXPECTED_WITNESS
    for direct_key, combined_key in (
        ("python3.12:0", "combined:python3.12:seed1:relocated-one"),
        (
            "python3.13:0",
            "combined:python3.13:seed4294967295:relocated-two",
        ),
    ):
        assert (combined_key in witness_matrix) == (direct_key in witness_matrix)
        if combined_key in witness_matrix:
            assert witness_matrix[combined_key] == EXPECTED_WITNESS


def test_missing_opposite_interpreter_keeps_current_proof(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    current = sys.version_info[:2]
    assert current in differential._SUPPORTED_INTERPRETERS
    module = differential
    monkeypatch.setattr(shutil, "which", lambda _command: None)
    monkeypatch.setattr(module, "_relocate_repository", lambda _source, _target: None)
    monkeypatch.setattr(
        module,
        "_subprocess_witness",
        lambda _executable, _seed, _root: EXPECTED_WITNESS,
    )
    observed = differential._build_witness_matrix(tmp_path_factory)
    combined_key = (
        "combined:python3.12:seed1:relocated-one"
        if current == (3, 12)
        else "combined:python3.13:seed4294967295:relocated-two"
    )
    assert set(observed) == {
        "current:default",
        "current:0",
        "current:1",
        "current:4294967295",
        f"python{current[0]}.{current[1]}:0",
        "relocated-one:default",
        "relocated-two:default",
        combined_key,
    }
    assert set(observed.values()) == {EXPECTED_WITNESS}


def test_discovered_interpreter_must_report_claimed_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = sys.version_info[:2]
    opposite = next(
        version
        for version in differential._SUPPORTED_INTERPRETERS
        if version != current
    )
    claimed = f"/claimed/python{opposite[0]}.{opposite[1]}"
    monkeypatch.setattr(shutil, "which", lambda _command: claimed)
    monkeypatch.setattr(
        differential,
        "_interpreter_version",
        lambda executable: current if executable == claimed else None,
    )
    assert differential._available_supported_interpreters() == {current: sys.executable}


def test_predecessor_pure_catalog_inspection_and_version_contracts_are_zero_delta() -> (
    None
):
    assert package_pure.PACKAGE_PURE_FORMAT_MARKER == "pietto.package-inspection.v1"
    assert CapabilityInspectionFormat.CAPABILITY_INSPECTION_V1.value == (
        "pietto.capability-inspection.v1"
    )
    assert slice11._corpus_digest() == EXPECTED_CAPABILITY_CORPUS_DIGEST
    assert PGVECTOR_V086_POSTGRESQL18_CATALOG.content_sha256 == EXPECTED_PGVECTOR[1]
    assert PG_TRGM_V16_POSTGRESQL18_CATALOG.content_sha256 == EXPECTED_PG_TRGM[1]
    assert (
        len(PGVECTOR_V086_POSTGRESQL18_CATALOG.canonical_bytes)
        == (EXPECTED_PGVECTOR[0])
    )
    assert (
        len(PG_TRGM_V16_POSTGRESQL18_CATALOG.canonical_bytes) == (EXPECTED_PG_TRGM[0])
    )
    fact_set = slice11._inspection(slice11._production_context())
    assert (
        len(fact_set.canonical_bytes),
        hashlib.sha256(fact_set.canonical_bytes).hexdigest(),
    ) == EXPECTED_INSPECTION
    assert tuple(
        field.name for field in fields(slice11.ExtensionCatalogInspection)
    ) == (
        "format",
        "requirement_namespace",
        "requirement_name",
        "catalogs",
        "provider_occurrences",
        "context",
    )


def test_new_pure_modules_are_private_and_not_publicly_exported() -> None:
    assert catalog_pure.__all__ == inspection_pure.__all__ == ()
    for module in (pietto, semantic_package, project_package):
        for name in (
            "ExtensionCatalogPureDocument",
            "ExtensionCatalogInspectionPureDocument",
            "evaluate_extension_catalog_document",
            "evaluate_extension_catalog_inspection_document",
        ):
            assert not hasattr(module, name)
    for path in (
        REPO_ROOT / "src/pietto/__init__.py",
        REPO_ROOT / "src/pietto/semantic/__init__.py",
        REPO_ROOT / "src/pietto/_project/__init__.py",
    ):
        source = path.read_text(encoding="utf-8")
        assert "extension_catalog_pure_boundary" not in source
        assert "extension_catalog_inspection_pure_boundary" not in source


def test_spec_and_package_smoke_are_exact() -> None:
    spec = SPEC.read_text(encoding="utf-8")
    for value in (
        "pietto.extension-catalog.v1",
        "pietto.extension-catalog-inspection.v1",
        "ExtensionCatalogPureStatus",
        "ExtensionCatalogInspectionPureStatus",
        "47",
        "14",
        "33",
        "19",
        "28",
        EXPECTED_CORPUS_DIGEST,
        EXPECTED_PGVECTOR[1],
        EXPECTED_PG_TRGM[1],
        EXPECTED_INSPECTION[1],
        "PYTHONHASHSEED",
        "Python 3.12",
        "Python 3.13",
        "Relocation",
        "Slice 13 remains unstarted and unauthorized",
    ):
        assert value in spec
    package_smoke = PACKAGE_SMOKE.read_text(encoding="utf-8")
    for value in (
        'f"{prefix}/semantic/extension_catalog_pure_boundary.py"',
        'f"{prefix}/_project/extension_catalog_inspection_pure_boundary.py"',
        '"from pietto.semantic.extension_catalog_pure_boundary "',
        '"from pietto._project.extension_catalog_inspection_pure_boundary "',
        "evaluate_extension_catalog_document",
    ):
        assert value in package_smoke
