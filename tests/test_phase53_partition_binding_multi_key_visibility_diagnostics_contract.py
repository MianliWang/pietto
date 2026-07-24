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
import pietto.semantic.window_partition_analysis as window_partition_analysis
from pietto._project.model import (
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectRowFieldProvenanceKind,
    ProjectRowResultRole,
    ProjectRowSchema,
    ProjectSemanticModel,
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
    build_window_result_project_fact,
)
from pietto.ast_nodes import (
    BinaryExpr,
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
    SelectItem,
    SatisfyingClause,
    SourceDef,
    Span,
    TableDef,
    UnaryExpr,
    WindowExpr,
)
from pietto.errors import Diagnostic, SourceLocation
from pietto.ir.lowering import lower_expr
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.model import (
    EffectiveNullability,
    ResolvedType,
    RowSchema,
    SemanticModel,
    TypeKind,
    ValueType,
    ValueTypeKind,
)
from pietto.semantic.window_semantics import (
    DistributionWindowPolicy,
    DistributionWindowSemanticFact,
    RankingWindowSemanticFact,
    WindowExpressionAnalysis,
    WindowExpressionSemanticFact,
    WindowExpressionStage,
    WindowExpressionUnsupported,
    WindowPartitionBindingFact,
    WindowPartitionFieldBinding,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_REL = (
    "docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md"
)
SPEC_REL = (
    "docs/spec/"
    "phase53-partition-binding-multi-key-visibility-diagnostics-contract-v1.md"
)
SELF_REL = (
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py"
)
PHASE52_PARITY_SPEC_REL = (
    "docs/spec/phase52-parity-privacy-cross-phase-readiness-drift-closure-v1.md"
)
PHASE52_PARITY_SPEC_SHA256 = (
    "7010cd8a39ed389de588d8cd734b136cc87456c3ef5eb324638467d1188fc935"
)
BASE_HEAD_SHA = "c9e04d833e36bdd7cdc521eeb2c5f030aac8a998"
SPEC_TITLE = (
    "Phase 53 Partition Binding, Multi-key Visibility, And Diagnostics Contract v1"
)
SLICE10_PLAN_H2 = "Slice 10 Partition Binding, Multi-key Visibility, And Diagnostics"
SPEC_H2 = (
    "Status And Authority",
    "Exact Function And Source Subset",
    "Partition Cardinality And Direct-field Binding",
    "Multi-key Visibility And Duplicate Policy",
    "Structural Partition Semantics And Nullable Fields",
    "Private Partition-binding Carrier",
    "Composite Semantic Result And Compatibility Wrappers",
    "Semantic Analysis Resolver And Diagnostics",
    "Partition Peer And Order-key Interaction",
    "Project Dependencies Occurrences And Edges",
    "Result Identity Provenance And Transience",
    "Persistence Row-schema And Downstream Boundaries",
    "IR SQL And Public Boundaries",
    "Completed-function Compatibility Matrix",
    "Reader Closure Validation And Publication",
    "Deferred Ownership And Stop Conditions",
)
SPEC_H3 = (
    "row_number",
    "rank",
    "dense_rank",
    "percent_rank",
    "cume_dist",
    "ntile",
)
IDENTITIES = SPEC_H3

EXPECTED_TEST_FUNCTIONS = (
    "test_slice10_artifact_paths_headings_and_lifecycle_are_exact",
    "test_completed_identity_source_subset_and_result_types_are_locked",
    "test_partition_cardinality_candidates_and_arbitrary_tuple_selection_are_exact",
    "test_grammar_ast_partition_tuple_cardinality_source_order_and_duplicates_are_locked",
    "test_partition_expression_candidates_and_direct_field_selection_are_exact",
    "test_multi_key_visibility_candidates_and_immediate_input_selection_are_exact",
    "test_duplicate_partition_candidates_and_occurrence_edge_selection_are_exact",
    "test_partition_carrier_candidates_and_sibling_selection_are_exact",
    "test_semantic_result_candidates_and_composite_selection_are_exact",
    "test_semantic_module_candidates_and_sibling_module_selection_are_exact",
    "test_partition_modules_are_private_acyclic_and_rust_friendly",
    "test_partition_binding_carrier_shape_field_order_and_privacy_are_exact",
    "test_partition_binding_carrier_malformed_matrix_fails_closed",
    "test_partition_binding_empty_order_duplicate_equality_and_hashing_are_exact",
    "test_window_expression_analysis_shape_field_order_and_privacy_are_exact",
    "test_window_expression_analysis_family_invariant_matrix_fails_closed",
    "test_all_six_zero_partition_semantic_results_remain_exact",
    "test_all_six_accept_one_bare_partition_field",
    "test_all_six_accept_one_immediate_qualified_partition_field",
    "test_all_six_accept_two_source_ordered_partition_fields",
    "test_all_six_accept_three_source_ordered_partition_fields",
    "test_all_six_preserve_duplicate_partition_bindings",
    "test_nullable_partition_fields_are_structurally_accepted",
    "test_partition_binding_supports_direct_source_and_immediate_upstream_matrix",
    "test_partition_qualifier_visibility_stops_at_the_immediate_input",
    "test_partition_child_value_type_facts_are_exact_and_transient",
    "test_partition_and_order_fields_use_exactly_one_existing_resolution_each",
    "test_partition_order_and_peer_keys_are_exact_for_all_identities",
    "test_percent_rank_and_cume_dist_partition_local_posture_is_structural_only",
    "test_ntile_partition_and_positive_literal_contract_remains_exact",
    "test_partitioned_window_analysis_is_structurally_repeatable",
    "test_computed_literal_call_and_nested_partition_shapes_use_pie_s2103",
    "test_selected_let_aggregate_and_window_result_partition_names_fail_closed",
    "test_unknown_partition_fields_use_pie_s2102_without_cascade",
    "test_invalid_immediate_original_and_three_part_partition_qualifiers_use_pie_s2102",
    "test_multi_key_partition_diagnostics_stop_at_first_source_error",
    "test_partition_diagnostics_precede_local_order_diagnostics",
    "test_zero_partition_identity_arity_and_ntile_diagnostic_order_is_unchanged",
    "test_group_aggregate_satisfying_and_let_contexts_remain_unsupported",
    "test_window_placements_outside_direct_select_remain_unsupported",
    "test_multiple_nested_and_same_select_window_dependencies_remain_unsupported",
    "test_zero_multiple_and_directed_local_order_shapes_remain_unsupported",
    "test_unknown_computed_and_invalid_qualified_local_order_fields_preserve_diagnostics",
    "test_partitioned_windows_coexist_with_ordinary_where_final_order_and_limit",
    "test_project_generic_builder_supports_all_six_partitioned_identities",
    "test_project_relation_partition_and_order_role_blocks_and_ordinals_are_exact",
    "test_project_duplicate_partition_occurrences_and_first_edges_are_exact",
    "test_project_partition_dependency_order_tracks_source_reversal",
    "test_partition_and_order_same_target_remain_role_distinct",
    "test_partition_dependency_targets_locations_and_nullable_fields_are_exact",
    "test_relation_input_and_ntile_dependency_free_argument_invariants_are_exact",
    "test_project_result_identity_and_derived_provenance_remain_exact",
    "test_semantic_and_project_compatibility_wrappers_preserve_return_shapes",
    "test_partition_semantic_analysis_and_project_facts_are_transient",
    "test_partition_alias_row_schema_downstream_and_final_order_visibility_remains_absent",
    "test_partitioned_window_ir_lowering_fails_closed_with_pie_i1000",
    "test_partitioned_window_postgres_and_private_mysql_fail_before_sql_lowering",
    "test_partition_carriers_cli_json_metadata_and_public_exports_remain_private",
    "test_all_424_slice9_items_and_completed_distribution_contract_remain_locked",
    "test_all_279_slice8_items_and_completed_ranking_contract_remain_locked",
    "test_all_168_slice7_items_and_row_number_contract_remain_locked",
    "test_all_156_slice6_items_and_core_window_contract_remain_locked",
    "test_grammar_generated_ast_parser_ir_sql_and_public_bytes_are_locked",
    "test_reader_hash_inventory_and_nested_closure_is_exact",
    "test_slice10_dirty_clean_and_depth_one_repository_states_are_locked",
    "test_test_inventory_focused_selector_dirty_overlay_and_formatter_are_exact",
    "test_validation_gate3_deferred_ownership_and_no_decisions_are_locked",
)
CARDINALITIES = (
    1,
    6,
    3,
    5,
    3,
    3,
    3,
    4,
    3,
    3,
    3,
    4,
    20,
    12,
    4,
    18,
    6,
    6,
    6,
    6,
    6,
    6,
    12,
    18,
    18,
    12,
    18,
    18,
    4,
    6,
    6,
    42,
    24,
    12,
    18,
    12,
    12,
    18,
    24,
    18,
    18,
    18,
    18,
    12,
    12,
    12,
    12,
    6,
    6,
    16,
    6,
    12,
    6,
    9,
    12,
    6,
    6,
    8,
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

# These exact literal manifests are populated before the single write formatter.
ADDED_PATHS = (
    "docs/spec/phase53-partition-binding-multi-key-visibility-diagnostics-contract-v1.md",
    "src/pietto/semantic/window_partition_analysis.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
)
MODIFIED_PATHS = (
    "docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md",
    "src/pietto/semantic/window_semantics.py",
    "src/pietto/semantic/window_analysis.py",
    "src/pietto/_project/window_semantics.py",
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
FORMATTER_PATHS = (
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
    "tests/test_phase53_percent_rank_cume_dist_ntile_contract.py",
    "src/pietto/semantic/window_semantics.py",
    "src/pietto/semantic/window_partition_analysis.py",
    "src/pietto/semantic/window_analysis.py",
    "src/pietto/_project/window_semantics.py",
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

# Formatting-neutral final identities are populated after the single formatter.
FINAL_SHA256: dict[str, str] = {
    "docs/spec/phase53-partition-binding-multi-key-visibility-diagnostics-contract-v1.md": "399e4db2791b299ebdb8d51846f8e9036f3bb642bfd45a47f5f728c907d16818",
    "src/pietto/semantic/window_partition_analysis.py": "de21fe2a55f40e79676206d1dbb01cfd25b57f579d251a5efab7d60a4c57faa6",
    "docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md": "61ab560db3af539d1a4eac7b56a5220956d0a76bba31b47a628a2af07e62a21f",
    "src/pietto/semantic/window_semantics.py": "d62fdd13b75ad3abaf54f7a0dcd86b2d52eb89d733874b8fcf63692c6a3f71af",
    "src/pietto/semantic/window_analysis.py": "2b16aa98da01452534d479518149737c9c1e8d554c90af31e18cc9aa817e2b71",
    "src/pietto/_project/window_semantics.py": "9dc4f1b141a53af17d26aa77e30a42e7d7306770935838f637be767f52ddbe34",
    "tests/test_phase53_percent_rank_cume_dist_ntile_contract.py": "bb11a632cbab5fd1d995f49e90d0da6071d5f95ebbb91a01b01d850498235f2b",
    "tests/test_phase53_rank_dense_rank_peer_semantics_contract.py": "dae5f72d1df4afd3fad0e8b0def3dda2a7a4805c3f3968047785b826874d6bd5",
    "tests/test_phase53_row_number_direct_field_mvp_contract.py": "e8c7461a8e68fa53853cf5c3e18b0015ba7c778be484a53c5680a76868a1dbfd",
    "tests/test_phase11_ci_workflow.py": "71d321593505e1e071dc1180d87cb5b4c38f4706049171671012cf3db02a8cd6",
    "tests/test_phase11_completion_audit.py": "e03bc679c6cbdb9cf889b0f6981789fc46abb95b6978281345599c6136f06870",
    "tests/test_phase11_generated_guard.py": "741fc2832941f171019568aff52354c3b95fa60fc3ffa83cdebc8708463299c8",
    "tests/test_phase11_golden_policy.py": "2d641f163f92b70fff9999bc64f27e238ecda938d4755b9b02294bf82675a785",
    "tests/test_phase11_packaging_smoke.py": "6656b5a6cfc7c913661d4207ef708c5aaee6a043d18b4cba605129600a422821",
    "tests/test_phase11_planning_audit.py": "0c4a9a74a8cb7800404d0367127b333a98c584402224627c0058258853b1f691",
    "tests/test_phase11_validation_entrypoint.py": "49ea8bd3877a12bae994ce36b3281b17ae80ac0827ef1c5133252a4d03ffda1d",
    "tests/test_phase12_completion_audit.py": "96b5d624397cb2736842785a30ef64cffd2698a2f7ee31309b004b659bfa6230",
    "tests/test_phase12_composition_cli_json_goldens.py": "c636ab5c406335725113f55aad6b529a07767a2672e372c1781624ae65758ded",
    "tests/test_phase12_order_limit_contract.py": "bfc2b6e5a6dc993e86b07302c687a79cc69724b9dbc4354b79476097b36ae1ff",
    "tests/test_phase12_planning_audit.py": "20c976ef4f3a2fdaea061e10076eed37e04c537fd2e29dbab49fd07e8a3bd0e1",
    "tests/test_phase13_completion_audit.py": "0b427994a58ab297853e3191bb717832fd2af87965ebda66123fe0257523b798",
    "tests/test_phase13_planning_audit.py": "bda8f4310a851d2335c11b80d047be3d5e87cf06e8557581864de59bcd099f2e",
    "tests/test_phase14_candidate_decision_audit.py": "204896591a282e7cc75d8b44f7aabede7414a44a97df060a2430254c6b96ce29",
    "tests/test_phase14_completion_audit.py": "8e3d337e52198627a1f89f109d7410f7fb4c1807fd8fa022f03ba3ef7bc958a0",
    "tests/test_phase14_planning_audit.py": "75cee8df9ec28b6edb6ade1155c1f0aec9006a7fe4551c746c60caff0e9ca44e",
    "tests/test_phase14_relationship_metadata_completion_audit.py": "6b4138d1c05742507c196594629a1bcac2358ccb852f65a0353a73d5a6cb00ea",
    "tests/test_phase15_completion_audit.py": "0300a7ea0e73a11cf205b9fe25dcc047be6d7315244d59e7642cb9986ace47e2",
    "tests/test_phase15_semantic_completion_audit.py": "98b907248958c339adb3fb66edee3a940ccbb66e47bf7a0e558ad4144d296cc1",
    "tests/test_phase16_completion_audit.py": "5bb098c6b7f8d74b2f1230ee78146c3a88bd69549e59a822f6a30859b1822da4",
    "tests/test_phase16_current_syntax_surface_audit.py": "b5fef1f7b78e390c09a8b72b02eef2a0ef324432be7fda4f3d1f1eb4f574f5ca",
    "tests/test_phase16_language_direction_audit.py": "f473aa88dcbcca75323e3397adf7f1e3f5880b32ab8b8ec07a84c60da1b2c370",
    "tests/test_phase16_safety_deferral_sql_portability.py": "54c48a59d9f5e805651ea65198cbc63f5db2a02ad109af9e4a5228289ca5b70a",
    "tests/test_phase21_group_by_hardening_audit.py": "6a9d8ea230b001b9f49c9e25010f1bc023795917b0be60c3307e02a17aa2c705",
    "tests/test_phase24_aggregate_expression_arguments_readiness.py": "9b7bf298b69fa48937d9bf07ed87fb2001abac3927db377a02b55b3a76f7b287",
    "tests/test_phase24_cli_json_output_hardening.py": "0b12521085d0ccc1f4e049671c219e6fde9482f64b8022a0d8afa2e0c3834608",
    "tests/test_phase24_completion_audit.py": "fdde028d8557d2c922a5d7dece3badcdaf1300b7fba1ce6de45fbd4b5d8a48ff",
    "tests/test_phase25_completion_audit.py": "94ebda8367c5e5160c538447062842872c5d568b40dd56c32c14ec405d356f16",
    "tests/test_phase26_completion_audit.py": "34f7bbdea06caf6784e3006da24e0eb9f6f0414ae9815a4ee1dedd878e5ccb00",
    "tests/test_phase27_completion_audit.py": "9825dd3624f99416e3b69462bdd8c553812efed3ed426e97b4401ef4e3af79e8",
    "tests/test_phase28_completion_audit.py": "ac013ab91e7c2c66b462096daf2e56992e9a3383906a612b47931e1e0584a98f",
    "tests/test_phase29_completion_audit.py": "b8253c4dfbf5cbe4982a499036e60f08860bcd2f813aef27cc315ad536b3c833",
    "tests/test_phase30_completion_audit.py": "2e0170fe0eb6377a680207f1bb89baa0465acd1a34d0b7e93aebe610946fe7d5",
    "tests/test_phase50_window_function_readiness.py": "4d5e26fd958a5bddbacc5f0fc426fd6ae872de8443c5bc356e37e5c459729cc8",
    "tests/test_phase51_completion_audit_and_status_lock.py": "34028007d9de0bfcc36d2db25288c96753bc8cc42dbba1b716ac06bfbcc8a7d3",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py": "096a9f334f909c65b190692275afd75c41ce82c6a6aaeeb03e8f1c853a8e863d",
    "tests/test_phase52_aggregate_signature_algebra_facts.py": "8bc751e81d12aba39cd20e60d0b7c4096b4622af35996a8cd1cee88adb033167",
    "tests/test_phase52_completion_audit_and_status_lock.py": "695bfa3399a24bbd3dc2829692de65da90e64e4ba05f177dd85df895b5458adb",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py": "852481f47261d35fbb0a6cc9b4619eaddfb2a8e3ecab619532bca5965131b56f",
    "tests/test_phase52_expression_stage_clause_capability_facts.py": "f2ff4dc0716a89cf9edfba347e72309850e29f2658ad1ea0998873230fe1f83d",
    "tests/test_phase52_fail_closed_capability_lookup.py": "f0b478e96620a7b95620b3c2bd83885268469d7b603d073f9336184bba7e7625",
    "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py": "a72b83b41aef187128833b9c006a0270c7b349730fdcb82b13f25a5a6a3d2c50",
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py": "c1a266fdc664793fececca7be67dffe9a34f87d7156298c4519b4b014fa487ed",
    "tests/test_phase52_private_capability_fact_foundation.py": "9452cf8cd0abc699374bd778203411d867cf0f61ce29597958b80de65d06a267",
    "tests/test_phase52_scalar_function_operator_signature_facts.py": "8a03f44465af302a9b9a3fc0e03c67d8f6f2fd0fad9a8a57f0193d60a0b2bde9",
    "tests/test_phase53_generic_type_variable_exact_compatibility_contract.py": "3f450ed73b07789998ca67df67b9b3306796f3506bdf0ae4facb8d72eed174ed",
    "tests/test_phase53_window_generic_nullability_foundation_scope_lock.py": "f234a1c91d391569c4e9e260135c7c88508cae46fa63d6cfdb862131c354f149",
    "tests/test_phase53_window_spec_function_identity_ast_contract.py": "12cf7e2a0795b2ce6b93b03675f06c88b2461278fae476893088c62f680b6028",
    "tests/test_phase53_window_syntax_contextual_grammar_contract.py": "866d977a8a8f563a3a65a6b836524ad62a6a9406c43a62d650e67459cc34e443",
    "tests/test_phase33_completion_audit.py": "8c20862dadda75da598a0cddba94878ac5a3ea5f4dd5f4bcdb9424060a2ccb3d",
    "tests/test_phase51_private_result_role_output_identity.py": "5769c04b6895cf28d35e4bc022a77373e2acec17d85f9a55e8b34f6dac7e02ba",
    "tests/test_phase53_nullability_algebra_signature_result_formula_contract.py": "1d30ed09ede899cb7764ef8ee3c684f8c4e2e01fc3cb2561e2ba3479238d24cf",
    "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py": "d77b2e3ca768e129ea201cbb06452bda08dc9a9e483e5c54553720611f04a0d2",
}
COMPILER_DIGEST = "b33ea239f32e1591a342560e42212a11f960075e6958e25c59b498963156ccde"
SEMANTIC_DIGEST = "5797637326c467ecabd5e93c5f84982b35cecff140f43f1a21451d86b196bdd2"
PHASE15_SUBSET_DIGEST = (
    "0cf41a4d625d937c5f3d83df260b405253d932054ea49d6a1a64dd8c8085ddd6"
)
PROJECT_DIGEST = "b3b115a4d70b05874e415ae060f1a3084a40e696a9004935ae54d183a06791bb"

FOCUSED_SHA256 = "dd7f1986b7c16b3875988311548d60a0314a4ebc606b57f67ef8f71cbccd29f9"
OVERLAY_SHA256 = "197b591aec962f43b9b9393da99a76ff21c3a36189cc02c7a75dc5a7b85d6b26"
FORMATTER_SHA256 = "1997fc520df1b14049b9421efef3f8bb03039d3f9439194dcbb36915a6b9e5c9"


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


def _call(function_name: str, bucket_count: int = 4) -> str:
    return (
        f"ntile({bucket_count})" if function_name == "ntile" else f"{function_name}()"
    )


def _program(
    *,
    kind: str = "query",
    call: str = "rank()",
    partition: tuple[str, ...] = (),
    order: tuple[str, ...] = ("observed_at",),
    direction: str | None = None,
    upstream: bool = False,
    alias: str = "ranking_value",
    before: tuple[str, ...] = (),
    after: tuple[str, ...] = (),
    where: bool = False,
    final_order: str | None = None,
    limit: bool = False,
) -> str:
    prefix = (
        "shape Row:\n"
        "    id: Int not null\n"
        "    observed_at: Timestamp not null\n"
        "    label: Text nullable\n"
        "    nullable_id: Int nullable\n"
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
            "        nullable_id\n"
        )
        input_name = "intermediate"
    lines = [f"{kind} ranked:", f"    from {input_name}"]
    if where:
        lines.append("    where id > 0")
    lines.append("    select:")
    lines.extend(f"        {value}" for value in before)
    lines.append(f"        {alias} = {call} window:")
    if partition:
        lines.append("            partition by:")
        lines.extend(f"                {value}" for value in partition)
    if order:
        lines.append("            order by:")
        suffix = f" {direction}" if direction is not None else ""
        lines.extend(f"                {value}{suffix}" for value in order)
    lines.extend(f"        {value}" for value in after)
    if final_order is not None:
        lines.extend(("    order by:", f"        {final_order}"))
    if limit:
        lines.append("    limit 10")
    return prefix + "\n".join(lines) + "\n"


def _parsed_relation(
    source: str, *, path: str = "slice10.pietto"
) -> tuple[Script, TableDef | QueryDef]:
    parsed = parse_source(source, path=path)
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    relation = parsed.ast.definitions[-1]
    assert isinstance(relation, (TableDef, QueryDef))
    return parsed.ast, relation


def _input_schema(script: Script, relation: TableDef | QueryDef) -> RowSchema:
    semantic = analyze(script)
    target = semantic.model.from_resolutions[relation.from_clause]
    if isinstance(target, SourceDef):
        return semantic.model.source_row_schemas[target]
    assert isinstance(target, (TableDef, QueryDef))
    return semantic.model.relation_row_schemas[target]


def _analysis(
    source: str,
    *,
    relation_override: TableDef | QueryDef | None = None,
    item_override: SelectItem | None = None,
    selected_output_ordinal: int | None = None,
    input_schema_override: RowSchema | None = None,
) -> tuple[
    WindowExpressionAnalysis | WindowExpressionUnsupported,
    list[Diagnostic],
    dict[Expression, ValueType],
    TableDef | QueryDef,
]:
    script, parsed_relation = _parsed_relation(source)
    relation = relation_override or parsed_relation
    ordinal = selected_output_ordinal
    if ordinal is None:
        ordinal = next(
            index
            for index, selected in enumerate(relation.select_items)
            if isinstance(selected.expression, WindowExpr)
        )
    item = item_override or relation.select_items[ordinal]
    assert isinstance(item.expression, WindowExpr)
    values: dict[Expression, ValueType] = {}
    diagnostics: list[Diagnostic] = []
    result = window_analysis.analyze_window_expression(
        definition=relation,
        item=item,
        selected_output_ordinal=ordinal,
        source_id=item.expression.span.path or relation.name,
        input_schema=input_schema_override or _input_schema(script, parsed_relation),
        field_qualifier=relation.from_clause.source_name,
        value_types=values,
        diagnostics=diagnostics,
    )
    return result, diagnostics, values, relation


def _canonical_analysis(
    function_name: str,
    *,
    partition: tuple[str, ...] = (),
    qualified_order: bool = False,
    upstream: bool = False,
    kind: str = "query",
    bucket_count: int = 4,
) -> tuple[WindowExpressionAnalysis, TableDef | QueryDef, dict[Expression, ValueType]]:
    input_name = "intermediate" if upstream else "rows"
    order = f"{input_name}.observed_at" if qualified_order else "observed_at"
    result, diagnostics, values, relation = _analysis(
        _program(
            kind=kind,
            call=_call(function_name, bucket_count),
            partition=partition,
            order=(order,),
            upstream=upstream,
        )
    )
    assert diagnostics == []
    assert isinstance(result, WindowExpressionAnalysis)
    return result, relation, values


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
            "observed_at": ProjectRowField(
                name="observed_at",
                resolved_type=ProjectResolvedType(
                    name="Timestamp", kind=ProjectResolvedTypeKind.BUILTIN
                ),
                nullability=ProjectRowFieldNullability.NON_NULL,
            ),
            "label": ProjectRowField(
                name="label",
                resolved_type=ProjectResolvedType(
                    name="Text", kind=ProjectResolvedTypeKind.BUILTIN
                ),
                nullability=ProjectRowFieldNullability.NULLABLE,
            ),
            "nullable_id": ProjectRowField(
                name="nullable_id",
                resolved_type=ProjectResolvedType(
                    name="Int", kind=ProjectResolvedTypeKind.BUILTIN
                ),
                nullability=ProjectRowFieldNullability.NULLABLE,
            ),
        }
    )


def _project_fact(
    function_name: str,
    *,
    partition: tuple[str, ...] = ("id", "label"),
    order: str = "observed_at",
    upstream: bool = False,
    kind: str = "query",
    bucket_count: int = 4,
    builder: str = "general",
) -> WindowResultProjectFact:
    source = _program(
        kind=kind,
        call=_call(function_name, bucket_count),
        partition=partition,
        order=(order,),
        upstream=upstream,
    )
    script, relation = _parsed_relation(source)
    upstream_name = "intermediate" if upstream else "rows"
    upstream_definition = next(
        definition
        for definition in script.definitions
        if getattr(definition, "name", None) == upstream_name
    )
    assert isinstance(upstream_definition, (SourceDef, TableDef, QueryDef))
    symbol = ProjectSymbol(
        namespace=ProjectSymbolNamespace.RELATION,
        kind=ProjectSymbolKind.TABLE if upstream else ProjectSymbolKind.SOURCE,
        name=upstream_name,
        path="slice10.pietto",
        location=SourceLocation(path="slice10.pietto", line=1, column=1),
        definition=upstream_definition,
    )
    build = {
        "general": build_window_result_project_fact,
        "ranking": build_ranking_window_result_project_fact,
        "row_number": build_row_number_window_result_project_fact,
    }[builder]
    result = build(
        definition=relation,
        item=relation.select_items[-1],
        selected_output_ordinal=len(relation.select_items) - 1,
        source_id="slice10.pietto",
        input_schema=_project_schema(),
        upstream_symbol=symbol,
    )
    assert isinstance(result, WindowResultProjectFact)
    return result


def _test_manifest(relative: str) -> tuple[tuple[str, ...], tuple[int, ...]]:
    tree = ast.parse(_read(relative), filename=relative)
    literal_sequences = {
        node.targets[0].id: ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and isinstance(node.value, (ast.List, ast.Tuple))
    }
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
            if isinstance(values, ast.Name):
                cardinality *= len(literal_sequences[values.id])
                continue
            assert isinstance(values, ast.Call)
            assert isinstance(values.func, ast.Name) and values.func.id == "range"
            assert len(values.args) == 1
            bound = values.args[0]
            assert isinstance(bound, ast.Constant) and type(bound.value) is int
            cardinality *= bound.value
        cardinalities.append(cardinality)
    return tuple(function.name for function in functions), tuple(cardinalities)


def _assert_unsupported(
    source: str,
    *,
    code: str,
) -> tuple[WindowExpressionUnsupported, Diagnostic, TableDef | QueryDef]:
    result, diagnostics, _, relation = _analysis(source)
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == [code]
    return result, diagnostics[0], relation


def _analysis_with_partition_expression(
    function_name: str,
    partition_expression: Expression,
) -> tuple[WindowExpressionAnalysis | WindowExpressionUnsupported, list[Diagnostic]]:
    source = _program(call=_call(function_name), partition=("id",))
    _, relation = _parsed_relation(source)
    item = relation.select_items[-1]
    outer = cast(WindowExpr, item.expression)
    replacement = dataclasses.replace(
        outer,
        spec=dataclasses.replace(
            outer.spec,
            partition_by=(partition_expression,),
        ),
    )
    replaced_item = dataclasses.replace(item, expression=replacement)
    replaced_relation = dataclasses.replace(
        relation,
        select_items=(*relation.select_items[:-1], replaced_item),
    )
    result, diagnostics, _, _ = _analysis(
        source,
        relation_override=replaced_relation,
        item_override=replaced_item,
    )
    return result, diagnostics


def test_slice10_artifact_paths_headings_and_lifecycle_are_exact() -> None:
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
        ).count(SLICE10_PLAN_H2)
        == 1
    )
    functions, cardinalities = _test_manifest(SELF_REL)
    assert functions == EXPECTED_TEST_FUNCTIONS
    assert cardinalities == CARDINALITIES
    assert len(functions) == 67
    assert sum(cardinalities) == 627


