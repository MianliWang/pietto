from __future__ import annotations

import ast
from dataclasses import fields
import hashlib
import inspect
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

import _pietto_package_differential_vectors as vectors
import pietto
import pietto._project as project_package
import pietto._project.package_inspection as package_inspection
import pietto._project.package_pure_boundary as pure_boundary
import test_phase55_slice10_package_inspection_canonical_serialization as slice10
from pietto._project.config import load_project_config
from pietto._project.package_inspection import _build_package_inspection_fact_set
from pietto._project.package_load_plan import (
    PackageLoadPlanBlockerKind,
    PackageLoadPlanResult,
    _build_package_load_plan,
)
from pietto._project.package_loader import LoadedRootPackage, _load_root_package
from pietto._project.package_locator import LocatedRootPackage, _locate_root_package
from pietto._project.path_trust import ProjectPinnedRoot
from pietto.errors import Diagnostic, Severity, SourceLocation


REPO_ROOT = Path(__file__).resolve().parents[1]
VECTOR_REL = "tests/_pietto_package_differential_vectors.py"
SOURCE_REL = "src/pietto/_project/package_pure_boundary.py"

_SUPPORTED_INTERPRETERS = ((3, 12), (3, 13))
_IDENTIFIER_CHARACTERS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_")


def _run_corpus() -> tuple[tuple[str, str, bool], ...]:
    corpus = vectors.differential_vectors()
    assert type(corpus) is tuple and corpus
    identifiers: set[str] = set()
    results: list[tuple[str, str, bool]] = []
    for vector in corpus:
        assert type(vector) is vectors.PackageDifferentialVector
        assert vector.vector_format == vectors.PACKAGE_DIFFERENTIAL_VECTOR_FORMAT
        assert vector.vector_id and not (set(vector.vector_id) - _IDENTIFIER_CHARACTERS)
        assert vector.vector_id not in identifiers
        identifiers.add(vector.vector_id)
        assert type(vector.purposes) is tuple and vector.purposes
        assert all(type(purpose) is str and purpose for purpose in vector.purposes)
        assert type(vector.document) is pure_boundary.PackagePureDocument
        assert type(vector.expected_status) is pure_boundary.PackagePureStatus
        outcome = pure_boundary.evaluate_package_document(vector.document)
        matched = (
            outcome.status is vector.expected_status
            and outcome.record_position == vector.expected_record_position
            and outcome.field_position == vector.expected_field_position
            and (
                vector.expected_status is not pure_boundary.PackagePureStatus.OK
                or outcome.canonical_bytes == vector.expected_bytes
            )
        )
        if vector.expected_status is pure_boundary.PackagePureStatus.OK:
            assert vector.classification is (
                vectors.PackageDifferentialClassification.PORTABLE_EVALUATION
            )
            assert type(vector.expected_bytes) is bytes
        else:
            assert vector.classification is (
                vectors.PackageDifferentialClassification.PORTABLE_REJECTION
            )
            assert vector.expected_bytes is None
        results.append((vector.vector_id, outcome.status.value, matched))
    return tuple(results)


def _corpus_digest() -> str:
    payload = "\n".join(
        f"{vector_id}:{status}:{matched}"
        for vector_id, status, matched in _run_corpus()
    )
    return hashlib.sha256(payload.encode()).hexdigest()


_SUBPROCESS_DIGEST = (
    "import hashlib\n"
    "import _pietto_package_differential_vectors as vectors\n"
    "from pietto._project.package_pure_boundary import evaluate_package_document\n"
    "rows = []\n"
    "for vector in vectors.differential_vectors():\n"
    "    outcome = evaluate_package_document(vector.document)\n"
    "    matched = (\n"
    "        outcome.status is vector.expected_status\n"
    "        and outcome.record_position == vector.expected_record_position\n"
    "        and outcome.field_position == vector.expected_field_position\n"
    "        and (vector.expected_bytes is None or outcome.canonical_bytes == vector.expected_bytes)\n"
    "    )\n"
    "    rows.append(f'{vector.vector_id}:{outcome.status.value}:{matched}')\n"
    "print(hashlib.sha256('\\n'.join(rows).encode()).hexdigest(), end='')\n"
)


