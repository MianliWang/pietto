"""Internal MySQL rendering for minimal relation SELECT statements."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields as dataclass_fields
from dataclasses import is_dataclass, replace
from itertools import chain, count
from typing import Any

from pietto._generated_names import generated_name
from pietto.ir.model import (
    AggregateCallIR,
    AggregateWindowCallIR,
    AnyFieldIR,
    ExpressionIR,
    FieldId,
    FieldRefIR,
    JoinIR,
    JoinKindIR,
    OrderDirectionIR,
    OrderItemIR,
    QualifyIR,
    NamedWindowDeclarationIR,
    RelationInputIR,
    RelationInputRoleIR,
    RelationIR,
    RelationSourceIR,
    SourceIR,
    SymbolId,
    SymbolNamespace,
    TypeKindIR,
    WindowCallIR,
    WindowUseKindIR,
)
from pietto.sql.expressions import expression_uses_qualified_field
from pietto.sql.joins import (
    MYSQL,
    full_join_key,
    render_conjunction_sql,
    render_join_sql,
)
from pietto.sql.mysql_expressions import (
    has_inexact_float_arithmetic,
    is_mysql_double,
    mysql_float_fields,
    mysql_rounded_float_fields,
    render_mysql_aggregate_window_call,
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
    _exists_reads,
    _qualify_outer_stage,
    alias_cte_outputs,
    has_untyped_result_predicate,
    hidden_table_read,
    _relation_dependencies,
    _validate_exists_targets,
    order_output_positions,
    qualify_alias_captured_order_fields,
    unnamed_output_read,
)
from pietto.sql.window_strategy import (
    NamedWindowLoweringDecision,
    NamedWindowLoweringStrategy,
    WindowTargetDialect,
    decide_named_window_lowering,
)

# MySQL's largest LIMIT, which keeps every row.
_EVERY_ROW = "\nLIMIT 18446744073709551615"
# Each emulated FULL JOIN repeats the inputs before it in both UNION ALL
# branches, so the SQL doubles with each one.
_MAX_FULL_JOINS = 8


class MySqlEmission:
    """What one MySQL emission decides once, for each statement it renders."""

    def __init__(self) -> None:
        # Each relation output decided so far, or being decided, and whether
        # both targets hold it as a DOUBLE.
        self.proved: dict[tuple[SymbolId, str], bool | None] = {}
        # Each relation rendered as a CTE, by id, with its SQL or refusal and
        # whether it refused; holding the relation keeps its id unique.
        self.ctes: dict[int, tuple[RelationIR, str, bool]] = {}


def render_mysql_relation(
    relation: RelationIR,
    *,
    sources: Mapping[SymbolId, SourceIR],
    relations: Mapping[SymbolId, RelationIR],
    emission: MySqlEmission | None = None,
    _include_dependencies: bool = True,
    _derived: str | None = None,
) -> str:
    """Render a minimal relation, defining the relations it reads as CTEs.

    `emission` holds what the statements of one emission share; without it
    the statement decides everything afresh. `_derived` is the SQL of the
    derived table that a FULL JOIN emulation reads in place of the relation's
    first input.
    """

    emission = MySqlEmission() if emission is None else emission
    # From the whole relation: a QUALIFY outer stage keeps its `any` reads.
    try:
        dependencies = (
            _relation_dependencies(relation, relations) if _include_dependencies else ()
        )
        _validate_exists_targets(relation, sources, relations)
    except ValueError as error:
        raise MySqlRenderError(str(error)) from error
    # A FULL JOIN outer stage reads its derived table's ports in place of the
    # fields that this check already passed in the relation it rewrites.
    for field in mysql_rounded_float_fields(relation) if _derived is None else ():
        if not _is_double_column(
            field,
            relation,
            sources=sources,
            relations=relations,
            proved=emission.proved,
        ):
            raise MySqlRenderError(
                f"MySQL function round(Float) reads Float field {field.name}, "
                "which is not proved a DOUBLE on both targets"
            )
    if relation.qualify is not None:
        return _with_dependencies(
            _render_mysql_qualify_relation(
                relation,
                sources=sources,
                relations=relations,
                derived=_derived,
                emission=emission,
            ),
            relation,
            dependencies,
            sources=sources,
            relations=relations,
            emission=emission,
        )
    if relation.joins and _derived is None:
        _refuse_join_aliases(relation)
    full = next((join for join in relation.joins if join.kind is JoinKindIR.FULL), None)
    if full is not None and _derived is None:
        # PostgreSQL's checks of each FULL JOIN, in JOIN order, come before the
        # refusals of the emulation.
        render_join_sql(
            relation,
            _join_inputs(relation, sources=sources, relations=relations, derived=None),
            MYSQL,
            full_as=JoinKindIR.LEFT,
        )
        if (
            sum(join.kind is JoinKindIR.FULL for join in relation.joins)
            > _MAX_FULL_JOINS
        ):
            raise MySqlRenderError(
                f"MySQL emulates at most {_MAX_FULL_JOINS} FULL JOINs in one "
                "relation, as each repeats the inputs before it"
            )
    if full is not None:
        return _with_dependencies(
            _render_mysql_full_relation(
                relation,
                full,
                sources=sources,
                relations=relations,
                derived=_derived,
            ),
            relation,
            dependencies,
            sources=sources,
            relations=relations,
            emission=emission,
        )
    quote_identifier(relation.name, context="relation identifier")
    input_sql, input_reference = (
        _relation_input_sql(
            relation.source.target, sources=sources, relations=relations
        )
        if _derived is None
        else (f"(\n{_derived}\n)", relation.source.name)
    )
    join_lines, conjuncts = (
        render_join_sql(
            relation,
            _join_inputs(
                relation, sources=sources, relations=relations, derived=_derived
            ),
            MYSQL,
        )
        if relation.joins
        else ((), ())
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
    alias = None
    if not relation.joins:
        # A qualified field already aliases the input with its Pietto name; else
        # a captured key is qualified with the table's own name and FROM is
        # kept. A derived table always takes its alias.
        alias = (
            relation.source.name
            if _derived is not None or _relation_uses_qualified_fields(relation)
            else None
        )
        relation = qualify_alias_captured_order_fields(
            relation,
            qualifier=alias or input_reference,
            mysql=True,
        )
    positions = order_output_positions(relation, mysql=True)

    projection_sql = ",\n".join(
        f"    {_render_projection(projection.expression, projection.name, named_decision)}"
        for projection in relation.projections
    )
    lines = [
        "SELECT",
        projection_sql,
        *(join_lines or (f"FROM {_render_input(input_sql, alias)}",)),
    ]
    if relation.filter is not None:
        conjuncts = (*conjuncts, render_mysql_expression(relation.filter.expression))
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
        emission=emission,
    )


def _with_dependencies(
    sql: str,
    relation: RelationIR,
    dependencies: tuple[RelationIR, ...],
    *,
    sources: Mapping[SymbolId, SourceIR],
    relations: Mapping[SymbolId, RelationIR],
    emission: MySqlEmission,
) -> str:
    """Define each relation the statement reads as a CTE before its SQL."""

    if not dependencies:
        return sql
    # A QUALIFY runs its windows in a derived table, so MySQL may merge its CTE
    # into each read and run them once per read, and ties may pick different
    # rows each time. MySQL's largest LIMIT keeps every row and stops the
    # merge, so the CTE is materialized once.
    definitions: list[str] = []
    for item, cte in zip(dependencies, alias_cte_outputs(dependencies, relation)):
        # A relation that refuses an output without an alias refuses here.
        sql_text = _cte_sql(
            item, sources=sources, relations=relations, emission=emission
        )
        if cte is not item:
            sql_text = render_mysql_relation(
                cte,
                sources=sources,
                relations=relations,
                emission=emission,
                _include_dependencies=False,
            )
        if item.qualify is not None and item.limit is None:
            sql_text += _EVERY_ROW
        name = quote_identifier(item.name, context="relation identifier")
        definitions.append(f"{name} AS (\n{sql_text}\n)")
    hidden = hidden_table_read(relation, dependencies, sources, relations, mysql=True)
    if hidden is not None:
        raise MySqlRenderError(
            f"Its SQL defines relation {hidden[0]} as a CTE, which would "
            f"hide table {hidden[1]} read in the same SQL; rename the "
            "relation or read the table with its schema"
        )
    # MySQL may compare CTE names without case: one WITH cannot hold both.
    names: dict[str, str] = {}
    for item in dependencies:
        other = names.setdefault(item.name.casefold(), item.name)
        if other != item.name:
            raise MySqlRenderError(
                f"Its SQL defines relations {other} and {item.name} as CTEs, "
                "whose names MySQL may compare without case; rename one of them"
            )
    # MySQL compares column names without case; a CTE's must be unique.
    for item in dependencies:
        outputs = _caseless_duplicate_outputs(item)
        if outputs is not None:
            raise MySqlRenderError(
                f"Its SQL defines relation {item.name} as a CTE with outputs "
                f"{outputs[0]} and {outputs[1]}, whose names MySQL compares "
                "without case; rename one of them"
            )
    unnamed = unnamed_output_read(relation, dependencies, mysql=True)
    if unnamed is not None:
        raise MySqlRenderError(unnamed)
    return "WITH " + ",\n".join(definitions) + f"\n{sql}"


def _cte_sql(
    relation: RelationIR,
    *,
    sources: Mapping[SymbolId, SourceIR],
    relations: Mapping[SymbolId, RelationIR],
    emission: MySqlEmission,
) -> str:
    """Render a relation as a CTE, or refuse it, once per emission.

    Its SQL reads nothing of the statement that defines it.
    """

    entry = emission.ctes.get(id(relation))
    if entry is None:
        try:
            sql = render_mysql_relation(
                relation,
                sources=sources,
                relations=relations,
                emission=emission,
                _include_dependencies=False,
            )
            entry = (relation, sql, False)
        except MySqlRenderError as error:
            entry = (relation, str(error), True)
        emission.ctes[id(relation)] = entry
    if entry[2]:
        raise MySqlRenderError(entry[1])
    return entry[1]


def _is_double_column(
    field: FieldRefIR | AnyFieldIR,
    reader: RelationIR | None,
    *,
    sources: Mapping[SymbolId, SourceIR],
    relations: Mapping[SymbolId, RelationIR],
    proved: dict[tuple[SymbolId, str], bool | None],
) -> bool:
    """Whether both targets hold a Float field as a DOUBLE.

    A source column is one. PostgreSQL holds a relation output as `numeric`
    when it computes it from exact values alone, such as `0.5 - 1e-17`, which
    MySQL may compute as a DOUBLE. A field without identity is an output of
    `reader`, as read by its QUALIFY, HAVING or ORDER BY.

    `proved` maps each relation output decided so far, or being decided, to
    its verdict, so each is proved once. The walk keeps an explicit stack, so
    a long chain of reads never exhausts the interpreter's recursion limit.
    """

    owner = _float_field_owner(field)
    if owner in sources:
        return True
    if owner is not None:
        reads: tuple[tuple[SymbolId, str], ...] | None = ((owner, field.name),)
    else:
        target = None if isinstance(field, AnyFieldIR) or field.qualifier else reader
        reads = _double_output_reads(target, field.name, sources)
    if reads is None:
        return False
    pending = list(reads)
    while pending:
        current = pending[-1]
        if proved.get(current) is not None:
            pending.pop()
            continue
        current_reads = _double_output_reads(
            relations.get(current[0]), current[1], sources
        )
        undecided = [read for read in current_reads or () if read not in proved]
        if undecided:
            proved[current] = None
            pending.extend(undecided)
            continue
        pending.pop()
        # An output still being decided reads itself: it is not proved.
        proved[current] = current_reads is not None and all(
            proved[read] is True for read in current_reads
        )
    return all(proved[read] is True for read in reads)


def _float_field_owner(field: FieldRefIR | AnyFieldIR) -> SymbolId | None:
    """Return the symbol that owns a field, if it has identity."""

    if isinstance(field, AnyFieldIR):
        return field.relation
    return None if field.field is None else field.field.owner


def _double_output_reads(
    relation: RelationIR | None,
    name: str,
    sources: Mapping[SymbolId, SourceIR],
) -> tuple[tuple[SymbolId, str], ...] | None:
    """Return the relation outputs that a DOUBLE output reads, each once.

    None means the output is not a DOUBLE on both targets, whatever its reads.
    """

    output = next(
        (
            item.expression
            for item in (() if relation is None else relation.projections)
            if item.name == name
        ),
        None,
    )
    if (
        output is None
        or not is_mysql_double(output)
        or has_inexact_float_arithmetic(output)
    ):
        return None
    reads: dict[tuple[SymbolId, str], None] = {}
    for item in mysql_float_fields(output):
        owner = _float_field_owner(item)
        if owner is None:
            return None
        if owner not in sources:
            reads[(owner, item.name)] = None
    return tuple(reads)


def _caseless_duplicate_outputs(relation: RelationIR) -> tuple[str, str] | None:
    """Return the first two output names that differ only in case."""

    names: dict[str, str] = {}
    for projection in relation.projections:
        if not projection.name:
            continue
        other = names.setdefault(projection.name.casefold(), projection.name)
        if other != projection.name:
            return other, projection.name
    return None


def _render_mysql_qualify_relation(
    relation: RelationIR,
    *,
    sources: Mapping[SymbolId, SourceIR],
    relations: Mapping[SymbolId, RelationIR],
    derived: str | None,
    emission: MySqlEmission,
) -> str:
    qualify = relation.qualify
    if type(qualify) is not QualifyIR:
        raise MySqlRenderError("MySQL QUALIFY requires an exact predicate")
    names = tuple(
        projection.name
        for projection in relation.projections
        if type(projection.name) is str
    )
    if len(names) != len(relation.projections) or any(not name for name in names):
        raise MySqlRenderError("MySQL QUALIFY requires named selected outputs")
    try:
        table, hidden, predicate, order_by = _qualify_outer_stage(relation)
    except ValueError as error:
        raise MySqlRenderError(str(error)) from error
    inner = replace(
        relation,
        qualify=None,
        projections=(*relation.projections, *hidden),
        order_by=(),
        limit=None,
    )
    # A JOIN's alias refusal comes first, as without QUALIFY.
    if inner.joins and derived is None:
        _refuse_join_aliases(inner)
    # MySQL compares column names without case; a derived table's must be unique.
    outputs = _caseless_duplicate_outputs(inner)
    if outputs is not None:
        raise MySqlRenderError(
            f"Its QUALIFY derived table has outputs {outputs[0]} and {outputs[1]}, "
            "whose names MySQL compares without case; rename one of them"
        )
    # The statement defines the relations both stages read, once, at its top.
    inner_sql = render_mysql_relation(
        inner,
        sources=sources,
        relations=relations,
        _include_dependencies=False,
        _derived=derived,
        emission=emission,
    )
    selected = ",\n".join(
        f"    {quote_identifier(name, context='select-list alias')}" for name in names
    )
    lines = [
        "SELECT",
        selected,
        "FROM (",
        inner_sql,
        f") AS {quote_identifier(table, context='derived table alias')}",
        "WHERE",
        f"    {render_mysql_expression(predicate)}",
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


def _join_inputs(
    relation: RelationIR,
    *,
    sources: Mapping[SymbolId, SourceIR],
    relations: Mapping[SymbolId, RelationIR],
    derived: str | None,
) -> list[str]:
    """Each input's `<table> AS <binding>` SQL, in input order."""

    tables = [
        _relation_input_sql(item.target, sources=sources, relations=relations)[0]
        if ordinal or derived is None
        else f"(\n{derived}\n)"
        for ordinal, item in enumerate(relation.inputs)
    ]
    return [
        f"{table} AS {quote_identifier(item.binding, context='relation identifier')}"
        for item, table in zip(relation.inputs, tables, strict=True)
    ]


