"""Phase77 S03: the MySQL sum forms the native qualification paired.

MySQL emits a conditional sum, a sum over one JOIN or the two-level route's
sums, each as S02's guarded SUM, only in a statement that is, names aside, one
of the nine forms the S03 qualification ran on PostgreSQL and MySQL (C1-C4,
J1-J3, T1, T2), the selected definition's SELECT items a subset of its
form's with one sum at least and T1's or T2's upstream exactly its form's
(D77.24), or one of S03's neighbours that MC's list `s03n` opens (_neighbour:
its Law C and Law T). Each reader reduces its own input to levels and
asks `paired`: emission the authored definitions and the bound contract,
compiled replay its records, the pure boundary its document. This module
imports nothing of the compiler.

A level is ``(join, keys, items)``, lowest first. ``join`` is None or
``(kind, left, right, from_fields, joined_fields, from_tokens)``: the
operands of its ON equality as written, the carriers of every field of the
FROM and the joined source in order, which the JOIN's row body carries
whole, and the tokens of the FROM source's fields in order. ``keys``
is the tuple of its GROUP BY key columns, or None for a plain level, which
aggregates nothing. A column is ``(side, field, carrier)``: side "A" reads
the FROM input, "B" the joined one, "U" the level below, whose ``field`` is
that level's item and carrier None; ``field`` is otherwise any token the
reader keeps per field and ``carrier`` the field's canonical contract
representation. An item is ``("read", column)`` of a plain level, or
``("key", column)``, ``("sum", column)``, ``("count", column)``, ``("count",
None)`` (`count()`) or ``("fsum", column, test)``; a test is ``("is", F)``,
``("not", F)``, ``("none", F)``, ``(">", I, L)``, L an int, or ``("and", T,
U)`` and ``("or", T, U)`` of two tests as written. ``clauses`` holds the
selected definition's ORDER BY keys, each ``("order", item, direction)``,
its HAVING lines, each ``(">=", item, L)`` or another comparison, the item
the one of its level that the key or line reads by name, and its WHERE,
``("where", test)``, the test over the columns of its level's input as a
conditional sum's test is written; ``organized`` is "alias" for a relation
alias that FROM reads and "import" for a source imported under its own name,
which only emission sees (D77.24).
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
# MC s03n's T-4: `orders` with one more nullable BIGINT field after `flag`.
WIDER = (*ORDERS, WIDE_NULL)


def _left(join, orders=ORDERS) -> bool:
    """J2's LEFT JOIN of orders and items, ON B.R == A.K over non-null
    BIGINT fields; ``orders`` the FROM source's carriers (MC s03n's T-4
    takes WIDER for T1)."""

    return (
        join is not None
        and len(join) == 6
        and join[0] == "left"
        and join[3:5] == (orders, ITEMS)
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
            join[3:5] == (ITEMS, ORDERS)
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


def paired(levels, preserve: bool, clauses=(), organized=None) -> bool:
    """Whether S03 levels are one of the nine paired forms, names aside, or
    one of the `s03n` neighbours (_neighbour); ``preserve`` is the literal
    policy's (C3 is paired only preserved)."""

    if (
        type(levels) is not tuple
        or not levels
        or type(clauses) is not tuple
        or not all(_shaped(level) for level in levels)
    ):
        return False
    return (
        not clauses and organized is None and _form(levels, preserve)
    ) or _neighbour(levels, clauses, organized)


def _shaped(level) -> bool:
    """A level's tuple shape (the module docstring)."""

    return (
        type(level) is tuple
        and len(level) == 3
        and (level[1] is None or type(level[1]) is tuple)
        and type(level[2]) is tuple
        and all(type(item) is tuple and len(item) in (2, 3) for item in level[2])
    )


def _form(levels, preserve: bool) -> bool:
    """One of the nine paired forms: aggregate levels whose every item reads
    a column."""

    if any(
        level[1] is None or any(item[1] is None for item in level[2])
        for level in levels
    ):
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


