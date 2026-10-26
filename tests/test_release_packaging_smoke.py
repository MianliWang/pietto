from __future__ import annotations

import ast
import inspect
import io
import json
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

import pietto.cli as cli
from _pietto_repo_package import (
    LICENSE_FILES,
    REPO_ROOT,
    SMOKE_PATH,
    license_members,
    metadata_bytes,
    smoke,
)


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
    contract = smoke._project_contract()
    sdist_prefix = f"{contract.name}-{contract.version}"
    wheel = tmp_path / f"{sdist_prefix}-py3-none-any.whl"
    sdist = tmp_path / f"{sdist_prefix}.tar.gz"
    wheel_prefix = f"{sdist_prefix}.dist-info"
    metadata = metadata_bytes()

    with zipfile.ZipFile(wheel, mode="w") as archive:
        for name in smoke._required_runtime_files("pietto"):
            archive.writestr(name, b"")
        archive.writestr(f"{wheel_prefix}/METADATA", metadata)
        archive.writestr(f"{wheel_prefix}/WHEEL", b"Wheel-Version: 1.0\n")
        for path, content in license_members().items():
            archive.writestr(f"{wheel_prefix}/licenses/{path}", content)
        archive.writestr(
            f"{wheel_prefix}/entry_points.txt",
            b"[console_scripts]\npietto = pietto.cli:main\n",
        )

    with tarfile.open(sdist, mode="w:gz") as archive:
        licenses = {f"{sdist_prefix}/{p}": c for p, c in license_members().items()}
        names = smoke._required_runtime_files(f"{sdist_prefix}/src/pietto") | {
            f"{sdist_prefix}/PKG-INFO",
            f"{sdist_prefix}/pyproject.toml",
            f"{sdist_prefix}/README.md",
            *licenses,
        }
        for name in names:
            content = metadata if name.endswith("PKG-INFO") else b""
            if name.endswith("pyproject.toml"):
                content = (REPO_ROOT / "pyproject.toml").read_bytes()
            elif name.endswith("README.md"):
                content = (REPO_ROOT / "README.md").read_bytes()
            elif name in licenses:
                content = licenses[name]
            info = tarfile.TarInfo(name)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))

    smoke._inspect_wheel(wheel, contract)
    smoke._inspect_sdist(sdist, contract)


def test_missing_generated_module_fails_artifact_inspection(tmp_path: Path) -> None:
    contract = smoke._project_contract()
    wheel = tmp_path / f"{contract.name}-{contract.version}-py3-none-any.whl"
    prefix = f"{contract.name}-{contract.version}.dist-info"
    required = smoke._required_runtime_files("pietto") - {
        "pietto/generated/PiettoParser.py"
    }

    with zipfile.ZipFile(wheel, mode="w") as archive:
        for name in required:
            archive.writestr(name, b"")
        archive.writestr(f"{prefix}/METADATA", metadata_bytes())
        archive.writestr(f"{prefix}/WHEEL", b"Wheel-Version: 1.0\n")
        for path, content in license_members().items():
            archive.writestr(f"{prefix}/licenses/{path}", content)
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
    assert '"--project"' in source
    assert '"installed CLI project check text"' in source
    assert '"installed CLI project check JSON v2"' in source
    assert '"pietto.toml"' in source
    assert "schema_version = 1" in source
    assert "models/*.pietto" in source
    assert "Project check OK: ." in source
    assert "Files checked: 1" in source
    assert '"schema_version": 2' in source
    assert '"mode": "project"' in source
    assert '"path": "models/user.pietto"' in source
    assert '"status": "parsed"' in source
    assert '"files_total": 1' in source
    assert '"files_ok": 1' in source
    assert '"files_with_errors": 0' in source
    assert '"explain"' in source
    assert "Semantic Metadata Artifact v1" in source
    assert "explain_document.get" in source
    assert '"postgres"' in source
    assert "postgres.stdout != expected_postgres" in source
    assert '"mysql"' in source
    assert '"json"' in source
    assert "json.loads(mysql.stdout)" in source
    assert "actual_mysql != expected_mysql" in source


def test_smoke_pietto_sources_check_cleanly_in_the_modern_syntax(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    explain_source = next(
        ast.literal_eval(node.value)
        for node in ast.walk(ast.parse(inspect.getsource(smoke._smoke_installed_cli)))
        if isinstance(node, ast.Assign)
        and ast.unparse(node.targets[0]) == "project_explain_source"
    )
    for name, source in (
        ("emit", smoke.PROJECT_EMIT_SOURCE),
        ("explain", explain_source.decode()),
    ):
        path = tmp_path / f"{name}.pietto"
        path.write_text(source, encoding="utf-8")
        assert cli.main(["check", str(path), "--format", "json"]) == 0
        captured = capsys.readouterr()
        assert captured.err == ""
        assert json.loads(captured.out)["diagnostics"] == []


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
    for path in (
        "scripts/validate.py",
        "scripts/check_generated.py",
        "scripts/check_goldens.py",
    ):
        assert "package_smoke" not in (REPO_ROOT / path).read_text(encoding="utf-8")

    for path in ("package.json", "setup.py", "setup.cfg", "MANIFEST.in"):
        assert not (REPO_ROOT / path).exists()


def test_project_declares_mit_and_the_reviewed_license_files() -> None:
    contract = smoke._project_contract()
    assert (contract.license, contract.license_files) == ("MIT", LICENSE_FILES)


def test_project_declares_the_reviewed_classifiers_urls_and_keywords() -> None:
    contract = smoke._project_contract()
    repository = "https://github.com/MianliWang/pietto"
    assert contract.classifiers == (
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Database",
        "Topic :: Software Development :: Compilers",
    )
    # The documentation link is pinned to the tag of the declared version.
    assert contract.urls == (
        ("Homepage", repository),
        ("Repository", repository),
        ("Documentation", f"{repository}/tree/v{contract.version}/docs"),
        ("Issues", f"{repository}/issues"),
        ("Releases", f"{repository}/releases"),
    )
    assert contract.keywords == ("sql", "dsl", "compiler", "postgresql", "mysql")
