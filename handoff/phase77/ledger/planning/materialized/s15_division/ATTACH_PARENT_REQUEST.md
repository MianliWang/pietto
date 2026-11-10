# Phase77 S15 — attachable MySQL raw-qualification request

Status: `PREPARED_NOT_STARTED`.  This request owns only a pure receipt judge
and its synthetic self-check in this directory.  It does not change Pietto,
the frozen `/tmp/pietto-p77-numeric-prereg` manifest, its PostgreSQL parent,
or any database resource lifecycle.

## Parent request

Attach one S15 child to the already reviewed, parent-owned MySQL campaign only
after the parent has independently rebound its candidate, image, relay, lock,
endpoint and cleanup authority.  Reuse its existing endpoint/materialization
and raw Connector/Python receipt convention.  Do not add a resource wrapper,
target launcher, driver, or product helper for this child.

The parent supplies one JSON receipt to `s15_pure_judge.py --receipt RECEIPT`.
It must contain the raw cursor metadata, rows, warnings and native error
terminal for every observation; this judge performs no I/O other than reading
that receipt.  Before a target run, invoke:

```sh
UV_PYTHON=3.13.13 UV_OFFLINE=1 UV_NO_SYNC=1 \
  uv run python /tmp/pietto-p77-s15-prep/s15_pure_judge.py --self-check
```

The child uses the exact ordered `SEED` embedded in the judge for both `/` and
`%`, and for all three routes in this order: `literal`, `physical_column`,
`prepared`.  The physical table is `c77_s15_signed_operands`, with nullable,
signed `BIGINT` `left_value`/`right_value`, and its raw `SHOW COLUMNS` plus
ordered readback must be in the receipt.  Literal SQL explicitly casts both
operands to `SIGNED`; prepared SQL binds the same values and explicitly casts
each placeholder to `SIGNED`; physical SQL reads the two physical columns.
Each literal observation also carries its exact `literal_operands` pair; each
physical statement identifies its seeded `ordinal`; prepared parameters equal
that same pair.  The three route records therefore cannot borrow a result from
another seed row.
No Decimal, unsigned, Float or Python/SQL floating-point oracle is allowed.

The fixed cells cover negative dividend/divisor combinations, NULL on both
sides, zero divisor, `INT64_MIN / 1`, `/ 2`, `/ 3`, and `INT64_MIN / -1`; the
same rows cover each remainder.  Expected non-error values use exact integer
truncation toward zero, and `remainder = dividend - quotient * divisor`.

## Receipt terminal rule

Every success has exactly one raw Connector/Python value metadata column,
type-code `8` (BIGINT), no UNSIGNED flag, one row, and a completed raw warning
receipt.  A nonzero safe/null cell must have no warning.  A zero-divisor cell
must succeed with `NULL`; its raw warning list is retained rather than guessed
or normalized.  `INT64_MIN / -1` and `INT64_MIN % -1` require one native error
terminal: no rows, null metadata, completed warning receipt, errno `1690`,
SQLSTATE `22003`, and a nonempty native message.  The judge rejects a warning
retrieval failure, a Decimal/unsigned result, a missing terminal, a reordered
seed, or a changed bind value.

Success is only `S15_RAW_PRIMITIVE_MATCHED_NOT_PRODUCT_QUALIFIED`.  It means
the raw target primitive is worth review; it neither opens S15 nor changes the
current MySQL project refusal.

## Required later candidate-emission evidence

Only after a raw primitive receipt passes review may an implementation candidate
be considered.  That later, separate experiment must compile actual MySQL
project `Int / Int` and `Int % Int` source through
`project_sql_emission_rows.py::resolved_binary_realization`, preserve the
emitted SQL and prepared values verbatim, and pair them with the same ordered
seed, raw metadata/warnings/native terminal, PostgreSQL differential and the
plan/verifier/pure/compiled/result-reader closure.  It must preserve MySQL
NULL-on-zero versus PostgreSQL `22012`; it must not translate MySQL `1690`/
`22003` into a portable `PIE-*` promise.  A raw-plan result or this pure-judge
result alone is not candidate emission, Gate 2, CI, publication or release.
