from __future__ import annotations

import pytest

from pietto.ast_nodes import Script
from pietto.errors import Severity
from pietto.ir import (
    AggregateCallIR,
    BinaryIR,
    CallIR,
    ComparisonIR,
    FieldId,
    FieldRefIR,
    RelationIR,
    ScriptIR,
    SymbolId,
    SymbolNamespace,
    build_ir,
)
from pietto.ir.model import OrderDirectionIR
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, analyze

SOURCE_PREFIX = (
    "shape Order:\n"
    "    region: Text not null\n"
    "    status: Text not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    score: Float not null\n"
    "    weight: Float not null\n"
    'source orders: Order is postgres.table("orders")\n'
)


def test_grouped_order_lowers_bare_group_key_output() -> None:
    relation, semantic_result = _compile_relation(
        _grouped_relation(
            projections=("region", "total = count()"),
            order_items=("region",),
        )
    )

    assert _errors(semantic_result) == []
    item = relation.order_by[0]
    assert item.direction is OrderDirectionIR.ASC
    _assert_field_order(item.expression, name="region", qualifier=())


def test_grouped_order_lowers_aliased_group_key_to_underlying_field() -> None:
    relation, semantic_result = _compile_relation(
        _grouped_relation(
            group_keys=("orders.region",),
            projections=("r = orders.region", "total = count()"),
            order_items=("r desc",),
        )
    )

    assert _errors(semantic_result) == []
    item = relation.order_by[0]
    assert item.direction is OrderDirectionIR.DESC
    field = _assert_field_order(item.expression, name="region", qualifier=("orders",))
    assert field.name != "r"


@pytest.mark.parametrize(
    ("projection", "function", "argument_names"),
    [
        ("total = count()", "count", ()),
        ("total = sum(amount)", "sum", ("amount",)),
        ("average_score = avg(score)", "avg", ("score",)),
        ("unique_statuses = count_distinct(status)", "count_distinct", ("status",)),
    ],
)
def test_grouped_order_lowers_direct_aggregate_aliases(
    projection: str,
    function: str,
    argument_names: tuple[str, ...],
) -> None:
    relation, semantic_result = _compile_relation(
        _grouped_relation(
            projections=("region", projection),
            order_items=(_projection_alias(projection),),
        )
    )

    assert _errors(semantic_result) == []
    aggregate = _assert_aggregate_order(relation.order_by[0].expression, function)
    assert [_field_argument(argument).name for argument in aggregate.arguments] == [
        *argument_names
    ]


def test_grouped_order_lowers_numeric_expression_aggregate_alias() -> None:
    relation, semantic_result = _compile_relation(
        _grouped_relation(
            projections=("region", "total = sum(amount + tax)"),
            order_items=("total desc",),
        )
    )

    assert _errors(semantic_result) == []
    item = relation.order_by[0]
    assert item.direction is OrderDirectionIR.DESC
    aggregate = _assert_aggregate_order(item.expression, "sum")
    assert len(aggregate.arguments) == 1
    argument = aggregate.arguments[0]
    assert isinstance(argument, BinaryIR)
    assert argument.operator == "+"
    assert _field_argument(argument.left).name == "amount"
    assert _field_argument(argument.right).name == "tax"


def test_grouped_order_lowers_text_transform_aggregate_alias() -> None:
    relation, semantic_result = _compile_relation(
        _grouped_relation(
            projections=("region", "normalized = count_distinct(lower(trim(status)))"),
            order_items=("normalized desc",),
        )
    )

    assert _errors(semantic_result) == []
    aggregate = _assert_aggregate_order(
        relation.order_by[0].expression, "count_distinct"
    )
    assert len(aggregate.arguments) == 1
    lower_call = aggregate.arguments[0]
    assert isinstance(lower_call, CallIR)
    assert lower_call.callee == "lower"
    trim_call = lower_call.arguments[0]
    assert isinstance(trim_call, CallIR)
    assert trim_call.callee == "trim"
    assert _field_argument(trim_call.arguments[0]).name == "status"


def test_grouped_satisfying_and_order_by_lower_underlying_expressions() -> None:
    relation, semantic_result = _compile_relation(
        _grouped_relation(
            projections=("region", "total = sum(amount + tax)"),
            satisfying="total > 1000",
            order_items=("total desc", "region asc"),
        )
    )

    assert _errors(semantic_result) == []
    assert relation.result_predicate is not None
    assert isinstance(relation.result_predicate.expression, ComparisonIR)
    assert len(relation.order_by) == 2
    _assert_aggregate_order(relation.order_by[0].expression, "sum")
    _assert_field_order(relation.order_by[1].expression, name="region", qualifier=())


