"""Private pinned-root and filesystem identity helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import stat

__all__: tuple[str, ...] = ()


class ProjectIdentityUnavailableError(OSError):
    """Signal that the filesystem cannot provide a meaningful identity."""


class ProjectRootChangedError(OSError):
    """Signal that a pinned project root no longer has its pinned identity."""


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPhysicalIdentity:
    """Private stable physical identity for one filesystem object."""

    device: int = field(repr=False)
    inode: int = field(repr=False)

    def __post_init__(self) -> None:
        """Reject unavailable or malformed identity values."""

        if type(self.device) is not int or type(self.inode) is not int:
            raise TypeError("Project physical identity requires integer values.")
        if self.device < 0 or self.inode <= 0:
            raise ProjectIdentityUnavailableError(
                "Project filesystem identity is unavailable."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectFilesystemState:
    """Private metadata consistency facts for one filesystem object."""

    physical_identity: ProjectPhysicalIdentity = field(repr=False)
    file_type: int = field(repr=False)
    size: int = field(repr=False)
    mtime_ns: int = field(repr=False)
    ctime_ns: int = field(repr=False)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPinnedRoot:
    """One once-resolved private project-root trust context."""

    display_path: str
    invocation_path: Path = field(repr=False)
    canonical_path: Path = field(repr=False)
    physical_identity: ProjectPhysicalIdentity = field(repr=False)

    def __post_init__(self) -> None:
        """Reject malformed pinned-root carrier facts."""

        if self.display_path != ".":
            raise ValueError("Project pinned root display path must be '.'.")
        if not self.invocation_path.is_absolute():
            raise ValueError("Project pinned root invocation path must be absolute.")
        if not self.canonical_path.is_absolute():
            raise ValueError("Project pinned root canonical path must be absolute.")


def _pin_project_root(root: str | Path) -> ProjectPinnedRoot:
    """Resolve the invocation root exactly once and pin its physical identity."""

    invocation_path = Path(root).absolute()
    canonical_path = Path(root).resolve(strict=True)
    root_state = _stat_state(canonical_path)
    if not stat.S_ISDIR(root_state.file_type):
        raise NotADirectoryError("Project root must be an existing directory.")
    return ProjectPinnedRoot(
        display_path=".",
        invocation_path=invocation_path,
        canonical_path=canonical_path,
        physical_identity=root_state.physical_identity,
    )


def _verify_pinned_root(pinned_root: ProjectPinnedRoot) -> None:
    """Require both invocation and canonical paths to retain the pinned root."""

    try:
        invocation_state = _stat_state(pinned_root.invocation_path)
        canonical_state = _stat_state(pinned_root.canonical_path)
    except ProjectIdentityUnavailableError:
        raise
    except OSError as error:
        raise ProjectRootChangedError(
            "Project root identity changed during project loading."
        ) from error

    for current_state in (invocation_state, canonical_state):
        if (
            not stat.S_ISDIR(current_state.file_type)
            or current_state.physical_identity != pinned_root.physical_identity
        ):
            raise ProjectRootChangedError(
                "Project root identity changed during project loading."
            )


def _lstat_state(path: Path) -> ProjectFilesystemState:
    """Return no-follow metadata consistency facts for one path."""

    return _filesystem_state(os.lstat(path))


def _stat_state(path: Path) -> ProjectFilesystemState:
    """Return followed metadata consistency facts for one path."""

    return _filesystem_state(os.stat(path))


def _fstat_state(file_descriptor: int) -> ProjectFilesystemState:
    """Return metadata consistency facts for one opened descriptor."""

    return _filesystem_state(os.fstat(file_descriptor))


def _filesystem_state(stat_result: os.stat_result) -> ProjectFilesystemState:
    """Convert standard-library stat facts into an immutable private value."""

    return ProjectFilesystemState(
        physical_identity=ProjectPhysicalIdentity(
            device=stat_result.st_dev,
            inode=stat_result.st_ino,
        ),
        file_type=stat.S_IFMT(stat_result.st_mode),
        size=stat_result.st_size,
        mtime_ns=stat_result.st_mtime_ns,
        ctime_ns=stat_result.st_ctime_ns,
    )


def _open_pinned_file(pinned_root: ProjectPinnedRoot, path: Path) -> int:
    """Open one stored canonical path beneath a verified pinned root."""

    _verify_pinned_root(pinned_root)
    relative_path = path.relative_to(pinned_root.canonical_path)
    if (
        relative_path.is_absolute()
        or not relative_path.parts
        or relative_path == Path(".")
        or ".." in relative_path.parts
    ):
        raise OSError("Project stored canonical path escapes the pinned root.")
    flags = os.O_RDONLY
    flags |= getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)

    if _supports_directory_relative_open():
        directory_flags = os.O_RDONLY
        directory_flags |= getattr(os, "O_CLOEXEC", 0)
        directory_flags |= getattr(os, "O_DIRECTORY", 0)
        directory_flags |= getattr(os, "O_NOFOLLOW", 0)
        directory_flags |= getattr(os, "O_NONBLOCK", 0)
        try:
            root_descriptor = os.open(pinned_root.canonical_path, directory_flags)
        except OSError:
            _verify_pinned_root(pinned_root)
            raise
        directory_descriptors = [root_descriptor]
        file_descriptor = -1
        try:
            root_state = _fstat_state(directory_descriptors[0])
            if (
                not stat.S_ISDIR(root_state.file_type)
                or root_state.physical_identity != pinned_root.physical_identity
            ):
                raise ProjectRootChangedError(
                    "Project root identity changed during project loading."
                )
            for component in relative_path.parts[:-1]:
                directory_descriptor = os.open(
                    component,
                    directory_flags,
                    dir_fd=directory_descriptors[-1],
                )
                directory_descriptors.append(directory_descriptor)
                directory_state = _fstat_state(directory_descriptor)
                if not stat.S_ISDIR(directory_state.file_type):
                    raise OSError(
                        "Project stored canonical parent must remain a directory."
                    )
            file_descriptor = os.open(
                relative_path.parts[-1],
                flags,
                dir_fd=directory_descriptors[-1],
            )
        except BaseException as error:
            descriptors_to_close = directory_descriptors
            if file_descriptor >= 0:
                descriptors_to_close = [*descriptors_to_close, file_descriptor]
            try:
                _close_file_descriptors(descriptors_to_close)
            except OSError:
                pass
            if isinstance(error, OSError) and not isinstance(
                error,
                (ProjectIdentityUnavailableError, ProjectRootChangedError),
            ):
                _verify_pinned_root(pinned_root)
            raise
        try:
            _close_file_descriptors(directory_descriptors)
            _verify_pinned_root(pinned_root)
        except BaseException:
            try:
                os.close(file_descriptor)
            except OSError:
                pass
            raise
        return file_descriptor

    try:
        inspected_state = _lstat_state(path)
    except ProjectIdentityUnavailableError:
        raise
    except OSError:
        _verify_pinned_root(pinned_root)
        raise
    if not stat.S_ISREG(inspected_state.file_type):
        _verify_pinned_root(pinned_root)
        raise OSError("Project stored canonical path must remain a regular file.")
    try:
        file_descriptor = os.open(path, flags)
    except OSError:
        _verify_pinned_root(pinned_root)
        raise
    try:
        opened_state = _fstat_state(file_descriptor)
        try:
            final_inspected_state = _lstat_state(path)
        except ProjectIdentityUnavailableError:
            raise
        except OSError:
            _verify_pinned_root(pinned_root)
            raise
        _verify_pinned_root(pinned_root)
        if (
            not stat.S_ISREG(opened_state.file_type)
            or opened_state != inspected_state
            or final_inspected_state != inspected_state
        ):
            raise OSError("Project stored canonical file changed while being opened.")
    except BaseException:
        try:
            os.close(file_descriptor)
        except OSError:
            pass
        raise
    return file_descriptor


def _close_file_descriptors(file_descriptors: list[int]) -> None:
    """Close every transient directory descriptor, preserving first failure."""

    first_error: OSError | None = None
    for file_descriptor in reversed(file_descriptors):
        try:
            os.close(file_descriptor)
        except OSError as error:
            if first_error is None:
                first_error = error
    if first_error is not None:
        raise first_error


def _supports_directory_relative_open() -> bool:
    """Return whether the platform exposes the stronger private open contract."""

    return (
        os.open in os.supports_dir_fd
        and hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
    )
