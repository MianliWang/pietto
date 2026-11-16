"""The SQLite storage kinds of a `sqlite_file` result (PL.47;
docs/spec/sqlite-project-v1.md, "Execution").

The route reads the compiled statement's rows as Python values through the
standard library's `sqlite3`. This owner gives each storage kind of the
compiled result its Arrow type and binds the rows: every value is checked
before PyArrow sees it (lesson 80-3), so it has its kind's exact Python type
(`int` in the signed 64-bit range, `int` 0 or 1, `str`, finite `float`) or
is None in a nullable column, else SQLITE_RESULT_CHECK (PIE-R3005). It
imports no PyArrow: the route passes the pinned module it verified.
"""

from __future__ import annotations

import math
from typing import Any

from pietto._project.project_result_contract import ResultError

__all__: tuple[str, ...] = ()

ARROW = {
    "sqlite_integer": "int64",
    "sqlite_bool01": "bool_",
    "sqlite_text": "string",
    "sqlite_real": "float64",
}


def _value(kind: str, value: object) -> object:
    """The value a non-null cell of `kind` carries into Arrow."""
    if kind == "sqlite_integer" and type(value) is int and -(2**63) <= value < 2**63:
        return value
    if kind == "sqlite_bool01" and type(value) is int and value in (0, 1):
        return value == 1
    if kind == "sqlite_text" and type(value) is str:
        return value
    if kind == "sqlite_real" and type(value) is float and math.isfinite(value):
        return value
    raise ResultError("SQLITE_RESULT_CHECK")


def result_schema(pa: Any, columns: tuple[tuple[str, str, bool], ...]) -> Any:
    """The compiled result: each (label, storage kind, nullable) in order."""
    return pa.schema(
        [
            pa.field(label, getattr(pa, ARROW[kind])(), nullable=nullable)
            for label, kind, nullable in columns
        ]
    )


def bind_result(
    pa: Any, rows: list[Any], columns: tuple[tuple[str, str, bool], ...]
) -> Any:
    """The rows, each a tuple in result order, as a table of the compiled
    schema; any other row or value is SQLITE_RESULT_CHECK."""
    if any(type(row) is not tuple or len(row) != len(columns) for row in rows):
        raise ResultError("SQLITE_RESULT_CHECK")
    arrays = []
    for k, (_label, kind, nullable) in enumerate(columns):
        values = []
        for row in rows:
            value = row[k]
            if value is None:
                if not nullable:
                    raise ResultError("SQLITE_RESULT_CHECK")
                values.append(None)
            else:
                values.append(_value(kind, value))
        arrays.append(pa.array(values, type=getattr(pa, ARROW[kind])()))
    return pa.Table.from_arrays(arrays, schema=result_schema(pa, columns))
