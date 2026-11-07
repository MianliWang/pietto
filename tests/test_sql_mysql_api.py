from __future__ import annotations

import inspect
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

import pietto.cli as cli
import pietto.ir as ir_api
import pietto.parser_api as parser_api
import pietto.semantic as semantic_api
import pietto.sql as sql_api
import pietto.sql.mysql as mysql_module
import pietto.sql.mysql_expressions as expression_module
import pietto.sql.mysql_relations as relation_module
import pietto.sql.mysql_render as render_module
from pietto.errors import Severity
from pietto.ir import DefinitionIR, RelationIR, ScriptIR, SourceSpan, build_ir
from pietto.sql import SqlResult
from pietto.sql.mysql import emit_mysql_sql

REPO_ROOT = Path(__file__).resolve().parents[1]

METADATA_SOURCE = (
    "type Email = Text\n"
    "enum Status:\n"
    "    active\n"
    "constraint valid_email(email: Text) -> Bool:\n"
    "    return email is not None\n"
    "derive normalize_email(email: Text) -> Text:\n"
    "    return trim(email)\n"
    "shape User:\n"
    "    email: Email\n"
    'source users: User = mysql.table("users")\n'
)
RELATION_SOURCE = (
    METADATA_SOURCE + "table first:\n"
    "    from users\n"
    "    select:\n"
    "        email\n"
    "query second:\n"
    "    from first\n"
    "    select:\n"
    "        email\n"
)


@dataclass(frozen=True, slots=True)
class FutureDefinitionIR(DefinitionIR):
    """Test-only future definition with standard diagnostic metadata."""

    name: str
    span: SourceSpan


def test_mysql_backend_is_private_and_script_ir_only() -> None:
    signature = inspect.signature(emit_mysql_sql)

    assert tuple(signature.parameters) == ("script_ir",)
    assert signature.return_annotation == "SqlResult"
    assert set(sql_api.__all__) == {
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    }
    assert "emit_mysql_sql" not in sql_api.__all__
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


def test_empty_script_ir_returns_empty_success() -> None:
    result = emit_mysql_sql(ScriptIR(definitions=()))

    assert result == SqlResult(artifacts=(), diagnostics=())
    assert result == SqlResult((), ())
    assert isinstance(result.artifacts, tuple)
    assert isinstance(result.diagnostics, tuple)


def test_all_current_metadata_definitions_are_non_emitting() -> None:
    script_ir = _compile_ir(METADATA_SOURCE)

    assert [type(definition).__name__ for definition in script_ir.definitions] == [
        "TypeIR",
        "EnumIR",
        "ConstraintIR",
        "DeriveIR",
        "ShapeIR",
        "SourceIR",
    ]
    assert emit_mysql_sql(script_ir) == SqlResult(artifacts=(), diagnostics=())


def test_relations_render_in_definition_order() -> None:
    result = emit_mysql_sql(_compile_ir(RELATION_SOURCE))

    assert [artifact.name for artifact in result.artifacts] == [
        "first",
        "second",
    ]
    assert result.artifacts[0].sql.endswith("FROM `users`")
    assert result.artifacts[1].sql.endswith("FROM `first`")
    assert result.diagnostics == ()


def test_unknown_definition_fails_closed_at_its_span() -> None:
    definition = FutureDefinitionIR(
        name="future_target",
        span=SourceSpan(
            path="future-mysql.pietto",
            line=7,
            column=3,
            end_line=7,
            end_column=16,
        ),
    )

    result = emit_mysql_sql(ScriptIR(definitions=(definition,)))

    assert result.artifacts == ()
    assert len(result.diagnostics) == 1
    diagnostic = result.diagnostics[0]
    assert diagnostic.code == "PIE-B1000"
    assert diagnostic.severity is Severity.ERROR
    assert diagnostic.message == (
        "MySQL SQL emission is not implemented for FutureDefinitionIR: future_target"
    )
    assert (
        diagnostic.location.path,
        diagnostic.location.line,
        diagnostic.location.column,
        diagnostic.location.end_line,
        diagnostic.location.end_column,
    ) == ("future-mysql.pietto", 7, 3, 7, 16)


