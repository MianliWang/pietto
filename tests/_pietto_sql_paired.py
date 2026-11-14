"""The Phase77 Wave A qualification pack's paired forms, copied verbatim.

PAIRS.md 5.1, 5.2, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9 and 5.10 give the paired
bodies (`{name}` is the selected definition's name), 4.1, 4.2, 4.3, 4.5,
4.6, 4.8, 4.9, 4.10 and 4.11 the MySQL worlds `agg_keys`, `dec`,
`rows_ntext`, `temporal`, `agg`, `join`, `rows`, `dec_ratio` and `dec_wide`
they read, and the pack's `mysql/plan.py` the MySQL contract its
`compile_sql` runs with. `FORMS` is in the order of
`project_sql_emission_paired.FORMS`: S16 P-S16-1..3, S10 bodies A (P-S10-1,
5), B (P-S10-2) and C (P-S10-3, 4), S08 P-S08-1..7 and P-S08T-1..4, S11
P-S11-1..8 and bodies D (P-S11B-1, 4), E (P-S11B-2) and F (P-S11B-3), S14
P-S14-1..4, then S17 bodies G to J (P-DEC-1..3, 4..6, 7..9 and 10..12, each
run with three arguments) and P-DECB-1..10. `project` writes one form with
only its names changed.
"""

import json
import re

HEADER = (
    "shape Row:\n"
    "    id: Int\n"
    "    flag: Bool | None\n"
    "    text: Text | None\n"
    "    money: Decimal(9, 2)\n"
    "    ratio: Float\n"
    'source rows: Row = mysql.table("opaque.locator.not.sql")\n'
)
TEMPORAL_HEADER = (
    "shape Row:\n"
    "    id: Int\n"
    "    g: Int | None\n"
    "    tier: Int\n"
    "    ts: Timestamp\n"
    "    ts2: Timestamp | None\n"
    "    d: Date\n"
    "    d2: Date | None\n"
    "    u: UUID\n"
    'source rows: Row = mysql.table("opaque.locator.not.sql")\n'
)
AGG_HEADER = (
    "shape Agg:\n"
    "    key: Int | None\n"
    "    value: Int | None\n"
    "    flag: Bool | None\n"
    "    label: Text\n"
    "    amount: Decimal(9, 2)\n"
    "    ratio: Float\n"
    "    rid: Int\n"
    "    agg_row = unique(rid)\n"
    'source agg: Agg = mysql.table("aggregate.locator.not.sql")\n'
)
KEYS_SOURCE = 'source keys: Agg = mysql.table("keys.locator.not.sql")\n'
# PAIRS.md 4.2, the MySQL pack's `H_ROWS`; 4.10 and 4.11 change one type.
DEC_HEADER = HEADER.replace("    text: Text | None\n", "    text: Text\n")
JOIN_HEADER = (
    "shape Row:\n"
    "    id: Int\n"
    "    key: Int | None\n"
    "    label: Text | None\n"
    "    row_key = unique(id)\n"
    'source lhs: Row = mysql.table("lhs")\n'
    'source rhs: Row = mysql.table("rhs")\n'
    "def band(x: Int) -> Int: return 1 if x <= 3 else 2\n"
)
_TEXT = {
    "collation": "utf8mb4_0900_bin",
    "encoding": "utf8mb4",
    "kind": "text",
    "max_characters": 64,
    "padding": "NO PAD",
}
_INT = {"kind": "int_range", "max": "9007199254740993", "min": "-9007199254740993"}
_AGG_FIELDS = (
    ("key", "group key", "Int", True),
    ("value", "value é", "Int", True),
    ("flag", "flag value", "Bool", True),
    ("label", 'text `"é', "Text", False),
    ("amount", "amount value", "Decimal", False),
    ("ratio", "ratio value", "Float", False),
    ("rid", "row id", "Int", False),
)
# Per logical type: the pack's MySQL storage and domain (mysql/plan.py).
STORAGE = {
    "Int": ({"kind": "my_bigint"}, _INT),
    "Bool": ({"kind": "my_bool01"}, {"kind": "bool01"}),
    "Text": ({"kind": "my_varchar", "length": 64}, _TEXT),
    "Decimal": (
        {"kind": "my_decimal", "precision": 9, "scale": 2},
        {"kind": "decimal", "precision": 9, "scale": 2},
    ),
    "Float": ({"kind": "my_double"}, {"format": "binary64", "kind": "finite_float"}),
    "Timestamp": (
        {"fractional_seconds": 6, "kind": "my_datetime"},
        {"kind": "timestamp"},
    ),
    "Date": ({"kind": "my_date"}, {"kind": "date"}),
    "UUID": ({"kind": "my_uuid_bytes"}, {"encoding": "standard_bytes", "kind": "uuid"}),
}


