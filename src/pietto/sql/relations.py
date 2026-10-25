"""Internal PostgreSQL rendering for minimal relation SELECT statements."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from dataclasses import replace
from typing import Any

from pietto.ir.model import (
    AggregateCallIR,
    ExpressionIR,
    ExistsIR,
    FieldId,
    FieldRefIR,
    LiteralIR,
    OrderDirectionIR,
    OrderItemIR,
    NamedWindowDeclarationIR,
    ProjectionIR,
    RelationIR,
    SourceIR,
    SymbolId,
    TypeKindIR,
    WindowCallIR,
    WindowUseKindIR,
)
from pietto.sql.expressions import (
    expression_uses_qualified_field,
    is_untyped_null,
    refuse_text_null_condition,
    render_expression_sql,
    render_window_call_sql,
    render_window_components_sql,
)
from pietto.sql.joins import render_conjunction_sql, render_join_sql
from pietto.sql.render import quote_identifier, quote_qualified_identifier
from pietto.sql.window_strategy import (
    NamedWindowLoweringDecision,
    NamedWindowLoweringStrategy,
    WindowTargetDialect,
    decide_named_window_lowering,
)


def render_relation_sql(
    relation: RelationIR,
    *,
    sources: Mapping[SymbolId, SourceIR],
    relations: Mapping[SymbolId, RelationIR],
    _include_exists_dependencies: bool = True,
) -> str:
    """Render a minimal relation using a source table or relation-name input."""

    dependencies = (
        _exists_relation_dependencies(relation, relations)
        if _include_exists_dependencies
        else ()
    )
    _validate_exists_targets(relation, sources, relations)
    input_name = _relation_input_name(
        relation.source.target,
        sources=sources,
        relations=relations,
    )
    join_lines, conjuncts = (
        render_join_sql(
            relation,
            [
                _relation_input_name(item.target, sources=sources, relations=relations)
                for item in relation.inputs
            ],
        )
        if relation.joins
        else ((), ())
    )
    if not relation.projections:
        raise ValueError("PostgreSQL relation emission requires projections")
    if any(
        is_untyped_null(projection.expression) for projection in relation.projections
    ) and any(
        other.source.target == relation.symbol
        or any(item.target == relation.symbol for item in other.inputs)
        for other in relations.values()
    ):
        raise ValueError(
            "PostgreSQL types a NULL output that another relation reads as text, "
            "which Pietto leaves untyped"
        )
    if has_untyped_result_predicate(relation):
        raise ValueError("PostgreSQL result predicate requires a known Bool type")
    if relation.result_predicate is not None and not relation.group_keys:
        raise ValueError("PostgreSQL result predicate requires GROUP BY")
    _validate_window_clause_boundaries(relation)
    if relation.group_keys:
        _validate_grouped_relation(relation)

    named_decision = decide_named_window_lowering(
        relation,
        WindowTargetDialect.POSTGRESQL,
    )
    if named_decision is not None and named_decision.strategy is (
        NamedWindowLoweringStrategy.NOT_LOWERABLE
    ):
        raise ValueError(named_decision.reason)
    alias = None
    if not relation.joins:
        # A qualified field already aliases the input with its Pietto name; else
        # a captured key is qualified with the table's own name and FROM is kept.
        alias = (
            relation.source.name if _relation_uses_qualified_fields(relation) else None
        )
        relation = qualify_alias_captured_order_fields(
            relation,
            qualifier=alias or input_name[-1],
            mysql=False,
        )

    projection_sql = ",\n".join(
        f"    {_render_projection(projection.expression, projection.name, named_decision)}"
        for projection in relation.projections
    )
    lines = [
        "SELECT",
        projection_sql,
        *(join_lines or (f"FROM {_render_input(input_name, alias)}",)),
    ]
    if relation.filter is not None:
        refuse_text_null_condition(relation.filter.expression)
        conjuncts = (*conjuncts, render_expression_sql(relation.filter.expression))
    if conjuncts:
        lines.append(f"WHERE {render_conjunction_sql(conjuncts)}")
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
            f"{quote_identifier(item.name)} AS (\n{render_relation_sql(item, sources=sources, relations=relations, _include_exists_dependencies=False)}\n)"
            for item in dependencies
        )
        hidden = hidden_table_read(
            relation, dependencies, sources, relations, mysql=False
        )
        if hidden is not None:
            raise ValueError(
                f"PostgreSQL scalar ANY defines relation {hidden[0]} as a CTE, "
                f"which would hide table {hidden[1]} read in the same SQL; rename "
                "the relation or read the table with its schema"
            )
        return f"WITH {definitions}\n{sql}"
    return sql


def qualify_alias_captured_order_fields(
    relation: RelationIR,
    *,
    qualifier: str,
    mysql: bool,
) -> RelationIR:
    """Qualify each bare ORDER BY input field that a SELECT item could capture.

    PostgreSQL and MySQL bind a whole bare ORDER BY name to a SELECT output
    before an input column (MySQL compares the names case-insensitively).
    Inside an expression PostgreSQL reads the input column; MySQL documents
    the alias-first lookup for every ORDER BY name, so for MySQL each field
    inside a key is qualified too (window calls and `any` reads keep their
    own scopes). An output that is the same input field reads the same
    value, so it captures nothing. PostgreSQL
    also names an unaliased computed item implicitly (`lower`, `coalesce`,
    `case`, ...), so there any unaliased computed item counts as a capture.
    MySQL names it by its expression text; of those names only an unaliased
    literal's can be a field name: a Text literal's value, or `TRUE`, `FALSE`
    or `NULL`, as written.
    """

    def spelling(name: str) -> str:
        return name.casefold() if mysql else name

    def captures(projection: ProjectionIR, key: FieldRefIR) -> bool:
        expression = projection.expression
        if projection.name is None:
            if isinstance(expression, FieldRefIR):
                return False
            if not mysql:
                return True
            if not isinstance(expression, LiteralIR):
                return False
            value = expression.value
            if type(value) is bool:
                name = "TRUE" if value else "FALSE"
            elif value is None:
                name = "NULL"
            elif type(value) is str:
                name = value
            else:
                return False
            return spelling(name) == spelling(key.name)
        return spelling(projection.name) == spelling(key.name) and not (
            isinstance(expression, FieldRefIR) and expression.field == key.field
        )

    def qualified(expression: ExpressionIR) -> ExpressionIR:
        if isinstance(expression, FieldRefIR):
            if (
                not expression.qualifier
                and expression.field is not None
                and any(
                    captures(projection, expression)
                    for projection in relation.projections
                )
            ):
                return replace(expression, qualifier=(qualifier,))
            return expression
        if not mysql or isinstance(expression, (ExistsIR, WindowCallIR)):
            return expression
        changes: dict[str, object] = {}
        for part in fields(expression):
            value = getattr(expression, part.name)
            if isinstance(value, ExpressionIR):
                changes[part.name] = qualified(value)
            elif type(value) is tuple and all(
                isinstance(item, ExpressionIR) for item in value
            ):
                changes[part.name] = tuple(qualified(item) for item in value)
        return replace(expression, **changes)

    order_by = tuple(
        replace(item, expression=qualified(item.expression))
        for item in relation.order_by
    )
    if order_by == relation.order_by:
        return relation
    return replace(relation, order_by=order_by)


def _render_input(input_name: tuple[str, ...], alias: str | None) -> str:
    """Alias an input only when qualified field SQL needs its logical name."""

    sql = quote_qualified_identifier(input_name)
    if alias is None:
        return sql
    return f"{sql} AS {quote_identifier(alias)}"


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


def _ir_children(value: Any) -> tuple[object, ...]:
    children: list[object] = []
    for field in fields(value):
        try:
            children.append(getattr(value, field.name))
        except AttributeError:
            raise ValueError(
                f"Incomplete IR node {type(value).__name__}: missing {field.name}"
            ) from None
    return tuple(children)


def _exists_reads(value: object) -> tuple[ExistsIR, ...]:
    """Return every scalar ANY read in an IR value, in source order."""

    reads: list[ExistsIR] = []
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, ExistsIR):
            reads.append(item)
        if isinstance(item, tuple):
            pending.extend(reversed(item))
        elif is_dataclass(item) and not isinstance(item, type):
            pending.extend(reversed(_ir_children(item)))
    return tuple(reads)


def _exists_relation_dependencies(
    relation: RelationIR, relations: Mapping[SymbolId, RelationIR]
) -> tuple[RelationIR, ...]:
    """Order named iterators and all of their dependencies before this reader."""

    def scalar_targets(value: object) -> tuple[SymbolId, ...]:
        return tuple(item.target for item in _exists_reads(value))

    done: set[SymbolId] = set()
    active: set[SymbolId] = {relation.symbol}
    result: list[RelationIR] = []

    def visit(symbol: SymbolId) -> None:
        dependency = relations.get(symbol)
        if dependency is None or symbol in done:
            return
        if symbol in active:
            raise ValueError("Scalar ANY relation dependency contains a cycle")
        active.add(symbol)
        for child in (
            dependency.source.target,
            *(item.target for item in dependency.inputs),
            *scalar_targets(dependency),
        ):
            visit(child)
        active.remove(symbol)
        done.add(symbol)
        result.append(dependency)

    for target in scalar_targets(relation):
        visit(target)
    return tuple(result)


def hidden_table_read(
    relation: RelationIR,
    dependencies: tuple[RelationIR, ...],
    sources: Mapping[SymbolId, SourceIR],
    relations: Mapping[SymbolId, RelationIR],
    *,
    mysql: bool,
) -> tuple[str, str] | None:
    """Return the first CTE name and table read that the CTE would hide.

    The statement defines `dependencies` as CTEs, in order, before the main
    SELECT of `relation`. A CTE without RECURSIVE is visible in the CTEs after
    it and in the main SELECT, where it takes the place of any table named
    without a schema (MySQL compares the names case-insensitively).
    """

    def spelling(name: str) -> str:
        return name.casefold() if mysql else name

    ctes = {item.symbol for item in dependencies}
    for index, reader in enumerate((*dependencies, relation)):
        visible = {spelling(item.name): item.name for item in dependencies[:index]}
        inputs = (reader.source.target, *(item.target for item in reader.inputs))
        reads = (
            *((target, None) for target in inputs),
            *((item.target, item.connector) for item in _exists_reads(reader)),
        )
        for target, connector in reads:
            if target in ctes:
                continue
            source = sources.get(target)
            if connector is None and source is not None:
                connector = source.connector
            name = (
                relations[target].name
                if connector is None
                else str(connector.arguments[0])
            )
            if "." not in name and spelling(name) in visible:
                return visible[spelling(name)], name
    return None


def _validate_exists_targets(
    relation: RelationIR,
    sources: Mapping[SymbolId, SourceIR],
    relations: Mapping[SymbolId, RelationIR],
) -> None:
    pending: list[object] = [relation]
    while pending:
        value = pending.pop()
        if isinstance(value, ExistsIR):
            source = sources.get(value.target)
            target = relations.get(value.target)
            if source is not None:
                if target is not None or value.connector != source.connector:
                    raise ValueError("Scalar ANY requires the exact source connector.")
            elif target is None or value.connector is not None:
                raise ValueError("Scalar ANY target does not resolve to a relation.")
        if isinstance(value, tuple):
            pending.extend(value)
        elif is_dataclass(value) and not isinstance(value, type):
            pending.extend(_ir_children(value))


def _relation_input_name(
    target: SymbolId,
    *,
    sources: Mapping[SymbolId, SourceIR],
    relations: Mapping[SymbolId, RelationIR],
) -> tuple[str, ...]:
    """Resolve an input to static table metadata or a relation artifact name."""

    source = sources.get(target)
    if source is not None:
        return _postgres_table_name(source)
    upstream = relations.get(target)
    if upstream is not None:
        return (upstream.name,)
    raise ValueError(
        "PostgreSQL relation input does not resolve to SourceIR or RelationIR"
    )


def _postgres_table_name(source: SourceIR) -> tuple[str, ...]:
    """Return the static `<table>` or `<schema>.<table>` name parts."""

    connector = source.connector
    if (
        connector.name != "postgres.table"
        or len(connector.arguments) != 1
        or not isinstance(connector.arguments[0], str)
        or not connector.arguments[0]
    ):
        raise ValueError("PostgreSQL relation emission requires postgres.table(Text)")
    parts = tuple(connector.arguments[0].split("."))
    if len(parts) > 2 or not all(parts):
        raise ValueError("PostgreSQL table name must be <table> or <schema>.<table>")
    return parts


def _render_projection(
    expression: ExpressionIR,
    name: str | None,
    named_decision: NamedWindowLoweringDecision | None,
) -> str:
    """Render one expression with a stable explicit output alias when present."""

    if isinstance(expression, WindowCallIR) and name is None:
        raise ValueError("PostgreSQL window projections require an explicit alias")
    if (
        isinstance(expression, WindowCallIR)
        and getattr(expression, "named_use", None) is not None
    ):
        if named_decision is None:
            raise ValueError("named window call requires one relation strategy")
        over_sql = (
            _render_named_over(expression)
            if named_decision.strategy
            in {
                NamedWindowLoweringStrategy.NATIVE_PRESERVE,
                NamedWindowLoweringStrategy.NATIVE_REORDER,
            }
            else None
        )
        sql = render_window_call_sql(expression, over_sql=over_sql)
    else:
        sql = render_expression_sql(expression)
    if name is None:
        return sql
    return f"{sql} AS {quote_identifier(name)}"


def _render_named_over(expression: WindowCallIR) -> str:
    named = expression.named_use
    if named is None:
        raise ValueError("native named OVER requires named use evidence")
    local = named.local_spec
    frame = local.frame
    effective_frame = expression.spec.frame
    if (
        frame is None
        and effective_frame is not None
        and not effective_frame.frame_is_explicit
    ):
        frame = effective_frame
    components = render_window_components_sql(
        local.partition_by,
        local.order_by,
        frame,
    )
    reference = quote_identifier(named.reference_spelling)
    if not components:
        return (
            f"({reference})"
            if named.occurrence.kind is WindowUseKindIR.NAMED_EXTENDED
            else reference
        )
    return f"({reference} {' '.join(components)})"


def _render_named_declaration(declaration: NamedWindowDeclarationIR) -> str:
    if type(declaration) is not NamedWindowDeclarationIR:
        raise TypeError("PostgreSQL named declaration must be exact")
    components = render_window_components_sql(
        declaration.local_spec.partition_by,
        declaration.local_spec.order_by,
        declaration.local_spec.frame,
    )
    parts = (
        ()
        if declaration.base is None
        else (quote_identifier(declaration.base.spelling),)
    ) + components
    return f"{quote_identifier(declaration.name)} AS ({' '.join(parts)})"


def _validate_grouped_relation(relation: RelationIR) -> None:
    """Fail closed for grouped IR shapes not authorized by the semantic slice."""

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
                raise ValueError(
                    "PostgreSQL grouped window projections require an explicit alias"
                )
            selected_window_aliases.add(projection.name)
            continue
        raise ValueError(
            "PostgreSQL grouped projection is neither a GROUP BY key, aggregate, "
            "nor direct window"
        )

    if not saw_aggregate:
        raise ValueError(
            "PostgreSQL pure grouped output without an aggregate is not supported"
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
    """Allow grouped ordering by selected underlying outputs or window aliases."""

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
        raise ValueError(
            "PostgreSQL grouped ORDER BY expression must match a selected GROUP BY "
            "key, aggregate projection, or window alias"
        )


def has_untyped_result_predicate(relation: RelationIR) -> bool:
    """Whether a result predicate was checked without a known Bool type.

    Semantic analysis keeps a predicate of unknown type (gradual typing); no
    target is asked to read it as a Bool.
    """

    if relation.result_predicate is None:
        return False
    value_type = relation.result_predicate.expression.value_type
    return not (
        value_type.canonical_kind is TypeKindIR.BUILTIN
        and value_type.canonical_name == "Bool"
    )


def _validate_window_clause_boundaries(relation: RelationIR) -> None:
    """Reject direct windows outside an explicitly aliased projection."""

    if relation.filter is not None and isinstance(
        relation.filter.expression, WindowCallIR
    ):
        raise ValueError("PostgreSQL WHERE does not support direct window calls")
    if relation.result_predicate is not None and isinstance(
        relation.result_predicate.expression, WindowCallIR
    ):
        raise ValueError("PostgreSQL HAVING does not support direct window calls")
    if any(isinstance(key, WindowCallIR) for key in relation.group_keys):
        raise ValueError("PostgreSQL GROUP BY does not support direct window calls")
    if any(isinstance(item.expression, WindowCallIR) for item in relation.order_by):
        raise ValueError(
            "PostgreSQL relation ORDER BY does not support direct window calls"
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