# MC s03n, Law C: the four bases (C1 and the three of G7's cell that G7's R3
# and R6 to R8 build on), by their conditional sum's test, and the bases each
# item takes: ORDER BY of the key, a relation alias, an imported source, a
# plain upstream and the HAVING line `paid >= 0`.
_BASES = {
    "order": frozenset({"C1", "G7T1"}),
    "alias": frozenset({"C1", "R6"}),
    "import": frozenset({"C1", "G7T1"}),
    "upstream": frozenset({"C1", "R7"}),
    "having": frozenset({"C1"}),
}


def _neighbour(levels, clauses, organized) -> bool:
    """MC s03n: Law C, one of four bases with exactly one of ORDER BY of the
    key ascending, a relation alias, an imported source, a plain upstream
    and the HAVING line `paid >= 0`, each over the bases it names
    (_BASES); or Law T, a chain over S03's T1 or T2 per-order bottom with
    exactly one of T-1 (T1's second level with `where C > 0`, C the
    bottom's count column), T-2 (the bottom without `id`), T-3 (T2's with
    an unread `count()`), T-4 (T1's over an `orders` with one more nullable
    BIGINT field, which no level reads) and T-5 and T-6 (T2 and T1 under a
    scalar third level of sums). Every other statement, two of these items
    among them, is no neighbour."""

    if len(levels) == 1:
        level = levels[0]
        base = _base(level, _direct)
        if base is None:
            return False
        if organized is not None:
            return not clauses and base in _BASES.get(organized, ())
        key = ("key", level[1][0])
        (summed,) = (item for item in level[2] if item[0] == "fsum")
        return (clauses == (("order", key, "asc"),) and base in _BASES["order"]) or (
            clauses == ((">=", summed, 0),) and base in _BASES["having"]
        )
    if organized is not None:
        return False
    if len(levels) == 2 and levels[0][1] is None:
        upstream, top = levels
        return (
            not clauses
            and _plain(upstream)
            and _base(top, _through) in _BASES["upstream"]
        )
    return _chain(levels, clauses)


def _direct(column):
    """The carrier of a column of the FROM source."""

    return column[2] if type(column) is tuple and column[:1] == ("A",) else None


def _through(column):
    """The carrier of a column of a plain upstream, its item's field's."""

    if type(column) is not tuple or len(column) != 3 or column[0] != "U":
        return None
    item = column[1]
    return _direct(item[1]) if type(item) is tuple and item[:1] == ("read",) else None


def _base(level, carrier):
    """Law C's base that ``level`` is, names and item order aside: grouped
    by one INT key, selecting it and one conditional sum of a nullable
    BIGINT field whose test is C1's `if F` ("C1"), G7's T1's `if F and I >
    3` ("G7T1"), G7's R6's `if F or I > 3` ("R6") or G7's R7's `if not F`
    ("R7"), F a read of a nullable Bool field and I one of a non-null BIGINT
    field, the literal 3 as written; None for any other level."""

    join, keys, items = level
    if join is not None or keys is None or len(keys) != 1 or len(items) != 2:
        return None
    sums = [item for item in items if item[0] == "fsum" and len(item) == 3]
    if (
        len(sums) != 1
        or ("key", keys[0]) not in items
        or carrier(keys[0]) != NARROW
        or carrier(sums[0][1]) != WIDE_NULL
    ):
        return None
    test = sums[0][2]

    def flag(read):
        return (
            type(read) is tuple
            and len(read) == 2
            and read[0] == "is"
            and (carrier(read[1]) == FLAG)
        )

    if type(test) is not tuple:
        return None
    if flag(test):
        return "C1"
    if len(test) == 2 and test[0] == "not" and flag(("is", test[1])):
        return "R7"
    if len(test) != 3:
        return None
    above = test[2]
    if test[0] not in ("and", "or") or not (
        flag(test[1])
        and type(above) is tuple
        and len(above) == 3
        and above[0] == ">"
        and carrier(above[1]) == WIDE
        and type(above[2]) is int
        and above[2] == 3
    ):
        return None
    return "G7T1" if test[0] == "and" else "R6"


