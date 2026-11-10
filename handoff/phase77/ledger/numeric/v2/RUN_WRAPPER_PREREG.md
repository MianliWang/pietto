# Phase77 numeric primitive wrapper preregistration

Status: `PREPARED_NOT_STARTED`. This record adds an endpoint identity for the
frozen numeric plan. It does not start a container, create a database, connect
to a target, or grant a product form.

## Parent-owned transport and input closure

The parent starts either engine only while its engine lock is held and the
other campaign state is known. Each wrapper has a two-hour outer timeout and
may create one new owned container using the fixed image with `--pull=never`
and `--network none`.

| Engine | Lock | Reused transport source | Inner target | Container bootstrap |
| --- | --- | --- | --- | --- |
| PostgreSQL 18.6 | `/tmp/claude-1000/pietto-docker-campaign-postgres.lock` | `/tmp/pietto-p77-maint-pg-run-r2/relay.py`, fixed port-5432 forward | `127.0.0.1:5432` | create `pietto_numeric_probe` role and same-named database, owned by that role |
| MySQL 8.4.12 | `/tmp/claude-1000/pietto-docker-campaign-mysql.lock` | `/tmp/pietto-p77-maint-mysql-none-campaign/relay.py`, fixed port-3306 forward | `127.0.0.1:3306` | create `pietto_numeric_probe`@`127.0.0.1` and same-named database, grant only that database |

The wrapper copies the named relay into its new run directory, verifies the
frozen source SHA in `manifest.json`, creates the owned loopback listener, and
writes the listener port only after the container's `NetworkMode == "none"`,
no attached networks/default routes and exact Docker-exec identity are
recorded. TLS remains end-to-end; the relay only copies bytes.

The role password is generated in the parent wrapper, passed only through the
wrapper child's `PIETTO_NUMERIC_PROBE_PASSWORD`, and never appears in command
arguments, plan, receipt or logs. Public maintenance roles and databases
(`pietto_reader`, `pietto_query`, `app`, `phase66`) are not numeric-probe
inputs.

The PostgreSQL hook appends one exact `hostssl pietto_numeric_probe
pietto_numeric_probe 127.0.0.1/32 scram-sha-256` line to the parent-created
container's HBA file and reloads it before it materializes the endpoint. A
failed run directory is preserved for the parent judge; cleanup removes only
the recorded owned container through the parent transport.

## Exact wrapper command interfaces

After START review, the parent creates the two small engine wrappers from the
listed transport sources. Their intended invocation is:

```sh
nice -n 19 flock --close -w 600 /tmp/claude-1000/pietto-docker-campaign-postgres.lock \
  timeout 7200 /tmp/pietto-p77-numeric-prereg-r4/numeric-pg.sh RUN_DIRECTORY

nice -n 19 flock --close -w 600 /tmp/claude-1000/pietto-docker-campaign-mysql.lock \
  timeout 7200 /tmp/pietto-p77-numeric-prereg-r4/numeric-mysql.sh RUN_DIRECTORY
```

These commands are an interface contract, not files that exist yet. Each
engine-specific wrapper must derive its container launch, certificate
setup, preflight, relay lifecycle and cleanup from the table's reviewed
transport source. It may add only the owned role/database bootstrap and this
call after it writes a complete endpoint JSON:

```sh
UV_PYTHON=3.13.13 UV_OFFLINE=1 UV_LINK_MODE=copy \
  CANDIDATE_PYTHON -I -B p77_mysql_numeric_probe.py \
  --run-plan manifest.json --endpoint-json endpoint.json --write-receipt numeric-receipt.json
```

`endpoint.json` has no password and must contain exactly the engine, dynamic
loopback listener port, `user` and `database` both equal to
`pietto_numeric_probe`, `password_env` equal to
`PIETTO_NUMERIC_PROBE_PASSWORD`, caller CA, identity verification, and the
matching frozen relay contract from `manifest.json`. Both engines require
hostname verification; before child START the parent verifies that the current
certificate SAN covers the endpoint name `127.0.0.1`. The probe rejects another
host, database, user, relay identity or TLS posture before opening a DB-API
connection.

## Required pre-START binding

The wrapper writes and its post-run judge reads: candidate base and complete
patch, wheel, lock, pin file, manifest bytes and SHA-256, Python/package origins,
relay source and command identity, exact image/config digest, container ID/name,
endpoint JSON with password removed, bootstrap role/database names, target
version record, raw DB-API receipt, relay log, server log, route proof, and
cleanup absence. A mismatch, missing record, warning retrieval failure,
listener/child cleanup failure or a failed plan verdict stops the engine
campaign. The next attempt is a new child observation, never a rerun claim.

## Deliberate non-goals

This is a raw primitive probe. It does not run emitted Pietto SQL, change the
numeric oracle, qualify the candidate maintenance wheel, open S01/S02, or
replace the public maintenance witness. Any raw result stays an observation
until the later candidate-emitted SQL and two-target product matrix closes.
