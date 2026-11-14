"""Phase77 S03: the MySQL sum forms the native qualification paired.

MySQL emits a conditional sum, a sum over one JOIN or the two-level route's
sums, each as S02's guarded SUM, only in a statement that is, names aside, one
of the nine forms the S03 qualification ran on PostgreSQL and MySQL (C1-C4,
J1-J3, T1, T2), the selected definition's SELECT items a subset of its
form's with one sum at least and T1's or T2's upstream exactly its form's
(D77.24). Each reader reduces its own input to levels and
asks `paired`: emission the authored definitions and the bound contract,
compiled replay its records, the pure boundary its document. This module
imports nothing of the compiler.

A level is ``(join, keys, items)``, upstream first. ``join`` is None or
``(kind, left, right, from_fields, joined_fields)``: the operands of its ON
equality as written, then the carriers of every field of the FROM and the
joined source in order, which the JOIN's row body carries whole. A column
is ``(side, field, carrier)``: side "A" reads the FROM input, "B" the joined
one, "U" the upstream definition, whose ``field`` is the upstream item and
carrier None; ``field`` is otherwise any token the reader keeps per field and
``carrier`` the field's canonical contract representation. An item is
``("key", column)``, ``("sum", column)``, ``("count", column)`` or
``("fsum", column, test)``; a test is ``("is", F)``, ``("not", F)``,
``("none", F)`` or ``(">", I, L)``, L an int.
"""

from __future__ import annotations

import json

__all__: tuple[str, ...] = ()


def carrier(representation) -> str | None:
    """A contract representation, canonical, or None for any other value."""

    try:
        value = json.loads(representation)
    except (TypeError, ValueError):
        return None
    if type(value) is not dict or set(value) != {"domain", "nullable", "storage"}:
        return None
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _carrier(storage: str, nullable: bool, domain: dict) -> str:
    return json.dumps(
        {"domain": domain, "nullable": nullable, "storage": {"kind": storage}},
        sort_keys=True,
        separators=(",", ":"),
    )


# The qualification's carriers: BIGINT and INT over their whole ranges and a
# 0/1 TINYINT Bool.
_BIGINT = {"kind": "int_range", "max": str((1 << 63) - 1), "min": str(-(1 << 63))}
WIDE = _carrier("my_bigint", False, _BIGINT)
WIDE_NULL = _carrier("my_bigint", True, _BIGINT)
NARROW = _carrier(
    "my_int", False, {"kind": "int_range", "max": "2147483647", "min": "-2147483648"}
)
FLAG = _carrier("my_bool01", True, {"kind": "bool01"})
# The qualification's two tables, field by field: a JOIN form's sources are
# exactly these, since its SQL carries every field of both.
ORDERS = (WIDE, NARROW, WIDE_NULL, WIDE, FLAG)
ITEMS = (WIDE, WIDE, WIDE_NULL)


def _left(join) -> bool:
    """J2's LEFT JOIN of orders and items, ON B.R == A.K over non-null
    BIGINT fields."""

    return (
        join is not None
        and join[0] == "left"
        and join[3:] == (ORDERS, ITEMS)
        and join[1][0] == "B"
        and join[1][2] == WIDE
        and join[2][0] == "A"
        and join[2][2] == WIDE
    )


