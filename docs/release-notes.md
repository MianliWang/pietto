# Pietto release notes

## MySQL project catch-up public alpha release notes — 0.1.12

**Status:** These notes cover `0.1.12`, the public alpha prepared from its
release commit, which follows the Phase77 batches and changes only version
owners and documentation. It is published only when the tag `v0.1.12`, the
versioned GitHub pre-release and PyPI carry its accepted wheel and sdist;
this document neither creates those channels nor substitutes for their byte
verification. As for earlier releases, the compiler and package are covered
on CPython 3.12 and 3.13 for Linux x86-64. CI also runs the
platform-neutral tests with CPython 3.12 and 3.13 on Windows x86-64, and
batch `emit-sql --project ROOT --all --output DIR` stays Linux-only; other
platforms and Python versions are not covered.

`0.1.12` is the release of Phase77, the MySQL catch-up, and of the Wave A
work package. MySQL projects now emit many forms that PostgreSQL projects
already emit, each only in the shapes that its own two-database run matched;
outside them MySQL keeps its `0.1.11` refusal, and the known limitations
list what MySQL still refuses. Projects on both targets also emit
`same_value` in a JOIN `on`, in the statements that its two-database run
qualified. The release also runs `now()` selected as an output and in
`relay_live` and PostgreSQL R2, fails a MySQL read at once when the server
sends an error after rows, and repairs project emission over rows without
fields, project window frame offsets, single-file MySQL `Text` literals and
table names, and MySQL `Float` membership in a let with `capture` lines. It
retires no source spelling of `0.1.11`, and the execution extras keep their
`0.1.11` pins. Each subsection below lists the changes against `0.1.11` that
a program can observe, its compatibility rows and the new refusals: the
execution changes and repairs first, then the new forms from "Float NOT
EXISTS in MySQL projects" on; the last one lists the known limitations. The
sections from 0.1.11 down describe published files.

### Highlights

- **MySQL projects catch up.** Checked `Int` `+`, `-`, `*`, sign and `abs`;
  a guarded `sum(Int)`, also conditional, over a JOIN and in two levels;
  `Int %`, `Float %` and an `Int /` that its literal proves; `stddev`,
  `variance`, `pvariance` and `pstdev` of a nullable `Float`; `Float` `==`,
  `!=` and `same_value` of two row reads, `Float` NOT EXISTS and `Float`
  GROUP BY keys; `Decimal`, `Date` and `Timestamp` query parameters; `lpad`
  and `now()`; and `first` and `last`. Each opens only in the forms that its
  two-database run matched.
- **Paired MySQL forms.** `count`, `min` and `max` over a window, the
  conditional count and the tests of a group, `count_distinct(a, b, ...)`, a
  conditional beside a JOIN and a call in an aggregate argument, `Text`
  defaults of `lag` and `lead`, and `Decimal` and `Int` arithmetic emit in the
  statements that their qualification packs pair across PostgreSQL and
  MySQL, names aside.
- **Null-safe JOINs.** `same_value(a, b)` in a JOIN `on` emits on PostgreSQL
  and MySQL in the qualified forms, as `IS NOT DISTINCT FROM` and `<=>`.
- **MySQL single files** emit an asof JOIN beside a FULL JOIN in seven
  qualified files.
- **`now()` in execution.** A PostgreSQL query can select `now()` as an
  output, `relay_live` runs queries that read `now()`, and PostgreSQL R2
  records one statement time and binds it in every page and every later
  `recover`.
- **MySQL reads.** A server error after the first rows fails the attempt at
  once, with the server's SQLSTATE (PIE-R3003).
- **Repairs.** Project SQL no longer reports VERIFIED a statement over rows
  without fields that no database parses; a project `check` refuses window
  frame offsets as a single file does; single-file MySQL writes a `Text`
  literal with a backslash or a control character in hexadecimal and refuses
  the table names that project SQL refuses; a MySQL `Float` `in` over a let
  with `capture` lines, which could return rows twice, is refused; and the
  wheel no longer ships twelve modules that only tests use.

### Upgrading from 0.1.11

- A `0.1.11` source file needs no `pietto migrate` step.
- **New refusals.** These programs were accepted by `0.1.11`:
  - A MySQL project `where v in m` or `where v not in m`, with a `Float` `v`
    and a let `m` with `capture` lines, is BLOCKED (PIE-B1003
    `membership_type_pair_not_admitted`): MySQL could return such rows
    twice. A compiled MySQL artifact that holds such a read is refused when
    it is replayed. See
    [MySQL `Float` membership in a let with `capture` lines](#mysql-float-membership-in-a-let-with-capture-lines).
  - A project WHERE or JOIN over a source whose shape declares no field is
    BLOCKED (PIE-B1003 `zero_column_stage_not_admitted_on_target`) on both
    targets: `0.1.11` reported it VERIFIED with SQL that no database
    parses. On MySQL, a capturing `let` whose `exists`, `in`, `scalar` or
    LATERAL read reads such rows is refused the same way. For such a
    statement `compile_query` now raises `CompileRejected` with this
    blocker, where `0.1.11` raised `RequestRejected` (PIE-R1004
    `QUERY_NOT_EXECUTABLE`, `detail` `COMPILED_SOURCE_FIELDS`); neither
    class derives from the other. See
    [Project SQL refuses a WHERE or JOIN over rows without fields](#project-sql-refuses-a-where-or-join-over-rows-without-fields).
  - A project `check` refuses a ROWS or GROUPS window frame offset that is
    not a nonnegative `Int` literal up to 9223372036854775807 (PIE-S2104),
    as a single file does, and `emit-sql --project` then refuses every
    object of that project. A schema_version = 1 project now also checks
    the RANGE offset of a QUALIFY window, as a schema_version = 2 project
    did. See
    [Project checks refuse window frame offsets as a single file does](#project-checks-refuse-window-frame-offsets-as-a-single-file-does).
  - A single-file `mysql.table` string with a part that ends with a space or
    holds `/`, `\` or a character outside the Basic Multilingual Plane fails
    `check` with PIE-S2306, so the file emits SQL for neither dialect. See
    [Single-file MySQL Text literals and table names](#single-file-mysql-text-literals-and-table-names).
- **SQL text changes.** Single-file MySQL SQL writes a `Text` literal that
  holds a backslash or a control character as `_utf8mb4 X'...'`, which MySQL
  reads the same in every `sql_mode`. PostgreSQL and MySQL statements that
  `0.1.11` refused emit in the forms that the subsections below state (on
  PostgreSQL, the qualified `same_value` in a JOIN `on`).
- **Execution.**
  - A PostgreSQL query that selects `now()` as an output now runs; `0.1.11`
    returned a handle whose schema export raised `HandleMisuse` (PIE-R4004).
    A `Timestamp` or `UUID` parameter, or another expression over `now()`,
    selected as an output in a program without a `Timestamp` or `UUID`
    source field is refused with PIE-R1004 (`MEANING_OUTPUT`) while it is
    prepared, before any workspace access or connection.
  - `relay_live` runs a query that reads `now()` as one statement, so
    PIE-R1004 no longer has the `detail` `STATEMENT_SNAPSHOT_ENTRY`.
    PostgreSQL `save_recoverable` and `recover` run one where R2 reads
    `now()`: a generation records the server's statement time as
    `statement_time` and binds it at each read, one more placeholder toward
    the `parameters` limit. A PostgreSQL query that reads `now()` and has
    another R2 refusal now gets that refusal instead of
    `PUBLIC_R2_STATEMENT_SNAPSHOT`.
  - On MySQL, `save_recoverable` and `recover` refuse, with PIE-R1004 and
    the new `detail` `PUBLIC_R2_UNQUALIFIED_FORM`, a query in a form that
    `0.1.11` refused (see the known limitations). A reader that lists
    `detail` values must add it.
  - On `mysql_rows`, a server error after the first rows fails the attempt
    when the read reaches it, with PIE-R3003, the server's SQLSTATE, `end`
    `FAILED` and `transaction` `ROLLBACK_ACK`. `0.1.11` waited for the read
    timeout (PIE-R3003 without a SQLSTATE, or PIE-R3001 `DEADLINE`) or
    reported PIE-R3999 `MYSQL_ROWSET_ARITY`. A cancel or deadline that the
    server reports as error 1317 during the read now ends it there:
    `cancel_observed` can be true where it was false, and a deadline's
    PIE-R3001 carries SQLSTATE `70100`.
  - `load_bundle` refuses a MySQL bundle with a JOIN and either a
    conditional in a definition without a JOIN of its own or a scalar call
    in an aggregate argument, unless its records and SQL are one of the
    paired forms (PIE-R1004 `COMPILED_OPERATOR` or
    `COMPILED_AGGREGATE_ARGUMENT`). `0.1.11` loaded such a bundle, which
    none of its emissions wrote.
- **Compiled bundles and saved jobs.** As with every release, those made
  under `0.1.11` or earlier are refused by code identity; new bundles keep
  the version marks `(8, 1, 8, 1)`. Keep an exact `pietto==0.1.11`
  environment for retained `0.1.11` bundles and saved jobs, or recompile
  from source.
- **Private modules.** `pietto._project.package_graph` and eleven other
  private modules that only tests use are no longer installed; importing one
  raises `ModuleNotFoundError`.
- Tools that compare exact diagnostics, SQL text or JSON must expect the
  changes listed below: the new blocker `detail`
  `zero_column_stage_not_admitted_on_target`, the new suggestion of the
  MySQL `first_last_not_admitted_on_target`, the `detail`
  `STATEMENT_SNAPSHOT_ENTRY`, which is no longer produced, the changed
  refusals of the statements and bundles in the tables below, and, in the
  statements that now emit on MySQL, R13 requirements with the existing
  evidence values `target_checked_signed64_narrowing` and
  `target_checked_binary64_overflow`.
- The output of `fmt` and the alpha surfaces `pietto lsp`, `pietto.compiler`
  and the relation-column document may still change before the Phase82
  freeze; each change is listed in these release notes.

### `now()` outputs run; other Timestamp and UUID outputs without a source are refused

A PostgreSQL query can now select `now()` as an output: `execute()` and
`save` run it, and its column is `timestamp[us]` with the civil meaning of a
`Timestamp` source field, which the statement's UTC start has, beside
`Timestamp` source fields or without any. Such an output is a SELECT item
whose whole value is the call, also as a `def` argument or in a collected
`let`, or a column that another relation selected from it, which keeps that
meaning wherever a source field's is kept, such as through `max`, whose
result admits NULL. The 0.1.10 notes said that `execute()` and `save()`
accept a query that reads `now()`; for `now()` selected as an output that
never held.

A `Timestamp` or `UUID` parameter, or another expression over `now()` such
as `coalesce(now(), now())`, selected as an output, also in a relation that
`collect` reads, now gets `PIE-R1004` (`detail` `MEANING_OUTPUT`) from
`execute()`, `save`, `save_recoverable` and `relay_live` while they prepare
it, before any workspace access or connection, when the program has no
`Timestamp` or `UUID` source field. Beside such a source field they already
refused it, with the same `detail`, or with `MEANING_UNAVAILABLE` in a
relation that `collect` reads: the output has no meaning that its result
could carry.

Before (measured at `d03d6e4b`, 0.1.11, on Linux with CPython 3.13.13 and
PyArrow 26.0.1, without a database): over a source of `Int` and `Text`
fields, `execute()` of `select: id, seen = now()` returned a handle, and
`pa.schema(result)` raised `HandleMisuse` `PIE-R4004` (`SCHEMA_EXPORT`,
`cause=AttributeError`). Its message blames PyArrow, which was not the cause.
`c = coalesce(now(), now())` and a `Timestamp` or `UUID` parameter output
did the same, and `save` reached the workspace. `relay_live` and
`save_recoverable` refused both `now()` forms with `PIE-R1004`
(`STATEMENT_SNAPSHOT_ENTRY` and `PUBLIC_R2_STATEMENT_SNAPSHOT`) and went on
to their sink and workspace checks for a parameter output. Beside
`Timestamp` source fields all four refused `seen = now()` with `PIE-R1004`
(`MEANING_OUTPUT`).

After: `pa.schema(result)` has `seen: timestamp[us] not null` in both
programs and `save` reaches the workspace; what `relay_live` and
`save_recoverable` do with `seen = now()` is in the section on their `now()`
reads below. The other outputs get `MEANING_OUTPUT` from all four, before
the `PIE-R1002` of a deployment premise that names the wrong schema.

`date_of(now())` and a WHERE comparison with `now()` run as before, and a
MySQL project still refuses `now()` with `PIE-B1003`
(`scalar_call_signature_not_admitted`) outside the position of "MySQL
project `lpad` and `now()`". No PIE code or detail is added; SQL output, CLI
JSON v1, project JSON v2, saved-result formats and the format and records of
compiled bundles are unchanged.

### `relay_live` and PostgreSQL R2 run queries that read `now()`

`relay_live` now runs a query that reads `now()`. It runs one statement, as
`save` does, so the rows its sink receives hold one `now()` value, and the
`detail` `STATEMENT_SNAPSHOT_ENTRY` of `PIE-R1004` is no longer produced.

On PostgreSQL, on both routes, `save_recoverable` and `recover` now run a
query that reads `now()` where R2 reads it: as the whole value of a SELECT
item, or as a side of a comparison in a SELECT item or in a WHERE built with
`and` and `or`, in any stage. An R2 generation is one statement for
`now()`: `save_recoverable` reads the server's UTC statement time once, in
its own transaction before its first page, records it with the generation,
and every page of that attempt and of each later `recover` binds that value
however much later it runs. `recover` still reads its data in its own later
snapshot, so the suffix it adds can hold rows committed after that time
whose value compares as before it. The generation's extraction
specification records the time as `statement_time`, and `recover` binds it
as a parameter: it is the one value `recover` takes from the workspace
without a fresh value to compare it with. A query that reads `now()` binds
one more placeholder at each read, which counts toward the contract's
`parameters` limit.

A PostgreSQL query that reads `now()` and whose SQL R2 does not read, such
as one with `date_of(now())`, `coalesce(t, now())`, `t <= now() <= u` or
`now() in (t, u)`, or one that also selects `lower(x)`, is still refused with
`PIE-R1004` (`detail` `PUBLIC_R2_STATEMENT_SNAPSHOT`) before any workspace
access or connection. That check is now the last step of R2 preparation, so
a query that reads `now()` and has another R2 refusal, such as
`PUBLIC_R2_COMPUTED_GROUP_KEY` or `REFINEMENT_RESOURCE_LIMIT`, gets that
refusal instead. It renders the bound query, so `recover` makes it only when
its restated values and parameters bind; otherwise it goes on to the
workspace, which refuses it with `PIE-R1009` (`BINDING_VECTOR` when the named
generation exists) without a connection. On
MySQL, `save_recoverable` and `recover` still refuse a query that reads
`now()` with `PUBLIC_R2_STATEMENT_SNAPSHOT` at its former place. That
`detail` now means a query that reads `now()` passed to R2 on MySQL, or on
PostgreSQL one whose SQL R2 does not read.

Before (measured at `d03d6e4b`, 0.1.11, on Linux with CPython 3.13.13,
without a database): over a source of `Int` and `Text` fields, `relay_live`
refused `select: id, seen = now()` and `day = date_of(now())` with
`PIE-R1004` (`STATEMENT_SNAPSHOT_ENTRY`) and `save_recoverable` refused them
with `PIE-R1004` (`PUBLIC_R2_STATEMENT_SNAPSHOT`). Beside `Timestamp` source
fields both refused `where stamp <= now()` and `day = date_of(now())` the
same way. `save_recoverable` refused a query that groups by its own `let`
value and has `where date_of(now()) <= date_of(stamp)` with
`PUBLIC_R2_STATEMENT_SNAPSHOT`, and so did `recover` of a query with a
parameter and `date_of(now())` whose restated parameter did not bind.

After: `relay_live` goes on to its sink checks for all of them (here
`PIE-R1001` `REFERENCE_SINK_ROOT`, as for a query without `now()`).
`save_recoverable` goes on to the workspace for `seen = now()`, with or
without `Timestamp` source fields, and for `where stamp <= now()`, and still
refuses `day = date_of(now())` with `PUBLIC_R2_STATEMENT_SNAPSHOT`. The
grouped query gets `PUBLIC_R2_COMPUTED_GROUP_KEY`, and the restatement that
does not bind goes on to the workspace.

The PostgreSQL native qualification passed on 2026-11-13: run
`now-resume-pg-20261113T163002Z-6b47a88871e31b73ad57ccac`, on PostgreSQL 18.6
over `postgres_rows` and `postgres_adbc`, gave `pass: true` with no reason
against for every cell (R2-0 to R2-4 and the `relay_live` cell), and the run
was accepted. It bound this change as first committed on the `now()` output
change (tree `2520fd61`). D77.50 carries it to the commit that integrates
this change: the experiment's compile record, apart from its record of the
installed code and each form's trust record (the bundle's `compatibility`
and `producer`, which name that code, and its pin, a digest of the bundle
bytes that hold both), the bundles without `compatibility` and `producer`,
and its page record are byte-identical there (sha256, first 16 digits, the
same on both sides: compile record `6324cbe6e6318cf0`, page record
`209c750b3c22d769`). MySQL R2 has no run, and keeps its refusal.

No PIE code or detail is added; emitted SQL, CLI JSON v1, project JSON v2
and the format and records of compiled bundles are unchanged. A generation
that does not read `now()` records the same specification as before.

### Project SQL refuses a WHERE or JOIN over rows without fields

Project SQL emission wrote a WHERE over a source whose shape declares no
field, such as a shape with only `always = check(True)`, and a JOIN of two
such sources, as a CTE with an empty column list,
`WITH "p0" () AS (SELECT  FROM ...)`, and reported it VERIFIED on
PostgreSQL and MySQL; neither database parses it. Such a statement is now
BLOCKED with PIE-B1003 `zero_column_stage_not_admitted_on_target`, once per
such WHERE or JOIN in statement order, the order of their CTEs, which may
differ from source order: a WHERE reports its stage at that WHERE, and a JOIN
reports the JOIN at its ON clause, or without a location when it has
none; an `any` filter written before a later JOIN is such a JOIN, at
its condition. MySQL has no SELECT without a column, so on MySQL a
capturing `let` that reads such rows inside its `exists`, `in`, `scalar` or
LATERAL read is refused the same way; PostgreSQL runs that inline SELECT
and keeps emitting it. A source like this read without a WHERE, through a
`let` value or by an aggregate alone emits as before.

Changed diagnostics (programs whose SQL no database parsed; every other
program is unchanged):

| Entry | Before (`0.1.11`, measured at `0541765a`) | After |
| --- | --- | --- |
| `pietto emit-sql --project` | `VERIFIED` with that SQL, exit 0 | `BLOCKED` with the blocker above, exit 1 |
| `pietto.compiler.compile_sql` | a `VERIFIED` document with that SQL | a `BLOCKED` document with the blocker above |
| `pietto.execution.compile_query` | `RequestRejected` with PIE-R1004 `QUERY_NOT_EXECUTABLE` (detail `COMPILED_SOURCE_FIELDS`) | `CompileRejected` with the blocker above |

`check --project` and single-file SQL are unchanged. A statement that
another blocker refuses keeps exactly the blockers it had: this one is
reported only when nothing else in the statement is refused. The MySQL
refusal of a `Float` `in` or `not in` read of a let with `capture` lines,
new in this release ([its note](#mysql-float-membership-in-a-let-with-capture-lines)),
yields to this one: a statement with both reports this blocker alone. A
query that reads a source without fields stays not executable, as before:
one that still emits SQL is refused by `compile_query` with that
PIE-R1004, so no execution entry ever sent this SQL to a database.

### A MySQL server error after the first rows fails with its SQLSTATE

On the `mysql_rows` route, a server error that MySQL sends after some rows of
the result now fails the attempt as soon as the read reaches it, without
waiting for the read timeout: `PIE-R3003` with the server's SQLSTATE and the
driver's error class as `cause`. Batches delivered before it stay delivered;
the batch being read is not. Such errors include a value out of range (error
1690, SQLSTATE `22003`), the error 1242 of a `scalar` read of more than one row
(SQLSTATE `21000`, as documented for every route) and the server's own
`max_execution_time` timeout (error 3024, SQLSTATE `HY000`). Pietto sets no
server-side statement limit on `mysql_rows`, so that timeout is `PIE-R3003`,
not `PIE-R3002`.

Before, the pinned mysql-connector-python 26.10.0 kept the previous row when
an error packet followed it within one batch read. If the error was the
batch's last packet, the previous row was delivered a second time as data.
Wherever the error came in the batch, it was lost:

- The reader waited for its read timeout (up to 10 s), and the attempt failed
  with `PIE-R3003` without a SQLSTATE (`cause` `ReadTimeoutError`), or with
  `PIE-R3001`, `end` `DEADLINE` and `transaction` `UNKNOWN` when the attempt's
  deadline (`limits.seconds`) passed during that wait. Both are now
  `PIE-R3003` with the server's SQLSTATE, `end` `FAILED` and `transaction`
  `ROLLBACK_ACK`.
- A guard read or a page read, which may return only a known number of rows,
  could count the repeated row as one row too many and fail with `PIE-R3999`
  (`detail` `MYSQL_ROWSET_ARITY`, no SQLSTATE) instead; it now fails with
  `PIE-R3003` and the server's SQLSTATE.
- A cancel or deadline that the server reports as error 1317 while the rows
  are read now ends the read when the read reaches that error.
  `cancel_observed` can then be true where it was false, and a deadline's
  `PIE-R3001` carries SQLSTATE `70100` and that error's class as `cause`,
  not the error of the connection that the deadline shut down.

Measured on MySQL 8.4.12 with the server's `max_execution_time` of 10 s, the
default `batch_rows` of 256 and `limits.seconds` 60: a read of 300,000 rows
that outlasted the server's limit delivered 101,632 rows both before and after
this change. Before, the attempt failed 10 s after the last of them with
`sqlstate` `None`; now it fails without the wait with `sqlstate` `HY000` and
`cause` `DatabaseError`.

Each row is now read with its own driver call. That costs about 0.7 µs more
per row in the reader alone; a whole read of 200,000 rows with `batch_rows`
4096 took 5.3–6.9 s before and 5.4–7.0 s after (five runs each). No
diagnostic code is added, no CLI JSON v1 or outcome shape changes, and the
PostgreSQL routes are not affected.

### R2 refuses the MySQL forms that `0.1.11` refused

On MySQL, `save_recoverable` and `recover` refuse a query in a form that
`0.1.11` refused, one of the forms this release opens on MySQL, with
`PIE-R1004` (`detail` `PUBLIC_R2_UNQUALIFIED_FORM`) before any workspace
access or connection: no native qualification has run R2's refined
statement of any of them. This check does not apply to `execute()`,
`save()` or bundles, and R2 of a PostgreSQL query or of a MySQL query that
`0.1.11` compiled does not change.

The check is R2's last, so a query that another R2 check refuses keeps
that refusal: a paired form (`PUBLIC_R2_PAIRED_FORM`), a query that reads
`now()` (`PUBLIC_R2_STATEMENT_SNAPSHOT`), a `Float` GROUP BY key form
(`REFINEMENT_COMPARISON_DOMAIN`) when R2 prepares it, and a `Timestamp`
parameter selected as an output (`MEANING_OUTPUT`, as in `save()`) when
its values and parameters bind. `recover` makes the check also when its
restated values or parameters cannot bind (see the
[R2 boundary](execution.md#known-limitations)).

Changed diagnostics (programs refused in `0.1.11`; no accepted program
changes):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-R1004 | R2 `save_recoverable` or `recover` of a MySQL query in a form this release opens: [`Float` statistics](#mysql-float-statistics-of-one-nullable-field), [`Float` row equality](#float-equality-of-two-row-reads-in-mysql-projects), [typed header parameters](#mysql-project-decimal-date-and-timestamp-parameters), [`lpad`](#mysql-project-lpad-and-now), [`first` and `last`](#mysql-project-first-and-last), [checked `Int` and `sum(Int)`](#mysql-project-checked-int-arithmetic-and-sumint), [conditionals, JOINs and two-level sums](#mysql-project-conditional-join-and-two-level-sumint), [`%`](#mysql-project-int--and-float-), [`Int /` proved by its literal](#mysql-project-int--proved-by-its-literal), [`Float` `not any`](#float-not-exists-in-mysql-projects) and [`same_value` in a JOIN `on`](#null-safe-same_value-in-a-project-join-on) | not reachable: the query did not compile | `PUBLIC_R2_UNQUALIFIED_FORM` |
| PIE-R1004 | R2 `recover`, with restated values or parameters that cannot bind, of a MySQL query with [`Float` GROUP BY keys](#float-group-by-keys-in-mysql-projects) or a `Timestamp` [header parameter](#mysql-project-decimal-date-and-timestamp-parameters) selected as an output | not reachable: the query did not compile | `PUBLIC_R2_UNQUALIFIED_FORM` |

### Project checks refuse window frame offsets as a single file does

A project `check`, of either schema version, now refuses a ROWS or GROUPS
window frame offset that is not, once `let` names are inlined, a
nonnegative `Int` literal up to 9223372036854775807, such as `"x"`, `-1`,
`1.5` or `9223372036854775808`, in a selected, named or QUALIFY window, a
JOIN window of a schema_version = 2 project included, as a single file does:
PIE-S2104 `Invalid window frame for function first_value: ROWS offsets must
be nonnegative integer literals up to 9223372036854775807` (`GROUPS` for a
GROUPS frame) at the call. A schema_version = 1 project now also checks a
RANGE offset of a QUALIFY window, as a schema_version = 2 project already
did.

Changed diagnostics. A schema_version = 1 project emits no SQL, so its
`check` now refuses a program it passed. `emit-sql --project` checks the
whole project first, so it now refuses such a program with that error in
place of an emission blocker, and also refuses any other object of the same
project, which emitted SQL before.

| Command | Before (`0.1.11`, measured at `a015afcf`) | After |
| --- | --- | --- |
| `pietto check --project` | no error, exit 0 | the PIE-S2104 error, exit 1 |
| `pietto emit-sql --project` of the object with the offset | `BLOCKED` with an emission blocker, such as PIE-B1004 `window_frame_offset_evidence_missing`, PIE-B1002 `window_frame_offset_out_of_signed64_range` above signed64 or, on MySQL, PIE-B1003 `window_frame_groups_approved_non_support_on_mysql`, exit 1 | `BLOCKED` with no blocker and the PIE-S2104 error in `diagnostics`, exit 1 |
| `pietto emit-sql --project` of another object | the SQL, exit 0 | `BLOCKED` with no blocker and the PIE-S2104 error in `diagnostics`, exit 1 |

An offset that reads a `let` binding with an error of its own reports
nothing more. Window count literals above 9223372036854775807 stay refused in
single files only. No diagnostic code is new, the CLI JSON and project JSON
shapes are unchanged, and a project without such an offset emits the same
SQL.

### Single-file MySQL Text literals and table names

- Single-file MySQL SQL wrote a backslash in a Text literal as `\\` and a
  line feed, carriage return, tab, backspace or Ctrl-Z as a backslash
  escape, which MySQL reads as another value under the `sql_mode`
  `NO_BACKSLASH_ESCAPES`: a WHERE test then compared the column with
  another value. A Text literal that holds a backslash or a control
  character is now written as its UTF-8 bytes in hexadecimal with the
  `_utf8mb4` introducer, as project MySQL SQL writes its Text literals in
  hexadecimal. MySQL reads it the same in every `sql_mode` and compares it
  under the column's collation, as any other literal. Another Text literal
  is unchanged, and no PostgreSQL or project Text literal changes.
- A single-file `mysql.table` string with a part that ends with a space or
  holds `/`, `\` or a character outside the Basic Multilingual Plane now
  fails `check` with PIE-S2306 at the string, as project SQL emission
  refuses such a name; MySQL `emit-sql` wrote it before. `check` knows no
  dialect, so a file that declares such a source no longer emits
  PostgreSQL SQL either, even when no statement reads that source. As for
  any `check` error, `emit-sql` of such a file reports only the `check`
  diagnostics, also for a statement that emission refused before. A string
  with a part that holds NUL or has more than 64 characters still passes
  `check`, even when its other part would fail it, and keeps its PIE-B1000
  from MySQL `emit-sql`. No PIE code is added and no JSON shape changes.

Changed single-file MySQL SQL (measured at `a015afcf`):

| Pietto | Before | After |
| --- | --- | --- |
| `where name == "a\\b\nc"` | ``WHERE `name` = 'a\\b\nc'`` | ``WHERE `name` = _utf8mb4 X'615c620a63'`` |
| `tag = "it's \\ ok"` | `` 'it''s \\ ok' AS `tag` `` | `` _utf8mb4 X'69742773205c206f6b' AS `tag` `` |
| `"\b\n\r\t"` | `'\b\n\r\t'` | `_utf8mb4 X'080a0d09'` |
| `"O'Reilly"`, `"你好"` | unchanged | unchanged |

New refusals (programs accepted before):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-S2306 | `mysql.table("𠀀.users")`, `mysql.table("app.users ")`, `mysql.table("   ")`, `mysql.table("app/users")` | `check` passes; MySQL `emit-sql` writes ``FROM `𠀀`.`users` `` and the like | `Invalid source connector arguments for mysql.table: a table or database name must not end with a space or hold /, \ or a character outside the Basic Multilingual Plane` |
| PIE-S2306 | a file whose `table q` reads `postgres.table("app.users")` and that declares an unread `mysql.table("app/users")` source | `check` passes; PostgreSQL `emit-sql` writes `FROM "app"."users"` | the same PIE-S2306 at the `mysql.table` string |

Changed diagnostics (programs refused before):

| Program | Before | After |
| --- | --- | --- |
| PostgreSQL `emit-sql` of a `table q` that reads `mysql.table("app/users")` | PIE-B1000 `PostgreSQL SQL emission is not implemented for RelationIR: q. PostgreSQL relation emission requires postgres.table(Text)` | PIE-S2306 at the `mysql.table` string |
| `emit-sql` for either dialect of another statement that emission refused, in a file that declares such a `mysql.table` source, such as a MySQL `table q` that reads `postgres.table("app.users")` | that statement's own refusal, here PIE-B1000 `MySQL SQL emission is not implemented for RelationIR: q. MySQL relation emission requires mysql.table(Text)` | only the file's PIE-S2306 |

### The wheel no longer ships modules that only tests use

Twelve private modules under `pietto._project` that no command, the Python
compile API or `pietto.execution` imports, about 22,000 lines, now live
under `tests/` as test helpers: `package_graph`,
`package_graph_inspection`, `project_bag_null_oracle`,
`project_ir_inspection`, `project_ir_pipeline`, `project_ir_pure_boundary`,
`project_job_store_verification`, `project_phase62_inspection`,
`project_phase62_pure_boundary`, `project_result_contract_correspondence`,
`project_sql_emission_portable` and `project_sql_emission_pure_boundary`.
An installed Pietto refuses `import pietto._project.package_graph` and the
other eleven with `ModuleNotFoundError`. These modules were private, and no
command, diagnostic, JSON document or SQL output changes.

### MySQL `Float` membership in a let with `capture` lines

- Fixed: MySQL project SQL (`emit-sql --project`, `compile_query`) emitted
  a `Float` `v in m` or `v not in m` written in a WHERE whose `m` is a let
  with `capture` lines, a correlated `IN` subquery. MySQL may flatten it
  into a semijoin, and its `Float` equality then gave wrong rows: in the
  Phase77 R01 qualification cells on MySQL 8.4.12, with the semijoin
  materialized beside a `VARCHAR(1000)` key (`where kw == o.kw` in the
  let), the outer rows whose `v` is `-0.0` or `0.0` came back twice in a
  fixture whose matching inner rows held both `-0.0` and `0.0`.
  PostgreSQL returned each row once. Every such read is now BLOCKED with
  PIE-B1003 `membership_type_pair_not_admitted` at the read, whatever its
  key, for `in` and `not in`, a nullable or non-null value, a literal or
  `None`.
- The same read as a SELECT item (`select: f = v in m`) emits as before,
  and so does a read of a let without `capture` lines or of a source
  (`where v in m` over `let m: from i`, `where v in iv`) and a correlated
  read of another type. PostgreSQL emits every form as before.
- A statement that emission refuses for another reason, such as an
  unreviewed MySQL release, reports the blockers it has without this one.
  A compiled MySQL artifact that holds such a read is refused when it is
  replayed. No PIE code is added and no JSON shape changes.

New refusals (programs accepted before):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | MySQL project `where v in m` or `where v not in m`, `v` a `Float` field and `m` a let of `capture o`, `from i`, `where kw == o.kw` (or `kn == o.kn`), `select: v` | VERIFIED: ``WHERE (`s1`.`v` IN (SELECT `e0`.`c0` FROM (SELECT `t1`.`c1` AS `c0` FROM (SELECT ... WHERE (`s0`.`kw` = `s1`.`kw`)) AS `t1`) AS `e0`))`` | BLOCKED PIE-B1003 `membership_type_pair_not_admitted` at `v in m` |

### Float NOT EXISTS in MySQL projects

- `emit-sql --project --dialect mysql` now emits a `Float` `==` of two row
  reads inside `not any(...)` in the forms the Phase77 R02 candidate
  emission experiment covers on MySQL 8.4.12 and nothing else: the whole
  WHERE of a query over one source `o` is `not any(z.v == o.v for z in i)`,
  or `not any(z.v == o.v and z.k == o.k for z in i)`, where `v` is a
  nullable `Float` field of `o` and of a source `i` over another table and
  `k` a NOT NULL binary-collation `Text` key of width 64 or 1000 on each
  side, after the `Float` `==`; each `==` may have its operands in either
  order. The query has no other expression, clause, JOIN or header
  parameter, reads no other query, declares no named window and no `let`
  except one relation alias of `i` that the `any(...)` reads
  (`let z = i` with `for z in z`), calls no `def`, and selects only `o`'s
  non-null `Int` (BIGINT) and nullable `Float` fields. `o` has, selected or
  not (the WHERE's CTE writes them all), exactly a non-null `Int`
  (BIGINT), a nullable `Float` and NOT NULL binary `Text` fields of width 64
  and 1000, in any order; `i`'s other fields never reach the SQL. The
  statement is the PostgreSQL one in MySQL spelling, one
  `NOT EXISTS (SELECT 1 FROM ...)`, and compiled replay and the live
  template carry the same SQL.
- The form keeps the [Float values](language.md#float-values) contract:
  an outer row is kept exactly when no inner row makes the condition true,
  once, `-0.0 == 0.0`, a NULL `v` keeps its row, and stored bits are kept.
  The opening rests on the 2026-11-11 Phase77 `s06-float-b10` matrix, where
  `anti_not_exists` matched 90 of 90 cells with the wide-key semijoin
  materialization witnessed in EXPLAIN, and on the R02 candidate emission
  experiment over Pietto's own statements. The lost Phase72 B10 record was
  not reconstructed or replayed. PostgreSQL output is unchanged.
- R2 `save_recoverable` and `recover` refuse a query of these forms with
  PIE-R1004 (`detail` `PUBLIC_R2_UNQUALIFIED_FORM`) before any workspace
  access or connection, since no native qualification has run its refined
  statement (see the [R2 boundary](execution.md#known-limitations)).
- The candidate emission experiment passed on 2026-11-14 in its eighth
  freeze, one run per database, each judged `QUALIFIED` with no reason
  against: PostgreSQL 18.6
  `r02-pg-20261114T015508Z-60cf4c2ca867beefd88ddd59` and MySQL 8.4.12
  `r02-my-20261114T015508Z-0ff6ea11ac361c2ba8fe8910`. The four forms
  matched, the PostgreSQL reference matched, and the pair judgment
  accepted the three templates (the bare `Float` `==` and the 64- and
  1000-character keys) for opening. The seventh freeze's run is void and
  carries nothing: its harness wrote each record in sorted key order,
  which its judge read as the execution order, so no run of it could
  qualify. The runs bound this change as first committed on the head of
  the first `0.1.12` batch (tree `299b8225`). D77.50 carries them to the
  commit that integrates this change: the experiment's projects, emitted
  SQL and compile-only observations are byte-identical there, and both
  halves' compile records are identical apart from the harness's install
  identity (sha256, first 16 digits, the same on both sides: `sql.json`
  `2559a63fe3378b44`, `compile-check.json` `bfe31e92338b5416`, compile
  records as sorted-key JSON without their `identity` field PostgreSQL
  `47273b5ec14413f7` and MySQL `ea93a59401231227`).
- Kept refused on MySQL with PIE-B1003 `comparison_type_pair_not_admitted`:
  every other `Float` comparison of two row reads inside `any(...)` or
  `not any(...)`, such as `any(...)` itself, `!=`, `not (!=)` or
  `same_value` inside it, a key before the `Float` `==` or a second key, a
  key of another width or of two widths, a nullable or `Int` key, a
  non-null `Float` operand, another test inside or beside the
  `not any(...)`, `not any(...)` as a SELECT value, beside a JOIN or over an
  upstream query, `i` over `o`'s table, an outer source with any other
  field, and a query that declares another `let` (also one it never reads)
  or a named window or calls a `def`. A statement of the forms above that
  emission refuses for another reason, such as an output label past 256
  characters, reports the earlier blockers, this PIE-B1003 included.

Changed diagnostics (programs refused before; no accepted program changes;
MySQL projects, no message text changed):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | `where not any(z.v == o.v for z in i)`, alone or with `and z.k == o.k` of a NOT NULL binary `Text` key of width 64 or 1000, over an outer source of exactly an `Int`, a nullable `Float` and those two keys | `comparison_type_pair_not_admitted` at the `where` | none: the statement emits |

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
  [R2 boundary](execution.md#known-limitations)).
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
  statement (see the [R2 boundary](execution.md#known-limitations)).
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
  project `Int` `/` stays refused (D77.23) outside the R08 cell of
  [its subsection](#mysql-project-int--proved-by-its-literal), and `Int` `%` outside the
  S15 cell of [its subsection](#mysql-project-int--and-float-).

A statement still refused reports exactly the blockers it has without this
note, object for object, a cell's own included: selecting `s = a + b` beside
`t = a + 1` keeps PIE-B1002 `arithmetic_outside_physical_range` at both, and
`x = sum(a)` beside `y = sum(a + b)` keeps PIE-B1004
`sum_int_aggregate_range_proof_missing` at `x` and PIE-B1002 at `y`.

### MySQL project conditional, JOIN and two-level `sum(Int)`

- A MySQL project now emits each `sum` of an `Int` of a statement that is,
  names aside, one of the nine forms that the
  [language page](language.md) states: the conditional sums C1 to C4
  (`sum(o.amount for o in group if o.flag)` per `INT` key over a nullable
  or a non-null `BIGINT`, `if not o.flag` and `if o.flag is None` without a
  key, and `if o.id > L` for an `Int` literal `L` of 0 or more under
  `preserve_literals`), the sums over one JOIN J1 to J3 (an INNER JOIN
  grouped by an `INT` field of the joined side summing a FROM field, a LEFT
  JOIN grouped by the FROM side's unique key, and an `INT` field for J3,
  summing a joined field) and the two-level route T1 and T2 (per order,
  then per customer). The selected definition's SELECT items are a subset
  of its form's with one sum at least, and T1's or T2's `per_order` selects
  exactly its form's items; each is in any order, under any names, in a
  `query` or a `table`.
- A `sum` there is the guarded `SUM` of the S02 cell, a nullable `Int`
  (`my_signed_int`): `CASE WHEN SUM(x) > 9223372036854775807 THEN
  CAST(9223372036854775807 AS SIGNED) + CAST(1 AS SIGNED) WHEN SUM(x) <
  -9223372036854775808 THEN CAST(-9223372036854775808 AS SIGNED) - CAST(1 AS
  SIGNED) ELSE CAST(SUM(x) AS SIGNED) END`. A conditional sum is
  `COALESCE(` that guard over `CASE WHEN TEST THEN x END`, `, 0)`, a non-null
  `Int`, 0 when no row's test is True. In range each is the exact sum;
  outside it the `BIGINT` arithmetic of its branch raises error 1690
  (SQLSTATE 22003), never a clamped value. Each R13 requirement carries the
  evidence `target_checked_signed64_narrowing`.
- PostgreSQL SQL and every other public PostgreSQL output are unchanged.
  Compiled bundles and live templates replay the same SQL. Emission reduces
  the statement as written over its bound contract to the form, and plain
  verification re-derives emission's refusals; compiled replay reduces its
  records to the same form law. A relation alias, an imported source, a
  read qualified by its source's name and parentheses leave the form's
  records apart from source positions and the source digest, so only
  emission and plain verification refuse them.
- R2 `save_recoverable` and `recover` refuse a query of these forms with
  PIE-R1004 (`detail` `PUBLIC_R2_UNQUALIFIED_FORM`) before any workspace
  access or connection, since no native qualification has run its refined
  statement (see the [R2 boundary](execution.md#known-limitations)).
- The raw MySQL 8.4.12 primitives behind these forms, each form's guarded
  statement over its own seeded tables, matched the signed 64-bit `Int`
  outcome beside PostgreSQL 18.6. The candidate emission experiment then
  ran the emitted SQL of the nine forms on both databases and passed on
  2026-11-14 in its second freeze: run
  `20261114T004403Z-5079c228d8f801082cb39673` judged every form
  `EMITTED_FORM_MATCHED`, both its safe and its overflow half included,
  with no receipt problem, the conditional, JOIN and two-level families
  matched, and the verdict was `MATCHED`. The run bound this change as
  stacked on S01's (tree `69d42812`). D77.50 carries it to the commit that
  integrates this change: the experiment's projects and emitted SQL are
  byte-identical there (`sql.json` sha256, first 16 digits,
  `76be71ac71ae8a02`), and its compile record is identical apart from the
  harness's install identity (the sha256 of the record as sorted-key JSON
  without its `identity` field, first 16 digits, the same on both sides:
  `9539a21293f93a07`).
- Every other MySQL project `sum(Int)` keeps the refusal it has without this
  note, object for object (PIE-B1004 `sum_int_aggregate_range_proof_missing`
  where that is its blocker). Among them are a test other than `F`,
  `not F`, `F is None` and `I > L`, a compound test, a negative literal,
  C3 under `bind_safe_literals`, an `INT` argument, a conditional sum beside
  `count()` or a direct sum, WHERE, ORDER BY, HAVING, LIMIT, DISTINCT, a
  header parameter, a relation alias, an imported source, a read qualified
  by its source's name in C1 to C4, parentheses, a JOIN of another kind,
  key, carrier or ON order, two sums over a JOIN, a JOIN or two-level form
  over a source with any field beyond the language page's two tables (the
  JOIN carries every field), an upstream query that is not T1's or T2's
  own, a third level, and the [style page](style.md)'s two-level example,
  whose `amount` is non-null.

Changed diagnostics: a MySQL statement whose only blockers in `0.1.11` were
PIE-B1004 `sum_int_aggregate_range_proof_missing` at sums of these forms
is now VERIFIED with those blockers gone. A statement still refused
reports exactly the blockers it has without this note, object for object,
such a sum's own included: a form beside `extra = sum(amount) + 1` keeps
the one PIE-B1003 `aggregate_composition_not_admitted_on_target` that
`0.1.11` reports.

### MySQL `Float` statistics of one nullable field

MySQL project SQL (`emit-sql --project`) now emits `stddev(x)`, `variance(x)`,
`pvariance(x)` and `pstdev(x)` of a `Float` in one shape only: the single
select item of a query or table whose only other clause is `from` one source,
with no `let`, JOIN, `where`, `group by`, window, `order by`, `limit`,
DISTINCT, set operation or header parameter (read or not), and whose argument
is one direct field of that source declared `Float | None` (a nullable
`DOUBLE` column), as in

```pietto
query spread:
    from orders
    select:
        d = stddev(ratio)
```

They are written as MySQL's own `STDDEV_SAMP(x)`, `VAR_SAMP(x)`, `VAR_POP(x)`
and `STDDEV_POP(x)`, with no cast and no `SQRT`. The result is a nullable
`Float` (`my_double`, `finite_float`): None for fewer than two values
(`stddev`, `variance`) or for none (`pvariance`, `pstdev`). Its R13
requirement carries the evidence
`{"overflow": "target_checked_binary64_overflow"}`: in the Phase77
qualification of these four primitives on MySQL 8.4.12, each result met the
bounds that [Aggregates](language.md#aggregates-and-grouping) states for a
`Float`, and where the sum of squares overflowed MySQL failed the statement
with SQLSTATE 22003 (error 1690), as PostgreSQL does, also where the
deviation itself is finite. Compiled bundles replay the form; the compiled
record format is unchanged. PostgreSQL output is unchanged.

The shape is that of the emitted statement: the query may be read by another
relation, or sit beside a declaration with a header parameter, and its SQL is
the same. Every other MySQL shape keeps its refusal. These keep the `0.1.11`
refusal PIE-B1004 `float_aggregate_finite_result_proof_missing`: a `Float`
field that is not nullable, another aggregate beside it, `group by`,
`where`, a relation `let` (`let x = orders`, read through `from x`, in a
chain, or never read), an upstream table or query, a JOIN, `limit`, DISTINCT,
a header parameter (read or not), `union all`, `intersect all` or
`except all`, and a query or table that reads the form from another
relation. A scalar call over the result, such as
`coalesce(stddev(ratio), 0.0)`, is refused as every MySQL aggregate
composition is, with PIE-B1003 `aggregate_composition_not_admitted_on_target`.
`sum` and `avg` of a `Float` stay PIE-B1004 on MySQL: there, an overflowing
`SUM` or `AVG` returned an infinity instead of failing. Each retained refusal
is a D77.07 exception. A statement in the shape above that emission refuses
for another reason, such as an output label past 256 characters, reports
the `0.1.11` blockers, this PIE-B1004 included.

R2 `save_recoverable` and `recover` refuse a query of this form with
PIE-R1004 (`detail` `PUBLIC_R2_UNQUALIFIED_FORM`) before any workspace
access or connection, since no native qualification has run its refined
statement (see the [R2 boundary](execution.md#known-limitations)).

The candidate emission experiment passed on 2026-11-13: run
`run-20261113T020637Z-be4ccbf718489cd6311774fb`, on PostgreSQL 18.6 and
MySQL 8.4.12, ran the 32 emitted statements, and its judge found
`CANDIDATE_EMISSION_MATCHED` with no reason against; the run was accepted.
It bound this change as first committed (tree `4285cd82`). D77.45 and D77.50
carry it to the commit that integrates this change: the experiment's 39
compile documents are byte-identical there, and so are the 32 documents it
ran (sha256 of each set, first 16 digits, the same on both sides:
PostgreSQL forms `723cda85014e9b58`, MySQL forms `6510f71d873d188d`, run
documents `3db6c5daec220708` and `a0c7e14af218cc4b`).

### Changed diagnostics

Programs refused in `0.1.11`; no accepted program changes:

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1004 | MySQL project, `stddev`, `variance`, `pvariance` or `pstdev` of one nullable `Float` field in the shape above | `float_aggregate_finite_result_proof_missing` | none: VERIFIED |

### Float equality of two row reads in MySQL projects

- `emit-sql --project --dialect mysql` now emits a `Float` comparison whose
  two operands both read rows, in the forms the Phase77 S06 native
  qualification matched on MySQL 8.4.12 and nothing else:
  - `a == b`, `a != b`, `not (a != b)`, `same_value(a, b)` or
    `not same_value(a, b)` of two different nullable `Float` fields of the
    one source a query reads, as the whole value of one SELECT item
    (`r = f1 == f2`) or as its whole WHERE (`where f1 != f2`);
  - an INNER JOIN on `==` or `not (!=)`, or a LEFT JOIN on `==`, of a
    nullable `Float` field of each of two sources over different tables, as
    the whole `on` or followed by `and` one `==` of a NOT NULL binary-collation
    `Text` key of width 64 or 1000 on each side
    (`inner join i on i.v == o.v and i.k == o.k`).

  The query has no other expression, clause, JOIN or header parameter,
  reads no other query, declares no `let` (a relation alias such as
  `let i = items` included, read or not) and no named window, and none of
  its expressions is a `def` call. Its other SELECT items read a non-null
  `Int` (BIGINT) field, and beside a WHERE or a JOIN also a nullable `Float`
  field. Its sources have, selected or not (the CTE of a WHERE or a JOIN
  writes them all), exactly the fields of the qualification's tables in
  their order: a non-null `Int` (BIGINT) and two nullable `Float` fields for
  a same-row form; a non-null `Int` (BIGINT), a nullable `Float` and NOT
  NULL binary `Text` fields of width 64 and 1000 for each JOIN input.
  Operands and keys may be written in either order and the `Float`
  comparison comes first in the `on`. The statement is the PostgreSQL one
  in MySQL spelling, with `<=>` for `same_value`, and compiled replay and
  the live template carry the same SQL.
- The forms keep the existing [Float values](language.md#float-values)
  contract (`-0.0 == 0.0`, stored bits kept, joins keep bag multiplicity),
  which the raw MySQL statements matched under the default, hash and
  nested-loop JOIN strategies, beside a 64- and a 1000-character key.
  PostgreSQL output is unchanged.
- R2 `save_recoverable` and `recover` refuse a query of these forms with
  PIE-R1004 (`detail` `PUBLIC_R2_UNQUALIFIED_FORM`) before any workspace
  access or connection, since no native qualification has run its refined
  statement (see the [R2 boundary](execution.md#known-limitations)).
- The candidate emission experiment passed on 2026-11-13: one run per
  database, PostgreSQL 18.6 (`postgres-20261113T160609Z-6419e80a65ff82e4`)
  and MySQL 8.4.12 (`mysql-20261113T160609Z-263ec360bd590fc7`), each judged
  its 25 forms MATCHED with no reason against, and the pair judgment found
  the 25 forms and 21 cells `CANDIDATE_EMISSION_QUALIFIED` with no reason
  against. The runs bound this change as first committed on the `0.1.11`
  release commit (tree `ae0bce0a`). D77.50 carries them to the commit that
  integrates this change: the experiment's projects, emitted SQL and
  refusal controls are byte-identical there (sha256, first 16 digits, the
  same on both sides: `sql.json` `618237d3cc7d2984`, `controls.json`
  `8415451073599485`).
- Kept refused on MySQL with PIE-B1003 `comparison_type_pair_not_admitted`,
  as in `0.1.11`: every other `Float` `==`, `!=` or `same_value` of two row
  reads. That includes `any(z.v == o.v for z in z)` and
  `any(not (z.v != o.v) for z in z)`, which returned outer rows twice through
  a materialized semijoin beside a 1000-character key (the Phase72 B10
  class), and `any(z.v != o.v for z in z)`, which matched but stays refused
  (D77.29); `not any(z.v == o.v for z in z)` emits in the forms of
  [Float NOT EXISTS](#float-not-exists-in-mysql-projects). It also includes a RIGHT
  JOIN, an INNER `!=`, a LEFT `not (!=)`, a key that is not such a `Text` key
  of one width on both sides or comes first, the same field or table on both
  sides, a non-null `Float` field, any other SELECT item, and the comparison
  beside or under anything else (`not (a == b)`, `or`, a second comparison,
  ORDER BY, LIMIT, DISTINCT, a window, a WHERE after the JOIN, a second
  JOIN, an upstream query, a `union all` operand), a query that declares a
  header parameter, a `let` (also a relation alias, a chain of them or one
  the query never reads) or a named window, or that calls a `def`, and a
  query whose source has other fields, read or not, or the same fields in
  another order (a `Decimal`, a `Text` of width 255 or 4000, a third
  `Float`, a nullable key, or the same-row table as a JOIN input).
  A null-safe `same_value` `on` opens only in the cells of
  [its own subsection](#null-safe-same_value-in-a-project-join-on), none of them `Float` on
  MySQL. A statement of the
  forms above that emission refuses for another reason, such as an output
  label past 256 characters, reports the `0.1.11` blockers, this PIE-B1003
  included.

Changed diagnostics (programs refused in `0.1.11`; no accepted program
changes; MySQL projects, no message text changed):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | `r = f1 == f2` (also `!=`, `not (!=)`, `same_value`, `not same_value`) as a SELECT item, or as the WHERE, of two nullable `Float` fields of one source | `comparison_type_pair_not_admitted` at the SELECT item or the `where` | none: the statement emits |
| PIE-B1003 | `inner join i on i.v == o.v` (also `not (!=)`, and `left join` on `==`), alone or followed by `and i.k == o.k` of a NOT NULL binary `Text` key of width 64 or 1000 | `comparison_type_pair_not_admitted` at the `on` | none: the statement emits |

### Null-safe `same_value` in a project JOIN `on`

- `emit-sql --project` now emits `same_value(a, b)` in a JOIN `on`, in the
  statements the Phase77 null-safe JOIN qualification matched on both
  PostgreSQL 18.6 and MySQL 8.4.12 (D77.41, D77.52), and in no other:
  - a query that reads two sources over different tables directly in one
    INNER, LEFT or RIGHT JOIN and holds nothing else: no WHERE, ORDER BY,
    LIMIT, GROUP BY, DISTINCT, window, second JOIN, `let` (a relation alias
    such as `let r = rhs` included, read or not), header parameter, named
    window, `def` call or other query;
  - each source declares no key and has, selected or not (the JOIN's CTE
    writes them all), exactly a non-null `Int` (BIGINT) `id`, a nullable
    `v` and, as the `on` needs, a non-null `Int` (BIGINT) `k` or a nullable
    `w` of `v`'s type, in that order and under any names;
  - `v` and `w` are an `Int` (BIGINT), a `Text` of 64 characters in the
    binary collation, a `Decimal(12, 2)`, a `Date`, a `Timestamp`, a `UUID`
    or, on PostgreSQL only, a `Float`, the same on both sides;
  - each field's representation in the emission contract (storage, width
    or precision, and domain) is exactly the qualification's: an `Int` is
    `pg_int8` or `my_bigint` with the domain `int_range` from
    -9007199254740993 to 9007199254740993, so a wider one, such as the
    whole 64-bit range, is refused;
  - the SELECT reads every field of the left input and then of the right,
    in order, under any names;
  - with `o` the preserved side (the left input of an INNER JOIN) and `i`
    the other, the whole `on` is one of `same_value(o.v, i.v)`,
    `same_value(i.v, o.v)`, `same_value(o.v, i.v) and o.k == i.k`,
    `o.k == i.k and same_value(o.v, i.v)`,
    `same_value(o.v, i.v) and same_value(o.w, i.w)`,
    `not same_value(o.v, i.v)` and `same_value(o.v, i.v) or o.k == i.k`.

```pietto
shape Row:
    id: Int
    v: Text | None

source lhs: Row = postgres.table("lhs")

source rhs: Row = postgres.table("rhs")

query result:
    from lhs
    left join rhs on same_value(lhs.v, rhs.v)
    select:
        l_id = lhs.id
        l_v = lhs.v
        r_id = rhs.id
        r_v = rhs.v
```

- The statement is the one the same program emits with `==`, each
  `same_value` written `(x IS NOT DISTINCT FROM y)` on PostgreSQL and
  `(x <=> y)` on MySQL; compiled replay and the live template carry the
  same SQL. The laws of `same_value` hold as written: two `None` keys
  match, pairs keep bag multiplicity, and LEFT and RIGHT pad only a row
  with no pair. An INNER JOIN does not make the operands of `same_value`
  non-null, as it does those of `==`, so their columns stay nullable.
  PostgreSQL cannot hash or merge `IS NOT DISTINCT FROM`: an `on` with no
  `==` joined to it by `and` (an `==` under `or` does not count) runs as a
  nested loop. Pietto promises no plan.
- After a LEFT JOIN on `same_value`, `r.v is None` does not tell an
  unmatched row: a left row whose `v` is `None` pairs with every right row
  whose `v` is `None`. Test a non-null field of the right side instead.
- R2 `save_recoverable` and `recover` refuse a MySQL query of these forms
  with PIE-R1004 (`detail` `PUBLIC_R2_UNQUALIFIED_FORM`) before any
  workspace access or connection, since no native qualification has run
  its refined statement. On PostgreSQL they prepare such a query as any
  other, and its R2 attempt fails closed at its first page, since R2 does
  not read the null-safe comparison of its statement (see the
  [R2 boundary](execution.md#known-limitations)).
- Native evidence: the raw campaign of 2026-11-13 ran each statement in the
  form Pietto emits, on six fixtures (with and without `None` keys, one side
  empty, rows inserted in reverse) and, for the first and third forms
  above, on physical NOT NULL columns and plain and unique indexes of the
  other side, under the default, forced hash and forced nested-loop JOIN
  methods on MySQL, and on PostgreSQL under the default method, with the
  nested-loop and merge methods forced as well for the third and fourth
  forms. Its six runs (`s06ns-{inner,left,right}-{postgres,mysql}`) are
  QUALIFIED: 3,990 MySQL and 2,184 PostgreSQL probes, every cell
  MATCHED on both databases, 126 cells ready on both and the 21 `Float`
  cells on PostgreSQL, whose MySQL rows are evidence only (D77.52 O7).
- Its candidate emission experiment of 2026-11-13 ran the SQL this change
  emits for every cell, unchanged, on both databases under the default
  method. Its six runs are QUALIFIED: 1,260 PostgreSQL and 1,080 MySQL
  probes, every cell MATCHED, the 126 cells on both databases and the
  21 `Float` cells on PostgreSQL. The runs bound this change as first
  committed on the head of the first `0.1.12` batch (tree `5bfe4d3e`).
  D77.50 carries them to the commit that integrates this change: the
  emission of the experiment's 2,340 probes and the pairing of its 273
  cells with the `==` statement are byte-identical there (sha256 of each
  map as compact sorted-key JSON, first 16 digits, the same on both
  sides: emission `c88bef0dfad8c8fe`, pairing `6b43453511a348e3`).
- Kept refused, with the `0.1.11` blockers in full (PIE-B1003
  `match_condition_not_in_row_domain` beside
  `scalar_projection_requires_later_slice` for each SELECT item and
  `join_shape_not_admitted_in_slice7`): every other `same_value` in an
  `on`. That includes a FULL JOIN, `any(...)` before a later JOIN, a
  literal, computed or same-side operand, `same_value(lhs.id, rhs.id)` over
  fields declared non-null, a `Bool`, an `Int` (INTEGER), a `Text` of
  another width, two sides of different widths or `Decimal` parameters, a
  MySQL `Float`, a source with another field (selected or not) or a
  declared key, a SELECT of some fields only, in another order or with a
  field twice, a relation alias `let` (`let r = rhs` and then
  `left join r on ...`), a WHERE after the JOIN (`where r.id is None`
  too), ORDER BY, a second JOIN before or after it, a header parameter and
  a `def` call. `==` in an `on` admits literal and computed operands, but
  `same_value` there admits one field of each side only. A statement of
  the emitted forms that emission refuses for another reason, such as an
  output label past 256 characters, a column name too long for the target
  or a resource limit, reports the whole list `0.1.11` reports for it
  (rule two, D77.37), which names that reason only where `0.1.11` does:
  the label and the column name, not the resource limit. So a MySQL
  `Float` pair is
  `comparison_type_pair_not_admitted` in a select item or WHERE and this
  list in an `on`.

Changed diagnostics (programs refused in `0.1.11`; no accepted program
changes; projects, no message text changed):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | `left join rhs on same_value(lhs.v, rhs.v)` (also INNER, RIGHT and the other six forms above) over the sources and SELECT above | `match_condition_not_in_row_domain` at the `on`, beside `scalar_projection_requires_later_slice` for each SELECT item and `join_shape_not_admitted_in_slice7` | none: the statement emits |

### Float GROUP BY keys in MySQL projects

- `emit-sql --project --dialect mysql` now emits a `Float` GROUP BY key in
  the forms the Phase77 S07 native qualification judged ready on MySQL
  8.4.12, and nothing else: a query over one source read directly that
  groups by the keys and selects exactly those keys in that order and then
  `count()` (`group by: price` / `select: price, n = count()`).

  The keys are different fields, as `x`, `x, y` or `x, k, y`, where `x` and
  `y` are `Float` fields both non-null or both nullable and `k` is a NOT NULL
  binary-collation `Text` field of width 64. The statement holds no other
  select item, aggregate, clause, JOIN, upstream query or header parameter,
  declares no `let` (a relation alias such as `let s = items` included, read
  or not) and no named window, and calls no `def`. Fields the statement does
  not read and the source's unique keys do not matter, and a table or query
  declaration and any output or field names give the same statement. The
  statement is the PostgreSQL one in MySQL spelling, and compiled replay and
  the live template carry the same SQL.
- The forms keep the existing [Float values](language.md#float-values)
  contract (`-0.0 == 0.0`, each group one member's value). PostgreSQL
  output is unchanged.
- The candidate emission experiment passed on 2026-11-13: one run per
  database, PostgreSQL 18.6 (`postgres-20261113T170618Z-f4eb8fe512b2c208`)
  and MySQL 8.4.12 (`mysql-20261113T170618Z-e0b38b159641d81d`), each
  judged its 8 forms MATCHED with no reason against, and the pair judgment
  found the 8 forms and 6 cells `CANDIDATE_EMISSION_QUALIFIED` with no
  reason against. The runs bound this change as first committed on the S06
  change (tree `3e8a3a92`). D77.50 carries them to the commit that
  integrates this change: the experiment's projects, emitted SQL, refusal
  controls and both runs' compile records are byte-identical there (sha256,
  first 16 digits, the same on both sides: `sql.json` `7861de97a43d65cd`,
  `controls.json` `3efcb9977df291ac`, the PostgreSQL compile record
  `ebb510d9d3a33587` and the MySQL one `bb7e9f753fccd6b3`).
- R2 `save_recoverable`, and `recover` when its restated values and
  parameters bind, refuse a query in these forms with PIE-R1004
  `REFINEMENT_COMPARISON_DOMAIN` while they prepare it, before any
  workspace access or connection. A `recover` whose restated values or
  parameters cannot bind prepares none and refuses such a query with
  PIE-R1004 (`detail` `PUBLIC_R2_UNQUALIFIED_FORM`), since no native
  qualification has run its refined statement (see the
  [R2 boundary](execution.md#known-limitations)).
- Kept refused on MySQL as in `0.1.11`, with PIE-B1003
  `group_key_type_outside_reviewed_comparison_domain`: a `Text` key of width
  1000 (the MySQL 8.4.12 deduplication kept `-0.0` and `0.0` apart beside
  it), 255 or 32, or a nullable one; a non-null and a nullable `Float`
  together, the `Text` key first or last, four keys, an `Int` key; another
  aggregate, a `count` with an argument, a key not selected or selected in
  another order, `count()` before the keys; a WHERE, ORDER BY or LIMIT, a
  JOIN, an upstream query, a header parameter, a `let`, a relation alias, a
  named window or a `def` call; and a window `percent_rank` or `cume_dist`
  result as a key. A MySQL `Float` DISTINCT
  (`distinct_field_comparison_domain_unsupported`) and UNION DISTINCT
  (`set_row_equivalence_domain_unsupported`), whose native qualification
  witnessed no on-disk deduplication, `Float` INTERSECT and EXCEPT, a
  `count_distinct` of a `Float`
  (`count_distinct_argument_outside_reviewed_int_domain`) and a `Float`
  window key stay refused as well. A refused statement, one of the forms
  above refused for another reason (an unreviewed target release, say)
  included, reports the blockers `0.1.11` reports.

Changed diagnostics (programs refused in `0.1.11`; no accepted program
changes; MySQL projects, no message text changed):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | `group by` one to three keys of the forms above, selected in order and then `count()` | `group_key_type_outside_reviewed_comparison_domain` at the GROUP BY item | none: the statement emits |
| PIE-R1004 | R2 `save_recoverable` of such a query, or its `recover` with restated values and parameters that bind | not reachable: the query did not compile | `REFINEMENT_COMPARISON_DOMAIN` |

### `count`, `min` and `max` over a window in eleven MySQL project forms

A MySQL project now emits `count()`, `count(x)` of an `Int`, `Timestamp`,
`Date` or `UUID` field and `min(x)` and `max(x)` of an `Int`, `Timestamp` or
`Date` field over a window in a statement that is, byte for byte, one of the
eleven forms that the Phase77 qualification pack pairs across PostgreSQL
18.6 and MySQL 8.4.12, with only its names changed. One of them is:

```pietto
shape Row:
    id: Int
    g: Int | None
    tier: Int
    ts: Timestamp
    ts2: Timestamp | None
    d: Date
    d2: Date | None
    u: UUID

source rows: Row = mysql.table("app.rows")

table result:
    from rows
    select:
        id
        n = count() window(order by tier)
        n_u = count(u) window(order by tier)
        n_d2 = count(d2) window(order by tier)
        low_id = min(id) window(order by tier)
        high_ts = max(ts) window(order by tier)
        high_d2 = max(d2) window(order by tier)
```

- Three other forms read the same shape and source in a `table`:
  `count_timestamp = count(ts)`, `count_date = count(d)`, `count_uuid =
  count(u)`, `low_timestamp = min(ts)` and `high_date = max(d)`, each
  `window(order by id)`; `id` then `count_ts2 = count(ts2)`, `count_d2 =
  count(d2)`, `high_timestamp = max(ts)`, `low_date = min(d)`, `low_ts2 =
  min(ts2)` and `high_d2 = max(d2)`, each `window(order by id)`; and `id`
  then `n_ts = count(ts)` and `high_ts = max(ts)` over `window(partition by
  g order by id rows between 1 preceding and current row)`, `high_d2 =
  max(d2)`, `low_d = min(d)` and `n_u = count(u)` over `window(partition by
  g)`.
- Seven read `shape Row` with `id: Int`, `flag: Bool | None`, `text: Text`,
  `money: Decimal(9, 2)` and `ratio: Float` from `source rows`. Six are
  `table` forms: `id` and `w = count()` over `window(order by id)`; `id` and
  `w = min(id)` over `window(order by id rows between 1 preceding and
  current row)` or over `window(partition by flag order by id)`; `let recent
  = window(partition by flag order by id)` and `n = count() window recent`;
  `group by: flag` then `flag`, `low = min(id)`, `high = max(low)` and `n =
  count()`, both over `window(order by low)`; and `id` with `qualify:
  count(id) window(order by id) > 1`. The seventh is a `query` that writes
  `let other = rows` and `inner join other on rows.id == other.id`, then
  selects `id = rows.id` and `high = max(other.id) window(partition by
  rows.flag order by rows.id)`. Each window and each item is written on the
  lines and in the order that the pack writes it; `pietto fmt` keeps them.
- The SQL is the plain aggregate with `OVER`, `COUNT(*) OVER` for
  `count()`, and the omitted frame reads `RANGE BETWEEN UNBOUNDED PRECEDING
  AND CURRENT ROW`, as on PostgreSQL. A count is a non-null `BIGINT`
  (`my_bigint`); an extreme is nullable and keeps its argument's carrier,
  `my_bigint`, `my_datetime` with 6 fractional digits or `my_date`.
  Compiled bundles and live templates replay the same SQL. PostgreSQL SQL is
  unchanged.
- The rest must match too, as for the `Text` defaults of `lag` and `lead`.
  The project has that one module, which holds only those declarations
  (empty lines aside), and the literal policy is `preserve`. The emission
  contract is the pack's: target `mysql` `8.4.12`; the statement premises
  `client_encoding` `utf8mb4`, `operator_environment` `builtin_only` and
  `identifier_case` `lower_case_table_names=0`, in that order; one source
  entry with the pack's field representations (`my_bigint`, `my_bool01`,
  `my_varchar` of length 64 in `utf8mb4_0900_bin`, `my_decimal(9, 2)`,
  `my_double`, `my_datetime` with 6 fractional digits, `my_date` and
  `my_uuid_bytes` with `standard_bytes`) and the premises
  `row_domain_matches` and `read_only_object`. A name follows the same rules
  as there. It is also none of the words `shape`, `source`, `query`,
  `table`, `from`, `select`, `window`, `order`, `by`, `lag`, `lead`,
  `mysql`, `Int`, `Bool`, `Text`, `Decimal`, `Float` and `None`, which are
  no names in the `lag` and `lead` forms either, and none of `count`,
  `min`, `max`, `partition`, `between`, `preceding`, `and`, `current`,
  `row`, `let`, `group`, `qualify`, `inner`, `join`, `on`, `Timestamp`,
  `Date` and `UUID`, which those forms still take as names. Each word is
  meant in exactly this case, so `Count` is a name. The `rows` of a frame is
  such a word too, the source `rows` a name.
- Every other MySQL project aggregate window keeps PIE-B1003
  `window_aggregate_approved_non_support_on_mysql` with its whole `0.1.11`
  output: `sum` and `avg`, another function, argument, frame, ORDER BY or
  PARTITION BY key, `desc`, the omitted frame written out, another JOIN, a
  `Timestamp`, `Date` or `UUID` argument in a named, QUALIFY, grouped or
  JOIN window, and a paired statement whose emission does not give its
  form's SQL, names aside. So the detail change that D77.11 planned for a
  `count` of a `Text`, `Bool`, `Float` or `Decimal` and a `min` or `max` of
  a `Float` or `Decimal` is not made. `load_bundle` keeps its `0.1.11`
  refusal, PIE-R1008, of every other bundle with a MySQL aggregate window,
  also of one whose records are a form's but whose SQL is not or that
  another check refuses, each with its `0.1.11` detail. R2
  `save_recoverable` and `recover` refuse a paired query with PIE-R1004
  `PUBLIC_R2_PAIRED_FORM`, before any workspace work.
- The native qualification passed on 2026-11-13: in one run of each half of
  the pack, PostgreSQL 18.6 and MySQL 8.4.12, the eleven forms matched the
  expected rows on both databases, and the MySQL half's three refusal
  controls, a `sum` and an `avg` over a window and a `count` over a window
  of a computed `let`, kept their `0.1.11` refusal. The PostgreSQL run
  `20261113T194605Z-ceea90a7ee8b576d598342bb` (verdict `pass` true, no
  reason) and the MySQL run `wave-a-mysql-20261113T194605Z` (acceptance
  `pass` true, no reason) bound this change as first committed on the `lag`
  and `lead` `Text` defaults on the head of the first `0.1.12` batch (tree
  `f0029580`), and their pairing summaries pair the eleven forms. D77.50
  carries them to the commit that integrates this change: the records both
  halves' compile steps export, the 83 forms of the PostgreSQL pack and the
  MySQL forms and controls, are identical there apart from the harness's
  install identity and the MySQL record's clock (the sha256 of each record
  as sorted-key JSON without its `identity` field and, for MySQL, its
  `started` and `finished` times, first 16 digits, the same on both sides:
  `b523f386dfc68ddd` and `78cb7016d87578cc`).

Changed diagnostics (programs refused in `0.1.11`; no accepted program
changes):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | MySQL project, one of the eleven forms above with only its names changed | `window_aggregate_approved_non_support_on_mysql` | none: the statement emits |
| PIE-R1004 | R2 `save_recoverable` or `recover` of such a query | not reachable: the query did not compile | `PUBLIC_R2_PAIRED_FORM` |

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
  exports and binds on MySQL, and `execute()`, `save()`, R2
  `save_recoverable`, and `recover` when its restated values and
  parameters bind, still refuse it with PIE-R1004 (`detail`
  `MEANING_OUTPUT`); a `recover` whose restated values or parameters
  cannot bind refuses it with PIE-R1004 (`detail`
  `PUBLIC_R2_UNQUALIFIED_FORM`; see the
  [R2 boundary](execution.md#known-limitations)).
- R2 `save_recoverable` and `recover` refuse any other query of these forms
  with PIE-R1004 (`detail` `PUBLIC_R2_UNQUALIFIED_FORM`) before any
  workspace access or connection, since no native qualification has run its
  refined statement (see the
  [R2 boundary](execution.md#known-limitations)).

Changed diagnostics (programs refused in `0.1.11`; no accepted program
changes):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | MySQL project, a `Decimal(p, s)`, `Date` or `Timestamp` header parameter read only in the positions above, in a query that declares no `UUID` parameter | `query_parameter_type_not_admitted_on_target` at each such declaration | none: the query emits |

Every refused query reports the list it reports without this note, object
for object.

### Conditional counts and tests of a group in three MySQL project forms

A MySQL project now emits the conditional count of a group,
`sum(1 for o in group if TEST)`, and the tests of a group,
`any(TEST for o in group)` and `all(TEST for o in group)`, in a statement
that is, byte for byte, one of the three forms that the Phase77
qualification pack pairs across PostgreSQL 18.6 and MySQL 8.4.12, with only
its names changed. One of them is:

```pietto
shape Agg:
    key: Int | None
    value: Int | None
    flag: Bool | None
    label: Text
    amount: Decimal(9, 2)
    ratio: Float
    rid: Int
    agg_row = unique(rid)

source agg: Agg = mysql.table("app.agg")

query result:
    from agg
    group by:
        key
    select:
        n = sum(1 for o in group if o.flag)
        a = all(o.flag for o in group)
        b = any(o.label == "a" for o in group)
```

- The other two forms hold the same shape and source; their query also
  selects `k = key` first, or has no `group by`. The pack runs the grouped
  and the ungrouped form over rows and over an empty table.
- The count is `COUNT(CASE WHEN TEST THEN 1 END)`, a non-null `BIGINT`
  (`my_bigint`, from 0 to 9223372036854775807); the tests are
  `(COUNT(CASE WHEN TEST THEN 1 END) > 0)` and
  `(COUNT(CASE WHEN TEST THEN NULL ELSE 1 END) = 0)`, each a non-null
  `my_signed_bool`, as on PostgreSQL. `"a"` is
  `CAST(X'61' AS CHAR CHARACTER SET utf8mb4) COLLATE utf8mb4_0900_bin`.
  Compiled bundles and live templates replay the same SQL. PostgreSQL SQL is
  unchanged.
- The rest must match too. The project has that one module, which holds
  only those three declarations (empty lines aside), and the literal policy
  is `preserve`. The emission contract is the pack's: target `mysql`
  `8.4.12`; the statement premises `client_encoding` `utf8mb4`,
  `operator_environment` `builtin_only` and `identifier_case`
  `lower_case_table_names=0`, in that order; one source entry with the
  pack's field representations (`my_bigint`, `my_bigint`, `my_bool01`,
  `my_varchar` of length 64 in `utf8mb4_0900_bin`, `my_decimal(9, 2)`,
  `my_double`, `my_bigint`) and the premises `row_domain_matches` and
  `read_only_object`. A name (of the module file, the shape, a field, the
  unique key, the source, the query, a label, the generator's member, the
  physical namespace, table or a column) is an ASCII identifier of at most
  63 bytes that does not start with `__pietto` in any case; the
  `mysql.table` locator is two such names joined by a dot. Two names that
  are both columns, or both Pietto names, are equal ignoring case exactly
  where the form's are: the shape and the source, `Agg` and `agg` above,
  stay so, and no other two are. A word the forms use as a keyword, such as
  `sum`, `any` or `group`, is no name there, and a name the SQL quotes may
  not be one the SQL also generates, such as `p0`, `s0`, `t1` or `c0`.
- Every other MySQL project conditional count or test of a group keeps
  PIE-B1003 `conditional_count_not_admitted_on_target` or
  `group_test_not_admitted_on_target`, with its whole `0.1.11` output, and
  so does a paired statement whose emission does not give its form's SQL,
  names aside. `load_bundle` keeps its `0.1.11` refusal, PIE-R1004
  `COMPILED_AGGREGATE_ARGUMENT`, of every other bundle with a MySQL
  conditional count or test of a group, also of one whose records are a
  form's but whose SQL is not. R2 `save_recoverable` and `recover` refuse a
  paired query with PIE-R1004 `PUBLIC_R2_PAIRED_FORM`, as for the `Text`
  defaults of `lag` and `lead`.
- The native qualification passed on 2026-11-13: in one run of each half of
  the pack, PostgreSQL 18.6 and MySQL 8.4.12, the three forms over rows and
  the two over an empty table matched the expected rows on both databases,
  and the MySQL half's refusal control, a conditional sum, kept its `0.1.11`
  refusal. The PostgreSQL run `20261113T172552Z-3974c1056495735a24c2ba22`
  (verdict `pass` true, no reason) and the MySQL run
  `wave-a-mysql-20261113T172552Z` (acceptance `pass` true, no reason) bound
  this change as first committed on the `lag` and `lead` `Text` defaults on
  the `0.1.11` release commit (tree `38976207`), and their pairing summaries
  pair the five forms. D77.50 carries them to the commit that integrates
  this change: the records both halves' compile steps export, the 83 forms
  of the PostgreSQL pack and the MySQL forms and control, are identical
  there apart from the harness's install identity and the MySQL record's
  clock (the sha256 of each record as sorted-key JSON without its
  `identity` field and, for MySQL, its `started` and `finished` times,
  first 16 digits, the same on both sides: `b523f386dfc68ddd` and
  `2bef424d5b336d83`).

Changed diagnostics (programs refused in `0.1.11`; no accepted program
changes):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | MySQL project, one of the three forms above with only its names changed | `conditional_count_not_admitted_on_target`, then `group_test_not_admitted_on_target` twice | none: the query emits |
| PIE-R1004 | R2 `save_recoverable` or `recover` of such a query | not reachable: the query did not compile | `PUBLIC_R2_PAIRED_FORM` |

### Distinct counts of several columns in eleven MySQL project forms

A MySQL project now emits `count_distinct(a, b, ...)` of two or more fields
as MySQL's own `COUNT(DISTINCT a, b)` in a statement that is, byte for byte,
one of the eleven forms that the Phase77 qualification pack pairs across
PostgreSQL 18.6 and MySQL 8.4.12, with only its names changed. One of them
is:

```pietto
shape Agg:
    key: Int | None
    value: Int | None
    flag: Bool | None
    label: Text
    amount: Decimal(9, 2)
    ratio: Float
    rid: Int
    agg_row = unique(rid)

source agg: Agg = mysql.table("app.agg")

source keys: Agg = mysql.table("app.keys")

query result:
    from keys
    let r = agg
    left join r on keys.rid == r.rid
    let lb = r.label
    group by:
        keys.rid
    select:
        k = keys.rid
        d = count_distinct(keys.label, r.rid, r.label)
```

- Seven other forms hold the same shape and sources and read the same
  JOIN with the same `let` lines: the query above with `inner join`, and
  each of the two with `d = count_distinct(keys.label, lb, r.rid)`; grouped
  by `keys.key`, selecting `k = keys.key` and
  `d = count_distinct(keys.label, lb)`, with `left join` or `inner join`,
  and with `left join` and then `e = count_distinct(r.key, keys.label)`;
  and `table result` with no `group by`, selecting only
  `d = count_distinct(lb, keys.key)`.
- Three forms have only the shape and `source agg`: `table result` from
  `agg` selecting `text_flag = count_distinct(label, flag)`,
  `int_text = count_distinct(key, label)` and
  `all_three = count_distinct(key, flag, label)`; `table result` selecting
  only `int_int = count_distinct(key, value)`; and `query result` grouped by
  `key`, selecting `k = key` and `n = count_distinct(label, flag)`. The pack
  runs the first of them over rows and over an empty table.
- Each count is `COUNT(DISTINCT a, b)` with its fields in the written order,
  which skips a row in which any field is NULL and compares a `Text` field
  by its bytes, with NO PAD (`utf8mb4_0900_bin`). It is a non-null `BIGINT`
  (`my_bigint`, from 0 to 9223372036854775807) with no R13 evidence. Its
  project JSON column keeps the provenance `function` `count_distinct_tuple`
  and has the `syntax` roles `aggregate_distinct` and `aggregate_separator`
  between the fields, without PostgreSQL's tuple roles. Compiled bundles and
  live templates replay the same SQL. PostgreSQL SQL is unchanged.
- The rest must match too. The project has that one module, which holds
  only the shape, the source or sources and that one definition (empty lines
  aside), and the literal policy is `preserve`. The emission contract is the
  pack's: target `mysql` `8.4.12`; the statement premises
  `client_encoding` `utf8mb4`, `operator_environment` `builtin_only` and
  `identifier_case` `lower_case_table_names=0`, in that order; one source
  entry per source, in the module's order, with the pack's field
  representations (`my_bigint`, `my_bigint`, `my_bool01`, `my_varchar` of
  length 64 in `utf8mb4_0900_bin`, `my_decimal(9, 2)`, `my_double`,
  `my_bigint`) and the premises `row_domain_matches` and `read_only_object`.
  A name (of the module file, the shape, a field, the unique key, a source,
  the definition, a `let`, a label, the physical namespace, a table or a
  column) is an ASCII identifier of at most 63 bytes that does not start
  with `__pietto` in any case; a `mysql.table` locator is two such names
  joined by a dot. Two names that are both columns, both tables, both
  namespaces, both locators or both Pietto names are equal exactly where
  the form's are, and equal ignoring case exactly where the form's are: the
  two tables of a JOIN form are in one namespace and have the same columns,
  the shape and the source `agg` stay equal ignoring case, and no other two
  names are. A word the forms use as a keyword, such as `count_distinct`,
  `left` or `join`, is no name there, and a name the SQL quotes may not be
  one the SQL also generates, such as `p0`, `m0`, `s0`, `t1` or `c0`.
- Every other MySQL project `count_distinct` of several fields keeps
  PIE-B1003 `count_distinct_tuple_not_admitted_on_target`, with its whole
  `0.1.11` output, and so does a paired statement whose emission does not
  give its form's SQL, names aside. `load_bundle` keeps its `0.1.11`
  refusal, PIE-R1004 `COMPILED_AGGREGATE_ARGUMENT`, of every other bundle
  with a MySQL `count_distinct` of several fields, also of one whose records
  are a form's but whose SQL is not. R2 `save_recoverable` and `recover`
  refuse a paired query with PIE-R1004 `PUBLIC_R2_PAIRED_FORM`, as for the
  other paired forms.
- The native qualification passed on 2026-11-13: in one run of each half of
  the pack, PostgreSQL 18.6 and MySQL 8.4.12, the eleven forms matched the
  expected rows on both databases, the first `agg` form also over an empty
  table, and the MySQL half's four refusal controls, a `Decimal` and `Float`
  pair and a field written twice, bare, through a `let` name or qualified,
  kept their `0.1.11` refusal. The PostgreSQL run
  `20261113T184428Z-39f2d1b0857c0cf1a46c3b37` (verdict `pass` true, no
  reason) and the MySQL run `wave-a-mysql-20261113T184428Z` (acceptance
  `pass` true, no reason) bound this change as first committed on the
  conditional counts and the `lag` and `lead` `Text` defaults on the
  `0.1.11` release commit (tree `4e1aca88`), and their pairing summaries
  pair the twelve form runs. D77.50 carries them to the commit that
  integrates this change: the records both halves' compile steps export,
  the 83 forms of the PostgreSQL pack and the MySQL forms and controls, are
  identical there apart from the harness's install identity and the MySQL
  record's clock (the sha256 of each record as sorted-key JSON without its
  `identity` field and, for MySQL, its `started` and `finished` times,
  first 16 digits, the same on both sides: `b523f386dfc68ddd` and
  `c98f507fe3baa050`).

Changed diagnostics (programs refused in `0.1.11`; no accepted program
changes):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | MySQL project, one of the eleven forms above with only its names changed | `count_distinct_tuple_not_admitted_on_target`, once for each `count_distinct` | none: the definition emits |
| PIE-R1004 | R2 `save_recoverable` or `recover` of such a query | not reachable: the query did not compile | `PUBLIC_R2_PAIRED_FORM` |

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
  `now()`, before any workspace access or connection. They refuse a query
  with `lpad` and no `now()` with PIE-R1004 `PUBLIC_R2_UNQUALIFIED_FORM`
  before any workspace access or connection, since no native qualification
  has run its refined statement (see the
  [R2 boundary](execution.md#known-limitations)).
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

### MySQL project `first` and `last`

- A MySQL project now emits `first(x, order by k, id)` and `last(...)` only in
  the forms that [Aggregates](language.md#aggregates-and-grouping) lists: a
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
  statement (see the [R2 boundary](execution.md#known-limitations)).
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

### Conditionals beside a JOIN and calls in aggregate arguments in four MySQL project forms

A MySQL project now emits a statement with a JOIN whose other query has a
conditional (a `def` that inlines to one) in its WHERE, or whose aggregate
argument over the JOIN's rows holds a scalar call, in a statement that is,
byte for byte, one of the four forms that the Phase77 qualification pack
pairs across PostgreSQL 18.6 and MySQL 8.4.12, with only its names changed.
One of them is:

```pietto
shape Row:
    id: Int
    key: Int | None
    label: Text | None
    row_key = unique(id)

source lhs: Row = mysql.table("app.lhs")

source rhs: Row = mysql.table("app.rhs")

def band(x: Int) -> Int: return 1 if x <= 3 else 2

query pred:
    from rhs
    where band(id) == 2
    select:
        id
        label

query result:
    from lhs
    let r = pred
    left join r on lhs.id == r.id
    select:
        a = lhs.id
        b = r.label
```

- The other three forms hold the same shape, sources and `def`. One has the
  same `pred` and a `query result` from `pred` with `let l = lhs`,
  `inner join l on l.id == pred.id`, selecting `a = pred.id` and
  `b = l.label`. One has no `pred`: its `query result` reads `from lhs`,
  `let r = rhs`, `left join r on lhs.id == r.id` and `group by lhs.id`, and
  selects `a = lhs.id`, `n = count(lower(r.label))`,
  `d = count_distinct(trim(r.label))`, `l = count(len(r.label))` and
  `c = count(lower(trim(r.label)))`. The last has the same `pred`, the LEFT
  JOIN of `r = pred` with that `group by`, and selects `a = lhs.id` and
  `n = count(lower(r.label))`.
- `pred`'s WHERE is written as it is without the JOIN, as
  `WHERE ((CASE WHEN (... <= CAST(3 AS SIGNED)) THEN CAST(1 AS SIGNED) ELSE
  CAST(2 AS SIGNED) END) = CAST(2 AS SIGNED))`, and each call inside its
  aggregate, as `COUNT(LOWER(...))`, `COUNT(DISTINCT TRIM(...))`,
  `COUNT(CAST(CHAR_LENGTH(...) AS SIGNED))` and `COUNT(LOWER(TRIM(...)))`.
  Each count is a non-null `my_bigint`, `a` the key's `my_bigint` and `b`
  the label's nullable `my_varchar`. Compiled bundles and live templates
  replay the same SQL. PostgreSQL SQL is unchanged.
- The rest must match too. The project has that one module, which holds
  only those declarations (empty lines aside). The literal policy is
  `preserve`, except for the last form, which the pack runs with
  `bind-safe`, its four `Int` literals as server parameters. The emission
  contract is the pack's: target `mysql` `8.4.12`; the statement premises
  `client_encoding` `utf8mb4`, `operator_environment` `builtin_only` and
  `identifier_case` `lower_case_table_names=0`, and for the last form then
  `parameter_protocol` `mysql_prepared`, in that order; one source entry
  per source, in the module's order, with the pack's field representations
  (`my_bigint`, `my_bigint`, `my_varchar` of length 64 in
  `utf8mb4_0900_bin`) and the premises `row_domain_matches` and
  `read_only_object`. A name (of the module file, the shape, a field, the
  unique key, a source, the `def` and its parameter, a definition, a `let`,
  a label, the physical namespace, a table or a column) is an ASCII
  identifier of at most 63 bytes that does not start with `__pietto` in any
  case; a `mysql.table` locator is two such names joined by a dot. Two names
  that are both columns, both tables, both namespaces, both locators or
  both Pietto names are equal, also ignoring case, exactly where the form's
  are: the two tables are in one namespace and have the same columns, and
  no other two names are. A word the forms use as a keyword, such as
  `where`, `count` or `lower`, is no name there, and a name the SQL quotes
  may not be one the SQL also generates, such as `p0`, `m0`, `s0`, `t1` or
  `c0`.
- Every other such MySQL statement keeps its whole `0.1.11` output, and so
  does a paired statement whose emission does not give its form's SQL,
  names aside. R2 `save_recoverable` and `recover` refuse a paired query
  with PIE-R1004 `PUBLIC_R2_PAIRED_FORM`, as for the other paired forms.
- `load_bundle` and compiled replay now read these positions themselves: a
  MySQL bundle whose statement has a JOIN and either a conditional in a
  definition with no JOIN of its own or a scalar call in an aggregate
  argument loads only when its records are one of the forms' and its SQL is
  that form's. `0.1.11` loaded such a bundle, which none of its emissions
  wrote.
- The native qualification passed on 2026-11-13: in one run of each half of
  the pack, PostgreSQL 18.6 and MySQL 8.4.12, the four forms matched the
  expected rows on both databases, the last with its four server
  parameters, and the MySQL half's refusal control, a `def` call in the
  JOIN's ON, kept its `0.1.11` refusal. The PostgreSQL run
  `20261113T201550Z-b1113cacc0fbfe3dcac90c19` (verdict `pass` true, no
  reason) and the MySQL run `wave-a-mysql-20261113T201550Z` (acceptance
  `pass` true, no reason) bound this change as first committed on the
  distinct-tuple counts, the conditional counts and the `lag` and `lead`
  `Text` defaults on the `0.1.11` release commit (tree `4db49248`), and
  their pairing summaries pair the four forms. D77.50 carries them to the
  commit that integrates this change: the records both halves' compile
  steps export, the 83 forms of the PostgreSQL pack and the MySQL forms and
  control, are identical there apart from the harness's install identity
  and the MySQL record's clock (the sha256 of each record as sorted-key
  JSON without its `identity` field and, for MySQL, its `started` and
  `finished` times, first 16 digits, the same on both sides:
  `b523f386dfc68ddd` and `5a2d04329d58c687`).

Changed diagnostics (programs refused in `0.1.11`; no accepted program
changes):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | MySQL project, one of the first two forms above with only its names changed | `scalar_projection_requires_later_slice` twice, then `join_shape_not_admitted_in_slice7` | none: the definition emits |
| PIE-B1003 | MySQL project, one of the last two forms above with only its names changed | `operator_not_implemented_in_slice6`, then `join_shape_not_admitted_in_slice7` | none: the definition emits |
| PIE-R1004 | R2 `save_recoverable` or `recover` of such a query | not reachable: the query did not compile | `PUBLIC_R2_PAIRED_FORM` |
| PIE-R1004 | `load_bundle` of a MySQL bundle described above that is no form's and that `0.1.11` refused at a replay check that now runs after the reading of these positions (one that runs before it keeps its detail) | that check's detail | `COMPILED_OPERATOR` for the conditional, `COMPILED_AGGREGATE_ARGUMENT` for the call; with both, the first in the bundle's record order (`COMPILED_OPERATOR` in a bundle shaped like the last form) |

New refusals (bundles `0.1.11` loaded, which none of its emissions wrote):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-R1004 | `load_bundle` of a MySQL bundle described above that is no form's | loaded | `COMPILED_OPERATOR` for the conditional, `COMPILED_AGGREGATE_ARGUMENT` for the call; with both, the first in the bundle's record order (`COMPILED_OPERATOR` in a bundle shaped like the last form) |

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
- R2 `save_recoverable` and `recover` refuse a query of these forms with
  PIE-R1004 (`detail` `PUBLIC_R2_UNQUALIFIED_FORM`) before any workspace
  access or connection, since no native qualification has run its refined
  statement (see the [R2 boundary](execution.md#known-limitations)).
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
  `Int /` (PIE-B1003 `binary_operator_not_admitted`, D77.23) outside the
  R08 cell of [its subsection](#mysql-project-int--proved-by-its-literal).

A statement still refused reports exactly the blockers it has without this
note, object for object, a cell's own included: selecting `r = a % b`
beside `q = x / y` keeps PIE-B1003 `binary_operator_not_admitted` at `r` and
`float_division_not_realized` at `q`.

### `Text` literal defaults of `lag` and `lead` in three MySQL project forms

A MySQL project now emits a static `Text` literal default of `lag` or
`lead` in a statement that is, byte for byte, one of the three forms that
the Phase77 qualification pack pairs across PostgreSQL 18.6 and MySQL 8.4.12,
with only its names changed. One of them is:

```pietto
shape Row:
    id: Int
    flag: Bool | None
    text: Text | None
    money: Decimal(9, 2)
    ratio: Float

source rows: Row = mysql.table("app.rows")

query result:
    from rows
    select:
        id
        previous = lag(text, 1, "雪") window(order by id)
        following = lead(text, 1, "a'b") window(order by id)
```

- The other two forms hold the same shape and source; their query selects
  `id`, `previous_empty = lag(text, 1, "")`, `following_unicode =
  lead(text, 1, "雪")` and `following_null = lead(text, 1)`, or `id`,
  `plain = text`, `lag_empty = lag(text, 1, "")`, `lead_snow = lead(text,
  1, "雪")`, `lead_quote = lead(text, 1, "a'b")` and `lead_none =
  lead(text, 1)`, each window `window(order by id)`, in that order.
- The default is the hexadecimal literal of its UTF-8 bytes: `X''`,
  `X'e99baa'` and `X'612762'`. The result keeps the value's `Text` carrier,
  a nullable `VARCHAR(64)`, and compiled bundles and live templates replay
  the same SQL. PostgreSQL SQL is unchanged.
- The rest must match too. The project has that one module, which holds
  only those three declarations (empty lines aside), and the literal policy
  is `preserve`. The emission contract is the pack's: target `mysql`
  `8.4.12`; the statement premises `client_encoding` `utf8mb4`,
  `operator_environment` `builtin_only` and `identifier_case`
  `lower_case_table_names=0`, in that order; one source entry with the
  pack's field representations (`my_bigint`, `my_bool01`, `my_varchar` of
  length 64 in `utf8mb4_0900_bin`, `my_decimal(9, 2)`, `my_double`) and the
  premises `row_domain_matches` and `read_only_object`. A name (of the
  module file, the shape, a field, the source, the query, a label, the
  physical namespace, table or a column) is an ASCII identifier of at most
  63 bytes that does not start with `__pietto` in any case; the
  `mysql.table` locator is two such names joined by a dot. Two different
  names may not be equal ignoring case when both are columns or both are
  Pietto names, which are the shape, field, source, query and label names
  together. A name the SQL quotes (an output label, the physical
  namespace, the table or a column) may not be one the SQL also generates,
  such as `p0`, `s0`, `t1` or `c0`, since the SQL then differs from the
  form's. Compiled replay reads the bundle's own records the same way, and
  their SQL must also be the form's SQL, names aside.
- Every other MySQL project `Text` literal default keeps PIE-B1003
  `window_default_literal_kind_not_realized_yet`, with its whole `0.1.11`
  output, and so does a paired statement whose emission does not give its
  form's SQL, names aside. `load_bundle` keeps its `0.1.11` refusal,
  PIE-R1008, of every other bundle with a MySQL `Text` default, also of
  one whose records are a form's but whose SQL is not. R2
  `save_recoverable` and `recover` refuse a paired query with PIE-R1004
  `PUBLIC_R2_PAIRED_FORM`, before any workspace work: its refined
  statement is not one of the forms.
- The native qualification passed on 2026-11-13: in one run of each half of
  the pack, PostgreSQL 18.6 and MySQL 8.4.12, the three forms matched the
  expected rows on both databases, and the MySQL half's two refusal
  controls, a field and a parameter default, kept their `0.1.11` refusal.
  The MySQL run `wave-a-mysql-20261113T162813Z` ran in the MySQL half's
  third freeze; the second-freeze run, which compared the driver's undecoded
  `Text` bytes with text values, was not accepted. The PostgreSQL run
  `20261113T140358Z-de1e2ec4d68dc2628eaf363f` (verdict `pass` true, no
  reason) and that MySQL run (acceptance `pass` true, no reason) bound this
  change as first committed on the `0.1.11` release commit (tree
  `34d2ce5d`), and their pairing summaries pair the three forms. D77.50
  carries them to the commit that integrates this change: the records both
  halves' compile steps export, the 83 forms of the PostgreSQL pack and the
  MySQL forms and controls, are identical there apart from the harness's
  install identity and the MySQL record's clock (the sha256 of each record
  as sorted-key JSON without its `identity` field and, for MySQL, its
  `started` and `finished` times, first 16 digits, the same on both sides:
  `b523f386dfc68ddd` and `cd2b9c6a9ed33830`).

Changed diagnostics (programs refused in `0.1.11`; no accepted program
changes):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | MySQL project, one of the three forms above with only its names changed | `window_default_literal_kind_not_realized_yet` | none: the query emits |
| PIE-R1004 | R2 `save_recoverable` or `recover` of such a query | not reachable: the query did not compile | `PUBLIC_R2_PAIRED_FORM` |

### Decimal and Int arithmetic and signs in fourteen MySQL project forms

A MySQL project now emits a `Decimal` plus or minus an `Int` in either
order, a `Decimal` plus or minus a `Decimal` of another scale, a `Decimal`
times an `Int` in either order and a unary `+` or `-` of a `Decimal` in a
statement that is, byte for byte, one of the fourteen forms that the
Phase77 qualification pack pairs across PostgreSQL 18.6 and MySQL 8.4.12,
with only its names changed. One of them is:

```pietto
shape Row:
    id: Int
    flag: Bool | None
    text: Text
    money: Decimal(9, 2)
    ratio: Float

source rows: Row = mysql.table("app.rows")

table result:
    from rows
    select:
        added = money + id
        subtracted = money - id
```

- Nine other forms hold the same shape and source and a `table result`
  from `rows` that selects `added = id + money` and
  `subtracted = id - money`, or one item `result = money * id`,
  `result = id * money`, `result = money * 2`, `result = -money`,
  `result = +money` or `result = -(money * id)`; or the shape with
  `ratio: Decimal(8, 3)`, selecting `added = money + ratio` and
  `subtracted = money - ratio`; or the shape with `money: Decimal(46, 30)`,
  selecting `result = money * id`. As in the pack, such an item's label is
  the definition's own name. The last four forms hold the first shape and
  source and a `query result(factor: Int)` from `rows` that selects
  `total = money + factor`, `total = factor - money`,
  `total = money * factor` or `total = factor * money`; the pack runs each
  with the arguments 7, 9223372036854775807 and -9223372036854775808.
- MySQL writes each operation without a result cast, as `(a + b)`,
  `(a * CAST(2 AS SIGNED))` or `(-a)`, and the header parameter as the
  server parameter `CAST(? AS SIGNED)`. Each result takes the carrier a
  PostgreSQL project takes ([project guide](project-package.md#emission-rules)):
  `my_decimal(22, 2)` for a sum or difference with an `Int`,
  `my_decimal(28, 2)` for a product with an `Int`, `my_decimal(11, 3)` for
  the two scales and `my_decimal(65, 30)` for the wide product; a sign
  keeps its operand's carrier, `my_decimal(9, 2)` for a field and
  `my_decimal(28, 2)` for `-(money * id)`. MySQL itself declares the result
  column of each form with a `CAST(... AS SIGNED)` operand, the four with a
  header parameter and `money * 2`, one digit wider, as `DECIMAL(23, 2)` or
  `DECIMAL(29, 2)`; every value fits the stated carrier. A binary
  operation's column is `nullable` `unknown`, and a sign
  keeps its operand's. Compiled bundles and live templates replay the same
  SQL. PostgreSQL SQL is unchanged.
- The rest must match too. The project has that one module, which holds
  only the shape, the source and that one definition (empty lines aside),
  and the literal policy is `preserve`. The emission contract is the pack's:
  target `mysql` `8.4.12`; the statement premises `client_encoding`
  `utf8mb4`, `operator_environment` `builtin_only` and `identifier_case`
  `lower_case_table_names=0`, and for the four forms with a header
  parameter then `parameter_protocol` `mysql_prepared`, in that order; one
  source entry with the pack's field representations (`my_bigint`,
  `my_bool01`, `my_varchar` of length 64 in `utf8mb4_0900_bin`, the
  shape's `my_decimal` and `my_double` or `my_decimal(8, 3)`) and the
  premises `row_domain_matches` and `read_only_object`. A name (of the
  module file, the shape, a field, the source, the definition, the header
  parameter, a label, the physical namespace, the table or a column) is an
  ASCII identifier of at most 63 bytes that does not start with `__pietto`
  in any case; a `mysql.table` locator is two such names joined by a dot.
  Two names that are both columns, both tables, both namespaces, both
  locators or both Pietto names are equal, also ignoring case, exactly
  where the form's are. A word the forms use as a keyword, such as `table`,
  `select` or `Decimal`, is no name there, and a name the SQL quotes may
  not be one the SQL also generates, such as `s0`.
- Every other MySQL project statement with such an operation keeps its
  whole `0.1.11` output, and so does a paired statement whose emission does
  not give its form's SQL, names aside. `load_bundle` keeps its `0.1.11`
  refusal, PIE-R1004 `COMPILED_PHYSICAL_DOMAIN`, or `COMPILED_UNARY_DOMAIN`
  for a sign of a field, of every other bundle with such a MySQL operation,
  also of one whose records are a form's but whose SQL is not. R2
  `save_recoverable` and `recover` refuse a paired query with PIE-R1004
  `PUBLIC_R2_PAIRED_FORM`, as for the other paired forms.
- The native qualification passed on 2026-11-14. The PostgreSQL half of
  the pack ran once on 2026-11-13 and was accepted: run
  `20261113T214055Z-72eabeeffb3e386dc9825de4` (verdict `pass` true, no
  reason) bound this change as first committed on the S14, S11, S10 and
  S16 changes (tree `d455776d`). The MySQL half's first run, on the same
  tree, failed only on the native length of the four header-parameter
  forms' total column, which its package had derived from the public
  carrier, while MySQL 8.4.12 takes `CAST(? AS SIGNED)` into `Decimal`
  arithmetic as 20 integer digits; the SQL and every value matched. That
  run is kept and carries nothing. The MySQL half was frozen again as a
  changed experiment with MySQL's own lengths and ran once: run
  `wave-a-mysql-20261114T005229Z` (acceptance `pass` true, no reason)
  bound this change rebased onto the S14, S11 and S08 changes (tree
  `c059e5c4`), where D77.50 carried the PostgreSQL run, and the two runs
  pair all 22 pairs of the pack's S17 to S19 scope. D77.50 carries both to
  the commit that integrates this change: the records both halves' compile
  steps export, the 83 forms of the PostgreSQL pack and the 27 MySQL forms
  and controls, are identical there apart from the harness's install
  identity and the MySQL record's clock (the sha256 of each record as
  sorted-key JSON without its `identity` field and, for MySQL, its
  `started` and `finished` times, first 16 digits, the same on both sides:
  `b523f386dfc68ddd` and `1545fd52f5781fbf`).

Changed diagnostics (programs refused in `0.1.11`; no accepted program
changes):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1003 | MySQL project, one of the fourteen forms above with only its names changed | for each SELECT item, `arithmetic_requires_signed_int_operands` for a sum or difference with an `Int`, `decimal_scale_mismatch` for the two scales, `binary_operator_not_admitted` for a product, also under a sign, and `unary_sign_requires_int_operand` for a sign of a field | none: the definition emits |
| PIE-R1004 | R2 `save_recoverable` or `recover` of such a query | not reachable: the query did not compile | `PUBLIC_R2_PAIRED_FORM` |

### An asof JOIN beside a FULL JOIN in seven MySQL single files

Single-file `emit-sql --dialect mysql` now emits an asof JOIN in a relation
with a FULL JOIN, which MySQL emulates with UNION ALL, in a file that is,
byte for byte, one of seven forms of the Phase77 qualification pack, which
pairs PostgreSQL 18.6 with MySQL 8.4.12, with only its names changed. One of
them is:

```text
shape Order:
    id: Int
    product_id: Int
    region: Text
    ordered_at: Timestamp
    ordered_on: Date
    week_start: Timestamp
    score: Float
    amount: Int

shape Price:
    product_id: Int
    region: Text
    valid_from: Timestamp
    valid_to: Timestamp
    valid_on: Date
    amount_cents: Int
    score: Float
    price_key = unique(product_id, valid_from)

shape PriceOn:
    product_id: Int
    valid_on: Date
    valid_from: Timestamp
    amount_cents: Int
    on_key = unique(product_id, valid_on)

shape Price3:
    product_id: Int
    region: Text
    valid_from: Timestamp
    amount_cents: Int
    p3_key = unique(product_id, region, valid_from)

shape PriceId:
    id: Int
    product_id: Int
    valid_from: Timestamp
    id_key = unique(id)

shape PriceTwo:
    id: Int
    product_id: Int
    region: Text
    valid_from: Timestamp
    a_key = unique(id)
    b_key = unique(product_id, region, valid_from)

shape PriceNone:
    product_id: Int
    valid_from: Timestamp

shape Rate:
    valid_from: Timestamp
    amount_cents: Int
    rate_key = unique(valid_from)

shape PriceKeyed:
    id: Int
    product_id: Int
    valid_from: Timestamp
    price_key = unique(id)

relationship order_price(o: Order, p: Price):
    o.product_id == p.product_id

source orders: Order = mysql.table("shop.orders")
source prices: Price = mysql.table("shop.prices")
source prices_on: PriceOn = mysql.table("shop.prices_on")
source prices3: Price3 = mysql.table("shop.prices3")
source prices_id: PriceId = mysql.table("shop.prices_id")
source prices_two: PriceTwo = mysql.table("shop.prices_two")
source prices_none: PriceNone = mysql.table("shop.prices_none")
source rates: Rate = mysql.table("shop.rates")
source prices_keyed: PriceKeyed = mysql.table("shop.prices_keyed")

table price_table:
    from prices
    select product_id = prices.product_id, valid_from = prices.valid_from

query q:
    from orders
    let p2 = prices_id
    full join p2 on orders.id == p2.id
    let price = prices
    asof left join price on orders.product_id == price.product_id and orders.ordered_at >= price.valid_from
    let p3 = prices_id
    full join p3 on orders.id == p3.id
    select order_id = orders.id, c = price.amount_cents
```

- The other six files hold the same shapes, relationship, sources and
  table, and one query `q` that reads `from orders` and then has:
  - `let p2 = prices_id`, `full join p2 on orders.id == p2.id`,
    `let price = prices` and `asof left join price on orders.product_id ==
    price.product_id and orders.ordered_at >= price.valid_from`, or the
    same with `asof inner join`;
  - `let price = prices`, that asof left or inner join, `let p2 =
    prices_id` and `full join p2 on orders.id == p2.id`;
  - the FULL JOIN on `p2`, `let price = prices` and the asof inner join,
    then `select order_id = orders.id, full_id = p2.id, c =
    price.amount_cents`, or, with `let p3 = prices_id` and `full join p3 on
    orders.id == p3.id` after it, `select order_id = orders.id,
    first_full_id = p2.id, second_full_id = p3.id, c = price.amount_cents`.

  The other queries end with `select order_id = orders.id, c =
  price.amount_cents`.
- The SQL is the FULL JOIN emulation with the asof JOIN's `LATERAL` latest
  row: an asof JOIN after a FULL JOIN reads the `__pietto_full` derived-table
  ports, and an earlier one is written in each UNION ALL branch, whose
  right-only branch tests the row it reads for NULL. The branches choose the
  same latest row only while the source's declared unique holds. PostgreSQL
  SQL is unchanged.
- A name (of a shape, field, constraint, relationship or its parameter,
  source, table, query, binding or label, or a part of a `mysql.table`
  locator) is an ASCII identifier of at most 63 bytes that does not start
  with `__pietto` in any case. Two names are equal ignoring case exactly
  when the names they replace are, as `Price` and `price` are, and each
  locator is two names joined by a dot. Empty lines and the final newline do
  not count; a comment, a line of spaces, other spacing, a carriage return, a
  byte order mark, another clause or another definition does.
- Only single-file `emit-sql --dialect mysql`, with text or JSON output,
  pairs a file. Every other single file keeps PIE-B1000 with its whole
  `0.1.11` output, and so does a paired file whose emission does not give
  its form's SQL, names aside. A FULL JOIN whose `on` reads the asof JOIN's
  row, such as `full join p2 on price.product_id == p2.id` after it, stays
  refused.
- The native qualification passed on 2026-11-13: in one run of each half of
  the pack, PostgreSQL 18.6 and MySQL 8.4.12, the seven files and the asof
  JOIN alone, which `0.1.11` already emits, matched the expected rows on
  both databases, and the MySQL half's refusal control, that FULL JOIN whose
  `on` reads the asof row, kept its `0.1.11` refusal. The runs,
  PostgreSQL `20261113T141451Z-20218a248bc183f4b57d4402` (verdict `pass`
  true, no reason) and MySQL `wave-a-mysql-20261113T141451Z` (acceptance
  `pass` true, no reason), bound this change as first committed on the
  `0.1.11` release commit (tree `bc4c08f8`). D77.50 carries them to the
  commit that integrates this change: the documents both halves' compile
  steps export, the 83 forms of the PostgreSQL pack and the nine MySQL
  files, are byte-identical there (sha256, first 16 digits, the same on
  both sides: `b523f386dfc68ddd` and `93336282f3619e97`).

Changed diagnostics (programs refused in `0.1.11`; no accepted program
changes):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1000 | single file, `emit-sql --dialect mysql`, one of the seven files above with only its names changed | `MySQL SQL emission is not implemented for RelationIR: <name>. MySQL has no ASOF JOIN in a relation with a FULL JOIN yet; emit with --dialect postgres` | none: the file emits |

### Known limitations of 0.1.12

- **R2 on MySQL refuses the forms this release opens.** On MySQL,
  `save_recoverable` and `recover` refuse every query in a form that
  `0.1.11` refused, before any workspace access or connection: with
  PIE-R1004 `PUBLIC_R2_UNQUALIFIED_FORM`, or with an earlier R2 refusal of
  the query (`PUBLIC_R2_PAIRED_FORM` for a paired form,
  `PUBLIC_R2_STATEMENT_SNAPSHOT` for `now()`, `REFINEMENT_COMPARISON_DOMAIN`
  for `Float` GROUP BY keys, `MEANING_OUTPUT` for a `Timestamp` parameter
  selected as an output). No native qualification has run R2's refined
  statement of any of them. This R2 check does not apply to `execute()`,
  `save()` or bundles. On MySQL, R2 also refuses every query that reads
  `now()`; on PostgreSQL it refuses one whose SQL R2 does not read, and an
  R2 attempt of a null-safe `same_value` JOIN fails closed at its first
  page, with `terminal` `FAILED` and no public reason.
- **MySQL refusals.** MySQL support trails PostgreSQL: a form opens on MySQL
  only after a two-database run passes, and only in the shapes that run
  matched; outside them MySQL emission refuses it with a PIE-B code and
  writes no SQL. These forms are refused on MySQL in `0.1.12`; the
  [capability page](capabilities.md) and the subsections above give the
  codes of most of them:
  - in single files and projects: `median` and `quantile` (MySQL has no
    interpolated percentile), `string_agg` (`GROUP_CONCAT` truncates
    silently), a GROUPS frame with an offset bound, and EXCLUDE CURRENT ROW,
    GROUP or TIES;
  - in single files: `first` and `last`; the conditional sum
    `sum(o.f for o in group if ...)`; `stddev`, `variance`, `pvariance` and
    `pstdev` of an `Int`; a window key that names a computed `Text` `let`;
    and an asof JOIN in a relation with a FULL JOIN, outside the seven files
    above;
  - in projects, in every form: `stddev`, `variance`, `pvariance` and
    `pstdev` of an `Int`; `Float` arithmetic other than between two
    literals, a sign on a `Float` value and `Float /`; `count_distinct`,
    `sum` and `avg` of a `Float`; `select distinct` over a `Float`, `Float`
    `union distinct`, `intersect` and `except`, a `Float` window key and a
    `percent_rank` or `cume_dist` result as a key; a `Float` literal list
    whose value and an option both read rows, and a `Float` `in` or `not in`
    in a WHERE over a let with `capture` lines; `UUID` query parameters;
    `sum` and `avg` over a window; scalar calls or arithmetic around
    aggregate results; a direct `sum` of a `Decimal`; an `in` or cast in a
    query that a JOIN reads or that reads JOIN rows; `max(a, b)` and
    `min(a, b)` of two `Date` values; `add_months`, `concat`, `round` with
    digits, `date_trunc` and `Text(x)` of an `Int`; typed `values(...)` and
    `generate_series`; FULL JOIN, which is not planned; and collected lists
    and nested results, which leave Phase77 for a separate work package;
  - in projects, outside the forms that the subsections above open: `Int`
    arithmetic not proved to fit signed 64 bits, `Int /`, `Int %` and `sum`
    of an `Int`, also conditional, over a JOIN or in two levels; `Float %`;
    `stddev`, `variance`, `pvariance` and `pstdev` of a `Float`; a `Float`
    GROUP BY key; `==`, `!=` and `same_value` of two `Float` row reads, also
    inside `any(...)` and `not any(...)`; `Decimal(p, s)`, `Date` and
    `Timestamp` query parameters; the conditional count, `any` and `all`
    over a group, `count`, `min` and `max` over a window and
    `count_distinct(a, b, ...)`; `first` and `last`; `Decimal` plus or minus
    an `Int` or another scale, `Decimal * Int` and a sign on a `Decimal`; a
    conditional or scalar call beside a JOIN; `lag` and `lead` with a `Text`
    literal default; `lpad` and `now()`; and `same_value` in a JOIN `on`,
    never of a `Float`.

  `sum` of an `Int` and nested results are approved exceptions to the MySQL
  cadence: Phase77, the target of `sum` of an `Int`, opened it only in the
  forms that its subsections state, and its other forms stay refused with no
  target until the owner sets one; nested results wait for the separate
  nested work package. `stddev` of an `Int` is one too and has no target
  release. FULL JOIN, a GROUPS frame with an offset bound, an EXCLUDE
  clause, `median`, `quantile` and `string_agg` are out of scope for MySQL.
  No Phase77 slice took typed `values(...)`, `generate_series`, `round` with
  digits, `date_trunc`, `Text(x)` of an `Int`, a `Float` literal list over
  two row reads, or the single-file conditional sum and window key that
  names a computed `Text` `let`; the `Float` membership over a let with
  `capture` lines is this release's repair. Every other form above is a
  retained exception that Phase77 kept refused (D77.07); D77.29 records many
  of them as R01, R03 to R07, R09, R11, R12, R14 and R16 to R18.
- **Not in this release.** The SQLite and DuckDB work of Phase78 and
  Phase79 and the Python interoperability of Phase80 are not part of
  `0.1.12`; the [roadmap](roadmap.md) plans them for `0.2.0`.
- On MySQL, `lower`, `upper` and `replace` give NULL when the result would
  exceed the server's `max_allowed_packet`, although Pietto types the result
  from its arguments.
- Single-file MySQL fails the smallest `Int` `/` 1 with error 1690, where
  PostgreSQL returns the value; the [language page](language.md#expressions)
  names only the overflow of dividing it by -1.
- On both targets, execution refuses a `Timestamp` or `UUID` parameter, or
  a `Timestamp` expression over `now()` that does not keep the call's
  meaning, such as `coalesce(now(), now())`, selected as an output
  (PIE-R1004 `MEANING_OUTPUT`, or `MEANING_UNAVAILABLE` in a relation that
  `collect` reads beside a `Timestamp` or `UUID` source field): such an
  output has no meaning that its result could carry.
- On both targets, `lpad` refuses a query parameter as its text or width,
  which its SQL writes more than once (PIE-S2355), a retained exception that
  D77.29 records as R13.
- `Float % Float` is accepted by `check` but refused by single-file
  `emit-sql` on both targets (PIE-B1000); a PostgreSQL project emits it, and
  a MySQL project in the one cell above.
- Window forms of `variance`, `pvariance`, `pstdev`,
  `count_distinct(a, b, ...)`, `first` and `last` are refused, and
  `any(... for o in group)` and `all(... for o in group)` take no window.
  The conditional count and sum, `any`, `all`, `first` and `last` over JOIN
  rows are refused (PIE-S2334): join in one query, then group it in another
  that reads it with `from`.
- A project FULL or CROSS JOIN that reads a `Timestamp`, `Date` or `UUID`
  field (a `select` item, a `where` operand, a group key or a window key) is
  BLOCKED (PIE-B1003 `scalar_meaning_requires_field_projection`) on both
  targets while an input has a `Timestamp` or `UUID` field.
- A project `same_value` in a JOIN `on` emits only in the qualified
  statements of its subsection; every other one is BLOCKED (PIE-B1003
  `match_condition_not_in_row_domain`) on both targets. A project WHERE or
  JOIN over a source whose shape declares no field is BLOCKED (PIE-B1003
  `zero_column_stage_not_admitted_on_target`) on both targets.
- `max(a, b)` and `min(a, b)` of two numeric types, such as an `Int` and a
  `Float`, are refused (PIE-S2104), and six or more nested values stop at
  PIE-S2399; a project `max(a, b)` of two `Bool` values is refused
  (PIE-B1003) on both targets. `add_months` takes a `Date` only.
- `pietto lsp` publishes no backend refusal (`PIE-B...`) and discovers no
  root (roots come only from `projectRoots`); hover, definition and
  completion cover only the uses that the `0.1.11` notes list. A root nested
  inside another root through a symbolic link publishes its modules under
  both spellings without the overlap message.
- The known limitations of 0.1.11 that the subsections above do not change
  still hold.

## Project arithmetic, aggregate composition and editor navigation public alpha release notes — 0.1.11

**Status:** These notes cover `0.1.11`, the public alpha prepared from its
release commit, which follows the Phase77 repair batch and changes only
version owners and documentation. It is published only when the tag
`v0.1.11`, the versioned GitHub pre-release and PyPI carry its accepted wheel
and sdist; this document neither creates those channels nor substitutes for
their byte verification. As for earlier releases, the compiler and package
are covered on CPython 3.12 and 3.13 for Linux x86-64. CI also runs the
platform-neutral tests with CPython 3.12 and 3.13 on Windows x86-64, and batch
`emit-sql --project ROOT --all --output DIR` stays Linux-only; other platforms
and Python versions are not covered.

`0.1.11` is the release of Phase76 and of the work published before its
cut: the Phase77 repairs, found by a whole-repository audit, the Phase77
dependency maintenance and the independent editor work package. It retires
no source spelling of `0.1.10`, but refuses `Int` literals outside signed 64
bits (see "Upgrading from 0.1.10"). It brings PostgreSQL projects closer to
single files, lets a single file group by a computed `let` and wrap
aggregates in scalars, opens `Decimal * Int`, writes MySQL single-file
constants and `now()`, verifies a PostgreSQL server against a CA file, and
gives `pietto lsp` hover, definition, symbols, links, formatting and
completion. The MySQL catch-up of Phase77 is not part of it; the known
limitations list what MySQL still refuses. Each subsection below lists the
changes against `0.1.10` that a program can observe, its compatibility rows
and the new refusals; the last one lists the known limitations. The Python
execution extras change two pins
(see "Dependency maintenance: PyArrow 26.0.1 and Psycopg 3.3.8"). The
sections from 0.1.10 down describe published files.

### Highlights

- **PostgreSQL projects closer to single files.** `Float` `+`, `-`, `*` and
  sign over fields; `Float` window, `string_agg` and FULL JOIN keys; `Int /`,
  `Int %`, `Float /` and `Float %`; `Decimal` plus or minus an `Int` or
  another scale, `Decimal * Int` and checked `sum(Decimal(p, s))`; a
  conditional, `in`, cast or scalar call beside a JOIN; `max(a, b)` and
  `min(a, b)` of two `Date` values; and FULL and CROSS JOINs beside an unread
  `Timestamp` or `UUID` field.
- **Scalars around aggregates and computed keys.** `coalesce(sum(qty), 0)`
  and `sum(qty) * 100 / count()` in a single file or a PostgreSQL project, and
  a single-file GROUP BY of a computed `let`.
- **MySQL single files** write top-level constants, `--set` values and
  `now()` as PostgreSQL does.
- **PostgreSQL server verification.** `PostgresAccess(..., ca_file=PATH)`
  checks the server certificate against your CA file before any credential is
  sent.
- **Editor (alpha).** `pietto lsp` adds hover and go-to-definition, document
  and workspace symbols, import links, formatting of the open buffer and
  completion.
- **Repairs.** Single-file PostgreSQL `Int` arithmetic is computed in 64 bits,
  a negated `-0.0` constant no longer starts an SQL comment, MySQL `Float`
  list membership over two row reads is refused, and inputs that stopped
  `check`, `explain`, `emit-sql` or `pietto lsp` with a Python traceback now
  get a diagnostic.

### Upgrading from 0.1.10

- **`Int` literals outside signed 64 bits are refused.** In a single file
  such a literal is now PIE-S2364, such an `Int` constant PIE-S2391 and such a
  `--set` value a usage error (exit 2); write a `Float` with a decimal point,
  such as `100000000000000000000.0`, where a `Float` is meant. See
  [Single-file `Int` literals in the signed 64-bit range](#single-file-int-literals-in-the-signed-64-bit-range).
- **SQL text changes.** Single-file PostgreSQL SQL writes `len(s)` as
  `CAST(length(s) AS bigint)`, casts the left operand of an `Int` `+`, `-`,
  `*` or `%` whose operands may both be `integer`, and writes `-2147483648`
  as `CAST(-2147483648 AS bigint)`; a sign before a constant whose value is
  negative is parenthesised, as in `-(-0.0)` (`0.1.10` wrote `--0.0` on
  PostgreSQL). A MySQL project `Float` literal
  list whose value and an option both read rows, which `0.1.10` emitted, is
  now BLOCKED (PIE-B1003 `membership_type_pair_not_admitted`).
- **Execution extras.** The extras select `pyarrow==26.0.1` and
  `psycopg[binary]==3.3.8`; an environment that keeps `pyarrow 26.0.0` or
  `psycopg 3.3.5` is refused with PIE-R2002. Upgrading `pietto` alone leaves
  them in place, so reinstall with the extra, for example
  `pip install -U "pietto[execute-postgres]"`.
- **Execution requests.** A query whose result needs more than the 64 Arrow
  fields of one batch is refused while it is prepared, with PIE-R1004
  (`LIMIT`), before any connection.
- **Compiled bundles and saved jobs.** As with every release, those made
  under `0.1.10` or earlier are refused by code identity; new bundles carry
  the version marks `(8, 1, 8, 1)`. `load_bundle` now also refuses, with
  PIE-R1008, a re-pinned bundle whose row stages do not follow its rows or
  whose operands form a cycle or an unbounded expansion; bundles that Pietto
  writes load as before. A compiled MySQL artifact that holds the `Float`
  list above is refused when it is replayed.
- **Configuration and packages.** A `pietto.toml` whose multi-line string
  holds a line like a `[package]` header followed by a `#` comment with the
  string's closing quotes can now be refused (see
  [Project configuration `[package]` table proof](#project-configuration-package-table-proof)),
  and a package asset path that starts with a non-ASCII letter and a colon,
  such as `é:x.pietto`, is refused as `C:/x.pietto` is (exit 2).
- Tools that compare exact diagnostics, SQL text or JSON must expect the
  changes listed below: diagnostics where `0.1.10` stopped with a Python
  traceback, changed messages of
  PIE-S2310 and PIE-R2004, the removed PIE-S2105 `Decimal` messages, the new
  suggestion of `set_row_equivalence_domain_unsupported`, project blockers
  located at the refused form, and the additive R05 evidence value
  `target_checked_binary64_overflow` of the project JSON v2 `arithmetic`
  requirement, which strict readers must accept.
- `PostgresAccess` gains the optional last field `ca_file`; calls without it
  keep their meaning.
- The output of `fmt` and the alpha surfaces `pietto lsp`, `pietto.compiler`
  and the relation-column document may still change before the Phase82
  freeze; each change is listed in these release notes. `pietto lsp` now
  answers an invalid `projectRoots` list with the JSON-RPC error `-32602`
  instead of stopping.

### FULL and CROSS JOINs beside an unread `Timestamp` or `UUID` field (projects)

- A `schema_version = 2` project relation with a FULL or CROSS JOIN now emits
  on PostgreSQL, and one with a CROSS JOIN also on MySQL, when an input has a
  `Timestamp` or `UUID` field that no JOIN of the relation passes to a read. `0.1.10` refused it on both targets with
  PIE-B1003 `scalar_meaning_requires_field_projection`, which has no
  location. The JOIN, its condition and the relation's rows, grain and
  output are those that `0.1.10` emits for the same relation without that
  field; the field is carried through the JOIN's CTE and never output, and
  compiled bundles carry it unchanged. A two-database run (PostgreSQL 18.6,
  MySQL 8.4.12) of these JOINs matched the expected rows on both databases.
- A relation that reads a `Timestamp`, `Date` or `UUID` field through a FULL
  or CROSS JOIN (a `select` item, a `where` operand, a group key or a window
  key) keeps that refusal while an input has a `Timestamp` or `UUID` field. A
  MySQL FULL JOIN stays refused (`mysql_full_join_approved_non_support`).

Changed diagnostics (programs refused in `0.1.10` too; no accepted program
changes):

| Program | 0.1.10 | Now |
| --- | --- | --- |
| A project relation with a FULL or CROSS JOIN, an input with a `Timestamp` or `UUID` field that it does not read, and another refusal, such as `full join c on orders.customer_id == c.id and c.name == c.name` on PostgreSQL | PIE-B1003 `scalar_meaning_requires_field_projection`, no location | that relation's own refusals, here PIE-B1003 `full_join_equality_within_one_input` at the `on` condition |
| The same relation with a FULL JOIN on MySQL | PIE-B1003 `scalar_meaning_requires_field_projection`, no location | PIE-B1003 `mysql_full_join_approved_non_support` at the JOIN, as without the field |

### Scalar forms beside a JOIN in PostgreSQL projects

- `emit-sql --project --dialect postgres` now emits a statement with a JOIN
  whose other tables, queries and `let`s, those without a JOIN of their own,
  use a conditional (also a `def` that inlines to one, such as
  `length_band(minutes) == 2`), a comparison chain, `in`, a cast or a scalar
  call: a query the JOIN reads, a `let` with capture lines that a JOIN reads
  LATERAL, and a query that reads the JOIN's rows. Each renders as it does in
  a statement without the JOIN, the CTE of a query the JOIN reads byte for
  byte, and the compiled replay and the live template carry the same SQL. A
  computed column of such a query, a derived `Date` among them, may be an
  equality JOIN key. This closes the two-module example's limitation of
  `0.1.10`: a query whose WHERE calls a def that inlines to a conditional is
  no longer BLOCKED when another query JOINs it.
- Over JOIN rows an aggregate argument that holds a scalar call is emitted
  inside the aggregate, as over one input: `count(lower(r.label))`,
  `count_distinct(trim(r.label))`, `count(len(r.label))`,
  `count(lower(trim(r.label)))`.
- Kept refused: such a form at a joined site, in the joined query's own
  `let`, WHERE or `on` (`where band(r.id) == 2` after the JOIN, or
  `let t = lower(r.label)` with `count(t)`), keeps its `0.1.10` blockers.
- MySQL is unchanged: each of these statements keeps its `0.1.10` blockers
  until its own two-database run.

### `max(a, b)` and `min(a, b)` of two `Date` values in PostgreSQL projects

- On PostgreSQL a project conditional whose values are two `Date` values of
  one carrier is emitted as `CASE`, so `max(a, b)` and `min(a, b)` of two
  `Date` values are too, with compiled replay and the live template, as for
  two `Timestamp` values. MySQL keeps them refused (PIE-B1003
  `conditional_realization_not_admitted`); project `Bool` values stay refused
  on both targets.

Compatibility (PostgreSQL projects; MySQL output is unchanged):

| Input | Before (0.1.10) | Now |
| --- | --- | --- |
| A query whose WHERE calls `length_band(minutes) == 2`, read by another query's JOIN | BLOCKED PIE-B1003 `scalar_projection_requires_later_slice` at each SELECT item of the JOIN query, then `join_shape_not_admitted_in_slice7` | VERIFIED |
| `count(lower(r.label))` over the rows of a JOIN | BLOCKED PIE-B1003 `operator_not_implemented_in_slice6`, `join_shape_not_admitted_in_slice7` | VERIFIED |
| `max(a, b)`, `min(a, b)`, `a if c else b` of two `Date` values | BLOCKED PIE-B1003 `conditional_realization_not_admitted` | VERIFIED |

Changed diagnostics (PostgreSQL projects; no message text changed): a
statement with a JOIN that reads a table or query whose own form stays
refused is now refused at that form, with its own blocker and suggestion.

| Input | Before (0.1.10) | Now |
| --- | --- | --- |
| A query with `m = matches(label, "a.*")` read by another query's JOIN | BLOCKED PIE-B1003 `scalar_projection_requires_later_slice` at each SELECT item of the JOIN query, then `join_shape_not_admitted_in_slice7` (no location) | BLOCKED PIE-B1003 `scalar_call_signature_not_admitted` at the `matches` select item |

### `Float` arithmetic and `Float` keys in PostgreSQL projects

PostgreSQL project SQL (`emit-sql --project`) now emits these forms, which
`check --project` already accepted (D76.02 E4, E6). MySQL project SQL keeps
each one BLOCKED with its `0.1.10` code; the known limitations of this release
list them. No VERIFIED output of `0.1.10` changes.

- A `Float` `+`, `-` or `*` whose operands are not both `Float` literals, such
  as `price * 2.0`, `price + cost` or `cost - price * price`, written
  `(a * CAST('2.0' AS pg_catalog.float8))` or `(a + b)` (before: PIE-B1003
  `float_literal_operands_required`), and a sign on a `Float` value, such as
  `-price`, written `(-a)` (before: PIE-B1003
  `unary_sign_requires_int_operand`). The value is Python's binary64 result,
  the sign of a zero included (`-price` of `0.0` is `-0.0`). PostgreSQL fails
  the statement with SQLSTATE 22003 where the result leaves binary64
  (`value out of range: overflow`) and where a product of two non-zero values
  rounds to zero (`value out of range: underflow`; Python gives `0.0`); it
  never returns an infinity or a wrong value. Each such `+`, `-` or `*` has the
  R05 evidence `{"overflow": "target_checked_binary64_overflow"}` (new on the
  `arithmetic` requirement kind; a reader that requires a statically proved
  finite result refuses it). The forms hold wherever a `let` does: in WHERE, a
  computed `let` GROUP BY key, an aggregate argument (`sum(price * 2.0)`) and
  over JOIN rows. A typed `None` operand keeps
  `float_literal_operands_required`.
- A `Float` as a window `partition by` or `order by` key (before: PIE-B1002
  `window_partition_comparison_domain_unsupported`,
  `window_order_comparison_domain_unsupported`), as a `string_agg` order key
  (before: PIE-B1003 `group_key_type_outside_reviewed_comparison_domain`) and in
  a FULL JOIN equality, alone or beside `Int` equalities (before: PIE-B1003
  `full_join_equality_outside_reviewed_int_domain`).
- A window `percent_rank` or `cume_dist` result read from another relation as
  a `group by` key (before: PIE-B1003
  `group_key_type_outside_reviewed_comparison_domain`), a `select distinct:`
  column (before: `distinct_field_comparison_domain_unsupported`), a relation
  `order by` key (before: `order_comparison_domain_unsupported`), a column of
  UNION DISTINCT, INTERSECT and EXCEPT (before:
  `set_row_equivalence_domain_unsupported`) and a window key (before: the
  PIE-B1002 window details above).

Each key compares by `Float` equality and orders by real value, as the
[Float values](language.md#float-values) contract states: `-0.0` and `0.0` are
one partition, peers of a window order and a FULL JOIN match, and a merged row
shows some member's value. `count_distinct`, `min` and `max` of a
`percent_rank` or `cume_dist` result, arithmetic over one, and an offset `RANGE`
frame over a `Float` key stay BLOCKED.

Fixed: a `group by` key over another relation's window result, such as
`group by ranks.rk` with `rk = rank() window(order by g)` in the table
`ranks`, was BLOCKED with PIE-B1008 `plan_ast_correspondence` on both
dialects, because the independent emission verifier rebuilt the key column
without the window origin the emitted column keeps; it is now emitted on
PostgreSQL and MySQL.

### Changed diagnostics

The `PIE-B1003` detail `set_row_equivalence_domain_unsupported` keeps its
code and ordering. Its suggestion changed from:

> Use Int, Bool, Text, Decimal or Float with exact matching carriers. On MySQL a Float set is limited to UNION ALL, a window distribution result is limited to UNION ALL on both targets, and Timestamp to UNION ALL/DISTINCT; keep other unreviewed set carriers in check --project.

to:

> Use Int, Bool, Text, Decimal or Float with exact matching carriers. On MySQL a Float set, a window distribution result included, is limited to UNION ALL, and Timestamp to UNION ALL/DISTINCT; keep other unreviewed set carriers in check --project.

The compiled record format is unchanged.

### Project expression emission

- PostgreSQL project emission now supports `Float % Float` over ordinary
  finite `Float` operands with an exact binary64 truncating-quotient
  remainder lowering. `check` and `check --project` accept it on both
  targets; a single file and a MySQL project refuse it at emission (below).
  Decimal and mixed numeric remainder still fail `check` with PIE-S2105.
- PostgreSQL project `lag` and `lead` accept static Text literal defaults,
  preserving UTF-8 text, C collation and the maximum result character width.
- PostgreSQL project `Int / Int` and `Int % Int` now emit, and so does
  `Float / Float` over ordinary finite `Float` operands; a zero divisor
  remains a target error instead of becoming MySQL NULL.

### Changed diagnostics

- PostgreSQL project `Int / Int` and `Int % Int`, and `Float / Float` over
  ordinary finite `Float` operands, previously blocked with
  `PIE-B1003 binary_operator_not_admitted`, now emit.
- A `Float %` failed `check --project` and `check` with PIE-S2105 in
  `0.1.10`; both now accept it on both targets. A project emits it on
  PostgreSQL over ordinary finite `Float` operands, the other project forms
  below are BLOCKED, and a single file refuses it at emission.
- A project `/` or `%` that stays BLOCKED reports the refusal of an operand
  refused on its own, and a `/` of an `Int` and a `Float` reports
  `arithmetic_requires_signed_int_operands`, where `0.1.10` reported
  `binary_operator_not_admitted` (the last two project rows).

The first two project rows hold for a literal operand, `None` included, or
a field operand (`ratio / 2.0`, `None / ratio`, `ratio / ratio`,
`ratio % 0.1` and `ratio % ratio` over a `Float` field `ratio`), and every
project row holds for both literal policies. A `None` operand and a
`percent_rank` or `cume_dist` result read from another relation are not
ordinary finite `Float` operands. Each project blocker of the `Now`
column is located as `binary_operator_not_admitted` is; an operand's refusal
keeps the suggestion that operand has alone, and every other blocker has the
suggestion of `binary_operator_not_admitted`.

| Project form | 0.1.10 | Now |
| --- | --- | --- |
| MySQL `Float / Float` | BLOCKED PIE-B1003 `binary_operator_not_admitted` | BLOCKED PIE-B1003 `float_division_not_realized` |
| MySQL `Float % Float` | `check --project` ERROR PIE-S2105 `Invalid operands for operator %: expected Int operands`; the `emit-sql --project` document is BLOCKED with that error and no blocker | BLOCKED PIE-B1003 `float_remainder_exact_binary64_not_realized` |
| `/` over a `percent_rank` or `cume_dist` result read from another relation (`f / 2.0`), PostgreSQL or MySQL | BLOCKED PIE-B1003 `binary_operator_not_admitted` | BLOCKED PIE-B1003 `float_division_not_realized` |
| `%` over such a result (`f % 2.0`), PostgreSQL or MySQL | as MySQL `Float % Float` | BLOCKED PIE-B1003 `float_remainder_exact_binary64_not_realized` |
| PostgreSQL `/` with a `None` operand (`None / ratio`, `ratio / None`, `None / 2.0`, also in `where`) | BLOCKED PIE-B1003 `binary_operator_not_admitted` | BLOCKED PIE-B1003 `float_division_not_realized` |
| PostgreSQL `%` with a `None` operand (`None % ratio`, `ratio % None`, `None % 2.0`, also in `where`) | as MySQL `Float % Float` | BLOCKED PIE-B1003 `float_remainder_exact_binary64_not_realized` |
| `/` of an `Int` and a `Float` (`id / 2.0`, `ratio / id`, `2 / ratio`, also in `where`), PostgreSQL or MySQL | BLOCKED PIE-B1003 `binary_operator_not_admitted` | BLOCKED PIE-B1003 `arithmetic_requires_signed_int_operands` |
| `/` or `%` with an operand refused on its own, such as MySQL `(id * 2) / 2`, `-id % 2` and `-ratio / ratio`, and `(f * 2.0) / 2.0` over such a result on PostgreSQL or MySQL | BLOCKED PIE-B1003 `binary_operator_not_admitted`; a `Float %`, such as MySQL `-ratio % ratio`, as MySQL `Float % Float` | BLOCKED with the refusal of the operand it holds, as that operand alone reports it: in order PIE-B1002 `arithmetic_outside_physical_range`, PIE-B1002 `unary_result_outside_physical_range`, PIE-B1003 `unary_sign_requires_int_operand` (also for `-ratio % ratio`) and PIE-B1003 `float_literal_operands_required` |

| Single-file form | 0.1.10 | Now |
| --- | --- | --- |
| `Float % Float` (`ratio % ratio`, `ratio % 0.1`), PostgreSQL | `check` and `emit-sql` ERROR PIE-S2105 `Invalid operands for operator %: expected Int operands` at the `%` expression | `check` accepts it; `emit-sql` refuses it at the relation with PIE-B1000 `PostgreSQL SQL emission is not implemented for RelationIR: <name>. PostgreSQL Float remainder requires project emission` |
| `Float % Float`, MySQL | as on PostgreSQL | `check` accepts it; `emit-sql` refuses it at the relation with PIE-B1000 `MySQL SQL emission is not implemented for RelationIR: <name>. MySQL Float remainder is not qualified` |

#### Compiled compatibility

This is the one Phase76 compiled schema and occurrence change: version
marks become `(8, 1, 8, 1)`. Recompile bundles and saved jobs from `0.1.10`;
the loader rejects their earlier marks with a typed failure. This does not
request rerunning a database query or migrating saved result data; result
reading keeps its separate existing contract.

### PostgreSQL Decimal project carriers

- PostgreSQL project emission now supports qualified Decimal plus/minus Int
  and Decimal values of different scales, including typed header parameters
  when the pair changes carrier shape. Its emitted arithmetic has the derived
  `numeric(p,s)` carrier; an already-refused same-shape Decimal parameter pair,
  Decimal literals, Decimal/Float and Decimal division remain refused.
- Direct `sum(Decimal(p,s))` emits a checked `numeric(p+19,s)` result only
  when that carrier fits 65 precision digits and 30 scale digits. A sum outside
  it fails with SQLSTATE 22003 rather than returning a value outside Pietto's
  result carrier. Decimal `avg` remains refused.

### Changed diagnostics

- PostgreSQL project `sum(Decimal(p,s))` forms that previously reported
  `PIE-B1004 decimal_aggregate_range_proof_missing` now emit when their exact
  input and result carrier satisfy the documented E10 bounds. MySQL and all
  out-of-range or unqualified forms retain deterministic refusal.

### PostgreSQL server verification with `ca_file`

`PostgresAccess` gains an optional last field, `ca_file`: the path of a PEM
file of the CAs you trust. With it, both PostgreSQL routes, `postgres_rows`
and `postgres_adbc`, connect with libpq `sslmode=verify-full` and that file as
the only root: the server's certificate must chain to a CA in the file and
name `host`, in a subject alternative name of `host`'s kind (an IP address or
a DNS name) or, when it has none of that kind, in its common name. Otherwise
the attempt fails with `PIE-R2004` before the startup message, so neither the
user name nor the password is sent; a missing file fails the same way. A `ca_file` with
`sslmode="disable"`, an empty `ca_file`, `ca_file="system"` (libpq's name for
the system's trusted roots) and a `ca_file` that is not a string are refused
with `PIE-R1002` (`EXECUTION_ACCESS_PROFILE`) before any connection. Pietto
reads no environment variable, default file or system store for a CA.
`MySQLAccess` is unchanged; its `ca_file` stays required.

Compatibility: `ca_file` defaults to `None` and comes after `sslmode`, so every
existing call keeps its meaning and its connection options: without
`ca_file`, `require` still encrypts without verifying the server. `repr()` of
a `PostgresAccess` without `ca_file` is unchanged; with one it ends with
`ca_file='PATH'`. No SQL, compiled record, bundle or saved-job record
changes.

### Read limits

`ExecutionLimits` is the read-limit contract of execution, as documented in
[Results](execution.md#results): `batch_rows` (at most 4096) and
`batch_bytes` (at most 8 MiB) bound each batch, `max_rows` and `max_bytes`
bound what an attempt delivers, `seconds` is its deadline, and each
PostgreSQL statement has a server-side limit of at most 10 seconds. No limit
changes. The PostgreSQL rows route still receives the whole native result at
the first batch, so the delivery limits do not bound what the driver
receives; bound the query with `limit`.

Changed diagnostics (no accepted program changes):

| Case | Before | After |
| --- | --- | --- |
| every `PIE-R2004` | message `the selected route's connection, TLS profile or authentication failed; PostgreSQL requires TCP SCRAM-SHA-256, a password encrypted with password_encryption='scram-sha-256', and a first matching pg_hba.conf scram-sha-256 line; MySQL requires caching_sha2_password, TLS and a caller CA that verifies server identity` | same code and category; message `the selected route's connection, TLS profile or authentication failed; PostgreSQL requires TCP SCRAM-SHA-256, a password encrypted with password_encryption='scram-sha-256', a first matching pg_hba.conf scram-sha-256 line and, with a ca_file, a server certificate that this CA verifies for the host; MySQL requires caching_sha2_password, TLS and a caller CA that verifies server identity` |
| `PostgresAccess(..., ca_file=PATH)` | `TypeError` from the constructor | accepted, or `PIE-R1002` `EXECUTION_ACCESS_PROFILE` for the values above |

### MySQL single files: constants, `--set` and `now()`

- MySQL single-file emission writes top-level constants and `--set` values
  as PostgreSQL does: each read is its literal, `DATE '...'` or
  `TIMESTAMP '...'` for a `Date` or `Timestamp`, and the SQL is
  byte-identical to the value written in the file. A table or query that
  reads a constant, directly, through a `def` or a relationship or by reading
  such a table or query, now emits; `0.1.10` refused each with PIE-B1000.
  The statements of the two-database differential that checked constants
  before `0.1.10` are emitted byte for byte.
- `now()` in a MySQL single file is `UTC_TIMESTAMP(6)`, and `date_of(now())`
  is `DATE(UTC_TIMESTAMP(6))`: the start of the running statement in UTC with
  microseconds, one value for every read of the statement, whatever the
  session time zone, as on PostgreSQL. A MySQL project still refuses `now()`
  with PIE-B1003 `scalar_call_signature_not_admitted`.
- The [capability page](capabilities.md) gains a row for `string_agg` and
  splits query header parameters by type: `Bool`, `Int`, `Float` and `Text`
  emit on MySQL projects, and `Decimal(p, s)`, `Date`, `Timestamp` and `UUID`
  are BLOCKED there with PIE-B1003
  `query_parameter_type_not_admitted_on_target`, as in `0.1.10`.

Changed diagnostics (programs refused in `0.1.10`; no accepted program
changes):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-B1000 | MySQL single file, a table or query that reads a constant | `MySQL SQL emission is not implemented for RelationIR: <name>. MySQL has no top-level constants yet; emit with --dialect postgres` | none: the relation emits, or reports the refusal of another form it holds |
| PIE-B1000 | MySQL single file, a table or query that reads `now()` | `MySQL SQL emission is not implemented for RelationIR: <name>. Unsupported MySQL function call: now` | none: the relation emits, or reports the refusal of another form it holds |

### Decimal multiplication by Int and unary signs

`Decimal * Int` and `Int * Decimal`, and unary `+` and `-` of Decimal,
now pass semantic checking. Single-file PostgreSQL and MySQL emission
renders these forms, including `sum(amount * n)` for an Int field `n`.
PostgreSQL projects retain an exact `Decimal(p+19,s)` product carrier while
`p+19 <= 65`; unary signs preserve `(p,s)`. Qualified Decimal/Int header
parameters use the same rule. MySQL project forms remain refused.

This removes the former `PIE-S2105` messages and JSON suggestions
`a Decimal multiplies only by a Decimal; Decimal times Int is not supported yet`
and `a Decimal has no sign operator yet; write ...` for these forms, and the
single-file product aggregate's `PIE-B1000`. Decimal/Float arithmetic still
reports `PIE-S2105`; same-scale Decimal parameter addition and parameter
Decimal/Decimal multiplication keep their refusal, as do project Decimal
division and `avg`. Products wider than 65 digits remain `PIE-B1002`.

### Computed let keys in single-file grouping

Single-file queries can group by and select a concrete computed `let`, using
its binding identity and inferred type as in projects. PostgreSQL and MySQL
lower the key expression in place; nullable keys retain their nullability.
The two-query form remains supported. The previous PIE-S2102 computed-key
refusal and PIE-S2329 self-selection refusal disappear for admitted keys;
non-key reads and invalid bindings remain refused. Scalar expressions around
aggregate results are covered by the aggregate-composition notes.

Semantic metadata keeps its v1 field-reference shape: computed GROUP BY keys
report all real field dependency leaves in per-key encounter order, including
repeats. A literal-only key has no field leaf; an empty `group_keys` summary
is not proof that GROUP BY is absent. Existing direct-field JSON/text bytes
are unchanged.

### Scalars around aggregate results

A single-file or PostgreSQL project SELECT can wrap direct aggregates in
scalar calls and arithmetic, using literals and its GROUP BY keys:
`coalesce(sum(qty), 0)` and `sum(qty) * 100 / count()` for `qty: Int | None`.
In a single file, `round(avg(amount), 2)` accepts `amount: Decimal | None`.
Each aggregate keeps its argument rules; each scalar keeps its type
rules. The existing two-query route remains accepted. Computed `let` group
keys retain their binding identity, and `first` and `last` retain their unique
ordering requirement inside a scalar call.

Nested aggregates, windows inside these expressions, raw input fields outside
an aggregate that are not group keys, and same-SELECT aliases remain refused.
This does not introduce general expressions after aggregation: conditional,
comparison and constructor forms around aggregates remain outside this first
version. A Float `avg` with a digits argument to `round` remains refused;
a Decimal average here is a single-file form.

`PIE-S2310` now says that aggregate composition requires scalar calls or
arithmetic over direct aggregates, group keys and literals, then identifies
the invalid composition. It retains the two-query suggestion. Supported
compositions no longer produce that blanket refusal; an invalid scalar call
reports its ordinary `PIE-S2104` type diagnostic instead, including a Float
average passed to `round` with digits. Unknown names retain `PIE-S2102`.

The worked example in `examples/queries/aggregate_composition.pietto` combines
a computed Text group key, nullable Int quantities, nullable Decimal amounts,
Decimal-by-Int multiplication, unary sign and aggregate composition, beside
its two-query equivalent.

In a grouped query with at least one real SELECT aggregate, another named
scalar output may use only its group keys and literals, such as `label = id + 1`
or `fixed = 7`. These checked outputs keep the existing HAVING and ORDER BY
alias namespace. A whole grouped query without an aggregate stays refused.
Without GROUP BY, a separate `fixed = 7` beside `n = count()` still reports
`PIE-S2312`; a single wrapped aggregate such as `count() + 1` remains accepted.
HAVING itself gains no new scalar-call or arithmetic syntax.

Single-file ORDER BY of a standalone literal output remains refused with
`PIE-S2380`, because spelling its value there would be read as a column
position or rejected. A project's already projected ORDER BY port retains
its existing value meaning.

PostgreSQL projects use their qualified result carriers and retain each
aggregate's argument and JOIN fan-out proofs. Decimal arithmetic keeps its
operation-specific proof; SUM's checked cast is not a product range proof.
MySQL projects refuse each authored outer composition in source order with
`PIE-B1003 aggregate_composition_not_admitted_on_target`. The suggestion is
`Keep this declaration in check/plan or select an artifact using the forms reviewed for the requested target. Do not relabel the target or source carrier to bypass this refusal.`
The two-query route retains its target rules. Active compiled execution keeps
the same boundary; retained logical-only records gain no execution grant.

Aggregate SELECT parameter positions remain `PIE-S2355`. A legal WHERE
parameter stays legal beside composition, while portable observation export
with parameter reads stays `OUTSIDE_SCHEMA`. A specialized literal use across
SELECT and HAVING makes every derived read of that authored identity preserve
its value; equal text at another source occurrence is independent.

Aggregate inspection records enumerate each real primitive call occurrence,
including repeated calls, while keeping its outer selected-output ownership
separate. `result_position` is the primitive-leaf ordinal and
`selected_ordinal` remains the SELECT ordinal; a zero-leaf output creates no
primitive fact. Existing direct-only record positions and wire fields remain
unchanged.

### Header compatibility and project formatting

The semantic API ignores a hand-built Header's retired mode field:
`analyze(script)` defaults to CHECKED, and `mode_override` is the caller's
mode selection. Source headers still produce the same per-line `PIE-P1000`
diagnostics, and `migrate` keeps its deletion and manual-migration behavior.
The legacy header grammar and tokens remain until the Phase82 freeze to
preserve those readers and their output bytes. No grammar, generated parser
or built-in catalog input changed, so this change requires no extension sync.

On platforms with directory-relative file operations, `fmt --project` binds
each source write to the parent directory of its trusted read: it records that
directory's identity at the read, reopens it for the write and refuses another
directory, checks the opened file identity and original bytes, and uses the
reopened directory for temporary files, replacement and cleanup. No directory
stays open between reading and writing, so a project with more source
directories than free file descriptors is formatted too. A detected directory
or symlink replacement refuses the write; a move at the final operation cannot
redirect the write to another directory. Formatting bytes and file order are
unchanged.

The directory binding starts at the trusted read, not initial directory
discovery. The path-based fallback, including Windows, adds an opened-source
identity check but does not eliminate every directory race. Writes remain
atomic per file; a project is not one transaction.

### A negated `-0.0` constant

- A `Float` constant or `--set` value of `-0.0` now reads as `-0.0` written
  in the file, a minus sign before `0.0`, as every other negative constant
  does. Negating it emitted `--0.0` on both targets, which PostgreSQL reads
  as the start of a comment: the rest of the line was lost, so the statement
  failed or silently dropped the output. A sign before a negative literal is
  now parenthesised.

| Case | Before | After |
| --- | --- | --- |
| `flipped = -flip` with `flip: Float = -0.0` or `--set flip=-0.0` | `--0.0 AS "flipped"` | `-(-0.0) AS "flipped"` |
| `scaled = amount * flip`, the same constant | `"amount" * -0.0 AS "scaled"` | `"amount" * (-0.0) AS "scaled"` |

### An `any(...)` test as a window value is refused without a crash

When the value of `lag`, `lead`, `first_value`, `last_value` or
`nth_value`, or a `lag`/`lead` default, was an `any(...)` test, `check`,
`check --project` and single-file `emit-sql` stopped with a Python
traceback (`ValueError: Unsupported navigation expression: AnyExpr`) and
`pietto lsp` exited when such a buffer was opened. Such a value is no direct
field: a single file now reports PIE-S2104 at the call (`value must be a
direct field or Bool, Text, Int, Float, or NULL literal`, or `default must
be ...`). A project fails closed at the call too: with PIE-S2104 over JOIN
inputs, as a single file does, and with PIE-S2103 over a single input, as
it already does for a window whose PARTITION BY or ORDER BY reads
`any(...)`. No accepted program changes.

### Project aggregate windows keep their argument refusals

A selected aggregate window in an explicit-module project, over the input
rows, JOIN rows or grouped rows, whose argument nests an aggregate
(PIE-S2311) or is refused by the aggregate argument rule (PIE-S2315) now
reports that error where a single file reports it, instead of crashing:
`sum(count()) window(order by id)` reports PIE-S2311
`Nested aggregate count() is not supported` at the inner call, and
`sum(None) window(order by id)` reports PIE-S2315
`Aggregate function sum requires a direct field argument; expression
arguments are not supported yet` at the call.

| Command | Before (`0.1.10` and until this fix) | After |
| --- | --- | --- |
| `pietto check --project` | Python traceback, `ValueError: Window diagnostics must retain exact analyzer source evidence.` | the PIE-S2311 or PIE-S2315 error, exit 1 |
| `pietto explain --project` | `project error: project_resource: Project relation columns are unavailable.` | the same error |
| `pietto emit-sql --project` | `INPUT_REJECTED` with `emission_selector` `Project planning roots are unavailable.` | `BLOCKED` with the same error |
| `pietto lsp` with the project in `projectRoots` | `project error: project_root: Project root could not be pinned.` at `pietto.toml` | the same error at the call |

A window in a hidden QUALIFY already reported these errors. No code is new,
and the CLI JSON, project JSON and relation-column formats are unchanged.

### Editor project roots that no file can have

The alpha `pietto lsp` server no longer stops when the `projectRoots`
initialization option holds a path that no POSIX file can have: one with a
NUL character, or with an unpaired UTF-16 surrogate that the file system
encoding cannot write. It refuses such a list as it refuses any other invalid
value, with the JSON-RPC error `-32602` and the message `projectRoots must be
a list of distinct absolute paths`, and then waits for the next message.

Before (measured at `864411cb` on Linux with CPython 3.13.13):
`"projectRoots": ["/tmp/a\u0000b"]` ended the server with exit code 1 and a
`ValueError` traceback on standard error, and `"projectRoots":
["/tmp/r\ud800"]` ended it with exit code 2 and `pietto: error: terminal
output could not be encoded`; neither request got a reply. After: both get the
`-32602` error above. On Windows, whose `realpath` accepts both paths, nothing
changes. Valid roots, diagnostics, the CLI commands, CLI JSON and PIE codes
are unchanged. The surface is alpha until the Phase82 freeze.

### PostgreSQL single-file `Int` literals and `len()` in 64 bits

- PostgreSQL types `length()` and an integer literal that fits 32 bits as
  `integer`, so single-file `Int` arithmetic over them failed with SQLSTATE
  22003 (`integer out of range`) beyond 32 bits, although a Pietto `Int` is
  a signed 64-bit integer: `1024 * 1024 * 1024 * 4` or `len(s) * len(s)`.
  Single-file PostgreSQL SQL now writes `len(s)` as
  `CAST(length(s) AS bigint)` and casts the left operand of an `Int` `+`,
  `-`, `*` or `%` whose two operands may both be `integer`: such a literal,
  or a sign, quotient, `abs`, `coalesce`, `nullif` or conditional of them.
  PostgreSQL reads `-2147483648` as the smallest `integer`, so `-x`,
  `abs(x)` and `x / -1` of it failed as well; that literal is now written
  `CAST(-2147483648 AS bigint)` wherever it stands. Other arithmetic with a
  field or another `bigint` operand, `/`, MySQL and project SQL are
  unchanged.
- Known limit, as before: PostgreSQL still computes in `integer` over an
  output that is such a value where another relation reads it
  (`x = 2147483647` read as `x + 1` fails with 22003), over `min` or `max`
  of such a value, and over `ntile`.

Changed PostgreSQL single-file SQL (measured on `main` before the change):

| Pietto | Before | After |
| --- | --- | --- |
| `len(name)` | `length("name")` | `CAST(length("name") AS bigint)` |
| `1024 * 1024 * 1024 * 4` | `((1024 * 1024) * 1024) * 4` | `((CAST(1024 AS bigint) * 1024) * 1024) * 4` |
| `where id < 65536 * 65536` | `WHERE "id" < (65536 * 65536)` | `WHERE "id" < (CAST(65536 AS bigint) * 65536)` |
| `-2147483647 - 1` | `(-2147483647) - 1` | `CAST(-2147483647 AS bigint) - 1` |
| `-2147483648 * 2` | `(-2147483648) * 2` | `CAST(-2147483648 AS bigint) * 2` |
| `-(-2147483648)`, `abs(-2147483648)` | `-(-2147483648)`, `abs((-2147483648))` | `-CAST(-2147483648 AS bigint)`, `abs(CAST(-2147483648 AS bigint))` |
| `where id > -2147483648` | `WHERE "id" > (-2147483648)` | `WHERE "id" > CAST(-2147483648 AS bigint)` |
| `count(len(name))` | `COUNT(length("name"))` | `COUNT(CAST(length("name") AS bigint))` |
| `id * 2`, `7 / 2`, `2147483648 * 2` | unchanged | unchanged |

### Single-file `Int` literals in the signed 64-bit range

- A single file accepted an `Int` literal outside the signed 64-bit range,
  which PostgreSQL computed as a `numeric` (so `/` kept a fraction) and
  MySQL `DIV` refused at run time. An `Int` literal, with a sign written
  directly before it, now lies from -9223372036854775808 to
  9223372036854775807: outside it, a file with no other error reports
  PIE-S2364, the code of a VALUES cell outside that range, at the literal.
  `-9223372036854775808` is accepted. A limit, window frame offset or window
  count out of range keeps its own error alone (PIE-S2307, PIE-S2104).
  An `lpad` width or `substr` index beyond the range has only a PIE-S2385
  warning, so it reports PIE-S2364 as well: `check` now fails, and
  PostgreSQL `emit-sql` reports PIE-S2364 in place of its PIE-B1000.
  The range holds wherever the literal stands, beside a `Decimal` or
  `Float` value too: a single file can no longer compare a `Decimal` with
  an integer beyond it, and a `Float` operand is written with a decimal
  point (`100000000000000000000.0`).
- An `Int` constant or `--set` value outside the range is no `Int` literal:
  the constant reports PIE-S2391 and the `--set` value is a usage error
  (exit 2). Their messages name the range.

New refusals (programs accepted before):

| Code | Case | Before | After |
| --- | --- | --- | --- |
| PIE-S2364 | `q = id / 9223372036854775808` in a single file | `check` passes with PIE-S2106 | ``Int literal 9223372036854775808 is outside the signed 64-bit range from -9223372036854775808 to 9223372036854775807.`` |
| PIE-S2364 | `where amount > 100000000000000000000`, `amount: Decimal(38, 0)` | accepted, compared exactly | the same message |
| PIE-S2364 | `ratio * 100000000000000000000`, `ratio: Float` | accepted | the same message; `ratio * 100000000000000000000.0` is accepted |
| PIE-S2364 | `lpad(name, 99999999999999999999, "0")`, `substr(name, 99999999999999999999, 1)` | `check` passes with PIE-S2385; PostgreSQL `emit-sql` refuses with PIE-B1000 | the same message beside PIE-S2385, in `check`, `emit-sql` and `explain` |
| PIE-S2391 | `n: Int = 9223372036854775808` | accepted | ``Constant `n` takes one `Int` literal: an integer such as `10` or `-10`, from -9223372036854775808 to 9223372036854775807.`` |
| usage error | `--set n=9223372036854775808` | accepted | ``--set n: constant n has type Int; write an integer such as 10 or -10, from -9223372036854775808 to 9223372036854775807`` |

### Results wider than one batch

`execute()`, `save`, `save_recoverable` and `relay_live` refuse a query whose
result needs more than the 64 Arrow fields of one batch with `PIE-R1004`
(`detail` `LIMIT`) while they prepare it, before any workspace access or
connection. A collected field counts once for itself and once for each of its
child fields. `compile_query`, `export_bundle` and `load_bundle` still accept
such a query.

Before (measured at `864411cb` on Linux with CPython 3.13.13 and PyArrow
26.0.1, without a database): a `table` of 65 columns compiled, exported and
loaded, `execute()` returned a handle and `pa.schema(result)` had 65 fields,
and the attempt's batch step refused one row with `PIE-R3004` (`detail`
`LIMIT`), which names row and byte limits that a caller can change but not
this one. Read from that code, without a database run: the attempt refused
only after its statement had run, an empty result completed with no rows, and
a saved empty result could not be read. After: the same `execute()` raises
`RequestRejected` `PIE-R1004` and nothing connects, so an empty result of such
a query is refused too.

The check runs after the code identity check and before the premise, access,
collection-route and R2 checks, so a request of more than 64 fields that one
of those also refuses now gets `PIE-R1004` (`LIMIT`) first. Measured at
`864411cb` and after: 65 columns with a premise that does not cover their
source went from `PIE-R1002` to it, and a collected field with 64 child
fields went from `PIE-R1003` (`COLLECTION_ROUTE`) on `postgres_adbc` and from
`PIE-R1004` (`COLLECTION_ENTRY`) in `relay_live` to it. No PIE code is added;
queries of at most 64 fields, SQL output and saved-result formats are
unchanged.

### Package asset paths that start with a letter and a colon

A package manifest asset path of any kind whose first character is a
non-ASCII letter followed by a colon, such as `é:x.pietto`, is now refused
as `C:/x.pietto` is: `explain --project` reports `project_path`
`Package manifest assets[0].path is structurally invalid.` and exits 2.
In JSON output its `location` names the path as a `package_relative`
value, where the `C:/x.pietto` error has a `null` location.

A manifest with a lone `module_source` asset `é:x.pietto` used to pass,
and `explain --project` printed a Python `ValueError` traceback and exited
1. Manifests that were already refused now report this `project_path`
error in place of a `config_schema` error located at `pietto-package.toml`,
and still exit 2:

- a `data` asset `é:x.pietto`, which reported
  `Package manifest assets[0].kind must be module_source.`;
- a `module_source` asset `é:x.txt`, which reported
  `Package manifest assets[0].path must end with .pietto.`;
- two `é:x.pietto` assets, which reported one
  `Package manifest assets[1].path duplicates assets[0].path.` error and
  now report one `project_path` error for each asset.

No dependency path changed, and no diagnostic code or JSON shape was added.

### Project configuration `[package]` table proof

A schema-v3 or schema-v4 `pietto.toml` now proves its `[package]` root
table with two TOML parses: one finds the only line that looks like a
`[package]` header and opens the table, and one renames that line to prove
it is the header, as before. The proof used to rename each such line in
turn and parse the whole file again, so its work grew with the square of
the number of such lines, for example lines inside a multi-line string.

A NaN anywhere in the file no longer fails that proof, so the file reports
its own fault, such as
`Project [capability_environment] contains unsupported key: weight.`, where
it reported
`Project configuration schema-v4 package activation requires an exact [package] root table.`

New refusal: a multi-line string that holds a line that looks like a
`[package]` header followed by a `#` comment containing the string's closing
quotes can now get the exact-table message where the file loaded before,
for example inside the `[package]` table itself, or in a capability fact's
`operands` array that continues on the next line. Every refusal keeps the
`config_schema` kind, and no file that was refused now loads.

### Single-file window values from every JOIN binding

In a single file with JOIN inputs, the value of `lag`, `lead`,
`first_value`, `last_value` or `nth_value`, and a `lag`/`lead` default, may
now be a field of any JOIN binding, such as `lag(o.amount)` over a query
that joins `o`, as a project already accepts. Before, only a field of the
FROM relation was accepted there and `lag(o.amount)` was PIE-S2104 (`value
must be a direct field or Bool, Text, Int, Float, or NULL literal`), even
where the PIE-S2335 refusal of an ambiguous bare name asked for `o.amount`.
PostgreSQL and MySQL emit the binding's column, such as
`LAG("o"."amount") OVER (ORDER BY "o"."id" ASC)`, and a field that a LEFT
JOIN may null-extend gives a nullable result. A hidden QUALIFY window
accepts the same values. A wrong value of a JOIN binding now reports its
real cause, as a project does: an unknown field, such as `lag(o.missing)`,
reports only PIE-S2102, without a PIE-S2104 beside it, and a default of
another type, such as `lag(o.amount, 1, "x")` over an Int `amount`,
reports PIE-S2104 `value and default must have the same exact type`.

### Editor navigation — independent editor work package

The alpha `pietto lsp` server now provides hover and go-to-definition for
resolved type and `from` references, plus document symbols for named top-level
declarations. Configured schema-v2 projects retain exact import and re-export
targets; `def` functions, relationship templates and single-file constants
appear in source order.

The server answers from facts attached to its current analysis; a request sent
while an analysis of its document or project root is pending waits for it.
Beside a project module with an error, the other modules keep their facts, but
no use navigates into that module. Unknown, conflicting, omitted or stale
facts, and a legacy-flat root, produce no navigation result; a request does
not reparse, compile or read disk. Builtin types have hover text and no
authored definition. Field, let, parameter and function-call navigation,
including a `from` that reads a relation let or a table-function input,
workspace symbols and filesystem watching remain outside this first version.

Standard LSP capability negotiation handles hover and symbol response formats.
A `file:` URI whose host does not parse, such as `file://[::1/x.pietto`, no
longer stops the server: it is checked as a standalone document. Existing
diagnostic codes, CLI JSON, semantic metadata and relation-column formats are
unchanged. This is the independently authorized editor line,
not an additional MySQL slice or a Marketplace release.

### Editor formatting — editor core work package

The alpha `pietto lsp` server now formats an open document: it advertises
`documentFormattingProvider` and answers `textDocument/formatting` with one
edit of the whole buffer that gives what `pietto fmt` prints for the same
text: it keeps a leading byte order mark and writes every line break as the
buffer's first one (LF when it has none). A buffer that is already formatted
gets no edit. The request has no result when
`pietto fmt` would refuse the buffer (a parser error, a retired header line,
the size limit, or output that formatting would not keep), when the document
is not open, when its last change was refused, or when the editor sent
unpaired UTF-16 surrogates.

Formatting reads only the open buffer: it neither waits for the analyses that
edits schedule nor starts one, although an analysis already running when it
arrives ends first; it reads and writes no file and publishes no
diagnostic. The editor's formatting options are ignored, because `fmt` has one
layout, and `fmt` output may still change before the Phase82 freeze. Range and
on-type formatting are not provided. Diagnostics, hover, definition and
document symbols are unchanged, and so are the CLI commands, CLI JSON, PIE
codes, semantic metadata and relation-column formats. The surface is alpha
until the Phase82 freeze.

### Editor workspace symbols and import links — editor core work package

The alpha `pietto lsp` server now advertises `workspaceSymbolProvider` and
`documentLinkProvider`. A `workspace/symbol` request lists the declarations
that document symbols list, for every module of the configured roots and
every other open document: the roots in `projectRoots` order, each root's
modules in the order `pietto check --project` selects them, then the other
open documents in URI order, each in source order. Every occurrence is kept,
so a name declared in two modules is listed twice. A declaration is listed
when the characters of the query appear in its name in order, ignoring the
case of ASCII letters, and every one is listed for an empty query. The
request waits while any analysis is pending, and a module or document without
facts lists nothing.

A `textDocument/documentLink` request returns one link for each import of a
schema-v2 project module, on the import path's string, to the module whose
project-relative path the string names exactly, as `pietto check --project`
resolves it. The target may have errors of its own, but there is no link in
a single file or in a module without facts, and none to a module that the
check left out, whose file shows a root, URI or file-name conflict, or whose
open document had a change refused, until that document is reopened.
Neither request resolves items later.

Both answer from the analysis that the diagnostics come from, with no new
check and no file read. Diagnostics, hover, definition, document symbols and
formatting are unchanged, and so are the CLI commands, CLI JSON, PIE codes,
semantic metadata and relation-column formats. The surface is alpha until the
Phase82 freeze.

### Editor completion — editor core work package

The alpha `pietto lsp` server now advertises `completionProvider` and answers
`textDocument/completion` with one list: the keywords that current source
writes (`True`, `False` and `None` included), the builtin types, the scalar
functions and aggregates of the core catalog, and then the identifiers that
the open buffer writes outside comments and strings, such as its field, `let`,
relation and parameter names, except the word being typed. Nothing else in
the list depends on the position, so the editor filters it as you type. The
server answers when it reads the request: it neither waits for nor starts an
analysis. It reads the buffer's words with one scan and does not parse, check
or classify them; a name spelled like a keyword, such as a field named `mode`,
is not among them, and other files are not read.

Words that `pietto check` refuses are not part of the fixed list: the retired
header words, `satisfying`, `semi` and `anti` JOINs, `cast`, `null`,
`nullable`, `endpoint` and `via`, and the PostgreSQL extension functions,
which are not callable. Window functions are not part of it either. A word
that is both a keyword and an aggregate, such as `first`, is one item of each.
There are no trigger characters, no resolve request, no context-aware
completion and no signature help.

On a development host of VS Code 1.145.2 with default settings and the Pietto
extension, the fixed list alone replaced the editor's word-based suggestions
in a `.pietto` file: the start of a field, `let` or relation name of the open
file had no suggestion, while the extension's snippets stayed. The buffer's
names are in the list so that they are still suggested; words of other open
files are not.

Diagnostics and document symbols are unchanged, and so are the CLI commands,
CLI JSON, PIE codes, semantic metadata and relation-column formats. The surface
is alpha until the Phase82 freeze.

### Editor hover and definition for fields, lets and calls — editor core work package

The alpha `pietto lsp` server now answers hover and definition on more uses,
each from a binding that the analysis already keeps, one fact per written
occurrence. In a single file, a field read of a JOIN relation shows
`field NAME` and, when it reads a source, defines the field of the source's
shape; a relationship call shows `relationship NAME` and defines its
template. In a schema-v2 project, a name that a `let` value, `select` item or
`where` of a relation without JOIN reads shows `field NAME` or `let NAME`
when the analysis bound it to exactly one input field or `let`: the field
defines its shape field when the relation reads a source, and the `let` its
binding. A `from` that reads a relation let now shows `let NAME` and defines
that let.

Every other use still has no hover or definition. In a single file, that is
any other read, such as one of a relation without JOIN, and a `let` use. In a
project, it is any other read, such as a JOIN relation's reads or a
`group by`, `order by` or window read, and a relationship call. In both, it
is a `def` call or parameter, a relationship parameter, a relationship call's
argument and a `from` that reads a table-function input. The facts come
from the analysis that the diagnostics come from, with no new check and no
file read. Diagnostics, document and workspace symbols, links and formatting
are unchanged, and so are the CLI commands, CLI JSON, PIE codes, semantic
metadata and relation-column formats. The surface is alpha until the Phase82
freeze.

### MySQL `Float` literal-list membership over two row reads

Fixed: MySQL project SQL (`emit-sql --project`) emitted a `Float` `in` or
`not in` literal list whose value and one of its options both read rows,
although each option stands for an `==` with the value and MySQL refuses
that `==` (PIE-B1003 `comparison_type_pair_not_admitted`). Such a list is
now BLOCKED with PIE-B1003 `membership_type_pair_not_admitted`, located as
that comparison is. Examples are `ratio not in (ratio)` and
`any(z.ratio in (rows.ratio) and z.text == rows.text for z in z)`, which
`0.1.10` emitted as a correlated `EXISTS` that differs from the refused
`==` form only in writing `IN (x)` for `= x`.

- A literal list whose value reads no row, or whose options read none, such
  as `0.0 in (ratio, 1.0)` or `ratio in (0.0, -0.0)`, is emitted as before.
- `value in r` over the one column of a relation `r` is unchanged on both
  targets, and PostgreSQL emits every form above as before.
- A compiled MySQL artifact that holds such a list is refused when it is
  replayed.

### Dependency maintenance: PyArrow 26.0.1 and Psycopg 3.3.8

- The optional extras now install `pyarrow==26.0.1` (`arrow`,
  `execute-postgres`, `execute-mysql` and `execute-postgres-adbc`) and
  `psycopg[binary]==3.3.8` (`execute-postgres`) instead of `26.0.0` and
  `3.3.5`. The core install is unchanged and still needs no Arrow.
- Only the new pins are accepted. An environment that keeps `pyarrow 26.0.0`
  is refused with `PIE-R2002`, before any connection on every route and at
  every public Arrow use including saved results, and `pa.schema(result)`
  refuses it with `PIE-R4004`; `postgres_rows` likewise refuses
  `psycopg 3.3.5` with `PIE-R2002` before connecting. Upgrading `pietto`
  alone leaves an extra's packages in place, so reinstall with the extra, for
  example `pip install -U "pietto[execute-postgres]"`.
- Psycopg `3.3.8` is chosen over `3.3.7`, whose change to the system SSL
  directory lookup `3.3.8` reverts.
- SQL output, result values and saved-result formats are unchanged. The
  `postgres_rows`, `postgres_adbc` and `mysql_rows` routes passed fresh local
  runs with the new pins against PostgreSQL 18.6 and MySQL 8.4.12.

### Known limitations of 0.1.11

- **MySQL refusals.** MySQL support trails PostgreSQL: a form opens on MySQL
  only after a two-database differential passes, and until then MySQL
  emission refuses it with a PIE-B code and writes no SQL. The MySQL catch-up
  of Phase77 is not part of this release; Phase77 continues it toward
  `0.1.12`, and each form opens only when its own run passes. These forms are
  refused on MySQL in `0.1.11`; the [capability page](capabilities.md) and
  the subsections above give the codes of most of them:
  - in single files and projects: `median` and `quantile` (MySQL has no
    interpolated percentile), the conditional sum
    `sum(o.f for o in group if ...)`, `string_agg` (`GROUP_CONCAT` truncates
    silently), and `first` and `last`;
  - in single files: `stddev`, `variance`, `pvariance` and `pstdev` of an
    `Int`; a window key that names a computed `Text` `let`; and an asof JOIN
    in a relation with a FULL JOIN;
  - in projects: `Int` arithmetic not proved to fit signed 64 bits, `Int /`
    and `Int %`; `sum` of an `Int`; `stddev`, `variance`, `pvariance` and
    `pstdev` of an `Int`; `Float` arithmetic other than between two
    literals, a sign on a `Float` value, `Float /` and `Float %`;
    `count_distinct`, `sum`, `avg`, `stddev`, `variance`, `pvariance` and
    `pstdev` of a `Float`; a `Float` GROUP BY key, `select distinct` over a
    `Float`, `Float` `union distinct`, `intersect` and `except`, a `Float`
    window key, `string_agg` ordered by a `Float` and a `percent_rank` or
    `cume_dist` result as a key; `==` and `!=` between two `Float` row
    reads, `same_value` of two such values and a `Float` literal list whose
    value and an option both read rows; `Decimal(p, s)`, `Date`,
    `Timestamp` and `UUID` query parameters; the conditional count,
    aggregate windows, `count_distinct(a, b, ...)`, and `any` and `all` over
    a group; scalar calls or arithmetic around aggregate results; `Decimal`
    plus or minus an `Int` or another scale, `Decimal * Int`, a sign on a
    `Decimal` and a direct `sum` of a `Decimal`; a conditional, `in`, cast
    or scalar call beside a JOIN, and `max(a, b)` and `min(a, b)` of two
    `Date` values; `lag` and `lead` with a `Text` literal default; `lpad`,
    `add_months`, `concat`, `now()`, `round` with digits, `date_trunc` and
    `Text(x)` of an `Int`; typed `values(...)` and `generate_series`; FULL
    JOIN, which is not planned; and collected lists and nested results,
    which leave Phase77 for a separate work package.

  `sum` of an `Int` and nested results are approved exceptions to the
  MySQL cadence; `stddev` of an `Int` is one too and has no target release.
- On MySQL, `lower`, `upper` and `replace` give NULL when the result would
  exceed the server's `max_allowed_packet`, although Pietto types the result
  from its arguments.
- `Float % Float` is accepted by `check` but refused by single-file
  `emit-sql` on both targets (PIE-B1000); a PostgreSQL project emits it.
- Window forms of `variance`, `pvariance`, `pstdev`,
  `count_distinct(a, b, ...)`, `first` and `last` are refused, and
  `any(... for o in group)` and `all(... for o in group)` take no window.
  The conditional count and sum, `any`, `all`, `first` and `last` over JOIN
  rows are refused (PIE-S2334): join in one query, then group it in another
  that reads it with `from`.
- A project FULL or CROSS JOIN that reads a `Timestamp`, `Date` or `UUID`
  field (a `select` item, a `where` operand, a group key or a window key) is
  BLOCKED (PIE-B1003 `scalar_meaning_requires_field_projection`) on both
  targets while an input has a `Timestamp` or `UUID` field; an unread field
  no longer blocks it.
- `max(a, b)` and `min(a, b)` of two numeric types, such as an `Int` and a
  `Float`, are refused (PIE-S2104), and six or more nested values stop at
  PIE-S2399; a project `max(a, b)` of two `Bool` values is refused
  (PIE-B1003) on both targets. `add_months` takes a `Date` only.
- `pietto lsp` publishes no backend refusal (`PIE-B...`) and discovers no
  root (roots come only from `projectRoots`); hover, definition and
  completion cover only the uses their subsections list. A root nested
  inside another root through a symbolic link publishes its modules under
  both spellings without the overlap message.
- The known limitations of 0.1.10 that the subsections above do not change
  still hold.

## Aggregates, cross-module reuse and editor tools public alpha release notes — 0.1.10

<a id="unreleased-changes-following-019"></a>
<!-- The id above keeps links written before these notes were released pointing here. -->

**Status:** These notes cover `0.1.10`, the public alpha prepared from its
release commit, the last commit of Phase75 batch 2. It is published only when
the tag `v0.1.10`, the versioned GitHub pre-release and PyPI carry its
accepted wheel and sdist; this document neither creates those channels nor
substitutes for their byte verification. As for earlier releases, the
compiler and package are covered on CPython 3.12 and 3.13 for Linux x86-64.
CI also runs the platform-neutral tests with CPython 3.12 and 3.13 on Windows
x86-64, and batch `emit-sql --project ROOT --all --output DIR` stays
Linux-only; other platforms and Python versions are not covered.

`0.1.10` is the release of Phase73, Phase74 and Phase75. It retires one
source spelling of `0.1.9`: the header lines, which `0.1.9` warned about, are
now refused. It adds conditional, ordered and statistical aggregates, small
scalar builtins and single-file constants; def and relationship imports
across modules, and table and query rows as relationship arguments; more
PostgreSQL forms on MySQL; and editor diagnostics, a Python compile API,
relation columns and project formatting. Each subsection below lists the
changes against `0.1.9` that a program can observe, its compatibility rows
and the new refusals: Phase73 first, Phase74 from "Importing a def or
relationship from another module" on, and Phase75 from "`explain --project`
lists relation columns" on; the last one lists the known limitations. The
Python execution extras keep the pins of `0.1.9`. The sections from 0.1.9
down describe published files.

### Highlights

- **New aggregates.** Count or add the rows of a group that pass a test,
  written as Python's generator: `sum(1 for o in group if o.paid)` and
  `sum(o.amount for o in group if o.paid)`; `median(x)` and
  `quantile(x, q)`; `variance`, `pvariance` and `pstdev`, as Python's
  `statistics`; `count_distinct(a, b, ...)`; the test of a group,
  `any(... for o in group)` and `all(... for o in group)`; and
  `first(x, order by k, id)` and `last(...)`, the value at the first or last
  row of a group in a total order.
- **Scalar builtins and constants.** `max(a, b)` and `min(a, b)`,
  `lpad(s, width, fill)`, `add_months(d, n)` and `now()`; top-level
  constants in a single file, which `--set` changes for one run.
- **Reuse across modules.** In an explicit-module project a module imports a
  `def` or relationship that another module exports (`export def` and
  `import def`, `export relationship` and `import relationship`), and a
  relationship parameter takes the rows of a table or query.
- **PostgreSQL projects closer to single files.** Project aggregate
  windows; typed `Decimal(p, s)`, `Date`, `Timestamp` and `UUID` query
  parameters; project aggregates of `Text`, `Bool`, `Float` and `Decimal`
  values; nested GROUP BY and DISTINCT keys; and `len`, `sum` and `any` over
  a row's collected list.
- **More forms on MySQL**, each after a two-database differential: project
  UUID ordering, project aggregates of `Text`, `Bool`, `Float` and `Decimal`
  values, `order by` a `Float`, project `min` and `max` of a `Timestamp` or
  `Date`, the backward asof JOIN, and single-file `variance`, `pvariance` and
  `pstdev` of a `Float`, `count_distinct(a, b, ...)` and the test of a group.
- **Editor and Python tools (alpha).** `pietto lsp` pushes the diagnostics
  of `check` to an editor; `pietto.compiler` returns the
  `emit-sql --project --format json` document without a subprocess;
  `explain --project` lists the columns of every table and query of an
  explicit-module project; `pietto fmt --project` formats every module, and
  `fmt` writes one spelling. Hints name the rewrite for the rules met most
  often.

### Upgrading from 0.1.9

- **Header lines are refused.** A `pietto 0.9`, `mode ...`, `dialect ...` or
  `encoding ...` line at the top of a file, which warned with PIE-P1012 in
  `0.1.9`, is now PIE-P1000 in every command and check mode. Run
  `pietto migrate FILE > FILE.new`, which deletes the header lines without
  effect; for `mode loose` or `mode strict`, delete the line and pass
  `--check-mode` instead. A dependency package with a header line no longer
  loads until it is migrated and published again, and `pietto fmt` refuses
  such a file. See
  [Header lines are refused](#header-lines-are-refused-pie-p1000).
- **Newly reserved names.** A `def` named `lpad`, `add_months`, `median`,
  `quantile`, `now`, `variance`, `pvariance`, `pstdev`, `any`, `all`, `first`
  or `last` is now PIE-S2398, so a project `emit-sql` document that holds one
  goes from VERIFIED to BLOCKED. A `constraint` or `derive` of such a name,
  called by that name, now means the builtin. In a query without GROUP BY
  where a relation or `let` named `group` is visible, a SELECT item
  `any(... for o in group)` is now PIE-S2334; it was a per-row `EXISTS` over
  that relation.
- **Other accepted programs that change.** A call whose name is both a `def`
  and a relationship, with an argument that names a table or query input, is
  now the relationship call. In a `schema_version = 2` project,
  `string_agg(x, ",", order by k)` after a JOIN whose order key names no
  field now reports PIE-S2102, as a single file does.
- Tools that compare exact diagnostics, SQL text or JSON must expect the
  changes listed below: the new PIE-S2388 warning, new refusals of forms
  that were parse errors, new and changed hint texts and JSON `suggestion`s,
  and additive JSON vocabulary that strict readers must accept, such as the
  project JSON v2 aggregate `function` values `filtered_count`,
  `filtered_sum`, `count_distinct_tuple`, `group_any` and `group_all`.
- As with every release, compiled bundles and saved jobs made under `0.1.9`
  or earlier are refused by code identity; new bundles carry the version
  marks `(7, 1, 7, 1)`.
- `pietto fmt` now writes one spelling, so a file that `fmt --check`
  accepted under `0.1.9` may be reported as `would reformat: PATH`. The
  output of `fmt` and the alpha surfaces `pietto lsp`, `pietto.compiler` and
  the relation-column document may still change before the Phase82 freeze;
  each change is listed in these release notes.
- The Pietto extension for VS Code `0.2.0` (repository
  `MianliWang/pietto-vscode-extension`, commit `5484ebdb`) shows diagnostics
  through `pietto lsp`. It is not yet on the Visual Studio Marketplace: until
  it is, use a generic LSP client as [editor diagnostics](editor-lsp.md)
  describes, or install the extension from its repository. The extension
  `0.1.0` accepted only the `0.1.2` wheel and refuses `0.1.10`.

### JOIN fan-out: the two-level route

- The PIE-S2381 message now ends, after the remedies it already names, with
  the two-level route, in every check mode, in a single file and in the
  PIE-S2381 that an EXPLICIT_MODULES project reports beside PIE-S2312 (a
  JOIN aggregate mixed with another projection without GROUP BY):
  ``; two-level route: group a first query by a unique key of each input the
  aggregate reads and by every other field that query selects, select an
  aggregate such as `count()` in it too, then aggregate in a second query
  that reads `from` it``.
  For example:
  ``An aggregate may read rows repeated by JOIN customer; match a unique key
  of customer in `on`, use `any(...)` for an input that only filters rows, or
  aggregate in a separate query first; two-level route: group a first query
  by a unique key of each input the aggregate reads and by every other field
  that query selects, select an aggregate such as `count()` in it too, then
  aggregate in a second query that reads `from` it``.
  Compatibility: only the message text changes. The code, severity, location,
  count and order of PIE-S2381 are unchanged, and so are a project's
  PIE-S2333 cause texts (`... (an aggregate may read rows repeated by JOIN
  x; ...)`), which do not add the route, although the same route closes
  them. A tool that matches the whole PIE-S2381 message must accept the new
  ending.
- No refusal changes. An average over items grouped by `orders.id` that also
  LEFT JOINs the order's payments (Phase72 case D11-04) stays PIE-S2381 in a
  single file, now with the route, and PIE-S2333 in a project, without it;
  the same query grouped by `orders.customer_id` (D11-05), whose result
  would be weighted by payment counts, stays refused the same way. Pietto
  has no rule that a group key fixes how often each row repeats.
- The two-level route is documented ([language](language.md), [style](style.md)):
  a first query grouped by the declared key of the repeated input (for
  example one row per order with `lines = count(item.id)`), and a second
  query that reads `from` it and sums or averages its rows. It is two
  ordinary grouped relations: single files emit it for PostgreSQL and MySQL;
  an EXPLICIT_MODULES project emits it for PostgreSQL VERIFIED and compiles
  and binds it as a template; project MySQL emission blocks each Int `sum`
  with PIE-B1004 `sum_int_aggregate_range_proof_missing`, as for any project
  MySQL Int `sum`. A two-database differential (PostgreSQL 18.6, MySQL
  8.4.12) of the single-file route, counting per order and summing per
  customer, and averaging over items in two levels, matched the expected rows
  on both databases.

### LIMIT 1 in a let with capture lines (documentation only)

- No behaviour changes. The docs now state what `limit 1` does when rows tie:
  a let with capture lines that ends in `limit 1`, read by a JOIN or by
  `scalar`, with an ORDER BY whose keys several rows share, or without ORDER
  BY, gets the row the database picks, with no warning and no refusal, and
  the pick may differ between runs and databases; end the ORDER BY with a
  unique field to fix it. `limit 1` is not a proof of at most one row: an
  aggregate of the left rows over a JOIN of such a let stays PIE-S2333.

### Conditional count and sum: `sum(1 for o in group if ...)`

- A single file now counts and adds the rows of a group that pass a test,
  written as Python's generator: `sum(1 for o in group if o.paid)` is the
  number of rows of this group whose test is True, and
  `sum(o.amount for o in group if o.paid)` adds their non-None `amount`, an
  `Int` field (an alias of `Int` included). Both are an `Int` that is never
  None: 0 when no row matches. A None test is no match. `group` is the rows of
  the current group after `from` and `where`, with their multiplicity (the
  rows `count()` counts); a query with aggregates and no GROUP BY reads its
  whole input as one group. The test reads the member's fields as `o.f` and,
  besides them, only the GROUP BY key fields. A generator is a whole aliased
  SELECT item, as every other non-window aggregate; `having` and `order by`
  read its output name.
- PostgreSQL emits `COUNT(CASE WHEN <test> THEN 1 END)` and
  `COALESCE(CAST(SUM(CASE WHEN <test> THEN CAST(<f> AS pg_catalog.int8) END)
  AS pg_catalog.int8), 0)` (a sum outside signed 64 bits fails with SQLSTATE
  22003, as `sum(Int)` does). MySQL writes the count the same way,
  `COUNT(CASE WHEN <test> THEN 1 END)`, a `BIGINT` (its two-database
  differential passed: the same rows and types as PostgreSQL), and refuses
  the sum (below).
- `where any(p for o in orders)` and `not any(...)` are unchanged, with the
  same SQL bytes: `for o in orders` always means every row of `orders`, never
  the current group.
- `pietto fmt` needs no new rule: a generator is tokens inside a call's
  parentheses. Its canonical layout is the whole call on its item's line,
  one space around `for`, `in` and `if`.

New refusals (programs that were PIE-P1000 before; the hint follows `; ` at
the end of the message and is also the JSON `suggestion`):

- MySQL single file, conditional sum: PIE-B1000 `MySQL SQL emission is not
  implemented for RelationIR: <name>. MySQL conditional sum of an Int argument
  is not supported` (MySQL sums integers in DECIMAL; a later MySQL catch-up
  takes it up).
- A `schema_version = 1` project, every generator: PIE-S2334 at the call,
  before semantic analysis, ``sum(... for ...): a schema_version = 1 project
  has no generator in the current syntax; set schema_version = 2 to check
  it`` (the callee's name in place of `sum`). A `schema_version = 2` project
  checks generators as a single file does (see [conditional count and sum in
  projects](#conditional-count-and-sum-in-projects)).
- PIE-S2334 at the call: ``count takes no generator; count matching rows with
  `sum(1 for o in group if ...)` `` (`len` likewise: ``len takes no generator;
  ...``); ``max takes no generator; a conditional max is not available; only
  `sum(... for o in group if ...)` takes a generator`` (also `min`, `avg`,
  `stddev`, `count_distinct`, `string_agg`); `A generator is only the argument
  of sum or any` for another known callee, such as a builtin or a `def`;
  ``any takes its test in the body; write `any(p and q for o in r)` `` for an
  `any(...)` with an `if` (``write `any(q for o in r)` `` when its body is
  `True`).
- At the source: PIE-S2301 ``Unknown or unavailable generator source: grp;
  for this group's rows write `for o in group` ``; PIE-S2334 ``Generator over
  orders in sum: orders is the whole relation, not this group; for this
  group's rows write `for o in group` `` (in a relation with a non-aggregate
  SELECT item and no GROUP BY: ``...; count per key in a grouped query and
  join it on the key``); a relation named `group`: ``Generator over group in
  sum: group is the relation group, not this group; rename the relation group
  to read this group's rows`` (a `let group`: `the let group`, `rename the let
  group`); a dotted source: ``A generator over c.items reads a row's
  collected list, which only a project collects; `sum` and `any` read a
  collected list in a project whose pietto.toml sets `schema_version = 2` ``
  (see [lists of one row](#lists-of-one-row-len-sum-and-any-postgresql-projects)).
- PIE-S2308 at the call for a group generator in a `where`, `let`, JOIN
  `on`, `having`, `order by` or `def` body: ``Aggregate sum() is not allowed
  in where clause; use it only as a direct aliased select projection; a
  group's rows exist only after `group by`; test a row's own fields
  directly`` (`let binding`, `JOIN ON`, `this position`; in `having clause`
  and `order by` without the part after the second `; `); PIE-S2313 without
  an alias; PIE-S2310 inside an expression.
- PIE-S2334 at the call for JOIN inputs: ``sum(... for o in group ...) over
  JOIN rows is not available yet; join in one query, then group it in another
  that reads it with `from` ``.
- PIE-S2334 at the call for a body without `if`: ``sum(1 for o in group)
  counts every row of the group; write `count()` ``; ``sum(o.amount for o in
  group) adds every row of the group; write `sum(amount)` ``.
- PIE-S2315 at the call for another body: `Aggregate function sum of a
  generator adds 1 or one field of o; expression bodies are not supported
  yet`, with ``; filter with `if` after the source: `sum(o.f for o in group
  if ...)` `` for a conditional body and ``; read the member as `o.amount` ``
  for a bare field.
- PIE-S2314 at the call for the summed field's type: ``Aggregate function sum
  of a generator adds an Int field of o, got Bool; count with `sum(1 for o in
  group if o.paid)` `` (`..., got Text` for another type); `Aggregate function
  sum of a generator adds an Int field of o; a Float or Decimal sum is not
  available yet`.
- In the test or body, at the read: ``Generator reads paid outside its
  member; write `o.paid` `` (PIE-S2334, also for `orders.paid`); a `let` of
  the query, a computed GROUP BY key included (an aggregate argument reads a
  `let` only as the whole argument): ``Generator reads the let k outside its
  member; write the let's expression over fields of o, such as `o.f` ``
  (PIE-S2334); ``Generator
  reads its member o as a value; read a field of it: `o.f` `` (PIE-S2334);
  PIE-S2102 `Unknown or unavailable field in generator: o.a.b` (also `o.f`
  where `f` names a `let`); PIE-S2102 `Unknown field: nosuch` at `o.nosuch`;
  PIE-S2311 for a nested aggregate; PIE-S2334 `A generator test reads one
  member row: no window, any(...), generator, relation read or captured field`;
  PIE-S2202 `Expected Bool expression in generator test` at a non-Bool test.
- PIE-S2334 at the call over an input without known fields (a source without
  a shape): `sum(... for o in group ...) reads an input whose fields are not
  known; give its source a shape`.
- PIE-P1000 stays for a second `for`, a second `if` (`Missing ')' before
  'if'.`), a second argument (`Missing ')' before ','.`), `[o for o in ...]`
  and SQL `FILTER (WHERE ...)`, and for a generator in a table-function
  `from` argument or a QUALIFY call (texts unchanged, `Unexpected 'for'; expected
  ')' or ','.` / `Unexpected 'for'.`).

Changed diagnostics of programs refused before (no accepted program is
refused; compatibility):

- Every generator call other than the exact `any(p for o in r)` was PIE-P1000
  (`Unexpected 'for'; expected ')' or ','.`, `Unexpected 'for'.` or, with an
  `if` in `any`, `Missing ')' before 'if'.`); it is now admitted or one of the
  refusals above.
- A generator in a SELECT window call, `r = sum(1 for o in group)
  window(order by id)`, was `Unexpected 'for'.` at the `for`; it is now
  ``Unexpected 'window'; expected ',' or end of line. A window call is a whole
  `select:` item on a line of its own.`` at the `window`.
- `any(p for o in group)` where no relation or `let` is named `group` is now
  the test of a group in a SELECT item; elsewhere it keeps PIE-S2301 (in a
  `having`, PIE-S2334) with the suggestions of "The test of a group: `any`
  and `all` over `group`" below.
- PIE-S2315 of `sum(amount if paid else 0)` and `count(1 if paid else None)`
  (a conditional argument, outside a window) gains ``; write `sum(o.v for o in
  group if ...)` `` (`sum`) or ``; write `sum(1 for o in group if ...)` ``
  (`count`) at the end of its message; its JSON `suggestion`, null before, is
  the text after that `; `.
- PIE-S2314 of `sum(paid)` over a Bool field gains ``; count with `sum(1 for o
  in group if o.paid)` `` (the field's name in place of `paid`); its JSON
  `suggestion`, null before, is the text after that `; `.
- PIE-S2103 of `count_if`, `countif`, `sum_if` and `sumif`, in any letter
  case, gains ``; write `sum(1 for o in group if ...)` or `sum(o.v for o in
  group if ...)` ``, also its JSON `suggestion` (null before); the PIE-S2319
  that a grouped SELECT reports after it at the same span is unchanged.
- The parser's nesting limits are unchanged: an expression nested inside a
  call or window-call argument parses to the same depth as before.

New warning (compatibility: a program that checked clean now reports a
warning; its exit code and SQL are unchanged):

- PIE-S2388 (WARNING, single-file check, every check mode, at the call):
  ``count(paid)` counts every row whose paid is not None, False included; to
  count the rows where it is True, write `sum(1 for o in group if o.paid)` ``
  for `count` of one field, bare or qualified (`count(orders.paid)` names it
  as written), of `Bool` type or an alias of `Bool`. Not reported at a call
  with an error of its own, at a window call (`count(paid) window(...)`),
  which takes no generator, nor in a project. No JSON `suggestion`, as for
  the other habit warnings.

### Nested GROUP BY and DISTINCT keys (PostgreSQL projects)

- In a `schema_version = 2` project on PostgreSQL, a table or query without
  JOIN inputs, a window or QUALIFY may `group by` a nested field read with
  `from` (`group by xs`, with `xs` and aggregates in its SELECT) and
  `select distinct` it. Two values
  are one key when both are None, or have the same length and pairwise
  `same_value` children in the collected let's order: `[1.0]`/`[1.00]` one
  key, `[-0.0]`/`[0.0]` one key (the key shows one member's value), `[]`,
  `[None]` and None three keys, `[1, 2]`/`[2, 1]` two keys. Emission groups by
  the count and every array column; `emit-sql --project`, compiled bundles
  and results carry the key as a collection.
- **New refusal text (code unchanged).** PIE-S2805 at the key or DISTINCT item
  when the collected let's ORDER BY may tie: ``Nested relation field xs cannot
  be a GROUP BY key: the ORDER BY of its collected let does not end in a
  declared unique key, so rows that tie have no promised order.`` and
  ``Nested relation field xs cannot be part of SELECT DISTINCT: the ORDER BY of
  its collected let does not end in a declared unique key, so rows that tie
  have no promised order.``, suggestion ``End the `order by` of the collected
  let with the fields of a `unique(...)` key of its source, such as `id`.``
- **Compatibility.** A program that grouped by a nested field with
  `group by xs` and selected `xs` reported two PIE-S2805 (``cannot be read in
  GROUP BY`` at the key and ``cannot be selected in a table or query with
  GROUP BY or an aggregate`` at the item); it now checks, or reports the one
  tie refusal above at the key. A `select distinct` of a carried nested field
  reported ``cannot be part of SELECT DISTINCT: a collected relation has no
  equality.``; it now checks or reports the tie refusal. Beside an admitted
  key the body's other errors are reported as beside a scalar key (for
  example PIE-S2308 for `having count() > 1`, where the key reported PIE-S2805
  before). Bodies with JOIN inputs keep every earlier refusal.
- **Compatibility, window or QUALIFY.** In a body with a window or QUALIFY,
  `group by xs` keeps ``Nested relation field xs cannot be read in GROUP BY: a
  collected relation has no comparison, ordering, grouping or scalar value.``
  at the key. A SELECT item `xs` that names that key, and a `select distinct`
  item `xs`, now report ``Nested relation field xs cannot be selected beside a
  window or QUALIFY yet.`` (suggestion ``Compute the window in another table or
  query and join it here.``) at the item, where they reported ``Nested
  relation field xs cannot be selected in a table or query with GROUP BY or an
  aggregate: it is no group key and has no aggregate.`` and ``Nested relation
  field xs cannot be part of SELECT DISTINCT: a collected relation has no
  equality.`` before. Same code, position and count.
- A nested field selected as it is beside scalars, without JOIN inputs and
  without DISTINCT, still checks and stays BLOCKED in `emit-sql --project`
  (PIE-B1003 `expression_evidence_unavailable`), whatever else the project
  reads. No program that checked before is refused now.
- **Unchanged refusals.** Nested `==`, ORDER BY and set-operation dedup stay
  PIE-S2805. MySQL keeps PIE-B1003 `collect_not_admitted_on_target`
  for every Collect read (Phase77).
- **Formats.** A result contract document may now carry a collection leaf
  with role `group_key`; a reader older than this change refuses it as
  `DOCUMENT`. A compiled bundle may now carry an `aggregate` record whose key
  reads a collection port and a DISTINCT `result` record that reads one; an
  older reader refuses such a bundle with `COMPILED_COLLECTION_PORT` or
  `COMPILED_COLLECTION_READ`. Neither format gains a record kind or field, so
  both keep their version marks.

### `max(a, b)` and `min(a, b)`

- `max(a, b)` and `min(a, b)`: Python's larger and smaller of two values (the
  first on a tie), `None` when either value is `None`; nest for more values,
  `max(a, max(b, c))`. Checked and emitted as
  `(b if a < b else a) if b is not None else b` (`>` for `min`), so SQL is a
  `CASE WHEN`, never PostgreSQL `GREATEST`/`LEAST`, which skip a NULL. The
  values are any pair that compares with `<` and has one type: `Int`,
  `Decimal`, `Float`, `Text`, `Date`, `Timestamp`, `UUID` and `Bool` in a
  single file (both targets); in `emit-sql --project` (with compiled
  replay and the live template) `Int`, `Decimal`, `Float`, `Text`,
  `Timestamp` and `UUID` on both targets (MySQL `UUID` with the UUID ordering
  of "MySQL catch-up in projects" below). Project `Date` and `Bool` values are
  refused (PIE-B1003 `conditional_realization_not_admitted`,
  `comparison_type_pair_not_admitted`).
  A `def` body may call them, and they work in WHERE and inside larger
  expressions. A two-database differential (PostgreSQL 18.6, MySQL 8.4.12)
  matched the expected rows for each of these types. On MySQL, which has no
  boolean type, two `Bool` values give an integer column holding 0, 1 or NULL,
  as every computed `Bool` (such as `a < b`) does there.

New or changed diagnostics (exact):

- PIE-S2104 (new message), at the call:
  `Invalid argument types for function max: expected same canonical comparable type`
  (also `min`), for values that do not compare as for `<` or have two
  canonical types, such as `max(t, 1)` with a `Text` `t` or `max(n, 1.5)` with
  an `Int` `n`.
- PIE-S2104 (new message), at the call:
  `Invalid argument type for function max at position N: expected a non-None value, got None`
  (also `min`), for a `None` argument or a `let` name bound to `None`; when the
  `None` reaches a `max`/`min` in a `def` body as a def argument, at the def
  call (`bigger(a, None)` with `def bigger(x: Int, y: Int | None) -> Int | None: return max(x, y)`).
- PIE-S2399 (new message, existing code and stage): a `max`/`min` call whose
  conditional, with each nested call written out, has more than 1000
  expression nodes or 64 levels:
  `The expansion of max has 3070 expression nodes nested 16 deep; an expansion, with its arguments, has at most 1000 nodes nested at most 64 deep`
  (for `max(a, max(a, max(a, max(a, max(a, a)))))`; `min` alike), at the
  innermost such call. Five fields nested in the second position, or seven in
  the first, fit.
- PIE-S2309 (message suffix): a `max`/`min` call with three or more arguments
  now reads `Aggregate function max expects 1 arguments, got 3; for more values, nest two-argument calls: max(a, max(b, c))`
  (`min` alike). Code, position and prefix are unchanged.
- PIE-S2103 (hint): `Unknown function: greatest; write `max(a, b)`, which is None when either value is None`
  and `Unknown function: least; write `min(a, b)`, which is None when either value is None`,
  in any letter case (`GREATEST`, `Least`).

Compatibility:

`a`, `c` are `Int` fields and `b` an `Int | None` field.

| Input | Before (0.1.9) | Now |
| --- | --- | --- |
| `max(a, b)` / `min(a, b)`, two arguments | PIE-S2309 `Aggregate function max expects 1 arguments, got 2` | accepted (scalar), or PIE-S2104 as above when the values do not fit |
| `max(x, None)` / `min(x, None)` | PIE-S2309 (an extra `None` argument was a wrong aggregate arity) | PIE-S2104 `... at position 2: expected a non-None value, got None` |
| `max(a, max(b, c))` (a nested call) | PIE-S2311 `Nested aggregate max() is not supported`, at the inner call | accepted |
| `max(a, max(nosuch, a))` | PIE-S2311 at the inner call, then PIE-S2102 `Unknown field: nosuch` | PIE-S2102 only |
| six or more nested values, such as `max(a, max(a, max(a, max(a, max(a, a)))))` | PIE-S2311 at the second call | PIE-S2399 `The expansion of max has 3070 expression nodes ...` at the outer call |
| `max(a, b) + 1` in a SELECT item | PIE-S2310 `Aggregate projection must be a direct aggregate call; composition around max() is not supported yet` | accepted |
| `where min(a, c) > 1` | PIE-S2308 `Aggregate min() is not allowed in where clause; use it only as a direct aliased select projection` | accepted |
| grouped SELECT item `m = max(a, b)` over fields that are not group keys | PIE-S2309 `Aggregate function max expects 1 arguments, got 2` | PIE-S2319 `Grouped scalar projection expressions are not supported yet`, as for the conditional it means |
| `def bigger(x: Int, y: Int) -> Int: return max(x, y)` | PIE-S2397 `Def bigger body uses the aggregate max; a def body reads only its parameters and calls scalar functions`, at the call in the body | accepted; a call that passes `None` is PIE-S2104 at the def call, a wrong argument type PIE-S2395 as before |
| `max`/`min` with 3+ arguments | PIE-S2309 | PIE-S2309, same prefix, hint suffix added |
| `greatest(...)`, `least(...)` | PIE-S2103 `Unknown function: greatest` | PIE-S2103 with the hint suffix |
| a file declaring a `constraint`, `derive` or relationship template named `max`/`min` | two-argument call PIE-S2309 | unchanged (the file keeps the earlier meaning) |
| `def max` / `def min` | PIE-S2398 | unchanged (no user `def` newly becomes PIE-S2398: both names were already reserved as aggregates) |
| one-argument `max(x)`/`min(x)` aggregate, window `max(x) window(...)` | unchanged | unchanged |

### `lpad` and `add_months`

- **`lpad(s, width, fill)` pads Text on the left and never truncates.** It
  is Python's `s.rjust(width, fill)`: a `s` of `width` characters or more, or
  a width of 0 or less, is `s` itself (SQL `LPAD` cuts it; MySQL `LPAD` gives
  NULL for a negative width). `fill` is a one-character `Text` literal written
  in the call; there is no default. The result is `None` when `s` or `width`
  is `None`.
  - PostgreSQL SQL: `CASE WHEN length(s) >= width THEN s ELSE lpad(s,
    CAST(width AS integer), 'f') END`; project SQL casts to
    `pg_catalog.int4` and parenthesises the CASE. Single-file MySQL SQL:
    `CASE WHEN CHAR_LENGTH(s) >= width THEN s ELSE LPAD(s, width, 'f') END`.
    A two-database differential (PostgreSQL 18.6, MySQL 8.4.12) matched the
    expected rows.
  - Project SQL (PostgreSQL) gives the result a width of the larger of the
    text's width and the width's upper bound.
- **`add_months(d, n)` moves a Date by months.** The day becomes the last day
  of a shorter month, and a month end is not sticky: one month after
  2024-01-31 is 2024-02-29, one month after 2024-02-29 is 2024-03-29. `None`
  when `d` or `n` is `None`. Date only in this release.
  - PostgreSQL SQL: `CAST((d + make_interval(months => CAST(n AS integer)))
    AS date)` (project: `pg_catalog.int4`). Single-file MySQL SQL:
    `DATE_ADD(d, INTERVAL n MONTH)`. The same differential matched both
    databases, month ends included.
- **New diagnostic texts** (codes unchanged; each at the whole call):
  - PIE-S2104 `Invalid arguments for function lpad: fill must be a
    one-character Text literal, such as "0"` for a fill that is a field, a
    `let` name, `None`, `""` or more than one character.
  - PIE-S2104 `Invalid arguments for function lpad: expected 3, got 2; fill
    must be a one-character Text literal, such as "0"` for a missing fill.
  - PIE-S2104 `Invalid argument type for function add_months at position 1:
    expected Date, got Timestamp; add_months takes a Date, such as
    add_months(date_of(ts), n)`.
  - PIE-S2103 hint (the lookup ignores letter case): an unknown `rjust` call,
    and a call whose dotted name ends in `.rjust` such as `code.rjust(5,
    "0")`, adds ``; write `lpad(s, width, fill)`, which pads like Python
    `str.rjust` and never truncates``.
  - PIE-S2385 (single-file check, PostgreSQL relations), at the call:
    `this lpad width is outside PostgreSQL's 32-bit integer range` for an
    integer literal width outside the signed 32-bit range (also under unary
    signs or through a `let:` name), and `PostgreSQL types a CASE, coalesce
    or nullif of only None values as text, which function lpad does not
    take` (`... which function add_months does not take`) for such a width
    or `add_months` argument.
- **New refusals.**
  - Single-file PostgreSQL emission, for the cases the PIE-S2385 warnings
    above name: PIE-B1000 `PostgreSQL SQL emission is not implemented for
    RelationIR: <name>. PostgreSQL lpad width is outside signed int32
    range` and `... PostgreSQL types a CASE, COALESCE or NULLIF of only
    NULL values as text, which function lpad does not take` (also
    `add_months`).
  - PostgreSQL project SQL: `lpad` with a width whose proven range leaves the
    signed 32-bit range, such as an `Int` field stored as `bigint`, is PIE-B1002
    with the new detail `lpad_width_outside_physical_range`; with a text or a
    width that has no proven bound, a `None` width included, PIE-B1004 with
    the new detail `lpad_result_bound_missing`; with a `None` text, and
    `add_months` with a `None` argument, PIE-B1003
    `scalar_call_signature_not_admitted`.
  - MySQL project SQL refuses `lpad` and `add_months`, as it refuses `concat`,
    `round` and `date_trunc`: PIE-B1003 `scalar_call_signature_not_admitted`
    at the statement part that holds the call.
- **Compatibility.** `lpad` and `add_months` are now reserved built-in names:
  a `def lpad(...)` or `def add_months(...)` is PIE-S2398 (``Def lpad has the
  name of a built-in function; a def cannot shadow one``) with the suggestion
  ``Rename this def: `lpad` is now the built-in left pad of Text, and a call
  to lpad always means it.`` (for `add_months`: ``Rename this def:
  `add_months` is now the built-in month arithmetic on Date, and a call to
  add_months always means it.``), so a project's `emit-sql` documents that
  hold such a def go from VERIFIED to BLOCKED. A `constraint` or `derive`
  named `lpad` or `add_months` called by that name, which was PIE-S2103
  (``Unknown function: lpad; lpad is a derive, which cannot be called; write a
  `def` instead``), now means the built-in. A call of `lpad` or `add_months`
  is no longer PIE-S2103.
- **Known limits.** A result after 9999-12-31 is outside Pietto's dates
  (PostgreSQL gives a later date, MySQL NULL); MySQL `LPAD` gives NULL when
  the result would exceed `max_allowed_packet`; single-file PostgreSQL may
  raise an error for an `add_months` count, or an `lpad` width that is not
  an integer literal, outside the signed 32-bit range (never another value;
  project SQL refuses such an `lpad` width with PIE-B1002). Single-file SQL
  writes an `lpad` text three times, so nested `lpad` calls grow the SQL
  threefold per level, as nested `round` of a Float grows it fivefold; project
  SQL stops at PIE-B1007 `public_artifact_byte_limit`.

### Aggregate windows in projects

- An EXPLICIT_MODULES project now admits `sum`, `count`, `avg`, `min` and
  `max` over a window, as a single file does: as a selected output of a table
  or query, over grouped rows (`running = sum(total) window(order by k)`), in a
  hidden QUALIFY window (`qualify: count(x) window(partition by k) > 1`), and
  over JOIN rows, with partition and order keys, an omitted or explicit
  ROWS/RANGE/GROUPS frame (GROUPS and EXCLUDE on PostgreSQL only, as for every
  window) and named windows. `check --project` accepted none of them before
  (PIE-S2103 `Aggregate window functions are not implemented: NAME`).
- A project's aggregate window reads each argument as one input column: each
  argument is a direct field (an input field, under GROUP BY a key or an
  aggregate output, or a `let` name bound to one). Another argument, such as
  `sum(amount * 2)` or a `let` name whose value is computed, is the new
  PIE-S2103 `Unsupported window computation for function NAME: argument must
  be a direct field in a project`, at the call, selected, in QUALIFY or over
  JOIN rows. A single file keeps admitting it. An argument the ordinary
  aggregate rules refuse keeps their diagnostic first, as in a single file
  (`count(1) window(order by id)` is PIE-S2104 `Invalid arguments for
  function count`).
- Changed diagnostic (compatibility, project): a hidden QUALIFY window in a
  query with aggregates and no GROUP BY, also over JOIN rows, is now
  PIE-S2103 `Unsupported window computation for function NAME: a query with
  aggregates and no GROUP BY admits no hidden QUALIFY window` at the call, as
  in a single file. It was the relation's bare PIE-S2333 `Project relation
  semantic completion is unavailable: NAME` for a window function such as
  `row_number`, and PIE-S2103 `Aggregate window functions are not
  implemented: NAME` for `sum`, `count`, `avg`, `min` and `max`.
- Changed text (compatibility): in a project, another aggregate called with a
  `window` specification (`stddev`, `count_distinct`) is now
  `Aggregate window functions are not implemented: NAME; window aggregates are
  sum, count, avg, min and max`, as in a single file (it had no suffix).
- `emit-sql --project` on PostgreSQL emits the project aggregate with `OVER`:
  `sum` of an Int is `CAST(SUM(CAST(x AS pg_catalog.int8)) OVER (...) AS
  pg_catalog.int8)` (SQLSTATE 22003 instead of a wrong total), `avg` of an Int
  `AVG(CAST(x AS pg_catalog.float8)) OVER (...)`, `count()` `COUNT(*) OVER
  (...)`, `count(x)`, `min` and `max` the plain aggregate; an omitted frame is
  written out (`RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`). The
  argument domain is the project aggregate's: a `Decimal` or `Float` `sum` or
  `avg` is PIE-B1004 (`decimal_aggregate_range_proof_missing`,
  `float_aggregate_finite_result_proof_missing`), and an argument outside the
  reviewed domain PIE-B1003 (`<function>_argument_outside_reviewed_int_domain`).
  Compiled bundles and live templates of these statements bind and render the
  same SQL. In `emit-sql --project --format json`, the R14
  `window_computation` requirement of a window `sum` of an Int carries
  `{"overflow": "target_checked_signed64_narrowing"}`, as the R13 `aggregate`
  requirement of a grouped one does; `window_origin.function` may be `sum`,
  `count`, `avg`, `min` or `max`, and `ranges` add the `syntax` roles
  `window_argument_cast_open`, `window_argument_cast_close`,
  `window_result_cast_open`, `window_result_cast_close` and
  `window_row_count`.
- New refusal: `emit-sql --project --dialect mysql` refuses every aggregate
  window with PIE-B1003 `window_aggregate_approved_non_support_on_mysql`, at
  the window, until its real-database differential, with the suggestion
  `Emit this aggregate window for PostgreSQL, or keep it in check/plan: a
  project's MySQL aggregate window awaits its real-database differential.`
  (single-file MySQL is unchanged).
- **Formats.** The compiled format's version marks become schema 7 and
  occurrence 7 (`(7, 1, 7, 1)`), Phase73's one change of them: a
  `window_value` record may name `sum`, `count`, `avg`, `min` or `max`
  (PostgreSQL), and only such a value may reference a `window_spec` with an
  empty `ordering`. A bundle labelled with earlier marks is refused with
  `COMPILED_COMPATIBILITY` (PIE-R1008 from `load_bundle`), with no migration;
  rebuild it with this version.
- **Known limits.** A project `count() window()` (no argument, partition or
  order key) passes `check --project`, but `emit-sql --project` refuses it
  with PIE-B1004 `window_result_anchor_missing`. The opt-in tie refinement
  (`TieRefinement`) does not lower aggregate windows; a refined execution of
  one is refused. A project aggregate window with a RANGE offset frame
  (`range between 1 preceding and current row`) passes `check --project`, but
  `emit-sql --project` keeps the existing RANGE offset refusal PIE-B1002
  `window_range_boundary_out_of_signed64_range`, as for `first_value`.

### Project aggregates match single files on PostgreSQL

- `emit-sql --project` on PostgreSQL now emits, VERIFIED, the aggregate forms
  a single file emits and a project refused before:
  - `count(x)` and `count_distinct(x)` of a `Text`, `Bool`, `Float` or
    `Decimal` value, as `COUNT(x)` and `COUNT(DISTINCT x)` (before: PIE-B1003
    `count_argument_outside_reviewed_int_domain`,
    `count_distinct_argument_outside_reviewed_int_domain`);
  - `min(x)` and `max(x)` of a `Float` or `Decimal` value, as `MIN(x)` and
    `MAX(x)`, keeping the argument's carrier and nullable (before: PIE-B1003
    `min_argument_outside_reviewed_int_domain`,
    `max_argument_outside_reviewed_int_domain`);
  - `sum(x)` and `avg(x)` of a `Float`, as the uncast `SUM(x)` and `AVG(x)`,
    a nullable `Float` (`pg_float8`, `finite_float`) with the R13 evidence
    `target_checked_binary64_overflow`: PostgreSQL raises SQLSTATE 22003
    instead of returning an infinite value, `avg` also where its running sum
    of squares overflows (about |x| > 1e154) (before: PIE-B1004
    `float_aggregate_finite_result_proof_missing`);
  - an aggregate whose argument is a row expression, such as `sum(qty * 2)`,
    `avg(qty + 1)`, `count(lower(label))`, `count_distinct(trim(lower(label)))`
    or `count(flag and flag)`, emitted inside the aggregate as a `let` would
    lower it (before: PIE-B1003
    `aggregate_argument_not_a_direct_established_field`). It is admitted
    exactly where `let t = <expression>` with `sum(t)` is, and otherwise
    reports that `let`'s blocker: `%` is PIE-B1003
    `binary_operator_not_admitted`, Float arithmetic over a field PIE-B1003
    `float_literal_operands_required`, an `Int` times a `Decimal` literal
    PIE-B1003 `arithmetic_requires_signed_int_operands`.
- `count_distinct`, `min` and `max` compare by the GROUP BY key law of the
  argument's carrier: `-0.0` and `0.0` are one distinct value, and a `min` or
  `max` whose extreme class holds both zeros shows some member's value (the
  `Float` value contract). These forms also emit over JOIN rows (`sum(r.ratio)`,
  `count_distinct(r.label)`, `min(r.ratio)`, `count(r.flag and r.flag)`,
  `sum(-r.value)`), except an argument that holds a scalar call, and compiled
  bundles and live templates of these statements bind and render the same
  SQL.
- Kept refused:
  - `sum` and `avg` of a `Decimal` stay PIE-B1004
    `decimal_aggregate_range_proof_missing` on both targets (a Decimal sum has
    no bounded precision and a Decimal average no fixed scale, so no
    `Decimal(p, s)` carrier holds the result). On PostgreSQL this now includes
    a `Decimal` row expression such as `sum(amount + amount)`, which reported
    PIE-B1003 `aggregate_argument_not_a_direct_established_field` before, at
    the same select item.
  - Over JOIN rows an aggregate argument that holds a scalar call such as
    `lower`, `trim` or `len` (`count(lower(r.label))`,
    `count_distinct(trim(r.label))`, `count(len(r.label))`) stays BLOCKED on
    PostgreSQL, unchanged, with PIE-B1003 `operator_not_implemented_in_slice6`
    and `join_shape_not_admitted_in_slice7`, as `let t = lower(r.label)` with
    `count(t)` is: over JOIN rows such a call is admitted only directly in a
    SELECT item. A single file emits these forms.
  - An aggregate over a window keeps the `Int` domain of the previous
    subsection: a window `sum` or `avg` of a `Float` stays PIE-B1004
    `float_aggregate_finite_result_proof_missing`, and a window `count` of a
    `Text`, `Bool`, `Float` or `Decimal` value or a window `min` or `max` of a
    `Float` or `Decimal` value stays PIE-B1003
    `<function>_argument_outside_reviewed_int_domain`.
- MySQL is unchanged: `emit-sql --project --dialect mysql` keeps each of these
  forms BLOCKED with its existing detail
  (`<function>_argument_outside_reviewed_int_domain`,
  `float_aggregate_finite_result_proof_missing`,
  `aggregate_argument_not_a_direct_established_field`, or first PIE-B1002
  `arithmetic_outside_physical_range` / `unary_result_outside_physical_range`
  for `Int` arithmetic not proved to fit BIGINT) until a real-database
  differential reviews them.
- No diagnostic code, detail, hint text, JSON shape or single-file SQL changes.
  A project statement that was BLOCKED only by these forms is now VERIFIED on
  PostgreSQL; one that also had another blocker now reports fewer blockers. A
  PostgreSQL row expression argument that stays refused now reports, at the
  same select item, the blocker its `let` form reports instead of PIE-B1003
  `aggregate_argument_not_a_direct_established_field` (`count(value % 2)`:
  PIE-B1003 `binary_operator_not_admitted`; `sum(amount + amount)`: PIE-B1004
  `decimal_aggregate_range_proof_missing`).

### `median` and `quantile` aggregates

- `median(x)` and `quantile(x, q)` are the interpolated median and quantile
  (pandas `Series.median()` / `Series.quantile(q)`, default `linear`) of the
  non-None values of a direct `Int` or `Float` field, each taken as its Float
  image: a nullable `Float`, `None` for an empty or all-None input. `q` is a
  Float literal from 0.0 to 1.0 written in the call. Grouped and no-GROUP-BY
  queries; HAVING reads one through its select-item alias (`having m > 1.0`),
  and a direct call in HAVING is PIE-S2308, as for the other aggregates.
  PostgreSQL SQL is
  `PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY x)` (an `Int` argument cast to
  `double precision`; project: `CAST(x AS pg_catalog.float8)`, the `quantile`
  fraction `CAST('0.9' AS pg_catalog.float8)`), VERIFIED in projects for `Int`
  and carried through compiled bundles and live templates. New public JSON v2
  `ranges` syntax roles `aggregate_fraction` and `aggregate_within`; aggregate
  `spelling` `PERCENTILE_CONT`.
- **New refusals.**
  - MySQL single file: PIE-B1000 `MySQL SQL emission is not implemented for
    RelationIR: <name>. MySQL aggregate median is not supported: MySQL has no
    interpolated percentile; emit this relation for PostgreSQL` (`quantile` for
    a `quantile`). MySQL project: PIE-B1003 `quantile_not_admitted_on_target`,
    suggestion `Emit this median or quantile for PostgreSQL, or keep it in
    check/plan: MySQL has no interpolated percentile.` MySQL 8.4 has no
    `PERCENTILE_CONT`; both stay refused until a MySQL formulation is
    reviewed.
  - PostgreSQL project `Float` argument: PIE-B1004
    `float_aggregate_finite_result_proof_missing` (as `sum`/`avg` of a Float
    before). Other PostgreSQL project argument types: PIE-B1003
    `median_argument_outside_reviewed_int_domain` /
    `quantile_argument_outside_reviewed_int_domain` (unreachable after check,
    which refuses them with PIE-S2314).
  - PIE-S2104 at the fraction: `Invalid arguments for aggregate quantile: q 1.5
    is outside 0.0 to 1.0; write a fraction such as 0.9 for the 90th
    percentile` (the value as Python writes it); `Invalid arguments for
    aggregate quantile: q must be a Float literal from 0.0 to 1.0, written in
    the call, such as quantile(x, 0.9)` for an Int literal, a signed literal,
    a field, a `let` name or an expression, in single files and in projects
    (a LEGACY_FLAT project's GROUP BY relation reports no error of any
    aggregate call that reads a `let` name).
  - PIE-S2314 `Aggregate function median expects Int or Float field argument,
    got Decimal` (also `quantile`; also `Date`, `Timestamp`, `Text`, ...).
    A `Decimal` median is not available: PostgreSQL `percentile_cont` has no
    `numeric` form.
  - PIE-S2315 for an expression or `let` name argument, PIE-S2309 for a wrong
    argument count (`expects 2 arguments` for `quantile`, `1` for `median`),
    PIE-S2103 `Aggregate window functions are not implemented: median; window
    aggregates are sum, count, avg, min and max` with a `window`.
  - PIE-P1000 at `within`: `Unexpected 'within'. Pietto has no ordered-set
    `WITHIN GROUP`; write `quantile(x, q)` with q a Float literal from 0.0 to
    1.0, or `median(x)`.` (only after a `)`).
  - Over a JOIN that repeats rows both are PIE-S2381, as `sum` is.
- **Compatibility.** `def median` and `def quantile` are now PIE-S2398
  (``Def median has the name of a built-in function; a def cannot shadow
  one``) with the suggestion ``Rename this def: `median` is now the built-in
  interpolated median aggregate, and a call to median always means it.``
  (`interpolated quantile` and `quantile` for `def quantile`). A `constraint`
  or `derive` named `median` or `quantile` still checks; a call of that name,
  which was PIE-S2103 (``Unknown function: median; median is a constraint,
  which cannot be called; write a `def` instead``, `a derive` for a derive),
  now means the aggregate, as for `stddev`. A `relationship median(...)` or
  `relationship quantile(...)` template keeps its meaning: a WHERE, `let` or
  select-item call of it binds the relationship, and its PostgreSQL SQL is
  unchanged. A lowercase `median(...)` call (PIE-S2103 with the
  available-aggregates hint) and a `quantile(...)` call (PIE-S2103 `Unknown
  function: quantile`) are now the aggregates.
- PIE-S2103 hints (the lookup ignores letter case): the available-aggregates
  list is now ``the available aggregates are avg, count, count_distinct, max,
  median, min, quantile, stddev, string_agg and sum`` (also for `MEDIAN` and
  `QUANTILE` in another case); `percentile`, `percentile_approx`,
  `percentile_cont` and `approx_percentile` hint ``write `quantile(x, q)`, the
  interpolated quantile (pandas `Series.quantile`) with q a Float literal from
  0.0 to 1.0; `median(x)` is `quantile(x, 0.5)` ``; `percentile_disc` hints
  ``write `quantile(x, q)`, the interpolated quantile (pandas
  `Series.quantile`) with q a Float literal from 0.0 to 1.0; a discrete
  percentile that picks one value is not available``.
- **Formats.** A compiled `aggregate_value` record may name `median` (one
  input) or `quantile` (two inputs, the second its literal fraction); such
  bundles carry the Phase73 version marks `(7, 1, 7, 1)` of the aggregate
  windows subsection, and a reader of earlier marks refuses them.

### `compile_query` takes the project's whole emission contract

- `compile_query` now accepts an emission contract that also describes
  sources the query does not read, as `emit-sql --project` always has. It used
  to refuse it with `PIE-R1004` (`COMPILED_EXPORT_SOURCE_BINDING`), so a
  multi-source project needed one contract per query.
- The whole contract is still checked first, exactly as the command checks
  it. A misspelled or unknown selector, a repeated source, an invalid field or
  premise of any source, or premises that disagree (`PIE-B1005`), also for a
  source the query does not read, raise `CompileRejected` with the command's
  failure document byte for byte.
- The query is then compiled with its own contract: the contract's sources
  that it reads, in contract order, and every premise scoped to the
  statement, to one of those sources or to an expression over one, wherever
  the contract declares it (one declared in the entry of a source the query
  does not read moves to `environment`), written as canonical JSON (sorted
  keys, no whitespace). A premise scoped to a source the query does not read
  is left out, wherever it is declared.
- The query's `emission` is the artifact the command prints for that contract:
  the same SQL, with `request.contract` and `target.environment` naming only
  what the query reads. `emit-sql --project` output does not change.
- Compatibility: a bundle's `producer` and `pin` are computed from the query's
  canonical contract instead of the contract file's bytes. Changing, adding or
  removing how the contract describes a source the query does not read, or
  only reformatting the contract file, no longer changes the query's bundle or
  its records, so its bundles and saved jobs stay valid. A change to a source
  the query reads, or to a statement premise, still gives a new producer and
  pin. A bundle no longer holds anything of how the contract describes a
  source the query does not read. No diagnostic code, failure document, JSON
  shape, SQL text or bundle format changes.

### Top-level constants and `--set` (single files)

- A single file may declare top-level constants `name: Type = literal` for
  `Bool`, `Int`, `Float`, `Text`, `Date` and `Timestamp` (a `Date` or
  `Timestamp` is written as a Text literal and read as a value of its type;
  PostgreSQL SQL `DATE '...'` / `TIMESTAMP '...'`). Each read emits the
  literal; constants never change semantic facts.
- `--set NAME=VALUE` (repeatable) on single-file `check`, `emit-sql` and
  `explain` changes one constant for that run, read as a literal of the
  declared type; the SQL is byte-identical to the value written in the
  source. An initializer that is not one literal of its type keeps its own
  error under `--set`.
- **New refusal.** MySQL single-file emission refuses each table or query
  that reads a constant, directly, through a `def` or a relationship or by
  reading such a table or query, with PIE-B1000 `MySQL
  SQL emission is not implemented for RelationIR: <name>. MySQL has no
  top-level constants yet; emit with --dialect postgres`, until a
  two-database differential reviews them; the file's other relations still
  emit (no JSON `suggestion`, as for every single-file PIE-B1000).
- **New diagnostics.** `PIE-S2391` (ERROR, every check mode, single file,
  reported before other semantic analysis), exact messages:
  - at the type: ``A constant is `Bool`, `Int`, `Float`, `Text`, `Date` or
    `Timestamp`, without `| None`.``
  - at the value: ``Constant `NAME` takes one `TYPE` literal: FORM.`` with
    FORM ``` `True` or `False` ``` / ``an integer such as `10` or `-10` `` /
    ``a number with a decimal point such as `1.5` or `-1.5` `` /
    ``a Text literal such as `"EU"` `` /
    ``a Text literal `"YYYY-MM-DD"` from 1000-01-01 to 9999-12-31`` /
    ``a Text literal `"YYYY-MM-DD HH:MM:SS"`, with up to six fractional
    digits, from 1000-01-01 00:00:00 to 9999-12-31 23:59:59.499999``
  - at the constant: ``Constant `NAME` is also declared as another name in
    this file; give the constant a name of its own.``
  - at the constant, for the name of a built-in scalar, aggregate or window
    function, `generate_series`, `concat`, `Float` or `Text`: ``Constant
    `NAME` has the name of a built-in function; give the constant a name of
    its own.``
  - at a read in a source's connector (what a source reads is part of its
    identity, which a `--set` value never changes): ``Constant `NAME` is no
    source connector argument; a source names what it reads with a literal
    written there.``
  - at a read that is a whole GROUP BY or ORDER BY key (relation, window or
    aggregate): ``Constant `NAME` is no GROUP BY or ORDER BY key; a key reads
    a field or an output.`` A key computed from a constant (`-n`, a `let`
    name bound to it) is checked as that key written with the literal:
    PIE-S2380 in a relation's ORDER BY, PIE-S2321 under GROUP BY.
  - at an unnamed SELECT item: ``A SELECT item that reads only constant
    `NAME` needs its own name, such as `value = NAME`.``
- `PIE-S2001` also reports a repeated constant name at the later constant:
  `Duplicate symbol name in constant namespace: NAME`.
- `PIE-S2392` (ERROR, pre-admission, at the constant) in a project:
  EXPLICIT_MODULES ``Top-level constants are available only in single files.
  In a project, give the query a header parameter instead, such as `query
  q(cutoff: Int):`.``; LEGACY_FLAT ``Top-level constants are available only
  in single files. A project takes such a value as a query header parameter,
  which needs `schema_version = 2` in pietto.toml.`` (`suggestion` = the
  second sentence). `explain --project` on a PACKAGE_ROOT project runs no
  semantic admission, for constants as for everything else, and `check
  --project` refuses such a project before parsing, so no PACKAGE_ROOT
  command reports PIE-S2392.
- **Changed diagnostics (compatibility).**
  - `PIE-S2346` in single-file analysis only: the message gains, and
    `suggestion` carries, ``In a single file, write the value as a top-level
    constant, such as `cutoff: Date = "2024-01-31"`, and change it with
    `--set cutoff=2024-02-29`.`` Project messages are unchanged.
  - `PIE-P1000` at a top-level line: `let ...` gains ``Write a top-level
    constant as `name: Type = literal`, without `let`.``; `const NAME ...`
    gains the same with `` `const` ``; `NAME = ...` gains ``A top-level
    constant names its type: `name: Type = literal`.`` (position and the
    leading `Unexpected ...; expected a declaration, end of file or end of
    line.` unchanged). Parsing and error recovery are otherwise unchanged:
    only a top-level line that starts with `name:` and holds an `=` outside
    parentheses is read as a constant, so every other line, `name:` and
    `name: Type` included, reports what it reported before, and an
    unexpected top-level line still ends the parse.
  - The CLI usage lines of `check`, `explain` and `emit-sql` list
    `[--set NAME=VALUE]`.
- **CLI usage errors** (exit 2):
  - `--set NAME is given more than once` (check, emit-sql, explain; text and
    JSON; reported before the file is read, and its JSON result names the
    input `path`);
  - `--set NAME: no top-level constant NAME is declared` (after the file
    parses);
  - `--set NAME: constant NAME has type TYPE; write VALUE-FORM` with
    VALUE-FORM `True or False` / `an integer such as 10 or -10` / `a number
    with a decimal point such as 1.5 or -1.5` / `UTF-8 text` / `YYYY-MM-DD
    from 1000-01-01 to 9999-12-31` / `YYYY-MM-DD HH:MM:SS, with up to six
    fractional digits, from 1000-01-01 00:00:00 to 9999-12-31
    23:59:59.499999`;
  - `--set and --project are mutually exclusive` (check, explain, and
    `emit-sql --project`, in its text or JSON contract);
  - `argument --set: expected NAME=VALUE` (argparse).
  - `migrate` and `fmt` do not take `--set` (argparse `unrecognized
    arguments`, as for any option a command lacks, such as `fmt --dialect`).

### Typed project query parameters

- In an EXPLICIT_MODULES project an entry query may declare `Decimal(p, s)`
  (two integer literals, `1 <= p <= 65`, `0 <= s <= min(p, 30)`), `Date`,
  `Timestamp` and `UUID` parameters, with `| None` as before. PostgreSQL
  project SQL reads one as `CAST($n AS pg_catalog.numeric(p,s))`,
  `CAST($n AS pg_catalog.date)`, `CAST($n AS pg_catalog.timestamp)` or
  `CAST($n AS pg_catalog.uuid)`; these reads add no binding obligation.
  `execute`, `save`, `save_recoverable` and `relay_live` take
  `decimal.Decimal` (finite, exactly within `numeric(p, s)`, never rounded),
  `datetime.date` (not a `datetime`) from `1000-01-01`, a naive
  `datetime.datetime` from `1000-01-01 00:00:00` to `9999-12-31
  23:59:59.499999`, and `uuid.UUID`; `None` only for a nullable parameter,
  sent as a typed NULL. The value travels as its canonical text (Decimal
  without exponent or trailing zero, `-0` as `0`; ISO date; ISO timestamp
  with a space and six fractional digits; lower-case UUID) on `postgres_rows`
  and `postgres_adbc`. `open_saved_read`, `release_saved_read`,
  `publish_saved_generation`, `verified_export` and `recover` restate such a
  value by equal value and the same Python type (`Decimal("12.5")` restates
  `Decimal("12.50")`).
- **Diagnostics and refusals** (exact):
  - PIE-S2353, at the parameter, text changed: `Query parameter type must be
    Bool, Int, Float, Text, Decimal(p, s), Date, Timestamp or UUID.` (was
    `Query parameter type must be Bool, Int, Float or Text.`), for any other
    type or a type argument on a type other than `Decimal`.
  - PIE-S2353, at the parameter, new message: `A Decimal query parameter is
    declared Decimal(p, s) with integer literals 1 <= p <= 65 and 0 <= s <=
    min(p, 30).`, for a `Decimal` without arguments, with one, named or
    non-literal arguments, or outside the bounds (a scale above 30, such as
    `Decimal(40, 35)`, included).
  - New refusal: PIE-B1003 with the new detail
    `query_parameter_type_not_admitted_on_target`, reason `UNSUPPORTED_RULE`,
    subject `{"kind": "selected_plan", "position": 0}`, at each such
    declaration in header order, read or not, and the suggestion `Keep this
    declaration in check/plan or select an artifact using the forms reviewed
    for the requested target. Do not relabel the target or source carrier to
    bypass this refusal.`: MySQL project emission (`emit-sql --project`;
    `compile_query` gets the BLOCKED document) of a query that declares a
    `Decimal(p, s)`, `Date`, `Timestamp` or `UUID` parameter, until a later
    MySQL catch-up.
  - PIE-R1006 `BINDING_PARAMETER:<ordinal>:<Decimal|Date|Timestamp|UUID>`
    (existing detail, new tags; a `Date` before `1000-01-01` included).
  - PIE-R1004 `QUERY_NOT_EXECUTABLE`, detail `MEANING_OUTPUT`, from `execute`
    (result preparation) and `save` (binding description), for a `Timestamp`
    or `UUID` parameter selected as an output, which has no source meaning;
    `emit-sql` still reports VERIFIED, and `compile_query`, `export_bundle`,
    `load_bundle` and binding succeed.
- **Compatibility.**
  - Programs that were PIE-S2353 because a parameter was `Decimal(p, s)`,
    `Date`, `Timestamp` or `UUID` now check. A plain `Decimal`, `Decimal(p)`
    and every other type stay PIE-S2353 with the new text.
  - Compiled bundles: the `parameter` record gains a sixth field `decimal`
    (null, or `[precision, scale]`), under the Phase73 version marks
    `(7, 1, 7, 1)` of the aggregate windows subsection; a bundle of an earlier
    release is refused (`COMPILED_COMPATIBILITY`, and `COMPILED_FIELDS` on its
    parameter records) and never migrated; export it again from the project.
  - Saved jobs keep their formats. The binding vector stays
    `pietto.binding-vector.v2` (new values `[tag, canonical text]` only); the
    generation description keeps interface `parameter` 1 and its entry shape
    (address, label, tag, nullable, reads). A job whose bundle predates the
    version marks is refused through its bundle (`JOB_BUNDLE`), not migrated.
  - `pietto.sql-emission.v2` gains no key: `parameters[j].tag` and
    `parameter_uses[i].physical_type` take new values on PostgreSQL only
    (`pg_numeric`, `pg_date`, `pg_timestamp`, `pg_uuid`).
  - A result contract document's parameter expression `type_name` may now be
    `Decimal`, `Date`, `Timestamp` or `UUID`.
  - `CompiledQuery.parameters` stays `(name, tag, nullable)`; a Decimal one
    reads `('floor', 'Decimal', False)` (precision and scale are in the
    source and the anchor cast).

### Window keys that name a computed `let`

- A window PARTITION BY or ORDER BY key may name a `let` computed from input
  fields: operators, comparisons, conditional expressions, casts and scalar or
  `def` calls (`let off_year = review_year != 2024`, `let band =
  size_band(level)`, then `window(partition by group_id order by off_year,
  band, id)`), in a selected, a named and a QUALIFY window of a relation
  without GROUP BY whose input is no JOIN row, an aggregate window included,
  in single files and EXPLICIT_MODULES projects alike. Single files write the
  value in the window specification; projects compute it in the stage before
  the window (emission on both targets; PostgreSQL compiled bundles and live
  templates). A two-database differential (PostgreSQL 18.6, MySQL 8.4.12) of
  single-file and project keys matched the expected rows on both databases.
  A single-file MySQL key that names a computed Text `let` is refused
  (below).
- **Changed (compatibility).**
  - Programs that `check` refused with `PIE-S2103` (`window partition
    expression must be a direct field` / `window order expression must be a
    direct field`) because a key named such a computed `let`, such as
    `let k = lower(t)` then `window(order by k)`, are now accepted.
  - A still-refused window whose first refusal was such a key now reports its
    next refusal, at the same window call, instead of that PIE-S2103. With
    `let k = amount + 1`: `rank() window(order by k rows between 1 preceding
    and current row)` reports `PIE-S2104 error: Invalid window frame for
    function rank: explicit ROWS frame is not allowed`; with also
    `let v = amount * 2`, `lag(v) window(order by k)` reports `PIE-S2104
    error: Invalid arguments for function lag: value must be a direct field or
    Bool, Text, Int, Float, or NULL literal, not the `let` name v`.
  - A key that names a computed `let` whose value has an error of its own,
    such as `let k = lower(missing)` then `window(order by k)`, reports
    `PIE-S2102 error: Unknown field: k` at the key beside the binding's own
    error (as a `let` bound to an erroneous name already did), instead of
    `PIE-S2103 ... window order expression must be a direct field` at the
    window call.
  - The `PIE-S2103` message for a computed expression written as a PARTITION
    BY or ORDER BY key in the window specification itself, where a `let` key
    is admitted (no GROUP BY, input no JOIN row) and a `let` could compute it
    (it reads an input field), now ends with ``; compute it in a `let` and
    name that `let` in the window``, for example `PIE-S2103 error: Unsupported
    window computation for function row_number: window order expression must
    be a direct field; compute it in a `let` and name that `let` in the
    window`. Code, position and order are unchanged; the message is unchanged
    where the hint does not apply (a grouped window, a JOIN row, a value that
    reads no field such as `order by 1 + 2`).
- **Still refused** (unchanged unless noted):
  - a `def` call written in a key, `window(order by shifted(score))`:
    `PIE-S2397` `A def call is not available in a window computation:
    shifted`;
  - a `let` key whose value reads no input field, `let k = 3`, `let k = -3`,
    `let k = 1 + 2`, `let k = Text(3)`: `PIE-S2103` `... window order
    expression must be a direct field`;
  - a computed `let` key of a grouped window, or of a window over JOIN inputs
    (single file and project): `PIE-S2103`;
  - a computed `let` key that reads a query parameter: `PIE-S2355` `Query
    parameters are not available in this position.`;
  - a computed `let` as a `lag`/`lead`/`first_value`/`last_value`/`nth_value`
    value or default: `PIE-S2104`;
  - a window value as an operand of an expression, `row_number()
    window(order by id) + 1`, `1 if c else dense_rank() window(...)`:
    `PIE-P1000` (`Unexpected '+'; expected end of line.` / `Unexpected
    'window'; expected ',' or end of line. A window call is a whole `select:`
    item on a line of its own.`);
  - new refusal of a newly admitted form: single-file MySQL, a key that names
    a computed Text `let`, `let s = lower(category)`, `let s = "A" if id > 2
    else "a"`: `PIE-B1000 error: MySQL SQL emission is not implemented for
    RelationIR: NAME. MySQL does not support a computed Text window key` at
    the relation (project MySQL emits such a key with the binary collation).

### `now()`: the UTC time of the running query

- `now()` takes no argument and is a `Timestamp` that is never None: the
  start of the running SQL statement in UTC, without a time zone, with
  microseconds (Python `datetime.now(timezone.utc).replace(tzinfo=None)`, not
  the local `datetime.now()`). Every `now()` of one statement is one value;
  each new execution reads a new one; the session time zone does not change
  it. `date_of(now())` is the UTC date. It stands in SELECT items and WHERE
  (also a WHERE between JOINs, an `any(...)` there and a `def` call argument
  there), in single files and projects.
- PostgreSQL SQL is `(statement_timestamp() AT TIME ZONE 'UTC')`, single file
  and project (VERIFIED, compiled bundle and live template). Emitted SQL,
  compiled bundles and goldens hold the expression, never a value; saved
  results keep the value of the run that saved them, so replay and verified
  export show it.
- **New refusal on MySQL**: MySQL emission refuses `now()`, single file with
  PIE-B1000 (`MySQL SQL emission is not implemented for RelationIR: NAME.
  Unsupported MySQL function call: now`), project with PIE-B1003
  (`scalar_call_signature_not_admitted`).
- **New refusal PIE-S2387** (ERROR at the call, every mode, before `def`
  inlining), by position:
  - a `let` value or SELECT item that GROUP BY of its body names: ``now()`
    cannot be in a GROUP BY key: every row has the same `now()`, so it never
    splits a group``;
  - an ORDER BY key, or a `let` value or SELECT item that ORDER BY of its body
    names: ``now()` cannot be in an ORDER BY key: every row has the same
    `now()`; order by a field``;
  - a JOIN `on`: ``now()` cannot be in a JOIN condition; compare it in WHERE``;
  - a field `derive`: ``now()` cannot be in a field derive, which reads one
    stored row; select `now()` in a query``;
  - every other position (another `let`, HAVING, QUALIFY, a window's
    arguments or keys, a named window, LIMIT, a `def`, `constraint` or
    `derive` body, a check, an ensure, a VALUES row, a top-level constant's
    value): ``now()` is available only in a SELECT item or a WHERE
    comparison``.
  - Not refused: a key that reads a column another relation selected from
    `now()`, and a call with arguments, `now(x)`, which is not the builtin.
- PIE-S2104: `now(x)` is `Invalid arguments for function now: expected 0,
  got N`.
- **New execution refusals (PIE-R1004)**, before any workspace or sink work:
  `relay_live` of a query that reads `now()` is `STATEMENT_SNAPSHOT_ENTRY`;
  `save_recoverable` and `recover` (R2) are `PUBLIC_R2_STATEMENT_SNAPSHOT`.
  `execute()` and `save()` accept it.
- PIE-S2103 hints (the lookup ignores letter case): `current_timestamp`,
  `utcnow`, `utc_now`, `datetime.now` and `datetime.utcnow` add ``; write
  `now()`, the UTC time when the query runs``; `today` and `date.today` add
  ``; write `date_of(now())`, the UTC date when the query runs``; `now` in a
  letter case other than lowercase adds ``; write `now()` in lowercase``.
- **Compatibility.** A call `now()` that was PIE-S2103 `Unknown function: now`
  now means the builtin. `def now` is now PIE-S2398 (``Def now has the name of
  a built-in function; a def cannot shadow one``) with the suggestion
  ``Rename this def: `now` has become the built-in UTC time of the running
  query, and a call to now always means it.``. A file's own
  `relationship now(row: Row)` keeps its meaning: `now(o)`, with an argument,
  is its call in every position, as before.
- **Formats.** Project JSON v2 and the emission observation: the closed
  `scalar_call` operator vocabulary gains `now` (no operands), whose `syntax`
  ranges are `scalar_call_open` (`(statement_timestamp() AT TIME ZONE 'UTC'`)
  and `scalar_call_close` (`)`); its result realization is `Timestamp`,
  `pg_timestamp` with 6 fractional digits, not nullable. A strict reader of
  that vocabulary must accept it. The compiled description's closed operator
  set gains `("scalar_call", "now")` with zero operands, under the Phase73
  version marks `(7, 1, 7, 1)` of the aggregate windows subsection; a reader
  of earlier marks refuses such a bundle.

### The rows of each group

- The language guide and the style page describe the per-group detail route:
  group in one query, read it with `from` in another, and collect a let that
  captures the grouped query, reads the same input and matches each key with
  `same_value`, so a group whose key is None gets its own rows and each
  group's list has as many rows as its `count()`. The guide also says what
  the other spellings give: with `==` the None group's list is `[]`; a let
  that reads the unfiltered input beside a filtered grouped query lists every
  row whose key matches; a `Float` key keeps each member's own value
  (`-0.0` and `0.0` group together); a `Bool` key cannot be matched yet, as
  `emit-sql --project` refuses a `Bool` `same_value` or `==` (PIE-B1003
  `comparison_type_pair_not_admitted`). The route needs no new syntax: it was
  already accepted, and PostgreSQL project SQL writes it as one LEFT JOIN
  LATERAL aggregate correlated with `IS NOT DISTINCT FROM`. MySQL still
  reports PIE-B1003 for its Collect read.
- PIE-S2803, for a Collect read in a grouped SELECT (a GROUP BY or an
  aggregate in that SELECT), now suggests that route. Old suggestion:
  ``Group the rows in another table or query, read it with `from` here, and
  collect a let that captures it.`` New suggestion: ``Group the rows in
  another table or query g, read it here with `from g`, and collect a let
  that captures g, reads the same input as g and matches each group key, if
  any, with `where same_value(input.k, g.k)`, so a None key keeps its
  rows.`` Compatibility: only the suggestion text changes (the JSON
  `suggestion`; text output prints no suggestion, as before). The code,
  severity, message, location, count and order of PIE-S2803 are unchanged,
  and so are its other two suggestions (in a relation let; a read that is no
  relation let). A tool that matches the whole suggestion must accept the
  new text.
- No new diagnostic, refusal or compatibility break. A let that matches a
  nested field (the output of a `collect`) to a captured group key stays
  PIE-S2805 at that field, with `same_value` as with `==`
  (``Nested relation field parent.xs cannot be read in WHERE: a collected
  relation has no comparison, ordering, grouping or scalar value.``).

### Lists of one row: `len`, `sum` and `any` (PostgreSQL projects)

- In a `schema_version = 2` project, list operations of one row over its
  collected field `c.xs`: `len(c.xs)`, `sum(o.f for o in c.xs)`,
  `sum(o.f for o in c.xs if TEST)`, `sum(1 for o in c.xs if TEST)` and
  `any(TEST for o in c.xs)`, in a SELECT item, a row `let` or the WHERE of a
  table or query without JOIN, GROUP BY, an aggregate, DISTINCT, a window or
  QUALIFY. Types `Int`, `Int`, `Int`, `Int`, `Bool`; None exactly when the
  row's list may be missing (after an outer JOIN); `[]` gives 0 / 0 / False;
  a None element value or test adds no value and no match; a list sum past
  64 bits is an error (SQLSTATE 22003), never a wrap. The summed field is an
  `Int`.
- PostgreSQL emits, compiles and bundles them (`emit-sql --project`,
  `compile_query`, `export_bundle`/`load_bundle`, both literal policies):
  `len` is the list's count column; `sum` is `CASE WHEN <count> IS NULL THEN
  NULL ELSE COALESCE((SELECT CAST(SUM(CAST(<body> AS pg_catalog.int8)) AS
  pg_catalog.int8) FROM ROWS FROM (pg_catalog.unnest(<array>), ...) AS "l"
  ("c0", ...) [WHERE <test>]), 0) END`; `any` is `CASE WHEN <count> IS NULL
  THEN NULL ELSE EXISTS (SELECT 1 FROM ROWS FROM (...) AS "l" (...) WHERE
  <test>) END`. Literals inside a list operation are never bound.
- A JOIN query that selects a collected field (`xs = p.xs`) now emits as an
  earlier relation of another query (it emitted only as the selected query;
  as an earlier relation it was PIE-B1004 `expression_logical_type_evidence_missing`
  at that item), so a later query reads the list, with a missing list for a
  LEFT JOIN row without a match.
- MySQL: unchanged; the Collect a list operation reads stays PIE-B1003
  `collect_not_admitted_on_target` (Phase77).

New refusals (programs that were PIE-P1000 in 0.1.9). All are PIE-S2334 at
the call unless noted, before semantic analysis, the hint after `; ` also the
JSON `suggestion` (an EXPLICIT_MODULES project, a generator over `c.xs`):

| Written | Diagnostic |
|---|---|
| `len(o for o in c.xs)` | ``len takes no generator; count the list with `len(c.xs)` `` |
| `count(... for o in c.xs)` | ``count takes no generator; count the list with `len(c.xs)` ``; with `if`: ``count takes no generator; count the matching elements with `sum(1 for o in c.xs if ...)` `` |
| `max`, `min`, `avg`, `stddev`, `count_distinct`, `string_agg` | ``max takes no generator; a list max is not available; `sum` and `any` take a list generator`` |
| another known callee | ``A generator is only the argument of sum or any; `sum` and `any` take a list generator`` |
| an unknown callee | PIE-S2103 as for any unknown function |
| `any(p for o in c.xs if q)` | ``any takes its test in the body; write `any(p and q for o in c.xs)` `` (`True` body: ``write `any(q for o in c.xs)` ``) |
| `sum(1 for o in c.xs)` | ``sum(1 for o in c.xs) counts every element; write `len(c.xs)` `` |
| `sum(BODY for o in c.xs ...)`, BODY neither `1` nor `o.f` | PIE-S2315 `sum of a list adds 1 or one field of o; expression bodies are not supported yet` (conditional body: ``; filter with `if` after the source: `sum(o.f for o in c.xs if ...)` ``; bare field: ``; read the element as `o.amount` ``) |
| `sum(... for o in xs ...)`, `xs` a name of no relation, `let` or `group` | PIE-S2301 at the source: ``Unknown or unavailable generator source: xs; a row's collected list is read through its row: `for o in c.xs` `` (`c` = the FROM name; in a body with JOIN inputs `c` as written) |
| a read in the body or test other than `o.f` | at the read: ``Generator reads id outside its member; read the element's fields as `o.f` and the row's values outside the generator`` (qualified: ``Generator reads parent.id outside its member; ...`` with the same hint), the member-read texts of the conditional count otherwise |

During the project checks (at the call unless noted, no suggestion unless shown):

| Written | Diagnostic |
|---|---|
| `sum(o.paid for o in c.xs)` | PIE-S2314 ``sum of a list adds an Int field of o, got Bool; count with `sum(1 for o in c.xs if o.paid)` `` (suggestion = the hint) |
| `sum(o.price for o in c.xs)` (not Int, not Bool) | PIE-S2314 `sum of a list adds an Int field of o, got Decimal; a list sum adds Int values` (suggestion `a list sum adds Int values`) |
| `any(o.amount for o in c.xs)` | PIE-S2202 `Expected Bool expression in any test` (at the body) |
| `sum(1 for o in c.xs if o.amount)` | PIE-S2202 `Expected Bool expression in generator test` (at the test) |
| `sum(o.nosuch for o in c.xs)` | PIE-S2102 `Unknown field: o.nosuch` (at the read) |
| `sum(o.f for o in c.nosuch)` | PIE-S2102 `Unknown field: c.nosuch` (at the source) |
| `sum(o.f for o in c.id)`, `id` a scalar field | PIE-S2334 ``Generator source c.id is not a collected list; a generator over a row's field reads a field that a `collect` SELECT item outputs`` |
| `len(xs)`, `xs` a collected field read bare, where `len(c.xs)` is admitted | PIE-S2334 at `xs` ``len reads a row's collected list through its row; write `len(c.xs)` `` (suggestion = the hint; `c` = the FROM binding) |
| a list operation in ORDER BY, a relation let, or a table or query with JOIN, GROUP BY, an aggregate, DISTINCT, a window or QUALIFY | PIE-S2805 at the field, today's message (ORDER BY: `... cannot be read in ORDER BY: ...`), suggestion below |

A single file refuses a generator over `c.xs` at the source with PIE-S2334
``A generator over c.xs reads a row's collected list, which only a project
collects; `sum` and `any` read a collected list in a project whose
pietto.toml sets `schema_version = 2` ``; a `schema_version = 1` project
refuses it as every generator (see the conditional count and sum above).

Changed diagnostics (programs refused in 0.1.9 too):

| Program | 0.1.9 | Now |
|---|---|---|
| `n = len(c.xs)` in a SELECT item, a row `let` or the WHERE of a table or query without JOIN, GROUP BY, aggregate, DISTINCT, window or QUALIFY | PIE-S2805 `Nested relation field c.xs cannot be read in ...: ...` | accepted (`Int`); PostgreSQL emits |
| `len(xs)` (bare collected field) there | PIE-S2805 | PIE-S2334 ``len reads a row's collected list through its row; write `len(c.xs)` `` |
| `len(c.xs)` in a table or query with an INNER, LEFT or CROSS JOIN and no GROUP BY, aggregate, DISTINCT, window or QUALIFY | PIE-S2805, suggestion `Filter, order or group the collected rows inside the let that is collected.` | same code, message, span and order; suggestion ``A table or query with a JOIN reads no list yet: select the list as it is here, as in `xs = c.xs`, and read it with `len`, `sum` or `any` in a later table or query that reads it with `from`.`` (a bare `xs`: without `, as in ...,`) |
| `len(c.xs)` anywhere else (RIGHT/FULL JOIN query, grouped or aggregate body, relation let, ORDER BY, ...) | PIE-S2805, suggestion `Filter, order or group the collected rows inside the let that is collected.` | same code, message, span and order; suggestion ``Read the list with `len`, `sum` or `any` in a SELECT item, a row `let` or the WHERE of a table or query without JOIN, GROUP BY, an aggregate, DISTINCT, a window or QUALIFY, and order or group by that output in a later table or query that reads it with `from`.`` |
| `count(c.xs)` | PIE-S2805, the same old suggestion | same code, message, span and order; suggestion ``Count the list with `len(c.xs)`.`` |
| `count(xs)` (bare collected field) | PIE-S2805, the same old suggestion | same code, message, span and order; suggestion ``Count the list with `len(c.xs)`.``, `c` the FROM row; in a table or query with JOIN inputs, whose row the suggestion cannot name, the `Read the list ...` suggestion above |
| `len([o for o in c.xs])`, and a `[` right after `sum(`, `any(` or `count(` | PIE-P1000 `Unexpected '['; expected an expression or ')'.` (or the parser's text there) | same code, position and text, followed by `` Write the generator without brackets, as in `sum(1 for o in c.xs if ...)`; count a row's list with `len(c.xs)`.`` (message only; PIE-P1000 has no JSON `suggestion`) |
| a JOIN query selecting a collected field, emitted as an earlier relation of the selected query | PIE-B1004 `expression_logical_type_evidence_missing` at that item | VERIFIED (the list's count and arrays carried, as when it is the selected query) |

Compatibility:

- No program accepted by 0.1.9 changes meaning, diagnostics or SQL bytes
  (the JOIN carry above only adds statements that were BLOCKED).
- No new builtin name (`len`, `sum` and `any` exist), so no user `def`
  becomes PIE-S2398.
- **Formats.** The compiled description gains the operation operator
  `("list", "len" | "sum" | "any")` (operands: a `value` read of a collection
  port, then the body and the test; arity 1, 2 or 3, and 2), the `read` role
  `element` (a port of a Collect's let, through that Collect's
  `expression_block_use`, only inside a list operation over that Collect) and
  the literal-site ancestry kind `generator`, under the Phase73 version marks
  `(7, 1, 7, 1)` of the aggregate windows subsection; a reader of earlier
  marks refuses such a bundle. Project JSON v2 (`emit-sql --project`) gains
  the `computed_origin` kind `list_operation`, the generated requirement and
  subject kind `list_operation` (rule R05; a list `sum`, the count
  `sum(1 for o in c.xs if TEST)` included, carries
  `target_checked_signed64_narrowing`: a total past signed 64 bits fails with
  SQLSTATE 22003), the `expression_range` role `list_operation`, the
  `identifier` roles `list_scope`, `list_count`, `list_array`,
  `list_rows_scope` and `list_column`, and the `syntax` roles `list_open`,
  `list_present`, `list_sum_open`, `list_sum_cast`, `list_any_open`,
  `list_rows_open`, `list_function`, `list_function_close`, `list_alias`,
  `list_columns_open`, `list_columns_close`, `list_where` and `list_close`
  ([project JSON v2](spec/project-cli-json-v2.md)). A consumer that closes
  these sets refuses such a document.
- A fail-closed emission detail PIE-B1003 `list_operation_not_admitted_on_target`
  stays for a non-PostgreSQL target that would reach a list operation (none
  does today: the Collect it reads is refused first); it is in the
  Collect/Unnest suggestion group.

### Conditional count and sum in projects

- A `schema_version = 2` project now checks and emits the conditional count
  and sum of a group as a single file does: `sum(1 for o in group if o.paid)`
  and `sum(o.amount for o in group if o.paid)`, a whole aliased SELECT item of
  a grouped query or of a query with aggregates and no GROUP BY, without JOIN
  inputs. Both are a non-null `Int`, 0 when no row matches; `having` and
  `order by` read the output name. The refused generator variants, their
  codes, texts and hints are the single file's (the gate is shared), except
  that outside a group (a body with no GROUP BY and a non-aggregate SELECT
  item) an unknown single-name source suggests the row's list, as in
  [lists of one row](#lists-of-one-row-len-sum-and-any-postgresql-projects);
  an `any(... for o in group)` keeps the project's own text and span and
  gains the single file's suggestion (below).
- PostgreSQL project SQL writes `COUNT(CASE WHEN <test> THEN 1 END)` and
  `COALESCE(CAST(SUM(CASE WHEN <test> THEN CAST(<f> AS pg_catalog.int8) END)
  AS pg_catalog.int8), 0)`; each result is a non-null `pg_int8`, and the sum's
  R13 requirement carries `target_checked_signed64_narrowing` (a sum outside
  signed 64 bits fails with SQLSTATE 22003). Compiled bundles and live
  templates carry both unchanged.
- **Formats.** Project JSON v2 (`emit-sql --project`) gains the aggregate
  column `function` values `filtered_count` and `filtered_sum` (`spelling`
  `COUNT` and `SUM`; a sum's test in `delimiter`) and the additive `ranges`
  syntax roles `aggregate_filter_open` (`CASE WHEN `), `aggregate_filter_then`
  (` THEN `), `aggregate_filter_one` (`1`), `aggregate_filter_close` (` END`),
  `aggregate_zero_open` (`COALESCE(`) and `aggregate_zero_close` (`, 0)`). A
  consumer that closes these sets refuses such a document. A compiled
  `aggregate_value` record may name `filtered_count` (one argument, the test)
  or `filtered_sum` (a direct field read, then the test), under the Phase73
  version marks `(7, 1, 7, 1)` of the aggregate windows subsection; a reader
  of earlier marks refuses such a bundle.

New refusals:

- MySQL project, conditional count: PIE-B1003
  `conditional_count_not_admitted_on_target` at its select item, suggestion
  `MySQL has no conditional count yet; emit with --dialect postgres.`
- MySQL project, conditional sum: PIE-B1004
  `sum_int_aggregate_range_proof_missing` at its select item, as `sum(Int)`.
- A query header parameter read in a project generator's test or body:
  PIE-S2355 `Query parameters are not available in this position.` at the
  read, as in every other aggregate argument (no suggestion).
- A project conditional count or sum whose test reads no field (`if True`,
  `if not False`): checked, but emission is BLOCKED on either target with
  PIE-B1003 `conditional_test_reads_no_field` at its select item, suggestion
  ``Test a field of the member, such as `if o.paid`: a test that reads no
  field is the same for every row.`` (a single file emits
  `COUNT(CASE WHEN TRUE THEN 1 END)`).

Changed diagnostics (programs refused in 0.1.9 too; no accepted program
changes):

| Program | 0.1.9 | Now |
| --- | --- | --- |
| a `schema_version = 2` project with `sum(1 for o in group if TEST)` or `sum(o.f for o in group if TEST)` as a whole aliased SELECT item without JOIN inputs | PIE-P1000 | accepted |
| a `schema_version = 2` project with any other generator call | PIE-P1000 | the single file's diagnostic for the same call (for example PIE-S2334 ``count takes no generator; ...``, PIE-S2314, PIE-S2202 `Expected Bool expression in generator test`, PIE-S2105 at an operator of the test such as `o.paid == None`) |
| a `schema_version = 1` project with any generator call | PIE-P1000 | PIE-S2334 ``sum(... for ...): a schema_version = 1 project has no generator in the current syntax; set schema_version = 2 to check it`` (the callee's name in place of `sum`; the hint is the JSON `suggestion`) |
| a `schema_version = 2` project with `any(... for o in group)` where no relation or `let` is named `group` | PIE-S2301 `Unknown relation: group` at the `any(...)` (a WHERE or SELECT), or PIE-S2334 `ANY is not supported in this context` (a `having`), suggestion null | in a SELECT item the test of a group; elsewhere the same code, text, span and order with the JSON `suggestion` of "The test of a group: `any` and `all` over `group`" below |

### A worked example

- A new page, [a worked example](worked-example.md), builds a monthly report
  for an invented bike-share with the forms of the style page: one single file
  (top-level constants and `--set`, `now()`, `lpad`, `add_months`,
  `max(a, b)`, conditional `sum(1 for r in group if ...)`, `median`,
  `quantile`, a window keyed by a computed `let`, and the two-level route over
  a JOIN that repeats rows) and one `schema_version = 2` project module (`Date`
  query parameters, aggregate windows, the rows of each group with
  `same_value`, and grouping by a collected list). The style page links to it
  and gains a section on aggregate windows.
- `tests/test_repo_docs_examples.py` checks the page's `pietto` blocks as it
  checks those of `README.md`, `docs/language.md` and `docs/style.md`, and
  runs the page's commands as it shows them: the single-file `check` and
  PostgreSQL `emit-sql` (also with `--set`), `check --project`, and
  `emit-sql --project --all` with a `contract.json` in the project.
- A third part, "Two modules", declares a `def` and a relationship in one
  module of a project, uses them in another and passes a grouped query's
  rows to the relationship. The test also compiles each of its queries with
  `compile_query` on PostgreSQL and, over `mysql.table` sources, on MySQL,
  and checks that the SQL is that of the same declarations in one module and
  that the live template and a loaded bundle bind to it.
- No new diagnostic, refusal or compatibility change.

### Importing a def or relationship from another module

- In an EXPLICIT_MODULES project, `export def pos` and
  `from "models/a.pietto" import def pos` (or `def pos as p`), and likewise
  `export relationship OrderCustomer` and `import relationship OrderCustomer`
  (or `relationship OrderCustomer as oc`), in the bare and the parenthesized
  list; re-exports chain as for other kinds.
- A def is checked once, in its module, where an alias in its signature means
  what it means there (never the importer's alias); a call is inlined and
  checked at the call, as a call of a local def is.
- A relationship is checked once, in its module; a call in the importer, in
  `on`, WHERE, SELECT and `any(...)`, binds its rows by the declaring
  module's parameter shapes. The importer need not import those shapes by
  name.
- The SQL of both is byte-equal to the same def or relationship declared
  locally (PostgreSQL and MySQL emission, compiled bundle and live template).
  A `concat` call in an imported body stays the built-in also in an importer
  that declares a callable `concat` (def, constraint, derive or
  relationship).
- **Refusals that become acceptances.** An `export def f` or import item
  `def f` was PIE-P1000 at the `def`, and an `export relationship R` or
  import item `relationship R` at the `relationship`: `Unexpected 'def'.`
  (`Unexpected 'relationship'.`) as the first item of a bare list or a later
  item of a parenthesized one, `Missing 'type', 'enum', 'shape', 'source',
  'table' or 'query' before 'def'.` (`... before 'relationship'.`) as the
  first item of a parenthesized list or a later item of a bare one. In an
  EXPLICIT_MODULES project each is now accepted and gets its binding result.
- **Changed messages** (forms already refused; same code and location unless
  stated):
  - PIE-P1000 kind list: `Missing 'type', 'enum', 'shape', 'source', 'table'
    or 'query' before 'X'.` is now `Missing 'type', 'enum', 'shape',
    'source', 'table', 'query', 'def' or 'relationship' before 'X'.` (for
    example `export (pos)`).
  - PIE-P1000 at a `*` item (`from "a.pietto" import *`, `export *`):
    ``Unexpected '*'. `*` is not supported; write `count()` or list the
    fields.`` is now `Unexpected '*'. Name each item.`
  - PIE-P1000 for a `def *` item: was at the `def`, with the texts of a `def
    f` item above; now at the `*`: `Unexpected '*'; expected a name. Name
    each item.`
  - PIE-P1000 at a `constraint` or `derive` item kind: bare
    (`export constraint c`) `Unexpected 'constraint'.` is now `Unexpected
    'constraint'. Constraint and derive stay in their module.`; parenthesized
    (`export (constraint c)`) `Unexpected 'constraint'; expected 'type',
    'enum', 'shape', 'source', 'table' or 'query'.` is now `Unexpected
    'constraint'; expected 'type', 'enum', 'shape', 'source', 'table',
    'query', 'def' or 'relationship'. Constraint and derive stay in their
    module.` (`'derive'` likewise).
  - PIE-P1000 for an `export:` block that holds a `def` item: was at the item
    (2:5), `Unexpected 'def'; expected 'type', 'enum', 'shape', 'source',
    'table', 'query' or end of line.`; now the block-form refusal at the `:`
    (1:7), `This spelling is not accepted by the modern syntax. Write 'export
    kind Name' or a parenthesized list with explicit kinds.` (same
    suggestion), as for a block that holds any other kind.
  - PIE-S2103 def and relationship hints: `Unknown function: pos; pos is a
    def of models/a.pietto, which a module cannot import: declare it in this
    module` is now `Unknown function: pos; pos is a def exported by
    models/a.pietto: import it with from "models/a.pietto" import def pos`,
    or, when no module exports it, `Unknown function: pos; pos is a def
    declared but not exported by models/a.pietto: export it there with export
    def pos, then import it with from "models/a.pietto" import def pos`; a
    relationship likewise (`Unknown function: OrderCustomer; OrderCustomer is
    a relationship exported by models/a.pietto: import it with from
    "models/a.pietto" import relationship OrderCustomer`, and the
    `declared but not exported ... export it there with export relationship
    OrderCustomer, then import it with ...` form). As for other import hints,
    at most three modules are named in full, and a module whose path no
    Pietto string spells, or that imports the module of the call, is not
    named. When no module is left, or when the module of the call already
    declares or imports the name (an import would be PIE-S2706), the 0.1.9
    text stays byte-equal, naming the declaring modules (`...; OrderCustomer
    is a relationship of models/a.pietto, which a module cannot import:
    declare it in this module`, `...; pos is a def of models/a.pietto, which
    a module cannot import: declare it in this module`). The JSON
    `suggestion` of the relationship hint is now the hint text (0.1.9:
    `null`), as for every hint on this path. A name that other modules
    declare both as a relationship and as a def gets the relationship hint,
    as before.
  - PIE-S2103 for a qualified call (`a.pos(x)`, `a.OrderCustomer(orders,
    buyer)`): `Unknown function: a.pos` gains, when another module declares
    `pos`, `; pos is a def exported by a.pietto: import it with from
    "a.pietto" import def pos, then call pos(...)` (or the relationship or
    not-exported form with `, then call NAME(...)`).
- **New refusals and diagnostics:**
  - PIE-S2706 at a def or relationship import binding that collides with a
    local declaration of any kind (a def or relationship included) or another
    import of the name: `Import binding collides with a local declaration:
    pos; import def pos as <name>`, `Import binding collides with a local
    declaration: OrderCustomer; import relationship OrderCustomer as <name>`,
    `Import binding name is ambiguous: oc; import relationship OrderCustomer
    as <name>` (the hint names the first def or relationship item that binds
    the name, whatever item comes first). Located as every PIE-S2706 is: at
    the import binding whatever the declaration order; an ambiguous name at
    its first binding, the others as related locations. The hint is in the
    message (module diagnostics carry no suggestion).
  - PIE-S2398 at a def or relationship import item bound to a built-in name,
    `Float`, `Text` and `concat` included: `Import binding concat has the
    name of a built-in function; a def cannot shadow one` (`...; a
    relationship cannot shadow one`).
  - PIE-S2705 and PIE-S2704 for def and relationship items as for other
    kinds, for example `Imported declaration is private or not exported: def
    helper from "a.pietto"`, `Imported declaration has another kind: def
    OrderCustomer from "a.pietto" is a relationship; write relationship
    OrderCustomer`, `Unknown export binding: relationship Nope`, `Ambiguous
    local export declaration: relationship OrderCustomer`.
  - PIE-S2604 at a row argument whose shape is not the declaring module's
    parameter shape (unchanged text): `Relationship OrderCustomer parameter
    order requires declared shape Order; the actual row has a different shape
    identity`. A body error of an imported relationship is reported once, at
    its declaration; a call of it is told `Relationship predicate
    OrderCustomer has no unambiguous checked declaration`, as a call of the
    same local relationship is.
  - PIE-S2707 at a `def` or `relationship` item of a PACKAGE_ROOT package
    module: `Unsupported module item: def pos`, suggestion `Package modules do
    not support def/relationship imports yet.`
  - A failed def or relationship import or export item, or such an import
    along an import cycle (PIE-S2703), stops the project check before
    semantic analysis, as a def error does; calls of a blocked def or
    relationship add no PIE-S2103, PIE-S2395 or PIE-S2604.
- **Compatibility.** No change for a project without a `def` or
  `relationship` import or export item (byte-equal check JSON, emission and
  compiled bundles). A module's own def or relationship still never collides
  with an import of another kind (`from "a.pietto" import source rows` beside
  `def rows` or `relationship rows`), also when another module's error stops
  the check. No compiled-record change: def and relationship items never
  reach a compiled bundle; a call's compiled predicate record names the
  declaring module's template, as a local one does.

### Relationships take table and query rows

- A relationship parameter now takes the rows of a table or a query, in a
  project also one imported from another module, matched by field name: each
  field of the parameter's shape needs an output column of its name and type.
  Types are compared after alias expansion on both sides, an enum by its
  declaration (enums of two modules with one name are two types). A column
  that may be None does not bind a field of type `T`: neither a column of type
  `T | None` nor one of unknown nullability, such as a computed `x + 1`, as a
  def parameter without `| None` takes neither (PIE-S2395); write
  `coalesce(x + 1, 0)` or declare the field `T | None`. A column of unknown
  type, such as `None` written alone, is compared by name only, as a def
  argument is. Decimal precision and scale are not compared, as a value's
  type is `Decimal`. Extra columns are ignored. A source's rows still need
  the parameter's own shape, so a source of another shape with the same
  fields is still refused, while a query that selects that source's columns
  is taken.
- Reading a LEFT-joined table or query row through a relationship keeps it
  nullable, as for a source row. Only a grouped query's GROUP BY key proves a
  key: the parameter shape's `unique` says nothing about a query's rows, so an
  aggregate over a JOIN on a query that is not grouped stays refused
  (PIE-S2381 in a single file, PIE-S2333 in a project, as for the same `on`
  written out).
- The SQL of such a call is the SQL of its body written as the `on` (or
  WHERE, SELECT or `let` test), byte for byte, in `emit-sql` and
  `emit-sql --project`, for PostgreSQL and MySQL; project `compile_query` and
  the live template keep it. A two-database differential (PostgreSQL 18.6,
  MySQL 8.4.12) of the LEFT, table, grouped, WHERE, SELECT, `let`, `any` and
  FROM forms, each as a single file and as a project query, matched the
  expected rows on both databases.
- **Refusals that become acceptances.** Each form below reported PIE-S2604
  `Unavailable row argument for relationship R parameter p` in 0.1.9 and is
  now accepted, in single files and EXPLICIT_MODULES projects:
  - a query's or a table's rows as a JOIN input in `on`
    (`let buyer = active_customers`, then
    `left join buyer on OrderCustomer(orders, buyer)`);
  - a grouped query's rows, its GROUP BY key proving the key of an aggregate
    over the JOIN (`left join s on CustomerSpend(customers, s)` with
    `count(customers.id)` per region);
  - a table or query JOIN input in WHERE, SELECT or a `let` of a JOIN query
    (`where OrderCustomer(orders, buyer)`);
  - a table or query read with `from`, in a query without JOIN
    (`from active_customers`, `where InRegion(active_customers)`);
  - the row of `any(... for c in q)` over a table or query
    (`where any(OrderCustomer(orders, c) for c in active_customers)`);
  - in a project, any of these forms over a query or table imported from
    another module, or over a local query that reads an imported source.
- **New refusal texts** (PIE-S2604, ERROR, at the row argument; the first
  field in the shape's declaration order that does not match):
  - `Unavailable row argument for relationship R parameter p: no column f`
  - `Unavailable row argument for relationship R parameter p: column f is T,
    field f is U` (for example `column region_id is Text, field region_id is
    Int`, or `column tier is Level, field tier is Tier` for two enums)
  - `Unavailable row argument for relationship R parameter p: column f is T |
    None, field f is T`
  - `Unavailable row argument for relationship R parameter p: column f is T
    of unknown nullability, field f is T` (a computed column such as `x + 1`)
  - `Unavailable row argument for relationship R parameter p: column f is E
    from "m.pietto", field f is E from "n.pietto"` (enums of two modules with
    the same name)
  - An imported relationship checks a table or query row against the field
    types of the module that declares it, as a local one does.
- **Compatibility.**
  - `Unavailable row argument for relationship R parameter p` without a
    reason still reports an argument that names no row the call can read,
    and, in a project, a query input whose columns are not known where the
    call is bound (below); it no longer reports a table or query input whose
    columns match.
  - A call whose name is both a `def` and a relationship, with an argument
    that names a table or query input, is now a relationship call (it was the
    `def` call), as for a source input; with only scalar arguments it is
    unchanged.
  - In a project, a query that itself has a JOIN binds a parameter only as
    the FROM row of a query without JOIN; read in a query with a JOIN (as
    its FROM row or a JOIN input) or through `any(...)`, its output row is
    not known where the call is bound, so the call still reports
    `Unavailable row argument for relationship R parameter p`, with no
    reason also when a column does not match. A single file takes it, and
    the same test written out (`on q.id == x.id`) compiles in a project too.

### MySQL catch-up in projects

- **UUID ordering on MySQL.** MySQL project SQL now emits UUID `<`, `<=`,
  `>`, `>=`, inclusive chains (`a <= u <= b`), a result `order by` key and a
  window `order by` key over the reviewed `BINARY(16)` carrier, ordered by
  the 16 bytes as unsigned big-endian values, as on PostgreSQL since `0.1.7`
  (compiled bundle and live template too). A two-database differential
  (PostgreSQL 18.6, MySQL 8.4.12) of each form, over UUIDs that tell signed
  and little-endian byte orders apart, matched the expected rows on both
  databases. **Refusals that become acceptances:** PIE-B1003
  `comparison_type_pair_not_admitted`, `between_type_pair_not_admitted` and
  `order_comparison_domain_unsupported`, and PIE-B1002
  `window_order_comparison_domain_unsupported` for a window key, at the same
  places as before, for these MySQL UUID forms. Project `max(a, b)` and
  `min(a, b)` of two UUID values, which are their `<` comparison inside a
  conditional, are now emitted on MySQL too (before: PIE-B1003
  `comparison_type_pair_not_admitted`).
- **Aggregates of Text, Bool, Float and Decimal values on MySQL.**
  `emit-sql --project --dialect mysql` now emits, VERIFIED, the aggregates
  that "Project aggregates match single files on PostgreSQL" above opened on
  PostgreSQL, with the same SQL shape and MySQL carriers (compiled bundle and
  live template too):
  - `count(x)` and `count_distinct(x)` of a `Text`, `Bool` or `Decimal` value
    and `count(x)` of a `Float`, as `COUNT(x)` and `COUNT(DISTINCT x)`, a
    non-null `my_bigint` count (before: PIE-B1003
    `count_argument_outside_reviewed_int_domain`,
    `count_distinct_argument_outside_reviewed_int_domain`);
  - `min(x)` and `max(x)` of a `Float` or `Decimal` value, as `MIN(x)` and
    `MAX(x)`, keeping the argument's carrier (`my_double`, `my_decimal`) and
    nullable (before: PIE-B1003 `min_argument_outside_reviewed_int_domain`,
    `max_argument_outside_reviewed_int_domain`);
  - an aggregate whose argument is a row expression, such as
    `count(lower(label))`, `count_distinct(trim(lower(label)))`,
    `count(len(label))` or `count(flag and flag)`, emitted inside the
    aggregate as a `let` would lower it (before: PIE-B1003
    `aggregate_argument_not_a_direct_established_field`).
  `count_distinct`, `min` and `max` compare by the GROUP BY key law of the
  argument's carrier, as on PostgreSQL: `utf8mb4_0900_bin` NO PAD keeps
  `"a"`, `"A"` and `"a "` apart; `-0.00` and `0.00` are one Decimal value; a
  Float `min` or `max` whose extreme class holds both zeros shows some
  member's value. Refusal move (MySQL, same select item): a row-expression
  argument that stays refused now reports the blocker its `let` form reports
  instead of PIE-B1003 `aggregate_argument_not_a_direct_established_field`,
  as on PostgreSQL: `sum(amount + amount)` reports PIE-B1004
  `decimal_aggregate_range_proof_missing`; an `Int` expression not proved to
  fit BIGINT still reports PIE-B1002 `arithmetic_outside_physical_range`
  first.
- **ORDER BY a Float on MySQL.** A relation `order by` over a finite `Float`
  column is now VERIFIED on MySQL, with or without `limit`, as on PostgreSQL:
  Floats order by real value, `-0.0` and `0.0` tie and tied rows have no
  promised relative order (before: PIE-B1003
  `order_comparison_domain_unsupported` at the ORDER BY item).
- **`min` and `max` of a Timestamp or Date on MySQL.**
  `emit-sql --project --dialect mysql` now emits, VERIFIED, `min(x)` and
  `max(x)` of a `Timestamp` (`DATETIME(6)`) or `Date` (`DATE`) value, grouped
  or over the whole input, as `MIN(x)` and `MAX(x)`, as on PostgreSQL
  (compiled bundle and live template too). The result keeps the argument's
  carrier (`my_datetime` with 6 fractional digits, so microseconds are kept;
  `my_date`) and admits NULL, which an empty input or a group of NULL values
  gives. A two-database differential (PostgreSQL 18.6, MySQL 8.4.12) of a
  grouped, a whole-input and an empty-input form, over values one microsecond
  apart, a leap day and NULLs, matched the expected rows on both databases,
  and MySQL reported each result column as `DATETIME` with 6 decimals or as
  `DATE`. **Refusals that become acceptances:** PIE-B1003
  `min_argument_outside_reviewed_int_domain` and
  `max_argument_outside_reviewed_int_domain`, at the same select items, for
  these MySQL arguments. **Refusal move** (MySQL): a statement that was
  refused only at such a `min` or `max` and has another blocker in a later
  stage now reports that blocker, for example an aggregate window in the same
  select (PIE-B1003 `window_aggregate_approved_non_support_on_mysql`, at the
  window); a blocker in the same select list, such as `sum` of an `Int`
  (PIE-B1004 `sum_int_aggregate_range_proof_missing`), was already reported
  beside it. An aggregate window over a Timestamp or Date stays refused on
  MySQL, as every MySQL aggregate window. Single-file MySQL `MIN` and `MAX`
  of these values are unchanged.
- **Two `Bool` values in single-file `max(a, b)` and `min(a, b)` on MySQL**
  are emitted (see "`max(a, b)` and `min(a, b)`" above): the result is an
  integer column holding 0, 1 or NULL, as every computed `Bool` is there.
- A two-database differential (PostgreSQL 18.6, MySQL 8.4.12) of the
  aggregate, Float ORDER BY and `Bool` `max`/`min` forms, with MySQL column
  types judged, matched the expected rows on both databases.
- **Kept refused on MySQL.** In projects, Int arithmetic not proved to fit
  signed 64 bits (PIE-B1002 `arithmetic_outside_physical_range`,
  `unary_result_outside_physical_range`, `abs_result_outside_physical_range`)
  stays refused: its two-database differential did not pass, as MySQL raised
  error 1690 (SQLSTATE 22003) on a product whose value, `-2^63`, fits signed 64
  bits. Also unchanged in MySQL projects: `count_distinct` of a `Float`
  (PIE-B1003 `count_distinct_argument_outside_reviewed_int_domain`; MySQL kept
  `-0.0` and `0.0` apart in deduplication beside a wide key); `sum`, `avg` and
  `stddev` of a `Float` (PIE-B1004
  `float_aggregate_finite_result_proof_missing`); `sum(Int)` (PIE-B1004
  `sum_int_aggregate_range_proof_missing`); `stddev` of an `Int` (PIE-B1003
  `stddev_int_not_admitted_on_target`); `select distinct` over a `Float`
  (PIE-B1003 `distinct_field_comparison_domain_unsupported`); Float
  `union distinct`, `intersect` and `except` (PIE-B1003
  `set_row_equivalence_domain_unsupported`); `==` and `!=` between two `Float`
  row reads and `same_value` of two such values (PIE-B1003
  `comparison_type_pair_not_admitted`); `concat(a, b)` (PIE-B1003
  `scalar_call_signature_not_admitted`) and `Text(x)` of an `Int` (PIE-B1003
  `cast_realization_not_admitted`); the `Decimal(p, s)`, `Date`, `Timestamp`
  and `UUID` query parameters (PIE-B1003
  `query_parameter_type_not_admitted_on_target`, see
  "Typed project query parameters" above); the conditional count and sum
  (PIE-B1003 `conditional_count_not_admitted_on_target`, PIE-B1004
  `sum_int_aggregate_range_proof_missing`, see
  "Conditional count and sum in projects" above). A MySQL single file emits
  each of these forms except `stddev` of an `Int` and the conditional sum
  (PIE-B1000, see "Conditional count and sum" above) and `select distinct`, the
  set operations and query parameters, which a single file does not check
  (PIE-S2334, PIE-S2346). Window ORDER BY and PARTITION BY over a `Float` stay
  refused in projects on both targets (PIE-B1002
  `window_order_comparison_domain_unsupported`,
  `window_partition_comparison_domain_unsupported`); single files emit them.
  `string_agg` stays refused on MySQL in both (single file PIE-B1000
  `MySQL aggregate string_agg is not supported`, project PIE-B1003
  `aggregate_function_not_promised_in_slice8`), as `GROUP_CONCAT` truncates
  silently at `group_concat_max_len`.
- The private emission observation of a Decimal operation over two Decimal
  fields, or of a Float operation over two Float literals, now passes its
  independent check on PostgreSQL; emitted SQL is unchanged.

### Asof JOIN on MySQL

- MySQL now emits the backward asof JOIN (`asof left join`, `asof inner
  join`), after a two-database differential on MySQL 8.4.12 and PostgreSQL
  18.6.
  - Single file (`emit-sql --dialect mysql`): the same latest row as
    PostgreSQL, with backticks:
    `LEFT JOIN LATERAL (SELECT * FROM <source> AS <b> WHERE <on> ORDER BY <b>.<time> DESC LIMIT 1) AS <b> ON TRUE`
    (`INNER JOIN LATERAL` for `asof inner join`). A `Text` key compares
    under the column's collation, as in any MySQL JOIN, so the declared
    `unique(...)` must hold under it. An asof JOIN in a relation with a FULL
    JOIN, which MySQL emulates with UNION ALL, stays refused (below).
  - Project (`emit-sql --project --dialect mysql`): the same JOIN plus
    `NOT EXISTS` latest-row test as PostgreSQL; the compiled replay and the
    live template bind the same statement.

Refusals that become acceptances:

| Mode | Before (exact) | After |
| --- | --- | --- |
| single file, `emit-sql --dialect mysql` | `PIE-B1000 error: MySQL SQL emission is not implemented for RelationIR: <name>. MySQL has no ASOF JOIN yet; emit with --dialect postgres` (at the relation) | emitted |
| project, `emit-sql --project --dialect mysql` | `blocker PIE-B1003 UNSUPPORTED_RULE: asof_join_not_admitted_on_target`, hint `MySQL has no ASOF JOIN yet; emit with --dialect postgres.` (at each plan JOIN with an asof JOIN, upstream relations included) | VERIFIED |

Refusal kept with a narrower text:

| Mode | Before (exact) | After (exact) |
| --- | --- | --- |
| single file, `emit-sql --dialect mysql`, an asof JOIN in a relation that also has a FULL JOIN (before or after it) | `PIE-B1000 error: MySQL SQL emission is not implemented for RelationIR: <name>. MySQL has no ASOF JOIN yet; emit with --dialect postgres` | `PIE-B1000 error: MySQL SQL emission is not implemented for RelationIR: <name>. MySQL has no ASOF JOIN in a relation with a FULL JOIN yet; emit with --dialect postgres` |

Same code, same position (the relation span), same order among the JOIN
refusals (the asof JOIN's place in the JOIN-order walk of the FULL JOIN
checks). PostgreSQL is unchanged and still emits both compositions natively.
A query that FULL JOINs another query holding an asof JOIN is emitted: the
asof JOIN stays in that query's own CTE.

No new diagnostic code, no other refusal or compatibility change, no compiled
record change (VERSIONS unchanged). The blocker detail
`asof_join_not_admitted_on_target` and its hint are retired with the project
family.

### `variance`, `pvariance` and `pstdev` aggregates

- `variance(x)`, `pvariance(x)` and `pstdev(x)` are the sample variance, the
  population variance and the population standard deviation of the non-None
  values of one direct `Int` or `Float` field, as Python's
  `statistics.variance`, `statistics.pvariance` and `statistics.pstdev`: a
  nullable `Float`. `variance` is None for fewer than two values; `pvariance`
  and `pstdev` are None for none and 0.0 for one. `stddev(x)` is unchanged.
- PostgreSQL, single file and project: `CAST(VAR_SAMP(x) AS double
  precision)`, `CAST(VAR_POP(x) AS double precision)` and
  `SQRT(CAST(VAR_POP(x) AS double precision))` (`pg_catalog.float8` in a
  project, where a `Float` argument carries the
  `target_checked_binary64_overflow` evidence, as `stddev`), VERIFIED in
  projects and carried through compiled bundles and live templates.
- MySQL: single-file `Float` as `VAR_SAMP(x)`, `VAR_POP(x)` and
  `STDDEV_POP(x)`, after a two-database differential (PostgreSQL 18.6, MySQL
  8.4.12) of the three functions over `Int` and `Float` groups matched
  Python's `statistics` within the stated bounds; `Int` refused (PIE-B1000);
  every project form refused (PIE-B1003 `Int`, PIE-B1004 `Float`), as
  `stddev`.
- Accuracy: `variance` and `pvariance` of an `Int` within ε·v and `stddev` and
  `pstdev` within 2·ε·s of Python's (ε = 2^-52); a `Float` result within the
  bounds stated in [Aggregates and grouping](language.md#aggregates-and-grouping).
- **New or changed diagnostics** (exact texts; "before" is `main` before this
  change):

| Code | Position | Program | Before | After |
|---|---|---|---|---|
| PIE-S2103 | the call | `var(x)` | `Unknown function: var; the available aggregates are avg, count, count_distinct, max, median, min, quantile, stddev, string_agg and sum` (no suggestion) | ``Unknown function: var; pandas `var()` is the sample variance: write `variance(x)`; numpy `var` is the population variance: write `pvariance(x)` ``; suggestion = the hint |
| PIE-S2103 | the call | `VARIANCE(x)`, `Variance(x)` (any non-lowercase spelling) | `Unknown function: VARIANCE; the available aggregates are ...` (the list above) | ``Unknown function: VARIANCE; write lowercase `variance(x)` for the sample variance (PostgreSQL `VARIANCE`, pandas `var()`); MySQL `VARIANCE` and numpy `var` are the population variance: write `pvariance(x)` ``; suggestion = the hint |
| PIE-S2103 | the call | `std(x)` | ``Unknown function: std; `stddev` is the sample standard deviation (Python `statistics.stdev`); MySQL `STD`/`STDDEV` and numpy `std` are the population deviation, which is not available`` | ``Unknown function: std; pandas `std()` is the sample deviation: write `stddev(x)`; numpy `std` and MySQL `STD` are the population deviation: write `pstdev(x)` ``; suggestion = the hint |
| PIE-S2103 | the call | `STDDEV(x)`, `Stddev(x)` | the `std` text before | ``Unknown function: STDDEV; write lowercase `stddev(x)` for the sample deviation (PostgreSQL `STDDEV`, pandas `std()`); MySQL `STDDEV` and numpy `std` are the population deviation: write `pstdev(x)` ``; suggestion = the hint |
| PIE-S2103 | the call | `var_samp(x)` | the available-aggregates list | ``Unknown function: var_samp; write `variance(x)`, the sample variance (Python `statistics.variance`)``; suggestion = the hint |
| PIE-S2103 | the call | `statistics.variance(x)` | `Unknown function: statistics.variance` (no hint) | as `var_samp` |
| PIE-S2103 | the call | `var_pop(x)` | the available-aggregates list | ``Unknown function: var_pop; write `pvariance(x)`, the population variance (Python `statistics.pvariance`)``; suggestion = the hint |
| PIE-S2103 | the call | `statistics.pvariance(x)` | `Unknown function: statistics.pvariance` (no hint) | as `var_pop` |
| PIE-S2103 | the call | `stddev_pop(x)`, `statistics.pstdev(x)` | the `std` text before | ``Unknown function: stddev_pop; write `pstdev(x)`, the population standard deviation (Python `statistics.pstdev`)``; suggestion = the hint |
| PIE-S2103 | the call | `pstddev(x)` | `Unknown function: pstddev` (no hint) | as `stddev_pop` |
| PIE-S2103 | the call | `PVARIANCE(x)` (any non-lowercase spelling) | `Unknown function: PVARIANCE` (no hint) | ``Unknown function: PVARIANCE; write lowercase `pvariance(x)` ``; suggestion = the hint |
| PIE-S2103 | the call | `PSTDEV(x)`, `Pstdev(x)` | the `std` text before | ``Unknown function: PSTDEV; write lowercase `pstdev(x)` ``; suggestion = the hint |
| PIE-S2103 | the call | `variance(x) window(...)` (also `pvariance`, `pstdev`) | `Unknown function: variance; the available aggregates are ...` (`pstdev`: `Unknown function: pstdev`, no hint) | `Aggregate window functions are not implemented: variance; window aggregates are sum, count, avg, min and max` (the `stddev` text; without the suffix where the relation admits no such window) |
| PIE-S2103 → PIE-S2314 | the call | `variance(d)` of a `Decimal` (also `Text`, `Date`, ...) | `Unknown function: variance; ...` + PIE-S2319 in a grouped query | `Aggregate function variance expects Int or Float field argument, got Decimal` alone |
| PIE-S2103 → PIE-S2309 | the call | `variance()`, `variance(a, b)` | `Unknown function: variance; ...` | `Aggregate function variance expects 1 arguments, got 0` / `got 2` |
| PIE-S2103 → PIE-S2315 | the call | `variance(a + 1)`, `variance(1)`, `variance(w)` with `let w = a` (file and project) | `Unknown function: variance; ...` | `Aggregate function variance requires a direct field argument; expression arguments are not supported yet` |
| PIE-S2103 → PIE-S2308/PIE-S2310/PIE-S2311/PIE-S2313/PIE-S2381 | as for `stddev` | `variance` in HAVING/QUALIFY, composed, nested, unaliased, over a repeating JOIN | `Unknown function: ...` | the `stddev` diagnostics with the function's name |
| PIE-S2103 → PIE-S2334 | the call | `variance(o.x for o in group)` (also `pvariance`, `pstdev`); in a `schema_version = 2` project also `variance(o.x for o in c.xs)` over a row's collected list | `Unknown function: variance; ...` (`pstdev`: the `std` text) | ``variance takes no generator; a conditional variance is not available; only `sum(... for o in group if ...)` takes a generator``; over a list ``variance takes no generator; a list variance is not available; `sum` and `any` take a list generator``; the hint the JSON `suggestion` |
| PIE-B1000 (new text) | the relation | single-file MySQL `variance`/`pvariance`/`pstdev` of an `Int` | PIE-S2103 at check | `MySQL SQL emission is not implemented for RelationIR: <name>. MySQL aggregate variance of an Int argument is not supported; emit with --dialect postgres` (each name) |
| PIE-B1003 (new details) | the aggregate | project MySQL `Int` | PIE-S2103 at check | `variance_int_not_admitted_on_target`, `pvariance_int_not_admitted_on_target`, `pstdev_int_not_admitted_on_target`; suggestion ``Emit this Int variance for PostgreSQL, or keep it in check/plan: MySQL computes an integer variance in DOUBLE, which loses Int accuracy; casting the input does not restore it.`` (`pvariance`: `Int pvariance` / `integer variance`; `pstdev`: `Int pstdev` / `integer deviation`) |
| PIE-B1004 | the aggregate | project MySQL `Float` | PIE-S2103 at check | `float_aggregate_finite_result_proof_missing` (existing detail and suggestion) |
| PIE-B1003 / PIE-B1002 (unreachable after check) | | | | `variance_argument_outside_reviewed_int_domain` (and `pvariance_`, `pstdev_`) with the existing reviewed-carrier suggestion; `variance_result_logical_type_or_argument_drift` (and `pvariance_`, `pstdev_`) |

The other names of the available-aggregates hint (`mean(x)`, `array_agg(x)`,
`group_concat(x)`, a non-lowercase `median`, `quantile` or `string_agg`) now
list ``avg, count, count_distinct, max, median, min, pstdev, pvariance,
quantile, stddev, string_agg, sum and variance`` (no suggestion, as before).
`stdev`, `stddev_samp` and `statistics.stdev` are unchanged (``write
`stddev`, the sample standard deviation (Python `statistics.stdev`)``, no
suggestion).

Compatibility (accepted programs that change; owner decision 7a,
2026-11-06):

| Program | Before | After |
|---|---|---|
| `def variance(x: Int) -> Int: ...` (called or not) | accepted; `variance(a)` calls the def | PIE-S2398 at the def, `Def variance has the name of a built-in function; a def cannot shadow one`, suggestion ``Rename this def: `variance` is now the built-in sample variance aggregate, and a call to variance always means it.`` |
| `def pvariance(...)` | accepted | PIE-S2398, same message with `pvariance`; suggestion ``Rename this def: `pvariance` is now the built-in population variance aggregate, and a call to pvariance always means it.`` |
| `def pstdev(...)` | accepted | PIE-S2398, same message with `pstdev`; suggestion ``Rename this def: `pstdev` is now the built-in population standard deviation aggregate, and a call to pstdev always means it.`` |

A `constraint` or `derive` named `variance`, `pvariance` or `pstdev` still
checks; a call of that name, which was PIE-S2103 ``Unknown function:
variance; variance is a constraint, which cannot be called; write a `def`
instead`` (`derive` alike), is now the aggregate. A `relationship
variance(...)` (or `pvariance`, `pstdev`) template keeps its meaning in WHERE
and in a select item, with byte-identical PostgreSQL SQL. A `schema_version =
1` project checks `variance`, `pvariance` and `pstdev` as `stddev` (before:
PIE-S2103 + PIE-S2319).

Formats: a compiled `aggregate_value` record may name `variance`, `pvariance`
or `pstdev` (one input); such bundles carry the Phase73 version marks `(7, 1,
7, 1)`, and a reader of earlier marks refuses them. Project JSON v2 gains the
aggregate `spelling` `VAR_POP` and the blocker details listed above; no new
`ranges` role.

### Distinct count of several columns: `count_distinct(a, b, ...)`

- `count_distinct(a, b, ...)` is the number of distinct tuples of two or more
  different direct fields (or `let:` names of fields) among the rows in which
  none of them is None: an `Int`, never None, 0 for no such row, with each
  field compared as `count_distinct(x)` compares it (`-0.0` = `0.0`, `Decimal`
  `1.0` = `1.00`). Single file and `schema_version = 2` project on PostgreSQL
  (`COUNT(DISTINCT CASE WHEN a IS NOT NULL AND b IS NOT NULL THEN ROW(a, b)
  END)`), also over JOIN rows, carried through compiled bundles and live
  templates. Single-file MySQL emits `COUNT(DISTINCT a, b)`, `Float` fields
  included, after a two-database differential (PostgreSQL 18.6, MySQL 8.4.12)
  of tuples with None members, `Decimal` scales, signed zeros and NO PAD Text
  matched the expected counts on both databases.
- **New diagnostics** (codes unchanged; new texts; hint = JSON `suggestion`
  where marked):

| Program | Code, position | Exact text |
| --- | --- | --- |
| `count_distinct(a, a)` (also `count_distinct(a, b, a)`, a `let:` name of `a`, or `a` beside `t.a` with `t` its binding: `count_distinct(pot, sales.pot)`) | PIE-S2104 at the repeated argument (the field named as first written; an unknown or ambiguous read is its own error alone) | ``Invalid arguments for aggregate count_distinct: a is written twice; write `count_distinct(a)` `` (two arguments) or `...; write each column once` (three or more); hint = suggestion |
| `count_distinct(lower(a), b)`, `count_distinct(a, None)`, a computed `let:` argument | PIE-S2315 at that argument | `Aggregate function count_distinct of several columns requires a direct field for each argument; expression arguments are not supported` |
| a field of a type `count_distinct(x)` refuses (enum, Json, Bytes, Any) | PIE-S2314 at that argument | `Aggregate function count_distinct expects Bool, Int, Float, Decimal, Text, Date, Timestamp, or UUID field argument, got NAME` (NAME: the type an alias expands to) |
| MySQL project | PIE-B1003 at the select item, detail `count_distinct_tuple_not_admitted_on_target` | suggestion `Emit this count_distinct of several columns for PostgreSQL, or keep it in check/plan: a project's MySQL emission has no COUNT(DISTINCT a, b) yet (a single file emits it).` |
| `schema_version = 1` project | PIE-S2334 at the call | `count_distinct(a, b, ...): a schema_version = 1 project has no count_distinct of several columns in the current syntax; set schema_version = 2 to check it.` |

Changed diagnostics of programs refused before:

| Program | Before | After |
| --- | --- | --- |
| `count_distinct(a, b)` | PIE-S2309 `Aggregate function count_distinct expects 1 arguments, got 2` (single file, project, `schema_version = 1`) | admitted, or one refusal above (in `schema_version = 1`: PIE-S2334) |
| `count_distinct()` | PIE-S2309 `Aggregate function count_distinct expects 1 arguments, got 0` | PIE-S2309 `Aggregate function count_distinct expects at least 1 argument, got 0` (same code and span) |
| `count_distinct(lower(a), trim(a))` | PIE-S2309 | PIE-S2315 at `lower(a)` |
| `nunique(x)`, `n_unique(x)` (any case) | PIE-S2103 `Unknown function: nunique` (+ PIE-S2319 where grouped) | same code, span and order; message gains ``; write `count_distinct(x)`, which does not count None (polars `n_unique` counts null as a value; pandas `nunique()` skips it by default); for several columns `count_distinct(a, b)` ``, also the JSON `suggestion` |
| `count(distinct a, b)` | PIE-P1000 ``Unexpected 'a'. Write `count_distinct(x)` for COUNT(DISTINCT x).`` | same code and position: ``Unexpected 'a'. Write `count_distinct(x)` for COUNT(DISTINCT x), or `count_distinct(x, y)` for several columns.`` (also `count(distinct a)`) |
| `count_distinct((a, b))`, `len(set((o.a, o.b) for o in group))` (a parenthesized `a`/`o.a` and more as the argument of `count_distinct` or `set`) | PIE-P1000 ``Unexpected ','.`` | same code and position: ``Unexpected ','. Write `count_distinct(a, b)` for the distinct combinations of several columns.`` (message only, as every PIE-P1000 hint) |
| `set(x)` (any case; `len(set(x))`) | PIE-S2103 `Unknown function: set` | same code and span: ``Unknown function: set; write `count_distinct(a, b)` for the number of distinct combinations of several columns, `count_distinct(x)` for one``, the hint also the JSON `suggestion` |

No accepted program changes: every program accepted before keeps its result
and bytes; `count_distinct` was already a reserved built-in name, and
`nunique` and `n_unique` stay ordinary names (a `def nunique` keeps working).
`count_distinct(x)` is unchanged (bytes, types, the `lower`/`trim` chain), and
so is `count_distinct(a, b) window(...)` (PIE-S2103 `Aggregate window
functions are not implemented: count_distinct`). Semantic Metadata Artifact v1
does not list the tuple count, as it lists no `stddev`.

Formats: a compiled `aggregate_value` record may name `count_distinct_tuple`
(every field an input; no record shape change); such bundles carry the Phase73
version marks `(7, 1, 7, 1)`, and a reader of earlier marks refuses them.
Project JSON v2 gains the provenance `function` `count_distinct_tuple` and the
`ranges` syntax roles `aggregate_tuple_open`, `aggregate_tuple_and`,
`aggregate_tuple_then` and `aggregate_tuple_close`.

### The test of a group: `any` and `all` over `group`

- `any(TEST for o in group)` is True when TEST is True for at least one row of
  the group, `all(TEST for o in group)` when it is True for every row; each is
  a `Bool`, never None, and with no row `any` is False and `all` is True, as in
  Python. They are a whole aliased SELECT item of a grouped query or of a query
  with aggregates and no GROUP BY, without JOIN inputs, in a single file and a
  `schema_version = 2` project; `having` and `order by` read the output name.
  Each row's TEST is read as WHERE reads it (three-valued), then folded as
  Python folds: a None TEST is not True, so it is no match for `any` and a
  failure for `all`. Python differs only where None meets `not`, `!=` or
  `not in`, or `==` compares two Nones (Python makes those True); write
  `coalesce(...)` or `... or x is None` for Python's meaning. pandas skips None
  (`skipna=True`), so pandas `all` of `[True, None]` is True; Pietto says False.
- PostgreSQL SQL, single file and project: `(COUNT(CASE WHEN TEST THEN 1 END) > 0)`
  and `(COUNT(CASE WHEN TEST THEN NULL ELSE 1 END) = 0)`; the project result is
  a non-null `pg_bool` (`bool01`) with no R13 evidence. Compiled bundles and
  live templates carry both unchanged.
- Single-file MySQL writes the same form, an integer 0/1 (the computed-Bool
  wire type), after a two-database differential (PostgreSQL 18.6, MySQL
  8.4.12) of None tests, all-True, all-False, mixed, all-None and empty groups
  matched the expected rows on both databases. A MySQL project refuses it with
  PIE-B1003 `group_test_not_admitted_on_target` at its select item,
  suggestion `MySQL has no group any or all yet; emit with --dialect
  postgres.`
- **New refusals.**
  - A project test of a group whose TEST reads no field (`any(True for o in
    group)`): checked, but emission is BLOCKED on either target with PIE-B1003
    `group_test_reads_no_field` at its select item, suggestion ``Test a field
    of the member, such as `any(o.paid for o in group)`: a test that reads no
    field is the same for every row.`` (a single file emits
    `(COUNT(CASE WHEN TRUE THEN 1 END) > 0)`).
  - A query header parameter read in a project test of a group: PIE-S2355
    `Query parameters are not available in this position.` at the read (no
    suggestion), as in every aggregate argument.
  - Internal-only details (forged inputs): PIE-B1002
    `group_test_result_not_non_null_bool`, PIE-B1003
    `group_test_argument_outside_reviewed_bool_domain`.

Compatibility (accepted programs that change; owner decisions 7a and 7b,
2026-11-06):

| Program (accepted in 0.1.9) | After |
| --- | --- |
| a `def any(...)` or `def all(...)` (a call `any(x)`/`all(x)` named the def) | PIE-S2398 `Def any has the name of a built-in function; a def cannot shadow one` at the def, suggestion ``Rename this def: `any` is the built-in test of a relation or of a group, and a call to any always means it.``; `def all`: `Def all has the name of a built-in function; a def cannot shadow one`, suggestion ``Rename this def: `all` is now the built-in test of a group, and a call to all always means it.`` |
| a SELECT item `x = any(... for o in group)` in a query without GROUP BY while a source, table, query, import or `let` named `group` is visible (before, a per-row `EXISTS` over that relation) | PIE-S2334 ``Generator over group in any: group is the relation group, not this group; rename the relation group to read this group's rows`` at `group` (`the let group`, `rename the let group` for a `let`), the hint the JSON `suggestion`. The same `any` in a WHERE, a row `let` or a JOIN `on` keeps its relation meaning and bytes. |
| such an `any(... for o in group)` inside a SELECT item rather than the whole item, as in `x = not any(...)`, `x = 1 if any(...) else 0` or another call's argument, in the same query (before, `NOT EXISTS (...)`, `CASE WHEN EXISTS (...) ...` over that relation) | the same PIE-S2334 at `group`: in a SELECT item, `any(... for o in group)` is always the test of a group |

Changed diagnostics (programs refused before):

| Program | Before | After |
| --- | --- | --- |
| `x = all(TEST for o in group)` (whole aliased SELECT item, no JOIN inputs) | PIE-S2103 `Unknown function: all` | accepted |
| `x = any(TEST for o in group)` in a grouped query; alone in a query without GROUP BY; in a `schema_version = 2` project | PIE-S2319 `Grouped scalar projection expressions are not supported yet` then PIE-S2301 `Unknown or unavailable ANY relation: group`; PIE-S2301 alone; project PIE-S2301 `Unknown relation: group` | accepted |
| `any(... for o in group)` in a WHERE, a row `let` or a JOIN `on`, no relation named `group` (file and `schema_version = 2` project) | PIE-S2301, suggestion ``a group test is not available yet: select `n = sum(1 for o in group if ...)` and test `n > 0` in `having` or a later query`` | same code, message, span and order; suggestion ``a group's rows exist only after `group by`; test a row's own fields directly`` |
| `any(... for o in group)` in `having` or ORDER BY (file and project) | PIE-S2334 `ANY is not supported in this context`, the suggestion above | same; suggestion ``select `has_paid = any(o.paid for o in group)` and read `has_paid` in `having` or `order by` `` (the call's binder in place of `o`) |
| `qualify any(... for o in group)`, grouped or not (file and project) | PIE-S2334 `ANY is not supported in this context`, the suggestion above | same code, message and span; no suggestion |
| `x = any(... for o in group)` beside a non-aggregate SELECT item (a field, a window) in a query without GROUP BY, no relation named `group` | PIE-S2301 `Unknown or unavailable ANY relation: group` at `group` (project: `Unknown relation: group` at the `any(...)`), the suggestion above | PIE-S2312 `Aggregate projections cannot be mixed with non-aggregate projections without GROUP BY` at the `any(...)`, no suggestion (as `sum(...)` there), file and project alike |
| `any(p for o in SOURCE if q)`, any source (`group` or a relation) | PIE-S2334 ``any takes its test in the body; write `any(p and q for o in r)` `` (``write `any(q for o in r)` `` for a `True` body) | same code and span; the generator's source in place of `r`: ``...; write `any(p and q for o in group)` `` |
| `all(... for o in group)` in a WHERE, a row `let`, a JOIN `on` or a `def` body | PIE-S2103 `Unknown function: all` | PIE-S2308 ``Aggregate all() is not allowed in where clause; use it only as a direct aliased select projection; a group's rows exist only after `group by`; test a row's own fields directly`` (`let binding`, `JOIN ON`, `this position`), the hint the JSON `suggestion` |
| `having all(... for o in group)` | PIE-S2103 `Unknown function: all` | PIE-S2308 ``Aggregate all() is not allowed in having clause; use it only as a direct aliased select projection; select `all_paid = all(o.paid for o in group)` and read `all_paid` in `having` or `order by` ``, the hint the JSON `suggestion` (the `any` form keeps PIE-S2334: a compatibility leftover) |
| `order by all(... for o in group)` | PIE-S2103 `Unknown function: all` | PIE-S2308 ``Aggregate all() is not allowed in order by; use it only as a direct aliased select projection; select `all_paid = all(o.paid for o in group)` and read `all_paid` in `having` or `order by` ``, the hint the JSON `suggestion` |
| a SELECT item `any(... for o in group)` grouped, or beside another aggregate, while a relation or `let` named `group` is visible; `all(... for o in group)` anywhere then | PIE-S2319; PIE-S2312 `Aggregate projections cannot be mixed with non-aggregate projections without GROUP BY`; PIE-S2103 `Unknown function: all` | PIE-S2334 ``Generator over group in any: group is the relation group, not this group; rename the relation group to read this group's rows`` (`in all`), alone |
| `all(p for o in group if q)` | PIE-S2103 `Unknown function: all` | PIE-S2334 ``all takes its test in the body; count the exceptions: `n = sum(1 for o in group if q and not p)`, then `having n == 0` `` |
| `all(... for o in orders)` (a relation) | PIE-S2103 `Unknown function: all` | PIE-S2334 ``Generator over orders in all: orders is the whole relation, not this group; for this group's rows write `for o in group`; all over a whole relation is not available`` at `orders` |
| a known non-Bool body: `all(o.amount for o in group)`; `any(o.status for o in group)` in a SELECT item | PIE-S2103 `Unknown function: all`; PIE-S2319 + PIE-S2301 | PIE-S2202 `Expected Bool expression in ALL predicate`; `Expected Bool expression in ANY predicate`, at the body; JSON `suggestion` only (the message keeps the relation `any` text) ``write the body as a test, such as `o.amount > 0` `` for a body that is one Int, Float or Decimal field (binder and field substituted), else `write the body as a test, such as a comparison` |
| `all`/`any(... for o in group)` over JOIN rows | PIE-S2103; PIE-S2301 (+ PIE-S2319) | PIE-S2334 ``all(... for o in group ...) over JOIN rows is not available yet; join in one query, then group it in another that reads it with `from` `` (`any` alike) |
| `all`/`any(... for o in group)` without an alias, or composed (`not all(...)`, `any(...) and True`) | PIE-S2103; PIE-S2301 | PIE-S2313 `Aggregate all() projection requires an explicit alias`; PIE-S2310 `Aggregate projection must be a direct aggregate call; composition around all() is not supported yet` |
| a test that reads a non-member name, a `let`, the binder, a nested aggregate, `any(...)` or a window (`all(paid for o in group)`, ...) | PIE-S2103 for `all`; PIE-S2301 for `any` | the generator rule's PIE-S2334 / PIE-S2311 / PIE-S2102 text, as for `sum(... if TEST)` (``Generator reads paid outside its member; write `o.paid` ``, ...) |
| `bool_and(x)`, `every(x)`, `all(x)` (any letter case) | PIE-S2103 `Unknown function: NAME` + PIE-S2319 | same codes, span and order; message gains ``; write `all(o.x for o in group)` `` (the field's name for `x`), also the JSON `suggestion` |
| `bool_or(x)`, `any(x)` | PIE-S2103 `Unknown function: NAME` + PIE-S2319 | same; ``; write `any(o.x for o in group)` `` |
| `max(b)`, `min(b)` of a `Bool` field | PIE-S2314 ``Aggregate function max expects Int, Float, Decimal, Date, or Timestamp field argument, got Bool`` | same code; message gains ``; for a test of the group write `any(o.b for o in group)` `` (`all` for `min`), also the JSON `suggestion` |
| another aggregate with a generator, `max(o.x for o in group)`, ... | PIE-S2334 ``max takes no generator; a conditional max is not available; only `sum(... for o in group if ...)` takes a generator`` | same code and span; hint ``only `sum(... for o in group if ...)`, `any(...)` and `all(...)` take a generator`` |
| another known callee with a generator, `lower(o.x for o in group)` | PIE-S2334 `A generator is only the argument of sum or any` | PIE-S2334 `A generator is only the argument of sum, any or all` |
| `all(... for o in c.xs)` over a row's collected list (`schema_version = 2` project) | PIE-S2103 `Unknown function: all` | PIE-S2334 ``all takes no list generator; `sum` and `any` take a list generator`` at the call, the hint the JSON `suggestion` |
| a `schema_version = 1` project with `x = any(... for o in group)` in a SELECT item | PIE-S2334 `any(...): a schema_version = 1 project has no any(...) in the current syntax; set schema_version = 2 to check it.` | PIE-S2334 ``any(... for ...): a schema_version = 1 project has no generator in the current syntax; set schema_version = 2 to check it``, the hint the JSON `suggestion`, same span (an `any(...)` elsewhere keeps its text) |

Formats: Project JSON v2 (`emit-sql --project`) gains the aggregate column
`function` values `group_any` and `group_all` (`spelling` `COUNT`, the test in
`argument`, no casts) and the additive `ranges` syntax roles
`aggregate_test_open` (`(`), `aggregate_filter_else` (`NULL ELSE 1`) and
`aggregate_test_close` (` > 0)` or ` = 0)`); a consumer that closes these sets
refuses such a document. A compiled `aggregate_value` record may name
`group_any` or `group_all` (one argument, the Bool test); such bundles carry
the Phase73 version marks `(7, 1, 7, 1)`, and a reader of earlier marks
refuses them.

### `first` and `last` aggregates (arg_max and arg_min)

- `first(x, order by k [desc], ..., id)` is the value of the direct field `x` at
  the first member row of the group in that order and `last(...)` at the last row
  (Python's `sorted(...)[0].x` / `[-1].x`). arg_max is
  `first(x, order by v desc, id)`, arg_min `first(x, order by v, id)`; there is no
  separate `arg_max`/`max_by` name. The order must be total, proven statically:
  each key is a direct field of the input (a `let` name of one reads as it), never
  None (by its type, or a top-level `where` conjunct `k is not None`), and the keys
  with the never-None field GROUP BY keys cover a `unique(...)` of the FROM source.
  A None value at the chosen row is the result (never skipped). Value types `Int`,
  `Decimal`, `Float`, `Text`, `Bool`, `Date`, `Timestamp`, `UUID`; the result has
  the field's type, None where the field may be None or the query has no GROUP BY.
  Grouped and no-GROUP-BY queries; HAVING reads one through its select-item alias.
  PostgreSQL SQL is `(ARRAY_AGG(x ORDER BY k ASC, id ASC))[1]`, `last` with every
  direction flipped, in single files and schema_version = 2 projects (VERIFIED,
  carried through compiled bundles and live templates).
- **New refusals.**
  - PIE-S2104 at the first failing key, once per call (single file and
    schema_version = 2 project alike; hint also the JSON `suggestion`):
    - `Order key of first must be a direct field` (at the key, no hint);
    - ``Order key weight of first may be None, and None has no promised place in
      the order; add `weight is not None` to the query's `where` as a top-level
      `and` test, or order by a key that is never None`` (at the key);
    - ``The order of first does not end in a unique key, so rows that tie have no
      promised order; end the `order by` with the fields of a `unique(...)` key of
      its source, such as `id` `` (at the call; the hint names the source's first
      declared key's fields; for a source without one ``declare a `unique(...)`
      key in the shape of its source and end the `order by` with its fields``; over
      a table or query input ``first reads the `unique(...)` keys of a source: read
      the source with `from`, not a table or query``);
    - ``The order of first reads an input whose fields are not known, so rows
      that tie have no promised order; give its source a shape with a
      `unique(...)` key and end the `order by` with its fields`` (at the call,
      over a source without a shape; over a query that reads one, the table or
      query hint above).

    `last` alike, with its name.
  - PIE-S2334 ``first over JOIN rows is not available yet; join in one query, then
    group it in another that reads it with `from` `` at the call (single file and
    project).
  - A call with an error inside it (an unknown field in its value or a key, a
    value of the wrong type or form, a missing `order by`) reports that error
    alone: no PIE-S2104 order refusal or PIE-S2334 JOIN refusal follows it, in
    single files and schema_version = 2 projects alike; the next call of the
    relation is still checked.
  - MySQL single file: PIE-B1000 `MySQL SQL emission is not implemented for
    RelationIR: <name>. MySQL has no ordered first or last yet; emit with
    --dialect postgres`. MySQL project: PIE-B1003
    `first_last_not_admitted_on_target`, suggestion `Emit this first or last for
    PostgreSQL, or keep it in check/plan: MySQL has no ordered first or last
    yet.` PostgreSQL project: PIE-B1003
    `first_last_order_key_outside_reviewed_order_domain` for a key outside the
    relation ORDER BY domain (R19), PIE-B1002 `first_last_result_logical_type_drift`
    (internal consistency; unreachable after check).
  - PIE-S2314 `Aggregate function first expects Bool, Int, Float, Decimal, Text,
    Date, Timestamp, or UUID field argument, got Size` for an enum or other type;
    PIE-S2315 for an expression value.
  - schema_version = 1 project: PIE-S2334 `first(...): a schema_version = 1
    project has no first(...) in the current syntax; set schema_version = 2 to
    check it.` (`last` alike) at each call; no other diagnostic inside it is kept.
    A project with a generator call reports only its generator refusals, which
    come before semantic analysis, and none of these (nor its JOIN, `any(...)`
    and `count_distinct(a, b, ...)` refusals).

Changed diagnostics (programs refused before):

| Program | Before | After |
| --- | --- | --- |
| `first`/`last(x, order by ...)` in a SELECT item | PIE-S2104 `Internal ORDER BY is only supported by string_agg` | admitted, or one refusal above |
| `first(x)` / `last(x)` without `order by` (grouped) | PIE-S2103 `Unknown function: first` + PIE-S2319 `Grouped scalar projection expressions are not supported yet` | PIE-S2104 ``Invalid arguments for aggregate first: expected ORDER BY key; a group's rows have no order: write `first(x, order by k, id)` `` alone (hint also `suggestion`) |
| `first(x)` / `last(x)` without `order by` elsewhere: in a WHERE (`where first(price_cents)`), or beside a field in a SELECT item without GROUP BY | PIE-S2103 `Unknown function: first` | the PIE-S2104 above, then at the same span PIE-S2308 `Aggregate first() is not allowed in where clause; use it only as a direct aliased select projection` or PIE-S2312 `Aggregate projections cannot be mixed with non-aggregate projections without GROUP BY` (a `schema_version = 2` project lists the WHERE pair PIE-S2308 first, as it does for a `string_agg` without `order by` there) |
| such a call beside a same-named `constraint first` or `derive last` | PIE-S2103 ``Unknown function: first; first is a constraint, which cannot be called; write a `def` instead`` (``...; last is a derive, ...`` for a derive) | the aggregate's diagnostics, as in the row above (PIE-S2104 with PIE-S2308 or PIE-S2312, in that row's order) |
| `first(o.x for o in group)` | PIE-S2103 `Unknown function: first` | PIE-S2334 ``first takes no generator; write `first(x, order by k, id)` `` (hint also `suggestion`; same text in a project, where before it was the project generator refusal) |
| `first(o.x for o in c.xs)` over a row's collected list (`schema_version = 2` project; `last` alike) | PIE-S2103 `Unknown function: first` | PIE-S2334 ``first takes no generator; a list first is not available; `sum` and `any` take a list generator`` at the call, the hint the JSON `suggestion` |
| `where first(x, order by id) == "a"`, `let f = first(...)`, `having first(...) == "a"` | PIE-S2104 `Internal ORDER BY is only supported by string_agg` | PIE-S2308 `Aggregate first() is not allowed in where clause; use it only as a direct aliased select projection` (`let binding`, `having clause`; a grouped query that selects no aggregate also keeps its PIE-S2320, as with `having sum(...)`) |
| `first`/`last(x, order by ...) window(...)` | two PIE-S2104 at one span: `Internal ORDER BY is not supported in a window`, `Internal ORDER BY is only supported by string_agg` | one PIE-S2104 ``Internal ORDER BY is not supported in a window; for one value per group, drop the `window(...)` `` (hint also `suggestion`; `string_agg(...) window(...)` keeps the text without the hint) |
| `first(x) window(...)` | PIE-S2103 `Unknown function: first` | PIE-S2103 `Aggregate window functions are not implemented: first; window aggregates are sum, count, avg, min and max` |
| `max(x, order by v)` and any other internal ORDER BY outside `string_agg`/`first`/`last` (also with a window, second diagnostic; a `def` or constructor call) | PIE-S2104 `Internal ORDER BY is only supported by string_agg` | same code and span; `Internal ORDER BY is only supported by string_agg, first and last` |
| `any_value(x)`, `nth(x, 0)`, `head(x)` | PIE-S2103 `Unknown function: NAME` (+ PIE-S2319 where grouped) | same code, span and order; message gains ``; Pietto never picks an arbitrary row; write `first(x, order by k, id)` ``, also the JSON `suggestion` |
| `arg_max`, `argmax`, `max_by`, `idxmax` | as above | gains ``; write `first(x, order by v desc, id)`; numpy and polars `argmax` return a position, not a value`` (also `suggestion`) |
| `arg_min`, `argmin`, `min_by`, `idxmin` | as above | gains ``; write `first(x, order by v, id)` `` (also `suggestion`) |
| `mean`, `array_agg`, `group_concat` and non-lowercase `median`/`quantile`/`string_agg` | PIE-S2103 `...; the available aggregates are avg, count, count_distinct, max, median, min, pstdev, pvariance, quantile, stddev, string_agg, sum and variance` | the list gains `first, last`: `avg, count, count_distinct, first, last, max, median, min, pstdev, pvariance, quantile, stddev, string_agg, sum and variance` |
| schema_version = 1 or 2 project: `first`/`last(x, order by ...)` | PIE-S2104 `Internal ORDER BY is only supported by string_agg` | v2: admitted or the refusals above; v1: PIE-S2334 `first(...): a schema_version = 1 project has no first(...) ...` |

Compatibility (accepted programs that change; owner decision 7a, 2026-11-06):

- A `def first` or `def last` is now PIE-S2398 `Def first has the name of a
  built-in function; a def cannot shadow one` with the suggestion ``Rename this
  def: `first` is now the built-in ordered first-value aggregate, and a call to
  first always means it.`` (`ordered last-value` for `last`), as `median` and
  `quantile` above; before, both were accepted. A `constraint first` still
  checks, and a call `first(x, order by id)` beside it is the aggregate.
- A schema_version = 2 project's `string_agg(x, ",", order by k)` after a JOIN
  whose order key names no field (`order by sales.sold_att`) passed `check`
  (exit 0, no diagnostic), while a single file reports PIE-S2102. The project now
  reads an internal `order by` key after a JOIN as it reads the aggregate's
  argument and reports PIE-S2102 `Unknown field: sales.sold_att` at the key, as
  a single file does.

Formats: Project JSON v2 gains the `ranges` syntax roles
`aggregate_element_open` (`(`), `aggregate_element_close` (`)[1]`) and
`aggregate_order_reversed_direction` (each key direction of a `last`), and the
aggregate `spelling` `ARRAY_AGG`. A compiled `aggregate_value` record may name
`first` or `last` (one input and a non-empty `order_by`); such bundles carry the
Phase73 version marks `(7, 1, 7, 1)`, and a reader of earlier marks refuses
them.

### `explain --project` lists relation columns (alpha)

- `pietto explain --project ROOT [--format json]` on a `schema_version = 2`
  project lists the output columns of every table and query, in the order of
  the `emit-sql --project --all` batch items: name, type `{kind, name}`
  (`builtin`, `type_alias`, `enum`, `shape`, `unknown`, or `collection` with
  `name: null` and `element` columns for a `collect` column) and nullability
  (`non_null`, `nullable`, `unknown`, kept as computed). An `enum` or `shape`
  type also has `module`, the module that declares it (past imports, import
  aliases, re-exports and alias chains), so two modules' enums of one name
  differ, as they do to the check. JSON format
  `pietto.project-relation-columns.v1` (`cli_errors`, `diagnostics`, `format`,
  `ok`, `relations`); `ok: false`, `relations: null` on failure; exit 1 for
  source errors, 2 for root/configuration/file problems and for an unavailable
  column fact. Text form: `MODULE KIND NAME`, then `  NAME: TYPE kind=KIND
  nullability=N` per column (` module=MODULE` after the kind of an `enum` or
  `shape`; `NAME: collection nullability=N`, element columns indented two more
  spaces); errors and diagnostics on stderr in the
  `check --project` style; stdout empty on failure. Contract:
  [project relation columns v1](spec/project-relation-columns-v1.md).
- No project produces the type kinds `type_alias` or `unknown` today: a
  column whose declared type is an alias reports the type the alias names
  (`total: Money` with `type Money = Int` is `{"kind": "builtin", "name":
  "Int"}`), while single-file `explain` reports `type_alias` for it, and an
  undeclared type name is the error PIE-S2002.
- A relation with an untyped `None` output (`x = None`, check warning
  PIE-S2385) makes the whole document fail closed with the `project_resource`
  error below.
- Alpha: until the Phase82 public format freeze the document may change in
  any release, with a release-note line and no deprecation period.
- Changed public messages of `explain --project` (`pietto.project-explain.v1`,
  `config_schema` at `pietto.toml`):
  - Schema 2 is no longer refused. Removed message:
    `Project Explain runtime requires project schema version 4. Use check --project and emit-sql --project for this schema version 2 project.`
  - Schema 1, old:
    `Project Explain runtime requires project schema version 4. Use check --project for this schema version 1 project.`
    new:
    `Project Explain runtime requires project schema version 2 or 4. Use check --project for this schema version 1 project, or set schema_version = 2 and declare the names a file uses from another file with import and export.`
  - Schema 3, old: `Project Explain runtime requires project schema version 4.`
    new: `Project Explain runtime requires project schema version 2 or 4.`
  - Suggestion (schemas 1 and 3), old:
    `explain --project reads only a schema version 4 package-root project, and changing schema_version alone does not convert a project.`
    new:
    `explain --project reads a schema version 2 explicit-module project or a schema version 4 package-root project, and changing schema_version alone does not convert a project.`
    (schema 3 keeps its appended one-step conversion sentence unchanged).
  - New, only when `pietto.toml` is rewritten between the routing read and a
    later read: `Project configuration changed while explain --project read it.`
    (`config_schema` at `pietto.toml`; in `pietto.project-explain.v1` when the
    later read finds schema 2, in the new document when the pinned parse finds
    schema 1).
- `explain DIR` (text) on a directory whose `pietto.toml` says
  `schema_version = 2` now prints `hint: for a project use pietto explain
  --project DIR` (schema 4 as before).
- CLI error kinds gain uses in the new document: `project_resource` with
  `Project relation columns are unavailable.` (`path: null`), and
  `project_path` with `Project source path must be valid UTF-8 to list
  relation columns: "<escaped path>"; rename it.` (`path: null`).
- No diagnostic code or compiled record changes.

### Python: project SQL without a subprocess (alpha)

- New module `pietto.compiler` with `compile_sql(project, *, module, kind,
  name, dialect, emission_contract, literal_policy="preserve")`,
  `compile_all_sql(project, *, dialect, emission_contract, module=None,
  kind=None, name=None, literal_policy="preserve")` and the frozen result
  `SqlEmission(status, document)`. `document` is byte for byte the stdout of
  `pietto emit-sql --project ... --format json` with the same arguments
  (`--all` for `compile_all_sql`, with only the selectors that are not
  `None`), and `status` is its top-level `status` (`VERIFIED`, `BLOCKED` or
  `INPUT_REJECTED`; the command exits 0, 1 or 2).
- Only a wrong Python argument type raises `TypeError` (a `project` that is
  not `str`/`os.PathLike[str]`, `bytes` paths included, or another argument
  that is not `str`; the batch selectors may be `None`). An out-of-domain
  dialect, kind or literal policy, an empty root, project, configuration and
  contract rejections, absent or ambiguous selectors, BLOCKED and the 64 MiB
  batch limit are returned documents. `UnicodeEncodeError` is raised when the
  command could not encode its document (it then prints
  `pietto: error: terminal output could not be encoded`, exit 2); every other
  exception is internal and propagates unchanged.
- Each call reads the project afresh, writes no file, has no text format and
  opens no database. `pietto.execution.compile_query` is unchanged; it still
  raises `RequestRejected`/`CompileRejected` where `compile_sql` returns a
  document. Spec: [Python compile API v1](spec/python-compile-api-v1.md).
- No diagnostic code, CLI output, JSON document or compiled record changes.

### Formatter: every module of a project

- `pietto fmt --check --project ROOT` and `pietto fmt --write --project ROOT`
  format the modules of an explicit-module project (`schema_version = 2`),
  the files `check --project` reads, in module order (code-point order of the
  project-relative paths), each exactly as `pietto fmt PATH` formats one file.
  `--project` is the same flag as in `check --project`; it takes no path and
  needs `--check` or `--write`.
- `--check` never writes. It prints `would reformat: PATH` on stderr, with the
  module's project-relative path, for each module that would change, and exits
  1 when there is one, 0 otherwise.
- A module with parser errors, or one that `fmt` cannot format (the result
  would not keep its tokens, comments and blocks, or would exceed the source
  size limit), refuses the whole project: the diagnostics and errors of every
  module are printed, no file is written, and `fmt` exits 1.
- `--write` refuses with exit 2, before writing any file, a module that is a
  symbolic link (formatted or not), and a module to replace that is
  read-only, belongs to another user, is not a regular file or is in a
  directory it cannot write. It then replaces each module that changes
  atomically, only while it still holds the bytes that were read, in module
  order; at the first module that changed after it was read or cannot be
  replaced it stops with exit 2, and the modules already replaced stay
  replaced. A formatted module is never rewritten. Only selected modules are
  written: never `pietto.toml`, an excluded or unselected file, or a file
  outside the root.
- Project errors (no `pietto.toml`, an invalid configuration, a selection that
  matches nothing, a source that cannot be read), and with them each source
  over the size limit (PIE-P1006), are printed as `check --project` prints
  them, with exit 2; no module is formatted.
- New refusals (exit 2):
  - schema_version 1:
    `project error: config_schema: fmt --project needs schema_version = 2 (explicit modules); this project uses schema_version 1. Set schema_version = 2 and declare the names a file uses from another file with import and export. (path: pietto.toml)`
  - schema_version 3 or 4 (N):
    `project error: config_schema: fmt --project needs schema_version = 2 (explicit modules); this project uses schema_version N. Select the package's modules with a schema_version = 2 pietto.toml in the package directory. (path: pietto.toml)`
  - `--write`, a module to replace in a directory it cannot write:
    `PATH: error: source file directory is not writable; the source file was not changed`
- New usage errors (exit 2), each after the line
  `usage: pietto fmt [-h] [--project PROJECT] [--check | --write] [path]`:
  - `pietto fmt: error: --project needs --check or --write`
  - `pietto fmt: error: one of the arguments path --project is required`
    (before: `pietto fmt: error: the following arguments are required: path`)
  - `pietto fmt: error: argument --project: not allowed with argument path`
    and `pietto fmt: error: argument path: not allowed with argument --project`
  - `pietto fmt: error: argument --project: expected one argument`
    (before: `pietto: error: unrecognized arguments: --project`)
  - `pietto fmt: error: argument --project: Project root must be a non-empty path.`
- Text only: `fmt --project` has no `--format json` and is outside CLI JSON v1
  and project CLI JSON v2.
- No diagnostic code, grammar, SQL, JSON document or compiled record changes.

### `fmt` writes one spelling

- `pietto fmt`, with or without `--project`, now writes three spellings one
  way. The program stays the same: `check` reports the same diagnostics
  apart from their positions, and `emit-sql` writes the same SQL on
  PostgreSQL and MySQL. The other spelling stays accepted with no warning;
  only `fmt` rewrites it.

| Rule | Before `fmt` | After `fmt` |
|---|---|---|
| A string takes double quotes | `where status == 'paid'` | `where status == "paid"` |
| A `"` inside it gains a backslash | `'say "hi"'` | `"say \"hi\""` |
| A `\'` loses its backslash, in either quote | `'it\'s'`, `"it\'s"` | `"it's"` |
| A one-line import list loses its parentheses and trailing comma | `from "m.pietto" import (def pos, source rows,)` | `from "m.pietto" import def pos, source rows` |
| A one-line export list, likewise | `export (query q, relationship oc)` | `export query q, relationship oc` |
| An order item loses its `asc` | `order by id asc, name desc` | `order by id, name desc` |
| In a window or an aggregate call too | `window(order by id asc)`, `string_agg(name, ",", order by name asc)`, `last(x, order by k asc, id)` | `window(order by id)`, `string_agg(name, ",", order by name)`, `last(x, order by k, id)` |

- When the `asc` that goes began a line inside parentheses, the line goes if
  nothing else was on it, and a comma right after the `asc` moves to the end
  of the last line before it that is not blank, unless that line ends with a
  comment.
- A list over several lines keeps its parentheses and trailing comma, and
  `desc` stays. `fmt` keeps `table` and `query`, `1_000`, a one-line clause
  and its block, comparison chains and every other trailing comma as written.
- In either quote, `\"` and `\'` stand for the quote itself, so the value of
  a string does not change; [Expressions](language.md#expressions) now says so.
- Compatibility: a file that `fmt --check` accepted under `0.1.9` may now be
  reported as `would reformat: PATH`, and `fmt --write` rewrites it once. Two
  examples of the language reference lose an `asc`. The output of `fmt` may
  still change before the Phase82 freeze; each change is listed in these
  release notes.
- No diagnostic code, grammar, SQL, JSON document or compiled record changes.

### Header lines are refused (PIE-P1000)

- **Compatibility.** A leading `pietto <number>`, `mode ...`, `dialect ...` or
  `encoding ...` line, which warned with PIE-P1012 since `0.1.9`, is now
  retired spelling, as source `is` was: every command and project that parses
  source, dependency packages included, refuses each one with PIE-P1000 in
  every check mode, at the line's keyword, and exits 1. The message is
  ``This spelling is not accepted by the modern syntax.`` followed by the
  suggestion, which the JSON `suggestion` field also carries:
  ``Delete the header line `mode <mode>`; in a single file pass `--check-mode <mode>` instead; a project never applied it.``
  for `mode loose` or `mode strict`,
  ``Delete the header line `dialect <name>`; it has no effect; `emit-sql` takes `--dialect <name>`.``
  for `dialect postgres` or `dialect mysql`, and
  ``Delete the header line `<line>`; it has no effect.`` for any other line
  (`pietto <number>`, `mode checked`, `encoding <name>`, another `dialect`).
  A header line is reported together with the file's other retired spellings,
  in source order.
- **A published dependency package with a header line fails to load.** Its
  modules are refused with the same PIE-P1000, prefixed
  `In dependency package <namespace>/<name>@<version>: `, so the project that
  depends on it is refused. The package must be migrated first
  (`pietto migrate FILE > FILE.new` for each module, then delete any
  `mode loose`/`mode strict` line by hand) and published again.
- `pietto fmt` refuses a file with a header line with the same diagnostics and
  exit 1; its rules for keeping header lines as written are gone.
- `pietto migrate FILE > FILE.new` is otherwise unchanged: it still deletes
  each header line without effect (`pietto <number>`, `mode checked`,
  `dialect`, `encoding`; a comment on the line stays) and refuses
  `mode loose` and `mode strict` with PIE-P1011. The hint in that PIE-P1011
  changes from ``... a project ignores it.`` to
  ``Delete it; in a single file pass `--check-mode <mode>` instead; a project never applied it.``
  (full message: ``The header line `mode <mode>` needs manual migration, as it sets the check mode. Delete it; in a single file pass `--check-mode <mode>` instead; a project never applied it. No migrated source was emitted.``).
  A `pietto 1_0` line, formerly refused by the modern syntax for its digit
  separator, is now one more header line that `migrate` deletes, and, as a
  digit separator anywhere does, it proves the file modern, since 0.1.4 never
  read one: a file whose other lines both syntaxes read keeps its bare types
  (`pietto 1_0` then `id: Int` migrates to `id: Int`; it used to be read as
  0.1.4 source and became `id: Int | None`).
- PIE-P1012 is retired: no source reports it, and the code is not reused.
- `pietto check|explain|emit-sql --help` describes `--check-mode` as
  `check mode (default: checked)` (it no longer mentions a source header).
- **Upgrading.** A source file with a header line no longer checks: run
  `pietto migrate FILE > FILE.new` (or delete the lines); for `mode loose` or
  `mode strict`, delete the line and pass `--check-mode`. A dependency package
  with a header line must be migrated and published again before a project
  that depends on it loads.

### `emit-sql --help` lists the project batch form

- `pietto emit-sql --help` now ends, after the project single-owner form it
  already showed, with the batch form:
  ``Project batch mode: pietto emit-sql --project PATH --all --dialect
  {postgres,mysql} --emission-contract FILE [--module LOGICAL_MODULE] [--kind
  {table,query}] [--name NAME] [--literal-policy {preserve,bind-safe}]
  [--format {text,json}] [--output DIR] emits every matching table and query;
  --output writes a new directory.`` (argparse wraps it to the terminal
  width). Its usage is the one `pietto emit-sql --project ROOT --all --help`
  prints. This closes the 0.1.7 known limitation "`--all` is missing from
  `pietto emit-sql --help`".
- Compatibility: only the text of `pietto emit-sql --help` (stdout, exit 0)
  changes. Argument parsing, the routes `--project` and `--all` select, exit
  codes, usage errors and the project `--help` texts are unchanged.

### Documentation

- Every `pietto` block of `README.md` and `docs/*.md` is now formatted as
  `pietto fmt --check` requires, and `tests/test_repo_docs_examples.py` keeps
  it so. Four blocks changed by blank lines only: no blank line between an
  `import (...)` and an `export (...)` in [project and package](project-package.md),
  and one blank line between two `source` lines in three 0.1.5 examples of the
  release notes. No example's meaning changed.
- New page [Capabilities by mode and target](capabilities.md): for each
  feature family, whether `check` accepts it and `emit-sql` emits it in a
  single file and in an explicit-module project, on PostgreSQL and MySQL,
  with the release note or reference section that states it. README and the language reference
  link it.
- No refusal, diagnostic or SQL changes.

### Editor diagnostics: `pietto lsp` (alpha)

- New command `pietto lsp` (`pietto lsp --stdio` is the same): a language
  server on standard input and output that pushes the diagnostics of the
  `check` stage to an editor, and does nothing else. It uses full document
  sync, UTF-16 positions and document versions, and drops a result that a
  newer edit made stale. Contract and VS Code steps:
  [editor diagnostics](editor-lsp.md).
- Project roots come only from the `projectRoots` initialization option, a
  list of absolute paths of distinct directories; without the option there
  are none, and any other value, two spellings of one directory included, is
  refused with the JSON-RPC error `-32602`. Every module that a root selects
  is published, open or not, and an open file is checked from its unsaved
  buffer. Any other open file is checked like `pietto check FILE`.
- In a `schema_version = 2` project, a module that stops the project check,
  and every module that imports it, is left out and the other modules are
  checked again, in at most five passes. The module that stopped the check
  shows its own errors. A module left out because of what it imports, or an
  import-cycle member without an error of its own, gets one Information
  diagnostic at its import instead: `Not checked: this module imports
  <file>, which has errors.` A root of another schema version, and
  `pietto check --project`, stay all or nothing.
- The server's own messages have no `PIE-` code: two roots select one file,
  one file is open under two URIs, two selected names differ only in letter
  case, a module was not checked, and a partial change. No diagnostic code
  changes, and backend refusals (`PIE-B...`) stay in `pietto emit-sql`.
- An editor buffer is not a trusted read: `emit-sql --project`, compiled
  builds and packages refuse buffer text by type.
- Compatibility: `pietto --help` lists `lsp` after `fmt`. No other command,
  CLI JSON document or compiled record changes.

### Hints that name the rewrite

- Hints for the rules met while writing a demo now name the one rewrite: a
  computed `group by` key (PIE-P1000, and PIE-S2102/PIE-S2329 for a computed
  `let` key in a single file) and an expression around an aggregate
  (PIE-S2310, also as the JSON `suggestion`) name the two-query route,
  `select` the value under a name in one query and group by or compute with
  it in a query that reads it with `from`; an invalid `date_trunc`
  (PIE-S2104) names the quoted units, and an invalid `round` (PIE-S2104)
  names its Decimal digits; a plain `Decimal` source field in project
  emission (PIE-B1004 `validated_decimal_parameters_missing`) says to
  declare `Decimal(p, s)` on the field or its type alias. The single-file
  `let` hints no longer point to an EXPLICIT_MODULES project. Where the
  `Decimal` rule refuses a pair or a sign, PIE-S2105 names that rule, also
  as the JSON `suggestion`, instead of `expected numeric operand(s)`:
  `Decimal` times `Int`, `Decimal` with `Float` under `+`, `-` or `*`, and
  a sign on a `Decimal`, whose text names the rewrite `0 - x` for `-x`. A
  `Decimal` beside a `Text`, `Bool` or `Date` operand, and `%`, keep their
  text. Codes, locations and accepted programs are unchanged.
- Compatibility: only diagnostic text changes. No code, location, ordering
  or accepted program changes. The PIE-S2310 and those PIE-S2105 JSON
  `suggestion`s change from `null` to the new hint; the PIE-B1004
  `suggestion` (text `hint:` line and JSON) changes for one detail.

| Where | Before | After |
|---|---|---|
| PIE-P1000, a `(`, `=`, `+`, `-`, `*`, `/` or `%` that breaks a `group by` clause, e.g. `group by date_trunc("month", d)` (at the `(`) | `Unexpected '('; expected ',' or end of line.` | `Unexpected '('; expected ',' or end of line. ` followed by the hint: `` `group by` lists names: select the value under a name in one query, then group by that name in another that reads it with `from`. `` |
| PIE-P1000, `group by m = x` (at `=`) | ``Unexpected '='; expected ',' or end of line. Compare with `==`; `=` only names a select output, a let binding or a type argument.`` | `Unexpected '='; expected ',' or end of line. ` + the `group by` hint above (replaces the `==` hint there) |
| PIE-P1000, `group by -x` (at `-`) | `Unexpected '-'. A clause lists its items on its header line, or in an indented block after ':'.` | `Unexpected '-'. ` + the `group by` hint above |
| PIE-S2102, single file, a GROUP BY key that names a computed `let` NAME | ``Unknown field: NAME; a query cannot group by a computed `let` value here yet: group by it in an EXPLICIT_MODULES project (schema version 2)`` | `` Unknown field: NAME; a query cannot group by a computed `let` value here yet: select NAME in one query, then group by NAME in another that reads it with `from` `` |
| PIE-S2329, single file, a computed `let` NAME that is a GROUP BY key selected by its own name | ``Let binding conflicts with projection output name: NAME; a query with GROUP BY cannot select a computed `let` value here yet: group by it and select it in an EXPLICIT_MODULES project (schema version 2)`` | `` Let binding conflicts with projection output name: NAME; a query with GROUP BY cannot select a computed `let` value here yet: select NAME in one query, then group by NAME in another that reads it with `from` `` |
| PIE-S2104 `date_trunc` (two arguments; unit not a static `"year"`/`"month"`/`"day"`, or `"hour"`/`"minute"` for a Timestamp; or value not Date/Timestamp) | `Invalid arguments for function date_trunc` | `Invalid arguments for function date_trunc: write date_trunc("month", value) with a Date or Timestamp value; the unit is a quoted "year", "month" or "day", or for a Timestamp also "hour" or "minute"` (a valid unit beside a value of unknown type, such as a refused aggregate, keeps the old text) |
| PIE-S2104 `round` (one or two arguments; value no Decimal or Float, a Float value with digits, or Decimal digits no Int literal from -30 to 30 after `let` expansion) | `Invalid arguments for function round` | `Invalid arguments for function round: write round(value) with a Decimal or Float value, or round(value, digits) with a Decimal value and digits an Int literal from -30 to 30` (a value of unknown type, such as a refused aggregate in `round(avg(x), 2)`, keeps the old text) |
| PIE-S2310 (single file and project) | `Aggregate projection must be a direct aggregate call; composition around NAME() is not supported yet`, `suggestion: null` | same + `` ; select the NAME() under a name in one query, then compute with that name in another that reads it with `from` ``, and that hint as `suggestion` |
| PIE-S2105, `*` of a `Decimal` and an `Int`, either side, also through a type alias (`amount * 2`, `n * amount`; single file and project) | `Invalid operands for operator *: expected numeric operands`, `suggestion: null` | `Invalid operands for operator *: a Decimal multiplies only by a Decimal; Decimal times Int is not supported yet`, and the text after `*: ` as `suggestion` |
| PIE-S2105, `+`, `-` or `*` of a `Decimal` and a `Float`, either side, also through a type alias (`amount + 1.5`, `fl * amount`; single file and project) | `Invalid operands for operator OP: expected numeric operands`, `suggestion: null` | `` Invalid operands for operator OP: a Decimal does not mix with a Float in `+`, `-` or `*` ``, and the text after `OP: ` as `suggestion` |
| PIE-S2105, unary `-` of a `Decimal`, also through a type alias (`-amount`; single file and project) | `Invalid operands for operator -: expected numeric operand`, `suggestion: null` | `` Invalid operands for operator -: a Decimal has no sign operator yet; write `0 - x` for `-x` ``, and the text after `-: ` as `suggestion` |
| PIE-S2105, unary `+` of a `Decimal`, also through a type alias (`+amount`; single file and project) | `Invalid operands for operator +: expected numeric operand`, `suggestion: null` | `` Invalid operands for operator +: a Decimal has no sign operator yet; write `x` for `+x` ``, and the text after `+: ` as `suggestion` |
| PIE-B1004 `validated_decimal_parameters_missing` (project emission, a source field declared plain `Decimal`, also through a type alias) | hint `Keep this expression in check/plan, or select a direct field with a reviewed carrier: the compiler lacks the required proof. Do not invent a range, meaning or bound in the contract.` | hint `Declare this field, or the type alias it uses, as Decimal(p, s) with the precision and scale of its column, such as Decimal(12, 2); a plain Decimal has none to match the contract.` |

### Known limitations of 0.1.10

- **MySQL refusals.** MySQL support trails PostgreSQL: a form opens on MySQL
  only after a two-database differential passes, and until then MySQL
  emission refuses it with a PIE-B code and writes no SQL. These forms of
  this release are refused on MySQL:
  - in single files and projects: `median` and `quantile` (MySQL has no
    interpolated percentile), `now()`, the conditional sum
    `sum(o.f for o in group if ...)`, `string_agg` (`GROUP_CONCAT` truncates
    silently), and `first` and `last`;
  - in single files: top-level constants; `stddev`, `variance`, `pvariance`
    and `pstdev` of an `Int`; a window key that names a computed `Text`
    `let`; and an asof JOIN in a relation with a FULL JOIN;
  - in projects: the conditional count; `Decimal(p, s)`, `Date`,
    `Timestamp` and `UUID` query parameters; aggregate windows; `lpad`,
    `add_months` and `concat`; `Int` arithmetic not proved to fit signed 64
    bits; `sum` and `stddev` of an `Int`; `count_distinct`, `sum`, `avg` and
    `stddev` of a `Float`; `variance`, `pvariance` and `pstdev`;
    `count_distinct(a, b, ...)`; `any` and `all` over a group; and collected
    lists and nested keys (Phase77).

  The other MySQL project refusals stay; "Kept refused on MySQL" under
  [MySQL catch-up in projects](#mysql-catch-up-in-projects) lists them.
- Window forms of `variance`, `pvariance`, `pstdev`,
  `count_distinct(a, b, ...)`, `first` and `last` are refused, and
  `any(... for o in group)` and `all(... for o in group)` take no window.
  The conditional count and sum, `any`, `all`, `first` and `last` over JOIN
  rows are refused (PIE-S2334): join in one query, then group it in another
  that reads it with `from`.
- `def` and `relationship` items in a package module (PIE-S2707), wildcard
  imports, `constraint` and `derive` import and export items, and qualified
  calls such as `a.pos(x)` are refused. In a project,
  `any(R(x, c) for c in q)` over a query `q` that has a JOIN keeps
  PIE-S2604 (write the `on` out); a table with a set-operation or VALUES
  body is not a row for a relationship parameter; and `Decimal` precision
  and scale are not compared when a column binds a relationship field.
- A project query whose WHERE calls a def that inlines to a conditional
  cannot be read through a JOIN by another project query: that JOIN query is
  BLOCKED (PIE-B1003) on PostgreSQL. Read it with `from` alone.
- A project FULL or CROSS JOIN is BLOCKED (PIE-B1003
  `scalar_meaning_requires_field_projection`) on both targets when an input
  of the relation has a `Timestamp` or `UUID` field, even one it does not
  read. INNER, LEFT and RIGHT JOINs are not affected.
- A project `count() window()` with an empty `window()` (no argument,
  partition or order key) passes `check --project`, but
  `emit-sql --project` refuses it (PIE-B1004 `window_result_anchor_missing`),
  and likewise a project aggregate window with a RANGE offset frame
  (PIE-B1002).
- `max(a, b)` and `min(a, b)` of two numeric types, such as an `Int` and a
  `Float`, are refused (PIE-S2104), and six or more nested values stop at
  PIE-S2399; a project `max(a, b)` of two `Date` or two `Bool` values is
  refused (PIE-B1003). `add_months` takes a `Date` only.
- In a project, `len`, `sum` and `any` over a row's collected list are
  available only in a table or query without JOIN, GROUP BY, an aggregate,
  DISTINCT, a window or QUALIFY: select the list in one query and read it in
  a later one.
- A project relation with aggregates and no JOIN input that reads a `let`
  name or a query parameter still reports some aggregate, grouping and ORDER
  BY errors as the bare PIE-S2333, as in `0.1.9`. Beside a `let` and
  projection name conflict (PIE-S2329), a `schema_version = 2` project can
  report other diagnostics than a single file where an `order by` key of
  `first` or `last`, a `count_distinct` or a `stddev` reads the refused
  `let`.
- `0 - x` of a `Decimal`, the rewrite that PIE-S2105 names for `-x`, passes
  `check`, but project `emit-sql` refuses it, as it refuses every `Decimal`
  and `Int` pair (PIE-B1003 `arithmetic_requires_signed_int_operands`).
- `pietto lsp` publishes only the diagnostics of `check`: no backend
  refusal (`PIE-B...`), hover or completion, and no root discovery (roots
  come only from `projectRoots`). A root nested inside another root through
  a symbolic link publishes its modules under both spellings without the
  overlap message. The VS Code acceptance did not run on native Windows
  Python, a Remote WSL session or macOS.
- `explain --project` lists no source columns and no schema-4 columns, and a
  relation with an untyped `None` output fails the whole document.
  `pietto.compiler` has no executable batch `compile_queries(...)` and no
  single-file entry.
- `fmt --project --write` replaces the modules one at a time: a write
  failure that its checks before writing cannot predict leaves the earlier
  modules replaced. `fmt` has no partial formatting, line width or style
  option.
- The known limitations of 0.1.9 that the subsections above do not change
  still hold; the asof JOIN is no longer PostgreSQL only (see
  [Asof JOIN on MySQL](#asof-join-on-mysql)).

## Equality, nullability and asof JOIN public alpha release notes — 0.1.9

<a id="unreleased-changes-following-018"></a>
<!-- The id above keeps links written before these notes were released pointing here. -->

**Status:** These notes cover `0.1.9`, the public alpha prepared from its
release commit, the last commit of Phase72 batch 2. It is published only when
the tag `v0.1.9`, the versioned GitHub pre-release and PyPI carry its
accepted wheel and sdist; this document neither creates those channels nor
substitutes for their byte verification. As for earlier releases, the
compiler and package are covered on CPython 3.12 and 3.13 for Linux x86-64;
other platforms and Python versions are not.

`0.1.9` retires no source spelling of `0.1.8`. It is the Phase72 release:
both Phase72 batches, the formatter step `pietto fmt` and a warning on the
header lines that Phase75 removes. It adds `pietto fmt`, the builtins
`concat`, `same_value` and `stddev`, project typing of always-null numbers,
fewer false JOIN fan-out refusals, one `Float` value contract and the backward
asof JOIN. Each subsection below lists the changes against `0.1.8` that a
program can observe and the new refusals; the last one lists the known
limitations. The Python execution extras keep the pins of `0.1.8`. The
sections from 0.1.8 down describe published files.

### Highlights

- **`pietto fmt`.** One command lays out a file in the one canonical form:
  `pietto fmt PATH` prints it, `--check` tells whether a file is formatted,
  `--write` replaces it. Only whitespace between tokens changes.
- **New builtins.** `concat(a, b, ...)` joins `Text`; `same_value(a, b)` is
  equality that treats two `None` as equal and is never `None`; `stddev(x)` is
  the sample standard deviation, as Python's `statistics.stdev`.
- **Backward asof JOIN on PostgreSQL.** `asof left join` and
  `asof inner join` keep, for each row, the latest matching row at or before
  its time, as pandas `merge_asof` does.
- **`Float` has one meaning.** A finite binary64 value whose equality is
  Python's, so `-0.0 == 0.0`; PostgreSQL project SQL now groups, orders and
  removes duplicates of `Float` values.
- **Fewer false refusals.** Sound JOIN aggregates, a JOIN on all the GROUP BY
  keys of a grouped query, and project arithmetic with an always-`None`
  operand now check, and an always-null project output no longer hides later
  errors.

### Upgrading from 0.1.8

- `0.1.9` retires no source spelling, so a `0.1.8` file needs no
  `pietto migrate` step. Each header line now warns with PIE-P1012, and
  `pietto migrate FILE > FILE.new` deletes the ones without effect; for
  `mode loose` or `mode strict`, delete the line and pass `--check-mode`.
- `same_value` and `stddev` are reserved: a `def` with either name is
  PIE-S2398. A file's own `concat` keeps its meaning.
- Tools that compare exact diagnostics, SQL text or JSON must expect the
  changes listed below: the new PIE-P1012 and PIE-S2385 warnings, new and
  changed hint texts, the typed NULL casts in single-file SQL, and additive
  JSON vocabulary that strict readers must accept.
- As with every release, compiled bundles and saved jobs made under `0.1.8`
  or earlier are refused by code identity.
- The output of `pietto fmt` may still change before the Phase82 freeze;
  each change is listed in these release notes.
- The VS Code extension `0.1.0` accepts only the `0.1.2` wheel and refuses
  `0.1.9`; the extension is set aside until the work before Phase75 is done.

### Formatter: `pietto fmt`

- `pietto fmt PATH` writes the formatted source of one file to stdout and
  never changes the file. `pietto fmt --check PATH` never writes: it exits 0
  when the file is formatted, and 1 with `would reformat: PATH` on stderr when
  it is not. `pietto fmt --write PATH` replaces the file atomically, only when
  formatting changes it, and keeps its permission bits. `--check` with
  `--write`, a directory, `--project` and `--format` are usage errors
  (exit 2). There is no configuration.
- `fmt` changes only the whitespace around tokens, never a token, its order
  or the spaces between two tokens of a line (`a -- b` still reports
  PIE-P1009): four-space blocks; a continuation line inside parentheses keeps
  its indentation relative to the line it continues; a comment line takes the
  indentation of the line that follows it in its block; two spaces before an
  end-of-line comment; one blank line between top-level declarations, none
  between consecutive imports and exports; the comment lines at the left
  margin over a declaration belong to it; comment lines that no declaration
  follows keep their written blank lines, one at most in a row; no trailing
  whitespace; every line ends with the file's first line ending and a
  non-empty file ends with one; a leading BOM and the header lines (`pietto`,
  `mode`, `dialect`, `encoding`) are kept as written.
- The result is lexed again and must give the input's tokens, blocks, logical
  lines, code and comments; otherwise, or when it would exceed the source size
  limit, `fmt` prints and writes nothing and exits 1. A file with parser
  errors is refused with the diagnostics `check` reports and exit 1, also with
  `--check` and `--write`. `--write` refuses with exit 2 a symbolic link or a
  file that is not regular, before reading it, and, when the file needs
  changing, a read-only file, a file owned by another user, a file whose bytes
  changed after it was read, or a failed replace.
- No diagnostic code, JSON shape, SQL output or existing command changes. The
  `pietto` code blocks of `README.md`, `docs/language.md` and `docs/style.md`
  are now in this layout, and `tests/test_repo_docs_examples.py` keeps them
  so.

### `concat` joins Text

- `concat(a, b, ...)` takes two or more `Text` values (a `Text` alias
  included, also one imported from another module) and is `None` when any
  argument is, in `check`, single-file `explain`, `emit-sql` and
  `emit-sql --project`. One argument or a non-Text argument is PIE-S2104
  (`Invalid arguments for function concat: expected at least 2, got N`,
  `Invalid argument type for function concat at position P: expected Text,
  got X`); write `Text(n)` for an `Int`.
- PostgreSQL SQL, single file and project, is `(a || b)`; in a single file an
  argument not known to be `Text`, such as a field of a source without a
  shape, is `CAST(x AS text)`. Single-file MySQL SQL is `CONCAT(a, b)`.
- Project SQL refuses, on PostgreSQL, `concat` of only `None` (PIE-B1003
  `scalar_call_signature_not_admitted`) and of a binding-width `Text` (new
  detail PIE-B1004 `text_concat_result_bound_missing`), and on MySQL every
  `concat` (PIE-B1003 `scalar_call_signature_not_admitted`, at the statement
  part that holds the call, also through a `def`).
- **Diagnostic text changes.** The PIE-P1000 hint for `||` is now ``Write
  `concat(a, b)` to join Text, or `or` for a condition.``; PIE-S2103 for
  `CONCAT(...)`, `Concat(...)` and other non-lowercase spellings now hints
  ``write `concat(...)` in lowercase``; PIE-S2105 for `+` with a `Text`
  operand now ends ``; use `concat(...)` to join Text values`` beside a
  `Text`, the null literal or a number of unknown type, ``; use `concat(...)`
  with `Text(n)` to join Text values`` beside an `Int`, and at `expected
  numeric operands` beside another type.
- **A file's own `concat` keeps its meaning.** A `def concat` (still
  accepted, not PIE-S2398), or a `constraint`, `derive` or relationship
  template named `concat`, keeps its `0.1.8` meaning in its own file, and in
  every file of a `schema_version = 1` project; there the messages above keep
  their `0.1.8` text. A callable that only another module declares does not
  hide the builtin, so a module's `concat(a, b)` that `0.1.8` reported as
  PIE-S2103 is now the builtin.

### `same_value`: NULL-safe equality

- `same_value(a, b)` is a `Bool` that is never `None`: true when both
  operands are `None` or equal, false when only one is `None`. Its operands
  compare as for `==`. PostgreSQL SQL is `(a IS NOT DISTINCT FROM b)`, MySQL
  SQL `(a <=> b)`, in `select`, `where`, `let`, conditions and JOIN `on` in
  single files, and in explicit-module project checks. Project SQL admits it
  in a relation's select items, WHERE and `let`, and in select items after a
  JOIN, on both targets.
- **Compatibility.** `same_value` is now a reserved builtin name: a
  `def same_value(...)` is PIE-S2398 (``Def same_value has the name of a
  built-in function; a def cannot shadow one``), so its project `emit-sql`
  documents go from VERIFIED to BLOCKED and `emit-sql --all` fails the batch
  with no items. A call is no longer PIE-S2103.
- **New refusals.** A `None` argument, also through a `let` name or a `def`
  argument, is PIE-S2104 ``Invalid argument type for function same_value at
  position N: expected a non-None value, got None; write `x is None`
  instead`` (no hint when both are `None`); operands that `==` refuses are
  PIE-S2104 `Invalid argument types for function same_value: expected
  comparable operands`; a wrong count is PIE-S2104 `expected 2, got N`. On
  PostgreSQL a single-file `same_value` beside a CASE/`coalesce`/`nullif` of
  only `None` warns PIE-S2385 at check and is refused at emission, as `==`
  is. Project SQL admits `Float` operands exactly where `==` admits them
  (on MySQL only beside an operand that reads no row) and refuses `Bool`
  operands and `same_value` in a JOIN `on` or in a WHERE or `let` after a
  JOIN (also as a GROUP BY key there) with the existing PIE-B1003 details.

### Always-null numbers in projects (D-12)

- In an explicit-module project an always-null number (`amount + None`,
  `None * 2`, `None - 3.0`) is typed as in a single file, the widest-type
  rule included (`(None + d) + 1.5` is a `Float`), so its relation completes
  where `0.1.8` reported the bare PIE-S2333, and the relations that read it
  report their own errors. A `schema_version = 1` project takes the same
  widest-type rule: such programs that failed with PIE-S2104 or PIE-S2105
  there now pass.
- A relation without a JOIN input of its own and without `select distinct`
  that selects an untyped NULL (`o = None`, `-None`, `None + None`), or a typed
  output that reads one (`coalesce(None, None) == amount`, `n is None` after
  `let n = None`), now completes with a PIE-S2385 warning at that output,
  which every emission document of the project also carries; project SQL
  refuses it with PIE-B1003 `expression_evidence_unavailable`.
- **SQL changes.** Single-file SQL writes a `None` operand of `+`, `-`, `*`,
  `/` or `%` as a typed NULL (PostgreSQL `CAST(NULL AS bigint|numeric|double
  precision)`, MySQL `CAST(NULL AS SIGNED|DECIMAL|DOUBLE)`), also in WHERE,
  `sign`/`abs`, comparisons, `coalesce`/`nullif`, conditionals, a `let` name
  bound to `None` and a `None` argument inlined from a `def`; it casts an
  always-null `Int` or `Decimal` operand beside a `Float` result to `double
  precision` / `DOUBLE`; MySQL divides `amount / None` with `DIV`. This
  changes the SQL text of every program with such an expression: `0.1.8`
  typed PostgreSQL `NULL * 2` as `integer` and `NULL - 3.0` as `numeric`, and
  MySQL `amount + NULL` as `DOUBLE`.
- Project SQL now emits `Int` arithmetic with a `None` operand on PostgreSQL
  and MySQL (`("s0"."amount" + CAST(NULL AS pg_catalog.int8))`), in the
  target's `Int` carrier with `int_range` 0..0, wherever it is read: a `let`
  value and a GROUP BY key over it, a JOIN output, a WHERE condition,
  `sign`/`abs`, comparisons, `coalesce`, conditionals, an `in` list, a grouped
  aggregate (MySQL `sum` keeps PIE-B1004
  `sum_int_aggregate_range_proof_missing`) and a `union all` branch. Its
  compiled bundle now emits and builds a live template, where `0.1.8` raised
  `COMPILED_NULL_CONTEXT`. Emission observations gain the additive `ranges`
  roles `expression_range` `null_cast` and `syntax` `null_cast_open`,
  `null_cast_close`. `Float` and `Decimal` arithmetic with a `None` operand
  and arithmetic over a `let` name bound to `None` stay refused.
- **Fixed crash.** Project SQL of `o = abs(None)` crashed with
  `KeyError: 'precision'` on both targets (also in `0.1.7`). A visible output
  whose value or window result is that precision-less `Decimal` typed NULL is
  now BLOCKED PIE-B1003 `scalar_call_signature_not_admitted` at the output
  item, also through a `let` name, ORDER BY, LIMIT, a named relation or a
  `def`. Every reader of it that `0.1.8` emitted (`abs(None) is None`,
  `coalesce(abs(None), price)`, `sign(abs(None))`, ...) emits the same
  document, and every form `0.1.8` refused keeps its blockers, with that
  PIE-B1003 added in source order when the relation also has such an output.
- Unchanged: comparisons with `None` and `label + None` stay PIE-S2105, and
  `sum(None + amount)` stays PIE-S2315.

### JOIN aggregates: fewer false fan-out refusals

- Single files (PIE-S2381) and explicit-module projects (PIE-S2333) now
  accept, and emit as one grouped JOIN: `min`, `max` and `count_distinct` over
  any JOIN; `count`, `sum`, `avg` and `stddev` of a field of the many side
  of a LEFT JOIN (or the same RIGHT JOIN) whose `on` matches the other side's
  unique key, and of a further LEFT JOIN on that side; the anti-join
  `where orders.id is None` after such a JOIN when the tested field is never
  `None`; and a JOIN on all the GROUP BY keys of a named grouped query.
- Real fan-out stays refused: `sum`/`count`/`avg`/`stddev` over a JOIN that
  repeats rows, an anti-join on a field that may be `None` or under `or`,
  `is not None`, a JOIN on only part of a grouped query's keys, and a
  hand-written WHERE equality.
- The PIE-S2381 message no longer asks to match a unique key that the `on`
  already matches: for a LEFT or RIGHT JOIN it says ``read no row that JOIN
  NAME keeps without a match``, and where only a FULL JOIN's `on` matches it
  names only the other remedies. MySQL project SQL keeps refusing `sum(Int)`
  with PIE-B1004.

### `Float` value contract

- `Float` has one meaning in both modes: a finite IEEE-754 binary64 value
  whose equality is Python's float equality, so `-0.0 == 0.0`. Single-file SQL
  bytes are unchanged.
- `check --project` accepts `select distinct` over `Float` values and UNION
  DISTINCT, INTERSECT and EXCEPT over `Float` columns; PIE-S2339 and PIE-S2344
  no longer report them, and their message tail "Float equality is not
  supported yet" is retired.
- PostgreSQL project SQL admits same-carrier finite `Float` comparisons in
  WHERE, SELECT, `let`, HAVING, QUALIFY, INNER and LEFT JOIN `on` and
  correlated predicates, and `Float` GROUP BY, DISTINCT, ORDER BY and every
  set form, a window `percent_rank`/`cume_dist` result included in
  comparisons. Each merged row carries the value of some member of its class,
  so a key whose class holds both zeros may show either sign.
- MySQL project SQL admits `Float` comparisons with a literal or a header
  parameter and every ordering inequality. `Float` GROUP BY
  (`group_key_type_outside_reviewed_comparison_domain`), relation ORDER
  (`order_comparison_domain_unsupported`) and `==`/`!=` between two row reads
  (`comparison_type_pair_not_admitted`) keep their PIE-B1003 blockers;
  `Float` DISTINCT, UNION DISTINCT,
  INTERSECT and EXCEPT are BLOCKED at emission with
  `distinct_field_comparison_domain_unsupported` or
  `set_row_equivalence_domain_unsupported` (real MySQL 8.4.12 kept `-0.0` and
  `0.0` apart beside a wide key).
- **Compatibility.** No VERIFIED `0.1.8` document changes bytes. Some
  refusals move: a MySQL `Float` DISTINCT or equivalence set form, and those
  forms over a window distribution result on both targets, pass the check and
  are BLOCKED by emission with one PIE-B1003 and no diagnostics (two on MySQL
  when the only inputs are typed VALUES bodies, the second
  `zero_physical_source_not_admitted_on_target`); a FULL JOIN whose `on`
  compares a `Float` is now refused by the FULL JOIN rule (subject reference
  `join`: PostgreSQL `full_join_equality_outside_reviewed_int_domain` or a
  shape detail, MySQL `mysql_full_join_approved_non_support`, except MySQL
  `==`/`!=` between two row reads, which keeps
  `comparison_type_pair_not_admitted`); and every FULL JOIN rule refusal now
  carries the location of the JOIN's `on` clause, for every type, on both
  targets. The suggestion of `set_row_equivalence_domain_unsupported` names
  the per-target limits.
- Still refused: `Float` beside `Int` (`price > 1`; write `1.0`), `Float`
  field arithmetic, unary minus on a field, `/` and `%`, `Float` `sum`, `avg`,
  `count`, `count_distinct`, `min` and `max`, a window PARTITION or ORDER BY a
  `Float`, a FULL JOIN on a `Float` equality, and DISTINCT, GROUP BY, ORDER and
  equivalence set forms over a window distribution result.

### `stddev` aggregate

- `stddev(x)` is the sample standard deviation (Python `statistics.stdev`)
  of a direct `Int` or `Float` field: a nullable `Float`, `None` below two
  values. PostgreSQL SQL is `SQRT(CAST(VAR_SAMP(x) AS double precision))`
  (project: `pg_catalog.float8`), VERIFIED in projects for `Int` and, with the
  new evidence token `target_checked_binary64_overflow`, for `Float`.
  Single-file MySQL SQL is `STDDEV_SAMP(x)` for a `Float`.
- **New refusals.** MySQL `stddev` of an `Int` is refused in both modes
  (single file PIE-B1000, project PIE-B1003
  `stddev_int_not_admitted_on_target`); MySQL project `Float` `stddev` is
  PIE-B1004. Over a JOIN that repeats rows it is PIE-S2381, as `sum` is, and
  where `sum` is accepted after a JOIN it is too.
- **Compatibility.** `def stddev` is now PIE-S2398 (``Def stddev has the name
  of a built-in function; a def cannot shadow one``) with the suggestion
  ``Rename this def: `stddev` is now the built-in sample standard deviation
  aggregate, and a call to stddev always means it.``; a `constraint stddev` or
  `derive stddev` called as `stddev(...)`, which was PIE-S2103, now means the
  aggregate. In a single file, the refusal of a non-window aggregate with a
  `window`, `count_distinct` included, gains the suffix `; window aggregates
  are sum, count, avg, min and max`, unless the relation admits no such
  window; a project keeps the text without a suffix.
- PIE-S2103 hints (the lookup ignores letter case): `stdev`, `stddev_samp` and
  `statistics.stdev` hint ``write `stddev`, the sample standard deviation
  (Python `statistics.stdev`)``; `std`, `pstdev`, `stddev_pop`,
  `statistics.pstdev` and `stddev` in a letter case other than lowercase say
  that the population deviation is not available; the aggregate list of the
  other hints now names `stddev`.
- PIE-S2103 hints: `in_range` hints ``write the half-open range
  `a <= ts < b` `` and `ranges_overlap` hints ``write `a_start < b_stop and
  b_start < a_stop` ``.
- Project JSON v2 gains the additive syntax roles `aggregate_root_open` and
  `aggregate_root_close`, the aggregate spelling `VAR_SAMP` and the evidence
  token `target_checked_binary64_overflow`; a strict reader of those
  vocabularies must accept them. Semantic metadata artifact v1 records no
  `stddev` call.

### Backward asof JOIN (PostgreSQL)

- `asof left join price on orders.product_id == price.product_id and
  orders.ordered_at >= price.valid_from` keeps, for each order, the latest
  price at or before its time (pandas `merge_asof`: backward, exact matches
  allowed); `asof inner join` drops the orders without one. The `on` is zero
  or more `==` keys, then one `>=` time test, each written earlier input
  first, on one line without parentheses; both times are `Date` or both
  `Timestamp`, and no key is a `Float`. The joined input is a source whose
  shape declares a `unique(...)` within the keys and the time, so the latest
  row is one row; Pietto never picks one of several tied rows. A `None` key
  or time matches nothing. Single files and explicit-module projects check it
  with the same rules and messages, except that a project reports a JOIN
  without `on` as PIE-S2333 and refuses an asof JOIN beside nested fields
  (below).
- **SQL.** Single-file PostgreSQL SQL is `LEFT JOIN LATERAL (SELECT * FROM
  <source> AS <b> WHERE <on> ORDER BY <b>.<time> DESC LIMIT 1) AS <b> ON
  TRUE` (`INNER JOIN LATERAL` for `asof inner join`). Project SQL is the JOIN
  with `AND (NOT EXISTS (...))` of a later matching row in its `ON`, in a
  table or query without a relation `let NAME:` block whose FROM is not a
  table function; compiled bundles and live templates replay that SQL. On
  PostgreSQL 18.6, 34 single-file and 30 project statements returned the rows
  of a reference implementation, and 7 of 7 mutated statements were caught.
- The JOIN repeats no earlier row: in a single file `sum(orders.x)` after an
  asof JOIN is accepted, and an aggregate of a joined field stays PIE-S2381.
  A project accepts an aggregate after an asof JOIN only where the `on` keys
  match a unique key of the joined source, as for any JOIN.
- **New refusals.** New PIE-S2386, at the JOIN, when the joined input cannot
  have one latest row: ``asof JOIN joins only a source: one latest row is
  proved by the source shape's unique(...).`` for a table, query or
  `let NAME:` block, and ``Several rows of price may be the latest for one
  orders row; Pietto does not pick one.`` followed by the `unique(...)` to
  declare or the key to match. An asof JOIN without `on` is PIE-S2335 in a
  single file and the cause of PIE-S2333 in a project, with a new text:
  `` JOIN price: write `on` with the keys, then one time test: `on
  orders.k == price.k and orders.t >= price.t` ``. PIE-S2336 refuses another
  kind (``ASOF JOIN is `asof left join` or `asof inner join`.``), a second
  asof JOIN in one query
  (``One asof JOIN per query: move the first into its own query and `from`
  it.``), a missing, strict, reversed, forward, misplaced or second time
  test, a repeated key, a chain, time arithmetic, a validity range, any other
  condition, a bare field name, mixed `Date` and `Timestamp` and a `Float`
  key, with a rewrite where one exists. A project also refuses, with
  PIE-S2336, an asof JOIN in a query with `collect` or `unnest` or whose
  earlier input has a nested-relation field (``Do the asof JOIN in a query
  with only flat fields first.``). PIE-P1000
  refuses `left asof join`, `asof join`, an `as` alias, `by` keys and an `on` that is
  broken over lines or in parentheses, with the asof form as its hint. MySQL
  refuses every asof JOIN: single file PIE-B1000 (``... MySQL has no ASOF
  JOIN yet; emit with --dialect postgres``), project PIE-B1003
  `asof_join_not_admitted_on_target`.
- **Compatibility.** `asof` is a new soft keyword of the generated parser; it
  stays a valid name elsewhere (`select asof = orders.id`). A relation-body
  line that starts with `Asof` now ends its PIE-P1000 with ``Keywords are
  lowercase: write `asof`.``, as for the other keywords. After an
  `asof left join`, PIE-S2383 names the asof remedies (test the chosen row
  in `select`, or write `asof inner join`). When only asof JOINs repeat the
  rows an aggregate reads, PIE-S2381 offers only `any(...)` or a separate
  query, not a key match in `on`.

### Header lines warn (PIE-P1012)

- **Compatibility.** Each leading `pietto <number>`, `mode ...`, `dialect ...`
  or `encoding ...` line now reports a new WARNING, PIE-P1012
  (``The header line `<line>` is deprecated and will be removed.`` followed
  by its hint), in every check mode, once the source parses, in every command
  and project that parses source, dependency packages included, except
  `migrate` (`emit-sql --project` only in a document refused before semantic
  analysis, as for PIE-P1009). Exit codes, `ok` and every other diagnostic are
  unchanged, but tools that compare exact diagnostics must expect it. Phase75
  removes the header syntax.
- `pietto migrate FILE > FILE.new` now deletes each header line without
  effect (`pietto <number>`, `mode checked`, `dialect`, `encoding`; a comment
  on the line stays), also from a source that it returned byte for byte in
  `0.1.8`, and refuses `mode loose` and `mode strict` with PIE-P1011
  (``The header line `mode <mode>` needs manual migration, as it sets the
  check mode.``): delete the line and pass `--check-mode` instead.

### Known limitations of 0.1.9

- MySQL project SQL refuses `concat`: real MySQL 8.4.12 types a `CONCAT`
  result from its arguments' storage lengths and counts the literal anchor
  that project SQL writes by its UTF-8 bytes, so the declared width does not
  hold. MySQL project `REPLACE` and the other Text calls whose result can grow
  have the same typing and are still emitted as in `0.1.8`; a MySQL project
  `replace` wider than the 16383-character bound stays the generic PIE-B1003.
  Single-file MySQL `CONCAT` returns NULL above `max_allowed_packet`.
- MySQL project SQL of `union distinct`, `intersect distinct` and
  `except distinct` over a `same_value` column is VERIFIED but was not run on a
  database. `same_value` is not emitted in a project JOIN `on` or in a WHERE
  or `let` after a JOIN (also as a GROUP BY key there), `having:` admits no
  call, a header parameter cannot be its operand (PIE-S2355), and on MySQL a
  `Text` operand relies on the `utf8mb4_0900_bin` collation premise. Project
  SQL admits a `Float` `same_value` exactly where it admits a `Float` `==`:
  on PostgreSQL, and on MySQL only beside an operand that reads no row
  (`same_value(ratio, 1.5)` is emitted with `<=>`; a MySQL `same_value` of
  two row `Float` operands is PIE-B1003 `comparison_type_pair_not_admitted`,
  as their `==` is).
- Project typing of untyped NULL values still fails with the bare PIE-S2333
  in a relation with a JOIN input of its own whose output has no type or reads
  one through a `let` name, a `select distinct` relation whose output has no
  type, a relation that computes with, groups by, aggregates or JOINs an
  untyped output it reads, a SELECT output with no type that is not always
  NULL (`abs(amount + (-None))`), and a relation with a `Decimal` quotient
  output; a relation that passes an untyped output through and has an invalid
  LIMIT still reports PIE-S2333 in place of PIE-S2307. A project places
  PIE-S2385 at the output, a single file at the value. Single-file SQL writes
  a `Decimal` typed NULL without precision.
- MySQL single-file GROUP BY of a `Float` beside a wide `Text` key can put
  `-0.0` and `0.0` in different groups.
- The asof JOIN is PostgreSQL only; MySQL refuses it in both modes. One asof
  JOIN per query, and no lower bound, tolerance, forward or nearest
  direction, strict `>` or validity range. A project emits it only in a table
  or query without a relation `let NAME:` block whose FROM is not a table
  function; elsewhere (a set or VALUES input in a `let NAME:` block, an
  asof JOIN inside a `let NAME:` block, a query with any other relation
  `let NAME:` block, a table-function FROM) the JOIN gets its own checks and
  then `asof JOIN is not available in projects yet.` (PIE-S2336); a
  `let NAME:` block as the joined input is PIE-S2386, as it is no source. A project
  refuses an aggregate after an asof JOIN (PIE-S2333) unless the `on` keys
  match a unique key of the joined source, where a single file accepts an
  aggregate of earlier fields: aggregate in a query that reads it with
  `from`. The project SQL pairs each earlier row with every joined row of its
  keys at or before its time and tests each pair with `NOT EXISTS`, so on a
  long history it costs more than the single-file SQL; an index on the joined
  table's keys and time makes each test one index lookup. The `unique(...)`
  that proves one latest row is trusted, not checked
  at run time: on data that breaks it, single-file SQL returns one of the
  tied rows and project SQL returns each of them.

## Project-mode quality public alpha release notes — 0.1.8

<a id="unreleased-changes-following-017"></a>
<!-- The id above keeps the links of the 0.1.7 notes below, written before these notes were released, pointing here. -->

**Status:** `0.1.8` was published from `61b05586` (tag `v0.1.8`) on the
versioned GitHub pre-release and PyPI channels. These historical release notes
neither publish a successor nor substitute for channel byte verification.
As for earlier releases, the compiler and package are covered on CPython 3.12
and 3.13 for Linux x86-64; other platforms and Python versions are not.

`0.1.8` retires no source spelling of `0.1.7`. It is `main` at `d654738f`
with only version and documentation changes: the project-mode quality
interlude that the [0.1.7 notes](#rescheduled) scheduled, that is, its first
batch `8cebe779` and PMS-2 `d654738f`. It changes the diagnostics that a
project reports and what `explain --project` lists, with one exit status of
`explain --project`, and it checks large projects faster, as described below.
On the programs whose SQL was compared with `0.1.7`, named under F5 and under
Measured output below, the SQL of the first batch is byte-identical to that
of `0.1.7`, and PMS-2 changed no exit status, stdout or stderr on the project
command invocations compared with the first batch. Every change but PMS-2
came in the interlude's first batch. The Python execution extras keep
the pins of `0.1.7`. The sections from 0.1.7 down describe published files.

### Highlights

- **Project diagnostics closer to a single file.** In an explicit-module
  project, a JOIN relation that a single file refuses with PIE-S2312 because
  it mixes an aggregate with another projection and has no GROUP BY (for
  example a JOIN query whose `select:` has `customer_id` and `n = count()`
  but no `group by`) now also reports what a single file reports beside it,
  unless its `let:` clause or WHERE is refused, and a repeated SELECT output
  name reports more as a single file does. Only relations that already report
  an error change, so a program that checks still checks.
- **`explain --project` lists the dependencies' diagnostics after a root
  parse failure.** When the root's pin check passes and a root module then
  fails to parse, the dependencies' diagnostics follow the root's, and in one
  case it now exits 2 instead of 1 (see
  [Upgrading from 0.1.7](#upgrading-from-017)).
- **Faster project checks.** With the first batch, one module with 600 tables
  checks in about 5.2 s where `0.1.7` took 13 s, and one query with 120 JOINs
  in about 11 s where `0.1.7` took 31 s. With the import-cycle change
  (PMS-2), a 160-module import cycle is reported in about 2.7 s and 108 MiB,
  against 103 s and 3,075 MiB on the first batch (the first batch was
  measured again beside PMS-2 on a shared machine; the `0.1.7` notes give
  71 s for 160 modules from an earlier measurement). The [Performance](#performance) section gives how these
  times were measured; they are no performance promise.
- **Documented rules.** An exactly repeated environment premise of an
  emission contract is now a documented rule, and the language
  reference no longer describes the PostgreSQL `sum` of a `bigint` column as
  `numeric`. Both change documentation only.

### Upgrading from 0.1.7

- 0.1.8 retires no source spelling, so a 0.1.7 file needs no `pietto migrate`
  step.
- Some project diagnostics change, only for relations that already report an
  error: in an explicit-module project, a mixed aggregate JOIN relation
  refused with PIE-S2312 and a repeated SELECT output name report more of
  what a single file reports (for such a JOIN relation `0.1.7` reported
  PIE-S2312 alone, or a bare PIE-S2333 when the only other projection was a
  window), and an unknown QUALIFY name in such a mixed
  aggregate JOIN relation is PIE-S2102; in an explicit-module or LEGACY_FLAT
  project, a repeated unknown bare name outside a JOIN reports PIE-S2102 only
  at its first item. A tool that compares the exact diagnostics of such a
  project with those of `0.1.7` must expect these changes; see
  [Project diagnostics](#project-diagnostics).
- `explain --project` now lists the dependencies' diagnostics after a root
  module that fails to parse once the root's pin check passes. When the
  root's only failures are error diagnostics found as its modules are parsed
  and a dependency reports a project error, it exits 2 where `0.1.7` exited 1.
  The `pietto.project-explain.v1` shape is unchanged.
- The private module inspection document that a project builds before it
  reports an import cycle (PMS-2) now lists a blocked module's cycle members
  once. It is private, built and checked in-process only, and keeps its
  marker `pietto.module-inspection.v1`; on the invocations compared for PMS-2
  with the interlude's first batch, the stdout, stderr and exit status of the
  project commands are unchanged.
- Bundles and saved-job records made by 0.1.7 or earlier are refused by the
  changed code identity; keep their matching old environment. Pietto supplies
  no migration or rewrite.
- The execution extras install the same driver versions as `0.1.7`.
- `0.1.8` is a normal version number: once it is published,
  `pip install -U pietto` upgrades to it, and so do the pins `pietto~=0.1`
  and `pietto<0.2`.

### Project diagnostics

These changes apply to explicit-module projects, and the change for a repeated
bare name outside a JOIN (F7) applies to LEGACY_FLAT (`schema_version = 1`)
projects too. They change only the diagnostics of relations that already
report an error, so a program that checks still checks. Each statement
describes the queries probed for these changes, apart from the differences
that the [known limitations](#known-limitations-of-018) list.

- **A mixed aggregate JOIN reports what a single file reports (F5).** A
  relation with JOIN inputs that a single file refuses with PIE-S2312, for
  mixing an aggregate with another projection without GROUP BY, now reports
  beside that PIE-S2312 what a single file reports, unless its `let:` clause
  or WHERE is refused: the errors of its other SELECT items, of the reads in
  its windows, of its QUALIFY (an unknown name there is PIE-S2102, where
  QUALIFY elsewhere in an explicit-module project still reports PIE-S2332) and
  of its ORDER BY keys, and PIE-S2381 at each aggregate that may read rows
  that a JOIN repeats. `0.1.7` reported PIE-S2312 alone, beside the PIE-S2305
  of a repeated output name, or, when the only other projection was a window,
  a bare PIE-S2333. The
  [PIE-S2312 row](spec/diagnostics.md#semantic-diagnostics) lists the codes.
  Compared with `0.1.7` on 44 JOIN programs and 68 grouped JOIN emissions with
  a window, for PostgreSQL and MySQL, the SQL and the `check --project` output
  of the programs that check are unchanged, and so are the single-file
  diagnostics of 674 cases.
- **A repeated SELECT output name reports more as a single file does (F7).**
  Under owner decision Q1-A, which aligns project diagnostics with single-file
  behaviour:
  - A repeated unknown bare name, such as `nosuch` in
    `select: id, nosuch, nosuch` or `x = nosuch` written twice, reports
    PIE-S2102 `Unknown field: nosuch` at the first item and only PIE-S2305 at
    the repeat. Outside a JOIN, `0.1.7` also reported PIE-S2102 at the repeat;
    in a JOIN query without GROUP BY or aggregates it reported it at neither
    item, or, after a JOIN `where` or `let:` that fails, at both.
  - In a JOIN query, a repeated item and the item that it repeats now report
    their other errors beside the PIE-S2305, as a single file does: an unknown
    field (PIE-S2102 at both items of `x = rows.nosuch` written twice), a name
    that two inputs have (PIE-S2335, `x = id`), or invalid operands or
    arguments (PIE-S2105, `x = rows.id + 'a'`; PIE-S2104,
    `z = abs(rows.nosuch, 1)`). Without GROUP BY, aggregates or a failing
    `where` or `let:`, `0.1.7` reported PIE-S2305 alone, and with GROUP BY it
    omitted the repeated item's errors.
  - A grouped JOIN query whose `where` or `let:` fails now also reports the
    errors of its SELECT items without an aggregate or a window, such as
    PIE-S2102, PIE-S2318 `Grouped projection is not a GROUP BY key` and
    PIE-S2319 at a computed output; `0.1.7` reported none of them.

  A LEGACY_FLAT (`schema_version = 1`) project checks no JOIN, so a JOIN query
  there still reports only PIE-S2334 at the JOIN.

On the 1392 generated JOIN queries probed for the first batch, these changes add
no project diagnostic that a single file does not report and `0.1.7` did not
report, remove none that `0.1.7` and a single file both report, and change no
single-file output; 504 of them now report exactly what a single file reports,
against 116 in `0.1.7`. The 286 queries probed for F7 show no regression from
`0.1.7`.

### `explain --project`

- **A root module that fails to parse no longer hides the dependencies' errors
  (EXD-5).** Explain reads the root package's manifest and every asset file
  and checks their content against the root's pin before it parses any module.
  When that check passes and a root module then fails to parse, explain now
  loads the dependencies that the verified manifest declares and lists their
  diagnostics after the root's, as it lists them once the root loads: the same
  codes, messages, locations, `In dependency package ...` prefix and order,
  and the same cycle, conflict and diamond rejections. A module fails to parse
  when its bytes, which match the pin, are not UTF-8 (`source_read`) or when
  it reports an error diagnostic as it is parsed: a syntax error, `PIE-S2801`
  for `collect` or `unnest`, or any other. A root that fails before the pin
  check still reports only its own diagnostics, because its dependency
  declarations are not verified: when its manifest or typed-asset validation
  fails, an asset read fails (`source_read` for a module file that is missing
  or not accessible), or the content does not match the pin, for example a
  stale pin. The `pietto.project-explain.v1` shape is unchanged. See the
  [project guide](project-package.md).
- **One exit status changes.** The exit status of such a failure now follows
  the whole list, as it does once the root loads: 2 when the root or a
  dependency reports a project error, such as `project_resource` for a missing
  dependency directory, and 1 otherwise. So when the root's only failures are
  error diagnostics found as its modules are parsed, such as a syntax error,
  and a dependency reports a project error, explain now exits 2 where `0.1.7`
  exited 1.

### Emission contracts

- **Repeated premises are documented (PE-09).**
  [Emission contract values](project-package.md#emission-contract-values) now
  states the rule that `0.1.7` already follows. PE-09 changes documentation
  and tests only, so acceptance, exit codes and output bytes are those of
  `0.1.7`. A premise declared again with the same bound scope, key and
  canonical value is an exact repeat, accepted in any number of copies, within
  `environment`, within one source's `premises` or across both; the SQL is
  unchanged, `request.contract` and `target.environment` echo every copy, and
  a requirement that uses the premise cites each copy. Each copy is still
  checked on its own, so a field premise that disagrees with the field's
  `domain` is BLOCKED with `PIE-B1005` however many copies there are. Two
  declarations of one key in one bound scope with different canonical values
  are BLOCKED with `PIE-B1005`, also on a source the statement does not read,
  and a source described twice is INPUT_REJECTED.

### Documentation

- The [language reference](language.md) no longer says that PostgreSQL holds
  the `sum` of a `bigint` column as `numeric`, so that `s / 2` with `s = 3` is
  `1.5000000000000000`. Since `0.1.7` Pietto casts the PostgreSQL `sum` of an
  `Int` back to `int8` and emits `s / 2`, for such a sum `s`, as an `int8`
  division, an integer division like `DIV` on MySQL. This changes
  documentation only.

### Performance

- **Faster checks of many relations (PMS-3).** In an explicit-module project,
  `check --project`, `emit-sql --project` and `compile_query` no longer build
  the private Project IR analysis bundle, which nothing on these paths read.
  Relational properties now take the verified Project IR result directly;
  private Project IR inspection still builds the bundle. With the first batch,
  one module with 600 tables checks in about 5.2 s and 90 MiB at peak, where
  `0.1.7` took 13 s and 361 MiB; 300 tables take 2.1 s instead of 4.2 s, and
  200 modules of one source, table and query each take 3.7 s instead of 11 s.
- **Faster JOIN functional dependencies (PMS-6, in part).** At each JOIN step,
  duplicate functional dependencies are merged through an index instead of
  being compared with every one merged so far, imaged classes are ordered by a
  position lookup, and strict-rule incidence lists are built from the set bits
  of each rule's determinant mask. With the first batch, one query with 60
  JOINs checks in about 1.6 s instead of 2.3 s, with 90 JOINs in 4.3 s instead
  of 9.4 s, and with 120 JOINs in 11 s and 567 MiB instead of 31 s and
  585 MiB. Every JOIN step still images the functional dependencies of its
  inputs into its own output, so the cost still grows faster than the JOIN
  count.
- **Measured output.** Both trees were measured again for this comparison, the
  first batch against `0.1.7`, so the times do not separate PMS-3 from PMS-6,
  on generated explicit-module projects, on the same machine with CPython
  3.13.13 on Linux x86-64; the `0.1.7` figures in its own notes come from an
  earlier measurement. The machine was shared with other work, so a run counts
  only when a reference CPU loop just before it took at most 1.40 s (the clean
  reference runs took 1.07 to 1.39 s); this rule was set after the runs had
  been made, because a planned fastest-of-five rule left the 300-table check
  without a clean run, and the 90- and 120-JOIN checks had been rerun, up to
  four times a run, until a reference loop just before them ran at normal
  speed. Each time is the fastest such run of one command on one tree: for the
  check times given here, 3 to 9 runs counted, out of 8 to 12. Peak memory, in
  MiB, is the median of all runs. The times show the change and are no
  performance promise. On these projects the stdout, stderr and exit status of
  `check --project`, and of `emit-sql --project` for PostgreSQL for the
  300-table module and the 60-JOIN query, are byte-identical to those of
  `0.1.7` in every run; other programs were not compared byte for byte for
  this measurement.
- **An import cycle is reported sooner (PMS-2).** Before `check --project` or
  `emit-sql --project` reports an import cycle (PIE-S2703), the project builds
  and self-checks its private module inspection. That inspection now lists a
  blocked module's cycle members once, under its first readiness cycle record,
  instead of once for each issue that blocks the module. For a cycle of N
  modules from which modules outside it make R relation imports, its readiness
  records now grow as N² + N·R instead of N³ + N²·R. Measured with
  `check --project` against the first batch on generated projects, on the same
  machine with CPython 3.13.13 on Linux x86-64: a 40-module cycle takes 0.92 s
  instead of 2.1 s; an 80-module cycle 1.2 s and 66 MiB instead of 10 s and
  446 MiB; a 160-module cycle 2.7 s and 108 MiB instead of 103 s and 3,075
  MiB; a 40-module cycle with 40 outside modules that each import a table from
  every member (R = 1,600) 4.8 s and 125 MiB instead of 55 s and 2,038 MiB.
  Each figure is the median of three runs per tree, the two trees alternating,
  and a pair of runs counted only when a reference CPU loop just before and
  just after it took at most 1.40 s. The machine was shared with other work,
  so the times show the change and are no performance promise; stdout, stderr
  and exit status were the same on both trees in every run.
  `emit-sql --project` was not timed. On 715 project command invocations
  compared with the first batch, 51 of them `emit-sql --project` for
  PostgreSQL and MySQL, the exit status, stdout and stderr are byte-identical;
  the 26 that produced SQL are all on projects without an import cycle,
  because PIE-S2703 blocks every emission from a project that has one. The
  private document keeps its marker `pietto.module-inspection.v1`, since it is
  built and checked in-process only. Its portable self-check still compares a
  blocked module's cycle count with its cycle records and its member list with
  the module's graph component. A forged document whose positive cycle member
  count disagrees with its member list or with the module's graph component is
  now refused when the module closes, as `inconsistent_scope_relation` instead
  of `child_count_mismatch`, so another fault later in the same module is
  reported first.

### Release notes

- The 0.1.7 notes below were corrected after publication: see
  [Corrections after publication](#corrections-after-publication).

### Known limitations of 0.1.8

These [known limitations of 0.1.7](#known-limitations) change in `0.1.8`; the
others stay as listed there, with the timings measured for `0.1.7`.

- `explain --project` no longer stops at the root package when a root module
  fails to parse after the root's pin check passes, and a repeated environment
  premise is a documented rule (both above). The 0.1.7 entries for many
  relations or many JOINs, a mixed aggregate JOIN and a repeated unknown
  SELECT item are replaced by the entries below, and an unknown QUALIFY name
  in a mixed aggregate JOIN relation is now PIE-S2102 (see F5). The 0.1.7
  entry for an import cycle is replaced by PMS-2 above: a ring's readiness
  records now grow with the square of its size, not its cube, when no module
  outside it imports from it, and in general as N² + N·R.
- **Many relations or many JOINs are still slower to check than in a single
  file.** In an explicit-module project, one module with 300 tables checks in
  about 2.1 s (a single file of them in 0.55 s, as the `0.1.7` notes give),
  and one with 600 tables in about 5.2 s; 200 modules of one source, table and
  query each take about 3.7 s. The JOIN properties of one query still grow
  faster than its JOIN count: one query with 60 JOINs checks in about 1.6 s,
  with 90 JOINs in about 4.3 s (a single file in 0.4 s, as the `0.1.7` notes
  give) and with 120 JOINs in about 11 s and 567 MiB.
- **A mixed aggregate JOIN relation whose `let:` clause or WHERE is refused.**
  In a project such a relation still stops before its aggregates, as in
  `0.1.7`: it reports only that refusal, and the PIE-S2305 of a repeated
  output name, where a single file also reports PIE-S2312 and what F5 above
  lists. For example, beside a JOIN `o` of `items` with `let p = items.price`,
  `where id > 1` with `select k = items.id, n = sum(items.price)` reports only
  its PIE-S2335. The [PIE-S2312 row](spec/diagnostics.md#semantic-diagnostics)
  lists the 20 cases measured for F5.
- **Other differences from a single file.** The probes for the first batch
  show these differences in explicit-module projects too; each is as in
  `0.1.7` or closer to a single file, and the list is not complete:
  - When a SELECT item reports an error, such as an unknown field or the
    PIE-S2305 of a repeated output name, a JOIN query or a query without GROUP
    BY reports no error of its ORDER BY keys, unless it is a JOIN relation
    that reports PIE-S2312 (F5 above): beside `select: id, y = nosuch + 1`,
    `order by k` reports no PIE-S2102. A relation without JOIN inputs that
    reports PIE-S2312 checks no key either, where a single file reports
    PIE-S2380.
  - With GROUP BY, a computed output can report PIE-S2319 without its own
    errors (`x = rows.nosuch + 1`).
  - After a failing `where` or `let:`, an aggregate or a window item can
    report fewer errors than in a single file, PIE-S2320 or PIE-S2329 can be
    missing, and after a failing `let:` an ambiguous name can miss its
    PIE-S2335.
  - A JOIN relation whose projections are all aggregates and which a single
    file refuses with PIE-S2381, or with ORDER BY PIE-S2334, is a PIE-S2333 in
    a project, with its fan-out cause when an aggregate may read rows that a
    JOIN repeats; so is a grouped JOIN relation whose aggregate may read such
    rows, where a single file reports PIE-S2381 or another error of the
    relation. A SELECT error, such as the PIE-S2305 of a repeated output name,
    or a refused `where` or `let:` can be reported instead.
  - An unnamed computed item in a JOIN query, such as `rows.id + 1`, is a
    PIE-S2304 error in a project and a warning in a single file, and the other
    items' errors can then be missing.
  - Some diagnostics come in another order: a call such as
    `abs(rows.nosuch, 1)` can report PIE-S2102 before PIE-S2104, and without a
    JOIN the diagnostics of a repeated dotted or computed output are not
    sorted by position.

A later architecture item, project joined aggregation analysis beside a
refused WHERE or `let:` binding, which lets the joined aggregation stage
analyse over a row filter that is not concrete, is to remove the differences
above that follow a refused or failing `where` or `let:`; it has no scheduled
phase yet (see the [roadmap](roadmap.md#project-mode-follow-up)). The other
differences have no scheduled home yet. Sharing JOIN functional dependencies
across JOIN steps is a separate design decision.

## Nested results and project emission public alpha release notes — 0.1.7

<a id="unreleased-changes-following-016"></a>
<!-- The id above keeps the links of the 0.1.6 notes below and of docs/phases/phase-71/slice-23.md, written before these notes were released, pointing here. -->

**Status:** `0.1.7` was published from `4c8348a4` (tag `v0.1.7`) on the
versioned GitHub pre-release and PyPI channels. These historical release notes
neither publish a successor nor substitute for channel byte verification.
As for earlier releases, the compiler and package are covered on CPython 3.12
and 3.13 for Linux x86-64; other platforms and Python versions are not.

`0.1.7` retires no source spelling of `0.1.6`. It completes Phase71: in an
explicit-module project (`schema_version = 2`), `collect` and `unnest` now
check, emit PostgreSQL SQL and run through the alpha Python API on
PostgreSQL. It also widens project SQL emission, adds batch project emission,
emits PostgreSQL `sum(Int)` with checked casts in single files as in projects,
and refuses a relation-name qualifier through a `let` alias in a project, as a
single file does. The Python execution extras keep the pins of `0.1.6`. The
sections from 0.1.6 down describe published files.

### Highlights

- **Nested PostgreSQL results.** In an explicit-module project,
  `name = collect r` reads an ordered relation let `r` as one nested value, and
  `let o = unnest(p.field)` followed by one `cross join o`,
  `inner join o on ...` or `left join o on ...` (for example `on True`)
  expands it again.
  `check --project` types and checks both, and `PIE-S2802` is retired. On
  PostgreSQL, `emit-sql --project` emits each Collect read as a
  `LEFT JOIN LATERAL` count-and-arrays aggregate and an admitted Unnest as
  `LATERAL ROWS FROM` over `pg_catalog.unnest`; MySQL reports `PIE-B1003` for
  every Collect read and Unnest. Single files, LEGACY_FLAT projects and
  package modules still report `PIE-S2801`.
- **Nested results in Python.** `compile_query`, `load_bundle` and
  `execute(..., route="postgres_rows")` run bounded Collect queries with Int,
  Bool, finite Text, finite Float, Decimal, Date, Timestamp and UUID children,
  several collections side by side, and one Unnest that may keep a sibling
  collection. Ordinary `save`, source-free R1 and `verified_export` keep the
  complete child lists. `postgres_adbc`, `mysql_rows` and guarded or refined
  requests refuse nested results before any connection, and R2 and recovery,
  relay and sink effects refuse them too.
- **Batch project SQL emission.** `emit-sql --project ROOT --all` emits every
  matching top-level table or query in one `pietto.sql-emission.batch.v1`
  document, each item the document of its single-owner call; when every item
  is VERIFIED, `--output DIR` writes them as files on supported Linux
  filesystems.
- **Wider project SQL emission.** On PostgreSQL, narrow Int arithmetic is
  computed in `bigint`, `bigint` arithmetic and `sum(Int)` use PostgreSQL's
  checked `bigint`, and UUID values compare and order. `Date` source fields
  and Timestamp and Date comparisons and ordering are emitted on both targets,
  and so are JOIN SELECT projections with the reviewed scalar calls, casts and
  conditionals, and Timestamp UNION ALL and UNION DISTINCT. Every blocker of a
  BLOCKED `emit-sql --project` document now carries a `suggestion`.
- **Exact `sum(Int)` in single-file PostgreSQL SQL.** Single-file `emit-sql`
  writes PostgreSQL `sum(Int)` as
  `CAST(SUM(CAST(x AS pg_catalog.int8)) AS pg_catalog.int8)` (an aggregate
  window as `CAST(SUM(CAST(x AS pg_catalog.int8)) OVER (...) AS pg_catalog.int8)`),
  as project emission does: a sum outside signed 64 bits fails with SQLSTATE
  22003 instead of returning an exact `numeric`.
- **Project-mode corrections.** A relation-name qualifier through a `let`
  alias (`customers.price` after `let c = customers` and `from c`) is refused
  in a project as in a single file. The import hint of an unknown name is now
  also the JSON `suggestion`; when no module exports the name, it names the
  modules that declare it without exporting it, and it never suggests an
  import that would close an import cycle. `explain --project` names the
  commands that read schema 1 and 2 projects.
- **Known limitations and rescheduled work.** The project-mode limits that
  remain, with fresh timings, are listed under
  [Known limitations](#known-limitations), and the
  [Rescheduled](#rescheduled) section gives the home that the owner decided
  for each debt reviewed for this release and not fixed in it.

### Upgrading from 0.1.6

- 0.1.7 retires no source spelling, so a 0.1.6 file needs no `pietto migrate`
  step.
- In an explicit-module project, a program that reads a relation-name
  qualifier through a `let` alias, which 0.1.6 accepted, now fails
  `check --project` and is BLOCKED by `emit-sql --project`: write `c.price`
  instead of `customers.price` after `let c = customers` and `from c`.
- `collect` and `unnest` in an explicit-module project, which 0.1.6 refused
  with `PIE-S2802`, now check, and on PostgreSQL emit; MySQL reports
  `PIE-B1003` for every Collect read and Unnest, and the new `PIE-S2803` to
  `PIE-S2807` say why a form is not admitted.
- Single-file PostgreSQL SQL for `sum(Int)` changes: its result is a nullable
  signed 64-bit `bigint` for every Int input, and a sum of a `bigint` column
  outside that range fails with SQLSTATE 22003 instead of returning an exact
  `numeric`. Single-file MySQL SQL is unchanged.
- Strict readers of the JSON documents must upgrade: every blocker of a
  BLOCKED `pietto.sql-emission.v1` document (a failure document is always
  v1) gains a nonempty `suggestion`; Collect documents add `collection`
  columns, R27 requirements and `collect_*` range roles; the import hint of
  PIE-S2002, PIE-S2303, PIE-S2604, PIE-S2301 and PIE-S2103 fills the
  diagnostic's `suggestion`, which was null; and the batch document is a new
  format. VERIFIED documents gain no `suggestion` field.
- Some messages change: PIE-S2370 in every project now names `collect` among
  the one read of a let with `capture` lines, and the `config_schema` refusal
  of `explain --project` for a schema 1 or 2 project names the commands to use.
- Bundles and saved-job records made by 0.1.6 or earlier are refused by the
  changed code identity; keep their matching old environment.
- Nested saves add no workspace version: `0.1.7` saves nested results in the
  v7 workspace format of `0.1.6`. A saved-job record, nested or flat, is
  usable only under the code identity it names, so `0.1.7` refuses the
  records that `0.1.6` saved and `0.1.6` refuses those that `0.1.7` saves,
  nested results included. Pietto supplies no migration or rewrite.
- Pietto's own PostgreSQL sessions now set and verify `extra_float_digits=1`
  and `DateStyle=ISO,MDY` on every request, flat ones included.
- The execution extras install the same driver versions as `0.1.6`.
- `0.1.7` is a normal version number: once it is published,
  `pip install -U pietto` upgrades to it, and so do the pins `pietto~=0.1`
  and `pietto<0.2`.

### Nested relations: checking

- **Phase71 nested-relation spellings are checked.** In an EXPLICIT_MODULES
  project (`schema_version = 2`), `name = collect let_name` and
  `let o = unnest(binding.field)` are typed and checked as the next two
  entries describe; `PIE-S2802`, which 0.1.6 reported at each of them, is
  retired. Single files, LEGACY_FLAT projects and package modules still
  report `PIE-S2801`, which says how to make a `schema_version = 2` project.
- **Collect reads in explicit-module projects.** A relation with a
  `name = collect r` SELECT item completes like any other: the Collect
  output is a nested relation that is never None, and its relation stays
  readable with `from`, a JOIN, `exists` and its scalar columns. Such a
  project checks.
  New errors say why a read is not admitted: `PIE-S2803` for a Collect in a
  grouped SELECT or a relation let, of a source, table or query instead of a
  relation let of the same body, of a let whose columns are not known before
  completion, or of a let with a field that is not one of the eight collected
  leaf types (`Bool`, `Date`, `Decimal`, `Float`, `Int`, `Text`, `Timestamp`
  and `UUID`), has no known nullability yet (one computed with a binary
  arithmetic or comparison operator, such as `id + 1`, with `and` or `or`, or
  with `not`, `-` or `+` over one of those) or is itself collected;
  `PIE-S2804` for a let without `order by`; and `PIE-S2805` for a read of a
  nested field that needs a value (a comparison, ordering, grouping, a scalar,
  `in` or ANY read, `select distinct` or a set operation), or a nested field
  selected beside a RIGHT or FULL JOIN, a window or QUALIFY, GROUP BY or an
  aggregate, or in a relation let. As in a `select distinct` relation, a
  SELECT item that reads a shape-typed field, or a `let` bound to one, makes a
  relation with a Collect read report `PIE-S2333`.
  A let with `capture` lines counts `collect` as its one read, so a second
  read is `PIE-S2370`, whose read-once message now reads ``... can be read
  only once, by exists, scalar, in, collect or a join in the body of q.`` in
  every project, including those that use no `collect`.
- **Unnest binding in explicit-module projects.** `let o = unnest(p.field)`
  followed by one `cross join o`, `inner join o on ...` or
  `left join o on ...` (for example `on True`) reads the rows of a nested
  field that a `collect` SELECT item outputs: `o` has the collected let's
  fields, and its JOIN reports what any JOIN reports. Such a project checks.
  New errors say why an Unnest is not admitted: `PIE-S2806` for an argument
  that is not a nested field of the FROM input or a CROSS, INNER or LEFT JOIN
  written before the let, and `PIE-S2807` for a RIGHT or FULL JOIN of it, a
  second JOIN, another read of its name, an Unnest in a relation let, or one
  beside grouping, aggregates, windows, `select distinct`, `any(...)`, a
  Collect read, another Unnest or a RIGHT or FULL JOIN that may null-extend
  its binding.

### Nested relations: SQL emission

- **PostgreSQL Collect emission.** `emit-sql --project --dialect postgres`
  emits a Collect read (`name = collect r`) of the selected table or
  query. Each read is one `LEFT JOIN LATERAL` single-row aggregate: `COUNT(*)`
  under the field's label, then one `ARRAY_AGG` per child field under the
  child's label, in child order. Every array of a read is ordered by one
  private `ROW_NUMBER()` over `r`'s own ORDER BY items, so the arrays of one
  parent row stay aligned; a LIMIT on `r` applies per parent row, and sibling
  Collect reads are independent laterals. An empty collection is a count of 0
  with NULL arrays; a child row whose fields are all None counts 1, and a
  missing outer-JOIN container has a NULL count and NULL arrays.
- **Collections in later relations.** A table or query that reads such a
  relation, by name or through an import, may read its scalar columns, test it
  with `exists`, expand one collection with an Unnest, and keep a collection
  as an output beside an ordinary JOIN or the Unnest of another collection.
  Grouped child producers, query parameters and scalar filters keep that
  collection intact. On PostgreSQL the admitted Unnest is a JOIN whose right
  side is one `LATERAL ROWS FROM` that zips one `pg_catalog.unnest` per child
  array in child-field order; the final columns stay scalar, except a retained
  collection.
- **JSON documents.** A document (`pietto.sql-emission.v1`, or v2 with header
  parameters) describes a nested column as `logical_type.kind` `collection`
  with `element` entries and a `pg_column_arrays_v1` representation that lists
  the count and array columns by statement position, with `result_origin`
  added when the relation ends in ORDER BY or LIMIT. Every
  `correspondence.sql_symbol` stays a logical position, so a flat column after
  a nested field with F fields is F statement columns further right than its
  `sql_symbol`. The `collection` requirements and the generated kinds
  `collect_lateral`, `collect_count`, `collect_array` and `collect_ordinal` use
  rule R27. Each `collect_lateral.evidence` holds exactly one object with the
  `use`, `producer`, `terminal` and ordered `children` of the read, which the
  public reader checks against the parsed SQL; it is consistency evidence, not
  an authentication of altered documents. SQL ranges add the `collect_*`,
  `ordinal_*`, `distinct_wrapper_*` and `unnest_*` roles. These additions
  leave a document without a nested field unchanged. A generated SELECT counts
  its physical columns against the column limit (`PIE-B1007`).
- **Refused forms.** MySQL reports `PIE-B1003` (`collect_not_admitted_on_target`
  or `unnest_not_admitted_on_target`) at each Collect read and Unnest let. A
  nested UNION, an ordinary RIGHT or FULL JOIN carrying a nested value, and a
  nested window value stay refused on PostgreSQL too.

### Nested relations: Python execution

- **Bounded Collect and Unnest.** `compile_query` and `load_bundle` prepare
  the admitted PostgreSQL collection shapes without connecting, and
  `execute(..., route="postgres_rows")` runs them through the live compiled
  graph or a loaded source-free bundle. Collect fields may have Int, Bool,
  finite Text, finite Float, Decimal, Date, Timestamp and UUID children, and
  one CROSS, INNER or LEFT Unnest can expand one collection while the result
  keeps another. Named and imported producers, ordinary JOIN carry, scalar
  filtering, grouped child producers and header parameters keep the whole
  nested field.
- **Values.** Each collection keeps its child's authored ordering, without a
  tie-break guarantee. A missing outer-JOIN container is `None`, distinct from
  an empty `[]` and from a real child row whose fields are None. Float keeps
  its binary64 bits; Decimal keeps its precision and scale, in decimal128 or
  decimal256 as needed; Date stays within 1000-01-01..9999-12-31; Timestamp is
  timezone-free civil microseconds; UUID keeps its 16 bytes. Pietto's own
  PostgreSQL sessions set and verify `extra_float_digits=1` and
  `DateStyle=ISO,MDY`, flat requests included.
- **Bounds.** Before the main SQL, in the same read-only snapshot, an attempt
  checks `server_encoding = UTF8`, bounded physical root counts (at most 64
  rows for a parent root and 16 for a root that a collected child reads) and
  actual Text lengths (at most 256 UTF-8 bytes). Preflight bounds every
  emitted field, batch and total bytes and retained child occurrences, counting
  each JOIN edge and each retained occurrence; an unknown or unsupported bound
  is refused, and no protective LIMIT is added. `batch_rows` and `max_rows`
  count top-level rows, the rows that an Unnest expands included, and a
  parent's collection is never split across batches.
- **Saves, R1 and export.** Ordinary `save(..., route="postgres_rows")` keeps
  admitted nested results, final-flat Unnest included, in the existing v7
  workspace. Source-free R1 and independent read-only `verified_export` read
  the fixed saved checkpoint with the original nested schema and complete child
  lists. Parent occurrences are the checkpoint, batch and ACK unit; children
  have no cursor or ACK of their own, and rebatching keeps each child list
  whole. Export verifies each member before its first returned slice, caches at
  most one verified member and rechecks acceptance and reader lifetime before
  each slice.
- **Refused routes.** `postgres_adbc`, `mysql_rows` and guarded or refined
  nested requests are refused before any connection; R2 and recovery, relay
  and nested sink effects remain refused. Nested IPC is an internal checked
  transport, not a public IPC API.

### Batch project SQL emission

`emit-sql --project ROOT --all` emits every matching top-level table or query,
with optional exact `--module`, `--kind` and `--name` filters, in one
`pietto.sql-emission.batch.v1` document. Each batch item contains the same
document as its single-owner call. The exit status is 0 only when every item is
VERIFIED, 1 when one or more is BLOCKED and none is INPUT_REJECTED, and 2 for
any INPUT_REJECTED. The complete batch JSON has a 64 MiB limit; overflow
rejects the whole batch with exit 2 and no output directory. On supported Linux
filesystems, `--output DIR` writes a new directory, only when every item is
VERIFIED, with complete JSON artifacts and a manifest installed last; an
interrupted run can leave a directory without its manifest, which is
incomplete. Other platforms retain batch stdout. Existing paths are never
overwritten, and calls without `--all` retain their prior output and behavior.
`pietto emit-sql --help` does not list `--all`;
`pietto emit-sql --project ROOT --all --help` prints the batch usage, and the
[project guide](project-package.md) and
[project CLI JSON v2](spec/project-cli-json-v2.md) describe it.

### JOIN projections, Timestamp UNION and blocker suggestions

- In `emit-sql --project`, JOIN SELECT projections now accept the existing
  reviewed scalar calls, casts, conditionals, membership and comparison
  chains. ON, joined LET/WHERE, JOIN kinds and source/key domains keep their
  previous limits.
- In `emit-sql --project`, Timestamp UNION ALL and UNION DISTINCT preserve the
  existing exact carrier, civil-microsecond meaning and NULL behavior. No
  Timestamp INTERSECT/EXCEPT or additional set carrier is enabled.
- Every blocker of an `emit-sql --project` document gains a nonempty
  `suggestion` shared with text `hint:`. This changes BLOCKED JSON bytes while
  retaining the current format names; old strict readers must upgrade.
  VERIFIED documents and CLI error records gain no field, and batch items
  remain byte-identical to current single-owner output.

### Project SQL emission: numeric and temporal operations

- **Narrow Int arithmetic in bigint on PostgreSQL.** `emit-sql --project`
  computes a `+`, `-`, `*`, unary `-` or `abs` over `pg_int2`/`pg_int4`
  operands whose exact range leaves that type in `bigint`, writing
  `CAST(x AS pg_catalog.int8)` around its first operand, so `id + id`,
  `id * id`, `-id` and `abs(id)` over an `int4` field are now emitted instead
  of `PIE-B1002`. The proof is static (a narrow operation always fits 64
  bits), so a parameterized template such as `-nullif(id, low)` now carries no
  `int_range_representable` obligation and binds; before, it kept an `int4`
  carrier that no binding could satisfy. An operation that already fits its
  narrow type, an operation with a `bigint` operand (`id + 1` with its literal
  anchored to `bigint` included) and every MySQL statement are unchanged, and
  arithmetic that may leave 64 bits stays `PIE-B1002` except on PostgreSQL
  `bigint` operands (see the checked bigint rule below). For a still-BLOCKED
  PostgreSQL operation, the blocker hint says every result lies outside signed
  64 bits and PostgreSQL's checked operation could only fail; the MySQL hint
  keeps the signed-64-bit fit requirement. A public consumer of the
  emission observation accepts the new `int8_widen` overlay only where this
  rule requires it.
- **Date source fields.** An emission contract may map a `Date` field to
  PostgreSQL `pg_date` or MySQL `my_date` with the `date` domain. Such a field,
  like a derived Date, supports carrying, `==`/`!=`, `count`,
  `count_distinct`, DISTINCT, GROUP BY and `year`/`month`/`day`, and unlike a
  derived Date it is an equality JOIN key (INNER, LEFT, RIGHT); a FULL JOIN on
  a Date key stays refused.
- **Timestamp and Date ordering.** Timestamp and Date values of one carrier
  compare with `<`, `<=`, `>`, `>=` and inclusive comparison chains, in WHERE
  and in a JOIN ON condition alike (`on a.id == b.id and a.ts <= b.ts`),
  order a result or a window, and on PostgreSQL are `min`/`max` arguments,
  whose result keeps the carrier and, for a Timestamp, its result-contract
  meaning (MySQL keeps `PIE-B1003` for these `min`/`max`). Timestamp, Date and
  UUID values may partition a window; UUID ordering follows below. `min`/`max`
  of a UUID stays refused, and a Timestamp never compares with a Date.
- **Exact `sum(Int)` on PostgreSQL.** Both single-file `emit-sql` and
  `emit-sql --project` emit PostgreSQL `sum(Int)` as
  `CAST(SUM(CAST(x AS pg_catalog.int8)) AS pg_catalog.int8)`. In project mode
  this replaces `PIE-B1004` (`sum_int_aggregate_range_proof_missing`): the sum
  accumulates exactly, and its result is a nullable `Int` with storage
  `pg_int8` over the whole signed 64-bit range. A sum outside that range,
  including one over a physical `bigint` input, is never returned as a wrong
  value: PostgreSQL may report SQLSTATE 22003 (`bigint out of range`) while
  planning or running the statement, with no timing guarantee. In single
  files, where it applies to global, grouped and HAVING aggregates and to
  aggregate windows (written
  `CAST(SUM(CAST(x AS pg_catalog.int8)) OVER (...) AS pg_catalog.int8)`), it
  replaces the bare `SUM(x)`, which returned `bigint` for a `smallint` or
  `integer` column and an exact `numeric`, possibly outside signed 64 bits,
  for a `bigint` column. Project emission's generated R13 requirement carries
  the new evidence
  `{"overflow": "target_checked_signed64_narrowing"}`. This revises Phase66
  R13, which admitted no final aggregate CAST. Project MySQL keeps `PIE-B1004`,
  as its `CAST(DECIMAL AS SIGNED)` would clamp such a sum; single-file MySQL,
  and `Decimal` or `Float` `sum` or `avg`, are unchanged.
- **Checked bigint arithmetic on PostgreSQL.** An `Int` sign, `+`, `-`, `*`
  or `abs` over `bigint` operands whose exact range leaves signed 64 bits but
  meets them, such as `qty + 1`, `-qty` or `abs(qty)` over a `pg_int8` field,
  is now emitted unchanged instead of `PIE-B1002`: PostgreSQL's `bigint`
  operators are checked, so an out-of-range value is the same run-time
  SQLSTATE 22003 and never a wrapped one. The result keeps the part of the
  exact range inside signed 64 bits, and the operation's generated R05
  requirement carries the same evidence. PostgreSQL may also raise the
  error while planning, wherever it reduces the operands to constants, such
  as `(9223372036854775807 if True else 0) + 1` or a bound value, even over
  no rows or in a branch no row takes. A range wholly outside signed 64 bits,
  such as that of a constant, stays `PIE-B1002`, as such an operation could
  only fail. A parameterized template keeps its
  `int_range_representable` obligation, and on PostgreSQL a binding now
  discharges it under the same rule when the bound range meets signed 64
  bits. Likewise a slot value under a sign or inside arithmetic whose result
  only meets signed 64 bits now binds on PostgreSQL instead of `PIE-R1004`
  (`BINDING_INVALID`), so `execute()` may then fail after connecting, with
  `PIE-R3003` and SQLSTATE 22003, where it refused the value before. MySQL
  keeps `PIE-B1002` until a real-database differential reviews its `BIGINT`
  overflow error.
- **UUID ordering on PostgreSQL.** UUID values of one carrier now compare
  with `<`, `<=`, `>`, `>=` and inclusive comparison chains, order a result
  and order a window on PostgreSQL, by their 16 bytes compared as unsigned
  big-endian values, the order of PostgreSQL `uuid_cmp` and of Python
  `uuid.UUID`. MySQL keeps them BLOCKED (`PIE-B1003` for a comparison or
  result ORDER, `PIE-B1002` for a window ORDER key) until a real-database
  differential reviews its `BINARY(16)` byte order; `min` and `max` of a UUID
  stay `PIE-S2314`.
- **Observation and evidence.** The private emission observation records
  each generated requirement's evidence tokens and each aggregate's
  `result_cast`, and a public consumer admits `SUM`, its two casts and
  `target_checked_signed64_narrowing` only where the rules above produce
  them.

### Project mode

- **A relation-name qualifier through a `let` alias is refused, as in a
  single file.** After `let c = customers` and `from c`, `0.1.6` projects
  accepted a read such as `customers.price` in a query without a JOIN,
  outside `any(...)`, in every clause but HAVING and the ORDER BY of a
  grouped query, and `emit-sql --project` read the field of `c`. An
  explicit-module project now refuses it as it refuses any name that is no
  input, so such a program fails `check --project` and is blocked by
  `emit-sql --project`. Rewrite the read with the alias: `c.price`. A query
  with a JOIN, or a read inside `any(...)`, already refused it. At the read
  a project reports what a single file reports, such as PIE-S2102
  `Unknown field: customers.price`, with the differences for any unknown name
  that the [known limitations](#known-limitations) below list.
- **An import hint is also the JSON suggestion, names a declaration that is
  not exported, and never closes a cycle.** The hint that `0.1.6` added to
  PIE-S2002, PIE-S2303, PIE-S2604 and PIE-S2301 when another module exports
  the unknown name, and to PIE-S2103 for a `def` of another module, is now
  also the diagnostic's JSON `suggestion`, which was null; the message is
  unchanged. A module that imports the module of the diagnostic, directly
  or through others, is no longer named, since that import would close a
  module import cycle (PIE-S2703). When no other module exports the name,
  the modules that declare it without asking to export it are named the
  same way, with the export to add, where `0.1.6` gave no hint:
  `Unknown relationship parameter shape: Order; Order is a shape declared but not exported by types.pietto: export it there with export (shape Order), then import it with from "types.pietto" import (shape Order)`.
  The unknown relation of a Collect read gets no hint, since `collect`
  reads only a relation let of its own table or query (PIE-S2803), which
  no import gives.
- **`explain --project` names the commands for schema 1 and 2 projects.**
  Its `config_schema` refusal of a `schema_version = 2` project now reads
  `Project Explain runtime requires project schema version 4. Use check --project and emit-sql --project for this schema version 2 project.`,
  and of a `schema_version = 1` project
  `Project Explain runtime requires project schema version 4. Use check --project for this schema version 1 project.`;
  `0.1.6` gave only the first sentence. Its suggestion, for every schema
  version below 4, is now
  `explain --project reads only a schema version 4 package-root project, and changing schema_version alone does not convert a project.`,
  followed for schema 3 by the one-step conversion as before; it no longer
  names the commands, which the message of a schema 1 or 2 project now
  does. The code, location and exit status are unchanged.

### Command line

- `pietto emit-sql --help` ends its project-mode usage line with
  `In project mode --output writes the JSON artifact in either --format.`,
  as the [project guide](project-package.md) and the project-mode help of
  `--output` already say. The behaviour is unchanged.

### Release notes

- The 0.1.6 notes below were corrected after publication: see
  [Corrections after publication](#corrections-after-publication).

### Known limitations

None of these limits produces wrong SQL. The timings were measured on the
code of this release with CPython 3.13.13 on Linux x86-64; they show how the
cost grows and are no performance promise.

- **Layered JOIN DAGs are slow to check.** When each relation JOINs the
  relation before it and the one before that, `check --project` takes about
  1.7 to 2.7 times as long for every two more layers: about 1.8 s at 16
  layers, 3.1 s at 18, 7.3 s at 20, 18 s at 22 and 48 s at 24, where a single
  file of 16 or 18 such layers checks in about 0.3 s. `emit-sql --project` was
  not timed for this release. The grain that a project keeps for each JOIN
  still copies the factors of every path to its inputs.
- **An import cycle is slow to report.** A ring of modules that import each
  other is reported with one PIE-S2703, but only after the project builds
  readiness records whose number grows with the cube of the ring's size:
  `check --project` takes about 2.3 s for 40 modules, 9.4 s and 458 MB for
  80, and 71 s and 3.1 GB for 160. The change after `0.1.7` that records
  each blocked module's cycle members once is described under
  [Unreleased changes following 0.1.7](#unreleased-changes-following-017).
- **Many relations or many JOINs are slow to check.** A project check builds
  an assessment for every pair of relations: one module with 300 tables
  checks in about 4.7 s (a single file of them in 0.55 s), and one with 600
  tables in about 14 s and 378 MB (a single file in 0.8 s); 200 modules of
  one source, table and query each take about 8.9 s. The JOIN properties of
  one query grow about with the cube of its JOIN count: one query with 60
  JOINs checks in about 3.0 s, with 90 JOINs in about 10 s (a single file in
  0.4 s), and with 120 JOINs in about 32 s and 609 MB. The changes after
  `0.1.7` make these checks faster; see
  [Unreleased changes following 0.1.7](#unreleased-changes-following-017).
- **A bare PIE-S2333 can hide later errors.** Some relations that a single
  file accepts, or refuses with another code, are still the bare PIE-S2333
  `Project relation semantic completion is unavailable: <r>` in a project,
  for example one whose SELECT output is an always-null number such as
  `o0 = None - 3.0`. The relations that read it report nothing of their own,
  such as an invalid LIMIT, until it is fixed. The
  [diagnostics reference](spec/diagnostics.md#semantic-diagnostics) lists
  these cases.
- **A cross-module shape error can add a bare PIE-S2333.** A source whose
  shape, imported from another module, fails for an error inside its
  declaration other than an unknown type, such as a duplicate field
  (PIE-S2501), still adds the bare PIE-S2333 at the source beside that
  error, where a shape in the source's own module reports only the error.
  So does a source whose field type is an alias, declared in another
  module, of a name that module imports with a relation kind (PIE-S2705).
- **A source without a shape is quiet beside some other errors.** In a module
  that reports some other errors, such as a duplicate shape field (PIE-S2501)
  or an unknown field (PIE-S2102), a source without a shape gets no
  PIE-S2333, and so no `(source items has no shape, ...)` advice, until that
  error is fixed; beside others, such as an invalid LIMIT (PIE-S2307), it
  still gets it.
- **An exported duplicate declaration.** A module that declares a source or
  shape twice and exports it reports PIE-S2704
  `Ambiguous local export declaration: source s` at the export; a single
  file, or the module without that export, reports PIE-S2001 at the second
  declaration.
- **An import after the target's own import fails.** When the target module
  re-exports a name whose own import of it fails, or imports a name and
  exports it with another kind, an import of the name from that module
  still adds PIE-S2705 (`Imported declaration is unavailable: ...` or
  `Imported declaration is private or not exported: ...`) beside the
  target's own error. An import of the very kind and name whose export the
  target refuses (PIE-S2704) adds nothing.
- **An unknown name.** A QUALIFY predicate that reads an unknown name outside
  a window reports PIE-S2332 `Unknown QUALIFY reference: <name>` in a project,
  where a single file reports PIE-S2102. When a relation name is read through
  a `let` alias after a JOIN (`customers.price` after `let c = customers`), a
  single file adds `; customers names a relation, not a binding: write c.price`
  and a project does not.
  When a query has several unknown names, a project can list a SELECT item's
  diagnostic before a WHERE test's or a GROUP BY key's, where a single file
  follows the source order. The change after `0.1.7` that reports the
  unknown QUALIFY name as PIE-S2102 in a mixed aggregate JOIN relation is
  described under
  [Unreleased changes following 0.1.7](#unreleased-changes-following-017).
- **A mixed aggregate JOIN.** A relation with JOIN inputs that mixes an
  aggregate with another projection reports only PIE-S2312 in a project, with
  or without ORDER BY, beside the PIE-S2305 of a repeated output name; a
  relation whose aggregate has an error of its own reports that error and no
  PIE-S2312, as a single file does. When its `let:` clause or WHERE is
  refused, it reports only that refusal, and the PIE-S2305 of a repeated
  output name, without PIE-S2312, and when its only other projection is a
  window, it is a bare PIE-S2333. A single file reports PIE-S2312 in the other
  cases, the errors of the other SELECT items and QUALIFY beside it, PIE-S2381
  when an aggregate may read rows repeated by a JOIN and, with ORDER BY, the
  PIE-S2380 of an ORDER BY key that reads an input field outside an aggregate.
  A project relation whose projections are all aggregates still reports that
  fan-out, as a PIE-S2333 with its cause. The change after `0.1.7` that aligns
  most of these cases is described under
  [Unreleased changes following 0.1.7](#unreleased-changes-following-017).
- **A repeated unknown SELECT item.** A SELECT item of an unknown name written
  twice, such as `nosuch`, reports PIE-S2102 at both items in a project
  outside a JOIN, and in a JOIN query at neither, at the first or at both,
  depending on GROUP BY and on whether a `where` or `let:` fails; for such a
  bare name a single file reports it at the first, with the PIE-S2305 that
  both report. The change after `0.1.7` that aligns it is described under
  [Unreleased changes following 0.1.7](#unreleased-changes-following-017).
- **`explain --project` stops at the root package.** When the root package
  of a schema 4 project fails to load, for example for a syntax error in one
  of its modules, `explain --project` reports only the root's diagnostics;
  the errors of its dependencies appear once the root is fixed. The change
  after `0.1.7` that lists them when the root's pin check passes is
  described under
  [Unreleased changes following 0.1.7](#unreleased-changes-following-017).
- **A repeated environment premise.** An emission contract whose
  `environment` lists one premise twice with the same value is VERIFIED, and
  the artifact's `target.environment` lists it twice, while a repeated source
  description is INPUT_REJECTED. After `0.1.7` this is a documented rule; see
  [Unreleased changes following 0.1.7](#unreleased-changes-following-017).
- **A collection selected without a JOIN.** A table or query that reads a
  relation with a Collect read and selects its collection, without a JOIN or
  an Unnest, checks, but `emit-sql --project` reports it BLOCKED with
  `PIE-B1003` (`expression_evidence_unavailable`) at that SELECT item. Keep the
  collection in the relation that collects it, or select it beside a JOIN.
- **Collect ordering by an output name.** Completion does not yet order a
  collection by a key of `r` that is one name alone naming a SELECT output
  other than a window's (`order by oid` over `oid = id`); order by the input
  value (`order by id`) instead, or the table or query reports PIE-S2333.
- **A non-UTF-8 unrecognized argument to `emit-sql --project`.** With JSON
  output, an unrecognized argument that holds a byte that is not valid
  UTF-8 prints `pietto: error: terminal output could not be encoded` on
  stderr and no `INPUT_REJECTED` usage document (exit `2`);
  `--format text` prints the usage error.
- **`--all` is missing from `pietto emit-sql --help`.** That help does not
  list the batch option; `pietto emit-sql --project ROOT --all --help` prints
  the batch usage and `--all`.
- **A swapped argument pair.** A relationship call whose arguments are given
  in the wrong order, such as `PlacedBy(customers, order)` for
  `relationship PlacedBy(order: Order, customer: Customer)`, still reports
  PIE-S2604 at each argument instead of one diagnostic, as since 0.1.5.

### Rescheduled

These items are not fixed in `0.1.7`. By the owner decision of 2026-11-03
(see the [decision record](decisions.md)), each has the following home; the
[roadmap](roadmap.md#project-mode-follow-up) records them.

- **A project-mode quality interlude after `0.1.7`**, which may run beside the
  formatter step, takes: the import-cycle readiness records behind the slow
  PIE-S2703 (PMS-2); building the pairwise relation assessments only when
  private inspection asks for them (PMS-3); an incremental JOIN
  functional-dependency closure (PMS-6); `explain --project` diagnostics of
  the dependencies after a root failure (EXD-5); a rule for an exactly
  repeated environment premise (PE-09); the mixed aggregate JOIN diagnostics
  (F5); and the repeated unknown SELECT item (F7).
- **A later phase** takes linear analysis of layered JOIN DAGs, which needs an
  ARCHITECTURE_DECISION on the semantic identity of grain facts.
- **Phase72 Gate 1 candidates**, which that Gate 1 may accept or not, are:
  the rest of the D-11 and D-12 restoration that the post-0.1.4 stability
  repair deferred, that is, sound outer-JOIN aggregates that `check` still
  refuses with PIE-S2381, such as `min`, `max` or `count_distinct` over a JOIN
  that may repeat rows, or a LEFT JOIN anti-test `where o.id is None`, and the
  typed-NULL arithmetic of a project SELECT; the bare PIE-S2333 of a project
  relation whose SELECT output is an always-null number, which hides the
  errors of the relations that read it (F2); the `concat` and `stddev`
  functions, which the owner placed after Phase71 on 2026-10-30; and `now()`,
  which needs a semantic design first. None of them is available in `0.1.7`:
  `concat`, `stddev` and `now()` are unknown functions (PIE-S2103).

This decision covers the debts reviewed for this release. The other known
limitations above are carried over from `0.1.6` or come with the changes of
this release; no decision has scheduled them yet, and they stay documented
here until one does.

### Corrections after publication

These notes were corrected after `0.1.7` was published; the release itself
is unchanged.

- The status above now says that `0.1.7` is published.
- The known limitation of a mixed aggregate JOIN said that a project reports
  only PIE-S2312. It now also names the two cases where `0.1.7` does not: a
  relation whose `let:` clause or WHERE is refused reports only that
  refusal, and one whose only other projection is a window is a bare
  PIE-S2333. It also names the errors of the other SELECT items and QUALIFY
  that a single file reports beside PIE-S2312.
- The known limitations that changes after `0.1.7` lift or reduce now point
  to [Unreleased changes following 0.1.7](#unreleased-changes-following-017).
- The known limitation of a mixed aggregate JOIN now also names the
  PIE-S2305 of a repeated output name and a relation whose aggregate has an
  error of its own.
- The known limitation of a repeated unknown SELECT item said that a project
  reports PIE-S2102 at both items. It now says that this holds outside a
  JOIN, and that a JOIN query reports it at neither, at the first or at both
  items.

## Corrections and MySQL parity public alpha release notes — 0.1.6

**Status:** `0.1.6` was published from `bdb3f567` (tag `v0.1.6`) on the
versioned GitHub pre-release and PyPI channels. These historical release notes
neither publish a successor nor substitute for channel byte verification.

`0.1.6` retires no source spelling of `0.1.5`. It corrects single-file SQL and
checking, brings single-file MySQL `emit-sql` close to PostgreSQL for JOINs,
FULL JOINs and windows, corrects project mode, and moves the driver pins of
two Python execution extras. Of Phase71 it contains only
batch B1: the nested-relation spellings are recognized and refused. The
sections from 0.1.5 down describe published files.

### Highlights

- **Same-file reads are CTEs.** A single-file read of a table or query of the
  same file includes its SQL as a dependency CTE, in text and JSON output
  alike, and the `PIE-S2382` warning of 0.1.5 is retired. `emit-sql` text
  output also names each statement with a `-- name` line and ends it with `;`;
  JSON artifact SQL has no name line and no `;`.
- **Single-file QUALIFY and aggregate windows.** `QUALIFY` checks and emits
  for PostgreSQL and MySQL; `sum`, `count`, `avg`, `min` and `max` windows
  emit in single files; and single-file windows read JOIN inputs.
- **Single-file MySQL parity.** `emit-sql --dialect mysql` emits INNER, LEFT,
  RIGHT and CROSS JOINs, most FULL JOINs within PostgreSQL's FULL JOIN limits
  (as a derived table), windows, QUALIFY and aggregates over JOIN rows,
  aggregate windows, `round(Float)` and `date_trunc`, with the same matches,
  duplicates and NULL-extended rows as PostgreSQL under each target's own
  comparison rules. Some forms that PostgreSQL emits stay `PIE-B1000` on
  MySQL, among them GROUPS frames with an offset bound, EXCLUDE CURRENT ROW,
  GROUP or TIES, a read of an enum or other non-builtin field after a FULL
  JOIN, and more than 8 FULL JOINs in one relation. Project MySQL emission
  gains none of these forms.
- **Fewer conservative fan-out refusals.** A hand-written `on` equality to a
  unique key proves an at-most-one match as a relationship call does, and the
  bounded D-11 and D-12 proofs accept some outer-JOIN aggregates and typed-NULL
  arithmetic that 0.1.5 refused.
- **Warnings for what a Python reader may misread.** `PIE-S2106` (`/` of two
  Int values truncates), `PIE-S2107` (a `None` option of an `in` list never
  matches), `PIE-P1009` (`--` is not a comment), `PIE-S2383` (a WHERE test
  that rejects the NULL-extended side of a LEFT JOIN), `PIE-S2384` (`not in`
  with a nullable left value) and `PIE-S2385` (a single-file relation that
  emission will refuse). Warnings do not change the exit status of `check`.
- **Checking corrections.** An explicit-module project reads a shape-typed
  field as that shape in more places, as a single file does, and reads a FROM
  input through its alias; several diagnostics that pointed at the wrong
  problem now name it.
- **Project mode.** After an external review of 0.1.5 project mode,
  `check --project` and `emit-sql --project` report what a single file
  reports in many more places. An ambiguous or unknown read and a grouping
  or aggregate error in a relation without JOIN inputs keep their
  single-file code, message and position instead of a bare `PIE-S2333`; a
  failed import is no longer masked, and the relations that read it add no
  bare `PIE-S2333`; follow-on diagnostics of an error already reported are
  dropped; each module gets the single-file declaration checks; and import
  or export statements outside a `schema_version = 2` project are
  `PIE-S2708`. A wrong-kind import is `PIE-S2705`, re-exports resolve
  through any number of modules, and an unresolved import or an unknown name
  suggests the path or import it may mean. JSON v2 counts a file with only a
  semantic error as a file with errors, configuration, selector and contract
  errors name their fault, emission blockers point at their item, and the
  project guide and contracts match the code. The SQL that project emission
  still produces is unchanged. The known limitations under Project mode below
  list what remains, among them slow checks of layered JOIN DAGs, some bare
  `PIE-S2333`, a mixed aggregate JOIN that reports only `PIE-S2312`, a
  relation-name qualifier through a `let` alias that is still accepted, and
  a repeated unknown SELECT item reported twice.
- **R2 and a trailing `any`.** `save_recoverable` and `recover` accept a
  trailing `where any(...)` or `where not any(...)`.
- **Python execution dependencies.** `pietto[execute-mysql]` installs
  `mysql-connector-python==26.10.0` and `pietto[execute-postgres-adbc]` installs
  `1.13.0` of both ADBC packages; each route refuses the previous driver
  version with `PIE-R2002` before any connection.
- **Phase71 nested-relation spellings, recognized and refused.**
  `name = collect let_name` and `let o = unnest(binding.field)` are recognized:
  an explicit-module project types them and reports `PIE-S2802`, and every
  other mode reports `PIE-S2801`.
- **A style page.** [Pietto style](style.md) shows one way to write each thing
  for readers who know Python and a little SQL.

### Upgrading from 0.1.5

- 0.1.6 retires no source spelling, so a 0.1.5 file needs no `pietto migrate`
  step.
- Some programs that 0.1.5 accepted are refused or warned about, and some
  emit different SQL; the entries below describe each change. Programs that
  assert an empty diagnostic list or empty stderr see the new warnings.
- Bundles and saved-job records made by 0.1.5 or earlier are refused by the
  changed code identity; keep their matching old environment.
- In project mode, `check --project` refuses more programs that a single file
  refuses and `emit-sql --project` blocks them, a `schema_version = 1`
  project with import or export statements fails `check --project`
  (`PIE-S2708`), and many project diagnostics, the project JSON v2
  `files_with_errors` count, related locations and some error kinds change;
  Project mode below lists each change.
- An environment that keeps `mysql-connector-python==26.7.0` or the `1.12.0`
  ADBC packages is refused on that route; install the extra of this release.
- `0.1.6` is a normal version number: `pip install -U pietto` upgrades to it,
  and so do the pins `pietto~=0.1` and `pietto<0.2`.

### Refinement

- **R2 and a trailing `any`.** `save_recoverable` and `recover` accept a
  trailing `where any(...)` or `where not any(...)`, alone or AND-composed
  with other filters, including the migration of a last `semi join` or `anti
  join`. R2 refines it as the semi or anti JOIN it represents and qualifies
  the source columns that its predicate and another block's operands read.
  An `any` under `or`, in a `select` item, over a let with `capture` lines, or
  whose predicate reads another block is still `PIE-R1004`
  (`REFINEMENT_EXPRESSION_BLOCK_READ`). SQL, CLI and JSON shapes are unchanged.

### Checking and diagnostics

- **Phase71 nested-relation spellings (batch B1).** `name = collect let_name`
  in a `select:` block and `let o = unnest(binding.field)` read by a later
  CROSS, INNER or LEFT JOIN are recognized. In an EXPLICIT_MODULES project
  (`schema_version = 2`) they are typed, and every Collect read and Unnest let
  then reports `PIE-S2802`, as this release cannot lower or return them;
  single files, LEGACY_FLAT projects and package modules report `PIE-S2801`,
  which says how to make a `schema_version = 2` project. A user `def` named `collect` or
  `unnest` keeps its ordinary meaning, and syntax errors keep their code,
  order and position.
- The bounded D-11 unmatched-row and one-key-value proofs and D-12 typed-NULL
  numeric rules described in the language reference are now accepted. Cases
  outside those proofs remain refused; `min`, `max` and `count_distinct` do
  not gain a general fan-out exemption.

- `Text(Int)`, `round` and `date_trunc` are now closed scalar forms. `Text`
  accepts only Int; another input type is `PIE-S2105`. `round` accepts Decimal
  with an optional literal or `let`-expanded scale from -30 to 30, or one Float
  argument; `date_trunc` accepts literal units year/month/day for Date and
  additionally hour/minute for Timestamp. A `let`-expanded scale or unit is
  read also where the call is a project select item. A project Date is
  obtained with `date_of(Timestamp)`. Unsupported arity or scalar shapes are
  `PIE-S2104`.
- `string_agg(value, delimiter, order by key[, key ...])` is a PostgreSQL
  aggregate with explicit, preserved internal ordering. Without its internal
  ORDER BY it is `PIE-S2104` (`expected ORDER BY key`) in single files and
  projects. In a single file an argument of only `None` values, also a
  conditional whose branches are only `None`, is `PIE-S2104` too (`expected
  two Text arguments`); an explicit-module project refuses it with the bare
  `PIE-S2333`, or `PIE-S2315` with JOIN inputs. MySQL and window use fail
  closed. Over a source without a shape it is an aggregate projection like
  `max`: beside another projection, a window included, without GROUP BY it
  is `PIE-S2312`, and `emit-sql` refuses it with `PIE-B1000`, as it refuses
  every aggregate over such a source.
- An aggregate called with an extra argument of only `None` values, such as
  `sum(id, None)` or `max(id, coalesce(None, None))`, is `PIE-S2309`
  (`Aggregate function sum expects 1 arguments, got 2`) in single files and
  LEGACY_FLAT projects, as with an extra typed argument. 0.1.5 accepted it at
  `check`, and `emit-sql` refused it with `PIE-B1000`.

- Handwritten `on` equalities can prove the same at-most-one match as a
  relationship predicate. Single files use declared source keys. Projects also
  use a key that a query carries through only `select`, a `where` without
  `any(...)`, `order by` and `limit`; the key of a query with GROUP BY, an
  `any(...)` filter, a window, QUALIFY, `select distinct`, a JOIN or a FROM
  over a query block does not yet prove an `on` match (a grouped query's key
  still protects its own GROUP BY). Matching a nullable unique key in
  `on` is allowed, while using a key as GROUP BY protection still requires
  non-null fields. A key proof does not prove a match exists. Fan-out errors
  name the JOINs that can repeat the aggregate's input, and suggest matching
  only keys that `on` can prove.
- `PIE-S2383` warns when WHERE rejects the NULL-extended side of a LEFT JOIN;
  `PIE-S2384` warns about `not in` with a nullable left value. An explicit
  `None` list option retains the separate `PIE-S2107` warning.
- `PIE-S2385` warns about known single-file emission limits. PostgreSQL and
  MySQL both refuse RANGE offsets; effective `ignore nulls` or `from last`; a
  FULL JOIN `on` conjunct that is not an equality between Int fields of its
  two sides, such as a non-Int equality, a filter, `<`, `True` or an `or`;
  and a FULL JOIN after a pending `where any(...)` or `where not any(...)`.
  In a relation whose FROM does not end at a `mysql.table` source it also
  warns about untyped all-NULL outputs read by another relation or by the
  relation's own QUALIFY, which reads them through a derived table;
  operators over `None` only (`None + None`); a CASE, `coalesce` or `nullif`
  of only `None` values where text cannot stand, a QUALIFY condition
  included; a cast of a value not known to be Int that reads no field of
  unknown type; a `count` of a field typed by a shape; a `substr`, `ntile`,
  `lag`, `lead` or `nth_value` integer literal outside the 32-bit range; and
  a CTE that would hide a table read by the same statement. MySQL emits an
  untyped all-NULL output that another relation reads, except a field read
  after a FULL JOIN, which it refuses without this warning. A relation with
  an error gets none of the expression or CTE warnings. Warnings do not
  change the check exit status; existing errors remain errors.
- `check --project` in an explicit-module project reads a field of a shape,
  also through a `let` name, after a JOIN, in the WHERE, `let` and
  `any(...)` of a `select distinct` query and as a captured field, as that
  shape, as single files do: `home + 1`, `-work`, `len(work)` or
  `lower(o.ship)` over such fields are PIE-S2105 or PIE-S2104. 0.1.5
  accepted them in a WHERE, a `let` or an `any(...)` and refused a select
  item with the bare PIE-S2333; `lag(h)` or `h is None` for `let h = home`
  now pass where 0.1.5 reported PIE-S2333. Without JOIN inputs a select item
  that tests such a field directly, such as `b = home is None` or
  `b = home == work`, and a select item of a `select distinct` query, where
  a project types no select item yet (`x = name + 1` is the bare PIE-S2333
  there too), are still the bare PIE-S2333, as in 0.1.5. The ungrouped
  `order by` of a relation without JOIN inputs that is not `select distinct`
  reads such a field as that shape too (`order by home + 1` is PIE-S2105),
  but a project still types no other part of that `order by`, so
  `order by name + 1` for a Text `name` passes `check --project`; project
  emission refuses it.
- A one-line set-operation body such as `union all a, b` may be followed by
  blank lines, as a block body may; 0.1.5 reported PIE-P1000
  (`Unexpected end of line; expected end of block.`) at the blank line.
- A simple legacy `== null` or `!= null` comparison now suggests `is None` or
  `is not None` directly. `migrate` still refuses output that the modern
  parser cannot accept.
- In a single file, an `any(...)` predicate that reads a field of the FROM row
  of a source without a shape, such as `items.id` in
  `any(o.item_id == items.id for o in orders)`, is PIE-S2102
  (`Unknown or unavailable field in ANY predicate: items.id`). 0.1.5 accepted
  it at `check`, and `emit-sql` and `explain` stopped with PIE-I1000. So is
  a read of an output of no type, such as `o.x` in
  `any(o.x == items.id for o in t)` for `x = None` of `t`, which 0.1.5 also
  accepted at `check`.
- Some programs that 0.1.5 refused with a diagnostic that pointed at the wrong
  problem now report the problem itself. They are still refused, and no other
  program or SQL output changes:
  - A `let` that a later JOIN reads as its input, as in `let c = customers`
    before `inner join c on ...`, names a relation, as `from` does. When its
    value names no relation, such as a relation that the module does not
    import or a misspelled name, it is PIE-S2301 `Unknown relation: <name>` at
    the value, in single files and projects, and when it names a `let`
    declared after it, PIE-S2330
    (`Let binding cannot reference a later binding: <name>`). 0.1.5 reported
    PIE-S2604 (`A row-value let must follow FROM and every JOIN and precede
    WHERE`) at the `let`. A value that names a field visible there, a query
    header parameter or an earlier `let` keeps PIE-S2604.
  - In a single file, such a `let` of a set-operation query, such as
    `let b = both` for a `query both:` whose body is `union all a, a`,
    reports two PIE-S2334,
    at the set operation
    (`Set operations are available only when an EXPLICIT_MODULES project
    (schema version 2) completes them.`) and at the JOIN
    (`Set-operation inputs are available only when an EXPLICIT_MODULES project
    (schema version 2) completes them: both`), where 0.1.5 reported
    PIE-S2604. A `schema_version = 1` project no longer adds PIE-S2604 to its
    two PIE-S2334, and an explicit-module project still accepts the program.
  - The value of `lag`, `lead`, `first_value`, `last_value` or `nth_value`,
    and a `lag` or `lead` default, that names a `let` whose value is not a
    field, such as `let k = amount + 1` or `let k = 1`, is PIE-S2104 at the
    call: ``Invalid arguments for function lag: value must be a direct field
    or Bool, Text, Int, Float, or NULL literal, not the `let` name k``
    (`default must be` for a default). 0.1.5 reported PIE-S2102
    `Unknown field: k` at the argument, although `k` is defined. This holds in
    single files and in projects, except that an explicit-module project still
    reports the bare PIE-S2333 for `let k = None`. A `let` whose value is a
    field, such as `let k = amount`, still reads that field.
  - A JOIN `on` that calls an unknown function with JOIN inputs as its
    arguments, such as `inner join customer on nosuch(orders, customer)`,
    reports PIE-S2103 `Unknown function: nosuch` alone: the inputs are row
    arguments of the call, not ON references. 0.1.5 also reported a PIE-S2335
    `JOIN ON reference is unknown: <input>` for each such argument in a single
    file, and in an explicit-module project reported PIE-S2334 (`JOIN-local ON
    is available only when an EXPLICIT_MODULES project (schema version 2)
    completes it.`) and such a PIE-S2335 without the name instead of
    PIE-S2103. A `schema_version = 1` project, which has no JOIN, is unchanged.
    In an explicit-module project, when the name is a relationship that only
    other files declare, the message adds
    `order_customer is a relationship of models.pietto, which a module cannot
    import: declare it in this module`.
- In a single file, a SELECT item of a relation with GROUP BY that names a
  `let` binding (PIE-S2102 `Unknown field: <name>`, or PIE-S2329 for a binding
  selected by its own name) adds what to write: the field, for a binding of a
  field that a GROUP BY key groups by
  (``Unknown field: key; a query with GROUP BY cannot select a `let` name here
  yet: write status in place of key`` for `let key = status`); an
  explicit-module project, for a computed binding that is a GROUP BY key
  (``a query with GROUP BY cannot select a computed `let` value here yet:
  group by it and select it in an EXPLICIT_MODULES project (schema version
  2)``); otherwise `<name> is not a GROUP BY key`. A GROUP BY key that names a
  computed `let` adds ``a query cannot group by a computed `let` value here
  yet: group by it in an EXPLICIT_MODULES project (schema version 2)``. Codes
  and locations are unchanged.

- EXPLICIT_MODULES projects read a FROM input through its alias and its
  original name: after `let c = customers` and `from c`, `c.id`, which 0.1.5
  refused with PIE-S2102 `Unknown field: c.id`, and `customers.id` name the
  same input occurrence in every clause but HAVING and the ORDER BY of a
  grouped query, which read no qualified input field (the bare PIE-S2333, as
  in 0.1.5, also without an alias).
  0.1.5 accepted `customers.id` in WHERE, GROUP BY, an ungrouped ORDER BY and
  a grouped SELECT, refused it in a
  row-value `let` with PIE-S2102 (`Unknown field: customers.id`) and stopped
  with an internal error (`inconsistent_scope_relation`) on it in an
  ungrouped SELECT. The original name is read only in a query without a JOIN and
  outside `any(...)`; intermediate aliases and `any`, capture and JOIN scopes
  still refuse it, as 0.1.5 did.

- A legacy INNER, LEFT, RIGHT, FULL or CROSS JOIN written with `as` now has a
  PIE-P1000 suggestion for its own JOIN kind; a CROSS JOIN suggestion has no
  `on`. The `migrate` PIE-P1011 for a legacy `semi join` or `anti join` with
  `as` names its `where any(...)` or `where not any(...)` rewrite. These are
  corrections to 0.1.5's migration guidance; codes and locations are unchanged.
- A diagnostic inside an `any(...)` or `not any(...)` filter before a later
  JOIN names the authored binder, including unknown, ambiguous and nested
  reads, rather than a generated binding.

- An IN/NOT IN list of an enum value and its labels, such as
  `status in ("paid", "shipped")`, is accepted and emitted as written. Before,
  it was `PIE-S2105` while the same list with a `None` option passed. A Text
  literal operand likewise takes the type of a Date, Timestamp, UUID, Bytes or
  Json value, also as the left value of an EXPLICIT_MODULES `in` read of such
  a column or an enum column; a literal that is not a label, such as
  `status in ("paid", "gone")`, is still refused.
- Three new warnings, in every check mode, for spellings a Python reader
  misreads; programs still check and emit as before. `PIE-S2106`: `/` of two
  Int values truncates (`7 / 2` is 3); write `Float(x) / y`. `PIE-S2107`: a
  `None` option of an `in` list never matches (and makes `not in` never
  true); write `x == "a" or x is None`. `PIE-P1009`: `--` is two minus
  signs, not a comment (`100 -- 50` is 150); write `#`. The semantic two are
  reported in single files and LEGACY_FLAT projects, `PIE-P1009` wherever
  source is parsed except `migrate`. Programs that assert an empty
  diagnostic list or empty stderr for such source now see the warning.
- `pietto.semantic.analyze` refuses an AST that carries the legacy JOIN
  fields with PIE-S2378, and the legacy JOIN codes PIE-S2601 to PIE-S2603 are
  retired and not reused.

### SQL emission

- Single-file reads of a table or query now include its SQL as a dependency
  CTE, in the text output and in the JSON `sql` of the reading artifact alike.
  An unsupported dependency also prevents SQL for its reader; the old
  `PIE-S2382` warning is retired. Text output names each statement with a
  `-- name` line and terminates it with `;`; JSON artifact SQL has no name
  line and no `;`.
- Single-file `QUALIFY` now checks and emits for PostgreSQL and MySQL,
  including hidden windows. Its filter follows the window stage and precedes
  ORDER BY and LIMIT; ambiguous input/selected-output names are refused.
  Under GROUP BY it reads the GROUP BY keys and selected outputs only
  (PIE-S2102 otherwise, also for a `let` whose `any(...)` reads another
  field); with aggregates and no GROUP BY it reads selected outputs and `let`
  names that read no input field, and a hidden window there is PIE-S2103.
  These hold over a source without a shape too, whose fields it reads by
  name; over such a source a name that a SELECT output has reads that output,
  and any other name, a `let` value's fields included, reads the input
  through a private derived-table port. Under GROUP BY over such a source
  `check` accepts a selected or hidden window, as 0.1.5 accepted both, and
  `emit-sql` refuses the relation with PIE-I1000. A window under GROUP BY,
  hidden or selected, reads the selected keys and aggregates by their
  output names; a name that an output shares with an input field whose
  value it is not, such as `cat` for `cat = max(price)` grouped by `cat`, is
  PIE-S2102 (`Ambiguous field: cat is both the input field items.cat and a
  SELECT output; give the output another name`), where 0.1.5 read the
  output. An aggregate call
  in the QUALIFY condition is PIE-S2308; read the aggregate through its selected alias. Its ambiguity
  message offers the qualified input name only where QUALIFY can read it.
  PostgreSQL emission refuses, with PIE-B1000, a QUALIFY that reads an
  untyped all-None output or whose condition is a CASE, `coalesce` or
  `nullif` of only `None` values, which PostgreSQL reads as text through the
  derived table; check warns with PIE-S2385, and MySQL emits it.
  A MySQL statement that reads a QUALIFY relation ends its CTE, when it has
  no `limit`, with `LIMIT 18446744073709551615`, which keeps every row and
  makes MySQL compute its windows once, however often the statement reads it.
- Over a source without a shape, an ORDER BY key that reads an input field,
  named alone or through a `let`, is qualified with the name FROM gives the
  input where a SELECT item would capture it, as over a source with a shape:
  `order by price` beside `Price = 0 - price` emits
  ``ORDER BY `items`.`price` `` on MySQL, and `order by p` with `let p =
  price` beside `price = 0 - price` emits `ORDER BY "items"."price"`. 0.1.5
  emitted the bare name, which both targets read as the SELECT output.
- PostgreSQL single files support `sum`, `count`, `avg`, `min`, and `max` as
  window aggregates, with their ordinary argument and logical result
  contracts. An omitted frame keeps SQL's default: ordered peer-inclusive
  accumulation, or the whole partition without ORDER BY. GROUPS requires
  ORDER BY. A `let` name bound to `None` as the argument is PIE-S2315, and a
  `let` name whose value is no field as a partition or order key is PIE-S2103,
  as for other windows; over a source without a shape every aggregate window
  outside GROUP BY that reads a field, `count(x) window()` included, is
  PIE-S2103 (`count() window()` reads none and is accepted), and a `count`
  window of a field typed by a shape is PIE-S2104. Project aggregate-window
  support is not introduced; for MySQL see Single-file MySQL parity.
- Single-file PostgreSQL windows can read JOIN inputs, including named
  specifications and hidden QUALIFY windows, while retaining input identities
  and the visibility limits of existence filters.
- MySQL refuses, with PIE-B1000 at that statement, a reader whose CTEs have
  names that differ only by case, a statement that would define as a CTE a
  table or query with two outputs whose names differ only by case, and a
  QUALIFY whose derived table would hold two such outputs; a top-level SELECT
  keeps them. Each name Pietto generates into a statement (an `any(...)`
  alias, a hidden SEMI or ANTI JOIN alias, a QUALIFY output or derived
  table) now skips, on both backends, a name it would capture that differs
  from it only by case: 0.1.5 aliased the EXISTS of
  `any(o.price == _Pietto_Value_1.price for o in orders)` over
  `from _Pietto_Value_1` as `_pietto_value_1`, which MySQL with
  `lower_case_table_names` 1 or 2 reads as that outer row, so the EXISTS
  compared each order with itself.
- An ORDER BY key that reads a SELECT output by its name (a selected window
  result, or an output over a row of unknown type) is emitted as that
  output's SELECT list position beside an unaliased item, which PostgreSQL
  and MySQL each name by rules of their own, and on MySQL beside another
  output whose name differs from it only in case: `order by n` beside `" n"`
  and `n = row_number() window(order by id)` emits `ORDER BY 2`. 0.1.5
  emitted `` ORDER BY `n` ``, which MySQL sorts by the unaliased `' n'`, as it
  names that item `n`, and `ORDER BY "lower"` beside `lower(cat)`, which
  PostgreSQL rejects as ambiguous. Beside an unaliased item an input field
  key is now qualified on MySQL too, as PostgreSQL already qualified it:
  0.1.5 left `order by price` bare beside `" price"`, so MySQL sorted by that
  constant.
- A CTE gives each unaliased output (PIE-S2304) a private alias
  `__pietto_column_<n>`, which no name the statement selects or reads takes,
  in any case, so a read of another output never binds to the name the
  database would give the unaliased one, such as `lower` for `lower(cat)` or
  for a CASE whose ELSE is `lower(cat)` in PostgreSQL, or `price` for
  `" price"` in MySQL; the relation's own statement keeps the output
  unaliased.
- A statement that reads a table or query of the same file by a name that
  relation gives no output, such as `lower` for an unaliased `lower(email)`
  over a source without a shape, is refused by `emit-sql` with PIE-B1000 on
  PostgreSQL and MySQL, at the reading relation (``Its SQL reads lower from
  relation a, which names no output lower; if it means the unaliased output
  at line 6, column 9, which has no name a reader can use, write `lower = ...`
  there to name it``); `check` still accepts it, as its fields are of unknown
  type. An ORDER BY key such as `Z` beside an output `z`, or `z + 1`, reads
  the relation, not the output, and is refused the same way. 0.1.5 read the
  name the database gives the unaliased output, and emitted a read of a name
  no output has, which the database rejected.

### Single-file MySQL parity

Single-file `emit-sql --dialect mysql` now emits the following forms that
PostgreSQL emits, each with the same matches, duplicates and NULL-extended
rows under each target's own comparison rules. A form without such a MySQL
8.4 spelling is still refused with `PIE-B1000`, and MySQL parity does not
change PostgreSQL SQL. As in the MySQL SQL emitted before, the place of NULLs in an
ascending or descending order, Text comparison under the column's collation,
and the type and scale of an aggregate's result follow MySQL. Project MySQL
emission gains none of these forms.

- **JOINs.** INNER, LEFT, RIGHT and CROSS JOINs, every `on` form,
  relationship and `def` calls in `on`, self-JOINs, JOIN chains, a JOIN of a
  table or query of the same file (read as a CTE), `any` and `not any` filters
  before a later JOIN, `any` inside `on`, `where` or `select`, and the ordinary
  tail after a JOIN. The pending-filter rules are PostgreSQL's: the next RIGHT
  JOIN takes a pending filter into its `on`, else it leads the `where`.
- **Windows, QUALIFY, GROUP BY and aggregates over JOIN rows**, as
  PostgreSQL emits them.
- **FULL JOIN** within PostgreSQL's FULL JOIN limits (only `Int` field
  equalities across its two sides, no pending `any` filter). MySQL has no
  FULL JOIN, so the inputs through it become a derived table `__pietto_full`
  (`__pietto_full2`, ... beside an alias of that name in any case): the LEFT
  JOIN, then UNION ALL the RIGHT JOIN rows whose first earlier-input key is
  NULL. A field read after it whose type is not builtin or is `Any`, such as
  an enum, is refused, and so is a relation with more than 8 FULL JOINs, as
  each repeats the inputs before it. Other FULL JOINs keep PostgreSQL's two
  refusals, worded for MySQL, which come before these two for every FULL JOIN
  of the relation; the old `MySQL JOIN emission is not available yet` refusal
  is gone.
- **Aggregate windows.** `sum`, `count`, `avg`, `min` and `max` windows,
  direct, named, over grouped rows, in QUALIFY and over JOIN rows, with the
  grouped MySQL aggregate contract (`SUM` of Int is DECIMAL, `avg` of Int
  casts to DOUBLE). A sliding Float `sum` or `avg` frame assumes MySQL's
  default `windowing_use_high_precision = ON`. As with a grouped `sum`, an
  Int `/` of a `sum` that PostgreSQL holds as `numeric`, such as one over a
  `bigint` column, truncates on MySQL but not yet on PostgreSQL.
- **Window frames.** A GROUPS frame without an offset bound is written as the
  same RANGE frame, and an authored EXCLUDE NO OTHERS is left out. GROUPS with
  an offset bound (`MySQL does not support GROUPS frames with an offset`) and
  EXCLUDE CURRENT ROW, GROUP or TIES (`MySQL does not support EXCLUDE CURRENT
  ROW, GROUP or TIES`) stay refused.
- **`round(Float)` and `date_trunc`.** `round` of a Float rounds a tie away
  from zero with `TRUNCATE` arithmetic, as MySQL's own `ROUND` of a DOUBLE may
  not. It refuses Float arithmetic without a DOUBLE operand in its argument,
  such as `round(amount + 0.5 - 0.00000000000000001)` with an Int `amount`,
  which PostgreSQL computes as `numeric` and MySQL may not, and a read of a
  Float relation output, such as a CTE column, that is not such a DOUBLE;
  `date_trunc` of a Date or Timestamp is built from the value's parts, so a
  unit other than `day`, which repeats the value, refuses a value that holds
  another `date_trunc`.
- **Aliases that differ only in case.** A MySQL JOIN statement with two input
  or `any` aliases whose names differ only in case is refused, as MySQL may
  compare aliases without case: `Its SQL aliases inputs <first> and <second>,
  whose names MySQL may compare without case; rename one of them`. PostgreSQL
  emits them.
- `string_agg`, `matches`, `ignore nulls`, `from last` and RANGE offsets stay
  refused on MySQL.

### Command startup

- Help, version and single-file commands start faster. Running without a
  subcommand still prints help and exits 0.

### Python execution

- `pietto[execute-mysql]` now installs `mysql-connector-python==26.10.0`
  instead of `26.7.0`, and the `mysql_rows` route accepts only `26.10.0`: an
  environment that keeps `26.7.0` is refused with `PIE-R2002` before any
  connection. The connector's connection, protocol, cursor, network and
  authentication modules that `mysql_rows` uses are unchanged in `26.10.0`.
  Its parameter conversion changed only for character sets whose multibyte
  characters can contain `0x5c` (`big5`, `sjis`, `gbk`, and newly `cp932` and
  `gb18030`); the `utf8mb4` connection that `mysql_rows` opens quotes
  parameters as before.
- `pietto[execute-postgres-adbc]` now installs `adbc-driver-postgresql==1.13.0`
  and `adbc-driver-manager==1.13.0` instead of `1.12.0`, and the
  `postgres_adbc` route accepts only `1.13.0`: an environment that keeps
  `1.12.0` is refused with `PIE-R2002` before any connection.
  `adbc-driver-postgresql` `1.13.0` no longer depends on `importlib-resources`,
  so the extra no longer installs it. The `1.13.0` driver returns a PostgreSQL
  `uuid` result column as the canonical `arrow.uuid` type instead of an opaque
  binary value; `postgres_adbc` checks that type and still delivers the same
  `UUID` values. The driver now classifies server errors by SQLSTATE, so the
  exception class in `failure.cause` can differ from `1.12.0`, which reported
  `ProgrammingError` for most of them: a multi-row scalar read (`21000`) now
  reports `OperationalError` and a data exception (class `22`) `DataError`.
  `code` and `sqlstate` are unchanged.

### Project mode

These entries correct `check --project`, `emit-sql --project` and
`explain --project` after a review of 0.1.5 project mode. An entry that also
changes single files says so.

#### Project diagnostics match single files

- Some explicit-module project programs that 0.1.5 refused with a diagnostic
  that hid the problem now report the problem itself, with the single-file
  code, message and position. They are still refused, and no SQL output
  changes:
  - A read after the JOINs of a field that more than one input has, such as
    `id` over `orders` and `customer`, in a SELECT item, an expression,
    a `let` value, WHERE, ORDER BY, a window's PARTITION BY or ORDER BY or a
    GROUP BY key, is PIE-S2335
    `Ambiguous field: id; write orders.id or customer.id` at the read. 0.1.5
    reported the bare PIE-S2333
    `Project relation semantic completion is unavailable: <relation>` at the
    relation, or PIE-S2102 `Unknown field: id` for a GROUP BY key, its
    SELECT item or a window.
  - A JOIN whose input names no relation, such as
    `inner join nosuch on nosuch.id == items.id`, is PIE-S2301
    `Unknown relation: nosuch` at the JOIN. 0.1.5 reported
    `JOIN pre-match input or relationship authority is unavailable.` and
    `JOIN ON reference is unavailable.` (PIE-S2335) instead.
  - A JOIN `on` read reports
    `JOIN ON reference is ambiguous: <f>; write <alternatives>`,
    `JOIN ON reference is unknown: <text>` or
    `JOIN ON reference is forward: <text>` at the read. 0.1.5 reported the
    same code without the read (`JOIN ON reference is unknown.`), after a
    PIE-S2334 `JOIN-local ON is available only when an EXPLICIT_MODULES
    project (schema version 2) completes it.`
  - A read in `any(...)` of a field its row does not have, such as
    `o.nosuch`, is PIE-S2102
    `Unknown or unavailable field in ANY predicate: o.nosuch`. 0.1.5
    reported PIE-S2334 `ANY predicate reference is unavailable.`, which
    remains for a bare name that only the generator row has: a project reads
    a generator field only qualified.
  - In a relation without JOIN inputs, an aggregate, grouping, grouped ORDER
    BY or `having` error is reported at its call or item with its
    single-file code and message: PIE-S2318
    (`Grouped projection is not a GROUP BY key: <f>`), PIE-S2319, PIE-S2320
    (`Grouped output without an aggregate is not supported yet`), PIE-S2312,
    PIE-S2311, PIE-S2314, PIE-S2315, PIE-S2104 for `string_agg` arguments,
    PIE-S2321, PIE-S2323 to PIE-S2327, and in `having` PIE-S2308 for an
    aggregate call (`Aggregate count() is not allowed in having clause; ...`),
    PIE-S2105 for operands and PIE-S2202 for a predicate that is no Bool.
    So are an unknown field (PIE-S2102) in an aggregate call, such as
    `sum(nosuch)`, or in a GROUP BY key, an aggregate's argument count
    (PIE-S2309, `Aggregate function sum expects 1 arguments, got 2`) and
    an invalid LIMIT (PIE-S2307), also beside another grouping error. An
    unknown GROUP BY key that is also selected is reported once, at the
    key, as in a single file. An
    aggregate argument of a field declared with a type alias names the
    alias (`got Whatever`), as in a single file.
    0.1.5 reported the bare PIE-S2333 at the relation. A grouped ORDER BY
    key that names a selected window result is not refused by this check. A relation over a row of unknown type, or one
    that reads a `let` name, a relation, a captured field, a query parameter
    or `any(...)` in those positions, still reports the bare PIE-S2333, and
    so does an aggregate of a shape-typed field. A relation that reports an
    error of its own, such as an unknown field in a grouped SELECT item, no
    longer adds a bare PIE-S2333 beside it.
    This replaces the bare PIE-S2333 that two entries under Checking and
    diagnostics above still name for a relation without JOIN inputs: a
    `string_agg` argument of only `None` values is now PIE-S2104
    (`Invalid arguments for aggregate string_agg: expected two Text arguments`),
    and a qualified input field such as `users.count`, also through a `let`
    alias, in HAVING is PIE-S2327
    (`Unsupported having expression form: qualified name`) and in a grouped
    ORDER BY PIE-S2321
    (`Unsupported grouped ORDER BY item; expected a supported select output name`),
    as in a single file.
  - In a relation without JOIN inputs that a project completes itself, such
    as one with `any(...)` or QUALIFY, an ORDER BY key that names a SELECT
    output is
    ``Unknown field: <name>; this project relation cannot order by a SELECT output yet (restate its expression, or bind it with `let` and order by that name)``,
    as with JOIN inputs. 0.1.5 reported `Unknown field: <name>` alone. An
    invalid LIMIT is PIE-S2307 whatever the ORDER BY key is, where 0.1.5
    reported that ORDER BY error instead.
- In a single file, a relation with JOIN inputs that mixes an aggregate with
  another projection and has ORDER BY reports PIE-S2312, with the PIE-S2380
  of a key that reads an input field outside an aggregate, as without the
  ORDER BY. 0.1.5 reported PIE-S2334
  ``ORDER BY is not available after an ungrouped aggregate over JOIN rows: the result has one row; remove `order by`.``,
  which is now reported only when every projection is an aggregate.
- A call's function is resolved before its arguments, in single files and
  projects. In WHERE, a row `let` and an `any(...)`, as already in a JOIN
  `on`, a call of an unknown function is PIE-S2103 `Unknown function: R`,
  also for a relationship that the module does not declare, and a bare name
  the call is given is no longer read as a field. 0.1.5 reported PIE-S2102
  `Unknown field: <row>` for each row argument instead, with no PIE-S2103;
  inside `any(...)` it reported
  `Unknown or unavailable field in ANY predicate: <row>` in a single file
  and PIE-S2334 `ANY predicate reference is unavailable.` in a project. An
  unknown function is now reported beside an argument's own error, for
  example both `foo` and `bar` in `foo(bar(x))`. In a project, a
  relationship of another module adds
  `; R is a relationship of a.pietto, which a module cannot import: declare it in this module`.
- An explicit-module project reports fewer diagnostics after an error it
  already reports. A relation stopped by an input whose failure is reported
  gets no PIE-S2333, and its JOIN no PIE-S2335
  `JOIN pre-match input or relationship authority is unavailable.` or
  `JOIN ON reference is unavailable.`. Such inputs are:
  - an import that does not resolve, is private or is ambiguous (PIE-S2701,
    PIE-S2705, PIE-S2706);
  - a source whose shape or field type does not resolve (PIE-S2303,
    PIE-S2002), also where another module reports it: an unknown type at a
    field of the shape it imports, or the export its import's target
    refuses (PIE-S2704); the cross-module cases under Known limitations
    below still add the bare PIE-S2333;
  - a name reported as unknown;
  - a relation or table-function body that fails with its own error;
  - an earlier JOIN of the same relation that fails;
  - a relation that a FROM, a JOIN, a set operand or an `any(...)`,
    `exists`, `scalar` or `in` read names and that fails, also one that
    only follows another failure.

  Such a read or operand also drops its own follow-on: PIE-S2334
  `ANY input relation is unavailable.` (and the PIE-S2202
  `ANY predicate requires a known Bool expression.` or PIE-S2335
  `JOIN ON expression type is unavailable.` of an expression around such an
  `any(...)`), PIE-S2348
  `... the columns of <r> are not known before completion.`, PIE-S2342
  `Set operand N has no concrete completed output.` and, in a JOIN's `on`,
  a relationship call's PIE-S2604
  `Unavailable row argument for relationship R parameter p` (a call in an
  `any(...)` over such an input keeps it, as a single file does for an
  unknown ANY relation).
  A read refused in its position (PIE-S2348, PIE-S2349, PIE-S2350) or one
  that closes a relation cycle (PIE-S2302) likewise stops its relation
  without a PIE-S2333 beside it.
  A relationship declaration's own errors now come before the calls that
  cannot use it, as in a single file, and a parameter shape that a failed
  import leaves unresolved reports only the import's error: the
  relationship's calls add no PIE-S2604
  `Relationship predicate R has no unambiguous checked declaration`. A
  relation that reports an error of its own from an earlier stage, such as
  an unknown field in a SELECT item, adds no PIE-S2333 without a cause
  beside it. A source
  without a shape, in a module that reports no other error, now says what it
  needs:
  ``Project relation semantic completion is unavailable: items (source items has no shape, which a project needs to type its rows: write `source items: <shape> = ...`)``.
  A relation stopped by an input whose failure is reported reports its own
  checks, also those that do not depend on the input, such as PIE-S2307 for
  an invalid LIMIT, once that failure is fixed. An
  explicit-module project also never reports the temporary texts
  `... is available only when an EXPLICIT_MODULES project (schema version 2) completes ...`
  of a JOIN kind, a JOIN-local `on` or a set operation; such an operation
  reports what stops it, such as PIE-S2341. 0.1.5 reported these follow-on
  diagnostics beside the root error. Each read of an unknown relation name
  is its own PIE-S2301, a set operand too: another relation's read of the
  same name does not stand in for it. 0.1.5 reported only PIE-S2334 at such
  a set operation.

#### Module diagnostics

- A failed import is no longer masked. In an explicit-module project, the
  module import and export errors (PIE-S2701, PIE-S2705, PIE-S2706,
  PIE-S2707) are reported even when a query has a query-local naming error,
  a `def` error (PIE-S2397), a query header error (such as PIE-S2001
  `Duplicate parameter name in query p: cutoff` or PIE-S2354) or a query
  parameter in a position that does not take one (PIE-S2355). They come
  first, ahead of the errors that stop the check before semantic analysis,
  for every module, in `check --project` and in `emit-sql --project`, once
  every module parses and its syntax is admitted. 0.1.5 dropped the module
  errors of every module.
  A `let` whose value is a relation that the module imports but cannot bind,
  as in `let c = customers` with `customers` not exported by its target, now
  reads that name as `inner join customers` would, and the import's own
  error reports it; 0.1.5 reported only PIE-S2604
  (`A row-value let must follow FROM and every JOIN and precede WHERE`) at
  the `let`. The PIE-S2301 `Unknown relation: <name>` of the `let` entry
  under Checking and diagnostics above is only for a name the module never
  imports.
- An import that names the wrong kind, such as `shape customers` for an
  exported `source customers`, is PIE-S2705 at the imported name:
  `Imported declaration has another kind: shape customers from "a.pietto" is a source; write source customers`.
  0.1.5 reported PIE-S2707
  `Inconsistent explicit-module target facade: "a.pietto"` at the target
  path, once per import statement. A relation read of such a name, as in
  `let c = customers`, follows that error as for a failed `source` import,
  and the other modules' errors are still reported; when the target also
  has the name as the requested kind or another kind of its namespace, such
  as a shape for `type customers`, privately or not, the module never
  imported the relation, and such a read is its own PIE-S2301. Likewise, a
  type use of a name that the import asks for with a relation kind, as in
  `source Customer` or `query Customer` for a shape, follows that error,
  unless the module declares a type of that name: no PIE-S2002 or PIE-S2303
  repeats its advice (a source in another module whose field type is an
  alias of such a name still adds the bare PIE-S2333; see Known
  limitations). When the target declares the requested
  kind but exports only another kind of that name, it is PIE-S2705
  `Imported declaration is private or not exported: ...`. An unknown export
  of a name that the module declares only with another kind names that
  kind: `Unknown export binding: type Customer; Customer is a shape`, and an
  export of a name that the module imports only with another kind names the
  imported kind:
  `Invalid imported export candidate: type Customer; Customer is a shape`.
  A wrong-kind import through a re-export points at the re-exporting
  module's import of the name, as a direct one points at the declaration.
- An import of a name that its target module only imports itself, with the
  same kind, no longer says the name is unknown. When the target does not
  export it, it is PIE-S2705
  `Imported declaration is private or not exported: shape Row from "b.pietto"`;
  when the target re-exports it but its own import of it fails, it is
  PIE-S2705
  `Imported declaration is unavailable: shape Row from "b.pietto", whose own import of Row fails`.
  Both point at the target's import of the name. 0.1.5 reported
  `Unknown imported declaration: shape Row from "b.pietto"`, with no
  related location.
- A re-export of a re-export now resolves through any number of modules, to
  the one original declaration. 0.1.5 rejected the third hop and beyond with
  PIE-S2705 `Unknown imported declaration`, plus a PIE-S2333 for each
  reader. Each further hop resolves the project's imports once more, so a
  chain of hundreds of re-exports takes tens of seconds to check.
- PIE-S2701 names up to three selected paths that an unresolved import
  target may have meant:
  `Unresolved module import target: "a.pietto"; did you mean "models/a.pietto"? An import path is the project-root-relative path of a selected source, with / separators`.
  0.1.5 reported `Unresolved module import target: "a.pietto"` alone.
  The target and the paths are quoted as Pietto strings, so a non-ASCII
  character stays as written; 0.1.5 echoed the target with `\u` escapes. A
  control character, which a file name rarely holds, is still shown as a
  `\u00XX` escape, which a Pietto string does not accept. A path that is not
  valid UTF-8, which no Pietto string spells, is never suggested.
  The language reference now states that an import target is the
  project-root-relative path of a selected source, with `/` separators.
- An unknown name that other selected modules export now says where and how
  to import it, for PIE-S2002 `Unknown type`, PIE-S2303
  `Unknown source shape`, PIE-S2604 `Unknown relationship parameter shape`
  and PIE-S2301 `Unknown relation`, for example
  `Unknown relationship parameter shape: Order; Order is a shape exported by types.pietto: import it with from "types.pietto" import (shape Order)`.
  Every exporter is listed in path order, at most three in full, and none is
  chosen. An exporter is an export that resolves: an export that is itself
  refused (PIE-S2704), a duplicate export request included, or a re-export
  whose own import fails, is not named, nor is a module whose path is not
  valid UTF-8, which no import can spell. A module that already declares or
  imports the name, in either namespace, such as a `source Customer` or an
  `import (source X as Customer)` beside a use of the shape `Customer`, gets
  no hint, since that import would collide with the declaration or binding
  (PIE-S2706).
  PIE-S2103 for a `def` that only other modules declare adds
  `; twice is a def of a.pietto, which a module cannot import: declare it in this module`.
  0.1.5 reported each of these messages without the hint.

#### Stricter checks

- `check --project` in an explicit-module (`schema_version = 2`) project now
  runs in each module the declaration checks a single file runs, with the
  same codes, messages and positions, reading each type name as the module
  declares or imports it. 0.1.5 printed `Project check OK` (exit 0) for
  these projects, and `emit-sql --project` emitted a VERIFIED artifact for
  their tables and queries. Now `check --project` reports these errors
  (exit 1), and `emit-sql --project` is BLOCKED with them. They follow each
  module's enum and shape declaration diagnostics, module by module, each
  module's in source order. While any import cycle (PIE-S2703) exists, these
  checks wait in every module, as the other completion checks do, and are
  reported once every cycle is fixed. The newly refused forms are:
  - Decimal type arguments out of range or misspelled, in shape fields, type
    aliases and constraint or derive signatures (PIE-S2004), such as
    `amount: Decimal(1, 2)`, `type M = Decimal(5, 9)`, `Decimal(66, 0)` or
    `Decimal(precision = 9, scale = 2)`. For such a field
    `emit-sql --project` reported the emission blocker PIE-B1004; it now
    reports PIE-S2004 at the field's type, and a project `select distinct`
    over such a field reports PIE-S2004 before PIE-S2339. A plain `Decimal`
    or `Decimal()` still passes `check --project`, and emission still blocks
    it with PIE-B1004;
  - a repeated constraint or derive name (PIE-S2001
    `Duplicate symbol name in callable namespace: N`) or parameter name
    (PIE-S2001 `Duplicate parameter name in ...`);
  - an unknown type in a constraint or derive signature (PIE-S2002); a name
    already blocked by an import collision, a duplicate type declaration, or
    a failed import of a type or of a name its target has only as a type,
    reports only that error, as at a shape field;
  - a constraint whose declared type is not Bool (PIE-S2401);
  - a constraint, derive or field `derive` body whose type does not match
    its declaration (PIE-S2402);
  - errors inside constraint and derive bodies, shape `check(...)`,
    `index ... when` predicates and field `derive` bodies, such as an unknown
    name (PIE-S2102), invalid operands (PIE-S2105), a check that is not Bool
    (PIE-S2202), an aggregate (PIE-S2308) or a `def` argument that does not
    fit its parameter (PIE-S2395);
  - a derived-field cycle (PIE-S2504).
- A bare name in `any(...)` that both the outer row and the generator row
  have, such as `price` in `where any(o.price == price for o in orders)`
  over `items`, is PIE-S2102 `Ambiguous field in ANY predicate: price` in
  WHERE, SELECT and `let` of an explicit-module project, as in a single
  file. 0.1.5 accepted it at `check --project`, and `emit-sql --project`
  read the outer row's `price`.
- In an explicit-module relation without JOIN inputs or GROUP BY, an ORDER BY
  key that reads a field the relation does not have, also through a field of
  a shape (`home.nosuch`), is PIE-S2102 `Unknown field: <name>`, a call of an
  unknown function is PIE-S2103 `Unknown function: <name>` (with the
  `def of <module>` hint for a `def` of another module), and a key written
  as a bare constant (`"x"`, `-1`) is PIE-S2380, as in a single file. A
  SELECT output is a key only as the whole key, so `-total` with an output
  `total` that is no input field is PIE-S2102. 0.1.5 accepted all of these at
  `check --project`, and `emit-sql --project` blocked them with PIE-B1003. A
  constant that a `let` name binds is still ordered by as a value, and such
  keys are still not typed: `order by lower(status)` passes
  `check --project`.
- Import and export statements outside a `schema_version = 2` project are no
  longer silently ignored (new PIE-S2708). 0.1.5 ignored them in single
  files and in `schema_version = 1` projects, so an unresolved import, or an
  export of an undeclared name, passed `check`, and single-file `emit-sql`
  emitted SQL.
  - A single-file command now warns at each import and export statement in
    every check mode:
    `Module import is resolved only by check --project ROOT, in a schema_version = 2 project`,
    with `Module export` for an export. An editor can still check one module
    file alone.
  - `check --project` of a `schema_version = 1` project refuses each such
    statement with a PIE-S2708 error:
    `Module import is read only in a schema_version = 2 project: set schema_version = 2 in pietto.toml`.
    A schema-1 project with import or export statements that 0.1.5 accepted
    now fails `check --project`.

#### Project CLI and JSON

- `result.check.files_with_errors` of `check --project --format json` now
  counts every input that is the primary location of an error diagnostic,
  parse or semantic, and `files_ok` is `files_total - files_with_errors`.
  0.1.5 counted parse status only, so a file with only a semantic error
  counted as ok. The keys are unchanged. `result` and `inputs[].kind`
  (`"source"`) are now documented in project CLI JSON v2.
- Explicit-module (schema 2) project JSON v2 diagnostics from the module
  graph, import binding and module resolution now carry the related
  locations those owners compute, each with a `null` message: for example,
  PIE-S2705 points at the private declaration and PIE-S2706 at the colliding
  local declaration. 0.1.5 always wrote `[]`. Legacy-flat (schema 1)
  diagnostics keep `[]`.
- Wrong project schema, still of kind `config_schema`:
  - `check --project` and `emit-sql --project` on a schema 3 or 4
    package-root project now say
    `check --project reads schema_version 1 or 2 projects and emit-sql --project schema_version 2 ones; this schema_version N package-root project is read by explain --project`
    (schema 3 adds ` once converted to schema_version 4`), with the path
    `pietto.toml`. 0.1.5 said
    `Schema-vN ... does not use project source selection.` with a null path.
  - `emit-sql --project` on schema 1 now says it needs `schema_version = 2`
    and to declare cross-file names with import and export. 0.1.5 said
    `Project emit-sql requires the explicit-module project mode.`
- Source patterns and selection:
  - Each pattern fault has its own message: `must use / as the path separator`,
    `must be relative to the project root`,
    `must be a normalized project-relative pattern`, or
    `uses unsupported glob syntax; patterns use only *, ? and a whole ** path part`.
    Unsupported glob syntax is now `project_glob`; it was `project_path`.
  - `matched no .pietto files` now carries the path `pietto.toml` and the
    include and exclude lists.
  - A `pietto.toml` that starts with a UTF-8 BOM now gets
    `pietto.toml starts with a UTF-8 byte-order mark; save it as UTF-8 without BOM.`
    0.1.5 gave a TOML `Invalid statement` error. Such a file is still
    refused.
  - A decimal integer longer than 4300 digits in `pietto.toml` is now
    `config_parse`
    (`Project configuration TOML is invalid: Exceeds the limit (4300 digits) for integer string conversion: value has N digits.`),
    and in a package manifest `Package manifest TOML is invalid.` 0.1.5
    printed a Python traceback in `check --project` and `explain --project`,
    and `emit-sql --project` reported `project_root`
    `Project root could not be pinned.`
  - Selection no longer lists a directory that no include pattern can
    reach, or that an exclude covers completely (`dir/**`), so an unreadable
    directory there, such as a database data directory, no longer fails the
    project. One that could hold a selected file still fails with
    `project_glob`.
- CLI usage:
  - `--project ''` and `--project=` are now a usage error,
    `argument --project: Project root must be a non-empty path.`, in
    `check`, `explain` and `emit-sql`. 0.1.5 used the working directory.
  - In text mode, giving a project directory as the file adds
    `hint: for a project use pietto <command> --project <dir>` when that
    command's `--project` reads the project's schema version (`check` 1 or
    2, `emit-sql` 2, `explain` 4); the `emit-sql` hint also names the
    arguments it needs (`--module FILE --kind KIND --name NAME --dialect DIALECT --emission-contract FILE`).
    JSON v1 output is unchanged.
- Project Explain package diagnostics:
  - A stale dependency pin now reads
    `In dependency package ns/name@ver: Package content digest does not match the sha256 pinned by [[dependencies]] in <declaring package>.`
    0.1.5 blamed `the declared root sha256`.
  - Every error and diagnostic from a dependency package names that
    package.
  - A root-manifest schema error's location kind is now `project_relative`;
    it was `package_relative`.

#### Project SQL emission

- Selector errors: `Selected owner is absent or ambiguous.` is now kept only
  for more than one match. With no match, the error lists the project
  modules, with a `/`-separator hint, or the declarations of that kind in
  the module. The `--module` help shows `models/queries.pietto`. Contract
  source selectors list the modules with sources, or the module's sources.
- Contract errors keep their kinds:
  - `Invalid emission contract structure.` now names the missing key, which
    the path points at, and the expected keys. An unexpected key is counted,
    not echoed.
  - A field-name mismatch says `Field ordinal N must be named <field>`.
  - A contract source selector with an empty `module` or `name`, or a `kind`
    other than `source`, names that key (`sources/0/selector/module`) and
    says what it must be, as `Source selector module must be a non-empty string; modules with sources: <modules>.`
  - `Invalid UTF-8 JSON emission input.` is split into a BOM, non-UTF-8,
    `Invalid JSON emission input: <reason> (line L, column C)`, a duplicate
    key, a non-finite number (`NaN`, `Infinity`, or one that overflows, such
    as `1e400`), nesting depth, an integer of more than 4300 digits
    (`Invalid JSON emission input: Exceeds the limit (4300 digits) for integer string conversion: value has N digits.`),
    and a string with an unpaired surrogate escape such as `"\ud800"`
    (`Emission contract strings must not hold a lone surrogate escape (\uD800-\uDFFF).`).
- A selected source whose file name is not valid UTF-8, which `check
  --project` reads, now makes `emit-sql --project` INPUT_REJECTED
  `project_path`
  `Project source path must be valid UTF-8 to emit SQL: "\udcff.pietto"; rename it.`
  (exit `2`) where a path in the document would name it: in place of SQL,
  whose request lists every selected source; in place of the diagnostics
  and blockers located in that file, which the document leaves out; and
  beside another input error about it or about such a source directory,
  such as `source_read` or `project_glob`, whose `path` is then null. An
  emission document is UTF-8, where such a name has no text. A message that
  names it, such as a PIE-S2103 hint for a `def` it declares or the
  `--module` listing of an `emission_selector` error, shows it escaped as
  in `project_path` (`m\udcff/a.pietto`) and is kept with its status
  and exit code. A PIE-S2701 suggestion or an import hint never names it,
  since no import can spell it. A project that is refused for another reason (a schema 1
  project, a parse or semantic error in another file, or the selected
  owner's blocker, selector, contract or `--dialect`) reports that as
  before. In place of SQL, in a diagnostic located in such a file and
  beside an input error about it, 0.1.5 printed
  `pietto: error: terminal output could not be encoded` and no document,
  also with `--format json`. So did an `--emission-contract` path that is
  not valid UTF-8 and cannot be opened; its `emission_contract_read` error
  now has `path` null.
- Blocker places and reasons, with codes unchanged except where stated:
  - Plan-stage refusals (`order`, `group`, `join`, `window`, ...) are
    located at their ORDER BY item or clause, not the whole declaration.
  - `count`, `count_distinct`, `min` and `max` over Decimal or Float are now
    PIE-B1003 `<fn>_argument_outside_reviewed_int_domain`; they were
    PIE-B1004 `decimal_aggregate_range_proof_missing` or
    `float_aggregate_finite_result_proof_missing`. Only `sum` and `avg` keep
    those proofs.
  - Every refused aggregate is reported at its own item; 0.1.5 reported only
    the first.
  - A refused group key is located at its GROUP BY item; 0.1.5 had location
    null.
  - `complete_ordered_source_schema_required` is located at the source
    declaration, with related locations at the shape fields the contract
    leaves out or maps out of order. A JOIN that reads such a left-out field
    reports `join_input_source_field_not_bound` at the same source; 0.1.5
    had location null.
- Text failure output now follows a premise, release, `order` or Int-range
  blocker with a `hint:` line naming the reviewed value or remedy, for
  example
  `add {"key":"client_encoding","scope":"statement","value":"UTF8"} to "environment"`
  or `the reviewed mysql value is {..."lower_case_table_names=0"}`, and
  prints `related:` locations. The Int-range hint names no storage type,
  since the field's own storage bounds the result. JSON detail tokens are unchanged, and
  `pietto.execution` refusal text matches the CLI.

#### Performance

- A project whose relations read earlier relations along several paths, for
  example `from` the previous relation and `any(...)` over the one before
  it, no longer takes minutes to report an error in an early relation: each
  relation's error report now visits every shared upstream result once.
- An import cycle (PIE-S2703) is reported several times sooner, for example
  a 40-module cycle in about 4 s instead of about 20 s, and an 80-module
  cycle in about 15 s instead of about two minutes: the private module
  inspection now derives each record kind's key sets once instead of once
  per checked scope. Its private cycle records still grow with the cube of
  the cycle length, so very long cycles stay slow.
- These two changes leave results, diagnostics and output unchanged.

#### Documentation

- The [project guide](project-package.md) starts from a minimal
  `schema_version = 2` `pietto.toml` and describes schema 1 as the
  legacy-flat mode, with no JOIN, no `any(...)` and no SQL emission. It
  documents the `[sources]` pattern rules, the per-file resource limits
  (1 MiB of UTF-8, PIE-P1006, and 200,000 tokens, PIE-P1007; the number of
  files, their total size and `pietto.toml` are not limited), and which
  schema each command reads: `check --project` 1 and 2,
  `emit-sql --project` 2, and `explain --project` only 4. A schema 3
  project converts by setting 4 and adding an empty
  `[capability_environment]`.
- Its new section on explaining a package-root project gives a copyable
  schema-4 layout with a schema-2 configuration beside it, a package
  manifest, a standard-library script that computes the package digest, and
  a target example. `explain --project` reports package and capability
  portability, not module semantics, and stops before dependencies when the
  root package fails to load.
- Its project SQL emission section documents the reviewed target releases
  (PostgreSQL 18.6 and MySQL 8.4.12), the field representation of each
  logical type per dialect, each premise's values per dialect and when it is
  needed, a MySQL contract example, that `--output` always writes the JSON
  artifact, and the forms that `check --project` accepts and
  `emit-sql --project` refuses.
- The [configuration contract](spec/pietto-config-v1.md) is rewritten as the
  implemented contract: `schema_version` 1 to 4 with the keys each allows,
  no `[project]` table, an optional `exclude`, the `[package]` and
  `[capability_environment]` tables, and the error kinds.
  [Project CLI JSON v2](spec/project-cli-json-v2.md) marks
  `explain --project` as the separate Project Explain JSON v1 command that
  needs schema 4 and lists the `emission_contract_read`,
  `emission_contract_schema` and `emission_selector` error kinds.
- The README links the new sections, and its Slice13 contract link points at
  the current specification on `main` instead of v0.1.1. The
  [roadmap](roadmap.md) records `explain` for schema 2 projects and wider
  project SQL emission (a PostgreSQL/MySQL parity batch) as follow-ups.

#### Known limitations

These project-mode limits remain. None of them produces wrong SQL.

- **Layered JOIN DAGs are slow to check.** When each relation JOINs the
  relation before it and the one before that, `check --project` and
  `emit-sql --project` take about 2 to 3 times as long for every two more
  layers: a few seconds at 16 layers, and tens of seconds at 20 to 22. This
  release is faster than 0.1.5 on such projects, but the grain that a
  project keeps for each JOIN still copies the factors of every path to its
  inputs; sharing them is deferred (see the [roadmap](roadmap.md)). Only the
  time is affected, and single-file checks are not.
- **A bare PIE-S2333 can hide later errors.** Some relations that a single
  file accepts, or refuses with another code, are still the bare PIE-S2333
  `Project relation semantic completion is unavailable: <r>` in a project,
  for example one whose SELECT output is an always-null number such as
  `o0 = None - 3.0`. The relations that read it report nothing of their own,
  such as an invalid LIMIT, until it is fixed. The
  [diagnostics reference](spec/diagnostics.md#semantic-diagnostics) lists
  these cases.
- **A cross-module shape error can add a bare PIE-S2333.** A source whose
  shape, imported from another module, fails for an error inside its
  declaration other than an unknown type, such as a duplicate field
  (PIE-S2501), still adds the bare PIE-S2333 at the source beside that
  error, where a shape in the source's own module reports only the error.
  So does a source whose field type is an alias, declared in another
  module, of a name that module imports with a relation kind (PIE-S2705).
- **A source without a shape is quiet beside another error.** In a module
  that reports another error, a source without a shape gets no PIE-S2333,
  and so no `(source items has no shape, ...)` advice, until that error is
  fixed.
- **An exported duplicate declaration.** A module that declares a source or
  shape twice and exports it reports PIE-S2704
  `Ambiguous local export declaration: source s` at the export; a single
  file, or the module without that export, reports PIE-S2001 at the second
  declaration.
- **A non-UTF-8 unrecognized argument to `emit-sql --project`.** With JSON
  output, an unrecognized argument that holds a byte that is not valid
  UTF-8 prints `pietto: error: terminal output could not be encoded` on
  stderr and no `INPUT_REJECTED` usage document (exit `2`), as 0.1.5 did;
  `--format text` prints the usage error.
- **A mixed aggregate JOIN.** A relation with JOIN inputs that mixes an
  aggregate with another projection reports only PIE-S2312 in a project,
  with or without ORDER BY. A single file also reports PIE-S2381 when an
  aggregate may read rows repeated by a JOIN and, with ORDER BY, the
  PIE-S2380 of an ORDER BY key that reads an input field outside an
  aggregate. A project relation whose projections are all aggregates still
  reports that fan-out, as a PIE-S2333 with its cause.
- **A relation-name qualifier through a `let` alias is accepted.** After
  `let c = customers` and `from c`, a read such as `customers.price` is
  accepted by `check --project`, and `emit-sql --project` reads the field of
  `c`, while a single file refuses it with PIE-S2102
  `Unknown field: customers.price`. Refusing it in a project would refuse
  programs that check today, so it waits for a decision. The change after
  `0.1.6` that refuses it is described under
  [Unreleased changes following 0.1.6](#unreleased-changes-following-016).
- **A repeated unknown SELECT item.** A SELECT item of an unknown name
  written twice, such as `nosuch`, reports PIE-S2102 at both items in a
  project; a single file reports it at the first, with the PIE-S2305 that
  both report.
- **An import after the target's own import fails.** When the target module
  re-exports a name whose own import of it fails, or imports a name and
  exports it with another kind, an import of the name from that module
  still adds PIE-S2705 (`Imported declaration is unavailable: ...` or
  `Imported declaration is private or not exported: ...`) beside the
  target's error, which it follows. An import of the very kind and name
  whose export the target refuses (PIE-S2704) adds nothing.

### Still deferred

- Reporting a swapped argument pair as one diagnostic, which the 0.1.5 notes
  deferred, is not in this release: a relationship call whose arguments are
  given in the wrong order, such as `PlacedBy(customers, order)` for
  `relationship PlacedBy(order: Order, customer: Customer)`, still reports
  PIE-S2604 at each argument.

### Corrections after publication

These notes were corrected after `0.1.6` was published; the release itself
is unchanged.

- The Project mode highlight said that a failed import keeps its single-file
  code, message and position. A single file resolves no import, so it has no
  such code; the highlight now says what changed, as
  [Module diagnostics](#module-diagnostics) describes: the import error is no
  longer masked, and the relations that read the failed import add no bare
  `PIE-S2333`.
- The known limitation of a mixed aggregate JOIN named only an ORDER BY
  case and the PIE-S2380 that a single file adds. It now also names the
  fan-out PIE-S2381 that a single file reports, with or without ORDER BY.
- The section [Still deferred](#still-deferred) was added: the 0.1.5 notes
  deferred reporting a swapped argument pair as one diagnostic, and these
  notes did not say that it stays deferred.
- The known limitation that a project accepts a relation-name qualifier
  through a `let` alias now points to the change after `0.1.6` that refuses
  it; `0.1.6` itself accepts such a read.

## Modern-syntax public alpha release notes — 0.1.5

**Status:** These notes cover the `0.1.5` public alpha, published from
`6d0f6c6c` on the versioned GitHub pre-release and PyPI. Both channels carry the
accepted wheel and sdist byte for byte; this document neither creates those
channels nor substitutes for their byte verification.

`0.1.5` is the first release whose compiler reads the modern source syntax. It
also contains the single-file JOIN support and the
[fix batch 7](#fix-batch-7-following-014-included-in-015) changes; the fix
batch 7 section keeps the 0.1.4 spelling in its examples. The sections from
0.1.4 down describe published files.

### Highlights

- **Modern source syntax.** `None`, `True` and `False`; `T` for a value that
  is never None and `T | None` for one that may be; `source name: Shape = ...`;
  single-line clauses without a colon; one `let` per name; shape-typed
  relationship predicates; and `any(predicate for row in relation)`.
- **`pietto migrate`** writes the modern form of a 0.1.4 file to stdout, or
  names each place that needs a manual decision.
- **Single-file JOINs.** `check` and PostgreSQL `emit-sql` accept INNER, LEFT,
  RIGHT, FULL and CROSS JOINs and `any`/`not any` filters over the sources,
  tables and queries of one file, within the
  [single-file JOIN limits](language.md#single-file-joins).
- **Diagnostics teach the modern spelling.** Each retired spelling is
  PIE-P1000 with its exact rewrite in the message.

### Upgrading a 0.1.4 file

Each spelling that the modern syntax retires is a syntax error (PIE-P1000)
whose message ends with the rewrite, such as
`This spelling is not accepted by the modern syntax. Write 'is None' or 'is not None'.`;
JSON output carries the rewrite as the diagnostic's `suggestion`. A
`pietto NUMBER` header does not select a syntax, and no flag restores the old
one. To convert a file, write the result to a new file and check it:

```bash
pietto migrate old.pietto > migrated.pietto
pietto check migrated.pietto
```

`migrate` never edits its input. It writes one complete source to stdout only
when the result passes the modern parser; otherwise it exits 1, writes nothing
to stdout and reports PIE-P1011 at every place that needs a decision, in
source order. It keeps comments, strings, line endings and a leading BOM, and
it neither checks SQL backend capability nor connects to a database. It
changes only what it must, so its output keeps the old layout around each
rewrite (for example an indented empty line where a `let:` header was);
`check` the result and tidy it by hand. Compiled bundles and saved-job records
are not source and are not migrated.

For example, this 0.1.4 file:

```text
shape Order:
    id: Int not null
    customer_id: Int not null
    amount: Int not null
    note: Text nullable

source orders: Order is postgres.table("orders")

query customer_totals:
    from orders
    where: amount between 100 and 500 and note is not null
    group by: customer_id
    select:
        customer_id
        total = sum(amount)
        n = count()
    satisfying: n > 1
    order by: customer_id
```

migrates to:

```pietto
shape Order:
    id: Int
    customer_id: Int
    amount: Int
    note: Text | None

source orders: Order = postgres.table("orders")

query customer_totals:
    from orders
    where 100 <= amount <= 500 and note is not None
    group by customer_id
    select:
        customer_id
        total = sum(amount)
        n = count()
    having n > 1
    order by customer_id
```

`migrate` also turns `null`, `true` and `false` into `None`, `True` and
`False`, a `let:` block into one `let` per name and `cast(x as Float)` into
`Float(x)`. It needs a manual decision (PIE-P1011) for a 0.1.4 JOIN written
with `as`, including `semi join` and `anti join`, and for a source-bound
`relationship` with endpoints: write `let name = relation`, a JOIN with `on`
or a [relationship predicate](language.md#named-inputs-and-reusable-relationship-predicates)
instead. A `schema_version = 1` project with such JOINs also needs
`schema_version = 2` (see
[legacy-flat projects](#legacy-flat-projects-and-relationship-joins)).
[Migrating old source](language.md#migrating-old-source) lists every rule.

### Syntax changes

Each example shows 0.1.4 source, then the source this release reads, except
where it says otherwise.

#### A bare type is never None

0.1.4 had three nullability states: `T not null`, `T nullable` and a bare `T`
of unknown nullability. Now `T` is never None and `T | None` may be None;
`not null` and `nullable` are PIE-P1000. `migrate` rewrites `T not null` to `T`
and both `T nullable` and a bare `T` to `T | None`, so it never adds a claim
that a value is not None: drop each `| None` it added to a bare type where the
column is in fact never NULL. A `type` alias names a type that is never None:
write `Email | None` where a field is declared. A `nullable` alias base needs
manual migration (PIE-P1011), and so does a bare type in a source that the
modern syntax also accepts, whose meaning changed, or that mixes 0.1.4
spelling with modern spelling that `migrate`'s reader of 0.1.4 source cannot
read, such as `T | None` (that reader also reads some modern spelling, such as
`source name: Shape = ...`, which does not count): `migrate` cannot tell which
syntax such a bare type was written for, so it never adds `| None` to it.

```text
shape User:
    id: Int not null
    nickname: Text
    email: Text nullable

source users: User is postgres.table("users")

table user_contacts:
    from users
    select:
        id
        nickname
        email
```

```pietto
shape User:
    id: Int
    nickname: Text | None
    email: Text | None

source users: User = postgres.table("users")

table user_contacts:
    from users
    select:
        id
        nickname
        email
```

#### Names after `select`

`select` may list a `let` name directly, and outside a grouped query an
`order by` key written as one name may name a SELECT output, as grouped
queries and `having` already could. A key that names both an input field and a
SELECT output of another value is now ambiguous (PIE-S2102) instead of
silently reading the input field: `migrate` qualifies such a 0.1.4 key
(`order by order_lines.quantity`) where the FROM input is a source of the same
file with that field in its shape, keeps it where that source has no shape or
its shape lacks the field, and asks for a decision (PIE-P1011) over JOIN
inputs or any other FROM input.
A single-file query with GROUP BY still cannot select a `let` name
(PIE-S2329). Without GROUP BY, project SQL cannot yet order by a SELECT output
other than a window result (PIE-B1003 at `emit-sql --project`, or PIE-S2102 at
`check --project` with JOIN inputs).

In 0.1.4 one value needed two names:

```text
query biggest_lines:
    from order_lines
    let:
        total_cents = price_cents * quantity
    select:
        id
        line_total = total_cents
    order by:
        total_cents desc
```

```pietto
shape OrderLine:
    id: Int
    price_cents: Int
    quantity: Int

source order_lines: OrderLine = postgres.table("order_lines")

query biggest_lines:
    from order_lines
    select id, total_cents = price_cents * quantity
    order by total_cents desc
```

`let total_cents = price_cents * quantity` with `select id, total_cents` is
the same query.

#### `any` and `not any` replace `semi join` and `anti join`

`semi join` and `anti join` are PIE-P1000. Write
`where any(predicate for row in relation)` or `where not any(...)`: before a
later JOIN the filter keeps the rows at that point, and after the last JOIN it
is the relation's WHERE. Both emit the same correlated `EXISTS` or
`NOT EXISTS`. 0.1.4 wrote every `semi join` and `anti join` with `as`: such a
JOIN is PIE-P1000 at its `as`, suggesting the `where any(...)` or
`where not any(...)` rewrite. `migrate` rewrites only `semi join x on p` and
`anti join x on p` themselves, written without `as`; one without `on`, and
each one written with `as`, is refused with PIE-P1011 (see
[migrating old source](language.md#migrating-old-source) for every case). The
explicit-module whole-relation read `exists name` is unchanged. See the R2
limitation under [known limitations](#known-limitations).

0.1.4 accepted this query only in an explicit-module project (a single file
reported PIE-S2334 at the JOIN); its modern form also checks as a single file:

```text
query customers_without_orders:
    from customers
    anti join orders as o:
        from customers
        on o.customer_id == customers.id
    select:
        id
        name
```

```pietto
shape Customer:
    id: Int
    name: Text

shape Order:
    id: Int
    customer_id: Int

source customers: Customer = postgres.table("customers")

source orders: Order = postgres.table("orders")

query customers_without_orders:
    from customers
    where not any(o.customer_id == customers.id for o in orders)
    select id, name
```

#### Named windows come before `select`

A named window is a `let name = window(...)` among the lets after FROM and
every JOIN, before `where`, `group by` and `select`; one declared after
`select` is PIE-P1000 (`Move the window before 'select', ...`). Windows share
the `let` namespace: a window named like a value `let` or an input alias is
PIE-S2604, and a window may not take the name of an input relation or input
field (PIE-S2329). `migrate` moves a window declared after `select`, with its
comment lines, to the end of the lets, and asks for a decision (PIE-P1011)
when its name clashes.

```text
query ranked:
    from accounts
    select:
        id
        position = row_number() window ordered
    window ordered:
        order by:
            id
```

```pietto
shape Account:
    id: Int
    account_id: Int

source accounts: Account = postgres.table("accounts")

query ranked:
    from accounts
    let ordered = window(order by id)
    select:
        id
        position = row_number() window ordered
```

#### One-line forms

An `enum` may list its members on its header line after `:`; the indented
form remains, and an enum header without `:` is PIE-P1000. A `def`,
relationship predicate, `constraint` or `derive` body may follow its header on
the same line. A `qualify:` block joins its lines with `and`, as `where:` and
`having:` do.

```text
enum Status:
    active
    suspended
```

```pietto
enum Status: active, suspended

shape Item:
    id: Int
    status: Status
    price: Int

source items: Item = postgres.table("items")

query top_items:
    from items
    where status == "active"
    select id, price
    qualify:
        row_number() window(order by price desc) <= 3
        price > 0
```

Single-file QUALIFY is checked but not lowered: `explain` and `emit-sql` still
refuse it with PIE-I1000.

#### Diagnostics teach the modern spelling

Messages name only modern spelling and state the fix within the diagnostic's
one line of text output. The fan-out remedies of
PIE-S2381 and PIE-S2333 no longer suggest grouping by a unique key, which
compiles but changes the result's grain.

0.1.4 for `where email == null`:

```text
users.pietto:9:11 PIE-S2105 error: Invalid operands for operator ==: comparison with null is never true; write `is null` instead
```

This release for `where email == None`, then for `where email is null`:

```text
users.pietto:9:11 PIE-S2105 error: Invalid operands for operator ==: comparison with null is never true; write `is None` instead
users.pietto:9:20 PIE-P1000 error: This spelling is not accepted by the modern syntax. Write 'is None' or 'is not None'.
```

```pietto
shape User:
    id: Int
    email: Text | None

source users: User = postgres.table("users")

table missing_email:
    from users
    where email is None
    select id
```

#### Reading a table or query of the same file warns

Single-file SQL emits each table and query as its own statement, so a `from`,
a JOIN or an `any(...)` before a later JOIN that reads a table or query of the
same file reads it by name: that SQL runs only where the database already has
a relation of that name. Each such read is now a PIE-S2382 warning in every
check mode; an explicit-module project emits the relation it reads as a CTE.
Any other `any(...)`, such as one after the last JOIN, defines the relation it
reads as a CTE of the reader's SQL and has no such warning.
The text output of `emit-sql` is unchanged in this release (see
[deferred to the next release](#deferred-to-the-next-release)).

0.1.4 checked such a file, written in its spelling, without a diagnostic.
This example is in the spelling of this release:

```text
shape Order:
    id: Int
    amount: Int

source orders: Order = postgres.table("orders")

table large_orders:
    from orders
    where amount > 100
    select id, amount

query large_order_ids:
    from large_orders
    select id
```

now reports:

```text
orders.pietto:13:5 PIE-S2382 warning: `large_orders` is a table of this file; single-file SQL reads it by name, so the SQL runs only where the database already has a relation named large_orders (an EXPLICIT_MODULES project emits it as a CTE)
```

Reading the source directly needs no such relation:

```pietto
shape Order:
    id: Int
    amount: Int

source orders: Order = postgres.table("orders")

query large_order_ids:
    from orders
    where amount > 100
    select id
```

### Single-file JOINs

No published release emits a single-file JOIN: 0.1.4 refused JOIN forms in
single files (PIE-S2334 at `check`, or PIE-I1000 at `explain` and
`emit-sql`), and the support merged after 0.1.4 spelled JOINs the 0.1.4 way.
This release offers them in modern spelling. Name each JOIN input with `let` and give every
JOIN but CROSS an `on`:

```pietto
shape Customer:
    id: Int
    name: Text
    customer_key = unique(id)

shape Order:
    id: Int
    customer_id: Int
    amount: Int

source customers: Customer = postgres.table("customers")

source orders: Order = postgres.table("orders")

relationship OrderCustomer(order: Order, customer: Customer): order.customer_id == customer.id

query orders_per_customer:
    from orders
    let customer = customers
    inner join customer on OrderCustomer(orders, customer)
    group by customer.name
    select:
        customer_name = customer.name
        order_count = count(orders.id)
```

PostgreSQL `emit-sql` writes one flat SELECT with every input aliased by its
name; `any` filters become correlated `EXISTS` or `NOT EXISTS`. MySQL
`emit-sql` refuses each JOIN relation (PIE-B1000) and keeps the file's other
SQL; `explain` refuses each JOIN relation (PIE-I1000), as its metadata
format has one input per relation. Windows over JOIN rows and ORDER BY after an
ungrouped aggregate are PIE-S2334, PostgreSQL FULL JOIN needs Int equalities
in `on`, and a JOIN of a source without a shape is PIE-S2334.

An aggregate other than `count()` must not read rows that a JOIN may repeat
(PIE-S2381). The relationship call above proves that each order matches at
most one customer, because its equality matches the declared key
`customer_key`. The same equality written by hand in `on` proves nothing yet:

```text
orders.pietto:23:23 PIE-S2381 error: An aggregate may read rows that a JOIN repeats; match a declared unique key of customer whose fields are never None in `on` with a relationship call, use `any(...)` for an input that only filters rows, or aggregate in a separate query first
```

[Single-file JOINs](language.md#single-file-joins) and
[Aggregates and grouping](language.md#aggregates-and-grouping) give the
complete rules.

### Legacy-flat projects and relationship JOINs

0.1.4 checked relationship JOINs in a legacy-flat project
(`schema_version = 1`): a JOIN such as `inner join customers as customer`
matched through a declared relationship, a JOIN `via` a relationship, and the
other forms written with `as`. They are no longer available. This release
names each JOIN input with `let` and states its condition with `on`, and a
legacy-flat project checks no JOIN and no `any(...)` of this syntax. Each
JOIN, of any kind and whatever its target, is one PIE-S2334 at its `on`, a
relationship call included, or at the JOIN when it has no `on`, with the text
``JOIN customer: a schema_version = 1 project has no JOIN in the current syntax; set schema_version = 2 to check it.``;
each `any(...)`, before a JOIN or after it, nested or not, in any clause, is
one PIE-S2334 at the `any(...)`, with the text
``any(...): a schema_version = 1 project has no any(...) in the current syntax; set schema_version = 2 to check it.``;
they come in source order. 0.1.4 refused this spelling of JOIN and `any(...)`
with PIE-P1000, so this refusal removes nothing that 0.1.4 accepted. A
legacy-flat project never emitted SQL, so no SQL changes. To check such a
project again:

1. Rewrite each JOIN and each relationship with endpoints in the current
   spelling; `migrate` reports each of them with PIE-P1011 and writes no
   source for the file.
2. Set `schema_version = 2` in `pietto.toml`.
3. In a project of several files, make each module import what it reads from
   another module, which exports it, and declare each relationship in the
   module whose JOINs call it, as a relationship is not imported (see
   [project and package](project-package.md#schema-compatibility)).

For example, this file of a 0.1.4 `schema_version = 1` project:

```text
shape Order:
    id: Int not null
    customer_id: Int not null

shape Customer:
    id: Int not null
    name: Text not null

source orders: Order is postgres.table("orders")
source customers: Customer is postgres.table("customers")

relationship order_customer: orders.customer_id == customers.id

query order_names:
    from orders
    inner join customers as customer
    select:
        order_id = orders.id
        customer_name = customer.name
```

is written as follows in a `schema_version = 2` project, where it also checks
as a single file:

```pietto
shape Order:
    id: Int
    customer_id: Int

shape Customer:
    id: Int
    name: Text

source orders: Order = postgres.table("orders")

source customers: Customer = postgres.table("customers")

relationship OrderCustomer(order: Order, customer: Customer): order.customer_id == customer.id

query order_names:
    from orders
    let customer = customers
    inner join customer on OrderCustomer(orders, customer)
    select:
        order_id = orders.id
        customer_name = customer.name
```

### Explicit-module JOIN diagnostics

In an explicit-module project, a JOIN whose `on` has an error of its own, such
as the invalid operand of `on orders.customer_id == -customer.name`
(PIE-S2105), or whose relationship call fails now reports only that error,
once. For that example 0.1.4 also reported PIE-S2334 at the `on`
(`JOIN-local ON is available only when an EXPLICIT_MODULES project (schema
version 2) completes it.`). A JOIN after one that failed keeps that PIE-S2334.

### Fixes

- **Comparison chains.** `check --project` no longer stops with an internal
  error on a comparison chain such as `0 < low + 1 <= high < 10`, where it
  reports what a single-file check reports, or on one over a window in
  QUALIFY, such as `0 < row_number() window(order by id) < 3`.
  `emit-sql --project` emits a chain as it emits the same comparisons joined
  with `and`, and so does single-file `emit-sql` for a chain over an
  `any(...)`, such as `False == any(z.id > 0 for z in b) == True`. An error in
  an operand that two comparisons of a chain share is reported once by
  `check --project` of a `schema_version = 2` project, as the next item
  states, and, in the cases this release fixes, in a single file and in a
  `schema_version = 1` project.
- **Repeated diagnostics in an explicit-module project.** `check --project`
  of a `schema_version = 2` project reports a diagnostic equal to an earlier
  one in code, severity, message, location and suggestion once, at its first
  position, as the
  [project JSON v2 contract](spec/project-cli-json-v2.md#ordering) states.
  0.1.4 reported an error in a call written inside another def's body as
  often as the called def's expansion made it, and a query header parameter
  passed to a `def` and read in a position that refuses it (PIE-S2355) at
  each use of the argument. A single file still reports such an error in a
  def body as often as the expansion makes it, except anywhere in an operand
  that a comparison chain copies, such as `x` in `0 < x < 10`, where it is
  reported once. The value of an inclusive chain `lower <= value <= upper` is
  not itself copied, so its error still follows the expansion unless the error
  lies in copied operand text, either around that chain or nested in its
  value.
- **Aggregates in a project `any`.** An explicit-module project refuses an
  aggregate in an `any(...)` predicate, such as
  `any(count() > 0 for o in orders)`, with PIE-S2335
  `Aggregate expressions are unavailable in ANY predicates.`, as a single file
  does; it accepted it.
- **A nested `any` before a later JOIN.** An enclosing binder hides the
  relations of its name from a nested `any(...)` also when the outer `any`
  filters before a later JOIN:
  `where any(any(True for nested_row in candidate) for candidate in rows)`
  followed by a JOIN was accepted, and its SQL read the table `candidate`; it
  is now PIE-S2301, as the same filter after the last JOIN is. A binder hides
  only the name as written, so a nested `any(...)` over a `let` alias of a
  relation with the binder's name, such as
  `any(any(True for other in buyers) for customers in orders)` after
  `let buyers = customers`, is now accepted, also after the last JOIN, where
  it was refused.
- **A nested `any` in a project.** An explicit-module project applies the same
  rule, also before a later JOIN:
  `any(any(True for nested_row in rows) for rows in rows)`, or the same
  through a `let` alias of `rows`, is PIE-S2301 and PIE-S2334 where it was
  accepted; before a later JOIN, that JOIN also reports PIE-S2335.
- **A CTE that hides a table.** Single-file SQL emission refuses a scalar
  `any(...)` reader with PIE-B1000 when a CTE that it defines would hide a
  table that the same SQL reads without a schema (MySQL compares the names
  case-insensitively); the SQL read the CTE in place of the table. Rename the
  relation, or read the table with its schema.
- **Private combined IR verification.** The verifier refuses a document whose
  scalar `any` read of an outer FROM or JOIN input names another relation, or
  other field names or another nullability than that input has; it accepted
  it.
- **A JOIN without `on` over a table or query.** In a single file, a JOIN
  without `on` whose FROM input or target is a table or query of the same file
  reports PIE-S2335 ``JOIN <binding>: write `on` with the condition that
  matches <input> to <relation>``, as every other JOIN without `on` does; it
  reported a PIE-S2334 text about relationship JOINs through a table or query.
- **A failed relationship call beside a window.** When a relationship call in
  `on` or in `any(...)` passes a table of the same file to a shape parameter
  and the file selects a window function, `check`, `explain` and `emit-sql`
  report PIE-S2604 as they do without the window; they stopped with an
  internal error.
- **`let` in a legacy-flat project.** A `schema_version = 1` project resolves
  each `let name = value` as a single file does, so a selected `let` name, a
  `let` alias read by `from` and an aggregate over a `let` are checked; they
  were PIE-S2102 `Unknown field`, PIE-S2301 or an empty row schema.
- **JOINs and `any(...)` in a legacy-flat project.** A `schema_version = 1`
  project reports one PIE-S2334 per JOIN and one per `any(...)`, in source
  order, each naming the way out (`set schema_version = 2 to check it`, see
  [legacy-flat projects](#legacy-flat-projects-and-relationship-joins)). A
  JOIN `on` said `JOIN-local ON is available only when an EXPLICIT_MODULES
  project (schema version 2) completes it.`; a CROSS, RIGHT or FULL JOIN
  reported its JOIN-kind text, such as `CROSS JOIN is available only when an
  EXPLICIT_MODULES project (schema version 2) completes it.`, and a RIGHT or
  FULL JOIN with `on` reported both. An INNER or LEFT JOIN without `on`, also
  one whose target names no relation in a relation that reads a field of its
  binding, and an `any(...)` in a `where`, `select` or `let` after the last
  JOIN, which such a project accepted without a diagnostic, are now refused
  the same way.
- **Deeply nested expressions.** A long chain of unary operators in a `derive`
  body and nested conditional expressions in a QUALIFY window argument parse
  to the depths 0.1.4 parsed; they stopped earlier with PIE-P1000
  `Parser recursion limit exceeded while processing source.`
- **Package check.** `scripts/package_smoke.py` writes its project sources in
  the modern spelling and accepts the approved PIE-S2382 warning of the MySQL
  ordering fixture; the installed package is unchanged by it.

### Known limitations

- **R2 and a trailing `any`.** A `where any(...)` or `where not any(...)` after
  the last JOIN, the rewrite of a last `semi join` or `anti join`, is an
  existence read, so R2's `save_recoverable` and `recover`
  refuse it with `PIE-R1004` (`REFINEMENT_EXPRESSION_BLOCK_READ`) where they
  accepted that last JOIN. A filter before a later JOIN, ordinary execution,
  an ordinary `save` and bundles are unaffected. A later release adds R2
  support for a trailing correlated `EXISTS`
  ([execution](execution.md#known-limitations)).
- **D-11 and D-12.** The conservative fan-out and typed-NULL refusals of
  [fix batch 7](#fix-batch-7-following-014-included-in-015) remain, including
  programs whose old SQL ran correctly.
- **Bundles and saved jobs.** As with every release, the changed code identity
  refuses bundles and saved-job records made by 0.1.4 or earlier; keep their
  matching environment.
- **The rewrite suggested for an old JOIN written with `as`.** The PIE-P1000
  of a 0.1.4 JOIN written with `as` suggests
  `let alias = relation` and then `left join alias on predicate` for every
  kind, also for an INNER, RIGHT, FULL or CROSS JOIN; keep the JOIN's own kind
  when rewriting it (a CROSS JOIN takes no `on`).
- **`migrate` and an old `semi join` or `anti join`.** Its PIE-P1011 for one
  written with `as` says to introduce `let` and `on`; rewrite it as
  `where any(predicate for o in orders)` or `where not any(...)`, as the
  PIE-P1000 of `check` suggests.
- **`migrate` and a parenthesized row argument.** A `semi join` or `anti join`
  whose relationship call passes the JOIN's own name in parentheses, such as
  `OrderCustomer((orders), customers)`, needs a manual rewrite (PIE-P1011),
  although the same call without the parentheses migrates.
- **A compiler-generated name in a diagnostic.** A bare binder as the
  predicate of an `any(...)` or `not any(...)` before a later JOIN, such as
  `where not any(o for o in orders)`, is PIE-S2335
  `JOIN ON reference is unknown: _pietto_any_1`, naming a binding that the
  compiler generated; after the last JOIN the same filter is PIE-S2102
  `Unknown or unavailable field in ANY predicate: o`.
- **MySQL and relation names that differ only in case.** When MySQL SQL
  defines two relations as CTEs whose names differ only in letter case, such
  as `chosen` and `CHOSEN`, a server with `lower_case_table_names` set to 1 or
  2 refuses the statement for a duplicate name; it returns no wrong rows.
- **Private combined IR verification.** The verifier does not check the type
  or the definition of a field that a scalar `any` reads from an outer input,
  as the document does not record them.
- **Very deeply nested comparison chains.** Checking a comparison chain nested
  in other chains many levels deep, such as
  `True == (True == (...) == True) == True`, is slower than in 0.1.4.
- **A diagnostic printed twice.** Apart from `check --project` of a
  `schema_version = 2` project, which reports an equal diagnostic once, an
  identical diagnostic printed twice at one position is a known issue to
  report, except for an error in a def body, which a single file reports as
  often as the def's expansion makes it, except anywhere in an operand that a
  comparison chain copies (including a nested operand). The value of an
  inclusive chain `lower <= value <= upper` is not itself copied; an error is
  reported once only when it lies in copied operand text, either around that
  chain or nested in its value.

### Deferred to the next release

These decided changes are not in this release:

- A hand-written `on` equality to a declared unique key whose fields are never
  None earns the same fan-out proof as a relationship call, in single files
  and projects.
- Warnings in every check mode for `Int / Int` truncation, `None` inside an
  `in` list (with the enum `in`-list fix) and `--` in an expression.
- Two warnings: a test in WHERE that rejects NULL on the NULL-extended side
  of a LEFT JOIN, and `not in` with a nullable left value.
- A style page for Python users.
- Relaxing the conservative fan-out (D-11) and typed-NULL (D-12) refusals of
  [fix batch 7](#fix-batch-7-following-014-included-in-015), so that the outer-JOIN
  aggregates and NULL arithmetic that the database runs correctly are accepted
  again (deferred, not dropped).
- R2 recovery through a trailing correlated `EXISTS`.
- Emitting a same-file table or query read as a CTE, and with it naming each
  statement and ending it with `;` in `emit-sql` text output, so that the SQL
  text changes once; this release's text output is unchanged.
- Reporting a swapped argument pair as one diagnostic.

## Fix batch 7 following 0.1.4 (included in 0.1.5)

This addendum covers the compiler fixes following 0.1.4, which `0.1.5` includes.
It does not replace the published 0.1.4 release notes.

### Checking and supported results

- Known function results are checked even when an argument's type is unknown.
  Decimal quotients and arithmetic with a NULL operand retain their numeric
  information, so incompatible scalar calls, comparisons and conditions receive
  specific diagnostics.
- The existing accepted NULL-containing IN/NOT IN compatibility branch now has
  type Bool nullable, including its supported numeric, Date/Text-literal and
  enum-label cases. Calls such as LOWER or ABS apply the existing Bool rules.
  Some previously accepted MySQL uses relying on implicit conversion are newly
  refused; the owner explicitly approved that compatibility change. Operand
  compatibility rules and unrelated Unknown operators are unchanged.
- A specific scalar error is retained inside an aggregate when the failing
  argument contains qualifying typed NULL arithmetic. For example,
  `count(trim(null % n))` reports the TRIM type error rather than only an
  unsupported-aggregate-expression error. Existing arity, bounds, def-argument
  and independent-error precedence remains.
- ABS accepts Int and Float as well as Decimal. Int-to-Float casts can use newly
  known Int results. Supported non-null def bodies and value windows with a
  provably nullable result can also be accepted in cases that previously lacked
  enough type information.
- Invalid qualifiers, grouped projections, aggregate forms and ORDER BY uses
  over sources without a shape are checked earlier. The unpublished aggregate
  emission expansion was removed: shapeless aggregate SQL, grouped-window
  lowering and downstream output-schema/lineage remain at the 0.1.4 boundary.

### JOIN proofs and metadata

RIGHT/FULL unmatched rows no longer receive an unconditional grain dependency
that can hide repeated aggregate inputs. Some programs that 0.1.4 accepted now
receive `PIE-S2333` with a more accurate repeating-JOIN explanation and remedy.

Correct existing COUNT cases retain narrowly justified proofs: an exact reverse
INNER/SEMI match can remove the original unmatched rows, and a grouped nullable
key can serve only the specific bounded unmatched-row proof whose full final
non-null and cardinality premises hold. It does not become a generic group key
for unrelated or unbounded JOINs.

INNER relationship equalities retain their actual matched-field non-null facts
even with an additional ON. Self-relationship directions use exact endpoint
roles, and compiled field ancestry preserves the original introducing input
through internal JOINs. Current and compiled key, FD and grain evidence follow
the same identity rules. These metadata corrections are not limited to queries
containing RIGHT/FULL.

Composed WHERE/LET proof traversal avoids adding the two expression depths while
preserving the values actually visited and existing short-circuit behavior.
Project source selection and cyclic-import inspection also retain diagnostics
instead of their documented recursion/inspection crashes.

### SQL and compatibility

MySQL integer division uses `DIV` where the dividend is now known Int, and
ORDER BY fields are qualified when an unaliased TRUE/FALSE/NULL output would
capture them. PostgreSQL's supported NULL temporal calls use a typed NULL
instead of an unresolved EXTRACT. These are generated-SQL changes, not claims
of new native database execution.

A semantic error still prevents emission of a single file or every relation of
an EXPLICIT_MODULES project. Newly detected errors can therefore remove partial
or otherwise-valid sibling output.

The documented conservative **D-11** fanout refusals and **D-12** typed-NULL
refusals remain for this release, including specified programs whose old SQL was
database-correct. Their relaxation is required after the JOIN demo; it has been
deferred, not dropped. The restored COUNT and composed-depth cases are not
additional exceptions under those decisions.

The detailed compatibility changes follow.

### Compatibility with 0.1.4: fix batch 7

This is the compatibility text for the fixes following 0.1.4 (included in 0.1.5).
Examples describe compiler checks, metadata and generated SQL. They do not claim
new execution against PostgreSQL or MySQL. This batch does not introduce the
single-file JOIN MVP or new aggregate emission over sources without a shape.

#### Effect of an error on emission

A new semantic error prevents SQL emission for the whole single file. Where
0.1.4 refused one relation but still printed another relation's SQL or returned
partial artifacts with `ok: false`, that partial output is no longer produced
once the program fails checking.

In an EXPLICIT_MODULES project, an error in any relation blocks
`emit-sql --project` for every relation, including otherwise valid siblings.
For example, rejecting `id in (1, "x", null)` in one query also blocks a sibling
table that 0.1.4 could emit. This follows the existing project policy; it is an
intentional compatibility effect, not a new project execution policy.

LEGACY_FLAT projects still do not emit SQL. Their checking changes are described
below.

#### Comparisons, membership and COALESCE

The same semantic type rules apply to both dialects. Programs relying on MySQL
implicit conversion can therefore be newly refused even when their old SQL ran.

- Enum values and enum aliases cannot be compared with Int, Float or Bool, a
  different enum family, an invalid or differently cased label, or a non-literal
  Text expression. Examples include `st == 1`, `st == other_enum`,
  `st == "bogus"`, `st == name` and `st > upper(name)`. These report
  `PIE-S2105`. Valid labels such as `st == "active"` and valid enum-label
  BETWEEN bounds remain accepted; a Text conditional is not a literal label.
- Date, Timestamp, UUID, Bytes and Json cannot be compared with non-literal Text
  fields, calls or bindings, including BETWEEN bounds. Literal forms such as
  `d == "2020-01-01"` retain their existing admission rules.
- Bytes and Json comparisons with unrelated families, and shape values compared
  with a different family or shape, report `PIE-S2105`. The existing permitted
  Text-literal comparisons, same-shape comparisons and gradual `Any` cases remain.
- A NULL option no longer hides an incompatible IN/NOT IN option:
  `id in (1, "x", null)` and `id not in ("x", null, null)` report
  `PIE-S2105`, “expected same canonical membership operands.”
  Numeric-looking or Bool-looking Text is not automatically converted:
  `id in ("5", null)` and `b in ("true", null)` are also refused.
  Existing compatible lists such as `amount in (2.5, null)`,
  `id in (2.5, null)`, `d in ("2020-01-01", null)` and valid enum-label
  lists retain their admission rules.
- In the existing NULL-containing membership compatibility branch, once the
  remaining operands are accepted by the existing pairing rules, IN and NOT IN
  now have type **Bool nullable**, rather than Unknown. This covers the accepted
  numeric, Date/Text-literal and enum-label cases. Direct expression metadata,
  and direct outputs on the supported typed-row path, reflect that type.
  Surrounding calls apply the existing Bool
  rules: `lower(d in ("2020-01-01", null))` and
  `abs(1.5 in (null, n))` report `PIE-S2104`. This includes newly refused
  MySQL uses that previously relied on implicit conversion, as explicitly
  approved by the owner. Unsupported operand pairings are not admitted, and
  unrelated Unknown operators are not retyped by this change.
- On an unknown row, known incompatible COALESCE arguments are checked even
  beside an unknown argument: `coalesce(t, 1, "x")` and
  `coalesce(t, true, 1)` report `PIE-S2104`. The existing gradual case
  `coalesce(t, 1, 2.5)` remains accepted.
- EXPLICIT_MODULES projects apply the comparison rules to query header
  parameters, JOIN predicates and joined result predicates as well as ordinary
  scalar expressions. A Text header parameter is not an enum label or temporal
  literal. Supported header parameter families remain Bool, Int, Float and Text;
  other families retain `PIE-S2353`.
- A def that compares a Date, Timestamp or UUID parameter with a Text parameter
  is checked at its declaration even if every call passes a Text literal.
  A def-body error still prevents the later call analysis.

The owner retained the documented dialect-independent comparison and
typed-result refusals for this release, including cases for which a database
would supply a conversion.

#### Fixed-signature results and numeric expressions

A fixed-signature call can have a known result even when its argument's type is
unknown: `len(t)`, `year(t)` and `count(t)` have Int results, and
`lower(t)` has a Text result. This affects expression checking; it does not
introduce type propagation through an unsupported shapeless relation output.

Consequently, `lower(t) + 1`, `-lower(t)`, `len(t) like "a%"`,
`lower(len(t))` and mismatched known parameters of `matches`, `contains` or
`replace` are refused with `PIE-S2104` or `PIE-S2105`.
A numeric result used as WHERE reports `PIE-S2202`. These checks also apply
when the argument is an all-NULL expression or a Decimal quotient on a shaped
row.

Known result types also receive Pietto's existing stricter rules:
`year(t) == "2020"`, `len(t) in (1.5, 2.5)`,
`coalesce(len(t), 1.5)` and `nullif(year(t), 2.5)` can now be refused.
A def expecting Text rejects `len(t)` with `PIE-S2395`. Unknown
nullability alone remains gradual; it is not treated as proven NULL.

Some refusals move earlier from emission to checking. These include a Text-to-
Float cast whose argument is now known to be Text, invalid arity for `nullif`,
unsupported aggregate expressions, and invalid uses of a COUNT result in
`satisfying`. Their original unsupported emission capability is not added.

A Decimal quotient is recognized as numeric even where its concrete numeric type
is unknown. The rule follows direct expressions, LET bindings, COALESCE, NULLIF
and conditionals:

- A quotient in WHERE, satisfying, a shape check or an index predicate must
  satisfy the Bool rule. Quotients used with `and`, `or`, `not` or as a
  conditional condition are likewise checked.
- Mixing a quotient with Text, Bool, an enum or another incompatible family in
  arithmetic, comparison, LIKE, membership, BETWEEN or a conditional reports the
  corresponding `PIE-S2104` or `PIE-S2105`.
  Numeric-looking Text literals do not receive an implicit conversion.
- Text and temporal functions reject a numeric quotient at the offending
  parameter: for example `lower(a / 2)` and `year(a / 2)`.
  Existing supported numeric uses of `abs`, `sign` and COALESCE remain.
  `substr(t, a / 2, 1)` remains refused because its start is not a positive
  Int literal; this is not a new refusal.
- The same checks apply inside def expansions and to a field's `derive`.
  A def call can report the expanded body's scalar errors at the call, rather
  than one `PIE-S2395`; this existing diagnostic distinction is retained.
- A branch known only to be numeric, with unknown concrete numeric type, can
  no longer be combined with Text merely because the condition has silent
  Unknown type. This includes an unknown-argument ABS result or a Decimal quotient.
  `abs(t) if b else "x"` reports `PIE-S2105` in that situation.
  Compatible numeric branches retain Unknown when the condition remains Unknown.
  Ordinary cases such as `1 if b else "x"` with silent Unknown `b` retain
  their existing gradual behavior; this is not a general conditional migration.

`abs` accepts Int and Float in addition to Decimal and preserves a concrete
argument's type and nullability. An unknown argument or Decimal quotient can
remain numeric with unknown concrete type, so numeric contexts continue to work
while Text and temporal calls reject it. The intermediate typing-lane refusals of
`abs(len(t))`, `abs(t) % 2 == 1`, `abs(t) + 1.5`,
`nn(abs(t))` and `nn(abs(amount / n))` are not retained.

#### NULL-only values and typed NULL arithmetic

A conditional, COALESCE or NULLIF made only of NULL values behaves like NULL
when combined with a known typed value. For example, a Text branch beside an
all-NULL branch yields nullable Text, and a not-null def parameter can reject
that nullable result with `PIE-S2395`. A known incompatible type is no longer
hidden by the all-NULL expression.

PostgreSQL emission refuses an all-NULL output when another relation reads its
relation, including a plain read, an IS NULL test or a reader that does not use
that column, as it already did for a literal NULL output. It also refuses all-NULL
CASE/COALESCE/NULLIF values in unsupported numeric, Bool or temporal uses within
one relation. The diagnostic is `PIE-B1000` and explains the text typing.
Text uses and the MySQL emission boundary retain their existing behavior;
`nullif(null, 1)` is typed and is not an all-NULL expression.

Arithmetic with one NULL operand and a known numeric operand is now typed as the
operator's typed twin and is nullable. This includes `+`, `-`, `*`, `/`
and `%`, and a NULL supplied by an allowed LET or inlined def value.
Thus `null + n` is nullable Int, `null + fl` nullable Float and
`null + d` nullable Decimal; division beside Decimal retains the existing
numeric-but-concrete-type-unknown rule.

The resulting compatibility changes include:

- `lower(null + n)`, `trim(null % n)`, `len(null + n)`,
  `year(null + n)` and `lower(null / d)` now report the scalar
  `PIE-S2104` type error. Mixing those results with Text in COALESCE also
  reports `PIE-S2104`.
- Arithmetic, comparison, LIKE, IN, BETWEEN or a conditional with an
  incompatible partner reports `PIE-S2105`. A numeric NULL expression as
  WHERE reports `PIE-S2202`.
- The typed twin's existing rules also reject some SQL that a database would
  evaluate: Decimal/Float or Decimal/Int combinations outside Pietto's supported
  rule, numeric-looking Text, incompatible canonical COALESCE/NULLIF arguments,
  and nonmatching def parameters. Def argument messages now name the inferred
  nullable numeric type where it is available.
- A declared def result can now be checked against the typed NULL arithmetic
  body. For example, an Int body declared as Text reports `PIE-S2402`.
  Conversely, nullable-Int bodies such as `coalesce(x + null, x)`,
  `(x + null) if x > 0 else x` and `x if x > 0 else x + null` can be
  accepted where their result was previously unknown.
- When a valid-arity scalar call has an actual type error caused by NULL
  arithmetic in its failing argument, an enclosing aggregate retains that
  specific error. `count(trim(null % n))` reports `PIE-S2104` at
  `trim` instead of the generic aggregate-form `PIE-S2315`.
  `count(null + n)` still reports `PIE-S2315`;
  `count(nn(n + null))` retains its def-argument error.
  Arity errors, substr bounds, prior independent errors, ordinary quotients and
  unrelated NULL siblings keep their existing precedence and multiplicity.
- The rules apply to readers of supported typed outputs and to known JOIN
  fields. In projects, a newly exposed semantic error also blocks otherwise
  valid siblings under the normal project policy.

**D-12 is retained for this release.** It includes the documented newly refused
uses whose old PostgreSQL or MySQL SQL was database-correct, including MySQL
implicit conversions. The owner requires those specified database-correct
classes to be accepted again after the JOIN demo; that work is deferred, not
dropped.

In the documented project LET/JOIN cases, typing can instead remove a check-time
`PIE-S2333` while emission still refuses the affected relation with
`PIE-B1003 expression_evidence_unavailable`. This covers a grouped
null-arithmetic LET key, an ungrouped SELECT reading such a LET or LET chain,
and null arithmetic over either a joined binding's field or the FROM binding's
field in an ON JOIN. Valid sibling relations can then emit again.
The direct no-LET/no-JOIN SELECT form retains its separate `PIE-S2333` boundary.

`null + null` and `-null` retain their unknown-type boundary.
PostgreSQL still refuses their unsupported emission; fix7 does not make every
NULL-valued expression lowerable.

#### Sources without a shape

The retained change is earlier checking, while the released aggregate emission
and output-schema boundaries remain.

- A qualifier other than the FROM binding, or a field path with three or more
  parts, reports `PIE-S2102` in WHERE, SELECT, ORDER BY and read LET values,
  including a stale upstream qualifier used by a downstream relation.
- An invalid reference in an unread LET is also reported. Dropping that LET from
  emitted SQL no longer hides its error.
- Grouped unknown rows are checked for a missing aggregate, a non-key projection,
  unsupported scalar projection and duplicate keys, using the existing
  `PIE-S2318`, `PIE-S2319`, `PIE-S2320` and `PIE-S2317` families.
  A GROUP BY is no longer silently discarded while row-level SQL is emitted.
- Aggregate arity, form and known argument types are checked even on an unknown
  row. This can move a failure from `PIE-B1000` emission to checking:
  examples include `count(x, y)`, `min(x + 1)`, `count(x + "a")`,
  non-grouped fields beside an aggregate, and an aggregate ORDER BY input.
  Unsupported computed LET arguments retain name/form errors. A known Bool
  min/max error remains visible beside independent unread-name errors, with
  their original locations, order and repeated occurrences.
- Aggregate modulo cases such as `count(x % 2.5)` and
  `count((x * 1.5) % 2)` remain subject to the aggregate form/type boundary;
  a plain unknown-field `x % 2.5` is not newly refused solely for being unknown.
- Grouped ORDER BY retains the released whole-clause `PIE-S2321` boundary.
  Grouped windows do not gain a new lowering path.
- Reading a single-file JOIN binding still requires the separate single-file
  JOIN capability; this batch retains its refusal.

The unpublished emission expansion was removed, including its later
count-only/grouped subset. There is no new shapeless COUNT/COUNT DISTINCT,
MIN/MAX/SUM/AVG, HAVING, grouped ORDER BY or grouped-window emission in this
batch. Unknown-input ungrouped relation outputs remain unknown; grouped
unknown-input outputs and downstream explain/lineage remain at their released
empty/unknown boundary. Restoring these boundaries is not a new refusal
relative to 0.1.4.

#### JOIN aggregation and relation identity

In projects, a RIGHT or FULL JOIN with an at-most-one match no longer supplies
an unconditional left-to-right grain dependency over its unmatched right rows.
An aggregate with an argument is refused with `PIE-S2333` when it can read
repeated rows that the available key/grain proofs do not protect. A unique key
on the NULL-extended left input alone does not fix its NULL group.

Affected forms include a subsequent LEFT/CROSS JOIN from the preserved side;
an argument such as `orders.rush or true` that is not NULL on unmatched rows;
WHERE conditions such as `orders.amount > 0 or c.vip` or
`orders.id is null`; and ANTI or unrelated SEMI conditions that retain those
rows. Empty-list conditions keep their actual TRUE/FALSE behavior, including
through LETs and NOT.

Accepted proofs include an argument that is NULL on those rows, a WHERE or
later INNER/SEMI/RIGHT match that excludes them, and the existing narrowly
qualified later-input proof. In addition:

- For the initial RIGHT/FULL over direct sources with no extra ON, a later
  INNER/SEMI reverse match over the exact same source domain can eliminate all
  original unmatched rows. Complete paired equalities are compared without
  treating authored conjunct order as meaning, while their multiplicity and
  field pairing are retained. A stricter later ON is allowed. ANTI, an extra
  earlier ON, a different source declaration sharing a physical table name, or
  a filtered source does not establish this proof.
- Generic group protection remains **source STRICT-key only**. A grouped nullable
  unique key can be used only for the exact later input that supplies the
  existing bounded RIGHT/FULL unmatched-row proof, when every key determinant
  is non-null in the final rows and the original pinning/cardinality premises
  hold. It restores only that original dependency; it adds no general group
  seed. An unrelated unbounded JOIN cannot borrow this capability.
  Missing composite-key evidence and later outer NULL extension defeat it.
- INNER relationship equalities contribute complete non-NULL facts even with an
  extra ON. These facts refer to the actual matched field occurrences, not an
  unwritten equivalent sibling; source declarations remain unchanged. A later
  outer JOIN can NULL-extend them again.
- A self-relationship's reverse guarantee is selected by its exact opposite
  endpoint roles, not by the shared output object. Current and compiled keys,
  FDs and grain retain the legitimate inverse dependencies. Compiled field
  ancestry follows internal JOIN outputs to the original introducing use while
  respecting named-producer boundaries.

The last two corrections also affect metadata outside a RIGHT/FULL aggregate,
including the applicable INNER/LEFT relationship paths.

**D-11 is retained for this release.** Some safe programs remain conservatively
refused because the proof does not simplify values, constants, contradictions,
vacuous conditions or every correlation. Examples include the documented
`where r.id is null` on a non-null CROSS input, contradictory comparisons,
and value-dependent COALESCE/conditional/NULLIF or empty-membership forms.
Some previously had correct VERIFIED SQL; other examples already failed
emission. Correlated ANTI/LEFT emptiness is distinct from a value-only proof.

`min`, `max` and `count_distinct` receive no general fanout exemption,
even when repetition would leave their value unchanged. The documented
database-correct D-11 classes remain scheduled for relaxation after the JOIN
demo, not silently reclassified as wrong SQL.

For already refused programs, `PIE-S2333` can name different repeating JOINs
or a different remedy while keeping its code and declaration location.
`count()` without an argument counts the joined rows and retains its separate
rule.

Composed WHERE/LET NULL proofs no longer stack the two expression depths or
evaluate unrelated LETs speculatively. Existing short-circuit visitation is
preserved. Very deep programs still have the existing `PIE-S2006` boundary;
historical recursion thresholds and timing samples are not public guarantees.

#### Windows and project checks

- RANGE offsets must be nonnegative Int literals no greater than
  `9223372036854775807` after permitted LET inlining. Unknown names, Text,
  Float, NULL, fields, computed offsets and out-of-range literals report
  `PIE-S2104`. Zero, the maximum literal and an allowed literal LET remain
  accepted. The check applies to named/selected windows and project JOIN and
  QUALIFY contexts.
- Value windows can accept a known value type with unknown nullability when the
  result is nevertheless known nullable: first/last/nth value and the admitted
  lag/lead cases. The existing limits for offset zero or a non-null default
  remain. Project emission still requires its target contract.
- Project windows over supported shape-valued inputs/aliases can pass checking
  without gaining shape SQL emission. JOIN/hidden-QUALIFY shape windows,
  shape partition/order keys, unsupported shape LET reads and the documented
  unknown-result-nullability cases retain their refusal boundaries.
- An unrelated unknown-typed LET no longer blocks a project window whose actual
  reads are supported. Some such relations still fail emission with
  `expression_evidence_unavailable`, while valid siblings can emit.
- LEGACY_FLAT checking reports the single-file semantic diagnostics after its
  model diagnostics. This includes type, predicate, field, aggregate, window,
  constraint/derive and relationship errors. SELECT-output ORDER BY keys outside
  grouped queries receive the existing `PIE-S2102` hint to restate the
  expression or bind it with LET. LEGACY_FLAT still refuses `def` with
  `PIE-S2379` and emits no SQL.
- Relationship JOIN routes through supported DISTINCT endpoints in
  EXPLICIT_MODULES projects can plan and emit again, including inferred/explicit
  routes and their readers, rather than failing with unavailable planning roots.

#### SQL, diagnostics and metadata changes

For programs accepted before and after, these generated SQL changes are
intentional:

- MySQL uses `DIV` rather than `/` where the dividend is now known Int:
  `len(t) / 2`, admitted temporal/sign calls, a typed branch beside all-NULL
  values, and `(null + n) / 2`. This does not introduce missing type
  propagation through an upstream relation.
- MySQL qualifies an ORDER BY field that an unaliased TRUE, FALSE or NULL SELECT
  item would otherwise capture.
- PostgreSQL emits a typed NULL for `year(null)` and the corresponding
  month/day/hour/minute forms, including permitted LET/def NULL values, instead
  of an unresolved EXTRACT over NULL.

Other supported outcomes include Int-to-Float casts of newly known Int results,
such as `cast(len(t) as Float)` and `cast(null + n as Float)`.
Float-to-Float casts remain unsupported and can now fail at check rather than
emission. Proven non-null def bodies over the supported operators can be
accepted; `/`, `%`, `and`, `or`, `nullif` and `matches` remain
outside that non-null proof. An all-NULL branch can establish a compatible
nullable def result without making PostgreSQL's unsupported all-NULL emission
valid.

Project Int/Float ABS uses retain physical range requirements. A range that
cannot establish safety blocks emission; public details include
`abs_result_outside_physical_range` and `int_range_proof_missing`.
A query header parameter is not newly admitted as an ABS argument.

Diagnostics become more specific in several already refused cases:

- Computed window partition/order LETs report the window-computation
  `PIE-S2103` rather than a spurious unknown name. Value-window offsets,
  defaults, unknown fields and unsupported shape equivalence keep their
  specific existing diagnostic families.
- Unsupported min/max LET arguments on known rows receive their actual
  argument/type/binding diagnostic rather than an unconditional unknown name.
- Known function results expose their own outer type errors; prior independent
  errors and duplicate authored occurrences are retained.
- Projects report scalar/name/duplicate-projection errors in place of a bare
  `PIE-S2333` where those facts are available. Redundant relation-level
  cascades and repeated reporting of the same JOIN issue are removed.
  Identical BLOCKED entries are deduplicated in text, JSON and `compile_query`.
- QUALIFY's single-file refusal and project configuration errors have clearer
  suggestions. Clause-header hints are no longer added in inapplicable parser
  contexts. ABS and def-result messages describe the supported types/proof
  limits more accurately.

Metadata reflects known fixed-signature expression results, typed nullable NULL
arithmetic, the accepted membership branch's Bool nullable result, and the
corrected JOIN nullability/identity facts. This does not restore the removed
shapeless output-schema or lineage expansion.

#### Retained limitations and stability

Unknown types alone remain gradual. These changes do not introduce arbitrary
casts, implicit canonical-type conversion, general computed aggregate arguments
or unrestricted window/shape lowering.

A value known only as numeric with unknown concrete type can still lose that
numeric marker at an existing relation-output boundary. The batch does not
introduce general propagation through those boundaries. The documented
known-row unknown-field aggregate forms remain separately limited; removing the
unpublished shapeless capability does not make those forms newly lowerable.

Project selection with deeply nested include/exclude patterns or paths no longer
ends in RecursionError, and ambiguous declarations in an import cycle retain
their diagnostics instead of crashing inspection. The new NULL analysis
preserves established LET-cycle diagnostics and shared-DAG behavior.

Development-tool and CI pin updates do not define new SQL, diagnostic, JSON or
golden behavior.

---

## Post-Phase70 public alpha release notes — 0.1.4

**Status:** These notes describe `0.1.4`, published and byte-verified on the
versioned GitHub pre-release and PyPI channels.

This release makes Pietto source read more like Python, adds one-line
relationships, inferred JOIN sources and inline `def` functions, and fixes
compiler and CLI defects found after 0.1.3. Source that 0.1.3 parsed keeps
parsing as before, with one exception: a file whose first code line is
indented is now PIE-P1000.
Some programs that 0.1.3 accepted are now refused because their SQL would fail
or mean something else; see
[Compatibility and retained data](#compatibility-and-retained-data). Pietto
remains an alpha; the CLI does not execute database queries.

### Highlights

- **Python-style layout.** `select:`, `select distinct:`, `group by:`,
  `order by:`, `partition by:`, the row `let:` and `enum NAME:` take their
  items after `:` on the header line, separated by commas, or in an indented
  block whose lines each hold one item or a comma-separated list, for example
  `order by: ordered_at desc, id desc`. `where:`, `satisfying:` and a shape's
  `check NAME:` take one condition after `:` or one condition per line of an
  indented block; the lines are joined with `and`, each as if written in
  parentheses. Inside parentheses an expression can continue over several
  lines; there is no backslash continuation, and an unclosed `(` is PIE-P1008.
  These forms parse to the same tree as the one-item-per-line form or the
  `and` chain, so checks and SQL are unchanged.
- **Soft keywords as names.** 26 words, among them `type`, `source`, `from`,
  `where`, `select`, `query`, `limit` and `check`, may also name a shape field,
  a `select` output, a row `let:` binding, a parameter or a typed VALUES
  column, as in `where type == "click"`. They do not name declarations or
  relations. `and`, `or`, `not`, `null`, `true`, `false`, `between`, `like`,
  `nullable` and `window` stay reserved.
- **One-line relationships.** `relationship r: a.x == b.y`, with one or more
  `and`-joined equalities between fields of two different relations, declares
  the endpoints `a` and `b`, so its roles are the relation names. A
  relationship of a relation to itself keeps the block form.
- **Shorter relationship JOINs.** A JOIN that follows a declared relationship
  needs only its header; its `from` line and VIA roles are optional, and the
  header may carry one step: `: from b`, `: via r` or `: via r: s -> t`. In an
  explicit-module project (`schema_version = 2`) a JOIN without `from` uses the
  one earlier binding that has a relationship to its target, in exactly one
  usable direction. No candidate is preferred: otherwise PIE-S2333 at the JOIN
  names every candidate. A JOIN with `on` and a CROSS JOIN still name their
  source with `from` (PIE-S2378). Single-file and schema version 1 project
  checks do not infer.
- **Inline `def` functions.** `def f(p: T not null) -> R nullable: return e`
  names a reusable scalar expression over `Bool`, `Int`, `Float`, `Decimal`,
  `Text`, `Date`, `Timestamp` or `UUID` parameters with explicit nullability.
  It is checked once where it is declared, and each call is replaced by its
  body before the call site is checked, so a call emits exactly the SQL of the
  same expression written by hand; no database function is created. A def
  belongs to its module (no import or export), recursion is refused, and an
  error inside a call is reported once however often the body uses the
  argument, except in a call written inside another def's body, where an
  error other than an argument mismatch (PIE-S2395) is reported as often as
  its expansion makes it, and in two project cases (see
  [Known limitations](#known-limitations)). An error in a def body stops the
  check before semantic analysis: of its file, and in a project of every
  module. Available in single files and explicit-module projects.
- **New diagnostics:** PIE-P1008 (an unclosed `(`), PIE-S2378 (a JOIN with
  `on` or a CROSS JOIN without `from`), PIE-S2379 (`def` in a schema version 1
  project), PIE-S2395 to PIE-S2399 (`def` arguments, recursion, forms, names
  and expansion size), PIE-S2380 (an ORDER BY key a target would misread) and
  PIE-S2604 (a relationship `on` operand error).

### Compatibility and retained data

- Bundles and saved jobs made by 0.1.3 or earlier are rejected by the 0.1.4
  code identity. Pietto neither migrates nor rewrites those bytes; use their
  matching old environment, then compile again for 0.1.4. Format markers are
  unchanged. The VS Code extension 0.1.0 accepts only the 0.1.2 wheel or its
  baseline fingerprint and refuses 0.1.4. This release adds no stable editor
  API.
- Explicit-module projects:
  - A field of an enum, or of an alias of one, is typed as that enum, as in a
    single file, and a `def` parameter the field does not fit is PIE-S2395.
    Programs 0.1.3 accepted are refused: `where status` (PIE-S2202),
    `status in ("active")` and `status not like "a%"` (PIE-S2105), and
    `lower(status)` and `coalesce(status, "x")` (PIE-S2104). Programs 0.1.3
    refused pass `check --project`: with JOIN inputs, a selected `let:` name
    bound to an enum field (0.1.3: PIE-S2333), a JOIN `on` that compares enum
    fields (PIE-S2334 and PIE-S2335) and a JOIN over a relation `let` that
    outputs one (PIE-S2333); without them, `select distinct` of an enum field
    and a grouped `satisfying` that compares one (PIE-S2333), a window or
    QUALIFY partitioned or ordered by one (PIE-S2103 `Unknown function`), and
    `lag`, `lead`, `first_value`, `last_value` and `nth_value` of one
    (PIE-S2104 `value type must be concrete`). The other JOINs over a source
    with an enum field, on which 0.1.3 crashed with a ValueError traceback
    (see Included repairs), pass when they select, group, order, compare or
    window the field, and `count(c.status)` there is PIE-S2314.
    `emit-sql --project` still blocks every table or query that reads a
    source with an enum field (PIE-B1003). Some enum reads still fail closed
    with PIE-S2333 (see Known limitations).
  - A LIKE pattern read through a `let:` name of a relation with JOIN inputs
    and ending in an unpaired `!` is PIE-S2105, where 0.1.3 emitted a
    VERIFIED `LIKE ... ESCAPE '!'` that PostgreSQL rejects.
  - The WHERE of a relation with a `let:` binding of unknown type, such as
    `k = null`, or with an error in a binding is checked as in a single file,
    except in a `select distinct` relation or one with QUALIFY (see Known
    limitations): `where n == k` is PIE-S2105, where 0.1.3 passed `check` and
    `emit-sql --project` blocked the relation with PIE-B1003, and a `def`
    argument there that does not fit is PIE-S2395.
  - A relation reports the errors of each `let:` binding, of its WHERE and of
    its SELECT items, in source order, where 0.1.3 reported only the first
    part that failed: the first failing SELECT item hid the others, an error
    in any relation's `let:` hid its WHERE, and an error in a JOIN relation's
    `let:` hid its WHERE and SELECT errors. After such an error in a JOIN
    relation's `let:`, its WHERE and, without GROUP BY or aggregates, each
    SELECT item that is no window report their own errors when they read no
    relation (`exists`, `scalar` or `in`), no binding with an error of its
    own and no field that does not resolve; any other SELECT item, such as a
    grouped or aggregate one, still reports none. Without JOIN inputs, the
    SELECT items of a `select distinct` relation and an aggregate argument a
    project refuses still report no error of their own (see Known
    limitations).
  - Beside a binding of unknown type or with an error, the other bindings keep
    their types: with `k = null`, `f = id` and `h = f`, `v = h` passes, where
    0.1.3 reported PIE-S2102 `Unknown field: h`, and a window that reads no
    binding, also through the named window it uses, is analyzed, where 0.1.3
    reported PIE-S2103 `Unknown function` for every window there. A selected
    read of `k` itself takes its type from where it stands, as in a single
    file, so `v = coalesce(k, 1)` and `v = 1 if k else 2` pass
    `check --project` where 0.1.3 reported PIE-S2102 `Unknown field: k`;
    `emit-sql --project` still blocks such a relation (PIE-B1003). A window
    that reads a binding there fails closed with the binding's error or
    PIE-S2333.
  - With JOIN inputs, a `let:` binding of unknown type is written into a later
    binding's `def` argument and null test, as without them: with `k = null`,
    `w = coalesce(k, o.id)` and `v = tnn(w)` for a `Text not null` parameter,
    `v` is PIE-S2395. A read of such a binding is typed as without JOIN inputs
    too, so a later binding, SELECT item or WHERE that is ill-typed only then
    reports its error: with `j = coalesce(k, 1)`, `d = len(j)` is PIE-S2104
    where 0.1.3 reported a bare PIE-S2333; with nothing ill-typed, such a
    relation still fails closed with PIE-S2333. A `let` that renames a field,
    such as `g = r.n` with `group by: g`, selects that field's group key, so
    `k = g` passes and emits where 0.1.3 reported PIE-S2102; another `let:`
    name selected from the groups is PIE-S2333 instead of PIE-S2102.
  - In a relation with JOIN inputs, a null literal compared or combined in
    `satisfying:`, also as a nullable `def` argument, is PIE-S2327 at the
    literal, and any other predicate of unknown type is PIE-S2333, where 0.1.3
    crashed with a ValueError traceback.
  - `emit-sql --project` reports an ORDER BY key with a part of unknown type,
    such as `(null is null)`, BLOCKED with PIE-B1003 `order`, where 0.1.3
    reported INPUT_REJECTED `Invalid current planning roots.` (exit `2`). A
    plan whose `let:` stages carry more columns than half the generated-node
    limit is BLOCKED with PIE-B1007 `generated_structure_limit` once the
    contract is read, before it is assessed and realized, beside no other
    blocker than a premise conflict: a 300-binding chain is refused in
    seconds instead of about a minute.
  - A GROUP BY over a table or query that is one global aggregate row, such
    as a table that selects only `c = count()`, passes `check --project` and
    emits, where 0.1.3 crashed with a TypeError traceback in `check --project`
    and in `emit-sql --project` of either relation.
  - A SEMI or ANTI JOIN over some inputs, such as a table that selects the
    fields of a source with a unique key in another order than the source
    declares them, emits, where 0.1.3 reported every table and query of the
    project INPUT_REJECTED `Project planning roots are unavailable.` (exit
    `2`) although `check --project` passed.
- LEGACY_FLAT projects (`schema_version = 1`): a table or query whose `from`
  reads a set operation reports PIE-S2334 at that `from`, as a single file
  does, where 0.1.3 stopped `check --project` with an internal
  AssertionError.
- Programs that 0.1.3 accepted and 0.1.4 refuses:
  - a file whose first code line is indented (PIE-P1000);
  - a comparison with the null literal, or with a `let:` name bound to it,
    a `between` whose value or both bounds are null, and an `in`/`not in`
    list whose value or every option is null, all never true (PIE-S2105;
    write `is null` or `is not null`);
  - a single file with an expression nested more than 450 levels anywhere,
    a relationship `on`, a type `ensure` and a window frame offset included
    (PIE-S2006 in every command; projects are not held to this bound);
  - checks that do not depend on an argument's type now also run over rows of
    unknown type, such as a source without a shape: an unknown function or
    connector, a window function without `window`, the argument count of
    `sign`, `year`, `month`, `day` and a connector, `substr` bounds, and a
    cast to any type but `Float` (PIE-S2103, PIE-S2104, PIE-S2105,
    PIE-S2306);
  - a condition that is not a `Bool` beside values of unknown type, for which
    0.1.3 emitted SQL that PostgreSQL rejects and MySQL converts: over a
    source without a shape, a `where`, shape `check` or index `when`
    condition that is a built-in call whose signature fixes another result
    type, such as `where len(t)` or `where lower(t)`, also through a `let:`
    name bound to one (PIE-S2202), and an operand of `and`, `or` or `not` or
    the condition of a conditional that is such a call, or of a known type
    that is not `Bool` beside an operand or branch of unknown type, such as
    `not lower(t)`, `t and 5` or `1 if len(t) else 2` (PIE-S2105). The same
    holds where an always-null argument leaves such a call's type unknown,
    as in `where lower(coalesce(null, null))`, also with a shape and in an
    explicit-module relation, which 0.1.3 passed and blocked at emission with
    PIE-B1003 or reported as a bare PIE-S2333 (a WHERE of such a relation
    with JOIN inputs still fails closed with PIE-S2333 unless a `let:`
    binding there has an error of its own). Over a source without a shape a
    `count()` output read alone, as an `and` operand or compared with a value
    that is not a number in `satisfying:` is PIE-S2202 or PIE-S2105, which
    0.1.3 refused only at emission;
  - an ORDER BY key that is a bare constant once `let:` names are inlined, and
    in a query with aggregates and no GROUP BY a key that reads an input field
    outside an aggregate (PIE-S2380);
  - a ROWS or GROUPS frame offset that is not a nonnegative `Int` literal up
    to 9223372036854775807, a larger window count literal (PIE-S2104),
    `cast(null as T)` and a literal LIKE pattern ending in an unpaired `!`
    (PIE-S2105);
  - a division with a known operand that is not `Int`, `Float` or `Decimal`
    (PIE-S2105); `Int / Int` is now an `Int` and a `Float` operand gives a
    `Float`, so a division result is checked where it is used;
  - `count` of a field typed by an alias of `Any` or of an enum, which 0.1.3
    passed at check and refused at emission (PIE-B1000), is PIE-S2314 at
    check;
  - in single files: a connector argument that is not a string literal
    (PIE-S2306), a repeated enum member (PIE-S2001), an aliased bare name that
    names no field (PIE-S2102), an INNER or LEFT JOIN whose target, `from`
    binding, relationship or role is unknown or whose VIA path does not
    connect (PIE-S2301, PIE-S2335), and a `let:` chain whose inlined
    expansion exceeds 768 weighted levels or 100,000 nodes (PIE-S2328);
  - in explicit-module projects: relationship declaration errors
    (PIE-S2601 to PIE-S2603), shape item errors (PIE-S2501 to PIE-S2503) and
    repeated enum members (PIE-S2001), as single files report them, and a
    relationship `on` operand error (PIE-S2604, in both modes), whether or
    not a query uses the relationship;
  - PostgreSQL emission of an identifier longer than 63 bytes, which
    PostgreSQL would truncate, and of a window integer argument outside int32
    (PIE-B1000);
  - single-file PostgreSQL emission of an arithmetic whose every operand is
    `null`, such as `null + null`, `-null` or `coalesce(-null, n)`, which
    PostgreSQL cannot type, and of a table or query that another relation of
    the file reads when one of its outputs is `null` itself, such as
    `v = null` or a `let:` name bound to `null`, which PostgreSQL gives the
    reader as a `text` column (PIE-B1000); MySQL emission is unchanged;
  - a `between` with one null bound, which is now a `Bool` whose other bound
    is checked against the value: `n between null and "z"` with an `Int`
    field and a conditional such as `n if flag else n between null and 1`
    are PIE-S2105, where 0.1.3 passed `check` and emitted SQL that
    PostgreSQL rejects;
  - an operand of `+`, `-`, `*`, `/` or `%` that the operator does not take
    beside a `null` operand, also a `let:` name bound to one, such as
    `label + null` for a `Text` field, `lower(label) - null` or `0.5 % null`
    (PIE-S2105), as `label + label` and `0.5 % 0.5` are, where 0.1.3 emitted
    SQL that PostgreSQL rejects for a `Text` operand;
  - a `let:` value, or an expression that reads a `let:` name, that is
    ill-typed once the name has the type of its value written in its place:
    a name whose value is `null` takes its type from where it is read, as
    `null` does, and over a source without a shape a name has its binding's
    type. With `k = null` and `j = coalesce(k, 1)`, `d = len(j)` is PIE-S2104
    in the binding and `v = lower(j)` PIE-S2104 at `lower`, where 0.1.3
    emitted `lower(COALESCE(NULL, 1))`; over a source without a shape, with
    `w = n is null`, `-w` is PIE-S2105 and `coalesce(w, 0)` PIE-S2104. An
    explicit-module project reports such an error too: in a binding of a
    relation without JOIN inputs, as `d = len(j)`, which 0.1.3 passed; in a
    SELECT item of such a relation, as `v = lower(j)`, where 0.1.3 reported
    PIE-S2102 `Unknown field: j`; and with JOIN inputs, where 0.1.3 reported
    a bare PIE-S2333 (see Explicit-module projects above). A column that a
    relation computes from such a name has that type in later relations: with
    `z = coalesce(k, n)` for an `Int nullable` field `n`, a later relation's
    `v = lower(z)` is PIE-S2104, where 0.1.3 emitted `lower("z")` (and in a
    project reported PIE-S2102 `Unknown field: k` and PIE-S2333).
- SQL that differs for programs 0.1.3 already emitted:
  - MySQL `Int / Int` emits `a DIV b` instead of `a / b`, so the result is an
    integer, not a DECIMAL; PostgreSQL bytes are unchanged. This includes a
    `let:` name read as above: with `k = null` and `j = coalesce(k, id)`,
    `j / 2` emits ``COALESCE(NULL, `id`) DIV 2``, and over a source without
    a shape, with `u = 7`, `u / 2` emits `7 DIV 2`, as the values written in
    place do; a later relation's `z / 2` of the column `z` above emits
    `` `z` DIV 2 ``.
  - Single-file `cast(j as Float)` of a `let:` name whose value reads `null`,
    such as `j` above, or of a column an earlier relation computes from one,
    such as `z` above, emits `CAST(... AS double precision)` (PostgreSQL) or
    `CAST(... AS DOUBLE)` (MySQL) as the value written in place does, where
    0.1.3 refused it with PIE-B1000.
  - Single-file `avg` of an `Int` emits `AVG(CAST(x AS double precision))` on
    PostgreSQL and `AVG(CAST(x AS DOUBLE))` on MySQL, as project SQL does.
  - PostgreSQL `sign(x)` of an `Int` emits `CAST(sign(x) AS bigint)`.
  - Single-file PostgreSQL `lag`, `lead`, `first_value`, `last_value` and
    `nth_value` of a string literal without a `lag`/`lead` default write the
    literal as `CAST('b' AS text)`, where 0.1.3 wrote `LAG('b')`, which
    PostgreSQL rejects; MySQL bytes are unchanged.
  - An ORDER BY input field that has the same name as a different output alias
    is qualified with its FROM item's reference name.
- Single-file `explain` reports the type an output has when it is computed
  from a `let:` name whose value reads `null`, also as the column of a later
  relation, where 0.1.3 reported `unknown`: with `j = coalesce(k, id)`,
  `v = j + 1` is `Int`.
- Diagnostics: many messages name their cause more precisely. Invalid source
  gets different PIE-P1000 wording, counts and positions: at most one parser
  error per top-level declaration, naming the unexpected token and what was
  expected. A lone CR now ends a line in every reported position, and
  PIE-P1004 counts lines only at LF, CRLF and CR. A project reports a restated
  diagnostic once.
- CLI: a failed write to stdout, and a refused `--output` (no SQL to write,
  an existing output the user may not write or that belongs to another user,
  or in single-file mode an existing FIFO, socket or device), exit `2`; a
  failing stderr is ignored and the command keeps its own exit code.
  Repeated or abbreviated `--format` and `--project` options are resolved as
  argparse resolves them, so `--form json` is no longer ignored.

### Included repairs

Compiler:

- Division follows SQL: `Int / Int` truncates toward zero (PostgreSQL `/`,
  MySQL `DIV`), a `Float` operand gives a bare `/`, and Pietto never inserts a
  cast; write `a * 1.0 / b` or `cast(a as Float) / b` to keep the fraction.
- Type aliases, alias chains included, are read as their builtin type by
  arithmetic, `not`/`and`/`or`, comparisons, `between`, `in`, `like`, the
  fixed-signature scalar functions, Bool conditions, the aggregates and the
  window value functions, so an alias program checks and emits like its
  base-typed twin.
- `sum` and `avg` of a `Decimal * Decimal` argument emit single-file SQL
  instead of PIE-B1000. `amount in (1, 2)` with a `Decimal` field is accepted
  wherever `amount == 1` is; project emission refuses that pair with
  PIE-B1003 (`membership_type_pair_not_admitted`), as it refuses the
  comparison.
- The `let:` inline limit (PIE-S2328) measures the recursion emission needs
  instead of crashing with RecursionError; `let:` bodies are checked with the
  earlier bindings, and a binding's own error no longer cascades into unknown
  fields or extra window errors.
- Single-file analysis of a long chain of tables takes linear time.
- Gradual typing is kept: an aliased read of a field of any type is a
  computed output, aggregates and `satisfying` over fields of unknown type are
  not refused at check, and a `satisfying` predicate of unknown type fails at
  emission with PIE-B1000 instead of an internal error.
- In a grouped query, `first_value`, `last_value` and `nth_value` over an
  aggregate output emit SQL instead of crashing.
- In single files, a `lag` or `lead` result of an enum keeps the enum's
  declaration, as a `first_value` result does, so a later relation may
  combine the column with a field of that enum, as in
  `coalesce(previous, status)`, which 0.1.3 refused with PIE-S2104 (and a
  conditional with PIE-S2105).
- Projects: a project relation may read a declaration written later in its
  module; a relationship JOIN over an input completed in the same run, such
  as a named `select distinct` query, and a SEMI or ANTI JOIN over a table
  that reorders a keyed source's fields emit instead of INPUT_REJECTED;
  repeated `on` operands, a VIA through a grouped endpoint, an unknown grain, a
  grouped query listing a window before an aggregate, a JOIN over a source
  with enum or shape fields, an ORDER BY of an enum group key, a GROUP BY over
  a global aggregate and a LEGACY_FLAT read of a set operation no longer
  crash; deeply nested project expressions are PIE-S2006 instead of a
  RecursionError traceback, and a configuration or package manifest nested
  too deeply is a `project_resource` error; a `let:` binding read in a
  SELECT item no longer reports a false unknown field; a bare PIE-S2333 for a
  relationship JOIN over an input it cannot read yet names the reason; the
  JOIN fan-out remedy lists each key once; and query block IR verification
  checks every use against the output its owner names.
- The execution API reports a recursion overflow while preparing a query as
  PIE-R1004.

CLI:

- Every command writes its results through one stdout writer. A full device,
  closed stream or other write failure exits `2` with a fixed notice instead
  of a traceback, exit `120` or a silent exit `0`, and a reader that closes the
  pipe early ends the run quietly. `--help`, `--version` and usage errors use
  the same writers.
- Operating-system errors are reported by path with a fixed English reason
  and errno or winerror codes, without temporary names or localized text.
- `--output` writes UTF-8 with LF line endings on every platform. A new file
  gets the mode `open(path, "w")` gives (`0o666` less the umask, or what a
  default ACL grants). A replacement never gets wider permission bits than
  the file it replaces: it keeps them only on Linux when both files have the
  same owner and group and are shown to carry no ACL, and otherwise keeps at
  most the owner bits. Temporary files use short `.pietto-*.tmp` names.
- C1 controls, line and paragraph separators and bidirectional controls are
  written as `\uNNNN` in CLI diagnostics, paths and project text records; SQL
  text (stdout and `--output`) and JSON values keep them raw.
- Windows: trusted project reads no longer refuse unchanged files because of
  ctime, and directory junctions are refused like symbolic links.

### Known limitations

- The release target is compiler and package coverage on CPython 3.12 and
  3.13 for Linux x86-64; the support boundary is established by formal
  acceptance of the actual distribution bytes. Native-route evidence is
  limited to CPython 3.13.13 on the qualified integration host with the
  lock's exact artifacts. Other platforms, Python versions, database releases
  and driver closures are not claimed. No signing or attestation.
- A successful `check` is not an emission proof. Single-file `explain` and
  `emit-sql` refuse an authored `qualify:` block and a relationship JOIN with
  PIE-I1000; JOINs, set operations, DISTINCT and relation lets need
  `emit-sql --project`.
- An error in a call written inside another def's body is reported at that
  def as often as the called def's expansion makes it, in single files and
  projects: with
  `def low(x: Int nullable) -> Bool nullable: return x < 3 or x < 4`, a def
  body that calls `low(null)` gets two PIE-S2105. An argument mismatch
  (PIE-S2395) there is reported once.
- A project check still repeats the errors of a JOIN `on` condition, written
  by hand or made by a `def` call, and reports a query header parameter passed
  to a `def` and read in a position that refuses it (PIE-S2355) at each use of
  the argument.
- In single files, `lag`, `lead`, `first_value`, `last_value` and
  `nth_value` over a field typed by an alias of an enum are PIE-S2104, while
  the enum itself is accepted; an explicit-module project types such a field
  as the enum and accepts both.
- In an explicit-module project, some reads of an enum value fail closed with
  PIE-S2333 at the table or query, where a single file passes or reports
  another code: without JOIN inputs, an aggregate of an enum field
  (PIE-S2314 in a single file and after a JOIN), a selected `let:` name
  bound to an enum value and a computed output of enum type other than a
  window value, such as `coalesce(new_status, status)`; with or without them,
  an output such as `status in ("active", null)`, and a window value function
  over an enum field of a row that also has a field of another module's enum
  of the same name. A project check does not type the ungrouped `order by` of
  a relation without JOIN inputs that is not `select distinct`, so
  `order by: lower(status)` passes `check --project` there.
- In an explicit-module project, a relation without JOIN inputs reports no
  error of its SELECT items when it is `select distinct`, nor of an aggregate
  argument that a project refuses (PIE-S2314 or PIE-S2315 in a single file,
  such as `max(t + 1)`): it reports PIE-S2333 at its table or query, or,
  beside another error such as one in its WHERE, only that error.
- In an explicit-module project, after an error in the `let:` of a relation
  with JOIN inputs, a SELECT item reports no error of its own when the
  relation has a GROUP BY or aggregates, when it is a window, or when it
  reads a relation, a binding with an error of its own or a field that does
  not resolve.
- Over a source without a shape, a built-in call with an argument of unknown
  type has an unknown type outside a condition, also where its result type
  does not depend on the argument: `lower(t) + 1` passes `check` and emits
  SQL that PostgreSQL rejects, `len(t) / 2` emits `/` on MySQL, which keeps
  the fraction that PostgreSQL drops, and a condition built on such a call,
  such as `where len(t) + 1`, passes. Over such a source a `count` output
  with an argument has an unknown type to `satisfying` too.
- In an explicit-module project, a relationship JOIN without `on` whose input
  is a `select distinct` query completes on its own, but reports PIE-S2333 at
  its table or query when that table or query is itself `select distinct` or
  once a later table or query reads its result with a JOIN `on`, a CROSS JOIN
  or `select distinct`. In some shapes, for example when such a query is
  joined through a relationship with the relation it reads, `check --project`
  passes but `emit-sql --project` reports INPUT_REJECTED (exit `2`).
- A function argument of known type is not checked when another argument has
  an unknown type: over a source without a shape, `matches(a, 1)` passes
  `check` and PostgreSQL emission writes `"a" ~ 1`.
- A `def` argument of unknown type is not checked against its parameter.
  Inside a built-in call, `coalesce`, conditional or `in` list only `null`
  itself takes a type from where it stands, and `null` takes none inside
  `and`/`or` or in a built-in whose parameter admits
  more than one type (`year`, `month`, `day`, `sign`), so the arguments
  `null and true`, `year(null)` and `coalesce(-null, n)` pass a `not null`
  parameter unchecked, written by hand or through a `let:` name.
- In a relation without JOIN inputs that is not `select distinct`, a project
  check does not type a `def` argument in the ungrouped `order by`, as it
  does not type the same expression written by hand there. An argument of
  known type that does not fit its parameter therefore passes
  `check --project` there: with a field `text: Text not null` and
  `def nn(x: Int not null) -> Int not null: return x`, `order by: nn(text)`
  passes. `emit-sql --project` blocks it with PIE-B1003 without naming the
  argument.
- In an explicit-module project, a relation with a `let:` binding of unknown
  type, such as `k = null`, fails closed: with JOIN inputs, a GROUP BY,
  `select distinct` or QUALIFY it reports PIE-S2333 at its table or query
  even when nothing in it is ill-typed (a single file passes such a GROUP BY,
  QUALIFY or relationship JOIN without `on`), and otherwise
  `emit-sql --project` blocks it with PIE-B1003 once it passes
  `check --project`. A `select distinct` relation or one with QUALIFY does
  not check its WHERE beside such a binding or a binding with an error of its
  own: it reports that PIE-S2333, or the binding's error, in place of the
  WHERE's errors.
- A `substr` start and count must be `Int` literals written in the call: a
  `let:` name bound to one, such as `start = 1` in `substr(t, start, 1)`, is
  PIE-S2104, also in a `def` argument, although single-file emission would
  write the literal in its place.
- Division with a `Decimal` operand is not specified yet: it has no result
  type and emits a bare `/`. Division by zero follows the target (PostgreSQL
  raises an error, MySQL returns NULL), and dividing the smallest `Int` by -1
  is not specified.
- `def` takes only the eight builtin types (or a same-file alias of one) and
  positional arguments; a call is refused where the written form must be a
  literal, a field or a window call that Pietto checks by its own rule, such
  as inside a window specification, LIMIT, a VALUES row or a relationship
  condition (PIE-S2397). A comparison, `between` or arithmetic is not proven
  non-null, so such defs declare a `nullable` result. An argument appears in
  the SQL as often as the body uses its parameter. `constraint` and `derive`
  still cannot be called.
- `--output` does not copy a replaced file's owner, group, set-id or sticky
  bits or its ACL entries; the write check uses the real user, so root can
  still replace a read-only output.

### Support and release boundary

The [language guide](language.md) is the reference for the forms above; its
[Layout](language.md#layout) and
[Inline functions](language.md#inline-functions-def) sections describe the new
syntax. Published bytes are never overwritten. A later defect
is addressed in a later version; any PyPI yank remains an owner action.

---

## Phase70 public alpha release notes — 0.1.3

**Status:** These notes describe `0.1.3`, published and byte-verified on the
versioned GitHub pre-release and PyPI channels.

`0.1.3` extends query authoring and checked execution in explicit-module
projects (`schema_version = 2`). Pietto remains an alpha; the CLI still has no
database-execution command.

### New capabilities

- **Relation lets.** `let NAME:` at the start of a table or query body declares
  a local relation whose body is FROM-based, a set operation or a typed VALUES
  body. The other lets and the body of its declaration read it by name with
  `from`, a JOIN target, a set operand or an `exists`, `scalar` or `in` read,
  any number of times and whether it is written before or after them (a let
  with `capture` lines, below, is read exactly once). Project
  SQL emits each let once as one named CTE, after the lets it reads and exactly
  like the equivalent module-level declaration, and every read refers to that
  CTE; a let keeps its own LIMIT, so a filter written where it is read stays
  outside that LIMIT. A source read only inside a let is a source of the query
  for the emission contract, the compiled query, source qualification and R2
  source requirements. A let is never a module declaration: it cannot be
  exported, imported, selected by `emit-sql --project` or compiled on its own.
  A declaration has at most 64 lets (`PIE-S2357`); a let named like a module
  relation, an import binding, another let or a JOIN binding is `PIE-S2001`,
  and no name hides another. A let that no block of its declaration reads is
  `PIE-S2359`, reads that form a cycle, a let reading itself included, are
  `PIE-S2302`, and a let nested deeper than 16 query blocks is `PIE-S2360`.
  The row-level `let:` clause keeps its meaning.
- **Named query parameters.** An entry `query` header declares at most 64
  `Bool`, `Int`, `Float` or `Text` parameters, each `not null` or `nullable`,
  for example `query since(low: Int not null, note: Text nullable):`. A read is
  available in `let:` bindings, `where`, JOIN `on`, ungrouped SELECT items,
  `satisfying`, `qualify`, ORDER BY keys through a `let:` binding or a restated
  selected expression, a computed group key of a query without JOIN inputs,
  `count`, `avg`, `min` or `max` of one `let:` name, and as a window value,
  `lag`/`lead` default or structural count (`lag`/`lead` offset, `ntile` bucket
  count, `nth_value` position; an `Int not null` parameter, `PIE-S2358`).
  LIMIT, window frames, window PARTITION BY and ORDER BY keys and other
  positions refuse a read (`PIE-S2355`). A header is available on an entry
  query whose own FROM reads a relation, with or without relation lets. Every
  FROM-based let of that query reads the header like its body, under the same
  position rules, a let with `capture` lines included (its reads render where
  the let renders); no other declaration reads it. A parameter named like a
  let of the query or like an input field, `let:` name, relation, JOIN
  binding, SELECT output or named window of the query or of one of its lets is
  `PIE-S2354`, and a query with parameters is never the input of another
  relation nor read by `exists`, `scalar` or `in` (`PIE-S2356`). On a VALUES,
  set-operation or table-function body, and beside a let whose FROM is a table
  function (whether or not that let reads a parameter), a header stays
  `PIE-S2346` at each parameter.
  `emit-sql --project` writes the unbound template as `pietto.sql-emission.v2`
  with a typed placeholder for each read under both literal policies:
  PostgreSQL reuses one `$n` per parameter across every CTE, subquery and
  LATERAL derived table, and MySQL writes one `?` per read in rendering order.
  One statement renders at most 65,535 placeholders, reads and bind-safe slot
  uses together (`PIE-B1007`, `parameter_occurrence_limit`). A check that
  needs a value is a binding obligation (`int_range_representable`,
  `text_result_width` or `structural_count_interval`) naming every parameter
  it depends on, including one read in a let with `capture` lines, and
  re-derived at every binding. `compile_query` and
  `export_bundle` keep the unbound template (bundle format marker
  `pietto.compiled-execution.v2`), and `execute(..., parameters={...})` binds
  it by name on `postgres_rows`, `mysql_rows` and `postgres_adbc`; a missing
  or extra name, a value of the wrong type, NULL for a `not null` parameter
  and a failed obligation are refused before any connection. `save`,
  `save_recoverable` and `relay_live` bind new values the same way before the
  workspace opens; `open_saved_read`, `release_saved_read`,
  `publish_saved_generation`, `verified_export` and `recover` restate the
  saved binding, and any difference is `PIE-R1009` (`BINDING_VECTOR`).
  `values=` slots are unchanged and independent.
- **Computed group keys and `let:` extrema.** In an explicit-module query,
  `group by` may name a computed `let:` binding; the emitted SQL groups by that
  value's LET-stage column, never by a repeated expression. Such a key never
  supplies source-row grain, and R2 refuses it before any workspace access
  (`PUBLIC_R2_COMPUTED_GROUP_KEY`). With JOIN inputs the key records every JOIN
  side its value reads but never proves a side unique per group, so it never
  removes a fan-out refusal; only direct field keys protect a JOIN side. `min`
  and `max` accept one `let:` name and keep its proven range while admitting
  NULL; with JOIN inputs the argument reads its JOIN-side fields under the
  fan-out rule of a direct field argument.
- **Typed VALUES.** A table, query or relation-let body may be a typed
  `values(name: Type not null, ...)` header followed by one row of fixed
  literals per line, or the header alone for a zero-row relation. Each column
  is `Bool`, `Int`, `Float` or `Text`, `not null` or `nullable`; rows keep
  their order and duplicates, and the row schema comes only from the header. A
  column type, a row width, a cell that is not a fixed literal, a cell that
  does not match its column, and more than 1,000 rows or 64 columns are
  `PIE-S2361` to `PIE-S2365`; a body within those limits whose emission
  exceeds the compiler's generated-structure or document limit is BLOCKED with
  `PIE-B1007`. Project SQL writes every column alias and every cell inside a
  CAST to its declared type, and a cell is never a bound parameter. A VALUES
  body read beside a physical source emits and compiles for PostgreSQL and
  MySQL. A statement whose only inputs are VALUES bodies runs on PostgreSQL
  under a session-context qualification whose premise includes `pg_catalog`
  and that records no relation root and no relation catalog check; MySQL
  refuses it (`PIE-B1003` at emission and compilation, `PIE-R1003` before
  connecting). R2 refuses a query with a VALUES body before any workspace
  access (`PIE-R1004`, `PUBLIC_R2_VALUES_COORDINATE_BASIS`). Grouping over a
  VALUES input is not available yet (`PIE-S2333`).
- **Closed relation reads.** In a table or query body `exists r` and `not
  exists r` test whether `r` has a row, `scalar r.c` reads the column `c` of
  `r`, and `value in r` and `value not in r` compare a value with the one
  column of `r`; `r` is a source, a module table or query, or a let of the
  declaration. A read is available in WHERE and in the SELECT of an ungrouped
  query, let bodies included; anywhere else it is `PIE-S2349`, `PIE-S2348` or
  `PIE-S2350` at the read. `exists` is a `Bool not null`. `scalar` is always
  nullable: a read of no row is NULL, and a read of more than one row is the
  database's own runtime error, `PIE-R3003` with SQLSTATE `21000`; no LIMIT is
  added. `in` and `not in` keep SQL three-valued logic, are a nullable `Bool`
  and are never rewritten to an ANTI JOIN, a literal list or a COALESCE; over
  an empty `r`, `NULL in r` is false and `NULL not in r` is true. `scalar`
  cannot yet read a set, an authored JOIN, a table function or a relation that
  reads one of them or a VALUES body (`PIE-S2348`), while a VALUES body itself
  is read like any relation; for such a block `emit-sql --project` and
  `compile_query` check the one column of an `in` read (`PIE-B1003`). Project
  SQL emits each read block once as its own named CTE and each read as a
  subquery over it, so the read block's `order by` and `limit` stay inside its
  CTE. A source read only through relation reads is a source of the query. R2
  refuses a query with a relation read before any workspace access
  (`PIE-R1004`, `REFINEMENT_EXPRESSION_BLOCK_READ`).
- **Correlated lets and LATERAL joins.** A relation let may start with
  `capture NAME` lines, one per line, naming the FROM input or a JOIN binding
  of its declaration body; inside the let `NAME.field` reads that field of the
  current outer row, while bare names keep naming the let's own input. Only
  FROM and JOIN row fields are captured. A captured field keeps the outer
  field's type and is nullable when that field is or when an earlier LEFT,
  RIGHT or FULL JOIN may null-extend its binding; an outer JOIN ON condition
  never narrows it. Such a let is read exactly once: by `exists`, `not
  exists`, `scalar`, `in` or `not in` in the WHERE or in the SELECT of an
  ungrouped declaration body, or as the target of a `cross join`, `inner join`
  or `left join`, which reads it LATERAL with no new keyword. Every outer row,
  duplicates included, gets its own result: a correlated read is never
  rewritten to a JOIN, deduplicated or decorrelated, a correlated `scalar`
  keeps the runtime error for more than one row (`PIE-R3003`, SQLSTATE
  `21000`), `in` and `not in` stay three-valued, and a `left join` keeps each
  left row without a row of the let once, with the let's fields NULL. The let
  body is a FROM relation with an optional WHERE and an ungrouped, window-free
  SELECT; a let joined LATERAL or read by `scalar`, `in` or `not in` may end
  in ORDER BY and a static LIMIT, a top-k per outer row in which the database
  chooses among rows that tie on every key. Project SQL emits the let inside
  its read as nested derived tables, or as the JOIN's `CROSS JOIN LATERAL`,
  `INNER JOIN LATERAL ... ON` or `LEFT JOIN LATERAL` derived relation, never
  as a CTE. A `scalar`, `in` or `not in` read of a let that ends in ORDER BY
  and LIMIT is PostgreSQL only: PostgreSQL wraps the let in the read's own
  derived table, while MySQL `emit-sql --project` and `compile_query` refuse
  each such read, in source order, with `PIE-B1003`
  (`mysql_correlated_order_or_limit_read_not_admitted`) before any connection,
  and `load_bundle` refuses a MySQL bundle that claims one (`PIE-R1008`); a
  let joined LATERAL keeps its ORDER BY and LIMIT on both targets. The binding of a table
  function cannot be captured (`PIE-S2366`), though its body's JOIN bindings
  can; otherwise, a capture line naming no single FROM or JOIN
  row input is `PIE-S2366`, a repeated
  capture name `PIE-S2367`, a capture of an input of the let itself
  (self-correlation) `PIE-S2368`, a captured field the input does not have
  `PIE-S2369`, a direct table-function FROM in a capture let (read it through
  another let), another let body or ORDER BY that correlation does not support,
  and every read of the let after its first `PIE-S2370`, a capture of an input
  that is not left of the LATERAL JOIN `PIE-S2371`, and a RIGHT, FULL, SEMI or
  ANTI JOIN of such a let `PIE-S2372`. A field read of a captured input whose
  columns are not known before completion (a set, an authored JOIN, a typed
  VALUES body, a table function, a relation reading one of them, or a relation
  whose own errors leave its columns unknown) is `PIE-S2369` at `check
  --project`, whatever field it names. When the captured outer input's fields
  are known, the let's own FROM may read a set, an authored JOIN, a typed
  VALUES body or a let reading a table function. R2 refuses a query with a
  correlated read
  (`REFINEMENT_EXPRESSION_BLOCK_READ`) or a LATERAL JOIN
  (`REFINEMENT_LATERAL_JOIN`) before any workspace access; ordinary execution
  on every route, `save` and bundles accept them.
- **Bounded `generate_series`.** A table, query or let body may read
  `from generate_series(start, stop, step) as n`, a zero-input relation whose
  rows and only column `n` are `Int not null`. `generate_series` with exactly
  three fixed integer literals in the signed 64-bit range is the only admitted
  table function: another function is `PIE-S2373`, another argument count
  `PIE-S2374`, an argument that is not such a literal (`null`, another literal
  type, a name, a parameter or an expression) `PIE-S2375`, a zero step
  `PIE-S2376` and more than 1,048,576 rows `PIE-S2377`. Its closed catalog
  entry carries the determinism and side-effect evidence admission consumes.
  Grouping or aggregating directly over a table-function input is `PIE-S2333`
  for now (read it through a let first), and `scalar` cannot read it
  (`PIE-S2348`). Project SQL writes each input as a CTE over
  `pg_catalog.generate_series` with each fixed argument CAST to
  `pg_catalog.int8`, never as a bound parameter; a binding longer than 63
  UTF-8 bytes is `PIE-B1002` (`table_function_binding_unrepresentable`). It is
  PostgreSQL only: MySQL `emit-sql --project` and `compile_query` block each
  input with `PIE-B1003` (`table_function_not_admitted_on_target`), and
  `load_bundle` refuses a MySQL bundle that claims one (`PIE-R1008`).
  PostgreSQL runs a statement whose only inputs are table functions or VALUES
  bodies under the session-context qualification of a VALUES-only statement,
  with no runtime catalog check of the function. R2 refuses a query with a
  table function before any workspace access (`PIE-R1004`,
  `PUBLIC_R2_TABLE_FUNCTION_COORDINATE_BASIS`).

### Refusals and limits

The new forms are available only in EXPLICIT_MODULES projects. Single-file
analysis and LEGACY_FLAT projects keep refusing them with the temporary
`PIE-S2345..PIE-S2352` diagnostics, and PACKAGE_ROOT `explain --project` does
not read relation bodies, so explaining a package that uses them does not make
its relations available. In an explicit-module project each file reports its
pre-admission diagnostics first, in source order (the capture forms
`PIE-S2366`, `PIE-S2367`, `PIE-S2368` and `PIE-S2370..PIE-S2372` among them),
and then the header checks of its entry queries; after either, semantic
analysis does not run. In an explicit-module project a header on a VALUES,
set-operation or table-function body or beside a let that reads a table
function (`PIE-S2346`) is still refused this way. This release adds
`PIE-S2345` to `PIE-S2377`.

Known limitations of this release:

- A typed VALUES body of 1,000 rows and 64 columns passes `PIE-S2365` but is
  always BLOCKED at emission by the compiler's generated-structure or document
  limit (`PIE-B1007`).
- The width and type pair of an `in` read of a set, an authored JOIN, a
  typed VALUES body or a table function is checked only at emission
  (`PIE-B1003`), not by `check --project`.
- An INNER JOIN whose ON has a nullable `Bool` field as an AND conjunct of its
  own (`on o.flag`) checks, but `emit-sql --project` and `compile_query` block
  it with `PIE-B1002` (`join_output_nullability_drift`) on both targets;
  `o.flag == true` is not admitted either (`PIE-B1003`). Write the test in
  WHERE instead (`where o.flag`).
- In a let with `capture` lines, an ORDER BY key that is not a field of the
  let's input, such as one of the let's own SELECT outputs, is reported only
  as `PIE-S2333` at the declaration (`Project relation semantic completion is
  unavailable`), with no diagnostic at the key.
- While a module import cycle exists (`PIE-S2703`), a project check reports
  besides it only parse, semantic analysis and source connector diagnostics;
  the checks made while completing relations appear once every cycle is
  fixed.
- An unknown field in a SELECT item of an explicit-module query can be
  reported twice as `PIE-S2102` at the same position.
- In a single-relation explicit-module query, a reference or shape error in a
  grouped `satisfying` is reported only as `PIE-S2333` at the declaration.
- LEGACY_FLAT project checks report neither `satisfying` errors nor a WHERE
  condition that is not `Bool`, which single-file `check` reports, and a
  LEGACY_FLAT query that reads a set operation stops `check --project` with an
  internal `AssertionError`.
- A selected query that reads a table declared later in the same module checks,
  but `emit-sql --project` refuses it as
  INPUT_REJECTED (`Project planning roots are unavailable.`) and
  `compile_query` raises `CompileRejected`; declare the read relation first.
- `compile_query` refuses (`PIE-R1004`, `COMPILED_EXPORT_SOURCE_BINDING`) an
  emission contract that also describes a source the query does not read,
  which `emit-sql --project` accepts; describe only the query's sources.

### Included repairs

- A module import cycle in an explicit-module project no longer crashes the
  project check, `emit-sql --project` or `compile_query`; it is reported as
  `PIE-S2703`.
- `import pietto.execution` no longer imports the saved-result job subsystem;
  the first use of a saved-result name imports it.
- In an explicit-module project, `satisfying` on a query without GROUP BY no
  longer crashes `check --project`, `emit-sql --project` or `compile_query`:
  it is `PIE-S2323` (`PIE-S2308` when the predicate holds an aggregate), as in
  single-file analysis. A single-relation aggregate query with `satisfying`,
  which reported `PIE-S2333` in `0.1.2`, now also reports `PIE-S2323`, the
  documented code.
- On `postgres_adbc` a server error raised while the result is read keeps its
  SQLSTATE: a `scalar` read of more than one row is `PIE-R3003` with
  `sqlstate` `21000`, as on the other routes, instead of an error without a
  `sqlstate` (cause `ArrowInvalid`), and the 10 second statement limit reached
  while reading is `PIE-R3002` (`STATEMENT_TIMEOUT`) instead of `PIE-R3003`.
  [Execution](execution.md) now states the terminal facts of a server error
  per route: `postgres_adbc` reports cleanup `LOCAL_CLOSED_REMOTE_UNOBSERVED`
  with no cleanup failure, and on `mysql_rows` a statement error does not end
  the transaction, which is then rolled back (`ROLLBACK_ACK`).
- `save_recoverable` and `recover` now reject a query whose largest
  continuation page binds more placeholders than the `parameters` resource
  limit with `PIE-R1004` (`REFINEMENT_RESOURCE_LIMIT`) before workspace access
  or a connection.

### Compatibility and retained data

Bundles and saved jobs produced by `0.1.2` are refused under `0.1.3` by code
identity. Pietto neither migrates nor rewrites them; keep the matching old
environment to use retained state, and compile again for this release.
`pietto.sql-emission.v1` and project JSON v2 keep their formats, and relation
lets, VALUES bodies and relation reads add nothing to project JSON; only a
verified document of a query with header parameters is
`pietto.sql-emission.v2`, which a v1 reader refuses by its tag. Such a query
bundles as `pietto.compiled-execution.v2`, which a v1 reader refuses, and a
saved binding with parameters is recorded as `pietto.binding-vector.v2`; a
binding without parameters is recorded as before.
The VS Code extension `0.1.0` accepts only the `0.1.2` wheel or the `9e74aa68`
baseline fingerprint and refuses `0.1.3`; updating it belongs to the
extension's owner, and this release adds no stable editor API.

Target-conformance receipt v3 stores each public emission document once. It is
test and CI evidence only, not a query, bundle or saved-job format.

### Support and release boundary

The release target is compiler and package coverage on CPython 3.12 and 3.13
for Linux x86-64. That support boundary is established only by acceptance of
the formal distribution bytes. Native route evidence is limited to CPython
3.13.13 on the qualified integration host with the lock's exact artifacts;
other native platforms, Python versions, database releases and driver closures
are not claimed. Published bytes are never overwritten. A defect found after
release is fixed in `0.1.4`; any PyPI yank is the owner's action, noted on the
GitHub pre-release.

---

## Phase69 public alpha release notes — 0.1.2

These notes describe `0.1.2`. Its versioned GitHub pre-release and PyPI listing
determine release availability. The historical `0.1.1` wheel and `v0.1.1`
assets are not replaced.

### Public alpha API

- `pietto.execution` exposes explicit `postgres_rows` for PostgreSQL 18.6,
  `mysql_rows` for MySQL 8.4.12, and `postgres_adbc` for PostgreSQL 18.6.
  Each route uses its selected pinned dependency closure and never falls back to
  another route.
- Results use caller-owned Arrow batches and terminal outcome facts.
  `UNKNOWN`, `REMOTE_QUIESCENCE_UNCONFIRMED`, and remote-unobserved cleanup are
  not acknowledgements. `ResultHandle.cancel()` may be requested by a
  controller thread; it returns `None`, while the outcome retains the observed
  cancellation, transaction, and cleanup facts.
- Query bundles carry caller-held content, producer, and compatibility records.
  They are snapshots: source edits need a new compilation. Bundle loading and
  every execution attempt check current code identity. Bundle trust records
  are checked at load time; each execution needs fresh access and deployment
  premises.
- v7 saved workspaces provide ordinary save, R1 source-free re-read,
  fixed-snapshot verified export, R2 same-source recovery, local publication,
  narrow caller-owned unpublished-generation retirement, and relay to the
  local reference cooperative sink. `inspect_job()` is read-only recorded
  metadata and grants none of those authorities.
- The API remains alpha. Names, fields, error codes, and behavior may change
  in later alpha releases; existing compiler and CLI contracts remain separate.
  The CLI still has no database-execution command.

### Compatibility and retained data

The installed Pietto and ANTLR code identity is checked for compile, bundle
load, and execution. The `0.1.2` version update changes the CLI fallback version,
and the wider source tree can also change that identity. A bundle or saved-job
record made under `0.1.1` can therefore be refused under `0.1.2`. Pietto
preserves the original bytes and does not migrate them; use the matching old
environment when the old state must remain usable.

### Support and durability limits

Only CPython 3.13.13 on Linux x86-64, with the lock's exact artifacts on the
qualified integration host, has native evidence for all three routes. Windows
native execution is `NOTRUN`; offline Windows compiler-project checks do not
establish job, database, or platform support.

Public save creates v7 only, with no migration. A workspace permits one
coordinator at a time and refuses concurrent capture, recovery, or relay with
`RUNTIME_BUSY`. There is no public scheduler, general garbage collector,
age-based deletion, or general directory cleanup. `retire_generation` removes
only the caller-owned unpublished generation's latest-checkpoint root; it does
not delete files. Publication-owned retention is permanent.

R1 and verified export are source-free reads with compatible code, fresh
caller-held scalar trust, integrity, and reader protections. R2 is live
same-source recovery: it requalifies one caller-supplied compiled-source
requirement for every source in compiled order, including guarded and refined
sources. A saved close only resumes or awaits bounded cleanup; until it
settles, remote state is `UNKNOWN` and no acknowledgement is claimed.

### Included compiler and CLI repairs

- A single leading UTF-8 BOM is ignored without changing parsed AST or source
  locations; a second or non-leading BOM remains invalid, and the original
  UTF-8 byte budget still applies.
- When the terminal cannot encode CLI output, Pietto preserves the terminal's
  configured encoding and returns the established clear output-encoding error
  instead of silently replacing source or diagnostic text.
- A single-file relation name may be `table` or `schema.table` (MySQL uses the
  database position); each component is quoted independently. Empty components
  and names with more than one dot fail closed with `PIE-S2306`.
- Cross-family comparison operands fail closed with `PIE-S2105`; there is no
  implicit conversion. This does not change the existing SQL three-valued
  behavior for comparisons with `null`.

### Attribution and release boundary

`THIRD_PARTY_NOTICES.md` records unbundled runtime and execution dependencies
and separates wheel/sdist material from the GitHub source archive.
`LICENSES/SOURCES.md` records the retained original-text provenance. This is
an attribution record, not a legal conclusion.

Before publication, the release stage must inspect the exact accepted wheel,
sdist, and source archive against those per-channel notices. Independent
rebuilds may verify the accepted bytes but never replace them.
