"""Private deterministic project source selection."""

from __future__ import annotations

import os
from pathlib import Path
import stat

from pietto._project.discovery import PROJECT_CONFIG_FILENAME
from pietto._project.module_carrier import (
    ProjectCompilationMode,
    ProjectModuleIdentity,
    _build_project_logical_modules,
)
from pietto._project.model import (
    ProjectConfig,
    ProjectConfigLoadResult,
    ProjectConfigPath,
    ProjectDiscoveryError,
    ProjectDiscoveryErrorKind,
    ProjectDiscoveryResult,
    ProjectInput,
    ProjectRoot,
)
from pietto._project.path_trust import (
    ProjectFilesystemState,
    ProjectIdentityUnavailableError,
    ProjectPinnedRoot,
    ProjectPhysicalIdentity,
    ProjectRootChangedError,
    _lstat_state,
    _stat_state,
    _verify_pinned_root,
)
from pietto._project.selected_input_index import (
    ProjectSelectedInputEntry,
    ProjectSelectedInputIndex,
)

_PROJECT_ROOT_PATH = "."
_SELECTED_STATUS = "selected"
_PIETTO_SUFFIX = ".pietto"


def select_project_sources(
    root: str | Path,
    config_result: ProjectConfigLoadResult,
) -> ProjectDiscoveryResult:
    """Select configured project sources without reading source text."""

    del root
    if not config_result.ok or config_result.config is None:
        return ProjectDiscoveryResult(
            root=config_result.root,
            config_path=config_result.config_path,
            inputs=(),
            errors=config_result.errors,
            pinned_root=config_result.pinned_root,
        )

    pinned_root = config_result.pinned_root
    if pinned_root is None:
        return _project_level_error(
            config_result,
            ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
            "Project filesystem identity is unavailable.",
        )
    try:
        _verify_pinned_root(pinned_root)
        inputs, entries, errors = _select_from_config(
            pinned_root,
            config_result.config,
        )
        _verify_pinned_root(pinned_root)
    except ProjectRootChangedError:
        return _project_level_error(
            config_result,
            ProjectDiscoveryErrorKind.PROJECT_ROOT,
            "Project root identity changed during project loading.",
        )
    except ProjectIdentityUnavailableError:
        return _project_level_error(
            config_result,
            ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
            "Project filesystem identity is unavailable.",
        )

    root_model = config_result.root or ProjectRoot(path=_PROJECT_ROOT_PATH)
    config_model = config_result.config_path or ProjectConfigPath(
        path=PROJECT_CONFIG_FILENAME
    )

    selected_input_index = (
        ProjectSelectedInputIndex(pinned_root=pinned_root, entries=entries)
        if not errors
        else None
    )
    return ProjectDiscoveryResult(
        root=root_model,
        config_path=config_model,
        inputs=inputs,
        errors=errors,
        compilation_mode=config_result.config.compilation_mode,
        modules=_build_project_logical_modules(
            config_result.config.compilation_mode,
            inputs,
        ),
        pinned_root=pinned_root,
        selected_input_index=selected_input_index,
    )


def _select_from_config(
    pinned_root: ProjectPinnedRoot,
    config: ProjectConfig,
) -> tuple[
    tuple[ProjectInput, ...],
    tuple[ProjectSelectedInputEntry, ...],
    tuple[ProjectDiscoveryError, ...],
]:
    discovered, traversal_errors = _discover_candidate_paths(pinned_root)
    selected_paths = {
        relative_path: path
        for relative_path, path in discovered.items()
        if relative_path.endswith(_PIETTO_SUFFIX)
        and _matches_any(config.sources.include_patterns, relative_path)
        and not _matches_any(config.sources.exclude_patterns, relative_path)
    }

    errors = list(traversal_errors)
    inputs: list[ProjectInput] = []
    entries: list[ProjectSelectedInputEntry] = []
    identities: dict[ProjectPhysicalIdentity, str] = {}
    for relative_path in sorted(selected_paths):
        input_model, entry, input_errors = _validate_selected_path(
            pinned_root,
            relative_path,
            selected_paths[relative_path],
            identities,
            position=len(entries),
        )
        errors.extend(input_errors)
        if input_model is not None and entry is not None:
            inputs.append(input_model)
            entries.append(entry)

    if not inputs and not errors:
        errors.append(
            ProjectDiscoveryError(
                ProjectDiscoveryErrorKind.PROJECT_GLOB,
                "Project source selection matched no .pietto files.",
                None,
            )
        )

    return tuple(inputs), tuple(entries), tuple(errors)


