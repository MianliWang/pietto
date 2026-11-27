### MySQL project `Float` arithmetic of two fields, one nesting and `count`

- `emit-sql --project` now emits on MySQL, in MC E4B's chain C
  ([E4B's cells](../language.md#mysql-float-wider-cells)), a `Float` `+`,
  `-` or `*` of two `DOUBLE` fields, such as `x + w` or `x - x`, and one
  level of nesting, an inner such operation as an operand beside a field or
  a `Float` literal, such as `(x * 2.0) + 1.0`, `x * (w + 1.0)` or
  `-(-x)`. Each stands as a whole SELECT item with no WHERE, as one `let`
  value read by the select list or by one ORDER BY key, or compared with a
  `Float` literal in a whole WHERE with no `let`.
- `count` of the unary `-` of a nullable field now emits on MySQL with no
  WHERE, ungrouped or beside GROUP BY keys that are fields, such as
  `n = count(-x)` or `group by g` with `n = count(-x)`. A `count` of a `+`,
  `-` or `*` stays refused, and so does any `count` under a WHERE: MySQL
  may count a row without computing an argument that it types non-nullable,
  as over a `NOT NULL` column that a nullable declaration describes, which
  the contract allows, while PostgreSQL computes it there and fails the
  statement where it overflows. A sign cannot fail, so its `count` is the
  same on both.
- The SQL is PostgreSQL's in MySQL's spelling, each `*` under E4's
  underflow guard with an inner operation written inside it as its own SQL;
  `count` counts in the aggregate CTE. Values, failures (error 1690,
  SQLSTATE 22003) of the operations MySQL computes, carriers, nullability
  and evidence are E4's;
  PostgreSQL's SQL does not change, and no field, role or code is added.
- Emission, plain verification, compiled replay and the pure boundary each
  apply E4B's operand law, the field or one-level inner operation beside a
  field or literal, and the `count` law above by their own reading of their
  input.
- Kept refused, with the blockers they have without this note, object for
  object: two fields or a nesting in two `let`s, under a WHERE over its
  `let`, beside or under an operation item or in two ORDER BY keys; two
  levels of nesting, two inner operations and a folded inner operation;
  `count` of a `+`, `-` or `*`, such as `n = count(x * 2.0)` or `group by g`
  with `n = count(x - w)`, of a nesting, of a non-null value, of a `let`
  name, beside an aggregate other than such a `count` (`count()` or
  `max(y)`; two such `count`s emit), ordered, composed or under any WHERE,
  and `count_distinct` of an operation; two fields under a WHERE. Under
  `bind_safe_literals` a statement with a literal stays refused, since that
  literal is a bind-safe `?`.
- R2 `save_recoverable` and `recover` refuse a MySQL query of these forms
  with PIE-R1004 (`detail` `PUBLIC_R2_UNQUALIFIED_FORM`) before any
  workspace access or connection, and one with an ORDER BY key with its
  earlier PIE-R1004 `REFINEMENT_COMPARISON_DOMAIN` when they prepare it
  (see the [R2 boundary](../execution.md#known-limitations)).
- Native evidence: E4B's chain C qualification on PostgreSQL 18.6 and
  MySQL 8.4.12 opens these forms. Its raw stage over MySQL `DOUBLE`
  (`e4b-c`), on the raw prepared and raw text routes, matched on both
  databases in every group that opens a position. Its one mismatch is its
  preregistered witness, a `count` of a non-null value, which MySQL
  returned where PostgreSQL failed with SQLSTATE 22003: the mechanism above
  for which a `count` of a `+`, `-` or `*` stays refused. Its emitted stage
  over this change's SQL (`e4b-c-emitted`) matched on both databases on the
  public, raw prepared and raw text routes.
- The [deferred subjects](../roadmap.md#deferred-subjects) give E4B's
  chain C owner a target before the Phase82 freeze for the refused counts
  of a `Float` `+`, `-` or `*` and for counts under a WHERE. Either MySQL
  SQL must evaluate the argument regardless of column nullability, or
  MySQL source admission must reject the conflicting column declaration.
  Each route needs a chain C witness. Other forms this note keeps refused
  and no other E4B note opens have no target under MC.10 (J12 (3)).

Changed diagnostics (programs refused in `0.2.1`; no accepted program
changes; MySQL projects, no message text changed):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | `r = x + w`, `r = (x * 2.0) + 1.0` and the other shapes above | `float_literal_operands_required` at the operation, `let` or WHERE | none: the statement emits |
| PIE-B1003 | `r = -(-x)`, `n = count(-x)` | `unary_sign_requires_int_operand` at the sign | none: the statement emits |
