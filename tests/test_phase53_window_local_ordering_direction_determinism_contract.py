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


def _phase53_gate2_paths(name: str) -> set[str]:
    if _git_output(["rev-parse", "HEAD"]) in {
        "d8a5e9ab3de70ce30575513c73560c86430eca63",
        "15bae172ee151e370fe59d3bf909d735aee6aa90",
        "0f3c955c5a5fbd8046ef611ad1bef0b636c8be01",
        "c44a4271d9592cb393d2232f127a59d8466cc60a",
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


def _phase54_slice4_state() -> tuple[set[str], set[str]] | None:
    modified = _phase53_gate2_paths("MODIFIED_PATHS")
    added = _phase53_gate2_paths("ADDED_PATHS")
    tracked = set(_git_output(["diff", "--name-only"]).splitlines()) - {""}
    untracked = set(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    ) - {""}
    if (
        _git_output(["rev-parse", "HEAD"])
        in {
            "15bae172ee151e370fe59d3bf909d735aee6aa90",
            "0f3c955c5a5fbd8046ef611ad1bef0b636c8be01",
            "c44a4271d9592cb393d2232f127a59d8466cc60a",
        }
        and tracked == modified
        and untracked == added
    ):
        return modified, added
    return None


_SLICE10_MODIFIED_PATHS = _literal_tuple(SLICE10_REL, "MODIFIED_PATHS")
_SLICE10_FOCUSED_OPERANDS = _literal_tuple(SLICE10_REL, "FOCUSED_OPERANDS")
_SLICE10_DIRTY_OVERLAY = _literal_tuple(SLICE10_REL, "DIRTY_OVERLAY")
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
ALLOWLIST_PATHS = frozenset((*ADDED_PATHS, *MODIFIED_PATHS))

# Populated with formatting-neutral literals after the sole write formatter.
FINAL_SHA256: dict[str, str] = {
    "docs/spec/phase53-window-ir-dual-backend-lowering-window-function-facts-contract-v1.md": "4ef55e40d3c176319d9316f14203a1f4991dd2e7086fa710ebca5c81f6737158",
    "src/pietto/semantic/capability_windows.py": "c0512933fc284bbc1dec98dab96411ee179d64e7bee005aa798b6fd7dba2024e",
    "tests/test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py": "66153762af9682d8e3d72069d4bb2fdd5bbbc9f574ade48100c2103fff0c3f24",
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
    "tests/test_phase11_ci_workflow.py": "d5590b1606c68e5d201a346b375cc3f711b522b22958603401ada3899e5442e0",
    "tests/test_phase11_completion_audit.py": "e245d5c09781a254bd7cb86df42df023a1978f096b72a7f6b39bd7b5509e1904",
    "tests/test_phase11_generated_guard.py": "950f4d1651bfb932eaac552e26ae788e8eef8795cf37ef29d21f9abc3b739b60",
    "tests/test_phase11_golden_policy.py": "7127e5bfa18f9948e511381b772092cf7083c64fbd240fa1f34bffa2d3883782",
    "tests/test_phase11_packaging_smoke.py": "345ce56ea0de926d1d9378369ca8d5d2a9fff9e6544bdc95a182df18fbfbf18d",
    "tests/test_phase11_planning_audit.py": "7a8f1d90196cdb4c863ca74d1901458ac692284f20240b08d423dea12884f91c",
    "tests/test_phase11_validation_entrypoint.py": "a20169ad55a14595b266199bf61cb9034b94374864227d9b76853c304ff1f990",
    "tests/test_phase12_completion_audit.py": "0de04470e0708bc914ea8113088023d1c52792f0572cd65caa6478fd8073d72d",
    "tests/test_phase12_composition_cli_json_goldens.py": "0991a2dba3a0786ec94a660fabf10b736fa237241a53588c70ebf95811ec2b12",
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
    "tests/test_phase16_completion_audit.py": "3a12ed927cddb1a68e21900109f1588e40a5d434e2e0f1040c1c51c635de9ecb",
    "tests/test_phase16_current_syntax_surface_audit.py": "09152dc891fcf671488209370bd742db3625f70dd57db64716476db5bbe99518",
    "tests/test_phase16_language_direction_audit.py": "65fcb93f6e413c75e2097fc1f985faef749ebda30b7c5004e2cc1ed6178b2462",
    "tests/test_phase16_safety_deferral_sql_portability.py": "f45aba956336efd635cf5d0656468da463de4e0bc55596c1bf0ea44acdbc586e",
    "tests/test_phase21_group_by_hardening_audit.py": "4cb834a37bdc9081d2b17e86aea5da48b79958d25cf7c5c6ff1c270dc462f9e2",
    "tests/test_phase24_aggregate_expression_arguments_readiness.py": "cb9b16d29b1528acef16d810deb96025a9ab31d72a82b3a2ed5bbbc94618a1ce",
    "tests/test_phase24_cli_json_output_hardening.py": "dfbb6595216fd6b68d4f7e3763a69e97b97265253996f66d09d78644e7631b8f",
    "tests/test_phase24_completion_audit.py": "bbdf796b7f343d2f81e69e69455ce04538da5a9280e9f411e97f8c6befccc807",
    "tests/test_phase25_completion_audit.py": "786ef6fa0ace267d45294045e97b6b5880af524b17c02a323204896564da8c83",
    "tests/test_phase26_completion_audit.py": "aab0d57b285ea137149b70d0ffc042f3f84609f638962c02eeb3af58f331001b",
    "tests/test_phase27_completion_audit.py": "640e9563a14c7c25fd3a626c9b011905ba5f355fbcab5decceb5728a473c218d",
    "tests/test_phase28_completion_audit.py": "4e09318d3c977906d9c8bfde86be676bf2ae546862a6cd442208561976e86631",
    "tests/test_phase29_completion_audit.py": "fa5d34d80068acaee6d33eb06655ea000ece9e3b6e526e42f064a6297b7c00db",
    "tests/test_phase30_completion_audit.py": "c8b0405d75363ff6723b31176ed1627ae51a0ad2575bd227c0224cc0d714d5bf",
    "tests/test_phase50_window_function_readiness.py": "75160c478d7bd3b72850f1c4fcbc640c9faf0bd733f899e604e93c567bf742b4",
    "tests/test_phase51_completion_audit_and_status_lock.py": "e751f65c0f4ccb485f8e46c12d78da5ac303997f8b60cc5fe3d7126520f8b7f5",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py": "797256285034ca6ef9ae94dc4bb2b678b4bf7f3b74df9ea7c7e3c658e8bd6191",
    "tests/test_phase52_aggregate_signature_algebra_facts.py": "b5ccd9ad4d7b911c2801e43c225bec6251ab9f443cd0ef2fd60ecec46d13ea71",
    "tests/test_phase52_completion_audit_and_status_lock.py": "f0216697c4dbeb9ff8e7496c7a7141755c96267e89d7dcb605565870c4b594e8",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py": "4fcaa26885c05fdada583e7800232a76ca6bd1206959451ff865b15c9abfc23d",
    "tests/test_phase52_expression_stage_clause_capability_facts.py": "e6d5d6287060aebd2ab16db39b7d754824d066006f759cd333e30169977ceddf",
    "tests/test_phase52_fail_closed_capability_lookup.py": "1db93235400d49965244ac9db170151e343e8edd4565ca73f59d62b1b0242cd5",
    "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py": "67892020e1b4f58eaea4d8bbda630fb24abc8843172db4752b2273edf0f83ea0",
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py": "e9493ce34d94c77f7ba2b120cf0befd44854feb253c318dd2a7272cf40e11a6f",
    "tests/test_phase52_private_capability_fact_foundation.py": "0536e4dbdce945b7990b019c99205a452ee417a4cf421af707790879c15c9e1a",
    "tests/test_phase52_scalar_function_operator_signature_facts.py": "f04fa9581bc37da1df0d037b6638fa5daa9aedabd5e8583a4b129f2afaff35ec",
    "tests/test_phase53_generic_type_variable_exact_compatibility_contract.py": "d3eee31623559d107f4d8b38b1b3100825da929aa8fc2d2305d64454f0558f9b",
    "tests/test_phase53_grouped_result_ranking_aggregate_result_inputs_bounded_let_visibility_contract.py": "6fc048d448bc5509074bbebb45260a2c39172083415267d54b74353455bf668b",
    "tests/test_phase53_multiple_window_outputs_final_order_alias_downstream_schema_lineage_contract.py": "1277e0535b15a724cef72e0ca5ae23970528c9ecbea8c49364d2a5c7faa1ff0f",
    "tests/test_phase53_nullability_algebra_signature_result_formula_contract.py": "640264a301985edab1531edc21154b7034501f4949910359b93db684f0442196",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py": "b8f24cd42e9e30d5a05a41bb05bfcce9b9d82b7e2d879d599a0c5ae887ddf11a",
    "tests/test_phase53_percent_rank_cume_dist_ntile_contract.py": "cc3b1d91db96162bd7e96bf60b911713607b1a8fed1b7b56d6cb088916f4eae5",
    "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py": "fe41e143a7be5306f8d604fa3a68a1ba3e8b97af09dbee18892a218962e22c29",
    "tests/test_phase53_rank_dense_rank_peer_semantics_contract.py": "2fdd6f29f8c5ad6c4587549cf361986495ad91b3339ff203dbeb91e491fbd294",
    "tests/test_phase53_row_number_direct_field_mvp_contract.py": "84580d66a10d88002646d3aac18da8fab74bddac34a9f24e6a6f576480904d92",
    "tests/test_phase53_window_generic_nullability_foundation_scope_lock.py": "42e08e1ab05581675b4b3ed4e7dff4722b839766184c2825e9b26535b89fbd81",
    "tests/test_phase53_window_spec_function_identity_ast_contract.py": "04e9d9a24ee3f31f6f13da158f8661f729ee7b97ac11acab355f28c551ba3c2a",
    "tests/test_phase53_window_syntax_contextual_grammar_contract.py": "2fe6c529e3f5efae04d500b833b37c819b3c1a6d306d7a16ad957bdf162b7994",
    "tests/test_ir_completion_audit.py": "e1467d8191883640e1beca8731b92ccf7c7ce9a25fc74d98664d12195051bf6e",
    "tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py": "144566f742a8ec414a0c8d8f8da8e5ce555152b59c01facad3f39391d1802385",
}
COMPILER_DIGEST = "395fcfbd790382e22aa4ed7ee07b45d10b079b7a53b6dc872e70314ff4bb195c"
SEMANTIC_DIGEST = "731e17cc85849c7716abeb08abeda03f72e3e21af183a391107adf96ccab6d70"
PHASE15_SUBSET_DIGEST = (
    "81db265a7bbd290b9c9227733e92dc502f8e8c8f0ff76b4d631651772876550d"
)
PROJECT_DIGEST = "75b90306fdb66ebb6b5ca140a88def5b71582d20da9e3dec7cc726d551521056"

FOCUSED_SHA256 = "fb685c521c70d879e0e3e751c434cf142700d82a66976961ca8036e8965b3429"
OVERLAY_SHA256 = "197b591aec962f43b9b9393da99a76ff21c3a36189cc02c7a75dc5a7b85d6b26"
FORMATTER_SHA256 = "2a733e091f94fb565c9fd3a86b93058bbdc2f032941fb75a1e1e589c29581a5c"


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
            elif isinstance(values, ast.Name):
                named_values: ast.expr | None = None
                for node in tree.body:
                    if (
                        isinstance(node, ast.Assign)
                        and len(node.targets) == 1
                        and isinstance(node.targets[0], ast.Name)
                        and node.targets[0].id == values.id
                    ):
                        named_values = node.value
                        break
                    if (
                        isinstance(node, ast.AnnAssign)
                        and isinstance(node.target, ast.Name)
                        and node.target.id == values.id
                    ):
                        named_values = node.value
                        break
                assert named_values is not None
                literal_values = ast.literal_eval(named_values)
                assert isinstance(literal_values, (list, tuple))
                cardinality *= len(literal_values)
            else:
                assert isinstance(values, ast.Call)
                assert isinstance(values.func, ast.Name) and values.func.id == "range"
                assert len(values.args) == 1
                bound = values.args[0]
                assert isinstance(bound, ast.Constant) and type(bound.value) is int
                cardinality *= bound.value
        cardinalities.append(cardinality)
    return tuple(function.name for function in functions), tuple(cardinalities)


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
        protected = (
            "src/pietto/__init__.py",
            "src/pietto/cli.py",
            "src/pietto/cli_json.py",
            "src/pietto/_project/json_v2.py",
            "src/pietto/_metadata/serializer.py",
            "src/pietto/semantic/__init__.py",
            "src/pietto/ir/__init__.py",
            "src/pietto/sql/postgres.py",
        )
        assert _git_output(["diff", "--", protected[case]]) == ""
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


def test_slice11_artifact_paths_headings_and_lifecycle_are_exact() -> None:
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
        ).count(SLICE11_PLAN_H2)
        == 1
    )
    functions, cardinalities = _test_manifest(SELF_REL)
    assert functions == EXPECTED_TEST_FUNCTIONS
    assert cardinalities == CARDINALITIES
    assert len(functions) == 81
    assert sum(cardinalities) == 834
    names_payload = ("\n".join(functions) + "\n").encode()
    cardinality_payload = (
        "\n".join(
            f"{name}={cardinality}"
            for name, cardinality in zip(functions, cardinalities, strict=True)
        )
        + "\n"
    ).encode()
    assert len(names_payload) == 5470
    assert hashlib.sha256(names_payload).hexdigest() == (
        "3537c206c74f0f9ead4f657793a11a3f44f0f9d017c1849b31602f8bee32a75c"
    )
    assert len(cardinality_payload) == 5672
    assert hashlib.sha256(cardinality_payload).hexdigest() == (
        "867033de15c2cf35ac99cf821faa900b51c916ed5776d37e1d0206f8fd7ac5ce"
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


def test_all_627_slice10_items_and_completed_partition_contract_remain_locked() -> None:
    functions, cardinalities = _test_manifest(SLICE10_REL)
    assert len(functions) == 67
    assert sum(cardinalities) == 627


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
        "src/pietto/ir/__init__.py",
        "src/pietto/sql/postgres.py",
        "src/pietto/sql/mysql.py",
        "pyproject.toml",
        "uv.lock",
        ".github/workflows/ci.yml",
    )
    changed = set(
        _git_output(["diff", "--name-only", "--", *protected]).splitlines()
    ) - {""}
    phase54_state = _phase54_slice4_state()
    if phase54_state is None:
        assert changed == set()
    else:
        phase54_modified, _ = phase54_state
        assert changed == phase54_modified & set(protected)
    generated = tuple(
        path for path in _repository_paths() if path.startswith("src/pietto/generated/")
    )
    assert len(generated) == 8


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
    ) == (99, 36, 33, 24)
    assert _digest(compiler_paths) == COMPILER_DIGEST
    assert _digest(semantic_paths) == SEMANTIC_DIGEST
    assert _digest(phase15_paths) == PHASE15_SUBSET_DIGEST
    assert _digest(project_paths) == PROJECT_DIGEST
    assert set(FINAL_SHA256) == set(ALLOWLIST_PATHS) - {
        SELF_REL,
        CURRENT_TEST_REL,
    }
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


