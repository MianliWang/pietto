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
    phase54_publication_clean_topic_is_active,
    phase54_publication_topic_branch,
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

import pietto.semantic.capability_contexts as capability_contexts
import pietto.semantic.capability_inventory as capability_inventory
import pietto.semantic.capability_signatures as capability_signatures
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
SOURCE_REL = "src/pietto/semantic/capability_contexts.py"
SPEC_REL = "docs/spec/phase52-expression-stage-clause-capability-facts-v1.md"
SELF_REL = "tests/test_phase52_expression_stage_clause_capability_facts.py"
FACTS_REL = "src/pietto/semantic/capability_facts.py"
LOOKUP_REL = "src/pietto/semantic/capability_lookup.py"
INVENTORY_REL = "src/pietto/semantic/capability_inventory.py"
SIGNATURE_REL = "src/pietto/semantic/capability_signatures.py"
SLICE2_TEST_REL = "tests/test_phase52_private_capability_fact_foundation.py"
SLICE3_TEST_REL = "tests/test_phase52_fail_closed_capability_lookup.py"
SLICE4_TEST_REL = (
    "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py"
)
SLICE5_TEST_REL = "tests/test_phase52_scalar_function_operator_signature_facts.py"
SLICE7_TEST_REL = "tests/test_phase52_aggregate_signature_algebra_facts.py"
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
SOURCE_PATH = REPO_ROOT / SOURCE_REL
SPEC_PATH = REPO_ROOT / SPEC_REL
SELF_PATH = REPO_ROOT / SELF_REL
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

SLICE6_GATE2_HEAD_SHA = "21bb988a8b28e9d13e7e2c8fdf78ea3a7054b5b0"
CI_REPAIR_BASE_HEAD_SHA = "7d9916fe8fbfd6c8d642a8f62f18eb87981d68bc"
PR_REPAIR_GATE2_BRANCH = "dependabot/uv/uv-build-gte-0.11.29-and-lt-0.12.0"
PR_REPAIR_GATE2_HEAD_SHA = "8538e9e612c4a39b93a43f85532bfcb75853f9c1"
PR_REPAIR_GATE2_MAIN_SHA = "522ce4ea193c3b2bbbe88644d77a2410230f42ad"
PR_REPAIR_GATE2_ORIGIN_REF = f"refs/remotes/origin/{PR_REPAIR_GATE2_BRANCH}"
FACTS_SHA256 = "bd68bad4e13a2b945962458fc47359a408d27b1563ba25f5713a8f8099671d21"
LOOKUP_SHA256 = "4d4c2676b3181758f01c95ca312fd0f76cebcb74ac1bcab0deefb15fc04abf26"
INVENTORY_SHA256 = "f11eee2a53fda26057c35be047bfa265c68794ad76054bc5636781f0b5164b26"
SIGNATURE_SHA256 = "810f347080e0bb7dc674821aa6387c5f7618ac216832194ef19820326eef71d2"
PROJECT_PRIVATE_DIGEST = (
    "61b7cdcd59e9a8d197d32e3e2c0df03f41ab1695e7ca36e2fb9687e6af280539"
)
TIER2_MANIFEST_BYTES = 18319
TIER2_MANIFEST_FILES = 108
TIER2_MANIFEST_SHA256 = (
    "aea0deb90e0870740b40614fc911ad9483cb3851842aa9a4a9ccecc63baf6f79"
)
COMPATIBLE_SELECTOR_SHA256 = (
    "b2a487be78c18fddd2e2857caef322729a2e87f8804ea5aa6aad00bb6a711b58"
)
DIRECT_SELECTOR_SHA256 = (
    "417a72e2091fdd85e8b1d5f76bc4a21a64e55dbdb1eb87de4318a1b344a67faf"
)
TIER1_OPERAND_SHA256 = (
    "5f2e05d466f89f18c26a8e6b6fe6739d56d75ded59711b990e10def17ba7aabd"
)

