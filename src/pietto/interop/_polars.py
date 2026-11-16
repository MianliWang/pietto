"""to_polars: polars.from_arrow, then each dtype compared with its mapping."""

from __future__ import annotations

from typing import Any

from pietto.interop import _common as common

# The kinds to_polars admits, nullable or not (D80.03).
ADMITS = ("Int", "Bool", "Float", "Text", "Decimal", "Date", "Timestamp")


def _mapped(pa: Any, polars: Any, data_type: Any) -> Any:
    for arrow, mapped in (
        (pa.int16(), polars.Int16()),
        (pa.int32(), polars.Int32()),
        (pa.int64(), polars.Int64()),
        (pa.bool_(), polars.Boolean()),
        (pa.float64(), polars.Float64()),
        (pa.string(), polars.String()),
        (pa.large_string(), polars.String()),
        (pa.date32(), polars.Date()),
        (pa.timestamp("us"), polars.Datetime("us")),
    ):
        if data_type == arrow:
            return mapped
    # Admission leaves only decimal128 here.
    return polars.Decimal(data_type.precision, data_type.scale)


def convert(name: str, pa: Any, polars: Any, data: Any) -> Any:
    frame = polars.from_arrow(data)
    for ordinal, (item, dtype) in enumerate(
        zip(data.schema, frame.dtypes, strict=True)
    ):
        mapped = _mapped(pa, polars, item.type)
        if type(dtype) is not type(mapped) or dtype != mapped:
            raise ValueError(
                f"{name}: field {ordinal} ({item.name!r}) became {dtype} instead"
                f" of {mapped}; {name} never returns a changed type;"
                f" {common.pinned('polars')}"
            )
    return frame