def _join_aliases(relation: RelationIR) -> tuple[str, ...]:
    """The aliases of a JOIN statement's inputs and `any` reads."""

    return (
        *(item.binding for item in relation.inputs),
        *(item.binding for item in _exists_reads(relation)),
    )


def _refuse_join_aliases(relation: RelationIR) -> None:
    """Refuse an alias of a JOIN statement that MySQL may confuse with another.

    MySQL compares table aliases without case when the server keeps its table
    names in lowercase (lower_case_table_names), which emission cannot see:
    there two aliases that differ only in case are one, or an `any` alias hides
    an outer one.
    """

    names: dict[str, str] = {}
    for binding in _join_aliases(relation):
        other = names.setdefault(binding.casefold(), binding)
        if other != binding:
            raise MySqlRenderError(
                f"Its SQL aliases inputs {other} and {binding}, whose names MySQL "
                "may compare without case; rename one of them"
            )


def _render_mysql_full_relation(
    relation: RelationIR,
    full: JoinIR,
    *,
    sources: Mapping[SymbolId, SourceIR],
    relations: Mapping[SymbolId, RelationIR],
    derived: str | None,
) -> str:
    """Emulate the relation's first FULL JOIN, which MySQL lacks.

    The inputs through the FULL JOIN become one derived table, the LEFT JOIN
    of the FULL JOIN's condition, which holds every matched pair and every
    unmatched left row, then UNION ALL the RIGHT JOIN rows whose first
    earlier-input key is NULL, which are exactly the unmatched right rows, as
    every key of a matched pair is non-NULL. The derived table holds each
    field that the rest of the relation reads; that rest reads them from it.
    """

    ordinal = full.target_input
    prefix = replace(
        relation,
        projections=(),
        filter=None,
        group_keys=(),
        result_predicate=None,
        named_windows=(),
        order_by=(),
        limit=None,
        inputs=relation.inputs[: ordinal + 1],
        joins=relation.joins[:ordinal],
    )
    inputs = _join_inputs(prefix, sources=sources, relations=relations, derived=derived)
    left, _ = render_join_sql(prefix, inputs, MYSQL, full_as=JoinKindIR.LEFT)
    right, _ = render_join_sql(prefix, inputs, MYSQL, full_as=JoinKindIR.RIGHT)
    key = full_join_key(full)
    assert key is not None
    binding = relation.inputs[ordinal].binding
    # The derived table's name avoids each alias of the statement, without
    # case; a later FULL JOIN's derived table reads this one and reuses it.
    name = (
        relation.source.name
        if derived is not None
        else generated_name(
            chain(("__pietto_full",), (f"__pietto_full{n}" for n in count(2))),
            {alias.casefold() for alias in _join_aliases(relation)},
        )
    )
    try:
        outer, ports = _full_outer_stage(relation, ordinal, name)
    except ValueError as error:
        raise MySqlRenderError(str(error)) from error
    for field in ports.values():
        value_type = field.value_type
        if (
            value_type.canonical_kind is not TypeKindIR.BUILTIN
            or value_type.canonical_name == "Any"
        ):
            raise MySqlRenderError(
                f"MySQL emulates FULL JOIN {binding} with UNION ALL, which keeps "
                "the column types of builtin types other than Any only; "
                f"{field.qualifier[0]}.{field.name} has type "
                f"{value_type.declared_name}"
            )
    select = "SELECT\n" + ",\n".join(
        f"    {render_mysql_expression(field)} AS {quote_identifier(port)}"
        for port, field in (ports or {f"{name}_0": key}).items()
    )
    full_sql = "\n".join(
        (
            select,
            *left,
            "UNION ALL",
            select,
            *right,
            f"WHERE {render_mysql_expression(key)} IS NULL",
        )
    )
    return render_mysql_relation(
        outer,
        sources=sources,
        relations=relations,
        _include_dependencies=False,
        _derived=full_sql,
    )


