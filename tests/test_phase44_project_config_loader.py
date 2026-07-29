from __future__ import annotations

from pathlib import Path

import pytest

from pietto._project.config import load_project_config
from pietto._project.module_carrier import ProjectCompilationMode
from pietto._project.model import ProjectConfigLoadResult, ProjectDiscoveryErrorKind


def test_valid_project_config_is_loaded_without_source_selection(
    tmp_path: Path,
) -> None:
    root = _project_root(
        tmp_path,
        """
        schema_version = 1

        [sources]
        include = ["models/**/*.pietto", "*.pietto"]
        exclude = ["models/tmp/*.pietto"]
        """,
    )

    result = load_project_config(root)

    assert result.ok
    assert result.root is not None
    assert result.root.path == "."
    assert result.config_path is not None
    assert result.config_path.path == "pietto.toml"
    assert result.config is not None
    assert result.config.schema_version == 1
    assert result.config.compilation_mode is ProjectCompilationMode.LEGACY_FLAT
    assert result.config.sources.include_patterns == (
        "models/**/*.pietto",
        "*.pietto",
    )
    assert result.config.sources.exclude_patterns == ("models/tmp/*.pietto",)


def test_missing_exclude_is_normalized_to_empty_tuple(tmp_path: Path) -> None:
    root = _project_root(
        tmp_path,
        """
        schema_version = 1

        [sources]
        include = ["models/**/*.pietto"]
        """,
    )

    result = load_project_config(root)

    assert result.ok
    assert result.config is not None
    assert result.config.sources.exclude_patterns == ()


def test_loader_does_not_expand_globs_or_read_sources(tmp_path: Path) -> None:
    root = _project_root(
        tmp_path,
        """
        schema_version = 1

        [sources]
        include = ["missing/**/*.pietto"]
        """,
    )

    result = load_project_config(root)

    assert result.ok
    assert result.config is not None
    assert result.config.sources.include_patterns == ("missing/**/*.pietto",)


@pytest.mark.parametrize(
    "config_text",
    [
        """
        [sources]
        include = ["models/**/*.pietto"]
        """,
        """
        schema_version = true

        [sources]
        include = ["models/**/*.pietto"]
        """,
        """
        schema_version = 3

        [sources]
        include = ["models/**/*.pietto"]
        """,
        """
        schema_version = 1
        """,
        """
        schema_version = 1

        [sources]
        exclude = []
        """,
        """
        schema_version = 1

        [sources]
        include = []
        """,
        """
        schema_version = 1

        [sources]
        include = [1]
        """,
        """
        schema_version = 1

        [sources]
        include = ["models/**/*.pietto"]
        exclude = [false]
        """,
        """
        schema_version = 1
        name = "project"

        [sources]
        include = ["models/**/*.pietto"]
        """,
        """
        schema_version = 1

        [sources]
        include = ["models/**/*.pietto"]
        default = []
        """,
    ],
)
def test_schema_invalid_config_reports_config_schema(
    tmp_path: Path,
    config_text: str,
) -> None:
    root = _project_root(tmp_path, config_text)

    result = load_project_config(root)

    assert not result.ok
    assert result.config is None
    assert _error_kinds(result) == (ProjectDiscoveryErrorKind.CONFIG_SCHEMA,)


@pytest.mark.parametrize(
    "config_text",
    [
        "schema_version = 1\nschema_version = 1\n",
        "not valid = [\n",
    ],
)
def test_invalid_toml_reports_config_parse(
    tmp_path: Path,
    config_text: str,
) -> None:
    root = _project_root(tmp_path, config_text)

    result = load_project_config(root)

    assert not result.ok
    assert result.config is None
    assert _error_kinds(result) == (ProjectDiscoveryErrorKind.CONFIG_PARSE,)


def test_missing_config_reports_config_read(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()

    result = load_project_config(root)

    assert not result.ok
    assert result.config is None
    assert _error_kinds(result) == (ProjectDiscoveryErrorKind.CONFIG_READ,)
    assert result.errors[0].path == "pietto.toml"


def test_invalid_root_reports_project_root(tmp_path: Path) -> None:
    result = load_project_config(tmp_path / "missing")

    assert not result.ok
    assert result.root is None
    assert result.config_path is None
    assert result.config is None
    assert _error_kinds(result) == (ProjectDiscoveryErrorKind.PROJECT_ROOT,)


@pytest.mark.parametrize(
    "pattern",
    [
        "",
        "/abs.pietto",
        "C:/models/a.pietto",
        "//server/share/a.pietto",
        "models\\a.pietto",
        "models//a.pietto",
        "./models/a.pietto",
        "models/../a.pietto",
        "models/",
        "~/.pietto",
        "$MODELS/*.pietto",
        "models/$(name).pietto",
        "models/`name`.pietto",
        "models/**.pietto",
        "models/a**/b.pietto",
        "models/[a-z].pietto",
        "models/{a,b}.pietto",
        "!models/*.pietto",
        "models/@(a).pietto",
        "models/!(a).pietto",
        "models/with\\u0000nul.pietto",
    ],
)
def test_invalid_patterns_report_project_path(
    tmp_path: Path,
    pattern: str,
) -> None:
    root = _project_root(
        tmp_path,
        f"""
        schema_version = 1

        [sources]
        include = [{pattern!r}]
        """,
    )

    result = load_project_config(root)

    assert not result.ok
    assert result.config is None
    assert _error_kinds(result) == (ProjectDiscoveryErrorKind.PROJECT_PATH,)


def test_multiple_invalid_patterns_are_reported_in_order(tmp_path: Path) -> None:
    root = _project_root(
        tmp_path,
        """
        schema_version = 1

        [sources]
        include = ["/abs.pietto"]
        exclude = ["models/[a-z].pietto"]
        """,
    )

    result = load_project_config(root)

    assert not result.ok
    assert result.config is None
    assert _error_kinds(result) == (
        ProjectDiscoveryErrorKind.PROJECT_PATH,
        ProjectDiscoveryErrorKind.PROJECT_PATH,
    )
    assert [error.path for error in result.errors] == [
        "/abs.pietto",
        "models/[a-z].pietto",
    ]


@pytest.mark.parametrize(
    "pattern",
    [
        "*.pietto",
        "models/*.pietto",
        "models/**/*.pietto",
        "models/a?b.pietto",
        ".generated/**/*.pietto",
    ],
)
def test_valid_pattern_subset_is_accepted(tmp_path: Path, pattern: str) -> None:
    root = _project_root(
        tmp_path,
        f"""
        schema_version = 1

        [sources]
        include = [{pattern!r}]
        """,
    )

    result = load_project_config(root)

    assert result.ok
    assert result.config is not None
    assert result.config.sources.include_patterns == (pattern,)


def _project_root(tmp_path: Path, config_text: str) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    (root / "pietto.toml").write_text(config_text, encoding="utf-8")
    return root


def _error_kinds(
    result: ProjectConfigLoadResult,
) -> tuple[ProjectDiscoveryErrorKind, ...]:
    return tuple(error.kind for error in result.errors)
