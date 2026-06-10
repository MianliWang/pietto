from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

import pietto.ir as ir_api
import pietto.parser_api as parser_api
import pietto.semantic as semantic_api
import pietto.sql as sql_api
import pietto.sql.postgres as postgres_module
from pietto.errors import Severity
from pietto.ir import RelationIR, ScriptIR, build_ir
from pietto.sql import (
    SqlArtifact,
    SqlArtifactKind,
    SqlResult,
    emit_postgres_sql,
)


def test_public_sql_api_is_explicit() -> None:
    assert sql_api.__all__ == [
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    ]
    assert all(hasattr(sql_api, name) for name in sql_api.__all__)
    assert not hasattr(sql_api, "_unsupported_definition_diagnostic")


def test_empty_script_ir_returns_successful_empty_result() -> None:
    result = emit_postgres_sql(ScriptIR(definitions=()))

    assert result == SqlResult(artifacts=(), diagnostics=())
    assert isinstance(result.artifacts, tuple)
    assert isinstance(result.diagnostics, tuple)


def test_nonempty_script_ir_emits_supported_relations_and_diagnoses_rest() -> None:
    script_ir = _all_definition_ir()

    result = emit_postgres_sql(script_ir)

    assert [artifact.name for artifact in result.artifacts] == [
        "active_users",
        "active_user_emails",
    ]
    unsupported_definitions = [
        definition
        for definition in script_ir.definitions
        if not isinstance(definition, RelationIR)
    ]
    assert len(result.diagnostics) == len(unsupported_definitions)
    assert [
        (
            diagnostic.code,
            diagnostic.severity,
            type(definition).__name__,
            definition.name,
            diagnostic.location.path,
            diagnostic.location.line,
            diagnostic.location.column,
            diagnostic.location.end_line,
            diagnostic.location.end_column,
        )
        for diagnostic, definition in zip(
            result.diagnostics,
            unsupported_definitions,
            strict=True,
        )
    ] == [
        (
            "PIE-B1000",
            Severity.ERROR,
            type(definition).__name__,
            definition.name,
            definition.span.path,
            definition.span.line,
            definition.span.column,
            definition.span.end_line,
            definition.span.end_column,
        )
        for definition in unsupported_definitions
    ]
    for diagnostic, definition in zip(
        result.diagnostics,
        unsupported_definitions,
        strict=True,
    ):
        assert type(definition).__name__ in diagnostic.message
        assert definition.name in diagnostic.message


def test_sql_models_are_frozen_and_tuple_backed() -> None:
    artifact = SqlArtifact(
        name="active_users",
        kind=SqlArtifactKind.RELATION,
        sql="",
    )
    result = SqlResult(artifacts=(artifact,), diagnostics=())

    assert isinstance(result.artifacts, tuple)
    assert isinstance(result.diagnostics, tuple)
    with pytest.raises(FrozenInstanceError):
        artifact.sql = "SELECT 1"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.artifacts = ()  # type: ignore[misc]


def test_emitter_does_not_run_frontend_or_ir_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script_ir = _all_definition_ir()

    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("SQL emission must consume ScriptIR directly")

    monkeypatch.setattr(parser_api, "parse_source", unexpected_call)
    monkeypatch.setattr(semantic_api, "analyze", unexpected_call)
    monkeypatch.setattr(ir_api, "build_ir", unexpected_call)

    result = emit_postgres_sql(script_ir)

    assert [artifact.name for artifact in result.artifacts] == [
        "active_users",
        "active_user_emails",
    ]
    assert result.diagnostics


def test_emitter_has_no_sqlglot_or_ddl_emission() -> None:
    source = inspect.getsource(postgres_module)
    result = emit_postgres_sql(_all_definition_ir())

    assert "sqlglot" not in source
    assert [artifact.name for artifact in result.artifacts] == [
        "active_users",
        "active_user_emails",
    ]
    assert all(
        keyword not in artifact.sql.upper()
        for artifact in result.artifacts
        for keyword in ("CREATE", "ALTER", "DROP", "WITH")
    )
    assert not hasattr(ir_api, "compile_to_ir")


def test_pie_b1000_is_documented() -> None:
    documented = Path("docs/spec/diagnostics.md").read_text(encoding="utf-8")

    assert "`PIE-B1000`" in documented


def _all_definition_ir() -> ScriptIR:
    parse_result = parser_api.parse_source(
        "type Email = Text not null\n"
        "enum Status:\n"
        "    active\n"
        "constraint valid_email(email: Text not null) -> Bool not null:\n"
        "    email is not null\n"
        "derive normalize_email(email: Text not null) -> Text not null:\n"
        "    trim(email)\n"
        "shape User:\n"
        "    email: Text not null\n"
        'source users: User is postgres.table("public.users")\n'
        "table active_users:\n"
        "    from users\n"
        "    select:\n"
        "        email\n"
        "query active_user_emails:\n"
        "    from active_users\n"
        "    select:\n"
        "        email\n",
        path="postgres-scaffold.pie",
    )
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
