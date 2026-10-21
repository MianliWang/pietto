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


def test_pipeline_emits_abs_of_every_numeric_type_as_written() -> None:
    # PostgreSQL abs() returns the type of its argument, as Pietto types it.
    result = _compile_and_emit(
        "shape Acct:\n"
        "    n: Int not null\n"
        "    f: Float nullable\n"
        "    d: Decimal(10, 2) not null\n"
        'source accts: Acct is postgres.table("accts")\n'
        "table q:\n"
        "    from accts\n"
        "    where abs(n - 1) < 3\n"
        "    select:\n"
        "        an = abs(n)\n"
        "        af = abs(f)\n"
        "        ad = abs(d)\n"
        "        al = abs(-2)\n"
    )

    assert [artifact.sql for artifact in result.artifacts] == [
        "SELECT\n"
        '    abs("n") AS "an",\n'
        '    abs("f") AS "af",\n'
        '    abs("d") AS "ad",\n'
        '    abs((-2)) AS "al"\n'
        'FROM "accts"\n'
        'WHERE abs(("n" - 1)) < 3'
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


def test_pipeline_refuses_null_arithmetic_and_read_null_outputs_on_postgresql() -> None:
    """PostgreSQL types an arithmetic from its operands and finds no operator
    when every one is an untyped NULL, and it makes an untyped NULL output a
    `text` column, which a relation that reads it takes for its type. Before,
    emission wrote `NULL + NULL`, `-NULL` and `NULL AS "c"` for a relation
    that another relation reads. A NULL beside a typed operand, and a NULL
    output no relation reads, emit as written."""
    result = _compile_and_emit(
        "shape Acct:\n"
        "    n: Int nullable\n"
        'source accts: Acct is postgres.table("accts")\n'
        "table sums:\n    from accts\n    select:\n        a = null + null\n"
        "table signs:\n    from accts\n    select:\n        b = coalesce(-null, n)\n"
        "table nothing:\n    from accts\n    let:\n        k = null\n"
        "    select:\n        c = null\n        d = k\n"
        "query later:\n    from nothing\n    select:\n        c\n"
        "query typed:\n    from accts\n    select:\n        e = n + null\n"
        "        f = null\n",
        path="null.pietto",
    )

    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in result.diagnostics
    ] == [
        (
            "PIE-B1000",
            "PostgreSQL SQL emission is not implemented for RelationIR: "
            f"{name}. PostgreSQL {reason}",
            line,
            1,
        )
        for name, reason, line in (
            ("sums", "cannot type operator + when every operand is NULL", 4),
            ("signs", "cannot type operator - when every operand is NULL", 8),
            (
                "nothing",
                "types a NULL output that another relation reads as text, "
                "which Pietto leaves untyped",
                12,
            ),
        )
    ]
    assert [artifact.sql for artifact in result.artifacts] == [
        'SELECT\n    "c" AS "c"\nFROM "nothing"',
        'SELECT\n    "n" + NULL AS "e",\n    NULL AS "f"\nFROM "accts"',
    ]


def test_pipeline_refuses_read_outputs_whose_every_value_is_null_on_postgresql() -> (
    None
):
    """PostgreSQL types a CASE, COALESCE or NULLIF whose every value is an
    untyped NULL as `text`, as it does the NULL itself. Before, emission wrote
    `CASE WHEN "b" THEN NULL ELSE NULL END AS "v"` and `COALESCE(NULL, NULL)
    AS "c"` for a relation that another relation reads, whose `"v" + 1` then
    failed with `operator does not exist: text + integer`. One typed value
    types them, and an output no relation reads emits as written."""
    result = _compile_and_emit(
        "shape S:\n    n: Int nullable\n    b: Bool nullable\n"
        'source src: S is postgres.table("app.src")\n'
        "table cases:\n    from src\n    select:\n        v = null if b else null\n"
        "table coalesced:\n    from src\n    select:\n        c = coalesce(null, null)\n"
        "table nested:\n    from src\n    let:\n        k = nullif(null, null)\n"
        "    select:\n        d = k if b else coalesce(null, null)\n"
        "table typed:\n    from src\n    select:\n        e = null if b else n\n"
        "        f = nullif(null, n)\n        g = coalesce(null, n)\n"
        "query later:\n    from cases\n    select:\n        w = v + 1\n"
        "query again:\n    from coalesced\n    select:\n        c\n"
        "query deeper:\n    from nested\n    select:\n        d\n"
        "query fine:\n    from typed\n    select:\n        e\n"
        "query unread:\n    from src\n    select:\n        h = null if b else null\n",
        path="null-trees.pietto",
    )

    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in result.diagnostics
    ] == [
        (
            "PIE-B1000",
            "PostgreSQL SQL emission is not implemented for RelationIR: "
            f"{name}. PostgreSQL types a NULL output that another relation "
            "reads as text, which Pietto leaves untyped",
            line,
            1,
        )
        for name, line in (("cases", 5), ("coalesced", 9), ("nested", 13))
    ]
    assert [artifact.name for artifact in result.artifacts] == [
        "typed",
        "later",
        "again",
        "deeper",
        "fine",
        "unread",
    ]
    assert result.artifacts[0].sql == (
        'SELECT\n    CASE WHEN "b" THEN NULL ELSE "n" END AS "e",\n'
        '    NULLIF(NULL, "n") AS "f",\n    COALESCE(NULL, "n") AS "g"\n'
        'FROM "app"."src"'
    )
    assert result.artifacts[-1].sql == (
        'SELECT\n    CASE WHEN "b" THEN NULL ELSE NULL END AS "h"\nFROM "app"."src"'
    )


