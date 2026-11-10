# MySQL maintenance candidate — preregistration

Status: `PREREGISTRATION_ONLY`. No container, database, target-conformance
command, Docker resource, package mutation, commit, push, or release has run.

## Candidate and immutable inputs

| Input | Bound value |
| --- | --- |
| Candidate checkout | `/tmp/pietto-maintenance-2601-338` at `f8ccd2c44a2d9adf431a496bd9bbae037783176f` plus its uncommitted maintenance patch |
| Candidate wheel | `/tmp/pietto-maintenance-2601-338-package-dist-r2/pietto-0.1.10-py3-none-any.whl` |
| Wheel SHA-256 | `f4c96921c4d4ceb057830f2dd21f2e634325dac2bef933532747ae4aab963a73` |
| Python and package identities | CPython 3.13.13; Pietto 0.1.10; PyArrow 26.0.1; mysql-connector-python 26.10.0 |
| Target | MySQL 8.4.12, linux/amd64, config digest `sha256:c9570e7b94230d3717b88a334acaea49a4fe6b162f68a8f2927eaaf866b7f867` |
| Target pins | Candidate `tests/phase66_target_pins.json`, only after its working tree and index agree with the candidate driver profile |

The final pre-acquisition rebind at 2026-11-08 uses absolute paths from
`/home/mianliwang/projects/pietto`: candidate `HEAD` is
`f8ccd2c44a2d9adf431a496bd9bbae037783176f`; the staged and working target-pin
bytes agree (`sha256 572a36a890cda4dc286cd9f9fcccf7998a292fc3b437b7836937960c74e87e92`)
and name Psycopg/Psycopg-binary 3.3.8; the candidate virtual environment
reports PyArrow 26.0.1 and mysql-connector-python 26.10.0. The earlier
relative-path observation of 3.3.5 was non-qualifying and is not an input to
this preregistration.

`expected-binding.json` in this directory is the preflight artifact supplied
to the launcher. It binds the candidate HEAD, complete uncommitted patch, pins,
lock and wheel bytes before Docker acquisition. The campaign recomputes every
field and refuses drift.

The run must reject a missing, mismatched or shadowed PyArrow distribution.
It does not qualify Psycopg, PostgreSQL, ADBC, nested results, or any Phase77
new MySQL form.

## Existing public-route witness

Use the existing execution-API native witness and its public `mysql_rows`
worker, through the external literal-none campaign package
`/tmp/pietto-p77-maint-mysql-none-campaign`. It is not a bare Arrow query. The
positive witness binds compiler source/contract, emitted SQL and parameters,
physical fixture/captured metadata, prepared execution, Arrow batch schema,
decoded values, EOF/terminal state, batch close and owned resource cleanup.

The existing MySQL public witness has these fixed observations:

| Case | Required result |
| --- | --- |
| rows and bundle | Ordered bag `[[1, null], [1, null]]`; terminal `COMPLETE` |
| empty | No rows; terminal `COMPLETE` |
| schema | `left_id: int64` non-null and `right_key: int64` nullable |
| bounded delivery | Existing `batch_rows=1` public handle/batch ownership path |
| cancel and deadline | Existing typed terminal and cleanup oracle; no cursor fallback |
| trust | Caller CA, verified `localhost`/`127.0.0.1` identity, TLS, no ambient connection attributes or OpenTelemetry propagation |

The broad current target-conformance manifest remains an unchanged
SQL/server/mysql-connector corpus for existing accepted forms. Its historical
internal-network receipt is retained as a non-literal-none closure reference;
it is not relabelled as this new PyArrow transport qualification. This
maintenance witness directly rechecks the changed PyArrow public flat path:
typed Int/NULL rows, empty result, `batch_rows=1`, prepared submission, bundle
load, Arrow batch lifetime/close and IPC round trip. It opens no previously
blocked target form.

## Proposed command sequence after review

1. Before acquisition, verify clean candidate state, its exact pin bytes,
   wheel identity, interpreter/distribution origins, cached image config digest,
   dependency profile, run directory absence, engine lock availability and no
   conflicting owned resource.
