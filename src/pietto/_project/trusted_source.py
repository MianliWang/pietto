"""Private trusted project-source loading and snapshot facts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
import os
import stat

from pietto._project.module_carrier import ProjectModuleIdentity
from pietto._project.path_trust import (
    ProjectFilesystemState,
    ProjectIdentityUnavailableError,
    ProjectPinnedRoot,
    ProjectRootChangedError,
    _fstat_state,
    _lstat_state,
    _open_pinned_file,
    _stat_state,
    _verify_pinned_root,
)
from pietto._project.selected_input_index import ProjectSelectedInputEntry
from pietto.errors import Diagnostic, Severity, SourceLocation

__all__: tuple[str, ...] = ()

_PROJECT_SOURCE_UTF8_BYTES = 1_048_576


class ProjectTrustedSourceFailure(StrEnum):
    """Private reasons adapted to existing project discovery errors."""

    ROOT_CHANGED = "root_changed"
    IDENTITY_UNAVAILABLE = "identity_unavailable"
    SYMBOLIC_LINK_CHANGED = "symbolic_link_changed"
    SOURCE_CHANGED = "source_changed"
    OPENED_IDENTITY_MISMATCH = "opened_identity_mismatch"
    NOT_REGULAR = "not_regular"
    READ_MUTATION = "read_mutation"


class ProjectTrustedSourceError(OSError):
    """Private trusted-loader failure with one stable adaptation reason."""

    def __init__(self, reason: ProjectTrustedSourceFailure) -> None:
        super().__init__(reason.value)
        self.reason = reason


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectTrustedSourceSnapshot:
    """Exact accepted bytes, digest, and decoded text for one selected input."""

    selected_input: ProjectSelectedInputEntry = field(repr=False)
    byte_count: int
    sha256: str = field(repr=False)
    source_text: str = field(repr=False)
    opened_target_state: ProjectFilesystemState = field(repr=False)

    def __post_init__(self) -> None:
        """Reject malformed or mismatched trusted snapshot facts."""

        if type(self.selected_input) is not ProjectSelectedInputEntry:
            raise TypeError("Trusted source snapshot requires a selected input.")
        if type(self.byte_count) is not int or self.byte_count < 0:
            raise ValueError("Trusted source byte count must be non-negative.")
        if (
            type(self.sha256) is not str
            or len(self.sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.sha256)
        ):
            raise ValueError("Trusted source SHA-256 must be lowercase hexadecimal.")
        if type(self.source_text) is not str:
            raise TypeError("Trusted source text must be a string.")
        if self.opened_target_state != self.selected_input.final_target_state:
            raise ValueError("Trusted source opened state must match selection.")
        source_bytes = self.source_text.encode("utf-8")
        if self.byte_count != len(source_bytes):
            raise ValueError("Trusted source byte count must match source text.")
        if self.sha256 != hashlib.sha256(source_bytes).hexdigest():
            raise ValueError("Trusted source SHA-256 must match source text.")

    @property
    def identity(self) -> ProjectModuleIdentity:
        """Return the stable logical module identity."""

        return self.selected_input.identity

    @property
    def path(self) -> str:
        """Return the stable logical project-relative source path."""

        return self.identity.path

    @property
    def position(self) -> int:
        """Return the stable selected-input position."""

        return self.selected_input.position


def _load_trusted_source(
    pinned_root: ProjectPinnedRoot,
    selected_input: ProjectSelectedInputEntry,
    *,
    byte_limit: int,
) -> ProjectTrustedSourceSnapshot | Diagnostic:
    """Load, verify, digest, and decode one exact selected source descriptor."""

    if type(byte_limit) is not int or byte_limit != _PROJECT_SOURCE_UTF8_BYTES:
        raise ValueError("Trusted source byte limit must be exactly 1048576.")

    _verify_selected_input(pinned_root, selected_input, after_read=False)
    file_descriptor = -1
    try:
        file_descriptor = _open_pinned_file(
            pinned_root,
            selected_input.canonical_path,
        )
        opened_state = _fstat_state(file_descriptor)
        if not stat.S_ISREG(opened_state.file_type):
            _verify_trusted_root(pinned_root)
            raise ProjectTrustedSourceError(ProjectTrustedSourceFailure.NOT_REGULAR)
        if (
            opened_state.physical_identity
            != selected_input.final_target_state.physical_identity
        ):
            _verify_trusted_root(pinned_root)
            raise ProjectTrustedSourceError(
                ProjectTrustedSourceFailure.OPENED_IDENTITY_MISMATCH
            )
        if opened_state != selected_input.final_target_state:
            _verify_trusted_root(pinned_root)
            raise ProjectTrustedSourceError(ProjectTrustedSourceFailure.SOURCE_CHANGED)

        with os.fdopen(file_descriptor, "rb", closefd=True) as source_file:
            file_descriptor = -1
            source_bytes = source_file.read(byte_limit + 1)
            final_opened_state = _fstat_state(source_file.fileno())
    except ProjectTrustedSourceError:
        raise
    except ProjectRootChangedError as error:
        raise ProjectTrustedSourceError(
            ProjectTrustedSourceFailure.ROOT_CHANGED
        ) from error
    except ProjectIdentityUnavailableError as error:
        raise ProjectTrustedSourceError(
            ProjectTrustedSourceFailure.IDENTITY_UNAVAILABLE
        ) from error
    finally:
        if file_descriptor >= 0:
            os.close(file_descriptor)

    if final_opened_state != opened_state:
        _verify_trusted_root(pinned_root)
        raise ProjectTrustedSourceError(ProjectTrustedSourceFailure.READ_MUTATION)
    _verify_selected_input(pinned_root, selected_input, after_read=True)

    if len(source_bytes) > byte_limit:
        return Diagnostic(
            code="PIE-P1006",
            severity=Severity.ERROR,
            message=(
                "Source exceeds the maximum supported size of "
                f"{byte_limit} UTF-8 bytes."
            ),
            location=SourceLocation(
                path=selected_input.identity.path,
                line=1,
                column=1,
            ),
        )

    digest = hashlib.sha256(source_bytes).hexdigest()
    source_text = source_bytes.decode("utf-8")
    return ProjectTrustedSourceSnapshot(
        selected_input=selected_input,
        byte_count=len(source_bytes),
        sha256=digest,
        source_text=source_text,
        opened_target_state=opened_state,
    )


def _verify_selected_input(
    pinned_root: ProjectPinnedRoot,
    selected_input: ProjectSelectedInputEntry,
    *,
    after_read: bool,
) -> None:
    """Require current root, leaf, and followed target to match selection."""

    _verify_trusted_root(pinned_root)
    logical_path = pinned_root.canonical_path / selected_input.identity.path
    selected_was_symlink = selected_input.final_leaf_is_symlink
    try:
        logical_state = _lstat_state(logical_path)
    except ProjectIdentityUnavailableError as error:
        raise ProjectTrustedSourceError(
            ProjectTrustedSourceFailure.IDENTITY_UNAVAILABLE
        ) from error
    except OSError as error:
        _verify_trusted_root(pinned_root)
        reason = (
            ProjectTrustedSourceFailure.READ_MUTATION
            if after_read
            else (
                ProjectTrustedSourceFailure.SYMBOLIC_LINK_CHANGED
                if selected_was_symlink
                else ProjectTrustedSourceFailure.SOURCE_CHANGED
            )
        )
        raise ProjectTrustedSourceError(reason) from error

    current_is_symlink = stat.S_ISLNK(logical_state.file_type)
    try:
        symlink_target = os.readlink(logical_path) if current_is_symlink else None
    except OSError as error:
        _verify_trusted_root(pinned_root)
        reason = (
            ProjectTrustedSourceFailure.READ_MUTATION
            if after_read
            else ProjectTrustedSourceFailure.SYMBOLIC_LINK_CHANGED
        )
        raise ProjectTrustedSourceError(reason) from error

    symlink_changed = selected_was_symlink and (
        not current_is_symlink
        or logical_state != selected_input.logical_leaf_state
        or symlink_target != selected_input.symlink_target
    )
    leaf_changed = not selected_was_symlink and (
        logical_state != selected_input.logical_leaf_state
    )
    if after_read and (symlink_changed or leaf_changed):
        _verify_trusted_root(pinned_root)
        raise ProjectTrustedSourceError(ProjectTrustedSourceFailure.READ_MUTATION)
    if symlink_changed:
        _verify_trusted_root(pinned_root)
        raise ProjectTrustedSourceError(
            ProjectTrustedSourceFailure.SYMBOLIC_LINK_CHANGED
        )
    if leaf_changed:
        _verify_trusted_root(pinned_root)
        raise ProjectTrustedSourceError(ProjectTrustedSourceFailure.SOURCE_CHANGED)

    try:
        final_state = _stat_state(logical_path)
    except ProjectIdentityUnavailableError as error:
        raise ProjectTrustedSourceError(
            ProjectTrustedSourceFailure.IDENTITY_UNAVAILABLE
        ) from error
    except OSError as error:
        _verify_trusted_root(pinned_root)
        reason = (
            ProjectTrustedSourceFailure.READ_MUTATION
            if after_read
            else ProjectTrustedSourceFailure.SOURCE_CHANGED
        )
        raise ProjectTrustedSourceError(reason) from error
    if final_state != selected_input.final_target_state:
        _verify_trusted_root(pinned_root)
        reason = (
            ProjectTrustedSourceFailure.READ_MUTATION
            if after_read
            else ProjectTrustedSourceFailure.SOURCE_CHANGED
        )
        raise ProjectTrustedSourceError(reason)

    try:
        canonical_leaf_state = _lstat_state(selected_input.canonical_path)
    except ProjectIdentityUnavailableError as error:
        raise ProjectTrustedSourceError(
            ProjectTrustedSourceFailure.IDENTITY_UNAVAILABLE
        ) from error
    except OSError as error:
        _verify_trusted_root(pinned_root)
        reason = (
            ProjectTrustedSourceFailure.READ_MUTATION
            if after_read
            else ProjectTrustedSourceFailure.SOURCE_CHANGED
        )
        raise ProjectTrustedSourceError(reason) from error
    if (
        not stat.S_ISREG(canonical_leaf_state.file_type)
        or canonical_leaf_state != selected_input.final_target_state
    ):
        _verify_trusted_root(pinned_root)
        reason = (
            ProjectTrustedSourceFailure.READ_MUTATION
            if after_read
            else ProjectTrustedSourceFailure.SOURCE_CHANGED
        )
        raise ProjectTrustedSourceError(reason)
    _verify_trusted_root(pinned_root)


def _verify_trusted_root(pinned_root: ProjectPinnedRoot) -> None:
    """Adapt pinned-root trust failures to trusted-loader failure reasons."""

    try:
        _verify_pinned_root(pinned_root)
    except ProjectRootChangedError as error:
        raise ProjectTrustedSourceError(
            ProjectTrustedSourceFailure.ROOT_CHANGED
        ) from error
    except ProjectIdentityUnavailableError as error:
        raise ProjectTrustedSourceError(
            ProjectTrustedSourceFailure.IDENTITY_UNAVAILABLE
        ) from error
