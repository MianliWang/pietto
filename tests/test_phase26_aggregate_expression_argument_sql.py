from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.errors import Severity
from pietto.ir import (
    AggregateCallIR,
    BinaryIR,
    CallIR,
    ExpressionIR,
    FieldId,
    FieldRefIR,
    LiteralIR,
    NullabilityIR,
    ProjectionIR,
    RelationIR,
    ScriptIR,
    SourceSpan,
    SymbolId,
    SymbolNamespace,
    TypeKindIR,
    TypeRefIR,
    build_ir,
)
from pietto.ir.model import StaticValue
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.sql import SqlResult, emit_postgres_sql
from pietto.sql.expressions import render_expression_sql
from pietto.sql.mysql import emit_mysql_sql
from pietto.sql.mysql_expressions import render_mysql_expression

SPAN = SourceSpan(
    path="phase26-aggregate-expression-argument-sql.pietto",
    line=1,
    column=1,
    end_line=1,
    end_column=2,
)
OWNER = SymbolId(SymbolNamespace.RELATION, "orders")
INT_NON_NULL = TypeRefIR(
    symbol=SymbolId(SymbolNamespace.TYPE, "Int"),
    canonical_symbol=SymbolId(SymbolNamespace.TYPE, "Int"),
    declared_name="Int",
    canonical_name="Int",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)
INT_NULLABLE = replace(INT_NON_NULL, nullability=NullabilityIR.NULLABLE)
FLOAT_NON_NULL = TypeRefIR(
    symbol=SymbolId(SymbolNamespace.TYPE, "Float"),
    canonical_symbol=SymbolId(SymbolNamespace.TYPE, "Float"),
    declared_name="Float",
    canonical_name="Float",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)
FLOAT_NULLABLE = replace(FLOAT_NON_NULL, nullability=NullabilityIR.NULLABLE)
DECIMAL_NON_NULL = TypeRefIR(
    symbol=SymbolId(SymbolNamespace.TYPE, "Decimal"),
    canonical_symbol=SymbolId(SymbolNamespace.TYPE, "Decimal"),
    declared_name="Decimal",
    canonical_name="Decimal",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)
DECIMAL_NULLABLE = replace(DECIMAL_NON_NULL, nullability=NullabilityIR.NULLABLE)
TEXT_NON_NULL = TypeRefIR(
    symbol=SymbolId(SymbolNamespace.TYPE, "Text"),
    canonical_symbol=SymbolId(SymbolNamespace.TYPE, "Text"),
    declared_name="Text",
    canonical_name="Text",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)
TEXT_UNKNOWN = replace(TEXT_NON_NULL, nullability=NullabilityIR.UNKNOWN)

BASE_SHAPE = (
    "shape Order:\n"
    "    status: Text not null\n"
    "    region: Text not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    score: Float not null\n"
    "    weight: Float not null\n"
    "    price: Decimal not null\n"
)


@pytest.mark.parametrize(
    ("projection", "expected_postgres", "expected_mysql"),
    [
        (
            "total = sum(amount + tax)",
            'SUM(("amount" + "tax"))',
            "SUM((`amount` + `tax`))",
        ),
        (
            "weighted = avg(score * weight)",
            'AVG(("score" * "weight"))',
            "AVG((`score` * `weight`))",
        ),
        (
            "decimal_total = sum(price + price)",
            'SUM(("price" + "price"))',
            "SUM((`price` + `price`))",
        ),
        (
            "decimal_average = avg(price - price)",
            'AVG(("price" - "price"))',
            "AVG((`price` - `price`))",
        ),
        (
            "normalized = count_distinct(lower(status))",
            'COUNT(DISTINCT lower("status"))',
            "COUNT(DISTINCT LOWER(`status`))",
        ),
        (
            "trimmed = count_distinct(trim(status))",
            'COUNT(DISTINCT trim("status"))',
            "COUNT(DISTINCT TRIM(`status`))",
        ),
        (
            "normalized_trimmed = count_distinct(lower(trim(status)))",
            'COUNT(DISTINCT lower(trim("status")))',
            "COUNT(DISTINCT LOWER(TRIM(`status`)))",
        ),
    ],
)
def test_direct_renderers_render_supported_expression_argument_aggregates(
    projection: str,
    expected_postgres: str,
    expected_mysql: str,
) -> None:
    expression = _single_projection_expression(_source("postgres.table", projection))

    assert render_expression_sql(expression) == expected_postgres
    assert render_mysql_expression(expression) == expected_mysql


