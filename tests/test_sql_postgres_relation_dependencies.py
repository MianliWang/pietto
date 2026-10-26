from __future__ import annotations

from dataclasses import replace

import pytest

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
    "    id: UUID\n"
    "    email: Text | None\n"
    "    active: Bool\n"
    'source users: User = postgres.table("users")\n'
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
        'WITH "active_users" AS (\n'
        "SELECT\n"
        '    "id" AS "id",\n'
        '    "email" AS "email"\n'
        'FROM "users"\n'
        'WHERE "active" = TRUE\n'
        ")\n"
        "SELECT\n"
        '    lower("email") AS "normalized_email"\n'
        'FROM "active_users"\n'
        'WHERE "email" IS NOT NULL'
    )
    assert result.diagnostics == ()


def test_a_relation_of_the_file_is_a_cte_of_its_readers_sql() -> None:
    """The CTE is the relation's own artifact SQL, so the reader runs without
    that relation in the database."""

    upstream, downstream = emit_postgres_sql(_chain_ir()).artifacts

    assert downstream.sql.startswith(f'WITH "active_users" AS (\n{upstream.sql}\n)\n')
    assert downstream.sql.count("WITH") == 1


def test_each_relation_a_statement_reads_is_one_cte_after_the_ones_it_reads() -> None:
    """FROM, JOIN and ANY reads, also through other relations of the file:
    each relation is defined once, after the relations it reads, in the order
    the statement reads them."""

    result = emit_postgres_sql(
        _compile_ir(
            SOURCE + "table base:\n    from users\n    select:\n        id\n"
            "        email\n"
            "table named:\n    from base\n    where email is not None\n"
            "    select:\n        id\n"
            "query joined:\n    from base\n    let n = named\n"
            "    inner join n on n.id == base.id\n    select:\n"
            "        id = base.id\n"
            "query tested:\n    from users\n"
            "    where any(n.id == users.id for n in named)\n"
            "    select:\n        id\n"
            "query chained:\n    from joined\n"
            "    where any(t.id == joined.id for t in tested)\n"
            "    select:\n        id\n"
        )
    )

    assert result.diagnostics == ()
    sql = {artifact.name: artifact.sql for artifact in result.artifacts}
    base = f'WITH "base" AS (\n{sql["base"]}\n)'
    assert sql["base"].startswith("SELECT\n")
    assert sql["named"].startswith(f"{base}\nSELECT\n")
    named = sql["named"].removeprefix(f"{base}\n")
    assert sql["joined"].startswith(f'{base},\n"named" AS (\n{named}\n)\nSELECT\n')
    assert 'INNER JOIN "named" AS "n"' in sql["joined"]
    assert sql["tested"].startswith('WITH "base" AS (\n')
    assert 'EXISTS (SELECT 1 FROM "named" AS' in sql["tested"]
    ctes = [
        line.split('"')[1]
        for line in sql["chained"].splitlines()
        if line.endswith(" AS (")
    ]
    assert ctes == ["base", "named", "joined", "tested"]


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


_HIDING = (
    "shape Row:\n    id: Int\n"
    'source raw: Row = postgres.table("raw_rows")\n'
    'source shadow: Row = postgres.table("{table}")\n'
    "table kept:\n    from raw\n    select:\n        id\n"
)
_LATER = "table later:\n    from shadow\n    select:\n        id\n"
_READS_SHADOW = (
    "query q:\n    from kept\n    where any(s.id == kept.id for s in shadow)\n"
    "    select:\n        id\n"
)


# A CTE takes the place of a same-named table without a schema in the CTEs
# after it and in the main SELECT, so emitting it would read the CTE's rows.
@pytest.mark.parametrize(
    ("reader", "artifacts", "line"),
    (
        (_READS_SHADOW, ["kept"], 9),
        (
            _LATER + "query q:\n    from kept\n"
            "    where any(l.id == kept.id for l in later)\n    select:\n        id\n",
            ["kept", "later"],
            13,
        ),
    ),
    ids=("main_select", "later_cte_body"),
)
def test_a_cte_that_would_hide_a_table_the_statement_reads_is_refused(
    reader: str, artifacts: list[str], line: int
) -> None:
    result = emit_postgres_sql(_compile_ir(_HIDING.format(table="kept") + reader))

    assert [artifact.name for artifact in result.artifacts] == artifacts
    assert [
        (item.code, item.severity, item.message, item.location.line)
        for item in result.diagnostics
    ] == [
        (
            "PIE-B1000",
            Severity.ERROR,
            "PostgreSQL SQL emission is not implemented for RelationIR: q. Its SQL "
            "defines relation kept as a CTE, which would hide table kept read in "
            "the same SQL; rename the relation or read the table with its schema",
            line,
        )
    ]


