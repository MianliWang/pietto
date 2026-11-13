### `now()` outputs run; other Timestamp and UUID outputs without a source are refused

A PostgreSQL query can now select `now()` as an output: `execute()` and
`save` run it, and its column is `timestamp[us]` with the civil meaning of a
`Timestamp` source field, which the statement's UTC start has, beside
`Timestamp` source fields or without any. Such an output is a SELECT item
whose whole value is the call, also as a `def` argument or in a collected
`let`, or a column that another relation selected from it, which keeps that
meaning wherever a source field's is kept, such as through `max`, whose
result admits NULL. The 0.1.10 notes said that `execute()` and `save()`
accept a query that reads `now()`; for `now()` selected as an output that
never held.

A `Timestamp` or `UUID` parameter, or another expression over `now()` such
as `coalesce(now(), now())`, selected as an output, also in a relation that
`collect` reads, now gets `PIE-R1004` (`detail` `MEANING_OUTPUT`) from
`execute()`, `save`, `save_recoverable` and `relay_live` while they prepare
it, before any workspace access or connection, when the program has no
`Timestamp` or `UUID` source field. Beside such a source field they already
refused it, with the same `detail`, or with `MEANING_UNAVAILABLE` in a
relation that `collect` reads: the output has no meaning that its result
could carry.

Before (measured at `d03d6e4b`, 0.1.11, on Linux with CPython 3.13.13 and
PyArrow 26.0.1, without a database): over a source of `Int` and `Text`
fields, `execute()` of `select: id, seen = now()` returned a handle, and
`pa.schema(result)` raised `HandleMisuse` `PIE-R4004` (`SCHEMA_EXPORT`,
`cause=AttributeError`). Its message blames PyArrow, which was not the cause.
`c = coalesce(now(), now())` and a `Timestamp` or `UUID` parameter output
did the same, and `save` reached the workspace. `relay_live` and
`save_recoverable` refused both `now()` forms with `PIE-R1004`
(`STATEMENT_SNAPSHOT_ENTRY` and `PUBLIC_R2_STATEMENT_SNAPSHOT`) and went on
to their sink and workspace checks for a parameter output. Beside
`Timestamp` source fields all four refused `seen = now()` with `PIE-R1004`
(`MEANING_OUTPUT`).

After: `pa.schema(result)` has `seen: timestamp[us] not null` in both
programs and `save` reaches the workspace; what `relay_live` and
`save_recoverable` do with `seen = now()` is in the section on their `now()`
reads below. The other outputs get `MEANING_OUTPUT` from all four, before
the `PIE-R1002` of a deployment premise that names the wrong schema.

`date_of(now())` and a WHERE comparison with `now()` run as before, and a
MySQL project still refuses `now()` with `PIE-B1003`
(`scalar_call_signature_not_admitted`) outside the position of "MySQL
project `lpad` and `now()`". No PIE code or detail is added; SQL output, CLI
JSON v1, project JSON v2, saved-result formats and the format and records of
compiled bundles are unchanged.
