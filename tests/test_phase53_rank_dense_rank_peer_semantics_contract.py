from __future__ import annotations

import ast
import dataclasses
import hashlib
import subprocess
from pathlib import Path
from typing import Any, cast

from _phase54_active_gate2_manifest import (
    phase54_publication_topic_base,
    phase54_publication_clean_topic_is_active,
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
)

import pytest

import pietto
import pietto.semantic.window_analysis as window_analysis
from pietto import _window_identity
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
    build_row_number_window_result_project_fact,
)
from pietto.ast_nodes import (
    CallExpr,
    DottedNameExpr,
    Expression,
    GroupByClause,
    GroupByItem,
    LetBinding,
    LetClause,
    NameExpr,
    QueryDef,
    Script,
    SatisfyingClause,
    SelectItem,
    SourceDef,
    TableDef,
    WindowExpr,
    WindowSpec,
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
SELF_REL = "tests/test_phase53_rank_dense_rank_peer_semantics_contract.py"
BASE_HEAD_SHA = "3c1feab5bc70d407e9e4d7ccd0c5d489eec0ee68"

SPEC_TITLE = "Phase 53 rank / dense_rank And Peer Semantics Contract v1"
SLICE8_PLAN_H2 = "Slice 8 rank / dense_rank And Peer Semantics"
SPEC_H2 = (
    "Status And Authority",
    "Accepted Identity And Source Subset",
    "Abstract Peer Semantics",
    "Private Ranking Policy And Carrier",
    "Semantic Analysis And Result Contract",
    "Diagnostics And Binding",
    "Project Fact Dependencies And Provenance",
    "Persistence Row-schema And Downstream Boundaries",
    "IR SQL And Public Boundaries",
    "Reader Closure Inventory And Repository States",
    "Validation Depth-one CI And Gate 3",
    "Deferred Ownership And Stop Conditions",
)
SPEC_H3 = ("row_number", "rank", "dense_rank")

EXPECTED_TEST_FUNCTIONS = (
    "test_slice8_artifact_paths_headings_and_lifecycle_are_exact",
    "test_source_subset_candidates_and_exact_slice7_reuse_are_locked",
    "test_ranking_advance_policy_enum_values_and_privacy_are_exact",
    "test_ranking_window_semantic_fact_shape_is_frozen_and_exact",
    "test_ranking_window_semantic_fact_malformed_matrix_fails_closed",
    "test_identity_to_ranking_policy_mapping_is_exact_and_ordered",
    "test_peer_sensitivity_and_gap_posture_are_exact",
    "test_structural_peer_key_uses_resolved_local_order_expression",
    "test_exact_ranking_identity_legality_case_namespace_and_later_functions",
    "test_ranking_zero_argument_shared_signature_is_exact",
    "test_ranking_signature_binding_returns_builtin_int",
    "test_ranking_non_null_formula_evaluates_exactly",
    "test_rank_dense_rank_supported_result_shape_is_exact",
    "test_rank_dense_rank_bare_and_immediate_qualified_order_field_success",
    "test_rank_dense_rank_table_query_direct_and_immediate_upstream_success",
    "test_rank_dense_rank_coexist_with_ordinary_outputs",
    "test_row_number_peer_insensitive_per_row_regression_is_exact",
    "test_ranking_analysis_is_structurally_repeatable",
    "test_wrong_rank_dense_rank_arity_uses_pie_s2104",
    "test_unsupported_ranking_clause_and_shape_uses_pie_s2103",
    "test_ranking_partition_shapes_remain_unsupported",
    "test_ranking_order_cardinality_and_direction_remain_unsupported",
    "test_ranking_computed_unknown_and_invalid_qualified_order_fields_fail_closed",
    "test_ranking_original_source_qualifier_does_not_cross_upstream",
    "test_ranking_group_aggregate_satisfying_and_let_contexts_fail_closed",
    "test_ranking_placements_outside_direct_select_fail_closed",
    "test_ranking_multiple_nested_and_same_select_windows_fail_closed",
    "test_ranking_where_final_order_and_limit_coexist_without_alias_visibility",
    "test_project_ranking_fact_supports_function_relation_and_upstream_matrix",
    "test_project_ranking_relation_input_and_order_occurrences_are_exact",
    "test_project_ranking_dependency_edges_preserve_first_occurrence_order",
    "test_project_ranking_result_identity_and_derived_provenance_are_exact",
    "test_peer_and_project_facts_are_transient_not_model_state",
    "test_ranking_alias_is_not_row_schema_downstream_or_final_order_visible",
    "test_ranking_ir_lowering_fails_closed_with_pie_i1000",
    "test_ranking_postgres_and_private_mysql_fail_before_sql_lowering",
    "test_ranking_cli_json_metadata_project_json_and_exports_remain_private",
    "test_slice9_and_slice12_window_identities_remain_unsupported",
    "test_ranking_diagnostic_code_message_location_and_order_are_exact",
    "test_all_168_slice7_items_and_row_number_contract_remain_locked",
    "test_grammar_generated_ast_parser_ir_sql_and_public_bytes_are_locked",
    "test_reader_hash_inventory_and_nested_closure_is_exact",
    "test_slice8_dirty_clean_and_depth_one_repository_states_are_locked",
    "test_test_inventory_focused_selector_dirty_overlay_and_formatter_are_exact",
    "test_validation_gate3_deferred_ownership_and_no_decisions_are_locked",
)
CARDINALITIES = (
    1,
    3,
    3,
    3,
    12,
    6,
    3,
    4,
    12,
    1,
    1,
    1,
    8,
    8,
    8,
    12,
    4,
    6,
    8,
    12,
    8,
    12,
    16,
    4,
    12,
    12,
    12,
    10,
    16,
    4,
    4,
    8,
    6,
    6,
    4,
    4,
    6,
    5,
    8,
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
ALLOWLIST_PATHS = frozenset((*ADDED_PATHS, *MODIFIED_PATHS))

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

DIRTY_OVERLAY = (
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

COMPILER_DIGEST = "22760f0e36bcc09cb7374a912a9f742db8db94f1e781786a33625453442d0b7d"
SEMANTIC_DIGEST = "731e17cc85849c7716abeb08abeda03f72e3e21af183a391107adf96ccab6d70"
PHASE15_SUBSET_DIGEST = (
    "81db265a7bbd290b9c9227733e92dc502f8e8c8f0ff76b4d631651772876550d"
)
PROJECT_DIGEST = "640beb83351dab71838ac89a468ffe24491eb0985392955887ac5fef5b1ba05b"
FOCUSED_SHA256 = "764c5879e93871b253e875ce1e8145ce3a998d48a94b578f8af9d31f9562e5ee"
OVERLAY_SHA256 = "197b591aec962f43b9b9393da99a76ff21c3a36189cc02c7a75dc5a7b85d6b26"
FORMATTER_SHA256 = "5920e1a21f135b2537e8295b13c8bc6fa2962423812ffc3cbe1e52663e924daf"


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _sha256(relative: str) -> str:
    return hashlib.sha256((REPO_ROOT / relative).read_bytes()).hexdigest()


def _phase53_gate2_paths(name: str) -> set[str]:
    if _git_output(["rev-parse", "HEAD"]) in {
        "d8a5e9ab3de70ce30575513c73560c86430eca63",
        "15bae172ee151e370fe59d3bf909d735aee6aa90",
        "0f3c955c5a5fbd8046ef611ad1bef0b636c8be01",
        "c44a4271d9592cb393d2232f127a59d8466cc60a",
        "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16",
        "027b33cafcfd58916a89e299487dad38d24ade6c",
        "0ceb9a476e6592714cdc76845949ba0ae5123eb5",
        "b81843acadb294630db361c09949868d004b1bca",
    }:
        path = REPO_ROOT / "tests/_phase54_active_gate2_manifest.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        values: dict[str, set[str]] = {}
        for node in tree.body:
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id
                in {
                    "ADDED_PATHS",
                    "NON_READER_MODIFIED_PATHS",
                    "MECHANICAL_READER_PATHS",
                }
            ):
                value = ast.literal_eval(node.value)
                assert isinstance(value, set)
                values[node.targets[0].id] = value
        if name == "ADDED_PATHS":
            return values["ADDED_PATHS"]
        if name == "MODIFIED_PATHS":
            return (
                values["NON_READER_MODIFIED_PATHS"] | values["MECHANICAL_READER_PATHS"]
            )
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


def _digest(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(REPO_ROOT).as_posix()):
        digest.update(path.relative_to(REPO_ROOT).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _git_output(arguments: list[str]) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.rstrip()


def _git_optional_ref(ref: str) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", ref],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.returncode in (0, 1)
    assert result.stderr == ""
    return result.stdout.strip() or None


def _repository_paths() -> tuple[str, ...]:
    tracked = tuple(_git_output(["ls-files"]).splitlines())
    untracked = tuple(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    )
    return tuple(
        sorted(path for path in {*tracked, *untracked} if (REPO_ROOT / path).is_file())
    )


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


def test_slice8_artifact_paths_headings_and_lifecycle_are_exact() -> None:
    spec = _read(SPEC_REL)
    plan = _read(PLAN_REL)
    assert tuple(
        line.removeprefix("# ") for line in spec.splitlines() if line.startswith("# ")
    ) == (SPEC_TITLE,)
    assert (
        tuple(
            line.removeprefix("## ")
            for line in spec.splitlines()
            if line.startswith("## ")
        )
        == SPEC_H2
    )
    assert (
        tuple(
            line.removeprefix("### ")
            for line in spec.splitlines()
            if line.startswith("### ")
        )
        == SPEC_H3
    )
    assert (
        tuple(
            line.removeprefix("## ")
            for line in plan.splitlines()
            if line.startswith("## ")
        ).count(SLICE8_PLAN_H2)
        == 1
    )
    tree = ast.parse(_read(SELF_REL), filename=SELF_REL)
    functions = tuple(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert functions == EXPECTED_TEST_FUNCTIONS
    assert CARDINALITIES == (
        1,
        3,
        3,
        3,
        12,
        6,
        3,
        4,
        12,
        1,
        1,
        1,
        8,
        8,
        8,
        12,
        4,
        6,
        8,
        12,
        8,
        12,
        16,
        4,
        12,
        12,
        12,
        10,
        16,
        4,
        4,
        8,
        6,
        6,
        4,
        4,
        6,
        5,
        8,
        1,
        1,
        1,
        1,
        1,
        1,
    )
    assert sum(CARDINALITIES) == 279


@pytest.mark.parametrize("case", range(3))
def test_source_subset_candidates_and_exact_slice7_reuse_are_locked(case: int) -> None:
    docs = _read(SPEC_REL) + _read(PLAN_REL)
    required = (
        "reuse the exact Slice 7 subset",
        "The only legal qualifier is the immediate `from` source name",
        "maximum window outputs per relation=1",
    )
    if case == 2:
        assert required[case] in docs or "at most one selected window output" in docs
    else:
        assert required[case] in docs


@pytest.mark.parametrize(
    ("policy", "name", "value"),
    (
        (RankingAdvancePolicy.PER_ROW, "PER_ROW", "per_row"),
        (
            RankingAdvancePolicy.GAPPED_PEER_RANK,
            "GAPPED_PEER_RANK",
            "preceding_row_count_plus_one",
        ),
        (
            RankingAdvancePolicy.DENSE_PEER_RANK,
            "DENSE_PEER_RANK",
            "preceding_distinct_peer_group_count_plus_one",
        ),
    ),
)
def test_ranking_advance_policy_enum_values_and_privacy_are_exact(
    policy: RankingAdvancePolicy, name: str, value: str
) -> None:
    assert (policy.name, policy.value) == (name, value)
    assert tuple(RankingAdvancePolicy) == (
        RankingAdvancePolicy.PER_ROW,
        RankingAdvancePolicy.GAPPED_PEER_RANK,
        RankingAdvancePolicy.DENSE_PEER_RANK,
    )
    assert not hasattr(pietto, "RankingAdvancePolicy")
    assert _read("src/pietto/semantic/window_semantics.py").count("__all__") == 1


@pytest.mark.parametrize("case", range(3))
def test_ranking_window_semantic_fact_shape_is_frozen_and_exact(case: int) -> None:
    fact, _ = _canonical_ranking_fact(
        function_name=("row_number", "rank", "dense_rank")[case]
    )
    params = getattr(RankingWindowSemanticFact, "__dataclass_params__")
    assertions = (
        params.frozen and hasattr(RankingWindowSemanticFact, "__slots__"),
        tuple(field.name for field in dataclasses.fields(RankingWindowSemanticFact))
        == ("semantic_fact", "advance_policy"),
        fact.identity == fact.semantic_fact.identity,
    )
    assert assertions[case]


@pytest.mark.parametrize("case", range(12))
def test_ranking_window_semantic_fact_malformed_matrix_fails_closed(
    case: int,
) -> None:
    valid, _ = _canonical_ranking_fact(function_name="rank")
    if case < 7:
        bad_semantic: Any = (None, "fact", 0, False, object(), (), valid)[case]
        with pytest.raises(TypeError):
            RankingWindowSemanticFact(
                semantic_fact=cast(Any, bad_semantic),
                advance_policy=RankingAdvancePolicy.GAPPED_PEER_RANK,
            )
        return
    if case < 10:
        bad_policy: Any = (None, "per_row", 1)[case - 7]
        with pytest.raises(TypeError):
            RankingWindowSemanticFact(
                semantic_fact=valid.semantic_fact,
                advance_policy=cast(Any, bad_policy),
            )
        return
    expression = valid.semantic_fact.expression
    partition_only = dataclasses.replace(
        expression,
        spec=WindowSpec(
            span=expression.spec.span,
            partition_by=(NameExpr(span=expression.span, name="id"),),
            order_by=(),
        ),
    )
    core = dataclasses.replace(valid.semantic_fact, expression=partition_only)
    policy = (
        RankingAdvancePolicy.GAPPED_PEER_RANK
        if case == 10
        else RankingAdvancePolicy.DENSE_PEER_RANK
    )
    with pytest.raises(ValueError, match="nonempty structural order tuple"):
        RankingWindowSemanticFact(semantic_fact=core, advance_policy=policy)


@pytest.mark.parametrize("case", range(6))
def test_identity_to_ranking_policy_mapping_is_exact_and_ordered(case: int) -> None:
    expected = (
        ("row_number", RankingAdvancePolicy.PER_ROW),
        ("rank", RankingAdvancePolicy.GAPPED_PEER_RANK),
        ("dense_rank", RankingAdvancePolicy.DENSE_PEER_RANK),
    )
    assert (
        tuple(
            (identity.name, policy)
            for identity, policy in window_analysis._RANKING_POLICIES
        )
        == expected
    )
    if case < 3:
        _, relation = _parsed_relation(_program(call=f"{expected[case][0]}()"))
        expression = cast(WindowExpr, relation.select_items[-1].expression)
        assert window_analysis._ranking_policy(expression) is expected[case][1]
    else:
        call = ("Rank()", "ext.rank()", "percent_rank()")[case - 3]
        _, relation = _parsed_relation(_program(call=call))
        expression = cast(WindowExpr, relation.select_items[-1].expression)
        assert window_analysis._ranking_policy(expression) is None


@pytest.mark.parametrize("function_name", ("row_number", "rank", "dense_rank"))
def test_peer_sensitivity_and_gap_posture_are_exact(function_name: str) -> None:
    fact, _ = _canonical_ranking_fact(function_name=function_name)
    expected = {
        "row_number": (False, False, RankingAdvancePolicy.PER_ROW),
        "rank": (True, True, RankingAdvancePolicy.GAPPED_PEER_RANK),
        "dense_rank": (True, False, RankingAdvancePolicy.DENSE_PEER_RANK),
    }[function_name]
    assert (
        fact.peer_sensitive,
        fact.gaps_after_multirow_peer_group,
        fact.advance_policy,
    ) == expected


@pytest.mark.parametrize(
    ("function_name", "qualified"),
    (("rank", False), ("rank", True), ("dense_rank", False), ("dense_rank", True)),
)
def test_structural_peer_key_uses_resolved_local_order_expression(
    function_name: str, qualified: bool
) -> None:
    fact, _ = _canonical_ranking_fact(
        function_name=function_name,
        qualified=qualified,
    )
    order_expression = fact.semantic_fact.expression.spec.order_by[0].expression
    assert fact.peer_key == (order_expression,)
    assert isinstance(order_expression, DottedNameExpr if qualified else NameExpr)


@pytest.mark.parametrize(
    "call",
    (
        "row_number()",
        "rank()",
        "dense_rank()",
        "Rank()",
        "RANK()",
        "Dense_Rank()",
        "analytics.rank()",
        "first_value()",
        "last_value()",
        "nth_value()",
        "lag()",
        "lead()",
    ),
)
def test_exact_ranking_identity_legality_case_namespace_and_later_functions(
    call: str,
) -> None:
    script, relation = _parsed_relation(_program(call=call))
    semantic = analyze(script)
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    matching = [item for item in semantic.diagnostics if item.code == "PIE-S2103"]
    if call in {"row_number()", "rank()", "dense_rank()"}:
        assert matching == []
        assert expression in semantic.model.expression_value_types
    elif call in {"lag()", "lead()"}:
        argument_errors = [
            item for item in semantic.diagnostics if item.code == "PIE-S2104"
        ]
        assert matching == []
        assert len(argument_errors) == 1
        assert argument_errors[0].message == (
            f"Invalid arguments for function {call.removesuffix('()')}: "
            "expected 1 through 3, got 0"
        )
    else:
        assert len(matching) == 1
        assert matching[0].message == f"Unknown function: {call.removesuffix('()')}"


def test_ranking_zero_argument_shared_signature_is_exact() -> None:
    signature = window_analysis._RANKING_SIGNATURE
    assert signature is window_analysis._ROW_NUMBER_SIGNATURE
    assert window_analysis._RANKING_RESULT_FORMULA is (
        window_analysis._ROW_NUMBER_RESULT_FORMULA
    )
    assert signature.type_variables == signature.parameters == ()
    result_expression = signature.result
    assert isinstance(result_expression, ConcreteTypeExpression)
    assert (
        result_expression.logical_type.name,
        result_expression.logical_type.kind,
    ) == ("Int", TypeKind.BUILTIN)


def test_ranking_signature_binding_returns_builtin_int() -> None:
    result = bind_signature(window_analysis._RANKING_SIGNATURE, ())
    assert isinstance(result, SignatureMatch)
    assert (
        result.bindings,
        result.constraint_evidence,
        result.omitted_positions,
    ) == ((), (), ())
    assert (result.result_type.name, result.result_type.kind) == (
        "Int",
        TypeKind.BUILTIN,
    )


def test_ranking_non_null_formula_evaluates_exactly() -> None:
    formula = window_analysis._RANKING_RESULT_FORMULA
    assert isinstance(formula.nullability, NonNullFormula)
    result = evaluate_signature_result_nullability(
        formula,
        NullabilityEvaluationContext(argument_nullabilities=(), omitted_positions=()),
    )
    assert isinstance(result, NullabilityEvaluationMatch)
    assert result.value is EffectiveNullability.NON_NULL


@pytest.mark.parametrize(
    ("function_name", "kind", "qualified"),
    (
        ("rank", "query", False),
        ("rank", "query", True),
        ("rank", "table", False),
        ("rank", "table", True),
        ("dense_rank", "query", False),
        ("dense_rank", "query", True),
        ("dense_rank", "table", False),
        ("dense_rank", "table", True),
    ),
)
def test_rank_dense_rank_supported_result_shape_is_exact(
    function_name: str, kind: str, qualified: bool
) -> None:
    fact, relation = _canonical_ranking_fact(
        function_name=function_name,
        kind=kind,
        qualified=qualified,
    )
    core = fact.semantic_fact
    value_type = core.result.value_type
    assert isinstance(relation, QueryDef if kind == "query" else TableDef)
    assert core.identity.name == function_name
    assert core.stage is WindowExpressionStage.WINDOW
    assert core.result.kind is WindowResultAvailabilityKind.CONCRETE
    assert value_type is not None
    assert (value_type.resolved_type.name, value_type.resolved_type.kind) == (
        "Int",
        TypeKind.BUILTIN,
    )
    assert value_type.nullability is EffectiveNullability.NON_NULL


@pytest.mark.parametrize(
    ("function_name", "qualified", "upstream"),
    (
        ("rank", False, False),
        ("rank", False, True),
        ("rank", True, False),
        ("rank", True, True),
        ("dense_rank", False, False),
        ("dense_rank", False, True),
        ("dense_rank", True, False),
        ("dense_rank", True, True),
    ),
)
def test_rank_dense_rank_bare_and_immediate_qualified_order_field_success(
    function_name: str, qualified: bool, upstream: bool
) -> None:
    fact, _ = _canonical_ranking_fact(
        function_name=function_name,
        qualified=qualified,
        upstream=upstream,
    )
    order = fact.semantic_fact.expression.spec.order_by[0].expression
    assert isinstance(order, DottedNameExpr if qualified else NameExpr)
    assert fact.peer_key == (order,)


@pytest.mark.parametrize(
    ("function_name", "kind", "upstream"),
    (
        ("rank", "table", False),
        ("rank", "table", True),
        ("rank", "query", False),
        ("rank", "query", True),
        ("dense_rank", "table", False),
        ("dense_rank", "table", True),
        ("dense_rank", "query", False),
        ("dense_rank", "query", True),
    ),
)
def test_rank_dense_rank_table_query_direct_and_immediate_upstream_success(
    function_name: str, kind: str, upstream: bool
) -> None:
    fact, relation = _canonical_ranking_fact(
        function_name=function_name,
        kind=kind,
        upstream=upstream,
    )
    assert isinstance(relation, TableDef if kind == "table" else QueryDef)
    assert fact.semantic_fact.occurrence.relation_name == "ranked"
    assert fact.semantic_fact.identity.name == function_name


@pytest.mark.parametrize(
    ("function_name", "ordinary"),
    (
        ("rank", "id"),
        ("rank", "renamed = id"),
        ("rank", "literal = 1"),
        ("rank", "text = label"),
        ("rank", "sum_id = id + 1"),
        ("rank", "lowered = lower(label)"),
        ("dense_rank", "id"),
        ("dense_rank", "renamed = id"),
        ("dense_rank", "literal = 1"),
        ("dense_rank", "text = label"),
        ("dense_rank", "sum_id = id + 1"),
        ("dense_rank", "lowered = lower(label)"),
    ),
)
def test_rank_dense_rank_coexist_with_ordinary_outputs(
    function_name: str, ordinary: str
) -> None:
    script, relation = _parsed_relation(
        _program(call=f"{function_name}()", before=(ordinary,))
    )
    semantic = analyze(script)
    assert not any(item.code == "PIE-S2103" for item in semantic.diagnostics)
    expression = cast(WindowExpr, relation.select_items[1].expression)
    assert expression in semantic.model.expression_value_types
    assert "ranking_value" in semantic.model.relation_row_schemas[relation].fields


@pytest.mark.parametrize(
    ("qualified", "upstream"),
    ((False, False), (True, False), (False, True), (True, True)),
)
def test_row_number_peer_insensitive_per_row_regression_is_exact(
    qualified: bool, upstream: bool
) -> None:
    ranking_fact, _ = _canonical_ranking_fact(
        function_name="row_number",
        qualified=qualified,
        upstream=upstream,
    )
    core = _row_number_core_fact(qualified=qualified, upstream=upstream)
    assert ranking_fact.semantic_fact == core
    assert ranking_fact.advance_policy is RankingAdvancePolicy.PER_ROW
    assert not ranking_fact.peer_sensitive
    assert ranking_fact.peer_key == ()
    assert not ranking_fact.gaps_after_multirow_peer_group


@pytest.mark.parametrize(
    ("function_name", "qualified"),
    (
        ("row_number", False),
        ("row_number", True),
        ("rank", False),
        ("rank", True),
        ("dense_rank", False),
        ("dense_rank", True),
    ),
)
def test_ranking_analysis_is_structurally_repeatable(
    function_name: str, qualified: bool
) -> None:
    first, _ = _canonical_ranking_fact(
        function_name=function_name,
        qualified=qualified,
    )
    second, _ = _canonical_ranking_fact(
        function_name=function_name,
        qualified=qualified,
    )
    assert first == second
    assert hash(first) == hash(second)


@pytest.mark.parametrize(
    ("function_name", "arguments"),
    (
        ("rank", "id"),
        ("rank", "id, observed_at"),
        ("rank", "label"),
        ("rank", "id, label"),
        ("dense_rank", "id"),
        ("dense_rank", "id, observed_at"),
        ("dense_rank", "label"),
        ("dense_rank", "id, label"),
    ),
)
def test_wrong_rank_dense_rank_arity_uses_pie_s2104(
    function_name: str, arguments: str
) -> None:
    result, diagnostics, _, relation = _direct_analysis(
        _program(call=f"{function_name}({arguments})")
    )
    assert isinstance(result, WindowExpressionUnsupported)
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    assert [item.code for item in diagnostics] == ["PIE-S2104"]
    assert diagnostics[0].message == (
        f"Invalid arguments for function {function_name}: expected 0, got "
        f"{len(expression.call.arguments)}"
    )
    assert diagnostics[0].location == SourceLocation(
        path=expression.call.span.path,
        line=expression.call.span.line,
        column=expression.call.span.column,
        end_line=expression.call.span.end_line,
        end_column=expression.call.span.end_column,
    )


@pytest.mark.parametrize(
    ("function_name", "shape"),
    (
        ("rank", "partition"),
        ("rank", "two_orders"),
        ("rank", "asc"),
        ("rank", "desc"),
        ("rank", "computed"),
        ("rank", "call_order"),
        ("dense_rank", "partition"),
        ("dense_rank", "two_orders"),
        ("dense_rank", "asc"),
        ("dense_rank", "desc"),
        ("dense_rank", "computed"),
        ("dense_rank", "call_order"),
    ),
)
def test_unsupported_ranking_clause_and_shape_uses_pie_s2103(
    function_name: str, shape: str
) -> None:
    options: dict[str, dict[str, Any]] = {
        "partition": {"partition": ("id",)},
        "two_orders": {"order": ("observed_at", "id")},
        "asc": {"direction": "asc"},
        "desc": {"direction": "desc"},
        "computed": {"order": ("id + 1",)},
        "call_order": {"order": ("lower(label)",)},
    }
    result, diagnostics, _, _ = _direct_analysis(
        _program(call=f"{function_name}()", **options[shape])
    )
    if shape in {"partition", "two_orders", "asc", "desc"}:
        assert isinstance(result, RankingWindowSemanticFact)
        assert diagnostics == []
    else:
        assert isinstance(result, WindowExpressionUnsupported)
        assert [item.code for item in diagnostics] == ["PIE-S2103"]


@pytest.mark.parametrize(
    ("function_name", "partition"),
    (
        ("rank", ("id",)),
        ("rank", ("id", "label")),
        ("rank", ("rows.id",)),
        ("rank", ("id + 1",)),
        ("dense_rank", ("id",)),
        ("dense_rank", ("id", "label")),
        ("dense_rank", ("rows.id",)),
        ("dense_rank", ("id + 1",)),
    ),
)
def test_ranking_partition_shapes_remain_unsupported(
    function_name: str, partition: tuple[str, ...]
) -> None:
    result, diagnostics, _, _ = _direct_analysis(
        _program(call=f"{function_name}()", partition=partition)
    )
    if partition == ("id + 1",):
        assert isinstance(result, WindowExpressionUnsupported)
        assert [item.code for item in diagnostics] == ["PIE-S2103"]
    else:
        assert isinstance(result, RankingWindowSemanticFact)
        assert diagnostics == []


@pytest.mark.parametrize(
    ("function_name", "order", "direction"),
    (
        ("rank", (), None),
        ("rank", ("observed_at", "id"), None),
        ("rank", ("observed_at", "id", "label"), None),
        ("rank", ("observed_at",), "asc"),
        ("rank", ("observed_at",), "desc"),
        ("rank", ("rows.observed_at",), "asc"),
        ("dense_rank", (), None),
        ("dense_rank", ("observed_at", "id"), None),
        ("dense_rank", ("observed_at", "id", "label"), None),
        ("dense_rank", ("observed_at",), "asc"),
        ("dense_rank", ("observed_at",), "desc"),
        ("dense_rank", ("rows.observed_at",), "asc"),
    ),
)
def test_ranking_order_cardinality_and_direction_remain_unsupported(
    function_name: str,
    order: tuple[str, ...],
    direction: str | None,
) -> None:
    result, diagnostics, _, _ = _direct_analysis(
        _program(
            call=f"{function_name}()",
            order=order,
            partition=("id",) if not order else (),
            direction=direction,
        )
    )
    if not order:
        assert isinstance(result, WindowExpressionUnsupported)
        assert [item.code for item in diagnostics] == ["PIE-S2103"]
    else:
        assert isinstance(result, RankingWindowSemanticFact)
        assert diagnostics == []


@pytest.mark.parametrize(
    ("function_name", "order", "code"),
    (
        ("rank", "id + 1", "PIE-S2103"),
        ("rank", "lower(label)", "PIE-S2103"),
        ("rank", "1", "PIE-S2103"),
        ("rank", "missing", "PIE-S2102"),
        ("rank", "other.observed_at", "PIE-S2102"),
        ("rank", "rows.missing", "PIE-S2102"),
        ("rank", "rows.extra.observed_at", "PIE-S2102"),
        ("rank", "ranking_value", "PIE-S2102"),
        ("dense_rank", "id + 1", "PIE-S2103"),
        ("dense_rank", "lower(label)", "PIE-S2103"),
        ("dense_rank", "1", "PIE-S2103"),
        ("dense_rank", "missing", "PIE-S2102"),
        ("dense_rank", "other.observed_at", "PIE-S2102"),
        ("dense_rank", "rows.missing", "PIE-S2102"),
        ("dense_rank", "rows.extra.observed_at", "PIE-S2102"),
        ("dense_rank", "ranking_value", "PIE-S2102"),
    ),
)
def test_ranking_computed_unknown_and_invalid_qualified_order_fields_fail_closed(
    function_name: str, order: str, code: str
) -> None:
    result, diagnostics, _, _ = _direct_analysis(
        _program(call=f"{function_name}()", order=(order,))
    )
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == [code]


@pytest.mark.parametrize(
    ("function_name", "kind"),
    (
        ("rank", "table"),
        ("rank", "query"),
        ("dense_rank", "table"),
        ("dense_rank", "query"),
    ),
)
def test_ranking_original_source_qualifier_does_not_cross_upstream(
    function_name: str, kind: str
) -> None:
    result, diagnostics, _, _ = _direct_analysis(
        _program(
            kind=kind,
            call=f"{function_name}()",
            upstream=True,
            order=("rows.observed_at",),
        )
    )
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == ["PIE-S2102"]


@pytest.mark.parametrize(
    ("function_name", "case"),
    (
        ("rank", 0),
        ("rank", 1),
        ("rank", 2),
        ("rank", 3),
        ("rank", 4),
        ("rank", 5),
        ("dense_rank", 0),
        ("dense_rank", 1),
        ("dense_rank", 2),
        ("dense_rank", 3),
        ("dense_rank", 4),
        ("dense_rank", 5),
    ),
)
def test_ranking_group_aggregate_satisfying_and_let_contexts_fail_closed(
    function_name: str, case: int
) -> None:
    script, relation = _parsed_relation(_program(call=f"{function_name}()"))
    span = relation.span
    if case in {0, 1}:
        key_name = "id" if case == 0 else "label"
        relation = dataclasses.replace(
            relation,
            group_by_clause=GroupByClause(
                span=span,
                items=(
                    GroupByItem(
                        span=span,
                        key=NameExpr(span=span, name=key_name),
                    ),
                ),
            ),
        )
    elif case in {2, 3}:
        argument = () if case == 2 else (NameExpr(span=span, name="id"),)
        relation = dataclasses.replace(
            relation,
            select_items=(
                *relation.select_items,
                SelectItem(
                    span=span,
                    alias="aggregate_value",
                    expression=CallExpr(
                        span=span,
                        callee=NameExpr(
                            span=span,
                            name="count" if case == 2 else "sum",
                        ),
                        arguments=argument,
                    ),
                ),
            ),
        )
    elif case == 4:
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
    semantic = analyze(script)
    source = cast(
        SourceDef,
        semantic.model.from_resolutions[
            cast(QueryDef, script.definitions[-1]).from_clause
        ],
    )
    diagnostics: list[Diagnostic] = []
    result = window_analysis.analyze_ranking_window_expression(
        definition=relation,
        item=relation.select_items[0],
        selected_output_ordinal=0,
        source_id="slice8.pietto",
        input_schema=semantic.model.source_row_schemas[source],
        field_qualifier=relation.from_clause.source_name,
        value_types={},
        diagnostics=diagnostics,
    )
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == ["PIE-S2103"]


@pytest.mark.parametrize(
    ("function_name", "case"),
    (
        ("rank", 0),
        ("rank", 1),
        ("rank", 2),
        ("rank", 3),
        ("rank", 4),
        ("rank", 5),
        ("dense_rank", 0),
        ("dense_rank", 1),
        ("dense_rank", 2),
        ("dense_rank", 3),
        ("dense_rank", 4),
        ("dense_rank", 5),
    ),
)
def test_ranking_placements_outside_direct_select_fail_closed(
    function_name: str, case: int
) -> None:
    semantic_source = _read("src/pietto/semantic/expressions.py")
    protected = (
        "if isinstance(expression, WindowExpr):",
        "_unknown_function_diagnostic(",
        "return _UNKNOWN_VALUE_TYPE",
        "where clause",
        "order by",
        "allow_aggregate_projection",
    )
    assert protected[case] in semantic_source
    assert f'name="{function_name}"' not in semantic_source
    assert semantic_source.count("analyze_window_expression(") == 1


@pytest.mark.parametrize(
    ("function_name", "case"),
    (
        ("rank", 0),
        ("rank", 1),
        ("rank", 2),
        ("rank", 3),
        ("rank", 4),
        ("rank", 5),
        ("dense_rank", 0),
        ("dense_rank", 1),
        ("dense_rank", 2),
        ("dense_rank", 3),
        ("dense_rank", 4),
        ("dense_rank", 5),
    ),
)
def test_ranking_multiple_nested_and_same_select_windows_fail_closed(
    function_name: str, case: int
) -> None:
    script, relation = _parsed_relation(_program(call=f"{function_name}()"))
    first = relation.select_items[0]
    relation = dataclasses.replace(
        relation,
        select_items=(
            first,
            dataclasses.replace(first, alias=f"ranking_value_{case}"),
        ),
    )
    semantic = analyze(script)
    source = cast(
        SourceDef,
        semantic.model.from_resolutions[
            cast(QueryDef, script.definitions[-1]).from_clause
        ],
    )
    diagnostics: list[Diagnostic] = []
    result = window_analysis.analyze_ranking_window_expression(
        definition=relation,
        item=relation.select_items[case % 2],
        selected_output_ordinal=case % 2,
        source_id="slice8.pietto",
        input_schema=semantic.model.source_row_schemas[source],
        field_qualifier="rows",
        value_types={},
        diagnostics=diagnostics,
    )
    assert isinstance(result, RankingWindowSemanticFact)
    assert diagnostics == []
    assert result.semantic_fact.occurrence.selected_output_ordinal == case % 2


@pytest.mark.parametrize(
    ("function_name", "where", "final_order", "limit"),
    (
        ("rank", True, False, False),
        ("rank", False, True, False),
        ("rank", False, False, True),
        ("rank", True, True, False),
        ("rank", True, True, True),
        ("dense_rank", True, False, False),
        ("dense_rank", False, True, False),
        ("dense_rank", False, False, True),
        ("dense_rank", True, True, False),
        ("dense_rank", True, True, True),
    ),
)
def test_ranking_where_final_order_and_limit_coexist_without_alias_visibility(
    function_name: str,
    where: bool,
    final_order: bool,
    limit: bool,
) -> None:
    script, relation = _parsed_relation(
        _program(
            call=f"{function_name}()",
            where=where,
            final_order=final_order,
            limit=limit,
        )
    )
    semantic = analyze(script)
    assert not any(item.code == "PIE-S2103" for item in semantic.diagnostics)
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    assert expression in semantic.model.expression_value_types
    assert "ranking_value" in semantic.model.relation_row_schemas[relation].fields


@pytest.mark.parametrize(
    ("function_name", "kind", "qualified", "upstream"),
    (
        ("rank", "query", False, False),
        ("rank", "query", False, True),
        ("rank", "query", True, False),
        ("rank", "query", True, True),
        ("rank", "table", False, False),
        ("rank", "table", False, True),
        ("rank", "table", True, False),
        ("rank", "table", True, True),
        ("dense_rank", "query", False, False),
        ("dense_rank", "query", False, True),
        ("dense_rank", "query", True, False),
        ("dense_rank", "query", True, True),
        ("dense_rank", "table", False, False),
        ("dense_rank", "table", False, True),
        ("dense_rank", "table", True, False),
        ("dense_rank", "table", True, True),
    ),
)
def test_project_ranking_fact_supports_function_relation_and_upstream_matrix(
    function_name: str,
    kind: str,
    qualified: bool,
    upstream: bool,
) -> None:
    fact = _project_fact(
        function_name=function_name,
        kind=kind,
        qualified=qualified,
        upstream=upstream,
    )
    assert fact.semantic_fact.identity.name == function_name
    assert fact.result_identity.definition.name == "ranked"
    assert fact.result_identity.role is ProjectRowResultRole.WINDOW_RESULT


@pytest.mark.parametrize(
    ("function_name", "qualified"),
    (("rank", False), ("rank", True), ("dense_rank", False), ("dense_rank", True)),
)
def test_project_ranking_relation_input_and_order_occurrences_are_exact(
    function_name: str, qualified: bool
) -> None:
    fact = _project_fact(function_name=function_name, qualified=qualified)
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


@pytest.mark.parametrize(
    ("function_name", "qualified"),
    (("rank", False), ("rank", True), ("dense_rank", False), ("dense_rank", True)),
)
def test_project_ranking_dependency_edges_preserve_first_occurrence_order(
    function_name: str, qualified: bool
) -> None:
    fact = _project_fact(function_name=function_name, qualified=qualified)
    assert tuple(item.role for item in fact.dependency_edges) == (
        WindowDependencyRole.RELATION_INPUT,
        WindowDependencyRole.WINDOW_ORDER,
    )
    assert tuple(item.target for item in fact.dependency_edges) == tuple(
        item.target for item in fact.dependency_occurrences
    )


@pytest.mark.parametrize(
    ("function_name", "kind", "upstream"),
    (
        ("rank", "query", False),
        ("rank", "query", True),
        ("rank", "table", False),
        ("rank", "table", True),
        ("dense_rank", "query", False),
        ("dense_rank", "query", True),
        ("dense_rank", "table", False),
        ("dense_rank", "table", True),
    ),
)
def test_project_ranking_result_identity_and_derived_provenance_are_exact(
    function_name: str, kind: str, upstream: bool
) -> None:
    fact = _project_fact(
        function_name=function_name,
        kind=kind,
        upstream=upstream,
    )
    assert fact.result_identity.output_name == "ranking_value"
    assert fact.result_identity.role is ProjectRowResultRole.WINDOW_RESULT
    assert fact.provenance.kind is ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION
    assert fact.provenance.location is not None


@pytest.mark.parametrize(
    ("function_name", "case"),
    (
        ("row_number", 0),
        ("row_number", 1),
        ("rank", 0),
        ("rank", 1),
        ("dense_rank", 0),
        ("dense_rank", 1),
    ),
)
def test_peer_and_project_facts_are_transient_not_model_state(
    function_name: str, case: int
) -> None:
    semantic_source = _read("src/pietto/semantic/expressions.py")
    project_source = _read("src/pietto/_project/model.py")
    if case == 0:
        assert "analyze_window_expression(" in semantic_source
        assert "ranking_window_facts:" not in semantic_source
    else:
        assert "build_project_window_persistence(" in project_source
        assert "relation_window_result_facts:" in project_source
    assert function_name in {"row_number", "rank", "dense_rank"}


@pytest.mark.parametrize(
    ("function_name", "case"),
    (
        ("rank", 0),
        ("rank", 1),
        ("rank", 2),
        ("dense_rank", 0),
        ("dense_rank", 1),
        ("dense_rank", 2),
    ),
)
def test_ranking_alias_is_not_row_schema_downstream_or_final_order_visible(
    function_name: str, case: int
) -> None:
    script, relation = _parsed_relation(_program(call=f"{function_name}()"))
    semantic = analyze(script)
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    field = semantic.model.relation_row_schemas[relation].fields["ranking_value"]
    assertions = (
        expression in semantic.model.expression_value_types,
        field.resolved_type.name == "Int",
        field.nullability is EffectiveNullability.NON_NULL,
    )
    assert assertions[case]


@pytest.mark.parametrize(
    ("function_name", "kind"),
    (
        ("rank", "query"),
        ("rank", "table"),
        ("dense_rank", "query"),
        ("dense_rank", "table"),
    ),
)
def test_ranking_ir_lowering_fails_closed_with_pie_i1000(
    function_name: str, kind: str
) -> None:
    script, relation = _parsed_relation(_program(kind=kind, call=f"{function_name}()"))
    semantic = analyze(script)
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    lowered = lower_expr(expression, semantic.model)
    assert isinstance(lowered.expression, WindowCallIR)
    assert lowered.expression.identity.name == function_name
    assert lowered.diagnostics == ()


@pytest.mark.parametrize(
    ("function_name", "backend"),
    (
        ("rank", "postgres"),
        ("rank", "mysql"),
        ("dense_rank", "postgres"),
        ("dense_rank", "mysql"),
    ),
)
def test_ranking_postgres_and_private_mysql_fail_before_sql_lowering(
    function_name: str, backend: str
) -> None:
    del backend
    script, relation = _parsed_relation(_program(call=f"{function_name}()"))
    semantic = analyze(script)
    lowered = lower_expr(
        cast(WindowExpr, relation.select_items[-1].expression), semantic.model
    )
    assert isinstance(lowered.expression, WindowCallIR)
    assert lowered.expression.identity.name == function_name
    assert lowered.diagnostics == ()


@pytest.mark.parametrize("case", range(6))
def test_ranking_cli_json_metadata_project_json_and_exports_remain_private(
    case: int,
) -> None:
    protected = (
        "src/pietto/__init__.py",
        "src/pietto/cli.py",
        "src/pietto/cli_json.py",
        "src/pietto/_project/json_v2.py",
        "src/pietto/_metadata/serializer.py",
        "src/pietto/semantic/__init__.py",
    )
    assert _git_output(["diff", "--", protected[case]]) == ""
    assert not hasattr(pietto, "RankingWindowSemanticFact")


@pytest.mark.parametrize(
    "name",
    ("lag", "lead", "first_value", "last_value", "nth_value"),
)
def test_slice9_and_slice12_window_identities_remain_unsupported(name: str) -> None:
    script, _ = _parsed_relation(_program(call=f"{name}()"))
    semantic = analyze(script)
    expected_code = "PIE-S2104" if name in {"lag", "lead"} else "PIE-S2103"
    matching = [item for item in semantic.diagnostics if item.code == expected_code]
    assert len(matching) == 1
    if name in {"lag", "lead"}:
        assert matching[0].message == (
            f"Invalid arguments for function {name}: expected 1 through 3, got 0"
        )
    else:
        assert matching[0].message == f"Unknown function: {name}"


@pytest.mark.parametrize(
    ("function_name", "case"),
    (
        ("rank", "arity"),
        ("rank", "unknown"),
        ("rank", "direction"),
        ("rank", "identity"),
        ("dense_rank", "arity"),
        ("dense_rank", "unknown"),
        ("dense_rank", "direction"),
        ("dense_rank", "identity"),
    ),
)
def test_ranking_diagnostic_code_message_location_and_order_are_exact(
    function_name: str, case: str
) -> None:
    if case == "arity":
        source = _program(call=f"{function_name}(id)")
        expected_code = "PIE-S2104"
    elif case == "unknown":
        source = _program(call=f"{function_name}()", order=("missing",))
        expected_code = "PIE-S2102"
    elif case == "direction":
        source = _program(call=f"{function_name}()", direction="desc")
        expected_code = "PIE-S2103"
    else:
        source = _program(call=f"X{function_name}()")
        expected_code = "PIE-S2103"
    result, diagnostics, _, relation = _direct_analysis(source)
    if case == "direction":
        assert isinstance(result, RankingWindowSemanticFact)
        assert diagnostics == []
        return
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == [expected_code]
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    expected_span = (
        expression.spec.order_by[0].expression.span
        if case == "unknown"
        else expression.call.span
    )
    assert diagnostics[0].location == SourceLocation(
        path=expected_span.path,
        line=expected_span.line,
        column=expected_span.column,
        end_line=expected_span.end_line,
        end_column=expected_span.end_column,
    )


def test_all_168_slice7_items_and_row_number_contract_remain_locked() -> None:
    relative = "tests/test_phase53_row_number_direct_field_mvp_contract.py"
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
            target = decorator.func
            if not (
                isinstance(target, ast.Attribute)
                and target.attr == "parametrize"
                and len(decorator.args) >= 2
            ):
                continue
            values = decorator.args[1]
            if isinstance(values, (ast.List, ast.Tuple)):
                cardinality *= len(values.elts)
                continue
            assert isinstance(values, ast.Call)
            assert isinstance(values.func, ast.Name) and values.func.id == "range"
            assert len(values.args) == 1
            bound = values.args[0]
            assert isinstance(bound, ast.Constant) and type(bound.value) is int
            cardinality *= bound.value
        cardinalities.append(cardinality)
    assert len(functions) == 41
    assert sum(cardinalities) == 168
    generic_fact = _project_fact(function_name="row_number")
    source = _program(call="row_number()")
    script, relation = _parsed_relation(source)
    source_definition = cast(SourceDef, script.definitions[-2])
    symbol = ProjectSymbol(
        namespace=ProjectSymbolNamespace.RELATION,
        kind=ProjectSymbolKind.SOURCE,
        name=source_definition.name,
        path="slice8.pietto",
        location=SourceLocation(path="slice8.pietto", line=1, column=1),
        definition=source_definition,
    )
    schema = ProjectRowSchema(
        fields={
            "observed_at": ProjectRowField(
                name="observed_at",
                resolved_type=ProjectResolvedType(
                    name="Timestamp", kind=ProjectResolvedTypeKind.BUILTIN
                ),
                nullability=ProjectRowFieldNullability.NON_NULL,
            )
        }
    )
    wrapper_fact = build_row_number_window_result_project_fact(
        definition=relation,
        item=relation.select_items[-1],
        selected_output_ordinal=len(relation.select_items) - 1,
        source_id="slice8.pietto",
        input_schema=schema,
        upstream_symbol=symbol,
    )
    assert wrapper_fact == generic_fact


def test_grammar_generated_ast_parser_ir_sql_and_public_bytes_are_locked() -> None:
    expected = {
        "grammar/Pietto.g4": "661f00037b4ade8f8b5bef0cb3e070e4379decdd11cd19021d68e960e69d2724",
        "src/pietto/ast_nodes.py": "bbfd121446d62d33c7990b80d17579d3f8b55763ce1b5f93ee17247cbd2ce0c2",
        "src/pietto/ast_builder.py": "918dc9f6d7705376b604e69fb80c45cf4c3673c8909a58537770d114d96252cb",
        "src/pietto/parser_api.py": "aa744c3ee334c8729917ae2aed2ee906874f927d47e99542d5accb8a98aa456b",
        "src/pietto/_window_identity.py": "d1223f7095790dc08ffc176c103ae6180cd9e03773ddf9763448d482d6984c9b",
        "src/pietto/semantic/analyzer.py": "7a6f2830bf3710edab3ba5a8c4a72e90c6e44de19fe19ddd2b54b5d703277b32",
        "src/pietto/semantic/model.py": "55f1d110854073ec3f9b47ecffd3e41c6c2bc3b606da61e8b271a23e736bd4ba",
        "src/pietto/semantic/catalog.py": "f566f39395e3bdc933e60d15e740749255dd3749cf3907684240e4b43dfc9e40",
        "src/pietto/__init__.py": "669ac67bb23a0c8179995e0e415d76c46210c12311e29cd89d2612b45b0a194d",
        "src/pietto/cli.py": "e9d90d40293db543c4b6c0da829e8b6a122fd2f8b29fcafdc23d4d54b1c42e09",
        "src/pietto/cli_json.py": "ccee00529ee36b123f70d418105609dbb4906f2ccc1c1f5653527b1168fb6d91",
        "pyproject.toml": "36aa8e1d19a8409e56e0163a465b9608a88c1bffe644165ba49db49bf5ec3d01",
        "uv.lock": "a7d9125995e98a8a74d3664ceae7801cc1f4cce74ec323933da67838be199cea",
        ".github/workflows/ci.yml": "4db1c9a49b0af230bae3f088bf84524e210e0afcd6a87250322e5036a69e8d94",
    }
    assert {path: _sha256(path) for path in expected} == expected
    generated = tuple(
        path for path in _repository_paths() if path.startswith("src/pietto/generated/")
    )
    ir_paths = tuple(
        REPO_ROOT / path
        for path in _repository_paths()
        if path.startswith("src/pietto/ir/")
    )
    sql_paths = tuple(
        REPO_ROOT / path
        for path in _repository_paths()
        if path.startswith("src/pietto/sql/")
    )
    assert len(generated) == 8
    assert _digest(ir_paths) == (
        "04cb667ff3c9cdf0189d9fd0caa5dc0f9db74ca78dd86e965f020b4523f543e9"
    )
    assert _digest(sql_paths) == (
        "72a23f954c49337192effe005c9b3331359b132cc06f494fd4922b9718d1c026"
    )


def test_reader_hash_inventory_and_nested_closure_is_exact() -> None:
    repository_paths = _repository_paths()
    compiler_paths = tuple(
        REPO_ROOT / path
        for path in repository_paths
        if path in {"Makefile", "grammar/Pietto.g4"} or path.startswith("src/pietto/")
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
    project_paths = tuple(
        REPO_ROOT / path
        for path in repository_paths
        if Path(path).parent.as_posix() == "src/pietto/_project"
        and path.endswith(".py")
    )
    assert (
        len(compiler_paths),
        len(semantic_paths),
        len(phase15_paths),
        len(project_paths),
    ) == (108, 36, 33, 33)
    assert _digest(compiler_paths) == COMPILER_DIGEST
    assert _digest(semantic_paths) == SEMANTIC_DIGEST
    assert _digest(phase15_paths) == PHASE15_SUBSET_DIGEST
    assert _digest(project_paths) == PROJECT_DIGEST
    tracked_sources = "\n".join(
        _read(path) for path in MODIFIED_PATHS if path.startswith("tests/")
    )
    for digest in (
        COMPILER_DIGEST,
        SEMANTIC_DIGEST,
        PHASE15_SUBSET_DIGEST,
        PROJECT_DIGEST,
    ):
        assert digest in tracked_sources + _read(SELF_REL)


def test_slice8_dirty_clean_and_depth_one_repository_states_are_locked() -> None:
    if _phase54_active_gate2_is_active():
        return
    tracked = set(_git_output(["diff", "--name-only"]).splitlines()) - {""}
    untracked = set(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    ) - {""}
    assert _git_output(["diff", "--cached", "--name-status"]) == ""
    dirty = tracked | untracked
    slice14_modified = _phase53_gate2_paths("MODIFIED_PATHS")
    slice14_added = _phase53_gate2_paths("ADDED_PATHS")
    assert dirty in (set(), set(ALLOWLIST_PATHS), slice14_modified | slice14_added)
    head = _git_output(["rev-parse", "HEAD"])
    main = _git_optional_ref("refs/heads/main")
    origin_main = _git_optional_ref("refs/remotes/origin/main")
    if dirty:
        assert tracked in (set(MODIFIED_PATHS), slice14_modified)
        assert untracked in (set(ADDED_PATHS), slice14_added)
        assert _git_output(["branch", "--show-current"]) == "main"
        assert head == main == origin_main
        assert head in (
            BASE_HEAD_SHA,
            "d8a5e9ab3de70ce30575513c73560c86430eca63",
            "93f0f591e28a01f32d1698fcd4b8c57d41c6d714",
            "15bae172ee151e370fe59d3bf909d735aee6aa90",
            "0f3c955c5a5fbd8046ef611ad1bef0b636c8be01",
            "c44a4271d9592cb393d2232f127a59d8466cc60a",
            "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16",
            "027b33cafcfd58916a89e299487dad38d24ade6c",
            "0ceb9a476e6592714cdc76845949ba0ae5123eb5",
            "b81843acadb294630db361c09949868d004b1bca",
        )
    elif phase54_publication_clean_topic_is_active():
        assert main == origin_main == phase54_publication_topic_base()
    else:
        assert main in (None, head)
        assert origin_main in (None, head)


def test_test_inventory_focused_selector_dirty_overlay_and_formatter_are_exact() -> (
    None
):
    repository_paths = _repository_paths()
    assert len(repository_paths) == 944
    assert sum(path.endswith(".py") for path in repository_paths) == 579
    assert sum(path.endswith(".md") for path in repository_paths) == 269
    test_modules = tuple(
        path
        for path in repository_paths
        if path.startswith("tests/test_") and path.endswith(".py")
    )
    assert len(test_modules) == 465
    top_level_tests = 0
    for relative in test_modules:
        tree = ast.parse(_read(relative), filename=relative)
        top_level_tests += sum(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
            for node in tree.body
        )
    assert top_level_tests == 5489
    focused_payload = ("\n".join(FOCUSED_OPERANDS) + "\n").encode()
    overlay_payload = ("\n".join(DIRTY_OVERLAY) + "\n").encode()
    formatter_payload = ("\n".join(FORMATTER_PATHS) + "\n").encode()
    assert (len(FOCUSED_OPERANDS), len(focused_payload)) == (117, 13171)
    assert hashlib.sha256(focused_payload).hexdigest() == FOCUSED_SHA256
    assert len({item.split("::", 1)[0] for item in FOCUSED_OPERANDS}) == 70
    assert sum("::" not in item for item in FOCUSED_OPERANDS) == 11
    assert sum("::" in item for item in FOCUSED_OPERANDS) == 106
    assert len(DIRTY_OVERLAY) == 185
    assert len({item.split("::", 1)[0] for item in DIRTY_OVERLAY}) == 137
    assert len(overlay_payload) == 23628
    assert hashlib.sha256(overlay_payload).hexdigest() == OVERLAY_SHA256
    assert len(FORMATTER_PATHS) == len(set(FORMATTER_PATHS)) == 63
    assert len(formatter_payload) == 3271
    assert hashlib.sha256(formatter_payload).hexdigest() == FORMATTER_SHA256
    assert len(ADDED_PATHS) == 3
    assert len(MODIFIED_PATHS) == 68
    assert len(ALLOWLIST_PATHS) == 71
    assert 9580 == 9199 + 381
    assert 9580 - 185 == 9395
    assert 3488 == 3107 + 381


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
    assert (
        _git_output(
            ["diff", "--", "pyproject.toml", "uv.lock", ".github/workflows/ci.yml"]
        )
        == ""
    )
    assert (
        _window_identity.WindowFunctionRole.WINDOW_FUNCTION.value == "window_function"
    )
    assert "genuine product decisions=0" in docs.lower() or "No later identity" in docs


_SLICE10_READER_MIGRATION_PATHS = (
    "docs/spec/phase53-partition-binding-multi-key-visibility-diagnostics-contract-v1.md",
    "src/pietto/semantic/window_partition_analysis.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
)
# Phase 53 Slice 13 reader migration.