def _subprocess_digest(executable: str, seed: str) -> str:
    environment = dict(os.environ)
    environment["PYTHONHASHSEED"] = seed
    environment["PYTHONPATH"] = os.pathsep.join(
        (str(REPO_ROOT / "src"), str(REPO_ROOT / "tests"))
    )
    completed = subprocess.run(
        [executable, "-c", _SUBPROCESS_DIGEST],
        check=True,
        text=True,
        capture_output=True,
        env=environment,
        cwd=REPO_ROOT.parent,
    )
    return completed.stdout


def test_package_pure_boundary_is_private_data_only_and_total() -> None:
    assert pure_boundary.__all__ == ()
    assert pure_boundary.PACKAGE_PURE_FORMAT_MARKER == ("pietto.package-inspection.v1")
    assert pure_boundary.PACKAGE_PURE_MAX_INTEGER == 2**63 - 1
    assert tuple(pure_boundary.PACKAGE_PURE_RECORD_KINDS) == (
        "inspection",
        "root",
        "package",
        "asset",
        "dependency",
        "error",
        "diagnostic",
        "rejection",
        "rejection_reason",
        "rejection_occurrence",
    )
    source = (REPO_ROOT / SOURCE_REL).read_text(encoding="utf-8")
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
        "thread",
        "time.",
        "repr(",
        "id(",
    ):
        assert forbidden not in source
    for name in (
        "PackagePureValue",
        "PackagePureDocument",
        "evaluate_package_document",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(project_package, name)


def test_production_uses_one_pure_canonical_serialization_path() -> None:
    serializer = inspect.getsource(package_inspection._serialize_package_inspection)
    projection = inspect.getsource(package_inspection._package_pure_document)
    source = inspect.getsource(package_inspection)
    assert "evaluate_package_document" in serializer
    assert "_package_pure_document" in serializer
    assert "PackagePureDocument" in projection
    assert "def _escape_text" not in source
    assert 'encode("utf-8")' not in serializer


def test_frozen_corpus_matches_all_literal_expectations() -> None:
    results = _run_corpus()
    assert len(results) == 55
    assert all(matched for _, _, matched in results)
    corpus = vectors.differential_vectors()
    accepted = tuple(
        vector
        for vector in corpus
        if vector.expected_status is pure_boundary.PackagePureStatus.OK
    )
    rejected = tuple(vector for vector in corpus if vector not in accepted)
    assert len(accepted) == 14
    assert len(rejected) == 41


def test_corpus_covers_the_required_package_matrix() -> None:
    purposes = {
        purpose
        for vector in vectors.differential_vectors()
        for purpose in vector.purposes
    }
    required = {
        "zero_dependency_root",
        "one_dependency",
        "multiple_dependencies",
        "multihop_dependency_chain",
        "duplicate_dependency_occurrences",
        "owner_distinct_same_module_path",
        "non_ascii_text",
        "control_character_text",
        "escaping",
        "several_assets",
        "ordered_project_errors",
        "parser_diagnostic",
        "cycle",
        "physical_conflict_reason",
        "version_conflict_reason",
        "identity_conflict_reason",
        "digest_conflict_reason",
        "ordered_multi_cause_conflict",
        "diamond",
        "wrong_format_marker",
        "missing_required_record",
        "unknown_record_kind",
        "wrong_key_order",
        "missing_field",
        "extra_field",
        "wrong_scalar_tag",
        "malformed_optional",
        "negative_ordinal",
        "integer_out_of_range",
        "invalid_enumeration",
        "invalid_sha256",
        "duplicate_singleton_header",
        "wrong_section_order",
        "wrong_child_count",
        "package_count_mismatch",
        "root_not_final",
        "target_outside_ledger",
        "target_self_or_later",
        "duplicate_package_position",
        "sparse_asset_position",
        "sparse_dependency_position",
        "sparse_error_position",
        "sparse_rejection_position",
        "success_with_failure_evidence",
        "failed_without_evidence",
        "conflicting_failure_families",
        "cycle_occurrence_count_mismatch",
        "unknown_conflict_reason",
        "malformed_declaring_authority_relation",
    }
    assert required <= purposes


def test_expected_accepted_bytes_are_frozen_literals() -> None:
    source = (REPO_ROOT / VECTOR_REL).read_text(encoding="utf-8")
    assert "evaluate_package_document" not in source
    tree = ast.parse(source)
    assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "_EXPECTED_CANONICAL_BYTES_LITERAL"
    )
    assert isinstance(assignment.value, ast.Dict)
    assert len(assignment.value.keys) == 14
    assert all(isinstance(key, ast.Constant) for key in assignment.value.keys)
    assert all(isinstance(value, ast.Constant) for value in assignment.value.values)


