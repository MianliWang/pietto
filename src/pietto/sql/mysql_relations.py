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
    NamedWindowDeclarationIR,
    RelationIR,
    SourceIR,
    SymbolId,
    WindowCallIR,
    WindowUseKindIR,
)
from pietto.sql.expressions import expression_uses_qualified_field
from pietto.sql.mysql_expressions import (
    render_mysql_expression,
    render_mysql_window_call,
    render_mysql_window_components,
)
from pietto.sql.mysql_render import (
    MYSQL_ALIAS_MAX_CHARACTERS,
    MySqlRenderError,
    quote_identifier,
)
from pietto.sql.relations import (
    has_untyped_result_predicate,
    hidden_table_read,
    _exists_relation_dependencies,
    _validate_exists_targets,
    qualify_alias_captured_order_fields,
)
from pietto.sql.window_strategy import (
    NamedWindowLoweringDecision,
    NamedWindowLoweringStrategy,
    WindowTargetDialect,
    decide_named_window_lowering,
)


def render_mysql_relation(
    relation: RelationIR,
    *,
    sources: Mapping[SymbolId, SourceIR],
    relations: Mapping[SymbolId, RelationIR],
    _include_exists_dependencies: bool = True,
) -> str:
    """Render a minimal relation using a MySQL source or relation-name input."""

    try:
        dependencies = (
            _exists_relation_dependencies(relation, relations)
            if _include_exists_dependencies
            else ()
        )
        _validate_exists_targets(relation, sources, relations)
    except ValueError as error:
        raise MySqlRenderError(str(error)) from error
    if relation.joins:
        raise MySqlRenderError("MySQL JOIN emission is not available yet")
    quote_identifier(relation.name, context="relation identifier")
    input_sql, input_reference = _relation_input_sql(
        relation,
        sources=sources,
        relations=relations,
    )
    if not relation.projections:
        raise MySqlRenderError("MySQL relation emission requires projections")
    if has_untyped_result_predicate(relation):
        raise MySqlRenderError("MySQL result predicate requires a known Bool type")
    if relation.result_predicate is not None and not relation.group_keys:
        raise MySqlRenderError("MySQL result predicate requires GROUP BY")
    _validate_window_clause_boundaries(relation)
    if relation.group_keys:
        _validate_grouped_relation(relation)

    named_decision = decide_named_window_lowering(
        relation,
        WindowTargetDialect.MYSQL,
    )
    if named_decision is not None and named_decision.strategy is (
        NamedWindowLoweringStrategy.NOT_LOWERABLE
    ):
        raise MySqlRenderError(named_decision.reason)
    # A qualified field already aliases the input with its Pietto name; else
    # a captured key is qualified with the table's own name and FROM is kept.
    alias = relation.source.name if _relation_uses_qualified_fields(relation) else None
    relation = qualify_alias_captured_order_fields(
        relation,
        qualifier=alias or input_reference,
        mysql=True,
    )

    projection_sql = ",\n".join(
        f"    {_render_projection(projection.expression, projection.name, named_decision)}"
        for projection in relation.projections
    )
    lines = [
        "SELECT",
        projection_sql,
        f"FROM {_render_input(input_sql, alias)}",
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
    if relation.result_predicate is not None:
        lines.extend(
            (
                "HAVING",
                f"    {render_mysql_expression(relation.result_predicate.expression)}",
            )
        )
    if named_decision is not None and named_decision.strategy in {
        NamedWindowLoweringStrategy.NATIVE_PRESERVE,
        NamedWindowLoweringStrategy.NATIVE_REORDER,
    }:
        lines.extend(
            (
                "WINDOW",
                ",\n".join(
                    f"    {_render_named_declaration(declaration)}"
                    for declaration in named_decision.emission_declarations
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
    sql = "\n".join(lines)
    if dependencies:
        definitions = ",\n".join(
            f"{quote_identifier(item.name, context='relation identifier')} AS (\n{render_mysql_relation(item, sources=sources, relations=relations, _include_exists_dependencies=False)}\n)"
            for item in dependencies
        )
        hidden = hidden_table_read(
            relation, dependencies, sources, relations, mysql=True
        )
        if hidden is not None:
            raise MySqlRenderError(
                f"MySQL scalar ANY defines relation {hidden[0]} as a CTE, which "
                f"would hide table {hidden[1]} read in the same SQL; rename the "
                "relation or read the table with its schema"
            )
        return f"WITH {definitions}\n{sql}"
    return sql


def _render_input(input_sql: str, alias: str | None) -> str:
    """Alias an input only when qualified field SQL needs its logical name."""

    if alias is None:
        return input_sql
    return f"{input_sql} AS {quote_identifier(alias, context='relation identifier')}"


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


def _relation_input_sql(
    relation: RelationIR,
    *,
    sources: Mapping[SymbolId, SourceIR],
    relations: Mapping[SymbolId, RelationIR],
) -> tuple[str, str]:
    """Return the input's FROM SQL and the name that references it unaliased."""

    source = sources.get(relation.source.target)
    if source is not None:
        parts = _mysql_table_name(source)
        sql = ".".join(
            quote_identifier(part, context="physical table identifier")
            for part in parts
        )
        return sql, parts[-1]
    upstream = relations.get(relation.source.target)
    if upstream is not None:
        return (
            quote_identifier(upstream.name, context="relation identifier"),
            upstream.name,
        )
    raise MySqlRenderError(
        "MySQL relation input does not resolve to SourceIR or RelationIR"
    )


def _mysql_table_name(source: SourceIR) -> tuple[str, ...]:
    """Return the static `<table>` or `<schema>.<table>` name parts."""

    connector = source.connector
    if (
        connector.name != "mysql.table"
        or len(connector.arguments) != 1
        or not isinstance(connector.arguments[0], str)
        or not connector.arguments[0]
    ):
        raise MySqlRenderError("MySQL relation emission requires mysql.table(Text)")
    parts = tuple(connector.arguments[0].split("."))
    if len(parts) > 2 or not all(parts):
        raise MySqlRenderError("MySQL table name must be <table> or <schema>.<table>")
    return parts


def _render_projection(
    expression: ExpressionIR,
    name: str | None,
    named_decision: NamedWindowLoweringDecision | None,
) -> str:
    if isinstance(expression, WindowCallIR) and name is None:
        raise MySqlRenderError("MySQL window projections require an explicit alias")
    if (
        isinstance(expression, WindowCallIR)
        and getattr(expression, "named_use", None) is not None
    ):
        if named_decision is None:
            raise MySqlRenderError("named window call requires one relation strategy")
        over_sql = (
            _render_named_over(expression)
            if named_decision.strategy
            in {
                NamedWindowLoweringStrategy.NATIVE_PRESERVE,
                NamedWindowLoweringStrategy.NATIVE_REORDER,
            }
            else None
        )
        sql = render_mysql_window_call(expression, over_sql=over_sql)
    else:
        sql = render_mysql_expression(expression)
    if name is None:
        return sql
    alias = quote_identifier(
        name,
        max_characters=MYSQL_ALIAS_MAX_CHARACTERS,
        context="select-list alias",
    )
    return f"{sql} AS {alias}"


def _render_named_over(expression: WindowCallIR) -> str:
    named = expression.named_use
    if named is None:
        raise MySqlRenderError("native named OVER requires named use evidence")
    local = named.local_spec
    frame = local.frame
    effective_frame = expression.spec.frame
    if (
        frame is None
        and effective_frame is not None
        and not effective_frame.frame_is_explicit
    ):
        frame = effective_frame
    components = render_mysql_window_components(
        local.partition_by,
        local.order_by,
        frame,
    )
    reference = quote_identifier(
        named.reference_spelling,
        context="named window identifier",
    )
    if not components:
        return (
            f"({reference})"
            if named.occurrence.kind is WindowUseKindIR.NAMED_EXTENDED
            else reference
        )
    return f"({reference} {' '.join(components)})"


def _render_named_declaration(declaration: NamedWindowDeclarationIR) -> str:
    if type(declaration) is not NamedWindowDeclarationIR:
        raise TypeError("MySQL named declaration must be exact")
    components = render_mysql_window_components(
        declaration.local_spec.partition_by,
        declaration.local_spec.order_by,
        declaration.local_spec.frame,
    )
    parts = (
        ()
        if declaration.base is None
        else (
            quote_identifier(
                declaration.base.spelling,
                context="named window identifier",
            ),
        )
    ) + components
    name = quote_identifier(
        declaration.name,
        context="named window identifier",
    )
    return f"{name} AS ({' '.join(parts)})"


def _validate_grouped_relation(relation: RelationIR) -> None:
    group_fields = _group_key_fields(relation.group_keys)
    orderable_expressions: list[ExpressionIR] = []
    selected_window_aliases: set[str] = set()
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
        if isinstance(expression, WindowCallIR):
            if type(projection.name) is not str or not projection.name:
                raise MySqlRenderError(
                    "MySQL grouped window projections require an explicit alias"
                )
            selected_window_aliases.add(projection.name)
            continue
        raise MySqlRenderError(
            "MySQL grouped projection is neither a GROUP BY key, aggregate, nor "
            "direct window"
        )

    if not saw_aggregate:
        raise MySqlRenderError(
            "MySQL pure grouped output without an aggregate is not supported"
        )

    _validate_grouped_order_by(
        relation.order_by,
        orderable_expressions,
        selected_window_aliases,
    )


def _validate_grouped_order_by(
    order_by: tuple[OrderItemIR, ...],
    orderable_expressions: list[ExpressionIR],
    selected_window_aliases: set[str],
) -> None:
    for item in order_by:
        if any(item.expression == expression for expression in orderable_expressions):
            continue
        expression = item.expression
        if (
            isinstance(expression, FieldRefIR)
            and expression.qualifier == ()
            and expression.field is None
            and expression.name in selected_window_aliases
        ):
            continue
        raise MySqlRenderError(
            "MySQL grouped ORDER BY expression must match a selected GROUP BY key, "
            "aggregate projection, or window alias"
        )


def _validate_window_clause_boundaries(relation: RelationIR) -> None:
    """Reject direct windows outside an explicitly aliased projection."""

    if relation.filter is not None and isinstance(
        relation.filter.expression, WindowCallIR
    ):
        raise MySqlRenderError("MySQL WHERE does not support direct window calls")
    if relation.result_predicate is not None and isinstance(
        relation.result_predicate.expression, WindowCallIR
    ):
        raise MySqlRenderError("MySQL HAVING does not support direct window calls")
    if any(isinstance(key, WindowCallIR) for key in relation.group_keys):
        raise MySqlRenderError("MySQL GROUP BY does not support direct window calls")
    if any(isinstance(item.expression, WindowCallIR) for item in relation.order_by):
        raise MySqlRenderError(
            "MySQL relation ORDER BY does not support direct windows"
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
