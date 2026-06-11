from __future__ import annotations

from dataclasses import fields

from pietto.ast_nodes import Script, SourceDef
from pietto.errors import Severity
from pietto.ir import ConnectorIR, SourceIR, build_ir
from pietto.parser_api import parse_source
from pietto.semantic import analyze

SHAPE = "shape User:\n    id: UUID not null\n    email: Text not null\n"


def test_mysql_connector_name_argument_and_span_are_preserved() -> None:
    script, source_ir = _lower_source(
        SHAPE + 'source users: User is mysql.table("app.users")\n',
        path="mysql-source.pietto",
    )
    source_ast = script.definitions[-1]
    assert isinstance(source_ast, SourceDef)

    assert source_ir.connector == ConnectorIR(
        name="mysql.table",
        arguments=("app.users",),
        span=source_ir.connector.span,
    )
    assert source_ir.connector.arguments[0] == "app.users"
    assert source_ir.connector.span.path == "mysql-source.pietto"
    assert (
        source_ir.connector.span.line,
        source_ir.connector.span.column,
        source_ir.connector.span.end_line,
        source_ir.connector.span.end_column,
    ) == (
        source_ast.connector.span.line,
        source_ast.connector.span.column,
        source_ast.connector.span.end_line,
        source_ast.connector.span.end_column,
    )


def test_mysql_and_postgres_sources_preserve_definition_order() -> None:
    source = (
        SHAPE
        + 'source mysql_users: User is mysql.table("app.users")\n'
        + 'source postgres_users: User is postgres.table("public.users")\n'
    )
    parse_result = parse_source(source, path="ordered-sources.pietto")
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None
    semantic_result = analyze(parse_result.ast)
    assert semantic_result.diagnostics == ()

    ir_result = build_ir(parse_result.ast, semantic_result.model)

    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    sources = tuple(
        definition
        for definition in ir_result.ir.definitions
        if isinstance(definition, SourceIR)
    )
    assert [
        (source_ir.name, source_ir.connector.name, source_ir.connector.arguments)
        for source_ir in sources
    ] == [
        ("mysql_users", "mysql.table", ("app.users",)),
        ("postgres_users", "postgres.table", ("public.users",)),
    ]


def test_connector_ir_contains_static_metadata_only() -> None:
    _, source_ir = _lower_source(SHAPE + 'source users: User is mysql.table("users")\n')

    assert [field.name for field in fields(source_ir.connector)] == [
        "name",
        "arguments",
        "span",
    ]
    assert [field.name for field in fields(source_ir)] == [
        "symbol",
        "name",
        "shape_symbol",
        "row_schema",
        "connector",
        "span",
    ]
    assert source_ir.connector.arguments == ("users",)
    assert all(
        forbidden not in repr(source_ir).lower()
        for forbidden in (
            "credential",
            "database connection",
            "dialect object",
            "endpoint",
            "runtime handle",
        )
    )


def test_postgres_connector_ir_behavior_is_unchanged() -> None:
    _, source_ir = _lower_source(
        SHAPE + 'source users: User is postgres.table("public.users")\n'
    )

    assert source_ir.connector == ConnectorIR(
        name="postgres.table",
        arguments=("public.users",),
        span=source_ir.connector.span,
    )


def _lower_source(
    source: str,
    *,
    path: str | None = None,
) -> tuple[Script, SourceIR]:
    parse_result = parse_source(source, path=path)
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
    source_ir = next(
        definition
        for definition in ir_result.ir.definitions
        if isinstance(definition, SourceIR)
    )
    return parse_result.ast, source_ir
