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
    SymbolId,
    SymbolNamespace,
    build_ir,
)
from pietto.sql import SqlArtifactKind, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql
from pietto.sql.relations import render_relation_sql

SOURCE = (
    "shape User:\n"
    "    email: Text | None\n"
    "    deleted_at: Timestamp | None\n"
    'source users: User = postgres.table("public.users")\n'
)


def test_source_backed_relation_emits_select_from_where_and_projections() -> None:
    script_ir = _compile(
        SOURCE + "table active_users:\n"
        "    from users\n"
        "    where deleted_at is None\n"
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
        'FROM "public"."users"\n'
        'WHERE "deleted_at" IS NULL'
    )
    assert result.diagnostics == ()


def test_concat_emits_the_null_propagating_postgres_operator() -> None:
    result = emit_postgres_sql(
        _compile(
            "type Label = Text\n"
            "shape Item:\n"
            "    code: Text\n"
            "    note: Text | None\n"
            "    tag: Label\n"
            'source items: Item = postgres.table("public.items")\n'
            "table labelled:\n"
            "    from items\n"
            "    select:\n"
            '        pair = concat(code, "-", tag)\n'
            "        nulled = concat(note, None)\n"
        )
    )

    assert result.diagnostics == ()
    assert result.artifacts[0].sql == (
        "SELECT\n"
        '    ("code" || \'-\' || "tag") AS "pair",\n'
        '    ("note" || NULL) AS "nulled"\n'
        'FROM "public"."items"'
    )


_CONCAT_POSITIONS = (
    "shape Item:\n    code: Text\n    note: Text | None\n    qty: Int\n"
    'source items: Item = {}.table("public.items")\n'
    'def tagged(x: Text) -> Text: return concat(x, "!")\n'
    "query q:\n    from items\n"
    '    where concat(code, "-") == "a-" or concat(concat(code, note), "x") != code\n'
    "    select:\n"
    '        nested = concat(concat(code, "-"), concat(note, Text(qty)))\n'
    "        nulls = concat(None, None)\n"
    "        defd = tagged(code)\n"
    "    order by:\n"
    '        concat(code, "z")\n'
)
_SHAPELESS_CONCAT = (
    'source raw = {}.table("events")\n'
    "query q:\n    from raw\n    select:\n"
    "        merged = concat(payload, extra)\n"
    "        nulls = concat(None, None)\n"
)


def test_concat_nests_in_every_position_and_casts_an_operand_of_unknown_type() -> None:
    parsed = parser_api.parse_source(_CONCAT_POSITIONS.format("postgres"))
    assert parsed.diagnostics == () and parsed.ast is not None
    checked = semantic_api.analyze(parsed.ast)
    assert checked.diagnostics == () and checked.script is not None
    lowered = build_ir(checked.script, checked.model)
    assert lowered.diagnostics == () and lowered.ir is not None
    assert emit_postgres_sql(lowered.ir).artifacts[0].sql == (
        "SELECT\n"
        '    (("code" || \'-\') || ("note" || (CAST("qty" AS text)))) AS "nested",\n'
        '    (NULL || NULL) AS "nulls",\n'
        '    ("code" || \'!\') AS "defd"\n'
        'FROM "public"."items"\n'
        'WHERE (("code" || \'-\') = \'a-\') OR ((("code" || "note") || \'x\') <> "code")\n'
        "ORDER BY\n"
        "    (\"code\" || 'z') ASC"
    )
    # A field of a source without a shape may be jsonb, an array or a bytea,
    # whose `||` joins no text.
    result = emit_postgres_sql(_compile(_SHAPELESS_CONCAT.format("postgres")))
    assert result.artifacts[0].sql == (
        "SELECT\n"
        '    (CAST("payload" AS text) || CAST("extra" AS text)) AS "merged",\n'
        '    (NULL || NULL) AS "nulls"\n'
        'FROM "events"'
    )


