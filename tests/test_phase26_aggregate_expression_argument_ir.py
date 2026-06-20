from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.ast_nodes import QueryDef, Script, TableDef
from pietto.errors import Severity
from pietto.ir import (
    AggregateCallIR,
    BetweenIR,
    BinaryIR,
    CallIR,
    ComparisonIR,
    ExpressionIR,
    FieldId,
    FieldRefIR,
    IsNullIR,
    NullabilityIR,
    ProjectionIR,
    RelationIR,
    ScriptIR,
    SymbolId,
    SymbolNamespace,
    UnaryIR,
    build_ir,
)
from pietto.ir.lowering import lower_expr
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, analyze

SOURCE_PREFIX = (
    "shape Order:\n"
    "    status: Text not null\n"
    "    region: Text not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    score: Float not null\n"
    "    weight: Float not null\n"
    "    price: Decimal not null\n"
    "    active: Bool not null\n"
    'source orders: Order is postgres.table("orders")\n'
)


def test_sum_avg_numeric_expression_arguments_lower_to_aggregate_call_ir() -> None:
    script = _parse(
        SOURCE_PREFIX + "table aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        total = sum(amount + tax)\n"
        "        weighted = avg(score * weight)\n"
        "        decimal_total = sum(price + price)\n"
        "        decimal_average = avg(price - price)\n"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    projections = _projections(_relation_ir(ir_result.ir))

    _assert_binary_aggregate(
        projections["total"].expression,
        function="sum",
        result_type="Int",
        operator="+",
        left_name="amount",
        right_name="tax",
        argument_type="Int",
    )
    _assert_binary_aggregate(
        projections["weighted"].expression,
        function="avg",
        result_type="Float",
        operator="*",
        left_name="score",
        right_name="weight",
        argument_type="Float",
    )
    _assert_binary_aggregate(
        projections["decimal_total"].expression,
        function="sum",
        result_type="Decimal",
        operator="+",
        left_name="price",
        right_name="price",
        argument_type="Decimal",
    )
    _assert_binary_aggregate(
        projections["decimal_average"].expression,
        function="avg",
        result_type="Decimal",
        operator="-",
        left_name="price",
        right_name="price",
        argument_type="Decimal",
    )


def test_count_distinct_transform_arguments_lower_to_aggregate_call_ir() -> None:
    script = _parse(
        SOURCE_PREFIX + "table status_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        normalized = count_distinct(lower(status))\n"
        "        trimmed = count_distinct(trim(status))\n"
        "        normalized_trimmed = count_distinct(lower(trim(status)))\n"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    projections = _projections(_relation_ir(ir_result.ir))

    _assert_transform_aggregate(
        projections["normalized"].expression,
        callees=("lower",),
        field_name="status",
    )
    _assert_transform_aggregate(
        projections["trimmed"].expression,
        callees=("trim",),
        field_name="status",
    )
    _assert_transform_aggregate(
        projections["normalized_trimmed"].expression,
        callees=("lower", "trim"),
        field_name="status",
    )


def test_qualified_expression_leaves_preserve_field_identity() -> None:
    script = _parse(
        SOURCE_PREFIX + "table aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        total = sum(orders.amount + orders.tax)\n"
        "        normalized = count_distinct(lower(orders.status))\n"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    projections = _projections(_relation_ir(ir_result.ir))

    _assert_binary_aggregate(
        projections["total"].expression,
        function="sum",
        result_type="Int",
        operator="+",
        left_name="orders.amount",
        right_name="orders.tax",
        argument_type="Int",
    )
    _assert_transform_aggregate(
        projections["normalized"].expression,
        callees=("lower",),
        field_name="orders.status",
    )


def test_grouped_expression_argument_aggregates_preserve_group_keys() -> None:
    script = _parse(
        SOURCE_PREFIX + "table aggregate_stats_by_region:\n"
        "    from orders\n"
        "    group by:\n"
        "        region\n"
        "    select:\n"
        "        region\n"
        "        total = sum(amount + tax)\n"
        "        normalized = count_distinct(lower(status))\n"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    relation = _relation_ir(ir_result.ir)
    projections = _projections(relation)

    assert [key.name for key in relation.group_keys] == ["region"]
    assert [key.qualifier for key in relation.group_keys] == [()]
    assert [key.field for key in relation.group_keys] == [
        FieldId(owner=_orders_symbol(), name="region")
    ]
    _assert_binary_aggregate(
        projections["total"].expression,
        function="sum",
        result_type="Int",
        operator="+",
        left_name="amount",
        right_name="tax",
        argument_type="Int",
    )
    _assert_transform_aggregate(
        projections["normalized"].expression,
        callees=("lower",),
        field_name="status",
    )


def test_direct_lower_expr_for_valid_expression_arguments_uses_aggregate_call_ir() -> (
    None
):
    script = _parse(
        SOURCE_PREFIX + "table aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        total = sum(amount + tax)\n"
        "        normalized = count_distinct(lower(status))\n"
    )
    relation = _relation_ast(script)
    semantic_result = analyze(script)
    input_schema = next(iter(semantic_result.model.source_row_schemas.values()))

    lowered_sum = lower_expr(
        relation.select_items[0].expression,
        semantic_result.model,
        fields=input_schema.fields,
        field_owner=_orders_symbol(),
        field_qualifier="orders",
    )
    lowered_count_distinct = lower_expr(
        relation.select_items[1].expression,
        semantic_result.model,
        fields=input_schema.fields,
        field_owner=_orders_symbol(),
        field_qualifier="orders",
    )

    assert _error_codes(semantic_result) == []
    assert lowered_sum.diagnostics == ()
    assert isinstance(lowered_sum.expression, AggregateCallIR)
    assert not isinstance(lowered_sum.expression, CallIR)
    assert isinstance(lowered_sum.expression.arguments[0], BinaryIR)
    assert lowered_count_distinct.diagnostics == ()
    assert isinstance(lowered_count_distinct.expression, AggregateCallIR)
    assert not isinstance(lowered_count_distinct.expression, CallIR)
    assert isinstance(lowered_count_distinct.expression.arguments[0], CallIR)


def test_direct_field_aggregate_lowering_remains_unchanged() -> None:
    script = _parse(
        SOURCE_PREFIX + "table aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        total = count()\n"
        "        known_statuses = count(status)\n"
        "        unique_statuses = count_distinct(status)\n"
        "        amount_total = sum(amount)\n"
        "        average_score = avg(score)\n"
        "        smallest_amount = min(amount)\n"
        "        largest_score = max(score)\n"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    projections = _projections(_relation_ir(ir_result.ir))

    _assert_direct_aggregate(
        projections["total"].expression,
        "count",
        "Int",
        NullabilityIR.NON_NULL,
        (),
    )
    _assert_direct_aggregate(
        projections["known_statuses"].expression,
        "count",
        "Int",
        NullabilityIR.NON_NULL,
        ("status",),
    )
    _assert_direct_aggregate(
        projections["unique_statuses"].expression,
        "count_distinct",
        "Int",
        NullabilityIR.NON_NULL,
        ("status",),
    )
    _assert_direct_aggregate(
        projections["amount_total"].expression,
        "sum",
        "Int",
        NullabilityIR.NULLABLE,
        ("amount",),
    )
    _assert_direct_aggregate(
        projections["average_score"].expression,
        "avg",
        "Float",
        NullabilityIR.NULLABLE,
        ("score",),
    )
    _assert_direct_aggregate(
        projections["smallest_amount"].expression,
        "min",
        "Int",
        NullabilityIR.NULLABLE,
        ("amount",),
    )
    _assert_direct_aggregate(
        projections["largest_score"].expression,
        "max",
        "Float",
        NullabilityIR.NULLABLE,
        ("score",),
    )


@pytest.mark.parametrize(
    ("projection", "expected_code"),
    [
        ("value = sum(amount / tax)", "PIE-S2315"),
        ("value = sum(amount % tax)", "PIE-S2315"),
        ("value = avg(price * price)", "PIE-S2315"),
        ("value = count_distinct(len(status))", "PIE-S2315"),
        ("value = count_distinct(lower(amount))", "PIE-S2315"),
        ("value = count(amount + tax)", "PIE-S2315"),
        ("value = min(amount + tax)", "PIE-S2315"),
        ("value = max(score * weight)", "PIE-S2315"),
        ("value = sum(avg(amount))", "PIE-S2311"),
        ("value = sum(amount) + 1", "PIE-S2310"),
    ],
)
def test_unsupported_aggregate_expression_shapes_remain_before_ir(
    projection: str,
    expected_code: str,
) -> None:
    script = _parse(
        SOURCE_PREFIX + "table aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        f"        {projection}\n"
    )
    semantic_result = analyze(script)

    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == [expected_code]
    if ir_result.ir is not None:
        assert _aggregate_expressions(ir_result.ir) == ()


def test_direct_aggregate_inside_satisfying_remains_semantic_error() -> None:
    script = _parse(
        SOURCE_PREFIX + "table aggregate_stats_by_region:\n"
        "    from orders\n"
        "    group by:\n"
        "        region\n"
        "    select:\n"
        "        region\n"
        "        total = sum(amount + tax)\n"
        "    satisfying:\n"
        "        sum(amount + tax) > 10\n"
    )
    semantic_result = analyze(script)

    assert _error_codes(semantic_result) == ["PIE-S2308"]


@pytest.mark.parametrize(
    ("dialect", "projection", "expected_sql"),
    [
        (
            "postgres",
            "total = sum(amount + tax)",
            'SELECT\n    SUM(("amount" + "tax")) AS "total"\nFROM "orders"',
        ),
        (
            "postgres",
            "normalized = count_distinct(lower(status))",
            "SELECT\n"
            '    COUNT(DISTINCT lower("status")) AS "normalized"\n'
            'FROM "orders"',
        ),
        (
            "mysql",
            "total = sum(amount + tax)",
            "SELECT\n    SUM((`amount` + `tax`)) AS `total`\nFROM `orders`",
        ),
        (
            "mysql",
            "normalized = count_distinct(lower(status))",
            "SELECT\n"
            "    COUNT(DISTINCT LOWER(`status`)) AS `normalized`\n"
            "FROM `orders`",
        ),
    ],
)
def test_emit_sql_for_expression_argument_aggregates_succeeds_after_sql_slice(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    dialect: str,
    projection: str,
    expected_sql: str,
) -> None:
    source = (
        _source_prefix("mysql.table" if dialect == "mysql" else "postgres.table")
        + "table aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        f"        {projection}\n"
    )
    script = _parse(source)
    semantic_result = analyze(script)
    ir_result = build_ir(script, semantic_result.model)
    path = _write(tmp_path, f"aggregate-expression-{dialect}.pietto", source)
    output = tmp_path / f"{dialect}.sql"

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    assert len(_aggregate_expressions(ir_result.ir)) == 1
    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                dialect,
                "--format=json",
                "--output",
                str(output),
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    result = cast(dict[str, object], json.loads(captured.out))
    artifacts = cast(list[dict[str, object]], result["artifacts"])

    assert captured.err == ""
    assert result["ok"] is True
    assert result["diagnostics"] == []
    assert result["output"] == {"path": str(output), "written": True}
    assert artifacts == [
        {
            "kind": "relation",
            "name": "aggregate_stats",
            "sql": expected_sql,
        }
    ]
    assert "PIE-B1000" not in captured.out
    assert "PIE-I1000" not in captured.out
    assert "PIE-S2315" not in captured.out
    assert output.read_text(encoding="utf-8") == expected_sql + "\n"


def _parse(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _source_prefix(connector: str) -> str:
    return (
        "shape Order:\n"
        "    status: Text not null\n"
        "    region: Text not null\n"
        "    amount: Int not null\n"
        "    tax: Int not null\n"
        "    score: Float not null\n"
        "    weight: Float not null\n"
        "    price: Decimal not null\n"
        "    active: Bool not null\n"
        f'source orders: Order is {connector}("orders")\n'
    )


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


def _projections(relation: RelationIR) -> dict[str, ProjectionIR]:
    return {str(projection.name): projection for projection in relation.projections}


def _assert_binary_aggregate(
    expression: ExpressionIR,
    *,
    function: str,
    result_type: str,
    operator: str,
    left_name: str,
    right_name: str,
    argument_type: str,
) -> None:
    assert isinstance(expression, AggregateCallIR)
    assert not isinstance(expression, CallIR)
    assert expression.function == function
    assert expression.value_type.canonical_name == result_type
    assert expression.value_type.nullability is NullabilityIR.NULLABLE
    assert len(expression.arguments) == 1
    argument = expression.arguments[0]
    assert isinstance(argument, BinaryIR)
    assert argument.operator == operator
    assert argument.value_type.canonical_name == argument_type
    _assert_field(argument.left, left_name)
    _assert_field(argument.right, right_name)


def _assert_transform_aggregate(
    expression: ExpressionIR,
    *,
    callees: Sequence[str],
    field_name: str,
) -> None:
    assert isinstance(expression, AggregateCallIR)
    assert not isinstance(expression, CallIR)
    assert expression.function == "count_distinct"
    assert expression.value_type.canonical_name == "Int"
    assert expression.value_type.nullability is NullabilityIR.NON_NULL
    assert len(expression.arguments) == 1
    current = expression.arguments[0]
    for callee in callees:
        assert isinstance(current, CallIR)
        assert current.callee == callee
        assert len(current.arguments) == 1
        current = current.arguments[0]
    _assert_field(current, field_name)


def _assert_direct_aggregate(
    expression: ExpressionIR,
    function: str,
    expected_type: str,
    expected_nullability: NullabilityIR,
    expected_arguments: tuple[str, ...],
) -> None:
    assert isinstance(expression, AggregateCallIR)
    assert not isinstance(expression, CallIR)
    assert expression.function == function
    assert expression.value_type.canonical_name == expected_type
    assert expression.value_type.nullability is expected_nullability
    assert len(expression.arguments) == len(expected_arguments)
    for argument, expected_argument in zip(
        expression.arguments,
        expected_arguments,
        strict=True,
    ):
        _assert_field(argument, expected_argument)


def _assert_field(expression: ExpressionIR, expected_name: str) -> None:
    assert isinstance(expression, FieldRefIR)
    parts = expected_name.split(".")
    assert expression.name == parts[-1]
    assert expression.qualifier == tuple(parts[:-1])
    assert expression.field == FieldId(owner=_orders_symbol(), name=parts[-1])


def _orders_symbol() -> SymbolId:
    return SymbolId(SymbolNamespace.RELATION, "orders")


def _aggregate_expressions(script_ir: ScriptIR) -> tuple[AggregateCallIR, ...]:
    aggregates: list[AggregateCallIR] = []
    for definition in script_ir.definitions:
        if not isinstance(definition, RelationIR):
            continue
        if definition.filter is not None:
            aggregates.extend(_walk_aggregates(definition.filter.expression))
        for projection in definition.projections:
            aggregates.extend(_walk_aggregates(projection.expression))
        for order_item in definition.order_by:
            aggregates.extend(_walk_aggregates(order_item.expression))
    return tuple(aggregates)


def _walk_aggregates(expression: ExpressionIR) -> Iterable[AggregateCallIR]:
    if isinstance(expression, AggregateCallIR):
        yield expression
    for child in _expression_children(expression):
        yield from _walk_aggregates(child)


def _expression_children(expression: ExpressionIR) -> tuple[ExpressionIR, ...]:
    if isinstance(expression, AggregateCallIR):
        return expression.arguments
    if isinstance(expression, CallIR):
        return expression.arguments
    if isinstance(expression, UnaryIR):
        return (expression.operand,)
    if isinstance(expression, BinaryIR):
        return (expression.left, expression.right)
    if isinstance(expression, ComparisonIR):
        return (expression.left, expression.right)
    if isinstance(expression, BetweenIR):
        return (expression.value, expression.lower, expression.upper)
    if isinstance(expression, IsNullIR):
        return (expression.value,)
    return ()


def _error_codes(result: SemanticResult) -> list[str]:
    return [
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path
