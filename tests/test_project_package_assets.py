from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
import inspect
import json

import pytest

import pietto
import pietto._project as project_package
from pietto._project.model import (
    ProjectDiscoveryError,
    ProjectDiscoveryErrorKind,
    ProjectRootPackageActivation,
)
from pietto._project.package_manifest import (
    PackageModuleSourceAsset,
    PackageTypedAssetValidationResult,
    TypedRootPackageAssetCatalog,
    ValidatedRootPackage,
    _normalize_package_manifest,
    _validate_root_package_manifest,
    _validate_typed_root_package_assets,
)


_MANIFEST_PATH = "pietto-package.toml"


def test_slice3_structural_unknown_kind_and_duplicate_path_still_normalize() -> None:
    result = _normalize_package_manifest(
        _activation(),
        _manifest(
            assets=(
                ("unknown-kind", "src/main.pietto"),
                ("future-kind", "src/main.pietto"),
            )
        ),
    )

    assert result.ok and result.manifest is not None
    assert tuple((asset.kind, asset.path) for asset in result.manifest.assets) == (
        ("unknown-kind", "src/main.pietto"),
        ("future-kind", "src/main.pietto"),
    )


@pytest.mark.parametrize(
    "path",
    ("a.pietto", "src/main.pietto", "nested/a.pietto", ".pietto"),
)
def test_typed_catalog_accepts_exact_module_source_paths(path: str) -> None:
    root = _validated_root(assets=(("module_source", path),))

    result = _validate_typed_root_package_assets(root)

    assert result.ok and result.catalog is not None
    assert result.catalog.root_package is root
    assert result.catalog.assets == (PackageModuleSourceAsset(path),)


@pytest.mark.parametrize(
    "kind",
    (
        "unknown-kind",
        "future-kind",
        "MODULE_SOURCE",
        "module-source",
        "source",
        "nominal_declaration",
    ),
)
def test_typed_catalog_rejects_every_other_kind(kind: str) -> None:
    root = _validated_root(assets=((kind, "a.pietto"),))

    result = _validate_typed_root_package_assets(root)

    assert not result.ok and result.catalog is None
    assert result.errors == (
        _error("Package manifest assets[0].kind must be module_source."),
    )


@pytest.mark.parametrize(
    "path",
    ("a.PIETTO", "a.pietto.txt", "a.sql", "module"),
)
def test_module_source_suffix_is_exact_lowercase(path: str) -> None:
    root = _validated_root(assets=(("module_source", path),))

    result = _validate_typed_root_package_assets(root)

    assert not result.ok and result.catalog is None
    assert result.errors == (
        _error("Package manifest assets[0].path must end with .pietto."),
    )


def test_typed_catalog_preserves_distinct_manifest_source_order() -> None:
    paths = ("z.pietto", "nested/a.pietto", "m.pietto")
    root = _validated_root(
        assets=tuple(("module_source", path) for path in paths),
    )

    result = _validate_typed_root_package_assets(root)

    assert result.ok and result.catalog is not None
    assert result.catalog.root_package is root
    assert tuple(asset.path for asset in result.catalog.assets) == paths
    assert tuple(field.name for field in fields(result.catalog)) == (
        "root_package",
        "assets",
    )


def test_same_kind_duplicate_path_is_rejected_without_deduplication() -> None:
    root = _validated_root(
        assets=(
            ("module_source", "a.pietto"),
            ("module_source", "a.pietto"),
        )
    )

    result = _validate_typed_root_package_assets(root)

    assert not result.ok and result.catalog is None
    assert result.errors == (
        _error("Package manifest assets[1].path duplicates assets[0].path."),
    )


def test_unsupported_kind_and_duplicate_path_errors_are_both_retained() -> None:
    root = _validated_root(
        assets=(
            ("module_source", "a.pietto"),
            ("unknown-kind", "a.pietto"),
        )
    )

    result = _validate_typed_root_package_assets(root)

    assert not result.ok and result.catalog is None
    assert result.errors == (
        _error("Package manifest assets[1].kind must be module_source."),
        _error("Package manifest assets[1].path duplicates assets[0].path."),
    )


def test_typed_asset_errors_are_complete_and_source_ordered() -> None:
    root = _validated_root(
        assets=(
            ("unknown-kind", "bad.sql"),
            ("module_source", "good.sql"),
            ("MODULE_SOURCE", "good.sql"),
            ("module_source", "ok.pietto"),
            ("module_source", "ok.pietto"),
        )
    )

    result = _validate_typed_root_package_assets(root)

    assert not result.ok and result.catalog is None
    assert result.errors == (
        _error("Package manifest assets[0].kind must be module_source."),
        _error("Package manifest assets[1].path must end with .pietto."),
        _error("Package manifest assets[2].kind must be module_source."),
        _error("Package manifest assets[2].path duplicates assets[1].path."),
        _error("Package manifest assets[4].path duplicates assets[3].path."),
    )


