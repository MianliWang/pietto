### MySQL project `Float` arithmetic in a `let`, a WHERE and an ORDER BY key

- `emit-sql --project` now emits on MySQL the narrow `Float` operations of
  [E4's cell](../language.md#mysql-float-arithmetic-cell), a `+`, `-` or `*`
  of a `DOUBLE` field and a `Float` literal and the unary `-` of such a
  field, in three more positions of MC E4B
  ([E4B's cells](../language.md#mysql-float-wider-cells)): one or two `let`
  values read by the select list, such as `let t = x * 2.0` with `r = t`; a
  WHERE that is one whole comparison, or its `not`, of such an operation or
  of its one `let` with a `Float` literal, such as `where x * 2.0 > 1.0` or
  `where t <= 0.0`; and ORDER BY keys that are `let` names, one key over one
  `let` or two over two, such as `order by t, u desc`. Every `let` is read,
  every one by the WHERE when there is one, and the statement reads one
  source of its own module with no JOIN, window, GROUP BY, DISTINCT, LIMIT,
  header parameter, upstream query or relation alias. PostgreSQL emitted
  these statements already; its SQL does not change.
- The SQL is PostgreSQL's in MySQL's spelling: a `let` value is computed for
  every source row in the first CTE, a WHERE filters in its own CTE and `*`
  stands under E4's underflow guard. Values, failures (error 1690, SQLSTATE
  22003), the `my_double` `finite_float` result, its nullability and the
  binary64 evidence are E4's; no field, role or code is added
  ([project JSON v2](../spec/project-cli-json-v2.md)).
- Emission derives the cells from the plan, compiled replay from its records
  and the pure boundary from its document; plain verification asks
  emission's function where the cells are and checks each operation's
  operands by its own law.
- Kept refused, with the blockers they have without this note, object for
  object: a `let` nothing reads or that a WHERE beside it does not read, a
  WHERE with another condition or comparing with a field or another
  operation, a `let` name as an operand, a `let` or ORDER BY key beside an
  operation item, a field key beside a `let` key, three `let`s, and these
  positions under LIMIT, DISTINCT, a window, an aggregate, an upstream query,
  a relation alias, an unread window or header parameter, or a JOIN. Under
  `bind_safe_literals` a statement with a literal stays refused.
- R2 `save_recoverable` and `recover` refuse a MySQL query of these forms
  with PIE-R1004 (`detail` `PUBLIC_R2_UNQUALIFIED_FORM`) before any
  workspace access or connection, and one with such an ORDER BY key with
  its earlier PIE-R1004 `REFINEMENT_COMPARISON_DOMAIN` when they prepare it
  (see the [R2 boundary](../execution.md#known-limitations)).
- Native evidence: these forms open only on E4B's chain B qualification, its raw
  stage over MySQL `DOUBLE` and its emitted stage over this change's SQL,
  each on PostgreSQL 18.6 and MySQL 8.4.12.
- Beyond the MySQL cadence under J12 (3): E4B's later positions, a
  parameter operand, a computed `let` GROUP BY key and a whole-column item
  on a JOIN row, wait for its later slices; a JOIN `on` keeps its refusal
  (owner, O1 (a)).

Changed diagnostics (programs refused in `0.2.1`; no accepted program
changes; MySQL projects, no message text changed):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | `let t = x * 2.0` read by the select list, a WHERE or an ORDER BY key, `where x * 2.0 > 1.0` and the other shapes above | `float_literal_operands_required` at the `let` or WHERE | none: the statement emits |
| PIE-B1003 | `let t = -x` in the shapes above | `unary_sign_requires_int_operand` at the `let` | none: the statement emits |
