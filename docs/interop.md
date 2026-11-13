# Python interoperability (alpha)

`pietto.interop` turns one open `ResultBatch` into one pandas or Polars
DataFrame, NumPy array, SciPy CSR array or Matplotlib artist on your own Axes.
It is an alpha interface beside `pietto.compiler` and `pietto.execution`, which
it leaves unchanged: its names, refusals and messages may change with
documented notes. It adds no Pietto syntax, CLI command or diagnostic code.

## From a project to a library

A batch comes from any route of the [execution guide](execution.md): a
`ResultHandle` from `execute()`, the `batch` of a `SavedBatch` from a saved
read, or a verified export. Each
function converts that one batch, so a whole result is the sequence of the
objects it returns.

```python
from pietto.execution import execute
from pietto.interop import to_pandas

with execute(query, route="postgres_rows", access=access, premise=premise) as result:
    for batch in result:
        frame = to_pandas(batch)
        batch.close()
        print(frame)
```

## Installing

Each library has its own extra beside `arrow`; there is no combined extra.

| Extra | Pins | Functions |
| --- | --- | --- |
| `pietto[arrow,interop-pandas]` | `pandas==3.1.1` | `to_pandas` |
| `pietto[arrow,interop-polars]` | `polars==2.1.0` (which pins `polars-runtime-32==2.1.0`) | `to_polars` |
| `pietto[arrow,interop-numpy]` | `numpy==2.5.4` | `to_numpy` |
| `pietto[arrow,interop-scipy]` | `scipy==1.18.1` | `to_scipy_csr` |
| `pietto[arrow,interop-matplotlib]` | `matplotlib==3.11.2` | `plot_line`, `plot_scatter` |

Only these pins, with `pyarrow==26.0.1`, on CPython 3.12 and 3.13 on Linux
x86-64 with glibc 2.28 or later, are qualified. Pietto checks no library
version at run time. Another route extra beside an interop extra, such as
`pietto[execute-postgres,interop-pandas]`, is expected to work because it
selects the same PyArrow, but it is not tested on its own.

## Calls

```python
to_pandas(batch)
to_polars(batch)
to_numpy(batch, column)
to_scipy_csr(batch, row, column, value, shape)
plot_line(batch, x, y, *, ax)
plot_scatter(batch, x, y, *, ax)
```

`column`, `row`, `value`, `x` and `y` are field ordinals: an `int` (never a
`bool`) with `0 <= ordinal < field count`. A field label is never looked up.
No function takes other keyword arguments.

Each call reads the batch once through `pyarrow.record_batch(batch)` and
never closes it. The returned object is yours and stays usable after
`batch.close()`, because the imported Arrow data keeps its buffers.

## Errors

Every call checks in this order and raises the first failure:

1. `TypeError` for an argument of the wrong type, in parameter order, before
   PyArrow or any target library is imported. `ax` is the one exception: it
   is checked only when Matplotlib is installed, so without Matplotlib a
   wrong `ax` passes this step and the call fails at a later one: with
   `HandleMisuse` `PIE-R4002` for a closed batch, otherwise with `ValueError`
   or `ModuleNotFoundError`.
2. `HandleMisuse` `PIE-R4002` for a closed batch, as any export of it.
3. `ValueError` for an ordinal outside the batch, then a field the function
   does not admit (its type, or a nullable field where a non-nullable one is
   needed), then a SciPy shape, then values: SciPy coordinates and the
   Matplotlib integer range. An admission message names the field by
   ordinal and label and, for a nullable field, the Pietto-side fix, such as
   `coalesce`; a coordinate or range message names the record, and a range
   message also the field's ordinal.
4. `ModuleNotFoundError` when the function's extra is not installed, naming
   that extra; its `name` is the missing library.
