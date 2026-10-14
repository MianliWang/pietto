from __future__ import annotations

from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path

import pytest

import pietto
import pietto.ir
import pietto.parser_api
import pietto.semantic
from pietto._project import __all__ as project_exports
from pietto._project.discovery import discover_project_inputs
from pietto._project.model import (
    ProjectConfigPath,
    ProjectDiscoveryErrorKind,
    ProjectDiscoveryResult,
    ProjectInput,
    ProjectParseCheckResult,
    ProjectRoot,
)


def test_private_model_is_frozen_tuple_based_and_not_reexported() -> None:
    result = ProjectDiscoveryResult(
        root=ProjectRoot(path="."),
        config_path=ProjectConfigPath(path="pietto.toml"),
        inputs=(ProjectInput(path="src/main.pietto", status="selected"),),
        errors=(),
    )

    assert project_exports == ()
    for public_module in (pietto, pietto.semantic, pietto.ir):
        assert not hasattr(public_module, "ProjectDiscoveryResult")
        assert "ProjectDiscoveryResult" not in getattr(public_module, "__all__", ())

    assert is_dataclass(result)
    assert is_dataclass(result.root)
    assert is_dataclass(result.config_path)
    assert is_dataclass(result.inputs[0])
    with pytest.raises(FrozenInstanceError):
        setattr(result, "inputs", ())

    assert isinstance(result.inputs, tuple)
    assert isinstance(result.errors, tuple)
    assert result.ok is True

    parse_result = ProjectParseCheckResult(
        root=result.root,
        config_path=result.config_path,
        inputs=result.inputs,
        errors=(),
        diagnostics=(),
    )
    assert is_dataclass(parse_result)
    assert parse_result.ok is True
    assert "ProjectParseCheckResult" not in getattr(pietto, "__all__", ())
    assert not hasattr(pietto, "ProjectParseCheckResult")


def test_missing_root_and_file_as_root_return_project_root(tmp_path: Path) -> None:
    missing = discover_project_inputs(tmp_path / "missing")

    assert missing.root is None
    assert missing.config_path is None
    assert missing.inputs == ()
    assert _error_kinds(missing) == [ProjectDiscoveryErrorKind.PROJECT_ROOT]

    file_root = tmp_path / "not-a-directory"
    file_root.write_text("", encoding="utf-8")
    result = discover_project_inputs(file_root)

    assert result.root is None
    assert result.config_path is None
    assert result.inputs == ()
    assert _error_kinds(result) == [ProjectDiscoveryErrorKind.PROJECT_ROOT]
    _assert_no_absolute_paths(result, tmp_path)


