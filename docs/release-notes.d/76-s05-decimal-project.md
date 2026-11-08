### PostgreSQL Decimal project carriers

- PostgreSQL project emission now supports qualified Decimal plus/minus Int
  and Decimal values of different scales, including typed header parameters
  when the pair changes carrier shape. Its emitted arithmetic has the derived
  `numeric(p,s)` carrier; an already-refused same-shape Decimal parameter pair,
  Decimal literals, Decimal/Float and Decimal division remain refused.
- Direct `sum(Decimal(p,s))` emits a checked `numeric(p+19,s)` result only
  when that carrier fits 65 precision digits and 30 scale digits. A sum outside
  it fails with SQLSTATE 22003 rather than returning a value outside Pietto's
  result carrier. Decimal `avg` remains refused.

### Changed diagnostics

- PostgreSQL project `sum(Decimal(p,s))` forms that previously reported
  `PIE-B1004 decimal_aggregate_range_proof_missing` now emit when their exact
  input and result carrier satisfy the documented E10 bounds. MySQL and all
  out-of-range or unqualified forms retain deterministic refusal.
