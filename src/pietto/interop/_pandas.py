"""to_pandas: each field as pandas.ArrowDtype of its exact Arrow type."""

from __future__ import annotations

from typing import Any


def convert(name: str, pandas: Any, data: Any) -> Any:
    # ignore_metadata keeps any pandas index metadata from choosing the index.
    frame = data.to_pandas(types_mapper=pandas.ArrowDtype, ignore_metadata=True)
    if type(frame.index) is not pandas.RangeIndex or len(frame.index) != len(data):
        raise ValueError(f"{name}: pandas built another index than a RangeIndex")
    # A changed type, as after a pin drift, is refused.
    for ordinal, (item, dtype) in enumerate(
        zip(data.schema, frame.dtypes, strict=True)
    ):
        wanted = pandas.ArrowDtype(item.type)
        if dtype != wanted:
            raise ValueError(
                f"{name}: field {ordinal} ({item.name!r}) became {dtype} instead"
                f" of {wanted}; {name} never returns a changed type"
            )
    return frame
