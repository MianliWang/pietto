from __future__ import annotations

import ast
import hashlib
import re
import subprocess
import tomllib
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

from _phase54_active_gate2_manifest import (
    phase54_post_slice12_interlude_dirty_is_active,
    phase54_post_slice12_interlude_expected_added_paths,
    phase54_post_slice12_interlude_expected_modified_paths,
    PHASE54_POST_SLICE12_INTERLUDE_BRANCH,
    phase54_post_slice12_interlude_clean_topic_is_active,
    PHASE54_ACTIVE_GATE2_ADDED_PATHS,
    PHASE54_ACTIVE_GATE2_MODIFIED_PATHS,
    PHASE54_SLICE11_PR_CI_REPAIR_MODIFIED_PATHS,
    PHASE54_SLICE12_PR_CI_REPAIR_MODIFIED_PATHS,
    PHASE54_SLICE12_MECHANICAL_REPAIR3_BASE,
    PHASE54_SLICE12_MECHANICAL_REPAIR3_BRANCH,
    PHASE54_SLICE12_MECHANICAL_REPAIR3_MODIFIED_PATHS,
    PHASE54_SLICE12_MECHANICAL_REPAIR3_SUBJECT,
    PHASE54_SLICE12_MECHANICAL_REPAIR4_BASE,
    PHASE54_SLICE12_MECHANICAL_REPAIR4_BRANCH,
    PHASE54_SLICE12_MECHANICAL_REPAIR4_MODIFIED_PATHS,
    PHASE54_SLICE12_MECHANICAL_REPAIR4_SUBJECT,
    PHASE54_SLICE12_PRODUCT_REPAIR3_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR10_BASE,
    PHASE54_SLICE12_PRODUCT_REPAIR10_BRANCH,
    PHASE54_SLICE12_PRODUCT_REPAIR10_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR10_SUBJECT,
    PHASE54_SLICE12_PRODUCT_REPAIR11_BASE,
    PHASE54_SLICE12_PRODUCT_REPAIR11_BRANCH,
    PHASE54_SLICE12_PRODUCT_REPAIR11_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR11_SUBJECT,
    PHASE54_SLICE12_PRODUCT_REPAIR12_BASE,
    PHASE54_SLICE12_PRODUCT_REPAIR12_BRANCH,
    PHASE54_SLICE12_PRODUCT_REPAIR12_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR12_SUBJECT,
    PHASE54_SLICE12_PRODUCT_REPAIR13_BASE,
    PHASE54_SLICE12_PRODUCT_REPAIR13_BRANCH,
    PHASE54_SLICE12_PRODUCT_REPAIR13_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR13_SUBJECT,
    PHASE54_SLICE12_PRODUCT_REPAIR14_BASE,
    PHASE54_SLICE12_PRODUCT_REPAIR14_BRANCH,
    PHASE54_SLICE12_PRODUCT_REPAIR14_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR14_SUBJECT,
    PHASE54_SLICE11_PYTHON313_REPAIR_MODIFIED_PATHS,
    PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_MODIFIED_PATHS,
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
    phase54_slice11_pr_ci_repair_is_active,
    phase54_slice12_pr_ci_repair_is_active,
    phase54_slice12_mechanical_repair3_clean_topic_is_active,
    phase54_slice12_mechanical_repair3_is_active,
    phase54_slice12_mechanical_repair4_clean_topic_is_active,
    phase54_slice12_mechanical_repair4_is_active,
    phase54_slice12_product_repair3_clean_topic_is_active,
    phase54_slice12_product_repair10_clean_topic_is_active,
    phase54_slice12_product_repair11_clean_topic_is_active,
    phase54_slice12_product_repair12_clean_topic_is_active,
    phase54_slice12_product_repair13_clean_topic_is_active,
    phase54_slice12_product_repair14_clean_topic_is_active,
    phase54_slice12_product_repair3_is_active,
    phase54_slice12_product_repair10_is_active,
    phase54_slice12_product_repair11_is_active,
    phase54_slice12_product_repair12_is_active,
    phase54_slice12_product_repair13_is_active,
    phase54_slice12_product_repair14_is_active,
    phase54_slice11_python313_repair_is_active,
    phase54_slice11_substantive_recovery_is_active,
)

import pytest