5. The target library's own failures, which are not wrapped.
6. `ValueError` when the target's result fails the comparison the function
   makes after the conversion: the result is refused, never converted.
   `to_pandas` compares the index, a `RangeIndex` of the batch's row count,
   and each column's dtype; `to_polars` each column's dtype; `to_numpy` the
   array's dtype; and `to_scipy_csr` the array's type and shape, its index,
   index-pointer and data dtypes, its entry count and its canonical order.
   No function compares the converted values, coordinates, null positions,
   row order or labels with the batch, `to_polars` does not compare the row
   count and `to_numpy` does not compare the shape. `plot_line` and
   `plot_scatter` have no such step: they compare nothing in the artist that
   Matplotlib returns.

A refused call leaves the batch open and adds nothing to an Axes.

## Field admission

| Arrow field | `to_pandas` | `to_polars` | `to_numpy` | `to_scipy_csr` | `plot_line`, `plot_scatter` |
| --- | --- | --- | --- | --- | --- |
| int16, int32, int64 (Int) | yes | yes | non-nullable | non-nullable | non-nullable, every value within ±2**53 |
| bool | yes | yes | non-nullable | refused | refused |
| float64 (Float) | yes | yes | non-nullable | refused | non-nullable |
| string, large_string (Text) | yes | yes | refused | refused | refused |
| decimal128 (Decimal up to precision 38) | yes | yes | refused | refused | refused |
| date32 (Date) | yes | yes | refused | refused | refused |
| timestamp[us] without a time zone | yes | yes | refused | refused | refused |
| decimal256, UUID, nested | refused | refused | refused | refused | refused |

pandas and Polars admit nullable fields and keep each null where it is. The
other functions read nullability from the schema, never from one batch's
values, so two batches of one query get the same answer: `coalesce` a field
in Pietto to make it non-nullable. Float values are finite by the result
contract, so no function checks them. A batch with no rows returns the
target's empty object with the same types.

## pandas

`to_pandas(batch)` returns a `pandas.DataFrame` with one column per field in
field order and a `RangeIndex`. Each column's dtype is
`pandas.ArrowDtype` of the field's exact Arrow type, for example
`int16[pyarrow]` or `decimal128(38, 2)[pyarrow]`: never NumPy's float64 for a
nullable Int, an object column or pandas' default string dtype. A null stays
`<NA>`. pandas' default `to_pandas()` would turn a nullable
Int into float64, losing `2**63 - 1`, which is why the call always maps
through `ArrowDtype`. Any other index or column dtype is refused with
`ValueError`, never cast.

## Polars

`to_polars(batch)` returns a `polars.DataFrame` from `polars.from_arrow` with
one column per field in field order and these dtypes:

| Arrow field | Polars dtype |
| --- | --- |
| int16, int32, int64 | `Int16`, `Int32`, `Int64` |
| bool | `Boolean` |
| float64 | `Float64` |
| string, large_string | `String` |
| decimal128(p, s) | `Decimal(p, s)` |
| date32 | `Date` |
| timestamp[us] | `Datetime("us")` |

Any other output dtype is refused with `ValueError`, never cast.

## NumPy

`to_numpy(batch, column)` takes one non-nullable Int, Bool or Float field and
returns an owned, writable copy of shape `(num_rows,)` with the field's exact
width.

| Arrow field | NumPy dtype |
| --- | --- |
| int16, int32, int64 | `int16`, `int32`, `int64` |
| bool | `bool` |
| float64 | `float64` |

The array keeps row order, repeated rows and every value bit for bit,
including `-2**63`, `2**63 - 1` and the sign of `-0.0`. A batch with no rows
gives shape `(0,)` with the same dtype. The array owns its memory and shares
no buffer with the batch, so writing to it leaves the batch unchanged, and it
stays usable after `batch.close()`.

A nullable field is refused even when the batch holds no null, so that every
batch of a query gets the same answer. A null would make an Int field float64
with NaN, losing `2**63 - 1`, a Bool field an object array and a Float null a
NaN; `coalesce` the field in Pietto first. A conversion that would give
another dtype than the field's is refused with `ValueError`, never cast.

## SciPy

