"""to_pandas: each field as pandas.ArrowDtype of its exact Arrow type, a UUID,
nested too, as its 16-byte storage."""

from __future__ import annotations

from typing import Any

from pietto.interop import _common as common

# The kinds to_pandas admits, nullable or not (D80.03, PL.47).
ADMITS = (
    "Int",
    "Bool",
    "Float",
    "Text",
    "Decimal",
    "Decimal256",
    "Date",
    "Timestamp",
    "UUID",
    "nested",
)


def _mapped(pa: Any, data_type: Any) -> Any:
    # pandas cannot compare, group, sort or merge the UUID extension type, so a
    # UUID becomes its storage, the 16 big-endian bytes (PL.47).
    if data_type == pa.uuid():
        return pa.binary(16)
    if pa.types.is_list(data_type):
        item = data_type.value_field
        fields = [f.with_type(_mapped(pa, f.type)) for f in item.type]
        return pa.list_(item.with_type(pa.struct(fields)))
    return data_type


def convert(name: str, pa: Any, pandas: Any, data: Any) -> Any:
    schema = pa.schema([f.with_type(_mapped(pa, f.type)) for f in data.schema])
    # ignore_metadata keeps any pandas index metadata from choosing the index.
    frame = data.cast(schema).to_pandas(
        types_mapper=pandas.ArrowDtype, ignore_metadata=True
    )
    if type(frame.index) is not pandas.RangeIndex or len(frame.index) != len(data):
        raise ValueError(
            f"{name}: pandas built another index than a RangeIndex;"
            f" {common.pinned('pandas')}"
        )
    # A changed type, as after a pin drift, is refused.
    for ordinal, (item, dtype) in enumerate(zip(schema, frame.dtypes, strict=True)):
        wanted = pandas.ArrowDtype(item.type)
        if dtype != wanted:
            raise ValueError(
                f"{name}: field {ordinal} ({item.name!r}) became {dtype} instead"
                f" of {wanted}; {name} never returns a changed type;"
                f" {common.pinned('pandas')}"
            )
    return frame