import pietto.semantic.capability_aggregates as capability_aggregates
from pietto.semantic.capability_facts import (
    CapabilityDispositionKind,
    CapabilityDomain,
    CapabilityEvidenceSource,
    CapabilityFact,
    CapabilityKey,
    CapabilityReasonCode,
    CapabilitySupport,
)
from pietto.semantic.capability_lookup import (
    Absent,
    Conflict,
    Found,
    Unknown,
    lookup_capability,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_REL = "src/pietto/semantic/capability_aggregates.py"
INVENTORY_REL = "src/pietto/semantic/capability_inventory.py"
SIGNATURE_REL = "src/pietto/semantic/capability_signatures.py"
SPEC_REL = "docs/spec/phase52-aggregate-signature-algebra-facts-v1.md"
SELF_REL = "tests/test_phase52_aggregate_signature_algebra_facts.py"
SOURCE_PATH = REPO_ROOT / SOURCE_REL
SPEC_PATH = REPO_ROOT / SPEC_REL
SELF_PATH = REPO_ROOT / SELF_REL
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

GATE2_BASE_HEAD_SHA = "db855822065f09f327b9fa243192445e4b9fa3f9"
PR_REPAIR_GATE2_BRANCH = "dependabot/uv/uv-build-gte-0.11.29-and-lt-0.12.0"
PR_REPAIR_GATE2_HEAD_SHA = "8538e9e612c4a39b93a43f85532bfcb75853f9c1"
PR_REPAIR_GATE2_MAIN_SHA = "522ce4ea193c3b2bbbe88644d77a2410230f42ad"
PR_REPAIR_GATE2_ORIGIN_REF = f"refs/remotes/origin/{PR_REPAIR_GATE2_BRANCH}"
COMPLETENESS_REPAIR_GATE2_BASE_HEAD_SHA = "b1d5002fb48dbbb06cc93de2261e2237655e0eab"
FACTS_SHA256 = "bd68bad4e13a2b945962458fc47359a408d27b1563ba25f5713a8f8099671d21"
LOOKUP_SHA256 = "4d4c2676b3181758f01c95ca312fd0f76cebcb74ac1bcab0deefb15fc04abf26"
INVENTORY_SHA256 = "f11eee2a53fda26057c35be047bfa265c68794ad76054bc5636781f0b5164b26"
SIGNATURE_SHA256 = "810f347080e0bb7dc674821aa6387c5f7618ac216832194ef19820326eef71d2"
CONTEXT_SHA256 = "132371eccca00ca9f8722a34f1ea0f540933515e560639ee12e53aee6594c60c"
COMPILER_DIGEST = "f9eca1bf5cadfcc1583ba465f33bf761114e6d9d2785de15a2d73b5a19a6ff62"
SEMANTIC_DIGEST = "731e17cc85849c7716abeb08abeda03f72e3e21af183a391107adf96ccab6d70"
PHASE15_SUBSET_DIGEST = (
    "81db265a7bbd290b9c9227733e92dc502f8e8c8f0ff76b4d631651772876550d"
)
PROJECT_PRIVATE_DIGEST = (
    "9269d0946eaa232a4471633214d6fc55cd69b55d684edba3213532242224183b"
)

SPEC_H2 = (
    "Status And Authority",
    "Private Aggregate Module And Ordering",
    "Signature Key Encoding And Completeness",
    "Exact Aggregate Signature Inventory",
    "Result Type Nullability Stage And Role",
    "Algebra Key Encoding And Completeness",
    "Empty Input Null Duplicate And Availability Facts",
    "Row Let Alias Shape And Expression Policy",
    "Distinct Filter Modifier And Window Policy",
    "Nested Global Grouped And Clause Boundary",
    "Four-result Lookup And Conflict Preservation",
    "Evidence Ordering Backend Parity And Authority",
    "Privacy Static Compatibility And Validation Locks",
    "Active Conflict Ledger And Omission Policy",
    "Slice Ownership Lifecycle And Release Boundary",
)

SLICE2_TEST_REL = "tests/test_phase52_private_capability_fact_foundation.py"
SLICE3_TEST_REL = "tests/test_phase52_fail_closed_capability_lookup.py"
SLICE4_TEST_REL = (
    "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py"
)
SLICE5_TEST_REL = "tests/test_phase52_scalar_function_operator_signature_facts.py"
SLICE6_TEST_REL = "tests/test_phase52_expression_stage_clause_capability_facts.py"
SLICE8_SPEC_REL = (
    "docs/spec/phase52-parity-privacy-cross-phase-readiness-drift-closure-v1.md"
)
SLICE8_TEST_REL = (
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py"
)
SLICE8_GATE2_BASE_HEAD_SHA = "11a0c48941c3c1c650be8d0ec8ddf5201f9525f2"
SLICE9_SPEC_REL = "docs/spec/phase52-completion-audit-and-status-lock-v1.md"
SLICE9_TEST_REL = "tests/test_phase52_completion_audit_and_status_lock.py"
SLICE9_BASE_HEAD_SHA = "36e466535d923f708a0201ae15a5708f06f2b1f8"

COMPILER_READERS = (
    "tests/test_phase53_completion_audit_and_status_lock.py",
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_packaging_smoke.py",
    "tests/test_phase11_validation_entrypoint.py",
    "tests/test_phase12_completion_audit.py",
    "tests/test_phase12_composition_cli_json_goldens.py",
    "tests/test_phase51_completion_audit_and_status_lock.py",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
    "tests/test_phase52_aggregate_signature_algebra_facts.py",
    "tests/test_phase52_completion_audit_and_status_lock.py",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py",
    "tests/test_phase52_fail_closed_capability_lookup.py",
    "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py",
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
    "tests/test_phase53_generic_type_variable_exact_compatibility_contract.py",
    "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
    "tests/test_phase53_nullability_algebra_signature_result_formula_contract.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
    "tests/test_phase53_percent_rank_cume_dist_ntile_contract.py",
    "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py",
    "tests/test_phase53_rank_dense_rank_peer_semantics_contract.py",
    "tests/test_phase53_row_number_direct_field_mvp_contract.py",
    "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
    "tests/test_phase53_window_spec_function_identity_ast_contract.py",
    "tests/test_phase54_local_import_module_export_foundation_scope_lock.py",
)
SEMANTIC_READERS = (
    "tests/test_phase53_completion_audit_and_status_lock.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_planning_audit.py",
    "tests/test_phase12_order_limit_contract.py",
    "tests/test_phase12_planning_audit.py",
    "tests/test_phase13_completion_audit.py",
    "tests/test_phase13_planning_audit.py",
    "tests/test_phase14_candidate_decision_audit.py",
    "tests/test_phase14_completion_audit.py",
    "tests/test_phase14_planning_audit.py",
    "tests/test_phase14_relationship_metadata_completion_audit.py",
    "tests/test_phase15_completion_audit.py",
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
    "tests/test_phase52_aggregate_signature_algebra_facts.py",
    "tests/test_phase52_completion_audit_and_status_lock.py",
    "tests/test_phase52_fail_closed_capability_lookup.py",
    "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py",
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
    "tests/test_phase53_generic_type_variable_exact_compatibility_contract.py",
    "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
    "tests/test_phase53_nullability_algebra_signature_result_formula_contract.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
    "tests/test_phase53_percent_rank_cume_dist_ntile_contract.py",
    "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py",
    "tests/test_phase53_rank_dense_rank_peer_semantics_contract.py",
    "tests/test_phase53_row_number_direct_field_mvp_contract.py",
    "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
    "tests/test_phase53_window_spec_function_identity_ast_contract.py",
    "tests/test_phase54_local_import_module_export_foundation_scope_lock.py",
)
PHASE15_READERS = (
    "tests/test_phase53_completion_audit_and_status_lock.py",
    "tests/test_phase15_semantic_completion_audit.py",
    "tests/test_phase52_aggregate_signature_algebra_facts.py",
    "tests/test_phase52_completion_audit_and_status_lock.py",
    "tests/test_phase52_fail_closed_capability_lookup.py",
    "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py",
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
    "tests/test_phase53_generic_type_variable_exact_compatibility_contract.py",
    "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
    "tests/test_phase53_nullability_algebra_signature_result_formula_contract.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
    "tests/test_phase53_percent_rank_cume_dist_ntile_contract.py",
    "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py",
    "tests/test_phase53_rank_dense_rank_peer_semantics_contract.py",
    "tests/test_phase53_row_number_direct_field_mvp_contract.py",
    "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
    "tests/test_phase53_window_spec_function_identity_ast_contract.py",
)

MODIFIED_READER_PATHS = (
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
    "tests/test_phase51_completion_audit_and_status_lock.py",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py",
    SLICE2_TEST_REL,
    SLICE3_TEST_REL,
    SLICE4_TEST_REL,
    SLICE5_TEST_REL,
    SLICE6_TEST_REL,
)
ADDED_PATHS = {SOURCE_REL, SPEC_REL, SELF_REL}
ALLOWLIST_PATHS = {*MODIFIED_READER_PATHS, *ADDED_PATHS}
PR_REPAIR_ALLOWLIST_PATHS = {
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase51_aggregate_grouped_downstream_propagation.py",
    "tests/test_phase51_completion_audit_and_status_lock.py",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
    "tests/test_phase52_expression_stage_clause_capability_facts.py",
    SELF_REL,
}
COMPLETENESS_REPAIR_ALLOWLIST_PATHS = set(MODIFIED_READER_PATHS) - {SLICE2_TEST_REL} | {
    SELF_REL,
    SOURCE_REL,
    INVENTORY_REL,
    SIGNATURE_REL,
}
SLICE8_MODIFIED_PATHS = {
    SLICE4_TEST_REL,
    SLICE5_TEST_REL,
    SLICE6_TEST_REL,
    SELF_REL,
}
SLICE8_ADDED_PATHS = {SLICE8_SPEC_REL, SLICE8_TEST_REL}
SLICE8_ALLOWLIST_PATHS = SLICE8_MODIFIED_PATHS | SLICE8_ADDED_PATHS
SLICE9_MODIFIED_PATHS = {
    "docs/plan/phase-52-core-type-system-capability-foundation.md",
    "docs/spec/pietto-active-roadmap-phase51-60-v1.md",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py",
    SLICE5_TEST_REL,
    SLICE6_TEST_REL,
    SELF_REL,
    SLICE8_TEST_REL,
}
SLICE9_ADDED_PATHS = {SLICE9_SPEC_REL, SLICE9_TEST_REL}
SLICE9_ALLOWLIST_PATHS = SLICE9_MODIFIED_PATHS | SLICE9_ADDED_PATHS

BOUNDARY_HASH_OWNERS = (
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_packaging_smoke.py",
    "tests/test_phase11_validation_entrypoint.py",
    "tests/test_phase12_completion_audit.py",
    "tests/test_phase12_composition_cli_json_goldens.py",
)

DIRECT_TIER1_NODES = (
    "tests/test_phase11_completion_audit.py::test_package_configuration_lockfile_makefile_and_compiler_are_unchanged",
    "tests/test_phase11_planning_audit.py::test_slice1_locks_configuration_and_compiler_boundaries",
    "tests/test_phase12_order_limit_contract.py::test_slice6_preserves_configuration_cli_and_golden_boundaries",
    "tests/test_phase12_planning_audit.py::test_slice6_locks_configuration_workflow_and_compiler_boundaries",
    "tests/test_phase13_completion_audit.py::test_production_compiler_and_phase13_implementation_markers_are_absent",
    "tests/test_phase13_planning_audit.py::test_slice1_locks_compiler_workflow_and_golden_boundaries",
    "tests/test_phase14_candidate_decision_audit.py::test_production_generated_dependency_api_json_golden_and_ci_are_locked",
    "tests/test_phase14_completion_audit.py::test_unchanged_compiler_repository_and_golden_surfaces_are_byte_locked",
    "tests/test_phase14_planning_audit.py::test_production_grammar_generated_workflow_and_scripts_are_locked",
    "tests/test_phase14_relationship_metadata_completion_audit.py::test_forbidden_compiler_layers_and_repository_surfaces_are_byte_locked",
    "tests/test_phase15_completion_audit.py::test_frontend_compiler_cli_and_repository_surfaces_are_byte_locked",
    "tests/test_phase15_semantic_completion_audit.py::test_frontend_ir_sql_cli_json_dependency_and_ci_boundaries_are_locked",
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
    "tests/test_phase11_ci_workflow.py::test_ci_and_package_smoke_preserve_metadata_and_compiler_boundaries",
    "tests/test_phase11_generated_guard.py::test_slice3_preserves_compiler_and_configuration_boundary_bytes",
    "tests/test_phase11_golden_policy.py::test_slice4_preserves_golden_and_compiler_boundary_bytes",
    "tests/test_phase11_packaging_smoke.py::test_prior_scripts_and_all_compiler_packaging_boundaries_are_unchanged",
    "tests/test_phase11_validation_entrypoint.py::test_slice2_preserves_compiler_and_configuration_boundary_bytes",
    "tests/test_phase12_completion_audit.py::test_production_compiler_and_configuration_boundary_is_unchanged",
    "tests/test_phase12_composition_cli_json_goldens.py::test_production_api_json_dependency_and_compiler_boundaries_are_unchanged",
    "tests/test_phase51_completion_audit_and_status_lock.py::test_live_compiler_project_private_protected_version_and_tag_locks_are_dirty_safe",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py::test_live_compiler_project_private_and_protected_locks_are_dirty_safe",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py::test_slice1_no_behavior_public_privacy_and_release_boundaries_are_locked",
    "tests/test_phase14_candidate_decision_audit.py::test_slice2_status_inputs_and_single_candidate_decision",
    "tests/test_phase14_planning_audit.py::test_phase13_inputs_are_referenced_and_byte_locked",
    "tests/test_phase15_completion_audit.py::test_slice1_and_slice2_specs_tests_and_behavior_are_byte_locked",
    "tests/test_phase16_completion_audit.py::test_all_phase16_specs_and_focused_audits_are_byte_locked",
    "tests/test_phase49_compatibility_privacy_hash_lock_readiness.py::test_existing_hash_and_private_surface_locks_remain_present",
    "tests/test_phase51_aggregate_only_project_row_schema.py::test_forbidden_existing_project_compiler_and_public_surfaces_have_no_diff",
    "tests/test_phase51_grouped_aggregate_project_row_schema.py::test_forbidden_existing_project_compiler_and_public_surfaces_have_no_diff",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py::test_phase51_compatibility_migrations_preserve_historical_locks",
)

EXPECTED_TEST_NAMES = (
    "test_private_module_api_and_dependency_shape_is_exact",
    "test_freezer_and_combined_fact_order_are_exact",
    "test_signature_family_counts_are_exact",
    "test_signature_inventory_order_keys_support_and_disposition_are_exact",
    "test_signature_key_schema_and_completeness_are_exact",
    "test_signature_result_type_nullability_stage_and_role_are_exact",
    "test_signature_evidence_order_and_authority_are_exact",
    "test_shape_signature_real_conflict_is_adjacent_ordered_and_winner_free",
    "test_count_alias_shape_let_and_expression_policy_is_exact",
    "test_signature_lookup_found_is_exact",
    "test_signature_complete_wrong_tail_is_absent",
    "test_signature_incomplete_questions_are_unknown",
    "test_injected_conflict_and_duplicate_freeze_preserve_lookup_contract",
    "test_algebra_inventory_order_keys_support_and_disposition_are_exact",
    "test_supported_algebra_fact_is_exact",
    "test_rejected_algebra_fact_group_is_exact",
    "test_algebra_completeness_absence_and_omission_are_exact",
    "test_modifier_window_nested_global_grouped_and_clause_boundaries_are_exact",
    "test_active_conflict_ledger_and_no_authority_omissions_are_preserved",
    "test_spec_headings_and_required_phrases_are_exact",
    "test_no_existing_consumer_public_export_registry_io_or_callback_exists",
    "test_prior_private_source_hashes_are_byte_identical",
    "test_compiler_semantic_subset_project_and_raw_hash_readers_are_exact",
    "test_package_version_tags_gate2_dirty_state_and_allowlist_are_exact",
    "test_static_test_inventory_and_tier1_selection_are_exact",
    "test_tier2_manifest_identity_and_classification_are_exact",
    "test_slice7_lifecycle_validation_gate3_and_release_boundaries_are_exact",
    "test_backend_evidence_is_separate_ordered_and_non_authoritative",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _slice13_paths(name: str) -> set[str]:
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
        modified, added = _phase54_slice2_paths()
        if name == "MODIFIED_PATHS":
            return modified
        if name == "ADDED_PATHS":
            return added
    path = REPO_ROOT / "tests/test_phase53_window_syntax_contextual_grammar_contract.py"
    tree = ast.parse(_read(path), filename=path.as_posix())
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
        ):
            value = ast.literal_eval(node.value)
            assert isinstance(value, (set, tuple))
            assert all(isinstance(item, str) for item in value)
            return set(value)
    raise AssertionError(f"missing Slice 13 path manifest {name}")


def _phase54_slice2_paths() -> tuple[set[str], set[str]]:
    path = REPO_ROOT / "tests/_phase54_active_gate2_manifest.py"
    tree = ast.parse(_read(path), filename=path.as_posix())
    expected = {
        "ADDED_PATHS",
        "NON_READER_MODIFIED_PATHS",
        "MECHANICAL_READER_PATHS",
    }
    values: dict[str, set[str]] = {}
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
            values[node.targets[0].id] = value
    assert set(values) == expected
    return (
        values["NON_READER_MODIFIED_PATHS"] | values["MECHANICAL_READER_PATHS"],
        values["ADDED_PATHS"],
    )


def _git_output(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return result.stdout.strip()


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
    output = result.stdout.strip()
    if result.returncode == 1:
        assert output == ""
        return None
    assert output
    return output


def _git_refs() -> tuple[tuple[str, str], ...]:
    output = _git_output(["for-each-ref", "--format=%(refname)%09%(objectname)"])
    if not output:
        return ()
    refs = []
    for line in output.splitlines():
        ref, object_name = line.split("\t", 1)
        assert ref and re.fullmatch(r"[0-9a-f]{40}", object_name)
        refs.append((ref, object_name))
    return tuple(refs)


def _git_commit_object_exists(commit: str) -> bool:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=REPO_ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.returncode in (0, 128)
    return result.returncode == 0


def _assert_clean_checkout_refs(
    *,
    branch: str,
    head: str,
    main: str | None,
    origin_main: str | None,
) -> None:
    if phase54_slice12_mechanical_repair4_clean_topic_is_active():
        assert branch == PHASE54_SLICE12_MECHANICAL_REPAIR4_BRANCH
        assert main == origin_main == "bc46faff1c9aa71f583ed7d2964b651cc659bc90"
        assert tuple(
            _git_output(["rev-list", "--parents", "-n", "1", head]).split()[1:]
        ) == (PHASE54_SLICE12_MECHANICAL_REPAIR4_BASE,)
        assert _git_output(["show", "-s", "--format=%s", head]) == (
            PHASE54_SLICE12_MECHANICAL_REPAIR4_SUBJECT
        )
        return
    if phase54_slice12_mechanical_repair3_clean_topic_is_active():
        assert branch == PHASE54_SLICE12_MECHANICAL_REPAIR3_BRANCH
        assert main == origin_main == "bc46faff1c9aa71f583ed7d2964b651cc659bc90"
        assert tuple(
            _git_output(["rev-list", "--parents", "-n", "1", head]).split()[1:]
        ) == (PHASE54_SLICE12_MECHANICAL_REPAIR3_BASE,)
        assert _git_output(["show", "-s", "--format=%s", head]) == (
            PHASE54_SLICE12_MECHANICAL_REPAIR3_SUBJECT
        )
        return
    if phase54_slice12_product_repair14_clean_topic_is_active():
        assert branch == PHASE54_SLICE12_PRODUCT_REPAIR14_BRANCH
        assert main == origin_main == "bc46faff1c9aa71f583ed7d2964b651cc659bc90"
        assert tuple(
            _git_output(["rev-list", "--parents", "-n", "1", head]).split()[1:]
        ) == (PHASE54_SLICE12_PRODUCT_REPAIR14_BASE,)
        assert _git_output(["show", "-s", "--format=%s", head]) == (
            PHASE54_SLICE12_PRODUCT_REPAIR14_SUBJECT
        )
        return
    if phase54_slice12_product_repair13_clean_topic_is_active():
        assert branch == PHASE54_SLICE12_PRODUCT_REPAIR13_BRANCH
        assert main == origin_main == "bc46faff1c9aa71f583ed7d2964b651cc659bc90"
        assert tuple(
            _git_output(["rev-list", "--parents", "-n", "1", head]).split()[1:]
        ) == (PHASE54_SLICE12_PRODUCT_REPAIR13_BASE,)
        assert _git_output(["show", "-s", "--format=%s", head]) == (
            PHASE54_SLICE12_PRODUCT_REPAIR13_SUBJECT
        )
        return
    if phase54_slice12_product_repair12_clean_topic_is_active():
        assert branch == PHASE54_SLICE12_PRODUCT_REPAIR12_BRANCH
        assert main == origin_main == "bc46faff1c9aa71f583ed7d2964b651cc659bc90"
        assert tuple(
            _git_output(["rev-list", "--parents", "-n", "1", head]).split()[1:]
        ) == (PHASE54_SLICE12_PRODUCT_REPAIR12_BASE,)
        assert _git_output(["show", "-s", "--format=%s", head]) == (
            PHASE54_SLICE12_PRODUCT_REPAIR12_SUBJECT
        )
        return
    if phase54_slice12_product_repair11_clean_topic_is_active():
        assert branch == PHASE54_SLICE12_PRODUCT_REPAIR11_BRANCH
        assert main == origin_main == "bc46faff1c9aa71f583ed7d2964b651cc659bc90"
        assert tuple(
            _git_output(["rev-list", "--parents", "-n", "1", head]).split()[1:]
        ) == (PHASE54_SLICE12_PRODUCT_REPAIR11_BASE,)
        assert _git_output(["show", "-s", "--format=%s", head]) == (
            PHASE54_SLICE12_PRODUCT_REPAIR11_SUBJECT
        )
        return
    if phase54_slice12_product_repair10_clean_topic_is_active():
        assert branch == PHASE54_SLICE12_PRODUCT_REPAIR10_BRANCH
        assert main == origin_main == "bc46faff1c9aa71f583ed7d2964b651cc659bc90"
        assert tuple(
            _git_output(["rev-list", "--parents", "-n", "1", head]).split()[1:]
        ) == (PHASE54_SLICE12_PRODUCT_REPAIR10_BASE,)
        assert _git_output(["show", "-s", "--format=%s", head]) == (
            PHASE54_SLICE12_PRODUCT_REPAIR10_SUBJECT
        )
        return
    if phase54_slice12_product_repair3_clean_topic_is_active():
        assert branch == "phase54/slice12-semantic-fact-preservation"
        assert main == origin_main == "bc46faff1c9aa71f583ed7d2964b651cc659bc90"
        assert tuple(
            _git_output(["rev-list", "--parents", "-n", "1", head]).split()[1:]
        ) == ("ab1445fcb8b3af9a14f0230edb5680c523a754d1",)
        assert _git_output(["show", "-s", "--format=%s", head]) == (
            "Fix Phase 54 Slice 12 semantic fact preservation"
        )
        return
    if branch == "main":
        assert main == head
        if origin_main is not None:
            assert origin_main == head
        return

    if branch == PHASE54_POST_SLICE12_INTERLUDE_BRANCH:
        assert phase54_post_slice12_interlude_clean_topic_is_active()
        return

    assert branch == ""
    refs = _git_refs()
    assert len(refs) == 1
    merge_ref, merge_head = refs[0]
    assert re.fullmatch(r"refs/remotes/pull/[1-9][0-9]*/merge", merge_ref)
    assert merge_head == head
    assert main is None
    assert origin_main is None

    raw_commit = _git_output(["cat-file", "-p", head])
    header, separator, message = raw_commit.partition("\n\n")
    assert separator == "\n\n"
    parents = tuple(
        line.removeprefix("parent ")
        for line in header.splitlines()
        if line.startswith("parent ")
    )
    assert len(parents) == 2
    assert parents[0] != parents[1]
    assert all(re.fullmatch(r"[0-9a-f]{40}", parent) for parent in parents)
    assert message == f"Merge {parents[1]} into {parents[0]}"

    parent_objects_exist = tuple(
        _git_commit_object_exists(parent) for parent in parents
    )
    assert len(set(parent_objects_exist)) == 1
    if all(parent_objects_exist):
        assert _git_output(["merge-base", *parents]) == parents[0]
        assert _git_output(["rev-parse", f"{parents[1]}^{{tree}}"]) == _git_output(
            ["rev-parse", f"{head}^{{tree}}"]
        )


def _digest(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(REPO_ROOT).as_posix()):
        digest.update(path.relative_to(REPO_ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _compiler_paths() -> tuple[Path, ...]:
    paths = [REPO_ROOT / "Makefile", REPO_ROOT / "grammar/Pietto.g4"]
    paths.extend(
        path
        for path in (REPO_ROOT / "src/pietto").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )
    return tuple(paths)


def _project_private_paths() -> tuple[Path, ...]:
    return tuple(
        path
        for path in (REPO_ROOT / "src/pietto/_project").rglob("*.py")
        if "__pycache__" not in path.parts
    )


def _parametrize_values(function: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    count = 1
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
        if not isinstance(values, (ast.List, ast.Tuple)):
            raise AssertionError("parametrize values must be literal")
        count *= len(values.elts)
    return count


def _pytest_shape(path: Path) -> tuple[int, int, list[str], list[int]]:
    tree = ast.parse(_read(path), filename=path.as_posix())
    functions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    ]
    parametrized = [node for node in functions if node.decorator_list]
    return (
        len(functions),
        sum(_parametrize_values(node) for node in functions),
        [node.name for node in parametrized],
        [_parametrize_values(node) for node in parametrized],
    )


def _literal_tuple(path: Path, name: str) -> tuple[str, ...]:
    tree = ast.parse(_read(path), filename=path.as_posix())
    for node in tree.body:
        value: ast.expr | None = None
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            value = node.value
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
        ):
            value = node.value
        if value is None:
            continue
        result = ast.literal_eval(value)
        assert isinstance(result, tuple)
        assert all(isinstance(item, str) for item in result)
        return cast(tuple[str, ...], result)
    raise AssertionError(f"missing literal tuple {name}")


def _facts(name: str) -> tuple[CapabilityFact, ...]:
    return cast(tuple[CapabilityFact, ...], getattr(capability_aggregates, name))


def _lookup(key: CapabilityKey) -> Found | Absent | Unknown | Conflict:
    helper = cast(Any, capability_aggregates.aggregate_lookup_inputs)
    facts, complete, reason = helper(key)
    return lookup_capability(
        key,
        facts,
        domain_complete=complete,
        unknown_reason=reason,
    )


def _signature_key(
    subject: str,
    shape: str,
    argument_type: str,
    result_type: str,
    nullability: str,
    *,
    arity: str = "1",
    context: str = "aggregate_signature",
    dialect: str | None = None,
) -> CapabilityKey:
    return CapabilityKey(
        CapabilityDomain.AGGREGATE,
        subject=subject,
        operation="signature",
        operands=(
            arity,
            shape,
            argument_type,
            result_type,
            nullability,
            "GROUP",
            "aggregate_result",
        ),
        context=context,
        dialect=dialect,
    )


def _algebra_key(
    subject: str,
    operation: str,
    scope: str,
    value: str,
    *,
    context: str = "aggregate_algebra",
) -> CapabilityKey:
    return CapabilityKey(
        CapabilityDomain.AGGREGATE,
        subject=subject,
        operation=operation,
        operands=(scope, value),
        context=context,
    )


def _expected_signature_rows() -> tuple[
    tuple[str, tuple[str, ...], CapabilitySupport], ...
]:
    supported = CapabilitySupport.SUPPORTED
    direct_count_types = (
        "Bool",
        "Bytes",
        "Date",
        "Decimal",
        "Float",
        "Int",
        "Json",
        "Text",
        "Timestamp",
        "UUID",
    )
    expression_count_types = ("Bool", "Int", "Float", "Decimal", "Text")
    distinct_types = (
        "Bool",
        "Int",
        "Float",
        "Decimal",
        "Text",
        "Date",
        "Timestamp",
        "UUID",
    )
    rows: list[tuple[str, tuple[str, ...], CapabilitySupport]] = []

    def add(
        subject: str,
        arity: str,
        shape: str,
        argument: str,
        result: str,
        nullability: str,
        support: CapabilitySupport = supported,
    ) -> None:
        rows.append(
            (
                subject,
                (
                    arity,
                    shape,
                    argument,
                    result,
                    nullability,
                    "GROUP",
                    "aggregate_result",
                ),
                support,
            )
        )

    add("count", "0", "no_argument", "NO_ARGUMENT", "Int", "non_null")
    for argument in direct_count_types:
        add("count", "1", "direct_field", argument, "Int", "non_null")
    for argument in expression_count_types:
        add(
            "count",
            "1",
            "field_bearing_expression",
            argument,
            "Int",
            "non_null",
        )
    add("count", "1", "direct_field", "Shape", "Int", "non_null")
    add(
        "count",
        "1",
        "direct_field",
        "Shape",
        "Int",
        "non_null",
        CapabilitySupport.EXPLICITLY_UNSUPPORTED,
    )
    for argument in distinct_types:
        add(
            "count_distinct",
            "1",
            "direct_field",
            argument,
            "Int",
            "non_null",
        )
    add(
        "count_distinct",
        "1",
        "lower_trim_text_transform_chain",
        "Text",
        "Int",
        "non_null",
    )
    for argument, result in (
        ("Int", "Int"),
        ("Float", "Float"),
        ("Decimal", "Decimal"),
    ):
        add("sum", "1", "direct_field", argument, result, "nullable")
    for argument, result in (
        ("Int", "Int"),
        ("Float", "Float"),
        ("Decimal", "Decimal"),
    ):
        add(
            "sum",
            "1",
            "field_only_numeric_expression",
            argument,
            result,
            "nullable",
        )
    for argument in ("Int", "Float"):
        add(
            "sum",
            "1",
            "field_and_literal_numeric_expression",
            argument,
            argument,
            "nullable",
        )
    for argument, result in (
        ("Int", "Float"),
        ("Float", "Float"),
        ("Decimal", "Decimal"),
    ):
        add("avg", "1", "direct_field", argument, result, "nullable")
    for argument, result in (
        ("Int", "Float"),
        ("Float", "Float"),
        ("Decimal", "Decimal"),
    ):
        add(
            "avg",
            "1",
            "field_only_numeric_expression",
            argument,
            result,
            "nullable",
        )
    for argument in ("Int", "Float"):
        add(
            "avg",
            "1",
            "field_and_literal_numeric_expression",
            argument,
            "Float",
            "nullable",
        )
    for subject in ("min", "max"):
        for argument in ("Int", "Float", "Decimal", "Date", "Timestamp"):
            add(subject, "1", "direct_field", argument, argument, "nullable")
    return tuple(rows)


def _expected_algebra_rows() -> tuple[
    tuple[
        str,
        str,
        tuple[str, str],
        CapabilitySupport,
        CapabilityDispositionKind,
    ],
    ...,
]:
    supported = CapabilitySupport.SUPPORTED
    unsupported = CapabilitySupport.EXPLICITLY_UNSUPPORTED
    none = CapabilityDispositionKind.NONE
    deferred = CapabilityDispositionKind.DEFERRED
    return (
        ("count", "empty_input_result", ("arity_0", "zero"), supported, none),
        ("count", "empty_input_result", ("arity_1", "zero"), supported, none),
        (
            "count_distinct",
            "empty_input_result",
            ("arity_1", "zero"),
            supported,
            none,
        ),
        (
            "sum",
            "empty_input_result",
            ("all_supported_signatures", "sql_null"),
            supported,
            none,
        ),
        (
            "min",
            "empty_input_result",
            ("all_supported_signatures", "nullable_on_empty_input"),
            supported,
            none,
        ),
        (
            "max",
            "empty_input_result",
            ("all_supported_signatures", "nullable_on_empty_input"),
            supported,
            none,
        ),
        (
            "count",
            "argument_inspection",
            ("arity_0", "does_not_inspect_values"),
            supported,
            none,
        ),
        (
            "count",
            "null_treatment",
            ("arity_1", "eliminates_sql_null_results"),
            supported,
            none,
        ),
        (
            "count_distinct",
            "null_treatment",
            ("arity_1", "eliminates_sql_null_results"),
            supported,
            none,
        ),
        (
            "count_distinct",
            "duplicate_treatment",
            ("arity_1", "eliminates_duplicates"),
            supported,
            none,
        ),
        (
            "SEMANTIC_AGGREGATE_NAMES",
            "aggregate_filter",
            ("all_current_aggregates", "not_supported"),
            unsupported,
            deferred,
        ),
        (
            "SEMANTIC_AGGREGATE_NAMES",
            "inline_distinct_modifier",
            ("all_current_aggregates", "not_supported"),
            unsupported,
            deferred,
        ),
        (
            "SEMANTIC_AGGREGATE_NAMES",
            "aggregate_internal_ordering",
            ("all_current_aggregates", "not_supported"),
            unsupported,
            deferred,
        ),
        (
            "SEMANTIC_AGGREGATE_NAMES",
            "generic_aggregate_modifier",
            ("all_current_aggregates", "not_supported"),
            unsupported,
            deferred,
        ),
        (
            "SEMANTIC_AGGREGATE_NAMES",
            "nested_aggregate",
            ("aggregate_argument", "not_supported"),
            unsupported,
            none,
        ),
        (
            "SEMANTIC_AGGREGATE_NAMES",
            "scalar_wrapping",
            ("direct_aggregate_projection", "not_supported"),
            unsupported,
            none,
        ),
    )


def _prior_compatible_nodes() -> tuple[tuple[str, ...], tuple[int, ...]]:
    files = (
        SLICE2_TEST_REL,
        SLICE3_TEST_REL,
        SLICE4_TEST_REL,
    )
    excluded = {
        SLICE2_TEST_REL + "::test_gate2_dirty_untracked_and_index_states_are_exact",
        SLICE3_TEST_REL + "::test_gate2_dirty_untracked_and_index_states_are_exact",
        SLICE4_TEST_REL + "::test_gate2_dirty_untracked_and_index_states_are_exact",
    }
    nodes: list[str] = []
    per_file_items: list[int] = []
    for relative in files:
        tree = ast.parse(_read(REPO_ROOT / relative), filename=relative)
        item_count = 0
        for function in tree.body:
            if not (
                isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef))
                and function.name.startswith("test_")
            ):
                continue
            node_id = relative + "::" + function.name
            if node_id in excluded:
                continue
            nodes.append(node_id)
            item_count += _parametrize_values(function)
        per_file_items.append(item_count)
    return tuple(nodes), tuple(per_file_items)


def test_private_module_api_and_dependency_shape_is_exact() -> None:
    assert capability_aggregates.__all__ == ()
    tree = ast.parse(_read(SOURCE_PATH), filename=SOURCE_REL)
    assert not any(
        isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef, ast.Import))
        for node in tree.body
    )
    imports = {node.module for node in tree.body if isinstance(node, ast.ImportFrom)}
    assert imports <= {
        "__future__",
        "collections.abc",
        "pietto.semantic.capability_facts",
    }
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert {"_freeze_aggregates", "aggregate_lookup_inputs"} <= functions
    source = _read(SOURCE_PATH)
    for forbidden in (
        "capability_lookup",
        "open(",
        "getenv",
        "os.environ",
        "database",
        "callback",
    ):
        assert forbidden not in source


