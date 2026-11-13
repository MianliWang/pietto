"""Alpha interop: one open ResultBatch to one pandas, Polars, NumPy, SciPy or
Matplotlib object.

    from pietto.interop import to_pandas
    frame = to_pandas(batch)

Each function reads the batch once through ``pyarrow.record_batch(batch)``,
never closes it, and returns an object that stays usable after the batch is
closed. Field arguments are field ordinals (an ``int``, never a ``bool``);
labels are never looked up. Errors come in one fixed order: ``TypeError`` for
an argument type (``ax`` is checked only when Matplotlib is installed, so
without it a wrong ``ax`` fails later), ``HandleMisuse`` PIE-R4002 for a
closed batch, ``ValueError``
for an ordinal, field, shape, coordinate or value the adapter does not admit,
and ``ModuleNotFoundError`` when the target's extra is not installed; the
target library's own failures are not wrapped. After the conversion, the
dtypes of a pandas, Polars or NumPy result, the pandas index and the SciPy
type, shape, dtypes, entry count and order are compared with what
docs/interop.md states, and a mismatch is refused with ``ValueError``; no
value, and nothing in a Matplotlib artist, is compared. A refused call leaves
the batch open and draws nothing.

This is an alpha interface. Importing it loads no PyArrow, no target library
and no ``pietto.execution``. See docs/interop.md.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pietto.interop import _common as common

if TYPE_CHECKING:
    import matplotlib.axes  # pyright: ignore[reportMissingImports]
    import matplotlib.collections  # pyright: ignore[reportMissingImports]
    import matplotlib.lines  # pyright: ignore[reportMissingImports]
    import numpy  # pyright: ignore[reportMissingImports]
    import pandas  # pyright: ignore[reportMissingImports]
    import polars  # pyright: ignore[reportMissingImports]
    import scipy.sparse  # pyright: ignore[reportMissingImports]

    from pietto.execution import ResultBatch

__all__ = [
    "plot_line",
    "plot_scatter",
    "to_numpy",
    "to_pandas",
    "to_polars",
    "to_scipy_csr",
]


def to_pandas(batch: ResultBatch) -> pandas.DataFrame:
    """A DataFrame with one column per field, in field order, each of dtype
    ``pandas.ArrowDtype`` of the field's exact Arrow type, and a RangeIndex.

    Int, Bool, Float, Text, Decimal (decimal128), Date and zone-less Timestamp
    fields are admitted, nullable or not; any other field is refused.
    """
    name = "to_pandas"
    common.check_batch(name, batch)
    pa, data = common.read(batch)
    common.admit_frame(name, pa, data)
    module = common.target(name, "pandas")
    from pietto.interop import _pandas

    return _pandas.convert(name, module, data)


def to_polars(batch: ResultBatch) -> polars.DataFrame:
    """A DataFrame with one column per field, in field order, of the Polars
    dtype docs/interop.md maps each admitted Arrow type to.

    The fields to_pandas admits are admitted; any other output dtype than the
    mapped one is refused, never cast.
    """
    name = "to_polars"
    common.check_batch(name, batch)
    pa, data = common.read(batch)
    common.admit_frame(name, pa, data)
    module = common.target(name, "polars")
    from pietto.interop import _polars

    return _polars.convert(name, pa, module, data)


def to_numpy(batch: ResultBatch, column: int) -> numpy.ndarray:
    """An owned, writable copy of one non-nullable Int, Bool or Float field, of
    shape ``(num_rows,)`` and the field's exact width."""
    name = "to_numpy"
    common.check_batch(name, batch)
    common.check_ordinal(name, "column", column)
    pa, data = common.read(batch)
    common.field(name, data, "column", column)
    common.admit_column(name, pa, data, "column", column, common.ARRAY)
    module = common.target(name, "numpy")
    from pietto.interop import _numpy

    return _numpy.convert(name, module, data, column)


def to_scipy_csr(
    batch: ResultBatch,
    row: int,
    column: int,
    value: int,
    shape: tuple[int, int],
) -> scipy.sparse.csr_array:
    """A canonical ``csr_array`` that stores one entry per record, explicit
    zeros included, from three distinct non-nullable Int fields.

    Each dimension of ``shape`` lies between 0 and 4096; a negative,
    out-of-shape or repeated coordinate is refused.
    """
    name = "to_scipy_csr"
    common.check_batch(name, batch)
    for parameter, ordinal in (("row", row), ("column", column), ("value", value)):
        common.check_ordinal(name, parameter, ordinal)
    common.check_shape(name, shape)
    pa, data = common.read(batch)
    for parameter, ordinal in (("row", row), ("column", column), ("value", value)):
        common.field(name, data, parameter, ordinal)
    common.distinct(name, (row, column, value), "row, column and value")
    for parameter, ordinal in (("row", row), ("column", column), ("value", value)):
        common.admit_column(name, pa, data, parameter, ordinal, common.COORDINATE)
    common.check_shape_bounds(name, shape)
    common.check_coordinates(name, data, row, column, shape)
    module = common.target(name, "scipy.sparse")
    from pietto.interop import _scipy

    return _scipy.convert(name, module, data, row, column, value, shape)


def _plotted(name: str, batch: object, x: int, y: int, ax: object) -> object:
    common.check_batch(name, batch)
    common.check_ordinal(name, "x", x)
    common.check_ordinal(name, "y", y)
    common.check_axes(name, ax)
    pa, data = common.read(batch)
    common.field(name, data, "x", x)
    common.field(name, data, "y", y)
    found = (
        common.admit_column(name, pa, data, "x", x, common.PLOT),
        common.admit_column(name, pa, data, "y", y, common.PLOT),
    )
    common.check_envelope(name, data, "x", x, found[0])
    common.check_envelope(name, data, "y", y, found[1])
    common.target(name, "matplotlib")
    return data


def plot_line(
    batch: ResultBatch, x: int, y: int, *, ax: matplotlib.axes.Axes
) -> matplotlib.lines.Line2D:
    """One Line2D on the caller's Axes, through ``ax.plot``, from two
    non-nullable Float fields or Int fields whose values lie within ±2**53."""
    data = _plotted("plot_line", batch, x, y, ax)
    from pietto.interop import _matplotlib

    return _matplotlib.line(data, x, y, ax)


def plot_scatter(
    batch: ResultBatch, x: int, y: int, *, ax: matplotlib.axes.Axes
) -> matplotlib.collections.PathCollection:
    """One PathCollection on the caller's Axes, through ``ax.scatter``, from
    the fields plot_line admits."""
    data = _plotted("plot_scatter", batch, x, y, ax)
    from pietto.interop import _matplotlib

    return _matplotlib.scatter(data, x, y, ax)
