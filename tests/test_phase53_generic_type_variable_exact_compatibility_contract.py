from __future__ import annotations

import ast
import hashlib
import inspect
import subprocess
import tomllib
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import Any, cast

from _phase54_active_gate2_manifest import (
    PHASE54_POST_SLICE12_INTERLUDE_BASE,
    phase54_post_slice12_interlude_clean_topic_is_active,
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
)

import pytest

import pietto
import pietto.semantic as semantic_api
import pietto.semantic.generic_compatibility as generic_compatibility
from pietto.semantic.generic_compatibility import (
    ArityMismatch,
    CandidateEvaluation,
    ConcreteTypeExpression,
    ConcreteTypeMismatch,
    ConstraintEvidence,
    ConstraintMismatch,
    GenericSignature,
    LogicalTypeIdentity,
    OverloadOutcome,
    OverloadSelection,
    OverloadSet,
    ParameterDefault,
    RepeatedVariableMismatch,
    SignatureMatch,
    SignatureParameter,
    SignatureUnsupported,
    TypeConstraint,
    TypeVariable,
    TypeVariableBinding,
    UnboundResult,
    UnresolvedArgument,
    VariableTypeExpression,
    bind_signature,
    select_overload,
    supports_constraint,
)
from pietto.semantic.model import TypeKind


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / (
    "docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md"
)
SPEC_PATH = REPO_ROOT / (
    "docs/spec/phase53-generic-type-variable-exact-compatibility-contract-v1.md"
)
SOURCE_PATH = REPO_ROOT / "src/pietto/semantic/generic_compatibility.py"
SELF_PATH = REPO_ROOT / (
    "tests/test_phase53_generic_type_variable_exact_compatibility_contract.py"
)

SPEC_H1 = (
    "Phase 53 Slice 4 Generic Type-variable, Constraint, And Exact "
    "Compatibility Foundation v1"
)
SPEC_H2 = (
    "Status And Slice Identity",
    "Existing Logical-type And Evidence Authority",
    "Private Module And No-integration Boundary",
    "Source-independent Logical-type Identity",
    "Exact Type-variable And Constraint Carriers",
    "Complete Type-by-constraint Matrix",
    "Signature Type-expression Carriers",
    "Ordered Parameter And Optional-default Contract",
    "Generic Signature And Result Contract",
    "Constructor Validation And Exception Policy",
    "Exact Same-type Binding Algorithm",
    "Binding Match And Mismatch Evidence",
    "Ordered Overload Collection",
    "Match Unsupported And Ambiguous Selection",
    "Capability-fact Non-authority",
    "Nullability And Phase 5 Boundary",
    "Phase 64 Exclusions",
    "Positive Compatibility Matrix",
    "Negative And Fail-closed Matrix",
    "Grammar AST Generated And Behavior Immutability",
    "Privacy Public Project IR SQL Boundary",
    "Reader Hash Inventory And Repository-state Closure",
    "Validation Depth-one CI And Gate 3 Publication",
    "Deferred Ownership And Stop Conditions",
)
SLICE4_H2 = (
    "Slice 4 Generic Type-variable, Constraint, And Exact Compatibility Foundation"
)
SLICE5_H2 = "Slice 5 Nullability Algebra And Signature Result-formula Foundation"
SLICE6_H2 = (
    "Slice 6 Private Window Semantic Carrier, WINDOW Stage, Dependency, "
    "And Result Roles"
)
SLICE7_H2 = "Slice 7 row_number Direct-field MVP"
SLICE8_H2 = "Slice 8 rank / dense_rank And Peer Semantics"
SLICE9_H2 = "Slice 9 percent_rank / cume_dist / ntile"
SLICE10_H2 = "Slice 10 Partition Binding, Multi-key Visibility, And Diagnostics"
SLICE11_H2 = (
    "Slice 11 Window-local Ordering, Direction, Mandatory-order Policy, And Determinism"
)
SLICE12_H2 = "Slice 12 lag / lead Navigation, Offset, Default, And Nullability"
SLICE13_H2 = (
    "Slice 13 — Grouped-result Ranking, Aggregate-result Inputs, And Bounded Let "
    "Visibility"
)
SLICE14_H2 = (
    "Slice 14 — Multiple Window Outputs, Final-order Alias, Downstream Schema, "
    "And Lineage"
)
SLICE15_H2 = "Slice 15 — Window IR, Dual-backend Lowering, And Window-function Facts"
EXPECTED_TEST_NAMES = (
    "test_slice4_artifact_paths_heading_contract_and_lifecycle_are_exact",
    "test_private_module_enum_carrier_and_privacy_shapes_are_exact",
    "test_logical_type_identity_validation_equality_hash_and_repr_are_exact",
    "test_type_variable_name_and_constraint_validation_is_exact",
    "test_complete_type_by_constraint_truth_matrix_is_exact",
    "test_alias_unknown_deferred_and_decimal_precision_boundaries_are_exact",
    "test_concrete_and_variable_type_expression_shapes_are_exact",
    "test_parameter_position_optional_and_default_contract_is_exact",
    "test_generic_signature_constructor_and_reference_invariants_are_exact",
    "test_unconstrained_and_repeated_variable_binding_is_exact",
    "test_concrete_mixed_and_independent_variable_binding_is_exact",
    "test_exact_logical_identity_binding_has_no_case_or_kind_coercion",
    "test_optional_trailing_parameter_binding_and_omission_is_exact",
    "test_arity_mismatch_evidence_is_exact",
    "test_binding_failures_are_structured_ordered_and_fail_closed",
    "test_multiple_constraint_evidence_uses_declaration_order",
    "test_variable_and_concrete_result_resolution_is_exact",
    "test_binding_results_are_immutable_hashable_and_repeatable",
    "test_overload_collection_preserves_order_and_duplicate_rows",
    "test_overload_selection_match_and_unsupported_outcomes_are_exact",
    "test_overload_ambiguity_preserves_every_matching_candidate_in_order",
    "test_overload_selection_has_no_first_match_or_tiebreaker",
    "test_phase52_capability_facts_are_evidence_not_compatibility_authority",
    "test_current_semantic_analyzer_and_window_paths_do_not_import_generic_compatibility",
    "test_nullability_phase5_and_phase64_exclusions_are_exact",
    "test_project_ir_sql_cli_serializer_and_public_exports_are_unchanged",
    "test_grammar_ast_generated_parser_and_window_identity_are_byte_locked",
    "test_reader_hash_inventory_and_nested_hash_closure_is_exact",
    "test_slice4_dirty_clean_and_depth_one_repository_states_are_locked",
    "test_test_inventory_focused_selector_and_dirty_overlay_are_exact",
    "test_validation_gate3_and_no_behavior_boundaries_are_locked",
)
EXPECTED_CARDINALITIES = (
    1,
    1,
    10,
    10,
    56,
    9,
    8,
    10,
    10,
    6,
    6,
    8,
    7,
    4,
    8,
    4,
    4,
    1,
    5,
    4,
    5,
    4,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
)
FOCUSED_OPERANDS, DIRTY_OVERLAY, ADDED_PATHS, MODIFIED_PATHS = (
    (
        "tests/test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py",
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
        "tests/test_phase53_grouped_result_ranking_aggregate_result_inputs_bounded_let_visibility_contract.py",
        "tests/test_phase43_let_binding_group_by_keys.py::test_group_by_direct_field_row_let_is_semantically_accepted",
        "tests/test_phase43_let_binding_group_by_keys.py::test_group_by_qualified_and_chained_field_row_lets_are_semantically_accepted",
        "tests/test_phase43_let_binding_group_by_keys.py::test_non_slice4_group_by_let_consumers_remain_rejected",
        "tests/test_phase43_let_binding_grouped_order_by.py::test_grouped_order_by_direct_field_row_let_is_semantically_accepted",
        "tests/test_phase43_let_binding_grouped_order_by.py::test_grouped_order_by_qualified_chained_alias_row_let_is_accepted",
        "tests/test_phase43_let_binding_grouped_order_by.py::test_non_slice5_grouped_order_let_consumers_remain_rejected",
        "tests/test_phase49_project_let_scope_value_facts.py::test_legal_let_bindings_produce_private_value_facts",
        "tests/test_phase49_let_visibility_order_shadowing_hardening.py::test_public_let_visibility_order_and_shadowing_fail_closed",
        "tests/test_phase51_grouped_aggregate_project_row_schema.py::test_multiple_keys_and_direct_aggregates_preserve_exact_select_order",
        "tests/test_phase51_grouped_aggregate_project_row_schema.py::test_direct_and_chained_group_key_lets_compose_with_direct_aggregates",
        "tests/test_phase51_aggregate_only_project_row_schema.py::test_exact_current_direct_aggregate_type_and_nullability_matrix",
        "tests/test_phase51_clause_dependency_fail_closed.py::test_grouped_order_outputs_row_lets_direction_identity_and_first_dedupe",
        "tests/test_phase51_clause_dependency_fail_closed.py::test_grouped_order_row_let_uses_first_selected_identity_in_source_order",
        "tests/test_phase51_clause_dependency_fail_closed.py::test_grouped_order_failure_matrix_is_atomic_and_does_not_widen_qualifiers",
        "tests/test_phase53_multiple_window_outputs_final_order_alias_downstream_schema_lineage_contract.py",
    ),
    (
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
    ),
    (
        "docs/spec/phase53-completion-audit-and-status-lock-v1.md",
        "tests/test_phase53_completion_audit_and_status_lock.py",
    ),
    (
        "docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md",
        "tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py",
        "tests/test_phase51_completion_audit_and_status_lock.py",
        "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
        "tests/test_phase52_aggregate_signature_algebra_facts.py",
        "tests/test_phase52_completion_audit_and_status_lock.py",
        "tests/test_phase52_expression_stage_clause_capability_facts.py",
        "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
        "tests/test_phase52_scalar_function_operator_signature_facts.py",
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
    ),
)
EXPECTED_DIRTY_PATHS = frozenset((*ADDED_PATHS, *MODIFIED_PATHS))

