"""The DuckDB storage kind of a `duckdb_arrow` result (D79.04;
docs/spec/duckdb-arrow-route-v1.md, "Session and attempt", step 4).

`to_arrow_table()` returns `int64`, `string`, `bool` and `double` columns and
marks every field nullable. This owner checks the labels, their order and
the types against the compiled result, restores its nullability, refuses a
NULL in a non-null field or a value that fails full validation
(`DUCKDB_RESULT_CHECK`, PIE-R3005), and cuts the batches under the attempt's
limits (PIE-R3004). Phase77 S23 owns the shared result readers; this kind is
wired into project_result_binding and project_execution_reader only after
S23 is integrated, so until then the route's attempt calls it directly. It
imports no PyArrow: the route passes the pinned module it verified.
"""

from __future__ import annotations

from typing import Any

from pietto._project.project_result_contract import ResultError

__all__: tuple[str, ...] = ()

STORAGE = {"Int": "int64", "Text": "string", "Bool": "bool_", "Float": "float64"}


def arrow_type(pa: Any, tag: str) -> Any:
    """The Arrow type of one admitted logical type."""
    return getattr(pa, STORAGE[tag])()


def result_schema(pa: Any, facts: Any) -> Any:
    """The compiled result: its labels in result order, each with the type
    and nullability of the source field it reads."""
    return pa.schema(
        [
            pa.field(
                label,
                arrow_type(pa, facts.fields[k].tag),
                nullable=facts.fields[k].nullable,
            )
            for label, k in facts.result
        ]
    )


def bind_result(pa: Any, table: Any, facts: Any) -> Any:
    """The engine's result under the compiled schema, or DUCKDB_RESULT_CHECK."""
    schema = result_schema(pa, facts)
    if type(table) is not pa.Table or table.schema.names != schema.names:
        raise ResultError("DUCKDB_RESULT_CHECK")
    for column, field in zip(table.columns, schema, strict=True):
        if (
            type(column.type) is not type(field.type)
            or not column.type.equals(field.type)
            or (not field.nullable and column.null_count)
        ):
            raise ResultError("DUCKDB_RESULT_CHECK")
        try:
            column.validate(full=True)
        except Exception:
            raise ResultError("DUCKDB_RESULT_CHECK") from None
    return pa.Table.from_arrays(table.columns, schema=schema)


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