def test_diagnostics_preserve_definition_order_around_metadata() -> None:
    script_ir = _compile_ir(RELATION_SOURCE)
    relations = tuple(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR)
    )
    metadata = tuple(
        definition
        for definition in script_ir.definitions
        if not isinstance(definition, RelationIR)
    )
    future = FutureDefinitionIR(
        name="future_middle",
        span=SourceSpan(
            path="ordered-mysql.pietto",
            line=20,
            column=1,
            end_line=20,
            end_column=14,
        ),
    )
    ordered_ir = ScriptIR(
        definitions=(
            metadata[0],
            relations[1],
            metadata[1],
            future,
            *metadata[2:],
            relations[0],
        )
    )

    result = emit_mysql_sql(ordered_ir)

    assert [artifact.name for artifact in result.artifacts] == ["second", "first"]
    assert [
        diagnostic.message.split(": ", maxsplit=1)[1].split(".", 1)[0]
        for diagnostic in result.diagnostics
    ] == [
        "future_middle",
    ]


def test_mysql_backend_does_not_run_frontend_or_ir_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script_ir = _compile_ir(RELATION_SOURCE)

    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("MySQL backend must consume ScriptIR directly")

    monkeypatch.setattr(parser_api, "parse_source", unexpected_call)
    monkeypatch.setattr(semantic_api, "analyze", unexpected_call)
    monkeypatch.setattr(ir_api, "build_ir", unexpected_call)

    result = emit_mysql_sql(script_ir)

    assert [artifact.name for artifact in result.artifacts] == ["first", "second"]
    assert result.diagnostics == ()


def test_mysql_backend_has_closed_definition_classification() -> None:
    assert mysql_module._EMITTING_DEFINITION_TYPES == (RelationIR,)
    assert {
        definition_type.__name__
        for definition_type in mysql_module._NON_EMITTING_DEFINITION_TYPES
    } == {
        "TypeIR",
        "EnumIR",
        "ShapeIR",
        "SourceIR",
        "ConstraintIR",
        "DeriveIR",
    }


def test_mysql_backend_catches_only_the_explicit_renderer_error() -> None:
    source = inspect.getsource(mysql_module.emit_mysql_sql)

    assert "except MySqlRenderError as error:" in source
    assert "except (TypeError, ValueError)" not in source
    assert "except Exception" not in source


def test_mysql_backend_is_cli_dispatched_without_public_export() -> None:
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
    assert "def _select_sql_emitter(" in runtime_source
    assert cli.main(["emit-sql", "missing.pietto", "--dialect", "sqlite"]) == 2


def test_mysql_backend_has_no_sqlglot_runtime_or_forbidden_stage_imports() -> None:
    mysql_source = _read("src/pietto/sql/mysql.py").lower()
    source = "\n".join(
        inspect.getsource(module)
        for module in (
            mysql_module,
            expression_module,
            relation_module,
            render_module,
        )
    ).lower()

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


def test_runtime_has_no_generic_or_public_emit_sql_dispatch() -> None:
    runtime_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (REPO_ROOT / "src" / "pietto").rglob("*.py")
        if "generated" not in path.parts
    ).lower()

    for forbidden in ("def emit_sql(", '"schema_version": 2'):
        assert forbidden not in runtime_source
    # An assignment, not prose: PIE-S2334 tells a schema_version = 1 project
    # to set `schema_version = 2` in its pietto.toml.
    assert not re.search(r"^\s*[\w.]*schema_version = 2", runtime_source, re.M)


def _compile_ir(source: str) -> ScriptIR:
    parse_result = parser_api.parse_source(source, path="mysql-api.pietto")
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = semantic_api.analyze(parse_result.ast)
    assert all(
        diagnostic.severity is not Severity.ERROR
        for diagnostic in semantic_result.diagnostics
    )
    ir_result = build_ir(parse_result.ast, semantic_result.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return ir_result.ir


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")
