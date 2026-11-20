### MySQL project `Float` parameter operands and computed GROUP BY keys

- `emit-sql --project` now emits on MySQL, in MC E4B's chain C
  ([E4B's cells](../language.md#mysql-float-wider-cells)), a `Float` header
  parameter as the operand of a `+` or `-` beside a `DOUBLE` field, such as
  `query result(p: Float | None)` with `r = p + x`, `let t = x - p` or
  `where y + p > 1.0`, and as the inner operation of a unary `-`, such as
  `-(x + p)`, in the shapes where two fields or a nesting stand. It is the
  statement's one header parameter, read once as a `CAST(? AS DOUBLE)`, and
  it appears nowhere else in the statement.
- One or two `let` values of narrow operations now emit as GROUP BY keys in
  an S07 form on MySQL, such as `let k = w * 2.0` with `group by k`, `k` and
  `n = count()`, or `let a = w + 1.0` with `group by a, kn, u`, with no
  WHERE and no other `let`. Each key stands for its operation's field
  (E4B's law, item 4): with every key replaced by its field the statement
  must be one of the S07 forms of
  [Float values](../language.md#float-values), so the fields differ and give
  an S07 key set. The `let` value is computed in the first CTE and grouped
  in the next.
- The SQL is PostgreSQL's in MySQL's spelling; values, failures (error
  1690, SQLSTATE 22003), carriers, nullability and evidence are E4's.
  PostgreSQL's SQL does not change, and no field, role or code is added.
  Emission, plain verification and compiled replay each apply the law; the
  pure boundary, whose closed schema holds no header parameter, applies it
  to the computed keys, and S07's cell is re-derived by emission, compiled
  replay and the pure boundary with each computed key's field.
- Kept refused, with the blockers they have without this note, object for
  object: a `*` beside a parameter, whose guard would render the
  parameter's one read three times; a parameter beside an inner operation,
  such as `(x * 2.0) + p`, or in an operation under anything but a `-`, such
  as `(x + p) + 1.0`; a second header parameter, read or not, and a second
  read of the one; an operation with no field, such as `p * 2.0` or
  `(p + 2.0) + x`; a value nullable only through a nullable
  parameter, such as `p + y`; a bare parameter read beside such an
  operation; a parameter in two `let`s or in a computed key; and a computed
  key under a WHERE, beside another `let` or a `count` argument, of two
  fields or a nesting, standing for a field another key reads, after a
  `Text` key or selected after the count.
- R2 `save_recoverable` and `recover` refuse a MySQL query with such a
  parameter with PIE-R1004 (`detail` `PUBLIC_R2_UNQUALIFIED_FORM`), and one
  with an ORDER BY key or a computed key with its earlier PIE-R1004
  `REFINEMENT_COMPARISON_DOMAIN` or `PUBLIC_R2_COMPUTED_GROUP_KEY`, before
  any workspace access or connection (see the
  [R2 boundary](../execution.md#known-limitations)).
- Native evidence: these forms open only on E4B's chain C qualification,
  the parameter ones on a harness that binds a `Float` per `?`, each on
  PostgreSQL 18.6 and MySQL 8.4.12.

Changed diagnostics (programs refused in `0.2.1`; no accepted program
changes; MySQL projects, no message text changed):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | `r = p + x`, `let t = x - p`, `let k = w * 2.0` as a GROUP BY key and the other shapes above | `float_literal_operands_required` at the operation or `let` | none: the statement emits |
| PIE-B1003 | `let k = -w` as a GROUP BY key | `unary_sign_requires_int_operand` at the `let` | none: the statement emits |
