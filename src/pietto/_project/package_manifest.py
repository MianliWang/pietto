"""Private semantic-package manifest parsing and canonical normalization."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import math
import re
import tomllib
from typing import cast

from pietto._project.model import (
    ProjectDiscoveryError,
    ProjectDiscoveryErrorKind,
    ProjectRootPackageActivation,
)

__all__: tuple[str, ...] = ()

_PACKAGE_MANIFEST_FILENAME = "pietto-package.toml"
_PACKAGE_MANIFEST_BYTE_LIMIT = 1_048_576
_TOP_LEVEL_KEYS = (
    "schema_version",
    "namespace",
    "name",
    "version",
    "assets",
    "dependencies",
)
_ASSET_KEYS = ("kind", "path")
_DEPENDENCY_KEYS = ("namespace", "name", "version", "sha256", "path")
_ASSET_HEADER = re.compile(
    r"(?m)^(?P<indent>[ \t]*)\[\[[ \t]*assets[ \t]*\]\]"
    r"(?P<suffix>[ \t]*(?:#[^\r\n]*)?(?:\r?\n|$))"
)
_DEPENDENCY_HEADER = re.compile(
    r"(?m)^(?P<indent>[ \t]*)\[\[[ \t]*dependencies[ \t]*\]\]"
    r"(?P<suffix>[ \t]*(?:#[^\r\n]*)?(?:\r?\n|$))"
)
_URI_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")

_ErrorSpec = tuple[ProjectDiscoveryErrorKind, str, str | None]


@dataclass(frozen=True, slots=True)
class PackageManifestAsset:
    """One source-ordered structural package asset declaration."""

    kind: str
    path: str

    def __post_init__(self) -> None:
        if type(self) is not PackageManifestAsset:
            raise TypeError("Package manifest asset does not admit subclasses.")
        _require_non_empty_text(self.kind, "Package manifest asset kind")
        _require_non_empty_text(self.path, "Package manifest asset path")
        if not _is_valid_asset_path(self.path):
            raise ValueError(
                "Package manifest asset path must be a normalized package-relative path."
            )


@dataclass(frozen=True, slots=True)
class PackageManifestDependency:
    """One source-ordered structural package dependency declaration."""

    namespace: str
    name: str
    version: str
    sha256: str
    path: str

    def __post_init__(self) -> None:
        if type(self) is not PackageManifestDependency:
            raise TypeError("Package manifest dependency does not admit subclasses.")
        for field_name in ("namespace", "name", "version", "sha256", "path"):
            _require_non_empty_text(
                getattr(self, field_name),
                f"Package manifest dependency {field_name}",
            )
        if not _is_valid_dependency_path(self.path):
            raise ValueError(
                "Package manifest dependency path must be a relative path declaration."
            )


@dataclass(frozen=True, slots=True)
class PackageManifest:
    """One canonical immutable representation of accepted manifest bytes."""

    schema_version: int
    namespace: str
    name: str
    version: str
    assets: tuple[PackageManifestAsset, ...]
    dependencies: tuple[PackageManifestDependency, ...]

    def __post_init__(self) -> None:
        if type(self) is not PackageManifest:
            raise TypeError("Package manifest does not admit subclasses.")
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("Package manifest schema version must be exact integer 1.")
        for field_name in ("namespace", "name", "version"):
            _require_non_empty_text(
                getattr(self, field_name),
                f"Package manifest {field_name}",
            )
        _require_exact_tuple(
            self.assets,
            PackageManifestAsset,
            "Package manifest assets",
        )
        if not self.assets:
            raise ValueError("Package manifest assets must be non-empty.")
        _require_exact_tuple(
            self.dependencies,
            PackageManifestDependency,
            "Package manifest dependencies",
        )


@dataclass(frozen=True, slots=True, init=False)
class PackageManifestNormalizationResult:
    """One complete private manifest normalization result or error tuple."""

    manifest_path: str
    manifest: PackageManifest | None
    errors: tuple[ProjectDiscoveryError, ...]

    def __new__(cls) -> PackageManifestNormalizationResult:
        raise TypeError(
            "Package manifest results are created only by canonical normalization."
        )

    @property
    def ok(self) -> bool:
        """Return whether normalization produced one accepted manifest value."""

        return self.manifest is not None


def _normalize_package_manifest(
    root_package: ProjectRootPackageActivation,
    manifest_bytes: bytes,
) -> PackageManifestNormalizationResult:
    """Normalize caller-supplied manifest bytes without filesystem authority."""

    if type(root_package) is not ProjectRootPackageActivation:
        raise TypeError("Package manifest normalization requires an exact activation.")
    if type(manifest_bytes) is not bytes:
        raise TypeError("Package manifest normalization requires exact bytes.")

    manifest_path = (
        _PACKAGE_MANIFEST_FILENAME
        if root_package.path == "."
        else f"{root_package.path}/{_PACKAGE_MANIFEST_FILENAME}"
    )

    def construct_result(
        manifest: PackageManifest | None,
        error_specs: tuple[_ErrorSpec, ...],
    ) -> PackageManifestNormalizationResult:
        if manifest is not None and type(manifest) is not PackageManifest:
            raise TypeError("Canonical normalization requires an exact manifest.")
        if type(error_specs) is not tuple:
            raise TypeError("Canonical normalization errors must be an exact tuple.")
        errors: list[ProjectDiscoveryError] = []
        for error_spec in error_specs:
            if type(error_spec) is not tuple or len(error_spec) != 3:
                raise TypeError(
                    "Canonical normalization requires primitive error specs."
                )
            kind, message, path = error_spec
            if type(kind) is not ProjectDiscoveryErrorKind:
                raise TypeError("Canonical normalization requires an exact error kind.")
            if type(message) is not str:
                raise TypeError("Canonical normalization error text must be exact.")
            if path is not None and type(path) is not str:
                raise TypeError("Canonical normalization error path must be exact.")
            errors.append(ProjectDiscoveryError(kind, message, path))
        if (manifest is None) is (not errors):
            raise ValueError(
                "Canonical normalization requires exactly one of a manifest or errors."
            )
        result = object.__new__(PackageManifestNormalizationResult)
        object.__setattr__(result, "manifest_path", manifest_path)
        object.__setattr__(result, "manifest", manifest)
        object.__setattr__(result, "errors", tuple(errors))
        return result

    if len(manifest_bytes) > _PACKAGE_MANIFEST_BYTE_LIMIT:
        return construct_result(
            None,
            (
                (
                    ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
                    "Package manifest exceeds the maximum supported size of 1048576 bytes.",
                    manifest_path,
                ),
            ),
        )
    try:
        manifest_text = manifest_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return construct_result(
            None,
            (
                (
                    ProjectDiscoveryErrorKind.CONFIG_PARSE,
                    "Package manifest must be valid UTF-8 TOML.",
                    manifest_path,
                ),
            ),
        )
    try:
        document = tomllib.loads(manifest_text)
    except tomllib.TOMLDecodeError:
        return construct_result(
            None,
            (
                (
                    ProjectDiscoveryErrorKind.CONFIG_PARSE,
                    "Package manifest TOML is invalid.",
                    manifest_path,
                ),
            ),
        )
    errors = _validate_document(manifest_path, manifest_text, document)
    if errors:
        return construct_result(None, errors)

    schema_version = document["schema_version"]
    assets_value = document["assets"]
    dependencies_value = document.get("dependencies", [])
    assert type(schema_version) is int
    assert type(assets_value) is list
    assert all(type(value) is dict for value in assets_value)
    assert type(dependencies_value) is list
    assert all(type(value) is dict for value in dependencies_value)
    asset_entries = cast(list[dict[str, object]], assets_value)
    dependency_entries = cast(list[dict[str, object]], dependencies_value)
    manifest = PackageManifest(
        schema_version=schema_version,
        namespace=document["namespace"],  # type: ignore[arg-type]
        name=document["name"],  # type: ignore[arg-type]
        version=document["version"],  # type: ignore[arg-type]
        assets=tuple(
            PackageManifestAsset(
                kind=value["kind"],  # type: ignore[arg-type]
                path=value["path"],  # type: ignore[arg-type]
            )
            for value in asset_entries
        ),
        dependencies=tuple(
            PackageManifestDependency(
                namespace=value["namespace"],  # type: ignore[arg-type]
                name=value["name"],  # type: ignore[arg-type]
                version=value["version"],  # type: ignore[arg-type]
                sha256=value["sha256"],  # type: ignore[arg-type]
                path=value["path"],  # type: ignore[arg-type]
            )
            for value in dependency_entries
        ),
    )
    return construct_result(manifest, ())


def _validate_document(
    manifest_path: str,
    manifest_text: str,
    document: Mapping[str, object],
) -> tuple[_ErrorSpec, ...]:
    errors: list[_ErrorSpec] = []

    schema_version = document.get("schema_version")
    if type(schema_version) is not int or schema_version != 1:
        errors.append(
            _schema_error(
                manifest_path,
                "Package manifest schema_version must be exact integer 1.",
            )
        )

    for field_name in ("namespace", "name", "version"):
        if not _is_non_empty_text(document.get(field_name)):
            errors.append(
                _schema_error(
                    manifest_path,
                    f"Package manifest {field_name} must be a non-empty string.",
                )
            )

    assets_value = document.get("assets")
    assets_are_entries = _is_non_empty_mapping_list(assets_value)
    if not assets_are_entries:
        errors.append(
            _schema_error(
                manifest_path,
                "Package manifest assets must be one or more root [[assets]] entries.",
            )
        )
    elif not _has_exact_root_array_of_tables(
        manifest_text,
        document,
        key="assets",
        header_pattern=_ASSET_HEADER,
    ):
        errors.append(
            _schema_error(
                manifest_path,
                "Package manifest assets must use exact root [[assets]] syntax.",
            )
        )

    dependencies_present = "dependencies" in document
    dependencies_value = document.get("dependencies")
    dependencies_are_entries = dependencies_present and _is_non_empty_mapping_list(
        dependencies_value
    )
    if dependencies_present and not dependencies_are_entries:
        errors.append(
            _schema_error(
                manifest_path,
                "Package manifest dependencies must be one or more root [[dependencies]] entries.",
            )
        )
    elif dependencies_are_entries and not _has_exact_root_array_of_tables(
        manifest_text,
        document,
        key="dependencies",
        header_pattern=_DEPENDENCY_HEADER,
    ):
        errors.append(
            _schema_error(
                manifest_path,
                "Package manifest dependencies must use exact root [[dependencies]] syntax.",
            )
        )

    for unknown_key in sorted(set(document) - set(_TOP_LEVEL_KEYS)):
        errors.append(
            _schema_error(
                manifest_path,
                f"Package manifest contains unsupported top-level key: {unknown_key}.",
            )
        )

    asset_values = assets_value if type(assets_value) is list else []
    for ordinal, asset_value in enumerate(asset_values):
        errors.extend(
            _validate_entry(
                manifest_path,
                asset_value,
                collection="assets",
                ordinal=ordinal,
                keys=_ASSET_KEYS,
                path_validator=_is_valid_asset_path,
            )
        )

    dependency_values = dependencies_value if type(dependencies_value) is list else []
    for ordinal, dependency_value in enumerate(dependency_values):
        errors.extend(
            _validate_entry(
                manifest_path,
                dependency_value,
                collection="dependencies",
                ordinal=ordinal,
                keys=_DEPENDENCY_KEYS,
                path_validator=_is_valid_dependency_path,
            )
        )

    return tuple(errors)


def _validate_entry(
    manifest_path: str,
    value: object,
    *,
    collection: str,
    ordinal: int,
    keys: tuple[str, ...],
    path_validator: Callable[[str], bool],
) -> tuple[_ErrorSpec, ...]:
    if type(value) is not dict:
        return (
            _schema_error(
                manifest_path,
                f"Package manifest {collection}[{ordinal}] must be a table.",
            ),
        )

    errors: list[_ErrorSpec] = []
    for key in keys:
        if not _is_non_empty_text(value.get(key)):
            errors.append(
                _schema_error(
                    manifest_path,
                    f"Package manifest {collection}[{ordinal}].{key} must be a non-empty string.",
                )
            )
    for unknown_key in sorted(set(value) - set(keys)):
        errors.append(
            _schema_error(
                manifest_path,
                f"Package manifest {collection}[{ordinal}] contains unsupported key: {unknown_key}.",
            )
        )

    path = value.get("path")
    if type(path) is str and path and not path_validator(path):
        errors.append(
            (
                ProjectDiscoveryErrorKind.PROJECT_PATH,
                f"Package manifest {collection}[{ordinal}].path is structurally invalid.",
                path,
            )
        )
    return tuple(errors)


def _has_exact_root_array_of_tables(
    manifest_text: str,
    document: Mapping[str, object],
    *,
    key: str,
    header_pattern: re.Pattern[str],
) -> bool:
    """Prove every decoded entry came from an exact bare root AOT header."""

    matches = tuple(header_pattern.finditer(manifest_text))
    if not matches:
        return False
    probe_keys = _allocate_aot_probe_keys(document, key, len(matches))

    try:
        first_probe = tomllib.loads(
            _insert_aot_probes(
                manifest_text,
                matches,
                probe_keys,
                frozenset(range(len(matches))),
            )
        )
    except tomllib.TOMLDecodeError:
        return False
    real_positions = _aot_probe_positions(
        first_probe.get(key),
        probe_keys,
    )
    if real_positions is None or not real_positions:
        return False

    try:
        probed = tomllib.loads(
            _insert_aot_probes(
                manifest_text,
                matches,
                probe_keys,
                real_positions,
            )
        )
    except tomllib.TOMLDecodeError:
        return False
    if not _remove_aot_probes(
        probed.get(key),
        probe_keys,
        real_positions,
    ):
        return False
    return _toml_values_equivalent(probed, document)


def _allocate_aot_probe_keys(
    document: Mapping[str, object],
    key: str,
    count: int,
) -> tuple[str, ...]:
    occupied = set(_toml_mapping_keys(document))
    probes: list[str] = []
    candidate_index = 0
    while len(probes) < count:
        candidate = f"__pietto_manifest_{key}_probe_{candidate_index}__"
        candidate_index += 1
        if candidate in occupied:
            continue
        occupied.add(candidate)
        probes.append(candidate)
    return tuple(probes)


def _toml_mapping_keys(value: object) -> frozenset[str]:
    keys: set[str] = set()
    pending = [value]
    while pending:
        current = pending.pop()
        if type(current) is dict:
            mapping = cast(dict[str, object], current)
            keys.update(mapping)
            pending.extend(mapping.values())
        elif type(current) is list:
            pending.extend(cast(list[object], current))
    return frozenset(keys)


def _aot_probe_positions(
    value: object,
    probe_keys: tuple[str, ...],
) -> frozenset[int] | None:
    if type(value) is not list:
        return None
    positions_by_probe = {
        probe_key: position for position, probe_key in enumerate(probe_keys)
    }
    found: set[int] = set()
    for item in cast(list[object], value):
        if type(item) is not dict:
            return None
        for item_key, item_value in cast(dict[str, object], item).items():
            position = positions_by_probe.get(item_key)
            if position is None:
                continue
            if item_value is not True or position in found:
                return None
            found.add(position)
    return frozenset(found)


def _remove_aot_probes(
    value: object,
    probe_keys: tuple[str, ...],
    expected_positions: frozenset[int],
) -> bool:
    if _aot_probe_positions(value, probe_keys) != expected_positions:
        return False
    expected_keys = {probe_keys[position] for position in expected_positions}
    for item in cast(list[object], value):
        mapping = cast(dict[str, object], item)
        for item_key in tuple(mapping):
            if item_key in expected_keys:
                del mapping[item_key]
    return True


def _toml_values_equivalent(left: object, right: object) -> bool:
    """Compare independently parsed TOML values without NaN non-reflexivity."""

    if type(left) is not type(right):
        return False
    if type(left) is dict:
        left_mapping = cast(dict[str, object], left)
        right_mapping = cast(dict[str, object], right)
        return left_mapping.keys() == right_mapping.keys() and all(
            _toml_values_equivalent(value, right_mapping[key])
            for key, value in left_mapping.items()
        )
    if type(left) is list:
        left_values = cast(list[object], left)
        right_values = cast(list[object], right)
        return len(left_values) == len(right_values) and all(
            _toml_values_equivalent(left_value, right_value)
            for left_value, right_value in zip(left_values, right_values, strict=True)
        )
    if type(left) is float:
        left_float = cast(float, left)
        right_float = cast(float, right)
        return left_float == right_float or (
            math.isnan(left_float) and math.isnan(right_float)
        )
    return left == right


def _insert_aot_probes(
    manifest_text: str,
    matches: tuple[re.Match[str], ...],
    probe_keys: tuple[str, ...],
    positions: frozenset[int],
) -> str:
    parts: list[str] = []
    cursor = 0
    for position, match in enumerate(matches):
        parts.append(manifest_text[cursor : match.end()])
        if position in positions:
            suffix = match.group("suffix")
            newline = "\r\n" if suffix.endswith("\r\n") else "\n"
            if not suffix.endswith("\n"):
                parts.append(newline)
            parts.append(f"{probe_keys[position]} = true{newline}")
        cursor = match.end()
    parts.append(manifest_text[cursor:])
    return "".join(parts)


def _is_non_empty_mapping_list(value: object) -> bool:
    return (
        type(value) is list
        and bool(value)
        and all(type(item) is dict for item in value)
    )


def _is_non_empty_text(value: object) -> bool:
    return type(value) is str and bool(value)


def _require_non_empty_text(value: object, label: str) -> None:
    if type(value) is not str or not value:
        raise TypeError(f"{label} must be an exact non-empty string.")


def _require_exact_tuple(values: object, item_type: type, label: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"{label} must be an exact tuple.")
    if any(type(value) is not item_type for value in values):
        raise TypeError(f"{label} must contain exact {item_type.__name__} values.")


def _is_valid_asset_path(value: str) -> bool:
    return _is_valid_relative_path(value) and all(
        part not in {".", ".."} for part in value.split("/")
    )


def _is_valid_dependency_path(value: str) -> bool:
    return _is_valid_relative_path(value)


def _is_valid_relative_path(value: str) -> bool:
    if not value or "\x00" in value or "\\" in value:
        return False
    if value.startswith("/") or value.endswith("/") or _URI_SCHEME.match(value):
        return False
    return all(part for part in value.split("/"))


def _schema_error(manifest_path: str, message: str) -> _ErrorSpec:
    return (
        ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
        message,
        manifest_path,
    )