SPEC_H2 = (
    "Status And Authority",
    "Private Context Module And Ordering",
    "Stage Vocabulary And Key Encoding",
    "Expression Stage Facts",
    "Clause Key Encoding And Completeness",
    "Where And Group By Clause Facts",
    "Satisfying Clause Facts",
    "Order By Clause Facts",
    "Unknown Window Aggregate And Omission Policy",
    "Four-result Lookup And Conflict Preservation",
    "Evidence Ordering And Authority Boundaries",
    "Privacy Static Compatibility And Validation Locks",
    "Slice Ownership Lifecycle And Release Boundary",
)

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
    "tests/test_phase52_private_capability_fact_foundation.py",
    "tests/test_phase52_fail_closed_capability_lookup.py",
    "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py",
    "tests/test_phase52_scalar_function_operator_signature_facts.py",
)
ADDED_PATHS = {SOURCE_REL, SPEC_REL, SELF_REL}
ALLOWLIST_PATHS = {*MODIFIED_READER_PATHS, *ADDED_PATHS}
REPAIR_ALLOWLIST_PATHS = {SELF_REL}
PR_REPAIR_ALLOWLIST_PATHS = {
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase51_aggregate_grouped_downstream_propagation.py",
    "tests/test_phase51_completion_audit_and_status_lock.py",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
    "tests/test_phase52_aggregate_signature_algebra_facts.py",
    SELF_REL,
}
SLICE8_MODIFIED_PATHS = {
    SLICE4_TEST_REL,
    SLICE5_TEST_REL,
    SELF_REL,
    SLICE7_TEST_REL,
}
SLICE8_ADDED_PATHS = {SLICE8_SPEC_REL, SLICE8_TEST_REL}
SLICE8_ALLOWLIST_PATHS = SLICE8_MODIFIED_PATHS | SLICE8_ADDED_PATHS
SLICE9_MODIFIED_PATHS = {
    "docs/plan/phase-52-core-type-system-capability-foundation.md",
    "docs/spec/pietto-active-roadmap-phase51-60-v1.md",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py",
    SLICE5_TEST_REL,
    SELF_REL,
    SLICE7_TEST_REL,
    SLICE8_TEST_REL,
}
SLICE9_ADDED_PATHS = {SLICE9_SPEC_REL, SLICE9_TEST_REL}
SLICE9_ALLOWLIST_PATHS = SLICE9_MODIFIED_PATHS | SLICE9_ADDED_PATHS

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
TIER2_MANIFEST = (
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
    "--deselect=tests/test_maintenance_phase3_developer_workflow.py::test_dirty_paths_are_clean_or_exact_slice8_allowlist",
    "--deselect=tests/test_maintenance_phase3_non_pytest_validation_optimization.py::test_dirty_paths_are_clean_or_exact_slice7_allowlist",
    "--deselect=tests/test_maintenance_phase3_parallel_safety.py::test_dirty_paths_are_clean_or_exact_slice5_allowlist",
    "--deselect=tests/test_maintenance_phase3_validation_acceleration_scope_lock.py::test_dirty_paths_are_clean_or_exact_slice3_allowlist",
    "--deselect=tests/test_maintenance_phase4_benchmark_evidence_decision.py::test_dirty_paths_are_clean_or_exact_slice3_allowlist",
    "--deselect=tests/test_maintenance_phase4_completion_audit.py::test_dirty_paths_are_clean_or_exact_slice4_allowlist",
    "--deselect=tests/test_maintenance_phase4_worker_strategy_benchmark_protocol.py::test_dirty_paths_are_clean_or_exact_slice1_allowlist",
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
    "--deselect=tests/test_phase49_compatibility_privacy_hash_lock_readiness.py::test_slice13_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase49_completion_audit_status_lock.py::test_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase49_computed_alias_origin_provenance_privacy.py::test_slice5_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase49_computed_alias_project_row_schema_mvp.py::test_phase49_slice4_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase49_computed_let_multi_hop_row_lineage.py::test_slice11_forbidden_files_source_boundaries_version_and_dirty_paths",
    "--deselect=tests/test_phase49_let_visibility_order_shadowing_hardening.py::test_slice8_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py::test_slice10_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase49_private_row_level_dependency_graph_scaffold.py::test_slice9_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase49_project_let_scope_value_facts.py::test_phase49_slice6_package_version_and_dirty_paths_are_locked",
    "--deselect=tests/test_phase49_project_row_expression_schema_helper_contract.py::test_slice2_allowlist_package_version_and_forbidden_surfaces_are_locked",
    "--deselect=tests/test_phase49_project_row_expression_type_nullability_adapter.py::test_slice3_dirty_paths_are_exactly_gate2_allowlist",
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
    "--deselect=tests/test_phase50_semantic_package_model_readiness.py::test_protected_paths_version_tag_staging_and_dirty_set_are_locked",
    "--deselect=tests/test_phase50_type_system_gap_capability_readiness.py::test_compatibility_guards_protected_surfaces_version_and_dirty_set_are_locked",
    "--deselect=tests/test_phase50_window_function_readiness.py::test_compatibility_guards_protected_surfaces_and_dirty_set_are_locked",
    "--deselect=tests/test_phase51_aggregate_grouped_downstream_propagation.py::test_slice10_documentation_allowlist_hashes_and_protected_boundaries",
    "--deselect=tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py::test_slice9_documentation_allowlist_hash_and_protected_boundaries",
    "--deselect=tests/test_phase51_aggregate_grouped_output_schema_foundation_scope_lock.py::test_historical_roadmap_package_tag_goldens_protected_diffs_and_dirty_set",
    "--deselect=tests/test_phase51_aggregate_grouped_state_duplicate_hardening.py::test_slice7_documentation_exact_allowlist_and_protected_boundaries",
    "--deselect=tests/test_phase51_clause_dependency_fail_closed.py::test_slice8_documentation_exact_allowlist_dirty_and_protected_boundaries",
    "--deselect=tests/test_phase51_completion_audit_and_status_lock.py::test_static_git_helper_and_exact_slice12_dirty_set_are_locked",
    "--deselect=tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py::test_slice11_contract_plan_allowlist_and_protected_boundaries_are_locked",
    "--deselect=tests/test_phase51_selected_let_accepted_expression_aggregate.py::test_plan_contract_versions_protected_boundaries_and_exact_dirty_set",
    "--deselect=tests/test_phase52_core_type_system_capability_foundation_scope_lock.py::test_static_audit_shape_allowlist_and_heading_matching_are_locked",
    "--deselect=tests/test_phase52_fail_closed_capability_lookup.py::test_gate2_dirty_untracked_and_index_states_are_exact",
    "--deselect=tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py::test_gate2_dirty_untracked_and_index_states_are_exact",
    "--deselect=tests/test_phase52_private_capability_fact_foundation.py::test_gate2_dirty_untracked_and_index_states_are_exact",
    "--deselect=tests/test_phase52_scalar_function_operator_signature_facts.py::test_package_version_tags_gate2_dirty_state_and_allowlist_are_exact",
)

STAGE_EVIDENCE_HASHES = (
    "38f2798010bbc9f00fadfdcac5a8cd7634f172ab74161282696f218a2393efd0",
    "8a0cbfa1e1ebd639ccf06c87c351405ada2b2ea86333b90ab6360707c9edb12f",
    "45f548b1d7116a7b1ff4b892f75dd2bb00f5ced607e3f250c386b1000a1c53d5",
    "16fa9648acf7d73982b7a1c720be3d8b8b10e8a6ab6c3f897406214f8ed8c253",
    "3bd671e6ce6ca80026373f5c45d0fd3b05cfeb980efb828990b0da430a88e065",
    "d9c4eb20148ef88e6e55ef402c5c0ec0f7c7b8ca578e860fef45c783e42b292d",
    "a87e9b63565dff68e098f12ebdb9ccf8b1be6d015767228aee86721a35438b78",
)
CLAUSE_EVIDENCE_HASHES = (
    "0dabfe42b6dcd93075114989e366b6853f7644655179b6a8226df9d8b96465a5",
    "1f8a8c6b58b5e314e349a39ca02525c501b6209906b1c9f768a6e635d2c0d6c0",
    "119d9fc3c2c7be7ace6f0174a822c96faa8faf1861c731a72948ee7e4e4de2b1",
    "f3a75561fee0ff7c35c33be54b09ac18d1de17f0b9d96e0d4e13b5129ea13e09",
    "35f95f8baa2e786b2c0c9c71644ca73c720434839ae180f1bf3788e72f52e4e2",
    "1249ea5ca0e48b280911c81a40d43955f825810c5593fcd45095e6c95d737582",
    "b3e2323ff10e4a28338df89a1a22472031b155783a858f4c5c62356b049d205c",
    "0820ff50a6cd582812677c6774646a428334379949a72953b9a720e06ae48257",
    "f532aa81e9eeb90616d727b065a5575840fd347ebf8c103dd5b0cd0437807643",
    "df976089e6a8adac23c375534f21fcb3c0e572f998066e5f51a1e114432c9d92",
    "c267eda6ad529ef684325974804662ef9c521a9a61c5f69d3cb703dd6ae89622",
)

