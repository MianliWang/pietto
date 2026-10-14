# Execution (public alpha)

**Version:** This document describes the public alpha API of this source
tree. The tree still declares version `0.1.2`, but it is not the published
`0.1.2`: it contains later unreleased changes; for example, its extras select
`pyarrow==26.0.0` where the published `0.1.2` distributions select
`pyarrow==25.0.1`. The published GitHub pre-release and PyPI `0.1.2` are
described by this document at tag `v0.1.2`. The historical `0.1.1` wheel does
not provide this alpha surface.

`pietto.execution` compiles one query of your project, runs it explicitly on
PostgreSQL 18.6 through the PostgreSQL rows route, and hands you typed Arrow
batches and the attempt's real terminal state. A compiled query can also be
exported as a query bundle and loaded elsewhere under your own trust records,
and a `bind-safe` query can run with explicit parameter values.

`compile_query()` is the ordinary live-query compiler entry. It has no R2
mode, guard constructor, refinement constructor or source-recovery authority.
R2 is a separate live-only workflow that starts from such a query and takes
its own complete ordered source declarations and, for recovery, fresh
caller-held trust records.

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

The alpha covers `postgres_rows` and `postgres_adbc`, against PostgreSQL 18.6,
and `mysql_rows`, against MySQL 8.4.12. Both PostgreSQL routes use the same
explicit TCP inputs and deployment premise; `postgres_adbc` selects only its
pinned ADBC driver closure. The only qualified native profile recorded here is
CPython 3.13.13 on Linux x86-64 with the lock's exact artifacts on the
qualified integration host. Windows native execution is `NOTRUN`; an offline
Windows compiler-project check is not native execution, job, or database
support. Saved-result workflows are local workspace APIs, and the reference
sink is a local bounded endpoint. There is no CLI command that connects to a
database.

Saved-result APIs are public alpha surface. Their Python calls are explicit:
callers name a workspace, durable operation identities, records and any source
or sink authority. The CLI remains compilation-only; it neither opens a
workspace nor connects to a database.

## Support matrix

| Route | Selected target and dependencies | Explicit prerequisites | Qualified native evidence | Not claimed |
| --- | --- | --- | --- | --- |
| `postgres_rows` | PostgreSQL 18.6; `psycopg[binary]==3.3.5`; `pyarrow==26.0.0` | One TCP host, `PostgresAccess`, `PostgresDeploymentPremise`, and SCRAM-SHA-256. | Linux x86-64, CPython 3.13.13. | Windows native execution; another PostgreSQL release, libpq closure or TLS profile. |
| `mysql_rows` | MySQL 8.4.12; `mysql-connector-python==26.7.0`; `pyarrow==26.0.0` | One TCP host, `MySQLAccess`, `MySQLDeploymentPremise`, and caller-supplied CA with certificate and server-identity verification. | Linux x86-64, CPython 3.13.13. | Windows native execution; another MySQL release, connector version or provider profile. |
| `postgres_adbc` | PostgreSQL 18.6; `adbc-driver-postgresql==1.12.0`; `adbc-driver-manager==1.12.0`; `pyarrow==26.0.0` | PostgreSQL TCP access, deployment premise, SCRAM profile, and the selected driver closure. | Linux x86-64, CPython 3.13.13. | Windows native execution; another ADBC/libpq closure, PostgreSQL release or platform. |

The qualified profile is the integration host with the lock's exact artifacts.
Installing an extra selects no route, grants no execution, opens no source and
does not qualify storage. A missing or wrong selected dependency is refused
before connection; another route's driver is never a fallback. The PyArrow pin
does not bound allocator retention. Windows native routes are `NOTRUN`; an
offline Windows compiler-project check does not establish jobs, database
execution or a supported Windows profile.

## Install

The `0.1.2` distribution exposes `pietto.execution`. Install its selected
`execute-postgres`, `execute-postgres-adbc`, or `execute-mysql` extra in a
fresh environment, or build a wheel from the matching checkout. The PostgreSQL
rows extra adds `psycopg[binary]==3.3.5`; PostgreSQL ADBC adds
`adbc-driver-postgresql==1.12.0` and `adbc-driver-manager==1.12.0`; MySQL
adds `mysql-connector-python==26.7.0`; all select `pyarrow==26.0.0`. Compiling,
exporting and loading a bundle and an unopened `execute()` need none of these
extras. Without the selected route closure, opening an attempt is refused with
`PIE-R2001` before any connection; another installed driver is never a fallback.

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

### Saved-result API

These APIs are public alpha in `0.1.2`. They do not add a CLI database
command. Existing `check`, `emit-sql`, text output and JSON output keep their
contracts: JSON uses `ensure_ascii=True` and one trailing newline, while
`--output` reports its clear output error through the established CLI result
rather than opening a database or workspace.

`create_workspace(root, *, budget_bytes) -> WorkspaceRef` creates exactly one
v7 workspace. `open_workspace(root, *, expected_identity) -> WorkspaceRef`
reopens only the named v7 identity and never migrates it. `new_operation() ->
str` allocates a caller-held durable-operation identity, and
`operation_result(workspace, operation) -> OperationReply | None` only reads
the recorded first step. `WorkspaceRef` is an opaque `(root, identity)` value;
it is not a SQLite connection and cannot be copied or pickled.

`inspect_job(workspace, *, job) -> JobObservation` returns one immutable,
consistent recorded-metadata view. `JobObservation` has `job`, `revision` and
generations in durable creation order. Each `GenerationObservation` has
`identity`, `route`, `isolation`, `checkpoint`, `frontier`, `committed`,
`holes`, `observed_end` and every recorded terminal attempt ID in ordered
`closings`. It refuses a concurrent revision change instead of merging
observations. This is recorded metadata only: it does not read saved rows,
open a source, claim a publisher, write state, verify a member, select a
closing, or grant execution, source, trust, publication, retention, recovery
or ACK authority. In particular, multiple `closings` remain multiple facts;
the observation never chooses a successful or publishable one.

`save(workspace, query, *, operation, route, access, premise,
limits=ExecutionLimits(), isolation="stable", values=None, job=None) ->
SaveReply` makes one ordinary capture. It is not R2. A repeated `operation` is
looked up before a later claim or generation write and returns the factual
`REPLY_LOST_OR_PARTIAL` observation; it never infers completion or retries.
`SaveReply` has `workspace`, `operation`, `job`, `generation`, `admission`,
`terminal`, `settlement` and `cleanup`. A `FAILED_REMOTE_UNOBSERVED` reply may
carry a `SaveCloseHandle`; call its `close()` to make one bounded cleanup
resume/await attempt. Until that returns, `closed` is false and the remote
outcome remains `UNKNOWN`; this is not an ACK.