BASE_HEAD = "3c1feab5bc70d407e9e4d7ccd0c5d489eec0ee68"
PHASE54_SLICE2_BASE_HEAD = "d8a5e9ab3de70ce30575513c73560c86430eca63"
PHASE54_SLICE4_BASE_HEAD = "15bae172ee151e370fe59d3bf909d735aee6aa90"
PHASE54_SLICE5_BASE_HEAD = "0f3c955c5a5fbd8046ef611ad1bef0b636c8be01"
PHASE54_SLICE6_BASE_HEAD = "c44a4271d9592cb393d2232f127a59d8466cc60a"
PHASE54_SLICE7_BASE_HEAD = "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16"
PHASE54_SLICE8_BASE_HEAD = "027b33cafcfd58916a89e299487dad38d24ade6c"
PHASE54_SLICE9_BASE_HEAD = "0ceb9a476e6592714cdc76845949ba0ae5123eb5"
FINAL_COMPILER_DIGEST = (
    "f9eca1bf5cadfcc1583ba465f33bf761114e6d9d2785de15a2d73b5a19a6ff62"
)
FINAL_SEMANTIC_DIGEST = (
    "731e17cc85849c7716abeb08abeda03f72e3e21af183a391107adf96ccab6d70"
)
FINAL_PHASE15_DIGEST = (
    "81db265a7bbd290b9c9227733e92dc502f8e8c8f0ff76b4d631651772876550d"
)
FINAL_SOURCE_SHA256 = "340703267a6185f0b37401c1097a1f246d34d3d0d46c1f583b5ce5134e5090f8"
FINAL_SPEC_SHA256 = "194ee730b88782afd6f84d90b52cb4f02a3f5efb386155fae062978f3dfe5bd9"
FINAL_PLAN_SHA256 = "3077c2fec0d7e2c4de717973c6403d5a450b8c01fe5846e427363ffcb41a78f5"

PROTECTED_SHA256 = {
    "grammar/Pietto.g4": "661f00037b4ade8f8b5bef0cb3e070e4379decdd11cd19021d68e960e69d2724",
    "src/pietto/ast_nodes.py": "bbfd121446d62d33c7990b80d17579d3f8b55763ce1b5f93ee17247cbd2ce0c2",
    "src/pietto/ast_builder.py": "918dc9f6d7705376b604e69fb80c45cf4c3673c8909a58537770d114d96252cb",
    "src/pietto/parser_api.py": "aa744c3ee334c8729917ae2aed2ee906874f927d47e99542d5accb8a98aa456b",
    "src/pietto/_window_identity.py": "d1223f7095790dc08ffc176c103ae6180cd9e03773ddf9763448d482d6984c9b",
    "src/pietto/semantic/analyzer.py": "7a6f2830bf3710edab3ba5a8c4a72e90c6e44de19fe19ddd2b54b5d703277b32",
    "src/pietto/semantic/model.py": "55f1d110854073ec3f9b47ecffd3e41c6c2bc3b606da61e8b271a23e736bd4ba",
    "src/pietto/semantic/catalog.py": "f566f39395e3bdc933e60d15e740749255dd3749cf3907684240e4b43dfc9e40",
    "src/pietto/semantic/expressions.py": "37b198f72b0c71c90a82d746671be8528a9ea5c2d4818ff7ef4ba55e30e9c595",
    "src/pietto/semantic/aggregates.py": "f5d5be237960e50f62f539d76e09be425980c9f8e657846333b5ef1aaa948333",
    "src/pietto/semantic/type_aliases.py": "57be862c49b24a57f53a541e04524e3d511a60b8d4bdbcfc28d3529b484ec9d8",
    "src/pietto/__init__.py": "669ac67bb23a0c8179995e0e415d76c46210c12311e29cd89d2612b45b0a194d",
    "src/pietto/semantic/__init__.py": "21dbef77211fa5dbf0a64c050d5751718d70e990498bebc3b1ba4590b6086cfb",
    "src/pietto/ir/__init__.py": "41940080d7fecb42ecd87f2fe2eb2b68a8ab7bd2dfe8b393dc8d7d880a1760ec",
    "src/pietto/sql/__init__.py": "e40bd3eee7f76bc68313adb8237a7a6c5d84286197261f70c827a4219c9e3418",
    "src/pietto/cli.py": "e9d90d40293db543c4b6c0da829e8b6a122fd2f8b29fcafdc23d4d54b1c42e09",
    "src/pietto/cli_json.py": "ccee00529ee36b123f70d418105609dbb4906f2ccc1c1f5653527b1168fb6d91",
    "src/pietto/_metadata/serializer.py": "dd1264f9c49e7f9bfe694d185b9ee30e775374cce2969d6e9ddb7796bbb4ae4b",
    "src/pietto/_project/json_v2.py": "74251e684a22de4dcdc7e1822a6843ca89cbdfa7e136a046676d848b57953bd5",
    "pyproject.toml": "36aa8e1d19a8409e56e0163a465b9608a88c1bffe644165ba49db49bf5ec3d01",
    "uv.lock": "a7d9125995e98a8a74d3664ceae7801cc1f4cce74ec323933da67838be199cea",
    ".github/workflows/ci.yml": "4db1c9a49b0af230bae3f088bf84524e210e0afcd6a87250322e5036a69e8d94",
}

_MATRIX_ROWS = (
    ("Any", TypeKind.BUILTIN, (True, False, False, False)),
    ("Bool", TypeKind.BUILTIN, (True, True, False, False)),
    ("Bytes", TypeKind.BUILTIN, (True, False, False, False)),
    ("Date", TypeKind.BUILTIN, (True, True, True, False)),
    ("Decimal", TypeKind.BUILTIN, (True, True, True, True)),
    ("Float", TypeKind.BUILTIN, (True, True, True, True)),
    ("Int", TypeKind.BUILTIN, (True, True, True, True)),
    ("Json", TypeKind.BUILTIN, (True, False, False, False)),
    ("Text", TypeKind.BUILTIN, (True, True, False, False)),
    ("Timestamp", TypeKind.BUILTIN, (True, True, True, False)),
    ("UUID", TypeKind.BUILTIN, (True, True, False, False)),
    ("OrderState", TypeKind.ENUM, (False, False, False, False)),
    ("OrderRow", TypeKind.SHAPE, (False, False, False, False)),
    (None, None, (False, False, False, False)),
)
_MATRIX_CASES = tuple(
    (
        name or "unresolved",
        None
        if name is None
        else LogicalTypeIdentity(name=name, kind=cast(TypeKind, kind)),
        constraint,
        expected[index],
    )
    for name, kind, expected in _MATRIX_ROWS
    for index, constraint in enumerate(TypeConstraint)
)