STAGE_EXPECTED = (
    ("literal_expression", "CONSTANT"),
    ("constant_scalar_expression", "CONSTANT"),
    ("resolved_row_reference", "ROW"),
    ("row_scalar_expression", "ROW"),
    ("aggregate_dependent_expression", "GROUP"),
    ("group_output_reference", "GROUP"),
    ("unresolved_reference_expression", "UNKNOWN"),
)

CLAUSE_EXPECTED = (
    (
        "where",
        (
            "ROW",
            "Bool_when_known",
            "current_nonaggregate_expression",
            "input_fields_and_row_lets",
            "select_output_aliases_forbidden",
        ),
        "pre_group_filter",
        CapabilitySupport.SUPPORTED,
        CapabilityDispositionKind.NONE,
        None,
        None,
    ),
    (
        "group_by",
        (
            "ROW",
            "no_result_type_constraint",
            "direct_input_field_or_direct_field_row_let",
            "input_fields_and_row_lets",
            "select_output_aliases_forbidden",
        ),
        "group_key",
        CapabilitySupport.SUPPORTED,
        CapabilityDispositionKind.NONE,
        None,
        None,
    ),
    (
        "satisfying",
        (
            "GROUP",
            "Bool",
            "bounded_result_predicate",
            "selected_group_key_and_aggregate_outputs",
            "selected_output_names_with_matching_aggregate_let_exception",
        ),
        "grouped_result_filter",
        CapabilitySupport.SUPPORTED,
        CapabilityDispositionKind.NONE,
        None,
        None,
    ),
    (
        "order_by",
        (
            "ROW",
            "no_result_type_constraint",
            "current_nonaggregate_expression",
            "input_fields_and_row_lets",
            "select_output_aliases_forbidden",
        ),
        "input_order",
        CapabilitySupport.SUPPORTED,
        CapabilityDispositionKind.NONE,
        None,
        None,
    ),
    (
        "order_by",
        (
            "GROUP",
            "no_result_type_constraint",
            "bare_selected_output_or_matching_group_key_row_let",
            "selected_group_key_and_aggregate_outputs",
            "selected_output_names_with_matching_group_key_let_exception",
        ),
        "grouped_result_order",
        CapabilitySupport.SUPPORTED,
        CapabilityDispositionKind.NONE,
        None,
        None,
    ),
    (
        "where",
        (
            "ROW",
            "Bool_when_known",
            "aggregate_dependent_expression",
            "input_fields_and_row_lets",
            "select_output_aliases_forbidden",
        ),
        "pre_group_filter",
        CapabilitySupport.EXPLICITLY_UNSUPPORTED,
        CapabilityDispositionKind.NONE,
        None,
        None,
    ),
    (
        "group_by",
        (
            "ROW",
            "no_result_type_constraint",
            "non_field_group_key",
            "input_fields_and_row_lets",
            "select_output_aliases_forbidden",
        ),
        "group_key",
        CapabilitySupport.EXPLICITLY_UNSUPPORTED,
        CapabilityDispositionKind.DEFERRED,
        "POST60_ADVANCED_AGGREGATION_GROUPING",
        "broad expression group keys require separate authorization",
    ),
    (
        "satisfying",
        (
            "GROUP",
            "Bool",
            "global_aggregate_postfilter",
            "no_group_aggregate_outputs",
            "selected_output_aliases_do_not_create_satisfying_scope",
        ),
        "no_group_result_filter",
        CapabilitySupport.EXPLICITLY_UNSUPPORTED,
        CapabilityDispositionKind.DEFERRED,
        "POST60_ADVANCED_AGGREGATION_GROUPING",
        "global aggregate post-filtering requires separate authorization",
    ),
    (
        "satisfying",
        (
            "GROUP",
            "Bool",
            "bounded_result_predicate",
            "unselected_raw_input_fields",
            "selected_output_names_required",
        ),
        "grouped_result_filter",
        CapabilitySupport.EXPLICITLY_UNSUPPORTED,
        CapabilityDispositionKind.NONE,
        None,
        None,
    ),
    (
        "order_by",
        (
            "ROW",
            "no_result_type_constraint",
            "aggregate_dependent_expression",
            "input_fields_and_row_lets",
            "select_output_aliases_forbidden",
        ),
        "input_order",
        CapabilitySupport.EXPLICITLY_UNSUPPORTED,
        CapabilityDispositionKind.NONE,
        None,
        None,
    ),
    (
        "order_by",
        (
            "GROUP",
            "no_result_type_constraint",
            "non_bare_or_unselected_grouped_order_expression",
            "grouped_input_or_unselected_outputs",
            "selected_output_names_required",
        ),
        "grouped_result_order",
        CapabilitySupport.EXPLICITLY_UNSUPPORTED,
        CapabilityDispositionKind.DEFERRED,
        "POST60_ADVANCED_AGGREGATION_GROUPING",
        "broad grouped result ordering requires separate authorization",
    ),
)

EXPECTED_TEST_NAMES = (
    "test_private_module_api_and_dependency_shape_is_exact",
    "test_freezer_and_combined_fact_order_are_exact",
    "test_fact_family_ownership_and_aggregate_window_separation_are_exact",
    "test_backend_and_project_evidence_remain_non_authoritative",
    "test_no_existing_consumer_or_public_export_is_added",
    "test_prior_private_source_hashes_are_byte_identical",
    "test_prior_slice4_and_slice5_fact_counts_are_unchanged",
    "test_spec_headings_and_required_phrases_are_exact",
    "test_compiler_semantic_subset_project_and_raw_hash_readers_are_exact",
    "test_package_version_tags_gate2_dirty_state_and_allowlist_are_exact",
    "test_static_test_inventory_and_tier1_selection_are_exact",
    "test_tier2_manifest_identity_and_classification_are_exact",
    "test_slice6_lifecycle_validation_publication_and_release_boundaries_are_exact",
    "test_expression_stage_fact_inventory_is_exact",
    "test_expression_stage_evidence_order_and_paths_are_exact",
    "test_expression_ast_and_context_coverage_map_is_exact",
    "test_expression_stage_lookup_found_is_exact",
    "test_expression_stage_complete_wrong_claim_is_absent",
    "test_expression_stage_incomplete_question_is_unknown",
    "test_stage_type_nullability_and_three_valued_truth_are_orthogonal",
    "test_expression_stage_injected_conflict_preserves_order",
    "test_clause_fact_inventory_order_and_combined_tuple_are_exact",
    "test_supported_clause_fact_is_exact",
    "test_unsupported_clause_fact_is_exact",
    "test_clause_evidence_order_and_paths_are_exact",
    "test_clause_completeness_and_absence_are_exact",
    "test_clause_lookup_four_results_are_exact",
    "test_clause_omissions_and_tensions_remain_unknown",
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

    if branch == phase54_publication_topic_branch():
        assert phase54_publication_clean_topic_is_active()
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


def _dirty_paths() -> set[str]:
    return {
        *_git_output(["diff", "--name-only"]).splitlines(),
        *_git_output(["ls-files", "--others", "--exclude-standard"]).splitlines(),
    } - {""}


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


def _pytest_shape(path: Path) -> tuple[int, int, list[str]]:
    tree = ast.parse(_read(path), filename=path.as_posix())
    functions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    ]
    parametrized = [node.name for node in functions if node.decorator_list]
    return (
        len(functions),
        sum(_parametrize_values(node) for node in functions),
        parametrized,
    )


