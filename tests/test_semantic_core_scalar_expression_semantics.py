from __future__ import annotations

from pathlib import Path

import pytest

from pietto.ast_nodes import (
    BetweenExpr,
    BinaryExpr,
    Expression,
    SelectItem,
    Script,
    TableDef,
    UnaryExpr,
)
from pietto.errors import Diagnostic, Severity
from pietto.ir import BinaryIR, RelationIR, ScriptIR, TypeKindIR, UnaryIR, build_ir
from pietto.parser_api import parse_source
from pietto.semantic import (
    EffectiveNullability,
    SemanticResult,
    ValueTypeKind,
    analyze,
)
from pietto.sql import emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PREFIX = (
    "shape Row:\n"
    "    text: Text not null\n"
    "    count: Int not null\n"
    "    active: Bool not null\n"
    'source rows: Row is postgres.table("rows")\n'
    'source mysql_rows: Row is mysql.table("rows")\n'
)


def test_boolean_binary_where_resolves_to_known_bool() -> None:
    script, semantic, _ = _compile(
        SOURCE_PREFIX + "table filtered:\n"
        "    from rows\n"
        "    where count > 1 and active == true\n"
        "    select:\n"
        "        text\n"
    )
    expression = _where_expression(script)

    value_type = semantic.model.expression_value_types[expression]

    assert isinstance(expression, BinaryExpr)
    assert value_type.resolved_type.name == "Bool"
    assert value_type.kind is ValueTypeKind.KNOWN
    assert value_type.nullability is EffectiveNullability.UNKNOWN


def test_between_where_resolves_to_known_bool() -> None:
    script, semantic, _ = _compile(
        SOURCE_PREFIX + "table filtered:\n"
        "    from rows\n"
        "    where count between 1 and 5\n"
        "    select:\n"
        "        text\n"
    )
    expression = _where_expression(script)

    value_type = semantic.model.expression_value_types[expression]

    assert isinstance(expression, BetweenExpr)
    assert value_type.resolved_type.name == "Bool"
    assert value_type.kind is ValueTypeKind.KNOWN
    assert value_type.nullability is EffectiveNullability.UNKNOWN


def test_invalid_bool_binary_reports_s2105_at_full_span() -> None:
    parse_result = parse_source(
        SOURCE_PREFIX + "table filtered:\n"
        "    from rows\n"
        "    where text and true\n"
        "    select:\n"
        "        text\n",
        path="scalar.pietto",
    )
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None
    expression = _where_expression(parse_result.ast)

    semantic = analyze(parse_result.ast)

    assert _diagnostics(semantic) == [
        (
            "PIE-S2105",
            "Invalid operands for operator and: expected Bool operands",
        )
    ]
    _assert_diagnostic_span(semantic.diagnostics[0], expression)


def test_int_arithmetic_projection_has_semantic_and_ir_type() -> None:
    script, semantic, script_ir = _compile(
        SOURCE_PREFIX + "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        value = count + 1\n"
    )
    expression = _select_expression(script, 0)

    semantic_type = semantic.model.expression_value_types[expression]
    ir_expression = _relation_ir(script_ir).projections[0].expression

    assert isinstance(expression, BinaryExpr)
    assert semantic_type.resolved_type.name == "Int"
    assert semantic_type.nullability is EffectiveNullability.UNKNOWN
    assert isinstance(ir_expression, BinaryIR)
    assert ir_expression.value_type.canonical_name == "Int"
    assert ir_expression.value_type.canonical_kind is TypeKindIR.BUILTIN


def test_mixed_numeric_projection_promotes_to_float() -> None:
    script, semantic, script_ir = _compile(
        SOURCE_PREFIX + "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        value = count + 1.5\n"
    )
    expression = _select_expression(script, 0)

    semantic_type = semantic.model.expression_value_types[expression]
    ir_expression = _relation_ir(script_ir).projections[0].expression

    assert isinstance(expression, BinaryExpr)
    assert semantic_type.resolved_type.name == "Float"
    assert isinstance(ir_expression, BinaryIR)
    assert ir_expression.value_type.canonical_name == "Float"


def test_unary_numeric_projection_preserves_type_and_nullability() -> None:
    script, semantic, script_ir = _compile(
        SOURCE_PREFIX + "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        value = -count\n"
    )
    expression = _select_expression(script, 0)

    semantic_type = semantic.model.expression_value_types[expression]
    ir_expression = _relation_ir(script_ir).projections[0].expression

    assert isinstance(expression, UnaryExpr)
    assert semantic_type.resolved_type.name == "Int"
    assert semantic_type.nullability is EffectiveNullability.NON_NULL
    assert isinstance(ir_expression, UnaryIR)
    assert ir_expression.value_type.canonical_name == "Int"
    assert ir_expression.value_type.nullability.value == "non_null"


def test_modulo_projection_requires_int_and_returns_int() -> None:
    script, semantic, script_ir = _compile(
        SOURCE_PREFIX + "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        value = count % 2\n"
    )
    expression = _select_expression(script, 0)

    semantic_type = semantic.model.expression_value_types[expression]
    ir_expression = _relation_ir(script_ir).projections[0].expression

    assert isinstance(expression, BinaryExpr)
    assert semantic_type.resolved_type.name == "Int"
    assert isinstance(ir_expression, BinaryIR)
    assert ir_expression.value_type.canonical_name == "Int"


