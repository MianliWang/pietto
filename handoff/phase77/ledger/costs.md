# Phase77 cumulative-cost recovery

Recovered 2026-11-09. This is a ledger reconstruction, not a validation
receipt or a claim that an unused budget balance has been certified.

> **WITHDRAWN — 2026-11-09.** The former `D<=2,773` / `D headroom>=1,227`
> conclusion is invalid. It excluded whole `maintenance_*`, `arrow_update`,
> and `editor_*` streams by task name, although several contain Phase77
> product work. It is retained below only as an error history and must not be
> used for planning or authorization. The replacement classifies each command
> by its actual workdir/path and exact task turn; mixed or unknown commands
> remain Phase77.

## Authority and units

The applicable authority is D77.02: `C280/F850/D4000/S12` cumulative.  The
definitions inherited from D70.10(5), D71.10, and the retained external
Phase76 ledger are:

- `C`: distinct causal repairs, grouped by root cause rather than edit count.
- `F`: every pytest launch, including failing and interrupted launches.  A
  guard that rejects before pytest starts is not an F launch.
- `D`: outer diagnostic commands; a loop inside one command remains one D.
  Pure waits cost zero.
- `S`: scope repairs.

## Recovered bounds

| Unit | Historical confirmed lower | P77-worker transcript ceiling | Whole-phase ceiling | Interpretation |
| --- | ---: | ---: | ---: | --- |
| C | 2 | — | 280 | Two causal roots are terminal-record confirmed. The missing root-cause grouping means the remaining C usage is unknown, not zero. |
| F | 72 | 73 | 850 | 70 direct P77 pytest launches plus the two B1 launches. The worker ceiling includes the one damaged final record. Root/wrapper launches outside this classification remain unknown. |
| D | 13 | 747 | 4000 | 13 is the prior terminal-ledger lower bound. `747` is an upper bound only for the classified P77 worker streams: 816 extracted inner commands, less 70 direct pytest launches, plus the damaged final record. It is not a whole-Phase77 upper bound. |
| S | 0 | — | 12 | No scope-repair terminal is recovered; this is a lower bound, not a zero-usage assertion. |

The `F=72` lower bound retains both B1 facts: the running `r3` launch and the
separately launched, SIGINT-interrupted `r4` both count.  The transcript does
not support treating the historical root session's 152 shell calls as a
Phase77 total: it contains editor, maintenance, recovery, and other scope.

Consequently no authenticated remaining balance can be claimed.  The useful
finite evidence is narrower: the classified worker streams fit below
`F<=73` and `D<=747`; the complete phase remains `[72,850]` for F and
`[13,4000]` for D before this recovery append.

## Sources and damage boundary

The source records preserve the original `source`, `line`, `call_id`, input,
and output. `costs.json` gives per-record time ranges, record anchors, and
direct-launch counts without copying commands or secrets.

- P77 worker records: 816 extracted `exec_command` calls across the fifteen
  `records/p77_*.jsonl` files. They are distinct from maintenance and editor
  records.
- One final source JSONL line is malformed:
  `p77_flat_pg_runner`, 2026-11-08T23:27:04.576Z,
  `call_f6b908739c334cd88abc536e7cf1153d`. It is one unclassified outer call,
  so it adds at most one to each worker-stream D/F ceiling; it is never filled
  in as zero.
- The 70 direct pytest call IDs are enumerated in `costs.json`; all outcomes,
  including failures/interrupts, count once when launch is evidenced.

## Withdrawn whole-phase D calculation (error history)

The previous `D<=747` is deliberately only a P77-worker-stream ceiling.  A
whole-phase bound has now been computed from every indexed mixed record as
`max(1, tools.exec_command occurrences)` per outer record, then adding the
current child sessions that were absent from the old index.

| Step | D units |
| --- | ---: |
| All indexed records | 5,168 |
| Exclude pure M77 streams | -1,711 |
| Exclude pure editor streams | -1,088 |
| Exclude pure future DuckDB/interop streams | -146 |
| Add malformed P77-flat tail | +1 |
| Add current Phase77-recovery children, root continuation, guardian calls, and active-ledger tail | +549 |
| **Whole Phase77 conservative upper** | **2,773** |

This calculation is withdrawn. It does not establish headroom or an actual
usage figure. The replacement below retains every mixed record on the
Phase77 side until a per-command workdir/path or exact-task-turn exclusion is
proved.

The exclusions are strict task/source exclusions, not keyword guesses:
`maintenance_*`, `arrow_update`, and `psycopg_candidate` are M77;
`editor_*`, `lsp_contract`, and `vscode_scope` are editor; `duckdb_*` and
`interop_gate1` are future dialect/interop work. Each excluded record file and
its first/last call anchors are in `costs.json`.

## Replacement: strict per-command/path D bound

The preceding paragraph is also withdrawn: a record-file or agent name is not
an exclusion. The replacement scans every extracted inner command and excludes
only a command with an explicit non-P77 target path. A command is retained if
it has a Phase77 product path, is mixed, or has no classifiable target.

| Step | D units |
| --- | ---: |
| All indexed records, `max(1, tools.exec_command occurrences)` | 5,168 |
| Strict M77 path exclusions | -244 |
| Strict editor path exclusions | -325 |
| Strict future path exclusions | -6 |
| Malformed P77-flat tail retained | +1 |
| All current recovery child sessions retained | +735 |
| Root continuation after the old-index cutoff retained | +11 |
| **Current whole-Phase77 conservative upper** | **5,340** |

This exceeds `D4000` by 1,340. Therefore there is **no certified D remaining
balance** and the value is not an actual-over-cap assertion. The conservative
classification intentionally retains known mixed product streams, including
the B1/B2/B3 integration, Phase77 numeric, S14/Decimal, S10, and S16 work.

The smallest manual-review frontier that could reduce the bound below the cap
contains ten large mixed groups with 1,428 retained-unknown units. Even if all
ten proved non-P77, 1,340 of those units must be excluded; any P77 result keeps
the phase at or above the cap. The groups, in review order, are
`maintenance_integration` (214), `maintenance_mysql_db` (188),
`editor_implementation` (161), `maintenance_pg_db` (147), `arrow_update`
(136), `vscode_scope` (122), `mysql_numeric_probe` (120), `phase_scope`
(114), `root` (114), and `editor_latency` (112). Their names are only review
handles, never exclusion evidence.

## Recovery append

Recovery is separately recorded and does not reset history. The earlier
child-only snapshot and its `548` Phase77-charged figure are **WITHDRAWN**:
they again excluded current recovery streams by task name. The strict current
inventory retains all 735 child-session units and 11 later root units. No
pytest, database, network, Gate 2, or product validation ran in this cost
reconstruction.
