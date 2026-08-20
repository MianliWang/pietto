from __future__ import annotations

from pathlib import Path
import tomllib

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = (
    REPO_ROOT / "docs/plan/maintenance-phase-3-validation-pipeline-performance.md"
)
SPEC_PATH = (
    REPO_ROOT / "docs/spec/maintenance-phase3-validation-acceleration-scope-lock-v1.md"
)
TIMING_SPEC_PATH = REPO_ROOT / "docs/spec/maintenance-phase3-validation-timings-v1.md"
WORKER_SPEC_PATH = REPO_ROOT / "docs/spec/maintenance-phase3-pytest-workers-v1.md"
VALIDATE_PATH = REPO_ROOT / "scripts/validate.py"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
UV_LOCK_PATH = REPO_ROOT / "uv.lock"
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/ci.yml"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def _docs() -> str:
    return " ".join(
        _normalized(path)
        for path in (PLAN_PATH, SPEC_PATH, TIMING_SPEC_PATH, WORKER_SPEC_PATH)
    )


def test_plan_and_spec_exist_and_name_the_slice() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()
    assert TIMING_SPEC_PATH.is_file()
    assert WORKER_SPEC_PATH.is_file()

    docs = _docs()
    for required in (
        "Maintenance Phase 3",
        "Validation Pipeline Performance & Workflow Acceleration",
        "Acceleration Scope Lock & Validation Profile Contract",
        "Validation Timings Contract",
        "Pytest Workers Contract",
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
        "--pytest-workers off",
        "--pytest-workers auto",
        "--pytest-workers logical",
        "--pytest-maxprocesses",
        "--pytest-dist loadscope",
        "default with no worker flag remains serial",
        "explicit serial fallback",
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
        "CI opt-in pytest parallelization remains deferred to Slice 6",
        "Generated, golden, hash/private-surface, dirty-path, and package-smoke checks remain serial initially",
    ):
        assert required in docs, required


def test_validate_py_has_timings_and_opt_in_worker_flags() -> None:
    validate_py = _read(VALIDATE_PATH)
    for required in (
        "--timings",
        "--pytest-workers",
        "--pytest-dist",
        "--pytest-maxprocesses",
        "PYTEST_DIST_CHOICES",
        "os.cpu_count",
        "--dist={dist_mode}",
        "--maxprocesses",
        "time.perf_counter",
        "[validate] total completed in",
        "[validate] {name} completed in",
    ):
        assert required in validate_py, required

    assert "check_generated.py" not in validate_py
    assert "check_goldens.py" not in validate_py
    assert "package_smoke.py" not in validate_py


def test_package_metadata_lockfile_and_xdist_dev_dependency_are_locked() -> None:
    pyproject = _read(PYPROJECT_PATH)
    lockfile = _read(UV_LOCK_PATH)
    pyproject_data = tomllib.loads(pyproject)
    project = pyproject_data["project"]
    dependency_groups = pyproject_data["dependency-groups"]

    assert project["version"] == "0.1.0"
    assert "pytest-xdist>=3.8.0" in dependency_groups["dev"]
    assert "pytest-xdist" not in project["dependencies"]
    assert 'name = "pytest-xdist"' in lockfile
    assert 'name = "execnet"' in lockfile
    assert "addopts" not in pyproject
