from __future__ import annotations

from pathlib import Path

import pytest

import pietto.ir as ir_api
import pietto.semantic as semantic_api
import pietto.sql as sql_api
import pietto.sql.mysql as mysql_backend
from pietto._project.check import check_project_parse_only
from pietto._project.model import ProjectDiscoveryErrorKind, ProjectInput


def test_parse_only_project_check_parses_selected_sources_deterministically(
    tmp_path: Path,
) -> None:
    root = _project_root(
        tmp_path,
        include=("models/*.pietto", "*.pietto"),
        exclude=("models/tmp/*.pietto",),
    )
    _write(root, "root.pietto", "shape Root:\n    id: Int\n")
    _write(root, "models/z.pietto", "shape Zed:\n    id: Int\n")
    _write(root, "models/a.pietto", "shape Alpha:\n    id: Int\n")
    _write(root, "models/tmp/skip.pietto", "not parsed\n")

    result = check_project_parse_only(root)

    assert result.ok
    assert result.errors == ()
    assert result.diagnostics == ()
    assert result.inputs == (
        ProjectInput(path="models/a.pietto", status="parsed"),
        ProjectInput(path="models/z.pietto", status="parsed"),
        ProjectInput(path="root.pietto", status="parsed"),
    )


def test_parse_only_project_check_aggregates_project_relative_parser_diagnostics(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto", "models/*.pietto"))
    _write(root, "bad.pietto", "shape Broken\n    id: Int\n")
    _write(root, "models/good.pietto", "shape Good:\n    id: Int\n")

    result = check_project_parse_only(root)

    assert not result.ok
    assert result.errors == ()
    assert result.inputs == (
        ProjectInput(path="bad.pietto", status="error"),
        ProjectInput(path="models/good.pietto", status="parsed"),
    )
    assert result.diagnostics
    assert {diagnostic.location.path for diagnostic in result.diagnostics} == {
        "bad.pietto"
    }
    assert all(
        str(tmp_path) not in str(diagnostic) for diagnostic in result.diagnostics
    )


@pytest.mark.parametrize("schema", [1, 2], ids=["legacy_flat", "explicit_modules"])
def test_parse_only_project_check_adds_gate_diagnostics_beside_parse_errors(
    tmp_path: Path, schema: int
) -> None:
    root = tmp_path / "project"
    _write(
        root,
        "pietto.toml",
        f'schema_version = {schema}\n[sources]\ninclude = ["*.pietto"]\n',
    )
    _write(root, "a.pietto", "table broken\n")
    _write(
        root,
        "b.pietto",
        "query q(a: Int not null):\n    from rows\n    select:\n        id\n"
        "query r:\n    from rows\n    where exists t and id == scalar t.c\n"
        "    select:\n        id\n"
        "type Age = Int:\n    ensure self > scalar t.c\n",
    )
    _write(root, "c.pietto", "query valid:\n    from rows\n    select:\n        id\n")

    result = check_project_parse_only(root)

    assert not result.ok and result.errors == ()
    assert result.inputs == (
        ProjectInput(path="a.pietto", status="error"),
        ProjectInput(path="b.pietto", status="parsed"),
        ProjectInput(path="c.pietto", status="parsed"),
    )
    paths = [diagnostic.location.path or "" for diagnostic in result.diagnostics]
    assert paths == sorted(paths) and set(paths) == {"a.pietto", "b.pietto"}
    assert {
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.location.path == "a.pietto"
    } == {"PIE-P1000"}
    # An explicit-module project admits a SELECT-body query header and the
    # relation reads inside a relation body; a read in a type rule stays gated.
    assert [
        (diagnostic.code, diagnostic.location.line, diagnostic.location.column)
        for diagnostic in result.diagnostics
        if diagnostic.location.path == "b.pietto"
    ] == [("PIE-S2346", 1, 9), ("PIE-S2349", 7, 11), ("PIE-S2348", 7, 30)] * (
        schema == 1
    ) + [("PIE-S2348", 11, 19)]


def test_parse_only_project_check_reports_source_read_errors_and_continues(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(root, "good.pietto", "shape Good:\n    id: Int\n")
    _write_bytes(root, "bad.pietto", b"\xff")

    result = check_project_parse_only(root)

    assert not result.ok
    assert result.inputs == (
        ProjectInput(path="bad.pietto", status="error"),
        ProjectInput(path="good.pietto", status="parsed"),
    )
    assert [(error.kind, error.path) for error in result.errors] == [
        (ProjectDiscoveryErrorKind.SOURCE_READ, "bad.pietto")
    ]
    assert result.diagnostics == ()


def test_parse_only_project_check_forwards_config_and_selection_errors(
    tmp_path: Path,
) -> None:
    missing_config_root = tmp_path / "missing-config"
    missing_config_root.mkdir()

    missing_config = check_project_parse_only(missing_config_root)

    assert missing_config.inputs == ()
    assert [error.kind for error in missing_config.errors] == [
        ProjectDiscoveryErrorKind.CONFIG_READ
    ]

    empty_selection_root = _project_root(
        tmp_path / "empty-selection", include=("*.pietto",)
    )

    empty_selection = check_project_parse_only(empty_selection_root)

    assert empty_selection.inputs == ()
    assert [error.kind for error in empty_selection.errors] == [
        ProjectDiscoveryErrorKind.PROJECT_GLOB
    ]


def test_parse_only_project_check_does_not_enter_compiler_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "semantically_invalid.pietto",
        "table report:\n    from missing\n    select:\n        id\n",
    )

    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError(
            "parse-only project check must stop before compiler stages"
        )

    monkeypatch.setattr(semantic_api, "analyze", unexpected_call)
    monkeypatch.setattr(ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(sql_api, "emit_postgres_sql", unexpected_call)
    monkeypatch.setattr(mysql_backend, "emit_mysql_sql", unexpected_call)

    result = check_project_parse_only(root)

    assert result.ok
    assert result.inputs == (
        ProjectInput(path="semantically_invalid.pietto", status="parsed"),
    )


def _project_root(
    tmp_path: Path,
    *,
    include: tuple[str, ...],
    exclude: tuple[str, ...] = (),
) -> Path:
    root = tmp_path / "project"
    root.mkdir(parents=True)
    config_text = (
        "schema_version = 1\n\n"
        "[sources]\n"
        f"include = {_toml_array(include)}\n"
        f"exclude = {_toml_array(exclude)}\n"
    )
    (root / "pietto.toml").write_text(config_text, encoding="utf-8")
    return root


def _toml_array(values: tuple[str, ...]) -> str:
    return "[" + ", ".join(f'"{value}"' for value in values) + "]"


def _write(root: Path, relative_path: str, source: str) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _write_bytes(root: Path, relative_path: str, content: bytes) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path