def _facts(name: str) -> tuple[CapabilityFact, ...]:
    return cast(tuple[CapabilityFact, ...], getattr(capability_contexts, name))


def _lookup(key: CapabilityKey) -> Found | Absent | Unknown | Conflict:
    helper = cast(Any, capability_contexts.stage_clause_lookup_inputs)
    facts, complete, reason = helper(key)
    return lookup_capability(
        key,
        facts,
        domain_complete=complete,
        unknown_reason=reason,
    )


def _evidence_hash(fact: CapabilityFact) -> str:
    rows = []
    for entry in fact.evidence:
        rows.append(
            "\x1f".join(
                (
                    entry.source.value,
                    entry.source_path,
                    entry.source_reference,
                    "" if entry.reason is None else entry.reason.value,
                    "" if entry.dialect is None else entry.dialect,
                    "" if entry.backend is None else entry.backend,
                    "" if entry.extension is None else entry.extension,
                )
            )
        )
    return hashlib.sha256(("\n".join(rows) + "\n").encode("utf-8")).hexdigest()


def _assert_evidence_shape(fact: CapabilityFact, expected_hash: str) -> None:
    assert _evidence_hash(fact) == expected_hash
    assert len(fact.evidence) == len(set(fact.evidence))
    assert all((REPO_ROOT / entry.source_path).is_file() for entry in fact.evidence)
    order = {source: index for index, source in enumerate(CapabilityEvidenceSource)}
    positions = [order[entry.source] for entry in fact.evidence]
    assert positions == sorted(positions)
    backends = [
        entry
        for entry in fact.evidence
        if entry.source is CapabilityEvidenceSource.BACKEND
    ]
    assert [entry.dialect for entry in backends] in (
        [],
        ["postgresql", "mysql"],
    )
    assert all(entry.extension is None for entry in fact.evidence)


def _prior_compatible_nodes() -> tuple[tuple[str, ...], tuple[int, ...]]:
    files = (SLICE2_TEST_REL, SLICE3_TEST_REL, SLICE4_TEST_REL, SLICE5_TEST_REL)
    excluded = {
        SLICE2_TEST_REL + "::test_gate2_dirty_untracked_and_index_states_are_exact",
        SLICE3_TEST_REL + "::test_gate2_dirty_untracked_and_index_states_are_exact",
        SLICE4_TEST_REL + "::test_gate2_dirty_untracked_and_index_states_are_exact",
        SLICE5_TEST_REL
        + "::test_package_version_tags_gate2_dirty_state_and_allowlist_are_exact",
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
    assert capability_contexts.__all__ == ()
    tree = ast.parse(_read(SOURCE_PATH), filename=SOURCE_REL)
    assert not any(
        isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef)) for node in tree.body
    )
    imports = {node.module for node in tree.body if isinstance(node, ast.ImportFrom)}
    assert imports == {
        "__future__",
        "collections.abc",
        "pietto.semantic.capability_facts",
    }
    source = _read(SOURCE_PATH)
    assert "capability_lookup" not in source
    assert "open(" not in source
    assert "getenv" not in source


def test_freezer_and_combined_fact_order_are_exact() -> None:
    stage = _facts("_EXPRESSION_STAGE_FACTS")
    clause = _facts("_CLAUSE_CAPABILITY_FACTS")
    combined = _facts("_CAPABILITY_CONTEXT_FACTS")
    assert combined == stage + clause
    freezer = cast(Any, getattr(capability_contexts, "_freeze_contexts"))
    with pytest.raises(ValueError, match="duplicate"):
        freezer((stage[0], stage[0]))
    distinct = replace(stage[0], support=CapabilitySupport.EXPLICITLY_UNSUPPORTED)
    assert freezer((stage[0], distinct)) == (stage[0], distinct)


def test_fact_family_ownership_and_aggregate_window_separation_are_exact() -> None:
    combined = _facts("_CAPABILITY_CONTEXT_FACTS")
    assert len(combined) == len(set(combined)) == 18
    assert {fact.key.domain for fact in combined} == {
        CapabilityDomain.EXPRESSION_STAGE,
        CapabilityDomain.CLAUSE,
    }
    assert not any("WINDOW" in fact.key.operands for fact in combined)
    assert not any(fact.key.domain is CapabilityDomain.AGGREGATE for fact in combined)


def test_backend_and_project_evidence_remain_non_authoritative() -> None:
    for fact in _facts("_CAPABILITY_CONTEXT_FACTS"):
        sources = tuple(entry.source for entry in fact.evidence)
        if CapabilityEvidenceSource.BACKEND in sources:
            assert CapabilityEvidenceSource.SEMANTIC_PROCEDURE in sources
            assert sources.index(
                CapabilityEvidenceSource.SEMANTIC_PROCEDURE
            ) < sources.index(CapabilityEvidenceSource.BACKEND)
        if CapabilityEvidenceSource.PROJECT in sources:
            assert sources[0] is CapabilityEvidenceSource.GRAMMAR_AST
            assert sources.index(CapabilityEvidenceSource.PROJECT) > sources.index(
                CapabilityEvidenceSource.SEMANTIC_PROCEDURE
            )


def test_no_existing_consumer_or_public_export_is_added() -> None:
    preservation_path = (
        REPO_ROOT / "src/pietto/_project/module_semantic_fact_preservation.py"
    )
    for path in (REPO_ROOT / "src/pietto").rglob("*.py"):
        if path in {SOURCE_PATH, preservation_path} or "generated" in path.parts:
            continue
        source = _read(path)
        assert "semantic.capability_contexts" not in source
        assert "stage_clause_lookup_inputs" not in source
    preservation_source = _read(preservation_path)
    assert "semantic.capability_contexts" in preservation_source
    assert "stage_clause_lookup_inputs" in preservation_source
    assert "capability_contexts" not in _read(
        REPO_ROOT / "src/pietto/semantic/__init__.py"
    )
    assert "capability_contexts" not in _read(REPO_ROOT / "src/pietto/__init__.py")