def test_direct_renderers_preserve_qualified_expression_argument_leaves() -> None:
    relation = _single_relation_ir(
        _source(
            "postgres.table",
            "total = sum(orders.amount + orders.tax)\n"
            "        normalized = count_distinct(lower(orders.status))",
            table_name="physical_orders",
        )
    )
    projections = _projections(relation)

    assert (
        render_expression_sql(projections["total"].expression)
        == 'SUM(("orders"."amount" + "orders"."tax"))'
    )
    assert (
        render_mysql_expression(projections["total"].expression)
        == "SUM((`orders`.`amount` + `orders`.`tax`))"
    )
    assert (
        render_expression_sql(projections["normalized"].expression)
        == 'COUNT(DISTINCT lower("orders"."status"))'
    )
    assert (
        render_mysql_expression(projections["normalized"].expression)
        == "COUNT(DISTINCT LOWER(`orders`.`status`))"
    )


@pytest.mark.parametrize(
    ("case", "expected_postgres", "expected_mysql"),
    [
        (
            "count_star",
            "COUNT(*)",
            "COUNT(*)",
        ),
        (
            "count_field",
            'COUNT("status")',
            "COUNT(`status`)",
        ),
        (
            "count_distinct_field",
            'COUNT(DISTINCT "status")',
            "COUNT(DISTINCT `status`)",
        ),
        (
            "sum_field",
            'SUM("amount")',
            "SUM(`amount`)",
        ),
        (
            "avg_field",
            'AVG("score")',
            "AVG(`score`)",
        ),
        (
            "min_field",
            'MIN("amount")',
            "MIN(`amount`)",
        ),
        (
            "max_field",
            'MAX("score")',
            "MAX(`score`)",
        ),
    ],
)
def test_direct_field_aggregate_renderer_sql_remains_byte_exact(
    case: str,
    expected_postgres: str,
    expected_mysql: str,
) -> None:
    aggregate = _direct_field_aggregate(case)

    assert render_expression_sql(aggregate) == expected_postgres
    assert render_mysql_expression(aggregate) == expected_mysql


@pytest.mark.parametrize(
    ("connector", "emitter", "expected_sql"),
    [
        (
            "postgres.table",
            emit_postgres_sql,
            "SELECT\n"
            '    SUM(("amount" + "tax")) AS "total",\n'
            '    AVG(("score" * "weight")) AS "weighted",\n'
            '    SUM(("price" + "price")) AS "decimal_total",\n'
            '    AVG(("price" - "price")) AS "decimal_average",\n'
            '    COUNT(DISTINCT lower("status")) AS "normalized"\n'
            'FROM "orders"',
        ),
        (
            "mysql.table",
            emit_mysql_sql,
            "SELECT\n"
            "    SUM((`amount` + `tax`)) AS `total`,\n"
            "    AVG((`score` * `weight`)) AS `weighted`,\n"
            "    SUM((`price` + `price`)) AS `decimal_total`,\n"
            "    AVG((`price` - `price`)) AS `decimal_average`,\n"
            "    COUNT(DISTINCT LOWER(`status`)) AS `normalized`\n"
            "FROM `orders`",
        ),
    ],
)
def test_backends_emit_no_group_aggregate_expression_argument_sql(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
    expected_sql: str,
) -> None:
    script_ir = _compile(
        _source(
            connector,
            "total = sum(amount + tax)\n"
            "        weighted = avg(score * weight)\n"
            "        decimal_total = sum(price + price)\n"
            "        decimal_average = avg(price - price)\n"
            "        normalized = count_distinct(lower(status))",
        )
    )

    result = emitter(script_ir)

    assert result.diagnostics == ()
    assert len(result.artifacts) == 1
    assert result.artifacts[0].sql == expected_sql


