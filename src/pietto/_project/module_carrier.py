"""Private immutable project compilation-mode and logical-module carriers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pietto._project.model import ProjectInput, ProjectParsedInput

__all__: tuple[str, ...] = ()


class ProjectCompilationMode(StrEnum):
    """Private project-wide compilation mode selected by config schema version."""

    LEGACY_FLAT = "legacy_flat"
    EXPLICIT_MODULES = "explicit_modules"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleIdentity:
    """Stable private module identity defined only by its logical path."""

    path: str

    def __post_init__(self) -> None:
        """Reject paths outside the exact selected module identity contract."""

        if (
            type(self.path) is not str
            or not _is_normalized_project_relative_path(self.path)
            or not self.path.endswith(".pietto")
        ):
            raise ValueError(
                "Project module identity path must be a normalized project-relative "
                ".pietto path."
            )


@dataclass(frozen=True, slots=True)
class ProjectLogicalModule:
    """One ordered logical module for an existing selected project input."""

    compilation_mode: ProjectCompilationMode
    path: str
    position: int
    project_input: ProjectInput
    parsed_input: ProjectParsedInput | None = None

    def __post_init__(self) -> None:
        """Reject malformed or mismatched private carrier facts."""

        from pietto._project.model import ProjectInput, ProjectParsedInput

        if type(self.compilation_mode) is not ProjectCompilationMode:
            raise TypeError("Project logical module requires a compilation mode.")
        if type(self.path) is not str or not _is_normalized_project_relative_path(
            self.path
        ):
            raise ValueError(
                "Project logical module path must be normalized and project-relative."
            )
        if type(self.position) is not int or self.position < 0:
            raise ValueError(
                "Project logical module position must be a non-negative integer."
            )
        if type(self.project_input) is not ProjectInput:
            raise TypeError("Project logical module requires a project input.")
        if self.project_input.path != self.path:
            raise ValueError(
                "Project logical module path must match its project input."
            )
        if self.parsed_input is not None:
            if type(self.parsed_input) is not ProjectParsedInput:
                raise TypeError(
                    "Project logical module parsed input must be a project parsed input."
                )
            if self.parsed_input.path != self.path:
                raise ValueError(
                    "Project logical module path must match its parsed input."
                )

    @property
    def identity(self) -> ProjectModuleIdentity:
        """Return the path-only stable private identity for this module."""

        return ProjectModuleIdentity(path=self.path)


def _build_project_logical_modules(
    compilation_mode: ProjectCompilationMode,
    inputs: tuple[ProjectInput, ...],
    parsed_inputs: tuple[ProjectParsedInput, ...] = (),
) -> tuple[ProjectLogicalModule, ...]:
    """Build one ordered private logical module per existing project input."""

    input_paths = tuple(project_input.path for project_input in inputs)
    if len(set(input_paths)) != len(input_paths):
        raise ValueError("Project logical module input paths must be unique.")

    parsed_by_path: dict[str, ProjectParsedInput] = {}
    for parsed_input in parsed_inputs:
        if parsed_input.path in parsed_by_path:
            raise ValueError("Project logical module parsed paths must be unique.")
        parsed_by_path[parsed_input.path] = parsed_input

    if set(parsed_by_path) - set(input_paths):
        raise ValueError("Project logical modules reject unmatched parsed inputs.")

    return tuple(
        ProjectLogicalModule(
            compilation_mode=compilation_mode,
            path=project_input.path,
            position=position,
            project_input=project_input,
            parsed_input=parsed_by_path.get(project_input.path),
        )
        for position, project_input in enumerate(inputs)
    )


def _is_normalized_project_relative_path(value: str) -> bool:
    if not value or "\x00" in value or "\\" in value:
        return False
    if Path(value).is_absolute() or value.startswith("/"):
        return False
    if _is_windows_drive_path(value) or value.startswith("//"):
        return False
    if value.endswith("/"):
        return False
    return all(part not in {"", ".", ".."} for part in value.split("/"))


def _is_windows_drive_path(value: str) -> bool:
    return len(value) >= 2 and value[0].isalpha() and value[1] == ":"
