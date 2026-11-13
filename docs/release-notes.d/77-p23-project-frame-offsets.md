### Project checks refuse window frame offsets as a single file does

A project `check`, of either schema version, now refuses a ROWS or GROUPS
window frame offset that is not, once `let` names are inlined, a
nonnegative `Int` literal up to 9223372036854775807, such as `"x"`, `-1`,
`1.5` or `9223372036854775808`, in a selected, named or QUALIFY window, a
JOIN window of a schema_version = 2 project included, as a single file does:
PIE-S2104 `Invalid window frame for function first_value: ROWS offsets must
be nonnegative integer literals up to 9223372036854775807` (`GROUPS` for a
GROUPS frame) at the call. A schema_version = 1 project now also checks a
RANGE offset of a QUALIFY window, as a schema_version = 2 project already
did.

Changed diagnostics. A schema_version = 1 project emits no SQL, so its
`check` now refuses a program it passed. `emit-sql --project` checks the
whole project first, so it now refuses such a program with that error in
place of an emission blocker, and also refuses any other object of the same
project, which emitted SQL before.

| Command | Before (`0.1.11`, measured at `a015afcf`) | After |
| --- | --- | --- |
| `pietto check --project` | no error, exit 0 | the PIE-S2104 error, exit 1 |
| `pietto emit-sql --project` of the object with the offset | `BLOCKED` with an emission blocker, such as PIE-B1004 `window_frame_offset_evidence_missing`, PIE-B1002 `window_frame_offset_out_of_signed64_range` above signed64 or, on MySQL, PIE-B1003 `window_frame_groups_approved_non_support_on_mysql`, exit 1 | `BLOCKED` with no blocker and the PIE-S2104 error in `diagnostics`, exit 1 |
| `pietto emit-sql --project` of another object | the SQL, exit 0 | `BLOCKED` with no blocker and the PIE-S2104 error in `diagnostics`, exit 1 |

An offset that reads a `let` binding with an error of its own reports
nothing more. Window count literals above 9223372036854775807 stay refused in
single files only. No diagnostic code is new, the CLI JSON and project JSON
shapes are unchanged, and a project without such an offset emits the same
SQL.
