### MySQL project `Int /` proved by its literal

- A MySQL project now emits `Int / Int` where an `Int` literal proves the
  quotient, in two shapes only: a literal dividend over a field, such as
  `100 / b` (the literal is never the smallest `Int`), and a field over a
  literal divisor of 2 or more, such as `b / 2`. The field is a `SMALLINT`,
  `INT` or `BIGINT` field, nullable or not, of a source declared in the
  query's own module, read by name (`b` or `nums.b`), and the `/` is the
  whole value of a SELECT item of the `query` or `table` that
  `emit-sql --project` emits; the field and the literal may each stand in
  parentheses, such as `b / (2)`.
  Every other SELECT item of that query is a direct read of such a field or
  another such `/`. As written the query reads that source directly and
  holds no `let`, WHERE, window, JOIN, GROUP BY or aggregate, HAVING,
  DISTINCT, ORDER BY, LIMIT, header parameter (read or not), set operand or
  read of another relation, and no operand or item comes from a `def`, as
  its argument or as the body of a call such as `two()` of a `def` that
  returns `2`; a literal may be a bind-safe `?`.
- The SQL is the bare `(l DIV r)`, MySQL's integer division, which
  truncates toward zero as PostgreSQL's `Int /` does; a literal operand is
  `CAST(100 AS SIGNED)`, or `CAST(? AS SIGNED)` under bind-safe. MySQL
  returns NULL for a zero divisor where PostgreSQL raises 22012, so the
  result's nullability is unknown: an `Int` (`my_bigint`, all of signed 64
  bits), with no R13 evidence.
- A field proves nothing, neither by its storage nor by its declared
  `int_range` or a `value_domain` premise: MySQL fails `INT64_MIN DIV 1`
  with error 1690 although the quotient fits, and a column the contract
  states as `INT` may hold that value. So the proof reads only the literal,
  and every literal divisor is 2 or more.
- Under bind-safe, `execute(values=...)` derives the statement again with
  the bound values and applies the same rule to them: a divisor slot bound
  to 1, 0 or a negative value, or a dividend slot bound to a negative value,
  is PIE-R1004 `BINDING_INVALID` on MySQL, before any connection.
  PostgreSQL binds them as before.
- PostgreSQL SQL and every other public PostgreSQL output are unchanged.
  Compiled bundles and live templates replay the same SQL. Emission derives
  the cells once per projection, and plain verification re-derives
  emission's refusals; compiled replay derives them from its records. Plain
  and compiled verification also check each cell's operands against a
  second, separate statement of the rule. A `def` spelling leaves the
  cell's records apart from source positions and the source digest, so only
  emission and plain verification refuse it.
- R2 `save_recoverable` and `recover` refuse a MySQL query of these forms
  with PIE-R1004 (`detail` `PUBLIC_R2_UNQUALIFIED_FORM`) before any
  workspace access or connection, since no native qualification has run
  its refined statement (see the
  [R2 boundary](../execution.md#known-limitations)).
- Native evidence: the six forms open together. The candidate emission
  experiment ran the emitted SQL of its six forms on both databases under
  both literal policies, each statement one binary prepared statement in
  a read-only transaction, over a seed loaded forward and in reverse and
  over four one-row cells of a zero divisor or the smallest `Int`. It
  passed on 2026-11-14, one accepted run per database with all 48 of its
  entries matched: PostgreSQL 18.6
  `r08-pg-20261114T100717Z-613a6e541cc6fabd1125fa4d`, which ran the SQL
  text through libpq rather than through Pietto's reader, and MySQL
  8.4.12 `r08-my-20261114T100834Z-ff559ebee9874e638372fa89`. An earlier
  PostgreSQL run stopped in its harness before any statement reached the
  database; it is void and was not replaced by a rerun of its freeze
  (D77.74). The runs bound this change as first committed (tree
  `571e559e`). D77.50 carries them to the commit that integrates this
  change: the experiment's projects and emitted SQL, its 164 observations
  of the forms and the 35 refusal controls and both halves' compile
  records are identical there apart from the harness's install identity
  and the observed commit's identity (sha256, first 16 digits, the same on
  both sides: MySQL `sql.json` `c6beddc7adf5577e`, PostgreSQL `sql.json`
  `098d02c13babb711`, observations `b6458f3546bc915e`, compile records as
  sorted-key JSON without their `identity` field PostgreSQL
  `f130129297e79554` and MySQL `cff9ce1e24e09d0a`).
- Every other MySQL project `Int /` keeps the refusal it has without this
  note, object for object (PIE-B1003 `binary_operator_not_admitted`): a
  field over a field, whatever the storages, declared domains or
  `value_domain` premises, such as `b / i`, `i / b` or `t / s`; a literal
  divisor below 2 (`b / 1`, `b / 0`) or under a sign (`b / -2`); a literal
  over a literal (`100 / 7`); a nested, signed or `abs` operand
  (`(i + 1) / b`, `b / (2 + 1)`, `-i / 2`, `abs(i) / 2`); a
  header-parameter operand; an operand from a `def`
  (`b / idn(2)`, `two() / b`); a `/` inside another operation
  (`b / 2 + d`, `b / 2 / t`), in a WHERE or a `let`; one beside an item of
  any other kind, such as `p = i + j`, an S01 cell `p = b + b` or an S15
  cell `r = b % d`; and one in a query with a WHERE, over an upstream query
  or over a JOIN.

A statement still refused reports exactly the blockers it has without this
note, object for object, a cell's own included: selecting `q = b / 2`
beside `p = b + b` keeps PIE-B1003 `binary_operator_not_admitted` at `q`
and PIE-B1002 `arithmetic_outside_physical_range` at `p`.
