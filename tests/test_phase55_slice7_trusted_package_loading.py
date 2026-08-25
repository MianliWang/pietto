from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace
import hashlib
import os
from pathlib import Path
import struct

import pytest

import pietto
import pietto._project as project_package
import pietto._project.package_loader as package_loader
from pietto._project.model import (
    ProjectDiscoveryErrorKind,
    ProjectRootPackageActivation,
)
from pietto._project.module_carrier import ProjectModuleIdentity
from pietto._project.package_loader import (
    PACKAGE_CONTENT_DOMAIN,
    LoadedRootPackage,
    PackageFileSnapshot,
    PackageLoadResult,
    PackageParsedModule,
    _compute_package_content_sha256,
    _load_root_package,
)
from pietto._project.package_locator import LocatedRootPackage, _locate_root_package
from pietto._project.path_trust import ProjectPinnedRoot, _pin_project_root
from pietto.errors import Severity


_MANIFEST_PATH = "pietto-package.toml"
_VALID_SOURCE_A = b"shape Alpha:\n    id: Int\n"
_VALID_SOURCE_B = b"shape Beta:\n    value: Text\n"


def test_d1_exact_domain_lengths_order_and_known_vector() -> None:
    records = (("a.pietto", b"x"),)
    expected_stream = (
        b"pietto-package-content-v1\0"
        + struct.pack(">Q", len(_MANIFEST_PATH.encode()))
        + _MANIFEST_PATH.encode()
        + struct.pack(">Q", 1)
        + b"m"
        + struct.pack(">Q", len(b"a.pietto"))
        + b"a.pietto"
        + struct.pack(">Q", 1)
        + b"x"
    )

    assert PACKAGE_CONTENT_DOMAIN == b"pietto-package-content-v1\0"
    assert (
        _compute_package_content_sha256(b"m", records)
        == hashlib.sha256(expected_stream).hexdigest()
    )
    assert hashlib.sha256(expected_stream).hexdigest() == (
        "62b708416f5e2dfda700fe87dadeeb9a578e2b627f4585b8eac08c47745ef664"
    )
    assert expected_stream[len(PACKAGE_CONTENT_DOMAIN) :][:8] == struct.pack(
        ">Q", len(_MANIFEST_PATH.encode())
    )


def test_d1_is_sensitive_only_to_logical_order_paths_and_exact_bytes() -> None:
    manifest = b"manifest\r\n"
    first = (("z.pietto", b"z\n"), ("a.pietto", b"a\n"))
    digest = _compute_package_content_sha256(manifest, first)

    assert digest != _compute_package_content_sha256(manifest, tuple(reversed(first)))
    assert digest != _compute_package_content_sha256(
        manifest, (("x.pietto", b"z\n"), first[1])
    )
    assert digest != _compute_package_content_sha256(
        manifest, (("z.pietto", b"z\r\n"), first[1])
    )
    assert digest != _compute_package_content_sha256(b"manifest\n", first)


def test_valid_package_loads_exact_bytes_and_package_owned_modules_in_manifest_order(
    tmp_path: Path,
) -> None:
    assets = (
        ("z.pietto", _VALID_SOURCE_A),
        ("nested/a.pietto", _VALID_SOURCE_B),
    )
    manifest = _manifest(
        assets=tuple(path for path, _ in assets),
        dependencies=(("dep", "missing", "1.0.0", "b" * 64, "deps/missing"),),
    )
    located = _package(
        tmp_path / "project",
        package_path="vendor/demo",
        manifest=manifest,
        assets=assets,
        extra_files=(("undeclared.pietto", b"not valid Pietto\x80"),),
    )

    result = _load_root_package(located)

    assert result.ok and type(result.loaded_package) is LoadedRootPackage
    loaded = result.loaded_package
    assert loaded.located_root is located
    assert loaded.manifest_snapshot.located_root is located
    assert loaded.manifest_snapshot.logical_path == _MANIFEST_PATH
    assert loaded.manifest_snapshot.content == manifest
    assert loaded.content_digest == located.activation.sha256
    assert tuple(snapshot.logical_path for snapshot in loaded.asset_snapshots) == (
        "z.pietto",
        "nested/a.pietto",
    )
    assert tuple(module.identity.path for module in loaded.modules) == (
        "z.pietto",
        "nested/a.pietto",
    )
    assert tuple(module.position for module in loaded.modules) == (0, 1)
    assert tuple(module.script.span.path for module in loaded.modules) == (
        "z.pietto",
        "nested/a.pietto",
    )
    for position, module in enumerate(loaded.modules):
        assert type(module.identity) is ProjectModuleIdentity
        assert module.catalog is loaded.catalog
        assert module.asset is loaded.catalog.assets[position]
        assert module.source is loaded.asset_snapshots[position]
    assert loaded.catalog.root_package.manifest.dependencies[0].path == "deps/missing"
    assert result.errors == result.diagnostics == ()


