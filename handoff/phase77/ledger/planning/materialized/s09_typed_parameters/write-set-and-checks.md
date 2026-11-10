# Root/write-set map and preparation checks

## Exact current stop and conflict

1. `project_sql_emission_parameters.HEADER_PHYSICAL["mysql"]` is `{}`.
   `project_sql_emission_ast.realize_rows()` rejects every unsupported typed
   declaration with `PIE-B1003` before collecting an occurrence.
2. `allocate_uses()` is already the sole MySQL multiplicity owner: it gives
   each occurrence `ordinal + 1`; this must remain the parent ordering law.
3. `project_execution_binding_verification.native_arguments()` repeats MySQL
   occurrences, but `native_value()` canonicalizes all four advanced tags to
   text.  This conflicts with a UUID BINARY(16) proposal and must be split by
   target/type only after the raw probe.
4. `project_sql_emission_parameters.anchor_suffix()` supports `pg_numeric`
   storage, while the renderer supplies only `physical_type`.  A MySQL Decimal
   anchor needs the declaration's `(p,s)` propagated into rendering and its
   independent verifier; a mapping-only change cannot be correct.
5. `project_sql_emission_rows.parameter_realization()` is rederived by both
   live and compiled paths.  Its storage/domain fields, the emission verifier,
   compiled lowering, compiled verification, portable schema/reader, and
   binding-vector serialization are all in the closure; none may merely trust
   an emitted string.

## Minimal future write set (only after probe/decision)

| Owner | Future responsibility |
| --- | --- |
| `project_sql_emission_parameters.py` | target carriers, SQL suffix storage contract, target-specific native codec (if selected) |
| `project_sql_emission_rows.py` | carrier realization and Decimal/Timestamp storage facts |
| `project_sql_emission_ast.py`, `project_sql_emission_rendering.py`, `project_sql_emission_verification.py` | ordered occurrence allocation; raw SQL spelling; independent re-derivation |
| `project_compiled_lowering.py`, `project_compiled_verification.py`, `project_completed_semantics.py` | compiled re-derivation and tamper rejection |
| `project_execution_binding_verification.py` | actual MySQL typed native arguments while preserving PG reuse and current wire bytes |
| existing parameter, compiled/pure, and native-prepared test owners | behavior, canonical-byte, metadata/warning, and independent-oracle checks |

Do not add a resource framework, a generic casting abstraction, a new native

## Checks actually performed

- Read the supplied boundary preregistration.
- Inspected the clean target clone and confirmed HEAD
  `f8ccd2c44a2d9adf431a496bd9bbae037783176f` with no status output.
- Inspected the current header carrier, realization, rendering, binding,
  compiled-verification, pure/canonical-byte, native-prepared helper, and
  MySQL UTC context roots listed above.
- Confirmed the target clone has no `.venv`; no `uv` command was run because
  offline environment creation could write the non-owned target clone.  No
  database, download, generated-file action, commit, or candidate/canonical
  modification occurred.

This is static/design evidence only.  It is not a focused-test PASS, a native