def test_prior_private_source_hashes_are_byte_identical() -> None:
    expected = {
        FACTS_REL: FACTS_SHA256,
        LOOKUP_REL: LOOKUP_SHA256,
        INVENTORY_REL: INVENTORY_SHA256,
        SIGNATURE_REL: SIGNATURE_SHA256,
    }
    assert {
        path: hashlib.sha256((REPO_ROOT / path).read_bytes()).hexdigest()
        for path in expected
    } == expected


def test_prior_slice4_and_slice5_fact_counts_are_unchanged() -> None:
    inventory = cast(
        tuple[CapabilityFact, ...],
        getattr(capability_inventory, "_CAPABILITY_FACTS"),
    )
    signatures = cast(
        tuple[CapabilityFact, ...],
        getattr(capability_signatures, "_CAPABILITY_SIGNATURE_FACTS"),
    )
    assert len(inventory) == len(set(inventory)) == 41
    assert len(signatures) == len(set(signatures)) == 39


def test_spec_headings_and_required_phrases_are_exact() -> None:
    spec = _read(SPEC_PATH)
    headings = tuple(
        match.group(1).strip()
        for match in re.finditer(r"^## (?!#)(.+?)\s*$", spec, re.MULTILINE)
    )
    assert headings == SPEC_H2
    for required in (
        "exactly 18 unique \x60CapabilityFact\x60 values",
        "expression_stage.single_file_compiler.v1",
        "clause.single_file_compiler.admissibility.v1",
        "Unknown(NOT_EVIDENCED)",
        "Conflict(CONFLICTING_EVIDENCE)",
        "POST60_ADVANCED_AGGREGATION_GROUPING",
        "PostgreSQL evidence precedes private MySQL evidence.",
        "Phase 52 Slice 7",
        "Phase 53",
        "Package version remains \x600.1.0\x60.",
        "Phase 52 remains active and incomplete",
        "Add Phase 52 private expression stage and clause facts",
    ):
        assert required in spec


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
        108,
        36,
        33,
    )
    assert len(project_paths) == 33
    assert _digest(project_paths) == PROJECT_PRIVATE_DIGEST

    tracked = tuple(_git_output(["ls-files"]).splitlines())
    untracked = tuple(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    )
    readable = tuple(
        sorted(path for path in {*tracked, *untracked} if (REPO_ROOT / path).is_file())
    )
    for digest, expected_readers in (
        (_digest(compiler_paths), COMPILER_READERS),
        (_digest(semantic_paths), SEMANTIC_READERS),
        (_digest(phase15_paths), PHASE15_READERS),
    ):
        actual = tuple(
            sorted(
                path
                for path in readable
                if path != SELF_REL
                and digest.encode("ascii") in (REPO_ROOT / path).read_bytes()
            )
        )
        assert actual == tuple(sorted(expected_readers))

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
    tracked_name_status = tuple(_git_output(["diff", "--name-status"]).splitlines())
    untracked_paths = set(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    ) - {""}
    dirty_paths = _dirty_paths()
    slice13_modified = _slice13_paths("MODIFIED_PATHS")
    slice13_added = _slice13_paths("ADDED_PATHS")
    slice13_allowlist = slice13_modified | slice13_added

    assert _git_output(["tag", "--list"]) == ""
    assert _git_output(["diff", "--cached", "--name-status"]) == ""
    assert dirty_paths == tracked_paths | untracked_paths
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
        REPAIR_ALLOWLIST_PATHS,
        PR_REPAIR_ALLOWLIST_PATHS,
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
        assert tracked_name_status == ()
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
        assert tracked_name_status == tuple(
            f"M\t{path}" for path in sorted(slice13_modified)
        )
        assert untracked_paths == slice13_added
        assert head == main == origin_main
        assert head in (
            "4ff3c131fba54d83b56f3c50e14f7c2337c1eb52",
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
    elif dirty_paths == SLICE9_ALLOWLIST_PATHS:
        assert branch == "main"
        assert tracked_paths == SLICE9_MODIFIED_PATHS
        assert tracked_name_status == tuple(
            f"M\t{path}" for path in sorted(SLICE9_MODIFIED_PATHS)
        )
        assert untracked_paths == SLICE9_ADDED_PATHS
        assert head == main == origin_main == SLICE9_BASE_HEAD_SHA
    elif dirty_paths == SLICE8_ALLOWLIST_PATHS:
        assert branch == "main"
        assert tracked_paths == SLICE8_MODIFIED_PATHS
        assert tracked_name_status == tuple(
            f"M\t{path}" for path in sorted(SLICE8_MODIFIED_PATHS)
        )
        assert untracked_paths == SLICE8_ADDED_PATHS
        assert head == main == origin_main == SLICE8_GATE2_BASE_HEAD_SHA
    elif dirty_paths == ALLOWLIST_PATHS:
        assert branch == "main"
        assert tracked_paths == set(MODIFIED_READER_PATHS)
        assert len(tracked_name_status) == len(MODIFIED_READER_PATHS)
        assert all(entry.startswith("M\t") for entry in tracked_name_status)
        assert {entry.removeprefix("M\t") for entry in tracked_name_status} == set(
            MODIFIED_READER_PATHS
        )
        assert untracked_paths == ADDED_PATHS
        assert origin_main is not None
        assert head == main == origin_main == SLICE6_GATE2_HEAD_SHA
    elif dirty_paths == REPAIR_ALLOWLIST_PATHS:
        assert branch == "main"
        assert dirty_paths == REPAIR_ALLOWLIST_PATHS
        assert tracked_paths == {SELF_REL}
        assert tracked_name_status == (f"M\t{SELF_REL}",)
        assert untracked_paths == set()
        assert origin_main is not None
        assert head == main == origin_main == CI_REPAIR_BASE_HEAD_SHA
    else:
        assert dirty_paths == PR_REPAIR_ALLOWLIST_PATHS
        assert branch == PR_REPAIR_GATE2_BRANCH
        assert tracked_paths == PR_REPAIR_ALLOWLIST_PATHS
        assert len(tracked_name_status) == len(PR_REPAIR_ALLOWLIST_PATHS)
        assert all(entry.startswith("M\t") for entry in tracked_name_status)
        assert {entry.removeprefix("M\t") for entry in tracked_name_status} == (
            PR_REPAIR_ALLOWLIST_PATHS
        )
        assert untracked_paths == set()
        assert origin_main == main == PR_REPAIR_GATE2_MAIN_SHA
        assert origin_pr_head == head == PR_REPAIR_GATE2_HEAD_SHA

    assert len(MODIFIED_READER_PATHS) == len(set(MODIFIED_READER_PATHS)) == 40
    assert len(ALLOWLIST_PATHS) == 43
    assert sum(path.endswith(".py") for path in ALLOWLIST_PATHS) == 42
    assert sum(path.endswith(".md") for path in ALLOWLIST_PATHS) == 1
    assert REPAIR_ALLOWLIST_PATHS == {SELF_REL}
    assert len(PR_REPAIR_ALLOWLIST_PATHS) == 6
    assert len(SLICE8_ALLOWLIST_PATHS) == 6
    assert sum(path.endswith(".py") for path in SLICE8_ALLOWLIST_PATHS) == 5
    assert sum(path.endswith(".md") for path in SLICE8_ALLOWLIST_PATHS) == 1
    assert len(SLICE9_ALLOWLIST_PATHS) == 9
    assert len(SLICE9_MODIFIED_PATHS) == 7
    assert len(SLICE9_ADDED_PATHS) == 2


def test_static_test_inventory_and_tier1_selection_are_exact() -> None:
    function_count, item_count, parametrized = _pytest_shape(SELF_PATH)
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
        "test_expression_stage_evidence_order_and_paths_are_exact",
        "test_expression_stage_lookup_found_is_exact",
        "test_expression_stage_complete_wrong_claim_is_absent",
        "test_expression_stage_incomplete_question_is_unknown",
        "test_supported_clause_fact_is_exact",
        "test_unsupported_clause_fact_is_exact",
        "test_clause_evidence_order_and_paths_are_exact",
    ]
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
    assert (len(test_files), top_level_functions) == (465, 5489)

    compatible, per_file_items = _prior_compatible_nodes()
    assert (len(compatible), per_file_items) == (96, (24, 33, 63, 63))
    compatible_payload = "".join(node + "\n" for node in compatible).encode("utf-8")
    direct_payload = "".join(node + "\n" for node in DIRECT_TIER1_NODES).encode("utf-8")
    operands = (SELF_REL, *compatible, *DIRECT_TIER1_NODES)
    operand_payload = "".join(node + "\n" for node in operands).encode("utf-8")
    assert (
        len(compatible_payload),
        hashlib.sha256(compatible_payload).hexdigest(),
    ) == (
        11942,
        COMPATIBLE_SELECTOR_SHA256,
    )
    assert len(DIRECT_TIER1_NODES) == len(set(DIRECT_TIER1_NODES)) == 44
    assert (len(direct_payload), hashlib.sha256(direct_payload).hexdigest()) == (
        4860,
        DIRECT_SELECTOR_SHA256,
    )
    assert (
        len(operands),
        len(operand_payload),
        hashlib.sha256(operand_payload).hexdigest(),
    ) == (
        141,
        16865,
        TIER1_OPERAND_SHA256,
    )
    assert 69 + sum(per_file_items) + 44 == 296
    assert 5949 + 69 == 6018


