"""Internal PostgreSQL rendering for minimal relation SELECT statements."""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ir.model import ExpressionIR, RelationIR, SourceIR, SymbolId
from pietto.sql.expressions import render_expression_sql
from pietto.sql.render import quote_identifier


def render_relation_sql(
    relation: RelationIR,
    *,
    sources: Mapping[SymbolId, SourceIR],
    relations: Mapping[SymbolId, RelationIR],
) -> str:
    """Render a minimal relation using a source table or relation-name input."""

    input_name = _relation_input_name(
        relation,
        sources=sources,
        relations=relations,
    )
    if not relation.projections:
        raise ValueError("PostgreSQL relation emission requires projections")

    projection_sql = ",\n".join(
        f"    {_render_projection(projection.expression, projection.name)}"
        for projection in relation.projections
    )
    lines = [
        "SELECT",
        projection_sql,
        f"FROM {quote_identifier(input_name)}",
    ]
    if relation.filter is not None:
        lines.append(f"WHERE {render_expression_sql(relation.filter.expression)}")
    return "\n".join(lines)


def _relation_input_name(
    relation: RelationIR,
    *,
    sources: Mapping[SymbolId, SourceIR],
    relations: Mapping[SymbolId, RelationIR],
) -> str:
    """Resolve an input to static table metadata or a relation artifact name."""

    source = sources.get(relation.source.target)
    if source is not None:
        return _postgres_table_name(source)
    upstream = relations.get(relation.source.target)
    if upstream is not None:
        return upstream.name
    raise ValueError(
        "PostgreSQL relation input does not resolve to SourceIR or RelationIR"
    )


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
