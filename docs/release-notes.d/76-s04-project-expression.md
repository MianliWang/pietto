### Project expression emission

- PostgreSQL project emission now supports finite `Float % Float` with an
  exact binary64 truncating-quotient remainder lowering. PostgreSQL single
  files and MySQL still reject Float `%`; Decimal and mixed numeric remainder
  remain unsupported.
- PostgreSQL project `lag` and `lead` accept static Text literal defaults,
  preserving UTF-8 text, C collation and the maximum result character width.
- PostgreSQL project `Int / Int`, `Float / Float` and `Int % Int` now emit;
  a zero divisor remains a target error instead of becoming MySQL NULL.

### Changed diagnostics

- PostgreSQL project forms previously blocked with
  `PIE-B1003 binary_operator_not_admitted` can emit for the supported E5
  operators above. MySQL Float `%` remains deterministically refused.

#### Compiled compatibility

This is the one Phase76 compiled schema and occurrence change: version
marks become `(8, 1, 8, 1)`. Recompile bundles and saved jobs from `0.1.10`;
the loader rejects their earlier marks with a typed failure. This does not
request rerunning a database query or migrating saved result data; result
reading keeps its separate existing contract.
