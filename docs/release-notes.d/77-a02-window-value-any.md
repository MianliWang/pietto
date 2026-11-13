### An `any(...)` test as a window value is refused without a crash

When the value of `lag`, `lead`, `first_value`, `last_value` or
`nth_value`, or a `lag`/`lead` default, was an `any(...)` test, `check`,
`check --project` and single-file `emit-sql` stopped with a Python
traceback (`ValueError: Unsupported navigation expression: AnyExpr`) and
`pietto lsp` exited when such a buffer was opened. Such a value is no direct
field: a single file now reports PIE-S2104 at the call (`value must be a
direct field or Bool, Text, Int, Float, or NULL literal`, or `default must
be ...`). A project fails closed at the call too: with PIE-S2104 over JOIN
inputs, as a single file does, and with PIE-S2103 over a single input, as
it already does for a window whose PARTITION BY or ORDER BY reads
`any(...)`. No accepted program changes.
