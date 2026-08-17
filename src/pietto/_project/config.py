"""Private project configuration loading and schema validation."""

from __future__ import annotations

from collections.abc import Mapping
import os
from pathlib import Path
import re
import stat
import tomllib

from pietto._project.discovery import PROJECT_CONFIG_FILENAME
from pietto._project.module_carrier import ProjectCompilationMode
from pietto._project.path_trust import (
    ProjectIdentityUnavailableError,
    ProjectPinnedRoot,
    ProjectRootChangedError,
    _fstat_state,
    _lstat_state,
    _open_pinned_file,
    _pin_project_root,
    _verify_pinned_root,
)
from pietto._project.model import (
    ProjectConfig,
    ProjectConfigLoadResult,
    ProjectConfigPath,
    ProjectDiscoveryError,
    ProjectDiscoveryErrorKind,
    ProjectRoot,
    ProjectRootPackageActivation,
    ProjectSourceConfig,
    _is_valid_project_root_package_path,
)

_PROJECT_ROOT_PATH = "."
_COMPILATION_MODE_BY_SCHEMA_VERSION = {
    1: ProjectCompilationMode.LEGACY_FLAT,
    2: ProjectCompilationMode.EXPLICIT_MODULES,
    3: ProjectCompilationMode.PACKAGE_ROOT,
}
_TOP_LEVEL_KEYS = frozenset({"schema_version", "sources", "package"})
_SOURCE_KEYS = frozenset({"include", "exclude"})
_PACKAGE_KEYS = ("path", "namespace", "name", "version", "sha256")
_PACKAGE_DECLARATION_PROBE_KEY = "__pietto_schema_v3_package_declaration_probe__"
_PACKAGE_TABLE_HEADER = re.compile(
    r"(?m)^(?P<indent>[ \t]*)\[[ \t]*package[ \t]*\][ \t]*(?:#[^\r\n]*)?"
    r"(?P<newline>\r?\n|$)"
)
_EXTGLOB_MARKERS = ("@(", "+(", "?(", "*(", "!(")


def load_project_config(root: str | Path) -> ProjectConfigLoadResult:
    """Load and validate the private Phase 44 project config contract."""

    try:
        pinned_root = _pin_project_root(root)
    except ProjectIdentityUnavailableError:
        return _root_resource_error("Project filesystem identity is unavailable.")
    except NotADirectoryError:
        return _root_error("Project root must be an existing directory.")
    except (OSError, RuntimeError):
        return _root_error("Project root does not exist or is not accessible.")

    root_model = ProjectRoot(path=_PROJECT_ROOT_PATH)
    config_model = ProjectConfigPath(path=PROJECT_CONFIG_FILENAME)
    config_path = pinned_root.canonical_path / PROJECT_CONFIG_FILENAME

    try:
        config_bytes = _read_project_config_bytes(pinned_root, config_path)
    except _ConfigTrustError as error:
        return _load_error(
            root_model,
            config_model,
            error.kind,
            error.message,
            pinned_root,
        )
    except ProjectRootChangedError:
        return _project_level_error(
            root_model,
            config_model,
            ProjectDiscoveryErrorKind.PROJECT_ROOT,
            "Project root identity changed during project loading.",
            pinned_root,
        )
    except ProjectIdentityUnavailableError:
        return _project_level_error(
            root_model,
            config_model,
            ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
            "Project filesystem identity is unavailable.",
            pinned_root,
        )
    except OSError:
        return _load_error(
            root_model,
            config_model,
            ProjectDiscoveryErrorKind.CONFIG_READ,
            "Project configuration file is not readable.",
            pinned_root,
        )

    try:
        config_text = config_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return _load_error(
            root_model,
            config_model,
            ProjectDiscoveryErrorKind.CONFIG_PARSE,
            "Project configuration file must be valid UTF-8 TOML.",
            pinned_root,
        )

    try:
        parsed = tomllib.loads(config_text)
    except tomllib.TOMLDecodeError as error:
        return _load_error(
            root_model,
            config_model,
            ProjectDiscoveryErrorKind.CONFIG_PARSE,
            f"Project configuration TOML is invalid: {error}.",
            pinned_root,
        )

    return _validate_config(
        root_model,
        config_model,
        parsed,
        config_text,
        pinned_root,
    )