def test_tier2_manifest_identity_and_classification_are_exact() -> None:
    assert len(TIER2_MANIFEST) == len(set(TIER2_MANIFEST)) == 142
    assert TIER2_MANIFEST == tuple(sorted(TIER2_MANIFEST))
    payload = "".join(line + "\n" for line in TIER2_MANIFEST).encode("utf-8")
    files = {
        line.removeprefix("--deselect=").split("::", maxsplit=1)[0]
        for line in TIER2_MANIFEST
    }
    assert (len(files), len(payload), hashlib.sha256(payload).hexdigest()) == (
        TIER2_MANIFEST_FILES,
        TIER2_MANIFEST_BYTES,
        TIER2_MANIFEST_SHA256,
    )
    required_added = {
        "--deselect="
        + SLICE4_TEST_REL
        + "::test_gate2_dirty_untracked_and_index_states_are_exact",
        "--deselect="
        + SLICE5_TEST_REL
        + "::test_package_version_tags_gate2_dirty_state_and_allowlist_are_exact",
    }
    assert required_added <= set(TIER2_MANIFEST)
    assert not any(SELF_REL in line for line in TIER2_MANIFEST)
    for line in TIER2_MANIFEST:
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
        for decorator in matches[0].decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(
                decorator.func, ast.Attribute
            ):
                assert decorator.func.attr != "parametrize"
    assert 6018 - len(TIER2_MANIFEST) == 5876


def test_slice6_lifecycle_validation_publication_and_release_boundaries_are_exact() -> (
    None
):
    spec = _read(SPEC_PATH)
    for required in (
        "Phase 52 remains active and incomplete",
        "Phase 52 Slice 7",
        "Phase 53",
        "Add Phase 52 private expression stage and clause facts",
        "No staging, commit, push, tag, release, publication, signing, or attestation",
    ):
        assert required in spec
    assert "scripts/validate.py" not in spec
    assert "package version bump" not in spec.lower()


def test_expression_stage_fact_inventory_is_exact() -> None:
    facts = _facts("_EXPRESSION_STAGE_FACTS")
    assert (
        tuple((fact.key.subject, fact.key.operands[0]) for fact in facts)
        == STAGE_EXPECTED
    )
    for fact in facts:
        assert fact.key.domain is CapabilityDomain.EXPRESSION_STAGE
        assert fact.key.operation == "observed_stage"
        assert fact.key.context == "expression"
        assert fact.key.dialect is fact.key.extension is None
        assert fact.support is CapabilitySupport.SUPPORTED
        assert fact.disposition.kind is CapabilityDispositionKind.NONE


@pytest.mark.parametrize(
    ("index", "expected_hash"),
    (
        (0, "38f2798010bbc9f00fadfdcac5a8cd7634f172ab74161282696f218a2393efd0"),
        (1, "8a0cbfa1e1ebd639ccf06c87c351405ada2b2ea86333b90ab6360707c9edb12f"),
        (2, "45f548b1d7116a7b1ff4b892f75dd2bb00f5ced607e3f250c386b1000a1c53d5"),
        (3, "16fa9648acf7d73982b7a1c720be3d8b8b10e8a6ab6c3f897406214f8ed8c253"),
        (4, "3bd671e6ce6ca80026373f5c45d0fd3b05cfeb980efb828990b0da430a88e065"),
        (5, "d9c4eb20148ef88e6e55ef402c5c0ec0f7c7b8ca578e860fef45c783e42b292d"),
        (6, "a87e9b63565dff68e098f12ebdb9ccf8b1be6d015767228aee86721a35438b78"),
    ),
    ids=(
        "ES01",
        "ES02",
        "ES03",
        "ES04",
        "ES05",
        "ES06",
        "ES07",
    ),
)
def test_expression_stage_evidence_order_and_paths_are_exact(
    index: int,
    expected_hash: str,
) -> None:
    _assert_evidence_shape(_facts("_EXPRESSION_STAGE_FACTS")[index], expected_hash)


