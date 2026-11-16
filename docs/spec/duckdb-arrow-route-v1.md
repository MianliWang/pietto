# Pietto DuckDB Arrow Route v1

## Status

This is an **alpha** contract until the Phase82 freeze. It is Phase79's first
vertical, B1: a read-only executor of one projection over one Arrow table that
the caller supplies, compiled for DuckDB `2.0.0` and run in process. It admits
an explicit-module project only, one `duckdb.arrow` source, a direct
projection of `Int`, `Text`, `Bool` and finite `Float` fields and at most one
comparison of an `Int` field with one non-null `Int` query parameter
([admission](#admission)). It has no JOIN, aggregation, `order by` or `limit`,
and it refuses an input table of more than 65,536 rows or 16 MiB
([capture](#capture)). It is qualified only for `duckdb` `2.0.0` with
`pyarrow` `26.0.1` on CPython 3.12 and 3.13, Linux x86-64 with glibc 2.28 or
later; every other release and platform is not qualified. Its names, fields,
detail words and limits may change in any later release, each with a
release-note line and no deprecation period.

B1 does not complete Phase79. B2, `group by` with `count`, `sum`, `min` and
`max`, `having`, `order by`, `limit` and wider `where` filters, is scheduled as
Phase79's second slice (PL.47, [roadmap](../roadmap.md#third-dialect)), with
higher capture limits; until a release carries it, this page binds and those
forms stay refused. The [B2 section](#b2-pending) at the end states what B2
will open, written before its code: it describes no released behavior, and
every section before it binds as written.

The rules come from the Phase79 Gate 1 decisions D79.01–D79.08, the
third-dialect seam AD78.03 and the failure rule AD79.01 in the
[decision record](../decisions.md). Rows marked *derived* are consequences of
those decisions that this page fixes; the lead states them to the owner as
inform before this page binds (see [open items](#open-items)).

Construction state: PUBLISHED. S02 landed the shared connector and dialect
sets and the family firewall, S03 the independent adapter with the DuckDB
target identity, S04 the execution route, S05 the `execute-duckdb` extra and
S06 the native qualification, and S08 applied the shared-page hunks below.
B1 reached `main` on 2026-11-14 in one fast-forward push ending at
`94b4097a` and ships in `0.2.0`; the
[B1 audit](../phases/phase-79/completion-audit.md) records its Gate 2 and
natural CI.

## Admission

| Admission | Exact limit |
| --- | --- |
| Project and source | An explicit-module project (`schema_version = 2`) whose statement reads exactly one source declared `source x: Shape = duckdb.arrow("key")`. The key is one non-empty string literal, used exactly: no normalization, trimming or case folding. |
| Relational shape | A direct projection of that source's fields, optionally with one `where` that is exactly one comparison `IntField <op> param`, where `<op>` is `==`, `!=`, `<`, `<=`, `>` or `>=`, `IntField` is a field of the source and `param` is the query's parameter. No relation `let`, derived source, second input, JOIN, `group by` or aggregate, window, `order by`, `limit`, `distinct`, set operation, typed VALUES body or table function. |
| Parameter | A projection declares none. A filtered query declares exactly one non-null `Int` parameter and reads it exactly once, in the comparison. Values bind through the existing exact binding (`execute(parameters=...)`, PIE-R1006). |
| Columns | Source and result fields are `Int`, `Text`, `Bool` or finite `Float`, each with its compiled nullability, in source order. `Text`, `Bool` and `Float` fields are projected only. |
| Literal policy | `preserve` only. |
| Entry points | `pietto check --project`; `pietto emit-sql --project ... --dialect duckdb`, with or without `--all`; `compile_sql`, `compile_all_sql` and `compile_query` with `dialect="duckdb"`; `execute(route="duckdb_arrow")`. |

Results are bags: B1 has no `order by`, so row order is not part of a result,
and qualification compares multisets of rows.

Not in B1: single-file mode (`pietto check FILE` and `pietto emit-sql FILE
--dialect duckdb` keep today's output byte for byte); `Decimal`, `Date`,
`Timestamp`, `UUID` and nested fields; `--literal-policy bind-safe`;
arbitrary SQL, file, database or connection URIs, caller settings, catalog
access, extension loading, SQL functions and UDFs; query bundles, saved
results, relay, jobs and R2; installation automation; sqlglot; and any change
to PostgreSQL or MySQL SQL bytes, contracts or diagnostics. No claim of parity
across databases is made.

## Source connector

`duckdb.arrow("key")` is a built-in source connector of explicit-module
projects only. It reads no catalog, file or environment, and `pietto fmt`
keeps its spelling byte for byte.

```pietto PIE-S2306
shape Order:
    id: Int
    amount: Int
    note: Text | None

source orders: Order = duckdb.arrow("orders")
```

The fence names `PIE-S2306` because the block is a project-only form: checked
as a single file, it reports `Unknown source connector: duckdb.arrow`.

- A `duckdb.arrow` call without exactly one argument, with a non-`Text`
  argument such as `1`, or with a `Text` argument that is not a non-empty
  string literal, such as `""` or `concat("a", "b")`, is `PIE-S2306`
  `Invalid source connector arguments for duckdb.arrow`, on the call, by the
  rule `mysql.table` follows today. As for `mysql.table`, an argument whose
  type is unknown reports only its own diagnostic: `PIE-S2102` for an unknown
  name, and none in a project for `None` or an unquoted dotted name such as
  `a.b`. Such a source is not a static source, so no emission admits it.
- In a single file and in a legacy-flat (`schema_version = 1`) project,
  `duckdb.arrow` stays unknown: `PIE-S2306` `Unknown source connector:
  duckdb.arrow`, unchanged.
- The key, the contract's `relation.name` and `DuckDBArrowInput.name` are one
  identity (D79.03, D76.06): compilation requires the first two to be equal
  and execution requires the third to equal them, by exact string equality.

## Emission contract values

A DuckDB contract is a `pietto.emission-contract.v1` document with these
values. Everything else keeps the rules of
[project emission](../project-package.md#emission-contract-values).

| Member | DuckDB value |
| --- | --- |
| `target` | `{"family": "duckdb", "release": "2.0.0"}` (D79.05). The family must equal `--dialect`, or the command fails with `emission_contract_schema`; another release is BLOCKED with `PIE-B1003` `target_release_not_reviewed`. |
| `sources[].relation` | *Derived:* `{"namespace": "arrow", "name": KEY}`. Another namespace is BLOCKED with `PIE-B1001` `source_identifier_unrepresentable`; a name other than the connector's key with `PIE-B1001` `duckdb_arrow_key_mismatch`. |
| `sources[].scan` | `"arrow_registration"` (D79.05). It is the only DuckDB value, and it is refused on the other families: either mismatch fails with `emission_contract_schema` at `sources/N/scan`. |
| `sources[].fields[].column` | The name of the field of the caller's Arrow table that the source field reads, matched exactly at execution. Every shape field is described once, in shape order, as on the other targets (`complete_ordered_source_schema_required`). |
| `MAX_PARAMETERS` | *Derived:* 65,535, the D70.07 placeholder ceiling, in place of the DuckDB-specific value that D79.05 expected. DuckDB `2.0.0` showed no ceiling of its own at or below 262,144: it prepared and bound 262,144 positional parameters in one statement. |

Each source field's `representation` (*derived*):

| Logical type | `storage` | `domain` |
| --- | --- | --- |
| `Int` | `arrow_int64` | `int_range`, with string `min` and `max` inside signed 64 bits |
| `Bool` | `arrow_bool` | `bool01` |
| `Text` | `arrow_string` | `text`, with `max_characters`, `encoding` `UTF8`, `collation` `C` and `padding` `NO PAD` |
| `Float` | `arrow_float64` | `finite_float`, with `format` `binary64` |

`nullable` is `false` for a non-null field and `true` for an optional one. A
`nullable` that does not fit the field is BLOCKED with `PIE-B1002`
`nullability_mismatch`, and a storage or domain that does not fit its logical
type with `PIE-B1002` `physical_storage_or_domain_mismatch`, the details the
other targets use. B1 compares no
`Text`, so its collation is never used; `C` names byte order, which DuckDB
`2.0.0` uses by default (`'B' < 'a'`, `'é' > 'z'`) and also accepts as
`COLLATE c`.

Premises (*derived*):

| Key | Scope | DuckDB value | Needed |
| --- | --- | --- | --- |
| `row_domain_matches` | source | `true` | always; otherwise `PIE-B1001`. Execution checks the declared domains of the captured columns (see [capture](#capture)). |
| `read_only_object` | source | `true` | always; otherwise `PIE-B1001`. The capture is Pietto's own copy. |
| `client_encoding` | statement | `"UTF8"` | always |
| `operator_environment` | statement | `"builtin_only"` | when the statement has its `where` comparison |
| `parameter_protocol` | statement | `"duckdb_prepared"` | when the statement has its parameter |
| `resource_limits` | statement | as today | optional |

A needed premise that is missing is BLOCKED with `PIE-B1004`, and one with
another value with `PIE-B1005`, as today. The field premises (`value_domain`,
`encoding`, `collation`, `padding`, `comparison_prefix_bytes`) stay optional
and must agree with the field's domain. `identifier_case`,
`session_sql_mode` and `session_time_zone` are BLOCKED on a DuckDB contract
with `PIE-B1003` `premise_not_admitted_on_target`, once, at the first such
declaration (see [compile refusals](#compile-refusals)): B1 SQL names only
Pietto-owned identifiers and reads no session mode or time zone.

The DuckDB limits are Pietto's. `sql_bytes` 8 MiB, `artifact_bytes` 16 MiB,
`nodes` 32,768 and `parameters` 65,535 are as on the other targets; `columns`
is 4,096 (*derived*), the MySQL value, which D79.05 does not give: a
4,096-column projection ran on the pin (see [pin facts](#pin-facts)).
`resource_limits` may only lower them.

## SQL

S03 owns the exact bytes and their goldens; any form it writes satisfies
these rules (AD78.03: the adapter has its own SQL AST, renderer and artifact
verifier, and consumes `ProjectSQLPlan`).

- One `SELECT` statement with no `WITH`, subquery, function call or second
  statement.
- It reads only `temp.main."pietto_arrow_0"`, the name under which the route
  registers the capture. DuckDB resolves names case-insensitively and lets a
  registered name shadow a system view such as `pg_tables` (observed on
  `2.0.0`), so the SQL never contains the caller's key or column names.
- Source field `k` (0-based, in shape order) is the capture column `"c<k>"`.
  DuckDB renames Arrow columns that differ only in case (`A` becomes `A_1`)
  and `"A"` then reads `a`, so the capture renames every selected column.
- Each result field is written `"c<k>" AS "<label>"`, the label quoted, in
  result order.
- The comparison is `"c<k>" <op> CAST($1 AS BIGINT)`, with `=`, `<>`, `<`,
  `<=`, `>` or `>=`. DuckDB types a bound Python `int` by its value
  (`INTEGER` for 5), so the placeholder is cast.
- The artifact's `target` is the contract target. A SQL AST or a document
  that breaks any rule above is BLOCKED with `PIE-B1008` (rules 30 and 32 of
  [compile refusals](#compile-refusals)).

The VERIFIED document is the `pietto.sql-emission.v1` envelope, or `v2` when
the statement reads its parameter, with these DuckDB values: `fixed_values` is
empty; the parameter's one `parameter_uses` entry has `server_index` 1 and
`physical_type` `duckdb_bigint`, and `binding_obligations` is empty; each
column's `correspondence` names the source field it reads; `requirements`
lists the plan's original demands with their target evidence under the rule
`duckdb_b1` and no generated requirement; and `ranges` cover the statement
byte for byte, in order.

## Execute API

```python
from pietto.execution import DuckDBArrowInput, compile_query, execute

query = compile_query("shop", module="models/queries.pietto", kind="query",
                      name="large_orders", dialect="duckdb",
                      emission_contract="duckdb-contract.json")
with execute(query, route="duckdb_arrow",
             access=DuckDBArrowInput(name="orders", table=orders),
             premise=None, parameters={"min_amount": 100}) as result:
    for batch in result:
        ...
```

`DuckDBArrowInput(name, table)` is a frozen value with two fields: `name`, the
key, and `table`, a `pyarrow.Table`. Constructing it checks nothing, imports
nothing and does no I/O; `execute()` checks it. Its `repr()` shows the name
and the table's type name only, never the table's contents. Pickling or
copying it raises `TypeError` (`DuckDBArrowInput holds a caller-owned table;
it cannot be pickled or copied`).

`execute()` keeps its signature. On `route="duckdb_arrow"`, `access` is a
`DuckDBArrowInput`, `premise` is `None` (the route takes no deployment
premise, which changes the `PIE-R1001` rule text), `isolation` is `"stable"`
(the owned capture snapshot) and `limits` is an `ExecutionLimits` whose
meaning is unchanged. There is no premise type for this route, no
`execute_local` and no new limit.

These checks run in `execute()`, in this order, and the first failure is
raised as `RequestRejected`: nothing has connected (see
[the error classes](../execution.md#errors)). Its code is a PIE-R1xxx code,
except that check 12 refuses with `PIE-R2001` or `PIE-R2002` (below).
Checks 1–11 import nothing;
check 12 verifies the PyArrow that the caller already loaded before the
capture uses it, and no check imports DuckDB:

| # | Check | Refusal |
| ---: | --- | --- |
| 1 | `query` is given and is a `CompiledQuery` | `PIE-R1001` `PUBLIC_QUERY_REQUIRED`; `PIE-R1002` `PUBLIC_QUERY_TYPE` |
| 2 | `route` is given, is a `str`, is a route, and fits `query.dialect` (`duckdb_arrow` takes exactly the `duckdb` dialect) | `PIE-R1001` `PUBLIC_ROUTE_REQUIRED`; `PIE-R1002` `PUBLIC_ROUTE_TYPE`; `PIE-R1003` `PUBLIC_ROUTE_UNAVAILABLE` |
| 3 | `access` is given and is a `DuckDBArrowInput` | `PIE-R1001` `PUBLIC_ACCESS_REQUIRED`; `PIE-R1002` `PUBLIC_ACCESS_TYPE` |
| 4 | `premise` is `None` | `PIE-R1002` `PUBLIC_PREMISE_TYPE` |
| 5 | `limits` is given and is an `ExecutionLimits`; `isolation` is given | `PIE-R1001` `PUBLIC_LIMITS_REQUIRED`; `PIE-R1002` `PUBLIC_LIMITS_TYPE`; `PIE-R1001` `PUBLIC_ISOLATION_REQUIRED` |
| 6 | `values` is `None` or a tuple; `parameters` is `None` or a dict with `str` keys | `PIE-R1002` `PUBLIC_VALUES_TYPE`, `PUBLIC_PARAMETERS_TYPE` |
| 7 | The query binds afresh to `values` and `parameters`; the installed code is the compiled code | `PIE-R1006` and `PIE-R1004`, as today; `PIE-R1005` |
| 8 | `access.name` is a non-empty `str`; `type(access.table)` is exactly the `Table` class of an already loaded `pyarrow.lib` (a table cannot exist otherwise, so nothing is imported) | `PIE-R1002` `EXECUTION_ACCESS` |
| 9 | `access.name` equals the contract's `relation.name` | `PIE-R1002` `DUCKDB_ARROW_SCHEMA` |
| 10 | `isolation` is exactly `"stable"` | `PIE-R1002` `EXECUTION_ISOLATION` |
| 11 | The values of `limits` | `PIE-R1002` `EXECUTION_LIMITS` |
| 12 | The loaded PyArrow is the installed `pyarrow` `26.0.1` distribution's own files | `PIE-R2001` `ARROW_DEPENDENCY_MISSING`; `PIE-R2002` `ARROW_DEPENDENCY_VERSION` |
| 13 | The capture admits the table (next section) | `PIE-R1002` `DUCKDB_ARROW_CAPTURE_LIMIT`, `DUCKDB_ARROW_SCHEMA` |

Check 12 runs in `execute()` because the capture uses PyArrow before anything
connects. A PyArrow whose distribution is not installed is refused with
`PIE-R2001` `ARROW_DEPENDENCY_MISSING`; one of another version, not that
distribution's own files or that cannot be loaded, with `PIE-R2002`
`ARROW_DEPENDENCY_VERSION`. These are the codes that the other Arrow routes
give their PyArrow, with this route's own details, raised here from
`execute()` as `RequestRejected`; the owner chose the codes on 2026-11-11
over a new `PIE-R1002` detail. The `PIE-R2001` and `PIE-R2002` rows of
[diagnostics](diagnostics.md) already cover the selected route's PyArrow and
hold. The class sentence of [the errors section](../execution.md#errors)
(`RequestRejected` (PIE-R1xxx) means nothing connected) changes to admit
them, and to name its precedent: `PIE-R2003`
`EXECUTION_AMBIENT_CONNECTION_PROFILE`, which `mysql_rows` and
`postgres_adbc` already raise as `RequestRejected`, because their ambient
check runs while `execute()` prepares the attempt. The docstrings of
`RequestRejected` and `AttemptFailed` in `src/pietto/execution/_errors.py`
repeat that sentence where `help()` shows it, and change with it.

Three passages of `docs/execution.md` also gain a `duckdb_arrow` clause:

- the `execute()` entry ("the driver and the environment are checked when the
  attempt opens, except MySQL's refused OpenSSL names");
- the request-check paragraph of the errors section, which lists the
  route/dialect pairs of `PIE-R1003` (`postgres_rows` or
  `postgres_adbc`/`postgres`, or `mysql_rows`/`mysql`) and the value checks up
  to `limits`: the pairs gain `duckdb_arrow`/`duckdb`, the relation-name check
  (check 9) follows `access`, and the PyArrow check (check 12) and the
  capture (check 13) follow `limits`;
- the attempt-open order of the errors section (environment, then the pinned
  driver, then pinned PyArrow).

On `duckdb_arrow` the PyArrow check runs in `execute()`, before the capture,
and the driver check when the attempt opens, as step 1 of
[the session](#session-and-attempt).

`execute()` returns an unopened `ResultHandle` only after the capture copy
exists. The PostgreSQL and MySQL routes keep their required premises and
every refusal they have today.

## Capture

The capture is admitted or refused before any session, with this fixed
private policy (D79.04). Checks run in this order, and the first failure is
raised; no detail carries a value, a name or a count.

1. **Limits.** The caller's whole table has at most 65,536 rows and
   `pyarrow.Table.nbytes` at most 16 MiB (16,777,216), measured before any
   copy; otherwise `DUCKDB_ARROW_CAPTURE_LIMIT`. `nbytes` counts the
   referenced ranges of every column, validity bitmaps included, and counts a
   buffer that two chunks or columns share once for each: it is a logical
   admission measure with no physical or peak-memory guarantee.
2. **Schema**, per source field in shape order: its `column` names exactly
   one field of the table, by exact string equality, so a name that no field
   or two fields of the table carry is refused; and that field's type is
   exactly `int64`, `string`, `bool` or `float64` as its storage says, so
   `dictionary`, `large_string`, `string_view`, extension, `null` and every
   other type are refused. Otherwise `DUCKDB_ARROW_SCHEMA`. A field of the
   table that no source field names is not examined, whatever its name (a
   duplicate included) or type (*derived*): it counts toward the limits of
   step 1 and is not copied.
3. **Values**, per source field in shape order, over the selected column: a
   non-null field has `null_count == 0`; an `Int` lies inside the declared
   `int_range`; a `Float` has no NaN, +Inf or -Inf; a `Text` value is valid
   UTF-8 under full validation and has at most the declared `max_characters`
   code points. Otherwise `DUCKDB_ARROW_SCHEMA`. PyArrow keeps a field's
   declared nullability only as metadata, so the null count is what is
   checked. A NUL is admitted anywhere in a `Text` value, counts as one code
   point, and reaches DuckDB and the caller unchanged (the owner's choice of
   2026-11-11; see the NUL row of [pin facts](#pin-facts)).
4. **Copy.** The capture is a new table of the selected columns only, in
   shape order, named `c0`, `c1` and so on, whose buffers are disjoint from
   the caller's and hold no unselected rows or columns. Changing the caller's
   buffers afterwards (a NumPy array that a column wraps without a copy, for
   example) does not change it. The route checks that its copy's buffers are
   disjoint from the caller's; a copy that shares one breaks an internal
   invariant, not a rule about the input, so `execute()` refuses it with the
   unclassified `PIE-R1999` `DUCKDB_ARROW_CAPTURE_COPY`, which is not one of
   the input refusals above and which the pinned PyArrow's copy is not
   expected to reach (see [pin facts](#pin-facts)).

`-0.0` is admitted under the `Float` value contract, where `-0.0 == 0.0`; on
`2.0.0` DuckDB delivered its sign bit unchanged (*derived*, inform). Each
`execute()` captures afresh, and the caller keeps the table.

## Session and attempt

The session opens when the handle is first entered. Each attempt has its own
`:memory:` DuckDB database and connection; nothing is pooled, cached or
reused. Every failure from here on is an `AttemptFailed` (AD79.01).

1. **Driver identity.** The installed `duckdb` distribution is `2.0.0` and
   owns the files of the imported `duckdb` and `_duckdb` modules, by the rule
   of the other routes' drivers; otherwise `PIE-R2001`
   `EXECUTION_DEPENDENCY_MISSING` or `PIE-R2002` `EXECUTION_DRIVER_VERSION`.
   The engine's `pragma_version()` row reports version `v2.0.0` and source
   id `d54cbbe3df`; otherwise `PIE-R2002` `DUCKDB_DRIVER_PROFILE`
   (accepted by the owner).
2. **Settings.** The route sets each value below with `SET`, in table order,
   on a fresh connection, then reads every row of both read-back lists from
   `duckdb_settings()` before the first statement. A `SET` that fails or a
   read-back that differs is `PIE-R2006` `DUCKDB_SESSION_CONTEXT`
   (accepted by the owner), and the route runs nothing.
3. **Statement.** The route registers the capture as `pietto_arrow_0`, runs
   the compiled statement once, with the bound parameter if it has one, and
   reads the result as Arrow through the relation API (`sql(...,
   params=...).to_arrow_table()`). Every call goes to the connection that
   step 2 set up, never to a `cursor()`, which is a connection of its own
   (see [pin facts](#pin-facts)). It never uses
   `execute(...).to_arrow_table()`, which warns about an extra copy on
   `2.0.0`, the deprecated `fetch_arrow_table()`, or `.arrow()`, which
   returns a reader.
4. **Result.** The result has the compiled result's labels and order, and
   types `int64`, `string`, `bool` and `double`. `to_arrow_table()` marks
   every field nullable, so the route restores the compiled nullability and
   refuses a NULL in a non-null field before it binds a `ResultBatch`;
   otherwise `PIE-R3005`. Batches then follow `ExecutionLimits` as on the
   other routes (`PIE-R3004`).
5. **End.** Whatever ends the attempt (success, early close, cancellation,
   deadline, result failure or setup failure), the route unregisters the
   capture if it was registered, then closes the connection if one was
   opened. A failure while the session is set up or the capture registered
   therefore closes the connection without unregistering, and an attempt
   that ends before it connects (a missing or mismatched driver, or a
   cancellation before the session opens) does neither. A failed close is
   `PIE-R3006`, with the failed step as its `PIE-R5001` entry.

| Setting | Value set | Read back |
| --- | --- | --- |
| `allow_community_extensions` | `false` | `false` |
| `allow_extension_repositories` | `'forbidden'` (*derived*) | `forbidden` |
| `allow_persistent_secrets` | `false` (*derived*) | `false` |
| `allow_unsigned_extensions` | `false` | `false` |
| `arrow_large_buffer_size` | `false` (*derived*) | `false` |
| `arrow_lossless_conversion` | `false` (*derived*) | `false` |
| `arrow_output_list_view` | `false` (*derived*) | `false` |
| `arrow_output_version` | `'1.0'` (*derived*) | `1.0` |
| `autoinstall_known_extensions` | `false` | `false` |
| `autoload_known_extensions` | `false` | `false` |
| `enable_progress_bar` | `false` (*derived*) | `false` |
| `enable_progress_bar_print` | `false` (*derived*) | `false` |
| `max_temp_directory_size` | `'0B'` | `0 bytes` |
| `memory_limit` | `'256MiB'` (*derived* value) | `256.0 MiB` |
| `python_enable_replacements` | `false` | `false` |
| `python_scan_all_frames` | `false` | `false` |
| `temp_directory` | `''` | the empty string |
| `threads` | `1` (*derived* value) | `1` |
| `enable_external_access` | `false`, after every row above | `false` |
| `lock_configuration` | `true`, last | `true` |

The rows marked *derived* go beyond the D79.06 items, and the values of
`memory_limit` and `threads` are this page's choice within D79.06's "explicit".

`enable_external_access = false` must come after `temp_directory`: on
`2.0.0`, `SET temp_directory` after it fails with `Modifying the
temp_directory has been disabled by configuration`. A connect-time
configuration of only these two values succeeded and read both back, but one
of all 17 values that `connect(config=...)` accepts one by one failed with
that same message, with `lock_configuration` in it and without; and
`connect(config=...)` refuses `enable_progress_bar` and
`enable_progress_bar_print` (`Could not set option ... as a global option`).
So the route uses `SET` only, in table order: that order succeeded on the pin
and read every row of both lists back as stated.

These are read back too and must equal their `2.0.0` values, which no
setting above may change: `allowed_configs`, `allowed_directories`,
`allowed_paths` and `extension_directories` `[]`; `custom_extension_repository`,
`autoinstall_extension_repository`, `log_query_path`, `profiling_output` and
`disabled_filesystems` the empty string; `enable_profiling` NULL;
`enable_logging` `0`; `logging_storage` `memory`; `access_mode` `automatic`.
`worker_threads` and `max_memory` are the aliases of `threads` and
`memory_limit`, which the table changes from the host's values, and are read
back as those values above: `1` and `256.0 MiB`.

A `:memory:` database cannot be opened read-only on `2.0.0` (`Cannot launch
in-memory database in read-only mode!`). The session is read-only because the
route runs only the compiled `SELECT`.

`threads = 1` gives each attempt one engine thread, and `memory_limit` is 16
times the capture limit; both are fixed private policy (*derived*). A
statement that needs more memory fails, because nothing can spill
(`OutOfMemoryException` on `2.0.0`).

## Failures

DuckDB errors become the existing `AttemptFailed` and `Failure` (AD79.01):
`phase` names the step, `cause` is the exception class name, and `sqlstate`
is `None`; no vendor code is kept. No DuckDB message enters any Pietto text.
The lead stated AD79.01 to the owner as inform on 2026-11-11.

| Event | Failure |
| --- | --- |
| A DuckDB error while the statement runs or its result is read, an integer overflow and `OutOfMemoryException` included | `PIE-R3003` |
| The caller cancels the attempt; the route interrupts the connection (`InterruptException` on `2.0.0`) | `PIE-R3009` |
| `limits.seconds` expires; the route interrupts the connection | `PIE-R3001` |
| A DuckDB error while the session is set up or the capture registered | `PIE-R2006` `DUCKDB_SESSION_CONTEXT` (accepted by the owner) |
| Returned types, labels, nullability or values do not match the compiled result | `PIE-R3005` `DUCKDB_RESULT_CHECK` |

`phase` is `driver` for the distribution check of step 1, `session` for the
engine profile, step 2 and the registration, `query` for step 3, `result`
for the binding of step 4, `delivery` for a batch, `finalization` for the end
after the last batch, and `consumer` for an exception of the caller's own
code. A failed cleanup step's `PIE-R5001` entry names `unregister` or
`close`.

The attempt's `outcome` takes the existing values. The statement runs, and
its whole result is read, when the handle is first entered; batches are then
cut from that result. `transaction` is `NOT_STARTED` until the statement
starts, `UNKNOWN` while it runs, and `COMMIT_ACK` once `to_arrow_table()` has
returned the whole result, because the statement ran in its own auto-commit
transaction, which ended then. A statement that fails, or that a
cancellation or the deadline interrupts before `to_arrow_table()` returns,
leaves `UNKNOWN`. When the route observes the deadline or a cancellation only
after `to_arrow_table()` has returned, the attempt still ends with no batch,
and `transaction` stays `COMMIT_ACK` (the owner's choice): the deadline is
`PIE-R3001` with `phase` `query`, and the cancellation is `PIE-R3009` with no
`phase`, as for any cancellation. `cleanup` is
`LOCAL_CLOSED_REMOTE_UNOBSERVED` once step 5 has run and none of its steps
failed, since there is no server whose end could be observed, and `FAILED`
when one did. The owner accepted these values, the details
`DUCKDB_RESULT_CHECK` and `DUCKDB_ARROW_CAPTURE_COPY` and these phase names
on 2026-11-11, and chose `COMMIT_ACK` for the late observation the same day;
it then accepted the details `DUCKDB_DRIVER_PROFILE` and
`DUCKDB_SESSION_CONTEXT`.

## Other entry points

- `export_bundle` refuses a DuckDB query with `PIE-R1004`
  `DUCKDB_BUNDLE_ENTRY` before it builds anything.
- `save`, `save_recoverable`, `recover`, `relay_live` and the job store keep
  their route sets: `duckdb_arrow` is not one of them, and a DuckDB query is
  refused there with `PIE-R1003` `PUBLIC_ROUTE_UNAVAILABLE` before any
  workspace is opened.
- `pietto explain --project` and every inspection stay non-executing, and no
  DuckDB catalog is inspected.

## Compile refusals

A DuckDB emission reports only the blockers of the table below, and no other
`PIE-B10xx` detail (*derived*). A contract that breaks its schema is still
`INPUT_REJECTED` with `emission_contract_schema` and has no blockers.

- Rules 1–29 are checked together. The document lists one blocker for each
  rule that fails, in rule order, and none for a rule that holds.
- A rule that fails at several sites reports the first one only: source and
  stage sites in source order (path, line, column), source fields in shape
  order, and premises in contract order (`environment`, then each source's
  `premises`, in `sources` order).
- A rule whose subject is absent holds: rules 8 and 13 need the `where`,
  rule 14 the parameter, and rules 21–29 a contract entry for the read
  source.
- When the plan is unavailable, rule 5 reports at the plan's first blocker,
  and rules 6–29 are not checked.
- Rule 16 counts the nodes of the SQL AST that the adapter will build, from
  the plan and before anything is built, as the existing emitter counts them
  before it builds a query, so it is one of rules 1–29. A built AST with
  another count does not correspond to the plan (rule 30).
- Only when rules 1–29 all hold is the SQL built, verified, rendered and put
  in its document; then the first of rules 30–33 that fails is the only
  blocker.

"Existing" names the suggestion text that the other targets give the same
detail today. A suggestion "by the premise rule" is the existing text for
that premise detail with the DuckDB value of the premise table in it.

| # | Code | Detail | Fails when | Site | Suggestion |
| ---: | --- | --- | --- | --- | --- |
| 1 | `PIE-B1005` | `inconsistent_declared_scope` | Two declarations of one premise key in one scope have different values | The later declaration | Existing |
| 2 | `PIE-B1003` | `target_release_not_reviewed` | `target.release` is not `"2.0.0"` | None, as today | `the reviewed duckdb release is "2.0.0"` |
| 3 | `PIE-B1003` | `literal_policy_not_admitted_on_target` | The literal policy is not `preserve` | The statement | `DuckDB emission takes --literal-policy preserve only` |
| 4 | `PIE-B1003` | `premise_not_admitted_on_target` | An `identifier_case`, `session_sql_mode` or `session_time_zone` premise is declared | The declaration | `remove this premise; the DuckDB route does not use it` |
| 5 | `PIE-B1003` | `duckdb_relation_shape_not_admitted` | The plan is unavailable, or the statement has a stage beyond one source read, at most one `where` and its final projection | The first such stage | `DuckDB emission admits a direct projection with at most one where comparison; JOIN, group by, windows, order by, limit, distinct, set operations, relation lets and derived sources are not available on DuckDB yet` |
| 6 | `PIE-B1003` | `duckdb_source_count_not_admitted` | The statement reads no source, or more than one | The second source read, or the statement | `read exactly one duckdb.arrow source; the DuckDB route runs one query over one Arrow table` |
| 7 | `PIE-B1003` | `duckdb_projection_not_admitted` | A result field is not a direct read of a source field | The result field | `project source fields directly, such as select: id, amount; computed values are not available on DuckDB yet` |
| 8 | `PIE-B1003` | `duckdb_filter_not_admitted` | The `where` is not one comparison of a direct read of an `Int` source field, on the left, with a direct read of the parameter | The `where` | `write one comparison of an Int field with the query parameter, such as where amount >= min_amount` |
| 9 | `PIE-B1003` | `duckdb_parameter_not_admitted` | A projection declares a parameter, or a filtered query declares other than one non-null `Int` parameter, or reads it other than once in the comparison | The parameter declaration, or the statement | `declare at most one non-null Int parameter and read it once, in the where comparison` |
| 10 | `PIE-B1003` | `duckdb_field_type_not_admitted` | A field of a read source is not established as `Int`, `Text`, `Bool` or `Float`, optional or not | The source field | `DuckDB emission reads Int, Text, Bool and Float fields; Text, Bool and Float are projected only` |
| 11 | `PIE-B1005` | `target_evidence_scope_conflict` | As on the other targets | As today | Existing |
| 12 | `PIE-B1006` | `original_profile_composition_unresolved` | As on the other targets | As today | Existing |
| 13 | `PIE-B1004`; `PIE-B1005` | `operator_environment_declaration_missing`; `operator_environment_declaration_mismatch` | The statement-scope premise is missing; it has another value than `"builtin_only"` | The statement | By the premise rule |
| 14 | `PIE-B1004`; `PIE-B1005` | `parameter_protocol_declaration_missing`; `parameter_protocol_declaration_mismatch` | The statement-scope premise is missing; it has another value than `"duckdb_prepared"` | The statement | By the premise rule |
| 15 | `PIE-B1007` | `parameter_occurrence_limit` | The placeholders exceed the `parameters` limit | The statement | Existing |
| 16 | `PIE-B1007` | `generated_structure_limit` | The read source or the result has more columns than the `columns` limit, or the SQL AST that the adapter will build has more nodes than `nodes`, counted from the plan | The statement | Existing |
| 17 | `PIE-B1006` | `negative_original_target_evidence` | As on the other targets | As today | Existing |
| 18 | `PIE-B1006` | `original_enforcement_not_fulfilled` | As on the other targets | As today | Existing |
| 19 | `PIE-B1001` | `source_family_mismatch` | A read source is not a `duckdb.arrow` source | The source | Existing |
| 20 | `PIE-B1001` | `source_mapping_missing` | A read source has no contract entry | The source | Existing |
| 21 | `PIE-B1001` | `complete_ordered_source_schema_required` | The entry does not describe every shape field once, in shape order; `related` lists the fields left out or out of order, as today | The source | Existing |
| 22 | `PIE-B1001` | `source_identifier_unrepresentable` | `relation.namespace` is not `"arrow"` | The source | `use the relation namespace "arrow"; the DuckDB route reads one registered Arrow table` |
| 23 | `PIE-B1001` | `duckdb_arrow_key_mismatch` | `relation.name` is not the connector's key | The source | `make the contract relation name equal the duckdb.arrow key` |
| 24 | `PIE-B1001` | `row_domain_matches_declaration_required` | The premise is missing or not `true` | The source | Existing |
| 25 | `PIE-B1001` | `read_only_object_declaration_required` | The premise is missing or not `true` | The source | Existing |
| 26 | `PIE-B1004`; `PIE-B1005` | `client_encoding_declaration_missing`; `client_encoding_mismatch` | The premise is missing; it has another value than `"UTF8"` | The source | By the premise rule |
| 27 | `PIE-B1002` | `nullability_mismatch` | A field's `nullable` does not fit the field | The source field | `set nullable to false for a non-null field and true for an optional one` |
| 28 | `PIE-B1002` | `physical_storage_or_domain_mismatch` | A field's `storage` or `domain` is not its logical type's row of the representation table | The source field | `use the DuckDB storage and domain of the field's logical type` |
| 29 | `PIE-B1005` | `field_domain_premise_mismatch` | A field premise disagrees with the field's `domain` | The source field | Existing |
| 30 | `PIE-B1008` | `plan_ast_correspondence` | The SQL AST breaks a rule of [SQL](#sql) or does not correspond to the plan | None | Existing |
| 31 | `PIE-B1007` | `sql_byte_limit` | The rendered SQL exceeds `sql_bytes` | None | Existing |
| 32 | `PIE-B1008` | `artifact_correspondence` | The artifact verifier refuses the document | None | Existing |
| 33 | `PIE-B1007` | `public_artifact_byte_limit` | The public document exceeds `artifact_bytes` | None | Existing |

PostgreSQL and MySQL emission of a `duckdb.arrow` source is BLOCKED with
`PIE-B1001` `source_family_mismatch` where those emitters place that detail
today, among their other blockers in their existing order; DuckDB emission of
a `postgres.table` or `mysql.table` source is rule 19.

`compile_query` raises `CompileRejected` with the BLOCKED document, and
`compile_sql` returns it, byte for byte what the command prints. A verified
document's bytes come only from the adapter; a live query is built only from
a VERIFIED document, and a forged one is refused (`PIE-B1008` at emission,
`PIE-R1004` when it would become an execution).

## Pin facts

The DuckDB facts this page relies on were observed offline on CPython 3.13.13
in the authorized probe environment, against `duckdb` `2.0.0` and `pyarrow`
`26.0.1`, on 2026-11-10. The raw outputs are owner-held working records
outside Git. CPython 3.12 comes from the packaging lane and natural CI.

- **Identity.** The cached `duckdb-2.0.0-cp312-abi3-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl`
  with sha256 `ab51ec57d329d6f3df37c0287b55d71c3fc07bb54b61d1afed09104f953b1431`
  is the archive whose `RECORD` equals the installed one apart from the
  installer's `INSTALLER` and `REQUESTED` lines; all 68 hashed `RECORD`
  entries match the installed files. Every loaded `duckdb` and `_duckdb`
  module file is owned by exactly `duckdb` `2.0.0`. `import duckdb` loads no
  PyArrow, NumPy or pandas. The engine reports `v2.0.0`, source id
  `d54cbbe3df` and platform `linux_amd64`, with `core_functions`, `icu`,
  `json` and `parquet` statically linked.
- **Lock.** Set in the table's order, every value succeeded and every row of
  both read-back lists read back as stated. After the lock, 200 statements
  were tried: on each of the 20 settings, `SET`, `SET GLOBAL`, `SET SESSION`,
  `SET LOCAL`, `RESET`, `RESET GLOBAL`, `RESET SESSION`, `RESET LOCAL` and
  `PRAGMA name = value` with another value, and `SET` through a `cursor()`.
  All 200 failed: 160 with `Cannot change configuration option ""<name>"" -
  the configuration has been locked`, naming the setting, and the 20
  `SET LOCAL` and 20 `RESET LOCAL` with `SET LOCAL is not implemented.` and
  `RESET LOCAL is not implemented.`. All 170 rows of `duckdb_settings()` read
  back unchanged.
- **Cursors.** A `cursor()` of the locked connection read back
  `python_enable_replacements` and `enable_progress_bar_print` as `true`,
  their defaults, while the connection read `false`; this is why the route
  never runs anything through a cursor.
- **No extension, file or network effect.** `INSTALL httpfs`,
  `FORCE INSTALL httpfs` and `INSTALL spatial FROM community` failed with
  `Cannot access directory "…/.duckdb/extensions/v2.0.0/linux_amd64" - file
  system operations are disabled by configuration` (the directory under the
  empty `HOME`), and `LOAD httpfs` and a `LOAD` of a file path with
  `Loading external extensions is disabled through configuration`. The
  functions of absent extensions (`st_point`, `read_xlsx`, `sqlite_scan`,
  `iceberg_scan`, `delta_scan`) failed with a catalog error naming their
  extension; the 1,161 names of `duckdb_functions()` were the same before and
  after these attempts and include none of them. `duckdb_extensions()` fails
  with the same directory refusal as `INSTALL`, so the loaded extensions
  cannot be read back. Reading, globbing, copying, attaching or exporting a
  file or an `https://` URL failed with `Cannot access file` (or
  `directory`) `"…" - file system operations are disabled by configuration`,
  through SQL and the Python relation API alike. The cells ran in a network
  namespace with no interface but `lo`, in empty `HOME`, `TMPDIR` and working
  directories, which stayed empty, so these are observed refusals, not a
  proof that no attempt exists.
- **No caller-frame scan.** A local Arrow table in the calling frame is not
  found (`Table with name probe_tbl does not exist!`); `register`,
  `unregister` and `from_arrow` still work after the lock.
- **No spill.** A sort larger than a 48 MiB limit failed with
  `OutOfMemoryException` (`no temporary directory is specified`) and wrote no
  file, while the same sort under the defaults spilled into `.tmp` in the
  working directory.
- **Lazy reads.** A registered table that wraps a NumPy array is read when the
  statement runs, so a change after `register` is visible; the capture copy
  is what keeps the snapshot.
- **Invalid UTF-8 read.** A registered table whose `string` column holds
  invalid UTF-8 was read on a default and on a hardened session, with the
  same results. Through `execute(...).fetchall()` the fetch failed (`Invalid
  unicode (byte sequence mismatch) detected in value construction`), and
  `register()` on the same connection then raised `ResourceInUseException`
  (`connection has an unfinished result from execute()`). Through
  `sql(...).to_arrow_table()` nothing failed: DuckDB returned both rows as
  `string` with the invalid bytes unchanged, the result passed `validate()`
  and failed `validate(full=True)`, only PyArrow's later `to_pylist()` raised
  `UnicodeDecodeError`, and `register()` then worked. On the cells' unfiltered
  projection (`select s from bad`), read through `register`, `sql(...)` and
  `to_arrow_table()`, DuckDB checked no UTF-8; the route's filtered,
  parameterized read was not observed. Step 3 of the [capture](#capture),
  with its full validation, is the route's only UTF-8 check by design. The two paths did not
  fail alike, so this is no reason for step 3 of the session to use the
  relation API. Its reasons are that `execute(...).to_arrow_table()` warns,
  and that an unfinished result could not reach another attempt anyway,
  because each attempt has its own connection.
- **Copy measure.** `Table.nbytes` counts only a slice's referenced range
  (620 bytes for 10 rows of a 100,000-row table whose buffers hold 6,200,004);
  `pa.concat_arrays` of a column's chunks gave buffers disjoint from the
  caller's, with only the 4-byte final string offset beyond `nbytes`, while
  `combine_chunks` of one chunk shared the caller's buffers and
  `Array.copy_to` copied the whole parent buffer. S04 chooses the copy and
  verifies it.
- **Values.** Invalid UTF-8 passes `Array.validate()` but fails
  `validate(full=True)`; `-0.0` keeps its sign bit through projection, filter
  and `to_arrow_table()`.
- **NUL.** On 2026-11-11, before the route admitted NUL, in the same
  environment: `Text` values with a NUL at the start, in the middle or at the
  end, values of only NUL (1, 3 and 40 of them), values of at most and of
  more than 12 bytes, multibyte text, `""` and NULL went through the route's
  own settings, copy and statement bytes (the projection and the filtered
  `<>` form), `to_arrow_table()`, the result binding and the batches, in one
  chunk and as 6,000 rows in three and four chunks, and came back with every
  byte and code point; `strlen` and `length` counted them all. Written into
  DuckDB storage (`CREATE TABLE ... AS` from the registration, and `INSERT`
  with a bound `str`), they read back unchanged; `=` and `<>` against a bound
  `str` parameter, with and without `CAST(... AS VARCHAR)`, `DISTINCT`,
  `GROUP BY` and an equality join all agreed with a Python oracle, so `'a'`,
  `'a\0'` and `'a\0b'` stayed distinct. The route compares no `Text` (B1
  projects it only), so the comparisons describe the engine, not a route
  form.
- **SQL form.** The form of [SQL](#sql), registered as `pietto_arrow_0`
  under the settings above, agreed with a Python oracle written before the run
  for each of the six operators and the parameters -2^63, -1, 0, 7 and
  2^63-1 over a table with a NULL key; an input-row permutation gave the same
  bag, the relation API emitted no warning, and a 4,096-column projection
  ran.

## Usability

| Spelling | Canonical form | Works with | Errors | Discoverability |
| --- | --- | --- | --- | --- |
| `source orders: Order = duckdb.arrow("orders")` in an explicit-module module | As written; `pietto fmt` keeps it byte for byte | `check --project`; `emit-sql --project --dialect duckdb`; `compile_sql`, `compile_all_sql`, `compile_query`; `execute(route="duckdb_arrow", access=DuckDBArrowInput(name="orders", table=t), premise=None)` | Not one non-empty string literal: `PIE-S2306` `Invalid source connector arguments for duckdb.arrow`, except that an argument of unknown type reports only its own diagnostic, as for `mysql.table` (see [source connector](#source-connector)). A single file or legacy-flat project: `PIE-S2306` `Unknown source connector: duckdb.arrow`. Another dialect: `PIE-B1001` `source_family_mismatch`. An unsupported shape: `PIE-B1003` with a detail and suggestion above. An input that does not match: `PIE-R1002` `DUCKDB_ARROW_SCHEMA`; too large: `DUCKDB_ARROW_CAPTURE_LIMIT` | The source connectors of the language guide, this page, the capability page's DuckDB subsection and the release notes |

## Shared-page hunks

S08 applied these to the shared pages at integration, one page at a time.

- `docs/spec/diagnostics.md`: the `PIE-R1001` row adds `premise=None` on
  `duckdb_arrow`; the `PIE-S2306` row names `duckdb.arrow`; the `PIE-B1001`,
  `PIE-B1003`, `PIE-R1002`, `PIE-R1004`, `PIE-R2002` and `PIE-R2006` rows
  name the new details above. The `PIE-R2001` and `PIE-R2002` rows already
  cover the selected route's PyArrow, so check 12 (see
  [execute API](#execute-api)) changes neither.
- `docs/execution.md`: a "DuckDB Arrow" route section (install, the input, the
  settings, the capture, the failures) and the support-matrix row. The three
  passages named under [execute API](#execute-api) state the `duckdb_arrow`
  order: the `execute()` entry and the attempt-open order of the errors
  section put PyArrow in `execute()` and the driver when the attempt opens,
  and the request-check paragraph adds the `duckdb_arrow`/`duckdb` pair,
  check 9 after `access`, and checks 12 and 13 after `limits` (*derived*).
  The class sentence (`RequestRejected` (PIE-R1xxx) means nothing connected)
  admits `PIE-R2001` and `PIE-R2002` from `execute()` on `duckdb_arrow`, and
  the `PIE-R2003` that `mysql_rows` and `postgres_adbc` already raise there.
- `docs/project-package.md`: `--dialect {postgres,mysql,duckdb}` and the
  DuckDB columns of the contract value and premise tables.
- `docs/language.md`: `duckdb.arrow` among the source connectors.
- `docs/capabilities.md`: its own "DuckDB local path" subsection.
- `docs/spec/project-cli-json-v2.md`: `duckdb` as a `dialect` value.

S04 gives the `execute()` docstring ("The driver and environment are checked
when the attempt opens") the same `duckdb_arrow` clause, and revises the
`RequestRejected` and `AttemptFailed` docstrings in
`src/pietto/execution/_errors.py` to match the revised class sentence.

## Open items

| Item | Owner | Latest point |
| --- | --- | --- |
| The D79.01 refusal mapping, the D79.04 `-0.0` admission and this page's *derived* rows, stated as inform: the `arrow` namespace; the storage and domain spellings; the premises and `premise_not_admitted_on_target`; the domain check at capture, and examining only the table fields that source fields name; Pietto-owned identifiers; admitting `--all` and `compile_all_sql`; `MAX_PARAMETERS` 65,535 in place of the DuckDB value that D79.05 expected; `columns` 4,096, the MySQL value; the settings beyond D79.06 (`allow_extension_repositories`, `allow_persistent_secrets`, the two progress-bar settings and the four `arrow_*` settings) and the fixed `threads` 1 and `memory_limit` 256 MiB; the closed order of compile refusals with its reused details, including the codes outside D79.01's list (`PIE-B1002`, `PIE-B1004` to `PIE-B1008`, and `PIE-R2001`, `PIE-R2002` with the existing driver details) | The lead | Before this page binds. Closed: stated to the owner on 2026-11-11, before S01 bound and S04 sealed; they stand with this page's derived items (D79.12; the B1 audit's [route deferrals](../phases/phase-79/completion-audit.md#route-deferrals-due-at-b1)) |
| Whether `duckdb.arrow` changes the built-in catalog (D76.12) | The lead, at S02 | Before the B1 batch push. Closed before that push: it does not, since no input of the extension's language sync changes, so B1 needs no extension sync (D79.16) |
| The release-note fragment `79-s01-duckdb-arrow-route.md` describes B1 as the batch delivers it. Each later slice checks and edits its own lines there and adds no second B1 fragment: S03 the emission and blocker lines, S04 the execute, capture and session lines, S05 the install and pin line, S07 the qualified platforms after S06. The batch audit compares the fragment with this page | Each slice; the batch audit | Before each slice seals; the B1 batch audit. Closed: the batch audit of 2026-11-14 compared the fragment with this page and found one low, the sentence on PostgreSQL and MySQL output, which the first documentation commit after the push scoped to this route |

## B2 (pending)

This section is B2's specification, written in its slice T01 before any B2
code. **No published release carries B2**: until one does, the sections
above bind, and every form they refuse stays refused with the texts they
state. Once a release carries B2, the rules below replace the rows of the
sections above that they name. Each of B2's code slices T02–T05 moves the
rows it lands from here into those sections, in its own commit, and the
closeout T08 checks that nothing is left here.

The rules come from PL.47, the owner's answer of 2026-11-15 to the B2
Gate 1 sheet, which revises D79.04's capture limits and this page's
`memory_limit` rule for B2, and from the lead's choices that PL.47 records:
NULLS clauses as the PostgreSQL emitter places NULL (as D78.02 for SQLite)
and B1's qualification framework. Rows marked *derived* are this page's
consequences of those decisions and of the T00 probe
([B2 pin facts](#b2-pin-facts-t00)); the lead states them to the owner as
inform. The owner saw the new and rewritten refusal texts before they bind
(PL.47) and agreed to them as written (PL.50); T02 binds them in code.

### B2 admission

B2 keeps B1's [admission](#admission) and replaces these rows:

| Admission | Exact limit |
| --- | --- |
| Relational shape | One read of the source, then at most one `where`, at most one `group by`, the final projection, at most one `having`, at most one `order by` and at most one `limit`. No relation `let`, derived source, second input, JOIN, window, `qualify`, `distinct`, set operation, typed VALUES body or table function. |
| Projection | Without `group by` or an aggregate: direct reads of source fields, as in B1. With either: direct reads of `group by` keys and the aggregates `count()`, `count(f)`, `sum(f)` of an `Int` field `f`, and `min(f)` and `max(f)` of an `Int` or `Float` field `f`, each over a direct read of a source field. No computed value, and no other aggregate: `avg`, `count_distinct`, `sum` of a `Float` and the rest stay refused. |
| Grouping | Each `group by` key is a direct read of a source field of one of the four types, optional or not. NULL keys form one group, and a `Float` key puts `-0.0` and `0.0` in one group (see [Float values](../language.md#float-values)). The number of keys has no limit of its own beyond `columns` and `nodes`. |
| Predicates | A `where` reads source fields and a `having` reads the query's selected outputs. Each is built from comparisons `a <op> b`, where `<op>` is `==`, `!=`, `<`, `<=`, `>` or `>=`, one side is a direct read (of a source field in `where`, of a selected output in `having`), the other is a literal or a parameter read, and both have one type, `Int`, `Text`, `Bool` or `Float`; from `x is None` and `x is not None` of such a read; and from `and`, `or` and `not` of these. A comparison of two reads, or of an `Int` with a `Float`, and a bare `Bool` read used as a test, such as `where flag`, stay refused, while `where flag == True` is admitted (*derived*: PL.47 names comparisons with literals and parameters). |
| Order and limit | Each `order by` key is a direct read of a source field (in a query without `group by` or an aggregate) or a selected output, of one of the four types, ascending or descending. The `limit` is the static non-negative `Int` that the language takes. |
| Literals | `Int`, `Float`, `Text` and `Bool` literals. An explicit-module project has no constants (PIE-S2392, [Top-level constants](../language.md#top-level-constants)), and the language reads a sign before a number as a unary operator, so a unary `-` whose operand is an `Int` or `Float` literal is admitted as one signed literal, that literal's negation, such as `-5`, or `-0.0`, a negative zero (*derived*). Every other unary `-` or `+`, such as `-amount`, `+5` or `- -5`, is a computed value and stays refused. A `Text` literal that holds NUL is refused (rule 8b). |
| Parameter | Any number of declared parameters, each non-null `Int`, `Text`, `Bool` or `Float`, each read at least once and only in `where` and `having` comparisons; one parameter may be read several times. Values bind through the existing exact binding (`execute(parameters=...)`, PIE-R1006). |
| Columns | `Int`, `Text`, `Bool` and finite `Float`, as in B1; B1's rule that `Text`, `Bool` and `Float` fields are projected only does not hold. |

Results are bags without `order by`, as in B1. With `order by` the rows come
in key order, rows that tie on every key have no promised order, and a
`limit` keeps the first rows of that order, the engine choosing among rows
that tie at its boundary; a `limit` without `order by` keeps rows the engine
chooses. `-0.0` and `0.0` tie. `count` gives a non-null `Int`, 0 over no
rows; `sum` an optional `Int`, NULL over no rows or only NULL values; `min`
and `max` keep their argument's type and give NULL likewise, and a `Float`
`min` or `max` whose extreme class holds both zeros shows some member's
value, as a merged row does. A `group by` over no rows gives no rows, and an
aggregate without `group by` gives one row.

A `sum` outside signed 64 bits fails the statement with PIE-R3003 (`phase`
`query`) and never returns a wrong value. Whether the statement fails when
the out-of-range group is removed by a `having` on another output, or lies
beyond the `limit`, depends on DuckDB's plan: it may fail, or return the
other rows correctly (*derived*; both were observed, see
[B2 pin facts](#b2-pin-facts-t00)), as the language leaves such failures to
the plan ([Aggregates](../language.md#aggregates-and-grouping)).

`sum` and `avg` of a `Float` stay refused: DuckDB `2.0.0` returns an infinity
when a `DOUBLE` sum overflows, where Pietto has no infinite value. T00 also
observed a checked spelling, `CASE WHEN isinf(sum(x)) THEN error(...) ELSE
sum(x) END`, which failed exactly on overflow, like PostgreSQL's checked
binary64 evidence. Opening that checked `sum` needs a later decision of the
lead, since PL.47's tier 1 names `sum`, and its own qualification cells.
`avg`, of an `Int` or a `Float`, lies beyond that tier: opening it needs the
owner, on the lead's proposal with its own qualification cells. B2 opens
neither.

### B2 SQL

T02, T03 and T04 own the exact bytes and their goldens. Every form they
write satisfies B1's rules of [SQL](#sql) with these changes:

- **Statement.** One `SELECT` with optional `WHERE`, `GROUP BY`, `HAVING`,
  `ORDER BY` and `LIMIT`, and no `WITH`, subquery or second statement. Its
  only function calls are the aggregates `count`, `sum`, `min` and `max`.
- **Names.** The select list and `WHERE` write a source field as `"c<k>"`,
  as B1 does, so B1's statements keep their bytes. `GROUP BY`, `HAVING` and
  `ORDER BY` write it qualified, `"pietto_arrow_0"."c<k>"`, and never name a
  select label, an unqualified column or a position; `HAVING` and
  `ORDER BY` restate the expression of each selected output they read. On
  `2.0.0` a bare name in `HAVING` and `ORDER BY` finds a select label before
  a column, and quoted names compare without case, so a label such as `c0`
  or `C0` would otherwise stand for a capture column; a qualified name or an
  expression always finds the column. Duplicate labels need no rule of
  their own: the language refuses a repeated output name (PIE-S2305), and
  labels that differ only in case stay distinct Arrow fields.
- **Aggregates.** `count()` is `count(*)`; `count(f)` is `count("c<k>")`;
  `sum(f)` is `CAST(sum("c<k>") AS BIGINT)`; `min(f)` and `max(f)` are
  `min("c<k>")` and `max("c<k>")`. DuckDB sums a `BIGINT` exactly as a
  `HUGEINT`, and the cast fails the statement when the sum leaves signed 64
  bits, so no `HUGEINT` reaches a result. This checked cast is the target
  evidence of `sum`.
- **Order.** Every ascending key ends with `ASC NULLS LAST` and every
  descending key with `DESC NULLS FIRST`, so NULL sorts where the PostgreSQL
  emitter's SQL puts it (PL.47; D78.02 for SQLite). DuckDB's own default
  puts NULL last in both directions. No session setting `default_null_order`
  is set.
- **Text order.** No `COLLATE` clause is written. `Text` compares, groups
  and orders by its UTF-8 bytes, which is code point order, under `2.0.0`'s
  default collation, the empty string, which the session reads back and the
  lock keeps ([B2 capture and session](#b2-capture-and-session)). This is
  the contract's collation `C` (*derived*).
- **Literals** (*derived*). A signed literal ([B2 admission](#b2-admission))
  is written as one literal with its sign, never as an operator. An `Int`
  literal is `CAST(<n> AS BIGINT)`, `<n>` its decimal digits with any minus
  sign inside the cast, so `CAST(-9223372036854775808 AS BIGINT)` holds the
  least value; `::` is never written. A `Float` literal is
  `CAST('<r>' AS DOUBLE)`, `<r>` the shortest decimal that reads back as the
  same finite binary64 value, with its sign, so `-0.0` stays a negative zero
  (DuckDB types a bare `1.5` or `-0.0` as `DECIMAL(2,1)`, which loses the
  sign of zero). A `Text` literal is `'...'` with each `'` doubled. T00 did
  not observe a backslash, nor a signed literal reaching the adapter, so
  T04's cells check quotes, backslashes, multibyte text and both `Int`
  extremes written as literals before it seals. A
  `Bool` literal is `TRUE` or `FALSE`.
- **Predicates.** `x is None` is `IS NULL`, `x is not None` `IS NOT NULL`,
  and `and`, `or` and `not` are `AND`, `OR` and `NOT`, with parentheses
  around every operand that is not a single comparison or test.
- **Parameters** (*derived*). Each parameter that the statement reads has
  one placeholder `$n`, numbered from 1 in the order of its first read in
  the SQL text, and every read is `CAST($n AS T)`, with `T` `BIGINT`,
  `DOUBLE`, `VARCHAR` or `BOOLEAN` for `Int`, `Float`, `Text` and `Bool`.
  DuckDB types a bound Python value by its value, and a cast alone would
  take `1.5` as the `BIGINT` 2, so the exact binding's type check (PIE-R1006)
  stays before any value reaches DuckDB.
- **Limit.** `LIMIT <n>`, `<n>` the static limit's decimal digits; a limit is
  never a placeholder, since DuckDB takes a bound NULL as no limit and a
  bound `2.5` as 2.

The document keeps B1's [envelope](#sql), with these values (*derived*):
one `parameter_uses` entry for each read, in SQL order, with the
`server_index` of its parameter's placeholder and the `physical_type`
`duckdb_bigint`, `duckdb_double`, `duckdb_varchar` or `duckdb_boolean`;
`binding_obligations` empty; and `requirements` listing the plan's original
demands with their target evidence under the rule `duckdb_b1`, so that B1's
documents keep their bytes. `operator_environment` is needed when the
statement has a `where` or a `having`, and `parameter_protocol` when it
reads a parameter.

### B2 compile refusals

B2 keeps B1's [compile refusals](#compile-refusals) and their rule numbers,
inserts rules 7a and 7b after rule 7 and rules 8a and 8b after rule 8, and
replaces rules 5 and 7–10 as below. Rules 7a, 7b, 8a and 8b are checked
together with rules 1–29 and, like rules 6–29, not at all when the plan is
unavailable. A rule whose subject is absent holds: rule 7a
needs an aggregate, 7b a `group by`, 8 a `where` or a `having`, 8a an
`order by`, 8b a `Text` literal, and 13 a `where` or a `having`. Rule 8
reports the first failing site, the `where` before the `having`. Every other
rule, site and suggestion stands. A statement that B2 still refuses reports
the details of this table; where B1 reported `duckdb_relation_shape_not_admitted`
for a stage that B2 opens, B2 reports the detail of that stage's own rule,
or nothing when the stage is admitted.

| # | Code | Detail | Fails when | Site | Suggestion |
| ---: | --- | --- | --- | --- | --- |
| 5 | `PIE-B1003` | `duckdb_relation_shape_not_admitted` | The plan is unavailable, or the statement has a stage beyond those of the relational shape above | The first such stage | `DuckDB emission admits one source read with where, group by, having, select, order by and limit; JOIN, windows, qualify, distinct, set operations, relation lets and derived sources are not available on DuckDB` |
| 7 | `PIE-B1003` | `duckdb_projection_not_admitted` | A result field is neither a direct read of a source field (of a `group by` key, when the statement groups or aggregates) nor an aggregate call | The result field | `select source fields directly, or group by keys and aggregates of fields, such as select: customer, total = sum(amount); computed values are not available on DuckDB` |
| 7a | `PIE-B1003` | `duckdb_aggregate_not_admitted` | An aggregate is not `count()`, `count(f)`, `sum(f)` of an `Int` field or `min(f)` or `max(f)` of an `Int` or `Float` field, over a direct read of a source field | The aggregate call | `use count(), count(field), sum of an Int field, or min or max of an Int or Float field; other aggregates, sum or avg of a Float and aggregates of computed values are not available on DuckDB` |
| 7b | `PIE-B1003` | `duckdb_grouping_not_admitted` | A `group by` key is not a direct read of a source field | The key | `group by source fields, such as group by customer; computed keys are not available on DuckDB` |
| 8 | `PIE-B1003` | `duckdb_filter_not_admitted` | The `where` or the `having` is not built as the predicates row above states | The `where`, or the `having` | `compare fields or selected outputs with literals or query parameters of the same type, and join the tests with and, or and not, such as where amount >= min_amount and note is not None` |
| 8a | `PIE-B1003` | `duckdb_order_not_admitted` | An `order by` key is not a direct read of a source field or a selected output, as the order row above states | The key | `order by source fields or selected outputs, such as order by total desc; computed keys are not available on DuckDB` |
| 8b | `PIE-B1003` | `duckdb_text_literal_nul_not_admitted` | A `Text` literal that the statement reads holds NUL | The literal | `remove NUL from the Text literal; DuckDB emission writes no NUL into SQL text` |
| 9 | `PIE-B1003` | `duckdb_parameter_not_admitted` | A declared parameter is optional, is not `Int`, `Text`, `Bool` or `Float`, or is read nowhere or outside a `where` or `having` comparison | The parameter declaration, or the statement | `declare non-null Int, Text, Bool or Float parameters and read each one in a where or having comparison` |
| 10 | `PIE-B1003` | `duckdb_field_type_not_admitted` | A field of a read source is not established as `Int`, `Text`, `Bool` or `Float`, optional or not | The source field | `DuckDB emission reads Int, Text, Bool and Float fields` |

The suggestions of rules 5 and 7, the only DuckDB texts that said "yet",
drop it, and those of rules 5 and 7–10 name the forms B2 opens (PL.47).
Rule 6's suggestion stands. Rule 16 counts the
nodes of the SQL AST that the adapter will build for every B2 form, as for
B1.

### B2 capture and session

B2 keeps B1's [capture](#capture) and [session](#session-and-attempt),
with these changes (PL.47 for the limits, *derived* for the rest):

1. **Rows.** The caller's table has at most 1,048,576 rows; otherwise
   `DUCKDB_ARROW_CAPTURE_LIMIT`. This is the first check.
2. **Schema**, as B1's step 2, except that a table field that no source
   field names counts toward no byte limit (step 3); it is still not copied.
3. **Bytes.** The selected columns, the table fields that the source fields
   name, measure at most 256 MiB (268,435,456 bytes) together, as the sum of
   each selected column's `pyarrow` `nbytes` before any copy; otherwise
   `DUCKDB_ARROW_CAPTURE_LIMIT`. A field that no source field names does not
   count, and a column that two source fields name counts twice, as the copy
   holds it twice. `nbytes` counts the referenced ranges and validity
   bitmaps; it is a logical admission measure with no physical or
   peak-memory guarantee.
4. **Values** and 5. **Copy**, as B1's steps 3 and 4.

Because the bytes are measured over the selected columns, the schema check
now comes before the byte limit: a table whose selected columns exceed
256 MiB and whose schema also fails reports `DUCKDB_ARROW_SCHEMA`.

In the session, `memory_limit` is set to `'1GiB'` and read back as
`1.0 GiB`, and its alias `max_memory` is read back as `1.0 GiB`; this fixed
value replaces the rule that `memory_limit` is 16 times the capture limit.
`default_collation` joins the values read back to their `2.0.0` value, the
empty string, and is not set. `threads` stays 1, and every other row of
both lists is unchanged. A statement that needs more memory fails with PIE-R3003
(`OutOfMemoryException` on `2.0.0`), and nothing spills. `to_arrow_table()`
still reads the whole result before the batches, outside `memory_limit`, and
a result beyond `ExecutionLimits.max_bytes` (64 MiB by default) is refused
when its batches are cut, as today (PIE-R3004). One `execute()` therefore
holds the caller's table, the copy of at most 256 MiB, at most 1 GiB in
DuckDB and the read result at its peak; T00 measured at most about 1.4 GiB
for the whole process on one host, and that is no guarantee.

### B2 usability

| Spelling | Canonical form | Works with | Errors | Discoverability |
| --- | --- | --- | --- | --- |
| The existing `where`, `group by`, `having`, `order by` and `limit` clauses, aggregates, literals and parameters, in a query or table over a `duckdb.arrow` source | As written; B2 adds no spelling, and `pietto fmt` is unchanged | `check --project`; `emit-sql --project --dialect duckdb`; `compile_sql`, `compile_all_sql`, `compile_query`; `execute(route="duckdb_arrow", access=DuckDBArrowInput(name="orders", table=t), premise=None, parameters={...})` | A shape that B2 does not admit: `PIE-B1003` with a detail and suggestion of [B2 compile refusals](#b2-compile-refusals) or of the B1 rules it keeps. An input beyond the limits: `PIE-R1002` `DUCKDB_ARROW_CAPTURE_LIMIT`. A sum outside signed 64 bits or a statement beyond `memory_limit`: `PIE-R3003`. A bound value of another type: `PIE-R1006` | This page, the capability page's DuckDB subsection and the release notes, from T08 |

### B2 pin facts (T00)

T00 was an offline probe that PL.47 allowed before Gate 0, for writing
specifications only; **it is not qualification evidence**, and B2's
qualification observes every cell again. It ran on 2026-11-15 on CPython
3.13.13 with `duckdb` `2.0.0` (`v2.0.0`, source id `d54cbbe3df`) and
`pyarrow` `26.0.1`, each process alone, with no network and empty home,
temporary and working directories, under B1's settings with a
`memory_limit` of 1 GiB. Its raw outputs are owner-held working records
outside Git.

- **Sums.** `sum` of a `BIGINT` is a `HUGEINT`, which reaches Arrow as
  `decimal128(38, 0)`. `CAST(sum(x) AS BIGINT)` was exact at 2^63−1 and
  −2^63 and after the running sum left that range and came back; a final
  sum outside it failed with `ConversionException` and no rows, and so did
  a grouped statement when one group did. On Arrow scans the plan kept
  `sum` at 3,000 and 1,048,576 rows. A `having` on another output that
  removed the out-of-range group gave the other rows correctly; the same
  group beyond an `ORDER BY ... LIMIT 1` still failed the statement.
- **Floats.** A `DOUBLE` `sum` or `avg` that overflows gives ±infinity, also
  with `ieee_floating_point_ops` false; the checked spelling above failed
  exactly on overflow. With `threads` 1 a `sum` of 1,048,576 values equalled
  Python's left fold in input order. `GROUP BY` and `DISTINCT` put `-0.0`
  and `0.0` in one class, showing the sign seen first, `min` and `max` too,
  and the two tie in `ORDER BY`.
- **NULL.** `default_null_order` reads `NULLS_LAST`: NULL sorts last in
  both directions by default, and explicit `NULLS FIRST` and `NULLS LAST`
  hold for `Int`, `Text`, `Float` and `Bool`. NULL keys form one group.
  `false` sorts before `true`.
- **Collation.** `default_collation` reads the empty string, can be set
  before the lock, and after it every `SET`, `RESET`, `SET SESSION`,
  `SET GLOBAL` and `PRAGMA` change failed and left it unchanged. Under it,
  4,009 strings with NUL, multibyte text and long common prefixes ordered,
  grouped, compared and gave `min` and `max` in code point order, as with
  `COLLATE c`.
- **Names.** Quoted names compare without case. In `HAVING` and `ORDER BY`
  a bare name finds a select label first; in `WHERE` and `GROUP BY` a
  column. Qualified names and expressions find the column everywhere.
  Duplicate labels, equal or differing in case, are accepted.
- **Literals.** `1.5` and `-0.0` are `DECIMAL(2,1)`, and `-0.0` loses its
  sign; `CAST('<r>' AS DOUBLE)` kept 1,200 binary64 values, both zeros,
  subnormals and extremes included, bit for bit. Integers are typed by value
  (`INTEGER`, `BIGINT`, `HUGEINT`); `-9223372036854775808::BIGINT` fails,
  and `CAST(-9223372036854775808 AS BIGINT)` holds the value. A NUL inside a
  quoted literal is kept; outside one it is a `ParserException`.
- **Limit.** `LIMIT NULL` and a bound `None` mean no limit, and a bound
  `2.5` means 2; `LIMIT 9223372036854775808` fails. The rows chosen among ties at the
  boundary stayed the same for one input order and changed with another.
- **Parameters.** Bound values are typed by value; `CAST($n AS T)` kept
  every sample value of the four types, and also took values of another
  type. Placeholders must be numbered without gaps.
- **Capacity.** At 1,048,576 rows with 267,386,880 bytes of selected
  columns, ten query shapes ran under the 1 GiB limit in at most 0.34 s
  each; the largest whole-process peak, a full sort on a 235-byte `Text`,
  was about 1.40 GiB with the caller's table and the copy. Under B1's
  256 MiB that sort and a grouping on 1,048,576 `Text` keys failed with
  `OutOfMemoryException`. The copy's `nbytes` equals the selected columns'.

### B2 release notes and open items

T01 changes nothing a program can observe, so it writes no release-note
fragment. T02, the first slice that does, writes
`docs/release-notes.d/79-t02-duckdb-grouping.md`; T03, T04, T05 and T08 check
and edit their own lines there, and B2 adds no second fragment.

| Item | Owner | Latest point |
| --- | --- | --- |
| This section's *derived* rows, stated as inform: the `Float` group key, `avg(Int)` and `sum` and `avg` of a `Float` left refused, the `Text` literal with NUL refused, predicates limited to comparisons of a read with a literal or a parameter (no comparison of two reads or of an `Int` with a `Float`, and no bare `Bool` test), a unary `-` on a number literal admitted as a signed literal since the project has no constants, the read-back of `default_collation` in place of `COLLATE`, qualified names, the literal and parameter spellings, the new `physical_type` values, the check order of the capture, and no limit on the number of group keys | The lead | Before T02 seals |
| Moving each row from this section into the sections above as its code lands | T02–T05; T08 checks | Before each slice seals; T08 |