def test_dependencies_remain_ignored_and_the_exact_root_is_retained() -> None:
    dependencies = (
        (" ns ", " Name ", "not-semver", "not-a-pin", "../one"),
        (" ns ", " Name ", "not-semver", "not-a-pin", "../one"),
    )
    root = _validated_root(
        assets=(("module_source", "a.pietto"),),
        dependencies=dependencies,
    )

    result = _validate_typed_root_package_assets(root)

    assert result.ok and result.catalog is not None
    assert result.catalog.root_package is root
    assert (
        tuple(
            (
                dependency.namespace,
                dependency.name,
                dependency.version,
                dependency.sha256,
                dependency.path,
            )
            for dependency in result.catalog.root_package.manifest.dependencies
        )
        == dependencies
    )


def test_catalog_and_result_require_canonical_construction() -> None:
    root = _validated_root(assets=(("module_source", "a.pietto"),))
    result = _validate_typed_root_package_assets(root)

    assert result.ok and result.catalog is not None
    assert result.catalog.root_package is root
    assert hasattr(type(result.catalog), "__slots__")
    assert not hasattr(result.catalog, "__dict__")
    with pytest.raises(TypeError):
        TypedRootPackageAssetCatalog()  # pyright: ignore[reportCallIssue]
    with pytest.raises(TypeError):
        PackageTypedAssetValidationResult()  # pyright: ignore[reportCallIssue]
    with pytest.raises(TypeError):
        _validate_typed_root_package_assets(object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="must end with .pietto"):
        PackageModuleSourceAsset("a.sql")
    with pytest.raises(FrozenInstanceError):
        result.catalog.assets = ()  # pyright: ignore[reportAttributeAccessIssue]


def test_typed_asset_boundary_is_private_pure_and_package_local() -> None:
    source = inspect.getsource(_validate_typed_root_package_assets)

    for public_name in (
        "PackageModuleSourceAsset",
        "TypedRootPackageAssetCatalog",
        "PackageTypedAssetValidationResult",
        "_validate_typed_root_package_assets",
    ):
        assert not hasattr(pietto, public_name)
        assert not hasattr(project_package, public_name)
    for forbidden in (
        "open(",
        "hashlib",
        "pathlib",
        "ProjectModuleIdentity",
        "ProjectLogicalModule",
        "TrustedSource",
        "dependency",
    ):
        assert forbidden not in source


def _activation() -> ProjectRootPackageActivation:
    return ProjectRootPackageActivation(
        path=".",
        namespace="example",
        name="demo",
        version="1.2.3",
        sha256="a" * 64,
    )


def _validated_root(
    *,
    assets: tuple[tuple[str, str], ...],
    dependencies: tuple[tuple[str, str, str, str, str], ...] = (),
) -> ValidatedRootPackage:
    result = _validate_root_package_manifest(
        _activation(),
        _manifest(assets=assets, dependencies=dependencies),
    )
    assert result.ok and type(result.package) is ValidatedRootPackage
    return result.package


def _manifest(
    *,
    assets: tuple[tuple[str, str], ...],
    dependencies: tuple[tuple[str, str, str, str, str], ...] = (),
) -> bytes:
    lines = [
        "schema_version = 1",
        'namespace = "example"',
        'name = "demo"',
        'version = "1.2.3"',
    ]
    for kind, path in assets:
        lines.extend(
            (
                "",
                "[[assets]]",
                f"kind = {json.dumps(kind, ensure_ascii=False)}",
                f"path = {json.dumps(path, ensure_ascii=False)}",
            )
        )
    for namespace, name, version, sha256, path in dependencies:
        lines.extend(
            (
                "",
                "[[dependencies]]",
                f"namespace = {json.dumps(namespace, ensure_ascii=False)}",
                f"name = {json.dumps(name, ensure_ascii=False)}",
                f"version = {json.dumps(version, ensure_ascii=False)}",
                f"sha256 = {json.dumps(sha256, ensure_ascii=False)}",
                f"path = {json.dumps(path, ensure_ascii=False)}",
            )
        )
    return ("\n".join(lines) + "\n").encode()


def _error(message: str) -> ProjectDiscoveryError:
    return ProjectDiscoveryError(
        ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
        message,
        _MANIFEST_PATH,
    )
