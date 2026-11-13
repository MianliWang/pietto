"""The Phase77 Wave A qualification pack's S16 forms, copied verbatim.

PAIRS.md 5.4 gives the three paired bodies (`{name}` is the selected query's
name), 4.3 the MySQL world `rows_ntext` they read and the pack's
`mysql/plan.py` the MySQL contract its `compile_sql` runs with. `project`
writes one form with only its names changed.
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
BODIES = (
    "query {name}:\n"
    "    from rows\n"
    "    select:\n"
    "        id\n"
    '        previous_empty = lag(text, 1, "") window(order by id)\n'
    '        following_unicode = lead(text, 1, "雪") window(order by id)\n'
    "        following_null = lead(text, 1) window(order by id)\n",
    "query {name}:\n"
    "    from rows\n"
    "    select:\n"
    "        id\n"
    '        previous = lag(text, 1, "雪") window(order by id)\n'
    '        following = lead(text, 1, "a\'b") window(order by id)\n',
    "query {name}:\n"
    "    from rows\n"
    "    select:\n"
    "        id\n"
    "        plain = text\n"
    '        lag_empty = lag(text, 1, "") window(order by id)\n'
    '        lead_snow = lead(text, 1, "雪") window(order by id)\n'
    '        lead_quote = lead(text, 1, "a\'b") window(order by id)\n'
    "        lead_none = lead(text, 1) window(order by id)\n",
)
# Per form: the SQL fragments and the public nullability PAIRS.md 5.4 pairs.
SQL = (
    ("X''", "X'e99baa'"),
    ("X'e99baa'", "X'612762'"),
    ("X''", "X'e99baa'", "X'612762'"),
)
NULLABLE = (
    [False, True, True, True],
    [False, True, True],
    [False, True, True, True, True, True],
)
_TEXT = {
    "collation": "utf8mb4_0900_bin",
    "encoding": "utf8mb4",
    "kind": "text",
    "max_characters": 64,
    "padding": "NO PAD",
}
_INT = {"kind": "int_range", "max": "9007199254740993", "min": "-9007199254740993"}
FIELDS = (
    ("id", "order.id", {"kind": "my_bigint"}, False, _INT),
    ("flag", "flag value", {"kind": "my_bool01"}, True, {"kind": "bool01"}),
    ("text", 'text `"é', {"kind": "my_varchar", "length": 64}, True, _TEXT),
    (
        "money",
        "amount value",
        {"kind": "my_decimal", "precision": 9, "scale": 2},
        False,
        {"kind": "decimal", "precision": 9, "scale": 2},
    ),
    (
        "ratio",
        "ratio value",
        {"kind": "my_double"},
        False,
        {"format": "binary64", "kind": "finite_float"},
    ),
)
ENVIRONMENT = (
    ("client_encoding", "utf8mb4"),
    ("operator_environment", "builtin_only"),
    ("identifier_case", "lower_case_table_names=0"),
)
# ASCII names for every name of the three forms.
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
}
PHYSICAL = ("app", "items", ("c_id", "c_flag", "c_body", "c_cash", "c_share"))
_WORD = re.compile(r"\b(" + "|".join(sorted(NAMES, key=len, reverse=True)) + r")\b")


def contract(physical=("phase66", "phase66 source é", None), names=None):
    """The pack's contract; ``physical`` and ``names`` rename its names."""
    names = names or {}
    namespace, table, columns = physical
    columns = columns or tuple(field[1] for field in FIELDS)
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
                            "domain": dict(domain),
                            "nullable": nullable,
                            "storage": dict(storage),
                        },
                    }
                    for ordinal, ((name, _, storage, nullable, domain), column) in (
                        enumerate(zip(FIELDS, columns, strict=True))
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
                    "name": names.get("rows", "rows"),
                },
            }
        ],
        "target": {"family": "mysql", "release": "8.4.12"},
    }


def module(form, names=NAMES, locator="app.items"):
    """Form ``form``'s module with ``names`` and ``locator`` written over."""
    text = HEADER.replace("opaque.locator.not.sql", locator) + BODIES[form].format(
        name="result"
    )
    return _WORD.sub(lambda match: names.get(match[0], match[0]), text)


def project(directory, form, *, names=NAMES, locator="app.items", physical=PHYSICAL):
    """Write form ``form`` as a one-module MySQL project in ``directory``."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n'
    )
    (directory / "main.pietto").write_text(
        module(form, names, locator), encoding="utf-8", newline="\n"
    )
    (directory / "contract.json").write_text(
        json.dumps(contract(physical, names)), encoding="utf-8"
    )
    return directory
