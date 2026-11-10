# PostgreSQL maintenance R3 preregistration

Status: `PREREGISTERED_NOT_STARTED`. This is the remaining PostgreSQL
maintenance qualification after the independently judged R2 TLS matrix. It
does not reopen TLS, change public behaviour, start Docker, or qualify a new
type/result shape.

R4 is a fresh run after the failed R3 judge. [ERRATUM.md](ERRATUM.md) freezes
the four existing-contract corrections. R3 raw evidence remains unchanged and
is not input evidence for R4 acceptance.

## Frozen closure

R3 reuses the exact candidate wheel, source patch, lock, PostgreSQL 18.6
configuration digest, `--network none` exec-stdio relay and fresh non-editable
wheel environment recorded by R2:

* base `f8ccd2c44a2d9adf431a496bd9bbae037783176f`;
* candidate patch sha256
  `548e72276b20c2bff3bb0613a527ef230fb9095942b562dca32a6150da12e1cc`;
* wheel sha256
  `f4c96921c4d4ceb057830f2dd21f2e634325dac2bef933532747ae4aab963a73`;
* PostgreSQL image configuration digest
  `sha256:f372eda99ac2ea249c3dce566dcdf468397035371284d2cf2103b4bc52b3b39e`.

The R2 raw directory is evidence of the preceding TLS matrix only. R3 creates
a fresh owned `raw/` directory, fresh container and fresh relay under the same
PostgreSQL engine lock. It records the same candidate wheel's
`direct_url.json`, Pietto module/`RECORD`, dependency origins and server
identity before a public attempt opens.

## Selected existing public stories

The fixture is a schema-2 project query against the existing typed PostgreSQL
source, through public `compile_query()` and `execute()` only.

| Story | Route | Existing contract being rechecked | Required observation |
| --- | --- | --- | --- |
| Bounded rows | `postgres_rows` | `ExecutionLimits` caps delivery, with the existing warning that native rows are received before delivery. | `batch_rows=1` yields ordered one-row public batches; `max_rows=3` fails with the existing resource terminal before a fourth delivered row; all handles close. |
| Early public close | `postgres_rows` | Closing before EOF stops delivery, rolls back and closes the owned attempt. | Read one checked batch, close the handle, record `STOPPED_EARLY`, `ROLLBACK_ACK`, owned session close and no later public batch. |
| Public cancellation | `postgres_rows` | `ResultHandle.cancel()` is the only controller-thread operation. | A client-owned controller cancels a current public handle; record the existing typed terminal, join the controller and close/reap the attempt. The test does not promise a new normalized target error. |
| Typed timestamp | `postgres_rows` | Existing supported timestamp result carrier. | One current documented typed `Timestamp` query gives the existing Arrow timestamp metadata/value; it is not a new temporal contract. |
| Flat Arrow batch lifetime | `postgres_adbc` | A public `ResultBatch` exports Arrow; imported Arrow data remains valid after the batch closes. | Import one flat batch, close the public batch, read the retained imported Arrow values/schema, exhaust handle to EOF and close its reader/attempt. |
| Raw Psycopg regression observation | direct Psycopg client only | Driver regression observation, not Pietto data admission. | For array, timestamp and interval values, record pre-close fetch, close connection, then the observed post-close operation/exception and process exit. No result is delivered through Pietto and no new array/interval/nested support is claimed. |

The driver observation runs in a child process with bounded stdout/stderr and
is judged only for complete raw fields and non-crash termination. Its expected
value is not a public Pietto oracle. `postgres_adbc` remains flat; neither the
driver observation nor a retained Arrow batch opens nested ADBC.

## Physical envelope

One later authorized command holds a persistent dispatch-selected lock for the
entire run. It creates only a fresh dispatch-selected container with
`--pull=never --network none`, tmpfs PostgreSQL data, and a trap that removes
the container and relay child. The host client reaches only a run-owned
`127.0.0.1` listener whose fixed `docker exec -i ... bash` forwarder connects
to `127.0.0.1:5432` inside the container. No port is published, no image is
downloaded, no external database or default network is used, and the command
has a two-hour ceiling.

## Negative self-checks before Docker

The R3 judge must reject at least these fabricated-world mutations before a
container starts:

1. an editable or non-wheel Pietto origin;
2. a missing candidate patch/wheel/image/relay identity;
3. a fourth `max_rows` delivery in the bounded story;
4. an early-close terminal marked `COMPLETE` or without `ROLLBACK_ACK`;
5. a retained ADBC Arrow batch that changes after public-batch close;
6. a raw driver observation that omits post-close status or exits by signal;
7. a lingering relay child or named container in the cleanup receipt.

## Stop conditions

Any changed emitted SQL, source fixture, candidate identity, driver origin,
raw public terminal, missing record, unbounded child, container/relay cleanup
failure, unavailable cached dependency or judge failure stops R3. Preserve its
raw directory and adjudicate a new run only after a root-cause repair. Do not
change the public runtime or normalize route terminals merely to satisfy this
maintenance witness.
