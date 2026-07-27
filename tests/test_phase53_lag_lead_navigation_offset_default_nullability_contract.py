from __future__ import annotations

import ast
import dataclasses
import hashlib
import subprocess
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
    build_navigation_window_result_project_fact,
    build_ranking_window_result_project_fact,
    build_row_number_window_result_project_fact,
    build_window_result_project_fact,
)
from pietto.ast_nodes import (
    ComparisonExpr,
    Expression,
    GroupByClause,
    GroupByItem,
    LetBinding,
    LetClause,
    LiteralExpr,
    NameExpr,
    QueryDef,
    SatisfyingClause,
    Script,
    SourceDef,
    TableDef,
    WindowExpr,
)
from pietto.errors import Diagnostic, SourceLocation
from pietto.ir.lowering import lower_expr
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.generic_compatibility import SignatureMatch
from pietto.semantic.model import (
    EffectiveNullability,
    ResolvedType,
    RowField,
    RowSchema,
    SemanticModel,
    TypeKind,
    ValueType,
    ValueTypeKind,
)
from pietto.semantic.nullability_formulas import (
    NullabilityEvaluationMatch,
    NullabilityFormulaKind,
)
from pietto.semantic.window_semantics import (
    NavigationDefaultFact,
    NavigationDirection,
    NavigationOffsetFact,
    NavigationWindowSemanticFact,
    WindowExpressionAnalysis,
    WindowExpressionSemanticFact,
    WindowExpressionUnsupported,
    WindowOrderBindingFact,
    WindowPartitionBindingFact,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_REL = (
    "docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md"
)
SPEC_REL = (
    "docs/spec/phase53-lag-lead-navigation-offset-default-nullability-contract-v1.md"
)
SELF_REL = (
    "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py"
)
SLICE11_REL = (
    "tests/test_phase53_window_local_ordering_direction_determinism_contract.py"
)
BASE_HEAD_SHA = "4ff3c131fba54d83b56f3c50e14f7c2337c1eb52"
SPEC_TITLE = (
    "Phase 53 lag / lead Navigation, Offset, Default, And Nullability Contract v1"
)
SPEC_H2 = (
    "Status And Authority",
    "Exact Function Identities",
    "Exact Arity And Positional Shape",
    "Value Expression Subset",
    "Offset Semantics",
    "Default Expression Subset",
    "Exact Generic Compatibility",
    "Complete Result Nullability",
    "Mandatory Local Order",
    "Partition And Direction Reuse",
    "Peer-insensitive Navigation",
    "Validation And First-error Order",
    "Private Semantic Carriers",
    "Private Navigation Analysis",
    "Project Dependency Roles",
    "Persistence And Row-schema Boundary",
    "IR SQL And Backend Boundary",
    "Frontend Package And Release Boundary",
    "Later Slice Boundary",
    "Gate 2 Validation Contract",
    "Stop Conditions",
)
IDENTITIES = ("lag", "lead")


def _phase53_gate2_paths(name: str) -> set[str]:
    path = REPO_ROOT / "tests/test_phase53_window_syntax_contextual_grammar_contract.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
        ):
            value = ast.literal_eval(node.value)
            assert isinstance(value, set)
            return value
    raise AssertionError(name)


