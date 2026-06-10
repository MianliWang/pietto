from __future__ import annotations

from pathlib import Path

import pytest

from pietto.errors import Diagnostic, Severity
from pietto.ir import ScriptIR, build_ir
from pietto.parser_api import parse_file, parse_source
from pietto.semantic import analyze
from pietto.sql import SqlArtifactKind, SqlResult, emit_postgres_sql

EXAMPLE_PATHS = tuple(sorted(Path("examples").rglob("*.pie")))
assert EXAMPLE_PATHS, "Expected at least one committed Pietto example."

EXPECTED_EXAMPLE_ARTIFACTS = {
    Path("examples/queries/active_user_emails.pie"): (
        "active_users",
        "active_user_emails",
    ),
    Path("examples/tables/active_users.pie"): ("active_users",),
}


def test_pipeline_emits_quoted_source_backed_relation_sql() -> None:
    result = _compile_and_emit(
        "shape Customer:\n"
        "    Email: Text not null\n"
        'source Customers: Customer is postgres.table("Sales.Customers")\n'
        "table ActiveCustomers:\n"
        "    from Customers\n"
        '    where Email == "O\'Reilly"\n'
        "    select:\n"
        "        ContactEmail = Email\n",
        path="postgres-integration.pie",
    )

    assert len(result.artifacts) == 1
    artifact = result.artifacts[0]
    assert artifact.kind is SqlArtifactKind.RELATION
    assert artifact.name == "ActiveCustomers"
    assert artifact.sql == (
        "SELECT\n"
        '    "Email" AS "ContactEmail"\n'
        'FROM "Sales.Customers"\n'
        "WHERE \"Email\" = 'O''Reilly'"
    )


def test_pipeline_uses_escape_string_for_backslash_quote_payload() -> None:
    result = _compile_and_emit(
        "shape User:\n"
        "    email: Text nullable\n"
        'source users: User is postgres.table("users")\n'
        "table matching_users:\n"
        "    from users\n"
        '    where email == "\\\\\'; DROP TABLE users; --"\n'
        "    select:\n"
        "        email\n",
    )

    sql = result.artifacts[0].sql
    assert sql.endswith("WHERE \"email\" = E'\\\\''; DROP TABLE users; --'")
    assert sql.count("E'") == 1
    assert result.diagnostics == ()


def test_pipeline_relation_without_filter_omits_where() -> None:
    result = _compile_and_emit(
        "shape Customer:\n"
        "    Email: Text not null\n"
        'source Customers: Customer is postgres.table("customers")\n'
        "query CustomerEmails:\n"
        "    from Customers\n"
        "    select:\n"
        "        Email\n",
    )

    assert [artifact.name for artifact in result.artifacts] == ["CustomerEmails"]
    assert "WHERE" not in result.artifacts[0].sql


def test_artifacts_and_diagnostics_preserve_their_definition_order() -> None:
    result = _compile_and_emit(
        "shape Customer:\n"
        "    Email: Text not null\n"
        'source Customers: Customer is postgres.table("customers")\n'
        "table FirstRelation:\n"
        "    from Customers\n"
        "    select:\n"
        "        Email\n"
        "enum Status:\n"
        "    active\n"
        "query SecondRelation:\n"
        "    from Customers\n"
        "    select:\n"
        "        Email\n"
        "type CustomerEmail = Text not null\n",
        path="postgres-ordering.pie",
    )

    assert [artifact.name for artifact in result.artifacts] == [
        "FirstRelation",
        "SecondRelation",
    ]
    assert result.diagnostics == ()


def test_relation_dependency_uses_quoted_upstream_name_without_expansion() -> None:
    result = _compile_and_emit(
        "shape Customer:\n"
        "    Email: Text not null\n"
        'source Customers: Customer is postgres.table("customers")\n'
        "table CustomerRows:\n"
        "    from Customers\n"
        "    select:\n"
        "        Email\n"
        "query CustomerEmails:\n"
        "    from CustomerRows\n"
        "    select:\n"
        "        Email\n",
    )

    assert [artifact.name for artifact in result.artifacts] == [
        "CustomerRows",
        "CustomerEmails",
    ]
    assert result.artifacts[1].sql.endswith('FROM "CustomerRows"')


@pytest.mark.parametrize("path", EXAMPLE_PATHS, ids=str)
def test_committed_examples_complete_postgres_backend_pipeline(path: Path) -> None:
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

    assert [artifact.name for artifact in sql_result.artifacts] == list(
        EXPECTED_EXAMPLE_ARTIFACTS.get(path, ())
    )
    assert all(
        artifact.kind is SqlArtifactKind.RELATION for artifact in sql_result.artifacts
    )
    assert sql_result.diagnostics == ()


def _compile_and_emit(
    source: str,
    *,
    path: str = "postgres-integration.pie",
) -> SqlResult:
    parse_result = parse_source(source, path=path)
    assert parse_result.diagnostics == (), _format_diagnostics(
        Path(path),
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
        Path(path),
        "semantic",
        semantic_errors,
    )

    ir_result = build_ir(parse_result.ast, semantic_result.model)
    assert ir_result.diagnostics == (), _format_diagnostics(
        Path(path),
        "IR",
        ir_result.diagnostics,
    )
    assert isinstance(ir_result.ir, ScriptIR)
    return emit_postgres_sql(ir_result.ir)


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
