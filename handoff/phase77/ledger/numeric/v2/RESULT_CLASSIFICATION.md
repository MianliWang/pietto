# Phase77 S01/S02 raw result classification

This template consumes one complete receipt from the frozen raw plan. It does
not declare a Pietto form open, change an emitted statement, or replace a
two-target product oracle.

The prior PostgreSQL R3 receipt is not such a receipt: it has the old v1 plan
identity, preserves the literal `safe_unary` observation only, and lacks the
failed column terminal. It remains historical evidence of that runner defect,
not evidence for either S01 result class.

## Receipt gate

Classify a run `UNQUALIFIED_RECEIPT` unless all of these match first:

1. Candidate base/patch, wheel, lock, Python distribution origins, plan SHA,
   target version, image/config identity and relay contract are exact.
2. The endpoint is the recorded loopback listener for the owned
   `pietto_numeric_probe` role/database, never a public maintenance role or
   database.
3. The ordered physical seed, `SHOW COLUMNS`/PostgreSQL catalog rows and both
   readbacks equal the frozen plan.
4. Every observed version, setup, seed, catalog, readback and probe record has
   one complete terminal before any oracle judgment: a successful statement has metadata,
   rows and a successful warnings receipt; an error has an explicit native
   terminal, empty rows, null metadata and a successful warnings receipt.
5. Relay close/reap, no-network route proof and container cleanup are present.

Any missing or mismatched item is a failure of the experiment receipt, not a
negative result for a language form.

## S01 checked Int arithmetic

| Primitive result | Classification | Product consequence |
| --- | --- | --- |
| Physical signed-column and prepared safe cells have exact values, `NULL` propagation, signed carrier metadata and no warning. | `S01_SAFE_PRIMITIVE_MATCHED` | Necessary evidence only. |
| Physical signed-column/prepared overflow gives native MySQL errno `1690`, SQLSTATE `22003`, no row, no warning-only conversion, and no unsigned/Decimal/clamped value. | `S01_NATIVE_OVERFLOW_MATCHED` | Necessary target-check evidence; retain the native terminal, do not rewrite it as PostgreSQL text. |
| `MIN_INT * 1` returns exact signed minimum with the same receipt shape. | `S01_MIN_TIMES_ONE_MATCHED` | Covers this operation's special boundary. |
| `MIN_INT * 1` raises a complete native terminal. | `S01_MIN_TIMES_ONE_TARGET_LIMIT` | Preserve the observation; do not infer that other operations are safe or open S01. |
| Literal/mixed-cast route differs, emits a warning or changes carrier. | `S01_LITERAL_OR_CAST_OBSERVATION` | Keep as engine observation only. It cannot reject or admit the signed-column product route by itself. |
| Any required column/prepared safe or overflow control differs from the table. | `S01_PRIMITIVE_MISMATCH` | Keep the current Pietto refusal for the affected family. |

Only after the matched rows are paired with candidate-emitted Pietto SQL,
compiled/pure verification and reader evidence may implementation extend
`_target_checked_int` and its independent target checker. The minimal possible
change stays in those shared gates; no new syntax, IR carrier or decoder is
licensed. A target terminal that cannot preserve the existing observable
boundary is a user-facing contract question, not an emitter fallback.

## S02 SUM(Int)

| Raw form | Classification | Product consequence |
| --- | --- | --- |
| `SUM(value)` reports exact Decimal values. | `S02_RAW_DECIMAL_OBSERVATION` | Never an `Int` result. |
| `CAST(SUM(value) AS SIGNED)` clamps, warns, changes carrier or errors. | `S02_CAST_OBSERVATION` | Never a selected lowering merely because in-range rows look correct. |
| Guarded SUM returns signed `Int` values for empty/all-NULL/safe/min/max, including grouped key/value rows, with no warning. | `S02_GUARD_SAFE_MATCHED` | Necessary evidence only. |
| Guarded SUM over each positive/negative global/group overflow emits the native terminal with no delivered row. | `S02_GUARD_OVERFLOW_MATCHED` | Necessary evidence only. |
| The guard errors on an unselected safe branch, folds an overflow branch, returns Decimal/unsigned/clamp, changes a group shape or returns a warning. | `S02_GUARD_MISMATCH` | Preserve the raw result and retain refusal. |

The only candidate lowering after `S02_GUARD_SAFE_MATCHED` and
`S02_GUARD_OVERFLOW_MATCHED` is the recorded guarded expression. It must still
be reproduced from emitted Pietto SQL and close aggregate realization,
verification, pure, compiled and result-reader consumers. If no guard matches,
the SUM strategy remains an architecture decision; widening `Int` to Decimal
is not a repair.

## Result terminals

The run report ends in exactly one of `UNQUALIFIED_RECEIPT`,
`PRIMITIVE_OBSERVATION_ONLY`, `PRIMITIVE_MISMATCH`, or
`CANDIDATE_EMISSION_EXPERIMENT_READY`. The last terminal only means that a
later emitted-product experiment is justified. It is never `S01_OPEN`,
`S02_OPEN`, Gate 2, CI, release or package qualification.
