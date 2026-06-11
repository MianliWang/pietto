from __future__ import annotations

import inspect
import tomllib
from pathlib import Path

import pietto.cli as cli
import pietto.sql as sql_api
import pietto.sql.mysql as mysql_module
import pietto.sql.mysql_expressions as expression_module
import pietto.sql.mysql_relations as relation_module
import pietto.sql.mysql_render as render_module
from pietto.sql.mysql import emit_mysql_sql

REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE10_PLAN = "docs/plan/phase-10-mysql-sql-generation-mvp.md"


def test_slice6_status_and_cross_references_are_complete() -> None:
    plan = _read(PHASE10_PLAN)
    status_documents = (
        _read("README.md"),
        _read("AGENTS.md"),
        _read("docs/spec/pietto-v0.9.md"),
    )

    assert "**Slice 6: MySQL Expression And Relation Rendering MVP is complete.**" in (
        plan
    )
    assert "6. **MySQL Expression And Relation Rendering MVP**: complete." in plan
    for document in status_documents:
        normalized = " ".join(document.split())
        assert "Slices 1 through 6 complete" in normalized
        assert "private handwritten MySQL" in normalized


def test_mysql_renderer_modules_are_private_and_closed() -> None:
    signature = inspect.signature(emit_mysql_sql)

    assert tuple(signature.parameters) == ("script_ir",)
    assert signature.return_annotation == "SqlResult"
    assert set(sql_api.__all__) == {
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    }
    for name in (
        "emit_mysql_sql",
        "render_mysql_expression",
        "render_mysql_relation",
        "quote_identifier",
        "render_literal",
        "MySqlRenderError",
        "emit_sql",
    ):
        assert not hasattr(sql_api, name)


def test_mysql_backend_catches_only_the_explicit_renderer_error() -> None:
    source = inspect.getsource(mysql_module.emit_mysql_sql)

    assert "except MySqlRenderError as error:" in source
    assert "except (TypeError, ValueError)" not in source
    assert "except Exception" not in source


def test_mysql_renderer_is_not_cli_enabled() -> None:
    cli_source = _read("src/pietto/cli.py")

    assert "pietto.sql.mysql" not in cli_source
    assert "emit_mysql_sql" not in cli_source
    assert 'choices=("postgres",)' in cli_source
    assert 'if dialect != "postgres":' in cli_source
    assert cli.main(["emit-sql", "missing.pietto", "--dialect", "mysql"]) == 2


def test_mysql_renderer_has_no_sqlglot_or_runtime_dependencies() -> None:
    project = tomllib.loads(_read("pyproject.toml"))
    source = "\n".join(
        inspect.getsource(module)
        for module in (
            mysql_module,
            expression_module,
            relation_module,
            render_module,
        )
    ).lower()

    assert project["project"]["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
    assert "sqlglot" not in _read("pyproject.toml").lower()
    assert 'name = "sqlglot"' not in _read("uv.lock")
    for forbidden in (
        "pietto.parser",
        "pietto.semantic",
        "pietto.ir.builder",
        "pietto.ir.lowering",
        "pietto.cli",
        "subprocess",
        "socket",
        "sqlalchemy",
        "requests",
    ):
        assert forbidden not in source


def test_slice6_does_not_add_generic_or_public_dispatch() -> None:
    runtime_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (REPO_ROOT / "src" / "pietto").rglob("*.py")
        if "generated" not in path.parts
    ).lower()

    for forbidden in (
        "def emit_sql(",
        "_select_sql_emitter",
        "_enabled_sql_dialects",
        "schema_version = 2",
        '"schema_version": 2',
    ):
        assert forbidden not in runtime_source


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")
