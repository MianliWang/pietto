from __future__ import annotations

from dataclasses import fields

import pytest

from pietto.ast_nodes import QueryDef, Script, ShapeDef, TableDef, TypeExpr
from pietto.errors import Severity
from pietto.ir import (
    AggregateCallIR,
    BinaryIR,
    ExpressionIR,
    FieldRefIR,
    NullabilityIR,
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
    TypeKind,
    ValueType,
    ValueTypeKind,
    analyze,
)
from pietto.semantic.aggregates import semantic_aggregate_result_value_type
from pietto.semantic.model import DecimalPrecisionScale
from pietto.sql import emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

MATRIX_SHAPE = (
    "enum Status:\n"
    "    active\n"
    "    paused\n"
    "shape Order:\n"
    "    status: Text not null\n"
    "    region: Text not null\n"
    "    active: Bool not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    score: Float not null\n"
    "    weight: Float not null\n"
    "    price: Decimal not null\n"
    "    discount: Decimal not null\n"
    "    order_date: Date nullable\n"
    "    created_at: Timestamp not null\n"
    "    raw: Bytes not null\n"
    "    payload: Json not null\n"
    "    customer_id: UUID not null\n"
    "    anything: Any nullable\n"
    "    enum_status: Status not null\n"
)

NO_GROUP_PROJECTIONS = (
    "        total = count()\n"
    "        count_status = count(status)\n"
    "        count_raw = count(raw)\n"
    "        count_payload = count(payload)\n"
    "        count_customer = count(customer_id)\n"
    "        known_amount_expr = count(amount + tax)\n"
    "        known_amount_literal_expr = count(amount + 1)\n"
    "        known_status_expr = count(lower(trim(status)))\n"
    "        unique_status = count_distinct(status)\n"
    "        unique_customer = count_distinct(customer_id)\n"
    "        unique_normalized = count_distinct(lower(trim(status)))\n"
    "        total_amount = sum(amount)\n"
    "        total_score = sum(score)\n"
    "        total_price = sum(price)\n"
    "        average_amount = avg(amount)\n"
    "        average_score = avg(score)\n"
    "        average_price = avg(price)\n"
    "        total_expr = sum(amount + tax)\n"
    "        total_literal_expr = sum(amount + 1)\n"
    "        average_expr = avg(score * weight)\n"
    "        average_literal_expr = avg(score + 1.5)\n"
    "        decimal_total_expr = sum(price + discount)\n"
    "        decimal_average_expr = avg(price - discount)\n"
    "        smallest_amount = min(amount)\n"
    "        smallest_score = min(score)\n"
    "        smallest_price = min(price)\n"
    "        first_order_date = min(order_date)\n"
    "        first_created_at = min(created_at)\n"
    "        largest_amount = max(amount)\n"
    "        largest_score = max(score)\n"
    "        largest_price = max(price)\n"
    "        latest_order_date = max(order_date)\n"
    "        latest_created_at = max(created_at)\n"
)

NO_GROUP_ROW_SCHEMA = (
    ("total", "Int", EffectiveNullability.NON_NULL),
    ("count_status", "Int", EffectiveNullability.NON_NULL),
    ("count_raw", "Int", EffectiveNullability.NON_NULL),
    ("count_payload", "Int", EffectiveNullability.NON_NULL),
    ("count_customer", "Int", EffectiveNullability.NON_NULL),
    ("known_amount_expr", "Int", EffectiveNullability.NON_NULL),
    ("known_amount_literal_expr", "Int", EffectiveNullability.NON_NULL),
    ("known_status_expr", "Int", EffectiveNullability.NON_NULL),
    ("unique_status", "Int", EffectiveNullability.NON_NULL),
    ("unique_customer", "Int", EffectiveNullability.NON_NULL),
    ("unique_normalized", "Int", EffectiveNullability.NON_NULL),
    ("total_amount", "Int", EffectiveNullability.NULLABLE),
    ("total_score", "Float", EffectiveNullability.NULLABLE),
    ("total_price", "Decimal", EffectiveNullability.NULLABLE),
    ("average_amount", "Float", EffectiveNullability.NULLABLE),
    ("average_score", "Float", EffectiveNullability.NULLABLE),
    ("average_price", "Decimal", EffectiveNullability.NULLABLE),
    ("total_expr", "Int", EffectiveNullability.NULLABLE),
    ("total_literal_expr", "Int", EffectiveNullability.NULLABLE),
    ("average_expr", "Float", EffectiveNullability.NULLABLE),
    ("average_literal_expr", "Float", EffectiveNullability.NULLABLE),
    ("decimal_total_expr", "Decimal", EffectiveNullability.NULLABLE),
    ("decimal_average_expr", "Decimal", EffectiveNullability.NULLABLE),
    ("smallest_amount", "Int", EffectiveNullability.NULLABLE),
    ("smallest_score", "Float", EffectiveNullability.NULLABLE),
    ("smallest_price", "Decimal", EffectiveNullability.NULLABLE),
    ("first_order_date", "Date", EffectiveNullability.NULLABLE),
    ("first_created_at", "Timestamp", EffectiveNullability.NULLABLE),
    ("largest_amount", "Int", EffectiveNullability.NULLABLE),
    ("largest_score", "Float", EffectiveNullability.NULLABLE),
    ("largest_price", "Decimal", EffectiveNullability.NULLABLE),
    ("latest_order_date", "Date", EffectiveNullability.NULLABLE),
    ("latest_created_at", "Timestamp", EffectiveNullability.NULLABLE),
)

