"""Lazy optional Arrow boundary: explicit Int64 schema and owned finite batches."""

from __future__ import annotations

from dataclasses import dataclass, field
import importlib
from typing import Any

from pietto._project.project_result_contract import ResultError
from pietto._project.project_result_binding import (
    ProducerResultBinding,
    verify_producer_binding,
)

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class BatchLimits:
    fields: int = 64
    rows: int = 4096
    bytes: int = 8 * 1024 * 1024


@dataclass(frozen=True, slots=True, eq=False)
class ArrowResultBinding:
    producer: ProducerResultBinding = field(repr=False)
    schema: Any = field(repr=False)


def _arrow() -> Any:
    try:
        return importlib.import_module("pyarrow")
    except ModuleNotFoundError as exc:
        if exc.name != "pyarrow":
            raise
        raise ResultError("ARROW_DEPENDENCY_MISSING") from exc


def bind_arrow(producer: ProducerResultBinding) -> ArrowResultBinding:
    if type(producer) is not ProducerResultBinding:
        raise ResultError("PRODUCER_ROOT")
    verify_producer_binding(producer, producer.contract, producer.artifact)
    pa = _arrow()
    schema = pa.schema(
        [
            pa.field(b.field.label, pa.int64(), nullable=b.nullable)
            for b in producer.fields
        ]
    )
    binding = ArrowResultBinding(producer, schema)
    verify_arrow_binding(binding, producer)
    return binding


def verify_arrow_binding(binding, producer) -> None:
    if type(producer) is not ProducerResultBinding:
        raise ResultError("PRODUCER_ROOT")
    verify_producer_binding(producer, producer.contract, producer.artifact)
    pa = _arrow()
    if (
        type(binding) is not ArrowResultBinding
        or binding.producer is not producer
        or not isinstance(binding.schema, pa.Schema)
        or len(binding.schema) != len(producer.fields)
        or binding.schema.metadata is not None
    ):
        raise ResultError("ARROW_BINDING")
    for actual, expected in zip(binding.schema, producer.fields, strict=True):
        if (
            actual.name != expected.field.label
            or actual.type != pa.int64()
            or actual.nullable is not expected.nullable
            or actual.metadata is not None
        ):
            raise ResultError("ARROW_BINDING")


def _dimensions(fields, rows, limits):
    if type(limits) is not BatchLimits or any(
        type(v) is not int or v < 0 for v in (limits.fields, limits.rows, limits.bytes)
    ):
        raise ResultError("LIMIT")
    if not fields or fields > min(limits.fields, 64) or rows > min(limits.rows, 4096):
        raise ResultError("LIMIT")
    # Int64 data plus one validity bitmap per column, regardless of actual NULLs.
    if fields * (rows * 8 + (rows + 7) // 8) > min(limits.bytes, 8 * 1024 * 1024):
        raise ResultError("LIMIT")


def _value(value, bound):
    if value is None:
        if not bound.nullable:
            raise ResultError("NULL")
    elif (
        type(value) is not int
        or not -(2**63) <= value < 2**63
        or not bound.observation.lower <= value <= bound.observation.upper
    ):
        raise ResultError("VALUE_DOMAIN")


def build_owned_batch(binding: ArrowResultBinding, rows, *, limits=BatchLimits()):
    if type(binding) is not ArrowResultBinding:
        raise ResultError("ARROW_BINDING")
    verify_arrow_binding(binding, binding.producer)
    if type(rows) not in (tuple, list):
        raise ResultError("ROWS")
    fields = binding.producer.fields
    _dimensions(len(fields), len(rows), limits)
    copied = []
    for row in rows:
        if type(row) not in (tuple, list) or len(row) != len(fields):
            raise ResultError("ROW_ARITY")
        values = tuple(row)
        for value, bound in zip(values, fields, strict=True):
            _value(value, bound)
        copied.append(values)
    pa = _arrow()
    arrays = [
        pa.array([row[i] for row in copied], type=pa.int64())
        for i in range(len(fields))
    ]
    batch = pa.RecordBatch.from_arrays(arrays, schema=binding.schema)
    verify_batch(batch, binding, binding.producer, limits=limits)
    return batch


def verify_batch(batch, binding, producer, *, limits=BatchLimits()) -> None:
    """Check the supplied carrier, not a rebuilt candidate or a checked flag.

    This proves bounded batch correspondence, not EOF or whole-result completion.
    """
    verify_arrow_binding(binding, producer)
    pa = _arrow()
    if not isinstance(batch, pa.RecordBatch) or not batch.is_cpu:
        raise ResultError("ARROW_BATCH")
    _dimensions(batch.num_columns, batch.num_rows, limits)
    if not batch.schema.equals(binding.schema, check_metadata=True):
        raise ResultError("ARROW_SCHEMA")
    try:
        batch.validate(full=True)
    except (ValueError, pa.ArrowException) as exc:
        raise ResultError("ARROW_BATCH") from exc
    retained_bytes = sum(
        buffer.size
        for column in batch.columns
        for buffer in column.buffers()
        if buffer is not None
    )
    if retained_bytes > min(limits.bytes, 8 * 1024 * 1024):
        raise ResultError("LIMIT")
    for i, bound in enumerate(producer.fields):
        for scalar in batch.column(i):
            _value(scalar.as_py(), bound)