INT = LogicalTypeIdentity(name="Int", kind=TypeKind.BUILTIN)
FLOAT = LogicalTypeIdentity(name="Float", kind=TypeKind.BUILTIN)
DECIMAL = LogicalTypeIdentity(name="Decimal", kind=TypeKind.BUILTIN)
TEXT = LogicalTypeIdentity(name="Text", kind=TypeKind.BUILTIN)
DATE = LogicalTypeIdentity(name="Date", kind=TypeKind.BUILTIN)
BOOL = LogicalTypeIdentity(name="Bool", kind=TypeKind.BUILTIN)
UUID = LogicalTypeIdentity(name="UUID", kind=TypeKind.BUILTIN)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(REPO_ROOT).as_posix()):
        digest.update(path.relative_to(REPO_ROOT).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _git(*arguments: str, check: bool = True) -> str:
    result = subprocess.run(
        ("git", *arguments),
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


def _headings(path: Path) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    lines = path.read_text().splitlines()
    h1 = tuple(line[2:] for line in lines if line.startswith("# "))
    h2 = tuple(line[3:] for line in lines if line.startswith("## "))
    h3 = tuple(line[4:] for line in lines if line.startswith("### "))
    assert len(h1) == 1
    return h1[0], h2, h3


def _concrete_signature(
    parameter_types: tuple[LogicalTypeIdentity, ...],
    result: LogicalTypeIdentity,
    *,
    optional_from: int | None = None,
) -> GenericSignature:
    return GenericSignature(
        type_variables=(),
        parameters=tuple(
            SignatureParameter(
                position=index,
                type_expression=ConcreteTypeExpression(logical_type=logical_type),
                optional=optional_from is not None and index >= optional_from,
            )
            for index, logical_type in enumerate(parameter_types)
        ),
        result=ConcreteTypeExpression(logical_type=result),
    )


def _variable_signature(
    constraints: tuple[TypeConstraint, ...] = (),
    *,
    repeated: bool = False,
    optional: bool = False,
    result: LogicalTypeIdentity | None = None,
) -> GenericSignature:
    variable = TypeVariable(name="T", constraints=constraints)
    expression = VariableTypeExpression(name="T")
    parameters = (
        SignatureParameter(
            position=0,
            type_expression=expression,
            optional=optional,
        ),
    )
    if repeated:
        parameters += (SignatureParameter(position=1, type_expression=expression),)
    result_expression = (
        ConcreteTypeExpression(logical_type=result)
        if result is not None
        else VariableTypeExpression(name="T")
    )
    return GenericSignature(
        type_variables=(variable,),
        parameters=parameters,
        result=result_expression,
    )


def _assert_unsupported(
    result: object,
    mismatch_type: type[object],
) -> object:
    assert type(result) is SignatureUnsupported
    mismatch = cast(SignatureUnsupported, result).mismatch
    assert type(mismatch) is mismatch_type
    return mismatch


def _all_repository_paths() -> tuple[str, ...]:
    paths = set(_git("ls-files").splitlines())
    paths.update(_git("ls-files", "--others", "--exclude-standard").splitlines())
    return tuple(sorted(paths))


def _phase54_slice2_paths() -> tuple[frozenset[str], frozenset[str]]:
    path = REPO_ROOT / "tests/_phase54_active_gate2_manifest.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
    expected = {
        "ADDED_PATHS",
        "NON_READER_MODIFIED_PATHS",
        "MECHANICAL_READER_PATHS",
    }
    values: dict[str, frozenset[str]] = {}
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in expected
        ):
            value = ast.literal_eval(node.value)
            assert isinstance(value, set)
            assert all(isinstance(item, str) for item in value)
            values[node.targets[0].id] = frozenset(value)
    assert set(values) == expected
    return (
        values["NON_READER_MODIFIED_PATHS"] | values["MECHANICAL_READER_PATHS"],
        values["ADDED_PATHS"],
    )


def test_slice4_artifact_paths_heading_contract_and_lifecycle_are_exact() -> None:
    assert SOURCE_PATH.is_file()
    assert SPEC_PATH.is_file()
    assert SELF_PATH.is_file()
    assert _headings(SPEC_PATH) == (SPEC_H1, SPEC_H2, ())
    plan_h1, plan_h2, plan_h3 = _headings(PLAN_PATH)
    assert plan_h1 == (
        "Phase 53 — Window Functions, Generic Signature Compatibility, "
        "And Nullability Foundation"
    )
    assert plan_h2.count(SLICE4_H2) == 1
    assert plan_h2[-13:] == (
        SLICE4_H2,
        SLICE5_H2,
        SLICE6_H2,
        SLICE7_H2,
        SLICE8_H2,
        SLICE9_H2,
        SLICE10_H2,
        SLICE11_H2,
        SLICE12_H2,
        SLICE13_H2,
        SLICE14_H2,
        SLICE15_H2,
        "Slice 16 — Completion Audit, Status Lock, Dialect, Privacy, And "
        "No-authority Closure",
    )
    assert plan_h2.count(SLICE5_H2) == 1
    assert plan_h2.count(SLICE6_H2) == 1
    assert plan_h2.count(SLICE7_H2) == 1
    assert plan_h2.count(SLICE8_H2) == 1
    assert plan_h2.count(SLICE9_H2) == 1
    assert plan_h2.count(SLICE11_H2) == 1
    assert plan_h2.count(SLICE12_H2) == 1
    assert plan_h2.count(SLICE13_H2) == 1
    assert plan_h2.count(SLICE14_H2) == 1
    assert plan_h2.count(SLICE15_H2) == 1
    assert plan_h3 == ()
    plan = PLAN_PATH.read_text()
    assert "Phase 53 is `ACTIVE`" in plan
    assert "Slice 4 remains `UNSTARTED` throughout Gate 2" in plan
    assert "Phase 53 Slice 4 Gate 3" not in plan
    assert "6383 passed, 183 deselected" in plan
    assert "6566 clean-CI passes per Python job" in plan


def test_private_module_enum_carrier_and_privacy_shapes_are_exact() -> None:
    assert generic_compatibility.__all__ == ()
    assert tuple(TypeConstraint) == (
        TypeConstraint.SCALAR,
        TypeConstraint.COMPARABLE,
        TypeConstraint.ORDERABLE,
        TypeConstraint.NUMERIC,
    )
    assert tuple(ParameterDefault) == (ParameterDefault.OMITTED,)
    assert tuple(OverloadOutcome) == (
        OverloadOutcome.MATCH,
        OverloadOutcome.UNSUPPORTED,
        OverloadOutcome.AMBIGUOUS,
    )
    assert tuple(member.value for member in TypeConstraint) == (
        "scalar",
        "comparable",
        "orderable",
        "numeric",
    )
    carriers = (
        LogicalTypeIdentity,
        TypeVariable,
        ConcreteTypeExpression,
        VariableTypeExpression,
        SignatureParameter,
        GenericSignature,
        TypeVariableBinding,
        ConstraintEvidence,
        ArityMismatch,
        UnresolvedArgument,
        ConcreteTypeMismatch,
        RepeatedVariableMismatch,
        ConstraintMismatch,
        UnboundResult,
        SignatureMatch,
        SignatureUnsupported,
        OverloadSet,
        CandidateEvaluation,
        OverloadSelection,
    )
    for carrier in carriers:
        assert is_dataclass(carrier)
        assert "__slots__" in carrier.__dict__
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in inspect.signature(carrier).parameters.values()
        )
    source = SOURCE_PATH.read_text()
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert imported == {"annotations", "dataclass", "StrEnum", "TypeKind"}
    assert not hasattr(pietto, "LogicalTypeIdentity")
    assert not hasattr(semantic_api, "LogicalTypeIdentity")
    assert "capability_" not in source
    assert "_window" not in source


