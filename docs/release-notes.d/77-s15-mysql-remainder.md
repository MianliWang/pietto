### MySQL project `Int %` and `Float %`

- A MySQL project now emits `Int % Int` whose operands are two `BIGINT`
  fields, nullable or not, and `Float % Float` whose operands are two
  `DOUBLE` fields, nullable or not, of a source declared in the query's own
  module, read by name (`a` or `nums.a`, also in parentheses), as the whole
  value of a SELECT item of the `query` or `table` that
  `emit-sql --project` emits. Every other SELECT item of that query is a
  direct read of a `BIGINT` or `DOUBLE` field of the same source or another
  such `%`. As written the query reads that source directly and holds no
  `let`, WHERE, window, JOIN, GROUP BY or aggregate, HAVING, DISTINCT,
  ORDER BY, LIMIT, header parameter (read or not), bind-safe `?`, set
  operand or read of another relation, and no operand or item is a `def`
  argument.
- The SQL is the bare `(a % b)`, with no CAST, CASE or guard. MySQL computes
  the `DOUBLE` remainder as `fmod` and returns NULL for a zero divisor where
  PostgreSQL raises 22012, so the result's nullability is unknown: an
  `Int` (`my_bigint`, all of signed 64 bits) or a finite binary64 `Float`
  (`my_double`), with no R13 evidence.
- PostgreSQL SQL and every other public PostgreSQL output are unchanged.
  Compiled bundles and live templates replay the same SQL. Emission derives
  the cells once per projection, and plain verification re-derives
  emission's refusals; compiled replay derives them from its records. A
  `def` spelling leaves the direct read's records apart from source
  positions and the source digest, so only emission and plain verification
  refuse it.
- R2 `save_recoverable` and `recover` refine a query of these forms as any
  other query, and no native qualification has run those refined
  statements; in the lead's survey on MySQL 8.4.12 on 2026-11-14, over the
  experiment's seed rows and over all its cell rows, a zero divisor and
  extreme values included, each such attempt completed with the rows
  `execute()` returns (see the
  [R2 boundary](../execution.md#known-limitations)).
- The raw MySQL 8.4.12 primitives behind these forms (`BIGINT` `%` and
  `DOUBLE` `%`) matched the PostgreSQL 18.6 outcome apart from the zero
  divisor above. The candidate emission experiment then ran the emitted
  SQL of its seven forms on both databases and passed on 2026-11-13 in its
  eighth freeze, one run per database, each with no reason against and
  accepted: PostgreSQL 18.6
  `s15c-pg-20261113T160648Z-b012c65cf778b3a13e2e71da` and MySQL 8.4.12
  `s15c-my-20261113T160648Z-6be83f52cdb53c5093a20372`. The runs bound this
  change as first committed (tree `eedeb14e`). D77.50 carries them to the
  commit that integrates this change: the experiment's projects and
  emitted SQL, its 90 refusal-control observations and both halves'
  compile records are identical there apart from the harness's install
  identity and the observed commit's identity (sha256, first 16 digits,
  the same on both sides: MySQL `sql.json` `1913d75af0758d4c`, PostgreSQL
  `sql.json` `2af3cb86fd11f7a9`, controls `1f36dad509c962b1`, compile
  records as sorted-key JSON without their `identity` field PostgreSQL
  `31462b5ccbf56ef8` and MySQL `cd53c18851072c60`).
- Every other MySQL project `%` keeps the refusal it has without this note,
  object for object (PIE-B1003 `binary_operator_not_admitted` for `Int`,
  `float_remainder_exact_binary64_not_realized` for `Float`): a literal or
  header-parameter operand such as `a % 2`, `INT` or `DECIMAL` operands,
  `(a % b) + n`, `x % y % u`, a `%` in a `let` or a WHERE, beside
  `s = a + b`, beside a comparison or a function call, beside a `DECIMAL`,
  text or `INT` field, under a WHERE, with ORDER BY, LIMIT or DISTINCT, over
  an upstream query or a JOIN, or through a `def`. MySQL project `Float /`
  stays refused (PIE-B1003 `float_division_not_realized`), and so does
  `Int /` (PIE-B1003 `binary_operator_not_admitted`, D77.23).

A statement still refused reports exactly the blockers it has without this
note, object for object, a cell's own included: selecting `r = a % b`
beside `q = x / y` keeps PIE-B1003 `binary_operator_not_admitted` at `r` and
`float_division_not_realized` at `q`.
