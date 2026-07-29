"""Private immutable selected-project-input index."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING

from pietto._project.module_carrier import ProjectModuleIdentity
from pietto._project.path_trust import (
    ProjectFilesystemState,
    ProjectPinnedRoot,
    ProjectPhysicalIdentity,
)

if TYPE_CHECKING:
    from pietto._project.model import ProjectInput

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectSelectedInputEntry:
    """One validated selected source and its private trust facts."""

    identity: ProjectModuleIdentity
    position: int
    project_input: ProjectInput = field(repr=False)
    canonical_path: Path = field(repr=False)
    logical_leaf_state: ProjectFilesystemState = field(repr=False)
    final_target_state: ProjectFilesystemState = field(repr=False)
    final_leaf_is_symlink: bool
    symlink_target: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Reject malformed or internally inconsistent selected facts."""

        from pietto._project.model import ProjectInput

        if type(self.identity) is not ProjectModuleIdentity:
            raise TypeError("Selected input entry requires a module identity.")
        if type(self.position) is not int or self.position < 0:
            raise ValueError(
                "Selected input entry position must be a non-negative integer."
            )
        if type(self.project_input) is not ProjectInput:
            raise TypeError("Selected input entry requires a project input.")
        if self.project_input.path != self.identity.path:
            raise ValueError("Selected input entry path facts must match.")
        if not self.canonical_path.is_absolute():
            raise ValueError("Selected input canonical path must be absolute.")
        if type(self.final_leaf_is_symlink) is not bool:
            raise TypeError("Selected input symlink fact must be boolean.")
        if self.final_leaf_is_symlink != (self.symlink_target is not None):
            raise ValueError("Selected input symlink facts must agree.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectSelectedInputIndex:
    """Ordered exact lookup over validated selected project inputs."""

    pinned_root: ProjectPinnedRoot = field(repr=False)
    entries: tuple[ProjectSelectedInputEntry, ...]
    _entries_by_identity: Mapping[ProjectModuleIdentity, ProjectSelectedInputEntry] = (
        field(init=False, repr=False, compare=False, hash=False)
    )

    def __post_init__(self) -> None:
        """Copy lookup state and reject duplicate or misordered entries."""

        if type(self.pinned_root) is not ProjectPinnedRoot:
            raise TypeError("Selected input index requires a pinned root.")
        if type(self.entries) is not tuple:
            raise TypeError("Selected input index entries must be a tuple.")
        if any(type(entry) is not ProjectSelectedInputEntry for entry in self.entries):
            raise TypeError("Selected input index requires selected entries.")
        positions = tuple(entry.position for entry in self.entries)
        if positions != tuple(range(len(self.entries))):
            raise ValueError("Selected input index positions must be contiguous.")

        entries_by_identity: dict[ProjectModuleIdentity, ProjectSelectedInputEntry] = {}
        physical_identities: set[ProjectPhysicalIdentity] = set()
        for entry in self.entries:
            if entry.identity in entries_by_identity:
                raise ValueError("Selected input index logical keys must be unique.")
            if entry.final_target_state.physical_identity in physical_identities:
                raise ValueError(
                    "Selected input index physical identities must be unique."
                )
            try:
                relative_path = entry.canonical_path.relative_to(
                    self.pinned_root.canonical_path
                )
            except ValueError as error:
                raise ValueError(
                    "Selected input index canonical paths must remain inside the root."
                ) from error
            if relative_path.is_absolute() or ".." in relative_path.parts:
                raise ValueError(
                    "Selected input index canonical paths must remain inside the root."
                )
            entries_by_identity[entry.identity] = entry
            physical_identities.add(entry.final_target_state.physical_identity)

        object.__setattr__(
            self,
            "_entries_by_identity",
            MappingProxyType(dict(entries_by_identity)),
        )

    def find(self, identity: ProjectModuleIdentity) -> ProjectSelectedInputEntry | None:
        """Return the exact selected entry for an identity, or None."""

        return self._entries_by_identity.get(identity)

    def find_path(self, path: str) -> ProjectSelectedInputEntry | None:
        """Return the exact selected entry for a logical path, or None."""

        try:
            identity = ProjectModuleIdentity(path=path)
        except (TypeError, ValueError):
            return None
        return self.find(identity)