@pytest.mark.parametrize(
    "case",
    (
        "builtin",
        "enum",
        "shape",
        "case",
        "equality",
        "name-type",
        "name-pattern",
        "kind-type",
        "kind-value",
        "builtin-name",
    ),
)
def test_logical_type_identity_validation_equality_hash_and_repr_are_exact(
    case: str,
) -> None:
    if case == "builtin":
        assert INT == LogicalTypeIdentity(name="Int", kind=TypeKind.BUILTIN)
    elif case == "enum":
        value = LogicalTypeIdentity(name="OrderState", kind=TypeKind.ENUM)
        assert (value.name, value.kind) == ("OrderState", TypeKind.ENUM)
    elif case == "shape":
        value = LogicalTypeIdentity(name="OrderRow", kind=TypeKind.SHAPE)
        assert hash(value) == hash(
            LogicalTypeIdentity(name="OrderRow", kind=TypeKind.SHAPE)
        )
    elif case == "case":
        upper = LogicalTypeIdentity(name="OrderState", kind=TypeKind.ENUM)
        lower = LogicalTypeIdentity(name="orderState", kind=TypeKind.ENUM)
        assert upper != lower
    elif case == "equality":
        assert len({INT, LogicalTypeIdentity(name="Int", kind=TypeKind.BUILTIN)}) == 1
        assert "name='Int'" in repr(INT)
        assert "TypeKind.BUILTIN" in repr(INT)
    elif case == "name-type":
        with pytest.raises(TypeError, match="logical type name must be an exact str"):
            LogicalTypeIdentity(name=cast(Any, 1), kind=TypeKind.ENUM)
    elif case == "name-pattern":
        with pytest.raises(ValueError, match="logical type name must match"):
            LogicalTypeIdentity(name="not-valid", kind=TypeKind.ENUM)
    elif case == "kind-type":
        with pytest.raises(
            TypeError, match="logical type kind must be an exact TypeKind"
        ):
            LogicalTypeIdentity(name="Int", kind=cast(Any, "builtin"))
    elif case == "kind-value":
        with pytest.raises(ValueError, match="must be BUILTIN, ENUM, or SHAPE"):
            LogicalTypeIdentity(name="Alias", kind=TypeKind.TYPE_ALIAS)
    else:
        with pytest.raises(ValueError, match="not in the exact catalog"):
            LogicalTypeIdentity(name="Integer", kind=TypeKind.BUILTIN)


@pytest.mark.parametrize(
    "case",
    (
        "empty",
        "ordered",
        "case",
        "name-type",
        "name-pattern",
        "container",
        "member",
        "duplicate",
        "frozen",
        "repr",
    ),
)
def test_type_variable_name_and_constraint_validation_is_exact(case: str) -> None:
    if case == "empty":
        assert TypeVariable(name="T", constraints=()).constraints == ()
    elif case == "ordered":
        value = TypeVariable(
            name="T",
            constraints=(TypeConstraint.NUMERIC, TypeConstraint.SCALAR),
        )
        assert value.constraints == (TypeConstraint.NUMERIC, TypeConstraint.SCALAR)
    elif case == "case":
        assert TypeVariable(name="T", constraints=()) != TypeVariable(
            name="t",
            constraints=(),
        )
    elif case == "name-type":
        with pytest.raises(TypeError, match="type variable name must be an exact str"):
            TypeVariable(name=cast(Any, 1), constraints=())
    elif case == "name-pattern":
        with pytest.raises(ValueError, match="type variable name must match"):
            TypeVariable(name="T-U", constraints=())
    elif case == "container":
        with pytest.raises(TypeError, match="constraints must be an exact tuple"):
            TypeVariable(name="T", constraints=cast(Any, []))
    elif case == "member":
        with pytest.raises(TypeError, match="exact TypeConstraint members"):
            TypeVariable(name="T", constraints=cast(Any, ("numeric",)))
    elif case == "duplicate":
        with pytest.raises(ValueError, match="constraints must be unique"):
            TypeVariable(
                name="T",
                constraints=(TypeConstraint.SCALAR, TypeConstraint.SCALAR),
            )
    elif case == "frozen":
        value = TypeVariable(name="T", constraints=())
        with pytest.raises(FrozenInstanceError):
            setattr(value, "name", "U")
    else:
        value = TypeVariable(name="T", constraints=(TypeConstraint.NUMERIC,))
        assert hash(value)
        assert repr(value).startswith("TypeVariable(name='T'")


@pytest.mark.parametrize(
    ("label", "logical_type", "constraint", "expected"),
    _MATRIX_CASES,
)
def test_complete_type_by_constraint_truth_matrix_is_exact(
    label: str,
    logical_type: LogicalTypeIdentity | None,
    constraint: TypeConstraint,
    expected: bool,
) -> None:
    assert label
    assert supports_constraint(logical_type, constraint) is expected


@pytest.mark.parametrize(
    "case",
    (
        "alias",
        "unknown",
        "DateTime",
        "Time",
        "Interval",
        "Money",
        "Currency",
        "Null",
        "decimal",
    ),
)
def test_alias_unknown_deferred_and_decimal_precision_boundaries_are_exact(
    case: str,
) -> None:
    if case == "alias":
        with pytest.raises(ValueError, match="BUILTIN, ENUM, or SHAPE"):
            LogicalTypeIdentity(name="Alias", kind=TypeKind.TYPE_ALIAS)
    elif case == "unknown":
        with pytest.raises(ValueError, match="BUILTIN, ENUM, or SHAPE"):
            LogicalTypeIdentity(name="Unknown", kind=TypeKind.UNKNOWN)
    elif case == "decimal":
        value = LogicalTypeIdentity(name="Decimal", kind=TypeKind.BUILTIN)
        assert tuple(field.name for field in fields(value)) == ("name", "kind")
        assert not hasattr(value, "precision")
        assert not hasattr(value, "scale")
    else:
        with pytest.raises(ValueError, match="not in the exact catalog"):
            LogicalTypeIdentity(name=case, kind=TypeKind.BUILTIN)


@pytest.mark.parametrize(
    "case",
    (
        "concrete",
        "variable",
        "equality",
        "concrete-member",
        "variable-type",
        "variable-pattern",
        "frozen",
        "shape",
    ),
)
def test_concrete_and_variable_type_expression_shapes_are_exact(case: str) -> None:
    if case == "concrete":
        assert ConcreteTypeExpression(logical_type=INT).logical_type == INT
    elif case == "variable":
        assert VariableTypeExpression(name="T").name == "T"
    elif case == "equality":
        assert ConcreteTypeExpression(logical_type=INT) == ConcreteTypeExpression(
            logical_type=INT
        )
        assert hash(VariableTypeExpression(name="T"))
    elif case == "concrete-member":
        with pytest.raises(TypeError, match="requires an exact logical type"):
            ConcreteTypeExpression(logical_type=cast(Any, "Int"))
    elif case == "variable-type":
        with pytest.raises(TypeError, match="reference name must be an exact str"):
            VariableTypeExpression(name=cast(Any, 1))
    elif case == "variable-pattern":
        with pytest.raises(ValueError, match="reference name must match"):
            VariableTypeExpression(name="T-U")
    elif case == "frozen":
        value = ConcreteTypeExpression(logical_type=INT)
        with pytest.raises(FrozenInstanceError):
            setattr(value, "logical_type", FLOAT)
    else:
        assert tuple(field.name for field in fields(ConcreteTypeExpression)) == (
            "logical_type",
        )
        assert tuple(field.name for field in fields(VariableTypeExpression)) == (
            "name",
        )


@pytest.mark.parametrize(
    "case",
    (
        "required",
        "optional-none",
        "optional-marker",
        "negative",
        "bool-position",
        "position-type",
        "expression",
        "optional-type",
        "default-type",
        "default-required",
    ),
)
def test_parameter_position_optional_and_default_contract_is_exact(case: str) -> None:
    expression = ConcreteTypeExpression(logical_type=INT)
    if case == "required":
        value = SignatureParameter(position=0, type_expression=expression)
        assert (value.optional, value.default) == (False, None)
    elif case == "optional-none":
        value = SignatureParameter(
            position=0, type_expression=expression, optional=True
        )
        assert (value.optional, value.default) == (True, None)
    elif case == "optional-marker":
        value = SignatureParameter(
            position=0,
            type_expression=expression,
            optional=True,
            default=ParameterDefault.OMITTED,
        )
        assert value.default is ParameterDefault.OMITTED
    elif case == "negative":
        with pytest.raises(ValueError, match="position must be nonnegative"):
            SignatureParameter(position=-1, type_expression=expression)
    elif case == "bool-position":
        with pytest.raises(TypeError, match="position must be an exact int"):
            SignatureParameter(position=cast(Any, True), type_expression=expression)
    elif case == "position-type":
        with pytest.raises(TypeError, match="position must be an exact int"):
            SignatureParameter(position=cast(Any, "0"), type_expression=expression)
    elif case == "expression":
        with pytest.raises(TypeError, match="requires an exact type expression"):
            SignatureParameter(position=0, type_expression=cast(Any, INT))
    elif case == "optional-type":
        with pytest.raises(TypeError, match="optional must be an exact bool"):
            SignatureParameter(
                position=0,
                type_expression=expression,
                optional=cast(Any, 1),
            )
    elif case == "default-type":
        with pytest.raises(TypeError, match="exact ParameterDefault or None"):
            SignatureParameter(
                position=0,
                type_expression=expression,
                optional=True,
                default=cast(Any, "omitted"),
            )
    else:
        with pytest.raises(ValueError, match="default requires optional=True"):
            SignatureParameter(
                position=0,
                type_expression=expression,
                default=ParameterDefault.OMITTED,
            )


