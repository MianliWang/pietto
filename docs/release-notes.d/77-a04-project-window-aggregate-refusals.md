### Project aggregate windows keep their argument refusals

A selected aggregate window in an explicit-module project, over the input
rows, JOIN rows or grouped rows, whose argument nests an aggregate
(PIE-S2311) or is refused by the aggregate argument rule (PIE-S2315) now
reports that error where a single file reports it, instead of crashing:
`sum(count()) window(order by id)` reports PIE-S2311
`Nested aggregate count() is not supported` at the inner call, and
`sum(None) window(order by id)` reports PIE-S2315
`Aggregate function sum requires a direct field argument; expression
arguments are not supported yet` at the call.

| Command | Before (`0.1.10` and until this fix) | After |
| --- | --- | --- |
| `pietto check --project` | Python traceback, `ValueError: Window diagnostics must retain exact analyzer source evidence.` | the PIE-S2311 or PIE-S2315 error, exit 1 |
| `pietto explain --project` | `project error: project_resource: Project relation columns are unavailable.` | the same error |
| `pietto emit-sql --project` | `INPUT_REJECTED` with `emission_selector` `Project planning roots are unavailable.` | `BLOCKED` with the same error |
| `pietto lsp` with the project in `projectRoots` | `project error: project_root: Project root could not be pinned.` at `pietto.toml` | the same error at the call |

A window in a hidden QUALIFY already reported these errors. No code is new,
and the CLI JSON, project JSON and relation-column formats are unchanged.