2. Run the existing MySQL native public witness against the candidate wheel,
   preserving its literal checker and raw report.
3. Run the external literal-none campaign through its only launcher,
   `mysql.sh`; it creates the owned offline installation prefix, calls the
   existing public worker and writes raw report, relay and cleanup facts.
4. Independently run `judge.py` over that exact report/relay evidence. Record
   raw command outputs, image/config identity, SQL inputs, physical metadata,
   report and cleanup chain. Do not rerun a failed attempt.

The launcher has a two-hour outer ceiling. The MySQL campaign holds
`/tmp/claude-1000/pietto-docker-campaign-mysql.lock` for the entire acquisition,
run, receipt check and cleanup. It can own only names beginning
`pietto-p77-maint-my-`; cleanup is `docker rm -f -v` only for its recorded
container. It creates no network.

## Literal `--network none` profile

The existing conformance/public-route harness uses an owned `--internal` bridge
network. That does not meet this dispatch's literal `--network none` rule, so
it cannot be reused as evidence for this run.

The smallest compatible delta reuses only its fixed `exec-stdio` raw TCP relay:
an owned host listener accepts a client and starts a fixed non-TTY
`docker container exec -i` child. Inside the verified owned MySQL container,
`/bin/bash` opens only `/dev/tcp/127.0.0.1/3306` and relays raw bytes. The
relay does not parse or terminate TLS. It owns no more than sixteen Docker
children, closes the listener and reaps every child before container cleanup.

The current repository helper limits that mode to PostgreSQL and hard-codes
port 5432. The external package retains repository behavior and carries the
target-specific immutable MySQL command for port 3306. Its profile must:

1. create the container with `--network none --pull=never`, without creating
   any Docker network;
2. verify `NetworkMode == "none"`, no attached networks and no default IPv4 or
   IPv6 route;
3. record the fixed command identity, container identity, `127.0.0.1:3306`
   target, owned listener, non-TTY property, child ceiling and close/reap
   lifecycle; and
4. write its own external literal-none receipt and verdict. It must not claim
   the existing internal-bridge profile passed.

The existing MySQL CA/hostname, prepared protocol, driver-origin, Arrow,
terminal and cleanup oracles remain unchanged. A missing command, cached image,
profile-reader update, route isolation proof, child cleanup or MySQL TLS
connection is a failure of this new profile, not a reason to fall back to the
internal bridge.

R7 preserved a deadline worker that reached `PIE-R3001` during admission before
its `open_ready` message. The observation is a pre-open deadline comparison;
it does not identify one transport operation as the sole cause, and the
separately recorded prepared-statement observer has no terminal label. The
external adapter changes only that deadline test input from 1.0 to 5.0 seconds,
the same bounded window already used by its cancel sibling. It records the
change in the resource journal and still requires the existing inflight lock
observation plus its original `PIE-R3001` deadline terminal. It does not alter
`ExecutionLimits` product behavior, the server timeout, or the native oracle.

The literal-none container keeps the base fixture bootstrap's three MySQL
environment keys: `MYSQL_ROOT_PASSWORD`, `MYSQL_ROOT_HOST=%` and
`MYSQL_DATABASE=phase66`. R1 omitted `MYSQL_ROOT_HOST`; R2 proved only that a
TCP listener answered before its manager connection failed. The next child
requires an authenticated in-container TCP `SELECT USER(), CURRENT_USER()`
over `127.0.0.1:3306` before it starts the relay. It records only the returned
user/host identities, never a credential hash or password.

R5's retained IPC record exposed `MYSQL_NATIVE_CONTEXT`; static comparison
found the external container had omitted `ONLY_FULL_GROUP_BY`. The repair child
uses `resources.MYSQL_MODE` directly, which is the same canonical value that
the target facility and native context validate. This is a fixture-profile
repair, not a new MySQL product form or a change to the native oracle. The
matched context observations remain required to witness the repair's actual
16-field row.

## Out of scope

No Phase77 S01–S27 product behavior, dependency release acceptance, Gate 2,
natural CI, tag, release, PyPI upload, external database, image pull, generic
network, ADBC route, or persisted execution artifact is included.
