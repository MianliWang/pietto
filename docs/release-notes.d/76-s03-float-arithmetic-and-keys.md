### `Float` arithmetic and `Float` keys in PostgreSQL projects

PostgreSQL project SQL (`emit-sql --project`) now emits these forms, which
`check --project` already accepted (D76.02 E4, E6). MySQL project SQL keeps
each one BLOCKED with its `0.1.10` code until Phase77, and no VERIFIED output
of `0.1.10` changes.

- A `Float` `+`, `-` or `*` whose operands are not both `Float` literals, such
  as `price * 2.0`, `price + cost` or `cost - price * price`, written
  `(a * CAST('2.0' AS pg_catalog.float8))` or `(a + b)` (before: PIE-B1003
  `float_literal_operands_required`), and a sign on a `Float` value, such as
  `-price`, written `(-a)` (before: PIE-B1003
  `unary_sign_requires_int_operand`). The value is Python's binary64 result,
  the sign of a zero included (`-price` of `0.0` is `-0.0`). PostgreSQL fails
  the statement with SQLSTATE 22003 where the result leaves binary64
  (`value out of range: overflow`) and where a product of two non-zero values
  rounds to zero (`value out of range: underflow`; Python gives `0.0`); it
  never returns an infinity or a wrong value. Each such `+`, `-` or `*` has the
  R05 evidence `{"overflow": "target_checked_binary64_overflow"}` (new on the
  `arithmetic` requirement kind; a reader that requires a statically proved
  finite result refuses it). The forms hold wherever a `let` does: in WHERE, a
  computed `let` GROUP BY key, an aggregate argument (`sum(price * 2.0)`) and
  over JOIN rows. A typed `None` operand keeps
  `float_literal_operands_required`.
- A `Float` as a window `partition by` or `order by` key (before: PIE-B1002
  `window_partition_comparison_domain_unsupported`,
  `window_order_comparison_domain_unsupported`), as a `string_agg` order key
  (before: PIE-B1003 `group_key_type_outside_reviewed_comparison_domain`) and in
  a FULL JOIN equality, alone or beside `Int` equalities (before: PIE-B1003
  `full_join_equality_outside_reviewed_int_domain`).
- A window `percent_rank` or `cume_dist` result read from another relation as
  a `group by` key (before: PIE-B1003
  `group_key_type_outside_reviewed_comparison_domain`), a `select distinct:`
  column (before: `distinct_field_comparison_domain_unsupported`), a relation
  `order by` key (before: `order_comparison_domain_unsupported`), a column of
  UNION DISTINCT, INTERSECT and EXCEPT (before:
  `set_row_equivalence_domain_unsupported`) and a window key (before: the
  PIE-B1002 window details above).

Each key compares by `Float` equality and orders by real value, as the
[Float values](../language.md#float-values) contract states: `-0.0` and `0.0` are
one partition, peers of a window order and a FULL JOIN match, and a merged row
shows some member's value. `count_distinct`, `min` and `max` of a
`percent_rank` or `cume_dist` result, arithmetic over one, and an offset `RANGE`
frame over a `Float` key stay BLOCKED.

Fixed: a `group by` key over another relation's window result, such as
`group by ranks.rk` with `rk = rank() window(order by g)` in the table
`ranks`, was BLOCKED with PIE-B1008 `plan_ast_correspondence` on both
dialects, because the independent emission verifier rebuilt the key column
without the window origin the emitted column keeps; it is now emitted on
PostgreSQL and MySQL.

### Changed diagnostics

The `PIE-B1003` detail `set_row_equivalence_domain_unsupported` keeps its
code and ordering. Its suggestion changed from:

> Use Int, Bool, Text, Decimal or Float with exact matching carriers. On MySQL a Float set is limited to UNION ALL, a window distribution result is limited to UNION ALL on both targets, and Timestamp to UNION ALL/DISTINCT; keep other unreviewed set carriers in check --project.

to:

> Use Int, Bool, Text, Decimal or Float with exact matching carriers. On MySQL a Float set, a window distribution result included, is limited to UNION ALL, and Timestamp to UNION ALL/DISTINCT; keep other unreviewed set carriers in check --project.

The compiled record format is unchanged.