GROUPED_PROJECTIONS = (
    "        status\n"
    "        total = count()\n"
    "        count_customer = count(customer_id)\n"
    "        known_amount_expr = count(amount + tax)\n"
    "        unique_normalized = count_distinct(lower(trim(status)))\n"
    "        total_amount = sum(amount)\n"
    "        total_literal_expr = sum(amount + 1)\n"
    "        average_expr = avg(score * weight)\n"
    "        decimal_average_expr = avg(price - discount)\n"
    "        smallest_price = min(price)\n"
    "        latest_created_at = max(created_at)\n"
)

GROUPED_ROW_SCHEMA = (
    ("status", "Text", EffectiveNullability.NON_NULL),
    ("total", "Int", EffectiveNullability.NON_NULL),
    ("count_customer", "Int", EffectiveNullability.NON_NULL),
    ("known_amount_expr", "Int", EffectiveNullability.NON_NULL),
    ("unique_normalized", "Int", EffectiveNullability.NON_NULL),
    ("total_amount", "Int", EffectiveNullability.NULLABLE),
    ("total_literal_expr", "Int", EffectiveNullability.NULLABLE),
    ("average_expr", "Float", EffectiveNullability.NULLABLE),
    ("decimal_average_expr", "Decimal", EffectiveNullability.NULLABLE),
    ("smallest_price", "Decimal", EffectiveNullability.NULLABLE),
    ("latest_created_at", "Timestamp", EffectiveNullability.NULLABLE),
)


