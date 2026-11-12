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
| EB2 | C5, C4, Z1 and this audit (Z2), one commit each in that order on `864411cb`. The batch's Gate 2 on its final tree, its batch audit, its editor checks, its fast-forward push and natural exact-head CI on its head come after this audit is written; EB2's publication record (D77.14) records them and the commit identities. |

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
   published head. This audit is part of EB2 and comes before EB2's head is
   published, so EB2's publication record (D77.14) records that read.
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
  the [status](../status.md) records. EB2's host check of completion (the
  ED.09 word-suggestion check repeated on `e61444f`) and of the new hover and
  definition facts comes after this audit is written; EB2's publication
  record records its result, or NOT_RUN with its reason, and this layer is
  not claimed for C5 and C4 before it.

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
| E-C | `C70/F210/D2400/S6` (ED.04); `C70/F210/D3900/S6` from the midpoint (ED.10); `C140/F420/D7800/S12` from 2026-11-12 (PL.09), with the stop points for C4 and for EB2's batch work at D1200 each (ED.10) | The lead's ledger stood at D2,326 (C at most 8, F 78, S 0) by its entry of 2026-11-12 at 07:45Z, the sixteenth review round; later rounds, EB2's integration and its publication follow, so EB2's publication record records the final figures. Every failure stays counted (ED.04). |

## Failed histories kept

- EB1's editor batch checks failed twice before the third run passed; the
  two failed runs are kept beside the passing one, outside Git.
- In the lanes, a pytest start that collected no test (arguments passed
  literally from outside the lane, exit 5) and a start whose arguments pytest
  refused are kept and counted, and so is a mutation run of the C5 closing
  review that stopped before any result (kept as void).
- No published E-C head failed its natural CI: `42900771741` (EB1),
  `42917583571` (its record) and `43181411369` (the midpoint) passed all 21
  jobs. Superseded lane trees and their rebase inputs stay outside Git.

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
