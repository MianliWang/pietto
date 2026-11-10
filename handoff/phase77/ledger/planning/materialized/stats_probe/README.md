# Phase77 S04/S05 raw statistics probe

Status: `PRE_RUN / NOT_PIETTO_QUALIFIED`. This directory is an owned, stdlib-only
preparation for one later raw PostgreSQL/MySQL campaign. It does not start
Docker, discover an endpoint, compile Pietto, or assert that a raw SQL result
opens an emitter or reader path.

`stats_probe.py --selfcheck` validates the static plan and judge without a
database. A future owner supplies `--run --endpoint ENDPOINT.json --table NAME`
only after the resource parent freezes the image, endpoint, session settings,
owned table lifetime and engine lock. The driver requires an explicit endpoint;
it has no default DSN, environment lookup, container command or network path.

Every `(engine, function, case)` record holds the exact SQL, bound parameters,
seed readback, normalized column metadata, warnings and either one result row
or a terminal error. Float seeds and observed values use `float.hex()`; Int
seeds remain decimal integers. The judge rejects missing metadata or warnings,
non-singleton rows, NULL shape mistakes, NaN/infinity, unexpected warning-only
conversion, and terminal errors that claim delivered rows.

The Int statistics oracle uses exact `Decimal` arithmetic and the existing
language bounds: `epsilon * variance` and `2 * epsilon * deviation`. The Float
statistics oracle computes its independent binary64-image truth with `Decimal`
and applies the existing magnitude/count/spread bounds separately for deviation
and variance. `SUM`/`AVG` use no invented epsilon: successful finite values are
recorded by exact bits only, while empty/all-null and terminal observations are
judged by their declared shape. Overflow SUM and AVG have separate dispositions.

The raw plan contains `VAR_SAMP(CAST(value AS DECIMAL(65,0)))` for MySQL Int
statistics only as reconnaissance. It is not an approved Pietto lowering.