def test_corpus_digest_is_process_hash_seed_and_interpreter_stable() -> None:
    expected = _corpus_digest()
    observed = {
        _subprocess_digest(sys.executable, seed) for seed in ("0", "1", "4294967295")
    }
    assert observed == {expected}
    assert sys.version_info[:2] in _SUPPORTED_INTERPRETERS
    for major, minor in _SUPPORTED_INTERPRETERS:
        executable = shutil.which(f"python{major}.{minor}")
        if executable is not None:
            assert _subprocess_digest(executable, "0") == expected


def test_rejections_are_normalized_and_do_not_echo_supplied_text() -> None:
    for vector in vectors.differential_vectors():
        outcome = pure_boundary.evaluate_package_document(vector.document)
        if outcome.status is pure_boundary.PackagePureStatus.OK:
            continue
        assert outcome.canonical_bytes is None
        rendered = (
            f"{outcome.status.value}|{outcome.record_position}|{outcome.field_position}"
        )
        assert "pietto.package" not in rendered
        assert "winner" not in rendered
        assert "/" not in rendered


def test_pure_evaluator_has_no_ambient_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(*arguments: object, **keywords: object) -> object:
        del arguments, keywords
        raise AssertionError("package pure evaluation must not use ambient state")

    monkeypatch.setattr("builtins.open", refuse)
    monkeypatch.setattr(Path, "open", refuse)
    monkeypatch.setattr(Path, "read_text", refuse)
    monkeypatch.setattr(Path, "read_bytes", refuse)
    monkeypatch.setattr(os, "getcwd", refuse)
    monkeypatch.setattr(os, "listdir", refuse)
    monkeypatch.setattr(os, "urandom", refuse)
    assert all(matched for _, _, matched in _run_corpus())


def test_portable_carriers_and_outcomes_are_exact_and_atomic() -> None:
    for carrier in (
        pure_boundary.PackagePureValue,
        pure_boundary.PackagePureField,
        pure_boundary.PackagePureRecord,
        pure_boundary.PackagePureDocument,
        pure_boundary.PackagePureOutcome,
    ):
        assert hasattr(carrier, "__slots__")
    assert tuple(field.name for field in fields(pure_boundary.PackagePureValue)) == (
        "tag",
        "text",
        "integer",
    )
    with pytest.raises(TypeError):
        pure_boundary.PackagePureDocument(records=("x",))  # pyright: ignore[reportArgumentType]
    with pytest.raises(ValueError):
        pure_boundary.PackagePureOutcome(status=pure_boundary.PackagePureStatus.OK)
    with pytest.raises(ValueError):
        pure_boundary.PackagePureOutcome(
            status=pure_boundary.PackagePureStatus.UNKNOWN_RECORD_KIND,
            canonical_bytes=b"forged\n",
        )


