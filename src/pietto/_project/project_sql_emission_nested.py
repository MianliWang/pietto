"""Collect read SQL construction: one ``LEFT JOIN LATERAL`` aggregate per read.

A Collect read is the value of one nested export of its parent: per parent row,
the complete bag of its collected relation let, in that let's own ORDER. It is
emitted as one single-row aggregate attached after the FROM of the parent body
that realizes the parent's projection block::

    LEFT JOIN LATERAL (SELECT COUNT(*) AS "n",
        ARRAY_AGG("e<n>"."c0" ORDER BY "e<n>"."c<V>") AS "a0", ...
        FROM <terminal> AS "e<n>") AS "g<n>" ON TRUE

The parent column is the count column under the field's label, then one array
column per child field under the child's label (``pg_column_arrays_v1``). Each
lateral reads only its parent row, so sibling Collects are never joined before
they are collected. Every array of one lateral orders by one ordinal, so the
arrays of one evaluation stay aligned. The ordinal restates exactly the let's
terminal ORDER items: a private column of the terminal result body when it has
no DISTINCT, or a wrapper SELECT at the read when it has one, because a window
function in a DISTINCT SELECT would make every row distinct.

This module owns the Collect-specific construction only. The renderer turns the
returned nodes into bytes and the independent verifier re-derives them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from pietto._project import project_sql_emission_results as resulting
from pietto._project import project_sql_emission_rows as rows

__all__: tuple[str, ...] = ()

COUNT = "n"
"""The lateral's count column: ``COUNT(*)`` counts an all-NULL child row."""


@dataclass(frozen=True, slots=True, eq=False)
class CollectOrdinal:
    """``ROW_NUMBER() OVER (ORDER BY <keys>) AS <symbol>``: one terminal's sequence.

    ``order`` is the collected terminal's own ORDER. ``scope`` is the alias the
    keys read: the terminal's result scope, or the DISTINCT wrapper of a read.
    Each key is ``(order item, column name, direction)`` of one ORDER item, in
    item order, with no NULLS spelling.
    """

    order: Any
    scope: Any
    keys: tuple[tuple[Any, str, str], ...]
    symbol: Any


@dataclass(frozen=True, slots=True, eq=False)
class CollectLateral:
    """One Collect read's single-row aggregate over its collected terminal.

    ``target`` is the realized expression block use: the producer's terminal
    result body (a CTE, or a captured let's inline chain) and its ``e<n>``
    alias. ``arrays`` are ``(child port, column read, ordering column, alias)``
    in child order. ``wrapper`` names the DISTINCT terminal's ordinal wrapper
    and is None otherwise; ``sources`` are the terminal's visible column names.
    """

    collect: Any
    target: rows.SQLBlockTarget
    symbol: Any
    arrays: tuple[tuple[Any, str, str, str], ...]
    ordinal: CollectOrdinal
    wrapper: Any
    sources: tuple[str, ...]


@dataclass(frozen=True, slots=True, eq=False)
class CollectColumn:
    """One nested export of a parent body: 1+F physical columns of its lateral.

    ``carriers`` are ``(lateral column, label, subject)``: the count under the
    field's label, then each child's array under the child's label (or the
    private ``c<i>`` and ``c<i>_<j>`` of a closed stage). ``column`` has no
    scalar realization, so a scalar reader of a nested value fails closed.
    """

    ordinal: int
    export: Any
    collect: Any
    lateral: CollectLateral
    symbol: Any
    label: str
    carriers: tuple[tuple[str, str, Any], ...]
    column: rows.StageColumn


def collect_admitted(plan, collect, family) -> bool:
    """D-S08-4: PostgreSQL emits a Collect read of the selected table or query.

    A statement that reads the relation holding a Collect read from another
    relation carries the nested value through a reader (S16), and no other
    target emits a Collect read, so each of those keeps its refusal.
    """
    blocks = tuple(block for block in plan.blocks if block.ref is collect.block)
    owners = tuple(
        definition.entry.owner
        for definition in plan.bindings.definitions
        if len(blocks) == 1 and definition.ref is blocks[0].definition
    )
    return (
        family == "postgres"
        and len(owners) == 1
        and owners[0] is plan.scope.selected_owner
    )


def field_names(lateral: CollectLateral) -> tuple[str, ...]:
    """The child field labels: the collected terminal's own visible exports."""
    return tuple(
        column.export.identity.name for column in lateral.target.producer.columns
    )


