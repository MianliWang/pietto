### MySQL project `sum(Int)` beside S03's clauses, organizations and levels

- A MySQL project now also emits S03's neighbours that the G7 and G8 notes
  above leave refused, as the
  [language page](../language.md#aggregates-and-grouping) states (the `s03n`
  list of the MySQL catch-up work package), names, a `table` declaration and
  SELECT item order aside, each statement with exactly the items written
  here. First, `from orders` `group by customer` selecting
  `customer` and one conditional sum `sum(o.amount for o in group if TEST)`,
  TEST S03's `o.flag` or G7's `o.flag and o.id > 3`, `o.flag or o.id > 3` or
  `not o.flag`, with exactly one of these: `order by customer`, on one line or
  as an `order by:` block, over `o.flag` and `o.flag and o.id > 3`; a relation
  alias `let x = orders`, `from x`, over `o.flag` and `o.flag or o.id > 3`;
  `orders` imported under its own name from the module that declares it, into
  a module that imports nothing else but a `def`, over `o.flag` and
  `o.flag and o.id > 3`; FROM reading a plain `query` of the same
  module, with no WHERE and no GROUP BY, that reads `orders` and selects
  exactly `customer`, `amount` and `flag`, each by its own name, over `o.flag`
  and `not o.flag`; and the HAVING line `paid >= 0`, on the `having` line or
  as a `having:` block, over `o.flag`.
- Second, S03's T1 and T2 with exactly one of these: T1 with
  `where lines > 0` in its second level, on one line or as a `where:` block, a
  WHERE that reads the count column of the per-order level, under `preserve`
  (under `bind-safe` that `0` is a bind-safe `?`, and the statement keeps its
  refusal); the per-order level without its `id` item, still grouped by
  `orders.id`; T2's per-order level with a `count()` that no level reads; T1
  over an `orders` that declares one more nullable `BIGINT` field after
  `flag`, which no level reads; and a third level with no key and no WHERE
  that sums each sum of T2's or T1's second level exactly once. In both
  lists, the literal `3` in TEST, the HAVING line's `0` and the `0` of T1's
  WHERE may each also be written as a call, not in parentheses, of a `def`
  with no parameters that returns it, such as `lines > zero()`. That `def`
  may have any body and declared return type that return the literal
  itself, such as `return (0)`, `return idn(0)` or `-> Int | None`, and it
  may be declared after the query or imported, also under another name,
  without parentheses or through a module that re-exports it.
- These spellings, which MySQL already emits in the base statement, are
  admitted at the same part of these statements: SELECT and GROUP BY
  layout, spaces inside an item, comment and blank lines, an unread `def` or
  `query` or an export beside the statement, also in the module that C-2
  imports from, the quoting of a source's table name, comments among the
  declarations, and at the per-order JOIN those of S03's T1 and T2, such as
  `let i = (items)`.
  Spaces between tokens, comments and blank lines do not count at the parts
  this note adds either, but for the
  line breaks and spaces at the parentheses of a `sum` or `count` call
  named below; nor do other integer spellings of the same value, such as
  `0_3` or `00`, definition order, the import's placement and the quoting of
  its path, or a space inside the call of such a `def`, such as `zero( )`:
  the literals are read by value, not by spelling. The words above also
  admit C-2's import without parentheses or as `source orders as orders`,
  and its source exported in parentheses; C-3's upstream items and the key
  written `customer = customer`; the key relabelled and ordered by its
  label, such as `c = customer` with `order by c`; and T-1's count column
  under another label, which the WHERE reads by that label.
- Each sum, at every level, is S02's guarded `SUM`, a nullable `Int`
  (`my_signed_int`), NULL for no or only NULL values, and each conditional sum
  S03's `COALESCE(` guarded `SUM` of `CASE WHEN TEST THEN x END` `, 0)`, a
  non-null `Int` (`my_signed_int`), 0 when no row's test is True; each is the
  exact sum in range, and error 1690 (SQLSTATE 22003) outside signed 64 bits,
  at any level, fails the whole statement, never a clamped value.
  Every other part of the statement, the ORDER BY, the HAVING line's WHERE over
  the aggregation stage, T1's second-level WHERE, the upstream stage and the
  per-order JOIN included, is the MySQL SQL of the same statement with each sum
  written `max`, which MySQL already emits; a relation alias or an import emits
  the SQL of the same statement read directly.
