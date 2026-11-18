### A MySQL rank is cast to `SIGNED`

MySQL project SQL now writes each `row_number`, `rank`, `dense_rank` and
`ntile` window result as `CAST(ROW_NUMBER() OVER (...) AS SIGNED)` (`RANK`,
`DENSE_RANK`, `NTILE(n)`), and so does the refined statement that R2
`save_recoverable` and `recover` read. Its column keeps its `my_bigint`
carrier from 0 to 9223372036854775807, an Arrow `int64` on the `mysql_rows`
route, and its values are unchanged.

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
`DECIMAL`, which failed the same way. This held for `0.2.1` too, and for
R2's refined statement. Each of these statements now runs and returns its
signed values: a native MySQL 8.4.12 run of the four functions under binary
`-` and set operations through the public `execute` matched type codes and
values, and one of R2's first page of `rn - 5`, `5 - rn` and a `union all`
of a rank and a literal returned the original statement's signed values for
each of the four.

So every MySQL project statement that reads one of these four functions has
different stable SQL. A `union all` of an operation over a rank and a
`SMALLINT` or `INT` column, BLOCKED with `PIE-B1002`
(`set_column_physical_representation_mismatch`) in `0.2.1`, is now VERIFIED
as a `my_signed_int` and runs. A `union all` of a rank, first, and an
integer literal or an operation over a rank, declared `my_bigint` in
`0.2.1`, is a `my_signed_int` with the same range (an Arrow `int64` as
before), as the set rule in the note on a MySQL `min` or `max` over a stage
states. PostgreSQL's SQL and the `percent_rank` and `cume_dist` results are
unchanged. Single-file MySQL SQL still writes the rank uncast, so there
`rn - 5` still fails with error 1690 below zero. No diagnostic code or
detail is added, and no CLI JSON v1, project JSON v2 or artifact shape
changes.