def _plain(level) -> bool:
    """Law C's plain upstream (its item C-3): a plain level of three reads
    of fields of the FROM source, an INT, a nullable BIGINT and a nullable
    Bool one, in any order."""

    join, keys, items = level
    return (
        join is None
        and keys is None
        and len(items) == 3
        and all(item[0] == "read" for item in items)
        and sorted(str(_direct(item[1])) for item in items)
        == sorted((NARROW, WIDE_NULL, FLAG))
    )


def _chain(levels, clauses) -> bool:
    """Law T: S03's T1 or T2 over its per-order bottom with one of T-1 to
    T-6 (_neighbour), names and item order aside; each level as S03's T1 or
    T2 writes it but for that item, and no clause but T-1's WHERE."""

    if len(levels) not in (2, 3) or any(level[1] is None for level in levels):
        return False
    join, keys, items = levels[0]
    if (
        not (_left(join) or _left(join, WIDER))
        or len(keys) not in (2, 3)
        or len(set(items)) != len(items)
        or keys[0] != join[2]
        or keys[1][0] != "A"
        or keys[1][2] != NARROW
    ):
        return False
    customer = ("key", keys[1])
    found = set(items)
    if len(keys) == 3:
        # T1's per_order: keys A.K, an INT field of A and A's third field,
        # a nullable BIGINT, which the second level sums, selecting those
        # keys, A.K but under T-2, and the count of another non-null BIGINT
        # field of B; T-4 over WIDER, whose last field no level reads.
        amount = ("key", keys[2])
        count = next((item for item in items if item[0] == "count"), None)
        if (
            keys[2][:2] != ("A", join[5][2])
            or keys[2][2] != WIDE_NULL
            or count is None
            or count[1] is None
            or count[1][0] != "B"
            or count[1][2] != WIDE
            or count[1][1] == join[1][1]
        ):
            return False
        sums = (amount, count)
        variant = (
            "T-2"
            if found == {customer, amount, count}
            else "T1"
            if found == {("key", keys[0]), customer, amount, count}
            else None
        )
        if join[3] == WIDER:
            variant = "T-4" if variant == "T1" else None
        where = ("where", (">", ("U", count, None), 0))
        allowed = {(2, "T-1"), (2, "T-2"), (2, "T-4"), (3, "T1")}
    else:
        # T2's per_order, J3: keys A.K and the INT field, selecting them, A.K
        # but under T-2, beside `count()` under T-3, and the sum of a nullable
        # BIGINT field of B.
        summed = next((item for item in items if item[0] == "sum"), None)
        if (
            join[3] != ORDERS
            or summed is None
            or summed[1][0] != "B"
            or summed[1][2] != WIDE_NULL
        ):
            return False
        sums = (summed,)
        whole = {("key", keys[0]), customer, summed}
        variant = (
            "T-2"
            if found == {customer, summed}
            else "T-3"
            if found == {*whole, ("count", None)}
            else "T2"
            if found == whole
            else None
        )
        where = None
        allowed = {(2, "T-2"), (2, "T-3"), (3, "T2")}
    if clauses:
        # T-1: T1 with `where C > 0` in its second level, C the bottom's
        # count column and the literal 0 as written, the WHERE's one test.
        variant = (
            "T-1"
            if variant == "T1" and clauses == (where,) and type(clauses[0][1][2]) is int
            else None
        )
    if (len(levels), variant) not in allowed:
        return False
    # The second level, T1's or T2's: grouped by the customer column and
    # selecting it and the sum of each of ``sums``, each once.
    join, keys, items = levels[1]
    key = ("U", customer, None)
    second = {("key", key), *(("sum", ("U", item, None)) for item in sums)}
    if (
        join is not None
        or keys != (key,)
        or len(items) != len(set(items))
        or set(items) != second
    ):
        return False
    if len(levels) == 2:
        return True
    # T-5 and T-6: a scalar third level selecting the sum of each sum of the
    # second level, each once.
    join, keys, items = levels[2]
    third = {("sum", ("U", item, None)) for item in second if item[0] == "sum"}
    return (
        join is None
        and keys == ()
        and len(items) == len(set(items))
        and set(items) == third
    )
