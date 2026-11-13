### Results wider than one batch

`execute()`, `save`, `save_recoverable` and `relay_live` refuse a query whose
result needs more than the 64 Arrow fields of one batch with `PIE-R1004`
(`detail` `LIMIT`) while they prepare it, before any workspace access or
connection. A collected field counts once for itself and once for each of its
child fields. `compile_query`, `export_bundle` and `load_bundle` still accept
such a query.

Before (measured at `864411cb` on Linux with CPython 3.13.13 and PyArrow
26.0.1, without a database): a `table` of 65 columns compiled, exported and
loaded, `execute()` returned a handle and `pa.schema(result)` had 65 fields,
and the attempt's batch step refused one row with `PIE-R3004` (`detail`
`LIMIT`), which names row and byte limits that a caller can change but not
this one. Read from that code, without a database run: the attempt refused
only after its statement had run, an empty result completed with no rows, and
a saved empty result could not be read. After: the same `execute()` raises
`RequestRejected` `PIE-R1004` and nothing connects, so an empty result of such
a query is refused too.

The check runs after the code identity check and before the premise, access,
collection-route and R2 checks, so a request of more than 64 fields that one
of those also refuses now gets `PIE-R1004` (`LIMIT`) first. Measured at
`864411cb` and after: 65 columns with a premise that does not cover their
source went from `PIE-R1002` to it, and a collected field with 64 child
fields went from `PIE-R1003` (`COLLECTION_ROUTE`) on `postgres_adbc` and from
`PIE-R1004` (`COLLECTION_ENTRY`) in `relay_live` to it. No PIE code is added;
queries of at most 64 fields, SQL output and saved-result formats are
unchanged.
