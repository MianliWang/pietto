"""Private immutable models for project discovery and configuration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pietto.ast_nodes import Script
from pietto.errors import Diagnostic, Severity


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
class ProjectParsedInput:
    """One successfully parsed selected project input for later semantics."""

    path: str
    script: Script


@dataclass(frozen=True, slots=True)
class ProjectSourceConfig:
    """Private project source pattern configuration."""

    include_patterns: tuple[str, ...]
    exclude_patterns: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    """Private parsed project configuration."""

    schema_version: int
    sources: ProjectSourceConfig


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


@dataclass(frozen=True, slots=True)
class ProjectConfigLoadResult:
    """Private project configuration load result."""

    root: ProjectRoot | None
    config_path: ProjectConfigPath | None
    config: ProjectConfig | None
    errors: tuple[ProjectDiscoveryError, ...]

    @property
    def ok(self) -> bool:
        """Return whether configuration loading completed without errors."""

        return not self.errors


@dataclass(frozen=True, slots=True)
class ProjectParseCheckResult:
    """Private parse-only project check result."""

    root: ProjectRoot | None
    config_path: ProjectConfigPath | None
    inputs: tuple[ProjectInput, ...]
    errors: tuple[ProjectDiscoveryError, ...]
    diagnostics: tuple[Diagnostic, ...]
    parsed_inputs: tuple[ProjectParsedInput, ...] = ()

    @property
    def ok(self) -> bool:
        """Return whether parse-only project check completed without errors."""

        return not self.errors and not any(
            diagnostic.severity is Severity.ERROR for diagnostic in self.diagnostics
        )


@dataclass(frozen=True, slots=True)
class ProjectSemanticCatalog:
    """Empty private project semantic catalog placeholder for later slices."""


@dataclass(frozen=True, slots=True)
class ProjectSemanticModel:
    """Private project-wide semantic model scaffold."""

    root: ProjectRoot
    config_path: ProjectConfigPath
    inputs: tuple[ProjectParsedInput, ...]
    catalog: ProjectSemanticCatalog


@dataclass(frozen=True, slots=True)
class ProjectSemanticResult:
    """Private project-wide semantic scaffold result."""

    root: ProjectRoot | None
    config_path: ProjectConfigPath | None
    model: ProjectSemanticModel | None
    diagnostics: tuple[Diagnostic, ...] = ()

    @property
    def ok(self) -> bool:
        """Return whether project semantic scaffolding completed without errors."""

        return self.model is not None and not any(
            diagnostic.severity is Severity.ERROR for diagnostic in self.diagnostics
        )


def build_empty_project_semantic_result(
    parse_result: ProjectParseCheckResult,
) -> ProjectSemanticResult:
    """Build the empty private project semantic scaffold from parse-only input."""

    if (
        not parse_result.ok
        or parse_result.root is None
        or parse_result.config_path is None
    ):
        return ProjectSemanticResult(
            root=parse_result.root,
            config_path=parse_result.config_path,
            model=None,
        )

    return ProjectSemanticResult(
        root=parse_result.root,
        config_path=parse_result.config_path,
        model=ProjectSemanticModel(
            root=parse_result.root,
            config_path=parse_result.config_path,
            inputs=parse_result.parsed_inputs,
            catalog=ProjectSemanticCatalog(),
        ),
    )
