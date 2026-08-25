from __future__ import annotations

from dataclasses import fields
import json
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
import test_phase58_slice13_project_explain_runtime_builder as slice13
from pietto._project.capability_checking import (
    _selected_profile_availability_blockers,
)
from pietto._project.config import load_project_config
from pietto._project.extension_catalog_availability import (
    ExtensionCatalogAvailabilityOwner,
    ExtensionCatalogSelectionOutcome,
)
from pietto._project.model import ProjectCapabilityEnvironmentConfig
from pietto._project.project_capability_environment import (
    _build_project_capability_environment,
)
from pietto._project_explain.compatibility_matrix_projection import (
    ProjectExplainCheckedStatus,
    ProjectExplainEvaluationState,
)
from pietto._project_explain.extension_catalog_evidence_projection import (
    ProjectExplainCatalogSelectionOutcome,
    ProjectExplainExtensionCatalogTypeReference,
)
from pietto._project_explain.json_v1 import (
    serialize_project_explain_json_document,
)
from pietto._project_explain.portability_projection import (
    ProjectExplainPortabilityClassification,
    ProjectExplainPortabilityReason,
)
from pietto._project_explain.runtime_builder import (
    ProjectExplainRuntimeOutcome,
    _build_project_explain_runtime,
)
from pietto._project_explain.text import render_project_explain_text


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase58-slice15-reachability-aware-multi-target-end-to-end-assurance-v1.md"
)

ROOT_SELECTOR = '''[[extension_signature_selectors]]
requirement_position = 0
family = "native_type"
physical_name = "halfvec"'''
UNSUPPORTED_REQUIREMENT = """[[capability_requirements.entries]]
domain = "logical_type"
subject = "UnsupportedType"
operands = []"""
ABSENT_REQUIREMENT = '''[[capability_requirements.entries]]
domain = "logical_type"
subject = "AbsentType"
operation = "catalog_membership"
operands = []
context = "builtin_registry"'''
CONFLICT_REQUIREMENT = """[[capability_requirements.entries]]
domain = "logical_type"
subject = "ConflictType"
operands = []"""


def _fact(
    support: str,
    domain: str,
    *,
    subject: str | None = None,
    operation: str | None = None,
    context: str | None = None,
    dialect: str | None = None,
    extension: str | None = None,
) -> str:
    lines = [
        "[[capability_environment.profiles.facts]]",
        f'support = "{support}"',
        f'domain = "{domain}"',
    ]
    for key, value in (
        ("subject", subject),
        ("operation", operation),
        ("context", context),
        ("dialect", dialect),
        ("extension", extension),
    ):
        if value is not None:
            lines.append(f'{key} = "{value}"')
    lines.append("operands = []")
    return "\n".join(lines)


def _profile(
    name: str,
    database_release: str,
    *,
    kind: str = "base",
    facts: tuple[str, ...] = (),
    extension_identity: str = "vector",
    extension_release: str = "0.8.6",
    base_name: str = "base",
) -> str:
    lines = [
        "[[capability_environment.profiles]]",
        'namespace = "profiles"',
        f'name = "{name}"',
        'release = "r1"',
        f'kind = "{kind}"',
        'database_family = "PostgreSQL"',
        f'database_release = "{database_release}"',
    ]
    if kind == "overlay":
        lines.extend(
            (
                f'extension_identity = "{extension_identity}"',
                f'extension_release = "{extension_release}"',
                'base_namespace = "profiles"',
                f'base_name = "{base_name}"',
                'base_release = "r1"',
            )
        )
    for fact in facts:
        lines.extend(("", fact))
    return "\n".join(lines)


def _target(base_name: str, database_release: str, overlay_name: str | None) -> str:
    lines = [
        "[[capability_environment.targets]]",
        'database_family = "PostgreSQL"',
        f'database_release = "{database_release}"',
        'base_profile_namespace = "profiles"',
        f'base_profile_name = "{base_name}"',
        'base_profile_release = "r1"',
    ]
    if overlay_name is not None:
        lines.extend(
            (
                "",
                "[[capability_environment.targets.overlays]]",
                'namespace = "profiles"',
                f'name = "{overlay_name}"',
                'release = "r1"',
            )
        )
    return "\n".join(lines)


