from __future__ import annotations

import ast
import hashlib
import importlib.util
import inspect
import io
import subprocess
import sys
import tarfile
import zipfile
from collections.abc import Iterable
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SMOKE_PATH = REPO_ROOT / "scripts" / "package_smoke.py"
BOUNDARY_HASH = "9a2f4bb13d0c7f4e5a39b066077c33495853db57f66d042244be9f3e0bf17ea8"
GOLDEN_HASH = "488f3465e3cc20999abd0b3be730788c1e83c74011fdf7cc7a52de6497d331bc"
PRIOR_SCRIPT_HASHES = {
    "scripts/validate.py": "4387101bc68e13539c74c45b595ba742ca17c9c0",
    "scripts/check_generated.py": "51081d5337e0659e73f8666ba639c0d4c3fe3a4b",
    "scripts/check_goldens.py": "1133139c95a20cc25c50f26043d0eccab74a02b1",
}


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


smoke = cast(Any, _load_module("pietto_package_smoke", SMOKE_PATH))


def test_packaging_smoke_exists_and_uses_only_standard_library_imports() -> None:
    tree = ast.parse(SMOKE_PATH.read_text(encoding="utf-8"))
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

    assert SMOKE_PATH.is_file()
    assert {module.split(".", 1)[0] for module in imported_modules} <= (
        sys.stdlib_module_names
    )


def test_smoke_uses_temporary_build_venv_and_external_scratch_directories() -> None:
    source = inspect.getsource(smoke.main)
    cli_source = inspect.getsource(smoke._smoke_installed_cli)

    assert "TemporaryDirectory" in source
    assert 'temporary_root / "dist"' in source
    assert 'temporary_root / "venv"' in source
    assert 'temporary_root / "scratch"' in source
    assert 'REPO_ROOT / "dist"' not in source
    assert "scratch_dir.relative_to(REPO_ROOT)" in cli_source
    assert "cwd=scratch_dir" in inspect.getsource(smoke._run_installed_cli)


def test_builds_sdist_and_wheel_and_installs_a_non_editable_wheel() -> None:
    source = inspect.getsource(smoke.main)

    for argument in ('"build"', '"--sdist"', '"--wheel"', '"--out-dir"'):
        assert argument in source
    assert '(sys.executable, "-m", "venv", str(venv_dir))' in source
    assert '"pip"' in source
    assert '"install"' in source
    assert '"--python"' in source
    assert "str(wheel)" in source
    assert "--editable" not in source
    assert '"-e"' not in source


def test_wheel_and_sdist_inventory_metadata_and_entry_point_are_checked(
    tmp_path: Path,
) -> None:
    contract = smoke.ProjectContract(
        name="pietto",
        version="0.1.0",
        requires_python=">=3.12",
        dependencies=("antlr4-python3-runtime>=4.13.2",),
        console_entry="pietto.cli:main",
        readme="README.md",
    )
    wheel = tmp_path / "pietto-0.1.0-py3-none-any.whl"
    sdist = tmp_path / "pietto-0.1.0.tar.gz"
    wheel_prefix = "pietto-0.1.0.dist-info"
    sdist_prefix = "pietto-0.1.0"
    metadata = _metadata_bytes()

    with zipfile.ZipFile(wheel, mode="w") as archive:
        for name in smoke._required_runtime_files("pietto"):
            archive.writestr(name, b"")
        archive.writestr(f"{wheel_prefix}/METADATA", metadata)
        archive.writestr(f"{wheel_prefix}/WHEEL", b"Wheel-Version: 1.0\n")
        archive.writestr(
            f"{wheel_prefix}/entry_points.txt",
            b"[console_scripts]\npietto = pietto.cli:main\n",
        )

    with tarfile.open(sdist, mode="w:gz") as archive:
        names = smoke._required_runtime_files(f"{sdist_prefix}/src/pietto") | {
            f"{sdist_prefix}/PKG-INFO",
            f"{sdist_prefix}/pyproject.toml",
            f"{sdist_prefix}/README.md",
        }
        for name in names:
            content = metadata if name.endswith("PKG-INFO") else b""
            info = tarfile.TarInfo(name)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))

    smoke._inspect_wheel(wheel, contract)
    smoke._inspect_sdist(sdist, contract)