def test_pipeline_refuses_typed_uses_of_null_cases_on_postgresql() -> None:
    """PostgreSQL types a CASE, COALESCE or NULLIF whose every value is an
    untyped NULL as `text`, also inside one relation. Before, emission wrote
    `COALESCE(NULL, NULL) + 1`, `"n" IN (COALESCE(NULL, NULL), 1)` and
    `COALESCE((CASE WHEN "b" THEN NULL ELSE NULL END), "n")`, which
    PostgreSQL rejects (`operator does not exist: text + integer`, `COALESCE
    types text and bigint cannot be matched`, `argument of WHERE must be type
    boolean`). Beside a `Text` operand, an enum or the null literal, as the
    argument of a function that takes text, and where nothing reads it, it
    emits as written."""
    result = _compile_and_emit(
        "enum Status:\n    active\n    done\n"
        "shape S:\n    n: Int nullable\n    b: Bool nullable\n"
        "    t: Text nullable\n    st: Status nullable\n"
        'source src: S is postgres.table("app.src")\n'
        "query plus:\n    from src\n    select:\n"
        "        x = coalesce(null, null) + 1\n"
        "query sign:\n    from src\n    select:\n        x = -nullif(null, null)\n"
        "query both:\n    from src\n    select:\n"
        "        x = (null if b else null) and b\n"
        "query equal:\n    from src\n    select:\n"
        "        x = coalesce(null, null) == 1\n"
        "query listed:\n    from src\n    select:\n"
        "        x = n in (coalesce(null, null), 1)\n"
        "query nested:\n    from src\n    select:\n"
        "        x = coalesce(null if b else null, n)\n"
        "query branch:\n    from src\n    select:\n"
        "        x = coalesce(null, null) if b else 1\n"
        "query test:\n    from src\n    select:\n"
        "        x = 1 if coalesce(null, null) else 2\n"
        "query kept:\n    from src\n    where nullif(null, null)\n    select:\n"
        "        n\n"
        "query part:\n    from src\n    select:\n"
        "        x = year(null if b else null)\n"
        "query fine:\n    from src\n    select:\n"
        "        x = coalesce(null, null) == t\n"
        "        y = coalesce(null if b else null, t)\n"
        "        z = st == coalesce(null, null)\n"
        "        w = len(nullif(null, null))\n"
        "        v = coalesce(coalesce(null, null), null)\n",
        path="null-cases.pietto",
    )

    text = "PostgreSQL types a CASE, COALESCE or NULLIF of only NULL values as text"
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in result.diagnostics
    ] == [
        (
            "PIE-B1000",
            "PostgreSQL SQL emission is not implemented for RelationIR: "
            f"{name}. {text}, {reason}",
            line,
            1,
        )
        for name, reason, line in (
            ("plus", "which operator + does not take", 10),
            ("sign", "which operator - does not take", 14),
            ("both", "which operator and does not take", 18),
            ("equal", "and operator == has no common type for text and Int", 22),
            ("listed", "and operator in has no common type for text and Int", 26),
            ("nested", "and coalesce has no common type for text and Int", 30),
            ("branch", "and a conditional has no common type for text and Int", 34),
            ("test", "which a condition does not take", 38),
            ("kept", "which a condition does not take", 42),
            ("part", "which function year does not take", 47),
        )
    ]
    assert [artifact.sql for artifact in result.artifacts] == [
        "SELECT\n"
        '    COALESCE(NULL, NULL) = "t" AS "x",\n'
        '    COALESCE((CASE WHEN "b" THEN NULL ELSE NULL END), "t") AS "y",\n'
        '    "st" = COALESCE(NULL, NULL) AS "z",\n'
        '    length(NULLIF(NULL, NULL)) AS "w",\n'
        '    COALESCE(COALESCE(NULL, NULL), NULL) AS "v"\n'
        'FROM "app"."src"'
    ]


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
