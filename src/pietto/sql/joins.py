"""Internal FROM and JOIN lines of a relation with JOINs, for either target."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from pietto.ir.model import (
    BinaryIR,
    ComparisonIR,
    ExpressionIR,
    FieldRefIR,
    JoinIR,
    JoinKindIR,
    RelationIR,
    TypeKindIR,
)
from pietto.sql.expressions import refuse_text_null_condition, render_expression_sql
from pietto.sql.mysql_expressions import render_mysql_expression
from pietto.sql.mysql_render import MySqlRenderError

_JOIN_KEYWORDS = {
    JoinKindIR.INNER: "INNER JOIN",
    JoinKindIR.LEFT: "LEFT JOIN",
    JoinKindIR.RIGHT: "RIGHT JOIN",
    JoinKindIR.FULL: "FULL JOIN",
    JoinKindIR.CROSS: "CROSS JOIN",
}
_EXISTS_KEYWORDS = {JoinKindIR.SEMI: "EXISTS", JoinKindIR.ANTI: "NOT EXISTS"}


@dataclass(frozen=True, slots=True)
class JoinTarget:
    """What one SQL target lends the shared JOIN algorithm."""

    name: str
    render: Callable[[ExpressionIR], str]
    error: type[Exception]
    refuse_condition: Callable[[ExpressionIR], None]
    native_full: bool


POSTGRESQL = JoinTarget(
    name="PostgreSQL",
    render=render_expression_sql,
    error=ValueError,
    refuse_condition=refuse_text_null_condition,
    native_full=True,
)
MYSQL = JoinTarget(
    name="MySQL",
    render=render_mysql_expression,
    error=MySqlRenderError,
    # MySQL takes a NULL of any type where it takes a Boolean.
    refuse_condition=lambda condition: None,
    native_full=False,
)


def render_join_sql(
    relation: RelationIR,
    inputs: Sequence[str],
    target: JoinTarget = POSTGRESQL,
    *,
    full_as: JoinKindIR | None = None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Render the FROM line, one line per row JOIN and the pending filters.

    `inputs` holds each input's SQL, `<table> AS <binding>`, in input order. A
    SEMI or ANTI JOIN renders no line: it becomes an [NOT] EXISTS filter that a
    later INNER, LEFT, CROSS, SEMI or ANTI JOIN keeps pending, as the filter
    reads only columns of earlier inputs, which those JOINs never NULL-extend.
    The next RIGHT JOIN takes the pending filters into its ON, and a FULL JOIN
    while any is pending is refused; the filters still pending at the end lead
    the relation's WHERE, in JOIN order. A target without FULL JOIN renders a
    FULL JOIN that passes the same checks as the kind `full_as` names.
    """

    lines = [f"FROM {inputs[0]}"]
    pending: list[str] = []
    for join in relation.joins:
        kind = JoinKindIR(join.kind)
        if kind is JoinKindIR.FULL:
            binding = relation.inputs[join.target_input].binding
            if pending:
                raise target.error(
                    f"A SEMI or ANTI JOIN before FULL JOIN {binding} is not "
                    f"available in {target.name} emission yet"
                )
            if full_join_key(join) is None:
                raise target.error(
                    f"{target.name} FULL JOIN {binding} needs an ON made only of "
                    "equalities between Int fields of its two sides; Pietto does "
                    "not rewrite other FULL JOIN conditions yet"
                )
            if not target.native_full:
                if full_as is None:
                    raise target.error(f"{target.name} has no FULL JOIN")
                kind = full_as
        if join.condition is not None:
            target.refuse_condition(join.condition)
        conjuncts = [
            f"{target.render(equality.left)} = {target.render(equality.right)}"
            for hop in join.hops
            for equality in hop.equalities
        ]
        if join.condition is not None:
            conjuncts.append(target.render(join.condition))
        joined = inputs[join.target_input]
        if kind in _EXISTS_KEYWORDS:
            pending.append(
                f"{_EXISTS_KEYWORDS[kind]} (SELECT 1 FROM {joined} "
                f"WHERE {render_conjunction_sql(conjuncts)})"
            )
            continue
        if kind is JoinKindIR.CROSS:
            lines.append(f"{_JOIN_KEYWORDS[kind]} {joined}")
            continue
        if kind is JoinKindIR.RIGHT:
            conjuncts.extend(pending)
            pending.clear()
        lines.append(
            f"{_JOIN_KEYWORDS[kind]} {joined} ON {render_conjunction_sql(conjuncts)}"
        )
    return tuple(lines), tuple(pending)


def render_conjunction_sql(conjuncts: Sequence[str]) -> str:
    """Render one conjunct as is, or several each parenthesized and ANDed."""

    if len(conjuncts) == 1:
        return conjuncts[0]
    return " AND ".join(f"({conjunct})" for conjunct in conjuncts)


def full_join_key(join: JoinIR) -> FieldRefIR | None:
    """The earlier-input field of a FULL JOIN's first conjunct, if it is exact.

    PostgreSQL plans a FULL JOIN only on merge- or hash-joinable conditions.
    The conjuncts are the hop equalities and the `on` split at every `and`;
    each must equate a field of an earlier input with a field of the target,
    both of builtin Int type once aliases are expanded, whatever their
    nullability. Otherwise None. Every such field is non-NULL in a row the
    JOIN matches.
    """

    sides: list[tuple[ExpressionIR, ExpressionIR]] = [
        (equality.left, equality.right)
        for hop in join.hops
        for equality in hop.equalities
    ]
    pending = [] if join.condition is None else [join.condition]
    while pending:
        node = pending.pop(0)
        if type(node) is BinaryIR and node.operator == "and":
            pending[:0] = (node.left, node.right)
        elif type(node) is ComparisonIR and node.operator == "==":
            sides.append((node.left, node.right))
        else:
            return None
    for left, right in sides:
        inputs = (_int_field_input(left), _int_field_input(right))
        if None in inputs or inputs.count(join.target_input) != 1:
            return None
    left, right = sides[0]
    key = right if _int_field_input(left) == join.target_input else left
    assert type(key) is FieldRefIR
    return key


def _int_field_input(expression: ExpressionIR) -> int | None:
    """The input of a resolved field reference of builtin Int type, else None."""

    if (
        type(expression) is FieldRefIR
        and expression.field is not None
        and expression.value_type.canonical_kind is TypeKindIR.BUILTIN
        and expression.value_type.canonical_name == "Int"
    ):
        return expression.field.input
    return None