@pytest.mark.parametrize(
    ("connector", "emitter", "expected_sql"),
    [
        (
            "postgres.table",
            emit_postgres_sql,
            "SELECT\n"
            '    "region" AS "region",\n'
            '    SUM(("amount" + "tax")) AS "total",\n'
            '    COUNT(DISTINCT lower(trim("status"))) AS "normalized"\n'
            'FROM "orders"\n'
            "GROUP BY\n"
            '    "region"',
        ),
        (
            "mysql.table",
            emit_mysql_sql,
            "SELECT\n"
            "    `region` AS `region`,\n"
            "    SUM((`amount` + `tax`)) AS `total`,\n"
            "    COUNT(DISTINCT LOWER(TRIM(`status`))) AS `normalized`\n"
            "FROM `orders`\n"
            "GROUP BY\n"
            "    `region`",
        ),
    ],
)
def test_backends_emit_grouped_aggregate_expression_argument_sql(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
    expected_sql: str,
) -> None:
    script_ir = _compile(
        _source(
            connector,
            "region\n"
            "        total = sum(amount + tax)\n"
            "        normalized = count_distinct(lower(trim(status)))",
            grouped=True,
        )
    )

    result = emitter(script_ir)

    assert result.diagnostics == ()
    assert len(result.artifacts) == 1
    assert result.artifacts[0].sql == expected_sql


@pytest.mark.parametrize(
    ("connector", "emitter", "expected_sql", "forbidden_alias"),
    [
        (
            "postgres.table",
            emit_postgres_sql,
            "SELECT\n"
            '    "region" AS "region",\n'
            '    SUM(("amount" + "tax")) AS "total"\n'
            'FROM "orders"\n'
            "GROUP BY\n"
            '    "region"\n'
            "HAVING\n"
            '    SUM(("amount" + "tax")) > 1000',
            '"total" > 1000',
        ),
        (
            "mysql.table",
            emit_mysql_sql,
            "SELECT\n"
            "    `region` AS `region`,\n"
            "    SUM((`amount` + `tax`)) AS `total`\n"
            "FROM `orders`\n"
            "GROUP BY\n"
            "    `region`\n"
            "HAVING\n"
            "    SUM((`amount` + `tax`)) > 1000",
            "`total` > 1000",
        ),
    ],
)
def test_grouped_satisfying_uses_underlying_aggregate_expression_not_alias(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
    expected_sql: str,
    forbidden_alias: str,
) -> None:
    script_ir = _compile(
        _source(
            connector,
            "region\n        total = sum(amount + tax)",
            grouped=True,
            satisfying="total > 1000",
        )
    )

    result = emitter(script_ir)

    assert result.diagnostics == ()
    assert len(result.artifacts) == 1
    assert result.artifacts[0].sql == expected_sql
    assert forbidden_alias not in result.artifacts[0].sql


@pytest.mark.parametrize(
    ("connector", "emitter", "expected_sql"),
    [
        (
            "postgres.table",
            emit_postgres_sql,
            "SELECT\n"
            '    SUM(("orders"."amount" + "orders"."tax")) AS "total",\n'
            '    COUNT(DISTINCT lower("orders"."status")) AS "normalized"\n'
            'FROM "physical_orders" AS "orders"',
        ),
        (
            "mysql.table",
            emit_mysql_sql,
            "SELECT\n"
            "    SUM((`orders`.`amount` + `orders`.`tax`)) AS `total`,\n"
            "    COUNT(DISTINCT LOWER(`orders`.`status`)) AS `normalized`\n"
            "FROM `physical_orders` AS `orders`",
        ),
    ],
)
def test_backends_preserve_source_aliases_for_qualified_expression_leaves(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
    expected_sql: str,
) -> None:
    script_ir = _compile(
        _source(
            connector,
            "total = sum(orders.amount + orders.tax)\n"
            "        normalized = count_distinct(lower(orders.status))",
            table_name="physical_orders",
        )
    )

    result = emitter(script_ir)

    assert result.diagnostics == ()
    assert len(result.artifacts) == 1
    assert result.artifacts[0].sql == expected_sql


