"""The DuckDB storage kind of a `duckdb_arrow` result (D79.04;
docs/spec/duckdb-arrow-route-v1.md, "Session and attempt", step 4).

`to_arrow_table()` returns `int64`, `string`, `bool` and `double` columns and
marks every field nullable. The shared result readers hold this kind (D77.32's
wiring): project_result_binding closes the DuckDB storage kinds of each type,
and project_execution_reader binds the result against the compiled schema
built here (`DUCKDB_RESULT_CHECK`, PIE-R3005). This owner gives each kind its
Arrow type and cuts the batches under the attempt's limits (PIE-R3004). It
imports no PyArrow: the route passes the pinned module it verified.
"""

from __future__ import annotations

from typing import Any

from pietto._project.project_duckdb_contract import FAMILY
from pietto._project.project_result_binding import _storages
from pietto._project.project_result_contract import ResultError

__all__: tuple[str, ...] = ()

ARROW = {
    "arrow_int64": "int64",
    "arrow_string": "string",
    "arrow_bool": "bool_",
    "arrow_float64": "float64",
}


def arrow_type(pa: Any, tag: str) -> Any:
    """The Arrow type of one admitted logical type's DuckDB storage kind."""
    (kind,) = _storages(FAMILY, False)[tag]
    return getattr(pa, ARROW[kind])()


def result_schema(pa: Any, facts: Any) -> Any:
    """The compiled result: its labels in result order, each with its logical
    type's Arrow type and its nullability."""
    return pa.schema(
        [
            pa.field(label, arrow_type(pa, tag), nullable=nullable)
            for label, tag, nullable in facts.result
        ]
    )


class DuckDBBatch:
    """One delivered record batch; the caller imports it through the Arrow
    PyCapsule interface."""

    __slots__ = ("_batch",)

    def __init__(self, batch: Any) -> None:
        self._batch = batch

    def __arrow_c_schema__(self) -> Any:
        return self._batch.__arrow_c_schema__()

    def __arrow_c_array__(self, requested_schema: Any = None) -> Any:
        return self._batch.__arrow_c_array__(requested_schema)

    def close(self) -> None:
        """The batch holds no resource of the attempt; nothing to release."""


class DuckDBBatches:
    """The checked result, cut into batches of at most `batch_rows` rows.
    A batch whose `nbytes` exceeds `batch_bytes`, or that would take the
    delivered rows or bytes past `max_rows` or `max_bytes`, is refused whole
    (EXECUTION_RESOURCE_LIMIT), never truncated."""

    def __init__(self, pa: Any, table: Any, limits: Any) -> None:
        self._pa = pa
        self._table = table
        self._limits = limits
        self._offset = 0
        self.rows = self.batches = self.bytes = 0

    def next(self) -> DuckDBBatch | None:
        """The next batch, or None at the end of the result."""
        if self._offset >= self._table.num_rows:
            return None
        part = self._table.slice(self._offset, self._limits.batch_rows)
        batch = self._pa.RecordBatch.from_arrays(
            [column.combine_chunks() for column in part.columns], schema=part.schema
        )
        charge = batch.nbytes
        if (
            charge > self._limits.batch_bytes
            or self.rows + batch.num_rows > self._limits.max_rows
            or self.bytes + charge > self._limits.max_bytes
        ):
            raise ResultError("EXECUTION_RESOURCE_LIMIT")
        self._offset += batch.num_rows
        self.rows += batch.num_rows
        self.batches += 1
        self.bytes += charge
        return DuckDBBatch(batch)
