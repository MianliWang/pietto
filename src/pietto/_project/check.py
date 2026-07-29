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
    ProjectDiscoveryResult,
    ProjectInput,
    ProjectParsedInput,
    ProjectParseCheckResult,
    ProjectRoot,
)
from pietto._project.path_trust import ProjectPinnedRoot
from pietto._project.selected_input_index import ProjectSelectedInputEntry
from pietto._project.source_selection import select_project_sources
from pietto._project.trusted_source import (
    ProjectTrustedSourceError,
    ProjectTrustedSourceFailure,
    ProjectTrustedSourceSnapshot,
    _load_trusted_source,
)
from pietto.errors import Diagnostic, Severity

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
            pinned_root=selection_result.pinned_root,
            selected_input_index=selection_result.selected_input_index,
        )

    pinned_root = selection_result.pinned_root
    selected_input_index = selection_result.selected_input_index
    if pinned_root is None or selected_input_index is None:
        return _selection_resource_error(selection_result)

    inputs: list[ProjectInput] = []
    parsed_inputs: list[ProjectParsedInput] = []
    errors: list[ProjectDiscoveryError] = []
    diagnostics: list[Diagnostic] = []
    trusted_source_snapshots: list[ProjectTrustedSourceSnapshot] = []
    for entry in selected_input_index.entries:
        (
            parsed_input,
            parsed_semantic_input,
            trusted_source_snapshot,
            input_errors,
            input_diagnostics,
        ) = _parse_selected_input(
            pinned_root,
            entry,
        )
        inputs.append(parsed_input)
        if parsed_semantic_input is not None:
            parsed_inputs.append(parsed_semantic_input)
        if trusted_source_snapshot is not None:
            trusted_source_snapshots.append(trusted_source_snapshot)
        errors.extend(input_errors)
        diagnostics.extend(input_diagnostics)
        if input_errors and input_errors[0].path is None:
            inputs.extend(
                ProjectInput(path=remaining.identity.path, status=_ERROR_STATUS)
                for remaining in selected_input_index.entries[entry.position + 1 :]
            )
            break

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
        pinned_root=pinned_root,
        selected_input_index=selected_input_index,
        trusted_source_snapshots=tuple(trusted_source_snapshots),
    )


def _parse_selected_input(
    pinned_root: ProjectPinnedRoot,
    selected_input: ProjectSelectedInputEntry,
) -> tuple[
    ProjectInput,
    ProjectParsedInput | None,
    ProjectTrustedSourceSnapshot | None,
    tuple[ProjectDiscoveryError, ...],
    tuple[Diagnostic, ...],
]:
    try:
        trusted_source = _load_trusted_source(
            pinned_root,
            selected_input,
            byte_limit=_PROJECT_SOURCE_UTF8_BYTES,
        )
    except UnicodeDecodeError:
        return _source_read_failure(
            selected_input.project_input,
            "Project source file must be valid UTF-8.",
        )
    except ProjectTrustedSourceError as error:
        return _trusted_source_failure(selected_input.project_input, error.reason)
    except OSError:
        return _source_read_failure(
            selected_input.project_input,
            "Project source file is not readable.",
        )

    if isinstance(trusted_source, Diagnostic):
        return (
            ProjectInput(path=selected_input.identity.path, status=_ERROR_STATUS),
            None,
            None,
            (),
            (trusted_source,),
        )

    parse_result = parser_api.parse_source(
        trusted_source.source_text,
        path=selected_input.identity.path,
    )
    diagnostics = tuple(
        _with_project_relative_path(diagnostic, selected_input.identity.path)
        for diagnostic in parse_result.diagnostics
    )
    if _has_errors(diagnostics):
        return (
            ProjectInput(path=selected_input.identity.path, status=_ERROR_STATUS),
            None,
            trusted_source,
            (),
            diagnostics,
        )
    if parse_result.ast is None:
        return (
            ProjectInput(path=selected_input.identity.path, status=_ERROR_STATUS),
            None,
            trusted_source,
            (
                ProjectDiscoveryError(
                    ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
                    "Project parser produced no AST.",
                    selected_input.identity.path,
                ),
            ),
            diagnostics,
        )
    return (
        ProjectInput(path=selected_input.identity.path, status=_PARSED_STATUS),
        ProjectParsedInput(
            path=selected_input.identity.path,
            script=parse_result.ast,
        ),
        trusted_source,
        (),
        diagnostics,
    )


def _source_read_failure(
    selected_input: ProjectInput,
    message: str,
) -> tuple[
    ProjectInput,
    ProjectParsedInput | None,
    ProjectTrustedSourceSnapshot | None,
    tuple[ProjectDiscoveryError, ...],
    tuple[Diagnostic, ...],
]:
    return (
        ProjectInput(path=selected_input.path, status=_ERROR_STATUS),
        None,
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


def _trusted_source_failure(
    selected_input: ProjectInput,
    reason: ProjectTrustedSourceFailure,
) -> tuple[
    ProjectInput,
    ProjectParsedInput | None,
    ProjectTrustedSourceSnapshot | None,
    tuple[ProjectDiscoveryError, ...],
    tuple[Diagnostic, ...],
]:
    kind, message, path = {
        ProjectTrustedSourceFailure.ROOT_CHANGED: (
            ProjectDiscoveryErrorKind.PROJECT_ROOT,
            "Project root identity changed during project loading.",
            None,
        ),
        ProjectTrustedSourceFailure.IDENTITY_UNAVAILABLE: (
            ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
            "Project filesystem identity is unavailable.",
            None,
        ),
        ProjectTrustedSourceFailure.SYMBOLIC_LINK_CHANGED: (
            ProjectDiscoveryErrorKind.SOURCE_READ,
            "Project source symbolic link changed after selection.",
            selected_input.path,
        ),
        ProjectTrustedSourceFailure.SOURCE_CHANGED: (
            ProjectDiscoveryErrorKind.SOURCE_READ,
            "Project source file changed after selection.",
            selected_input.path,
        ),
        ProjectTrustedSourceFailure.OPENED_IDENTITY_MISMATCH: (
            ProjectDiscoveryErrorKind.SOURCE_READ,
            "Project source opened identity does not match the selected file.",
            selected_input.path,
        ),
        ProjectTrustedSourceFailure.NOT_REGULAR: (
            ProjectDiscoveryErrorKind.SOURCE_READ,
            "Project source path must resolve to a regular file.",
            selected_input.path,
        ),
        ProjectTrustedSourceFailure.READ_MUTATION: (
            ProjectDiscoveryErrorKind.SOURCE_READ,
            "Project source file changed while being read.",
            selected_input.path,
        ),
    }[reason]
    return (
        ProjectInput(path=selected_input.path, status=_ERROR_STATUS),
        None,
        None,
        (ProjectDiscoveryError(kind, message, path),),
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


def _selection_resource_error(
    selection_result: ProjectDiscoveryResult,
) -> ProjectParseCheckResult:
    return ProjectParseCheckResult(
        root=selection_result.root,
        config_path=selection_result.config_path,
        inputs=selection_result.inputs,
        errors=(
            ProjectDiscoveryError(
                ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
                "Project selected-input index is unavailable.",
                None,
            ),
        ),
        diagnostics=(),
        compilation_mode=selection_result.compilation_mode,
        modules=selection_result.modules,
        pinned_root=selection_result.pinned_root,
        selected_input_index=selection_result.selected_input_index,
    )