def test_freezer_and_combined_fact_order_are_exact() -> None:
    signature = _facts("_AGGREGATE_SIGNATURE_FACTS")
    algebra = _facts("_AGGREGATE_ALGEBRA_FACTS")
    combined = _facts("_AGGREGATE_CAPABILITY_FACTS")
    assert combined == signature + algebra
    freezer = cast(Any, getattr(capability_aggregates, "_freeze_aggregates"))
    with pytest.raises(ValueError, match="duplicate"):
        freezer((signature[0], signature[0]))
    distinct = replace(signature[0], support=CapabilitySupport.EXPLICITLY_UNSUPPORTED)
    assert freezer((signature[0], distinct)) == (signature[0], distinct)


@pytest.mark.parametrize(
    ("subject", "fact_count", "key_count"),
    (
        ("count", 18, 17),
        ("count_distinct", 9, 9),
        ("sum", 8, 8),
        ("avg", 8, 8),
        ("min", 5, 5),
        ("max", 5, 5),
    ),
)
def test_signature_family_counts_are_exact(
    subject: str,
    fact_count: int,
    key_count: int,
) -> None:
    facts = tuple(
        fact
        for fact in _facts("_AGGREGATE_SIGNATURE_FACTS")
        if fact.key.subject == subject
    )
    assert (len(facts), len({fact.key for fact in facts})) == (fact_count, key_count)


