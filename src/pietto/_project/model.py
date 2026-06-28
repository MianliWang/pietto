"""Private immutable models for project discovery."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ProjectDiscoveryErrorKind(StrEnum):
    """Private project discovery error categories."""

    PROJECT_ROOT = "project_root"
    CONFIG_READ = "config_read"
    CONFIG_PARSE = "config_parse"
    CONFIG_SCHEMA = "config_schema"
    PROJECT_PATH = "project_path"
    PROJECT_GLOB = "project_glob"
    PROJECT_RESOURCE = "project_resource"
    SOURCE_READ = "source_read"


@dataclass(frozen=True, slots=True)
class ProjectRoot:
    """Established project root as a project-relative identity."""

    path: str


@dataclass(frozen=True, slots=True)
class ProjectConfigPath:
    """Project configuration path relative to the established root."""

    path: str


@dataclass(frozen=True, slots=True)
class ProjectInput:
    """One explicitly selected project input."""

    path: str
    status: str


@dataclass(frozen=True, slots=True)
class ProjectDiscoveryError:
    """One private project discovery error."""

    kind: ProjectDiscoveryErrorKind
    message: str
    path: str | None = None


@dataclass(frozen=True, slots=True)
class ProjectDiscoveryResult:
    """Private project discovery result for future project-mode orchestration."""

    root: ProjectRoot | None
    config_path: ProjectConfigPath | None
    inputs: tuple[ProjectInput, ...]
    errors: tuple[ProjectDiscoveryError, ...]

    @property
    def ok(self) -> bool:
        """Return whether discovery completed without private project errors."""

        return not self.errors
