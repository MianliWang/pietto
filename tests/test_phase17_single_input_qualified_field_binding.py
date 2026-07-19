from __future__ import annotations

import hashlib
from pathlib import Path
from typing import cast

import pytest

from pietto.ast_nodes import (
    ComparisonExpr,
    DottedNameExpr,
    QueryDef,
    Script,
    SourceDef,
    TableDef,
)
from pietto.errors import Diagnostic, Severity
from pietto.ir import (
    ComparisonIR,
    FieldId,
    FieldRefIR,
    RelationIR,
    ScriptIR,
    SourceIR,
    SymbolId,
    SymbolNamespace,
    build_ir,
)
from pietto.parser_api import parse_source
from pietto.semantic import EffectiveNullability, SemanticResult, TypeKind, analyze
from pietto.sql import emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

REPO_ROOT = Path(__file__).resolve().parents[1]
GRAMMAR_HASH = "1c394db1f72561022941e0e937899e2d340880de220ebfa85cf387b86573384e"
GENERATED_HASH = "bc5be46411f947c4d591e81ce8dd8345140fd5e10276f2ff0055eccfc12babe4"


def test_qualified_projection_resolves_type_and_field_identity() -> None:
    script, semantic, script_ir = _compile(_source("postgres.table", "public.users"))
    relation_ast = cast(TableDef, script.definitions[-1])
    expression = cast(DottedNameExpr, relation_ast.select_items[0].expression)

    value_type = semantic.model.expression_value_types[expression]
    assert value_type.resolved_type.name == "Text"
    assert value_type.resolved_type.kind is TypeKind.BUILTIN
    assert value_type.nullability is EffectiveNullability.NULLABLE

    row_schema = semantic.model.relation_row_schemas[relation_ast]
    assert list(row_schema.fields) == ["email"]
    assert row_schema.fields["email"].resolved_type.name == "Text"
    assert row_schema.fields["email"].nullability is EffectiveNullability.NULLABLE

    relation_ir = _relation_ir(script_ir)
    field = cast(FieldRefIR, relation_ir.projections[0].expression)
    assert field.qualifier == ("users",)
    assert field.name == "email"
    assert field.field == FieldId(
        owner=SymbolId(SymbolNamespace.RELATION, "users"),
        name="email",
    )
    assert field.value_type.canonical_name == "Text"
    assert field.value_type.nullability.value == "nullable"


def test_aliased_qualified_projection_preserves_output_schema_type() -> None:
    source = (
        _source_prefix("postgres.table", "public.users") + "table selected:\n"
        "    from users\n"
        "    select:\n"
        "        email = users.email\n"
    )
    script, semantic, script_ir = _compile(source)
    relation_ast = cast(TableDef, script.definitions[-1])

    row_schema = semantic.model.relation_row_schemas[relation_ast]
    assert list(row_schema.fields) == ["email"]
    assert row_schema.fields["email"].resolved_type.name == "Text"
    assert row_schema.fields["email"].nullability is EffectiveNullability.NULLABLE

    relation_ir = _relation_ir(script_ir)
    assert relation_ir.projections[0].name == "email"
    field = cast(FieldRefIR, relation_ir.projections[0].expression)
    assert field.field == FieldId(
        owner=SymbolId(SymbolNamespace.RELATION, "users"),
        name="email",
    )


def test_downstream_relation_reads_unaliased_qualified_projection_schema() -> None:
    source = (
        _source_prefix("postgres.table", "public.users") + "table user_emails:\n"
        "    from users\n"
        "    select:\n"
        "        users.email\n"
        "table normalized:\n"
        "    from user_emails\n"
        "    select:\n"
        "        email\n"
    )
    script, semantic, script_ir = _compile(source)
    user_emails_ast = cast(TableDef, script.definitions[-2])
    normalized_ast = cast(TableDef, script.definitions[-1])

    user_emails_schema = semantic.model.relation_row_schemas[user_emails_ast]
    normalized_schema = semantic.model.relation_row_schemas[normalized_ast]
    assert list(user_emails_schema.fields) == ["email"]
    assert list(normalized_schema.fields) == ["email"]
    assert user_emails_schema.fields["email"].resolved_type.name == "Text"
    assert normalized_schema.fields["email"].resolved_type.name == "Text"
    assert normalized_schema.fields["email"].nullability is (
        EffectiveNullability.NULLABLE
    )

    normalized_ir = _relation_ir_by_name(script_ir, "normalized")
    field = cast(FieldRefIR, normalized_ir.projections[0].expression)
    assert field.field == FieldId(
        owner=SymbolId(SymbolNamespace.RELATION, "user_emails"),
        name="email",
    )