R1 is source-free replay of one fixed saved checkpoint. Allocate a caller-held
identity with `new_consumer_identity()`, then call
`open_saved_read(workspace, *, job, generation, checkpoint, consumer,
register_operation=None, open_operation, expected_pin, accepted_producer,
accepted_compatibility, values, scope="complete_capture", extent, purpose,
route, batch_rows, seconds) -> SavedRead`. `SavedRead.next(rows, *, operation)`
returns `SavedBatch | SavedReadEnd`; only `SavedRead.ack(batch, *, operation)`
advances its frontier. Close the reader (or use `with`) to release its local
reader and publisher resources. `release_saved_read(workspace, *, job,
generation, checkpoint, consumer, operation, expected_pin, accepted_producer,
accepted_compatibility, values, scope="complete_capture", extent, purpose,
route, batch_rows, seconds) -> OperationReply` is the separate retention
release. R1 does not access a source, manufacture an ACK, or release retention
when a reader merely exhausts its local extent.

Both R1 calls take `expected_pin`, `accepted_producer` and
`accepted_compatibility` as fresh caller-held scalar strings; the public API
does not infer them from a workspace, checkpoint or inspection result.

`verified_export(workspace, *, job, generation, checkpoint, scope, extent,
purpose, route, values, expected_pin, accepted_producer,
accepted_compatibility, seconds, batch_rows) -> VerifiedExport` is a distinct,
read-only source-free reader of one fixed snapshot. Iterate it or use `with`;
its `close()` closes its local reader and workspace. It has no caller operation,
does not acquire a coordinator, and writes no row, delivery, ACK or retention
fact.

R2 is live same-source recovery only. `R2SourceInput(namespace, name,
provider, version, revision, registry_namespace, registry_name, definition,
token_columns, role, provider_guarantee)` declares one qualified source. R2
requires an ordinary live `CompiledQuery` from `compile_query`; a loaded bundle
is refused, and callers cannot manufacture a guard or refinement. Its
`source_requirements` must be one `R2SourceInput` for every compiled source,
in the compiled source order, including guarded and refined sources and sources
read only inside a relation let; a partial,
reordered or substituted tuple is refused. It is not an option on
`compile_query`.
`save_recoverable(workspace, query, *, source_requirements, operation, route,
access, premise, limits, isolation="stable", values=None, job=None) ->
SaveReply` records R2 retention before progress. `recover(workspace, *, job,
generation, checkpoint, query, source_requirements, operation, route, access,
premise, limits, expected_pin, accepted_producer, accepted_compatibility,
purpose, seconds, isolation="stable", values=None) -> SaveReply` validates the
recorded checkpoint and trust inputs, requalifies the sources and continues one
new R2 attempt. Before any workspace access, `recover` requires a non-empty,
printable `purpose` of at most 256 UTF-8 bytes and integer `seconds` from 1 to
86400. In both calls `source_requirements` is caller-supplied and in
the compiled source order, with one declaration for every source, including
guarded and refined sources. An ordinary `save`, a source-free reader/export,
and a loaded bundle never acquire this authority. R2 uses the same factual
operation replay and possible `SaveCloseHandle` rule as ordinary save.

Each R2 attempt takes the caller's values, access and deployment premise anew.
`recover` also takes fresh caller-held scalar `expected_pin`,
`accepted_producer` and `accepted_compatibility` inputs; `save_recoverable`
uses the current live query's records. Neither call derives R2 authority,
values, trust, or a premise from inspection metadata.

`publish_saved_generation(workspace, *, job, generation, checkpoint, closing,
purpose, route, isolation, values, expected_pin, accepted_producer,
accepted_compatibility, seconds, operation) -> PublicationReply` makes one
complete local publication after accepting a fixed captured generation.
`PublicationReply` names the workspace, operation, job, generation,
checkpoint, closing, extent, retention and terminal. Repeating the preparation
operation reports `REPLY_LOST_OR_PARTIAL`; it does not guess a later visibility
write. Publication also takes the three fresh caller-held scalar trust inputs
`expected_pin`, `accepted_producer` and `accepted_compatibility`; `closing` is
an explicit caller choice subject to publication validation, never an
`inspect_job` selection. `retire_generation(workspace, *, job, generation, operation) ->
OperationReply` retires only a caller-owned unpublished generation's implicit
latest-checkpoint root. It is neither general garbage collection nor a release
of another retention.

`create_reference_sink(root, *, namespace, epoch, retention_seconds,
budget_bytes=..., busy_seconds=5.0) -> ReferenceSinkDescriptor` creates and
reads back the minimal local reference-sink descriptor. The descriptor holds
no open sink resource and carries `root`, `identity`, `namespace`, `epoch`,
`retention`, `budget_bytes` and `busy_seconds`.
`relay_live(workspace, query, *, operation, route, access, premise, sink_root,
expected_sink_identity, sink_namespace, sink_epoch, sink_retention,
sink_budget_bytes, sink_busy_seconds=5.0, limits=None,
isolation="stable", values=None) -> RelayReply` starts one fresh live
capture/relay to that exact descriptor; earlier saved results are not its
input. `RelayReply` has the save-like factual fields and may carry a
`RelayCloseHandle`; close it only to settle the retained relay cleanup. A
reference sink is not a general callback facility and a relay does not promise
delivery to arbitrary sink code.

### Effects and resource end

| Call | Source and database use | Local workspace/sink effect | Caller end or release |
| --- | --- | --- | --- |
| direct `execute()` | one fresh route attempt | none | close `ResultHandle` and batches |
| `inspect_job()` | no source or database access | read-only recorded metadata; no publisher claim | no retained public handle |
| `save()` | one admitted fresh attempt | job, generation, chunks and checkpoints | terminal capture; close a returned cleanup handle |
| R1 `open_saved_read()` | no source or database access | holds the reader/publisher resources for its fixed scope | close the `SavedRead`; release retention separately when authorized |
| `verified_export()` | no source or database access | read-only fixed-snapshot reader; no coordinator | close the export |
| R2 `save_recoverable()` / `recover()` | one qualified live same-source attempt | R2 retention plus capture/recovery facts | terminal capture; close a returned cleanup handle |
| `publish_saved_generation()` | no source or database access | local publication and its retention fact | no retained public handle |
| `retire_generation()` | no source or database access | only the eligible unpublished root | no retained public handle |
| `create_reference_sink()` | no database access | creates and closes a local sink before returning its descriptor | descriptor owns no handle |
| `relay_live()` | one qualified fresh route attempt | a submission to the named local sink | close a returned relay cleanup handle |

