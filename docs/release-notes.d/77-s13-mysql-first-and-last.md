### MySQL project `first` and `last`

- A MySQL project now emits `first(x, order by k, id)` and `last(...)` only in
  the forms that [Aggregates](../language.md#aggregates-and-grouping) lists: a
  query over one source by its own name, directly or through a WHERE of
  `f is not None` tests, each of a nullable order key of a `first` or `last`
  and each key once, and at most one `f == p` test, which compares the GROUP
  BY key or, without GROUP BY, a non-null `Int` (BIGINT) field with the
  query's one header parameter, a non-null `Int` (a query with a header
  parameter has this test); grouped by one non-null `Int` (BIGINT) field,
  selected first and ordered by it ascending, or with no GROUP BY and no
  ORDER BY; whose other select items are bare `first` and `last` of
  nullable `Int` (BIGINT), `Float` (DOUBLE), `Text` (VARCHAR(32) or
  VARCHAR(64), binary) or `Decimal` (DECIMAL(65,30)) fields, all ordered by
  one key list of `Int` (BIGINT) fields and of nullable `Text` fields of that
  VARCHAR that the WHERE proves never None, field for field and direction
  for direction. The SQL is `MAX(CASE WHEN t.r1 = 1 THEN t.x END)` over a
  derived table with one `ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...)`
  per `first` or `last`, `last` with every direction flipped. The result keeps
  the value's carrier and is nullable. Compiled bundles and live templates
  replay the same SQL. PostgreSQL SQL and every other public PostgreSQL output
  are unchanged.
- They follow the raw Phase77 campaign, which matched the primitive for
  these four carriers only and ranked every value of a statement by one key
  list, both ways. The candidate emission experiment passed on 2026-11-13
  in the second attempt of its campaign: run
  `02-20261113T185329Z-d31401e667e5ee10e6596b70`, on PostgreSQL 18.6 and
  MySQL 8.4.12, judged `READY` with its 11 executed forms equal to the
  oracle on both databases and the generalized forms refused. The first
  attempt was `UNQUALIFIED`: the experiment's own MySQL seed table
  declared `TINYINT(1)`, which MySQL 8.4 warns about. The experiment's
  table and relay were fixed, and the second attempt ran against this
  change unchanged. The runs bound this change as first committed (tree
  `3a3906fd`). D77.50 carries them to the commit that integrates this
  change: the experiment's compile record, its SQL and refusal controls
  included, is byte-identical there (sha256 of the file, first 16 digits,
  the same on both sides: `ec2ecfb838900176`).
- R2 `save_recoverable` and `recover` refuse a query of these forms with
  PIE-R1004 (`detail` `PUBLIC_R2_UNQUALIFIED_FORM`) before any workspace
  access or connection, since no native qualification has run its refined
  statement (see the [R2 boundary](../execution.md#known-limitations)).
- Emission and its verifier refuse a relation alias (`let base = rows` then
  `from base`) from the plan. Compiled bundles and observation documents keep
  no trace of the alias: its SQL is the direct read's byte for byte, and its
  records and document differ from the direct read's only in the source
  text's positions and digest, so they cannot refuse it themselves. An
  observation of a query with a header parameter stays `OUTSIDE_SCHEMA`.
- Every other MySQL project `first` and `last` keeps the refusal it has without
  this note, PIE-B1003 `first_last_not_admitted_on_target` at its select item,
  with the suggestion below: for example a `Bool`, `Date`, `Timestamp` or `UUID`
  value, whose column metadata MySQL changed, a non-null value, a DECIMAL other
  than (65,30), a VARCHAR other than 32 or 64 characters, a nullable or `Text`
  group key, two group keys, a `Float` or non-null `Text` order key, `first`
  and `last` ordered by different key lists or directions, another
  aggregate beside it, a grouped query without ORDER BY or ordered descending
  or by a result, the key selected after a result, LIMIT, DISTINCT, a relation
  alias, an `is not None` test of a field that orders no `first` or `last`,
  of a non-null field or of one key twice, any other WHERE test, a second
  `== p` test, a header parameter that is not a non-null `Int`, is compared
  with another field than the group key (without GROUP BY, than a non-null
  BIGINT field) or is read in no test, a row `let` or a set operation. A
  query in the forms above that emission refuses for another reason keeps
  this refusal of each call: beside that refusal for an output label longer
  than 256 characters or a column name MySQL cannot write, and alone for the
  contract's SQL or artifact byte limit, which a query refused before its
  SQL is written never reaches. A query that check refuses, such as PIE-S2104
  for a `first` over a table or query, reports that refusal instead. These
  refusals are retained exceptions (D77.07). A MySQL single file still
  refuses every `first` and `last` with PIE-B1000.

Changed diagnostics (programs refused in `0.1.11`; no accepted program
changes):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | MySQL project, `first` or `last` in the forms above | `first_last_not_admitted_on_target`, one per call at its select item | none: the query emits |
| PIE-B1003 | MySQL project, every other `first` or `last` | `first_last_not_admitted_on_target` with the suggestion `Emit this first or last for PostgreSQL, or keep it in check/plan: MySQL has no ordered first or last yet.` | the same blocker, code, location and order, with the suggestion `Emit this first or last for PostgreSQL, or keep it in check/plan: this first or last form is not admitted on MySQL yet.` |

The Before column was measured with `emit-sql --project` on the `0.1.11`
release (`d03d6e4b`). Every other refusal is the one the query has without
this note, object for object, the suggestion above aside.
