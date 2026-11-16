### Nullable fields in `plot_line` and `plot_scatter`

`pietto.interop.plot_line` and `plot_scatter` now admit a nullable `Int` or
`Float` field, which they refused even when the batch held no null. A null
becomes NaN: the line breaks there and the scatter draws no point for that
record, while the artist keeps one row per record in row order and every
other value bit for bit. The ±2**53 check of an `Int` field skips nulls, and
a value beyond it is still refused, naming its record. See the
[interop guide](../interop.md#matplotlib).
