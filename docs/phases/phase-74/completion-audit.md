# Phase74 completion audit

Phase74 owns cross-module reuse of `def` and relationships, relationship
parameters that take the rows of a table or query, the MySQL catch-up, and
the owner's additions: the backward asof JOIN on MySQL and the new
aggregates (row 74 of the [Future Roadmap v6](../../roadmap.md#future-roadmap-v6)).
This audit checks the closure conditions of its [route](route.md) on the
integrated batch-2 tree. It publishes nothing: live `main` and its natural
exact-head CI remain the lifecycle authority, and the
[Phase75 handoff](phase75-handoff.md) lists what moves on.

## Baseline and batches

| Step | Fact |
| --- | --- |
| Gate 0 | `main` at the Phase73 completion commit `37143dcb00694ad5b7e23a1f4e928ecafa23b185` (tree `d93f939363d335b4fa4f38812597ac185eb25849`); natural exact-head CI `42277807557` attempt 1 accepted all 21 jobs. It is the repair child of the Phase73 batch-3 head `b148fdee`, whose CI `42272513354` failed one Windows 3.12 test; the Phase74 series was first built on `b148fdee` and rebuilt on `37143dcb` with each step's changed lines unchanged. The Gate 0 probes are recorded as the rebind and the lanes' witnesses; there was no separate probe run. |
| Gate 1 | D74.01–D74.16 in the [decision record](../../decisions.md#phase74--owner-decisions-2026-11-05-and-2026-11-06), recorded by the lead as the Phase74 plan recommends; on 2026-11-05 the owner kept the joint-plan answers and let the three lines start, and on 2026-11-06 approved the aggregate spelling table with its defaults (D74.11). Budget C206/F660/D2650/S12 (D74.16). |
| Batch 1 | Seven commits on `37143dcb`: the route publication, S01 (def import and export), S02 (relationship import and export), S03 (table and query rows), S04 (MySQL UUID ordering), S05 (MySQL aggregates, Float ORDER BY and `Bool` `max`/`min`) and S06 (asof JOIN on MySQL), ending at `ef29b423bf20cedee984d42eaed455968ae63b9f` (tree `8b801001cb9ebc7a39d7be6ef62fe2bd0252a035`). One Gate 2 on that tree (26,537 passed, 41 skipped); natural exact-head CI `42298363606` attempt 1 accepted all 21 jobs. No slice changed a compiled record. |
| Midpoint | At the batch-1 head `ef29b423`: 74-A and 74-B are on `main` with their emission, compiled and live witnesses on PostgreSQL, and 74-A on MySQL too; the MySQL compiled and live witness of 74-B came with the S07 example in batch 2 (§2); each batch-1 MySQL form is open after a passing differential or refused with its code (§4); the lane tallies project inside the caps (Budget); the batch-1 natural CI is the midpoint CI reading. |
| Batch 2 | Seven commits on `ef29b423`: S09 (`variance`, `pvariance`, `pstdev`), S10 (`count_distinct(a, b, ...)`), S11 (`all` and `any` over a group), S12 (`first` and `last`), the S04 follow-up (MySQL project `min` and `max` of a `Timestamp` or `Date`, after its differential rerun passed), S07 (the two-module example and the acquisition consolidation) and this audit (S08), in that order. The new `aggregate_value` function values ride the unreleased `(7, 1, 7, 1)`; `VERSIONS` is unchanged in Phase74 (D74.15). No version change: `0.1.10` is cut after Phase75 closes (D74.14). One Gate 2 on the final tree; Phase74 closes when its head passes natural exact-head CI. |

## Closure conditions

### 1. 74-A and 74-B are delivered

- 74-A: in a `schema_version = 2` project `def NAME` and `relationship NAME`
  are items of the bare and the parenthesized import and export lists. They
  bind through the existing exporter and binder; a def or relationship is
  checked once, in its own module; collisions are refused with no winner;
  PIE-S2103 names the export or import to write. An imported def or
  relationship emits the bytes of the same declaration written locally,
  which is the 74-A oracle (D74.02).
- 74-B: a relationship parameter takes the rows of a table or query whose
  output columns match its fields by name and type (D74.08); PIE-S2604 names
  the first field that does not match. Source rows still bind only by their
  declared shape.

### 2. Acceptance

Each project form needs an emission, a compiled-bundle and a live-template
witness on PostgreSQL and MySQL; a single-file form needs only the emission
layer. "E" is emission, "C" the compiled bundle and "L" the live template.

| Slice | Admitted, with its layers | Refused exactly |
| --- | --- | --- |
| S01 def import and export | Parser: `test_parser_import_export_contextual_grammar_ast.py::test_def_and_relationship_items_are_kind_name_items_of_both_list_forms`, `::test_import_list_accepts_exact_eight_declaration_kinds_in_source_order`, `::test_export_list_accepts_exact_eight_declaration_kinds_in_source_order`. Check: `test_project_def_imports.py::test_an_imported_def_is_called_by_the_name_its_import_binds` (both list forms, renamed re-export chains, an importer alias that never types the signature), `::test_an_imported_def_keeps_the_builtin_concat_its_module_bound`. E, C and L on both databases: `test_execution_compiled_bundle.py::test_an_imported_def_renders_the_sql_of_the_same_local_def` (the imported def's SQL equals the local def's, and the loaded bundle and the live template bind to it) | `test_project_def_imports.py::test_each_failed_def_import_is_reported_at_its_item_and_none_wins` (PIE-S2705, PIE-S2706, PIE-S2398), `::test_two_imports_of_one_local_name_are_ambiguous`, `::test_an_unknown_export_of_a_def_is_refused_at_the_export`, `::test_call_errors_are_at_the_call_and_def_errors_at_the_def_once`, `::test_an_expansion_over_the_size_bound_is_refused_at_the_call`, `::test_a_def_imported_along_an_import_cycle_is_blocked`; `test_parser_import_export_contextual_grammar_ast.py::test_a_wildcard_or_constraint_or_derive_item_is_refused_with_a_hint`; a package module, PIE-S2707: `test_project_package_loading.py::test_def_and_relationship_module_items_are_refused_in_a_package` |
| S02 relationship import and export | Check: `test_project_relationship_imports.py::test_an_imported_relationship_is_called_by_the_name_its_import_binds`, `::test_a_query_row_is_checked_by_the_field_types_of_the_declaring_module`. E, C and L on both databases: `test_execution_compiled_bundle.py::test_an_imported_relationship_renders_the_sql_of_the_same_local_one` (ON, a WHERE `any(...)` and SELECT) | `test_project_relationship_imports.py::test_each_failed_relationship_import_is_reported_at_its_item_and_none_wins`, `::test_an_export_or_import_the_declaring_module_does_not_offer_is_refused`, `::test_a_relationship_imported_along_an_import_cycle_is_blocked`, `::test_call_errors_are_at_the_call_and_template_errors_at_the_declaration_once`, `::test_a_call_of_a_relationship_whose_shape_import_failed_follows_that_error`; the PIE-S2103 hints `::test_an_unknown_function_says_how_to_import_the_relationship_of_another_module`, `::test_a_call_that_no_import_can_bind_is_told_to_declare_it_in_its_module` and `test_project_def_imports.py::test_an_unknown_function_says_how_to_import_the_def_of_another_module` (the qualified call `a.pos(x)` included) |
| S03 table and query rows | Single file: `test_semantic_relationship_declarations.py::test_a_table_or_query_row_binds_a_relationship_by_field_name`, `::test_a_left_joined_query_row_keeps_its_nullability_and_identity`; E on both databases `test_sql_join_emission.py::test_a_relationship_over_query_rows_emits_its_written_on`. Project check: `test_project_query_result.py::test_table_and_query_row_arguments_check_as_in_a_single_file`, `::test_table_and_query_rows_bind_across_modules`. E, C and L on PostgreSQL: `test_execution_compiled_families.py::test_a_relationship_over_query_rows_replays_as_its_written_on` (LEFT, grouped by its GROUP BY key, imported); E on MySQL: `test_sql_joins.py::test_a_join_over_a_distinct_endpoint_emits_its_on_form`, `test_sql_upstream_values.py::test_a_promoted_endpoint_is_a_relationship_row_by_its_columns`; E, C and L on MySQL: the two-module example (S07 below), whose grouped query rows bind a relationship | the same tests over `tests/_pietto_semantic_relationship_rows.py`: a missing column, another type, a nullable or computed column for a field that cannot be None, an enum of another declaration and a source of another shape are PIE-S2604 naming the field or the shape; a shape's `unique` proves no key of a query's rows, so an aggregate over that JOIN stays PIE-S2381 (PIE-S2333 in a project); across modules, an enum of another module with the same name |
| S04 MySQL UUID ordering | E: `test_project_sql_temporal_operations.py::test_uuid_filters_compare_by_order`, `test_sql_result_bounds.py::test_timestamp_date_and_uuid_keys_order_a_result`, `test_sql_windows.py::test_temporal_and_uuid_window_keys`, `test_results_timestamp_uuid.py::test_intrinsic_meaning_admits_temporal_equality_grouping_and_uuid_order`. C and L: `test_execution_compiled_families.py::test_a_uuid_order_replays_from_compiled_input`, `::test_max_and_min_of_two_timestamps_or_uuids_emit_replay_and_bind` (UUID `max` and `min` too) | `test_project_sql_temporal_operations.py::test_uuid_orders_by_its_bytes_and_mixed_temporal_carriers_stay_unordered` (mixed carriers); project `Date` `max`/`min` has no project conditional on either database (PIE-B1003 `conditional_realization_not_admitted`, the same compiled-families test) |
| S04 follow-up: MySQL project `min` and `max` of a `Timestamp` or `Date` (batch 2) | Law: `test_project_sql_temporal_operations.py::test_one_temporal_carrier_orders_and_compares`. E on both databases: `test_sql_grouped.py::test_min_and_max_of_a_temporal_carrier_keep_it` (MySQL `MIN`/`MAX` keep `DATETIME(6)` and `DATE`, nullable), `test_results_timestamp_uuid.py::test_min_of_a_timestamp_keeps_its_source_meaning` (result contract and a compiled replay). C and L on both databases: `test_execution_compiled_families.py::test_temporal_extrema_replay_from_compiled_input` (grouped and filtered whole-input bodies) | a MySQL aggregate window over them stays PIE-B1003 `window_aggregate_approved_non_support_on_mysql`, as every MySQL aggregate window (`test_sql_windows.py::test_mysql_keeps_aggregate_windows_refused_before_its_database_evidence`) |
| S05 MySQL aggregates, Float ORDER BY, `Bool` `max`/`min` | E: `test_sql_grouped.py::test_postgres_aggregates_reach_single_file_argument_parity` (its MySQL `postgres_carriers` case), `::test_row_expression_and_float_arguments_count_and_compare_on_both_targets`, `::test_an_aggregate_argument_is_a_field_or_a_lowered_row_expression`, `::test_joined_grouped_aggregates_keep_the_same_parity`, `test_sql_result_bounds.py::test_float_order_key_orders_by_value_on_both_targets`; single file `test_sql_mysql_relations.py::test_max_and_min_of_two_bool_values_emit_the_conditional`. C: `test_execution_compiled_families.py::test_aggregate_parity_replays_from_compiled_input`, `::test_float_equality_and_order_replay_from_compiled_input` (its MySQL `fo_ascending` case, with the live template). L: `test_execution_compiled_bundle.py::test_an_aggregate_parity_template_binds_and_renders_the_same_sql` | MySQL projects keep the Float `sum` and `avg`, an `Int` expression outside BIGINT and `count_distinct` of a `Float` refused (the same `test_sql_grouped.py` tests), and `string_agg` stays refused in single files and projects, each with its code (§4) |
| S06 asof JOIN on MySQL | Single file E: `test_sql_join_emission.py::test_an_asof_join_renders_as_the_latest_lateral_row` (both databases). Project E, C and L: `test_execution_compiled_families.py::test_an_asof_join_emits_its_latest_row_as_an_anti_join_and_replays` (both databases, `left` and `inner`) | `test_sql_join_emission.py::test_mysql_refuses_an_asof_join_in_a_relation_with_a_full_join` (PIE-B1000 with the narrower text) |
| S07 two-module example | `docs/worked-example.md`, part "Two modules": a project whose `report.pietto` imports a def, a relationship and two sources from `models.pietto`, and passes a grouped query's rows to the relationship. `test_repo_docs_examples.py::test_worked_example_commands_run_as_the_page_shows` runs its `check --project` and `emit-sql --project --all`; `::test_the_two_module_example_has_the_sql_of_one_module` compiles each query with `compile_query` on PostgreSQL and MySQL, finds the SQL of the same declarations in one module, and binds the live template and a bundle that `export_bundle` wrote and `load_bundle` read to it. Both blocks are strict-checked and `fmt` fixed points | the single-file codes of each module (PIE-S2708 and the unknown names) on the fences |
| S09 `variance`, `pvariance`, `pstdev` | Check: `test_semantic_sum_avg_semantics.py::test_stddev_of_an_int_or_float_field_is_a_nullable_float` (each of the four spreads); IR `test_ir_aggregate_expression_argument_ir.py::test_stddev_aggregate_call_contract_is_one_int_or_float_field`. Single file E: `test_sql_sum_avg_sql.py::test_postgres_variance_and_population_deviation_cast_the_variance_once`, on MySQL `::test_mysql_variance_and_population_deviation_are_of_a_float_only` (`Float`). Project E on PostgreSQL: `test_sql_grouped.py::test_variance_and_population_deviation_are_the_postgres_float8_variance`; C: `test_execution_compiled_families.py::test_postgresql_variance_and_population_deviation_replay_from_compiled_input`; C and L: `test_execution_compiled_bundle.py::test_a_variance_template_binds_its_header_read_and_renders_the_same_sql`; closed data: `test_harness_sql_emission_portability.py::test_variance_casts_spellings_and_evidence_are_closed_data_relations` | `test_semantic_sum_avg_semantics.py::test_stddev_misuse_keeps_the_aggregate_diagnostics` (a `Decimal`, misplaced, composed, an expression, a `let` name); the habit hints `test_semantic_functions.py::test_unknown_function_reports_pie_s2103`, `::test_a_variance_habit_hint_is_also_the_json_suggestion`; `def variance` PIE-S2398 `test_semantic_inline_functions.py::test_only_a_def_named_for_a_new_builtin_is_told_to_rename`; a window `test_semantic_window_computation.py::test_refused_window_computations_name_their_reason`; MySQL: a single-file `Int` PIE-B1000 (`test_sql_sum_avg_sql.py::test_mysql_variance_and_population_deviation_are_of_a_float_only`), a project PIE-B1003 (`Int`) or PIE-B1004 (`Float`) (`test_sql_grouped.py::test_variance_and_population_deviation_are_the_postgres_float8_variance`) |
| S10 `count_distinct(a, b, ...)` | Check: `test_semantic_count_distinct_semantics.py::test_count_distinct_of_several_fields_is_a_non_null_int`. Single file E: `test_sql_count_distinct_sql.py::test_count_distinct_of_several_fields_is_one_postgresql_record`, on MySQL `::test_count_distinct_of_several_fields_is_native_on_mysql` (`Float` members included), the IR contract `::test_count_distinct_tuple_ir_renders_only_its_contract`. Project E on PostgreSQL: `test_sql_grouped.py::test_postgres_aggregates_reach_single_file_argument_parity` (its `count_distinct_tuple` case), `::test_postgres_count_distinct_tuple_reads_left_join_rows`; C: `test_execution_compiled_families.py::test_aggregate_parity_replays_from_compiled_input` (its `count_distinct_tuple` row), `::test_postgresql_count_distinct_tuple_over_join_rows_replays`; C and L: `test_execution_compiled_bundle.py::test_a_count_distinct_tuple_template_binds_its_header_read`; closed data: `test_harness_sql_emission_portability.py::test_count_distinct_tuple_is_a_closed_data_relation` | `test_semantic_count_distinct_semantics.py::test_count_distinct_of_several_fields_refuses_at_the_argument` (a repeated field, PIE-S2104; an expression, PIE-S2315; a type, PIE-S2314), `::test_a_pandas_or_polars_distinct_count_names_count_distinct`, `::test_a_python_set_count_names_count_distinct`; project `test_project_grouped_aggregate_project_row_schema.py::test_project_check_refuses_a_count_distinct_tuple_as_a_file_does`, `::test_a_legacy_flat_project_refuses_a_count_distinct_tuple` (PIE-S2334); a window `test_semantic_window_computation.py::test_refused_window_computations_name_their_reason`; MySQL project PIE-B1003 `count_distinct_tuple_not_admitted_on_target` (`test_sql_grouped.py::test_postgres_aggregates_reach_single_file_argument_parity`, its MySQL `count_distinct_tuple` case) |
| S11 `all` and `any` over a group | Check: `test_semantic_conditional_aggregates.py::test_a_group_test_is_a_bool_that_is_never_none`, project `test_project_grouped_aggregate_project_row_schema.py::test_a_schema_version_2_project_checks_the_test_of_a_group`. Single file E: `test_sql_conditional_aggregates.py::test_postgres_tests_a_group_with_one_count`, on MySQL `::test_mysql_tests_a_group_with_the_postgres_form`. Project E on PostgreSQL: `::test_a_project_emits_the_test_of_a_group_on_postgres`; C: `test_execution_compiled_families.py::test_postgresql_group_tests_replay_from_compiled_input`; C and L: `test_execution_compiled_bundle.py::test_a_group_test_template_binds_its_header_read`; closed data: `test_harness_sql_emission_portability.py::test_the_test_of_a_group_is_a_closed_data_relation` | `test_semantic_conditional_aggregates.py::test_each_refused_group_test_reports_its_first_broken_rule`, `::test_a_group_test_body_that_is_no_bool_suggests_a_test`, `::test_a_group_test_habit_names_the_generator`, `::test_a_group_test_before_group_by_says_there_is_no_group`, `::test_a_group_test_in_having_or_order_by_says_to_select_it`, `::test_a_group_test_in_qualify_has_no_having_hint`, `::test_a_select_item_refuses_a_group_test_over_a_relation_named_group` and `::test_a_let_named_group_is_refused_in_a_group_test` (7b), `::test_a_group_test_over_join_rows_is_refused_with_a_hint`, `::test_a_def_named_any_or_all_is_refused_with_a_rename` (7a); project `test_project_grouped_aggregate_project_row_schema.py::test_a_schema_version_1_project_has_no_test_of_a_group`, `::test_a_project_refuses_a_test_of_a_group_as_a_single_file_does`, `::test_a_project_refuses_a_test_of_a_group_over_a_let_named_group`, `::test_a_project_any_over_group_outside_a_select_item_says_where_it_goes`; emission `test_sql_conditional_aggregates.py::test_a_project_refuses_a_group_test_that_reads_no_field`, MySQL project PIE-B1003 `::test_a_project_refuses_the_test_of_a_group_on_mysql`; a forged bundle `test_execution_compiled_families.py::test_a_compiled_group_test_keeps_its_signature` |
| S12 `first` and `last` | Check: `test_semantic_aggregate_ordered_value.py::test_a_grouped_first_or_last_has_its_fields_type`, `::test_without_group_by_the_value_may_be_none`, `::test_an_order_that_ends_in_a_unique_key_is_admitted`, `::test_a_let_name_of_a_field_reads_as_that_field`, project `::test_a_schema_version_2_project_reports_what_a_file_does`. Single file E on PostgreSQL: `test_sql_aggregate_ordered_value.py::test_postgres_writes_the_first_element_of_an_ordered_array_agg`, `::test_postgres_first_over_a_whole_input_is_one_row`, `::test_postgres_orders_by_an_enum_key_as_a_relation_does`. Project E on PostgreSQL: `::test_a_project_writes_first_and_last_as_a_file_does`; C: `test_execution_compiled_families.py::test_postgresql_first_and_last_replay_from_compiled_input`; C and L: `test_execution_compiled_bundle.py::test_a_first_and_last_template_binds_its_header_read`; `fmt`: `test_parser_format.py::test_the_first_and_last_example_is_a_fixed_point_and_only_reindents` | `test_semantic_aggregate_ordered_value.py::test_each_refused_order_or_value_is_one_diagnostic`, `::test_an_enum_value_is_refused_by_type`, `::test_an_input_whose_fields_are_not_known_is_refused`, `::test_join_rows_and_a_query_input_are_refused`, `::test_a_window_form_reports_its_window_refusal`, `::test_a_first_outside_a_select_item_is_an_aggregate_out_of_place`, `::test_an_arbitrary_row_or_arg_max_habit_names_first`, `::test_a_def_named_first_or_last_must_be_renamed` (7a), `::test_a_call_with_an_error_inside_it_reports_that_error_alone`, `::test_a_schema_version_1_project_has_no_first_or_last`; MySQL `test_sql_aggregate_ordered_value.py::test_mysql_has_no_ordered_first_or_last_yet` (PIE-B1000), `::test_a_mysql_project_refuses_first_and_last` (PIE-B1003) |

Each delivering slice added its canonical form and its "Not this" list to
[style](../../style.md); `test_repo_docs_examples.py` checks every example.
Every row above with project forms has an emission, a compiled-bundle and a
live-template witness on PostgreSQL; on MySQL, 74-A, S03 (through the S07
example), S04 and its follow-up, S05 and S06 have them as well. S09, S10 and
S11 open on MySQL in single files only, whose witness is the emission layer;
their MySQL project forms and every MySQL `first` and `last` are refused (§4).

### 3. A project without def or relationship items is unchanged

The route asks for byte-equal check output for a project without def or
relationship items. No A05 corpus was frozen at Gate 0. The lanes ran every
`schema_version = 2` test owner before and after their change, and the
batch-1 integration ran 104 focused owners and the harness differential
owners; the intended differences are the PIE-S2103 hints, the PIE-P1000
kind list and the PIE-S2604 field texts, each listed in the
[release notes](../../release-notes.md).

### 4. MySQL

A form opens on MySQL only after a passing two-database differential
(PostgreSQL 18.6, MySQL 8.4.12); otherwise it keeps its refusal and the
release notes list it (D74.09). Every row of the
[Phase74 handoff's MySQL table](../phase-73/phase74-handoff.md#mysql-items-for-the-phase74-mysql-catch-up)
and every 74-M and 74-G form:

| Form | MySQL on `main` after Phase74 |
| --- | --- |
| Def and relationship imports, table and query rows | open: their SQL equals forms already open |
| Project UUID comparison, BETWEEN, `order by` keys, UUID `max(a, b)` and `min(a, b)` (S04) | open |
| Project aggregates of `Text`, `Bool`, `Float` and `Decimal` values and over row expressions (S05) | open |
| Relation `order by` a finite `Float` (S05) | open |
| Single-file `max(a, b)` and `min(a, b)` of two `Bool` values (S05) | open: an integer column, as every computed `Bool` |
| Backward asof JOIN (S06) | open in single files and projects, except beside a FULL JOIN (PIE-B1000) |
| Project `min` and `max` of a `Timestamp` or `Date` (S04 follow-up, batch 2) | open after the rerun of its differential: `MIN` and `MAX` keep `DATETIME(6)` and `DATE`; over a window refused, as every MySQL aggregate window (PIE-B1003) |
| `Int` arithmetic not proved to fit signed 64 bits | refused (PIE-B1002 `arithmetic_outside_physical_range`, `unary_result_outside_physical_range`, `abs_result_outside_physical_range`): MySQL raised error 1690 for a product of -2^63, which fits signed 64 bits |
| Project `count_distinct`, `sum`, `avg` and `stddev` of a `Float`; project `sum(Int)` and `stddev` of an `Int` | refused (PIE-B1004 `float_aggregate_finite_result_proof_missing` for a `Float` `sum`, `avg` and `stddev`; PIE-B1003 `count_distinct_argument_outside_reviewed_int_domain`; PIE-B1004 `sum_int_aggregate_range_proof_missing`; PIE-B1003 `stddev_int_not_admitted_on_target`); a single file emits each of them but an `Int` `stddev` (PIE-B1000); project `sum(Int)` and `Int` `stddev` wait for Phase77 |
| `string_agg` | refused (single file PIE-B1000, project PIE-B1003): `GROUP_CONCAT` truncates silently |
| `Float` DISTINCT, GROUP BY, set operations and `==` between two row reads | refused: the zero guard waits for a decision on the `Float` value contract |
| Single-file conditional sum | refused (PIE-B1000); no Phase74 run |
| Project conditional count and sum | refused (PIE-B1003 `conditional_count_not_admitted_on_target`, PIE-B1004 `sum_int_aggregate_range_proof_missing`) |
| Single-file constants and `--set` | refused (PIE-B1000 per relation); its database run passed (18 of 18 flags), but no slice of the published route takes it and a new one would exceed the scope cap S12; a Phase76/77 catch-up item |
| `now()` | refused (PIE-B1000 single file, PIE-B1003 project); its database run passed (33 checks), but no slice takes it, as for constants; a Phase76/77 catch-up item |
| Project `lpad` and `add_months` | refused, as `concat` is (PIE-B1003 `scalar_call_signature_not_admitted`) |
| Computed `Text` window key in a single file | refused (PIE-B1000) |
| Typed project parameters (`Decimal(p, s)`, `Date`, `Timestamp`, `UUID`) | refused (PIE-B1003 `query_parameter_type_not_admitted_on_target`, D73.14) |
| Project aggregate windows | refused (PIE-B1003 `window_aggregate_approved_non_support_on_mysql`; project `sum(Int)` also PIE-B1004) |
| Project `max(a, b)` and `min(a, b)` of two `Date` values | refused on both databases: no project `Date` conditional yet (PIE-B1003 `conditional_realization_not_admitted`) |
| `variance`, `pvariance`, `pstdev` (S09) | single-file `Float` open after its run (`VAR_SAMP`, `VAR_POP`, `STDDEV_POP`); a single-file `Int` refused (PIE-B1000); projects refused (PIE-B1003 `variance_int_not_admitted_on_target` and its `pvariance`/`pstdev` details for an `Int`, PIE-B1004 `float_aggregate_finite_result_proof_missing` for a `Float`) |
| `count_distinct(a, b, ...)` (S10) | single file open after its run, `Float` members included (`COUNT(DISTINCT a, b)`); projects refused (PIE-B1003 `count_distinct_tuple_not_admitted_on_target`) |
| `all` and `any` over a group (S11) | single file open after its run, an integer 0/1; projects refused (PIE-B1003 `group_test_not_admitted_on_target`) |
| `first` and `last` (S12) | refused in the first version (D74.11): single file PIE-B1000, project PIE-B1003 `first_last_not_admitted_on_target` |
| `median` and `quantile`; nested keys, list operations and the detail route | not catch-up items: no interpolated percentile on MySQL; Phase77 (D71.05) |

The refused rows that are not 74-M forms move to the
[Phase75 handoff](phase75-handoff.md#mysql-items-after-phase74).

### 5. Deferrals stay refused

Each "Not included" item of the route keeps its refusal with a negative
test: wildcard imports and `constraint` and `derive` items (PIE-P1000,
`test_parser_import_export_contextual_grammar_ast.py::test_a_wildcard_or_constraint_or_derive_item_is_refused_with_a_hint`);
qualified calls (PIE-S2103 with the import hint, the S02 row); def and
relationship items in a PACKAGE_ROOT package module (PIE-S2707, the S01
row); source rows bound by field name (the "source of another shape" case of
the S03 row). MySQL `first` and `last`, window forms of the new aggregates,
and `all`, `any`, `first` and `last` in a grouped query with a JOIN:
`test_sql_aggregate_ordered_value.py::test_mysql_has_no_ordered_first_or_last_yet`
and `::test_a_mysql_project_refuses_first_and_last`; a window, for each new
aggregate that has one, in
`test_semantic_window_computation.py::test_refused_window_computations_name_their_reason`
(`variance`, `count_distinct(a, b)`) and
`test_semantic_aggregate_ordered_value.py::test_a_window_form_reports_its_window_refusal`,
while a generator call such as `any(... for o in group)` takes no `window` at
all (PIE-P1000,
`test_parser_generators.py::test_window_table_function_and_qualify_calls_take_no_generator`);
JOIN rows in
`test_semantic_conditional_aggregates.py::test_a_group_test_over_join_rows_is_refused_with_a_hint`
and `test_semantic_aggregate_ordered_value.py::test_join_rows_and_a_query_input_are_refused`.

### 6. Real databases

Every run used local images by ID on PostgreSQL 18.6 and MySQL 8.4.12, no
network, one container at a time under the campaign lock, and an oracle
written before the run; each verdict was built only from the run's saved
outputs, and an independent integrity audit read each run.

| Run | What it checked | Result |
| --- | --- | --- |
| 74-B | table and query rows passed to a relationship, single file and project, on both databases | 32 of 32 |
| 74-M part 1 | MySQL UUID ordering, temporal `min`/`max`, checked `Int` arithmetic | 77 passed, 3 failed: a judge expectation that omitted the group column (temporal grouping; types right) and MySQL error 1690 for a product of -2^63 that PostgreSQL returns (checked multiplication stays refused) |
| 74-M UUID `max`/`min` | project UUID `max(a, b)` and `min(a, b)` | run 1: 12 passed, 2 failed in a judge that kept one-column rows only; run 2 after an erratum, with the first run kept: 14 of 14 |
| 74-M part 2 | MySQL aggregates, Float ORDER BY, `Bool` `max`/`min`, with MySQL column types judged | 21 of 21; a recorded design probe showed `GROUP_CONCAT` truncation (error 1260) |
| Asof JOIN on MySQL | single file and project, against PostgreSQL | 152 verdicts, 0 failed; 14 of 14 mutations killed |
| 74-M part 1, run 2 | the part-1 package again under a judge erratum, with run 1 kept | the temporal `min`/`max` families 6 of 6, MySQL column types judged (`DATETIME` with 6 decimals, `DATE`), so they opened in batch 2; checked multiplication failed again (error 1690) and stays refused |
| S09 `va` | `variance`, `pvariance`, `pstdev` | 80 of 80 statements (405 values, 6 accepted overflow errors); damage controls caught |
| S11 `ba` | `all` and `any` over a group | both families passed; mutants detected |
| S10 `cd` | `count_distinct(a, b, ...)` | 3 of 3 families; the single-column MySQL `count_distinct(Float)` witness passed too |

CI health was read at the start (run `42277807557`) and at the midpoint
(run `42298363606`); the closing reading is the batch-2 natural CI.

### 7. Acquisition consolidation

S07 ran the phase-end acquisition review over the tests batch 1 added or
changed (33 files) and the four aggregate lanes' candidates. Batch 1 was
already lean: its new compiled and live witnesses build each project once
per node and check the loaded bundle and the live template in one loop, and
each second build is the local-declaration or written-out oracle of the
claim. One duplicate build is gone: a new MySQL test rebuilt the corpus
variant that a parametrized case of the same file built only to assert that
it is VERIFIED, and its assertions now run in that case (one node and one
project build fewer). The two-module example adds six nodes, so S07 adds
five; the batch-2 collection is 26,902 nodes (26,578 at the batch-1 head).
For batch 2 the review shares one module fixture: the `all`/`any` replay
and its two forgeries read one PostgreSQL project build (its emission
artifact), built once, and each node still builds its own compiled bundle
from it. On the
three acquisition owners `test_sql_grouped.py`,
`test_execution_compiled_families.py` and
`test_execution_compiled_bundle.py`, `build_case` goes from 775 to 772 and
`emit_project_sql` from 868 to 865 per run, `build_compiled` stays 755,
and the wall time at two workers moved within noise (139.1 s to 136.9 s):
a structural gain with no measured wall-time gain. The aggregate owners
keep one build per node, each node its own body, and their three corpus
variants per target join the kept corpus consumers. The bounded profile read
the batch-1 head's natural CI health (run `42298363606`, Python 3.13): its
ten slowest in-process nodes are the same ten ids as in Phase73 and
Phase72. Each ran alone under cProfile on the batch-2 tree, two at a time,
at a load of 0.9 to 3.2. The verifier runs per build are unchanged (plan
verification 31.6, source maps 5.5 and emission verification 1.7 on the
receipt corpus, now 274 variants per target; 2.0 to 2.4 portable
observations per emission), and no Phase74 test helper is in a top frame.
The Phase74 functions in the top frames are the parse path that S01 split,
whose time is the parse itself, and `group_any_calls`, which is the first
reader of the one shared node inventory of a parse (0.47 s of a
64,000-cell VALUES node) that the later readers reuse, so Phase74 adds no
tree walk. No new finding; the Phase73 F1, F2 and F4 debts
stand as recorded, and the duplicated `_check` helper of the two new import
owners joins the prelude debt for the second whole-tree pass.

### 8. Decisions, audit, handoff and lessons

The [decision record](../../decisions.md#phase74--owner-decisions-2026-11-05-and-2026-11-06)
holds D74.01–D74.16. This audit, the [Phase75 handoff](phase75-handoff.md)
and the Phase74 section of the
[engineering lessons](../../references/engineering-lessons.md#phase74) are in
the S08 commit.

## Budget

| Account | Cap | Use |
| --- | --- | --- |
| Phase74 (S01–S12) | C206 / F660 / D2650 / S12 | batch-1 lanes about C35, F90 and D715 (route-draft tally, integration included), the batch-1 replay and integration about C4, F8 and D56, the four aggregate lanes about C13, F42 and D271, the closeout lane C0, F5 and D34, the temporal follow-up lane about C1, F4 and D18, the batch-2 integration with its audit repair about C12, F15 and D50, and its final assembly C2, F8 and about D62, with its audit repair C3, F7 and about D23; database runs count in D, ten in all (§6); no cap was reached |

## Failed histories kept

- The batch-1 series was built on `b148fdee`; when that head's CI failed
  and its repair child `37143dcb` became the Phase73 completion, Gate 0
  moved and each step tree was rebuilt with the same changed lines.
- 74-M part 1 failed three cells: one judge error (temporal `min`/`max`),
  and two cells where MySQL refuses a product of -2^63, so checked
  multiplication stays refused. Temporal `min` and `max` stayed refused in
  batch 1 and waited for an erratum run.
- The first UUID `max`/`min` run failed two cells in its judge; the form
  opened only after an erratum and a fresh run, with the first run kept.
- The aggregate lanes' reviews found blocking defects before integration: a
  PIE-S2202 hint for a non-`Bool` group test, a cascade of two defects in
  `first`/`last`, and a joined `let` field argument position and one field
  under two spellings in `count_distinct(a, b, ...)`; each was fixed in the
  lane.
- The batch-2 series was first built on the batch-1 tree before that
  batch's audit repairs; its own batch audit found the stale base (a def
  import through a re-exported source crashed) and twelve more defects, and
  every step was replayed onto the repaired tree with each fix in the step
  that introduced it.
- The S10, S11 and S12 compiled-bundle tests named a live template but
  bound only the compiled one; each now binds the live template in the same
  loop, as the S09 test did.
- The batch-2 lane briefs numbered S10–S12 in another order than the
  route; the commits and this audit follow the route.