@pytest.mark.parametrize(
    "case",
    (
        "zero",
        "optional-only",
        "containers",
        "member",
        "duplicate",
        "positions",
        "optional-order",
        "undeclared-parameter",
        "undeclared-result",
        "unused-result-only",
    ),
)
def test_generic_signature_constructor_and_reference_invariants_are_exact(
    case: str,
) -> None:
    concrete = ConcreteTypeExpression(logical_type=INT)
    variable = TypeVariable(name="T", constraints=())
    reference = VariableTypeExpression(name="T")
    if case == "zero":
        value = GenericSignature(type_variables=(), parameters=(), result=concrete)
        assert value.parameters == ()
    elif case == "optional-only":
        value = GenericSignature(
            type_variables=(variable,),
            parameters=(
                SignatureParameter(
                    position=0,
                    type_expression=reference,
                    optional=True,
                ),
            ),
            result=reference,
        )
        assert value.type_variables == (variable,)
    elif case == "containers":
        with pytest.raises(TypeError, match="type_variables must be an exact tuple"):
            GenericSignature(
                type_variables=cast(Any, []),
                parameters=(),
                result=concrete,
            )
        with pytest.raises(TypeError, match="parameters must be an exact tuple"):
            GenericSignature(
                type_variables=(),
                parameters=cast(Any, []),
                result=concrete,
            )
    elif case == "member":
        with pytest.raises(TypeError, match="exact TypeVariable members"):
            GenericSignature(
                type_variables=cast(Any, ("T",)),
                parameters=(),
                result=concrete,
            )
    elif case == "duplicate":
        with pytest.raises(ValueError, match="names must be unique"):
            GenericSignature(
                type_variables=(variable, variable),
                parameters=(SignatureParameter(position=0, type_expression=reference),),
                result=reference,
            )
    elif case == "positions":
        with pytest.raises(ValueError, match="positions must be continuous"):
            GenericSignature(
                type_variables=(),
                parameters=(SignatureParameter(position=1, type_expression=concrete),),
                result=concrete,
            )
    elif case == "optional-order":
        with pytest.raises(ValueError, match="trailing suffix"):
            GenericSignature(
                type_variables=(),
                parameters=(
                    SignatureParameter(
                        position=0,
                        type_expression=concrete,
                        optional=True,
                    ),
                    SignatureParameter(position=1, type_expression=concrete),
                ),
                result=concrete,
            )
    elif case == "undeclared-parameter":
        with pytest.raises(ValueError, match="reference declared variables"):
            GenericSignature(
                type_variables=(),
                parameters=(SignatureParameter(position=0, type_expression=reference),),
                result=concrete,
            )
    elif case == "undeclared-result":
        with pytest.raises(ValueError, match="reference declared variables"):
            GenericSignature(type_variables=(), parameters=(), result=reference)
    else:
        with pytest.raises(ValueError, match="must appear in a parameter"):
            GenericSignature(
                type_variables=(variable,),
                parameters=(),
                result=reference,
            )


@pytest.mark.parametrize(
    "case",
    (
        "one",
        "enum",
        "repeated",
        "repeated-mismatch",
        "arguments-container",
        "signature-member",
    ),
)
def test_unconstrained_and_repeated_variable_binding_is_exact(case: str) -> None:
    if case == "one":
        result = bind_signature(_variable_signature(), (INT,))
        assert type(result) is SignatureMatch
        assert cast(SignatureMatch, result).bindings == (
            TypeVariableBinding(
                variable_name="T",
                logical_type=INT,
                first_parameter_position=0,
            ),
        )
    elif case == "enum":
        enum_type = LogicalTypeIdentity(name="OrderState", kind=TypeKind.ENUM)
        result = bind_signature(_variable_signature(), (enum_type,))
        assert type(result) is SignatureMatch
        assert cast(SignatureMatch, result).result_type == enum_type
    elif case == "repeated":
        result = bind_signature(_variable_signature(repeated=True), (INT, INT))
        assert type(result) is SignatureMatch
        assert len(cast(SignatureMatch, result).bindings) == 1
    elif case == "repeated-mismatch":
        mismatch = _assert_unsupported(
            bind_signature(_variable_signature(repeated=True), (INT, FLOAT)),
            RepeatedVariableMismatch,
        )
        assert cast(RepeatedVariableMismatch, mismatch).parameter_position == 1
    elif case == "arguments-container":
        with pytest.raises(TypeError, match="arguments must be an exact tuple"):
            bind_signature(_variable_signature(), cast(Any, [INT]))
    else:
        with pytest.raises(
            TypeError, match="signature must be an exact GenericSignature"
        ):
            bind_signature(cast(Any, "signature"), (INT,))


@pytest.mark.parametrize(
    "case",
    ("concrete", "concrete-mismatch", "mixed", "independent", "zero", "ordered"),
)
def test_concrete_mixed_and_independent_variable_binding_is_exact(case: str) -> None:
    if case == "concrete":
        result = bind_signature(_concrete_signature((INT,), TEXT), (INT,))
        assert type(result) is SignatureMatch
        assert cast(SignatureMatch, result).result_type == TEXT
    elif case == "concrete-mismatch":
        mismatch = _assert_unsupported(
            bind_signature(_concrete_signature((INT,), TEXT), (FLOAT,)),
            ConcreteTypeMismatch,
        )
        assert cast(ConcreteTypeMismatch, mismatch).expected == INT
    elif case == "mixed":
        variable = TypeVariable(name="T", constraints=())
        signature = GenericSignature(
            type_variables=(variable,),
            parameters=(
                SignatureParameter(
                    position=0,
                    type_expression=ConcreteTypeExpression(logical_type=TEXT),
                ),
                SignatureParameter(
                    position=1,
                    type_expression=VariableTypeExpression(name="T"),
                ),
            ),
            result=VariableTypeExpression(name="T"),
        )
        result = bind_signature(signature, (TEXT, INT))
        assert type(result) is SignatureMatch
        assert cast(SignatureMatch, result).result_type == INT
    elif case == "independent":
        variables = (
            TypeVariable(name="U", constraints=()),
            TypeVariable(name="T", constraints=()),
        )
        signature = GenericSignature(
            type_variables=variables,
            parameters=(
                SignatureParameter(
                    position=0,
                    type_expression=VariableTypeExpression(name="T"),
                ),
                SignatureParameter(
                    position=1,
                    type_expression=VariableTypeExpression(name="U"),
                ),
            ),
            result=VariableTypeExpression(name="U"),
        )
        result = cast(SignatureMatch, bind_signature(signature, (INT, TEXT)))
        assert tuple(binding.variable_name for binding in result.bindings) == ("T", "U")
        assert result.result_type == TEXT
    elif case == "zero":
        result = bind_signature(_concrete_signature((), BOOL), ())
        assert result == SignatureMatch(
            bindings=(),
            result_type=BOOL,
            constraint_evidence=(),
            omitted_positions=(),
        )
    else:
        signature = _concrete_signature((INT, TEXT), BOOL)
        mismatch = cast(
            ConcreteTypeMismatch,
            _assert_unsupported(
                bind_signature(signature, (INT, UUID)),
                ConcreteTypeMismatch,
            ),
        )
        assert mismatch.parameter_position == 1


_IDENTITY_MISMATCH_CASES = (
    (INT, FLOAT),
    (FLOAT, DECIMAL),
    (TEXT, UUID),
    (DATE, TEXT),
    (BOOL, INT),
    (
        LogicalTypeIdentity(name="OrderState", kind=TypeKind.ENUM),
        LogicalTypeIdentity(name="orderState", kind=TypeKind.ENUM),
    ),
    (
        LogicalTypeIdentity(name="Entity", kind=TypeKind.ENUM),
        LogicalTypeIdentity(name="Entity", kind=TypeKind.SHAPE),
    ),
    (
        LogicalTypeIdentity(name="OrderRow", kind=TypeKind.SHAPE),
        LogicalTypeIdentity(name="orderRow", kind=TypeKind.SHAPE),
    ),
)


@pytest.mark.parametrize(("expected", "actual"), _IDENTITY_MISMATCH_CASES)
def test_exact_logical_identity_binding_has_no_case_or_kind_coercion(
    expected: LogicalTypeIdentity,
    actual: LogicalTypeIdentity,
) -> None:
    mismatch = _assert_unsupported(
        bind_signature(_concrete_signature((expected,), BOOL), (actual,)),
        ConcreteTypeMismatch,
    )
    assert cast(ConcreteTypeMismatch, mismatch).actual == actual


