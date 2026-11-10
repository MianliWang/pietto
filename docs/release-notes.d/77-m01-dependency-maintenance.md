### Dependency maintenance: PyArrow 26.0.1 and Psycopg 3.3.8

- The optional extras pin `pyarrow==26.0.1` (`arrow`, `execute-postgres`,
  `execute-mysql` and `execute-postgres-adbc`) and `psycopg[binary]==3.3.8`
  (`execute-postgres`); `0.1.10` pinned `26.0.0` and `3.3.5`. The core
  install is unchanged and still needs no Arrow.
- Psycopg `3.3.8` is chosen over `3.3.7`, whose change to the system SSL
  directory lookup `3.3.8` reverts.
- SQL output, results, diagnostics and saved-result formats are unchanged.
  The PostgreSQL rows, ADBC and TLS routes and the MySQL route passed fresh
  local runs against PostgreSQL 18.6 and MySQL 8.4.12.
