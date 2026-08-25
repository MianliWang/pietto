"""Private semantic-package manifest normalization and root validation."""

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
from pietto.semantic.capability_facts import CapabilityDomain, CapabilityKey
from pietto.semantic.capability_profiles import CapabilityRequirementCollectionIdentity

__all__: tuple[str, ...] = ()

_PACKAGE_MANIFEST_FILENAME = "pietto-package.toml"
_PACKAGE_MANIFEST_BYTE_LIMIT = 1_048_576
_SCHEMA_V1_TOP_LEVEL_KEYS = (
    "schema_version",
    "namespace",
    "name",
    "version",
    "assets",
    "dependencies",
)
_TOP_LEVEL_KEYS = (*_SCHEMA_V1_TOP_LEVEL_KEYS, "capability_requirements")
_ASSET_KEYS = ("kind", "path")
_DEPENDENCY_KEYS = ("namespace", "name", "version", "sha256", "path")
_CAPABILITY_REQUIREMENT_KEYS = (
    "domain",
    "subject",
    "operation",
    "operands",
    "context",
    "dialect",
    "extension",
)
_CAPABILITY_REQUIREMENT_OPTIONAL_TEXT_KEYS = (
    "subject",
    "operation",
    "context",
    "dialect",
    "extension",
)
_CAPABILITY_DOMAIN_VALUES = frozenset(
    {
        "logical_type",
        "literal",
        "parameter",
        "scalar_function",
        "unary_operator",
        "binary_operator",
        "comparison",
        "null_test",
        "clause",
        "aggregate",
        "window_function",
        "expression_stage",
        "conversion",
        "dialect_lowering",
        "extension_signature",
    }
)
_ASSET_HEADER = re.compile(
    r"(?m)^(?P<indent>[ \t]*)\[\[[ \t]*assets[ \t]*\]\]"
    r"(?P<suffix>[ \t]*(?:#[^\r\n]*)?(?:\r?\n|$))"
)
_DEPENDENCY_HEADER = re.compile(
    r"(?m)^(?P<indent>[ \t]*)\[\[[ \t]*dependencies[ \t]*\]\]"
    r"(?P<suffix>[ \t]*(?:#[^\r\n]*)?(?:\r?\n|$))"
)
_CAPABILITY_REQUIREMENTS_HEADER = re.compile(
    r"(?m)^(?P<indent>[ \t]*)\[[ \t]*capability_requirements[ \t]*\]"
    r"(?P<suffix>[ \t]*(?:#[^\r\n]*)?(?:\r?\n|$))"
)
_CAPABILITY_REQUIREMENT_ENTRY_HEADER = re.compile(
    r"(?m)^(?P<indent>[ \t]*)\[\[[ \t]*capability_requirements[ \t]*"
    r"\.[ \t]*entries[ \t]*\]\]"
    r"(?P<suffix>[ \t]*(?:#[^\r\n]*)?(?:\r?\n|$))"
)
_URI_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_CONTENT_SHA256_PIN = re.compile(r"[0-9a-f]{64}")
_MODULE_SOURCE_ASSET_KIND = "module_source"
_PIETTO_MODULE_SUFFIX = ".pietto"
_ASCII_DIGITS = "0123456789"
_ASCII_NONZERO_DIGITS = "123456789"
_SEMVER_IDENTIFIER_CHARACTERS = (
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-"
)

_ErrorSpec = tuple[ProjectDiscoveryErrorKind, str, str | None]


@dataclass(frozen=True, slots=True)
class PackageIdentity:
    """One exact logical package identity, independent of release content."""

    namespace: str
    name: str

    def __post_init__(self) -> None:
        if type(self) is not PackageIdentity:
            raise TypeError("Package identity does not admit subclasses.")
        _require_non_empty_text(self.namespace, "Package identity namespace")
        _require_non_empty_text(self.name, "Package identity name")