@pytest.mark.parametrize(
    "case",
    (
        "omitted",
        "default",
        "supplied",
        "unbound",
        "optional-result",
        "two-omitted",
        "one-of-two",
    ),
)
def test_optional_trailing_parameter_binding_and_omission_is_exact(case: str) -> None:
    if case == "omitted":
        signature = _concrete_signature((INT, TEXT), BOOL, optional_from=1)
        result = cast(SignatureMatch, bind_signature(signature, (INT,)))
        assert result.omitted_positions == (1,)
    elif case == "default":
        signature = GenericSignature(
            type_variables=(),
            parameters=(
                SignatureParameter(
                    position=0,
                    type_expression=ConcreteTypeExpression(logical_type=INT),
                    optional=True,
                    default=ParameterDefault.OMITTED,
                ),
            ),
            result=ConcreteTypeExpression(logical_type=BOOL),
        )
        result = cast(SignatureMatch, bind_signature(signature, ()))
        assert result.omitted_positions == (0,)
    elif case == "supplied":
        signature = _concrete_signature((INT,), BOOL, optional_from=0)
        assert (
            cast(SignatureMatch, bind_signature(signature, (INT,))).omitted_positions
            == ()
        )
    elif case == "unbound":
        mismatch = _assert_unsupported(
            bind_signature(_variable_signature(optional=True), ()),
            UnboundResult,
        )
        assert cast(UnboundResult, mismatch).variable_name == "T"
    elif case == "optional-result":
        result = bind_signature(_variable_signature(optional=True), (TEXT,))
        assert cast(SignatureMatch, result).result_type == TEXT
    elif case == "two-omitted":
        signature = _concrete_signature((INT, TEXT), BOOL, optional_from=0)
        assert cast(
            SignatureMatch, bind_signature(signature, ())
        ).omitted_positions == (
            0,
            1,
        )
    else:
        signature = _concrete_signature((INT, TEXT, UUID), BOOL, optional_from=1)
        assert cast(
            SignatureMatch, bind_signature(signature, (INT, TEXT))
        ).omitted_positions == (2,)


_ARITY_CASES = (
    (_concrete_signature((INT,), BOOL), (), (1, 1, 0)),
    (_concrete_signature((INT,), BOOL), (INT, INT), (1, 1, 2)),
    (_concrete_signature((INT, TEXT, UUID), BOOL, optional_from=2), (INT,), (2, 3, 1)),
    (
        _concrete_signature((INT, TEXT, UUID), BOOL, optional_from=2),
        (INT, TEXT, UUID, BOOL),
        (2, 3, 4),
    ),
)


@pytest.mark.parametrize(("signature", "arguments", "expected"), _ARITY_CASES)
def test_arity_mismatch_evidence_is_exact(
    signature: GenericSignature,
    arguments: tuple[LogicalTypeIdentity, ...],
    expected: tuple[int, int, int],
) -> None:
    mismatch = cast(
        ArityMismatch,
        _assert_unsupported(bind_signature(signature, arguments), ArityMismatch),
    )
    assert (mismatch.minimum, mismatch.maximum, mismatch.actual) == expected


@pytest.mark.parametrize(
    "case",
    (
        "member-type",
        "unresolved",
        "concrete-precedence",
        "repeated-precedence",
        "constraint",
        "constraint-order",
        "unbound",
        "structured",
    ),
)
def test_binding_failures_are_structured_ordered_and_fail_closed(case: str) -> None:
    if case == "member-type":
        with pytest.raises(TypeError, match="exact LogicalTypeIdentity or None"):
            bind_signature(_variable_signature(), cast(Any, ("Int",)))
    elif case == "unresolved":
        mismatch = _assert_unsupported(
            bind_signature(_variable_signature(repeated=True), (None, FLOAT)),
            UnresolvedArgument,
        )
        assert cast(UnresolvedArgument, mismatch).parameter_position == 0
    elif case == "concrete-precedence":
        signature = _concrete_signature((INT, TEXT), BOOL)
        mismatch = _assert_unsupported(
            bind_signature(signature, (FLOAT, None)),
            ConcreteTypeMismatch,
        )
        assert cast(ConcreteTypeMismatch, mismatch).parameter_position == 0
    elif case == "repeated-precedence":
        signature = _variable_signature(
            (TypeConstraint.NUMERIC,),
            repeated=True,
        )
        mismatch = _assert_unsupported(
            bind_signature(signature, (TEXT, UUID)),
            RepeatedVariableMismatch,
        )
        assert cast(RepeatedVariableMismatch, mismatch).parameter_position == 1
    elif case == "constraint":
        mismatch = _assert_unsupported(
            bind_signature(_variable_signature((TypeConstraint.NUMERIC,)), (TEXT,)),
            ConstraintMismatch,
        )
        assert cast(ConstraintMismatch, mismatch).constraint is TypeConstraint.NUMERIC
    elif case == "constraint-order":
        signature = _variable_signature(
            (TypeConstraint.ORDERABLE, TypeConstraint.NUMERIC)
        )
        mismatch = cast(
            ConstraintMismatch,
            _assert_unsupported(bind_signature(signature, (TEXT,)), ConstraintMismatch),
        )
        assert mismatch.constraint is TypeConstraint.ORDERABLE
    elif case == "unbound":
        assert (
            type(
                _assert_unsupported(
                    bind_signature(_variable_signature(optional=True), ()),
                    UnboundResult,
                )
            )
            is UnboundResult
        )
    else:
        result = bind_signature(_concrete_signature((INT,), BOOL), (FLOAT,))
        assert type(result) is SignatureUnsupported
        assert type(result.mismatch) is ConcreteTypeMismatch


_CONSTRAINT_ORDER_CASES = (
    (
        INT,
        (
            TypeConstraint.SCALAR,
            TypeConstraint.COMPARABLE,
            TypeConstraint.ORDERABLE,
            TypeConstraint.NUMERIC,
        ),
    ),
    (
        DATE,
        (
            TypeConstraint.ORDERABLE,
            TypeConstraint.SCALAR,
            TypeConstraint.COMPARABLE,
        ),
    ),
    (BOOL, (TypeConstraint.COMPARABLE, TypeConstraint.SCALAR)),
    (DECIMAL, (TypeConstraint.NUMERIC, TypeConstraint.ORDERABLE)),
)


@pytest.mark.parametrize(("logical_type", "constraints"), _CONSTRAINT_ORDER_CASES)
def test_multiple_constraint_evidence_uses_declaration_order(
    logical_type: LogicalTypeIdentity,
    constraints: tuple[TypeConstraint, ...],
) -> None:
    result = cast(
        SignatureMatch,
        bind_signature(_variable_signature(constraints), (logical_type,)),
    )
    assert (
        tuple(evidence.constraint for evidence in result.constraint_evidence)
        == constraints
    )
    assert all(evidence.supported for evidence in result.constraint_evidence)
    assert all(
        evidence.parameter_position == 0 for evidence in result.constraint_evidence
    )


@pytest.mark.parametrize("case", ("concrete", "variable", "second", "unbound"))
def test_variable_and_concrete_result_resolution_is_exact(case: str) -> None:
    if case == "concrete":
        result = bind_signature(_variable_signature(result=BOOL), (INT,))
        assert cast(SignatureMatch, result).result_type == BOOL
    elif case == "variable":
        result = bind_signature(_variable_signature(), (DECIMAL,))
        assert cast(SignatureMatch, result).result_type == DECIMAL
    elif case == "second":
        variables = (
            TypeVariable(name="T", constraints=()),
            TypeVariable(name="U", constraints=()),
        )
        signature = GenericSignature(
            type_variables=variables,
            parameters=(
                SignatureParameter(
                    position=0,
                    type_expression=VariableTypeExpression(name="T"),
                ),
                SignatureParameter(
                    position=1,
                    type_expression=VariableTypeExpression(name="U"),
                ),
            ),
            result=VariableTypeExpression(name="U"),
        )
        assert (
            cast(SignatureMatch, bind_signature(signature, (INT, TEXT))).result_type
            == TEXT
        )
    else:
        assert (
            type(
                _assert_unsupported(
                    bind_signature(_variable_signature(optional=True), ()),
                    UnboundResult,
                )
            )
            is UnboundResult
        )


