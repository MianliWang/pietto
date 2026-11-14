"""The fixtures of the Phase79 S06 native qualification (preregistration v5,
section 3): projects P0, P1 and P2, tables T5, TN and the sized and forged
tables, the cells with their sub-cases, the processes that run them, and the
one value encoding the producer and the oracle share. Importing it loads
neither PyArrow nor DuckDB nor Pietto; tables are built from the caller's
PyArrow module."""

from __future__ import annotations

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
MAX_ROWS = 65_536
MAX_BYTES = 16_777_216
WATCHDOG_SECONDS = 30.0

SLOW_SQL = 'SELECT count(*) AS "id", NULL AS "note" FROM pietto_running'
FRAME_SQL = "SELECT * FROM pietto_frame_table"
NEVER_SQL = "SELECT pietto_never_runs()"
OVERFLOW_SQL = (
    'SELECT CAST(9223372036854775807 AS BIGINT) + "c0" AS "id", "c2" AS "note" '
    'FROM temp.main."pietto_arrow_0"'
)
RELABEL_SQL = 'SELECT "c0" AS "ID", "c2" AS "note" FROM temp.main."pietto_arrow_0"'
E_SQL = "SELECT extension_name FROM duckdb_extensions() WHERE loaded ORDER BY 1"
SETTINGS_SQL = "SELECT name, value FROM duckdb_settings()"
K_SQL = (
    "SELECT database_name, schema_name, function_name, function_type, "
    "CAST(parameter_types AS VARCHAR), return_type FROM duckdb_functions() "
    "ORDER BY ALL",
    "SELECT name FROM duckdb_settings() ORDER BY 1",
    "SELECT database_name, schema_name, type_name FROM duckdb_types() ORDER BY ALL",
)

# Projects (section 3): the amount field's spelling, nullability and range.
PROJECTS = {
    "P0": ("Int", False, INT64),
    "P1": ("Int | None", True, INT64),
    "P2": ("Int", False, (-100, 100)),
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
        ("ok", "Bool", False, INT64),
        ("price", "Float", False, INT64),
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
    header = (
        f"shape Order:\n    id: Int\n    amount: {spelling}\n    note: Text | None\n"
        '    ok: Bool\n    price: Float\n\nsource orders: Order = duckdb.arrow("orders")\n'
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


def sized(pa: Any, total: int) -> Any:
    """C05: five columns of MAX_ROWS rows whose `Table.nbytes` is `total`; the
    caller checks the size before use."""
    empty = [(k, 5, "", True, 0.0) for k in range(MAX_ROWS)]
    each, extra = divmod(total - table(pa, empty).nbytes, MAX_ROWS)
    return table(
        pa, [(k, 5, _text_of(each + (k < extra)), True, 0.0) for k in range(MAX_ROWS)]
    )


def padded(pa: Any) -> tuple[Any, int]:
    """C05 (e): the five columns and an unselected `bool` column `extra`, with
    `Table.nbytes` MAX_BYTES + 1 and the five alone at most MAX_BYTES; returns
    the table and the five columns' own size."""
    extra = pa.array([True] * MAX_ROWS)
    five = sized(pa, MAX_BYTES + 1 - extra.nbytes)
    return five.append_column("extra", extra), five.nbytes


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
)
C15_SUBS = ("bundle", "save", "save_recoverable", "recover", "relay_live", "job_store")
REPEATED = ("C07", "C10", "C11", "C14")
_CELLS = {
    "C01": ("",),
    "C02a": ("",),
    "C02b": ("",),
    "C02c": ("a", "b", "c", "d"),
    "C03": ("a", "b", "c", "d"),
    "C04": ("",),
    "C05": ("a", "b", "c", "d", "e"),
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
}
CELLS = {
    **{cell: _CELLS[cell] for cell in list(_CELLS)[:13]},
    "C12": ("ns", *(f"{cell}/{sub}" for cell in REPEATED for sub in _CELLS[cell])),
    **{cell: _CELLS[cell] for cell in list(_CELLS)[13:]},
}
U0_CELLS = ("C01", "C02a", "C15")
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
