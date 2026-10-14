from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest

import _pietto_differential_process_acquisition as acquisition
import _pietto_differential_probe_batch as batch


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATE_PATH = REPO_ROOT / "scripts/validate.py"
WORKFLOW = REPO_ROOT / ".github/workflows/ci.yml"
EXPECTED_GATES = (
    ("lockfile", ("uv", "lock", "--check")),
    ("format", ("uv", "run", "ruff", "format", "--check", ".")),
    ("lint", ("uv", "run", "ruff", "check", ".")),
    ("production typing", ("uv", "run", "pyright", "--threads", "4")),
    (
        "test typing",
        (
            "uv",
            "run",
            "pyright",
            "--project",
            "pyrightconfig.tests.json",
            "--threads",
            "4",
        ),
    ),
    ("tests", ("uv", "run", "pytest")),
)
CUSTOM_SCHEDULER_TOKENS = (
    "pytest_xdist_make_scheduler",
    "xdist_group",
    "DistScheduling",
    "custom scheduler",
)


def _load_validate_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "pietto_ci_validation_workload_scheduling", VALIDATE_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validate = cast(Any, _load_validate_module())


def test_no_custom_scheduler_exists_and_the_retained_policy_is_intact() -> None:
    assert validate.GATES == EXPECTED_GATES
    assert validate.PYTEST_COMMAND == ("uv", "run", "pytest")
    assert validate.PYTEST_DIST_CHOICES == ("loadfile", "loadscope")
    assert validate.PYTEST_WORKER_MEMORY_BYTES == 1024 * 1024 * 1024
    assert validate.PYTEST_MIN_MEMORY_RESERVE_BYTES == 1024 * 1024 * 1024
    assert validate.PYTEST_MAX_RESOURCE_WORKERS == 8

    command_source = inspect.getsource(validate._pytest_command)
    assert 'dist_mode = args.pytest_dist or "loadfile"' in command_source
    assert "if worker_count == 1:\n            return PYTEST_COMMAND" in command_source

    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert workflow.count("uv run python scripts/ci_validation.py run") == 2
    for override in ("--pytest-workers", "--pytest-dist", "--pytest-maxprocesses"):
        assert override not in workflow

    scheduling_owners = (
        VALIDATE_PATH.read_text(encoding="utf-8")
        + inspect.getsource(acquisition)
        + inspect.getsource(batch)
    )
    for token in CUSTOM_SCHEDULER_TOKENS:
        assert token not in scheduling_owners
    for retained in ("worksteal", "loadgroup"):
        assert retained not in VALIDATE_PATH.read_text(encoding="utf-8")


def test_resource_worker_ceiling_bounds_every_resource_computation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gib = 1024**3
    ceiling = validate.PYTEST_MAX_RESOURCE_WORKERS

    monkeypatch.setattr(validate, "_usable_cpu_count", lambda: 64)
    monkeypatch.setattr(validate, "_memory_snapshot", lambda: (128 * gib, 96 * gib))
    assert validate._resource_worker_count() == ceiling
    assert validate._resource_worker_count() == ceiling

    monkeypatch.setattr(validate, "_memory_snapshot", lambda: (16 * gib, 6 * gib))
    assert validate._resource_worker_count() == 2

    monkeypatch.setattr(validate, "_usable_cpu_count", lambda: 1)
    monkeypatch.setattr(validate, "_memory_snapshot", lambda: (128 * gib, 96 * gib))
    assert validate._resource_worker_count() == 1

    monkeypatch.setattr(validate, "_usable_cpu_count", lambda: 64)
    assert validate._resource_worker_count(2) == 2
    assert validate._resource_worker_count(ceiling * 4) == ceiling

    monkeypatch.setattr(validate, "_memory_snapshot", lambda: (8 * gib, gib))
    assert validate._resource_worker_count() == 1
    monkeypatch.setattr(validate, "_memory_snapshot", lambda: None)
    assert validate._resource_worker_count() == 1


def test_authoritative_command_reaches_the_ceiling_without_any_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gib = 1024**3
    parser = validate._build_parser()
    arguments = parser.parse_args(())

    monkeypatch.setattr(validate, "_usable_cpu_count", lambda: 64)
    monkeypatch.setattr(validate, "_memory_snapshot", lambda: (128 * gib, 96 * gib))
    assert validate._pytest_command(arguments, parser) == (
        "uv",
        "run",
        "pytest",
        "-n",
        str(validate.PYTEST_MAX_RESOURCE_WORKERS),
        "--dist=loadfile",
    )

    monkeypatch.setattr(validate, "_memory_snapshot", lambda: None)
    assert validate._pytest_command(arguments, parser) == validate.PYTEST_COMMAND