def ordinal_terminal(body) -> CollectOrdinal | None:
    """The private ordinal column of one collected terminal without DISTINCT.

    It is named after the terminal's visible columns and restates exactly its
    ORDER items under its own result scope. None for a DISTINCT terminal (each
    read wraps it instead) or a terminal without ORDER.
    """
    from pietto._project.project_sql_emission_ast import SQLSymbol

    if body.distinct is not None or body.order is None:
        return None
    width = len(body.columns)
    return CollectOrdinal(
        body.order,
        body.scan.symbol,
        tuple((item, item.read.name, item.direction) for item in body.order.items),
        SQLSymbol(width, body.order.order.ref, f"c{width}"),
    )


def realize_collect(collect, target, *, export, position, final, terminal):
    """Realize one Collect read as its parent column and that column's lateral.

    ``export`` is the parent's nested export, ``terminal`` the terminal port of
    the parent column at ``position``; ``final`` labels the carriers with the
    field and child labels. Returns ``(column, None)`` or ``(None, problem)``.
    The parent is the selected owner on PostgreSQL alone (D-S08-4), so the
    children's labels are its output labels whichever body writes them, and
    each is admitted as a flat output label is, even at a closed stage.
    """
    from pietto._project.project_sql_emission_ast import SQLSymbol, identifier_valid

    def problem(detail):
        return None, ("PIE-B1001", detail, collect.ref, None)

    unit = target.producer
    children = tuple(collect.children)
    if (
        target.use.ref is not collect.use
        or target.source is not None
        or export.ref is not collect.export
    ):
        return problem("collect_read_drift")
    if (
        type(unit) is not resulting.RowResultBody
        or unit.order is None
        or unit.definition.original.ref is not collect.producer
    ):
        return problem("collect_terminal_without_order")
    if (
        not children
        or len(children) != len(unit.columns)
        or any(
            column.export.ref is not child
            for column, child in zip(unit.columns, children, strict=True)
        )
    ):
        return problem("collect_children_drift")
    for column in unit.columns:
        if not identifier_valid(column.export.identity.name, "postgres", label=True):
            return None, (
                "PIE-B1002",
                "output_label_unrepresentable",
                column.export.ref,
                None,
            )
    sources = []
    for index in range(len(children)):
        read = rows.block_column(target, index)
        if read is None:
            return problem("collect_children_drift")
        sources.append(read[0])
    n = target.use.ref.position
    width = len(children)
    if unit.distinct is None:
        if unit.ordinal is None:
            return problem("collect_terminal_without_ordinal")
        ordinal, wrapper, reads = unit.ordinal, None, tuple(sources)
    else:
        if unit.ordinal is not None:
            return problem("collect_ordinal_inside_distinct")
        wrapper = SQLSymbol(0, collect.ref, f"d{n}")
        keys = []
        for item in unit.order.items:
            visible = tuple(
                index
                for index, column in enumerate(unit.columns)
                if column.read is item.read
            )
            if len(visible) != 1:
                return problem("collect_order_key_not_visible")
            keys.append((item, sources[visible[0]], item.direction))
        ordinal = CollectOrdinal(
            unit.order,
            wrapper,
            tuple(keys),
            SQLSymbol(width, unit.order.order.ref, f"c{width}"),
        )
        reads = tuple(f"c{index}" for index in range(width))
    lateral = CollectLateral(
        collect,
        target,
        SQLSymbol(0, collect.ref, f"g{n}"),
        tuple(
            (child, reads[index], ordinal.symbol.name, f"a{index}")
            for index, child in enumerate(children)
        ),
        ordinal,
        wrapper,
        tuple(sources),
    )
    label = export.identity.name if final else f"c{position}"
    names = field_names(lateral)
    carriers = (
        (COUNT, label, export.ref),
        *(
            (alias, names[index] if final else f"c{position}_{index}", child)
            for index, (child, _, _, alias) in enumerate(lateral.arrays)
        ),
    )
    return (
        CollectColumn(
            position,
            export,
            collect,
            lateral,
            SQLSymbol(position + 1, export.ref, label),
            label,
            carriers,
            # A nested group has no scalar realization.
            rows.StageColumn(position, label, terminal.ref, cast(Any, None)),
        ),
        None,
    )


def physical_width(unit) -> int:
    """Physical columns of one generated unit: a nested group is 1+F columns
    and a collected terminal's ordinal is one more."""
    width = sum(
        len(column.carriers)
        if type(column) in (CollectColumn, resulting.ResultGroupColumn)
        else 1
        for column in unit.columns
    )
    return width + (getattr(unit, "ordinal", None) is not None)


def node_count(lateral: CollectLateral) -> int:
    """The lateral (join, SELECT, FROM, alias, ON), its count, each array's
    aggregate, ORDER BY and parent carrier column, and a DISTINCT wrapper's
    SELECT, FROM, carried columns and ordinal."""
    total = 5 + 1 + 3 * len(lateral.arrays)
    if lateral.wrapper is not None:
        total += 2 + len(lateral.sources) + 1 + len(lateral.ordinal.keys)
    return total
