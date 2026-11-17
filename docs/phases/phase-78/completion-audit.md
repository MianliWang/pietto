# Phase78 completion audit

Phase78 owns the roadmap's SQLite deep adaptation. It delivered two
verticals under its [route](route.md): B1, single-file SQLite SQL
(D78.01–D78.11), published in `0.2.0`; and the first tier of B2, SQLite
project mode with `having`, `count_distinct`, `avg` of an `Int` and a
one-sided `sum` of an `Int`, and the read-only `sqlite_file` route over a
caller's file (PL.47 with the rows it keeps, PL.54, PL.59 and D78.12, in
the [decision record](../../decisions.md)). This audit is S16. It records
delivery, qualification, what is not verified, the acquisition review and
the CI health, and closes Phase78; B2's second tier goes to the owner's
plan. The batch that carries R1 and S16 determines the closure's
publication through its Gate 2 seal and natural exact-head CI; this
document does not certify its own publication, and a documentation commit
after that batch is published, before the `0.2.2` release commit, records
the batch's facts here.

## Baseline and publication boundary

| Step | Fact |
| --- | --- |
| B1 | Gate 0 on `ab972f36` with natural CI `42831340276`. Published in the Phase78–80 integration batch ending at `94b4097a` (tree `58f5e281`), whose natural exact-head CI `43645308189` passed all 21 jobs, and shipped in `0.2.0` (PL.32, PL.37); the [B1 record](route.md#b1-record) holds its facts |
| B2 Gate 0 | S05 on `8cb9d9de` (tree `b2ad91b2`) with natural CI `43767179471` and its health ([B2 starting point](route.md#b2-starting-point)) |
| Integration | After batch 2, which published the third whole-tree test pass at `851ad83f` (PL.49), as the [single-writer order](route.md#b2-single-writer-order) requires. The slices were built on a lane branch from `851ad83f` and replayed one commit each onto `main` at `64a7f885` |
| First batch | 13 commits on `64a7f885`, ending at `31859bc66a6f53d301491dcaed9ad9111c94e089` (tree `8e8a9fba8f04402c2276b012836ae6b56165dc11`): S06–S12, the diagnostics rows, PL.59 and D78.12, the Windows CI change and the MySQL catch-up's Gate 1 record, below them the owner-answers record `489108bc`. Fast-forward pushed under PL.52 on 2026-11-16 at 20:04:45Z by the lead's record. Its Gate 2 is [below](#gate-2-durations); its natural exact-head CI `43946002245`, push/main attempt 1, succeeded, as the health history of `44006845752` records ([CI health](#ci-health)) |
| Between | The pure verifier fidelity repair, four commits ending at `6a0646b4` (tree `feeb6b93`), whose natural exact-head CI `44006845752` passed all 21 jobs; not Phase78's work (PL.20, PL.60) |
| Second batch | R1 `a47a5713` (tree `a6735d4f`) on `6a0646b4`, S16 above it and, above S16, the VR2 fix that lets a split Gate 2's local receipt accept the route's counted ARROW skip and, above the fix, the documentation commit that records the Gate 2 and CI facts of DuckDB B2's batch in its [audit](../phase-79/b2-completion-audit.md#budget-failures-and-gate-2) (by the lead's record of 2026-11-17): one Gate 2 and one natural CI (PL.59 (3)); they publish as one batch under PL.52 |

The [B2 record](route.md#b2-record) gives each slice's commit and the
midpoint record. B2 has two release-note fragments, `78-s06-sqlite-project-mode.md`
(tier 1a) and `78-s11-sqlite-file-route.md` (tier 1b); both reached `main`
in the first batch, and the `0.2.2` release commit assembles them.

## Accepted scope

**Opened by B2.** In an explicit-module project, a `sqlite.table("name")`
source checks, and `emit-sql --project ... --dialect sqlite`, with or
without `--all`, `compile_sql` and `compile_all_sql` emit one `SELECT` over
`main`.`<table>` for `where`, `group by`, `having`, `order by`, `limit` and
`select` over `Int`, `Text`, `Bool` and `Float` fields and query
parameters, with `count`, `count_distinct`, `min`, `max`, `avg` of an `Int`
and `sum` of an `Int` whose contract `int_range` lies on one side of zero;
`COLLATE BINARY` at each `Text` comparison and key. Single files gain
`having`, `count_distinct` and `avg` of an `Int`, and write `Bool` literals
as `1` or `0` (PL.54). `compile_query(dialect="sqlite")` and
`execute(route="sqlite_file")` run a query in process, read-only, behind
eleven defences and a value and integrity check, on the qualified build, at
most 128 MiB and 1,048,576 rows per source table
([SQLite project mode](../../spec/sqlite-project-v1.md),
[SQLite file route](../../execution.md#sqlite-file-route)).

**Kept refused.** The second tier (JOINs, range-proved `Int` arithmetic,
windows); other arithmetic, `Float` `sum` and `avg`, text functions and
`LIKE`; `Decimal`, `Date`, `Timestamp`, `UUID` and nested fields;
`--literal-policy bind-safe`; a `sum` over a mixed-sign range and
single-file `sum`; `Text` holding NUL in a file or a parameter; bundles,
saved results, relay, jobs and R2 on SQLite; every other build and
platform. The route's [B2 deferred owners](route.md#b2-deferred-owners)
and the roadmap's [deferred subjects](../../roadmap.md#deferred-subjects)
name each owner.

PostgreSQL, MySQL and DuckDB bytes, contracts and diagnostics are unchanged
apart from the refusal of a `sqlite.table` source that the specification
states; `VERSIONS` and every compiled record are unchanged.

## Qualification evidence

- **Native, in process.** On the measured build, SQLite `3.53.1` with its
  source id and 46 compile options, under CPython 3.13.13 and 3.12.13 on
  Linux x86-64: row 9 of validation runner acceptance records the S09 cells
  and the route's S12 cells under both interpreters on 2026-11-16 (the
  specification's [qualification](../../spec/sqlite-project-v1.md#qualification)).
  Each authoritative Gate 2 declares the qualified class (D78.07) and,
  since the first batch, runs `tests/test_execution_api_sqlite_file.py`
  again with the `arrow` extra and admits no skip: 80 passed and none
  skipped in both Gate 2 runs [below](#gate-2-durations). S16's own run on
  R1's tree, on 2026-11-17 from 06:16:53Z to 06:17:06Z under CPython
  3.13.13 only, with the qualified class and `-n 4 --dist=loadfile`, passed
  587 tests of the four SQLite owners and `tests/test_plan_target_profiles.py`
  with none skipped; the native module recorded 121 single-file `cell` and
  185 `project_cell` properties beside 4 `sum_order`, 4 `golden`, 4
  `native_error` and 2 `premise_error`, and observed the build `3.53.1`.
- **Judges and coverage.** `test_the_judge_fails_every_fabricated_fail_open_shape`
  and `test_the_sqlite_route_judge_accepts_its_result_and_refuses_each_fabricated_shape`
  fail every fabricated fail-open shape (72-4), and the coverage law asks a
  native cell of every form the emitter and the adapter write (73-6).
- **PostgreSQL replay, R1.** One campaign, `PASS` in its first attempt on
  2026-11-17, 124 entries: the 14 single-file T2 cells and 110 project
  cells, 12 with bound arguments; `ZERO_SIGN` on two cells, where a
  `STRICT` `REAL` column stores `-0.0` as `0.0`, and `AVG_ORDER` on the two
  cancelling `avg` cells, each value one of the left-to-right sums listed
  before the run ([R1 record](route.md#b2-qualification-and-replay)).
  `test_each_r1_postgres_replay_binds_the_bytes_it_ran` judges it on every
  runner with no database.
- **Windows refusal.** Since `a6c89521` both Windows jobs run the route's
  test file, whose native cells assert the route's own refusal there and
  skip, and whose two POSIX cells skip themselves (PL.59 (2)). The first
  natural CI with that change, `43946002245`, succeeded; in `44006845752`
  each Windows job passed 24,786 tests with 252 skips. The log lines read
  do not split those counts by file, so only the jobs' success shows the
  file's result there. No Windows support is claimed.
- **Hosted Linux CI** asserts the refusal of the native classes and runs
  the byte tests everywhere.

## Not verified

- **R1's five gaps.** `having` with `Int`, `Text` and `Float` query
  parameters; a `Bool` parameter echoed in `select` or read bare in
  `where`; binding a `pg_bool` argument; the `Bool`-name cells in either
  mode; and the one-sided `sum` overflow, whose SQLSTATE 22003 stays
  inferred. The lead accepted them; each would need a new campaign, which
  needs the owner.
- **PostgreSQL's `avg` summation** in general stays *inferred*; R1 observed
  only its two cancelling cells.
- **Other builds and platforms.** Hosted CI's SQLite builds are
  unobserved, Windows and macOS do not run the route, and the Teach column
  of runner row 9 stays Not observed (D78.09).
- **The library itself.** No claim is made of SQLite's memory safety on a
  malformed file; a file replaced between the type check and the open is
  not detected; `cancel()` during a lock wait takes effect at the deadline
  (the 1b fragment's known limitations).
- **The derived rows.** The specification's
  [open items](../../spec/sqlite-project-v1.md#open-items) ask the lead to
  state its *derived* rows to the owner as inform, at the latest before S08
  sealed. No record of that statement exists in the repository. Owner: the
  lead, at the latest before the `0.2.2` release commit, which releases
  these rows; once stated, a decision row records it, as D79.12 did for
  Phase79's.
- **The cProfile half of the ten-slowest profile** ([below](#b2-acquisition-review)).

## Route items due at S16

- **Dependencies.** R1 `a47a5713` passed; S12 `dd7e3b5f` is published;
  the third whole-tree test pass ran in batch 2 as M11 `269fede5`,
  published at `851ad83f` with natural CI `43814266697`, and meets that
  condition of Phase78's closure (PL.49; the route's B1 closure). All three
  are met.
- **Midpoint.** Written after the fact in the [B2 record](route.md#b2-record);
  lesson 78-1.
- **Fragments.** S16 compared both fragments with the specification and
  the code: each detail word and limit they name appears in all three, and
  no rule differs. Their known limitations stand: R1 found no difference
  beyond the zero sign and the `avg` summation that the specification's
  differences table, the language guide and the 1a fragment's `avg` line
  state, and S12's facts are already in the 1b fragment. Neither fragment
  changes.
- **Specification.** Its construction state now reads that the first tier
  is qualified. Its open items keep only the derived rows, with the latest
  point [above](#not-verified); the fragment comparison is the item above
  and the extension sync the next, so S16 removed both.
- **Extension sync (D76.12).** No B2 commit changes `grammar/Pietto.g4`,
  `src/pietto/semantic/catalog.py`, `aggregates.py`, `window_semantics.py`
  or an example, and the `pietto` blocks of `README.md`,
  `docs/language.md`, `docs/style.md` and `docs/worked-example.md` are
  byte for byte the same at `489108bc`, `a6c89521` and `a47a5713`. B2 needs
  no sync patch, and no extension push is authorized.
- **Goldens.** S08's write set named new goldens; none was added. Project
  bytes are pinned in `tests/test_sql_sqlite_project_emission.py` and in
  the native cells' prewritten oracles, and the single-file golden changed
  only for the `Bool` literals (PL.54 (1)).
- **AD78.03.** The PostgreSQL/MySQL pipeline never receives `sqlite`: the
  firewall in `tests/test_repo_static_checks.py` writes each adapter
  family's own connector, and a test there holds the adapter's imports to
  its whitelist. Both Gate 2 runs ran them.

## Earlier audits read

- **Phase79 B1** ([audit](../phase-79/completion-audit.md#phase78-handoff)).
  Its order item is met (PL.32). Its seam item asked SQLite B2's Gate 1 to
  generalize the firewall or build its own pipeline: PL.47 chose a separate
  adapter, S07 changed the shared lines in one commit, and the firewall
  lists both families. Its reading item is this section.
- **Phase79 B2** ([audit](../phase-79/b2-completion-audit.md)). T08 wrote
  the shared pages before S16, as the order of the two pushes put it, and
  S16 builds on a tree that carries T08. It hands nothing to Phase78;
  Phase79 stays open until DuckDB's second tier is done (PL.57).
- **Phase80** ([audit](../phase-80/completion-audit.md#lessons)). B2's
  route consumed 80-2 (S11's tests are gated by entry point and platform,
  and the Windows jobs now run the route's file), 80-3 (admission before
  binding), 80-4 (S07's seam in one commit) and 80-5, which B2 missed: its
  midpoint record is written here. Its handoff names no Phase78 item.
- **Phase77**, read again ([audit](../phase-77/completion-audit.md#next-phase-handoff)).
  B1 published after DuckDB B1, and the fragments reached `main` only after
  `0.1.12`. The `verify_project_sql_plan` debt passes to the next phase
  that changes project SQL emission: B2 changes no PostgreSQL or MySQL
  project SQL, and the SQLite adapter's modules do not name that function,
  so the debt stays with Phase81 (PL.40 D15 A). Its owed ten-node profile
  is still owed, beside Phase78's.

## B2 acquisition review

Base: B2's own commits against their parents, `489108bc..a6c89521` for the
first batch's B2 commits and `6a0646b4..a47a5713` for R1, under the
[phase-end acquisition consolidation](../../development.md#phase-end-acquisition-consolidation);
the record commits of that batch change no test.

- **New.** The owners `tests/test_sql_sqlite_project_emission.py` (15
  test functions, 43 nodes) and `tests/test_execution_api_sqlite_file.py`
  (31 functions, 80 nodes); the shared helper `tests/_pietto_sql_sqlite.py`
  (the project, its contract, the SQLite class and the route's judge),
  read by both, the native module, `tests/test_sql_compile_api.py` and
  the harness self-test; the fixture `tests/fixtures/sqlite/postgres_replay_r1.json`.
- **Changed.** `tests/test_sql_sqlite_native.py` (12 to 15 test functions,
  1,186 lines added and 192 removed, R1's included),
  `tests/test_sql_sqlite_emission.py`, the firewall and whitelist in
  `tests/test_repo_static_checks.py`, `tests/test_semantic_source_connectors.py`,
  `tests/test_plan_target_profiles.py`, `tests/test_cli_project_emit_sql.py`,
  `tests/test_sql_compile_api.py`, `tests/test_execution_api_errors.py`,
  `tests/test_harness_execution_api.py`, `tests/test_ci_workflow.py`, three
  one-line edits (`tests/test_execution_api_postgres_rows.py`,
  `tests/test_execution_api_queries.py` and
  `tests/test_sql_mysql_connector_semantic_surface.py`), the `conftest.py`
  docstring, the single-file goldens and two lines of
  `scripts/package_smoke.py`.

Timings are those of S16's run above (summed per file): the native module
342 nodes in 11.06 s, the route's file 80 in 6.78 s, single-file emission
40 in 2.46 s, project emission 43 in 1.50 s and the plan profiles 82 in
3.96 s. The slowest nodes were R1's replay test (6.37 s), B1's
`test_the_cli_alone_dispatches_the_sqlite_backend` (2.22 s), the plan
profile's `sqlite.table` case (1.13 s, beside 1.19 s for `duckdb.arrow`)
and the route's result-binding cell (0.85 s).

Classified:

- **Shared, kept.** The native module's `project_emit` fixture emits each
  project program once per contract and worker module, and the project
  cells and the coverage law read it; the build is observed once per module
  (D78.03).
- **Repeated across CI shards: debt.** CI places
  `tests/test_sql_sqlite_native.py` over three shards (114, 114 and 113
  nodes in `44006845752`), so each shard's memo holds about a third of the
  project emissions, and the coverage law, which reads them all, emits the
  rest again: 9.5 s on Python 3.13 in that run, against 0.32 s with the
  file on one worker. Placing the file whole, as M13 of PL.49 allows, is a
  placement change of `ci/workloads.toml` that needs its own review and is
  outside S16's write set. About 9 s of one shard is low value. Owner: the
  lead, at the next reviewed placement change (lesson 78-7).
- **Fresh by design.** R1's replay test emits each project cell's program
  through the PostgreSQL pipeline, another backend from the memo's, as B1
  kept its replay test. Each route cell builds its own file under the
  pytest base temporary directory and opens its own connection per attempt,
  which is what it tests; the lock and deadline cells wait in real time.
  The plan profile's `sqlite.table` case compiles its own project, as its
  `duckdb.arrow` neighbour does. The whitelist test parses only the
  adapter's own modules.
- **B1's fresh parse.** `test_the_cli_alone_dispatches_the_sqlite_backend`
  still parses every `src/pietto/**/*.py` itself (6.5 s on Python 3.13 and
  11.9 s on 3.12 in CI); S11 added `execution/_sqlite.py` to its importers.
  B1's reason stands, since `tests/_pietto_repo_facts.py` does not resolve
  relative imports, and its debt stays the lead's, at the next whole-tree
  test pass.

Structural improvement: none; wall-time improvement: none claimed; no-gain:
the cross-shard re-emission and the replay's PostgreSQL front end above.

**Ten-slowest profile.** From the health of `44006845752`, Python 3.13,
which records 126 slowest nodes. Ranked by setup, call and teardown, 13
nodes above the tenth in-process one spend their time in child processes,
of the kinds the [B1 review](route.md#b1-acquisition-review) lists, and
`test_the_duckdb_native_checker_accepts_honest_units_and_refuses_each_fabricated_shape`
(51.8 s) stays set apart, as there. The ten in-process ones:

| Node | Job | 3.13 s | 3.12 s |
| --- | --- | ---: | ---: |
| `test_harness_sql_emission_portability.py::test_every_admitted_artifact_exports_corresponds_and_decodes[postgres]` and `[mysql]` | Runtime 3.13 / shared-acquisition | 121.8, 112.9 | 116.5, 104.2 |
| `test_harness_target_conformance.py::test_data_only_receipt_controls_have_nonempty_positive_denominators[postgres]` (setup 101.8 s, the `valid_receipts` fixture) | Runtime 3.13 / general-runtime-1 | 104.9 | 143.1 |
| `test_repo_reader_acquisition.py::test_shared_facts_match_legacy_text_ast_import_and_identifier_acquisition` | Runtime 3.13 / general-runtime-1 | 29.4 | 43.3 |
| `test_repo_test_layout.py::test_no_test_reads_the_mutable_status_or_roadmap` | Runtime 3.13 / general-runtime-2 | 29.2 | 31.3 |
| `test_harness_target_conformance.py::test_empty_text_anchor_requires_the_observed_var_string_type` | Runtime 3.13 / general-runtime-1 | 27.6 | 38.5 |
| `test_semantic_capability_facts.py::test_private_module_has_only_authorized_window_strategy_compiler_consumer` | Runtime 3.13 / general-runtime-2 | 23.8 | 24.4 |
| `test_project_r2_proposal.py::test_r2_refuses_a_paired_mysql_form_before_any_workspace` | Runtime 3.13 / general-runtime-2 | 23.2 | 26.7 |
| `test_execution_compiled_bundle.py::test_mysql_lpad_and_now_cells_are_derived_in_linear_work[words-_chained_lets]` | Runtime 3.13 / general-runtime-1 | 21.5 | 27.9 |
| `test_sql_project_scalar_expressions.py::test_q1_scalar_surface_is_verified_through_both_project_targets[mysql]` | Runtime 3.13 / general-runtime-2 | 21.3 | 23.6 |

None is a Phase78 node. The `valid_receipts` fixture is now built in one
shard (M13 of PL.49), where B1's profile saw it in three. The Phase78 nodes
in the recorded lists are the coverage law (9.5 s, 3.13 only), B1's CLI
dispatch test (6.5 s and 11.9 s) and the plan profile's `sqlite.table` case
(4.8 s and 6.9 s). The cProfile half of step 4 is NOT_OBSERVED: S16's
pytest starts run at the lowest priority with four workers on a host that
other lanes share, which is not the quiet host the step names, so none of
the ten ran alone under cProfile and no performance claim rests on the
table. The table reads `44006845752`, the newest natural CI when S16 ran,
not this batch's: a documentation commit after this batch is published,
before the `0.2.2` release commit, reads the health of the batch's natural
CI and redoes the table.
The cProfile half is the lead's, at the latest before the `0.2.2` release
commit, together with the profile Phase77's audit still owes; if no quiet
host runs it by then, it is recorded here as NOT_OBSERVED with the reason.
Health is advisory, and nothing here changes scheduling, topology or test
selection.

## CI health

S16 read the health of `44006845752`, the natural exact-head CI of
`6a0646b4`, the newest published head, through the owner's read-only token
(PL.07), with GET requests only, on 2026-11-17 from 06:15:18Z to 06:15:33Z.
The run, push/main attempt 1, ran from 02:58:41Z to 03:17:33Z and passed
all 21 jobs, which took 11,061 s in all (jobs API, start to completion);
the longest was Windows 3.12 at 1,125 s. Its 15 `ci-health` artifacts
match the digests, sizes and head that the API lists, the workflow summary
passes `verify_workflow_health` of that head's `scripts/ci_workloads.py`,
and the aggregate job's `[ci-health]` lines agree. Each Python collected
31,423 nodes.

The status is INSUFFICIENT_EVIDENCE with a WATCH screen. History read 4
candidates and accepted 3, `43946002245` (`31859bc6`), `43902311675`
(`64a7f885`) and `43888270979` (`107df991`), each a natural successful
attempt 1 on `main`, with none rejected and none comparable: each differs
in runner images and test set (29 more nodes than `31859bc6`). Of 24
signals, the structural `FEWER_UNITS_THAN_WORKERS` (plan- and
emission-portability, 3 nodes on 4 workers, both Pythons) predates B2; the
provisional ones are `SHARD_IMBALANCE_REVIEW` for the runtime on both
Pythons and `LONG_INDIVISIBLE_NODE` 18 times. The health's cost is
incomplete, as always, since it is written before Windows 3.12 and the
aggregate job finish. Health is advisory and holds nothing.

## Gate 2 durations

The two most recent Gate 2 runs, each on the integration host with
`scripts/validate.py` under 20 workers and the qualified SQLite class:

| Batch | Tree | Run (UTC) | `validate.py` | pytest | Tests | Beside it |
| --- | --- | --- | ---: | ---: | --- | --- |
| S06–S12 | `8e8a9fba` | 2026-11-16, 19:51:43Z to 20:01:11Z | 541.2 s | 488.12 s | 31,254 passed, 140 skipped | package smoke passed; the route's file with the `arrow` extra, 80 passed, none skipped; the DuckDB extra start, 166 passed |
| Pure repair | `feeb6b93` | 2026-11-17, 02:46:01Z to 02:55:25Z | 535.2 s | 485.01 s | 31,283 passed, 140 skipped | the same three, with the same counts |

Each sealed its tree unchanged and is the Gate 2 line of its batch's last
commit. The Arrow-free core counts the route's native cells with the
`PIETTO_NOT_RUN sqlite-native ARROW` line; its log lists no skip reasons.
The Gate 2 of R1 and S16 runs once on this batch's final tree after this
commit; a documentation commit after publication, before the `0.2.2`
release commit, records it here.

## Budget and failures

P78B2's ceiling is `C160/F480/D6,000/S8` (PL.47), under PL.15. By the
lead's ledger through R1, at 06:30Z on 2026-11-17, B2 had used at most C19,
F115, D3,248 and S1, 54% of D; no figure reached 80%, so PL.15 raised none.
S16's own costs and the second batch's Gate 2 follow on the ledger, which
P78B2 closes with S16 (owner: the lead, outside Git). B1's ledger closed
with B1 (the [B1 record](route.md#b1-acquisition-review)).

Failures are kept, never rerun as replacements, by the lead's ledger and
records: S05's first attempt and the first B2 round, both stopped; S10's
review, NEEDS_CHANGES on the `Bool` literals that PL.54 (1) answered; the
real bugs fixed before delivery in S08–S12 (among them a `-journal` FIFO
that hung the route, a 0-byte database whose `-wal` file SQLite deleted,
and the integrity check computing a file's expressions); the first batch's
Gate 2 contradiction, root-fixed with the counted ARROW line before that
Gate 2; R1's first lane, which stopped before any freeze (PL.56): Docker
Desktop's Engine was running, but the lane's client failed with an
input/output error from Docker Desktop's CLI mount, and a boot-time rule of
the host's podman-docker package had linked `/var/run/docker.sock` and
`/run/docker.sock` to podman's socket (the lead's record of 2026-11-16,
14:50Z); and R1's first package, whose review found two medium and eleven
low issues before a revised package ran.

## Lessons

The [engineering lessons](../../references/engineering-lessons.md#phase78)
hold them: a midpoint is a stop the dispatch encodes; know what a
library's check runs on untrusted input; a size cap bounds the measured
shape and the deadline bounds time; give a keyword that the target can
read as a name a cell beside that name; a read-only claim names the files
it touches; decide where a class that needs an extra runs without skips; a
module memo does not cross CI shards; and the engine path is a fact of
each boot.

## Phase82 inputs

The [freeze ledger](../../roadmap.md#phase82-freeze-ledger)'s SQLite row
now covers project mode and the `sqlite_file` route beside single files:
the project dialect and contract target, the compile refusals and their
order, the first tier's SQL spellings, the route's request, defences,
limits, side files and detail words, and the support matrix of one build
on Linux x86-64 under CPython 3.13.13 and 3.12.13. The surfaces stay alpha
until the freeze rules on them.

## Handoff

- **Second tier.** SQLite's second tier (S13 JOINs, S14 range-proved `Int`
  arithmetic and S15 windows) goes to the owner's plan (PL.54 (2)) and
  comes before the Phase82 freeze, with its own Gate 1 and ledger; the
  cutoff for admitting it is Phase82's Gate 1 (PL.58 (4)), and the decision
  on the freeze ledger's JOIN key and grain row comes before any slice that
  opens a JOIN. Reminder 8 stays met by exclusion: the first tier opens no
  JOIN and refuses bundles. Unclaimed items are unsupported at the freeze.
- **Next phase.** Phase81 waits for the owner's next revision of the draft
  plan, r17, and the lead does not start it (PL.58); its commits reach
  `main` only after the `0.2.2` release commit (PL.57).
- **`0.2.2`.** It waits for this batch and the rest of PL.55's scope; the
  owner authorized its publication once its gates pass (PL.56). Its
  release commit assembles `78-s06` and `78-s11` and lists the single-file
  `Bool` literals as an incompatible change (PL.54).
- **Deferred owners.** As the route's [B2 deferred owners](route.md#b2-deferred-owners)
  and the roadmap's deferred subjects name them.
- **Debts.** The derived-rows inform and the cProfile half of the profile,
  both before the `0.2.2` release commit; the ten-slowest table from this
  batch's natural CI, in a documentation commit after it and before the
  `0.2.2` release commit; the coverage law's cross-shard re-emission; and
  B1's fresh parse. The Gate 2 and natural CI of this batch are recorded
  here after publication, by the same point.
