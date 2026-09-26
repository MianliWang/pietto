"""Lazy Arrow boundary: checked scalars and explicit UTF-8 offset widths."""

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
class TextOffsetWidthRequest:
    field: ResultField = field(repr=False)
    bits: int


@dataclass(frozen=True, slots=True, eq=False)
class ArrowResultBinding:
    producer: ProducerResultBinding = field(repr=False)
    schema: Any = field(repr=False)
    integer_widths: tuple[IntegerWidthRequest | None, ...] | None = None
    text_offset_widths: tuple[TextOffsetWidthRequest | None, ...] | None = None


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


def _text_widths(producer, requests):
    if requests is None:
        requests = (None,) * len(producer.fields)
    if type(requests) is not tuple or len(requests) != len(producer.fields):
        raise ResultError("ARROW_ADAPTATION")
    widths = []
    for bound, request in zip(producer.fields, requests, strict=True):
        is_text = bound.field.shape.canonical.name == "Text"
        width = 32 if is_text else None
        if request is not None:
            if (
                not is_text
                or type(request) is not TextOffsetWidthRequest
                or request.field is not bound.field
                or type(request.bits) is not int
                or request.bits not in (32, 64)
            ):
                raise ResultError("ARROW_ADAPTATION")
            width = request.bits
        widths.append(width)
    return tuple(widths)


def _arrow_type(pa, bound, width, text_width):
    kind = bound.field.shape.canonical.name
    if kind == "Int":
        return getattr(pa, f"int{width}")()
    if kind == "Text":
        return pa.string() if text_width == 32 else pa.large_string()
    return pa.bool_() if kind == "Bool" else pa.float64()


def bind_arrow(
    producer: ProducerResultBinding, *, integer_widths=None, text_offset_widths=None
) -> ArrowResultBinding:
    if type(producer) is not ProducerResultBinding:
        raise ResultError("PRODUCER_ROOT")
    verify_producer_binding(producer, producer.contract, producer.artifact)
    widths = _widths(producer, integer_widths)
    text_widths = _text_widths(producer, text_offset_widths)
    pa = _arrow()
    schema = pa.schema(
        [
            pa.field(
                b.field.label,
                _arrow_type(pa, b, width, text_width),
                nullable=b.nullable,
            )
            for b, width, text_width in zip(
                producer.fields, widths, text_widths, strict=True
            )
        ]
    )
    binding = ArrowResultBinding(producer, schema, integer_widths, text_offset_widths)
    verify_arrow_binding(binding, producer)
    return binding


def verify_arrow_binding(binding, producer) -> None:
    if type(producer) is not ProducerResultBinding:
        raise ResultError("PRODUCER_ROOT")
    verify_producer_binding(producer, producer.contract, producer.artifact)
    if type(binding) is not ArrowResultBinding or binding.producer is not producer:
        raise ResultError("ARROW_BINDING")
    widths = _widths(producer, binding.integer_widths)
    text_widths = _text_widths(producer, binding.text_offset_widths)
    pa = _arrow()
    if (
        not isinstance(binding.schema, pa.Schema)
        or len(binding.schema) != len(producer.fields)
        or binding.schema.metadata is not None
    ):
        raise ResultError("ARROW_BINDING")
    for actual, expected, width, text_width in zip(
        binding.schema, producer.fields, widths, text_widths, strict=True
    ):
        if (
            actual.name != expected.field.label
            or actual.type != _arrow_type(pa, expected, width, text_width)
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


def _base_charge(binding, rows, limits):
    widths = _text_widths(binding.producer, binding.text_offset_widths)
    # Keep the inherited eight-byte numeric/Bool/Float admission allowance.
    charge = sum(
        (rows + 7) // 8 + (rows * 8 if width is None else width // 8 * (rows + 1))
        for width in widths
    )
    if charge > min(limits.bytes, 8 * 1024 * 1024):
        raise ResultError("LIMIT")
    return charge


def _text_bytes(value, remaining):
    # No bulk encode before admission; stop once the cumulative allowance is spent.
    size = 0
    if len(value) > remaining:
        raise ResultError("LIMIT")
    for char in value:
        code = ord(char)
        if 0xD800 <= code <= 0xDFFF:
            raise ResultError("VALUE_DOMAIN")
        size += 1 if code < 0x80 else 2 if code < 0x800 else 3 if code < 0x10000 else 4
        if size > remaining:
            raise ResultError("LIMIT")
    return size


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
    elif kind == "Text":
        text = bound.observation.text
        if (
            type(value) is not str
            or len(value) > text.max_characters
            or (bound.observation.storage == "pg_text" and "\0" in value)
        ):
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
    charge = _base_charge(binding, len(rows), limits)
    text_sizes = [0] * len(fields)
    text_widths = _text_widths(binding.producer, binding.text_offset_widths)
    copied = []
    for row in rows:
        if type(row) not in (tuple, list) or len(row) != len(fields):
            raise ResultError("ROW_ARITY")
        values = tuple(
            _value(value, bound)
            for value, bound in zip(tuple(row), fields, strict=True)
        )
        for i, (value, width) in enumerate(zip(values, text_widths, strict=True)):
            if width is not None and value is not None:
                size = _text_bytes(value, min(limits.bytes, 8 * 1024 * 1024) - charge)
                text_sizes[i] += size
                if text_sizes[i] >= 1 << (width - 1):
                    raise ResultError("LIMIT")
                charge += size
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
    charge = _base_charge(binding, batch.num_rows, limits)
    retained_bytes = sum(
        buffer.size
        for column in batch.columns
        for buffer in column.buffers()
        if buffer is not None
    )
    if retained_bytes > min(limits.bytes, 8 * 1024 * 1024):
        raise ResultError("LIMIT")
    try:
        batch.validate(full=True)
        widths = _text_widths(producer, binding.text_offset_widths)
        for i, bound in enumerate(producer.fields):
            text_size = 0
            for scalar in batch.column(i):
                value = _value(scalar.as_py(), bound, logical=True)
                if widths[i] is not None and value is not None:
                    size = _text_bytes(
                        value, min(limits.bytes, 8 * 1024 * 1024) - charge
                    )
                    text_size += size
                    if text_size >= 1 << (widths[i] - 1):
                        raise ResultError("LIMIT")
                    charge += size
    except ResultError:
        raise
    except (ValueError, pa.ArrowException) as exc:
        raise ResultError("ARROW_BATCH") from exc
