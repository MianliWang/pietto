from __future__ import annotations

import ast
import hashlib
import importlib.util
import inspect
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, cast

from _phase54_active_gate2_manifest import (  # noqa: F401
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
)

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GUARD_PATH = REPO_ROOT / "scripts" / "check_generated.py"
CHECKSUM_PATH = REPO_ROOT / "tools" / "antlr-4.13.2-complete.jar.sha256"
JAR_PATH = REPO_ROOT / "tools" / "antlr-4.13.2-complete.jar"
EXPECTED_CHECKSUM = "eae2dfa119a64327444672aff63e9ec35a20180dc5b8090b7a6ab85125df4d76"
EXPECTED_INVENTORY = (
    "Pietto.interp",
    "Pietto.tokens",
    "PiettoLexer.interp",
    "PiettoLexer.py",
    "PiettoLexer.tokens",
    "PiettoParser.py",
    "PiettoVisitor.py",
    "__init__.py",
)
BOUNDARY_HASH = "c8eb68697deb410f0edae88e926d2737ded846433e8ea6fad663141b93d7e7af"
VALIDATION_GATES = (
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


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


guard = cast(Any, _load_module("pietto_check_generated", GUARD_PATH))
validate = cast(
    Any,
    _load_module(
        "pietto_validate_for_generated_guard", REPO_ROOT / "scripts/validate.py"
    ),
)


def test_checksum_and_guard_use_the_reviewed_jar_and_standard_library() -> None:
    checksum_text = CHECKSUM_PATH.read_text(encoding="ascii")

    assert checksum_text == f"{EXPECTED_CHECKSUM}\n"
    assert hashlib.sha256(JAR_PATH.read_bytes()).hexdigest() == EXPECTED_CHECKSUM

    tree = ast.parse(GUARD_PATH.read_text(encoding="utf-8"))
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
        "hashlib",
        "pathlib",
        "shlex",
        "subprocess",
        "sys",
        "tempfile",
    }


def test_checksum_failure_stops_before_any_subprocess(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_fake_repository(tmp_path, checksum="0" * 64)
    monkeypatch.setattr(guard, "REPO_ROOT", tmp_path)

    def unexpected_run(*args: object, **kwargs: object) -> None:
        raise AssertionError("subprocess must not run before checksum succeeds")

    monkeypatch.setattr(guard.subprocess, "run", unexpected_run)

    assert guard.main() == 1


@pytest.mark.parametrize("missing_path", ("jar", "checksum"))
def test_missing_provenance_input_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    missing_path: str,
) -> None:
    _write_fake_repository(tmp_path)
    target = (
        tmp_path / guard.ANTLR_JAR
        if missing_path == "jar"
        else tmp_path / guard.CHECKSUM_FILE
    )
    target.unlink()
    monkeypatch.setattr(guard, "REPO_ROOT", tmp_path)

    assert guard.main() == 1


def test_fake_regeneration_uses_temp_output_and_exact_inventory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tracked_files = _write_fake_repository(tmp_path)
    monkeypatch.setattr(guard, "REPO_ROOT", tmp_path)
    calls: list[tuple[tuple[str, ...], Path, bool]] = []

    def fake_run(
        command: tuple[str, ...],
        *,
        cwd: Path,
        check: bool,
        stdout: int | None = None,
    ) -> subprocess.CompletedProcess[bytes]:
        calls.append((command, cwd, check))
        if command[:2] == ("git", "ls-files"):
            inventory = b"\0".join(
                f"src/pietto/generated/{name}".encode() for name in EXPECTED_INVENTORY
            )
            return subprocess.CompletedProcess(command, 0, inventory + b"\0")

        output = Path(command[command.index("-o") + 1])
        assert tmp_path not in output.parents
        for name, content in tracked_files.items():
            if name == "__init__.py":
                continue
            (output / name).write_bytes(content)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(guard.subprocess, "run", fake_run)

    assert guard.main() == 0
    assert calls[0][0] == (
        "git",
        "ls-files",
        "-z",
        "--",
        "src/pietto/generated",
    )
    assert calls[1][0][:7] == (
        "java",
        "-jar",
        "tools/antlr-4.13.2-complete.jar",
        "-Dlanguage=Python3",
        "-visitor",
        "-no-listener",
        "-Xexact-output-dir",
    )
    assert all(cwd == tmp_path and check is False for _, cwd, check in calls)


