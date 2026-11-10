# 76-S06 C76-06 TLS PostgreSQL package, run 2: root commands

`P=/home/mianliwang/.local/state/pietto/evidence/pietto-phase71-20261026/claude-takeover-20261027/claude-closeout-017-20261103/phase76/codex-recovery/s06/db-run2`.
`judge.py` and `relay.py` are stdlib-only (any Python 3.12+ runs them). `client.py` runs
in `$P/venv`, which holds the tree under test with both PostgreSQL extras.

```bash
P=/home/mianliwang/.local/state/pietto/evidence/pietto-phase71-20261026/claude-takeover-20261027/claude-closeout-017-20261103/phase76/codex-recovery/s06/db-run2
TREE=/home/mianliwang/projects/pietto-wt/p76-s06-codex   # or the integration tree that carries S06
cd "$P"
# 0. Only if the certificates expired (60 days from 2026-11-07, see raw/campaign.log):
#      nice -n 19 bash gen-tls.sh
# 1. The client environment: the tree under test plus psycopg-binary 3.3.5, ADBC 1.13.0 and
#    pyarrow 26.0.0 from the lock (offline; the editable install points at $TREE/src).
(cd "$TREE" && UV_PROJECT_ENVIRONMENT="$P/venv" UV_PYTHON=3.13.13 UV_OFFLINE=1 nice -n 19 \
   uv sync --locked --no-dev --extra execute-postgres --extra execute-postgres-adbc)
# 2. The SQL that tree emits must still be the pre-registered statement:
(cd "$P/in" && nice -n 19 "$P/venv/bin/pietto" emit-sql --project demo-exec --module main.pietto \
   --kind table --name active_items --dialect postgres --emission-contract contract.json --format json) \
  | python3 -I -c 'import hashlib, json, sys; print(hashlib.sha256(json.load(sys.stdin)["sql"].encode()).hexdigest())'
#    expect 1091fc2827007cadcd1c821937e212441eaa81a19cf77c984a8d211e93cc240f (sql/manifest.txt)
nice -n 19 python3 -I judge.py selftest           # fabricated worlds; writes no file
sha256sum ORACLE.md judge.py client.py receipt.py relay.py pg.sh gen-tls.sh sql/statement.sql  # compare with ORACLE-ERRATA.md
# 3. The database: one PostgreSQL container, local image by ID, --pull=never, --network none.
#    If raw/ exists from an earlier run, move it to raw-runN first (pg.sh refuses to overwrite).
nice -n 19 flock --close -w 600 /tmp/claude-1000/pietto-docker-campaign-postgres.lock timeout 3600 bash "$P/pg.sh"
# 4. Verdicts: 18 (9 cells x 2 routes); raw/campaign.json and raw/compare.json;
#    exit 1 on any FAIL.  The judge rejects a missing or incomplete receipt.
nice -n 19 python3 -I judge.py compare
```

- `pg.sh` follows the Phase74 `m/diff/pg.sh` recipe: image PG
  `sha256:f372eda99ac2ea249c3dce566dcdf468397035371284d2cf2103b4bc52b3b39e` (18.6), container
  `pietto-p76-s06-pg`, `--cpus 2 --memory 2g`, tmpfs data dir, `docker rm -f -v` in a trap (also
  on TERM from `timeout`). It logs the sha256 of every package file, the certificate end dates,
  the tree and staged-diff identity the venv points at, and the image
  before the first container command.
- In the container it writes `server.pem`, `elsewhere.pem` and their keys (mode 600, owner
  postgres) to the tmpfs, replaces `pg_hba.conf` with `in/pg_hba.conf`, loads `in/fixture.sql`,
  gives `pietto_reader` a random SCRAM password (never logged; the client reads it on stdin),
  and turns on `ssl` and `log_connections`. Phase B switches the server certificate to
  `elsewhere.pem` with `ALTER SYSTEM` and a reload, and logs the setting it observes.
- `--network none` leaves the server reachable only inside the container. `relay.py` listens on
  host 127.0.0.1 and runs one `docker exec -i ... bash` forwarder per TCP connection to
  127.0.0.1:5432 inside; TLS stays end to end (the relay copies ciphertext) and the server sees the
  client as 127.0.0.1, the only `hostssl` address of `pg_hba.conf`. The relay logs one `accept`
  line per connection.
- Each cell is one `client.py` process under `env -i` (no `PG*` or OpenSSL variables) with a
  run-owned HOME containing a controlled hostile root certificate, bracketed by
  `pietto-s06-mark begin|end CELL ROUTE` lines that pg.sh writes into the
  server log (`RAISE LOG`) and into `raw/relay.log`; the judge reads each log only between them.
- Expected wall time: about 3 minutes (18 cells; one failed connection costs up to about 10
  seconds of `connect_timeout`).

## Dry run already done in the lane (not evidence of record)

The same `client.py`, `relay.py` and `judge.py` ran against a local PostgreSQL 16 server (no
Docker; a stand-in `docker` forwarded the relay to the local port): `../dryrun-pg16/`. The ten
refusal and failure cells PASS on both routes; the six rows cells reach an authorized TLS session
(`verify-full` for A1) and then stop at the server version check (`PIE-R2005` on the rows route,
`PIE-R3999` on ADBC), as PostgreSQL 16 is not the pinned 18.6. Only the root's run above, on
18.6, decides C76-06.