def test_qualified_fields_bind_in_where_and_input_scope_ordering() -> None:
    source = (
        _source_prefix("postgres.table", "public.users") + "query selected:\n"
        "    from users\n"
        "    where users.active == true\n"
        "    select:\n"
        "        users.email\n"
        "    order by:\n"
        "        users.email desc\n"
    )
    script, semantic, script_ir = _compile(source)
    relation_ast = cast(QueryDef, script.definitions[-1])
    assert relation_ast.where_clause is not None
    predicate = cast(ComparisonExpr, relation_ast.where_clause.expression)
    where_field = cast(DottedNameExpr, predicate.left)
    assert relation_ast.order_by_clause is not None
    order_field = cast(
        DottedNameExpr,
        relation_ast.order_by_clause.items[0].expression,
    )

    assert semantic.model.expression_value_types[where_field].resolved_type.name == (
        "Bool"
    )
    assert semantic.model.expression_value_types[order_field].resolved_type.name == (
        "Text"
    )

    relation_ir = _relation_ir(script_ir)
    assert relation_ir.filter is not None
    filter_ir = cast(ComparisonIR, relation_ir.filter.expression)
    assert cast(FieldRefIR, filter_ir.left).field == FieldId(
        owner=relation_ir.source.target,
        name="active",
    )
    assert cast(FieldRefIR, relation_ir.order_by[0].expression).field == FieldId(
        owner=relation_ir.source.target,
        name="email",
    )


@pytest.mark.parametrize(
    ("reference", "message"),
    [
        ("orders.email", "Unknown field: orders.email"),
        ("users.missing_field", "Unknown field: users.missing_field"),
        ("users.profile.email", "Unknown field: users.profile.email"),
    ],
)
def test_invalid_qualified_references_fail_closed_with_exact_span(
    reference: str,
    message: str,
) -> None:
    parse_result = parse_source(
        _source_prefix("postgres.table", "public.users") + "table selected:\n"
        "    from users\n"
        "    select:\n"
        f"        {reference}\n",
        path="qualified.pietto",
    )
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None
    relation = cast(TableDef, parse_result.ast.definitions[-1])
    expression = cast(DottedNameExpr, relation.select_items[0].expression)

    semantic = analyze(parse_result.ast)
    errors = [
        diagnostic
        for diagnostic in semantic.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]

    assert [(diagnostic.code, diagnostic.message) for diagnostic in errors] == [
        ("PIE-S2102", message)
    ]
    _assert_diagnostic_span(errors[0], expression)


def test_existing_relation_name_that_is_not_input_fails_as_qualifier() -> None:
    source = (
        _source_prefix("postgres.table", "public.users")
        + 'source orders: User is postgres.table("public.orders")\n'
        "table selected:\n"
        "    from users\n"
        "    select:\n"
        "        orders.email\n"
    )
    parse_result = parse_source(source, path="qualified.pietto")
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic = analyze(parse_result.ast)

    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic.diagnostics
        if diagnostic.severity is Severity.ERROR
    ] == [("PIE-S2102", "Unknown field: orders.email")]


def test_connector_dotted_call_remains_static_connector_metadata() -> None:
    script, semantic, script_ir = _compile(_source("postgres.table", "public.users"))
    source_ast = cast(SourceDef, script.definitions[1])
    source_ir = cast(SourceIR, script_ir.definitions[1])

    assert semantic.diagnostics == ()
    assert source_ast.connector not in semantic.model.expression_value_types
    assert source_ir.connector.name == "postgres.table"
    assert source_ir.connector.arguments == ("public.users",)


def test_dotted_function_call_remains_call_not_qualified_field() -> None:
    parse_result = parse_source(
        _source_prefix("postgres.table", "public.users") + "table selected:\n"
        "    from users\n"
        "    select:\n"
        "        email_call = users.email()\n"
    )
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic = analyze(parse_result.ast)

    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic.diagnostics
        if diagnostic.severity is Severity.ERROR
    ] == [("PIE-S2103", "Unknown function: users.email")]


def test_projection_alias_does_not_enter_order_by_input_scope() -> None:
    parse_result = parse_source(
        _source_prefix("postgres.table", "public.users") + "table selected:\n"
        "    from users\n"
        "    select:\n"
        "        sort_key = users.email\n"
        "    order by:\n"
        "        sort_key\n"
    )
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic = analyze(parse_result.ast)

    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic.diagnostics
        if diagnostic.severity is Severity.ERROR
    ] == [("PIE-S2102", "Unknown field: sort_key")]


