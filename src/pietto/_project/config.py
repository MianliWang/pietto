"""Private project configuration loading and schema validation."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import tomllib

from pietto._project.discovery import PROJECT_CONFIG_FILENAME
from pietto._project.model import (
    ProjectConfig,
    ProjectConfigLoadResult,
    ProjectConfigPath,
    ProjectDiscoveryError,
    ProjectDiscoveryErrorKind,
    ProjectRoot,
    ProjectSourceConfig,
)

_PROJECT_ROOT_PATH = "."
_SCHEMA_VERSION = 1
_TOP_LEVEL_KEYS = frozenset({"schema_version", "sources"})
_SOURCE_KEYS = frozenset({"include", "exclude"})
_EXTGLOB_MARKERS = ("@(", "+(", "?(", "*(", "!(")


def load_project_config(root: str | Path) -> ProjectConfigLoadResult:
    """Load and validate the private Phase 44 project config contract."""

    try:
        resolved_root = Path(root).resolve(strict=True)
    except OSError:
        return _root_error("Project root does not exist or is not accessible.")

    if not resolved_root.is_dir():
        return _root_error("Project root must be an existing directory.")

    root_model = ProjectRoot(path=_PROJECT_ROOT_PATH)
    config_model = ProjectConfigPath(path=PROJECT_CONFIG_FILENAME)
    config_path = resolved_root / PROJECT_CONFIG_FILENAME

    if not config_path.is_file():
        return _load_error(
            root_model,
            config_model,
            ProjectDiscoveryErrorKind.CONFIG_READ,
            "Project configuration file is required.",
        )

    try:
        config_text = config_path.read_text(encoding="utf-8")
    except OSError:
        return _load_error(
            root_model,
            config_model,
            ProjectDiscoveryErrorKind.CONFIG_READ,
            "Project configuration file is not readable.",
        )
    except UnicodeDecodeError:
        return _load_error(
            root_model,
            config_model,
            ProjectDiscoveryErrorKind.CONFIG_PARSE,
            "Project configuration file must be valid UTF-8 TOML.",
        )

    try:
        parsed = tomllib.loads(config_text)
    except tomllib.TOMLDecodeError as error:
        return _load_error(
            root_model,
            config_model,
            ProjectDiscoveryErrorKind.CONFIG_PARSE,
            f"Project configuration TOML is invalid: {error}.",
        )

    return _validate_config(root_model, config_model, parsed)


def _validate_config(
    root: ProjectRoot,
    config_path: ProjectConfigPath,
    document: Mapping[str, object],
) -> ProjectConfigLoadResult:
    unknown_keys = sorted(set(document) - _TOP_LEVEL_KEYS)
    if unknown_keys:
        return _schema_error(
            root,
            config_path,
            f"Project configuration contains unsupported top-level key: {unknown_keys[0]}.",
        )

    schema_version = document.get("schema_version")
    if not _is_exact_int(schema_version):
        return _schema_error(
            root,
            config_path,
            "Project configuration schema_version must be integer 1.",
        )
    if schema_version != _SCHEMA_VERSION:
        return _schema_error(
            root,
            config_path,
            "Project configuration schema_version must be 1.",
        )

    sources = document.get("sources")
    if not isinstance(sources, Mapping):
        return _schema_error(
            root,
            config_path,
            "Project configuration requires a [sources] table.",
        )

    unknown_source_keys = sorted(set(sources) - _SOURCE_KEYS)
    if unknown_source_keys:
        return _schema_error(
            root,
            config_path,
            f"Project [sources] contains unsupported key: {unknown_source_keys[0]}.",
        )

    include = sources.get("include")
    if not isinstance(include, list):
        return _schema_error(
            root,
            config_path,
            "Project [sources].include must be a non-empty array of strings.",
        )
    if not include:
        return _schema_error(
            root,
            config_path,
            "Project [sources].include must be non-empty.",
        )
    if not all(isinstance(pattern, str) for pattern in include):
        return _schema_error(
            root,
            config_path,
            "Project [sources].include must contain only strings.",
        )

    exclude = sources.get("exclude", [])
    if not isinstance(exclude, list):
        return _schema_error(
            root,
            config_path,
            "Project [sources].exclude must be an array of strings.",
        )
    if not all(isinstance(pattern, str) for pattern in exclude):
        return _schema_error(
            root,
            config_path,
            "Project [sources].exclude must contain only strings.",
        )

    patterns = tuple(include) + tuple(exclude)
    path_errors = tuple(
        ProjectDiscoveryError(
            ProjectDiscoveryErrorKind.PROJECT_PATH,
            "Project source pattern must be a normalized project-relative pattern.",
            pattern,
        )
        for pattern in patterns
        if not _is_valid_project_pattern(pattern)
    )
    if path_errors:
        return ProjectConfigLoadResult(
            root=root,
            config_path=config_path,
            config=None,
            errors=path_errors,
        )

    return ProjectConfigLoadResult(
        root=root,
        config_path=config_path,
        config=ProjectConfig(
            schema_version=_SCHEMA_VERSION,
            sources=ProjectSourceConfig(
                include_patterns=tuple(include),
                exclude_patterns=tuple(exclude),
            ),
        ),
        errors=(),
    )


def _is_valid_project_pattern(value: str) -> bool:
    if not value:
        return False
    if "\x00" in value or "\\" in value:
        return False
    if Path(value).is_absolute() or value.startswith("/"):
        return False
    if _is_windows_drive_path(value) or value.startswith("//"):
        return False
    if value.endswith("/"):
        return False
    if "$" in value or "`" in value:
        return False

    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        return False
    if any(part.startswith("~") or part.startswith("!") for part in parts):
        return False

    for part in parts:
        if not _is_valid_pattern_segment(part):
            return False
    return True


def _is_valid_pattern_segment(segment: str) -> bool:
    if "[" in segment or "]" in segment or "{" in segment or "}" in segment:
        return False
    if any(marker in segment for marker in _EXTGLOB_MARKERS):
        return False
    if "**" in segment and segment != "**":
        return False
    return True


def _is_exact_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_windows_drive_path(value: str) -> bool:
    return len(value) >= 2 and value[0].isalpha() and value[1] == ":"


def _root_error(message: str) -> ProjectConfigLoadResult:
    return ProjectConfigLoadResult(
        root=None,
        config_path=None,
        config=None,
        errors=(
            ProjectDiscoveryError(
                ProjectDiscoveryErrorKind.PROJECT_ROOT,
                message,
                None,
            ),
        ),
    )


def _load_error(
    root: ProjectRoot,
    config_path: ProjectConfigPath,
    kind: ProjectDiscoveryErrorKind,
    message: str,
) -> ProjectConfigLoadResult:
    return ProjectConfigLoadResult(
        root=root,
        config_path=config_path,
        config=None,
        errors=(
            ProjectDiscoveryError(
                kind,
                message,
                PROJECT_CONFIG_FILENAME,
            ),
        ),
    )


def _schema_error(
    root: ProjectRoot,
    config_path: ProjectConfigPath,
    message: str,
) -> ProjectConfigLoadResult:
    return _load_error(
        root,
        config_path,
        ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
        message,
    )