@pytest.mark.parametrize(
    ("dialect", "connector", "projection", "expected_sql"),
    [
        (
            "postgres",
            "postgres.table",
            "total = sum(amount + tax)",
            'SELECT\n    SUM(("amount" + "tax")) AS "total"\nFROM "orders"',
        ),
        (
            "postgres",
            "postgres.table",
            "normalized = count_distinct(lower(status))",
            "SELECT\n"
            '    COUNT(DISTINCT lower("status")) AS "normalized"\n'
            'FROM "orders"',
        ),
        (
            "mysql",
            "mysql.table",
            "total = sum(amount + tax)",
            "SELECT\n    SUM((`amount` + `tax`)) AS `total`\nFROM `orders`",
        ),
        (
            "mysql",
            "mysql.table",
            "normalized = count_distinct(lower(status))",
            "SELECT\n"
            "    COUNT(DISTINCT LOWER(`status`)) AS `normalized`\n"
            "FROM `orders`",
        ),
    ],
)
def test_cli_text_emits_supported_expression_argument_sql(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    dialect: str,
    connector: str,
    projection: str,
    expected_sql: str,
) -> None:
    path = _write(
        tmp_path,
        f"{dialect}-aggregate-expression.pietto",
        _source(connector, projection),
    )

    assert cli.main(["emit-sql", str(path), "--dialect", dialect]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == expected_sql + "\n"


@pytest.mark.parametrize(
    ("dialect", "connector", "projection", "expected_sql"),
    [
        (
            "postgres",
            "postgres.table",
            "total = sum(amount + tax)",
            'SELECT\n    SUM(("amount" + "tax")) AS "total"\nFROM "orders"',
        ),
        (
            "postgres",
            "postgres.table",
            "normalized = count_distinct(lower(status))",
            "SELECT\n"
            '    COUNT(DISTINCT lower("status")) AS "normalized"\n'
            'FROM "orders"',
        ),
        (
            "mysql",
            "mysql.table",
            "total = sum(amount + tax)",
            "SELECT\n    SUM((`amount` + `tax`)) AS `total`\nFROM `orders`",
        ),
        (
            "mysql",
            "mysql.table",
            "normalized = count_distinct(lower(status))",
            "SELECT\n"
            "    COUNT(DISTINCT LOWER(`status`)) AS `normalized`\n"
            "FROM `orders`",
        ),
    ],
)
def test_cli_json_output_writes_supported_expression_argument_sql(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    dialect: str,
    connector: str,
    projection: str,
    expected_sql: str,
) -> None:
    path = _write(
        tmp_path,
        f"{dialect}-aggregate-expression.pietto",
        _source(connector, projection),
    )
    output_path = tmp_path / f"{dialect}.sql"

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                dialect,
                "--format",
                "json",
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    result = _read_json(capsys)
    artifacts = cast(list[dict[str, object]], result["artifacts"])

    assert result["ok"] is True
    assert result["diagnostics"] == []
    assert result["cli_errors"] == []
    assert result["output"] == {"path": str(output_path), "written": True}
    assert artifacts == [
        {
            "kind": "relation",
            "name": "aggregate_stats",
            "sql": expected_sql,
        }
    ]
    assert output_path.read_text(encoding="utf-8") == expected_sql + "\n"


@pytest.mark.parametrize(
    ("projection", "expected_code"),
    [
        ("value = sum(amount / tax)", "PIE-S2315"),
        ("value = sum(amount % tax)", "PIE-S2315"),
        ("value = avg(price * price)", "PIE-S2315"),
        ("value = count_distinct(len(status))", "PIE-S2315"),
        ("value = count_distinct(lower(amount))", "PIE-S2315"),
        # Phase 39 Slice 3 accepts "value = count(amount + tax)" semantically.
        ("value = count(1)", "PIE-S2315"),
        ("value = min(amount + tax)", "PIE-S2315"),
        ("value = max(score * weight)", "PIE-S2315"),
        ("value = sum(avg(amount))", "PIE-S2311"),
        ("value = sum(amount) + 1", "PIE-S2310"),
    ],
)
def test_unsupported_semantic_shapes_stop_before_sql_without_artifacts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    projection: str,
    expected_code: str,
) -> None:
    output_path = tmp_path / "unsupported.sql"
    path = _write(tmp_path, "unsupported.pietto", _source("postgres.table", projection))

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format",
                "json",
                "--output",
                str(output_path),
            ]
        )
        == 1
    )

    result = _read_json(capsys)
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])
    codes = [diagnostic["code"] for diagnostic in diagnostics]

    assert result["ok"] is False
    assert codes == [expected_code]
    assert "PIE-B1000" not in codes
    assert result["artifacts"] == []
    assert result["output"] == {"path": str(output_path), "written": False}
    assert not output_path.exists()