Workspace and sink locks, coordinators, SQLite connections, native owners,
credentials, queues and schedulers remain private. No call performs automatic
retry, general collection, age-based deletion, fallback, or acknowledgement.

### Saved workflow and observation boundary

The ordinary capture part of a saved workflow is public. It reuses the live
`query`, `access` and `premise` from the example above and needs a real qualified
route; it does not fabricate a saved result when a database is unavailable.

```python
from pietto.execution import create_workspace, new_operation, save

workspace = create_workspace("saved-results", budget_bytes=64 * 1024 * 1024)
operation = new_operation()
reply = save(
    workspace,
    query,
    operation=operation,
    route="postgres_rows",
    access=access,
    premise=premise,
)
if reply.terminal != "COMPLETED":
    raise RuntimeError(reply.terminal)
assert reply.job is not None and reply.generation is not None
```

`reply.settlement` is a state word such as `RELEASED`, not an operation or
snapshot identity. Inspect the recorded job, locate the generation named by the
reply, and make the completeness decision explicitly. `frontier` is the saved
extent only when the caller has checked `checkpoint is not None`, `holes == ()`
and `observed_end == frontier`. `closings` preserves every recorded terminal
attempt and does not pick one; this ordinary example refuses zero or multiple
closings rather than selecting a winner. It is not an R2 closing-selection
procedure.

```python
from pietto.execution import (
    export_bundle,
    inspect_job,
    new_consumer_identity,
    open_saved_read,
    release_saved_read,
    SavedReadEnd,
    verified_export,
)

# Trust and values are caller-held public records; inspect_job never supplies them.
bundle = export_bundle(query)
expected_pin = bundle.pin
accepted_producer = bundle.producer
accepted_compatibility = bundle.compatibility
values = ()  # The preceding preserve query has no value slots.

observed = inspect_job(workspace, job=reply.job)
generation = next(item for item in observed.generations if item.identity == reply.generation)
if (
    generation.checkpoint is None
    or generation.frontier <= 0
    or generation.holes != ()
    or generation.observed_end != generation.frontier
    or len(generation.closings) != 1
):
    raise RuntimeError("generation is not a complete single-closing capture")

checkpoint = generation.checkpoint
extent = generation.frontier
consumer = new_consumer_identity()

with open_saved_read(
    workspace,
    job=observed.job,
    generation=generation.identity,
    checkpoint=checkpoint,
    consumer=consumer,
    register_operation=new_operation(),
    open_operation=new_operation(),
    expected_pin=expected_pin,
    accepted_producer=accepted_producer,
    accepted_compatibility=accepted_compatibility,
    values=values,
    extent=extent,
    purpose="read-saved-result",
    route=generation.route,
    batch_rows=256,
    seconds=60,
) as reader:
    while True:
        item = reader.next(256, operation=new_operation())
        if isinstance(item, SavedReadEnd):
            break
        with item.batch:
            print(item.batch.num_rows)
        reader.ack(item, operation=new_operation())

release_saved_read(
    workspace,
    job=observed.job,
    generation=generation.identity,
    checkpoint=checkpoint,
    consumer=consumer,
    operation=new_operation(),
    expected_pin=expected_pin,
    accepted_producer=accepted_producer,
    accepted_compatibility=accepted_compatibility,
    values=values,
    extent=extent,
    purpose="read-saved-result",
    route=generation.route,
    batch_rows=256,
    seconds=60,
)

with verified_export(
    workspace,
    job=observed.job,
    generation=generation.identity,
    checkpoint=checkpoint,
    scope="complete_capture",
    extent=extent,
    purpose="export-saved-result",
    route=generation.route,
    values=values,
    expected_pin=expected_pin,
    accepted_producer=accepted_producer,
    accepted_compatibility=accepted_compatibility,
    seconds=60,
    batch_rows=256,
) as exported:
    for batch in exported:
        batch.close()
```

The example deliberately does not turn recorded facts into verified members,
native completion, ACK or trust. It also does not use private attributes,
SQLite files or test helpers. It does not select a `closing` for publication:
multiple recorded closings remain multiple facts. Publication, when separately
authorized by its caller, requires an explicit caller-supplied closing that its
own validation accepts. R2 recovery still requires its caller-held checkpoint
and fresh trust, source, value and deployment inputs.

- `compile_query(project, *, module, kind, name, dialect, emission_contract,
  literal_policy="preserve") -> CompiledQuery` takes the arguments of
  `pietto emit-sql --project` and runs the same pipeline. When the project input
  is refused it raises `CompileRejected`: its `emission` is the command's JSON
  failure document byte for byte, its `status` that document's status and its
  `str()` the command's `--format text` report. It raises `RequestRejected`
  instead for an argument that is `None` (`PIE-R1001`) or invalid (`PIE-R1002`),
  checked before the project is read (where the command prints its usage
  error), and when a verified query cannot become an execution (`PIE-R1004`,
  `PIE-R1005`).
