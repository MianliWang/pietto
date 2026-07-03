from __future__ import annotations

from dataclasses import fields

import pytest

from pietto.ast_nodes import BinaryExpr, Script, TableDef
from pietto.errors import Severity
from pietto.ir import (
    AggregateCallIR,
    BinaryIR,
    RelationIR,
    ScriptIR,
    TypeRefIR,
    build_ir,
)
from pietto.parser_api import parse_source
from pietto.semantic import (
    EffectiveNullability,
    ResolvedType,
    SemanticResult,
    ValueType,
    ValueTypeKind,
    analyze,
)
from pietto.sql import SqlResult, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

BASE_SHAPE = (
    "shape Order:\n"
    "    price: Decimal not null\n"
    "    discount: Decimal not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    score: Float not null\n"
    "    status: Text not null\n"
)


def test_decimal_int_add_subtract_scalar_matrix_returns_logical_decimal() -> None:
    script = _parse(
        _source(
            "postgres.table",
            "table projected:\n"
            "    from orders\n"
            "    select:\n"
            "        decimal_plus_int = price + amount\n"
            "        int_plus_decimal = amount + price\n"
            "        decimal_minus_int = price - amount\n"
            "        int_minus_decimal = amount - price\n",
        )
    )
    result = analyze(script)
    relation = _relation_ast(script)

    assert _error_codes(result) == []
    for alias, operator in (
        ("decimal_plus_int", "+"),
        ("int_plus_decimal", "+"),
        ("decimal_minus_int", "-"),
        ("int_minus_decimal", "-"),
    ):
        expression = _select_expression(relation, alias)
        assert isinstance(expression, BinaryExpr)
        assert expression.operator == operator
        field = result.model.relation_row_schemas[relation].fields[alias]
        value_type = result.model.expression_value_types[expression]

        _assert_decimal_unknown(field)
        _assert_decimal_unknown(value_type)


def test_decimal_int_aggregate_expressions_lower_and_render_sql() -> None:
    projections = (
        "total = sum(price + amount)\n"
        "        average = avg(price - amount)\n"
        "        known = count(price + amount)"
    )
    for connector, emitter, expected_fragments in (
        (
            "postgres.table",
            emit_postgres_sql,
            (
                'SUM(("price" + "amount")) AS "total"',
                'AVG(("price" - "amount")) AS "average"',
                'COUNT(("price" + "amount")) AS "known"',
            ),
        ),
        (
            "mysql.table",
            emit_mysql_sql,
            (
                "SUM((`price` + `amount`)) AS `total`",
                "AVG((`price` - `amount`)) AS `average`",
                "COUNT((`price` + `amount`)) AS `known`",
            ),
        ),
    ):
        script, semantic, script_ir = _compile(
            _source(
                connector,
                "table aggregate_stats:\n"
                "    from orders\n"
                "    select:\n"
                f"        {projections}\n",
            )
        )
        relation = _relation_ast(script)
        schema = semantic.model.relation_row_schemas[relation]

        _assert_value_type(schema.fields["total"], "Decimal")
        _assert_value_type(schema.fields["average"], "Decimal")
        assert schema.fields["known"].resolved_type.name == "Int"
        assert schema.fields["known"].nullability is EffectiveNullability.NON_NULL

        projections_by_name = {
            projection.name: projection
            for projection in _relation_ir(script_ir).projections
        }
        for alias, function_name, expected_type in (
            ("total", "sum", "Decimal"),
            ("average", "avg", "Decimal"),
            ("known", "count", "Int"),
        ):
            aggregate = projections_by_name[alias].expression
            assert isinstance(aggregate, AggregateCallIR)
            assert aggregate.function == function_name
            assert aggregate.value_type.canonical_name == expected_type
            assert isinstance(aggregate.arguments[0], BinaryIR)

        sql_result = emitter(script_ir)
        assert sql_result.diagnostics == ()
        sql = _sql_text(sql_result)
        for fragment in expected_fragments:
            assert fragment in sql


@pytest.mark.parametrize(
    "projection",
    [
        "value = price * amount",
        "value = amount * price",
        "value = price * discount",
        "value = score + price",
        "value = price + score",
        "value = price % amount",
    ],
)
def test_decimal_int_multiply_modulo_and_float_decimal_remain_fail_closed(
    projection: str,
) -> None:
    result = analyze(
        _parse(
            _source(
                "postgres.table",
                "table projected:\n"
                "    from orders\n"
                "    select:\n"
                f"        {projection}\n",
            )
        )
    )

    assert _error_codes(result) == ["PIE-S2105"]


