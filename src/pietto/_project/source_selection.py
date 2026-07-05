"""Private deterministic project source selection."""

from __future__ import annotations

from pathlib import Path

from pietto._project.discovery import PROJECT_CONFIG_FILENAME
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

_PROJECT_ROOT_PATH = "."
_SELECTED_STATUS = "selected"
_PIETTO_SUFFIX = ".pietto"


def select_project_sources(
    root: str | Path,
    config_result: ProjectConfigLoadResult,
) -> ProjectDiscoveryResult:
    """Select configured project sources without reading source text."""

    if not config_result.ok or config_result.config is None:
        return ProjectDiscoveryResult(
            root=config_result.root,
            config_path=config_result.config_path,
            inputs=(),
            errors=config_result.errors,
        )

    try:
        resolved_root = Path(root).resolve(strict=True)
    except OSError:
        return _root_error("Project root does not exist or is not accessible.")

    if not resolved_root.is_dir():
        return _root_error("Project root must be an existing directory.")

    root_model = config_result.root or ProjectRoot(path=_PROJECT_ROOT_PATH)
    config_model = config_result.config_path or ProjectConfigPath(
        path=PROJECT_CONFIG_FILENAME
    )

    inputs, errors = _select_from_config(resolved_root, config_result.config)
    return ProjectDiscoveryResult(
        root=root_model,
        config_path=config_model,
        inputs=inputs,
        errors=errors,
    )


def _select_from_config(
    root: Path,
    config: ProjectConfig,
) -> tuple[tuple[ProjectInput, ...], tuple[ProjectDiscoveryError, ...]]:
    discovered, traversal_errors = _discover_candidate_paths(root)
    selected_paths = {
        relative_path: path
        for relative_path, path in discovered.items()
        if relative_path.endswith(_PIETTO_SUFFIX)
        and _matches_any(config.sources.include_patterns, relative_path)
        and not _matches_any(config.sources.exclude_patterns, relative_path)
    }

    errors = list(traversal_errors)
    inputs: list[ProjectInput] = []
    identities: dict[tuple[int, int], str] = {}
    for relative_path in sorted(selected_paths):
        input_model, input_errors = _validate_selected_path(
            root,
            relative_path,
            selected_paths[relative_path],
            identities,
        )
        errors.extend(input_errors)
        if input_model is not None:
            inputs.append(input_model)

    if not inputs and not errors:
        errors.append(
            ProjectDiscoveryError(
                ProjectDiscoveryErrorKind.PROJECT_GLOB,
                "Project source selection matched no .pietto files.",
                None,
            )
        )

    return tuple(inputs), tuple(errors)


def _discover_candidate_paths(
    root: Path,
) -> tuple[dict[str, Path], tuple[ProjectDiscoveryError, ...]]:
    discovered: dict[str, Path] = {}
    errors: list[ProjectDiscoveryError] = []
    stack: list[tuple[Path, tuple[str, ...]]] = [(root, ())]

    while stack:
        directory, prefix = stack.pop()
        try:
            children = sorted(directory.iterdir(), key=lambda child: child.name)
        except OSError:
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
            discovered[relative_path] = child
            if child.is_symlink():
                continue
            try:
                is_directory = child.is_dir()
            except OSError:
                errors.append(
                    ProjectDiscoveryError(
                        ProjectDiscoveryErrorKind.PROJECT_GLOB,
                        "Project source path is not accessible during selection.",
                        relative_path,
                    )
                )
                continue
            if is_directory:
                stack.append((child, relative_parts))

    return discovered, tuple(errors)


def _validate_selected_path(
    root: Path,
    relative_path: str,
    path: Path,
    identities: dict[tuple[int, int], str],
) -> tuple[ProjectInput | None, tuple[ProjectDiscoveryError, ...]]:
    try:
        resolved_path = path.resolve(strict=True)
    except OSError:
        return None, (
            ProjectDiscoveryError(
                ProjectDiscoveryErrorKind.SOURCE_READ,
                "Project source file does not exist or is not accessible.",
                relative_path,
            ),
        )

    try:
        resolved_path.relative_to(root)
    except ValueError:
        return None, (
            ProjectDiscoveryError(
                ProjectDiscoveryErrorKind.PROJECT_PATH,
                "Project source path escapes the project root.",
                relative_path,
            ),
        )

    if not resolved_path.is_file():
        return None, (
            ProjectDiscoveryError(
                ProjectDiscoveryErrorKind.SOURCE_READ,
                "Project source path must resolve to a regular file.",
                relative_path,
            ),
        )

    try:
        stat_result = resolved_path.stat()
    except OSError:
        return None, (
            ProjectDiscoveryError(
                ProjectDiscoveryErrorKind.SOURCE_READ,
                "Project source file does not exist or is not accessible.",
                relative_path,
            ),
        )

    identity = (stat_result.st_dev, stat_result.st_ino)
    duplicate_path = identities.get(identity)
    if duplicate_path is not None:
        return None, (
            ProjectDiscoveryError(
                ProjectDiscoveryErrorKind.PROJECT_PATH,
                "Project source path duplicates an already selected file.",
                relative_path,
            ),
        )

    identities[identity] = relative_path
    return ProjectInput(path=relative_path, status=_SELECTED_STATUS), ()


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


def _root_error(message: str) -> ProjectDiscoveryResult:
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
    )