# A CTE is not visible in its own body or in the CTEs before it.
@pytest.mark.parametrize(
    ("source", "sql"),
    (
        (
            "shape Row:\n    id: Int\n"
            'source raw: Row = postgres.table("kept")\n'
            "table kept:\n    from raw\n    select:\n        id\n"
            "query q:\n    from kept\n    select:\n        id\n",
            'WITH "kept" AS (\nSELECT\n    "id" AS "id"\nFROM "kept"\n)\n'
            'SELECT\n    "id" AS "id"\nFROM "kept"',
        ),
        (
            _HIDING.format(table="kept") + _LATER + "query q:\n    from later\n"
            "    where any(k.id == later.id for k in kept)\n    select:\n        id\n",
            'WITH "later" AS (\nSELECT\n    "id" AS "id"\nFROM "kept"\n),\n'
            '"kept" AS (\nSELECT\n    "id" AS "id"\nFROM "raw_rows"\n)\n'
            'SELECT\n    "id" AS "id"\nFROM "later" AS "later"\n'
            'WHERE EXISTS (SELECT 1 FROM "kept" AS "_pietto_value_1" '
            'WHERE "_pietto_value_1"."id" = "later"."id")',
        ),
    ),
    ids=("own_body", "earlier_cte_body"),
)
def test_a_cte_hides_no_table_read_where_it_is_not_visible(
    source: str, sql: str
) -> None:
    result = emit_postgres_sql(_compile_ir(source))

    assert result.diagnostics == ()
    assert result.artifacts[-1].sql == sql


@pytest.mark.parametrize(
    ("table", "quoted"),
    (
        ("public.kept", '"public"."kept"'),
        ("Kept", '"Kept"'),
        ("kept_rows", '"kept_rows"'),
    ),
)
def test_a_cte_hides_no_table_of_another_name_or_with_a_schema(
    table: str, quoted: str
) -> None:
    result = emit_postgres_sql(_compile_ir(_HIDING.format(table=table) + _READS_SHADOW))

    assert result.diagnostics == ()
    assert result.artifacts[1].sql == (
        'WITH "kept" AS (\nSELECT\n    "id" AS "id"\nFROM "raw_rows"\n)\n'
        'SELECT\n    "id" AS "id"\nFROM "kept" AS "kept"\n'
        f'WHERE EXISTS (SELECT 1 FROM {quoted} AS "_pietto_value_1" '
        'WHERE "_pietto_value_1"."id" = "kept"."id")'
    )


def test_a_relation_whose_sql_is_refused_refuses_its_readers() -> None:
    result = emit_postgres_sql(
        _compile_ir(
            SOURCE + "table unset:\n    from users\n    select:\n        id\n"
            "        nothing = None\n"
            "query reader:\n    from unset\n    select:\n        id\n"
            "table direct:\n    from users\n    select:\n        id\n"
        )
    )

    assert [artifact.name for artifact in result.artifacts] == ["direct"]
    assert [(item.code, item.message) for item in result.diagnostics] == [
        (
            "PIE-B1000",
            f"PostgreSQL SQL emission is not implemented for RelationIR: {name}. "
            "PostgreSQL types a NULL output that another relation reads as text, "
            "which Pietto leaves untyped",
        )
        for name in ("unset", "reader")
    ]


def _chain_ir() -> ScriptIR:
    return _compile_ir(
        SOURCE + "table active_users:\n"
        "    from users\n"
        "    where active == True\n"
        "    select:\n"
        "        id\n"
        "        email\n"
        "query active_user_emails:\n"
        "    from active_users\n"
        "    where email is not None\n"
        "    select:\n"
        "        normalized_email = lower(email)\n"
    )


def _compile_ir(source: str) -> ScriptIR:
    parse_result = parse_source(source, path="relation-dependencies.pietto")
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    assert all(
        diagnostic.severity is not Severity.ERROR
        for diagnostic in semantic_result.diagnostics
    )
    # As the CLI does: JOIN lowering reads the normalized script.
    assert semantic_result.script is not None
    ir_result = build_ir(semantic_result.script, semantic_result.model)
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