class _ConfigTrustError(OSError):
    """One config-leaf trust failure adapted to the existing envelope."""

    def __init__(self, kind: ProjectDiscoveryErrorKind, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message


def _read_project_config_bytes(
    pinned_root: ProjectPinnedRoot,
    config_path: Path,
) -> bytes:
    """Read the exact bytes of one verified non-symlink regular config."""

    try:
        inspected_state = _lstat_state(config_path)
    except FileNotFoundError as error:
        _verify_pinned_root(pinned_root)
        raise _ConfigTrustError(
            ProjectDiscoveryErrorKind.CONFIG_READ,
            "Project configuration file is required.",
        ) from error
    except ProjectIdentityUnavailableError:
        raise
    except OSError:
        _verify_pinned_root(pinned_root)
        raise

    if stat.S_ISLNK(inspected_state.file_type):
        _verify_pinned_root(pinned_root)
        raise _ConfigTrustError(
            ProjectDiscoveryErrorKind.CONFIG_READ,
            "Project configuration path must not be a symbolic link.",
        )
    if not stat.S_ISREG(inspected_state.file_type):
        _verify_pinned_root(pinned_root)
        raise _ConfigTrustError(
            ProjectDiscoveryErrorKind.CONFIG_READ,
            "Project configuration path must be a regular file.",
        )

    file_descriptor = -1
    try:
        try:
            file_descriptor = _open_pinned_file(pinned_root, config_path)
        except (ProjectRootChangedError, ProjectIdentityUnavailableError):
            raise
        except OSError as error:
            raise _ConfigTrustError(
                ProjectDiscoveryErrorKind.CONFIG_READ,
                "Project configuration opened identity does not match the inspected file.",
            ) from error
        opened_state = _fstat_state(file_descriptor)
        if (
            not stat.S_ISREG(opened_state.file_type)
            or opened_state.physical_identity != inspected_state.physical_identity
        ):
            _verify_pinned_root(pinned_root)
            raise _ConfigTrustError(
                ProjectDiscoveryErrorKind.CONFIG_READ,
                "Project configuration opened identity does not match the inspected file.",
            )
        if opened_state != inspected_state:
            _verify_pinned_root(pinned_root)
            raise _ConfigTrustError(
                ProjectDiscoveryErrorKind.CONFIG_READ,
                "Project configuration file changed while being read.",
            )

        with os.fdopen(file_descriptor, "rb", closefd=True) as config_file:
            file_descriptor = -1
            config_bytes = config_file.read()
            final_opened_state = _fstat_state(config_file.fileno())
    finally:
        if file_descriptor >= 0:
            os.close(file_descriptor)

    if final_opened_state != opened_state:
        _verify_pinned_root(pinned_root)
        raise _ConfigTrustError(
            ProjectDiscoveryErrorKind.CONFIG_READ,
            "Project configuration file changed while being read.",
        )
    try:
        final_inspected_state = _lstat_state(config_path)
    except ProjectIdentityUnavailableError:
        raise
    except OSError as error:
        _verify_pinned_root(pinned_root)
        raise _ConfigTrustError(
            ProjectDiscoveryErrorKind.CONFIG_READ,
            "Project configuration file changed while being read.",
        ) from error
    if (
        stat.S_ISLNK(final_inspected_state.file_type)
        or final_inspected_state != inspected_state
    ):
        _verify_pinned_root(pinned_root)
        raise _ConfigTrustError(
            ProjectDiscoveryErrorKind.CONFIG_READ,
            "Project configuration file changed while being read.",
        )
    _verify_pinned_root(pinned_root)
    return config_bytes


def _validate_config(
    root: ProjectRoot,
    config_path: ProjectConfigPath,
    document: Mapping[str, object],
    config_text: str,
    pinned_root: ProjectPinnedRoot,
) -> ProjectConfigLoadResult:
    unknown_keys = sorted(set(document) - _TOP_LEVEL_KEYS)
    if unknown_keys:
        return _schema_error(
            root,
            config_path,
            f"Project configuration contains unsupported top-level key: {unknown_keys[0]}.",
            pinned_root,
        )

    schema_version = document.get("schema_version")
    if not _is_exact_int(schema_version):
        return _schema_error(
            root,
            config_path,
            "Project configuration schema_version must be integer 1, 2, or 3.",
            pinned_root,
        )
    assert isinstance(schema_version, int)
    if schema_version not in _COMPILATION_MODE_BY_SCHEMA_VERSION:
        return _schema_error(
            root,
            config_path,
            "Project configuration schema_version must be 1, 2, or 3.",
            pinned_root,
        )

    allowed_keys = (
        frozenset({"schema_version", "package"})
        if schema_version == 3
        else frozenset({"schema_version", "sources"})
    )
    version_unknown_keys = sorted(set(document) - allowed_keys)
    if version_unknown_keys:
        return _schema_error(
            root,
            config_path,
            f"Project configuration contains unsupported top-level key: {version_unknown_keys[0]}.",
            pinned_root,
        )

    if schema_version == 3:
        if not _has_exact_root_package_table(config_text, document):
            return _schema_error(
                root,
                config_path,
                "Project configuration schema-v3 package activation requires an exact [package] root table.",
                pinned_root,
            )
        return _validate_root_package_config(
            root,
            config_path,
            document.get("package"),
            pinned_root,
        )

    sources = document.get("sources")
    if not isinstance(sources, Mapping):
        return _schema_error(
            root,
            config_path,
            "Project configuration requires a [sources] table.",
            pinned_root,
        )

    unknown_source_keys = sorted(set(sources) - _SOURCE_KEYS)
    if unknown_source_keys:
        return _schema_error(
            root,
            config_path,
            f"Project [sources] contains unsupported key: {unknown_source_keys[0]}.",
            pinned_root,
        )

    include = sources.get("include")
    if not isinstance(include, list):
        return _schema_error(
            root,
            config_path,
            "Project [sources].include must be a non-empty array of strings.",
            pinned_root,
        )
    if not include:
        return _schema_error(
            root,
            config_path,
            "Project [sources].include must be non-empty.",
            pinned_root,
        )
    if not all(isinstance(pattern, str) for pattern in include):
        return _schema_error(
            root,
            config_path,
            "Project [sources].include must contain only strings.",
            pinned_root,
        )

    exclude = sources.get("exclude", [])
    if not isinstance(exclude, list):
        return _schema_error(
            root,
            config_path,
            "Project [sources].exclude must be an array of strings.",
            pinned_root,
        )
    if not all(isinstance(pattern, str) for pattern in exclude):
        return _schema_error(
            root,
            config_path,
            "Project [sources].exclude must contain only strings.",
            pinned_root,
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
            pinned_root=pinned_root,
        )

    return ProjectConfigLoadResult(
        root=root,
        config_path=config_path,
        config=ProjectConfig(
            schema_version=schema_version,
            sources=ProjectSourceConfig(
                include_patterns=tuple(include),
                exclude_patterns=tuple(exclude),
            ),
            compilation_mode=_COMPILATION_MODE_BY_SCHEMA_VERSION[schema_version],
        ),
        errors=(),
        pinned_root=pinned_root,
    )


def _has_exact_root_package_table(
    config_text: str,
    document: Mapping[str, object],
) -> bool:
    """Prove that TOML's ``package`` mapping came from a root table header."""

    for match in _PACKAGE_TABLE_HEADER.finditer(config_text):
        probe_text = (
            config_text[: match.start()]
            + match.group("indent")
            + f"[{_PACKAGE_DECLARATION_PROBE_KEY}]"
            + match.group("newline")
            + config_text[match.end() :]
        )
        try:
            probed = tomllib.loads(probe_text)
        except tomllib.TOMLDecodeError:
            continue
        probe_value = probed.pop(_PACKAGE_DECLARATION_PROBE_KEY, None)
        if probe_value is None or "package" in probed:
            continue
        probed["package"] = probe_value
        if probed == document:
            return True
    return False


def _validate_root_package_config(
    root: ProjectRoot,
    config_path: ProjectConfigPath,
    package: object,
    pinned_root: ProjectPinnedRoot,
) -> ProjectConfigLoadResult:
    if not isinstance(package, Mapping):
        return _schema_error(
            root,
            config_path,
            "Project configuration requires a [package] table.",
            pinned_root,
        )

    unknown_keys = sorted(set(package) - set(_PACKAGE_KEYS))
    if unknown_keys:
        return _schema_error(
            root,
            config_path,
            f"Project [package] contains unsupported key: {unknown_keys[0]}.",
            pinned_root,
        )
    for key in _PACKAGE_KEYS:
        value = package.get(key)
        if type(value) is not str or not value:
            return _schema_error(
                root,
                config_path,
                f"Project [package].{key} must be a non-empty string.",
                pinned_root,
            )

    path = package["path"]
    assert type(path) is str
    if not _is_valid_project_root_package_path(path):
        return ProjectConfigLoadResult(
            root=root,
            config_path=config_path,
            config=None,
            errors=(
                ProjectDiscoveryError(
                    ProjectDiscoveryErrorKind.PROJECT_PATH,
                    'Project [package].path must be "." or a normalized project-relative directory.',
                    path,
                ),
            ),
            pinned_root=pinned_root,
        )

    return ProjectConfigLoadResult(
        root=root,
        config_path=config_path,
        config=ProjectConfig(
            schema_version=3,
            sources=None,
            compilation_mode=ProjectCompilationMode.PACKAGE_ROOT,
            root_package=ProjectRootPackageActivation(
                path=path,
                namespace=package["namespace"],  # type: ignore[arg-type]
                name=package["name"],  # type: ignore[arg-type]
                version=package["version"],  # type: ignore[arg-type]
                sha256=package["sha256"],  # type: ignore[arg-type]
            ),
        ),
        errors=(),
        pinned_root=pinned_root,
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


def _root_resource_error(message: str) -> ProjectConfigLoadResult:
    return ProjectConfigLoadResult(
        root=None,
        config_path=None,
        config=None,
        errors=(
            ProjectDiscoveryError(
                ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
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
    pinned_root: ProjectPinnedRoot,
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
        pinned_root=pinned_root,
    )


def _project_level_error(
    root: ProjectRoot,
    config_path: ProjectConfigPath,
    kind: ProjectDiscoveryErrorKind,
    message: str,
    pinned_root: ProjectPinnedRoot,
) -> ProjectConfigLoadResult:
    return ProjectConfigLoadResult(
        root=root,
        config_path=config_path,
        config=None,
        errors=(ProjectDiscoveryError(kind, message, None),),
        pinned_root=pinned_root,
    )


def _schema_error(
    root: ProjectRoot,
    config_path: ProjectConfigPath,
    message: str,
    pinned_root: ProjectPinnedRoot,
) -> ProjectConfigLoadResult:
    return _load_error(
        root,
        config_path,
        ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
        message,
        pinned_root,
    )