@pytest.mark.parametrize("case", range(6))
def test_completed_identity_source_subset_and_result_types_are_locked(
    case: int,
) -> None:
    function_name = IDENTITIES[case]
    result, relation, _ = _canonical_analysis(function_name)
    value_type = result.semantic_fact.result.value_type
    assert value_type is not None
    assert result.semantic_fact.identity.name == function_name
    assert result.semantic_fact.occurrence.relation_name == relation.name
    assert value_type.resolved_type.name == (
        "Float" if function_name in {"percent_rank", "cume_dist"} else "Int"
    )
    assert value_type.nullability is EffectiveNullability.NON_NULL
    assert result.semantic_fact.stage is WindowExpressionStage.WINDOW


@pytest.mark.parametrize("case", range(3))
def test_partition_cardinality_candidates_and_arbitrary_tuple_selection_are_exact(
    case: int,
) -> None:
    docs = _read(SPEC_REL) + _read(PLAN_REL)
    required = (
        "arbitrary source-ordered tuple",
        "including\nzero, one, or many elements",
        "zero or any number of bare or immediate-qualified",
    )
    assert required[case] in docs


@pytest.mark.parametrize("case", range(5))
def test_grammar_ast_partition_tuple_cardinality_source_order_and_duplicates_are_locked(
    case: int,
) -> None:
    partitions = (
        (),
        ("id",),
        ("id", "label"),
        ("id", "label", "nullable_id"),
        ("id", "id", "label"),
    )
    _, relation = _parsed_relation(_program(partition=partitions[case]))
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    partition_items = cast(
        tuple[NameExpr | DottedNameExpr, ...],
        expression.spec.partition_by,
    )
    source_names = tuple(
        item.name if isinstance(item, NameExpr) else ".".join(item.parts)
        for item in partition_items
    )
    assert source_names == partitions[case]
    assert type(expression.spec.partition_by) is tuple


