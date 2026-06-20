"""Internal PostgreSQL rendering for minimal relation SELECT statements."""

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
from pietto.sql.expressions import (
    expression_uses_qualified_field,
    render_expression_sql,
)
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
    if relation.result_predicate is not None and not relation.group_keys:
        raise ValueError("PostgreSQL result predicate requires GROUP BY")
    if relation.group_keys:
        _validate_grouped_relation(relation)

    projection_sql = ",\n".join(
        f"    {_render_projection(projection.expression, projection.name)}"
        for projection in relation.projections
    )
    lines = [
        "SELECT",
        projection_sql,
        f"FROM {_render_input(input_name, relation)}",
    ]
    if relation.filter is not None:
        lines.append(f"WHERE {render_expression_sql(relation.filter.expression)}")
    if relation.group_keys:
        lines.extend(
            (
                "GROUP BY",
                ",\n".join(
                    f"    {_render_group_key(key)}" for key in relation.group_keys
                ),
            )
        )
    if relation.result_predicate is not None:
        lines.extend(
            (
                "HAVING",
                f"    {render_expression_sql(relation.result_predicate.expression)}",
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


def _render_input(input_name: str, relation: RelationIR) -> str:
    """Alias an input only when qualified field SQL needs its logical name."""

    sql = quote_identifier(input_name)
    if not _relation_uses_qualified_fields(relation):
        return sql
    return f"{sql} AS {quote_identifier(relation.source.name)}"


def _relation_uses_qualified_fields(relation: RelationIR) -> bool:
    expressions = [projection.expression for projection in relation.projections]
    if relation.filter is not None:
        expressions.append(relation.filter.expression)
    if relation.result_predicate is not None:
        expressions.append(relation.result_predicate.expression)
    expressions.extend(item.expression for item in relation.order_by)
    expressions.extend(relation.group_keys)
    return any(
        expression_uses_qualified_field(expression) for expression in expressions
    )


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


def _validate_grouped_relation(relation: RelationIR) -> None:
    """Fail closed for grouped IR shapes not authorized by the semantic slice."""

    group_fields = _group_key_fields(relation.group_keys)
    orderable_expressions: list[ExpressionIR] = []
    saw_aggregate = False
    for projection in relation.projections:
        expression = projection.expression
        if isinstance(expression, AggregateCallIR):
            saw_aggregate = True
            orderable_expressions.append(expression)
            continue
        if isinstance(expression, FieldRefIR) and expression.field in group_fields:
            orderable_expressions.append(expression)
            continue
        raise ValueError(
            "PostgreSQL grouped projection is neither a GROUP BY key nor aggregate"
        )

    if not saw_aggregate:
        raise ValueError(
            "PostgreSQL pure grouped output without an aggregate is not supported"
        )

    _validate_grouped_order_by(relation.order_by, orderable_expressions)


def _validate_grouped_order_by(
    order_by: tuple[OrderItemIR, ...],
    orderable_expressions: list[ExpressionIR],
) -> None:
    """Allow grouped ordering only by selected group-key or aggregate outputs."""

    for item in order_by:
        if not any(
            item.expression == expression for expression in orderable_expressions
        ):
            raise ValueError(
                "PostgreSQL grouped ORDER BY expression must match a selected "
                "GROUP BY key or aggregate projection"
            )


def _group_key_fields(group_keys: tuple[FieldRefIR, ...]) -> set[FieldId]:
    fields: set[FieldId] = set()
    for key in group_keys:
        if not isinstance(key, FieldRefIR) or key.field is None:
            raise ValueError("PostgreSQL GROUP BY keys must be resolved fields")
        if key.field in fields:
            raise ValueError("PostgreSQL GROUP BY keys must be unique")
        fields.add(key.field)
    return fields


def _render_group_key(key: FieldRefIR) -> str:
    if not isinstance(key, FieldRefIR) or key.field is None:
        raise ValueError("PostgreSQL GROUP BY keys must be resolved fields")
    return render_expression_sql(key)


def _render_limit(value: int) -> str:
    """Render a validated static limit and fail closed for malformed IR."""

    if type(value) is not int or not 0 <= value <= 9_223_372_036_854_775_807:
        raise ValueError("PostgreSQL relation limit is outside the supported range")
    return str(value)


def _render_order_item(item: OrderItemIR) -> str:
    """Render one validated sorting item without dropping its direction."""

    if not isinstance(item.direction, OrderDirectionIR):
        raise ValueError("PostgreSQL relation order direction is invalid")
    return f"{render_expression_sql(item.expression)} {item.direction.value}"
