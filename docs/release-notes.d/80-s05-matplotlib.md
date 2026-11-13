### Matplotlib artists from a batch

`pietto.interop.plot_line(batch, x, y, *, ax)` draws one
`matplotlib.lines.Line2D` through `ax.plot`, and `plot_scatter(batch, x, y,
*, ax)` one `matplotlib.collections.PathCollection` through `ax.scatter`, on
the Axes the caller passes and on no other, from two fields the schema
declares non-nullable: Float fields, or Int fields whose values all lie
within ±2**53. Each field reaches Matplotlib as a float64 copy in row order,
so the artist's `get_xydata()` or `get_offsets()` equals the source values
bit for bit, `-0.0` included, keeps repeated rows, and stays usable after the
batch is closed; a typed empty batch gives an artist with no points. Neither
call imports `matplotlib.pyplot`, selects a backend, shows or saves.

An `ax` that is not a `matplotlib.axes.Axes` is a `TypeError` before the
batch is read; a Bool, Text or other field, a nullable field and an Int value
beyond ±2**53 are refused with `ValueError` before anything is drawn. Install
them with `pietto[arrow,interop-matplotlib]` (`matplotlib==3.11.2`).
