### JOINs in SQLite projects (alpha)

`pietto emit-sql --project ... --dialect sqlite`, `compile_sql`,
`compile_all_sql` and `compile_query(dialect="sqlite")` now write INNER and
LEFT JOINs of `sqlite.table` sources. See
[SQLite project mode](../spec/sqlite-project-v1.md#admission).

- `inner join x on ...` and `left join x on ...` of a source bound by
  `let x = source`, a self-join included, one after another. An `on` is
  one or more equalities joined with `and`, each of a field of the joined
  source and a field of an earlier input, the two of one type, `Int`,
  `Text` or `Bool`.
- After the JOINs, `where`, `select`, `group by`, `having`, `order by` and
  `limit` read the fields of every input as they read one source's; an
  aggregate over rows that a JOIN may repeat stays refused by `check`
  (PIE-S2333), as on every target.
- Each input has its own alias, `s0`, `s1`, ... in input order, and each
  `Text` equality writes `COLLATE BINARY`, so a `COLLATE NOCASE` key column
  still matches by its bytes. A LEFT JOIN's right fields are nullable in
  the result, and each column that reads a field names the `join_port` of
  its input.

New refusal: `sqlite_join_not_admitted` (PIE-B1003) for a RIGHT, FULL,
CROSS or asof JOIN, a JOIN to a table, query or relation `let`, a
relationship match, or any other `on`.

Compatibility: PostgreSQL, MySQL and DuckDB SQL bytes, contracts and
diagnostics are unchanged, and so are a statement's bytes over one source.
Against `0.2.2`, which refused every JOIN of `sqlite.table` sources, these
outputs change:

- A statement with an INNER or LEFT JOIN of sources, which `0.2.2` refused
  with `sqlite_relation_shape_not_admitted` and with the other rules that
  its clauses broke, such as `sqlite_source_count_not_admitted`, is now
  emitted, or reports only the rules it breaks, such as
  `sqlite_join_not_admitted` at the JOIN.
- A RIGHT, FULL or CROSS JOIN of two sources, which `0.2.2` refused with
  `sqlite_relation_shape_not_admitted` and `sqlite_source_count_not_admitted`,
  now reports `sqlite_join_not_admitted` alone, at the JOIN.
- A JOIN to a table or query still reports
  `sqlite_relation_shape_not_admitted`, now at that JOIN rather than at an
  earlier JOIN of sources, and also `sqlite_join_not_admitted` there. Such
  a statement no longer reports `sqlite_source_count_not_admitted` or the
  rules 9, 9b and 10 to 13 that read fields, such as
  `sqlite_expression_not_admitted` and `sqlite_order_not_admitted`.
- The suggestions of `sqlite_relation_shape_not_admitted` and
  `sqlite_source_count_not_admitted` change for every statement they refuse,
  and scripts that match their text must follow. They now read `SQLite
  emission admits one source read, or INNER and LEFT JOINs of sources, with
  where, group by, having, order by, limit and select, and windows over one
  source read without group by; qualify, distinct, set operations, relation
  lets and reads of another table or query are not available on SQLite` and
  `read one sqlite.table source, or join sqlite.table sources`.
