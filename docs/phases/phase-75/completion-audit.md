# Phase75 completion audit

Phase75 owns the formatter follow-ups, editor diagnostics with `pietto lsp`
and partial analysis, diagnostic hints, the Python compile API, the relation
column view and the retirement of header lines (row 75 of the
[Future Roadmap v6](../../roadmap.md#future-roadmap-v6)). This audit checks
the closure conditions of its [route](route.md) on the integrated batch-2
tree. It publishes nothing: live `main` and its natural exact-head CI remain
the lifecycle authority, and the [Phase76 handoff](phase76-handoff.md) lists
what moves on.

## Baseline and batches

| Step | Fact |
| --- | --- |
| Gate 0 | `main` at the Phase74 completion commit `24645b36afa0dce61c1ceaae2be496bdd9366d3d` (tree `22b2b05a04158a7a17b79479c73a05ee41fda8a6`); natural exact-head CI `42316298753` attempt 1 accepted all 21 jobs. A provisional Gate 0 on the Phase72 batch-2 integration tree `9cd8007b` came first, under the owner's answers of 2026-11-05 that let the first Phase75 lines start beside Phase74 (J13). The lines were built on that tree, on `bca733bb`, `3d37449b` and `ac4d18ae`, and on Phase74 trees, and were replayed onto `main` (see "Failed histories kept"). The rebind witnesses are the ones D75 records: the compile API is byte-equal to `emit-sql --project`, the column view keeps the relation sequence and single-file parity, `check --project` is byte-equal before and after partial analysis, and partial analysis obeys the restriction law against `[sources].exclude`. There was no separate probe run. |
| Gate 1 | D75.01–D75.18 in the [decision record](../../decisions.md#phase75--owner-decisions-2026-11-05-to-2026-11-07). On 2026-11-05 the owner chose the names of the compile API and the column view; on 2026-11-06 the owner answered the editor questions and named a client; on 2026-11-07 the owner answered the Gate 1 questions with the lead's recommendations, except that the VS Code acceptance runs with the owner's own extension, which takes its diagnostics from `pietto lsp` (D75.13, D75.15). Budget C120/F350/D1500/S10 (D75.18). |
| Batch 1 | Ten commits on `24645b36`: the route publication `052370a5`, S01 `2f358639` (relation columns), S02 `f9cea095` (compile API), S03 `cecdeb4e` (`fmt --project`), S04 `89251785` (header lines), the first S05 commit `b964d113` (`emit-sql --help`, the capability page, the documentation fmt gate), S06 `d6f0ce03` (partial analysis), S07 `8fb0f560` (`pietto lsp`), the second S05 commit `832e2de5` (the D8 hints and the named `Decimal` rule) and the Phase74 follow-up `ff1aa713` (below), ending at `ff1aa71389cacf6eb43ed5c94df53246f7f84eae` (tree `db2fbbaadd2a6c8365c6ee40ecd6466a2a0613d6`). One Gate 2 on that tree (27,091 passed, 41 skipped; goldens, generated files and the package smoke passed, the tree equal before and after). The VS Code acceptance passed against a wheel built from that tree before the push (§3). Natural exact-head CI `42333099891` attempt 1 accepted all 21 jobs. No slice changed a compiled record. |
| The tenth batch-1 commit | `ff1aa713` is a Phase74 follow-up, recorded here as the Phase74 audit recorded its S04 follow-up. In a `schema_version = 2` project, a `first` or `last` over a `let` name beside a let/projection name conflict (PIE-S2329) reported a false PIE-S2315 that a single file does not. The project check now reads the `let` scope as a single file does. The route keeps its nine-commit plan; the fix rides batch 1 as its tenth commit (lead decision, 2026-11-07). Witness: `test_semantic_aggregate_ordered_value.py::test_a_schema_version_2_project_reports_what_a_file_does` (its `let`-conflict bodies). |
| Midpoint | At the batch-1 head `ff1aa713`: S01–S07 are on `main`. The new editor and partial-analysis owners `test_cli_lsp.py`, `test_project_check_partial.py` and `test_project_editor_overlays.py` are in the Windows selector `tests/test_{parser,semantic,ir,plan,sql,project,cli,results}_*.py`, so the Windows jobs of run `42333099891`, which accepted all 21 jobs on attempt 1, ran them. The VS Code acceptance passed on the B1 candidate before the push and again on the B1 head (§3). The lane tallies project inside the caps (Budget). The batch-1 natural CI is the midpoint CI reading. |
| Batch 2 | Five commits on `ff1aa713`: S08 (one fmt spelling), S09 (the second whole-tree test pass and the acquisition consolidation), the S01 follow-up that names the declaring module of `enum` and `shape` column types (B1 audit item B1-1, accepted on 2026-11-07), this audit (S10) and the `0.1.10` release commit, in that order. One Gate 2 on the final tree; Phase75 closes when its head passes natural exact-head CI. `0.1.10` carries Phase73, Phase74 and Phase75 (D75.16); its release commit changes only version owners and documentation, and the owner approved its publication chain on 2026-11-07. `VERSIONS` stays `(7, 1, 7, 1)` (D75.17). |

## Closure conditions

### 1. The lines are delivered

- 75-V: `pietto explain --project ROOT` on a `schema_version = 2` project
  lists the output columns of each table and query, in the order of
  `emit-sql --project --all`, as text or as the alpha JSON document
  `pietto.project-relation-columns.v1` (D75.01). A column has a name, a type
  `{kind, name}` and a nullability `non_null`, `nullable` or `unknown`.
- 75-A: `pietto.compiler.compile_sql` and `compile_all_sql` return
  `SqlEmission(status, document)`, byte-equal to
  `pietto emit-sql --project ... --format json` with the same arguments
  (D75.02).
- 75-F: `pietto fmt --project ROOT` with `--check` or `--write` (D75.04); the
  fmt gate over every `pietto` block of `README.md` and `docs/*.md` (D75.08);
  one spelling for strings, one-line import and export lists and `order by`
  keys, with both spellings still accepted and no warning (D75.05, S08).
- 75-H: every header line is refused with PIE-P1000 and a hint for that line,
  in every command, check mode and dependency package; `migrate` still deletes
  them; PIE-P1012 is retired and not reused (D75.06).
- 75-D: `pietto emit-sql --help` names the project batch form;
  [`docs/capabilities.md`](../../capabilities.md) is the hand-kept capability
  page; the hints for the eight implicit rules of the external audit D8 and the
  named `Decimal` rule of PIE-S2105 change message and suggestion text only
  (D75.08).
- 75-E: `pietto lsp` over standard input and output, diagnostics only,
  standard library only (D75.09); editor buffers as their own type (D75.10);
  editor partial analysis in `schema_version = 2` roots, at most five passes
  (D75.11); five editor-only messages without a PIE code (D75.12).

### 2. Acceptance

Phase75 changes no SQL output, so a project form needs no new emission,
compiled-bundle or live-template witness. Each row names the layers its
witnesses observe.

| Slice | Admitted, with its layers | Refused exactly |
| --- | --- | --- |
| S01 relation columns | Project semantic: `test_project_relation_columns.py::test_every_table_and_query_lists_its_columns_as_computed`, `::test_relations_follow_the_emit_sql_batch_item_sequence`, `::test_columns_agree_with_single_file_explain_on_flat_relations`. CLI text and JSON: `test_cli_project_explain.py::test_schema2_project_writes_relation_columns_in_json_and_text`, `::test_the_schema_2_decision_and_the_parsed_project_come_from_one_read`; the batch-2 module follow-up: `test_project_relation_columns.py::test_an_enum_or_shape_type_names_the_module_that_declares_it`, `::test_two_enums_of_one_name_differ_by_their_modules`, `::test_an_enum_whose_declaring_module_is_not_proven_is_unavailable` | `test_project_relation_columns.py::test_a_failure_publishes_no_relations`, `::test_a_completion_that_raises_is_reported_without_relations`; `test_cli_project_explain.py::test_schema2_failures_keep_stdout_empty_in_text_and_null_relations_in_json`, `::test_a_configuration_that_fails_before_dispatch_keeps_the_v1_document`, `::test_a_configuration_rewritten_to_schema_2_after_routing_is_refused` |
| S02 compile API | Python API against the command bytes: `test_sql_compile_api.py::test_single_emission_is_the_command_document`, `::test_both_literal_policies_and_a_path_object_root`, `::test_batch_is_the_command_batch_in_authority_order`, `::test_a_verified_emission_needs_no_execution_template`, `::test_calls_are_independent_and_write_nothing`, `::test_a_real_child_process_prints_the_same_bytes` | `test_sql_compile_api.py::test_rejected_values_are_returned_documents`, `::test_option_like_values_stay_values`, `::test_batch_keeps_every_outcome_and_rejects_an_empty_match`, `::test_batch_output_limit_is_a_returned_document`, `::test_wrong_python_types_raise_before_the_project_is_read`, `::test_internal_errors_propagate_and_unencodable_output_raises` |
| S03 `fmt --project` | Parser layout: `test_parser_format.py::test_project_fmt_lays_out_each_module_as_fmt_lays_out_one_file`. CLI: `test_cli_format.py::test_fmt_project_checks_and_rewrites_every_module_in_module_order` | `test_cli_format.py::test_fmt_project_refuses_the_whole_project_as_check_reports_its_parser_errors`, `::test_fmt_project_refuses_the_whole_project_when_one_module_cannot_be_formatted`, `::test_fmt_project_write_refuses_a_symbolic_link_module` (an oversize link included), `::test_fmt_project_write_writes_no_module_when_one_cannot_be_replaced`, `::test_fmt_project_write_refuses_a_module_changed_after_it_was_read`, `::test_fmt_project_reports_project_errors_as_check_does`, `::test_fmt_project_refuses_another_schema_version_with_a_hint`, `::test_fmt_project_usage_errors`, `::test_fmt_needs_a_path_or_a_project` |
| S04 header lines | `migrate` still reads and deletes them: `test_parser_source_migration.py::test_a_digit_separator_in_the_header_number_proves_modern_source` and the migration owners | Parser: `test_parser_basic.py::test_each_header_line_is_refused_with_its_hint`, `::test_a_header_line_is_refused_with_every_other_retired_spelling`. CLI, every check mode, single file and project: `test_cli_check_mode.py::test_each_header_line_is_refused_in_a_single_file_and_a_project`, `::test_a_header_line_is_refused_in_text_output_whatever_the_check_mode`. Packages: `test_project_explain_runtime.py::test_header_lines_are_refused_in_the_package_root_and_its_dependencies` |
| S05 help, capability page, hints | CLI: `test_cli_project_emit_sql.py::test_batch_help_is_explicit_and_does_not_change_single_help`. Documentation fmt gate: `test_repo_docs_examples.py::test_documented_example_is_already_formatted` over `README.md` and `docs/*.md`. The accepted routes the hints name: `test_semantic_let_binding_group_by_keys.py::test_the_two_query_route_the_computed_key_hint_names_is_accepted`, `test_semantic_sum_avg_semantics.py::test_round_of_an_avg_names_the_two_query_route_that_is_accepted`, `test_semantic_decimal_scalar_expression_semantics.py::test_decimal_sign_rewrite_named_by_s2105_is_accepted`. `docs/capabilities.md` is probed, not tested (D75.08) | The same codes, locations and order with the new text, message and JSON suggestion: `test_semantic_functions.py::test_date_trunc_refusals_name_the_quoted_unit`, `::test_round_refusals_name_the_decimal_digits`, `test_semantic_decimal_scalar_expression_semantics.py::test_decimal_rule_reaches_json_suggestion_in_file_and_project` (PIE-S2105), `test_cli_project_emit_sql.py::test_a_plain_decimal_field_names_the_decimal_type_to_declare` (PIE-B1004) |
| S06 partial analysis | Project check: `test_project_check_partial.py::test_partial_analysis_checks_past_each_stop_by_the_three_laws`, `::test_a_check_that_completes_reports_what_the_cli_reports` | The command line stays all or nothing: `test_project_check_partial.py::test_the_cli_check_still_stops_at_its_first_stop`, `::test_a_check_without_modules_to_leave_out_is_the_cli_check` |
| S07 `pietto lsp` | Editor protocol over a process: `test_cli_lsp.py::test_lifecycle_over_a_process` (full document sync, nothing else advertised), `::test_single_file_diagnostics_equal_check_json`, `::test_root_publishes_open_and_closed_modules`, `::test_overlays_follow_the_buffer_and_write_nothing`, `::test_positions_count_utf16_units_against_the_shown_text`, `::test_file_uris_map_to_paths`, `::test_versions_increase_and_the_last_publish_is_the_last_version`, `::test_a_result_made_stale_while_checking_is_dropped`, `::test_a_suggestion_the_message_already_carries_is_shown_once`. Editor buffers in the project check: `test_project_editor_overlays.py::test_an_overlay_replaces_only_the_read_of_its_selected_file`, `::test_the_report_without_overlays_is_the_cli_project_check`. The five editor-only messages: `test_cli_lsp.py::test_overlapping_roots_publish_only_the_overlap_error`, `::test_a_file_open_under_two_uris_gets_only_the_alias_error`, `::test_two_selected_names_of_one_path_get_only_the_names_error`, `::test_a_module_left_out_says_which_import_has_errors`, `::test_a_ranged_change_is_refused_until_the_file_reopens`. Installed CLI: `test_release_packaging_smoke.py::test_installed_lsp_smoke_requires_the_exact_round_trip` | `test_cli_lsp.py::test_protocol_errors_over_a_process`, `::test_project_roots_must_be_distinct_absolute_paths`, `::test_two_spellings_of_one_root_directory_are_not_distinct`; a buffer refused by type: `test_project_editor_overlays.py::test_emission_refuses_an_overlay_by_type_even_with_the_disk_text`, `::test_a_compiled_build_refuses_an_overlay_by_type_past_emission`, `::test_a_package_graph_refuses_overlay_lineage_by_type` |
| S08 one fmt spelling | Parser layout and the AST, check and SQL laws: `test_parser_format.py::test_formatting_writes_one_spelling_of_strings_lists_and_order`, `::test_both_quotes_read_each_escaped_quote_as_the_quote`, `::test_first_and_last_lose_their_asc_and_keep_check_and_sql`, `::test_corpus_formatting_is_idempotent_and_keeps_comments_ast_and_output` (each fixture also written with single quotes and explicit `asc`), `::test_project_fmt_lays_out_each_module_as_fmt_lays_out_one_file` | The spellings fmt does not choose stay as written (J16): `test_parser_format.py::test_formatting_keeps_the_spellings_it_does_not_choose` |
| S09 whole-tree pass | The naming law: `test_repo_test_layout.py::test_tests_and_helpers_are_named_by_area_without_history_words`, `::test_the_naming_law_reads_history_words_in_any_case_or_number`. The receipt memo: `test_harness_target_conformance.py::test_receipt_verification_validates_each_distinct_public_artifact_once`. The restored scanner mutation families in `test_repo_reader_acquisition.py` (§7) | The recorded exceptions of the naming law, by name (§7) |

Each new fmt rule, hint and editor message is in [style](../../style.md),
[language](../../language.md), [editor LSP](../../editor-lsp.md) or the
[release notes](../../release-notes.md), with every exact new text.

### 3. VS Code acceptance

The acceptance ran the owner's extension, changed in its own repository to
take its diagnostics from `pietto lsp` (D75.13), in VS Code 1.145.2 through
the extension's own test host.

| Run | Wheel | Result |
| --- | --- | --- |
| B1 candidate, before the push (2026-11-07 02:56–02:59 UTC) | built from tree `db2fbbaa` | PASS: `npm ci`, build and lint; unit tests 23 of 23 with the 15 snippets checked by the CLI; host tests 11 of 11 against the real `pietto lsp`; the restricted-workspace run; the VSIX host run 11 of 11; the VSIX `da086ffb...` byte-identical when packaged again; no `pietto lsp` or stand-in process left |
| B1 head, after the push (2026-11-07 03:36–03:39 UTC) | built from the head `ff1aa713`, byte-identical to the candidate's wheel | PASS: `npm ci`, build and lint; unit tests 23 of 23 with the snippets checked by the CLI; host tests 11 of 11 against the real `pietto lsp`; the restricted-workspace run; the VSIX host run 11 of 11; the same VSIX `da086ffb...`, byte-identical when packaged again; no `pietto lsp` or stand-in process left |

Not run in the editor: native Windows Python, the Windows desktop `wsl.exe`
launcher, a Remote WSL session, macOS and the oldest admitted VS Code; and
four of the five editor-only messages, whose behaviour the `test_cli_lsp.py`
rows of §2 cover. The extension's change is made, reviewed and pushed in its
own repository, with no tag and no Marketplace release (D75.13); its README
links `docs/editor-lsp.md` on `main`, so it is pushed after batch 1.

### 4. What Phase75 leaves unchanged

- No SQL output, grammar, IR or compiled record changed: `check_goldens`
  verifies the same 41 fixtures, `check_generated` the same eight generated
  files, and `VERSIONS` stays `(7, 1, 7, 1)` (D75.17). Phase75 has no
  real-database run.
- `pietto check --project` stays all or nothing, byte for byte (S06 row of
  §2), and a report without editor buffers is the command-line check
  (`test_project_editor_overlays.py::test_the_report_without_overlays_is_the_cli_project_check`).
- No new PIE code. PIE-P1012 is retired and its code is not reused; the D8
  hints and PIE-S2105 change text only, and the release notes list each
  text before and after.
- `fmt` accepts both spellings of every S08 rule with no warning; `table` and
  `query`, `1_000`, one-line and block forms, chained comparisons and other
  trailing commas are left as written (D75.05, D75.07).

### 5. Deferrals stay refused

Each "Not included" item of the route keeps its refusal or stays absent:
schema-4 and source columns are not listed, and a column the compiler did not
prove fails the whole document (S01 row); there is no `compile_queries`, no
cache and no single-file Python entry (D75.03); `fmt` has no partial
formatting, line width, style option, JSON output or new code; the grammar
keeps the header rule for the PIE-P1000 refusal and `migrate`, and
`migrate` has no in-place flag
(`test_cli_source_migration.py::test_migrate_requires_input_and_has_no_in_place_flag`);
the D8 rules keep their refusals with the same codes (S05 row); `pietto lsp`
advertises full document sync and nothing else, sends no PIE-B... refusal and
discovers no root (S07 row).

### 6. Windows

The Windows jobs collect `tests/test_{parser,semantic,ir,plan,sql,project,cli,results}_*.py`.
Batch 1's new owners are in that set. A case that renames a module to a
non-UTF-8 bytes path skips where the file system refuses such a name, as the
emission owner already did, because Windows decodes bytes paths as strict
UTF-8; and the test of two
selected names that differ only in letter case skips on a file system that
ignores letter case, so its witness is the Linux run with a case-folding path
type. S09 moves tests into the selector: 22,087 Windows-collected nodes on
the S08 tree become 22,417 (S09's replayed merge +80; the parser renames of
the post-replay pass +250). Natural Windows CI owns them; a red Windows head
gets a repair child.

### 7. The second whole-tree test pass and the acquisition consolidation

S09 is the second whole-tree pass, due by the Phase75 close. Three lanes
built it on `main` at `24645b36` while batch 1 was replayed, leaving alone
the 96 files that Phase75 touched; an independent verifier found no blocking
defect, and its seven minor items were handled at their root cause. The
merged candidate (tree `0e7829db`) was applied onto the S08 tree with a
three-way apply; it shares no path with Phase75, and its changed lines are
the candidate's, line for line. The post-replay pass then placed the touched
files: `test_diagnostics.py` and `test_resource_budgets.py` became
`test_parser_diagnostics.py` and `test_parser_resource_budgets.py`,
`test_semantic_scaffold.py` became `test_semantic_api.py`, and six files
merged into their owners (`test_cli_json_completion_audit.py` into
`test_cli_json.py`, `test_cli_completion_audit.py` into `test_cli_check.py`,
and the aggregate readiness, candidate-decision and `Decimal` contract files
into the aggregate semantic owners), with the capability evidence repointed
and every assertion kept.

- Naming law: every Python file under `tests/` sits at its top level, every
  `tests/test_*.py` starts with `test_<area>_`, every helper with
  `_pietto_<area>_`, and no word of a name is a history word, in any letter
  case or with a plural `s`. The
  recorded exceptions are named in the test: `test_sql_emission_closure.py`
  (named by a `ci/workloads.toml` cost entry), the four
  `_pietto_differential_*` helpers, the five `_pietto_target_conformance*`
  helpers and `_pietto_mysql_native_prepared.py` (loaded with that family).
  The law compares sets, so a new violation or a stale exception fails it.
- Collection: 27,160 nodes on the S08 tree, 27,112 after S09 (-49 from the
  replayed merge and +1 for the naming law's own test; the post-replay pass
  moves 283 node ids and renames 22, so it keeps the count). Every one of the
  1,267 removed node ids is mapped: 1,099 moved, 81 renamed (a history word
  dropped from the function name: 59 in the replayed merge, 22 in the
  post-replay pass), 59 folded into a named holder and 28 deleted as prose,
  route or count locks. The 33 added ids without a source are the 31 restored
  scanner mutation nodes (a Phase72 change had turned their file into a
  helper, so they were no longer collected), the receipt memo test and the
  naming law's test. Test files go from 612 to 571; the 166 helpers stay,
  four of them renamed by area.
- Acquisition: `verify_receipt` validates each distinct public artifact once
  per receipt (F4, with an op-count test); twelve hand-built preludes use
  `parameterized_fixture` with byte-identical sources and contracts (O4); the
  sixth temporal prelude of `test_sql_project_scalar_expressions.py` is one
  in-file builder (K3); the bare-code and suffix scans are one repository
  scan. F3, the round-robin placement that builds a module fixture in up to
  three CI shards, is placement policy and is recorded only. The bounded
  ten-slowest profile on Phase75's final natural CI health is not done; it
  moves to the [Phase76 handoff](phase76-handoff.md#acquisition-debt).

### 8. Decisions, audit, handoff and lessons

The [decision record](../../decisions.md#phase75--owner-decisions-2026-11-05-to-2026-11-07)
holds D75.01–D75.18. This audit, the [Phase76 handoff](phase76-handoff.md)
and the Phase75 section of the
[engineering lessons](../../references/engineering-lessons.md#phase75) are in
the S10 commit.

## Budget

| Account | Cap | Use |
| --- | --- | --- |
| Phase75 (S01–S10) | C120 / F350 / D1500 / S10 | recorded lane tallies: the lines before the route about C40, F74 and D308 (columns, compile API, `fmt --project`, header lines, polish, D8 hints, the LSP design, partial analysis, the LSP repair run, the first integration and the first replay); the second replay with its verifier round and its overlay lane about C11, F18 and D82; the `Decimal` message lane C2, F5 and about D43; S08 with its verifier round C3, F10 and D49; the PIE-S2315 follow-up two candidates (C2); S09 (three lanes, the merge and the verifier disposition) about C4, F24 and D216; the third replay with its verifier round and the batch-1 audit repairs about C20, F25 and D154; the batch-2 assembly with its audit repairs C6, F19 and about D130; about C82, F156 and D852 before the batch-2 assembly. Not recorded: the earliest LSP runs, the design and verifier workflows and the extension's own lanes. No real-database run. The ten route slices are unchanged; no scope-repair slice was added. No cap was reached |

## Failed histories kept

- The lines were replayed onto `main` three times. The first replay sat on an
  older Phase74 replay and was superseded. The second was built on the
  Phase74 batch-1 tree before that batch's audit repairs; its verifier's
  blocking finding was the stale base. The third replay, onto the Phase74
  completion tree, is batch 1. Two earlier series of it were superseded: one
  built on an earlier Phase74 tree (`6529cc5a`), and one from before the
  PIE-S2315 follow-up and the batch-1 audit repairs.
- The batch-1 audit (two rounds over three areas) confirmed nine defects, each
  fixed in the step that introduced it. The high one: `pietto lsp` published a
  module's diagnostics under one URI spelling and then cleared the other
  spelling of the same file, which VS Code shows as one resource, so the
  diagnostics vanished on Windows. The others: a percent-encoded `\\wsl$` host,
  an oversize symbolic-link module in `fmt --project --write`, the
  `initializationOptions` shapes, two `projectRoots` naming one directory,
  the unscoped partial-analysis documentation, two diagnostic rows and the
  release-note wording. The `enum`/`shape` module identity in the column view
  went to the owner and was added in batch 2: those type objects now carry
  `module`, the declaring module.
- The PIE-S2315 follow-up needed a second candidate after its verifier.
- S09's verifier found the 31 uncollected scanner mutation nodes, which were
  restored as collected tests; the first merged candidate had dropped them as
  dead copies.
- The first integration found that the Windows jobs, added on `main` after the
  lanes started, could not run a bytes-path case; it now skips where the file
  system refuses that name.
- The extension's snippet check passed by skipping when its interpreter was
  not set; it now fails instead. The generic LSP client that the Phase75 plan
  first named was replaced by the owner's extension (D75.13).
