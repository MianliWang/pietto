from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from pietto.errors import Diagnostic, Severity
from pietto.ir import CallIR, RelationIR, ScriptIR, SourceIR, build_ir
from pietto.parser_api import parse_file, parse_source
from pietto.semantic import analyze
from pietto.sql import SqlArtifactKind, SqlResult, emit_postgres_sql

EXAMPLE_PATHS = tuple(sorted(Path("examples").rglob("*.pie")))
assert EXAMPLE_PATHS, "Expected at least one committed Pietto example."

BASE_SOURCE = (
    "shape User:\n"
    "    id: UUID not null\n"
    "    email: Text nullable\n"
    "    active: Bool not null\n"
    'source users: User is postgres.table("users")\n'
)


def test_minimal_relation_sql_has_stable_multiline_format() -> None:
    result = _emit(
        BASE_SOURCE + "table active_users:\n"
        "    from users\n"
        "    where active == true\n"
        "    select:\n"
        "        id\n"
        "        email_norm = lower(trim(email))\n"
        "        email\n"
    )

    assert result.artifacts == (result.artifacts[0],)
    assert result.artifacts[0].kind is SqlArtifactKind.RELATION
    assert result.artifacts[0].name == "active_users"
    assert result.artifacts[0].sql == (
        "SELECT\n"
        '    "id" AS "id",\n'
        '    lower(trim("email")) AS "email_norm",\n'
        '    "email" AS "email"\n'
        'FROM "users"\n'
        'WHERE "active" = TRUE'
    )
    assert not result.artifacts[0].sql.endswith("\n")
    assert result.diagnostics == ()


def test_relation_without_filter_omits_where_exactly() -> None:
    result = _emit(
        BASE_SOURCE + "query user_emails:\n    from users\n    select:\n        email\n"
    )

    assert result.artifacts[0].sql == ('SELECT\n    "email" AS "email"\nFROM "users"')
    assert "WHERE" not in result.artifacts[0].sql


def test_relation_with_filter_has_exactly_one_where_clause() -> None:
    result = _emit(
        BASE_SOURCE + "query active_user_emails:\n"
        "    from users\n"
        "    where active == true\n"
        "    select:\n"
        "        email\n"
    )

    sql = result.artifacts[0].sql
    assert sql.count("WHERE") == 1
    assert sql.endswith('WHERE "active" = TRUE')


def test_relation_dependency_uses_exact_quoted_upstream_name() -> None:
    result = _emit(
        BASE_SOURCE + "table active_users:\n"
        "    from users\n"
        "    select:\n"
        "        email\n"
        "query active_user_emails:\n"
        "    from active_users\n"
        "    select:\n"
        "        normalized_email = lower(email)\n"
    )

    assert [artifact.name for artifact in result.artifacts] == [
        "active_users",
        "active_user_emails",
    ]
    assert result.artifacts[1].sql == (
        'SELECT\n    lower("email") AS "normalized_email"\nFROM "active_users"'
    )


def test_metadata_does_not_change_artifact_text_or_add_diagnostics() -> None:
    baseline = _emit(
        BASE_SOURCE + "table user_emails:\n    from users\n    select:\n        email\n"
    )
    with_metadata = _emit(
        "type Email = Text not null\n"
        "enum Status:\n"
        "    active\n"
        "constraint valid_email(email: Text not null) -> Bool not null:\n"
        "    email is not null\n"
        "derive normalize_email(email: Text not null) -> Text not null:\n"
        "    trim(email)\n" + BASE_SOURCE + "table user_emails:\n"
        "    from users\n"
        "    select:\n"
        "        email\n"
    )

    assert with_metadata.artifacts == baseline.artifacts
    assert with_metadata.diagnostics == baseline.diagnostics == ()