@pytest.mark.parametrize("case", range(3))
def test_partition_expression_candidates_and_direct_field_selection_are_exact(
    case: int,
) -> None:
    source = _read("src/pietto/semantic/window_analysis.py")
    required = (
        "NameExpr | DottedNameExpr",
        "window partition expression must be a direct field",
        "bind_window_partition_fields(",
    )
    assert required[case] in source


@pytest.mark.parametrize("case", range(3))
def test_multi_key_visibility_candidates_and_immediate_input_selection_are_exact(
    case: int,
) -> None:
    docs = _read(SPEC_REL)
    required = (
        "only fields of the immediate concrete relation input",
        "Original-source\nqualifiers beyond an upstream query",
        "field_qualifier",
    )
    assert required[case] in docs


@pytest.mark.parametrize("case", range(3))
def test_duplicate_partition_candidates_and_occurrence_edge_selection_are_exact(
    case: int,
) -> None:
    fact = _project_fact("rank", partition=("id", "id"))
    partition_occurrences = tuple(
        item
        for item in fact.dependency_occurrences
        if item.role is WindowDependencyRole.WINDOW_PARTITION
    )
    partition_edges = tuple(
        item
        for item in fact.dependency_edges
        if item.role is WindowDependencyRole.WINDOW_PARTITION
    )
    checks = (
        len(partition_occurrences) == 2,
        len(partition_edges) == 1,
        tuple(item.role_ordinal for item in partition_occurrences) == (0, 1),
    )
    assert checks[case]


