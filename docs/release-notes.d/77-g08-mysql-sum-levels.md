### MySQL project `sum(Int)` over several levels

- A MySQL project now also emits each `sum` of an `Int` of a statement
  whose definitions form a chain of levels, as the [language
  page](../language.md#aggregates-and-grouping) states: the selected
  `query` or `table` reads by `from` one definition of its module by its
  own name, which reads one in turn, down to a source of the module, three
  levels or more, or down to the per-order level of the
  [style page](../style.md)'s two-level example, two levels or more. The
  style page's example itself, whose `amount` is non-null, is one.
- Each level is a plain level, which reads the level below by name under any
  names with one WHERE at most; an aggregate level in the S02 cell as the G1
  and G2 notes above widen it, which below the top groups by a key and holds a
  `sum`; or, as the bottom only, the style page's per-order level over its
  `Order` (a non-null `BIGINT` `id` with its one key `unique(id)`, a
  non-null `INT` `customer_id` and a non-null `BIGINT` `amount`, each over
  its storage's whole range) and `Item` (two non-null `BIGINT`s, `id` and
  `order_id`, and no key), names and item order aside, under T1's second
  level. The per-order keys are `id`, `customer_id`, `amount` in that order.
  The second level groups by the customer with no WHERE. It selects any
  of the customer, `sum(amount)` and `sum(lines)`, each at most once, with
  at least one sum. A `sum` reads a `BIGINT` or `INT` field carried up, or a sum or
  count of the level below, directly or through a value `let` of its level; a
  key reads a `BIGINT`, `INT` or `VARCHAR` field; no `count` or `min` reads a
  `SMALLINT` field, which only S02's own cell takes, as the G1 note states;
  `min`, `max` and `avg` may
  also read a `min` or `max` column of a `BIGINT` field, and no other `min` or
  `max` column: one of a `SMALLINT` or `INT` field is, as in the G4 note, the
  cast `my_signed_int` at every level above it, and no aggregate, a `min`
  included, reads it or one of a `Float`, `Decimal`, `Date` or `Timestamp`
  field. Every sum below the top is read by a `sum` above it or reaches the
  result, and no level above the lowest one with a `sum` has a WHERE.
- Each `sum`, at every level, is the cell's guarded `SUM`, a nullable `Int`
  (`my_signed_int`): NULL for no or only NULL values, the exact sum in
  range, and error 1690 (SQLSTATE 22003) outside signed 64 bits, at any
  level, which fails the whole statement, never a clamped value. Every
  level's keys, other aggregates, plain items, `let` stages, FROM, the
  per-order JOIN, WHERE and GROUP BY are the MySQL SQL of the same
  statement with each `sum` written `max`, which MySQL already emits.
- PostgreSQL SQL and every other public PostgreSQL output are unchanged.
  Compiled bundles and live templates replay the same SQL. Emission derives
  the chain from the plan, the bound contract and the shapes as written,
  and plain verification re-derives emission's refusals; compiled replay
  derives it from its records and the pure boundary from its document.
- The two-database qualification of these chains, the G8 campaign of the
  MySQL catch-up work package on PostgreSQL 18.6 and MySQL 8.4.12, has not
  run on this change.
- Every other MySQL project `sum(Int)` over several definitions keeps the
  refusal it has without this note, object for object, with PIE-B1004
  `sum_int_aggregate_range_proof_missing` only at the sums of the lowest
  definition that holds one, where that is its blocker. Among them are two
  levels over a source outside the G4 note's upstream, a conditional sum (the
  G7 note's, one level only) at any level, a JOIN above the bottom, a sum,
  count or `avg` as a key or under another aggregate than `sum`, a `min` or
  `max` as a key or summed, one of a field that is not `BIGINT` under `min`,
  `max` or `avg`, a lower aggregate level without a key or a `sum`, a lower
  `sum` that no `sum` above reads, a WHERE above the lowest level with a `sum`,
  a per-order level over other sources, keys, carriers or JOIN (S03's T1 and
  T2 under a third level among them, but those that the `s03n` note below
  opens), and HAVING, ORDER BY, LIMIT, DISTINCT, a header parameter, a
  bind-safe `?`, a relation alias, an unread window, an imported definition
  and a read qualified by a definition's name. R2 `save_recoverable` and
  `recover` refuse a MySQL query of these chains with PIE-R1004 (`detail`
  `PUBLIC_R2_UNQUALIFIED_FORM`), as for the other forms that MySQL opened
  after `0.1.11`.

Changed diagnostics: a MySQL statement whose only blockers in `0.2.1` were
PIE-B1004 `sum_int_aggregate_range_proof_missing` at the sums of a chain of
these levels is now VERIFIED with those blockers gone, such as the style
page's two-level example and a third level summing its `revenue` and
`lines`. A
statement still refused reports exactly the blockers it has without this
note, object for object: a third level grouped by a lower sum (`group by k,
s`) keeps the PIE-B1004 of the lower level's sums alone.
