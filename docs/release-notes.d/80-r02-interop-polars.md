### UUID and nested fields in `to_polars`

`pietto.interop.to_polars` now admits a `UUID` field as Polars `Binary`,
each value its 16 bytes unchanged, and one level of nesting, a list of
non-null structs of the fields it admits, as `List(Struct(...))` with each
child mapped like a field of its type; a missing outer-JOIN container stays
null, distinct from `[]`. A `decimal256` field, alone or inside a nested
field, is still refused before the call imports Polars, which cannot read
it, and its message now names `to_pandas` as the fix in place of "leave it
out of the query"; a `to_polars` refusal of a field lists `UUID` and nested
fields among the kinds it admits. A call that such a `UUID` or nested field
made fail now returns a DataFrame. See the [interop guide](../interop.md#polars).