def storage(logical, precision=9, scale=2):
    """The pack's MySQL (storage, domain) of ``logical``; a Decimal's with its
    precision and scale."""
    if logical != "Decimal":
        return STORAGE[logical]
    return tuple(
        {"kind": kind, "precision": precision, "scale": scale}
        for kind in ("my_decimal", "decimal")
    )


_DEC_FIELDS = (
    ("id", "order.id", "Int", False),
    ("flag", "flag value", "Bool", True),
    ("text", 'text `"é', "Text", False),
    ("money", "amount value", "Decimal", False),
    ("ratio", "ratio value", "Float", False),
)
# Per world: its header, its sources, their (field, pack column, logical type,
# nullable, and a Decimal's precision and scale when not (9, 2)) and the
# pack's namespace and tables. The sources of a world share their shape,
# namespace and columns, as in the pack.
WORLDS = {
    "rows_ntext": (
        HEADER,
        ("rows",),
        (
            ("id", "order.id", "Int", False),
            ("flag", "flag value", "Bool", True),
            ("text", 'text `"é', "Text", True),
            ("money", "amount value", "Decimal", False),
            ("ratio", "ratio value", "Float", False),
        ),
        ("phase66", ("phase66 source é",)),
    ),
    "agg": (AGG_HEADER, ("agg",), _AGG_FIELDS, ("phase66", ("phase66 agg é",))),
    "agg_keys": (
        AGG_HEADER + KEYS_SOURCE,
        ("agg", "keys"),
        _AGG_FIELDS,
        ("phase66", ("phase66 agg é", "phase66 agg keys é")),
    ),
    "dec": (DEC_HEADER, ("rows",), _DEC_FIELDS, ("phase66", ("phase66 source é",))),
    "dec_ratio": (
        DEC_HEADER.replace("    ratio: Float\n", "    ratio: Decimal(8, 3)\n"),
        ("rows",),
        _DEC_FIELDS[:4] + (("ratio", "ratio value", "Decimal", False, 8, 3),),
        ("phase66", ("phase66 source é",)),
    ),
    "dec_wide": (
        DEC_HEADER.replace(
            "    money: Decimal(9, 2)\n", "    money: Decimal(46, 30)\n"
        ),
        ("rows",),
        _DEC_FIELDS[:3]
        + (("money", "amount value", "Decimal", False, 46, 30), _DEC_FIELDS[4]),
        ("phase66", ("phase66 source é",)),
    ),
    "join": (
        JOIN_HEADER,
        ("lhs", "rhs"),
        (
            ("id", "order.id", "Int", False),
            ("key", "key value", "Int", True),
            ("label", "label", "Text", True),
        ),
        ("phase66", ("phase66 lhs é", "phase66 rhs é")),
    ),
    "rows": (
        HEADER.replace("    text: Text | None\n", "    text: Text\n"),
        ("rows",),
        (
            ("id", "order_id", "Int", False),
            ("flag", "flag_value", "Bool", True),
            ("text", "text_value", "Text", False),
            ("money", "amount_value", "Decimal", False),
            ("ratio", "ratio_value", "Float", False),
        ),
        ("phase66", ("phase66 source é",)),
    ),
    "temporal": (
        TEMPORAL_HEADER,
        ("rows",),
        (
            ("id", "row_id", "Int", False),
            ("g", "group_key", "Int", True),
            ("tier", "tier_value", "Int", False),
            ("ts", "ts_value", "Timestamp", False),
            ("ts2", "ts2_value", "Timestamp", True),
            ("d", "d_value", "Date", False),
            ("d2", "d2_value", "Date", True),
            ("u", "uuid_value", "UUID", False),
        ),
        ("phase66", ("phase66 source é",)),
    ),
}
_S10_TESTS = (
    "        n = sum(1 for o in group if o.flag)\n"
    "        a = all(o.flag for o in group)\n"
    '        b = any(o.label == "a" for o in group)\n'
)
_S10_GROUPED = "query {name}:\n    from agg\n    group by:\n        key\n    select:\n"
_S08 = "table {name}:\n    from rows\n    select:\n        id\n"


