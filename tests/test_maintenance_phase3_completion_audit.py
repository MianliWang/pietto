from __future__ import annotations

import re
import subprocess
import tomllib
from pathlib import Path
from typing import cast
from test_phase54_local_import_module_export_foundation_scope_lock import (
    phase54_slice5_gate2_manifest_is_active as _slice5_gate2,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = (
    REPO_ROOT / "docs/plan/maintenance-phase-3-validation-pipeline-performance.md"
)
SPEC_PATH = REPO_ROOT / "docs/spec/maintenance-phase3-completion-audit-v1.md"
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/ci.yml"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
UV_LOCK_PATH = REPO_ROOT / "uv.lock"

SLICE8_COMMIT = "12d834a41300044f4017b1f9853093cbe8d91764"
SLICE8_CI_RUN = "29050956461"
CI_VALIDATE_COMMAND = (
    "uv run python scripts/validate.py --timings --pytest-workers auto "
    "--pytest-dist loadfile --pytest-maxprocesses 4"
)
SERIAL_POST_VALIDATE_COMMANDS = (
    "uv run python scripts/check_generated.py",
    "uv run python scripts/check_goldens.py",
    "uv run python scripts/package_smoke.py",
)

SLICE_INVENTORY = (
    "Slice 1: Codex Read-only Runtime Audit Report",
    "Slice 2: Acceleration Scope Lock & Validation Profile Contract",
    "Slice 3: Add `scripts/validate.py --timings`",
    "Slice 4: Adaptive Pytest Multiprocessing",
    "Slice 5: Parallel Safety Audit & Repairs",
    "Slice 6: CI Opt-in Pytest Parallelization",
    "Slice 7: Ruff / Pyright / Generated / Golden / Package Smoke Optimization",
    "Slice 8: Developer Workflow Docs",
    "Slice 9: Completion Audit / Status Lock",
)

PHASE_SPEC_PATHS = (
    "docs/spec/maintenance-phase3-validation-acceleration-scope-lock-v1.md",
    "docs/spec/maintenance-phase3-validation-timings-v1.md",
    "docs/spec/maintenance-phase3-pytest-workers-v1.md",
    "docs/spec/maintenance-phase3-parallel-safety-v1.md",
    "docs/spec/maintenance-phase3-ci-pytest-parallelization-v1.md",
    "docs/spec/maintenance-phase3-non-pytest-validation-optimization-v1.md",
    "docs/spec/maintenance-phase3-developer-workflow-v1.md",
    "docs/spec/maintenance-phase3-completion-audit-v1.md",
)

ALLOWED_SLICE9_GATE2_PATHS = {
    "docs/plan/maintenance-phase-3-validation-pipeline-performance.md",
    "docs/spec/maintenance-phase3-completion-audit-v1.md",
    "tests/test_maintenance_phase3_completion_audit.py",
}

FORBIDDEN_DIFF_PATHS = (
    "README.md",
    "AGENTS.md",
    ".github/workflows/ci.yml",
    "scripts/validate.py",
    "scripts/check_generated.py",
    "scripts/check_goldens.py",
    "scripts/package_smoke.py",
    "pyproject.toml",
    "uv.lock",
    "src",
    "grammar",
    "tests/fixtures",
    "docs/spec/pietto-v0.9.md",
    "docs/spec/pietto-roadmap-phase45-60-v1.md",
)

POSITIVE_GATE3_PRECLAIMS = (
    "Slice 9 Gate 3 natural CI succeeded",
    "Gate 3 natural CI has already succeeded",
    "Maintenance Phase 3 is complete during Gate 2",
    "Gate 2 marks Maintenance Phase 3 complete",
)

POSITIVE_RELEASE_CLAIMS = (
    "tag created",
    "release created",
    "package release occurred",
    "published package",
    "uploaded package",
    "signing completed",
    "attestation completed",
    "release operation occurred",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def _documents() -> tuple[str, str]:
    return (_normalized(PLAN_PATH), _normalized(SPEC_PATH))


def _git_output(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    return result.stdout.rstrip()


def _git_status_paths() -> set[str]:
    output = _git_output(["status", "--porcelain", "--untracked-files=all"])
    paths: set[str] = set()
    for line in output.splitlines():
        if not line:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", maxsplit=1)[1]
        paths.add(path)
    return paths


def test_plan_spec_identity_slice_inventory_and_spec_inventory_are_locked() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()

    for document in _documents():
        assert "Maintenance Phase 3" in document
        assert "Completion Audit / Status Lock" in document
        for slice_entry in SLICE_INVENTORY:
            assert slice_entry in document, slice_entry
        for relative_path in PHASE_SPEC_PATHS:
            assert relative_path in document, relative_path
            assert (REPO_ROOT / relative_path).is_file(), relative_path


def test_slice8_baseline_and_gate3_aware_completion_are_locked() -> None:
    completion_condition = (
        "Maintenance Phase 3 can be marked complete only after Slice 9 Gate 3 "
        "records the final commit, normal push, and successful natural CI with "
        "exact `headSha` match"
    )

    for document in _documents():
        for required in (
            SLICE8_COMMIT,
            SLICE8_CI_RUN,
            "Add Maintenance Phase 3 developer workflow docs",
            "workflow `CI`",
            "event `push`",
            "completed / success",
            "headSha",
            completion_condition,
            "Gate 2 does not mark the phase complete by itself",
        ):
            assert required in document, required
        assert (
            "does not claim that Slice 9 Gate 3 has already succeeded" in document
            or "does not preclaim Slice 9 Gate 3 natural CI success" in document
        )
        for forbidden in POSITIVE_GATE3_PRECLAIMS:
            assert forbidden not in document, forbidden


def test_delivered_features_and_validation_profiles_are_locked() -> None:
    for document in _documents():
        for required in (
            "read-only runtime audit",
            "acceleration scope lock",
            "focused-dirty",
            "local-fast",
            "full-release",
            "scripts/validate.py --timings",
            "opt-in pytest workers",
            "CI opt-in pytest parallelization",
            "parallel safety",
            "non-pytest optimization decisions",
            "developer workflow",
            "completion audit/status lock only",
        ):
            assert required in document, required


def test_exact_worker_dependency_and_package_surface_is_locked() -> None:
    for document in _documents():
        for required in (
            "local no-worker default remains serial",
            "--pytest-workers off",
            "--pytest-workers auto",
            "--pytest-workers logical",
            "--pytest-workers <positive integer>",
            "--pytest-dist loadfile|loadscope",
            "--pytest-maxprocesses <positive integer>",
            "pytest-xdist` remains a dev-only dependency",
            "no global pytest addopts",
            "Package version remains `0.1.0`",
        ):
            assert required in document, required

    pyproject = tomllib.loads(_read(PYPROJECT_PATH))
    project = cast(dict[str, object], pyproject["project"])
    dependency_groups = cast(dict[str, object], pyproject["dependency-groups"])
    dev_dependencies = cast(list[str], dependency_groups["dev"])
    runtime_dependencies = cast(list[str], project["dependencies"])

    assert project["version"] == "0.1.0"
    assert "pytest-xdist>=3.8.0" in dev_dependencies
    assert all("pytest-xdist" not in item for item in runtime_dependencies)
    assert "addopts" not in _read(PYPROJECT_PATH)
    assert 'name = "pytest-xdist"' in _read(UV_LOCK_PATH)


def test_exact_ci_command_serial_steps_matrix_and_cache_are_locked() -> None:
    workflow = _read(WORKFLOW_PATH)

    for document in _documents():
        assert CI_VALIDATE_COMMAND in document
        for command in SERIAL_POST_VALIDATE_COMMANDS:
            assert command in document, command
        for required in (
            "separate serial post-validate CI steps",
            "one validation job per Python 3.12/3.13 matrix entry",
            "enable-cache: false",
            "UV_PROJECT_ENVIRONMENT",
            "UV_CACHE_DIR",
        ):
            assert required in document, required

    assert workflow.count(CI_VALIDATE_COMMAND) == 1
    for command in SERIAL_POST_VALIDATE_COMMANDS:
        assert workflow.count(command) == 1
    assert re.findall(r"(?m)^  ([A-Za-z0-9_-]+):\n    name:", workflow) == [
        "validation"
    ]
    assert re.findall(r'(?m)^          - "(3\.\d+)"$', workflow) == [
        "3.12",
        "3.13",
    ]
    assert "enable-cache: false" in workflow
    assert "UV_PROJECT_ENVIRONMENT=$RUNNER_TEMP/pietto-venv" in workflow
    assert "UV_CACHE_DIR=$RUNNER_TEMP/uv-cache" in workflow


def test_deferred_non_goals_and_release_boundaries_are_locked() -> None:
    for document in _documents():
        for required in (
            "no job-level CI split",
            "no Pyright/pytest concurrent execution",
            "no hidden concurrency inside `scripts/validate.py`",
            "no generated/golden/package-smoke parallelization",
            "no setup-uv cache policy change",
            "no package smoke weakening or relocation",
            "no CI worker cap increase above 4",
            "no CI distribution change away from `loadfile`",
            "benchmark-driven and separately approved",
            "no tag, release, publish, upload, signing, or attestation",
            "Package smoke remains validation only and is not a release operation",
            "no validation behavior",
            "source/compiler",
            "public API/schema",
            "runtime",
            "database",
        ):
            assert required in document, required
        lowered = document.lower()
        for forbidden in POSITIVE_RELEASE_CLAIMS:
            assert forbidden not in lowered, forbidden


def test_gate2_allowlist_and_forbidden_diffs_are_locked() -> None:
    for document in _documents():
        for relative_path in sorted(ALLOWED_SLICE9_GATE2_PATHS):
            assert relative_path in document, relative_path
        for required in (
            "No other file is approved in Slice 9 Gate 2",
            "focused only",
            "full pytest",
            "full `scripts/validate.py`",
            "generated checks",
            "golden checks",
            "package smoke",
            "package builds",
            "timing benchmarks",
            "CI",
        ):
            assert required in document, required

    for relative_path in FORBIDDEN_DIFF_PATHS:
        assert (_git_output(["diff", "--", relative_path]) == "") or _slice5_gate2(), (
            relative_path
        )


def test_dirty_paths_are_clean_or_subset_of_slice9_allowlist() -> None:
    assert (_git_status_paths().issubset(ALLOWED_SLICE9_GATE2_PATHS)) or _slice5_gate2()
