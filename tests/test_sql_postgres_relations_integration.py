from __future__ import annotations

from pathlib import Path

import pytest

from pietto.errors import Diagnostic, Severity
from pietto.ir import ScriptIR, build_ir
from pietto.parser_api import parse_file, parse_source
from pietto.semantic import analyze
from pietto.sql import SqlArtifactKind, SqlResult, emit_postgres_sql

EXAMPLE_PATHS = tuple(sorted(Path("examples").rglob("*.pietto")))
assert EXAMPLE_PATHS, "Expected at least one committed Pietto example."

EXPECTED_EXAMPLE_ARTIFACTS = {
    Path("examples/queries/active_user_emails.pietto"): (
        "active_users",
        "active_user_emails",
    ),
    Path("examples/tables/active_users.pietto"): ("active_users",),
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
        path="postgres-integration.pietto",
    )

    assert len(result.artifacts) == 1
    artifact = result.artifacts[0]
    assert artifact.kind is SqlArtifactKind.RELATION
    assert artifact.name == "ActiveCustomers"
    assert artifact.sql == (
        "SELECT\n"
        '    "Email" AS "ContactEmail"\n'
        'FROM "Sales"."Customers"\n'
        "WHERE \"Email\" = 'O''Reilly'"
    )


def test_pipeline_casts_sign_to_the_int_its_semantics_declare() -> None:
    # PostgreSQL sign() returns double precision for an integer and numeric for
    # a numeric argument; Pietto types every sign() as Int.
    result = _compile_and_emit(
        "shape Acct:\n"
        "    n: Int not null\n"
        "    d: Decimal(10, 2) not null\n"
        "    m: Int nullable\n"
        'source accts: Acct is postgres.table("accts")\n'
        "table q:\n"
        "    from accts\n"
        "    where sign(m) == -1\n"
        "    select:\n"
        "        sn = sign(n)\n"
        "        sd = sign(d)\n"
        "        sm = sign(n - 1)\n"
        "    order by:\n"
        "        sign(d) desc\n",
    )

    assert [artifact.sql for artifact in result.artifacts] == [
        "SELECT\n"
        '    CAST(sign("n") AS bigint) AS "sn",\n'
        '    CAST(sign("d") AS bigint) AS "sd",\n'
        '    CAST(sign(("n" - 1)) AS bigint) AS "sm"\n'
        'FROM "accts"\n'
        'WHERE CAST(sign("m") AS bigint) = (-1)\n'
        "ORDER BY\n"
        '    CAST(sign("d") AS bigint) DESC'
    ]


def test_pipeline_emits_decimal_int_membership_as_written() -> None:
    # `amount in (1, 2)` checks like `amount == 1 or amount == 2`; neither
    # side is cast.
    result = _compile_and_emit(
        "type Money = Decimal(12, 2) not null\n"
        "shape Acct:\n"
        "    amount: Decimal(12, 2) not null\n"
        "    n: Int not null\n"
        "    m: Money not null\n"
        'source accts: Acct is postgres.table("accts")\n'
        "table q:\n"
        "    from accts\n"
        "    let:\n"
        "        listed = m in (n, null)\n"
        "    where amount in (1, 2)\n"
        "    select:\n"
        "        n\n"
        "        r = n not in (amount, -3)\n"
        "        s = listed\n"
    )

    assert [artifact.sql for artifact in result.artifacts] == [
        "SELECT\n"
        '    "n" AS "n",\n'
        '    "n" NOT IN ("amount", (-3)) AS "r",\n'
        '    "m" IN ("n", NULL) AS "s"\n'
        'FROM "accts"\n'
        'WHERE "amount" IN (1, 2)'
    ]
    assert result.diagnostics == ()


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
        path="postgres-ordering.pietto",
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
    path: str = "postgres-integration.pietto",
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
