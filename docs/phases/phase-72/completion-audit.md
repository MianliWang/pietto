# Phase72 completion audit

Phase72 owns advanced equality, types and nullability, and temporal and asof
relationships (row 72 of the [Future Roadmap v6](../../roadmap.md#future-roadmap-v6)).
This audit checks its closure conditions on the integrated batch-2 tree. It
publishes nothing: live `main` and its natural exact-head CI remain the
lifecycle authority, and the
[Phase73 handoff](phase73-handoff.md) lists what moves on.

## Baseline and batches

| Step | Fact |
| --- | --- |
| Gate 0 | `main` `8cebe7798eb4ecf49f68d3655f133ffe2c115b49` (tree `357eeaa47593799bbce67a9fb8a9c0f7c7cce480`); natural exact-head CI `41766849826` attempt 1 accepted all 19 jobs. |
| Gate 1 | On 2026-11-04 the owner accepted B1–B15 as recommended: eight must-do items, the MySQL rule of the table below and the budget C150/F600/D400/S8. The same day the owner raised D once, to 1200. The [decision record](../../decisions.md#phase72--owner-decisions-2026-11-04-and-2026-11-05) lists the rules. |
| Rebase | After the Gate 0, `0.1.8` was released from `61b05586` (tag `v0.1.8`) without Phase72 work, and the batch-1 lanes were replayed onto it. |
| Batch 1 | Eight commits from `4d3e62dc` (the `0.1.8` publication record) to `2fc9c427` (release notes): `pietto fmt` `8f4d7020`, `concat` `9088d0a3`, `same_value` and always-None numbers `9f364198`, JOIN aggregates and grouped keys `d0d30f76`, `Float` row equivalence `ec0af9e5`, `stddev` `55dd2a4e`. One Gate 2 on tree `6ce654b66936774b05b0251964065027ef047308` (25,830 passed, 41 skipped); natural exact-head CI `42000149840` attempt 1 accepted all 19 jobs. |
| Batch 2 | The backward asof JOIN; the PIE-P1012 header warning, an independent step that the owner placed in this release (J2); `Float` `same_value` parity, the MySQL `same_value` GROUP BY key and DISTINCT column, and half-open range witnesses and hints; documentation; the whole-tree test reorganization; the acquisition consolidation; this audit; and the `0.1.9` release commit. One Gate 2 on the final tree; the owner pre-approved the push of the batch and the `v0.1.9` tag and GitHub pre-release after natural CI (2026-11-05); [status](../../status.md) records its head and natural CI. |

## Closure conditions

### 1. The eight must-do items, each with a positive and an exact refusal

Each refusal test pins a diagnostic code with its text, or the blocker detail
of an emission refusal. F2 adds no refusal: it removes an error that hid later
ones, so its row pins the warning that stays.

| Item | Admitted | Refused exactly |
| --- | --- | --- |
| D-11 sound JOIN aggregates, with B14 (a grouped query's GROUP BY keys as a unique key) | `test_semantic_join_grouping.py::test_joined_aggregates_admit_exactly_their_proved_rows`, `test_semantic_join_fanout.py::test_count_and_set_insensitive_aggregates_are_exempt`, `test_sql_joins.py::test_a_joined_aggregate_emits_exactly_where_its_rows_are_proved` | `test_sql_joins.py::test_a_join_on_part_of_a_grouped_querys_keys_stays_blocked`; the refused rows of `test_joined_aggregates_admit_exactly_their_proved_rows`; `test_semantic_join_grouping.py::test_an_outer_match_already_in_on_is_not_asked_for_again` (PIE-S2381 text) |
| D-12 arithmetic with an always-None operand | `test_sql_rows.py::test_int_arithmetic_with_a_typed_null_casts_it_to_the_int_carrier`, `test_sql_postgres_relations.py` and `test_sql_mysql_relations.py::test_sql_types_an_always_null_number_as_pietto_types_it` | `test_sql_rows.py::test_an_always_null_value_outside_the_row_boundary_names_its_rule`, `test_sql_project_scalar_expressions.py::test_a_typed_null_decimal_output_refuses_instead_of_crashing` |
| F2: an always-null project output no longer hides later errors | `test_project_semantic_model.py::test_an_always_null_output_checks_as_in_a_single_file`, `test_project_query_result.py::test_explicit_project_select_test_of_an_untyped_let_completes` | `test_project_semantic_model.py::test_a_relation_a_set_operation_reads_keeps_its_untyped_null_warning` (`check` passes with exactly one PIE-S2385 warning) |
| `concat` | `test_semantic_functions.py::test_concat_joins_text_and_is_null_when_any_argument_is`, `test_sql_postgres_relations.py::test_concat_emits_the_null_propagating_postgres_operator`, `test_sql_mysql_relations.py::test_concat_renders_mysql_concat` | `test_semantic_functions.py::test_concat_refuses_one_argument_and_a_non_text_argument`, `test_sql_project_scalar_expressions.py::test_mysql_project_sql_refuses_concat`, `::test_concat_of_only_none_stays_fail_closed` |
| `stddev` | `test_semantic_sum_avg_semantics.py::test_stddev_of_an_int_or_float_field_is_a_nullable_float`, `test_sql_sum_avg_sql.py::test_postgres_stddev_casts_the_exact_sample_variance_once` | `test_semantic_sum_avg_semantics.py::test_stddev_misuse_keeps_the_aggregate_diagnostics`, `test_sql_sum_avg_sql.py::test_mysql_stddev_is_the_sample_deviation_of_a_float_only`, `test_semantic_inline_functions.py::test_only_a_def_stddev_is_told_to_rename_for_the_new_aggregate` |
| `Float` value contract (row equivalence and project emission, Branch B) | `test_sql_result_bounds.py::test_float_distinct_merges_zeros_on_postgres_only`, `test_plan_set_bodies.py::test_float_set_bodies_build_and_verify`, `test_project_numeric_carriers.py::test_float_equivalence_and_order_arms_admit_postgres_finite_only` | `test_project_numeric_carriers.py::test_mysql_float_equality_between_two_row_reads_stays_refused`, `test_sql_set_forms.py::test_the_verifier_refuses_a_mysql_float_intersect_on_its_own`, `test_sql_joins.py::test_a_full_join_outside_its_reviewed_rule_is_refused_at_its_on_clause` |
| `same_value` | `test_semantic_functions.py::test_same_value_is_a_bool_that_is_never_none`, `test_sql_project_scalar_expressions.py::test_same_value_is_a_null_safe_never_null_bool` | `test_semantic_functions.py::test_same_value_refuses_none_and_operands_that_do_not_compare`, `::test_same_value_refuses_none_reaching_it_through_a_def_argument`, `test_sql_project_scalar_expressions.py::test_same_value_is_not_yet_a_project_join_match_condition` (blocker detail `match_condition_not_in_row_domain`) |
| Backward asof JOIN | `test_semantic_join_asof.py::test_admitted_asof_joins_check_clean`, `::test_a_file_and_a_project_admit_the_asof_join_example`, `test_sql_join_emission.py::test_postgresql_renders_an_asof_join_as_the_latest_lateral_row` | `test_semantic_join_asof.py::test_each_refused_asof_form_has_one_diagnostic_and_its_hint`, `::test_a_project_refuses_each_asof_form_as_a_single_file_does`, `test_sql_join_emission.py::test_mysql_refuses_an_asof_join_at_its_relation` |

`now()` was decided only as a meaning (Gate 1: the UTC statement snapshot);
its implementation is not a Phase72 item.

### 2. Layered closure of each new family

A new family needs an emission, a compiled-bundle and a live-template witness
before it ships. A dash means that no test of that layer is named here.

| Family | Emission | Compiled bundle | Live template |
| --- | --- | --- | --- |
| `same_value` | `test_sql_project_scalar_expressions.py::test_same_value_emission_admits_exactly_what_equality_admits` | `::test_same_value_is_a_null_safe_never_null_bool` builds, loads and replays it | `test_execution_compiled_families.py::test_scalar_families_replay_and_bind_their_live_template[postgres-same_value]`, `[mysql-same_value]` |
| Typed NULL in `Int` arithmetic | `test_sql_rows.py::test_int_arithmetic_with_a_typed_null_casts_it_to_the_int_carrier` | `test_execution_compiled_families.py::test_scalar_families_replay_and_bind_their_live_template[postgres-typed_null]`, `[mysql-typed_null]` build, load and replay it | `test_execution_compiled_families.py::test_scalar_families_replay_and_bind_their_live_template[postgres-typed_null]`, `[mysql-typed_null]` |
| Project PostgreSQL `concat` | `test_sql_project_scalar_expressions.py::test_q1_text_result_growth_uses_the_derived_bound_not_input_length` | the same test builds, loads and replays it | `test_execution_compiled_families.py::test_scalar_families_replay_and_bind_their_live_template[postgres-concat]` |
| D-11 and B14 | `test_sql_joins.py::test_a_joined_aggregate_emits_exactly_where_its_rows_are_proved` | `test_execution_compiled_families.py::test_unmatched_row_value_proofs_replay_with_the_compiled_records` | `test_execution_compiled_families.py::test_sound_joined_aggregates_replay_and_bind_their_live_template` (8 nodes, both targets) |
| `Float` project forms | `test_project_numeric_carriers.py::test_float_equivalence_and_order_arms_admit_postgres_finite_only` | `test_execution_compiled_families.py::test_float_equality_and_order_replay_from_compiled_input`, `test_execution_compiled_bundle.py::test_float_set_export_keeps_kind_quantifier_and_operand_order` | `test_execution_compiled_families.py::test_float_equality_and_order_replay_from_compiled_input` (10 nodes) now also binds the live template |
| `stddev` | `test_sql_sum_avg_sql.py::test_postgres_stddev_casts_the_exact_sample_variance_once` | `test_execution_compiled_families.py::test_postgresql_stddev_replays_from_compiled_input`, `test_execution_compiled_bundle.py::test_a_stddev_template_binds_its_header_read_and_renders_the_same_sql` (a compiled template) | `test_execution_compiled_bundle.py::test_a_stddev_template_binds_its_header_read_and_renders_the_same_sql` binds the loaded compiled and the live template |
| Asof JOIN | `test_sql_join_emission.py::test_postgresql_renders_an_asof_join_as_the_latest_lateral_row` | `test_execution_compiled_families.py::test_an_asof_join_emits_its_latest_row_as_an_anti_join_and_replays` | the same test: emission, compiled replay and live template give one statement |
| Half-open range `start <= ts < stop` | `test_execution_compiled_bundle.py::test_a_half_open_range_template_renders_the_emitted_sql` | the same test, on both targets | the same test, on both targets |

Every family above has an emission, a compiled-bundle and a live-template witness.

`pietto fmt` and the PIE-P1012 warning add no value, relation or call family.

### 3. MySQL

Only a form that a real MySQL run compared with PostgreSQL and the reference
is open on MySQL; every other form fails closed with a fixed diagnostic. MySQL
may trail PostgreSQL by two to three releases (owner, 2026-10-28).

| Feature | MySQL in `0.1.9` | Next MySQL owner |
| --- | --- | --- |
| `concat` | single file open (`CONCAT`); project refused | Phase74 MySQL catch-up |
| `same_value` | open in both modes; `Text` relies on the `utf8mb4_0900_bin` premise; two row `Float` operands refused as `==` is | — |
| D-11, B14, D-12, F2, typed NULL | opened form by form after the real-database runs; project `sum(Int)` keeps PIE-B1004 | Phase77 for project `sum(Int)` |
| `Float` | Branch B: comparisons with a literal or parameter and ordering inequalities open; GROUP BY, relation ORDER, DISTINCT, UNION DISTINCT, INTERSECT, EXCEPT, and `==` or `!=` between two row reads refused | Phase74 MySQL catch-up, with a ±0 guard |
| Single-file DISTINCT | as in `0.1.8`: the `Float` contract left single-file SQL bytes unchanged | Phase74 MySQL catch-up |
| `stddev` | single-file `Float` open (`STDDEV_SAMP`); `Int` refused in both modes; project `Float` PIE-B1004 | Phase77 |
| Asof JOIN | refused in both modes | Phase74 MySQL catch-up candidate, otherwise Phase77 |
| `start <= ts < stop` | open; one form on both targets | — |

### 4. Multi-level collections stay unsupported

The Phase72 initiation that Gate 1 adopted lists multi-level collections as a
non-goal, beside nested GROUP/DISTINCT keys and whole-value equality of nested
values. Phase72 adds no nesting level and changes no nested refusal.

### 5. Decisions, audit, handoff and lessons

The [decision record](../../decisions.md#phase72--owner-decisions-2026-11-04-and-2026-11-05)
holds the Gate 1 rules and the later answers. This audit, the
[Phase73 handoff](phase73-handoff.md) and the Phase72 section of the
[engineering lessons](../../references/engineering-lessons.md#phase72) are in
the closeout documentation commit.

### 6. Three-layer acceptance and real databases

Each family was checked as real (it runs on the database), present (the
documented spelling reaches emission) and connected (the compiled bundle
replays the emitted SQL; §2 shows which families also have a live-template
test). The campaigns used local images by ID, no network, their own
containers and a reference written before the run, on PostgreSQL 18.6 and
MySQL 8.4.12; W5 instead ran the target-conformance manifest on the
facility's pinned images over the facility's internal network:

| Run | What it checked | Result |
| --- | --- | --- |
| Campaign 1 | `Float` ±0 and set-operation facts, `concat` facts | 885 statements, 410 of them compared with the reference, and a fix round that compared 646 more; MySQL kept `-0.0` and `0.0` apart where the reference merged them, so the MySQL `Float` rule (Branch B) follows from them |
| Campaign 2 | `same_value`, typed NULL, F2, D-11 and B14 | 325 statements equal to the reference on both databases |
| W5 | the `Float` lane on the target-conformance manifest | full manifest on both databases, cleanup clean |
| Campaign 3 | `stddev` | 80 statements, 144 cells, no failure; overflow raises an error on both |
| Campaign 4 | asof JOIN | PostgreSQL: 34 single-file and 30 project statements equal, 7 of 7 mutations caught |
| Campaign 5 | project `Float` `same_value` | 22 statements, no failure |
| Campaign 6 | MySQL project `==` of `Bool` through GROUP BY and DISTINCT | values correct; MySQL sends `LONG`, which the reader accepts |
| Total campaign | every earlier statement re-emitted from the final tree, plus the half-open range and the MySQL forms no campaign had run | recorded with the batch-2 Gate 2 |

CI health was read at the start (Gate 0 run `41766849826`) and at the midpoint
(batch 1 run `42000149840`); the closing reading is the batch-2 natural CI.

## Budget

| Account | Cap | Use |
| --- | --- | --- |
| Phase72 | C150 / F600 / D1200 / S8 | about D590 and F125 at the midpoint tally (2026-11-04); C well below its cap |
| `pietto fmt` step | C20 / F40 / D150 / S1 | about F30 and D129 after three review rounds and two lead repair rounds |
| Header warning step | C15 / F30 / D120 / S1 | C10, F18 and about D80 in the lane round, then one lead repair |
| Whole-tree reorganization | C15 / F40 / D200 / S1 | lane C7 / F6 / D19; 135 test nodes removed, 114 moved |

## Failed histories kept

- Batch 1 Gate 2 failed twice before passing: on tree `74a4a8da` the test
  type check found 14 errors in four lane tests, and on tree `6b863e0d` two
  tests failed (a layering policy and a cycle-internals guard). Both repairs
  went into the slices they belong to; the failed runs stay recorded.
- The asof lane's first project lowering spike failed; the lowering used
  instead covers only the contexts the second spike proved, and the others
  keep a fixed refusal.
- The batch-1 MySQL refusal of a project `same_value` GROUP BY key or
  DISTINCT column rested on a wrong reading of the result reader; campaign 6
  showed it, and batch 2 re-admits the form.
- Two lane process failures are kept as lessons: subagents answered a
  relayed owner message instead of working, and one lane wrote a comparison
  verdict from fabricated outputs, which was removed and rebuilt from real
  outputs before use.
