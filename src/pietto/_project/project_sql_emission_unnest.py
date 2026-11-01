"""Unnest read SQL construction: one ``JOIN LATERAL ROWS FROM`` right input.

An Unnest is the right input of one CROSS, INNER or LEFT JOIN whose left input
carries the nested field as one Collect group (``pg_column_arrays_v1``): the
count column, then one typed array per child field, in child order. Its rows
are the child rows of the left row, restored by one single-argument call per
array, all zipped by position in one ``ROWS FROM``::

    <KIND> JOIN LATERAL ROWS FROM (pg_catalog.unnest("m<a>"."c<i>_0"), ...)
        AS "m<b>" ("c0", ...) [ON ...]

The arrays of one group always have one length, so the zip never pads. A NULL
array (an empty or missing set) yields no row. There is no ordinality and no
count read: an Unnest has no order and no key. Each element column keeps its
child terminal's realization; the JOIN decides its output nullability.

From the Unnest JOIN on, every nested port is withheld: it keeps its port
position in the JOIN body but has no SELECT item and no CTE header column.

This module owns the Unnest-specific construction only. The renderer turns the
returned nodes into bytes and the independent verifier re-derives them.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from pietto._project import project_sql_emission_nested as nested
from pietto._project import project_sql_emission_results as resulting
from pietto._project import project_sql_emission_rows as rows
from pietto.ast_nodes import AuthoredJoinKind

__all__: tuple[str, ...] = ()

FUNCTION = "pg_catalog.unnest"
"""Schema-qualified, one argument per call: never the bare multi-argument form."""
KINDS = frozenset(
    {AuthoredJoinKind.CROSS, AuthoredJoinKind.INNER, AuthoredJoinKind.LEFT}
)


@dataclass(frozen=True, slots=True, eq=False)
class NestedRead:
    """One JOIN left input entry at a nested port: a Collect group, never a value.

    ``group`` is the left producer's Collect or result group column there;
    ``count`` names its count column and ``arrays`` its array columns in child
    order; ``children`` are the child terminal realizations in child order. It
    has no scalar realization, so any scalar reader of it fails closed.
    """

    position: int
    port: Any
    scope: Any
    group: Any
    count: str
    arrays: tuple[str, ...]
    children: tuple[rows.Realization, ...]


@dataclass(frozen=True, slots=True, eq=False)
class UnnestColumn:
    """One element column of an Unnest, shaped like a named producer column."""

    position: int
    column: rows.StageColumn


@dataclass(frozen=True, slots=True, eq=False)
class UnnestRows:
    """The producer of one Unnest JOIN right input; never a CTE.

    ``unnest`` is the plan's Unnest record, ``scope`` the left input's alias,
    ``arrays`` the left group's array columns in child order and ``columns``
    one element column per child.
    """

    unnest: Any
    scope: Any
    arrays: tuple[str, ...]
    columns: tuple[UnnestColumn, ...]


@dataclass(frozen=True, slots=True, eq=False)
class WithheldPort:
    """A JOIN body output port with no physical column: a nested port from the
    Unnest JOIN on. It keeps its port position; no label is allocated."""

    position: int
    port: Any


def nested_read(column, *, position, port, scope):
    """The left input entry of the nested port ``port`` at ``position``.

    ``column`` is the left producer's column there; ``scope`` the left alias.
    Returns ``(NestedRead, None)`` or ``(None, problem)``.
    """
    group = column
    if type(group) is resulting.ResultGroupColumn:
        group = group.group
    if type(group) is not nested.CollectColumn:
        return None, ("PIE-B1001", "nested_read_without_group", port.ref, None)
    children = tuple(
        item.column.realization for item in group.lateral.target.producer.columns
    )
    return (
        NestedRead(
            position,
            port,
            scope,
            column,
            column.carriers[0][1],
            tuple(label for _, label, _ in column.carriers[1:]),
            children,
        ),
        None,
    )


def realize_unnest(unnest, left, *, kind, terminals):
    """Realize one Unnest JOIN right input over its realized left input.

    ``terminals`` are the Unnest definition's export ports, one per child, in
    child order. Returns ``(UnnestRows, None)`` or ``(None, problem)``.
    """

    def problem(detail):
        return None, ("PIE-B1001", detail, unnest.ref, None)

    if kind not in KINDS:
        return problem("unnest_join_kind_drift")
    at = tuple(i for i, port in enumerate(left.ports) if port is unnest.source)
    if len(at) != 1:
        return problem("unnest_source_not_in_left_input")
    read = left.columns[at[0]]
    if type(read) is not NestedRead:
        return problem("unnest_source_not_nested")
    group = read.group
    if type(group) is resulting.ResultGroupColumn:
        group = group.group
    if (
        type(group) is not nested.CollectColumn
        or group.collect.ref is not unnest.collect
    ):
        return problem("unnest_collect_drift")
    width = len(read.arrays)
    if not width or not (
        width == len(unnest.outputs) == len(terminals) == len(read.children)
    ):
        return problem("unnest_children_drift")
    children = tuple(column.column for column in group.lateral.target.producer.columns)
    return (
        UnnestRows(
            unnest,
            left.symbol,
            read.arrays,
            tuple(
                UnnestColumn(
                    j,
                    replace(
                        child, position=j, name=f"c{j}", terminal=terminal, scope=None
                    ),
                )
                for j, (terminal, child) in enumerate(
                    zip(terminals, children, strict=True)
                )
            ),
        ),
        None,
    )


def node_count(item: UnnestRows) -> int:
    """``ROWS FROM``'s open and close, its alias and its column list (4), then
    per child the call, its scope, its array and its column alias (4 each)."""
    return 4 + 4 * len(item.arrays)
