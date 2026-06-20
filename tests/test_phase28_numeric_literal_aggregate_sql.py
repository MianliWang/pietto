from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

import pytest

import pietto.sql as sql_api
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
    path="phase28-numeric-literal-aggregate-sql.pietto",
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
BOOL_NON_NULL = TypeRefIR(
    symbol=SymbolId(SymbolNamespace.TYPE, "Bool"),
    canonical_symbol=SymbolId(SymbolNamespace.TYPE, "Bool"),
    declared_name="Bool",
    canonical_name="Bool",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)

BASE_SHAPE = (
    "shape Order:\n"
    "    region: Text not null\n"
    "    status: Text not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    score: Float not null\n"
    "    weight: Float not null\n"
    "    price: Decimal not null\n"
    "    discount: Decimal not null\n"
    "    active: Bool not null\n"
)


@pytest.mark.parametrize(
    ("projection", "expected_postgres", "expected_mysql"),
    [
        (
            "total = sum(amount + 1)",
            'SUM(("amount" + 1))',
            "SUM((`amount` + 1))",
        ),
        (
            "total = sum(1 + amount)",
            'SUM((1 + "amount"))',
            "SUM((1 + `amount`))",
        ),
        (
            "total = sum(amount - 1)",
            'SUM(("amount" - 1))',
            "SUM((`amount` - 1))",
        ),
        (
            "total = sum(amount * 2)",
            'SUM(("amount" * 2))',
            "SUM((`amount` * 2))",
        ),
        (
            "average = avg(score * 2)",
            'AVG(("score" * 2))',
            "AVG((`score` * 2))",
        ),
        (
            "average = avg(score + 1.5)",
            'AVG(("score" + 1.5))',
            "AVG((`score` + 1.5))",
        ),
    ],
)
def test_direct_renderers_render_numeric_literal_aggregate_arguments(
    projection: str,
    expected_postgres: str,
    expected_mysql: str,
) -> None:
    expression = _single_projection_expression(_source("postgres.table", projection))

    assert render_expression_sql(expression) == expected_postgres
    assert render_mysql_expression(expression) == expected_mysql


def test_direct_renderers_render_qualified_and_unary_literal_aggregate_arguments() -> (
    None
):
    relation = _single_relation_ir(
        _source(
            "postgres.table",
            "qualified = sum(orders.amount + 1)\n"
            "        unary_total = sum(+orders.amount + 1)\n"
            "        unary_average = avg(-orders.score + 1.5)",
            table_name="physical_orders",
        )
    )
    projections = _projections(relation)

    assert (
        render_expression_sql(projections["qualified"].expression)
        == 'SUM(("orders"."amount" + 1))'
    )
    assert (
        render_mysql_expression(projections["qualified"].expression)
        == "SUM((`orders`.`amount` + 1))"
    )
    assert (
        render_expression_sql(projections["unary_total"].expression)
        == 'SUM(((+"orders"."amount") + 1))'
    )
    assert (
        render_mysql_expression(projections["unary_total"].expression)
        == "SUM(((+`orders`.`amount`) + 1))"
    )
    assert (
        render_expression_sql(projections["unary_average"].expression)
        == 'AVG(((-"orders"."score") + 1.5))'
    )
    assert (
        render_mysql_expression(projections["unary_average"].expression)
        == "AVG(((-`orders`.`score`) + 1.5))"
    )


