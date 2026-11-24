"""The fixtures of the Phase79 DuckDB native qualification (preregistration
v7, sections 3, 4f-4k and 4l-4r): projects P0, P1, P2 and PB, tables T5, TN,
B2's tables and the sized, capacity and forged tables, B2's statements, tier
2's projects PT, PA and PJ with their tables and statements, the cells with
their sub-cases, the processes that run them, and the one value encoding the
producer and the oracle share. Importing it loads neither PyArrow nor DuckDB
nor Pietto; tables are built from the caller's PyArrow module."""

from __future__ import annotations

import hashlib
import json
import math
import struct
from datetime import date, datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any

INT64 = (-(2**63), 2**63 - 1)
COLUMNS = ("id", "amount", "note", "ok", "price")
TYPES = ("int64", "int64", "string", "bool_", "float64")
T5 = (
    (1, 5, "a", True, 1.5),
    (2, 10, None, False, -0.0),
    (3, 15, "c", True, 2.5),
    (4, -(2**63), "", False, -1.0),
    (5, 2**63 - 1, "é", True, 0.0),
)
T1 = ((1, 5, None, True, 1.0),)
ROW6 = (6, None, "n", True, 3.0)
NOTES = (
    "\0a",
    "a\0b",
    "a\0",
    "\0",
    "\0\0\0",
    "\0" * 100,
    "a",
    "",
    "é\0é",
    "abcdefghijkl\0mnopq",
    "abcdefghijk\0",
    None,
)
TN = tuple((k, k % 3, NOTES[k], True, 1.0) for k in range(12))
OPERATORS = ("==", "!=", "<", "<=", ">", ">=")
C08_VALUES = (-(2**63), -1, 0, 7, 2**63 - 1)
# The capture limits as PL.47 revises D79.04: rows, and bytes of the selected
# columns only.
MAX_ROWS = 1_048_576
MAX_BYTES = 268_435_456
WATCHDOG_SECONDS = 30.0

SLOW_SQL = 'SELECT count(*) AS "id", NULL AS "note" FROM pietto_running'
FRAME_SQL = "SELECT * FROM pietto_frame_table"
NEVER_SQL = "SELECT pietto_never_runs()"
OVERFLOW_SQL = (
    'SELECT CAST(9223372036854775807 AS BIGINT) + "c0" AS "id", "c2" AS "note" '
    'FROM temp.main."pietto_arrow_0"'
)
RELABEL_SQL = 'SELECT "c0" AS "ID", "c2" AS "note" FROM temp.main."pietto_arrow_0"'
# L13: a grouping on 60,000,000 distinct keys, beyond the 1 GiB memory_limit
# with no temporary directory to spill into.
OOM_SQL = (
    'SELECT count(*) AS "id", NULL AS "note" FROM '
    "(SELECT r FROM range(60000000) t(r) GROUP BY r)"
)
E_SQL = "SELECT extension_name FROM duckdb_extensions() WHERE loaded ORDER BY 1"
SETTINGS_SQL = "SELECT name, value FROM duckdb_settings()"
K_SQL = (
    "SELECT database_name, schema_name, function_name, function_type, "
    "CAST(parameter_types AS VARCHAR), return_type FROM duckdb_functions() "
    "ORDER BY ALL",
    "SELECT name FROM duckdb_settings() ORDER BY 1",
    "SELECT database_name, schema_name, type_name FROM duckdb_types() ORDER BY ALL",
)

# Projects (section 3): the amount field's spelling, nullability and range;
# PB (section 4f) also makes `ok` and `price` optional.
PROJECTS = {
    "P0": ("Int", False, INT64),
    "P1": ("Int | None", True, INT64),
    "P2": ("Int", False, (-100, 100)),
    "PB": ("Int | None", True, INT64),
}
P_BODY = "table result:\n    from orders\n    select:\n        id\n        note\n"


def q_body(operator: str, selected: tuple[str, str] = ("id", "price")) -> str:
    """Q(op), or QN with ("id", "note")."""
    return (
        "query result(min_amount: Int):\n    from orders\n"
        f"    where amount {operator} min_amount\n    select:\n"
        f"        {selected[0]}\n        {selected[1]}\n"
    )


def _representation(kind: str, nullable: bool, bounds: tuple[int, int]) -> dict:
    if kind.startswith("Decimal("):
        precision, scale = decimal_of(kind)
        pair = {"precision": precision, "scale": scale}
        return {
            "storage": {"kind": "arrow_decimal128", **pair},
            "domain": {"kind": "decimal", **pair},
            "nullable": nullable,
        }
    if kind in ("Date", "Timestamp"):
        storage = "arrow_date32" if kind == "Date" else "arrow_timestamp_us"
        return {
            "storage": {"kind": storage},
            "domain": {"kind": kind.lower()},
            "nullable": nullable,
        }
    domains = {
        "Int": {"kind": "int_range", "min": str(bounds[0]), "max": str(bounds[1])},
        "Text": {
            "kind": "text",
            "max_characters": 100,
            "encoding": "UTF8",
            "collation": "C",
            "padding": "NO PAD",
        },
        "Bool": {"kind": "bool01"},
        "Float": {"kind": "finite_float", "format": "binary64"},
    }
    storage = {"Int": "arrow_int64", "Text": "arrow_string", "Bool": "arrow_bool"}
    return {
        "storage": {"kind": storage.get(kind, "arrow_float64")},
        "domain": domains[kind],
        "nullable": nullable,
    }


def contract(project: str) -> dict:
    _spelling, nullable, bounds = PROJECTS[project]
    fields = (
        ("id", "Int", False, INT64),
        ("amount", "Int", nullable, bounds),
        ("note", "Text", True, INT64),
        ("ok", "Bool", project == "PB", INT64),
        ("price", "Float", project == "PB", INT64),
    )
    statement = [
        {"key": key, "scope": "statement", "value": value}
        for key, value in (
            ("client_encoding", "UTF8"),
            ("operator_environment", "builtin_only"),
            ("parameter_protocol", "duckdb_prepared"),
        )
    ]
    source = {
        "selector": {"module": "main.pietto", "kind": "source", "name": "orders"},
        "relation": {"namespace": "arrow", "name": "orders"},
        "scan": "arrow_registration",
        "fields": [
            {
                "ordinal": i,
                "name": name,
                "column": name,
                "representation": _representation(kind, field_nullable, field_bounds),
            }
            for i, (name, kind, field_nullable, field_bounds) in enumerate(fields)
        ],
        "premises": [
            {"key": key, "scope": "source", "value": True}
            for key in ("row_domain_matches", "read_only_object")
        ],
    }
    return {
        "format": "pietto.emission-contract.v1",
        "target": {"family": "duckdb", "release": "2.0.1"},
        "sources": [source],
        "environment": statement,
    }


def header(project: str) -> str:
    """The shapes and sources above a statement: P's one source, or a tier 2
    project's shapes, in order of first use, and sources."""
    if project in T2_PROJECTS:
        sources = T2_PROJECTS[project]
        text = ""
        for shape in dict.fromkeys(shape for _name, shape, _key in sources):
            text += f"shape {shape}:\n"
            for name, kind, nullable in T2_SHAPES[shape]:
                text += f"    {name}: {kind}{' | None' if nullable else ''}\n"
            text += "".join(f"    key = unique({k})\n" for k in T2_KEYS.get(shape, ()))
            text += "\n"
        return text + "".join(
            f'source {name}: {shape} = duckdb.arrow("{key}")\n'
            for name, shape, key in sources
        )
    spelling = PROJECTS[project][0]
    optional = " | None" if project == "PB" else ""
    return (
        f"shape Order:\n    id: Int\n    amount: {spelling}\n    note: Text | None\n"
        f"    ok: Bool{optional}\n    price: Float{optional}\n\n"
        'source orders: Order = duckdb.arrow("orders")\n'
    )


