"""A compiled DuckDB B1 query and Arrow inputs for the `duckdb_arrow` route
(docs/spec/duckdb-arrow-route-v1.md). The project is `_pietto_sql_duckdb`'s
`orders` source; tables are built from the caller's PyArrow module, so this
helper imports no PyArrow itself."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from _pietto_sql_duckdb import PROJECTION, contract, filtered, write

from pietto import execution

ROWS = (
    (1, 5, "a", True, 1.5),
    (2, 10, None, False, -0.0),
    (3, 15, "c", True, 2.5),
    (4, -(2**63), "", False, -1.0),
    (5, 2**63 - 1, "é", True, 0.0),
)
COLUMNS = ("id", "amount", "note", "ok", "price")


def compiled(root: Path, body: str | None = None) -> execution.CompiledQuery:
    """compile_query of `body` (the filtered `>=` query by default)."""
    body = filtered(">=") if body is None else body
    write(root, body, contract())
    return execution.compile_query(
        root,
        module="main.pietto",
        kind="query" if body.startswith("query") else "table",
        name="result",
        dialect="duckdb",
        emission_contract="contract.json",
    )


def projection(root: Path) -> execution.CompiledQuery:
    return compiled(root, PROJECTION)


def orders(pa: Any, rows: tuple[tuple[Any, ...], ...] = ROWS, **columns: Any) -> Any:
    """The `orders` table of `rows`, each named column replaced by an array."""
    types = (pa.int64(), pa.int64(), pa.string(), pa.bool_(), pa.float64())
    arrays = {
        name: pa.array([row[k] for row in rows], type=types[k])
        for k, name in enumerate(COLUMNS)
    }
    arrays.update(columns)
    return pa.table(arrays)


def run(pa: Any, query: execution.CompiledQuery, table: Any, **arguments: Any) -> Any:
    """Every delivered row as a dict, and the handle, of one attempt."""
    arguments.setdefault("parameters", {"min_amount": 10} if query.parameters else None)
    handle = execution.execute(
        query,
        route="duckdb_arrow",
        access=execution.DuckDBArrowInput("orders", table),
        premise=None,
        **arguments,
    )
    with handle as result:
        rows = [row for batch in result for row in pa.record_batch(batch).to_pylist()]
    return rows, handle


def bag(rows: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
    """A multiset of rows: B1 has no ordering."""
    return sorted((tuple(row.items()) for row in rows), key=repr)
