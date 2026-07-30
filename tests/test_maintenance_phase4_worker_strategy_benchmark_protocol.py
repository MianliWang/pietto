from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path
from typing import cast
from test_phase54_local_import_module_export_foundation_scope_lock import (
    phase54_slice5_gate2_manifest_is_active as _slice5_gate2,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = (
    REPO_ROOT
    / "docs/plan/maintenance-phase-4-worker-strategy-benchmark-ci-split-evaluation.md"
)
SPEC_PATH = (
    REPO_ROOT / "docs/spec/maintenance-phase4-worker-strategy-benchmark-protocol-v1.md"
)
VALIDATE_PATH = REPO_ROOT / "scripts/validate.py"
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/ci.yml"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
UV_LOCK_PATH = REPO_ROOT / "uv.lock"

BASELINE_COMMIT = "2f2ff037b81f1a3b31a3da2bd4e4ce661ab2fbdf"
BASELINE_SUBJECT = "Complete Maintenance Phase 3 validation pipeline audit"
CI_VALIDATE_COMMAND = (
    "uv run python scripts/validate.py --timings --pytest-workers auto "
    "--pytest-dist loadfile --pytest-maxprocesses 4"
)
DIRECT_PYTEST_ROWS = (
    "uv run pytest",
    "uv run pytest -n 2 --dist=loadfile",
    "uv run pytest -n 4 --dist=loadfile",
    "uv run pytest -n 6 --dist=loadfile",
    "uv run pytest -n 8 --dist=loadfile",
    "uv run pytest -n auto --maxprocesses 4 --dist=loadfile",
    "uv run pytest -n 4 --dist=loadscope",
    "uv run pytest -n 4 --dist=load",
    "uv run pytest -n 4 --dist=worksteal",
)
WRAPPER_ROWS = (
    "uv run python scripts/validate.py --timings --pytest-workers off",
    "uv run python scripts/validate.py --timings --pytest-workers 2 "
    "--pytest-dist loadfile",
    "uv run python scripts/validate.py --timings --pytest-workers 4 "
    "--pytest-dist loadfile",
    CI_VALIDATE_COMMAND,
)
ALLOWED_SLICE1_GATE2_PATHS = {
    "docs/plan/maintenance-phase-4-worker-strategy-benchmark-ci-split-evaluation.md",
    "docs/spec/maintenance-phase4-worker-strategy-benchmark-protocol-v1.md",
    "tests/test_maintenance_phase4_worker_strategy_benchmark_protocol.py",
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


def test_plan_and_spec_exist_and_lock_phase_identity_and_baseline() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()

    for document in _documents():
        for required in (
            "Maintenance Phase 4",
            "Worker Strategy Benchmark & CI Split Evaluation",
            "Worker Strategy Benchmark Protocol",
            "docs/spec/static-audit",
            "Maintenance Phase 3",
            BASELINE_COMMIT,
            BASELINE_SUBJECT,
            "29052797303",
            "CI / push",
            "completed / success",
            "headSha",
            "0.1.0",
            "no exact-match tag",
        ):
            assert required in document, required


def test_current_worker_semantics_are_documented_and_source_backed() -> None:
    validate = _read(VALIDATE_PATH)

    for document in _documents():
        for required in (
            "--pytest-workers off",
            "--pytest-workers auto",
            "--pytest-workers logical",
            "--pytest-workers <positive integer>",
            "uv run pytest",
            "-n auto",
            "pytest-xdist auto",
            "os.cpu_count()",
            "max(os.cpu_count() or 1, 1)",
            "--pytest-maxprocesses",
            "--maxprocesses",
            "loadfile",
            "loadscope",
            "not currently wrapper-supported",
            "before validation subprocesses",
            "--timings",
            "dev-only",
            "No global pytest addopts",
        ):
            assert required in document, required

    for required in (
        'PYTEST_DIST_CHOICES = ("loadfile", "loadscope")',
        'command.extend(("-n", "auto"))',
        "worker_count = max(os.cpu_count() or 1, 1)",
        'command.extend(("--maxprocesses", str(args.pytest_maxprocesses)))',
        'dist_mode = args.pytest_dist or "loadfile"',
    ):
        assert required in validate, required


def test_current_ci_command_matrix_cache_and_serial_steps_are_locked() -> None:
    workflow = _read(WORKFLOW_PATH)

    assert workflow.count(CI_VALIDATE_COMMAND) == 1
    for document in _documents():
        for required in (
            CI_VALIDATE_COMMAND,
            "Python 3.12/3.13",
            "no job-level split",
            "Local default remains serial",
            "capped at 4",
            "distribution remains `loadfile`",
            "separate serial post-validate steps",
            "enable-cache: false",
            "UV_PROJECT_ENVIRONMENT",
            "UV_CACHE_DIR",
            "Pyright and pytest remain sequential",
            "No hidden validation concurrency",
        ):
            assert required in document, required

    for required in (
        '          - "3.12"',
        '          - "3.13"',
        "enable-cache: false",
        "UV_PROJECT_ENVIRONMENT=$RUNNER_TEMP/pietto-venv",
        "UV_CACHE_DIR=$RUNNER_TEMP/uv-cache",
        "uv run python scripts/check_generated.py",
        "uv run python scripts/check_goldens.py",
        "uv run python scripts/package_smoke.py",
    ):
        assert required in workflow, required


def test_direct_and_wrapper_benchmark_rows_are_protocol_only() -> None:
    for document in _documents():
        for command in (*DIRECT_PYTEST_ROWS, *WRAPPER_ROWS):
            assert command in document, command
        for required in (
            "Serial",
            "control",
            "2/4/6/8",
            "reviewed safe cohort",
            "full-suite compatibility",
            "direct-pytest",
            "not currently wrapper-supported",
            "Slice 1",
            "does not run",
        ):
            assert required in document, required


def test_sampling_protocol_and_decision_threshold_are_locked() -> None:
    for document in _documents():
        for required in (
            "one warm-up",
            "discarded",
            "at least 5 successful measured samples",
            "randomized or counterbalanced",
            "same clean commit",
            "Cold-cache and warm-cache",
            "median",
            "p90",
            "coefficient of variation",
            "zero unexplained failures",
            "second day",
            "10% median improvement",
            "5% p90 regression",
            "no material variance increase",
            "no reliability regression",
            "below-threshold result means no change",
        ):
            assert required in document, required


def test_safety_exclusions_and_serial_commands_are_locked() -> None:
    for document in _documents():
        for required in (
            "serial-only",
            "dirty-path guards",
            "git status/diff tests",
            "completion-audit dirty-state checks",
            "hash/private-surface",
            "generated/golden/package-smoke audit tests",
            "dependency/workflow/release boundary tests",
            "package builds",
            "temporary venv",
            "installed CLI smoke tests",
            "package/network/build-sensitive",
            "fixed/shared output paths",
            "shared caches",
            "cwd/env mutation",
            "subprocess/CLI tests",
            "tmp_path",
            "random",
            "time.sleep",
            "broad repository scans",
            "scripts/check_generated.py",
            "scripts/check_goldens.py",
            "scripts/package_smoke.py",
        ):
            assert required in document, required


def test_data_capture_schema_is_complete() -> None:
    for document in _documents():
        for required in (
            "commit SHA and clean status",
            "timestamp",
            "sample index",
            "randomized order position",
            "runner label",
            "OS",
            "architecture",
            "CPU model",
            "os.cpu_count()",
            "CPU quota",
            "available memory",
            "Python, uv, pytest, and pytest-xdist versions",
            "dependency lock identity",
            "cache posture",
            "background-load notes",
            "exact command",
            "requested and effective worker count",
            "--maxprocesses",
            "distribution mode",
            "selected suite or cohort",
            "external wall-clock elapsed time",
            "pytest-reported runtime",
            "collection time",
            "xdist startup",
            "scripts/validate.py --timings",
            "exit code",
            "passed, failed, skipped, and xfailed counts",
            "worker-crash",
            "CPU or memory utilization",
            "raw samples plus",
        ):
            assert required in document, required


def test_local_first_ci_sequence_deferrals_and_non_goals_are_locked() -> None:
    for document in _documents():
        for required in (
            "local-only",
            "clean immutable checkout",
            "stable local winner",
            "at least 5 comparable successful samples",
            "per Python matrix version",
            "Manual reruns",
            "current CI command",
            "Pyright/pytest concurrent execution remains deferred",
            "Hidden concurrency inside `scripts/validate.py`",
            "Job-level CI split remains deferred",
            "distribution",
            "cache",
            "queue",
            "startup duplication",
            "fail-fast",
            "log clarity",
            "total billed time",
            "wall-clock improvement",
            "no benchmark",
            "selects no winner",
            "no benchmark script",
            "global pytest addopts",
            "package version",
            "source/compiler/parser/grammar/generated/fixture/golden/package",
            "release",
            "publish",
            "upload",
            "signing",
            "attestation",
        ):
            assert required in document, required
        assert "worker-cap" in document or "Worker cap" in document


def test_forbidden_surfaces_have_no_diff() -> None:
    for relative_path in UNCHANGED_PATHS:
        assert (_git_output(["diff", "--", relative_path]) == "") or _slice5_gate2(), (
            relative_path
        )


def test_package_version_addopts_and_xdist_dependency_scope_are_unchanged() -> None:
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


def test_dirty_paths_are_clean_or_exact_slice1_allowlist() -> None:
    assert (_dirty_paths() in (set(), ALLOWED_SLICE1_GATE2_PATHS)) or _slice5_gate2()