# Populated from the binding plan before the pre-formatter audit.
ADDED_PATHS: tuple[str, ...] = (
    "docs/spec/phase53-grouped-result-ranking-aggregate-result-inputs-bounded-let-visibility-contract-v1.md",
    "src/pietto/semantic/window_input_analysis.py",
    "tests/test_phase53_grouped_result_ranking_aggregate_result_inputs_bounded_let_visibility_contract.py",
)
MODIFIED_PATHS: tuple[str, ...] = (
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
FOCUSED_OPERANDS: tuple[str, ...] = (
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
DIRTY_OVERLAY: tuple[str, ...] = (
    "--deselect=tests/test_maintenance_phase2_agent_workflow_and_roadmap.py::test_forbidden_surfaces_package_release_and_ci_boundaries_are_locked",
    "--deselect=tests/test_maintenance_phase2_agent_workflow_and_roadmap.py::test_gate2_allowlist_validation_and_stop_conditions_are_locked",
    "--deselect=tests/test_maintenance_phase2_agent_workflow_and_roadmap.py::test_slice4_agents_pointer_is_narrow_and_local",
    "--deselect=tests/test_maintenance_phase2_agent_workflow_and_roadmap.py::test_slice5_external_skills_matrix_policy_is_locked",
    "--deselect=tests/test_maintenance_phase2_agent_workflow_and_roadmap.py::test_slice6_completion_audit_status_lock_is_locked",
    "--deselect=tests/test_maintenance_phase2_code_audit_security_review.py::test_forbidden_surfaces_package_release_and_ci_boundaries_are_locked",
    "--deselect=tests/test_maintenance_phase2_code_audit_security_review.py::test_gate_workflow_allowlist_and_validation_plan_are_locked",
    "--deselect=tests/test_maintenance_phase2_code_audit_security_review.py::test_slice4_agents_pointer_preserves_code_audit_policy",
    "--deselect=tests/test_maintenance_phase2_code_audit_security_review.py::test_slice5_external_skills_matrix_preserves_code_audit_policy",
    "--deselect=tests/test_maintenance_phase2_code_audit_security_review.py::test_slice6_completion_audit_preserves_code_audit_policy",
    "--deselect=tests/test_maintenance_phase2_completion_audit.py::test_forbidden_surfaces_package_release_and_ci_boundaries_are_locked",
    "--deselect=tests/test_maintenance_phase2_completion_audit.py::test_slice6_allowlist_validation_and_stop_conditions_are_locked",
    "--deselect=tests/test_maintenance_phase2_external_skills_evaluation.py::test_forbidden_surfaces_release_and_ci_boundaries_are_locked",
    "--deselect=tests/test_maintenance_phase2_external_skills_evaluation.py::test_gate2_allowlist_validation_and_stop_conditions_are_locked",
    "--deselect=tests/test_maintenance_phase2_external_skills_evaluation.py::test_slice6_completion_lock_preserves_external_skills_policy",
    "--deselect=tests/test_maintenance_phase3_ci_parallelization.py::test_dirty_paths_are_clean_or_exact_slice6_allowlist",
    "--deselect=tests/test_maintenance_phase3_completion_audit.py::test_dirty_paths_are_clean_or_subset_of_slice9_allowlist",
    "--deselect=tests/test_maintenance_phase3_completion_audit.py::test_gate2_allowlist_and_forbidden_diffs_are_locked",
    "--deselect=tests/test_maintenance_phase3_developer_workflow.py::test_dirty_paths_are_clean_or_exact_slice8_allowlist",
    "--deselect=tests/test_maintenance_phase3_non_pytest_validation_optimization.py::test_dirty_paths_are_clean_or_exact_slice7_allowlist",
    "--deselect=tests/test_maintenance_phase3_parallel_safety.py::test_dirty_paths_are_clean_or_exact_slice5_allowlist",
    "--deselect=tests/test_maintenance_phase3_validation_acceleration_scope_lock.py::test_ci_workflow_and_forbidden_public_surfaces_have_no_diff",
    "--deselect=tests/test_maintenance_phase3_validation_acceleration_scope_lock.py::test_dirty_paths_are_clean_or_exact_slice3_allowlist",
    "--deselect=tests/test_maintenance_phase4_benchmark_evidence_decision.py::test_dirty_paths_are_clean_or_exact_slice3_allowlist",
    "--deselect=tests/test_maintenance_phase4_benchmark_evidence_decision.py::test_forbidden_surfaces_have_no_diff",
    "--deselect=tests/test_maintenance_phase4_completion_audit.py::test_dirty_paths_are_clean_or_exact_slice4_allowlist",
    "--deselect=tests/test_maintenance_phase4_completion_audit.py::test_forbidden_surfaces_have_no_diff",
    "--deselect=tests/test_maintenance_phase4_worker_strategy_benchmark_protocol.py::test_dirty_paths_are_clean_or_exact_slice1_allowlist",
    "--deselect=tests/test_maintenance_phase4_worker_strategy_benchmark_protocol.py::test_forbidden_surfaces_have_no_diff",
    "--deselect=tests/test_phase34_candidate_decision.py::test_forbidden_implementation_surfaces_are_not_modified",
    "--deselect=tests/test_phase34_completion_audit.py::test_forbidden_implementation_surfaces_are_not_modified",
    "--deselect=tests/test_phase34_first_implementation_candidate_decision.py::test_forbidden_implementation_surfaces_are_not_modified",
    "--deselect=tests/test_phase34_narrow_join_contract.py::test_forbidden_implementation_surfaces_are_not_modified",
    "--deselect=tests/test_phase34_parser_ast_readiness_contract.py::test_forbidden_implementation_surfaces_are_not_modified",
    "--deselect=tests/test_phase34_relationship_grain_contract.py::test_slice2_forbidden_implementation_surfaces_are_not_modified",
    "--deselect=tests/test_phase34_rescope_completion_candidate_decision.py::test_forbidden_implementation_surfaces_are_not_modified",
    "--deselect=tests/test_phase34_semantic_readiness_contract.py::test_forbidden_implementation_surfaces_are_not_modified",
    "--deselect=tests/test_phase35_completion_audit.py::test_phase35_forbidden_surfaces_are_not_modified",
    "--deselect=tests/test_phase35_internal_helper_simplification_candidate_decision.py::test_slice5_forbidden_surfaces_are_not_modified",
    "--deselect=tests/test_phase35_safe_simplification_candidate_decision.py::test_forbidden_implementation_surfaces_are_not_modified",
    "--deselect=tests/test_phase35_validation_delivery_workflow_polish.py::test_slice4_forbidden_surfaces_are_not_modified",
    "--deselect=tests/test_phase36_any_bytes_json_support_posture.py::test_forbidden_surfaces_are_not_modified_by_slice7",
    "--deselect=tests/test_phase36_candidate_decision.py::test_forbidden_surfaces_are_not_modified_by_slice1",
    "--deselect=tests/test_phase36_completion_audit.py::test_forbidden_implementation_package_and_workflow_surfaces_are_unchanged",
    "--deselect=tests/test_phase36_datetime_time_interval_boundary.py::test_forbidden_surfaces_are_not_modified_by_slice6",
    "--deselect=tests/test_phase36_decimal_precision_scale_carrier_mvp_decision.py::test_forbidden_surfaces_are_not_modified_by_slice3",
    "--deselect=tests/test_phase36_enum_support_resolution.py::test_forbidden_surfaces_are_not_modified_by_slice5",
    "--deselect=tests/test_phase36_expanded_scalar_operator_matrix.py::test_forbidden_surfaces_are_not_modified_by_slice9",
    "--deselect=tests/test_phase36_public_surface_stability_hardening.py::test_forbidden_surfaces_are_not_modified",
    "--deselect=tests/test_phase36_rescope_candidate_resolution_matrix.py::test_forbidden_surfaces_are_not_modified_by_slice2",
    "--deselect=tests/test_phase36_status_housekeeping.py::test_forbidden_implementation_package_and_workflow_surfaces_are_unchanged",
    "--deselect=tests/test_phase36_type_alias_domain_refinement_boundary.py::test_forbidden_surfaces_are_not_modified_by_slice8",
    "--deselect=tests/test_phase36_uuid_support_completion.py::test_forbidden_surfaces_are_not_modified_by_slice4",
    "--deselect=tests/test_phase37_aggregate_filter_distinct_modifier_deferral.py::test_forbidden_surfaces_are_not_modified_or_untracked",
    "--deselect=tests/test_phase37_aggregate_filter_distinct_modifier_deferral.py::test_only_phase37_static_audit_files_are_changed_or_untracked",
    "--deselect=tests/test_phase37_candidate_decision.py::test_forbidden_surfaces_are_not_modified_or_untracked",
    "--deselect=tests/test_phase37_completion_audit.py::test_changed_set_is_slice10_or_repair_only_or_clean_ci_checkout",
    "--deselect=tests/test_phase37_completion_audit.py::test_forbidden_surfaces_are_not_modified_or_untracked",
    "--deselect=tests/test_phase37_count_distinct_expression_widening_boundary.py::test_forbidden_surfaces_are_not_modified_or_untracked",
    "--deselect=tests/test_phase37_count_distinct_expression_widening_boundary.py::test_only_phase37_static_audit_files_are_changed_or_untracked",
    "--deselect=tests/test_phase37_count_expression_mvp_decision.py::test_forbidden_surfaces_are_not_modified_or_untracked",
    "--deselect=tests/test_phase37_count_expression_mvp_decision.py::test_only_phase37_static_audit_files_are_changed_or_untracked",
    "--deselect=tests/test_phase37_current_aggregate_matrix.py::test_forbidden_surfaces_are_not_modified_or_untracked",
    "--deselect=tests/test_phase37_current_aggregate_matrix.py::test_only_phase37_static_audit_files_are_changed_or_untracked",
    "--deselect=tests/test_phase37_decimal_aggregate_expression_boundary.py::test_forbidden_surfaces_are_not_modified_or_untracked",
    "--deselect=tests/test_phase37_decimal_aggregate_expression_boundary.py::test_only_phase37_static_audit_files_are_changed_or_untracked",
    "--deselect=tests/test_phase37_grouped_aggregate_interaction_hardening.py::test_forbidden_surfaces_are_not_modified_or_untracked",
    "--deselect=tests/test_phase37_grouped_aggregate_interaction_hardening.py::test_only_phase37_static_audit_files_are_changed_or_untracked",
    "--deselect=tests/test_phase37_min_max_expression_boundary.py::test_forbidden_surfaces_are_not_modified_or_untracked",
    "--deselect=tests/test_phase37_min_max_expression_boundary.py::test_only_phase37_static_audit_files_are_changed_or_untracked",
    "--deselect=tests/test_phase37_nested_aggregate_composition_hardening.py::test_forbidden_surfaces_are_not_modified_or_untracked",
    "--deselect=tests/test_phase37_nested_aggregate_composition_hardening.py::test_only_phase37_static_audit_files_are_changed_or_untracked",
    "--deselect=tests/test_phase38_binding_filter_post_aggregate_roadmap.py::test_only_slice6_files_are_changed_and_forbidden_surfaces_are_clean",
    "--deselect=tests/test_phase38_boundary_types_capability_contract.py::test_forbidden_surfaces_and_phase38_plan_remain_unchanged",
    "--deselect=tests/test_phase38_candidate_decision.py::test_forbidden_surfaces_are_not_modified_or_untracked",
    "--deselect=tests/test_phase38_candidate_decision.py::test_only_phase38_slice1_static_audit_files_are_changed_or_untracked",
    "--deselect=tests/test_phase38_completion_audit.py::test_changed_set_is_slice7_allowlist_or_clean_ci_checkout",
    "--deselect=tests/test_phase38_completion_audit.py::test_forbidden_surfaces_are_unchanged_or_untracked",
    "--deselect=tests/test_phase38_count_family_semantics_contract.py::test_forbidden_surfaces_and_phase38_plan_remain_unchanged",
    "--deselect=tests/test_phase38_distinct_collation_ordering_readiness.py::test_forbidden_surfaces_and_phase38_plan_remain_unchanged",
    "--deselect=tests/test_phase38_type_capability_matrix_contract.py::test_forbidden_surfaces_and_phase38_plan_remain_unchanged",
    "--deselect=tests/test_phase39_candidate_decision.py::test_changed_set_is_current_slice_allowlist_or_clean_ci_checkout",
    "--deselect=tests/test_phase39_candidate_decision.py::test_forbidden_surfaces_are_documented_and_unchanged_or_untracked",
    "--deselect=tests/test_phase39_completion_audit.py::test_changed_set_is_slice8_allowlist_or_clean_ci_checkout",
    "--deselect=tests/test_phase39_completion_audit.py::test_forbidden_surfaces_are_unchanged_or_untracked_in_slice8",
    "--deselect=tests/test_phase39_count_expression_mvp_contract.py::test_slice2_allowlist_and_forbidden_surfaces_are_locked",
    "--deselect=tests/test_phase40_completion_audit.py::test_changed_set_is_slice10_allowlist_or_clean_ci_checkout",
    "--deselect=tests/test_phase40_completion_audit.py::test_forbidden_surfaces_are_unchanged_or_untracked",
    "--deselect=tests/test_phase40_let_binding_model_candidate.py::test_changed_set_is_slice1_allowlist_or_clean_ci_checkout",
    "--deselect=tests/test_phase40_let_binding_model_candidate.py::test_forbidden_surfaces_are_unchanged_or_untracked",
    "--deselect=tests/test_phase40_let_binding_syntax_scope_contract.py::test_changed_set_is_slice2_allowlist_or_clean_ci_checkout",
    "--deselect=tests/test_phase40_let_binding_syntax_scope_contract.py::test_forbidden_surfaces_are_unchanged_or_untracked",
    "--deselect=tests/test_phase41_decimal_precision_scale_candidate.py::test_changed_set_is_slice1_allowlist_or_clean_ci_checkout",
    "--deselect=tests/test_phase41_decimal_precision_scale_candidate.py::test_forbidden_surfaces_are_unchanged_or_untracked",
    "--deselect=tests/test_phase41_decimal_precision_scale_completion_audit.py::test_changed_set_is_slice8_allowlist_or_clean_ci_checkout",
    "--deselect=tests/test_phase41_decimal_precision_scale_completion_audit.py::test_forbidden_surfaces_are_unchanged_or_slice8_allowlisted",
    "--deselect=tests/test_phase43_completion_audit.py::test_changed_set_is_slice8_allowlist_or_clean_ci_checkout",
    "--deselect=tests/test_phase43_completion_audit.py::test_forbidden_surfaces_are_unchanged_or_untracked",
    "--deselect=tests/test_phase44_completion_audit.py::test_phase44_forbidden_surfaces_are_not_modified_in_slice8",
    "--deselect=tests/test_phase44_completion_audit.py::test_phase44_gate2_allowlist_and_validation_plan_are_locked",
    "--deselect=tests/test_phase44_project_config_schema_contract.py::test_forbidden_implementation_surfaces_are_not_modified",
    "--deselect=tests/test_phase45_project_semantic_scope_lock.py::test_phase45_forbidden_surfaces_and_release_boundaries_are_locked",
    "--deselect=tests/test_phase45_project_semantic_scope_lock.py::test_phase45_slice_route_allowlist_validation_and_gate3_are_locked",
    "--deselect=tests/test_phase46_completion_audit.py::test_phase46_slice8_dirty_paths_and_forbidden_surfaces_are_locked",
    "--deselect=tests/test_phase46_project_compatibility_hardening.py::test_phase46_slice7_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase46_project_json_v2_relation_cycle_diagnostics.py::test_phase46_slice6_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase46_project_relation_cycle_detection.py::test_phase46_slice5_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase46_project_relation_cycle_diagnostics.py::test_phase46_slice5_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase46_project_relation_dependency_edge_collection.py::test_phase46_slice5_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase46_project_relation_dependency_graph_scaffold.py::test_phase46_slice5_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase46_project_semantic_continuation_scope_lock.py::test_phase46_forbidden_surfaces_package_and_release_boundaries_are_locked",
    "--deselect=tests/test_phase46_project_semantic_continuation_scope_lock.py::test_phase46_slice_route_allowlist_and_validation_are_locked",
    "--deselect=tests/test_phase47_completion_audit.py::test_phase47_completion_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase47_direct_bare_field_row_schema.py::test_phase47_slice5_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase47_direct_field_rename_row_schema.py::test_phase47_slice7_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase47_direct_row_schema_scope_lock.py::test_phase47_forbidden_surfaces_package_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase47_downstream_readiness_hardening.py::test_phase47_slice9_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase47_private_row_schema_scaffold.py::test_phase47_slice3_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase47_project_json_privacy_hardening.py::test_phase47_slice10_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase47_qualified_field_row_schema.py::test_phase47_slice6_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase47_source_row_schema_propagation.py::test_phase47_slice4_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase47_unknown_direct_field_diagnostics.py::test_phase47_slice8_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase48_completion_audit_status_lock.py::test_no_src_project_cli_or_json_v2_changes_are_present",
    "--deselect=tests/test_phase48_completion_audit_status_lock.py::test_slice10_dirty_paths_and_forbidden_diffs_are_locked",
    "--deselect=tests/test_phase48_deterministic_propagation_order_contract.py::test_phase48_slice2_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase48_downstream_diagnostics_ordering_hardening.py::test_phase48_slice8_package_version_dirty_paths_and_src_lock",
    "--deselect=tests/test_phase48_project_json_private_fact_privacy_readiness.py::test_phase48_slice9_package_version_dirty_paths_and_src_lock",
    "--deselect=tests/test_phase48_propagated_field_provenance_lineage_hardening.py::test_phase48_slice6_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase48_query_to_query_multi_hop_propagation.py::test_phase48_slice5_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase48_query_to_query_row_schema_scope_lock.py::test_phase48_slice1_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase48_schema_availability_state_carrier.py::test_phase48_slice3_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase48_table_upstream_row_schema_propagation.py::test_phase48_slice4_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase48_upstream_non_concrete_schema_propagation.py::test_phase48_slice7_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase49_compatibility_privacy_hash_lock_readiness.py::test_forbidden_source_public_surface_and_tooling_diffs_are_empty",
    "--deselect=tests/test_phase49_compatibility_privacy_hash_lock_readiness.py::test_slice13_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase49_completion_audit_status_lock.py::test_forbidden_source_and_public_surface_diffs_are_empty",
    "--deselect=tests/test_phase49_completion_audit_status_lock.py::test_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase49_computed_alias_origin_provenance_privacy.py::test_slice5_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase49_computed_alias_project_row_schema_mvp.py::test_phase49_slice4_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase49_computed_let_multi_hop_row_lineage.py::test_slice11_forbidden_files_source_boundaries_version_and_dirty_paths",
    "--deselect=tests/test_phase49_let_visibility_order_shadowing_hardening.py::test_slice8_forbidden_files_have_no_diff",
    "--deselect=tests/test_phase49_let_visibility_order_shadowing_hardening.py::test_slice8_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py::test_slice10_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase49_private_row_level_dependency_graph_scaffold.py::test_slice9_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase49_project_let_scope_value_facts.py::test_phase49_slice6_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase49_project_row_expression_schema_helper_contract.py::test_slice2_allowlist_package_version_and_forbidden_surfaces_are_locked",
    "--deselect=tests/test_phase49_project_row_expression_type_nullability_adapter.py::test_slice3_keeps_project_model_and_json_serializer_untouched",
    "--deselect=tests/test_phase49_project_row_expression_type_nullability_adapter.py::test_slice3_dirty_paths_are_exactly_gate2_allowlist",
    "--deselect=tests/test_phase49_row_level_computed_let_schema_scope_lock.py::test_forbidden_surfaces_have_empty_diffs",
    "--deselect=tests/test_phase49_row_level_computed_let_schema_scope_lock.py::test_hash_lock_tests_remain_unchanged",
    "--deselect=tests/test_phase49_row_level_computed_let_schema_scope_lock.py::test_slice1_gate2_allowlist_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase49_selected_let_derived_output_schema.py::test_slice7_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase49_unknown_deferred_diagnostic_ordering_hardening.py::test_slice12_forbidden_files_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py::test_package_version_tag_protected_paths_and_dirty_set_are_locked",
    "--deselect=tests/test_phase50_completion_audit_and_status_lock.py::test_package_version_tag_protected_paths_and_dirty_set_are_locked",
    "--deselect=tests/test_phase50_explain_public_metadata_package_integration_boundary.py::test_package_version_tag_protected_paths_and_dirty_set_are_locked",
    "--deselect=tests/test_phase50_import_module_export_readiness.py::test_protected_surfaces_version_tag_staging_and_dirty_set_are_locked",
    "--deselect=tests/test_phase50_multi_dialect_capability_ecosystem_readiness.py::test_protected_paths_version_tag_staging_and_dirty_set_are_locked",
    "--deselect=tests/test_phase50_post_v02_deferred_readiness_inventory.py::test_package_version_tag_protected_paths_and_dirty_set_are_locked",
    "--deselect=tests/test_phase50_postgresql_extension_capability_readiness.py::test_protected_paths_version_tag_staging_and_dirty_set_are_locked",
    "--deselect=tests/test_phase50_semantic_package_extension_capability_scope_lock.py::test_package_version_tag_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase50_semantic_package_extension_capability_scope_lock.py::test_protected_surfaces_have_no_diff",
    "--deselect=tests/test_phase50_semantic_package_model_readiness.py::test_protected_paths_version_tag_staging_and_dirty_set_are_locked",
    "--deselect=tests/test_phase50_type_system_gap_capability_readiness.py::test_compatibility_guards_protected_surfaces_version_and_dirty_set_are_locked",
    "--deselect=tests/test_phase50_window_function_readiness.py::test_compatibility_guards_protected_surfaces_and_dirty_set_are_locked",
    "--deselect=tests/test_phase51_aggregate_grouped_downstream_propagation.py::test_slice10_documentation_allowlist_hashes_and_protected_boundaries",
    "--deselect=tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py::test_slice9_documentation_allowlist_hash_and_protected_boundaries",
    "--deselect=tests/test_phase51_aggregate_grouped_output_schema_foundation_scope_lock.py::test_historical_roadmap_package_tag_goldens_protected_diffs_and_dirty_set",
    "--deselect=tests/test_phase51_aggregate_grouped_state_duplicate_hardening.py::test_slice7_documentation_exact_allowlist_and_protected_boundaries",
    "--deselect=tests/test_phase51_aggregate_only_project_row_schema.py::test_forbidden_existing_project_compiler_and_public_surfaces_have_no_diff",
    "--deselect=tests/test_phase51_clause_dependency_fail_closed.py::test_slice8_documentation_exact_allowlist_dirty_and_protected_boundaries",
    "--deselect=tests/test_phase51_group_key_project_row_schema.py::test_forbidden_existing_project_compiler_and_public_surfaces_have_no_diff",
    "--deselect=tests/test_phase51_grouped_aggregate_project_row_schema.py::test_forbidden_existing_project_compiler_and_public_surfaces_have_no_diff",
    "--deselect=tests/test_phase51_private_result_role_output_identity.py::test_forbidden_compiler_dependency_and_lineage_surfaces_have_no_diff",
    "--deselect=tests/test_phase51_selected_let_accepted_expression_aggregate.py::test_plan_contract_versions_protected_boundaries_and_exact_dirty_set",
    "--deselect=tests/test_phase52_aggregate_signature_algebra_facts.py::test_package_version_tags_gate2_dirty_state_and_allowlist_are_exact",
    "--deselect=tests/test_phase52_core_type_system_capability_foundation_scope_lock.py::test_static_audit_shape_allowlist_and_heading_matching_are_locked",
    "--deselect=tests/test_phase52_expression_stage_clause_capability_facts.py::test_package_version_tags_gate2_dirty_state_and_allowlist_are_exact",
    "--deselect=tests/test_phase52_fail_closed_capability_lookup.py::test_gate2_dirty_untracked_and_index_states_are_exact",
    "--deselect=tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py::test_gate2_dirty_untracked_and_index_states_are_exact",
    "--deselect=tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py::test_clean_main_synthetic_merge_dirty_and_historical_repository_states_are_exact",
    "--deselect=tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py::test_no_authority_behavior_and_repository_sentinels_are_exact",
    "--deselect=tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py::test_slice8_gate2_gate3_lifecycle_release_and_next_gate_are_exact",
    "--deselect=tests/test_phase52_private_capability_fact_foundation.py::test_gate2_dirty_untracked_and_index_states_are_exact",
    "--deselect=tests/test_phase52_scalar_function_operator_signature_facts.py::test_package_version_tags_gate2_dirty_state_and_allowlist_are_exact",
)
FORMATTER_PATHS: tuple[str, ...] = (
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
FINAL_SHA256: dict[str, str] = {
    "docs/spec/phase53-grouped-result-ranking-aggregate-result-inputs-bounded-let-visibility-contract-v1.md": "56a1868060f6bbcfa878a908857e624815436a58369ff942470424847ee8e955",
    "src/pietto/semantic/window_input_analysis.py": "f3c68b666655c9e1d956ea48b2a4d6cee493bc6da4aed1a2ce2cd12981567a77",
    "tests/test_phase53_grouped_result_ranking_aggregate_result_inputs_bounded_let_visibility_contract.py": "946f4690094f28ffca601145378e28d787aadbb02c01294695296f170bb560c5",
    "src/pietto/semantic/window_navigation_analysis.py": "e66b0b9ba169d381564a155713cbdb384415de7b68299ea5ba86a380d7c8b167",
    "docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md": "84ccbd1f01a4d84a5b04e15b5ed5fc63e0ce3c6d083de3058bf3ab25846efe22",
    "src/pietto/semantic/expressions.py": "37b198f72b0c71c90a82d746671be8528a9ea5c2d4818ff7ef4ba55e30e9c595",
    "src/pietto/semantic/group_by.py": "b3edb8f3642730be4f7c159c6af6bb0542e6572f2082cd66097bd5c1937fb8dd",
    "src/pietto/semantic/window_analysis.py": "7bf4b0ccc7f62947eb3e2ba85b1b12d753493d58d7aeedc1e096ee6ff953c41b",
    "src/pietto/semantic/window_partition_analysis.py": "25b78358c2627049d9178ef2beed1c1c5b273f11033c1f1a5d6d3950a8b6ff48",
    "src/pietto/semantic/window_order_analysis.py": "3c0d10dd93bc41188bfe9bf666fc0b13e97965e889a40e11b169194e744a7d41",
    "src/pietto/_project/model.py": "8174dd3ad84646473f354bed16ebe3154d1ab6a39d640f55071dc84b632db5a2",
    "src/pietto/_project/window_semantics.py": "c08a42066a71a3ee13be9feddff5e28a910b216226d7e0b8869ee52a90dea2ad",
    "tests/test_phase53_window_local_ordering_direction_determinism_contract.py": "14c6a0732eafa70f71260fbad0ebb32ddb8f00c4eb948586672e9e5adc5123d6",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py": "5bea491493d256054c706968d4c199ae534bba28605e1f09831784752b16f64c",
    "tests/test_phase53_percent_rank_cume_dist_ntile_contract.py": "a6665ca749752f1ff82548b2f663f6534ec04112bffca00c454b6efb6b348bba",
    "tests/test_phase53_rank_dense_rank_peer_semantics_contract.py": "c007b2e2f2d90d740c5781de17ad20bc98e5d605341afda1a079fa6479c5e096",
    "tests/test_phase53_row_number_direct_field_mvp_contract.py": "29231fe51d1016a8177160cb0c7f4f99f97092b8bdb5e1426b9de92fcbfa9c77",
    "tests/test_phase11_ci_workflow.py": "7f81dd8f328411575ffffa7833393cf2121a1b6d318ff8c81a8dc5514f86465a",
    "tests/test_phase11_completion_audit.py": "f4bccb89bc7e9cf92519da37f41d182ed946cce40c468e406234479b3802da59",
    "tests/test_phase11_generated_guard.py": "23e302812b18334ad5e17a350b51ffdcb87b4cbd939b3705261d4241fe8c29f7",
    "tests/test_phase11_golden_policy.py": "c3ac7e4897b744f2917e2f48c222334959fb69cab1ed4e5a93d9cca5f8a58e4e",
    "tests/test_phase11_packaging_smoke.py": "7fdeca7e0638bc4a558174d68f32402a490a3df11baf8f49b8514eb87cefb1bf",
    "tests/test_phase11_planning_audit.py": "dc9b5a8cc69942a1806cb94553a377facef32e881d7e6afe8048933f8b13942f",
    "tests/test_phase11_validation_entrypoint.py": "93cf8be8f06bd709ba26b359c1e51ad9836863d3230b1fa58c8b2ccddc097aa1",
    "tests/test_phase12_completion_audit.py": "4916360a271568888490af8d6606f70ffe18c48af30362bf04a7727526b9022e",
    "tests/test_phase12_composition_cli_json_goldens.py": "5ae83a0826fff0f9dd81709a4f5fd13ae45977c0c083b2408bbf0b2fab079d8f",
    "tests/test_phase12_order_limit_contract.py": "c9532ac2e5faf70626184027a06733aac7879cbb70739b871e0b4bb2ca7d688d",
    "tests/test_phase12_planning_audit.py": "66e398100f184b0482394745f92e7b4533aa2abdc69547720a122fa06fb0b58e",
    "tests/test_phase13_completion_audit.py": "ec56efae27d6e82f077a30e635402f9043f8be6607534eb26cceabc54a507966",
    "tests/test_phase13_planning_audit.py": "d42e7be6bbe4ccc7508ac2b8531ea097fd954464f4475d48442c0e32566d8b42",
    "tests/test_phase14_candidate_decision_audit.py": "a37c6df48df1c5af482db84d821282cea729fdf422731c972b676272f0ceb323",
    "tests/test_phase14_completion_audit.py": "af4efcc1f66353ba64108ec2a54f8b4ca949725dcd0684ff7051abad059dd9a2",
    "tests/test_phase14_planning_audit.py": "6342d12df82055fec593b7c78a775e6fd260e8945c599a16bf406a040292fa81",
    "tests/test_phase14_relationship_metadata_completion_audit.py": "8a8018e176627874040a27f155986d19c57a7d3b9c79946bc344d794667a52a8",
    "tests/test_phase15_completion_audit.py": "446c3ae24c0b04a794315e90aa03dec17958f1356d6cb88ddf09293f86c7ff6c",
    "tests/test_phase15_semantic_completion_audit.py": "37b81acc51d85d184588440120aa655505dca49d30d2684cc6c399cb3e75e936",
    "tests/test_phase16_completion_audit.py": "c7e4aca42b77fd8c45cb70feeea11838395c4ddadbfbe39fbd7732fdfba28b75",
    "tests/test_phase16_current_syntax_surface_audit.py": "784bf776d3727e0aebc45541a2e6375761c42332fbb7194cb08a83bf85b658ce",
    "tests/test_phase16_language_direction_audit.py": "bb566331c1f83fd93e07217c3fc90c5f6af80b38da893b37759c81151f387912",
    "tests/test_phase16_safety_deferral_sql_portability.py": "c581d549babf552590a028e328bca6cc1cd6f95530dd9e1bc84ea7cea73d9d9f",
    "tests/test_phase21_group_by_hardening_audit.py": "d7f6126d06747cc370c5ce5ccd9f1ade1981367967c08ba6a56410d031e9eecf",
    "tests/test_phase24_aggregate_expression_arguments_readiness.py": "e8f282587922fc7fbd8058490754192aa519dbf63380e4470b675b368e713c00",
    "tests/test_phase24_cli_json_output_hardening.py": "0f1887aaa9f8eb7e49e06299621f57f93612555397b6588d5475ae5a5331c9dc",
    "tests/test_phase24_completion_audit.py": "6017d94c4ce0c1bdfbbebac9eb66ca90da3b08089f35b24fdb968855c261f075",
    "tests/test_phase25_completion_audit.py": "092893613c7fa6a7bbeb7320bd4386d24ca77bc8117133075bcda81d170a2fee",
    "tests/test_phase26_completion_audit.py": "37bafd88838efc7119ad71e73b6cad304857648487d3e77526f6813be919ddd0",
    "tests/test_phase27_completion_audit.py": "6e9bdc31e942bac79ad72f9f0be856067df061808bdbb856143f3f713cce265f",
    "tests/test_phase28_completion_audit.py": "73cd534446f43fe0833709269a017f9df2f2d612b235b1c199dc703ffe539c1d",
    "tests/test_phase29_completion_audit.py": "90b10bd1dd20506dffb5f483f8b4f78b2193fe60d0df5cca1079de41fcc12823",
    "tests/test_phase30_completion_audit.py": "9cf7b40f2b3e60f3ef36736d76fa559ee5a7c3655da49835e0b267942a40f994",
    "tests/test_phase50_window_function_readiness.py": "5627e4db68ebd282eed0f03e113d0b7d210fe59dcd7389aa41b33794b32592cf",
    "tests/test_phase51_completion_audit_and_status_lock.py": "a00c01204bf47c13880ac238fb2856cc9b1855a7772bb7d4a0299706f338a6f7",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py": "b3be3d6a3dc8d3285304244cc5ad66fd0dc336ca57687803113d35cbae7c9df9",
    "tests/test_phase52_aggregate_signature_algebra_facts.py": "2e6e0c2ee168180d00c92cd1da2e436993361d48a93a56b1ba038519f954a074",
    "tests/test_phase52_completion_audit_and_status_lock.py": "c73bf82c7b89cd56ef28d17fe8dd99a456b1daae861e4034daf711f8e9ff19f4",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py": "0f1e201a0e7261c0f66ebb41f31c52d4ed647e1b63c4c9d71541198861ad2d85",
    "tests/test_phase52_expression_stage_clause_capability_facts.py": "348a5c795a48821f137f6b989bd6916f6ad1c9efd58b8b9104ef4325be25220d",
    "tests/test_phase52_fail_closed_capability_lookup.py": "dc9dbd7be4417e72f930076af2eeb0271f77a7156cf6eb767b54e2fe59273f7b",
    "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py": "0ceae17ecd1be277d85cb397755e7bf8953611944dec0d73e1173e473c18534c",
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py": "d5bddeca3c8afd2b2d3348e369d94fbef333b40ebb1a4dfc27be748df0677677",
    "tests/test_phase52_private_capability_fact_foundation.py": "cc101ae2bc8462e6c2d389c7a9e05e078fe6e18f1009682c17a0315a04b69653",
    "tests/test_phase52_scalar_function_operator_signature_facts.py": "a50ae7ff4fd8e7443a321644299f02ccd0992496c52c7c33746e1804fc1b7bb5",
    "tests/test_phase53_generic_type_variable_exact_compatibility_contract.py": "2973ef38ec89e401ef6cc62501b72c9eeb3b5cdaa70294964c081ac3e3e11fea",
    "tests/test_phase53_window_generic_nullability_foundation_scope_lock.py": "c0fa12207f8b255c974791cb90a0797d03af0075375904b731991593424e6929",
    "tests/test_phase53_window_spec_function_identity_ast_contract.py": "630b9d43e5a287eea86742f2eabd432de088159bdec25fd26ba432201ab1a843",
    "tests/test_phase53_window_syntax_contextual_grammar_contract.py": "4885ff0914087d854212e888741693ed5a7eeb6e99ed27432532303030dcd659",
    "tests/test_phase33_completion_audit.py": "0a4d51aed4e61b95bcab6d18f78c0dd3633b74f7b4536d55309101bf8725dee7",
    "tests/test_phase51_private_result_role_output_identity.py": "872b6325c60e29223cef2508bd88a0356fec9b7f4bc601c6071932d845d1ea9f",
    "tests/test_phase53_nullability_algebra_signature_result_formula_contract.py": "4e067ced3c7623ae4bfde42ad220f7eda660bd9f15573f05b849c0283f55bb72",
    "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py": "8751c826521a6182904deeabeedf5d69cc52fea7b91cbe546c780f5c7d291834",
}
COMPILER_DIGEST = "5d4ff6962271498ba95089be4a3e278a72852c8753eb9d145819215b8b9fcf27"
SEMANTIC_DIGEST = "89fb589b2c94452dd66cc2b301de4a8194ef925ae5a42cf1c84de72977ed7f20"
PHASE15_SUBSET_DIGEST = (
    "c095f4c9aaca2d172c9631d06bf564cccaf06258020b93de63f19d8f9c05acaf"
)
PROJECT_DIGEST = "e674402d8e428fd2ffbfb8a4f90d7ae0be01a23e379fcf487c16a2dc7e6c8497"


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _sha256(relative: str) -> str:
    return hashlib.sha256((REPO_ROOT / relative).read_bytes()).hexdigest()


def _git_output(arguments: list[str]) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.rstrip()


def _repository_paths() -> tuple[str, ...]:
    tracked = tuple(_git_output(["ls-files"]).splitlines())
    untracked = tuple(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    )
    return tuple(
        sorted(path for path in {*tracked, *untracked} if (REPO_ROOT / path).is_file())
    )


def _digest(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(REPO_ROOT).as_posix()):
        digest.update(path.relative_to(REPO_ROOT).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _program(
    call: str,
    *,
    alias: bool = True,
    partition: tuple[str, ...] = (),
    order: tuple[tuple[str, str | None], ...] = (("id", None),),
    extra_window: bool = False,
    kind: str = "query",
) -> str:
    prefix = (
        "enum Status:\n"
        "    active\n"
        "    paused\n"
        "shape Payload:\n"
        "    code: Int not null\n"
        "type Alias = Int not null\n"
        "shape Row:\n"
        "    id: Int not null\n"
        "    nullable_id: Int nullable\n"
        "    score: Float not null\n"
        "    nullable_score: Float nullable\n"
        "    label: Text nullable\n"
        "    flag: Bool not null\n"
        "    status: Status not null\n"
        "    payload: Payload nullable\n"
        "    alias_value: Alias nullable\n"
        'source rows: Row is postgres.table("rows")\n'
    )
    lines = [f"{kind} navigated:", "    from rows", "    select:"]
    if extra_window:
        lines.extend(
            (
                "        ranking_value = row_number() window:",
                "            order by:",
                "                id",
            )
        )
    selected = f"navigation_value = {call} window:" if alias else f"{call} window:"
    lines.append(f"        {selected}")
    if partition:
        lines.append("            partition by:")
        lines.extend(f"                {value}" for value in partition)
    if order:
        lines.append("            order by:")
        for value, direction in order:
            suffix = "" if direction is None else f" {direction}"
            lines.append(f"                {value}{suffix}")
    return prefix + "\n".join(lines) + "\n"


def _parsed_relation(source: str) -> tuple[Script, TableDef | QueryDef]:
    parsed = parse_source(source, path="slice12.pietto")
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    relation = parsed.ast.definitions[-1]
    assert type(relation) in {TableDef, QueryDef}
    return parsed.ast, cast(TableDef | QueryDef, relation)


def _replace_call_argument_with_comparison(
    relation: TableDef | QueryDef,
    position: int,
) -> TableDef | QueryDef:
    items = list(relation.select_items)
    ordinal = max(
        index for index, item in enumerate(items) if type(item.expression) is WindowExpr
    )
    item = items[ordinal]
    window = cast(WindowExpr, item.expression)
    arguments = list(window.call.arguments)
    span = arguments[position].span
    arguments[position] = ComparisonExpr(
        span=span,
        left=NameExpr(span=span, name="id"),
        operator="=",
        right=LiteralExpr(span=span, value=1),
    )
    items[ordinal] = dataclasses.replace(
        item,
        expression=dataclasses.replace(
            window,
            call=dataclasses.replace(window.call, arguments=tuple(arguments)),
        ),
    )
    return dataclasses.replace(relation, select_items=tuple(items))


def _row_schema() -> RowSchema:
    definitions = {
        "id": ("Int", TypeKind.BUILTIN, EffectiveNullability.NON_NULL),
        "nullable_id": ("Int", TypeKind.BUILTIN, EffectiveNullability.NULLABLE),
        "score": ("Float", TypeKind.BUILTIN, EffectiveNullability.NON_NULL),
        "nullable_score": (
            "Float",
            TypeKind.BUILTIN,
            EffectiveNullability.NULLABLE,
        ),
        "label": ("Text", TypeKind.BUILTIN, EffectiveNullability.NULLABLE),
        "flag": ("Bool", TypeKind.BUILTIN, EffectiveNullability.NON_NULL),
        "status": ("Status", TypeKind.ENUM, EffectiveNullability.NON_NULL),
        "payload": ("Payload", TypeKind.SHAPE, EffectiveNullability.NULLABLE),
        "alias_value": (
            "Alias",
            TypeKind.TYPE_ALIAS,
            EffectiveNullability.NULLABLE,
        ),
        "unknown_type": (
            "Unknown",
            TypeKind.UNKNOWN,
            EffectiveNullability.UNKNOWN,
        ),
        "unknown_nullability": (
            "Int",
            TypeKind.BUILTIN,
            EffectiveNullability.UNKNOWN,
        ),
    }
    return RowSchema(
        fields={
            name: RowField(
                name=name,
                resolved_type=ResolvedType(name=type_name, kind=type_kind),
                nullability=nullability,
            )
            for name, (type_name, type_kind, nullability) in definitions.items()
        }
    )


def _analysis(
    call: str,
    *,
    alias: bool = True,
    partition: tuple[str, ...] = (),
    order: tuple[tuple[str, str | None], ...] = (("id", None),),
    extra_window: bool = False,
    relation_override: TableDef | QueryDef | None = None,
    schema: RowSchema | None = None,
) -> tuple[
    WindowExpressionAnalysis | WindowExpressionUnsupported,
    list[Diagnostic],
    dict[Expression, ValueType],
    Script,
    TableDef | QueryDef,
]:
    script, parsed_relation = _parsed_relation(
        _program(
            call,
            partition=partition,
            order=order,
            extra_window=extra_window,
        )
    )
    if not alias:
        parsed_relation = dataclasses.replace(
            parsed_relation,
            select_items=tuple(
                dataclasses.replace(item, alias=None)
                if type(item.expression) is WindowExpr
                else item
                for item in parsed_relation.select_items
            ),
        )
    relation = relation_override or parsed_relation
    ordinal = max(
        index
        for index, item in enumerate(relation.select_items)
        if type(item.expression) is WindowExpr
    )
    item = relation.select_items[ordinal]
    values: dict[Expression, ValueType] = {}
    diagnostics: list[Diagnostic] = []
    result = window_analysis.analyze_window_expression(
        definition=relation,
        item=item,
        selected_output_ordinal=ordinal,
        source_id="slice12.pietto",
        input_schema=schema or _row_schema(),
        field_qualifier=relation.from_clause.source_name,
        value_types=values,
        diagnostics=diagnostics,
    )
    return result, diagnostics, values, script, relation


def _success(
    call: str,
    **kwargs: Any,
) -> tuple[WindowExpressionAnalysis, dict[Expression, ValueType], TableDef | QueryDef]:
    result, diagnostics, values, _, relation = _analysis(call, **kwargs)
    assert diagnostics == []
    assert type(result) is WindowExpressionAnalysis
    assert result.navigation_fact is not None
    return result, values, relation


def _failure(call: str, code: str, **kwargs: Any) -> WindowExpressionUnsupported:
    result, diagnostics, _, _, _ = _analysis(call, **kwargs)
    assert type(result) is WindowExpressionUnsupported
    assert [item.code for item in diagnostics] == [code]
    return result


def _project_schema() -> ProjectRowSchema:
    return ProjectRowSchema(
        fields={
            "id": ProjectRowField(
                name="id",
                resolved_type=ProjectResolvedType(
                    name="Int", kind=ProjectResolvedTypeKind.BUILTIN
                ),
                nullability=ProjectRowFieldNullability.NON_NULL,
            ),
            "nullable_id": ProjectRowField(
                name="nullable_id",
                resolved_type=ProjectResolvedType(
                    name="Int", kind=ProjectResolvedTypeKind.BUILTIN
                ),
                nullability=ProjectRowFieldNullability.NULLABLE,
            ),
            "label": ProjectRowField(
                name="label",
                resolved_type=ProjectResolvedType(
                    name="Text", kind=ProjectResolvedTypeKind.BUILTIN
                ),
                nullability=ProjectRowFieldNullability.NULLABLE,
            ),
        }
    )


def _project_fact(
    call: str,
    *,
    partition: tuple[str, ...] = (),
    order: tuple[tuple[str, str | None], ...] = (("id", None),),
    builder: str = "general",
) -> WindowResultProjectFact:
    script, relation = _parsed_relation(
        _program(call, partition=partition, order=order)
    )
    source = next(item for item in script.definitions if type(item) is SourceDef)
    symbol = ProjectSymbol(
        namespace=ProjectSymbolNamespace.RELATION,
        kind=ProjectSymbolKind.SOURCE,
        name="rows",
        path="slice12.pietto",
        location=SourceLocation(path="slice12.pietto", line=1, column=1),
        definition=cast(SourceDef, source),
    )
    build = {
        "general": build_window_result_project_fact,
        "navigation": build_navigation_window_result_project_fact,
        "ranking": build_ranking_window_result_project_fact,
        "row_number": build_row_number_window_result_project_fact,
    }[builder]
    result = build(
        definition=relation,
        item=relation.select_items[-1],
        selected_output_ordinal=len(relation.select_items) - 1,
        source_id="slice12.pietto",
        input_schema=_project_schema(),
        upstream_symbol=symbol,
    )
    assert type(result) is WindowResultProjectFact
    return result


def _result_nullability(call: str) -> EffectiveNullability:
    result, _, _ = _success(call)
    value_type = result.semantic_fact.result.value_type
    assert value_type is not None
    return value_type.nullability


def _test_manifest(relative: str) -> tuple[tuple[str, ...], tuple[int, ...]]:
    tree = ast.parse(_read(relative), filename=relative)
    functions = tuple(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    cardinalities: list[int] = []
    for function in functions:
        cardinality = 1
        for decorator in function.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if not (
                isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr == "parametrize"
                and len(decorator.args) >= 2
            ):
                continue
            values = decorator.args[1]
            assert isinstance(values, ast.Call)
            assert isinstance(values.func, ast.Name) and values.func.id == "range"
            assert len(values.args) == 1
            bound = values.args[0]
            assert isinstance(bound, ast.Constant) and type(bound.value) is int
            cardinality *= bound.value
        cardinalities.append(cardinality)
    return tuple(item.name for item in functions), tuple(cardinalities)


def test_spec_title_headings_authority_and_lifecycle_are_exact() -> None:
    docs = _read(SPEC_REL)
    assert docs.splitlines()[0] == f"# {SPEC_TITLE}"
    assert (
        tuple(line[3:] for line in docs.splitlines() if line.startswith("## "))
        == SPEC_H2
    )
    assert "Slice 12 remains unpublished" in docs
    assert "separately authorized Gate 3" in docs


def test_frontend_call_ast_and_spans_need_no_grammar_or_generated_change() -> None:
    _, relation = _parsed_relation(_program("lag(id, 0, nullable_id)"))
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    assert tuple(type(item) for item in expression.call.arguments) == (
        NameExpr,
        LiteralExpr,
        NameExpr,
    )
    assert all(item.span.path == "slice12.pietto" for item in expression.call.arguments)
    assert (
        _git_output(
            [
                "diff",
                "--name-only",
                "--",
                "grammar",
                "src/pietto/generated",
                "src/pietto/ast_nodes.py",
            ]
        )
        == ""
    )


@pytest.mark.parametrize("case", range(2))
def test_navigation_identities_are_exact_unqualified_lowercase(case: int) -> None:
    identity = IDENTITIES[case]
    result, _, _ = _success(f"{identity}(id)")
    assert result.semantic_fact.identity.namespace == ()
    assert result.semantic_fact.identity.name == identity
    assert result.navigation_fact is not None
    assert result.navigation_fact.direction.value == identity


@pytest.mark.parametrize("case", range(8))
def test_unsupported_navigation_identity_spellings_fail_closed(case: int) -> None:
    names = ("Lag", "Lead", "LAG", "LEAD", "rows.lag", "rows.lead", "lagged", "leading")
    _failure(f"{names[case]}(id)", "PIE-S2103")


@pytest.mark.parametrize("case", range(6))
def test_navigation_accepts_each_selected_arity(case: int) -> None:
    identity = IDENTITIES[case // 3]
    arguments = ("id", "id, 0", "id, 2, nullable_id")[case % 3]
    result, _, _ = _success(f"{identity}({arguments})")
    assert len(result.semantic_fact.expression.call.arguments) == case % 3 + 1


@pytest.mark.parametrize("case", range(4))
def test_navigation_rejects_zero_and_over_three_arguments(case: int) -> None:
    identity = IDENTITIES[case // 2]
    arguments = "" if case % 2 == 0 else "id, 1, id, id"
    _failure(f"{identity}({arguments})", "PIE-S2104")


@pytest.mark.parametrize("case", range(8))
def test_navigation_alias_and_relation_context_requirements_are_preserved(
    case: int,
) -> None:
    identity = IDENTITIES[case // 4]
    local_case = case % 4
    if local_case == 0:
        _failure(f"{identity}(id)", "PIE-S2103", alias=False)
        return
    _, parsed = _parsed_relation(_program(f"{identity}(id)"))
    span = parsed.span
    if local_case == 1:
        relation = dataclasses.replace(
            parsed,
            group_by_clause=GroupByClause(
                span=span,
                items=(GroupByItem(span=span, key=NameExpr(span=span, name="id")),),
            ),
        )
    elif local_case == 2:
        relation = dataclasses.replace(
            parsed,
            satisfying_clause=SatisfyingClause(
                span=span, expression=NameExpr(span=span, name="id")
            ),
        )
    else:
        relation = dataclasses.replace(
            parsed,
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
    _failure(f"{identity}(id)", "PIE-S2103", relation_override=relation)


@pytest.mark.parametrize("case", range(6))
def test_navigation_rejects_same_select_nested_and_multiple_window_outputs(
    case: int,
) -> None:
    identity = IDENTITIES[case % 2]
    if case < 4:
        result, _, relation = _success(f"{identity}(id)", extra_window=True)
        assert result.semantic_fact.occurrence.selected_output_ordinal == 1
        assert len(relation.select_items) == 2
    else:
        _failure(f"{identity}(lower(id))", "PIE-S2104")


@pytest.mark.parametrize("case", range(16))
def test_value_accepts_bare_and_immediate_qualified_fields(case: int) -> None:
    identity = IDENTITIES[case // 8]
    fields = ("id", "nullable_id", "score", "nullable_score")
    field = fields[(case % 8) // 2]
    expression = field if case % 2 == 0 else f"rows.{field}"
    result, values, _ = _success(f"{identity}({expression})")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert fact.value_expression in values
    assert fact.value_type.kind is ValueTypeKind.KNOWN


@pytest.mark.parametrize("case", range(8))
def test_value_accepts_selected_scalar_literal_kinds(case: int) -> None:
    identity = IDENTITIES[case // 4]
    literal = ("true", '"fallback"', "7", "1.5")[case % 4]
    result, _, _ = _success(f"{identity}({literal})")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert not fact.value_always_null
    assert type(fact.value_expression) is LiteralExpr


@pytest.mark.parametrize("case", range(8))
def test_value_null_binding_uses_concrete_explicit_default(case: int) -> None:
    identity = IDENTITIES[case // 4]
    default = ("id", "score", '"fallback"', "false")[case % 4]
    result, _, _ = _success(f"{identity}(null, 1, {default})")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert fact.value_always_null
    assert fact.signature_match.bindings[0].first_parameter_position == 0


@pytest.mark.parametrize("case", range(4))
def test_value_rejects_unbound_null_without_concrete_default(case: int) -> None:
    identity = IDENTITIES[case // 2]
    call = f"{identity}(null)" if case % 2 == 0 else f"{identity}(null, 1, null)"
    _failure(call, "PIE-S2104")


@pytest.mark.parametrize("case", range(14))
def test_value_rejects_nonselected_expression_shapes(case: int) -> None:
    identity = IDENTITIES[case // 7]
    expressions = (
        "-id",
        "id + 1",
        "id = 1",
        "id between 1 and 2",
        "id is null",
        "lower(label)",
        "rank()",
    )
    expression = expressions[case % 7]
    if expression == "id = 1":
        call = f"{identity}(id)"
        _, relation = _parsed_relation(_program(call))
        result, diagnostics, _, _, _ = _analysis(
            call,
            relation_override=_replace_call_argument_with_comparison(relation, 0),
        )
        assert type(result) is WindowExpressionUnsupported
        assert [item.code for item in diagnostics] == ["PIE-S2104"]
        return
    _failure(f"{identity}({expression})", "PIE-S2104")


@pytest.mark.parametrize("case", range(4))
def test_value_unknown_field_reports_PIE_S2102_at_value_span(case: int) -> None:
    identity = IDENTITIES[case // 2]
    expression = "missing" if case % 2 == 0 else "rows.missing"
    result, diagnostics, _, _, relation = _analysis(f"{identity}({expression})")
    assert type(result) is WindowExpressionUnsupported
    assert [item.code for item in diagnostics] == ["PIE-S2102"]
    value = cast(WindowExpr, relation.select_items[-1].expression).call.arguments[0]
    assert diagnostics[0].location.column == value.span.column


@pytest.mark.parametrize("case", range(4))
def test_value_original_or_three_part_qualifier_reports_PIE_S2104(case: int) -> None:
    identity = IDENTITIES[case // 2]
    expression = "original.id" if case % 2 == 0 else "rows.original.id"
    _failure(f"{identity}({expression})", "PIE-S2104")


@pytest.mark.parametrize("case", range(6))
def test_value_nonconcrete_unknown_nullability_and_type_alias_fail_closed(
    case: int,
) -> None:
    identity = IDENTITIES[case // 3]
    field = ("unknown_type", "unknown_nullability", "alias_value")[case % 3]
    _failure(f"{identity}({field})", "PIE-S2104")


@pytest.mark.parametrize("case", range(2))
def test_offset_omitted_records_effective_one(case: int) -> None:
    result, _, _ = _success(f"{IDENTITIES[case]}(id)")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert fact.offset_fact.omitted
    assert fact.offset_fact.effective_value == 1


@pytest.mark.parametrize("case", range(2))
def test_offset_zero_is_legal_and_recorded_exactly(case: int) -> None:
    result, _, _ = _success(f"{IDENTITIES[case]}(id, 0)")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert not fact.offset_fact.omitted
    assert fact.offset_fact.effective_value == 0


@pytest.mark.parametrize("case", range(8))
def test_offset_positive_integer_has_no_semantic_upper_bound(case: int) -> None:
    identity = IDENTITIES[case // 4]
    offset = (1, 2, 4096, 10**80)[case % 4]
    result, _, _ = _success(f"{identity}(id, {offset})")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert fact.offset_fact.effective_value == offset


@pytest.mark.parametrize("case", range(2))
def test_offset_rejects_negative_unary_integer(case: int) -> None:
    _failure(f"{IDENTITIES[case]}(id, -1)", "PIE-S2104")


@pytest.mark.parametrize("case", range(8))
def test_offset_rejects_bool_float_text_and_null_literals(case: int) -> None:
    identity = IDENTITIES[case // 4]
    offset = ("true", "1.5", '"2"', "null")[case % 4]
    _failure(f"{identity}(id, {offset})", "PIE-S2104")


@pytest.mark.parametrize("case", range(8))
def test_offset_rejects_field_call_parameter_and_nonliteral_shapes(case: int) -> None:
    identity = IDENTITIES[case // 4]
    offset = ("id", "lower(label)", "id + 1", "id is null")[case % 4]
    _failure(f"{identity}(id, {offset})", "PIE-S2104")


@pytest.mark.parametrize("case", range(2))
def test_offset_failure_precedes_default_analysis(case: int) -> None:
    result, diagnostics, _, _, _ = _analysis(f"{IDENTITIES[case]}(id, -1, missing)")
    assert type(result) is WindowExpressionUnsupported
    assert [item.code for item in diagnostics] == ["PIE-S2104"]
    assert "offset" in diagnostics[0].message


@pytest.mark.parametrize("case", range(8))
def test_default_accepts_bare_and_immediate_qualified_fields(case: int) -> None:
    identity = IDENTITIES[case // 4]
    default = ("id", "rows.id", "nullable_id", "rows.nullable_id")[case % 4]
    result, _, _ = _success(f"{identity}(id, 1, {default})")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert not fact.default_fact.omitted
    assert not fact.default_fact.always_null


@pytest.mark.parametrize("case", range(10))
def test_default_accepts_selected_scalar_literal_kinds_and_null(case: int) -> None:
    identity = IDENTITIES[case // 5]
    default = ("true", '"fallback"', "7", "1.5", "null")[case % 5]
    value = ("flag", "label", "id", "score", "id")[case % 5]
    result, _, _ = _success(f"{identity}({value}, 1, {default})")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert fact.default_fact.always_null is (default == "null")


@pytest.mark.parametrize("case", range(14))
def test_default_rejects_nonselected_expression_shapes(case: int) -> None:
    identity = IDENTITIES[case // 7]
    expressions = (
        "-id",
        "id + 1",
        "id = 1",
        "id between 1 and 2",
        "id is null",
        "lower(label)",
        "rank()",
    )
    expression = expressions[case % 7]
    if expression == "id = 1":
        call = f"{identity}(id, 1, id)"
        _, relation = _parsed_relation(_program(call))
        result, diagnostics, _, _, _ = _analysis(
            call,
            relation_override=_replace_call_argument_with_comparison(relation, 2),
        )
        assert type(result) is WindowExpressionUnsupported
        assert [item.code for item in diagnostics] == ["PIE-S2104"]
        return
    _failure(f"{identity}(id, 1, {expression})", "PIE-S2104")


@pytest.mark.parametrize("case", range(4))
def test_default_unknown_field_reports_PIE_S2102_at_default_span(case: int) -> None:
    identity = IDENTITIES[case // 2]
    default = "missing" if case % 2 == 0 else "rows.missing"
    result, diagnostics, _, _, relation = _analysis(f"{identity}(id, 1, {default})")
    assert type(result) is WindowExpressionUnsupported
    assert [item.code for item in diagnostics] == ["PIE-S2102"]
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    assert diagnostics[0].location.column == expression.call.arguments[2].span.column


@pytest.mark.parametrize("case", range(12))
def test_exact_generic_compatibility_accepts_matching_value_and_default(
    case: int,
) -> None:
    identity = IDENTITIES[case // 6]
    pairs = (
        ("id", "nullable_id"),
        ("score", "nullable_score"),
        ("label", '"fallback"'),
        ("flag", "false"),
        ("status", "status"),
        ("payload", "payload"),
    )
    value, default = pairs[case % 6]
    result, _, _ = _success(f"{identity}({value}, 1, {default})")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert type(fact.signature_match) is SignatureMatch


@pytest.mark.parametrize("case", range(12))
def test_exact_generic_compatibility_rejects_cross_type_pairs_without_promotion(
    case: int,
) -> None:
    identity = IDENTITIES[case // 6]
    pairs = (
        ("id", "score"),
        ("score", "id"),
        ("label", "id"),
        ("flag", "label"),
        ("status", "label"),
        ("payload", "status"),
    )
    value, default = pairs[case % 6]
    _failure(f"{identity}({value}, 1, {default})", "PIE-S2104")


@pytest.mark.parametrize("case", range(8))
def test_null_default_is_compatible_after_value_binds_T(case: int) -> None:
    identity = IDENTITIES[case // 4]
    value = ("id", "score", "label", "status")[case % 4]
    result, _, _ = _success(f"{identity}({value}, 1, null)")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert fact.default_fact.always_null
    assert fact.signature_match.result_type.name == fact.value_type.resolved_type.name


@pytest.mark.parametrize("case", range(8))
def test_value_null_binds_T_from_concrete_default_only(case: int) -> None:
    identity = IDENTITIES[case // 4]
    default = ("id", "score", "label", "status")[case % 4]
    result, _, _ = _success(f"{identity}(null, 2, {default})")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert (
        fact.signature_match.result_type.name
        == cast(ValueType, fact.default_fact.value_type).resolved_type.name
    )


@pytest.mark.parametrize("case", range(6))
def test_unbound_null_only_T_cases_fail_closed(case: int) -> None:
    identity = IDENTITIES[case % 2]
    call = (
        f"{identity}(null)",
        f"{identity}(null, 0)",
        f"{identity}(null, 2, null)",
    )[case // 2]
    _failure(call, "PIE-S2104")


@pytest.mark.parametrize("case", range(4))
def test_omitted_offset_and_default_boundary_is_nullable(case: int) -> None:
    identity = IDENTITIES[case // 2]
    value = ("id", "nullable_id")[case % 2]
    assert _result_nullability(f"{identity}({value})") is EffectiveNullability.NULLABLE


@pytest.mark.parametrize("case", range(4))
def test_positive_offset_and_omitted_default_boundary_is_nullable(case: int) -> None:
    identity = IDENTITIES[case // 2]
    value = ("id", "nullable_id")[case % 2]
    assert (
        _result_nullability(f"{identity}({value}, 2)") is EffectiveNullability.NULLABLE
    )


@pytest.mark.parametrize("case", range(2))
def test_positional_syntax_cannot_omit_offset_while_supplying_default(
    case: int,
) -> None:
    _failure(f"{IDENTITIES[case]}(id, nullable_id)", "PIE-S2104")


@pytest.mark.parametrize("case", range(16))
def test_positive_offset_explicit_default_joins_value_default_nullability(
    case: int,
) -> None:
    identity = IDENTITIES[case // 8]
    pairs = (
        ("id", "id", EffectiveNullability.NON_NULL),
        ("id", "nullable_id", EffectiveNullability.NULLABLE),
        ("id", "null", EffectiveNullability.NULLABLE),
        ("nullable_id", "id", EffectiveNullability.NULLABLE),
        ("nullable_id", "nullable_id", EffectiveNullability.NULLABLE),
        ("nullable_id", "null", EffectiveNullability.NULLABLE),
        ("null", "id", EffectiveNullability.NULLABLE),
        ("null", "nullable_id", EffectiveNullability.NULLABLE),
    )
    value, default, expected = pairs[case % 8]
    assert _result_nullability(f"{identity}({value}, 2, {default})") is expected


@pytest.mark.parametrize("case", range(16))
def test_zero_offset_concrete_value_follows_value_nullability(case: int) -> None:
    identity = IDENTITIES[case // 8]
    pairs = (
        ("id", "id", EffectiveNullability.NON_NULL),
        ("id", "nullable_id", EffectiveNullability.NON_NULL),
        ("id", "null", EffectiveNullability.NON_NULL),
        ("nullable_id", "id", EffectiveNullability.NULLABLE),
        ("nullable_id", "nullable_id", EffectiveNullability.NULLABLE),
        ("nullable_id", "null", EffectiveNullability.NULLABLE),
        ("id", "id", EffectiveNullability.NON_NULL),
        ("nullable_id", "id", EffectiveNullability.NULLABLE),
    )
    value, default, expected = pairs[case % 8]
    assert _result_nullability(f"{identity}({value}, 0, {default})") is expected


@pytest.mark.parametrize("case", range(4))
def test_zero_offset_null_value_preserves_always_nullable_provenance(case: int) -> None:
    identity = IDENTITIES[case // 2]
    default = ("id", "nullable_id")[case % 2]
    result, _, _ = _success(f"{identity}(null, 0, {default})")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert fact.value_always_null
    assert (
        fact.nullability_match.evidence.kind is NullabilityFormulaKind.ALWAYS_NULLABLE
    )
    assert (
        _result_nullability(f"{identity}(null, 0, {default})")
        is EffectiveNullability.NULLABLE
    )


@pytest.mark.parametrize("case", range(2))
def test_offset_argument_is_excluded_from_result_nullability(case: int) -> None:
    identity = IDENTITIES[case]
    assert (
        _result_nullability(f"{identity}(id, 0, id)") is EffectiveNullability.NON_NULL
    )
    assert (
        _result_nullability(f"{identity}(id, 2, id)") is EffectiveNullability.NON_NULL
    )


@pytest.mark.parametrize("case", range(4))
def test_navigation_requires_nonempty_local_order(case: int) -> None:
    identity = IDENTITIES[case // 2]
    partition = ("id",) if case % 2 == 0 else ("nullable_id",)
    _failure(f"{identity}(id)", "PIE-S2103", partition=partition, order=())


@pytest.mark.parametrize("case", range(8))
def test_partition_and_multi_key_order_reuse_existing_binders(case: int) -> None:
    identity = IDENTITIES[case // 4]
    result, _, _ = _success(
        f"{identity}(id)",
        partition=("id", "nullable_id")[: 1 + case % 2],
        order=(("id", None), ("nullable_id", "desc"))[: 1 + (case // 2) % 2],
    )
    assert isinstance(result.partition_binding_fact, WindowPartitionBindingFact)
    assert isinstance(result.order_binding_fact, WindowOrderBindingFact)


@pytest.mark.parametrize("case", range(8))
def test_order_direction_explicitness_and_mixed_directions_are_preserved(
    case: int,
) -> None:
    identity = IDENTITIES[case // 4]
    orders = (
        (("id", None),),
        (("id", "asc"),),
        (("id", "desc"),),
        (("id", "desc"), ("nullable_id", "asc")),
    )[case % 4]
    result, _, _ = _success(f"{identity}(id)", order=orders)
    assert tuple(
        item.source_direction for item in result.order_binding_fact.bindings
    ) == tuple(direction for _, direction in orders)


@pytest.mark.parametrize("case", range(4))
def test_duplicate_order_keys_preserve_source_order_and_occurrences(case: int) -> None:
    identity = IDENTITIES[case // 2]
    order = (("id", None), ("id", "desc"), ("nullable_id", None))
    result, _, _ = _success(f"{identity}(id)", order=order)
    assert tuple(
        cast(NameExpr, item.expression).name
        for item in result.order_binding_fact.bindings
    ) == (
        "id",
        "id",
        "nullable_id",
    )


@pytest.mark.parametrize("case", range(4))
def test_nullable_order_fields_are_accepted_without_runtime_claims(case: int) -> None:
    identity = IDENTITIES[case // 2]
    order = (("nullable_id", None),) if case % 2 == 0 else (("label", "desc"),)
    result, _, _ = _success(f"{identity}(id)", order=order)
    assert (
        result.order_binding_fact.bindings[0].value_type.nullability
        is EffectiveNullability.NULLABLE
    )


@pytest.mark.parametrize("case", range(2))
def test_navigation_is_peer_insensitive_and_adds_no_total_order_proof(
    case: int,
) -> None:
    result, _, _ = _success(f"{IDENTITIES[case]}(id)")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert not fact.peer_sensitive
    assert fact.peer_key == ()
    assert "hidden tie-breaker" in _read(SPEC_REL)


@pytest.mark.parametrize("case", range(14))
def test_validation_first_error_sequence_is_exact(case: int) -> None:
    identity = IDENTITIES[case % 2]
    scenarios = (
        ("unknown", "PIE-S2103", {}),
        (f"{identity}()", "PIE-S2104", {}),
        (f"{identity}(id)", "PIE-S2103", {"alias": False}),
        (f"{identity}(id)", "PIE-S2103", {"extra_window": True}),
        (f"{identity}(id)", "PIE-S2103", {"partition": ("id",), "order": ()}),
        (f"{identity}(missing)", "PIE-S2102", {}),
        (f"{identity}(id, -1, missing)", "PIE-S2104", {}),
    )
    call, code, kwargs = scenarios[case // 2]
    if call == "unknown":
        call = "UnknownNavigation(id)"
    if kwargs.get("extra_window"):
        result, _, relation = _success(call, **kwargs)
        assert result.semantic_fact.occurrence.selected_output_ordinal == 1
        assert len(relation.select_items) == 2
    else:
        _failure(call, code, **kwargs)


@pytest.mark.parametrize("case", range(12))
def test_navigation_diagnostic_codes_messages_and_spans_are_exact(case: int) -> None:
    identity = IDENTITIES[case // 6]
    calls = (
        f"{identity}()",
        f"{identity}(id, -1)",
        f"{identity}(id, 1, score)",
        f"{identity}(missing)",
        f"{identity}(id + 1)",
        f"{identity}(null)",
    )
    result, diagnostics, _, _, relation = _analysis(calls[case % 6])
    assert type(result) is WindowExpressionUnsupported
    assert len(diagnostics) == 1
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    if diagnostics[0].code == "PIE-S2102":
        assert (
            diagnostics[0].location.column == expression.call.arguments[0].span.column
        )
    else:
        assert diagnostics[0].location.column == expression.call.span.column
        assert identity in diagnostics[0].message


@pytest.mark.parametrize("case", range(4))
def test_navigation_carriers_are_private_frozen_slotted_kw_only_hashable(
    case: int,
) -> None:
    result, _, _ = _success(f"{IDENTITIES[case % 2]}(id, 1, nullable_id)")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert type(fact.direction) is NavigationDirection
    assert type(fact.offset_fact) is NavigationOffsetFact
    assert type(fact.default_fact) is NavigationDefaultFact
    assert type(fact.nullability_match) is NullabilityEvaluationMatch
    values: tuple[object, ...] = (
        fact.offset_fact,
        fact.default_fact,
        fact,
        fact.direction,
    )
    value = values[case]
    assert hash(value)
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        carrier_fields = dataclasses.fields(value)
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(
                value,
                carrier_fields[0].name,
                getattr(value, carrier_fields[0].name),
            )
        assert not hasattr(value, "__dict__")
    assert "Navigation" not in getattr(pietto, "__all__", ())


@pytest.mark.parametrize("case", range(2))
def test_composite_analysis_reuses_identical_common_and_navigation_facts(
    case: int,
) -> None:
    result, _, _ = _success(f"{IDENTITIES[case]}(id, 1, nullable_id)")
    fact = cast(NavigationWindowSemanticFact, result.navigation_fact)
    assert fact.semantic_fact is result.semantic_fact
    assert result.partition_binding_fact.semantic_fact is result.semantic_fact
    assert result.order_binding_fact.semantic_fact is result.semantic_fact


@pytest.mark.parametrize("case", range(6))
def test_compatibility_wrappers_preserve_completed_identity_behavior(case: int) -> None:
    function_name = ("row_number", "rank", "dense_rank")[case % 3]
    if case >= 3:
        project_fact = _project_fact(
            f"{function_name}()",
            builder="row_number" if function_name == "row_number" else "ranking",
        )
        assert project_fact.semantic_fact.identity.name == function_name
        return
    _, relation = _parsed_relation(_program(f"{function_name}()"))
    diagnostics: list[Diagnostic] = []
    result = window_analysis.analyze_ranking_window_expression(
        definition=relation,
        item=relation.select_items[-1],
        selected_output_ordinal=0,
        source_id="slice12.pietto",
        input_schema=_row_schema(),
        field_qualifier="rows",
        value_types={},
        diagnostics=diagnostics,
    )
    assert diagnostics == []
    assert not isinstance(result, WindowExpressionUnsupported)
    assert result.semantic_fact.identity.name == function_name
    if function_name == "row_number":
        core = window_analysis.analyze_row_number_window_expression(
            definition=relation,
            item=relation.select_items[-1],
            selected_output_ordinal=0,
            source_id="slice12.pietto",
            input_schema=_row_schema(),
            field_qualifier="rows",
            value_types={},
            diagnostics=[],
        )
        assert type(core) is WindowExpressionSemanticFact


@pytest.mark.parametrize("case", range(8))
def test_project_dependency_role_order_and_ordinals_are_exact(case: int) -> None:
    identity = IDENTITIES[case // 4]
    calls = (
        f"{identity}(id)",
        f"{identity}(id, 1, nullable_id)",
        f"{identity}(1)",
        f"{identity}(1, 0, 2)",
    )
    fact = _project_fact(calls[case % 4], partition=("nullable_id",))
    roles = tuple(item.role for item in fact.dependency_occurrences)
    assert tuple(item.global_ordinal for item in fact.dependency_occurrences) == tuple(
        range(len(roles))
    )
    assert tuple(WindowDependencyRole).index(roles[0]) <= tuple(
        WindowDependencyRole
    ).index(roles[-1])


@pytest.mark.parametrize("case", range(8))
def test_project_value_and_default_occurrences_use_argument_and_default_roles(
    case: int,
) -> None:
    identity = IDENTITIES[case // 4]
    value, default = (
        ("id", "nullable_id"),
        ("rows.id", "rows.nullable_id"),
        ("id", "id"),
        ("nullable_id", "nullable_id"),
    )[case % 4]
    fact = _project_fact(f"{identity}({value}, 1, {default})")
    assert tuple(item.role for item in fact.dependency_occurrences[:2]) == (
        WindowDependencyRole.WINDOW_ARGUMENT,
        WindowDependencyRole.WINDOW_DEFAULT,
    )


@pytest.mark.parametrize("case", range(8))
def test_project_literals_offsets_and_null_create_no_dependency_occurrence(
    case: int,
) -> None:
    identity = IDENTITIES[case // 4]
    call = (
        f"{identity}(1)",
        f"{identity}(1, 0)",
        f"{identity}(1, 2, null)",
        f"{identity}(null, 2, 1)",
    )[case % 4]
    fact = _project_fact(call)
    assert all(
        item.role
        not in {
            WindowDependencyRole.WINDOW_ARGUMENT,
            WindowDependencyRole.WINDOW_DEFAULT,
        }
        for item in fact.dependency_occurrences
    )


@pytest.mark.parametrize("case", range(6))
def test_project_edges_dedupe_first_role_target_and_preserve_occurrences(
    case: int,
) -> None:
    identity = IDENTITIES[case % 2]
    fact = _project_fact(
        f"{identity}(id, 1, id)",
        partition=("id", "id"),
        order=(("id", None), ("id", "desc")),
    )
    assert len(fact.dependency_occurrences) == 6
    assert len(fact.dependency_edges) == 4
    assert tuple(edge.role for edge in fact.dependency_edges) == (
        WindowDependencyRole.WINDOW_ARGUMENT,
        WindowDependencyRole.WINDOW_DEFAULT,
        WindowDependencyRole.WINDOW_PARTITION,
        WindowDependencyRole.WINDOW_ORDER,
    )


@pytest.mark.parametrize("case", range(4))
def test_relation_input_fallback_is_exact_for_dependency_free_arguments(
    case: int,
) -> None:
    identity = IDENTITIES[case // 2]
    call = f"{identity}(1)" if case % 2 == 0 else f"{identity}(null, 1, 1)"
    fact = _project_fact(call)
    relation_occurrences = tuple(
        item
        for item in fact.dependency_occurrences
        if item.role is WindowDependencyRole.RELATION_INPUT
    )
    assert len(relation_occurrences) == 1
    assert (
        relation_occurrences[0].target.kind
        is ProjectRowDependencyNodeKind.RELATION_INPUT
    )


@pytest.mark.parametrize("case", range(4))
def test_project_result_identity_provenance_and_row_schema_boundaries_hold(
    case: int,
) -> None:
    identity = IDENTITIES[case // 2]
    builder = "general" if case % 2 == 0 else "navigation"
    fact = _project_fact(f"{identity}(id)", builder=builder)
    assert fact.result_identity.role is ProjectRowResultRole.WINDOW_RESULT
    assert fact.provenance.kind is ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION
    assert fact.result_identity.output_name == "navigation_value"


def test_semantic_and_project_models_do_not_persist_navigation_facts() -> None:
    script, _ = _parsed_relation(_program("lag(id)"))
    semantic = analyze(script)
    assert semantic.diagnostics == ()
    assert "navigation" not in {
        field.name for field in dataclasses.fields(SemanticModel)
    }
    assert "navigation" not in _read("src/pietto/_project/model.py")


@pytest.mark.parametrize("case", range(4))
def test_ir_lowering_remains_PIE_I1000_and_sql_is_unreachable(case: int) -> None:
    identity = IDENTITIES[case // 2]
    script, relation = _parsed_relation(_program(f"{identity}(id)"))
    semantic = analyze(script)
    expression = relation.select_items[-1].expression
    lowered = lower_expr(expression, semantic.model)
    assert lowered.expression is None
    assert [item.code for item in lowered.diagnostics] == ["PIE-I1000"]
    assert "WindowExpr" not in _read("src/pietto/sql/postgres.py")


def test_public_cli_json_metadata_grammar_generated_and_backends_are_unchanged() -> (
    None
):
    protected = (
        "grammar/Pietto.g4",
        "src/pietto/ast_nodes.py",
        "src/pietto/cli.py",
        "src/pietto/ir/model.py",
        "src/pietto/sql/postgres.py",
        "pyproject.toml",
        "uv.lock",
        ".github/workflows/ci.yml",
    )
    assert _git_output(["diff", "--name-only", "--", *protected]) == ""
    assert 'version = "0.1.0"' in _read("pyproject.toml")


def test_reader_fixed_point_manifests_and_preedit_fingerprints_are_exact() -> None:
    assert len(ADDED_PATHS) == 3
    assert len(MODIFIED_PATHS) == 68
    assert len(FINAL_SHA256) == 70
    assert {path: _sha256(path) for path in FINAL_SHA256} == FINAL_SHA256
    repository_paths = _repository_paths()
    compiler = tuple(
        REPO_ROOT / path
        for path in repository_paths
        if path in {"Makefile", "grammar/Pietto.g4"} or path.startswith("src/pietto/")
    )
    semantic = tuple(
        path
        for path in compiler
        if path.parent.relative_to(REPO_ROOT).as_posix() == "src/pietto/semantic"
        and path.suffix == ".py"
    )
    phase15 = tuple(
        path
        for path in semantic
        if path.name not in {"analyzer.py", "model.py", "relationship_metadata.py"}
    )
    project = tuple(
        REPO_ROOT / path
        for path in repository_paths
        if Path(path).parent.as_posix() == "src/pietto/_project"
        and path.endswith(".py")
    )
    assert (len(compiler), len(semantic), len(phase15), len(project)) == (
        92,
        35,
        32,
        18,
    )
    assert (
        _digest(compiler),
        _digest(semantic),
        _digest(phase15),
        _digest(project),
    ) == (
        COMPILER_DIGEST,
        SEMANTIC_DIGEST,
        PHASE15_SUBSET_DIGEST,
        PROJECT_DIGEST,
    )


@pytest.mark.parametrize("case", range(3))
def test_dirty_untracked_clean_and_depth_one_states_are_all_modeled(case: int) -> None:
    tracked = set(_git_output(["diff", "--name-only"]).splitlines()) - {""}
    untracked = set(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    ) - {""}
    slice14_modified = _phase53_gate2_paths("MODIFIED_PATHS")
    slice14_added = _phase53_gate2_paths("ADDED_PATHS")
    assert _git_output(["diff", "--cached", "--name-status"]) == ""
    if case == 0:
        assert tracked in (set(), set(MODIFIED_PATHS), slice14_modified)
    elif case == 1:
        assert untracked in (set(), set(ADDED_PATHS), slice14_added)
    else:
        assert _git_output(["rev-parse", "HEAD"]) == BASE_HEAD_SHA or not tracked


def test_test_inventory_selector_overlay_formatter_and_clean_ci_arithmetic_is_exact() -> (
    None
):
    names, cardinalities = _test_manifest(SELF_REL)
    assert len(names) == 64 and sum(cardinalities) == 381
    name_payload = "".join(name + "\n" for name in names).encode()
    cardinality_payload = "".join(
        f"{name}\t{cardinality}\n"
        for name, cardinality in zip(names, cardinalities, strict=True)
    ).encode()
    assert (
        hashlib.sha256(name_payload).hexdigest()
        == "c5a3690a30d8476be77f57a38ffd7d249e41980bb4618af80a3570f14f465cef"
    )
    assert (
        hashlib.sha256(cardinality_payload).hexdigest()
        == "e7a1812740ffa6f2b77d71eaa21a38ebe10ed3c9c0b0e750fa2a36333582856f"
    )
    assert (
        hashlib.sha256(("\n".join(FOCUSED_OPERANDS) + "\n").encode()).hexdigest()
        == "764c5879e93871b253e875ce1e8145ce3a998d48a94b578f8af9d31f9562e5ee"
    )
    assert (
        hashlib.sha256(("\n".join(DIRTY_OVERLAY) + "\n").encode()).hexdigest()
        == "197b591aec962f43b9b9393da99a76ff21c3a36189cc02c7a75dc5a7b85d6b26"
    )
    assert (
        hashlib.sha256(("\n".join(FORMATTER_PATHS) + "\n").encode()).hexdigest()
        == "5920e1a21f135b2537e8295b13c8bc6fa2962423812ffc3cbe1e52663e924daf"
    )
    assert (9199 + 381, 9580 - 185, 3107 + 381) == (9580, 9395, 3488)


def test_gate2_evidence_and_gate3_deferral_contract_are_exact() -> None:
    docs = _read(SPEC_REL) + _read(PLAN_REL)
    for value in (
        "A3/M62/D0",
        "64-function/381-item",
        "3488 focused",
        "9395 passed, 185",
        "9580",
        "one write-mode Ruff invocation",
        "Add Phase 53 lag and lead navigation semantics",
        "Gate 3",
    ):
        assert value in docs
    assert not (REPO_ROOT / ".git/index.lock").exists()


def test_protected_surfaces_version_tags_and_release_boundaries_are_locked() -> None:
    protected = (
        "AGENTS.md",
        "README.md",
        "grammar/Pietto.g4",
        "src/pietto/ast_nodes.py",
        "src/pietto/parser_api.py",
        "src/pietto/semantic/model.py",
        "src/pietto/ir/model.py",
        "src/pietto/sql",
        "pyproject.toml",
        "uv.lock",
        ".github/workflows",
        "tests/fixtures",
    )
    assert _git_output(["diff", "--name-only", "--", *protected]) == ""
    assert _git_output(["tag", "--list"]) == ""
    assert 'version = "0.1.0"' in _read("pyproject.toml")


# Phase 53 Slice 13 reader migration.