def test_signature_inventory_order_keys_support_and_disposition_are_exact() -> None:
    facts = _facts("_AGGREGATE_SIGNATURE_FACTS")
    expected = _expected_signature_rows()
    assert len(facts) == len(expected) == 53
    assert len({fact.key for fact in facts}) == 52
    assert (
        tuple((fact.key.subject, fact.key.operands, fact.support) for fact in facts)
        == expected
    )
    for fact in facts:
        assert fact.key.domain is CapabilityDomain.AGGREGATE
        assert fact.key.operation == "signature"
        assert fact.key.context == "aggregate_signature"
        assert fact.key.dialect is None
        assert fact.key.extension is None
        assert fact.disposition.kind is CapabilityDispositionKind.NONE
        assert fact.disposition.owner is None
        assert fact.disposition.reason is None


def test_signature_key_schema_and_completeness_are_exact() -> None:
    facts = _facts("_AGGREGATE_SIGNATURE_FACTS")
    assert all(len(fact.key.operands) == 7 for fact in facts)
    assert facts[0].key.operands == (
        "0",
        "no_argument",
        "NO_ARGUMENT",
        "Int",
        "non_null",
        "GROUP",
        "aggregate_result",
    )
    assert {fact.key.operands[1] for fact in facts} == {
        "no_argument",
        "direct_field",
        "field_bearing_expression",
        "lower_trim_text_transform_chain",
        "field_only_numeric_expression",
        "field_and_literal_numeric_expression",
    }
    for fact in facts:
        inputs, complete, reason = capability_aggregates.aggregate_lookup_inputs(
            fact.key
        )
        assert inputs == facts
        assert complete is True
        assert reason is None