@pytest.mark.parametrize(
    ("connector", "emitter", "expected_sql"),
    [
        (
            "postgres.table",
            emit_postgres_sql,
            "SELECT\n"
            '    SUM(("amount" + 1)) AS "plus_total",\n'
            '    SUM((1 + "amount")) AS "left_literal_total",\n'
            '    SUM(("amount" - 1)) AS "minus_total",\n'
            '    SUM(("amount" * 2)) AS "multiplied_total",\n'
            '    AVG(("score" * 2)) AS "weighted_average",\n'
            '    AVG(("score" + 1.5)) AS "adjusted_average"\n'
            'FROM "orders"',
        ),
        (
            "mysql.table",
            emit_mysql_sql,
            "SELECT\n"
            "    SUM((`amount` + 1)) AS `plus_total`,\n"
            "    SUM((1 + `amount`)) AS `left_literal_total`,\n"
            "    SUM((`amount` - 1)) AS `minus_total`,\n"
            "    SUM((`amount` * 2)) AS `multiplied_total`,\n"
            "    AVG((`score` * 2)) AS `weighted_average`,\n"
            "    AVG((`score` + 1.5)) AS `adjusted_average`\n"
            "FROM `orders`",
        ),
    ],
)
def test_backends_emit_no_group_numeric_literal_aggregate_sql(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
    expected_sql: str,
) -> None:
    result = emitter(
        _compile(
            _source(
                connector,
                "plus_total = sum(amount + 1)\n"
                "        left_literal_total = sum(1 + amount)\n"
                "        minus_total = sum(amount - 1)\n"
                "        multiplied_total = sum(amount * 2)\n"
                "        weighted_average = avg(score * 2)\n"
                "        adjusted_average = avg(score + 1.5)",
            )
        )
    )

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
            '    SUM(("amount" + 1)) AS "total",\n'
            '    AVG(("score" * 2)) AS "average"\n'
            'FROM "orders"\n'
            "GROUP BY\n"
            '    "region"\n'
            "HAVING\n"
            '    SUM(("amount" + 1)) > 1000\n'
            "ORDER BY\n"
            '    AVG(("score" * 2)) DESC,\n'
            '    SUM(("amount" + 1)) ASC\n'
            "LIMIT 10",
        ),
        (
            "mysql.table",
            emit_mysql_sql,
            "SELECT\n"
            "    `region` AS `region`,\n"
            "    SUM((`amount` + 1)) AS `total`,\n"
            "    AVG((`score` * 2)) AS `average`\n"
            "FROM `orders`\n"
            "GROUP BY\n"
            "    `region`\n"
            "HAVING\n"
            "    SUM((`amount` + 1)) > 1000\n"
            "ORDER BY\n"
            "    AVG((`score` * 2)) DESC,\n"
            "    SUM((`amount` + 1)) ASC\n"
            "LIMIT 10",
        ),
    ],
)
def test_grouped_satisfying_order_by_and_limit_render_numeric_literal_aggregates(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
    expected_sql: str,
) -> None:
    result = emitter(
        _compile(
            _source(
                connector,
                "region\n"
                "        total = sum(amount + 1)\n"
                "        average = avg(score * 2)",
                grouped=True,
                satisfying="total > 1000",
                order_by=("average desc", "total asc"),
                limit="10",
            )
        )
    )

    assert result.diagnostics == ()
    assert len(result.artifacts) == 1
    sql = result.artifacts[0].sql
    assert sql == expected_sql
    assert sql.index("GROUP BY") < sql.index("HAVING") < sql.index("ORDER BY")
    assert sql.index("ORDER BY") < sql.index("LIMIT")
    assert '"total"' not in _order_by_clause(sql)
    assert "`total`" not in _order_by_clause(sql)


@pytest.mark.parametrize(
    ("connector", "emitter", "expected_sql"),
    [
        (
            "postgres.table",
            emit_postgres_sql,
            "SELECT\n"
            '    SUM(("amount" + "tax")) AS "total",\n'
            '    AVG(("score" * "weight")) AS "weighted",\n'
            '    SUM(("price" + "discount")) AS "decimal_total",\n'
            '    AVG(("price" - "discount")) AS "decimal_average"\n'
            'FROM "orders"',
        ),
        (
            "mysql.table",
            emit_mysql_sql,
            "SELECT\n"
            "    SUM((`amount` + `tax`)) AS `total`,\n"
            "    AVG((`score` * `weight`)) AS `weighted`,\n"
            "    SUM((`price` + `discount`)) AS `decimal_total`,\n"
            "    AVG((`price` - `discount`)) AS `decimal_average`\n"
            "FROM `orders`",
        ),
    ],
)
def test_phase26_field_only_expression_aggregate_sql_remains_supported(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
    expected_sql: str,
) -> None:
    result = emitter(
        _compile(
            _source(
                connector,
                "total = sum(amount + tax)\n"
                "        weighted = avg(score * weight)\n"
                "        decimal_total = sum(price + discount)\n"
                "        decimal_average = avg(price - discount)",
            )
        )
    )

    assert result.diagnostics == ()
    assert len(result.artifacts) == 1
    assert result.artifacts[0].sql == expected_sql


