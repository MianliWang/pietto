"""The Phase77 Wave A qualification pack's paired forms, copied verbatim.

PAIRS.md 5.4 and 5.6 give the paired bodies (`{name}` is the selected query's
name), 4.3 and 4.6 the MySQL worlds `rows_ntext` and `agg` they read, and the
pack's `mysql/plan.py` the MySQL contract its `compile_sql` runs with. `FORMS`
is in the order of `project_sql_emission_paired.FORMS`: S16 P-S16-1..3, then
S10 bodies A (P-S10-1, 5), B (P-S10-2) and C (P-S10-3, 4). `project` writes
one form with only its names changed.
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
_TEXT = {
    "collation": "utf8mb4_0900_bin",
    "encoding": "utf8mb4",
    "kind": "text",
    "max_characters": 64,
    "padding": "NO PAD",
}
_INT = {"kind": "int_range", "max": "9007199254740993", "min": "-9007199254740993"}
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
}
# Per world: its header, its source, its (field, pack column, logical type,
# nullable) and the pack's namespace and table.
WORLDS = {
    "rows_ntext": (
        HEADER,
        "rows",
        (
            ("id", "order.id", "Int", False),
            ("flag", "flag value", "Bool", True),
            ("text", 'text `"é', "Text", True),
            ("money", "amount value", "Decimal", False),
            ("ratio", "ratio value", "Float", False),
        ),
        ("phase66", "phase66 source é"),
    ),
    "agg": (
        AGG_HEADER,
        "agg",
        (
            ("key", "group key", "Int", True),
            ("value", "value é", "Int", True),
            ("flag", "flag value", "Bool", True),
            ("label", 'text `"é', "Text", False),
            ("amount", "amount value", "Decimal", False),
            ("ratio", "ratio value", "Float", False),
            ("rid", "row id", "Int", False),
        ),
        ("phase66", "phase66 agg é"),
    ),
}
_S10_TESTS = (
    "        n = sum(1 for o in group if o.flag)\n"
    "        a = all(o.flag for o in group)\n"
    '        b = any(o.label == "a" for o in group)\n'
)
_S10_GROUPED = "query {name}:\n    from agg\n    group by:\n        key\n    select:\n"
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
)
S16 = range(3)
S10 = range(3, 6)
_S10_SQL = (
    "COUNT(CASE WHEN `s0`.`{flag}` THEN 1 END)",
    "(COUNT(CASE WHEN `s0`.`{flag}` THEN NULL ELSE 1 END) = 0)",
    "`s0`.`{label}` = CAST(X'61' AS CHAR CHARACTER SET utf8mb4)"
    " COLLATE utf8mb4_0900_bin",
    "THEN 1 END) > 0)",
)
# Per form: the SQL fragments the pack's MySQL half preregisters (PAIRS.md 5.4
# and 5.6), `{field}` standing for the field's physical column; the public
# nullability and the logical type of each public column PAIRS.md pairs.
SQL = (
    ("X''", "X'e99baa'"),
    ("X'e99baa'", "X'612762'"),
    ("X''", "X'e99baa'", "X'612762'"),
    _S10_SQL,
    _S10_SQL,
    _S10_SQL,
)
NULLABLE = (
    [False, True, True, True],
    [False, True, True],
    [False, True, True, True, True, True],
    [False, False, False],
    [True, False, False, False],
    [False, False, False],
)
LOGICAL = (
    ("Int", "Text", "Text", "Text"),
    ("Int", "Text", "Text"),
    ("Int", "Text", "Text", "Text", "Text", "Text"),
    ("Int", "Bool", "Bool"),
    ("Int", "Int", "Bool", "Bool"),
    ("Int", "Bool", "Bool"),
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
}
_COLUMNS = ("c_id", "c_flag", "c_body", "c_cash", "c_share", "c_f", "c_g")
# A name outside a string literal; a string literal is kept.
_WORD = re.compile(
    r'"(?:[^"\\]|\\.)*"|\b(?:' + "|".join(sorted(NAMES, key=len, reverse=True)) + r")\b"
)
_LOCATOR = re.compile(r'(?<=mysql\.table\(")[^"]*')


def physical_names(form, namespace="app", table="items", columns=_COLUMNS):
    """(namespace, table, columns) for form ``form``: one column per field."""
    return namespace, table, tuple(columns[: len(WORLDS[FORMS[form][0]][2])])


PHYSICAL = physical_names(0)


def contract(form=0, physical=None, names=None):
    """The pack's contract of ``form``; ``physical`` and ``names`` rename its
    names, by default the pack's namespace, table and columns."""
    names = names or {}
    _, source, fields, (namespace, table) = WORLDS[FORMS[form][0]]
    namespace, table, columns = physical or (
        namespace,
        table,
        tuple(field[1] for field in fields),
    )
    return {
        "environment": [
            {"key": key, "scope": "statement", "value": value}
            for key, value in ENVIRONMENT
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
                            "domain": dict(STORAGE[logical][1]),
                            "nullable": nullable,
                            "storage": dict(STORAGE[logical][0]),
                        },
                    }
                    for ordinal, ((name, _, logical, nullable), column) in (
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
        ],
        "target": {"family": "mysql", "release": "8.4.12"},
    }


def pack(form):
    """Form ``form``'s module as the pack writes it."""
    world, body = FORMS[form]
    return WORLDS[world][0] + body.format(name="result")


def module(form, names=NAMES, locator="app.items"):
    """Form ``form``'s module with ``names`` and ``locator`` written over."""
    text = _LOCATOR.sub(locator, pack(form), count=1)
    return _WORD.sub(lambda match: names.get(match[0], match[0]), text)


def project(directory, form, *, names=NAMES, locator="app.items", physical=None):
    """Write form ``form`` as a one-module MySQL project in ``directory``."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n'
    )
    (directory / "main.pietto").write_text(
        module(form, names, locator), encoding="utf-8", newline="\n"
    )
    (directory / "contract.json").write_text(
        json.dumps(contract(form, physical or physical_names(form), names)),
        encoding="utf-8",
    )
    return directory
