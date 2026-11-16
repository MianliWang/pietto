# E-C completion audit

E-C, the editor core work package whose scope ED.03 fixes, adds five alpha
surfaces to `pietto lsp` and measures an editor latency budget. It is a work
package of the [editor line](../roadmap.md#editor-work-package), not a phase.
This audit checks the closure conditions of its [route](ed03-route.md) and
ends with the handoff to the next editor step. It publishes nothing: live
`main` and its natural exact-head CI remain the lifecycle authority, and the
surfaces stay alpha until the [Phase82 freeze](../roadmap.md#phase82-freeze-ledger).

## Baseline and batches

| Step | Fact |
| --- | --- |
| Gate 0 | `main` at `ab972f362c433b234a74f542c5d274d22c8cdeae` (tree `821be1ccf7bb6f3e14b8d00d80f1f30d3cc087fe`), the published D77.04 head; natural exact-head CI `42831340276`, push/main attempt 1, passed all 21 jobs. |
| Gate 1 | The owner approved the route on 2026-11-10 with the decision sheet's recommended answers: PL.01–PL.06 and ED.03–ED.06 in the [decision record](../decisions.md). On 2026-11-11 the owner added ED.07 (the editor defaults, M1's budget as inform) and PL.07 (the CI health token). |
| EB1 | Four commits fast-forward pushed on 2026-11-10 at 21:00:30Z on `a503167f`: `26748232` (M1), `25e3dd47` (C1), `4a664902` (C2) and `ae48f00a` (its candidate record), ending at `ae48f00ae253dcde81050548b69fc297aad2c3f0` (tree `4c5cc7c0e4347930946e92fffa1616de10cfbc12`). One Python 3.13 Gate 2 on that tree passed 27,688 tests with 41 skips. Natural exact-head CI `42900771741`, push/main attempt 1, passed all 21 jobs. Its publication record `41e27e5c` (D77.14) passed natural CI `42917583571`. |
| Midpoint | The EB1 health was read on 2026-11-11 between 10:21Z and 10:22Z through PL.07 (runs `42831340276`, `42900771741` and `42917583571`, each INSUFFICIENT_EVIDENCE with a WATCH screen; the only alert that needs no history is the structural `FEWER_UNITS_THAN_WORKERS` that predates Gate 0). The Phase77 overlap was measured again between 16:51Z and 17:10Z on `e0116e41`. The midpoint record, with ED.08 (M1's budget), ED.09 (the completion words) and the route changes it carries, ED.10 (the ledger and stop points), ED.11 (C4's scope) and PL.09 (every ledger doubled), is the documentation-only batch `864411cb2ab4a89deccd14904de3e35f67b04010` (D77.14); its natural exact-head CI `43181411369`, push/main attempt 1, started at 08:15:09Z on 2026-11-12, completed at 08:34:15Z and passed all 21 jobs. |
| EB2 | C5, C4, Z1 and this audit (Z2), one commit each in that order on `864411cb`. The batch's Gate 2 on its final tree, its batch audit, its editor checks, its fast-forward push and natural exact-head CI on its head come after this audit is written; [EB2's publication record](#eb2-publication-record) records them and the commit identities. |

## Closure conditions

The route's [closure](ed03-route.md#midpoint-unfreeze-and-closure) has five
conditions:

1. M1's budget is recorded: ED.08, published with `864411cb` (CI
   `43181411369`).
2. C1, C2, C5 and C4 are on `main` with green natural exact-head CI. C1 and
   C2: EB1, CI `42900771741`. C5 and C4 are in EB2 and take the result of
   its batch head, which EB2's publication record records.