def _project_config(
    package_path: str,
    digest: str,
    *,
    profiles: tuple[str, ...] = (),
    targets: tuple[str, ...] = (),
    environment_entries: tuple[str, ...] = (),
) -> str:
    return "\n".join(
        (
            "schema_version = 4",
            "",
            "[package]",
            f'path = "{package_path}"',
            'namespace = "example"',
            'name = "root"',
            'version = "1.0.0"',
            f'sha256 = "{digest}"',
            "",
            "[capability_environment]",
            *environment_entries,
            *(part for section in (*profiles, *targets) for part in ("", section)),
            "",
        )
    )


def _write_single_project(
    tmp_path: Path,
    manifest: bytes,
    *,
    profiles: tuple[str, ...] = (),
    targets: tuple[str, ...] = (),
    environment_entries: tuple[str, ...] = (),
    name: str,
) -> Path:
    root = tmp_path / name
    digest = slice13._write_package(root / "package", manifest)
    (root / "pietto.toml").write_text(
        _project_config(
            "package",
            digest,
            profiles=profiles,
            targets=targets,
            environment_entries=environment_entries,
        ),
        encoding="utf-8",
    )
    return root


def _multi_package_multi_target_project(tmp_path: Path, name: str) -> Path:
    root = tmp_path / name
    dependency_manifest = slice13._manifest(
        3,
        namespace="example",
        name="dependency",
        requirements=(slice13.EXTENSION_REQUIREMENT,),
        selectors=(slice13.EXTENSION_SELECTOR,),
    )
    dependency_digest = slice13._write_package(root / "dependency", dependency_manifest)
    root_manifest = slice13._manifest(
        3,
        requirements=(
            slice13.EXTENSION_REQUIREMENT,
            UNSUPPORTED_REQUIREMENT,
            ABSENT_REQUIREMENT,
            CONFLICT_REQUIREMENT,
        ),
        selectors=(ROOT_SELECTOR,),
        dependencies=(
            ("example", "dependency", "1.0.0", dependency_digest, "../dependency"),
        ),
    )
    root_digest = slice13._write_package(root / "root", root_manifest)
    extension_fact = _fact(
        "supported",
        "extension_signature",
        operation="vector-native-type",
        dialect="postgresql",
        extension="vector",
    )
    absent_fact = _fact(
        "supported",
        "logical_type",
        subject="AbsentType",
        operation="catalog_membership",
        context="builtin_registry",
    )
    profiles = (
        _profile(
            "base18",
            "18",
            facts=(
                _fact(
                    "explicitly_unsupported",
                    "logical_type",
                    subject="UnsupportedType",
                ),
                absent_fact,
                _fact("supported", "logical_type", subject="ConflictType"),
                _fact(
                    "explicitly_unsupported",
                    "logical_type",
                    subject="ConflictType",
                ),
            ),
        ),
        _profile(
            "vector18",
            "18",
            kind="overlay",
            facts=(extension_fact,),
            base_name="base18",
        ),
        _profile("base17", "17", facts=(absent_fact,)),
        _profile(
            "vector17",
            "17",
            kind="overlay",
            facts=(extension_fact,),
            base_name="base17",
        ),
    )
    targets = (
        _target("base18", "18", "vector18"),
        _target("base17", "17", "vector17"),
    )
    (root / "pietto.toml").write_text(
        _project_config("root", root_digest, profiles=profiles, targets=targets),
        encoding="utf-8",
    )
    return root


