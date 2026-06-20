from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.ast_nodes import QueryDef, Script, TableDef
from pietto.errors import Severity
from pietto.ir import (
    AggregateCallIR,
    BinaryIR,
    CallIR,
    ComparisonIR,
    ExpressionIR,
    FieldId,
    FieldRefIR,
    LiteralIR,
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
from pietto.semantic import analyze

SOURCE_PREFIX = (
    "shape Order:\n"
    "    status: Text not null\n"
    "    region: Text not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    score: Float not null\n"
    "    weight: Float not null\n"
    "    price: Decimal not null\n"
    "    discount: Decimal not null\n"
    "    active: Bool not null\n"
    'source orders: Order is postgres.table("orders")\n'
)


def test_numeric_literal_aggregate_arguments_lower_to_existing_ir_nodes() -> None:
    relation = _compile_relation(
        SOURCE_PREFIX + "table aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        plus_total = sum(amount + 1)\n"
        "        left_literal_total = sum(1 + amount)\n"
        "        minus_total = sum(amount - 1)\n"
        "        multiplied_total = sum(amount * 2)\n"
        "        weighted_average = avg(score * 2)\n"
        "        adjusted_average = avg(score + 1.5)\n"
    )
    projections = _projections(relation)

    _assert_binary_aggregate(
        projections["plus_total"].expression,
        function="sum",
        result_type="Int",
        operator="+",
        argument_type="Int",
        left="amount",
        right=1,
    )
    _assert_binary_aggregate(
        projections["left_literal_total"].expression,
        function="sum",
        result_type="Int",
        operator="+",
        argument_type="Int",
        left=1,
        right="amount",
    )
    _assert_binary_aggregate(
        projections["minus_total"].expression,
        function="sum",
        result_type="Int",
        operator="-",
        argument_type="Int",
        left="amount",
        right=1,
    )
    _assert_binary_aggregate(
        projections["multiplied_total"].expression,
        function="sum",
        result_type="Int",
        operator="*",
        argument_type="Int",
        left="amount",
        right=2,
    )
    _assert_binary_aggregate(
        projections["weighted_average"].expression,
        function="avg",
        result_type="Float",
        operator="*",
        argument_type="Float",
        left="score",
        right=2,
    )
    _assert_binary_aggregate(
        projections["adjusted_average"].expression,
        function="avg",
        result_type="Float",
        operator="+",
        argument_type="Float",
        left="score",
        right=1.5,
    )


def test_qualified_field_and_unary_leaves_lower_inside_aggregate_arguments() -> None:
    relation = _compile_relation(
        SOURCE_PREFIX + "table aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        total = sum(+orders.amount + 1)\n"
        "        average = avg(-orders.score + 1.5)\n"
    )
    projections = _projections(relation)

    total = _assert_binary_aggregate(
        projections["total"].expression,
        function="sum",
        result_type="Int",
        operator="+",
        argument_type="Int",
        left=None,
        right=1,
    )
    _assert_unary_operand(total.left, "+", "orders.amount")

    average = _assert_binary_aggregate(
        projections["average"].expression,
        function="avg",
        result_type="Float",
        operator="+",
        argument_type="Float",
        left=None,
        right=1.5,
    )
    _assert_unary_operand(average.left, "-", "orders.score")


def test_grouped_numeric_literal_aggregates_lower_with_group_keys() -> None:
    relation = _compile_relation(
        SOURCE_PREFIX + "table aggregate_stats_by_status:\n"
        "    from orders\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total = sum(amount + 1)\n"
        "        average = avg(score * 2)\n"
    )
    projections = _projections(relation)

    assert [key.name for key in relation.group_keys] == ["status"]
    assert [key.qualifier for key in relation.group_keys] == [()]
    assert [key.field for key in relation.group_keys] == [
        FieldId(owner=_orders_symbol(), name="status")
    ]
    _assert_field(projections["status"].expression, "status")
    _assert_binary_aggregate(
        projections["total"].expression,
        function="sum",
        result_type="Int",
        operator="+",
        argument_type="Int",
        left="amount",
        right=1,
    )
    _assert_binary_aggregate(
        projections["average"].expression,
        function="avg",
        result_type="Float",
        operator="*",
        argument_type="Float",
        left="score",
        right=2,
    )


def test_direct_lower_expr_for_numeric_literal_aggregate_uses_aggregate_call_ir() -> (
    None
):
    script = _parse(
        SOURCE_PREFIX + "table aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        total = sum(amount + 1)\n"
    )
    relation = _relation_ast(script)
    semantic_result = analyze(script)
    input_schema = next(iter(semantic_result.model.source_row_schemas.values()))

    lowered = lower_expr(
        relation.select_items[0].expression,
        semantic_result.model,
        fields=input_schema.fields,
        field_owner=_orders_symbol(),
        field_qualifier="orders",
    )

    assert _error_codes(semantic_result) == []
    assert lowered.diagnostics == ()
    _assert_binary_aggregate(
        cast(ExpressionIR, lowered.expression),
        function="sum",
        result_type="Int",
        operator="+",
        argument_type="Int",
        left="amount",
        right=1,
    )


def test_phase26_field_only_expression_aggregate_arguments_still_lower() -> None:
    relation = _compile_relation(
        SOURCE_PREFIX + "table aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        total = sum(amount + tax)\n"
        "        weighted = avg(score * weight)\n"
        "        decimal_total = sum(price + discount)\n"
        "        decimal_average = avg(price - discount)\n"
    )
    projections = _projections(relation)

    _assert_binary_aggregate(
        projections["total"].expression,
        function="sum",
        result_type="Int",
        operator="+",
        argument_type="Int",
        left="amount",
        right="tax",
    )
    _assert_binary_aggregate(
        projections["weighted"].expression,
        function="avg",
        result_type="Float",
        operator="*",
        argument_type="Float",
        left="score",
        right="weight",
    )
    _assert_binary_aggregate(
        projections["decimal_total"].expression,
        function="sum",
        result_type="Decimal",
        operator="+",
        argument_type="Decimal",
        left="price",
        right="discount",
    )
    _assert_binary_aggregate(
        projections["decimal_average"].expression,
        function="avg",
        result_type="Decimal",
        operator="-",
        argument_type="Decimal",
        left="price",
        right="discount",
    )


def test_source_level_emit_sql_remains_backend_fail_closed_after_ir_lowering(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = (
        SOURCE_PREFIX + "table aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        total = sum(amount + 1)\n"
        "        average = avg(score * 2)\n"
    )
    script = _parse(source)
    semantic_result = analyze(script)
    ir_result = build_ir(script, semantic_result.model)
    path = _write(tmp_path, "numeric-literal-aggregate.pietto", source)
    output = _write(tmp_path, "aggregate.sql", "stale SQL\n")

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    assert len(_aggregate_expressions(ir_result.ir)) == 2
    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format=json",
                "--output",
                str(output),
            ]
        )
        == 1
    )

    captured = capsys.readouterr()
    result = cast(dict[str, object], json.loads(captured.out))
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])

    assert captured.err == ""
    assert result["ok"] is False
    assert result["cli_errors"] == []
    assert [diagnostic["code"] for diagnostic in diagnostics] == ["PIE-B1000"]
    assert result["artifacts"] == []
    assert result["output"] == {"path": str(output), "written": False}
    assert output.read_text(encoding="utf-8") == "stale SQL\n"


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
        ("value = sum(avg(amount))", "PIE-S2311"),
        ("value = sum(amount) + 1", "PIE-S2310"),
        ("value = count(amount + 1)", "PIE-S2315"),
        ("value = min(amount + 1)", "PIE-S2315"),
        ("value = max(score * 2)", "PIE-S2315"),
        ("value = count_distinct(len(status))", "PIE-S2315"),
        ("value = sum(price + 1)", "PIE-S2315"),
        ("value = sum(price + 1.5)", "PIE-S2315"),
        ("value = sum(price * discount)", "PIE-S2315"),
    ],
)
def test_unsupported_numeric_literal_aggregate_shapes_remain_before_ir(
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


def _compile_relation(source: str) -> RelationIR:
    script = _parse(source)
    semantic_result = analyze(script)
    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return _relation_ir(ir_result.ir)


def _parse(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


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
    argument_type: str,
    left: str | int | float | None,
    right: str | int | float | None,
) -> BinaryIR:
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
    if left is not None:
        _assert_operand(argument.left, left)
    if right is not None:
        _assert_operand(argument.right, right)
    return argument


def _assert_operand(
    expression: ExpressionIR,
    expected: str | int | float,
) -> None:
    if isinstance(expected, str):
        _assert_field(expression, expected)
        return
    _assert_literal(expression, expected)


def _assert_field(expression: ExpressionIR, expected_name: str) -> None:
    assert isinstance(expression, FieldRefIR)
    parts = expected_name.split(".")
    assert expression.name == parts[-1]
    assert expression.qualifier == tuple(parts[:-1])
    assert expression.field == FieldId(owner=_orders_symbol(), name=parts[-1])


def _assert_literal(expression: ExpressionIR, expected_value: int | float) -> None:
    assert isinstance(expression, LiteralIR)
    assert expression.value == expected_value
    if type(expected_value) is int:
        assert expression.value_type.canonical_name == "Int"
    else:
        assert type(expected_value) is float
        assert expression.value_type.canonical_name == "Float"


def _assert_unary_operand(
    expression: ExpressionIR,
    expected_operator: str,
    expected_operand: str,
) -> None:
    assert isinstance(expression, UnaryIR)
    assert expression.operator == expected_operator
    _assert_field(expression.operand, expected_operand)


def _orders_symbol() -> SymbolId:
    return SymbolId(SymbolNamespace.RELATION, "orders")


def _aggregate_expressions(script_ir: ScriptIR) -> tuple[AggregateCallIR, ...]:
    aggregates: list[AggregateCallIR] = []
    for definition in script_ir.definitions:
        if not isinstance(definition, RelationIR):
            continue
        for projection in definition.projections:
            aggregates.extend(_walk_aggregates(projection.expression))
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
    return ()


def _error_codes(result: object) -> list[str]:
    diagnostics = getattr(result, "diagnostics")
    return [
        diagnostic.code
        for diagnostic in diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path