def _full_outer_stage(
    relation: RelationIR, ordinal: int, name: str
) -> tuple[RelationIR, dict[str, FieldRefIR]]:
    """The relation after its FULL JOIN `ordinal`, over its derived table.

    Each field of an input through the FULL JOIN is read as a port
    `<name>_<n>` of the derived table `name`, the inputs after it are
    renumbered, and its first input is the derived table. Return that
    relation and each port's field.
    """

    symbol = SymbolId(SymbolNamespace.RELATION, name)
    later = relation.inputs[ordinal + 1 :]
    ports: dict[FieldId, str] = {}
    fields_by_port: dict[str, FieldRefIR] = {}

    def renumber(item: int) -> int:
        return 0 if item <= ordinal else item - ordinal

    def rewrite(value: Any) -> Any:
        if type(value) is FieldRefIR and value.field is not None:
            if value.field.input is None or value.field.input > ordinal:
                if value.field.input is None:
                    return value
                return replace(
                    value, field=replace(value.field, input=value.field.input - ordinal)
                )
            port = ports.setdefault(value.field, f"{name}_{len(ports)}")
            fields_by_port.setdefault(port, value)
            return FieldRefIR(
                span=value.span,
                value_type=value.value_type,
                name=port,
                qualifier=(name,),
                field=FieldId(owner=symbol, name=port, input=0 if later else None),
            )
        if type(value) is tuple:
            items = tuple(map(rewrite, value))
            changed = any(new is not old for new, old in zip(items, value, strict=True))
            return items if changed else value
        if is_dataclass(value) and not isinstance(value, type):
            changes = {
                item.name: new
                for item in dataclass_fields(value)
                if (new := rewrite(old := getattr(value, item.name))) is not old
            }
            return replace(value, **changes) if changes else value
        return value

    projections = rewrite(relation.projections)
    joins = tuple(
        replace(
            rewrite(join),
            ordinal=join.ordinal - ordinal,
            source_input=renumber(join.source_input),
            target_input=join.target_input - ordinal,
            hops=tuple(
                replace(
                    rewrite(hop),
                    left_input=renumber(hop.left_input),
                    right_input=hop.right_input - ordinal,
                )
                for hop in join.hops
            ),
            null_extends=tuple(dict.fromkeys(map(renumber, join.null_extends))),
        )
        for join in relation.joins[ordinal:]
    )
    source = RelationSourceIR(target=symbol, name=name, span=relation.source.span)
    outer = replace(
        relation,
        source=source,
        projections=projections,
        inputs=(
            ()
            if not later
            else (
                RelationInputIR(
                    ordinal=0,
                    role=RelationInputRoleIR.FROM,
                    target=symbol,
                    binding=name,
                    visible=True,
                    span=relation.source.span,
                ),
                *(replace(item, ordinal=item.ordinal - ordinal) for item in later),
            )
        ),
        joins=joins,
        filter=rewrite(relation.filter),
        group_keys=rewrite(relation.group_keys),
        result_predicate=rewrite(relation.result_predicate),
        named_windows=rewrite(relation.named_windows),
        order_by=rewrite(relation.order_by),
    )
    return outer, fields_by_port


