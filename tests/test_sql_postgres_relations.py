from __future__ import annotations

import inspect
from dataclasses import replace

import pytest

import pietto.ir as ir_api
import pietto.parser_api as parser_api
import pietto.semantic as semantic_api
import pietto.sql.postgres as postgres_module
import pietto.sql.relations as relation_module
from pietto.errors import Severity
from pietto.ir import (
    CallIR,
    ComparisonIR,
    LiteralIR,
    RelationIR,
    ScriptIR,
    SourceIR,
    build_ir,
)
from pietto.sql import SqlArtifactKind, emit_postgres_sql
from pietto.sql.relations import render_relation_sql

SOURCE = (
    "shape User:\n"
    "    email: Text nullable\n"
    "    deleted_at: Timestamp nullable\n"
    'source users: User is postgres.table("public.users")\n'
)


def test_source_backed_relation_emits_select_from_where_and_projections() -> None:
    script_ir = _compile(
        SOURCE + "table active_users:\n"
        "    from users\n"
        "    where deleted_at is null\n"
        "    select:\n"
        "        email\n"
        "        email_norm = lower(trim(email))\n"
    )

    result = emit_postgres_sql(script_ir)

    assert len(result.artifacts) == 1
    artifact = result.artifacts[0]
    assert artifact.name == "active_users"
    assert artifact.kind is SqlArtifactKind.RELATION
    assert artifact.sql == (
        "SELECT\n"
        '    "email" AS "email",\n'
        '    lower(trim("email")) AS "email_norm"\n'
        'FROM "public.users"\n'
        'WHERE "deleted_at" IS NULL'
    )
    assert result.diagnostics == ()


def test_relation_without_filter_omits_where() -> None:
    script_ir = _compile(
        SOURCE + "query user_emails:\n    from users\n    select:\n        email\n"
    )

    result = emit_postgres_sql(script_ir)

    assert len(result.artifacts) == 1
    assert result.artifacts[0].sql == (
        'SELECT\n    "email" AS "email"\nFROM "public.users"'
    )
    assert "WHERE" not in result.artifacts[0].sql


def test_relation_renderer_uses_source_symbol_mapping() -> None:
    script_ir = _compile(
        SOURCE + "table user_emails:\n    from users\n    select:\n        email\n"
    )
    source = _definition(script_ir, SourceIR, "users")
    relation = _definition(script_ir, RelationIR, "user_emails")

    assert render_relation_sql(
        relation,
        sources={source.symbol: source},
        relations={relation.symbol: relation},
    ).endswith('FROM "public.users"')


def test_source_backed_relation_artifacts_preserve_definition_order() -> None:
    script_ir = _compile(
        SOURCE + "table first:\n"
        "    from users\n"
        "    select:\n"
        "        email\n"
        "query second:\n"
        "    from users\n"
        "    select:\n"
        "        email\n"
    )

    result = emit_postgres_sql(script_ir)

    assert [artifact.name for artifact in result.artifacts] == ["first", "second"]


def test_relation_to_relation_input_uses_quoted_relation_name() -> None:
    script_ir = _compile(
        SOURCE + "table active_users:\n"
        "    from users\n"
        "    select:\n"
        "        email\n"
        "query active_user_emails:\n"
        "    from active_users\n"
        "    select:\n"
        "        email\n"
    )

    result = emit_postgres_sql(script_ir)

    assert [artifact.name for artifact in result.artifacts] == [
        "active_users",
        "active_user_emails",
    ]
    assert result.artifacts[1].sql.endswith('FROM "active_users"')


def test_unsupported_source_connector_reports_pie_b1000_without_crashing() -> None:
    script_ir = _compile(
        SOURCE + "table user_emails:\n    from users\n    select:\n        email\n"
    )
    source = _definition(script_ir, SourceIR, "users")
    bad_source = replace(
        source,
        connector=replace(source.connector, name="unsupported.table"),
    )
    definitions = tuple(
        bad_source if definition is source else definition
        for definition in script_ir.definitions
    )

    result = emit_postgres_sql(ScriptIR(definitions=definitions))

    assert result.artifacts == ()
    relation_diagnostic = next(
        diagnostic
        for diagnostic in result.diagnostics
        if "user_emails" in diagnostic.message
    )
    assert relation_diagnostic.code == "PIE-B1000"
    assert "postgres.table(Text)" in relation_diagnostic.message