def test_binding_results_are_immutable_hashable_and_repeatable() -> None:
    signature = _variable_signature(
        (TypeConstraint.SCALAR, TypeConstraint.COMPARABLE),
        repeated=True,
    )
    first = bind_signature(signature, (INT, INT))
    second = bind_signature(signature, (INT, INT))
    assert first == second
    assert hash(first) == hash(second)
    assert type(first) is SignatureMatch
    with pytest.raises(FrozenInstanceError):
        setattr(first, "result_type", FLOAT)
    mismatch = bind_signature(signature, (INT, FLOAT))
    assert hash(mismatch)
    assert mismatch == bind_signature(signature, (INT, FLOAT))


@pytest.mark.parametrize("case", ("empty", "one", "order", "duplicate", "invalid"))
def test_overload_collection_preserves_order_and_duplicate_rows(case: str) -> None:
    int_signature = _concrete_signature((INT,), INT)
    text_signature = _concrete_signature((TEXT,), TEXT)
    if case == "empty":
        assert OverloadSet(signatures=()).signatures == ()
    elif case == "one":
        assert OverloadSet(signatures=(int_signature,)).signatures == (int_signature,)
    elif case == "order":
        value = OverloadSet(signatures=(text_signature, int_signature))
        assert value.signatures == (text_signature, int_signature)
    elif case == "duplicate":
        value = OverloadSet(signatures=(int_signature, int_signature))
        assert value.signatures == (int_signature, int_signature)
    else:
        with pytest.raises(TypeError, match="signatures must be an exact tuple"):
            OverloadSet(signatures=cast(Any, [int_signature]))
        with pytest.raises(TypeError, match="exact GenericSignature members"):
            OverloadSet(signatures=cast(Any, ("signature",)))


@pytest.mark.parametrize("case", ("empty", "match", "unsupported", "mixed"))
def test_overload_selection_match_and_unsupported_outcomes_are_exact(
    case: str,
) -> None:
    int_signature = _concrete_signature((INT,), INT)
    text_signature = _concrete_signature((TEXT,), TEXT)
    if case == "empty":
        selection = select_overload(OverloadSet(signatures=()), (INT,))
        assert selection == OverloadSelection(
            outcome=OverloadOutcome.UNSUPPORTED,
            evaluations=(),
        )
    elif case == "match":
        selection = select_overload(
            OverloadSet(signatures=(int_signature,)),
            (INT,),
        )
        assert selection.outcome is OverloadOutcome.MATCH
        assert type(selection.evaluations[0].result) is SignatureMatch
    elif case == "unsupported":
        selection = select_overload(
            OverloadSet(signatures=(text_signature,)),
            (INT,),
        )
        assert selection.outcome is OverloadOutcome.UNSUPPORTED
        assert type(selection.evaluations[0].result) is SignatureUnsupported
    else:
        selection = select_overload(
            OverloadSet(signatures=(text_signature, int_signature)),
            (INT,),
        )
        assert selection.outcome is OverloadOutcome.MATCH
        assert tuple(type(item.result) for item in selection.evaluations) == (
            SignatureUnsupported,
            SignatureMatch,
        )


@pytest.mark.parametrize(
    "case", ("duplicate", "generic", "indices", "three", "evidence")
)
def test_overload_ambiguity_preserves_every_matching_candidate_in_order(
    case: str,
) -> None:
    int_signature = _concrete_signature((INT,), INT)
    generic_signature = _variable_signature()
    mismatch_signature = _concrete_signature((TEXT,), TEXT)
    if case == "duplicate":
        signatures = (int_signature, int_signature)
    elif case == "generic":
        signatures = (generic_signature, int_signature)
    elif case == "indices":
        signatures = (int_signature, mismatch_signature, generic_signature)
    elif case == "three":
        signatures = (int_signature, generic_signature, int_signature)
    else:
        signatures = (mismatch_signature, generic_signature, int_signature)
    selection = select_overload(OverloadSet(signatures=signatures), (INT,))
    assert selection.outcome is OverloadOutcome.AMBIGUOUS
    assert tuple(item.index for item in selection.evaluations) == tuple(
        range(len(signatures))
    )
    assert (
        sum(type(item.result) is SignatureMatch for item in selection.evaluations) >= 2
    )


@pytest.mark.parametrize("case", ("specificity", "result", "reverse", "three"))
def test_overload_selection_has_no_first_match_or_tiebreaker(case: str) -> None:
    generic = _variable_signature()
    concrete_int = _concrete_signature((INT,), INT)
    concrete_bool = _concrete_signature((INT,), BOOL)
    if case == "specificity":
        signatures = (generic, concrete_int)
    elif case == "result":
        signatures = (concrete_int, concrete_bool)
    elif case == "reverse":
        signatures = (concrete_int, generic)
    else:
        signatures = (concrete_int, _concrete_signature((TEXT,), TEXT), generic)
    selection = select_overload(OverloadSet(signatures=signatures), (INT,))
    assert selection.outcome is OverloadOutcome.AMBIGUOUS
    assert tuple(item.index for item in selection.evaluations) == tuple(
        range(len(signatures))
    )


def test_phase52_capability_facts_are_evidence_not_compatibility_authority() -> None:
    source = SOURCE_PATH.read_text()
    for forbidden in (
        "capability_facts",
        "capability_lookup",
        "capability_inventory",
        "capability_signatures",
        "capability_contexts",
        "capability_aggregates",
        "Found",
        "Absent",
        "Conflict",
    ):
        assert forbidden not in source
    spec = SPEC_PATH.read_text()
    assert "Capability-fact Non-authority" in SPEC_H2
    assert "not compatibility or compiler-acceptance authority" in spec
    assert "does not consult capability lookup" in spec


def test_current_semantic_analyzer_and_window_paths_do_not_import_generic_compatibility() -> (
    None
):
    for relative in (
        "src/pietto/semantic/analyzer.py",
        "src/pietto/semantic/catalog.py",
        "src/pietto/semantic/expressions.py",
        "src/pietto/semantic/aggregates.py",
        "src/pietto/semantic/type_aliases.py",
        "src/pietto/_window_identity.py",
        "src/pietto/ast_nodes.py",
        "src/pietto/ast_builder.py",
    ):
        assert "generic_compatibility" not in (REPO_ROOT / relative).read_text()
    window_analysis = (REPO_ROOT / "src/pietto/semantic/window_analysis.py").read_text()
    assert "pietto.semantic.generic_compatibility import" in window_analysis
    assert "_RANKING_SIGNATURE = GenericSignature(" in window_analysis
    assert "_ROW_NUMBER_SIGNATURE = _RANKING_SIGNATURE" in window_analysis
    assert "bind_signature(signature, signature_arguments)" in window_analysis
    for identity in ("row_number", "rank", "dense_rank"):
        assert f'name="{identity}"' in window_analysis
    assert "PIE-S2103" in (REPO_ROOT / "src/pietto/semantic/expressions.py").read_text()


def test_nullability_phase5_and_phase64_exclusions_are_exact() -> None:
    source = SOURCE_PATH.read_text()
    assert "EffectiveNullability" not in source
    assert "DecimalPrecisionScale" not in source
    assert all(
        "nullability" not in field.name
        for carrier in (
            LogicalTypeIdentity,
            TypeVariable,
            SignatureParameter,
            GenericSignature,
            SignatureMatch,
        )
        for field in fields(carrier)
    )
    combined = SPEC_PATH.read_text() + PLAN_PATH.read_text()
    for required in (
        "Phase 53 Slice 5",
        "no coercion",
        "promotion",
        "LUB",
        "Decimal",
        "temporal conversion",
        "Phase 64",
    ):
        assert required in combined


def test_project_ir_sql_cli_serializer_and_public_exports_are_unchanged() -> None:
    for relative in (
        "src/pietto/_project/json_v2.py",
        "src/pietto/ir/__init__.py",
        "src/pietto/sql/__init__.py",
        "src/pietto/cli.py",
        "src/pietto/cli_json.py",
        "src/pietto/_metadata/serializer.py",
        "src/pietto/__init__.py",
        "src/pietto/semantic/__init__.py",
        "pyproject.toml",
        "uv.lock",
        ".github/workflows/ci.yml",
    ):
        assert _sha256(REPO_ROOT / relative) == PROTECTED_SHA256[relative]
    assert not hasattr(pietto, "select_overload")
    assert not hasattr(semantic_api, "select_overload")


