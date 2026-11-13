### Python interop package (alpha)

The new alpha package `pietto.interop` names six functions that each turn one
open `ResultBatch` into one library object: `to_pandas(batch)`,
`to_polars(batch)`, `to_numpy(batch, column)`,
`to_scipy_csr(batch, row, column, value, shape)`, and
`plot_line(batch, x, y, *, ax)` and `plot_scatter(batch, x, y, *, ax)`.
Field arguments are `int` field ordinals, never labels. Importing the package
loads no PyArrow, no target library and no `pietto.execution`.

Each call reads the batch once through `pyarrow.record_batch(batch)`, never
closes it, and checks in one fixed order: `TypeError` for an argument type
(for `ax` only when Matplotlib is installed), `HandleMisuse` `PIE-R4002` for
a closed batch, `ValueError` for an ordinal,
an unadmitted or nullable field, a SciPy shape above 4096 or a negative,
out-of-shape or repeated coordinate, or a Matplotlib integer beyond ±2**53,
and `ModuleNotFoundError`, naming the extra, when the target library is not
installed. A refused call leaves the batch open. Decimal256, UUID and nested
fields are refused by every function. No diagnostic code is added, and
`pietto.compiler` and `pietto.execution` are unchanged. The
[interop guide](../interop.md) lists every refusal.
