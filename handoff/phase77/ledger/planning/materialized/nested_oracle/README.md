# Phase77 MySQL nested raw preparation

This directory is deliberately outside the repository and is **not** S21
implementation. It has no database client, no Pietto imports, no SQL execution,
no package download and no claim that MySQL nested results are supported.

`p77_nested_raw_oracle.py` supplies independent small expected logical
witnesses and a PG `count + aligned arrays` control for each witness.
`p77_nested_raw_hook.py` writes a plan/fixture, then validates an observation
recorded by a future isolated raw experiment. The SQL in every accepted record
must be labelled `RAW_CANDIDATE_NOT_PIETTO_EMITTED`; it is evidence input, not
an emission artifact.

## Commands

```bash
python3 p77_nested_raw_hook.py --self-check
python3 p77_nested_raw_hook.py --write-plan plan.json
python3 p77_nested_raw_hook.py --write-fixture observations.template.json
python3 p77_nested_raw_hook.py --verify observations.json
```

The self-check is pure standard-library code. It first accepts the fixture, then
proves refusal for Float `-0.0` sign loss, Int64 numeric coercion, Decimal
exponent spelling, invalid Date, UUID case normalization, unique-order swap,
empty/absent conflation, count drift and unknown envelope key.

A future raw probe replaces only `raw_candidate_sql` and raw-result fields in
the fixture. It must record SQL bytes, typed parameters, driver/image identity,
metadata and raw result separately in its evidence store. It must not present
the placeholder or candidate SQL as Pietto-emitted SQL.

The tie case deliberately permits two equal-key orders. The unique-order case
does not: it is the concrete check that the candidate window/JSON aggregation
keeps its claimed order. No client-side sorting is allowed.

