from __future__ import annotations

import inspect
import tomllib
from pathlib import Path

import pietto.cli as cli
import pietto.sql as sql_api
from pietto.ir import ScriptIR
from pietto.sql import SqlResult
from pietto.sql.mysql import emit_mysql_sql

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_mysql_entry_point_is_private_and_keeps_existing_models() -> None:
    signature = inspect.signature(emit_mysql_sql)

    assert tuple(signature.parameters) == ("script_ir",)
    assert signature.return_annotation == "SqlResult"
    assert emit_mysql_sql(ScriptIR(definitions=())) == SqlResult((), ())
    assert set(sql_api.__all__) == {
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    }
    assert not hasattr(sql_api, "emit_mysql_sql")
    assert not hasattr(sql_api, "emit_sql")


def test_mysql_skeleton_remains_private_after_cli_dispatch() -> None:
    cli_source = _read("src/pietto/cli.py")
    runtime_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (REPO_ROOT / "src" / "pietto").rglob("*.py")
        if "generated" not in path.parts
    )

    assert "import pietto.sql.mysql as mysql_backend" in cli_source
    assert "return mysql_backend.emit_mysql_sql" in cli_source
    assert '_ENABLED_SQL_DIALECTS = ("postgres", "mysql")' in cli_source
    assert "mysql.table" in runtime_source
    assert "def emit_sql(" not in runtime_source
    assert "def _select_sql_emitter(" in runtime_source
    assert cli.main(["emit-sql", "missing.pietto", "--dialect", "sqlite"]) == 2


def test_mysql_skeleton_has_no_dependency_or_forbidden_stage_imports() -> None:
    project = tomllib.loads(_read("pyproject.toml"))
    mysql_source = _read("src/pietto/sql/mysql.py").lower()

    assert [
        dependency.split(">", 1)[0].split("=", 1)[0].split("<", 1)[0]
        for dependency in project["project"]["dependencies"]
    ] == ["antlr4-python3-runtime"]
    assert "sqlglot" not in _read("pyproject.toml").lower()
    assert 'name = "sqlglot"' not in _read("uv.lock")
    for forbidden in (
        "pietto.parser",
        "pietto.semantic",
        "pietto.ir.builder",
        "pietto.cli",
        "pietto.cli_json",
        "pathlib",
        "open(",
        "sqlglot",
    ):
        assert forbidden not in mysql_source


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")
