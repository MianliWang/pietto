"""Shared semantic-expression fixtures."""

from __future__ import annotations

from pietto.ast_nodes import Expression, QueryDef, Script, TableDef
from pietto.parser_api import parse_source
from pietto.semantic import ValueType, analyze


_BOUNDARY_SHAPE = """shape Order:
    status: Text not null
    active: Bool not null
    amount: Int not null
    tax: Int not null
    optional_amount: Int nullable
    score: Float not null
    weight: Float nullable
    price: Decimal not null
    discount: Decimal nullable
    order_date: Date nullable
    created_at: Timestamp not null
"""


def expression_facts(
    expression_source: str,
) -> tuple[ValueType, tuple[tuple[str, str], ...]]:
    """Return source typing and diagnostics for a projected expression."""
    script = _parse(_projected_source("postgres.table", f"value = {expression_source}"))
    result = analyze(script)
    expression = _select_expression(_relation_ast(script), "value")
    return result.model.expression_value_types[expression], tuple(
        (diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics
    )


def _projected_source(connector: str, projections: str) -> str:
    return (
        _BOUNDARY_SHAPE
        + f'source orders: Order is {connector}("orders")\n'
        + "table projected:\n"
        + "    from orders\n"
        + "    select:\n"
        + f"        {projections}\n"
    )


def _parse(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _relation_ast(script: Script) -> TableDef | QueryDef:
    relation = script.definitions[-1]
    assert isinstance(relation, (TableDef, QueryDef))
    return relation


def _select_expression(relation: TableDef | QueryDef, alias: str) -> Expression:
    for item in relation.select_items:
        if item.alias == alias:
            return item.expression
        if item.alias is None and getattr(item.expression, "name", None) == alias:
            return item.expression
    raise AssertionError(f"Missing select item: {alias}")
