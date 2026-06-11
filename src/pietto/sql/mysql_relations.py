"""Internal MySQL rendering for minimal relation SELECT statements."""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ir.model import ExpressionIR, RelationIR, SourceIR, SymbolId
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

    projection_sql = ",\n".join(
        f"    {_render_projection(projection.expression, projection.name)}"
        for projection in relation.projections
    )
    lines = [
        "SELECT",
        projection_sql,
        f"FROM {input_sql}",
    ]
    if relation.filter is not None:
        lines.append(f"WHERE {render_mysql_expression(relation.filter.expression)}")
    return "\n".join(lines)


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