@pytest.mark.parametrize(
    ("connector", "emitter"),
    [
        ("postgres.table", emit_postgres_sql),
        ("mysql.table", emit_mysql_sql),
    ],
)
@pytest.mark.parametrize(
    "case",
    [
        "sum_literal_argument",
        "sum_arbitrary_call_argument",
        "count_distinct_binary_argument",
        "count_division_argument",
        "min_expression_argument",
        "max_expression_argument",
        "decimal_multiplication_argument",
        "mixed_decimal_int_argument",
    ],
)
def test_malformed_hand_built_aggregate_expression_ir_fails_closed_with_pie_b1000(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
    case: str,
) -> None:
    script_ir = _compile(_source(connector, "total = sum(amount)"))
    relation = _single_relation(script_ir)
    projection = relation.projections[0]
    bad_relation = replace(
        relation,
        projections=(replace(projection, expression=_malformed_aggregate(case)),),
    )
    definitions = tuple(
        bad_relation if definition is relation else definition
        for definition in script_ir.definitions
    )

    result = emitter(ScriptIR(definitions=definitions))

    assert result.artifacts == ()
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code == "PIE-B1000"
    assert result.diagnostics[0].severity is Severity.ERROR


def _source(
    connector: str,
    select_body: str,
    *,
    table_name: str = "orders",
    grouped: bool = False,
    satisfying: str | None = None,
) -> str:
    group_block = "    group by:\n        region\n" if grouped else ""
    satisfying_block = (
        f"    satisfying:\n        {satisfying}\n" if satisfying is not None else ""
    )
    return (
        BASE_SHAPE + f'source orders: Order is {connector}("{table_name}")\n'
        "table aggregate_stats:\n"
        "    from orders\n"
        f"{group_block}"
        "    select:\n"
        f"        {select_body}\n"
        f"{satisfying_block}"
    )


def _single_projection_expression(source: str) -> ExpressionIR:
    relation = _single_relation_ir(source)
    assert len(relation.projections) == 1
    return relation.projections[0].expression


def _single_relation_ir(source: str) -> RelationIR:
    return _single_relation(_compile(source))


def _compile(source: str) -> ScriptIR:
    parse_result = parse_source(source)
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


def _single_relation(script_ir: ScriptIR) -> RelationIR:
    relations = [
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR)
    ]
    assert len(relations) == 1
    return relations[0]


def _projections(relation: RelationIR) -> dict[str, ProjectionIR]:
    return {str(projection.name): projection for projection in relation.projections}


