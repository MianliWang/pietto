from __future__ import annotations

from pathlib import Path

import pytest

from pietto._project import config
from pietto._project.config import load_project_config
from pietto._project.module_carrier import ProjectCompilationMode
from pietto._project.model import (
    ProjectConfigLoadResult,
    ProjectDiscoveryError,
    ProjectDiscoveryErrorKind,
)


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
    assert result.config.sources is not None
    assert result.config.sources.include_patterns == (
        "models/**/*.pietto",
        "*.pietto",
    )
    assert result.config.sources.exclude_patterns == ("models/tmp/*.pietto",)
    assert result.config.root_package is None


@pytest.mark.parametrize(
    ("schema_version", "compilation_mode"),
    (
        (1, ProjectCompilationMode.LEGACY_FLAT),
        (2, ProjectCompilationMode.EXPLICIT_MODULES),
    ),
)
def test_schema_v1_v2_keep_exact_sources_arm_after_package_activation(
    tmp_path: Path,
    schema_version: int,
    compilation_mode: ProjectCompilationMode,
) -> None:
    root = _project_root(
        tmp_path,
        f"""\n        schema_version = {schema_version}\n\n        [sources]\n        include = ["models/**/*.pietto"]\n        """,
    )

    result = load_project_config(root)

    assert result.ok
    assert result.config is not None
    assert result.config.compilation_mode is compilation_mode
    assert result.config.sources is not None
    assert result.config.root_package is None


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
    assert result.config.sources is not None
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
    assert result.config.sources is not None
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


def test_an_integer_too_long_for_tomllib_reports_config_parse(
    tmp_path: Path,
) -> None:
    # tomllib refuses a decimal integer over 4300 digits with the plain
    # ValueError of int(), not TOMLDecodeError; it used to escape the loader.
    root = _project_root(tmp_path, "schema_version = 2\nx = " + "9" * 5000 + "\n")

    result = load_project_config(root)

    assert not result.ok and result.config is None
    assert result.errors == (
        ProjectDiscoveryError(
            ProjectDiscoveryErrorKind.CONFIG_PARSE,
            "Project configuration TOML is invalid: Exceeds the limit (4300 digits)"
            " for integer string conversion: value has 5000 digits.",
            "pietto.toml",
        ),
    )


@pytest.mark.parametrize("probe", [False, True], ids=["parse", "header_probe"])
def test_toml_nested_too_deeply_reports_project_resource(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, probe: bool
) -> None:
    # Both used to raise RecursionError out of the loader: the parse of a
    # 5,000-deep array, and validation's second parse with a header probe of
    # a value just shallow enough for the first.
    if probe:
        config_text = 'schema_version = 3\n[package]\npath = "package"\n'

        def exhausted(*args: object) -> bool:
            del args
            raise RecursionError

        monkeypatch.setattr(config, "_has_exact_root_package_table", exhausted)
    else:
        config_text = "schema_version = 1\nx = " + "[" * 5000 + "]" * 5000 + "\n"
    root = _project_root(tmp_path, config_text)

    result = load_project_config(root)

    assert not result.ok and result.config is None
    assert result.errors == (
        ProjectDiscoveryError(
            ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
            "Project configuration TOML is nested too deeply.",
            "pietto.toml",
        ),
    )


def test_a_nan_beside_an_exact_package_table_reports_its_own_fault(
    tmp_path: Path,
) -> None:
    root = _project_root(
        tmp_path,
        "schema_version = 4\n"
        + _PACKAGE_TABLE
        + "[capability_environment]\nweight = nan\n",
    )

    assert load_project_config(root).errors == (
        ProjectDiscoveryError(
            ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
            "Project [capability_environment] contains unsupported key: weight.",
            "pietto.toml",
        ),
    )


@pytest.mark.parametrize("quote", ['"', "'"])
def test_a_header_line_inside_a_string_does_not_prove_a_quoted_package_table(
    tmp_path: Path, quote: str
) -> None:
    root = _project_root(
        tmp_path,
        f"schema_version = 4\n[capability_environment]\n[{quote}package{quote}]\n"
        + _PACKAGE_TABLE.removeprefix('[package]\npath = "."\n')
        + f"path = {quote * 3}\n[package] #{quote * 3} # c\n",
    )

    assert load_project_config(root).errors == (
        ProjectDiscoveryError(
            ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
            "Project configuration schema-v4 package activation "
            "requires an exact [package] root table.",
            "pietto.toml",
        ),
    )


