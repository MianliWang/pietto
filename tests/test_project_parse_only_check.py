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


DEF_HEAD = (
    "shape Row:\n"
    "    id: Int not null\n"
    "    n: Int nullable\n"
    "    text: Text not null\n"
    "    unique row_key on id\n"
    "shape Other:\n"
    "    id: Int not null\n"
    "    row_id: Int not null\n"
    'source rows: Row is postgres.table("rows")\n'
    'source others: Other is postgres.table("others")\n'
    "def idi(x: Int not null) -> Int not null: return x\n"
    "def pos(x: Int nullable) -> Bool nullable: return x > 0\n"
)
# The first line written after DEF_HEAD.
DEF_LINE = 13


def _def_project(tmp_path: Path, source: str, schema: int = 2):
    root = tmp_path / "project"
    _write(
        root,
        "pietto.toml",
        f'schema_version = {schema}\n[sources]\ninclude = ["*.pietto"]\n',
    )
    _write(root, "a.pietto", DEF_HEAD + source)
    result = check_project_parse_only(root)
    assert result.errors == ()
    return [
        (diagnostic.code, diagnostic.location.line, diagnostic.location.column)
        for diagnostic in result.diagnostics
    ], [diagnostic.message for diagnostic in result.diagnostics]


def test_a_flat_project_keeps_every_def_gated(tmp_path: Path) -> None:
    located, messages = _def_project(tmp_path, "", schema=1)
    assert located == [("PIE-S2379", DEF_LINE - 2, 1), ("PIE-S2379", DEF_LINE - 1, 1)]
    assert set(messages) == {
        "Inline `def` functions are available only in single files and "
        "EXPLICIT_MODULES projects (schema version 2)."
    }


DEF_POSITIONS = {
    "table_function": (
        "query q:\n    from generate_series(idi(1), 3, 1) as s\n"
        "    select:\n        s\n",
        [(DEF_LINE + 1, 26)],
        "a table-function input",
    ),
    "window_argument": (
        "query q:\n    from rows\n    select:\n        id\n"
        "        r = lag(idi(n)) window:\n            order by: id\n",
        [(DEF_LINE + 4, 17)],
        "a window computation",
    ),
    "window_key": (
        "query q:\n    from rows\n    select:\n        id\n"
        "        r = row_number() window:\n            partition by: idi(id)\n"
        "            order by: idi(n)\n",
        [(DEF_LINE + 5, 27), (DEF_LINE + 6, 23)],
        "a window computation",
    ),
    "values_row": (
        "query q:\n    values(a: Int not null, b: Int not null):\n        idi(1), 2\n",
        [(DEF_LINE + 2, 9)],
        "a VALUES row",
    ),
    "relationship": (
        "relationship link:\n    endpoint row: rows\n    endpoint other: others\n"
        "    on idi(other.row_id) == row.id\n",
        [(DEF_LINE + 3, 8)],
        "a relationship condition",
    ),
}


@pytest.mark.parametrize(
    ("source", "calls", "position"), DEF_POSITIONS.values(), ids=DEF_POSITIONS
)
def test_a_project_refuses_a_def_call_where_the_written_form_has_its_own_rule(
    tmp_path: Path, source: str, calls: list[tuple[int, int]], position: str
) -> None:
    located, messages = _def_project(tmp_path, source)
    assert located == [("PIE-S2397", line, column) for line, column in calls]
    assert set(messages) == {f"A def call is not available in {position}: idi"}


def test_a_def_argument_cannot_read_a_relation(tmp_path: Path) -> None:
    located, messages = _def_project(
        tmp_path,
        "query q:\n    let low:\n        from rows\n        select:\n"
        "            k = id\n    from rows\n    where pos(scalar low.k) and pos(id)\n"
        "    select:\n        id\n",
    )
    assert located == [("PIE-S2395", DEF_LINE + 6, 11)]
    assert messages == [
        "Invalid argument for def pos at position 1 (x): an argument cannot read "
        "a relation (exists, scalar or in) yet"
    ]


def test_a_def_cannot_be_an_export_item(tmp_path: Path) -> None:
    located, _ = _def_project(tmp_path, "export:\n    def idi\n")
    assert located == [("PIE-P1000", DEF_LINE + 1, 5)]


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