@pytest.mark.parametrize(
    ("subject", "shape", "argument", "result", "nullability"),
    (
        ("count", "no_argument", "NO_ARGUMENT", "Int", "non_null"),
        ("count", "direct_field", "Bytes", "Int", "non_null"),
        ("count", "field_bearing_expression", "Text", "Int", "non_null"),
        ("count", "direct_field", "Shape", "Int", "non_null"),
        ("count_distinct", "direct_field", "UUID", "Int", "non_null"),
        (
            "count_distinct",
            "lower_trim_text_transform_chain",
            "Text",
            "Int",
            "non_null",
        ),
        ("sum", "direct_field", "Int", "Int", "nullable"),
        (
            "sum",
            "field_only_numeric_expression",
            "Decimal",
            "Decimal",
            "nullable",
        ),
        (
            "sum",
            "field_and_literal_numeric_expression",
            "Float",
            "Float",
            "nullable",
        ),
        ("avg", "direct_field", "Int", "Float", "nullable"),
        (
            "avg",
            "field_only_numeric_expression",
            "Decimal",
            "Decimal",
            "nullable",
        ),
        ("min", "direct_field", "Date", "Date", "nullable"),
        ("max", "direct_field", "Timestamp", "Timestamp", "nullable"),
    ),
)
def test_signature_result_type_nullability_stage_and_role_are_exact(
    subject: str,
    shape: str,
    argument: str,
    result: str,
    nullability: str,
) -> None:
    matches = tuple(
        fact
        for fact in _facts("_AGGREGATE_SIGNATURE_FACTS")
        if fact.key.subject == subject
        and fact.key.operands[1:5] == (shape, argument, result, nullability)
    )
    assert matches
    assert all(
        fact.key.operands[5:] == ("GROUP", "aggregate_result") for fact in matches
    )


@pytest.mark.parametrize(
    "index",
    (0, 1, 11, 16, 17, 26, 33, 43),
)
def test_signature_evidence_order_and_authority_are_exact(index: int) -> None:
    fact = _facts("_AGGREGATE_SIGNATURE_FACTS")[index]
    assert len(fact.evidence) == len(set(fact.evidence))
    assert all((REPO_ROOT / entry.source_path).is_file() for entry in fact.evidence)
    order = {
        source: position for position, source in enumerate(CapabilityEvidenceSource)
    }
    positions = [order[entry.source] for entry in fact.evidence]
    assert positions == sorted(positions)
    assert fact.evidence[0].source is CapabilityEvidenceSource.GRAMMAR_AST
    assert CapabilityEvidenceSource.SEMANTIC_PROCEDURE in {
        entry.source for entry in fact.evidence
    }
    backends = [
        entry
        for entry in fact.evidence
        if entry.source is CapabilityEvidenceSource.BACKEND
    ]
    assert [(entry.dialect, entry.backend) for entry in backends] in (
        [],
        [("postgresql", "postgresql"), ("mysql", "private-mysql")],
    )


def test_shape_signature_real_conflict_is_adjacent_ordered_and_winner_free() -> None:
    facts = _facts("_AGGREGATE_SIGNATURE_FACTS")
    supported, unsupported = facts[16:18]
    assert (
        supported.key
        == unsupported.key
        == _signature_key("count", "direct_field", "Shape", "Int", "non_null")
    )
    assert supported.support is CapabilitySupport.SUPPORTED
    assert unsupported.support is CapabilitySupport.EXPLICITLY_UNSUPPORTED
    assert any(
        entry.reason is CapabilityReasonCode.DIALECT_LOWERING_GAP
        for entry in unsupported.evidence
    )
    result = _lookup(supported.key)
    assert isinstance(result, Conflict)
    assert result.reason is CapabilityReasonCode.CONFLICTING_EVIDENCE
    assert result.evidence == (supported, unsupported)


def test_count_alias_shape_let_and_expression_policy_is_exact() -> None:
    facts = _facts("_AGGREGATE_SIGNATURE_FACTS")
    keys = {fact.key for fact in facts}
    assert not any("row_let" in key.operands for key in keys)
    assert not any("aggregate_let" in key.operands for key in keys)
    assert not any("projection_alias" in key.operands for key in keys)
    assert not any("literal_only" in key.operands for key in keys)
    assert not any("null_literal" in key.operands for key in keys)
    count_expression_types = tuple(
        fact.key.operands[2]
        for fact in facts
        if fact.key.subject == "count"
        and fact.key.operands[1] == "field_bearing_expression"
    )
    assert count_expression_types == ("Bool", "Int", "Float", "Decimal", "Text")
    distinct_shapes = {
        fact.key.operands[1] for fact in facts if fact.key.subject == "count_distinct"
    }
    assert distinct_shapes == {
        "direct_field",
        "lower_trim_text_transform_chain",
    }


@pytest.mark.parametrize(
    "key",
    (
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="count",
            operation="signature",
            operands=(
                "0",
                "no_argument",
                "NO_ARGUMENT",
                "Int",
                "non_null",
                "GROUP",
                "aggregate_result",
            ),
            context="aggregate_signature",
        ),
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="count",
            operation="signature",
            operands=(
                "1",
                "direct_field",
                "Int",
                "Int",
                "non_null",
                "GROUP",
                "aggregate_result",
            ),
            context="aggregate_signature",
        ),
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="count",
            operation="signature",
            operands=(
                "1",
                "field_bearing_expression",
                "Text",
                "Int",
                "non_null",
                "GROUP",
                "aggregate_result",
            ),
            context="aggregate_signature",
        ),
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="count_distinct",
            operation="signature",
            operands=(
                "1",
                "lower_trim_text_transform_chain",
                "Text",
                "Int",
                "non_null",
                "GROUP",
                "aggregate_result",
            ),
            context="aggregate_signature",
        ),
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="sum",
            operation="signature",
            operands=(
                "1",
                "field_and_literal_numeric_expression",
                "Int",
                "Int",
                "nullable",
                "GROUP",
                "aggregate_result",
            ),
            context="aggregate_signature",
        ),
    ),
)
def test_signature_lookup_found_is_exact(key: CapabilityKey) -> None:
    result = _lookup(key)
    assert isinstance(result, Found)
    assert result.fact.key == key


def test_signature_complete_wrong_tail_is_absent() -> None:
    key = _signature_key("count", "direct_field", "Int", "Float", "non_null")
    result = _lookup(key)
    assert isinstance(result, Absent)
    assert result.key == key
    assert result.reason is CapabilityReasonCode.NO_CATALOG_ENTRY


def test_signature_incomplete_questions_are_unknown() -> None:
    keys = (
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="count",
            operation="signature",
            operands=(
                "1",
                "direct_field",
                "TYPE_ALIAS",
                "Int",
                "non_null",
                "GROUP",
                "aggregate_result",
            ),
            context="aggregate_signature",
        ),
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="future_aggregate",
            operation="signature",
            operands=(
                "1",
                "direct_field",
                "Int",
                "Int",
                "nullable",
                "GROUP",
                "aggregate_result",
            ),
            context="aggregate_signature",
        ),
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="count",
            operation="signature",
            operands=(
                "1",
                "direct_field",
                "Int",
                "Int",
                "non_null",
                "GROUP",
                "aggregate_result",
            ),
            context="alternate_context",
        ),
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="count",
            operation="signature",
            operands=(
                "1",
                "direct_field",
                "Int",
                "Int",
                "non_null",
                "GROUP",
                "aggregate_result",
            ),
            context="aggregate_signature",
            dialect="postgresql",
        ),
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="count",
            operation="signature",
            operands=(
                "1",
                "direct_field",
                "Int",
                "Int",
                "non_null",
                "GROUP",
                "aggregate_result",
            ),
            context="aggregate_signature",
            dialect="postgresql",
            extension="future",
        ),
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="count",
            operation="signature",
            operands=("1", "direct_field", "Int", "Int", "non_null", "GROUP"),
            context="aggregate_signature",
        ),
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="sum",
            operation="signature",
            operands=(
                "1",
                "direct_field",
                "Decimal(12,2)",
                "Decimal(12,2)",
                "nullable",
                "GROUP",
                "aggregate_result",
            ),
            context="aggregate_signature",
        ),
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="sum",
            operation="window_signature",
            operands=(
                "1",
                "direct_field",
                "Int",
                "Int",
                "nullable",
                "WINDOW",
                "window_result",
            ),
            context="aggregate_signature",
        ),
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="count",
            operation="signature",
            operands=(
                "1",
                "project_only",
                "Int",
                "Int",
                "non_null",
                "GROUP",
                "aggregate_result",
            ),
            context="aggregate_signature",
        ),
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="avg",
            operation="signature",
            operands=(
                "1",
                "literal_only_numeric_expression",
                "Int",
                "Float",
                "nullable",
                "GROUP",
                "aggregate_result",
            ),
            context="aggregate_signature",
        ),
        CapabilityKey(
            CapabilityDomain.SCALAR_FUNCTION,
            subject="count",
            operation="signature",
            operands=("Int",),
            context="expression",
        ),
    )
    for key in keys:
        result = _lookup(key)
        assert isinstance(result, Unknown)
        assert result.reason is CapabilityReasonCode.NOT_EVIDENCED


def test_injected_conflict_and_duplicate_freeze_preserve_lookup_contract() -> None:
    original = _facts("_AGGREGATE_SIGNATURE_FACTS")[0]
    conflicting = replace(original, support=CapabilitySupport.EXPLICITLY_UNSUPPORTED)
    result = lookup_capability(
        original.key,
        (original, conflicting),
        domain_complete=True,
    )
    assert isinstance(result, Conflict)
    assert result.reason is CapabilityReasonCode.CONFLICTING_EVIDENCE
    assert result.evidence == (original, conflicting)
    freezer = cast(Any, getattr(capability_aggregates, "_freeze_aggregates"))
    assert freezer((original, conflicting)) == (original, conflicting)
    with pytest.raises(ValueError, match="duplicate"):
        freezer((original, original))


def test_algebra_inventory_order_keys_support_and_disposition_are_exact() -> None:
    facts = _facts("_AGGREGATE_ALGEBRA_FACTS")
    expected = _expected_algebra_rows()
    property_values = frozenset(
        (
            "zero",
            "sql_null",
            "nullable_on_empty_input",
            "does_not_inspect_values",
            "eliminates_sql_null_results",
            "eliminates_duplicates",
            "not_supported",
        )
    )
    assert len(facts) == len({fact.key for fact in facts}) == len(expected) == 16
    assert (
        cast(
            frozenset[str],
            getattr(capability_aggregates, "_ALGEBRA_PROPERTY_VALUES"),
        )
        == property_values
    )
    assert (
        tuple(
            (
                fact.key.subject,
                fact.key.operation,
                cast(tuple[str, str], fact.key.operands),
                fact.support,
                fact.disposition.kind,
            )
            for fact in facts
        )
        == expected
    )
    assert tuple(dict.fromkeys(fact.key.operands[1] for fact in facts)) == (
        "zero",
        "sql_null",
        "nullable_on_empty_input",
        "does_not_inspect_values",
        "eliminates_sql_null_results",
        "eliminates_duplicates",
        "not_supported",
    )
    for index, fact in enumerate(facts):
        _, complete, reason = cast(
            Any,
            capability_aggregates.aggregate_lookup_inputs,
        )(fact.key)
        assert complete is True
        assert reason is None
        assert fact.key.domain is CapabilityDomain.AGGREGATE
        assert fact.key.context == "aggregate_algebra"
        assert fact.key.dialect is None
        assert fact.key.extension is None
        if 10 <= index <= 13:
            assert fact.disposition.owner == "POST60_ADVANCED_AGGREGATION_GROUPING"
            assert fact.disposition.reason
        else:
            assert fact.disposition.owner is None
            assert fact.disposition.reason is None


