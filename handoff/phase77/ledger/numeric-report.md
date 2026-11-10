# Phase77 raw numeric v2 and PostgreSQL parent R4 recovery

## Recovered status

The original v2 package at `/tmp/pietto-p77-numeric-prereg-r4` is no longer
present. Its recovered source inputs are now in `numeric/v2/`; the manifest
was deterministically regenerated from the recovered probe. The retained
plan/review sessions classify the historical package only as
`READY-for-bounded-raw-experiment`; that is neither an executed raw result,
Pietto support qualification, nor Gate 2 evidence.

The PostgreSQL parent R4 raw directory is also absent. The original parent
session reports one R4 raw primitive observation PASS: `numeric-receipt`
terminal `success`, 119 records, `safe_unary` literal/column/prepared rows
`[-7, -7, NULL]`, parent closure `23 inputs / 13 raw / 4 hook files`, owned
container removal, and relay reaping. This recovery preserves that as a
reported observation only; it does not manufacture the missing receipt or its
119 individual records.

## Frozen v2 boundary recovered from source statements

- Every `safe_unary` route (literal, physical column, prepared) executes the
  same ordered seed program: ordinal `0` is `+`, ordinal `1` is `-`, and
  ordinal `2` is `+`. Thus the reported `[-7, -7, NULL]` is not a claim that
  the three routes use different operators.
- Literal arithmetic is recorded observation and cannot reject physical column
  or prepared routes.
- Finite physical-column and prepared routes are strict controls. MySQL
  `MIN_INT * 1` remains observation.
- The runner appends every actual probe terminal before calling the oracle.
- Exact-manifest comparison and no-DB self-checks were reported historically;
  they were not rerun here.

## PostgreSQL parent lineage and safeguards

| Round | Preserved status | Recoverable detail |
| --- | --- | --- |
| R1 | failure | Hook mode gap; exit 126; Docker did not start. |
| R2 | failure | POSIX `$10/$11` parameter parsing; exit 2; cleanup reported. |
| R3 | failure | 69 partial records, then `safe_unary:column:0` oracle mismatch. Failing column row/metadata were not written and must not be inferred from seed or SQL. |
| R4 | reported raw observation PASS | 119 records and parent closure reported; original raw receipt unavailable. |

Retained source records the causal repairs: explicit `sh` hook entry,
`${10}`/`${11}` POSIX expansion, hex container-ID validation, server-log
capture before cleanup, and exact parent receipt/judge bindings. They remain
historical properties, not reusable runtime material.

## Byte audit and missing-artifact policy

`numeric/byte-provenance.tsv` gives canonical session paths, current SHA-256
values, physical JSONL lines, and tool call IDs. `numeric/source-integrity.json`
ties the restored inputs to those records and marks whether old exact file
bytes survive. Missing raw logs, endpoints, credentials, and private keys are
explicitly marked missing. A future runtime must provision fresh secrets and
endpoints under a newly approved campaign.

No database, network, historical shell command, pytest, or full Gate 2 ran in
this recovery.
