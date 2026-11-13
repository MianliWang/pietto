### MySQL project `Decimal`, `Date` and `Timestamp` parameters

- A MySQL project now emits a query header parameter of type
  `Decimal(p, s)`, `Date` or `Timestamp` in two positions: as the whole
  value of a SELECT item of the query that `emit-sql --project` emits, or
  as the right operand of `==`, `!=`, `<`, `<=`, `>` or `>=` whose left
  operand is a field of that query's source with the parameter's type, in
  a comparison that the WHERE reaches through `and` and `or` alone. The
  query reads its one source directly, through one WHERE at most, with no
  `let`, JOIN, GROUP BY or other aggregate, window, HAVING, QUALIFY,
  DISTINCT, ORDER BY, LIMIT or read of another relation, declares no
  `UUID` parameter and reads every such parameter it declares. Each read
  is one `?` in rendering order, also when one parameter is read twice:
  `CAST(? AS DECIMAL(p,s))`, `CAST(? AS DATE)` or
  `CAST(? AS DATETIME(6))`. A bound value travels as its canonical text;
  the public typed values, their binding checks and NULL are unchanged,
  and each value is checked before any statement is prepared. Compiled
  bundles and live templates replay the same SQL. PostgreSQL SQL and every
  other public PostgreSQL output are unchanged.
- The `0.1.11` notes say that a MySQL project refuses these three
  parameter types and `UUID` with PIE-B1003
  `query_parameter_type_not_admitted_on_target`; for the three, that now
  holds only outside the positions above.
- The candidate emission experiment passed on 2026-11-13: run
  `run-20261113T184243Z-f8031e2d653b4bcbfbaa584f`, on PostgreSQL 18.6 and
  MySQL 8.4.12, ran its 26 forms with 90 bindings on each database,
  directly and through Pietto's reader, and its judge found
  `CANDIDATE_EMISSION_MATCHED` with no reason against; the run was
  accepted. It bound this change as first
  committed (tree `436ef88d`). D77.50 carries it to the commit that
  integrates this change: the experiment's compile records, its SQL and
  refusal controls included, are identical there apart from the harness's
  install identity (the sha256 of each record as sorted-key JSON without
  its `identity` field, first 16 digits, the same on both sides: PostgreSQL
  `76501ec0a5e6e478`, MySQL `cf49944a24eae1a7`).
- A MySQL `UUID` header parameter stays refused as a retained exception
  (D77.07), read or not and in any position, and so does every other typed
  declaration of a query that declares one. The S09 candidate emission
  experiment found MySQL returning its `CAST(? AS BINARY(16))` output as
  `VARBINARY` (column type 253), as the MySQL manual states for
  `CAST(... AS BINARY(N))`, while Pietto describes a MySQL `UUID` column
  as `BINARY(16)` (254), so its MySQL opening was withdrawn. A new
  preregistered experiment is needed to open it.
- Every other MySQL query that declares one of these types, read or not,
  keeps the refusal it has without this note: PIE-B1003
  `query_parameter_type_not_admitted_on_target` at each such declaration.
  Examples are a parameter on the left of its comparison, under `not`,
  `between`, `in`, `is None` or a call, compared with a `let` value or
  another parameter, declared and never read, or read in a query with a
  `let`, an ORDER BY, LIMIT, DISTINCT, GROUP BY, window or JOIN, or that
  reads another query. A query whose reads all sit in the positions above
  but that another rule refuses, such as a `Decimal(10, 2)` parameter
  compared with a `Decimal(9, 2)` field or `add_months` in another SELECT
  item, reports that same list, as without this note.
- A `Timestamp` parameter selected as an output still emits, compiles,
  exports and binds on MySQL, and `execute()`, `save()` and R2
  `save_recoverable` and `recover` still refuse it with PIE-R1004 (`detail`
  `MEANING_OUTPUT`; see the
  [R2 boundary](../execution.md#known-limitations)).

Changed diagnostics (programs refused in `0.1.11`; no accepted program
changes):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | MySQL project, a `Decimal(p, s)`, `Date` or `Timestamp` header parameter read only in the positions above, in a query that declares no `UUID` parameter | `query_parameter_type_not_admitted_on_target` at each such declaration | none: the query emits |

Every refused query reports the list it reports without this note, object
for object.