@pytest.mark.parametrize(
    ("projection", "expected_code"),
    [
        ("value = sum(1)", "PIE-S2315"),
        ("value = avg(1)", "PIE-S2315"),
        ("value = sum(1 + 2)", "PIE-S2315"),
        ("value = avg(1.5 * 2)", "PIE-S2315"),
        ("value = sum(amount / tax)", "PIE-S2315"),
        ("value = sum(amount % tax)", "PIE-S2315"),
        ("value = sum(amount + len(status))", "PIE-S2315"),
        ("value = count(amount + 1)", "PIE-S2315"),
        ("value = min(amount + 1)", "PIE-S2315"),
        ("value = max(score * 2)", "PIE-S2315"),
        ("value = count_distinct(len(status))", "PIE-S2315"),
        ("value = sum(price + 1)", "PIE-S2315"),
        ("value = sum(price + 1.5)", "PIE-S2315"),
        ("value = sum(price * discount)", "PIE-S2315"),
        ("value = sum(avg(amount))", "PIE-S2311"),
        ("value = sum(amount) + 1", "PIE-S2310"),
    ],
)
def test_unsupported_source_shapes_stop_before_sql_with_semantic_diagnostics(
    projection: str,
    expected_code: str,
) -> None:
    parse_result = parse_source(_source("postgres.table", projection))
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    result = analyze(parse_result.ast)

    assert [
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ] == [expected_code]


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
        "avg_literal_binary_argument",
        "sum_bool_literal_argument",
        "sum_division_argument",
        "sum_modulo_argument",
        "sum_arbitrary_call_argument",
        "count_expression_argument",
        "min_expression_argument",
        "max_expression_argument",
        "count_distinct_binary_argument",
        "decimal_literal_argument",
        "decimal_multiplication_argument",
        "mixed_decimal_float_argument",
    ],
)
def test_malformed_hand_built_numeric_literal_aggregate_ir_fails_closed(
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


def test_private_mysql_api_remains_unexported() -> None:
    assert sql_api.__all__ == [
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    ]
    assert not hasattr(sql_api, "emit_mysql_sql")


def _source(
    connector: str,
    select_body: str,
    *,
    table_name: str = "orders",
    grouped: bool = False,
    satisfying: str | None = None,
    order_by: tuple[str, ...] = (),
    limit: str | None = None,
) -> str:
    group_block = "    group by:\n        region\n" if grouped else ""
    satisfying_block = (
        f"    satisfying:\n        {satisfying}\n" if satisfying is not None else ""
    )
    order_block = ""
    if order_by:
        order_items = "".join(f"        {item}\n" for item in order_by)
        order_block = f"    order by:\n{order_items}"
    limit_block = "" if limit is None else f"    limit {limit}\n"
    return (
        BASE_SHAPE + f'source orders: Order is {connector}("{table_name}")\n'
        "table aggregate_stats:\n"
        "    from orders\n"
        f"{group_block}"
        "    select:\n"
        f"        {select_body}\n"
        f"{satisfying_block}"
        f"{order_block}"
        f"{limit_block}"
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


def _order_by_clause(sql: str) -> str:
    _, order = sql.split("ORDER BY\n", maxsplit=1)
    return order.split("\nLIMIT", maxsplit=1)[0]


def _malformed_aggregate(case: str) -> AggregateCallIR:
    amount = _field("amount", INT_NON_NULL)
    tax = _field("tax", INT_NON_NULL)
    score = _field("score", FLOAT_NON_NULL)
    price = _field("price", DECIMAL_NON_NULL)
    discount = _field("discount", DECIMAL_NON_NULL)
    status = _field("status", TEXT_NON_NULL)

    if case == "sum_literal_argument":
        return _aggregate("sum", INT_NULLABLE, _literal(1, INT_NON_NULL))
    if case == "avg_literal_binary_argument":
        return _aggregate(
            "avg",
            FLOAT_NULLABLE,
            _binary(
                _literal(1.5, FLOAT_NON_NULL),
                "+",
                _literal(2, INT_NON_NULL),
                FLOAT_NON_NULL,
            ),
        )
    if case == "sum_bool_literal_argument":
        return _aggregate(
            "sum",
            INT_NULLABLE,
            _binary(amount, "+", _literal(True, BOOL_NON_NULL), INT_NON_NULL),
        )
    if case == "sum_division_argument":
        return _aggregate("sum", INT_NULLABLE, _binary(amount, "/", tax, INT_NON_NULL))
    if case == "sum_modulo_argument":
        return _aggregate("sum", INT_NULLABLE, _binary(amount, "%", tax, INT_NON_NULL))
    if case == "sum_arbitrary_call_argument":
        return _aggregate(
            "sum",
            INT_NULLABLE,
            _binary(amount, "+", _call("len", INT_NON_NULL, status), INT_NON_NULL),
        )
    if case == "count_expression_argument":
        return _aggregate(
            "count", INT_NON_NULL, _binary(amount, "+", tax, INT_NON_NULL)
        )
    if case == "min_expression_argument":
        return _aggregate("min", INT_NULLABLE, _binary(amount, "+", tax, INT_NON_NULL))
    if case == "max_expression_argument":
        return _aggregate(
            "max", FLOAT_NULLABLE, _binary(score, "*", score, FLOAT_NON_NULL)
        )
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
    if case == "decimal_literal_argument":
        return _aggregate(
            "sum",
            DECIMAL_NULLABLE,
            _binary(price, "+", _literal(1, INT_NON_NULL), DECIMAL_NON_NULL),
        )
    if case == "decimal_multiplication_argument":
        return _aggregate(
            "sum",
            DECIMAL_NULLABLE,
            _binary(price, "*", discount, DECIMAL_NON_NULL),
        )
    if case == "mixed_decimal_float_argument":
        return _aggregate(
            "sum",
            DECIMAL_NULLABLE,
            _binary(price, "+", _literal(1.5, FLOAT_NON_NULL), DECIMAL_NON_NULL),
        )
    raise AssertionError(f"Unknown malformed aggregate case: {case}")


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
