### JOINs on the `sqlite_file` route (alpha)

The `sqlite_file` route now runs a SQLite project statement that joins
`sqlite.table` sources, over one caller's file. See
[SQLite project mode](../spec/sqlite-project-v1.md#attempt).

- Each source table that the statement reads passes every check that one
  source passes, in the attempt's one read transaction: its object,
  columns, indexes and integrity, its row limit and the domain of each
  value. The authorizer allows the reads of each source's contract
  columns.
- A statement that joins sources and aggregates first checks each
  declared `unique(...)` key of each source, as the verified plan keeps it,
  with one bounded scan that compares as Pietto's `==` does: `Text` by its
  bytes, also on a `COLLATE NOCASE` column, and `-0.0` equal to `0.0`. A
  duplicate key fails the attempt with PIE-R2007 `SQLITE_SOURCE_UNIQUE`
  before the statement runs, since it would make the JOIN repeat rows that
  the aggregate then counts again. A JOIN that does not aggregate is not
  scanned.
- Such a statement reads its result only up to the first batch that crosses
  `max_rows`, `max_bytes` or `batch_bytes`, which delivery then refuses
  with PIE-R3004, so a JOIN's fan-out cannot fill memory beyond the limits
  and one batch. An error that only a later row would raise may then not be
  seen. Each row read passes the result check as it is read, so a
  PIE-R3005 `SQLITE_RESULT_CHECK` of such a statement has the phase
  `query`, not `result`. A statement over one source runs as before.

Compatibility: the route runs a statement over one source as before, and
`0.2.2` refused every statement that joins sources.

Known limitations:

- The route over a JOIN is qualified by native cells on the measured
  SQLite library, under CPython 3.13.13 and 3.12.13 on Linux x86-64; it
  writes no SQL of its own, so no PostgreSQL replay reaches it.
- A statement that joins sources and aggregates checks every declared
  `unique(...)` key of each source, so a file that breaks a key the
  statement does not use is refused too.