def test_real_multi_package_multi_target_runtime_preserves_authority_and_states(
    tmp_path: Path,
) -> None:
    root = _multi_package_multi_target_project(tmp_path, "matrix")

    result = _build_project_explain_runtime(root)

    assert result.outcome is ProjectExplainRuntimeOutcome.SUCCESS
    assert result == _build_project_explain_runtime(root)
    payload = result.envelope.payload
    assert payload is not None
    assert tuple(
        (package.position, package.coordinate.name)
        for package in payload.package_requirements.packages
    ) == ((0, "dependency"), (1, "root"))
    assert payload.package_requirements.packages[0].dependencies == ()
    assert tuple(
        dependency.target_package_position
        for dependency in payload.package_requirements.packages[1].dependencies
    ) == (0,)
    requests = payload.package_requirements.requirements
    assert tuple(
        (
            request.position,
            request.declared_by,
            request.requested_by,
            request.occurrence_position,
        )
        for request in requests
    ) == (
        (0, 0, 1, 0),
        (1, 1, 1, 0),
        (2, 1, 1, 1),
        (3, 1, 1, 2),
        (4, 1, 1, 3),
    )
    assert requests[0].key == requests[1].key
    assert tuple(
        (request.key.operation, request.key.subject) for request in requests
    ) == (
        ("vector-native-type", None),
        ("vector-native-type", None),
        (None, "UnsupportedType"),
        ("catalog_membership", "AbsentType"),
        (None, "ConflictType"),
    )
    assert tuple(
        (target.position, target.database_release)
        for target in payload.compatibility.targets
    ) == ((0, "18"), (1, "17"))
    assert tuple(
        (evaluation.package_position, evaluation.target_position, evaluation.state)
        for evaluation in payload.compatibility.package_target_evaluations
    ) == (
        (0, 0, ProjectExplainEvaluationState.CHECKED),
        (0, 1, ProjectExplainEvaluationState.CHECKED),
        (1, 0, ProjectExplainEvaluationState.CHECKED),
        (1, 1, ProjectExplainEvaluationState.CHECKED),
    )
    assert tuple(
        tuple(cell.checked_status for cell in row.cells)
        for row in payload.compatibility.rows
    ) == (
        (ProjectExplainCheckedStatus.SATISFIED, ProjectExplainCheckedStatus.UNKNOWN),
        (ProjectExplainCheckedStatus.SATISFIED, ProjectExplainCheckedStatus.UNKNOWN),
        (ProjectExplainCheckedStatus.UNSUPPORTED, ProjectExplainCheckedStatus.UNKNOWN),
        (ProjectExplainCheckedStatus.ABSENT, ProjectExplainCheckedStatus.ABSENT),
        (ProjectExplainCheckedStatus.CONFLICT, ProjectExplainCheckedStatus.UNKNOWN),
    )
    assert tuple(
        row.requirement_position for row in payload.compatibility.rows
    ) == tuple(range(5))
    contexts = payload.extension_catalog_evidence.contexts
    assert tuple(
        (context.package_position, context.target_position) for context in contexts
    ) == ((0, 0), (0, 1), (1, 0), (1, 1))
    assert tuple(context.requirements[0].selection.outcome for context in contexts) == (
        ProjectExplainCatalogSelectionOutcome.SELECTED,
        ProjectExplainCatalogSelectionOutcome.UNDECLARED,
        ProjectExplainCatalogSelectionOutcome.SELECTED,
        ProjectExplainCatalogSelectionOutcome.UNDECLARED,
    )
    assert all(
        type(context.requirements[0].selector.identity)
        is ProjectExplainExtensionCatalogTypeReference
        for context in contexts
    )
    assert tuple(
        cast(
            ProjectExplainExtensionCatalogTypeReference,
            context.requirements[0].selector.identity,
        ).physical_name
        for context in contexts
    ) == ("vector", "vector", "halfvec", "halfvec")
    assert payload.portability.classification is (
        ProjectExplainPortabilityClassification.NOT_PORTABLE
    )
    assert {
        gap.status
        for requirement in payload.portability.requirements
        for gap in requirement.definite_gaps
    } == {
        ProjectExplainCheckedStatus.UNSUPPORTED,
        ProjectExplainCheckedStatus.ABSENT,
    }
    assert tuple(
        (
            explanation.request.positions,
            explanation.declared_by.positions,
            explanation.requested_by.positions,
            explanation.portability.positions,
        )
        for explanation in payload.requirement_explanations
    ) == (
        ((0,), (0,), (1,), (0,)),
        ((1,), (1,), (1,), (1,)),
        ((2,), (1,), (1,), (2,)),
        ((3,), (1,), (1,), (3,)),
        ((4,), (1,), (1,), (4,)),
    )


