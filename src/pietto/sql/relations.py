"""Internal PostgreSQL rendering for minimal relation SELECT statements."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import fields, is_dataclass, replace
from itertools import chain, count
from typing import Any

from pietto._generated_names import generated_name
from pietto.ir.model import (
    AggregateCallIR,
    AggregateWindowCallIR,
    AnyFieldIR,
    ExpressionIR,
    ExistsIR,
    FieldId,
    FieldRefIR,
    OrderDirectionIR,
    OrderItemIR,
    NamedWindowDeclarationIR,
    ProjectionIR,
    QualifyIR,
    RelationIR,
    SourceIR,
    SymbolId,
    TypeKindIR,
    WindowCallIR,
    WindowOrderItemIR,
    WindowUseKindIR,
)
from pietto.sql.expressions import (
    expression_uses_qualified_field,
    is_untyped_null,
    refuse_text_null_condition,
    render_expression_sql,
    render_aggregate_window_call_sql,
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
    _include_dependencies: bool = True,
) -> str:
    """Render a minimal relation, defining the relations it reads as CTEs."""

    # From the whole relation: a QUALIFY outer stage keeps its `any` reads.
    dependencies = (
        _relation_dependencies(relation, relations) if _include_dependencies else ()
    )
    _validate_exists_targets(relation, sources, relations)
    if relation.qualify is not None:
        return _with_dependencies(
            _render_qualify_relation_sql(
                relation,
                sources=sources,
                relations=relations,
            ),
            relation,
            dependencies,
            sources=sources,
            relations=relations,
        )
    input_name = _relation_input_name(
        relation.source.target,
        sources=sources,
        relations=relations,
    )
    join_lines, conjuncts = (
        render_join_sql(
            relation,
            # Every input name resolves before any is quoted.
            [
                _render_input(name, item.binding)
                for item, name in zip(
                    relation.inputs,
                    [
                        _relation_input_name(
                            item.target, sources=sources, relations=relations
                        )
                        for item in relation.inputs
                    ],
                    strict=True,
                )
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
    positions = order_output_positions(relation, mysql=False)

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
                    f"    {_render_named_declaration(declaration, named_decision.emission_declarations)}"
                    for declaration in named_decision.emission_declarations
                ),
            )
        )
    if relation.order_by:
        lines.extend(
            (
                "ORDER BY",
                ",\n".join(
                    f"    {_render_order_item(item, positions.get(index))}"
                    for index, item in enumerate(relation.order_by)
                ),
            )
        )
    if relation.limit is not None:
        lines.append(f"LIMIT {_render_limit(relation.limit.value)}")
    return _with_dependencies(
        "\n".join(lines),
        relation,
        dependencies,
        sources=sources,
        relations=relations,
    )


def _with_dependencies(
    sql: str,
    relation: RelationIR,
    dependencies: tuple[RelationIR, ...],
    *,
    sources: Mapping[SymbolId, SourceIR],
    relations: Mapping[SymbolId, RelationIR],
) -> str:
    """Define each relation the statement reads as a CTE before its SQL."""

    if not dependencies:
        return sql
    definitions: list[str] = []
    for item, cte in zip(dependencies, alias_cte_outputs(dependencies, relation)):
        if cte is not item:
            # A relation that refuses an output without an alias refuses here.
            render_relation_sql(
                item, sources=sources, relations=relations, _include_dependencies=False
            )
        sql_text = render_relation_sql(
            cte, sources=sources, relations=relations, _include_dependencies=False
        )
        definitions.append(f"{quote_identifier(item.name)} AS (\n{sql_text}\n)")
    hidden = hidden_table_read(relation, dependencies, sources, relations, mysql=False)
    if hidden is not None:
        raise ValueError(
            f"Its SQL defines relation {hidden[0]} as a CTE, which would "
            f"hide table {hidden[1]} read in the same SQL; rename the "
            "relation or read the table with its schema"
        )
    unnamed = unnamed_output_read(relation, dependencies, mysql=False)
    if unnamed is not None:
        raise ValueError(unnamed)
    return "WITH " + ",\n".join(definitions) + f"\n{sql}"


def alias_cte_outputs(
    dependencies: tuple[RelationIR, ...], relation: RelationIR
) -> tuple[RelationIR, ...]:
    """The statement's CTEs, each output without an alias given a private one.

    PostgreSQL and MySQL each name an output without an alias by rules of
    their own, and a read of a CTE column by its name, or a bare ORDER BY name
    inside the CTE, could bind to that name. A private alias takes no name the
    statement selects or reads, in any case. The main SELECT keeps its
    unaliased outputs, whose names are the result's.
    """

    if all(item.name is not None for d in dependencies for item in d.projections):
        return dependencies
    names = _statement_names((*dependencies, relation))
    aliased: list[RelationIR] = []
    for dependency in dependencies:
        if all(item.name is not None for item in dependency.projections):
            aliased.append(dependency)
            continue
        used = set(names)
        projections = tuple(
            item
            if item.name is not None
            else replace(
                item,
                name=generated_name((f"__pietto_column_{n}" for n in count(1)), used),
            )
            for item in dependency.projections
        )
        aliased.append(replace(dependency, projections=projections))
    return tuple(aliased)


def _statement_names(relations: tuple[RelationIR, ...]) -> set[str]:
    """Each column name the relations select or read, case-folded."""

    found: set[str] = set()
    pending: list[object] = list(relations)
    while pending:
        value = pending.pop()
        if isinstance(value, (ProjectionIR, FieldRefIR, AnyFieldIR)) and value.name:
            found.add(value.name.casefold())
        if isinstance(value, tuple):
            pending.extend(value)
        elif is_dataclass(value) and not isinstance(value, type):
            pending.extend(getattr(value, item.name) for item in fields(value))
    return found


def _render_qualify_relation_sql(
    relation: RelationIR,
    *,
    sources: Mapping[SymbolId, SourceIR],
    relations: Mapping[SymbolId, RelationIR],
) -> str:
    """Render QUALIFY as an exact derived-table post-window predicate."""

    qualify = relation.qualify
    if type(qualify) is not QualifyIR:
        raise ValueError("PostgreSQL QUALIFY requires an exact predicate")
    names = tuple(
        projection.name
        for projection in relation.projections
        if type(projection.name) is str
    )
    if len(names) != len(relation.projections) or any(not name for name in names):
        raise ValueError("PostgreSQL QUALIFY requires named selected outputs")
    derived, hidden, predicate, order_by = _qualify_outer_stage(relation)
    # The outer stage reads the inner one as a derived table, whose NULL
    # outputs PostgreSQL types as text, as it does a CTE's.
    untyped = {
        projection.name
        for projection in relation.projections
        if is_untyped_null(projection.expression)
    }
    pending: list[object] = [predicate]
    while pending:
        item = pending.pop()
        if type(item) is FieldRefIR and item.field is None and item.name in untyped:
            raise ValueError(
                "PostgreSQL types a NULL output that its QUALIFY stage reads as "
                "text, which Pietto leaves untyped"
            )
        if isinstance(item, ExpressionIR):
            pending.extend(getattr(item, part.name) for part in fields(item))
        elif type(item) is tuple:
            pending.extend(item)
    refuse_text_null_condition(predicate)
    inner = replace(
        relation,
        qualify=None,
        projections=(*relation.projections, *hidden),
        order_by=(),
        limit=None,
    )
    # The statement defines the relations both stages read, once, at its top.
    inner_sql = render_relation_sql(
        inner, sources=sources, relations=relations, _include_dependencies=False
    )
    selected = ",\n".join(f"    {quote_identifier(name)}" for name in names)
    lines = [
        "SELECT",
        selected,
        "FROM (",
        inner_sql,
        f") AS {quote_identifier(derived)}",
        "WHERE",
        f"    {render_expression_sql(predicate)}",
    ]
    if order_by:
        lines.extend(
            (
                "ORDER BY",
                ",\n".join(f"    {_render_order_item(item)}" for item in order_by),
            )
        )
    if relation.limit is not None:
        lines.append(f"LIMIT {_render_limit(relation.limit.value)}")
    return "\n".join(lines)


def _qualify_outer_stage(
    relation: RelationIR,
) -> tuple[str, tuple[ProjectionIR, ...], ExpressionIR, tuple[OrderItemIR, ...]]:
    """Name the derived table and carry every outer QUALIFY/ORDER input as a
    private port of it."""

    qualify = relation.qualify
    if type(qualify) is not QualifyIR:
        raise ValueError("QUALIFY stage requires an exact predicate")
    # A port avoids each output name and the derived table each input alias.
    used = {
        projection.name.casefold()
        for projection in relation.projections
        if projection.name
    }
    derived = generated_name(
        chain(("__pietto_qualify",), (f"__pietto_qualify{n}" for n in count(2))),
        {
            name.casefold()
            for name in (
                relation.source.name,
                *(item.binding for item in relation.inputs),
            )
        },
    )
    hidden: list[ProjectionIR] = []
    windows: dict[int, FieldRefIR] = {}
    inputs: dict[FieldId, FieldRefIR] = {}

    def port(expression: ExpressionIR) -> FieldRefIR:
        alias = generated_name((f"__pietto_qualify_{n}" for n in count()), used)
        value = FieldRefIR(
            name=alias,
            qualifier=(),
            field=None,
            span=expression.span,
            value_type=expression.value_type,
        )
        hidden.append(
            ProjectionIR(
                name=alias,
                expression=expression,
                type_ref=None,
                span=expression.span,
            )
        )
        return value

    def outer(expression: ExpressionIR, nested: bool = False) -> ExpressionIR:
        if isinstance(expression, (WindowCallIR, AggregateWindowCallIR)):
            saved = windows.get(id(expression))
            if saved is None:
                saved = windows[id(expression)] = port(expression)
            return saved
        if isinstance(expression, AggregateCallIR):
            saved = windows.get(id(expression))
            if saved is None:
                saved = windows[id(expression)] = port(expression)
            return saved
        if isinstance(expression, FieldRefIR) and expression.field is not None:
            saved = inputs.get(expression.field)
            if saved is None:
                saved = inputs[expression.field] = port(expression)
            # Inside EXISTS a bare port would first bind to a same-named
            # column of the subquery's own FROM, so it names the derived table.
            return replace(saved, qualifier=(derived,)) if nested else saved
        nested = nested or isinstance(expression, ExistsIR)
        changes: dict[str, object] = {}
        for field in fields(expression):
            value = getattr(expression, field.name)
            if isinstance(value, ExpressionIR):
                changes[field.name] = outer(value, nested)
            elif type(value) is tuple and any(
                isinstance(item, ExpressionIR) for item in value
            ):
                changes[field.name] = tuple(
                    outer(item, nested) if isinstance(item, ExpressionIR) else item
                    for item in value
                )
        return replace(expression, **changes) if changes else expression

    # Hidden named windows retain source-selected ordinals, so they must occupy
    # the slots immediately after visible projections, before carried inputs.
    for expression in _qualify_windows(qualify.expression):
        outer(expression)
    predicate = outer(qualify.expression)
    order_by = tuple(
        replace(item, expression=outer(item.expression)) for item in relation.order_by
    )
    return derived, tuple(hidden), predicate, order_by


def _qualify_windows(
    expression: ExpressionIR,
) -> tuple[WindowCallIR | AggregateWindowCallIR, ...]:
    found: list[WindowCallIR | AggregateWindowCallIR] = []
    pending = [expression]
    while pending:
        item = pending.pop()
        if isinstance(item, (WindowCallIR, AggregateWindowCallIR)):
            found.append(item)
            continue
        if isinstance(item, ExpressionIR):
            for field in reversed(fields(item)):
                value = getattr(item, field.name)
                if isinstance(value, ExpressionIR):
                    pending.append(value)
                elif type(value) is tuple:
                    pending.extend(reversed(value))
    return tuple(found)


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
    own scopes). An output of the field's name captures it unless it is the
    same input field. PostgreSQL and MySQL each name an item without an
    alias by rules of their own, so beside one every such field is qualified.
    """

    def spelling(name: str) -> str:
        return name.casefold() if mysql else name

    unaliased = any(projection.name is None for projection in relation.projections)

    def captures(projection: ProjectionIR, key: FieldRefIR) -> bool:
        expression = projection.expression
        return (
            projection.name is not None
            and spelling(projection.name) == spelling(key.name)
            and not (
                isinstance(expression, FieldRefIR)
                and (
                    expression.field == key.field
                    # A field of a row of unknown type is selected by name alone.
                    or (expression.field is None and expression.name == key.name)
                )
            )
        )

    def qualified(expression: ExpressionIR) -> ExpressionIR:
        if isinstance(expression, FieldRefIR):
            if (
                not expression.qualifier
                and expression.field is not None
                and (
                    unaliased
                    or any(
                        captures(projection, expression)
                        for projection in relation.projections
                    )
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


def order_output_positions(relation: RelationIR, *, mysql: bool) -> dict[int, int]:
    """The SELECT list position each ORDER BY key that reads an output by its
    name sorts by, keyed by the key's index, where the name could bind to
    another item: beside an item without an alias, which PostgreSQL and MySQL
    each name by rules of their own, or, on MySQL, which compares names
    without case, beside another output whose name differs only in case."""

    names = [projection.name for projection in relation.projections]
    positions: dict[int, int] = {}
    for index, item in enumerate(relation.order_by):
        key = item.expression
        if (
            not isinstance(key, FieldRefIR)
            or key.field is not None
            or key.qualifier
            or key.name not in names
        ):
            continue
        if None in names or (
            mysql
            and any(
                name != key.name and name.casefold() == key.name.casefold()
                for name in names
                if name is not None
            )
        ):
            positions[index] = names.index(key.name) + 1
    return positions


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


def _read_targets(relation: RelationIR) -> tuple[SymbolId, ...]:
    """What one relation reads, in order: FROM, each JOIN input, each ANY."""

    return (
        relation.source.target,
        *(item.target for item in relation.inputs),
        *(item.target for item in _exists_reads(relation)),
    )


def _relation_dependencies(
    relation: RelationIR, relations: Mapping[SymbolId, RelationIR]
) -> tuple[RelationIR, ...]:
    """Order the tables and queries of the file that a reader's SQL defines.

    Each table or query that the reader reads (by FROM, a JOIN or ANY), and
    each one those read, becomes a CTE named after it, after the ones it reads.
    """

    done: set[SymbolId] = set()
    active: set[SymbolId] = {relation.symbol}
    result: list[RelationIR] = []
    # A depth-first walk on an explicit stack, so a long chain of reads never
    # exhausts the interpreter's recursion limit.
    stack: list[tuple[RelationIR | None, Iterator[SymbolId]]] = [
        (None, iter(_read_targets(relation)))
    ]
    while stack:
        dependency, children = stack[-1]
        for symbol in children:
            child = relations.get(symbol)
            if child is None or symbol in done:
                continue
            if symbol in active:
                raise ValueError("Relation dependency contains a cycle")
            active.add(symbol)
            stack.append((child, iter(_read_targets(child))))
            break
        else:
            stack.pop()
            if dependency is not None:
                active.remove(dependency.symbol)
                done.add(dependency.symbol)
                result.append(dependency)
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


def unnamed_output_read(
    relation: RelationIR,
    dependencies: tuple[RelationIR, ...],
    *,
    mysql: bool,
) -> str | None:
    """Return why the statement reads a CTE column that its relation does not
    name, at the first such read in source order, or None.

    A check reads any name from a relation over a row of unknown type, such as
    a source without a shape, yet its CTE has exactly the outputs it names,
    each unaliased one under a private alias (`alias_cte_outputs`), so a read
    of another name, such as `lower` for an unaliased `lower(email)`, names
    no column of the CTE. ORDER BY, HAVING and QUALIFY may also read the
    reader's own outputs, each as a field of no input; any other name they
    read, an output's in another case or inside an expression included, is an
    input field. MySQL compares column names without case.
    """

    def spelling(name: str) -> str:
        return name.casefold() if mysql else name

    ctes = {item.symbol: item for item in dependencies if item.row_schema.is_unknown}
    if not ctes:
        return None
    for reader in (*dependencies, relation):
        inputs = (
            {item.binding: item.target for item in reader.inputs}
            if reader.inputs
            else {"": reader.source.target, reader.source.name: reader.source.target}
        )
        found: list[tuple[FieldRefIR | AnyFieldIR, RelationIR]] = []
        for part in fields(reader):
            own = part.name in {"order_by", "result_predicate", "qualify"}
            pending: list[object] = [getattr(reader, part.name)]
            while pending:
                item = pending.pop()
                if isinstance(item, tuple):
                    pending.extend(item)
                    continue
                if not is_dataclass(item) or isinstance(item, type):
                    continue
                pending.extend(_ir_children(item))
                if type(item) is AnyFieldIR:
                    cte = ctes.get(item.relation)
                elif (
                    type(item) is FieldRefIR
                    and len(item.qualifier) <= 1
                    and not (own and item.field is None)
                ):
                    target = inputs.get("".join(item.qualifier))
                    cte = None if target is None else ctes.get(target)
                else:
                    continue
                if cte is not None and spelling(item.name) not in {
                    spelling(output.name) for output in cte.projections if output.name
                }:
                    found.append((item, cte))
        if not found:
            continue
        read, cte = min(
            found, key=lambda pair: (pair[0].span.line, pair[0].span.column)
        )
        reason = (
            f"Its SQL reads {read.name} from relation {cte.name}, which names "
            f"no output {read.name}"
        )
        unnamed = [item.span for item in cte.projections if item.name is None]
        # A read that differs from an output only in case means that output.
        if not unnamed or read.name.casefold() in {
            output.name.casefold() for output in cte.projections if output.name
        }:
            return reason
        where = " and ".join(
            f"line {span.line}, column {span.column}" for span in unnamed
        )
        many = len(unnamed) > 1
        return (
            f"{reason}; if it means {'one of ' if many else ''}the unaliased "
            f"output{'s' if many else ''} at {where}, which "
            f"{'have' if many else 'has'} no name a reader can use, write "
            f"`{read.name} = ...` there to name it"
        )
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

    if isinstance(expression, (WindowCallIR, AggregateWindowCallIR)) and name is None:
        raise ValueError("PostgreSQL window projections require an explicit alias")
    if (
        isinstance(expression, (WindowCallIR, AggregateWindowCallIR))
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
        if type(expression) is WindowCallIR:
            sql = render_window_call_sql(expression, over_sql=over_sql)
        else:
            assert type(expression) is AggregateWindowCallIR
            sql = render_aggregate_window_call_sql(expression, over_sql=over_sql)
    else:
        sql = render_expression_sql(expression)
    if name is None:
        return sql
    return f"{sql} AS {quote_identifier(name)}"


def _render_named_over(expression: WindowCallIR | AggregateWindowCallIR) -> str:
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
        effective_order_by=expression.spec.order_by,
    )
    reference = quote_identifier(named.reference_spelling)
    if not components:
        return (
            f"({reference})"
            if named.occurrence.kind is WindowUseKindIR.NAMED_EXTENDED
            else reference
        )
    return f"({reference} {' '.join(components)})"


def _render_named_declaration(
    declaration: NamedWindowDeclarationIR,
    declarations: tuple[NamedWindowDeclarationIR, ...],
) -> str:
    if type(declaration) is not NamedWindowDeclarationIR:
        raise TypeError("PostgreSQL named declaration must be exact")
    components = render_window_components_sql(
        declaration.local_spec.partition_by,
        declaration.local_spec.order_by,
        declaration.local_spec.frame,
        effective_order_by=_named_declaration_order_by(declaration, declarations),
    )
    parts = (
        ()
        if declaration.base is None
        else (quote_identifier(declaration.base.spelling),)
    ) + components
    return f"{quote_identifier(declaration.name)} AS ({' '.join(parts)})"


def _named_declaration_order_by(
    declaration: NamedWindowDeclarationIR,
    declarations: tuple[NamedWindowDeclarationIR, ...],
) -> tuple[WindowOrderItemIR, ...]:
    by_occurrence = {item.occurrence: item for item in declarations}
    current = declaration
    seen = set()
    while not current.local_spec.order_by:
        if current.occurrence in seen:
            raise ValueError("named window declaration graph contains a cycle")
        seen.add(current.occurrence)
        if current.base is None:
            return ()
        current = by_occurrence.get(current.base.target)
        if current is None:
            raise ValueError("named window declaration base is absent")
    return current.local_spec.order_by


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
        if isinstance(expression, (WindowCallIR, AggregateWindowCallIR)):
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
        relation.filter.expression, (WindowCallIR, AggregateWindowCallIR)
    ):
        raise ValueError("PostgreSQL WHERE does not support direct window calls")
    if relation.result_predicate is not None and isinstance(
        relation.result_predicate.expression, (WindowCallIR, AggregateWindowCallIR)
    ):
        raise ValueError("PostgreSQL HAVING does not support direct window calls")
    if any(
        isinstance(key, (WindowCallIR, AggregateWindowCallIR))
        for key in relation.group_keys
    ):
        raise ValueError("PostgreSQL GROUP BY does not support direct window calls")
    if any(
        isinstance(item.expression, (WindowCallIR, AggregateWindowCallIR))
        for item in relation.order_by
    ):
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


def _render_order_item(item: OrderItemIR, position: int | None = None) -> str:
    """Render one validated sorting item, by its SELECT list position when
    given, without dropping its direction."""

    if not isinstance(item.direction, OrderDirectionIR):
        raise ValueError("PostgreSQL relation order direction is invalid")
    key = render_expression_sql(item.expression) if position is None else position
    return f"{key} {item.direction.value}"
