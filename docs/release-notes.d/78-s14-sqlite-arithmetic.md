### SQLite project mode — range-proved `Int` arithmetic (alpha)

SQLite project mode now admits `Int` arithmetic whose range the contract
proves. `+`, `-`, `*`, unary `-` and `abs(x)` over `Int` fields and literals
may appear in `select` and `where`, and all but `abs` also as the argument
of `avg` and `sum` (`check` refuses `abs` there with PIE-S2315), when the
contract's `int_range` bounds keep every result inside signed 64 bits.
SQLite turns an `Int` result outside them into a `REAL` without an error,
so the proof covers every intermediate result and an aggregate's argument
row by row. The bounds are computed operation by operation, each field read
on its own, so `x - x` over the full range is refused although it is 0. See
[SQLite project mode](../spec/sqlite-project-v1.md#compile-refusals).

- A unary `-` before an `Int` literal is written as one signed literal, so
  `-9223372036854775808` is SQLite's `INTEGER` minimum; `abs` is `ABS(x)`,
  and `avg` and `sum` of arithmetic are `AVG(CAST(... AS REAL))` and
  `SUM(...)`.
- A `sum` of arithmetic needs bounds on one side of zero, as a `sum` of a
  field does (PIE-B1004 `sum_int_aggregate_range_proof_missing`).
- New refusal: arithmetic whose bounds leave signed 64 bits, such as `x + 1`
  over the full `int_range` or `abs(x)` over one that holds the minimum, is
  BLOCKED with PIE-B1004 `int_arithmetic_range_proof_missing`. Arithmetic on
  parameters or aggregates, `Float` arithmetic, `/`, `%`, unary `+` and an
  `Int` literal outside signed 64 bits stay PIE-B1003
  `sqlite_expression_not_admitted`, and `count` of arithmetic stays
  `sqlite_aggregate_not_admitted`.

Compatibility: PostgreSQL, MySQL and DuckDB SQL bytes, contracts and
diagnostics are unchanged, and so is the SQL of every SQLite statement that
emitted before. Only SQLite programs that were refused change:

| Code or output | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | `Int` `+`, `-`, `*`, unary `-` or `abs` over `Int` fields and literals in `select` or `where`, or all but `abs` as the argument of `avg` or `sum` | `sqlite_expression_not_admitted`, and `sqlite_aggregate_not_admitted` for the `avg` or `sum` | neither: the statement emits unless a row below or another rule refuses it |
| PIE-B1004 | such arithmetic whose bounds leave signed 64 bits at some result | the PIE-B1003 details above | `int_arithmetic_range_proof_missing` at the first such operation |
| PIE-B1004 | a `sum` of such arithmetic whose bounds, every result inside signed 64 bits, hold values of both signs | the PIE-B1003 details above | `sum_int_aggregate_range_proof_missing` |
| PIE-B1003 | `count` of such arithmetic | `sqlite_expression_not_admitted` and `sqlite_aggregate_not_admitted` | `sqlite_aggregate_not_admitted`, after `int_arithmetic_range_proof_missing` where the bounds leave signed 64 bits |
| suggestion (JSON) and `hint:` (text) | `sqlite_expression_not_admitted` | `use fields, literals, parameters, comparisons of two values of one type, and, or, not and is None; arithmetic, signs, in, ranges, conditionals, casts and function calls are not available on SQLite` | `use fields, literals, parameters, comparisons of two values of one type, and, or, not, is None, and Int +, -, *, unary - and abs of fields and Int literals; Float arithmetic, /, %, arithmetic on parameters or aggregates, in, ranges, conditionals, casts and other function calls are not available on SQLite` |
| suggestion (JSON) and `hint:` (text) | `sqlite_aggregate_not_admitted` | `use count, count_distinct of an Int, Text or Bool field, min or max of an Int or Float field, or avg or sum of an Int field, each over one field of the source` | `use count, count_distinct of an Int, Text or Bool field, min or max of an Int or Float field, or avg or sum of an Int field or of Int arithmetic, each over the fields of the source` |