_SAME_VALUE = (
    "shape Order:\n"
    "    id: Int\n"
    "    customer_id: Int | None\n"
    "    code: Text\n"
    "    note: Text | None\n"
    "shape Customer:\n"
    "    id: Int\n"
    "    ref: Int | None\n"
    'source orders: Order = postgres.table("public.orders")\n'
    'source customers: Customer = postgres.table("public.customers")\n'
)


def test_same_value_is_not_distinct_from_in_select_where_and_join_on() -> None:
    selected = emit_postgres_sql(
        _compile(
            _SAME_VALUE + "table matched:\n"
            "    from orders\n"
            "    where same_value(note, code)\n"
            "    select:\n"
            "        id\n"
            "        same = same_value(customer_id, id)\n"
            "        other = not same_value(note, code)\n"
        )
    )
    joined = emit_postgres_sql(
        _compile(
            _SAME_VALUE + "query q:\n"
            "    from orders\n"
            "    left join customers on same_value(customers.ref, orders.customer_id)\n"
            "    select:\n"
            "        oid = orders.id\n"
            "        cid = customers.id\n"
        )
    )

    assert selected.diagnostics == joined.diagnostics == ()
    assert selected.artifacts[0].sql == (
        "SELECT\n"
        '    "id" AS "id",\n'
        '    ("customer_id" IS NOT DISTINCT FROM "id") AS "same",\n'
        '    NOT ("note" IS NOT DISTINCT FROM "code") AS "other"\n'
        'FROM "public"."orders"\n'
        'WHERE ("note" IS NOT DISTINCT FROM "code")'
    )
    assert joined.artifacts[0].sql == (
        "SELECT\n"
        '    "orders"."id" AS "oid",\n'
        '    "customers"."id" AS "cid"\n'
        'FROM "public"."orders" AS "orders"\n'
        'LEFT JOIN "public"."customers" AS "customers" '
        'ON ("customers"."ref" IS NOT DISTINCT FROM "orders"."customer_id")'
    )


def test_relation_without_filter_omits_where() -> None:
    script_ir = _compile(
        SOURCE + "query user_emails:\n    from users\n    select:\n        email\n"
    )

    result = emit_postgres_sql(script_ir)

    assert len(result.artifacts) == 1
    assert result.artifacts[0].sql == (
        'SELECT\n    "email" AS "email"\nFROM "public"."users"'
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
    ).endswith('FROM "public"."users"')


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


def test_output_alias_over_63_bytes_reports_pie_b1000_on_postgresql_only() -> None:
    alias = "a" * 63 + "_one"
    body = f"table long_names:\n    from users\n    select:\n        {alias} = email\n"
    mysql_source = SOURCE.replace("postgres.table", "mysql.table")

    result = emit_postgres_sql(_compile(SOURCE + body))
    mysql = emit_mysql_sql(_compile(mysql_source + body))

    # Before: PostgreSQL truncated the alias silently to its first 63 bytes.
    assert result.artifacts == ()
    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-B1000"]
    # The refusal names the identifier and is not reported as unimplemented.
    assert result.diagnostics[0].message == (
        "PostgreSQL SQL emission refuses RelationIR: long_names. PostgreSQL "
        f'identifier "{"a" * 24}..." is 67 bytes, over the 63 bytes PostgreSQL '
        "keeps of a name"
    )
    assert mysql.diagnostics == ()
    assert f"`email` AS `{alias}`" in mysql.artifacts[0].sql


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


@pytest.mark.parametrize("table_name", ["a.b.c", ".users", "public.", "a..b"])
def test_malformed_dotted_source_table_name_reports_pie_b1000(
    table_name: str,
) -> None:
    script_ir = _compile(
        SOURCE + "table user_emails:\n    from users\n    select:\n        email\n"
    )
    source = _definition(script_ir, SourceIR, "users")
    bad_source = replace(
        source,
        connector=replace(source.connector, arguments=(table_name,)),
    )
    definitions = tuple(
        bad_source if definition is source else definition
        for definition in script_ir.definitions
    )

    result = emit_postgres_sql(ScriptIR(definitions=definitions))

    assert result.artifacts == ()
    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-B1000"]
    assert result.diagnostics[0].message.endswith(
        "PostgreSQL table name must be <table> or <schema>.<table>"
    )


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
        expression=replace(
            projection.expression,
            callee="unsupported",
            callee_symbol=SymbolId(SymbolNamespace.CALLABLE, "unsupported"),
        ),
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


