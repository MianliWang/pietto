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

The extras are the qualified path, not the only one. `pietto[arrow]` with a
target library of another version that you install yourself is expected to
run, because Pietto checks no library version, but it is neither qualified
nor tested: a result that fails the comparison of step 6 in
[Errors](#errors) is refused with the fix to install the pinned versions, and
a change that the comparison does not cover goes unnoticed. PyArrow must
still be `pyarrow==26.0.1`, which `pietto[arrow]` installs: the Arrow routes
refuse another version with `PIE-R2002` `ARROW_DEPENDENCY_VERSION` (see
[Install](execution.md#install) in the execution guide).

## An Arrow table through DuckDB

The [DuckDB Arrow route](execution.md#duckdb-arrow-route) runs a query over an
Arrow table that your program holds, in process, so this example needs no
database server. It needs `pip install "pietto[execute-duckdb,interop-pandas]"`,
a route extra beside an interop extra as described above.

A project directory holds three files. `pietto.toml`:

```toml
schema_version = 2

[sources]
include = ["*.pietto"]
```

`main.pietto` declares the table's shape, its source and one query:

```pietto
shape Reading:
    station: Int
    level: Float

source readings: Reading = duckdb.arrow("readings")

query high(floor: Int):
    from readings
    where station >= floor
    select:
        station
        level
```

`contract.json` describes the table's columns by the rules of the
[route](spec/duckdb-arrow-route-v1.md#emission-contract-values):

```json
{
  "format": "pietto.emission-contract.v1",
  "target": {"family": "duckdb", "release": "2.0.0"},
  "sources": [{
    "selector": {"module": "main.pietto", "kind": "source", "name": "readings"},
    "relation": {"namespace": "arrow", "name": "readings"},
    "scan": "arrow_registration",
    "fields": [
      {"ordinal": 0, "name": "station", "column": "station",
       "representation": {"storage": {"kind": "arrow_int64"}, "nullable": false,
                          "domain": {"kind": "int_range", "min": "0", "max": "1000"}}},
      {"ordinal": 1, "name": "level", "column": "level",
       "representation": {"storage": {"kind": "arrow_float64"}, "nullable": false,
                          "domain": {"kind": "finite_float", "format": "binary64"}}}
    ],
    "premises": [
      {"key": "row_domain_matches", "scope": "source", "value": true},
      {"key": "read_only_object", "scope": "source", "value": true}
    ]
  }],
  "environment": [
    {"key": "client_encoding", "scope": "statement", "value": "UTF8"},
    {"key": "operator_environment", "scope": "statement", "value": "builtin_only"},
    {"key": "parameter_protocol", "scope": "statement", "value": "duckdb_prepared"}
  ]
}
```

`analyze.py`, run from that directory, builds the table, runs the query and
converts each batch:

```python
import pyarrow as pa

from pietto.execution import DuckDBArrowInput, compile_query, execute
from pietto.interop import to_pandas

readings = pa.table({"station": [1, 2, 3, 4], "level": [0.5, 1.5, 2.5, 3.5]})
query = compile_query(".", module="main.pietto", kind="query", name="high",
                      dialect="duckdb", emission_contract="contract.json")
with execute(query, route="duckdb_arrow",
             access=DuckDBArrowInput(name="readings", table=readings),
             premise=None, parameters={"floor": 2}) as result:
    for batch in result:
        frame = to_pandas(batch)
        batch.close()
        print(frame.sort_values("station").to_string(index=False))
        print(frame["level"].mean())
```

It prints:

```text
 station  level
       2    1.5
       3    2.5
       4    3.5
2.5
```

The route's results have no order, so the example sorts the frame. Both
fields are non-nullable, so with their extras `to_numpy(batch, 1)` and
`plot_line(batch, 0, 1, ax=ax)` take the same batch.

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
3. `ValueError` for an ordinal outside the batch, then, in `to_scipy_csr`,
   fields that are not distinct, then a field the function does not admit
   (its type, or a nullable field where a non-nullable one is needed), then,
   in `to_pandas` and `to_polars`, a field whose label an earlier field
   already has, whatever their types, then a SciPy shape, then values: SciPy
   coordinates and the Matplotlib integer range. A message about a field's
   type, nullability or label, a SciPy coordinate or the integer range names
   the function, the field it is about by ordinal and label (both coordinate
   fields for a SciPy coordinate), the rule the call breaks and a fix from
   [Refusals and fixes](#refusals-and-fixes): a change to the query, such as
   `coalesce` for a nullable field, or another function, such as `to_pandas`
   for a `Text` field. A repeated label's message also names the earlier
   field's ordinal, and a coordinate or range message names the record. A
   message about an ordinal outside the batch or a SciPy shape names the
   value given and the valid range, and one about SciPy fields that are not
   distinct names the ordinals given.
4. `ModuleNotFoundError` when the function's extra is not installed, naming
   that extra; its `name` is the missing library.
5. The target library's own failures, which are not wrapped.
6. `ValueError` when the target's result fails the comparison the function
   makes after the conversion: the result is refused, never converted. Its
   message names the extra whose pinned versions to install, because only
   those are qualified.
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

What each function accepts, by the field's Pietto type and its Arrow type in
the batch, for a field the schema declares non-nullable and for a nullable
one (`T | None`). A letter names the row of
[Refusals and fixes](#refusals-and-fixes) that says why and what to write
instead.

| Field (Arrow type) | `to_pandas` | `to_polars` | `to_numpy` | `to_scipy_csr` | `plot_line`, `plot_scatter` |
| --- | --- | --- | --- | --- | --- |
| `Int` (int16, int32, int64) | yes; nullable too | yes; nullable too | yes; nullable: no (A) | yes; nullable: no (A) | yes, every value within ±2**53 (D); nullable too, a null as NaN |
| `Float` (float64) | yes; nullable too | yes; nullable too | yes; nullable too, a null as NaN | as the value, not as a coordinate (B); nullable: no (A) | yes; nullable too, a null as NaN |
| `Bool` (bool) | yes; nullable too | yes; nullable too | yes; nullable: no (A) | no (C) | no (C) |
| `Text` (string, large_string) | yes; nullable too | yes; nullable too | no (B) | no (B) | no (B) |
| `Date` (date32) | yes; nullable too | yes; nullable too | no (B) | no (B) | no (B) |
| `Timestamp` (timestamp[us], no time zone) | yes; nullable too | yes; nullable too | no (B) | no (B) | no (B) |
| `Decimal` up to precision 38 (decimal128) | yes; nullable too | yes; nullable too | no (B) | no (B) | no (B) |
| `Decimal` above precision 38 (decimal256) | yes; nullable too | no (E) | no (E) | no (E) | no (E) |
| `UUID` (extension `arrow.uuid`) | yes, as its 16 bytes; nullable too | yes, as its 16 bytes; nullable too | no (B) | no (B) | no (B) |
| nested: one level, a list of non-null structs of the types above | yes; nullable too | yes, unless a child is a decimal256 (E); nullable too | no (B; E if a child is a decimal256) | no (B; E if a child is a decimal256) | no (B; E if a child is a decimal256) |
| any other Arrow type, such as a deeper nesting | no (F) | no (F) | no (F) | no (F) | no (F) |

pandas and Polars admit nullable fields and keep each null where it is, a
nested field's null container too, distinct from an empty list. `to_numpy`
admits a nullable `Float` field and the plots a nullable `Int` or `Float`
field, and give NaN for each null; a Pietto `Float` is never NaN, so a NaN
stands only for a null. `to_numpy` for an `Int` or `Bool` field and
`to_scipy_csr` read nullability from the schema, never from one batch's
values, so two batches of one query get the same answer, even when a batch
holds no null. Float values are finite by the result contract, so no function
checks them. A batch with no rows returns the target's empty object with the
same types.

### Refusals and fixes

Each fix below is a change to the query or a call of another function. The
query forms compile on a PostgreSQL project. A MySQL project compiles them
too, except the two aggregate forms, which it can block (`PIE-B1004` for
`sum(v)` of an `Int`, `PIE-B1003` for `coalesce` of an aggregate). The DuckDB
route admits direct reads of fields, `group by` keys and the aggregates
`count`, `sum` of an `Int` field, `min` and `max`, filtered by comparisons in
`where` and `having`, but no computed value, so a `coalesce`, a conditional
expression or `Float(...)` cannot be written there; the fix there is a
`where`, or `to_pandas` or `to_polars`.

| | Refused | Why | What to do instead |
| --- | --- | --- | --- |
| A | A nullable `Int` or `Bool` field in `to_numpy`; a nullable field in `to_scipy_csr` | A null would make an Int array float64 with NaN, losing `2**63 - 1`, and a Bool array an object array; a sparse array has no entry for a null, because a missing entry means 0. | Make the field non-nullable in the query: `level = coalesce(level, 0.0)`. The default has the field's type: `0.0` for a `Float`, `0` for an `Int`. A grouped `sum` is nullable too: for an `Int` field `v`, write `v = coalesce(sum(v), 0)`. |
| B | `Text`, `Date`, `Timestamp`, `Decimal` up to precision 38, `UUID` or a nested field without a decimal256 child in `to_numpy`, `to_scipy_csr` or a plot; a `Float` coordinate in `to_scipy_csr` | These functions return or draw only exact numeric arrays: an Int, Bool or Float array for `to_numpy`, Int coordinates and Int or Float values for `to_scipy_csr`, and float64 values for a plot. | Convert the batch with `to_pandas` or `to_polars`, which keep the field's type, a `UUID` as its 16 bytes. |
| C | `Bool` in `to_scipy_csr` or a plot | The same exact numeric arrays; a Bool is not an Int. | Make it an `Int` in the query: `ok = 1 if ok else 0`. |
| D | An `Int` value beyond ±2**53 in a plot | A plot passes float64 values to Matplotlib, and float64 holds integers exactly only within ±2**53. | Convert the field in the query with `Float(n)` to accept the rounding, or filter such rows out with a `where`. |
| E | `Decimal` above precision 38, alone or as a child of a nested field, in any function but `to_pandas` | Polars 2.1.0 cannot read decimal256 at any precision, so `to_polars` refuses it before it imports Polars; the other functions return or draw only numeric arrays. | Convert the batch with `to_pandas`, which keeps the exact type. |
| F | Any other Arrow type, such as a deeper nesting | No function has a tested mapping for it. | Leave the field out of the query's select. |

The other refusals name their fix too: give a repeated field label its own
label in the query (`to_pandas`, `to_polars`); pass three distinct fields and
a shape of at most 4096 in each dimension to `to_scipy_csr`; and for a
coordinate that is negative, outside the shape or repeated, filter the record
out with a `where`, pass a larger shape, or give each coordinate one record,
for example by grouping the query by both coordinate fields and writing the
`Int` value as `coalesce(sum(v), 0)`.

## pandas

`to_pandas(batch)` returns a `pandas.DataFrame` with one column per field in
field order and a `RangeIndex`. Each column's dtype is
`pandas.ArrowDtype` of the field's exact Arrow type, for example
`int16[pyarrow]`, `decimal128(38, 2)[pyarrow]` or
`decimal256(65, 30)[pyarrow]`, except that a `UUID` becomes
`fixed_size_binary[16][pyarrow]`: never NumPy's float64 for a nullable Int, an
object column or pandas' default string dtype. A null stays `<NA>`. pandas'
default `to_pandas()` would turn a nullable
Int into float64, losing `2**63 - 1`, which is why the call always maps
through `ArrowDtype`. Any other index or column dtype is refused with
`ValueError`, never cast. So is a batch with a repeated field label, before
the call imports pandas, because PyArrow would give the repeated columns one
type or fail to convert them: give each field its own label.

A `UUID` column holds each value's 16 big-endian bytes unchanged, one `bytes`
value per row: `uuid.UUID(bytes=b)` restores a value and `u.bytes` gives the
bytes to compare with. pandas compares, groups, sorts and merges such a
column, which it cannot do with the UUID extension type itself. A nested
field keeps its exact type, `list<item: struct<...> not null>[pyarrow]`, with
each `UUID` child as its 16 bytes too; a missing container, as an outer JOIN
leaves it, stays `<NA>`, distinct from an empty list.

Three behaviors of pandas 3.1.1 need care with these columns:

- `isin` with a Python `list` or `set` of `bytes` silently misses every value
  that holds a `0x00` byte, because pandas first makes NumPy fixed-width bytes
  of it, which end at the first `0x00`. Pass a `Series` of the column's dtype
  instead: `frame["key"].isin(pandas.Series(keys, dtype=frame["key"].dtype))`.
- A nested column cannot be compared: `==`, even of a column with itself,
  silently gives `False` for every row, and `!=` gives `True`. Grouping,
  sorting, `unique`, `drop_duplicates` and `merge` on it raise
  `ArrowNotImplementedError`.
- `merge` matches null keys with each other, unlike a SQL JOIN.

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
| extension `arrow.uuid` | `Binary`, each value its 16 big-endian bytes |
| `list<item: struct<...> not null>` | `List(Struct(...))`, each child mapped by this table |

Any other output dtype is refused with `ValueError`, never cast; for a nested
field each child's dtype is compared too. So is a batch with a repeated field
label, before the call imports Polars, which would refuse it without naming
either field's ordinal: give each field its own label. A `decimal256` field,
alone or as a child of a nested field, is refused before the call imports
Polars, which cannot read it at any precision: convert such a batch with
`to_pandas`. A missing container of a nested field stays null, distinct from
`[]`.

A `UUID` column compares in an expression with the value's bytes, such as
`frame.filter(polars.col("key") == u.bytes)`: a `uuid.UUID` is not a Polars
literal, and `==` between the `Series` itself and `bytes` raises
`ShapeError`. `join` leaves null keys unmatched unless you pass
`nulls_equal=True`.

## NumPy

`to_numpy(batch, column)` takes one non-nullable Int or Bool field, or one
Float field, nullable or not, and returns an owned, writable copy of shape
`(num_rows,)` with the field's exact width.

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

A nullable Float field gives float64 with NaN at each null and every other
value bit for bit, also in a batch that holds no null. A Pietto `Float` is
never NaN, so a NaN stands only for a null, and NumPy propagates it: use
`numpy.nanmean` and its kin to skip nulls. A nullable Int or Bool field is
refused even when the batch holds no null, so that every batch of a query
gets the same answer: a null would make an Int field float64 with NaN, losing
`2**63 - 1`, and a Bool field an object array; `coalesce` the field in Pietto
first. A conversion that would give another dtype than the field's is refused
with `ValueError`, never cast.

## SciPy

`to_scipy_csr(batch, row, column, value, shape)` takes three distinct
non-nullable fields, Int `row` and `column` coordinates and an Int or Float
`value`, and a `shape` of two `int` values, each between 0 and 4096. It
returns a canonical `scipy.sparse.csr_array` that stores one entry per
record, explicit zeros included; a negative, out-of-shape or repeated
coordinate is refused. CSR allocates `shape[0] + 1` index pointers whatever
the records, which is why the shape has its own bound.

```python
from pietto.interop import to_scipy_csr

matrix = to_scipy_csr(batch, 0, 1, 2, (100, 100))
```

Each record is one entry: its `row` and `column` fields give the coordinate
and its `value` field the value. The array is canonical: the column indices
are sorted within each row and no coordinate repeats; the index and
index-pointer arrays are int32, and the data has the value field's type,
int16, int32, int64 or float64. The same records in any order therefore give
the same arrays. A zero value stays stored, so `matrix.nnz` is the batch's row
count, and a repeated coordinate is refused, never summed. A Float `-0.0` is
stored as given: `matrix.data` and `matrix.tocoo()` keep its sign, while
`matrix[i, j]`, `toarray()` and `todense()` give `0.0`. A batch with no rows
gives an array of the given shape with no entries. If SciPy builds anything
else, another type, shape, index or data dtype or entry count, or indices
out of order, the call is refused with `ValueError`, never converted. A
nullable field is refused, because a sparse array has no entry for a null: a
missing entry means 0.

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

`x` and `y` each name a field, nullable or not: a Float field, or an Int
field whose values all lie within ±2**53 (9,007,199,254,740,992), where
float64 holds every integer exactly. Every value is checked before anything
is drawn, and a value beyond the bound, such as `2**53 + 1`, is refused with
`ValueError` naming the parameter, the field's ordinal and label, the value,
its record and the fix (D in [Refusals and fixes](#refusals-and-fixes)); a
null is not checked. Bool, Text and every other field is refused.

Each field becomes a float64 copy in row order, so repeated rows stay
repeated and nothing is sorted. `plot_line` returns the one
`matplotlib.lines.Line2D` that `ax.plot` makes, and `plot_scatter` the
`matplotlib.collections.PathCollection` that `ax.scatter` makes. The artist's
`get_xydata()` (for the line) or `get_offsets()` (for the scatter) holds the
source values bit for bit, `-0.0` included, one row per record. A null becomes
NaN: the line breaks there, `get_xydata()` holds NaN at that place, and the
scatter draws no point for a record with a null in either field, whose row
`get_offsets()`, a masked array, masks. How Matplotlib renders the values is
not promised. A batch with no rows gives an artist with no points, whose data
has shape `(0, 2)`. The artist keeps its own copy of the values and stays
usable after `batch.close()`.

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
