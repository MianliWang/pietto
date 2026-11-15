# Phase79 B1 completion audit

Phase79 B1 implements the limited DuckDB path of its [route](route.md): one
local, read-only query over one Arrow table that the caller supplies,
compiled for DuckDB `2.0.0` and run in process
([DuckDB Arrow route](../../spec/duckdb-arrow-route-v1.md)). Its decisions
are D79.01–D79.16, AD79.01, the third-dialect seam AD78.03 and the shared
PL rows that the route cites, in the [decision record](../../decisions.md). B1 is one
vertical: this audit closes B1, not Phase79. It records delivery,
qualification and the acquisition review, and hands over to Phase78 and to
a Phase79 B2. The batch that publishes S08 determines B1's completion
through its Gate 2 seal and natural exact-head CI; this document does not
certify its own publication. The first documentation commit after that
batch was published records the batch's facts here.

## Baseline and publication boundary

Gate 0 is bound to `ab972f362c433b234a74f542c5d274d22c8cdeae` (tree
`821be1ccf7bb6f3e14b8d00d80f1f30d3cc087fe`) with natural CI `42831340276`
(PL.02). The lane worked on `ab972f36`; the chain was integrated onto
`a015afcf` on 2026-11-13 and, after `0.1.12` was published, replayed onto
`ab594829` on 2026-11-14 in the same order, one commit per slice. B1 has one
release-note fragment, `79-s01-duckdb-arrow-route.md`, which S01's commit
adds; each later slice checks its own lines there and adds no second
fragment (the specification's open items), and on the replayed chain only
S08 changes it; the first documentation commit after the push changes it
once more. Phase77 closed with `0.1.12`, so the replay carried every
Phase77 slice. The route's Gate 0 has the Phase77 overlap measured again on
the published head; B1 did not measure it, so it is NOT_RECORDED. This
departs from the route: Phase77 had closed before the replay, so no
unpublished Phase77 write set was left to overlap, and the replay compared
each slice's changed lines on the published tree instead. Owner: the lead;
this paragraph is the record of the omission, and the first push's Gate 2
sealed the tree that carries it.

On the replayed candidate chain, B1 is PK `0dd333e4` (S05, shared with
Phase80), S01 `97c1377e`, S02 `3d25e016`, S03 `134a566b`, S04 `57ba2d79`,
S07 `471e4915`, the midpoint record `1029dd74` and S04's result-reader
wiring `cf460bda`. The wiring followed the `0.1.12` publication (D77.32),
as the owner's answer D77.83 (c) has it, and D77.83 (b) retires as moot
PL.04's midpoint clause, the step of bringing option C back that the
midpoint record did not carry out.
Phase78's SQLite B1 commits `c9b96365` to `faa46a2a` lie above S07 and below
the midpoint record. At that replay S06 had no commit on the chain. By
the lead's rulings of 2026-11-13 it seals as a fresh commit, and its
commit goes below S07, which depends on it, with S07 replayed on top
(2026-11-13T19:02Z). S06 had
not sealed at the replay of 2026-11-14, so S07 still has no S06 below it.
The owner's answer on the order (PL.32; see the Phase78 handoff)
supersedes that ruling: S06 and S08 go on top of the chain, above the
Phase77 follow-ups `04a74539` and `01c3b7f4`, and the whole chain
publishes in one fast-forward push. S06 sealed on 2026-11-14 as `ff74023e`
on `cf460bda` and was restacked unchanged, with the same patch, as
`1abbc7d5`; D77.50 carries its run there, and that commit's message
records the comparison. The B1 commits of the batch are the eight above,
in that order, and S06 `1abbc7d5`. The owner's answers
and the lead's rulings for `0.2.0` (PL.30–PL.34, D79.16) are the commit
`0c645606` between S06 and S08, and S08 is the commit that adds this
audit. The batch, 23 commits on `ab594829`, was fast-forward pushed
under PL.31 on 2026-11-14 at 21:54:54Z and ends at S08,
`94b4097a5ec3e1fa5936e352d5b63bf84ec4d688` (tree
`58f5e2810fe016c63def144a8eec81e1389c6248`). Its Gate 2 and batch audit
are below; its natural exact-head CI,
[`43645308189`](https://github.com/MianliWang/pietto/actions/runs/43645308189),
push/main attempt 1, passed all 21 jobs. Interior batch commits take the
batch head's result.

## Accepted scope

| Slice | Delivered |
| --- | --- |
| S00 | The package evidence: the PyPI fetch and install probe of 2026-11-10 (PL.05) and the offline cells in the probe's environment, recorded at the midpoint. No repository change. |
| S01 | The alpha specification, revised by S04 with the owner's later answers (D79.13–D79.15), and B1's only release-note fragment, `79-s01-duckdb-arrow-route.md`. |
| S02 | The `duckdb.arrow` connector of explicit-module projects, the `duckdb` project dialect and the family firewall of AD78.03, which lists `duckdb` and `sqlite`. |
| S03 | The independent adapter, `src/pietto/_project/project_duckdb_*.py`, with its own SQL AST, renderer and artifact verifier, and the plan's admission of `duckdb.arrow`. |
| S04 | `execute(route="duckdb_arrow")`, `DuckDBArrowInput`, the owned capture, the hardened session, the attempt's lifecycle and the DuckDB storage kinds, wired into the shared result readers on 2026-11-14 (D77.83 (c)). |
| S05 | The `execute-duckdb` extra and its installed cells, in the PK commit. |
| S06 | The native qualification (D79.07): attempt `s06-20261114T164751Z` of preregistration v5 judged U0, U1, U2 and U3 each ACCEPTED on its first attempt on 2026-11-14, on `cf460bda`'s tree, with no void and no rerun; D77.50 carries the run to `1abbc7d5`. |
| S07 | One real DuckDB Arrow query in the `arrow-ready` cell of natural CI. |
| S08 | The shared pages (below), the freeze-ledger rows, this audit and the B1 acquisition review; the specification is left unchanged until the batch is published (below). |

S08 applied the specification's shared-page hunks, one page at a time:
`docs/spec/diagnostics.md` (the `PIE-S2306`, `PIE-B1001`, `PIE-B1003`,
`PIE-R1001`, `PIE-R1002`, `PIE-R1004`, `PIE-R2002` and `PIE-R2006` rows),
`docs/execution.md` (a DuckDB Arrow route section, the support-matrix and
install rows, and the `duckdb_arrow` clauses of the `execute()` entry and the
errors section), `docs/project-package.md` (the dialect and the DuckDB
columns of the contract tables), `docs/language.md` (the connector),
`docs/capabilities.md` (the [DuckDB local path](../../capabilities.md#duckdb-local-path),
each row run once through `check --project` and `emit-sql --project
--dialect duckdb` on the tree of S08's first draft) and
`docs/spec/project-cli-json-v2.md` (the `duckdb` dialect value), which the
specification's hunk list names beside the route's write set. By the
lead's ruling of 2026-11-13 the 64-field width statement of
`docs/execution.md` and the `PIE-R1004` row now name only the PostgreSQL
and MySQL routes.

S08 leaves `docs/spec/duckdb-arrow-route-v1.md` unchanged. S06's frozen
preregistration binds it by its sha256 (`b5559597…`, the route's midpoint
record), its checker refuses a run whose tree holds another specification,
and D77.50 carries S06's native run to the batch head only while the
experiment documents stay byte-identical. The specification's construction
state, which said PLANNED, and its open items, which the deferrals below
settle, were therefore updated only in the first documentation commit after
the batch that carries S06 was published: the construction state now says
B1 is published, the catalog item records D79.16, and the inform and
fragment items are closed. S06's frozen preregistration v5 binds the page
as it was before that commit (`SPEC_SHA256` in
`tests/_pietto_execution_duckdb_native_oracle.py`, `b5559597…`), so a
rerun of S06's native qualification on `main` after it is refused by the
checker for its spec digest and needs a new preregistration. S06's
accepted run stays bound to `cf460bda`'s tree and, under D77.50, to the
batch head. A Gate 2 is unaffected: the harness self-test checks only that
constant.

## Acceptance layers

**Observable.** The specification, the fragment, the capability rows and
the shared pages state each admitted form, refusal and limit. The fragment
now links the capability subsection and the execution section, and states
that the width refusal stays with the PostgreSQL and MySQL routes.

**Existing.** No Phase79 commit touches `tests/fixtures/golden/`. At the
midpoint, on `85577f75`, `scripts/check_goldens.py` verified 43 fixtures
and the firewall's three nodes passed. On the batch tree, which holds 43
golden fixtures (Phase78's two `emit_sqlite_single_file` goldens are the
only ones the chain adds since `ab594829`), the batch Gate 2 passed every
golden owner with no failure: among them
`tests/test_release_golden_policy.py`, whose run of
`scripts/check_goldens.py` on the tree asserts 43 fixtures verified (35 SQL
byte-exact, 8 JSON structural, none missing or orphaned), and the firewall
of `tests/test_repo_static_checks.py`.
B1 changes no PostgreSQL or MySQL SQL bytes or contracts, and no
diagnostic of theirs except the refusal of a project `duckdb.arrow`
source, which `0.1.12` refused at `check` with PIE-S2306 and which now
checks, while its PostgreSQL and MySQL emission refuses it with
PIE-B1001 beside PIE-B1006; single files keep their output for
`duckdb.arrow`.

**Connected.** The native matrix runs in process on the integration host
against `duckdb` `2.0.0` and `pyarrow` `26.0.1`, with no Docker and no engine
lock (D79.07); every unit was accepted on its first attempt (S06 above).
Natural CI runs one real query in the `arrow-ready` cell on CPython 3.12
and 3.13 (S07); the batch head's run,
[`43645308189`](https://github.com/MianliWang/pietto/actions/runs/43645308189),
push/main attempt 1, passed all 21 jobs.
The batch Gate 2 also runs `tests/test_sql_duckdb_emission.py` and
`tests/test_execution_api_duckdb_arrow.py` in an `execute-duckdb`
environment, recorded as one extra pytest start (the lead's ruling of
2026-11-13).

## Compiled compatibility

`VERSIONS` is unchanged and no compiled record changed. `export_bundle`
refuses a DuckDB query (`PIE-R1004` `DUCKDB_BUNDLE_ENTRY`), and saved
results, relay and jobs do not take the route, so B1 adds nothing to migrate.
After a pin upgrade an old DuckDB contract is BLOCKED with `PIE-B1003`
`target_release_not_reviewed`.

## Route deferrals due at B1

- **NUL in `Text`** (D79.13), due before the batch Gate 2: S04's
  `test_a_nul_in_text_reaches_duckdb_and_the_caller_unchanged` and S06's
  frozen cell C14, whose table carries texts with NUL at the start, middle
  and end, cover it; C14 was accepted in U1, U2 and U3.
- **Result-reader wiring:** done on 2026-11-14 in `cf460bda` (D77.32,
  D77.83 (c)).
- **Informs:** the D79.01 refusal mapping, the D79.04 `-0.0` admission and
  AD79.01 were stated to the owner on 2026-11-11, before S01 bound and S04
  sealed, and stand with the specification's derived items (D79.12). This
  settles the specification's inform row.
- **Extension sync** (D76.12), due before the batch push, read as Phase78
  B1 read `sqlite.table` (its acceptance item 16): the extension's language
  sync test reads the keywords of `grammar/Pietto.g4`, the
  built-in names of `src/pietto/semantic/catalog.py`, `aggregates.py` and
  `window_semantics.py`, and the `pietto` blocks of `README.md`,
  `docs/language.md`, `docs/style.md`, `docs/worked-example.md` and every
  `examples/**/*.pietto` file. No B1 commit changes the grammar, those
  modules or an example, and S08's text in `docs/language.md` adds no
  `pietto` block, so `duckdb.arrow` is no catalog change, B1 needs no sync
  patch and the extension's corpus is unchanged. The lead's ruling is
  D79.16; no extension push is authorized.
- **Fragment:** the specification's fragment row closes with the batch
  audit's comparison of the fragment with the specification. The audit
  found the fragment's links resolvable and one low: its sentence that
  PostgreSQL and MySQL SQL bytes, contracts and diagnostics are unchanged
  could read, in the assembled `0.2.0` notes, as if no part of the release
  changed them, while the Phase77 follow-ups below add a PostgreSQL R2
  refusal. The first documentation commit after the batch was published
  scopes it to this route.

## B1 acquisition review

Base: `ab594829`, onto which the chain was replayed (`a015afcf` before it,
with the same test changes above it). B1 adds two owners,
`tests/test_sql_duckdb_emission.py` (20 tests) and
`tests/test_execution_api_duckdb_arrow.py` (28 tests), and two helpers,
`tests/_pietto_sql_duckdb.py` and `tests/_pietto_execution_duckdb.py`, and
changes 15 existing test files: PK's `tests/test_release_installation.py`
and three helpers, S02's six connector, dialect, `fmt` and firewall owners,
which S03 also edits, S03's plan, compile-API and R2 owners, and S04's
error and optional-Arrow owners. In all, these 19 files take 23 changes,
one per commit and file, which add 3,157 lines and remove 24. PK's part,
`tests/test_release_installation.py` and its three helpers (199 lines
added, 2 removed), is shared with Phase80; this count includes it once, so
a Phase80 count that includes it covers the same lines. The three helpers
only extend constant tables (the extras' requirements, the expected wheel
metadata and the origin's extras). Their direct existing consumers,
checked here, compare against those tables and acquire nothing new:
`tests/_pietto_execution_installation_probe.py`,
`tests/_pietto_execution_matrix_check.py` and
`tests/test_execution_compatibility.py` read
`_pietto_execution_installation_check`;
`tests/_pietto_repo_arrow.py`, `tests/test_results_optional_arrow.py`,
`tests/test_release_packaging_smoke.py` and
`tests/test_execution_compatibility.py` read `_pietto_repo_package`; and
`tests/_pietto_results_product.py`, `tests/_pietto_execution_matrix_probe.py`,
`tests/test_results_consumer.py` and `scripts/phase68_executor_premise.py`
read `_pietto_results_consumer`. S07 changes no test. S06, counted apart
from these, adds the four frozen helpers
`tests/_pietto_execution_duckdb_native_*.py` (3,673 lines), which are the
preregistered experiment's bytes and acquire nothing that an owner reads,
and a 34-line harness self-test in the existing owner
`tests/test_harness_execution_api.py`; it adds no owner. The self-test
keeps its fresh interpreter, since only a fresh process shows that the
oracle runs without DuckDB.

Timings are the per-test times of the midpoint's first pytest output
(`-n 8`, 2026-11-13T17:42:55Z), one median `compile_query` measurement on
the S08 tree (0.050 to 0.060 s under a load near 20), and the S08 focused
pytest start (2026-11-14T16:43:35Z, `-n 8 --dist=loadfile`, nine files in
an `execute-duckdb` environment: 505 passed, none skipped; the execution
module's 29 nodes summed 15.98 s). Gate 2 distributes by file
(`--dist=loadfile`), so a module fixture is built once per run.

Consolidated, with equal assertions:

- `tests/test_execution_api_duckdb_arrow.py`: 19 compiles of the two B1
  queries (13 tests of the projection, 6 of the filtered query) now read two
  module fixtures, `filtered_query` and `projection_query`; a
  `CompiledQuery` is an immutable snapshot that `execute()` binds afresh.
  About 17 compiles fewer per run, about 0.9 s on the file's worker.
- `tests/test_sql_duckdb_emission.py`: the VERIFIED emission that the six
  forgeries and the `compile_query` cell read is one module fixture,
  `verified`; a forgery replaces the artifact and never changes it. Six
  emissions fewer per run.
- `tests/test_plan_target_profiles.py`: the pure-boundary cell of a
  `duckdb.arrow` source builds its project record once and assesses it for
  the three families, instead of three parametrized nodes that built the
  same record (0.448 to 0.541 s each at the midpoint); an assessment
  asserts that it leaves its record unchanged. Two record builds fewer.
- The adapter's import scan in `tests/test_sql_duckdb_emission.py` reads
  `REPOSITORY_FACTS.python(path).imported_modules` of the existing owner
  `tests/_pietto_repo_facts.py` in place of its own `ast` walk. Both take
  every `import` name and every `from` module; a module-less `from . import
  x` gave the walk an empty name and gives the owner none, and neither is
  banned. Structural only: the walk took milliseconds.

Kept fresh, each with its reason:

- The three child interpreters of the execution module (checks 1–8 import
  nothing, checks 9–13 import no DuckDB, a shadowing `_duckdb` on the path)
  and the adapter's child: absence of an import is observable only in a
  fresh process.
- The cell that forges the compiled template in place
  (`test_check_seven_refuses_a_forged_template_and_another_code_identity`)
  compiles its own query, and the cells of distinct bodies or contracts
  (the six operators, the NUL query, the out-of-range `Int`) compile theirs.
- Each attempt opens its own `:memory:` session, which is the property
  under test (nothing is pooled); the cancel and deadline cells keep their
  real threads and the 30 s watchdog bound.
- The firewall drives every entry per dialect, contract and output on the
  integrated tree, as AD78.03 asks at every replay; its inputs differ.
- The other emission cells read distinct inputs at about 0.04 s each (the
  module's 63 nodes summed 4.23 s at the midpoint); S02's connector cells
  use in-process `tmp_path` projects (0.96 s for 100 nodes).
- PK's installed wheel and sdist cells are independent install witnesses of
  package smoke.

Structural improvement: one existing-owner reuse, three module fixtures and
one record shared across families. Wall-time improvement: about 1.2 s of
worker time per run, estimated from the operation counts and the measured
compile time; no before-and-after run was made. The S08 run shows the
emission module at 3.69 s summed (4.23 s at the midpoint) and the shared
plan cell at 1.41 s (1.515 s for its three nodes at the midpoint), under
other loads and trees, so no measured gain is claimed: the record build
was not the plan cell's main cost. The bounded ten-slowest profile of
step 4 reads the final natural CI health after publication:
natural exact-head CI
[`43645308189`](https://github.com/MianliWang/pietto/actions/runs/43645308189)
of `94b4097a`, push/main attempt 1, ran from 21:54:59Z to 22:14:04Z on
2026-11-14 (1,145 s) and passed all 21 jobs, which took 11,094 s in all
(jobs API, start to completion, without queueing); the longest was
Windows 3.12 at 1,132 s. Its health was read at 22:15Z through the owner's
read-only token (PL.07): the 15 `ci-health` artifacts match the digests
the API lists, the workflow summary passes `verify_workflow_health` of
that head's `scripts/ci_workloads.py`, and the `[ci-health]` lines of the
aggregate job's log agree. The status is INSUFFICIENT_EVIDENCE with a
WATCH screen. History read 4 candidates and accepted 3 (`43603167533`,
`43600539878`, `43590596831`) with none rejected, but none is comparable:
each differs in its test set (345 more nodes now) and in the runner
images of its shards.
Each Python collected 30,844 nodes; 30,795 passed and 49 were skipped. The
only alert that needs no history is the structural
`FEWER_UNITS_THAN_WORKERS` that predates Gate 0 (plan- and
emission-portability, 3 nodes on 4 workers, on both Pythons). The
provisional ones are `SHARD_IMBALANCE_REVIEW` on both Pythons (longest
over median 1.54 on 3.12 and 1.82 on 3.13, general-runtime-1 the longest
each time) and `LONG_INDIVISIBLE_NODE` 18 times, the same nine
child-process nodes on each Python as in the Gate 0 run. Both comparisons
with Gate 0 rest on the editor core's midpoint read of the Gate 0 run
`42831340276` on 2026-11-11 (E-C route,
[midpoint](../../editor/ed03-route.md#midpoint-unfreeze-and-closure)), not
on a read at Gate 0; this package did not read that run's health. There is
no finish-spread, startup, cost or repeat signal; the health's own cost is
partial, as always, because it is written before Windows 3.12 and the
aggregate job finish. The general-runtime shards that ran on runner image
`20261111.370.1` (all three on 3.12, general-runtime-1 on 3.13) took 878
to 1,029 s, and the two on `20261111.127.1` took 531 to 538 s; the cause
is not established.

The Python 3.13 health records 126 slowest nodes: 30 for each of the
shared-acquisition and three general-runtime partitions and 3 for each
portability partition. Ranked by setup, call and teardown time, 15 nodes
above the tenth in-process one were left out because their time is spent
in child processes, of the same kinds and number as in the E-C profile:
the differential process cells of `test_harness_ir_differential.py`,
`test_harness_plan_conformance.py` (its setup is that acquisition),
`test_harness_plan_portability.py` and
`test_harness_sql_emission_portability.py`; the six checkout, relocated
and installed standalone batches of the two portability files; the two
fresh source-free processes of `test_execution_compiled_source_free.py`;
and three nodes of `test_harness_execution_api.py` whose module fixture
starts a fresh `-I` worker for each consumer case. One more is set apart:
`test_harness_execution_api.py::test_the_duckdb_native_checker_accepts_honest_units_and_refuses_each_fabricated_shape`
(23.8 s, Runtime 3.13 / general-runtime-3), new with Phase79 S06, starts
one fresh `-I` oracle interpreter and then checks in process; its split
between the two is not observed.

| Node | Job | 3.13 s | 3.12 s | Where the time is |
| --- | --- | ---: | ---: | --- |
| `test_harness_target_conformance.py::test_data_only_receipt_controls_have_nonempty_positive_denominators[mysql]` | Runtime 3.13 / general-runtime-1 | 182.2 | 208.9 | setup, 178.1 s: the module fixture `valid_receipts` |
| `test_harness_target_conformance.py::test_receipt_corruption_is_rejected_without_any_resource[postgres-missing]` | Runtime 3.13 / general-runtime-3 | 113.0 | 197.7 | setup, 110.4 s: the same fixture |
| `test_harness_target_conformance.py::test_data_only_receipt_controls_have_nonempty_positive_denominators[postgres]` | Runtime 3.13 / general-runtime-2 | 111.8 | 195.4 | setup, 108.7 s: the same fixture |
| `test_harness_sql_emission_portability.py::test_every_admitted_artifact_exports_corresponds_and_decodes[postgres]` | Runtime 3.13 / shared-acquisition | 108.6 | 130.1 | call |
| `test_harness_sql_emission_portability.py::test_every_admitted_artifact_exports_corresponds_and_decodes[mysql]` | Runtime 3.13 / shared-acquisition | 98.8 | 117.7 | call |
| `test_harness_target_conformance.py::test_empty_text_anchor_requires_the_observed_var_string_type` | Runtime 3.13 / general-runtime-1 | 44.3 | 56.1 | call; the fixture was already built on its worker |
| `test_repo_reader_acquisition.py::test_shared_facts_match_legacy_text_ast_import_and_identifier_acquisition` | Runtime 3.13 / general-runtime-3 | 32.6 | 59.0 | call |
| `test_execution_compiled_bundle.py::test_mysql_lpad_and_now_cells_are_derived_in_linear_work[pair-_beside_a_capture]` | Runtime 3.13 / general-runtime-1 | 28.0 | 32.8 | call |
| `test_repo_test_layout.py::test_no_test_reads_the_mutable_status_or_roadmap` | Runtime 3.13 / general-runtime-1 | 26.6 | 30.2 | call |
| `test_execution_compiled_bundle.py::test_mysql_lpad_and_now_cells_are_derived_in_linear_work[words-_chained_lets]` | Runtime 3.13 / general-runtime-2 | 22.7 | 37.1 | call |

Seven of the ten ids are in the E-C profile of `43181411369`. New are the
two `test_mysql_lpad_and_now_cells_are_derived_in_linear_work` cells, which
by their source compile and export MySQL programs of m × m cells for m
of 4, 8 and 16 to prove a linear-work count law, and
`test_repo_test_layout.py::test_no_test_reads_the_mutable_status_or_roadmap`,
which by its source reads the string literals of every test file through
the shared repository facts. The two `test_sql_values.py` bound nodes
(20.7 s and 19.9 s) and
`test_semantic_capability_facts.py::test_private_module_has_only_authorized_window_strategy_compiler_consumer`
(21.2 s) left the list. On Python 3.12 the same seven lead and the two
`lpad` and `now()` cells follow; its tenth in-process node is
`test_sql_values.py::test_the_static_values_bound_is_no_emission_guarantee[postgres-1000-64-blockers2]`
(31.5 s), and `test_repo_test_layout.py` is the twelfth.

The cProfile half of step 4 is NOT_OBSERVED (PL.07): this reading ran no
pytest, so none of the ten ran alone under cProfile, no verifier-runs,
call-count or self-time finding is recorded, and no performance claim
rests on the table. The Windows jobs are outside partition health by
design, so their nodes are not ranked. GitHub's rendered Job Summary has
no REST endpoint and was not read; the summary was regenerated from the
artifact with `summary_markdown`, the function CI writes it with. Health
is advisory, and nothing here changes scheduling, topology or test
selection.

## S06's run on the batch head

The commit message of `1abbc7d5` carries S06's run under D77.50 by the
reach of the changed code. The first documentation commit after the batch
was published adds the comparison that D77.50's promotion record names:
from the frozen `tests/_pietto_execution_duckdb_native_cases.py`, 24
queries, which include every query the probe compiles (P0, P1 and P2, each
with the projection, the comparison for each of the six operators and the
`!=` query that selects `note`), were compiled with `compile_query` once on
the source tree of `cf460bda` and once on that of `94b4097a`. The 24
`pietto.sql-emission` documents are byte-identical on both sides, without
setting aside the `compatibility` and `producer` fields, with the same
slots and parameters; the listing of their digests has the sha256
`fa964d6a86587f0cdc1ace9d4c6de046e36c13355eb9c7333837cd12f2d75bb6` on
both trees.

## Budget, failures and Gate 2

The ceiling is `C240/F720/D8200/S8` (D79.08, D79.09, PL.09) plus half of
PK's `C80/F240/D2400/S8`. The owner's raise of near-exhausted ceilings on
2026-11-14 changes neither: at 16:30Z Phase79 with its half of PK had used
about 40% of its D and less of the rest, below the 75% that qualifies
(PL.30). At the midpoint Phase79 had used at most C15, F71, D2,349 and S0.
By the row sum of the owner-held ledger through S06's seal at 17:05Z on
2026-11-14, Phase79 has used at most C17, F99, D3,432 and S0 of
`C240/F720/D8200/S8`, and with its half of PK at most C18, F118, D3,866
and S0 of `C280/F840/D9400/S12`. The S08 lane's work after 16:30Z, this
batch's assembly, its two Gate 2 runs and its audit are charged after that
row; when the batch was published, the ledger held no Phase79 row after
S06's seal, so no total with them is recorded here (owner: the lead, on
the ledger outside Git).

The route has the closeout read the CI health again, as the midpoint did.
That read is NOT_OBSERVED (PL.07): the lane that closed B1 holds no
read-only token, so it read no health of the newest published head,
`ab594829`, and the midpoint's read of `a015afcf` stays the last one.
Health is advisory, and the ten-slowest profile above reads the batch
head's own health after publication.

Failures are kept, never rerun as replacements: the midpoint's first
`pyright` pass, which ran without the run's interpreter; by the lead's
ledger, the S06 lane of 2026-11-13 that stopped BLOCKED for its missing
midpoint record and result-reader wiring; the integration chain INT1
(`01c3b7f4`, tree `7b0db316`), which passed its Gate 2 on 2026-11-14
(16:31:26Z to 16:42:21Z: 30,780 passed, 65 skipped) but was not pushed,
because its batch audit found that pushing it alone would publish SQLite
B1 before the complete DuckDB B1 (PL.31, PL.32), so that Gate 2 stands for
that tree only; the first offline sync of INT1's `execute-duckdb`
environment, which stopped before it installed anything because its cache
lacked `ruff` 0.17.4; and S08's first draft, which changed the
specification that S06's freeze binds until its review sent it back, so
the specification is restored byte for byte.

The batch audit's first round found one real bug, the owner-answer
times in PL.30–PL.32, and six lows; the times were fixed in the decision
commit and S08 was replayed onto it, and a judge found no real bug left.
A Gate 2 on the first assembly, `1c64a26c` (tree `bafe3c0e`), passed
and stands for that tree only. The batch Gate 2 ran once on
the final tree `58f5e281`, on the integration host, on 2026-11-14 from
21:43:45Z to 21:52:57Z: `scripts/validate.py` passed in 542.2 s, with
pytest at 489.42 s on 20 workers (30,779 passed, 65 skipped, none
failed). Its package smoke (21:53:08Z to 21:53:36Z) built the wheel and
sdist and passed the core and `execute-duckdb` cells, the latter with a
real `duckdb_arrow` query, and the DuckDB extra start of the lead's
ruling of 2026-11-13 (21:53:36Z to 21:53:48Z) passed 92 tests of
`tests/test_sql_duckdb_emission.py` and
`tests/test_execution_api_duckdb_arrow.py` in an `execute-duckdb`
environment. The lows that touch B1 are fixed in that first
documentation commit.

## Phase82 inputs

The [freeze ledger](../../roadmap.md#phase82-freeze-ledger) gains two rows:
the DuckDB Arrow route surface (the connector spelling and texts, the
dialect, the contract values, the compile refusals and their order, the
execute API, the capture limits, the session settings, the detail words and
the extra), and the error-class rule that `RequestRejected` carries the
PIE-R2xxx refusals of `execute()`'s own checks while the PIE-R1004 width
refusal covers only the PostgreSQL and MySQL routes.

## Phase78 handoff

- **Order.** SQLite B1 publishes only once DuckDB B1 has published or lies
  below it (AD78.02), and a change of that order needs the owner. On the
  INT1 candidate chain the SQLite commits lay above S07 and below the
  midpoint record and the wiring, and S06 and S08 were not on it. On
  2026-11-14 the lead asked the owner which order holds: S06 and S08 sit
  above Phase78 S01–S04 and publish with them in one push, or a strict
  restack puts S06 below S07 and S06 to S08 below Phase78 S01. The owner
  answered that the same batch is fine (PL.32): S06 and S08 sit above
  Phase78 S01–S04, and both B1 batches publish in one fast-forward push,
  so SQLite B1 never reaches `main` before the complete DuckDB B1.
- **Seam.** AD78.03 holds on the integrated tree: the PostgreSQL and MySQL
  pipeline never receives `duckdb` or `sqlite`, and the firewall in
  `tests/test_repo_static_checks.py` lists both. SQLite B2's Gate 1
  decides, before any B2 code, whether it generalizes that firewall or
  builds its own pipeline (the route's deferral). The connector and dialect
  sets were written in a shape that SQLite's entries extend, and
  `project_sql_plan_target_assessment.py` maps each family as the pure
  boundary does.
- **Reading.** The Phase78 completion audit reads this audit.

## Phase79 B2 handoff

- **Owner decision, made.** Whether `0.2.0` also needs a B2 (`group by`
  with `count`, `sum`, `min` and `max`, then `order by` and `limit`) was
  the owner's. The route set its latest point at this audit, before any
  `0.2.0` request, and the owner's request of 2026-11-14 to release
  Phase78–80, which the lead reads as `0.2.0` (PL.31), came first. The
  owner then answered that `0.2.0` carries B1 only (PL.33), so B2 is not
  part of `0.2.0` and is not opened without its own Gate 1.
- **Gate 1 first.** B2 needs its own Gate 1. It inherits the adapter with
  its closed order of 33 compile rules, which B2 extends; the session
  settings and capture policy; the storage kinds; S06's native matrix with
  its Pietto-owned oracle; and the deferral of sqlglot as a test oracle to
  the first slice beyond projection and filter.
- **Deferred owners.** Other Phase79 forms (multi-source, JOIN, windows,
  more parameters, `Decimal`, temporal, `UUID` and nested types, bundles,
  saved, relay and job routes) wait for later Phase79 Gate 1s, and the
  Phase82 freeze lists each one that no Gate 1 takes as unsupported.
  Platforms beyond PL.05 belong to Phase81. Reminder 8 (JOIN facts, a
  forged compiled `median`) stays satisfied by exclusion: B1 has no JOIN
  and, since it refuses bundles, no new consumer of compiled admission. It
  passes to the first Phase79 slice that admits a JOIN or such a consumer.
- **Debt.** Any finding of the ten-slowest profile above. The
  specification's construction state and open items were updated in the
  first documentation commit after the batch was published.