def test_grammar_ast_generated_parser_and_window_identity_are_byte_locked() -> None:
    for relative in (
        "grammar/Pietto.g4",
        "src/pietto/ast_nodes.py",
        "src/pietto/ast_builder.py",
        "src/pietto/parser_api.py",
        "src/pietto/_window_identity.py",
    ):
        assert _sha256(REPO_ROOT / relative) == PROTECTED_SHA256[relative]
    generated = tuple(
        path
        for path in (REPO_ROOT / "src/pietto/generated").iterdir()
        if path.is_file()
    )
    assert len(generated) == 8
    assert _digest(generated) == (
        "9a84d108062bdbd87f5cd1d6e237e66f8bbb39d1d9d7674312eab6eb156cbad1"
    )


def test_reader_hash_inventory_and_nested_hash_closure_is_exact() -> None:
    repository_paths = _all_repository_paths()
    compiler_paths = (
        REPO_ROOT / "Makefile",
        REPO_ROOT / "grammar/Pietto.g4",
        *(
            REPO_ROOT / path
            for path in repository_paths
            if path.startswith("src/pietto/")
        ),
    )
    semantic_paths = tuple(
        REPO_ROOT / path
        for path in repository_paths
        if Path(path).parent.as_posix() == "src/pietto/semantic"
        and path.endswith(".py")
    )
    phase15_paths = tuple(
        path
        for path in semantic_paths
        if path.name not in {"analyzer.py", "model.py", "relationship_metadata.py"}
    )
    assert (len(compiler_paths), len(semantic_paths), len(phase15_paths)) == (
        105,
        36,
        33,
    )
    assert _digest(tuple(compiler_paths)) == FINAL_COMPILER_DIGEST
    assert _digest(semantic_paths) == FINAL_SEMANTIC_DIGEST
    assert _digest(phase15_paths) == FINAL_PHASE15_DIGEST
    assert _sha256(SOURCE_PATH) == FINAL_SOURCE_SHA256
    assert _sha256(SPEC_PATH) == FINAL_SPEC_SHA256
    assert _sha256(PLAN_PATH) == FINAL_PLAN_SHA256

    test_paths = tuple((REPO_ROOT / "tests").glob("test_*.py"))
    assert sum(FINAL_COMPILER_DIGEST in path.read_text() for path in test_paths) == 28
    assert sum(FINAL_SEMANTIC_DIGEST in path.read_text() for path in test_paths) == 42
    assert sum(FINAL_PHASE15_DIGEST in path.read_text() for path in test_paths) == 17
    assert (
        sum(
            f'BOUNDARY_HASH = "{FINAL_COMPILER_DIGEST}"' in path.read_text()
            for path in test_paths
        )
        == 8
    )


def test_slice4_dirty_clean_and_depth_one_repository_states_are_locked() -> None:
    if _phase54_active_gate2_is_active():
        return
    tracked = frozenset(_git("diff", "--name-only").splitlines()) - {""}
    untracked = frozenset(
        _git("ls-files", "--others", "--exclude-standard").splitlines()
    ) - {""}
    staged = _git("diff", "--cached", "--name-status")
    assert staged == ""
    if tracked or untracked:
        head = _git("rev-parse", "HEAD")
        if head in {
            PHASE54_SLICE2_BASE_HEAD,
            PHASE54_SLICE4_BASE_HEAD,
            PHASE54_SLICE5_BASE_HEAD,
            PHASE54_SLICE6_BASE_HEAD,
            PHASE54_SLICE7_BASE_HEAD,
            PHASE54_SLICE8_BASE_HEAD,
            PHASE54_SLICE9_BASE_HEAD,
        }:
            expected_modified, expected_added = _phase54_slice2_paths()
            expected_base = head
        else:
            expected_modified = frozenset(MODIFIED_PATHS)
            expected_added = frozenset(ADDED_PATHS)
            expected_base = BASE_HEAD
        assert tracked == expected_modified
        assert untracked == expected_added
        assert _git("branch", "--show-current") == "main"
        assert head == expected_base
        for reference in ("refs/heads/main", "refs/remotes/origin/main"):
            result = subprocess.run(
                ("git", "show-ref", "--verify", "--quiet", reference),
                cwd=REPO_ROOT,
                check=False,
            )
            if result.returncode == 0:
                assert _git("rev-parse", reference) == expected_base
    elif phase54_post_slice12_interlude_clean_topic_is_active():
        for reference in ("refs/heads/main", "refs/remotes/origin/main"):
            assert _git("rev-parse", reference) == PHASE54_POST_SLICE12_INTERLUDE_BASE
    else:
        head = _git("rev-parse", "HEAD")
        for reference in ("refs/heads/main", "refs/remotes/origin/main"):
            result = subprocess.run(
                ("git", "show-ref", "--verify", "--quiet", reference),
                cwd=REPO_ROOT,
                check=False,
            )
            if result.returncode == 0:
                assert _git("rev-parse", reference) == head


def test_test_inventory_focused_selector_and_dirty_overlay_are_exact() -> None:
    repository_paths = _all_repository_paths()
    python_paths = tuple(path for path in repository_paths if path.endswith(".py"))
    markdown_paths = tuple(path for path in repository_paths if path.endswith(".md"))
    test_paths = tuple(
        path
        for path in repository_paths
        if path.startswith("tests/test_") and path.endswith(".py")
    )
    top_level_functions = 0
    for relative in test_paths:
        tree = ast.parse((REPO_ROOT / relative).read_text())
        top_level_functions += sum(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
            for node in tree.body
        )
    assert (
        len(repository_paths),
        len(python_paths),
        len(markdown_paths),
        len(test_paths),
        top_level_functions,
    ) == (933, 571, 266, 462, 5330)
    self_tree = ast.parse(SELF_PATH.read_text())
    self_names = tuple(
        node.name
        for node in self_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert self_names == EXPECTED_TEST_NAMES
    assert len(EXPECTED_CARDINALITIES) == 31
    assert sum(EXPECTED_CARDINALITIES) == 190

    focused_payload = ("\n".join(FOCUSED_OPERANDS) + "\n").encode()
    assert (
        len(FOCUSED_OPERANDS),
        len({item.split("::", 1)[0] for item in FOCUSED_OPERANDS}),
        sum("::" not in item for item in FOCUSED_OPERANDS),
        sum("::" in item for item in FOCUSED_OPERANDS),
        len(focused_payload),
        hashlib.sha256(focused_payload).hexdigest(),
    ) == (
        134,
        80,
        14,
        120,
        15130,
        "fb685c521c70d879e0e3e751c434cf142700d82a66976961ca8036e8965b3429",
    )
    assert len(set(FOCUSED_OPERANDS)) == 134

    overlay_payload = ("\n".join(DIRTY_OVERLAY) + "\n").encode()
    assert (
        len(DIRTY_OVERLAY),
        len({item.split("::", 1)[0] for item in DIRTY_OVERLAY}),
        len(overlay_payload),
        hashlib.sha256(overlay_payload).hexdigest(),
    ) == (
        185,
        137,
        23628,
        "197b591aec962f43b9b9393da99a76ff21c3a36189cc02c7a75dc5a7b85d6b26",
    )
    assert len(set(DIRTY_OVERLAY)) == 185

    missing: list[str] = []
    for operand in (*FOCUSED_OPERANDS, *DIRTY_OVERLAY):
        normalized = operand.removeprefix("--deselect=")
        relative, *node_name = normalized.split("::", 1)
        if not node_name:
            continue
        tree = ast.parse((REPO_ROOT / relative).read_text())
        matches = [
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == node_name[0]
        ]
        if len(matches) != 1:
            missing.append(operand)
    assert missing == []


def test_validation_gate3_and_no_behavior_boundaries_are_locked() -> None:
    combined = " ".join((SPEC_PATH.read_text() + PLAN_PATH.read_text()).split())
    for required in (
        "A3/M73/D0",
        "4765 focused passes",
        "10599 passed / 185 deselected",
        "10784",
        "one write-mode Ruff invocation",
        "Slice 16 is `UNSTARTED`",
        "SLICE16_GATE0_GATE1",
        "Gate 3",
    ):
        assert required in combined
    metadata = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    assert metadata["project"]["version"] == "0.1.0"
    assert _git("tag", "--list") == ""
    assert (
        sum(path.is_file() for path in (REPO_ROOT / "src/pietto/generated").iterdir())
        == 8
    )
    assert len(tuple((REPO_ROOT / "tests/fixtures/golden").iterdir())) == 37


_SLICE10_READER_MIGRATION_PATHS = (
    "docs/spec/phase53-partition-binding-multi-key-visibility-diagnostics-contract-v1.md",
    "src/pietto/semantic/window_partition_analysis.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
)
# Phase 53 Slice 13 reader migration.
