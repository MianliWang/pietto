from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = (
    REPO_ROOT / "docs/plan/maintenance-phase-3-validation-pipeline-performance.md"
)
SPEC_PATH = REPO_ROOT / "docs/spec/maintenance-phase3-developer-workflow-v1.md"
README_PATH = REPO_ROOT / "README.md"
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/ci.yml"
VALIDATE_PATH = REPO_ROOT / "scripts/validate.py"
CHECK_GENERATED_PATH = REPO_ROOT / "scripts/check_generated.py"
CHECK_GOLDENS_PATH = REPO_ROOT / "scripts/check_goldens.py"
PACKAGE_SMOKE_PATH = REPO_ROOT / "scripts/package_smoke.py"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
UV_LOCK_PATH = REPO_ROOT / "uv.lock"

DAILY_FOCUSED_COMMAND = "uv run pytest tests/test_current_slice.py"
SERIAL_FALLBACK_COMMANDS = (
    "uv run python scripts/validate.py --pytest-workers off --timings",
    "uv run python scripts/validate.py --timings",
)
LOCAL_FAST_COMMANDS = (
    "uv run pytest -n auto --dist=loadfile",
    "uv run python scripts/validate.py --timings --pytest-workers auto "
    "--pytest-dist loadfile --pytest-maxprocesses 4",
)
FULL_RELEASE_COMMANDS = (
    "uv run python scripts/check_generated.py",
    "uv run python scripts/check_goldens.py",
    "uv run python scripts/package_smoke.py",
)
UNCHANGED_PATHS = (
    "README.md",
    "AGENTS.md",
    ".github/workflows/ci.yml",
    "scripts/validate.py",
    "scripts/check_generated.py",
    "scripts/check_goldens.py",
    "scripts/package_smoke.py",
    "pyproject.toml",
    "uv.lock",
)
ALLOWED_SLICE8_GATE2_PATHS = {
    "docs/plan/maintenance-phase-3-validation-pipeline-performance.md",
    "docs/spec/maintenance-phase3-developer-workflow-v1.md",
    "tests/test_maintenance_phase3_developer_workflow.py",
}


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


def test_plan_and_spec_exist_and_name_developer_workflow_docs() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()

    for path in (PLAN_PATH, SPEC_PATH):
        text = _normalized(path)
        assert "Maintenance Phase 3" in text
        assert "Developer Workflow Docs" in text


def test_plan_and_spec_define_validation_profiles() -> None:
    for path in (PLAN_PATH, SPEC_PATH):
        text = _normalized(path)
        for required in ("focused-dirty", "local-fast", "full-release"):
            assert required in text, required


def test_plan_and_spec_lock_daily_serial_fast_and_release_commands() -> None:
    docs = _docs()

    assert DAILY_FOCUSED_COMMAND in docs
    for command in (
        *SERIAL_FALLBACK_COMMANDS,
        *LOCAL_FAST_COMMANDS,
        *FULL_RELEASE_COMMANDS,
    ):
        assert command in docs, command


def test_ci_behavior_and_serial_post_validate_checks_are_documented() -> None:
    docs = _docs()

    for required in (
        "CI uses pytest worker flags only through `scripts/validate.py`",
        "generated/golden/package-smoke as separate serial post-validate",
        "No job-level CI split yet",
        "setup-uv cache policy remains unchanged",
        "Local default remains serial",
        *LOCAL_FAST_COMMANDS[1:],
        *FULL_RELEASE_COMMANDS,
    ):
        assert required in docs, required


def test_package_smoke_caveats_are_documented() -> None:
    docs = _docs()

    for required in (
        "package/network/build-sensitive",
        "builds/installs in temporary directories",
        "validates installed CLI behavior",
        "remains serial",
        "not a release, publish, upload, signing, or attestation operation",
        "not routine dirty Gate 2 validation unless explicitly approved",
    ):
        assert required in docs, required


def test_when_not_to_use_parallel_mode_is_documented() -> None:
    docs = _docs()

    for required in (
        "dirty-path guard suites outside the current allowlist",
        "hash/private-surface locks unless reviewed for the dirty tree",
        "generated/golden/package-smoke audit tests",
        "package build, temporary venv, and installed CLI smoke tests",
        "fixed output paths",
        "cwd/env mutation",
        "subprocesses",
        "shared caches",
        "random",
        "time.sleep",
        "broad repository scans",
        "initial diagnosis of flakes/failures",
    ):
        assert required in docs, required


def test_deferred_tuning_decisions_are_documented() -> None:
    docs = _docs()

    for required in (
        "worker cap above 4",
        "Distribution mode change away from loadfile",
        "Pyright/pytest concurrent execution",
        "Hidden concurrency inside `scripts/validate.py`",
        "Job-level CI split",
        "Generated/golden/package-smoke parallelization",
    ):
        assert required in docs, required


def test_forbidden_documentation_workflow_scripts_and_lockfiles_have_no_diff() -> None:
    for path in (
        README_PATH,
        AGENTS_PATH,
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


def test_dirty_paths_are_clean_or_exact_slice8_allowlist() -> None:
    dirty_paths = _dirty_paths()
    assert dirty_paths in (set(), ALLOWED_SLICE8_GATE2_PATHS)
