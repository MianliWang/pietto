from __future__ import annotations

import ast
import importlib.util
import subprocess
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATE_PATH = REPO_ROOT / "scripts" / "validate.py"
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/ci.yml"
SLICE5_SPEC = (
    REPO_ROOT
    / "docs/spec/validation-performance-interlude-slice5-resource-aware-xdist-and-ci-parallelism-decision-v1.md"
)
EXPECTED_GATES = (
    ("lockfile", ("uv", "lock", "--check")),
    ("format", ("uv", "run", "ruff", "format", "--check", ".")),
    ("lint", ("uv", "run", "ruff", "check", ".")),
    ("production typing", ("uv", "run", "pyright")),
    (
        "test typing",
        ("uv", "run", "pyright", "--project", "pyrightconfig.tests.json"),
    ),
    ("tests", ("uv", "run", "pytest")),
)
DEFAULT_GATES = (
    *EXPECTED_GATES[:-1],
    ("tests", ("uv", "run", "pytest", "-n", "4", "--dist=loadfile")),
)


def _load_validate_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("pietto_validate", VALIDATE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validate = cast(Any, _load_validate_module())
resource_worker_count = validate._resource_worker_count


@pytest.fixture(autouse=True)
def _stable_resource_worker_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        validate,
        "_resource_worker_count",
        lambda maximum=None: min(4, maximum) if maximum is not None else 4,
    )


def test_validation_script_exists_and_uses_only_standard_library_imports() -> None:
    assert VALIDATE_PATH.is_file()

    tree = ast.parse(VALIDATE_PATH.read_text(encoding="utf-8"))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    imported_modules.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )

    assert imported_modules == {
        "__future__",
        "argparse",
        "collections.abc",
        "os",
        "pathlib",
        "shlex",
        "subprocess",
        "sys",
        "time",
    }


def test_validation_gates_have_the_exact_non_mutating_order() -> None:
    assert validate.GATES == EXPECTED_GATES
    assert EXPECTED_GATES[0][1] == ("uv", "lock", "--check")
    assert EXPECTED_GATES[1][1] == (
        "uv",
        "run",
        "ruff",
        "format",
        "--check",
        ".",
    )
    assert ("uv", "run", "ruff", "format", ".") not in {
        command for _, command in EXPECTED_GATES
    }
    assert EXPECTED_GATES[3][1] == ("uv", "run", "pyright")
    assert EXPECTED_GATES[4][1] == (
        "uv",
        "run",
        "pyright",
        "--project",
        "pyrightconfig.tests.json",
    )
    assert EXPECTED_GATES[5][1] == ("uv", "run", "pytest")


def test_validation_runs_from_repo_root_and_keeps_child_output_attached(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[tuple[str, ...], Path, bool]] = []

    def fake_run(
        command: tuple[str, ...],
        *,
        cwd: Path,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd, check))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(validate.subprocess, "run", fake_run)

    assert validate.main(()) == 0
    assert calls == [(command, REPO_ROOT, False) for _, command in DEFAULT_GATES]

    output = capsys.readouterr().out
    assert output.splitlines() == [
        f"[validate] {name}: {' '.join(command)}" for name, command in DEFAULT_GATES
    ]
    assert " completed in " not in output
    assert "[validate] total completed in " not in output


