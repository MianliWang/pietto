### Single-file window values from every JOIN binding

In a single file with JOIN inputs, the value of `lag`, `lead`,
`first_value`, `last_value` or `nth_value`, and a `lag`/`lead` default, may
now be a field of any JOIN binding, such as `lag(o.amount)` over a query
that joins `o`, as a project already accepts. Before, only a field of the
FROM relation was accepted there and `lag(o.amount)` was PIE-S2104 (`value
must be a direct field or Bool, Text, Int, Float, or NULL literal`), even
where the PIE-S2335 refusal of an ambiguous bare name asked for `o.amount`.
PostgreSQL and MySQL emit the binding's column, such as
`LAG("o"."amount") OVER (ORDER BY "o"."id" ASC)`, and a field that a LEFT
JOIN may null-extend gives a nullable result. A hidden QUALIFY window
accepts the same values. A wrong value of a JOIN binding now reports its
real cause, as a project does: an unknown field, such as `lag(o.missing)`,
reports only PIE-S2102, without a PIE-S2104 beside it, and a default of
another type, such as `lag(o.amount, 1, "x")` over an Int `amount`,
reports PIE-S2104 `value and default must have the same exact type`.