def test_identical_content_is_host_location_independent(tmp_path: Path) -> None:
    assets = (("main.pietto", _VALID_SOURCE_A),)
    manifest = _manifest(assets=("main.pietto",))
    first = _package(
        tmp_path / "one",
        package_path="pkg",
        manifest=manifest,
        assets=assets,
    )
    second = _package(
        tmp_path / "two",
        package_path="other/location",
        manifest=manifest,
        assets=assets,
    )

    first_result = _load_root_package(first)
    second_result = _load_root_package(second)

    assert first_result.ok and second_result.ok
    assert first_result.loaded_package is not None
    assert second_result.loaded_package is not None
    assert first_result.loaded_package.content_digest == (
        second_result.loaded_package.content_digest
    )
    assert first_result.loaded_package.located_root.canonical_path != (
        second_result.loaded_package.located_root.canonical_path
    )


@pytest.mark.parametrize("shape", ("missing", "directory", "symlink"))
def test_manifest_leaf_failures_are_closed_and_package_local(
    tmp_path: Path,
    shape: str,
) -> None:
    root = tmp_path / shape
    package_root = root / "pkg"
    package_root.mkdir(parents=True)
    manifest_path = package_root / _MANIFEST_PATH
    if shape == "directory":
        manifest_path.mkdir()
    elif shape == "symlink":
        outside = tmp_path / "outside.toml"
        outside.write_bytes(_manifest(assets=("a.pietto",)))
        manifest_path.symlink_to(outside)
    located = _locate(root, package_root, sha256="a" * 64)

    result = _load_root_package(located)

    assert not result.ok and result.loaded_package is None
    assert result.errors[0].kind is ProjectDiscoveryErrorKind.CONFIG_READ
    assert result.errors[0].path == _MANIFEST_PATH
    assert str(tmp_path) not in (result.errors[0].path or "")


@pytest.mark.parametrize("shape", ("missing", "directory", "symlink"))
def test_asset_leaf_failures_are_closed_and_package_local(
    tmp_path: Path,
    shape: str,
) -> None:
    root = tmp_path / shape
    package_root = root / "pkg"
    package_root.mkdir(parents=True)
    asset_path = "models/main.pietto"
    manifest = _manifest(assets=(asset_path,))
    (package_root / _MANIFEST_PATH).write_bytes(manifest)
    physical_asset = package_root / asset_path
    physical_asset.parent.mkdir()
    if shape == "directory":
        physical_asset.mkdir()
    elif shape == "symlink":
        outside = tmp_path / "outside.pietto"
        outside.write_bytes(_VALID_SOURCE_A)
        physical_asset.symlink_to(outside)
    located = _locate(
        root,
        package_root,
        sha256=_independent_digest(manifest, ((asset_path, _VALID_SOURCE_A),)),
    )

    result = _load_root_package(located)

    assert not result.ok and result.loaded_package is None
    assert result.errors[0].kind is ProjectDiscoveryErrorKind.SOURCE_READ
    assert result.errors[0].path == asset_path
    assert str(tmp_path) not in (result.errors[0].path or "")


def test_asset_parent_symlink_traversal_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "project"
    package_root = root / "pkg"
    package_root.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "main.pietto").write_bytes(_VALID_SOURCE_A)
    (package_root / "models").symlink_to(outside, target_is_directory=True)
    manifest = _manifest(assets=("models/main.pietto",))
    (package_root / _MANIFEST_PATH).write_bytes(manifest)
    located = _locate(root, package_root, sha256="a" * 64)

    result = _load_root_package(located)

    assert not result.ok
    assert result.errors[0].kind is ProjectDiscoveryErrorKind.PROJECT_PATH
    assert result.errors[0].path == "models/main.pietto"


