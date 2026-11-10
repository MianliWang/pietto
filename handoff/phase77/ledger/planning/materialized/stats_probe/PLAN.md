# S04/S05 raw-stats plan

This prepares `C77-float-stat`, a future raw target observation package. It is
not a Pietto SQL test, emitter proof, database qualification or differential
result.

## Fixed records

For every applicable `(engine, function, case)`, the future driver writes one
JSON record with exact raw SQL, bound parameters, seed, ordinal seed readback,
metadata, warnings and either one one-column row or terminal error. `IN10K`
uses `random.Random(72)`. Int seeds remain JSON integers; Float seeds and raw
results use `float.hex()`, preserving zero sign. Terminal errors retain only
SQLSTATE, errno and exception type.

The output directory must be absent; the driver creates it 0700 and drops its
owned table in `finally`. The resource parent still owns endpoint creation,
engine lock, image identity, SQL mode, time ceiling, container cleanup, raw
receipt and campaign manifest. This driver has no Docker command, default
endpoint or environment credential lookup.

## Raw SQL matrix

| Pietto function | PostgreSQL primitive | MySQL Float primitive | MySQL Int reconnaissance only |
| --- | --- | --- | --- |
| `stddev` | Int: `SQRT(CAST(VAR_SAMP(value) AS double precision))`; Float: `STDDEV_SAMP(value)` | `STDDEV_SAMP(value)` | `STDDEV_SAMP(CAST(value AS DECIMAL(65,0)))` |
| `variance` | Int: `CAST(VAR_SAMP(value) AS double precision)`; Float: `VAR_SAMP(value)` | `VAR_SAMP(value)` | `VAR_SAMP(CAST(value AS DECIMAL(65,0)))` |
| `pvariance` | Int: `CAST(VAR_POP(value) AS double precision)`; Float: `VAR_POP(value)` | `VAR_POP(value)` | `VAR_POP(CAST(value AS DECIMAL(65,0)))` |
| `pstdev` | Int: `SQRT(CAST(VAR_POP(value) AS double precision))`; Float: `STDDEV_POP(value)` | `STDDEV_POP(value)` | `STDDEV_POP(CAST(value AS DECIMAL(65,0)))` |
| `sum` / `avg` | raw `SUM(value)` / `AVG(value)` on Float only | same | not in this probe |

The MySQL Int expressions prove only primitive behavior. Their carrier,
warnings, precision and terminal behavior decide whether an emitter proposal
is possible. `STD`, `STDDEV` and `VARIANCE` never appear because their
sample/population aliases disagree across targets.

## Cell matrix and judge

S04 Int statistics use `I0`, `I1`, `I1N`, `IN`, `I2`, `M8`, `I53`, `I64`,
`IS` and `IN10K`. The exact `Decimal` truth accepts Int variance
only within `epsilon * variance` and deviation only within
`2 * epsilon * deviation`; zero remains exact.

S05 Float statistics and SUM/AVG use `F0`, `FN`, `F1`, `F2`, `F3`, `FZ`,
`FO`, `FL`, `FT`, `FOVER_SUM`, `O1` and `O2`. The existing Float deviation
bound is `4*epsilon*s + 8*n*epsilon*r + 2*sqrt(n*2^-1074)`; variance has its
own `2*s*deviation_bound` rule. Documented tiny Float statistics may underflow
to zero. `O2` statistics must terminate with no rows.

SUM/AVG have no new closeness or ULP tolerance. Empty/all-NULL must be NULL;
successful nonempty results must be finite binary64 and are preserved as bits.
`FOVER_SUM` has separate functions: SUM must terminate with zero rows; AVG may
record either a zero-row terminal or its own finite binary64 observation. Neither
may return infinity, NaN, warning-only conversion or a row after terminal.

## Future `--run` preconditions

The endpoint JSON stays outside the output: PostgreSQL expects `{"dsn":"..."}`;
MySQL expects `mysql.connector.connect` keyword arguments. It is never copied
into a record or error. The future resource parent separately freezes images,
server/session identity, source candidate and emitted Pietto SQL. A raw record
does not close any product reader, compiler or qualification boundary.

Run `stats_probe.py --selfcheck` before a future campaign. It rejects missing
warnings/metadata, bad seed readback, wrong arity, NULL mismatch, NaN, infinity,
out-of-bound statistics and terminal rows. It passed locally on CPython 3.13.13
without a connection.