def test_nul_in_source_table_name_reports_pie_b1000() -> None:
    script_ir = _compile(
        SOURCE + "table user_emails:\n    from users\n    select:\n        email\n"
    )
    source = _definition(script_ir, SourceIR, "users")
    bad_source = replace(
        source,
        connector=replace(source.connector, arguments=("public.\x00users",)),
    )
    definitions = tuple(
        bad_source if definition is source else definition
        for definition in script_ir.definitions
    )

    result = emit_postgres_sql(ScriptIR(definitions=definitions))

    assert result.artifacts == ()
    assert len(result.diagnostics) == 1
    diagnostic = result.diagnostics[0]
    assert diagnostic.code == "PIE-B1000"
    assert "identifiers must not contain NUL" in diagnostic.message
    assert "\x00" not in diagnostic.message


def test_nul_in_relation_literal_reports_pie_b1000() -> None:
    script_ir = _compile(
        SOURCE + "table matching_users:\n"
        "    from users\n"
        '    where email == "safe"\n'
        "    select:\n"
        "        email\n"
    )
    relation = _definition(script_ir, RelationIR, "matching_users")
    assert relation.filter is not None
    expression = relation.filter.expression
    assert isinstance(expression, ComparisonIR)
    assert isinstance(expression.right, LiteralIR)
    bad_relation = replace(
        relation,
        filter=replace(
            relation.filter,
            expression=replace(
                expression,
                right=replace(expression.right, value="bad\x00value"),
            ),
        ),
    )
    definitions = tuple(
        bad_relation if definition is relation else definition
        for definition in script_ir.definitions
    )

    result = emit_postgres_sql(ScriptIR(definitions=definitions))

    assert result.artifacts == ()
    assert len(result.diagnostics) == 1
    diagnostic = result.diagnostics[0]
    assert diagnostic.code == "PIE-B1000"
    assert "string literals must not contain NUL" in diagnostic.message
    assert "\x00" not in diagnostic.message


def test_unsupported_projection_expression_becomes_pie_b1000() -> None:
    script_ir = _compile(
        SOURCE + "table user_emails:\n"
        "    from users\n"
        "    select:\n"
        "        normalized = lower(email)\n"
    )
    relation = _definition(script_ir, RelationIR, "user_emails")
    projection = relation.projections[0]
    assert isinstance(projection.expression, CallIR)
    bad_projection = replace(
        projection,
        expression=replace(projection.expression, callee="unsupported"),
    )
    bad_relation = replace(relation, projections=(bad_projection,))
    definitions = tuple(
        bad_relation if definition is relation else definition
        for definition in script_ir.definitions
    )

    result = emit_postgres_sql(ScriptIR(definitions=definitions))

    assert result.artifacts == ()
    relation_diagnostic = next(
        diagnostic
        for diagnostic in result.diagnostics
        if "user_emails" in diagnostic.message
    )
    assert relation_diagnostic.code == "PIE-B1000"
    assert "Unsupported PostgreSQL function call" in relation_diagnostic.message


def test_metadata_definitions_are_non_emitting_without_diagnostics() -> None:
    script_ir = _compile(
        SOURCE + "table user_emails:\n    from users\n    select:\n        email\n"
    )

    result = emit_postgres_sql(script_ir)

    assert [artifact.name for artifact in result.artifacts] == ["user_emails"]
    assert result.diagnostics == ()


def test_relation_emitter_does_not_run_frontend_or_ir_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script_ir = _compile(
        SOURCE + "table user_emails:\n    from users\n    select:\n        email\n"
    )

    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("SQL emission must consume ScriptIR directly")

    monkeypatch.setattr(parser_api, "parse_source", unexpected_call)
    monkeypatch.setattr(semantic_api, "analyze", unexpected_call)
    monkeypatch.setattr(ir_api, "build_ir", unexpected_call)

    result = emit_postgres_sql(script_ir)

    assert [artifact.name for artifact in result.artifacts] == ["user_emails"]


def test_relation_sql_modules_have_no_runtime_or_sqlglot_dependencies() -> None:
    source = inspect.getsource(postgres_module) + inspect.getsource(relation_module)

    for dependency in (
        "antlr",
        "pietto.parser",
        "pietto.semantic",
        "pietto.ir.builder",
        "pietto.ir.lowering",
        "sqlglot",
        "database",
        "connector execution",
        "pietto.cli",
    ):
        assert dependency not in source
    assert not hasattr(ir_api, "compile_to_ir")


def _compile(source: str) -> ScriptIR:
    parse_result = parser_api.parse_source(source, path="postgres-relations.pietto")
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


def _definition(
    script_ir: ScriptIR,
    definition_type: type[SourceIR] | type[RelationIR],
    name: str,
) -> SourceIR | RelationIR:
    return next(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, definition_type) and definition.name == name
    )