- PostgreSQL SQL and every other public PostgreSQL output are unchanged.
  Compiled bundles and live templates replay the same SQL. Emission derives
  these statements from the plan, the bound contract and the shapes as written,
  and plain verification re-derives emission's refusals; compiled replay
  derives them from its records and the pure boundary from its document, which
  a relation alias, an import, a `let` that FROM does not read, a second
  `let`, an alias of an alias or of a `query`, a parenthesized relation in
  it, a `let` in a level below the selected definition, an import beside
  another import or a `let` or one that a level below reads, the alias or
  the import over a statement of the G7 note that this note does not name,
  such as `if not not o.flag`, an upstream written as a `let` block inside
  the selected query, an explicit
  `asc`, a parenthesized ORDER BY key, WHERE test or HAVING line, a
  parenthesized part of TEST, sum argument or SELECT item, a call of a `def`
  in place of TEST, a key, an item or the argument of a `sum` without TEST
  read through the name of its source, its relation or the alias or, in the
  per-order level, without its JOIN input's name, a line break inside a
  `sum` or `count` call, a space around its argument or a comma after it, a
  space inside or before the parentheses of `count()`, a parenthesized ON
  comparison or operand of the per-order JOIN, or, at the literal `3` or `0`
  of a test, a parenthesized call, literal or column, a call with an
  argument, a call in place of the test or a column read through its
  relation's name leaves as the underlying read, and which hold no name of
  an upstream item.
- The two-database qualification of these statements, the `s03n` campaign of
  the MySQL catch-up work package on PostgreSQL 18.6 and MySQL 8.4.12, has not
  run on this change.
- Every other such MySQL project `sum(Int)` keeps the refusal it has without
  this note, object for object, with PIE-B1004
  `sum_int_aggregate_range_proof_missing` only at the sums of the lowest
  definition that holds one, where that is its blocker. Among them are every
  other WHERE in a level above the per-order level or in it, such as
  `where amount > 0` in T1's second level, which reads a field column, a
  WHERE over T2's sum or unread `count()`, another operator or literal than
  T1's, the literal first, a parenthesized or second test, a header parameter
  in it, or a WHERE in a third level; `order by customer desc`, `asc` written
  out, a parenthesized key, an ORDER BY of the sum, of two keys or of a key that
  is no `INT`, and LIMIT or DISTINCT beside a conditional sum; another HAVING
  line, operator or literal, a header parameter in it, or a HAVING line on the
  key; an upstream with a WHERE, a GROUP BY or another item, an item under
  another name such as `k = customer`, or of another module; a source
  imported under another name or through a module that re-exports it; any of
  these parts over another TEST, another literal than `3`, S03's C3 or C4, or
  over a subset of the items; a read of T1's extra `orders` field, an extra
  field of another type, a second one or one declared before `flag`; a fourth
  level, a keyed third level, or one that skips a sum of the second level or
  selects another aggregate; a read of the unread `count()`, a `count()` in
  T1's per-order level, the count of the ON field, an INNER JOIN, or a second
  level without one of its sums or with another aggregate; an ORDER BY over
  two levels; a third level over a statement that this note opens
  otherwise; and two of these changes in one statement. R2
  `save_recoverable` and `recover` refuse a MySQL query of these statements
  with PIE-R1004 (`detail` `PUBLIC_R2_UNQUALIFIED_FORM`), as for the other
  forms that MySQL opened after `0.1.11`.
- Under J12 (3), the MySQL project `sum` of an `Int` outside the forms that
  `0.1.12`, the G1 to G8 notes and this note open stays beyond the MySQL
  cadence, with the MySQL catch-up work package as its target.

Changed diagnostics: a MySQL statement whose only blockers in `0.2.1` were
PIE-B1004 `sum_int_aggregate_range_proof_missing` at the sums of these
statements is now VERIFIED with those blockers gone, such as S03's C1 with
`order by customer` or with `having:` `paid >= 0`, S03's T2 under a third
level summing its `qty`, and S03's T1 with `where lines > 0` in its second
level under `preserve`, which `0.2.1` refuses with PIE-B1004
`sum_int_aggregate_range_proof_missing` at each of that level's two sums. A
statement still refused reports exactly the blockers it has without this note,
object for object: C1 with `order by customer desc` keeps the conditional sum's
PIE-B1004, T2 under a fourth level keeps the PIE-B1004 of the per-order level's
sum alone, and T1 with `where amount > 0` in its second level, or with
`where lines > 0` under `bind-safe`, keeps the PIE-B1004 at each of that
level's two sums.
