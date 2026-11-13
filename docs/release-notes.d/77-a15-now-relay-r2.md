### `relay_live` and PostgreSQL R2 run queries that read `now()`

`relay_live` now runs a query that reads `now()`. It runs one statement, as
`save` does, so the rows its sink receives hold one `now()` value, and the
`detail` `STATEMENT_SNAPSHOT_ENTRY` of `PIE-R1004` is no longer produced.

On PostgreSQL, on both routes, `save_recoverable` and `recover` now run a
query that reads `now()` where R2 reads it: as the whole value of a SELECT
item, or as a side of a comparison in a SELECT item or in a WHERE built with
`and` and `or`, in any stage. An R2 generation is one statement for
`now()`: `save_recoverable` reads the server's UTC statement time once, in
its own transaction before its first page, records it with the generation,
and every page of that attempt and of each later `recover` binds that value
however much later it runs. `recover` still reads its data in its own later
snapshot, so the suffix it adds can hold rows committed after that time
whose value compares as before it. The generation's extraction
specification records the time as `statement_time`, and `recover` binds it
as a parameter: it is the one value `recover` takes from the workspace
without a fresh value to compare it with. A query that reads `now()` binds
one more placeholder at each read, which counts toward the contract's
`parameters` limit.

A PostgreSQL query that reads `now()` and whose SQL R2 does not read, such
as one with `date_of(now())`, `coalesce(t, now())`, `t <= now() <= u` or
`now() in (t, u)`, or one that also selects `lower(x)`, is still refused with
`PIE-R1004` (`detail` `PUBLIC_R2_STATEMENT_SNAPSHOT`) before any workspace
access or connection. That check is now the last step of R2 preparation, so
a query that reads `now()` and has another R2 refusal, such as
`PUBLIC_R2_COMPUTED_GROUP_KEY` or `REFINEMENT_RESOURCE_LIMIT`, gets that
refusal instead. It renders the bound query, so `recover` makes it only when
its restated values and parameters bind; otherwise it goes on to the
workspace, which refuses it with `PIE-R1009` (`BINDING_VECTOR` when the named
generation exists) without a connection. On
MySQL, `save_recoverable` and `recover` still refuse a query that reads
`now()` with `PUBLIC_R2_STATEMENT_SNAPSHOT` at its former place. That
`detail` now means a query that reads `now()` passed to R2 on MySQL, or on
PostgreSQL one whose SQL R2 does not read.

Before (measured at `d03d6e4b`, 0.1.11, on Linux with CPython 3.13.13,
without a database): over a source of `Int` and `Text` fields, `relay_live`
refused `select: id, seen = now()` and `day = date_of(now())` with
`PIE-R1004` (`STATEMENT_SNAPSHOT_ENTRY`) and `save_recoverable` refused them
with `PIE-R1004` (`PUBLIC_R2_STATEMENT_SNAPSHOT`). Beside `Timestamp` source
fields both refused `where stamp <= now()` and `day = date_of(now())` the
same way. `save_recoverable` refused a query that groups by its own `let`
value and has `where date_of(now()) <= date_of(stamp)` with
`PUBLIC_R2_STATEMENT_SNAPSHOT`, and so did `recover` of a query with a
parameter and `date_of(now())` whose restated parameter did not bind.

After: `relay_live` goes on to its sink checks for all of them (here
`PIE-R1001` `REFERENCE_SINK_ROOT`, as for a query without `now()`).
`save_recoverable` goes on to the workspace for `seen = now()`, with or
without `Timestamp` source fields, and for `where stamp <= now()`, and still
refuses `day = date_of(now())` with `PUBLIC_R2_STATEMENT_SNAPSHOT`. The
grouped query gets `PUBLIC_R2_COMPUTED_GROUP_KEY`, and the restatement that
does not bind goes on to the workspace.

The PostgreSQL native qualification passed on 2026-11-13: run
`now-resume-pg-20261113T163002Z-6b47a88871e31b73ad57ccac`, on PostgreSQL 18.6
over `postgres_rows` and `postgres_adbc`, gave `pass: true` with no reason
against for every cell (R2-0 to R2-4 and the `relay_live` cell), and the run
was accepted. It bound this change as first committed on the `now()` output
change (tree `2520fd61`). D77.50 carries it to the commit that integrates
this change: the experiment's compile record, apart from its record of the
installed code and each form's trust record (the bundle's `compatibility`
and `producer`, which name that code, and its pin, a digest of the bundle
bytes that hold both), the bundles without `compatibility` and `producer`,
and its page record are byte-identical there (sha256, first 16 digits, the
same on both sides: compile record `6324cbe6e6318cf0`, page record
`209c750b3c22d769`). MySQL R2 has no run, and keeps its refusal.

No PIE code or detail is added; emitted SQL, CLI JSON v1, project JSON v2
and the format and records of compiled bundles are unchanged. A generation
that does not read `now()` records the same specification as before.
