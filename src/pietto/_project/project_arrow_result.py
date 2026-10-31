"""Lazy Arrow boundary: checked scalars, explicit UTF-8 offset widths and one
level of collected child records (``list<item: struct<...> not null>``)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID
import importlib
import math
from typing import Any

from pietto._project.project_result_contract import (
    NestedShape,
    ResultError,
    ResultField,
    ScalarShape,
)
from pietto._project.project_sql_emission_rows import INT_WIDTHS
from pietto._project.project_scalar_meaning import (
    TIMESTAMP_LOWER,
    TIMESTAMP_UPPER,
    MIN_TIMESTAMP_TICKS,
    MAX_TIMESTAMP_TICKS,
    civil_ticks,
)
from pietto._project.project_result_binding import (
    CHILD_KINDS,
    MAX_CHILD_ROWS,
    ProducerFieldBinding,
    ProducerNestedBinding,
    ProducerResultBinding,
    verify_producer_binding,
)

__all__: tuple[str, ...] = ()
# The pinned Arrow package of every public Arrow-producing flow. The route
# owners use this at their public boundary; internal callers stay lazy.
PYARROW = ("pyarrow", "26.0.0", "pyarrow")
DATE_LOWER = date(1000, 1, 1)
DATE_UPPER = date(9999, 12, 31)


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
class DecimalWidthRequest:
    field: ResultField = field(repr=False)
    bits: int


@dataclass(frozen=True, slots=True, eq=False)
class UUIDRepresentationRequest:
    field: ResultField = field(repr=False)
    representation: str


@dataclass(frozen=True, slots=True, eq=False)
class ArrowFieldLabelRequest:
    field: ResultField = field(repr=False)
    label: str


@dataclass(frozen=True, slots=True, eq=False)
class ArrowResultBinding:
    producer: ProducerResultBinding = field(repr=False)
    schema: Any = field(repr=False)
    integer_widths: tuple[IntegerWidthRequest | None, ...] | None = None
    text_offset_widths: tuple[TextOffsetWidthRequest | None, ...] | None = None
    decimal_widths: tuple[DecimalWidthRequest | None, ...] | None = None
    uuid_representations: tuple[UUIDRepresentationRequest | None, ...] | None = None
    field_labels: tuple[ArrowFieldLabelRequest | None, ...] | None = None


def _arrow() -> Any:
    try:
        return importlib.import_module("pyarrow")
    except ModuleNotFoundError as exc:
        if exc.name != "pyarrow":
            raise
        raise ResultError("ARROW_DEPENDENCY_MISSING") from exc


def pinned() -> Any:
    """The installed PyArrow selected for a public use boundary."""
    from pietto._project.project_execution import pinned_modules

    (pa,) = pinned_modules((PYARROW,), "ARROW_DEPENDENCY_VERSION")
    return pa


def _children(bound):
    """The scalar child bindings of a nested field, or None for a scalar field."""
    if type(bound) is not ProducerNestedBinding:
        if type(bound) is not ProducerFieldBinding or (
            type(bound.field.shape) is not ScalarShape
        ):
            raise ResultError("PRODUCER_FIELDS")
        return None
    shape = bound.field.shape
    children = bound.children
    if (
        type(shape) is not NestedShape
        or type(children) is not tuple
        or type(shape.fields) is not tuple
        or not children
        or len(children) != len(shape.fields)
        or type(bound.nullable) is not bool
        or any(
            type(child) is not ProducerFieldBinding
            or child.field is not leaf
            or type(leaf.shape) is not ScalarShape
            or type(child.nullable) is not bool
            for child, leaf in zip(children, shape.fields, strict=True)
        )
        # Struct values are keyed by label; a duplicate would drop a child value.
        or len({child.field.label for child in children}) != len(children)
    ):
        raise ResultError("PRODUCER_FIELDS")
    if any(child.field.shape.canonical.name not in CHILD_KINDS for child in children):
        raise ResultError("PRODUCER_UNSUPPORTED")
    return children


def _nested_request(bound, request, category):
    """True for a nested field; Phase71 offers no request on one (D-S10-3)."""
    if _children(bound) is None:
        return False
    if request is not None:
        raise ResultError(category)
    return True


def _width(fields):
    """N_fields: top-level fields plus every child field."""
    return sum(1 + len(_children(bound) or ()) for bound in fields)


def _widths(producer, requests):
    if requests is None:
        requests = (None,) * len(producer.fields)
    if type(requests) is not tuple or len(requests) != len(producer.fields):
        raise ResultError("ARROW_ADAPTATION")
    widths = []
    for bound, request in zip(producer.fields, requests, strict=True):
        if _nested_request(bound, request, "ARROW_ADAPTATION"):
            widths.append(None)
            continue
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
        if _nested_request(bound, request, "ARROW_ADAPTATION"):
            widths.append(None)
            continue
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


def _decimal_widths(producer, requests):
    if requests is None:
        requests = (None,) * len(producer.fields)
    if type(requests) is not tuple or len(requests) != len(producer.fields):
        raise ResultError("ARROW_ADAPTATION")
    widths = []
    for bound, request in zip(producer.fields, requests, strict=True):
        if _nested_request(bound, request, "ARROW_ADAPTATION"):
            widths.append(None)
            continue
        decimal = bound.observation.decimal
        width = None if decimal is None else 128 if decimal.precision <= 38 else 256
        if request is not None:
            if (
                decimal is None
                or type(request) is not DecimalWidthRequest
                or request.field is not bound.field
                or type(request.bits) is not int
                or request.bits not in (128, 256)
                or (request.bits == 128 and decimal.precision > 38)
            ):
                raise ResultError("ARROW_ADAPTATION")
            width = request.bits
        widths.append(width)
    return tuple(widths)


def _uuid_representations(producer, requests):
    if requests is None:
        requests = (None,) * len(producer.fields)
    if type(requests) is not tuple or len(requests) != len(producer.fields):
        raise ResultError("ARROW_ADAPTATION")
    policies = []
    for bound, request in zip(producer.fields, requests, strict=True):
        if _nested_request(bound, request, "ARROW_ADAPTATION"):
            policies.append(None)
            continue
        is_uuid = bound.field.shape.canonical.name == "UUID"
        policy = "uuid" if is_uuid else None
        if request is not None:
            if (
                not is_uuid
                or type(request) is not UUIDRepresentationRequest
                or request.field is not bound.field
                or type(request.representation) is not str
                or request.representation not in ("uuid", "binary16")
            ):
                raise ResultError("ARROW_ADAPTATION")
            policy = request.representation
        policies.append(policy)
    return tuple(policies)


def _arrow_type(pa, bound, width, text_width, decimal_width, uuid_representation):
    children = _children(bound)
    if children is not None:
        # One collected child relation (slice-07.md 5): 32-bit offsets, an always
        # valid item, children by ordinal with the default scalar policies.
        return pa.list_(
            pa.field(
                "item",
                pa.struct(
                    [
                        pa.field(
                            child.field.label,
                            _arrow_type(
                                pa, child, _child_int_width(child), 32, None, None
                            ),
                            nullable=child.nullable,
                        )
                        for child in children
                    ]
                ),
                nullable=False,
            )
        )
    kind = bound.field.shape.canonical.name
    if kind == "Int":
        return getattr(pa, f"int{width}")()
    if kind == "Text":
        return pa.string() if text_width == 32 else pa.large_string()
    if kind == "Decimal":
        decimal = bound.observation.decimal
        return getattr(pa, f"decimal{decimal_width}")(decimal.precision, decimal.scale)
    if kind == "Date":
        return pa.date32()
    if kind == "Timestamp":
        return pa.timestamp("us", tz=None)
    if kind == "UUID":
        return pa.uuid() if uuid_representation == "uuid" else pa.binary(16)
    if kind == "Bool":
        return pa.bool_()
    if kind == "Float":
        return pa.float64()
    raise ResultError("PRODUCER_UNSUPPORTED")


def _child_int_width(child):
    if child.field.shape.canonical.name != "Int":
        return None
    width = INT_WIDTHS.get(child.observation.storage)
    if width is None:
        raise ResultError("PRODUCER_OBSERVATION")
    return width


def _field_labels(producer, requests):
    if requests is None:
        return tuple(bound.field.label for bound in producer.fields)
    if type(requests) is not tuple or len(requests) != len(producer.fields):
        raise ResultError("ARROW_LABELS")
    labels = []
    total = 0
    for bound, request in zip(producer.fields, requests, strict=True):
        if request is None:
            labels.append(bound.field.label)
            continue
        if (
            _children(bound) is not None
            or type(request) is not ArrowFieldLabelRequest
            or getattr(request, "field", None) is not bound.field
            or type(getattr(request, "label", None)) is not str
            or not 0 < len(request.label) <= 1024
            or "\0" in request.label
        ):
            raise ResultError("ARROW_LABELS")
        try:
            size = len(request.label.encode("utf-8"))
        except UnicodeEncodeError as exc:
            raise ResultError("ARROW_LABELS") from exc
        total += size
        if size > 1024 or total > 64 * 1024:
            raise ResultError("ARROW_LABELS")
        labels.append(request.label)
    return tuple(labels)


def bind_arrow(
    producer: ProducerResultBinding,
    *,
    integer_widths=None,
    text_offset_widths=None,
    decimal_widths=None,
    uuid_representations=None,
    field_labels: tuple[ArrowFieldLabelRequest | None, ...] | None = None,
) -> ArrowResultBinding:
    if type(producer) is not ProducerResultBinding:
        raise ResultError("PRODUCER_ROOT")
    verify_producer_binding(producer, producer.contract, producer.artifact)
    widths = _widths(producer, integer_widths)
    text_widths = _text_widths(producer, text_offset_widths)
    decimals = _decimal_widths(producer, decimal_widths)
    uuids = _uuid_representations(producer, uuid_representations)
    labels = _field_labels(producer, field_labels)
    pa = _arrow()
    schema = pa.schema(
        [
            pa.field(
                label,
                _arrow_type(pa, b, width, text_width, decimal_width, uuid_policy),
                nullable=b.nullable,
            )
            for b, width, text_width, decimal_width, uuid_policy, label in zip(
                producer.fields,
                widths,
                text_widths,
                decimals,
                uuids,
                labels,
                strict=True,
            )
        ]
    )
    binding = ArrowResultBinding(
        producer,
        schema,
        integer_widths,
        text_offset_widths,
        decimal_widths,
        uuid_representations,
        field_labels,
    )
    verify_arrow_binding(binding, producer)
    return binding


def verify_arrow_binding(binding, producer) -> None:
    if type(producer) is not ProducerResultBinding:
        raise ResultError("PRODUCER_ROOT")
    verify_producer_binding(producer, producer.contract, producer.artifact)
    if type(binding) is not ArrowResultBinding or binding.producer is not producer:
        raise ResultError("ARROW_BINDING")
    if not hasattr(binding, "field_labels"):
        raise ResultError("ARROW_LABELS")
    labels = _field_labels(producer, binding.field_labels)
    if any(
        not hasattr(binding, name)
        for name in (
            "integer_widths",
            "text_offset_widths",
            "decimal_widths",
            "uuid_representations",
        )
    ):
        raise ResultError("ARROW_ADAPTATION")
    widths = _widths(producer, binding.integer_widths)
    text_widths = _text_widths(producer, binding.text_offset_widths)
    decimals = _decimal_widths(producer, binding.decimal_widths)
    uuids = _uuid_representations(producer, binding.uuid_representations)
    pa = _arrow()
    if (
        not isinstance(binding.schema, pa.Schema)
        or len(binding.schema) != len(producer.fields)
        or binding.schema.metadata is not None
    ):
        raise ResultError("ARROW_BINDING")
    for actual, expected, width, text_width, decimal_width, uuid_policy, label in zip(
        binding.schema,
        producer.fields,
        widths,
        text_widths,
        decimals,
        uuids,
        labels,
        strict=True,
    ):
        expected_type = _arrow_type(
            pa, expected, width, text_width, decimal_width, uuid_policy
        )
        if _children(expected) is not None:
            # DataType equality ignores the item name and child metadata, and
            # metadata equality treats {} as none; no level carries metadata.
            if not actual.equals(
                pa.field(label, expected_type, nullable=expected.nullable),
                check_metadata=True,
            ) or any(
                level.metadata is not None
                for level in (actual, actual.type.value_field, *actual.type.value_type)
            ):
                raise ResultError("ARROW_BINDING")
            continue
        if (
            (uuid_policy is not None and type(actual.type) is not type(expected_type))
            or actual.name != label
            or actual.type != expected_type
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
    decimals = _decimal_widths(binding.producer, binding.decimal_widths)
    # Keep the inherited eight-byte numeric/Bool/Float admission allowance.
    charge = sum(
        (rows + 7) // 8
        + (
            # A nested field: its list validity and 32-bit offsets; children
            # are charged by _child_charge once their row count is known.
            4 * (rows + 1)
            if _children(bound) is not None
            else rows
            * (
                decimal_width // 8
                if decimal_width is not None
                else 16
                if bound.field.shape.canonical.name == "UUID"
                else 8
            )
            if width is None
            else width // 8 * (rows + 1)
        )
        for bound, width, decimal_width in zip(
            binding.producer.fields, widths, decimals, strict=True
        )
    )
    if charge > min(limits.bytes, 8 * 1024 * 1024):
        raise ResultError("LIMIT")
    return charge


def _child_charge(children, count):
    """Struct validity plus each child leaf over ``count`` referenced child rows;
    Text bytes are charged as they are read (32-bit child offsets)."""
    validity = (count + 7) // 8
    return validity + sum(
        validity
        + (4 * (count + 1) if child.field.shape.canonical.name == "Text" else 8 * count)
        for child in children
    )


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


def _decimal_value(value, decimal):
    """Exact fixed-scale encoding, without consulting or changing Decimal context."""
    if type(value) is not Decimal or not value.is_finite():
        raise ResultError("VALUE_DOMAIN")
    sign, digits, exponent = value.as_tuple()
    end = len(digits)
    while end and digits[end - 1] == 0:
        end -= 1
    if not end:
        return Decimal((0, (0,), -decimal.scale))
    assert isinstance(exponent, int)  # Finite Decimal exponents are integers.
    shift = exponent + decimal.scale + len(digits) - end
    if shift < 0 or end + shift > decimal.precision:
        raise ResultError("VALUE_DOMAIN")
    # Only now can the tuple grow, bounded by the retained precision (at most 65).
    return Decimal((sign, digits[:end] + (0,) * shift, -decimal.scale))


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
    elif kind == "Date":
        if type(value) is not date or not DATE_LOWER <= value <= DATE_UPPER:
            raise ResultError("VALUE_DOMAIN")
    elif kind == "Timestamp":
        if not logical:
            if (
                type(value) is not datetime
                or value.tzinfo is not None
                or value.fold != 0
                or not TIMESTAMP_LOWER <= value <= TIMESTAMP_UPPER
            ):
                raise ResultError("VALUE_DOMAIN")
            value = civil_ticks(value)
        if (
            type(value) is not int
            or not MIN_TIMESTAMP_TICKS <= value <= MAX_TIMESTAMP_TICKS
        ):
            raise ResultError("VALUE_DOMAIN")
    elif kind == "UUID":
        if not logical and bound.observation.carrier == "uuid":
            if type(value) is not UUID:
                raise ResultError("VALUE_DOMAIN")
            value = value.bytes
        if type(value) is not bytes or len(value) != 16:
            raise ResultError("VALUE_DOMAIN")
    elif kind == "Decimal":
        return _decimal_value(value, bound.observation.decimal)
    elif kind == "Float":
        if type(value) is not float or not math.isfinite(value):
            raise ResultError("VALUE_DOMAIN")
    else:
        raise ResultError("PRODUCER_UNSUPPORTED")
    return value


def _container(value, bound, children):
    """A logical nested value, independent of any carrier: None for an absent
    container, else one sequence of values per child field, all equally long."""
    if value is None:
        if not bound.nullable:
            raise ResultError("NULL")
        return None
    if type(value) is not tuple:
        raise ResultError("VALUE_DOMAIN")
    if len(value) != len(children):
        raise ResultError("ROW_ARITY")
    if any(type(sequence) not in (tuple, list) for sequence in value):
        raise ResultError("VALUE_DOMAIN")
    sequences = tuple(tuple(sequence) for sequence in value)
    if len({len(sequence) for sequence in sequences}) != 1:
        raise ResultError("ROW_ARITY")
    return sequences


class _Collected:
    """Checked child columns of one nested field, before any Arrow allocation."""

    def __init__(self, children):
        self.offsets = [0]
        self.nulls: list[bool] = []
        self.columns: list[list[Any]] = [[] for _ in children]
        self.text = [0] * len(children)


def build_owned_batch(binding: ArrowResultBinding, rows, *, limits=BatchLimits()):
    return _build_owned_batch_with_usage(binding, rows, limits=limits)[0]


def _build_owned_batch_with_usage(
    binding: ArrowResultBinding, rows, *, limits=BatchLimits()
):
    if type(binding) is not ArrowResultBinding:
        raise ResultError("ARROW_BINDING")
    verify_arrow_binding(binding, binding.producer)
    if type(rows) not in (tuple, list):
        raise ResultError("ROWS")
    fields = binding.producer.fields
    nested = tuple(_children(bound) for bound in fields)
    _dimensions(_width(fields), len(rows), limits)
    charge = _base_charge(binding, len(rows), limits)
    limit = min(limits.bytes, 8 * 1024 * 1024)
    # Each row below charges only its children's growth, so the struct and
    # child arrays' zero-row part (a Text child's first offset) is charged
    # here, before any Arrow allocation, as the verifier charges it.
    charge += sum(_child_charge(c, 0) for c in nested if c is not None)
    if charge > limit:
        raise ResultError("LIMIT")
    text_sizes = [0] * len(fields)
    text_widths = _text_widths(binding.producer, binding.text_offset_widths)
    collected = [None if c is None else _Collected(c) for c in nested]
    child_rows = 0
    copied = []
    for row in rows:
        if type(row) not in (tuple, list) or len(row) != len(fields):
            raise ResultError("ROW_ARITY")
        values = tuple(
            _value(value, bound)
            if children is None
            else _container(value, bound, children)
            for value, bound, children in zip(tuple(row), fields, nested, strict=True)
        )
        for i, (value, width) in enumerate(zip(values, text_widths, strict=True)):
            children, state = nested[i], collected[i]
            if children is not None and state is not None:
                # Count and charge the children before checking their values.
                count = 0 if value is None else len(value[0])
                child_rows += count
                if child_rows > MAX_CHILD_ROWS:
                    raise ResultError("LIMIT")
                before = state.offsets[-1]
                charge += _child_charge(children, before + count)
                charge -= _child_charge(children, before)
                if charge > limit:
                    raise ResultError("LIMIT")
                for k, child in enumerate(children):
                    column = state.columns[k]
                    is_text = child.field.shape.canonical.name == "Text"
                    for element in () if value is None else value[k]:
                        checked = _value(element, child)
                        if is_text and checked is not None:
                            size = _text_bytes(checked, limit - charge)
                            state.text[k] += size
                            if state.text[k] >= 1 << 31:
                                raise ResultError("LIMIT")
                            charge += size
                        column.append(checked)
                state.offsets.append(before + count)
                state.nulls.append(value is None)
            elif width is not None and value is not None:
                size = _text_bytes(value, limit - charge)
                text_sizes[i] += size
                if text_sizes[i] >= 1 << (width - 1):
                    raise ResultError("LIMIT")
                charge += size
        copied.append(values)
    pa = _arrow()
    arrays = []
    for i, state in enumerate(collected):
        kind = binding.schema[i].type
        if state is None:
            arrays.append(
                pa.array([row[i] for row in copied], type=kind, from_pandas=False)
            )
            continue
        # Columnar: never pa.array over nested Python values; a null container
        # owns an empty segment and no struct validity is allocated.
        struct = pa.StructArray.from_arrays(
            [
                pa.array(column, type=child.type, from_pandas=False)
                for column, child in zip(state.columns, kind.value_type, strict=True)
            ],
            fields=list(kind.value_type),
        )
        arrays.append(
            pa.ListArray.from_arrays(
                pa.array(state.offsets, type=pa.int32()),
                struct,
                type=kind,
                mask=pa.array(state.nulls, type=pa.bool_())
                if any(state.nulls)
                else None,
            )
        )
    batch = pa.RecordBatch.from_arrays(arrays, schema=binding.schema)
    usage = _checked_batch_usage(batch, binding, binding.producer, limits=limits)
    return batch, usage


def _verify_schema(schema, binding) -> None:
    pa = _arrow()
    if not isinstance(schema, pa.Schema):
        raise ResultError("ARROW_SCHEMA")
    if len(schema) != len(binding.producer.fields):
        raise ResultError("ARROW_SCHEMA")
    if any(
        _children(bound) is None
        and bound.field.shape.canonical.name == "UUID"
        and type(schema[i].type) is not type(binding.schema[i].type)
        for i, bound in enumerate(binding.producer.fields)
    ):
        raise ResultError("ARROW_SCHEMA")
    if not schema.equals(binding.schema, check_metadata=True):
        raise ResultError("ARROW_SCHEMA")


def verify_batch(batch, binding, producer, *, limits=BatchLimits()) -> None:
    _checked_batch_usage(batch, binding, producer, limits=limits)


def _checked_batch_usage(batch, binding, producer, *, limits=BatchLimits()):
    """Check the supplied carrier, not a rebuilt candidate or a checked flag.

    This proves bounded batch correspondence, not EOF or whole-result completion.
    """
    verify_arrow_binding(binding, producer)
    pa = _arrow()
    if not isinstance(batch, pa.RecordBatch) or not batch.is_cpu:
        raise ResultError("ARROW_BATCH")
    _dimensions(batch.num_columns, batch.num_rows, limits)
    _verify_schema(batch.schema, binding)
    # Identity comes only from batch.schema, never from a column's own type.
    _dimensions(_width(producer.fields), batch.num_rows, limits)
    charge = _base_charge(binding, batch.num_rows, limits)
    limit = min(limits.bytes, 8 * 1024 * 1024)
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
        child_rows = 0
        for i, bound in enumerate(producer.fields):
            text_size = 0
            column = batch.column(i)
            children = _children(bound)
            if children is not None:
                charge, count = _nested_usage(
                    column, bound, children, charge, limit, child_rows
                )
                child_rows += count
                continue
            kind = bound.field.shape.canonical.name
            if kind in ("Timestamp", "UUID"):
                storage = (
                    column.storage
                    if kind == "UUID" and type(column.type) is type(pa.uuid())
                    else column
                )
                if not len(storage):
                    continue
                validity, data = storage.buffers()
                mask = None if validity is None else memoryview(validity)
                payload = memoryview(data)
                width = 8 if kind == "Timestamp" else 16
                for position in range(len(storage)):
                    offset = storage.offset + position
                    if mask is not None and not (mask[offset // 8] >> (offset % 8)) & 1:
                        _value(None, bound, logical=True)
                        continue
                    raw = payload[offset * width : (offset + 1) * width]
                    value = (
                        int.from_bytes(raw, "little", signed=True)
                        if kind == "Timestamp"
                        else bytes(raw)
                    )
                    _value(value, bound, logical=True)
                continue
            for scalar in column:
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
    return charge, retained_bytes


def _nested_usage(column, bound, children, charge, limit, child_rows):
    """Check one supplied nested column after schema identity and full Arrow
    validation; return the new charge and the referenced child rows.

    A zero-length list is never read through a list accessor: PyArrow 26 can
    crash on one whose offsets buffer is absent.
    """
    count = 0
    referenced = None
    if len(column):
        offsets = column.offsets.to_pylist()
        if column.null_count:
            for position, valid in enumerate(column.is_valid().to_pylist()):
                if not valid:
                    if not bound.nullable:
                        raise ResultError("NULL")
                    # The canonical absent container owns an empty segment.
                    if offsets[position + 1] != offsets[position]:
                        raise ResultError("ARROW_BATCH")
        count = offsets[-1] - offsets[0]
        # Validation does not enforce the item's non-null flag.
        referenced = column.values.slice(offsets[0], count)
        if referenced.null_count:
            raise ResultError("NULL")
    if child_rows + count > MAX_CHILD_ROWS:
        raise ResultError("LIMIT")
    charge += _child_charge(children, count)
    if charge > limit:
        raise ResultError("LIMIT")
    if referenced is None or not count:
        return charge, count
    for k, child in enumerate(children):
        text_size = 0
        is_text = child.field.shape.canonical.name == "Text"
        for value in referenced.field(k).to_pylist():
            value = _value(value, child, logical=True)
            if is_text and value is not None:
                size = _text_bytes(value, limit - charge)
                text_size += size
                if text_size >= 1 << 31:
                    raise ResultError("LIMIT")
                charge += size
    return charge, count