@pytest.mark.parametrize("case", range(4))
def test_partition_carrier_candidates_and_sibling_selection_are_exact(
    case: int,
) -> None:
    docs = _read(SPEC_REL) + _read(PLAN_REL)
    required = (
        "WindowPartitionFieldBinding",
        "WindowPartitionBindingFact",
        "private frozen sibling carriers",
        "existing core, ranking, and distribution carrier field definitions remain",
    )
    assert required[case] in docs


@pytest.mark.parametrize("case", range(3))
def test_semantic_result_candidates_and_composite_selection_are_exact(
    case: int,
) -> None:
    result, _, _ = _canonical_analysis("percent_rank", partition=("id",))
    checks = (
        type(result) is WindowExpressionAnalysis,
        result.ranking_fact is not None and result.distribution_fact is not None,
        result.partition_binding_fact.semantic_fact is result.semantic_fact,
    )
    assert checks[case]


@pytest.mark.parametrize("case", range(3))
def test_semantic_module_candidates_and_sibling_module_selection_are_exact(
    case: int,
) -> None:
    analysis_source = _read("src/pietto/semantic/window_analysis.py")
    helper_source = _read("src/pietto/semantic/window_partition_analysis.py")
    required = (
        "from pietto.semantic.window_partition_analysis import",
        "def bind_window_partition_fields(",
        "infer_row_expression(",
    )
    assert required[case] in analysis_source + helper_source


@pytest.mark.parametrize("case", range(3))
def test_partition_modules_are_private_acyclic_and_rust_friendly(case: int) -> None:
    semantic_source = _read("src/pietto/semantic/window_semantics.py")
    helper_source = _read("src/pietto/semantic/window_partition_analysis.py")
    checks = (
        "__all__: tuple[str, ...] = ()" in semantic_source,
        "__all__: tuple[str, ...] = ()" in helper_source,
        "from pietto.semantic.window_analysis" not in helper_source,
    )
    assert checks[case]
    assert "dict[" not in "\n".join(
        line
        for line in semantic_source.splitlines()
        if line.startswith("class WindowPartition")
    )


@pytest.mark.parametrize("case", range(4))
def test_partition_binding_carrier_shape_field_order_and_privacy_are_exact(
    case: int,
) -> None:
    field_names = tuple(
        field.name for field in dataclasses.fields(WindowPartitionFieldBinding)
    )
    fact_names = tuple(
        field.name for field in dataclasses.fields(WindowPartitionBindingFact)
    )
    result, _, _ = _canonical_analysis("rank", partition=("id", "label"))
    checks = (
        field_names == ("expression", "value_type"),
        fact_names == ("semantic_fact", "bindings"),
        all(field.kw_only for field in dataclasses.fields(WindowPartitionBindingFact)),
        not hasattr(pietto, "WindowPartitionBindingFact")
        and hash(result.partition_binding_fact),
    )
    assert checks[case]


@pytest.mark.parametrize("case", range(20))
def test_partition_binding_carrier_malformed_matrix_fails_closed(case: int) -> None:
    result, _, _ = _canonical_analysis("rank", partition=("id", "label"))
    first, second = result.partition_binding_fact.bindings
    known = first.value_type
    span = first.expression.span
    variant = case % 10
    if variant < 6:
        kwargs: dict[str, object]
        error: type[Exception]
        if variant == 0:
            kwargs, error = {"expression": object(), "value_type": known}, TypeError
        elif variant == 1:
            kwargs, error = (
                {
                    "expression": LiteralExpr(span=span, value=1),
                    "value_type": known,
                },
                TypeError,
            )
        elif variant == 2:
            kwargs, error = (
                {
                    "expression": DottedNameExpr(span=span, parts=("a", "b", "c")),
                    "value_type": known,
                },
                ValueError,
            )
        elif variant == 3:
            kwargs, error = (
                {"expression": first.expression, "value_type": object()},
                TypeError,
            )
        elif variant == 4:
            kwargs, error = (
                {
                    "expression": first.expression,
                    "value_type": ValueType(
                        resolved_type=known.resolved_type,
                        nullability=known.nullability,
                        kind=ValueTypeKind.UNKNOWN,
                    ),
                },
                ValueError,
            )
        else:
            kwargs, error = (
                {
                    "expression": first.expression,
                    "value_type": ValueType(
                        resolved_type=ResolvedType(name="?", kind=TypeKind.UNKNOWN),
                        nullability=EffectiveNullability.UNKNOWN,
                    ),
                },
                ValueError,
            )
        with pytest.raises(error):
            WindowPartitionFieldBinding(**cast(Any, kwargs))
        return
    if variant == 6:
        fact_kwargs = {"semantic_fact": object(), "bindings": (first, second)}
        error = TypeError
    elif variant == 7:
        fact_kwargs = {
            "semantic_fact": result.semantic_fact,
            "bindings": [first, second],
        }
        error = TypeError
    elif variant == 8:
        fact_kwargs = {
            "semantic_fact": result.semantic_fact,
            "bindings": (first, object()),
        }
        error = TypeError
    else:
        fact_kwargs = {
            "semantic_fact": result.semantic_fact,
            "bindings": (second, first),
        }
        error = ValueError
    with pytest.raises(error):
        WindowPartitionBindingFact(**cast(Any, fact_kwargs))


@pytest.mark.parametrize("case", range(12))
def test_partition_binding_empty_order_duplicate_equality_and_hashing_are_exact(
    case: int,
) -> None:
    partitions = ((), ("id",), ("id", "label"), ("id", "id"))
    partition = partitions[case % 4]
    first, _, _ = _canonical_analysis(IDENTITIES[case % 6], partition=partition)
    second, _, _ = _canonical_analysis(IDENTITIES[case % 6], partition=partition)
    assert (
        tuple(binding.expression for binding in first.partition_binding_fact.bindings)
        == first.semantic_fact.expression.spec.partition_by
    )
    assert first == second
    assert hash(first) == hash(second)


@pytest.mark.parametrize("case", range(4))
def test_window_expression_analysis_shape_field_order_and_privacy_are_exact(
    case: int,
) -> None:
    fields = tuple(dataclasses.fields(WindowExpressionAnalysis))
    result, _, _ = _canonical_analysis("percent_rank", partition=("id",))
    checks = (
        tuple(field.name for field in fields)
        == (
            "semantic_fact",
            "ranking_fact",
            "distribution_fact",
            "partition_binding_fact",
        ),
        all(field.kw_only for field in fields),
        getattr(WindowExpressionAnalysis, "__dataclass_params__").frozen,
        hasattr(WindowExpressionAnalysis, "__slots__")
        and not hasattr(pietto, "WindowExpressionAnalysis")
        and hash(result),
    )
    assert checks[case]


