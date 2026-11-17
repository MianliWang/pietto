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

The second tier opens three forms under the owner's answers to its own
Gate 1 of 2026-11-17 (D78.14): range-proved `Int` arithmetic (S14), windows
over one source read (S15), and INNER and LEFT JOINs of `sqlite.table`
sources with their execution on the `sqlite_file` route (S13a, S13b). Each
form ships refused until its native cells pass and its replay (R2 for S14
and S15, R3 for S13) ends `PASS`, or, for a form that PostgreSQL project
emission does not write, until the owner rules on it (D78.15). The tier's
two batches are pushed after
the `0.2.2` release commit (PL.64 (3)), and the route's
[second tier](../phases/phase-78/route.md#b2-second-tier) holds its slices.

Construction state: FIRST TIER QUALIFIED. S06 wrote this page before any B2 code.
S07 added the shared connector entry and the three family mappings, so a
project's `check` accepts a `sqlite.table` source and PostgreSQL, MySQL and
DuckDB emission refuse it as [compile refusals](#compile-refusals) states.
S08 added the adapter and the T1 forms, so `emit-sql --project --dialect
sqlite`, `compile_sql` and `compile_all_sql` emit them. S09 added their native
qualification under CPython 3.13.13 and 3.12.13. S10 added the T2
aggregates in both modes with their native cells. S11 added
`compile_query(dialect="sqlite")` and the `sqlite_file` route of
[execution](#execution). S12 added the route's native qualification and,
by its timing, the file cap of 128 MiB. R1 added the PostgreSQL replay,
which passed, and S16 closed the tier; the second tier has its own
Gate 1 (PL.54, PL.58, D78.14). In the second tier, S14 added range-proved
`Int` arithmetic (D78.14 (3), rule 9b). Each slice edits the rows it lands.
No published release carries a form until the owner approves
one: `0.2.1` and earlier refuse a project `sqlite.table` with `PIE-S2306`
`Unknown source connector: sqlite.table`.

## Admission

| Admission | Exact limit |
| --- | --- |
| Project and source | An explicit-module project (`schema_version = 2`) whose statement reads exactly one source declared `source x: Shape = sqlite.table("name")`. |
| Relational shape | One source read, its `where` filter, a `group by`, a `having`, an `order by`, a `limit`, and the final projection. No JOIN, window or `qualify`, relation `let`, read of another table or query, `distinct`, set operation, typed VALUES body or table function. |
| Columns | Source fields are `Int`, `Text`, `Bool` or `Float`, each with its compiled nullability. Results follow the projection. |
| Expressions | In `select`, `where` and `having`: a field of the source, a literal, a query parameter, a comparison (`==`, `!=`, `<`, `<=`, `>`, `>=`) of two values of one type, `and`, `or`, `not`, `is None` and `is not None`; in `having` and in the `select` of an aggregated relation also an admitted aggregate. In `select` and `where` also `Int` arithmetic (S14): `+`, `-`, `*`, unary `-` and `abs(x)`, whose operands are `Int` fields of the source, `Int` literals and such arithmetic, when the bounds of every result lie inside signed 64 bits (rule 9b). `check` refuses arithmetic in `having` (PIE-S2327) and arithmetic over `group by` keys in the `select` of an aggregated relation that selects no aggregate (PIE-S2319); beside an aggregate, rules 9 and 11 refuse such arithmetic. Arithmetic that reads an aggregate passes `check`, and rule 9 refuses it, beside rules 10 and 11. No arithmetic that reads a parameter or an aggregate, no `Float` arithmetic, `/`, `%` or unary `+`, no `in`, range comparison, conditional, cast, other function call or `any(...)` read, and no `None` literal outside `is None` and `is not None`. |
| Aggregates | `count()` and `count(x)`; `count_distinct(x)` of an `Int`, `Text` or `Bool` field; `min(x)` and `max(x)` of an `Int` or `Float` field; `avg(x)` of an `Int` field or of admitted `Int` arithmetic (S14); and `sum(x)` of the same whose bounds lie on one side of zero (a field's contract `int_range` with a `min` of 0 or more or a `max` of 0 or less, or arithmetic whose bounds do, rule 35). Each other aggregate reads one field of the source directly; `check` refuses `abs` in an aggregate's argument and `min` and `max` of an expression on every target (PIE-S2315). |
| Grouping and order | A `group by` key is a field of the source. In an aggregated relation a result field is a `group by` key, an admitted aggregate or a literal (`check` refuses a query parameter there with `PIE-S2355`), and an `order by` key is a selected `group by` key or aggregate; elsewhere an `order by` key is a field of the source. A `limit` is an `Int` literal from 0 to 9223372036854775807. |
| Parameters | Query header parameters of type `Int`, `Text`, `Bool` or `Float`, optional or not, read in `select`, `where` or `having`. |
| Literal policy | `preserve` only. |
| Entry points | `pietto check --project`; `pietto emit-sql --project ... --dialect sqlite`, with or without `--all`; `compile_sql` and `compile_all_sql` with `dialect="sqlite"`; `compile_query` with `dialect="sqlite"`, and `execute` on the `sqlite_file` route ([execution](#execution)). |

`having`, `count_distinct`, `avg` and `sum` are the T2 forms that S10
landed. A `having` reads selected `group by` keys and aggregates by their
output names, literals and parameters, as `check` requires: it refuses a
field read (`PIE-S2325`), a direct aggregate call (`PIE-S2308`), `not` and
null tests (`PIE-S2327`) there, and a `having` without `group by`
(`PIE-S2323`).

Not in this tier: `Decimal`, `Date`, `Timestamp`, `UUID`, `Bytes`, `Json`,
enum and nested fields; `--literal-policy bind-safe`; arithmetic other than
that of the expressions row above, `Float` `sum` and `avg`, text functions
and `LIKE`, `string_agg`, `median` and `quantile`; JOINs and windows,
which a later Gate 1 decides at the B2 midpoint; schema-qualified or
attached tables; query bundles, saved results, relay, jobs and R2 recovery; and any
change to PostgreSQL, MySQL or DuckDB SQL bytes, contracts or diagnostics
beyond the refusal of a `sqlite.table` source that
[compile refusals](#compile-refusals) states. No claim of parity across
databases is made.

Of the JOINs, arithmetic and windows, the second tier (D78.14) opens only
the forms that its slices add to the table above, each when its slice
lands, and leaves these closed: RIGHT, FULL and CROSS JOINs, `any` and
`not any` reads, a JOIN to a query or relation `let`, an `on` other than
equalities of two fields of one type, `Float` JOIN keys, relationship
matches and single-match obligations; `Float` arithmetic, `/`, `%`,
arithmetic that reads a parameter and arithmetic under a run-time guard;
`qualify`, `lag`, `lead`, `ntile`, `first_value`, `last_value`,
`nth_value`, `percent_rank`, `cume_dist`, a window `avg`, named windows,
windows over grouped or joined rows, and a window `sum` in any frame other
than one from `UNBOUNDED PRECEDING` to `CURRENT ROW` or
`UNBOUNDED FOLLOWING`.

## Single files

S10 also opened three forms in `pietto emit-sql FILE --dialect sqlite`, by the
[SQLite single-file rules](../language.md#sqlite-single-files), which S10
edited: `having`, with the expressions of the table above over `group by` keys
and aggregates; `count_distinct` of an `Int`, `Text` or `Bool` field, written
`COUNT(DISTINCT x)`; and `avg` of an `Int` field, written
`AVG(CAST(x AS REAL))`. A single-file `HAVING` writes each key and aggregate
itself, and single-file SQL writes every `Bool` literal as `1` or `0`, both
as project SQL does. B1 wrote `TRUE` and `FALSE`, which SQLite reads as a
column of that name, in any letter case, when the table has one, and in
`WHERE` as an output so named, so a B1 statement could return wrong rows
where the table has a column so named or, in `where`, beside an output so
named. By the owner's ruling (PL.54) this changes published
single-file bytes and the reviewed single-file golden; a statement without a
`Bool` literal keeps its bytes. Single-file SQL keeps B1's premises, the
`BINARY` collation among them, and writes no `COLLATE`. A
file has no contract and no `int_range`, so `sum` of an `Int` stays refused
with its `PIE-B1000` reason, unchanged. The new single-file refusals keep the
existing `PIE-B1000` text, `SQLite SQL emission is not implemented for
RelationIR: <name>. <reason>`, with these reasons (*derived*):

| Form | Reason |
| --- | --- |
| `avg` of a `Float` field | `SQLite aggregate avg supports only Int fields` |
| `count_distinct` of a `Float` field | `SQLite aggregate count_distinct supports only Int, Text and Bool fields` |

A relation refused before with the reason `... no having yet`,
`... no aggregate count_distinct yet` or `... no aggregate avg yet` now
emits, or takes the reason of the first form still refused in the backend's
order, such as the field's type for `count_distinct` of a `Decimal` field.
Every other single-file reason stays as it is.

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
and it is the evidence that admits `sum` (rule 35) and arithmetic (rule 9b).

Premises (*derived*):

| Key | Scope | SQLite value | Needed |
| --- | --- | --- | --- |
| `row_domain_matches` | source | `true` | always; otherwise `PIE-B1001`. Execution checks it ([execution](#execution)). |
| `read_only_object` | source | `true` | always; otherwise `PIE-B1001` |
| `client_encoding` | statement | `"UTF-8"`: the database encoding, as `PRAGMA encoding` names it | always |
| `operator_environment` | statement | `"builtin_only"` | when the SQL computes more than the selected columns: a `where`, `group by`, aggregate, `having`, `order by`, `limit`, or a literal, parameter, comparison or arithmetic in `select` |
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

S08, S10 and S14 own the exact bytes and their goldens; any form they write
satisfies these rules (AD78.03: the adapter has its own SQL AST, renderer and
artifact verifier, and consumes `ProjectSQLPlan`).

- One `SELECT` statement with no `WITH`, subquery or second statement, its
  clauses in the order `SELECT`, `FROM`, `WHERE`, `GROUP BY`, `HAVING`,
  `ORDER BY`, `LIMIT`, on one line, separated by single spaces, with no final
  semicolon. An operand that is itself a comparison, arithmetic other than
  `abs`, `and`, `or`, `not` or null test is in parentheses.
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
- `count()` is `COUNT(*)`, `count(x)` is `COUNT(x)`, `count_distinct(x)` is
  `COUNT(DISTINCT x)`, `min` and `max` are `MIN(x)` and `MAX(x)`, `avg(x)` is
  `AVG(CAST(x AS REAL))`, by the language's rule that an `Int` is cast to the
  target's binary64 before it is averaged, and `sum(x)` is `SUM(x)`; the `x`
  of `avg` and `sum` may be arithmetic, as in `` SUM(`s0`.`a` * `s0`.`b`) ``.
- `+`, `-` and `*` are written between their operands, `abs(x)` as
  `ABS(x)`, and a unary `-` right before its operand, so a unary `-` before
  an `Int` literal is one signed literal: `-9223372036854775808` is the
  `INTEGER` minimum, while `0 - 9223372036854775808` reads as a `REAL`, so
  9223372036854775808 is refused anywhere but there (rule 9). A unary `-`
  before another one is written `-(-x)`, never `--`, which starts a comment.
- `HAVING` follows `GROUP BY` and holds only a `group by` key's column, an
  aggregate, a literal, a parameter, comparisons, `AND` and `OR`; a key or
  aggregate read by its output name is written as that key or aggregate,
  never as the name, which SQLite would read there as the output or as a
  column of that name.
- A `Bool` literal is written `1` or `0`: SQLite reads `TRUE` and `FALSE` as
  a column or result alias of that name when one exists, and the table may
  have columns that the contract does not name. Other literals are written
  as single files write them: an unsigned `Int`, an unsigned finite `Float`
  and a single-quoted `Text` with each quote doubled. A `Text` literal that
  holds NUL is refused (rule 9). No literal is a `GROUP BY` or `ORDER BY`
  key, where SQLite reads a number as a result position.
- Each parameter has one number, from 1 in the order of its first read in the
  SQL (`SELECT`, then `WHERE`, then `HAVING`), and each read is written `?N`
  with it.
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
`ranges` cover the statement byte for byte, in order, each with the plan
object it renders as its `subject`.

Each column has its export's logical type and nullability. A column that
reads a source field, selected directly or as a `group by` key, has that
field's contract `representation`; a `count` has the storage `sqlite_integer`
and the `int_range` 0 to 9223372036854775807; a `min` or `max` has its
field's storage and domain; a `count_distinct` is a `count`; and any other
value, arithmetic, an `avg` or a `sum` among them, has its type's storage kind
and the widest domain of its type (an `int_range` of signed 64 bits,
`bool01`, `finite_float`, or `text` with `max_characters` null), except that
an `Int` literal's range is its value and a `Text` literal's
`max_characters` is its length. Each column's `correspondence` names its
`export`, its `projection` (an aggregate projection in an aggregated
relation) and its `sql_symbol`, its position. A column that reads a source
field also names `source`, `field` and `source_port`, with the `input_port`
it reads outside aggregation or the `group_key` it is; an aggregate column
names its `aggregate`; and any other column names its select `expression`.

## Differences from PostgreSQL and MySQL

The facts are observations of S05, at Gate 0 on the measured build under
CPython 3.13.13 and 3.12.13 with identical results, unless a row says
*inferred* or names another source. Each row states what this tier does
about it.

| Difference | Fact on the measured build | Handling |
| --- | --- | --- |
| Type affinity | A table that is not `STRICT` converts values by column affinity (*inferred* from SQLite's documentation; S05 measured `STRICT` tables only); a `STRICT` `ANY` column takes any value | The storage kinds name `STRICT` columns of the four declared types; `ANY` and `BLOB` have none. Emission assumes it (`row_domain_matches`); execution checks the table and its column types |
| `Int` overflow outside `sum` | `9223372036854775807 + 1` gives a `REAL`; `abs(-9223372036854775808)` fails with `integer overflow`. S14's native cells saw a `+`, a binary or unary `-` and a `*` whose result leaves signed 64 bits give the `REAL` of the binary64 operation, without an error, `abs` of the minimum fail with `integer overflow`, and a `sum` of such a value give a `REAL` too, while each result at the bounds is the exact `INTEGER` | `Int` arithmetic only with a range proof (rule 9b): each field read contributes its contract `int_range`, each read on its own, and each literal its value, each operation's bounds follow from its operands', and the bounds of every result, an aggregate's argument row by row included, must lie inside signed 64 bits, so `abs` of bounds that hold the minimum is refused too. `check` bounds a single file's literals to signed 64 bits (`PIE-S2364`); in a project, rule 9 refuses 9223372036854775808 anywhere but right after a unary `-`. The `sqlite_file` route holds each value to its `int_range` before the statement runs ([execution](#execution)) |
| `sum` overflow | `sum()` fails with `integer overflow` (`SQLITE_ERROR`, code 1) as soon as a partial sum leaves signed 64 bits, even when the result is inside them, so the scan order decides: `[MAX, 1, -1]` fails and the reverse gives `MAX`, and an index on the column changes the plan and so the result. Over values of one sign it failed exactly when the result left signed 64 bits, in all 5,334 random cases; over mixed signs 470 of 2,666 failed with the result inside; no wrong value was returned | `sum` of an `Int` only when the contract's `int_range` lies on one side of zero: then every partial sum lies between zero and the result (*derived*), so SQLite fails exactly when PostgreSQL's exact sum raises SQLSTATE 22003, and never returns a wrong value. A mixed range is `PIE-B1004` `sum_int_aggregate_range_proof_missing` (rule 35); single files keep `sum` refused |
| Collation | A column may be `COLLATE NOCASE`; `PRAGMA table_xinfo` does not report a column's collation. With `COLLATE BINARY` written, comparisons, `ORDER BY`, `GROUP BY`, `HAVING`, `count(distinct ...)`, `min` and `max` compare bytes, on either side of a comparison | Project SQL writes `COLLATE BINARY` (see [SQL](#sql)); single files keep the `BINARY` premise |
| Encoding | A database may be `UTF-16le`, and `PRAGMA encoding` reports it | Emission assumes UTF-8 (`client_encoding` `"UTF-8"`); execution checks `PRAGMA encoding` |
| Identifier case | Every identifier, quoted or not, matches without ASCII case: `"a"` and `"A"` are one column, tables `IC` and `ic` one table | Columns that collide under ASCII case folding are refused (rule 31); the relation name must equal the connector's string exactly (rule 27); the SQL names only the alias `s0` and qualified columns; `identifier_case` is not admitted |
| NULL order | Ascending order puts NULL first by default; explicit `NULLS FIRST` and `NULLS LAST` hold in all four combinations | Explicit NULLS clauses, as D78.02 decided for single files (lead, stated to the owner in PL.47) |
| `-0.0` | A `STRICT` `REAL` column stores `-0.0` as `0.0`. A bound `-0.0` keeps its sign as a value, also through `abs`, and loses it when cast to text; `GROUP BY` puts both zeros in one group and keeps the first; `count(distinct ...)` counts them once | No stored value is a negative zero. A projected `Float` parameter returns `-0.0` as Pietto's value does; this tier has no `abs` or `count_distinct` of a `Float` and no cast to text |
| `Bool` | A `STRICT` `INTEGER` column stores 2 and -1 | Emission assumes 0 and 1 (`bool01`, `row_domain_matches`); execution checks each value |
| NaN and infinities | A bound NaN becomes NULL; a `REAL` column stores ±Infinity | Execution refuses a NaN or infinite `Float` parameter before it binds and checks each stored value; emission assumes finite values (`finite_float`) |
| NUL in `Text` | A `TEXT` value may hold NUL, and `length` counts only up to it; invalid UTF-8 is stored too, and no SQL form detects it | No form reads `length`; a `Text` literal with NUL is refused (rule 9); execution refuses a stored NUL and decodes each `Text` value in Python |
| `avg` rounding | `AVG(CAST(x AS REAL))` equalled compensated summation (`math.fsum`) divided by the count in 400 of 400 random cases, whatever the scan order, and plain left-to-right summation in 221; under cancellation it differs by more than the last bit (`[1, 2^53, -2^53]` gives 1/3 where plain summation gives 0). PostgreSQL's plain summation is *inferred*, not measured | The lead's ruling, stated to the owner as inform under PL.47: within the existing rules, which leave the summation of a binary64 average to the target, so the result may differ from PostgreSQL and MySQL in the last bits, or more under cancellation, and this page and the language guide say so. The native cells compare with `fsum` divided by the count, never with plain summation; R1 passes its `avg` entries only on data whose sum does not depend on the order and records a cancelling case as an observed difference. A claim of bitwise equality with PostgreSQL, or SQL that imitates plain summation, would need the owner |
| `HAVING` and bare columns | `HAVING` runs without `GROUP BY` and may read an output alias or a column that is not grouped, and a `SELECT` of an aggregated query may read a column that is not grouped (PostgreSQL refusing these is *inferred*) | The SQL writes only aggregates, qualified `group by` keys, literals and parameters there, and the projection rule refuses other fields (rule 11) |
| Quoted names | A double-quoted name that names no column reads as text (a B1 Q0 cell; see the route's [B2 handoff](../phases/phase-78/route.md#b2-handoff)) | Backtick quoting |
| `LIKE` | `LIKE` folds ASCII case; the build has no ICU | Not opened |

## Compile refusals

A SQLite emission reports only the blockers of the table below, and no other
`PIE-B10xx` detail (*derived*). A contract that breaks its schema is still
`INPUT_REJECTED` with `emission_contract_schema` and has no blockers.
Emission first runs `check --project`, then the one existing verification of
the project SQL plan, then reads the contract, then checks these rules:

- Rules 1–35, with rule 9b after rule 9, are checked together. The
  document lists one blocker for each rule that fails, in rule order, and
  none for a rule that holds.
- A rule that fails at several sites reports the first one only: source,
  stage and expression sites in source order (path, line, column), source
  fields in shape order, and premises in contract order (`environment`, then
  each source's `premises`, in `sources` order).
- A rule whose subject is absent holds: rules 12–14 need their clause, rule
  18 a parameter read, rules 25–34 a contract entry for the read source, and
  rules 9b and 35 arithmetic or a `sum` argument whose bounds are known:
  every field it reads passes rule 33 and rule 9 admits its operands, and
  for rule 35 rule 9b holds at each operation in it.
- When the plan is unavailable, rule 5 reports at the plan's first blocker,
  and rules 6–35 and 9b are not checked.
- Rule 20 counts the nodes and the expression depth of the SQL AST that the
  adapter will build, from the plan and before anything is built. A built AST
  with another count does not correspond to the plan (rule 36).
- Only when rules 1–35 and 9b all hold is the SQL built, verified,
  rendered and put in its document; then the first of rules 36–39 that
  fails is the only blocker.

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
| 9 | `PIE-B1003` | `sqlite_expression_not_admitted` | An expression in `select`, `where` or `having`, or arithmetic in an aggregate's argument, is outside the expressions of [admission](#admission), or is a `Text` literal that holds NUL, or an `Int` literal of 9223372036854775808 anywhere but right after a unary `-` | The expression | `use fields, literals, parameters, comparisons of two values of one type, and, or, not, is None, and Int +, -, *, unary - and abs of fields and Int literals; Float arithmetic, /, %, arithmetic on parameters or aggregates, in, ranges, conditionals, casts and other function calls are not available on SQLite` |
| 9b | `PIE-B1004` | `int_arithmetic_range_proof_missing` | The bounds of the result of an `Int` `+`, `-`, `*`, unary `-` or `abs` leave signed 64 bits, computed operation by operation from those of its operands, each field read bounded on its own by its contract `int_range` and each literal by its value; this holds for every intermediate result and for the argument of `avg` and `sum` row by row (S14) | The first such operation | `declare int_range bounds that keep every operand and result inside signed 64 bits, or keep this expression in check/plan: SQLite turns an Int overflow into a REAL without an error` |
| 10 | `PIE-B1003` | `sqlite_aggregate_not_admitted` | An aggregate is outside the aggregates of [admission](#admission), reads anything but one field of the source directly, except the arithmetic that `avg` and `sum` may read, or appears anywhere but as a whole result field, a `having` operand or an `order by` key | The aggregate | `use count, count_distinct of an Int, Text or Bool field, min or max of an Int or Float field, or avg or sum of an Int field or of Int arithmetic, each over the fields of the source` |
| 11 | `PIE-B1003` | `sqlite_projection_not_admitted` | In an aggregated relation, a result field is not a `group by` key, an admitted aggregate or a literal | The result field | `in a relation with group by or an aggregate, select group by keys, aggregates and literals` |
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
| 35 | `PIE-B1004` | `sum_int_aggregate_range_proof_missing` | A `sum` reads an `Int` field whose `int_range` has a negative `min` and a positive `max`, or arithmetic whose bounds (rule 9b) do | The aggregate | `declare an int_range on one side of zero, or keep this sum in check/plan: SQLite can fail a sum over values of both signs whose result fits` |
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

- `compile_query(dialect="sqlite")` compiles a query of this page, and
  [execution](#execution) states where it runs and which entry points refuse
  it.
- `pietto explain --project` and every inspection stay non-executing and
  dialect-neutral, and no SQLite catalog is inspected.
- `pietto lsp` reports what `check` reports, so a project `sqlite.table`
  stops being `PIE-S2306` there too.

## Execution

`execute(query, route="sqlite_file", access=SQLiteFileInput(path),
premise=None)` runs a query compiled with `dialect="sqlite"` once, in
process and read-only, over one SQLite file that the caller names. This is
tier 1b of PL.47; with Q6a and Q6b it is D78.01's trust Gate 1, and the
[external reference record](../phases/phase-78/route.md#b2-external-reference-untrusted-sqlite-files)
of untrusted SQLite files informs it. The file's bytes are untrusted:
Pietto checks what it reads before the statement runs, but the memory
safety of the SQLite library on a malformed file is no part of its
guarantee. Pietto writes no database content and takes no content digest.
It runs only on Linux x86-64 with the measured build of
[status](#status); everywhere else `execute()` refuses before any file
opens, while the SQL text stays the same.

### Request

`SQLiteFileInput(path)` holds a `str` or `os.PathLike`; constructing it
checks and reads nothing, and it refuses pickle and copy.
`compile_query(dialect="sqlite")` compiles each form of
[admission](#admission) with `literal_policy="preserve"`; `bind-safe` is the
adapter's rule 3 refusal (`CompileRejected`). The `CompiledQuery` has no
value slots and lists the header parameters. `export_bundle` refuses it
(`PIE-R1004` `SQLITE_BUNDLE_ENTRY`), and `save`, `save_recoverable`,
`recover`, `relay_live` and the job store do not take the route or the
dialect (`PIE-R1003` `PUBLIC_ROUTE_UNAVAILABLE`).

`execute()` opens no file. After its shared checks (the route `sqlite_file`
for a `sqlite` query, else `PIE-R1003`; a `SQLiteFileInput`; `premise`
None, else `PIE-R1002` `PUBLIC_PREMISE_TYPE`), it checks in this order:

1. The binding (`PIE-R1006`): no `values` (`BINDING_SLOTS`), exactly the
   declared parameters (`BINDING_PARAMETERS`), each of its exact type or None
   when nullable, and a `Text` parameter without NUL
   (`BINDING_PARAMETER:<i>:<tag>`); the artifact verifies afresh
   (`PIE-R1004`); the installed code is the code that compiled it
   (`PIE-R1005`).
2. The path is a non-empty `str` without NUL after `os.fspath`
   (`PIE-R1002` `EXECUTION_ACCESS`); a relative path is joined to the
   working directory of this call (one that no longer exists is
   `EXECUTION_ACCESS` too). The path is not normalized, so a `..` after a
   symbolic link steps out of the link's target, as the operating system
   reads it.
3. `isolation` is `"stable"`, the attempt's one read transaction
   (`PIE-R1002` `EXECUTION_ISOLATION`), and the limits are valid
   (`PIE-R1002` `EXECUTION_LIMITS`).
4. Defence 9: the platform is Linux x86-64 and the linked SQLite's release,
   source id and compile options, read from a `:memory:` database, are the
   measured build's (`PIE-R2002` `SQLITE_BUILD`, raised as
   `RequestRejected`).

### Attempt

Entering the handle, or the first `next()`, runs these steps within
`limits.seconds` of its start. Each refusal is `AttemptFailed`:

1. PyArrow is the `arrow` extra's pinned `pyarrow==26.0.1` (`PIE-R2001`
   `EXECUTION_DEPENDENCY_MISSING`, `PIE-R2002` `ARROW_DEPENDENCY_VERSION`).
2. Defences 1 and 6 and the file limit: the path, as the operating system
   reads it, is an existing regular file that is not empty and the same file
   that it resolves to through symbolic links, and each of the
   `-wal`, `-journal` and `-shm` files beside it that exists is a regular
   file too, the `-shm` file with no other link (`PIE-R2004`
   `SQLITE_FILE_TYPE`; `/dev/null` would open as an empty database, SQLite
   deletes the `-wal` file beside a 0-byte one, it opens each of the three
   files itself, where a FIFO would block it beyond the deadline, and it
   truncates an `-shm` file in place); the file and its `-wal` file hold at
   most 128 MiB together (`PIE-R3004` `SQLITE_FILE_LIMIT`; a `-wal` file can
   be far larger than its database). PL.47 set 256 MiB unless the checks
   and the query could not finish within 20 seconds there; S12 measured,
   with a cold cache under both interpreters, the check of a 253 MiB file
   whose 13 indexes were keyed at random run past that deadline, and
   10.9 s at 117 MiB, so the cap is 128 MiB and the deadline stays. No
   size bounds the time of the file's own expressions, which step 4
   refuses before the integrity check would run them.
3. Defences 1 to 3 and 7: one connection opens
   `Path.resolve().as_uri() + "?mode=ro"`, which percent-encodes `?`, `#`,
   `%`, `=` and `&` in the name, so a name cannot add URI parameters, never
   with `immutable=1` (which ignores locks and reads old rows); `mode=ro`
   creates no missing file. Defensive mode is on, trusted schema off,
   extension loading off, `cell_size_check` on, `mmap_size` 0 and
   `query_only` on, each read back (`PIE-R2006` `SQLITE_SESSION_CONTEXT`).
   The progress handler is installed, then the busy timeout is set to the
   time left (Python's default would wait 5 s), then the authorizer; `BEGIN`
   and `PRAGMA schema_version`, the first read, open the read transaction
   that every later step shares, so the checks and the statement see one
   snapshot of schema and data.
4. Defences 4 and 5 and the value check of Q6b (i), in that transaction:
   `PRAGMA encoding` is `UTF-8` (`PIE-R2007` `SQLITE_FILE_ENCODING`);
   `PRAGMA table_list` lists exactly one object of that name, in `main`,
   named exactly as the contract's `relation.name`, of type `table` and
   `STRICT` (`PIE-R2007` `SQLITE_SOURCE_OBJECT`: a missing table, a view, a
   virtual or shadow table, a table that is not `STRICT`, or another letter
   case); `PRAGMA index_list` and `PRAGMA index_xinfo` show no index of the
   table with a `WHERE` clause or a key that is an expression (`PIE-R2007`
   `SQLITE_SOURCE_OBJECT`); `PRAGMA table_xinfo` shows no generated column,
   stored or virtual, in the table and declares each contract column with
   exactly its name, as `INT` or `INTEGER` for an `Int` or `Bool` field,
   `REAL` for a `Float` and `TEXT` for a `Text`, never `ANY` or `BLOB`
   (`PIE-R2007` `SQLITE_SOURCE_COLUMNS`). The integrity check would compute
   each index expression, partial-index `WHERE` clause and virtual
   generated column of the table for every row, without the authorizer and
   within single steps that the progress handler does not split: S12's
   review saw a 12 KiB file's index expression of `hex`, `zeroblob` and
   `replace` run 94.5 s under the 20 s deadline. A stored generated column,
   which the check does not compute, is refused with them so that the rule
   stays simple and fails closed. Then `PRAGMA
   integrity_check` of the table and its indexes reports `ok` before any of
   its rows is read (`PIE-R2007` `SQLITE_SOURCE_INTEGRITY`; it finds an
   index that disagrees with its table, which `quick_check` misses and
   which makes a query return wrong rows, and a `STRICT` type or `NOT NULL`
   violation that a tampered file holds; on this read-only connection it
   checks no `CHECK` constraint, which the route never relies on); the
   table holds at most 1,048,576
   rows (`PIE-R3004` `SQLITE_SOURCE_LIMIT`); and every row holds each
   contract field's domain (`PIE-R2007` `SQLITE_SOURCE_VALUES`): one scan
   checks the storage class by `typeof`, NULL only in a nullable field, an
   `Int` within its `int_range`, a `Bool` of 0 or 1 and a finite `Float`,
   and each `Text` value's bytes are decoded in Python, since no SQL form
   finds invalid UTF-8, and must be UTF-8 without NUL and of at most
   `max_characters` characters. A broken view, or an expression index or
   generated column of another table, elsewhere in the file leaves these
   checks working.
5. The compiled statement runs once with the parameters at `?1`, `?2`, ...;
   its whole result is read, `COMMIT` ends the transaction and the
   connection closes, so no lock is held while batches are delivered.
6. Each value is checked against its result column before PyArrow sees it:
   an `int` in signed 64 bits, an `int` 0 or 1 for a `Bool`, a `str`, a
   finite `float`, or None in a nullable column (`PIE-R3005`
   `SQLITE_RESULT_CHECK`); batches follow the `ExecutionLimits`
   (`PIE-R3004`).

The authorizer answers allow or `SQLITE_DENY`, never `SQLITE_IGNORE`, which
would read a column as NULL. It allows reads of the source's contract
columns in `main`; reads of no column (`count(*)`, `rowid`), whose database
is `main` or, unqualified, None; `SELECT`; the functions `count`, `min`,
`max`, `avg`, `sum`, `typeof` and `abs`; the PRAGMA statements of steps 3
and 4, with no argument, the source's name or, for `index_xinfo`, the name
of an index that `index_list` listed for the source, until the statement
runs;
and the transaction's `BEGIN`, `COMMIT` and `ROLLBACK`. Everything else is
denied, `ATTACH`, writes and any access through a view or trigger included.

The progress handler stops a running statement once the deadline passes or
`cancel()` was called; `cancel()` also calls `interrupt()` while the
connection is open, and the steps in Python check between batches of 4,096
rows. The end is `DEADLINE` (`PIE-R3001`) or `CANCELLED` (`PIE-R3009`).
The busy timeout is the time left, so a lock that the caller's writer holds
until the deadline ends the attempt there too (`PIE-R3001`
`SQLITE_ERRORCODE_5`); while the attempt waits for that lock, `cancel()`
takes effect only at the deadline (`PIE-R3009`), since SQLite's busy
handler does not see an interrupt. A failure inside the transaction closes a
cursor that still holds rows, which would keep an interrupt alive, and sends
`ROLLBACK` before the connection closes. An error that SQLite raises is
`PIE-R2004` before the first read and `PIE-R3003` after it, and is named by
its extended result code, `SQLITE_ERRORCODE_<n>`, never by
`sqlite_errorname`, which calls a `STRICT` type error (code 3091)
`unknown`; where the code is not enough, by its message: a `sum` past
signed 64 bits is `SQLITE_INTEGER_OVERFLOW` (code 1, `integer overflow`).
The message is never shown.

The outcome's `transaction` is `COMMIT_ACK` once the result is read and
`ROLLBACK_ACK` after a failure inside the transaction, and `cleanup` is
`CLOSED`. Since the whole result is read when the attempt opens, an early
`close()` ends `STOPPED_EARLY` with `COMMIT_ACK`.

Effects. `execute()` imports `sqlite3` and opens one `:memory:` database.
An opening attempt reads the file and its `-wal` file and holds SQLite's
read lock until it closes the connection, at the latest at its deadline: in
WAL mode the caller's writers go on and the attempt keeps its snapshot; in
rollback-journal mode they fail with `database is locked` meanwhile. On a
WAL file SQLite writes the `-shm` file, its shared index, on every read: it
creates the `-wal` and `-shm` files when they are missing and leaves them,
and when no other connection has the file open it truncates and rebuilds
an existing `-shm` file (step 2 refuses one with another link, which would
be rewritten too). When a sort, a grouping or `count_distinct` outgrows
its memory, SQLite writes temporary files to the first directory it can
write of these: a temporary directory set for the whole process, where one
is, `SQLITE_TMPDIR`, `TMPDIR`, `/var/tmp`, `/usr/tmp`, `/tmp` and the
working directory; each is deleted as it is opened (S12 saw them under
`/var/tmp`). Pietto creates and writes no other file and starts no
thread.

Known limits. The types and sizes of the file and of the files beside it
are checked before it opens, so a file replaced or added between the check
and the open is not detected (a FIFO put there would block the attempt
beyond its deadline); the checks inside the transaction still read what was
opened. In a directory that cannot be written, a WAL file whose `-wal` and
`-shm` files are missing cannot be read (`PIE-R2004`
`SQLITE_ERRORCODE_1544`). While the attempt waits for a lock that the
caller holds, `cancel()` takes effect only at the deadline. `max_rows` and
`max_bytes` bound delivery, not the result read when the attempt opens,
which the source's row limit bounds.

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
hold the rest. The route's native cells in
`tests/test_execution_api_sqlite_file.py` open test-owned files under the
same SQLite class, judge each result by its types as well as its values,
and give each defence and value check a cell that breaks it, on a file
where a file can, with control cells that show the harm behind several;
S12 ran them under CPython 3.13.13 and 3.12.13. They need the `arrow`
extra: without PyArrow they skip with the counted line
`PIETTO_NOT_RUN sqlite-native ARROW`, and Gate 2 qualifies them in a run of
their file with the extra and no skip. Hosted CI asserts the
refusal of the native classes and runs the byte and golden tests
everywhere.

The second tier adds two campaigns under the first one's conditions and
method (D78.14): R2 covers the new bytes of S14 and S15 that PostgreSQL
project emission also writes, and R3 those of S13 and of S13 with S14. A
window `count`, `min` or `max` of a `Float`, `count()` over an empty window
and the `Int` minimum written as one signed literal have no PostgreSQL
project emission, so they have native cells only, and the owner rules on
them before the first batch's push (D78.15). A `row_number` entry compares
only results that do not depend on the order of peers.

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
- S10: `docs/language.md`, the single-file aggregates, `having`, the `avg`
  rounding and the `Bool` literal written `1` or `0`;
  `docs/capabilities.md`, the SQLite table;
  `docs/spec/diagnostics.md`, the `PIE-B1004` row naming SQLite's
  `sum_int_aggregate_range_proof_missing`.
- S11: `docs/execution.md` (the route's section, the support matrix row and
  the request checks), `README.md` (its SQLite entry), the sentences of
  `docs/language.md` and `docs/capabilities.md` that said Pietto runs no
  SQLite statement, and `docs/spec/diagnostics.md`, the `PIE-R1001`,
  `PIE-R1002`, `PIE-R1004`, `PIE-R1006`, `PIE-R2002`, `PIE-R2004`,
  `PIE-R2006`, `PIE-R2007`, `PIE-R3003` and `PIE-R3004` rows naming the
  route's details,
  at a time the lead schedules apart from Phase81's diagnostic review (P03,
  PL.58).
- S14: `docs/language.md`, range-proved `Int` arithmetic in its SQLite
  project section; `docs/capabilities.md`, the project bullet of its SQLite
  section; and `docs/spec/diagnostics.md`, the `PIE-B1004` row naming
  `int_arithmetic_range_proof_missing`, at a time the lead schedules apart
  from Phase81's diagnostic review (P03, PL.58).

## Open items

| Item | Owner | Latest point |
| --- | --- | --- |
| The second tier's *derived* rows, stated as inform as each slice lands them: the new details, rule letters and suggestions of [compile refusals](#compile-refusals); the SQL rules it adds, such as the aliases `s0` to `sN` in input order, `COLLATE BINARY` at each `ON` equality and window key, the signed writing of a negative `Int` literal and the inline `OVER`; the functions that the route's authorizer adds; the detail of a duplicate declared key; and how the bounded read of a statement that joins sources measures its batches | The lead | Each batch's rows before that batch's push, with a decision row |
| This page's *derived* rows, stated as inform: the `main` namespace, the `sqlite_` and dot refusals and `sqlite_table_name_mismatch`; the `relation_rows` scan; the storage kinds and domain spellings (`UTF-8`, `BINARY`); the premise values and `premise_not_admitted_on_target`; the limits `columns` 2,000, `parameters` 32,766 and the depth 500; the SQL rules (`s0`, backticks, `?N`); the closed order of compile refusals with its new details and suggestions; the two new single-file reasons | The lead | Settled: not stated by S08's seal ([Phase78 audit](../phases/phase-78/completion-audit.md#not-verified)); stated to the owner as inform on 2026-11-17 at about 08:20Z, before the `0.2.2` release commit, and recorded by D78.13 in the [decision record](../decisions.md) |
