"""Typed original token fragments; no SQL parsing or unguarded semantic clone.

Every fragment is a complete unit of an independently verified original AST.
Only identified source/parameter tokens and final private labels may relocate.
"""

from dataclasses import dataclass, field
from typing import Any

from pietto._project.project_sql_emission_results import RowResultBody

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class OriginalFragment:
    unit: Any = field(repr=False)
    events: tuple = field(repr=False)
    position: int


def original_fragments(program):
    rendered = program.preparation.artifact.rendered
    openings = tuple(e for e in rendered.events if e.role == "cte_body_open")
    endings = tuple(e for e in rendered.events if e.role == "cte_body_close")
    units = program.output.units
    if len(openings) != len(units) - 1 or len(openings) != len(endings):
        raise ValueError("GUARD_ORIGINAL_UNIT_RANGES")
    ranges = [(a.end, b.start) for a, b in zip(openings, endings, strict=True)]
    body = tuple(e for e in rendered.events if e.role == "with_body")
    ranges.append((body[0].end if body else 0, len(rendered.sql)))
    return tuple(
        OriginalFragment(
            unit,
            tuple(e for e in rendered.events if low <= e.start and e.end <= high),
            i,
        )
        for i, (unit, (low, high)) in enumerate(zip(units, ranges, strict=True))
    )


def terminal_order(program):
    """Carry only the original final order, without selecting a tie refinement."""
    unit = program.output.units[-1]
    if type(unit) is not RowResultBody or unit.order is None:
        return (), ()
    extra, ordered = [], []
    for position, item in enumerate(unit.order.items):
        if unit.distinct is not None:
            matches = tuple(
                i
                for i, c in enumerate(unit.columns)
                if c.read.terminal is item.read.terminal
                and c.read.name == item.read.name
            )
            if len(matches) != 1:
                raise ValueError("GUARD_DISTINCT_ORDER_CORRESPONDENCE")
            name = program.prefix + "v" + str(matches[0])
        else:
            name = program.prefix + "o" + str(position)
            extra.append((name, unit.scan.symbol.name, item.read.name, item))
        ordered.append((name, item.direction))
    return tuple(extra), tuple(ordered)


def refined_guard_syntax(statement):
    """Complete refined producer terminals; no page predicate enters a guard."""
    from pietto._project.project_refinement_rendering import (
        Expr,
        Relation,
        Select,
        Statement,
        conjunction,
        integer,
        ref,
    )
    from pietto._project.project_sql_emission_contract import BoundSource

    program = statement.program
    query = program.refinement
    if query is None or statement.kind != "guard":
        raise ValueError("GUARD_REFINED_STATEMENT")

    def relation(item):
        if type(item.producer) is BoundSource:
            (i,) = tuple(
                i
                for i, s in enumerate(query.original.request.sources)
                if s is item.producer
            )
            name = query.prefix + "source" + str(i)
        else:
            (producer,) = tuple(u for u in query.units if u.original is item.producer)
            name = producer.terminal
        return Relation((name,), item.symbol.name)

    columns = []
    for i, subject in enumerate(statement.subjects):
        unit = subject.unit
        condition = conjunction(
            *(
                Expr(
                    "=",
                    (
                        ref(e.left_scope.name, e.left.name),
                        ref(e.right_scope.name, e.right.name),
                    ),
                )
                for e in unit.equalities
            ),
            None
            if unit.predicate is None
            else Expr("original_scalar", (unit.predicate, "")),
        )
        second = Select(
            ((program.prefix + "one", integer(1)),),
            relation(subject.inputs[1]),
            where=condition,
            limit=Expr("guard_control", (statement.controls[0],)),
            offset=Expr("guard_control", (statement.controls[1],)),
        )
        bad = Select(
            ((program.prefix + "one", integer(1)),),
            relation(subject.inputs[0]),
            where=Expr("exists", (second,)),
        )
        flag = Expr(
            "cast_integer",
            (Expr("case", (Expr("exists", (bad,)), integer(1), integer(0))),),
        )
        columns.append((program.prefix + "g" + str(i), flag))
    return Statement(
        query.statement.ctes, Select(tuple(columns), None), query.statement.recursive
    )