- A `CompiledQuery` exposes `origin` (`"live"` from `compile_query`, `"bundle"`
  from `load_bundle`), `module`, `kind`, `name`, `dialect`, `release`,
  `literal_policy`, `slots` (the tag of each value slot, see [Values](#values))
  and `emission`, the same `pietto.sql-emission.v1` artifact the command prints
  (`None` for a loaded bundle). Only `compile_query` and `load_bundle` create
  one, and it cannot be pickled or copied. It is a snapshot of what was
  compiled; see [Repeated calls and
  invalidation](#repeated-calls-and-invalidation).
- `export_bundle(query) -> QueryBundle` returns the query as bundle bytes,
  `payload`, and three records that name them, `pin`, `producer` and
  `compatibility`. `load_bundle(payload, *, expected_pin, accepted_producer,
  accepted_compatibility) -> CompiledQuery` loads exactly the bytes your
  records name. See [Query bundles](#query-bundles).
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
- `MySQLAccess(host, port, database, user, password, ca_file, account,
  roles="NONE")` is the explicit MySQL connection input. It redacts its
  password and cannot be pickled or copied. `ca_file` is required; Pietto
  verifies both the certificate and server identity. `account` and `roles`
  are checked against the freshly observed session context.
- `MySQLDeploymentPremise(schemas)` is the same operator commitment for the
  query's MySQL sources. The schemas must cover every source and cannot name
  `mysql`, `sys`, `information_schema` or `performance_schema`.
- `ExecutionLimits(batch_rows=256, batch_bytes=1 MiB, max_rows=1048576,
  max_bytes=64 MiB, seconds=20.0)` bounds one attempt; `seconds` is its
  deadline, `max_bytes` also counts the route's qualifying profile and catalog
  reads, and each statement runs with a server-side timeout of at most 10
  seconds that Pietto sets itself.
- `execute(query, *, route, access, premise, limits=ExecutionLimits(),
  isolation="stable", values=None) -> ResultHandle` checks the request before
  any connection and returns an unopened handle; the driver and the environment
  are checked when the attempt opens, except MySQL's refused OpenSSL names,
  which are checked while its bridge is prepared before the private native
  module imports `ssl`. `route`, `access` and `premise` have no
  default. There is no parameter that takes SQL text. Each call binds afresh and
  is a new attempt with its own `attempt` identifier. `isolation` is `stable`
  (REPEATABLE READ READ ONLY) or `serializable` (SERIALIZABLE READ ONLY).
  `values` gives one value per slot of the query (see [Values](#values)).
- `ResultHandle` runs that one attempt. Use it in a `with` block or iterate it:
  entering, or the first `next()`, connects; each `next()` returns a
  `ResultBatch`; the end of the result commits and closes it; `close()` before
  the end stops early and rolls back. `pa.schema(result)` gives the schema
  of its batches without opening or consuming the attempt. `outcome` returns a
  fresh `Outcome` snapshot. Use a handle from one thread; it cannot be pickled.
- `ResultBatch` is one checked batch you own. Export it through the Arrow
  PyCapsule interface, for example `pyarrow.record_batch(batch)`; the imported
  Arrow batch shares its buffers and stays valid after you close the batch or
  the handle. `num_rows` gives its size.
- `Outcome` carries `attempt`, `route`, `end`, the layered `source`,
  `transaction`, `delivery` and `cleanup` states, `remote_source_use_end`,
  `rows`, `batches`, `bytes`, `deadline_expired`, `primary`,
  `cleanup_failures`, `cancel_requested`, `cancel_sent`, `cancel_observed` and
  the two declarations above as `premise_compliance` and
  `native_definition_lifetime_exclusion`.

### Terminal states

| `end` | Meaning |
| --- | --- |
| `NOT_STARTED` | Not opened yet, or closed before it was opened. |
| `OPEN` | Opened and not closed. |
| `COMPLETE` | Read to the end of the result and committed (`transaction` is `COMMIT_ACK`), with no failure. |
| `STOPPED_EARLY` | Closed before the end; the transaction was rolled back. |
| `DEADLINE` | `limits.seconds` expired. |
| `CANCELLED` | `cancel()` won before the attempt completed. |
| `FAILED` | A failure ended it; `primary` says which. This includes a result read to the end and committed whose cleanup then failed (see below). |
| `FAILED_REMOTE_UNOBSERVED` | PostgreSQL ADBC cleanup has failed or timed out and remains available only for an explicit `close()` retry. The handle is not closed, but cannot read, reopen or claim remote completion. |
| `DROPPED` | Only in an `UnclosedHandleWarning`: the open handle was garbage-collected, or was still open at interpreter exit. |

`transaction` is `COMMIT_ACK` or `ROLLBACK_ACK` only after the server
acknowledged it; `UNKNOWN` stays `UNKNOWN`, and `remote_source_use_end` is then
`REMOTE_QUIESCENCE_UNCONFIRMED`. It is `REMOTE_QUIESCENCE_UNCONFIRMED` for an
attempt that never connected too: Pietto reports the end of remote use only
when the server acknowledged it. Closing a handle is not an acknowledgement and
does not make an early stop complete. Once an attempt is closed its outcome no
longer changes; an exception raised afterwards inside the `with` block passes
through without being recorded.

`ResultHandle.cancel()` returns `None` and is the one handle operation a
controller thread may call while another thread consumes the handle. It records
whether manual cancellation was requested, sent to the driver and observed by
the attempt in `outcome.cancel_requested`, `cancel_sent` and `cancel_observed`.
The same facts also record a deadline's private cancellation request; they do
not by themselves select a terminal. A request that loses to completion, close
or another failure changes no settled terminal. A request without an observed
cancellation does not claim remote quiescence.

If manual cancellation wins, the later public operation reports `PIE-R3009`
and the settled end is `CANCELLED`. Sending a request and observing it are
separate facts; neither alone establishes a server acknowledgement. A cancel
after another terminal has settled is a no-op and cannot change the outcome.
When PostgreSQL reports a cancelled statement after it has entered an aborted
transaction, the outcome retains `transaction=UNKNOWN`, failed cleanup and its
`PIE-R5001` transaction failure; cancellation observation is not a rollback ACK
or a remote-quiescence claim.

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

When PostgreSQL ADBC cleanup cannot complete, its public end is
`FAILED_REMOTE_UNOBSERVED` while `closed` remains false. The original failure,
`UNKNOWN` transaction state and remote-unobserved cleanup facts remain in the
outcome; `next()` and re-entry are refused with `PIE-R4001`. A later explicit `close()` retries
only the established cleanup and does not resume execution or replace those
facts with an acknowledgement.

A `KeyboardInterrupt` or other `BaseException` during finalization first runs
the bounded cleanup available to the route, records its resulting terminal and
cleanup facts, then propagates the original exception unchanged. It is never
replaced by an execution error.

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
the selected route and the query was compiled for its selected dialect
(`postgres_rows` or `postgres_adbc`/`postgres`, or `mysql_rows`/`mysql`,
`PIE-R1003`). It
then checks that `values` is `None` or a tuple (`PIE-R1002`), binds the query
to the values (`PIE-R1006`, `PIE-R1004`), reads the installed code identity
again (`PIE-R1005`) and checks the values of `premise`, `access`, `isolation`
(its type included) and `limits`, in this order, and raises the first refusal.
When an attempt opens, refused environment variables run first; then the
pinned driver and its selected implementation; then pinned PyArrow; all run
before a connection. `pyarrow.schema(result)` can instead raise `HandleMisuse`
`PIE-R4004` when it cannot export the schema, without changing the attempt.

`load_bundle()` checks `payload`, `expected_pin`, `accepted_producer` and
`accepted_compatibility` in this order, each given (`PIE-R1001`) and then of
the right type (`PIE-R1002`). It then checks that the installed code is the
code `accepted_compatibility` names (`PIE-R1005`), before it reads the bytes;
that the bytes are not empty and at most 32 MiB (`PIE-R1002`); that they are
the bytes `expected_pin` names (`PIE-R1007`); that they decode, verify and name
the accepted producer and compatibility (`PIE-R1008`); that the query is one
`compile_query` can produce (`PIE-R1004`); and that it becomes an execution
template (`PIE-R1004`, or `PIE-R1005` when the code changed in between). Bytes
whose bracket nesting the bounded reader refuses before it hashes them are
malformed (`PIE-R1008`), whatever the pin. `export_bundle()` checks that
`query` is given (`PIE-R1001`) and is a `CompiledQuery` (`PIE-R1002`).

Error text never contains a password, driver message, SQL text, value or bundle
content, and a public error is not chained to the private or driver exception
it classifies. A
`KeyboardInterrupt` or another `BaseException` that is not an `Exception`
passes through unchanged after bounded cleanup and is recorded as `PIE-R3008`.
If it arrives while the attempt commits, rolls back or closes its connection,
the outcome also records that step's `PIE-R3006` or `PIE-R5001` cleanup failure;
the original exception still propagates.

## Values

With `literal_policy="bind-safe"`, the literals that Pietto sends to the server
as parameters of the prepared statement are the query's slots; the SQL text is
the same for every value. `query.slots` gives the tag of each slot, `Bool`,
`Int`, `Float` or `Text`, in slot order, the order in which `execute()` takes
their values. Compiled with `bind-safe`, the example's `1` in `where id > 1` is
its only slot: `query.slots` is `('Int',)`, and `values=(3,)` returns the rows
with `id > 3`. A `preserve` query writes its literals into the SQL text and has
no slots.

Slot order is the compiler's order of the literals:

- The tables and queries that the query reads come first, each after the ones
  it reads, then the query itself. This is the compiler's schedule, not the
  order in which the query names its inputs: in a `union all` of `from a` and
  `from b`, the literals of `b` come first when `b` is declared before `a`. A
  table that the query reads twice contributes its literals once.
- Within one table or query, the literals of `let` come before those of
  `where`, and those before the ones of `select`; each expression is read from
  left to right. With `let: bonus = id + 30`, `where id > 1 and label != "x"`
  and `select: more = bonus + 7`, the slots are `30`, `1`, `"x"` and `7`.
- The live query's `emission` shows every slot: `fixed_values[i]` is slot `i`
  with its tag and compiled value, and the `ranges` entry of kind `parameter`
  whose `subject` is that record's `site` locates the literal in your source
  file through its origin's `location` (`path`, `line` and `column`). A loaded
  bundle has no `emission` but keeps the slot order of the query it was
  exported from, so keep this mapping with your records if you need it.

The values:

- `values=None`, the default, binds the values the query was compiled with
  (for a loaded bundle, the values recorded in it).
- Otherwise `values` is a tuple with exactly one value per slot, in slot order,
  each of its slot's exact type; nothing is converted. `Bool` takes a `bool`;
  `Int` an `int` that is not a `bool`, from `-2**63` to `2**63 - 1`; `Float` a
  finite `float`, never an `int`; `Text` a `str` that UTF-8 can encode and that
  contains no NUL character. A list or any other type is refused with
  `PIE-R1002` (`PUBLIC_VALUES_TYPE`). A tuple of another length is refused with
  `PIE-R1006` and `detail` `BINDING_SLOTS`, and a value outside its slot's type
  or range with `PIE-R1006` and `detail` `BINDING_VALUE:<ordinal>:<tag>`, where
  `<ordinal>` is the 0-based slot number; neither shows the value.
- A slot is one literal. In `where id > -1` the slot holds `1` and the minus
  stays part of the query, so `values=(5,)` means `id > -5`. `LIMIT` counts and
  window frames are part of the query, never slots.
- A value of the right type can still make the query impossible to prepare:
  under a sign or inside arithmetic, a slot accepts only values whose result
  stays representable for every value that the contract's domains allow, so
  `-2**63` under that minus is refused. That is `PIE-R1004` with `detail`
  `BINDING_INVALID`, which does not name the slot.

## Query bundles

`export_bundle(query)` returns a `QueryBundle`: `payload`, the bundle bytes,
and three records of 64 lowercase hexadecimal characters each:

- `pin`, the content identity of exactly these bytes;
- `producer`, the identity of the project's source files and emission contract
  and of the code that built the bytes;
- `compatibility`, the identity of the Pietto and ANTLR runtime files that were
  installed when the query was compiled; only installed code with that identity
  loads and runs the bytes.

`load_bundle(payload, *, expected_pin, accepted_producer,
accepted_compatibility)` returns a `CompiledQuery` with `origin` `"bundle"`
that runs exactly like the query it was exported from: the same SQL, the same
slots and, for `values=None`, the same values. It reads no project file. Each
load is a new query, and nothing about an accepted bundle is remembered.

`bundle_query.py` sits next to `run_query.py` in the example. It builds the
bundle from `demo-exec` with `bind-safe` literals, then loads it and runs it
with two values. Run it like `run_query.py`, with the password on standard
input:

```python
import sys

import pyarrow as pa

from pietto.execution import (
    PostgresAccess,
    PostgresDeploymentPremise,
    compile_query,
    execute,
    export_bundle,
    load_bundle,
)

# Build: compile, export and write the bundle bytes.
bundle = export_bundle(
    compile_query(
        "demo-exec",
        module="main.pietto",
        kind="table",
        name="active_items",
        dialect="postgres",
        emission_contract="contract.json",
        literal_policy="bind-safe",
    )
)
with open("active_items.bundle", "wb") as file:
    file.write(bundle.payload)
# Keep these three records in your own records, not next to the bundle file.
records = dict(
    expected_pin=bundle.pin,
    accepted_producer=bundle.producer,
    accepted_compatibility=bundle.compatibility,
)

# Run: load exactly the bytes the records name, then run them twice.
with open("active_items.bundle", "rb") as file:
    query = load_bundle(file.read(), **records)
print(query.origin, query.slots)
access = PostgresAccess(
    host=sys.argv[1],
    port=int(sys.argv[2]),
    database=sys.argv[3],
    user=sys.argv[4],
    password=sys.stdin.readline().rstrip("\n"),
    sslmode=sys.argv[5] if len(sys.argv) > 5 else "require",
)
premise = PostgresDeploymentPremise(schemas=("fixture", "pg_catalog"))
for value in (1, 3):
    ids = []
    with execute(
        query, route="postgres_rows", access=access, premise=premise, values=(value,)
    ) as result:
        for batch in result:
            with batch:
                ids.extend(pa.record_batch(batch).column("id").to_pylist())
    print(value, sorted(ids), result.outcome.end)
```

It prints `bundle ('Int',)`, then `1 [2, 2, 3, 5] COMPLETE` and
`3 [5] COMPLETE`.

A bundle never vouches for itself. Each entry has its own trust basis:

| Entry | What it trusts | Where that comes from |
| --- | --- | --- |
| `compile_query` | the project files under the root you name, read once when compiling, and the installed code | your own project |
| `load_bundle` | exactly the bytes `expected_pin` names, built from the inputs `accepted_producer` names, for the code `accepted_compatibility` names | your own records, typically taken from `export_bundle` when you build the bundle and kept apart from where the bytes travel |

- The three records are required keyword arguments without a default. Pietto
  never takes them from the bytes, a file beside them or the environment, and
  it has no function that turns bytes you pass, or the installed code alone,
  into a record: records come only from `export_bundle` of a query that you
  compiled or loaded yourself. The bundle's own producer and compatibility are
  compared with yours, never adopted.
- The pin is a content identity, not a signature. It protects the bytes only
  when it comes from your own records: whoever can change the bytes can also
  compute a pin for the changed bytes, and changed bytes loaded with such a pin
  are accepted. Keep the records where the sender of the bytes cannot change
  them. This alpha has no signing, registry or revocation. The records are
  deterministic identities of the content, not secrets: they confirm a guess
  of the query's literals and names, so where the literals matter, keep the
  records as confidential as the bundle.
- A bundle holds the query's literal values, names and emission contract in
  clear text, but never an access, a premise, a credential or the state of an
  attempt: exporting before and after attempts gives the same bytes. Treat a
  bundle like the query's source. Pietto never shows its content: errors carry
  category words only, and `repr()` of a `QueryBundle` shows only the length of
  its payload.
- A loaded query is an ordinary direct query: every `execute()` takes its own
  access and premise, the premise's `schemas` must cover the bundle's own
  sources (`PIE-R1002` otherwise), and the sources are requalified in every
  attempt. No SQL text enters through a bundle: bytes that are not a bundle,
  SQL text included, are refused with `PIE-R1008` even under their own pin.
- Only queries that `compile_query` can produce are loaded; a bundle with a
  guard program or a refinement is refused with `PIE-R1004`.
- The same query of the same project files, contract and literal policy,
  compiled by the same installed code, gives byte-identical bundles wherever
  the project directory is.
- A bundle loads only while the installed code has the identity that its
  compatibility names: changing any installed Pietto `.py` file or the ANTLR
  runtime, which includes every Pietto release, refuses its records with
  `PIE-R1005`. Export the bundle again from the project with the new code, or
  keep the environment that built it to run it; there is no migration and no
  compatibility between versions.

## Repeated calls and invalidation

A `CompiledQuery` can be executed any number of times, one call after another.
Each `execute()` binds the query afresh and is a new attempt; the calls share
only the immutable compiled query. Values, access, role, premise, limits and
isolation come from that call, and each attempt qualifies the sources and meets
the server's privilege checks itself. A refused call creates nothing and
changes nothing, and a failed attempt does not affect the next one. Pietto
caches no binding, request, qualification, accepted bundle or failure.

The code identity is that of the installed Pietto and ANTLR runtime files at
the moment of each call, not that of the modules a running process has already
imported. After the installed code changes, for example by an upgrade, restart
every process that imported Pietto before it compiles, exports, loads or
executes again. A process that keeps running refuses what it compiled or
loaded before the change (`PIE-R1005`), but a query it compiles afterwards, and
a bundle it exports from it, carries the new identity although its old modules
built them; such a bundle may differ from the bundle the new code builds, or be
refused by it.

| What changes after `compile_query` or `load_bundle` | A later `execute()` | A later `load_bundle()` |
| --- | --- | --- |
| The values | Each call binds its own. | Not applicable. |
| The access, role, password or premise | Each call uses its own; the server authorizes each attempt. | Not applicable. |
| Database definitions, privileges or rows | Requalified and authorized in each attempt (`PIE-R2007`, `PIE-R3003`). | Not applicable. |
| An installed Pietto `.py` file or the ANTLR runtime, including any upgrade | `PIE-R1005` for every query compiled or loaded before; it works again when the code is restored. | The old records: `PIE-R1005`. The old bytes relabeled with the new compatibility: `PIE-R1008`. |
| The bundle bytes | Nothing for a query already loaded; it keeps what it loaded. | Changed bytes under the old pin: `PIE-R1007` (`PIE-R1008` when the change breaks the bracket nesting that is checked before hashing). |
| The project's source files or contract | Nothing for a query already compiled: it is a snapshot, and the edits take effect with the next `compile_query`. | A new export has another producer and pin; records of two exports mixed together are refused (`PIE-R1007`, `PIE-R1008`). |

## Results

Each `ResultBatch` has the query's result schema: one uniquely labelled field
per selected column, in select order, with the contract's Arrow type and
nullability. Values are checked before their batch is returned. Rows keep the
server's order and duplicates; only an `order by` fixes that order.
`pa.schema(result)` returns this schema before any row, including for an
empty result, without opening the handle. Pass batches rather than a handle to
libraries: a library that accepts an iterable can iterate a handle and thereby
open and consume its attempt.

`batch_rows` and `batch_bytes` bound one batch; `max_rows` and `max_bytes`
bound the whole attempt. All are finite positive integers; their defaults are
256 rows, 1 MiB, 1,048,576 rows and 64 MiB. `max_bytes` includes the route's
qualifying profile and catalog reads plus every delivered batch, including one
you have closed. A batch that would cross a bound is refused whole
(`PIE-R3004`); it is never truncated, and batches already delivered remain
valid. Only `outcome.end == "COMPLETE"` means every row was delivered.

The caller owns a returned batch independently of its handle and attempt. It
may import the batch through PyArrow without a copy; that imported data remains
valid after the `ResultBatch` or its handle closes. Exporting a closed
`ResultBatch` is refused (`PIE-R4002`). Pietto has no call that materializes a
whole result in one object.

The PostgreSQL rows route receives its native result into libpq at the first
`next()`, before Pietto checks or counts a batch. Thus `max_rows` and
`max_bytes` bound delivery, not the native result already received. The
PostgreSQL witness observes four native rows when it delivers one row from the
documented query ordered by `id` with `max_rows=1`, and one native row when the
same ordered query has `limit 1`. Bound the query with `limit` first, then use
the delivery limits.
PyArrow's allocator may retain freed memory, and its import reads its documented
`ARROW_*` resource inputs.

`consume_query.py` sits next to `run_query.py`. Run it in the same way, with the
password on standard input:

```python
import sys

import pyarrow as pa

from pietto.execution import (
    AttemptFailed,
    ExecutionLimits,
    PostgresAccess,
    PostgresDeploymentPremise,
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
access = PostgresAccess(
    host=sys.argv[1],
    port=int(sys.argv[2]),
    database=sys.argv[3],
    user=sys.argv[4],
    password=sys.stdin.readline().rstrip("\n"),
    sslmode=sys.argv[5] if len(sys.argv) > 5 else "require",
)
premise = PostgresDeploymentPremise(schemas=("fixture", "pg_catalog"))


def read_table(limits):
    batches = []
    with execute(
        query, route="postgres_rows", access=access, premise=premise, limits=limits
    ) as result:
        schema = pa.schema(result)
        for batch in result:
            with batch:
                batches.append(pa.record_batch(batch))
    return pa.Table.from_batches(batches, schema=schema), result.outcome


table, outcome = read_table(
    ExecutionLimits(batch_rows=2, max_rows=100, max_bytes=1024 * 1024)
)
print(table.schema)
print(outcome.end, table.num_rows, sorted(table.column("id").to_pylist()))
try:
    read_table(ExecutionLimits(batch_rows=2, max_rows=3))
except AttemptFailed as error:
    print(error.code, error.outcome.end, error.outcome.rows)
```

```text
id: int64 not null
label: string not null
COMPLETE 4 [2, 2, 3, 5]
PIE-R3004 FAILED 2
```

## Connection and trust requirements

### MySQL rows

`mysql_rows` accepts only a query compiled for MySQL 8.4.12 and an explicit
`MySQLAccess` plus `MySQLDeploymentPremise`. It has no fallback to a PostgreSQL
route, cursor API or whole-result materializer.

- **One verified TCP connection profile.** `host` is one hostname or IP address;
  `/...`, `@...` and comma-separated forms are refused before the connector is
  imported. The caller supplies `ca_file`; certificate and hostname verification
  are always enabled, including loopback.
- **Explicit context and premise.** `account` and `roles` are not inferred from
  `user`. Each attempt observes its own data and control sessions, requalifies
  its compiled sources, and treats the schemas declaration as an explicit managed
  deployment premise, not a grant or proof of compliance.
- **Selected dependency and ambient inputs.** Only
  `mysql-connector-python==26.7.0`, its own `mysql.connector.connection` file,
  and `pyarrow==26.0.0` are accepted. A missing selected dependency is
  `PIE-R2001`; a wrong, shadowed or unloadable selected file is `PIE-R2002`.
  `SSLKEYLOGFILE`, `OPENSSL_CONF` and `OPENSSL_MODULES` are refused before the
  private MySQL module imports `ssl`; their values are never read. Earlier
  process imports remain outside that boundary.
- **Connection metadata.** Pietto disables Connector/Python default connection
  attributes and OpenTelemetry context propagation on both data and control
  connections. The prepared binary row protocol and its EOF remain the native
  completion evidence; statement close-send is not a server acknowledgement.

### PostgreSQL ADBC rows

`postgres_adbc` reuses `PostgresAccess` and `PostgresDeploymentPremise`, but
selects exactly `adbc-driver-postgresql==1.12.0`,
`adbc-driver-manager==1.12.0` and `pyarrow==26.0.0`. It uses the same bound
query, `ResultHandle`, `ResultBatch`, schema protocol and `Outcome` as the
other rows routes; it exposes no ADBC connection, reader, URI, driver path or
fallback to `postgres_rows`. Its private bridge creates the route-bound ADBC
premise from the binding's exact ordered sources on every call.

The route refuses `PG*`, `SSLKEYLOGFILE`, `OPENSSL_CONF` and `OPENSSL_MODULES`
before importing its native owner. It uses the documented PostgreSQL TCP SCRAM
profile, including `require_auth=scram-sha-256`; an ADBC service witness is the
acceptance evidence for a successful SCRAM exchange and pre-response rejection
of non-SCRAM methods. The selected Linux driver library is checked as adjacent
to the pinned driver module; Pietto makes no broader transitive-libpq or
platform claim.

### PostgreSQL rows

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
- **Pinned driver and Arrow files.** The imported `psycopg` and `psycopg_binary` must be
  files recorded by the installed `psycopg 3.3.5` and `psycopg-binary 3.3.5`
  distributions, and the implementation psycopg selected must be
  psycopg-binary's own module, whatever it calls itself; a shadowing copy on
  `PYTHONPATH` or in the working directory is refused with `PIE-R2002` before it
  receives any connection value. While `PSYCOPG_IMPL` is unset, psycopg prefers
  a `psycopg_c` module to its binary implementation whenever one can be found:
  an installed psycopg-c, which loads a system libpq, or a copy next to your
  script, which would receive the password. So, with `PSYCOPG_IMPL` unset,
  opening an attempt is refused with `PIE-R2002` if a `psycopg_c` module is
  loaded or can be found; Pietto checks this without importing it, before it
  imports psycopg. To keep psycopg-c installed, set `PSYCOPG_IMPL=binary`:
  psycopg then imports only its binary implementation. This stops accidental
  shadowing, not a deliberately constructed environment, which can run arbitrary
  code anyway. Run scripts with `python -I` to keep the working directory and
  `PYTHONPATH` out of the import path. PyArrow must be the installed
  `pyarrow 26.0.0` distribution's own files: a missing package is `PIE-R2001`,
  and another release or a shadowing copy is `PIE-R2002`, before connecting.
- **Code identity.** Each compile, bundle load and attempt identifies the
  installed Pietto and ANTLR runtime code from the installed files at that
  moment; restart a running process after they change (see [Repeated calls and
  invalidation](#repeated-calls-and-invalidation)). The ANTLR version comes from
  the distribution that owns the imported runtime files, so a stray
  `*.dist-info` in the working directory changes neither the identity, nor the
  `compatibility` that `export_bundle` returns, nor what `load_bundle` accepts:
  one whose `RECORD` claims the imported runtime files makes every compile,
  load and attempt refuse with `PIE-R1005` (`COMPILED_CODE_ORIGIN`). Run scripts
  with `python -I`.

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

The following table describes direct execution. The saved-result calls have
their separate workspace, lock and retention effects in
[Effects and resource end](#effects-and-resource-end); they are not covered by
the no-state statement below.

| Call | Database and network | Reads | Threads | Imports |
| --- | --- | --- | --- | --- |
| `import pietto.execution` | none | Python modules; importing `hashlib` lets CPython's OpenSSL read `OPENSSL_CONF` or the system `openssl.cnf` | none | no driver, no PyArrow |
| `compile_query(...)` | none; no schema is read | `pietto.toml`, the selected sources and the contract under the project root; the installed Pietto and ANTLR runtime `.py` files; the ANTLR distribution's `METADATA` and `RECORD` | none | none |
| attributes, `repr()` of the value objects, `CompiledQuery`, `QueryBundle` and an unopened handle | none | none | none | none |
| `export_bundle(...)` | none | none; the bytes are encoded in memory | none | none |
| `load_bundle(...)` | none | the installed Pietto and ANTLR runtime `.py` files and the `METADATA` and `RECORD` of each ANTLR runtime distribution on `sys.path`, for the code identity; no project file, nothing looked up next to the bytes and no environment variable | none | none |
| `execute(...)`, with or without `values` | none | the installed code and ANTLR metadata again, to bind afresh | none | none |
| `pa.schema(result)` | none | the `METADATA` and `RECORD` of pyarrow | none | PyArrow 26.0.0 if it was not already imported |
| entering, or the first `next()` | one TCP connection: TLS with channel binding unless `disable`, SCRAM-SHA-256; `BEGIN ... READ ONLY`; a settings read; catalog reads that qualify the sources, between two reads of the session context | environment variable names and the value of `PSYCOPG_IMPL`; with it unset, whether a `psycopg_c` module is loaded or can be found on the import path (it is not imported); the `METADATA` and `RECORD` of psycopg, psycopg-binary and pyarrow; the type of `/dev/null` | one non-daemon `pietto-deadline-<attempt>` timer | psycopg 3.3.5 and PyArrow 26.0.0 |
| the first `next()` | a read of the session context, the statement timeout (`set_config`), then one prepared statement of at most 10 s; the whole result is read into client memory | none | as above | none |
| each later `next()` | a read of the session context before the batch is returned | none | as above | none |
| the end of the result, or `close()` | a read of the session context, then `COMMIT` at the end, `ROLLBACK` before it; the connection closes | none | the timer is joined (at most 3 s) | none |

Direct compilation, bundle and `execute()` calls write no file and keep no
state between calls. Saved-result calls write only their caller-named local
workspace or reference-sink roots. `help()` runs pydoc, which reads `HOME` and
other variables itself.

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
  truncating it. Use `limit` to bound the native result.
- With `PSYCOPG_IMPL` unset, a psycopg-binary that cannot be loaded makes
  psycopg fall back to its ctypes implementation, which searches for a system
  libpq (running `ldconfig`, then compiler and linker tools found on `PATH`) and
  loads it before Pietto refuses that implementation with `PIE-R2002`;
  `PSYCOPG_IMPL=binary` prevents the fallback.
- `Timestamp` and `UUID` source fields carry meaning only under the qualified
  physical mapping in [Language](language.md#timestamp-and-uuid-source-meaning):
  PostgreSQL `timestamp without time zone(6)` and `uuid`, MySQL `DATETIME(6)`
  and `BINARY(16)`. `compile_query` still refuses a field whose meaning it
  cannot derive, for example one declared through an alias of `Timestamp`
  (`CompileRejected` with status `BLOCKED` and `PIE-B1004`), and a contract
  that declares other storage for it (status `INPUT_REJECTED`); each attempt
  checks the actual catalog types of these columns before the query runs
  (`PIE-R2007`). There is no string, integer, binary, timezone, precision or
  implicit UUID fallback.
- A query whose single-match requirements need runtime enforcement is blocked
  when compiled (`PIE-B1006`), as with `pietto emit-sql --project`.
- Only the literals of a `bind-safe` query can take other values (see
  [Values](#values)); a `preserve` query always runs with the literal values of
  its source.
- A compiled query is a snapshot of the project files `compile_query` read;
  edits take effect with the next `compile_query`, and a bundle keeps the query
  it was exported from.
- A bundle loads only while the installed code has the identity that its
  compatibility names, so every Pietto release needs a new export (or the
  environment that built it); there is no migration between versions. The
  identity is read from the installed files at each call, so restart running
  processes after the installed code changes.
  A bundle or saved-job record made under `0.1.1` can be refused under
  `0.1.2` when that identity differs. The old data is preserved; use its
  matching old environment. Pietto supplies no migration.
- The pin of a bundle is a content identity, not a signature, and protects the
  bytes only when it comes from your own records. There is no signing,
  registry or revocation.
- Bundles with a guard program or a refinement, which `compile_query` does not
  produce, are refused (`PIE-R1004`).
- `cancel()` asks the route's control owner to cancel a running attempt and
  returns `None`; its `Outcome` keeps the observed cancellation, transaction and
  cleanup facts. A deadline and server-side statement limit remain separate, and
  neither bounds a server or network that stops responding.
- The real-database witness of this alpha uses CPython 3.13.13 on Linux x86-64
  and PostgreSQL 18.6 with TLS, channel binding and SCRAM-SHA-256, and the
  loopback `sslmode="disable"` case; other interpreters, platforms, server
  versions and setups are not covered by it.