def test_java_failure_is_returned_without_comparison(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_fake_repository(tmp_path)
    monkeypatch.setattr(guard, "REPO_ROOT", tmp_path)
    commands: list[tuple[str, ...]] = []

    def fake_run(
        command: tuple[str, ...],
        *,
        cwd: Path,
        check: bool,
        stdout: int | None = None,
    ) -> subprocess.CompletedProcess[bytes]:
        assert cwd == tmp_path
        assert check is False
        commands.append(command)
        if command[0] == "git":
            inventory = b"\0".join(
                f"src/pietto/generated/{name}".encode() for name in EXPECTED_INVENTORY
            )
            return subprocess.CompletedProcess(command, 0, inventory + b"\0")
        return subprocess.CompletedProcess(command, 23)

    monkeypatch.setattr(guard.subprocess, "run", fake_run)

    assert guard.main() == 23
    assert [command[0] for command in commands] == ["git", "java"]


@pytest.mark.parametrize("failure", ("missing", "extra", "bytes"))
def test_generated_inventory_and_bytes_must_match_exactly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    tracked_files = _write_fake_repository(tmp_path)
    monkeypatch.setattr(guard, "REPO_ROOT", tmp_path)

    def fake_run(
        command: tuple[str, ...],
        *,
        cwd: Path,
        check: bool,
        stdout: int | None = None,
    ) -> subprocess.CompletedProcess[bytes]:
        if command[0] == "git":
            inventory = b"\0".join(
                f"src/pietto/generated/{name}".encode() for name in EXPECTED_INVENTORY
            )
            return subprocess.CompletedProcess(command, 0, inventory + b"\0")

        output = Path(command[command.index("-o") + 1])
        for name, content in tracked_files.items():
            if name == "__init__.py":
                continue
            if failure == "missing" and name == "PiettoParser.py":
                continue
            if failure == "bytes" and name == "PiettoParser.py":
                content = b"different"
            (output / name).write_bytes(content)
        if failure == "extra":
            (output / "Unexpected.py").write_bytes(b"extra")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(guard.subprocess, "run", fake_run)

    assert guard.main() == 1


def test_guard_compares_bytes_without_downloads_or_repository_writes() -> None:
    source = GUARD_PATH.read_text(encoding="utf-8")
    compare_source = inspect.getsource(guard._compare_generated_files)

    assert "TemporaryDirectory" in source
    assert "read_bytes()" in compare_source
    assert ".stat(" not in compare_source
    assert "mtime" not in compare_source
    for forbidden in ("urllib", "requests", "curl", "wget"):
        assert forbidden not in source


def test_real_guard_runs_from_outside_the_repository(tmp_path: Path) -> None:
    result = subprocess.run(
        (sys.executable, str(GUARD_PATH)),
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "verified 8 tracked files byte-for-byte" in result.stdout


def test_slice3_guard_stays_independent_from_later_workflows() -> None:
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
    assert validate.GATES == VALIDATION_GATES
    assert all("check_generated.py" not in command for _, command in validate.GATES)
    assert "check_goldens" not in GUARD_PATH.read_text(encoding="utf-8")
    assert "package_smoke" not in GUARD_PATH.read_text(encoding="utf-8")
    assert _sha256(REPO_ROOT / "Makefile") == (
        "dbd38c41e2af5275c379de0b88c92f3861efb90724c7de1a291e0aa007ce2db7"
    )
    assert (REPO_ROOT / ".github/workflows/ci.yml").is_file()
    assert (REPO_ROOT / "scripts" / "package_smoke.py").is_file()


def test_slice3_preserves_compiler_and_configuration_boundary_bytes() -> None:
    paths = [
        REPO_ROOT / "Makefile",
        REPO_ROOT / "grammar" / "Pietto.g4",
    ]
    paths.extend(
        path
        for path in (REPO_ROOT / "src" / "pietto").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )

    digest = hashlib.sha256()
    for path in sorted(paths):
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        digest.update(relative_path.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")

    assert digest.hexdigest() == BOUNDARY_HASH


def _write_fake_repository(
    root: Path,
    *,
    checksum: str | None = None,
) -> dict[str, bytes]:
    jar_bytes = b"reviewed ANTLR jar"
    jar_path = root / "tools" / "antlr-4.13.2-complete.jar"
    jar_path.parent.mkdir(parents=True)
    jar_path.write_bytes(jar_bytes)
    expected_checksum = checksum or hashlib.sha256(jar_bytes).hexdigest()
    (root / "tools" / "antlr-4.13.2-complete.jar.sha256").write_text(
        f"{expected_checksum}\n",
        encoding="ascii",
    )
    grammar_path = root / "grammar" / "Pietto.g4"
    grammar_path.parent.mkdir()
    grammar_path.write_text("grammar Pietto;\n", encoding="utf-8")

    generated_root = root / "src" / "pietto" / "generated"
    generated_root.mkdir(parents=True)
    tracked_files = {
        name: b"" if name == "__init__.py" else f"{name}\n".encode()
        for name in EXPECTED_INVENTORY
    }
    for name, content in tracked_files.items():
        (generated_root / name).write_bytes(content)
    return tracked_files


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


_SLICE10_READER_MIGRATION_PATHS = (
    "docs/spec/phase53-partition-binding-multi-key-visibility-diagnostics-contract-v1.md",
    "src/pietto/semantic/window_partition_analysis.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
)
# Phase 53 Slice 13 reader migration.
