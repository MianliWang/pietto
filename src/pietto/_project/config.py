"""Private project configuration loading and schema validation."""

from __future__ import annotations

from collections.abc import Mapping
import math
import os
from pathlib import Path
import re
import stat
import tomllib
from typing import cast

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
    ProjectCapabilityEnvironmentConfig,
    ProjectCapabilityProfileDeclaration,
    ProjectCapabilityProfileFactDeclaration,
    ProjectCapabilityTargetSelection,
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
from pietto.semantic.capability_facts import (
    CapabilityDomain,
    CapabilityKey,
    CapabilitySupport,
)
from pietto.semantic.capability_profiles import (
    CapabilityProfileIdentity,
    CapabilityProfileKind,
    CapabilityProfileReference,
    CapabilityProfileTarget,
    CapabilityProfileTargetKind,
)

_PROJECT_ROOT_PATH = "."
_COMPILATION_MODE_BY_SCHEMA_VERSION = {
    1: ProjectCompilationMode.LEGACY_FLAT,
    2: ProjectCompilationMode.EXPLICIT_MODULES,
    3: ProjectCompilationMode.PACKAGE_ROOT,
    4: ProjectCompilationMode.PACKAGE_ROOT,
}
_TOP_LEVEL_KEYS = frozenset(
    {"schema_version", "sources", "package", "capability_environment"}
)
_SOURCE_KEYS = frozenset({"include", "exclude"})
_PACKAGE_KEYS = ("path", "namespace", "name", "version", "sha256")
_PACKAGE_DECLARATION_PROBE_KEY = "__pietto_schema_v3_package_declaration_probe__"
_PACKAGE_TABLE_HEADER = re.compile(
    r"(?m)^(?P<indent>[ \t]*)\[[ \t]*package[ \t]*\][ \t]*(?:#[^\r\n]*)?"
    r"(?P<newline>\r?\n|$)"
)
_CAPABILITY_ENVIRONMENT_TABLE_HEADER = re.compile(
    r"(?m)^(?P<indent>[ \t]*)\[[ \t]*capability_environment[ \t]*\]"
    r"(?P<suffix>[ \t]*(?:#[^\r\n]*)?(?:\r?\n|$))"
)
_CAPABILITY_PROFILE_HEADER = re.compile(
    r"(?m)^(?P<indent>[ \t]*)\[\[[ \t]*capability_environment[ \t]*"
    r"\.[ \t]*profiles[ \t]*\]\]"
    r"(?P<suffix>[ \t]*(?:#[^\r\n]*)?(?:\r?\n|$))"
)
_CAPABILITY_PROFILE_FACT_HEADER = re.compile(
    r"(?m)^(?P<indent>[ \t]*)\[\[[ \t]*capability_environment[ \t]*"
    r"\.[ \t]*profiles[ \t]*\.[ \t]*facts[ \t]*\]\]"
    r"(?P<suffix>[ \t]*(?:#[^\r\n]*)?(?:\r?\n|$))"
)
_CAPABILITY_TARGET_HEADER = re.compile(
    r"(?m)^(?P<indent>[ \t]*)\[\[[ \t]*capability_environment[ \t]*"
    r"\.[ \t]*targets[ \t]*\]\]"
    r"(?P<suffix>[ \t]*(?:#[^\r\n]*)?(?:\r?\n|$))"
)
_CAPABILITY_TARGET_OVERLAY_HEADER = re.compile(
    r"(?m)^(?P<indent>[ \t]*)\[\[[ \t]*capability_environment[ \t]*"
    r"\.[ \t]*targets[ \t]*\.[ \t]*overlays[ \t]*\]\]"
    r"(?P<suffix>[ \t]*(?:#[^\r\n]*)?(?:\r?\n|$))"
)
_CAPABILITY_ENVIRONMENT_KEYS = frozenset({"profiles", "targets"})
_CAPABILITY_PROFILE_COMMON_KEYS = frozenset(
    {
        "namespace",
        "name",
        "release",
        "kind",
        "database_family",
        "database_release",
        "facts",
    }
)
_CAPABILITY_PROFILE_OVERLAY_KEYS = frozenset(
    {
        "extension_identity",
        "extension_release",
        "base_namespace",
        "base_name",
        "base_release",
    }
)
_CAPABILITY_FACT_KEYS = frozenset(
    {
        "support",
        "domain",
        "subject",
        "operation",
        "operands",
        "context",
        "dialect",
        "extension",
    }
)
_CAPABILITY_OPTIONAL_TEXT_KEYS = (
    "subject",
    "operation",
    "context",
    "dialect",
    "extension",
)
_CAPABILITY_TARGET_KEYS = frozenset(
    {
        "database_family",
        "database_release",
        "base_profile_namespace",
        "base_profile_name",
        "base_profile_release",
        "overlays",
    }
)
_CAPABILITY_TARGET_OVERLAY_KEYS = ("namespace", "name", "release")
_CAPABILITY_DOMAIN_VALUES = frozenset(
    {
        "logical_type",
        "literal",
        "parameter",
        "scalar_function",
        "unary_operator",
        "binary_operator",
        "comparison",
        "null_test",
        "clause",
        "aggregate",
        "window_function",
        "expression_stage",
        "conversion",
        "dialect_lowering",
        "extension_signature",
    }
)
_CAPABILITY_SUPPORTS = {
    "supported": CapabilitySupport.SUPPORTED,
    "explicitly_unsupported": CapabilitySupport.EXPLICITLY_UNSUPPORTED,
}
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
            "Project configuration schema_version must be integer 1, 2, 3, or 4.",
            pinned_root,
        )
    assert isinstance(schema_version, int)
    if schema_version not in _COMPILATION_MODE_BY_SCHEMA_VERSION:
        return _schema_error(
            root,
            config_path,
            "Project configuration schema_version must be 1, 2, 3, or 4.",
            pinned_root,
        )

    if schema_version == 3:
        allowed_keys = frozenset({"schema_version", "package"})
    elif schema_version == 4:
        allowed_keys = frozenset(
            {"schema_version", "package", "capability_environment"}
        )
    else:
        allowed_keys = frozenset({"schema_version", "sources"})
    version_unknown_keys = sorted(set(document) - allowed_keys)
    if version_unknown_keys:
        return _schema_error(
            root,
            config_path,
            f"Project configuration contains unsupported top-level key: {version_unknown_keys[0]}.",
            pinned_root,
        )

    if schema_version in {3, 4}:
        if not _has_exact_root_package_table(config_text, document):
            return _schema_error(
                root,
                config_path,
                f"Project configuration schema-v{schema_version} package activation "
                "requires an exact [package] root table.",
                pinned_root,
            )
        capability_environment = None
        if schema_version == 4:
            if not _has_exact_root_table(
                config_text,
                document,
                key="capability_environment",
                header_pattern=_CAPABILITY_ENVIRONMENT_TABLE_HEADER,
            ):
                return _schema_error(
                    root,
                    config_path,
                    "Project configuration schema-v4 requires an exact "
                    "[capability_environment] root table.",
                    pinned_root,
                )
            capability_environment, environment_error = (
                _normalize_capability_environment(config_text, document)
            )
            if environment_error is not None:
                return _schema_error(
                    root,
                    config_path,
                    environment_error,
                    pinned_root,
                )
            assert type(capability_environment) is ProjectCapabilityEnvironmentConfig
        return _validate_root_package_config(
            root,
            config_path,
            document.get("package"),
            pinned_root,
            schema_version=schema_version,
            capability_environment=capability_environment,
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


def _normalize_capability_environment(
    config_text: str,
    document: Mapping[str, object],
) -> tuple[ProjectCapabilityEnvironmentConfig | None, str | None]:
    value = document.get("capability_environment")
    if type(value) is not dict:
        return None, "Project [capability_environment] must be an exact table."
    environment = cast(dict[str, object], value)
    unknown_keys = sorted(set(environment) - _CAPABILITY_ENVIRONMENT_KEYS)
    if unknown_keys:
        return (
            None,
            "Project [capability_environment] contains unsupported key: "
            f"{unknown_keys[0]}.",
        )

    profiles_value = environment.get("profiles", [])
    if "profiles" in environment and not _is_nonempty_mapping_list(profiles_value):
        return (
            None,
            "Project capability profiles must be omitted or use one or more exact "
            "[[capability_environment.profiles]] entries.",
        )
    if "profiles" in environment and not _has_exact_aot_path(
        config_text,
        document,
        path=("capability_environment", "profiles"),
        header_pattern=_CAPABILITY_PROFILE_HEADER,
    ):
        return (
            None,
            "Project capability profiles must use exact "
            "[[capability_environment.profiles]] syntax.",
        )
    profiles = cast(list[dict[str, object]], profiles_value)

    for position, profile in enumerate(profiles):
        facts_value = profile.get("facts", [])
        if "facts" in profile and not _is_nonempty_mapping_list(facts_value):
            return (
                None,
                f"Project capability profile[{position}].facts must be omitted or "
                "use exact nested array-of-table entries.",
            )
    if any("facts" in profile for profile in profiles) and not _has_exact_aot_path(
        config_text,
        document,
        path=("capability_environment", "profiles", "facts"),
        header_pattern=_CAPABILITY_PROFILE_FACT_HEADER,
    ):
        return (
            None,
            "Project capability profile facts must use exact "
            "[[capability_environment.profiles.facts]] syntax.",
        )

    targets_value = environment.get("targets", [])
    if "targets" in environment and not _is_nonempty_mapping_list(targets_value):
        return (
            None,
            "Project capability targets must be omitted or use one or more exact "
            "[[capability_environment.targets]] entries.",
        )
    if "targets" in environment and not _has_exact_aot_path(
        config_text,
        document,
        path=("capability_environment", "targets"),
        header_pattern=_CAPABILITY_TARGET_HEADER,
    ):
        return (
            None,
            "Project capability targets must use exact "
            "[[capability_environment.targets]] syntax.",
        )
    targets = cast(list[dict[str, object]], targets_value)

    for position, target in enumerate(targets):
        overlays_value = target.get("overlays", [])
        if "overlays" in target and not _is_nonempty_mapping_list(overlays_value):
            return (
                None,
                f"Project capability target[{position}].overlays must be omitted or "
                "use exact nested array-of-table entries.",
            )
    if any("overlays" in target for target in targets) and not _has_exact_aot_path(
        config_text,
        document,
        path=("capability_environment", "targets", "overlays"),
        header_pattern=_CAPABILITY_TARGET_OVERLAY_HEADER,
    ):
        return (
            None,
            "Project capability target overlays must use exact "
            "[[capability_environment.targets.overlays]] syntax.",
        )

    profile_declarations: list[ProjectCapabilityProfileDeclaration] = []
    for position, profile in enumerate(profiles):
        declaration, error = _normalize_capability_profile(profile, position)
        if error is not None:
            return None, error
        assert type(declaration) is ProjectCapabilityProfileDeclaration
        profile_declarations.append(declaration)

    target_selections: list[ProjectCapabilityTargetSelection] = []
    for position, target in enumerate(targets):
        selection, error = _normalize_capability_target(target, position)
        if error is not None:
            return None, error
        assert type(selection) is ProjectCapabilityTargetSelection
        target_selections.append(selection)

    return (
        ProjectCapabilityEnvironmentConfig(
            tuple(profile_declarations),
            tuple(target_selections),
        ),
        None,
    )


def _normalize_capability_profile(
    profile: Mapping[str, object],
    position: int,
) -> tuple[ProjectCapabilityProfileDeclaration | None, str | None]:
    prefix = f"Project capability profile[{position}]"
    unknown_keys = sorted(
        set(profile)
        - _CAPABILITY_PROFILE_COMMON_KEYS
        - _CAPABILITY_PROFILE_OVERLAY_KEYS
    )
    if unknown_keys:
        return None, f"{prefix} contains unsupported key: {unknown_keys[0]}."
    for key in (
        "namespace",
        "name",
        "release",
        "kind",
        "database_family",
        "database_release",
    ):
        if not _is_nonblank_text(profile.get(key)):
            return None, f"{prefix}.{key} must be a nonblank string."

    kind_value = profile["kind"]
    assert type(kind_value) is str
    if kind_value not in {"base", "overlay"}:
        return None, f"{prefix}.kind must be exactly base or overlay."
    kind = CapabilityProfileKind(kind_value)
    overlay_fields = tuple(
        key for key in _CAPABILITY_PROFILE_OVERLAY_KEYS if key in profile
    )
    if kind is CapabilityProfileKind.BASE and overlay_fields:
        return (
            None,
            f"{prefix} BASE declaration forbids overlay-only key: "
            f"{sorted(overlay_fields)[0]}.",
        )
    if kind is CapabilityProfileKind.OVERLAY:
        for key in sorted(_CAPABILITY_PROFILE_OVERLAY_KEYS):
            if not _is_nonblank_text(profile.get(key)):
                return None, f"{prefix}.{key} must be a nonblank string for OVERLAY."

    facts: list[ProjectCapabilityProfileFactDeclaration] = []
    first_position_by_fact: dict[tuple[CapabilitySupport, CapabilityKey], int] = {}
    for fact_position, fact_value in enumerate(
        cast(list[dict[str, object]], profile.get("facts", []))
    ):
        fact, error = _normalize_capability_fact(fact_value, position, fact_position)
        if error is not None:
            return None, error
        assert type(fact) is ProjectCapabilityProfileFactDeclaration
        identity = (fact.support, fact.key)
        first_position = first_position_by_fact.setdefault(identity, fact_position)
        if first_position != fact_position:
            return (
                None,
                f"{prefix}.facts[{fact_position}] duplicates support and CapabilityKey "
                f"from facts[{first_position}].",
            )
        facts.append(fact)

    reference = CapabilityProfileReference(
        CapabilityProfileIdentity(
            cast(str, profile["namespace"]),
            cast(str, profile["name"]),
        ),
        cast(str, profile["release"]),
    )
    if kind is CapabilityProfileKind.BASE:
        target = CapabilityProfileTarget(
            CapabilityProfileTargetKind.DATABASE,
            cast(str, profile["database_family"]),
            cast(str, profile["database_release"]),
        )
        base = None
    else:
        target = CapabilityProfileTarget(
            CapabilityProfileTargetKind.EXTENSION,
            cast(str, profile["database_family"]),
            cast(str, profile["database_release"]),
            cast(str, profile["extension_identity"]),
            cast(str, profile["extension_release"]),
        )
        base = CapabilityProfileReference(
            CapabilityProfileIdentity(
                cast(str, profile["base_namespace"]),
                cast(str, profile["base_name"]),
            ),
            cast(str, profile["base_release"]),
        )
    return (
        ProjectCapabilityProfileDeclaration(
            position,
            reference,
            kind,
            target,
            base,
            tuple(facts),
        ),
        None,
    )


def _normalize_capability_fact(
    value: Mapping[str, object],
    profile_position: int,
    fact_position: int,
) -> tuple[ProjectCapabilityProfileFactDeclaration | None, str | None]:
    prefix = f"Project capability profile[{profile_position}].facts[{fact_position}]"
    unknown_keys = sorted(set(value) - _CAPABILITY_FACT_KEYS)
    if unknown_keys:
        return None, f"{prefix} contains unsupported key: {unknown_keys[0]}."

    support_value = value.get("support")
    if type(support_value) is not str or support_value not in _CAPABILITY_SUPPORTS:
        return (
            None,
            f"{prefix}.support must be exactly supported or explicitly_unsupported.",
        )
    domain_value = value.get("domain")
    if type(domain_value) is not str or domain_value not in _CAPABILITY_DOMAIN_VALUES:
        return (
            None,
            f"{prefix}.domain must be one exact current CapabilityDomain value.",
        )

    operands_value = value.get("operands")
    if type(operands_value) is not list:
        return None, f"{prefix}.operands must be an array of strings."
    operands = cast(list[object], operands_value)
    for operand_position, operand in enumerate(operands):
        if type(operand) is not str:
            return None, f"{prefix}.operands[{operand_position}] must be a string."
        if not operand.strip():
            return None, f"{prefix}.operands[{operand_position}] must be nonblank."

    for key in _CAPABILITY_OPTIONAL_TEXT_KEYS:
        if key in value and not _is_nonblank_text(value[key]):
            return None, f"{prefix}.{key} must be nonblank text when present."
    if "subject" not in value and "operation" not in value:
        return None, f"{prefix} requires subject or operation."
    if "extension" in value and "dialect" not in value:
        return None, f"{prefix}.extension requires dialect."

    key = CapabilityKey(
        CapabilityDomain(domain_value),
        subject=cast(str | None, value.get("subject")),
        operation=cast(str | None, value.get("operation")),
        operands=tuple(cast(list[str], operands_value)),
        context=cast(str | None, value.get("context")),
        dialect=cast(str | None, value.get("dialect")),
        extension=cast(str | None, value.get("extension")),
    )
    return (
        ProjectCapabilityProfileFactDeclaration(
            fact_position,
            _CAPABILITY_SUPPORTS[support_value],
            key,
        ),
        None,
    )


def _normalize_capability_target(
    value: Mapping[str, object],
    position: int,
) -> tuple[ProjectCapabilityTargetSelection | None, str | None]:
    prefix = f"Project capability target[{position}]"
    unknown_keys = sorted(set(value) - _CAPABILITY_TARGET_KEYS)
    if unknown_keys:
        return None, f"{prefix} contains unsupported key: {unknown_keys[0]}."
    for key in (
        "database_family",
        "database_release",
        "base_profile_namespace",
        "base_profile_name",
        "base_profile_release",
    ):
        if not _is_nonblank_text(value.get(key)):
            return None, f"{prefix}.{key} must be a nonblank string."

    overlay_references: list[CapabilityProfileReference] = []
    for overlay_position, overlay in enumerate(
        cast(list[dict[str, object]], value.get("overlays", []))
    ):
        overlay_prefix = f"{prefix}.overlays[{overlay_position}]"
        unknown_overlay_keys = sorted(
            set(overlay) - set(_CAPABILITY_TARGET_OVERLAY_KEYS)
        )
        if unknown_overlay_keys:
            return (
                None,
                f"{overlay_prefix} contains unsupported key: "
                f"{unknown_overlay_keys[0]}.",
            )
        for key in _CAPABILITY_TARGET_OVERLAY_KEYS:
            if not _is_nonblank_text(overlay.get(key)):
                return None, f"{overlay_prefix}.{key} must be a nonblank string."
        overlay_references.append(
            CapabilityProfileReference(
                CapabilityProfileIdentity(
                    cast(str, overlay["namespace"]),
                    cast(str, overlay["name"]),
                ),
                cast(str, overlay["release"]),
            )
        )

    return (
        ProjectCapabilityTargetSelection(
            position,
            cast(str, value["database_family"]),
            cast(str, value["database_release"]),
            CapabilityProfileReference(
                CapabilityProfileIdentity(
                    cast(str, value["base_profile_namespace"]),
                    cast(str, value["base_profile_name"]),
                ),
                cast(str, value["base_profile_release"]),
            ),
            tuple(overlay_references),
        ),
        None,
    )


def _is_nonempty_mapping_list(value: object) -> bool:
    return (
        type(value) is list
        and bool(value)
        and all(type(item) is dict for item in value)
    )


def _is_nonblank_text(value: object) -> bool:
    return type(value) is str and bool(value.strip())


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


def _has_exact_root_table(
    config_text: str,
    document: Mapping[str, object],
    *,
    key: str,
    header_pattern: re.Pattern[str],
) -> bool:
    matches = tuple(header_pattern.finditer(config_text))
    if not matches:
        return False
    probe_keys = _allocate_probe_keys(document, key, len(matches))
    try:
        first_probe = tomllib.loads(
            _insert_header_probes(
                config_text,
                matches,
                probe_keys,
                frozenset(range(len(matches))),
            )
        )
    except tomllib.TOMLDecodeError:
        return False
    value = first_probe.get(key)
    if type(value) is not dict:
        return False
    real_positions = _mapping_probe_positions(value, probe_keys)
    if real_positions is None or len(real_positions) != 1:
        return False
    try:
        probed = tomllib.loads(
            _insert_header_probes(
                config_text,
                matches,
                probe_keys,
                real_positions,
            )
        )
    except tomllib.TOMLDecodeError:
        return False
    probed_value = probed.get(key)
    if not _remove_mapping_probes(probed_value, probe_keys, real_positions):
        return False
    return _toml_values_equivalent(probed, document)


def _has_exact_aot_path(
    config_text: str,
    document: Mapping[str, object],
    *,
    path: tuple[str, ...],
    header_pattern: re.Pattern[str],
) -> bool:
    matches = tuple(header_pattern.finditer(config_text))
    if not matches:
        return False
    probe_keys = _allocate_probe_keys(document, "_".join(path), len(matches))
    try:
        first_probe = tomllib.loads(
            _insert_header_probes(
                config_text,
                matches,
                probe_keys,
                frozenset(range(len(matches))),
            )
        )
    except tomllib.TOMLDecodeError:
        return False
    entries = _toml_path_entries(first_probe, path)
    real_positions = _entry_probe_positions(entries, probe_keys)
    if real_positions is None or len(real_positions) != len(entries):
        return False
    try:
        probed = tomllib.loads(
            _insert_header_probes(
                config_text,
                matches,
                probe_keys,
                real_positions,
            )
        )
    except tomllib.TOMLDecodeError:
        return False
    if not _remove_entry_probes(
        _toml_path_entries(probed, path),
        probe_keys,
        real_positions,
    ):
        return False
    return _toml_values_equivalent(probed, document)


def _toml_path_entries(
    document: Mapping[str, object],
    path: tuple[str, ...],
) -> tuple[dict[str, object], ...]:
    values: tuple[object, ...] = (document,)
    for key in path:
        children: list[object] = []
        for value in values:
            containers = cast(list[object], value) if type(value) is list else (value,)
            for container in containers:
                if type(container) is dict and key in container:
                    children.append(cast(dict[str, object], container)[key])
        values = tuple(children)
    entries: list[dict[str, object]] = []
    for value in values:
        if type(value) is not list or any(type(item) is not dict for item in value):
            return ()
        entries.extend(cast(list[dict[str, object]], value))
    return tuple(entries)


def _allocate_probe_keys(
    document: Mapping[str, object],
    label: str,
    count: int,
) -> tuple[str, ...]:
    occupied = set(_toml_mapping_keys(document))
    probes: list[str] = []
    candidate_position = 0
    while len(probes) < count:
        candidate = f"__pietto_schema_v4_{label}_probe_{candidate_position}__"
        candidate_position += 1
        if candidate in occupied:
            continue
        occupied.add(candidate)
        probes.append(candidate)
    return tuple(probes)


def _toml_mapping_keys(value: object) -> frozenset[str]:
    keys: set[str] = set()
    pending = [value]
    while pending:
        current = pending.pop()
        if type(current) is dict:
            mapping = cast(dict[str, object], current)
            keys.update(mapping)
            pending.extend(mapping.values())
        elif type(current) is list:
            pending.extend(cast(list[object], current))
    return frozenset(keys)


def _mapping_probe_positions(
    value: object,
    probe_keys: tuple[str, ...],
) -> frozenset[int] | None:
    if type(value) is not dict:
        return None
    positions_by_key = {key: position for position, key in enumerate(probe_keys)}
    found: set[int] = set()
    for item_key, item_value in cast(dict[str, object], value).items():
        position = positions_by_key.get(item_key)
        if position is None:
            continue
        if item_value is not True or position in found:
            return None
        found.add(position)
    return frozenset(found)


def _remove_mapping_probes(
    value: object,
    probe_keys: tuple[str, ...],
    expected_positions: frozenset[int],
) -> bool:
    if _mapping_probe_positions(value, probe_keys) != expected_positions:
        return False
    mapping = cast(dict[str, object], value)
    for position in expected_positions:
        del mapping[probe_keys[position]]
    return True


def _entry_probe_positions(
    entries: tuple[dict[str, object], ...],
    probe_keys: tuple[str, ...],
) -> frozenset[int] | None:
    if not entries:
        return None
    positions_by_key = {key: position for position, key in enumerate(probe_keys)}
    found: set[int] = set()
    for entry in entries:
        entry_positions = tuple(
            positions_by_key[key] for key in entry if key in positions_by_key
        )
        if (
            len(entry_positions) != 1
            or entry[probe_keys[entry_positions[0]]] is not True
            or entry_positions[0] in found
        ):
            return None
        found.add(entry_positions[0])
    return frozenset(found)


def _remove_entry_probes(
    entries: tuple[dict[str, object], ...],
    probe_keys: tuple[str, ...],
    expected_positions: frozenset[int],
) -> bool:
    if _entry_probe_positions(entries, probe_keys) != expected_positions:
        return False
    for entry in entries:
        for probe_key in probe_keys:
            if probe_key in entry:
                del entry[probe_key]
    return True


def _insert_header_probes(
    config_text: str,
    matches: tuple[re.Match[str], ...],
    probe_keys: tuple[str, ...],
    positions: frozenset[int],
) -> str:
    parts: list[str] = []
    cursor = 0
    for position, match in enumerate(matches):
        parts.append(config_text[cursor : match.end()])
        if position in positions:
            suffix = match.group("suffix")
            newline = "\r\n" if suffix.endswith("\r\n") else "\n"
            if not suffix.endswith("\n"):
                parts.append(newline)
            parts.append(f"{probe_keys[position]} = true{newline}")
        cursor = match.end()
    parts.append(config_text[cursor:])
    return "".join(parts)


def _toml_values_equivalent(left: object, right: object) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        left_mapping = cast(dict[str, object], left)
        right_mapping = cast(dict[str, object], right)
        return left_mapping.keys() == right_mapping.keys() and all(
            _toml_values_equivalent(value, right_mapping[key])
            for key, value in left_mapping.items()
        )
    if type(left) is list:
        left_values = cast(list[object], left)
        right_values = cast(list[object], right)
        return len(left_values) == len(right_values) and all(
            _toml_values_equivalent(left_value, right_value)
            for left_value, right_value in zip(left_values, right_values, strict=True)
        )
    if type(left) is float:
        left_float = cast(float, left)
        right_float = cast(float, right)
        return left_float == right_float or (
            math.isnan(left_float) and math.isnan(right_float)
        )
    return left == right


def _validate_root_package_config(
    root: ProjectRoot,
    config_path: ProjectConfigPath,
    package: object,
    pinned_root: ProjectPinnedRoot,
    *,
    schema_version: int = 3,
    capability_environment: ProjectCapabilityEnvironmentConfig | None = None,
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
            schema_version=schema_version,
            sources=None,
            compilation_mode=ProjectCompilationMode.PACKAGE_ROOT,
            root_package=ProjectRootPackageActivation(
                path=path,
                namespace=package["namespace"],  # type: ignore[arg-type]
                name=package["name"],  # type: ignore[arg-type]
                version=package["version"],  # type: ignore[arg-type]
                sha256=package["sha256"],  # type: ignore[arg-type]
            ),
            capability_environment=capability_environment,
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
