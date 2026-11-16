### `Float` values in `to_scipy_csr`

`pietto.interop.to_scipy_csr` now admits a non-nullable `Float` field as its
value, which it refused with the fix to use `to_pandas` or `to_polars`. The
array's data is then float64 and holds each record's value as given,
explicit `0.0` and `-0.0` included, with the sign kept in `matrix.data`. The
coordinates still take only `Int` fields and a nullable field is still
refused. A refused value field's message now gives the value's rule as `Int
or Float fields`, for example `to_scipy_csr: value field 2 ('flag') has Arrow
type bool; to_scipy_csr admits only Int or Float fields; make it an Int in
the query, for example 1 if flag else 0`. See the
[interop guide](../interop.md#scipy).
