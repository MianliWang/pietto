### MySQL project `sum(Int)` through aliases, imports and an upstream

- A MySQL project now also emits a `sum` of an `Int` in the S02 cell that
  the [language page](../language.md#aggregates-and-grouping) states, as the
  G1 to G3 notes above widen it, when its query names and reaches its rows
  in other ways. Each `query` or `table` may declare relation aliases
  (`let r = rows`) of the relation its FROM reads, read by `from r` or not
  at all, and windows that nothing reads; each field read may be qualified
  by the name under which the query reads its relation (`rows.a`, `r.a`,
  `base.a`); the source may be declared in another module and imported,
  under its own name or another, directly or through re-exports.
- The query may also read, in place of the source, one upstream `query` or
  `table`, declared in its module or imported, that reads the source so
  through one WHERE at most and nothing else: either a plain upstream whose
  SELECT items are field reads under any names, or an aggregating one that
  is itself a query of the cell with at least one GROUP BY key and at least
  one `sum`. The query reads an upstream column as a field of the column's
  carrier: a field or key keeps its field's, a `sum` is a nullable `Int`, a
  count a non-null `BIGINT`, a `min` or `max` keeps its field's and an `avg`
  is a `DOUBLE`. A `sum` of the query may read a `sum`, count, `min`, `max`,
  key or field column; its keys and the arguments of its `max`, `avg` and
  `count_distinct` keep the storages of the G2 note above. Over an
  aggregating upstream the query holds a `sum`, reads every `sum` of the
  upstream as an aggregate's argument, directly or through a `let`, and has
  no WHERE, HAVING, ORDER BY, LIMIT or DISTINCT; over a plain upstream the
  G3 clauses stay as that note states them.
- Each `sum`, at either level, is the cell's guarded `SUM`, a nullable `Int`
  (`my_signed_int`): NULL for no or only NULL values, the exact sum in
  range, and error 1690 (SQLSTATE 22003) outside signed 64 bits, which fails
  the whole statement, never a clamped value. Everything else is the MySQL
  SQL of the same statement with each relation alias and unread window
  dropped, each read unqualified, each import declared in place and each
  `sum` written `max` at both levels, which MySQL already emits. Each `sum`
  of an aggregating upstream is a column of its aggregation stage that the
  query reads under no filter, so an out-of-range one is expected to fail
  the statement on both targets (not yet observed: see below). Each R13
  requirement of a `sum` carries the evidence
  `target_checked_signed64_narrowing`.
- PostgreSQL SQL and every other public PostgreSQL output are unchanged.
  Compiled bundles and live templates replay the same SQL. Emission derives
  the upstream's law from the plan and the written definitions, and plain
  verification re-derives emission's refusals; compiled replay derives it
  from its records and the pure boundary from its document, each following
  the query's reads into the upstream. A relation alias, one of a second
  import name of the upstream included, an unread window, an imported
  source and an upstream declared as a relation `let` block of the query
  leave the records and document of the plain read, its upstream a `query`
  of its module, so emission alone refuses those outside the cell.
- The two-database qualification of these forms, the G4 campaign of the
  MySQL catch-up work package on PostgreSQL 18.6 and MySQL 8.4.12, has not
  run on this change.
- Every other MySQL project `sum(Int)` keeps the refusal it has without
  this note, object for object (PIE-B1004
  `sum_int_aggregate_range_proof_missing` where that is its blocker). Among
  them are an alias of an alias, an unread alias of a relation that FROM
  does not read (a second import name of FROM's upstream included), a
  window that is read, a third level, an upstream declared as a relation
  `let` block of the query, an upstream with a JOIN, HAVING, ORDER BY,
  LIMIT, DISTINCT, a header parameter or a bind-safe `?` other than the G5
  note below opens, a plain upstream with a `let` or an item that
  computes, an aggregating upstream with no key, no `sum` or a `sum` the
  query does not read (a mention in an unread window is no read), a WHERE
  or a G3 clause over one, a query with no
  `sum` over one, an upstream `sum` or `avg` as a key or as the argument of
  `max`, `avg` or `count_distinct`, and an upstream `min` or `max` of an
  `INT` field below the upstream's WHERE or `let` in either place. R2
  `save_recoverable` and `recover` refuse a MySQL query of these forms with
  PIE-R1004 (`detail` `PUBLIC_R2_UNQUALIFIED_FORM`), as for the other forms
  that MySQL opened after `0.1.11`.
- Under J12 (3), the MySQL project `sum` of an `Int` outside the forms
  that `0.1.12`, the G1 to G3 notes, this note and the G5 note below open
  stays beyond the MySQL cadence, with the MySQL catch-up work package as
  its target.

Changed diagnostics: a MySQL statement whose only blockers in `0.2.1` were
PIE-B1004 `sum_int_aggregate_range_proof_missing` at sums of these forms is
now VERIFIED with those blockers gone, such as `let x = rows`, `from x`,
`group by k` selecting `k` and `sum(a)`, or `query up` selecting `k` and
`a` from `rows` read by `from up`, `group by k` selecting `k` and
`sum(a)`. A statement still refused reports exactly the blockers it has
without this note, object for object: `let y = x` after `let x = rows`,
read by `from y`, keeps its one PIE-B1004.
