from __future__ import annotations

import ast
import hashlib
import re
import subprocess
import tomllib
from collections import Counter
from pathlib import Path

from _phase54_active_gate2_manifest import (
    PHASE54_SLICE12_PR_CI_REPAIR_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR3_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR10_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR11_MODIFIED_PATHS,
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
    phase54_slice12_pr_ci_repair_is_active,
    phase54_slice12_product_repair3_is_active,
    phase54_slice12_product_repair10_is_active,
    phase54_slice12_product_repair11_is_active,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_REL = "docs/plan/phase-54-local-import-module-export-foundation.md"
SCOPE_REL = (
    "docs/spec/phase54-slice1-scope-authority-expansion-readiness-and-route-lock-v1.md"
)
GOVERNANCE_REL = (
    "docs/spec/pietto-phase-start-expansion-pull-forward-readiness-governance-v1.md"
)
ROADMAP_V1_REL = "docs/spec/pietto-active-roadmap-phase53-70-v1.md"
ROADMAP_V2_REL = "docs/spec/pietto-active-roadmap-phase53-70-v2.md"
SLICE2_SPEC_REL = (
    "docs/spec/phase54-slice2-schema-v2-explicit-module-activation-and-"
    "immutable-carrier-v1.md"
)
SLICE2_TEST_REL = "tests/test_phase54_schema_v2_explicit_module_carrier.py"
SLICE3_SPEC_REL = (
    "docs/spec/phase54-slice3-module-identity-selected-input-index-trusted-"
    "local-loader-path-symlink-boundary-v1.md"
)
SLICE3_TEST_REL = (
    "tests/test_phase54_module_identity_selected_input_index_trusted_local_loader.py"
)
SLICE4_SPEC_REL = (
    "docs/spec/phase54-slice4-import-export-contextual-grammar-generated-"
    "parser-and-immutable-ast-v1.md"
)
SLICE4_TEST_REL = "tests/test_phase54_import_export_contextual_grammar_ast.py"
SLICE5_SPEC_REL = (
    "docs/spec/phase54-slice5-module-qualified-nominal-declaration-identity-"
    "and-per-module-catalogs-v1.md"
)
SLICE5_TEST_REL = "tests/test_phase54_module_qualified_nominal_declaration_catalogs.py"
SLICE6_SPEC_REL = (
    "docs/spec/phase54-slice6-local-export-eligibility-visibility-explicit-"
    "named-reexport-and-facade-semantics-v1.md"
)
SLICE6_TEST_REL = "tests/test_phase54_local_export_visibility_module_facades.py"
SELF_REL = "tests/test_phase54_local_import_module_export_foundation_scope_lock.py"

PLAN_TITLE = "Phase 54 — Local Import / Module / Export Foundation"
SCOPE_TITLE = (
    "Phase 54 Slice 1 Scope, Authority, Phase-start Expansion Audit, Decisions, "
    "Activation, And Route Lock v1"
)
GOVERNANCE_TITLE = (
    "Pietto Phase-start Expansion, Pull-forward, And Readiness Governance v1"
)
ROADMAP_V2_TITLE = "Pietto Active Roadmap Phase 53–70 v2"
SLICE2_SPEC_TITLE = (
    "Phase 54 Slice 2 Schema-v2 Explicit-module Activation And Immutable "
    "Project / Module Carrier v1"
)
SLICE3_SPEC_TITLE = (
    "Phase 54 Slice 3 — Module Identity, Selected-input Index, Trusted Local "
    "Loader, And Path / Symlink Boundary v1"
)
SLICE4_SPEC_TITLE = (
    "Phase 54 Slice 4 — Import / Export Contextual Grammar, Generated Parser, "
    "And Immutable AST v1"
)
SLICE5_SPEC_TITLE = (
    "Phase 54 Slice 5 — Module-qualified Nominal Declaration Identity And "
    "Per-module Catalogs v1"
)
SLICE6_SPEC_TITLE = (
    "Phase 54 Slice 6 — Local Export Eligibility, Visibility, Explicit Named "
    "Re-export, And Facade Semantics v1"
)

SLICE2_EXPECTED_TEST_NAMES = (
    "test_schema_versions_map_to_exact_project_compilation_modes",
    "test_schema_version_validation_and_unknown_keys_remain_fail_closed",
    "test_schema_versions_select_identical_normalized_ordered_inputs",
    "test_logical_module_carrier_is_frozen_slots_hashable_and_enforces_invariants",
    "test_selection_builds_one_zero_based_logical_module_per_input",
    "test_parse_check_rebuilds_modules_with_parsed_input_references",
    "test_parse_and_read_failures_retain_ordered_logical_modules",
    "test_explicit_mode_returns_before_legacy_flat_catalog_collection",
    "test_legacy_mode_still_enters_flat_catalog_and_reports_duplicate_pie_s2001",
    "test_schema_v2_project_text_cli_fails_closed_without_success_output",
    "test_schema_v2_project_json_keeps_exact_envelope_and_fails_exit",
    "test_schema_v1_project_cli_output_remains_exact",
    "test_project_json_and_public_exports_do_not_expose_module_carriers",
    "test_single_file_check_behavior_remains_exact",
    "test_import_export_grammar_ast_and_module_diagnostic_codes_remain_absent",
    "test_slice2_contract_allowlist_and_retained_later_boundaries_are_exact",
)

SLICE3_EXPECTED_TEST_NAMES = (
    "test_module_identity_is_exact_normalized_path_only",
    "test_logical_module_identity_property_preserves_slice2_fields",
    "test_selected_input_index_is_ordered_immutable_and_filesystem_free",
    "test_selected_input_index_rejects_duplicate_logical_and_physical_identities",
    "test_regular_config_pins_root_and_reads_opened_bytes_once",
    "test_invocation_root_symlink_is_accepted_once_and_retarget_fails_closed",
    "test_root_replacement_identity_mismatch_fails_closed",
    "test_config_symlink_and_non_regular_config_are_rejected_exactly",
    "test_config_opened_identity_and_read_mutation_fail_closed",
    "test_regular_selected_source_builds_trusted_snapshot_and_exact_digest",
    "test_inside_root_source_symlink_is_accepted_with_logical_identity",
    "test_outside_root_source_symlink_is_rejected_exactly",
    "test_symlink_directory_traversal_remains_excluded",
    "test_source_symlink_retarget_after_selection_fails_before_parser",
    "test_regular_source_replacement_after_selection_fails_before_parser",
    "test_non_regular_selected_source_is_rejected_exactly",
    "test_physical_duplicate_has_no_selected_index_winner",
    "test_opened_descriptor_identity_mismatch_fails_before_parser",
    "test_source_byte_limit_and_oversize_diagnostic_remain_exact",
    "test_invalid_utf8_and_read_error_order_remain_exact",
    "test_parser_consumes_snapshot_text_without_second_path_open",
    "test_source_digest_changes_only_with_exact_accepted_bytes",
    "test_source_descriptors_close_on_success_and_failure",
    "test_pre_post_read_mutation_is_rejected_when_observed",
    "test_schema_v1_and_schema_v2_retain_trust_facts_and_existing_semantics",
    "test_single_file_public_privacy_scope_and_flat_evidence_contract_remain_exact",
)

SLICE4_EXPECTED_TEST_NAMES = (
    "test_slice4_contract_artifacts_ast_surface_and_test_inventory_are_exact",
    "test_minimal_import_block_preserves_decoded_target_item_and_exact_spans",
    "test_import_block_accepts_exact_six_declaration_kinds_in_source_order",
    "test_import_alias_direction_preserves_exported_and_local_names_and_spans",
    "test_multiple_import_blocks_preserve_module_statement_source_order",
    "test_import_comments_blank_lines_and_string_escape_policy_are_preserved",
    "test_import_target_is_retained_without_path_normalization_or_filesystem_lookup",
    "test_minimal_export_block_preserves_item_and_exact_spans",
    "test_export_block_accepts_exact_six_declaration_kinds_in_source_order",
    "test_multiple_export_blocks_preserve_module_statement_source_order",
    "test_import_export_blocks_interleave_with_definitions_and_relationships_without_reclassification",
    "test_script_without_module_syntax_keeps_empty_module_statements_and_equal_existing_ast",
    "test_module_ast_is_frozen_slots_tuple_backed_value_equal_and_hashable",
    "test_module_ast_contains_no_antlr_nodes_or_semantic_identity_fields",
    "test_import_export_as_remain_contextual_identifiers_across_existing_definition_positions",
    "test_import_export_as_remain_contextual_in_relationship_let_aggregate_and_window_positions",
    "test_existing_parser_ast_corpus_representatives_remain_accepted_and_unchanged",
    "test_import_export_top_level_blocks_do_not_change_semantic_catalog_or_diagnostics",
    "test_import_export_top_level_blocks_do_not_change_ir_or_postgres_mysql_sql",
    "test_import_export_top_level_blocks_do_not_change_public_cli_json_or_metadata_shape",
    "test_schema_v1_preserves_module_ast_without_import_binding_or_catalog_effect",
    "test_schema_v2_retains_module_ast_and_stops_before_legacy_flat_catalog",
    "test_module_diagnostics_remain_private_without_serializer_or_dependency_surfaces",
    "test_invalid_import_forms_fail_with_existing_parser_diagnostics_and_spans",
    "test_invalid_export_forms_fail_with_existing_parser_diagnostics_and_spans",
    "test_import_and_export_require_nonempty_indented_bodies",
    "test_import_and_export_are_rejected_outside_top_level",
    "test_tabs_and_malformed_module_indentation_use_existing_diagnostics",
    "test_generated_inventory_rules_and_contextual_token_order_are_exact",
    "test_reader_allowlist_retained_later_and_publication_topology_contracts_are_exact",
)

SLICE5_EXPECTED_TEST_NAMES = (
    "test_nominal_declaration_identity_is_exact_frozen_slotted_four_component_value",
    "test_nominal_declaration_identity_preserves_exact_module_path_case_suffix_and_unicode",
    "test_each_nominal_identity_component_independently_controls_equality_and_hash",
    "test_occurrence_span_ast_object_positions_and_trust_payload_do_not_change_nominal_identity",
    "test_nominal_identity_and_occurrence_constructors_reject_wrong_exact_types_and_mismatches",
    "test_all_eight_definition_classes_map_to_exact_namespace_kind_and_declared_name",
    "test_relationships_imports_and_exports_are_excluded_from_local_declaration_occurrences",
    "test_occurrences_retain_exact_module_and_declaration_positions_and_definition_values",
    "test_module_catalog_is_frozen_slotted_tuple_backed_and_retains_exact_owner",
    "test_module_catalog_rejects_wrong_mode_unparsed_owner_and_incomplete_or_misordered_occurrences",
    "test_project_catalog_set_builds_one_catalog_per_module_in_exact_selected_input_order",
    "test_project_catalog_set_rejects_duplicate_module_paths_and_noncontiguous_or_missing_modules",
    "test_empty_catalog_set_and_lookup_results_are_exact_immutable_empty_tuples",
    "test_project_module_path_lookup_returns_exact_zero_or_one_element_tuple",
    "test_exact_nominal_identity_lookup_returns_all_source_ordered_occurrences",
    "test_exact_namespace_declared_name_lookup_returns_zero_one_or_multiple_occurrences",
    "test_catalog_construction_never_reopens_sources_or_consults_import_targets_or_registries",
    "test_same_declaration_spelling_in_different_modules_has_distinct_nominal_identities",
    "test_same_spelling_in_different_namespaces_has_distinct_identity_and_lookup_buckets",
    "test_same_namespace_and_name_across_different_kinds_preserves_one_ambiguous_bucket",
    "test_repeated_exact_nominal_identity_preserves_every_occurrence_in_source_order",
    "test_declaration_order_changes_only_occurrence_order_and_never_creates_precedence_or_winner",
    "test_schema_v2_catalog_collisions_emit_one_pie_s2001_and_no_pie_s2701_through_pie_s2707",
    "test_schema_v2_success_retains_catalogs_privately_without_changing_model_diagnostics_ok_or_defaults",
    "test_schema_v2_parse_or_read_failure_builds_no_complete_or_partial_catalog_set",
    "test_current_zero_selected_input_project_remains_project_glob_failure_without_catalogs",
    "test_schema_v2_text_and_json_cli_remain_fail_closed_with_exact_envelope_and_no_catalog_fields",
    "test_schema_v1_legacy_flat_catalog_duplicate_diagnostics_and_cli_json_remain_exact",
    "test_import_export_blocks_do_not_add_remove_rename_reorder_or_link_local_declarations",
    "test_private_public_dependency_version_and_retained_later_surfaces_remain_exact",
)

EXPECTED_TEST_NAMES = (
    "test_slice1_artifact_titles_heading_order_and_lifecycle_are_exact",
    "test_authority_hierarchy_grounding_and_historical_predecessors_are_exact",
    "test_product_decisions_p1_through_p5_are_exact",
    "test_architecture_decisions_a1_through_a5_are_exact",
    "test_phase_start_governance_vocabulary_ledgers_scoring_and_template_are_exact",
    "test_sixteen_slice_titles_prerequisites_and_parallelism_are_exact",
    "test_phase55_70_named_reexport_release_and_rust_ownership_is_reconciled",
    "test_current_production_readiness_and_retained_later_ledgers_are_exact",
    "test_grammar_generated_ast_parser_and_public_exports_are_byte_locked",
    "test_legacy_config_discovery_selection_loader_and_project_json_are_byte_locked",
    "test_flat_catalog_collect_before_resolve_semantic_and_project_fact_surfaces_are_locked",
    "test_private_module_export_surfaces_are_implemented_without_graph_or_public_diagnostics",
    "test_public_json_artifact_cli_sql_dependency_workflow_version_and_release_surfaces_are_locked",
    "test_gate_allowlist_reader_evidence_publication_stop_and_next_state_contracts_are_exact",
)

PHASE54_ROUTE = (
    "Scope, Authority, Phase-start Expansion Audit, Decisions, Activation, And Route Lock",
    "Schema-v2 Explicit-module Activation And Immutable Project / Module Carrier",
    "Module Identity, Selected-input Index, Trusted Local Loader, And Path / Symlink Boundary",
    "Import / Export Contextual Grammar, Generated Parser, And Immutable AST",
    "Module-qualified Nominal Declaration Identity And Per-module Catalogs",
    "Local Export Eligibility, Visibility, Explicit Named Re-export, And Facade Semantics",
    "Named Imports, Aliases, Binding Environments, And Collision Rules",
    "Module Graph, Cycles, Diagnostics, And Deterministic Ordering",
    "Cross-module Type Alias, Enum, Shape, And Source Resolution",
    "Cross-module Table / Query / Relation Resolution, Row Facts, And Legacy Compatibility",
    "Module Attribution, Dependency, Origin, Provenance, And Lineage",
    "Generic-signature, Nullability, Aggregate, Grouped, Window, Result-role, And Capability-fact Preservation",
    "Package-neutral Identity Layering, Owner / Asset-compatible Carriers, Source Digest, And Loader Readiness",
    "Private Module Inspection And Canonical Serialization",
    "Rust-ready Pure Boundaries, Differential Vectors, And End-to-end Hardening",
    "Completion Audit, Status Lock, And Phase 55 Handoff",
)
PHASE54_PREREQUISITES = (
    ("Phase 53 completion",),
    (1,),
    (2,),
    (1,),
    (2, 4),
    (5,),
    (6,),
    (7,),
    (8,),
    (3, 8, 9),
    (10,),
    (10,),
    (3, 11, 12),
    (13,),
    tuple(range(8, 15)),
    tuple(range(1, 16)),
)

PHASE_OWNERS = (
    (55, "Semantic Package Asset Schema And Deterministic Local Loading"),
    (56, "Capability Profile Static Schema And Declared Checking"),
    (57, "PostgreSQL Extension Signature Catalog Foundation"),
    (58, "Public Explain / Portability / Package Inspection Artifact v1"),
    (59, "Local Package Graph, Attribution, Provenance, And Lineage"),
    (
        60,
        "Advanced Window Frames And Phase 51–60 Ecosystem / Release Readiness Checkpoint",
    ),
    (61, "Project IR And Semantic Composition Foundation"),
    (62, "Relationship, JOIN, Grain, And Fanout-safe Semantics"),
    (63, "Multi-relation SQL Artifacts, Project Emit-SQL, And QUALIFY Lowering"),
    (
        64,
        "Advanced Generic Types, Coercion, Temporal, Decimal, And Native Mapping",
    ),
    (65, "Advanced Aggregation And Grouping"),
    (66, "Advanced Module And Semantic-package Assets"),
    (
        67,
        "Remote Package Manager, Registry, Fetch, Install, Cache, And Trust Boundary",
    ),
    (
        68,
        "Dependency Ranges, Version Solver, Canonical Lockfile, And First Rust Kernel",
    ),
    (
        69,
        "Extension-specific Lowering And Additional Dialect Backend Foundation",
    ),
    (
        70,
        "Public Schema / Lineage / Attribution Expansion, Ecosystem Completion Audit, Rust Migration Decision, And v0.2 Release Readiness",
    ),
)

CLASSIFICATIONS = (
    "IMPLEMENT_NOW",
    "PRIVATE_READINESS_NOW",
    "CONTRACT_ONLY_NOW",
    "DEFER_BY_NECESSITY",
    "OUT_OF_SCOPE",
)
FREEZE_LEDGERS = ("CURRENT_PRODUCTION", "CURRENT_READINESS", "RETAINED_LATER")

ADDED_PATHS = {
    "docs/spec/phase54-slice5-module-qualified-nominal-declaration-identity-and-per-module-catalogs-v1.md",
    "src/pietto/_project/module_catalog.py",
    "tests/test_phase54_module_qualified_nominal_declaration_catalogs.py",
}
NON_READER_MODIFIED_PATHS = {
    "README.md",
    "docs/plan/phase-54-local-import-module-export-foundation.md",
    "docs/spec/pietto-v0.9.md",
    "src/pietto/_project/model.py",
}
MECHANICAL_READER_PATHS = {
    "tests/test_maintenance_phase2_agent_workflow_and_roadmap.py",
    "tests/test_maintenance_phase2_code_audit_security_review.py",
    "tests/test_maintenance_phase2_completion_audit.py",
    "tests/test_maintenance_phase2_external_skills_evaluation.py",
    "tests/test_maintenance_phase3_ci_parallelization.py",
    "tests/test_maintenance_phase3_completion_audit.py",
    "tests/test_maintenance_phase3_developer_workflow.py",
    "tests/test_maintenance_phase3_non_pytest_validation_optimization.py",
    "tests/test_maintenance_phase3_parallel_safety.py",
    "tests/test_maintenance_phase3_validation_acceleration_scope_lock.py",
    "tests/test_maintenance_phase4_benchmark_evidence_decision.py",
    "tests/test_maintenance_phase4_completion_audit.py",
    "tests/test_maintenance_phase4_worker_strategy_benchmark_protocol.py",
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_packaging_smoke.py",
    "tests/test_phase11_validation_entrypoint.py",
    "tests/test_phase12_completion_audit.py",
    "tests/test_phase12_composition_cli_json_goldens.py",
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
    "tests/test_phase35_completion_audit.py",
    "tests/test_phase35_internal_helper_simplification_candidate_decision.py",
    "tests/test_phase35_safe_simplification_candidate_decision.py",
    "tests/test_phase35_validation_delivery_workflow_polish.py",
    "tests/test_phase36_completion_audit.py",
    "tests/test_phase36_public_surface_stability_hardening.py",
    "tests/test_phase36_status_housekeeping.py",
    "tests/test_phase37_aggregate_filter_distinct_modifier_deferral.py",
    "tests/test_phase37_candidate_decision.py",
    "tests/test_phase37_completion_audit.py",
    "tests/test_phase37_count_distinct_expression_widening_boundary.py",
    "tests/test_phase37_count_expression_mvp_decision.py",
    "tests/test_phase37_current_aggregate_matrix.py",
    "tests/test_phase37_decimal_aggregate_expression_boundary.py",
    "tests/test_phase37_grouped_aggregate_interaction_hardening.py",
    "tests/test_phase37_min_max_expression_boundary.py",
    "tests/test_phase37_nested_aggregate_composition_hardening.py",
    "tests/test_phase38_binding_filter_post_aggregate_roadmap.py",
    "tests/test_phase38_boundary_types_capability_contract.py",
    "tests/test_phase38_candidate_decision.py",
    "tests/test_phase38_completion_audit.py",
    "tests/test_phase38_count_family_semantics_contract.py",
    "tests/test_phase38_distinct_collation_ordering_readiness.py",
    "tests/test_phase38_type_capability_matrix_contract.py",
    "tests/test_phase39_candidate_decision.py",
    "tests/test_phase39_completion_audit.py",
    "tests/test_phase39_count_expression_mvp_contract.py",
    "tests/test_phase40_completion_audit.py",
    "tests/test_phase40_let_binding_model_candidate.py",
    "tests/test_phase40_let_binding_syntax_scope_contract.py",
    "tests/test_phase41_decimal_precision_scale_candidate.py",
    "tests/test_phase41_decimal_precision_scale_completion_audit.py",
    "tests/test_phase43_completion_audit.py",
    "tests/test_phase44_completion_audit.py",
    "tests/test_phase44_project_config_schema_contract.py",
    "tests/test_phase45_project_semantic_scope_lock.py",
    "tests/test_phase46_completion_audit.py",
    "tests/test_phase46_project_compatibility_hardening.py",
    "tests/test_phase46_project_json_v2_relation_cycle_diagnostics.py",
    "tests/test_phase46_project_relation_cycle_detection.py",
    "tests/test_phase46_project_relation_cycle_diagnostics.py",
    "tests/test_phase46_project_relation_dependency_edge_collection.py",
    "tests/test_phase46_project_relation_dependency_graph_scaffold.py",
    "tests/test_phase46_project_semantic_continuation_scope_lock.py",
    "tests/test_phase47_completion_audit.py",
    "tests/test_phase47_direct_bare_field_row_schema.py",
    "tests/test_phase47_direct_field_rename_row_schema.py",
    "tests/test_phase47_direct_row_schema_scope_lock.py",
    "tests/test_phase47_downstream_readiness_hardening.py",
    "tests/test_phase47_private_row_schema_scaffold.py",
    "tests/test_phase47_project_json_privacy_hardening.py",
    "tests/test_phase47_qualified_field_row_schema.py",
    "tests/test_phase47_source_row_schema_propagation.py",
    "tests/test_phase47_unknown_direct_field_diagnostics.py",
    "tests/test_phase48_completion_audit_status_lock.py",
    "tests/test_phase48_deterministic_propagation_order_contract.py",
    "tests/test_phase48_downstream_diagnostics_ordering_hardening.py",
    "tests/test_phase48_project_json_private_fact_privacy_readiness.py",
    "tests/test_phase48_propagated_field_provenance_lineage_hardening.py",
    "tests/test_phase48_query_to_query_multi_hop_propagation.py",
    "tests/test_phase48_query_to_query_row_schema_scope_lock.py",
    "tests/test_phase48_schema_availability_state_carrier.py",
    "tests/test_phase48_table_upstream_row_schema_propagation.py",
    "tests/test_phase48_upstream_non_concrete_schema_propagation.py",
    "tests/test_phase49_compatibility_privacy_hash_lock_readiness.py",
    "tests/test_phase49_completion_audit_status_lock.py",
    "tests/test_phase49_computed_alias_origin_provenance_privacy.py",
    "tests/test_phase49_computed_alias_project_row_schema_mvp.py",
    "tests/test_phase49_computed_let_multi_hop_row_lineage.py",
    "tests/test_phase49_let_visibility_order_shadowing_hardening.py",
    "tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py",
    "tests/test_phase49_private_row_level_dependency_graph_scaffold.py",
    "tests/test_phase49_project_let_scope_value_facts.py",
    "tests/test_phase49_project_row_expression_schema_helper_contract.py",
    "tests/test_phase49_project_row_expression_type_nullability_adapter.py",
    "tests/test_phase49_row_level_computed_let_schema_scope_lock.py",
    "tests/test_phase49_selected_let_derived_output_schema.py",
    "tests/test_phase49_unknown_deferred_diagnostic_ordering_hardening.py",
    "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
    "tests/test_phase50_completion_audit_and_status_lock.py",
    "tests/test_phase50_explain_public_metadata_package_integration_boundary.py",
    "tests/test_phase50_import_module_export_readiness.py",
    "tests/test_phase50_multi_dialect_capability_ecosystem_readiness.py",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
    "tests/test_phase50_postgresql_extension_capability_readiness.py",
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    "tests/test_phase50_semantic_package_model_readiness.py",
    "tests/test_phase50_type_system_gap_capability_readiness.py",
    "tests/test_phase50_window_function_readiness.py",
    "tests/test_phase51_aggregate_grouped_downstream_propagation.py",
    "tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py",
    "tests/test_phase51_aggregate_grouped_output_schema_foundation_scope_lock.py",
    "tests/test_phase51_aggregate_grouped_state_duplicate_hardening.py",
    "tests/test_phase51_aggregate_only_project_row_schema.py",
    "tests/test_phase51_clause_dependency_fail_closed.py",
    "tests/test_phase51_completion_audit_and_status_lock.py",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
    "tests/test_phase51_group_key_project_row_schema.py",
    "tests/test_phase51_grouped_aggregate_project_row_schema.py",
    "tests/test_phase51_selected_let_accepted_expression_aggregate.py",
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
    "tests/test_phase54_local_import_module_export_foundation_scope_lock.py",
    "tests/test_phase54_module_identity_selected_input_index_trusted_local_loader.py",
    "tests/test_phase54_schema_v2_explicit_module_carrier.py",
}
MODIFIED_PATHS = {*NON_READER_MODIFIED_PATHS, *MECHANICAL_READER_PATHS}
ALLOWLIST_PATHS = ADDED_PATHS | MODIFIED_PATHS
FORMATTER_PATHS = {
    relative
    for relative in ALLOWLIST_PATHS
    if relative.endswith(".py") and not relative.startswith("src/pietto/generated/")
}

PROTECTED_SHA256 = {
    "grammar/Pietto.g4": "661f00037b4ade8f8b5bef0cb3e070e4379decdd11cd19021d68e960e69d2724",
    "src/pietto/ast_nodes.py": "bbfd121446d62d33c7990b80d17579d3f8b55763ce1b5f93ee17247cbd2ce0c2",
    "src/pietto/ast_builder.py": "918dc9f6d7705376b604e69fb80c45cf4c3673c8909a58537770d114d96252cb",
    "src/pietto/parser_api.py": "aa744c3ee334c8729917ae2aed2ee906874f927d47e99542d5accb8a98aa456b",
    "src/pietto/__init__.py": "669ac67bb23a0c8179995e0e415d76c46210c12311e29cd89d2612b45b0a194d",
    "src/pietto/_project/module_carrier.py": "fa235758cc39ddc6efea004d03bd28ccae4833463c14b9f7664cf013f7b66fd5",
    "src/pietto/_project/path_trust.py": "99923ff2ac195c6400935bb6eb9b7f8212815085a777fa4fd910ad66160dce8a",
    "src/pietto/_project/selected_input_index.py": "9eef9b472e22eb1de0ca920c4264c72e5661d835d938966c872eba0fdd290772",
    "src/pietto/_project/trusted_source.py": "21e6962bfb066be6af2539db1229e4fcc97c651d3e29f818794c46039317d8dc",
    "src/pietto/_project/config.py": "da060cc15428ccc4b29ed992a814d7c5f41cca42dcd200655d2909a9d31a3d1e",
    "src/pietto/_project/source_selection.py": "fb1c531bcdd81696aa0c26b110433a6775cde878aeb4af3373d0d4aaf1f1443e",
    "src/pietto/_project/check.py": "6f2f2805249cc86a8ff3510a03abc702d2a029186cf16b50cabd11dbaf1da9e1",
    "src/pietto/_project/json_v2.py": "74251e684a22de4dcdc7e1822a6843ca89cbdfa7e136a046676d848b57953bd5",
    SLICE2_TEST_REL: "5cc502ca1abd9b3edc3aecd7c292988e99e8059a6d7b70bfe26d522fb2742cc1",
    SLICE3_TEST_REL: "66aabae45c0d902f47a0c099d03f4aeb4e1702aea19c90c14444a9fbf2d4103e",
    SLICE4_TEST_REL: "6083d07b639853d4dc0d53d0e0ad3a4d117b6588cfcf359ce423016e95f7200f",
    ".github/workflows/ci.yml": "4db1c9a49b0af230bae3f088bf84524e210e0afcd6a87250322e5036a69e8d94",
    "pyproject.toml": "36aa8e1d19a8409e56e0163a465b9608a88c1bffe644165ba49db49bf5ec3d01",
    "uv.lock": "a7d9125995e98a8a74d3664ceae7801cc1f4cce74ec323933da67838be199cea",
}


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _sha256(relative: str) -> str:
    return hashlib.sha256((REPO_ROOT / relative).read_bytes()).hexdigest()


def _headings(relative: str, level: int) -> tuple[str, ...]:
    return tuple(
        match.group(1).strip()
        for match in re.finditer(
            rf"^{'#' * level} (?!#)(.+?)\s*$", _read(relative), flags=re.MULTILINE
        )
    )


def _section(relative: str, heading: str) -> str:
    source = _read(relative)
    marker = f"## {heading}\n"
    start = source.index(marker) + len(marker)
    end = source.find("\n## ", start)
    return source[start:] if end < 0 else source[start:end]


def _git_output(args: list[str]) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.rstrip()


def phase54_slice5_gate2_manifest_is_active() -> bool:
    """Compatibility wrapper for historical readers of the active Gate 2."""

    return _phase54_active_gate2_is_active()


def _readable_paths() -> tuple[str, ...]:
    paths = (
        *_git_output(["ls-files"]).splitlines(),
        *_git_output(["ls-files", "--others", "--exclude-standard"]).splitlines(),
    )
    return tuple(path for path in paths if path and (REPO_ROOT / path).is_file())


def _top_level_test_functions(relative: str) -> tuple[str, ...]:
    tree = ast.parse(_read(relative), filename=relative)
    return tuple(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )


def _digest(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(REPO_ROOT).as_posix()):
        digest.update(path.relative_to(REPO_ROOT).as_posix().encode())
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


def _production_text() -> str:
    paths = (
        REPO_ROOT / "grammar/Pietto.g4",
        *(REPO_ROOT / "src/pietto").rglob("*.py"),
    )
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)


