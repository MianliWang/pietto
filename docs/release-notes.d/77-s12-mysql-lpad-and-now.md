### MySQL project `lpad` and `now()`

- A MySQL project now emits `lpad(s, width, fill)`, `now()` and
  `date_of(now())` in one position: as the whole value of a SELECT item of
  the query that `emit-sql --project` emits. `s` is a field of that query's
  source, read directly, through a row input alias (`let x = words` before
  `from x`) or through row `let` names that only rename it
  (`let t = text`), or a `Text` literal; `width` is an `Int` literal from 0
  to 256 and `fill` a one-character literal. A `def` call counts as the body
  it expands to, and parentheses change nothing. The query reads its source
  through row `let`, WHERE and window stages only, with no JOIN, GROUP BY or
  other aggregate, HAVING, QUALIFY, DISTINCT, ORDER BY or LIMIT, no header
  parameter of its own, no bind-safe `?` and no read of another relation,
  except one `scalar` read of a capturing relation `let` as the whole value
  of another SELECT item, in a query without row `let`, WHERE or window
  stages, where that relation `let` reads a captured field and its own
  source directly, through a WHERE at most. The SQL is `CASE WHEN
  CHAR_LENGTH(s) >= width THEN s ELSE LPAD(s, width, 'f') END`, which never
  truncates, `UTC_TIMESTAMP(6)` and `DATE(UTC_TIMESTAMP(6))`; PostgreSQL SQL
  and every other public PostgreSQL output are unchanged. The width bound
  keeps `LPAD` within the least `max_allowed_packet`, 1024 bytes, four per
  utf8mb4 character, above which MySQL returns NULL. Compiled bundles and
  live templates replay the same SQL.
- The `0.1.11` notes say that a MySQL project still refuses `now()` with
  PIE-B1003 `scalar_call_signature_not_admitted`; that now holds only
  outside the position above.
- The native qualification passed on 2026-11-13 in two halves on one tree
  and wheel, each accepted with no reason against: the PostgreSQL 18.6 run
  `s12-pg-20261113T161835Z-dfe5b0fcd12124d982c6d84c` and the MySQL 8.4.12
  run `s12-my-20261113T180139Z-0df8a7e9b5e881d384243993`, which also ran
  Pietto's own `mysql_rows` reader on the `now()` outputs. The MySQL
  package ran in its seventh freeze, after the fifth-round run failed on a
  wrong preregistered cleanup expectation; the PostgreSQL half ran once,
  and its package did not change. The cross-half comparison found the
  seven forms paired: every digest of each pairing summary equal and the
  nullability the design gives. The runs bound this change as first
  committed (tree `2e20e0a5`). D77.50 carries them to the commit that
  integrates this change: the records both halves' compile steps export
  are identical there apart from the harness's install identity (the
  sha256 of each record as sorted-key JSON without its `identity` field,
  first 16 digits, the same on both sides: PostgreSQL `193c8dd954adfcf4`,
  MySQL `289be8f576d3a36b`).
- R2 `save_recoverable` and `recover` refuse a query with `now()` or
  `date_of(now())` in the position above, `lpad` beside it or not, with
  PIE-R1004 `PUBLIC_R2_STATEMENT_SNAPSHOT`, as every MySQL query that reads
  `now()`, before any workspace access or connection. The SQL of `lpad`
  has a conditional CASE, so R2 prepares a query with `lpad` and no
  `now()`, and its attempt fails closed at its first page: the `SaveReply`
  of `save_recoverable` and of `recover` has the `terminal` `FAILED` (see
  the [R2 boundary](../execution.md#known-limitations)).
- Every other MySQL project `lpad` and `now()` keeps the refusal it has
  without this note. Most often that is PIE-B1003
  `scalar_call_signature_not_admitted` at the `let`, clause or select item
  that holds the call: for example a width above 256, negative or not a
  literal; a text that a `let` computes, a conditional or a read of a
  capturing `let`; a call inside another expression, in a `let` or in a
  WHERE; and a call in a query that has a JOIN, an ORDER BY, LIMIT,
  DISTINCT, QUALIFY, a `Bool`, `Int`, `Float` or `Text` header parameter, a
  bind-safe `?` or a read of another relation outside the one position
  above, or that reads an upstream query. An `lpad` select item that an
  ORDER BY names is PIE-B1003 `order`. A select item of a grouped query
  that checking admits is PIE-B1003
  `aggregate_composition_not_admitted_on_target`, as "Scalars around
  aggregate results" in the `0.1.11` notes says, and a grouped query with
  no aggregate in its SELECT is refused at check. A query that another
  refusal stops first reports that refusal instead, for example a JOIN
  shape or window aggregate that a MySQL project refuses, a
  `Decimal(p, s)`, `Date`, `Timestamp` or `UUID` header parameter, a table
  function input, `Int` arithmetic outside its physical range (PIE-B1002)
  or a capturing `let` whose body has an ORDER BY or LIMIT. `now()` in a
  `let`, a GROUP BY or ORDER BY key and the other positions that checking
  refuses stays PIE-S2387. MySQL project `concat` and `add_months` stay
  refused as without this note; `add_months` is a retained exception
  (D77.07).

Changed diagnostics (programs refused in `0.1.11`; no accepted program
changes):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | MySQL project, `lpad(s, width, fill)` in the position above, also written through a `def`, in parentheses or over a row input alias | `scalar_call_signature_not_admitted` | none: the statement emits |
| PIE-B1003 | MySQL project, `now()` or `date_of(now())` in the position above, also as a `def` argument | `scalar_call_signature_not_admitted` | none: the statement emits |
| PIE-R1004 | R2 `save_recoverable` or `recover` of a query with `now()` or `date_of(now())` in the position above | not reachable: the query did not compile | `PUBLIC_R2_STATEMENT_SNAPSHOT` |

A statement with a call in the position above that emission refuses for
another reason, such as a select of `lpad(text, 5, "0")`, `now()` and
`concat(text, "x")`, reports the `0.1.11` blockers, those of the calls in
the position included (D77.37). Every other refusal is the one the query has
without this note, object for object.
