# Phase77 recovery planning inputs

Status: `HISTORICAL_PREPARATION_ONLY` — reconstructed from the recorded source
patches on 2026-11-09. Nothing here is a Gate 1 decision, implementation
authority, database observation, qualification, publication, or runtime proof.

This directory is deliberately separate from canonical planning and candidates.
The recovery inputs retain their original uncertainty rather than converting a
previous proposal into a current decision.

## Restored planning documents

* `duckdb-gate1-proposal.md` and `duckdb-gate1-review.md` preserve the concrete
  Phase79 first-vertical proposal and the review that found four owner choices
  still open.
* `phase80-interop-api-contract.md` preserves the smallest proposed five-adapter
  API/type-loss envelope. It is an API candidate, not a public contract.
* `mysql-nested-envelope-pending.md` preserves the MySQL nested transport seam.
  Its wire/JSON choice is explicitly `OWNER_DECISION_PENDING`.

## Raw-prep recovery map

`raw-prep-manifest.json` identifies the exact source record and original patch
line for the independently prepared, non-DB inputs:

* S09 typed-parameter qualification;
* S13 ordered-value witnesses;
* S15 division pure judge;
* Float equivalence;
* nested logical oracle; and
* statistics probe.

`recover_patch_bundles.py` is a standard-library, fail-closed extractor for
the original patch strings. It only writes beneath an explicit output directory
inside this planning directory, and rejects a malformed/ambiguous record. It
is supplied for a future authorized replay; it has not been executed here.

`raw_oracles.py` contains only record-shape checks used before a later,
separately authorized campaign can consume a captured observation. It opens no
database, network connection, package, driver, or Pietto runtime.

## Known gaps

There is no recovered database output, driver metadata, emitted SQL, timing
sample, package pin, selected owner choice, or Gate result. The patch records
are sufficient to recover the preparation artifacts, but not to manufacture
any of those missing evidence layers.

The extractor has now materialized every available literal patch under
`materialized/`; see `MATERIALIZATION-GAPS.md` and
`materialized/materialization-report.json` for updates whose recorded hunk base
is absent. The materialized files are historical inputs, not current source.