@pytest.mark.parametrize("case", range(18))
def test_window_expression_analysis_family_invariant_matrix_fails_closed(
    case: int,
) -> None:
    rank, _, _ = _canonical_analysis("rank", partition=("id",))
    percent, _, _ = _canonical_analysis("percent_rank", partition=("id",))
    cume, _, _ = _canonical_analysis("cume_dist", partition=("id",))
    variant = case % 9
    if variant == 0:
        kwargs = dataclasses.asdict(rank)
        kwargs["semantic_fact"] = object()
        error = TypeError
    elif variant == 1:
        kwargs = {
            "semantic_fact": rank.semantic_fact,
            "ranking_fact": object(),
            "distribution_fact": None,
            "partition_binding_fact": rank.partition_binding_fact,
        }
        error = TypeError
    elif variant == 2:
        kwargs = {
            "semantic_fact": rank.semantic_fact,
            "ranking_fact": rank.ranking_fact,
            "distribution_fact": object(),
            "partition_binding_fact": rank.partition_binding_fact,
        }
        error = TypeError
    elif variant == 3:
        kwargs = {
            "semantic_fact": rank.semantic_fact,
            "ranking_fact": rank.ranking_fact,
            "distribution_fact": None,
            "partition_binding_fact": object(),
        }
        error = TypeError
    elif variant == 4:
        kwargs = {
            "semantic_fact": rank.semantic_fact,
            "ranking_fact": rank.ranking_fact,
            "distribution_fact": None,
            "partition_binding_fact": cume.partition_binding_fact,
        }
        error = ValueError
    elif variant == 5:
        kwargs = {
            "semantic_fact": rank.semantic_fact,
            "ranking_fact": None,
            "distribution_fact": None,
            "partition_binding_fact": rank.partition_binding_fact,
        }
        error = ValueError
    elif variant == 6:
        kwargs = {
            "semantic_fact": percent.semantic_fact,
            "ranking_fact": None,
            "distribution_fact": percent.distribution_fact,
            "partition_binding_fact": percent.partition_binding_fact,
        }
        error = ValueError
    elif variant == 7:
        kwargs = {
            "semantic_fact": percent.semantic_fact,
            "ranking_fact": percent.ranking_fact,
            "distribution_fact": None,
            "partition_binding_fact": percent.partition_binding_fact,
        }
        error = ValueError
    else:
        kwargs = {
            "semantic_fact": cume.semantic_fact,
            "ranking_fact": rank.ranking_fact,
            "distribution_fact": cume.distribution_fact,
            "partition_binding_fact": cume.partition_binding_fact,
        }
        error = ValueError
    with pytest.raises(error):
        WindowExpressionAnalysis(**cast(Any, kwargs))


@pytest.mark.parametrize("case", range(6))
def test_all_six_zero_partition_semantic_results_remain_exact(case: int) -> None:
    result, _, values = _canonical_analysis(IDENTITIES[case])
    assert result.partition_binding_fact.bindings == ()
    assert result.partition_binding_fact.partition_key == ()
    assert result.semantic_fact.expression not in values
    assert (result.ranking_fact is not None) is (case in {0, 1, 2, 3})
    assert (result.distribution_fact is not None) is (case in {3, 4, 5})


@pytest.mark.parametrize("case", range(6))
def test_all_six_accept_one_bare_partition_field(case: int) -> None:
    result, _, _ = _canonical_analysis(IDENTITIES[case], partition=("id",))
    bindings = result.partition_binding_fact.bindings
    assert len(bindings) == 1
    assert type(bindings[0].expression) is NameExpr
    assert cast(NameExpr, bindings[0].expression).name == "id"
    assert bindings[0].value_type.resolved_type.name == "Int"


@pytest.mark.parametrize("case", range(6))
def test_all_six_accept_one_immediate_qualified_partition_field(case: int) -> None:
    result, _, _ = _canonical_analysis(IDENTITIES[case], partition=("rows.id",))
    binding = result.partition_binding_fact.bindings[0]
    assert type(binding.expression) is DottedNameExpr
    assert cast(DottedNameExpr, binding.expression).parts == ("rows", "id")
    assert binding.value_type.resolved_type.name == "Int"


@pytest.mark.parametrize("case", range(6))
def test_all_six_accept_two_source_ordered_partition_fields(case: int) -> None:
    result, _, _ = _canonical_analysis(IDENTITIES[case], partition=("label", "id"))
    bindings = result.partition_binding_fact.bindings
    assert tuple(cast(NameExpr, item.expression).name for item in bindings) == (
        "label",
        "id",
    )
    assert tuple(item.value_type.resolved_type.name for item in bindings) == (
        "Text",
        "Int",
    )


@pytest.mark.parametrize("case", range(6))
def test_all_six_accept_three_source_ordered_partition_fields(case: int) -> None:
    result, _, _ = _canonical_analysis(
        IDENTITIES[case], partition=("id", "label", "nullable_id")
    )
    assert tuple(
        cast(NameExpr, item.expression).name
        for item in result.partition_binding_fact.bindings
    ) == ("id", "label", "nullable_id")
    assert len(result.partition_binding_fact.partition_key) == 3


@pytest.mark.parametrize("case", range(6))
def test_all_six_preserve_duplicate_partition_bindings(case: int) -> None:
    result, _, _ = _canonical_analysis(
        IDENTITIES[case], partition=("id", "id", "label")
    )
    bindings = result.partition_binding_fact.bindings
    assert len(bindings) == 3
    assert bindings[0] is not bindings[1]
    assert bindings[0].value_type == bindings[1].value_type
    first_expression = cast(NameExpr, bindings[0].expression)
    second_expression = cast(NameExpr, bindings[1].expression)
    assert first_expression is not second_expression
    assert first_expression.name == second_expression.name == "id"
    assert first_expression.span != second_expression.span
    assert first_expression.span.line < second_expression.span.line


@pytest.mark.parametrize("case", range(12))
def test_nullable_partition_fields_are_structurally_accepted(case: int) -> None:
    function_name = IDENTITIES[case % 6]
    field_name = "label" if case < 6 else "nullable_id"
    result, _, _ = _canonical_analysis(function_name, partition=(field_name,))
    binding = result.partition_binding_fact.bindings[0]
    assert binding.value_type.nullability is EffectiveNullability.NULLABLE
    assert binding.value_type.kind is ValueTypeKind.KNOWN
    assert "runtime SQL null grouping" not in _read(SPEC_REL)


@pytest.mark.parametrize("case", range(18))
def test_partition_binding_supports_direct_source_and_immediate_upstream_matrix(
    case: int,
) -> None:
    function_name = IDENTITIES[case % 6]
    variant = case // 6
    upstream = variant != 0
    qualifier = "intermediate" if upstream else "rows"
    partition = ("id",) if variant != 2 else (f"{qualifier}.id",)
    result, relation, _ = _canonical_analysis(
        function_name,
        partition=partition,
        upstream=upstream,
        kind="table" if variant == 1 else "query",
    )
    assert result.semantic_fact.occurrence.relation_name == relation.name
    assert len(result.partition_binding_fact.bindings) == 1
    assert isinstance(relation, (TableDef, QueryDef))


