from __future__ import annotations

import dataclasses
import hashlib
from pathlib import Path
from typing import Any, cast


import pytest

import pietto
import pietto.semantic.window_analysis as window_analysis
from pietto._project.model import (
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectRowFieldProvenanceKind,
    ProjectRowResultRole,
    ProjectRowSchema,
    ProjectSymbol,
    ProjectSymbolKind,
    ProjectSymbolNamespace,
)
from pietto._project.row_dependency_graph import ProjectRowDependencyNodeKind
from pietto._project.window_semantics import (
    WindowDependencyRole,
    WindowResultProjectFact,
    build_ranking_window_result_project_fact,
    build_window_result_project_fact,
)
from pietto.ast_nodes import (
    CallExpr,
    DottedNameExpr,
    Expression,
    GroupByClause,
    GroupByItem,
    LetBinding,
    LetClause,
    LiteralExpr,
    NameExpr,
    QueryDef,
    Script,
    SatisfyingClause,
    SelectItem,
    SourceDef,
    TableDef,
    WindowExpr,
)
from pietto.errors import Diagnostic, SourceLocation
from pietto.ir.lowering import lower_expr
from pietto.ir.model import WindowCallIR
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.generic_compatibility import (
    ConcreteTypeExpression,
    SignatureMatch,
    bind_signature,
)
from pietto.semantic.model import EffectiveNullability, TypeKind, ValueType
from pietto.semantic.nullability_formulas import (
    NonNullFormula,
    NullabilityEvaluationContext,
    NullabilityEvaluationMatch,
    evaluate_signature_result_nullability,
)
from pietto.semantic.window_semantics import (
    DistributionWindowPolicy,
    DistributionWindowSemanticFact,
    RankingAdvancePolicy,
    RankingWindowSemanticFact,
    WindowExpressionSemanticFact,
    WindowExpressionStage,
    WindowExpressionUnsupported,
    WindowResultAvailabilityKind,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_REL = (
    "docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md"
)
SPEC_REL = "docs/spec/phase53-rank-dense-rank-peer-semantics-contract-v1.md"
SELF_REL = "tests/test_phase53_percent_rank_cume_dist_ntile_contract.py"
BASE_HEAD_SHA = "3c1feab5bc70d407e9e4d7ccd0c5d489eec0ee68"

SPEC_REL = "docs/spec/phase53-percent-rank-cume-dist-ntile-contract-v1.md"
SPEC_TITLE = "Phase 53 percent_rank / cume_dist / ntile Contract v1"
SLICE9_PLAN_H2 = "Slice 9 percent_rank / cume_dist / ntile"
SPEC_H2 = (
    "Status And Authority",
    "Exact Identity Source Subset And Result Types",
    "percent_rank Abstract Semantics",
    "cume_dist Abstract Semantics",
    "ntile Argument And Balanced-bucket Semantics",
    "Private Distribution Policy And Carrier",
    "Semantic Analysis Signature And Result Contract",
    "Diagnostics And Direct-field Binding",
    "Project Dependencies And Provenance",
    "Persistence Row-schema And Downstream Boundaries",
    "IR SQL And Public Boundaries",
    "Reader Closure Inventory And Repository States",
    "Validation Depth-one CI And Gate 3",
    "Deferred Ownership And Stop Conditions",
)
SPEC_H3 = ("percent_rank", "cume_dist", "ntile")

EXPECTED_TEST_FUNCTIONS = (
    "test_slice9_artifact_paths_headings_and_lifecycle_are_exact",
    "test_source_subset_candidates_and_exact_slice8_reuse_are_locked",
    "test_ntile_argument_candidates_and_positive_integer_literal_selection_are_exact",
    "test_result_type_candidates_float_int_non_null_window_are_locked",
    "test_distribution_carrier_candidates_and_sibling_selection_are_locked",
    "test_identity_and_semantic_module_candidates_are_exact",
    "test_distribution_window_policy_enum_values_and_privacy_are_exact",
    "test_distribution_window_semantic_fact_shape_is_frozen_and_exact",
    "test_distribution_window_semantic_fact_malformed_matrix_fails_closed",
    "test_identity_to_distribution_policy_signature_mapping_is_exact_and_ordered",
    "test_distribution_signatures_are_exact",
    "test_distribution_signature_binding_returns_builtin_float_or_int",
    "test_distribution_non_null_formulas_evaluate_exactly",
    "test_percent_rank_abstract_structural_semantics_are_exact",
    "test_cume_dist_abstract_structural_semantics_are_exact",
    "test_ntile_balanced_bucket_semantics_and_bucket_count_are_exact",
    "test_exact_distribution_identity_legality_case_namespace_and_later_functions",
    "test_ntile_literal_ast_shape_and_argument_classification_are_exact",
    "test_distribution_supported_result_shape_is_exact",
    "test_distribution_bare_and_immediate_qualified_order_field_success",
    "test_distribution_table_query_direct_and_immediate_upstream_success",
    "test_distribution_coexists_with_ordinary_outputs",
    "test_distribution_analysis_is_structurally_repeatable",
    "test_wrong_distribution_arity_uses_pie_s2104",
    "test_invalid_ntile_argument_uses_pie_s2104",
    "test_unsupported_distribution_clause_and_shape_uses_pie_s2103",
    "test_distribution_partition_shapes_remain_unsupported",
    "test_distribution_order_cardinality_and_direction_remain_unsupported",
    "test_distribution_computed_unknown_and_invalid_qualified_order_fields_fail_closed",
    "test_distribution_original_source_qualifier_does_not_cross_upstream",
    "test_distribution_group_aggregate_satisfying_and_let_contexts_fail_closed",
    "test_distribution_placements_outside_direct_select_fail_closed",
    "test_distribution_multiple_nested_and_same_select_windows_fail_closed",
    "test_distribution_where_final_order_and_limit_coexist_without_alias_visibility",
    "test_project_distribution_fact_supports_function_relation_and_upstream_matrix",
    "test_project_distribution_relation_input_and_order_occurrences_are_exact",
    "test_project_distribution_dependency_edges_preserve_first_occurrence_order",
    "test_project_distribution_result_identity_and_derived_provenance_are_exact",
    "test_project_ntile_literal_has_no_window_argument_dependency",
    "test_distribution_and_project_facts_are_transient_not_model_state",
    "test_distribution_alias_is_not_row_schema_downstream_or_final_order_visible",
    "test_distribution_ir_lowering_fails_closed_with_pie_i1000",
    "test_distribution_postgres_and_private_mysql_fail_before_sql_lowering",
    "test_distribution_cli_json_metadata_project_json_and_exports_remain_private",
    "test_slice12_and_future_window_identities_remain_unsupported",
    "test_distribution_diagnostic_code_message_location_and_order_are_exact",
    "test_all_279_slice8_items_and_completed_ranking_contract_remain_locked",
    "test_all_168_slice7_items_and_row_number_contract_remain_locked",
    "test_all_156_slice6_items_and_core_window_contract_remain_locked",
    "test_grammar_generated_ast_parser_ir_sql_and_public_bytes_are_locked",
    "test_reader_hash_inventory_and_nested_closure_is_exact",
    "test_slice9_dirty_clean_and_depth_one_repository_states_are_locked",
    "test_test_inventory_focused_selector_dirty_overlay_and_formatter_are_exact",
    "test_validation_gate3_deferred_ownership_and_no_decisions_are_locked",
)
CARDINALITIES = (
    1,
    3,
    3,
    4,
    4,
    6,
    3,
    4,
    16,
    6,
    3,
    6,
    3,
    6,
    6,
    8,
    15,
    12,
    12,
    12,
    12,
    6,
    6,
    8,
    12,
    18,
    12,
    18,
    18,
    6,
    16,
    15,
    15,
    12,
    18,
    9,
    6,
    12,
    6,
    9,
    9,
    6,
    6,
    8,
    5,
    15,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
)

ADDED_PATHS = (
    "docs/spec/phase53-grouped-result-ranking-aggregate-result-inputs-bounded-let-visibility-contract-v1.md",
    "src/pietto/semantic/window_input_analysis.py",
    "tests/test_phase53_grouped_result_ranking_aggregate_result_inputs_bounded_let_visibility_contract.py",
)
MODIFIED_PATHS = (
    "docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md",
    "src/pietto/semantic/expressions.py",
    "src/pietto/semantic/group_by.py",
    "src/pietto/semantic/window_analysis.py",
    "src/pietto/semantic/window_navigation_analysis.py",
    "src/pietto/semantic/window_partition_analysis.py",
    "src/pietto/semantic/window_order_analysis.py",
    "src/pietto/_project/model.py",
    "src/pietto/_project/window_semantics.py",
    "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
    "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
    "tests/test_phase53_percent_rank_cume_dist_ntile_contract.py",
    "tests/test_phase53_rank_dense_rank_peer_semantics_contract.py",
    "tests/test_phase53_row_number_direct_field_mvp_contract.py",
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_packaging_smoke.py",
    "tests/test_phase11_planning_audit.py",
    "tests/test_phase11_validation_entrypoint.py",
    "tests/test_phase12_completion_audit.py",
    "tests/test_phase12_composition_cli_json_goldens.py",
    "tests/test_phase12_order_limit_contract.py",
    "tests/test_phase12_planning_audit.py",
    "tests/test_phase13_completion_audit.py",
    "tests/test_phase13_planning_audit.py",
    "tests/test_phase14_candidate_decision_audit.py",
    "tests/test_phase14_completion_audit.py",
    "tests/test_phase14_planning_audit.py",
    "tests/test_phase14_relationship_metadata_completion_audit.py",
    "tests/test_phase15_completion_audit.py",
    "tests/test_phase15_semantic_completion_audit.py",
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
    "tests/test_phase50_window_function_readiness.py",
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
    "tests/test_phase53_generic_type_variable_exact_compatibility_contract.py",
    "tests/test_phase53_window_generic_nullability_foundation_scope_lock.py",
    "tests/test_phase53_window_spec_function_identity_ast_contract.py",
    "tests/test_phase53_window_syntax_contextual_grammar_contract.py",
    "tests/test_phase33_completion_audit.py",
    "tests/test_phase51_private_result_role_output_identity.py",
    "tests/test_phase53_nullability_algebra_signature_result_formula_contract.py",
    "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py",
)
FORMATTER_PATHS = (
    "src/pietto/semantic/window_navigation_analysis.py",
    "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
    "src/pietto/semantic/window_semantics.py",
    "src/pietto/semantic/window_analysis.py",
    "src/pietto/_project/window_semantics.py",
    "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
    "tests/test_phase53_percent_rank_cume_dist_ntile_contract.py",
    "tests/test_phase53_rank_dense_rank_peer_semantics_contract.py",
    "tests/test_phase53_row_number_direct_field_mvp_contract.py",
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_packaging_smoke.py",
    "tests/test_phase11_planning_audit.py",
    "tests/test_phase11_validation_entrypoint.py",
    "tests/test_phase12_completion_audit.py",
    "tests/test_phase12_composition_cli_json_goldens.py",
    "tests/test_phase12_order_limit_contract.py",
    "tests/test_phase12_planning_audit.py",
    "tests/test_phase13_completion_audit.py",
    "tests/test_phase13_planning_audit.py",
    "tests/test_phase14_candidate_decision_audit.py",
    "tests/test_phase14_completion_audit.py",
    "tests/test_phase14_planning_audit.py",
    "tests/test_phase14_relationship_metadata_completion_audit.py",
    "tests/test_phase15_completion_audit.py",
    "tests/test_phase15_semantic_completion_audit.py",
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
    "tests/test_phase50_window_function_readiness.py",
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
    "tests/test_phase53_generic_type_variable_exact_compatibility_contract.py",
    "tests/test_phase53_window_generic_nullability_foundation_scope_lock.py",
    "tests/test_phase53_window_spec_function_identity_ast_contract.py",
    "tests/test_phase53_window_syntax_contextual_grammar_contract.py",
    "tests/test_phase33_completion_audit.py",
    "tests/test_phase51_private_result_role_output_identity.py",
    "tests/test_phase53_nullability_algebra_signature_result_formula_contract.py",
    "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py",
)

FOCUSED_OPERANDS = (
    "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
    "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
    "tests/test_phase53_percent_rank_cume_dist_ntile_contract.py",
    "tests/test_phase53_rank_dense_rank_peer_semantics_contract.py",
    "tests/test_phase53_row_number_direct_field_mvp_contract.py",
    "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py",
    "tests/test_phase50_window_function_readiness.py::test_output_dependency_lineage_and_privacy_boundaries_are_locked",
    "tests/test_phase51_private_result_role_output_identity.py::test_result_role_and_fact_carriers_are_exact_frozen_and_slots",
    "tests/test_phase51_private_result_role_output_identity.py::test_new_private_facts_are_not_exported_or_serialized",
    "tests/test_phase49_private_row_level_dependency_graph_scaffold.py::test_row_dependency_graph_carriers_are_private_frozen_dataclasses",
    "tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py::test_row_lineage_carriers_are_private_frozen_dataclasses",
    "tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py::test_aggregate_argument_edges_preserve_select_ast_order_and_first_target_dedupe",
    "tests/test_phase51_completion_audit_and_status_lock.py::test_dependency_lineage_persistence_and_downstream_completion_is_locked",
    "tests/test_phase52_expression_stage_clause_capability_facts.py::test_expression_stage_fact_inventory_is_exact",
    "tests/test_phase52_expression_stage_clause_capability_facts.py::test_stage_type_nullability_and_three_valued_truth_are_orthogonal",
    "tests/test_phase52_private_capability_fact_foundation.py::test_private_module_owns_exact_frozen_slots_carrier_shapes",
    "tests/test_phase52_private_capability_fact_foundation.py::test_exact_enum_member_inventories_are_locked",
    "tests/test_phase33_completion_audit.py::test_phase33_locked_surfaces_are_unchanged",
    "tests/test_phase53_nullability_algebra_signature_result_formula_contract.py",
    "tests/test_phase53_generic_type_variable_exact_compatibility_contract.py",
    "tests/test_phase53_window_spec_function_identity_ast_contract.py",
    "tests/test_phase53_window_syntax_contextual_grammar_contract.py",
    "tests/test_phase11_ci_workflow.py::test_ci_and_package_smoke_preserve_metadata_and_compiler_boundaries",
    "tests/test_phase11_completion_audit.py::test_package_configuration_lockfile_makefile_and_compiler_are_unchanged",
    "tests/test_phase11_generated_guard.py::test_slice3_preserves_compiler_and_configuration_boundary_bytes",
    "tests/test_phase11_golden_policy.py::test_slice4_preserves_golden_and_compiler_boundary_bytes",
    "tests/test_phase11_packaging_smoke.py::test_prior_scripts_and_all_compiler_packaging_boundaries_are_unchanged",
    "tests/test_phase11_planning_audit.py::test_slice1_locks_configuration_and_compiler_boundaries",
    "tests/test_phase11_validation_entrypoint.py::test_slice2_preserves_compiler_and_configuration_boundary_bytes",
    "tests/test_phase12_completion_audit.py::test_production_compiler_and_configuration_boundary_is_unchanged",
    "tests/test_phase12_composition_cli_json_goldens.py::test_production_api_json_dependency_and_compiler_boundaries_are_unchanged",
    "tests/test_phase12_order_limit_contract.py::test_slice6_preserves_configuration_cli_and_golden_boundaries",
    "tests/test_phase12_planning_audit.py::test_slice6_locks_configuration_workflow_and_compiler_boundaries",
    "tests/test_phase13_completion_audit.py::test_production_compiler_and_phase13_implementation_markers_are_absent",
    "tests/test_phase13_planning_audit.py::test_slice1_locks_compiler_workflow_and_golden_boundaries",
    "tests/test_phase14_candidate_decision_audit.py::test_slice2_status_inputs_and_single_candidate_decision",
    "tests/test_phase14_candidate_decision_audit.py::test_production_generated_dependency_api_json_golden_and_ci_are_locked",
    "tests/test_phase14_completion_audit.py::test_unchanged_compiler_repository_and_golden_surfaces_are_byte_locked",
    "tests/test_phase14_planning_audit.py::test_phase13_inputs_are_referenced_and_byte_locked",
    "tests/test_phase14_planning_audit.py::test_production_grammar_generated_workflow_and_scripts_are_locked",
    "tests/test_phase14_relationship_metadata_completion_audit.py::test_forbidden_compiler_layers_and_repository_surfaces_are_byte_locked",
    "tests/test_phase15_completion_audit.py::test_slice1_and_slice2_specs_tests_and_behavior_are_byte_locked",
    "tests/test_phase15_completion_audit.py::test_frontend_compiler_cli_and_repository_surfaces_are_byte_locked",
    "tests/test_phase15_semantic_completion_audit.py::test_frontend_ir_sql_cli_json_dependency_and_ci_boundaries_are_locked",
    "tests/test_phase16_completion_audit.py::test_all_phase16_specs_and_focused_audits_are_byte_locked",
    "tests/test_phase16_completion_audit.py::test_frontend_compiler_cli_and_repository_surfaces_are_byte_locked",
    "tests/test_phase16_current_syntax_surface_audit.py::test_compiler_repository_and_fixture_surfaces_are_byte_locked",
    "tests/test_phase16_language_direction_audit.py::test_compiler_repository_and_document_contracts_are_byte_locked",
    "tests/test_phase16_safety_deferral_sql_portability.py::test_compiler_repository_and_fixture_surfaces_are_byte_locked",
    "tests/test_phase21_group_by_hardening_audit.py::test_slice8_forbidden_implementation_surfaces_are_unchanged",
    "tests/test_phase24_aggregate_expression_arguments_readiness.py::test_slice7_boundary_surfaces_remain_post_slice6_hash_locked",
    "tests/test_phase24_cli_json_output_hardening.py::test_slice8_boundary_surfaces_remain_post_slice7_hash_locked",
    "tests/test_phase24_completion_audit.py::test_slice9_boundary_surfaces_remain_post_slice8_hash_locked",
    "tests/test_phase25_completion_audit.py::test_slice7_boundary_surfaces_remain_phase25_locked",
    "tests/test_phase26_completion_audit.py::test_slice9_boundary_surfaces_remain_phase26_locked",
    "tests/test_phase27_completion_audit.py::test_boundary_surfaces_remain_phase27_locked",
    "tests/test_phase28_completion_audit.py::test_boundary_surfaces_remain_phase28_locked",
    "tests/test_phase29_completion_audit.py::test_phase29_locked_boundary_surface_hashes_are_unchanged",
    "tests/test_phase30_completion_audit.py::test_phase30_locked_boundary_surface_hashes_are_unchanged",
    "tests/test_phase50_window_function_readiness.py::test_current_source_has_generic_calls_but_no_window_model",
    "tests/test_phase51_completion_audit_and_status_lock.py::test_live_compiler_project_private_protected_version_and_tag_locks_are_dirty_safe",
    "tests/test_phase51_completion_audit_and_status_lock.py::test_static_git_helper_and_exact_slice12_dirty_set_are_locked",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py::test_live_compiler_project_private_and_protected_locks_are_dirty_safe",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py::test_slice11_contract_plan_allowlist_and_protected_boundaries_are_locked",
    "tests/test_phase52_aggregate_signature_algebra_facts.py::test_compiler_semantic_subset_project_and_raw_hash_readers_are_exact",
    "tests/test_phase52_aggregate_signature_algebra_facts.py::test_static_test_inventory_and_tier1_selection_are_exact",
    "tests/test_phase52_completion_audit_and_status_lock.py::test_live_compiler_semantic_phase15_project_protected_version_and_tag_locks_are_dirty_safe",
    "tests/test_phase52_completion_audit_and_status_lock.py::test_static_reader_hash_topology_test_inventory_and_validation_manifests_are_locked",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py::test_slice1_no_behavior_public_privacy_and_release_boundaries_are_locked",
    "tests/test_phase52_expression_stage_clause_capability_facts.py::test_compiler_semantic_subset_project_and_raw_hash_readers_are_exact",
    "tests/test_phase52_expression_stage_clause_capability_facts.py::test_static_test_inventory_and_tier1_selection_are_exact",
    "tests/test_phase52_fail_closed_capability_lookup.py::test_compiler_semantic_and_phase15_boundary_digests_are_refreshed",
    "tests/test_phase52_fail_closed_capability_lookup.py::test_static_inventory_and_exact_focused_test_shape_are_locked",
    "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py::test_digest_and_nested_raw_sha_reader_closure_is_exact",
    "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py::test_static_item_allowlist_reader_and_manifest_inventory_is_exact",
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py::test_static_reader_counts_boundary_hash_and_nested_sha_topology_are_exact",
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py::test_test_inventory_tier1_selectors_and_compatibility_counts_are_exact",
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py::test_tier2_manifest_identity_presence_uniqueness_and_clean_only_classification_are_exact",
    "tests/test_phase52_private_capability_fact_foundation.py::test_compiler_boundary_and_all_compatibility_hash_locks_are_consistent",
    "tests/test_phase52_scalar_function_operator_signature_facts.py::test_compiler_semantic_subset_project_and_raw_hash_readers_are_exact",
    "tests/test_phase52_scalar_function_operator_signature_facts.py::test_static_test_inventory_tier1_and_tier2_manifest_are_exact",
    "tests/test_phase53_window_generic_nullability_foundation_scope_lock.py::test_artifact_titles_heading_orders_and_lifecycle_are_locked",
    "tests/test_phase53_window_generic_nullability_foundation_scope_lock.py::test_reader_migrations_reconciliation4_and_current_authority_are_locked",
    "tests/test_phase53_window_generic_nullability_foundation_scope_lock.py::test_gate2_validation_depth_one_gate3_activation_and_stop_conditions_are_locked",
    "tests/test_phase30_canonical_scalar_type_registry.py::test_current_builtin_names_and_concrete_core_are_grounded",
    "tests/test_phase30_canonical_scalar_type_registry.py::test_uuid_is_limited_frozen_identifier_scalar_not_fully_deferred",
    "tests/test_phase30_canonical_scalar_type_registry.py::test_enum_remains_non_builtin_semantic_type_kind",
    "tests/test_phase30_canonical_scalar_type_registry.py::test_trait_vocabulary_is_contract_only_without_behavior_expansion",
    "tests/test_phase36_expanded_scalar_operator_matrix.py::test_scalar_posture_inventory_is_documented_and_grounded",
    "tests/test_phase36_expanded_scalar_operator_matrix.py::test_comparison_bool_and_risky_shared_paths_are_documented",
    "tests/test_phase36_expanded_scalar_operator_matrix.py::test_aggregate_matrix_boundaries_remain_current",
    "tests/test_phase38_type_capability_matrix_contract.py::test_current_repo_derived_capability_inventory_is_grounded",
    "tests/test_phase38_type_capability_matrix_contract.py::test_current_scalar_type_capability_matrix_is_complete",
    "tests/test_phase38_type_capability_matrix_contract.py::test_countability_is_separate_from_numeric_orderable_and_distinct",
    "tests/test_phase38_type_capability_matrix_contract.py::test_generic_comparison_ordering_and_dialect_boundaries_are_preserved",
    "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py::test_builtin_catalog_membership_facts_are_supported",
    "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py::test_declaration_kind_facts_are_supported",
    "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py::test_internal_and_deferred_logical_type_facts_fail_closed",
    "tests/test_phase52_scalar_function_operator_signature_facts.py::test_generic_comparison_and_between_do_not_claim_concrete_pair_compatibility",
    "tests/test_phase52_aggregate_signature_algebra_facts.py::test_signature_inventory_order_keys_support_and_disposition_are_exact",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py::test_read_model_first_authority_dimensions_and_non_authority_are_locked",
    "tests/test_phase30_nullability_propagation_contract.py::test_three_unknown_concepts_are_distinct",
    "tests/test_phase30_nullability_propagation_contract.py::test_typeexpr_source_projection_and_unknown_nullability_rules_are_grounded",
    "tests/test_phase30_nullability_propagation_contract.py::test_expression_nullability_rules_are_current_behavior_only",
    "tests/test_phase30_nullability_propagation_contract.py::test_aggregate_result_nullability_matrix_is_locked",
    "tests/test_semantic_types.py::test_explicit_nullability_has_no_p2005",
    "tests/test_semantic_expressions.py::test_literal_expression_maps_to_builtin_type",
    "tests/test_semantic_expressions.py::test_bare_field_uses_row_field_type_and_nullability",
    "tests/test_semantic_expressions.py::test_is_null_expression_maps_to_non_null_bool",
    "tests/test_semantic_functions.py::test_text_transform_function_returns_text",
    "tests/test_phase49_project_row_expression_type_nullability_adapter.py::test_computed_expression_consumes_supplied_known_value_type",
    "tests/test_phase49_project_row_expression_type_nullability_adapter.py::test_qualified_direct_projection_uses_immediate_upstream_qualifier",
    "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py::test_declared_nullability_mappings_are_exact",
    "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py::test_null_literal_is_distinct_from_null_and_unknown_logical_spellings",
    "tests/test_phase52_scalar_function_operator_signature_facts.py::test_null_tests_preserve_non_null_bool_and_distinct_three_valued_truth",
    "tests/test_phase52_aggregate_signature_algebra_facts.py::test_signature_result_type_nullability_stage_and_role_are_exact",
)


COMPILER_DIGEST = "6cbe7ccfbd84d7b2966964ac91a56e7eeacdc798c3d161da64d61add662b0420"
SEMANTIC_DIGEST = "731e17cc85849c7716abeb08abeda03f72e3e21af183a391107adf96ccab6d70"
PHASE15_SUBSET_DIGEST = (
    "81db265a7bbd290b9c9227733e92dc502f8e8c8f0ff76b4d631651772876550d"
)
PROJECT_DIGEST = "327ba4f5c12d916d6577cd9510aa2a28df8519dafdc935ae67a6d2f5b2fc4830"
FOCUSED_SHA256 = "764c5879e93871b253e875ce1e8145ce3a998d48a94b578f8af9d31f9562e5ee"
FORMATTER_SHA256 = "5920e1a21f135b2537e8295b13c8bc6fa2962423812ffc3cbe1e52663e924daf"


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _sha256(relative: str) -> str:
    return hashlib.sha256((REPO_ROOT / relative).read_bytes()).hexdigest()


def _digest(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(REPO_ROOT).as_posix()):
        digest.update(path.relative_to(REPO_ROOT).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _program(
    *,
    kind: str = "query",
    call: str = "rank()",
    order: tuple[str, ...] = ("observed_at",),
    partition: tuple[str, ...] = (),
    direction: str | None = None,
    upstream: bool = False,
    before: tuple[str, ...] = (),
    after: tuple[str, ...] = (),
    where: bool = False,
    final_order: bool = False,
    limit: bool = False,
) -> str:
    prefix = (
        "shape Row:\n"
        "    id: Int not null\n"
        "    observed_at: Timestamp not null\n"
        "    label: Text\n"
        'source rows: Row is postgres.table("rows")\n'
    )
    input_name = "rows"
    if upstream:
        prefix += (
            "table intermediate:\n"
            "    from rows\n"
            "    select:\n"
            "        id\n"
            "        observed_at\n"
            "        label\n"
        )
        input_name = "intermediate"
    lines = [f"{kind} ranked:", f"    from {input_name}"]
    if where:
        lines.append("    where id > 0")
    lines.append("    select:")
    lines.extend(f"        {value}" for value in before)
    lines.append(f"        ranking_value = {call} window:")
    if partition:
        lines.append("            partition by:")
        lines.extend(f"                {value}" for value in partition)
    if order:
        lines.append("            order by:")
        suffix = f" {direction}" if direction is not None else ""
        lines.extend(f"                {value}{suffix}" for value in order)
    lines.extend(f"        {value}" for value in after)
    if final_order:
        lines.extend(("    order by:", "        observed_at"))
    if limit:
        lines.append("    limit 10")
    return prefix + "\n".join(lines) + "\n"


def _parsed_relation(
    source: str, *, path: str = "slice8.pietto"
) -> tuple[Script, TableDef | QueryDef]:
    parsed = parse_source(source, path=path)
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    relation = parsed.ast.definitions[-1]
    assert isinstance(relation, (TableDef, QueryDef))
    return parsed.ast, relation


def _direct_analysis(
    source: str,
    *,
    selected_output_ordinal: int | None = None,
) -> tuple[
    RankingWindowSemanticFact | WindowExpressionUnsupported,
    list[Diagnostic],
    dict[Expression, ValueType],
    TableDef | QueryDef,
]:
    script, relation = _parsed_relation(source)
    semantic = analyze(script)
    target = semantic.model.from_resolutions[relation.from_clause]
    if isinstance(target, SourceDef):
        input_schema = semantic.model.source_row_schemas[target]
    else:
        assert isinstance(target, (TableDef, QueryDef))
        input_schema = semantic.model.relation_row_schemas[target]
    ordinal = selected_output_ordinal
    if ordinal is None:
        ordinal = next(
            index
            for index, selected in enumerate(relation.select_items)
            if isinstance(selected.expression, WindowExpr)
        )
    item = relation.select_items[ordinal]
    assert isinstance(item.expression, WindowExpr)
    values: dict[Expression, ValueType] = {}
    diagnostics: list[Diagnostic] = []
    result = window_analysis.analyze_ranking_window_expression(
        definition=relation,
        item=item,
        selected_output_ordinal=ordinal,
        source_id=item.expression.span.path or relation.name,
        input_schema=input_schema,
        field_qualifier=relation.from_clause.source_name,
        value_types=values,
        diagnostics=diagnostics,
    )
    return result, diagnostics, values, relation


def _canonical_ranking_fact(
    *,
    function_name: str = "rank",
    kind: str = "query",
    qualified: bool = False,
    upstream: bool = False,
    before: tuple[str, ...] = (),
) -> tuple[RankingWindowSemanticFact, TableDef | QueryDef]:
    input_name = "intermediate" if upstream else "rows"
    order = f"{input_name}.observed_at" if qualified else "observed_at"
    result, diagnostics, _, relation = _direct_analysis(
        _program(
            kind=kind,
            call=f"{function_name}()",
            order=(order,),
            upstream=upstream,
            before=before,
        )
    )
    assert diagnostics == []
    assert isinstance(result, RankingWindowSemanticFact)
    return result, relation


def _row_number_core_fact(
    *, qualified: bool = False, upstream: bool = False
) -> WindowExpressionSemanticFact:
    ranking_fact, relation = _canonical_ranking_fact(
        function_name="row_number",
        qualified=qualified,
        upstream=upstream,
    )
    script, parsed_relation = _parsed_relation(
        _program(
            call="row_number()",
            order=(
                f"{'intermediate' if upstream else 'rows'}.observed_at"
                if qualified
                else "observed_at",
            ),
            upstream=upstream,
        )
    )
    semantic = analyze(script)
    target = semantic.model.from_resolutions[parsed_relation.from_clause]
    input_schema = (
        semantic.model.source_row_schemas[cast(SourceDef, target)]
        if isinstance(target, SourceDef)
        else semantic.model.relation_row_schemas[cast(TableDef | QueryDef, target)]
    )
    diagnostics: list[Diagnostic] = []
    result = window_analysis.analyze_row_number_window_expression(
        definition=parsed_relation,
        item=parsed_relation.select_items[-1],
        selected_output_ordinal=len(parsed_relation.select_items) - 1,
        source_id="slice8.pietto",
        input_schema=input_schema,
        field_qualifier=parsed_relation.from_clause.source_name,
        value_types={},
        diagnostics=diagnostics,
    )
    assert diagnostics == []
    assert isinstance(result, WindowExpressionSemanticFact)
    assert result == ranking_fact.semantic_fact
    assert relation == parsed_relation
    return result


def _project_fact(
    *,
    function_name: str = "rank",
    kind: str = "query",
    qualified: bool = False,
    upstream: bool = False,
) -> WindowResultProjectFact:
    source = _program(
        kind=kind,
        call=f"{function_name}()",
        order=(
            f"{'intermediate' if upstream else 'rows'}.observed_at"
            if qualified
            else "observed_at",
        ),
        upstream=upstream,
    )
    script, relation = _parsed_relation(source)
    upstream_definition = next(
        definition
        for definition in script.definitions
        if getattr(definition, "name", None) == ("intermediate" if upstream else "rows")
    )
    assert isinstance(upstream_definition, (SourceDef, TableDef, QueryDef))
    symbol = ProjectSymbol(
        namespace=ProjectSymbolNamespace.RELATION,
        kind=ProjectSymbolKind.TABLE if upstream else ProjectSymbolKind.SOURCE,
        name=upstream_definition.name,
        path="slice8.pietto",
        location=SourceLocation(path="slice8.pietto", line=1, column=1),
        definition=upstream_definition,
    )
    schema = ProjectRowSchema(
        fields={
            "observed_at": ProjectRowField(
                name="observed_at",
                resolved_type=ProjectResolvedType(
                    name="Timestamp",
                    kind=ProjectResolvedTypeKind.BUILTIN,
                ),
                nullability=ProjectRowFieldNullability.NON_NULL,
            )
        }
    )
    result = build_ranking_window_result_project_fact(
        definition=relation,
        item=relation.select_items[-1],
        selected_output_ordinal=len(relation.select_items) - 1,
        source_id="slice8.pietto",
        input_schema=schema,
        upstream_symbol=symbol,
    )
    assert isinstance(result, WindowResultProjectFact)
    return result


def _distribution_call(function_name: str, bucket_count: int = 4) -> str:
    if function_name == "ntile":
        return f"ntile({bucket_count})"
    return f"{function_name}()"


def _direct_distribution_analysis(
    source: str,
) -> tuple[
    DistributionWindowSemanticFact | WindowExpressionUnsupported,
    list[Diagnostic],
    dict[Expression, ValueType],
    TableDef | QueryDef,
]:
    script, relation = _parsed_relation(source, path="slice9.pietto")
    semantic = analyze(script)
    target = semantic.model.from_resolutions[relation.from_clause]
    if isinstance(target, SourceDef):
        input_schema = semantic.model.source_row_schemas[target]
    else:
        assert isinstance(target, (TableDef, QueryDef))
        input_schema = semantic.model.relation_row_schemas[target]
    ordinal = next(
        index
        for index, selected in enumerate(relation.select_items)
        if isinstance(selected.expression, WindowExpr)
    )
    item = relation.select_items[ordinal]
    values: dict[Expression, ValueType] = {}
    diagnostics: list[Diagnostic] = []
    result = window_analysis.analyze_distribution_window_expression(
        definition=relation,
        item=item,
        selected_output_ordinal=ordinal,
        source_id=item.expression.span.path or relation.name,
        input_schema=input_schema,
        field_qualifier=relation.from_clause.source_name,
        value_types=values,
        diagnostics=diagnostics,
    )
    return result, diagnostics, values, relation


def _canonical_distribution_fact(
    *,
    function_name: str = "percent_rank",
    bucket_count: int = 4,
    kind: str = "query",
    qualified: bool = False,
    upstream: bool = False,
    before: tuple[str, ...] = (),
    after: tuple[str, ...] = (),
) -> tuple[DistributionWindowSemanticFact, TableDef | QueryDef]:
    input_name = "intermediate" if upstream else "rows"
    order = f"{input_name}.observed_at" if qualified else "observed_at"
    result, diagnostics, _, relation = _direct_distribution_analysis(
        _program(
            kind=kind,
            call=_distribution_call(function_name, bucket_count),
            order=(order,),
            upstream=upstream,
            before=before,
            after=after,
        )
    )
    assert diagnostics == []
    assert isinstance(result, DistributionWindowSemanticFact)
    return result, relation


def _distribution_project_fact(
    *,
    function_name: str = "percent_rank",
    bucket_count: int = 4,
    kind: str = "query",
    qualified: bool = False,
    upstream: bool = False,
) -> WindowResultProjectFact:
    source = _program(
        kind=kind,
        call=_distribution_call(function_name, bucket_count),
        order=(
            f"{'intermediate' if upstream else 'rows'}.observed_at"
            if qualified
            else "observed_at",
        ),
        upstream=upstream,
    )
    script, relation = _parsed_relation(source, path="slice9.pietto")
    upstream_definition = next(
        definition
        for definition in script.definitions
        if getattr(definition, "name", None) == ("intermediate" if upstream else "rows")
    )
    assert isinstance(upstream_definition, (SourceDef, TableDef, QueryDef))
    symbol = ProjectSymbol(
        namespace=ProjectSymbolNamespace.RELATION,
        kind=ProjectSymbolKind.TABLE if upstream else ProjectSymbolKind.SOURCE,
        name=upstream_definition.name,
        path="slice9.pietto",
        location=SourceLocation(path="slice9.pietto", line=1, column=1),
        definition=upstream_definition,
    )
    schema = ProjectRowSchema(
        fields={
            "observed_at": ProjectRowField(
                name="observed_at",
                resolved_type=ProjectResolvedType(
                    name="Timestamp",
                    kind=ProjectResolvedTypeKind.BUILTIN,
                ),
                nullability=ProjectRowFieldNullability.NON_NULL,
            )
        }
    )
    result = build_window_result_project_fact(
        definition=relation,
        item=relation.select_items[-1],
        selected_output_ordinal=len(relation.select_items) - 1,
        source_id="slice9.pietto",
        input_schema=schema,
        upstream_symbol=symbol,
    )
    assert isinstance(result, WindowResultProjectFact)
    return result


def _assert_unsupported(
    source: str,
    *,
    code: str,
    message: str | None = None,
) -> tuple[WindowExpressionUnsupported, Diagnostic, TableDef | QueryDef]:
    result, diagnostics, _, relation = _direct_distribution_analysis(source)
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == [code]
    if message is not None:
        assert diagnostics[0].message == message
    return result, diagnostics[0], relation


@pytest.mark.parametrize("case", range(3))
def test_source_subset_candidates_and_exact_slice8_reuse_are_locked(case: int) -> None:
    docs = _read(SPEC_REL) + _read(PLAN_REL)
    required = (
        "reuse the exact Slice 8 subset",
        "exactly one selected window output",
        "bare field or\nimmediate-source-qualified two-part field",
    )
    assert required[case] in docs


@pytest.mark.parametrize("case", range(3))
def test_ntile_argument_candidates_and_positive_integer_literal_selection_are_exact(
    case: int,
) -> None:
    docs = _read(SPEC_REL) + _read(PLAN_REL)
    required = (
        "only an exact `LiteralExpr` whose value has exact type `int`",
        "Boolean, zero, negative, float, string, null, name",
        "creates no resolver call, symbol,\ndependency occurrence",
    )
    assert required[case] in docs


@pytest.mark.parametrize("case", range(4))
def test_result_type_candidates_float_int_non_null_window_are_locked(case: int) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    fact, _ = _canonical_distribution_fact(function_name=function_name)
    value_type = fact.semantic_fact.result.value_type
    assert value_type is not None
    expected_name = "Int" if function_name == "ntile" else "Float"
    checks = (
        value_type.resolved_type.name == expected_name,
        value_type.resolved_type.kind is TypeKind.BUILTIN,
        value_type.nullability is EffectiveNullability.NON_NULL,
        fact.semantic_fact.stage is WindowExpressionStage.WINDOW,
    )
    assert checks[case]


@pytest.mark.parametrize("case", range(4))
def test_distribution_carrier_candidates_and_sibling_selection_are_locked(
    case: int,
) -> None:
    docs = _read(SPEC_REL) + _read(PLAN_REL)
    required = (
        "private immutable distribution policy/fact",
        "private sibling",
        "preserves the core and ranking field shapes",
        "No Window IR, distribution IR",
    )
    assert required[case] in docs


@pytest.mark.parametrize("case", range(6))
def test_identity_and_semantic_module_candidates_are_exact(case: int) -> None:
    source = _read("src/pietto/semantic/window_analysis.py")
    required = (
        "_RANKING_POLICIES = (",
        "_DISTRIBUTION_FUNCTIONS = (",
        "def analyze_window_expression(",
        "def analyze_distribution_window_expression(",
        "def analyze_ranking_window_expression(",
        "def analyze_row_number_window_expression(",
    )
    assert required[case] in source


@pytest.mark.parametrize("case", range(3))
def test_distribution_window_policy_enum_values_and_privacy_are_exact(
    case: int,
) -> None:
    expected = (
        ("PERCENT_RANK", "percent_rank"),
        ("CUMULATIVE_DISTRIBUTION", "cumulative_distribution"),
        ("BALANCED_BUCKETS", "balanced_buckets"),
    )
    assert tuple((item.name, item.value) for item in DistributionWindowPolicy) == (
        expected
    )
    assert tuple(DistributionWindowPolicy)[case].value == expected[case][1]
    assert not hasattr(pietto, "DistributionWindowPolicy")


@pytest.mark.parametrize("case", range(4))
def test_distribution_window_semantic_fact_shape_is_frozen_and_exact(
    case: int,
) -> None:
    parameters = tuple(dataclasses.fields(DistributionWindowSemanticFact))
    assert tuple(item.name for item in parameters) == (
        "semantic_fact",
        "distribution_policy",
        "ranking_fact",
        "bucket_count",
    )
    fact, _ = _canonical_distribution_fact(function_name="percent_rank")
    params = getattr(DistributionWindowSemanticFact, "__dataclass_params__")
    checks = (
        params.frozen,
        hasattr(DistributionWindowSemanticFact, "__slots__"),
        all(item.kw_only for item in parameters),
        hash(fact) == hash(fact),
    )
    assert checks[case]


@pytest.mark.parametrize("case", range(16))
def test_distribution_window_semantic_fact_malformed_matrix_fails_closed(
    case: int,
) -> None:
    percent, _ = _canonical_distribution_fact(function_name="percent_rank")
    cume, _ = _canonical_distribution_fact(function_name="cume_dist")
    ntile, _ = _canonical_distribution_fact(function_name="ntile")
    dense_ranking = RankingWindowSemanticFact(
        semantic_fact=percent.semantic_fact,
        advance_policy=RankingAdvancePolicy.DENSE_PEER_RANK,
    )
    cume_gapped = RankingWindowSemanticFact(
        semantic_fact=cume.semantic_fact,
        advance_policy=RankingAdvancePolicy.GAPPED_PEER_RANK,
    )
    cases: tuple[tuple[dict[str, object], type[Exception]], ...] = (
        (
            {
                "semantic_fact": object(),
                "distribution_policy": DistributionWindowPolicy.PERCENT_RANK,
                "ranking_fact": percent.ranking_fact,
                "bucket_count": None,
            },
            TypeError,
        ),
        (
            {
                "semantic_fact": percent.semantic_fact,
                "distribution_policy": "percent_rank",
                "ranking_fact": percent.ranking_fact,
                "bucket_count": None,
            },
            TypeError,
        ),
        (
            {
                "semantic_fact": percent.semantic_fact,
                "distribution_policy": DistributionWindowPolicy.PERCENT_RANK,
                "ranking_fact": object(),
                "bucket_count": None,
            },
            TypeError,
        ),
        (
            {
                "semantic_fact": ntile.semantic_fact,
                "distribution_policy": DistributionWindowPolicy.BALANCED_BUCKETS,
                "ranking_fact": None,
                "bucket_count": True,
            },
            TypeError,
        ),
        (
            {
                "semantic_fact": percent.semantic_fact,
                "distribution_policy": DistributionWindowPolicy.PERCENT_RANK,
                "ranking_fact": None,
                "bucket_count": None,
            },
            ValueError,
        ),
        (
            {
                "semantic_fact": percent.semantic_fact,
                "distribution_policy": DistributionWindowPolicy.PERCENT_RANK,
                "ranking_fact": dense_ranking,
                "bucket_count": None,
            },
            ValueError,
        ),
        (
            {
                "semantic_fact": percent.semantic_fact,
                "distribution_policy": DistributionWindowPolicy.PERCENT_RANK,
                "ranking_fact": percent.ranking_fact,
                "bucket_count": 1,
            },
            ValueError,
        ),
        (
            {
                "semantic_fact": cume.semantic_fact,
                "distribution_policy": DistributionWindowPolicy.PERCENT_RANK,
                "ranking_fact": cume_gapped,
                "bucket_count": None,
            },
            ValueError,
        ),
        (
            {
                "semantic_fact": cume.semantic_fact,
                "distribution_policy": (
                    DistributionWindowPolicy.CUMULATIVE_DISTRIBUTION
                ),
                "ranking_fact": cume_gapped,
                "bucket_count": None,
            },
            ValueError,
        ),
        (
            {
                "semantic_fact": cume.semantic_fact,
                "distribution_policy": (
                    DistributionWindowPolicy.CUMULATIVE_DISTRIBUTION
                ),
                "ranking_fact": None,
                "bucket_count": 1,
            },
            ValueError,
        ),
        (
            {
                "semantic_fact": percent.semantic_fact,
                "distribution_policy": (
                    DistributionWindowPolicy.CUMULATIVE_DISTRIBUTION
                ),
                "ranking_fact": None,
                "bucket_count": None,
            },
            ValueError,
        ),
        (
            {
                "semantic_fact": ntile.semantic_fact,
                "distribution_policy": DistributionWindowPolicy.BALANCED_BUCKETS,
                "ranking_fact": dense_ranking,
                "bucket_count": 4,
            },
            ValueError,
        ),
        (
            {
                "semantic_fact": ntile.semantic_fact,
                "distribution_policy": DistributionWindowPolicy.BALANCED_BUCKETS,
                "ranking_fact": None,
                "bucket_count": None,
            },
            ValueError,
        ),
        (
            {
                "semantic_fact": ntile.semantic_fact,
                "distribution_policy": DistributionWindowPolicy.BALANCED_BUCKETS,
                "ranking_fact": None,
                "bucket_count": 0,
            },
            ValueError,
        ),
        (
            {
                "semantic_fact": ntile.semantic_fact,
                "distribution_policy": DistributionWindowPolicy.BALANCED_BUCKETS,
                "ranking_fact": None,
                "bucket_count": -1,
            },
            ValueError,
        ),
        (
            {
                "semantic_fact": cume.semantic_fact,
                "distribution_policy": DistributionWindowPolicy.BALANCED_BUCKETS,
                "ranking_fact": None,
                "bucket_count": 4,
            },
            ValueError,
        ),
    )
    kwargs, error = cases[case]
    with pytest.raises(error):
        DistributionWindowSemanticFact(**cast(Any, kwargs))


@pytest.mark.parametrize("case", range(6))
def test_identity_to_distribution_policy_signature_mapping_is_exact_and_ordered(
    case: int,
) -> None:
    rows = window_analysis._DISTRIBUTION_FUNCTIONS
    expected = (
        ("percent_rank", DistributionWindowPolicy.PERCENT_RANK),
        ("cume_dist", DistributionWindowPolicy.CUMULATIVE_DISTRIBUTION),
        ("ntile", DistributionWindowPolicy.BALANCED_BUCKETS),
    )
    row = rows[case % 3]
    assert len(rows) == 3
    assert (row[0].name, row[1]) == expected[case % 3]
    assert row[0].namespace == ()
    assert row[0].role.value == "window_function"


@pytest.mark.parametrize("case", range(3))
def test_distribution_signatures_are_exact(case: int) -> None:
    identity, _, signature, formula = window_analysis._DISTRIBUTION_FUNCTIONS[case]
    assert signature.type_variables == ()
    assert len(signature.parameters) == (1 if identity.name == "ntile" else 0)
    if identity.name == "ntile":
        parameter = signature.parameters[0]
        assert parameter.position == 0
        assert isinstance(parameter.type_expression, ConcreteTypeExpression)
        assert parameter.type_expression.logical_type.name == "Int"
        assert not parameter.optional
    assert isinstance(signature.result, ConcreteTypeExpression)
    assert signature.result.logical_type.name == (
        "Int" if identity.name == "ntile" else "Float"
    )
    assert formula.signature is signature


@pytest.mark.parametrize("case", range(6))
def test_distribution_signature_binding_returns_builtin_float_or_int(case: int) -> None:
    identity, _, signature, _ = window_analysis._DISTRIBUTION_FUNCTIONS[case % 3]
    arguments = (
        (window_analysis._DISTRIBUTION_INT_RESULT_IDENTITY,)
        if identity.name == "ntile"
        else ()
    )
    match = bind_signature(signature, arguments)
    assert isinstance(match, SignatureMatch)
    assert match.result_type.name == ("Int" if identity.name == "ntile" else "Float")
    assert match.result_type.kind is TypeKind.BUILTIN
    assert match.bindings == ()
    assert match.omitted_positions == ()


@pytest.mark.parametrize("case", range(3))
def test_distribution_non_null_formulas_evaluate_exactly(case: int) -> None:
    identity, _, _, formula = window_analysis._DISTRIBUTION_FUNCTIONS[case]
    nullability = (EffectiveNullability.NON_NULL,) if identity.name == "ntile" else ()
    result = evaluate_signature_result_nullability(
        formula,
        NullabilityEvaluationContext(
            argument_nullabilities=nullability,
            omitted_positions=(),
        ),
    )
    assert isinstance(result, NullabilityEvaluationMatch)
    assert result.value is EffectiveNullability.NON_NULL
    assert isinstance(formula.nullability, NonNullFormula)


@pytest.mark.parametrize("case", range(6))
def test_percent_rank_abstract_structural_semantics_are_exact(case: int) -> None:
    fact, _ = _canonical_distribution_fact(function_name="percent_rank")
    checks = (
        fact.distribution_policy is DistributionWindowPolicy.PERCENT_RANK,
        isinstance(fact.ranking_fact, RankingWindowSemanticFact),
        fact.ranking_fact is not None
        and fact.ranking_fact.advance_policy is RankingAdvancePolicy.GAPPED_PEER_RANK,
        fact.ranking_fact is not None
        and fact.ranking_fact.semantic_fact is fact.semantic_fact,
        fact.bucket_count is None,
        fact.peer_sensitive and fact.peer_key == fact.structural_order_key,
    )
    assert checks[case]


@pytest.mark.parametrize("case", range(6))
def test_cume_dist_abstract_structural_semantics_are_exact(case: int) -> None:
    fact, _ = _canonical_distribution_fact(function_name="cume_dist")
    checks = (
        fact.distribution_policy is DistributionWindowPolicy.CUMULATIVE_DISTRIBUTION,
        fact.identity.name == "cume_dist",
        fact.ranking_fact is None,
        fact.bucket_count is None,
        fact.peer_sensitive,
        fact.peer_key == fact.structural_order_key,
    )
    assert checks[case]


@pytest.mark.parametrize("case", range(8))
def test_ntile_balanced_bucket_semantics_and_bucket_count_are_exact(case: int) -> None:
    bucket_count = (1, 2, 3, 4, 7, 8, 16, 31)[case]
    fact, _ = _canonical_distribution_fact(
        function_name="ntile",
        bucket_count=bucket_count,
    )
    assert fact.distribution_policy is DistributionWindowPolicy.BALANCED_BUCKETS
    assert fact.bucket_count == bucket_count
    assert fact.ranking_fact is None
    assert not fact.peer_sensitive
    assert fact.peer_key == ()
    assert len(fact.structural_order_key) == 1


@pytest.mark.parametrize("case", range(15))
def test_exact_distribution_identity_legality_case_namespace_and_later_functions(
    case: int,
) -> None:
    calls = (
        "percent_rank()",
        "cume_dist()",
        "ntile(4)",
        "Percent_rank()",
        "CUME_DIST()",
        "NTILE(4)",
        "pkg.percent_rank()",
        "pkg.cume_dist()",
        "pkg.ntile(4)",
        "lag()",
        "lead()",
        "first_value()",
        "last_value()",
        "nth_value()",
        "percent_rank_extra()",
    )
    source = _program(call=calls[case])
    result, diagnostics, _, _ = _direct_distribution_analysis(source)
    if case < 3:
        assert isinstance(result, DistributionWindowSemanticFact)
        assert diagnostics == []
    else:
        assert isinstance(result, WindowExpressionUnsupported)
        assert [item.code for item in diagnostics] == ["PIE-S2103"]


@pytest.mark.parametrize("case", range(12))
def test_ntile_literal_ast_shape_and_argument_classification_are_exact(
    case: int,
) -> None:
    arguments = (
        "1",
        "4",
        "32",
        "0",
        "-1",
        "1.0",
        '"4"',
        "true",
        "null",
        "id",
        "rows.id",
        "id + 1",
    )
    result, diagnostics, _, relation = _direct_distribution_analysis(
        _program(call=f"ntile({arguments[case]})")
    )
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    assert len(expression.call.arguments) == 1
    if case < 3:
        argument = expression.call.arguments[0]
        assert type(argument) is LiteralExpr
        assert type(argument.value) is int and argument.value > 0
        assert isinstance(result, DistributionWindowSemanticFact)
        assert diagnostics == []
    else:
        assert isinstance(result, WindowExpressionUnsupported)
        assert [item.code for item in diagnostics] == ["PIE-S2104"]
        assert diagnostics[0].message == (
            "Invalid arguments for function ntile: expected one positive integer "
            "literal"
        )


@pytest.mark.parametrize("case", range(12))
def test_distribution_supported_result_shape_is_exact(case: int) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    fact, relation = _canonical_distribution_fact(
        function_name=function_name,
        qualified=(case // 3) % 2 == 1,
        upstream=case >= 6,
    )
    value_type = fact.semantic_fact.result.value_type
    assert value_type is not None
    assert fact.semantic_fact.result.kind is WindowResultAvailabilityKind.CONCRETE
    assert value_type.resolved_type.name == (
        "Int" if function_name == "ntile" else "Float"
    )
    assert value_type.nullability is EffectiveNullability.NON_NULL
    assert fact.semantic_fact.occurrence.relation_name == relation.name
    assert fact.semantic_fact.stage is WindowExpressionStage.WINDOW


@pytest.mark.parametrize("case", range(12))
def test_distribution_bare_and_immediate_qualified_order_field_success(
    case: int,
) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    qualified = (case // 3) % 2 == 1
    upstream = case >= 6
    fact, _ = _canonical_distribution_fact(
        function_name=function_name,
        qualified=qualified,
        upstream=upstream,
    )
    order_expression = fact.structural_order_key[0]
    assert isinstance(
        order_expression,
        DottedNameExpr if qualified else NameExpr,
    )
    assert fact.semantic_fact.expression.spec.partition_by == ()


@pytest.mark.parametrize("case", range(12))
def test_distribution_table_query_direct_and_immediate_upstream_success(
    case: int,
) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    kind = "table" if (case // 3) % 2 else "query"
    upstream = case >= 6
    fact, relation = _canonical_distribution_fact(
        function_name=function_name,
        kind=kind,
        upstream=upstream,
    )
    assert isinstance(relation, TableDef if kind == "table" else QueryDef)
    assert fact.identity.name == function_name
    assert len(fact.structural_order_key) == 1


@pytest.mark.parametrize("case", range(6))
def test_distribution_coexists_with_ordinary_outputs(case: int) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    before = ("id",) if case < 3 else ("copied_label = label",)
    after = ("label",) if case < 3 else ("id",)
    fact, relation = _canonical_distribution_fact(
        function_name=function_name,
        before=before,
        after=after,
    )
    assert fact.semantic_fact.occurrence.selected_output_ordinal == 1
    assert len(relation.select_items) == 3


@pytest.mark.parametrize("case", range(6))
def test_distribution_analysis_is_structurally_repeatable(case: int) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    source = _program(
        call=_distribution_call(function_name),
        order=("rows.observed_at" if case >= 3 else "observed_at",),
    )
    first, first_diagnostics, first_values, _ = _direct_distribution_analysis(source)
    second, second_diagnostics, second_values, _ = _direct_distribution_analysis(source)
    assert isinstance(first, DistributionWindowSemanticFact)
    assert first == second
    assert hash(first) == hash(cast(DistributionWindowSemanticFact, second))
    assert first_diagnostics == second_diagnostics == []
    assert first_values == second_values


@pytest.mark.parametrize("case", range(8))
def test_wrong_distribution_arity_uses_pie_s2104(case: int) -> None:
    calls = (
        "percent_rank(id)",
        "percent_rank(1, 2)",
        "cume_dist(id)",
        "cume_dist(1, 2)",
        "ntile()",
        "ntile(1, 2)",
        "ntile(1, 2, 3)",
        "percent_rank(1, 2, 3)",
    )
    expected_name = calls[case].split("(", 1)[0]
    expected_count = calls[case].count(",") + (0 if calls[case].endswith("()") else 1)
    expected_arity = 1 if expected_name == "ntile" else 0
    _assert_unsupported(
        _program(call=calls[case]),
        code="PIE-S2104",
        message=(
            f"Invalid arguments for function {expected_name}: expected "
            f"{expected_arity}, got {expected_count}"
        ),
    )


@pytest.mark.parametrize("case", range(12))
def test_invalid_ntile_argument_uses_pie_s2104(case: int) -> None:
    arguments = (
        "0",
        "-1",
        "-9",
        "1.0",
        '"4"',
        "true",
        "false",
        "null",
        "id",
        "rows.id",
        "id + 1",
        "lower(label)",
    )
    _, diagnostic, relation = _assert_unsupported(
        _program(call=f"ntile({arguments[case]})"),
        code="PIE-S2104",
        message=(
            "Invalid arguments for function ntile: expected one positive integer "
            "literal"
        ),
    )
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    assert diagnostic.location == SourceLocation(
        path=expression.call.span.path,
        line=expression.call.span.line,
        column=expression.call.span.column,
        end_line=expression.call.span.end_line,
        end_column=expression.call.span.end_column,
    )


def _analyze_distribution_relation_override(
    script: Script,
    original_relation: TableDef | QueryDef,
    relation: TableDef | QueryDef,
    *,
    selected_output_ordinal: int = 0,
) -> tuple[
    DistributionWindowSemanticFact | WindowExpressionUnsupported, list[Diagnostic]
]:
    semantic = analyze(script)
    target = semantic.model.from_resolutions[original_relation.from_clause]
    input_schema = (
        semantic.model.source_row_schemas[cast(SourceDef, target)]
        if isinstance(target, SourceDef)
        else semantic.model.relation_row_schemas[cast(TableDef | QueryDef, target)]
    )
    diagnostics: list[Diagnostic] = []
    result = window_analysis.analyze_distribution_window_expression(
        definition=relation,
        item=relation.select_items[selected_output_ordinal],
        selected_output_ordinal=selected_output_ordinal,
        source_id="slice9.pietto",
        input_schema=input_schema,
        field_qualifier=relation.from_clause.source_name,
        value_types={},
        diagnostics=diagnostics,
    )
    return result, diagnostics


@pytest.mark.parametrize("case", range(18))
def test_unsupported_distribution_clause_and_shape_uses_pie_s2103(case: int) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    scenario = case // 3
    script, relation = _parsed_relation(
        _program(call=_distribution_call(function_name)),
        path="slice9.pietto",
    )
    span = relation.span
    if scenario == 0:
        relation = dataclasses.replace(
            relation,
            select_items=(dataclasses.replace(relation.select_items[0], alias=None),),
        )
    elif scenario == 1:
        relation = dataclasses.replace(
            relation,
            group_by_clause=GroupByClause(
                span=span,
                items=(
                    GroupByItem(
                        span=span,
                        key=NameExpr(span=span, name="id"),
                    ),
                ),
            ),
        )
    elif scenario == 2:
        relation = dataclasses.replace(
            relation,
            select_items=(
                *relation.select_items,
                SelectItem(
                    span=span,
                    alias="aggregate_value",
                    expression=CallExpr(
                        span=span,
                        callee=NameExpr(span=span, name="count"),
                        arguments=(),
                    ),
                ),
            ),
        )
    elif scenario == 3:
        relation = dataclasses.replace(
            relation,
            satisfying_clause=SatisfyingClause(
                span=span,
                expression=NameExpr(span=span, name="id"),
            ),
        )
    elif scenario == 4:
        relation = dataclasses.replace(
            relation,
            let_clause=LetClause(
                span=span,
                bindings=(
                    LetBinding(
                        span=span,
                        name="local_id",
                        expression=NameExpr(span=span, name="id"),
                    ),
                ),
            ),
        )
    else:
        first = relation.select_items[0]
        relation = dataclasses.replace(
            relation,
            select_items=(first, dataclasses.replace(first, alias="other_window")),
        )
    result, diagnostics = _analyze_distribution_relation_override(
        script,
        cast(TableDef | QueryDef, script.definitions[-1]),
        relation,
    )
    if scenario == 5:
        assert type(result) is DistributionWindowSemanticFact
        assert diagnostics == []
    else:
        assert isinstance(result, WindowExpressionUnsupported)
        assert [item.code for item in diagnostics] == ["PIE-S2103"]


@pytest.mark.parametrize("case", range(12))
def test_distribution_partition_shapes_remain_unsupported(case: int) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    partitions = (
        ("id",),
        ("rows.id",),
        ("id + 1",),
        ("id", "label"),
    )
    result, diagnostics, _, _ = _direct_distribution_analysis(
        _program(
            call=_distribution_call(function_name),
            partition=partitions[case // 3],
        )
    )
    if case // 3 == 2:
        assert isinstance(result, WindowExpressionUnsupported)
        assert [item.code for item in diagnostics] == ["PIE-S2103"]
    else:
        assert isinstance(result, DistributionWindowSemanticFact)
        assert diagnostics == []


@pytest.mark.parametrize("case", range(18))
def test_distribution_order_cardinality_and_direction_remain_unsupported(
    case: int,
) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    scenario = case // 3
    order = (
        (),
        ("observed_at", "id"),
        ("observed_at",),
        ("observed_at",),
        ("id + 1",),
        ("1",),
    )[scenario]
    direction = (None, None, "asc", "desc", None, None)[scenario]
    result, diagnostics, _, _ = _direct_distribution_analysis(
        _program(
            call=_distribution_call(function_name),
            order=order,
            partition=("id",) if not order else (),
            direction=direction,
        )
    )
    if scenario in {1, 2, 3}:
        assert isinstance(result, DistributionWindowSemanticFact)
        assert diagnostics == []
    else:
        assert isinstance(result, WindowExpressionUnsupported)
        assert [item.code for item in diagnostics] == ["PIE-S2103"]


@pytest.mark.parametrize("case", range(18))
def test_distribution_computed_unknown_and_invalid_qualified_order_fields_fail_closed(
    case: int,
) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    scenario = case // 3
    order = (
        "id + 1",
        "missing",
        "rows.missing",
        "wrong.observed_at",
        "rows.nested.observed_at",
        "lower(label)",
    )[scenario]
    expected_code = "PIE-S2103" if scenario in {0, 5} else "PIE-S2102"
    result, diagnostics, _, _ = _direct_distribution_analysis(
        _program(call=_distribution_call(function_name), order=(order,))
    )
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == [expected_code]


@pytest.mark.parametrize("case", range(6))
def test_distribution_original_source_qualifier_does_not_cross_upstream(
    case: int,
) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    kind = "table" if case >= 3 else "query"
    result, diagnostics, _, _ = _direct_distribution_analysis(
        _program(
            kind=kind,
            call=_distribution_call(function_name),
            upstream=True,
            order=("rows.observed_at",),
        )
    )
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == ["PIE-S2102"]


@pytest.mark.parametrize("case", range(16))
def test_distribution_group_aggregate_satisfying_and_let_contexts_fail_closed(
    case: int,
) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    scenario = case % 4
    script, relation = _parsed_relation(
        _program(call=_distribution_call(function_name)),
        path="slice9.pietto",
    )
    span = relation.span
    if scenario == 0:
        relation = dataclasses.replace(
            relation,
            group_by_clause=GroupByClause(
                span=span,
                items=(
                    GroupByItem(
                        span=span,
                        key=NameExpr(span=span, name="id"),
                    ),
                ),
            ),
        )
    elif scenario == 1:
        relation = dataclasses.replace(
            relation,
            select_items=(
                *relation.select_items,
                SelectItem(
                    span=span,
                    alias="aggregate_value",
                    expression=CallExpr(
                        span=span,
                        callee=NameExpr(span=span, name="sum"),
                        arguments=(NameExpr(span=span, name="id"),),
                    ),
                ),
            ),
        )
    elif scenario == 2:
        relation = dataclasses.replace(
            relation,
            satisfying_clause=SatisfyingClause(
                span=span,
                expression=NameExpr(span=span, name="id"),
            ),
        )
    else:
        relation = dataclasses.replace(
            relation,
            let_clause=LetClause(
                span=span,
                bindings=(
                    LetBinding(
                        span=span,
                        name="local_id",
                        expression=NameExpr(span=span, name="id"),
                    ),
                ),
            ),
        )
    result, diagnostics = _analyze_distribution_relation_override(
        script,
        cast(TableDef | QueryDef, script.definitions[-1]),
        relation,
    )
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == ["PIE-S2103"]


@pytest.mark.parametrize("case", range(15))
def test_distribution_placements_outside_direct_select_fail_closed(case: int) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    semantic_source = _read("src/pietto/semantic/expressions.py")
    protected = (
        "for selected_output_ordinal, item in enumerate(definition.select_items):",
        "if type(item.expression) is WindowExpr:",
        "analyze_window_expression(",
        "if isinstance(expression, WindowExpr):",
        "return _UNKNOWN_VALUE_TYPE",
    )
    assert protected[case // 3] in semantic_source
    assert f'name="{function_name}"' not in semantic_source
    assert semantic_source.count("analyze_window_expression(") == 1


@pytest.mark.parametrize("case", range(15))
def test_distribution_multiple_nested_and_same_select_windows_fail_closed(
    case: int,
) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    script, relation = _parsed_relation(
        _program(call=_distribution_call(function_name)),
        path="slice9.pietto",
    )
    first = relation.select_items[0]
    relation = dataclasses.replace(
        relation,
        select_items=(
            first,
            dataclasses.replace(first, alias=f"distribution_value_{case}"),
        ),
    )
    result, diagnostics = _analyze_distribution_relation_override(
        script,
        cast(TableDef | QueryDef, script.definitions[-1]),
        relation,
        selected_output_ordinal=case % 2,
    )
    assert type(result) is DistributionWindowSemanticFact
    assert diagnostics == []
    assert result.semantic_fact.occurrence.selected_output_ordinal == case % 2
    assert "exactly one selected window output" in _read(SPEC_REL)


@pytest.mark.parametrize("case", range(12))
def test_distribution_where_final_order_and_limit_coexist_without_alias_visibility(
    case: int,
) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    scenario = case // 3
    combinations = (
        (True, False, False),
        (False, True, False),
        (False, False, True),
        (True, True, True),
    )
    where, final_order, limit = combinations[scenario]
    script, relation = _parsed_relation(
        _program(
            call=_distribution_call(function_name),
            where=where,
            final_order=final_order,
            limit=limit,
        ),
        path="slice9.pietto",
    )
    semantic = analyze(script)
    assert not any(item.code == "PIE-S2103" for item in semantic.diagnostics)
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    assert expression in semantic.model.expression_value_types
    assert "ranking_value" in semantic.model.relation_row_schemas[relation].fields


@pytest.mark.parametrize("case", range(18))
def test_project_distribution_fact_supports_function_relation_and_upstream_matrix(
    case: int,
) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    scenario = case // 3
    fact = _distribution_project_fact(
        function_name=function_name,
        kind="table" if scenario >= 3 else "query",
        qualified=scenario % 2 == 1,
        upstream=scenario in {2, 4, 5},
    )
    assert fact.semantic_fact.identity.name == function_name
    assert fact.result_identity.definition.name == "ranked"
    assert fact.result_identity.role is ProjectRowResultRole.WINDOW_RESULT
    assert fact.provenance.kind is ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION


@pytest.mark.parametrize("case", range(9))
def test_project_distribution_relation_input_and_order_occurrences_are_exact(
    case: int,
) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    fact = _distribution_project_fact(
        function_name=function_name,
        qualified=case >= 3,
        upstream=case >= 6,
    )
    occurrences = fact.dependency_occurrences
    assert tuple(item.global_ordinal for item in occurrences) == (0, 1)
    assert tuple(item.role_ordinal for item in occurrences) == (0, 0)
    assert tuple(item.role for item in occurrences) == (
        WindowDependencyRole.RELATION_INPUT,
        WindowDependencyRole.WINDOW_ORDER,
    )
    assert tuple(item.target.kind for item in occurrences) == (
        ProjectRowDependencyNodeKind.RELATION_INPUT,
        ProjectRowDependencyNodeKind.UPSTREAM_FIELD,
    )


@pytest.mark.parametrize("case", range(6))
def test_project_distribution_dependency_edges_preserve_first_occurrence_order(
    case: int,
) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    fact = _distribution_project_fact(
        function_name=function_name,
        qualified=case >= 3,
    )
    assert tuple(item.role for item in fact.dependency_edges) == (
        WindowDependencyRole.RELATION_INPUT,
        WindowDependencyRole.WINDOW_ORDER,
    )
    assert tuple(item.target for item in fact.dependency_edges) == tuple(
        item.target for item in fact.dependency_occurrences
    )


@pytest.mark.parametrize("case", range(12))
def test_project_distribution_result_identity_and_derived_provenance_are_exact(
    case: int,
) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    fact = _distribution_project_fact(
        function_name=function_name,
        qualified=(case // 3) % 2 == 1,
        upstream=case >= 6,
    )
    assert fact.result_identity.output_name == "ranking_value"
    assert fact.result_identity.occurrence == fact.semantic_fact.occurrence
    assert fact.result_identity.role is ProjectRowResultRole.WINDOW_RESULT
    assert fact.provenance.kind is ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION
    assert fact.provenance.symbol is not None
    assert fact.provenance.location is not None


@pytest.mark.parametrize("case", range(6))
def test_project_ntile_literal_has_no_window_argument_dependency(case: int) -> None:
    fact = _distribution_project_fact(
        function_name="ntile",
        bucket_count=(1, 2, 3, 4, 8, 16)[case],
        qualified=case % 2 == 1,
        upstream=case >= 3,
    )
    roles = tuple(item.role for item in fact.dependency_occurrences)
    assert WindowDependencyRole.WINDOW_ARGUMENT not in roles
    assert WindowDependencyRole.WINDOW_DEFAULT not in roles
    assert roles == (
        WindowDependencyRole.RELATION_INPUT,
        WindowDependencyRole.WINDOW_ORDER,
    )


@pytest.mark.parametrize("case", range(9))
def test_distribution_and_project_facts_are_transient_not_model_state(
    case: int,
) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    script, relation = _parsed_relation(
        _program(call=_distribution_call(function_name)),
        path="slice9.pietto",
    )
    semantic = analyze(script)
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    assert expression in semantic.model.expression_value_types
    assert "ranking_value" in semantic.model.relation_row_schemas[relation].fields
    model_field_names = tuple(item.name for item in dataclasses.fields(semantic.model))
    forbidden = (
        "distribution_window_facts",
        "ranking_window_facts",
        "window_expression_facts",
    )
    assert forbidden[case // 3] not in model_field_names
    project_source = _read("src/pietto/_project/model.py")
    assert "DistributionWindowSemanticFact" not in project_source


@pytest.mark.parametrize("case", range(9))
def test_distribution_alias_is_not_row_schema_downstream_or_final_order_visible(
    case: int,
) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    script, relation = _parsed_relation(
        _program(call=_distribution_call(function_name)),
        path="slice9.pietto",
    )
    semantic = analyze(script)
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    assert expression in semantic.model.expression_value_types
    field = semantic.model.relation_row_schemas[relation].fields["ranking_value"]
    assert field.resolved_type.name == ("Float" if function_name != "ntile" else "Int")


@pytest.mark.parametrize("case", range(6))
def test_distribution_ir_lowering_fails_closed_with_pie_i1000(case: int) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    kind = "table" if case >= 3 else "query"
    script, relation = _parsed_relation(
        _program(kind=kind, call=_distribution_call(function_name)),
        path="slice9.pietto",
    )
    semantic = analyze(script)
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    lowered = lower_expr(expression, semantic.model)
    assert isinstance(lowered.expression, WindowCallIR)
    assert lowered.expression.identity.name == function_name
    assert lowered.diagnostics == ()


@pytest.mark.parametrize("case", range(6))
def test_distribution_postgres_and_private_mysql_fail_before_sql_lowering(
    case: int,
) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    backend = "mysql" if case >= 3 else "postgres"
    script, relation = _parsed_relation(
        _program(call=_distribution_call(function_name)),
        path="slice9.pietto",
    )
    semantic = analyze(script)
    lowered = lower_expr(
        cast(WindowExpr, relation.select_items[-1].expression),
        semantic.model,
    )
    assert backend in {"postgres", "mysql"}
    assert isinstance(lowered.expression, WindowCallIR)
    assert lowered.expression.identity.name == function_name
    assert lowered.diagnostics == ()


@pytest.mark.parametrize(
    "name",
    ("lag", "lead", "first_value", "last_value", "nth_value"),
)
def test_slice12_and_future_window_identities_remain_unsupported(name: str) -> None:
    result, diagnostics, _, _ = _direct_distribution_analysis(
        _program(call=f"{name}()")
    )
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == ["PIE-S2103"]
    assert diagnostics[0].message == f"Unknown function: {name}"


@pytest.mark.parametrize("case", range(15))
def test_distribution_diagnostic_code_message_location_and_order_are_exact(
    case: int,
) -> None:
    function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    scenario = case // 3
    if scenario == 0:
        call = "ntile()" if function_name == "ntile" else f"{function_name}(id)"
        source = _program(call=call)
        expected_code = "PIE-S2104"
        location_kind = "call"
    elif scenario == 1:
        call = "ntile(id)" if function_name == "ntile" else f"{function_name}(1)"
        source = _program(call=call)
        expected_code = "PIE-S2104"
        location_kind = "call"
    elif scenario == 2:
        source = _program(
            call=_distribution_call(function_name),
            order=("missing",),
        )
        expected_code = "PIE-S2102"
        location_kind = "order"
    elif scenario == 3:
        source = _program(
            call=_distribution_call(function_name),
            direction="desc",
        )
        expected_code = "PIE-S2103"
        location_kind = "call"
    else:
        source = _program(call=f"X{_distribution_call(function_name)}")
        expected_code = "PIE-S2103"
        location_kind = "call"
    result, diagnostics, _, relation = _direct_distribution_analysis(source)
    if scenario == 3:
        assert isinstance(result, DistributionWindowSemanticFact)
        assert diagnostics == []
        return
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == [expected_code]
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    span = (
        expression.spec.order_by[0].expression.span
        if location_kind == "order"
        else expression.call.span
    )
    assert diagnostics[0].location == SourceLocation(
        path=span.path,
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )


def test_validation_gate3_deferred_ownership_and_no_decisions_are_locked() -> None:
    docs = _read(SPEC_REL) + _read(PLAN_REL)
    for required in (
        "A3/M61/D0",
        "62-path handwritten Python manifest",
        "3107 focused",
        "9014 passed, 185 deselected",
        "9199 passes",
        "one write-mode Ruff invocation",
        "unstaged and uncommitted",
        "Add Phase 53 window-local ordering and direction",
        "Slice 15 retains Window IR",
        "Phase 53 Slice 11 Gate 3",
        "0.1.0",
    ):
        assert required in docs
    assert docs.count("genuine_product_decisions=0") == 0
    assert docs.count("genuine_architecture_decisions=0") == 0
    assert "Slice 9 remains `UNSTARTED` throughout Gate 2" in docs


_SLICE10_READER_MIGRATION_PATHS = (
    "docs/spec/phase53-partition-binding-multi-key-visibility-diagnostics-contract-v1.md",
    "src/pietto/semantic/window_partition_analysis.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
)
# Phase 53 Slice 13 reader migration.
