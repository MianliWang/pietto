# Phase77 numeric PostgreSQL parent R4 preregistration

Status: `PREPARED_NOT_STARTED`. This parent runs the frozen raw PostgreSQL
numeric primitive hook once after its owned literal-none container and relay
are ready. It does not run Phase76 TLS cells, public execution stories, MySQL,
or emitted Pietto SQL.

The parent binds base `f8ccd2c44a2d9adf431a496bd9bbae037783176f`, patch
`7345ddec240b89308f20867bfbcc9abf6f9cd7c49498b641f95df142cf62da2c`, wheel
`f4c96921c4d4ceb057830f2dd21f2e634325dac2bef933532747ae4aab963a73`, and
PostgreSQL image configuration
`sha256:f372eda99ac2ea249c3dce566dcdf468397035371284d2cf2103b4bc52b3b39e`.
It uses `/tmp/pietto-p77-maint-pg-run-r2/relay.py` copied here unchanged, a
fresh generated CA/server certificate pair, one owned `--network none`
container and `/tmp/claude-1000/pietto-docker-campaign-postgres.lock`.

Before Docker, `numeric_pg_hook.sh --self-check`,
`materialize_endpoint.py --self-check`, and
`p77_mysql_numeric_probe.py --self-check` must pass. The hook creates only
the `pietto_numeric_probe` role/database inside the owned container, passes
its generated password only through the named environment variable, and writes
the raw numeric receipt under its fresh `/tmp/pietto-p77-numeric-pg-run-*`
directory. The parent captures its stdout/stderr, server/relay logs, image,
container and cleanup facts. A hook failure leaves that run directory intact.

The parent saves those three actual preflight stdout/stderr pairs in its raw
directory, records the installed non-editable wheel origin and RECORD presence,
and writes `cleanup.json` only after the relay's checked wait terminal and the
owned container's absence. `parent_receipt.py` hashes the complete fixed parent
input, TLS-key, candidate lock/pins, raw and hook-file sets. `parent_judge.py`
then re-reads all of them and rejects a changed input, missing raw, failed
numeric terminal, wrong relay identity, non-`none` network, or incomplete
cleanup. The no-DB preparation selfchecks are saved in
`prestart-selfcheck/`; a later live run saves fresh preflight outputs in its
own raw directory and does not reuse these preparation observations.

The parent saves those three actual preflight stdout/stderr pairs in its raw
directory, records the installed non-editable wheel origin and RECORD presence,
and writes `cleanup.json` only after the relay's checked wait terminal and the
owned container's absence. `parent_receipt.py` hashes the complete fixed parent
input, TLS-key, candidate lock/pins, raw and hook-file sets. `parent_judge.py`
then re-reads all of them and rejects a changed input, missing raw, failed
numeric terminal, wrong relay identity, non-`none` network, or incomplete
cleanup. The no-DB preparation selfchecks are saved in
`prestart-selfcheck/`; a later live run saves fresh preflight outputs in its
own raw directory and does not reuse these preparation observations.

R4 is a fresh child of the preserved R1/R2 transport-entry failures and R3's
failed v1 raw plan. It freezes the independently reviewed v2 numeric manifest,
probe, hook and materializer from `/tmp/pietto-p77-numeric-prereg-r4`: unary
routes are repaired coherently; every observed raw terminal is appended before
judgment; literal arithmetic remains observation-only. The parent rebinds those
artifacts to its own copied relay and TLS closure, retains the already-reviewed
POSIX argument and container-ID protections, and captures `pg-server.log`
before cleanup whenever the hook fails. R4 does not alter candidate bytes,
image, transport topology or the raw-plan acceptance oracle.
