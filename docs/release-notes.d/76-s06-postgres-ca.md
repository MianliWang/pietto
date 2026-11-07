### PostgreSQL server verification with `ca_file`

`PostgresAccess` gains an optional last field, `ca_file`: the path of a PEM
file of the CAs you trust. With it, both PostgreSQL routes, `postgres_rows`
and `postgres_adbc`, connect with libpq `sslmode=verify-full` and that file as
the only root: the server's certificate must chain to a CA in the file and
name `host`, in a subject alternative name of `host`'s kind (an IP address or
a DNS name) or, when it has none of that kind, in its common name. Otherwise
the attempt fails with `PIE-R2004` before the startup message, so neither the
user name nor the password is sent; a missing file fails the same way. A `ca_file` with
`sslmode="disable"`, an empty `ca_file`, `ca_file="system"` (libpq's name for
the system's trusted roots) and a `ca_file` that is not a string are refused
with `PIE-R1002` (`EXECUTION_ACCESS_PROFILE`) before any connection. Pietto
reads no environment variable, default file or system store for a CA.
`MySQLAccess` is unchanged; its `ca_file` stays required.

Compatibility: `ca_file` defaults to `None` and comes after `sslmode`, so every
existing call keeps its meaning and its connection options: without
`ca_file`, `require` still encrypts without verifying the server. `repr()` of
a `PostgresAccess` without `ca_file` is unchanged; with one it ends with
`ca_file='PATH'`. No SQL, compiled record, bundle or saved-job record
changes.

### Read limits

`ExecutionLimits` is the read-limit contract of execution, as documented in
[Results](../execution.md#results): `batch_rows` (at most 4096) and
`batch_bytes` (at most 8 MiB) bound each batch, `max_rows` and `max_bytes`
bound what an attempt delivers, `seconds` is its deadline, and each
PostgreSQL statement has a server-side limit of at most 10 seconds. No limit
changes. The PostgreSQL rows route still receives the whole native result at
the first batch, so the delivery limits do not bound what the driver
receives; bound the query with `limit`.

Changed diagnostics (no accepted program changes):

| Case | Before | After |
| --- | --- | --- |
| every `PIE-R2004` | message `the selected route's connection, TLS profile or authentication failed; PostgreSQL requires TCP SCRAM-SHA-256, a password encrypted with password_encryption='scram-sha-256', and a first matching pg_hba.conf scram-sha-256 line; MySQL requires caching_sha2_password, TLS and a caller CA that verifies server identity` | same code and category; message `the selected route's connection, TLS profile or authentication failed; PostgreSQL requires TCP SCRAM-SHA-256, a password encrypted with password_encryption='scram-sha-256', a first matching pg_hba.conf scram-sha-256 line and, with a ca_file, a server certificate that this CA verifies for the host; MySQL requires caching_sha2_password, TLS and a caller CA that verifies server identity` |
| `PostgresAccess(..., ca_file=PATH)` | `TypeError` from the constructor | accepted, or `PIE-R1002` `EXECUTION_ACCESS_PROFILE` for the values above |
