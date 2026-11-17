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

A MySQL set operation now also joins a `my_signed_int` operand, a computed
signed 64-bit `Int` such as this extreme, an `Int` operation or an integer
literal, with `SMALLINT`, `INT` or `BIGINT` operands of one width, which
MySQL types `BIGINT`, in `union`, `intersect` and `except`, `all` or
`distinct`: the column is a `my_signed_int` over the operands' merged range,
an Arrow `int64`, whatever the operand order. Every other mix of widths,
such as an `INT` and a `BIGINT` column, or a `my_signed_int` beside both an
`INT` and a `BIGINT` column, stays BLOCKED with `PIE-B1002`
(`set_column_physical_representation_mismatch`), and PostgreSQL's set rules
are unchanged.

- Breaking: every such MySQL `min` or `max` has new stable SQL, and its
  column is declared `my_signed_int` and `int64` where it was `my_int` and
  `int32` (`my_smallint` and `int16` for a `SMALLINT`). This includes
  statements that ran before: a `min` or `max` over a query that ends in
  `limit`, which MySQL materializes and whose column keeps the field's type,
  returned an `int32` or `int16` column and now returns an `int64` one.
- Breaking: a MySQL set column whose first operand is a `my_bigint`, such as
  a `BIGINT` field, a `count` or a rank, and which has a `my_signed_int`
  operand, such as `lo = b` and then `lo = 1`, took the first operand's
  carrier and is now a `my_signed_int` in either order. Its Arrow type stays
  `int64`, and its SQL and values are unchanged.
- A `min` or `max` read straight from the source keeps the field's carrier
  and SQL, as does every PostgreSQL extreme and every MySQL extreme of a
  `BIGINT`, `DOUBLE`, `DECIMAL`, `DATE` or `DATETIME`. When that source is a
  MySQL view, which emission cannot tell from a table, MySQL returns a
  `SMALLINT` or `INT` extreme as `BIGINT`, so `execute` on `mysql_rows`
  still fails it with `PIE-R3005` (`EXECUTION_METADATA`), as in `0.2.1`;
  read through a stage over that view, such as a WHERE, it is cast and
  runs.
- Known limit: MySQL returns a `row_number`, `rank`, `dense_rank` or `ntile`
  result, a `my_bigint`, as `BIGINT UNSIGNED`, and computes an `Int`
  operation over one, such as `rn - 5`, as unsigned too. A set column of
  such a value beside a signed 64-bit operand (a `BIGINT` column or a
  `my_signed_int`), or through this widening beside a `SMALLINT` or `INT`
  column, is VERIFIED, but MySQL returns it as `DECIMAL` or fails with error
  1690, and `execute` on `mysql_rows` fails it with `PIE-R3005`
  (`EXECUTION_METADATA`); it never returns wrong rows. A rank beside a
  literal failed so in `0.2.1` too; a rank beside such a staged extreme,
  and an operation over a rank beside a `SMALLINT` column, were BLOCKED
  with `PIE-B1002` there.

Compatibility: PostgreSQL SQL, carriers and set rules are unchanged. These
MySQL outputs change:

| Code or output | Case | Before | After |
| --- | --- | --- | --- |
| SQL | a `min` or `max` of a `SMALLINT` or `INT` read through a stage | `MIN(x)` or `MAX(x)` | `CAST(MIN(x) AS SIGNED)` or `CAST(MAX(x) AS SIGNED)` |
| project JSON v2 aggregate | that extreme | no `result_cast`; no cast roles in `ranges` | `result_cast` `SIGNED`; `ranges` add the `syntax` roles `aggregate_result_cast_open` and `aggregate_result_cast_close` |
| `columns[].representation.storage` | that extreme, and a set column of it beside a column of its width | `my_int` or `my_smallint` | `my_signed_int` |
| Arrow type on `mysql_rows` | the same | `int32` or `int16`; `execute` failed with `PIE-R3005` except over a query that ends in `limit` | `int64`; `execute` returns its rows |
| `columns[].representation.storage` | a set column whose first operand is a `my_bigint` and which has a `my_signed_int` operand | `my_bigint` | `my_signed_int`; Arrow `int64` either way |
| PIE-B1002 `set_column_physical_representation_mismatch` | a set column of a literal, an `Int` operation or a sign beside `SMALLINT` or `INT` operands of one width, or of such a staged extreme beside a column of another width | refused | VERIFIED; `execute` runs it, except in the known limit above |

No diagnostic code or detail is added and no JSON schema changes.
