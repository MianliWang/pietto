"""Exact test-only authority for the currently active Phase 54 Gate 2."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[1]

PHASE54_ACTIVE_GATE2_MARKER = "PHASE54_SLICE12_GATE2"
PHASE54_ACTIVE_GATE2_BASE = "bc46faff1c9aa71f583ed7d2964b651cc659bc90"
PHASE54_POST_REVIEW_PRODUCT_REPAIR1_BASE = "6104002486d21b7b25dbec74d037c0fc7cc5099a"
PHASE54_POST_REVIEW_PRODUCT_REPAIR1_BRANCH = (
    "phase54/slice10-cross-module-relation-row-facts"
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR2_BASE = "3caa5e52be41cd7e1ed0ed364f2d62574adce840"
PHASE54_POST_REVIEW_PRODUCT_REPAIR2_BRANCH = (
    "phase54/slice10-cross-module-relation-row-facts"
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR3_BASE = "17a5b01e555930537334d4d0bcf3480e332b7e91"
PHASE54_POST_REVIEW_PRODUCT_REPAIR3_BRANCH = (
    "phase54/slice10-cross-module-relation-row-facts"
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR4_BASE = "3f057874a1bec524da38b58c243267f4590c167b"
PHASE54_POST_REVIEW_PRODUCT_REPAIR4_BRANCH = (
    "phase54/slice10-cross-module-relation-row-facts"
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR5_BASE = "fcdd02b5604c2b84d861b593a1887eaeb4620c91"
PHASE54_POST_REVIEW_PRODUCT_REPAIR5_BRANCH = (
    "phase54/slice10-cross-module-relation-row-facts"
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR6_BASE = "c73e5ea0628d821ada5a8cbb93102bae69768600"
PHASE54_POST_REVIEW_PRODUCT_REPAIR6_BRANCH = (
    "phase54/slice10-cross-module-relation-row-facts"
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR7_BASE = "a5df3ed264c443d902831fe532d265ac1e452158"
PHASE54_POST_REVIEW_PRODUCT_REPAIR7_BRANCH = (
    "phase54/slice10-cross-module-relation-row-facts"
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR8_BASE = "7b96b416d963e67624a461ec906ab2fe14630380"
PHASE54_POST_REVIEW_PRODUCT_REPAIR8_BRANCH = (
    "phase54/slice10-cross-module-relation-row-facts"
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR9_BASE = "38353a00bdaf6b1edb9a0eb53ada1a3249b6ae79"
PHASE54_POST_REVIEW_PRODUCT_REPAIR9_BRANCH = (
    "phase54/slice10-cross-module-relation-row-facts"
)
PHASE54_SLICE11_PR_CI_REPAIR_BASE = "c6aba9522f7e16e358005f86cfb119dd6d005463"
PHASE54_SLICE11_PR_CI_REPAIR_BRANCH = (
    "phase54/slice11-module-attribution-dependency-origin-provenance-lineage"
)
PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_BASE = "691db405a7e787adec5d7bd0498330b070bf6b75"
PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_BRANCH = (
    "phase54/slice11-module-attribution-dependency-origin-provenance-lineage"
)
PHASE54_SLICE11_PYTHON313_REPAIR_BASE = "35895e72877925603f90159d6830be91a64002e4"
PHASE54_SLICE11_PYTHON313_REPAIR_BRANCH = (
    "phase54/slice11-module-attribution-dependency-origin-provenance-lineage"
)
PHASE54_SLICE12_PR_CI_REPAIR_BASE = "1c8a9ff9ce95563da0312dc640e6ac30248168e2"
PHASE54_SLICE12_PR_CI_REPAIR_BRANCH = "phase54/slice12-semantic-fact-preservation"
PHASE54_SLICE12_PRODUCT_REPAIR3_BASE = "ab1445fcb8b3af9a14f0230edb5680c523a754d1"
PHASE54_SLICE12_PRODUCT_REPAIR3_BRANCH = "phase54/slice12-semantic-fact-preservation"
PHASE54_SLICE12_PRODUCT_REPAIR3_SUBJECT = (
    "Fix Phase 54 Slice 12 semantic fact preservation"
)
PHASE54_SLICE12_PRODUCT_REPAIR10_BASE = "0aeab98d9fee99f8e5375ba09b30945ecd532baf"
PHASE54_SLICE12_PRODUCT_REPAIR10_BRANCH = "phase54/slice12-semantic-fact-preservation"
PHASE54_SLICE12_PRODUCT_REPAIR10_PARENT = "edb574d1c489f4944d04d687feac26d6f2f72303"
PHASE54_SLICE12_PRODUCT_REPAIR10_SUBJECT = (
    "Fix Phase 54 Slice 12 nested let expression facts"
)
PHASE54_SLICE12_PRODUCT_REPAIR10_REVIEWED_TREE_TRAILER = "Pietto-Reviewed-Tree"
PHASE54_SLICE12_PRODUCT_REPAIR11_BASE = "0aeab98d9fee99f8e5375ba09b30945ecd532baf"
PHASE54_SLICE12_PRODUCT_REPAIR11_BRANCH = "phase54/slice12-semantic-fact-preservation"
PHASE54_SLICE12_PRODUCT_REPAIR11_SUBJECT = (
    "Fix Phase 54 Slice 12 nonconcrete expression facts"
)
PHASE54_SLICE12_PRODUCT_REPAIR11_REVIEWED_TREE_TRAILER = "Pietto-Reviewed-Tree"
PHASE54_SLICE12_PRODUCT_REPAIR12_BASE = "0aeab98d9fee99f8e5375ba09b30945ecd532baf"
PHASE54_SLICE12_PRODUCT_REPAIR12_BRANCH = "phase54/slice12-semantic-fact-preservation"
PHASE54_SLICE12_PRODUCT_REPAIR12_SUBJECT = (
    "Fix Phase 54 Slice 12 clause readiness atomicity"
)
PHASE54_SLICE12_PRODUCT_REPAIR12_REVIEWED_TREE_TRAILER = "Pietto-Reviewed-Tree"
PHASE54_SLICE12_PRODUCT_REPAIR13_BASE = "0aeab98d9fee99f8e5375ba09b30945ecd532baf"
PHASE54_SLICE12_PRODUCT_REPAIR13_BRANCH = "phase54/slice12-semantic-fact-preservation"
PHASE54_SLICE12_PRODUCT_REPAIR13_SUBJECT = (
    "Fix Phase 54 Slice 12 clause and reader closure"
)
PHASE54_SLICE12_PRODUCT_REPAIR13_REVIEWED_TREE_TRAILER = "Pietto-Reviewed-Tree"
PHASE54_SLICE12_PRODUCT_REPAIR14_BASE = "0aeab98d9fee99f8e5375ba09b30945ecd532baf"
PHASE54_SLICE12_PRODUCT_REPAIR14_BRANCH = "phase54/slice12-semantic-fact-preservation"
PHASE54_SLICE12_PRODUCT_REPAIR14_SUBJECT = (
    "Fix Phase 54 Slice 12 window lineage preservation"
)
PHASE54_SLICE12_PRODUCT_REPAIR14_REVIEWED_TREE_TRAILER = "Pietto-Reviewed-Tree"
PHASE54_SLICE12_MECHANICAL_REPAIR3_BASE = "f7cf045358db7280acb66288d30e0bf64cce966d"
PHASE54_SLICE12_MECHANICAL_REPAIR3_BRANCH = "phase54/slice12-semantic-fact-preservation"
PHASE54_SLICE12_MECHANICAL_REPAIR3_SUBJECT = (
    "Fix Phase 54 Slice 12 clean topic manifest"
)
PHASE54_SLICE12_MECHANICAL_REPAIR3_REVIEWED_TREE_TRAILER = "Pietto-Reviewed-Tree"
ADDED_PATHS = {
    "docs/spec/phase54-slice12-semantic-fact-preservation-v1.md",
    "src/pietto/_project/module_semantic_fact_preservation.py",
    "tests/test_phase54_semantic_fact_preservation.py",
}
PHASE54_POST_REVIEW_PRODUCT_REPAIR1_TO_8_SEED_PATHS = {
    "src/pietto/_project/module_relation_resolution.py",
    "tests/_phase54_active_gate2_manifest.py",
    "tests/test_phase54_cross_module_table_query_relation_resolution_row_facts_legacy_compatibility.py",
}
MECHANICAL_READER_PATHS = {
    "tests/test_maintenance_phase2_agent_workflow_and_roadmap.py",
    "tests/test_maintenance_phase2_code_audit_security_review.py",
    "tests/test_maintenance_phase2_completion_audit.py",
    "tests/test_maintenance_phase2_external_skills_evaluation.py",
    "tests/test_maintenance_phase3_ci_parallelization.py",
    "tests/test_maintenance_phase3_completion_audit.py",
    "tests/test_maintenance_phase3_developer_workflow.py",
    "tests/test_maintenance_phase3_non_pytest_validation_optimization.py",
    "tests/test_maintenance_phase3_parallel_safety.py",
    "tests/test_maintenance_phase3_validation_acceleration_scope_lock.py",
    "tests/test_maintenance_phase4_benchmark_evidence_decision.py",
    "tests/test_maintenance_phase4_completion_audit.py",
    "tests/test_maintenance_phase4_worker_strategy_benchmark_protocol.py",
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_packaging_smoke.py",
    "tests/test_phase11_validation_entrypoint.py",
    "tests/test_phase12_completion_audit.py",
    "tests/test_phase12_composition_cli_json_goldens.py",
    "tests/test_phase16_completion_audit.py",
    "tests/test_phase16_current_syntax_surface_audit.py",
    "tests/test_phase16_language_direction_audit.py",
    "tests/test_phase16_safety_deferral_sql_portability.py",
    "tests/test_phase21_group_by_hardening_audit.py",
    "tests/test_phase24_aggregate_expression_arguments_readiness.py",
    "tests/test_phase24_cli_json_output_hardening.py",
    "tests/test_phase24_completion_audit.py",
    "tests/test_phase25_completion_audit.py",
    "tests/test_phase26_completion_audit.py",
    "tests/test_phase27_completion_audit.py",
    "tests/test_phase28_completion_audit.py",
    "tests/test_phase29_completion_audit.py",
    "tests/test_phase30_completion_audit.py",
    "tests/test_phase33_completion_audit.py",
    "tests/test_phase35_completion_audit.py",
    "tests/test_phase35_internal_helper_simplification_candidate_decision.py",
    "tests/test_phase35_safe_simplification_candidate_decision.py",
    "tests/test_phase35_validation_delivery_workflow_polish.py",
    "tests/test_phase36_completion_audit.py",
    "tests/test_phase36_public_surface_stability_hardening.py",
    "tests/test_phase36_status_housekeeping.py",
    "tests/test_phase37_aggregate_filter_distinct_modifier_deferral.py",
    "tests/test_phase37_candidate_decision.py",
    "tests/test_phase37_completion_audit.py",
    "tests/test_phase37_count_distinct_expression_widening_boundary.py",
    "tests/test_phase37_count_expression_mvp_decision.py",
    "tests/test_phase37_current_aggregate_matrix.py",
    "tests/test_phase37_decimal_aggregate_expression_boundary.py",
    "tests/test_phase37_grouped_aggregate_interaction_hardening.py",
    "tests/test_phase37_min_max_expression_boundary.py",
    "tests/test_phase37_nested_aggregate_composition_hardening.py",
    "tests/test_phase38_binding_filter_post_aggregate_roadmap.py",
    "tests/test_phase38_boundary_types_capability_contract.py",
    "tests/test_phase38_candidate_decision.py",
    "tests/test_phase38_completion_audit.py",
    "tests/test_phase38_count_family_semantics_contract.py",
    "tests/test_phase38_distinct_collation_ordering_readiness.py",
    "tests/test_phase38_type_capability_matrix_contract.py",
    "tests/test_phase39_candidate_decision.py",
    "tests/test_phase39_completion_audit.py",
    "tests/test_phase39_count_expression_mvp_contract.py",
    "tests/test_phase40_completion_audit.py",
    "tests/test_phase40_let_binding_model_candidate.py",
    "tests/test_phase40_let_binding_syntax_scope_contract.py",
    "tests/test_phase41_decimal_precision_scale_candidate.py",
    "tests/test_phase41_decimal_precision_scale_completion_audit.py",
    "tests/test_phase43_completion_audit.py",
    "tests/test_phase44_completion_audit.py",
    "tests/test_phase44_project_config_schema_contract.py",
    "tests/test_phase45_project_semantic_scope_lock.py",
    "tests/test_phase46_completion_audit.py",
    "tests/test_phase46_project_compatibility_hardening.py",
    "tests/test_phase46_project_json_v2_relation_cycle_diagnostics.py",
    "tests/test_phase46_project_relation_cycle_detection.py",
    "tests/test_phase46_project_relation_cycle_diagnostics.py",
    "tests/test_phase46_project_relation_dependency_edge_collection.py",
    "tests/test_phase46_project_relation_dependency_graph_scaffold.py",
    "tests/test_phase46_project_semantic_continuation_scope_lock.py",
    "tests/test_phase47_completion_audit.py",
    "tests/test_phase47_direct_bare_field_row_schema.py",
    "tests/test_phase47_direct_field_rename_row_schema.py",
    "tests/test_phase47_direct_row_schema_scope_lock.py",
    "tests/test_phase47_downstream_readiness_hardening.py",
    "tests/test_phase47_private_row_schema_scaffold.py",
    "tests/test_phase47_project_json_privacy_hardening.py",
    "tests/test_phase47_qualified_field_row_schema.py",
    "tests/test_phase47_source_row_schema_propagation.py",
    "tests/test_phase47_unknown_direct_field_diagnostics.py",
    "tests/test_phase48_completion_audit_status_lock.py",
    "tests/test_phase48_deterministic_propagation_order_contract.py",
    "tests/test_phase48_downstream_diagnostics_ordering_hardening.py",
    "tests/test_phase48_project_json_private_fact_privacy_readiness.py",
    "tests/test_phase48_propagated_field_provenance_lineage_hardening.py",
    "tests/test_phase48_query_to_query_multi_hop_propagation.py",
    "tests/test_phase48_query_to_query_row_schema_scope_lock.py",
    "tests/test_phase48_schema_availability_state_carrier.py",
    "tests/test_phase48_table_upstream_row_schema_propagation.py",
    "tests/test_phase48_upstream_non_concrete_schema_propagation.py",
    "tests/test_phase49_compatibility_privacy_hash_lock_readiness.py",
    "tests/test_phase49_completion_audit_status_lock.py",
    "tests/test_phase49_computed_alias_origin_provenance_privacy.py",
    "tests/test_phase49_computed_alias_project_row_schema_mvp.py",
    "tests/test_phase49_computed_let_multi_hop_row_lineage.py",
    "tests/test_phase49_let_visibility_order_shadowing_hardening.py",
    "tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py",
    "tests/test_phase49_private_row_level_dependency_graph_scaffold.py",
    "tests/test_phase49_project_let_scope_value_facts.py",
    "tests/test_phase49_project_row_expression_schema_helper_contract.py",
    "tests/test_phase49_project_row_expression_type_nullability_adapter.py",
    "tests/test_phase49_row_level_computed_let_schema_scope_lock.py",
    "tests/test_phase49_selected_let_derived_output_schema.py",
    "tests/test_phase49_unknown_deferred_diagnostic_ordering_hardening.py",
    "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
    "tests/test_phase50_completion_audit_and_status_lock.py",
    "tests/test_phase50_explain_public_metadata_package_integration_boundary.py",
    "tests/test_phase50_import_module_export_readiness.py",
    "tests/test_phase50_multi_dialect_capability_ecosystem_readiness.py",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
    "tests/test_phase50_postgresql_extension_capability_readiness.py",
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    "tests/test_phase50_semantic_package_model_readiness.py",
    "tests/test_phase50_type_system_gap_capability_readiness.py",
    "tests/test_phase50_window_function_readiness.py",
    "tests/test_phase51_aggregate_grouped_downstream_propagation.py",
    "tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py",
    "tests/test_phase51_aggregate_grouped_output_schema_foundation_scope_lock.py",
    "tests/test_phase51_aggregate_grouped_state_duplicate_hardening.py",
    "tests/test_phase51_aggregate_only_project_row_schema.py",
    "tests/test_phase51_clause_dependency_fail_closed.py",
    "tests/test_phase51_completion_audit_and_status_lock.py",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
    "tests/test_phase51_group_key_project_row_schema.py",
    "tests/test_phase51_grouped_aggregate_project_row_schema.py",
    "tests/test_phase51_private_result_role_output_identity.py",
    "tests/test_phase51_selected_let_accepted_expression_aggregate.py",
    "tests/test_phase52_aggregate_signature_algebra_facts.py",
    "tests/test_phase52_completion_audit_and_status_lock.py",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py",
    "tests/test_phase52_expression_stage_clause_capability_facts.py",
    "tests/test_phase52_fail_closed_capability_lookup.py",
    "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py",
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
    "tests/test_phase52_private_capability_fact_foundation.py",
    "tests/test_phase52_scalar_function_operator_signature_facts.py",
    "tests/test_phase53_completion_audit_and_status_lock.py",
    "tests/test_phase53_generic_type_variable_exact_compatibility_contract.py",
    "tests/test_phase53_grouped_result_ranking_aggregate_result_inputs_bounded_let_visibility_contract.py",
    "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
    "tests/test_phase53_multiple_window_outputs_final_order_alias_downstream_schema_lineage_contract.py",
    "tests/test_phase53_nullability_algebra_signature_result_formula_contract.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
    "tests/test_phase53_percent_rank_cume_dist_ntile_contract.py",
    "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py",
    "tests/test_phase53_rank_dense_rank_peer_semantics_contract.py",
    "tests/test_phase53_row_number_direct_field_mvp_contract.py",
    "tests/test_phase53_window_generic_nullability_foundation_scope_lock.py",
    "tests/test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py",
    "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
    "tests/test_phase53_window_spec_function_identity_ast_contract.py",
    "tests/test_phase53_window_syntax_contextual_grammar_contract.py",
    "tests/test_phase54_cross_module_table_query_relation_resolution_row_facts_legacy_compatibility.py",
    "tests/test_phase54_cross_module_type_alias_enum_shape_source_resolution.py",
    "tests/test_phase54_import_export_contextual_grammar_ast.py",
    "tests/test_phase54_local_export_visibility_module_facades.py",
    "tests/test_phase54_local_import_module_export_foundation_scope_lock.py",
    "tests/test_phase54_module_attribution_dependency_origin_provenance_lineage.py",
    "tests/test_phase54_module_graph_cycles_diagnostics_deterministic_ordering.py",
    "tests/test_phase54_module_identity_selected_input_index_trusted_local_loader.py",
    "tests/test_phase54_module_qualified_nominal_declaration_catalogs.py",
    "tests/test_phase54_named_import_alias_binding_environments_collision_rules.py",
    "tests/test_phase54_schema_v2_explicit_module_carrier.py",
}
PHASE54_POST_REVIEW_PRODUCT_REPAIR2_TO_8_READER_PATHS = {
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_packaging_smoke.py",
    "tests/test_phase11_validation_entrypoint.py",
    "tests/test_phase12_completion_audit.py",
    "tests/test_phase12_composition_cli_json_goldens.py",
    "tests/test_phase33_completion_audit.py",
    "tests/test_phase51_aggregate_grouped_downstream_propagation.py",
    "tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py",
    "tests/test_phase51_completion_audit_and_status_lock.py",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
    "tests/test_phase52_aggregate_signature_algebra_facts.py",
    "tests/test_phase52_completion_audit_and_status_lock.py",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py",
    "tests/test_phase52_expression_stage_clause_capability_facts.py",
    "tests/test_phase52_fail_closed_capability_lookup.py",
    "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py",
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
    "tests/test_phase52_private_capability_fact_foundation.py",
    "tests/test_phase52_scalar_function_operator_signature_facts.py",
    "tests/test_phase53_completion_audit_and_status_lock.py",
    "tests/test_phase53_generic_type_variable_exact_compatibility_contract.py",
    "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
    "tests/test_phase53_multiple_window_outputs_final_order_alias_downstream_schema_lineage_contract.py",
    "tests/test_phase53_nullability_algebra_signature_result_formula_contract.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
    "tests/test_phase53_percent_rank_cume_dist_ntile_contract.py",
    "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py",
    "tests/test_phase53_rank_dense_rank_peer_semantics_contract.py",
    "tests/test_phase53_row_number_direct_field_mvp_contract.py",
    "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
    "tests/test_phase53_window_spec_function_identity_ast_contract.py",
    "tests/test_phase54_cross_module_type_alias_enum_shape_source_resolution.py",
    "tests/test_phase54_local_export_visibility_module_facades.py",
    "tests/test_phase54_local_import_module_export_foundation_scope_lock.py",
    "tests/test_phase54_module_graph_cycles_diagnostics_deterministic_ordering.py",
    "tests/test_phase54_module_qualified_nominal_declaration_catalogs.py",
    "tests/test_phase54_named_import_alias_binding_environments_collision_rules.py",
}
PHASE54_SLICE10_PRIOR_MECHANICAL_READER_PATHS = frozenset(
    {
        "tests/test_phase11_ci_workflow.py",
        "tests/test_phase11_completion_audit.py",
        "tests/test_phase11_generated_guard.py",
        "tests/test_phase11_golden_policy.py",
        "tests/test_phase11_packaging_smoke.py",
        "tests/test_phase11_validation_entrypoint.py",
        "tests/test_phase12_completion_audit.py",
        "tests/test_phase12_composition_cli_json_goldens.py",
        "tests/test_phase16_completion_audit.py",
        "tests/test_phase16_current_syntax_surface_audit.py",
        "tests/test_phase16_language_direction_audit.py",
        "tests/test_phase16_safety_deferral_sql_portability.py",
        "tests/test_phase21_group_by_hardening_audit.py",
        "tests/test_phase24_aggregate_expression_arguments_readiness.py",
        "tests/test_phase24_cli_json_output_hardening.py",
        "tests/test_phase24_completion_audit.py",
        "tests/test_phase25_completion_audit.py",
        "tests/test_phase26_completion_audit.py",
        "tests/test_phase27_completion_audit.py",
        "tests/test_phase28_completion_audit.py",
        "tests/test_phase29_completion_audit.py",
        "tests/test_phase30_completion_audit.py",
        "tests/test_phase33_completion_audit.py",
        "tests/test_phase47_project_json_privacy_hardening.py",
        "tests/test_phase50_import_module_export_readiness.py",
        "tests/test_phase51_aggregate_grouped_downstream_propagation.py",
        "tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py",
        "tests/test_phase51_completion_audit_and_status_lock.py",
        "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
        "tests/test_phase52_aggregate_signature_algebra_facts.py",
        "tests/test_phase52_completion_audit_and_status_lock.py",
        "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py",
        "tests/test_phase52_expression_stage_clause_capability_facts.py",
        "tests/test_phase52_fail_closed_capability_lookup.py",
        "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py",
        "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
        "tests/test_phase52_private_capability_fact_foundation.py",
        "tests/test_phase52_scalar_function_operator_signature_facts.py",
        "tests/test_phase53_completion_audit_and_status_lock.py",
        "tests/test_phase53_generic_type_variable_exact_compatibility_contract.py",
        "tests/test_phase53_grouped_result_ranking_aggregate_result_inputs_bounded_let_visibility_contract.py",
        "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
        "tests/test_phase53_multiple_window_outputs_final_order_alias_downstream_schema_lineage_contract.py",
        "tests/test_phase53_nullability_algebra_signature_result_formula_contract.py",
        "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
        "tests/test_phase53_percent_rank_cume_dist_ntile_contract.py",
        "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py",
        "tests/test_phase53_rank_dense_rank_peer_semantics_contract.py",
        "tests/test_phase53_row_number_direct_field_mvp_contract.py",
        "tests/test_phase53_window_generic_nullability_foundation_scope_lock.py",
        "tests/test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py",
        "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
        "tests/test_phase53_window_spec_function_identity_ast_contract.py",
        "tests/test_phase53_window_syntax_contextual_grammar_contract.py",
        "tests/test_phase54_cross_module_type_alias_enum_shape_source_resolution.py",
        "tests/test_phase54_import_export_contextual_grammar_ast.py",
        "tests/test_phase54_local_export_visibility_module_facades.py",
        "tests/test_phase54_local_import_module_export_foundation_scope_lock.py",
        "tests/test_phase54_module_graph_cycles_diagnostics_deterministic_ordering.py",
        "tests/test_phase54_module_identity_selected_input_index_trusted_local_loader.py",
        "tests/test_phase54_module_qualified_nominal_declaration_catalogs.py",
        "tests/test_phase54_named_import_alias_binding_environments_collision_rules.py",
        "tests/test_phase54_schema_v2_explicit_module_carrier.py",
    }
)
NON_READER_MODIFIED_PATHS = {
    "README.md",
    "docs/plan/phase-54-local-import-module-export-foundation.md",
    "docs/spec/pietto-v0.9.md",
    "src/pietto/_project/model.py",
    "src/pietto/_project/row_expression_type_facts.py",
    "tests/_phase54_active_gate2_manifest.py",
}
VALIDATION_READER_PATHS = set(MECHANICAL_READER_PATHS)
MODIFIED_PATHS = NON_READER_MODIFIED_PATHS | MECHANICAL_READER_PATHS
ALLOWLIST_PATHS = ADDED_PATHS | MODIFIED_PATHS
PHASE54_ACTIVE_GATE2_ADDED_PATHS = frozenset(ADDED_PATHS)
PHASE54_ACTIVE_GATE2_MODIFIED_PATHS = frozenset(MODIFIED_PATHS)
PHASE54_ACTIVE_GATE2_DELETED_PATHS = frozenset()
PHASE54_SLICE11_PR_CI_REPAIR_MODIFIED_PATHS = frozenset(
    {
        "tests/_phase54_active_gate2_manifest.py",
        "tests/test_phase50_import_module_export_readiness.py",
        "tests/test_phase51_aggregate_grouped_downstream_propagation.py",
        "tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py",
        "tests/test_phase51_completion_audit_and_status_lock.py",
        "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
        "tests/test_phase52_aggregate_signature_algebra_facts.py",
        "tests/test_phase52_completion_audit_and_status_lock.py",
        "tests/test_phase52_expression_stage_clause_capability_facts.py",
        "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
        "tests/test_phase52_scalar_function_operator_signature_facts.py",
        "tests/test_phase53_completion_audit_and_status_lock.py",
        "tests/test_phase53_grouped_result_ranking_aggregate_result_inputs_bounded_let_visibility_contract.py",
        "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
        "tests/test_phase53_multiple_window_outputs_final_order_alias_downstream_schema_lineage_contract.py",
        "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
        "tests/test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py",
        "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
        "tests/test_phase54_local_export_visibility_module_facades.py",
        "tests/test_phase54_local_import_module_export_foundation_scope_lock.py",
    }
)
PHASE54_SLICE11_PYTHON313_REPAIR_MODIFIED_PATHS = frozenset(
    {
        "tests/_phase54_active_gate2_manifest.py",
        "tests/test_phase50_import_module_export_readiness.py",
        "tests/test_phase51_aggregate_grouped_downstream_propagation.py",
        "tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py",
        "tests/test_phase51_completion_audit_and_status_lock.py",
        "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
        "tests/test_phase52_aggregate_signature_algebra_facts.py",
        "tests/test_phase52_completion_audit_and_status_lock.py",
        "tests/test_phase52_expression_stage_clause_capability_facts.py",
        "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
        "tests/test_phase52_scalar_function_operator_signature_facts.py",
        "tests/test_phase53_completion_audit_and_status_lock.py",
        "tests/test_phase53_grouped_result_ranking_aggregate_result_inputs_bounded_let_visibility_contract.py",
        "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
        "tests/test_phase53_multiple_window_outputs_final_order_alias_downstream_schema_lineage_contract.py",
        "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
        "tests/test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py",
        "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
        "tests/test_phase54_local_export_visibility_module_facades.py",
        "tests/test_phase54_local_import_module_export_foundation_scope_lock.py",
        "tests/test_phase54_module_attribution_dependency_origin_provenance_lineage.py",
        "tests/test_phase54_module_graph_cycles_diagnostics_deterministic_ordering.py",
    }
)
PHASE54_SLICE12_PR_CI_REPAIR_MODIFIED_PATHS = frozenset(
    {
        "tests/_phase54_active_gate2_manifest.py",
        "tests/test_phase50_import_module_export_readiness.py",
        "tests/test_phase51_aggregate_grouped_downstream_propagation.py",
        "tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py",
        "tests/test_phase51_completion_audit_and_status_lock.py",
        "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
        "tests/test_phase52_aggregate_signature_algebra_facts.py",
        "tests/test_phase52_completion_audit_and_status_lock.py",
        "tests/test_phase52_expression_stage_clause_capability_facts.py",
        "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
        "tests/test_phase52_scalar_function_operator_signature_facts.py",
        "tests/test_phase53_completion_audit_and_status_lock.py",
        "tests/test_phase53_grouped_result_ranking_aggregate_result_inputs_bounded_let_visibility_contract.py",
        "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
        "tests/test_phase53_multiple_window_outputs_final_order_alias_downstream_schema_lineage_contract.py",
        "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
        "tests/test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py",
        "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
        "tests/test_phase54_local_export_visibility_module_facades.py",
        "tests/test_phase54_local_import_module_export_foundation_scope_lock.py",
    }
)
PHASE54_SLICE12_PRODUCT_REPAIR3_MODIFIED_PATHS = frozenset(
    {
        "src/pietto/_project/module_semantic_fact_preservation.py",
        "tests/_phase54_active_gate2_manifest.py",
        "tests/test_phase11_ci_workflow.py",
        "tests/test_phase11_completion_audit.py",
        "tests/test_phase11_generated_guard.py",
        "tests/test_phase11_golden_policy.py",
        "tests/test_phase11_packaging_smoke.py",
        "tests/test_phase11_validation_entrypoint.py",
        "tests/test_phase12_completion_audit.py",
        "tests/test_phase12_composition_cli_json_goldens.py",
        "tests/test_phase33_completion_audit.py",
        "tests/test_phase50_import_module_export_readiness.py",
        "tests/test_phase51_aggregate_grouped_downstream_propagation.py",
        "tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py",
        "tests/test_phase51_completion_audit_and_status_lock.py",
        "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
        "tests/test_phase52_aggregate_signature_algebra_facts.py",
        "tests/test_phase52_completion_audit_and_status_lock.py",
        "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py",
        "tests/test_phase52_expression_stage_clause_capability_facts.py",
        "tests/test_phase52_fail_closed_capability_lookup.py",
        "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py",
        "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
        "tests/test_phase52_private_capability_fact_foundation.py",
        "tests/test_phase52_scalar_function_operator_signature_facts.py",
        "tests/test_phase53_completion_audit_and_status_lock.py",
        "tests/test_phase53_generic_type_variable_exact_compatibility_contract.py",
        "tests/test_phase53_grouped_result_ranking_aggregate_result_inputs_bounded_let_visibility_contract.py",
        "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
        "tests/test_phase53_multiple_window_outputs_final_order_alias_downstream_schema_lineage_contract.py",
        "tests/test_phase53_nullability_algebra_signature_result_formula_contract.py",
        "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
        "tests/test_phase53_percent_rank_cume_dist_ntile_contract.py",
        "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py",
        "tests/test_phase53_rank_dense_rank_peer_semantics_contract.py",
        "tests/test_phase53_row_number_direct_field_mvp_contract.py",
        "tests/test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py",
        "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
        "tests/test_phase53_window_spec_function_identity_ast_contract.py",
        "tests/test_phase53_window_syntax_contextual_grammar_contract.py",
        "tests/test_phase54_local_export_visibility_module_facades.py",
        "tests/test_phase54_local_import_module_export_foundation_scope_lock.py",
        "tests/test_phase54_semantic_fact_preservation.py",
    }
)
PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_MODIFIED_PATHS = frozenset(
    {
        "README.md",
        "docs/plan/phase-54-local-import-module-export-foundation.md",
        "docs/spec/phase54-slice11-module-attribution-dependency-origin-provenance-and-lineage-v1.md",
        "docs/spec/phase54-slice8-module-graph-cycles-diagnostics-and-deterministic-ordering-v1.md",
        "docs/spec/pietto-v0.9.md",
        "src/pietto/_project/model.py",
        "src/pietto/_project/module_attribution.py",
        "src/pietto/_project/module_graph.py",
        "src/pietto/_project/module_relation_resolution.py",
        "tests/_phase54_active_gate2_manifest.py",
        "tests/test_phase11_ci_workflow.py",
        "tests/test_phase11_completion_audit.py",
        "tests/test_phase11_generated_guard.py",
        "tests/test_phase11_golden_policy.py",
        "tests/test_phase11_packaging_smoke.py",
        "tests/test_phase11_validation_entrypoint.py",
        "tests/test_phase12_completion_audit.py",
        "tests/test_phase12_composition_cli_json_goldens.py",
        "tests/test_phase21_group_by_hardening_audit.py",
        "tests/test_phase24_aggregate_expression_arguments_readiness.py",
        "tests/test_phase24_cli_json_output_hardening.py",
        "tests/test_phase24_completion_audit.py",
        "tests/test_phase26_completion_audit.py",
        "tests/test_phase27_completion_audit.py",
        "tests/test_phase28_completion_audit.py",
        "tests/test_phase29_completion_audit.py",
        "tests/test_phase30_completion_audit.py",
        "tests/test_phase33_completion_audit.py",
        "tests/test_phase50_import_module_export_readiness.py",
        "tests/test_phase51_aggregate_grouped_downstream_propagation.py",
        "tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py",
        "tests/test_phase51_completion_audit_and_status_lock.py",
        "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
        "tests/test_phase52_aggregate_signature_algebra_facts.py",
        "tests/test_phase52_completion_audit_and_status_lock.py",
        "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py",
        "tests/test_phase52_expression_stage_clause_capability_facts.py",
        "tests/test_phase52_fail_closed_capability_lookup.py",
        "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py",
        "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
        "tests/test_phase52_private_capability_fact_foundation.py",
        "tests/test_phase52_scalar_function_operator_signature_facts.py",
        "tests/test_phase53_completion_audit_and_status_lock.py",
        "tests/test_phase53_generic_type_variable_exact_compatibility_contract.py",
        "tests/test_phase53_grouped_result_ranking_aggregate_result_inputs_bounded_let_visibility_contract.py",
        "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
        "tests/test_phase53_multiple_window_outputs_final_order_alias_downstream_schema_lineage_contract.py",
        "tests/test_phase53_nullability_algebra_signature_result_formula_contract.py",
        "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
        "tests/test_phase53_percent_rank_cume_dist_ntile_contract.py",
        "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py",
        "tests/test_phase53_rank_dense_rank_peer_semantics_contract.py",
        "tests/test_phase53_row_number_direct_field_mvp_contract.py",
        "tests/test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py",
        "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
        "tests/test_phase53_window_spec_function_identity_ast_contract.py",
        "tests/test_phase53_window_syntax_contextual_grammar_contract.py",
        "tests/test_phase54_cross_module_table_query_relation_resolution_row_facts_legacy_compatibility.py",
        "tests/test_phase54_cross_module_type_alias_enum_shape_source_resolution.py",
        "tests/test_phase54_local_export_visibility_module_facades.py",
        "tests/test_phase54_local_import_module_export_foundation_scope_lock.py",
        "tests/test_phase54_module_attribution_dependency_origin_provenance_lineage.py",
        "tests/test_phase54_module_graph_cycles_diagnostics_deterministic_ordering.py",
        "tests/test_phase54_named_import_alias_binding_environments_collision_rules.py",
    }
)
PHASE54_SLICE10_ORIGINAL_ADDED_PATHS = frozenset(
    {
        "docs/spec/phase54-slice10-cross-module-table-query-relation-resolution-row-facts-and-legacy-compatibility-v1.md",
        "src/pietto/_project/module_relation_resolution.py",
        "tests/test_phase54_cross_module_table_query_relation_resolution_row_facts_legacy_compatibility.py",
    }
)
PHASE54_SLICE10_ORIGINAL_NON_READER_MODIFIED_PATHS = frozenset(
    {
        "README.md",
        "docs/plan/phase-54-local-import-module-export-foundation.md",
        "docs/spec/diagnostics.md",
        "docs/spec/pietto-v0.9.md",
        "src/pietto/_project/model.py",
        "tests/_phase54_active_gate2_manifest.py",
    }
)
PHASE54_SLICE10_ORIGINAL_MECHANICAL_READER_PATHS = frozenset(
    PHASE54_SLICE10_PRIOR_MECHANICAL_READER_PATHS
)
PHASE54_SLICE10_ORIGINAL_MODIFIED_PATHS = frozenset(
    PHASE54_SLICE10_ORIGINAL_NON_READER_MODIFIED_PATHS
    | PHASE54_SLICE10_ORIGINAL_MECHANICAL_READER_PATHS
)
PHASE54_SLICE10_ORIGINAL_ALLOWLIST_PATHS = frozenset(
    PHASE54_SLICE10_ORIGINAL_ADDED_PATHS | PHASE54_SLICE10_ORIGINAL_MODIFIED_PATHS
)
PHASE54_SLICE12_PRE_REPAIR10_MECHANICAL_READER_PATHS = frozenset(
    PHASE54_SLICE10_ORIGINAL_MECHANICAL_READER_PATHS
    | {
        "tests/test_phase54_cross_module_table_query_relation_resolution_row_facts_legacy_compatibility.py",
        "tests/test_phase54_module_attribution_dependency_origin_provenance_lineage.py",
    }
)
PHASE54_SLICE12_PRODUCT_REPAIR10_SEED_PATHS = frozenset(
    {
        "src/pietto/_project/model.py",
        "src/pietto/_project/module_semantic_fact_preservation.py",
        "src/pietto/_project/row_expression_type_facts.py",
        "tests/_phase54_active_gate2_manifest.py",
        "tests/test_phase54_semantic_fact_preservation.py",
    }
)
PHASE54_SLICE12_PRODUCT_REPAIR10_REFRESHED_PREEXISTING_READER_PATHS = frozenset(
    {
        "tests/test_phase11_ci_workflow.py",
        "tests/test_phase11_completion_audit.py",
        "tests/test_phase11_generated_guard.py",
        "tests/test_phase11_golden_policy.py",
        "tests/test_phase11_packaging_smoke.py",
        "tests/test_phase11_validation_entrypoint.py",
        "tests/test_phase12_completion_audit.py",
        "tests/test_phase12_composition_cli_json_goldens.py",
        "tests/test_phase33_completion_audit.py",
        "tests/test_phase50_import_module_export_readiness.py",
        "tests/test_phase51_aggregate_grouped_downstream_propagation.py",
        "tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py",
        "tests/test_phase51_completion_audit_and_status_lock.py",
        "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
        "tests/test_phase52_aggregate_signature_algebra_facts.py",
        "tests/test_phase52_completion_audit_and_status_lock.py",
        "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py",
        "tests/test_phase52_expression_stage_clause_capability_facts.py",
        "tests/test_phase52_fail_closed_capability_lookup.py",
        "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py",
        "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
        "tests/test_phase52_private_capability_fact_foundation.py",
        "tests/test_phase52_scalar_function_operator_signature_facts.py",
        "tests/test_phase53_completion_audit_and_status_lock.py",
        "tests/test_phase53_generic_type_variable_exact_compatibility_contract.py",
        "tests/test_phase53_grouped_result_ranking_aggregate_result_inputs_bounded_let_visibility_contract.py",
        "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
        "tests/test_phase53_multiple_window_outputs_final_order_alias_downstream_schema_lineage_contract.py",
        "tests/test_phase53_nullability_algebra_signature_result_formula_contract.py",
        "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
        "tests/test_phase53_percent_rank_cume_dist_ntile_contract.py",
        "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py",
        "tests/test_phase53_rank_dense_rank_peer_semantics_contract.py",
        "tests/test_phase53_row_number_direct_field_mvp_contract.py",
        "tests/test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py",
        "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
        "tests/test_phase53_window_spec_function_identity_ast_contract.py",
        "tests/test_phase53_window_syntax_contextual_grammar_contract.py",
        "tests/test_phase54_cross_module_table_query_relation_resolution_row_facts_legacy_compatibility.py",
        "tests/test_phase54_cross_module_type_alias_enum_shape_source_resolution.py",
        "tests/test_phase54_local_export_visibility_module_facades.py",
        "tests/test_phase54_local_import_module_export_foundation_scope_lock.py",
        "tests/test_phase54_module_attribution_dependency_origin_provenance_lineage.py",
        "tests/test_phase54_module_graph_cycles_diagnostics_deterministic_ordering.py",
        "tests/test_phase54_named_import_alias_binding_environments_collision_rules.py",
    }
)
PHASE54_SLICE12_PRODUCT_REPAIR10_READER_PATHS = frozenset(
    MECHANICAL_READER_PATHS - PHASE54_SLICE12_PRE_REPAIR10_MECHANICAL_READER_PATHS
    | PHASE54_SLICE12_PRODUCT_REPAIR10_REFRESHED_PREEXISTING_READER_PATHS
)
PHASE54_SLICE12_PRODUCT_REPAIR10_MODIFIED_PATHS = frozenset(
    PHASE54_SLICE12_PRODUCT_REPAIR10_SEED_PATHS
    | PHASE54_SLICE12_PRODUCT_REPAIR10_READER_PATHS
)
PHASE54_SLICE12_PRODUCT_REPAIR11_SEED_PATHS = frozenset(
    PHASE54_SLICE12_PRODUCT_REPAIR10_SEED_PATHS
    | {"docs/spec/phase54-slice12-semantic-fact-preservation-v1.md"}
)
PHASE54_SLICE12_PRODUCT_REPAIR11_READER_PATHS = frozenset(
    PHASE54_SLICE12_PRODUCT_REPAIR10_READER_PATHS
)
PHASE54_SLICE12_PRODUCT_REPAIR11_MODIFIED_PATHS = frozenset(
    PHASE54_SLICE12_PRODUCT_REPAIR11_SEED_PATHS
    | PHASE54_SLICE12_PRODUCT_REPAIR11_READER_PATHS
)
PHASE54_SLICE12_PRODUCT_REPAIR12_SEED_PATHS = frozenset(
    PHASE54_SLICE12_PRODUCT_REPAIR11_SEED_PATHS
)
PHASE54_SLICE12_PRODUCT_REPAIR12_READER_PATHS = frozenset(
    PHASE54_SLICE12_PRODUCT_REPAIR11_READER_PATHS
)
PHASE54_SLICE12_PRODUCT_REPAIR12_MODIFIED_PATHS = frozenset(
    PHASE54_SLICE12_PRODUCT_REPAIR12_SEED_PATHS
    | PHASE54_SLICE12_PRODUCT_REPAIR12_READER_PATHS
)
PHASE54_SLICE12_PRODUCT_REPAIR13_SEED_PATHS = frozenset(
    PHASE54_SLICE12_PRODUCT_REPAIR12_SEED_PATHS
)
PHASE54_SLICE12_PRODUCT_REPAIR13_READER_PATHS = frozenset(
    PHASE54_SLICE12_PRODUCT_REPAIR12_READER_PATHS
)
PHASE54_SLICE12_PRODUCT_REPAIR13_MODIFIED_PATHS = frozenset(
    PHASE54_SLICE12_PRODUCT_REPAIR13_SEED_PATHS
    | PHASE54_SLICE12_PRODUCT_REPAIR13_READER_PATHS
)
PHASE54_SLICE12_PRODUCT_REPAIR14_SEED_PATHS = frozenset(
    PHASE54_SLICE12_PRODUCT_REPAIR13_SEED_PATHS
)
PHASE54_SLICE12_PRODUCT_REPAIR14_READER_PATHS = frozenset(
    PHASE54_SLICE12_PRODUCT_REPAIR13_READER_PATHS
)
PHASE54_SLICE12_PRODUCT_REPAIR14_MODIFIED_PATHS = frozenset(
    PHASE54_SLICE12_PRODUCT_REPAIR14_SEED_PATHS
    | PHASE54_SLICE12_PRODUCT_REPAIR14_READER_PATHS
)
PHASE54_SLICE12_MECHANICAL_REPAIR3_SEED_PATHS = frozenset(
    {
        "tests/_phase54_active_gate2_manifest.py",
        "tests/test_phase54_semantic_fact_preservation.py",
    }
)
PHASE54_SLICE12_MECHANICAL_REPAIR3_READER_PATHS = frozenset(
    {
        "tests/test_phase50_import_module_export_readiness.py",
        "tests/test_phase51_aggregate_grouped_downstream_propagation.py",
        "tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py",
        "tests/test_phase51_completion_audit_and_status_lock.py",
        "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
        "tests/test_phase52_aggregate_signature_algebra_facts.py",
        "tests/test_phase52_completion_audit_and_status_lock.py",
        "tests/test_phase52_expression_stage_clause_capability_facts.py",
        "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
        "tests/test_phase52_scalar_function_operator_signature_facts.py",
        "tests/test_phase53_completion_audit_and_status_lock.py",
        "tests/test_phase53_grouped_result_ranking_aggregate_result_inputs_bounded_let_visibility_contract.py",
        "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
        "tests/test_phase53_multiple_window_outputs_final_order_alias_downstream_schema_lineage_contract.py",
        "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
        "tests/test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py",
        "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
        "tests/test_phase54_local_export_visibility_module_facades.py",
        "tests/test_phase54_local_import_module_export_foundation_scope_lock.py",
    }
)
PHASE54_SLICE12_MECHANICAL_REPAIR3_MODIFIED_PATHS = frozenset(
    PHASE54_SLICE12_MECHANICAL_REPAIR3_SEED_PATHS
    | PHASE54_SLICE12_MECHANICAL_REPAIR3_READER_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR1_SEED_PATHS = frozenset(
    PHASE54_POST_REVIEW_PRODUCT_REPAIR1_TO_8_SEED_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR1_READER_PATHS = frozenset(
    PHASE54_SLICE10_PRIOR_MECHANICAL_READER_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR1_MODIFIED_PATHS = frozenset(
    PHASE54_POST_REVIEW_PRODUCT_REPAIR1_TO_8_SEED_PATHS
    | PHASE54_POST_REVIEW_PRODUCT_REPAIR1_READER_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR2_SEED_PATHS = frozenset(
    PHASE54_POST_REVIEW_PRODUCT_REPAIR1_TO_8_SEED_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR2_READER_PATHS = frozenset(
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_TO_8_READER_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR2_MODIFIED_PATHS = frozenset(
    PHASE54_POST_REVIEW_PRODUCT_REPAIR1_TO_8_SEED_PATHS
    | PHASE54_POST_REVIEW_PRODUCT_REPAIR2_TO_8_READER_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR3_SEED_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_SEED_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR3_READER_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_READER_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR3_MODIFIED_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_MODIFIED_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR4_SEED_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_SEED_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR4_READER_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_READER_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR4_MODIFIED_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_MODIFIED_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR5_SEED_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_SEED_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR5_READER_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_READER_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR5_MODIFIED_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_MODIFIED_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR6_SEED_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_SEED_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR6_READER_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_READER_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR6_MODIFIED_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_MODIFIED_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR7_SEED_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_SEED_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR7_READER_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_READER_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR7_MODIFIED_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_MODIFIED_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR8_SEED_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_SEED_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR8_READER_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_READER_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR8_MODIFIED_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_MODIFIED_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR9_SEED_PATHS = frozenset(
    {
        "README.md",
        "tests/_phase54_active_gate2_manifest.py",
        "tests/test_phase54_cross_module_table_query_relation_resolution_row_facts_legacy_compatibility.py",
    }
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR9_READER_PATHS = frozenset(
    PHASE54_SLICE10_PRIOR_MECHANICAL_READER_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR9_MODIFIED_PATHS = frozenset(
    PHASE54_POST_REVIEW_PRODUCT_REPAIR9_SEED_PATHS
    | PHASE54_POST_REVIEW_PRODUCT_REPAIR9_READER_PATHS
)


@dataclass(frozen=True, slots=True, kw_only=True)
class Phase54Gate2RepositoryState:
    """The exact read-only repository facts used by the active manifest gate."""

    marker: str
    branch_oid: str
    branch_head: str
    branch_upstream: str
    ahead: int
    behind: int
    added_paths: frozenset[str]
    modified_paths: frozenset[str]
    deleted_paths: frozenset[str]
    staged_paths: frozenset[str]
    other_paths: frozenset[str]
    worktree_count: int
    shallow: bool
    active_git_operation: bool


def _git_output(args: list[str]) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.rstrip()


def _git_commit_message(revision: str) -> str:
    """Read one full commit message without normalizing trailing spaces."""

    return subprocess.run(
        ["git", "show", "-s", "--format=%B", revision],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.rstrip("\n")


def _phase54_slice12_product_repair10_message_matches_tree(
    message: str,
    tree: str,
) -> bool:
    """Require one canonical final reviewed-tree trailer for the exact tree."""

    if re.fullmatch(r"[0-9a-f]{40}", tree) is None:
        return False
    lines = message.splitlines()
    expected = f"{PHASE54_SLICE12_PRODUCT_REPAIR10_REVIEWED_TREE_TRAILER}: {tree}"
    trailer_key = PHASE54_SLICE12_PRODUCT_REPAIR10_REVIEWED_TREE_TRAILER.casefold()
    reviewed_tree_lines = tuple(
        line for line in lines if line.lstrip().casefold().startswith(trailer_key)
    )
    return (
        len(lines) >= 3
        and lines[0] == PHASE54_SLICE12_PRODUCT_REPAIR10_SUBJECT
        and lines[-2] == ""
        and lines[-1] == expected
        and reviewed_tree_lines == (expected,)
    )


def _phase54_slice12_product_repair11_message_matches_tree(
    message: str,
    tree: str,
) -> bool:
    """Require one canonical generation-11 reviewed-tree trailer."""

    if re.fullmatch(r"[0-9a-f]{40}", tree) is None:
        return False
    lines = message.splitlines()
    expected = f"{PHASE54_SLICE12_PRODUCT_REPAIR11_REVIEWED_TREE_TRAILER}: {tree}"
    trailer_key = PHASE54_SLICE12_PRODUCT_REPAIR11_REVIEWED_TREE_TRAILER.casefold()
    reviewed_tree_lines = tuple(
        line for line in lines if line.lstrip().casefold().startswith(trailer_key)
    )
    return (
        len(lines) >= 3
        and lines[0] == PHASE54_SLICE12_PRODUCT_REPAIR11_SUBJECT
        and lines[-2] == ""
        and lines[-1] == expected
        and reviewed_tree_lines == (expected,)
    )


def _phase54_slice12_product_repair12_message_matches_tree(
    message: str,
    tree: str,
) -> bool:
    """Require one canonical generation-12 reviewed-tree trailer."""

    if re.fullmatch(r"[0-9a-f]{40}", tree) is None:
        return False
    lines = message.splitlines()
    expected = f"{PHASE54_SLICE12_PRODUCT_REPAIR12_REVIEWED_TREE_TRAILER}: {tree}"
    trailer_key = PHASE54_SLICE12_PRODUCT_REPAIR12_REVIEWED_TREE_TRAILER.casefold()
    reviewed_tree_lines = tuple(
        line for line in lines if line.lstrip().casefold().startswith(trailer_key)
    )
    return (
        len(lines) >= 3
        and lines[0] == PHASE54_SLICE12_PRODUCT_REPAIR12_SUBJECT
        and lines[-2] == ""
        and lines[-1] == expected
        and reviewed_tree_lines == (expected,)
    )


def _phase54_slice12_product_repair13_message_matches_tree(
    message: str,
    tree: str,
) -> bool:
    """Require one canonical generation-13 reviewed-tree trailer."""

    if re.fullmatch(r"[0-9a-f]{40}", tree) is None:
        return False
    lines = message.splitlines()
    expected = f"{PHASE54_SLICE12_PRODUCT_REPAIR13_REVIEWED_TREE_TRAILER}: {tree}"
    trailer_key = PHASE54_SLICE12_PRODUCT_REPAIR13_REVIEWED_TREE_TRAILER.casefold()
    reviewed_tree_lines = tuple(
        line for line in lines if line.lstrip().casefold().startswith(trailer_key)
    )
    return (
        len(lines) >= 3
        and lines[0] == PHASE54_SLICE12_PRODUCT_REPAIR13_SUBJECT
        and lines[-2] == ""
        and lines[-1] == expected
        and reviewed_tree_lines == (expected,)
    )


def _phase54_slice12_product_repair14_message_matches_tree(
    message: str,
    tree: str,
) -> bool:
    """Require one canonical generation-14 reviewed-tree trailer."""

    if re.fullmatch(r"[0-9a-f]{40}", tree) is None:
        return False
    lines = message.splitlines()
    expected = f"{PHASE54_SLICE12_PRODUCT_REPAIR14_REVIEWED_TREE_TRAILER}: {tree}"
    trailer_key = PHASE54_SLICE12_PRODUCT_REPAIR14_REVIEWED_TREE_TRAILER.casefold()
    reviewed_tree_lines = tuple(
        line for line in lines if line.lstrip().casefold().startswith(trailer_key)
    )
    return (
        len(lines) >= 3
        and lines[0] == PHASE54_SLICE12_PRODUCT_REPAIR14_SUBJECT
        and lines[-2] == ""
        and lines[-1] == expected
        and reviewed_tree_lines == (expected,)
    )


def _phase54_slice12_mechanical_repair3_message_matches_tree(
    message: str,
    tree: str,
) -> bool:
    """Require one canonical mechanical-repair3 reviewed-tree trailer."""

    if re.fullmatch(r"[0-9a-f]{40}", tree) is None:
        return False
    lines = message.splitlines()
    expected = f"{PHASE54_SLICE12_MECHANICAL_REPAIR3_REVIEWED_TREE_TRAILER}: {tree}"
    trailer_key = PHASE54_SLICE12_MECHANICAL_REPAIR3_REVIEWED_TREE_TRAILER.casefold()
    reviewed_tree_lines = tuple(
        line for line in lines if line.lstrip().casefold().startswith(trailer_key)
    )
    return (
        len(lines) >= 3
        and lines[0] == PHASE54_SLICE12_MECHANICAL_REPAIR3_SUBJECT
        and lines[-2] == ""
        and lines[-1] == expected
        and reviewed_tree_lines == (expected,)
    )


def _read_phase54_gate2_repository_state() -> Phase54Gate2RepositoryState:
    status = _git_output(
        ["status", "--porcelain=v2", "--branch", "--untracked-files=all"]
    )
    branch_oid = ""
    branch_head = ""
    branch_upstream = ""
    ahead = -1
    behind = -1
    added_paths: set[str] = set()
    modified_paths: set[str] = set()
    deleted_paths: set[str] = set()
    staged_paths: set[str] = set()
    other_paths: set[str] = set()

    for line in status.splitlines():
        if line.startswith("# branch.oid "):
            branch_oid = line.removeprefix("# branch.oid ")
        elif line.startswith("# branch.head "):
            branch_head = line.removeprefix("# branch.head ")
        elif line.startswith("# branch.upstream "):
            branch_upstream = line.removeprefix("# branch.upstream ")
        elif line.startswith("# branch.ab "):
            ahead_text, behind_text = line.removeprefix("# branch.ab ").split()
            ahead = int(ahead_text.removeprefix("+"))
            behind = int(behind_text.removeprefix("-"))
        elif line.startswith("? "):
            added_paths.add(line.removeprefix("? "))
        elif line.startswith("1 "):
            parts = line.split(" ", 8)
            if len(parts) != 9:
                other_paths.add(line)
                continue
            index_status, worktree_status = parts[1]
            path = parts[8]
            if index_status != ".":
                staged_paths.add(path)
            if worktree_status == "M":
                modified_paths.add(path)
            elif worktree_status == "D":
                deleted_paths.add(path)
            elif worktree_status != ".":
                other_paths.add(path)
        elif not line.startswith("# "):
            other_paths.add(line)

    git_dir = Path(_git_output(["rev-parse", "--git-dir"]))
    if not git_dir.is_absolute():
        git_dir = REPO_ROOT / git_dir
    active_git_operation = any(
        (git_dir / name).exists()
        for name in (
            "MERGE_HEAD",
            "CHERRY_PICK_HEAD",
            "REVERT_HEAD",
            "REBASE_HEAD",
            "rebase-merge",
            "rebase-apply",
        )
    )
    worktree_count = _git_output(["worktree", "list", "--porcelain"]).count("worktree ")
    shallow = _git_output(["rev-parse", "--is-shallow-repository"]) == "true"
    return Phase54Gate2RepositoryState(
        marker=PHASE54_ACTIVE_GATE2_MARKER,
        branch_oid=branch_oid,
        branch_head=branch_head,
        branch_upstream=branch_upstream,
        ahead=ahead,
        behind=behind,
        added_paths=frozenset(added_paths),
        modified_paths=frozenset(modified_paths),
        deleted_paths=frozenset(deleted_paths),
        staged_paths=frozenset(staged_paths),
        other_paths=frozenset(other_paths),
        worktree_count=worktree_count,
        shallow=shallow,
        active_git_operation=active_git_operation,
    )


def _matches_phase54_active_gate2_manifest(
    state: Phase54Gate2RepositoryState,
) -> bool:
    """Return whether supplied facts are exactly the frozen active Gate 2."""

    if type(state) is not Phase54Gate2RepositoryState:
        return False
    common = (
        state.marker == PHASE54_ACTIVE_GATE2_MARKER
        and state.ahead == 0
        and state.behind == 0
        and state.staged_paths == frozenset()
        and state.other_paths == frozenset()
        and state.worktree_count == 1
        and not state.shallow
        and not state.active_git_operation
    )
    active_gate2 = (
        state.branch_oid == PHASE54_ACTIVE_GATE2_BASE
        and state.branch_head == "main"
        and state.branch_upstream == "origin/main"
        and state.added_paths == PHASE54_ACTIVE_GATE2_ADDED_PATHS
        and state.modified_paths == PHASE54_ACTIVE_GATE2_MODIFIED_PATHS
        and state.deleted_paths == PHASE54_ACTIVE_GATE2_DELETED_PATHS
    )
    slice10_original_gate2 = (
        state.branch_oid == PHASE54_ACTIVE_GATE2_BASE
        and state.branch_head == "main"
        and state.branch_upstream == "origin/main"
        and state.added_paths == PHASE54_SLICE10_ORIGINAL_ADDED_PATHS
        and state.modified_paths == PHASE54_SLICE10_ORIGINAL_MODIFIED_PATHS
        and state.deleted_paths == PHASE54_ACTIVE_GATE2_DELETED_PATHS
    )
    product_repair1 = (
        state.branch_oid == PHASE54_POST_REVIEW_PRODUCT_REPAIR1_BASE
        and state.branch_head == PHASE54_POST_REVIEW_PRODUCT_REPAIR1_BRANCH
        and state.branch_upstream
        == f"origin/{PHASE54_POST_REVIEW_PRODUCT_REPAIR1_BRANCH}"
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_POST_REVIEW_PRODUCT_REPAIR1_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
    product_repair2 = (
        state.branch_oid == PHASE54_POST_REVIEW_PRODUCT_REPAIR2_BASE
        and state.branch_head == PHASE54_POST_REVIEW_PRODUCT_REPAIR2_BRANCH
        and state.branch_upstream
        == f"origin/{PHASE54_POST_REVIEW_PRODUCT_REPAIR2_BRANCH}"
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_POST_REVIEW_PRODUCT_REPAIR2_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
    product_repair3 = (
        state.branch_oid == PHASE54_POST_REVIEW_PRODUCT_REPAIR3_BASE
        and state.branch_head == PHASE54_POST_REVIEW_PRODUCT_REPAIR3_BRANCH
        and state.branch_upstream
        == f"origin/{PHASE54_POST_REVIEW_PRODUCT_REPAIR3_BRANCH}"
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_POST_REVIEW_PRODUCT_REPAIR3_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
    product_repair4 = (
        state.branch_oid == PHASE54_POST_REVIEW_PRODUCT_REPAIR4_BASE
        and state.branch_head == PHASE54_POST_REVIEW_PRODUCT_REPAIR4_BRANCH
        and state.branch_upstream
        == f"origin/{PHASE54_POST_REVIEW_PRODUCT_REPAIR4_BRANCH}"
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_POST_REVIEW_PRODUCT_REPAIR4_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
    product_repair5 = (
        state.branch_oid == PHASE54_POST_REVIEW_PRODUCT_REPAIR5_BASE
        and state.branch_head == PHASE54_POST_REVIEW_PRODUCT_REPAIR5_BRANCH
        and state.branch_upstream
        == f"origin/{PHASE54_POST_REVIEW_PRODUCT_REPAIR5_BRANCH}"
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_POST_REVIEW_PRODUCT_REPAIR5_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
    product_repair6 = (
        state.branch_oid == PHASE54_POST_REVIEW_PRODUCT_REPAIR6_BASE
        and state.branch_head == PHASE54_POST_REVIEW_PRODUCT_REPAIR6_BRANCH
        and state.branch_upstream
        == f"origin/{PHASE54_POST_REVIEW_PRODUCT_REPAIR6_BRANCH}"
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_POST_REVIEW_PRODUCT_REPAIR6_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
    product_repair7 = (
        state.branch_oid == PHASE54_POST_REVIEW_PRODUCT_REPAIR7_BASE
        and state.branch_head == PHASE54_POST_REVIEW_PRODUCT_REPAIR7_BRANCH
        and state.branch_upstream
        == f"origin/{PHASE54_POST_REVIEW_PRODUCT_REPAIR7_BRANCH}"
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_POST_REVIEW_PRODUCT_REPAIR7_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
    product_repair8 = (
        state.branch_oid == PHASE54_POST_REVIEW_PRODUCT_REPAIR8_BASE
        and state.branch_head == PHASE54_POST_REVIEW_PRODUCT_REPAIR8_BRANCH
        and state.branch_upstream
        == f"origin/{PHASE54_POST_REVIEW_PRODUCT_REPAIR8_BRANCH}"
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_POST_REVIEW_PRODUCT_REPAIR8_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
    product_repair9 = (
        state.branch_oid == PHASE54_POST_REVIEW_PRODUCT_REPAIR9_BASE
        and state.branch_head == PHASE54_POST_REVIEW_PRODUCT_REPAIR9_BRANCH
        and state.branch_upstream
        == f"origin/{PHASE54_POST_REVIEW_PRODUCT_REPAIR9_BRANCH}"
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_POST_REVIEW_PRODUCT_REPAIR9_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
    slice11_pr_ci_repair = (
        state.branch_oid == PHASE54_SLICE11_PR_CI_REPAIR_BASE
        and state.branch_head == PHASE54_SLICE11_PR_CI_REPAIR_BRANCH
        and state.branch_upstream == f"origin/{PHASE54_SLICE11_PR_CI_REPAIR_BRANCH}"
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_SLICE11_PR_CI_REPAIR_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
    slice11_substantive_recovery = (
        state.branch_oid == PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_BASE
        and state.branch_head == PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_BRANCH
        and state.branch_upstream
        == f"origin/{PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_BRANCH}"
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
    slice11_python313_repair = (
        state.branch_oid == PHASE54_SLICE11_PYTHON313_REPAIR_BASE
        and state.branch_head == PHASE54_SLICE11_PYTHON313_REPAIR_BRANCH
        and state.branch_upstream == f"origin/{PHASE54_SLICE11_PYTHON313_REPAIR_BRANCH}"
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_SLICE11_PYTHON313_REPAIR_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
    slice12_pr_ci_repair = (
        state.branch_oid == PHASE54_SLICE12_PR_CI_REPAIR_BASE
        and state.branch_head == PHASE54_SLICE12_PR_CI_REPAIR_BRANCH
        and state.branch_upstream == f"origin/{PHASE54_SLICE12_PR_CI_REPAIR_BRANCH}"
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_SLICE12_PR_CI_REPAIR_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
    slice12_product_repair3 = (
        state.branch_oid == PHASE54_SLICE12_PRODUCT_REPAIR3_BASE
        and state.branch_head == PHASE54_SLICE12_PRODUCT_REPAIR3_BRANCH
        and state.branch_upstream == f"origin/{PHASE54_SLICE12_PRODUCT_REPAIR3_BRANCH}"
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_SLICE12_PRODUCT_REPAIR3_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
    slice12_product_repair10 = (
        state.branch_oid == PHASE54_SLICE12_PRODUCT_REPAIR10_BASE
        and state.branch_head == PHASE54_SLICE12_PRODUCT_REPAIR10_BRANCH
        and state.branch_upstream == f"origin/{PHASE54_SLICE12_PRODUCT_REPAIR10_BRANCH}"
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_SLICE12_PRODUCT_REPAIR10_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
    slice12_product_repair11 = (
        state.branch_oid == PHASE54_SLICE12_PRODUCT_REPAIR11_BASE
        and state.branch_head == PHASE54_SLICE12_PRODUCT_REPAIR11_BRANCH
        and state.branch_upstream == f"origin/{PHASE54_SLICE12_PRODUCT_REPAIR11_BRANCH}"
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_SLICE12_PRODUCT_REPAIR11_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
    slice12_product_repair12 = (
        state.branch_oid == PHASE54_SLICE12_PRODUCT_REPAIR12_BASE
        and state.branch_head == PHASE54_SLICE12_PRODUCT_REPAIR12_BRANCH
        and state.branch_upstream == f"origin/{PHASE54_SLICE12_PRODUCT_REPAIR12_BRANCH}"
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_SLICE12_PRODUCT_REPAIR12_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
    slice12_product_repair13 = (
        state.branch_oid == PHASE54_SLICE12_PRODUCT_REPAIR13_BASE
        and state.branch_head == PHASE54_SLICE12_PRODUCT_REPAIR13_BRANCH
        and state.branch_upstream == f"origin/{PHASE54_SLICE12_PRODUCT_REPAIR13_BRANCH}"
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_SLICE12_PRODUCT_REPAIR13_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
    slice12_product_repair14 = (
        state.branch_oid == PHASE54_SLICE12_PRODUCT_REPAIR14_BASE
        and state.branch_head == PHASE54_SLICE12_PRODUCT_REPAIR14_BRANCH
        and state.branch_upstream == f"origin/{PHASE54_SLICE12_PRODUCT_REPAIR14_BRANCH}"
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_SLICE12_PRODUCT_REPAIR14_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
    slice12_mechanical_repair3 = (
        state.branch_oid == PHASE54_SLICE12_MECHANICAL_REPAIR3_BASE
        and state.branch_head == PHASE54_SLICE12_MECHANICAL_REPAIR3_BRANCH
        and state.branch_upstream
        == f"origin/{PHASE54_SLICE12_MECHANICAL_REPAIR3_BRANCH}"
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_SLICE12_MECHANICAL_REPAIR3_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
    return common and (
        slice12_mechanical_repair3
        or active_gate2
        or slice10_original_gate2
        or product_repair1
        or product_repair2
        or product_repair3
        or product_repair4
        or product_repair5
        or product_repair6
        or product_repair7
        or product_repair8
        or product_repair9
        or slice11_pr_ci_repair
        or slice11_substantive_recovery
        or slice11_python313_repair
        or slice12_pr_ci_repair
        or slice12_product_repair3
        or slice12_product_repair10
        or slice12_product_repair11
        or slice12_product_repair12
        or slice12_product_repair13
        or slice12_product_repair14
    )


def _matches_phase54_slice12_product_repair3_clean_topic(
    state: Phase54Gate2RepositoryState,
) -> bool:
    """Recognize only the future clean non-amend generation-3 topic child."""

    if type(state) is not Phase54Gate2RepositoryState:
        return False
    clean_topic = (
        state.marker == PHASE54_ACTIVE_GATE2_MARKER
        and state.branch_head == PHASE54_SLICE12_PRODUCT_REPAIR3_BRANCH
        and state.branch_upstream == f"origin/{PHASE54_SLICE12_PRODUCT_REPAIR3_BRANCH}"
        and state.ahead == 0
        and state.behind == 0
        and state.added_paths == frozenset()
        and state.modified_paths == frozenset()
        and state.deleted_paths == frozenset()
        and state.staged_paths == frozenset()
        and state.other_paths == frozenset()
        and state.worktree_count == 1
        and not state.shallow
        and not state.active_git_operation
    )
    if not clean_topic:
        return False
    try:
        parents = tuple(
            _git_output(["rev-list", "--parents", "-n", "1", "HEAD"]).split()[1:]
        )
        subject = _git_output(["show", "-s", "--format=%s", "HEAD"])
        main = _git_output(["rev-parse", "--verify", "refs/heads/main"])
        origin_main = _git_output(["rev-parse", "--verify", "refs/remotes/origin/main"])
    except subprocess.SubprocessError:
        return False
    return (
        parents == (PHASE54_SLICE12_PRODUCT_REPAIR3_BASE,)
        and subject == PHASE54_SLICE12_PRODUCT_REPAIR3_SUBJECT
        and main == origin_main == PHASE54_ACTIVE_GATE2_BASE
    )


def _matches_phase54_slice12_product_repair10_clean_topic(
    state: Phase54Gate2RepositoryState,
) -> bool:
    """Recognize a clean generation-10 child carrying an exact tree claim."""

    if type(state) is not Phase54Gate2RepositoryState:
        return False
    clean_topic = (
        state.marker == PHASE54_ACTIVE_GATE2_MARKER
        and state.branch_head == PHASE54_SLICE12_PRODUCT_REPAIR10_BRANCH
        and state.branch_upstream == f"origin/{PHASE54_SLICE12_PRODUCT_REPAIR10_BRANCH}"
        and state.ahead == 0
        and state.behind == 0
        and state.added_paths == frozenset()
        and state.modified_paths == frozenset()
        and state.deleted_paths == frozenset()
        and state.staged_paths == frozenset()
        and state.other_paths == frozenset()
        and state.worktree_count == 1
        and not state.shallow
        and not state.active_git_operation
    )
    if not clean_topic:
        return False
    try:
        head_before = _git_output(["rev-parse", "--verify", "HEAD^{commit}"])
        revision = tuple(
            _git_output(["rev-list", "--parents", "-n", "1", head_before]).split()
        )
        subject = _git_output(["show", "-s", "--format=%s", head_before])
        tree = _git_output(["show", "-s", "--format=%T", head_before])
        message = _git_commit_message(head_before)
        main_before = _git_output(["rev-parse", "--verify", "refs/heads/main"])
        origin_main_before = _git_output(
            ["rev-parse", "--verify", "refs/remotes/origin/main"]
        )
        state_after = _read_phase54_gate2_repository_state()
        head_after = _git_output(["rev-parse", "--verify", "HEAD^{commit}"])
        main_after = _git_output(["rev-parse", "--verify", "refs/heads/main"])
        origin_main_after = _git_output(
            ["rev-parse", "--verify", "refs/remotes/origin/main"]
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return (
        state.branch_oid == head_before == head_after
        and state_after == state
        and state_after.branch_oid == head_after
        and revision == (head_before, PHASE54_SLICE12_PRODUCT_REPAIR10_BASE)
        and subject == PHASE54_SLICE12_PRODUCT_REPAIR10_SUBJECT
        # Create-once Gate 2 evidence separately authorizes this exact tree claim.
        and _phase54_slice12_product_repair10_message_matches_tree(message, tree)
        and main_before
        == origin_main_before
        == main_after
        == origin_main_after
        == PHASE54_ACTIVE_GATE2_BASE
    )


def _matches_phase54_slice12_product_repair11_clean_topic(
    state: Phase54Gate2RepositoryState,
) -> bool:
    """Recognize a clean generation-11 child carrying an exact tree claim."""

    if type(state) is not Phase54Gate2RepositoryState:
        return False
    clean_topic = (
        state.marker == PHASE54_ACTIVE_GATE2_MARKER
        and state.branch_head == PHASE54_SLICE12_PRODUCT_REPAIR11_BRANCH
        and state.branch_upstream == f"origin/{PHASE54_SLICE12_PRODUCT_REPAIR11_BRANCH}"
        and state.ahead == 0
        and state.behind == 0
        and state.added_paths == frozenset()
        and state.modified_paths == frozenset()
        and state.deleted_paths == frozenset()
        and state.staged_paths == frozenset()
        and state.other_paths == frozenset()
        and state.worktree_count == 1
        and not state.shallow
        and not state.active_git_operation
    )
    if not clean_topic:
        return False
    try:
        head_before = _git_output(["rev-parse", "--verify", "HEAD^{commit}"])
        revision = tuple(
            _git_output(["rev-list", "--parents", "-n", "1", head_before]).split()
        )
        subject = _git_output(["show", "-s", "--format=%s", head_before])
        tree = _git_output(["show", "-s", "--format=%T", head_before])
        message = _git_commit_message(head_before)
        main_before = _git_output(["rev-parse", "--verify", "refs/heads/main"])
        origin_main_before = _git_output(
            ["rev-parse", "--verify", "refs/remotes/origin/main"]
        )
        state_after = _read_phase54_gate2_repository_state()
        head_after = _git_output(["rev-parse", "--verify", "HEAD^{commit}"])
        main_after = _git_output(["rev-parse", "--verify", "refs/heads/main"])
        origin_main_after = _git_output(
            ["rev-parse", "--verify", "refs/remotes/origin/main"]
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return (
        state.branch_oid == head_before == head_after
        and state_after == state
        and state_after.branch_oid == head_after
        and revision == (head_before, PHASE54_SLICE12_PRODUCT_REPAIR11_BASE)
        and subject == PHASE54_SLICE12_PRODUCT_REPAIR11_SUBJECT
        # Create-once Gate 2 evidence separately authorizes this exact tree claim.
        and _phase54_slice12_product_repair11_message_matches_tree(message, tree)
        and main_before
        == origin_main_before
        == main_after
        == origin_main_after
        == PHASE54_ACTIVE_GATE2_BASE
    )


def _matches_phase54_slice12_product_repair12_clean_topic(
    state: Phase54Gate2RepositoryState,
) -> bool:
    """Recognize a clean generation-12 child carrying an exact tree claim."""

    if type(state) is not Phase54Gate2RepositoryState:
        return False
    clean_topic = (
        state.marker == PHASE54_ACTIVE_GATE2_MARKER
        and state.branch_head == PHASE54_SLICE12_PRODUCT_REPAIR12_BRANCH
        and state.branch_upstream == f"origin/{PHASE54_SLICE12_PRODUCT_REPAIR12_BRANCH}"
        and state.ahead == 0
        and state.behind == 0
        and state.added_paths == frozenset()
        and state.modified_paths == frozenset()
        and state.deleted_paths == frozenset()
        and state.staged_paths == frozenset()
        and state.other_paths == frozenset()
        and state.worktree_count == 1
        and not state.shallow
        and not state.active_git_operation
    )
    if not clean_topic:
        return False
    try:
        head_before = _git_output(["rev-parse", "--verify", "HEAD^{commit}"])
        revision = tuple(
            _git_output(["rev-list", "--parents", "-n", "1", head_before]).split()
        )
        subject = _git_output(["show", "-s", "--format=%s", head_before])
        tree = _git_output(["show", "-s", "--format=%T", head_before])
        message = _git_commit_message(head_before)
        main_before = _git_output(["rev-parse", "--verify", "refs/heads/main"])
        origin_main_before = _git_output(
            ["rev-parse", "--verify", "refs/remotes/origin/main"]
        )
        state_after = _read_phase54_gate2_repository_state()
        head_after = _git_output(["rev-parse", "--verify", "HEAD^{commit}"])
        main_after = _git_output(["rev-parse", "--verify", "refs/heads/main"])
        origin_main_after = _git_output(
            ["rev-parse", "--verify", "refs/remotes/origin/main"]
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return (
        state.branch_oid == head_before == head_after
        and state_after == state
        and state_after.branch_oid == head_after
        and revision == (head_before, PHASE54_SLICE12_PRODUCT_REPAIR12_BASE)
        and subject == PHASE54_SLICE12_PRODUCT_REPAIR12_SUBJECT
        # Create-once Gate 2 evidence separately authorizes this exact tree claim.
        and _phase54_slice12_product_repair12_message_matches_tree(message, tree)
        and main_before
        == origin_main_before
        == main_after
        == origin_main_after
        == PHASE54_ACTIVE_GATE2_BASE
    )


def _matches_phase54_slice12_product_repair13_clean_topic(
    state: Phase54Gate2RepositoryState,
) -> bool:
    """Recognize a clean generation-13 child carrying an exact tree claim."""

    if type(state) is not Phase54Gate2RepositoryState:
        return False
    clean_topic = (
        state.marker == PHASE54_ACTIVE_GATE2_MARKER
        and state.branch_head == PHASE54_SLICE12_PRODUCT_REPAIR13_BRANCH
        and state.branch_upstream == f"origin/{PHASE54_SLICE12_PRODUCT_REPAIR13_BRANCH}"
        and state.ahead == 0
        and state.behind == 0
        and state.added_paths == frozenset()
        and state.modified_paths == frozenset()
        and state.deleted_paths == frozenset()
        and state.staged_paths == frozenset()
        and state.other_paths == frozenset()
        and state.worktree_count == 1
        and not state.shallow
        and not state.active_git_operation
    )
    if not clean_topic:
        return False
    try:
        head_before = _git_output(["rev-parse", "--verify", "HEAD^{commit}"])
        revision = tuple(
            _git_output(["rev-list", "--parents", "-n", "1", head_before]).split()
        )
        subject = _git_output(["show", "-s", "--format=%s", head_before])
        tree = _git_output(["show", "-s", "--format=%T", head_before])
        message = _git_commit_message(head_before)
        main_before = _git_output(["rev-parse", "--verify", "refs/heads/main"])
        origin_main_before = _git_output(
            ["rev-parse", "--verify", "refs/remotes/origin/main"]
        )
        state_after = _read_phase54_gate2_repository_state()
        head_after = _git_output(["rev-parse", "--verify", "HEAD^{commit}"])
        main_after = _git_output(["rev-parse", "--verify", "refs/heads/main"])
        origin_main_after = _git_output(
            ["rev-parse", "--verify", "refs/remotes/origin/main"]
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return (
        state.branch_oid == head_before == head_after
        and state_after == state
        and state_after.branch_oid == head_after
        and revision == (head_before, PHASE54_SLICE12_PRODUCT_REPAIR13_BASE)
        and subject == PHASE54_SLICE12_PRODUCT_REPAIR13_SUBJECT
        # Create-once Gate 2 evidence separately authorizes this exact tree claim.
        and _phase54_slice12_product_repair13_message_matches_tree(message, tree)
        and main_before
        == origin_main_before
        == main_after
        == origin_main_after
        == PHASE54_ACTIVE_GATE2_BASE
    )


def _matches_phase54_slice12_product_repair14_clean_topic(
    state: Phase54Gate2RepositoryState,
) -> bool:
    """Recognize a clean generation-14 child carrying an exact tree claim."""

    if type(state) is not Phase54Gate2RepositoryState:
        return False
    clean_topic = (
        state.marker == PHASE54_ACTIVE_GATE2_MARKER
        and state.branch_head == PHASE54_SLICE12_PRODUCT_REPAIR14_BRANCH
        and state.branch_upstream == f"origin/{PHASE54_SLICE12_PRODUCT_REPAIR14_BRANCH}"
        and state.ahead == 0
        and state.behind == 0
        and state.added_paths == frozenset()
        and state.modified_paths == frozenset()
        and state.deleted_paths == frozenset()
        and state.staged_paths == frozenset()
        and state.other_paths == frozenset()
        and state.worktree_count == 1
        and not state.shallow
        and not state.active_git_operation
    )
    if not clean_topic:
        return False
    try:
        head_before = _git_output(["rev-parse", "--verify", "HEAD^{commit}"])
        revision = tuple(
            _git_output(["rev-list", "--parents", "-n", "1", head_before]).split()
        )
        subject = _git_output(["show", "-s", "--format=%s", head_before])
        tree = _git_output(["show", "-s", "--format=%T", head_before])
        message = _git_commit_message(head_before)
        main_before = _git_output(["rev-parse", "--verify", "refs/heads/main"])
        origin_main_before = _git_output(
            ["rev-parse", "--verify", "refs/remotes/origin/main"]
        )
        state_after = _read_phase54_gate2_repository_state()
        head_after = _git_output(["rev-parse", "--verify", "HEAD^{commit}"])
        main_after = _git_output(["rev-parse", "--verify", "refs/heads/main"])
        origin_main_after = _git_output(
            ["rev-parse", "--verify", "refs/remotes/origin/main"]
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return (
        state.branch_oid == head_before == head_after
        and state_after == state
        and state_after.branch_oid == head_after
        and revision == (head_before, PHASE54_SLICE12_PRODUCT_REPAIR14_BASE)
        and subject == PHASE54_SLICE12_PRODUCT_REPAIR14_SUBJECT
        # Create-once Gate 2 evidence separately authorizes this exact tree claim.
        and _phase54_slice12_product_repair14_message_matches_tree(message, tree)
        and main_before
        == origin_main_before
        == main_after
        == origin_main_after
        == PHASE54_ACTIVE_GATE2_BASE
    )


def _matches_phase54_slice12_mechanical_repair3_clean_topic(
    state: Phase54Gate2RepositoryState,
) -> bool:
    """Recognize the clean non-amend mechanical-repair3 child."""

    if type(state) is not Phase54Gate2RepositoryState:
        return False
    clean_topic = (
        state.marker == PHASE54_ACTIVE_GATE2_MARKER
        and state.branch_head == PHASE54_SLICE12_MECHANICAL_REPAIR3_BRANCH
        and state.branch_upstream
        == f"origin/{PHASE54_SLICE12_MECHANICAL_REPAIR3_BRANCH}"
        and state.ahead == 0
        and state.behind == 0
        and state.added_paths == frozenset()
        and state.modified_paths == frozenset()
        and state.deleted_paths == frozenset()
        and state.staged_paths == frozenset()
        and state.other_paths == frozenset()
        and state.worktree_count == 1
        and not state.shallow
        and not state.active_git_operation
    )
    if not clean_topic:
        return False
    try:
        head_before = _git_output(["rev-parse", "--verify", "HEAD^{commit}"])
        revision = tuple(
            _git_output(["rev-list", "--parents", "-n", "1", head_before]).split()
        )
        subject = _git_output(["show", "-s", "--format=%s", head_before])
        tree = _git_output(["show", "-s", "--format=%T", head_before])
        message = _git_commit_message(head_before)
        main_before = _git_output(["rev-parse", "--verify", "refs/heads/main"])
        origin_main_before = _git_output(
            ["rev-parse", "--verify", "refs/remotes/origin/main"]
        )
        state_after = _read_phase54_gate2_repository_state()
        head_after = _git_output(["rev-parse", "--verify", "HEAD^{commit}"])
        main_after = _git_output(["rev-parse", "--verify", "refs/heads/main"])
        origin_main_after = _git_output(
            ["rev-parse", "--verify", "refs/remotes/origin/main"]
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return (
        state.branch_oid == head_before == head_after
        and state_after == state
        and state_after.branch_oid == head_after
        and revision == (head_before, PHASE54_SLICE12_MECHANICAL_REPAIR3_BASE)
        and subject == PHASE54_SLICE12_MECHANICAL_REPAIR3_SUBJECT
        # Create-once mechanical Gate 2 evidence authorizes this tree claim.
        and _phase54_slice12_mechanical_repair3_message_matches_tree(message, tree)
        and main_before
        == origin_main_before
        == main_after
        == origin_main_after
        == PHASE54_ACTIVE_GATE2_BASE
    )


def phase54_active_gate2_manifest_is_active() -> bool:
    """Read exact local Git facts and recognize only the active Gate 2 state."""

    try:
        state = _read_phase54_gate2_repository_state()
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return (
        _matches_phase54_active_gate2_manifest(state)
        or _matches_phase54_slice12_mechanical_repair3_clean_topic(state)
        or _matches_phase54_slice12_product_repair14_clean_topic(state)
        or _matches_phase54_slice12_product_repair13_clean_topic(state)
        or _matches_phase54_slice12_product_repair12_clean_topic(state)
        or _matches_phase54_slice12_product_repair11_clean_topic(state)
        or _matches_phase54_slice12_product_repair10_clean_topic(state)
        or _matches_phase54_slice12_product_repair3_clean_topic(state)
    )


def phase54_slice12_product_repair3_clean_topic_is_active() -> bool:
    """Recognize only the clean non-amend generation-3 topic child."""

    try:
        state = _read_phase54_gate2_repository_state()
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return _matches_phase54_slice12_product_repair3_clean_topic(state)


def phase54_slice12_product_repair10_clean_topic_is_active() -> bool:
    """Recognize only the clean non-amend generation-10 topic child."""

    try:
        state = _read_phase54_gate2_repository_state()
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return _matches_phase54_slice12_product_repair10_clean_topic(state)


def phase54_slice12_product_repair11_clean_topic_is_active() -> bool:
    """Recognize only the clean non-amend generation-11 topic child."""

    try:
        state = _read_phase54_gate2_repository_state()
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return _matches_phase54_slice12_product_repair11_clean_topic(state)


def phase54_slice12_product_repair12_clean_topic_is_active() -> bool:
    """Recognize only the clean non-amend generation-12 topic child."""

    try:
        state = _read_phase54_gate2_repository_state()
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return _matches_phase54_slice12_product_repair12_clean_topic(state)


def phase54_slice12_product_repair13_clean_topic_is_active() -> bool:
    """Recognize only the clean non-amend generation-13 topic child."""

    try:
        state = _read_phase54_gate2_repository_state()
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return _matches_phase54_slice12_product_repair13_clean_topic(state)


def phase54_slice12_product_repair14_clean_topic_is_active() -> bool:
    """Recognize only the clean non-amend generation-14 topic child."""

    try:
        state = _read_phase54_gate2_repository_state()
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return _matches_phase54_slice12_product_repair14_clean_topic(state)


def phase54_slice12_mechanical_repair3_clean_topic_is_active() -> bool:
    """Recognize only the clean non-amend mechanical-repair3 topic child."""

    try:
        state = _read_phase54_gate2_repository_state()
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return _matches_phase54_slice12_mechanical_repair3_clean_topic(state)


def phase54_slice11_pr_ci_repair_is_active() -> bool:
    """Recognize only the exact Slice 11 natural-PR-CI mechanical repair."""

    try:
        state = _read_phase54_gate2_repository_state()
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return (
        _matches_phase54_active_gate2_manifest(state)
        and state.branch_oid == PHASE54_SLICE11_PR_CI_REPAIR_BASE
        and state.branch_head == PHASE54_SLICE11_PR_CI_REPAIR_BRANCH
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_SLICE11_PR_CI_REPAIR_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )


def phase54_slice11_substantive_recovery_is_active() -> bool:
    """Recognize only the exact Slice 11 substantive-recovery Gate 2."""

    try:
        state = _read_phase54_gate2_repository_state()
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return (
        _matches_phase54_active_gate2_manifest(state)
        and state.branch_oid == PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_BASE
        and state.branch_head == PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_BRANCH
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )


def phase54_slice11_python313_repair_is_active() -> bool:
    """Recognize only the exact Slice 11 Python 3.13 CI compatibility repair."""

    try:
        state = _read_phase54_gate2_repository_state()
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return (
        _matches_phase54_active_gate2_manifest(state)
        and state.branch_oid == PHASE54_SLICE11_PYTHON313_REPAIR_BASE
        and state.branch_head == PHASE54_SLICE11_PYTHON313_REPAIR_BRANCH
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_SLICE11_PYTHON313_REPAIR_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )


def phase54_slice12_pr_ci_repair_is_active() -> bool:
    """Recognize only the exact Slice 12 natural-PR-CI mechanical repair."""

    try:
        state = _read_phase54_gate2_repository_state()
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return (
        _matches_phase54_active_gate2_manifest(state)
        and state.branch_oid == PHASE54_SLICE12_PR_CI_REPAIR_BASE
        and state.branch_head == PHASE54_SLICE12_PR_CI_REPAIR_BRANCH
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_SLICE12_PR_CI_REPAIR_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )


def phase54_slice12_product_repair3_is_active() -> bool:
    """Recognize only the exact Slice 12 generation-3 product repair."""

    try:
        state = _read_phase54_gate2_repository_state()
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return (
        _matches_phase54_active_gate2_manifest(state)
        and state.branch_oid == PHASE54_SLICE12_PRODUCT_REPAIR3_BASE
        and state.branch_head == PHASE54_SLICE12_PRODUCT_REPAIR3_BRANCH
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_SLICE12_PRODUCT_REPAIR3_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )


def phase54_slice12_product_repair10_is_active() -> bool:
    """Recognize only the exact Slice 12 generation-10 product repair."""

    try:
        state = _read_phase54_gate2_repository_state()
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return (
        _matches_phase54_active_gate2_manifest(state)
        and state.branch_oid == PHASE54_SLICE12_PRODUCT_REPAIR10_BASE
        and state.branch_head == PHASE54_SLICE12_PRODUCT_REPAIR10_BRANCH
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_SLICE12_PRODUCT_REPAIR10_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )


def phase54_slice12_product_repair11_is_active() -> bool:
    """Recognize only the exact Slice 12 generation-11 product repair."""

    try:
        state = _read_phase54_gate2_repository_state()
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return (
        _matches_phase54_active_gate2_manifest(state)
        and state.branch_oid == PHASE54_SLICE12_PRODUCT_REPAIR11_BASE
        and state.branch_head == PHASE54_SLICE12_PRODUCT_REPAIR11_BRANCH
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_SLICE12_PRODUCT_REPAIR11_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )


def phase54_slice12_product_repair12_is_active() -> bool:
    """Recognize only the exact Slice 12 generation-12 product repair."""

    try:
        state = _read_phase54_gate2_repository_state()
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return (
        _matches_phase54_active_gate2_manifest(state)
        and state.branch_oid == PHASE54_SLICE12_PRODUCT_REPAIR12_BASE
        and state.branch_head == PHASE54_SLICE12_PRODUCT_REPAIR12_BRANCH
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_SLICE12_PRODUCT_REPAIR12_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )


def phase54_slice12_product_repair13_is_active() -> bool:
    """Recognize only the exact Slice 12 generation-13 product repair."""

    try:
        state = _read_phase54_gate2_repository_state()
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return (
        _matches_phase54_active_gate2_manifest(state)
        and state.branch_oid == PHASE54_SLICE12_PRODUCT_REPAIR13_BASE
        and state.branch_head == PHASE54_SLICE12_PRODUCT_REPAIR13_BRANCH
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_SLICE12_PRODUCT_REPAIR13_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )


def phase54_slice12_product_repair14_is_active() -> bool:
    """Recognize only the exact Slice 12 generation-14 product repair."""

    try:
        state = _read_phase54_gate2_repository_state()
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return (
        _matches_phase54_active_gate2_manifest(state)
        and state.branch_oid == PHASE54_SLICE12_PRODUCT_REPAIR14_BASE
        and state.branch_head == PHASE54_SLICE12_PRODUCT_REPAIR14_BRANCH
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_SLICE12_PRODUCT_REPAIR14_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )


def phase54_slice12_mechanical_repair3_is_active() -> bool:
    """Recognize only the exact Slice 12 mechanical-repair3 dirty overlay."""

    try:
        state = _read_phase54_gate2_repository_state()
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return (
        _matches_phase54_active_gate2_manifest(state)
        and state.branch_oid == PHASE54_SLICE12_MECHANICAL_REPAIR3_BASE
        and state.branch_head == PHASE54_SLICE12_MECHANICAL_REPAIR3_BRANCH
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_SLICE12_MECHANICAL_REPAIR3_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
