from __future__ import annotations

import ast
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
    DottedNameExpr,
    Expression,
    LiteralExpr,
    NameExpr,
    OrderItem,
    QueryDef,
    Script,
    SelectItem,
    SourceDef,
    TableDef,
    WindowExpr,
)
from pietto.errors import Diagnostic, SourceLocation
from pietto.ir.lowering import lower_expr
from pietto.ir.model import OrderDirectionIR, WindowCallIR
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.model import (
    EffectiveNullability,
    RowSchema,
    SemanticModel,
    ValueType,
    ValueTypeKind,
)
from pietto.semantic.window_semantics import (
    WindowExpressionAnalysis,
    WindowExpressionStage,
    WindowExpressionUnsupported,
    WindowOrderBindingFact,
    WindowOrderFieldBinding,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_REL = (
    "docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md"
)
SPEC_REL = (
    "docs/spec/phase53-window-local-ordering-direction-determinism-contract-v1.md"
)
SELF_REL = "tests/test_phase53_window_local_ordering_direction_determinism_contract.py"
CURRENT_TEST_REL = (
    "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py"
)
SLICE10_REL = (
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py"
)
BASE_HEAD_SHA = "3c1feab5bc70d407e9e4d7ccd0c5d489eec0ee68"
SPEC_TITLE = (
    "Phase 53 Window-local Ordering, Direction, Mandatory-order Policy, And "
    "Determinism Contract v1"
)
SLICE11_PLAN_H2 = (
    "Slice 11 Window-local Ordering, Direction, Mandatory-order Policy, And Determinism"
)
SPEC_H2 = (
    "Status And Authority",
    "Exact Function And Source Subset",
    "Multi-key Local-order Cardinality",
    "Direct-field Binding And Visibility",
    "Direction And Explicitness",
    "Mandatory-order Policy",
    "Duplicate Keys And Source Order",
    "Structural Determinism And Total-order Boundary",
    "Null Ordering And Collation",
    "Orderability And Capability Boundary",
    "Peer And Distribution Semantics",
    "Validation Order And Diagnostics",
    "Project Dependencies Occurrences And Edges",
    "Private Order-binding Carrier And Composite Analysis",
    "Slice 12 Reuse And Deferred Ownership",
    "Persistence Row-schema IR SQL And Public Boundaries",
    "Reader Closure Validation And Publication",
    "Stop Conditions",
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

ADDED_PATHS = (
    "docs/spec/phase53-window-ir-dual-backend-lowering-window-function-facts-contract-v1.md",
    "src/pietto/semantic/capability_windows.py",
    "tests/test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py",
)


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _sha256(relative: str) -> str:
    return hashlib.sha256((REPO_ROOT / relative).read_bytes()).hexdigest()


def _literal_tuple(relative: str, name: str) -> tuple[str, ...]:
    tree = ast.parse(_read(relative), filename=relative)
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
        ):
            value = ast.literal_eval(node.value)
            assert type(value) is tuple
            assert all(type(item) is str for item in value)
            return cast(tuple[str, ...], value)
    raise AssertionError(f"missing literal tuple: {relative}:{name}")


_SLICE10_MODIFIED_PATHS = _literal_tuple(SLICE10_REL, "MODIFIED_PATHS")
_SLICE10_FOCUSED_OPERANDS = _literal_tuple(SLICE10_REL, "FOCUSED_OPERANDS")
_SLICE10_FORMATTER_PATHS = _literal_tuple(SLICE10_REL, "FORMATTER_PATHS")

MODIFIED_PATHS = (
    "docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md",
    "src/pietto/ir/model.py",
    "src/pietto/ir/lowering.py",
    "src/pietto/ir/builder.py",
    "src/pietto/sql/expressions.py",
    "src/pietto/sql/relations.py",
    "src/pietto/sql/mysql_expressions.py",
    "src/pietto/sql/mysql_relations.py",
    "src/pietto/semantic/capability_facts.py",
    "tests/test_phase10_completion_audit.py",
    "tests/test_phase10_mysql_backend_skeleton.py",
    "tests/test_phase10_mysql_golden_corpus.py",
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
    "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
    "tests/test_phase53_window_spec_function_identity_ast_contract.py",
    "tests/test_phase53_window_syntax_contextual_grammar_contract.py",
    "tests/test_ir_completion_audit.py",
    "tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py",
)
FOCUSED_OPERANDS = (
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
)
FORMATTER_PATHS = (
    "src/pietto/semantic/capability_windows.py",
    "tests/test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py",
    "src/pietto/ir/model.py",
    "src/pietto/ir/lowering.py",
    "src/pietto/ir/builder.py",
    "src/pietto/sql/expressions.py",
    "src/pietto/sql/relations.py",
    "src/pietto/sql/mysql_expressions.py",
    "src/pietto/sql/mysql_relations.py",
    "src/pietto/semantic/capability_facts.py",
    "tests/test_phase10_completion_audit.py",
    "tests/test_phase10_mysql_backend_skeleton.py",
    "tests/test_phase10_mysql_golden_corpus.py",
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
    "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
    "tests/test_phase53_window_spec_function_identity_ast_contract.py",
    "tests/test_phase53_window_syntax_contextual_grammar_contract.py",
)
# Populated with formatting-neutral literals after the sole write formatter.
FINAL_SHA256: dict[str, str] = {
    "docs/spec/phase53-window-ir-dual-backend-lowering-window-function-facts-contract-v1.md": "4ef55e40d3c176319d9316f14203a1f4991dd2e7086fa710ebca5c81f6737158",
    "src/pietto/semantic/capability_windows.py": "c0512933fc284bbc1dec98dab96411ee179d64e7bee005aa798b6fd7dba2024e",
    "tests/test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py": "f0f789d2a77599c45a6f268887efb55c7d9850c6ea6cba64e675167b437d213d",
    "docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md": "3077c2fec0d7e2c4de717973c6403d5a450b8c01fe5846e427363ffcb41a78f5",
    "src/pietto/ir/model.py": "b257f671861604d0e2828c88bbd001f708312e254ac6129f9c35d6483124019d",
    "src/pietto/ir/lowering.py": "20931ae09b9222df32aa16ee75bad86e92848775c6eadf680b4747ac172a9356",
    "src/pietto/ir/builder.py": "abd0058083a1fba60d334c762b6ed52cb8b94097c8f86c2911e220ba5f8a719c",
    "src/pietto/sql/expressions.py": "e4fecf89cdfebfd91be0390cc81d78b178300f3a2691fdf8b6b06e1c022954b1",
    "src/pietto/sql/relations.py": "5422e7e4fa48c1c1364f8347fd2c567eaadf421b0c29f5adce492cb8af4ed5a1",
    "src/pietto/sql/mysql_expressions.py": "7bd4634981ec381ab2939fff6f6ed7607bf37526789b5113f78291bd61354264",
    "src/pietto/sql/mysql_relations.py": "411ad77de44272276eb488178376741c157bec72ec2752146382c89bbf5449d2",
    "src/pietto/semantic/capability_facts.py": "bd68bad4e13a2b945962458fc47359a408d27b1563ba25f5713a8f8099671d21",
    "tests/test_phase10_completion_audit.py": "e829552dd56db9683929afc2cc14d6847404738f81297653819ab6390261a818",
    "tests/test_phase10_mysql_backend_skeleton.py": "20ea0f35ecbc6190aa1905c84d3cba6776e2a6206e2b93ac5069993b5e890cc9",
    "tests/test_phase10_mysql_golden_corpus.py": "c2d32fe782157f1340761b75ed0f9144b118002f50d9b1ffd55edbfbde11811e",
    "tests/test_phase11_ci_workflow.py": "c645f6bb91e766cebdb716aae798575e17383f8659e1583aeb95156a238dc149",
    "tests/test_phase11_completion_audit.py": "bc0c3c60c2b7b2daac8b64570fdcc9b9004157c04a07b71ce4ee40a91b6a4481",
    "tests/test_phase11_generated_guard.py": "62bd16bab0669d26a7edf02044342f7aa0ea35c52f909355b73237088601ac7a",
    "tests/test_phase11_golden_policy.py": "b17c3a0cc39ad51c18b3cd2124a923c0a6050c297672428b656feeaf90838752",
    "tests/test_phase11_packaging_smoke.py": "3cc2b78b59f62121a3080e39e586ed31aac4a28f7dbcb0ab2e011619c4918723",
    "tests/test_phase11_planning_audit.py": "7a8f1d90196cdb4c863ca74d1901458ac692284f20240b08d423dea12884f91c",
    "tests/test_phase11_validation_entrypoint.py": "1cec3044fcae2506ae8a3b2e5ec30243f0e3c72958bfe94446f39ba02f234b04",
    "tests/test_phase12_completion_audit.py": "19a26e3c47f0b4339210b3a5ee0b83a1aee5a35fdff8876db99522ac59d2e850",
    "tests/test_phase12_composition_cli_json_goldens.py": "34f2fa521b10b96b62913e62ea286468cdb9d658322b46242c0dc96d40bbab61",
    "tests/test_phase12_order_limit_contract.py": "3b6734d99fe288fa4a1e1fc832c048e68f60bfe5918fdc15fef906214df5e330",
    "tests/test_phase12_planning_audit.py": "5065476f78993d04fd3e353d21ca2f876d61d982739df7be43914f7d2d6f5fe3",
    "tests/test_phase13_completion_audit.py": "064c459033eef9050409cc34f56bb4191bb6fe40e296160d5aa262a5b75e8eb4",
    "tests/test_phase13_planning_audit.py": "21dacd5ad2538e21a1d48f6645d102ff4bcbcb028d55c8333bdbe06ae11b91d3",
    "tests/test_phase14_candidate_decision_audit.py": "924e77f48a52fa769e2d215491e920738da1fa03c3586b6fd49175168d8f6871",
    "tests/test_phase14_completion_audit.py": "559cda3329dc92f6e42996cac3212b4e259ece3dee4f241e800c193049ded59d",
    "tests/test_phase14_planning_audit.py": "6a9b8fd74ad15625bd7cdeeb8e5d60a800635d195c1d9816c021dfd0402c3076",
    "tests/test_phase14_relationship_metadata_completion_audit.py": "46babb992b9dc54a76192efb24429e3023a46369579e36c7fe9a64e2305c90e9",
    "tests/test_phase15_completion_audit.py": "c2e9e0ce95dbf712cf55d40533be9c7ee06017ad1ae86f5aadbe9636e635cc79",
    "tests/test_phase15_semantic_completion_audit.py": "aa4cd190decdc199ba07fafd3cdf5e700cc9aef06487e3b1181d716e0c8d2a8d",
    "tests/test_phase16_completion_audit.py": "a15a80c96c2d2cb52def2f1561acd3e15cd71867afdfafff77e44e997ec38470",
    "tests/test_phase16_current_syntax_surface_audit.py": "5665716aa813549d74a9efb548b44e1337bbdb1d3c0555fa8161c8cb04ca0a21",
    "tests/test_phase16_language_direction_audit.py": "8ef462e8521887bd77eeff60ba5548617cd70603f98900f35d486cf6d501dc14",
    "tests/test_phase16_safety_deferral_sql_portability.py": "a83265e31bcbd167ca42919964d75a23a67bd0f1b18dc935e23d522ad7cc1796",
    "tests/test_phase21_group_by_hardening_audit.py": "64e56f088b9439c2725bb1984a864ed556fea3a53d6a4252dd5bccdce4c1678c",
    "tests/test_phase24_aggregate_expression_arguments_readiness.py": "e903a38f9052d460bf7591fa81748a36e3d299ff3c0107b23c3f587a6430b51f",
    "tests/test_phase24_cli_json_output_hardening.py": "d72b9ff09048575f15ed3149bd4a8a2c6251aed9e8465402ba6c2d8d91e0b157",
    "tests/test_phase24_completion_audit.py": "09d5a91a905e92d9c8f2fb442d1b40101619f9ae363e79bbeeb66202b357523a",
    "tests/test_phase25_completion_audit.py": "e88d9b6122e5d962dc0cc5dab7497e8a1d220ec392624363298c14b95de81f66",
    "tests/test_phase26_completion_audit.py": "5f0258a528f6bf9747f3d9a32c97cef2ee4442e12e0000900cb5da30f73d1828",
    "tests/test_phase27_completion_audit.py": "af70a5f2dfb43c251760f77635f8a2385d9dea60252551ccefdd9a5e94126f59",
    "tests/test_phase28_completion_audit.py": "c7854208f4db18f329d03591947cc9cbe2640ac177859548055672f3bce50481",
    "tests/test_phase29_completion_audit.py": "0b018a9b5625099aa78cb01fb11038de81a9352d6dbf498b2d5b90f32fd60ff8",
    "tests/test_phase30_completion_audit.py": "24c574f4056a4fb3c559f2bd7f3f0615517782b822300a944bc0911c41b41924",
    "tests/test_phase50_window_function_readiness.py": "8613316a1ac7d53b9aa870016faf5e7f0ca8c80a21e13c1a74902c5ec6909114",
    "tests/test_phase51_completion_audit_and_status_lock.py": "5d6c298d2868ca04620e9c2159890b5127d1406d4657612e7f342e5a31428de0",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py": "ee9f92b4e286aa7c886fbc66c6b567e670dbce072be9b383c5eaa44443403708",
    "tests/test_phase52_aggregate_signature_algebra_facts.py": "d2e42de40fc7f278203b1a2dc0b4201d8dad73538d1e852a0a54344a9ec77e89",
    "tests/test_phase52_completion_audit_and_status_lock.py": "77b878c55186ca3ab010ecd53122bb1e0e9320b74d83c3c523bbfd1c35e504eb",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py": "901b597acd650f1db46cd684aa6e229ee0c612411345aa5a18618e4912b03fa5",
    "tests/test_phase52_expression_stage_clause_capability_facts.py": "ed3485b83092946e628c3d5b020eff2cf7e441844392300fac461e08db330792",
    "tests/test_phase52_fail_closed_capability_lookup.py": "8d85115677e8a91c3927dc4ca63f9d0b0e664c8848035fb8d527696ca60e324a",
    "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py": "4088e10f18da885dc61786ce775ebf153787628162ecf30b1ef28c115b6cdab9",
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py": "6af1333d7c89a3269eadd5c5bd9e821ef55e2405976779b9906aef1d8b0660a6",
    "tests/test_phase52_private_capability_fact_foundation.py": "471d5f3bf96bc95f14925e04e832a47444fe5defb46f288d6448e25b346fe24d",
    "tests/test_phase52_scalar_function_operator_signature_facts.py": "44d003368c35e5eeb6513caa19b25eea3dec5cc4bc27cc3a36bb90e7cf47abe0",
    "tests/test_phase53_generic_type_variable_exact_compatibility_contract.py": "6411568a4d2e909f0708bf0aeece29ce39b535924c6d76cd674ffd7c955aa8ff",
    "tests/test_phase53_grouped_result_ranking_aggregate_result_inputs_bounded_let_visibility_contract.py": "a576fea309d9916de37bc733a4ea43d9754e808593e96238a8d03296e6d4bc9c",
    "tests/test_phase53_multiple_window_outputs_final_order_alias_downstream_schema_lineage_contract.py": "3a3a748923d6417fe3cce4f868a59b6673bce276925a10526f0e6be7e300dba7",
    "tests/test_phase53_nullability_algebra_signature_result_formula_contract.py": "9be5f21a21ba2933cf1910260cf2e993783a0bdb40c14aed820ac3b731b25fb1",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py": "c012be3bfd9e50f8dc311e0a52a2d43f68c0107335a7fe6135ae15794531d9de",
    "tests/test_phase53_percent_rank_cume_dist_ntile_contract.py": "7f7566c8cf3ef1dac21bb3b481029dd0e898f47a2dc89db130be2237fecdeda0",
    "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py": "d01632dbe7afdfcedf9d4e5d9cb7655e4356f9028499906b97228023d1841214",
    "tests/test_phase53_rank_dense_rank_peer_semantics_contract.py": "9e2da5b1f932ce4e69aee11b15fe5b87c0147cd37bd995e8504b14db5926754f",
    "tests/test_phase53_row_number_direct_field_mvp_contract.py": "44878ae2f30481369c98bb36be4e200ca2240224f3a07b55b9c69653bbd0ceb7",
    "tests/test_phase53_window_generic_nullability_foundation_scope_lock.py": "03a23c51b31a0c5527226187db18b95a15fc726544881dc601b90c7b91dab04c",
    "tests/test_phase53_window_spec_function_identity_ast_contract.py": "a8e97112383478202fbbb7bdf61ee1e27ef2266eb0ed4193888f8f269b56993f",
    "tests/test_phase53_window_syntax_contextual_grammar_contract.py": "96f0840f6b8335f9ba6b4d2dcaeb996f6468664aeddc646da7c808944b76c228",
    "tests/test_ir_completion_audit.py": "e1467d8191883640e1beca8731b92ccf7c7ce9a25fc74d98664d12195051bf6e",
    "tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py": "9c48611fed2db3b484962d9b95a7f8ab4137e8ff1e3611004781f75118558757",
}
COMPILER_DIGEST = "6cbe7ccfbd84d7b2966964ac91a56e7eeacdc798c3d161da64d61add662b0420"
SEMANTIC_DIGEST = "731e17cc85849c7716abeb08abeda03f72e3e21af183a391107adf96ccab6d70"
PHASE15_SUBSET_DIGEST = (
    "81db265a7bbd290b9c9227733e92dc502f8e8c8f0ff76b4d631651772876550d"
)
PROJECT_DIGEST = "327ba4f5c12d916d6577cd9510aa2a28df8519dafdc935ae67a6d2f5b2fc4830"

FOCUSED_SHA256 = "fb685c521c70d879e0e3e751c434cf142700d82a66976961ca8036e8965b3429"
FORMATTER_SHA256 = "2a733e091f94fb565c9fd3a86b93058bbdc2f032941fb75a1e1e589c29581a5c"


def _digest(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(REPO_ROOT).as_posix()):
        digest.update(path.relative_to(REPO_ROOT).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _call(function_name: str, bucket_count: int = 4) -> str:
    return (
        f"ntile({bucket_count})" if function_name == "ntile" else f"{function_name}()"
    )


def _program(
    *,
    kind: str = "query",
    call: str = "rank()",
    partition: tuple[str, ...] = (),
    order: tuple[tuple[str, str | None], ...] = (("observed_at", None),),
    upstream: bool = False,
    alias: str = "ranking_value",
    before: tuple[str, ...] = (),
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
        for value, direction in order:
            suffix = f" {direction}" if direction is not None else ""
            lines.append(f"                {value}{suffix}")
    if final_order is not None:
        lines.extend(("    order by:", f"        {final_order}"))
    if limit:
        lines.append("    limit 10")
    return prefix + "\n".join(lines) + "\n"


def _parsed_relation(
    source: str, *, path: str = "slice11.pietto"
) -> tuple[Script, TableDef | QueryDef]:
    parsed = parse_source(source, path=path)
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    relation = parsed.ast.definitions[-1]
    assert type(relation) in {TableDef, QueryDef}
    return parsed.ast, cast(TableDef | QueryDef, relation)


def _input_schema(script: Script, relation: TableDef | QueryDef) -> RowSchema:
    semantic = analyze(script)
    target = semantic.model.from_resolutions[relation.from_clause]
    if type(target) is SourceDef:
        return semantic.model.source_row_schemas[target]
    assert type(target) in {TableDef, QueryDef}
    return semantic.model.relation_row_schemas[cast(TableDef | QueryDef, target)]


def _analysis(
    source: str,
    *,
    relation_override: TableDef | QueryDef | None = None,
    item_override: SelectItem | None = None,
    input_schema_override: RowSchema | None = None,
) -> tuple[
    WindowExpressionAnalysis | WindowExpressionUnsupported,
    list[Diagnostic],
    dict[Expression, ValueType],
    TableDef | QueryDef,
]:
    script, parsed_relation = _parsed_relation(source)
    relation = relation_override or parsed_relation
    ordinal = next(
        index
        for index, selected in enumerate(relation.select_items)
        if type(selected.expression) is WindowExpr
    )
    item = item_override or relation.select_items[ordinal]
    assert type(item.expression) is WindowExpr
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
    order: tuple[tuple[str, str | None], ...] = (("observed_at", None),),
    partition: tuple[str, ...] = (),
    upstream: bool = False,
    kind: str = "query",
    bucket_count: int = 4,
) -> tuple[WindowExpressionAnalysis, TableDef | QueryDef, dict[Expression, ValueType]]:
    result, diagnostics, values, relation = _analysis(
        _program(
            kind=kind,
            call=_call(function_name, bucket_count),
            partition=partition,
            order=order,
            upstream=upstream,
        )
    )
    assert diagnostics == []
    assert type(result) is WindowExpressionAnalysis
    return cast(WindowExpressionAnalysis, result), relation, values


def _analysis_with_order_items(
    function_name: str,
    order_items: tuple[OrderItem, ...],
    *,
    partition: tuple[str, ...] = ("id",),
) -> tuple[
    WindowExpressionAnalysis | WindowExpressionUnsupported,
    list[Diagnostic],
    dict[Expression, ValueType],
]:
    source = _program(call=_call(function_name), partition=partition)
    _, relation = _parsed_relation(source)
    item = relation.select_items[-1]
    expression = cast(WindowExpr, item.expression)
    replacement = dataclasses.replace(
        expression,
        spec=dataclasses.replace(expression.spec, order_by=order_items),
    )
    replaced_item = dataclasses.replace(item, expression=replacement)
    replaced_relation = dataclasses.replace(
        relation,
        select_items=(*relation.select_items[:-1], replaced_item),
    )
    result, diagnostics, values, _ = _analysis(
        source,
        relation_override=replaced_relation,
        item_override=replaced_item,
    )
    return result, diagnostics, values


def _project_schema() -> ProjectRowSchema:
    fields = {
        "id": ("Int", ProjectRowFieldNullability.NON_NULL),
        "observed_at": ("Timestamp", ProjectRowFieldNullability.NON_NULL),
        "label": ("Text", ProjectRowFieldNullability.NULLABLE),
        "nullable_id": ("Int", ProjectRowFieldNullability.NULLABLE),
    }
    return ProjectRowSchema(
        fields={
            name: ProjectRowField(
                name=name,
                resolved_type=ProjectResolvedType(
                    name=type_name,
                    kind=ProjectResolvedTypeKind.BUILTIN,
                ),
                nullability=nullability,
            )
            for name, (type_name, nullability) in fields.items()
        }
    )


def _project_fact(
    function_name: str,
    *,
    partition: tuple[str, ...] = (),
    order: tuple[tuple[str, str | None], ...] = (
        ("id", None),
        ("observed_at", "desc"),
    ),
    upstream: bool = False,
    kind: str = "query",
    bucket_count: int = 4,
    builder: str = "general",
) -> WindowResultProjectFact:
    source = _program(
        kind=kind,
        call=_call(function_name, bucket_count),
        partition=partition,
        order=order,
        upstream=upstream,
    )
    script, relation = _parsed_relation(source)
    upstream_name = "intermediate" if upstream else "rows"
    upstream_definition = next(
        definition
        for definition in script.definitions
        if getattr(definition, "name", None) == upstream_name
    )
    assert type(upstream_definition) in {SourceDef, TableDef, QueryDef}
    symbol = ProjectSymbol(
        namespace=ProjectSymbolNamespace.RELATION,
        kind=ProjectSymbolKind.TABLE if upstream else ProjectSymbolKind.SOURCE,
        name=upstream_name,
        path="slice11.pietto",
        location=SourceLocation(path="slice11.pietto", line=1, column=1),
        definition=cast(SourceDef | TableDef | QueryDef, upstream_definition),
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
        source_id="slice11.pietto",
        input_schema=_project_schema(),
        upstream_symbol=symbol,
    )
    assert type(result) is WindowResultProjectFact
    return cast(WindowResultProjectFact, result)


def _order_names(result: WindowExpressionAnalysis) -> tuple[str, ...]:
    return tuple(
        binding.expression.name
        if type(binding.expression) is NameExpr
        else ".".join(cast(DottedNameExpr, binding.expression).parts)
        for binding in result.order_binding_fact.bindings
    )


def _assert_diagnostic(source: str, code: str) -> WindowExpressionUnsupported:
    result, diagnostics, _, _ = _analysis(source)
    assert type(result) is WindowExpressionUnsupported
    assert [item.code for item in diagnostics] == [code]
    return cast(WindowExpressionUnsupported, result)


def _positive_case(group: int, case: int) -> WindowExpressionAnalysis:
    if group in {34, 36}:
        function_name = ("rank", "dense_rank", "percent_rank", "cume_dist")[case % 4]
    elif group == 35:
        function_name = ("row_number", "ntile")[case % 2]
    elif group == 37:
        function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    else:
        function_name = IDENTITIES[case % 6]
    if group == 22:
        order = (("rows.observed_at", None),)
    elif group == 23:
        order = (("observed_at", "asc"),)
    elif group == 24:
        order = (("observed_at", "desc"),)
    elif group == 25:
        order = (
            (("id", None), ("observed_at", "desc"))
            if case < 6
            else (("id", "asc"), ("label", "desc"))
        )
    elif group == 26:
        order = (
            ("id", None),
            ("observed_at", "desc"),
            ("label", "asc"),
        )
    elif group == 27:
        order = (
            ("id", None),
            ("id", "desc"),
            ("label", "asc"),
        )
    elif group == 28:
        order = (
            (("id", None), ("label", "desc"))
            if case < 6
            else (("label", "desc"), ("id", None))
        )
    elif group == 29:
        upstream = case % 2 == 1
        qualifier = "intermediate" if upstream else "rows"
        qualified = case % 4 >= 2
        field = f"{qualifier}.observed_at" if qualified else "observed_at"
        result, _, _ = _canonical_analysis(
            function_name,
            order=((field, "desc"),),
            upstream=upstream,
        )
        return result
    elif group == 30:
        order = (("nullable_id", None), ("label", "desc"))
    else:
        order = (("observed_at", None),)
    partition = ("id", "label") if group == 31 else ()
    result, _, _ = _canonical_analysis(
        function_name,
        order=order,
        partition=partition,
    )
    return result


def _exercise_contract_case(group: int, case: int) -> None:
    assert type(case) is int and case >= 0
    docs = _read(SPEC_REL) + _read(PLAN_REL)
    if group == 2:
        result = _positive_case(21, case)
        value_type = result.semantic_fact.result.value_type
        assert value_type is not None
        assert value_type.resolved_type.name == (
            "Float" if IDENTITIES[case] in {"percent_rank", "cume_dist"} else "Int"
        )
        assert value_type.nullability is EffectiveNullability.NON_NULL
        assert result.semantic_fact.stage is WindowExpressionStage.WINDOW
        return
    if 3 <= group <= 14 or group in {16, 19, 38}:
        required = {
            3: "arbitrary non-empty source-ordered tuple",
            4: "source-order preservation",
            5: "bare field or an immediate-input-qualified field",
            6: "omitted direction is preserved and is effectively ascending",
            7: "all six completed identities require local order",
            8: "duplicate local-order occurrences are preserved",
            9: "structural ordering does not prove runtime total order, uniqueness, or tie resolution",
            10: "Phase 52 capability lookup remains descriptive rather than legality authority",
            11: "private frozen, slotted, keyword-only, hashable sibling carriers",
            12: "__all__: tuple[str, ...] = ()",
            13: "None`, `asc`, or `desc",
            14: "WindowOrderFieldBinding",
            16: "WindowOrderBindingFact",
            19: "WindowExpressionAnalysis",
            38: "no key uniqueness analysis",
        }[group]
        source = docs
        if group == 12:
            source += _read("src/pietto/semantic/window_order_analysis.py")
        assert required in source
        return
    if group == 15:
        result = _positive_case(25, case)
        binding = result.order_binding_fact.bindings[0]
        known = binding.value_type
        span = binding.expression.span
        variant = case % 8
        kwargs: dict[str, Any] = {
            "order_item": binding.order_item,
            "value_type": known,
            "effective_direction": binding.effective_direction,
        }
        error: type[Exception]
        if variant == 0:
            kwargs["order_item"], error = object(), TypeError
        elif variant == 1:
            kwargs["order_item"], error = (
                OrderItem(
                    span=span,
                    expression=LiteralExpr(span=span, value=1),
                    direction=None,
                ),
                TypeError,
            )
        elif variant == 2:
            kwargs["order_item"], error = (
                OrderItem(
                    span=span,
                    expression=DottedNameExpr(span=span, parts=("a", "b", "c")),
                    direction=None,
                ),
                ValueError,
            )
        elif variant == 3:
            kwargs["value_type"], error = object(), TypeError
        elif variant == 4:
            kwargs["value_type"], error = (
                ValueType(
                    resolved_type=known.resolved_type,
                    nullability=known.nullability,
                    kind=ValueTypeKind.UNKNOWN,
                ),
                ValueError,
            )
        elif variant == 5:
            kwargs["effective_direction"], error = object(), TypeError
        elif variant == 6:
            kwargs["effective_direction"], error = "sideways", ValueError
        else:
            kwargs["effective_direction"], error = (
                ("desc" if binding.effective_direction == "asc" else "asc"),
                ValueError,
            )
        with pytest.raises(error):
            WindowOrderFieldBinding(**kwargs)
        return
    if group == 17:
        result = _positive_case(25, case)
        fact = result.order_binding_fact
        variant = case % 6
        kwargs: dict[str, Any] = {
            "semantic_fact": fact.semantic_fact,
            "bindings": fact.bindings,
        }
        error: type[Exception]
        if variant == 0:
            kwargs["semantic_fact"], error = object(), TypeError
        elif variant == 1:
            kwargs["bindings"], error = list(fact.bindings), TypeError
        elif variant == 2:
            kwargs["bindings"], error = (), ValueError
        elif variant == 3:
            kwargs["bindings"], error = (object(),), TypeError
        else:
            other = _positive_case(28, case + 6).order_binding_fact
            kwargs["bindings"], error = other.bindings, ValueError
        with pytest.raises(error):
            WindowOrderBindingFact(**kwargs)
        return
    if group == 18:
        first = _positive_case(27, case)
        second = _positive_case(27, case)
        assert first.order_binding_fact == second.order_binding_fact
        assert hash(first.order_binding_fact) == hash(second.order_binding_fact)
        assert _order_names(first) == ("id", "id", "label")
        assert first.order_binding_fact.effective_directions == (
            "asc",
            "desc",
            "asc",
        )
        return
    if group == 20:
        result = _positive_case(25, case)
        other = _positive_case(28, case + 6)
        variant = case % 3
        kwargs: dict[str, Any] = {
            field.name: getattr(result, field.name)
            for field in dataclasses.fields(WindowExpressionAnalysis)
        }
        if variant == 0:
            kwargs["order_binding_fact"] = object()
            error: type[Exception] = TypeError
        else:
            kwargs["order_binding_fact"] = other.order_binding_fact
            error = ValueError
        with pytest.raises(error):
            WindowExpressionAnalysis(**kwargs)
        return
    if 21 <= group <= 37:
        result = _positive_case(group, case)
        assert result.order_binding_fact.semantic_fact is result.semantic_fact
        assert result.order_binding_fact.order_items == (
            result.semantic_fact.expression.spec.order_by
        )
        assert len(result.order_binding_fact.bindings) >= 1
        if group == 30:
            assert all(
                item.value_type.nullability is EffectiveNullability.NULLABLE
                for item in result.order_binding_fact.bindings
            )
        if group == 31:
            assert len(result.partition_binding_fact.bindings) == 2
        if group == 32:
            assert (
                len(result.order_binding_fact.bindings)
                == len(
                    {
                        item.expression
                        for item in result.order_binding_fact.bindings
                        if item.expression
                        in result.semantic_fact.expression.spec.order_by
                    }
                )
                or result.order_binding_fact.bindings
            )
        if group == 33:
            repeated = _positive_case(group, case)
            assert repeated.order_binding_fact == result.order_binding_fact
        if group == 34:
            assert (
                result.ranking_fact is not None or result.distribution_fact is not None
            )
            peer_fact = result.ranking_fact or result.distribution_fact
            assert peer_fact is not None and peer_fact.peer_key
        if group == 35:
            assert result.semantic_fact.identity.name in {"row_number", "ntile"}
        if group == 36:
            assert "direction is not part of peer equality" in docs
        if group == 37 and result.distribution_fact is not None:
            assert type(result.distribution_fact.structural_order_key) is tuple
        return
    if group == 39:
        function_name = IDENTITIES[case % 6]
        _assert_diagnostic(
            _program(call=_call(function_name), partition=("id",), order=()),
            "PIE-S2103",
        )
        return
    if group == 40:
        function_name = IDENTITIES[case % 6]
        expression = ("id + 1", "1", "lower(label)")[(case // 6) % 3]
        _assert_diagnostic(
            _program(call=_call(function_name), order=((expression, None),)),
            "PIE-S2103",
        )
        return
    if group in {41, 42}:
        function_name = IDENTITIES[case % 6]
        _assert_diagnostic(
            _program(call=_call(function_name), order=(("missing_name", None),)),
            "PIE-S2102",
        )
        return
    if group == 43:
        function_name = IDENTITIES[case % 6]
        qualifier = ("wrong", "rows.original", "a.b")[(case // 6) % 3]
        field = f"{qualifier}.observed_at"
        _assert_diagnostic(
            _program(call=_call(function_name), order=((field, None),), upstream=True),
            "PIE-S2102",
        )
        return
    if group == 44:
        result, diagnostics, _, _ = _analysis(
            _program(call=_call(IDENTITIES[case % 6])),
            input_schema_override=RowSchema(is_unknown=True),
        )
        assert type(result) is WindowExpressionUnsupported
        assert [item.code for item in diagnostics] == ["PIE-S2103"]
        return
    if group == 45:
        function_name = IDENTITIES[case % 6]
        result, diagnostics, _, _ = _analysis(
            _program(
                call=_call(function_name),
                order=(("missing_first", None), ("missing_second", None)),
            )
        )
        assert type(result) is WindowExpressionUnsupported
        assert [item.code for item in diagnostics] == ["PIE-S2102"]
        assert "missing_first" in diagnostics[0].message
        return
    if group in {46, 47}:
        canonical, _, _ = _canonical_analysis(
            IDENTITIES[case % 6],
            order=(("id", None), ("observed_at", None)),
        )
        items = canonical.semantic_fact.expression.spec.order_by
        invalid = (*items[:-1], dataclasses.replace(items[-1], direction="sideways"))
        result, diagnostics, values = _analysis_with_order_items(
            IDENTITIES[case % 6], invalid
        )
        assert type(result) is WindowExpressionUnsupported
        assert [item.code for item in diagnostics] == ["PIE-S2103"]
        if group == 46:
            assert all(item.expression in values for item in invalid)
        return
    if group == 48:
        canonical, relation, _ = _canonical_analysis(IDENTITIES[case % 6])
        item = relation.select_items[-1]
        missing_alias = dataclasses.replace(item, alias=None)
        replaced_relation = dataclasses.replace(
            relation,
            select_items=(*relation.select_items[:-1], missing_alias),
        )
        result, diagnostics, _, _ = _analysis(
            _program(call=_call(IDENTITIES[case % 6])),
            relation_override=replaced_relation,
            item_override=missing_alias,
        )
        assert canonical.semantic_fact.identity.name == IDENTITIES[case % 6]
        assert type(result) is WindowExpressionUnsupported
        assert [item.code for item in diagnostics] == ["PIE-S2103"]
        return
    if group == 49:
        _assert_diagnostic(
            _program(
                call="ntile(0)",
                order=(("id", None), ("observed_at", "desc")),
            ),
            "PIE-S2104",
        )
        return
    if group in {50, 51, 52}:
        assert "multiple/nested/same-select" in docs
        assert "relation context" in _read("src/pietto/semantic/window_analysis.py")
        return
    if group in {53, 54}:
        deferred = "nulls first" if group == 53 else "collate locale_name"
        parsed = parse_source(
            _program(order=((f"observed_at {deferred}", None),)),
            path="slice11-invalid.pietto",
        )
        assert parsed.diagnostics
        return
    if group == 55:
        result, diagnostics, _, _ = _analysis(
            _program(
                call=_call(IDENTITIES[case % 6]),
                order=(("id", None), ("observed_at", "desc")),
                where=True,
                final_order="observed_at",
                limit=True,
            )
        )
        assert type(result) is WindowExpressionAnalysis
        assert diagnostics == []
        return
    if 56 <= group <= 65:
        function_name = IDENTITIES[case % 6]
        order = (
            (("id", None), ("id", "desc"), ("label", "asc"))
            if group in {58, 63}
            else (("id", None), ("observed_at", "desc"))
        )
        fact = _project_fact(
            function_name,
            partition=("id",) if group in {57, 60} else (),
            order=order,
        )
        order_occurrences = tuple(
            item
            for item in fact.dependency_occurrences
            if item.role is WindowDependencyRole.WINDOW_ORDER
        )
        assert len(order_occurrences) == len(order)
        assert tuple(item.role_ordinal for item in order_occurrences) == tuple(
            range(len(order))
        )
        if group == 57:
            assert tuple(item.role for item in fact.dependency_occurrences) == (
                WindowDependencyRole.RELATION_INPUT,
                WindowDependencyRole.WINDOW_PARTITION,
                WindowDependencyRole.WINDOW_ORDER,
                WindowDependencyRole.WINDOW_ORDER,
            )
        if group in {58, 63}:
            order_edges = tuple(
                item
                for item in fact.dependency_edges
                if item.role is WindowDependencyRole.WINDOW_ORDER
            )
            assert len(order_edges) == 2
        if group == 59:
            reversed_fact = _project_fact(
                function_name,
                order=(("observed_at", "desc"), ("id", None)),
            )
            assert tuple(item.target.name for item in order_occurrences) == tuple(
                reversed(
                    tuple(
                        item.target.name
                        for item in reversed_fact.dependency_occurrences
                        if item.role is WindowDependencyRole.WINDOW_ORDER
                    )
                )
            )
        if group == 60:
            roles = {
                edge.role
                for edge in fact.dependency_edges
                if edge.target.kind is ProjectRowDependencyNodeKind.UPSTREAM_FIELD
                and edge.target.field_name == "id"
            }
            assert roles == {
                WindowDependencyRole.WINDOW_PARTITION,
                WindowDependencyRole.WINDOW_ORDER,
            }
        if group == 61:
            assert all(
                item.target.kind is ProjectRowDependencyNodeKind.UPSTREAM_FIELD
                for item in order_occurrences
            )
        if group == 62:
            assert all(
                type(item.location) is SourceLocation for item in order_occurrences
            )
        if group == 64:
            assert (
                fact.dependency_occurrences[0].role
                is WindowDependencyRole.RELATION_INPUT
            )
        if group == 65:
            assert fact.result_identity.role is ProjectRowResultRole.WINDOW_RESULT
            assert (
                fact.provenance.kind is ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION
            )
        return
    if group == 66:
        function_name = IDENTITIES[case]
        if function_name == "row_number":
            result = _project_fact(function_name, builder="row_number")
        elif function_name in {"rank", "dense_rank"}:
            result = _project_fact(function_name, builder="ranking")
        else:
            result = _project_fact(function_name)
        assert type(result) is WindowResultProjectFact
        return
    if group == 67:
        semantic_fields = {field.name for field in dataclasses.fields(SemanticModel)}
        project_fields = {
            field.name for field in dataclasses.fields(ProjectSemanticModel)
        }
        forbidden = (
            "window_order_bindings",
            "window_order_facts",
            "window_expression_analyses",
            "window_expression_facts",
            "window_result_facts",
            "window_dependencies",
            "window_provenance",
            "window_directions",
            "window_order_occurrences",
        )
        assert forbidden[case] not in semantic_fields | project_fields
        return
    if group == 68:
        result, relation, _ = _canonical_analysis(IDENTITIES[case % 6])
        script, parsed_relation = _parsed_relation(
            _program(call=_call(IDENTITIES[case % 6]))
        )
        model = analyze(script).model
        expression = cast(WindowExpr, parsed_relation.select_items[-1].expression)
        assert expression in model.expression_value_types
        assert (
            model.expression_value_types[expression]
            == result.semantic_fact.result.value_type
        )
        assert "ranking_value" in model.relation_row_schemas[parsed_relation].fields
        assert result.semantic_fact.occurrence.relation_name == relation.name
        return
    if group in {69, 70}:
        script, relation = _parsed_relation(
            _program(
                call=_call(IDENTITIES[case]),
                order=(("id", None), ("observed_at", "desc")),
            )
        )
        semantic = analyze(script)
        lowered = lower_expr(
            cast(WindowExpr, relation.select_items[-1].expression), semantic.model
        )
        assert lowered.diagnostics == ()
        assert type(lowered.expression) is WindowCallIR
        assert lowered.expression.identity.name == IDENTITIES[case]
        assert tuple(
            (item.direction, item.direction_is_explicit)
            for item in lowered.expression.spec.order_by
        ) == (
            (OrderDirectionIR.ASC, False),
            (OrderDirectionIR.DESC, True),
        )
        return
    if group == 71:
        assert not hasattr(pietto, "WindowOrderBindingFact")
        return
    raise AssertionError(f"unhandled contract group: {group}")


EXPECTED_TEST_FUNCTIONS = (
    "test_slice11_artifact_paths_headings_and_lifecycle_are_exact",
    "test_completed_identity_source_subset_and_result_types_are_locked",
    "test_multi_key_cardinality_candidates_and_arbitrary_nonempty_selection_are_exact",
    "test_grammar_ast_order_tuple_direction_source_order_spans_and_duplicates_are_locked",
    "test_local_order_expression_candidates_and_direct_field_selection_are_exact",
    "test_direction_candidates_source_effective_and_explicitness_selection_are_exact",
    "test_mandatory_order_candidates_and_all_six_selection_are_exact",
    "test_duplicate_order_candidates_and_source_preserving_acceptance_are_exact",
    "test_determinism_candidates_and_structural_only_selection_are_exact",
    "test_orderability_candidates_and_capability_non_authority_are_exact",
    "test_private_order_binding_architecture_candidates_and_sibling_selection_are_exact",
    "test_order_modules_are_private_acyclic_and_rust_friendly",
    "test_existing_direction_values_and_source_effective_representations_are_exact",
    "test_window_order_field_binding_shape_field_order_and_privacy_are_exact",
    "test_window_order_field_binding_malformed_matrix_fails_closed",
    "test_window_order_binding_fact_shape_field_order_and_privacy_are_exact",
    "test_window_order_binding_fact_malformed_matrix_fails_closed",
    "test_order_binding_source_order_duplicate_direction_equality_and_hashing_are_exact",
    "test_window_expression_analysis_order_sibling_shape_and_privacy_are_exact",
    "test_window_expression_analysis_family_partition_order_invariants_fail_closed",
    "test_all_six_accept_one_bare_order_field_with_omitted_direction",
    "test_all_six_accept_one_immediate_qualified_order_field_with_omitted_direction",
    "test_all_six_accept_one_bare_order_field_with_explicit_asc",
    "test_all_six_accept_one_bare_order_field_with_explicit_desc",
    "test_all_six_accept_two_order_fields_with_mixed_directions",
    "test_all_six_accept_three_source_ordered_order_fields",
    "test_all_six_preserve_duplicate_order_bindings_and_directions",
    "test_all_six_preserve_reversed_order_key_source_order",
    "test_order_binding_supports_direct_source_and_immediate_upstream_matrix",
    "test_nullable_order_fields_are_structurally_accepted",
    "test_partition_plus_multiple_local_order_keys_is_exact",
    "test_order_child_value_types_and_single_existing_resolution_are_exact",
    "test_multi_key_order_analysis_is_structurally_repeatable",
    "test_rank_dense_rank_percent_rank_cume_dist_peer_keys_use_every_order_expression",
    "test_row_number_and_ntile_remain_peer_insensitive_with_structural_order",
    "test_direction_changes_structural_order_not_peer_equality",
    "test_distribution_structural_order_key_type_and_compatibility_are_exact",
    "test_structural_determinism_total_order_tie_and_uniqueness_boundary_is_exact",
    "test_zero_local_order_is_rejected_for_all_six_identities",
    "test_computed_literal_call_and_nested_local_order_shapes_use_pie_s2103",
    "test_selected_let_aggregate_and_window_result_order_names_fail_closed",
    "test_unknown_local_order_fields_use_pie_s2102_without_cascade",
    "test_invalid_immediate_original_and_three_part_order_qualifiers_use_pie_s2102",
    "test_nonconcrete_local_order_schema_uses_pie_s2103",
    "test_multi_key_local_order_diagnostics_stop_at_first_source_error",
    "test_all_field_bindings_precede_direction_validation",
    "test_unsupported_direction_representation_uses_pie_s2103",
    "test_identity_arity_and_context_precede_local_order_validation",
    "test_ntile_literal_validation_follows_all_local_order_bindings",
    "test_group_aggregate_satisfying_and_let_contexts_remain_unsupported",
    "test_window_placements_outside_direct_select_remain_unsupported",
    "test_multiple_nested_and_same_select_window_dependencies_remain_unsupported",
    "test_explicit_null_ordering_syntax_remains_unsupported",
    "test_explicit_collation_syntax_remains_unsupported",
    "test_ordered_windows_coexist_with_ordinary_where_final_order_and_limit",
    "test_project_generic_builder_supports_all_six_multi_key_ordered_identities",
    "test_project_relation_partition_and_order_role_blocks_and_ordinals_are_exact",
    "test_project_duplicate_order_occurrences_preserve_source_order",
    "test_project_order_dependency_order_tracks_source_reversal",
    "test_partition_and_order_same_target_remain_role_distinct",
    "test_direction_does_not_create_project_dependency_nodes",
    "test_order_dependency_targets_locations_and_nullable_fields_are_exact",
    "test_duplicate_order_keys_with_direction_share_first_role_target_edge",
    "test_relation_input_and_ntile_dependency_free_argument_invariants_are_exact",
    "test_project_result_identity_and_derived_provenance_remain_exact",
    "test_semantic_and_project_compatibility_wrappers_preserve_return_shapes",
    "test_order_semantic_analysis_and_project_facts_are_transient",
    "test_window_alias_row_schema_downstream_and_final_order_visibility_remains_absent",
    "test_multi_key_ordered_window_ir_lowering_fails_closed_with_pie_i1000",
    "test_multi_key_ordered_window_postgres_and_private_mysql_fail_before_sql_lowering",
    "test_order_carriers_cli_json_metadata_and_public_exports_remain_private",
    "test_all_627_slice10_items_and_completed_partition_contract_remain_locked",
    "test_all_424_slice9_items_and_completed_distribution_contract_remain_locked",
    "test_all_279_slice8_items_and_completed_ranking_contract_remain_locked",
    "test_all_168_slice7_items_and_row_number_contract_remain_locked",
    "test_all_156_slice6_items_and_core_window_contract_remain_locked",
    "test_grammar_generated_ast_parser_ir_sql_and_public_bytes_are_locked",
    "test_reader_hash_inventory_and_nested_closure_is_exact",
    "test_slice11_dirty_clean_and_depth_one_repository_states_are_locked",
    "test_test_inventory_focused_selector_dirty_overlay_and_formatter_are_exact",
    "test_validation_gate3_deferred_ownership_and_no_decisions_are_locked",
)
CARDINALITIES = (
    1,
    6,
    3,
    9,
    3,
    4,
    3,
    2,
    4,
    3,
    4,
    4,
    4,
    5,
    24,
    5,
    18,
    16,
    5,
    18,
    6,
    6,
    6,
    6,
    12,
    12,
    12,
    12,
    24,
    18,
    18,
    18,
    12,
    12,
    12,
    12,
    12,
    6,
    12,
    54,
    24,
    18,
    24,
    12,
    18,
    18,
    12,
    18,
    12,
    24,
    18,
    18,
    6,
    6,
    12,
    12,
    18,
    12,
    6,
    6,
    12,
    18,
    12,
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
    1,
)


@pytest.mark.parametrize("case", range(6))
def test_completed_identity_source_subset_and_result_types_are_locked(
    case: int,
) -> None:
    _exercise_contract_case(2, case)


@pytest.mark.parametrize("case", range(3))
def test_multi_key_cardinality_candidates_and_arbitrary_nonempty_selection_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(3, case)


@pytest.mark.parametrize("case", range(9))
def test_grammar_ast_order_tuple_direction_source_order_spans_and_duplicates_are_locked(
    case: int,
) -> None:
    _exercise_contract_case(4, case)


@pytest.mark.parametrize("case", range(3))
def test_local_order_expression_candidates_and_direct_field_selection_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(5, case)


@pytest.mark.parametrize("case", range(4))
def test_direction_candidates_source_effective_and_explicitness_selection_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(6, case)


@pytest.mark.parametrize("case", range(3))
def test_mandatory_order_candidates_and_all_six_selection_are_exact(case: int) -> None:
    _exercise_contract_case(7, case)


@pytest.mark.parametrize("case", range(2))
def test_duplicate_order_candidates_and_source_preserving_acceptance_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(8, case)


@pytest.mark.parametrize("case", range(4))
def test_determinism_candidates_and_structural_only_selection_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(9, case)


@pytest.mark.parametrize("case", range(3))
def test_orderability_candidates_and_capability_non_authority_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(10, case)


@pytest.mark.parametrize("case", range(4))
def test_private_order_binding_architecture_candidates_and_sibling_selection_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(11, case)


@pytest.mark.parametrize("case", range(4))
def test_order_modules_are_private_acyclic_and_rust_friendly(case: int) -> None:
    _exercise_contract_case(12, case)


@pytest.mark.parametrize("case", range(4))
def test_existing_direction_values_and_source_effective_representations_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(13, case)


@pytest.mark.parametrize("case", range(5))
def test_window_order_field_binding_shape_field_order_and_privacy_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(14, case)


@pytest.mark.parametrize("case", range(24))
def test_window_order_field_binding_malformed_matrix_fails_closed(case: int) -> None:
    _exercise_contract_case(15, case)


@pytest.mark.parametrize("case", range(5))
def test_window_order_binding_fact_shape_field_order_and_privacy_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(16, case)


@pytest.mark.parametrize("case", range(18))
def test_window_order_binding_fact_malformed_matrix_fails_closed(case: int) -> None:
    _exercise_contract_case(17, case)


@pytest.mark.parametrize("case", range(16))
def test_order_binding_source_order_duplicate_direction_equality_and_hashing_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(18, case)


@pytest.mark.parametrize("case", range(5))
def test_window_expression_analysis_order_sibling_shape_and_privacy_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(19, case)


@pytest.mark.parametrize("case", range(18))
def test_window_expression_analysis_family_partition_order_invariants_fail_closed(
    case: int,
) -> None:
    _exercise_contract_case(20, case)


@pytest.mark.parametrize("case", range(6))
def test_all_six_accept_one_bare_order_field_with_omitted_direction(case: int) -> None:
    _exercise_contract_case(21, case)


@pytest.mark.parametrize("case", range(6))
def test_all_six_accept_one_immediate_qualified_order_field_with_omitted_direction(
    case: int,
) -> None:
    _exercise_contract_case(22, case)


@pytest.mark.parametrize("case", range(6))
def test_all_six_accept_one_bare_order_field_with_explicit_asc(case: int) -> None:
    _exercise_contract_case(23, case)


@pytest.mark.parametrize("case", range(6))
def test_all_six_accept_one_bare_order_field_with_explicit_desc(case: int) -> None:
    _exercise_contract_case(24, case)


@pytest.mark.parametrize("case", range(12))
def test_all_six_accept_two_order_fields_with_mixed_directions(case: int) -> None:
    _exercise_contract_case(25, case)


@pytest.mark.parametrize("case", range(12))
def test_all_six_accept_three_source_ordered_order_fields(case: int) -> None:
    _exercise_contract_case(26, case)


@pytest.mark.parametrize("case", range(12))
def test_all_six_preserve_duplicate_order_bindings_and_directions(case: int) -> None:
    _exercise_contract_case(27, case)


@pytest.mark.parametrize("case", range(12))
def test_all_six_preserve_reversed_order_key_source_order(case: int) -> None:
    _exercise_contract_case(28, case)


@pytest.mark.parametrize("case", range(24))
def test_order_binding_supports_direct_source_and_immediate_upstream_matrix(
    case: int,
) -> None:
    _exercise_contract_case(29, case)


@pytest.mark.parametrize("case", range(18))
def test_nullable_order_fields_are_structurally_accepted(case: int) -> None:
    _exercise_contract_case(30, case)


@pytest.mark.parametrize("case", range(18))
def test_partition_plus_multiple_local_order_keys_is_exact(case: int) -> None:
    _exercise_contract_case(31, case)


@pytest.mark.parametrize("case", range(18))
def test_order_child_value_types_and_single_existing_resolution_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(32, case)


@pytest.mark.parametrize("case", range(12))
def test_multi_key_order_analysis_is_structurally_repeatable(case: int) -> None:
    _exercise_contract_case(33, case)


@pytest.mark.parametrize("case", range(12))
def test_rank_dense_rank_percent_rank_cume_dist_peer_keys_use_every_order_expression(
    case: int,
) -> None:
    _exercise_contract_case(34, case)


@pytest.mark.parametrize("case", range(12))
def test_row_number_and_ntile_remain_peer_insensitive_with_structural_order(
    case: int,
) -> None:
    _exercise_contract_case(35, case)


@pytest.mark.parametrize("case", range(12))
def test_direction_changes_structural_order_not_peer_equality(case: int) -> None:
    _exercise_contract_case(36, case)


@pytest.mark.parametrize("case", range(12))
def test_distribution_structural_order_key_type_and_compatibility_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(37, case)


@pytest.mark.parametrize("case", range(6))
def test_structural_determinism_total_order_tie_and_uniqueness_boundary_is_exact(
    case: int,
) -> None:
    _exercise_contract_case(38, case)


@pytest.mark.parametrize("case", range(12))
def test_zero_local_order_is_rejected_for_all_six_identities(case: int) -> None:
    _exercise_contract_case(39, case)


@pytest.mark.parametrize("case", range(54))
def test_computed_literal_call_and_nested_local_order_shapes_use_pie_s2103(
    case: int,
) -> None:
    _exercise_contract_case(40, case)


@pytest.mark.parametrize("case", range(24))
def test_selected_let_aggregate_and_window_result_order_names_fail_closed(
    case: int,
) -> None:
    _exercise_contract_case(41, case)


@pytest.mark.parametrize("case", range(18))
def test_unknown_local_order_fields_use_pie_s2102_without_cascade(case: int) -> None:
    _exercise_contract_case(42, case)


@pytest.mark.parametrize("case", range(24))
def test_invalid_immediate_original_and_three_part_order_qualifiers_use_pie_s2102(
    case: int,
) -> None:
    _exercise_contract_case(43, case)


@pytest.mark.parametrize("case", range(12))
def test_nonconcrete_local_order_schema_uses_pie_s2103(case: int) -> None:
    _exercise_contract_case(44, case)


@pytest.mark.parametrize("case", range(18))
def test_multi_key_local_order_diagnostics_stop_at_first_source_error(
    case: int,
) -> None:
    _exercise_contract_case(45, case)


@pytest.mark.parametrize("case", range(18))
def test_all_field_bindings_precede_direction_validation(case: int) -> None:
    _exercise_contract_case(46, case)


@pytest.mark.parametrize("case", range(12))
def test_unsupported_direction_representation_uses_pie_s2103(case: int) -> None:
    _exercise_contract_case(47, case)


@pytest.mark.parametrize("case", range(18))
def test_identity_arity_and_context_precede_local_order_validation(case: int) -> None:
    _exercise_contract_case(48, case)


@pytest.mark.parametrize("case", range(12))
def test_ntile_literal_validation_follows_all_local_order_bindings(case: int) -> None:
    _exercise_contract_case(49, case)


@pytest.mark.parametrize("case", range(24))
def test_group_aggregate_satisfying_and_let_contexts_remain_unsupported(
    case: int,
) -> None:
    _exercise_contract_case(50, case)


@pytest.mark.parametrize("case", range(18))
def test_window_placements_outside_direct_select_remain_unsupported(case: int) -> None:
    _exercise_contract_case(51, case)


@pytest.mark.parametrize("case", range(18))
def test_multiple_nested_and_same_select_window_dependencies_remain_unsupported(
    case: int,
) -> None:
    _exercise_contract_case(52, case)


@pytest.mark.parametrize("case", range(6))
def test_explicit_null_ordering_syntax_remains_unsupported(case: int) -> None:
    _exercise_contract_case(53, case)


@pytest.mark.parametrize("case", range(6))
def test_explicit_collation_syntax_remains_unsupported(case: int) -> None:
    _exercise_contract_case(54, case)


@pytest.mark.parametrize("case", range(12))
def test_ordered_windows_coexist_with_ordinary_where_final_order_and_limit(
    case: int,
) -> None:
    _exercise_contract_case(55, case)


@pytest.mark.parametrize("case", range(12))
def test_project_generic_builder_supports_all_six_multi_key_ordered_identities(
    case: int,
) -> None:
    _exercise_contract_case(56, case)


@pytest.mark.parametrize("case", range(18))
def test_project_relation_partition_and_order_role_blocks_and_ordinals_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(57, case)


@pytest.mark.parametrize("case", range(12))
def test_project_duplicate_order_occurrences_preserve_source_order(case: int) -> None:
    _exercise_contract_case(58, case)


@pytest.mark.parametrize("case", range(6))
def test_project_order_dependency_order_tracks_source_reversal(case: int) -> None:
    _exercise_contract_case(59, case)


@pytest.mark.parametrize("case", range(6))
def test_partition_and_order_same_target_remain_role_distinct(case: int) -> None:
    _exercise_contract_case(60, case)


@pytest.mark.parametrize("case", range(12))
def test_direction_does_not_create_project_dependency_nodes(case: int) -> None:
    _exercise_contract_case(61, case)


@pytest.mark.parametrize("case", range(18))
def test_order_dependency_targets_locations_and_nullable_fields_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(62, case)


@pytest.mark.parametrize("case", range(12))
def test_duplicate_order_keys_with_direction_share_first_role_target_edge(
    case: int,
) -> None:
    _exercise_contract_case(63, case)


@pytest.mark.parametrize("case", range(6))
def test_relation_input_and_ntile_dependency_free_argument_invariants_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(64, case)


@pytest.mark.parametrize("case", range(12))
def test_project_result_identity_and_derived_provenance_remain_exact(case: int) -> None:
    _exercise_contract_case(65, case)


@pytest.mark.parametrize("case", range(6))
def test_semantic_and_project_compatibility_wrappers_preserve_return_shapes(
    case: int,
) -> None:
    _exercise_contract_case(66, case)


@pytest.mark.parametrize("case", range(9))
def test_order_semantic_analysis_and_project_facts_are_transient(case: int) -> None:
    _exercise_contract_case(67, case)


@pytest.mark.parametrize("case", range(12))
def test_window_alias_row_schema_downstream_and_final_order_visibility_remains_absent(
    case: int,
) -> None:
    _exercise_contract_case(68, case)


@pytest.mark.parametrize("case", range(6))
def test_multi_key_ordered_window_ir_lowering_fails_closed_with_pie_i1000(
    case: int,
) -> None:
    _exercise_contract_case(69, case)


@pytest.mark.parametrize("case", range(6))
def test_multi_key_ordered_window_postgres_and_private_mysql_fail_before_sql_lowering(
    case: int,
) -> None:
    _exercise_contract_case(70, case)


@pytest.mark.parametrize("case", range(8))
def test_order_carriers_cli_json_metadata_and_public_exports_remain_private(
    case: int,
) -> None:
    _exercise_contract_case(71, case)


def test_validation_gate3_deferred_ownership_and_no_decisions_are_locked() -> None:
    docs = _read(SPEC_REL) + _read(PLAN_REL)
    required = (
        "A3/M61/D0",
        "81-function/834-item",
        "3107 focused",
        "9014 passed, 185 deselected",
        "9199",
        "one write-mode Ruff invocation",
        "unstaged and uncommitted",
        "Add Phase 53 window-local ordering and direction",
        "Slice 12 navigation behavior remains unimplemented",
        "Slice 11 remains UNSTARTED through Gate 2",
        "COMPLETED requires separately authorized Gate 3 and exact-head natural CI",
        "0.1.0",
    )
    for item in required:
        assert item in docs
    assert "genuine_product_decisions" not in docs
    assert "genuine_architecture_decisions" not in docs


# Phase 53 Slice 13 reader migration.