def _s11_join(join, members, key=None, kind="query"):
    """PAIRS.md 5.1: keys LEFT or INNER joins agg on its unique rid."""
    body = (
        f"{kind} {{name}}:\n    from keys\n    let r = agg\n"
        f"    {join} join r on keys.rid == r.rid\n    let lb = r.label\n"
    )
    if key is not None:
        body += f"    group by:\n        {key}\n    select:\n        k = {key}\n"
    else:
        body += "    select:\n"
    return body + f"        d = count_distinct({members})\n"


# PAIRS.md 5.8: P-S14-1, 2 and 4 read this query beside their own.
_S14_PRED = (
    "query pred:\n    from rhs\n    where band(id) == 2\n"
    "    select:\n        id\n        label\n"
)
_S11_TUPLES = (
    "table {name}:\n    from agg\n    select:\n"
    "        text_flag = count_distinct(label, flag)\n"
    "        int_text = count_distinct(key, label)\n"
    "        all_three = count_distinct(key, flag, label)\n"
)
# Per form: its world and its body.
FORMS = (
    (
        "rows_ntext",
        "query {name}:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        '        previous_empty = lag(text, 1, "") window(order by id)\n'
        '        following_unicode = lead(text, 1, "雪") window(order by id)\n'
        "        following_null = lead(text, 1) window(order by id)\n",
    ),
    (
        "rows_ntext",
        "query {name}:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        '        previous = lag(text, 1, "雪") window(order by id)\n'
        '        following = lead(text, 1, "a\'b") window(order by id)\n',
    ),
    (
        "rows_ntext",
        "query {name}:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "        plain = text\n"
        '        lag_empty = lag(text, 1, "") window(order by id)\n'
        '        lead_snow = lead(text, 1, "雪") window(order by id)\n'
        '        lead_quote = lead(text, 1, "a\'b") window(order by id)\n'
        "        lead_none = lead(text, 1) window(order by id)\n",
    ),
    ("agg", _S10_GROUPED + _S10_TESTS),
    ("agg", _S10_GROUPED + "        k = key\n" + _S10_TESTS),
    ("agg", "query {name}:\n    from agg\n    select:\n" + _S10_TESTS),
    (
        "rows",
        _S08 + "        w = count() window(\n            order by id\n        )\n",
    ),
    (
        "rows",
        _S08 + "        w = min(id) window(\n"
        "            order by id\n"
        "            rows between 1 preceding and current row\n"
        "        )\n",
    ),
    (
        "rows",
        _S08 + "        w = min(id) window(\n"
        "            partition by flag\n"
        "            order by id\n"
        "        )\n",
    ),
    (
        "rows",
        "table {name}:\n"
        "    from rows\n"
        "    let recent = window(partition by flag order by id)\n"
        "    select:\n"
        "        n = count() window recent\n",
    ),
    (
        "rows",
        "table {name}:\n"
        "    from rows\n"
        "    group by:\n"
        "        flag\n"
        "    select:\n"
        "        flag\n"
        "        low = min(id)\n"
        "        high = max(low) window(order by low)\n"
        "        n = count() window(order by low)\n",
    ),
    (
        "rows",
        "table {name}:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "    qualify:\n"
        "        count(id) window(order by id) > 1\n",
    ),
    (
        "rows",
        "query {name}:\n"
        "    from rows\n"
        "    let other = rows\n"
        "    inner join other on rows.id == other.id\n"
        "    select:\n"
        "        id = rows.id\n"
        "        high = max(other.id) window(partition by rows.flag order by rows.id)\n",
    ),
    (
        "temporal",
        "table {name}:\n"
        "    from rows\n"
        "    select:\n"
        "        count_timestamp = count(ts) window(order by id)\n"
        "        count_date = count(d) window(order by id)\n"
        "        count_uuid = count(u) window(order by id)\n"
        "        low_timestamp = min(ts) window(order by id)\n"
        "        high_date = max(d) window(order by id)\n",
    ),
    (
        "temporal",
        _S08 + "        count_ts2 = count(ts2) window(order by id)\n"
        "        count_d2 = count(d2) window(order by id)\n"
        "        high_timestamp = max(ts) window(order by id)\n"
        "        low_date = min(d) window(order by id)\n"
        "        low_ts2 = min(ts2) window(order by id)\n"
        "        high_d2 = max(d2) window(order by id)\n",
    ),
    (
        "temporal",
        _S08 + "        n_ts = count(ts) window(\n"
        "            partition by g\n"
        "            order by id\n"
        "            rows between 1 preceding and current row\n"
        "        )\n"
        "        high_ts = max(ts) window(\n"
        "            partition by g\n"
        "            order by id\n"
        "            rows between 1 preceding and current row\n"
        "        )\n"
        "        high_d2 = max(d2) window(partition by g)\n"
        "        low_d = min(d) window(partition by g)\n"
        "        n_u = count(u) window(partition by g)\n",
    ),
    (
        "temporal",
        _S08 + "        n = count() window(order by tier)\n"
        "        n_u = count(u) window(order by tier)\n"
        "        n_d2 = count(d2) window(order by tier)\n"
        "        low_id = min(id) window(order by tier)\n"
        "        high_ts = max(ts) window(order by tier)\n"
        "        high_d2 = max(d2) window(order by tier)\n",
    ),
    ("agg_keys", _s11_join("left", "keys.label, r.rid, r.label", "keys.rid")),
    ("agg_keys", _s11_join("left", "keys.label, lb, r.rid", "keys.rid")),
    ("agg_keys", _s11_join("inner", "keys.label, r.rid, r.label", "keys.rid")),
    ("agg_keys", _s11_join("inner", "keys.label, lb, r.rid", "keys.rid")),
    ("agg_keys", _s11_join("left", "keys.label, lb", "keys.key")),
    ("agg_keys", _s11_join("inner", "keys.label, lb", "keys.key")),
    ("agg_keys", _s11_join("left", "lb, keys.key", kind="table")),
    (
        "agg_keys",
        _s11_join("left", "keys.label, lb", "keys.key")
        + "        e = count_distinct(r.key, keys.label)\n",
    ),
    ("agg", _S11_TUPLES),
    (
        "agg",
        "table {name}:\n    from agg\n    select:\n"
        "        int_int = count_distinct(key, value)\n",
    ),
    (
        "agg",
        "query {name}:\n    from agg\n    group by:\n        key\n    select:\n"
        "        k = key\n        n = count_distinct(label, flag)\n",
    ),
    (
        "join",
        _S14_PRED + "query {name}:\n    from lhs\n    let r = pred\n"
        "    left join r on lhs.id == r.id\n"
        "    select:\n        a = lhs.id\n        b = r.label\n",
    ),
    (
        "join",
        _S14_PRED + "query {name}:\n    from pred\n    let l = lhs\n"
        "    inner join l on l.id == pred.id\n"
        "    select:\n        a = pred.id\n        b = l.label\n",
    ),
    (
        "join",
        "query {name}:\n    from lhs\n    let r = rhs\n"
        "    left join r on lhs.id == r.id\n    group by lhs.id\n"
        "    select:\n        a = lhs.id\n        n = count(lower(r.label))\n"
        "        d = count_distinct(trim(r.label))\n        l = count(len(r.label))\n"
        "        c = count(lower(trim(r.label)))\n",
    ),
    (
        "join",
        _S14_PRED + "query {name}:\n    from lhs\n    let r = pred\n"
        "    left join r on lhs.id == r.id\n    group by lhs.id\n"
        "    select:\n        a = lhs.id\n        n = count(lower(r.label))\n",
    ),
    *(
        (
            "dec",
            "query {name}(factor: Int):\n    from rows\n    select:\n"
            f"        total = {expression}\n",
        )
        for expression in ("money + factor", "factor - money")
        + ("money * factor", "factor * money")
    ),
    *(
        (world, "table {name}:\n    from rows\n    select:\n" + items)
        for world, items in (
            ("dec", "        added = money + id\n        subtracted = money - id\n"),
            ("dec", "        added = id + money\n        subtracted = id - money\n"),
            ("dec", "        result = money * id\n"),
            ("dec", "        result = id * money\n"),
            ("dec", "        result = money * 2\n"),
            ("dec", "        result = -money\n"),
            ("dec", "        result = +money\n"),
            ("dec", "        result = -(money * id)\n"),
            (
                "dec_ratio",
                "        added = money + ratio\n        subtracted = money - ratio\n",
            ),
            ("dec_wide", "        result = money * id\n"),
        )
    ),
)
S16 = range(3)
S10 = range(3, 6)
S08 = range(6, 17)
S11 = range(17, 28)
S14 = range(28, 32)
S17 = range(32, 46)
# P-S14-4 runs with bind-safe literals; every other form preserves its
# literals. It and the S17 forms with a header parameter run with a
# contract that declares the MySQL parameter protocol.
BIND_SAFE = (31,)
PROTOCOL = (31, 32, 33, 34, 35)


