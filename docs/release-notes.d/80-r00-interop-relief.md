### Repeated labels in `to_polars`

`pietto.interop.to_polars` now refuses a batch with a repeated field label
before it imports Polars, as `to_pandas` does, with a `ValueError` that names
the field, the ordinal of the earlier field with that label and the fix:
`to_polars: field 1 ('same') repeats the label of field 0; to_polars admits
only distinct labels, so give each field its own label in the query`. Polars'
own `polars.exceptions.DuplicateError` no longer reaches the caller for such a
batch, so a program that caught it must catch the `ValueError` instead. See
the [interop guide](../interop.md#polars).
