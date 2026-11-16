"""The fixtures of the Phase79 DuckDB native qualification (preregistration
v6, sections 3 and 4f-4k): projects P0, P1, P2 and PB, tables T5, TN, B2's
tables and the sized, capacity and forged tables, B2's statements, the cells
with their sub-cases, the processes that run them, and the one value encoding
the producer and the oracle share. Importing it loads neither PyArrow nor
DuckDB nor Pietto; tables are built from the caller's PyArrow module."""

from __future__ import annotations

import hashlib
import json
import math
import struct
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
        "target": {"family": "duckdb", "release": "2.0.0"},
        "sources": [source],
        "environment": statement,
    }


def write_project(root: Path, project: str, body: str) -> Path:
    """An explicit-module project: P's header, the body, the contract."""
    spelling = PROJECTS[project][0]
    optional = " | None" if project == "PB" else ""
    header = (
        f"shape Order:\n    id: Int\n    amount: {spelling}\n    note: Text | None\n"
        f"    ok: Bool{optional}\n    price: Float{optional}\n\n"
        'source orders: Order = duckdb.arrow("orders")\n'
    )
    root.mkdir(parents=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    (root / "main.pietto").write_text(header + "\n" + body, encoding="utf-8")
    (root / "contract.json").write_text(json.dumps(contract(project)), encoding="utf-8")
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
    }
    spec.update(parts)
    return spec


def body(spec: dict) -> str:
    """The Pietto text of a statement."""
    params = ", ".join(f"{name}: {kind}" for name, kind in spec["params"])
    text = f"query result({params}):\n" if params else "table result:\n"
    text += "    from orders\n"
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
# rule 7 refuses at that output; B1 is the same output beside B1's filter.
COMPUTED = "more = amount + 1"
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
B2 = {"C17": C17, "C18": C18, "C19": C19, "C20": C20, "C21": C21, "C22": RULE_TWO}


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
        elif cell != "C12":
            listed.append((cell, subs, False))
    return listed


def encode(value: Any) -> Any:
    """A delivered value with its Pietto type: Int as its decimal digits,
    Float as its 64-bit pattern, Text as its UTF-8 bytes in hex; NULL is
    None."""
    if value is None:
        return None
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