def _over(after, *calls):
    return tuple(
        f"{function}(`s0`.`{{{name}}}`) OVER ({after}" for function, name in calls
    )


_BY_ID, _BY_G = "ORDER BY `s0`.`{id}` ASC", "PARTITION BY `s0`.`{g}`"
_BY_TIER = "ORDER BY `s0`.`{tier}` ASC"
_S10_SQL = (
    "COUNT(CASE WHEN `s0`.`{flag}` THEN 1 END)",
    "(COUNT(CASE WHEN `s0`.`{flag}` THEN NULL ELSE 1 END) = 0)",
    "`s0`.`{label}` = CAST(X'61' AS CHAR CHARACTER SET utf8mb4)"
    " COLLATE utf8mb4_0900_bin",
    "THEN 1 END) > 0)",
)
# The JOIN tuples' aggregate, its members named by the SQL's generated names.
_S11_PLAIN = "COUNT(DISTINCT `t1`.`c3`, `t1`.`c13`, `t1`.`c10`) AS `c1`"
_S11_ALIAS = "COUNT(DISTINCT `t1`.`c3`, `t1`.`c14`, `t1`.`c13`) AS `c1`"
_S11_TEXT_FLAG = "COUNT(DISTINCT `s0`.`{label}`, `s0`.`{flag}`)"
# The inlined `band(id) == 2` of P-S14-1, 2 and 4, preserved and bound.
_S14_WHERE = (
    "WHERE ((CASE WHEN (`s0`.`{id}` <= CAST(3 AS SIGNED)) THEN CAST(1 AS SIGNED)"
    " ELSE CAST(2 AS SIGNED) END) = CAST(2 AS SIGNED))"
)
_S14_BOUND = (
    "WHERE ((CASE WHEN (`s0`.`{id}` <= CAST(? AS SIGNED)) THEN CAST(? AS SIGNED)"
    " ELSE CAST(? AS SIGNED) END) = CAST(? AS SIGNED))"
)
# P-DEC's operands (PAIRS.md 5.2), money and the argument, in each order.
_S17_PARAMETER = tuple(
    f"SELECT ({left} {operator} {right}) AS `"
    for operator, (left, right) in (
        ("+", ("`s0`.`{money}`", "CAST(? AS SIGNED)")),
        ("-", ("CAST(? AS SIGNED)", "`s0`.`{money}`")),
        ("*", ("`s0`.`{money}`", "CAST(? AS SIGNED)")),
        ("*", ("CAST(? AS SIGNED)", "`s0`.`{money}`")),
    )
)
# Per form: the SQL fragments the pack's MySQL half preregisters (PAIRS.md 5.1,
# 5.2, 5.4, 5.5, 5.6, 5.7 and 5.9), `{field}` standing for the field's
# physical column, and for P-DECB-1 to 10, which the pack does not spell
# (5.10), the candidate's own; the public nullability, and the logical type
# of each public column PAIRS.md pairs, a Decimal with its precision and
# scale.
SQL = (
    ("X''", "X'e99baa'"),
    ("X'e99baa'", "X'612762'"),
    ("X''", "X'e99baa'", "X'612762'"),
    _S10_SQL,
    _S10_SQL,
    _S10_SQL,
    ("COUNT(*) OVER (ORDER BY",),
    ("MIN(", " ROWS ", "MIN(`s0`.`{id}`) OVER (ORDER BY `s0`.`{id}` ASC ROWS"),
    ("MIN(", "PARTITION BY"),
    ("COUNT(",),
    ("MAX(", "COUNT(*) OVER ("),
    ("COUNT(`s0`.`{id}`) OVER (ORDER BY",),
    ("MAX(",),
    _over(
        _BY_ID,
        ("COUNT", "ts"),
        ("COUNT", "d"),
        ("COUNT", "u"),
        ("MIN", "ts"),
        ("MAX", "d"),
    ),
    _over(
        _BY_ID,
        ("COUNT", "ts2"),
        ("COUNT", "d2"),
        ("MAX", "ts"),
        ("MIN", "d"),
        ("MIN", "ts2"),
        ("MAX", "d2"),
    ),
    _over(
        _BY_G,
        ("COUNT", "ts"),
        ("MAX", "ts"),
        ("MAX", "d2"),
        ("MIN", "d"),
        ("COUNT", "u"),
    )
    + (" ROWS ",),
    ("COUNT(*) OVER (" + _BY_TIER,)
    + _over(
        _BY_TIER,
        ("COUNT", "u"),
        ("COUNT", "d2"),
        ("MIN", "id"),
        ("MAX", "ts"),
        ("MAX", "d2"),
    ),
    (_S11_PLAIN, " LEFT JOIN "),
    (_S11_ALIAS, " LEFT JOIN "),
    (_S11_PLAIN, " INNER JOIN "),
    (_S11_ALIAS, " INNER JOIN "),
    ("COUNT(DISTINCT `t1`.", " LEFT JOIN "),
    ("COUNT(DISTINCT `t1`.", " INNER JOIN "),
    ("COUNT(DISTINCT `t1`.", " LEFT JOIN "),
    ("COUNT(DISTINCT `t1`.", " LEFT JOIN "),
    (
        _S11_TEXT_FLAG,
        "COUNT(DISTINCT `s0`.`{key}`, `s0`.`{label}`)",
        "COUNT(DISTINCT `s0`.`{key}`, `s0`.`{flag}`, `s0`.`{label}`)",
    ),
    ("COUNT(DISTINCT `s0`.`{key}`, `s0`.`{value}`)",),
    (_S11_TEXT_FLAG,),
    (_S14_WHERE, " LEFT JOIN "),
    (_S14_WHERE, " INNER JOIN "),
    (
        "COUNT(LOWER(",
        "COUNT(DISTINCT TRIM(",
        "COUNT(CAST(CHAR_LENGTH(",
        "COUNT(LOWER(TRIM(",
        " LEFT JOIN ",
    ),
    (_S14_BOUND, " LEFT JOIN ", "COUNT(LOWER("),
    *((fragment,) for fragment in _S17_PARAMETER),
    ("(`s0`.`{money}` + `s0`.`{id}`)", "(`s0`.`{money}` - `s0`.`{id}`)"),
    ("(`s0`.`{id}` + `s0`.`{money}`)", "(`s0`.`{id}` - `s0`.`{money}`)"),
    ("(`s0`.`{money}` * `s0`.`{id}`)",),
    ("(`s0`.`{id}` * `s0`.`{money}`)",),
    ("(`s0`.`{money}` * CAST(2 AS SIGNED))",),
    ("(-`s0`.`{money}`)",),
    ("(+`s0`.`{money}`)",),
    ("(-(`s0`.`{money}` * `s0`.`{id}`))",),
    ("(`s0`.`{money}` + `s0`.`{ratio}`)", "(`s0`.`{money}` - `s0`.`{ratio}`)"),
    ("(`s0`.`{money}` * `s0`.`{id}`)",),
)
NULLABLE = (
    [False, True, True, True],
    [False, True, True],
    [False, True, True, True, True, True],
    [False, False, False],
    [True, False, False, False],
    [False, False, False],
    [False, False],
    [False, True],
    [False, True],
    [False],
    [True, True, True, False],
    [False],
    [False, True],
    [False, False, False, True, True],
    [False, False, False, True, True, True, True],
    [False, False, True, True, True, False],
    [False, False, False, False, True, True, True],
    *([False, False],) * 4,
    *([True, False],) * 2,
    [False],
    [True, False, False],
    [False, False, False],
    [False],
    [True, False],
    [False, True],
    [False, True],
    [False] * 5,
    [False, False],
    # Binary arithmetic is UNKNOWN; a sign keeps its operand's nullability.
    *(["unknown"],) * 4,
    *(["unknown", "unknown"],) * 2,
    *(["unknown"],) * 3,
    *([False],) * 2,
    ["unknown"],
    ["unknown", "unknown"],
    ["unknown"],
)
LOGICAL = (
    ("Int", "Text", "Text", "Text"),
    ("Int", "Text", "Text"),
    ("Int", "Text", "Text", "Text", "Text", "Text"),
    ("Int", "Bool", "Bool"),
    ("Int", "Int", "Bool", "Bool"),
    ("Int", "Bool", "Bool"),
    ("Int", "Int"),
    ("Int", "Int"),
    ("Int", "Int"),
    ("Int",),
    ("Bool", "Int", "Int", "Int"),
    ("Int",),
    ("Int", "Int"),
    ("Int", "Int", "Int", "Timestamp", "Date"),
    ("Int", "Int", "Int", "Timestamp", "Date", "Timestamp", "Date"),
    ("Int", "Int", "Timestamp", "Date", "Date", "Int"),
    ("Int", "Int", "Int", "Int", "Int", "Timestamp", "Date"),
    *(("Int", "Int"),) * 6,
    ("Int",),
    ("Int", "Int", "Int"),
    ("Int", "Int", "Int"),
    ("Int",),
    ("Int", "Int"),
    ("Int", "Text"),
    ("Int", "Text"),
    ("Int",) * 5,
    ("Int", "Int"),
    *((("Decimal", 22, 2),),) * 2,
    *((("Decimal", 28, 2),),) * 2,
    *((("Decimal", 22, 2),) * 2,) * 2,
    *((("Decimal", 28, 2),),) * 3,
    *((("Decimal", 9, 2),),) * 2,
    (("Decimal", 28, 2),),
    (("Decimal", 11, 3),) * 2,
    (("Decimal", 65, 30),),
)
ENVIRONMENT = (
    ("client_encoding", "utf8mb4"),
    ("operator_environment", "builtin_only"),
    ("identifier_case", "lower_case_table_names=0"),
)
# ASCII names for every name of the forms, none a name the SQL generates.
NAMES = {
    "Row": "Item",
    "id": "k",
    "flag": "f",
    "text": "body",
    "money": "cash",
    "ratio": "share",
    "rows": "items",
    "result": "q16",
    "previous_empty": "pe",
    "following_unicode": "fu",
    "following_null": "fnull",
    "previous": "prv",
    "following": "fol",
    "plain": "pl",
    "lag_empty": "le",
    "lead_snow": "lsn",
    "lead_quote": "lq",
    "lead_none": "lno",
    # The form's shape and source are equal ignoring case, and so are these.
    "Agg": "Entry",
    "key": "bucket",
    "value": "qty",
    "label": "tag",
    "amount": "price",
    "rid": "row_no",
    "agg_row": "entry_key",
    "agg": "entry",
    "n": "cnt",
    "a": "every_f",
    "b": "some_tag",
    "k": "bkt",
    "o": "e",
    "g": "grp",
    "tier": "rank_key",
    "ts": "stamp",
    "ts2": "stamp2",
    "d": "day",
    "d2": "day2",
    "u": "ident",
    "w": "win",
    "low": "lo",
    "high": "hi",
    "other": "twin",
    "recent": "recentw",
    "count_timestamp": "cat",
    "count_date": "cday",
    "count_uuid": "cident",
    "low_timestamp": "loat",
    "high_date": "hiday",
    "count_ts2": "cat2",
    "count_d2": "cday2",
    "high_timestamp": "hiat",
    "low_date": "loday",
    "low_ts2": "loat2",
    "high_d2": "hiday2",
    "n_ts": "nat",
    "high_ts": "hiats",
    "low_d": "lod",
    "n_u": "nident",
    "n_d2": "nday2",
    "low_id": "lok",
    "keys": "ledger",
    "r": "rt",
    "lb": "rtag",
    "e": "dist2",
    "text_flag": "tf",
    "int_text": "it",
    "all_three": "a3",
    "int_int": "ii",
    "lhs": "left_side",
    "rhs": "right_side",
    "row_key": "item_key",
    "band": "tier",
    "x": "v",
    "pred": "picked",
    "l": "ll",
    "c": "cc",
    "factor": "mult",
    "total": "tot",
    "added": "plus",
    "subtracted": "minus",
}
_COLUMNS = ("c_id", "c_flag", "c_body", "c_cash", "c_share", "c_f", "c_g", "c_h")
# A name outside a string literal; a string literal and the frame keyword
# `rows` are kept.
_WORD = re.compile(
    r'"(?:[^"\\]|\\.)*"|\b(?:'
    + "|".join(sorted(NAMES, key=len, reverse=True))
    + r")\b(?! between )"
)
_LOCATOR = re.compile(r'(?<=mysql\.table\(")[^"]*')


