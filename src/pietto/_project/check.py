"""Private parse-only project check orchestration."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pietto.parser_api as parser_api
from pietto._project.config import load_project_config
from pietto._project.module_carrier import (
    ProjectCompilationMode,
    _build_project_logical_modules,
)
from pietto._project.model import (
    ProjectConfigPath,
    ProjectDiscoveryError,
    ProjectDiscoveryErrorKind,
    ProjectInput,
    ProjectParsedInput,
    ProjectParseCheckResult,
    ProjectRoot,
)
from pietto._project.source_selection import select_project_sources
from pietto.errors import Diagnostic, Severity, SourceLocation

_PROJECT_ROOT_PATH = "."
_PROJECT_CONFIG_PATH = "pietto.toml"
_PROJECT_SOURCE_UTF8_BYTES = 1_048_576
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
            compilation_mode=selection_result.compilation_mode,
            modules=selection_result.modules,
        )

    try:
        resolved_root = Path(root).resolve(strict=True)
    except OSError:
        return _root_error(
            "Project root does not exist or is not accessible.",
            compilation_mode=selection_result.compilation_mode,
        )

    if not resolved_root.is_dir():
        return _root_error(
            "Project root must be an existing directory.",
            compilation_mode=selection_result.compilation_mode,
        )

    inputs: list[ProjectInput] = []
    parsed_inputs: list[ProjectParsedInput] = []
    errors: list[ProjectDiscoveryError] = []
    diagnostics: list[Diagnostic] = []
    for selected_input in selection_result.inputs:
        (
            parsed_input,
            parsed_semantic_input,
            input_errors,
            input_diagnostics,
        ) = _parse_selected_input(
            resolved_root,
            selected_input,
        )
        inputs.append(parsed_input)
        if parsed_semantic_input is not None:
            parsed_inputs.append(parsed_semantic_input)
        errors.extend(input_errors)
        diagnostics.extend(input_diagnostics)

    final_inputs = tuple(inputs)
    final_parsed_inputs = tuple(parsed_inputs)
    return ProjectParseCheckResult(
        root=selection_result.root or ProjectRoot(path=_PROJECT_ROOT_PATH),
        config_path=selection_result.config_path
        or ProjectConfigPath(path=_PROJECT_CONFIG_PATH),
        inputs=final_inputs,
        errors=tuple(errors),
        diagnostics=tuple(diagnostics),
        parsed_inputs=final_parsed_inputs,
        compilation_mode=selection_result.compilation_mode,
        modules=_build_project_logical_modules(
            selection_result.compilation_mode,
            final_inputs,
            final_parsed_inputs,
        ),
    )


def _parse_selected_input(
    root: Path,
    selected_input: ProjectInput,
) -> tuple[
    ProjectInput,
    ProjectParsedInput | None,
    tuple[ProjectDiscoveryError, ...],
    tuple[Diagnostic, ...],
]:
    source_path = root / selected_input.path
    try:
        source_text = _read_project_source_text(source_path, selected_input.path)
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

    if isinstance(source_text, Diagnostic):
        return (
            ProjectInput(path=selected_input.path, status=_ERROR_STATUS),
            None,
            (),
            (source_text,),
        )

    parse_result = parser_api.parse_source(source_text, path=selected_input.path)
    diagnostics = tuple(
        _with_project_relative_path(diagnostic, selected_input.path)
        for diagnostic in parse_result.diagnostics
    )
    if _has_errors(diagnostics):
        return (
            ProjectInput(path=selected_input.path, status=_ERROR_STATUS),
            None,
            (),
            diagnostics,
        )
    if parse_result.ast is None:
        return (
            ProjectInput(path=selected_input.path, status=_ERROR_STATUS),
            None,
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
        ProjectParsedInput(path=selected_input.path, script=parse_result.ast),
        (),
        diagnostics,
    )


def _read_project_source_text(
    source_path: Path, relative_path: str
) -> str | Diagnostic:
    with source_path.open("rb") as source_file:
        source_bytes = source_file.read(_PROJECT_SOURCE_UTF8_BYTES + 1)
    if len(source_bytes) > _PROJECT_SOURCE_UTF8_BYTES:
        return Diagnostic(
            code="PIE-P1006",
            severity=Severity.ERROR,
            message=(
                "Source exceeds the maximum supported size of "
                f"{_PROJECT_SOURCE_UTF8_BYTES} UTF-8 bytes."
            ),
            location=SourceLocation(
                path=relative_path,
                line=1,
                column=1,
            ),
        )
    return source_bytes.decode("utf-8")


def _source_read_failure(
    selected_input: ProjectInput,
    message: str,
) -> tuple[
    ProjectInput,
    ProjectParsedInput | None,
    tuple[ProjectDiscoveryError, ...],
    tuple[Diagnostic, ...],
]:
    return (
        ProjectInput(path=selected_input.path, status=_ERROR_STATUS),
        None,
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


def _root_error(
    message: str,
    *,
    compilation_mode: ProjectCompilationMode = ProjectCompilationMode.LEGACY_FLAT,
) -> ProjectParseCheckResult:
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
        compilation_mode=compilation_mode,
    )
