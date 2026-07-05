"""Private parse-only project check orchestration."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pietto.parser_api as parser_api
from pietto._project.config import load_project_config
from pietto._project.model import (
    ProjectConfigPath,
    ProjectDiscoveryError,
    ProjectDiscoveryErrorKind,
    ProjectInput,
    ProjectParseCheckResult,
    ProjectRoot,
)
from pietto._project.source_selection import select_project_sources
from pietto.errors import Diagnostic, Severity

_PROJECT_ROOT_PATH = "."
_PROJECT_CONFIG_PATH = "pietto.toml"
_PARSED_STATUS = "parsed"
_ERROR_STATUS = "error"


def check_project_parse_only(root: str | Path) -> ProjectParseCheckResult:
    """Load, select, read, and parse project sources without semantic analysis."""

    config_result = load_project_config(root)
    selection_result = select_project_sources(root, config_result)
    if selection_result.errors:
        return ProjectParseCheckResult(
            root=selection_result.root,
            config_path=selection_result.config_path,
            inputs=selection_result.inputs,
            errors=selection_result.errors,
            diagnostics=(),
        )

    try:
        resolved_root = Path(root).resolve(strict=True)
    except OSError:
        return _root_error("Project root does not exist or is not accessible.")

    if not resolved_root.is_dir():
        return _root_error("Project root must be an existing directory.")

    inputs: list[ProjectInput] = []
    errors: list[ProjectDiscoveryError] = []
    diagnostics: list[Diagnostic] = []
    for selected_input in selection_result.inputs:
        parsed_input, input_errors, input_diagnostics = _parse_selected_input(
            resolved_root,
            selected_input,
        )
        inputs.append(parsed_input)
        errors.extend(input_errors)
        diagnostics.extend(input_diagnostics)

    return ProjectParseCheckResult(
        root=selection_result.root or ProjectRoot(path=_PROJECT_ROOT_PATH),
        config_path=selection_result.config_path
        or ProjectConfigPath(path=_PROJECT_CONFIG_PATH),
        inputs=tuple(inputs),
        errors=tuple(errors),
        diagnostics=tuple(diagnostics),
    )


def _parse_selected_input(
    root: Path,
    selected_input: ProjectInput,
) -> tuple[ProjectInput, tuple[ProjectDiscoveryError, ...], tuple[Diagnostic, ...]]:
    source_path = root / selected_input.path
    try:
        parse_result = parser_api.parse_file(source_path)
    except UnicodeDecodeError:
        return _source_read_failure(
            selected_input,
            "Project source file must be valid UTF-8.",
        )
    except OSError:
        return _source_read_failure(
            selected_input,
            "Project source file is not readable.",
        )

    diagnostics = tuple(
        _with_project_relative_path(diagnostic, selected_input.path)
        for diagnostic in parse_result.diagnostics
    )
    if _has_errors(diagnostics):
        return (
            ProjectInput(path=selected_input.path, status=_ERROR_STATUS),
            (),
            diagnostics,
        )
    if parse_result.ast is None:
        return (
            ProjectInput(path=selected_input.path, status=_ERROR_STATUS),
            (
                ProjectDiscoveryError(
                    ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
                    "Project parser produced no AST.",
                    selected_input.path,
                ),
            ),
            diagnostics,
        )
    return (
        ProjectInput(path=selected_input.path, status=_PARSED_STATUS),
        (),
        diagnostics,
    )


def _source_read_failure(
    selected_input: ProjectInput,
    message: str,
) -> tuple[ProjectInput, tuple[ProjectDiscoveryError, ...], tuple[Diagnostic, ...]]:
    return (
        ProjectInput(path=selected_input.path, status=_ERROR_STATUS),
        (
            ProjectDiscoveryError(
                ProjectDiscoveryErrorKind.SOURCE_READ,
                message,
                selected_input.path,
            ),
        ),
        (),
    )


def _with_project_relative_path(
    diagnostic: Diagnostic,
    relative_path: str,
) -> Diagnostic:
    return replace(
        diagnostic,
        location=replace(diagnostic.location, path=relative_path),
    )


def _has_errors(diagnostics: tuple[Diagnostic, ...]) -> bool:
    return any(diagnostic.severity is Severity.ERROR for diagnostic in diagnostics)


def _root_error(message: str) -> ProjectParseCheckResult:
    return ProjectParseCheckResult(
        root=None,
        config_path=None,
        inputs=(),
        errors=(
            ProjectDiscoveryError(
                ProjectDiscoveryErrorKind.PROJECT_ROOT,
                message,
                None,
            ),
        ),
        diagnostics=(),
    )
