"""Internal MySQL rendering for minimal relation SELECT statements."""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ir.model import (
    ExpressionIR,
    OrderDirectionIR,
    OrderItemIR,
    RelationIR,
    SourceIR,
    SymbolId,
)
from pietto.sql.expressions import expression_uses_qualified_field
from pietto.sql.mysql_expressions import render_mysql_expression
from pietto.sql.mysql_render import (
    MYSQL_ALIAS_MAX_CHARACTERS,
    MySqlRenderError,
    quote_identifier,
)


def render_mysql_relation(
    relation: RelationIR,
    *,
    sources: Mapping[SymbolId, SourceIR],
    relations: Mapping[SymbolId, RelationIR],
) -> str:
    """Render a minimal relation using a MySQL source or relation-name input."""

    if relation.group_keys:
        raise MySqlRenderError("MySQL grouped relation SQL lowering is not implemented")
    quote_identifier(relation.name, context="relation identifier")
    input_sql = _relation_input_sql(
        relation,
        sources=sources,
        relations=relations,
    )
    if not relation.projections:
        raise MySqlRenderError("MySQL relation emission requires projections")

    projection_sql = ",\n".join(
        f"    {_render_projection(projection.expression, projection.name)}"
        for projection in relation.projections
    )
    lines = [
        "SELECT",
        projection_sql,
        f"FROM {_render_input(input_sql, relation)}",
    ]
    if relation.filter is not None:
        lines.append(f"WHERE {render_mysql_expression(relation.filter.expression)}")
    if relation.order_by:
        lines.extend(
            (
                "ORDER BY",
                ",\n".join(
                    f"    {_render_order_item(item)}" for item in relation.order_by
                ),
            )
        )
    if relation.limit is not None:
        lines.append(f"LIMIT {_render_limit(relation.limit.value)}")
    return "\n".join(lines)


def _render_input(input_sql: str, relation: RelationIR) -> str:
    """Alias an input only when qualified field SQL needs its logical name."""

    if not _relation_uses_qualified_fields(relation):
        return input_sql
    alias = quote_identifier(relation.source.name, context="relation identifier")
    return f"{input_sql} AS {alias}"


def _relation_uses_qualified_fields(relation: RelationIR) -> bool:
    expressions = [projection.expression for projection in relation.projections]
    if relation.filter is not None:
        expressions.append(relation.filter.expression)
    expressions.extend(item.expression for item in relation.order_by)
    return any(
        expression_uses_qualified_field(expression) for expression in expressions
    )


def _relation_input_sql(
    relation: RelationIR,
    *,
    sources: Mapping[SymbolId, SourceIR],
    relations: Mapping[SymbolId, RelationIR],
) -> str:
    source = sources.get(relation.source.target)
    if source is not None:
        return quote_identifier(
            _mysql_table_name(source),
            context="physical table identifier",
        )
    upstream = relations.get(relation.source.target)
    if upstream is not None:
        if upstream.group_keys:
            raise MySqlRenderError(
                "MySQL relation input depends on unsupported grouped lowering"
            )
        return quote_identifier(upstream.name, context="relation identifier")
    raise MySqlRenderError(
        "MySQL relation input does not resolve to SourceIR or RelationIR"
    )


def _mysql_table_name(source: SourceIR) -> str:
    connector = source.connector
    if (
        connector.name != "mysql.table"
        or len(connector.arguments) != 1
        or not isinstance(connector.arguments[0], str)
        or not connector.arguments[0]
    ):
        raise MySqlRenderError("MySQL relation emission requires mysql.table(Text)")
    return connector.arguments[0]


def _render_projection(expression: ExpressionIR, name: str | None) -> str:
    sql = render_mysql_expression(expression)
    if name is None:
        return sql
    alias = quote_identifier(
        name,
        max_characters=MYSQL_ALIAS_MAX_CHARACTERS,
        context="select-list alias",
    )
    return f"{sql} AS {alias}"


def _render_limit(value: int) -> str:
    if type(value) is not int or not 0 <= value <= 9_223_372_036_854_775_807:
        raise MySqlRenderError("MySQL relation limit is outside the supported range")
    return str(value)


def _render_order_item(item: OrderItemIR) -> str:
    if not isinstance(item.direction, OrderDirectionIR):
        raise MySqlRenderError("MySQL relation order direction is invalid")
    return f"{render_mysql_expression(item.expression)} {item.direction.value}"
