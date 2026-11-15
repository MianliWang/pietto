"""The checks every pietto.interop adapter runs, in their fixed order.

First ``TypeError`` for a wrong argument type (``ax`` only when Matplotlib is
installed: without it no Axes exists); then the one read of the batch,
``pyarrow.record_batch(batch)``, which raises ``HandleMisuse`` PIE-R4002 for a
closed batch; then ``ValueError`` for ordinal, admission, shape, coordinate
and envelope failures, schema checks before value checks; then
``ModuleNotFoundError`` when the target library is missing. Importing this
module loads no PyArrow, no target library and no ``pietto.execution``.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from typing import Any

# D67.10's per-batch row ceiling also bounds each dimension of a SciPy shape.
SHAPE_LIMIT = 4096
# Every integer of this magnitude or less is exact in float64.
ENVELOPE = 2**53
ARRAY = ("Int", "Bool", "Float")
COORDINATE = ("Int",)
PLOT = ("Int", "Float")
FRAME = ("Int", "Bool", "Float", "Text", "Decimal", "Date", "Timestamp")
EXTRAS = {
    "pandas": "interop-pandas",
    "polars": "interop-polars",
    "numpy": "interop-numpy",
    "scipy": "interop-scipy",
    "matplotlib": "interop-matplotlib",
}


def check_batch(name: str, batch: object) -> None:
    from pietto.execution import ResultBatch

    if type(batch) is not ResultBatch:
        raise TypeError(
            f"{name}: batch must be a pietto.execution.ResultBatch,"
            f" not {type(batch).__name__}"
        )


def check_ordinal(name: str, parameter: str, value: object) -> None:
    if type(value) is not int:
        raise TypeError(
            f"{name}: {parameter} must be an int field ordinal,"
            f" not {type(value).__name__}"
        )


def check_shape(name: str, shape: object) -> None:
    if (
        type(shape) is not tuple
        or len(shape) != 2
        or any(type(size) is not int for size in shape)
    ):
        raise TypeError(f"{name}: shape must be a tuple of two ints")


def check_axes(name: str, ax: object) -> None:
    axes = sys.modules.get("matplotlib.axes")
    if axes is not None:
        if not isinstance(ax, axes.Axes):
            raise TypeError(
                f"{name}: ax must be a matplotlib.axes.Axes, not {type(ax).__name__}"
            )
    elif importlib.util.find_spec("matplotlib") is not None:
        # Every Axes object has already imported matplotlib.axes.
        raise TypeError(
            f"{name}: ax must be a matplotlib.axes.Axes, not {type(ax).__name__}"
        )
    # Without Matplotlib no Axes exists: the target import reports the extra.


def read(batch: object) -> tuple[Any, Any]:
    """PyArrow and the one imported batch; a closed batch raises PIE-R4002."""
    pa: Any = importlib.import_module("pyarrow")
    return pa, pa.record_batch(batch)


def field(name: str, data: Any, parameter: str, ordinal: int) -> Any:
    count = data.num_columns
    if not 0 <= ordinal < count:
        raise ValueError(
            f"{name}: {parameter} {ordinal} is not a field ordinal of this batch"
            f" (0 <= ordinal < {count})"
        )
    return data.schema.field(ordinal)


def distinct(name: str, ordinals: tuple[int, ...], parameters: str) -> None:
    if len(set(ordinals)) != len(ordinals):
        given = ", ".join(map(str, ordinals[:-1])) + f" and {ordinals[-1]}"
        raise ValueError(
            f"{name}: {parameters} must name distinct fields, not fields {given}"
        )


def kind(pa: Any, data_type: Any) -> str | None:
    """The D80.03 row of an exact Arrow type, or None when no adapter admits it."""
    if data_type in (pa.int16(), pa.int32(), pa.int64()):
        return "Int"
    if data_type == pa.bool_():
        return "Bool"
    if data_type == pa.float64():
        return "Float"
    if data_type in (pa.string(), pa.large_string()):
        return "Text"
    if pa.types.is_decimal128(data_type):
        return "Decimal"
    if data_type == pa.date32():
        return "Date"
    if (
        pa.types.is_timestamp(data_type)
        and data_type.unit == "us"
        and data_type.tz is None
    ):
        return "Timestamp"
    return None


def _listed(kinds: tuple[str, ...]) -> str:
    if len(kinds) == 1:
        return kinds[0]
    return ", ".join(kinds[:-1]) + " or " + kinds[-1]


def pinned(top: str) -> str:
    """The fix for a target result of another type: the qualified pins."""
    return f'install the versions that "pietto[arrow,{EXTRAS[top]}]" pins'


def admit_frame(name: str, pa: Any, data: Any) -> None:
    for ordinal, item in enumerate(data.schema):
        if kind(pa, item.type) is None:
            raise ValueError(
                f"{name}: field {ordinal} ({item.name!r}) has Arrow type"
                f" {item.type}; {name} admits only {_listed(FRAME)} fields"
                " (Decimal up to precision 38); leave it out of the query"
            )


def distinct_labels(name: str, data: Any) -> None:
    # PyArrow gives repeated labels one pandas type, or fails casting them.
    first: dict[str, int] = {}
    for ordinal, item in enumerate(data.schema):
        earlier = first.setdefault(item.name, ordinal)
        if earlier != ordinal:
            raise ValueError(
                f"{name}: field {ordinal} ({item.name!r}) repeats the label of"
                f" field {earlier}; {name} admits only distinct labels, so give"
                " each field its own label in the query"
            )


def admit_column(
    name: str,
    pa: Any,
    data: Any,
    parameter: str,
    ordinal: int,
    kinds: tuple[str, ...],
) -> str:
    item = data.schema.field(ordinal)
    found = kind(pa, item.type)
    if found not in kinds:
        if found is None:
            instead = "no pietto.interop function admits it; leave it out of the query"
        elif found == "Bool":
            instead = "make it an Int in the query, for example 1 if flag else 0"
        else:
            instead = "to_pandas and to_polars admit it"
        raise ValueError(
            f"{name}: {parameter} field {ordinal} ({item.name!r}) has Arrow type"
            f" {item.type}; {name} admits only {_listed(kinds)} fields; {instead}"
        )
    if item.nullable:
        raise ValueError(
            f"{name}: {parameter} field {ordinal} ({item.name!r}) is nullable in"
            " the schema; make it non-nullable in Pietto first, for example with"
            " coalesce"
        )
    return found


def check_shape_bounds(name: str, shape: tuple[int, int]) -> None:
    for index, size in enumerate(shape):
        if not 0 <= size <= SHAPE_LIMIT:
            raise ValueError(
                f"{name}: shape[{index}] is {size}; each dimension must lie"
                f" between 0 and {SHAPE_LIMIT}"
            )


def check_coordinates(
    name: str, data: Any, row: int, column: int, shape: tuple[int, int]
) -> None:
    first: dict[tuple[int, int], int] = {}
    fields = (
        f"row field {row} ({data.schema.field(row).name!r}) and column field"
        f" {column} ({data.schema.field(column).name!r})"
    )
    pairs = zip(
        data.column(row).to_pylist(), data.column(column).to_pylist(), strict=True
    )
    for record, coordinate in enumerate(pairs):
        if coordinate[0] < 0 or coordinate[1] < 0:
            raise ValueError(
                f"{name}: record {record} has the negative coordinate {coordinate}"
                f" in {fields}; coordinates start at 0, so filter such records out"
                " with a where in the query"
            )
        if coordinate[0] >= shape[0] or coordinate[1] >= shape[1]:
            raise ValueError(
                f"{name}: record {record} has the coordinate {coordinate} in"
                f" {fields}, outside the shape {shape}; pass a shape that holds it,"
                f" at most {SHAPE_LIMIT} in each dimension, or filter the record out"
                " with a where in the query"
            )
        earlier = first.setdefault(coordinate, record)
        if earlier != record:
            raise ValueError(
                f"{name}: records {earlier} and {record} have the same coordinate"
                f" {coordinate} in {fields}; {name} stores each coordinate once and"
                " never sums, so give each coordinate one record in the query, for"
                " example by grouping it by both fields"
            )


def check_envelope(
    name: str, data: Any, parameter: str, ordinal: int, found: str
) -> None:
    if found != "Int":
        return
    for record, value in enumerate(data.column(ordinal).to_pylist()):
        if not -ENVELOPE <= value <= ENVELOPE:
            label = data.schema.field(ordinal).name
            raise ValueError(
                f"{name}: {parameter} field {ordinal} ({label!r}) has {value} in"
                f" record {record}, outside the float64-exact range of ±2**53;"
                " convert the field with Float(...) in the query to accept its"
                " rounding, or filter the record out with a where"
            )


def target(name: str, module: str) -> Any:
    """The target library; its absence names the extra that provides it."""
    top = module.partition(".")[0]
    try:
        return importlib.import_module(module)
    except ModuleNotFoundError as missing:
        if missing.name != top:
            raise
    raise ModuleNotFoundError(
        f'{name} needs {top}: install "pietto[arrow,{EXTRAS[top]}]"', name=top
    )