def test_artifacts_and_diagnostics_coexist_in_source_order() -> None:
    script_ir = _compile_ir(
        BASE_SOURCE + 'source backup: User is postgres.table("backup")\n'
        "table first_ok:\n"
        "    from users\n"
        "    select:\n"
        "        email\n"
        "table first_bad:\n"
        "    from backup\n"
        "    select:\n"
        "        email\n"
        "query second_ok:\n"
        "    from first_ok\n"
        "    select:\n"
        "        email\n"
        "query second_bad:\n"
        "    from users\n"
        "    select:\n"
        "        normalized = lower(email)\n"
    )
    backup = _source(script_ir, "backup")
    first_bad = _relation(script_ir, "first_bad")
    second_bad = _relation(script_ir, "second_bad")
    projection = second_bad.projections[0]
    assert isinstance(projection.expression, CallIR)

    invalid_backup = replace(
        backup,
        connector=replace(backup.connector, name="unsupported.table"),
    )
    invalid_second_bad = replace(
        second_bad,
        projections=(
            replace(
                projection,
                expression=replace(projection.expression, callee="unsupported"),
            ),
        ),
    )
    definitions = tuple(
        invalid_backup
        if definition is backup
        else invalid_second_bad
        if definition is second_bad
        else definition
        for definition in script_ir.definitions
    )

    result = emit_postgres_sql(ScriptIR(definitions=definitions))

    assert [artifact.name for artifact in result.artifacts] == [
        "first_ok",
        "second_ok",
    ]
    assert [
        (diagnostic.code, _diagnostic_definition_name(diagnostic))
        for diagnostic in result.diagnostics
    ] == [
        ("PIE-B1000", first_bad.name),
        ("PIE-B1000", second_bad.name),
    ]


@pytest.mark.parametrize("path", EXAMPLE_PATHS, ids=str)
def test_committed_examples_emit_without_ordinary_exceptions(path: Path) -> None:
    parse_result = parse_file(path)
    assert parse_result.diagnostics == (), _format_diagnostics(
        path,
        "parser",
        parse_result.diagnostics,
    )
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    semantic_errors = tuple(
        diagnostic
        for diagnostic in semantic_result.diagnostics
        if diagnostic.severity is Severity.ERROR
    )
    assert semantic_errors == (), _format_diagnostics(
        path,
        "semantic",
        semantic_errors,
    )

    ir_result = build_ir(parse_result.ast, semantic_result.model)
    ir_errors = tuple(
        diagnostic
        for diagnostic in ir_result.diagnostics
        if diagnostic.severity is Severity.ERROR
    )
    assert ir_errors == (), _format_diagnostics(path, "IR", ir_errors)
    assert ir_result.ir is not None

    sql_result = emit_postgres_sql(ir_result.ir)

    assert all(
        artifact.kind is SqlArtifactKind.RELATION for artifact in sql_result.artifacts
    )
    assert sql_result.diagnostics == ()


def _emit(source: str) -> SqlResult:
    return emit_postgres_sql(_compile_ir(source))


def _compile_ir(source: str) -> ScriptIR:
    parse_result = parse_source(source, path="artifact-formatting.pie")
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


def _source(script_ir: ScriptIR, name: str) -> SourceIR:
    return next(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, SourceIR) and definition.name == name
    )


def _relation(script_ir: ScriptIR, name: str) -> RelationIR:
    return next(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR) and definition.name == name
    )


def _diagnostic_definition_name(diagnostic: Diagnostic) -> str:
    head = diagnostic.message.split(".", maxsplit=1)[0]
    return head.rsplit(": ", maxsplit=1)[-1]


def _format_diagnostics(
    path: Path,
    stage: str,
    diagnostics: tuple[Diagnostic, ...],
) -> str:
    details = "\n".join(
        (
            f"{diagnostic.severity.value} {diagnostic.code} "
            f"{diagnostic.location.line}:{diagnostic.location.column} "
            f"{diagnostic.message}"
        )
        for diagnostic in diagnostics
    )
    return f"{path} produced {stage} diagnostics:\n{details}"
