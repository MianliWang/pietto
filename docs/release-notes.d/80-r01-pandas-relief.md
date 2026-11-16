### UUID, wide Decimal and nested fields in `to_pandas`

`pietto.interop.to_pandas` now converts three kinds of field that it refused:

- A `UUID` becomes a column of dtype `ArrowDtype(fixed_size_binary(16))` that
  holds its 16 big-endian bytes unchanged, one `bytes` value per row:
  `uuid.UUID(bytes=b)` restores it and `u.bytes` compares with it. pandas
  compares, groups, sorts and merges such a column.
- A `Decimal` above precision 38 keeps its exact type,
  `ArrowDtype(decimal256(p, s))`.
- One level of nesting, a list of non-null structs of fields that `to_pandas`
  admits, keeps its exact type, each `UUID` child as its 16 bytes. A missing
  container stays `<NA>`, distinct from an empty list.

Deeper or other shapes stay refused. A refusal of such a field in another
function now names the frame functions that admit it in place of "leave it
out of the query": when `to_numpy`, `to_scipy_csr` or a plot refuses a `UUID`
or a nested field without a `decimal256` child, its message ends with
`to_pandas and to_polars admit it`, for example `to_numpy: column field 2
('key_value') has Arrow type extension<arrow.uuid>; to_numpy admits only Int,
Bool or Float fields; to_pandas and to_polars admit it`, and when one of them
or `to_polars` refuses a `Decimal` above precision 38, alone or as a child of
a nested field, with `to_pandas admits it`. A `to_pandas` refusal of a field
lists `UUID` and nested fields among the kinds it admits. See the
[interop guide](../interop.md#pandas).
