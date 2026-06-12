from __future__ import annotations

import ast
import hashlib
import importlib.util
import subprocess
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATE_PATH = REPO_ROOT / "scripts" / "validate.py"
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
BOUNDARY_HASH = "4c4d7423a8353ce9552e031045c0daf5cf51e9b39e545a6cfb7464e07569f3d9"


def _load_validate_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("pietto_validate", VALIDATE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validate = cast(Any, _load_validate_module())


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
        "pathlib",
        "shlex",
        "subprocess",
        "sys",
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

    assert validate.main() == 0
    assert calls == [(command, REPO_ROOT, False) for _, command in EXPECTED_GATES]

    output = capsys.readouterr().out
    for name, command in EXPECTED_GATES:
        assert f"[validate] {name}: {' '.join(command)}" in output


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

    assert validate.main() == 23
    assert calls == [command for _, command in EXPECTED_GATES[:3]]


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
    assert _sha256(REPO_ROOT / "Makefile") == (
        "dbd38c41e2af5275c379de0b88c92f3861efb90724c7de1a291e0aa007ce2db7"
    )
    assert (REPO_ROOT / ".github/workflows/ci.yml").is_file()
    assert (REPO_ROOT / "scripts" / "package_smoke.py").is_file()


def test_slice2_preserves_compiler_and_configuration_boundary_bytes() -> None:
    paths = [
        REPO_ROOT / "Makefile",
        REPO_ROOT / "grammar" / "Pietto.g4",
        REPO_ROOT / "pyproject.toml",
        REPO_ROOT / "uv.lock",
    ]
    paths.extend(
        path
        for path in (REPO_ROOT / "src" / "pietto").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )

    digest = hashlib.sha256()
    for path in sorted(paths):
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")

    assert digest.hexdigest() == BOUNDARY_HASH


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