def test_current_runtime_structurally_prevents_blocked_and_catalog_multi_candidate(
    tmp_path: Path,
) -> None:
    root = _multi_package_multi_target_project(tmp_path, "coherent")
    loaded = load_project_config(root)
    assert loaded.ok and loaded.root is not None and loaded.config is not None
    environment_result = _build_project_capability_environment(
        loaded.root, loaded.config
    )
    assert environment_result.ok and environment_result.environment is not None
    environment = environment_result.environment

    assert tuple(
        field.name for field in fields(ProjectCapabilityEnvironmentConfig)
    ) == (
        "profiles",
        "targets",
    )
    assert all(
        _selected_profile_availability_blockers(
            target.composition,
            environment.profile_availability,
        )
        == ()
        for target in environment.targets
    )
    declarations = environment.extension_catalog_availability.declarations
    assert all(
        declaration.owner is ExtensionCatalogAvailabilityOwner.COMPILER
        and declaration.project is None
        for declaration in declarations
    )
    assert len({declaration.target for declaration in declarations}) == len(
        declarations
    )
    assert tuple(member.value for member in ExtensionCatalogSelectionOutcome) == (
        "undeclared",
        "selected",
        "ambiguous",
        "conflict",
    )

    result = _build_project_explain_runtime(root)
    payload = result.envelope.payload
    assert payload is not None
    assert all(
        evaluation.state is not ProjectExplainEvaluationState.BLOCKED
        for evaluation in payload.compatibility.package_target_evaluations
    )
    assert {
        context.requirements[0].selection.outcome
        for context in payload.extension_catalog_evidence.contexts
    } == {
        ProjectExplainCatalogSelectionOutcome.SELECTED,
        ProjectExplainCatalogSelectionOutcome.UNDECLARED,
    }


@pytest.mark.parametrize(
    ("case", "message"),
    (
        ("missing-profile", "base profile is unresolved"),
        ("duplicate-profile", "duplicates exact reference"),
        ("authored-catalog", "unsupported key: catalogs"),
    ),
)
def test_invalid_blocker_or_catalog_prerequisites_fail_before_project_explain(
    tmp_path: Path,
    case: str,
    message: str,
) -> None:
    if case == "missing-profile":
        profiles = (_profile("base", "18"),)
        targets = (_target("missing", "18", None),)
        environment_entries = ()
    elif case == "duplicate-profile":
        profiles = (_profile("base", "18"), _profile("base", "18"))
        targets = ()
        environment_entries = ()
    else:
        profiles = ()
        targets = ()
        environment_entries = ("catalogs = []",)
    root = _write_single_project(
        tmp_path,
        slice13._manifest(2, requirements=(UNSUPPORTED_REQUIREMENT,)),
        profiles=profiles,
        targets=targets,
        environment_entries=environment_entries,
        name=case,
    )

    result = _build_project_explain_runtime(root)

    assert result.outcome is ProjectExplainRuntimeOutcome.USAGE_OR_RESOURCE_ERROR
    assert result.envelope.payload is None
    assert result.envelope.diagnostics[0].code == "config_schema"
    assert message in result.envelope.diagnostics[0].message
    assert "blocked" not in result.envelope.diagnostics[0].message.lower()


