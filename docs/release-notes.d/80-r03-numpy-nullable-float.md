### Nullable `Float` fields in `to_numpy`

`pietto.interop.to_numpy` now admits a nullable `Float` field, which it
refused even when the batch held no null. It returns float64 with NaN at each
null and every other value bit for bit, `-0.0` included, as an owned copy
that shares no buffer with the batch; a batch without a null gives float64
too. A nullable `Int` or `Bool` field is still refused with the `coalesce`
fix. See the [interop guide](../interop.md#numpy).
