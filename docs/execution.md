# Execution (alpha)

`pietto.execution` compiles one query of your project, runs it explicitly on
PostgreSQL 18.6 through the PostgreSQL rows route, and hands you typed Arrow
batches and the attempt's real terminal state.

This is an **alpha interface**. It is separate from the public contracts listed
in the README: its names, fields, error codes and behavior may change in later
alpha releases, and each change is noted in the release notes. The compiler, the
CLI and their contracts do not change.

- `Managed operator compliance: NOT_INDEPENDENTLY_VERIFIED`
- `Native all-definition lifetime exclusion: NOT_DEMONSTRATED / NOT CLAIMED`

Pietto checks the deployment premise you declare against the compiled query and
requalifies the sources on every attempt, but it cannot verify that the operator
keeps the premise, and it does not claim that native definitions stay unchanged
for the attempt's whole lifetime.

The alpha covers one route, `postgres_rows`, against PostgreSQL 18.6, reached
over TCP and authenticated with SCRAM-SHA-256. The MySQL and PostgreSQL ADBC
routes, compiled query bundles, explicit parameter values, cancellation and
saved results remain private. There is no CLI command that connects to a
database.

## Install

`pietto.execution` exists only in a wheel built from this checkout. The
released 0.1.1 on PyPI does not contain it, so `pip install
"pietto[execute-postgres]"` from PyPI does not provide it. Build the wheel here
with `uv build --wheel`, then install it with the `execute-postgres` extra in a
fresh virtual environment, for example
`python -m pip install "dist/pietto-0.1.1-py3-none-any.whl[execute-postgres]"`.
The extra adds the pinned `psycopg[binary]==3.3.5` and `pyarrow==25.0.1` (see
the README's execution extras). Without them, opening an attempt is refused with
`PIE-R2001` before any connection, and no other installed driver is used
instead.

## Example

A project `demo-exec` with one source and one table, and a script next to it:

```text
demo-exec/
    pietto.toml
    main.pietto
    contract.json
run_query.py
```

`demo-exec/pietto.toml`:

```toml
schema_version = 2

[sources]
include = ["*.pietto"]
```

`demo-exec/main.pietto`:

```pietto
shape Item:
    id: Int not null
    label: Text not null

source items: Item is postgres.table("fixture.items")

table active_items:
    from items
    where id > 1
    select:
        id
        label
```

`demo-exec/contract.json` maps the source to the physical relation
`fixture.items`:

```json
{
  "format": "pietto.emission-contract.v1",
  "target": {"family": "postgres", "release": "18.6"},
  "sources": [{
    "selector": {"module": "main.pietto", "kind": "source", "name": "items"},
    "relation": {"namespace": "fixture", "name": "items"},
    "scan": "relation_rows",
    "fields": [
      {"ordinal": 0, "name": "id", "column": "item_id",
       "representation": {"storage": {"kind": "pg_int8"}, "nullable": false,
                          "domain": {"kind": "int_range", "min": "0", "max": "100"}}},
      {"ordinal": 1, "name": "label", "column": "item_label",
       "representation": {"storage": {"kind": "pg_text"}, "nullable": false,
                          "domain": {"kind": "text", "max_characters": 64,
                                     "encoding": "UTF8", "collation": "C",
                                     "padding": "NO PAD"}}}
    ],
    "premises": [
      {"key": "row_domain_matches", "scope": "source", "value": true},
      {"key": "read_only_object", "scope": "source", "value": true}
    ]
  }],
  "environment": [
    {"key": "client_encoding", "scope": "statement", "value": "UTF8"},
    {"key": "operator_environment", "scope": "statement", "value": "builtin_only"},
    {"key": "identifier_case", "scope": "statement", "value": "quoted_exact"},
    {"key": "parameter_protocol", "scope": "statement", "value": "postgres_extended"}
  ]
}
```

The relation in the database `app`, with rows that keep the contract's
domains (ids from 0 to 100, labels of at most 64 characters):

```sql
CREATE SCHEMA fixture;
CREATE TABLE fixture.items (item_id int8 NOT NULL, item_label text COLLATE "C" NOT NULL);
INSERT INTO fixture.items VALUES (0, 'zero'), (1, 'one'), (2, 'two'), (2, 'two'), (3, 'three'), (5, 'five');
```

`run_query.py` compiles the table, runs it and prints the rows and the
terminal state. Run it from the directory that holds both, as
`python -I run_query.py HOST PORT DATABASE USER [SSLMODE]`, with the password
on standard input; Pietto itself reads no environment variable for it. Without
`SSLMODE` it connects with TLS, which the server must have enabled (see
[Setting up the server](#setting-up-the-server)).

```python
import sys

import pyarrow as pa

from pietto.execution import (
    PostgresAccess,
    PostgresDeploymentPremise,
    RequestRejected,
    compile_query,
    execute,
)

query = compile_query(
    "demo-exec",
    module="main.pietto",
    kind="table",
    name="active_items",
    dialect="postgres",
    emission_contract="contract.json",
)
print(query)
access = PostgresAccess(
    host=sys.argv[1],
    port=int(sys.argv[2]),
    database=sys.argv[3],
    user=sys.argv[4],
    password=sys.stdin.readline().rstrip("\n"),
    sslmode=sys.argv[5] if len(sys.argv) > 5 else "require",
)
premise = PostgresDeploymentPremise(schemas=("fixture", "pg_catalog"))
with execute(query, route="postgres_rows", access=access, premise=premise) as result:
    for batch in result:
        with batch:
            print(pa.record_batch(batch).to_pylist())
outcome = result.outcome
print(outcome.end, outcome.transaction, outcome.cleanup)
try:
    execute(query, route="postgres_rows", access=access, premise=None)
except RequestRejected as error:
    print(error.code, error.category)
```

## API

- `compile_query(project, *, module, kind, name, dialect, emission_contract,
  literal_policy="preserve") -> CompiledQuery` takes the arguments of
  `pietto emit-sql --project` and runs the same pipeline. When the project input
  is refused it raises `CompileRejected`: its `emission` is the command's JSON
  failure document byte for byte, its `status` that document's status and its
  `str()` the command's `--format text` report. It raises `RequestRejected`
  instead for an argument that is `None` (`PIE-R1001`) or invalid (`PIE-R1002`),
  checked before the project is read (where the command prints its usage
  error), and when a verified query cannot become an execution (`PIE-R1004`,
  `PIE-R1005`). A `CompiledQuery` exposes `module`, `kind`, `name`, `dialect`,
  `release`, `literal_policy` and `emission`, the same `pietto.sql-emission.v1`
  artifact the command prints. Only `compile_query` creates one, and it cannot
  be pickled.
- `PostgresAccess(host, port, database, user, password, sslmode="require")` is
  the explicit connection input; `repr()` and `str()` show `password=<redacted>`,
  and it cannot be pickled or copied.
- `PostgresDeploymentPremise(schemas)` is your operator's commitment: from before
  source discovery until the last possible remote use, administrative paths keep
  the definitions and security of the relations in these schemas stable (row
  data may change). `schemas` is a tuple that covers the schema of every source
  of the query and must include `pg_catalog`, because qualification checks
  built-in definitions there; other `pg_*` schemas and `information_schema` are
  refused. Pietto binds it to the compiled query's own sources on every call.
- `ExecutionLimits(batch_rows=256, batch_bytes=1 MiB, max_rows=1048576,
  max_bytes=64 MiB, seconds=20.0)` bounds one attempt; `seconds` is its
  deadline, and each statement runs with a server-side timeout of at most 10
  seconds that Pietto sets itself.
- `execute(query, *, route, access, premise, limits=ExecutionLimits(),
  isolation="stable") -> ResultHandle` checks the request before any
  connection and returns an unopened handle; the driver and the environment
  are checked when the attempt opens. `route`, `access` and `premise` have no
  default. There is no parameter that takes SQL text. Each call binds afresh and
  is a new attempt with its own `attempt` identifier. `isolation` is `stable`
  (REPEATABLE READ READ ONLY) or `serializable` (SERIALIZABLE READ ONLY).
- `ResultHandle` runs that one attempt. Use it in a `with` block or iterate it:
  entering, or the first `next()`, connects; each `next()` returns a
  `ResultBatch`; the end of the result commits and closes it; `close()` before
  the end stops early and rolls back. `outcome` returns a fresh `Outcome`
  snapshot. Use a handle from one thread; it cannot be pickled.
- `ResultBatch` is one checked batch you own. Export it through the Arrow
  PyCapsule interface, for example `pyarrow.record_batch(batch)`; the exported
  copy stays valid after you close the batch. `num_rows` gives its size.
- `Outcome` carries `attempt`, `route`, `end`, the layered `source`,
  `transaction`, `delivery` and `cleanup` states, `remote_source_use_end`,
  `rows`, `batches`, `bytes`, `deadline_expired`, `primary`,
  `cleanup_failures` and the two declarations above as `premise_compliance` and
  `native_definition_lifetime_exclusion`.

### Terminal states

| `end` | Meaning |
| --- | --- |
| `NOT_STARTED` | Not opened yet, or closed before it was opened. |
| `OPEN` | Opened and not closed. |
| `COMPLETE` | Read to the end of the result and committed (`transaction` is `COMMIT_ACK`), with no failure. |
| `STOPPED_EARLY` | Closed before the end; the transaction was rolled back. |
| `DEADLINE` | `limits.seconds` expired. |
| `FAILED` | A failure ended it; `primary` says which. This includes a result read to the end and committed whose cleanup then failed (see below). |
| `DROPPED` | Only in an `UnclosedHandleWarning`: the open handle was garbage-collected, or was still open at interpreter exit. |

`transaction` is `COMMIT_ACK` or `ROLLBACK_ACK` only after the server
acknowledged it; `UNKNOWN` stays `UNKNOWN`, and `remote_source_use_end` is then
`REMOTE_QUIESCENCE_UNCONFIRMED`. It is `REMOTE_QUIESCENCE_UNCONFIRMED` for an
attempt that never connected too: Pietto reports the end of remote use only
when the server acknowledged it. Closing a handle is not an acknowledgement and
does not make an early stop complete. Once an attempt is closed its outcome no
longer changes; an exception raised afterwards inside the `with` block passes
through without being recorded.

When the server reports an error inside the transaction (a failing statement,
the 10 second statement limit, or the cancel a deadline sends), the transaction
is aborted. This alpha then does not send `ROLLBACK`: it reports `transaction`
`UNKNOWN`, `cleanup` `FAILED` with one `PIE-R5001` cleanup failure in phase
`transaction`, and closes the connection, which ends the transaction on the
server.

A cleanup step that fails at the end is reported by where it happened. If the
result was read to the end and the server acknowledged `COMMIT`, but a cleanup
step then failed (closing the connection, for example), the attempt ends
`FAILED`: `source` `EOF`, `transaction` `COMMIT_ACK`, `delivery` `FAILED`,
`cleanup` `FAILED`, `primary` `PIE-R3006` in phase `finalization` (cause
`ExecutionError`), and the step that failed only as a `PIE-R5001` entry in
`cleanup_failures`. The same failure in `close()` before the end leaves
`STOPPED_EARLY` with no `primary`, `cleanup` `FAILED` and that `PIE-R5001`
entry.

### Errors

Errors carry a `PIE-R` code (see [Diagnostics](spec/diagnostics.md)), its
`category`, and a `failure` with the private `detail` word, the `phase`, the
server's `sqlstate` and the exception class as `cause`. Code against `code`;
`detail` may change between alpha releases. `RequestRejected` (PIE-R1xxx) means
nothing connected; `AttemptFailed` (PIE-R2xxx and PIE-R3xxx) ends the attempt and
carries its `outcome`; `HandleMisuse` (PIE-R4xxx) leaves the attempt unchanged.
`execute()` first checks that `query`, `route`, `access`, `premise` and
`limits` are given and have the right type and that `isolation` is given, in
this order; right after the route's type it checks that the route is
`postgres_rows` and the query was compiled for `postgres` (`PIE-R1003`). It
then binds the query (`PIE-R1004`, `PIE-R1005`) and checks the values of
`premise`, `access`, `isolation` (its type included) and `limits`, in this
order, and raises the first refusal. The driver and environment checks
(`PIE-R2001` to `PIE-R2003`) run when the attempt opens. Error text never
contains a password, driver message, SQL text or value, and a public error is
not chained to the driver's exception. A
`KeyboardInterrupt` or another `BaseException` that is not an `Exception`
passes through unchanged and is recorded as `PIE-R3008`; in this alpha one that
arrives while the attempt commits, rolls back or closes its connection is
recorded as that step's failure (`PIE-R3006`, or a `PIE-R5001` cleanup failure)
and does not propagate.

## Connection and trust requirements

Pietto uses only what you pass: no environment variable, service file, password
file or certificate supplies a connection setting.

- **TCP only.** `host` is one host name or IP address. A Unix-socket directory
  (`/...`), an abstract socket (`@...`) or a host list (a comma) is refused with
  `PIE-R1002` before any connection. Host names are resolved by the system
  resolver configuration.
- **SCRAM-SHA-256 only.** A server that asks for trust, peer, `password`, `md5`,
  GSSAPI or SSPI authentication is refused before the password is sent
  (`PIE-R2004`). With TLS, Pietto requires channel binding
  (SCRAM-SHA-256-PLUS), which ties the login to the TLS connection.
- **TLS encrypts but does not verify the server.** `sslmode="require"`, the
  default and the only mode for other hosts, encrypts the connection without
  checking the server's certificate; Pietto never reads a CA, revocation list,
  client certificate or key, including those in `~/.postgresql`. Channel binding
  means that an attacker who terminates this unverified TLS cannot relay your
  login to the real server, and SCRAM fails if the other side does not know the
  role's password verifier. Such an attacker still sees one SCRAM exchange and
  can try to guess a weak password offline, so give the role a long random
  password. `sslmode="disable"` is accepted only for `127.0.0.1` and `::1`.
- **Refused environment.** With any `PG*` variable, `SSLKEYLOGFILE`,
  `OPENSSL_CONF` or `OPENSSL_MODULES` set, opening an attempt is refused with
  `PIE-R2003` before the driver is loaded. Pietto checks the names in
  `os.environ` only and never reads their values; a variable that C code or
  `os.putenv()` sets after startup is not in `os.environ` and is not seen.
  `import pietto.execution` itself imports `hashlib`, so CPython's OpenSSL has
  already read `OPENSSL_CONF` or the system `openssl.cnf` (and may have loaded
  the modules it names) before any refusal; the refusal keeps libpq's OpenSSL
  from connecting under them. PyArrow reads `OPENSSL_CONF` and creates the
  `SSLKEYLOGFILE` file when it is imported, so a program that imports PyArrow
  earlier has done so before Pietto can refuse the variables. `PSYCOPG_IMPL`
  other than `binary` is refused with `PIE-R2002` before psycopg is imported,
  because another implementation would load a system libpq.
  `PSYCOPG_WAIT_FUNC`, which only selects psycopg's I/O wait function, is
  accepted.
- **Pinned driver files.** The imported `psycopg` and `psycopg_binary` must be
  files recorded by the installed `psycopg 3.3.5` and `psycopg-binary 3.3.5`
  distributions, and the binary implementation must be the selected one; a
  shadowing copy on `PYTHONPATH` or in the working directory is refused with
  `PIE-R2002` before it receives any connection value. This stops accidental
  shadowing, not a deliberately constructed environment, which can run
  arbitrary code anyway. Run scripts with `python -I` to keep the working
  directory and `PYTHONPATH` out of the import path. PyArrow only has to be
  importable: this alpha checks neither its version nor the files it is
  imported from.
- **Code identity.** Each compile and attempt identifies the installed Pietto
  and ANTLR runtime code; the ANTLR version comes from the distribution that
  owns the imported runtime files, so a stray `*.dist-info` in the working
  directory cannot change it.

### Setting up the server

For `sslmode="require"` the server needs TLS: `ssl = on` and a certificate and
key in `postgresql.conf` (`ssl_cert_file`, `ssl_key_file`). Channel binding needs
a certificate signed with a digest-based algorithm such as RSA or ECDSA and a
direct connection to PostgreSQL: with an Ed25519 or Ed448 certificate, or
through a TLS-terminating proxy or pooler that does not offer
SCRAM-SHA-256-PLUS, every connection fails with `PIE-R2004`. Then, connected as
a superuser with `psql`, create a login role without a password and let it read
the source relations:

```sql
CREATE ROLE pietto_reader LOGIN;
GRANT CONNECT ON DATABASE app TO pietto_reader;
GRANT USAGE ON SCHEMA fixture TO pietto_reader;
GRANT SELECT ON fixture.items TO pietto_reader;
```

Set its password in the same `psql` session. `\password` asks for it twice and
sends the server only a SCRAM-SHA-256 verifier computed by `psql`, so the
password itself never reaches the server log or your shell history, as it would
with `CREATE ROLE ... PASSWORD '...'` (`password_encryption` is
`scram-sha-256` by default; its `SET` makes sure of it). Treat the verifier as a
secret too: whoever holds it can pose as the server to a client that does not
verify the server's certificate. The first two `SET` commands keep this
superuser session from logging the statement that carries it:

```psql
SET log_statement = 'none';
SET log_min_error_statement = 'panic';
SET password_encryption = 'scram-sha-256';
\password pietto_reader
```

Allow the role in `pg_hba.conf`. The server uses the first line whose
connection type, database, role and client address match and ignores the
rest, so put these lines above every other line that could match the same
connection; a fresh `initdb` cluster, for example, starts with `trust` lines
for `127.0.0.1/32` and `::1/128`, and some distributions use `ident` or `peer`.
A `hostssl` line accepts only TLS connections. Keep `host` lines, which also
accept unencrypted connections, for the `sslmode="disable"` case from the same
machine, with one line for IPv4 and one for IPv6 loopback (they also match TLS
connections from there, which still use SCRAM with channel binding):

```conf
# TYPE   DATABASE  USER           ADDRESS        METHOD
hostssl  app       pietto_reader  192.0.2.0/24   scram-sha-256
host     app       pietto_reader  127.0.0.1/32   scram-sha-256
host     app       pietto_reader  ::1/128        scram-sha-256
```

Replace `app` with your database and `192.0.2.0/24` with your clients'
addresses, leave out the `host` lines if you do not use `sslmode="disable"`, and
reload the configuration (`SELECT pg_reload_conf();`). A failed connection or
authentication is `PIE-R2004`.

## Effects

| Call | Database and network | Reads | Threads | Imports |
| --- | --- | --- | --- | --- |
| `import pietto.execution` | none | Python modules; importing `hashlib` lets CPython's OpenSSL read `OPENSSL_CONF` or the system `openssl.cnf` | none | no driver, no PyArrow |
| `compile_query(...)` | none; no schema is read | `pietto.toml`, the selected sources and the contract under the project root; the installed Pietto and ANTLR runtime `.py` files; the ANTLR distribution's `METADATA` and `RECORD` | none | none |
| attributes, `repr()` of the value objects, `CompiledQuery` and an unopened handle | none | none | none | none |
| `execute(...)` | none | the installed code and ANTLR metadata again, to bind afresh | none | none |
| entering, or the first `next()` | one TCP connection: TLS with channel binding unless `disable`, SCRAM-SHA-256; `BEGIN ... READ ONLY`; a settings read; catalog reads that qualify the sources, between two reads of the session context | environment variable names and the value of `PSYCOPG_IMPL`; the `METADATA` and `RECORD` of psycopg and psycopg-binary; the type of `/dev/null` | one non-daemon `pietto-deadline-<attempt>` timer | psycopg 3.3.5 and PyArrow |
| the first `next()` | a read of the session context, the statement timeout (`set_config`), then one prepared statement of at most 10 s; the whole result is read into client memory | none | as above | none |
| each later `next()` | a read of the session context before the batch is returned | none | as above | none |
| the end of the result, or `close()` | a read of the session context, then `COMMIT` at the end, `ROLLBACK` before it; the connection closes | none | the timer is joined (at most 3 s) | none |

Pietto writes no file and keeps no state between calls. `help()` runs pydoc,
which reads `HOME` and other variables itself.

### Dropped handles

Garbage-collecting an open handle without closing it issues an
`UnclosedHandleWarning` (`PIE-R5002`) whose `outcome` has `end` `DROPPED`; a
handle that is still open at interpreter exit is reported the same way. It is a
`ResourceWarning`, which Python hides by default: run with
`-W default::ResourceWarning` or `-X dev` to see it. Pietto does no network I/O
at that point. The server session and its read-only transaction stay open until
the attempt's resources are garbage-collected after its deadline timer ran, or
until the process exits; the deadline itself only cancels a statement that is
still running. Interpreter exit waits for the deadline timer, up to
`limits.seconds`. Use `with`.

## Known limitations

- The PostgreSQL rows route reads the whole native result into client memory at
  the first `next()`; `max_rows` and `max_bytes` limit only what is delivered to
  you, and exceeding them refuses the whole batch (`PIE-R3004`) instead of
  truncating it.
- Sources with `Timestamp` or `UUID` fields are blocked when compiled
  (`PIE-B1004`), even if the query does not select those fields; public Timestamp
  and UUID results are not part of this alpha.
- A query whose single-match requirements need runtime enforcement is blocked
  when compiled (`PIE-B1006`), as with `pietto emit-sql --project`.
- A query always runs with the literal values of its source; a `bind-safe`
  query binds them as parameters.
- There is no `cancel()` yet. The deadline cancels a running statement and the
  server's 10 second statement limit ends one; neither bounds a wait on a server
  or network that stops responding, and neither ends an idle session. When both
  expire together the error is `DEADLINE`.
- The real-database witness of this alpha uses CPython 3.13.13 on Linux x86-64
  and PostgreSQL 18.6 with TLS, channel binding and SCRAM-SHA-256, and the
  loopback `sslmode="disable"` case; other interpreters, platforms, server
  versions and setups are not covered by it.
