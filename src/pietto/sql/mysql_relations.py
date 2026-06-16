"""Internal MySQL rendering for minimal relation SELECT statements."""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ir.model import (
    AggregateCallIR,
    ExpressionIR,
    FieldId,
    FieldRefIR,
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

    quote_identifier(relation.name, context="relation identifier")
    input_sql = _relation_input_sql(
        relation,
        sources=sources,
        relations=relations,
    )
    if not relation.projections:
        raise MySqlRenderError("MySQL relation emission requires projections")
    if relation.group_keys:
        _validate_grouped_relation(relation)

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
    if relation.group_keys:
        lines.extend(
            (
                "GROUP BY",
                ",\n".join(
                    f"    {_render_group_key(key)}" for key in relation.group_keys
                ),
            )
        )
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
    expressions.extend(relation.group_keys)
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


def _validate_grouped_relation(relation: RelationIR) -> None:
    if relation.order_by:
        raise MySqlRenderError("MySQL grouped ORDER BY is not supported")

    group_fields = _group_key_fields(relation.group_keys)
    saw_aggregate = False
    for projection in relation.projections:
        expression = projection.expression
        if isinstance(expression, AggregateCallIR):
            saw_aggregate = True
            continue
        if isinstance(expression, FieldRefIR) and expression.field in group_fields:
            continue
        raise MySqlRenderError(
            "MySQL grouped projection is neither a GROUP BY key nor aggregate"
        )

    if not saw_aggregate:
        raise MySqlRenderError(
            "MySQL pure grouped output without an aggregate is not supported"
        )


def _group_key_fields(group_keys: tuple[FieldRefIR, ...]) -> set[FieldId]:
    fields: set[FieldId] = set()
    for key in group_keys:
        if not isinstance(key, FieldRefIR) or key.field is None:
            raise MySqlRenderError("MySQL GROUP BY keys must be resolved fields")
        if key.field in fields:
            raise MySqlRenderError("MySQL GROUP BY keys must be unique")
        fields.add(key.field)
    return fields


def _render_group_key(key: FieldRefIR) -> str:
    if not isinstance(key, FieldRefIR) or key.field is None:
        raise MySqlRenderError("MySQL GROUP BY keys must be resolved fields")
    return render_mysql_expression(key)


def _render_limit(value: int) -> str:
    if type(value) is not int or not 0 <= value <= 9_223_372_036_854_775_807:
        raise MySqlRenderError("MySQL relation limit is outside the supported range")
    return str(value)


def _render_order_item(item: OrderItemIR) -> str:
    if not isinstance(item.direction, OrderDirectionIR):
        raise MySqlRenderError("MySQL relation order direction is invalid")
    return f"{render_mysql_expression(item.expression)} {item.direction.value}"
