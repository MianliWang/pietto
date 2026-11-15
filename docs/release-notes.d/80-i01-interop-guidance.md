### Interop refusals name their fix

Each `ValueError` of `pietto.interop` about a field's type, nullability or
label, a SciPy coordinate, the plot integer range or a target result of
another type now names the rule the call breaks and a fix, and names the
field by ordinal and label where one is involved. The exception classes, the
checks and their order are unchanged, and only the message texts change.
Several messages gain a field label in the middle of the text, so a program
that matches a whole message or its start sees the new text:

- A field of a type the function does not admit ends with the fix: `to_pandas
  and to_polars admit it` for a `Text`, `Date`, `Timestamp`, `Decimal` or
  `Float` field they keep; `make it an Int in the query, for example 1 if flag
  else 0` for a `Bool` field in `to_scipy_csr` or a plot; and `no
  pietto.interop function admits it; leave it out of the query` for a
  `decimal256`, `UUID` or nested field.
- A repeated field label in `to_pandas` adds `so give each field its own label
  in the query`.
- `to_scipy_csr` names the ordinals of fields that are not distinct (`row,
  column and value must name distinct fields, not fields 4, 4 and 0`), and a
  coordinate refusal names both coordinate fields by ordinal and label, then
  the fix: filter the record out with a `where`, pass a shape that holds it,
  or, for a repeated coordinate, give each coordinate one record in the
  query, for example by grouping it by both fields.
- A plot's integer beyond ±2**53 names the field's label too and adds
  `convert the field with Float(...) in the query to accept its rounding, or
  filter the record out with a where`.
- A refusal after the conversion, when the target's result has another type,
  index, shape or entry count, ends with `install the versions that
  "pietto[arrow,interop-X]" pins`, naming the function's extra.

The [interop guide](../interop.md#field-admission) now has a table of what
each function accepts by field type and nullability, the reason for each
refusal with the query form that avoids it, and an
[end-to-end example](../interop.md#an-arrow-table-through-duckdb) that runs a
query over an Arrow table on the DuckDB route and converts the batch with
`to_pandas`.
