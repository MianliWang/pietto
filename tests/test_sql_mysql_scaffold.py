from __future__ import annotations

import inspect
from dataclasses import dataclass

import pytest

import pietto.ir as ir_api
import pietto.parser_api as parser_api
import pietto.semantic as semantic_api
import pietto.sql as sql_api
import pietto.sql.mysql as mysql_module
from pietto.errors import Severity
from pietto.ir import DefinitionIR, RelationIR, ScriptIR, SourceSpan, build_ir
from pietto.sql import SqlResult
from pietto.sql.mysql import emit_mysql_sql

METADATA_SOURCE = (
    "type Email = Text not null\n"
    "enum Status:\n"
    "    active\n"
    "constraint valid_email(email: Text not null) -> Bool not null:\n"
    "    email is not null\n"
    "derive normalize_email(email: Text not null) -> Text not null:\n"
    "    trim(email)\n"
    "shape User:\n"
    "    email: Email not null\n"
    'source users: User is mysql.table("users")\n'
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


def test_mysql_skeleton_boundary_is_private_and_script_ir_only() -> None:
    signature = inspect.signature(emit_mysql_sql)

    assert tuple(signature.parameters) == ("script_ir",)
    assert signature.return_annotation == "SqlResult"
    assert not hasattr(sql_api, "emit_mysql_sql")
    assert "emit_mysql_sql" not in sql_api.__all__


def test_empty_script_ir_returns_empty_success() -> None:
    result = emit_mysql_sql(ScriptIR(definitions=()))

    assert result == SqlResult(artifacts=(), diagnostics=())
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


def test_mysql_skeleton_does_not_run_frontend_or_ir_builder(
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


def test_mysql_skeleton_has_closed_definition_classification() -> None:
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


def _compile_ir(source: str) -> ScriptIR:
    parse_result = parser_api.parse_source(source, path="mysql-scaffold.pietto")
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