def _relation_input_sql(
    target: SymbolId,
    *,
    sources: Mapping[SymbolId, SourceIR],
    relations: Mapping[SymbolId, RelationIR],
) -> tuple[str, str]:
    """Return the input's FROM SQL and the name that references it unaliased."""

    source = sources.get(target)
    if source is not None:
        parts = _mysql_table_name(source)
        sql = ".".join(
            quote_identifier(part, context="physical table identifier")
            for part in parts
        )
        return sql, parts[-1]
    upstream = relations.get(target)
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
    if isinstance(expression, (WindowCallIR, AggregateWindowCallIR)) and name is None:
        raise MySqlRenderError("MySQL window projections require an explicit alias")
    if (
        isinstance(expression, (WindowCallIR, AggregateWindowCallIR))
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
        if type(expression) is WindowCallIR:
            sql = render_mysql_window_call(expression, over_sql=over_sql)
        else:
            assert type(expression) is AggregateWindowCallIR
            sql = render_mysql_aggregate_window_call(expression, over_sql=over_sql)
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


def _render_named_over(expression: WindowCallIR | AggregateWindowCallIR) -> str:
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
        if isinstance(expression, (WindowCallIR, AggregateWindowCallIR)):
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
        relation.filter.expression, (WindowCallIR, AggregateWindowCallIR)
    ):
        raise MySqlRenderError("MySQL WHERE does not support direct window calls")
    if relation.result_predicate is not None and isinstance(
        relation.result_predicate.expression, (WindowCallIR, AggregateWindowCallIR)
    ):
        raise MySqlRenderError("MySQL HAVING does not support direct window calls")
    if any(
        isinstance(key, (WindowCallIR, AggregateWindowCallIR))
        for key in relation.group_keys
    ):
        raise MySqlRenderError("MySQL GROUP BY does not support direct window calls")
    if any(
        isinstance(item.expression, (WindowCallIR, AggregateWindowCallIR))
        for item in relation.order_by
    ):
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


def _render_order_item(item: OrderItemIR, position: int | None = None) -> str:
    if not isinstance(item.direction, OrderDirectionIR):
        raise MySqlRenderError("MySQL relation order direction is invalid")
    key = render_mysql_expression(item.expression) if position is None else position
    return f"{key} {item.direction.value}"