def test_slice1_artifact_titles_heading_order_and_lifecycle_are_exact() -> None:
    assert _headings(PLAN_REL, 1) == (PLAN_TITLE,)
    assert _headings(SCOPE_REL, 1) == (SCOPE_TITLE,)
    assert _headings(GOVERNANCE_REL, 1) == (GOVERNANCE_TITLE,)
    assert _headings(ROADMAP_V2_REL, 1) == (ROADMAP_V2_TITLE,)
    assert _headings(SLICE2_SPEC_REL, 1) == (SLICE2_SPEC_TITLE,)
    assert _headings(SLICE3_SPEC_REL, 1) == (SLICE3_SPEC_TITLE,)
    assert _headings(SLICE4_SPEC_REL, 1) == (SLICE4_SPEC_TITLE,)
    assert _headings(SLICE5_SPEC_REL, 1) == (SLICE5_SPEC_TITLE,)
    assert _headings(SLICE6_SPEC_REL, 1) == (SLICE6_SPEC_TITLE,)
    for relative in (PLAN_REL, SCOPE_REL, GOVERNANCE_REL, ROADMAP_V2_REL):
        assert _headings(relative, 2)
    plan_h2 = _headings(PLAN_REL, 2)
    assert plan_h2[:5] == (
        "Status And Slice 15 Lifecycle",
        "Trusted Phase 53 Baseline And Controlling Evidence",
        "Phase Identity, Minimum Production Boundary, And Activation",
        "Current Production, Readiness, And Retained-later Freeze",
        "Phase-start Expansion, Pull-forward, And Readiness Audit",
    )
    assert plan_h2[-15:] == tuple(
        f"Slice {index} — {title}"
        for index, title in enumerate(PHASE54_ROUTE[1:], start=2)
    )
    lifecycle = _section(PLAN_REL, "Status And Slice 15 Lifecycle")
    for phrase in (
        "Phase 53 and Slices 1-16 are `COMPLETED`",
        "Phase 54 is `ACTIVE`",
        "Slices\n1 through 14 plus the unnumbered post-Slice-12 workflow hardening",
        "Slice 16 remains `UNSTARTED`",
        "PHASE54_SLICE15_GATE2_COMPLETED_AWAITING_PUBLICATION",
        "PHASE54_SLICE15_GATE3",
        "Slice 16 does not begin in Slice 15",
    ):
        assert phrase in lifecycle
    tests = _top_level_test_functions(SELF_REL)
    assert tests == EXPECTED_TEST_NAMES
    tree = ast.parse(_read(SELF_REL), filename=SELF_REL)
    test_nodes = tuple(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert len(test_nodes) == 14
    assert all(not node.decorator_list for node in test_nodes)
    slice2_tests = _top_level_test_functions(SLICE2_TEST_REL)
    assert slice2_tests == SLICE2_EXPECTED_TEST_NAMES
    slice2_tree = ast.parse(_read(SLICE2_TEST_REL), filename=SLICE2_TEST_REL)
    slice2_nodes = tuple(
        node
        for node in slice2_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert len(slice2_nodes) == 16
    assert all(not node.decorator_list for node in slice2_nodes)
    slice3_tests = _top_level_test_functions(SLICE3_TEST_REL)
    assert slice3_tests == SLICE3_EXPECTED_TEST_NAMES
    slice3_tree = ast.parse(_read(SLICE3_TEST_REL), filename=SLICE3_TEST_REL)
    slice3_nodes = tuple(
        node
        for node in slice3_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert len(slice3_nodes) == 26
    assert all(not node.decorator_list for node in slice3_nodes)
    slice4_tests = _top_level_test_functions(SLICE4_TEST_REL)
    assert slice4_tests == SLICE4_EXPECTED_TEST_NAMES
    slice4_tree = ast.parse(_read(SLICE4_TEST_REL), filename=SLICE4_TEST_REL)
    slice4_nodes = tuple(
        node
        for node in slice4_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert len(slice4_nodes) == 30
    assert all(not node.decorator_list for node in slice4_nodes)
    slice5_tests = _top_level_test_functions(SLICE5_TEST_REL)
    assert slice5_tests == SLICE5_EXPECTED_TEST_NAMES
    slice5_tree = ast.parse(_read(SLICE5_TEST_REL), filename=SLICE5_TEST_REL)
    slice5_nodes = tuple(
        node
        for node in slice5_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert len(slice5_nodes) == 30
    assert all(not node.decorator_list for node in slice5_nodes)
    slice6_tests = _top_level_test_functions(SLICE6_TEST_REL)
    assert len(slice6_tests) == 30
    slice6_tree = ast.parse(_read(SLICE6_TEST_REL), filename=SLICE6_TEST_REL)
    slice6_nodes = tuple(
        node
        for node in slice6_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert tuple(node.name for node in slice6_nodes) == slice6_tests
    assert all(not node.decorator_list for node in slice6_nodes)


def test_authority_hierarchy_grounding_and_historical_predecessors_are_exact() -> None:
    assert _sha256(ROADMAP_V1_REL) == (
        "67c886a05234d4513d2083a12fc0f95ad550fdd892565a6ef7c52de9631743e3"
    )
    assert _sha256("docs/plan/phase-50-semantic-readiness-consolidation.md") == (
        "4a3cc652461741cd0d4df71112c4d69251ecefc7a222aad94727d2e67d6ae34c"
    )
    assert _sha256("docs/spec/phase50-import-module-export-readiness-v1.md") == (
        "8c3656805db451946d60e341b8ac0ca9181997378d07576133c9c4aeef3e3f77"
    )
    assert _sha256("tests/test_phase50_import_module_export_readiness.py") == (
        "22e55fad318240515fa6df8f56d65a2c21e6c862781ec8ca41b72cac11813c1b"
    )
    scope = _read(SCOPE_REL)
    roadmap = _read(ROADMAP_V2_REL)
    assert "Historical readiness is evidence" in scope
    assert "governance-schema successor" in roadmap
    assert "No predecessor byte is appended, edited, deleted" in roadmap
    assert "Live source and completed-phase evidence" in roadmap
    assert "67c886a05234d4513d2083a12fc0f95ad550fdd892565a6ef7c52de9631743e3" in roadmap
    assert "current-state-" + "and-roadmap-audit.txt" not in _read(SELF_REL)


def test_product_decisions_p1_through_p5_are_exact() -> None:
    assert _headings(SCOPE_REL, 3)[:5] == (
        "P1 — Activation And Module Identity",
        "P2 — Import / Export Syntax",
        "P3 — Visibility, Eligibility, And Explicit Named Re-export",
        "P4 — Collision, Cycles, Ordering, And Diagnostics",
        "P5 — Root, Symlink, Path, TOCTOU, Dedup, And Digest",
    )
    scope = _read(SCOPE_REL)
    for phrase in (
        "Schema version 2 explicitly activates project-wide module mode",
        "one module identified by its exact normalized project-root-relative",
        'import "models/customer.pietto":',
        "shape Customer",
        "query orders as imported_orders",
        "exported_name as local_name",
        "explicit named re-export",
        "every hop is explicit",
        "No local/import/alias/export",
        "one canonical root",
        "opened descriptor matches selection",
        "digests exact opened bytes",
        "immutable selected-input index",
    ):
        assert phrase in scope
    for kind in ("`type`", "`enum`", "`shape`", "`source`", "`table`", "`query`"):
        assert kind in scope
    for forbidden in (
        "dotted module reference",
        "wildcard",
        "side-effect import",
        "brace form",
        "package target",
        "`export from`",
    ):
        assert forbidden in scope


def test_architecture_decisions_a1_through_a5_are_exact() -> None:
    assert _headings(SCOPE_REL, 3)[5:10] == (
        "A1 — Layered Immutable Identities",
        "A2 — Selected-input Index And Trusted Local Loader",
        "A3 — Pure Resolver Procedure And Diagnostic Adapter",
        "A4 — Identity-safe Project-model Facts",
        "A5 — Private Inspection, Canonical Serialization, And Rust-ready Seam",
    )
    scope = _read(SCOPE_REL)
    for phrase in (
        "(module,\nnamespace, declaration_kind, declared_name)",
        "AST object identity",
        "immutable,\nordered exact module index",
        "global/callback registry",
        "filesystem walker",
        "package loader",
        "Parse all modules",
        "structured issues",
        "diagnostics\nseparately",
        "distinct legacy-flat resolver",
        "`_project/module_*.py`",
        "aggregate,",
        "capability facts",
        "canonical private serialization",
        "no Python-object identity",
        "frozen differential vectors",
    ):
        assert phrase in scope


def test_phase_start_governance_vocabulary_ledgers_scoring_and_template_are_exact() -> (
    None
):
    governance = _read(GOVERNANCE_REL)
    scope_ledger = _section(SCOPE_REL, "No-unnecessary-deferral Ledger")
    for value in CLASSIFICATIONS + FREEZE_LEDGERS:
        assert value in governance
    for reason in (
        "remote I/O or registry state",
        "dependency solving, ranges, or lockfile semantics",
        "public artifact or serializer-schema publication",
        "runtime plugins, executable hooks, or ambient callbacks",
        "release, signing, attestation, or supply-chain authority",
        "additional dialect production ownership",
        "unresolved semantics",
        "genuine product boundary",
    ):
        assert reason in governance
    assert "belongs to Phase N” is never sufficient" in governance
    weights = tuple(
        int(value)
        for value in re.findall(
            r"^\| (?:semantic|foreseeable|preservation|slice|dependency|implementation|reader|CI|public).*?\| (\d) \|$",
            _section(GOVERNANCE_REL, "Route Scoring Weights And Hard Gates"),
            flags=re.MULTILINE,
        )
    )
    assert weights == (2, 2, 2, 2, 1, 1, 1, 1, 2)
    assert sum(weight * 5 for weight in weights) == 70
    plan_scores = dict(
        (int(count), int(score))
        for count, score in re.findall(
            r"^\| (1[0-6]) \| (\d+) \|", _read(PLAN_REL), flags=re.MULTILINE
        )
    )
    assert plan_scores == {10: 49, 11: 53, 12: 54, 13: 57, 14: 60, 15: 62, 16: 63}
    ledger_rows = re.findall(
        r"^\| ((?:5[5-9]|6\d|70)[A-E]|RLS) / .*?\| (IMPLEMENT_NOW|PRIVATE_READINESS_NOW|CONTRACT_ONLY_NOW|DEFER_BY_NECESSITY|OUT_OF_SCOPE) \|.*$",
        scope_ledger,
        flags=re.MULTILINE,
    )
    assert len(ledger_rows) == 54
    assert len({row_id for row_id, _ in ledger_rows}) == 54
    assert Counter(value for _, value in ledger_rows) == Counter(
        {
            "IMPLEMENT_NOW": 5,
            "PRIVATE_READINESS_NOW": 7,
            "CONTRACT_ONLY_NOW": 4,
            "DEFER_BY_NECESSITY": 34,
            "OUT_OF_SCOPE": 4,
        }
    )
    defer_lines = tuple(
        line for line in scope_ledger.splitlines() if "| DEFER_BY_NECESSITY |" in line
    )
    assert len(defer_lines) == 34
    assert all("DEFERRED BY NECESSITY —" in line for line in defer_lines)
    for field in (
        "PHASE:",
        "TRUSTED_BASELINE:",
        "CURRENT_PRODUCTION:",
        "CURRENT_READINESS:",
        "RETAINED_LATER:",
        "NO_UNNECESSARY_DEFERRAL_LEDGER:",
        "ROUTE_COUNTS_SCREENED: 8,9,10,11,12,13,14,15,16",
        "RECOMMENDED_EXACT_ROUTE:",
        "MAXIMUM_SAFE_PULL_FORWARD:",
        "STOP_CONDITIONS:",
        "NEXT_GATE:",
    ):
        assert field in governance


def test_sixteen_slice_titles_prerequisites_and_parallelism_are_exact() -> None:
    plan_h2 = _headings(PLAN_REL, 2)
    slice_headings = tuple(
        heading for heading in plan_h2 if re.match(r"^Slice \d+ —", heading)
    )
    assert slice_headings == tuple(
        f"Slice {index} — {title}"
        for index, title in enumerate(PHASE54_ROUTE[1:], start=2)
    )
    scope_route = _section(SCOPE_REL, "Exact Sixteen-slice Route And Prerequisites")
    for index, title in enumerate(PHASE54_ROUTE, start=1):
        assert f"{index}. {title}" in scope_route
    assert PHASE54_PREREQUISITES == (
        ("Phase 53 completion",),
        (1,),
        (2,),
        (1,),
        (2, 4),
        (5,),
        (6,),
        (7,),
        (8,),
        (3, 8, 9),
        (10,),
        (10,),
        (3, 11, 12),
        (13,),
        (8, 9, 10, 11, 12, 13, 14),
        (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15),
    )
    dependency = _section(SCOPE_REL, "Dependency Graph And Parallelism")
    assert "Slice 4 may proceed alongside Slices\n2-3" in dependency
    assert "Slices 11 and 12 may proceed in parallel" in dependency
    assert "Publication and Git operations remain\nsequential" in dependency


def test_phase55_70_named_reexport_release_and_rust_ownership_is_reconciled() -> None:
    roadmap = _read(ROADMAP_V2_REL)
    for phase, title in PHASE_OWNERS:
        assert f"| {phase} | {title} |" in roadmap
    owner = _section(
        ROADMAP_V2_REL, "No-unnecessary-deferral And Retained-owner Reconciliation"
    )
    for phrase in (
        "Basic explicit named re-export is `IMPLEMENT_NOW`",
        "wildcard\nimport/export",
        "source-qualified forms",
        "`export from`",
        "callable/constraint/derive/relationship module assets",
        "package-aware advanced\nfacades",
    ):
        assert phrase in owner
    assert "Phase 68 remains the preferred first production Rust" in roadmap
    release = _section(ROADMAP_V2_REL, "Release Train")
    assert "No phase gate implicitly publishes" in release
    assert "Only Release Gate 3" in release
    assert "This roadmap creates none" in release


def test_current_production_readiness_and_retained_later_ledgers_are_exact() -> None:
    scope = _read(SCOPE_REL)
    production = _section(SCOPE_REL, "Current Production Ledger")
    readiness = _section(SCOPE_REL, "Current Readiness Ledger")
    retained = _section(SCOPE_REL, "Retained Later Ledger")
    assert re.findall(r"\| CP-(\d\d) \|", production) == [
        f"{n:02d}" for n in range(1, 9)
    ]
    assert re.findall(r"\| CR-(\d\d) \|", readiness) == [
        f"{n:02d}" for n in range(1, 7)
    ]
    assert re.findall(r"\| RL-(\d\d) \|", retained) == [
        f"{n:02d}" for n in range(1, 17)
    ]
    assert "Historical readiness is evidence" in scope
    maximum = _section(SCOPE_REL, "Maximum Safe Pull-forward Boundary")
    for value in CLASSIFICATIONS[:3]:
        assert value in maximum
    for prohibited in (
        "final package schemas",
        "public\nartifacts",
        "remote operations",
        "solver/lockfile behavior",
        "production Rust",
        "additional dialects",
        "release/supply-chain behavior",
    ):
        assert prohibited in maximum


def test_grammar_generated_ast_parser_and_public_exports_are_byte_locked() -> None:
    for relative in (
        "grammar/Pietto.g4",
        "src/pietto/ast_nodes.py",
        "src/pietto/ast_builder.py",
        "src/pietto/parser_api.py",
        "src/pietto/__init__.py",
    ):
        assert _sha256(relative) == PROTECTED_SHA256[relative]
    generated = tuple(
        path
        for path in (REPO_ROOT / "src/pietto/generated").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )
    assert len(generated) == 8
    assert _digest(generated) == (
        "9a84d108062bdbd87f5cd1d6e237e66f8bbb39d1d9d7674312eab6eb156cbad1"
    )
    grammar = _read("grammar/Pietto.g4")
    ast_nodes = _read("src/pietto/ast_nodes.py")
    ast_builder = _read("src/pietto/ast_builder.py")
    parser_api = _read("src/pietto/parser_api.py")
    for rule in (
        "moduleStatement",
        "importStatement",
        "importTarget",
        "importBody",
        "importItem",
        "exportStatement",
        "exportBody",
        "exportItem",
        "moduleDeclarationKind",
    ):
        assert re.search(rf"(?m)^{rule}\n\s+:", grammar)
    for class_name in (
        "ModuleDeclarationKind",
        "ImportItem",
        "ImportStatement",
        "ExportItem",
        "ExportStatement",
    ):
        assert f"class {class_name}" in ast_nodes
    assert "module_statements: tuple[ModuleStatement, ...] = ()" in ast_nodes
    assert "def visitImportStatement" in ast_builder
    assert "def visitExportStatement" in ast_builder
    assert "parse_module" not in parser_api


def test_legacy_config_discovery_selection_loader_and_project_json_are_byte_locked() -> (
    None
):
    for relative in (
        "src/pietto/_project/module_carrier.py",
        "src/pietto/_project/path_trust.py",
        "src/pietto/_project/selected_input_index.py",
        "src/pietto/_project/trusted_source.py",
        "src/pietto/_project/config.py",
        "src/pietto/_project/source_selection.py",
        "src/pietto/_project/check.py",
        "src/pietto/_project/json_v2.py",
        SLICE2_TEST_REL,
        SLICE3_TEST_REL,
        SLICE4_TEST_REL,
    ):
        assert _sha256(relative) == PROTECTED_SHA256[relative]
    config = _read("src/pietto/_project/config.py")
    selection = _read("src/pietto/_project/source_selection.py")
    check = _read("src/pietto/_project/check.py")
    model = _read("src/pietto/_project/model.py")
    carrier = _read("src/pietto/_project/module_carrier.py")
    path_trust = _read("src/pietto/_project/path_trust.py")
    index = _read("src/pietto/_project/selected_input_index.py")
    trusted = _read("src/pietto/_project/trusted_source.py")
    assert "_SCHEMA_VERSION = 1" not in config
    assert "_COMPILATION_MODE_BY_SCHEMA_VERSION" in config
    assert "1: ProjectCompilationMode.LEGACY_FLAT" in config
    assert "2: ProjectCompilationMode.EXPLICIT_MODULES" in config
    assert '_TOP_LEVEL_KEYS = frozenset({"schema_version", "sources"})' in config
    assert 'LEGACY_FLAT = "legacy_flat"' in carrier
    assert 'EXPLICIT_MODULES = "explicit_modules"' in carrier
    assert "class ProjectModuleIdentity" in carrier
    assert "class ProjectLogicalModule" in carrier
    assert "_build_project_logical_modules" in selection
    assert "resolved_path.relative_to(pinned_root.canonical_path)" in selection
    assert "ProjectSelectedInputIndex" in selection
    assert "ProjectParsedInput" in check and "script=parse_result.ast" in check
    assert "_load_trusted_source" in check
    assert "class ProjectPinnedRoot" in path_trust
    assert "O_NOFOLLOW" in path_trust and "_fstat_state" in path_trust
    assert "class ProjectSelectedInputIndex" in index
    assert "MappingProxyType" in index
    assert "class ProjectTrustedSourceSnapshot" in trusted
    assert "hashlib.sha256(source_bytes).hexdigest()" in trusted
    assert "class ProjectInput" in model and "class ProjectParsedInput" in model
    assert "compilation_mode: ProjectCompilationMode" in model
    assert "modules: tuple[ProjectLogicalModule, ...]" in model
    assert (
        "parse_result.compilation_mode is not ProjectCompilationMode.LEGACY_FLAT"
        in model
    )
    assert "trusted_source_snapshots" in model
    assert "module_catalogs: ProjectModuleCatalogSet | None = None" in model
    assert "module_exports: ProjectModuleExportSurfaceSet | None = None" in model
    assert "module_bindings: ProjectModuleBindingEnvironmentSet | None = None" in model
    assert "module_graph: ProjectModuleGraph | None = None" in model
    assert "module_diagnostic_facts: ProjectModuleDiagnosticSet | None = None" in model
    assert (
        "module_type_source_resolutions: ProjectTypeSourceResolutionSet | None = None"
        in model
    )
    assert "_build_project_module_catalog_set" in model
    assert "module_catalogs = _build_project_module_catalog_set" in model
    assert "_build_project_module_export_surface_set" in model
    assert "module_exports = _build_project_module_export_surface_set" in model
    assert "_build_project_module_binding_environment_set" in model
    assert "module_bindings = _build_project_module_binding_environment_set" in model
    assert "module_bindings.imported_export_candidates" in model
    assert "_build_project_module_graph" in model
    assert "module_graph = _build_project_module_graph" in model
    assert "_build_project_module_diagnostic_set" in model
    assert "module_diagnostic_facts = _build_project_module_diagnostic_set" in model
    assert "_build_project_type_source_resolution_set" in model
    assert (
        "module_type_source_resolutions = _build_project_type_source_resolution_set"
        in model
    )
    assert "module_exports=module_exports" in model
    assert "module_bindings=module_bindings" in model
    assert "module_graph=module_graph" in model
    assert "module_diagnostic_facts=module_diagnostic_facts" in model
    assert "module_type_source_resolutions=module_type_source_resolutions" in model
    assert "*module_diagnostic_facts.diagnostics" in model
    assert "*module_type_source_resolutions.diagnostics" in model
    assert "module_catalogs=None" not in model
    scope_readiness = _section(SCOPE_REL, "Current Readiness Ledger")
    assert "not a pinned descriptor loader" in scope_readiness
    assert (
        "not bound to later open" in scope_readiness
        or "not a pinned descriptor" in scope_readiness
    )
    slice3 = _read(SLICE3_SPEC_REL)
    assert "one once-pinned root" in slice3
    assert "exact accepted raw bytes" in slice3
    assert "immutable selected-input index" in slice3.lower()


def test_flat_catalog_collect_before_resolve_semantic_and_project_fact_surfaces_are_locked() -> (
    None
):
    compiler = _compiler_paths()
    semantic = tuple((REPO_ROOT / "src/pietto/semantic").glob("*.py"))
    project = tuple((REPO_ROOT / "src/pietto/_project").glob("*.py"))
    assert len(compiler) == 108
    assert _digest(compiler) == (
        "4e8229c91278c48bb90d72e35d853fbf015e43fd14ddb1879f6a922db94b17e4"
    )
    assert _digest(semantic) == (
        "731e17cc85849c7716abeb08abeda03f72e3e21af183a391107adf96ccab6d70"
    )
    assert _digest(project) == (
        "d4d11f9f1a46e994302db8c64da28f3f2af172b1a14e10f98cd2669d7c70483c"
    )
    assert len(project) == 33
    model = _read("src/pietto/_project/model.py")
    for namespace in (
        'TYPE = "type"',
        'RELATION = "relation"',
        'CALLABLE = "callable"',
    ):
        assert namespace in model
    for kind in (
        'TYPE_ALIAS = "type"',
        'ENUM = "enum"',
        'SHAPE = "shape"',
        'SOURCE = "source"',
        'TABLE = "table"',
        'QUERY = "query"',
        'CONSTRAINT = "constraint"',
        'DERIVE = "derive"',
    ):
        assert kind in model
    module_catalog = _read("src/pietto/_project/module_catalog.py")
    for class_name in (
        "ProjectNominalDeclarationIdentity",
        "ProjectDeclarationOccurrence",
        "ProjectModuleCatalog",
        "ProjectModuleCatalogSet",
    ):
        assert f"class {class_name}" in module_catalog
    assert "def _build_project_module_catalog_set" in module_catalog
    assert "parsed_input.script.definitions" in module_catalog
    current = _section(SCOPE_REL, "Current Production Ledger")
    assert "flat project-wide catalog before relation resolution" in current
    assert "row-schema, field-origin, aggregate, grouped, window" in current
    assert "may not flatten" in _section(
        SCOPE_REL, "Legacy-flat And Schema-v2 Activation"
    )


def test_private_module_export_surfaces_are_implemented_without_graph_or_public_diagnostics() -> (
    None
):
    production = _production_text()
    graph_source = _read("src/pietto/_project/module_graph.py")
    resolution_source = _read("src/pietto/_project/module_resolution.py")
    relation_resolution_source = _read(
        "src/pietto/_project/module_relation_resolution.py"
    )
    attribution_source = _read("src/pietto/_project/module_attribution.py")
    preservation_source = _read(
        "src/pietto/_project/module_semantic_fact_preservation.py"
    )
    inspection_source = _read("src/pietto/_project/module_inspection.py")
    non_graph_production = (
        production.replace(graph_source, "")
        .replace(resolution_source, "")
        .replace(relation_resolution_source, "")
        .replace(attribution_source, "")
        .replace(preservation_source, "")
        .replace(inspection_source, "")
    )
    assert all(f"PIE-S270{number}" in graph_source for number in range(1, 8))
    assert not re.search(r"PIE-S270[1-7]", non_graph_production)
    ast_nodes = _read("src/pietto/ast_nodes.py")
    analyzer = _read("src/pietto/semantic/analyzer.py")
    for value in (
        "class ModuleDeclarationKind",
        "class ImportItem",
        "class ImportStatement",
        "class ExportItem",
        "class ExportStatement",
        "module_statements: tuple[ModuleStatement, ...] = ()",
    ):
        assert value in ast_nodes
    assert "module_statements" not in analyzer
    carrier = _read("src/pietto/_project/module_carrier.py")
    assert "class ProjectCompilationMode(StrEnum)" in carrier
    assert "class ProjectModuleIdentity" in carrier
    assert "class ProjectLogicalModule" in carrier
    trusted = _read("src/pietto/_project/trusted_source.py")
    assert "class ProjectTrustedSourceSnapshot" in trusted
    assert "_load_trusted_source" in trusted
    module_catalog = _read("src/pietto/_project/module_catalog.py")
    assert "__all__: tuple[str, ...] = ()" in module_catalog
    assert "class ProjectNominalDeclarationIdentity" in module_catalog
    assert "class ProjectModuleCatalogSet" in module_catalog
    assert "find_identity" in module_catalog
    assert "find_namespace_name" in module_catalog
    for forbidden in ("winner", "precedence", "shadow", "PIE-S270"):
        assert forbidden not in module_catalog
    module_exports = _read("src/pietto/_project/module_exports.py")
    assert "__all__: tuple[str, ...] = ()" in module_exports
    for class_name in (
        "ProjectModuleExportRequest",
        "ProjectImportedExportCandidate",
        "ProjectModuleExportEntry",
        "ProjectModuleExportIssue",
        "ProjectModuleExportSurface",
        "ProjectModuleExportSurfaceSet",
    ):
        assert f"class {class_name}" in module_exports
    assert "def _build_project_module_export_surface_set" in module_exports
    assert "ImportStatement.target" not in module_exports
    assert "PIE-S270" not in module_exports
    module_bindings = _read("src/pietto/_project/module_bindings.py")
    assert "__all__: tuple[str, ...] = ()" in module_bindings
    for class_name in (
        "ProjectImportedBindingIdentity",
        "ProjectModuleImportRequest",
        "ProjectResolvedImportedBinding",
        "ProjectModuleBindingIssue",
        "ProjectModuleBindingEnvironment",
        "ProjectModuleBindingEnvironmentSet",
    ):
        assert f"class {class_name}" in module_bindings
    assert "def _build_project_module_binding_environment_set" in module_bindings
    assert "ProjectModuleBindingIssueStatus" in module_bindings
    assert "imported_export_candidates" in module_bindings
    assert "selected_input_index.find_path" in module_bindings
    assert "PIE-S270" not in module_bindings
    assert "ModuleGraph" not in module_bindings
    for forbidden in (
        "ModuleGraph",
        "ImportDef",
        "ExportDef",
        "declaration_catalog",
        "content_digest",
        "opened_identity",
    ):
        assert forbidden not in carrier
    assert "class ProjectModuleGraph" in graph_source
    for forbidden in ("ImportBinding", "ResolvedModule"):
        assert forbidden not in non_graph_production
    assert "ProjectResolvedModuleRelationReference" in preservation_source
    assert "ProjectResolvedModuleRelationReference" in inspection_source
    reservation = _section(
        SCOPE_REL,
        "Collision Cycle Ordering And PIE-S2701 Through PIE-S2707 Reservation",
    )
    descriptions = (
        "invalid, unselected, or unresolved local module target",
        "duplicate or conflicting module identity",
        "module import cycle",
        "duplicate, unknown, ineligible, or invalid export request",
        "unknown, private, or non-exported imported declaration",
        "local/import/alias/export binding collision",
        "unresolved explicit-module reference or unsupported advanced form",
    )
    for index, description in enumerate(descriptions, start=1):
        assert f"`PIE-S270{index}`" in reservation
        assert description in reservation
    assert "does not add these codes" in reservation
    for code in ("PIE-S2001", "PIE-S2002", "PIE-S2301", "PIE-S2302"):
        assert code in reservation


def test_public_json_artifact_cli_sql_dependency_workflow_version_and_release_surfaces_are_locked() -> (
    None
):
    for relative in (".github/workflows/ci.yml", "pyproject.toml", "uv.lock"):
        assert _sha256(relative) == PROTECTED_SHA256[relative]
    with (REPO_ROOT / "pyproject.toml").open("rb") as stream:
        pyproject = tomllib.load(stream)
    assert pyproject["project"]["version"] == "0.1.0"
    assert not (REPO_ROOT / "Cargo.toml").exists()
    assert not any(path.name == "Cargo.toml" for path in REPO_ROOT.rglob("Cargo.toml"))
    paths = _readable_paths()
    assert sum(path.startswith(".github/workflows/") for path in paths) == 1
    assert sum(path.startswith("src/pietto/generated/") for path in paths) == 8
    goldens = tuple((REPO_ROOT / "tests/fixtures/golden").glob("*"))
    assert sum(path.suffix == ".sql" for path in goldens) == 32
    assert sum(path.suffix == ".json" for path in goldens) == 5
    boundary = _section(
        SCOPE_REL,
        "No Grammar Source Runtime Public Schema Dependency Version Or Release Change",
    )
    for phrase in (
        "CLI",
        "JSON/artifact schema",
        "public exports",
        "workflow",
        "dependency",
        "lockfile",
        "package metadata/version",
        "Rust",
        "Release",
        "signing",
        "attestation",
    ):
        assert phrase in boundary


def test_gate_allowlist_reader_evidence_publication_stop_and_next_state_contracts_are_exact() -> (
    None
):
    assert (len(ADDED_PATHS), len(MODIFIED_PATHS), 0) == (3, 164, 0)
    assert len(NON_READER_MODIFIED_PATHS) == 4
    assert len(MECHANICAL_READER_PATHS) == 160
    assert len(FORMATTER_PATHS) == 163
    assert len(ALLOWLIST_PATHS) == 167
    readable = _readable_paths()
    assert len(readable) == 944
    assert sum(path.endswith(".py") for path in readable) == 579
    assert sum(path.endswith(".md") for path in readable) == 269
    test_modules = tuple(
        path
        for path in readable
        if path.startswith("tests/test_") and path.endswith(".py")
    )
    assert len(test_modules) == 465
    assert sum(len(_top_level_test_functions(path)) for path in test_modules) == 5489
    dirty = set(_git_output(["diff", "--name-only"]).splitlines()) | set(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    )
    dirty.discard("")
    if dirty:
        assert _phase54_active_gate2_is_active()
        if dirty == set(PHASE54_SLICE12_PR_CI_REPAIR_MODIFIED_PATHS):
            assert phase54_slice12_pr_ci_repair_is_active()
        elif dirty == set(PHASE54_SLICE12_PRODUCT_REPAIR3_MODIFIED_PATHS):
            assert phase54_slice12_product_repair3_is_active()
        elif dirty == set(PHASE54_SLICE12_PRODUCT_REPAIR10_MODIFIED_PATHS):
            assert phase54_slice12_product_repair10_is_active()
        elif dirty == set(PHASE54_SLICE12_PRODUCT_REPAIR11_MODIFIED_PATHS):
            assert phase54_slice12_product_repair11_is_active()
        assert _git_output(["diff", "--cached", "--name-only"]) == ""
    scope = _read(SCOPE_REL)
    for path in (
        "/home/mianliwang/.local/state/pietto/evidence/phase54-slice1/gate0-gate1-plan.txt",
        "/home/mianliwang/.local/state/pietto/evidence/phase54-slice1/gate0-gate1-plan-correction-1.txt",
        "/home/mianliwang/.local/state/pietto/evidence/phase54-slice1/gate2-evidence-and-diff.txt",
        "/home/mianliwang/.local/state/pietto/evidence/phase54-slice1/gate3-publication-evidence.txt",
    ):
        assert path in scope
    for phrase in (
        "O_CREAT | O_EXCL | O_NOFOLLOW",
        "mode `0644`",
        "A5_M32_D0",
        "14 primary tests",
        "10,814",
        "generated inventory 8",
        "goldens 37",
        "package smoke PASS",
        "phase54/slice1-scope-authority-expansion-route-lock",
        "Add Phase 54 scope authority and expansion route lock",
        "one ready PR",
        "exact tree equality",
        "ff-only",
        "phase54=ACTIVE",
        "slice1=COMPLETED",
        "next=PHASE54_SLICE2_GATE0_GATE1",
    ):
        assert phrase in scope
    assert (
        "PHASE54_SLICE1_GATE0_GATE1_CORRECTION_PASS "
        "base=af92f30c22e5d3df5219554a0663855a5b9f51a6 "
        "original_allowlist=A5_M21_D0 corrected_allowlist=A5_M32_D0 "
        "readers=31 candidates=classified tests=14 clean=10814 focused=14 "
        "formatter_paths=32 "
        "report=/home/mianliwang/.local/state/pietto/evidence/phase54-slice1/"
        "gate0-gate1-plan-correction-1.txt next=GATE2_RESUME_OFFLINE" in scope
    )
    slice2 = _read(SLICE2_SPEC_REL)
    slice2_flat = " ".join(slice2.split())
    for phrase in (
        "Authority is `A3_M54_D0`.",
        "contains exactly 16 top-level, non-parametrized tests",
        "ProjectLogicalModule",
        "permits only `LEGACY_FLAT` to reach `_build_project_semantic_catalog`",
        "Projected clean collection is 10,830",
        "executing mechanical reader closure contains exactly 48 modules",
        "write-mode formatter invocation contains exactly 55 literal Python paths",
        "Generated inventory remains 8",
        "Goldens remain 37: 32 SQL and 5 JSON",
        "Package smoke must pass and installed CLI remains 0.1.0",
        "`O_CREAT | O_EXCL | O_NOFOLLOW`, mode 0644",
        "phase54/slice2-schema-v2-module-carrier",
        "Add Phase 54 schema v2 module activation carrier",
        "one ready PR",
        "exact-tree squash",
        "fetch/ff-only reconciliation",
        "`next=PHASE54_SLICE3_GATE0_GATE1`",
        "Do not begin Slice 3",
    ):
        assert phrase in slice2_flat
    slice3 = _read(SLICE3_SPEC_REL)
    for path in (
        "/home/mianliwang/.local/state/pietto/evidence/pietto-phase54-slice3-gate0-gate1-plan.txt",
        "/home/mianliwang/.local/state/pietto/evidence/pietto-phase54-slice3-gate0-gate1-plan-correction-1.txt",
        "/home/mianliwang/.local/state/pietto/evidence/pietto-phase54-slice3-gate0-gate1-plan-correction-2.txt",
        "/home/mianliwang/.local/state/pietto/evidence/pietto-phase54-slice3-gate2-evidence-and-diff.txt",
        "/home/mianliwang/.local/state/pietto/evidence/pietto-phase54-slice3-gate3-publication-evidence.txt",
    ):
        assert path in slice3
    assert "/evidence/phase54-slice3/" not in slice3
    for phrase in (
        "`A5_M56_D0`",
        "exactly 26 undecorated top-level tests",
        "O_CREAT | O_EXCL | O_NOFOLLOW",
        "mode=0644",
        "natural exact-head PR CI attempt 1",
        "squash-tree equality",
        "ff-only reconciliation",
        "next state is\n`PHASE54_SLICE4_GATE0_GATE1`",
    ):
        assert phrase in slice3
    slice4 = _read(SLICE4_SPEC_REL)
    for phrase in (
        "`15bae172ee151e370fe59d3bf909d735aee6aa90`",
        "`A2_M138_D0`",
        "exactly 30 undecorated, non-parametrized",
        "exactly seven generated paths and 125",
        "exactly\n128 literal handwritten Python paths",
        "10886 passed",
        "Successful\nparsing or checking therefore does not validate",
        "PIE-S2701",
        "remain absent and un-emitted",
        "PHASE54_SLICE5_GATE0_GATE1",
    ):
        assert phrase in slice4
    slice5 = _read(SLICE5_SPEC_REL)
    for phrase in (
        "`0f3c955c5a5fbd8046ef611ad1bef0b636c8be01`",
        "`A3_M53_D0`",
        "exactly 30\nundecorated, non-parametrized top-level tests",
        "and 49\nexecuting mechanical readers",
        "52 literal handwritten\nPython paths",
        "10916",
        "There is no `first`, winner",
        "do not emit `PIE-S2001` or `PIE-S2701`\nthrough `PIE-S2707`",
        "PHASE54_SLICE6_GATE0_GATE1",
    ):
        assert phrase in slice5
    plan = _read(PLAN_REL)
    for forbidden in ("dirty overlay", "skip", "xfail", "deselection", "masking"):
        assert forbidden in plan
    stop = _section(SCOPE_REL, "Stop Conditions")
    assert (
        "Mechanical hash, manifest, inventory, heading, phrase, formatter, topology"
        in stop
    )
    assert "without a routine user pause" in stop
    slice2_stop = _section(SLICE2_SPEC_REL, "Stop And Next State")
    assert "mechanical reader/hash/inventory/topology repair" in slice2_stop
    assert "not a product decision" in slice2_stop