`to_scipy_csr(batch, row, column, value, shape)` takes three distinct
non-nullable Int fields and a `shape` of two `int` values, each between 0 and
4096. It returns a canonical `scipy.sparse.csr_array` that stores one entry
per record, explicit zeros included; a negative, out-of-shape or repeated
coordinate is refused. CSR allocates `shape[0] + 1` index pointers whatever
the records, which is why the shape has its own bound.

```python
from pietto.interop import to_scipy_csr

matrix = to_scipy_csr(batch, 0, 1, 2, (100, 100))
```

Each record is one entry: its `row` and `column` fields give the coordinate
and its `value` field the value. The array is canonical: the column indices
are sorted within each row and no coordinate repeats; the index and
index-pointer arrays are int32, and the data has the value field's width,
int16, int32 or int64. The same records in any order therefore give the same
arrays. A zero value stays stored, so `matrix.nnz` is the batch's row count,
and a repeated coordinate is refused, never summed. A batch with no rows
gives an array of the given shape with no entries. If SciPy builds anything
else, another type, shape, index dtype, data width or entry count, or
indices out of order, the call is refused with `ValueError`, never converted.

## Matplotlib

`plot_line(batch, x, y, *, ax)` and `plot_scatter(batch, x, y, *, ax)` draw
one artist on the Axes you pass, through `ax.plot` or `ax.scatter`. Without
the extra, both raise `ModuleNotFoundError` whatever `ax` is, after the other
checks. They never import `matplotlib.pyplot`, select no backend and never
show or save.

```python
from matplotlib.figure import Figure
from pietto.interop import plot_line, plot_scatter

figure = Figure()
ax = figure.add_subplot()
line = plot_line(batch, 0, 1, ax=ax)
points = plot_scatter(batch, 0, 2, ax=ax)
```

`x` and `y` each name a field that the schema declares non-nullable: a Float
field, or an Int field whose values all lie within ±2**53
(9,007,199,254,740,992), where float64 holds every integer exactly. Every
value is checked before anything is drawn, and a value beyond the bound, such
as `2**53 + 1`, is refused with `ValueError` naming the parameter, the field's
ordinal, the value and its record. Bool, Text and every other field is
refused, and so is a nullable field even when this batch holds no null.

Each field becomes a float64 copy in row order, so repeated rows stay
repeated and nothing is sorted. `plot_line` returns the one
`matplotlib.lines.Line2D` that `ax.plot` makes, and `plot_scatter` the
`matplotlib.collections.PathCollection` that `ax.scatter` makes. The artist's
`get_xydata()` (for the line) or `get_offsets()` (for the scatter) holds the
source values bit for bit, `-0.0` included; how Matplotlib renders them is not
promised. A batch with no rows gives an artist with no points, whose data has
shape `(0, 2)`. The artist keeps its own copy of the values and stays usable
after `batch.close()`.

`ax` must be a `matplotlib.axes.Axes`: anything else, such as the `Figure`
itself, is a `TypeError` before the batch is read, so it comes before
`PIE-R4002` for a closed batch. Only the Axes you pass gets the artist, even
when its Figure's current Axes is another one, and a refused call adds
nothing to it. Each call passes `ax.plot` or `ax.scatter` the two float64
arrays and no keyword argument, so style and labels stay yours to set, and
no dates or other unit types reach Matplotlib. Importing `matplotlib.figure`
to make the Figure already writes
Matplotlib's font cache; the two calls add no file to its configuration
directory.

## Effects of the libraries

Pietto adds no cache, thread, file, network or database access, and no call
is asynchronous, so there is nothing to cancel. The space of a call is one
batch (at most 4,096 rows and 8 MiB) plus the returned object. The libraries
keep their own effects: PyArrow and Polars run thread pools, and Matplotlib
writes its font cache, `fontlist-v3.11.0.json`, into its configuration
directory (`MPLCONFIGDIR`, by default `$HOME/.cache/matplotlib` on Linux) as
soon as `matplotlib.figure` is imported, even without `pyplot`. PyArrow's
import effects are those the
[execution guide](execution.md) lists.
