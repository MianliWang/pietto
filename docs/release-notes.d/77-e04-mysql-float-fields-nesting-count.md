### MySQL project `Float` arithmetic of two fields, one nesting and `count`

- `emit-sql --project` now emits on MySQL, in MC E4B's chain C
  ([E4B's cells](../language.md#mysql-float-wider-cells)), a `Float` `+`,
  `-` or `*` of two `DOUBLE` fields, such as `x + w` or `x - x`, and one
  level of nesting, an inner such operation as an operand beside a field or
  a `Float` literal, such as `(x * 2.0) + 1.0`, `x * (w + 1.0)` or
  `-(-x)`. Each stands as a whole SELECT item with no WHERE, as one `let`
  value read by the select list or by one ORDER BY key, or compared with a
  `Float` literal in a whole WHERE with no `let`.
- `count` of a nullable narrow operation, or of a `+` or `-` of two fields
  of which one is nullable, now emits on MySQL with no WHERE, ungrouped or
  beside GROUP BY keys that are fields, such as `n = count(x + 1e308)` or
  `group by g` with `n = count(x - w)`, and a narrow one also under a WHERE
  that compares a narrow operation with a `Float` literal, such as
  `where x * 2.0 > 1.0` with `n = count(w * 2.0)`.
- The SQL is PostgreSQL's in MySQL's spelling, each `*` under E4's
  underflow guard with an inner operation written inside it as its own SQL;
  `count` counts in the aggregate CTE. Values, failures (error 1690,
  SQLSTATE 22003), carriers, nullability and evidence are E4's;
  PostgreSQL's SQL does not change, and no field, role or code is added.
- Emission, plain verification, compiled replay and the pure boundary each
  apply E4B's operand law, the field or one-level inner operation beside a
  field or literal, by their own reading of their input.
- Kept refused, with the blockers they have without this note, object for
  object: two fields or a nesting in two `let`s, under a WHERE over its
  `let`, beside or under an operation item or in two ORDER BY keys; two
  levels of nesting, two inner operations and a folded inner operation;
  `count` of a nesting, of a product of two fields, of a non-null value, of
  a `let` name, beside an aggregate other than such a `count` (`count()` or
  `max(y)`; two such `count`s emit), ordered, composed, under a WHERE that
  compares no operation or with two fields under a WHERE, and
  `count_distinct` of an operation; two fields under such a WHERE. Under
  `bind_safe_literals` a statement with a literal outside a `count`
  argument stays refused, since that literal is a bind-safe `?`; a `count`
  argument's literals stay inline under both policies, as on PostgreSQL, so
  `n = count(x + 1.0)` emits under both.
- R2 `save_recoverable` and `recover` refuse a MySQL query of these forms
  with PIE-R1004 (`detail` `PUBLIC_R2_UNQUALIFIED_FORM`) before any
  workspace access or connection, and one with an ORDER BY key with its
  earlier PIE-R1004 `REFINEMENT_COMPARISON_DOMAIN` when they prepare it
  (see the [R2 boundary](../execution.md#known-limitations)).
- Native evidence: these forms open only on E4B's chain C qualification,
  its raw stage over MySQL `DOUBLE` and its emitted stage over this change's
  SQL, each on PostgreSQL 18.6 and MySQL 8.4.12.

Changed diagnostics (programs refused in `0.2.1`; no accepted program
changes; MySQL projects, no message text changed):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | `r = x + w`, `r = (x * 2.0) + 1.0`, `n = count(x * 2.0)` and the other shapes above | `float_literal_operands_required` at the operation, `let`, WHERE or aggregate | none: the statement emits |
| PIE-B1003 | `r = -(-x)`, `n = count(-x)` | `unary_sign_requires_int_operand` at the sign | none: the statement emits |
