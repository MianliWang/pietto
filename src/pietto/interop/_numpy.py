"""to_numpy: PyArrow's to_numpy, then an owned copy of the field's exact dtype."""

from __future__ import annotations

from typing import Any

from pietto.interop import _common as common

# The kinds to_numpy admits, and those it admits nullable too (D80.03, PL.47):
# a Float null becomes NaN, which no Pietto Float value is, while an Int or
# Bool null has no lossless form in the field's dtype.
ADMITS = ("Int", "Bool", "Float")
NULLABLE = ("Float",)
# Admission leaves only these Arrow types; each keeps its width in NumPy.
DTYPES = {
    "int16": "int16",
    "int32": "int32",
    "int64": "int64",
    "bool": "bool",
    "double": "float64",
}


def convert(name: str, numpy: Any, data: Any, column: int) -> Any:
    item = data.schema.field(column)
    wanted = numpy.dtype(DTYPES[str(item.type)])
    # An Int, or a Float without a null, converts as a read-only view of the
    # batch's buffer, and a Float null as NaN; the copy owns its memory and
    # shares none with the batch.
    array = numpy.array(data.column(column).to_numpy(zero_copy_only=False), copy=True)
    if array.dtype != wanted:
        raise ValueError(
            f"{name}: field {column} ({item.name!r}) became {array.dtype} instead"
            f" of {wanted}; {name} never returns a changed type;"
            f" {common.pinned('numpy')}"
        )
    return array
