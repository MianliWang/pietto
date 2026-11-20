### SQLite file execution route (alpha)

`compile_query(dialect="sqlite")` now compiles a query of an
explicit-module project that reads one `sqlite.table` source, and
`execute(query, route="sqlite_file", access=SQLiteFileInput(path),
premise=None)` runs it once, in process and read-only, over one SQLite file
that your program names. It needs `pietto[arrow]` and no database driver,
and runs only on Linux x86-64 with the measured SQLite `3.53.1` build,
where it is qualified under CPython 3.13.13 and 3.12.13. See
[SQLite file route](../execution.md#sqlite-file-route) and
[SQLite project mode](../spec/sqlite-project-v1.md#execution).

- The file's content is treated as untrusted. It is opened through its
  percent-encoded `file:` URI with `mode=ro`, never `immutable=1`, in
  defensive mode with trusted schema, extension loading and memory mapping
  off, `query_only` on and an authorizer that allows only the source's
  reads, the statement's functions and the fixed checks.
- In one read transaction, before the statement runs, the attempt checks
  that the file is UTF-8, that the source is one `STRICT` table with exactly
  the contract's name and column types, with no index on an expression or
  with a `WHERE` clause and no virtual generated column, which the
  integrity check would compute without the authorizer or the deadline,
  and no stored generated column either, refused with them to keep the
  rule simple, that `PRAGMA integrity_check` of the table is `ok`, that it
  holds at most 1,048,576 rows, and that every value lies in its field's
  domain: no NULL in a non-null field, an `Int` within its `int_range`, a
  `Bool` of 0 or 1, a
  finite `Float`, and `Text` that is valid UTF-8 without NUL and within
  `max_characters`. The file is a
  non-empty regular file that, with its `-wal` file, holds at most 128 MiB;
  its `-wal`, `-journal` and `-shm` files, where present, are regular files,
  the `-shm` file with no other link; and the whole attempt runs within
  `limits.seconds`. The cap is 128 MiB because the check of a 253 MiB
  file of randomly keyed indexes outran the default 20 seconds.
- The whole result is read, the transaction committed and the file closed
  before the first batch, which carries the compiled Arrow schema. A column
  is nullable there as in the emission's `columns`, so a comparison of a
  nullable field, or a `not`, `and` or `or` of one, delivers its NULL.
- An error that SQLite raises is named by its extended result code
  (`SQLITE_ERRORCODE_<n>`), or `SQLITE_INTEGER_OVERFLOW` for a `sum` past
  signed 64 bits, never by its message.
- `export_bundle` refuses a SQLite query (PIE-R1004 `SQLITE_BUNDLE_ENTRY`),
  and `save`, `save_recoverable`, `recover`, `relay_live` and the job store
  do not take it (PIE-R1003).

Compatibility: no existing route, code or text changes. These outputs
change:

| Code or output | Case | Before | After |
| --- | --- | --- | --- |
| PIE-R1002 | `compile_query(..., dialect="sqlite")` | `PUBLIC_COMPILE_ARGUMENT` | compiles, or the emission's `CompileRejected` |
| PIE-R1003 | `execute(..., route="sqlite_file")` | `PUBLIC_ROUTE_UNAVAILABLE` | runs a `sqlite` query; any other query keeps the refusal |
| exports | `pietto.execution` | | adds `SQLiteFileInput` |

New details: PIE-R1002 `EXECUTION_ACCESS` for a path that is not a
non-empty string without NUL; PIE-R1004 `SQLITE_BUNDLE_ENTRY`; PIE-R1006
`BINDING_PARAMETER:<i>:Text` for a `Text` parameter that holds NUL;
PIE-R2002 `SQLITE_BUILD` before any file opens; and, once the attempt
opens, PIE-R2004 `SQLITE_FILE_TYPE`, PIE-R2006 `SQLITE_SESSION_CONTEXT`,
PIE-R2007 `SQLITE_FILE_ENCODING`, `SQLITE_SOURCE_OBJECT`,
`SQLITE_SOURCE_COLUMNS`, `SQLITE_SOURCE_INTEGRITY` and
`SQLITE_SOURCE_VALUES`, PIE-R3004 `SQLITE_FILE_LIMIT` and
`SQLITE_SOURCE_LIMIT`, PIE-R3005 `SQLITE_RESULT_CHECK`, and PIE-R2004 or
PIE-R3003 with `SQLITE_ERRORCODE_<n>` or `SQLITE_INTEGER_OVERFLOW`.

Known limitations:

- No other SQLite build or platform runs the route, and the library's
  memory safety on a malformed file is not part of Pietto's guarantee.
- In rollback-journal mode your writers fail with `database is locked`
  while an attempt reads the file. On a WAL file SQLite writes the `-shm`
  file on every read: it creates missing `-wal` and `-shm` files and leaves
  them, and rebuilds an existing `-shm` file in place when no other
  connection has the file open. In a directory that cannot be written, a
  WAL file whose `-wal` and `-shm` files are missing cannot be read.
- The types and sizes of the file and the files beside it are checked
  before it opens, so a file replaced or added between the check and the
  open is not detected.
- While an attempt waits for a lock that your writer holds, `cancel()`
  takes effect only at the attempt's deadline.
- When a sort, a grouping or `count_distinct` outgrows its memory, SQLite
  writes temporary files to its temporary directory (`SQLITE_TMPDIR`,
  `TMPDIR`, a system one such as `/var/tmp`, or else the working
  directory), each deleted as it is opened.
- On the read-only connection `PRAGMA integrity_check` checks no `CHECK`
  constraint; the route never relies on one.
