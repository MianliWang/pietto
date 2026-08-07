from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path
from typing import cast
from _phase54_active_gate2_manifest import (
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = (
    REPO_ROOT
    / "docs/plan/maintenance-phase-4-worker-strategy-benchmark-ci-split-evaluation.md"
)
SPEC_PATH = REPO_ROOT / "docs/spec/maintenance-phase4-completion-audit-v1.md"
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/ci.yml"
VALIDATE_PATH = REPO_ROOT / "scripts/validate.py"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
UV_LOCK_PATH = REPO_ROOT / "uv.lock"

CI_VALIDATE_COMMAND = (
    "uv run python scripts/validate.py --timings --pytest-workers auto "
    "--pytest-dist loadfile --pytest-maxprocesses 4"
)
ALLOWED_SLICE4_GATE2_PATHS = {
    "docs/plan/maintenance-phase-4-worker-strategy-benchmark-ci-split-evaluation.md",
    "docs/spec/maintenance-phase4-completion-audit-v1.md",
    "tests/test_maintenance_phase4_completion_audit.py",
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
            "Worker Strategy Benchmark & CI Split Evaluation",
            "Completion Audit / Status Lock",
            "docs/spec/tests-only",
            "developer validation infrastructure",
            "changes no validation behavior",
            "runs no benchmark",
        ):
            assert required in document, required


def test_gate2_completion_is_explicitly_conditional_on_gate3() -> None:
    for document in _documents():
        for required in (
            "Maintenance Phase 4 is not complete during Gate 2",
            "Slice 4 is not complete during Gate 2",
            "does not claim Gate 3 has already succeeded",
            "final commit",
            "normal push",
            "natural CI",
            "completed / success",
            "exact headSha match",
            "If Gate 3 push or natural CI does not succeed, Phase 4 remains incomplete",
            "After successful Gate 3",
        ):
            assert required in document, required


def test_slice1_inventory_and_natural_ci_identity_are_locked() -> None:
    for document in _documents():
        for required in (
            "Worker Strategy Benchmark Protocol",
            "9bdf1aebce0dc5f7985c95f36bb0d20b0a996fb3",
            "Add Maintenance Phase 4 worker benchmark protocol",
            "29054341393",
            "CI / push",
            "completed / success",
            "exact headSha match",
            "docs/spec/static-audit",
        ):
            assert required in document, required


def test_slice2_evidence_summary_is_locked_without_runtime_dependency() -> None:
    for document in _documents():
        for required in (
            "Controlled Clean-local Benchmark Execution",
            "effective_cpu=20",
            "7 configs",
            "7 warmups",
            "35 measured samples",
            "42 total runs",
            "294 passed",
            "serial_control",
            "ci_auto_cap4_loadfile",
            "1.568251",
            "1.714843",
            "8.548",
            "no row met threshold",
            "provisional candidate",
            "none",
        ):
            assert required in document, required


def test_slice3_inventory_and_no_change_identity_are_locked() -> None:
    for document in _documents():
        for required in (
            "Benchmark Evidence Decision / No-change Lock",
            "024b23a5a000cbedf0415880bf365173ad250db4",
            "Add Phase 4 benchmark no-change decision",
            "29057920189",
            "CI / push",
            "completed / success",
            "exact headSha match",
            "docs/spec/tests-only no-change decision lock",
            "no final CI winner",
        ):
            assert required in document, required


def test_no_change_authorization_and_future_boundaries_are_locked() -> None:
    for document in _documents():
        for required in (
            "no CI change",
            "no scripts/validate.py change",
            "no wrapper change",
            "no worker cap/default change",
            "no distribution mode change",
            "no cache policy change",
            "no job-level CI split",
            "no Pyright/pytest concurrency",
            "no load/worksteal wrapper support",
            "no dependency or lockfile change",
            "no final CI winner",
            "full-suite",
            "wrapper-track",
            "fresh-session/second-day",
            "hosted-CI",
            "remains deferred",
            "requires separate approval",
        ):
            assert required in document, required


def test_current_ci_and_release_boundaries_are_preserved() -> None:
    workflow = _read(WORKFLOW_PATH)

    assert workflow.count(CI_VALIDATE_COMMAND) == 1
    assert "enable-cache: false" in workflow

    for document in _documents():
        for required in (
            CI_VALIDATE_COMMAND,
            "local default remains serial",
            "auto/maxprocesses-4/loadfile",
            "pytest-xdist remains dev-only",
            "no global pytest addopts",
            "one validation job per Python 3.12/3.13 matrix entry",
            "separate serial post-validate checks",
            "enable-cache: false",
            "Pyright and pytest remain sequential",
            "0.1.0",
            "no tag",
            "no release",
            "no publish",
            "no upload",
            "no signing",
            "no attestation",
        ):
            assert required in document, required


def test_forbidden_surfaces_have_no_diff() -> None:
    for relative_path in UNCHANGED_PATHS:
        assert (
            _git_output(["diff", "--", relative_path]) == ""
        ) or _phase54_active_gate2_is_active(), relative_path


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


def test_validate_and_workflow_sources_remain_current_and_unchanged() -> None:
    validate = _read(VALIDATE_PATH)

    assert 'PYTEST_DIST_CHOICES = ("loadfile", "loadscope")' in validate
    assert _git_output(["diff", "--", ".github/workflows/ci.yml"]) == ""
    assert _git_output(["diff", "--", "scripts/validate.py"]) == ""


def test_dirty_paths_are_clean_or_exact_slice4_allowlist() -> None:
    assert (
        _dirty_paths() in (set(), ALLOWED_SLICE4_GATE2_PATHS)
    ) or _phase54_active_gate2_is_active()
