### pandas and Polars DataFrames from a batch

`pietto.interop.to_pandas(batch)` returns a pandas DataFrame whose columns
keep field order, row order, repeated rows and null positions, with a
`RangeIndex` and each column of dtype `pandas.ArrowDtype` of the field's exact
Arrow type, so a nullable Int stays an exact integer. `to_polars(batch)`
returns a Polars DataFrame with `Int16`, `Int32`, `Int64`, `Boolean`,
`Float64`, `String`, `Decimal(p, s)`, `Date` and `Datetime("us")` columns.
Both admit nullable and non-nullable Int, Bool, Float, Text, Decimal up to
precision 38, Date and zone-less Timestamp fields; a typed empty batch gives an
empty frame of the same types, and the frame stays usable after the batch is
closed.

A conversion that would change a field's type is refused with `ValueError`,
never cast, and `to_pandas` refuses a batch with a repeated field label the
same way before converting it. Install them with `pietto[arrow,interop-pandas]`
(`pandas==3.1.1`) or
`pietto[arrow,interop-polars]` (`polars==2.1.0`).
