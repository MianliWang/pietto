"""to_scipy_csr: a canonical csr_array from the records' coordinate triplets."""

from __future__ import annotations

from typing import Any

from pietto.interop import _common as common


def convert(
    name: str,
    sparse: Any,
    data: Any,
    row: int,
    column: int,
    value: int,
    shape: tuple[int, int],
) -> Any:
    # The coordinates are checked unique and inside the shape, so building
    # from triplets sums nothing and stores every record, zeros included.
    # They lie below 4096, so int32 holds them exactly; SciPy would keep
    # int64 coordinates as int64 indices.
    rows, columns = (
        data.column(ordinal).to_numpy(zero_copy_only=False).astype("int32")
        for ordinal in (row, column)
    )
    values = data.column(value).to_numpy(zero_copy_only=False)
    matrix = sparse.csr_array((values, (rows, columns)), shape=shape)
    if type(matrix) is not sparse.csr_array:
        raise ValueError(
            f"{name}: scipy built a {type(matrix).__name__} instead of a"
            f" csr_array; {common.pinned('scipy')}"
        )
    built = tuple(int(size) for size in matrix.shape)
    if built != shape:
        raise ValueError(
            f"{name}: scipy built the shape {built} instead of {shape};"
            f" {common.pinned('scipy')}"
        )
    wanted = ("int32", "int32", f"int{data.schema.field(value).type.bit_width}")
    found = tuple(
        str(part.dtype) for part in (matrix.indices, matrix.indptr, matrix.data)
    )
    if found != wanted:
        raise ValueError(
            f"{name}: scipy built {found[0]} indices, {found[1]} index pointers"
            f" and {found[2]} data instead of {wanted[0]}, {wanted[1]} and"
            f" {wanted[2]}; {name} never returns a changed type;"
            f" {common.pinned('scipy')}"
        )
    if matrix.nnz != data.num_rows or not matrix.has_canonical_format:
        raise ValueError(
            f"{name}: scipy did not store the {data.num_rows} records once each"
            f" in canonical order; {common.pinned('scipy')}"
        )
    return matrix