def _discover_candidate_paths(
    pinned_root: ProjectPinnedRoot,
) -> tuple[dict[str, Path], tuple[ProjectDiscoveryError, ...]]:
    discovered: dict[str, Path] = {}
    errors: list[ProjectDiscoveryError] = []
    root = pinned_root.canonical_path
    try:
        root_state = _lstat_state(root)
    except ProjectIdentityUnavailableError:
        raise
    except OSError as error:
        raise ProjectRootChangedError(
            "Project root identity changed during project loading."
        ) from error
    stack: list[tuple[Path, tuple[str, ...], ProjectFilesystemState]] = [
        (root, (), root_state)
    ]

    while stack:
        directory, prefix, inspected_state = stack.pop()
        try:
            _verify_pinned_root(pinned_root)
            current_state = _lstat_state(directory)
            if current_state != inspected_state or not stat.S_ISDIR(
                current_state.file_type
            ):
                raise OSError("Project source directory changed during selection.")
            children = sorted(directory.iterdir(), key=lambda child: child.name)
            final_state = _lstat_state(directory)
            if final_state != inspected_state:
                raise OSError("Project source directory changed during selection.")
        except (ProjectRootChangedError, ProjectIdentityUnavailableError):
            raise
        except OSError:
            _verify_pinned_root(pinned_root)
            errors.append(
                ProjectDiscoveryError(
                    ProjectDiscoveryErrorKind.PROJECT_GLOB,
                    "Project source directory is not accessible.",
                    _optional_relative_path(prefix),
                )
            )
            continue

        for child in reversed(children):
            relative_parts = (*prefix, child.name)
            relative_path = _relative_path(relative_parts)
            try:
                child_state = _lstat_state(child)
            except ProjectIdentityUnavailableError:
                raise
            except OSError:
                _verify_pinned_root(pinned_root)
                errors.append(
                    ProjectDiscoveryError(
                        ProjectDiscoveryErrorKind.PROJECT_GLOB,
                        "Project source path is not accessible during selection.",
                        relative_path,
                    )
                )
                continue
            discovered[relative_path] = child
            if stat.S_ISLNK(child_state.file_type):
                continue
            if stat.S_ISDIR(child_state.file_type):
                stack.append((child, relative_parts, child_state))

    return discovered, tuple(errors)


def _validate_selected_path(
    pinned_root: ProjectPinnedRoot,
    relative_path: str,
    path: Path,
    identities: dict[ProjectPhysicalIdentity, str],
    *,
    position: int,
) -> tuple[
    ProjectInput | None,
    ProjectSelectedInputEntry | None,
    tuple[ProjectDiscoveryError, ...],
]:
    try:
        module_identity = ProjectModuleIdentity(path=relative_path)
    except (TypeError, ValueError):
        return (
            None,
            None,
            (
                ProjectDiscoveryError(
                    ProjectDiscoveryErrorKind.PROJECT_PATH,
                    "Project source path must be a normalized relative path.",
                    relative_path,
                ),
            ),
        )

    try:
        logical_leaf_state = _lstat_state(path)
        final_leaf_is_symlink = stat.S_ISLNK(logical_leaf_state.file_type)
        symlink_target = os.readlink(path) if final_leaf_is_symlink else None
        resolved_path = path.resolve(strict=True)
    except ProjectIdentityUnavailableError:
        raise
    except (OSError, RuntimeError):
        _verify_pinned_root(pinned_root)
        return (
            None,
            None,
            (
                ProjectDiscoveryError(
                    ProjectDiscoveryErrorKind.SOURCE_READ,
                    "Project source file does not exist or is not accessible.",
                    relative_path,
                ),
            ),
        )

    try:
        resolved_path.relative_to(pinned_root.canonical_path)
    except ValueError:
        return (
            None,
            None,
            (
                ProjectDiscoveryError(
                    ProjectDiscoveryErrorKind.PROJECT_PATH,
                    "Project source path escapes the project root.",
                    relative_path,
                ),
            ),
        )

    try:
        final_target_state = _stat_state(resolved_path)
    except ProjectIdentityUnavailableError:
        raise
    except OSError:
        _verify_pinned_root(pinned_root)
        return (
            None,
            None,
            (
                ProjectDiscoveryError(
                    ProjectDiscoveryErrorKind.SOURCE_READ,
                    "Project source file does not exist or is not accessible.",
                    relative_path,
                ),
            ),
        )

    if not stat.S_ISREG(final_target_state.file_type):
        return (
            None,
            None,
            (
                ProjectDiscoveryError(
                    ProjectDiscoveryErrorKind.SOURCE_READ,
                    "Project source path must resolve to a regular file.",
                    relative_path,
                ),
            ),
        )

    identity = final_target_state.physical_identity
    duplicate_path = identities.get(identity)
    if duplicate_path is not None:
        return (
            None,
            None,
            (
                ProjectDiscoveryError(
                    ProjectDiscoveryErrorKind.PROJECT_PATH,
                    "Project source path duplicates an already selected file.",
                    relative_path,
                ),
            ),
        )

    identities[identity] = relative_path
    input_model = ProjectInput(path=relative_path, status=_SELECTED_STATUS)
    return (
        input_model,
        ProjectSelectedInputEntry(
            identity=module_identity,
            position=position,
            project_input=input_model,
            canonical_path=resolved_path,
            logical_leaf_state=logical_leaf_state,
            final_target_state=final_target_state,
            final_leaf_is_symlink=final_leaf_is_symlink,
            symlink_target=symlink_target,
        ),
        (),
    )


