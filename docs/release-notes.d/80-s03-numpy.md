### NumPy arrays from a batch

`pietto.interop.to_numpy(batch, column)` returns one field of the batch as a
NumPy array of shape `(num_rows,)`: `int16`, `int32` or `int64` for an Int
field of that width, `bool` for a Bool field and `float64` for a Float field.
The array keeps row order, repeated rows and every value bit for bit,
including `2**63 - 1` and the sign of `-0.0`, and a typed empty batch gives
shape `(0,)` with the same dtype. It is an owned, writable copy that shares no
buffer with the batch, so writing to it leaves the batch unchanged and it stays
usable after the batch is closed.

Only a field that the schema declares non-nullable is admitted: a nullable
field is refused with `ValueError` even when the batch holds no null, so
`coalesce` it in Pietto first. Text, Decimal, Date, Timestamp, UUID and nested
fields are refused, and a conversion that would change the field's dtype is
refused, never cast. Install it with `pietto[arrow,interop-numpy]`
(`numpy==2.5.4`).