def test_distinct_declared_paths_cannot_alias_one_physical_file(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    package_root = root / "pkg"
    package_root.mkdir(parents=True)
    manifest = _manifest(assets=("a.pietto", "b.pietto"))
    (package_root / _MANIFEST_PATH).write_bytes(manifest)
    first = package_root / "a.pietto"
    first.write_bytes(_VALID_SOURCE_A)
    os.link(first, package_root / "b.pietto")
    located = _locate(root, package_root, sha256="a" * 64)

    result = _load_root_package(located)

    assert not result.ok and result.loaded_package is None
    assert result.errors == (
        package_loader._error(
            ProjectDiscoveryErrorKind.PROJECT_PATH,
            "Package asset path aliases an earlier declared physical file.",
            "b.pietto",
        ),
    )


@pytest.mark.parametrize("failure", ("structural", "root", "typed"))
def test_manifest_validation_failures_stop_before_asset_reads(
    tmp_path: Path,
    failure: str,
) -> None:
    root = tmp_path / failure
    package_root = root / "pkg"
    package_root.mkdir(parents=True)
    if failure == "structural":
        manifest = _manifest(assets=("missing.pietto",)).replace(
            b"schema_version = 1",
            b"schema_version = 3",
        )
    elif failure == "root":
        manifest = _manifest(assets=("missing.pietto",), namespace="other")
    else:
        manifest = _manifest(
            assets=("missing.pietto",),
            asset_kind="future_kind",
        )
    (package_root / _MANIFEST_PATH).write_bytes(manifest)
    located = _locate(root, package_root, sha256="a" * 64)

    result = _load_root_package(located)

    assert not result.ok
    assert all(
        error.kind is ProjectDiscoveryErrorKind.CONFIG_SCHEMA for error in result.errors
    )
    assert all(error.path != "missing.pietto" for error in result.errors)


def test_matching_pin_succeeds_and_mismatch_never_enters_parser(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assets = (("main.pietto", _VALID_SOURCE_A),)
    manifest = _manifest(assets=("main.pietto",))
    matching = _package(
        tmp_path / "matching",
        package_path="pkg",
        manifest=manifest,
        assets=assets,
    )
    mismatch = _package(
        tmp_path / "mismatch",
        package_path="pkg",
        manifest=manifest,
        assets=assets,
        sha256="0" * 64,
    )

    assert _load_root_package(matching).ok

    def forbidden_parser(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("digest mismatch entered parser")

    monkeypatch.setattr(package_loader.parser_api, "parse_source", forbidden_parser)
    result = _load_root_package(mismatch)

    assert not result.ok and result.loaded_package is None
    assert result.errors[0].kind is ProjectDiscoveryErrorKind.PROJECT_RESOURCE
    assert result.errors[0].path == _MANIFEST_PATH
    assert result.diagnostics == ()


def test_matching_digest_invalid_utf8_fails_before_parse(tmp_path: Path) -> None:
    assets = (("bad.pietto", b"\xff"),)
    manifest = _manifest(assets=("bad.pietto",))
    located = _package(
        tmp_path / "project",
        package_path="pkg",
        manifest=manifest,
        assets=assets,
    )

    result = _load_root_package(located)

    assert not result.ok and result.loaded_package is None
    assert result.errors[0].kind is ProjectDiscoveryErrorKind.SOURCE_READ
    assert result.errors[0].path == "bad.pietto"
    assert result.diagnostics == ()


def test_parser_diagnostics_are_package_local_and_prevent_success(
    tmp_path: Path,
) -> None:
    assets = (("bad.pietto", b"shape Broken:\n  bad\n"),)
    manifest = _manifest(assets=("bad.pietto",))
    located = _package(
        tmp_path / "project",
        package_path="vendor/demo",
        manifest=manifest,
        assets=assets,
    )

    result = _load_root_package(located)

    assert not result.ok and result.loaded_package is None
    assert result.diagnostics
    assert any(
        diagnostic.severity is Severity.ERROR for diagnostic in result.diagnostics
    )
    assert all(
        diagnostic.location.path == "bad.pietto" for diagnostic in result.diagnostics
    )
    assert all(
        str(tmp_path) not in str(diagnostic.location.path)
        for diagnostic in result.diagnostics
    )


def test_manifest_and_asset_byte_limits_are_enforced_before_digest(
    tmp_path: Path,
) -> None:
    manifest_root = tmp_path / "manifest"
    manifest_package = manifest_root / "pkg"
    manifest_package.mkdir(parents=True)
    (manifest_package / _MANIFEST_PATH).write_bytes(b"x" * 1_048_577)
    manifest_located = _locate(manifest_root, manifest_package, sha256="a" * 64)
    manifest_result = _load_root_package(manifest_located)
    assert not manifest_result.ok
    assert "1048576" in manifest_result.errors[0].message

    asset = ("large.pietto", b"x" * 1_048_577)
    manifest = _manifest(assets=(asset[0],))
    asset_located = _package(
        tmp_path / "asset",
        package_path="pkg",
        manifest=manifest,
        assets=(asset,),
    )
    asset_result = _load_root_package(asset_located)
    assert not asset_result.ok
    assert asset_result.errors[0].path == asset[0]
    assert "1048576" in asset_result.errors[0].message


@pytest.mark.parametrize("target", ("manifest", "asset"))
def test_read_mutation_observed_by_filesystem_state_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
) -> None:
    assets = (("main.pietto", _VALID_SOURCE_A),)
    manifest = _manifest(assets=("main.pietto",))
    located = _package(
        tmp_path / target,
        package_path="pkg",
        manifest=manifest,
        assets=assets,
    )
    original_fstat = package_loader._fstat_state
    calls = 0
    mutation_call = 2 if target == "manifest" else 4

    def changed(file_descriptor: int) -> object:
        nonlocal calls
        calls += 1
        state = original_fstat(file_descriptor)
        return (
            replace(state, mtime_ns=state.mtime_ns + 1)
            if calls == mutation_call
            else state
        )

    monkeypatch.setattr(package_loader, "_fstat_state", changed)

    result = _load_root_package(located)

    assert not result.ok and result.loaded_package is None
    expected_path = _MANIFEST_PATH if target == "manifest" else "main.pietto"
    assert result.errors[0].path == expected_path
    assert "changed while being read" in result.errors[0].message


@pytest.mark.parametrize("target", ("project", "package"))
def test_project_and_package_root_replacement_are_rejected(
    tmp_path: Path,
    target: str,
) -> None:
    assets = (("main.pietto", _VALID_SOURCE_A),)
    manifest = _manifest(assets=("main.pietto",))
    root = tmp_path / target
    located = _package(
        root,
        package_path="pkg",
        manifest=manifest,
        assets=assets,
    )
    if target == "project":
        root.rename(tmp_path / "displaced-project")
        (root / "pkg").mkdir(parents=True)
    else:
        package_root = root / "pkg"
        package_root.rename(root / "displaced-package")
        package_root.mkdir()

    result = _load_root_package(located)

    assert not result.ok and result.loaded_package is None
    expected_kind = (
        ProjectDiscoveryErrorKind.PROJECT_ROOT
        if target == "project"
        else ProjectDiscoveryErrorKind.PROJECT_RESOURCE
    )
    assert result.errors[0].kind is expected_kind
    assert result.errors[0].path is None


def test_package_root_replacement_during_parse_is_rejected_before_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assets = (("main.pietto", _VALID_SOURCE_A),)
    manifest = _manifest(assets=("main.pietto",))
    root = tmp_path / "project"
    located = _package(
        root,
        package_path="pkg",
        manifest=manifest,
        assets=assets,
    )
    package_root = root / "pkg"
    original_parse = package_loader.parser_api.parse_source

    def replacing_parse(*args: object, **kwargs: object) -> object:
        result = original_parse(*args, **kwargs)  # type: ignore[arg-type]
        package_root.rename(root / "displaced")
        package_root.mkdir()
        return result

    monkeypatch.setattr(package_loader.parser_api, "parse_source", replacing_parse)

    result = _load_root_package(located)

    assert not result.ok and result.loaded_package is None
    assert result.errors[0].kind is ProjectDiscoveryErrorKind.PROJECT_RESOURCE
    assert result.errors[0].path is None


def test_loader_carriers_are_private_canonical_and_exactly_root_bound(
    tmp_path: Path,
) -> None:
    assets = (("main.pietto", _VALID_SOURCE_A),)
    manifest = _manifest(assets=("main.pietto",))
    located = _package(
        tmp_path / "project",
        package_path="pkg",
        manifest=manifest,
        assets=assets,
    )
    result = _load_root_package(located)

    assert result.ok and result.loaded_package is not None
    loaded = result.loaded_package
    assert tuple(field.name for field in fields(loaded)) == (
        "located_root",
        "manifest_snapshot",
        "catalog",
        "asset_snapshots",
        "content_digest",
        "modules",
    )
    assert loaded.located_root is located
    assert loaded.modules[0].catalog is loaded.catalog
    assert loaded.modules[0].asset is loaded.catalog.assets[0]
    for value in (
        loaded,
        loaded.manifest_snapshot,
        loaded.modules[0],
        result,
    ):
        assert hasattr(type(value), "__slots__") and not hasattr(value, "__dict__")
    with pytest.raises(TypeError):
        LoadedRootPackage()  # pyright: ignore[reportCallIssue]
    with pytest.raises(TypeError):
        PackageFileSnapshot()  # pyright: ignore[reportCallIssue]
    with pytest.raises(TypeError):
        PackageParsedModule()  # pyright: ignore[reportCallIssue]
    with pytest.raises(TypeError):
        PackageLoadResult()  # pyright: ignore[reportCallIssue]
    with pytest.raises(FrozenInstanceError):
        loaded.content_digest = "0" * 64  # pyright: ignore[reportAttributeAccessIssue]

    class ForeignLocatedRoot(LocatedRootPackage):
        pass

    foreign = object.__new__(ForeignLocatedRoot)
    for field_name in (
        "pinned_root",
        "activation",
        "canonical_path",
        "directory_state",
    ):
        object.__setattr__(foreign, field_name, getattr(located, field_name))
    with pytest.raises(TypeError):
        _load_root_package(foreign)

    assert package_loader.__all__ == ()
    for name in (
        "LoadedRootPackage",
        "PackageFileSnapshot",
        "PackageParsedModule",
        "PackageLoadResult",
        "_load_root_package",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(project_package, name)


def _package(
    root: Path,
    *,
    package_path: str,
    manifest: bytes,
    assets: tuple[tuple[str, bytes], ...],
    sha256: str | None = None,
    extra_files: tuple[tuple[str, bytes], ...] = (),
) -> LocatedRootPackage:
    package_root = root if package_path == "." else root / package_path
    package_root.mkdir(parents=True)
    (package_root / _MANIFEST_PATH).write_bytes(manifest)
    for logical_path, content in assets:
        physical_path = package_root.joinpath(*logical_path.split("/"))
        physical_path.parent.mkdir(parents=True, exist_ok=True)
        physical_path.write_bytes(content)
    for logical_path, content in extra_files:
        physical_path = package_root.joinpath(*logical_path.split("/"))
        physical_path.parent.mkdir(parents=True, exist_ok=True)
        physical_path.write_bytes(content)
    digest = sha256 or _independent_digest(manifest, assets)
    return _locate(root, package_root, package_path=package_path, sha256=digest)


def _locate(
    root: Path,
    package_root: Path,
    *,
    package_path: str = "pkg",
    sha256: str,
) -> LocatedRootPackage:
    pinned_root = _pin_project_root(root)
    assert type(pinned_root) is ProjectPinnedRoot
    activation = ProjectRootPackageActivation(
        path=package_path,
        namespace="example",
        name="demo",
        version="1.2.3",
        sha256=sha256,
    )
    result = _locate_root_package(pinned_root, activation)
    assert result.ok and type(result.located_root) is LocatedRootPackage
    assert result.located_root.canonical_path == package_root.resolve(strict=True)
    return result.located_root


def _manifest(
    *,
    assets: tuple[str, ...],
    namespace: str = "example",
    asset_kind: str = "module_source",
    dependencies: tuple[tuple[str, str, str, str, str], ...] = (),
) -> bytes:
    lines = [
        "schema_version = 1",
        f'namespace = "{namespace}"',
        'name = "demo"',
        'version = "1.2.3"',
    ]
    for path in assets:
        lines.extend(
            (
                "",
                "[[assets]]",
                f'kind = "{asset_kind}"',
                f'path = "{path}"',
            )
        )
    for dep_namespace, name, version, sha256, path in dependencies:
        lines.extend(
            (
                "",
                "[[dependencies]]",
                f'namespace = "{dep_namespace}"',
                f'name = "{name}"',
                f'version = "{version}"',
                f'sha256 = "{sha256}"',
                f'path = "{path}"',
            )
        )
    return ("\n".join(lines) + "\n").encode()


def _independent_digest(
    manifest: bytes,
    assets: tuple[tuple[str, bytes], ...],
) -> str:
    stream = bytearray(b"pietto-package-content-v1\0")
    for path, content in ((_MANIFEST_PATH, manifest), *assets):
        path_bytes = path.encode("utf-8")
        stream.extend(struct.pack(">Q", len(path_bytes)))
        stream.extend(path_bytes)
        stream.extend(struct.pack(">Q", len(content)))
        stream.extend(content)
    return hashlib.sha256(stream).hexdigest()
