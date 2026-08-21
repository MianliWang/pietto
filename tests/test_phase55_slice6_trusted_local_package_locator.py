from __future__ import annotations

import builtins
from dataclasses import FrozenInstanceError, fields
import hashlib
import os
from pathlib import Path
import stat

import pytest

import pietto
import pietto._project as project_package
import pietto._project.package_locator as package_locator
import pietto._project.path_trust as path_trust
from pietto._project.config import load_project_config
from pietto._project.model import (
    ProjectDiscoveryError,
    ProjectDiscoveryErrorKind,
    ProjectRootPackageActivation,
)
from pietto._project.module_carrier import ProjectCompilationMode
from pietto._project.package_locator import (
    LocatedRootPackage,
    PackageRootLocationResult,
    _locate_root_package,
)
from pietto._project.path_trust import (
    ProjectFilesystemState,
    ProjectIdentityUnavailableError,
    ProjectPinnedRoot,
)
from pietto._project.source_selection import select_project_sources


def test_dot_and_nested_directories_locate_with_exact_authority(tmp_path: Path) -> None:
    for package_path in (".", "packages/root"):
        root = tmp_path / package_path.replace("/", "-").replace(".", "dot")
        if package_path != ".":
            (root / package_path).mkdir(parents=True)
        pinned_root, activation = _authority(root, package_path)

        result = _locate_root_package(pinned_root, activation)

        assert result.ok and type(result.located_root) is LocatedRootPackage
        located = result.located_root
        assert located.pinned_root is pinned_root
        assert located.activation is activation
        assert located.activation.path == activation.path
        expected_path = (
            pinned_root.canonical_path
            if package_path == "."
            else pinned_root.canonical_path / package_path
        )
        assert located.canonical_path == expected_path
        assert type(located.directory_state) is ProjectFilesystemState
        assert stat.S_ISDIR(located.directory_state.file_type)
        if package_path == ".":
            assert located.canonical_path == pinned_root.canonical_path
            assert (
                located.directory_state.physical_identity
                == pinned_root.physical_identity
            )


def test_missing_and_non_directory_package_roots_fail_closed(tmp_path: Path) -> None:
    missing_root = tmp_path / "missing"
    missing_root.mkdir()
    missing_pinned, missing_activation = _authority(missing_root, "pkg")

    missing = _locate_root_package(missing_pinned, missing_activation)

    assert missing.located_root is None
    assert missing.errors == (_resource_error("pkg"),)

    file_root = tmp_path / "file"
    file_root.mkdir()
    (file_root / "pkg").write_text("not a directory", encoding="utf-8")
    file_pinned, file_activation = _authority(file_root, "pkg")

    non_directory = _locate_root_package(file_pinned, file_activation)

    assert non_directory.located_root is None
    assert non_directory.errors == (_resource_error("pkg"),)