def test_validation_pytest_workers_off_keeps_serial_pytest_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(
        command: tuple[str, ...],
        *,
        cwd: Path,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        assert cwd == REPO_ROOT
        assert check is False
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(validate.subprocess, "run", fake_run)

    assert validate.main(("--pytest-workers", "off")) == 0
    assert calls == [command for _, command in EXPECTED_GATES]
    assert calls[-1] == ("uv", "run", "pytest")


def test_validation_pytest_integer_workers_use_loadfile_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(
        command: tuple[str, ...],
        *,
        cwd: Path,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(validate.subprocess, "run", fake_run)

    assert validate.main(("--pytest-workers", "4")) == 0
    assert calls[:-1] == [command for _, command in EXPECTED_GATES[:-1]]
    assert calls[-1] == ("uv", "run", "pytest", "-n", "4", "--dist=loadfile")


def test_validation_pytest_integer_workers_are_capped_by_maxprocesses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(
        command: tuple[str, ...],
        *,
        cwd: Path,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(validate.subprocess, "run", fake_run)

    assert validate.main(("--pytest-workers", "4", "--pytest-maxprocesses", "2")) == 0
    assert calls[-1] == ("uv", "run", "pytest", "-n", "2", "--dist=loadfile")


def test_validation_pytest_auto_workers_support_maxprocesses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(
        command: tuple[str, ...],
        *,
        cwd: Path,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(validate.subprocess, "run", fake_run)

    assert (
        validate.main(("--pytest-workers", "auto", "--pytest-maxprocesses", "4")) == 0
    )
    assert calls[-1] == (
        "uv",
        "run",
        "pytest",
        "-n",
        "auto",
        "--maxprocesses",
        "4",
        "--dist=loadfile",
    )


def test_validation_pytest_logical_workers_use_cpu_count_and_maxprocesses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(
        command: tuple[str, ...],
        *,
        cwd: Path,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(validate.subprocess, "run", fake_run)
    monkeypatch.setattr(validate.os, "cpu_count", lambda: 20)

    assert (
        validate.main(("--pytest-workers", "logical", "--pytest-maxprocesses", "4"))
        == 0
    )
    assert calls[-1] == ("uv", "run", "pytest", "-n", "4", "--dist=loadfile")


def test_validation_pytest_logical_workers_fall_back_to_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(
        command: tuple[str, ...],
        *,
        cwd: Path,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(validate.subprocess, "run", fake_run)
    monkeypatch.setattr(validate.os, "cpu_count", lambda: None)

    assert validate.main(("--pytest-workers", "logical")) == 0
    assert calls[-1] == ("uv", "run", "pytest", "-n", "1", "--dist=loadfile")


def test_validation_pytest_dist_is_emitted_only_when_workers_are_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(
        command: tuple[str, ...],
        *,
        cwd: Path,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(validate.subprocess, "run", fake_run)

    assert validate.main(("--pytest-workers", "2", "--pytest-dist", "loadscope")) == 0
    assert calls[-1] == ("uv", "run", "pytest", "-n", "2", "--dist=loadscope")
    assert "--dist=loadfile" not in calls[-1]


def test_validation_fails_fast_and_returns_the_failing_exit_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []
    failing_command = EXPECTED_GATES[2][1]

    def fake_run(
        command: tuple[str, ...],
        *,
        cwd: Path,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        assert cwd == REPO_ROOT
        assert check is False
        calls.append(command)
        return subprocess.CompletedProcess(
            command,
            23 if command == failing_command else 0,
        )

    monkeypatch.setattr(validate.subprocess, "run", fake_run)

    assert validate.main(()) == 23
    assert calls == [command for _, command in EXPECTED_GATES[:3]]


def test_resource_aware_pytest_failure_is_returned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []
    failing_command = DEFAULT_GATES[-1][1]

    def fake_run(
        command: tuple[str, ...],
        *,
        cwd: Path,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        assert cwd == REPO_ROOT
        assert check is False
        calls.append(command)
        return subprocess.CompletedProcess(
            command,
            23 if command == failing_command else 0,
        )

    monkeypatch.setattr(validate.subprocess, "run", fake_run)

    assert validate.main(()) == 23
    assert calls == [command for _, command in DEFAULT_GATES]


def test_validation_timings_success_path_reports_each_gate_and_total(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[tuple[str, ...], Path, bool]] = []
    timer_values = iter(
        (
            1.0,
            2.0,
            2.125,
            3.0,
            3.250,
            4.0,
            4.375,
            5.0,
            5.500,
            6.0,
            6.625,
            7.0,
            7.750,
            8.0,
        )
    )

    def fake_run(
        command: tuple[str, ...],
        *,
        cwd: Path,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd, check))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(validate.subprocess, "run", fake_run)
    monkeypatch.setattr(validate.time, "perf_counter", lambda: next(timer_values))

    assert validate.main(("--timings",)) == 0
    assert calls == [(command, REPO_ROOT, False) for _, command in DEFAULT_GATES]

    expected_lines: list[str] = []
    for (name, command), elapsed in zip(
        DEFAULT_GATES,
        ("0.125", "0.250", "0.375", "0.500", "0.625", "0.750"),
        strict=True,
    ):
        expected_lines.append(f"[validate] {name}: {' '.join(command)}")
        expected_lines.append(f"[validate] {name} completed in {elapsed}s")
    expected_lines.append("[validate] total completed in 7.000s")

    assert capsys.readouterr().out.splitlines() == expected_lines


def test_validation_timings_compose_with_pytest_workers(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[tuple[str, ...], Path, bool]] = []
    timer_values = iter(
        (
            1.0,
            2.0,
            2.125,
            3.0,
            3.250,
            4.0,
            4.375,
            5.0,
            5.500,
            6.0,
            6.625,
            7.0,
            7.750,
            8.0,
        )
    )

    def fake_run(
        command: tuple[str, ...],
        *,
        cwd: Path,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd, check))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(validate.subprocess, "run", fake_run)
    monkeypatch.setattr(validate.time, "perf_counter", lambda: next(timer_values))

    assert validate.main(("--timings", "--pytest-workers", "2")) == 0
    expected_gates = (
        *EXPECTED_GATES[:-1],
        ("tests", ("uv", "run", "pytest", "-n", "2", "--dist=loadfile")),
    )
    assert calls == [(command, REPO_ROOT, False) for _, command in expected_gates]

    output_lines = capsys.readouterr().out.splitlines()
    assert output_lines[-3:] == [
        "[validate] tests: uv run pytest -n 2 --dist=loadfile",
        "[validate] tests completed in 0.750s",
        "[validate] total completed in 7.000s",
    ]


def test_validation_timings_failure_path_reports_failed_gate_and_total(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[str, ...]] = []
    failing_command = EXPECTED_GATES[2][1]
    timer_values = iter((1.0, 2.0, 2.500, 3.0, 3.250, 4.0, 4.750, 5.0))

    def fake_run(
        command: tuple[str, ...],
        *,
        cwd: Path,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        assert cwd == REPO_ROOT
        assert check is False
        calls.append(command)
        return subprocess.CompletedProcess(
            command,
            23 if command == failing_command else 0,
        )

    monkeypatch.setattr(validate.subprocess, "run", fake_run)
    monkeypatch.setattr(validate.time, "perf_counter", lambda: next(timer_values))

    assert validate.main(("--timings",)) == 23
    assert calls == [command for _, command in EXPECTED_GATES[:3]]

    expected_lines: list[str] = []
    for (name, command), elapsed in zip(
        EXPECTED_GATES[:3],
        ("0.500", "0.250", "0.750"),
        strict=True,
    ):
        expected_lines.append(f"[validate] {name}: {' '.join(command)}")
        expected_lines.append(f"[validate] {name} completed in {elapsed}s")
    expected_lines.append("[validate] total completed in 4.000s")

    output_lines = capsys.readouterr().out.splitlines()
    assert output_lines == expected_lines
    assert not any("production typing" in line for line in output_lines)


def test_validation_argparse_errors_do_not_invoke_gates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(
        command: tuple[str, ...],
        *,
        cwd: Path,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(validate.subprocess, "run", fake_run)

    with pytest.raises(SystemExit) as raised:
        validate.main(("--unknown-option",))

    assert raised.value.code == 2
    assert calls == []


@pytest.mark.parametrize(
    "argv",
    (
        ("--pytest-workers", "0"),
        ("--pytest-workers", "-1"),
        ("--pytest-workers", "many"),
        ("--pytest-workers", ""),
        ("--pytest-workers", "off", "--pytest-maxprocesses", "4"),
        ("--pytest-workers", "off", "--pytest-dist", "loadfile"),
        ("--pytest-workers", "2", "--pytest-maxprocesses", "0"),
        ("--pytest-workers", "2", "--pytest-maxprocesses", "-1"),
        ("--pytest-workers", "2", "--pytest-maxprocesses", "many"),
        ("--pytest-workers", "2", "--pytest-dist", "load"),
    ),
)
def test_validation_pytest_worker_argparse_errors_do_not_invoke_gates(
    argv: tuple[str, ...],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(
        command: tuple[str, ...],
        *,
        cwd: Path,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(validate.subprocess, "run", fake_run)

    with pytest.raises(SystemExit) as raised:
        validate.main(argv)

    assert raised.value.code == 2
    assert calls == []


def test_slice2_validation_stays_separate_from_later_workflows() -> None:
    scripts = tuple(
        path.relative_to(REPO_ROOT).as_posix()
        for path in sorted((REPO_ROOT / "scripts").glob("*.py"))
    )

    assert scripts == (
        "scripts/check_generated.py",
        "scripts/check_goldens.py",
        "scripts/package_smoke.py",
        "scripts/validate.py",
    )
    assert all("check_generated.py" not in command for _, command in validate.GATES)
    assert all("check_goldens.py" not in command for _, command in validate.GATES)
    assert all("package_smoke.py" not in command for _, command in validate.GATES)
    assert (REPO_ROOT / ".github/workflows/ci.yml").is_file()
    assert (REPO_ROOT / "scripts" / "package_smoke.py").is_file()


def test_validation_does_not_use_global_pytest_addopts() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    validate_source = VALIDATE_PATH.read_text(encoding="utf-8")

    assert "addopts" not in pyproject
    assert "PYTEST_ADDOPTS" not in validate_source


def test_resource_worker_formula_respects_cpu_memory_and_optional_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gib = 1024**3
    monkeypatch.setattr(validate, "_usable_cpu_count", lambda: 20)
    monkeypatch.setattr(validate, "_memory_snapshot", lambda: (8 * gib, 4 * gib))
    assert resource_worker_count() == 4
    assert resource_worker_count(2) == 2

    monkeypatch.setattr(validate, "_memory_snapshot", lambda: (8 * gib, gib))
    assert resource_worker_count() == 1
    monkeypatch.setattr(validate, "_memory_snapshot", lambda: None)
    assert resource_worker_count() == 1


def test_cpu_and_memory_detection_use_effective_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(validate.os, "cpu_count", lambda: 20)
    monkeypatch.setattr(validate.os, "process_cpu_count", lambda: 8, raising=False)
    monkeypatch.setattr(validate.os, "sched_getaffinity", lambda _pid: set(range(6)))
    monkeypatch.setattr(validate, "_cgroup_cpu_count", lambda: 4)
    assert validate._usable_cpu_count() == 4

    gib = 1024**3
    meminfo = f"MemTotal: {8 * gib // 1024} kB\nMemAvailable: {6 * gib // 1024} kB"
    values = {
        "/proc/meminfo": meminfo,
        "/sys/fs/cgroup/memory.max": str(4 * gib),
        "/sys/fs/cgroup/memory.current": str(gib),
    }
    monkeypatch.setattr(validate, "_read_text", lambda path: values.get(path))
    assert validate._memory_snapshot() == (4 * gib, 3 * gib)


def test_default_validator_is_resource_aware_with_serial_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parser = validate._build_parser()
    monkeypatch.setattr(validate, "_resource_worker_count", lambda maximum=None: 4)
    assert validate._pytest_command(parser.parse_args(()), parser) == (
        "uv",
        "run",
        "pytest",
        "-n",
        "4",
        "--dist=loadfile",
    )

    capped = parser.parse_args(("--pytest-maxprocesses", "2"))
    monkeypatch.setattr(
        validate,
        "_resource_worker_count",
        lambda maximum=None: min(4, maximum) if maximum is not None else 4,
    )
    assert validate._pytest_command(capped, parser) == (
        "uv",
        "run",
        "pytest",
        "-n",
        "2",
        "--dist=loadfile",
    )
    loadscope = parser.parse_args(("--pytest-dist", "loadscope"))
    assert validate._pytest_command(loadscope, parser)[-1] == "--dist=loadscope"

    monkeypatch.setattr(validate, "_resource_worker_count", lambda maximum=None: 1)
    assert validate._pytest_command(parser.parse_args(()), parser) == (
        "uv",
        "run",
        "pytest",
    )


def test_ci_keeps_two_jobs_and_uses_the_same_default_resource_policy() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert workflow.count('          - "3.12"') == 1
    assert workflow.count('          - "3.13"') == 1
    assert workflow.count("uv run python scripts/validate.py --timings") == 1
    assert "--pytest-workers" not in workflow
    assert "--pytest-maxprocesses" not in workflow


def test_slice5_resource_evidence_and_handoff_are_exact() -> None:
    document = " ".join(SLICE5_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "`XDIST = ADOPTED`",
        "20 affinity CPUs",
        "8.32 GB total RAM",
        "512 MiB per worker",
        "1 GiB or 20%",
        "68.72s",
        "44.85s",
        "41.24s",
        "129.85s",
        "130.74s",
        "61.28s",
        "60.72s",
        "69.30s, or 53.2%",
        "10348 passed twice",
        "plain serial pytest command",
        "No `xdist_group` marker",
        "Phase 60 = NOT ACTIVATED",
        "VALIDATION_PERFORMANCE_INTERLUDE_SLICE6_COMPLETION_BENCHMARK_PHASE60_READINESS_ASSURANCE",
    ):
        assert evidence in document
