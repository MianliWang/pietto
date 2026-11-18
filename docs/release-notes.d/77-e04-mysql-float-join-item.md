### MySQL project `Float` arithmetic as a whole item on a JOIN row

- `emit-sql --project` now emits on MySQL, in MC E4B's chain J
  ([E4B's cells](../language.md#mysql-float-wider-cells)), a narrow `Float`
  operation, or with no WHERE a `+` or `*` of two `DOUBLE` fields, as a
  whole SELECT item over the row of one INNER or LEFT JOIN of two sources of
  the query's own module, such as `inner join f6i on f6i.id == f6o.id` with
  `r = f6o.v * f6i.v`, or `left join f6i on f6i.v == f6o.v` with
  `r = f6i.v + 1.0`. The JOIN is computed first and the item above it.
- The `on` is one `==` of an `Int` field of each source or of a `Text`
  field of each, under a WHERE with no `Float` operation and no `any` or
  none, or with no WHERE one of the S06 `Float`-keyed JOIN forms; with each
  item replaced by its first field of the item's nullability, the statement
  must be one MySQL emits already. Emission, plain verification, compiled
  replay and the pure boundary each apply that law to the JOIN's kind and
  its `on` by their own reading, and compiled replay and the pure boundary
  take two inputs of two different sources; that the inputs are sources of
  the query's own module, read directly and not through an alias `let`, is
  checked by emission and plain verification alone, as for E4's cell.
  Emission, compiled replay and the pure boundary each derive the S06 cell
  with that replacement, its bound below included, and admit beside such an
  item only field reads and other such items.
- The SQL is PostgreSQL's in MySQL's spelling, each `*` under E4's
  underflow guard; values, failures (error 1690, SQLSTATE 22003), carriers,
  nullability and evidence are E4's. PostgreSQL's SQL does not change, and
  no field, role or code is added.
- Kept refused, with the blockers they have without this note, object for
  object: a nesting or a `-` of two fields on a JOIN row, two fields under a
  WHERE, another SELECT item that is neither a field nor such an item
  (`c = 2.0`), a `Float` operation in the `on` (PL.68) or in the WHERE, any
  other `on`, such as a `Float` or `Text` ordering comparison (`on f6i.v <
  f6o.v`), a comparison with a literal, an `or`, a second condition beside
  an `Int` or `Text` key or a `not` over one, a WHERE beside a
  `Float`-keyed JOIN, an `any` in the WHERE, a `let`, a header parameter,
  a RIGHT JOIN, and GROUP BY, ORDER BY, LIMIT or DISTINCT beside such an
  item. Under `bind_safe_literals` a statement with a literal stays
  refused. S06's cell bounds a statement to nine expressions beyond one per
  SELECT item, so over `not (!=)` beside a `Text` key items beyond one sign
  of a field, such as `r = f6o.v * 2.0`, and over `==` beside a `Text` key
  items beyond one `+`, `-` or `*` of two fields or over an unsigned
  literal, or two signs, such as `r = f6o.v * -2.0`, keep
  `comparison_type_pair_not_admitted`.
- R2 `save_recoverable` and `recover` refuse a MySQL query of these forms
  with PIE-R1004 (`detail` `PUBLIC_R2_UNQUALIFIED_FORM`) before any
  workspace access or connection (see the
  [R2 boundary](../execution.md#known-limitations)).
- Native evidence: these forms open only on E4B's chain J qualification,
  each on PostgreSQL 18.6 and MySQL 8.4.12.
- Beyond the MySQL cadence under J12 (3): what this note keeps refused and
  no other E4B note opens keeps its refusal with no target (MC.10).

Changed diagnostics (programs refused in `0.2.1`; no accepted program
changes; MySQL projects, no message text changed):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | `r = f6o.v * 2.0` or another such item within S06's bound beside an S06 `Float`-keyed JOIN (beside `not (!=)` and a `Text` key, one sign of a field, such as `r = -f6o.v`) | `comparison_type_pair_not_admitted` at the `on` | none: the statement emits |
| PIE-B1003 | `r = f6o.v * f6i.v` or another such item beside a JOIN on an `Int` or `Text` key | `float_literal_operands_required` at the item (`unary_sign_requires_int_operand` for a sign) | none: the statement emits |
