# Required qualification matrix

All rows require separate PostgreSQL and MySQL observations.  A differential

| Case | Raw SQL and typed inputs | Evidence / expected result |
| --- | --- | --- |
| Decimal positive | `CAST(? AS DECIMAL(p,s))`; `Decimal('12.30')`, negative nonzero, zero | exact selected rows and `DECIMAL(p,s)` result metadata; no warning; PG/MySQL differential agrees |
| Decimal limits | `(1,0)`, `(65,30)`, exact maximum magnitude | no rounding; expected accepted result and canonical binding/vector bytes |
| Decimal rejects | excess scale, excess precision, `NaN`, `Infinity` | bind rejection before native allocation; raw SQL never contains the supplied value |
| Date positive/bounds | `CAST(? AS DATE)`; `1000-01-01`, leap day, `9999-12-31` | exact date round trip and no warning |
| Timestamp positive/bounds | `CAST(? AS DATETIME(6))`; microseconds `000001`, `999999`, both civil ends | exact six-digit preservation; source/result session context is `+00:00` |
| Timestamp rejects | aware datetime, out-of-range civil year | bind rejection before prepare |
| UUID native-bytes probe | `CAST(? AS BINARY(16))`; nil, high-bit UUID, ordinary UUID, NULL | raw packet/value trace of `UUID.bytes`, standard-order byte oracle, metadata, rows, and no warning; prerequisite, not a capability test |
| Nullable typed values | each tag with `None` on a nullable header and a repeated read | two `?` occurrences yield two bound NULL argument positions; expected three-valued SQL rows |
| Repeated occurrence | same parameter read in SELECT and WHERE, then in reversed textual order | exact SQL-order `parameter_uses`, argument order, metadata arity, and result; never an arbitrary winner |
| Injection control | invalid typed string first; then valid Text control with quotes/comment/placeholder syntax | invalid input rejected pre-prepare; valid Text stays one bound datum; raw SQL SHA-256, canonical SQL emission bytes, `?` count, and metadata are unchanged across values |
| Compiled/pure closure | source emission, compiled template, loaded compiled template, pure reader | identical `parameter_physical`, Decimal `(p,s)`, Timestamp precision, use order/multiplicity, blockers, canonical bytes, and binding-template-byte check |

For every accepted live row, preserve exactly these artifacts: source and

The MySQL context already requires `@@time_zone == '+00:00'`; the candidate
