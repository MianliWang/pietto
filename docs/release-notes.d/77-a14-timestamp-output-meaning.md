### Timestamp and UUID outputs without a source meaning

A PostgreSQL query that selects `now()`, or a `Timestamp` or `UUID`
parameter, as an output now gets `PIE-R1004` (`detail` `MEANING_OUTPUT`)
from `execute()`, `save`, `save_recoverable` and `relay_live` while they
prepare it, before any workspace access or connection, also when the program
has no `Timestamp` or `UUID` source field. Beside such a source field they
already refused it this way. The output has no source meaning that its
result could carry. A column of a relation that `collect` reads is such an
output too.

Before (measured at `4ef90859` on Linux with CPython 3.13.13 and PyArrow
26.0.1, without a database): over a source of `Int` and `Text` fields,
`execute()` of `select: id, seen = now()` returned a handle, and
`pa.schema(result)` raised `HandleMisuse` `PIE-R4004` (`SCHEMA_EXPORT`,
`cause=AttributeError`). Its message blames PyArrow, which was not the cause.
`seen = now()` in a collected relation, and a `Timestamp` or `UUID`
parameter output, did the same. `save` reached the workspace, and
`relay_live` and `save_recoverable` refused with `PIE-R1004`
(`STATEMENT_SNAPSHOT_ENTRY` and `PUBLIC_R2_STATEMENT_SNAPSHOT`). After: all
four refuse with `PIE-R1004` (`MEANING_OUTPUT`), which now comes before
those two refusals and before the `PIE-R1002` of a deployment premise that
names the wrong schema.

The refusal of `now()` as an output is transitional: a later slice is to
give it a `Timestamp` meaning of its own and let it run. A `Timestamp` or
`UUID` parameter output stays refused. `date_of(now())` and a WHERE
comparison with `now()` run as before. No PIE code is added, and SQL output,
JSON documents and saved-result formats are unchanged.
