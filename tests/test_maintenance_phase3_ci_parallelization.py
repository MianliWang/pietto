from __future__ import annotations

import re
from pathlib import Path
import subprocess
import tomllib
from test_phase54_local_import_module_export_foundation_scope_lock import (
    phase54_slice5_gate2_manifest_is_active as _slice5_gate2,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = (
    REPO_ROOT / "docs/plan/maintenance-phase-3-validation-pipeline-performance.md"
)
SPEC_PATH = REPO_ROOT / "docs/spec/maintenance-phase3-ci-pytest-parallelization-v1.md"
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/ci.yml"
VALIDATE_PATH = REPO_ROOT / "scripts/validate.py"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
UV_LOCK_PATH = REPO_ROOT / "uv.lock"
CHECK_GENERATED_PATH = REPO_ROOT / "scripts/check_generated.py"
CHECK_GOLDENS_PATH = REPO_ROOT / "scripts/check_goldens.py"
PACKAGE_SMOKE_PATH = REPO_ROOT / "scripts/package_smoke.py"

ACCELERATED_VALIDATE_COMMAND = (
    "uv run python scripts/validate.py --timings --pytest-workers auto "
    "--pytest-dist loadfile --pytest-maxprocesses 4"
)
SERIAL_POST_VALIDATE_COMMANDS = (
    "uv run python scripts/check_generated.py",
    "uv run python scripts/check_goldens.py",
    "uv run python scripts/package_smoke.py",
)
ALLOWED_SLICE6_GATE2_PATHS = {
    ".github/workflows/ci.yml",
    "docs/plan/maintenance-phase-3-validation-pipeline-performance.md",
    "docs/spec/maintenance-phase3-ci-pytest-parallelization-v1.md",
    "tests/test_maintenance_phase3_ci_parallelization.py",
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase12_completion_audit.py",
    "tests/_maintenance_surface_helpers.py",
}
UNCHANGED_PATHS = (
    "scripts/validate.py",
    "pyproject.toml",
    "uv.lock",
    "scripts/check_generated.py",
    "scripts/check_goldens.py",
    "scripts/package_smoke.py",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def _docs() -> str:
    return " ".join(_normalized(path) for path in (PLAN_PATH, SPEC_PATH))


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


def _dirty_paths() -> set[str]:
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


def _direct_run_commands(workflow: str) -> tuple[str, ...]:
    return tuple(
        command
        for command in re.findall(r"(?m)^        run: (.+)$", workflow)
        if command != "|"
    )


def test_plan_and_spec_exist_and_name_slice6_ci_opt_in() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()

    docs = _docs()
    for required in (
        "Maintenance Phase 3",
        "CI Opt-in Pytest Parallelization",
        "conservative CI",
        "developer validation infrastructure",
    ):
        assert required in docs, required


def test_ci_authoritative_validation_uses_accelerated_validate_command() -> None:
    workflow = _read(WORKFLOW_PATH)
    docs = _docs()

    assert workflow.count(ACCELERATED_VALIDATE_COMMAND) == 1
    assert ACCELERATED_VALIDATE_COMMAND in docs
    assert "run: uv run python scripts/validate.py\n" not in workflow
    assert "addopts" not in _read(PYPROJECT_PATH)


def test_ci_preserves_serial_post_validate_steps() -> None:
    workflow = _read(WORKFLOW_PATH)
    commands = _direct_run_commands(workflow)

    assert commands == (
        "uv sync --locked",
        ACCELERATED_VALIDATE_COMMAND,
        *SERIAL_POST_VALIDATE_COMMANDS,
    )
    for command in SERIAL_POST_VALIDATE_COMMANDS:
        assert workflow.count(command) == 1
        assert command in _docs()


def test_ci_preserves_matrix_single_job_and_cache_policy() -> None:
    workflow = _read(WORKFLOW_PATH)
    job_ids = tuple(
        match.group(1)
        for match in re.finditer(r"(?m)^  ([A-Za-z0-9_-]+):\n    name:", workflow)
    )

    assert job_ids == ("validation",)
    assert re.findall(r'(?m)^          - "(3\.\d+)"$', workflow) == [
        "3.12",
        "3.13",
    ]
    assert "enable-cache: false" in workflow
    assert (
        'echo "UV_PROJECT_ENVIRONMENT=$RUNNER_TEMP/pietto-venv" >> "$GITHUB_ENV"'
        in workflow
    )
    assert 'echo "UV_CACHE_DIR=$RUNNER_TEMP/uv-cache" >> "$GITHUB_ENV"' in workflow
    assert "needs:" not in workflow


def test_plan_and_spec_lock_ci_safety_fallback_and_non_goals() -> None:
    docs = _docs()

    for required in (
        "Local default",
        "remains serial",
        "--pytest-workers off",
        "--pytest-maxprocesses 4",
        "--pytest-dist loadfile",
        "No job-level CI split",
        "enable-cache: false",
        "generated checks",
        "golden checks",
        "package smoke",
        "not parallelized",
        "scripts/validate.py",
        "pyproject.toml",
        "uv.lock",
        "package version",
        "release",
        "publish",
        "upload",
        "signing",
        "attestation",
    ):
        assert required in docs, required


def test_unchanged_scripts_dependencies_and_lockfile_have_no_diff() -> None:
    for path in (
        VALIDATE_PATH,
        PYPROJECT_PATH,
        UV_LOCK_PATH,
        CHECK_GENERATED_PATH,
        CHECK_GOLDENS_PATH,
        PACKAGE_SMOKE_PATH,
    ):
        assert path.is_file()

    for relative_path in UNCHANGED_PATHS:
        assert _git_output(["diff", "--", relative_path]) == "", relative_path


def test_package_version_and_pytest_addopts_are_unchanged() -> None:
    pyproject = _read(PYPROJECT_PATH)
    pyproject_data = tomllib.loads(pyproject)

    assert pyproject_data["project"]["version"] == "0.1.0"
    assert "addopts" not in pyproject


def test_ci_has_no_release_publication_or_attestation_surface() -> None:
    workflow = _read(WORKFLOW_PATH).lower()

    for forbidden in (
        "contents: write",
        "write-all",
        "pull-requests:",
        "id-token:",
        "secrets.",
        "pypi-token",
        "twine",
        "trusted publishing",
        "upload-artifact",
        "sigstore",
        "attestation",
    ):
        assert forbidden not in workflow, forbidden


def test_dirty_paths_are_clean_or_exact_slice6_allowlist() -> None:
    dirty_paths = _dirty_paths()
    assert (dirty_paths in (set(), ALLOWED_SLICE6_GATE2_PATHS)) or _slice5_gate2()