def test_relationship_metadata_does_not_participate_in_qualified_lookup() -> None:
    source = (
        _source_prefix("postgres.table", "public.users") + "relationship membership:\n"
        "    endpoint member: users\n"
        "    endpoint group: users\n"
        "table selected:\n"
        "    from users\n"
        "    select:\n"
        "        users.email\n"
    )
    _, semantic, script_ir = _compile(source)

    assert len(semantic.model.relationships) == 1
    field = cast(FieldRefIR, _relation_ir(script_ir).projections[0].expression)
    assert field.field == FieldId(
        owner=SymbolId(SymbolNamespace.RELATION, "users"),
        name="email",
    )


def test_postgres_qualified_sql_uses_narrow_logical_input_alias() -> None:
    _, _, script_ir = _compile(
        _source("postgres.table", "public.users", include_where_order=True)
    )

    result = emit_postgres_sql(script_ir)

    assert result.diagnostics == ()
    assert result.artifacts[0].sql == (
        "SELECT\n"
        '    "users"."email" AS "email"\n'
        'FROM "public.users" AS "users"\n'
        'WHERE "users"."active" = TRUE\n'
        "ORDER BY\n"
        '    "users"."email" DESC'
    )


def test_mysql_qualified_sql_uses_narrow_logical_input_alias() -> None:
    _, _, script_ir = _compile(
        _source("mysql.table", "app_users", include_where_order=True)
    )

    result = emit_mysql_sql(script_ir)

    assert result.diagnostics == ()
    assert result.artifacts[0].sql == (
        "SELECT\n"
        "    `users`.`email` AS `email`\n"
        "FROM `app_users` AS `users`\n"
        "WHERE `users`.`active` = TRUE\n"
        "ORDER BY\n"
        "    `users`.`email` DESC"
    )


def test_unqualified_sql_keeps_existing_from_bytes() -> None:
    source = (
        _source_prefix("postgres.table", "public.users") + "table selected:\n"
        "    from users\n"
        "    select:\n"
        "        email\n"
    )
    _, _, script_ir = _compile(source)

    result = emit_postgres_sql(script_ir)

    assert result.diagnostics == ()
    assert result.artifacts[0].sql == (
        'SELECT\n    "email" AS "email"\nFROM "public.users"'
    )


def test_unqualified_mysql_sql_keeps_existing_from_bytes() -> None:
    source = (
        _source_prefix("mysql.table", "app_users") + "table selected:\n"
        "    from users\n"
        "    select:\n"
        "        email\n"
    )
    _, _, script_ir = _compile(source)

    result = emit_mysql_sql(script_ir)

    assert result.diagnostics == ()
    assert result.artifacts[0].sql == (
        "SELECT\n    `email` AS `email`\nFROM `app_users`"
    )


def test_phase17_changes_no_grammar_or_generated_antlr() -> None:
    assert _sha256(REPO_ROOT / "grammar/Pietto.g4") == GRAMMAR_HASH
    generated = tuple(
        path
        for path in sorted((REPO_ROOT / "src/pietto/generated").iterdir())
        if path.is_file()
    )
    assert _aggregate_sha256(generated) == GENERATED_HASH


def _source(
    connector: str,
    physical_name: str,
    *,
    include_where_order: bool = False,
) -> str:
    body = "table selected:\n    from users\n"
    if include_where_order:
        body += "    where users.active == true\n"
    body += "    select:\n        users.email\n"
    if include_where_order:
        body += "    order by:\n        users.email desc\n"
    return _source_prefix(connector, physical_name) + body


def _source_prefix(connector: str, physical_name: str) -> str:
    return (
        "shape User:\n"
        "    email: Text nullable\n"
        "    active: Bool not null\n"
        f'source users: User is {connector}("{physical_name}")\n'
    )


def _compile(source: str) -> tuple[Script, SemanticResult, ScriptIR]:
    parse_result = parse_source(source, path="qualified.pietto")
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic = analyze(parse_result.ast)
    assert all(
        diagnostic.severity is not Severity.ERROR for diagnostic in semantic.diagnostics
    )
    ir_result = build_ir(parse_result.ast, semantic.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return parse_result.ast, semantic, ir_result.ir


def _relation_ir(script_ir: ScriptIR) -> RelationIR:
    return next(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR)
    )


def _relation_ir_by_name(script_ir: ScriptIR, name: str) -> RelationIR:
    return next(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR) and definition.name == name
    )


def _assert_diagnostic_span(
    diagnostic: Diagnostic,
    expression: DottedNameExpr,
) -> None:
    assert diagnostic.location.path == expression.span.path
    assert diagnostic.location.line == expression.span.line
    assert diagnostic.location.column == expression.span.column
    assert diagnostic.location.end_line == expression.span.end_line
    assert diagnostic.location.end_column == expression.span.end_column


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _aggregate_sha256(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        relative = path.relative_to(REPO_ROOT).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()
