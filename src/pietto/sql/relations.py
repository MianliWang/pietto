"""Internal PostgreSQL rendering for minimal source-backed relations."""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ir.model import ExpressionIR, RelationIR, SourceIR, SymbolId
from pietto.sql.expressions import render_expression_sql
from pietto.sql.render import quote_identifier


def render_relation_sql(
    relation: RelationIR,
    *,
    sources: Mapping[SymbolId, SourceIR],
) -> str:
    """Render a minimal relation whose input is a PostgreSQL table source."""

    source = sources.get(relation.source.target)
    if source is None:
        raise ValueError(
            "PostgreSQL relation emission currently requires a direct SourceIR input"
        )
    table_name = _postgres_table_name(source)
    if not relation.projections:
        raise ValueError("PostgreSQL relation emission requires projections")

    projection_sql = ",\n".join(
        f"    {_render_projection(projection.expression, projection.name)}"
        for projection in relation.projections
    )
    lines = [
        "SELECT",
        projection_sql,
        f"FROM {quote_identifier(table_name)}",
    ]
    if relation.filter is not None:
        lines.append(f"WHERE {render_expression_sql(relation.filter.expression)}")
    return "\n".join(lines)


def _postgres_table_name(source: SourceIR) -> str:
    """Return the single static table name supported by this backend slice."""

    connector = source.connector
    if (
        connector.name != "postgres.table"
        or len(connector.arguments) != 1
        or not isinstance(connector.arguments[0], str)
        or not connector.arguments[0]
    ):
        raise ValueError("PostgreSQL relation emission requires postgres.table(Text)")
    return connector.arguments[0]


def _render_projection(expression: ExpressionIR, name: str | None) -> str:
    """Render one expression with a stable explicit output alias when present."""

    sql = render_expression_sql(expression)
    if name is None:
        return sql
    return f"{sql} AS {quote_identifier(name)}"
