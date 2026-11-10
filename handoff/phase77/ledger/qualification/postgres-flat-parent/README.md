# P77 flat PostgreSQL parent

Status: `PREPARED_NOT_STARTED`.

This parent binds the frozen B2 candidate tree
`9e688596fdb52667531b120d10ace4d836c426f2`, its candidate wheel, the
existing flat qualification compiler/judge, and the reviewed PostgreSQL relay.
It has no database entry point yet.

The future native runner must consume each supplied plan's real public source,
configuration, contract, emitted SQL, fixed values and parameter uses. It must
create only the plan's trusted DDL and typed seed, run the candidate's public
`compile_query`/`execute` PostgreSQL rows route, preserve actual SQL, binds,
driver metadata, raw rows, decoded Arrow/results, EOF and cleanup, then pass
those records to an independent common judge. A failed case keeps raw output
and server logs before any verdict.

The Decimal and S16 B2 plans remain external inputs. Until they are rebound to
this exact candidate wheel, `preflight.py --self-check` is the only supported
operation. No invocation of this directory starts Docker, a relay or a
database.