def test_semantic_aggregate_result_typeclass_adjacent_matrix_is_locked() -> None:
    accepted = (
        ("count", None, "Int", EffectiveNullability.NON_NULL),
        ("count", _builtin("Bool"), "Int", EffectiveNullability.NON_NULL),
        ("count", _builtin("Int"), "Int", EffectiveNullability.NON_NULL),
        ("count", _builtin("Float"), "Int", EffectiveNullability.NON_NULL),
        ("count", _builtin("Decimal"), "Int", EffectiveNullability.NON_NULL),
        ("count", _builtin("Text"), "Int", EffectiveNullability.NON_NULL),
        ("count", _builtin("Date"), "Int", EffectiveNullability.NON_NULL),
        ("count", _builtin("Timestamp"), "Int", EffectiveNullability.NON_NULL),
        ("count", _builtin("Bytes"), "Int", EffectiveNullability.NON_NULL),
        ("count", _builtin("Json"), "Int", EffectiveNullability.NON_NULL),
        ("count", _builtin("UUID"), "Int", EffectiveNullability.NON_NULL),
        ("count_distinct", _builtin("Bool"), "Int", EffectiveNullability.NON_NULL),
        ("count_distinct", _builtin("Int"), "Int", EffectiveNullability.NON_NULL),
        ("count_distinct", _builtin("Float"), "Int", EffectiveNullability.NON_NULL),
        (
            "count_distinct",
            _builtin("Decimal"),
            "Int",
            EffectiveNullability.NON_NULL,
        ),
        ("count_distinct", _builtin("Text"), "Int", EffectiveNullability.NON_NULL),
        ("count_distinct", _builtin("Date"), "Int", EffectiveNullability.NON_NULL),
        (
            "count_distinct",
            _builtin("Timestamp"),
            "Int",
            EffectiveNullability.NON_NULL,
        ),
        ("count_distinct", _builtin("UUID"), "Int", EffectiveNullability.NON_NULL),
        ("sum", _builtin("Int"), "Int", EffectiveNullability.NULLABLE),
        ("sum", _builtin("Float"), "Float", EffectiveNullability.NULLABLE),
        ("sum", _builtin("Decimal"), "Decimal", EffectiveNullability.NULLABLE),
        ("avg", _builtin("Int"), "Float", EffectiveNullability.NULLABLE),
        ("avg", _builtin("Float"), "Float", EffectiveNullability.NULLABLE),
        ("avg", _builtin("Decimal"), "Decimal", EffectiveNullability.NULLABLE),
        ("min", _builtin("Int"), "Int", EffectiveNullability.NULLABLE),
        ("min", _builtin("Float"), "Float", EffectiveNullability.NULLABLE),
        ("min", _builtin("Decimal"), "Decimal", EffectiveNullability.NULLABLE),
        ("min", _builtin("Date"), "Date", EffectiveNullability.NULLABLE),
        ("min", _builtin("Timestamp"), "Timestamp", EffectiveNullability.NULLABLE),
        ("max", _builtin("Int"), "Int", EffectiveNullability.NULLABLE),
        ("max", _builtin("Float"), "Float", EffectiveNullability.NULLABLE),
        ("max", _builtin("Decimal"), "Decimal", EffectiveNullability.NULLABLE),
        ("max", _builtin("Date"), "Date", EffectiveNullability.NULLABLE),
        ("max", _builtin("Timestamp"), "Timestamp", EffectiveNullability.NULLABLE),
    )

    for function, argument, expected_name, expected_nullability in accepted:
        result = semantic_aggregate_result_value_type(function, argument)
        assert result is not None, function
        _assert_value_type(result, expected_name, expected_nullability)

    for function, argument in (
        ("count", _builtin("Any")),
        ("count", _enum("Status")),
        ("count", _unknown()),
        ("count_distinct", None),
        ("count_distinct", _builtin("Bytes")),
        ("count_distinct", _builtin("Json")),
        ("count_distinct", _builtin("Any")),
        ("count_distinct", _enum("Status")),
        ("count_distinct", _unknown()),
        ("sum", None),
        ("sum", _builtin("Text")),
        ("sum", _builtin("Date")),
        ("sum", _builtin("UUID")),
        ("sum", _unknown()),
        ("avg", None),
        ("avg", _builtin("Bool")),
        ("avg", _builtin("Timestamp")),
        ("avg", _unknown()),
        ("min", None),
        ("min", _builtin("Text")),
        ("min", _builtin("Bool")),
        ("min", _builtin("UUID")),
        ("min", _unknown()),
        ("max", None),
        ("max", _builtin("Json")),
        ("max", _builtin("Any")),
        ("max", _unknown()),
        ("median", _builtin("Int")),
    ):
        assert semantic_aggregate_result_value_type(function, argument) is None


