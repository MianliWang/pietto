### SQLite single files

- `pietto emit-sql FILE --dialect sqlite`, a usage error before, writes
  SQLite SQL for one file, as text or as CLI JSON v1, whose `dialect` gains
  the successful value `"sqlite"`. It covers a flat subset: a table or query
  reading one `sqlite.table("name")` source directly, with `where`,
  `select`, `order by`, `limit`, `group by`, `count`, `min` and `max` over
  `Int`, `Text`, `Bool` and `Float` fields (`min` and `max` of an `Int` or
  `Float` field), with no arithmetic, a sign before a number included. The
  SQL quotes each name in backticks and writes each field with its table
  name, as in `` `users`.`id` ``.
  The [SQLite rules](../language.md#sqlite-single-files) state the premises
  the SQL assumes (`STRICT` tables, `BINARY` collation, UTF-8, `Bool` as an
  `INTEGER` 0 or 1, finite `REAL` values) and what each form means under
  them.
- Ascending keys end with `NULLS LAST` and descending keys with
  `NULLS FIRST`, so NULL sorts last ascending and first descending, the
  default that PostgreSQL documents for the PostgreSQL emitter's SQL;
  SQLite's own default would put NULL first in ascending order.
- Pietto writes the SQL text only. It runs no SQLite statement, opens no
  database file and adds no dependency.

```pietto
shape User:
    id: Int
    name: Text
    active: Bool

source users: User = sqlite.table("users")

query active_users:
    from users
    where active
    select id, name
    order by name
    limit 10
```

Compatibility: PostgreSQL and MySQL output and CLI JSON schema version 1 are
unchanged, and so is project mode: `emit-sql --project --dialect sqlite`
stays a usage error, `compile_query(dialect="sqlite")` keeps PIE-R1002, and a
project's `check` still refuses `sqlite.table("users")` with PIE-S2306
`Unknown source connector: sqlite.table` on the whole call. Existing
diagnostics are unchanged except these, for programs refused before as well;
the PIE-S2306 ones are single-file only:

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-P1000 | a `dialect sqlite` header line, also in a project or a dependency package; the message and its suggestion end with the hint | ``Delete the header line `dialect sqlite`; it has no effect.`` | ``Delete the header line `dialect sqlite`; it has no effect; `emit-sql` takes `--dialect sqlite`.`` |
| PIE-S2306 | a `sqlite.table` call with one bare table name | `Unknown source connector: sqlite.table` on the whole call | none: the source checks |
| PIE-S2306 | a `sqlite.table` string with a dot, or an empty string | `Unknown source connector: sqlite.table` on the whole call | `Invalid source connector arguments for sqlite.table: expected <table>` at the string |
| PIE-S2306 | a `sqlite.table` call without exactly one argument, or with a non-`Text` argument such as `1`, and no argument reports an error of its own | `Unknown source connector: sqlite.table` on the whole call | `Invalid source connector arguments for sqlite.table` on the whole call |
| PIE-S2306 | any other `sqlite.table` argument that is not a string literal, such as the unquoted dotted name `main.users`, `None` or `concat("a", "b")`, and no argument reports an error of its own | `Unknown source connector: sqlite.table` on the whole call | `Invalid source connector arguments for sqlite.table: expected a string literal "<table>"` at the argument |

New refusals of `emit-sql --dialect sqlite` (a usage error before):

| Code | Case | Text |
| --- | --- | --- |
| PIE-B1000 | a SQLite single-file form outside the subset, such as arithmetic or a signed literal, a comparison of an `Int` with a `Float`, `in`, `having`, a table or query that reads another, a JOIN, a window, a function call, a `Decimal`, `Date`, `Timestamp` or `UUID` field, or any table or query of a file that declares a top-level constant | `SQLite SQL emission is not implemented for RelationIR: <name>. <reason>` |

Known limitations:

- The SQL is qualified on one measured SQLite library only: release
  `3.53.1` together with the source id and compile options that the
  [SQLite rules](../language.md#sqlite-single-files) refer to. A version
  number alone is no identity, and no other build is qualified, the SQLite
  of hosted CI, Windows and macOS included. The SQL text is the same
  whatever library later runs it.
- The SQL assumes and does not check its premises: `STRICT` tables,
  `BINARY` collation, UTF-8, `Bool` as an `INTEGER` 0 or 1 and finite
  `REAL` values. A `COLLATE NOCASE` column, a 2 in a `Bool` column or an
  infinity in a `REAL` column changes what the SQL means.
- Projects have no SQLite target, and Pietto has no route that runs SQLite
  SQL or reads its result.
- Beyond the refusals above, `sum`, `avg` and every aggregate other than
  `count`, `min` and `max`, casts, conditional expressions, range
  comparisons, `any(...)` reads and a `None` literal that `check` accepts
  outside `is None` and `is not None`, such as `n = None` in `select`, are
  refused with PIE-B1000 too. `== None` and `!= None` fail `check` with
  PIE-S2105 for every target.