3. Z1 is done: the acquisition review below and the shared rows of
   `docs/status.md`, `docs/roadmap.md` and `README.md`. The Z1 commit of
   EB2 adds the Editor core EB2 status row, removes the delivered E-C
   sentence from the editor section of the roadmap, adds the E-C row to the
   [Phase82 freeze ledger](../roadmap.md#phase82-freeze-ledger) and names
   completion in the README's Editors item; the ten-slowest profile is
   below.
4. The closeout reads the eligible CI health and alerts of the latest
   published head. This audit is part of EB2 and came before EB2's head was
   published. EB2's publication record read the health of `22046a4f` but
   did not close E-C; the [E-C closeout record](#e-c-closeout-record) reads
   that of `107df991`.
5. This audit is on `main` with green natural exact-head CI. It takes the
   result of EB2's batch head, which EB2's publication record records.

### The surfaces are delivered

- **Formatting (C1).** `textDocument/formatting` runs `format_source` on the
  request's current buffer and returns one whole-document edit, `[]` when
  nothing changes, or `null` for each refusal path; it reads no disk and
  answers when the request is read.
- **Workspace symbols and document links (C2).** `workspace/symbol` lists
  every retained declaration of the current analyses in root, module and
  source order without deduplication; `textDocument/documentLink` links each
  import path that the same analysis resolved to exactly one module.
- **Completion (C5, revised by ED.09).** One complete list: the keywords that
  accepted source writes, the builtin types, scalar functions and aggregates
  of the core catalog, in a fixed order, then the identifiers of the request's
  open buffer that the list does not already hold, without the word being
  typed. It reads no snapshot, disk file or other document and never waits for
  an analysis. The owner asked for the buffer's identifiers after a VS Code
  1.145.2 development host showed that the static list alone removed the
  editor's word-based suggestions (ED.09). The completion record that the
  route asks for before C5's acceptance is written: the
  [external-reference review](../spec/lsp-editor-facts-v1.md#external-reference-review)
  of LSP editor facts v1 read the LSP 3.17 page on 2026-11-12 at 07:07:16Z.
- **Hover and definition (C4), delivered in part.** Facts come only from
  bindings the analysis already keeps, one per use occurrence: the field reads
  and relationship calls of a single file's JOIN relations, the field and
  `let` reads of `let` values, `select` items and `where` of a project relation
  without JOIN, and a `from` that reads a project relation `let`. Other uses
  have no fact: the analysis keeps no exact per-use binding for the other
  reads, `let` uses, `def` calls and parameters, or relationship parameters,
  and this version does not project a relationship call's arguments, which the
  analysis keeps. The owner chose to deliver only what the analysis keeps and
  to leave the semantic layer unchanged, between about 18:00Z on 2026-11-11
  and 2026-11-12 (ED.11).
- **The latency budget (M1).** M1 measured snapshot construction, diagnostics
  after an edit, the request families and `format_source` on a named corpus,
  in the [latency measurement](../spec/lsp-editor-facts-v1.md#latency-measurement-ed03-m1)
  of LSP editor facts v1. ED.08 keeps its budget as a review bar, not a test.

### Acceptance

- **Observable.** Protocol tests run through `pietto lsp`
  (`tests/test_cli_lsp.py`) and project facts through
  `tests/test_project_editor_overlays.py`. Nodes per Python: 96 and 7 at
  Gate 0, 115 and 8 at EB1 (CI health groups of `42831340276` and
  `42900771741`). On the lanes, C5 adds 3 nodes to `test_cli_lsp.py` and C4
  adds 1 to each owner (2026-11-12 lane runs: 99 passed on the C5 lane, 125
  passed on the C4 lane). On the integration tree after C4, before Gate 2,
  `test_cli_lsp.py` has 119 nodes and `test_project_editor_overlays.py`
  9, and all passed on 2026-11-12; EB2's publication record records the
  counts and results of its Gate 2 and CI.
- **Existing.** `test_cli_format.py` and `test_parser_format.py` are
  unchanged (C1); `test_project_check_partial.py` is unchanged (C2, C4); the
  CLI project check builds no editor facts
  (`test_project_editor_overlays.py::test_cli_project_checks_do_not_build_editor_facts`);
  fact, symbol, link and completion requests start no analysis (count tests in
  `test_cli_lsp.py`). On the integration tree the repository-wide owners
  (`tests/test_repo_*.py`), the layering tests and
  `test_project_check_partial.py` passed after C4, and the repository-wide
  owners and layering tests again on the final tree, on 2026-11-12; EB2's
  Gate 2 is recorded by its publication record.
- **Connected.** EB1's VS Code 1.145.2 host check, through extension `e61444f`
  and `vscode-languageclient` 9.0.1 on Linux/WSL, passed 19 capability checks,
  failed none and skipped 4, each skip owned by a protocol test, and covered
  `file` URIs (percent-encoded and non-ASCII paths included) and `untitled:`
  buffers; formatting, workspace symbols and import links passed narrowed, as
  the [status](../status.md) records. EB2's publication record left the
  host check of completion (the ED.09 word-suggestion check repeated on
  `e61444f`) and of the new hover and definition facts NOT_RUN; the
  [E-C closeout record](#e-c-closeout-record) records its run, which
  passed.

### What E-C leaves unchanged

E-C changes no CLI command, JSON artifact, semantic metadata artifact,
relation column view, compiled record, PIE code, editor-only message, grammar
or built-in catalog, and so triggers no extension sync under D76.12. C4 reads
semantic results and changes no file under `semantic/**`, `_project/project_*`
or the IR. From Gate 0 to EB2's Z1 commit, the E-C commits change no file
outside `src/pietto/_lsp.py`, `src/pietto/_editor_facts.py`, the new
`src/pietto/_editor_completion.py`, `src/pietto/_project/check.py`,
`scripts/package_smoke.py`, the two protocol test owners, `README.md` and
`docs/`, so no generated lexer or parser, grammar or built-in catalog file.

### Acquisition consolidation (Z1)

Z1 reviewed the new and changed tests since Gate 0 under the
[phase-end acquisition consolidation](../development.md#phase-end-acquisition-consolidation),
on the C5 and C4 lanes on 2026-11-12.

- **Coverage.** No node was removed, merged or moved, so coverage equivalence
  is trivial: `test_cli_lsp.py` goes from 96 nodes at Gate 0 to 119 and
  `test_project_editor_overlays.py` from 7 to 9 on EB2's integration tree.
- **In-process sessions.** Each protocol test runs its own scripted session
  through `_lsp._Server` in the test process, with its own input; nothing is
  shared.
- **Fresh processes.** `run_process` starts a real `pietto lsp` process for
  `test_lifecycle_over_a_process` (changed by C1, C2 and C5),
  `test_formatting_over_a_process` (C1), one request of
  `test_completion_answers_the_oracle_at_once_at_every_position` (C5) and the
  older `test_protocol_errors_over_a_process`. One start took 0.46 to 0.50 s
  on the integration host. The completion test's process also reads the
  advertised capabilities that the lifecycle test reads; it is kept as a
  low-value exception (owner `tests/test_cli_lsp.py`), because it proves the
  completion list over real stdio in a fresh interpreter, and folding it into
  the lifecycle test saves one start per run.
- **Oracles and fixtures.** The in-process `pietto check` comparisons and the
  completion oracle are independent assertions over distinct inputs. Each
  test writes its own small project under `tmp_path`, with different sources
  and, for some, its own URI spellings. Mutation witnesses live outside the
  tree. E-C changed no shared test helper.
- **Cost.** In the EB1 record's health (`42917583571`) neither owner appears
  among any partition's 30 slowest nodes or 10 slowest file groups. Serial
  lane runs on a quiet host (one-minute load 0.9) took 6.20 s for the C5
  lane's 99 nodes and 6.85 s and 0.33 s for the C4 lane's two owners. The
  slowest new or changed E-C node is C1's
  `test_formatting_edits_the_buffer_into_the_bytes_fmt_prints` (0.94 s, the
  `fmt` corpus); the nodes of C5 and C4 take 0.01 to 0.50 s each, and E-C's
  two new process starts take about 1 s per Python per run.
- **Result.** No significant repeated acquisition: no consolidation,
  structural or wall-time gain (no gain). Outside E-C, the Gate 0 test
  `test_protocol_errors_over_a_process` takes about 3 s in several process
  starts; it is left to the next whole-tree pass.
- **Ten-slowest profile.** The Python 3.13 health of the midpoint run
  `43181411369` records 126 slowest nodes: 30 for each of the
  shared-acquisition and three general-runtime partitions and 3 for each
  portability partition. Ranked by setup, call and teardown time, 15 nodes
  above the tenth in-process one were left out because their time is spent
  in child processes: the differential process cells of
  `test_harness_ir_differential.py`, `test_harness_plan_conformance.py`
  (its setup is that acquisition), `test_harness_plan_portability.py` and
  `test_harness_sql_emission_portability.py`; the six checkout, relocated
  and installed standalone batches of the two portability files; the two
  fresh source-free processes of `test_execution_compiled_source_free.py`;
  and three nodes of `test_harness_execution_api.py`, whose module fixture
  starts a fresh `-I` worker for each consumer case. Each of the ten
  in-process nodes ran once alone under cProfile (`-n 0`, `nice -n 19`)
  between 10:25Z and 11:15Z on 2026-11-12, on EB2's integration tree at
  its Z1 commit, whose code is this batch's. The host was quiet, by the
  one-minute load under 2 and no other pytest process, only for the last
  four; after waiting five minutes each, the first six started at a load of
  3.4 to 17.2, five of them beside other pytest processes. Call counts do
  not depend on the load; the seconds do.

  | Node | CI s | Alone s | What the time is |
  | --- | ---: | ---: | --- |
  | `test_harness_target_conformance.py::test_receipt_corruption_is_rejected_without_any_resource[postgres-missing]` | 182.8 | 151.8 | the module fixture `valid_receipts`: 548 in-process emissions |
  | `test_harness_target_conformance.py::test_data_only_receipt_controls_have_nonempty_positive_denominators[mysql]` | 176.1 | 154.1 | the same fixture |
  | `test_harness_sql_emission_portability.py::test_every_admitted_artifact_exports_corresponds_and_decodes[postgres]` | 166.0 | 130.0 | 277 emissions and 226 observation checks |
  | `test_harness_target_conformance.py::test_data_only_receipt_controls_have_nonempty_positive_denominators[postgres]` | 149.7 | 140.2 | the same fixture |
  | `test_harness_sql_emission_portability.py::test_every_admitted_artifact_exports_corresponds_and_decodes[mysql]` | 149.3 | 112.8 | 276 emissions |
  | `test_repo_reader_acquisition.py::test_shared_facts_match_legacy_text_ast_import_and_identifier_acquisition` | 50.0 | 52.7 | repeated AST walks of 354 files |
  | `test_harness_target_conformance.py::test_empty_text_anchor_requires_the_observed_var_string_type` | 43.8 | 148.6 | the same fixture, which CI had already built (its call is about 25 s) |
  | `test_sql_values.py::test_the_static_values_bound_is_no_emission_guarantee[postgres-1000-64-blockers2]` | 30.0 | 23.3 | one emission, 15.4 s of it the parse-only project check of the bound VALUES body |
  | `test_sql_values.py::test_the_static_values_bound_is_no_emission_guarantee[mysql-1000-64-blockers3]` | 29.9 | 24.0 | the same on MySQL |
  | `test_semantic_capability_facts.py::test_private_module_has_only_authorized_window_strategy_compiler_consumer` | 25.8 | 24.3 | 23.6 s building the AST facts of 330 source files |

  No E-C code runs in these nodes; the repository readers among them read
  E-C's files with every other source file. Findings:

  1. **Recorded as debt.** Project SQL emission verifies the same plan
     completely many times. `verify_project_sql_plan` is not memoized: the
     call-scoped memo covers `_verify_compiled_sql_plan` only. A bounded
     count over 24 generation inputs of both targets found 4 to 29 complete
     runs per case, 21.1 on average, always on one plan object, one of them
     by the test helper; the rest come from five callers inside
     `emit_project_sql` (the requirement and source-map `_require_plan`,
     plan inspection, emission layout scopes and `prepared_current`). In
     the fixture nodes, 17,324 runs for the fixture's 560 emission
     preparations (548 through the helper, 12 through the CLI) took 42 to
     50 s of 135 to 149 s; the source-map and requirement-report verifiers
     ran 3,012 and 6,570 times there, how many on one object not
     measured. A fix needs an op-count test under the verification
     budget. Owner: `_project/project_sql_plan_verification.py` and its
     emission callers; latest point: Phase77's phase-end acquisition
     consolidation, before its completion audit.
  2. **Kept.** Four of the ten nodes are one module fixture,
     `valid_receipts`, which CI builds at least once in each of the three
     general-runtime partitions that run parts of its file (146 to 179 s
     each). Sharing it
     across jobs is a placement change, which needs its own evidence and
     authority (CI governance), not a review conclusion. Its 1,122
     temporary directories took 0.1 s of `mkdir` in two runs and 4.7 to
     7.2 s in the two that started at a load of 14 to 17.
  3. **Kept.** The reader-acquisition node walks each AST more than once
     because it is the equivalence witness of the shared reader against the
     legacy acquisition.
  4. **Kept.** The capability-facts node pays the per-worker shared
     acquisition of `tests/_pietto_repo_facts.py` alone; in CI the first
     reader on a worker pays it.
  5. **Kept.** The two VALUES nodes are parse-bound by the input that the
     static bound needs, and `_input_tree`, the top self time of the
     portability nodes (7.3 to 8.6 s), makes about three bound checks per
     JSON value, linear in its input.

  No earlier review of these nodes is in the tree to reuse; the last
  recorded profile, Phase74's, kept no result.

### Gate 2 duration

EB1's Gate 2 took 327.2 s in all, 277.99 s of it pytest, at 20 workers; its
publication record's Gate 2 took 319.1 s (pytest 268.78 s). EB2's Gate 2
runs after this audit is written, on the final tree that holds it, so EB2's
publication record records its duration.

## Lessons

- **Batch work needs its own allocation.** ED.04 allocated D by slice and
  kept a 400 D replay reserve, but no allocation for the work of a batch.
  EB1's batch work alone used D865, so the ledger had to be raised at the
  midpoint (ED.10).
- **Inventory the retained bindings before promising facts.** The route
  promised hover and definition for fields, lets, parameters and calls from
  exact existing bindings. C4's first step found that the analysis keeps an
  exact per-use binding for only some of these uses, and the write set that
  excludes `semantic/**` turned the rest into an owner decision. A slice that
  reads semantic results takes that inventory before its scope is fixed.
- **A mutation per filter branch.** The project-side occurrence filter of C4
  had no witness until a mutation that removes it was run; each branch that
  drops or keeps a use gets its own mutation.
- **Observe the client before fixing a contract.** A static completion list
  looked additive, but on VS Code 1.145.2 with default settings a development
  host showed that the static list alone removed the editor's word-based
  suggestions for the open file (ED.09), while the extension's snippets
  stayed; why was inferred from the 1.145.2 source, not observed. The check
  found it before release.
- **Name a quiet point for a quiet-host check.** On the shared integration
  host, six of the ten profile runs found no quiet point within five
  minutes and ran at a one-minute load of 3.4 to 17.2; the last four found
  one. M1 likewise ran at a load of 1.2 to 4.7. A check that needs a quiet
  host gets a quiet point that the lead names, or records the load it had.
- EB2's batch audit and editor checks come after this audit is written;
  EB2's publication record records what they find.

## Budget

| Account | Cap | Use |
| --- | --- | --- |
| E-C | `C70/F210/D2400/S6` (ED.04); `C70/F210/D3900/S6` from the midpoint (ED.10); `C140/F420/D7800/S12` from 2026-11-12 (PL.09), with the stop points for C4 and for EB2's batch work at D1200 each (ED.10) | The lead's ledger stood at D2,326 (C at most 8, F 78, S 0) by its entry of 2026-11-12 at 07:45Z, the sixteenth review round; later rounds, EB2's integration and its publication follow, so EB2's publication record and the [E-C closeout record](#e-c-closeout-record) record the later figures. Every failure stays counted (ED.04). |

## Failed histories kept

- EB1's editor batch checks failed twice before the third run passed; the
  two failed runs are kept beside the passing one, outside Git.
- In the lanes, a pytest start that collected no test (arguments passed
  literally from outside the lane, exit 5) and a start whose arguments pytest
  refused are kept and counted, and so is a mutation run of the C5 closing
  review that stopped before any result (kept as void).
- The closeout's first completion host run failed before it wrote a result;
  it is kept beside the two passing runs, outside Git (see the
  [E-C closeout record](#e-c-closeout-record)).
- No published E-C head failed its natural CI: `42900771741` (EB1),
  `42917583571` (its record) and `43181411369` (the midpoint) passed all 21
  jobs. Superseded lane trees and their rebase inputs stay outside Git.

## EB2 publication record

EB2 reached `main` without the documentation-only record (D77.14) that the
sections above expect: its four commits end the repairs before the `0.1.11`
cut and shipped in `0.1.11` (see the [status](../status.md)). This record,
written on 2026-11-15 on `22046a4f`, adds what they leave to it.

- **Commits, Gate 2 and CI.** `9264295a` (C5), `945f9ada` (C4), `3bf3aae3`
  (Z1) and `4ef90859` (Z2) end the repairs before the cut at
  `4ef90859ec9366088af1a74690fc35ee5344de7f` (tree
  `427b976ff3228a73fdcb0c20fb1d9d4e957c377d`), fast-forward pushed on
  `864411cb` on 2026-11-13 at 01:43:28Z. Its Python 3.13 Gate 2 on that tree
  passed 27,758 tests with 41 skips in 504.2 s, 445.11 s of it pytest, at 8
  workers. Natural exact-head CI `43347023208`, push/main attempt 1,
  completed with success at 02:02:06Z and passed all 21 jobs, so closure
  conditions 2 and 5 hold. By the lead's ledger, outside Git, EB2's own
  batch audit found three low findings, and the batch audit of the repairs
  before the cut was clean with four low findings. The lead's records hold
  no editor batch check, package smoke or host check of EB2's head.
- **Test owners.** The Gate 2 log records totals only. On `4ef90859`
  (tree `427b976f`), `tests/test_cli_lsp.py` has 121 nodes and
  `tests/test_project_editor_overlays.py` 9; a run of the two on 2026-11-15
  at 09:29Z (Python 3.13.13, 8 workers, temporary storage on ext4) passed
  all 130 with no skip. The two nodes beyond the 119 of EB2's integration
  tree are the parameters that the PL.18 repair `f6505643` added before EB2
  in the same batch. Gate 2 had no failure. Its log does not show whether
  any of its 41 skips fell in these owners, whose only skips are on Windows
  and where file names ignore letter case; its temporary storage was also
  ext4. The health of the latest published head (below) counts 121 and 9
  nodes per Python, on a tree whose `test_cli_lsp.py` is that of `4ef90859`
  byte for byte and whose `test_project_editor_overlays.py` differs only in
  two import lines.
- **Closure condition 4: not complete.** Read on 2026-11-15 between 08:05:00Z
  and 08:05:58Z through the owner's read-only token (PL.07): the health of the
  latest published head `22046a4f`, whose natural exact-head CI `43677803825`,
  push/main attempt 1, passed all 21 jobs. Its workflow report verifies and
  says INSUFFICIENT_EVIDENCE with a WATCH screen; history is available, with
  three accepted runs and no comparable sample. The alerts are the structural
  `FEWER_UNITS_THAN_WORKERS` of the plan- and emission-portability partitions
  on both Pythons; the provisional `SHARD_IMBALANCE_REVIEW` (3.12) and
  `SHARD_IMBALANCE_WATCH` (3.13), which compare each Python's six partitions
  and name no node; and 18 `LONG_INDIVISIBLE_NODE`, each on a harness node.
  There is no cost signal or repeat confirmation, and the cost record is
  partial without the target conformance aggregate job. No alert names an E-C
  test owner. EB2's own run `43347023208` had no health read. E-C does not
  close in this record (below), so this read is not the closeout's: the
  closeout reads the eligible CI health and alerts of the latest published
  head again when E-C closes.
- **Connected layer of C5 and C4: NOT_RUN, open.** Neither the ED.09
  word-suggestion check on `e61444f` nor a host check of the new hover and
  definition facts has run. The host steps for those facts were never written.
  This record changes only documentation and runs no VS Code host; that is its
  scope, not a check that cannot run, so the connected layer stays an open E-C
  item and is not claimed for C5 and C4. The extension's `0.4.0` completion
  step with Pietto `0.1.11`, which the status records, stays related evidence;
  none of its steps reads a hover or definition fact.
- **Ledger.** The lead's E-C ledger, outside Git, has no row after the
  sixteenth review round (2026-11-12 at 07:45Z): C at most 8, F 78, D 2,326
  and S 0 of `C140/F420/D7800/S12` (PL.09). EB2's assembly, with its batch
  audit and the ten-slowest profile (F 6, D 193), a further review of EB2 in
  the lead's nineteenth round and its integration into the repairs before the
  cut were counted on Phase77's ledger, the last two with no share for E-C.
  With the assembly, and excluding the unapportioned shares of the
  nineteenth round and the integration, E-C stands at C at most 8, F 84,
  D 2,519 (about 32% of D7800) and S 0. These figures do not count this
  record.

With these facts closure conditions 1, 2, 3 and 5 hold, and condition 4
is not complete. E-C stays open until a VS Code host check runs the
connected layer of C5 and C4 and the closeout then reads the latest
published head.

## E-C closeout record

E-C closes with this record, written on 2026-11-16 on `107df991`, the latest
published head. It adds the connected layer of C5 and C4, the closeout read
of condition 4 and the ledger. The connected layer ran against `851ad83f`;
the commits from `851ad83f` to `107df991` change no editor file
(`pietto lsp`, its analysis and the editor tests), only DuckDB's sources and
tests, a package smoke script and documentation.

- **Connected layer of C5 and C4: passed.** The host checks ran on
  2026-11-16 between 14:12Z and 14:21Z on the integration host (Linux/WSL):
  the VS Code 1.145.2 test host, extension `e61444f` from a `git archive`
  copy built with `npm run build`, the `node_modules` already on the host
  with `vscode-languageclient` 9.0.1, and Pietto at `851ad83f`, whose
  `pietto lsp` reports `0.2.1`, started with `-B`. The host steps lived only
  in that scratch copy. The extension's canonical worktree kept its HEAD,
  status and diff, and no file in it, `.git` included, was newer than any
  run's start; nothing was committed or pushed to the extension repository.
  Before the runs, a `git status` of the closeout's inventory at 14:02:23Z
  changed the modification time of that `.git` directory; its index,
  tracked files, HEAD and status did not change.
  - **Completion (C5).** ED.09's word-suggestion check, repeated with its own
    probe and file under default editor settings: the suggest widget showed
    `zebra_count` for `zebr`, `quokka_report` and `quokka_total` for `quok`,
    `walrus_name` for `walr`, `animals` and `Animal` for `anim`, and the
    keyword `select` for `sele`, each read at the first trigger. The list
    that `vscode.executeCompletionItemProvider` returns holds all six
    identifiers, so the server offers them, not the editor's word-based
    provider. 7 checks passed, none failed or was skipped. Of three runs, the
    first failed before it wrote any result: its host ended after about 8 s
    with exit 1, from a cause not established, and the run is kept. The
    second, through a wrapper that only records the probe's outcome, and the
    third, unwrapped, each passed all 7.
  - **Hover and definition (C4).** New host steps ask
    `vscode.executeHoverProvider` and `vscode.executeDefinitionProvider` at
    46 positions. Each answer must be the exact hover text over the exact use
    range and the exact target, or nothing. The positions with a fact cover
    every context C4 delivers: the field reads and the relationship call of a
    single file's JOIN relation; the field and `let` reads of `let` values,
    `select` items and `where` of a project relation without JOIN, through an
    imported source's alias too; a `from` that reads a project relation
    `let`; and fields read from a relation `let`, which have a hover and no
    target. The positions without one are a relationship call's argument, a
    template's parameter, a single file's reads outside a JOIN, its `let` use
    and `def` call, and a project's `group by` read, JOIN relation reads,
    relationship call, `def` call and table-function input. The single-file
    positions ran in a plain `file` URI, in a percent-encoded, non-ASCII one
    and in an `untitled:` buffer; the project root is named `Prøj 50% x`.
    Three unsaved edits followed. A line inserted at the top of the untitled
    buffer, and one at the top of a project module, moves their facts with
    the text. A failing shape in the open `models.pietto` removes the field
    and `let` facts of the module that reads it and keeps its `from` fact;
    restored, the text gives a field fact back, with a target that names the
    open document's URI, spelled as the closed file's. 59 checks passed and
    none failed. 3 were skipped, each owned by a protocol test: the wait for a
    pending analysis, no analysis per request, and the occurrence bound of
    the projection. A second run returned the same answers. Before the host
    runs, a `pietto lsp` process asked over stdio gave the expected answer at
    all 46 positions, and each host run's client trace holds a server
    response to each of its 53 hover and 53 definition requests.
- **Closure condition 4: done.** The latest published head is `107df991`,
  whose natural exact-head CI `43888270979`, push/main attempt 1, completed
  with success at 15:04:04Z on 2026-11-16 and passed all 21 jobs. Its health
  artifacts were downloaded on 2026-11-16 between 15:22:41Z and 15:22:56Z
  through the owner's read-only token (PL.07) and checked offline twice:
  their digests, sizes and head match the run's artifact listing (15 of 15),
  and `verify_workflow_health` of `107df991` passes. The workflow report
  says INSUFFICIENT_EVIDENCE with a WATCH screen; history is available, with
  three accepted runs and no comparable sample. The alerts are the
  structural `FEWER_UNITS_THAN_WORKERS` of the plan- and
  emission-portability partitions on both Pythons; the provisional
  `SHARD_IMBALANCE_WATCH` (3.12), which compares the runtime partitions and
  names no node; and 18 `LONG_INDIVISIBLE_NODE`, each on a harness node.
  There is no cost signal or repeat confirmation, and the cost record is
  partial. No alert or suggested action names an E-C test owner. An earlier
  read of the health of `851ad83f` (CI `43814266697`) was superseded when
  `main` moved to `107df991`. Health stays advisory, and E-C takes no
  action on it.
- **Ledger.** The closeout's inventory (D 40), its connected checks and its
  read of the health of `851ad83f` (D 64), and the read of the health of
  `107df991` (D 5) add D 109 and no F. E-C stands at C at most 8, F 84,
  D 2,628 (about 34% of D7800) and S 0, still excluding the unapportioned
  shares of the nineteenth review round and the integration. These figures
  do not count the writing of this record, its checks, Gate 2, batch audit
  and publication.

With these facts all five closure conditions hold: 1 (ED.08), 2 (C1 and C2
by CI `42900771741`, C5 and C4 by CI `43347023208`), 3 (Z1), 4 (above) and 5
(CI `43347023208`). The connected layer of C5 and C4 is no longer open, and
E-C is closed.

## Handoff to the next editor step

- **Uses without a retained binding.** The other reads, `let` uses, `def`
  calls and parameters, relationship parameters, and the arguments of a
  relationship call have no fact. A fact for them needs the analysis to keep
  an exact per-use binding: a semantic change and a scope repair that needs
  its own Gate 1 and the owner.
- **Deferred by the route:** semantic tokens (C3, after M1 and an owner
  decision), references and rename (C6, its own Gate 1), capability facts (K1,
  a Gate 1 design now, implementation after Phase77 S26), quick fixes, watched
  files, the model view, PIE-B diagnostics in the editor, JOIN facts and the
  navigation of import or export list items.
- **Context-aware completion and signature help:** an ARCHITECTURE_DECISION
  after M1.
- **Latency:** ED.08's budget is not claimed for project roots beyond 14
  JOIN-DAG layers or for single queries of 60 to 120 JOINs until linear
  JOIN-DAG analysis or PMS-6 lands or they are measured again.
- **Phase82:** the freeze-ledger row of the E-C surfaces and the use of
  `pietto.cli.main(argv)` by the VS Code extension, in the row that Z1 adds
  to the [freeze ledger](../roadmap.md#phase82-freeze-ledger).
- **The extension:** its documentation of the new surfaces waits for its own
  lane (Q4 is not approved).
- **The connected layer of C5 and C4:** NOT_RUN in EB2's publication record,
  then run and passed in the [E-C closeout record](#e-c-closeout-record). Its
  host steps are kept with that run's evidence outside Git, not in the
  extension repository.