def test_no_group_aggregate_typeclass_matrix_semantic_ir_and_sql_are_locked() -> None:
    script, semantic, script_ir = _compile(_matrix_source("postgres.table", grouped=False))
    relation = _relation_ast(script)
    schema = semantic.model.relation_row_schemas[relation]

    assert tuple(schema.fields) == tuple(name for name, _, _ in NO_GROUP_ROW_SCHEMA)
    for name, expected_type, expected_nullability in NO_GROUP_ROW_SCHEMA:
        field = schema.fields[name]
        _assert_value_type(field, expected_type, expected_nullability)
        select_item = next(item for item in relation.select_items if item.alias == name)
        _assert_value_type(
            semantic.model.expression_value_types[select_item.expression],
            expected_type,
            expected_nullability,
        )

    _assert_aggregate_ir_matrix(script_ir, NO_GROUP_ROW_SCHEMA)

    for connector, emitter, expected_fragments in (
        (
            "postgres.table",
            emit_postgres_sql,
            (
                'COUNT(*) AS "total"',
                'COUNT("raw") AS "count_raw"',
                'COUNT("payload") AS "count_payload"',
                'COUNT(("amount" + "tax")) AS "known_amount_expr"',
                'COUNT(DISTINCT lower(trim("status"))) AS "unique_normalized"',
                'SUM("price") AS "total_price"',
                'AVG("price") AS "average_price"',
                'SUM(("amount" + 1)) AS "total_literal_expr"',
                'AVG(("price" - "discount")) AS "decimal_average_expr"',
                'MIN("created_at") AS "first_created_at"',
                'MAX("order_date") AS "latest_order_date"',
            ),
        ),
        (
            "mysql.table",
            emit_mysql_sql,
            (
                "COUNT(*) AS `total`",
                "COUNT(`raw`) AS `count_raw`",
                "COUNT(`payload`) AS `count_payload`",
                "COUNT((`amount` + `tax`)) AS `known_amount_expr`",
                "COUNT(DISTINCT LOWER(TRIM(`status`))) AS `unique_normalized`",
                "SUM(`price`) AS `total_price`",
                "AVG(`price`) AS `average_price`",
                "SUM((`amount` + 1)) AS `total_literal_expr`",
                "AVG((`price` - `discount`)) AS `decimal_average_expr`",
                "MIN(`created_at`) AS `first_created_at`",
                "MAX(`order_date`) AS `latest_order_date`",
            ),
        ),
    ):
        sql_result = emitter(_compile(_matrix_source(connector, grouped=False))[2])
        assert sql_result.diagnostics == ()
        assert len(sql_result.artifacts) == 1
        sql = sql_result.artifacts[0].sql
        for fragment in expected_fragments:
            assert fragment in sql


def test_grouped_aggregate_typeclass_matrix_semantic_and_ir_are_locked() -> None:
    script, semantic, script_ir = _compile(_matrix_source("postgres.table", grouped=True))
    relation = _relation_ast(script)
    schema = semantic.model.relation_row_schemas[relation]

    assert tuple(schema.fields) == tuple(name for name, _, _ in GROUPED_ROW_SCHEMA)
    for name, expected_type, expected_nullability in GROUPED_ROW_SCHEMA:
        _assert_value_type(schema.fields[name], expected_type, expected_nullability)

    relation_ir = _relation_ir(script_ir)
    assert [key.name for key in relation_ir.group_keys] == ["status"]
    _assert_aggregate_ir_matrix(script_ir, GROUPED_ROW_SCHEMA)


@pytest.mark.parametrize(
    ("projection", "expected_code"),
    [
        ("value = count(1)", "PIE-S2315"),
        ("value = sum(1)", "PIE-S2315"),
        ("value = avg(1)", "PIE-S2315"),
        ("value = count_distinct(1)", "PIE-S2315"),
        ("value = count_distinct(raw)", "PIE-S2314"),
        ("value = count_distinct(payload)", "PIE-S2314"),
        ("value = count_distinct(anything)", "PIE-S2314"),
        ("value = count_distinct(enum_status)", "PIE-S2314"),
        ("value = min(status)", "PIE-S2314"),
        ("value = max(active)", "PIE-S2314"),
        ("value = min(customer_id)", "PIE-S2314"),
        ("value = max(raw)", "PIE-S2314"),
        ("value = min(payload)", "PIE-S2314"),
        ("value = max(anything)", "PIE-S2314"),
        ("value = min(enum_status)", "PIE-S2314"),
        ("value = sum(price * discount)", "PIE-S2315"),
        ("value = avg(price * discount)", "PIE-S2315"),
        ("value = sum(price + amount)", "PIE-S2315"),
        ("value = sum(price + score)", "PIE-S2315"),
    ],
)
def test_fail_closed_aggregate_typeclass_boundaries_are_locked(
    projection: str,
    expected_code: str,
) -> None:
    semantic = analyze(
        _parse(
            MATRIX_SHAPE
            + 'source orders: Order is postgres.table("orders")\n'
            + "table aggregate_stats:\n"
            + "    from orders\n"
            + "    select:\n"
            + f"        {projection}\n"
        )
    )

    assert expected_code in _error_codes(semantic)