@pytest.mark.parametrize("case", range(18))
def test_partition_qualifier_visibility_stops_at_the_immediate_input(case: int) -> None:
    function_name = IDENTITIES[case % 6]
    invalid = ("rows.id", "wrong.id", "intermediate.nested.id")[case // 6]
    _, diagnostic, relation = _assert_unsupported(
        _program(
            call=_call(function_name),
            partition=(invalid,),
            upstream=True,
        ),
        code="PIE-S2102",
    )
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    partition_expression = expression.spec.partition_by[0]
    assert diagnostic.message == f"Unknown field: {invalid}"
    assert diagnostic.location == SourceLocation(
        path=partition_expression.span.path,
        line=partition_expression.span.line,
        column=partition_expression.span.column,
        end_line=partition_expression.span.end_line,
        end_column=partition_expression.span.end_column,
    )


@pytest.mark.parametrize("case", range(12))
def test_partition_child_value_type_facts_are_exact_and_transient(case: int) -> None:
    function_name = IDENTITIES[case % 6]
    partition = ("id", "label") if case < 6 else ("nullable_id", "id")
    result, _, values = _canonical_analysis(function_name, partition=partition)
    expressions = result.partition_binding_fact.partition_key
    order_expression = result.semantic_fact.expression.spec.order_by[0].expression
    assert all(expression in values for expression in (*expressions, order_expression))
    assert result.semantic_fact.expression not in values
    assert tuple(values[item] for item in expressions) == tuple(
        binding.value_type for binding in result.partition_binding_fact.bindings
    )


@pytest.mark.parametrize("case", range(18))
def test_partition_and_order_fields_use_exactly_one_existing_resolution_each(
    case: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    function_name = IDENTITIES[case % 6]
    partition = (
        ("id",),
        ("id", "label"),
        ("id", "id", "nullable_id"),
    )[case // 6]
    source = _program(call=_call(function_name), partition=partition)
    script, relation = _parsed_relation(source)
    input_schema = _input_schema(script, relation)
    partition_calls: list[Expression] = []
    order_calls: list[Expression] = []
    real_partition = window_partition_analysis.infer_row_expression
    real_order = window_analysis.infer_row_expression

    def record_partition(*args: Any, **kwargs: Any) -> ValueType:
        partition_calls.append(cast(Expression, args[0]))
        return real_partition(*args, **kwargs)

    def record_order(*args: Any, **kwargs: Any) -> ValueType:
        order_calls.append(cast(Expression, args[0]))
        return real_order(*args, **kwargs)

    monkeypatch.setattr(
        window_partition_analysis, "infer_row_expression", record_partition
    )
    monkeypatch.setattr(window_analysis, "infer_row_expression", record_order)
    result, diagnostics, _, _ = _analysis(
        source,
        input_schema_override=input_schema,
    )
    assert diagnostics == []
    assert isinstance(result, WindowExpressionAnalysis)
    assert len(partition_calls) == len(partition)
    assert len(order_calls) == 1


@pytest.mark.parametrize("case", range(18))
def test_partition_order_and_peer_keys_are_exact_for_all_identities(case: int) -> None:
    function_name = IDENTITIES[case % 6]
    partition = (
        ("id",),
        ("label", "id"),
        ("id", "id", "nullable_id"),
    )[case // 6]
    result, _, _ = _canonical_analysis(function_name, partition=partition)
    assert result.partition_binding_fact.partition_key == tuple(
        item.expression for item in result.partition_binding_fact.bindings
    )
    order_expression = result.semantic_fact.expression.spec.order_by[0].expression
    if result.ranking_fact is not None:
        expected_peer = () if function_name == "row_number" else (order_expression,)
        assert result.ranking_fact.peer_key == expected_peer
    if result.distribution_fact is not None:
        assert result.distribution_fact.structural_order_key == (order_expression,)
        expected_peer = () if function_name == "ntile" else (order_expression,)
        assert result.distribution_fact.peer_key == expected_peer


@pytest.mark.parametrize("case", range(4))
def test_percent_rank_and_cume_dist_partition_local_posture_is_structural_only(
    case: int,
) -> None:
    function_name = ("percent_rank", "cume_dist")[case % 2]
    result, _, _ = _canonical_analysis(function_name, partition=("id", "label"))
    assert result.distribution_fact is not None
    checks = (
        result.distribution_fact.peer_sensitive,
        len(result.partition_binding_fact.bindings) == 2,
        "Pietto evaluates no denominator" in _read(SPEC_REL),
        "runtime" not in result.distribution_fact.distribution_policy.value,
    )
    assert checks[case]


@pytest.mark.parametrize("case", range(6))
def test_ntile_partition_and_positive_literal_contract_remains_exact(case: int) -> None:
    bucket_count = case + 1
    result, _, _ = _canonical_analysis(
        "ntile", partition=("id", "label"), bucket_count=bucket_count
    )
    assert result.distribution_fact is not None
    assert result.distribution_fact.distribution_policy is (
        DistributionWindowPolicy.BALANCED_BUCKETS
    )
    assert result.distribution_fact.bucket_count == bucket_count
    assert result.ranking_fact is None


@pytest.mark.parametrize("case", range(6))
def test_partitioned_window_analysis_is_structurally_repeatable(case: int) -> None:
    function_name = IDENTITIES[case]
    first, _, first_values = _canonical_analysis(
        function_name, partition=("id", "label", "id")
    )
    second, _, second_values = _canonical_analysis(
        function_name, partition=("id", "label", "id")
    )
    assert first == second
    assert hash(first) == hash(second)
    assert first_values == second_values


@pytest.mark.parametrize("case", range(42))
def test_computed_literal_call_and_nested_partition_shapes_use_pie_s2103(
    case: int,
) -> None:
    function_name = IDENTITIES[case % 6]
    span = Span(path="slice10.pietto", line=8, column=17, end_line=8, end_column=25)
    outer, _, _ = _canonical_analysis(function_name)
    shapes: tuple[Expression, ...] = (
        LiteralExpr(span=span, value=1),
        BinaryExpr(
            span=span,
            left=NameExpr(span=span, name="id"),
            operator="+",
            right=LiteralExpr(span=span, value=1),
        ),
        CallExpr(
            span=span,
            callee=NameExpr(span=span, name="lower"),
            arguments=(NameExpr(span=span, name="label"),),
        ),
        UnaryExpr(
            span=span,
            operator="-",
            operand=NameExpr(span=span, name="id"),
        ),
        outer.semantic_fact.expression,
        LiteralExpr(span=span, value="id"),
        BinaryExpr(
            span=span,
            left=NameExpr(span=span, name="id"),
            operator="*",
            right=NameExpr(span=span, name="nullable_id"),
        ),
    )
    result, diagnostics = _analysis_with_partition_expression(
        function_name, shapes[case // 6]
    )
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == ["PIE-S2103"]
    assert diagnostics[0].message == f"Unknown function: {function_name}"


@pytest.mark.parametrize("case", range(24))
def test_selected_let_aggregate_and_window_result_partition_names_fail_closed(
    case: int,
) -> None:
    function_name = IDENTITIES[case % 6]
    unavailable_name = (
        "selected_alias",
        "local_value",
        "aggregate_value",
        "prior_window_value",
    )[case // 6]
    _, diagnostic, _ = _assert_unsupported(
        _program(call=_call(function_name), partition=(unavailable_name,)),
        code="PIE-S2102",
    )
    assert diagnostic.message == f"Unknown field: {unavailable_name}"


@pytest.mark.parametrize("case", range(12))
def test_unknown_partition_fields_use_pie_s2102_without_cascade(case: int) -> None:
    function_name = IDENTITIES[case % 6]
    unknown = "missing" if case < 6 else "rows.missing"
    result, diagnostic, relation = _assert_unsupported(
        _program(call=_call(function_name), partition=(unknown,)),
        code="PIE-S2102",
    )
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    assert result.reason == "window partition field type must be concrete"
    assert diagnostic.message == f"Unknown field: {unknown}"
    assert diagnostic.location.line == expression.spec.partition_by[0].span.line


@pytest.mark.parametrize("case", range(18))
def test_invalid_immediate_original_and_three_part_partition_qualifiers_use_pie_s2102(
    case: int,
) -> None:
    function_name = IDENTITIES[case % 6]
    invalid = ("wrong.id", "rows.id", "intermediate.deep.id")[case // 6]
    _, diagnostic, _ = _assert_unsupported(
        _program(
            call=_call(function_name),
            partition=(invalid,),
            upstream=True,
        ),
        code="PIE-S2102",
    )
    assert diagnostic.message == f"Unknown field: {invalid}"


@pytest.mark.parametrize("case", range(12))
def test_multi_key_partition_diagnostics_stop_at_first_source_error(case: int) -> None:
    function_name = IDENTITIES[case % 6]
    partition = (
        ("missing_first", "missing_second"),
        ("id", "missing_second", "missing_third"),
    )[case // 6]
    _, diagnostic, _ = _assert_unsupported(
        _program(call=_call(function_name), partition=partition),
        code="PIE-S2102",
    )
    expected = partition[0] if case < 6 else partition[1]
    assert diagnostic.message == f"Unknown field: {expected}"


@pytest.mark.parametrize("case", range(12))
def test_partition_diagnostics_precede_local_order_diagnostics(case: int) -> None:
    function_name = IDENTITIES[case % 6]
    order = "missing_order" if case < 6 else "id + 1"
    _, diagnostic, _ = _assert_unsupported(
        _program(
            call=_call(function_name),
            partition=("missing_partition",),
            order=(order,),
        ),
        code="PIE-S2102",
    )
    assert diagnostic.message == "Unknown field: missing_partition"


@pytest.mark.parametrize("case", range(18))
def test_zero_partition_identity_arity_and_ntile_diagnostic_order_is_unchanged(
    case: int,
) -> None:
    function_name = IDENTITIES[case % 6]
    scenario = case // 6
    if scenario == 0:
        call = "ntile()" if function_name == "ntile" else f"{function_name}(id)"
        expected = "PIE-S2104"
    elif scenario == 1:
        call = f"wrong_{function_name}()"
        expected = "PIE-S2103"
    else:
        call = "ntile(0)" if function_name == "ntile" else f"{function_name}(1)"
        expected = "PIE-S2104"
    result, diagnostics, _, _ = _analysis(_program(call=call))
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == [expected]


@pytest.mark.parametrize("case", range(24))
def test_group_aggregate_satisfying_and_let_contexts_remain_unsupported(
    case: int,
) -> None:
    function_name = IDENTITIES[case % 6]
    source = _program(call=_call(function_name), partition=("id",))
    _, relation = _parsed_relation(source)
    span = relation.span
    scenario = case // 6
    if scenario == 0:
        replacement = dataclasses.replace(
            relation,
            group_by_clause=GroupByClause(
                span=span,
                items=(GroupByItem(span=span, key=NameExpr(span=span, name="id")),),
            ),
        )
    elif scenario == 1:
        replacement = dataclasses.replace(
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
    elif scenario == 2:
        replacement = dataclasses.replace(
            relation,
            satisfying_clause=SatisfyingClause(
                span=span, expression=NameExpr(span=span, name="id")
            ),
        )
    else:
        replacement = dataclasses.replace(
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
    result, diagnostics, _, _ = _analysis(source, relation_override=replacement)
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == ["PIE-S2103"]


@pytest.mark.parametrize("case", range(18))
def test_window_placements_outside_direct_select_remain_unsupported(case: int) -> None:
    source = _read("src/pietto/semantic/expressions.py")
    required = (
        "for selected_output_ordinal, item in enumerate(definition.select_items):",
        "if type(item.expression) is WindowExpr:",
        "analyze_window_expression(",
    )
    assert required[case // 6] in source
    assert f'name="{IDENTITIES[case % 6]}"' not in source


@pytest.mark.parametrize("case", range(18))
def test_multiple_nested_and_same_select_window_dependencies_remain_unsupported(
    case: int,
) -> None:
    function_name = IDENTITIES[case % 6]
    source = _program(call=_call(function_name), partition=("id",))
    _, relation = _parsed_relation(source)
    first = relation.select_items[-1]
    replacement = dataclasses.replace(
        relation,
        select_items=(
            first,
            dataclasses.replace(first, alias=f"other_window_{case}"),
        ),
    )
    result, diagnostics, _, _ = _analysis(
        source,
        relation_override=replacement,
        selected_output_ordinal=case % 2,
    )
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == ["PIE-S2103"]
    assert "same-select aliases" in _read(SPEC_REL)


@pytest.mark.parametrize("case", range(18))
def test_zero_multiple_and_directed_local_order_shapes_remain_unsupported(
    case: int,
) -> None:
    function_name = IDENTITIES[case % 6]
    scenario = case // 6
    order = ((), ("observed_at", "id"), ("observed_at",))[scenario]
    direction = "asc" if scenario == 2 else None
    result, diagnostics, _, _ = _analysis(
        _program(
            call=_call(function_name),
            partition=("id",),
            order=order,
            direction=direction,
        )
    )
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == ["PIE-S2103"]


@pytest.mark.parametrize("case", range(18))
def test_unknown_computed_and_invalid_qualified_local_order_fields_preserve_diagnostics(
    case: int,
) -> None:
    function_name = IDENTITIES[case % 6]
    order = ("missing", "wrong.observed_at", "id + 1")[case // 6]
    expected = "PIE-S2103" if case // 6 == 2 else "PIE-S2102"
    result, diagnostics, _, _ = _analysis(
        _program(
            call=_call(function_name),
            partition=("id",),
            order=(order,),
        )
    )
    assert isinstance(result, WindowExpressionUnsupported)
    assert [item.code for item in diagnostics] == [expected]


@pytest.mark.parametrize("case", range(12))
def test_partitioned_windows_coexist_with_ordinary_where_final_order_and_limit(
    case: int,
) -> None:
    function_name = IDENTITIES[case % 6]
    full = case >= 6
    source = _program(
        call=_call(function_name),
        partition=("id", "label"),
        before=("id",),
        after=("label",),
        where=True,
        final_order="observed_at" if full else None,
        limit=full,
    )
    script, relation = _parsed_relation(source)
    semantic = analyze(script)
    assert not any(item.code == "PIE-S2103" for item in semantic.diagnostics)
    expression = cast(WindowExpr, relation.select_items[1].expression)
    assert expression not in semantic.model.expression_value_types


@pytest.mark.parametrize("case", range(12))
def test_project_generic_builder_supports_all_six_partitioned_identities(
    case: int,
) -> None:
    function_name = IDENTITIES[case % 6]
    fact = _project_fact(
        function_name,
        partition=("id", "label"),
        upstream=case >= 6,
    )
    assert fact.semantic_fact.identity.name == function_name
    assert fact.result_identity.role is ProjectRowResultRole.WINDOW_RESULT
    assert len(fact.dependency_occurrences) == 4


@pytest.mark.parametrize("case", range(12))
def test_project_relation_partition_and_order_role_blocks_and_ordinals_are_exact(
    case: int,
) -> None:
    function_name = IDENTITIES[case % 6]
    partition = ("id",) if case < 6 else ("id", "label", "nullable_id")
    fact = _project_fact(function_name, partition=partition)
    assert tuple(item.role for item in fact.dependency_occurrences) == (
        WindowDependencyRole.RELATION_INPUT,
        *(WindowDependencyRole.WINDOW_PARTITION for _ in partition),
        WindowDependencyRole.WINDOW_ORDER,
    )
    assert tuple(item.global_ordinal for item in fact.dependency_occurrences) == tuple(
        range(len(partition) + 2)
    )
    assert tuple(
        item.role_ordinal
        for item in fact.dependency_occurrences
        if item.role is WindowDependencyRole.WINDOW_PARTITION
    ) == tuple(range(len(partition)))


@pytest.mark.parametrize("case", range(12))
def test_project_duplicate_partition_occurrences_and_first_edges_are_exact(
    case: int,
) -> None:
    function_name = IDENTITIES[case % 6]
    partition = ("id", "id") if case < 6 else ("label", "id", "label")
    fact = _project_fact(function_name, partition=partition)
    occurrences = tuple(
        item
        for item in fact.dependency_occurrences
        if item.role is WindowDependencyRole.WINDOW_PARTITION
    )
    edges = tuple(
        item
        for item in fact.dependency_edges
        if item.role is WindowDependencyRole.WINDOW_PARTITION
    )
    assert len(occurrences) == len(partition)
    assert tuple(item.target.field_name for item in occurrences) == partition
    assert tuple(item.target.field_name for item in edges) == tuple(
        dict.fromkeys(partition)
    )


@pytest.mark.parametrize("case", range(6))
def test_project_partition_dependency_order_tracks_source_reversal(case: int) -> None:
    function_name = IDENTITIES[case]
    forward = _project_fact(function_name, partition=("id", "label"))
    reverse = _project_fact(function_name, partition=("label", "id"))

    def extract(fact: WindowResultProjectFact) -> tuple[str | None, ...]:
        return tuple(
            item.target.field_name
            for item in fact.dependency_occurrences
            if item.role is WindowDependencyRole.WINDOW_PARTITION
        )

    assert extract(forward) == ("id", "label")
    assert extract(reverse) == ("label", "id")


@pytest.mark.parametrize("case", range(6))
def test_partition_and_order_same_target_remain_role_distinct(case: int) -> None:
    fact = _project_fact(IDENTITIES[case], partition=("observed_at",))
    field_edges = tuple(
        item
        for item in fact.dependency_edges
        if item.target.field_name == "observed_at"
    )
    assert tuple(item.role for item in field_edges) == (
        WindowDependencyRole.WINDOW_PARTITION,
        WindowDependencyRole.WINDOW_ORDER,
    )
    assert field_edges[0].target == field_edges[1].target


@pytest.mark.parametrize("case", range(16))
def test_partition_dependency_targets_locations_and_nullable_fields_are_exact(
    case: int,
) -> None:
    partition = (
        ("id",),
        ("label",),
        ("nullable_id",),
        ("id", "label"),
    )[case % 4]
    fact = _project_fact(IDENTITIES[case % 6], partition=partition)
    occurrences = tuple(
        item
        for item in fact.dependency_occurrences
        if item.role is WindowDependencyRole.WINDOW_PARTITION
    )
    assert tuple(item.target.field_name for item in occurrences) == partition
    assert all(
        item.target.kind is ProjectRowDependencyNodeKind.UPSTREAM_FIELD
        for item in occurrences
    )
    assert all(item.location.path == "slice10.pietto" for item in occurrences)
    assert all(item.target.relation_name == "rows" for item in occurrences)


@pytest.mark.parametrize("case", range(6))
def test_relation_input_and_ntile_dependency_free_argument_invariants_are_exact(
    case: int,
) -> None:
    fact = _project_fact(
        "ntile",
        partition=("id",) if case % 2 else ("id", "label"),
        bucket_count=case + 1,
    )
    roles = tuple(item.role for item in fact.dependency_occurrences)
    assert roles.count(WindowDependencyRole.RELATION_INPUT) == 1
    assert WindowDependencyRole.WINDOW_ARGUMENT not in roles
    assert WindowDependencyRole.WINDOW_DEFAULT not in roles
    assert fact.dependency_occurrences[0].target.kind is (
        ProjectRowDependencyNodeKind.RELATION_INPUT
    )


@pytest.mark.parametrize("case", range(12))
def test_project_result_identity_and_derived_provenance_remain_exact(case: int) -> None:
    function_name = IDENTITIES[case % 6]
    fact = _project_fact(function_name, upstream=case >= 6)
    assert fact.result_identity.output_name == "ranking_value"
    assert fact.result_identity.occurrence is fact.semantic_fact.occurrence
    assert fact.provenance.kind is ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION
    assert fact.provenance.symbol is not None
    assert fact.provenance.symbol.name == ("intermediate" if case >= 6 else "rows")
    assert fact.provenance.location is not None


@pytest.mark.parametrize("case", range(6))
def test_semantic_and_project_compatibility_wrappers_preserve_return_shapes(
    case: int,
) -> None:
    function_name = IDENTITIES[case]
    source = _program(call=_call(function_name), partition=("id", "label"))
    script, relation = _parsed_relation(source)
    item = relation.select_items[-1]
    common = {
        "definition": relation,
        "item": item,
        "selected_output_ordinal": len(relation.select_items) - 1,
        "source_id": "slice10.pietto",
        "input_schema": _input_schema(script, relation),
        "field_qualifier": relation.from_clause.source_name,
        "value_types": {},
        "diagnostics": [],
    }
    if function_name == "row_number":
        semantic_result = window_analysis.analyze_row_number_window_expression(
            **cast(Any, common)
        )
        assert type(semantic_result) is WindowExpressionSemanticFact
        project = _project_fact(function_name, builder="row_number")
    elif function_name in {"rank", "dense_rank"}:
        semantic_result = window_analysis.analyze_ranking_window_expression(
            **cast(Any, common)
        )
        assert type(semantic_result) is RankingWindowSemanticFact
        project = _project_fact(function_name, builder="ranking")
    else:
        semantic_result = window_analysis.analyze_distribution_window_expression(
            **cast(Any, common)
        )
        assert type(semantic_result) is DistributionWindowSemanticFact
        project = _project_fact(function_name)
    assert type(project) is WindowResultProjectFact


@pytest.mark.parametrize("case", range(9))
def test_partition_semantic_analysis_and_project_facts_are_transient(case: int) -> None:
    semantic_fields = {field.name for field in dataclasses.fields(SemanticModel)}
    project_fields = {field.name for field in dataclasses.fields(ProjectSemanticModel)}
    forbidden = (
        "window_partition_bindings",
        "window_partition_facts",
        "window_expression_analyses",
        "window_expression_facts",
        "ranking_window_facts",
        "distribution_window_facts",
        "window_result_facts",
        "window_dependencies",
        "window_provenance",
    )
    assert forbidden[case] not in semantic_fields | project_fields


@pytest.mark.parametrize("case", range(12))
def test_partition_alias_row_schema_downstream_and_final_order_visibility_remains_absent(
    case: int,
) -> None:
    function_name = IDENTITIES[case % 6]
    source = _program(
        call=_call(function_name),
        partition=("id", "label"),
        final_order="observed_at" if case >= 6 else None,
    )
    script, relation = _parsed_relation(source)
    semantic = analyze(script)
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    assert expression not in semantic.model.expression_value_types
    docs = _read(SPEC_REL)
    assert "No semantic or project model schema changes" in docs
    assert "same-select lookup" in docs


@pytest.mark.parametrize("case", range(6))
def test_partitioned_window_ir_lowering_fails_closed_with_pie_i1000(case: int) -> None:
    script, relation = _parsed_relation(
        _program(call=_call(IDENTITIES[case]), partition=("id", "label"))
    )
    semantic = analyze(script)
    expression = cast(WindowExpr, relation.select_items[-1].expression)
    lowered = lower_expr(expression, semantic.model)
    assert lowered.expression is None
    assert [item.code for item in lowered.diagnostics] == ["PIE-I1000"]
    assert lowered.diagnostics[0].message == (
        "Missing semantic fact required for IR lowering: expression value type"
    )


@pytest.mark.parametrize("case", range(6))
def test_partitioned_window_postgres_and_private_mysql_fail_before_sql_lowering(
    case: int,
) -> None:
    backend = "postgres" if case < 3 else "mysql"
    function_name = IDENTITIES[case]
    script, relation = _parsed_relation(
        _program(call=_call(function_name), partition=("id",))
    )
    semantic = analyze(script)
    lowered = lower_expr(
        cast(WindowExpr, relation.select_items[-1].expression), semantic.model
    )
    assert backend in {"postgres", "mysql"}
    assert lowered.expression is None
    assert [item.code for item in lowered.diagnostics] == ["PIE-I1000"]


@pytest.mark.parametrize("case", range(8))
def test_partition_carriers_cli_json_metadata_and_public_exports_remain_private(
    case: int,
) -> None:
    protected = (
        "src/pietto/__init__.py",
        "src/pietto/cli.py",
        "src/pietto/cli_json.py",
        "src/pietto/_project/json_v2.py",
        "src/pietto/_metadata/serializer.py",
        "src/pietto/semantic/__init__.py",
        "src/pietto/ir/lowering.py",
        "src/pietto/sql/postgres.py",
    )
    assert _git_output(["diff", "--", protected[case]]) == ""
    assert not hasattr(pietto, "WindowPartitionBindingFact")
    assert not hasattr(pietto, "WindowExpressionAnalysis")


def test_all_424_slice9_items_and_completed_distribution_contract_remain_locked() -> (
    None
):
    functions, cardinalities = _test_manifest(
        "tests/test_phase53_percent_rank_cume_dist_ntile_contract.py"
    )
    assert len(functions) == 54
    assert sum(cardinalities) == 424


def test_all_279_slice8_items_and_completed_ranking_contract_remain_locked() -> None:
    functions, cardinalities = _test_manifest(
        "tests/test_phase53_rank_dense_rank_peer_semantics_contract.py"
    )
    assert len(functions) == 45
    assert sum(cardinalities) == 279


def test_all_168_slice7_items_and_row_number_contract_remain_locked() -> None:
    functions, cardinalities = _test_manifest(
        "tests/test_phase53_row_number_direct_field_mvp_contract.py"
    )
    assert len(functions) == 41
    assert sum(cardinalities) == 168


def test_all_156_slice6_items_and_core_window_contract_remain_locked() -> None:
    functions, cardinalities = _test_manifest(
        "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py"
    )
    assert len(functions) == 36
    assert sum(cardinalities) == 156


def test_grammar_generated_ast_parser_ir_sql_and_public_bytes_are_locked() -> None:
    protected = (
        "grammar/Pietto.g4",
        "src/pietto/ast_nodes.py",
        "src/pietto/ast_builder.py",
        "src/pietto/parser_api.py",
        "src/pietto/_window_identity.py",
        "src/pietto/__init__.py",
        "src/pietto/ir/lowering.py",
        "src/pietto/sql/postgres.py",
        "src/pietto/sql/mysql.py",
        "pyproject.toml",
        "uv.lock",
        ".github/workflows/ci.yml",
    )
    assert all(_git_output(["diff", "--", path]) == "" for path in protected)
    repository_paths = _repository_paths()
    generated = tuple(
        path for path in repository_paths if path.startswith("src/pietto/generated/")
    )
    ir_paths = tuple(
        REPO_ROOT / path
        for path in repository_paths
        if path.startswith("src/pietto/ir/")
    )
    sql_paths = tuple(
        REPO_ROOT / path
        for path in repository_paths
        if path.startswith("src/pietto/sql/")
    )
    assert len(generated) == 8
    assert _digest(ir_paths) == (
        "57097f43ba5e0ffa8d531b827b7029c9104b85ab3dc0657889cccd28caec5249"
    )
    assert _digest(sql_paths) == (
        "b18229fbda079d706416119002a70d091e7f5b79e0e4818a5b1292d9b88e898b"
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
    ) == (88, 32, 29, 17)
    assert _digest(compiler_paths) == COMPILER_DIGEST
    assert _digest(semantic_paths) == SEMANTIC_DIGEST
    assert _digest(phase15_paths) == PHASE15_SUBSET_DIGEST
    assert _digest(project_paths) == PROJECT_DIGEST
    assert _sha256(PHASE52_PARITY_SPEC_REL) == PHASE52_PARITY_SPEC_SHA256
    assert set(FINAL_SHA256) == set(ALLOWLIST_PATHS) - {SELF_REL}
    assert {path: _sha256(path) for path in FINAL_SHA256} == FINAL_SHA256
    reader_source = "\n".join(
        _read(path) for path in MODIFIED_PATHS if path.startswith("tests/")
    )
    for digest in (
        COMPILER_DIGEST,
        SEMANTIC_DIGEST,
        PHASE15_SUBSET_DIGEST,
        PROJECT_DIGEST,
    ):
        assert digest in reader_source + _read(SELF_REL)


def test_slice10_dirty_clean_and_depth_one_repository_states_are_locked() -> None:
    tracked = set(_git_output(["diff", "--name-only"]).splitlines()) - {""}
    untracked = set(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    ) - {""}
    assert _git_output(["diff", "--cached", "--name-status"]) == ""
    dirty = tracked | untracked
    assert dirty in (set(), set(ALLOWLIST_PATHS))
    assert tracked in (set(), set(MODIFIED_PATHS))
    assert untracked in (set(), set(ADDED_PATHS))
    head = _git_output(["rev-parse", "HEAD"])
    if dirty:
        assert head == BASE_HEAD_SHA
        assert _git_output(["branch", "--show-current"]) == "main"
        assert _git_optional_ref("refs/heads/main") == BASE_HEAD_SHA
        assert _git_optional_ref("refs/remotes/origin/main") == BASE_HEAD_SHA
    else:
        for ref in ("refs/heads/main", "refs/remotes/origin/main"):
            value = _git_optional_ref(ref)
            assert value in {None, head}


def test_test_inventory_focused_selector_dirty_overlay_and_formatter_are_exact() -> (
    None
):
    repository_paths = _repository_paths()
    python_paths = tuple(path for path in repository_paths if path.endswith(".py"))
    markdown_paths = tuple(path for path in repository_paths if path.endswith(".md"))
    test_modules = tuple(
        path
        for path in python_paths
        if path.startswith("tests/") and Path(path).name.startswith("test_")
    )
    top_level_tests = 0
    for path in test_modules:
        tree = ast.parse(_read(path), filename=path)
        top_level_tests += sum(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
            for node in tree.body
        )
    assert (
        len(repository_paths),
        len(python_paths),
        len(markdown_paths),
        len(test_modules),
        top_level_tests,
    ) == (864, 531, 237, 443, 4531)
    added_payload = ("\n".join(ADDED_PATHS) + "\n").encode()
    modified_payload = ("\n".join(MODIFIED_PATHS) + "\n").encode()
    allowlist_payload = ("\n".join((*ADDED_PATHS, *MODIFIED_PATHS)) + "\n").encode()
    focused_payload = ("\n".join(FOCUSED_OPERANDS) + "\n").encode()
    overlay_payload = ("\n".join(DIRTY_OVERLAY) + "\n").encode()
    formatter_payload = ("\n".join(FORMATTER_PATHS) + "\n").encode()
    assert (len(ADDED_PATHS), len(added_payload)) == (3, 215)
    assert hashlib.sha256(added_payload).hexdigest() == (
        "4363e3cbb535acf8fe2e897b887270801f0ec440a582194c5c9d9b9e6781939a"
    )
    assert (len(MODIFIED_PATHS), len(modified_payload)) == (60, 3066)
    assert hashlib.sha256(modified_payload).hexdigest() == (
        "d2d000c43603d38981725a73acaf9b733b6dfdf7d4640bd6686188e2ff7a5f88"
    )
    assert (len(ALLOWLIST_PATHS), len(allowlist_payload)) == (63, 3281)
    assert hashlib.sha256(allowlist_payload).hexdigest() == (
        "6f030ae5ac1549f706bc3786d1650edf2ad1d381a48d50e040df7de78d2982e5"
    )
    assert (len(FOCUSED_OPERANDS), len(focused_payload)) == (115, 13018)
    assert hashlib.sha256(focused_payload).hexdigest() == FOCUSED_SHA256
    assert len({item.split("::", 1)[0] for item in FOCUSED_OPERANDS}) == 68
    assert sum("::" not in item for item in FOCUSED_OPERANDS) == 9
    assert sum("::" in item for item in FOCUSED_OPERANDS) == 106
    assert len(DIRTY_OVERLAY) == 185
    assert len({item.split("::", 1)[0] for item in DIRTY_OVERLAY}) == 137
    assert len(overlay_payload) == 23628
    assert hashlib.sha256(overlay_payload).hexdigest() == OVERLAY_SHA256
    assert len(FORMATTER_PATHS) == len(set(FORMATTER_PATHS)) == 61
    assert len(formatter_payload) == 3117
    assert hashlib.sha256(formatter_payload).hexdigest() == FORMATTER_SHA256
    assert 8365 == 7738 + 627
    assert 8180 == 8365 - 185
    assert 2273 == 1646 + 627


def test_validation_gate3_deferred_ownership_and_no_decisions_are_locked() -> None:
    docs = _read(SPEC_REL) + _read(PLAN_REL)
    required = (
        "A3/M60/D0",
        "67-function/627-item",
        "2273 focused",
        "8180 passed and 185 deselected",
        "8365 passes",
        "one write-mode Ruff invocation",
        "unstaged and uncommitted",
        "Add Phase 53 partition binding and diagnostics",
        "Slice 15 retains Window IR",
        "Phase 53 Slice 10 Gate 3",
        "0.1.0",
    )
    for item in required:
        assert item in docs
    assert "genuine_product_decisions" not in docs
    assert "genuine_architecture_decisions" not in docs
    assert "Slice 10 remains\n`UNSTARTED` throughout Gate 2" in docs