_EXTREMA = (
    "shape Item:\n    a: Int\n    b: Int | None\n    t: Text\n"
    "    ts: Timestamp\n    ts2: Timestamp | None\n    uu: UUID\n    flag: Bool\n"
    'source items: Item = {}.table("public.items")\n'
    "query q:\n    from items\n"
    "    where max(a, b) > 1\n"
    "    select:\n"
    "        hi = max(a, b)\n"
    '        word = min(t, "m")\n'
    "        nested = min(a, max(b, 3))\n"
    "        late = max(ts, ts2)\n"
    "        key = min(uu, uu)\n"
    "        both = max(flag, flag)\n"
)


def _extremum(q: str, operator: str, first: str, second: str) -> str:
    a, b = f"{q}{first}{q}", f"{q}{second}{q}"
    return (
        f"CASE WHEN ({b} IS NOT NULL) THEN (CASE WHEN ({a} {operator} {b}) "
        f"THEN {b} ELSE {a} END) ELSE {b} END"
    )


def test_max_and_min_emit_the_conditional_that_is_none_when_either_value_is() -> None:
    # GREATEST and LEAST skip a NULL argument; a None `b` must give NULL.
    parsed = parser_api.parse_source(_EXTREMA.format("postgres"))
    assert parsed.diagnostics == () and parsed.ast is not None
    checked = semantic_api.analyze(parsed.ast)
    assert checked.diagnostics == () and checked.script is not None
    lowered = build_ir(checked.script, checked.model)
    assert lowered.diagnostics == () and lowered.ir is not None
    hi = (
        'CASE WHEN ("b" IS NOT NULL) THEN (CASE WHEN ("a" < "b") '
        'THEN "b" ELSE "a" END) ELSE "b" END'
    )
    inner = '(CASE WHEN ("b" < 3) THEN 3 ELSE "b" END)'
    # Timestamp, UUID and Bool values compare as for `<` here too.
    late = _extremum('"', "<", "ts", "ts2")
    key = _extremum('"', ">", "uu", "uu")
    both = _extremum('"', "<", "flag", "flag")
    assert emit_postgres_sql(lowered.ir).artifacts[0].sql == (
        "SELECT\n"
        f'    {hi} AS "hi",\n'
        '    CASE WHEN ("t" > \'m\') THEN \'m\' ELSE "t" END AS "word",\n'
        f'    CASE WHEN ({inner} IS NOT NULL) THEN (CASE WHEN ("a" > {inner}) '
        f'THEN {inner} ELSE "a" END) ELSE {inner} END AS "nested",\n'
        f'    {late} AS "late",\n'
        f'    {key} AS "key",\n'
        f'    {both} AS "both"\n'
        'FROM "public"."items"\n'
        f"WHERE ({hi}) > 1"
    )


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


def _definition[DefinitionT: (SourceIR, RelationIR)](
    script_ir: ScriptIR,
    definition_type: type[DefinitionT],
    name: str,
) -> DefinitionT:
    return next(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, definition_type) and definition.name == name
    )


def test_scalar_any_in_or_preserves_outer_capture_and_binding() -> None:
    source = """shape Row:
    id: Int
source orders: Row = postgres.table("orders")
source customers: Row = postgres.table("customers")
query result:
    from orders
    where orders.id > 0 or any(buyer.id == orders.id for buyer in customers)
    select id = orders.id
"""
    parsed = parser_api.parse_source(source, path="any-postgres.pietto")
    assert parsed.ast is not None and not parsed.diagnostics
    semantic = semantic_api.analyze(parsed.ast)
    assert semantic.script is not None and not semantic.diagnostics
    lowered = build_ir(semantic.script, semantic.model)
    assert lowered.ir is not None and not lowered.diagnostics
    result = emit_postgres_sql(lowered.ir)
    assert not result.diagnostics
    (artifact,) = result.artifacts
    assert "EXISTS (SELECT 1 FROM " in artifact.sql
    assert " OR " in artifact.sql
    assert '"orders"."id"' in artifact.sql


