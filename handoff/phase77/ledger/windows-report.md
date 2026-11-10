# Phase77 S16/S08 Windows recovery

Status: `RECOVERED_CANDIDATES_NOT_READY`.

Both candidates are isolated shared local clones at
`f8ccd2c44a2d9adf431a496bd9bbae037783176f`. Neither candidate is canonical,
staged, committed, published, or a Gate 2 result.

## Evidence and edits

| Candidate | Auditable source | Restored files | Binary diff SHA-256 |
| --- | --- | --- | --- |
| `candidates/s16` | `records/editor_contract_draft.jsonl`: calls `call_3ebb5e9cca644e50bb07203c792abbc4`, plus the S16 source edits at source lines 1072, 1104, 1207 and 1228 | `project_sql_emission_pure_boundary.py`, `project_sql_emission_windows.py`, `test_execution_compiled_families.py`, `test_harness_sql_emission_portability.py`, `test_sql_project_scalar_expressions.py` | `37a0f165df2194c809899eeea0b905cbc255286eaa08f85060924325c5de71b0` |
| `candidates/s08` | `records/p77_aggregate_windows.jsonl`: final construction/pure repair and source lines 604--607 in the original session | `project_compiled_verification.py`, `project_sql_emission_pure_boundary.py`, `project_sql_emission_verification.py`, `project_sql_emission_windows.py`, `test_execution_compiled_families.py`, `test_sql_windows.py` | `da0ee136c738222bb7e42c8195b2a6fde5d38f4c675586e8f3cd85963f92ee56` |

S16 restores target-separated pure token admission: PostgreSQL accepts only
`E'\\ooo'`; MySQL accepts only `X'hex'`. Empty `X''` has width zero, while a
NUL byte remains rejected. Its authored and compiled-replay tests are present.

S08 restores only MySQL direct `count`, `min`, and `max` aggregate windows;
`sum` and `avg` remain target-gated. The pure reader independently derives
the direct source/aggregate stage, carrier, result realization, and NULL law.
The final actual repair refuses a computed named `let` at construction, while
the pure and compiled forgery tests retain their independent negatives.

The complete candidate diffs are the live, reviewable outputs of:

```text
git -C .cache/phase77-recovery/candidates/s16 diff --binary HEAD
git -C .cache/phase77-recovery/candidates/s08 diff --binary HEAD
```

## Performed checks

`git diff --check` passed for both candidates. The following minimal syntax
check passed with `UV_PYTHON=3.13.13` and the existing offline `.venv`:

```text
.venv/bin/python -m py_compile <all 11 restored production and test modules>
```

## Remaining gaps

No pytest, Ruff, package/generated check, database qualification, full Gate 2,
commit, or publication was run. S08 therefore has no MySQL runtime evidence;
S16 has no target-runtime qualification. These candidates must not be called
ready or accepted on the basis of this recovery.
