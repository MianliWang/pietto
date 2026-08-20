from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
import hashlib
import inspect
import json
from pathlib import Path

import pytest

import pietto
import pietto._project as project_package
import pietto._project.package_manifest as package_manifest
from pietto._project.model import (
    ProjectDiscoveryError,
    ProjectDiscoveryErrorKind,
    ProjectRootPackageActivation,
)
from pietto._project.package_manifest import (
    PackageCoordinate,
    PackageIdentity,
    PackageManifest,
    PackageManifestAsset,
    PackageManifestDependency,
    PackageManifestNormalizationResult,
    PackageRootValidationResult,
    ValidatedRootPackage,
    _normalize_package_manifest,
    _validate_root_package_manifest,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_normalizes_exact_v1_root_aots_and_logical_manifest_path() -> None:
    root_result = _normalize_package_manifest(_activation(), _valid_manifest())
    nested_result = _normalize_package_manifest(
        _activation("packages/demo"),
        _valid_manifest(),
    )

    assert root_result.ok and nested_result.ok
    assert root_result.manifest_path == "pietto-package.toml"
    assert nested_result.manifest_path == "packages/demo/pietto-package.toml"
    manifest = root_result.manifest
    assert type(manifest) is PackageManifest
    assert tuple(field.name for field in fields(PackageManifestAsset)) == (
        "kind",
        "path",
    )
    assert tuple(field.name for field in fields(PackageManifestDependency)) == (
        "namespace",
        "name",
        "version",
        "sha256",
        "path",
    )
    assert tuple(field.name for field in fields(PackageManifest)) == (
        "schema_version",
        "namespace",
        "name",
        "version",
        "assets",
        "dependencies",
    )
    assert tuple(
        field.name for field in fields(PackageManifestNormalizationResult)
    ) == (
        "manifest_path",
        "manifest",
        "errors",
    )
    assert manifest == PackageManifest(
        schema_version=1,
        namespace="example",
        name="demo",
        version="not-yet-semver",
        assets=(PackageManifestAsset("unknown-kind", "src/main.pietto"),),
        dependencies=(
            PackageManifestDependency(
                "dep-ns",
                "dep-name",
                "not-yet-semver",
                "not-yet-sha256",
                "../dependencies/demo",
            ),
        ),
    )
    assert type(manifest.assets) is tuple
    assert type(manifest.dependencies) is tuple
    assert isinstance(hash(manifest), int)


def test_absent_dependencies_normalize_to_empty_tuple() -> None:
    result = _normalize_package_manifest(
        _activation(),
        _valid_manifest(dependencies=()),
    )

    assert result.ok and result.manifest is not None
    assert result.manifest.dependencies == ()
    assert type(result.manifest.dependencies) is tuple


def test_occurrence_order_multiplicity_and_nonsemantic_text_are_preserved() -> None:
    assets = (
        ("future-kind", "a.pietto"),
        ("other-kind", "b.pietto"),
        ("future-kind", "a.pietto"),
    )
    dependencies = (
        ("not slug!", "first", "v?", "pin?", "../one"),
        ("other", "second", "release", "digest", "./two"),
        ("not slug!", "first", "v?", "pin?", "../one"),
    )
    first = _normalize_package_manifest(
        _activation(),
        _valid_manifest(assets=assets, dependencies=dependencies),
    )
    equivalent = _normalize_package_manifest(
        _activation(),
        _valid_manifest(
            assets=assets,
            dependencies=dependencies,
            root_order=("version", "name", "namespace", "schema_version"),
            reverse_entry_fields=True,
            comment="same normalized value",
        ),
    )
    reordered = _normalize_package_manifest(
        _activation(),
        _valid_manifest(
            assets=assets[1:] + assets[:1],
            dependencies=dependencies,
        ),
    )

    assert first.ok and equivalent.ok and reordered.ok
    assert first.manifest == equivalent.manifest
    assert hash(first.manifest) == hash(equivalent.manifest)
    assert first.manifest != reordered.manifest
    assert first.manifest is not None
    assert tuple((item.kind, item.path) for item in first.manifest.assets) == assets
    assert (
        tuple(
            (item.namespace, item.name, item.version, item.sha256, item.path)
            for item in first.manifest.dependencies
        )
        == dependencies
    )


@pytest.mark.parametrize("size", (1_048_575, 1_048_576))
def test_manifest_byte_limit_is_inclusive(size: int) -> None:
    result = _normalize_package_manifest(_activation(), _padded_manifest(size))

    assert result.ok


def test_byte_utf8_and_toml_hard_failures_are_exact() -> None:
    over_limit = _normalize_package_manifest(
        _activation(),
        _padded_manifest(1_048_576) + b"x",
    )
    invalid_utf8 = _normalize_package_manifest(_activation(), b"\x80")
    invalid_toml = _normalize_package_manifest(
        _activation(),
        b"schema_version = 1\nschema_version = 1\n",
    )

    assert _error_kinds(over_limit) == (ProjectDiscoveryErrorKind.PROJECT_RESOURCE,)
    assert _error_kinds(invalid_utf8) == (ProjectDiscoveryErrorKind.CONFIG_PARSE,)
    assert _error_kinds(invalid_toml) == (ProjectDiscoveryErrorKind.CONFIG_PARSE,)
    for result in (over_limit, invalid_utf8, invalid_toml):
        assert not result.ok and result.manifest is None
        assert len(result.errors) == 1


@pytest.mark.parametrize(
    "replacement",
    (
        "schema_version = true",
        'schema_version = "1"',
        "schema_version = 1.0",
        "schema_version = 0",
        "schema_version = 2",
        "schema_version = 1979-05-27",
    ),
)
def test_schema_version_is_exact_non_boolean_integer_one(replacement: str) -> None:
    result = _normalize_package_manifest(
        _activation(),
        _valid_manifest().replace(b"schema_version = 1", replacement.encode(), 1),
    )

    assert not result.ok and result.manifest is None
    assert result.errors[0].kind is ProjectDiscoveryErrorKind.CONFIG_SCHEMA


def test_empty_bytes_report_every_missing_required_root_field() -> None:
    result = _normalize_package_manifest(_activation(), b"")

    assert not result.ok and result.manifest is None
    assert tuple(error.kind for error in result.errors) == (
        ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
        ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
        ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
        ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
        ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
    )
    assert tuple(error.message for error in result.errors) == (
        "Package manifest schema_version must be exact integer 1.",
        "Package manifest namespace must be a non-empty string.",
        "Package manifest name must be a non-empty string.",
        "Package manifest version must be a non-empty string.",
        "Package manifest assets must be one or more root [[assets]] entries.",
    )


@pytest.mark.parametrize(
    "field_name", ("schema_version", "namespace", "name", "version")
)
@pytest.mark.parametrize("mode", ("missing", "empty", "wrong_kind"))
def test_each_required_root_scalar_is_independently_closed(
    field_name: str,
    mode: str,
) -> None:
    result = _normalize_package_manifest(
        _activation(),
        _mutate_root_field(_valid_manifest(), field_name, mode),
    )

    assert not result.ok and result.manifest is None
    assert result.errors[0].kind is ProjectDiscoveryErrorKind.CONFIG_SCHEMA


def test_missing_assets_are_rejected() -> None:
    result = _normalize_package_manifest(
        _activation(),
        _valid_manifest(assets=()),
    )

    assert not result.ok and result.manifest is None
    assert result.errors[0].kind is ProjectDiscoveryErrorKind.CONFIG_SCHEMA


@pytest.mark.parametrize(
    ("collection", "field_name"),
    (
        ("assets", "kind"),
        ("assets", "path"),
        ("dependencies", "namespace"),
        ("dependencies", "name"),
        ("dependencies", "version"),
        ("dependencies", "sha256"),
        ("dependencies", "path"),
    ),
)
@pytest.mark.parametrize("mode", ("missing", "empty", "wrong_kind"))
def test_each_entry_field_is_independently_closed(
    collection: str,
    field_name: str,
    mode: str,
) -> None:
    result = _normalize_package_manifest(
        _activation(),
        _entry_field_manifest(collection, field_name, mode),
    )

    assert not result.ok and result.manifest is None
    assert ProjectDiscoveryErrorKind.CONFIG_SCHEMA in _error_kinds(result)


@pytest.mark.parametrize("asset_count", (1, 2, 3))
@pytest.mark.parametrize("dependency_count", (0, 1, 2, 3))
def test_valid_asset_and_dependency_cardinality_matrix(
    asset_count: int,
    dependency_count: int,
) -> None:
    assets = tuple(
        (f"kind-{index}", f"asset-{index}.pietto") for index in range(asset_count)
    )
    dependencies = tuple(
        (
            f"namespace-{index}",
            f"name-{index}",
            f"version-{index}",
            f"sha-{index}",
            f"../dependency-{index}",
        )
        for index in range(dependency_count)
    )
    result = _normalize_package_manifest(
        _activation(),
        _valid_manifest(assets=assets, dependencies=dependencies),
    )

    assert result.ok and result.manifest is not None
    assert len(result.manifest.assets) == asset_count
    assert len(result.manifest.dependencies) == dependency_count


def test_dependency_order_and_multiplicity_change_value_equality_and_hash() -> None:
    first = ("ns-1", "name-1", "v-1", "sha-1", "../one")
    second = ("ns-2", "name-2", "v-2", "sha-2", "../two")
    original = _normalize_package_manifest(
        _activation(),
        _valid_manifest(dependencies=(first, second, first)),
    )
    reordered = _normalize_package_manifest(
        _activation(),
        _valid_manifest(dependencies=(second, first, first)),
    )
    dropped = _normalize_package_manifest(
        _activation(),
        _valid_manifest(dependencies=(first, second)),
    )

    assert original.ok and reordered.ok and dropped.ok
    assert original.manifest != reordered.manifest
    assert original.manifest != dropped.manifest
    assert hash(original.manifest) != hash(reordered.manifest)
    assert hash(original.manifest) != hash(dropped.manifest)


def test_nonsemantic_whitespace_and_unicode_values_are_preserved_exactly() -> None:
    result = _normalize_package_manifest(
        _activation(),
        _valid_manifest(
            namespace="  namespace snow 雪  ",
            name=" name ",
            version=" version β ",
            assets=((" future kind 雪 ", "目录/雪.pietto"),),
            dependencies=((" ns ", " name 雪 ", " v ", " sha ", "../依赖"),),
        ),
    )

    assert result.ok and result.manifest is not None
    assert (
        result.manifest.namespace,
        result.manifest.name,
        result.manifest.version,
    ) == ("  namespace snow 雪  ", " name ", " version β ")
    assert result.manifest.assets[0] == PackageManifestAsset(
        " future kind 雪 ",
        "目录/雪.pietto",
    )
    assert result.manifest.dependencies[0] == PackageManifestDependency(
        " ns ",
        " name 雪 ",
        " v ",
        " sha ",
        "../依赖",
    )


@pytest.mark.parametrize(
    "manifest_bytes",
    (
        b'schema_version = 1\nnamespace = "ns"\nname = "name"\nversion = "v"\nassets = [{ kind = "k", path = "a" }]\n',
        b'schema_version = 1\nnamespace = "ns"\nname = "name"\nversion = "v"\nassets = []\n',
        b'schema_version = 1\nnamespace = "ns"\nname = "name"\nversion = "v"\n[assets]\nkind = "k"\npath = "a"\n',
        b'schema_version = 1\nnamespace = "ns"\nname = "name"\nversion = "v"\n[["assets"]]\nkind = "k"\npath = "a"\n',
        b'schema_version = 1\nnamespace = "ns"\nname = "name"\nversion = "v"\n[[assets.nested]]\nkind = "k"\npath = "a"\n',
    ),
)
def test_assets_require_exact_bare_root_array_of_tables(
    manifest_bytes: bytes,
) -> None:
    result = _normalize_package_manifest(_activation(), manifest_bytes)

    assert not result.ok and result.manifest is None
    assert ProjectDiscoveryErrorKind.CONFIG_SCHEMA in _error_kinds(result)


@pytest.mark.parametrize(
    "dependency_source",
    (
        'dependencies = [{ namespace = "n", name = "d", version = "v", sha256 = "s", path = "." }]',
        "dependencies = []",
        '[dependencies]\nnamespace = "n"\nname = "d"\nversion = "v"\nsha256 = "s"\npath = "."',
        '[["dependencies"]]\nnamespace = "n"\nname = "d"\nversion = "v"\nsha256 = "s"\npath = "."',
        '[[dependencies.nested]]\nnamespace = "n"\nname = "d"\nversion = "v"\nsha256 = "s"\npath = "."',
    ),
)
def test_present_dependencies_require_exact_nonempty_root_array_of_tables(
    dependency_source: str,
) -> None:
    result = _normalize_package_manifest(
        _activation(),
        _valid_manifest(dependencies=()) + dependency_source.encode() + b"\n",
    )

    assert not result.ok and result.manifest is None
    assert ProjectDiscoveryErrorKind.CONFIG_SCHEMA in _error_kinds(result)


def test_aot_source_proof_handles_multiple_entries_and_header_text_in_strings() -> None:
    manifest_bytes = b'''schema_version = 1
namespace = """
[[assets]]
"""
name = "demo"
version = "v"

[[assets]]
kind = "one"
path = "one.pietto"

[[assets]] # second real occurrence
path = "two.pietto"
kind = "two"
'''

    result = _normalize_package_manifest(_activation(), manifest_bytes)

    assert result.ok and result.manifest is not None
    assert result.manifest.namespace == "[[assets]]\n"
    assert tuple(asset.path for asset in result.manifest.assets) == (
        "one.pietto",
        "two.pietto",
    )


def test_exact_bare_aot_identity_retains_toml_header_whitespace_precedent() -> None:
    manifest_bytes = (
        'schema_version = 1\r\nnamespace = "n"\r\nname = "n"\r\n'
        'version = "v"\r\n  [[ assets ]] # exact bare key with TOML whitespace\r\n'
        'kind = "k"\r\npath = "a.pietto"\r\n'
        '\t[[ dependencies ]]\r\nnamespace = "d"\r\nname = "d"\r\n'
        'version = "v"\r\nsha256 = "s"\r\npath = "."\r\n'
    ).encode()

    result = _normalize_package_manifest(_activation(), manifest_bytes)

    assert result.ok and result.manifest is not None
    assert result.manifest.assets == (PackageManifestAsset("k", "a.pietto"),)
    assert result.manifest.dependencies == (
        PackageManifestDependency("d", "d", "v", "s", "."),
    )


@pytest.mark.parametrize(
    "literal",
    (
        '"text"',
        "1",
        "1.5",
        "true",
        "1979-05-27",
        "07:32:00",
        "1979-05-27T07:32:00Z",
        "nan",
        "+nan",
        "-nan",
        "+inf",
        "-inf",
        "[]",
        "[nan]",
        "[[nan]]",
        "{ leaf = nan }",
        "{ outer = [{ inner = [nan, +inf] }] }",
    ),
)
@pytest.mark.parametrize("location", ("top", "asset", "dependency"))
def test_exact_aot_proof_is_total_over_toml_payload_values(
    literal: str,
    location: str,
) -> None:
    result = _normalize_package_manifest(
        _activation(),
        _manifest_with_unknown_toml_value(location, literal),
    )
    manifest_path = "pietto-package.toml"
    messages = {
        "top": "Package manifest contains unsupported top-level key: future.",
        "asset": "Package manifest assets[0] contains unsupported key: future.",
        "dependency": (
            "Package manifest dependencies[0] contains unsupported key: future."
        ),
    }

    assert not result.ok and result.manifest is None
    assert result.errors == (
        ProjectDiscoveryError(
            ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
            messages[location],
            manifest_path,
        ),
    )


@pytest.mark.parametrize("collection", ("assets", "dependencies"))
def test_non_aot_forms_with_nan_remain_rejected(collection: str) -> None:
    result = _normalize_package_manifest(
        _activation(),
        _inline_collection_with_nan(collection),
    )
    manifest_path = "pietto-package.toml"

    assert not result.ok and result.manifest is None
    assert result.errors == (
        ProjectDiscoveryError(
            ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
            f"Package manifest {collection} must use exact root [[{collection}]] syntax.",
            manifest_path,
        ),
        ProjectDiscoveryError(
            ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
            f"Package manifest {collection}[0] contains unsupported key: future.",
            manifest_path,
        ),
    )


@pytest.mark.parametrize("collection", ("assets", "dependencies"))
@pytest.mark.parametrize("spelling", ("bare", "quoted", "dotted"))
def test_probe_allocation_uses_decoded_user_key_identity(
    collection: str,
    spelling: str,
) -> None:
    probe_key = f"__pietto_manifest_{collection}_probe_0__"
    result = _normalize_package_manifest(
        _activation(),
        _manifest_with_root_declarations(
            (_root_key_declaration(probe_key, spelling),),
        ),
    )

    assert not result.ok and result.manifest is None
    assert result.errors == (
        ProjectDiscoveryError(
            ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
            f"Package manifest contains unsupported top-level key: {probe_key}.",
            "pietto-package.toml",
        ),
    )


def test_probe_allocation_skips_many_occupied_keys_and_is_deterministic() -> None:
    asset_keys = tuple(
        f"__pietto_manifest_assets_probe_{position}__" for position in range(8)
    )
    dependency_keys = tuple(
        f"__pietto_manifest_dependencies_probe_{position}__" for position in range(8)
    )
    all_keys = asset_keys + dependency_keys
    declarations = tuple(
        _root_key_declaration(
            key,
            "bare" if position % 2 == 0 else "quoted",
        )
        for position, key in enumerate(reversed(all_keys))
    )
    manifest_bytes = _manifest_with_root_declarations(
        declarations,
        asset_count=3,
        dependency_count=3,
    )
    first = _normalize_package_manifest(_activation(), manifest_bytes)
    second = _normalize_package_manifest(_activation(), manifest_bytes)
    expected = tuple(
        ProjectDiscoveryError(
            ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
            f"Package manifest contains unsupported top-level key: {key}.",
            "pietto-package.toml",
        )
        for key in sorted(all_keys)
    )

    assert first.errors == second.errors == expected
    assert first.manifest is second.manifest is None
    assert all(
        first_error is not second_error
        for first_error, second_error in zip(
            first.errors,
            second.errors,
            strict=True,
        )
    )


@pytest.mark.parametrize("collection", ("assets", "dependencies"))
@pytest.mark.parametrize("child_kind", ("table", "aot"))
@pytest.mark.parametrize("quoted", (False, True))
def test_root_aot_with_child_declaration_retains_parent_source_form(
    collection: str,
    child_kind: str,
    quoted: bool,
) -> None:
    result = _normalize_package_manifest(
        _activation(),
        _manifest_with_child_declaration(collection, child_kind, quoted),
    )

    assert not result.ok and result.manifest is None
    assert result.errors == (
        ProjectDiscoveryError(
            ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
            f"Package manifest {collection}[0] contains unsupported key: meta.",
            "pietto-package.toml",
        ),
    )


def test_multiple_interleaved_parent_and_child_aots_preserve_occurrence_order() -> None:
    result = _normalize_package_manifest(
        _activation(),
        _interleaved_parent_child_manifest(),
    )
    manifest_path = "pietto-package.toml"

    assert not result.ok and result.manifest is None
    assert result.errors == (
        ProjectDiscoveryError(
            ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
            "Package manifest assets[0] contains unsupported key: meta.",
            manifest_path,
        ),
        ProjectDiscoveryError(
            ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
            "Package manifest assets[1] contains unsupported key: meta.",
            manifest_path,
        ),
        ProjectDiscoveryError(
            ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
            "Package manifest dependencies[0] contains unsupported key: meta.",
            manifest_path,
        ),
        ProjectDiscoveryError(
            ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
            "Package manifest dependencies[1] contains unsupported key: meta.",
            manifest_path,
        ),
    )


def test_multiline_fake_headers_and_multiple_real_aots_are_deterministic() -> None:
    manifest_bytes = b'''schema_version = 1
namespace = """
[[assets]]
[[dependencies]]
"""
name = "name"
version = "v"

[[assets]]
kind = "a0"
path = "a0.pietto"

[[dependencies]]
namespace = "d0"
name = "d0"
version = "v0"
sha256 = "s0"
path = "."

[[assets]]
kind = "a1"
path = "a1.pietto"

[[dependencies]]
namespace = "d1"
name = "d1"
version = "v1"
sha256 = "s1"
path = ".."
'''
    first = _normalize_package_manifest(_activation(), manifest_bytes)
    second = _normalize_package_manifest(_activation(), manifest_bytes)

    assert first == second
    assert first.ok and first.errors == () and first.manifest is not None
    assert tuple(asset.kind for asset in first.manifest.assets) == ("a0", "a1")
    assert tuple(dependency.name for dependency in first.manifest.dependencies) == (
        "d0",
        "d1",
    )


def test_aot_header_at_eof_is_classified_before_entry_validation() -> None:
    result = _normalize_package_manifest(
        _activation(),
        (b'schema_version = 1\nnamespace = "n"\nname = "n"\nversion = "v"\n[[assets]]'),
    )

    assert not result.ok and result.manifest is None
    assert tuple(error.message for error in result.errors) == (
        "Package manifest assets[0].kind must be a non-empty string.",
        "Package manifest assets[0].path must be a non-empty string.",
    )


def test_post_parse_multi_error_order_is_complete_and_field_order_invariant() -> None:
    first = _normalize_package_manifest(_activation(), _multi_error_manifest(False))
    second = _normalize_package_manifest(_activation(), _multi_error_manifest(True))

    assert not first.ok and not second.ok
    assert first.manifest is second.manifest is None
    assert first.errors == second.errors
    schema = ProjectDiscoveryErrorKind.CONFIG_SCHEMA
    path = ProjectDiscoveryErrorKind.PROJECT_PATH
    manifest_path = "pietto-package.toml"
    assert first.errors == (
        ProjectDiscoveryError(
            schema,
            "Package manifest schema_version must be exact integer 1.",
            manifest_path,
        ),
        ProjectDiscoveryError(
            schema,
            "Package manifest namespace must be a non-empty string.",
            manifest_path,
        ),
        ProjectDiscoveryError(
            schema,
            "Package manifest version must be a non-empty string.",
            manifest_path,
        ),
        ProjectDiscoveryError(
            schema,
            "Package manifest contains unsupported top-level key: unknown_a.",
            manifest_path,
        ),
        ProjectDiscoveryError(
            schema,
            "Package manifest contains unsupported top-level key: unknown_z.",
            manifest_path,
        ),
        ProjectDiscoveryError(
            schema,
            "Package manifest assets[0].kind must be a non-empty string.",
            manifest_path,
        ),
        ProjectDiscoveryError(
            schema,
            "Package manifest assets[0] contains unsupported key: unknown_a.",
            manifest_path,
        ),
        ProjectDiscoveryError(
            schema,
            "Package manifest assets[0] contains unsupported key: unknown_z.",
            manifest_path,
        ),
        ProjectDiscoveryError(
            path,
            "Package manifest assets[0].path is structurally invalid.",
            "/absolute.pietto",
        ),
        ProjectDiscoveryError(
            schema,
            "Package manifest assets[1].kind must be a non-empty string.",
            manifest_path,
        ),
        ProjectDiscoveryError(
            schema,
            "Package manifest assets[1].path must be a non-empty string.",
            manifest_path,
        ),
        ProjectDiscoveryError(
            schema,
            "Package manifest dependencies[0].namespace must be a non-empty string.",
            manifest_path,
        ),
        ProjectDiscoveryError(
            schema,
            "Package manifest dependencies[0].version must be a non-empty string.",
            manifest_path,
        ),
        ProjectDiscoveryError(
            schema,
            "Package manifest dependencies[0].sha256 must be a non-empty string.",
            manifest_path,
        ),
        ProjectDiscoveryError(
            schema,
            "Package manifest dependencies[0] contains unsupported key: extra.",
            manifest_path,
        ),
        ProjectDiscoveryError(
            path,
            "Package manifest dependencies[0].path is structurally invalid.",
            "C:/dependency",
        ),
    )


@pytest.mark.parametrize(
    "path",
    (
        "",
        "/absolute",
        "//server/share",
        "C:/drive",
        "https://example.test/path",
        "scheme:value",
        "a\\b",
        "a//b",
        "a/",
        "a\x00b",
        ".",
        "..",
        "a/./b",
        "a/../b",
    ),
)
def test_asset_path_structural_rejections(path: str) -> None:
    result = _normalize_package_manifest(
        _activation(),
        _valid_manifest(assets=(("kind", path),)),
    )

    assert not result.ok and result.manifest is None
    expected_kind = (
        ProjectDiscoveryErrorKind.CONFIG_SCHEMA
        if path == ""
        else ProjectDiscoveryErrorKind.PROJECT_PATH
    )
    assert expected_kind in _error_kinds(result)


@pytest.mark.parametrize("path", (".", "..", "./dep", "../dep", "a/../dep"))
def test_dependency_dot_segments_are_preserved(path: str) -> None:
    result = _normalize_package_manifest(
        _activation(),
        _valid_manifest(dependencies=(("ns", "name", "version", "sha", path),)),
    )

    assert result.ok and result.manifest is not None
    assert result.manifest.dependencies[0].path == path


@pytest.mark.parametrize(
    "path",
    (
        "",
        "/absolute",
        "//server/share",
        "C:/drive",
        "https://example.test/path",
        "scheme:value",
        "a\\b",
        "a//b",
        "a/",
        "a\x00b",
    ),
)
def test_dependency_common_structural_rejections(path: str) -> None:
    result = _normalize_package_manifest(
        _activation(),
        _valid_manifest(dependencies=(("ns", "name", "version", "sha", path),)),
    )

    assert not result.ok and result.manifest is None


def test_private_carriers_reject_unsupported_inputs_and_construct_fresh_values() -> (
    None
):
    asset = PackageManifestAsset("kind", "a.pietto")
    dependency = PackageManifestDependency("ns", "name", "version", "sha", ".")
    manifest = PackageManifest(1, "ns", "name", "version", (asset,), (dependency,))
    error = ProjectDiscoveryError(ProjectDiscoveryErrorKind.CONFIG_SCHEMA, "bad")
    success = _normalize_package_manifest(_activation(), _valid_manifest())
    repeated_success = _normalize_package_manifest(_activation(), _valid_manifest())
    equal_from_other_activation = _normalize_package_manifest(
        ProjectRootPackageActivation(".", "other", "pins", "remain", "separate"),
        _valid_manifest(),
    )
    failure = _normalize_package_manifest(_activation(), b"\x80")
    repeated_failure = _normalize_package_manifest(_activation(), b"\x80")

    class AssetSubclass(PackageManifestAsset):
        pass

    class DependencySubclass(PackageManifestDependency):
        pass

    class ManifestSubclass(PackageManifest):
        pass

    class ResultSubclass(PackageManifestNormalizationResult):
        pass

    class TupleSubclass(tuple):
        pass

    class ActivationSubclass(ProjectRootPackageActivation):
        pass

    assert success == equal_from_other_activation
    assert success is not equal_from_other_activation
    assert success.manifest is not equal_from_other_activation.manifest
    assert success == repeated_success
    assert hash(success) == hash(repeated_success)
    assert success is not repeated_success
    assert success.manifest is not repeated_success.manifest
    assert failure == repeated_failure
    assert hash(failure) == hash(repeated_failure)
    assert failure is not repeated_failure
    assert failure.errors[0] is not repeated_failure.errors[0]
    for value in (asset, dependency, manifest, success, failure):
        assert hasattr(type(value), "__slots__")
        assert not hasattr(value, "__dict__")
        assert isinstance(hash(value), int)

    with pytest.raises(TypeError):
        PackageManifest(1, "ns", "name", "version", [asset], ())  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        PackageManifest(
            1,
            "ns",
            "name",
            "version",
            TupleSubclass((asset,)),  # type: ignore[arg-type]
            (),
        )
    with pytest.raises(TypeError):
        AssetSubclass("kind", "a.pietto")
    with pytest.raises(TypeError):
        DependencySubclass("ns", "name", "version", "sha", ".")
    with pytest.raises(TypeError):
        ManifestSubclass(1, "ns", "name", "version", (asset,), (dependency,))
    with pytest.raises(TypeError):
        result_subclass_args = (_activation(), _valid_manifest())
        ResultSubclass(*result_subclass_args)  # pyright: ignore[reportCallIssue]
    with pytest.raises(TypeError):
        result_args = ("pietto-package.toml", manifest, (error,))
        PackageManifestNormalizationResult(*result_args)  # pyright: ignore[reportCallIssue]
    with pytest.raises(TypeError):
        _normalize_package_manifest(
            ActivationSubclass(".", "ns", "name", "version", "sha"),
            _valid_manifest(),
        )
    for foreign_bytes in (
        "text",
        bytearray(_valid_manifest()),
        memoryview(_valid_manifest()),
        {"schema_version": 1},
        [],
        asset,
        dependency,
        manifest,
        error,
    ):
        with pytest.raises(TypeError):
            _normalize_package_manifest(_activation(), foreign_bytes)  # type: ignore[arg-type]

    with pytest.raises(FrozenInstanceError):
        asset.kind = "changed"  # pyright: ignore[reportAttributeAccessIssue]
    with pytest.raises(FrozenInstanceError):
        success.manifest_path = "changed"  # pyright: ignore[reportAttributeAccessIssue]


def test_slice3_is_private_and_has_no_filesystem_or_public_integration() -> None:
    source = inspect.getsource(package_manifest)

    assert package_manifest.__all__ == ()
    assert not hasattr(package_manifest, "_normalize_document")
    assert not hasattr(package_manifest, "_normalize_input")
    for public_name in (
        "PackageManifestAsset",
        "PackageManifestDependency",
        "PackageManifest",
        "PackageManifestNormalizationResult",
        "_normalize_package_manifest",
    ):
        assert not hasattr(pietto, public_name)
        assert not hasattr(project_package, public_name)
    for forbidden in (
        "from pathlib",
        "import pathlib",
        "import os",
        "path_trust",
        "trusted_source",
        "source_selection",
        "project_check",
        "open(",
        ".resolve(",
        ".stat(",
        ".lstat(",
    ):
        assert forbidden not in source

    for path in sorted((REPO_ROOT / "src/pietto").rglob("*.py")):
        if path == Path(package_manifest.__file__):
            continue
        other_source = path.read_text(encoding="utf-8")
        assert "pietto._project.package_manifest" not in other_source
        assert "_normalize_package_manifest" not in other_source


def test_slice4_package_identity_excludes_release_pin_and_logical_path() -> None:
    identity = PackageIdentity("Exact Namespace", "snow 雪")
    same_identity = PackageIdentity("Exact Namespace", "snow 雪")

    assert identity == same_identity
    assert hash(identity) == hash(same_identity)
    assert identity != PackageIdentity("exact Namespace", "snow 雪")
    assert PackageIdentity("ns", "é") != PackageIdentity("ns", "e\u0301")
    assert PackageIdentity(" ns ", " name ").namespace == " ns "
    assert tuple(field.name for field in fields(PackageIdentity)) == (
        "namespace",
        "name",
    )

    first = _validate_root_package_manifest(
        _slice4_activation(
            namespace=identity.namespace,
            name=identity.name,
            version="1.2.3+linux",
            sha256="a" * 64,
        ),
        _slice4_manifest(
            namespace=identity.namespace,
            name=identity.name,
            version="1.2.3+linux",
        ),
    )
    second = _validate_root_package_manifest(
        _slice4_activation(
            path="packages/demo",
            namespace=identity.namespace,
            name=identity.name,
            version="1.2.3+mac",
            sha256="b" * 64,
        ),
        _slice4_manifest(
            namespace=identity.namespace,
            name=identity.name,
            version="1.2.3+mac",
        ),
    )

    assert first.ok and first.package is not None
    assert second.ok and second.package is not None
    assert first.package.coordinate.identity == second.package.coordinate.identity
    assert first.package.coordinate != second.package.coordinate
    assert first.package.content_digest_pin != second.package.content_digest_pin
    assert first.package.manifest_path != second.package.manifest_path


@pytest.mark.parametrize(
    "version",
    (
        "0.0.0",
        "1.2.3",
        "1.2.3-0",
        "1.2.3-alpha.1",
        "1.2.3+linux.01",
        "1.2.3-rc.1+linux-x.01",
    ),
)
def test_slice4_exact_semver_accepts_strict_forms(version: str) -> None:
    coordinate = PackageCoordinate(PackageIdentity("ns", "name"), version)

    assert coordinate.exact_version == version


@pytest.mark.parametrize(
    "version",
    (
        "1",
        "1.2",
        "1.2.3.4",
        "+1.2.3",
        "-1.2.3",
        "01.2.3",
        "1.02.3",
        "1.2.03",
        "1.2.3-01",
        "1.2.3-",
        "1.2.3+",
        "1.2.3-alpha..1",
        "1.2.3+build..1",
        " 1.2.3",
        "1.2.3 ",
        "1.2.3-雪",
        "v1.2.3",
        "^1.2.3",
        ">=1.2.3",
    ),
)
def test_slice4_exact_semver_rejects_non_strict_forms(version: str) -> None:
    with pytest.raises(ValueError, match="strict SemVer 2.0.0"):
        PackageCoordinate(PackageIdentity("ns", "name"), version)


def test_slice4_exact_semver_equality_includes_build_metadata() -> None:
    identity = PackageIdentity("ns", "name")

    assert PackageCoordinate(identity, "1.2.3+linux") != PackageCoordinate(
        identity,
        "1.2.3+mac",
    )


def test_slice4_accepts_matching_root_coordinate_and_declared_digest_pin() -> None:
    result = _validate_root_package_manifest(
        _slice4_activation(),
        _slice4_manifest(),
    )

    assert result.ok and type(result.package) is ValidatedRootPackage
    assert result.errors == ()
    assert result.package.manifest_path == "pietto-package.toml"
    assert result.package.coordinate == PackageCoordinate(
        PackageIdentity("example", "demo"),
        "1.2.3",
    )
    assert result.package.content_digest_pin == "a" * 64
    assert result.package.manifest is not None
    assert not hasattr(result.package, "verified_digest")


@pytest.mark.parametrize(
    "field",
    ("namespace", "name", "version"),
)
def test_slice4_rejects_each_root_coordinate_mismatch(field: str) -> None:
    activation = _slice4_activation(
        namespace="activation" if field == "namespace" else "example",
        name="activation" if field == "name" else "demo",
        version="1.2.3+activation" if field == "version" else "1.2.3",
    )
    manifest_bytes = _slice4_manifest(
        namespace="manifest" if field == "namespace" else "example",
        name="manifest" if field == "name" else "demo",
        version="1.2.3+manifest" if field == "version" else "1.2.3",
    )

    result = _validate_root_package_manifest(activation, manifest_bytes)

    assert not result.ok and result.package is None
    assert tuple(error.kind for error in result.errors) == (
        ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
    )
    assert tuple(error.message for error in result.errors) == (
        f"Project package activation {field} must exactly match package manifest {field}.",
    )


def test_slice4_reports_all_root_coordinate_mismatches_in_field_order() -> None:
    result = _validate_root_package_manifest(
        _slice4_activation(
            namespace="activation-ns",
            name="activation-name",
            version="1.2.3+activation",
        ),
        _slice4_manifest(
            namespace="manifest-ns",
            name="manifest-name",
            version="1.2.3+manifest",
        ),
    )

    assert not result.ok and result.package is None
    assert tuple(error.message for error in result.errors) == (
        "Project package activation namespace must exactly match package manifest namespace.",
        "Project package activation name must exactly match package manifest name.",
        "Project package activation version must exactly match package manifest version.",
    )


def test_slice4_semantics_run_only_after_structural_normalization_succeeds() -> None:
    activation = _slice4_activation(version="not-semver", sha256="not-a-pin")
    manifest_bytes = b"\x80"
    normalized = _normalize_package_manifest(activation, manifest_bytes)

    result = _validate_root_package_manifest(activation, manifest_bytes)

    assert not normalized.ok and not result.ok
    assert result.package is None
    assert result.errors == normalized.errors


def test_slice4_reports_complete_independent_root_semantic_errors() -> None:
    result = _validate_root_package_manifest(
        _slice4_activation(
            namespace="activation-ns",
            name="activation-name",
            version="01.2.3",
            sha256="A" * 64,
        ),
        _slice4_manifest(
            namespace="manifest-ns",
            name="manifest-name",
            version="1.2.3-01",
        ),
    )

    assert not result.ok and result.package is None
    assert tuple(error.message for error in result.errors) == (
        "Project package activation namespace must exactly match package manifest namespace.",
        "Project package activation name must exactly match package manifest name.",
        "Project package activation version must be strict SemVer 2.0.0.",
        "Package manifest version must be strict SemVer 2.0.0.",
        "Project package activation sha256 must be exactly 64 lowercase hexadecimal characters.",
    )


@pytest.mark.parametrize(
    "sha256",
    (
        "a" * 63,
        "a" * 65,
        "A" * 64,
        "g" * 64,
        "a" * 63 + " ",
    ),
)
def test_slice4_declared_digest_pin_requires_exact_lowercase_hex(
    sha256: str,
) -> None:
    result = _validate_root_package_manifest(
        _slice4_activation(sha256=sha256),
        _slice4_manifest(),
    )

    assert not result.ok and result.package is None
    assert tuple(error.message for error in result.errors) == (
        "Project package activation sha256 must be exactly 64 lowercase hexadecimal characters.",
    )


def test_slice4_declared_pin_is_not_compared_with_manifest_bytes() -> None:
    pin = "a" * 64
    first_bytes = _slice4_manifest()
    second_bytes = _slice4_manifest(comment="same package facts, different bytes")
    assert hashlib.sha256(first_bytes).hexdigest() != pin
    assert hashlib.sha256(second_bytes).hexdigest() != pin
    assert (
        hashlib.sha256(first_bytes).hexdigest()
        != hashlib.sha256(second_bytes).hexdigest()
    )

    first = _validate_root_package_manifest(
        _slice4_activation(sha256=pin),
        first_bytes,
    )
    second = _validate_root_package_manifest(
        _slice4_activation(sha256=pin),
        second_bytes,
    )

    assert first.ok and second.ok
    assert first.package is not None and second.package is not None
    assert first.package.content_digest_pin == second.package.content_digest_pin == pin


def test_slice4_dependency_values_remain_raw_ordered_and_repeated() -> None:
    first = (" ns ", " Name 雪 ", "not-semver", "not-a-pin", "../one")
    second = ("other", "second", "v?", "digest?", "./two")
    result = _validate_root_package_manifest(
        _slice4_activation(),
        _slice4_manifest(dependencies=(first, second, first)),
    )

    assert result.ok and result.package is not None
    assert tuple(
        (
            dependency.namespace,
            dependency.name,
            dependency.version,
            dependency.sha256,
            dependency.path,
        )
        for dependency in result.package.manifest.dependencies
    ) == (first, second, first)


def test_slice4_boundary_is_private_pure_and_does_not_hash_package_content() -> None:
    source = inspect.getsource(package_manifest)

    assert "hashlib" not in source
    for public_name in (
        "PackageIdentity",
        "PackageCoordinate",
        "ValidatedRootPackage",
        "PackageRootValidationResult",
        "_validate_root_package_manifest",
    ):
        assert not hasattr(pietto, public_name)
        assert not hasattr(project_package, public_name)
    with pytest.raises(TypeError):
        PackageRootValidationResult()  # pyright: ignore[reportCallIssue]


def _activation(path: str = ".") -> ProjectRootPackageActivation:
    return ProjectRootPackageActivation(
        path, "expected", "expected", "expected", "expected"
    )


def _slice4_activation(
    *,
    path: str = ".",
    namespace: str = "example",
    name: str = "demo",
    version: str = "1.2.3",
    sha256: str = "a" * 64,
) -> ProjectRootPackageActivation:
    return ProjectRootPackageActivation(path, namespace, name, version, sha256)


def _slice4_manifest(
    *,
    namespace: str = "example",
    name: str = "demo",
    version: str = "1.2.3",
    dependencies: tuple[tuple[str, str, str, str, str], ...] = (),
    comment: str | None = None,
) -> bytes:
    return _valid_manifest(
        namespace=namespace,
        name=name,
        version=version,
        dependencies=dependencies,
        comment=comment,
    )


def _valid_manifest(
    *,
    namespace: str = "example",
    name: str = "demo",
    version: str = "not-yet-semver",
    assets: tuple[tuple[str, str], ...] = (("unknown-kind", "src/main.pietto"),),
    dependencies: tuple[tuple[str, str, str, str, str], ...] = (
        (
            "dep-ns",
            "dep-name",
            "not-yet-semver",
            "not-yet-sha256",
            "../dependencies/demo",
        ),
    ),
    root_order: tuple[str, ...] = ("schema_version", "namespace", "name", "version"),
    reverse_entry_fields: bool = False,
    comment: str | None = None,
) -> bytes:
    root_values = {
        "schema_version": "1",
        "namespace": _toml_string(namespace),
        "name": _toml_string(name),
        "version": _toml_string(version),
    }
    lines = [f"{field} = {root_values[field]}" for field in root_order]
    if comment is not None:
        lines.append(f"# {comment}")
    asset_fields = ("kind", "path")
    if reverse_entry_fields:
        asset_fields = tuple(reversed(asset_fields))
    for kind, path in assets:
        values = {"kind": kind, "path": path}
        lines.extend(("", "[[assets]]"))
        lines.extend(
            f"{field} = {_toml_string(values[field])}" for field in asset_fields
        )
    dependency_fields = ("namespace", "name", "version", "sha256", "path")
    if reverse_entry_fields:
        dependency_fields = tuple(reversed(dependency_fields))
    for namespace, name, version, sha256, path in dependencies:
        values = {
            "namespace": namespace,
            "name": name,
            "version": version,
            "sha256": sha256,
            "path": path,
        }
        lines.extend(("", "[[dependencies]]"))
        lines.extend(
            f"{field} = {_toml_string(values[field])}" for field in dependency_fields
        )
    return ("\n".join(lines) + "\n").encode()


def _mutate_root_field(
    manifest_bytes: bytes,
    field_name: str,
    mode: str,
) -> bytes:
    lines = manifest_bytes.decode().splitlines()
    prefix = f"{field_name} = "
    for position, line in enumerate(lines):
        if line.startswith("[["):
            break
        if not line.startswith(prefix):
            continue
        if mode == "missing":
            del lines[position]
        elif mode == "empty":
            lines[position] = f'{field_name} = ""'
        else:
            assert mode == "wrong_kind"
            lines[position] = f"{field_name} = true"
        break
    else:  # pragma: no cover - helper contract
        raise AssertionError(field_name)
    return ("\n".join(lines) + "\n").encode()


def _entry_field_manifest(collection: str, field_name: str, mode: str) -> bytes:
    root = [
        "schema_version = 1",
        'namespace = "ns"',
        'name = "name"',
        'version = "version"',
        "",
        "[[assets]]",
    ]
    asset_values = {"kind": "kind", "path": "asset.pietto"}
    dependency_values = {
        "namespace": "dep-ns",
        "name": "dep-name",
        "version": "dep-version",
        "sha256": "dep-sha",
        "path": ".",
    }
    if collection == "assets":
        root.extend(_mutated_entry_lines(asset_values, field_name, mode))
    else:
        assert collection == "dependencies"
        root.extend(
            f"{key} = {_toml_string(value)}" for key, value in asset_values.items()
        )
        root.extend(("", "[[dependencies]]"))
        root.extend(_mutated_entry_lines(dependency_values, field_name, mode))
    return ("\n".join(root) + "\n").encode()


def _mutated_entry_lines(
    values: dict[str, str],
    field_name: str,
    mode: str,
) -> tuple[str, ...]:
    lines: list[str] = []
    for key, value in values.items():
        if key == field_name and mode == "missing":
            continue
        if key == field_name and mode == "empty":
            lines.append(f'{key} = ""')
        elif key == field_name and mode == "wrong_kind":
            lines.append(f"{key} = true")
        else:
            lines.append(f"{key} = {_toml_string(value)}")
    return tuple(lines)


def _padded_manifest(size: int) -> bytes:
    base = _valid_manifest()
    padding = size - len(base) - 2
    assert padding >= 0
    value = base + b"#" + (b"x" * padding) + b"\n"
    assert len(value) == size
    return value


def _multi_error_manifest(reverse_fields: bool) -> bytes:
    root = (
        (
            'unknown_z = 1\nversion = ""\nname = "ok"\nunknown_a = 2\n'
            'namespace = ""\nschema_version = true\n'
        )
        if reverse_fields
        else (
            'schema_version = true\nnamespace = ""\nname = "ok"\nversion = ""\n'
            "unknown_a = 2\nunknown_z = 1\n"
        )
    )
    asset = (
        '[[assets]]\nunknown_z = 2\npath = "/absolute.pietto"\nunknown_a = 1\n'
        if reverse_fields
        else '[[assets]]\nunknown_a = 1\nunknown_z = 2\npath = "/absolute.pietto"\n'
    )
    asset_two = (
        "[[assets]]\npath = 1\nkind = false\n"
        if reverse_fields
        else "[[assets]]\nkind = false\npath = 1\n"
    )
    dependency = (
        '[[dependencies]]\nextra = 1\npath = "C:/dependency"\nversion = 1\n'
        'name = "ok"\nnamespace = ""\n'
        if reverse_fields
        else (
            '[[dependencies]]\nnamespace = ""\nname = "ok"\nversion = 1\n'
            'path = "C:/dependency"\nextra = 1\n'
        )
    )
    return (root + "\n" + asset + "\n" + asset_two + "\n" + dependency).encode()


def _manifest_with_unknown_toml_value(location: str, literal: str) -> bytes:
    lines = [
        "schema_version = 1",
        'namespace = "ns"',
        'name = "name"',
        'version = "v"',
    ]
    if location == "top":
        lines.append(f"future = {literal}")
    lines.extend(("", "[[assets]]", 'kind = "k"', 'path = "a.pietto"'))
    if location == "asset":
        lines.append(f"future = {literal}")
    lines.extend(
        (
            "",
            "[[dependencies]]",
            'namespace = "d"',
            'name = "d"',
            'version = "v"',
            'sha256 = "s"',
            'path = "."',
        )
    )
    if location == "dependency":
        lines.append(f"future = {literal}")
    return ("\n".join(lines) + "\n").encode()


def _inline_collection_with_nan(collection: str) -> bytes:
    lines = [
        "schema_version = 1",
        'namespace = "ns"',
        'name = "name"',
        'version = "v"',
    ]
    if collection == "assets":
        lines.append('assets = [{ kind = "k", path = "a.pietto", future = nan }]')
    else:
        assert collection == "dependencies"
        lines.append(
            'dependencies = [{ namespace = "d", name = "d", version = "v", '
            'sha256 = "s", path = ".", future = nan }]'
        )
        lines.extend(("", "[[assets]]", 'kind = "k"', 'path = "a.pietto"'))
    return ("\n".join(lines) + "\n").encode()


def _root_key_declaration(key: str, spelling: str) -> str:
    if spelling == "bare":
        return f"{key} = 1"
    if spelling == "quoted":
        return f'"{key}" = 1'
    assert spelling == "dotted"
    return f'"{key}".leaf = 1'


def _manifest_with_root_declarations(
    declarations: tuple[str, ...],
    *,
    asset_count: int = 1,
    dependency_count: int = 1,
) -> bytes:
    lines = [
        "schema_version = 1",
        'namespace = "ns"',
        'name = "name"',
        'version = "v"',
        *declarations,
    ]
    for position in range(asset_count):
        lines.extend(
            (
                "",
                "[[assets]]",
                f'kind = "a{position}"',
                f'path = "a{position}.pietto"',
            )
        )
    for position in range(dependency_count):
        lines.extend(
            (
                "",
                "[[dependencies]]",
                f'namespace = "d{position}"',
                f'name = "d{position}"',
                f'version = "v{position}"',
                f'sha256 = "s{position}"',
                'path = "."',
            )
        )
    return ("\n".join(lines) + "\n").encode()


def _manifest_with_child_declaration(
    collection: str,
    child_kind: str,
    quoted: bool,
) -> bytes:
    lines = [
        "schema_version = 1",
        'namespace = "ns"',
        'name = "name"',
        'version = "v"',
        "",
        "[[assets]]",
        'kind = "k"',
        'path = "a.pietto"',
    ]
    collection_key = f'"{collection}"' if quoted else collection
    brackets = "[[{}]]" if child_kind == "aot" else "[{}]"
    child_header = brackets.format(f"{collection_key}.meta")
    child = (child_header, "value = 1")
    dependency = (
        "",
        "[[dependencies]]",
        'namespace = "d"',
        'name = "d"',
        'version = "v"',
        'sha256 = "s"',
        'path = "."',
    )
    if collection == "assets":
        lines.extend(child)
        lines.extend(dependency)
    else:
        assert collection == "dependencies"
        lines.extend(dependency)
        lines.extend(child)
    return ("\n".join(lines) + "\n").encode()


def _interleaved_parent_child_manifest() -> bytes:
    return b"""schema_version = 1
namespace = "ns"
name = "name"
version = "v"

[[assets]]
kind = "a0"
path = "a0.pietto"
[assets.meta]
value = 0

[[dependencies]]
namespace = "d0"
name = "d0"
version = "v0"
sha256 = "s0"
path = "."
[[dependencies.meta]]
value = 0

[[assets]]
kind = "a1"
path = "a1.pietto"
[[assets.meta]]
value = 1

[[dependencies]]
namespace = "d1"
name = "d1"
version = "v1"
sha256 = "s1"
path = ".."
[dependencies.meta]
value = 1
"""


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _error_kinds(
    result: PackageManifestNormalizationResult,
) -> tuple[ProjectDiscoveryErrorKind, ...]:
    return tuple(error.kind for error in result.errors)
