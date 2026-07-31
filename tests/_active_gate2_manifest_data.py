"""Exact per-Goal data for Pietto's active Gate 2 manifest."""

from __future__ import annotations


ACTIVE_GATE2_SCHEMA = "pietto.active-gate2-manifest.v1"
ACTIVE_GATE2_GOAL = "PHASE54_POST_SLICE6_WORKFLOW_EFFICIENCY"
ACTIVE_GATE2_MARKER = "PHASE54_POST_SLICE6_WORKFLOW_EFFICIENCY_GATE2"
ACTIVE_GATE2_BASE = "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16"
ACTIVE_GATE2_BRANCH = "main"
ACTIVE_GATE2_UPSTREAM = "origin/main"
ACTIVE_GATE2_CANDIDATE_BRANCH = "phase54/post-slice6-workflow-efficiency"
ACTIVE_GATE2_CANDIDATE_SUBJECT = "Add Pietto lean end-to-end workflow infrastructure"

ADDED_PATHS = {
    "docs/spec/phase54-post-slice6-workflow-efficiency-interlude-v1.md",
    "docs/spec/pietto-end-to-end-resilience-and-recovery-standard-v1.md",
    "docs/spec/pietto-lean-validation-and-evidence-standard-v1.md",
    "scripts/audit_gate2_readers.py",
    "scripts/build_evidence_bundle.py",
    "scripts/run_gate2_topology_checks.py",
    "scripts/run_lean_gate2.py",
    "scripts/verify_evidence_bundle.py",
    "tests/_active_gate2_manifest.py",
    "tests/_active_gate2_manifest_data.py",
    "tests/_topology_sensitive_registry.py",
    "tests/test_phase54_post_slice6_workflow_efficiency_interlude.py",
}
NON_READER_MODIFIED_PATHS = {
    "AGENTS.md",
}
MECHANICAL_READER_PATHS = {
    "tests/_phase54_active_gate2_manifest.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_planning_audit.py",
    "tests/test_phase11_validation_entrypoint.py",
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
    "tests/test_phase54_import_export_contextual_grammar_ast.py",
    "tests/test_phase54_local_export_visibility_module_facades.py",
    "tests/test_phase54_local_import_module_export_foundation_scope_lock.py",
}
REOPEN1_HASH_LOCK_READER_PATHS = {
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
}
ACTIVE_GATE2_DIRECT_READER_PATHS = {
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_packaging_smoke.py",
    "tests/test_phase11_validation_entrypoint.py",
    "tests/test_phase12_completion_audit.py",
    "tests/test_phase12_composition_cli_json_goldens.py",
    "tests/test_phase21_completion_audit.py",
    "tests/test_phase21_group_by_hardening_audit.py",
    "tests/test_phase24_aggregate_expression_arguments_readiness.py",
    "tests/test_phase24_cli_json_output_hardening.py",
    "tests/test_phase24_completion_audit.py",
    "tests/test_phase26_aggregate_expression_arguments_candidate_decision.py",
    "tests/test_phase26_completion_audit.py",
    "tests/test_phase27_completion_audit.py",
    "tests/test_phase28_completion_audit.py",
    "tests/test_phase29_completion_audit.py",
    "tests/test_phase30_candidate_decision.py",
    "tests/test_phase30_completion_audit.py",
    "tests/test_phase30_decimal_precision_scale_contract.py",
    "tests/test_phase33_completion_audit.py",
    "tests/test_phase44_project_source_selection_scope_lock.py",
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
    "tests/test_phase54_import_export_contextual_grammar_ast.py",
    "tests/test_phase54_local_export_visibility_module_facades.py",
    "tests/test_phase54_local_import_module_export_foundation_scope_lock.py",
    "tests/test_phase54_module_identity_selected_input_index_trusted_local_loader.py",
    "tests/test_phase54_schema_v2_explicit_module_carrier.py",
}
ACTIVE_GATE2_DIRECT_READER_SHA256 = (
    "649415db62667eff8e5dbfa47fb83ae30b05c0cac58fd01da87cd55df58672cd"
)
ACTIVE_GATE2_TRANSITIVE_READER_SHA256 = (
    "44cbf17112a093bd97ee3c2d88e37f290551222f4a636faf063d7200f1875fb3"
)
ACTIVE_GATE2_READER_CLOSURE_SHA256 = (
    "760af336b0b47c9443a6dfbe99c477bc67ead160e5e0401a9d53c2cfecbb2b54"
)
ACTIVE_GATE2_READER_ITEMS = 6786
MODIFIED_PATHS = NON_READER_MODIFIED_PATHS | MECHANICAL_READER_PATHS
DELETED_PATHS: set[str] = set()
ALLOWLIST_PATHS = ADDED_PATHS | MODIFIED_PATHS

ACTIVE_GATE2_ADDED_PATHS = frozenset(ADDED_PATHS)
ACTIVE_GATE2_MODIFIED_PATHS = frozenset(MODIFIED_PATHS)
ACTIVE_GATE2_DELETED_PATHS = frozenset(DELETED_PATHS)
ACTIVE_GATE2_ALLOWLIST_PATHS = frozenset(ALLOWLIST_PATHS)
ACTIVE_GATE2_COUNTS = (12, 51, 0)


assert (len(ADDED_PATHS), len(MODIFIED_PATHS), len(DELETED_PATHS)) == (
    ACTIVE_GATE2_COUNTS
)
assert len(ALLOWLIST_PATHS) == 63
assert len(REOPEN1_HASH_LOCK_READER_PATHS) == 10
assert REOPEN1_HASH_LOCK_READER_PATHS <= MECHANICAL_READER_PATHS
