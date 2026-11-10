# Phase77 dependency-maintenance recovery

Status: `RESTORATION_CANDIDATE_NOT_READY`.

## Baseline and scope

The recovery clone is `candidates/maintenance`, detached at
`f8ccd2c44a2d9adf431a496bd9bbae037783176f`. It is the sole modified
candidate tree. The canonical checkout was only read.

Recovered source edits retarget current package and runtime identity readers to
PyArrow `26.0.1` and Psycopg/Psycopg-binary `3.3.8`: `pyproject.toml`, the
PostgreSQL and Arrow/ADBC dependency gates, package-smoke expectation,
installation and target-conformance readers, wheelhouse filenames, and their
direct assertions. Historical recovery identities and historical qualification
documents remain unchanged.

## Source provenance

The recovery used only extracted `response_item` tool calls and their outputs:

| Source record | Original session line and call | Used evidence |
| --- | --- | --- |
| `records/arrow_update.jsonl` | line 195, `call_3f2f513aa604497b92bedf76e7664083` | reviewed PyArrow current-reader edits |
| `records/psycopg_candidate.jsonl` | line 249, `call_8843d259050c4392bd5b49604985cbc5` | reviewed Psycopg current-reader edits |
| `records/maintenance_integration.jsonl` | line 574, `call_abdd40d880144721974e9b71cf111239` | integrated candidate path inventory and old-version exclusions |

## Lock reconstruction

The archived target states that `uv.lock` revision 5 changes only the Pietto
metadata and the PyArrow, Psycopg and Psycopg-binary distributions. The
expected historical full-patch SHA-256 is
`7345ddec240b89308f20867bfbcc9abf6f9cd7c49498b641f95df142cf62da2c`.

The exact lock artifact was not present in the recovered source records or the
local object search. Under the continuing authorization, the resolver fetched
only official fixed-package metadata into `candidates/maintenance/.uv-recovery-cache`.
It updated PyArrow, Psycopg and Psycopg-binary, plus Pietto's corresponding
metadata; `UV_PYTHON=3.13.13 UV_OFFLINE=1 uv lock --check` then passed. No
other package version changed.

The restoration diff SHA-256 is
`548e72276b20c2bff3bb0613a527ef230fb9095942b562dca32a6150da12e1cc`;
it does not match the expected historical SHA and is a fresh restoration
candidate requiring focused checks before any seal, build, publication, or
execution qualification.

The difference from the historical patch is expected: its exact untracked
patch artifact was lost, while this candidate regenerated the three official
distribution records and restored each current reader from the reviewed source
calls. It also states the older 3.3.5/26.0.0 native evidence explicitly rather
than assigning that evidence to the new pins.

The restored lock itself is exact to the retained recovery identity:
`b2cc96b25b0b9f2225c4529f0123ae869cd804af0578b4f83c931a15aa893064`.

No historical test, package-smoke, native-database, Gate 2, CI, build, commit,
or publication result is claimed as newly run or as raw recovery evidence.
