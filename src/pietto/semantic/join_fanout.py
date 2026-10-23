"""The conservative fan-out rule for aggregates over single-file JOIN rows.

Private: nothing here is exported. It reads only the AST, diagnostics and
semantic facts, never project code.
"""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ast_nodes import (
    AuthoredJoinKind,
    CallExpr,
    Definition,
    DottedNameExpr,
    Expression,
    NameExpr,
    QueryDef,
    ShapeDef,
    SourceDef,
    TableDef,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.aggregates import (
    COUNT_AGGREGATE_NAME,
    child_expressions,
    semantic_aggregate_call_name,
)
from pietto.semantic.model import (
    EffectiveNullability,
    JoinFieldRef,
    RelationJoinsInfo,
    RowSchema,
)

__all__ = ()

# An edge `u -> v`: in every JOIN row the part of input u, NULL included,
# determines the part of input v.
type _Edge = tuple[int, int]
type _KeyIdentity = tuple[str, frozenset[str]]

_NOT_FACTORS = (AuthoredJoinKind.SEMI, AuthoredJoinKind.ANTI)
_FORWARD_KINDS = (AuthoredJoinKind.INNER, AuthoredJoinKind.LEFT)


def join_fanout_diagnostics(
    definition: TableDef | QueryDef,
    info: RelationJoinsInfo,
    *,
    type_symbols: Mapping[str, Definition],  # shapes of sources (keys)
    source_row_schemas: Mapping[SourceDef, RowSchema],  # NOT NULL of key fields
    let_expressions: Mapping[str, Expression],  # admitted `let:` values
) -> tuple[Diagnostic, ...]:
    """One PIE-S2381 per refused aggregate call, in select order."""

    # Factors: the FROM input and every JOIN target other than SEMI and ANTI.
    factors = frozenset({0}).union(
        join.target_input for join in info.joins if join.kind not in _NOT_FACTORS
    )
    keys = tuple(_declared_keys(item.relation, type_symbols) for item in info.inputs)
    edges = _edges(info, keys)
    protected = _group_protection(
        definition, info, keys, factors, source_row_schemas, let_expressions
    )
    diagnostics: list[Diagnostic] = []
    for item in definition.select_items:
        call = item.expression
        name = semantic_aggregate_call_name(call)
        if name is None or item.alias is None or not isinstance(call, CallExpr):
            continue
        if name == COUNT_AGGREGATE_NAME and not call.arguments:
            # count() counts JOIN rows by definition.
            continue
        seed = _argument_inputs(call, info, let_expressions) | protected
        if factors <= _closure(seed, edges):
            continue
        span = call.span
        diagnostics.append(
            Diagnostic(
                code="PIE-S2381",
                severity=Severity.ERROR,
                message=_message(info, factors, seed, edges),
                location=SourceLocation(
                    path=span.path,
                    line=span.line,
                    column=span.column,
                    end_line=span.end_line,
                    end_column=span.end_column,
                ),
            )
        )
    return tuple(diagnostics)


def _declared_keys(
    relation: SourceDef | TableDef | QueryDef,
    type_symbols: Mapping[str, Definition],
) -> tuple[tuple[str, ...], ...]:
    """The field sets of a source shape's `unique` items in declaration order;
    tables and queries carry no keys."""

    if not isinstance(relation, SourceDef) or relation.shape_name is None:
        return ()
    shape = type_symbols.get(relation.shape_name)
    if not isinstance(shape, ShapeDef):
        return ()
    return tuple(unique.field_names for unique in shape.uniques)


def _edges(
    info: RelationJoinsInfo, keys: tuple[tuple[tuple[str, ...], ...], ...]
) -> tuple[_Edge, ...]:
    """Forward edges of INNER and LEFT relationship JOINs whose target fields
    hold a key of the target, reverse edges of INNER JOINs without `on` whose
    source fields hold a key of the source; nothing else gives an edge."""

    edges: list[_Edge] = []
    for join in info.joins:
        if join.mode not in ("M1", "M2", "M4"):
            continue
        sources = frozenset(equality.left.field for equality in join.equalities)
        targets = frozenset(equality.right.field for equality in join.equalities)
        if join.kind in _FORWARD_KINDS and any(
            frozenset(key) <= targets for key in keys[join.target_input]
        ):
            edges.append((join.source_input, join.target_input))
        if (
            join.kind is AuthoredJoinKind.INNER
            and join.mode in ("M1", "M2")
            and any(frozenset(key) <= sources for key in keys[join.source_input])
        ):
            edges.append((join.target_input, join.source_input))
    return tuple(edges)


def _group_protection(
    definition: TableDef | QueryDef,
    info: RelationJoinsInfo,
    keys: tuple[tuple[tuple[str, ...], ...], ...],
    factors: frozenset[int],
    source_row_schemas: Mapping[SourceDef, RowSchema],
    let_expressions: Mapping[str, Expression],
) -> frozenset[int]:
    """Every factor with a strict key whose fields are all GROUP BY keys."""

    grouped: set[tuple[int, str]] = set()
    if definition.group_by_clause is not None:
        for item in definition.group_by_clause.items:
            read = _renamed_field(item.key, info, let_expressions)
            if read is not None:
                grouped.add((read.input, read.field))
    protected: set[int] = set()
    for position in factors:
        relation = info.inputs[position].relation
        schema = (
            source_row_schemas.get(relation)
            if isinstance(relation, SourceDef)
            else None
        )
        if schema is None:
            continue
        for key in keys[position]:
            fields = tuple(schema.fields.get(name) for name in key)
            if all((position, name) in grouped for name in key) and all(
                field is not None and field.nullability is EffectiveNullability.NON_NULL
                for field in fields
            ):
                protected.add(position)
                break
    return frozenset(protected)


def _renamed_field(
    expression: Expression,
    info: RelationJoinsInfo,
    let_expressions: Mapping[str, Expression],
) -> JoinFieldRef | None:
    """The field a GROUP BY key reads, following `let:` names that rename one."""

    followed: set[str] = set()
    while isinstance(expression, (NameExpr, DottedNameExpr)):
        read = info.field_reads.get(expression)
        if read is not None:
            return read
        if (
            not isinstance(expression, NameExpr)
            or expression.name in followed
            or expression.name not in let_expressions
        ):
            return None
        followed.add(expression.name)
        expression = let_expressions[expression.name]
    return None


def _argument_inputs(
    call: CallExpr,
    info: RelationJoinsInfo,
    let_expressions: Mapping[str, Expression],
) -> frozenset[int]:
    """The inputs whose fields the arguments read, through `let:` names."""

    inputs: set[int] = set()
    followed: set[str] = set()
    pending: list[Expression] = list(call.arguments)
    while pending:
        node = pending.pop()
        if not isinstance(node, (NameExpr, DottedNameExpr)):
            pending.extend(child_expressions(node))
            continue
        read = info.field_reads.get(node)
        if read is not None:
            inputs.add(read.input)
        elif (
            isinstance(node, NameExpr)
            and node.name in let_expressions
            and node.name not in followed
        ):
            followed.add(node.name)
            pending.append(let_expressions[node.name])
    return frozenset(inputs)


def _closure(
    seed: frozenset[int],
    edges: tuple[_Edge, ...],
    extra: tuple[_Edge, ...] = (),
) -> frozenset[int]:
    closed = set(seed)
    grown = True
    while grown:
        grown = False
        for lhs, rhs in (*edges, *extra):
            if lhs in closed and rhs not in closed:
                closed.add(rhs)
                grown = True
    return frozenset(closed)


def _message(
    info: RelationJoinsInfo,
    factors: frozenset[int],
    seed: frozenset[int],
    edges: tuple[_Edge, ...],
) -> str:
    """The JOINs that may repeat the aggregate's rows, then the keys whose
    declaration, or the inputs whose grouping, would close the rule."""

    def binding(position: int) -> str:
        return info.inputs[position].binding

    reached = _closure(seed, edges)
    repeated = tuple(
        dict.fromkeys(
            f"JOIN {binding(join.target_input)}"
            for join in info.joins
            if join.kind not in _NOT_FACTORS
            and (join.source_input in reached) != (join.target_input in reached)
        )
    )

    # Declarable keys: the edges a missing declaration could add, keyed by
    # (relation, field set); the first JOIN that needs a key spells it.
    keys: dict[_KeyIdentity, tuple[str, list[_Edge], dict[str, None]]] = {}
    for join in info.joins:
        if join.mode not in ("M1", "M2"):
            continue
        sides: list[tuple[int, tuple[str, ...], _Edge]] = []
        if join.kind in _FORWARD_KINDS:
            sides.append(
                (
                    join.target_input,
                    tuple(dict.fromkeys(item.right.field for item in join.equalities)),
                    (join.source_input, join.target_input),
                )
            )
        if join.kind is AuthoredJoinKind.INNER:
            sides.append(
                (
                    join.source_input,
                    tuple(dict.fromkeys(item.left.field for item in join.equalities)),
                    (join.target_input, join.source_input),
                )
            )
        for position, fields, dependency in sides:
            relation = info.inputs[position].relation
            if not isinstance(relation, SourceDef):
                continue
            _, dependencies, matched = keys.setdefault(
                (relation.name, frozenset(fields)),
                (_key(relation.name, fields), [], {}),
            )
            dependencies.append(dependency)
            matched[binding(join.target_input)] = None

    def with_keys(chosen: tuple[_KeyIdentity, ...]) -> tuple[_Edge, ...]:
        return tuple(edge for key in chosen for edge in keys[key][1])

    chosen: tuple[_KeyIdentity, ...] | None = ()
    while chosen is not None and not factors <= _closure(
        seed, edges, with_keys(chosen)
    ):
        current = _closure(seed, edges, with_keys(chosen))
        found = next(
            (
                key
                for key, (_, dependencies, _) in keys.items()
                if key not in chosen
                and any(
                    lhs in current and rhs not in current for lhs, rhs in dependencies
                )
            ),
            None,
        )
        chosen = None if found is None else (*chosen, found)
    if chosen:
        for key in tuple(chosen):
            rest = tuple(other for other in chosen if other != key)
            if factors <= _closure(seed, edges, with_keys(rest)):
                chosen = rest
    declared = tuple(key for key in keys if key in (chosen or ()))

    # Group keys: the source factors, each dropped when the rest still close.
    picked = tuple(
        position
        for position, item in enumerate(info.inputs)
        if position in factors and isinstance(item.relation, SourceDef)
    )

    def grouped(inputs: tuple[int, ...]) -> bool:
        return factors <= _closure(seed | frozenset(inputs), edges)

    if grouped(picked):
        for position in tuple(picked):
            rest = tuple(other for other in picked if other != position)
            if grouped(rest):
                picked = rest
    else:
        picked = ()

    remedies: list[str] = []
    if declared:
        remedies.append(
            "declare "
            + _and_list(
                tuple(
                    f"a unique key on {keys[key][0]} (matched by "
                    f"JOIN{'s' if len(keys[key][2]) > 1 else ''} "
                    f"{_and_list(tuple(keys[key][2]))})"
                    for key in declared
                )
            )
        )
    if picked:
        noun = "a unique key" if len(picked) == 1 else "unique keys"
        remedies.append(
            f"group by {noun} of {_and_list(tuple(binding(item) for item in picked))} "
            "whose fields are all not null"
        )
    cause = (
        f"An aggregate may read rows repeated by {_and_list(repeated)}"
        if repeated
        else "An aggregate may read rows that a JOIN repeats"
    )
    return cause + ("; " + ", or ".join(remedies) if remedies else "")


def _key(relation: str, fields: tuple[str, ...]) -> str:
    if len(fields) == 1:
        return f"{relation}.{fields[0]}"
    return f"{relation} ({', '.join(fields)})"


def _and_list(items: tuple[str, ...]) -> str:
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"
