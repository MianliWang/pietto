# Phase70 public alpha release notes — 0.1.3 (draft)

**Status:** draft. These notes describe the current source, not a release:
the package version is still `0.1.2`, and no `0.1.3` tag, GitHub pre-release,
PyPI upload or release date exists or is authorized by this text. The release
step replaces this status and the `TODO(S19)` below with the accepted
candidate's evidence.

`0.1.3` extends query authoring and checked execution in explicit-module
projects (`schema_version = 2`). Pietto remains an alpha; the CLI still has no
database-execution command.

## New capabilities

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

## Refusals and limits

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

## Included repairs

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

## Compatibility and retained data

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

## Support and release boundary

TODO(S19): the support statement of the accepted candidate's installation and
native execution evidence; the `0.1.2` statement below applies until then.
Published bytes are never overwritten. A defect found after release is fixed
in `0.1.4`; any PyPI yank is the owner's action, noted on the GitHub
pre-release.

---

# Phase69 public alpha release notes — 0.1.2

These notes describe `0.1.2`. Its versioned GitHub pre-release and PyPI listing
determine release availability. The historical `0.1.1` wheel and `v0.1.1`
assets are not replaced.

## Public alpha API

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

## Compatibility and retained data

The installed Pietto and ANTLR code identity is checked for compile, bundle
load, and execution. The `0.1.2` version update changes the CLI fallback version,
and the wider source tree can also change that identity. A bundle or saved-job
record made under `0.1.1` can therefore be refused under `0.1.2`. Pietto
preserves the original bytes and does not migrate them; use the matching old
environment when the old state must remain usable.

## Support and durability limits

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

## Included compiler and CLI repairs

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

## Attribution and release boundary

`THIRD_PARTY_NOTICES.md` records unbundled runtime and execution dependencies
and separates wheel/sdist material from the GitHub source archive.
`LICENSES/SOURCES.md` records the retained original-text provenance. This is
an attribution record, not a legal conclusion.

Before publication, the release stage must inspect the exact accepted wheel,
sdist, and source archive against those per-channel notices. Independent
rebuilds may verify the accepted bytes but never replace them.