def write_project(
    root: Path, project: str, body: str, namespace: dict | None = None
) -> Path:
    """An explicit-module project: the header, the body, the contract, whose
    relation namespace `namespace` changes for the sources it names."""
    document = t2_contract(project) if project in T2_PROJECTS else contract(project)
    for entry in document["sources"]:
        entry["relation"]["namespace"] = (namespace or {}).get(
            entry["selector"]["name"], "arrow"
        )
    root.mkdir(parents=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    (root / "main.pietto").write_text(header(project) + "\n" + body, encoding="utf-8")
    (root / "contract.json").write_text(json.dumps(document), encoding="utf-8")
    return root


def table(pa: Any, rows: Any, **columns: Any) -> Any:
    """The `orders` table of `rows`, each named column replaced by an array."""
    rows = tuple(rows)
    arrays = {
        name: pa.array([row[k] for row in rows], type=getattr(pa, TYPES[k])())
        for k, name in enumerate(COLUMNS)
    }
    arrays.update(columns)
    return pa.table(arrays)


_CHARACTER = {1: "a", 2: "é", 3: "€", 4: "\U0001f600"}


def _text_of(size: int) -> str:
    """A string of exactly `size` UTF-8 bytes in at most 100 code points."""
    fours, rest = divmod(size, 4)
    return _CHARACTER[4] * fours + (_CHARACTER[rest] if rest else "")


def _strings(pa: Any, values: list[bytes]) -> Any:
    """A `string` array of these UTF-8 values with no validity buffer."""
    offsets, at = [0], 0
    for value in values:
        at += len(value)
        offsets.append(at)
    buffer = pa.array(offsets, pa.int32()).buffers()[1]
    return pa.StringArray.from_buffers(
        len(values), buffer, pa.py_buffer(b"".join(values))
    )


def _five(pa: Any, note: Any, amount: list, ok: list, price: list) -> Any:
    rows = len(note)
    return pa.table(
        {
            "id": pa.array(list(range(rows)), pa.int64()),
            "amount": pa.array(amount, pa.int64()),
            "note": note,
            "ok": pa.array(ok, pa.bool_()),
            "price": pa.array(price, pa.float64()),
        }
    )


def sized(pa: Any, total: int) -> Any:
    """C05: five columns of MAX_ROWS rows (k, 5, a note, True, 0.0) whose
    `Table.nbytes` is `total`, each note of valid UTF-8 in at most 100 code
    points; the caller checks the size before use."""
    rows = MAX_ROWS
    filled = ([5] * rows, [True] * rows, [0.0] * rows)
    empty = _five(pa, _strings(pa, [b""] * rows), *filled)
    each, extra = divmod(total - empty.nbytes, rows)
    texts = [_text_of(each + 1).encode(), _text_of(each).encode()]
    notes = [texts[0]] * extra + [texts[1]] * (rows - extra)
    return _five(pa, _strings(pa, notes), *filled)


# C21's capacity table: MAX_ROWS rows k = 0, 1, ..., whose five columns
# measure 267,517,956 bytes, within MAX_BYTES; every note is distinct.
CAPACITY_PAD = "\U0001f600" * 55


def capacity_row(k: int) -> tuple:
    return (k, k % 1000 - 500, f"{k:07d}{CAPACITY_PAD}", k % 3 == 0, float(k % 7 - 3))


def capacity(pa: Any) -> Any:
    rows = range(MAX_ROWS)
    pad = CAPACITY_PAD.encode()
    note = _strings(pa, [b"%07d" % k + pad for k in rows])
    return _five(
        pa,
        note,
        [k % 1000 - 500 for k in rows],
        [k % 3 == 0 for k in rows],
        [float(k % 7 - 3) for k in rows],
    )


C06_SUBS = (
    "note:dictionary",
    "note:large_string",
    "note:string_view",
    "note:null",
    "note:binary",
    "id:extension",
    "id:int32",
    "id:bool",
    "price:float32",
    "schema:amount missing",
    "schema:second id",
    "schema:ID",
    "price:NaN",
    "price:+Inf",
    "price:-Inf",
    "note:invalid UTF-8",
    "id:NULL",
    "note:101 characters",
    "note:101 NULs",
    "P2:amount 101",
)


def forged(pa: Any, sub: str) -> Any:
    """C06: a one-row table that differs from P0's source in one way."""
    one = ((1, 5, "a", True, 1.5),)

    def changed(**columns: Any) -> Any:
        return table(pa, one, **columns)

    if sub == "id:extension":

        class Tagged(pa.ExtensionType):
            def __init__(self) -> None:
                super().__init__(pa.int64(), "pietto.s06.tagged")

            def __arrow_ext_serialize__(self) -> bytes:
                return b""

            @classmethod
            def __arrow_ext_deserialize__(
                cls, storage_type: Any, serialized: bytes
            ) -> Any:
                return cls()

        storage = pa.array([1], pa.int64())
        return changed(id=pa.ExtensionArray.from_storage(Tagged(), storage))
    base = table(pa, one)
    offsets = pa.py_buffer(bytes([0, 0, 0, 0, 1, 0, 0, 0]))
    builders = {
        "note:dictionary": lambda: changed(note=pa.array(["a"]).dictionary_encode()),
        "note:large_string": lambda: changed(note=pa.array(["a"], pa.large_string())),
        "note:string_view": lambda: changed(note=pa.array(["a"], pa.string_view())),
        "note:null": lambda: changed(note=pa.array([None], pa.null())),
        "note:binary": lambda: changed(note=pa.array([b"a"], pa.binary())),
        "id:int32": lambda: changed(id=pa.array([1], pa.int32())),
        "id:bool": lambda: changed(id=pa.array([True], pa.bool_())),
        "price:float32": lambda: changed(price=pa.array([1.5], pa.float32())),
        "schema:amount missing": lambda: base.drop_columns(["amount"]),
        "schema:second id": lambda: base.append_column("id", pa.array([2], pa.int64())),
        "schema:ID": lambda: base.rename_columns(
            ["ID", "amount", "note", "ok", "price"]
        ),
        "price:NaN": lambda: changed(price=pa.array([math.nan])),
        "price:+Inf": lambda: changed(price=pa.array([math.inf])),
        "price:-Inf": lambda: changed(price=pa.array([-math.inf])),
        "note:invalid UTF-8": lambda: changed(
            note=pa.Array.from_buffers(
                pa.string(), 1, [None, offsets, pa.py_buffer(b"\xff")]
            )
        ),
        "id:NULL": lambda: changed(id=pa.array([None], pa.int64())),
        "note:101 characters": lambda: changed(note=pa.array(["x" * 101])),
        "note:101 NULs": lambda: changed(note=pa.array(["\0" * 101])),
        "P2:amount 101": lambda: table(pa, ((1, 101, "a", True, 1.5),)),
    }
    return builders[sub]()


# B2's tables (section 4f): (id, amount, note, ok, price) rows over PB.
TB = (
    (1, 5, "a", True, 1.5),
    (2, 10, None, False, -0.0),
    (3, 15, "a", True, 0.0),
    (4, None, "a\0", None, -1.0),
    (5, -7, None, False, 2.5),
    (6, 20, "a", False, None),
    (7, 1, "a\0b", True, 0.0),
    (8, None, "é", None, -0.0),
    (9, 5, "B", True, 1.5),
    (10, -(2**62), "é", False, 2.5),
    (11, 2**62, "z", True, -1.0),
    (12, 0, "", None, None),
)
TL = (
    (1, 5, "it's", True, 1.5),
    (2, -(2**63), "a\\b", False, -0.0),
    (3, 2**63 - 1, "é€", True, 0.0),
    (4, 0, None, False, 0.000001),
    (5, 7, 'say "hi"', True, 0.1),
    (6, None, "a\0b", None, None),
)
TZ = (
    (1, 1, "x", True, -0.0),
    (2, 1, "x", True, 0.0),
    (3, 1, "x", False, 0.0),
    (4, 1, "x", False, -0.0),
    (5, 1, "x", False, 1.0),
)
TE = tuple(
    (k, amount, note, True, 0.0)
    for k, (note, amount) in enumerate(
        [("x", 2**63 - 1), ("x", 1), ("y", 1), ("y", 2), ("y", 3)]
        + [("z", 4), ("z", 5), ("z", 6)]
    )
)


def _sums(*amounts: int) -> tuple:
    return tuple((k, a, "s", True, 0.0) for k, a in enumerate(amounts))


TABLES: dict[str, Any] = {
    "TB": TB,
    "TL": TL,
    "TZ": TZ,
    "TE": TE,
    "EMPTY": (),
    "TNULL": ((4, None, "a\0", None, None), (8, None, "é", None, None)),
    "SUM max": _sums(2**63 - 2, 1),
    "SUM min": _sums(-(2**63) + 1, -1),
    "SUM back": _sums(2**63 - 1, 1, -1),
    "SUM over": _sums(2**63 - 1, 1),
    "SUM under": _sums(-(2**63), -1),
    "SUM grouped": ((1, 2**63 - 1, "g", True, 0.0), (2, 1, "g", True, 0.0))
    + ((3, 5, "h", True, 0.0),),
    "NARROW": tuple((k, k % 7, f"n{k % 3}", True, 0.0) for k in range(3000)),
    "WIDE": tuple(
        (k, (2**62, 2**62, -(2**62), -(2**62))[k % 4], "w", True, 0.0)
        for k in range(100_000)
    ),
}

# B2's statements (section 4f): expressions are ("f", name) for a field or a
# selected output, ("p", name), ("lit", value, spelling), ("cmp", op, a, b),
# ("null", x, negated), ("not", a), ("and", a, b) and ("or", a, b); a select
# item is (label, ("f", field)) or (label, ("agg", function, field or None)).


def F(name: str) -> tuple:
    return ("f", name)


def P(name: str) -> tuple:
    return ("p", name)


def L(value: Any, spelling: str | None = None) -> tuple:
    if spelling is None:
        if isinstance(value, bool):
            spelling = str(value)
        elif isinstance(value, str):
            spelling = '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
        else:
            spelling = repr(value)
    return ("lit", value, spelling)


def cmp(op: str, a: tuple, b: tuple) -> tuple:
    return ("cmp", op, a, b)


def null(x: tuple, negated: bool = False) -> tuple:
    return ("null", x, negated)


def agg(function: str, field: str | None = None) -> tuple:
    return ("agg", function, field)


COUNT = agg("count")


def reads(*names: str) -> list:
    return [(name, F(name)) for name in names]


def render(expr: tuple) -> str:
    kind = expr[0]
    if kind in ("f", "p"):
        return expr[1]
    if kind == "lit":
        return expr[2]
    if kind == "agg":
        return f"{expr[1]}({expr[2] or ''})"
    if kind == "arith":
        return f"{render(expr[2])} {expr[1]} {render(expr[3])}"
    if kind in ("neg", "pos"):
        return f"{'-' if kind == 'neg' else '+'}{render(expr[1])}"
    if kind == "cmp":
        return f"{render(expr[2])} {expr[1]} {render(expr[3])}"
    if kind == "null":
        return f"{render(expr[1])} is {'not ' if expr[2] else ''}None"
    if kind == "not":
        return f"not ({render(expr[1])})"

    def operand(x: tuple) -> str:
        return render(x) if x[0] in ("cmp", "null") else f"({render(x)})"

    return f" {kind} ".join(operand(x) for x in expr[1:])


def stmt(select: list, **parts: Any) -> dict:
    spec = {
        "project": "PB",
        "table": "TB",
        "params": (),
        "values": None,
        "where": None,
        "group": (),
        "having": None,
        "order": (),
        "limit": None,
        "digest": False,
        "select": select,
        "from": "orders",
        "lets": (),
        "joins": (),
        "inputs": None,
        "limits": None,
        "swap": False,
        "namespace": None,
    }
    spec.update(parts)
    return spec


def body(spec: dict) -> str:
    """The Pietto text of a statement."""
    params = ", ".join(f"{name}: {kind}" for name, kind in spec["params"])
    text = f"query result({params}):\n" if params else "table result:\n"
    text += f"    from {spec['from']}\n"
    text += "".join(f"    {line}\n" for line in spec["lets"])
    for join in spec["joins"]:
        if isinstance(join, str):
            text += f"    {join}\n"
            continue
        kind, source, pairs = join
        on = " and ".join(f"{a} == {b}" for a, b in pairs)
        text += f"    {kind} join {source} on {on}\n"
    if spec["where"] is not None:
        text += f"    where {render(spec['where'])}\n"
    if spec["group"]:
        text += f"    group by {', '.join(spec['group'])}\n"
    text += "    select:\n"
    for label, item in spec["select"]:
        if item[0] == "raw":
            line = item[1]
        else:
            same = item[0] == "f" and item[1] == label
            line = label if same else f"{label} = {render(item)}"
        text += f"        {line}\n"
    if spec["having"] is not None:
        text += f"    having {render(spec['having'])}\n"
    if spec["order"]:
        text += "    order by:\n"
        text += "".join(
            f"        {k}{' desc' if d else ''}\n" for k, d in spec["order"]
        )
    if spec["limit"] is not None:
        text += f"    limit {spec['limit']}\n"
    return text


BOTH = ("forward", "reversed")
OPS = ("==", "!=", "<", "<=", ">", ">=")


def _orders(named: dict, orders: tuple = BOTH) -> dict:
    return {f"{name} {order}": spec for name, spec in named.items() for order in orders}


GROUP_NOTE = [("note", F("note")), ("n", COUNT), ("total", agg("sum", "amount"))]
C17 = {
    **_orders(
        {
            "keys": stmt(
                [
                    *reads("note", "ok"),
                    ("n", COUNT),
                    ("filled", agg("count", "amount")),
                    ("total", agg("sum", "amount")),
                    ("low", agg("min", "price")),
                    ("high", agg("max", "id")),
                ],
                group=("note", "ok"),
            ),
            "float key": stmt(
                [*reads("price"), ("n", COUNT), ("total", agg("sum", "amount"))],
                group=("price",),
            ),
            "int key": stmt(
                [*reads("amount"), ("n", COUNT), ("low", agg("min", "id"))],
                group=("amount",),
            ),
            "bool key": stmt(
                [
                    *reads("ok"),
                    ("n", COUNT),
                    ("filled", agg("count", "note")),
                    ("total", agg("sum", "amount")),
                    ("high", agg("max", "price")),
                ],
                group=("ok",),
            ),
            "text key": stmt(
                [*reads("note"), ("n", COUNT), ("low", agg("min", "id"))],
                group=("note",),
            ),
            "global": stmt(
                [
                    ("n", COUNT),
                    ("filled", agg("count", "amount")),
                    ("total", agg("sum", "amount")),
                    ("low", agg("min", "price")),
                    ("high", agg("max", "price")),
                ]
            ),
            "zero extremes": stmt(
                [
                    *reads("ok"),
                    ("low", agg("min", "price")),
                    ("high", agg("max", "price")),
                ],
                group=("ok",),
                table="TZ",
            ),
            "labels": stmt(
                [
                    ("c1", F("note")),
                    ("C0", COUNT),
                    ("c4", agg("min", "id")),
                    ("c2", agg("sum", "amount")),
                ],
                group=("note",),
            ),
            "narrow": stmt(GROUP_NOTE, group=("note",), table="NARROW"),
            "wide": stmt([("total", agg("sum", "amount")), ("n", COUNT)], table="WIDE"),
            **{
                f"sum {name}": stmt(
                    [("total", agg("sum", "amount"))], table=f"SUM {name}"
                )
                for name in ("max", "min", "back")
            },
        }
    ),
    **_orders(
        {
            "global empty": stmt(
                [
                    ("n", COUNT),
                    ("total", agg("sum", "amount")),
                    ("low", agg("min", "price")),
                    ("high", agg("max", "id")),
                ],
                table="EMPTY",
            ),
            "grouped empty": stmt(GROUP_NOTE, group=("note",), table="EMPTY"),
            "all null": stmt(
                [
                    ("n", COUNT),
                    ("filled", agg("count", "amount")),
                    ("total", agg("sum", "amount")),
                    ("low", agg("min", "price")),
                    ("high", agg("max", "amount")),
                ],
                table="TNULL",
            ),
            "sum over": stmt([("total", agg("sum", "amount"))], table="SUM over"),
            "sum under": stmt([("total", agg("sum", "amount"))], table="SUM under"),
            "sum grouped over": stmt(GROUP_NOTE, group=("note",), table="SUM grouped"),
            "filtered overflow": stmt(
                GROUP_NOTE,
                group=("note",),
                having=cmp(">", F("n"), L(2)),
                table="TE",
            ),
            "cut overflow": stmt(
                GROUP_NOTE,
                group=("note",),
                order=(("n", True), ("note", False)),
                limit=1,
                table="TE",
            ),
        },
        ("forward",),
    ),
}
# The two admitted outcomes of an out-of-range group that a having on another
# output removes or that lies beyond the limit (section 4f).
EITHER = ("filtered overflow forward", "cut overflow forward")


def _having(having: Any, **parts: Any) -> dict:
    return stmt(GROUP_NOTE, group=("note",), having=having, **parts)


LOW_NOTE = [("note", F("note")), ("low", agg("min", "price"))]


C18 = {
    **{
        name: spec
        for op in OPS
        for name, spec in (
            (f"n {op} literal forward", _having(cmp(op, F("n"), L(2)))),
            (
                f"n {op} param forward",
                _having(
                    cmp(op, F("n"), P("k")), params=(("k", "Int"),), values={"k": 2}
                ),
            ),
            (f"total {op} literal forward", _having(cmp(op, F("total"), L(15)))),
            (
                f"total {op} param forward",
                _having(
                    cmp(op, F("total"), P("t")),
                    params=(("t", "Int"),),
                    values={"t": 15},
                ),
            ),
        )
    },
    **_orders(
        {
            "none": _having(cmp(">", F("n"), L(100))),
            # The language admits neither `not`, a null test nor a signed
            # literal in a having (PIE-S2327); a NULL total is unknown in each
            # comparison.
            "logic": _having(
                (
                    "or",
                    ("and", cmp(">", F("n"), L(1)), cmp(">=", F("total"), L(0))),
                    cmp("<", F("total"), L(3)),
                )
            ),
            "labels": stmt(
                [("c0", F("note")), ("C2", COUNT), ("c1", agg("sum", "amount"))],
                group=("note",),
                having=("and", cmp(">=", F("C2"), L(2)), cmp(">", F("c1"), L(0))),
            ),
            # v7: a having over a Text and a Bool key and a Float min.
            "note > literal": _having(cmp(">", F("note"), L("a"))),
            "ok == literal": stmt(
                [("ok", F("ok")), ("n", COUNT)],
                group=("ok",),
                having=cmp("==", F("ok"), L(True)),
            ),
            "low < literal": stmt(
                LOW_NOTE, group=("note",), having=cmp("<", F("low"), L(0.0))
            ),
            "low == param": stmt(
                LOW_NOTE,
                group=("note",),
                having=cmp("==", F("low"), P("z")),
                params=(("z", "Float"),),
                values={"z": -0.0},
            ),
        }
    ),
}

C19 = {
    **_orders(
        {
            f"{field} {'desc' if desc else 'asc'}": stmt(
                reads("id", field), order=((field, desc),)
            )
            for field in ("amount", "note", "ok", "price")
            for desc in (False, True)
        }
    ),
    **_orders(
        {
            "multi": stmt(reads("id", "note"), order=(("note", True), ("id", False))),
            "tie boundary": stmt(
                reads("id", "price"), order=(("price", False),), limit=4
            ),
            "grouped": stmt(
                GROUP_NOTE,
                group=("note",),
                order=(("total", True), ("note", False)),
                limit=5,
            ),
            "labels": stmt(
                [("c1", F("note")), ("C0", COUNT), ("c2", agg("sum", "amount"))],
                group=("note",),
                order=(("C0", True), ("c1", False)),
            ),
        }
    ),
    **_orders(
        {
            "limit 0": stmt(reads("id"), order=(("id", False),), limit=0),
            "limit over": stmt(reads("id", "note"), order=(("id", False),), limit=100),
            "no order limit": stmt(reads("id", "note"), limit=3),
        },
        ("forward",),
    ),
}

# (field, its type, a literal of it, the parameter's value) for C20's grid.
GRID = (
    ("amount", "Int", L(5), 5),
    ("note", "Text", L("a"), "a"),
    ("ok", "Bool", L(True), True),
    ("price", "Float", L(0.0), -0.0),
)
MANY = (
    ("lo", "Int"),
    ("hi", "Int"),
    ("label", "Text"),
    ("flag", "Bool"),
    ("cap", "Float"),
)
MANY_WHERE = (
    "or",
    (
        "or",
        (
            "or",
            ("and", cmp("<=", P("lo"), F("amount")), cmp("<=", F("amount"), P("hi"))),
            ("and", cmp("==", F("note"), P("label")), cmp("==", F("ok"), P("flag"))),
        ),
        cmp(">", F("price"), P("cap")),
    ),
    cmp("==", F("amount"), P("lo")),
)
MANY_VALUES = {
    "s1": {"lo": -(2**63), "hi": 2**63 - 1, "label": "a\0", "flag": False, "cap": -0.0},
    "s2": {"lo": 5, "hi": 15, "label": "é", "flag": True, "cap": 2.5},
    "s3": {"lo": 2**63 - 1, "hi": -(2**63), "label": "", "flag": True, "cap": 1.5},
}
LONG_TENTH = "0.1000000000000000055511151231257827021181583404541015625"
NUL_LITERAL = cmp("==", F("note"), L("a\0b"))


def _where(where: tuple, **parts: Any) -> dict:
    return stmt(reads("id", "note"), where=where, **parts)


C20 = {
    **_orders(
        {
            name: spec
            for field, kind, literal, value in GRID
            for op in OPS
            for name, spec in (
                (
                    f"{field} {op} literal",
                    stmt(reads("id", field), where=cmp(op, F(field), literal)),
                ),
                (
                    f"{field} {op} param",
                    stmt(
                        reads("id", field),
                        where=cmp(op, F(field), P("p")),
                        params=(("p", kind),),
                        values={"p": value},
                    ),
                ),
            )
        }
    ),
    **_orders(
        {
            "left literal": _where(cmp("<", L(5), F("amount"))),
            "3vl and or": _where(
                (
                    "or",
                    ("and", cmp(">", F("amount"), L(0)), null(F("note"), True)),
                    ("not", cmp("==", F("ok"), L(True))),
                )
            ),
            "3vl not": _where(
                (
                    "not",
                    ("or", cmp("<", F("price"), L(1.0)), cmp("==", F("note"), L("a"))),
                )
            ),
            "amount is None": _where(null(F("amount"))),
            "note is not None": _where(null(F("note"), True)),
            "ok is None": _where(null(F("ok"))),
            "price is None": _where(null(F("price"))),
            **{
                f"params {name}": _where(MANY_WHERE, params=MANY, values=values)
                for name, values in MANY_VALUES.items()
            },
            **{
                f"lit {name}": _where(where, table="TL")
                for name, where in (
                    ("int min", cmp("==", F("amount"), L(-(2**63)))),
                    ("int max", cmp("==", F("amount"), L(2**63 - 1))),
                    (
                        "quotes",
                        (
                            "or",
                            cmp("==", F("note"), L("it's")),
                            cmp("==", F("note"), L('say "hi"')),
                        ),
                    ),
                    ("backslash", cmp("==", F("note"), L("a\\b"))),
                    ("zero", cmp("==", F("price"), L(-0.0))),
                    ("tiny", cmp("==", F("price"), L(0.000001, "0.000001"))),
                    ("long", cmp("==", F("price"), L(0.1, LONG_TENTH))),
                    ("multibyte", cmp(">", F("note"), L("z"))),
                )
            },
        }
    ),
    "lit nul forward": _where(NUL_LITERAL, table="TL"),
}
# Compiled and refused at compile time (rule 8b): no attempt.
REFUSED = ("lit nul forward",)

C21 = {
    "count": stmt(
        [
            ("n", COUNT),
            ("total", agg("sum", "amount")),
            ("low", agg("min", "price")),
            ("high", agg("max", "id")),
        ]
    ),
    "group": stmt(
        [*reads("note"), ("n", COUNT)],
        group=("note",),
        order=(("note", True),),
        limit=2,
    ),
    "sort": stmt(reads("id"), order=(("note", True),), digest=True),
    "bool": stmt(
        [
            *reads("ok"),
            ("n", COUNT),
            ("total", agg("sum", "amount")),
            ("low", agg("min", "price")),
        ],
        group=("ok",),
        order=(("ok", False),),
    ),
}
for _spec in C21.values():
    _spec.update(project="P0", table="CAPACITY")

# Rule two (section 4j): each family's form beside a computed output, which
# rule 7 refuses at that output on main and on this tree; B1 is the same
# output beside B1's filter. v7: tier 2 admits `amount + 1` as arithmetic
# (refused by rule 7c's range), so the output nests two operations.
COMPUTED = "more = amount + id + 1"
RULE_TWO = {
    "B1": stmt(
        [*reads("id"), ("more", ("raw", COMPUTED))],
        project="P0",
        params=(("min_amount", "Int"),),
        where=cmp(">=", F("amount"), P("min_amount")),
    ),
    "A1": stmt(
        [*reads("note"), ("n", COUNT), ("more", ("raw", "more = count() + 1"))],
        project="P0",
        group=("note",),
    ),
    "A2": stmt(
        [*GROUP_NOTE, ("more", ("raw", "more = sum(amount) + 1"))],
        project="P0",
        group=("note",),
        params=(("low", "Int"),),
        having=("and", cmp(">", F("n"), L(1)), cmp(">=", F("total"), P("low"))),
    ),
    "A3": stmt(
        [*reads("id", "note"), ("more", ("raw", COMPUTED))],
        project="P0",
        order=(("note", True), ("id", False)),
        limit=3,
    ),
    "A4": stmt(
        [*reads("id"), ("more", ("raw", COMPUTED))],
        project="P0",
        params=(("low", "Int"), ("label", "Text")),
        where=(
            "or",
            (
                "and",
                cmp(">=", F("amount"), P("low")),
                ("not", cmp("==", F("note"), P("label"))),
            ),
            cmp("<", F("price"), L(2.5)),
        ),
    ),
}

# B2 forms on every other entry point (section 4i).
B2_FORMS = {
    "grouped": _having(
        cmp(">=", F("total"), P("t")), params=(("t", "Int"),), values={"t": 0}
    ),
    "ordered": stmt(reads("id", "note"), order=(("note", True),), limit=3),
    "filtered": _where(MANY_WHERE, params=MANY, values=MANY_VALUES["s2"]),
}

# Tier 2 (sections 4l-4r): shapes as (field, type, optional), each Int's
# int_range where it is not all of signed 64 bits, and declared keys.
MAX_FLOAT = 1.7976931348623157e308
# The largest Int whose square fits signed 64 bits.
ROOT_63 = 3037000499
T2_SHAPES = {
    "Event": (
        ("id", "Int", False),
        ("day", "Date", True),
        ("at", "Timestamp", True),
        ("cost", "Decimal(12, 2)", True),
        ("big", "Decimal(38, 10)", False),
    ),
    "Pair": (
        ("id", "Int", False),
        ("a", "Int", True),
        ("b", "Int", True),
        ("r", "Int", False),
        ("x", "Float", True),
        ("y", "Float", True),
    ),
    "Order": (
        ("id", "Int", False),
        ("amount", "Int", True),
        ("note", "Text", True),
        ("ok", "Bool", True),
        ("price", "Float", True),
    ),
    "Customer": (
        ("id", "Int", False),
        ("name", "Text", False),
        ("rate", "Float", True),
    ),
    "Rate": (("r", "Float", True), ("tag", "Text", False)),
    "Visit": (
        ("day", "Date", True),
        ("at", "Timestamp", False),
        ("n", "Int", False),
        ("cost", "Decimal(12, 2)", True),
    ),
    "Account": (("id", "Int", False), ("name", "Text", False)),
    "Handle": (("h", "Text", False), ("n", "Int", False)),
    # Rule 10: a Decimal beyond 38 digits, which DuckDB cannot store.
    "Wide": (("id", "Int", False), ("big", "Decimal(39, 2)", False)),
}
T2_RANGES = {
    ("Pair", "a"): (-(2**62), 2**62),
    ("Pair", "b"): (-(2**62), 2**62 - 1),
    ("Pair", "r"): (-ROOT_63, ROOT_63),
    ("Order", "amount"): (-1000, 1000),
    ("Customer", "id"): (-1000, 1000),
}
T2_KEYS = {"Customer": ("id",), "Rate": ("r",), "Account": ("id",), "Handle": ("h",)}
# Each project's sources: (name, shape, key).
T2_PROJECTS = {
    "PT": (("orders", "Event", "orders"),),
    "PA": (("orders", "Pair", "orders"),),
    "PJ": (
        ("orders", "Order", "orders"),
        ("customers", "Customer", "customers"),
        ("buyers", "Customer", "customers"),
        ("rates", "Rate", "rates"),
        ("visits", "Visit", "visits"),
        ("stays", "Visit", "stays"),
        ("accounts", "Account", "accounts"),
        ("handles", "Handle", "handles"),
    ),
    "PD": (("orders", "Wide", "orders"),),
}


def decimal_of(kind: str) -> tuple[int, int]:
    """(precision, scale) of `Decimal(p, s)`."""
    precision, scale = (int(k) for k in kind[8:-1].split(","))
    return precision, scale


def t2_contract(project: str) -> dict:
    """A tier 2 project's contract: every source in declaration order."""
    document = contract("P0")
    document["sources"] = [
        {
            "selector": {"module": "main.pietto", "kind": "source", "name": name},
            "relation": {"namespace": "arrow", "name": key},
            "scan": "arrow_registration",
            "fields": [
                {
                    "ordinal": i,
                    "name": field,
                    "column": field,
                    "representation": _representation(
                        kind, nullable, T2_RANGES.get((shape, field), INT64)
                    ),
                }
                for i, (field, kind, nullable) in enumerate(T2_SHAPES[shape])
            ],
            "premises": [
                {"key": premise, "scope": "source", "value": True}
                for premise in ("row_domain_matches", "read_only_object")
            ],
        }
        for name, shape, key in T2_PROJECTS[project]
    ]
    return document


def arrow_type(pa: Any, kind: str) -> Any:
    if kind.startswith("Decimal("):
        return pa.decimal128(*decimal_of(kind))
    if kind == "Timestamp":
        return pa.timestamp("us")
    names = {"Int": "int64", "Text": "string", "Bool": "bool_", "Float": "float64"}
    return getattr(pa, names.get(kind, "date32"))()


def shaped(pa: Any, shape: str, rows: Any, **columns: Any) -> Any:
    """The table of a tier 2 shape's `rows`, each named column replaced."""
    rows = tuple(rows)
    arrays = {
        name: pa.array([row[k] for row in rows], type=arrow_type(pa, kind))
        for k, (name, kind, _nullable) in enumerate(T2_SHAPES[shape])
    }
    arrays.update(columns)
    return pa.table(arrays)


def quantized(value: Any, kind: str) -> Any:
    """A fixture value as the column delivers it: a Decimal at its scale."""
    if value is None or not kind.startswith("Decimal("):
        return value
    with localcontext() as context:
        context.prec = 80
        return value.quantize(Decimal(1).scaleb(-decimal_of(kind)[1]))


def D(text: str) -> tuple:
    return L(date.fromisoformat(text), f'"{text}"')


def TS(text: str) -> tuple:
    return L(datetime.fromisoformat(text), f'"{text}"')


def DEC(spelling: str) -> tuple:
    """A number literal beside a Decimal: its exact decimal value."""
    return L(Decimal(spelling.replace("_", "")), spelling)


def A(op: str, a: tuple, b: tuple) -> tuple:
    return ("arith", op, a, b)


def NEG(a: tuple) -> tuple:
    return ("neg", a)


def POS(a: tuple) -> tuple:
    return ("pos", a)


def raw(label: str, text: str) -> tuple:
    return (label, ("raw", text))


# Written out: Decimal arithmetic would round to the default 28 digits.
BIG = Decimal("9999999999999999999999999999.9999999999")
LEAST = Decimal("-9999999999999999999999999999.9999999999")
# Tier 2 tables: (shape, rows).
T2_TABLES: dict[str, Any] = {
    "TT": (
        "Event",
        (
            (
                1,
                date(1000, 1, 1),
                datetime(1000, 1, 1),
                Decimal("-9999999999.99"),
                LEAST,
            ),
            (
                2,
                date(9999, 12, 31),
                datetime(9999, 12, 31, 23, 59, 59, 499999),
                Decimal("9999999999.99"),
                BIG,
            ),
            (
                3,
                None,
                datetime(2024, 1, 1, 10, 0, 0, 500000),
                Decimal("0.12"),
                Decimal("0.0000000001"),
            ),
            (4, date(2024, 1, 1), None, None, Decimal("0")),
            (
                5,
                date(2024, 2, 29),
                datetime(2024, 1, 1),
                Decimal("0.13"),
                Decimal("-0.0000000001"),
            ),
            (
                6,
                date(1970, 1, 1),
                datetime(1970, 1, 1, 0, 0, 0, 1),
                Decimal("-0.01"),
                Decimal("1"),
            ),
            (
                7,
                date(2024, 1, 1),
                datetime(2024, 1, 1, 10, 0, 0, 500000),
                Decimal("0.12"),
                Decimal("1"),
            ),
            (8, None, None, Decimal("0.00"), Decimal("0.0000000001")),
        ),
    ),
    # (id, a, b, r, x, y): Int results at both ends of signed 64 bits, the
    # sign of each zero, subnormal products and NULL operands.
    "TA": (
        "Pair",
        (
            (1, 2**62, 2**62 - 1, ROOT_63, 1.5, 2.25),
            (2, -(2**62), -(2**62), -ROOT_63, -0.0, 0.0),
            (3, None, 5, 0, None, 1.0),
            (4, 0, -(2**62), 1, 5e-324, 0.75),
            (5, 7, None, -1, 2.2250738585072014e-308, 0.5),
            (6, -1, 1, 2, 0.0, 1e-200),
            (7, 1, -1, 3, 0.1, 0.2),
            (8, 2, 3, ROOT_63, -0.0, -0.0),
            (9, -(2**62), 2**62 - 1, -ROOT_63, MAX_FLOAT / 2, 0.5),
            (10, 2**62, -(2**62), 5, -1.0, None),
        ),
    ),
    # Group keys (r, x): -0.0 and 0.0 in one group, -0.0 alone in another.
    "TG": (
        "Pair",
        tuple(
            (k, 0, 0, r, x, 0.0)
            for k, (r, x) in enumerate(
                [(2, -0.0), (2, 0.0), (3, 1.5), (3, 1.5), (ROOT_63, None)]
                + [(-ROOT_63, 2.5), (5, -0.0)]
            )
        ),
    ),
    **{
        name: ("Pair", ((1, 0, 0, 0, x, y),))
        for name, (x, y) in {
            "F add": (MAX_FLOAT, MAX_FLOAT),
            "F sub": (-MAX_FLOAT, MAX_FLOAT),
            "F mul": (1e200, 1e200),
            "F lit": (MAX_FLOAT, 1.0),
            "U mul": (1e-200, 1e-200),
            "U signed": (-1e-200, 1e-200),
            "U subnormal": (5e-324, 0.5),
        }.items()
    },
    # 2,048 rows that add to 2.0, then one whose sum leaves binary64.
    "F later": (
        "Pair",
        tuple((k, 0, 0, 0, 1.0, 1.0) for k in range(2048))
        + ((2048, 0, 0, 0, MAX_FLOAT, MAX_FLOAT),),
    ),
    "JO": (
        "Order",
        (
            (1, 5, "a", True, 1.5),
            (2, 10, None, False, -0.0),
            (3, 15, "c", True, 0.0),
            (4, None, "a", None, 2.5),
            (5, 5, "é", False, None),
            (6, 99, "z", True, -1.0),
        ),
    ),
    "JC": (
        "Customer",
        (
            (1, "p", 2.5),
            (5, "a", 0.5),
            (10, "x", None),
            (15, "c", -0.0),
            (20, "a", 1.0),
        ),
    ),
    # A declared key broken: id 5 twice.
    "JC dup": ("Customer", ((5, "a", 0.5), (5, "b", 1.0), (10, "x", None))),
    # 300 customers of id 5: a JOIN without an aggregate repeats rows.
    "JC fan": ("Customer", tuple((5, f"n{k}", None) for k in range(300))),
    "JR": (
        "Rate",
        ((0.0, "zero"), (2.5, "two"), (None, "n1"), (None, "n2"), (-1.0, "neg")),
    ),
    # A Float key broken under ==: -0.0 and 0.0.
    "JR zeros": ("Rate", ((0.0, "zero"), (-0.0, "minus"), (2.5, "two"))),
    "JV": (
        "Visit",
        (
            (date(2024, 1, 1), datetime(2024, 1, 1), 1, Decimal("1.00")),
            (None, datetime(2024, 1, 2), 2, None),
            (date(1000, 1, 1), datetime(1000, 1, 1), 3, Decimal("2.50")),
        ),
    ),
    "JS": (
        "Visit",
        (
            (date(2024, 1, 1), datetime(1000, 1, 1), 10, Decimal("1.00")),
            (None, datetime(2024, 1, 2), 20, None),
            (date(9999, 12, 31), datetime(2024, 1, 1), 30, Decimal("3.00")),
        ),
    ),
}


# Distinct Text keys under ==: case and a trailing NUL make other values.
T2_TABLES["JH"] = ("Handle", (("a", 1), ("A", 2), ("a\0", 3), ("z", 4)))
# MUCH_LATER rows that add to 2.0, then one whose sum leaves binary64: DuckDB
# reads the first 104,448 ahead in its reader, so batches are delivered
# before the failing row is read (observed on 2.0.0 before the freeze).
MUCH_LATER = 131_072
T2_TABLES["F much later"] = (
    "Pair",
    tuple((k, 0, 0, 0, 1.0, 1.0) for k in range(MUCH_LATER))
    + ((MUCH_LATER, 0, 0, 0, MAX_FLOAT, MAX_FLOAT),),
)


def t2_rows(name: str, order: str) -> tuple:
    rows = T2_TABLES[name][1]
    return rows[::-1] if order == "reversed" else rows


def _typed(select: list, **parts: Any) -> dict:
    return stmt(select, project="PT", inputs={"orders": "TT"}, **parts)


TYPED_WHERES = {
    "day >= literal": cmp(">=", F("day"), D("2024-01-01")),
    "literal == day": cmp("==", D("1000-01-01"), F("day")),
    "day != literal": cmp("!=", F("day"), D("2024-02-29")),
    "day < literal": cmp("<", F("day"), D("1970-01-02")),
    "at < literal": cmp("<", F("at"), TS("2024-01-01 10:00:00.5")),
    "at == literal": cmp("==", F("at"), TS("9999-12-31 23:59:59.499999")),
    "at >= literal": cmp(">=", F("at"), TS("1970-01-01 00:00:00")),
    "cost > literal": cmp(">", F("cost"), DEC("0.125")),
    "cost == literal": cmp("==", F("cost"), DEC("0.120")),
    "cost != literal": cmp("!=", F("cost"), DEC("0.13")),
    "cost <= underscored": cmp("<=", F("cost"), DEC("-9_999_999_999.99")),
    "cost >= signed": cmp(">=", F("cost"), DEC("-0.01")),
    "big > literal": cmp(">", F("big"), DEC("0.0000000001")),
    "big < literal": cmp("<", F("big"), DEC(str(BIG))),
    "big > signed int": cmp(">", F("big"), DEC("-1")),
    "big <= underscored int": cmp("<=", F("big"), DEC("1_000")),
    "day is None": null(F("day")),
    "at is None": null(F("at")),
    "cost is not None": null(F("cost"), True),
}
TYPED_PARAMS = (
    ("since", "Timestamp"),
    ("on", "Date"),
    ("floor", "Decimal(38, 10)"),
)
TYPED_PARAM_WHERE = (
    "or",
    ("or", cmp(">=", F("at"), P("since")), cmp("==", F("day"), P("on"))),
    cmp(">=", F("big"), P("floor")),
)
TYPED_VALUES = {
    "s1": {
        "since": datetime(9999, 12, 31),
        "on": date(1000, 1, 1),
        # More than 38 digits with its trailing zeros; one value of (38, 10).
        "floor": Decimal("9999999999999999999999999999.99999999990000"),
    },
    "s2": {
        "since": datetime(2024, 1, 1, 10, 0, 0, 500000),
        "on": date(2024, 2, 29),
        "floor": Decimal("1"),
    },
}
TYPED_NAMES = ("day", "at", "cost", "big")
C23 = {
    **_orders(
        {
            "read": _typed(reads("id", *TYPED_NAMES)),
            **{name: _typed(reads("id"), where=w) for name, w in TYPED_WHERES.items()},
            **{
                f"params {name}": _typed(
                    reads("id"),
                    where=TYPED_PARAM_WHERE,
                    params=TYPED_PARAMS,
                    values=values,
                )
                for name, values in TYPED_VALUES.items()
            },
            "param cost": _typed(
                reads("id", "cost"),
                where=cmp("==", F("cost"), P("c")),
                params=(("c", "Decimal(12, 2)"),),
                values={"c": Decimal("0.12")},
            ),
            "group day": _typed(
                [
                    *reads("day"),
                    ("n", COUNT),
                    ("filled", agg("count", "cost")),
                    ("first", agg("min", "at")),
                    ("last", agg("max", "at")),
                    ("low", agg("min", "cost")),
                    ("top", agg("max", "big")),
                ],
                group=("day",),
            ),
            "group cost": _typed(
                [*reads("cost"), ("n", COUNT), ("early", agg("min", "day"))],
                group=("cost",),
            ),
            "global": _typed(
                [
                    ("n", COUNT),
                    ("lo", agg("min", "day")),
                    ("hi", agg("max", "day")),
                    ("first", agg("min", "at")),
                    ("last", agg("max", "at")),
                    ("low", agg("min", "cost")),
                    ("high", agg("max", "cost")),
                    ("bottom", agg("min", "big")),
                    ("top", agg("max", "big")),
                ]
            ),
            **{
                f"{field} {'desc' if desc else 'asc'}": _typed(
                    reads("id", field), order=((field, desc),)
                )
                for field in TYPED_NAMES
                for desc in (False, True)
            },
            "order limit": _typed(
                reads("id", "day"), order=(("day", True), ("id", False)), limit=3
            ),
        }
    ),
    **_orders(
        {
            "bad date": _typed(
                reads("id"), where=cmp("==", F("day"), L(None, '"2024-02-30"'))
            ),
            "T separator": _typed(
                reads("id"), where=cmp("==", F("at"), L(None, '"2024-01-01T10:00:00"'))
            ),
            "wide decimal": _typed(
                reads("id"), where=cmp(">", F("big"), DEC("0.12345678901"))
            ),
            "having timestamp": _typed(
                [*reads("day"), ("first", agg("min", "at"))],
                group=("day",),
                having=cmp(">", F("first"), TS("2024-01-01 00:00:00")),
            ),
            "sum decimal": _typed([("total", agg("sum", "cost"))]),
            # Rules 9 and 10 with their tier 2 suggestions (D79.26).
            "parameter unread": _typed(
                reads("id"), params=(("m", "Int"),), values={"m": 1}
            ),
            "field beyond 38 digits": stmt(reads("id"), project="PD"),
        },
        ("forward",),
    ),
}


def _pair(select: list, table: str = "TA", **parts: Any) -> dict:
    return stmt(select, project="PA", inputs={"orders": table}, **parts)


ARITH_ALL = [
    *reads("id"),
    ("s", A("+", F("a"), F("b"))),
    ("d", A("-", F("b"), F("a"))),
    ("m", A("*", F("r"), F("r"))),
    ("e", A("*", F("r"), L(ROOT_63))),
    ("z", A("+", F("a"), L(0))),
    ("fs", A("+", F("x"), F("y"))),
    ("fd", A("-", F("x"), F("y"))),
    ("fm", A("*", F("x"), F("y"))),
    ("n", NEG(F("x"))),
    ("p", POS(F("x"))),
    ("k", A("*", F("x"), L(-2.0, "-2.0"))),
]
FLOAT_PARAM = [
    *reads("id"),
    ("q", A("+", F("x"), P("c"))),
    ("w", A("*", P("c"), F("y"))),
]
C24 = {
    **_orders(
        {
            "all": _pair(ARITH_ALL),
            **{
                f"param {name}": _pair(
                    FLOAT_PARAM, params=(("c", "Float"),), values={"c": value}
                )
                for name, value in (("-0.0", -0.0), ("1e300", 1e300))
            },
            "grouped": _pair(
                [
                    *reads("r", "x"),
                    ("t", A("*", F("r"), F("r"))),
                    ("f", A("*", F("x"), F("x"))),
                    ("g", NEG(F("x"))),
                    ("h", POS(F("x"))),
                    ("n", COUNT),
                ],
                "TG",
                group=("r", "x"),
            ),
        }
    ),
    **_orders(
        {
            **{
                f"{name}": _pair([*reads("id"), (label, value)], table)
                for name, label, value, table in (
                    ("overflow +", "fs", A("+", F("x"), F("y")), "F add"),
                    ("overflow -", "fd", A("-", F("x"), F("y")), "F sub"),
                    ("overflow *", "fm", A("*", F("x"), F("y")), "F mul"),
                    ("overflow literal", "k", A("*", F("x"), L(-2.0, "-2.0")), "F lit"),
                    ("underflow", "fm", A("*", F("x"), F("y")), "U mul"),
                    ("underflow signed", "fm", A("*", F("x"), F("y")), "U signed"),
                    (
                        "underflow subnormal",
                        "fm",
                        A("*", F("x"), F("y")),
                        "U subnormal",
                    ),
                    ("overflow later", "fs", A("+", F("x"), F("y")), "F later"),
                    (
                        "overflow after batches",
                        "fs",
                        A("+", F("x"), F("y")),
                        "F much later",
                    ),
                )
            },
            # inf - inf: no nesting reaches it, and no infinity enters.
            "inf minus inf": _pair([*reads("id"), raw("t", "t = (x + y) - (x + y)")]),
            "int sign": _pair([*reads("id"), raw("t", "t = -a")]),
            "range": _pair([*reads("id"), raw("t", "t = a + a")]),
            "int param": _pair(
                [*reads("id"), raw("t", "t = r + k")],
                params=(("k", "Int"),),
                values={"k": 1},
            ),
            "division": _pair([*reads("id"), raw("t", "t = x / y")]),
            "mixed": _pair([*reads("id"), raw("t", "t = a + 1.5")]),
            **{
                f"{name} parameter": _pair(
                    FLOAT_PARAM, params=(("c", "Float"),), values={"c": value}
                )
                for name, value in (("inf", math.inf), ("nan", math.nan))
            },
        },
        ("forward",),
    ),
}


def _joined(select: list, inputs: dict, **parts: Any) -> dict:
    return stmt(select, project="PJ", inputs=inputs, **parts)


def _self(select: list, join: tuple, **parts: Any) -> dict:
    """`orders` read twice, the second time through the alias `o2`."""
    return _joined(
        select, {"orders": "JO"}, lets=("let o2 = orders",), joins=(join,), **parts
    )


OC = {"orders": "JO", "customers": "JC"}
ON_AMOUNT = (("orders.amount", "customers.id"),)
INNER = ("inner", "customers", ON_AMOUNT)
NAMED = [("id", F("orders.id")), ("name", F("customers.name"))]
C26 = {
    **_orders(
        {
            "inner": _joined(
                [*NAMED, ("rate", F("customers.rate"))], OC, joins=(INNER,)
            ),
            "inner swapped": _joined(
                [*NAMED, ("rate", F("customers.rate"))], OC, joins=(INNER,), swap=True
            ),
            "left": _joined(
                [*NAMED, ("rate", F("customers.rate"))],
                OC,
                joins=(("left", "customers", ON_AMOUNT),),
            ),
            "two keys": _joined(
                NAMED,
                OC,
                joins=(
                    (
                        "inner",
                        "customers",
                        (*ON_AMOUNT, ("customers.name", "orders.note")),
                    ),
                ),
            ),
            "shared input": _joined(
                [*NAMED, ("buyer", F("buyers.name"))],
                OC,
                joins=(INNER, ("left", "buyers", (("buyers.id", "orders.id"),))),
            ),
            "float key": _joined(
                [("id", F("orders.id")), ("tag", F("rates.tag"))],
                {"orders": "JO", "rates": "JR"},
                joins=(("inner", "rates", (("orders.price", "rates.r"),)),),
            ),
            "date key": _joined(
                [("a", F("visits.n")), ("b", F("stays.n"))],
                {"visits": "JV", "stays": "JS"},
                joins=(("inner", "stays", (("visits.day", "stays.day"),)),),
                **{"from": "visits"},
            ),
            "timestamp key": _joined(
                [("a", F("visits.n")), ("b", F("stays.n"))],
                {"visits": "JV", "stays": "JS"},
                joins=(("left", "stays", (("stays.at", "visits.at"),)),),
                **{"from": "visits"},
            ),
            "where": _joined(
                NAMED,
                OC,
                joins=(INNER,),
                where=(
                    "or",
                    cmp(">", F("customers.rate"), L(0.0)),
                    null(F("orders.note")),
                ),
            ),
            "grouped": _joined(
                [
                    ("name", F("customers.name")),
                    ("n", COUNT),
                    ("total", agg("sum", "orders.amount")),
                    ("top", agg("max", "orders.price")),
                ],
                OC,
                joins=(INNER,),
                group=("customers.name",),
                having=cmp(">=", F("total"), L(5)),
                order=(("total", True),),
            ),
            "arithmetic": _joined(
                [
                    ("id", F("orders.id")),
                    ("s", A("+", F("orders.amount"), F("customers.id"))),
                    ("r", A("*", F("customers.rate"), F("orders.price"))),
                ],
                OC,
                joins=(("left", "customers", ON_AMOUNT),),
            ),
            "ordered limit": _joined(
                NAMED, OC, joins=(INNER,), order=(("orders.id", True),), limit=2
            ),
            # One source read twice through a row-input alias (D79.29).
            "self join": _self(
                [("id", F("orders.id")), ("other", F("o2.note"))],
                ("inner", "o2", (("orders.id", "o2.amount"),)),
            ),
            "left self join": _self(
                [
                    ("id", F("orders.id")),
                    ("note", F("orders.note")),
                    ("other", F("o2.id")),
                ],
                ("left", "o2", (("o2.id", "orders.amount"),)),
            ),
            "self join arithmetic": _self(
                [
                    ("id", F("orders.id")),
                    ("s", A("+", F("orders.amount"), F("o2.amount"))),
                    ("p", A("*", F("orders.price"), F("o2.price"))),
                ],
                ("left", "o2", (("o2.id", "orders.amount"),)),
            ),
            "bool key": _self(
                [("a", F("orders.id")), ("b", F("o2.id"))],
                ("inner", "o2", (("o2.ok", "orders.ok"),)),
            ),
            # Labels named like a capture column or a registered name.
            "labels": _joined(
                [
                    ("c1", F("orders.id")),
                    ("pietto_arrow_0", F("customers.name")),
                    ("c0", F("customers.rate")),
                ],
                OC,
                joins=(INNER,),
            ),
            # An inner JOIN's on makes a direct read of its key non-null, but
            # not an arithmetic value that reads it (section 4n).
            "inner key read": _joined(
                [
                    ("a", F("orders.amount")),
                    ("k", F("customers.id")),
                    ("s", A("+", F("orders.amount"), F("customers.id"))),
                ],
                OC,
                joins=(INNER,),
            ),
        }
    ),
    **_orders(
        {
            "right join": _joined(
                NAMED,
                OC,
                joins=("right join customers on orders.amount == customers.id",),
            ),
            "decimal key": _joined(
                [("a", F("visits.n"))],
                {"visits": "JV", "stays": "JS"},
                joins=("inner join stays on stays.cost == visits.cost",),
                **{"from": "visits"},
            ),
            "namespace": _joined(
                NAMED, OC, joins=(INNER,), namespace={"customers": "main"}
            ),
            # A refused JOIN beside rule 9 or 8b in its on (section 4p).
            "right join parameter": _joined(
                NAMED,
                OC,
                joins=(
                    "right join customers on orders.amount == customers.id"
                    " and customers.id == m",
                ),
                params=(("m", "Int"),),
                values={"m": 5},
            ),
            "right join nul": _joined(
                NAMED,
                OC,
                joins=(
                    "right join customers on orders.amount == customers.id"
                    ' and customers.name == "a\0b"',
                ),
            ),
        },
        ("forward",),
    ),
}
C23.update(
    {
        f"bind {name} forward": _typed(
            reads("id"),
            where=TYPED_PARAM_WHERE,
            params=TYPED_PARAMS,
            values={**TYPED_VALUES["s1"], **change},
        )
        for name, change in (
            ("date as datetime", {"on": datetime(2024, 1, 1)}),
            ("zoned timestamp", {"since": datetime(2024, 1, 1, tzinfo=timezone.utc)}),
            (
                "timestamp past the end",
                {"since": datetime(9999, 12, 31, 23, 59, 59, 500000)},
            ),
            ("decimal scale", {"floor": Decimal("0.00000000001")}),
            ("decimal nan", {"floor": Decimal("NaN")}),
        )
    }
)
RATES_COUNT = [("n", COUNT)]
# customers read twice, grouped: each read's declared key is checked.
SELF_KEY = _joined(
    [("name", F("customers.name")), ("n", COUNT)],
    {"customers": "JC"},
    lets=("let c2 = customers",),
    joins=(("inner", "c2", (("c2.id", "customers.id"),)),),
    group=("customers.name",),
    **{"from": "customers"},
)
ON_RATE = (("inner", "rates", (("orders.price", "rates.r"),)),)
GROUPED_BUYERS = [("name", F("buyers.name")), ("n", COUNT)]
C26.update(
    {
        **_orders(
            {
                "key nulls": _joined(
                    RATES_COUNT, {"orders": "JO", "rates": "JR"}, joins=ON_RATE
                ),
                "key without aggregate": _joined(
                    NAMED, {"orders": "JO", "customers": "JC dup"}, joins=(INNER,)
                ),
                "self join key check": SELF_KEY,
                # 'a', 'A' and 'a\0' are three values of a Text key.
                "text key distinct": _joined(
                    [("h", F("handles.h")), ("n", COUNT)],
                    {"orders": "JO", "handles": "JH"},
                    joins=(("inner", "handles", (("handles.h", "orders.note"),)),),
                    group=("handles.h",),
                ),
            }
        ),
        **_orders(
            {
                "key repeated": {
                    **C26["grouped forward"],
                    "inputs": {"orders": "JO", "customers": "JC dup"},
                },
                "key zeros": _joined(
                    RATES_COUNT, {"orders": "JO", "rates": "JR zeros"}, joins=ON_RATE
                ),
                "self join key repeated": {
                    **SELF_KEY,
                    "inputs": {"customers": "JC dup"},
                },
                "key shared input": _joined(
                    GROUPED_BUYERS,
                    {"orders": "JO", "customers": "JC dup"},
                    joins=(("inner", "buyers", (("orders.amount", "buyers.id"),)),),
                    group=("buyers.name",),
                ),
                # 600 JOIN rows under max_rows 500: one batch of 256, then
                # the second would cross it.
                "fan-out cut": _joined(
                    [("id", F("orders.id")), ("who", F("buyers.name"))],
                    {"orders": "JO", "customers": "JC fan"},
                    joins=(("inner", "buyers", (("buyers.id", "orders.amount"),)),),
                    limits={"max_rows": 500},
                ),
            },
            ("forward",),
        ),
    }
)
# Tier 2's statements that compile refuses (each one blocker), and those
# whose request execute() refuses (PIE-R1006).
T2_REFUSED = {
    cell: tuple(f"{name} forward" for name in names)
    for cell, names in (
        (
            "C23",
            (
                "bad date",
                "T separator",
                "wide decimal",
                "having timestamp",
                "sum decimal",
                "parameter unread",
                "field beyond 38 digits",
            ),
        ),
        (
            "C24",
            ("inf minus inf", "int sign", "range", "int param", "division", "mixed"),
        ),
        (
            "C26",
            (
                "right join",
                "decimal key",
                "namespace",
                "right join parameter",
                "right join nul",
            ),
        ),
    )
}
T2_BINDING = {
    "C23": tuple(sub for sub in C23 if sub.startswith("bind ")),
    "C24": ("inf parameter forward", "nan parameter forward"),
}

# Tier 2's rule two forms: each tier 2 family beside the nested output.
RULE_TWO.update(
    {
        "T1": _typed(
            [*reads("id", "day"), raw("more", "more = id + id + 1")],
            where=(
                "and",
                cmp(">=", F("day"), D("2024-01-01")),
                cmp(">", F("big"), DEC("0.5")),
            ),
        ),
        "T2": _pair(
            [
                *reads("id"),
                ("s", A("+", F("a"), F("b"))),
                ("f", A("*", F("x"), F("y"))),
                raw("more", "more = a + b + 1"),
            ]
        ),
        "T3": _joined(
            [*NAMED, raw("more", "more = orders.id + orders.amount + 1")],
            OC,
            joins=(INNER,),
            where=cmp(">", F("customers.rate"), L(0.0)),
        ),
    }
)
B2_FORMS.update(
    {
        "typed": _typed(
            reads("id", "day"),
            where=cmp(">=", F("day"), P("on")),
            params=(("on", "Date"),),
            values={"on": date(2024, 1, 1)},
            order=(("day", False),),
            limit=3,
        ),
        "arithmetic": _pair(ARITH_ALL),
        "joined": C26["inner forward"],
    }
)

B2 = {"C17": C17, "C18": C18, "C19": C19, "C20": C20, "C21": C21, "C22": RULE_TWO}
# Tier 2's statement cells; C25, C27 and C28 have their own sub-cases.
T2 = {"C23": C23, "C24": C24, "C26": C26}

# C25 (section 4o): batch reading at its boundaries.
C25_SUBS = (
    "bytes at the limit",
    "bytes one below",
    "batch bytes one below",
    "bytes in many batches",
    "rows cut",
    "close after the last batch",
    "cancel after the last batch",
    "deadline after the last batch",
    "sum in a later chunk",
    "bytes cut after two batches",
    "reader close fails",
)
# T5's projection of id and note charged as one batch from the reader, with
# a validity bitmap for each column (section 4o): 41 + 25 bytes; the first
# tier cut it from the whole result with no bitmap for id, 65 bytes.
T5_CHARGE = 66
# T5's first two batches of two rows, 27 bytes each: the third crosses it.
BYTES_CUT = 54
# A grouped sum over 50,000 Text keys; one group's sum leaves signed 64 bits.
LATER_GROUPS = 50_000
LATER_OVER = 25_000


def later_rows() -> tuple:
    rows = tuple((k, 1, f"g{k:05d}", True, 0.0) for k in range(LATER_GROUPS))
    return rows + ((LATER_GROUPS, 2**63 - 1, f"g{LATER_OVER:05d}", True, 0.0),)


LATER = stmt(GROUP_NOTE, project="P0", group=("note",))

# C27 (section 4q): typed inputs, input names and the limits over inputs.
TYPED_FORGED = (
    "timestamp ns",
    "timestamp ms",
    "timestamp utc",
    "date64",
    "date as text",
    "decimal precision",
    "decimal scale",
    "decimal256",
    "decimal as float",
    "date before 1000",
    "date after 9999",
    "timestamp past the end",
    "timestamp before 1000",
    "decimal beyond its precision",
    "decimal below its precision",
)
C27_SUBS = (
    *(f"typed:{name}" for name in TYPED_FORGED),
    "typed:edges",
    "names:list",
    "names:repeated",
    "names:missing",
    "names:extra",
    "names:case",
    "names:one in a tuple",
    "rows:each input at the limit",
    "rows:one input beyond",
    "bytes:over all inputs",
    "bytes:shared input once",
    "bytes:self join once",
)


def forged_typed(pa: Any, sub: str) -> Any:
    """C27: a one-row TT table that differs from PT's source in one way."""
    one = T2_TABLES["TT"][1][1:2]
    day, at = pa.array([date(2024, 1, 1)]), pa.array([datetime(2024, 1, 1)])

    def over(value: int, kind: Any) -> Any:
        data = pa.py_buffer(value.to_bytes(16, "little", signed=True))
        return pa.Array.from_buffers(kind, 1, [None, data])

    columns = {
        "timestamp ns": lambda: {"at": at.cast(pa.timestamp("ns"))},
        "timestamp ms": lambda: {"at": at.cast(pa.timestamp("ms"))},
        "timestamp utc": lambda: {"at": at.cast(pa.timestamp("us", tz="UTC"))},
        "date64": lambda: {"day": day.cast(pa.date64())},
        "date as text": lambda: {"day": pa.array(["2024-01-01"])},
        "decimal precision": lambda: {
            "cost": pa.array([Decimal("1")], pa.decimal128(13, 2))
        },
        "decimal scale": lambda: {
            "cost": pa.array([Decimal("1")], pa.decimal128(12, 3))
        },
        "decimal256": lambda: {"cost": pa.array([Decimal("1")], pa.decimal256(12, 2))},
        "decimal as float": lambda: {"cost": pa.array([1.0])},
        "date before 1000": lambda: {"day": pa.array([date(999, 12, 31)], pa.date32())},
        "date after 9999": lambda: {
            "day": pa.array([2_932_897], pa.int32()).cast(pa.date32())
        },
        "timestamp past the end": lambda: {
            "at": pa.array(
                [datetime(9999, 12, 31, 23, 59, 59, 500000)], pa.timestamp("us")
            )
        },
        "timestamp before 1000": lambda: {
            "at": pa.array(
                [datetime(999, 12, 31, 23, 59, 59, 999999)], pa.timestamp("us")
            )
        },
        "decimal beyond its precision": lambda: {
            "cost": over(10**12, pa.decimal128(12, 2))
        },
        "decimal below its precision": lambda: {
            "big": over(-(10**38), pa.decimal128(38, 10))
        },
        # The admitted ends: 12 and 38 digits.
        "edges": lambda: {
            "cost": over(10**12 - 1, pa.decimal128(12, 2)),
            "big": over(-(10**38) + 1, pa.decimal128(38, 10)),
        },
    }
    return shaped(pa, "Event", one, **columns[sub]())


# Each name of bytes:shared input once, and each note of bytes:self join
# once: 1,048,576 customers then measure about 160 MiB and as many orders
# about 168 MiB, within MAX_BYTES once and beyond it twice.
SHARED_NAME_BYTES = 140


def wide_customers(pa: Any, rows: int, size: int) -> Any:
    """`rows` customers of ids k % 1000, each name of `size` UTF-8 bytes."""
    name = _text_of(size).encode()
    return pa.table(
        {
            "id": pa.array([k % 1000 for k in range(rows)], pa.int64()),
            "name": _strings(pa, [name] * rows),
            "rate": pa.array([0.0] * rows, pa.float64()),
        }
    )


def wide_orders(pa: Any, rows: int, size: int) -> Any:
    """`rows` orders of amounts k % 1000, each note of `size` UTF-8 bytes."""
    note = _text_of(size).encode()
    return pa.table(
        {
            "id": pa.array(range(rows), pa.int64()),
            "amount": pa.array([k % 1000 for k in range(rows)], pa.int64()),
            "note": _strings(pa, [note] * rows),
            "ok": pa.array([True] * rows, pa.bool_()),
            "price": pa.array([0.0] * rows, pa.float64()),
        }
    )


# C28 (section 4r): the declared key check's peak at 1,048,576 rows.
C28_SUBS = ("int key", "text key", "no key check", "sorted read", "memory margin")
PEAK_PAD = "\U0001f600" * 48
PEAK = {
    "int key": _joined(
        [("name", F("accounts.name")), ("n", COUNT)],
        {"orders": "JO", "accounts": "accounts"},
        joins=(("inner", "accounts", (("orders.amount", "accounts.id"),)),),
        group=("accounts.name",),
    ),
    "text key": _joined(
        [("h", F("handles.h")), ("c", COUNT)],
        {"orders": "JO", "handles": "handles"},
        joins=(("inner", "handles", (("orders.note", "handles.h"),)),),
        group=("handles.h",),
    ),
    "no key check": _joined(
        [("h", F("handles.h")), ("id", F("orders.id"))],
        {"orders": "JO", "handles": "handles"},
        joins=(("inner", "handles", (("orders.note", "handles.h"),)),),
    ),
    # Batch reading's worst shape here: a sort of every row under the
    # default limits, whose ids come out in descending order.
    "sorted read": _joined(
        [("id", F("accounts.id"))],
        {"accounts": "accounts"},
        order=(("accounts.name", True),),
        **{"from": "accounts"},
    ),
}
# L13's statement around the 1 GiB memory_limit, recorded (section 4r).
MARGIN_LIMITS = ("768MiB", "1GiB", "1152MiB", "1280MiB", "1536MiB", "2GiB")


def account_name(k: int) -> str:
    return f"{k:07d}{PEAK_PAD[:24]}"


def handle_rows() -> list:
    """MAX_ROWS handles: three that match orders' notes, then distinct ones."""
    named = [("a", 1), ("c", 2), ("z", 3)]
    return named + [(f"{k:07d}{PEAK_PAD}", k) for k in range(MAX_ROWS - 3)]


def peak_table(pa: Any, name: str) -> Any:
    if name == "accounts":
        rows = range(MAX_ROWS)
        pad = PEAK_PAD[:24].encode()
        return pa.table(
            {
                "id": pa.array(list(rows), pa.int64()),
                "name": _strings(pa, [b"%07d" % k + pad for k in rows]),
            }
        )
    rows = handle_rows()
    return pa.table(
        {
            "h": _strings(pa, [h.encode() for h, _n in rows]),
            "n": pa.array([n for _h, n in rows], pa.int64()),
        }
    )


def rows_of(name: str, order: str) -> tuple:
    rows = TABLES[name]
    return rows[::-1] if order == "reversed" else rows


def digest(rows: list) -> dict:
    """C21's whole delivered sequence: its length and the sha256 of its JSON."""
    text = json.dumps(rows)
    return {"count": len(rows), "sha256": hashlib.sha256(text.encode()).hexdigest()}


C08_SUBS = tuple(
    f"{op} {value} {order}"
    for op in OPERATORS
    for value in C08_VALUES
    for order in ("forward", "reversed")
)
C11_SUBS = (
    "L1",
    "L2",
    "L3",
    "L4",
    "L5",
    "L6",
    "L7",
    "L8",
    "L9a",
    "L9b",
    "L9c",
    "L10",
    "L11a",
    "L11b",
    "L12",
    "L13",
)
ENTRIES = ("bundle", "save", "save_recoverable", "recover", "relay_live")
C15_SUBS = (
    *ENTRIES,
    "job_store",
    *(f"{form} {entry}" for form in B2_FORMS for entry in ENTRIES),
)
REPEATED = ("C07", "C10", "C11", "C14")
_CELLS = {
    "C01": ("",),
    "C02a": ("",),
    "C02b": ("",),
    "C02c": ("a", "b", "c", "d"),
    "C03": ("a", "b", "c", "d"),
    "C04": ("",),
    "C05": ("a", "b", "c", "d", "e", "f", "g"),
    "C06": C06_SUBS,
    "C07": ("P", "Q=="),
    "C08": C08_SUBS,
    "C09": ("",),
    "C10": ("i", "ii"),
    "C11": C11_SUBS,
    "C13": ("",),
    "C14": ("a", "b", "c"),
    "C15": C15_SUBS,
    "C16": ("",),
    **{cell: tuple(subs) for cell, subs in B2.items()},
    "C23": tuple(C23),
    "C24": tuple(C24),
    "C25": C25_SUBS,
    "C26": tuple(C26),
    "C27": C27_SUBS,
    "C28": C28_SUBS,
}
CELLS = {
    **{cell: _CELLS[cell] for cell in list(_CELLS)[:13]},
    "C12": ("ns", *(f"{cell}/{sub}" for cell in REPEATED for sub in _CELLS[cell])),
    **{cell: _CELLS[cell] for cell in list(_CELLS)[13:]},
}
U0_CELLS = ("C01", "C02a", "C15", "C22")
UNITS = ("U0", "U1", "U2", "U3")
SKIP = "*"
U0_SKIP = "U0 has neither duckdb nor pyarrow"


def processes(unit: str) -> list[tuple[str, tuple[str, ...], bool]]:
    """(cell, sub-cases, shadow first on sys.path), one fresh interpreter each;
    C12 runs in the namespace instead and is not listed."""
    if unit == "U0":
        return [(cell, CELLS[cell], False) for cell in U0_CELLS]
    listed = []
    for cell, subs in CELLS.items():
        if cell == "C03":
            listed += [(cell, ("a", "b", "d"), False), (cell, ("c",), True)]
        elif cell == "C28":
            # Each peak in its own interpreter: ru_maxrss never falls.
            listed += [(cell, (sub,), False) for sub in subs]
        elif cell != "C12":
            listed.append((cell, subs, False))
    return listed


def encode(value: Any) -> Any:
    """A delivered value with its Pietto type: Int as its decimal digits,
    Float as its 64-bit pattern, Text as its UTF-8 bytes in hex, Date and
    Timestamp as their civil text, Decimal as its digits at its scale; NULL
    is None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return ["Timestamp", value.isoformat(sep=" ", timespec="microseconds")]
    if isinstance(value, date):
        return ["Date", value.isoformat()]
    if isinstance(value, Decimal):
        return ["Decimal", format(value, "f")]
    if isinstance(value, bool):
        return ["Bool", value]
    if isinstance(value, int):
        return ["Int", str(value)]
    if isinstance(value, float):
        return ["Float", struct.pack(">d", value).hex()]
    if isinstance(value, str):
        return ["Text", value.encode("utf-8").hex()]
    return ["Other", type(value).__name__, repr(value)]


def encode_row(values: Any) -> list:
    return [encode(value) for value in values]
