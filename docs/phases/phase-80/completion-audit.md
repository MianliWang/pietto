# Phase80 completion audit

Phase80 adds `pietto.interop`: one-batch adapters to pandas, Polars, NumPy,
SciPy and Matplotlib, their five extras and the guide
[Python interoperability](../../interop.md), under its [route](route.md),
D80.01–D80.09 and the shared PL rows of the
[decision record](../../decisions.md#phase7880-and-editor-core-gate-1--owner-decisions-2026-11-10).
This audit is S06. It checks the route's closure conditions, records the
freeze-ledger inputs and the acquisition review, and ends with the handoff.
It publishes nothing: live `main` and its natural exact-head CI remain the
lifecycle authority, and the surface stays alpha until the
[Phase82 freeze](../../roadmap.md#phase82-freeze-ledger).

## Baseline and batches

| Step | Fact |
| --- | --- |
| Gate 0 | `main` at `ab972f362c433b234a74f542c5d274d22c8cdeae` (tree `821be1ccf7bb6f3e14b8d00d80f1f30d3cc087fe`), the published D77.04 head; natural exact-head CI `42831340276`, push/main attempt 1, passed all 21 jobs. The route left the read of that CI's eligible health and alerts and the re-measured Phase77 overlap to the first implementation batch; neither is recorded (see open items). |
| Gate 1 | The owner approved the route on 2026-11-10 with the decision sheet's recommended answers: D80.01–D80.07, AD80.01 and PL.01–PL.06. Later rows: D80.08 (the two pandas refusals; the D80.02 wording stands), D80.09 (where D80.08's checks run), PL.09 (every ledger doubled), PL.10 (the one networked lock and the downloads the work needs), PL.13 (b) (the Phase80 batches after the `0.1.11` release commit are pushed without a new request), PL.15 (ledger auto-raise) and PL.17 (the pytest start condition). |
| P0b | The PyPI fetch and isolated install probe of PL.05 ran at 2026-11-10T11:32:46Z. The remaining cells ran offline in the probe's venv on CPython 3.13.13 at 2026-11-10T14:35Z; their results are in the P0b section below. |
| Integration | After the `0.1.11` publication (PL.26) the PK, Phase79, Phase80 and Phase78 lanes were replayed in that order onto `main` at `a015afcf710aaa63b9aeb4b39e31ea0a1cb793b5` (tree `248d74f983d2a3f8b0d913e4fb679d6d17d180a3`) as a candidate of 14 commits, ending at `97156c76d49346af551718651faa3acc72dbfc40` (tree `dada3025e8373d6a40b48282632f68b3ed7035ed`), on which this audit was drafted. On 2026-11-13 Phase79 S07, after PK-80, and the Phase78 closeout (its S04), at the end, joined the chain, which became `85577f75` (tree `8c4b45934c4a9f00d650abe121c34c65b6e44c93`), 16 commits. After the `0.1.12` publication (PL.29) those 16 were replayed in their order onto `main` at `ab594829d0a6a97a3ca85becbdb5fd3e197be1b3` (tree `6685721d32e20beca217784b7679ce062cf2f85d`), each fragment in the commit of the slice that carries it, and Phase79's midpoint record, Phase79 S04's result-reader wiring (D77.83) and the Phase77 follow-up package (D77.80) went above them. With Phase79 S06 and S08, which complete DuckDB B1, that chain is the Phase78–80 integration batch: 23 commits on `ab594829`, fast-forward pushed together under PL.31 on 2026-11-14 at 21:54:54Z, ending at `94b4097a5ec3e1fa5936e352d5b63bf84ec4d688` (tree `58f5e2810fe016c63def144a8eec81e1389c6248`). AD78.02 lets Phase78 B1 publish only once all of DuckDB B1 has published or lies below it; PL.32 records, before the push, the order in which the batch meets that rule: S06 and S08 on top and one fast-forward push. |
| IB1 | Phase80's commits in that batch: PK `0dd333e4` (the five extras, their hash allowlist, the lock and the installed cells, shared with Phase79 S05), S01 `3933b756`, S02 `b5e9a0f7`, S03 `7f9c8d01`, S04 `af43f81f`, S05 `e1067b22` and PK-80 `2a18113e` (the CI consumer steps and the wheel file list). The six Phase80 release-note fragments came with them into `docs/release-notes.d/`, for the `0.2.0` assembly. Gate 2: the Python 3.13 run on the batch's exact tree passed 30,779 tests with 65 skips (20 workers), its package smoke passed and the DuckDB extra start passed 92 tests; the batch audit's one real bug, the owner-answer times of PL.30–PL.32, was fixed before that Gate 2, with no real bug left. Natural exact-head CI: [`43645308189`](https://github.com/MianliWang/pietto/actions/runs/43645308189), push/main attempt 1, passed all 21 jobs. |
| IB2 | This audit, one commit in a batch after IB1's natural CI. |

IB1 differs from the route's plan of one commit each for S01, PK-80 and
S02–S05; the commit messages give the reasons, and the lead's rulings of
2026-11-13 accept these write-set deviations as reviewed
([Lanes and integration](route.md#lanes-and-integration)). PK-80 is two
commits: the one approved lock resolved the five interop extras together with
Phase79's `execute-duckdb`, and the wheel file list and consumer steps need
the S05 modules, so they follow S05. S01 holds the cases, guide sections and
admission table of S02–S05, because the lanes built them into one seam and
revised it as a whole; S02–S05 each add their target module. Under Lean Gate
v3 the batch also carries Phase78, Phase79 and the Phase77 follow-up package.

## Phase77 handoff

D80.01 asks Phase80 to consume the Phase77
[completion audit](../phase-77/completion-audit.md#next-phase-handoff) at
S06 at the latest. That audit was published with `0.1.12` (`50b9c937`
below the release commit `cfafcef3`, natural CI `43600539878`; PL.29), and
Phase77 is closed (D77.83). The replay onto `ab594829` and this audit read
it:

- Its condition for the Phase78–80 lanes, fragments off `main` until
  `0.1.12` is published, is met: they reached `main` with IB1.
- The readers Phase80 reads, `ResultBatch` and the Arrow result types, are
  the ones `0.1.12` published, and Phase79 S04's DuckDB result is now wired
  into them (D77.83); `pietto.interop` reads only the public `ResultBatch`
  (AD80.01), so the wiring changes nothing in it.
- Of its lessons, Phase80 met the third, a Linux Gate 2 does not see
  Windows test failures, as the second lesson below. Lessons 1, 2, 4 and 5
  concern SQL openings, native runs and database engines, which Phase80
  does not touch; lesson 6 binds the lead's workflows, not Phase80's
  product.
- Its owner items were answered on 2026-11-14 (D77.76–D77.83), and its
  debts keep their owners and need nothing of Phase80.

## Closure conditions

The route's [closure](route.md#midpoint-unfreeze-and-closure) has three
conditions:

1. **The five adapters pass all ten installed cells.** On 2026-11-12, from
   06:54:28Z to 06:55:26Z, the CI-shaped consumer passed every cell on
   CPython 3.12.13 and 3.13.13 (cases: arrow 9, pandas 17, Polars 17, NumPy
   18, SciPy 16, Matplotlib 15), and the report checker accepted all twelve
   reports, after an offline package smoke that built the core,
   `execute-duckdb` and five interop cells on both interpreters. That tree was
   `e0116e41` with PK's and the lane's files, not IB1's. On IB1's tree:
   Gate 2 PASS on tree `58f5e281` (30,779 passed, 65 skipped), whose
   package smoke built the core and `execute-duckdb` cells; natural CI
   [`43645308189`](https://github.com/MianliWang/pietto/actions/runs/43645308189),
   push/main attempt 1, whose two check jobs run the interop cells, passed
   all 21 jobs. The D80.08
   repair after IB1 changes `to_pandas` and adds a shared case to every
   cell, so after it the ten cells take the Gate 2 and natural CI of IB2's
   batch head, as IB2 does in condition 2.
2. **IB1 and IB2 are on `main` with green natural exact-head CI.** IB1:
   [`43645308189`](https://github.com/MianliWang/pietto/actions/runs/43645308189),
   push/main attempt 1, passed all 21 jobs. IB2 is this commit and takes
   the result of its own batch head.
3. **The audit records the freeze-ledger inputs, the Gate 2 duration and the
   handoff.** This commit adds the `pietto.interop` row to the
   [freeze ledger](../../roadmap.md#phase82-freeze-ledger) and the deferred
   candidates' latest points (below); the Gate 2 duration is below;
   the handoff ends this audit.

`0.2.0` also needs Phase79, whose DuckDB B1 publishes in the same
integration batch, and its own release approval (D76.14), which the owner
gave on 2026-11-14 (PL.31).

## Delivered

- **Adapters (S01–S05).** `to_pandas`, `to_polars`, `to_numpy`,
  `to_scipy_csr`, `plot_line` and `plot_scatter` with the D80.02 signatures,
  the D80.03 admission table and the D80.04 exception order: `TypeError`,
  then PIE-R4002 for a closed batch, then `ValueError`, then
  `ModuleNotFoundError`, then the target's own errors, unwrapped. Admission
  runs before any target import, so a refused call leaves the batch open and
  no artist on the Axes. `to_pandas` also refuses a repeated field label at
  admission, whatever the fields' types, and after the conversion an index
  other than a `RangeIndex` of the row count and a column dtype other than
  its mapping (D80.08, D80.09; see open items). The package imports none of
  PyArrow, its targets or `pietto.execution` at import (AD80.01).
- **Packaging (PK-80).** `interop-pandas` (`pandas==3.1.1`),
  `interop-polars` (`polars==2.1.0`), `interop-numpy` (`numpy==2.5.4`),
  `interop-scipy` (`scipy==1.18.1`) and `interop-matplotlib`
  (`matplotlib==3.11.2`) each pin only their target (D80.05). The hash
  allowlist `ci/phase80-interop-requirements.txt` pins the versions of
  `uv.lock`, which comes from the owner-approved networked `uv lock` of
  2026-11-11T16:01:21Z (PL.10), and keeps every hash the lock lists; for
  five pins it also lists PyPI files that `uv.lock` omits, as its header
  states. `scripts/package_smoke.py --extra-env interop-X=PATH` builds
  each installed cell, and each CPython check job runs
  `tests/_pietto_results_interop.py` in the arrow-ready cell (the
  missing-extra negatives) and in each interop cell.
- **Local consumer entry.** The Phase68 S19 `consumer` entry is unchanged:
  since PK-80 the two check jobs of natural CI run the interop cells and
  their consumers, as `docs/development.md` states.

### P0b's remaining cells

The route's P0b row and its external-reference table still mark these cells
remaining or "to verify"; this record carries their results. At the pins on
CPython 3.13.13:

- pandas `ArrowDtype` kept int16, int32, large_string and decimal128(38, 2),
  with null positions, a RangeIndex and typed empty frames.
- Polars gave Int16, Int32, String and Decimal(38, 2) with the same nulls,
  and both libraries kept ±(10^38 − 1) in decimal128(38, 0).
  It loads the UUID extension and binary16 as Binary and `list<struct>` as
  List(Struct), and it panics (`PanicException`) on decimal256 inside
  `from_arrow`. The admission table refuses all four before Polars sees them.
- NumPy kept int16 and int32 in writable copies, also for an empty batch.
- SciPy built a canonical `csr_array` from int16, int32 and int64
  triplets, with int32 indices, the value field's dtype and two explicit
  zeros kept; a permuted input gave an equal array.
- Matplotlib, from `matplotlib.figure.Figure()` without `pyplot`, put a
  `Line2D` and a `PathCollection` on the caller's Axes with bit-equal data;
  `pyplot` stayed unloaded, and only the font cache appeared, in
  `MPLCONFIGDIR`.

The probe's first construction of a negative precision-38 value failed in
PyArrow's own type inference; a construction with the explicit type passed
for pandas and Polars. Both runs are kept.

## Acceptance

- **Observable.** The core-only owner `tests/test_results_interop.py` holds
  the fresh-import, import-direction, signature, `TypeError`,
  report-checker, missing-target and CI-cell checks. On the candidate head
  `97156c76`, on 2026-11-13 at about 15:31Z, it passed in the core
  environment and in an arrow-ready environment without NumPy, within the
  integration lane's focused runs (143 passed with 22 DuckDB skips, and 415
  passed with none).
- **Installed.** The ten `pietto[arrow,interop-X]` cells and the arrow-ready
  negatives, as in closure condition 1. Oracles come from the producers'
  inputs, and batches come from real producers through `_batch`.
- **Published.** Gate 2: PASS on tree `58f5e281` (30,779 passed, 65 skipped). Natural CI: [`43645308189`](https://github.com/MianliWang/pietto/actions/runs/43645308189), push/main attempt 1, passed all 21 jobs.

### What Phase80 leaves unchanged

Phase80 changes no grammar, built-in catalog, CLI command, JSON shape, PIE
code, SQL output, compiled `VERSIONS` or core dependency, and so triggers no
extension sync (D76.12). Its commits touch only `src/pietto/interop/`, the
extras, lock and hash allowlist, `scripts/package_smoke.py`, `ci.yml`, the
installation and interop tests and their helpers, `docs/interop.md`,
`docs/development.md`, their six release-note fragments and, in the
shared PK commit, Phase79's `duckdb` block of
`ci/phase67-arrow-compatibility-requirements.txt`. `ResultBatch`,
PIE-R4002 and the Arrow result types stay with their owners.

## Acquisition consolidation

The review covers the tests that Phase80 and its half of PK add or change
since Gate 0, under the
[phase-end acquisition consolidation](../../development.md#phase-end-acquisition-consolidation).

- **New owners.** `tests/test_results_interop.py` (core-only) and the
  consumer script `tests/_pietto_results_interop.py`, which pytest does not
  collect. The consumer reuses `_pietto_results_product` and
  `_pietto_results_nested` and builds its fixtures through real producers in
  each installed cell: independent installed witnesses, kept.
- **Fresh processes.** The fresh `-I -B` import child and the missing-target
  consumer run are process-isolation witnesses, kept.
- **Import direction.** The node parses the source files of `src/pietto`
  itself. `REPOSITORY_FACTS.python(path).imported_modules` of
  `tests/_pietto_repo_facts.py` gives equal sets for all of them: 366 on
  2026-11-13, and 357 on this commit's tree on 2026-11-14, after Phase77
  S26 moved twelve test-only modules out of `src/pietto` and Phase77 added
  three emission modules. The local walk
  took 1.8 s; the shared index took 4.8 s cold, because it also builds four
  other fact sets, and 0.005 s warm (on 2026-11-14, on a busier host,
  3.8 s, 10.3 s and 0.012 s). Reuse saves
  about 1.8 s in a worker that also runs another full reader of `src/pietto`,
  such as `tests/test_repo_reader_acquisition.py`, in either order, and costs
  about 3 s more otherwise, and sharing notes never place tests. Kept as a
  low-value exception; owner `tests/test_results_interop.py`, revisited at the
  next whole-tree pass.
- **Changed shared owners (PK).** `tests/test_release_installation.py`,
  `_pietto_execution_installation_check.py`, `_pietto_repo_package.py` and
  `_pietto_results_consumer.py` read the new extra pins as literals. The new
  per-cell installation tests each export one cell's distinct closure; the
  repeated `uv.lock` parse takes about 12 ms per cell. Their later changes
  on the chain come from Phase77 S26's module move and the `0.1.12` version
  and leave these literals as they were.
- **Result.** No significant repeated acquisition: no consolidation,
  structural or wall-time gain (no gain).
- **Ten-slowest profile.** From the health of IB1's natural CI:
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
  child-process nodes on each Python as at Gate 0. Both comparisons with
  Gate 0 rest on the editor core's read of the Gate 0 run `42831340276` on
  2026-11-11; this package did not read that run's health. There is no
  finish-spread, startup, cost or repeat signal; the health's own cost is
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

### Gate 2 duration

IB1's batch Gate 2 ran on 2026-11-14 from 21:43:45Z to 21:52:57Z on the
integration host: `scripts/validate.py` took 542.2 s, of which pytest took
489.42 s with 20 workers. The package smoke (21:53:08Z to 21:53:36Z) and
the DuckDB extra start (21:53:36Z to 21:53:48Z) followed it.

## Open items

- **Gate 0 reads.** The CI health read of `42831340276` and the re-measured
  Phase77 overlap are not recorded by Phase80. The editor core read that
  run's health on 2026-11-11 (its
  [route](../../editor/ed03-route.md#midpoint-unfreeze-and-closure)), and the
  acquisition review's comparisons with Gate 0 rest on that read.
- **Midpoint.** No midpoint record exists. Its inputs are in this audit: the
  P0b results above, the ledger figures below and the acquisition review.
  The PL.04 option-C check lapsed: the `0.1.11` cut came first (PL.21), and
  S21–S24 had left Phase77 (D77.32); D77.83 (b) retired that clause as moot.
- **`AGENTS.md`.** Closed: the owner added `pietto.interop` and the DuckDB
  Arrow route to its alpha list (PL.34), and this commit makes the edit.
- **README install line.** The route's S06 write set names a `README.md`
  install line, but the 2026-11-13 README trim (`e2b63e3a`) made the README
  the page of the published release, and neither `0.1.11` nor `0.1.12` has
  an `interop-*` extra. The line waits for the release that ships them: the
  `0.2.0` release commit, after this audit in the same push, adds it.
- **D80.08 and repeated labels.** Closed. D80.08 says `to_pandas` refuses
  duplicate field labels, but IB1's code refused them only when the dtype
  check saw a changed type, so repeated labels of one type passed. The lead
  ruled that D80.08 stands and the code deviated (D80.09), and the commit
  after this audit in the same push refuses every repeated label at
  admission, before the pandas import, with no new PIE code. That check
  runs before the conversion, since PyArrow itself fails on some repeats
  during it; the dtype check still runs after the conversion.
- **Deferred candidates.** D80.06 gives them to a later Phase80 Gate 1;
  this audit closes Phase80, so the owner decides who takes them.

## Lessons

- **Check what a `-I` child imports.** `sys.executable -I` ignores
  `PYTHONPATH` and `PYTHONDONTWRITEBYTECODE`. In a lane venv whose `.pth`
  pointed at another checkout, the `-I` children of three test sites
  imported that checkout's `pietto` and wrote 265 `.pyc` files there
  (2026-11-12). Run such children from an environment installed from the
  tree under test.
- **Gate a test by its entry point's platform.** The Windows jobs collect
  `tests/test_results_*.py`, and the consumer's `main` admits only Linux
  x86-64, so its negative test would have failed on Windows CI; the
  integration review found it. A test of a platform-gated entry point
  carries the same predicate.
- **Admit before the target sees the value.** Polars 2.1.0 panics on a
  decimal256 field instead of raising a Python error. A target library's
  failure is not a refusal; admission runs first.
- **Plan shared resolutions as one commit.** One approved lock resolved two
  packages' extras, and one seam held four slices' cases, so neither could be
  split per slice at integration. A route names such shared commits, or gives
  each slice its own files, before the lanes start.
- **Record the midpoint where the closure can read it.** The parallel lanes
  met most midpoint inputs, but no record held them, so this audit had to
  reconstruct them.

## Budget

| Account | Cap | Use |
| --- | --- | --- |
| Phase80 | `C120/F360/D4200/S10` (D80.07); `C240/F720/D8400/S20` from 2026-11-12 (PL.09) | By the lead's apportionment to 16:30Z on 2026-11-14, which counted every shell call of every lane: C at most 11, F 60, D 1,748, S 0, without PK (4.6%, 8.3%, 20.8% and 0%), below 75%, so the owner's raise of nearly used-up ceilings that day leaves the cap unchanged. The lead's earlier entry of 2026-11-13 at 15:32Z, mostly estimates, gave D1,091, C at most 5 and F 38. Later lanes, this audit's replay and repair rounds among them, follow on the ledger. Every failure stays counted. |
| PK, half to Phase80 | `C40/F120/D1200/S4` (PL.05); `C80/F240/D2400/S8` from 2026-11-12 (PL.09) | With Phase80's half of PK, by the same apportionment: C at most 12, F 79, D 2,182, S 0 of `C280/F840/D9600/S24`; the half was D307.5 by 2026-11-13 at 15:32Z. |

## Failed histories kept

Every failed run stays on the ledgers and outside Git: among them the lane
failures of S01–S05, PK's infeasible offline relock (its tenth round), and
the simulated Windows run of the consumer test before its platform gate
(integration round 1). No Phase80 head was published before IB1, so no
natural CI of Phase80 failed before it; IB1's,
[`43645308189`](https://github.com/MianliWang/pietto/actions/runs/43645308189),
push/main attempt 1, passed all 21 jobs.

## Handoff

- **Next direction.** After `0.2.0` the owner runs an external audit and
  then chooses the next direction (PL.31), such as Phase81
  or the MySQL catch-up below.
- **Deferred candidates (D80.06).** D80.06 names a later Phase80 Gate 1 for
  each; who takes them once Phase80 closes is the owner's decision (see open
  items). The [roadmap](../../roadmap.md#deferred-subjects) gives each its
  latest point: `compile_queries(...)` after the forged-compiled trust
  decision; pandas and Polars nesting after the nested work package that
  took Phase77 S24 (D77.32); the Arrow data-analysis example, whose inputs
  Phase79 B1 and Phase80 S02 deliver; `round` of a `Float` with digits,
  database-native array and JSON columns and the `postgres_adbc` nested
  route at the Phase82 freeze.
- **MySQL catch-up.** The owner's answers of 2026-11-14 put a MySQL
  catch-up phase after Phase80 (D77.76, D77.78); it needs nothing of
  `pietto.interop`.
- **Phase81.** CPython 3.14, Windows and macOS claims for the interop cells;
  high-intensity assurance, where a fuzz framework for the closed admission
  table was `NOT_APPLICABLE`.
- **Phase82.** The `pietto.interop` row of the freeze ledger.
- **Pins.** A pin change reruns the admission table and the ten installed
  cells and goes to the owner as a compatibility decision.
- **Phase86.** DLPack and device adapters stay there.
