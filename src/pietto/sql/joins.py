"""Internal PostgreSQL FROM and JOIN lines of a relation with JOINs."""

from __future__ import annotations

from collections.abc import Sequence

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
from pietto.sql.render import quote_identifier, quote_qualified_identifier

_JOIN_KEYWORDS = {
    JoinKindIR.INNER: "INNER JOIN",
    JoinKindIR.LEFT: "LEFT JOIN",
    JoinKindIR.RIGHT: "RIGHT JOIN",
    JoinKindIR.FULL: "FULL JOIN",
    JoinKindIR.CROSS: "CROSS JOIN",
}
_EXISTS_KEYWORDS = {JoinKindIR.SEMI: "EXISTS", JoinKindIR.ANTI: "NOT EXISTS"}


def render_join_sql(
    relation: RelationIR,
    input_names: Sequence[tuple[str, ...]],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Render the FROM line, one line per row JOIN and the pending filters.

    `input_names` holds the SQL name of each input, in input order. Every
    input is aliased with its binding. A SEMI or ANTI JOIN renders no line: it
    becomes an [NOT] EXISTS filter that a later INNER, LEFT, CROSS, SEMI or ANTI
    JOIN keeps pending, as the filter reads only columns of earlier inputs,
    which those JOINs never NULL-extend. The next RIGHT JOIN takes the pending
    filters into its ON, and a FULL JOIN while any is pending is refused; the
    filters still pending at the end lead the relation's WHERE, in JOIN order.
    """

    inputs = [
        f"{quote_qualified_identifier(name)} AS {quote_identifier(item.binding)}"
        for item, name in zip(relation.inputs, input_names, strict=True)
    ]
    lines = [f"FROM {inputs[0]}"]
    pending: list[str] = []
    for join in relation.joins:
        kind = JoinKindIR(join.kind)
        binding = relation.inputs[join.target_input].binding
        if kind is JoinKindIR.FULL and pending:
            raise ValueError(
                f"A SEMI or ANTI JOIN before FULL JOIN {binding} is not available "
                "in PostgreSQL emission yet"
            )
        if kind is JoinKindIR.FULL and not _natively_executable(join):
            raise ValueError(
                f"PostgreSQL FULL JOIN {binding} needs an ON made only of equalities "
                "between Int fields of its two sides; Pietto does not rewrite other "
                "FULL JOIN conditions yet"
            )
        if join.condition is not None:
            refuse_text_null_condition(join.condition)
        conjuncts = [
            f"{render_expression_sql(equality.left)} = "
            f"{render_expression_sql(equality.right)}"
            for hop in join.hops
            for equality in hop.equalities
        ]
        if join.condition is not None:
            conjuncts.append(render_expression_sql(join.condition))
        target = inputs[join.target_input]
        if kind in _EXISTS_KEYWORDS:
            pending.append(
                f"{_EXISTS_KEYWORDS[kind]} (SELECT 1 FROM {target} "
                f"WHERE {render_conjunction_sql(conjuncts)})"
            )
            continue
        if kind is JoinKindIR.CROSS:
            lines.append(f"{_JOIN_KEYWORDS[kind]} {target}")
            continue
        if kind is JoinKindIR.RIGHT:
            conjuncts.extend(pending)
            pending.clear()
        lines.append(
            f"{_JOIN_KEYWORDS[kind]} {target} ON {render_conjunction_sql(conjuncts)}"
        )
    return tuple(lines), tuple(pending)


def render_conjunction_sql(conjuncts: Sequence[str]) -> str:
    """Render one conjunct as is, or several each parenthesized and ANDed."""

    if len(conjuncts) == 1:
        return conjuncts[0]
    return " AND ".join(f"({conjunct})" for conjunct in conjuncts)


def _natively_executable(join: JoinIR) -> bool:
    """Whether every conjunct of a FULL JOIN is an Int field equality across it.

    PostgreSQL plans a FULL JOIN only on merge- or hash-joinable conditions.
    The conjuncts are the hop equalities and the `on` split at every `and`;
    each must equate a field of an earlier input with a field of the target,
    both of builtin Int type once aliases are expanded, whatever their
    nullability.
    """

    sides: list[tuple[ExpressionIR, ExpressionIR]] = [
        (equality.left, equality.right)
        for hop in join.hops
        for equality in hop.equalities
    ]
    pending = [] if join.condition is None else [join.condition]
    while pending:
        node = pending.pop()
        if type(node) is BinaryIR and node.operator == "and":
            pending.extend((node.left, node.right))
        elif type(node) is ComparisonIR and node.operator == "==":
            sides.append((node.left, node.right))
        else:
            return False
    for left, right in sides:
        inputs = (_int_field_input(left), _int_field_input(right))
        if None in inputs or inputs.count(join.target_input) != 1:
            return False
    return True


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