def test_invalid_arithmetic_reports_s2105() -> None:
    parse_result = parse_source(
        SOURCE_PREFIX + "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        value = text + 1\n",
        path="scalar.pietto",
    )
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic = analyze(parse_result.ast)
    expression = _select_expression(parse_result.ast, 0)

    assert _diagnostics(semantic) == [
        (
            "PIE-S2105",
            "Invalid operands for operator +: expected numeric operands",
        )
    ]
    _assert_diagnostic_span(semantic.diagnostics[0], expression)


@pytest.mark.parametrize(
    "body",
    [
        "    select:\n        value = missing + 1\n",
        "    where missing and true\n    select:\n        text\n",
        "    where missing between 1 and 5\n    select:\n        text\n",
    ],
)
def test_unknown_children_suppress_s2105_cascades(body: str) -> None:
    parse_result = parse_source(
        SOURCE_PREFIX + "table validated:\n    from rows\n" + body,
    )
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic = analyze(parse_result.ast)

    assert _diagnostics(semantic) == [("PIE-S2102", "Unknown field: missing")]
    assert "PIE-S2105" not in [diagnostic.code for diagnostic in semantic.diagnostics]


@pytest.mark.parametrize(
    ("value", "type_name", "postgres_sql", "mysql_sql"),
    [
        ("n / m", "Int", '"n" / "m"', "`n` DIV `m`"),
        ("n / f", "Float", '"n" / "f"', "`n` / `f`"),
        ("f / n", "Float", '"f" / "n"', "`f` / `n`"),
        ("f / g", "Float", '"f" / "g"', "`f` / `g`"),
        ("age / 2", "Int", '"age" / 2', "`age` DIV 2"),
        ("ratio / 2", "Float", '"ratio" / 2', "`ratio` / 2"),
        ("n * 1.0 / m", "Float", '("n" * 1.0) / "m"', "(`n` * 1.0) / `m`"),
        (
            "cast(n as Float) / m",
            "Float",
            '(CAST("n" AS double precision)) / "m"',
            "(CAST(`n` AS DOUBLE)) / `m`",
        ),
    ],
    ids=(
        "int-int",
        "int-float",
        "float-int",
        "float-float",
        "int-alias",
        "float-alias",
        "times-one",
        "cast-float",
    ),
)
def test_division_follows_sql_and_never_inserts_a_cast(
    value: str,
    type_name: str,
    postgres_sql: str,
    mysql_sql: str,
) -> None:
    def source(connector: str) -> str:
        return (
            "type Age = Int not null\n"
            "type Ratio = Float not null\n"
            "shape Row:\n"
            "    n: Int not null\n"
            "    m: Int not null\n"
            "    f: Float not null\n"
            "    g: Float not null\n"
            "    age: Age not null\n"
            "    ratio: Ratio not null\n"
            f'source rows: Row is {connector}.table("rows")\n'
            "table divided:\n"
            "    from rows\n"
            "    select:\n"
            f"        value = {value}\n"
        )

    script, semantic, postgres_ir = _compile(source("postgres"))
    _, _, mysql_ir = _compile(source("mysql"))
    value_type = semantic.model.expression_value_types[_select_expression(script, 0)]

    # Int / Int truncates toward zero as SQL does: PostgreSQL keeps its bare
    # `/` (unchanged bytes) and MySQL, whose `/` gives DECIMAL, emits DIV.
    assert semantic.diagnostics == ()
    assert value_type.kind is ValueTypeKind.KNOWN
    assert value_type.resolved_type.name == type_name
    assert emit_postgres_sql(postgres_ir).artifacts[0].sql == (
        f'SELECT\n    {postgres_sql} AS "value"\nFROM "rows"'
    )
    assert emit_mysql_sql(mysql_ir).artifacts[0].sql == (
        f"SELECT\n    {mysql_sql} AS `value`\nFROM `rows`"
    )


def test_decimal_division_keeps_its_deferred_type_and_bare_sql() -> None:
    # Byte-identical to main; Decimal division awaits a decision.
    body = (
        "    select:\n"
        "        dd = d / e\n"
        "        di = d / n\n"
        "        id = n / d\n"
        "        df = d / f\n"
        "        fd = f / d\n"
    )
    shape = (
        "shape Money:\n"
        "    n: Int not null\n"
        "    f: Float not null\n"
        "    d: Decimal(10, 2) not null\n"
        "    e: Decimal(12, 4) nullable\n"
    )
    columns = ("dd", "di", "id", "df", "fd")
    expected = ("d / e", "d / n", "n / d", "d / f", "f / d")
    for connector, emitter, quote in (
        ("postgres", emit_postgres_sql, '"'),
        ("mysql", emit_mysql_sql, "`"),
    ):
        script, semantic, script_ir = _compile(
            shape
            + f'source money: Money is {connector}.table("money")\n'
            + "table divided:\n    from money\n"
            + body
        )
        assert semantic.diagnostics == ()
        assert all(
            semantic.model.expression_value_types[_select_expression(script, i)].kind
            is ValueTypeKind.UNKNOWN
            for i in range(len(columns))
        )
        sql = emitter(script_ir).artifacts[0].sql
        for column, division in zip(columns, expected, strict=True):
            left, right = division.split(" / ")
            assert (
                f"    {quote}{left}{quote} / {quote}{right}{quote} "
                f"AS {quote}{column}{quote}"
            ) in sql


