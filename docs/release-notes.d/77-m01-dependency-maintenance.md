### Dependency maintenance: PyArrow 26.0.1 and Psycopg 3.3.8

- The optional extras now install `pyarrow==26.0.1` (`arrow`,
  `execute-postgres`, `execute-mysql` and `execute-postgres-adbc`) and
  `psycopg[binary]==3.3.8` (`execute-postgres`) instead of `26.0.0` and
  `3.3.5`. The core install is unchanged and still needs no Arrow.
- Only the new pins are accepted. An environment that keeps `pyarrow 26.0.0`
  is refused with `PIE-R2002`, before any connection on every route and at
  every public Arrow use including saved results, and `pa.schema(result)`
  refuses it with `PIE-R4004`; `postgres_rows` likewise refuses
  `psycopg 3.3.5` with `PIE-R2002` before connecting. Upgrading `pietto`
  alone leaves an extra's packages in place, so reinstall with the extra, for
  example `pip install -U "pietto[execute-postgres]"`.
- Psycopg `3.3.8` is chosen over `3.3.7`, whose change to the system SSL
  directory lookup `3.3.8` reverts.
- SQL output, result values and saved-result formats are unchanged. The
  `postgres_rows`, `postgres_adbc` and `mysql_rows` routes passed fresh local
  runs with the new pins against PostgreSQL 18.6 and MySQL 8.4.12.
