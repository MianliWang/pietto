from __future__ import annotations

import inspect
from dataclasses import replace
from typing import Callable

import pytest

import pietto.ir as ir_api
import pietto.parser_api as parser_api
import pietto.semantic as semantic_api
import pietto.sql.mysql as mysql_module
import pietto.sql.mysql_relations as relation_module
from pietto.errors import Severity
from pietto.ir import (
    CallIR,
    ComparisonIR,
    FieldRefIR,
    LiteralIR,
    RelationIR,
    ScriptIR,
    SourceIR,
    build_ir,
)
from pietto.sql import SqlArtifactKind
from pietto.sql.mysql import emit_mysql_sql

SOURCE = (
    "shape User:\n"
    "    email: Text nullable\n"
    "    age: Int not null\n"
    "    deleted_at: Timestamp nullable\n"
    'source users: User is mysql.table("app.users")\n'
)


def test_source_backed_relation_renders_approved_format() -> None:
    result = emit_mysql_sql(
        _compile(
            SOURCE + "table active_users:\n"
            "    from users\n"
            "    where deleted_at is null\n"
            "    select:\n"
            "        email\n"
            "        normalized = lower(trim(email))\n"
            "        email_length = len(email)\n"
        )
    )

    assert len(result.artifacts) == 1
    artifact = result.artifacts[0]
    assert artifact.name == "active_users"
    assert artifact.kind is SqlArtifactKind.RELATION
    assert artifact.sql == (
        "SELECT\n"
        "    `email` AS `email`,\n"
        "    LOWER(TRIM(`email`)) AS `normalized`,\n"
        "    CHAR_LENGTH(`email`) AS `email_length`\n"
        "FROM `app.users`\n"
        "WHERE `deleted_at` IS NULL"
    )
    assert result.diagnostics == ()


def test_relation_reference_and_artifact_order_are_stable() -> None:
    result = emit_mysql_sql(
        _compile(
            SOURCE + "table first:\n"
            "    from users\n"
            "    select:\n"
            "        email\n"
            "query second:\n"
            "    from first\n"
            "    select:\n"
            "        email\n"
        )
    )

    assert [artifact.name for artifact in result.artifacts] == ["first", "second"]
    assert result.artifacts[0].sql.endswith("FROM `app.users`")
    assert result.artifacts[1].sql.endswith("FROM `first`")
    assert result.diagnostics == ()


def test_physical_source_name_is_opaque_and_escapes_backticks() -> None:
    script_ir = _compile(
        SOURCE + "table selected:\n    from users\n    select:\n        email\n"
    )
    source = _definition(script_ir, SourceIR, "users")
    connector = replace(source.connector, arguments=("app.we`ird.users",))
    bad_source = replace(source, connector=connector)
    definitions = tuple(
        bad_source if definition is source else definition
        for definition in script_ir.definitions
    )

    result = emit_mysql_sql(ScriptIR(definitions=definitions))

    assert result.artifacts[0].sql.endswith("FROM `app.we``ird.users`")
    assert result.diagnostics == ()


def test_reserved_alias_is_backtick_quoted() -> None:
    script_ir = _compile(
        SOURCE + "table selected:\n    from users\n    select:\n        email\n"
    )
    relation = _definition(script_ir, RelationIR, "selected")
    projection = replace(relation.projections[0], name="order")
    bad_relation = replace(relation, projections=(projection,))
    definitions = tuple(
        bad_relation if definition is relation else definition
        for definition in script_ir.definitions
    )

    result = emit_mysql_sql(ScriptIR(definitions=definitions))

    assert result.artifacts[0].sql.startswith("SELECT\n    `email` AS `order`\n")