def test_expression_ast_and_context_coverage_map_is_exact() -> None:
    facts = _facts("_EXPRESSION_STAGE_FACTS")
    assert {fact.key.subject for fact in facts} == {
        subject for subject, _ in STAGE_EXPECTED
    }
    assert {fact.key.operands[0] for fact in facts} == {
        "CONSTANT",
        "ROW",
        "GROUP",
        "UNKNOWN",
    }
    assert not any("WINDOW" in fact.key.operands for fact in facts)
    assert all(fact.key.context == "expression" for fact in facts)


@pytest.mark.parametrize(
    "index",
    (0, 1, 2, 3, 4, 5, 6),
    ids=("ES01", "ES02", "ES03", "ES04", "ES05", "ES06", "ES07"),
)
def test_expression_stage_lookup_found_is_exact(index: int) -> None:
    fact = _facts("_EXPRESSION_STAGE_FACTS")[index]
    result = _lookup(fact.key)
    assert result == Found(fact)


@pytest.mark.parametrize(
    "key",
    (
        CapabilityKey(
            CapabilityDomain.EXPRESSION_STAGE,
            subject="literal_expression",
            operation="observed_stage",
            operands=("ROW",),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.EXPRESSION_STAGE,
            subject="resolved_row_reference",
            operation="observed_stage",
            operands=("CONSTANT",),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.EXPRESSION_STAGE,
            subject="aggregate_dependent_expression",
            operation="observed_stage",
            operands=("ROW",),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.EXPRESSION_STAGE,
            subject="unresolved_reference_expression",
            operation="observed_stage",
            operands=("GROUP",),
            context="expression",
        ),
    ),
    ids=("literal-row", "resolved-constant", "aggregate-row", "unresolved-group"),
)
def test_expression_stage_complete_wrong_claim_is_absent(key: CapabilityKey) -> None:
    assert isinstance(_lookup(key), Absent)


@pytest.mark.parametrize(
    "key",
    (
        CapabilityKey(
            CapabilityDomain.EXPRESSION_STAGE,
            subject="literal_expression",
            operation="observed_stage",
            operands=("WINDOW",),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.EXPRESSION_STAGE,
            subject="future_expression",
            operation="observed_stage",
            operands=("ROW",),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.EXPRESSION_STAGE,
            subject="literal_expression",
            operation="observed_stage",
            operands=("CONSTANT",),
            context="select",
        ),
        CapabilityKey(
            CapabilityDomain.EXPRESSION_STAGE,
            subject="literal_expression",
            operation="observed_stage",
            operands=("CONSTANT",),
            context="expression",
            dialect="postgresql",
        ),
        CapabilityKey(
            CapabilityDomain.EXPRESSION_STAGE,
            subject="literal_expression",
            operation="observed_stage",
            operands=("CONSTANT",),
            context="expression",
            dialect="mysql",
            extension="vendor",
        ),
        CapabilityKey(
            CapabilityDomain.EXPRESSION_STAGE,
            subject="literal_expression",
            operation="observed_stage",
            operands=("CONSTANT", "ROW"),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.EXPRESSION_STAGE,
            subject="literal_expression",
            operation="classify",
            operands=("CONSTANT",),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.CONVERSION,
            subject="literal_expression",
            operation="observed_stage",
            operands=("CONSTANT",),
            context="expression",
        ),
    ),
    ids=(
        "window",
        "future-subject",
        "wrong-context",
        "dialect",
        "extension",
        "malformed-operands",
        "wrong-operation",
        "other-domain",
    ),
)
def test_expression_stage_incomplete_question_is_unknown(key: CapabilityKey) -> None:
    result = _lookup(key)
    assert result == Unknown(CapabilityReasonCode.NOT_EVIDENCED)


def test_stage_type_nullability_and_three_valued_truth_are_orthogonal() -> None:
    literal = _facts("_EXPRESSION_STAGE_FACTS")[0]
    unresolved = _facts("_EXPRESSION_STAGE_FACTS")[-1]
    assert literal.key.operands == ("CONSTANT",)
    assert any(
        entry.reason is CapabilityReasonCode.NULL_LITERAL_NO_CONCRETE_TYPE
        for entry in literal.evidence
    )
    assert unresolved.key.operands == ("UNKNOWN",)
    assert isinstance(_lookup(unresolved.key), Found)
    assert any(
        entry.reason is CapabilityReasonCode.UNRESOLVED_EXPRESSION
        for entry in unresolved.evidence
    )


def test_expression_stage_injected_conflict_preserves_order() -> None:
    fact = _facts("_EXPRESSION_STAGE_FACTS")[0]
    distinct = replace(fact, support=CapabilitySupport.EXPLICITLY_UNSUPPORTED)
    facts, complete, reason = cast(Any, capability_contexts.stage_clause_lookup_inputs)(
        fact.key
    )
    result = lookup_capability(
        fact.key,
        (*facts, distinct),
        domain_complete=complete,
        unknown_reason=reason,
    )
    assert result == Conflict(
        CapabilityReasonCode.CONFLICTING_EVIDENCE,
        (fact, distinct),
    )


def test_clause_fact_inventory_order_and_combined_tuple_are_exact() -> None:
    facts = _facts("_CLAUSE_CAPABILITY_FACTS")
    observed = tuple(
        (
            fact.key.subject,
            fact.key.operands,
            fact.key.context,
            fact.support,
            fact.disposition.kind,
            fact.disposition.owner,
            fact.disposition.reason,
        )
        for fact in facts
    )
    assert observed == CLAUSE_EXPECTED
    assert (
        _facts("_CAPABILITY_CONTEXT_FACTS") == _facts("_EXPRESSION_STAGE_FACTS") + facts
    )


@pytest.mark.parametrize(
    "index",
    (0, 1, 2, 3, 4),
    ids=("C01", "C02", "C03", "C04", "C05"),
)
def test_supported_clause_fact_is_exact(index: int) -> None:
    fact = _facts("_CLAUSE_CAPABILITY_FACTS")[index]
    assert fact.support is CapabilitySupport.SUPPORTED
    assert fact.disposition.kind is CapabilityDispositionKind.NONE
    assert _lookup(fact.key) == Found(fact)


