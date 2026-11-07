### MySQL single files: constants, `--set` and `now()`

- MySQL single-file emission writes top-level constants and `--set` values
  as PostgreSQL does: each read is its literal, `DATE '...'` or
  `TIMESTAMP '...'` for a `Date` or `Timestamp`, and the SQL is
  byte-identical to the value written in the file. A table or query that
  reads a constant, directly, through a `def` or a relationship or by reading
  such a table or query, now emits; `0.1.10` refused each with PIE-B1000.
  The statements of the two-database differential that checked constants
  before `0.1.10` are emitted byte for byte.
- `now()` in a MySQL single file is `UTC_TIMESTAMP(6)`, and `date_of(now())`
  is `DATE(UTC_TIMESTAMP(6))`: the start of the running statement in UTC with
  microseconds, one value for every read of the statement, whatever the
  session time zone, as on PostgreSQL. A MySQL project still refuses `now()`
  with PIE-B1003 `scalar_call_signature_not_admitted`.
- The [capability page](../capabilities.md) gains a row for `string_agg` and
  splits query header parameters by type: `Bool`, `Int`, `Float` and `Text`
  emit on MySQL projects, and `Decimal(p, s)`, `Date`, `Timestamp` and `UUID`
  are BLOCKED there with PIE-B1003
  `query_parameter_type_not_admitted_on_target`, as in `0.1.10`.

Changed diagnostics (programs refused in `0.1.10`; no accepted program
changes):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1000 | MySQL single file, a table or query that reads a constant | `MySQL SQL emission is not implemented for RelationIR: <name>. MySQL has no top-level constants yet; emit with --dialect postgres` | none: the relation emits, or reports the refusal of another form it holds |
| PIE-B1000 | MySQL single file, a table or query that reads `now()` | `MySQL SQL emission is not implemented for RelationIR: <name>. Unsupported MySQL function call: now` | none: the relation emits, or reports the refusal of another form it holds |
