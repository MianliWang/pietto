"""MC G8: the MySQL chains of levels whose every `sum` is S02's guarded SUM.

MySQL emits each `sum` of an `Int` of a statement whose definitions form a
chain of levels as S02's guarded SUM (the G8 list's Law): the selected
definition reads by FROM one definition, which reads one in turn, down to a
source or to the per-order level over the style page's two sources; three
levels or more over a source, two or more over the per-order level, and a `sum`
in one level at least. Each level is a plain level (reads of the level below, a
WHERE at most), an aggregate level in S02's cell as MC G1 and G2 widen it (a
key and a `sum` in each one below the top), or, as the bottom only, the
per-order level, whose level above is T1's second level, names aside. Each
column is read by the kinds the law admits (a `min` or `max` is the argument of
an aggregate only as a BIGINT field's: one of a SMALLINT or INT is the
`my_signed_int` of MySQL's SIGNED cast, and no aggregate reads it or one of any
other field; a `count` or `min` of a SMALLINT field is S02's own cell's alone,
lead ruling of 2026-11-21), every sum below the top feeds a `sum` above it or
the result, and no level above the lowest one with a `sum` has a WHERE, so
every sum of every level is computed and an overflow anywhere fails the
statement. Each reader
reduces its own input to levels and asks `chain`: emission the plan and the
bound contract, compiled replay its records, the pure boundary its document.
This module imports nothing of the compiler.

A chain is a tuple of levels, bottom first, the selected definition last.
A level is ``(join, where, lets, keys, items)``: ``join`` is None or, at
the per-order bottom, ``(kind, left, right, from_fields, joined_fields)``
as in sum_forms; ``where`` whether it has a WHERE; ``lets`` the column each
of its value `let`s reads; ``keys`` its GROUP BY key columns, and ``items``
its SELECT items in order. A column is ``("A", ordinal, carrier)`` or
``("B", ordinal, carrier)``, a field of the bottom's FROM or joined source
(carrier as sum_forms.carrier), ``("U", index)``, the item ``index`` of the
level below, or ``("L", index)``, this level's `let` ``index``. An item is
``(function, column)``: "read" a read of the column (in an aggregate level,
of a key), or "sum", "count", "count_distinct", "min", "max" or "avg" of
it, the column None for `count()`. Each reader checks what it alone sees:
that each `let` is a value `let` read only as the whole argument of a
`sum`, and that each aggregate is the whole value of its SELECT item.
"""

from __future__ import annotations

import json
from typing import Any

from pietto._project.project_sql_emission_sum_forms import NARROW, WIDE

__all__: tuple[str, ...] = ()

# The style page's `Order` and `Item` with T1's carriers, field by field.
ORDER = (WIDE, NARROW, WIDE)
ITEM = (WIDE, WIDE)
# The per-order JOIN: `left join i on i.order_id == O.id`.
PER_ORDER_JOIN = ("left", ("B", 1, WIDE), ("A", 0, WIDE), ORDER, ITEM)
_PER_ORDER_KEYS = (("A", 0, WIDE), ("A", 1, NARROW), ("A", 2, WIDE))
# MC G1: a summed field's storages; MC G2: a key's, and the field storages
# each other aggregate may read (None: any field).
_SUMMED = frozenset({"my_bigint", "my_int"})
_KEYS = frozenset({"my_bigint", "my_int", "my_varchar"})
_READS = {
    "count": None,
    "count_distinct": _KEYS,
    "min": None,
    "max": _SUMMED,
    "avg": _SUMMED,
}


def _storage(carrier) -> str | None:
    try:
        return json.loads(carrier)["storage"]["kind"]
    except (KeyError, TypeError, ValueError):
        return None


def _extreme(carrier):
    """A `min` or `max`'s carrier: its argument's, but the `my_signed_int`
    of MySQL's SIGNED cast of one of a SMALLINT or INT (MC G4, item 5), at
    every level above it, which no aggregate reads."""

    if _storage(carrier) not in ("my_smallint", "my_int"):
        return carrier
    value = json.loads(carrier)
    value["storage"] = {"kind": "my_signed_int"}
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _aggregate(level) -> bool:
    """An aggregate level: a key or an aggregate item."""

    return bool(level[3]) or any(item[0] != "read" for item in level[4])


def _shaped(level: Any) -> bool:
    """A level's tuple shape (the module docstring)."""

    return (
        type(level) is tuple
        and len(level) == 5
        and type(level[1]) is bool
        and all(type(part) is tuple for part in level[2:])
        and all(type(item) is tuple and len(item) == 2 for item in level[4])
    )