def test_grouped_order_preserves_duplicates_and_source_order() -> None:
    relation, semantic_result = _compile_relation(
        _grouped_relation(
            projections=("region", "total = count()"),
            order_items=("total desc", "region", "total asc"),
        )
    )

    assert _errors(semantic_result) == []
    assert [item.direction for item in relation.order_by] == [
        OrderDirectionIR.DESC,
        OrderDirectionIR.ASC,
        OrderDirectionIR.ASC,
    ]
    assert [_order_expression_label(item.expression) for item in relation.order_by] == [
        "count",
        "region",
        "count",
    ]


def test_no_group_order_by_still_uses_input_scope_ir() -> None:
    relation, semantic_result = _compile_relation(
        SOURCE_PREFIX + "table sorted_orders:\n"
        "    from orders\n"
        "    select:\n"
        "        amount_alias = amount\n"
        "    order by:\n"
        "        amount desc\n",
        name="sorted_orders",
    )

    assert _errors(semantic_result) == []
    item = relation.order_by[0]
    assert item.direction is OrderDirectionIR.DESC
    _assert_field_order(item.expression, name="amount", qualifier=())


def test_no_group_projection_alias_still_does_not_resolve_in_order_by() -> None:
    script = _parse(
        SOURCE_PREFIX + "table sorted_orders:\n"
        "    from orders\n"
        "    select:\n"
        "        sort_key = lower(status)\n"
        "    order by:\n"
        "        sort_key\n"
    )

    assert _errors(analyze(script)) == [("PIE-S2102", "Unknown field: sort_key")]


def test_unsupported_grouped_order_fails_before_ir_with_s2321() -> None:
    script = _parse(
        _grouped_relation(
            projections=("region", "total = count()"),
            order_items=("sum(amount)",),
        )
    )

    semantic_result = analyze(script)

    assert _errors(semantic_result) == [
        (
            "PIE-S2321",
            "Unsupported grouped ORDER BY item; expected a supported select output name",
        )
    ]


def test_grouped_order_ordinal_remains_parser_owned() -> None:
    parse_result = parse_source(
        _grouped_relation(
            projections=("region", "total = count()"),
            order_items=("1",),
        ),
        path="phase27-grouped-order-ir.pietto",
    )

    assert parse_result.ast is None
    assert [diagnostic.code for diagnostic in parse_result.diagnostics] == ["PIE-P1000"]


def _grouped_relation(
    *,
    projections: tuple[str, ...],
    order_items: tuple[str, ...],
    group_keys: tuple[str, ...] = ("region",),
    satisfying: str | None = None,
) -> str:
    key_block = "".join(f"        {key}\n" for key in group_keys)
    projection_block = "".join(f"        {projection}\n" for projection in projections)
    satisfying_block = (
        "" if satisfying is None else f"    satisfying:\n        {satisfying}\n"
    )
    order_block = "".join(f"        {item}\n" for item in order_items)
    return (
        SOURCE_PREFIX + "table grouped_orders:\n"
        "    from orders\n"
        "    group by:\n"
        f"{key_block}"
        "    select:\n"
        f"{projection_block}"
        f"{satisfying_block}"
        "    order by:\n"
        f"{order_block}"
    )


def _parse(source: str) -> Script:
    parse_result = parse_source(source, path="phase27-grouped-order-ir.pietto")
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None
    return parse_result.ast


def _compile_relation(
    source: str,
    *,
    name: str = "grouped_orders",
) -> tuple[RelationIR, SemanticResult]:
    script = _parse(source)
    semantic_result = analyze(script)
    ir_result = build_ir(script, semantic_result.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return _relation_ir(ir_result.ir, name), semantic_result


def _relation_ir(script_ir: ScriptIR, name: str) -> RelationIR:
    matches = [
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR) and definition.name == name
    ]
    assert len(matches) == 1
    return matches[0]


def _assert_field_order(
    expression: object,
    *,
    name: str,
    qualifier: tuple[str, ...],
) -> FieldRefIR:
    assert isinstance(expression, FieldRefIR)
    assert expression.name == name
    assert expression.qualifier == qualifier
    assert expression.field == FieldId(owner=_orders_symbol(), name=name)
    return expression


def _assert_aggregate_order(expression: object, function: str) -> AggregateCallIR:
    assert isinstance(expression, AggregateCallIR)
    assert expression.function == function
    return expression


def _field_argument(expression: object) -> FieldRefIR:
    assert isinstance(expression, FieldRefIR)
    assert expression.field == FieldId(owner=_orders_symbol(), name=expression.name)
    return expression


def _order_expression_label(expression: object) -> str:
    if isinstance(expression, AggregateCallIR):
        return expression.function
    if isinstance(expression, FieldRefIR):
        return expression.name
    raise AssertionError(f"Unexpected order expression: {type(expression).__name__}")


def _projection_alias(projection: str) -> str:
    return projection.split("=", maxsplit=1)[0].strip()


def _orders_symbol() -> SymbolId:
    return SymbolId(SymbolNamespace.RELATION, "orders")


def _errors(result: SemanticResult) -> list[tuple[str, str]]:
    return [
        (diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]