@pytest.mark.parametrize(
    "index",
    (5, 6, 7, 8, 9, 10),
    ids=("C06", "C07", "C08", "C09", "C10", "C11"),
)
def test_unsupported_clause_fact_is_exact(index: int) -> None:
    fact = _facts("_CLAUSE_CAPABILITY_FACTS")[index]
    assert fact.support is CapabilitySupport.EXPLICITLY_UNSUPPORTED
    if index in {6, 7, 10}:
        assert fact.disposition.kind is CapabilityDispositionKind.DEFERRED
        assert fact.disposition.owner == "POST60_ADVANCED_AGGREGATION_GROUPING"
    else:
        assert fact.disposition.kind is CapabilityDispositionKind.NONE
    assert _lookup(fact.key) == Found(fact)


@pytest.mark.parametrize(
    ("index", "expected_hash"),
    (
        (0, "0dabfe42b6dcd93075114989e366b6853f7644655179b6a8226df9d8b96465a5"),
        (1, "1f8a8c6b58b5e314e349a39ca02525c501b6209906b1c9f768a6e635d2c0d6c0"),
        (2, "119d9fc3c2c7be7ace6f0174a822c96faa8faf1861c731a72948ee7e4e4de2b1"),
        (3, "f3a75561fee0ff7c35c33be54b09ac18d1de17f0b9d96e0d4e13b5129ea13e09"),
        (4, "35f95f8baa2e786b2c0c9c71644ca73c720434839ae180f1bf3788e72f52e4e2"),
        (5, "1249ea5ca0e48b280911c81a40d43955f825810c5593fcd45095e6c95d737582"),
        (6, "b3e2323ff10e4a28338df89a1a22472031b155783a858f4c5c62356b049d205c"),
        (7, "0820ff50a6cd582812677c6774646a428334379949a72953b9a720e06ae48257"),
        (8, "f532aa81e9eeb90616d727b065a5575840fd347ebf8c103dd5b0cd0437807643"),
        (9, "df976089e6a8adac23c375534f21fcb3c0e572f998066e5f51a1e114432c9d92"),
        (10, "c267eda6ad529ef684325974804662ef9c521a9a61c5f69d3cb703dd6ae89622"),
    ),
    ids=(
        "C01",
        "C02",
        "C03",
        "C04",
        "C05",
        "C06",
        "C07",
        "C08",
        "C09",
        "C10",
        "C11",
    ),
)
def test_clause_evidence_order_and_paths_are_exact(
    index: int,
    expected_hash: str,
) -> None:
    _assert_evidence_shape(_facts("_CLAUSE_CAPABILITY_FACTS")[index], expected_hash)


def test_clause_completeness_and_absence_are_exact() -> None:
    absent_key = CapabilityKey(
        CapabilityDomain.CLAUSE,
        subject="where",
        operation="admit",
        operands=(
            "ROW",
            "Bool",
            "current_nonaggregate_expression",
            "input_fields_and_row_lets",
            "select_output_aliases_forbidden",
        ),
        context="pre_group_filter",
    )
    assert isinstance(_lookup(absent_key), Absent)
    malformed = replace(absent_key, operands=("ROW",))
    assert _lookup(malformed) == Unknown(CapabilityReasonCode.NOT_EVIDENCED)


def test_clause_lookup_four_results_are_exact() -> None:
    fact = _facts("_CLAUSE_CAPABILITY_FACTS")[0]
    assert _lookup(fact.key) == Found(fact)
    absent_key = replace(
        fact.key,
        operands=(
            "ROW",
            "Bool",
            "current_nonaggregate_expression",
            "input_fields_and_row_lets",
            "select_output_aliases_forbidden",
        ),
    )
    assert isinstance(_lookup(absent_key), Absent)
    unknown_key = replace(
        fact.key,
        operands=(
            "WINDOW",
            "Bool_when_known",
            "current_nonaggregate_expression",
            "input_fields_and_row_lets",
            "select_output_aliases_forbidden",
        ),
    )
    assert _lookup(unknown_key) == Unknown(CapabilityReasonCode.NOT_EVIDENCED)
    distinct = replace(fact, support=CapabilitySupport.EXPLICITLY_UNSUPPORTED)
    facts, complete, reason = cast(Any, capability_contexts.stage_clause_lookup_inputs)(
        fact.key
    )
    conflict = lookup_capability(
        fact.key,
        (*facts, distinct),
        domain_complete=complete,
        unknown_reason=reason,
    )
    assert conflict == Conflict(
        CapabilityReasonCode.CONFLICTING_EVIDENCE,
        (fact, distinct),
    )


def test_clause_omissions_and_tensions_remain_unknown() -> None:
    keys = (
        CapabilityKey(
            CapabilityDomain.CLAUSE,
            subject="select",
            operation="admit",
            context="output",
        ),
        CapabilityKey(
            CapabilityDomain.CLAUSE, subject="let", operation="admit", context="binding"
        ),
        CapabilityKey(
            CapabilityDomain.CLAUSE,
            subject="limit",
            operation="admit",
            context="static",
        ),
        CapabilityKey(
            CapabilityDomain.CLAUSE,
            subject="where",
            operation="admit",
            operands=(
                "WINDOW",
                "Bool_when_known",
                "current_nonaggregate_expression",
                "input_fields_and_row_lets",
                "select_output_aliases_forbidden",
            ),
            context="pre_group_filter",
        ),
        CapabilityKey(
            CapabilityDomain.CLAUSE,
            subject="where",
            operation="admit",
            operands=(
                "ROW",
                "Bool_when_known",
                "current_nonaggregate_expression",
                "input_fields_and_row_lets",
                "select_output_aliases_forbidden",
            ),
            context="pre_group_filter",
            dialect="postgresql",
        ),
        CapabilityKey(
            CapabilityDomain.CLAUSE,
            subject="where",
            operation="admit",
            operands=("ROW",),
            context="pre_group_filter",
        ),
        CapabilityKey(
            CapabilityDomain.CLAUSE,
            subject="where",
            operation="admit",
            operands=(
                "ROW",
                "Bool_when_known",
                "future_shape",
                "input_fields_and_row_lets",
                "select_output_aliases_forbidden",
            ),
            context="pre_group_filter",
        ),
        CapabilityKey(
            CapabilityDomain.CLAUSE,
            subject="where",
            operation="admit",
            operands=(
                "ROW",
                "Bool_when_known",
                "current_nonaggregate_expression",
                "input_fields_and_row_lets",
                "select_output_aliases_forbidden",
            ),
            context="project_pre_group_filter",
        ),
    )
    assert all(
        _lookup(key) == Unknown(CapabilityReasonCode.NOT_EVIDENCED) for key in keys
    )


_SLICE10_READER_MIGRATION_PATHS = (
    "docs/spec/phase53-partition-binding-multi-key-visibility-diagnostics-contract-v1.md",
    "src/pietto/semantic/window_partition_analysis.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
)
# Phase 53 Slice 13 reader migration.
