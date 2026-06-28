"""Private project discovery for future project-mode work."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from pietto._project.model import (
    ProjectConfigPath,
    ProjectDiscoveryError,
    ProjectDiscoveryErrorKind,
    ProjectDiscoveryResult,
    ProjectInput,
    ProjectRoot,
)

PROJECT_CONFIG_FILENAME = "pietto.toml"

_PROJECT_ROOT_PATH = "."
_SELECTED_STATUS = "selected"


def discover_project_inputs(
    root: str | Path,
    source_paths: Iterable[str | Path] = (),
) -> ProjectDiscoveryResult:
    """Discover explicitly selected project inputs without reading source text."""

    try:
        resolved_root = Path(root).resolve(strict=True)
    except OSError:
        return _root_error("Project root does not exist or is not accessible.")

    if not resolved_root.is_dir():
        return _root_error("Project root must be an existing directory.")

    root_model = ProjectRoot(path=_PROJECT_ROOT_PATH)
    config_model = ProjectConfigPath(path=PROJECT_CONFIG_FILENAME)
    errors: list[ProjectDiscoveryError] = []

    config_path = resolved_root / PROJECT_CONFIG_FILENAME
    if not config_path.is_file():
        errors.append(
            ProjectDiscoveryError(
                ProjectDiscoveryErrorKind.CONFIG_READ,
                "Project configuration file is required.",
                PROJECT_CONFIG_FILENAME,
            )
        )

    inputs: list[ProjectInput] = []
    identities: dict[tuple[int, int], str] = {}
    for raw_path in source_paths:
        normalized_path = _normalize_project_relative_path(raw_path)
        if normalized_path is None:
            errors.append(
                ProjectDiscoveryError(
                    ProjectDiscoveryErrorKind.PROJECT_PATH,
                    "Project source path must be a normalized relative path.",
                    _safe_error_path(raw_path),
                )
            )
            continue

        candidate_path = resolved_root / normalized_path
        try:
            resolved_candidate = candidate_path.resolve(strict=True)
        except OSError:
            errors.append(
                ProjectDiscoveryError(
                    ProjectDiscoveryErrorKind.SOURCE_READ,
                    "Project source file does not exist or is not accessible.",
                    normalized_path,
                )
            )
            continue

        try:
            resolved_candidate.relative_to(resolved_root)
        except ValueError:
            errors.append(
                ProjectDiscoveryError(
                    ProjectDiscoveryErrorKind.PROJECT_PATH,
                    "Project source path escapes the project root.",
                    normalized_path,
                )
            )
            continue

        if not resolved_candidate.is_file():
            errors.append(
                ProjectDiscoveryError(
                    ProjectDiscoveryErrorKind.SOURCE_READ,
                    "Project source path must be a regular file.",
                    normalized_path,
                )
            )
            continue

        try:
            stat_result = resolved_candidate.stat()
        except OSError:
            errors.append(
                ProjectDiscoveryError(
                    ProjectDiscoveryErrorKind.SOURCE_READ,
                    "Project source file does not exist or is not accessible.",
                    normalized_path,
                )
            )
            continue

        identity = (stat_result.st_dev, stat_result.st_ino)
        if identity in identities:
            errors.append(
                ProjectDiscoveryError(
                    ProjectDiscoveryErrorKind.PROJECT_PATH,
                    "Project source path duplicates an already selected file.",
                    normalized_path,
                )
            )
            continue

        identities[identity] = normalized_path
        inputs.append(ProjectInput(path=normalized_path, status=_SELECTED_STATUS))

    return ProjectDiscoveryResult(
        root=root_model,
        config_path=config_model,
        inputs=tuple(sorted(inputs, key=lambda item: item.path)),
        errors=tuple(errors),
    )


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


def _normalize_project_relative_path(raw_path: str | Path) -> str | None:
    value = str(raw_path)
    if not value:
        return None
    if "\x00" in value or "\\" in value:
        return None
    if Path(value).is_absolute() or value.startswith("/"):
        return None
    if _is_windows_drive_path(value) or value.startswith("//"):
        return None
    if value.startswith("/") or value.endswith("/"):
        return None

    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        return None

    return "/".join(parts)


def _safe_error_path(raw_path: str | Path) -> str | None:
    value = str(raw_path)
    if not value:
        return None
    if "\\" in value or Path(value).is_absolute() or _is_windows_drive_path(value):
        return None
    if value.startswith("/") or value.startswith("//"):
        return None
    return value


def _is_windows_drive_path(value: str) -> bool:
    return len(value) >= 2 and value[0].isalpha() and value[1] == ":"