def test_slice10_real_products_reproduce_byte_for_byte_through_pure_boundary(
    tmp_path: Path,
) -> None:
    project = tmp_path / "success"
    dep_digest = slice10._write_package(project, "dep", name="dep")
    root_digest = slice10._write_package(
        project,
        "root",
        dependencies=(("example", "dep", "1.0.0", dep_digest, "../dep"),),
    )
    result = slice10._plan(project, "root", root_digest)
    facts = _build_package_inspection_fact_set(result)
    document = package_inspection._package_pure_document(facts.inspection)
    outcome = pure_boundary.evaluate_package_document(document)
    assert outcome.status is pure_boundary.PackagePureStatus.OK
    assert outcome.canonical_bytes == facts.canonical_bytes

    error = slice10.ProjectDiscoveryError(
        slice10.ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
        "",
        "pietto-package.toml",
    )
    error_facts = _build_package_inspection_fact_set(slice10._error_result((error,)))
    error_outcome = pure_boundary.evaluate_package_document(
        package_inspection._package_pure_document(error_facts.inspection)
    )
    assert error_outcome.canonical_bytes == error_facts.canonical_bytes

    diagnostic_result = object.__new__(PackageLoadPlanResult)
    object.__setattr__(diagnostic_result, "plan", None)
    object.__setattr__(diagnostic_result, "errors", ())
    object.__setattr__(diagnostic_result, "blockers", ())
    object.__setattr__(
        diagnostic_result,
        "diagnostics",
        (
            Diagnostic(
                code="",
                severity=Severity.ERROR,
                message="",
                location=SourceLocation(path="", line=0, column=0),
                suggestion="",
            ),
        ),
    )
    diagnostic_facts = _build_package_inspection_fact_set(diagnostic_result)
    diagnostic_outcome = pure_boundary.evaluate_package_document(
        package_inspection._package_pure_document(diagnostic_facts.inspection)
    )
    assert diagnostic_outcome.canonical_bytes == diagnostic_facts.canonical_bytes


def test_schema3_multihop_relocation_duplicates_and_owner_isolation_e2e(
    tmp_path: Path,
) -> None:
    facts = []
    for location in ("one", "two"):
        project = tmp_path / location
        leaf_digest = slice10._write_package(
            project,
            "deps/leaf",
            name="leaf",
            assets=(("models/main.pietto", slice10._SOURCE_A),),
        )
        middle_digest = slice10._write_package(
            project,
            "deps/middle",
            name="middle",
            assets=(("models/main.pietto", slice10._SOURCE_A),),
            dependencies=(("example", "leaf", "1.0.0", leaf_digest, "../leaf"),),
        )
        declaration = (
            "example",
            "middle",
            "1.0.0",
            middle_digest,
            "../deps/middle",
        )
        root_digest = slice10._write_package(
            project,
            "root",
            assets=(("models/main.pietto", slice10._SOURCE_A),),
            dependencies=(declaration, declaration),
        )
        result = _schema3_plan(project, "root", root_digest)
        first = _build_package_inspection_fact_set(result)
        second = _build_package_inspection_fact_set(result)
        assert first.canonical_bytes == second.canonical_bytes
        assert tuple(package.project_path for package in first.inspection.packages) == (
            "deps/leaf",
            "deps/middle",
            "root",
        )
        assert len(first.inspection.packages[-1].dependencies) == 2
        assert (
            tuple(
                package.entry.package.modules[0].identity.path
                for package in first.inspection.packages
            )
            == ("models/main.pietto",) * 3
        )
        facts.append(first)
    assert facts[0].inspection == facts[1].inspection
    assert facts[0].canonical_bytes == facts[1].canonical_bytes


def test_schema3_digest_mismatch_and_missing_dependency_fail_closed_e2e(
    tmp_path: Path,
) -> None:
    digest_project = tmp_path / "digest"
    actual_digest = slice10._write_package(digest_project, "dep", name="dep")
    assert actual_digest != "0" * 64
    root_digest = slice10._write_package(
        digest_project,
        "root",
        dependencies=(("example", "dep", "1.0.0", "0" * 64, "../dep"),),
    )
    digest_result = _schema3_plan(digest_project, "root", root_digest)
    assert digest_result.plan is None and digest_result.errors
    digest_facts = _build_package_inspection_fact_set(digest_result)
    assert digest_facts.inspection.outcome.value == "error"
    assert (
        pure_boundary.evaluate_package_document(
            package_inspection._package_pure_document(digest_facts.inspection)
        ).canonical_bytes
        == digest_facts.canonical_bytes
    )

    missing_project = tmp_path / "missing"
    missing_root_digest = slice10._write_package(
        missing_project,
        "root",
        dependencies=(("example", "missing", "1.0.0", "a" * 64, "../missing"),),
    )
    missing_result = _schema3_plan(missing_project, "root", missing_root_digest)
    assert missing_result.plan is None and missing_result.errors
    missing_facts = _build_package_inspection_fact_set(missing_result)
    assert (
        pure_boundary.evaluate_package_document(
            package_inspection._package_pure_document(missing_facts.inspection)
        ).canonical_bytes
        == missing_facts.canonical_bytes
    )