def test_package_directory_symlinks_are_rejected_inside_or_outside_root(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    inside = root / "inside"
    inside.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    pinned_root, activation = _authority(root, "pkg")

    for target in (inside, outside):
        link = root / "pkg"
        link.symlink_to(target, target_is_directory=True)

        result = _locate_root_package(pinned_root, activation)

        assert result.located_root is None
        assert result.errors == (
            ProjectDiscoveryError(
                ProjectDiscoveryErrorKind.PROJECT_PATH,
                "Project package root path must not traverse symbolic links.",
                "pkg",
            ),
        )
        link.unlink()


def test_intermediate_package_directory_symlink_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    real_parent = root / "real-parent"
    (real_parent / "pkg").mkdir(parents=True)
    (root / "alias").symlink_to(real_parent, target_is_directory=True)
    pinned_root, activation = _authority(root, "alias/pkg")

    result = _locate_root_package(pinned_root, activation)

    assert result.located_root is None
    assert result.errors[0].kind is ProjectDiscoveryErrorKind.PROJECT_PATH


def test_project_root_replacement_is_project_root_error(tmp_path: Path) -> None:
    root = tmp_path / "project"
    (root / "pkg").mkdir(parents=True)
    pinned_root, activation = _authority(root, "pkg")
    root.rename(tmp_path / "displaced")
    (root / "pkg").mkdir(parents=True)

    result = _locate_root_package(pinned_root, activation)

    assert result.located_root is None
    assert result.errors == (
        ProjectDiscoveryError(
            ProjectDiscoveryErrorKind.PROJECT_ROOT,
            "Project root identity changed during project loading.",
            None,
        ),
    )


def test_package_root_replacement_during_location_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "project"
    package_root = root / "pkg"
    package_root.mkdir(parents=True)
    pinned_root, activation = _authority(root, "pkg")
    displaced = root / "displaced"
    original_open = path_trust.os.open
    replaced = False

    def replacing_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal replaced
        descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
        opened_package = path == "pkg" or (
            dir_fd is None and os.fspath(path) == os.fspath(package_root)
        )
        if opened_package and not replaced:
            replaced = True
            package_root.rename(displaced)
            package_root.mkdir()
        return descriptor

    monkeypatch.setattr(path_trust, "_supports_directory_relative_open", lambda: True)
    monkeypatch.setattr(path_trust.os, "open", replacing_open)

    result = _locate_root_package(pinned_root, activation)

    assert replaced
    assert result.located_root is None
    assert result.errors == (_resource_error("pkg"),)


def test_identity_unavailable_is_project_resource_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "project"
    (root / "pkg").mkdir(parents=True)
    pinned_root, activation = _authority(root, "pkg")

    def unavailable(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise ProjectIdentityUnavailableError(
            "Project filesystem identity is unavailable."
        )

    monkeypatch.setattr(package_locator, "_capture_pinned_directory_state", unavailable)

    result = _locate_root_package(pinned_root, activation)

    assert result.located_root is None
    assert result.errors == (
        ProjectDiscoveryError(
            ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
            "Project filesystem identity is unavailable.",
            None,
        ),
    )


def test_identity_verified_fallback_locates_without_directory_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "project"
    (root / "pkg").mkdir(parents=True)
    pinned_root, activation = _authority(root, "pkg")

    monkeypatch.setattr(path_trust, "_supports_directory_relative_open", lambda: False)

    def forbidden_open(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("fallback attempted directory open")

    monkeypatch.setattr(path_trust.os, "open", forbidden_open)

    result = _locate_root_package(pinned_root, activation)

    assert result.ok and result.located_root is not None


def test_empty_directory_location_reads_no_manifest_assets_or_content_digest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "project"
    package_root = root / "pkg"
    package_root.mkdir(parents=True)
    (package_root / "pietto-package.toml").write_text(
        'assets = [{ path = "missing.pietto" }]\n',
        encoding="utf-8",
    )
    pinned_root, activation = _authority(root, "pkg")

    def forbidden(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("package content boundary was entered")

    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(os, "read", forbidden)
    monkeypatch.setattr(os, "fdopen", forbidden)
    monkeypatch.setattr(hashlib, "sha256", forbidden)

    result = _locate_root_package(pinned_root, activation)

    assert result.ok and result.located_root is not None


def test_locator_carriers_are_private_frozen_and_canonical(tmp_path: Path) -> None:
    root = tmp_path / "project"
    (root / "pkg").mkdir(parents=True)
    pinned_root, activation = _authority(root, "pkg")
    result = _locate_root_package(pinned_root, activation)

    assert result.ok and result.located_root is not None
    located = result.located_root
    assert tuple(field.name for field in fields(located)) == (
        "pinned_root",
        "activation",
        "canonical_path",
        "directory_state",
    )
    assert hasattr(type(located), "__slots__") and not hasattr(located, "__dict__")
    assert package_locator.__all__ == ()
    for name in (
        "LocatedRootPackage",
        "PackageRootLocationResult",
        "_locate_root_package",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(project_package, name)
    with pytest.raises(TypeError):
        LocatedRootPackage()  # pyright: ignore[reportCallIssue]
    with pytest.raises(TypeError):
        PackageRootLocationResult()  # pyright: ignore[reportCallIssue]
    with pytest.raises(FrozenInstanceError):
        located.canonical_path = root  # pyright: ignore[reportAttributeAccessIssue]

    class ForeignPinnedRoot(ProjectPinnedRoot):
        pass

    class ForeignActivation(ProjectRootPackageActivation):
        pass

    foreign_root = ForeignPinnedRoot(
        display_path=pinned_root.display_path,
        invocation_path=pinned_root.invocation_path,
        canonical_path=pinned_root.canonical_path,
        physical_identity=pinned_root.physical_identity,
    )
    foreign_activation = ForeignActivation(
        activation.path,
        activation.namespace,
        activation.name,
        activation.version,
        activation.sha256,
    )
    with pytest.raises(TypeError):
        _locate_root_package(foreign_root, activation)
    with pytest.raises(TypeError):
        _locate_root_package(pinned_root, foreign_activation)


def test_schema_v1_v2_v3_and_existing_routes_remain_separate(tmp_path: Path) -> None:
    for version, mode in (
        (1, ProjectCompilationMode.LEGACY_FLAT),
        (2, ProjectCompilationMode.EXPLICIT_MODULES),
    ):
        root = tmp_path / f"v{version}"
        root.mkdir()
        (root / "pietto.toml").write_text(
            f'schema_version = {version}\n\n[sources]\ninclude = ["*.pietto"]\n',
            encoding="utf-8",
        )
        (root / "row.pietto").write_text("shape Row:\n    id: Int\n", encoding="utf-8")
        config = load_project_config(root)
        selection = select_project_sources(root, config)
        assert config.ok and config.config is not None
        assert config.config.compilation_mode is mode
        assert config.config.root_package is None
        assert selection.ok and len(selection.inputs) == 1

    root = tmp_path / "v3"
    (root / "pkg").mkdir(parents=True)
    pinned_root, activation = _authority(root, "pkg")
    located = _locate_root_package(pinned_root, activation)
    assert located.ok and located.located_root is not None
    assert located.located_root.activation is activation


def _authority(
    root: Path,
    package_path: str,
) -> tuple[ProjectPinnedRoot, ProjectRootPackageActivation]:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        "\n".join(
            (
                "schema_version = 3",
                "",
                "[package]",
                f'path = "{package_path}"',
                'namespace = "example"',
                'name = "demo"',
                'version = "1.2.3"',
                f'sha256 = "{"a" * 64}"',
                "",
            )
        ),
        encoding="utf-8",
    )
    result = load_project_config(root)
    assert result.ok and result.config is not None
    assert type(result.pinned_root) is ProjectPinnedRoot
    assert type(result.config.root_package) is ProjectRootPackageActivation
    return result.pinned_root, result.config.root_package


def _resource_error(path: str) -> ProjectDiscoveryError:
    return ProjectDiscoveryError(
        ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
        "Project package root must be an accessible existing directory and remain unchanged during location.",
        path,
    )