def _malformed_aggregate(case: str) -> AggregateCallIR:
    amount = _field("amount", INT_NON_NULL)
    tax = _field("tax", INT_NON_NULL)
    price = _field("price", DECIMAL_NON_NULL)
    status = _field("status", TEXT_NON_NULL)

    if case == "sum_literal_argument":
        return _aggregate("sum", INT_NULLABLE, _literal(1, INT_NON_NULL))
    if case == "sum_arbitrary_call_argument":
        return _aggregate("sum", INT_NULLABLE, _call("lower", TEXT_UNKNOWN, status))
    if case == "count_distinct_binary_argument":
        return _aggregate(
            "count_distinct",
            INT_NON_NULL,
            _binary(
                _call("lower", TEXT_UNKNOWN, status),
                "+",
                _call("trim", TEXT_UNKNOWN, status),
                TEXT_UNKNOWN,
            ),
        )
    if case == "count_division_argument":
        return _aggregate(
            "count", INT_NON_NULL, _binary(amount, "/", tax, INT_NON_NULL)
        )
    if case == "min_expression_argument":
        return _aggregate("min", INT_NULLABLE, _binary(amount, "+", tax, INT_NON_NULL))
    if case == "max_expression_argument":
        return _aggregate("max", INT_NULLABLE, _binary(amount, "+", tax, INT_NON_NULL))
    if case == "decimal_multiplication_argument":
        return _aggregate(
            "sum",
            DECIMAL_NULLABLE,
            _binary(price, "*", price, DECIMAL_NON_NULL),
        )
    if case == "mixed_decimal_int_argument":
        return _aggregate(
            "sum",
            DECIMAL_NULLABLE,
            _binary(price, "+", amount, DECIMAL_NON_NULL),
        )
    raise AssertionError(f"Unknown malformed aggregate case: {case}")


def _direct_field_aggregate(case: str) -> AggregateCallIR:
    if case == "count_star":
        return _aggregate("count", INT_NON_NULL)
    if case == "count_field":
        return _aggregate("count", INT_NON_NULL, _field("status", TEXT_NON_NULL))
    if case == "count_distinct_field":
        return _aggregate(
            "count_distinct",
            INT_NON_NULL,
            _field("status", TEXT_NON_NULL),
        )
    if case == "sum_field":
        return _aggregate("sum", INT_NULLABLE, _field("amount", INT_NON_NULL))
    if case == "avg_field":
        return _aggregate("avg", FLOAT_NULLABLE, _field("score", FLOAT_NON_NULL))
    if case == "min_field":
        return _aggregate("min", INT_NULLABLE, _field("amount", INT_NON_NULL))
    if case == "max_field":
        return _aggregate("max", FLOAT_NULLABLE, _field("score", FLOAT_NON_NULL))
    raise AssertionError(f"Unknown direct aggregate case: {case}")


def _aggregate(
    function: str,
    value_type: TypeRefIR,
    *arguments: ExpressionIR,
) -> AggregateCallIR:
    return AggregateCallIR(
        span=SPAN,
        value_type=value_type,
        function=function,
        arguments=arguments,
    )


def _field(
    name: str,
    value_type: TypeRefIR,
    *,
    qualifier: tuple[str, ...] = (),
    resolved: bool = True,
) -> FieldRefIR:
    return FieldRefIR(
        span=SPAN,
        value_type=value_type,
        name=name,
        qualifier=qualifier,
        field=FieldId(owner=OWNER, name=name) if resolved else None,
    )


def _literal(value: StaticValue, value_type: TypeRefIR) -> LiteralIR:
    return LiteralIR(span=SPAN, value_type=value_type, value=value)


def _call(
    callee: str,
    value_type: TypeRefIR,
    *arguments: ExpressionIR,
) -> CallIR:
    return CallIR(
        span=SPAN,
        value_type=value_type,
        callee=callee,
        callee_symbol=SymbolId(SymbolNamespace.CALLABLE, callee),
        arguments=arguments,
    )


def _binary(
    left: ExpressionIR,
    operator: str,
    right: ExpressionIR,
    value_type: TypeRefIR,
) -> BinaryIR:
    return BinaryIR(
        span=SPAN,
        value_type=value_type,
        left=left,
        operator=operator,
        right=right,
    )


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _read_json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.startswith("{")
    return cast(dict[str, object], json.loads(captured.out))