def physical_names(form, namespace="app", tables=("items", "ledger"), columns=_COLUMNS):
    """(namespace, tables, columns) for form ``form``: one table per source and
    one column per field."""
    _, sources, fields, _ = WORLDS[FORMS[form][0]]
    return namespace, tuple(tables[: len(sources)]), tuple(columns[: len(fields)])


def contract(form=0, physical=None, names=None):
    """The pack's contract of ``form``; ``physical`` and ``names`` rename its
    names, by default the pack's namespace, tables and columns."""
    names = names or {}
    _, sources, fields, (namespace, tables) = WORLDS[FORMS[form][0]]
    namespace, tables, columns = physical or (
        namespace,
        tables,
        tuple(field[1] for field in fields),
    )
    protocol = (("parameter_protocol", "mysql_prepared"),) * (form in PROTOCOL)
    return {
        "environment": [
            {"key": key, "scope": "statement", "value": value}
            for key, value in ENVIRONMENT + protocol
        ],
        "format": "pietto.emission-contract.v1",
        "sources": [
            {
                "fields": [
                    {
                        "column": column,
                        "name": names.get(name, name),
                        "ordinal": ordinal,
                        "representation": {
                            "domain": dict(storage(logical, *scale)[1]),
                            "nullable": nullable,
                            "storage": dict(storage(logical, *scale)[0]),
                        },
                    }
                    for ordinal, ((name, _, logical, nullable, *scale), column) in (
                        enumerate(zip(fields, columns, strict=True))
                    )
                ],
                "premises": [
                    {"key": key, "scope": "source", "value": True}
                    for key in ("row_domain_matches", "read_only_object")
                ],
                "relation": {"name": table, "namespace": namespace},
                "scan": "relation_rows",
                "selector": {
                    "kind": "source",
                    "module": "main.pietto",
                    "name": names.get(source, source),
                },
            }
            for source, table in zip(sources, tables, strict=True)
        ],
        "target": {"family": "mysql", "release": "8.4.12"},
    }


def pack(form):
    """Form ``form``'s module as the pack writes it."""
    world, body = FORMS[form]
    return WORLDS[world][0] + body.format(name="result")


def module(form, names=NAMES, locators=("app.items", "app.ledger")):
    """Form ``form``'s module with ``names`` and ``locators``, one per source,
    written over."""
    found = iter(locators)
    text = _LOCATOR.sub(lambda match: next(found), pack(form))
    return _WORD.sub(lambda match: names.get(match[0], match[0]), text)


def project(
    directory,
    form,
    *,
    names=NAMES,
    locators=("app.items", "app.ledger"),
    physical=None,
):
    """Write form ``form`` as a one-module MySQL project in ``directory``."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n'
    )
    (directory / "main.pietto").write_text(
        module(form, names, locators), encoding="utf-8", newline="\n"
    )
    (directory / "contract.json").write_text(
        json.dumps(contract(form, physical or physical_names(form), names)),
        encoding="utf-8",
    )
    return directory
