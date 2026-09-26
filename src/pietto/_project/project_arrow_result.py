"""Lazy Arrow boundary: lossless signed widths, Bool and finite Float64 batches."""

from __future__ import annotations

from dataclasses import dataclass, field
import importlib
import math
from typing import Any

from pietto._project.project_result_contract import ResultError, ResultField
from pietto._project.project_sql_emission_rows import INT_WIDTHS
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
class IntegerWidthRequest:
    field: ResultField = field(repr=False)
    bits: int


@dataclass(frozen=True, slots=True, eq=False)
class ArrowResultBinding:
    producer: ProducerResultBinding = field(repr=False)
    schema: Any = field(repr=False)
    integer_widths: tuple[IntegerWidthRequest | None, ...] | None = None


def _arrow() -> Any:
    try:
        return importlib.import_module("pyarrow")
    except ModuleNotFoundError as exc:
        if exc.name != "pyarrow":
            raise
        raise ResultError("ARROW_DEPENDENCY_MISSING") from exc


def _widths(producer, requests):
    if requests is None:
        requests = (None,) * len(producer.fields)
    if type(requests) is not tuple or len(requests) != len(producer.fields):
        raise ResultError("ARROW_ADAPTATION")
    widths = []
    for bound, request in zip(producer.fields, requests, strict=True):
        is_int = bound.field.shape.canonical.name == "Int"
        width = INT_WIDTHS[bound.observation.storage] if is_int else None
        if request is not None:
            if (
                not is_int
                or type(request) is not IntegerWidthRequest
                or request.field is not bound.field
                or type(request.bits) is not int
                or request.bits not in (16, 32, 64)
            ):
                raise ResultError("ARROW_ADAPTATION")
            width = request.bits
            if (
                not -(1 << (width - 1))
                <= bound.observation.lower
                <= bound.observation.upper
                < (1 << (width - 1))
            ):
                raise ResultError("ARROW_ADAPTATION")
        widths.append(width)
    return tuple(widths)


def _arrow_type(pa, bound, width):
    kind = bound.field.shape.canonical.name
    if kind == "Int":
        return getattr(pa, f"int{width}")()
    return pa.bool_() if kind == "Bool" else pa.float64()


def bind_arrow(
    producer: ProducerResultBinding, *, integer_widths=None
) -> ArrowResultBinding:
    if type(producer) is not ProducerResultBinding:
        raise ResultError("PRODUCER_ROOT")
    verify_producer_binding(producer, producer.contract, producer.artifact)
    widths = _widths(producer, integer_widths)
    pa = _arrow()
    schema = pa.schema(
        [
            pa.field(b.field.label, _arrow_type(pa, b, width), nullable=b.nullable)
            for b, width in zip(producer.fields, widths, strict=True)
        ]
    )
    binding = ArrowResultBinding(producer, schema, integer_widths)
    verify_arrow_binding(binding, producer)
    return binding


def verify_arrow_binding(binding, producer) -> None:
    if type(producer) is not ProducerResultBinding:
        raise ResultError("PRODUCER_ROOT")
    verify_producer_binding(producer, producer.contract, producer.artifact)
    if type(binding) is not ArrowResultBinding or binding.producer is not producer:
        raise ResultError("ARROW_BINDING")
    widths = _widths(producer, binding.integer_widths)
    pa = _arrow()
    if (
        not isinstance(binding.schema, pa.Schema)
        or len(binding.schema) != len(producer.fields)
        or binding.schema.metadata is not None
    ):
        raise ResultError("ARROW_BINDING")
    for actual, expected, width in zip(
        binding.schema, producer.fields, widths, strict=True
    ):
        if (
            actual.name != expected.field.label
            or actual.type != _arrow_type(pa, expected, width)
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
    # Eight bytes per cell plus validity also bounds the smaller Bool bitmaps.
    if fields * (rows * 8 + (rows + 7) // 8) > min(limits.bytes, 8 * 1024 * 1024):
        raise ResultError("LIMIT")


def _value(value, bound, *, logical=False):
    if value is None:
        if not bound.nullable:
            raise ResultError("NULL")
        return None
    kind = bound.field.shape.canonical.name
    if kind == "Int":
        if (
            type(value) is not int
            or not bound.observation.lower <= value <= bound.observation.upper
        ):
            raise ResultError("VALUE_DOMAIN")
    elif kind == "Bool":
        if not logical and bound.observation.carrier == "int01":
            if type(value) is not int or value not in (0, 1):
                raise ResultError("VALUE_DOMAIN")
            return value == 1
        if type(value) is not bool:
            raise ResultError("VALUE_DOMAIN")
    elif type(value) is not float or not math.isfinite(value):
        raise ResultError("VALUE_DOMAIN")
    return value


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
        values = tuple(
            _value(value, bound)
            for value, bound in zip(tuple(row), fields, strict=True)
        )
        copied.append(values)
    pa = _arrow()
    arrays = [
        pa.array(
            [row[i] for row in copied], type=binding.schema[i].type, from_pandas=False
        )
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
            _value(scalar.as_py(), bound, logical=True)
