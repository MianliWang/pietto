### A MySQL `min` or `max` of an `INT` over a stage is a `BIGINT`

On MySQL, a project `min` or `max` of a `SMALLINT` or `INT` field that its
aggregation reads through a stage (a WHERE, a `let`, another query or a
JOIN), not straight from the source, is now emitted as
`CAST(MIN(x) AS SIGNED)` (or `MAX`). Its column is a `my_signed_int` with the
field's own range, an Arrow `int64` on the `mysql_rows` route, as a MySQL
`sum(Int)` is. Its values are unchanged.

Before, such a column was declared with the field's carrier, `my_int` or
`my_smallint`, but MySQL 8.4 returns a MIN or MAX over a merged stage's
column as `BIGINT`, so `execute` on the `mysql_rows` route failed every such
statement with `PIE-R3005` (`EXECUTION_METADATA`), and a program that ran
the emitted SQL itself got a `BIGINT` column that the emission's
`columns` did not describe. This held for `0.2.1` too. The `0.1.12` (Phase77
S02) cell was among them: `where id > 3`, `group by k`, `x = sum(a)`,
`lo = min(c)` over an `INT` field `c`.

So every such MySQL statement now has different stable SQL, and its
column is declared `int64` where it was `int32` (`int16` for a
`SMALLINT`). This includes statements that ran before: a `min` or `max`
over a query that ends in `limit`, which MySQL materializes and whose
column keeps the field's type, returned an `int32` or `int16` column and
now returns an `int64` one.

A MySQL set operation now also joins a `my_signed_int` operand, a computed
signed 64-bit `Int` such as this extreme, an `Int` operation or an integer
literal, with `SMALLINT`, `INT` or `BIGINT` operands of one width, which
MySQL types `BIGINT`: the column is a `my_signed_int` over the operands'
merged range, an Arrow `int64`, whatever the operand order. So a MySQL
`union all` of such an extreme and an `INT` or `SMALLINT` column, the same
extreme read straight from the source included, is VERIFIED with an
`int64` column, and one of it and a `BIGINT` column, BLOCKED with
`PIE-B1002` (`set_column_physical_representation_mismatch`) before, is now
VERIFIED. A literal or an `Int` operation beside a `SMALLINT` or `INT`
column, BLOCKED so before, is VERIFIED too. A set column of a
`my_signed_int` and a `BIGINT` column took the first operand's carrier
before and is a `my_signed_int` in either order now. Every other mix of
widths, such as an `INT` and a `BIGINT` column, or a `my_signed_int`
beside both an `INT` and a `BIGINT` column, stays BLOCKED with that
detail, and PostgreSQL's set rules are unchanged.

A `min` or `max` read straight from the source keeps the field's carrier
and SQL, as does every PostgreSQL extreme and every MySQL extreme of a
`BIGINT`, `DOUBLE`, `DECIMAL`, `DATE` or `DATETIME`. No diagnostic code or
detail is added, and no CLI JSON v1, project JSON v2 or artifact shape
changes.