@pytest.mark.parametrize(
    "index",
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
)
def test_supported_algebra_fact_is_exact(index: int) -> None:
    fact = _facts("_AGGREGATE_ALGEBRA_FACTS")[index]
    assert fact.support is CapabilitySupport.SUPPORTED
    assert fact.disposition.kind is CapabilityDispositionKind.NONE
    result = _lookup(fact.key)
    assert isinstance(result, Found)
    assert result.fact == fact


@pytest.mark.parametrize(
    "indexes",
    ((10,), (11,), (12,), (13,), (14, 15)),
)
def test_rejected_algebra_fact_group_is_exact(indexes: tuple[int, ...]) -> None:
    facts = _facts("_AGGREGATE_ALGEBRA_FACTS")
    for index in indexes:
        fact = facts[index]
        assert fact.support is CapabilitySupport.EXPLICITLY_UNSUPPORTED
        if index < 14:
            assert fact.disposition.kind is CapabilityDispositionKind.DEFERRED
            assert fact.disposition.owner == "POST60_ADVANCED_AGGREGATION_GROUPING"
        else:
            assert fact.disposition.kind is CapabilityDispositionKind.NONE
        result = _lookup(fact.key)
        assert isinstance(result, Found)
        assert result.fact == fact


def test_algebra_completeness_absence_and_omission_are_exact() -> None:
    complete_absences = (
        _algebra_key(
            "count",
            "argument_inspection",
            "arity_0",
            "eliminates_duplicates",
        ),
        _algebra_key(
            "SEMANTIC_AGGREGATE_NAMES",
            "aggregate_filter",
            "all_current_aggregates",
            "zero",
        ),
        _algebra_key(
            "SEMANTIC_AGGREGATE_NAMES",
            "nested_aggregate",
            "aggregate_argument",
            "sql_null",
        ),
    )
    for key in complete_absences:
        result = _lookup(key)
        assert isinstance(result, Absent)
        assert result.reason is CapabilityReasonCode.NO_CATALOG_ENTRY

    canonical = _algebra_key(
        "count", "argument_inspection", "arity_0", "does_not_inspect_values"
    )
    malformed = (
        replace(canonical, operands=("arity_0",)),
        replace(
            canonical,
            operands=("arity_0", "does_not_inspect_values", "extra"),
        ),
        replace(canonical, operands=("arity_0", "Bogus")),
        replace(canonical, operands=("arity_0", "Zero")),
        replace(canonical, operands=("Bogus", "zero")),
        replace(canonical, subject="future_aggregate"),
        replace(canonical, operation="future_property"),
        replace(canonical, context="expression"),
        replace(canonical, dialect="postgresql"),
        replace(canonical, dialect="postgresql", extension="future"),
        _algebra_key("avg", "empty_input_result", "arity_1", "sql_null"),
        _algebra_key("sum", "associativity", "all_supported_signatures", "true"),
        _algebra_key(
            "SEMANTIC_AGGREGATE_NAMES",
            "window_over",
            "all_current_aggregates",
            "supported",
        ),
    )
    for key in malformed:
        unknown = _lookup(key)
        assert isinstance(unknown, Unknown)
        assert unknown.reason is CapabilityReasonCode.NOT_EVIDENCED


def test_modifier_window_nested_global_grouped_and_clause_boundaries_are_exact() -> (
    None
):
    algebra = _facts("_AGGREGATE_ALGEBRA_FACTS")
    assert tuple(fact.key.operation for fact in algebra[10:]) == (
        "aggregate_filter",
        "inline_distinct_modifier",
        "aggregate_internal_ordering",
        "generic_aggregate_modifier",
        "nested_aggregate",
        "scalar_wrapping",
    )
    combined = _facts("_AGGREGATE_CAPABILITY_FACTS")
    assert not any("window" in (fact.key.operation or "").lower() for fact in combined)
    assert not any(fact.key.domain is CapabilityDomain.CLAUSE for fact in combined)
    assert all(
        fact.key.operands[-2:] == ("GROUP", "aggregate_result")
        for fact in _facts("_AGGREGATE_SIGNATURE_FACTS")
    )
    assert not any("global" in fact.key.operands for fact in combined)
    assert not any("grouped" in fact.key.operands for fact in combined)


def test_active_conflict_ledger_and_no_authority_omissions_are_preserved() -> None:
    combined = _facts("_AGGREGATE_CAPABILITY_FACTS")
    key_text = "\n".join(
        "\x1f".join(
            (
                fact.key.domain.value,
                fact.key.subject or "",
                fact.key.operation or "",
                *fact.key.operands,
                fact.key.context or "",
                fact.key.dialect or "",
                fact.key.extension or "",
            )
        )
        for fact in combined
    ).lower()
    for forbidden in (
        "monoid",
        "associativ",
        "commutativ",
        "decompos",
        "invertib",
        "incremental",
        "fanout",
        "grain",
        "native_database",
        "precision_scale",
    ):
        assert forbidden not in key_text
    spec = _read(SPEC_PATH)
    for ledger_item in (
        "count(alias/Shape)",
        "like",
        "matches(Text, Text)",
        "Non-Decimal type arguments",
        "Division",
        "Null literal",
        "Generic comparison",
        "No-GROUP aggregate post-filtering",
    ):
        assert ledger_item in spec


def test_spec_headings_and_required_phrases_are_exact() -> None:
    spec = _read(SPEC_PATH)
    headings = tuple(
        match.group(1).strip()
        for match in re.finditer(r"^## (?!#)(.+?)\s*$", spec, re.MULTILINE)
    )
    assert headings == SPEC_H2
    for required in (
        "53 entries / 52 unique keys",
        "16 entries / 16 unique keys",
        "69 entries / 68 unique keys",
        "Unknown(NOT_EVIDENCED)",
        "Conflict(CONFLICTING_EVIDENCE)",
        "POST60_ADVANCED_AGGREGATION_GROUPING",
        "Phase 52 Slice 8",
        "Phase 53",
        "0.1.0",
        "Phase 52 remains active and incomplete",
        "Add Phase 52 private aggregate signature and algebra facts",
    ):
        assert required in spec


def test_no_existing_consumer_public_export_registry_io_or_callback_exists() -> None:
    preservation_path = (
        REPO_ROOT / "src/pietto/_project/module_semantic_fact_preservation.py"
    )
    for path in (REPO_ROOT / "src/pietto").rglob("*.py"):
        if path in {SOURCE_PATH, preservation_path} or "generated" in path.parts:
            continue
        source = _read(path)
        assert "semantic.capability_aggregates" not in source
        assert "aggregate_lookup_inputs" not in source
    preservation_source = _read(preservation_path)
    assert "semantic.capability_aggregates" in preservation_source
    assert "aggregate_lookup_inputs" in preservation_source
    assert "capability_aggregates" not in _read(
        REPO_ROOT / "src/pietto/semantic/__init__.py"
    )
    assert "capability_aggregates" not in _read(REPO_ROOT / "src/pietto/__init__.py")
    tree = ast.parse(_read(SOURCE_PATH), filename=SOURCE_REL)
    assigned_names = {
        target.id
        for node in tree.body
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        for target in (node.targets if isinstance(node, ast.Assign) else (node.target,))
        if isinstance(target, ast.Name)
    }
    assert not any(
        token in name.lower()
        for name in assigned_names
        for token in ("registry", "cache", "callback", "consumer")
    )


def test_prior_private_source_hashes_are_byte_identical() -> None:
    expected = {
        "src/pietto/semantic/capability_facts.py": FACTS_SHA256,
        "src/pietto/semantic/capability_lookup.py": LOOKUP_SHA256,
        "src/pietto/semantic/capability_inventory.py": INVENTORY_SHA256,
        "src/pietto/semantic/capability_signatures.py": SIGNATURE_SHA256,
        "src/pietto/semantic/capability_contexts.py": CONTEXT_SHA256,
    }
    assert {
        path: hashlib.sha256((REPO_ROOT / path).read_bytes()).hexdigest()
        for path in expected
    } == expected


def test_compiler_semantic_subset_project_and_raw_hash_readers_are_exact() -> None:
    compiler_paths = _compiler_paths()
    semantic_paths = tuple((REPO_ROOT / "src/pietto/semantic").glob("*.py"))
    phase15_paths = tuple(
        path
        for path in semantic_paths
        if path.name not in {"analyzer.py", "model.py", "relationship_metadata.py"}
    )
    project_paths = _project_private_paths()
    assert (len(compiler_paths), len(semantic_paths), len(phase15_paths)) == (
        105,
        36,
        33,
    )
    assert len(project_paths) == 30
    assert _digest(compiler_paths) == COMPILER_DIGEST
    assert _digest(semantic_paths) == SEMANTIC_DIGEST
    assert _digest(phase15_paths) == PHASE15_SUBSET_DIGEST
    assert _digest(project_paths) == PROJECT_PRIVATE_DIGEST

    tracked = tuple(_git_output(["ls-files"]).splitlines())
    untracked = tuple(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    )
    readable = tuple(
        sorted(path for path in {*tracked, *untracked} if (REPO_ROOT / path).is_file())
    )
    for digest, expected_readers in (
        (COMPILER_DIGEST, COMPILER_READERS),
        (SEMANTIC_DIGEST, SEMANTIC_READERS),
        (PHASE15_SUBSET_DIGEST, PHASE15_READERS),
    ):
        actual = tuple(
            sorted(
                path
                for path in readable
                if digest.encode("ascii") in (REPO_ROOT / path).read_bytes()
            )
        )
        assert actual == tuple(sorted(expected_readers))

    boundary_owners = tuple(
        sorted(
            path
            for path in readable
            if re.search(
                rb'^BOUNDARY_HASH = "[0-9a-f]{64}"$',
                (REPO_ROOT / path).read_bytes(),
                re.MULTILINE,
            )
        )
    )
    assert boundary_owners == tuple(sorted(BOUNDARY_HASH_OWNERS))
    for path in boundary_owners:
        match = re.search(
            r'^BOUNDARY_HASH = "([0-9a-f]{64})"$',
            _read(REPO_ROOT / path),
            re.MULTILINE,
        )
        assert match is not None
        assert match.group(1) == COMPILER_DIGEST

    topology = (
        (
            "tests/test_phase13_completion_audit.py",
            (
                "tests/test_phase14_candidate_decision_audit.py",
                "tests/test_phase14_planning_audit.py",
            ),
        ),
        (
            "tests/test_phase15_semantic_completion_audit.py",
            ("tests/test_phase15_completion_audit.py",),
        ),
        (
            "tests/test_phase16_current_syntax_surface_audit.py",
            ("tests/test_phase16_completion_audit.py",),
        ),
        (
            "tests/test_phase16_language_direction_audit.py",
            ("tests/test_phase16_completion_audit.py",),
        ),
        (
            "tests/test_phase16_safety_deferral_sql_portability.py",
            ("tests/test_phase16_completion_audit.py",),
        ),
    )
    assert sum(len(outers) for _, outers in topology) == 6
    for inner, outers in topology:
        inner_sha = hashlib.sha256((REPO_ROOT / inner).read_bytes()).hexdigest()
        actual = tuple(
            path
            for path in readable
            if inner_sha.encode("ascii") in (REPO_ROOT / path).read_bytes()
        )
        assert actual == (
            *outers,
            "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
            _SLICE10_READER_MIGRATION_PATHS[-1],
            "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
        )
    for outer in (
        "tests/test_phase14_candidate_decision_audit.py",
        "tests/test_phase14_planning_audit.py",
        "tests/test_phase15_completion_audit.py",
        "tests/test_phase16_completion_audit.py",
    ):
        outer_sha = hashlib.sha256((REPO_ROOT / outer).read_bytes()).hexdigest()
        actual = tuple(
            path
            for path in readable
            if outer_sha.encode("ascii") in (REPO_ROOT / path).read_bytes()
        )
        assert actual == (
            "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
            _SLICE10_READER_MIGRATION_PATHS[-1],
            "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
        )