def test_schema3_cycle_conflict_and_diamond_e2e(tmp_path: Path) -> None:
    cycle_project = tmp_path / "cycle"
    cycle_digest = slice10._write_package(
        cycle_project,
        "root",
        dependencies=(("example", "root", "1.0.0", "a" * 64, "."),),
    )
    cycle = _schema3_plan(cycle_project, "root", cycle_digest)
    assert cycle.blockers[0].kind is PackageLoadPlanBlockerKind.CYCLE

    conflict_project = tmp_path / "conflict"
    one_digest = slice10._write_package(
        conflict_project, "deps/one", name="same", version="1.0.0"
    )
    two_digest = slice10._write_package(
        conflict_project, "deps/two", name="same", version="2.0.0"
    )
    conflict_root = slice10._write_package(
        conflict_project,
        "root",
        dependencies=(
            ("example", "same", "1.0.0", one_digest, "../deps/one"),
            ("example", "same", "2.0.0", two_digest, "../deps/two"),
        ),
    )
    conflict = _schema3_plan(conflict_project, "root", conflict_root)
    assert conflict.blockers[0].kind is PackageLoadPlanBlockerKind.CONFLICT

    diamond_project = tmp_path / "diamond"
    leaf_digest = slice10._write_package(diamond_project, "deps/leaf", name="leaf")
    left_digest = slice10._write_package(
        diamond_project,
        "deps/left",
        name="left",
        dependencies=(("example", "leaf", "1.0.0", leaf_digest, "../leaf"),),
    )
    right_digest = slice10._write_package(
        diamond_project,
        "deps/right",
        name="right",
        dependencies=(("example", "leaf", "1.0.0", leaf_digest, "../leaf"),),
    )
    diamond_root = slice10._write_package(
        diamond_project,
        "root",
        dependencies=(
            ("example", "left", "1.0.0", left_digest, "../deps/left"),
            ("example", "right", "1.0.0", right_digest, "../deps/right"),
        ),
    )
    diamond = _schema3_plan(diamond_project, "root", diamond_root)
    assert diamond.blockers[0].kind is PackageLoadPlanBlockerKind.DIAMOND

    for result in (cycle, conflict, diamond):
        facts = _build_package_inspection_fact_set(result)
        outcome = pure_boundary.evaluate_package_document(
            package_inspection._package_pure_document(facts.inspection)
        )
        assert outcome.status is pure_boundary.PackagePureStatus.OK
        assert outcome.canonical_bytes == facts.canonical_bytes


def test_public_cli_json_and_module_pure_corpus_boundaries_are_unchanged() -> None:
    package_init = (REPO_ROOT / "src/pietto/_project/__init__.py").read_text(
        encoding="utf-8"
    )
    assert "package_pure_boundary" not in package_init
    assert "package_inspection" not in package_init
    for relative in (
        "src/pietto/__init__.py",
        "src/pietto/cli.py",
        "src/pietto/_project/json_v2.py",
        "src/pietto/_project/module_pure_boundary.py",
        "tests/_pietto_differential_harness.py",
        "tests/_pietto_differential_vectors.py",
    ):
        source = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert "package_pure_boundary" not in source


def _schema3_plan(
    project: Path,
    package_path: str,
    digest: str,
) -> PackageLoadPlanResult:
    (project / "pietto.toml").write_text(
        "\n".join(
            (
                "schema_version = 3",
                "",
                "[package]",
                f'path = "{package_path}"',
                'namespace = "example"',
                'name = "root"',
                'version = "1.0.0"',
                f'sha256 = "{digest}"',
                "",
            )
        ),
        encoding="utf-8",
    )
    config = load_project_config(project)
    assert config.ok and config.config is not None
    assert type(config.pinned_root) is ProjectPinnedRoot
    activation = config.config.root_package
    assert activation is not None
    located = _locate_root_package(config.pinned_root, activation)
    assert located.ok and type(located.located_root) is LocatedRootPackage
    loaded = _load_root_package(located.located_root)
    assert loaded.ok and type(loaded.loaded_package) is LoadedRootPackage
    return _build_package_load_plan(loaded.loaded_package)