def _matches_any(patterns: tuple[str, ...], relative_path: str) -> bool:
    return any(_matches_path(pattern, relative_path) for pattern in patterns)


def _matches_path(pattern: str, relative_path: str) -> bool:
    pattern_parts = tuple(pattern.split("/"))
    path_parts = tuple(relative_path.split("/"))
    return _matches_path_parts(pattern_parts, path_parts)


def _matches_path_parts(
    pattern_parts: tuple[str, ...],
    path_parts: tuple[str, ...],
) -> bool:
    if not pattern_parts:
        return not path_parts

    head, *tail = pattern_parts
    remaining_pattern = tuple(tail)
    if head == "**":
        return _matches_path_parts(remaining_pattern, path_parts) or (
            bool(path_parts)
            and not path_parts[0].startswith(".")
            and _matches_path_parts(pattern_parts, path_parts[1:])
        )

    return (
        bool(path_parts)
        and _matches_segment(head, path_parts[0])
        and (_matches_path_parts(remaining_pattern, path_parts[1:]))
    )


def _matches_segment(pattern: str, value: str) -> bool:
    if value.startswith(".") and not pattern.startswith("."):
        return False
    return _matches_segment_from(pattern, value, 0, 0)


def _matches_segment_from(
    pattern: str,
    value: str,
    pattern_index: int,
    value_index: int,
) -> bool:
    if pattern_index == len(pattern):
        return value_index == len(value)

    token = pattern[pattern_index]
    if token == "*":
        return _matches_segment_from(
            pattern,
            value,
            pattern_index + 1,
            value_index,
        ) or (
            value_index < len(value)
            and _matches_segment_from(pattern, value, pattern_index, value_index + 1)
        )
    if token == "?":
        return value_index < len(value) and _matches_segment_from(
            pattern,
            value,
            pattern_index + 1,
            value_index + 1,
        )
    return (
        value_index < len(value)
        and token == value[value_index]
        and _matches_segment_from(
            pattern,
            value,
            pattern_index + 1,
            value_index + 1,
        )
    )


def _relative_path(parts: tuple[str, ...]) -> str:
    return "/".join(parts)


def _optional_relative_path(parts: tuple[str, ...]) -> str | None:
    if not parts:
        return None
    return _relative_path(parts)


def _root_error(
    message: str,
    *,
    compilation_mode: ProjectCompilationMode = ProjectCompilationMode.LEGACY_FLAT,
) -> ProjectDiscoveryResult:
    return ProjectDiscoveryResult(
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
        compilation_mode=compilation_mode,
    )


def _project_level_error(
    config_result: ProjectConfigLoadResult,
    kind: ProjectDiscoveryErrorKind,
    message: str,
) -> ProjectDiscoveryResult:
    return ProjectDiscoveryResult(
        root=config_result.root,
        config_path=config_result.config_path,
        inputs=(),
        errors=(ProjectDiscoveryError(kind, message, None),),
        compilation_mode=(
            config_result.config.compilation_mode
            if config_result.config is not None
            else ProjectCompilationMode.LEGACY_FLAT
        ),
        pinned_root=config_result.pinned_root,
    )