@pytest.mark.parametrize(
    "value", ["text / 2", "count / active", "(count / 2) and active"]
)
def test_division_of_non_numeric_operands_reports_s2105(value: str) -> None:
    semantic = analyze(
        _parse(
            SOURCE_PREFIX
            + "table projected:\n    from rows\n    select:\n"
            + f"        value = {value}\n"
        )
    )

    assert [code for code, _ in _diagnostics(semantic)] == ["PIE-S2105"]


def test_existing_unqualified_sql_bytes_remain_stable() -> None:
    _, _, script_ir = _compile(
        SOURCE_PREFIX + "table selected:\n    from rows\n    select:\n        text\n"
    )

    postgres = emit_postgres_sql(script_ir)
    mysql = emit_mysql_sql(
        _compile(
            SOURCE_PREFIX + "table selected:\n"
            "    from mysql_rows\n"
            "    select:\n"
            "        text\n"
        )[2]
    )

    assert postgres.diagnostics == ()
    assert postgres.artifacts[0].sql == 'SELECT\n    "text" AS "text"\nFROM "rows"'
    assert mysql.diagnostics == ()
    assert mysql.artifacts[0].sql == "SELECT\n    `text` AS `text`\nFROM `rows`"


def test_qualified_sql_bytes_from_slice1_remain_stable() -> None:
    _, _, postgres_ir = _compile(
        SOURCE_PREFIX + "table selected:\n"
        "    from rows\n"
        "    where rows.active == true\n"
        "    select:\n"
        "        rows.text\n"
    )
    _, _, mysql_ir = _compile(
        SOURCE_PREFIX + "table selected:\n"
        "    from mysql_rows\n"
        "    where mysql_rows.active == true\n"
        "    select:\n"
        "        mysql_rows.text\n"
    )

    postgres = emit_postgres_sql(postgres_ir)
    mysql = emit_mysql_sql(mysql_ir)

    assert postgres.diagnostics == ()
    assert postgres.artifacts[0].sql == (
        'SELECT\n    "rows"."text" AS "text"\nFROM "rows" AS "rows"\n'
        'WHERE "rows"."active" = TRUE'
    )
    assert mysql.diagnostics == ()
    assert mysql.artifacts[0].sql == (
        "SELECT\n    `mysql_rows`.`text` AS `text`\n"
        "FROM `rows` AS `mysql_rows`\n"
        "WHERE `mysql_rows`.`active` = TRUE"
    )


def test_relationship_metadata_does_not_participate_in_scalar_expression_binding() -> (
    None
):
    script, semantic, _ = _compile(
        SOURCE_PREFIX + "relationship membership:\n"
        "    endpoint member: rows\n"
        "    endpoint group: rows\n"
        "table selected:\n"
        "    from rows\n"
        "    where count > 1 and active == true\n"
        "    select:\n"
        "        value = count % 2\n"
    )

    assert len(semantic.model.relationships) == 1
    assert semantic.model.expression_value_types[
        _where_expression(script)
    ].resolved_type.name == ("Bool")
    assert semantic.model.expression_value_types[
        _select_expression(script, 0)
    ].resolved_type.name == ("Int")


def _compile(source: str) -> tuple[Script, SemanticResult, ScriptIR]:
    script = _parse(source)
    semantic = analyze(script)
    assert all(
        diagnostic.severity is not Severity.ERROR for diagnostic in semantic.diagnostics
    )
    ir_result = build_ir(script, semantic.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return script, semantic, ir_result.ir


def _parse(source: str) -> Script:
    parse_result = parse_source(source)
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None
    return parse_result.ast


def _relation(script: Script) -> TableDef:
    relation = script.definitions[-1]
    assert isinstance(relation, TableDef)
    return relation


def _relation_ir(script_ir: ScriptIR) -> RelationIR:
    return next(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR)
    )


def _where_expression(script: Script) -> Expression:
    relation = _relation(script)
    assert relation.where_clause is not None
    return relation.where_clause.expression


def _select_expression(script: Script, index: int) -> Expression:
    item = _relation(script).select_items[index]
    assert isinstance(item, SelectItem)
    return item.expression


def _diagnostics(result: SemanticResult) -> list[tuple[str, str]]:
    return [
        (diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _assert_diagnostic_span(diagnostic: Diagnostic, expression: Expression) -> None:
    assert diagnostic.location.path == expression.span.path
    assert diagnostic.location.line == expression.span.line
    assert diagnostic.location.column == expression.span.column
    assert diagnostic.location.end_line == expression.span.end_line
    assert diagnostic.location.end_column == expression.span.end_column
