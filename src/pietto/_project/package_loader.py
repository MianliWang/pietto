"""Private trusted root-package loading and parsed-module integration."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path
import stat

import pietto.parser_api as parser_api
from pietto._project.model import ProjectDiscoveryError, ProjectDiscoveryErrorKind
from pietto._project.module_carrier import ProjectModuleIdentity
from pietto._project.package_locator import LocatedRootPackage
from pietto._project.package_manifest import (
    PackageModuleSourceAsset,
    TypedRootPackageAssetCatalog,
    _PACKAGE_MANIFEST_BYTE_LIMIT,
    _PACKAGE_MANIFEST_FILENAME,
    _validate_root_package_manifest,
    _validate_typed_root_package_assets,
)
from pietto._project.path_trust import (
    ProjectFilesystemState,
    ProjectIdentityUnavailableError,
    ProjectPhysicalIdentity,
    ProjectRootChangedError,
    ProjectSymbolicLinkTraversalError,
    _capture_pinned_directory_state,
    _fstat_state,
    _lstat_state,
    _open_pinned_file,
)
from pietto.ast_nodes import Script
from pietto.errors import Diagnostic, Severity

__all__: tuple[str, ...] = ()

PACKAGE_CONTENT_DOMAIN = b"pietto-package-content-v1\0"


@dataclass(frozen=True, slots=True, init=False)
class PackageFileSnapshot:
    """Exact trusted bytes and filesystem facts for one package-local file."""

    located_root: LocatedRootPackage = field(repr=False)
    logical_path: str
    content: bytes = field(repr=False)
    opened_state: ProjectFilesystemState = field(repr=False)

    def __new__(cls) -> PackageFileSnapshot:
        raise TypeError("Package file snapshots are created only by trusted loading.")


@dataclass(frozen=True, slots=True, init=False)
class PackageParsedModule:
    """One package-owned parsed module in typed-manifest source order."""

    catalog: TypedRootPackageAssetCatalog = field(repr=False)
    asset: PackageModuleSourceAsset
    identity: ProjectModuleIdentity
    position: int
    source: PackageFileSnapshot = field(repr=False)
    script: Script = field(repr=False)

    def __new__(cls) -> PackageParsedModule:
        raise TypeError("Package parsed modules are created only by trusted loading.")


@dataclass(frozen=True, slots=True, init=False)
class LoadedRootPackage:
    """One integrity-verified local root package and parsed module bundle."""

    located_root: LocatedRootPackage = field(repr=False)
    manifest_snapshot: PackageFileSnapshot = field(repr=False)
    catalog: TypedRootPackageAssetCatalog
    asset_snapshots: tuple[PackageFileSnapshot, ...] = field(repr=False)
    content_digest: str
    modules: tuple[PackageParsedModule, ...]

    def __new__(cls) -> LoadedRootPackage:
        raise TypeError("Loaded root packages are created only by trusted loading.")


@dataclass(frozen=True, slots=True, init=False)
class PackageLoadResult:
    """One complete loaded package or private error and diagnostic facts."""

    loaded_package: LoadedRootPackage | None
    errors: tuple[ProjectDiscoveryError, ...]
    diagnostics: tuple[Diagnostic, ...]

    def __new__(cls) -> PackageLoadResult:
        raise TypeError("Package load results are created only by trusted loading.")

    @property
    def ok(self) -> bool:
        """Return whether one complete integrity-verified package was loaded."""

        return self.loaded_package is not None


def _compute_package_content_sha256(
    manifest_bytes: bytes,
    assets: tuple[tuple[str, bytes], ...],
) -> str:
    """Compute frozen D1 framing over exact package-local bytes and paths."""

    if type(manifest_bytes) is not bytes:
        raise TypeError("Package content framing requires exact manifest bytes.")
    if type(assets) is not tuple:
        raise TypeError("Package content framing assets must be an exact tuple.")
    for record in assets:
        if (
            type(record) is not tuple
            or len(record) != 2
            or type(record[0]) is not str
            or type(record[1]) is not bytes
        ):
            raise TypeError("Package content framing requires exact asset records.")

    hasher = hashlib.sha256()
    hasher.update(PACKAGE_CONTENT_DOMAIN)

    def update_record(logical_path: str, content: bytes) -> None:
        path_bytes = logical_path.encode("utf-8")
        hasher.update(len(path_bytes).to_bytes(8, "big"))
        hasher.update(path_bytes)
        hasher.update(len(content).to_bytes(8, "big"))
        hasher.update(content)

    update_record(_PACKAGE_MANIFEST_FILENAME, manifest_bytes)
    for logical_path, content in assets:
        update_record(logical_path, content)
    return hasher.hexdigest()


def _load_root_package(located_root: LocatedRootPackage) -> PackageLoadResult:
    """Load, verify, and parse one exact located root package."""

    if type(located_root) is not LocatedRootPackage:
        raise TypeError("Package loading requires an exact located root.")

    def construct_result(
        loaded_package: LoadedRootPackage | None,
        errors: tuple[ProjectDiscoveryError, ...],
        diagnostics: tuple[Diagnostic, ...],
    ) -> PackageLoadResult:
        if loaded_package is not None:
            if type(loaded_package) is not LoadedRootPackage:
                raise TypeError("Canonical package loading requires an exact package.")
            if loaded_package.located_root is not located_root:
                raise ValueError("Canonical package loading requires the caller root.")
        if type(errors) is not tuple or any(
            type(error) is not ProjectDiscoveryError for error in errors
        ):
            raise TypeError("Canonical package loading requires exact errors.")
        if type(diagnostics) is not tuple or any(
            type(diagnostic) is not Diagnostic for diagnostic in diagnostics
        ):
            raise TypeError("Canonical package loading requires exact diagnostics.")
        has_error_diagnostic = any(
            diagnostic.severity is Severity.ERROR for diagnostic in diagnostics
        )
        if loaded_package is None:
            if not errors and not has_error_diagnostic:
                raise ValueError(
                    "Failed package loading requires an error or error diagnostic."
                )
        elif errors or has_error_diagnostic:
            raise ValueError("Successful package loading forbids error facts.")
        result = object.__new__(PackageLoadResult)
        object.__setattr__(result, "loaded_package", loaded_package)
        object.__setattr__(result, "errors", errors)
        object.__setattr__(result, "diagnostics", diagnostics)
        return result

    manifest_read = _read_trusted_package_file(
        located_root,
        _PACKAGE_MANIFEST_FILENAME,
        byte_limit=_PACKAGE_MANIFEST_BYTE_LIMIT,
        kind=ProjectDiscoveryErrorKind.CONFIG_READ,
        label="Package manifest",
    )
    if type(manifest_read) is ProjectDiscoveryError:
        return construct_result(None, (manifest_read,), ())
    manifest_snapshot = manifest_read
    assert type(manifest_snapshot) is PackageFileSnapshot

    validated = _validate_root_package_manifest(
        located_root.activation,
        manifest_snapshot.content,
    )
    if not validated.ok:
        return construct_result(None, validated.errors, ())
    root_package = validated.package
    assert root_package is not None

    typed = _validate_typed_root_package_assets(root_package)
    if not typed.ok:
        return construct_result(None, typed.errors, ())
    catalog = typed.catalog
    assert type(catalog) is TypedRootPackageAssetCatalog

    asset_snapshots: list[PackageFileSnapshot] = []
    asset_errors: list[ProjectDiscoveryError] = []
    physical_identities: set[ProjectPhysicalIdentity] = set()
    for asset in catalog.assets:
        asset_read = _read_trusted_package_file(
            located_root,
            asset.path,
            byte_limit=parser_api._MAX_SOURCE_UTF8_BYTES,
            kind=ProjectDiscoveryErrorKind.SOURCE_READ,
            label="Package asset",
        )
        if type(asset_read) is ProjectDiscoveryError:
            if asset_read.path is None:
                return construct_result(None, (asset_read,), ())
            asset_errors.append(asset_read)
            continue
        snapshot = asset_read
        assert type(snapshot) is PackageFileSnapshot
        if snapshot.opened_state.physical_identity in physical_identities:
            asset_errors.append(
                _error(
                    ProjectDiscoveryErrorKind.PROJECT_PATH,
                    "Package asset path aliases an earlier declared physical file.",
                    asset.path,
                )
            )
        else:
            physical_identities.add(snapshot.opened_state.physical_identity)
        asset_snapshots.append(snapshot)

    if asset_errors:
        return construct_result(None, tuple(asset_errors), ())
    snapshots = tuple(asset_snapshots)
    if len(snapshots) != len(catalog.assets):
        raise ValueError("Trusted package loading requires every typed asset.")

    content_digest = _compute_package_content_sha256(
        manifest_snapshot.content,
        tuple(
            (asset.path, snapshot.content)
            for asset, snapshot in zip(catalog.assets, snapshots, strict=True)
        ),
    )
    if content_digest != root_package.content_digest_pin:
        return construct_result(
            None,
            (
                _error(
                    ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
                    "Package content digest does not match the declared root sha256.",
                    _PACKAGE_MANIFEST_FILENAME,
                ),
            ),
            (),
        )

    scripts: list[Script] = []
    parse_errors: list[ProjectDiscoveryError] = []
    diagnostics: list[Diagnostic] = []
    for asset, snapshot in zip(catalog.assets, snapshots, strict=True):
        try:
            source_text = snapshot.content.decode("utf-8")
        except UnicodeDecodeError:
            parse_errors.append(
                _error(
                    ProjectDiscoveryErrorKind.SOURCE_READ,
                    "Package module source must be valid UTF-8.",
                    asset.path,
                )
            )
            continue
        parse_result = parser_api.parse_source(source_text, path=asset.path)
        diagnostics.extend(parse_result.diagnostics)
        if any(
            diagnostic.severity is Severity.ERROR
            for diagnostic in parse_result.diagnostics
        ):
            continue
        if parse_result.ast is None:
            parse_errors.append(
                _error(
                    ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
                    "Package parser produced no AST.",
                    asset.path,
                )
            )
            continue
        scripts.append(parse_result.ast)

    final_diagnostics = tuple(diagnostics)
    if parse_errors or any(
        diagnostic.severity is Severity.ERROR for diagnostic in final_diagnostics
    ):
        return construct_result(None, tuple(parse_errors), final_diagnostics)
    if len(scripts) != len(catalog.assets):
        raise ValueError("Trusted package loading requires every parsed module.")
    root_error = _verify_located_root(located_root)
    if root_error is not None:
        return construct_result(None, (root_error,), final_diagnostics)

    modules: list[PackageParsedModule] = []
    for position, (asset, snapshot, script) in enumerate(
        zip(catalog.assets, snapshots, scripts, strict=True)
    ):
        module = object.__new__(PackageParsedModule)
        object.__setattr__(module, "catalog", catalog)
        object.__setattr__(module, "asset", asset)
        object.__setattr__(module, "identity", ProjectModuleIdentity(path=asset.path))
        object.__setattr__(module, "position", position)
        object.__setattr__(module, "source", snapshot)
        object.__setattr__(module, "script", script)
        modules.append(module)

    loaded_package = object.__new__(LoadedRootPackage)
    object.__setattr__(loaded_package, "located_root", located_root)
    object.__setattr__(loaded_package, "manifest_snapshot", manifest_snapshot)
    object.__setattr__(loaded_package, "catalog", catalog)
    object.__setattr__(loaded_package, "asset_snapshots", snapshots)
    object.__setattr__(loaded_package, "content_digest", content_digest)
    object.__setattr__(loaded_package, "modules", tuple(modules))
    return construct_result(loaded_package, (), final_diagnostics)


def _read_trusted_package_file(
    located_root: LocatedRootPackage,
    logical_path: str,
    *,
    byte_limit: int,
    kind: ProjectDiscoveryErrorKind,
    label: str,
) -> PackageFileSnapshot | ProjectDiscoveryError:
    """Read one bounded regular non-symlink package file with identity checks."""

    if type(located_root) is not LocatedRootPackage:
        raise TypeError("Trusted package reads require an exact located root.")
    if type(logical_path) is not str or not logical_path:
        raise TypeError("Trusted package reads require an exact logical path.")
    if type(byte_limit) is not int or byte_limit <= 0:
        raise ValueError("Trusted package reads require a positive byte limit.")
    if type(kind) is not ProjectDiscoveryErrorKind or type(label) is not str:
        raise TypeError("Trusted package reads require exact error facts.")

    root_error = _verify_located_root(located_root)
    if root_error is not None:
        return root_error

    canonical_path = located_root.canonical_path.joinpath(*logical_path.split("/"))
    try:
        relative_path = canonical_path.relative_to(located_root.canonical_path)
    except ValueError:
        return _error(
            ProjectDiscoveryErrorKind.PROJECT_PATH,
            "Package file path escapes the located package root.",
            logical_path,
        )
    if (
        relative_path.is_absolute()
        or not relative_path.parts
        or relative_path == Path(".")
        or ".." in relative_path.parts
    ):
        return _error(
            ProjectDiscoveryErrorKind.PROJECT_PATH,
            "Package file path escapes the located package root.",
            logical_path,
        )

    parent_state = _capture_package_parent(
        located_root,
        canonical_path.parent,
        logical_path,
    )
    if type(parent_state) is ProjectDiscoveryError:
        return parent_state

    try:
        inspected_state = _lstat_state(canonical_path)
    except ProjectIdentityUnavailableError:
        return _identity_unavailable_error()
    except OSError:
        root_error = _verify_located_root(located_root)
        return root_error or _error(
            kind,
            f"{label} file does not exist or is not accessible.",
            logical_path,
        )
    if stat.S_ISLNK(inspected_state.file_type):
        root_error = _verify_located_root(located_root)
        return root_error or _error(
            kind,
            f"{label} path must not be a symbolic link.",
            logical_path,
        )
    if not stat.S_ISREG(inspected_state.file_type):
        root_error = _verify_located_root(located_root)
        return root_error or _error(
            kind,
            f"{label} path must be a regular file.",
            logical_path,
        )

    file_descriptor = -1
    try:
        try:
            file_descriptor = _open_pinned_file(
                located_root.pinned_root,
                canonical_path,
            )
        except ProjectRootChangedError:
            return _project_root_changed_error()
        except ProjectIdentityUnavailableError:
            return _identity_unavailable_error()
        except OSError:
            root_error = _verify_located_root(located_root)
            return root_error or _error(
                kind,
                f"{label} opened identity does not match the inspected file.",
                logical_path,
            )

        opened_state = _fstat_state(file_descriptor)
        if not stat.S_ISREG(opened_state.file_type) or opened_state != inspected_state:
            root_error = _verify_located_root(located_root)
            return root_error or _error(
                kind,
                f"{label} opened identity does not match the inspected file.",
                logical_path,
            )
        with os.fdopen(file_descriptor, "rb", closefd=True) as package_file:
            file_descriptor = -1
            content = package_file.read(byte_limit + 1)
            final_opened_state = _fstat_state(package_file.fileno())
    except ProjectIdentityUnavailableError:
        return _identity_unavailable_error()
    except OSError:
        root_error = _verify_located_root(located_root)
        return root_error or _error(
            kind,
            f"{label} file changed while being read.",
            logical_path,
        )
    finally:
        if file_descriptor >= 0:
            os.close(file_descriptor)

    if final_opened_state != opened_state:
        root_error = _verify_located_root(located_root)
        return root_error or _error(
            kind,
            f"{label} file changed while being read.",
            logical_path,
        )
    try:
        final_inspected_state = _lstat_state(canonical_path)
    except ProjectIdentityUnavailableError:
        return _identity_unavailable_error()
    except OSError:
        root_error = _verify_located_root(located_root)
        return root_error or _error(
            kind,
            f"{label} file changed while being read.",
            logical_path,
        )
    if stat.S_ISLNK(final_inspected_state.file_type) or (
        final_inspected_state != inspected_state
    ):
        root_error = _verify_located_root(located_root)
        return root_error or _error(
            kind,
            f"{label} file changed while being read.",
            logical_path,
        )

    final_parent_state = _capture_package_parent(
        located_root,
        canonical_path.parent,
        logical_path,
    )
    if type(final_parent_state) is ProjectDiscoveryError:
        return final_parent_state
    if final_parent_state != parent_state:
        return _error(
            kind,
            f"{label} parent directory changed while being read.",
            logical_path,
        )
    root_error = _verify_located_root(located_root)
    if root_error is not None:
        return root_error
    if len(content) > byte_limit:
        return _error(
            kind,
            f"{label} exceeds the maximum supported size of {byte_limit} bytes.",
            logical_path,
        )

    snapshot = object.__new__(PackageFileSnapshot)
    object.__setattr__(snapshot, "located_root", located_root)
    object.__setattr__(snapshot, "logical_path", logical_path)
    object.__setattr__(snapshot, "content", content)
    object.__setattr__(snapshot, "opened_state", opened_state)
    return snapshot


def _capture_package_parent(
    located_root: LocatedRootPackage,
    parent_path: Path,
    logical_path: str,
) -> ProjectFilesystemState | ProjectDiscoveryError:
    """Capture one package file parent without following directory symlinks."""

    try:
        return _capture_pinned_directory_state(located_root.pinned_root, parent_path)
    except ProjectRootChangedError:
        return _project_root_changed_error()
    except ProjectIdentityUnavailableError:
        return _identity_unavailable_error()
    except ProjectSymbolicLinkTraversalError:
        root_error = _verify_located_root(located_root)
        return root_error or _error(
            ProjectDiscoveryErrorKind.PROJECT_PATH,
            "Package file path must not traverse symbolic links.",
            logical_path,
        )
    except (OSError, RuntimeError):
        root_error = _verify_located_root(located_root)
        return root_error or _error(
            ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
            "Package file parent directory is not accessible or changed.",
            logical_path,
        )


def _verify_located_root(
    located_root: LocatedRootPackage,
) -> ProjectDiscoveryError | None:
    """Require the project and package roots to retain their located identities."""

    try:
        current_state = _capture_pinned_directory_state(
            located_root.pinned_root,
            located_root.canonical_path,
        )
    except ProjectRootChangedError:
        return _project_root_changed_error()
    except ProjectIdentityUnavailableError:
        return _identity_unavailable_error()
    except (OSError, RuntimeError):
        return _error(
            ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
            "Located package root changed after location.",
            None,
        )
    if current_state != located_root.directory_state:
        return _error(
            ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
            "Located package root changed after location.",
            None,
        )
    return None


def _project_root_changed_error() -> ProjectDiscoveryError:
    return _error(
        ProjectDiscoveryErrorKind.PROJECT_ROOT,
        "Project root identity changed during project loading.",
        None,
    )


def _identity_unavailable_error() -> ProjectDiscoveryError:
    return _error(
        ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
        "Project filesystem identity is unavailable.",
        None,
    )


def _error(
    kind: ProjectDiscoveryErrorKind,
    message: str,
    path: str | None,
) -> ProjectDiscoveryError:
    return ProjectDiscoveryError(kind, message, path)
