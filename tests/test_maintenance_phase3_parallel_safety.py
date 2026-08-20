from __future__ import annotations

from pathlib import Path
import tomllib

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = (
    REPO_ROOT / "docs/plan/maintenance-phase-3-validation-pipeline-performance.md"
)
SPEC_PATH = REPO_ROOT / "docs/spec/maintenance-phase3-parallel-safety-v1.md"
VALIDATE_PATH = REPO_ROOT / "scripts/validate.py"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
UV_LOCK_PATH = REPO_ROOT / "uv.lock"
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/ci.yml"
CHECK_GENERATED_PATH = REPO_ROOT / "scripts/check_generated.py"
CHECK_GOLDENS_PATH = REPO_ROOT / "scripts/check_goldens.py"
PACKAGE_SMOKE_PATH = REPO_ROOT / "scripts/package_smoke.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def _docs() -> str:
    return " ".join(_normalized(path) for path in (PLAN_PATH, SPEC_PATH))


def test_plan_and_spec_exist_and_name_parallel_safety_slice() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()

    for path in (PLAN_PATH, SPEC_PATH):
        text = _normalized(path)
        assert "Maintenance Phase 3" in text
        assert "Parallel Safety Audit & Repairs" in text
        assert "parallel safety" in text


def test_parallel_safety_categories_are_documented() -> None:
    docs = _docs()

    for required in (
        "likely xdist-safe candidate categories",
        "pure parser tests",
        "in-memory source strings",
        "pure semantic/IR/SQL renderer tests",
        "in-memory diagnostics/facts/IR/SQL strings",
        "isolated `tmp_path` tests",
        "unit tests that monkeypatch subprocess calls",
        "static audit tests",
        "needs-review categories",
        "`tmp_path` or tempdir tests that write output files",
        "`subprocess.run`",
        "`cwd=`",
        "`monkeypatch.chdir`",
        "`setenv`/`delenv`",
        "`os.environ`",
        "global caches",
        "`random`",
        "`time.sleep`",
        "shared output paths",
        "package/build temp directories",
        "CLI tests that invoke subprocesses",
        "broad repository scans",
    ):
        assert required in docs, required


def test_serial_only_and_sensitive_surfaces_are_documented() -> None:
    docs = _docs()

    for required in (
        "serial-only initial surfaces",
        "scripts/check_generated.py",
        "scripts/check_goldens.py",
        "scripts/package_smoke.py",
        "full `scripts/validate.py` release path",
        "dirty-path guards",
        "hash/private-surface lock tests",
        "generated/golden/package-smoke audit tests",
        "dependency/workflow/release boundary tests",
        "Generated checks, golden checks, package smoke",
        "remain serial initially",
        "package/network/build-sensitive",
        "Package smoke",
        "serial",
    ):
        assert required in docs, required


def test_slice5_deferrals_and_non_goals_are_documented() -> None:
    docs = _docs()

    for required in (
        "CI opt-in remains deferred to Slice 6",
        "Job-level CI split remains deferred",
        "Full pytest",
        "full `scripts/validate.py`",
        "dependency changes",
        "lockfile changes",
        "workflow changes",
        "source/compiler changes",
        "generated changes",
        "golden changes",
        "package version changes",
        "release changes",
        "tag changes",
        "publish changes",
        "upload changes",
        "signing changes",
        "attestation changes",
    ):
        assert required in docs, required


def test_focused_xdist_smoke_command_is_locked() -> None:
    docs = _docs()

    assert "tests/test_phase11_validation_entrypoint.py" in docs
    assert "tests/test_maintenance_phase3_parallel_safety.py" in docs
    assert (
        "uv run pytest -n 2 --dist=loadfile "
        "tests/test_phase11_validation_entrypoint.py "
        "tests/test_maintenance_phase3_parallel_safety.py"
    ) in docs


def test_validation_scripts_dependency_files_and_ci_workflow_have_no_diff() -> None:
    for path in (
        VALIDATE_PATH,
        PYPROJECT_PATH,
        UV_LOCK_PATH,
        WORKFLOW_PATH,
        CHECK_GENERATED_PATH,
        CHECK_GOLDENS_PATH,
        PACKAGE_SMOKE_PATH,
    ):
        assert path.is_file()


def test_package_version_and_pytest_addopts_are_unchanged() -> None:
    pyproject = _read(PYPROJECT_PATH)
    pyproject_data = tomllib.loads(pyproject)
    project = pyproject_data["project"]

    assert project["version"] == "0.1.0"
    assert "addopts" not in pyproject
