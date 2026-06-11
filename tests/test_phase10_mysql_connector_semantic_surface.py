from __future__ import annotations

import inspect
import tomllib
from pathlib import Path

import pietto.cli as cli
import pietto.semantic.source_connectors as connector_module
import pietto.sql as sql_api
from pietto.sql.mysql import emit_mysql_sql

REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE10_PLAN = "docs/plan/phase-10-mysql-sql-generation-mvp.md"


def test_slice5_status_and_cross_references_are_complete() -> None:
    plan = _read(PHASE10_PLAN)
    status_documents = (
        _read("README.md"),
        _read("AGENTS.md"),
        _read("docs/spec/pietto-v0.9.md"),
    )

    assert "**Slice 5: MySQL Connector Semantic Surface is complete.**" in plan
    assert "5. **MySQL Connector Semantic Surface**: complete." in plan
    for document in status_documents:
        normalized = " ".join(document.split())
        assert "Phase 10 MySQL SQL Generation MVP is complete" in normalized
        assert "mysql.table(Text)" in normalized
        assert "private handwritten MySQL" in normalized


def test_connector_catalog_is_exact_and_static() -> None:
    assert connector_module._KNOWN_CONNECTORS == (
        "postgres.table",
        "mysql.table",
    )

    connector_paths = {
        path.relative_to(REPO_ROOT).as_posix()
        for path in (REPO_ROOT / "src" / "pietto").rglob("*.py")
        if "generated" not in path.parts
        and "mysql.table" in path.read_text(encoding="utf-8")
    }
    assert connector_paths == {
        "src/pietto/ir/lowering.py",
        "src/pietto/semantic/source_connectors.py",
        "src/pietto/sql/mysql_relations.py",
    }


def test_connector_modules_have_no_runtime_or_database_surface() -> None:
    source = "\n".join(
        _read(path)
        for path in (
            "src/pietto/semantic/source_connectors.py",
            "src/pietto/ir/lowering.py",
        )
    ).lower()

    for forbidden in (
        "credential",
        "database connection",
        "dsn",
        "endpoint",
        "requests",
        "socket",
        "sqlalchemy",
        "subprocess",
        "urllib",
    ):
        assert forbidden not in source


def test_mysql_backend_remains_private_when_cli_enabled() -> None:
    signature = inspect.signature(emit_mysql_sql)
    cli_source = _read("src/pietto/cli.py")

    assert tuple(signature.parameters) == ("script_ir",)
    assert signature.return_annotation == "SqlResult"
    assert set(sql_api.__all__) == {
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    }
    assert not hasattr(sql_api, "emit_mysql_sql")
    assert not hasattr(sql_api, "emit_sql")
    assert "mysql.table" not in cli_source
    assert "return mysql_backend.emit_mysql_sql" in cli_source
    assert '_ENABLED_SQL_DIALECTS = ("postgres", "mysql")' in cli_source
    assert cli.main(["emit-sql", "missing.pietto", "--dialect", "sqlite"]) == 2


def test_dependencies_and_sqlglot_boundary_are_unchanged() -> None:
    project = tomllib.loads(_read("pyproject.toml"))

    assert project["project"]["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
    assert "sqlglot" not in _read("pyproject.toml").lower()
    assert 'name = "sqlglot"' not in _read("uv.lock")


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")
