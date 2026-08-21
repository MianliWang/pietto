"""Private exact dependency validation and deterministic local package load plan."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
import posixpath

from pietto._project.model import ProjectDiscoveryError, ProjectDiscoveryErrorKind
from pietto._project.package_loader import (
    LoadedRootPackage,
    _LoadedPackageContent,
    _PackageModuleContent,
    _error,
    _load_package_content,
    _verify_package_root,
)
from pietto._project.package_manifest import (
    PackageCoordinate,
    PackageIdentity,
    PackageManifest,
    PackageManifestDependency,
    TypedRootPackageAssetCatalog,
    ValidatedRootPackage,
    _PACKAGE_MANIFEST_FILENAME,
    _is_strict_semver,
    _is_valid_content_digest_pin,
    _is_valid_dependency_path,
    _normalize_package_manifest_at_path,
)
from pietto._project.path_trust import (
    ProjectFilesystemState,
    ProjectIdentityUnavailableError,
    ProjectPhysicalIdentity,
    ProjectPinnedRoot,
    ProjectRootChangedError,
    ProjectSymbolicLinkTraversalError,
    _capture_pinned_directory_state,
)
from pietto.errors import Diagnostic

__all__: tuple[str, ...] = ()


class DependencyLocatorKind(StrEnum):
    LOCAL_DIRECTORY = "local_directory"


class PackageLoadPlanBlockerKind(StrEnum):
    CYCLE = "cycle"
    CONFLICT = "conflict"
    DIAMOND = "diamond"


@dataclass(frozen=True, slots=True, init=False)
class PackageDependencyOccurrence:
    declaring_package: LoadedRootPackage | LoadedDependencyPackage = field(repr=False)
    declaration: PackageManifestDependency
    position: int
    coordinate: PackageCoordinate
    content_digest_pin: str = field(repr=False)
    locator_kind: DependencyLocatorKind
    resolved_project_path: str

    def __new__(cls) -> PackageDependencyOccurrence:
        raise TypeError(
            "Package dependency occurrences are created only by semantic validation."
        )


@dataclass(frozen=True, slots=True, init=False)
class PackageDependencyValidationResult:
    occurrences: tuple[PackageDependencyOccurrence, ...]
    errors: tuple[ProjectDiscoveryError, ...]

    def __new__(cls) -> PackageDependencyValidationResult:
        raise TypeError(
            "Package dependency validation results require canonical validation."
        )

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass(frozen=True, slots=True, init=False)
class LocatedDependencyPackage:
    occurrence: PackageDependencyOccurrence
    pinned_root: ProjectPinnedRoot = field(repr=False)
    canonical_path: Path = field(repr=False)
    directory_state: ProjectFilesystemState = field(repr=False)

    def __new__(cls) -> LocatedDependencyPackage:
        raise TypeError(
            "Located dependency packages are created only by trusted location."
        )


@dataclass(frozen=True, slots=True, init=False)
class LoadedDependencyPackage:
    location: LocatedDependencyPackage = field(repr=False)
    content: _LoadedPackageContent = field(repr=False)

    def __new__(cls) -> LoadedDependencyPackage:
        raise TypeError(
            "Loaded dependency packages are created only by trusted loading."
        )

    @property
    def catalog(self) -> TypedRootPackageAssetCatalog:
        return self.content.catalog

    @property
    def content_digest(self) -> str:
        return self.content.content_digest

    @property
    def modules(self) -> tuple[_PackageModuleContent, ...]:
        return self.content.modules


LoadedPackage = LoadedRootPackage | LoadedDependencyPackage


@dataclass(frozen=True, slots=True, init=False)
class PackageDependencyEdge:
    occurrence: PackageDependencyOccurrence
    package: LoadedPackage = field(repr=False)

    def __new__(cls) -> PackageDependencyEdge:
        raise TypeError("Package dependency edges require canonical planning.")


@dataclass(frozen=True, slots=True, init=False)
class PackageLoadPlanEntry:
    package: LoadedPackage = field(repr=False)
    dependencies: tuple[PackageDependencyEdge, ...]
    position: int

    def __new__(cls) -> PackageLoadPlanEntry:
        raise TypeError("Package load-plan entries require canonical planning.")


@dataclass(frozen=True, slots=True, init=False)
class PackageLoadPlan:
    root_package: LoadedRootPackage = field(repr=False)
    entries: tuple[PackageLoadPlanEntry, ...]

    def __new__(cls) -> PackageLoadPlan:
        raise TypeError("Package load plans require canonical planning.")


@dataclass(frozen=True, slots=True, init=False)
class PackageLoadPlanBlocker:
    kind: PackageLoadPlanBlockerKind
    occurrences: tuple[PackageDependencyOccurrence, ...]
    location: LocatedDependencyPackage = field(repr=False)
    packages: tuple[LoadedPackage, ...] = field(repr=False)

    def __new__(cls) -> PackageLoadPlanBlocker:
        raise TypeError("Package load-plan blockers require canonical detection.")


@dataclass(frozen=True, slots=True, init=False)
class PackageLoadPlanResult:
    plan: PackageLoadPlan | None
    errors: tuple[ProjectDiscoveryError, ...]
    blockers: tuple[PackageLoadPlanBlocker, ...]
    diagnostics: tuple[Diagnostic, ...]

    def __new__(cls) -> PackageLoadPlanResult:
        raise TypeError("Package load-plan results require canonical planning.")

    @property
    def ok(self) -> bool:
        return self.plan is not None


@dataclass(slots=True)
class _Frame:
    package: LoadedPackage
    key: ProjectPhysicalIdentity
    occurrences: tuple[PackageDependencyOccurrence, ...]
    incoming: PackageDependencyOccurrence | None
    next_position: int = 0
    dependencies: list[PackageDependencyEdge] = field(default_factory=list)


def _validate_dependency_occurrences(
    declaring_package: LoadedPackage,
) -> PackageDependencyValidationResult:
    """Semantically validate every exact dependency occurrence in source order."""

    if type(declaring_package) not in {LoadedRootPackage, LoadedDependencyPackage}:
        raise TypeError("Dependency validation requires an exact loaded package.")
    declarations = _package_catalog(
        declaring_package
    ).root_package.manifest.dependencies
    declaring_path = _package_project_path(declaring_package)
    occurrences: list[PackageDependencyOccurrence] = []
    errors: list[ProjectDiscoveryError] = []

    for position, declaration in enumerate(declarations):
        occurrence_errors: list[ProjectDiscoveryError] = []
        if not _is_strict_semver(declaration.version):
            occurrence_errors.append(
                _error(
                    ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
                    "Package dependency version must be strict SemVer 2.0.0.",
                    declaration.path,
                )
            )
        if not _is_valid_content_digest_pin(declaration.sha256):
            occurrence_errors.append(
                _error(
                    ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
                    "Package dependency sha256 must be exactly 64 lowercase hexadecimal characters.",
                    declaration.path,
                )
            )
        resolved_path = _normalize_dependency_path(
            declaring_path,
            declaration.path,
        )
        if resolved_path is None:
            occurrence_errors.append(
                _error(
                    ProjectDiscoveryErrorKind.PROJECT_PATH,
                    "Package dependency path escapes the pinned project root.",
                    declaration.path,
                )
            )
        if occurrence_errors:
            errors.extend(occurrence_errors)
            continue

        identity = PackageIdentity(declaration.namespace, declaration.name)
        coordinate = PackageCoordinate(identity, declaration.version)
        occurrence = object.__new__(PackageDependencyOccurrence)
        object.__setattr__(occurrence, "declaring_package", declaring_package)
        object.__setattr__(occurrence, "declaration", declaration)
        object.__setattr__(occurrence, "position", position)
        object.__setattr__(occurrence, "coordinate", coordinate)
        object.__setattr__(occurrence, "content_digest_pin", declaration.sha256)
        object.__setattr__(
            occurrence,
            "locator_kind",
            DependencyLocatorKind.LOCAL_DIRECTORY,
        )
        object.__setattr__(occurrence, "resolved_project_path", resolved_path)
        occurrences.append(occurrence)

    result = object.__new__(PackageDependencyValidationResult)
    object.__setattr__(result, "occurrences", () if errors else tuple(occurrences))
    object.__setattr__(result, "errors", tuple(errors))
    return result


def _normalize_dependency_path(
    declaring_project_path: str,
    authored_path: str,
) -> str | None:
    if not _is_valid_dependency_path(authored_path):
        return None
    normalized = posixpath.normpath(
        posixpath.join(declaring_project_path, authored_path)
    )
    if (
        posixpath.isabs(normalized)
        or normalized == ".."
        or normalized.startswith("../")
    ):
        return None
    return normalized


def _locate_dependency_package(
    occurrence: PackageDependencyOccurrence,
) -> LocatedDependencyPackage | ProjectDiscoveryError:
    pinned_root = _package_pinned_root(occurrence.declaring_package)
    canonical_path = (
        pinned_root.canonical_path
        if occurrence.resolved_project_path == "."
        else pinned_root.canonical_path.joinpath(
            *occurrence.resolved_project_path.split("/")
        )
    )
    try:
        relative_path = canonical_path.relative_to(pinned_root.canonical_path)
    except ValueError:
        return _dependency_path_error(occurrence)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        return _dependency_path_error(occurrence)

    try:
        directory_state = _capture_pinned_directory_state(
            pinned_root,
            canonical_path,
        )
    except ProjectRootChangedError:
        return _error(
            ProjectDiscoveryErrorKind.PROJECT_ROOT,
            "Project root identity changed during dependency loading.",
            None,
        )
    except ProjectIdentityUnavailableError:
        return _error(
            ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
            "Project filesystem identity is unavailable.",
            None,
        )
    except ProjectSymbolicLinkTraversalError:
        return _error(
            ProjectDiscoveryErrorKind.PROJECT_PATH,
            "Package dependency path must not traverse symbolic links.",
            occurrence.declaration.path,
        )
    except (OSError, RuntimeError):
        return _error(
            ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
            "Package dependency directory is missing, inaccessible, or changed.",
            occurrence.declaration.path,
        )

    location = object.__new__(LocatedDependencyPackage)
    object.__setattr__(location, "occurrence", occurrence)
    object.__setattr__(location, "pinned_root", pinned_root)
    object.__setattr__(location, "canonical_path", canonical_path)
    object.__setattr__(location, "directory_state", directory_state)
    return location


def _load_dependency_package(
    location: LocatedDependencyPackage,
) -> tuple[
    LoadedDependencyPackage | None,
    tuple[ProjectDiscoveryError, ...],
    tuple[Diagnostic, ...],
]:
    content_result = _load_package_content(
        location.pinned_root,
        location.canonical_path,
        location.directory_state,
        lambda manifest_bytes: _validate_dependency_manifest(
            location.occurrence,
            manifest_bytes,
        ),
    )
    if not content_result.ok:
        return None, content_result.errors, content_result.diagnostics
    content = content_result.content
    assert type(content) is _LoadedPackageContent
    loaded = object.__new__(LoadedDependencyPackage)
    object.__setattr__(loaded, "location", location)
    object.__setattr__(loaded, "content", content)
    return loaded, (), content_result.diagnostics


def _validate_dependency_manifest(
    occurrence: PackageDependencyOccurrence,
    manifest_bytes: bytes,
) -> tuple[ValidatedRootPackage | None, tuple[ProjectDiscoveryError, ...]]:
    normalized = _normalize_package_manifest_at_path(
        _PACKAGE_MANIFEST_FILENAME,
        manifest_bytes,
    )
    if not normalized.ok:
        return None, normalized.errors
    manifest = normalized.manifest
    assert type(manifest) is PackageManifest
    errors: list[ProjectDiscoveryError] = []

    def add_error(message: str) -> None:
        errors.append(
            _error(
                ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
                message,
                _PACKAGE_MANIFEST_FILENAME,
            )
        )

    if manifest.namespace != occurrence.coordinate.identity.namespace:
        add_error(
            "Package dependency namespace must exactly match the loaded manifest namespace."
        )
    if manifest.name != occurrence.coordinate.identity.name:
        add_error(
            "Package dependency name must exactly match the loaded manifest name."
        )
    if not _is_strict_semver(manifest.version):
        add_error("Loaded package manifest version must be strict SemVer 2.0.0.")
    elif manifest.version != occurrence.coordinate.exact_version:
        add_error(
            "Package dependency version must exactly match the loaded manifest version."
        )
    if errors:
        return None, tuple(errors)

    package = ValidatedRootPackage(
        manifest_path=_PACKAGE_MANIFEST_FILENAME,
        coordinate=occurrence.coordinate,
        content_digest_pin=occurrence.content_digest_pin,
        manifest=manifest,
    )
    return package, ()


def _build_package_load_plan(root_package: LoadedRootPackage) -> PackageLoadPlanResult:
    """Iteratively build declaration-order DFS postorder or fail closed."""

    if type(root_package) is not LoadedRootPackage:
        raise TypeError("Package load planning requires an exact loaded root package.")

    def finish(
        plan: PackageLoadPlan | None,
        *,
        errors: tuple[ProjectDiscoveryError, ...] = (),
        blockers: tuple[PackageLoadPlanBlocker, ...] = (),
        diagnostics: tuple[Diagnostic, ...] = (),
    ) -> PackageLoadPlanResult:
        result = object.__new__(PackageLoadPlanResult)
        object.__setattr__(result, "plan", plan)
        object.__setattr__(result, "errors", errors)
        object.__setattr__(result, "blockers", blockers)
        object.__setattr__(result, "diagnostics", diagnostics)
        return result

    root_error = _verify_loaded_package(root_package)
    if root_error is not None:
        return finish(None, errors=(root_error,))
    validated = _validate_dependency_occurrences(root_package)
    if not validated.ok:
        return finish(None, errors=validated.errors)

    root_key = _package_physical_identity(root_package)
    frames = [
        _Frame(
            package=root_package,
            key=root_key,
            occurrences=validated.occurrences,
            incoming=None,
        )
    ]
    packages_by_key: dict[ProjectPhysicalIdentity, LoadedPackage] = {
        root_key: root_package
    }
    identity_to_key: dict[PackageIdentity, ProjectPhysicalIdentity] = {
        _package_coordinate(root_package).identity: root_key
    }
    incoming_by_key: dict[
        ProjectPhysicalIdentity, PackageDependencyOccurrence | None
    ] = {root_key: None}
    visiting_index: dict[ProjectPhysicalIdentity, int] = {root_key: 0}
    entries: list[PackageLoadPlanEntry] = []
    diagnostics: list[Diagnostic] = []

    while frames:
        frame = frames[-1]
        if frame.next_position == len(frame.occurrences):
            entry = object.__new__(PackageLoadPlanEntry)
            object.__setattr__(entry, "package", frame.package)
            object.__setattr__(entry, "dependencies", tuple(frame.dependencies))
            object.__setattr__(entry, "position", len(entries))
            entries.append(entry)
            visiting_index.pop(frame.key)
            frames.pop()
            continue

        occurrence = frame.occurrences[frame.next_position]
        frame.next_position += 1
        located = _locate_dependency_package(occurrence)
        if type(located) is ProjectDiscoveryError:
            return finish(None, errors=(located,), diagnostics=tuple(diagnostics))
        location = located
        assert type(location) is LocatedDependencyPackage
        key = location.directory_state.physical_identity
        existing = packages_by_key.get(key)

        if existing is not None:
            cycle_index = visiting_index.get(key)
            if cycle_index is not None:
                blocker = _cycle_blocker(
                    frames,
                    cycle_index,
                    occurrence,
                    location,
                )
                return finish(
                    None,
                    blockers=(blocker,),
                    diagnostics=tuple(diagnostics),
                )
            first_occurrence = incoming_by_key[key]
            if not _occurrence_matches_package(occurrence, existing):
                blocker = _conflict_blocker(
                    first_occurrence,
                    occurrence,
                    location,
                    existing,
                )
                return finish(
                    None,
                    blockers=(blocker,),
                    diagnostics=tuple(diagnostics),
                )
            if (
                first_occurrence is not None
                and first_occurrence.declaring_package is occurrence.declaring_package
                and first_occurrence.declaration == occurrence.declaration
                and first_occurrence.resolved_project_path
                == occurrence.resolved_project_path
            ):
                frame.dependencies.append(_edge(occurrence, existing))
                continue
            blocker_kind = (
                PackageLoadPlanBlockerKind.DIAMOND
                if first_occurrence is not None
                and first_occurrence.declaring_package
                is not occurrence.declaring_package
                else PackageLoadPlanBlockerKind.CONFLICT
            )
            blocker = _blocker(
                blocker_kind,
                tuple(
                    item for item in (first_occurrence, occurrence) if item is not None
                ),
                location,
                (existing,),
            )
            return finish(
                None,
                blockers=(blocker,),
                diagnostics=tuple(diagnostics),
            )

        conflicting_key = identity_to_key.get(occurrence.coordinate.identity)
        if conflicting_key is not None and conflicting_key != key:
            existing_package = packages_by_key[conflicting_key]
            blocker = _conflict_blocker(
                incoming_by_key[conflicting_key],
                occurrence,
                location,
                existing_package,
            )
            return finish(
                None,
                blockers=(blocker,),
                diagnostics=tuple(diagnostics),
            )

        loaded, load_errors, load_diagnostics = _load_dependency_package(location)
        diagnostics.extend(load_diagnostics)
        if loaded is None:
            return finish(
                None,
                errors=load_errors,
                diagnostics=tuple(diagnostics),
            )
        child = loaded
        child_validation = _validate_dependency_occurrences(child)
        if not child_validation.ok:
            return finish(
                None,
                errors=child_validation.errors,
                diagnostics=tuple(diagnostics),
            )

        packages_by_key[key] = child
        identity_to_key[occurrence.coordinate.identity] = key
        incoming_by_key[key] = occurrence
        visiting_index[key] = len(frames)
        frame.dependencies.append(_edge(occurrence, child))
        frames.append(
            _Frame(
                package=child,
                key=key,
                occurrences=child_validation.occurrences,
                incoming=occurrence,
            )
        )

    for entry in entries:
        root_error = _verify_loaded_package(entry.package)
        if root_error is not None:
            return finish(
                None,
                errors=(root_error,),
                diagnostics=tuple(diagnostics),
            )
    plan = object.__new__(PackageLoadPlan)
    object.__setattr__(plan, "root_package", root_package)
    object.__setattr__(plan, "entries", tuple(entries))
    return finish(plan, diagnostics=tuple(diagnostics))


def _edge(
    occurrence: PackageDependencyOccurrence,
    package: LoadedPackage,
) -> PackageDependencyEdge:
    edge = object.__new__(PackageDependencyEdge)
    object.__setattr__(edge, "occurrence", occurrence)
    object.__setattr__(edge, "package", package)
    return edge


def _cycle_blocker(
    frames: list[_Frame],
    cycle_index: int,
    occurrence: PackageDependencyOccurrence,
    location: LocatedDependencyPackage,
) -> PackageLoadPlanBlocker:
    cycle_occurrences = tuple(
        frame.incoming
        for frame in frames[cycle_index + 1 :]
        if frame.incoming is not None
    ) + (occurrence,)
    return _blocker(
        PackageLoadPlanBlockerKind.CYCLE,
        cycle_occurrences,
        location,
        tuple(frame.package for frame in frames[cycle_index:]),
    )


def _conflict_blocker(
    first: PackageDependencyOccurrence | None,
    current: PackageDependencyOccurrence,
    location: LocatedDependencyPackage,
    existing: LoadedPackage,
) -> PackageLoadPlanBlocker:
    occurrences = (current,) if first is None else (first, current)
    return _blocker(
        PackageLoadPlanBlockerKind.CONFLICT,
        occurrences,
        location,
        (existing,),
    )


def _blocker(
    kind: PackageLoadPlanBlockerKind,
    occurrences: tuple[PackageDependencyOccurrence, ...],
    location: LocatedDependencyPackage,
    packages: tuple[LoadedPackage, ...],
) -> PackageLoadPlanBlocker:
    blocker = object.__new__(PackageLoadPlanBlocker)
    object.__setattr__(blocker, "kind", kind)
    object.__setattr__(blocker, "occurrences", occurrences)
    object.__setattr__(blocker, "location", location)
    object.__setattr__(blocker, "packages", packages)
    return blocker


def _occurrence_matches_package(
    occurrence: PackageDependencyOccurrence,
    package: LoadedPackage,
) -> bool:
    return occurrence.coordinate == _package_coordinate(
        package
    ) and occurrence.content_digest_pin == _package_content_digest(package)


def _verify_loaded_package(package: LoadedPackage) -> ProjectDiscoveryError | None:
    return _verify_package_root(
        _package_pinned_root(package),
        _package_canonical_path(package),
        _package_directory_state(package),
    )


def _package_catalog(package: LoadedPackage) -> TypedRootPackageAssetCatalog:
    return package.catalog


def _package_coordinate(package: LoadedPackage) -> PackageCoordinate:
    return _package_catalog(package).root_package.coordinate


def _package_content_digest(package: LoadedPackage) -> str:
    return package.content_digest


def _package_project_path(package: LoadedPackage) -> str:
    if type(package) is LoadedRootPackage:
        return package.located_root.activation.path
    if type(package) is LoadedDependencyPackage:
        return package.location.occurrence.resolved_project_path
    raise TypeError("Package path lookup requires an exact loaded package.")


def _package_pinned_root(package: LoadedPackage) -> ProjectPinnedRoot:
    if type(package) is LoadedRootPackage:
        return package.located_root.pinned_root
    if type(package) is LoadedDependencyPackage:
        return package.location.pinned_root
    raise TypeError("Package root lookup requires an exact loaded package.")


def _package_canonical_path(package: LoadedPackage) -> Path:
    if type(package) is LoadedRootPackage:
        return package.located_root.canonical_path
    if type(package) is LoadedDependencyPackage:
        return package.location.canonical_path
    raise TypeError("Package path lookup requires an exact loaded package.")


def _package_directory_state(package: LoadedPackage) -> ProjectFilesystemState:
    if type(package) is LoadedRootPackage:
        return package.located_root.directory_state
    if type(package) is LoadedDependencyPackage:
        return package.location.directory_state
    raise TypeError("Package state lookup requires an exact loaded package.")


def _package_physical_identity(package: LoadedPackage) -> ProjectPhysicalIdentity:
    return _package_directory_state(package).physical_identity


def _dependency_path_error(
    occurrence: PackageDependencyOccurrence,
) -> ProjectDiscoveryError:
    return _error(
        ProjectDiscoveryErrorKind.PROJECT_PATH,
        "Package dependency path escapes the pinned project root.",
        occurrence.declaration.path,
    )