@dataclass(frozen=True, slots=True)
class PackageCoordinate:
    """One logical package identity at one exact SemVer release."""

    identity: PackageIdentity
    exact_version: str

    def __post_init__(self) -> None:
        if type(self) is not PackageCoordinate:
            raise TypeError("Package coordinate does not admit subclasses.")
        if type(self.identity) is not PackageIdentity:
            raise TypeError("Package coordinate requires an exact package identity.")
        if type(self.exact_version) is not str:
            raise TypeError("Package coordinate exact version must be text.")
        if not _is_strict_semver(self.exact_version):
            raise ValueError(
                "Package coordinate exact version must be strict SemVer 2.0.0."
            )


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
class PackageManifestCapabilityRequirements:
    """One normalized package-owned capability requirement declaration."""

    identity: CapabilityRequirementCollectionIdentity
    keys: tuple[CapabilityKey, ...]

    def __post_init__(self) -> None:
        if type(self) is not PackageManifestCapabilityRequirements:
            raise TypeError(
                "Package manifest capability requirements do not admit subclasses."
            )
        if type(self.identity) is not CapabilityRequirementCollectionIdentity:
            raise TypeError(
                "Package manifest capability requirements require an exact identity."
            )
        _require_exact_tuple(
            self.keys,
            CapabilityKey,
            "Package manifest capability requirement keys",
        )
        first_position_by_key: dict[CapabilityKey, int] = {}
        for position, key in enumerate(self.keys):
            first_position = first_position_by_key.setdefault(key, position)
            if first_position != position:
                raise ValueError(
                    "Package manifest capability requirement key "
                    f"{position} duplicates key {first_position}."
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
    capability_requirements: PackageManifestCapabilityRequirements | None = None

    def __post_init__(self) -> None:
        if type(self) is not PackageManifest:
            raise TypeError("Package manifest does not admit subclasses.")
        if type(self.schema_version) is not int or self.schema_version not in {1, 2}:
            raise ValueError(
                "Package manifest schema version must be exact integer 1 or 2."
            )
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
        if (
            self.capability_requirements is not None
            and type(self.capability_requirements)
            is not PackageManifestCapabilityRequirements
        ):
            raise TypeError(
                "Package manifest capability requirements require an exact declaration."
            )
        if self.schema_version == 1 and self.capability_requirements is not None:
            raise ValueError(
                "Package manifest schema version 1 forbids capability requirements."
            )


@dataclass(frozen=True, slots=True)
class ValidatedRootPackage:
    """One root package with validated coordinate and declared digest pin."""

    manifest_path: str
    coordinate: PackageCoordinate
    content_digest_pin: str
    manifest: PackageManifest

    def __post_init__(self) -> None:
        if type(self) is not ValidatedRootPackage:
            raise TypeError("Validated root package does not admit subclasses.")
        _require_non_empty_text(self.manifest_path, "Validated manifest path")
        if type(self.coordinate) is not PackageCoordinate:
            raise TypeError("Validated root package requires an exact coordinate.")
        if type(self.content_digest_pin) is not str:
            raise TypeError("Package content digest pin must be text.")
        if not _is_valid_content_digest_pin(self.content_digest_pin):
            raise ValueError(
                "Package content digest pin must be exactly 64 lowercase hexadecimal characters."
            )
        if type(self.manifest) is not PackageManifest:
            raise TypeError("Validated root package requires an exact manifest.")
        if (
            self.coordinate.identity.namespace != self.manifest.namespace
            or self.coordinate.identity.name != self.manifest.name
            or self.coordinate.exact_version != self.manifest.version
        ):
            raise ValueError(
                "Validated root package coordinate must match its manifest."
            )


@dataclass(frozen=True, slots=True)
class PackageModuleSourceAsset:
    """One typed package-local Pietto module-source declaration."""

    path: str

    def __post_init__(self) -> None:
        if type(self) is not PackageModuleSourceAsset:
            raise TypeError("Package module-source asset does not admit subclasses.")
        _require_non_empty_text(self.path, "Package module-source asset path")
        if not _is_valid_asset_path(self.path):
            raise ValueError(
                "Package module-source asset path must be normalized and package-relative."
            )
        if not self.path.endswith(_PIETTO_MODULE_SUFFIX):
            raise ValueError("Package module-source asset path must end with .pietto.")


@dataclass(frozen=True, slots=True, init=False)
class TypedRootPackageAssetCatalog:
    """One exact root-bound, source-ordered typed package asset catalog."""

    root_package: ValidatedRootPackage
    assets: tuple[PackageModuleSourceAsset, ...]

    def __new__(cls) -> TypedRootPackageAssetCatalog:
        raise TypeError(
            "Typed package asset catalogs are created only by canonical validation."
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


@dataclass(frozen=True, slots=True, init=False)
class PackageRootValidationResult:
    """One complete private validated-root-package result or error tuple."""

    package: ValidatedRootPackage | None
    errors: tuple[ProjectDiscoveryError, ...]

    def __new__(cls) -> PackageRootValidationResult:
        raise TypeError(
            "Root package validation results are created only by canonical validation."
        )

    @property
    def ok(self) -> bool:
        """Return whether root package validation produced one complete value."""

        return self.package is not None


@dataclass(frozen=True, slots=True, init=False)
class PackageTypedAssetValidationResult:
    """One complete private typed-asset catalog result or error tuple."""

    catalog: TypedRootPackageAssetCatalog | None
    errors: tuple[ProjectDiscoveryError, ...]

    def __new__(cls) -> PackageTypedAssetValidationResult:
        raise TypeError(
            "Typed package asset results are created only by canonical validation."
        )

    @property
    def ok(self) -> bool:
        """Return whether typed-asset validation produced one complete catalog."""

        return self.catalog is not None


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
    return _normalize_package_manifest_at_path(manifest_path, manifest_bytes)


def _normalize_package_manifest_at_path(
    manifest_path: str,
    manifest_bytes: bytes,
) -> PackageManifestNormalizationResult:
    """Normalize exact bytes for one already-authorized logical manifest path."""

    if type(manifest_path) is not str or not manifest_path:
        raise TypeError("Package manifest normalization requires an exact path.")
    if type(manifest_bytes) is not bytes:
        raise TypeError("Package manifest normalization requires exact bytes.")

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
    capability_requirements = _normalized_capability_requirements(document)
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
        capability_requirements=capability_requirements,
    )
    return construct_result(manifest, ())


def _validate_root_package_manifest(
    root_package: ProjectRootPackageActivation,
    manifest_bytes: bytes,
) -> PackageRootValidationResult:
    """Validate root package declarations after structural normalization."""

    normalized = _normalize_package_manifest(root_package, manifest_bytes)

    def construct_result(
        package: ValidatedRootPackage | None,
        errors: tuple[ProjectDiscoveryError, ...],
    ) -> PackageRootValidationResult:
        if package is not None and type(package) is not ValidatedRootPackage:
            raise TypeError("Canonical root validation requires an exact package.")
        if type(errors) is not tuple or any(
            type(error) is not ProjectDiscoveryError for error in errors
        ):
            raise TypeError("Canonical root validation requires exact errors.")
        if (package is None) is (not errors):
            raise ValueError(
                "Canonical root validation requires exactly one of a package or errors."
            )
        result = object.__new__(PackageRootValidationResult)
        object.__setattr__(result, "package", package)
        object.__setattr__(result, "errors", errors)
        return result

    if not normalized.ok:
        return construct_result(None, normalized.errors)
    manifest = normalized.manifest
    assert type(manifest) is PackageManifest

    errors: list[ProjectDiscoveryError] = []

    def add_error(message: str) -> None:
        errors.append(
            ProjectDiscoveryError(
                ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
                message,
                normalized.manifest_path,
            )
        )

    if root_package.namespace != manifest.namespace:
        add_error(
            "Project package activation namespace must exactly match package manifest namespace."
        )
    if root_package.name != manifest.name:
        add_error(
            "Project package activation name must exactly match package manifest name."
        )

    activation_version_is_valid = _is_strict_semver(root_package.version)
    manifest_version_is_valid = _is_strict_semver(manifest.version)
    if not activation_version_is_valid:
        add_error("Project package activation version must be strict SemVer 2.0.0.")
    if not manifest_version_is_valid:
        add_error("Package manifest version must be strict SemVer 2.0.0.")
    if (
        activation_version_is_valid
        and manifest_version_is_valid
        and root_package.version != manifest.version
    ):
        add_error(
            "Project package activation version must exactly match package manifest version."
        )
    if not _is_valid_content_digest_pin(root_package.sha256):
        add_error(
            "Project package activation sha256 must be exactly 64 lowercase hexadecimal characters."
        )

    if errors:
        return construct_result(None, tuple(errors))

    identity = PackageIdentity(root_package.namespace, root_package.name)
    coordinate = PackageCoordinate(identity, root_package.version)
    package = ValidatedRootPackage(
        manifest_path=normalized.manifest_path,
        coordinate=coordinate,
        content_digest_pin=root_package.sha256,
        manifest=manifest,
    )
    return construct_result(package, ())


def _validate_typed_root_package_assets(
    root_package: ValidatedRootPackage,
) -> PackageTypedAssetValidationResult:
    """Build one complete pure typed-asset catalog for an exact root package."""

    if type(root_package) is not ValidatedRootPackage:
        raise TypeError("Typed asset validation requires an exact root package.")

    def construct_result(
        catalog: TypedRootPackageAssetCatalog | None,
        errors: tuple[ProjectDiscoveryError, ...],
    ) -> PackageTypedAssetValidationResult:
        if catalog is not None and type(catalog) is not TypedRootPackageAssetCatalog:
            raise TypeError(
                "Canonical typed-asset validation requires an exact catalog."
            )
        if type(errors) is not tuple or any(
            type(error) is not ProjectDiscoveryError for error in errors
        ):
            raise TypeError("Canonical typed-asset validation requires exact errors.")
        if (catalog is None) is (not errors):
            raise ValueError(
                "Canonical typed-asset validation requires exactly one of a catalog or errors."
            )
        result = object.__new__(PackageTypedAssetValidationResult)
        object.__setattr__(result, "catalog", catalog)
        object.__setattr__(result, "errors", errors)
        return result

    errors: list[ProjectDiscoveryError] = []
    first_position_by_path: dict[str, int] = {}

    def add_error(message: str) -> None:
        errors.append(
            ProjectDiscoveryError(
                ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
                message,
                root_package.manifest_path,
            )
        )

    for ordinal, manifest_asset in enumerate(root_package.manifest.assets):
        if manifest_asset.kind != _MODULE_SOURCE_ASSET_KIND:
            add_error(f"Package manifest assets[{ordinal}].kind must be module_source.")
        elif not manifest_asset.path.endswith(_PIETTO_MODULE_SUFFIX):
            add_error(f"Package manifest assets[{ordinal}].path must end with .pietto.")

        first_position = first_position_by_path.get(manifest_asset.path)
        if first_position is None:
            first_position_by_path[manifest_asset.path] = ordinal
        else:
            add_error(
                f"Package manifest assets[{ordinal}].path duplicates "
                f"assets[{first_position}].path."
            )

    if errors:
        return construct_result(None, tuple(errors))

    typed_assets = tuple(
        PackageModuleSourceAsset(manifest_asset.path)
        for manifest_asset in root_package.manifest.assets
    )
    catalog = object.__new__(TypedRootPackageAssetCatalog)
    object.__setattr__(catalog, "root_package", root_package)
    object.__setattr__(catalog, "assets", typed_assets)
    return construct_result(catalog, ())


def _validate_document(
    manifest_path: str,
    manifest_text: str,
    document: Mapping[str, object],
) -> tuple[_ErrorSpec, ...]:
    errors: list[_ErrorSpec] = []

    schema_version = document.get("schema_version")
    if type(schema_version) is not int or schema_version not in {1, 2}:
        errors.append(
            _schema_error(
                manifest_path,
                "Package manifest schema_version must be exact integer 1 or 2.",
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
    elif not _has_exact_array_of_tables(
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
    elif dependencies_are_entries and not _has_exact_array_of_tables(
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

    schema_is_v2 = type(schema_version) is int and schema_version == 2
    allowed_top_level_keys = (
        _TOP_LEVEL_KEYS if schema_is_v2 else _SCHEMA_V1_TOP_LEVEL_KEYS
    )
    for unknown_key in sorted(set(document) - set(allowed_top_level_keys)):
        errors.append(
            _schema_error(
                manifest_path,
                f"Package manifest contains unsupported top-level key: {unknown_key}.",
            )
        )

    if schema_is_v2 and "capability_requirements" in document:
        errors.extend(
            _validate_capability_requirements(
                manifest_path,
                manifest_text,
                document,
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


def _validate_capability_requirements(
    manifest_path: str,
    manifest_text: str,
    document: Mapping[str, object],
) -> tuple[_ErrorSpec, ...]:
    value = document.get("capability_requirements")
    if type(value) is not dict:
        return (
            _schema_error(
                manifest_path,
                "Package manifest capability_requirements must be an exact root table.",
            ),
        )

    errors: list[_ErrorSpec] = []
    declaration = cast(dict[str, object], value)
    if not _has_exact_root_table(
        manifest_text,
        document,
        key="capability_requirements",
        header_pattern=_CAPABILITY_REQUIREMENTS_HEADER,
    ):
        errors.append(
            _schema_error(
                manifest_path,
                "Package manifest capability_requirements must use exact root "
                "[capability_requirements] syntax.",
            )
        )

    for field_name in ("namespace", "name"):
        if not _is_nonblank_text(declaration.get(field_name)):
            errors.append(
                _schema_error(
                    manifest_path,
                    "Package manifest capability_requirements."
                    f"{field_name} must be a nonblank string.",
                )
            )
    for unknown_key in sorted(set(declaration) - {"namespace", "name", "entries"}):
        errors.append(
            _schema_error(
                manifest_path,
                "Package manifest capability_requirements contains unsupported "
                f"key: {unknown_key}.",
            )
        )

    if "entries" not in declaration:
        return tuple(errors)
    entries_value = declaration["entries"]
    if not _is_non_empty_mapping_list(entries_value):
        errors.append(
            _schema_error(
                manifest_path,
                "Package manifest capability_requirements.entries must be omitted "
                "or use one or more exact nested array-of-table entries.",
            )
        )
        return tuple(errors)
    if not _has_exact_array_of_tables(
        manifest_text,
        document,
        parent_key="capability_requirements",
        key="entries",
        header_pattern=_CAPABILITY_REQUIREMENT_ENTRY_HEADER,
    ):
        errors.append(
            _schema_error(
                manifest_path,
                "Package manifest capability_requirements.entries must use exact "
                "[[capability_requirements.entries]] syntax.",
            )
        )

    entries = cast(list[dict[str, object]], entries_value)
    first_position_by_key: dict[CapabilityKey, int] = {}
    for ordinal, entry in enumerate(entries):
        entry_errors = _validate_capability_requirement_entry(
            manifest_path,
            entry,
            ordinal,
        )
        errors.extend(entry_errors)
        if entry_errors:
            continue
        key = _capability_requirement_key(entry)
        first_position = first_position_by_key.setdefault(key, ordinal)
        if first_position != ordinal:
            errors.append(
                _schema_error(
                    manifest_path,
                    "Package manifest capability_requirements.entries"
                    f"[{ordinal}] duplicates exact CapabilityKey at entries"
                    f"[{first_position}].",
                )
            )
    return tuple(errors)


def _validate_capability_requirement_entry(
    manifest_path: str,
    entry: Mapping[str, object],
    ordinal: int,
) -> tuple[_ErrorSpec, ...]:
    errors: list[_ErrorSpec] = []
    prefix = f"Package manifest capability_requirements.entries[{ordinal}]"

    if "domain" not in entry:
        errors.append(_schema_error(manifest_path, f"{prefix}.domain is required."))
    else:
        domain = entry["domain"]
        if type(domain) is not str or domain not in _CAPABILITY_DOMAIN_VALUES:
            errors.append(
                _schema_error(
                    manifest_path,
                    f"{prefix}.domain must be one exact current CapabilityDomain value.",
                )
            )

    if "operands" not in entry:
        errors.append(_schema_error(manifest_path, f"{prefix}.operands is required."))
    else:
        operands = entry["operands"]
        if type(operands) is not list:
            errors.append(
                _schema_error(
                    manifest_path,
                    f"{prefix}.operands must be an array of strings.",
                )
            )
        else:
            for position, operand in enumerate(cast(list[object], operands)):
                if type(operand) is not str:
                    errors.append(
                        _schema_error(
                            manifest_path,
                            f"{prefix}.operands[{position}] must be a string.",
                        )
                    )
                elif not operand.strip():
                    errors.append(
                        _schema_error(
                            manifest_path,
                            f"{prefix}.operands[{position}] must be nonblank.",
                        )
                    )

    for field_name in _CAPABILITY_REQUIREMENT_OPTIONAL_TEXT_KEYS:
        if field_name not in entry:
            continue
        field_value = entry[field_name]
        if type(field_value) is not str:
            errors.append(
                _schema_error(
                    manifest_path,
                    f"{prefix}.{field_name} must be a string when present.",
                )
            )
        elif not field_value.strip():
            errors.append(
                _schema_error(
                    manifest_path,
                    f"{prefix}.{field_name} must be nonblank when present.",
                )
            )

    if "subject" not in entry and "operation" not in entry:
        errors.append(
            _schema_error(
                manifest_path,
                f"{prefix} requires subject or operation.",
            )
        )
    extension = entry.get("extension")
    if type(extension) is str and extension.strip() and "dialect" not in entry:
        errors.append(
            _schema_error(
                manifest_path,
                f"{prefix}.extension requires dialect.",
            )
        )
    for unknown_key in sorted(set(entry) - set(_CAPABILITY_REQUIREMENT_KEYS)):
        errors.append(
            _schema_error(
                manifest_path,
                f"{prefix} contains unsupported key: {unknown_key}.",
            )
        )
    return tuple(errors)


def _capability_requirement_key(entry: Mapping[str, object]) -> CapabilityKey:
    operands = cast(list[str], entry["operands"])
    return CapabilityKey(
        domain=CapabilityDomain(cast(str, entry["domain"])),
        subject=cast(str | None, entry.get("subject")),
        operation=cast(str | None, entry.get("operation")),
        operands=tuple(operands),
        context=cast(str | None, entry.get("context")),
        dialect=cast(str | None, entry.get("dialect")),
        extension=cast(str | None, entry.get("extension")),
    )


def _normalized_capability_requirements(
    document: Mapping[str, object],
) -> PackageManifestCapabilityRequirements | None:
    value = document.get("capability_requirements")
    if value is None:
        return None
    declaration = cast(dict[str, object], value)
    entries = cast(list[dict[str, object]], declaration.get("entries", []))
    return PackageManifestCapabilityRequirements(
        CapabilityRequirementCollectionIdentity(
            cast(str, declaration["namespace"]),
            cast(str, declaration["name"]),
        ),
        tuple(_capability_requirement_key(entry) for entry in entries),
    )


def _has_exact_root_table(
    manifest_text: str,
    document: Mapping[str, object],
    *,
    key: str,
    header_pattern: re.Pattern[str],
) -> bool:
    """Prove one decoded mapping came from an exact bare root table header."""

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
    real_positions = _table_probe_positions(first_probe.get(key), probe_keys)
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
    if not _remove_table_probes(probed.get(key), probe_keys, real_positions):
        return False
    return _toml_values_equivalent(probed, document)


def _has_exact_array_of_tables(
    manifest_text: str,
    document: Mapping[str, object],
    *,
    parent_key: str | None = None,
    key: str,
    header_pattern: re.Pattern[str],
) -> bool:
    """Prove every decoded entry came from one exact bare AOT path."""

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
        _toml_child(first_probe, parent_key, key),
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
        _toml_child(probed, parent_key, key),
        probe_keys,
        real_positions,
    ):
        return False
    return _toml_values_equivalent(probed, document)


def _toml_child(
    document: Mapping[str, object],
    parent_key: str | None,
    key: str,
) -> object | None:
    if parent_key is None:
        return document.get(key)
    parent = document.get(parent_key)
    if type(parent) is not dict:
        return None
    return cast(dict[str, object], parent).get(key)


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


def _table_probe_positions(
    value: object,
    probe_keys: tuple[str, ...],
) -> frozenset[int] | None:
    if type(value) is not dict:
        return None
    positions_by_probe = {
        probe_key: position for position, probe_key in enumerate(probe_keys)
    }
    found: set[int] = set()
    for item_key, item_value in cast(dict[str, object], value).items():
        position = positions_by_probe.get(item_key)
        if position is None:
            continue
        if item_value is not True or position in found:
            return None
        found.add(position)
    return frozenset(found)


def _remove_table_probes(
    value: object,
    probe_keys: tuple[str, ...],
    expected_positions: frozenset[int],
) -> bool:
    if _table_probe_positions(value, probe_keys) != expected_positions:
        return False
    mapping = cast(dict[str, object], value)
    for position in expected_positions:
        del mapping[probe_keys[position]]
    return True


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


def _is_nonblank_text(value: object) -> bool:
    return type(value) is str and bool(value.strip())


def _require_non_empty_text(value: object, label: str) -> None:
    if type(value) is not str or not value:
        raise TypeError(f"{label} must be an exact non-empty string.")


def _require_exact_tuple(values: object, item_type: type, label: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"{label} must be an exact tuple.")
    if any(type(value) is not item_type for value in values):
        raise TypeError(f"{label} must contain exact {item_type.__name__} values.")


def _is_strict_semver(value: object) -> bool:
    if type(value) is not str:
        return False
    core_and_prerelease, build_marker, build = value.partition("+")
    if build_marker and not _are_valid_semver_identifiers(
        build,
        reject_numeric_leading_zero=False,
    ):
        return False

    core, prerelease_marker, prerelease = core_and_prerelease.partition("-")
    core_numbers = core.split(".")
    if len(core_numbers) != 3 or not all(
        _is_valid_semver_core_number(number) for number in core_numbers
    ):
        return False
    return not prerelease_marker or _are_valid_semver_identifiers(
        prerelease,
        reject_numeric_leading_zero=True,
    )


def _is_valid_semver_core_number(value: str) -> bool:
    return value == "0" or (
        bool(value)
        and value[0] in _ASCII_NONZERO_DIGITS
        and all(character in _ASCII_DIGITS for character in value)
    )


def _are_valid_semver_identifiers(
    value: str,
    *,
    reject_numeric_leading_zero: bool,
) -> bool:
    for identifier in value.split("."):
        if not identifier or any(
            character not in _SEMVER_IDENTIFIER_CHARACTERS for character in identifier
        ):
            return False
        is_numeric = all(character in _ASCII_DIGITS for character in identifier)
        if (
            reject_numeric_leading_zero
            and is_numeric
            and len(identifier) > 1
            and identifier.startswith("0")
        ):
            return False
    return True


def _is_valid_content_digest_pin(value: object) -> bool:
    return type(value) is str and _CONTENT_SHA256_PIN.fullmatch(value) is not None


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