def test_package_version_tags_gate2_dirty_state_and_allowlist_are_exact() -> None:
    with PYPROJECT_PATH.open("rb") as stream:
        project = tomllib.load(stream)
    assert project["project"]["version"] == "0.1.0"
    branch = _git_output(["branch", "--show-current"])
    head = _git_output(["rev-parse", "HEAD"])
    main = _git_optional_ref("refs/heads/main")
    origin_main = _git_optional_ref("refs/remotes/origin/main")
    origin_pr_head = _git_optional_ref(PR_REPAIR_GATE2_ORIGIN_REF)
    tracked_paths = set(_git_output(["diff", "--name-only"]).splitlines()) - {""}
    tracked_status = tuple(_git_output(["diff", "--name-status"]).splitlines())
    untracked_paths = set(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    ) - {""}
    dirty_paths = tracked_paths | untracked_paths
    slice13_modified = _slice13_paths("MODIFIED_PATHS")
    slice13_added = _slice13_paths("ADDED_PATHS")
    slice13_allowlist = slice13_modified | slice13_added

    assert _git_output(["tag", "--list"]) == ""
    assert _git_output(["tag", "--points-at", "HEAD"]) == ""
    assert _git_output(["diff", "--cached", "--name-status"]) == ""
    repair_gate2_active = _phase54_active_gate2_is_active()
    slice11_pr_ci_repair_active = phase54_slice11_pr_ci_repair_is_active()
    slice12_pr_ci_repair_active = phase54_slice12_pr_ci_repair_is_active()
    slice12_product_repair3_active = phase54_slice12_product_repair3_is_active()
    slice12_product_repair10_active = phase54_slice12_product_repair10_is_active()
    slice12_product_repair11_active = phase54_slice12_product_repair11_is_active()
    slice12_product_repair12_active = phase54_slice12_product_repair12_is_active()
    slice12_product_repair13_active = phase54_slice12_product_repair13_is_active()
    slice12_product_repair14_active = phase54_slice12_product_repair14_is_active()
    slice12_mechanical_repair4_active = phase54_slice12_mechanical_repair4_is_active()
    slice12_mechanical_repair3_active = phase54_slice12_mechanical_repair3_is_active()
    slice12_product_repair3_clean_topic_active = (
        phase54_slice12_product_repair3_clean_topic_is_active()
    )
    slice12_product_repair10_clean_topic_active = (
        phase54_slice12_product_repair10_clean_topic_is_active()
    )
    slice12_product_repair11_clean_topic_active = (
        phase54_slice12_product_repair11_clean_topic_is_active()
    )
    slice12_product_repair12_clean_topic_active = (
        phase54_slice12_product_repair12_clean_topic_is_active()
    )
    slice12_product_repair13_clean_topic_active = (
        phase54_slice12_product_repair13_clean_topic_is_active()
    )
    slice12_product_repair14_clean_topic_active = (
        phase54_slice12_product_repair14_clean_topic_is_active()
    )
    slice12_mechanical_repair3_clean_topic_active = (
        phase54_slice12_mechanical_repair3_clean_topic_is_active()
    )
    slice12_mechanical_repair4_clean_topic_active = (
        phase54_slice12_mechanical_repair4_clean_topic_is_active()
    )
    slice11_python313_repair_active = phase54_slice11_python313_repair_is_active()
    slice11_substantive_recovery_active = (
        phase54_slice11_substantive_recovery_is_active()
    )
    assert repair_gate2_active or dirty_paths in (
        set(),
        ALLOWLIST_PATHS,
        PR_REPAIR_ALLOWLIST_PATHS,
        COMPLETENESS_REPAIR_ALLOWLIST_PATHS,
        SLICE8_ALLOWLIST_PATHS,
        SLICE9_ALLOWLIST_PATHS,
        slice13_allowlist,
    )

    if slice11_python313_repair_active:
        assert tracked_paths == set(PHASE54_SLICE11_PYTHON313_REPAIR_MODIFIED_PATHS)
        assert untracked_paths == set()
    elif slice11_substantive_recovery_active:
        assert tracked_paths == set(PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_MODIFIED_PATHS)
        assert untracked_paths == set()
    elif slice11_pr_ci_repair_active:
        assert tracked_paths == set(PHASE54_SLICE11_PR_CI_REPAIR_MODIFIED_PATHS)
        assert untracked_paths == set()
    elif slice12_pr_ci_repair_active:
        assert tracked_paths == set(PHASE54_SLICE12_PR_CI_REPAIR_MODIFIED_PATHS)
        assert untracked_paths == set()
    elif slice12_mechanical_repair4_active:
        assert tracked_paths == set(PHASE54_SLICE12_MECHANICAL_REPAIR4_MODIFIED_PATHS)
        assert untracked_paths == set()
    elif slice12_mechanical_repair3_active:
        assert tracked_paths == set(PHASE54_SLICE12_MECHANICAL_REPAIR3_MODIFIED_PATHS)
        assert untracked_paths == set()
    elif slice12_product_repair14_active:
        assert tracked_paths == set(PHASE54_SLICE12_PRODUCT_REPAIR14_MODIFIED_PATHS)
        assert untracked_paths == set()
    elif slice12_product_repair13_active:
        assert tracked_paths == set(PHASE54_SLICE12_PRODUCT_REPAIR13_MODIFIED_PATHS)
        assert untracked_paths == set()
    elif slice12_product_repair12_active:
        assert tracked_paths == set(PHASE54_SLICE12_PRODUCT_REPAIR12_MODIFIED_PATHS)
        assert untracked_paths == set()
    elif slice12_product_repair11_active:
        assert tracked_paths == set(PHASE54_SLICE12_PRODUCT_REPAIR11_MODIFIED_PATHS)
        assert untracked_paths == set()
    elif slice12_product_repair10_active:
        assert tracked_paths == set(PHASE54_SLICE12_PRODUCT_REPAIR10_MODIFIED_PATHS)
        assert untracked_paths == set()
    elif slice12_mechanical_repair4_clean_topic_active:
        assert tracked_paths == untracked_paths == set()
        _assert_clean_checkout_refs(
            branch=branch,
            head=head,
            main=main,
            origin_main=origin_main,
        )
    elif slice12_mechanical_repair3_clean_topic_active:
        assert tracked_paths == untracked_paths == set()
        _assert_clean_checkout_refs(
            branch=branch,
            head=head,
            main=main,
            origin_main=origin_main,
        )
    elif slice12_product_repair14_clean_topic_active:
        assert tracked_paths == untracked_paths == set()
        _assert_clean_checkout_refs(
            branch=branch,
            head=head,
            main=main,
            origin_main=origin_main,
        )
    elif slice12_product_repair13_clean_topic_active:
        assert tracked_paths == untracked_paths == set()
        _assert_clean_checkout_refs(
            branch=branch,
            head=head,
            main=main,
            origin_main=origin_main,
        )
    elif slice12_product_repair12_clean_topic_active:
        assert tracked_paths == untracked_paths == set()
        _assert_clean_checkout_refs(
            branch=branch,
            head=head,
            main=main,
            origin_main=origin_main,
        )
    elif slice12_product_repair10_clean_topic_active:
        assert tracked_paths == untracked_paths == set()
        _assert_clean_checkout_refs(
            branch=branch,
            head=head,
            main=main,
            origin_main=origin_main,
        )
    elif slice12_product_repair11_clean_topic_active:
        assert tracked_paths == untracked_paths == set()
        _assert_clean_checkout_refs(
            branch=branch,
            head=head,
            main=main,
            origin_main=origin_main,
        )
    elif slice12_product_repair3_active:
        assert tracked_paths == set(PHASE54_SLICE12_PRODUCT_REPAIR3_MODIFIED_PATHS)
        assert untracked_paths == set()
    elif slice12_product_repair3_clean_topic_active:
        assert tracked_paths == untracked_paths == set()
        _assert_clean_checkout_refs(
            branch=branch,
            head=head,
            main=main,
            origin_main=origin_main,
        )
    elif phase54_post_slice12_interlude_dirty_is_active():
        assert tracked_paths == set(
            phase54_post_slice12_interlude_expected_modified_paths()
        )
        assert untracked_paths == set(
            phase54_post_slice12_interlude_expected_added_paths()
        )
    elif repair_gate2_active:
        assert tracked_paths == set(PHASE54_ACTIVE_GATE2_MODIFIED_PATHS)
        assert untracked_paths == set(PHASE54_ACTIVE_GATE2_ADDED_PATHS)
    elif not dirty_paths:
        assert tracked_paths == set()
        assert tracked_status == ()
        assert untracked_paths == set()
        _assert_clean_checkout_refs(
            branch=branch,
            head=head,
            main=main,
            origin_main=origin_main,
        )
    elif dirty_paths == slice13_allowlist:
        assert branch == "main"
        assert tracked_paths == slice13_modified
        assert tracked_status == tuple(
            f"M\t{path}" for path in sorted(slice13_modified)
        )
        assert untracked_paths == slice13_added
        assert head == main == origin_main
        assert head in (
            "4ff3c131fba54d83b56f3c50e14f7c2337c1eb52",
            "d8a5e9ab3de70ce30575513c73560c86430eca63",
            "15bae172ee151e370fe59d3bf909d735aee6aa90",
            "0f3c955c5a5fbd8046ef611ad1bef0b636c8be01",
            "c44a4271d9592cb393d2232f127a59d8466cc60a",
            "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16",
            "027b33cafcfd58916a89e299487dad38d24ade6c",
            "0ceb9a476e6592714cdc76845949ba0ae5123eb5",
            "b81843acadb294630db361c09949868d004b1bca",
        )
    elif dirty_paths == SLICE9_ALLOWLIST_PATHS:
        assert branch == "main"
        assert tracked_paths == SLICE9_MODIFIED_PATHS
        assert tracked_status == tuple(
            f"M\t{path}" for path in sorted(SLICE9_MODIFIED_PATHS)
        )
        assert untracked_paths == SLICE9_ADDED_PATHS
        assert head == main == origin_main == SLICE9_BASE_HEAD_SHA
    elif dirty_paths == SLICE8_ALLOWLIST_PATHS:
        assert branch == "main"
        assert tracked_paths == SLICE8_MODIFIED_PATHS
        assert tracked_status == tuple(
            f"M\t{path}" for path in sorted(SLICE8_MODIFIED_PATHS)
        )
        assert untracked_paths == SLICE8_ADDED_PATHS
        assert head == main == origin_main == SLICE8_GATE2_BASE_HEAD_SHA
    elif dirty_paths == ALLOWLIST_PATHS:
        assert branch == "main"
        assert dirty_paths == ALLOWLIST_PATHS
        assert tracked_paths == set(MODIFIED_READER_PATHS)
        assert len(tracked_status) == len(MODIFIED_READER_PATHS)
        assert all(entry.startswith("M\t") for entry in tracked_status)
        assert {entry.removeprefix("M\t") for entry in tracked_status} == set(
            MODIFIED_READER_PATHS
        )
        assert untracked_paths == ADDED_PATHS
        assert origin_main is not None
        assert head == main == origin_main == GATE2_BASE_HEAD_SHA
    elif dirty_paths == COMPLETENESS_REPAIR_ALLOWLIST_PATHS:
        assert branch == "main"
        assert tracked_paths == COMPLETENESS_REPAIR_ALLOWLIST_PATHS
        assert len(tracked_status) == 44
        assert all(entry.startswith("M\t") for entry in tracked_status)
        assert {entry.removeprefix("M\t") for entry in tracked_status} == (
            COMPLETENESS_REPAIR_ALLOWLIST_PATHS
        )
        assert untracked_paths == set()
        assert head == main == origin_main == COMPLETENESS_REPAIR_GATE2_BASE_HEAD_SHA
    else:
        assert dirty_paths == PR_REPAIR_ALLOWLIST_PATHS
        assert branch == PR_REPAIR_GATE2_BRANCH
        assert tracked_paths == PR_REPAIR_ALLOWLIST_PATHS
        assert len(tracked_status) == len(PR_REPAIR_ALLOWLIST_PATHS)
        assert all(entry.startswith("M\t") for entry in tracked_status)
        assert {entry.removeprefix("M\t") for entry in tracked_status} == (
            PR_REPAIR_ALLOWLIST_PATHS
        )
        assert untracked_paths == set()
        assert origin_main == main == PR_REPAIR_GATE2_MAIN_SHA
        assert origin_pr_head == head == PR_REPAIR_GATE2_HEAD_SHA

    assert len(MODIFIED_READER_PATHS) == len(set(MODIFIED_READER_PATHS)) == 41
    assert len(ALLOWLIST_PATHS) == 44
    assert sum(path.endswith(".py") for path in ALLOWLIST_PATHS) == 43
    assert sum(path.endswith(".md") for path in ALLOWLIST_PATHS) == 1
    assert len(PR_REPAIR_ALLOWLIST_PATHS) == 6
    assert len(COMPLETENESS_REPAIR_ALLOWLIST_PATHS) == 44
    assert all(path.endswith(".py") for path in COMPLETENESS_REPAIR_ALLOWLIST_PATHS)
    assert len(SLICE8_ALLOWLIST_PATHS) == 6
    assert sum(path.endswith(".py") for path in SLICE8_ALLOWLIST_PATHS) == 5
    assert sum(path.endswith(".md") for path in SLICE8_ALLOWLIST_PATHS) == 1
    assert len(SLICE9_ALLOWLIST_PATHS) == 9
    assert len(SLICE9_MODIFIED_PATHS) == 7
    assert len(SLICE9_ADDED_PATHS) == 2