@pytest.mark.parametrize(
    ("manifest", "collection_count", "requirement_count"),
    (
        (slice13._manifest(1), 0, 0),
        (slice13._manifest(2, requirements=()), 1, 0),
        (
            slice13._manifest(2, requirements=(slice13.EXTENSION_REQUIREMENT,)),
            1,
            1,
        ),
    ),
    ids=("undeclared", "declared-empty", "declared-nonempty"),
)
def test_empty_targets_preserve_declaration_identity_without_synthetic_results(
    tmp_path: Path,
    manifest: bytes,
    collection_count: int,
    requirement_count: int,
) -> None:
    root = _write_single_project(tmp_path, manifest, name=f"empty-{requirement_count}")

    result = _build_project_explain_runtime(root)

    assert result.outcome is ProjectExplainRuntimeOutcome.SUCCESS
    payload = result.envelope.payload
    assert payload is not None
    assert len(payload.package_requirements.requirement_collections) == collection_count
    assert len(payload.package_requirements.requirements) == requirement_count
    assert payload.compatibility.targets == ()
    assert payload.compatibility.package_target_evaluations == ()
    assert len(payload.compatibility.rows) == requirement_count
    assert all(row.cells == () for row in payload.compatibility.rows)
    assert payload.extension_catalog_evidence.contexts == ()
    assert payload.portability.classification is (
        ProjectExplainPortabilityClassification.INDETERMINATE
    )
    assert payload.portability.reason is (
        ProjectExplainPortabilityReason.NO_EVALUATED_TARGETS
    )


@pytest.mark.parametrize(
    ("manifest", "collection_count", "state"),
    (
        (slice13._manifest(1), 0, ProjectExplainEvaluationState.UNDECLARED),
        (
            slice13._manifest(2, requirements=()),
            1,
            ProjectExplainEvaluationState.CHECKED,
        ),
    ),
    ids=("undeclared", "declared-empty"),
)
def test_nonempty_targets_with_zero_requirements_are_portable_and_distinct(
    tmp_path: Path,
    manifest: bytes,
    collection_count: int,
    state: ProjectExplainEvaluationState,
) -> None:
    root = _write_single_project(
        tmp_path,
        manifest,
        profiles=(_profile("base", "18"),),
        targets=(_target("base", "18", None),),
        name=f"zero-requirements-{collection_count}",
    )

    result = _build_project_explain_runtime(root)

    payload = result.envelope.payload
    assert result.outcome is ProjectExplainRuntimeOutcome.SUCCESS
    assert payload is not None
    assert len(payload.package_requirements.requirement_collections) == collection_count
    assert payload.compatibility.rows == ()
    assert tuple(
        evaluation.state
        for evaluation in payload.compatibility.package_target_evaluations
    ) == (state,)
    assert payload.portability.classification is (
        ProjectExplainPortabilityClassification.PORTABLE
    )


def test_schema2_extension_is_valid_empty_and_diagnostic_with_a_target(
    tmp_path: Path,
) -> None:
    manifest = slice13._manifest(
        2,
        requirements=(slice13.EXTENSION_REQUIREMENT,),
    )
    empty = _write_single_project(tmp_path, manifest, name="legacy-empty")
    profiles = (
        _profile("base", "18"),
        _profile(
            "vector",
            "18",
            kind="overlay",
            facts=(
                _fact(
                    "supported",
                    "extension_signature",
                    operation="vector-native-type",
                    dialect="postgresql",
                    extension="vector",
                ),
            ),
        ),
    )
    targeted = _write_single_project(
        tmp_path,
        manifest,
        profiles=profiles,
        targets=(_target("base", "18", "vector"),),
        name="legacy-targeted",
    )

    empty_result = _build_project_explain_runtime(empty)
    targeted_result = _build_project_explain_runtime(targeted)

    assert empty_result.outcome is ProjectExplainRuntimeOutcome.SUCCESS
    assert empty_result.envelope.payload is not None
    assert empty_result.envelope.payload.compatibility.rows[0].cells == ()
    assert targeted_result.outcome is ProjectExplainRuntimeOutcome.DIAGNOSTIC_ERROR
    assert targeted_result.envelope.payload is None
    assert tuple(
        diagnostic.code for diagnostic in targeted_result.envelope.diagnostics
    ) == ("not_evidenced",)