def _single(level, preserve: bool) -> bool:
    """C1-C4 and J1-J3: one level over sources whose items are reads of its
    keys and its sums, each once, one sum at least, every sum of one field."""

    join, keys, items = level
    sums = [item for item in items if item[0] in ("sum", "fsum")]
    if (
        not sums
        or len(set(items)) != len(items)
        or any(
            item[0] not in ("sum", "fsum") and (item[0] != "key" or item[1] not in keys)
            for item in items
        )
        or len({item[1] for item in sums}) != 1
    ):
        return False
    x = sums[0][1]
    if join is None:
        if any(item[0] != "fsum" for item in sums) or x[0] != "A":
            return False
        tests = [item[2] for item in sums]
        flag = tests[0][1]
        if keys:
            # C1 (x nullable) and C4 (x non-null): one INT key, `if F`.
            return (
                len(keys) == 1
                and keys[0][0] == "A"
                and keys[0][2] == NARROW
                and len(sums) == 1
                and tests[0][0] == "is"
                and flag[0] == "A"
                and flag[2] == FLAG
                and x[2] in (WIDE_NULL, WIDE)
            )
        if all(test[0] in ("not", "none") for test in tests):
            # C2: `if not F` and `if F is None`, over one x and one F.
            return (
                x[2] == WIDE_NULL
                and len({test[0] for test in tests}) == len(tests)
                and len({test[1] for test in tests}) == 1
                and flag[0] == "A"
                and flag[2] == FLAG
            )
        # C3: `if I > L`, L a non-negative Int literal, only preserved.
        return (
            preserve
            and len(tests) == 1
            and tests[0][0] == ">"
            and flag[0] == "A"
            and flag[2] == WIDE
            and type(tests[0][2]) is int
            and tests[0][2] >= 0
            and x[2] == WIDE_NULL
        )
    if len(sums) != 1 or sums[0][0] != "sum" or x[2] != WIDE_NULL:
        return False
    if join[0] == "inner":
        # J1: ON B.K == A.R over non-null BIGINT fields, one INT key of B,
        # the sum of an A field.
        return (
            join[3:] == (ITEMS, ORDERS)
            and join[1][0] == "B"
            and join[1][2] == WIDE
            and join[2][0] == "A"
            and join[2][2] == WIDE
            and len(keys) == 1
            and keys[0][0] == "B"
            and keys[0][2] == NARROW
            and x[0] == "A"
        )
    # J2 and J3: keys A.K and, for J3, an INT field of A; the sum of a B field.
    return (
        _left(join)
        and keys[:1] == (join[2],)
        and (
            len(keys) == 1
            or len(keys) == 2
            and keys[1][0] == "A"
            and keys[1][2] == NARROW
        )
        and x[0] == "B"
    )


def paired(levels, preserve: bool) -> bool:
    """Whether S03 levels are one of the nine paired forms, names aside;
    ``preserve`` is the literal policy's (C3 is paired only preserved)."""

    if type(levels) is not tuple:
        return False
    if len(levels) == 1:
        return _single(levels[0], preserve)
    if len(levels) != 2:
        return False
    (join, keys, items), (top_join, top_keys, top_items) = levels
    counts = [item for item in items if item[0] == "count"]
    if len(counts) == 1:
        # T1's per_order: J2's JOIN, keys A.K, an INT and a nullable BIGINT
        # field of A, those keys and the count of another non-null BIGINT
        # field of B.
        count = counts[0]
        if not (
            _left(join)
            and len(keys) == 3
            and keys[0] == join[2]
            and keys[1][0] == "A"
            and keys[1][2] == NARROW
            and keys[2][0] == "A"
            and keys[2][2] == WIDE_NULL
            and len(items) == 4
            and set(items) == {*(("key", key) for key in keys), count}
            and count[1][0] == "B"
            and count[1][2] == WIDE
            and count[1][1] != join[1][1]
        ):
            return False
        summed = {("key", keys[2]), count}
    elif len(keys) == 2 and len(items) == 3 and _single((join, keys, items), True):
        # T2's per_order: exactly J3.
        summed = {item for item in items if item[0] == "sum"}
    else:
        return False
    key = ("U", ("key", keys[1]), None)
    return (
        top_join is None
        and top_keys == (key,)
        and len(set(top_items)) == len(top_items)
        and any(item[0] == "sum" for item in top_items)
        and all(
            item == ("key", key)
            or item[0] == "sum"
            and item[1][0] == "U"
            and item[1][1] in summed
            for item in top_items
        )
    )