def test_header_proofs_parse_as_often_however_many_headers_a_string_holds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A proof that parses once per header line is quadratic in such a file.
    parses: list[str] = []
    load = config.load_toml_text

    def counted(text: str) -> dict[str, object]:
        parses.append(text)
        return load(text)

    monkeypatch.setattr(config, "load_toml_text", counted)
    counts: list[int] = []
    for lines in (1, 200):
        parses.clear()
        (tmp_path / str(lines)).mkdir()
        root = _project_root(
            tmp_path / str(lines),
            'schema_version = 4\n[capability_environment]\njunk = """\n'
            + "[package]\n" * lines
            + '"""\n'
            + _PACKAGE_TABLE,
        )
        assert not load_project_config(root).ok
        counts.append(len(parses))

    assert counts[0] == counts[1]


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


_PATH = ProjectDiscoveryErrorKind.PROJECT_PATH
_GLOB = ProjectDiscoveryErrorKind.PROJECT_GLOB
_SEPARATOR = "Project source pattern must use / as the path separator."
_RELATIVE = "Project source pattern must be relative to the project root."
_NORMALIZED = "Project source pattern must be a normalized project-relative pattern."
_SYNTAX = (
    "Project source pattern uses unsupported glob syntax; patterns use only *, ?"
    " and a whole ** path part."
)


@pytest.mark.parametrize(
    ("pattern", "kind", "message"),
    [
        ("", _PATH, _NORMALIZED),
        ("/abs.pietto", _PATH, _RELATIVE),
        ("C:/models/a.pietto", _PATH, _RELATIVE),
        ("//server/share/a.pietto", _PATH, _RELATIVE),
        ("models\\a.pietto", _PATH, _SEPARATOR),
        ("models//a.pietto", _PATH, _NORMALIZED),
        ("./models/a.pietto", _PATH, _NORMALIZED),
        ("models/../a.pietto", _PATH, _RELATIVE),
        ("models/", _PATH, _NORMALIZED),
        ("~/.pietto", _PATH, _RELATIVE),
        ("$MODELS/*.pietto", _GLOB, _SYNTAX),
        ("models/$(name).pietto", _GLOB, _SYNTAX),
        ("models/`name`.pietto", _GLOB, _SYNTAX),
        ("models/**.pietto", _GLOB, _SYNTAX),
        ("models/a**/b.pietto", _GLOB, _SYNTAX),
        ("models/[a-z].pietto", _GLOB, _SYNTAX),
        ("models/{a,b}.pietto", _GLOB, _SYNTAX),
        ("!models/*.pietto", _GLOB, _SYNTAX),
        ("models/@(a).pietto", _GLOB, _SYNTAX),
        ("models/!(a).pietto", _GLOB, _SYNTAX),
        ("models/with\\u0000nul.pietto", _PATH, _SEPARATOR),
    ],
)
def test_invalid_patterns_report_their_own_fault(
    tmp_path: Path,
    pattern: str,
    kind: ProjectDiscoveryErrorKind,
    message: str,
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
    assert [(error.kind, error.message) for error in result.errors] == [(kind, message)]


def test_utf8_bom_config_reports_a_readable_parse_error(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "pietto.toml").write_bytes(
        b'\xef\xbb\xbfschema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n'
    )

    result = load_project_config(root)

    assert result.config is None
    assert [(error.kind, error.message, error.path) for error in result.errors] == [
        (
            ProjectDiscoveryErrorKind.CONFIG_PARSE,
            "pietto.toml starts with a UTF-8 byte-order mark; save it as UTF-8"
            " without BOM.",
            "pietto.toml",
        )
    ]


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
        ProjectDiscoveryErrorKind.PROJECT_GLOB,
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
    assert result.config.sources is not None
    assert result.config.sources.include_patterns == (pattern,)


_PACKAGE_TABLE = (
    '[package]\npath = "."\nnamespace = "a"\nname = "x"\nversion = "1.0.0"\n'
    'sha256 = "' + "0" * 64 + '"\n'
)


def _project_root(tmp_path: Path, config_text: str) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    (root / "pietto.toml").write_text(config_text, encoding="utf-8")
    return root


def _error_kinds(
    result: ProjectConfigLoadResult,
) -> tuple[ProjectDiscoveryErrorKind, ...]:
    return tuple(error.kind for error in result.errors)