@pytest.mark.parametrize(
    "mutate",
    [
        lambda source: replace(
            source,
            connector=replace(source.connector, name="postgres.table"),
        ),
        lambda source: replace(
            source,
            connector=replace(source.connector, arguments=("",)),
        ),
        lambda source: replace(
            source,
            connector=replace(source.connector, arguments=("x" * 65,)),
        ),
        lambda source: replace(
            source,
            connector=replace(source.connector, arguments=("bad\x00name",)),
        ),
    ],
)
def test_unsupported_or_invalid_connectors_emit_no_partial_artifact(
    mutate: Callable[[SourceIR], SourceIR],
) -> None:
    script_ir = _compile(
        SOURCE + "table selected:\n    from users\n    select:\n        email\n"
    )
    source = _definition(script_ir, SourceIR, "users")
    bad_source = mutate(source)
    definitions = tuple(
        bad_source if definition is source else definition
        for definition in script_ir.definitions
    )

    result = emit_mysql_sql(ScriptIR(definitions=definitions))

    assert result.artifacts == ()
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code == "PIE-B1000"
    assert "selected" in result.diagnostics[0].message


def test_matches_relation_fails_closed_without_approximation() -> None:
    result = emit_mysql_sql(
        _compile(
            SOURCE + "table matching:\n"
            "    from users\n"
            '    where matches(email, "@")\n'
            "    select:\n"
            "        email\n"
        )
    )

    assert result.artifacts == ()
    assert len(result.diagnostics) == 1
    assert "Unsupported MySQL function call: matches" in (result.diagnostics[0].message)


def test_invalid_projection_expression_emits_no_partial_artifact() -> None:
    script_ir = _compile(
        SOURCE + "table selected:\n"
        "    from users\n"
        "    select:\n"
        "        normalized = lower(email)\n"
    )
    relation = _definition(script_ir, RelationIR, "selected")
    projection = relation.projections[0]
    assert isinstance(projection.expression, CallIR)
    bad_projection = replace(
        projection,
        expression=replace(projection.expression, callee="unknown"),
    )
    bad_relation = replace(relation, projections=(bad_projection,))
    definitions = tuple(
        bad_relation if definition is relation else definition
        for definition in script_ir.definitions
    )

    result = emit_mysql_sql(ScriptIR(definitions=definitions))

    assert result.artifacts == ()
    assert len(result.diagnostics) == 1
    assert "Unsupported MySQL function call: unknown" in (result.diagnostics[0].message)


def test_invalid_literal_emits_no_partial_artifact() -> None:
    script_ir = _compile(
        SOURCE + "table selected:\n"
        "    from users\n"
        '    where email == "safe"\n'
        "    select:\n"
        "        email\n"
    )
    relation = _definition(script_ir, RelationIR, "selected")
    assert relation.filter is not None
    expression = relation.filter.expression
    assert isinstance(expression, ComparisonIR)
    assert isinstance(expression.right, LiteralIR)
    bad_filter = replace(
        relation.filter,
        expression=replace(
            expression,
            right=replace(expression.right, value="bad\x00value"),
        ),
    )
    bad_relation = replace(relation, filter=bad_filter)
    definitions = tuple(
        bad_relation if definition is relation else definition
        for definition in script_ir.definitions
    )

    result = emit_mysql_sql(ScriptIR(definitions=definitions))

    assert result.artifacts == ()
    assert len(result.diagnostics) == 1
    assert "string literal must not contain NUL" in result.diagnostics[0].message
    assert "\x00" not in result.diagnostics[0].message


def test_invalid_field_identifier_emits_no_partial_artifact() -> None:
    script_ir = _compile(
        SOURCE + "table selected:\n    from users\n    select:\n        email\n"
    )
    relation = _definition(script_ir, RelationIR, "selected")
    projection = relation.projections[0]
    assert isinstance(projection.expression, FieldRefIR)
    bad_expression = replace(projection.expression, name="x" * 65)
    bad_relation = replace(
        relation,
        projections=(replace(projection, expression=bad_expression),),
    )
    definitions = tuple(
        bad_relation if definition is relation else definition
        for definition in script_ir.definitions
    )

    result = emit_mysql_sql(ScriptIR(definitions=definitions))

    assert result.artifacts == ()
    assert len(result.diagnostics) == 1
    assert "column identifier must not exceed 64 characters" in (
        result.diagnostics[0].message
    )


