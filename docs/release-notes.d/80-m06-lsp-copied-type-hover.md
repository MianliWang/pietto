### Hover over a `def` call or a relationship call

In a single file, the alpha `pietto lsp` server no longer answers hover over a
`def` call or a relationship call's arguments with the type of a conversion
that the `def` body or the relationship template writes, and a relationship
call whose template writes a conversion now has its hover and definition, as
other relationship calls do. Such a conversion keeps its hover where a
relationship template writes it; one in a `def` body has none.

Before (measured at `22046a4f` on Linux with CPython 3.13.13): with
`def label_of(n: Int) -> Text: return Text(n)`, hover over `label_of` and over
its argument in `label = label_of(customer_id)` showed `builtin Text` for the
whole call. With a relationship template whose body writes
`Text(order.customer_id)`, hover over the call's arguments showed
`builtin Text` for the whole call, and the call's name had no hover or
definition. After: the `def` call has no hover and its argument keeps only
its own facts (`customer_id` there has none), the relationship call's
arguments have none, and the call's name shows `relationship NAME` and
defines the template. A conversion written in a `max` or `min` argument, such
as each `Float` in `max(Float(id), Float(account_id))`, now shows its type,
`builtin Float`; before, it had no hover, because the copies that `max` and
`min` make kept its range. Projects, the CLI commands, CLI JSON and PIE codes
are unchanged. The surface is alpha until the Phase82 freeze.
