# Phase73 completion audit

Phase73 owns the explicit two-level aggregation route, conditional and list
aggregates, per-group detail lists, nested GROUP BY and DISTINCT keys and the
small scalar features, plus the owner's additions of 2026-11-05 (row 73 of
the [Future Roadmap v6](../../roadmap.md#future-roadmap-v6)). This audit
checks the closure conditions of its [route](route.md) on the integrated
batch-3 tree. It publishes nothing: live `main` and its natural exact-head CI
remain the lifecycle authority, and the [Phase74 handoff](phase74-handoff.md)
lists what moves on.

## Baseline and batches

| Step | Fact |
| --- | --- |
| Gate 0 | Under the owner's answer of 2026-11-05 that let Phase73 start before Phase72 closed, a provisional Gate 0 ran the read-only probes on the Phase72 batch-2 integration tree. It was rebound to `main` at the `0.1.9` release commit `bca733bbd18ef08cdf5a794ae3c0bbc3f1a85b33` (tag `v0.1.9`, tree `161769de93428fcbd11b134a50b0d2134bc37a33`); natural exact-head CI `42090026718` attempt 1 accepted all 19 jobs. |
| Gate 1 | On 2026-11-05 the owner accepted every recommendation: D73.01–D73.19 in the [decision record](../../decisions.md#phase73--owner-decisions-2026-11-05), the budget C180/F600/D2400/S11, and the conditional-aggregate spelling table with its defaults. The same day the owner added S14–S17; with their caps the budget is C225/F720/D3060/S11. Later the same day the owner made Phase73–75 one release, `0.1.10` (D73.15). |
| Batch 1 | Six commits on `bca733bb`: the route publication `c12d7d2b`, S01 `882174f0`, S02 `58771344`, S03 `18dce679`, S04 `c07819b5` and S05 `ac4d18ae017293c1ab4c14dd969bb8e4df9ce2c1` (tree `0c073795018d11a5caf9c352cc7a00d622c9d3b9`). One Gate 2 on that tree (25,980 passed, 41 skipped); natural exact-head CI `42148220359` attempt 1 accepted all 19 jobs. |
| Midpoint | At the batch-1 head: nested-key witnesses existed at three layers on PostgreSQL, with their database run; the generator grammar was on `main`; no batch-1 slice changed a compiled record, so the one compiled `VERSIONS` change waited for batch 2; the lane tallies projected well inside the caps; the batch-1 natural CI (run `42148220359`) is the midpoint CI reading. The owner asked for fewer repair rounds the same day, so the remaining slices were integrated with one loop-until-dry batch audit instead of further per-lane review rounds, except for new grammar or semantic work. |
| Batch 2 | Nine commits, S14, S16, S17, S15, S08, S09, S10, S11 and S07 with the repairs of one batch audit, rebased onto the Windows CI maintenance `e961ddb6` and ending at `3caa5e6c4aa61417c60c21d1e2a669a9ef3c923b` (tree `3f6f6d9434eae7653b7152026007c1c5ccaee1f4`). S14 carries the single compiled `VERSIONS` change of the phase, `(6, 1, 6, 1)` to `(7, 1, 7, 1)` (D73.16); S17, S09 and S11 add their record changes under it. One Gate 2 on that tree (26,293 passed, 41 skipped); natural exact-head CI `42232536210` accepted all 21 jobs, the two Windows jobs included. |
| Batch 3 | Seven commits: the Windows `ctime` test parameter (the Windows 3.12 job of CI `42230229990` failed on it), S06, S02P (project conditional aggregates), the single-file MySQL conditional count after its database run, one shared node walk per parsed script (F6 and F7), S12 (the [worked example](../../worked-example.md) and the acquisition consolidation) and this audit (S13), ending at `b148fdeee68f563a3e759c7121a1eaee72a9632c` (tree `0f12d466c6392479966d9f5ac4403abaecf24040`). S06 and S02P add their record changes under the same `VERSIONS` value. No version change: `0.1.10` is cut after Phase75 closes (D73.15). One Gate 2 on that tree (26,400 passed, 41 skipped). Its natural exact-head CI `42272513354` failed only on Windows 3.12, in one test that forced a comparable `ctime`; that head is kept and was not rerun. Its repair child `37143dcb00694ad5b7e23a1f4e928ecafa23b185` (tree `d93f939363d335b4fa4f38812597ac185eb25849`), which runs that case on POSIX only, passed its Gate 2 (26,401 passed, 41 skipped) and natural exact-head CI `42277807557` attempt 1 on all 21 jobs, and closed Phase73. |

## Closure conditions

### 1. T-K and T-G are delivered

- T-K: an EXPLICIT_MODULES project groups and deduplicates by a collected
  list on PostgreSQL. The key is admitted only when the collected `let` is
  ordered by keys that end in a proved unique key; elements are compared
  after decoding with `same_value` (D73.05). Nested `==`, ORDER BY and
  set-operation dedup stay refused (D73.06).
- T-G: the per-group detail route needs no new spelling. A query groups;
  another reads it with `from` and collects a `let` that captures it, reads
  the same input and matches each key with `same_value`, so a None-key group
  gets its own rows. PIE-S2803 now suggests the route.

The owner did not reopen C1 or C5, so T-K and T-G are delivered as Gate 1
narrowed them.

### 2. Acceptance rows

Each project form needs an emission, a compiled-bundle and a live-template
witness; a single-file form needs only the emission layer. "E" is emission,
"C" the compiled bundle and "L" the live template. Each refusal test pins a
diagnostic code with its text, or the blocker detail of an emission refusal.

| Row | Admitted, with its layers | Refused exactly |
| --- | --- | --- |
| A01 two-level route | E: `test_sql_join_emission.py::test_the_two_level_route_counts_per_key_then_sums_per_group` (single file, both dialects), `test_sql_joins.py::test_the_two_level_route_counts_per_key_then_sums_on_postgresql_only` (project). C and L: `test_execution_compiled_bundle.py::test_the_two_level_route_template_renders_the_emitted_sql` (one node binds the loaded bundle and the live template) | without the declared unique key the first query is PIE-S2381; project MySQL is blocked by two PIE-B1004 `sum_int_aggregate_range_proof_missing` (same project test) |
| A02 PIE-S2381 names the route; D11-04 keeps PIE-S2381 with the hint (D73.11) | E: `test_semantic_join_grouping.py::test_joined_aggregates_admit_exactly_their_proved_rows` (case `avg_in_two_levels` admits the route in both modes) | the same test: `avg_by_the_repeating_key` (D11-04) and `avg_by_a_non_key` (D11-05) end with the fixed route sentence; no new code, and the project PIE-S2333 cause is unchanged |
| A03 conditional count and sum | Single file, E: `test_sql_conditional_aggregates.py::test_postgres_counts_and_adds_the_rows_whose_test_is_true`, MySQL count `::test_mysql_counts_with_the_same_case_form`, `test_semantic_conditional_aggregates.py::test_a_group_generator_sum_is_a_non_none_int`, `::test_an_aggregate_query_without_group_by_reads_its_whole_input_as_a_group`, `test_ir_aggregate_expression_argument_ir.py::test_group_generators_lower_to_the_filtered_aggregate_identities`. `schema_version = 2` project (S02P): check `test_project_grouped_aggregate_project_row_schema.py::test_a_schema_version_2_project_checks_the_conditional_count_and_sum`; E `test_sql_conditional_aggregates.py::test_a_project_emits_the_conditional_count_and_sum_on_postgres`, `test_harness_sql_emission_portability.py::test_conditional_count_and_sum_are_closed_data_relations`; C `test_execution_compiled_families.py::test_postgresql_conditional_count_and_sum_replay_from_compiled_input`; L `test_execution_compiled_bundle.py::test_a_conditional_count_and_sum_template_binds_its_header_read` | `test_semantic_conditional_aggregates.py::test_each_refused_generator_reports_its_first_broken_rule`, `::test_any_over_group_keeps_its_error_and_names_the_conditional_count`, `::test_count_of_a_bool_field_warns_that_false_counts_too` (PIE-S2388); MySQL `test_sql_conditional_aggregates.py::test_mysql_refuses_the_conditional_sum`; projects `test_project_grouped_aggregate_project_row_schema.py::test_a_project_refuses_a_generator_as_a_single_file_does`, `::test_a_schema_version_1_project_has_no_generator`, `::test_a_generator_test_reads_no_let`, `test_sql_conditional_aggregates.py::test_a_project_refuses_a_test_that_reads_no_field`, `test_execution_compiled_families.py::test_a_compiled_conditional_aggregate_keeps_its_signature`; MySQL projects `test_sql_conditional_aggregates.py::test_a_project_refuses_the_conditional_count_and_sum_on_mysql` |
| A04 constants and `--set` (single file) | E: `test_sql_constants.py::test_each_read_emits_its_literal_of_the_declared_type`, `::test_set_values_emit_the_bytes_of_the_same_source_values`, `test_cli_constants.py::test_set_emits_the_bytes_of_the_value_written_in_the_source`, `::test_check_and_explain_read_the_set_value` | `test_cli_constants.py::test_text_usage_errors_exit_two_with_their_exact_text`, `::test_json_usage_errors_are_cli_errors`, `::test_migrate_and_project_emission_refuse_set`, `test_semantic_constants.py::test_declarations_that_are_not_one_literal_of_a_constant_type`, `test_project_query_parameters.py::test_a_top_level_constant_is_refused_in_a_project`; MySQL `test_cli_constants.py::test_mysql_refuses_each_relation_that_reads_a_constant` |
| A05 project parameters `Decimal(p, s)`, `Date`, `Timestamp`, `UUID` | E: `test_sql_query_parameters.py::test_typed_parameters_cast_to_their_source_carrier_on_postgresql`, `::test_a_decimal_parameter_keeps_the_existing_decimal_laws`. C: `test_execution_compiled_bundle.py::test_a_typed_root_records_each_parameter_kind_and_its_decimal_carrier`. L and binding: `test_execution_binding.py::test_a_typed_witness_binds_to_its_canonical_text_arguments`, `test_execution_api_postgres_adbc.py::test_adbc_submits_a_typed_parameter_as_its_canonical_text`. Save, R1 and export: `test_jobs_store.py::test_typed_parameters_store_their_canonical_text_and_rebind_by_value`, `test_jobs_saved_replay.py::test_r1_and_verified_export_restate_typed_parameters_by_value` | `test_execution_binding.py::test_a_typed_value_is_checked_by_its_binding`, `test_jobs_store.py::test_a_damaged_typed_parameter_vector_is_a_typed_refusal`; an earlier compiled version is `COMPILED_COMPATIBILITY` (`test_execution_compiled_bundle.py::test_a_description_of_an_earlier_version_is_refused`); MySQL `test_sql_query_parameters.py::test_mysql_refuses_each_typed_parameter_at_its_declaration` (D73.14) |
| A06 `max(a, b)`, `min(a, b)` | E: `test_sql_postgres_relations.py::test_max_and_min_emit_the_conditional_that_is_none_when_either_value_is`, the same test in `test_sql_mysql_relations.py`. C and L: `test_execution_compiled_families.py::test_max_and_min_of_two_values_emit_replay_and_bind_one_statement`, `::test_max_and_min_of_two_timestamps_or_uuids_emit_replay_and_bind` | `test_semantic_functions.py::test_max_and_min_refuse_none_values_that_do_not_compare_and_more_arguments`, `::test_a_same_file_callable_named_max_or_min_keeps_the_meaning_it_had`; MySQL `Bool` `test_sql_mysql_relations.py::test_max_and_min_of_two_bool_values_stay_refused` |
| A07 `lpad`, `add_months` | E: `test_sql_postgres_expressions.py::test_lpad_never_truncates_and_add_months_clamps`, `test_sql_mysql_expressions.py::test_lpad_keeps_a_longer_text_and_add_months_is_date_add`, `test_sql_project_scalar_expressions.py::test_postgres_lpad_and_add_months_project_forms_are_verified`. C and L: `test_execution_compiled_bundle.py::test_lpad_and_add_months_templates_render_the_emitted_sql` | `test_semantic_functions.py::test_lpad_and_add_months_refuse_their_variants`, `test_sql_project_scalar_expressions.py::test_postgres_lpad_refuses_a_width_outside_int4`, `::test_mysql_project_sql_refuses_lpad_and_add_months` |
| A08 window keys that name a computed `let` (the sub-form list the lead reviewed, D73.10) | E: `test_sql_windows.py::test_window_keys_read_the_columns_of_computed_lets`, `test_ir_window_dual_backend_lowering.py::test_window_keys_naming_computed_lets_lower_to_their_values`. C and L: `test_execution_compiled_bundle.py::test_windows_over_computed_let_keys_bind_and_render_the_emitted_sql` | `test_project_window_grouped_result_inputs.py::test_a_window_key_naming_no_computed_value_stays_refused`, `test_parser_window_syntax.py::test_a_window_value_as_an_expression_operand_stays_a_syntax_error`; MySQL computed `Text` key `test_ir_window_dual_backend_lowering.py::test_mysql_refuses_a_computed_text_window_key` |
| A09 `now()` | E: `test_semantic_functions.py::test_now_is_a_never_none_timestamp_in_select_items_and_where`, `test_sql_postgres_expressions.py::test_now_is_the_statement_start_in_utc_whatever_the_session_time_zone`. C and L: `test_sql_project_scalar_expressions.py::test_now_is_one_utc_statement_snapshot_evaluated_at_execution` (no value enters a compiled byte) | `test_semantic_functions.py::test_now_outside_select_items_and_where_is_refused_where_it_stands`, `::test_now_takes_no_argument`, `test_project_json_v2_semantic_diagnostics.py::test_a_project_refuses_now_where_a_single_file_does`, `test_project_r2_proposal.py::test_r2_refuses_a_now_read_before_any_workspace`, `test_execution_api_live_relay.py::test_relay_refuses_a_now_read_before_the_sink_or_workspace`, `test_semantic_constants.py::test_a_constant_value_is_never_now_and_never_named_like_a_new_builtin` |
| A10 nested GROUP BY and DISTINCT keys | E: `test_sql_nested_relations.py::test_a_nested_key_is_compared_by_each_carrier_on_postgres_only`. C and L: `test_execution_nested_relations.py::test_a_nested_key_bundle_lowers_to_the_live_statement` | `test_project_nested_relation_facts.py::test_a_nested_key_needs_a_collected_order_without_ties`, `::test_a_nested_key_keeps_its_refusal_beside_a_join`, `::test_a_nested_key_keeps_the_refusals_of_its_body`, `test_sql_nested_relations.py::test_a_carried_nested_field_stays_blocked_beside_any_reader`; MySQL in the first test |
| A11 `len`, `sum`, `any` over a collected list | Check: `test_project_list_operations.py::test_each_list_operation_checks_with_its_type`, `::test_a_container_that_may_be_missing_makes_each_result_nullable`. E: `test_sql_nested_relations.py::test_a_list_operation_reads_its_rows_collect_carrier`. C and L: `test_execution_nested_relations.py::test_a_list_operation_compiles_and_its_bundle_loads`, `::test_a_list_operation_bundle_lowers_to_the_live_statement`, and `test_execution_compiled_families.py::test_list_operations_replay_with_their_requirements` (the compiled replay keeps the live requirements, an element read R01, over a LEFT JOIN carrier and an imported parent too) | `test_project_list_operations.py::test_each_refused_list_spelling_reports_its_first_broken_rule`, `::test_each_mistyped_list_operation_reports_one_error`, `::test_a_list_read_outside_its_place_stays_a_nested_read` (a JOIN body keeps PIE-S2805 with the carry hint), `::test_a_schema_version_1_project_refuses_a_list_generator`; MySQL `test_sql_nested_relations.py::test_mysql_refuses_the_collect_that_a_list_operation_reads` |
| A12 per-group detail route | E, C and L: `test_execution_nested_relations.py::test_the_per_group_detail_route_lowers_and_binds_its_live_statement` (routes `same_value` and `shared_filter`); the hint `test_project_nested_relation_facts.py::test_a_grouped_collect_names_the_per_group_detail_route` | with `==` the None-key group's list is `[]` (route `equality`), and a `let` that reads the unfiltered input beside a filtered grouped query lists every matching row (route `raw_source`): both documented, not refused |
| A13 scalar `Float` key | E, C and L: the same test, route `float_key`; in the PostgreSQL run each `-0.0` and `0.0` member keeps its own value | `test_project_nested_relation_facts.py::test_a_capture_on_a_nested_group_key_is_refused` |
| A14 worked example | `docs/worked-example.md`, checked in strict mode and as an `fmt` fixed point by `test_repo_docs_examples.py`, whose `test_worked_example_commands_run_as_the_page_shows` runs the page's commands (single-file `check` and `emit-sql`, `--set`, `check --project`, `emit-sql --project --all`) | its project part names the single-file refusal codes, as the style page does for project forms |
| A15 canonical forms | each delivering slice added its canonical form and a "Not this" list to [style](../../style.md); `test_repo_docs_examples.py` checks every example; `test_parser_format.py::test_the_conditional_aggregate_example_is_a_fixed_point_and_only_reindents` and the `top_level_constants_are_declarations` case | the refused variants of each row above |

### 3. The owner's additions

| Slice | Admitted, with its layers | Refused exactly |
| --- | --- | --- |
| S14 project aggregate windows | E: `test_sql_windows.py::test_postgres_emits_each_aggregate_window_with_its_aggregate_casts`, `::test_postgres_aggregate_windows_over_frames_groups_qualify_and_joins`, `test_semantic_window_aggregate.py::test_a_project_admits_the_aggregate_windows_a_single_file_admits`. C and L: `test_execution_compiled_bundle.py::test_an_aggregate_window_template_binds_and_renders_the_emitted_sql` | `test_semantic_window_aggregate.py::test_a_project_refuses_what_a_single_file_refuses_at_the_call`, `::test_a_project_aggregate_window_reads_only_direct_fields`, `test_sql_windows.py::test_postgres_aggregate_window_arguments_keep_the_aggregate_domain`; MySQL `::test_mysql_keeps_aggregate_windows_refused_before_its_database_evidence` |
| S15 `compile_query` takes the whole contract | `test_execution_api_queries.py::test_compile_query_keeps_only_the_contract_sources_the_query_reads` | the whole contract is still checked first, in the same test |
| S16 project aggregate parity | E: `test_sql_grouped.py::test_postgres_aggregates_reach_single_file_argument_parity`, `::test_joined_grouped_aggregates_keep_the_same_parity`. C: `test_execution_compiled_families.py::test_postgresql_aggregate_parity_replays_from_compiled_input`. L: `test_execution_compiled_bundle.py::test_an_aggregate_parity_template_binds_and_renders_the_same_sql` | `test_execution_compiled_families.py::test_a_compiled_aggregate_that_reads_no_row_stays_refused` |
| S17 `median`, `quantile` | E: `test_sql_sum_avg_sql.py::test_postgres_median_and_quantile_are_the_interpolated_percentile`, `test_sql_grouped.py::test_median_and_quantile_are_the_postgres_percentile_of_an_int`. C: `test_execution_compiled_families.py::test_postgresql_median_and_quantile_replay_from_compiled_input`. L: `test_execution_compiled_bundle.py::test_a_median_and_quantile_template_binds_its_header_read` | `test_semantic_sum_avg_semantics.py::test_median_and_quantile_misuse_is_refused_with_a_hint`, `test_sql_grouped.py::test_a_float_median_needs_a_finite_result_proof`; MySQL `test_sql_sum_avg_sql.py::test_mysql_refuses_median_and_quantile` |

Every acceptance row and owner addition above that has project forms has an
emission, a compiled-bundle and a live-template witness.

### 4. MySQL

A new single-file form opens on MySQL only after a two-database run; a form
that fails it, or has no run, stays refused with a fixed diagnostic and
moves to the Phase74 MySQL catch-up. T-L, T-G and T-K stay refused on MySQL
until Phase77 (D71.05).

| Feature | MySQL on `main` |
| --- | --- |
| Two-level route | single file open; project PIE-B1004 (project `sum(Int)`) |
| Conditional count and sum | single-file count open after its database run (batch 3); single-file sum refused (PIE-B1000, D73.01); project count PIE-B1003, project sum PIE-B1004 |
| Constants and `--set` | refused per relation that reads a constant (PIE-B1000); the database run passed |
| `max(a, b)`, `min(a, b)` | open, except two `Bool` values (MySQL returns an integer) and project `Date` and `UUID` |
| `lpad`, `add_months` | single file open; project refused, as `concat` is |
| Computed window keys | open, except a computed `Text` key in a single file |
| `now()` | refused; the database run passed |
| Typed project parameters | refused (D73.14) |
| Project aggregate windows and parity | refused with their existing blocker details |
| `median`, `quantile` | refused with a hint: MySQL 8.4 has no interpolated percentile |
| Nested keys, list operations, detail route | refused until Phase77 |

### 5. Deferrals stay refused

Phase73 adds no nesting level. Multi-level collections, a capture that reads
another capture, nested carry and window values, and child-level recovery,
R2 and sinks keep their Phase71 refusals (D73.19); a capture on a nested
group key is refused by the detail route's own negative test above. The
other deferrals of the route are in the [Phase74 handoff](phase74-handoff.md).

### 6. Real databases

Every run used local images by ID on PostgreSQL 18.6 and MySQL 8.4.12, no
network, one container at a time under the campaign lock, and an oracle
written before the run; each verdict was built only from the run's saved
outputs.

| Run | What it checked | Result |
| --- | --- | --- |
| Gate 0 | the detail route with `same_value` and a `Float` key, at emission, compiled and live layers | 50 judged, 0 failures; the None-key group gets its own rows, and each `-0.0` and `0.0` member keeps its sign |
| S01 | the single-file two-level route | 12 of 12 on six statements, both databases; the controls differ as the oracle predicts |
| S03 | the nested-key cases | 9 of 9 on PostgreSQL |
| S04 | `max(a, b)` and `min(a, b)` | 17 of 18; MySQL returns two `Bool` columns as an integer with the right values, so that form stays refused on MySQL |
| S05 | `lpad` and `add_months` | 8 of 8 |
| S10 | computed window keys | 32 checks on both databases |
| S11 | `now()` | 33 checks |
| S02 | the MySQL conditional count | 8 of 8 |
| S08 | constants and `--set` | 18 of 18; 8 rows equal to the oracle |
| S17 | `median` and `quantile` on PostgreSQL | 8 statements and 26 flags; the MySQL refusals checked |
| S06 | the list-operation value table: missing list, `[]`, all-None children, a bag, a negative child, `Int` overflow, at E, C and L | 7 of 7 on PostgreSQL; the overflow is SQLSTATE 22003 at each layer |
| S02P | the conditional count and sum on PostgreSQL in a single file and a project: None key, duplicates, None tests, a group with no match, whole input, empty input, HAVING, overflow and the signed 64-bit maximum; the MySQL project refusals | 37 of 37 flags |
| S09 | typed `Timestamp` and `UUID` parameters | the target-conformance jobs of the batch-2 natural CI `42232536210` on both databases |

CI health was read at the start (run `42090026718`) and at the midpoint
(run `42148220359`); the closing reading is the batch-3 natural CI.

### 7. Acquisition consolidation

S12 ran the phase-end acquisition review against the batch-1 natural CI
health (run `42148220359`) and kept the justified fresh witnesses. Five test
files changed: 40 project builds fewer per complete run (38 in the review, 2
more when the batch-3 conditional-aggregate forgeries share one bundle), 7
nodes fewer, one duplicated carrier and contract builder removed and one
hand-built prelude moved to its owner. The ten slowest in-process nodes are
the same ids as in Phase72, and no Phase73 test acquisition is in their top
frames. The one new product finding, F7 (the generator and `now()` whole-tree
walks on every parse), shares its root cause with the Phase72 F6: batch 3
gives each parsed script one shared node walk, pinned by
`test_project_parse_only_check.py::test_a_project_check_walks_each_parsed_script_once`
and `test_semantic_inline_functions.py::test_an_analysis_walks_its_script_once`.
F1, F2 and F4 stay as Phase72 recorded them, and a sixth copy of a test
prelude (`test_sql_project_scalar_expressions.py::test_now_is_one_utc_statement_snapshot_evaluated_at_execution`)
joins the Phase72 prelude debt for the next whole-tree pass.

### 8. Decisions, audit, handoff and lessons

The [decision record](../../decisions.md#phase73--owner-decisions-2026-11-05)
holds D73.01–D73.19 and the owner's additions. This audit, the
[Phase74 handoff](phase74-handoff.md) and the Phase73 section of the
[engineering lessons](../../references/engineering-lessons.md#phase73) are
in the S13 commit.

## Budget

| Account | Cap | Use |
| --- | --- | --- |
| Phase73 (S01–S17) | C225 / F720 / D3060 / S11 | lane records give about C76, F130 and D850 through batch 2, and the batch-3 lanes add about C21, F42 and D328 (S06 C14/F21/D153 over both rounds, S02P C4/F6/D74, S12 C2/F4/D31, the acquisition review C0/F1/D30, the walk C1/F9/D31, these drafts C0/F1/D9), plus the batch-3 integration; root database runs and the interrupted lane runs that kept no count are not included; no cap was reached |
| S03 lane | C15 / F30 / D120 | C11, F14, D about 117–123: at or just over its D cap |

## Failed histories kept

- S02 shipped its single-file forms only: the project forms stayed refused
  until S02P, and a first grammar lowered the pinned parser nesting limit by
  one before the lane restored it.
- The batch-1 integration first carried the MySQL conditional count before
  its database run; the review caught it and the form shipped refused until
  its run passed (opened in batch 3).
- Five database packages started PostgreSQL and MySQL at once and were not
  run until they were rebuilt to one container at a time, with the oracle
  unchanged.
- S04's database run failed one cell (MySQL `Bool` result type); the form
  is refused on MySQL.
- S10 tried and reverted computed keys over JOIN rows; S06's first round had
  no PostgreSQL layers and one rejected kernel change.
- A network outage ended the batch-2 workflow after its integration had
  finished; the resumed run skipped the finished step. Several interrupted
  lane runs kept no command count.
- At the batch-3 integration S02P's project path ran the group generator
  normalizer over S06's list generators, which turned each element read into
  a row read; S06's emission, compiled and live tests caught it, and the
  normalizer now leaves list generators alone. Both lanes had added the same
  `GeneratorExpr` walker branches; the merge kept S06's list-aware ones.
- The Windows 3.12 job of the Windows CI repair head failed once on a test
  parameter that forces comparable `ctime` (CI `42230229990`); batch 3 marks
  that parameter POSIX-only, as Windows trusted reads do not use `ctime`.
