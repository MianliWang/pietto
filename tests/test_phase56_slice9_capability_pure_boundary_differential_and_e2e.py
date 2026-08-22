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
from typing import Any, cast

import pytest

import _pietto_capability_differential_vectors as vectors
import pietto
import pietto._project as project_package
import pietto._project.capability_inspection as capability_inspection
import pietto._project.capability_pure_boundary as pure_boundary
import pietto._project.module_pure_boundary as module_pure_boundary
import pietto._project.package_pure_boundary as package_pure_boundary
import test_phase56_slice8_capability_inspection_representation as slice8
from pietto._project.capability_availability import (
    DeclaredCapabilityProfileAvailabilityReady,
    build_declared_capability_profile_availability,
)
from pietto._project.capability_inspection import (
    _capability_pure_document,
    build_capability_inspection,
)
from pietto._project.capability_matrix import (
    PackageCapabilityCheckingMatrix,
    build_package_capability_checking_matrix,
)
from pietto._project.capability_pure_boundary import (
    CAPABILITY_PURE_ABSENT,
    CapabilityPureOutcome,
    CapabilityPureStatus,
    CapabilityPureTag,
    CapabilityPureValue,
    capability_pure_text,
    encode_capability_pure_value,
    evaluate_capability_document,
)
from pietto._project.model import ProjectRoot
from pietto._project.package_load_plan import LoadedDependencyPackage
from pietto._project.package_loader import LoadedRootPackage
from pietto.semantic.capability_composition import (
    CapabilityProfileCompositionSuccess,
    compose_capability_profiles,
)
from pietto.semantic.capability_facts import (
    CapabilityDisposition,
    CapabilityDispositionKind,
    CapabilityDomain,
    CapabilityKey,
    CapabilityReasonCode,
    CapabilitySupport,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
VECTOR_REL = "tests/_pietto_capability_differential_vectors.py"
SOURCE_REL = "src/pietto/_project/capability_pure_boundary.py"
EXPECTED_CORPUS_DIGEST = (
    "8453c3babda888b105f37f667f5fadf3a12aa68ca9a561bda98e5f6b6604a69e"
)
_SUPPORTED_INTERPRETERS = ((3, 12), (3, 13))
_IDENTIFIER_CHARACTERS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_")


@pytest.fixture(scope="module")
def loaded_packages(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[LoadedRootPackage, LoadedDependencyPackage]:
    return slice8.slice6.slice5._loaded_packages(
        tmp_path_factory.mktemp("slice9-packages")
    )


def _run_corpus() -> tuple[tuple[str, str, int | None, int | None, bool], ...]:
    corpus = vectors.differential_vectors()
    assert type(corpus) is tuple and corpus
    identifiers: set[str] = set()
    rows: list[tuple[str, str, int | None, int | None, bool]] = []
    for vector in corpus:
        assert type(vector) is vectors.CapabilityDifferentialVector
        assert vector.vector_format == vectors.CAPABILITY_DIFFERENTIAL_VECTOR_FORMAT
        assert vector.vector_id and not (set(vector.vector_id) - _IDENTIFIER_CHARACTERS)
        assert vector.vector_id not in identifiers
        identifiers.add(vector.vector_id)
        assert type(vector.purposes) is tuple and vector.purposes
        assert all(type(purpose) is str and purpose for purpose in vector.purposes)
        assert type(vector.document) is pure_boundary.CapabilityPureDocument
        assert type(vector.expected_status) is CapabilityPureStatus
        outcome = evaluate_capability_document(vector.document)
        matched = (
            outcome.status is vector.expected_status
            and outcome.record_position == vector.expected_record_position
            and outcome.field_position == vector.expected_field_position
            and (
                vector.expected_status is CapabilityPureStatus.OK
                and outcome.canonical_bytes == vector.expected_bytes
                or vector.expected_status is not CapabilityPureStatus.OK
                and outcome.canonical_bytes is None
            )
        )
        if vector.expected_status is CapabilityPureStatus.OK:
            assert vector.classification is (
                vectors.CapabilityDifferentialClassification.PORTABLE_EVALUATION
            )
            assert type(vector.expected_bytes) is bytes
        else:
            assert vector.classification is (
                vectors.CapabilityDifferentialClassification.PORTABLE_REJECTION
            )
            assert vector.expected_bytes is None
        rows.append(
            (
                vector.vector_id,
                outcome.status.value,
                outcome.record_position,
                outcome.field_position,
                matched,
            )
        )
    return tuple(rows)


def _corpus_digest() -> str:
    payload = "\n".join(
        f"{vector_id}:{status}:"
        f"{record if record is not None else '-'}:"
        f"{field if field is not None else '-'}:{matched}"
        for vector_id, status, record, field, matched in _run_corpus()
    )
    return hashlib.sha256(payload.encode()).hexdigest()


_SUBPROCESS_DIGEST = (
    "import hashlib\n"
    "import _pietto_capability_differential_vectors as vectors\n"
    "from pietto._project.capability_pure_boundary import CapabilityPureStatus, evaluate_capability_document\n"
    "rows = []\n"
    "for vector in vectors.differential_vectors():\n"
    "    outcome = evaluate_capability_document(vector.document)\n"
    "    matched = (\n"
    "        outcome.status is vector.expected_status\n"
    "        and outcome.record_position == vector.expected_record_position\n"
    "        and outcome.field_position == vector.expected_field_position\n"
    "        and ((vector.expected_status is CapabilityPureStatus.OK and outcome.canonical_bytes == vector.expected_bytes)\n"
    "             or (vector.expected_status is not CapabilityPureStatus.OK and outcome.canonical_bytes is None))\n"
    "    )\n"
    "    record = outcome.record_position if outcome.record_position is not None else '-'\n"
    "    field = outcome.field_position if outcome.field_position is not None else '-'\n"
    "    rows.append(f'{vector.vector_id}:{outcome.status.value}:{record}:{field}:{matched}')\n"
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


def test_capability_pure_boundary_is_private_stdlib_only_and_total() -> None:
    assert pure_boundary.__all__ == ()
    assert pure_boundary.CAPABILITY_PURE_FORMAT_MARKER == (
        "pietto.capability-inspection.v1"
    )
    assert pure_boundary.CAPABILITY_PURE_MAX_INTEGER == 2**63 - 1
    assert pure_boundary.CAPABILITY_PURE_RECORD_KINDS == (
        "inspection",
        "package",
        "requirements",
        "target",
        "target_profile",
        "availability",
        "blocker",
        "blocker_profile",
        "blocker_availability",
        "requirement",
        "requirement_operand",
        "cell",
        "target_occurrence",
        "target_fact",
        "target_fact_operand",
        "target_fact_evidence",
        "provider_fact",
        "provider_fact_operand",
        "provider_fact_evidence",
    )
    source = (REPO_ROOT / SOURCE_REL).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=SOURCE_REL)
    imported_roots = {
        node.module.split(".")[0]
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert imported_roots <= {
        "__future__",
        "collections",
        "dataclasses",
        "enum",
        "types",
    }
    for forbidden in (
        "capability_inspection",
        "capability_matrix",
        "capability_checking",
        "capability_availability",
        "capability_composition",
        "CapabilityKey",
        "CapabilityFact",
        "LoadedPackage",
        "ProjectRoot",
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
        "hash(",
    ):
        assert forbidden not in source
    with pytest.raises(TypeError):
        evaluate_capability_document(cast(Any, object()))
    for name in (
        "CapabilityPureValue",
        "CapabilityPureDocument",
        "evaluate_capability_document",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(project_package, name)


def test_exact_field_schemas_and_enum_domains_are_frozen() -> None:
    expected_fields = {
        "inspection": ("format", "declaration", "targets", "requirements"),
        "package": ("role", "namespace", "name", "release", "content_digest"),
        "requirements": ("namespace", "name", "count"),
        "target": (
            "target",
            "variant",
            "supplied_overlays",
            "dependency_profiles",
            "availability",
            "blockers",
        ),
        "target_profile": (
            "target",
            "order",
            "profile",
            "schema",
            "namespace",
            "name",
            "profile_release",
            "kind",
            "target_kind",
            "database_family",
            "target_release",
            "extension_identity",
            "extension_release",
        ),
        "availability": (
            "target",
            "occurrence",
            "owner_kind",
            "owner_position",
            "project_path",
            "schema",
            "namespace",
            "name",
            "profile_release",
            "kind",
            "target_kind",
            "database_family",
            "target_release",
            "extension_identity",
            "extension_release",
        ),
        "blocker": (
            "target",
            "blocker",
            "kind",
            "has_bucket",
            "bucket_occurrences",
        ),
        "blocker_profile": (
            "target",
            "blocker",
            "role",
            "schema",
            "namespace",
            "name",
            "profile_release",
            "kind",
            "target_kind",
            "database_family",
            "target_release",
            "extension_identity",
            "extension_release",
        ),
        "blocker_availability": (
            "target",
            "blocker",
            "occurrence",
            "owner_kind",
            "owner_position",
            "project_path",
            "schema",
            "namespace",
            "name",
            "profile_release",
            "kind",
            "target_kind",
            "database_family",
            "target_release",
            "extension_identity",
            "extension_release",
        ),
        "requirement": (
            "requirement",
            "domain",
            "subject",
            "operation",
            "operands",
            "context",
            "dialect",
            "extension",
        ),
        "requirement_operand": ("requirement", "operand", "value"),
        "cell": (
            "requirement",
            "target",
            "has_check",
            "status",
            "target_occurrences",
            "target_lookup",
            "target_reason",
            "target_lookup_facts",
            "provider_domain_complete",
            "provider_unknown_reason",
            "provider_lookup",
            "provider_reason",
            "provider_lookup_facts",
        ),
        "target_occurrence": (
            "requirement",
            "target",
            "occurrence",
            "profile",
            "profile_namespace",
            "profile_name",
            "profile_release",
            "profile_fact",
        ),
        "target_fact": (
            "requirement",
            "target",
            "occurrence",
            "domain",
            "subject",
            "operation",
            "operands",
            "context",
            "dialect",
            "extension",
            "support",
            "disposition",
            "disposition_owner",
            "disposition_reason",
            "evidence",
        ),
        "target_fact_operand": (
            "requirement",
            "target",
            "occurrence",
            "operand",
            "value",
        ),
        "target_fact_evidence": (
            "requirement",
            "target",
            "occurrence",
            "evidence",
            "source",
            "source_path",
            "source_reference",
            "reason",
            "dialect",
            "backend",
            "extension",
        ),
        "provider_fact": (
            "requirement",
            "target",
            "fact",
            "domain",
            "subject",
            "operation",
            "operands",
            "context",
            "dialect",
            "extension",
            "support",
            "disposition",
            "disposition_owner",
            "disposition_reason",
            "evidence",
        ),
        "provider_fact_operand": (
            "requirement",
            "target",
            "fact",
            "operand",
            "value",
        ),
        "provider_fact_evidence": (
            "requirement",
            "target",
            "fact",
            "evidence",
            "source",
            "source_path",
            "source_reference",
            "reason",
            "dialect",
            "backend",
            "extension",
        ),
    }
    assert {
        kind: tuple(field.key for field in specification)
        for kind, specification in pure_boundary._SCHEMA.items()
    } == expected_fields
    assert "extension_signature" in pure_boundary._CAPABILITY_DOMAINS
    assert "window_function" in pure_boundary._CAPABILITY_DOMAINS


def test_portable_carriers_tags_and_outcomes_are_exact() -> None:
    for carrier in (
        pure_boundary.CapabilityPureValue,
        pure_boundary.CapabilityPureField,
        pure_boundary.CapabilityPureRecord,
        pure_boundary.CapabilityPureDocument,
        pure_boundary.CapabilityPureOutcome,
    ):
        assert hasattr(carrier, "__slots__")
    assert tuple(field.name for field in fields(CapabilityPureValue)) == (
        "tag",
        "text",
        "integer",
        "boolean",
    )
    assert tuple(CapabilityPureTag) == (
        CapabilityPureTag.TEXT,
        CapabilityPureTag.ENUMERATION,
        CapabilityPureTag.INTEGER,
        CapabilityPureTag.BOOLEAN,
        CapabilityPureTag.ABSENT,
    )
    assert encode_capability_pure_value(capability_pure_text("")) == "s:"
    assert encode_capability_pure_value(CAPABILITY_PURE_ABSENT) == "n:"
    assert (
        encode_capability_pure_value(capability_pure_text("a\\\tb\nc\rd\x01\x7f雪"))
        == "s:a\\\\\\tb\\nc\\rd\\x01\\x7f雪"
    )
    assert (
        encode_capability_pure_value(
            CapabilityPureValue(tag=CapabilityPureTag.BOOLEAN, boolean=True)
        )
        == "b:true"
    )
    with pytest.raises(TypeError):
        CapabilityPureValue(
            tag=CapabilityPureTag.INTEGER,
            integer=cast(Any, True),
        )
    with pytest.raises(ValueError):
        CapabilityPureOutcome(status=CapabilityPureStatus.OK)
    with pytest.raises(ValueError):
        CapabilityPureOutcome(
            status=CapabilityPureStatus.UNKNOWN_RECORD_KIND,
            canonical_bytes=b"forged\n",
        )


def test_production_has_one_pure_canonical_serialization_path() -> None:
    serializer = inspect.getsource(
        capability_inspection._serialize_capability_inspection
    )
    projection = inspect.getsource(capability_inspection._capability_pure_document)
    source = inspect.getsource(capability_inspection)
    assert "evaluate_capability_document" in serializer
    assert "_capability_pure_document" in serializer
    assert "CapabilityPureDocument" in projection
    assert "def _escape_text" not in source
    assert 'encode("utf-8")' not in serializer
    assert '"\\n".join' not in serializer


def test_frozen_corpus_matches_literal_oracles_and_digest() -> None:
    rows = _run_corpus()
    assert len(rows) == 125
    assert all(matched for *_coordinates, matched in rows)
    corpus = vectors.differential_vectors()
    accepted = tuple(
        vector for vector in corpus if vector.expected_status is CapabilityPureStatus.OK
    )
    rejected = tuple(vector for vector in corpus if vector not in accepted)
    assert len(accepted) == 16
    assert len(rejected) == 109
    assert _corpus_digest() == EXPECTED_CORPUS_DIGEST


def test_corpus_covers_required_capability_matrix_and_rejections() -> None:
    purposes = {
        purpose
        for vector in vectors.differential_vectors()
        for purpose in vector.purposes
    }
    required = {
        "undeclared",
        "declared_empty",
        "root_package",
        "dependency_package",
        "satisfied",
        "unsupported",
        "absent",
        "unknown",
        "conflict",
        "blocked",
        "multiple_requirements",
        "multiple_targets",
        "rectangular_matrix",
        "sibling_overlays",
        "overlay_dependency_chain",
        "compiler_availability",
        "project_availability",
        "unicode",
        "control_characters",
        "escaping",
        "optional_absence",
        "ordered_target_conflict",
        "ordered_provider_conflict",
        "empty_document",
        "missing_inspection_header",
        "unknown_record_kind",
        "wrong_format_marker",
        "missing_field",
        "extra_field",
        "wrong_field_order",
        "wrong_scalar_tag",
        "malformed_absent_payload",
        "malformed_boolean_payload",
        "negative_integer",
        "integer_out_of_range",
        "unknown_enumeration",
        "trailing_record",
        "target_count_mismatch",
        "requirement_count_mismatch",
        "operand_count_mismatch",
        "cell_count_mismatch",
        "missing_base_projection",
        "supplied_overlay_count_mismatch",
        "dependency_profile_count_mismatch",
        "availability_count_mismatch",
        "availability_owner_path_relation",
        "duplicate_availability_owner_position",
        "sparse_availability_owner_position",
        "availability_owner_partition_order",
        "blocker_count_mismatch",
        "blocker_bucket_state",
        "blocker_availability_owner_position",
        "blocked_cell_fake_check",
        "checked_cell_requires_check",
        "target_occurrence_count_mismatch",
        "found_lookup_posture",
        "absent_lookup_posture",
        "unknown_lookup_posture",
        "conflict_lookup_posture",
        "provider_completeness_posture",
        "fact_operand_count_mismatch",
        "evidence_count_mismatch",
        "disposition_posture",
        "invalid_evidence_source",
        "malformed_optional_scope",
    }
    assert required <= purposes


def test_accepted_expected_bytes_are_static_literals() -> None:
    source = (REPO_ROOT / VECTOR_REL).read_text(encoding="utf-8")
    assert "evaluate_capability_document" not in source
    assert "capability_inspection" not in source
    tree = ast.parse(source, filename=VECTOR_REL)
    assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "_EXPECTED_CANONICAL_BYTES_LITERAL"
    )
    assert isinstance(assignment.value, ast.Dict)
    assert len(assignment.value.keys) == 16
    assert all(isinstance(key, ast.Constant) for key in assignment.value.keys)
    assert all(isinstance(value, ast.Constant) for value in assignment.value.values)


def test_corpus_is_hash_seed_and_interpreter_stable() -> None:
    observed = {
        _subprocess_digest(sys.executable, seed) for seed in ("0", "1", "4294967295")
    }
    assert observed == {EXPECTED_CORPUS_DIGEST}
    assert sys.version_info[:2] in _SUPPORTED_INTERPRETERS
    for major, minor in _SUPPORTED_INTERPRETERS:
        executable = shutil.which(f"python{major}.{minor}")
        if executable is not None:
            assert _subprocess_digest(executable, "0") == EXPECTED_CORPUS_DIGEST


def test_rejections_are_normalized_and_never_echo_or_carry_bytes() -> None:
    for vector in vectors.differential_vectors():
        outcome = evaluate_capability_document(vector.document)
        if outcome.status is CapabilityPureStatus.OK:
            continue
        assert outcome.canonical_bytes is None
        rendered = (
            f"{outcome.status.value}|{outcome.record_position}|{outcome.field_position}"
        )
        assert "pietto.capability" not in rendered
        assert "winner" not in rendered
        assert "/" not in rendered


def test_pure_evaluator_has_no_ambient_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(*arguments: object, **keywords: object) -> object:
        del arguments, keywords
        raise AssertionError("capability pure evaluation used ambient state")

    monkeypatch.setattr("builtins.open", refuse)
    monkeypatch.setattr(Path, "open", refuse)
    monkeypatch.setattr(Path, "read_text", refuse)
    monkeypatch.setattr(Path, "read_bytes", refuse)
    monkeypatch.setattr(os, "getcwd", refuse)
    monkeypatch.setattr(os, "listdir", refuse)
    monkeypatch.setattr(os, "urandom", refuse)
    assert all(matched for *_coordinates, matched in _run_corpus())


def _assert_zero_delta(matrix: PackageCapabilityCheckingMatrix) -> None:
    fact_set = build_capability_inspection(matrix)
    document = _capability_pure_document(fact_set.inspection)
    outcome = evaluate_capability_document(document)
    assert outcome.status is CapabilityPureStatus.OK
    assert outcome.canonical_bytes == fact_set.canonical_bytes


def test_real_slice1_to_slice8_products_reproduce_exact_bytes(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    slice6 = slice8.slice6
    matrices: list[PackageCapabilityCheckingMatrix] = []

    empty_composition = slice6._composition()
    empty_context = slice8._context(0, empty_composition)
    matrices.append(
        build_package_capability_checking_matrix(package, None, (empty_context,))
    )
    matrices.append(
        build_package_capability_checking_matrix(
            package,
            slice6._binding(package),
            (empty_context,),
        )
    )

    supported_key = slice6._SUPPORTED_PROVIDER_FACT.key
    supported = slice6._target_fact(supported_key)
    unsupported = slice6._target_fact(
        supported_key,
        support=CapabilitySupport.EXPLICITLY_UNSUPPORTED,
    )
    absent_key = CapabilityKey(
        CapabilityDomain.LOGICAL_TYPE,
        subject="FutureScalar",
        operation="catalog_membership",
        context="builtin_registry",
    )
    unknown_key = CapabilityKey(CapabilityDomain.CONVERSION, subject="future")
    checked_cases = (
        (supported_key, slice6._composition(supported)),
        (supported_key, slice6._composition(unsupported)),
        (absent_key, slice6._composition(slice6._target_fact(absent_key))),
        (unknown_key, slice6._composition(slice6._target_fact(unknown_key))),
        (
            slice6._COUNT_CONFLICT_KEY,
            slice6._composition(slice6._target_fact(slice6._COUNT_CONFLICT_KEY)),
        ),
    )
    for key, composition in checked_cases:
        matrices.append(
            build_package_capability_checking_matrix(
                package,
                slice6._binding(package, key),
                (slice8._context(0, composition),),
            )
        )

    blocked_composition = slice6._composition()
    unavailable = build_declared_capability_profile_availability(
        slice6.slice5._compiler_ledger()
    )
    assert isinstance(unavailable, DeclaredCapabilityProfileAvailabilityReady)
    matrices.append(
        build_package_capability_checking_matrix(
            package,
            slice6._binding(package, supported_key),
            (slice8._context(0, blocked_composition, unavailable),),
        )
    )
    matrices.append(
        build_package_capability_checking_matrix(
            package,
            slice6._binding(package, supported_key),
            (
                slice8._context(0, slice6._composition(supported)),
                slice8._context(1, slice6._composition()),
            ),
        )
    )

    base = slice6.slice4._base(facts=(supported,))
    overlay = slice6.slice4._overlay("overlay", base.profile)
    overlay_composition = compose_capability_profiles(base, (overlay,))
    assert isinstance(overlay_composition, CapabilityProfileCompositionSuccess)
    matrices.append(
        build_package_capability_checking_matrix(
            package,
            slice6._binding(package, supported_key),
            (slice8._context(0, overlay_composition),),
        )
    )

    project_base = slice6.slice4._base()
    project_composition = compose_capability_profiles(project_base, ())
    assert isinstance(project_composition, CapabilityProfileCompositionSuccess)
    project = ProjectRoot("logical/project")
    project_availability = build_declared_capability_profile_availability(
        slice6.slice5._compiler_ledger(),
        slice6.slice5._project_ledger(project, project_base),
    )
    assert isinstance(project_availability, DeclaredCapabilityProfileAvailabilityReady)
    matrices.append(
        build_package_capability_checking_matrix(
            package,
            slice6._binding(package),
            (slice8._context(0, project_composition, project_availability),),
        )
    )

    for matrix in matrices:
        _assert_zero_delta(matrix)


def test_relocation_and_hidden_authority_do_not_change_values(tmp_path: Path) -> None:
    first, _ = slice8.slice6.slice5._loaded_packages(tmp_path / "first")
    second, _ = slice8.slice6.slice5._loaded_packages(tmp_path / "second")
    first_facts = slice8._unknown_inspection(first)
    second_facts = slice8._unknown_inspection(second)

    assert first is not second
    assert first_facts.inspection == second_facts.inspection
    assert first_facts.canonical_bytes == second_facts.canonical_bytes
    first_outcome = evaluate_capability_document(
        _capability_pure_document(first_facts.inspection)
    )
    second_outcome = evaluate_capability_document(
        _capability_pure_document(second_facts.inspection)
    )
    assert first_outcome.canonical_bytes == second_outcome.canonical_bytes
    for root in (tmp_path / "first", tmp_path / "second"):
        assert str(root).encode() not in cast(bytes, first_outcome.canonical_bytes)


def test_semantic_sensitivity_survives_pure_migration(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    baseline = slice8._unknown_inspection(package)
    variants = (
        slice8._unknown_inspection(package, subject="Value"),
        slice8._unknown_inspection(
            package,
            support=CapabilitySupport.EXPLICITLY_UNSUPPORTED,
        ),
        slice8._unknown_inspection(package, source_path="other/path"),
        slice8._unknown_inspection(package, source_reference="other reference"),
        slice8._unknown_inspection(
            package,
            evidence_reason=CapabilityReasonCode.NO_CURRENT_RESULT_RULE,
        ),
        slice8._unknown_inspection(
            package,
            disposition=CapabilityDisposition(
                CapabilityDispositionKind.DEFERRED,
                "Phase 60",
                "later",
            ),
        ),
        slice8._unknown_inspection(package, profile_release="other release"),
        slice8._unknown_inspection(package, project=True),
        slice8._unknown_inspection(package, availability_position_one=True),
    )
    for variant in variants:
        assert variant.canonical_bytes != baseline.canonical_bytes
        outcome = evaluate_capability_document(
            _capability_pure_document(variant.inspection)
        )
        assert outcome.canonical_bytes == variant.canonical_bytes


def test_slice8_byte_locks_and_existing_pure_boundaries_remain_isolated(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    assert slice8._lock_payloads(package) == slice8._EXACT_BYTE_LOCKS
    for module in (module_pure_boundary, package_pure_boundary):
        source = inspect.getsource(module)
        assert "capability_pure_boundary" not in source
        assert "CapabilityPure" not in source
    for relative in (
        "tests/_pietto_differential_vectors.py",
        "tests/_pietto_package_differential_vectors.py",
    ):
        source = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert "capability_pure_boundary" not in source


def test_no_public_artifact_classifier_or_runtime_surface_is_added() -> None:
    assert capability_inspection.__all__ == ()
    for name in (
        "CapabilityPureDocument",
        "CapabilityPureOutcome",
        "evaluate_capability_document",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(project_package, name)
    source = inspect.getsource(capability_inspection).lower()
    for forbidden in (
        "portabilityclassifier",
        "portable_status",
        "best_target",
        "worst_status",
        "json.dumps",
        "database connection",
        "requests",
        "socket",
    ):
        assert forbidden not in source
