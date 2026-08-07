from __future__ import annotations

import re
import subprocess
import tomllib
from pathlib import Path
from _phase54_active_gate2_manifest import (
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = (
    REPO_ROOT / "docs/plan/maintenance-phase-3-validation-pipeline-performance.md"
)
SPEC_PATH = (
    REPO_ROOT / "docs/spec/maintenance-phase3-non-pytest-validation-optimization-v1.md"
)
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/ci.yml"
VALIDATE_PATH = REPO_ROOT / "scripts/validate.py"
CHECK_GENERATED_PATH = REPO_ROOT / "scripts/check_generated.py"
CHECK_GOLDENS_PATH = REPO_ROOT / "scripts/check_goldens.py"
PACKAGE_SMOKE_PATH = REPO_ROOT / "scripts/package_smoke.py"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
UV_LOCK_PATH = REPO_ROOT / "uv.lock"

SLICE6_COMMIT = "41a3ec38ddc30fbdcb3348253c976e36dc7be7b9"
SLICE6_CI_RUN = "29009063082"
SLICE7_NAME = "Ruff / Pyright / Generated / Golden / Package Smoke Optimization"
AUTHORITATIVE_VALIDATE_COMMAND = (
    "uv run python scripts/validate.py --timings --pytest-workers auto "
    "--pytest-dist loadfile --pytest-maxprocesses 4"
)
SERIAL_POST_VALIDATE_COMMANDS = (
    "uv run python scripts/check_generated.py",
    "uv run python scripts/check_goldens.py",
    "uv run python scripts/package_smoke.py",
)
ALLOWED_SLICE7_GATE2_PATHS = {
    "docs/plan/maintenance-phase-3-validation-pipeline-performance.md",
    "docs/spec/maintenance-phase3-non-pytest-validation-optimization-v1.md",
    "tests/test_maintenance_phase3_non_pytest_validation_optimization.py",
}
UNCHANGED_PATHS = (
    ".github/workflows/ci.yml",
    "scripts/validate.py",
    "scripts/check_generated.py",
    "scripts/check_goldens.py",
    "scripts/package_smoke.py",
    "pyproject.toml",
    "uv.lock",
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


def test_plan_and_spec_exist_and_name_slice7() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()

    docs = _docs()
    for required in (
        "Maintenance Phase 3",
        SLICE7_NAME,
        "non-pytest validation optimization",
        "developer validation infrastructure",
        SLICE6_CI_RUN,
        SLICE6_COMMIT,
    ):
        assert required in docs, required


def test_plan_and_spec_record_slice6_ci_timing_evidence() -> None:
    docs = _docs()

    for timing in (
        "92.091s",
        "74.977s",
        "65.534s",
        "50.362s",
        "10.826s",
        "15.380s",
        "9.116s",
        "15.136s",
        "0.192s",
        "0.220s",
        "6s",
        "8s",
    ):
        assert timing in docs, timing

    for required in (
        "Python 3.12",
        "Python 3.13",
        "generated check",
        "golden check",
        "package smoke",
    ):
        assert required in docs, required


def test_plan_and_spec_lock_non_pytest_optimization_decisions() -> None:
    docs = _docs()

    for required in (
        "ruff remains unchanged",
        "pyright remains unchanged for now",
        "generated/golden remain serial and unchanged",
        "package smoke remains serial and unchanged",
        "setup-uv cache policy remains unchanged",
        "job-level CI split remains deferred",
        "more aggressive pytest worker tuning remains deferred",
        "Pyright/pytest concurrent execution remains deferred",
        "hidden concurrency inside scripts/validate.py is rejected for now",
        "no behavior/workflow/script/dependency change in Slice 7",
    ):
        assert required in docs, required


def test_forbidden_surfaces_have_no_diff() -> None:
    for path in (
        WORKFLOW_PATH,
        VALIDATE_PATH,
        CHECK_GENERATED_PATH,
        CHECK_GOLDENS_PATH,
        PACKAGE_SMOKE_PATH,
        PYPROJECT_PATH,
        UV_LOCK_PATH,
    ):
        assert path.is_file()

    for relative_path in UNCHANGED_PATHS:
        assert _git_output(["diff", "--", relative_path]) == "", relative_path


def test_package_version_and_global_pytest_addopts_are_unchanged() -> None:
    pyproject = _read(PYPROJECT_PATH)
    pyproject_data = tomllib.loads(pyproject)

    assert pyproject_data["project"]["version"] == "0.1.0"
    assert "addopts" not in pyproject


def test_ci_workflow_commands_cache_and_worker_strategy_are_unchanged() -> None:
    workflow = _read(WORKFLOW_PATH)
    commands = _direct_run_commands(workflow)

    assert commands == (
        "uv sync --locked",
        AUTHORITATIVE_VALIDATE_COMMAND,
        *SERIAL_POST_VALIDATE_COMMANDS,
    )
    assert "enable-cache: false" in workflow
    assert (
        'echo "UV_PROJECT_ENVIRONMENT=$RUNNER_TEMP/pietto-venv" >> "$GITHUB_ENV"'
        in workflow
    )
    assert 'echo "UV_CACHE_DIR=$RUNNER_TEMP/uv-cache" >> "$GITHUB_ENV"' in workflow
    assert "--pytest-maxprocesses 4" in workflow
    assert "--pytest-dist loadfile" in workflow
    assert "--pytest-maxprocesses 8" not in workflow
    assert "--dist=loadscope" not in workflow
    assert "needs:" not in workflow


def test_dirty_paths_are_clean_or_exact_slice7_allowlist() -> None:
    dirty_paths = _dirty_paths()
    assert (
        dirty_paths in (set(), ALLOWED_SLICE7_GATE2_PATHS)
    ) or _phase54_active_gate2_is_active()
