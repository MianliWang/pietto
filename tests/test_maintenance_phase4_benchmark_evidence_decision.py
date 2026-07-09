from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path
from typing import cast

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = (
    REPO_ROOT
    / "docs/plan/maintenance-phase-4-worker-strategy-benchmark-ci-split-evaluation.md"
)
SPEC_PATH = REPO_ROOT / "docs/spec/maintenance-phase4-benchmark-evidence-decision-v1.md"
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/ci.yml"
VALIDATE_PATH = REPO_ROOT / "scripts/validate.py"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
UV_LOCK_PATH = REPO_ROOT / "uv.lock"

CI_VALIDATE_COMMAND = (
    "uv run python scripts/validate.py --timings --pytest-workers auto "
    "--pytest-dist loadfile --pytest-maxprocesses 4"
)
EVIDENCE_PATHS = (
    "/tmp/maintenance-phase4-slice2-local-benchmark-evidence.txt",
    "/tmp/maintenance-phase4-slice2-local-benchmark-results.csv",
    "/tmp/maintenance-phase4-slice2-local-benchmark-results.json",
)
CONFIG_IDS = (
    "serial_control",
    "ci_auto_cap4_loadfile",
    "fixed4_loadfile",
    "cpu50_10_loadfile",
    "cpu75_15_loadfile",
    "cpu90_18_loadfile",
    "cpu75_15_loadscope",
)
ALLOWED_SLICE3_GATE2_PATHS = {
    "docs/plan/maintenance-phase-4-worker-strategy-benchmark-ci-split-evaluation.md",
    "docs/spec/maintenance-phase4-benchmark-evidence-decision-v1.md",
    "tests/test_maintenance_phase4_benchmark_evidence_decision.py",
}
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
    "src",
    "grammar",
    "tests/fixtures",
    "tests/goldens",
    "docs/spec/pietto-v0.9.md",
    "docs/spec/pietto-roadmap-phase45-60-v1.md",
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


def test_plan_and_spec_exist_and_lock_slice_identity() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()

    for document in _documents():
        for required in (
            "Maintenance Phase 4",
            "Benchmark Evidence Decision / No-change Lock",
            "docs/spec/tests-only",
            "no-change decision",
            "developer validation infrastructure",
        ):
            assert required in document, required


def test_evidence_identity_context_and_config_matrix_are_locked() -> None:
    for document in _documents():
        for required in (
            *EVIDENCE_PATHS,
            "effective_cpu=20",
            "local WSL2",
            "direct-pytest",
            "safe-cohort",
            "no wrapper track",
            "no `load`/`worksteal`",
            "no full suite",
            "no CI experiment",
            *CONFIG_IDS,
        ):
            assert required in document, required


def test_sample_counts_and_reliability_facts_are_locked() -> None:
    for document in _documents():
        for required in (
            "42 rows",
            "7 warmups",
            "35 measured samples",
            "5 measured samples per config",
            "exit 0",
            "294 passed",
            "0 failed",
            "0 skipped",
            "0 xfailed",
            "no retry",
            "no worker crash",
            "no stop condition",
        ):
            assert required in document, required


def test_key_result_threshold_and_no_change_decision_are_locked() -> None:
    for document in _documents():
        for required in (
            "ci_auto_cap4_loadfile",
            "1.714843s",
            "serial_control",
            "1.568251s",
            "8.548%",
            "10%",
            "No row met threshold",
            "provisional_candidate",
            "none",
            "no final CI winner",
            "no change",
        ):
            assert required in document, required


def test_no_change_authorization_boundaries_are_locked() -> None:
    for document in _documents():
        for required in (
            "no CI change",
            "no `scripts/validate.py` change",
            "no wrapper change",
            "no worker cap/default change",
            "no distribution mode change",
            "no `load`/`worksteal` wrapper expansion",
            "no cache policy change",
            "no job-level CI split",
            "no Pyright/pytest concurrency",
            "no dependency change",
            "no lockfile change",
            "no final CI winner",
        ):
            assert required in document, required


def test_current_behavior_and_interpretation_limits_are_preserved() -> None:
    workflow = _read(WORKFLOW_PATH)
    validate = _read(VALIDATE_PATH)

    assert workflow.count(CI_VALIDATE_COMMAND) == 1
    assert 'PYTEST_DIST_CHOICES = ("loadfile", "loadscope")' in validate

    for document in _documents():
        for required in (
            CI_VALIDATE_COMMAND,
            "local default remains serial",
            "pytest-xdist remains dev-only",
            "no global pytest addopts",
            "one validation job per Python 3.12/3.13 matrix entry",
            "separate serial post-validate checks",
            "full-suite",
            "wrapper-track",
            "fresh-session/second-day",
            "hosted-CI evaluation",
            "remain deferred",
            "does not prove full-suite behavior or GitHub-hosted CI behavior",
            "descriptive evidence, not universal xdist proof",
            "0.1.0",
        ):
            assert required in document, required


def test_forbidden_surfaces_have_no_diff() -> None:
    for relative_path in UNCHANGED_PATHS:
        assert _git_output(["diff", "--", relative_path]) == "", relative_path


def test_package_version_addopts_and_xdist_scope_are_unchanged() -> None:
    pyproject_text = _read(PYPROJECT_PATH)
    pyproject = tomllib.loads(pyproject_text)
    project = cast(dict[str, object], pyproject["project"])
    dependency_groups = cast(dict[str, object], pyproject["dependency-groups"])
    runtime_dependencies = cast(list[str], project["dependencies"])
    dev_dependencies = cast(list[str], dependency_groups["dev"])

    assert project["version"] == "0.1.0"
    assert "addopts" not in pyproject_text
    assert "pytest-xdist>=3.8.0" in dev_dependencies
    assert all("pytest-xdist" not in item for item in runtime_dependencies)
    assert 'name = "pytest-xdist"' in _read(UV_LOCK_PATH)


def test_dirty_paths_are_clean_or_exact_slice3_allowlist() -> None:
    assert _dirty_paths() in (set(), ALLOWED_SLICE3_GATE2_PATHS)