def test_config_detection_does_not_parse_toml(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()

    missing_config = discover_project_inputs(root)

    assert missing_config.root == ProjectRoot(path=".")
    assert missing_config.config_path == ProjectConfigPath(path="pietto.toml")
    assert missing_config.inputs == ()
    assert _error_kinds(missing_config) == [ProjectDiscoveryErrorKind.CONFIG_READ]
    assert missing_config.errors[0].path == "pietto.toml"
    _assert_no_absolute_paths(missing_config, tmp_path)

    (root / "pietto.toml").write_text("this is not toml = [", encoding="utf-8")
    invalid_toml = discover_project_inputs(root)

    assert invalid_toml.ok is True
    assert invalid_toml.root == ProjectRoot(path=".")
    assert invalid_toml.config_path == ProjectConfigPath(path="pietto.toml")
    assert invalid_toml.inputs == ()
    assert invalid_toml.errors == ()
    _assert_no_absolute_paths(invalid_toml, tmp_path)


def test_explicit_sources_are_normalized_sorted_and_not_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "project"
    sources = root / "sources"
    sources.mkdir(parents=True)
    (root / "pietto.toml").write_text("invalid toml = [", encoding="utf-8")
    (sources / "b.pietto").write_bytes(b"\xff\xfe\x00")
    (sources / "a.pietto").write_bytes(b"\x00\xff\xfe")

    def fail_if_called(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("parse_file must not be called")

    monkeypatch.setattr(pietto.parser_api, "parse_file", fail_if_called)

    result = discover_project_inputs(
        root,
        (Path("sources") / "b.pietto", "sources/a.pietto"),
    )

    assert result.ok is True
    assert result.root == ProjectRoot(path=".")
    assert result.config_path == ProjectConfigPath(path="pietto.toml")
    assert result.inputs == (
        ProjectInput(path="sources/a.pietto", status="selected"),
        ProjectInput(path="sources/b.pietto", status="selected"),
    )
    assert result.errors == ()
    _assert_no_absolute_paths(result, tmp_path)


@pytest.mark.parametrize(
    "source_path",
    [
        "",
        ".",
        "..",
        "sources/../a.pietto",
        "../a.pietto",
        "/tmp/a.pietto",
        "C:/a.pietto",
        "C:\\a.pietto",
        "//server/share/a.pietto",
        "\\\\server\\share\\a.pietto",
        "sources\\a.pietto",
        "/sources/a.pietto",
        "sources/a.pietto/",
        "sources//a.pietto",
    ],
)
def test_invalid_project_relative_source_paths_are_rejected(
    tmp_path: Path,
    source_path: str,
) -> None:
    root = _configured_project(tmp_path)

    result = discover_project_inputs(root, (source_path,))

    assert result.inputs == ()
    assert _error_kinds(result) == [ProjectDiscoveryErrorKind.PROJECT_PATH]
    _assert_no_absolute_paths(result, tmp_path)


def test_missing_and_non_file_sources_return_source_read(tmp_path: Path) -> None:
    root = _configured_project(tmp_path)
    (root / "sources").mkdir()

    missing = discover_project_inputs(root, ("sources/missing.pietto",))
    directory = discover_project_inputs(root, ("sources",))

    assert missing.inputs == ()
    assert _error_kinds(missing) == [ProjectDiscoveryErrorKind.SOURCE_READ]
    assert missing.errors[0].path == "sources/missing.pietto"
    assert directory.inputs == ()
    assert _error_kinds(directory) == [ProjectDiscoveryErrorKind.SOURCE_READ]
    assert directory.errors[0].path == "sources"
    _assert_no_absolute_paths(missing, tmp_path)
    _assert_no_absolute_paths(directory, tmp_path)


def test_duplicate_physical_identity_is_rejected(tmp_path: Path) -> None:
    root = _configured_project(tmp_path)
    (root / "sources").mkdir()
    (root / "sources" / "a.pietto").write_text("not parsed", encoding="utf-8")

    result = discover_project_inputs(
        root,
        ("sources/a.pietto", "sources/a.pietto"),
    )

    assert result.inputs == (ProjectInput(path="sources/a.pietto", status="selected"),)
    assert _error_kinds(result) == [ProjectDiscoveryErrorKind.PROJECT_PATH]
    assert result.ok is False
    _assert_no_absolute_paths(result, tmp_path)


def test_symlink_root_escape_is_rejected(tmp_path: Path) -> None:
    root = _configured_project(tmp_path)
    outside = tmp_path / "outside.pietto"
    outside.write_text("not parsed", encoding="utf-8")
    link = root / "linked.pietto"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is not supported on this filesystem")

    result = discover_project_inputs(root, ("linked.pietto",))

    assert result.inputs == ()
    assert _error_kinds(result) == [ProjectDiscoveryErrorKind.PROJECT_PATH]
    assert result.errors[0].path == "linked.pietto"
    _assert_no_absolute_paths(result, tmp_path)


def _configured_project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    (root / "pietto.toml").write_text("invalid toml = [", encoding="utf-8")
    return root


def _error_kinds(result: ProjectDiscoveryResult) -> list[ProjectDiscoveryErrorKind]:
    return [error.kind for error in result.errors]


def _assert_no_absolute_paths(result: ProjectDiscoveryResult, tmp_path: Path) -> None:
    leaked = str(tmp_path)
    values = [
        result.root.path if result.root is not None else None,
        result.config_path.path if result.config_path is not None else None,
        *(input_.path for input_ in result.inputs),
        *(error.path for error in result.errors),
        *(error.message for error in result.errors),
    ]
    assert all(leaked not in value for value in values if value is not None)