def chain(levels: Any) -> bool:
    """Whether ``levels`` is a G8 chain (the module docstring)."""

    if (
        type(levels) is not tuple
        or not levels
        or not all(_shaped(level) for level in levels)
    ):
        return False
    route = levels[0][0] is not None
    if len(levels) < (2 if route else 3):
        return False
    kinds: list[list] = []
    sums: list[int] = []
    for index, level in enumerate(levels):
        join, where, lets, keys, items = level
        below = kinds[-1] if kinds else []

        def kind(column, index=index, below=below):
            """A column's kind: ("field", carrier), ("extreme", carrier) (a
            min or max, its carrier as _extreme gives it), ("sum",),
            ("count",) or ("avg",); None for a column this level cannot
            read."""
            if type(column) is not tuple or not column:
                return None
            if column[0] in ("A", "B") and index == 0 and len(column) == 3:
                return ("field", column[2]) if route or column[0] == "A" else None
            if (
                column[0] == "U"
                and len(column) == 2
                and type(column[1]) is int
                and 0 <= column[1] < len(below)
            ):
                return below[column[1]]
            return None

        if index and join is not None:
            return False
        # Over the per-order bottom, L2 is T1's second level, whatever kind.
        if route and index == 1 and not _second_level(levels[0][4], level):
            return False
        if route and index == 0:
            current = _per_order(level)
        elif not _aggregate(level):
            current = [kind(column) for _, column in items]
            if lets or not items:
                return False
        else:
            current = _aggregate_level(level, kind)
            if (
                current is not None
                and index + 1 < len(levels)
                and not (keys and any(item[0] == "sum" for item in items))
            ):
                return False
        if current is None or None in current:
            return False
        if any(item[0] == "sum" for item in items):
            sums.append(index)
        # Law item 4 (b): no WHERE above the lowest level with a sum.
        if where and sums and index > sums[0]:
            return False
        kinds.append(current)
    # Law item 4 (a): every sum below the top feeds a sum or the result.
    return bool(sums) and all(
        value != ("sum",) or _consumed(levels, index, position)
        for index in range(len(levels) - 1)
        for position, value in enumerate(kinds[index])
    )


def _per_order(level):
    """The kinds of T1's per_order, names aside, or None."""

    join, where, lets, keys, items = level
    if (
        join != PER_ORDER_JOIN
        or where
        or lets
        or keys != _PER_ORDER_KEYS
        or len(items) != 4
        or set(items) != {*(("read", key) for key in keys), ("count", ("B", 0, WIDE))}
    ):
        return None
    return [
        ("count",) if function == "count" else ("field", column[2])
        for function, column in items
    ]


def _second_level(per_order, level) -> bool:
    """T1's second level over ``per_order``'s items, names aside: grouped by
    the customer column, selecting it, `sum(amount)` and `sum(lines)`, each
    at most once, one sum at least, with no WHERE."""

    _, where, lets, keys, items = level
    customer = ("U", per_order.index(("read", _PER_ORDER_KEYS[1])))
    amount = ("U", per_order.index(("read", _PER_ORDER_KEYS[2])))
    lines = ("U", per_order.index(("count", ("B", 0, WIDE))))
    return (
        not where
        and not lets
        and keys == (customer,)
        and len(set(items)) == len(items)
        and set(items) <= {("read", customer), ("sum", amount), ("sum", lines)}
    )


def _summable(value) -> bool:
    """A `sum` argument: a field of MC G1's storages, a sum or a count."""

    return (
        value in (("sum",), ("count",))
        or value is not None
        and value[0] == "field"
        and _storage(value[1]) in _SUMMED
    )


def _aggregate_level(level, kind):
    """The kinds of an aggregate level's items, or None when it reads a
    column outside the law (item 3) or a `let` outside a `sum`."""

    _, _, lets, keys, items = level
    if any(not _summable(kind(column)) for column in lets) or any(
        (value := kind(key)) is None
        or value[0] != "field"
        or _storage(value[1]) not in _KEYS
        for key in keys
    ):
        return None
    current: list = []
    read: set = set()
    for function, column in items:
        if function == "read":
            current.append(kind(column) if column in keys else None)
        elif type(column) is tuple and column[:1] == ("L",):
            if (
                function != "sum"
                or len(column) != 2
                or type(column[1]) is not int
                or not 0 <= column[1] < len(lets)
            ):
                return None
            read.add(column[1])
            current.append(("sum",))
        elif function == "sum":
            current.append(("sum",) if _summable(kind(column)) else None)
        elif function == "count" and column is None:
            current.append(("count",))
        elif function in _READS:
            value = kind(column)
            storages = _READS[function]
            current.append(
                None
                if value is None
                or value[0]
                not in (
                    ("field", "extreme")
                    if function in ("min", "max", "avg")
                    else ("field",)
                )
                or storages is not None
                and _storage(value[1]) not in storages
                # MC G1-G3 (lead ruling of 2026-11-21, S02-SMALLINT): a
                # `count` or `min` of a SMALLINT field is S02's own cell's
                # alone, which no level of a chain is.
                or function in ("count", "min")
                and value[0] == "field"
                and _storage(value[1]) == "my_smallint"
                # Law item 3: an extreme is the argument of `min`, `max` or
                # `avg` only as a BIGINT field's; a SMALLINT or INT field's
                # (its cast, _extreme), a Float's, a Timestamp's or any other
                # field's is read by no aggregate, `min` included.
                or value[0] == "extreme"
                and _storage(value[1]) != "my_bigint"
                else ("count",)
                if function in ("count", "count_distinct")
                else ("avg",)
                if function == "avg"
                else ("extreme", _extreme(value[1]))
            )
        else:
            return None
    return current if read == set(range(len(lets))) else None


def _consumed(levels, index, position) -> bool:
    """Whether item ``position`` of level ``index`` reaches, through plain
    levels, a `sum` argument of the next aggregate level (directly or through
    a `let`), or the result."""

    column = ("U", position)
    _, _, lets, _, items = above = levels[index + 1]
    if _aggregate(above):
        return any(
            function == "sum"
            and (
                read == column
                or type(read) is tuple
                and read[:1] == ("L",)
                and lets[read[1]] == column
            )
            for function, read in items
        )
    if index + 2 == len(levels):
        return any(read == column for _, read in items)
    return any(
        read == column and _consumed(levels, index + 1, out)
        for out, (_, read) in enumerate(items)
    )
