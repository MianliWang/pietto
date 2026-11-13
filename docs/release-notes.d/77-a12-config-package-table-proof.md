### Project configuration `[package]` table proof

A schema-v3 or schema-v4 `pietto.toml` now proves its `[package]` root
table with two TOML parses: one finds the only line that looks like a
`[package]` header and opens the table, and one renames that line to prove
it is the header, as before. The proof used to rename each such line in
turn and parse the whole file again, so its work grew with the square of
the number of such lines, for example lines inside a multi-line string.

A NaN anywhere in the file no longer fails that proof, so the file reports
its own fault, such as
`Project [capability_environment] contains unsupported key: weight.`, where
it reported
`Project configuration schema-v4 package activation requires an exact [package] root table.`

New refusal: a multi-line string that holds a line that looks like a
`[package]` header followed by a `#` comment containing the string's closing
quotes can now get the exact-table message where the file loaded before,
for example inside the `[package]` table itself, or in a capability fact's
`operands` array that continues on the next line. Every refusal keeps the
`config_schema` kind, and no file that was refused now loads.
