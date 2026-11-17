### MySQL project `Float` arithmetic in E4's narrow cell

- `emit-sql --project` now emits a MySQL `Float` `+`, `-` or `*` of a field
  and a literal, and the unary `-` of a field, in one cell (MC.04): one
  operand is a nullable or non-null `DOUBLE` field of a source declared in
  the query's own module, read by name (`x` or `rows.x`), and the other, for
  `+`, `-` and `*`, a `Float` literal under one `-` at most, in either order,
  such as `x * 2.0`, `-2.0 * x` or `y + -0.0`. Each operand and the whole
  operation may also be written in parentheses (`(x) * (2.0)`,
  `y * -(2.0)`) or through a `def` call that inlines to it, a literal
  argument included (`x * two()`, `mul(x, 2.0)`, `same(-x)`). The operation
  is the whole value of a SELECT item of the `query` or `table` that is
  emitted, and the query reads its source through one WHERE at most and
  holds no `let`, window, JOIN, GROUP BY or aggregate, HAVING, DISTINCT,
  ORDER BY, LIMIT or header parameter. PostgreSQL emitted these statements
  already; its SQL does not change.
- `+` and `-` are written `(a + b)`, the sign `(-a)` and a literal
  `CAST(2.0e0 AS DOUBLE)`. `*` is written under an underflow guard (MC.05),
  `CASE WHEN (x * y) = 0 AND x <> 0 AND y <> 0 THEN
  CAST(9223372036854775807 AS SIGNED) + CAST(1 AS SIGNED) ELSE (x * y) END`,
  with `x` and `y` the two operands in their written order. The values are
  Python's binary64 results, the sign of a zero included, as on PostgreSQL.
  A result outside binary64 fails the statement with error 1690
  (SQLSTATE 22003), and so does a product of two non-zero values that rounds
  to zero, which MySQL alone would return as `0.0`; PostgreSQL fails both
  with SQLSTATE 22003. The `Float` law of the
  [language page](../language.md#float-values) does not change.
- The result is a `my_double` with the domain `finite_float` `binary64`, of
  the nullability PostgreSQL gives it: unknown for `+`, `-` and `*`, the
  field's own for the sign. Each `+`, `-` and `*` requirement carries the
  evidence `{"overflow": "target_checked_binary64_overflow"}`, as on
  PostgreSQL, and a sign none; the guard's tokens have the additive `syntax`
  roles `product_guard_open`, `product_guard_zero`, `product_guard_and`,
  `product_guard_then` and `product_guard_close`
  ([project JSON v2](../spec/project-cli-json-v2.md)).
- Emission derives the cell from the plan, compiled replay from its records
  and the pure boundary from its document; plain verification asks
  emission's function where the cell is and checks its operands by its own
  law. Compiled bundles and live templates replay the same SQL.
- Kept refused, with the blockers they have without this note, object for
  object: two `Float` fields (`x + y`, `x - x`), a nested operation such as
  `(x * 2.0) + 1.0` or `-(-x)`, unary `+`, an `Int` literal, a literal under
  `+` or under two signs, `/`, a header parameter, the operation in a `let`,
  a WHERE comparison, an ORDER BY key or an aggregate argument, and a cell's
  operation in a query with any clause listed above, an imported source, an
  upstream query or a relation alias. Under `bind_safe_literals` a statement
  with a literal, a WHERE's included, stays refused, since its literals are
  bind-safe `?`. A statement still refused reports exactly the blockers it
  has without this note.
- R2 `save_recoverable` and `recover` refuse a MySQL query of these forms
  with PIE-R1004 (`detail` `PUBLIC_R2_UNQUALIFIED_FORM`) before any
  workspace access or connection, as for the other forms that MySQL opened
  after a native qualification (see the
  [R2 boundary](../execution.md#known-limitations)).
- Native evidence: these forms open on MC's E4 qualification, its raw
  primitive stage over MySQL `DOUBLE` and its emitted stage over this
  change's SQL, each on PostgreSQL 18.6 and MySQL 8.4.12 (MC.04, MC.05,
  MC.06).
- Beyond the MySQL cadence under J12 (3): E4's wider positions, a `let`
  carry, a WHERE comparison and an ORDER BY key of such a result, wait for
  the owner's later plan, before the Phase82 freeze (MC.04); every other
  position of PostgreSQL's E4 keeps its refusal, with no target (MC.04,
  MC.10).

Changed diagnostics (programs refused in `0.2.1`; no accepted program
changes; MySQL projects, no message text changed):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | `r = x * 2.0`, `r = 0.1 + y` or another `+`, `-` or `*` of a `DOUBLE` field and a `Float` literal in the cell above | `float_literal_operands_required` at the operation | none: the statement emits |
| PIE-B1003 | `r = -x` of a `DOUBLE` field in the cell above | `unary_sign_requires_int_operand` at the sign | none: the statement emits |
