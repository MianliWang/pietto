# Phase77 qualification recovery

## Recovered material

- `qualification/commonflat/judge.py` was rebuilt from the qualification-repair
  record. Its SHA-256 is
  `6641e9180c6d54b903b2140f46a89453999fb3d69820ea0ab9ac36eaa4960bf1`.
- `qualification/commonflat/flat_qualification.py`,
  `qualification/decimal/build_decimal_plan.py`, and
  `qualification/s16/build_s16_plan.py` were replayed from their recorded
  patch calls. Each emits or validates a closure over its full plan envelope.
- The S16 recovered source retains the strict-v2 case envelope: exact plan
  closure, case inventory, source/config/contract/public artifact, SQL, fixed
  values and parameter occurrences, DDL/typed seed, native metadata, warnings,
  terminal record, and cleanup record. Its Decimal peer calculates the 65/30
  case with `Decimal` and the recorded scale-30 oracle path.
- `qualification/postgres-flat-parent/preflight.py` is recovered as a
  database-free preflight skeleton. `runner.py` is recovered as source only.

## Evidence and limits

`qualification/recovery-evidence.json` is the ordered replay ledger. It
records source session, original line/ordinal, call ID, operation, and target
file. Key source calls are:

- Common judge replacement: line 173, `call_6942c086c44341d8a6708817dc58dced`;
  final replacement: line 190, `call_ef6bdb453e4941338dfea181cb037788`.
- Common-flat materializer replacement: line 216,
  `call_056f2ae7040a4758898b2ed7b8bf05d1`; B3 manifest binding update: line
  611, `call_97630a54e2cb47c6b9f5efd0566e936a`.
- Decimal builder creation: line 308,
  `call_f46f6032d12f45de990cc76da706aa2f`; closure repair: line 1086,
  `call_97801eb9e93f49b680d1d0b0e930a5e6`.
- S16 builder creation: line 1355,
  `call_97922662d01348c18393bb803736bd15`; strict closure addition: line
  1880, `call_34f7da25df104ee5a7a39599dabfc049`.
- PostgreSQL parent skeleton: line 3171,
  `call_c890f494bee7412aa9b0c224274e636b`; source-only runner: line 145,
  `call_c5483f5a18bd4223ad0e0ac078d7545b`.

The old `p77_flat_pg_runner` record is truncated at its final original line
157 (`records/gaps.json`). `runner.py` also names absent `common_judge.py` and
`worker.py`. It is therefore not an actual PostgreSQL runner, and no native
receipt, plan identity, candidate tree, wheel identity, or success result has
been recreated.

Three historical update calls did not apply during deterministic replay:
S16 line 1729 `call_5eb289897da24731aa6010f87822dfd6`, Decimal line 551
`call_724f2b5da570401992f91817b4538aa7`, and an obsolete pre-replacement
common-flat update sequence. Later closure-bearing updates were replayed; the
ledger retains each miss rather than choosing a guessed hunk. Historical JSON
plans were not regenerated: without a newly bound candidate they would be
historical input only.

## Local check performed

Only syntax compilation was run for the recovered Python files. No database,
network, `pytest`, Gate 2, native runner, or historical shell command was run.
The SHA-256 above was checked after replay.

## Next binding requirement

Use a new candidate to rebuild every plan with `UV_PYTHON=3.13.13` and
`UV_OFFLINE=1`, then bind that candidate's index tree/worktree state and wheel
bytes into fresh closure-bearing plans. The PostgreSQL parent remains blocked
until the missing actual `worker.py` and common-judge inputs are recovered or
re-authored under a new dispatch.