def test_decimal_int_division_remains_unknown_without_diagnostic() -> None:
    script = _parse(
        _source(
            "postgres.table",
            "table projected:\n"
            "    from orders\n"
            "    select:\n"
            "        value = price / amount\n",
        )
    )
    result = analyze(script)
    relation = _relation_ast(script)
    expression = _select_expression(relation, "value")

    assert result.diagnostics == ()
    assert result.model.expression_value_types[expression].kind is (
        ValueTypeKind.UNKNOWN
    )


@pytest.mark.parametrize(
    "projection",
    [
        "value = sum(price + 1)",
        "value = sum(price * amount)",
        "value = avg(amount * price)",
        "value = sum(price + score)",
        "value = count_distinct(price + amount)",
        "value = min(price + amount)",
        "value = max(price + amount)",
    ],
)
def test_decimal_int_aggregate_boundaries_remain_fail_closed(
    projection: str,
) -> None:
    result = analyze(
        _parse(
            _source(
                "postgres.table",
                "table aggregate_stats:\n"
                "    from orders\n"
                "    select:\n"
                f"        {projection}\n",
            )
        )
    )

    assert _error_codes(result) == ["PIE-S2315"]


def test_projection_alias_let_and_type_alias_aggregate_arguments_stay_closed() -> None:
    projection_alias = analyze(
        _parse(
            _source(
                "postgres.table",
                "table aggregate_stats:\n"
                "    from orders\n"
                "    select:\n"
                "        subtotal = price + amount\n"
                "        value = sum(subtotal)\n",
            )
        )
    )
    assert "PIE-S2102" in _error_codes(projection_alias)

    let_name = analyze(
        _parse(
            _source(
                "postgres.table",
                "query aggregate_stats:\n"
                "    from orders\n"
                "    let:\n"
                "        gross = price + amount\n"
                "    select:\n"
                "        value = sum(gross)\n",
            )
        )
    )
    assert "PIE-S2102" in _error_codes(let_name)

    type_alias = analyze(
        _parse(
            "type Money = Decimal(12, 2) not null\n"
            "shape Order:\n"
            "    money: Money not null\n"
            'source orders: Order is postgres.table("orders")\n'
            "table aggregate_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        value = sum(money)\n"
        )
    )
    assert "PIE-S2314" in _error_codes(type_alias)


def test_decimal_int_mvp_adds_no_public_precision_scale_fields() -> None:
    for type_surface in (ResolvedType, ValueType, TypeRefIR):
        assert {"precision", "scale"}.isdisjoint(
            {field.name for field in fields(type_surface)}
        )


def _source(connector: str, relation: str) -> str:
    return BASE_SHAPE + f'source orders: Order is {connector}("orders")\n' + relation


def _parse(source: str) -> Script:
    result = parse_source(source, path="phase42_decimal_int.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _compile(source: str) -> tuple[Script, SemanticResult, ScriptIR]:
    script = _parse(source)
    semantic = analyze(script)
    assert _error_codes(semantic) == []
    ir_result = build_ir(script, semantic.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return script, semantic, ir_result.ir


def _relation_ast(script: Script) -> TableDef:
    relation = script.definitions[-1]
    assert isinstance(relation, TableDef)
    return relation


def _relation_ir(script_ir: ScriptIR) -> RelationIR:
    relations = [
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR)
    ]
    assert len(relations) == 1
    return relations[0]


def _select_expression(relation: TableDef, alias: str) -> BinaryExpr:
    for item in relation.select_items:
        if item.alias == alias:
            expression = item.expression
            assert isinstance(expression, BinaryExpr)
            return expression
    raise AssertionError(f"Missing select alias: {alias}")


def _assert_decimal_unknown(value_type: object) -> None:
    _assert_value_type(value_type, "Decimal", EffectiveNullability.UNKNOWN)


def _assert_value_type(
    value_type: object,
    expected_name: str,
    expected_nullability: EffectiveNullability = EffectiveNullability.NULLABLE,
) -> None:
    assert getattr(value_type, "resolved_type").name == expected_name
    assert getattr(value_type, "nullability") is expected_nullability


def _error_codes(result: SemanticResult) -> list[str]:
    return [
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _sql_text(result: SqlResult) -> str:
    return "\n".join(artifact.sql for artifact in result.artifacts)
