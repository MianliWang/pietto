### A MySQL rank is cast to `SIGNED`

MySQL SQL, single-file and project, now writes each `row_number`, `rank`,
`dense_rank` and `ntile` window result as
`CAST(ROW_NUMBER() OVER (...) AS SIGNED)` (`RANK`, `DENSE_RANK`,
`NTILE(n)`), and so does the refined statement that R2 `save_recoverable`
and `recover` read. A project column keeps its `my_bigint` carrier from 0 to
9223372036854775807, an Arrow `int64` on the `mysql_rows` route, and its
values are unchanged.

MySQL 8.4 returns these four as `BIGINT UNSIGNED`, so it computed a binary
`+`, `-` or `*` over one in unsigned arithmetic (unary `-` it computes
signed), while Pietto declared the result a signed `my_signed_int`.
`rn - 5` or `5 - rn` over a rank `rn` failed with MySQL error 1690
(`BIGINT UNSIGNED value is out of range`) as soon as a value fell below
zero, and returned an unsigned column otherwise, so `execute` on the
`mysql_rows` route failed every such statement with `PIE-R3005`
(`EXECUTION_METADATA`), and a program that ran the emitted SQL itself got
that error. A set operation of a rank beside a signed operand, such as a
`union all` of a rank and an integer literal or a `BIGINT` column, returned
`DECIMAL`, which failed the same way. This held for `0.2.1` too, for
single-file MySQL SQL, and for R2's refined statement. Each of these project
statements now runs and returns its signed values: a native MySQL 8.4.12 run
of the four functions under binary `-` and set operations through the public
`execute` matched type codes and values, and one of R2's first page of
`rn - 5`, `5 - rn` and a `union all` of a rank and a literal returned the
original statement's signed values for each of the four. Single-file SQL
writes the same cast around the same window call.

So every MySQL statement, single-file or project, that reads one of these
four functions has different stable SQL. No declared carrier changes: a set
operation still takes its first operand's 64-bit carrier over the operands'
merged range, so a `union all` of a rank, first, and an integer literal stays
a `my_bigint` from 0 to 9223372036854775807, now sent as a signed `BIGINT`
rather than a `DECIMAL`. A set of a rank beside a 16- or 32-bit operand, such
as a `min` of an `INT` field, stays BLOCKED with `PIE-B1002`
(`set_column_physical_representation_mismatch`), as no common type is taken.
PostgreSQL's SQL and the `percent_rank` and `cume_dist` results are
unchanged. No diagnostic code or detail is added, and no CLI JSON v1,
project JSON v2 or artifact shape changes.
