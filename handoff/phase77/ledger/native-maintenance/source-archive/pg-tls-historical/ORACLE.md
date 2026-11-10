# 76-S06 C76-06 oracle: PostgreSQL CA verification on both routes

Written before any run of this package. Never edited after a run; corrections go
to `ORACLE-ERRATA.md`. This run-2 package supersedes the flawed judge in the
adjacent `db/` recovery copy; the original package and Oracle remain unchanged.
`judge.py` encodes exactly these expectations.

## What the run must prove

The maintenance candidate preserves D76.07: with `PostgresAccess(...,
ca_file=PATH)` both PostgreSQL routes (`postgres_rows` through psycopg-binary
3.3.8's libpq, `postgres_adbc` through ADBC 1.13.0's libpq) verify the server certificate chain against that file and
the certificate's name against `host` (libpq `verify-full`) on a real
PostgreSQL 18.6 server with TLS on, and refuse before connecting a `ca_file`
that cannot be honoured. Without `ca_file` the behaviour is unchanged
(`require`: encryption without verification).

## Independent inputs

- Data (`in/fixture.sql`, the documented example of `docs/execution.md`):
  `fixture.items(item_id int8, item_label text COLLATE "C")` with the rows
  (0,'zero'), (1,'one'), (2,'two'), (2,'two'), (3,'three'), (5,'five').
- Query (`in/demo-exec`, the documented example): `table active_items: from
  items where id > 1 select id, label`. Its meaning, independent of Pietto:
  every row whose id is greater than 1, duplicates kept, no order. Expected
  bag: **[2,'two'], [2,'two'], [3,'three'], [5,'five']** (compared sorted).
- SQL produced by the candidate CLI (`pietto emit-sql --project demo-exec
  --module main.pietto --kind table --name active_items --dialect postgres
  --emission-contract contract.json --format json`, status VERIFIED):
  `sql/statement.sql`, sha256
  `1091fc2827007cadcd1c821937e212441eaa81a19cf77c984a8d211e93cc240f`. Every
  client record must carry this sha256 for the SQL of the query it compiled
  from the tree under test.
- TLS (`gen-tls.sh`, local openssl, no network): `ca.pem` signs `server.pem`
  (subjectAltName `IP:127.0.0.1` only) and `elsewhere.pem` (subjectAltName
  `DNS:elsewhere.invalid` only); `other-ca.pem` signs neither. `absent.pem`
  does not exist. The server's `pg_hba.conf` admits `pietto_reader` only by
  `hostssl ... scram-sha-256` from 127.0.0.1 inside the container.
- The client always connects to `host="127.0.0.1"` (the relay), database
  `app`, user `pietto_reader`, premise `("fixture", "pg_catalog")`, default
  limits and isolation.

## Cells (each on `postgres_rows` and on `postgres_adbc`: 18 verdicts)

Phase A: the server presents `server.pem`.

| Cell | `sslmode`, `ca_file` | Expected result | Relay connection in the cell | Authorized `pietto_reader` session in the server log |
| --- | --- | --- | --- | --- |
| A1_full_ok | `require`, `ca.pem` | rows = the expected bag, `end == "COMPLETE"` | at least 1 | at least 1 |
| A2_wrong_ca | `require`, `other-ca.pem` | `AttemptFailed` `PIE-R2004` `CONNECTION_FAILED` | at least 1 | none, and no authentication line for it |
| A3_missing_ca | `require`, `absent.pem` | `AttemptFailed` `PIE-R2004` `CONNECTION_FAILED` | at least 1 | none, and no authentication line for it |
| A4_require | `require`, none | rows = the expected bag, `COMPLETE` (unchanged behaviour) | at least 1 | at least 1 |
| A5_disable_ca | `disable`, `ca.pem` | `RequestRejected` `PIE-R1002` detail `EXECUTION_ACCESS_PROFILE` | **0** (refused before connecting) | none |
| A6_system_ca | `require`, the literal `system` | `RequestRejected` `PIE-R1002` detail `EXECUTION_ACCESS_PROFILE` | **0** | none |
| C1_ambient_pgsslrootcert | `require`, `ca.pem`, plus `PGSSLROOTCERT` pointing at the run-owned fixture | `RequestRejected` `PIE-R2003` detail `AMBIENT_ENVIRONMENT` | **0** | none |

Phase B: the server presents `elsewhere.pem` (same CA, another name).

| Cell | `sslmode`, `ca_file` | Expected result | Relay connection | Authorized session |
| --- | --- | --- | --- | --- |
| B1_wrong_host | `require`, `ca.pem` | `AttemptFailed` `PIE-R2004` `CONNECTION_FAILED` | at least 1 | none, and no authentication line for it |
| B2_require_any_name | `require`, none | rows = the expected bag, `COMPLETE` (`require` checks no name) | at least 1 | at least 1 |

Reasons, independent of Pietto: libpq `verify-full` fails the TLS handshake
for an untrusted chain (A2), fails before the handshake when the root file is
missing (A3) and fails after the handshake, before the startup message, for a
name mismatch (B1); none of them reaches authentication. `require` verifies
neither chain nor name (A4, B2). A5 and A6 are refused by Pietto's own access
check, which runs before any connection.

Each successful cell must have a server log line with `SSL enabled` and its
route-specific `application_name` (`pietto_private_execution` for rows,
`pietto_postgres_adbc` for ADBC). A2 must contain the observed server TLS
`unknown ca` alert. B1 is a hostname-verification negative because B2 on the
same phase-B certificate and route succeeds without a CA; A2 is a chain
negative because A1 on the same phase-A certificate and route succeeds with
the trusted CA. These controls exclude an ordinary transport failure.

## Integrity (judged)

Exactly one client record per cell and route, no unexpected record; each record
must carry the pre-registered `sslmode`, `ca_file`, route application and SQL
sha256. Each cell's begin and end markers occur exactly once, in order, in both
`raw/relay.log` and `raw/pg-server.log`. `raw/campaign.json` must bind the
captured candidate tree and diff, fixed image and network, public input and
certificate identities, the public runner, relay, certificate generator and
installed HBA identities, every client exit status, the controlled HOME
fixture, and every raw record/log hash. Its absence or any mismatch is FAIL.

The runner creates the controlled HOME fixture from `other-ca.pem` and uses it
for every client. C1 alone also sets `PGSSLROOTCERT` to that run-owned path;
the expected pre-connect refusal verifies that Pietto rejects an ambient `PG*`
override before it can use a default. No user home, credentials or certificate
is read.

## Not proved here

Other TLS profiles (client certificates, CRLs, `verify-ca`), host names that
need resolution, IPv6, platforms other than the integration host, and MySQL
(whose `ca_file` is required already).