def test_static_test_inventory_and_tier1_selection_are_exact() -> None:
    function_count, item_count, parametrized, cardinalities = _pytest_shape(SELF_PATH)
    assert (function_count, item_count) == (28, 69)
    assert (
        tuple(
            node.name
            for node in ast.parse(_read(SELF_PATH), filename=SELF_REL).body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
        )
        == EXPECTED_TEST_NAMES
    )
    assert parametrized == [
        "test_signature_family_counts_are_exact",
        "test_signature_result_type_nullability_stage_and_role_are_exact",
        "test_signature_evidence_order_and_authority_are_exact",
        "test_signature_lookup_found_is_exact",
        "test_supported_algebra_fact_is_exact",
        "test_rejected_algebra_fact_group_is_exact",
    ]
    assert cardinalities == [6, 13, 8, 5, 10, 5]

    test_files = tuple((REPO_ROOT / "tests").glob("test_*.py"))
    top_level_functions = sum(
        len(
            [
                node
                for node in ast.parse(_read(path), filename=path.as_posix()).body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name.startswith("test_")
            ]
        )
        for path in test_files
    )
    assert (len(test_files), top_level_functions) == (462, 5324)

    compatible, per_file_items = _prior_compatible_nodes()
    assert (len(compatible), per_file_items) == (69, (24, 33, 63))
    compatible_payload = "".join(node + "\n" for node in compatible).encode("utf-8")
    direct_payload = "".join(node + "\n" for node in DIRECT_TIER1_NODES).encode("utf-8")
    operands = (
        SLICE5_TEST_REL,
        SLICE6_TEST_REL,
        SELF_REL,
        SLICE8_TEST_REL,
        *compatible,
        *DIRECT_TIER1_NODES,
    )
    operand_payload = "".join(node + "\n" for node in operands).encode("utf-8")
    assert (
        len(compatible_payload),
        hashlib.sha256(compatible_payload).hexdigest(),
    ) == (
        8708,
        "ad36af418104abe3afb21e94e1f64e87762ec2006047151c20ddb7047b25392a",
    )
    assert len(DIRECT_TIER1_NODES) == len(set(DIRECT_TIER1_NODES)) == 44
    assert (len(direct_payload), hashlib.sha256(direct_payload).hexdigest()) == (
        4860,
        "417a72e2091fdd85e8b1d5f76bc4a21a64e55dbdb1eb87de4318a1b344a67faf",
    )
    assert (
        len(operands),
        len(operand_payload),
        hashlib.sha256(operand_payload).hexdigest(),
    ) == (
        117,
        13823,
        "9d77e53a1d9d439d570cac70e1facfbfaaae5645958604de98924390cb6b3212",
    )
    assert 64 + 69 + 69 + 69 + sum(per_file_items) + 44 == 435
    assert 6087 + 69 == 6156


def test_tier2_manifest_identity_and_classification_are_exact() -> None:
    prior = _literal_tuple(REPO_ROOT / SLICE6_TEST_REL, "TIER2_MANIFEST")
    removed = {
        "--deselect="
        + SLICE4_TEST_REL
        + "::test_gate2_dirty_untracked_and_index_states_are_exact",
        "--deselect="
        + SLICE5_TEST_REL
        + "::test_package_version_tags_gate2_dirty_state_and_allowlist_are_exact",
    }
    manifest = tuple(sorted(set(prior) - removed))
    assert removed <= set(prior)
    assert len(manifest) == len(set(manifest)) == 140
    payload = "".join(line + "\n" for line in manifest).encode("utf-8")
    files = {
        line.removeprefix("--deselect=").split("::", maxsplit=1)[0] for line in manifest
    }
    assert (len(files), len(payload), hashlib.sha256(payload).hexdigest()) == (
        106,
        18035,
        "a74e473501185eb2c1912018091d12711fdab8cc80c6a2a2849ceb63e09c5e1f",
    )
    classification = {line: "CLEAN_ONLY_DESELECT" for line in manifest}
    assert set(classification.values()) == {"CLEAN_ONLY_DESELECT"}
    assert not any(SELF_REL in line for line in manifest)
    for line in manifest:
        node_id = line.removeprefix("--deselect=")
        path, function = node_id.split("::", maxsplit=1)
        tree = ast.parse(_read(REPO_ROOT / path), filename=path)
        matches = [
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == function
        ]
        assert len(matches) == 1
        assert _parametrize_values(matches[0]) == 1
    assert not any(
        path in line
        for path in (SLICE6_TEST_REL, SELF_REL, SLICE8_TEST_REL)
        for line in manifest
    )
    assert 6156 - len(manifest) == 6016


def test_slice7_lifecycle_validation_gate3_and_release_boundaries_are_exact() -> None:
    spec = _read(SPEC_PATH)
    for required in (
        "Phase 52 remains active and incomplete",
        "Phase 52 Slice 8",
        "Phase 53",
        "Add Phase 52 private aggregate signature and algebra facts",
        "does not authorize staging, committing, pushing, tags, release",
    ):
        assert required in spec
    assert "scripts/validate.py" not in spec
    assert "package version bump" not in spec.lower()


def test_backend_evidence_is_separate_ordered_and_non_authoritative() -> None:
    combined = _facts("_AGGREGATE_CAPABILITY_FACTS")
    assert len(combined) == 69
    assert len({fact.key for fact in combined}) == 68
    for fact in combined:
        sources = tuple(entry.source for entry in fact.evidence)
        backends = tuple(
            entry
            for entry in fact.evidence
            if entry.source is CapabilityEvidenceSource.BACKEND
        )
        if backends:
            assert CapabilityEvidenceSource.SEMANTIC_PROCEDURE in sources
            assert sources.index(CapabilityEvidenceSource.SEMANTIC_PROCEDURE) < (
                sources.index(CapabilityEvidenceSource.BACKEND)
            )
            assert tuple((entry.dialect, entry.backend) for entry in backends) == (
                ("postgresql", "postgresql"),
                ("mysql", "private-mysql"),
            )
        assert all(entry.extension is None for entry in fact.evidence)


_SLICE10_READER_MIGRATION_PATHS = (
    "docs/spec/phase53-partition-binding-multi-key-visibility-diagnostics-contract-v1.md",
    "src/pietto/semantic/window_partition_analysis.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
)
# Phase 53 Slice 13 reader migration.
