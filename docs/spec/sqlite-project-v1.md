# Pietto SQLite Project Mode v1

## Status

This is an **alpha** contract until the Phase82 freeze. It is the first tier
of Phase78's second vertical, SQLite B2: project-mode SQLite SQL from a
separate SQLite project adapter, with `having`, `count_distinct`, `avg` of an
`Int` and a guarded `sum` of an `Int` in project mode, the same aggregates
except `sum` in single files, and (in tier 1b) the read-only execution of a
caller's SQLite file. It is qualified only for SQLite `3.53.1` with the
source id and the 46 compile options of the measured build, under CPython
3.13.13 and 3.12.13 on Linux x86-64; every other build and platform is not
qualified, and there the SQL text is the same but nothing runs. Its names,
fields, detail words and limits may change in any later release, each with a
release-note line and no deprecation period.

The rules come from the owner's answer PL.47, which approves the SQLite B2
Gate 1, and from the decisions it keeps: the third-dialect seam AD78.03,
SQLite B1's value rules D78.02 (revised by PL.47 for the collation premise in
project mode only), target identity D78.03, errors D78.04 and the replay rules
D78.08, D78.10 and D78.11 ([decision record](../decisions.md)). The
[Phase78 route](../phases/phase-78/route.md#b2-route) holds the slices.
Rows marked *derived* are consequences of those decisions that this page
fixes; the lead states them to the owner as inform before this page binds
(see [open items](#open-items)). A text outside the tables of this page, or
a new diagnostic code, needs the owner.

Construction state: SPECIFIED. S06 wrote this page before any B2 code. S07
adds the shared connector entry and the three family mappings, S08 the
adapter and the T1 forms, S09 their native qualification, S10 the T2
aggregates in both modes, R1 the PostgreSQL replay, S11 the
[execution](#execution) section and its route, S12 that route's
qualification, and S16 closes the tier. Each slice edits the rows it lands.
Until a release that the owner approves carries a form, today's behavior
stands: a project's `check` refuses `sqlite.table` with `PIE-S2306`
`Unknown source connector: sqlite.table`, `emit-sql --project --dialect
sqlite` is a usage error, `compile_query(dialect="sqlite")` reports
`PIE-R1002`, and Pietto opens no SQLite file.

## Admission

| Admission | Exact limit |
| --- | --- |
| Project and source | An explicit-module project (`schema_version = 2`) whose statement reads exactly one source declared `source x: Shape = sqlite.table("name")`. |
| Relational shape | One source read, its `where` filter, a `group by`, a `having`, an `order by`, a `limit`, and the final projection. No JOIN, window or `qualify`, relation `let`, read of another table or query, `distinct`, set operation, typed VALUES body or table function. |
| Columns | Source fields are `Int`, `Text`, `Bool` or `Float`, each with its compiled nullability. Results follow the projection. |
| Expressions | In `select`, `where` and `having`: a field of the source, a literal, a query parameter, a comparison (`==`, `!=`, `<`, `<=`, `>`, `>=`) of two values of one type, `and`, `or`, `not`, `is None` and `is not None`; in `having` and in the `select` of an aggregated relation also an admitted aggregate. No arithmetic, a sign before a number included, no `in`, range comparison, conditional, cast, function call or `any(...)` read, and no `None` literal outside `is None` and `is not None`. |
| Aggregates | `count()` and `count(x)`; `count_distinct(x)` of an `Int`, `Text` or `Bool` field; `min(x)` and `max(x)` of an `Int` or `Float` field; `avg(x)` of an `Int` field; and `sum(x)` of an `Int` field whose contract `int_range` lies on one side of zero (`min` of 0 or more, or `max` of 0 or less). Each reads one field of the source directly. |
| Grouping and order | A `group by` key is a field of the source. In an aggregated relation a result field is a `group by` key, an admitted aggregate, a literal or a parameter, and an `order by` key is a selected `group by` key or aggregate; elsewhere an `order by` key is a field of the source. A `limit` is an `Int` literal from 0 to 9223372036854775807. |
| Parameters | Query header parameters of type `Int`, `Text`, `Bool` or `Float`, optional or not, read in `select`, `where` or `having`. |
| Literal policy | `preserve` only. |
| Entry points | `pietto check --project`; `pietto emit-sql --project ... --dialect sqlite`, with or without `--all`; `compile_sql` and `compile_all_sql` with `dialect="sqlite"`. `compile_query` and `execute` wait for S11. |

The aggregates of the table are the T2 forms that S10 lands; until S10 they
are refused with `sqlite_aggregate_not_admitted`, and an aggregated relation
admits `count`, `min` and `max` only, as SQLite single files do today.
`having`, also a T2 form, is refused until S10 by rule 5,
`sqlite_relation_shape_not_admitted`, at the `having`. S10 edits this
paragraph when it opens them.

Not in this tier: `Decimal`, `Date`, `Timestamp`, `UUID`, `Bytes`, `Json`,
enum and nested fields; `--literal-policy bind-safe`; arithmetic, `Float`
`sum` and `avg`, text functions and `LIKE`, `string_agg`, `median` and
`quantile`; JOINs and windows, which a later Gate 1 decides at the B2
midpoint; schema-qualified or attached tables; query bundles, saved
results, relay, jobs and R2; and any change to PostgreSQL, MySQL or DuckDB SQL
bytes, contracts or diagnostics beyond the refusal of a `sqlite.table` source
that [compile refusals](#compile-refusals) states. No claim of parity across
databases is made.

## Single files

S10 also opens three forms in `pietto emit-sql FILE --dialect sqlite`, by the
[SQLite single-file rules](../language.md#sqlite-single-files), which S10
edits: `having`, with the expressions of the table above over `group by` keys
and aggregates; `count_distinct` of an `Int`, `Text` or `Bool` field; and
`avg` of an `Int` field, written `AVG(CAST(x AS REAL))`. Single-file SQL keeps
B1's premises, the `BINARY` collation among them, and writes no `COLLATE`. A
file has no contract and no `int_range`, so `sum` of an `Int` stays refused
with its `PIE-B1000` reason, unchanged. The new single-file refusals keep the
existing `PIE-B1000` text, `SQLite SQL emission is not implemented for
RelationIR: <name>. <reason>`, with these reasons (*derived*):

| Form | Reason |
| --- | --- |
| `avg` of a `Float` field | `SQLite aggregate avg supports only Int fields` |
| `count_distinct` of a `Float` field | `SQLite aggregate count_distinct supports only Int, Text and Bool fields` |

Every other single-file text stays as it is.

## Source connector

`sqlite.table("name")` becomes a built-in source connector of
explicit-module projects too. It reads no catalog, file or environment, and
`pietto fmt` keeps its spelling byte for byte.

- A project `sqlite.table` call without exactly one argument, with a
  non-`Text` argument such as `1`, or with a `Text` argument that is not a
  non-empty string literal, such as `""` or `concat("a", "b")`, is
  `PIE-S2306` `Invalid source connector arguments for sqlite.table`, on the
  call, by the rule `mysql.table` and `duckdb.arrow` follow today; an
  argument whose type is unknown reports only its own diagnostic, as for
  them. Such a source is not a static source, so no emission admits it.
  This argument rule applies in explicit-module projects only.
- A project's `check` takes the table's physical name from the emission
  contract, as for `postgres.table` and `mysql.table`, so it does not run the
  single-file check of the string's form. A name with a dot, which a single
  file refuses at `check`, is refused by project emission instead (rule 26),
  so the same source never names different tables in the two modes.
- In a single file nothing changes. In a legacy-flat (`schema_version = 1`)
  project `sqlite.table` stays unknown: `PIE-S2306` `Unknown source
  connector: sqlite.table`, unchanged.
- The connector's string and the contract's `relation.name` are one
  identity: emission requires them to be equal, by exact string equality
  (rule 27), and S11's execution reads that one table.

## Emission contract values

A SQLite contract is a `pietto.emission-contract.v1` document with these
values. Everything else keeps the rules of
[project emission](../project-package.md#emission-contract-values).

| Member | SQLite value |
| --- | --- |
| `target` | `{"family": "sqlite", "release": "3.53.1"}`. The family must equal `--dialect`, or the command fails with `emission_contract_schema`; another release is BLOCKED with `PIE-B1003` `target_release_not_reviewed`. The release names the reviewed library; it is not the qualified build, which its source id and compile options identify with it (D78.03), and a contract cannot name a build. |
| `sources[].relation` | *Derived:* `{"namespace": "main", "name": NAME}`, where `NAME` is the `sqlite.table` string. Another namespace, or a name that holds a dot or NUL or starts with `sqlite_` in any ASCII case, is BLOCKED with `PIE-B1001` `source_identifier_unrepresentable` (SQLite reserves `sqlite_` names, so no `STRICT` user table has one); a name other than the connector's string with `PIE-B1001` `sqlite_table_name_mismatch`. |
| `sources[].scan` | *Derived:* `"relation_rows"`, as on PostgreSQL and MySQL. Another value fails with `emission_contract_schema` at `sources/N/scan`. |
| `sources[].fields[].column` | The column of the table that the source field reads. A `column` equal to an earlier one of the same source fails with `emission_contract_schema`, as on DuckDB. SQLite matches names without ASCII case, so a `column` equal to an earlier one only under ASCII case folding (`A` to `Z` against `a` to `z`; other letters stay distinct, as in SQLite), or one that holds NUL, is BLOCKED with `PIE-B1001` `column_identifier_unrepresentable_or_colliding`. Every shape field is described once, in shape order, as on the other targets (`complete_ordered_source_schema_required`). |

Each source field's `representation` (*derived*):

| Logical type | `storage` | Column it names | `domain` |
| --- | --- | --- | --- |
| `Int` | `sqlite_integer` | a `STRICT` table column declared `INTEGER` or `INT` | `int_range`, with string `min` and `max` inside signed 64 bits |
| `Bool` | `sqlite_bool01` | a `STRICT` table column declared `INTEGER` or `INT` that holds 0, 1 or NULL | `bool01` |
| `Text` | `sqlite_text` | a `STRICT` table column declared `TEXT` | `text`, with `max_characters`, `encoding` `UTF-8`, `collation` `BINARY` and `padding` `NO PAD` |
| `Float` | `sqlite_real` | a `STRICT` table column declared `REAL` | `finite_float`, with `format` `binary64` |

The storage objects have only their `kind`. `nullable` is `false` for a
non-null field and `true` for an optional one. A `nullable` that does not fit
the field is BLOCKED with `PIE-B1002` `nullability_mismatch`, and a storage
or domain that does not fit its logical type with `PIE-B1002`
`physical_storage_or_domain_mismatch`, the details the other targets use. The
`Text` collation `BINARY` names the comparison that the SQL writes
explicitly (see [SQL](#sql)), not the column's declared collation, which
SQLite does not report and the SQL overrides. `ANY` and `BLOB` columns have no
storage kind.

The `int_range` of an `Int` field is the range evidence of the project
`avg(Int)` rule of the [language guide](../language.md#aggregates-and-grouping),
so `avg_int_range_evidence_missing` does not arise on SQLite in this tier,
and it is the evidence that admits `sum` (rule 35).

Premises (*derived*):

| Key | Scope | SQLite value | Needed |
| --- | --- | --- | --- |
| `row_domain_matches` | source | `true` | always; otherwise `PIE-B1001`. Execution checks it ([execution](#execution)). |
| `read_only_object` | source | `true` | always; otherwise `PIE-B1001` |
| `client_encoding` | statement | `"UTF-8"`: the database encoding, as `PRAGMA encoding` names it | always |
| `operator_environment` | statement | `"builtin_only"` | when the SQL computes more than the selected columns: a `where`, `group by`, aggregate, `having`, `order by`, `limit`, or a literal, parameter or comparison in `select` |
| `parameter_protocol` | statement | `"sqlite_prepared"` | when the statement reads a parameter |
| `resource_limits` | statement | as today | optional |

A needed premise that is missing is BLOCKED with `PIE-B1004`, and one with
another value with `PIE-B1005`, as today. The field premises (`value_domain`,
`encoding`, `collation`, `padding`, `comparison_prefix_bytes`) stay optional
and must agree with the field's domain. `identifier_case`,
`session_sql_mode` and `session_time_zone` are BLOCKED on a SQLite contract
with `PIE-B1003` `premise_not_admitted_on_target`, once, at the first such
declaration: SQLite matches every identifier, quoted or not, without ASCII
case and no setting changes that, the SQL names no stage of its own beyond
the alias `s0` (see [SQL](#sql)), and it reads no session mode or time zone.

The SQLite limits are Pietto's, inside the measured build's compile options.
`sql_bytes` 8 MiB, `artifact_bytes` 16 MiB and `nodes` 32,768 are as on the
other targets. `columns` is 2,000 and `parameters` 32,766 (*derived*), the
build's `MAX_COLUMN` and `MAX_VARIABLE_NUMBER`. An expression of the SQL AST
nests at most 500 levels deep (*derived*), half the build's
`MAX_EXPR_DEPTH=1000`, a margin for the nodes that SQLite adds, such as
`COLLATE`. `resource_limits` may only lower the first five.

## SQL

S08 and S10 own the exact bytes and their goldens; any form they write
satisfies these rules (AD78.03: the adapter has its own SQL AST, renderer and
artifact verifier, and consumes `ProjectSQLPlan`).

- One `SELECT` statement with no `WITH`, subquery or second statement, its
  clauses in the order `SELECT`, `FROM`, `WHERE`, `GROUP BY`, `HAVING`,
  `ORDER BY`, `LIMIT`.
- Every identifier is quoted in backticks, a backtick inside doubled: SQLite
  reads a double-quoted name that names no column as text, a backticked one
  never.
- The one `FROM` item is `` `main`.`<table>` AS `s0` ``, and every column is
  written `` `s0`.`<column>` ``. A qualified name never reads an output
  alias or a `WITH` name, so a label or a table named like a column cannot
  change what the SQL reads.
- Each result field is written `` <expression> AS `<label>` ``, in result
  order.
- Each `Text` comparison writes `COLLATE BINARY` after its left operand, and
  each `Text` `GROUP BY` key, `ORDER BY` key and `count_distinct` argument
  after itself, as in `` COUNT(DISTINCT `s0`.`name` COLLATE BINARY) ``, so a
  `COLLATE NOCASE` column still compares by its bytes (PL.47). `min` and
  `max` of a `Text`, which `check` refuses on every target, never reach the
  SQL.
- Each ascending key ends with `ASC NULLS LAST` and each descending one with
  `DESC NULLS FIRST`, the NULL place that the PostgreSQL emitter keeps
  (D78.02).
- `count()` is `COUNT(*)`, `count(x)` is `COUNT(x)`, `min` and `max` are
  `MIN(x)` and `MAX(x)`, `avg(x)` is `AVG(CAST(x AS REAL))`, by the language's
  rule that an `Int` is cast to the target's binary64 before it is averaged,
  and `sum(x)` is `SUM(x)`.
- Literals are written as single files write them: `TRUE` and `FALSE`, an
  unsigned `Int`, an unsigned finite `Float` and a single-quoted `Text` with
  each quote doubled. A `Text` literal that holds NUL is refused (rule 9).
- Each parameter has one number, from 1 in the order of its first read in the
  SQL, and each read is written `?N` with it.
- The artifact's `target` is the contract target. A SQL AST or a document
  that breaks any rule above is BLOCKED with `PIE-B1008` (rules 36 and 38 of
  [compile refusals](#compile-refusals)).

The VERIFIED document is the `pietto.sql-emission.v1` envelope, or `v2` when
the selected query declares header parameters, as
[project CLI JSON v2](project-cli-json-v2.md#emit-sql-result) states, with
these SQLite values: `fixed_values` and `binding_obligations` are empty;
`parameter_uses` has one entry per rendered read, in occurrence order, each
with its parameter's `server_index` N above and the `physical_type` of its
type's storage kind (`sqlite_integer`, `sqlite_bool01`, `sqlite_text` or
`sqlite_real`), so a parameter read twice has two entries with one N;
`requirements` lists the plan's original demands with their target evidence
under the rule `sqlite_b2` and, as v2 requires, the generated
`query_parameter` requirement (rule `R04`) of each rendered read; and
`ranges` cover the statement byte for byte, in order. S08 fixes each column's
`correspondence` by the v1 rules and adds it here.

## Differences from PostgreSQL and MySQL

The facts are observations of S05, at Gate 0 on the measured build under
CPython 3.13.13 and 3.12.13 with identical results, unless a row says
*inferred* or names another source. Each row states what this tier does
about it.

| Difference | Fact on the measured build | Handling |
| --- | --- | --- |
| Type affinity | A table that is not `STRICT` converts values by column affinity (*inferred* from SQLite's documentation; S05 measured `STRICT` tables only); a `STRICT` `ANY` column takes any value | The storage kinds name `STRICT` columns of the four declared types; `ANY` and `BLOB` have none. Emission assumes it (`row_domain_matches`); execution checks the table and its column types |
| `Int` overflow outside `sum` | `9223372036854775807 + 1` gives a `REAL`; `abs(-9223372036854775808)` fails with `integer overflow` | Arithmetic is refused (rule 9); `check` bounds literals to signed 64 bits (`PIE-S2364`) |
| `sum` overflow | `sum()` fails with `integer overflow` (`SQLITE_ERROR`, code 1) as soon as a partial sum leaves signed 64 bits, even when the result is inside them, so the scan order decides: `[MAX, 1, -1]` fails and the reverse gives `MAX`, and an index on the column changes the plan and so the result. Over values of one sign it failed exactly when the result left signed 64 bits, in all 5,334 random cases; over mixed signs 470 of 2,666 failed with the result inside; no wrong value was returned | `sum` of an `Int` only when the contract's `int_range` lies on one side of zero: then every partial sum lies between zero and the result (*derived*), so SQLite fails exactly when PostgreSQL's exact sum raises SQLSTATE 22003, and never returns a wrong value. A mixed range is `PIE-B1004` `sum_int_aggregate_range_proof_missing` (rule 35); single files keep `sum` refused |
| Collation | A column may be `COLLATE NOCASE`; `PRAGMA table_xinfo` does not report a column's collation. With `COLLATE BINARY` written, comparisons, `ORDER BY`, `GROUP BY`, `HAVING`, `count(distinct ...)`, `min` and `max` compare bytes, on either side of a comparison | Project SQL writes `COLLATE BINARY` (see [SQL](#sql)); single files keep the `BINARY` premise |
| Encoding | A database may be `UTF-16le`, and `PRAGMA encoding` reports it | Emission assumes UTF-8 (`client_encoding` `"UTF-8"`); execution checks `PRAGMA encoding` |
| Identifier case | Every identifier, quoted or not, matches without ASCII case: `"a"` and `"A"` are one column, tables `IC` and `ic` one table | Columns that collide under ASCII case folding are refused (rule 31); the relation name must equal the connector's string exactly (rule 27); the SQL names only the alias `s0` and qualified columns; `identifier_case` is not admitted |
| NULL order | Ascending order puts NULL first by default; explicit `NULLS FIRST` and `NULLS LAST` hold in all four combinations | Explicit NULLS clauses, as D78.02 decided for single files (lead, stated to the owner in PL.47) |
| `-0.0` | A `STRICT` `REAL` column stores `-0.0` as `0.0`. A bound `-0.0` keeps its sign as a value, also through `abs`, and loses it when cast to text; `GROUP BY` puts both zeros in one group and keeps the first; `count(distinct ...)` counts them once | No stored value is a negative zero. A projected `Float` parameter returns `-0.0` as Pietto's value does; this tier has no `abs`, no cast to text and no `count_distinct` of a `Float` |
| `Bool` | A `STRICT` `INTEGER` column stores 2 and -1 | Emission assumes 0 and 1 (`bool01`, `row_domain_matches`); execution checks each value |
| NaN and infinities | A bound NaN becomes NULL; a `REAL` column stores ±Infinity | Execution refuses a NaN or infinite `Float` parameter before it binds and checks each stored value; emission assumes finite values (`finite_float`) |
| NUL in `Text` | A `TEXT` value may hold NUL, and `length` counts only up to it; invalid UTF-8 is stored too, and no SQL form detects it | No form reads `length`; a `Text` literal with NUL is refused (rule 9); execution refuses a stored NUL and decodes each `Text` value in Python |
| `avg` rounding | `AVG(CAST(x AS REAL))` equalled compensated summation (`math.fsum`) divided by the count in 400 of 400 random cases, whatever the scan order, and plain left-to-right summation in 221; under cancellation it differs by more than the last bit (`[1, 2^53, -2^53]` gives 1/3 where plain summation gives 0). PostgreSQL's plain summation is *inferred*, not measured | The language leaves the summation of a binary64 average to the target, so the result may differ from PostgreSQL and MySQL in the last bits, or more under cancellation (*derived*; see [open items](#open-items)). Qualification compares with `fsum` divided by the count, or uses data whose sum does not depend on the order |
| `HAVING` and bare columns | `HAVING` runs without `GROUP BY` and may read an output alias or a column that is not grouped, and a `SELECT` of an aggregated query may read a column that is not grouped (PostgreSQL refusing these is *inferred*) | The SQL writes only aggregates, qualified `group by` keys, literals and parameters there, and the projection rule refuses other fields (rule 11) |
| Quoted names | A double-quoted name that names no column reads as text (a B1 Q0 cell; see the route's [B2 handoff](../phases/phase-78/route.md#b2-handoff)) | Backtick quoting |
| `LIKE` | `LIKE` folds ASCII case; the build has no ICU | Not opened |

## Compile refusals

A SQLite emission reports only the blockers of the table below, and no other
`PIE-B10xx` detail (*derived*). A contract that breaks its schema is still
`INPUT_REJECTED` with `emission_contract_schema` and has no blockers.
Emission first runs `check --project`, then the one existing verification of
the project SQL plan, then reads the contract, then checks these rules:

- Rules 1–35 are checked together. The document lists one blocker for each
  rule that fails, in rule order, and none for a rule that holds.
- A rule that fails at several sites reports the first one only: source,
  stage and expression sites in source order (path, line, column), source
  fields in shape order, and premises in contract order (`environment`, then
  each source's `premises`, in `sources` order).
- A rule whose subject is absent holds: rules 12–14 need their clause, rule
  18 a parameter read, rules 25–34 a contract entry for the read source, and
  rule 35 a `sum` whose field passes rule 33.
- When the plan is unavailable, rule 5 reports at the plan's first blocker,
  and rules 6–35 are not checked.
- Rule 20 counts the nodes and the expression depth of the SQL AST that the
  adapter will build, from the plan and before anything is built. A built AST
  with another count does not correspond to the plan (rule 36).
- Only when rules 1–35 all hold is the SQL built, verified, rendered and put
  in its document; then the first of rules 36–39 that fails is the only
  blocker.

"Existing" names the suggestion text that the other targets give the same
detail today, with no family. A suggestion "by the premise rule" is the
existing text for that premise detail with the SQLite value of the premise
table in it.

| # | Code | Detail | Fails when | Site | Suggestion |
| ---: | --- | --- | --- | --- | --- |
| 1 | `PIE-B1005` | `inconsistent_declared_scope` | Two declarations of one premise key in one scope have different values | The later declaration | Existing |
| 2 | `PIE-B1003` | `target_release_not_reviewed` | `target.release` is not `"3.53.1"` | None, as today | `the reviewed sqlite release is "3.53.1"` |
| 3 | `PIE-B1003` | `literal_policy_not_admitted_on_target` | The literal policy is not `preserve` | The statement | `SQLite emission takes --literal-policy preserve only` |
| 4 | `PIE-B1003` | `premise_not_admitted_on_target` | An `identifier_case`, `session_sql_mode` or `session_time_zone` premise is declared | The declaration | `remove this premise; SQLite project SQL does not use it` |
| 5 | `PIE-B1003` | `sqlite_relation_shape_not_admitted` | The plan is unavailable, or the statement has a stage beyond one source read, its `where` filter, a `group by`, a `having`, an `order by`, a `limit` and its final projection | The first such stage | `SQLite emission admits one source read with where, group by, having, order by, limit and select; JOINs, windows, qualify, distinct, set operations, relation lets and reads of another table or query are not available on SQLite` |
| 6 | `PIE-B1003` | `sqlite_source_count_not_admitted` | The statement reads no source, or more than one | The second source read, or the statement | `read exactly one sqlite.table source` |
| 7 | `PIE-B1003` | `sqlite_field_type_not_admitted` | A field of the read source is not established as `Int`, `Text`, `Bool` or `Float`, optional or not | The source field | `SQLite emission reads Int, Text, Bool and Float fields` |
| 8 | `PIE-B1003` | `sqlite_parameter_not_admitted` | A header parameter's type is not `Int`, `Text`, `Bool` or `Float` | The parameter declaration | `declare Int, Text, Bool or Float parameters, with or without None` |
| 9 | `PIE-B1003` | `sqlite_expression_not_admitted` | An expression in `select`, `where` or `having` is outside the expressions of [admission](#admission), or is a `Text` literal that holds NUL | The expression | `use fields, literals, parameters, comparisons of two values of one type, and, or, not and is None; arithmetic, signs, in, ranges, conditionals, casts and function calls are not available on SQLite` |
| 10 | `PIE-B1003` | `sqlite_aggregate_not_admitted` | An aggregate is outside the aggregates of [admission](#admission), reads anything but one field of the source directly, or appears anywhere but as a whole result field, a `having` operand or an `order by` key | The aggregate | `use count, count_distinct of an Int, Text or Bool field, min or max of an Int or Float field, or avg or sum of an Int field, each over one field of the source` |
| 11 | `PIE-B1003` | `sqlite_projection_not_admitted` | In an aggregated relation, a result field is not a `group by` key, an admitted aggregate, a literal or a parameter | The result field | `in a relation with group by or an aggregate, select group by keys, aggregates, literals and parameters` |
| 12 | `PIE-B1003` | `sqlite_group_key_not_admitted` | A `group by` key is not a field of the source | The key | `group by fields of the source` |
| 13 | `PIE-B1003` | `sqlite_order_not_admitted` | An `order by` key is not a field of the source, or, in an aggregated relation, not a selected `group by` key or aggregate | The key | `order by fields of the source, or, with group by or an aggregate, by selected keys and aggregates` |
| 14 | `PIE-B1003` | `sqlite_limit_not_admitted` | The `limit` is not an `Int` literal from 0 to 9223372036854775807 | The `limit` | `write limit as an Int literal` |
| 15 | `PIE-B1005` | `target_evidence_scope_conflict` | As on the other targets | As today | Existing |
| 16 | `PIE-B1006` | `original_profile_composition_unresolved` | As on the other targets | As today | Existing |
| 17 | `PIE-B1004`; `PIE-B1005` | `operator_environment_declaration_missing`; `operator_environment_declaration_mismatch` | The statement-scope premise is needed and missing; it has another value than `"builtin_only"` | The statement | By the premise rule |
| 18 | `PIE-B1004`; `PIE-B1005` | `parameter_protocol_declaration_missing`; `parameter_protocol_declaration_mismatch` | The statement-scope premise is missing; it has another value than `"sqlite_prepared"` | The statement | By the premise rule |
| 19 | `PIE-B1007` | `parameter_occurrence_limit` | The placeholders exceed the `parameters` limit | The statement | Existing |
| 20 | `PIE-B1007` | `generated_structure_limit` | The read source or the result has more columns than the `columns` limit, or the SQL AST that the adapter will build has more nodes than `nodes` or an expression deeper than 500 levels, counted from the plan | The statement | Existing |
| 21 | `PIE-B1006` | `negative_original_target_evidence` | As on the other targets | As today | Existing |
| 22 | `PIE-B1006` | `original_enforcement_not_fulfilled` | As on the other targets | As today | Existing |
| 23 | `PIE-B1001` | `source_family_mismatch` | A read source is not a `sqlite.table` source | The source | Existing |
| 24 | `PIE-B1001` | `source_mapping_missing` | A read source has no contract entry | The source | Existing |
| 25 | `PIE-B1001` | `complete_ordered_source_schema_required` | The entry does not describe every shape field once, in shape order; `related` lists the fields left out or out of order, as today | The source | Existing |
| 26 | `PIE-B1001` | `source_identifier_unrepresentable` | `relation.namespace` is not `"main"`, or `relation.name` holds a dot or NUL or starts with `sqlite_` in any ASCII case | The source | `use the relation namespace "main" and a bare table name with no dot or NUL that does not start with sqlite_` |
| 27 | `PIE-B1001` | `sqlite_table_name_mismatch` | `relation.name` is not the connector's string | The source | `make the contract relation name equal the sqlite.table name` |
| 28 | `PIE-B1001` | `row_domain_matches_declaration_required` | The premise is missing or not `true` | The source | Existing |
| 29 | `PIE-B1001` | `read_only_object_declaration_required` | The premise is missing or not `true` | The source | Existing |
| 30 | `PIE-B1004`; `PIE-B1005` | `client_encoding_declaration_missing`; `client_encoding_mismatch` | The premise is missing; it has another value than `"UTF-8"` | The source | By the premise rule |
| 31 | `PIE-B1001` | `column_identifier_unrepresentable_or_colliding` | A field's `column` holds NUL, or equals an earlier `column` of the source under ASCII case folding | The source field | `map each field to its own column; SQLite matches column names without ASCII case, so "A" and "a" are one column` |
| 32 | `PIE-B1002` | `nullability_mismatch` | A field's `nullable` does not fit the field | The source field | `set nullable to false for a non-null field and true for an optional one` |
| 33 | `PIE-B1002` | `physical_storage_or_domain_mismatch` | A field's `storage` or `domain` is not its logical type's row of the representation table | The source field | `use the SQLite storage and domain of the field's logical type` |
| 34 | `PIE-B1005` | `field_domain_premise_mismatch` | A field premise disagrees with the field's `domain` | The source field | Existing |
| 35 | `PIE-B1004` | `sum_int_aggregate_range_proof_missing` | A `sum` reads an `Int` field whose `int_range` has a negative `min` and a positive `max` | The aggregate | `declare an int_range on one side of zero, or keep this sum in check/plan: SQLite can fail a sum over values of both signs whose result fits` |
| 36 | `PIE-B1008` | `plan_ast_correspondence` | The SQL AST breaks a rule of [SQL](#sql) or does not correspond to the plan | None | Existing |
| 37 | `PIE-B1007` | `sql_byte_limit` | The rendered SQL exceeds `sql_bytes` | None | Existing |
| 38 | `PIE-B1008` | `artifact_correspondence` | The artifact verifier refuses the document | None | Existing |
| 39 | `PIE-B1007` | `public_artifact_byte_limit` | The public document exceeds `artifact_bytes` | None | Existing |

PostgreSQL and MySQL emission of a `sqlite.table` source is BLOCKED with
`PIE-B1001` `source_family_mismatch` where those emitters place that detail
today, beside `PIE-B1006` `negative_original_target_evidence`, among their
other blockers in their existing order, as for a `duckdb.arrow` source;
DuckDB emission of a `sqlite.table` source is its rule 19, and SQLite
emission of a `postgres.table`, `mysql.table` or `duckdb.arrow` source is
rule 23 above.

`compile_sql` and `compile_all_sql` return the document, byte for byte what
the command prints. A verified document's bytes come only from the adapter.

## Other entry points

- Until S11, `compile_query(dialect="sqlite")` keeps `PIE-R1002`, so no
  query bundle, saved result, relay, job or R2 path meets a SQLite query; S11
  states each of their refusals.
- `pietto explain --project` and every inspection stay non-executing and
  dialect-neutral, and no SQLite catalog is inspected.
- `pietto lsp` reports what `check` reports, so a project `sqlite.table`
  stops being `PIE-S2306` there too.

## Execution

S11 writes this section: the `sqlite_file` route that PL.47 approves, as
tier 1b. Its bounds are fixed there: a read-only open of the caller's file
behind eleven defences, sources that are `STRICT` tables and not views,
virtual or temporary tables, UTF-8, a file of at most 256 MiB, at most
1,048,576 rows per source table, the whole attempt within
`ExecutionLimits.seconds` (by default 20 seconds), results under the
`ExecutionLimits` defaults, the `arrow` extra reused, and a bounded check of
each source's value domains and of table and index integrity in the same
read transaction before each run, which refuses `Text` that holds NUL.
Until S11 lands, Pietto runs no SQLite statement and opens no SQLite file.

S05 observed these facts on the measured build; S11 implements each, and S12
gives each a control cell:

- **Opening.** The URI is `Path.resolve().as_uri()` with `?mode=ro`, never a
  plain `"file:" + path` and never `immutable=1`: plain concatenation let a
  file named `weird?mode=rwc&immutable=1#frag.db` open, and create, a file
  `weird` with those parameters, and an `immutable=1` reader ignored locks
  and kept reading the old rows after a writer committed. `mode=ro` creates
  no missing file. A 0-byte file and `/dev/null` open as an empty database,
  so the path must be a regular file and a missing source table is refused.
- **Size.** The 256 MiB cap counts the database file and its `-wal` file
  together when one exists; a `-wal` file may be far larger than the main
  file (10,304,152 bytes beside 4,096).
- **Time.** Python's default busy timeout waited 5.01 s on a locked file, so
  the timeout is set explicitly and counted inside `ExecutionLimits.seconds`.
- **Read transaction.** In WAL mode a read transaction keeps its data and
  schema while a writer inserts, alters or drops. In rollback-journal mode
  it makes the caller's own writers fail with `database is locked` while it
  lasts; the execution documentation states this.
- **Authorizer.** A `count(*)` or `rowid` read reaches the callback as a READ
  of the table with the column `''` and no database name (`None`), which an
  allowlist that requires `main` refuses, so the allowlist admits that shape
  for the source table. The callback answers only allow or DENY:
  `SQLITE_IGNORE` silently reads a column as NULL.
- **Objects.** A source column is declared `INT`, `INTEGER`, `REAL` or
  `TEXT`, as the representation table requires; `ANY`, `BLOB` and a
  generated column (`hidden` 2 or 3 in `PRAGMA table_xinfo`) are refused. A
  broken view elsewhere in the file leaves `PRAGMA table_list(t)` and
  `PRAGMA integrity_check(t)` working.
- **Values.** `instr(x, char(0)) > 0` finds a NUL in `Text`, and no SQL form
  detects invalid UTF-8, so each `Text` value is decoded in Python.
  `integrity_check(t)` finds a planted index fault that `quick_check(t)`
  misses and that makes a query return wrong rows.
- **Errors.** A native error is named by `sqlite_errorcode`, extended code
  included, and by its message where the code is not enough, never by
  `sqlite_errorname` alone: a `STRICT` type error is named `unknown` (code
  3091), and a `sum` overflow is `SQLITE_ERROR` (code 1) with the message
  `integer overflow`.

## Qualification

Qualification is in process on the measured build (D78.03, PL.47): native
cells in `tests/test_sql_sqlite_native.py` over `:memory:` or test-owned
files, against oracles written before the run, under CPython 3.13.13 and
3.12.13, with a coverage law read from the adapter's vocabulary, so a form
without a passing cell ships refused. One PostgreSQL replay campaign, R1,
covers the new project bytes of T1 and every T2 form under D78.08's
conditions and the method of D78.10 and D78.11, on one PostgreSQL slot; its
`avg` entries pass on data whose sum does not depend on the order, and a
cancelling case is recorded as an observed difference, not a failure. The
route's [qualification rules](../phases/phase-78/route.md#b2-qualification-and-replay)
hold the rest. Hosted CI asserts the refusal of the native classes and runs
the byte and golden tests everywhere.

## Usability

| Spelling | Canonical form | Works with | Errors | Discoverability |
| --- | --- | --- | --- | --- |
| `source orders: Order = sqlite.table("orders")` in an explicit-module module | As written; `pietto fmt` keeps it byte for byte | `check --project`; `emit-sql --project --dialect sqlite`; `compile_sql`, `compile_all_sql` | Not one non-empty string literal: `PIE-S2306` `Invalid source connector arguments for sqlite.table`. A legacy-flat project: `PIE-S2306` `Unknown source connector: sqlite.table`. Another dialect: `PIE-B1001` `source_family_mismatch`. An unsupported form: `PIE-B1003` with a detail and suggestion above | The source connectors of the language guide, this page, the capability page's SQLite section and the release notes |

## Shared-page hunks

The slice that lands a behavior applies its hunks to the shared pages at
integration, one page at a time, in the route's single-writer order.

- S07: `docs/language.md` and `docs/capabilities.md`, the sentences that a
  project's check refuses `sqlite.table` with `PIE-S2306`, which become that
  a project's check accepts it and that PostgreSQL, MySQL and DuckDB emission
  refuse it; the release-note fragment records the `check --project` change.
- S08: `docs/project-package.md`, `--dialect {postgres,mysql,duckdb,sqlite}`
  and the SQLite columns of the contract value and premise tables;
  `docs/spec/project-cli-json-v2.md`, `sqlite` as a `dialect` value;
  `docs/language.md`, `sqlite.table` among the project source connectors and
  a SQLite project section in place of S07's sentence;
  `docs/capabilities.md`, the project row of its SQLite section; `README.md`,
  project mode in its SQLite entry;
  `docs/spec/diagnostics.md`, the `PIE-S2306`, `PIE-B1001` and `PIE-B1003`
  rows naming the details above, at a time the lead schedules apart from
  Phase81's diagnostic review (P03, PL.58); and the CLI usage strings.
- S10: `docs/language.md`, the single-file aggregates, `having` and the
  `avg` rounding; `docs/capabilities.md`, the SQLite table;
  `docs/spec/diagnostics.md`, the `PIE-B1004` row naming SQLite's
  `sum_int_aggregate_range_proof_missing`.
- S11: the execution pages, which its section names.

## Open items

| Item | Owner | Latest point |
| --- | --- | --- |
| This page's *derived* rows, stated as inform: the `main` namespace, the `sqlite_` and dot refusals and `sqlite_table_name_mismatch`; the `relation_rows` scan; the storage kinds and domain spellings (`UTF-8`, `BINARY`); the premise values and `premise_not_admitted_on_target`; the limits `columns` 2,000, `parameters` 32,766 and the depth 500; the SQL rules (`s0`, backticks, `?N`); the closed order of compile refusals with its new details and suggestions; the two new single-file reasons | The lead | Before this page binds, at the latest before S08 seals |
| The `avg(Int)` rounding row: S05 found it within the existing rules (the target sums a binary64 average) and recommended that the lead decide and inform the owner, as for the NULL order; the owner is asked only if a claim of bitwise equality with PostgreSQL or SQL that imitates plain summation is wanted | The lead | Before S10 seals; this page and S10's `language.md` text follow the ruling |
| Rules 5–14 follow the plan's structure as S08 and S10 find it: a slice may move a site or split a condition between these rules, editing this page in the same commit, but adds no detail or text outside these tables | S08, S10 | Before each seals |
| Whether the value check of S11 also checks each `Text` value's `max_characters`, which the domain states and Q6b's list does not name | S11 | Before S11 seals |
| The release-note fragment `78-s06-sqlite-project-mode.md` describes tier 1a as its batch delivers it; S07 to S10 edit their lines there and add no second 1a fragment; S11 writes its own fragment for 1b | Each slice; the batch audit | Before each slice seals; the 1a batch audit compares the fragment with this page |
| Whether `sqlite.table` changes the built-in catalog (D76.12): it adds no grammar and no catalog entry, so no extension sync is expected | S07 | Before the 1a batch push |
