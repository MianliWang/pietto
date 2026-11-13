### Project SQL refuses a WHERE or JOIN over rows without fields

Project SQL emission wrote a WHERE over a source whose shape declares no
field, such as a shape with only `always = check(True)`, and a JOIN of two
such sources, as a CTE with an empty column list,
`WITH "p0" () AS (SELECT  FROM ...)`, and reported it VERIFIED on
PostgreSQL and MySQL; neither database parses it. Such a statement is now
BLOCKED with PIE-B1003 `zero_column_stage_not_admitted_on_target`, once per
such WHERE or JOIN in statement order, the order of their CTEs, which may
differ from source order: a WHERE reports its stage at that WHERE, and a JOIN
reports the JOIN at its ON clause, or without a location when it has
none; an `any` filter written before a later JOIN is such a JOIN, at
its condition. MySQL has no SELECT without a column, so on MySQL a
capturing `let` that reads such rows inside its `exists`, `in`, `scalar` or
LATERAL read is refused the same way; PostgreSQL runs that inline SELECT
and keeps emitting it. A source like this read without a WHERE, through a
`let` value or by an aggregate alone emits as before.

Changed diagnostics (programs whose SQL no database parsed; every other
program is unchanged):

| Entry | Before (`0.1.11`, measured at `0541765a`) | After |
| --- | --- | --- |
| `pietto emit-sql --project` | `VERIFIED` with that SQL, exit 0 | `BLOCKED` with the blocker above, exit 1 |
| `pietto.compiler.compile_sql` | a `VERIFIED` document with that SQL | a `BLOCKED` document with the blocker above |
| `pietto.execution.compile_query` | `RequestRejected` with PIE-R1004 `QUERY_NOT_EXECUTABLE` (detail `COMPILED_SOURCE_FIELDS`) | `CompileRejected` with the blocker above |

`check --project` and single-file SQL are unchanged. A statement that
another blocker refuses keeps exactly the blockers it had: this one is
reported only when nothing else in the statement is refused. A query that
reads a source without fields stays not executable, as before: one that
still emits SQL is refused by `compile_query` with that PIE-R1004, so no
execution entry ever sent this SQL to a database.