def test_projection_alias_let_and_type_alias_aggregate_arguments_fail_closed() -> None:
    projection_alias = analyze(
        _parse(
            MATRIX_SHAPE
            + 'source orders: Order is postgres.table("orders")\n'
            + "table aggregate_stats:\n"
            + "    from orders\n"
            + "    select:\n"
            + "        subtotal = amount + tax\n"
            + "        value = sum(subtotal)\n"
        )
    )
    assert "PIE-S2102" in _error_codes(projection_alias)

    let_name = analyze(
        _parse(
            MATRIX_SHAPE
            + 'source orders: Order is postgres.table("orders")\n'
            + "query aggregate_stats:\n"
            + "    from orders\n"
            + "    let:\n"
            + "        gross = amount + tax\n"
            + "    select:\n"
            + "        value = sum(gross)\n"
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


def test_decimal_precision_scale_aggregates_remain_logical_non_public_decimal() -> None:
    script, semantic, script_ir = _compile(
        "shape Order:\n"
        "    amount: Decimal(12, 2) not null\n"
        "    tax: Decimal(12, 2) not null\n"
        'source orders: Order is postgres.table("orders")\n'
        "table decimal_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        total = sum(amount)\n"
        "        average = avg(amount - tax)\n"
        "        smallest = min(amount)\n"
        "        largest = max(amount)\n"
        "        known_values = count(amount + tax)\n"
        "        unique_values = count_distinct(amount)\n"
    )
    amount_type_expr = _shape_field_type_expr(script, "amount")
    assert semantic.model.decimal_precision_scale_for(
        amount_type_expr
    ) == DecimalPrecisionScale(12, 2)

    semantic_fields = semantic.model.relation_row_schemas[_relation_ast(script)].fields
    for field_name in ("total", "average", "smallest", "largest"):
        _assert_value_type(
            semantic_fields[field_name],
            "Decimal",
            EffectiveNullability.NULLABLE,
        )
    for field_name in ("known_values", "unique_values"):
        _assert_value_type(semantic_fields[field_name], "Int", EffectiveNullability.NON_NULL)

    for type_surface in (ResolvedType, ValueType, TypeRefIR):
        assert {"precision", "scale"}.isdisjoint(
            {field.name for field in fields(type_surface)}
        )

    sql_result = emit_postgres_sql(script_ir)
    assert sql_result.diagnostics == ()
    assert sql_result.artifacts
    lowered_sql = "\n".join(artifact.sql for artifact in sql_result.artifacts)
    for forbidden in ("DECIMAL(", "NUMERIC(", "precision", "scale"):
        assert forbidden not in lowered_sql


def _matrix_source(connector: str, *, grouped: bool) -> str:
    relation = (
        "table aggregate_stats_by_status:\n"
        "    from orders\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        f"{GROUPED_PROJECTIONS}"
        if grouped
        else "table aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        f"{NO_GROUP_PROJECTIONS}"
    )
    return MATRIX_SHAPE + f'source orders: Order is {connector}("orders")\n' + relation


def _parse(source: str) -> Script:
    result = parse_source(source, path="phase42_matrix_lock.pietto")
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


def _relation_ast(script: Script) -> TableDef | QueryDef:
    relation = script.definitions[-1]
    assert isinstance(relation, (TableDef, QueryDef))
    return relation


def _relation_ir(script_ir: ScriptIR) -> RelationIR:
    relations = [
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR)
    ]
    assert len(relations) == 1
    return relations[0]


def _assert_aggregate_ir_matrix(
    script_ir: ScriptIR,
    expected_schema: tuple[tuple[str, str, EffectiveNullability], ...],
) -> None:
    relation = _relation_ir(script_ir)
    projections = {projection.name: projection for projection in relation.projections}
    fields_by_name = {field.name: field for field in relation.row_schema.fields}

    for name, expected_type, expected_nullability in expected_schema:
        projection = projections[name]
        row_field = fields_by_name[name]
        assert row_field.type_ref.canonical_name == expected_type
        assert row_field.nullability is _ir_nullability(expected_nullability)
        if name == "status":
            assert isinstance(projection.expression, FieldRefIR)
            continue
        assert isinstance(projection.expression, AggregateCallIR), name
        assert projection.expression.value_type.canonical_name == expected_type
        assert projection.expression.value_type.nullability is _ir_nullability(
            expected_nullability
        )

    aggregate_expectations = {
        "total": ("count", 0, ()),
        "count_status": ("count", 1, ("status",)),
        "count_raw": ("count", 1, ("raw",)),
        "count_payload": ("count", 1, ("payload",)),
        "count_customer": ("count", 1, ("customer_id",)),
        "known_amount_expr": ("count", 1, ("amount", "tax")),
        "known_amount_literal_expr": ("count", 1, ("amount",)),
        "known_status_expr": ("count", 1, ("status",)),
        "unique_status": ("count_distinct", 1, ("status",)),
        "unique_customer": ("count_distinct", 1, ("customer_id",)),
        "unique_normalized": ("count_distinct", 1, ("status",)),
        "total_amount": ("sum", 1, ("amount",)),
        "total_score": ("sum", 1, ("score",)),
        "total_price": ("sum", 1, ("price",)),
        "average_amount": ("avg", 1, ("amount",)),
        "average_score": ("avg", 1, ("score",)),
        "average_price": ("avg", 1, ("price",)),
        "total_expr": ("sum", 1, ("amount", "tax")),
        "total_literal_expr": ("sum", 1, ("amount",)),
        "average_expr": ("avg", 1, ("score", "weight")),
        "average_literal_expr": ("avg", 1, ("score",)),
        "decimal_total_expr": ("sum", 1, ("price", "discount")),
        "decimal_average_expr": ("avg", 1, ("price", "discount")),
        "smallest_amount": ("min", 1, ("amount",)),
        "smallest_score": ("min", 1, ("score",)),
        "smallest_price": ("min", 1, ("price",)),
        "first_order_date": ("min", 1, ("order_date",)),
        "first_created_at": ("min", 1, ("created_at",)),
        "largest_amount": ("max", 1, ("amount",)),
        "largest_score": ("max", 1, ("score",)),
        "largest_price": ("max", 1, ("price",)),
        "latest_order_date": ("max", 1, ("order_date",)),
        "latest_created_at": ("max", 1, ("created_at",)),
    }
    for name, (function, argument_count, field_names) in aggregate_expectations.items():
        if name not in projections:
            continue
        aggregate = projections[name].expression
        assert isinstance(aggregate, AggregateCallIR), name
        assert aggregate.function == function
        assert len(aggregate.arguments) == argument_count
        assert _field_names(aggregate) == field_names


def _field_names(expression: ExpressionIR) -> tuple[str, ...]:
    if isinstance(expression, FieldRefIR):
        return (expression.name,) if expression.field is not None else ()
    if isinstance(expression, AggregateCallIR):
        return tuple(
            name for argument in expression.arguments for name in _field_names(argument)
        )
    if isinstance(expression, BinaryIR):
        return (*_field_names(expression.left), *_field_names(expression.right))
    arguments = getattr(expression, "arguments", ())
    operand = getattr(expression, "operand", None)
    return (
        tuple(name for argument in arguments for name in _field_names(argument))
        if arguments
        else (() if operand is None else _field_names(operand))
    )


def _error_codes(result: SemanticResult) -> list[str]:
    return [
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _assert_value_type(
    value_type: object,
    expected_name: str,
    expected_nullability: EffectiveNullability,
) -> None:
    assert getattr(value_type, "resolved_type").name == expected_name
    assert getattr(value_type, "nullability") is expected_nullability


def _shape_field_type_expr(script: Script, field_name: str) -> TypeExpr:
    shape = next(
        definition for definition in script.definitions if isinstance(definition, ShapeDef)
    )
    field = next(field for field in shape.fields if field.name == field_name)
    return field.type_expr


def _builtin(
    name: str,
    nullability: EffectiveNullability = EffectiveNullability.NON_NULL,
) -> ValueType:
    return ValueType(
        resolved_type=ResolvedType(name=name, kind=TypeKind.BUILTIN),
        nullability=nullability,
    )


def _enum(name: str) -> ValueType:
    return ValueType(
        resolved_type=ResolvedType(name=name, kind=TypeKind.ENUM),
        nullability=EffectiveNullability.NON_NULL,
    )


def _unknown() -> ValueType:
    return ValueType(
        resolved_type=ResolvedType(name="<unknown>", kind=TypeKind.UNKNOWN),
        nullability=EffectiveNullability.UNKNOWN,
        kind=ValueTypeKind.UNKNOWN,
    )


def _ir_nullability(nullability: EffectiveNullability) -> NullabilityIR:
    if nullability is EffectiveNullability.NON_NULL:
        return NullabilityIR.NON_NULL
    if nullability is EffectiveNullability.NULLABLE:
        return NullabilityIR.NULLABLE
    return NullabilityIR.UNKNOWN
