### DuckDB Arrow route — DuckDB 2.0.1

- The `execute-duckdb` extra now installs `duckdb==2.0.1` instead of
  `2.0.0`, with `pyarrow==26.0.1` as before. The core install is unchanged
  and still needs no Arrow.
- `execute(route="duckdb_arrow")` accepts only `duckdb` `2.0.1`. An
  environment that keeps `duckdb` `2.0.0` is refused when the attempt opens,
  before any statement: with `PIE-R2002` (`EXECUTION_DRIVER_VERSION`) for the
  installed distribution, or with `PIE-R2002` (`DUCKDB_DRIVER_PROFILE`) for
  an engine that does not report `v2.0.1` with source id `8d78114e90`.
  Upgrading `pietto` alone leaves the extra's packages in place, so
  reinstall with the extra, for example
  `pip install -U "pietto[execute-duckdb]"`.
- The DuckDB emission contract's target becomes
  `{"family": "duckdb", "release": "2.0.1"}`. A contract that still names
  `2.0.0` is BLOCKED with `PIE-B1003` (`target_release_not_reviewed`) by
  `emit-sql --project --dialect duckdb`, `compile_sql` and `compile_query`,
  and the suggestion now reads `the reviewed duckdb release is "2.0.1"`;
  write `2.0.1` in the contract. This is a compatibility change of the
  emission contract, as D79.05 states for a pin upgrade. PostgreSQL, MySQL
  and SQLite contracts are unchanged.
- DuckDB `2.0.1` names the logging setting `logging_sink` where `2.0.0`
  named it `logging_storage`, with the same value `memory`, so the session
  reads back `logging_sink`; every other setting that the route sets and
  reads back has the value it had. SQL output, result values and limits are
  unchanged. See
  [Session and attempt](../spec/duckdb-arrow-route-v1.md#session-and-attempt).
- The route is qualified with `duckdb` `2.0.1` and `pyarrow` `26.0.1` on
  CPython 3.12 and 3.13, Linux x86-64 with glibc 2.28 or later
  (every unit accepted on its first attempt on 2026-11-27).