def test_scalar_any_null_predicate_emits_unknown_filter() -> None:
    parsed = parser_api.parse_source("""shape Row:
    id: Int
source rows: Row = postgres.table("rows")
query result:
    from rows
    select found = any(None for candidate in rows)
""")
    assert parsed.ast is not None and not parsed.diagnostics
    semantic = semantic_api.analyze(parsed.ast)
    assert semantic.script is not None and not semantic.diagnostics
    lowered = build_ir(semantic.script, semantic.model)
    assert lowered.ir is not None and not lowered.diagnostics
    result = emit_postgres_sql(lowered.ir)
    assert not result.diagnostics
    assert " WHERE NULL)" in result.artifacts[0].sql


def test_sql_types_an_always_null_number_as_pietto_types_it() -> None:
    # An untyped NULL takes its type from the database: PostgreSQL types
    # `NULL * 2` as integer and `NULL - 3.0` as numeric, MySQL `amount + NULL`
    # as DOUBLE, so the column type was not the Int or Float Pietto checks.
    # A NULL operand of arithmetic is now a typed NULL, and an always-null
    # number beside a Float result is cast to it; an untyped one stays NULL.
    # Each read of a let-bound `None` is typed as an inline `None` there.
    parsed = parser_api.parse_source(
        "shape Order:\n    id: Int\n    amount: Int\n    price: Decimal(10, 2)\n"
        '    rate: Float\nsource orders: Order = postgres.table("orders")\n'
        "table t0:\n    from orders\n    let k = None\n    select:\n        id\n"
        "        o0 = None - 3.0\n        o1 = amount + None\n"
        "        o2 = None * 2\n        o3 = amount / None\n"
        "        o4 = -(amount + None)\n        o6 = (None + price) + 1.5\n"
        "        o7 = coalesce(None + amount, price)\n        o9 = sign(None + rate)\n"
        "        o10 = (None + amount) if amount > 1 else 1.5\n"
        "        o12 = amount + k\n        o13 = k - 3.0\n"
    )
    assert parsed.ast is not None and not parsed.diagnostics
    semantic = semantic_api.analyze(parsed.ast)
    assert semantic.script is not None
    assert all(d.severity is not Severity.ERROR for d in semantic.diagnostics)
    lowered = build_ir(semantic.script, semantic.model)
    assert lowered.ir is not None and not lowered.diagnostics
    sql = emit_postgres_sql(lowered.ir).artifacts[0].sql
    expected = (
        '"id" AS "id"',
        'CAST(NULL AS double precision) - 3.0 AS "o0"',
        '"amount" + CAST(NULL AS bigint) AS "o1"',
        'CAST(NULL AS bigint) * 2 AS "o2"',
        '"amount" / CAST(NULL AS bigint) AS "o3"',
        '-("amount" + CAST(NULL AS bigint)) AS "o4"',
        'CAST((CAST(NULL AS numeric) + "price") AS double precision) + 1.5 AS "o6"',
        'COALESCE((CAST(NULL AS bigint) + "amount"), "price") AS "o7"',
        'CAST(sign((CAST(NULL AS double precision) + "rate")) AS bigint) AS "o9"',
        'CASE WHEN ("amount" > 1) THEN CAST((CAST(NULL AS bigint) + "amount") '
        'AS double precision) ELSE 1.5 END AS "o10"',
        '"amount" + CAST(NULL AS bigint) AS "o12"',
        'CAST(NULL AS double precision) - 3.0 AS "o13"',
    )
    assert sql == "SELECT\n    " + ",\n    ".join(expected) + '\nFROM "orders"'