def test_missing_generated_module_fails_artifact_inspection(tmp_path: Path) -> None:
    contract = smoke.ProjectContract(
        name="pietto",
        version="0.1.0",
        requires_python=">=3.12",
        dependencies=("antlr4-python3-runtime>=4.13.2",),
        console_entry="pietto.cli:main",
        readme="README.md",
    )
    wheel = tmp_path / "pietto-0.1.0-py3-none-any.whl"
    prefix = "pietto-0.1.0.dist-info"
    required = smoke._required_runtime_files("pietto") - {
        "pietto/generated/PiettoParser.py"
    }

    with zipfile.ZipFile(wheel, mode="w") as archive:
        for name in required:
            archive.writestr(name, b"")
        archive.writestr(f"{prefix}/METADATA", _metadata_bytes())
        archive.writestr(f"{prefix}/WHEEL", b"Wheel-Version: 1.0\n")
        archive.writestr(
            f"{prefix}/entry_points.txt",
            b"[console_scripts]\npietto = pietto.cli:main\n",
        )

    with pytest.raises(smoke.SmokeFailure, match="PiettoParser.py"):
        smoke._inspect_wheel(wheel, contract)


def test_installed_cli_uses_console_executable_and_reviewed_comparisons() -> None:
    source = inspect.getsource(smoke._smoke_installed_cli)

    assert "_venv_cli(venv_dir)" in source
    assert '"--version"' in source
    assert '"--help"' in source
    assert '"check"' in source
    assert '"postgres"' in source
    assert "postgres.stdout != expected_postgres" in source
    assert '"mysql"' in source
    assert '"json"' in source
    assert "json.loads(mysql.stdout)" in source
    assert "actual_mysql != expected_mysql" in source


def test_smoke_sanitizes_import_environment_and_copies_only_temp_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYTHONPATH", "/unexpected")
    monkeypatch.setenv("PYTHONHOME", "/unexpected")

    environment = smoke._clean_environment()
    copy_source = inspect.getsource(smoke._copy_smoke_inputs)

    assert "PYTHONPATH" not in environment
    assert "PYTHONHOME" not in environment
    assert environment["PYTHONNOUSERSITE"] == "1"
    assert "scratch_dir / relative_path" in copy_source
    assert "shutil.copyfile" in copy_source


def test_subprocess_failure_is_reported_with_its_exit_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(
        command: tuple[str, ...],
        *,
        cwd: Path,
        check: bool,
        capture_output: bool,
        env: dict[str, str] | None,
    ) -> subprocess.CompletedProcess[bytes]:
        assert cwd == tmp_path
        assert check is False
        assert capture_output is False
        assert env is None
        return subprocess.CompletedProcess(command, 23)

    monkeypatch.setattr(smoke.subprocess, "run", fake_run)

    with pytest.raises(smoke.SmokeFailure) as raised:
        smoke._run_command("failing stage", ("tool", "arg"), cwd=tmp_path)
    assert raised.value.exit_code == 23


def test_smoke_has_no_distribution_or_credential_behavior() -> None:
    source = SMOKE_PATH.read_text(encoding="utf-8").lower()

    for forbidden in (
        "tw" + "ine",
        "pyp" + "i",
        "pub" + "lish",
        "up" + "load",
        "dep" + "loy",
        "create_" + "release",
        "attest" + "ation",
        "sign" + "ing",
        "sec" + "ret",
        "pass" + "word",
        "cred" + "ential",
    ):
        assert forbidden not in source


def test_prior_scripts_and_all_compiler_packaging_boundaries_are_unchanged() -> None:
    for path, expected_hash in PRIOR_SCRIPT_HASHES.items():
        assert _git_blob_hash(REPO_ROOT / path) == expected_hash
        assert "package_smoke" not in (REPO_ROOT / path).read_text(encoding="utf-8")

    assert _sha256(REPO_ROOT / "Makefile") == (
        "dbd38c41e2af5275c379de0b88c92f3861efb90724c7de1a291e0aa007ce2db7"
    )
    for path in ("package.json", "setup.py", "setup.cfg", "MANIFEST.in"):
        assert not (REPO_ROOT / path).exists()

    boundary_paths = [
        REPO_ROOT / "Makefile",
        REPO_ROOT / "grammar" / "Pietto.g4",
        REPO_ROOT / "pyproject.toml",
        REPO_ROOT / "uv.lock",
    ]
    boundary_paths.extend(
        path
        for path in (REPO_ROOT / "src" / "pietto").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )
    assert _aggregate_hash(boundary_paths) == BOUNDARY_HASH
    assert _aggregate_hash((REPO_ROOT / "tests/fixtures/golden").iterdir()) == (
        GOLDEN_HASH
    )


def _metadata_bytes() -> bytes:
    return (
        b"Metadata-Version: 2.3\n"
        b"Name: pietto\n"
        b"Version: 0.1.0\n"
        b"Requires-Python: >=3.12\n"
        b"Requires-Dist: antlr4-python3-runtime>=4.13.2\n"
        b"Description-Content-Type: text/markdown\n"
        b"\n"
        b"# Pietto\n"
    )


def _aggregate_hash(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        if not path.is_file():
            continue
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        digest.update(relative_path.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _git_blob_hash(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
