from __future__ import annotations

from pathlib import Path
import subprocess
import tomllib

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = (
    REPO_ROOT / "docs/plan/maintenance-phase-3-validation-pipeline-performance.md"
)
SPEC_PATH = (
    REPO_ROOT / "docs/spec/maintenance-phase3-validation-acceleration-scope-lock-v1.md"
)
VALIDATE_PATH = REPO_ROOT / "scripts/validate.py"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/ci.yml"

ALLOWED_SLICE2_GATE2_PATHS = {
    "docs/plan/maintenance-phase-3-validation-pipeline-performance.md",
    "docs/spec/maintenance-phase3-validation-acceleration-scope-lock-v1.md",
    "tests/test_maintenance_phase3_validation_acceleration_scope_lock.py",
}

FORBIDDEN_DIFF_PATHS = (
    "src",
    "grammar",
    ".github/workflows",
    "pyproject.toml",
    "uv.lock",
    "scripts/validate.py",
    "scripts/check_generated.py",
    "scripts/check_goldens.py",
    "scripts/package_smoke.py",
    "README.md",
    "AGENTS.md",
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
    return result.stdout.strip()


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


def test_plan_and_spec_exist_and_name_the_slice() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()

    docs = _docs()
    for required in (
        "Maintenance Phase 3",
        "Validation Pipeline Performance & Workflow Acceleration",
        "Acceleration Scope Lock & Validation Profile Contract",
        "docs/spec/tests-only",
        "reduce local and CI validation wall-clock time",
        "serial debug fallback",
        "release safety",
    ):
        assert required in docs, required


def test_slice1_runtime_audit_facts_are_locked() -> None:
    docs = _docs()
    for required in (
        "5190 passed",
        "25.93s",
        "37.15s",
        "10.32s test pyright",
        "88s CI wall time",
        "65-70s CI authoritative validation",
        "pytest-xdist",
        "is absent",
        "package smoke network/cache-sensitive",
        "0.05s",
        "0.13s",
        "3.73s",
        "0.68s",
        "0.06s",
        "10.33s",
    ):
        assert required in docs, required


def test_validation_profiles_and_route_are_locked() -> None:
    docs = _docs()

    for profile in ("focused-dirty", "local-fast", "full-release"):
        assert profile in docs

    for route_item in (
        "Codex Read-only Runtime Audit Report",
        "Acceleration Scope Lock & Validation Profile Contract",
        "Add `scripts/validate.py --timings`",
        "Adaptive Pytest Multiprocessing",
        "Parallel Safety Audit & Repairs",
        "CI Opt-in Pytest Parallelization",
        "Ruff / Pyright / Generated / Golden / Package Smoke Optimization",
        "Developer Workflow Docs",
        "Completion Audit / Status Lock",
    ):
        assert route_item in docs, route_item


def test_timing_worker_and_serial_contracts_are_locked() -> None:
    docs = _docs()
    timing_index = docs.index("--timings")
    worker_index = docs.index("pytest worker flags")

    assert timing_index < worker_index
    for required in (
        "Serial validation remains the default",
        "serial fallback must remain available",
        "Add `--timings` before pytest worker flags",
        "global pytest addopts",
        "must not set global pytest addopts for `-n auto`",
        "--dist=loadfile",
        "4 workers",
        "No job-level CI split",
        "uv cache changes should be audit-driven",
    ):
        assert required in docs, required


def test_serial_initial_checks_and_non_goals_are_locked() -> None:
    docs = _docs()

    for required in (
        "scripts/check_generated.py",
        "scripts/check_goldens.py",
        "hash/private-surface tests",
        "dirty-path guards",
        "scripts/package_smoke.py",
        "Package smoke is network/cache-sensitive and remains serial initially",
        "no `pytest-xdist` addition",
        "Slice 2 does not implement `--timings`",
        "pytest worker flags",
        "CI acceleration",
        "release, package, tag, signing, or attestation behavior",
    ):
        assert required in docs, required


def test_validate_py_has_no_diff_and_no_new_acceleration_flags() -> None:
    assert _git_output(["diff", "--", "scripts/validate.py"]) == ""

    validate_py = _read(VALIDATE_PATH)
    for forbidden in (
        "--timings",
        "--pytest-workers",
        "--pytest-dist",
        "--pytest-maxprocesses",
    ):
        assert forbidden not in validate_py, forbidden


def test_package_metadata_lockfile_and_xdist_remain_unchanged() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]
    pyproject = _read(PYPROJECT_PATH)

    assert project["version"] == "0.1.0"
    assert "pytest-xdist" not in pyproject
    assert _git_output(["diff", "--", "pyproject.toml"]) == ""
    assert _git_output(["diff", "--", "uv.lock"]) == ""


def test_ci_workflow_and_forbidden_public_surfaces_have_no_diff() -> None:
    assert WORKFLOW_PATH.is_file()
    assert _git_output(["diff", "--", ".github/workflows/ci.yml"]) == ""

    for relative_path in FORBIDDEN_DIFF_PATHS:
        assert _git_output(["diff", "--", relative_path]) == "", relative_path


def test_dirty_paths_are_clean_or_exact_slice2_allowlist() -> None:
    assert _dirty_paths() in (set(), ALLOWED_SLICE2_GATE2_PATHS)
