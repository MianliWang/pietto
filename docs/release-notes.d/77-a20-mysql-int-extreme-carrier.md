### A MySQL `min` or `max` of an `INT` is a `BIGINT`

On MySQL, every grouped project `min` or `max` of a `SMALLINT` or `INT`
field is now emitted as `CAST(MIN(x) AS SIGNED)` (or `MAX`), whatever its
aggregation reads: a base table, a view, or a stage (a WHERE, a `let`,
another query or a JOIN). Its column is a `my_signed_int` with the field's
own range, an Arrow `int64` on the `mysql_rows` route, as a MySQL
`sum(Int)` is. Its values are unchanged.

Before, such a column was declared with the field's carrier, `my_int` or
`my_smallint`, but MySQL 8.4 returns a MIN or MAX over a view's column or a
merged stage's column as `BIGINT`, and emission cannot tell a view from a
table, so `execute` on the `mysql_rows` route failed every such statement
with `PIE-R3005` (`EXECUTION_METADATA`), and a program that ran the emitted
SQL itself got a `BIGINT` column that the emission's `columns` did not
describe. This held for `0.2.1` too. The `0.1.12` (Phase77 S02) cell was
among them: `where id > 3`, `group by k`, `x = sum(a)`, `lo = min(c)` over
an `INT` field `c`. One cast for every source keeps one carrier whatever
MySQL returns.

A MySQL set operation now also joins a `my_signed_int` operand, a computed
signed 64-bit `Int` such as this extreme, an `Int` operation or an integer
literal, with `SMALLINT`, `INT` or `BIGINT` operands of one width, which
MySQL types `BIGINT`, in `union`, `intersect` and `except`, `all` or
`distinct`: the column is a `my_signed_int` over the operands' merged range,
an Arrow `int64`, whatever the operand order. With the `SIGNED` cast of a
`row_number`, `rank`, `dense_rank` or `ntile` result, a `union all`
of such a rank and such an extreme, such as `row_number()` or `ntile(2)`
beside `min(i)` of a nullable `INT` `i` under `where id > 3` and
`group by j`, is now VERIFIED as a nullable `my_signed_int` from
-2147483648 to 9223372036854775807, in either order, and runs. Every other
mix of widths, such as an `INT` and a `BIGINT` column, a rank beside an
`INT` or `SMALLINT` column, or a `my_signed_int` beside both an `INT` and a
`BIGINT` column, stays BLOCKED with `PIE-B1002`
(`set_column_physical_representation_mismatch`), and PostgreSQL's set rules
are unchanged.

- Breaking: every such MySQL `min` or `max` has new stable SQL, and its
  column is declared `my_signed_int` and `int64` where it was `my_int` and
  `int32` (`my_smallint` and `int16` for a `SMALLINT`). This includes
  statements that ran before: a `min` or `max` read straight from a base
  table, or over a query that ends in `limit`, which MySQL materializes,
  returned an `int32` or `int16` column and now returns an `int64` one.
- Breaking: a MySQL `lag`, `lead`, `first_value`, `last_value` or
  `nth_value` over such an extreme of a `SMALLINT`, such as `max(s)` in an
  upstream grouped table, now reads a `my_signed_int` and is a `my_bigint`
  (`int64`) where it was a `my_int` (`int32`), as MySQL types a window value
  over a `BIGINT` column; its values are unchanged.
- Breaking: a MySQL set column whose first operand is a `my_bigint`, such as
  a `BIGINT` field, a `count` or a rank, and which has a `my_signed_int`
  operand, such as `lo = rn` and then `lo = 1`, took the first operand's
  carrier and is now a `my_signed_int` in either order. Its Arrow type stays
  `int64`, and its SQL and values are unchanged.
- Unchanged: every PostgreSQL extreme; every MySQL extreme of a `BIGINT`,
  `DOUBLE`, `DECIMAL`, `DATE` or `DATETIME`; every `min` or `max` over a
  window, on either target; and single-file SQL, which this change does not
  touch.

Compatibility: PostgreSQL SQL, carriers and set rules are unchanged. These
MySQL project outputs change:

| Code or output | Case | Before | After |
| --- | --- | --- | --- |
| SQL | a grouped `min` or `max` of a `SMALLINT` or `INT`, over any source | `MIN(x)` or `MAX(x)` | `CAST(MIN(x) AS SIGNED)` or `CAST(MAX(x) AS SIGNED)` |
| project JSON v2 aggregate | that extreme | no `result_cast`; no cast roles in `ranges` | `result_cast` `SIGNED`; `ranges` add the `syntax` roles `aggregate_result_cast_open` and `aggregate_result_cast_close` |
| `columns[].representation.storage` | that extreme, and a set column of it beside a column of its width | `my_int` or `my_smallint` | `my_signed_int` |
| Arrow type on `mysql_rows` | the same | `int32` or `int16`; `execute` failed with `PIE-R3005` over a view or a merged stage | `int64`; `execute` returns its rows |
| `columns[].representation.storage` | a window value read of that extreme of a `SMALLINT` | `my_int` | `my_bigint`; Arrow `int64` |
| `columns[].representation.storage` | a set column whose first operand is a `my_bigint` and which has a `my_signed_int` operand | `my_bigint` | `my_signed_int`; Arrow `int64` either way |
| PIE-B1002 `set_column_physical_representation_mismatch` | a set column of a literal, an `Int` operation or a sign beside `SMALLINT` or `INT` operands of one width; of such an extreme beside a column of another width; of a rank beside such an extreme | refused | VERIFIED; `execute` runs it |

No diagnostic code or detail is added and no JSON schema changes.