def test_slice11_dirty_clean_and_depth_one_repository_states_are_locked() -> None:
    tracked = set(_git_output(["diff", "--name-only"]).splitlines()) - {""}
    untracked = set(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    ) - {""}
    assert _git_output(["diff", "--cached", "--name-status"]) == ""
    dirty = tracked | untracked
    slice14_modified = _phase53_gate2_paths("MODIFIED_PATHS")
    slice14_added = _phase53_gate2_paths("ADDED_PATHS")
    assert dirty in (set(), set(ALLOWLIST_PATHS), slice14_modified | slice14_added)
    assert tracked in (set(), set(MODIFIED_PATHS), slice14_modified)
    assert untracked in (set(), set(ADDED_PATHS), slice14_added)
    head = _git_output(["rev-parse", "HEAD"])
    if dirty:
        assert head in (
            BASE_HEAD_SHA,
            "d8a5e9ab3de70ce30575513c73560c86430eca63",
            "15bae172ee151e370fe59d3bf909d735aee6aa90",
            "0f3c955c5a5fbd8046ef611ad1bef0b636c8be01",
            "c44a4271d9592cb393d2232f127a59d8466cc60a",
        )
        assert _git_output(["branch", "--show-current"]) == "main"
        assert _git_optional_ref("refs/heads/main") == head
        assert _git_optional_ref("refs/remotes/origin/main") == head
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
    ) == (903, 555, 252, 455, 4998)
    added_payload = ("\n".join(ADDED_PATHS) + "\n").encode()
    modified_payload = ("\n".join(MODIFIED_PATHS) + "\n").encode()
    changed_payload = (
        "".join(f"A  {path}\n" for path in ADDED_PATHS)
        + "".join(f"M  {path}\n" for path in MODIFIED_PATHS)
    ).encode()
    focused_payload = ("\n".join(FOCUSED_OPERANDS) + "\n").encode()
    overlay_payload = ("\n".join(DIRTY_OVERLAY) + "\n").encode()
    formatter_payload = ("\n".join(FORMATTER_PATHS) + "\n").encode()
    assert (len(ADDED_PATHS), len(added_payload)) == (3, 214)
    assert hashlib.sha256(added_payload).hexdigest() == (
        "843d8242821834b8789b038cb3ffcecb81d403444f9053dc2d594c2da12cba4e"
    )
    assert (len(MODIFIED_PATHS), len(modified_payload)) == (73, 3762)
    assert hashlib.sha256(modified_payload).hexdigest() == (
        "08b43f65e3ec0e3039c9515176185477c02d053f61eb5a3c10c11ce4b8274058"
    )
    assert (len(ALLOWLIST_PATHS), len(changed_payload)) == (76, 4204)
    assert hashlib.sha256(changed_payload).hexdigest() == (
        "1c750f0c25e21b2abbd3626a3323a4c1311a69070d9dcd89f5ee5178196e1f7b"
    )
    assert (len(FOCUSED_OPERANDS), len(focused_payload)) == (134, 15130)
    assert hashlib.sha256(focused_payload).hexdigest() == FOCUSED_SHA256
    assert len({item.split("::", 1)[0] for item in FOCUSED_OPERANDS}) == 80
    assert sum("::" not in item for item in FOCUSED_OPERANDS) == 14
    assert sum("::" in item for item in FOCUSED_OPERANDS) == 120
    assert len(DIRTY_OVERLAY) == 185
    assert len({item.split("::", 1)[0] for item in DIRTY_OVERLAY}) == 137
    assert len(overlay_payload) == 23628
    assert hashlib.sha256(overlay_payload).hexdigest() == OVERLAY_SHA256
    assert len(FORMATTER_PATHS) == len(set(FORMATTER_PATHS)) == 72
    assert len(formatter_payload) == 3700
    assert hashlib.sha256(formatter_payload).hexdigest() == FORMATTER_SHA256
    assert 10784 == 10576 + 208
    assert 10599 == 10784 - 185
    assert 4765 == 4557 + 208


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
