### DuckDB Arrow route — limited local path (alpha)

An explicit-module project can now run one read-only query over one Arrow
table that the program supplies, in process, on DuckDB `2.0.0`. The source is
declared `source orders: Order = duckdb.arrow("orders")`; the query is a
direct projection of its `Int`, `Text`, `Bool` and finite `Float` fields,
optionally filtered by one comparison of an `Int` field with one non-null
`Int` query parameter. `pietto emit-sql --project ... --dialect duckdb`,
`compile_sql`, `compile_all_sql` and `compile_query` accept the `duckdb`
dialect with the contract target `{"family": "duckdb", "release": "2.0.0"}`
and `scan` `"arrow_registration"`, and
`execute(query, route="duckdb_arrow", access=DuckDBArrowInput(name="orders",
table=t), premise=None)` returns the usual `ResultHandle` and `ResultBatch`.
Results are bags: B1 has no ordering. See the
[DuckDB Arrow route](../spec/duckdb-arrow-route-v1.md), the
[DuckDB local path](../capabilities.md#duckdb-local-path) of the capability
page and the [route section](../execution.md#duckdb-arrow-route) of the
execution guide.

- `execute()` copies the admitted columns before it returns, so later changes
  to the caller's buffers do not reach the query. A table of more than 65,536
  rows or 16 MiB (`pyarrow.Table.nbytes`) is refused with `PIE-R1002`
  `DUCKDB_ARROW_CAPTURE_LIMIT`; a name, column, type, null, NaN or infinity,
  invalid UTF-8 or out-of-domain value that does not fit the compiled
  query with `PIE-R1002` `DUCKDB_ARROW_SCHEMA`. A NUL inside a `Text` value
  is admitted and reaches DuckDB and the result unchanged. Before the capture,
  `execute()` refuses a loaded PyArrow that is not the installed `pyarrow`
  `26.0.1` distribution's own files with the codes of the other Arrow
  routes, `PIE-R2001` when it is not installed and `PIE-R2002` otherwise.
  These are raised as `RequestRejected`, which on `mysql_rows` and
  `postgres_adbc` already carries `PIE-R2003`: nothing has connected.
- Each attempt opens its own `:memory:` session with extension install and
  load, external access, caller-frame scans and temporary spill off, one
  engine thread and a 256 MiB memory limit, then locks the configuration and
  reads every value back; a session that cannot be proven is `PIE-R2006`.
- `premise=None` is accepted on `duckdb_arrow` only; the PostgreSQL and MySQL
  routes keep their required premises.
- `emit-sql --project ... --dialect duckdb` prints the
  `pietto.sql-emission.v1` document (`v2` for the filtered query with its
  parameter), whose one `SELECT` reads only the registered capture
  `temp.main."pietto_arrow_0"` by Pietto-owned column names; `compile_sql`
  returns those bytes, and `compile_query` builds a query only from such a
  VERIFIED document.
- Unsupported shapes are BLOCKED with `PIE-B1003` and a suggestion. A
  `duckdb.arrow` source under PostgreSQL or MySQL is refused as a source of
  another family is today, with `PIE-B1001` `source_family_mismatch` beside
  `PIE-B1006` `negative_original_target_evidence`, and so is a
  `postgres.table` or `mysql.table` source under DuckDB. Single files keep
  `PIE-S2306` for `duckdb.arrow`, and their output is unchanged.
- Install it with `pip install "pietto[execute-duckdb]"`, which pins
  `pyarrow==26.0.1` and `duckdb==2.0.0`; another installed `duckdb` is
  refused with `PIE-R2002`. One `cp312-abi3` duckdb wheel serves CPython 3.12
  and 3.13; the qualified platforms are CPython 3.12 and 3.13 on Linux x86-64
  with glibc 2.28 or later. The core install is unchanged and still needs no
  PyArrow or DuckDB.
- PostgreSQL and MySQL SQL bytes, contracts and diagnostics are unchanged.
  The refusal of a result wider than the 64 Arrow fields of one batch
  (`PIE-R1004` `LIMIT`) stays on the PostgreSQL and MySQL routes;
  `duckdb_arrow` does not make it.
  Query bundles, saved results, relay, jobs, JOINs, aggregation, ordering and
  other types are not available on DuckDB in this version.