def test_supported_artifacts_and_diagnostics_preserve_definition_order() -> None:
    script_ir = _compile(
        SOURCE + "table first:\n"
        "    from users\n"
        "    select:\n"
        "        email\n"
        "table second:\n"
        "    from users\n"
        "    select:\n"
        "        age\n"
        "table third:\n"
        "    from users\n"
        "    select:\n"
        "        deleted_at\n"
    )
    second = _definition(script_ir, RelationIR, "second")
    projection = second.projections[0]
    bad_expression = ComparisonIR(
        span=projection.expression.span,
        value_type=projection.expression.value_type,
        left=projection.expression,
        operator="like",
        right=LiteralIR(
            span=projection.expression.span,
            value_type=projection.expression.value_type,
            value="2",
        ),
    )
    bad_second = replace(
        second,
        projections=(replace(projection, expression=bad_expression),),
    )
    definitions = tuple(
        bad_second if definition is second else definition
        for definition in script_ir.definitions
    )

    result = emit_mysql_sql(ScriptIR(definitions=definitions))

    assert [artifact.name for artifact in result.artifacts] == ["first", "third"]
    assert len(result.diagnostics) == 1
    assert "second" in result.diagnostics[0].message
    assert "comparison operator: like" in result.diagnostics[0].message


def test_metadata_remains_non_emitting() -> None:
    script_ir = _compile(
        "type Email = Text not null\n"
        "enum Status:\n"
        "    active\n"
        "constraint valid_email(email: Text not null) -> Bool not null:\n"
        "    email is not null\n"
        "derive normalize_email(email: Text not null) -> Text not null:\n"
        "    trim(email)\n"
        + SOURCE
        + "table selected:\n    from users\n    select:\n        email\n"
    )

    result = emit_mysql_sql(script_ir)

    assert [artifact.name for artifact in result.artifacts] == ["selected"]
    assert result.diagnostics == ()


def test_mysql_emitter_does_not_run_frontend_or_ir_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script_ir = _compile(
        SOURCE + "table selected:\n    from users\n    select:\n        email\n"
    )

    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("MySQL emission must consume ScriptIR directly")

    monkeypatch.setattr(parser_api, "parse_source", unexpected_call)
    monkeypatch.setattr(semantic_api, "analyze", unexpected_call)
    monkeypatch.setattr(ir_api, "build_ir", unexpected_call)

    result = emit_mysql_sql(script_ir)

    assert [artifact.name for artifact in result.artifacts] == ["selected"]
    assert result.diagnostics == ()


@pytest.mark.parametrize("exception_type", [TypeError, ValueError])
def test_unexpected_renderer_errors_remain_visible(
    monkeypatch: pytest.MonkeyPatch,
    exception_type: type[Exception],
) -> None:
    script_ir = _compile(
        SOURCE + "table selected:\n    from users\n    select:\n        email\n"
    )

    def unexpected_error(*args: object, **kwargs: object) -> str:
        del args, kwargs
        raise exception_type("unexpected renderer defect")

    monkeypatch.setattr(mysql_module, "render_mysql_relation", unexpected_error)

    with pytest.raises(exception_type, match="unexpected renderer defect"):
        emit_mysql_sql(script_ir)


def test_mysql_sql_modules_have_no_runtime_or_sqlglot_dependencies() -> None:
    source = inspect.getsource(mysql_module) + inspect.getsource(relation_module)

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


def _compile(source: str) -> ScriptIR:
    parse_result = parser_api.parse_source(source, path="mysql-relations.pietto")
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


def _definition[DefinitionT: (SourceIR, RelationIR)](
    script_ir: ScriptIR,
    definition_type: type[DefinitionT],
    name: str,
) -> DefinitionT:
    definition = next(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, definition_type) and definition.name == name
    )
    return definition
