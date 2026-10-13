from __future__ import annotations

import os
from pathlib import Path

import pytest

from pietto._project.config import load_project_config
from pietto._project.model import ProjectDiscoveryErrorKind, ProjectInput
from pietto._project.source_selection import select_project_sources
import pietto._project.source_selection as source_selection


def test_selects_included_sources_then_applies_excludes_deterministically(
    tmp_path: Path,
) -> None:
    root = _project_root(
        tmp_path,
        include=("models/**/*.pietto", "*.pietto"),
        exclude=("models/tmp/*.pietto",),
    )
    _write(root, "root.pietto")
    _write(root, "models/z.pietto")
    _write(root, "models/a.pietto")
    _write(root, "models/tmp/skip.pietto")
    _write(root, "models/readme.txt")

    result = select_project_sources(root, load_project_config(root))

    assert result.errors == ()
    assert result.inputs == (
        ProjectInput(path="models/a.pietto", status="selected"),
        ProjectInput(path="models/z.pietto", status="selected"),
        ProjectInput(path="root.pietto", status="selected"),
    )


def test_forwards_config_load_errors_without_selecting_sources(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()

    result = select_project_sources(root, load_project_config(root))

    assert result.inputs == ()
    assert [error.kind for error in result.errors] == [
        ProjectDiscoveryErrorKind.CONFIG_READ
    ]
    assert result.root is not None
    assert result.config_path is not None


def test_schema_v3_package_config_returns_before_candidate_discovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "pietto.toml").write_text(
        """
        schema_version = 3

        [package]
        path = "."
        namespace = "example"
        name = "demo"
        version = "release"
        sha256 = "pin"
        """,
        encoding="utf-8",
    )
    config_result = load_project_config(root)

    def unexpected_discovery(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("package mode must not discover project source paths")

    monkeypatch.setattr(
        source_selection, "_discover_candidate_paths", unexpected_discovery
    )
    result = select_project_sources(root, config_result)

    assert result.inputs == result.modules == ()
    assert result.selected_input_index is None
    assert [(error.kind, error.message) for error in result.errors] == [
        (
            ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
            "Schema-v3 package activation does not use project source selection.",
        )
    ]


def test_schema_v4_capability_environment_returns_before_candidate_discovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "schema-v4"
    root.mkdir()
    (root / "pietto.toml").write_text(
        """
        schema_version = 4

        [package]
        path = "."
        namespace = "example"
        name = "demo"
        version = "release"
        sha256 = "pin"

        [capability_environment]
        """,
        encoding="utf-8",
    )
    config_result = load_project_config(root)

    def unexpected_discovery(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("schema-v4 mode must not discover project source paths")

    monkeypatch.setattr(
        source_selection,
        "_discover_candidate_paths",
        unexpected_discovery,
    )
    result = select_project_sources(root, config_result)

    assert result.inputs == result.modules == ()
    assert result.selected_input_index is None
    assert [(error.kind, error.message) for error in result.errors] == [
        (
            ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
            "Schema-v4 capability environment does not use project source selection.",
        )
    ]


def test_empty_final_source_set_is_project_glob_error(tmp_path: Path) -> None:
    root = _project_root(
        tmp_path,
        include=("models/**/*.pietto",),
        exclude=("models/**/*.pietto",),
    )
    _write(root, "models/a.pietto")

    result = select_project_sources(root, load_project_config(root))

    assert result.inputs == ()
    assert [(error.kind, error.path) for error in result.errors] == [
        (ProjectDiscoveryErrorKind.PROJECT_GLOB, None)
    ]


def test_hidden_paths_require_hidden_pattern_segments(tmp_path: Path) -> None:
    root = _project_root(
        tmp_path,
        include=("models/**/*.pietto", ".hidden/**/*.pietto"),
    )
    _write(root, "models/.ignored/skip.pietto")
    _write(root, ".hidden/keep.pietto")
    _write(root, "models/keep.pietto")

    result = select_project_sources(root, load_project_config(root))

    assert result.errors == ()
    assert result.inputs == (
        ProjectInput(path=".hidden/keep.pietto", status="selected"),
        ProjectInput(path="models/keep.pietto", status="selected"),
    )


def test_uses_custom_selection_without_path_glob_or_source_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _project_root(tmp_path, include=("models/*.pietto",))
    _write_bytes(root, "models/bad.pietto", b"\xff")
    config_result = load_project_config(root)

    def fail_path_operation(_self: Path, *_args: object, **_kwargs: object) -> object:
        pytest.fail("source selection must not call Path glob/rglob or source reads")

    monkeypatch.setattr(Path, "glob", fail_path_operation)
    monkeypatch.setattr(Path, "rglob", fail_path_operation)
    monkeypatch.setattr(Path, "read_text", fail_path_operation)
    monkeypatch.setattr(Path, "read_bytes", fail_path_operation)
    monkeypatch.setattr(Path, "open", fail_path_operation)

    result = select_project_sources(root, config_result)

    assert result.errors == ()
    assert result.inputs == (ProjectInput(path="models/bad.pietto", status="selected"),)


def test_does_not_traverse_symlink_directories(tmp_path: Path) -> None:
    root = _project_root(tmp_path, include=("linked/**/*.pietto",))
    real_directory = tmp_path / "real"
    real_directory.mkdir()
    (real_directory / "a.pietto").write_text("not read\n", encoding="utf-8")
    linked_directory = root / "linked"
    try:
        linked_directory.symlink_to(real_directory, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlink directories are not supported: {error}")

    result = select_project_sources(root, load_project_config(root))

    assert result.inputs == ()
    assert [error.kind for error in result.errors] == [
        ProjectDiscoveryErrorKind.PROJECT_GLOB
    ]


def test_rejects_symlink_source_that_escapes_project_root(tmp_path: Path) -> None:
    root = _project_root(tmp_path, include=("models/*.pietto",))
    outside_source = tmp_path / "outside.pietto"
    outside_source.write_text("not read\n", encoding="utf-8")
    link = root / "models" / "outside.pietto"
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        link.symlink_to(outside_source)
    except OSError as error:
        pytest.skip(f"symlink files are not supported: {error}")

    result = select_project_sources(root, load_project_config(root))

    assert result.inputs == ()
    assert [(error.kind, error.path) for error in result.errors] == [
        (ProjectDiscoveryErrorKind.PROJECT_PATH, "models/outside.pietto")
    ]


def test_rejects_duplicate_physical_file_identity(tmp_path: Path) -> None:
    root = _project_root(tmp_path, include=("models/*.pietto",))
    original = _write(root, "models/a.pietto")
    alias = root / "models" / "alias.pietto"
    try:
        os.link(original, alias)
    except OSError as error:
        pytest.skip(f"hard links are not supported: {error}")

    result = select_project_sources(root, load_project_config(root))

    assert result.inputs == (ProjectInput(path="models/a.pietto", status="selected"),)
    assert [(error.kind, error.path) for error in result.errors] == [
        (ProjectDiscoveryErrorKind.PROJECT_PATH, "models/alias.pietto")
    ]


def _project_root(
    tmp_path: Path,
    *,
    include: tuple[str, ...],
    exclude: tuple[str, ...] = (),
) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    config_text = (
        "schema_version = 1\n\n"
        "[sources]\n"
        f"include = {_toml_array(include)}\n"
        f"exclude = {_toml_array(exclude)}\n"
    )
    (root / "pietto.toml").write_text(config_text, encoding="utf-8")
    return root


def _toml_array(values: tuple[str, ...]) -> str:
    return "[" + ", ".join(f'"{value}"' for value in values) + "]"


def _write(root: Path, relative_path: str) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not read\n", encoding="utf-8")
    return path


def _write_bytes(root: Path, relative_path: str, content: bytes) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path
