from __future__ import annotations

from dataclasses import replace

from pietto.errors import Severity
from pietto.ir import (
    RelationIR,
    ScriptIR,
    SourceIR,
    SymbolId,
    SymbolNamespace,
    build_ir,
)
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.sql import SqlArtifactKind, emit_postgres_sql

SOURCE = (
    "shape User:\n"
    "    id: UUID not null\n"
    "    email: Text nullable\n"
    "    active: Bool not null\n"
    'source users: User is postgres.table("users")\n'
)


def test_source_table_query_chain_emits_ordered_relation_artifacts() -> None:
    result = emit_postgres_sql(_chain_ir())

    assert [(artifact.name, artifact.kind) for artifact in result.artifacts] == [
        ("active_users", SqlArtifactKind.RELATION),
        ("active_user_emails", SqlArtifactKind.RELATION),
    ]
    assert result.artifacts[0].sql == (
        "SELECT\n"
        '    "id" AS "id",\n'
        '    "email" AS "email"\n'
        'FROM "users"\n'
        'WHERE "active" = TRUE'
    )
    assert result.artifacts[1].sql == (
        "SELECT\n"
        '    lower("email") AS "normalized_email"\n'
        'FROM "active_users"\n'
        'WHERE "email" IS NOT NULL'
    )


def test_relation_reference_is_not_inlined_or_expanded_as_cte() -> None:
    result = emit_postgres_sql(_chain_ir())
    downstream_sql = result.artifacts[1].sql

    assert downstream_sql.count("SELECT") == 1
    assert 'FROM "active_users"' in downstream_sql
    assert 'FROM "users"' not in downstream_sql
    assert "WITH" not in downstream_sql


def test_direct_source_backed_relation_behavior_is_unchanged() -> None:
    script_ir = _compile_ir(
        SOURCE + "table user_emails:\n    from users\n    select:\n        email\n"
    )

    result = emit_postgres_sql(script_ir)

    assert [artifact.name for artifact in result.artifacts] == ["user_emails"]
    assert result.artifacts[0].sql.endswith('FROM "users"')


def test_unresolved_relation_source_target_reports_pie_b1000() -> None:
    script_ir = _chain_ir()
    downstream = _relation(script_ir, "active_user_emails")
    unresolved = replace(
        downstream,
        source=replace(
            downstream.source,
            target=SymbolId(SymbolNamespace.RELATION, "missing_relation"),
        ),
    )
    definitions = tuple(
        unresolved if definition is downstream else definition
        for definition in script_ir.definitions
    )

    result = emit_postgres_sql(ScriptIR(definitions=definitions))

    assert [artifact.name for artifact in result.artifacts] == ["active_users"]
    diagnostic = next(
        item for item in result.diagnostics if "active_user_emails" in item.message
    )
    assert diagnostic.code == "PIE-B1000"
    assert diagnostic.severity is Severity.ERROR
    assert "does not resolve to SourceIR or RelationIR" in diagnostic.message


def test_bad_source_connector_still_reports_pie_b1000() -> None:
    script_ir = _compile_ir(
        SOURCE + "table user_emails:\n    from users\n    select:\n        email\n"
    )
    source = _source(script_ir, "users")
    invalid_source = replace(
        source,
        connector=replace(source.connector, name="unsupported.table"),
    )
    definitions = tuple(
        invalid_source if definition is source else definition
        for definition in script_ir.definitions
    )

    result = emit_postgres_sql(ScriptIR(definitions=definitions))

    assert result.artifacts == ()
    diagnostic = next(
        item for item in result.diagnostics if "user_emails" in item.message
    )
    assert diagnostic.code == "PIE-B1000"
    assert "postgres.table(Text)" in diagnostic.message


def _chain_ir() -> ScriptIR:
    return _compile_ir(
        SOURCE + "table active_users:\n"
        "    from users\n"
        "    where active == true\n"
        "    select:\n"
        "        id\n"
        "        email\n"
        "query active_user_emails:\n"
        "    from active_users\n"
        "    where email is not null\n"
        "    select:\n"
        "        normalized_email = lower(email)\n"
    )


def _compile_ir(source: str) -> ScriptIR:
    parse_result = parse_source(source, path="relation-dependencies.pie")
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    assert all(
        diagnostic.severity is not Severity.ERROR
        for diagnostic in semantic_result.diagnostics
    )
    ir_result = build_ir(parse_result.ast, semantic_result.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return ir_result.ir


def _relation(script_ir: ScriptIR, name: str) -> RelationIR:
    return next(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR) and definition.name == name
    )


def _source(script_ir: ScriptIR, name: str) -> SourceIR:
    return next(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, SourceIR) and definition.name == name
    )