def test_json_and_text_cli_match_runtime_and_are_same_environment_deterministic(
    tmp_path: Path,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    root = _multi_package_multi_target_project(tmp_path, "cli")
    runtime = _build_project_explain_runtime(root)
    expected_json = serialize_project_explain_json_document(runtime.envelope)
    expected_text = render_project_explain_text(runtime.envelope).encode()

    assert cli.main(["explain", "--project", str(root), "--format", "json"]) == 0
    first_json = capsysbinary.readouterr()
    assert cli.main(["explain", "--project", str(root), "--format", "json"]) == 0
    second_json = capsysbinary.readouterr()
    assert first_json == second_json
    assert first_json.out == expected_json and first_json.err == b""
    document = cast(dict[str, object], json.loads(first_json.out))
    assert tuple(document) == ("format", "ok", "diagnostics", "payload")
    assert document["format"] == "pietto.project-explain.v1"
    assert {"outcome", "exit_code"}.isdisjoint(document)

    assert cli.main(["explain", "--project", str(root)]) == 0
    first_text = capsysbinary.readouterr()
    assert cli.main(["explain", "--project", str(root), "--format", "text"]) == 0
    second_text = capsysbinary.readouterr()
    assert first_text == second_text
    assert first_text.out == expected_text and first_text.err == b""
    for marker in (
        b"Packages (2)",
        b"Targets (2)",
        b"status=unsupported",
        b"status=absent",
        b"status=conflict",
        b"selection=undeclared",
        b"project: not_portable",
    ):
        assert marker in first_text.out
    assert b" object at 0x" not in first_text.out


@pytest.mark.parametrize(
    ("kind", "expected_outcome", "expected_exit"),
    (
        ("diagnostic", ProjectExplainRuntimeOutcome.DIAGNOSTIC_ERROR, 1),
        ("resource", ProjectExplainRuntimeOutcome.USAGE_OR_RESOURCE_ERROR, 2),
    ),
)
def test_cli_failure_outcomes_preserve_exact_failure_envelopes(
    tmp_path: Path,
    capsysbinary: pytest.CaptureFixture[bytes],
    kind: str,
    expected_outcome: ProjectExplainRuntimeOutcome,
    expected_exit: int,
) -> None:
    if kind == "diagnostic":
        profiles = (
            _profile("base", "18"),
            _profile("vector", "18", kind="overlay"),
        )
        root = _write_single_project(
            tmp_path,
            slice13._manifest(
                2,
                requirements=(slice13.EXTENSION_REQUIREMENT,),
            ),
            profiles=profiles,
            targets=(_target("base", "18", "vector"),),
            name="failure",
        )
    else:
        root = tmp_path / "missing"
    runtime = _build_project_explain_runtime(root)
    assert runtime.outcome is expected_outcome

    assert (
        cli.main(["explain", "--project", str(root), "--format", "json"])
        == expected_exit
    )
    captured = capsysbinary.readouterr()
    assert captured.out == serialize_project_explain_json_document(runtime.envelope)
    assert captured.err == b""
    document = cast(dict[str, object], json.loads(captured.out))
    assert document["ok"] is False
    assert document["payload"] is None
    assert cast(list[object], document["diagnostics"])


def test_spec_records_reachability_ledger_boundaries_and_future_readiness() -> None:
    document = SPEC.read_text(encoding="utf-8")
    normalized = " ".join(document.split())
    for required in (
        "PRODUCTION_REACHABLE_E2E",
        "STRUCTURALLY_UNREACHABLE_CURRENT_RUNTIME",
        "INVALID_INPUT_REJECTED_BEFORE_PROJECT_EXPLAIN",
        "compatibility `BLOCKED`",
        "catalog `AMBIGUOUS`",
        "catalog `CONFLICT`",
        "PackageCapabilityRequirementsBlocked",
        "Project and package authored inputs cannot append or replace compiler catalog availability",
        "Availability is not selection, and selection is not extension installation",
        "Multi-source/generated catalog expansion remains later Phase 69 readiness",
        "PHASE58_SLICE15_SELF_OWNED_OPEN = 0",
    ):
        assert required in normalized
