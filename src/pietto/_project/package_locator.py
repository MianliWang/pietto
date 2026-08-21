"""Private trusted local root-package location and containment."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pietto._project.model import (
    ProjectDiscoveryError,
    ProjectDiscoveryErrorKind,
    ProjectRootPackageActivation,
)
from pietto._project.path_trust import (
    ProjectFilesystemState,
    ProjectIdentityUnavailableError,
    ProjectPinnedRoot,
    ProjectRootChangedError,
    ProjectSymbolicLinkTraversalError,
    _capture_pinned_directory_state,
)

__all__: tuple[str, ...] = ()

_ErrorSpec = tuple[ProjectDiscoveryErrorKind, str, str | None]


@dataclass(frozen=True, slots=True, init=False)
class LocatedRootPackage:
    """One exact activation bound to one trusted local directory identity."""

    pinned_root: ProjectPinnedRoot = field(repr=False)
    activation: ProjectRootPackageActivation
    canonical_path: Path = field(repr=False)
    directory_state: ProjectFilesystemState = field(repr=False)

    def __new__(cls) -> LocatedRootPackage:
        raise TypeError("Located package roots are created only by canonical location.")


@dataclass(frozen=True, slots=True, init=False)
class PackageRootLocationResult:
    """One complete trusted root location or deterministic error tuple."""

    located_root: LocatedRootPackage | None
    errors: tuple[ProjectDiscoveryError, ...]

    def __new__(cls) -> PackageRootLocationResult:
        raise TypeError("Package root results are created only by canonical location.")

    @property
    def ok(self) -> bool:
        """Return whether one trusted located root was produced."""

        return self.located_root is not None


def _locate_root_package(
    pinned_root: ProjectPinnedRoot,
    activation: ProjectRootPackageActivation,
) -> PackageRootLocationResult:
    """Locate one explicit package directory beneath an exact pinned root."""

    if type(pinned_root) is not ProjectPinnedRoot:
        raise TypeError("Package root location requires an exact pinned root.")
    if type(activation) is not ProjectRootPackageActivation:
        raise TypeError("Package root location requires an exact activation.")

    canonical_path = (
        pinned_root.canonical_path
        if activation.path == "."
        else pinned_root.canonical_path.joinpath(*activation.path.split("/"))
    )

    def construct_result(
        located_root: LocatedRootPackage | None,
        error_specs: tuple[_ErrorSpec, ...],
    ) -> PackageRootLocationResult:
        if located_root is not None:
            if type(located_root) is not LocatedRootPackage:
                raise TypeError("Canonical location requires an exact located root.")
            if (
                located_root.pinned_root is not pinned_root
                or located_root.activation is not activation
                or located_root.canonical_path != canonical_path
            ):
                raise ValueError("Canonical location requires exact caller authority.")
        if type(error_specs) is not tuple:
            raise TypeError("Canonical location errors must be an exact tuple.")
        errors: list[ProjectDiscoveryError] = []
        for error_spec in error_specs:
            if type(error_spec) is not tuple or len(error_spec) != 3:
                raise TypeError("Canonical location requires primitive error specs.")
            kind, message, path = error_spec
            if type(kind) is not ProjectDiscoveryErrorKind:
                raise TypeError("Canonical location requires an exact error kind.")
            if type(message) is not str:
                raise TypeError("Canonical location error text must be exact.")
            if path is not None and type(path) is not str:
                raise TypeError("Canonical location error path must be exact.")
            errors.append(ProjectDiscoveryError(kind, message, path))
        if (located_root is None) is (not errors):
            raise ValueError(
                "Canonical location requires exactly one of a located root or errors."
            )
        result = object.__new__(PackageRootLocationResult)
        object.__setattr__(result, "located_root", located_root)
        object.__setattr__(result, "errors", tuple(errors))
        return result

    try:
        relative_path = canonical_path.relative_to(pinned_root.canonical_path)
    except ValueError:
        return construct_result(
            None,
            (
                (
                    ProjectDiscoveryErrorKind.PROJECT_PATH,
                    "Project package root path escapes the pinned project root.",
                    activation.path,
                ),
            ),
        )
    if relative_path.is_absolute() or ".." in relative_path.parts:
        return construct_result(
            None,
            (
                (
                    ProjectDiscoveryErrorKind.PROJECT_PATH,
                    "Project package root path escapes the pinned project root.",
                    activation.path,
                ),
            ),
        )

    try:
        directory_state = _capture_pinned_directory_state(
            pinned_root,
            canonical_path,
        )
    except ProjectRootChangedError:
        return construct_result(
            None,
            (
                (
                    ProjectDiscoveryErrorKind.PROJECT_ROOT,
                    "Project root identity changed during project loading.",
                    None,
                ),
            ),
        )
    except ProjectIdentityUnavailableError:
        return construct_result(
            None,
            (
                (
                    ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
                    "Project filesystem identity is unavailable.",
                    None,
                ),
            ),
        )
    except ProjectSymbolicLinkTraversalError:
        return construct_result(
            None,
            (
                (
                    ProjectDiscoveryErrorKind.PROJECT_PATH,
                    "Project package root path must not traverse symbolic links.",
                    activation.path,
                ),
            ),
        )
    except (OSError, RuntimeError):
        return construct_result(
            None,
            (
                (
                    ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
                    "Project package root must be an accessible existing directory and remain unchanged during location.",
                    activation.path,
                ),
            ),
        )

    if type(directory_state) is not ProjectFilesystemState:
        raise TypeError("Package root location requires an exact filesystem state.")
    located_root = object.__new__(LocatedRootPackage)
    object.__setattr__(located_root, "pinned_root", pinned_root)
    object.__setattr__(located_root, "activation", activation)
    object.__setattr__(located_root, "canonical_path", canonical_path)
    object.__setattr__(located_root, "directory_state", directory_state)
    return construct_result(located_root, ())
