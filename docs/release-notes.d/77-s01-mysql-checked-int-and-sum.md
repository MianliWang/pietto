### MySQL project checked `Int` arithmetic and `sum(Int)`

- A MySQL project now emits `+`, `-`, `*`, unary `-` and `abs` whose `Int`
  operands are nullable `BIGINT` fields of a source declared in the query's
  own module, read by its own name (`a` or `rows.a`), as the whole value of
  a SELECT item of the `query` or `table` that `emit-sql --project` emits.
  Parentheses and any `def` whose inlined body is the operation, such as
  `add(a, b)`, `idf(a + b)` or `idf(a) + b` beside
  `def idf(x: Int | None) -> Int | None: return x`, count as it: the plan
  holds the inlined operation. Its other
  SELECT items may be any form the query emits without this note. The query
  reads its source through one WHERE at most, of any predicate it emits
  without this note, and as written holds no `let` (a value, a carried
  field, or a relation alias such as `let x = rows`, read by `from x` or not
  read at all), window, JOIN, GROUP BY or aggregate, HAVING, DISTINCT,
  ORDER BY, LIMIT, header parameter (read or not), bind-safe `?`, set
  operand or read of another relation (an imported source, aliased or not,
  included). The SQL is the
  operation itself, such as `(a + b)`, `(-a)` or `ABS(b)`: MySQL's `BIGINT`
  operators raise error 1690 (SQLSTATE 22003) outside signed 64 bits, as
  PostgreSQL's raise 22003, and never return a wrapped value. The result is
  an `Int` (`my_signed_int`) whose range is the part of its exact range
  inside signed 64 bits, and the requirement of one whose exact range
  leaves signed 64 bits carries the evidence
  `target_checked_signed64_narrowing`, as PostgreSQL's checked `bigint`
  operation does.
- A MySQL project now emits a direct `sum` of a nullable `BIGINT` field of
  a source declared in the query's own module, read by its own name (`a` or
  `rows.a`), as the whole value of a SELECT item of the emitted `query` or
  `table`; parentheses and any `def` whose inlined body is the field, as in
  `sum((a))` or `sum(idf(a))`, count as it.
  The query reads its source through one WHERE at most, groups by at most
  one non-null `Int` field of that source or not at all, and selects only
  that key (under any name, or not at all) and direct aggregates; its
  aggregation holds `sum`, `count` and `min` only. As written it holds no
  `let` (a relation alias or a window, read or not, included), window,
  JOIN, HAVING, DISTINCT, ORDER BY, LIMIT, header parameter (read or not),
  bind-safe `?` or read of another relation (an imported source, aliased or
  not, included). The SQL is
  `CASE WHEN SUM(x) > 9223372036854775807 THEN CAST(9223372036854775807 AS
  SIGNED) + CAST(1 AS SIGNED) WHEN SUM(x) < -9223372036854775808 THEN
  CAST(-9223372036854775808 AS SIGNED) - CAST(1 AS SIGNED) ELSE CAST(SUM(x)
  AS SIGNED) END`: in range it is the exact sum, and outside it the `BIGINT`
  arithmetic of its branch raises error 1690 (SQLSTATE 22003), never a
  clamped value. The result is a nullable `Int`, NULL for no or only NULL
  values, and its R13 requirement carries the evidence
  `target_checked_signed64_narrowing`.
- PostgreSQL SQL and every other public PostgreSQL output are unchanged.
  Compiled bundles and live templates replay the same SQL. Emission derives
  these cells from the plan and the authored declaration, and plain
  verification re-derives emission's refusals from the same two; compiled
  replay derives them from its records. A relation alias or a window, read
  or not, and an imported source leave the direct read's records apart
  from source positions and the source digest, so only emission and plain
  verification refuse them.
- R2 `save_recoverable` and `recover` refuse a query of these cells with
  PIE-R1004 (`detail` `PUBLIC_R2_UNQUALIFIED_FORM`) before any workspace
  access or connection, since no native qualification has run its refined
  statement (see the [R2 boundary](../execution.md#known-limitations)).
- The raw MySQL 8.4.12 primitives behind these forms (BIGINT `+`, `-`,
  `*`, sign and `ABS`, and that guarded `SUM`) matched the signed 64-bit
  `Int` outcome beside PostgreSQL 18.6. The candidate emission experiment
  then ran the emitted SQL of its twelve forms on both databases and
  passed on 2026-11-13 in its seventh freeze: run
  `20261113T234234Z-0feefcaca55ad4d5810b6bf1` judged every form
  `EMITTED_FORM_MATCHED` with no receipt problem, each of the five S01
  families and both S02 guard outcomes matched, and the verdict was
  `MATCHED`. The run bound this change on the fix for a MySQL rows read at
  a server error after rows (tree `41bcd78a`). D77.50 carries it to the
  commit that integrates this change: the experiment's projects and
  emitted SQL are byte-identical there (`sql.json` sha256, first 16
  digits, `2fb135896e786fdd`), and its compile record is identical apart
  from the harness's install identity (the sha256 of the record as
  sorted-key JSON without its `identity` field, first 16 digits, the same
  on both sides: `7aa75d65897ea63d`).
- Every other MySQL project `Int` operation that may leave signed 64 bits
  and every other MySQL `sum(Int)` keeps the refusal it has without this
  note, object for object. Among them are `a + 1`, `n + a` or `abs(n)` over
  a non-null `BIGINT` `n`, an `INT` operand beside a `BIGINT` one,
  `a + b + a`, `-(a + b)`, `abs(-a)`, a conditional or `coalesce` around the
  operation, the operation in a `let`, a WHERE or an aggregate argument, an
  operand carried by a `let`, and a query that declares a relation alias,
  read, chained or not read at all, or a window, read or not, a query that
  reads an imported source, aliased or not, and one with ORDER BY, LIMIT,
  DISTINCT, a
  header parameter read or not, a bind-safe `?`, a JOIN, a set operand or
  an upstream query
  (PIE-B1002 `arithmetic_outside_physical_range`,
  `unary_result_outside_physical_range` or
  `abs_result_outside_physical_range`). Among the sums are a `sum` of a
  non-null or `INT` field or of a `let` name, beside a nullable or second
  group key or beside an aggregate other than `sum`, `count` and `min`
  (such as `avg`), with a relation alias or a window read or not, over an
  imported source, under HAVING, ORDER BY
  or LIMIT, with a header parameter read or not or over an upstream query,
  and a conditional sum (PIE-B1004 `sum_int_aggregate_range_proof_missing`);
  a sum of an operation, such as `sum(a + b)`, keeps that operation's
  PIE-B1002, and a sum inside another expression stays PIE-B1003
  `aggregate_composition_not_admitted_on_target`. MySQL
  project `Int` `/` stays refused (D77.23), and `Int` `%` outside the S15
  cell of [its fragment](77-s15-mysql-remainder.md).

A statement still refused reports exactly the blockers it has without this
note, object for object, a cell's own included: selecting `s = a + b` beside
`t = a + 1` keeps PIE-B1002 `arithmetic_outside_physical_range` at both, and
`x = sum(a)` beside `y = sum(a + b)` keeps PIE-B1004
`sum_int_aggregate_range_proof_missing` at `x` and PIE-B1002 at `y`.
