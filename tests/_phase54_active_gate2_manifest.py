"""Exact test-only authority for the currently active Phase 54 Gate 2."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[1]

PHASE54_ACTIVE_GATE2_MARKER = "PHASE54_SLICE10_GATE2"
PHASE54_ACTIVE_GATE2_BASE = "fadb1924af057cfc901a1658e117810d699e2358"
PHASE54_POST_REVIEW_PRODUCT_REPAIR1_BASE = "6104002486d21b7b25dbec74d037c0fc7cc5099a"
PHASE54_POST_REVIEW_PRODUCT_REPAIR1_BRANCH = (
    "phase54/slice10-cross-module-relation-row-facts"
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR2_BASE = "3caa5e52be41cd7e1ed0ed364f2d62574adce840"
PHASE54_POST_REVIEW_PRODUCT_REPAIR2_BRANCH = (
    "phase54/slice10-cross-module-relation-row-facts"
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR3_BASE = "17a5b01e555930537334d4d0bcf3480e332b7e91"
PHASE54_POST_REVIEW_PRODUCT_REPAIR3_BRANCH = (
    "phase54/slice10-cross-module-relation-row-facts"
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR4_BASE = "3f057874a1bec524da38b58c243267f4590c167b"
PHASE54_POST_REVIEW_PRODUCT_REPAIR4_BRANCH = (
    "phase54/slice10-cross-module-relation-row-facts"
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR5_BASE = "fcdd02b5604c2b84d861b593a1887eaeb4620c91"
PHASE54_POST_REVIEW_PRODUCT_REPAIR5_BRANCH = (
    "phase54/slice10-cross-module-relation-row-facts"
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR6_BASE = "c73e5ea0628d821ada5a8cbb93102bae69768600"
PHASE54_POST_REVIEW_PRODUCT_REPAIR6_BRANCH = (
    "phase54/slice10-cross-module-relation-row-facts"
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR7_BASE = "a5df3ed264c443d902831fe532d265ac1e452158"
PHASE54_POST_REVIEW_PRODUCT_REPAIR7_BRANCH = (
    "phase54/slice10-cross-module-relation-row-facts"
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR8_BASE = "7b96b416d963e67624a461ec906ab2fe14630380"
PHASE54_POST_REVIEW_PRODUCT_REPAIR8_BRANCH = (
    "phase54/slice10-cross-module-relation-row-facts"
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR9_BASE = "38353a00bdaf6b1edb9a0eb53ada1a3249b6ae79"
PHASE54_POST_REVIEW_PRODUCT_REPAIR9_BRANCH = (
    "phase54/slice10-cross-module-relation-row-facts"
)
ADDED_PATHS = set()
PHASE54_POST_REVIEW_PRODUCT_REPAIR1_TO_8_SEED_PATHS = {
    "src/pietto/_project/module_relation_resolution.py",
    "tests/_phase54_active_gate2_manifest.py",
    "tests/test_phase54_cross_module_table_query_relation_resolution_row_facts_legacy_compatibility.py",
}
MECHANICAL_READER_PATHS = {
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_packaging_smoke.py",
    "tests/test_phase11_validation_entrypoint.py",
    "tests/test_phase12_completion_audit.py",
    "tests/test_phase12_composition_cli_json_goldens.py",
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
    "tests/test_phase33_completion_audit.py",
    "tests/test_phase47_project_json_privacy_hardening.py",
    "tests/test_phase50_import_module_export_readiness.py",
    "tests/test_phase51_aggregate_grouped_downstream_propagation.py",
    "tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py",
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
    "tests/test_phase54_cross_module_type_alias_enum_shape_source_resolution.py",
    "tests/test_phase54_import_export_contextual_grammar_ast.py",
    "tests/test_phase54_local_export_visibility_module_facades.py",
    "tests/test_phase54_local_import_module_export_foundation_scope_lock.py",
    "tests/test_phase54_module_graph_cycles_diagnostics_deterministic_ordering.py",
    "tests/test_phase54_module_identity_selected_input_index_trusted_local_loader.py",
    "tests/test_phase54_module_qualified_nominal_declaration_catalogs.py",
    "tests/test_phase54_named_import_alias_binding_environments_collision_rules.py",
    "tests/test_phase54_schema_v2_explicit_module_carrier.py",
}
PHASE54_POST_REVIEW_PRODUCT_REPAIR2_TO_8_READER_PATHS = {
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_packaging_smoke.py",
    "tests/test_phase11_validation_entrypoint.py",
    "tests/test_phase12_completion_audit.py",
    "tests/test_phase12_composition_cli_json_goldens.py",
    "tests/test_phase33_completion_audit.py",
    "tests/test_phase51_aggregate_grouped_downstream_propagation.py",
    "tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py",
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
    "tests/test_phase53_completion_audit_and_status_lock.py",
    "tests/test_phase53_generic_type_variable_exact_compatibility_contract.py",
    "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
    "tests/test_phase53_multiple_window_outputs_final_order_alias_downstream_schema_lineage_contract.py",
    "tests/test_phase53_nullability_algebra_signature_result_formula_contract.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
    "tests/test_phase53_percent_rank_cume_dist_ntile_contract.py",
    "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py",
    "tests/test_phase53_rank_dense_rank_peer_semantics_contract.py",
    "tests/test_phase53_row_number_direct_field_mvp_contract.py",
    "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
    "tests/test_phase53_window_spec_function_identity_ast_contract.py",
    "tests/test_phase54_cross_module_type_alias_enum_shape_source_resolution.py",
    "tests/test_phase54_local_export_visibility_module_facades.py",
    "tests/test_phase54_local_import_module_export_foundation_scope_lock.py",
    "tests/test_phase54_module_graph_cycles_diagnostics_deterministic_ordering.py",
    "tests/test_phase54_module_qualified_nominal_declaration_catalogs.py",
    "tests/test_phase54_named_import_alias_binding_environments_collision_rules.py",
}
PHASE54_SLICE10_PRIOR_MECHANICAL_READER_PATHS = set(MECHANICAL_READER_PATHS)
NON_READER_MODIFIED_PATHS = {
    "README.md",
    "tests/_phase54_active_gate2_manifest.py",
    "tests/test_phase54_cross_module_table_query_relation_resolution_row_facts_legacy_compatibility.py",
}
VALIDATION_READER_PATHS = set(MECHANICAL_READER_PATHS)
MODIFIED_PATHS = NON_READER_MODIFIED_PATHS | MECHANICAL_READER_PATHS
ALLOWLIST_PATHS = ADDED_PATHS | MODIFIED_PATHS
PHASE54_ACTIVE_GATE2_ADDED_PATHS = frozenset(ADDED_PATHS)
PHASE54_ACTIVE_GATE2_MODIFIED_PATHS = frozenset(MODIFIED_PATHS)
PHASE54_ACTIVE_GATE2_DELETED_PATHS = frozenset()
PHASE54_SLICE10_ORIGINAL_ADDED_PATHS = frozenset(
    {
        "docs/spec/phase54-slice10-cross-module-table-query-relation-resolution-row-facts-and-legacy-compatibility-v1.md",
        "src/pietto/_project/module_relation_resolution.py",
        "tests/test_phase54_cross_module_table_query_relation_resolution_row_facts_legacy_compatibility.py",
    }
)
PHASE54_SLICE10_ORIGINAL_NON_READER_MODIFIED_PATHS = frozenset(
    {
        "README.md",
        "docs/plan/phase-54-local-import-module-export-foundation.md",
        "docs/spec/diagnostics.md",
        "docs/spec/pietto-v0.9.md",
        "src/pietto/_project/model.py",
        "tests/_phase54_active_gate2_manifest.py",
    }
)
PHASE54_SLICE10_ORIGINAL_MECHANICAL_READER_PATHS = frozenset(
    PHASE54_SLICE10_PRIOR_MECHANICAL_READER_PATHS
)
PHASE54_SLICE10_ORIGINAL_MODIFIED_PATHS = frozenset(
    PHASE54_SLICE10_ORIGINAL_NON_READER_MODIFIED_PATHS
    | PHASE54_SLICE10_ORIGINAL_MECHANICAL_READER_PATHS
)
PHASE54_SLICE10_ORIGINAL_ALLOWLIST_PATHS = frozenset(
    PHASE54_SLICE10_ORIGINAL_ADDED_PATHS | PHASE54_SLICE10_ORIGINAL_MODIFIED_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR1_SEED_PATHS = frozenset(
    PHASE54_POST_REVIEW_PRODUCT_REPAIR1_TO_8_SEED_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR1_READER_PATHS = frozenset(
    PHASE54_SLICE10_PRIOR_MECHANICAL_READER_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR1_MODIFIED_PATHS = frozenset(
    PHASE54_POST_REVIEW_PRODUCT_REPAIR1_TO_8_SEED_PATHS
    | PHASE54_POST_REVIEW_PRODUCT_REPAIR1_READER_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR2_SEED_PATHS = frozenset(
    PHASE54_POST_REVIEW_PRODUCT_REPAIR1_TO_8_SEED_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR2_READER_PATHS = frozenset(
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_TO_8_READER_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR2_MODIFIED_PATHS = frozenset(
    PHASE54_POST_REVIEW_PRODUCT_REPAIR1_TO_8_SEED_PATHS
    | PHASE54_POST_REVIEW_PRODUCT_REPAIR2_TO_8_READER_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR3_SEED_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_SEED_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR3_READER_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_READER_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR3_MODIFIED_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_MODIFIED_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR4_SEED_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_SEED_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR4_READER_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_READER_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR4_MODIFIED_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_MODIFIED_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR5_SEED_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_SEED_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR5_READER_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_READER_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR5_MODIFIED_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_MODIFIED_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR6_SEED_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_SEED_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR6_READER_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_READER_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR6_MODIFIED_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_MODIFIED_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR7_SEED_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_SEED_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR7_READER_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_READER_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR7_MODIFIED_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_MODIFIED_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR8_SEED_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_SEED_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR8_READER_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_READER_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR8_MODIFIED_PATHS = (
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_MODIFIED_PATHS
)
PHASE54_POST_REVIEW_PRODUCT_REPAIR9_SEED_PATHS = frozenset(NON_READER_MODIFIED_PATHS)
PHASE54_POST_REVIEW_PRODUCT_REPAIR9_READER_PATHS = frozenset(MECHANICAL_READER_PATHS)
PHASE54_POST_REVIEW_PRODUCT_REPAIR9_MODIFIED_PATHS = frozenset(MODIFIED_PATHS)


@dataclass(frozen=True, slots=True, kw_only=True)
class Phase54Gate2RepositoryState:
    """The exact read-only repository facts used by the active manifest gate."""

    marker: str
    branch_oid: str
    branch_head: str
    branch_upstream: str
    ahead: int
    behind: int
    added_paths: frozenset[str]
    modified_paths: frozenset[str]
    deleted_paths: frozenset[str]
    staged_paths: frozenset[str]
    other_paths: frozenset[str]
    worktree_count: int
    shallow: bool
    active_git_operation: bool


def _git_output(args: list[str]) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.rstrip()


def _read_phase54_gate2_repository_state() -> Phase54Gate2RepositoryState:
    status = _git_output(
        ["status", "--porcelain=v2", "--branch", "--untracked-files=all"]
    )
    branch_oid = ""
    branch_head = ""
    branch_upstream = ""
    ahead = -1
    behind = -1
    added_paths: set[str] = set()
    modified_paths: set[str] = set()
    deleted_paths: set[str] = set()
    staged_paths: set[str] = set()
    other_paths: set[str] = set()

    for line in status.splitlines():
        if line.startswith("# branch.oid "):
            branch_oid = line.removeprefix("# branch.oid ")
        elif line.startswith("# branch.head "):
            branch_head = line.removeprefix("# branch.head ")
        elif line.startswith("# branch.upstream "):
            branch_upstream = line.removeprefix("# branch.upstream ")
        elif line.startswith("# branch.ab "):
            ahead_text, behind_text = line.removeprefix("# branch.ab ").split()
            ahead = int(ahead_text.removeprefix("+"))
            behind = int(behind_text.removeprefix("-"))
        elif line.startswith("? "):
            added_paths.add(line.removeprefix("? "))
        elif line.startswith("1 "):
            parts = line.split(" ", 8)
            if len(parts) != 9:
                other_paths.add(line)
                continue
            index_status, worktree_status = parts[1]
            path = parts[8]
            if index_status != ".":
                staged_paths.add(path)
            if worktree_status == "M":
                modified_paths.add(path)
            elif worktree_status == "D":
                deleted_paths.add(path)
            elif worktree_status != ".":
                other_paths.add(path)
        elif not line.startswith("# "):
            other_paths.add(line)

    git_dir = Path(_git_output(["rev-parse", "--git-dir"]))
    if not git_dir.is_absolute():
        git_dir = REPO_ROOT / git_dir
    active_git_operation = any(
        (git_dir / name).exists()
        for name in (
            "MERGE_HEAD",
            "CHERRY_PICK_HEAD",
            "REVERT_HEAD",
            "REBASE_HEAD",
            "rebase-merge",
            "rebase-apply",
        )
    )
    worktree_count = _git_output(["worktree", "list", "--porcelain"]).count("worktree ")
    shallow = _git_output(["rev-parse", "--is-shallow-repository"]) == "true"
    return Phase54Gate2RepositoryState(
        marker=PHASE54_ACTIVE_GATE2_MARKER,
        branch_oid=branch_oid,
        branch_head=branch_head,
        branch_upstream=branch_upstream,
        ahead=ahead,
        behind=behind,
        added_paths=frozenset(added_paths),
        modified_paths=frozenset(modified_paths),
        deleted_paths=frozenset(deleted_paths),
        staged_paths=frozenset(staged_paths),
        other_paths=frozenset(other_paths),
        worktree_count=worktree_count,
        shallow=shallow,
        active_git_operation=active_git_operation,
    )


def _matches_phase54_active_gate2_manifest(
    state: Phase54Gate2RepositoryState,
) -> bool:
    """Return whether supplied facts are exactly the frozen active Gate 2."""

    if type(state) is not Phase54Gate2RepositoryState:
        return False
    common = (
        state.marker == PHASE54_ACTIVE_GATE2_MARKER
        and state.ahead == 0
        and state.behind == 0
        and state.staged_paths == frozenset()
        and state.other_paths == frozenset()
        and state.worktree_count == 1
        and not state.shallow
        and not state.active_git_operation
    )
    original_gate2 = (
        state.branch_oid == PHASE54_ACTIVE_GATE2_BASE
        and state.branch_head == "main"
        and state.branch_upstream == "origin/main"
        and state.added_paths == PHASE54_SLICE10_ORIGINAL_ADDED_PATHS
        and state.modified_paths == PHASE54_SLICE10_ORIGINAL_MODIFIED_PATHS
        and state.deleted_paths == PHASE54_ACTIVE_GATE2_DELETED_PATHS
    )
    product_repair1 = (
        state.branch_oid == PHASE54_POST_REVIEW_PRODUCT_REPAIR1_BASE
        and state.branch_head == PHASE54_POST_REVIEW_PRODUCT_REPAIR1_BRANCH
        and state.branch_upstream
        == f"origin/{PHASE54_POST_REVIEW_PRODUCT_REPAIR1_BRANCH}"
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_POST_REVIEW_PRODUCT_REPAIR1_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
    product_repair2 = (
        state.branch_oid == PHASE54_POST_REVIEW_PRODUCT_REPAIR2_BASE
        and state.branch_head == PHASE54_POST_REVIEW_PRODUCT_REPAIR2_BRANCH
        and state.branch_upstream
        == f"origin/{PHASE54_POST_REVIEW_PRODUCT_REPAIR2_BRANCH}"
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_POST_REVIEW_PRODUCT_REPAIR2_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
    product_repair3 = (
        state.branch_oid == PHASE54_POST_REVIEW_PRODUCT_REPAIR3_BASE
        and state.branch_head == PHASE54_POST_REVIEW_PRODUCT_REPAIR3_BRANCH
        and state.branch_upstream
        == f"origin/{PHASE54_POST_REVIEW_PRODUCT_REPAIR3_BRANCH}"
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_POST_REVIEW_PRODUCT_REPAIR3_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
    product_repair4 = (
        state.branch_oid == PHASE54_POST_REVIEW_PRODUCT_REPAIR4_BASE
        and state.branch_head == PHASE54_POST_REVIEW_PRODUCT_REPAIR4_BRANCH
        and state.branch_upstream
        == f"origin/{PHASE54_POST_REVIEW_PRODUCT_REPAIR4_BRANCH}"
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_POST_REVIEW_PRODUCT_REPAIR4_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
    product_repair5 = (
        state.branch_oid == PHASE54_POST_REVIEW_PRODUCT_REPAIR5_BASE
        and state.branch_head == PHASE54_POST_REVIEW_PRODUCT_REPAIR5_BRANCH
        and state.branch_upstream
        == f"origin/{PHASE54_POST_REVIEW_PRODUCT_REPAIR5_BRANCH}"
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_POST_REVIEW_PRODUCT_REPAIR5_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
    product_repair6 = (
        state.branch_oid == PHASE54_POST_REVIEW_PRODUCT_REPAIR6_BASE
        and state.branch_head == PHASE54_POST_REVIEW_PRODUCT_REPAIR6_BRANCH
        and state.branch_upstream
        == f"origin/{PHASE54_POST_REVIEW_PRODUCT_REPAIR6_BRANCH}"
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_POST_REVIEW_PRODUCT_REPAIR6_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
    product_repair7 = (
        state.branch_oid == PHASE54_POST_REVIEW_PRODUCT_REPAIR7_BASE
        and state.branch_head == PHASE54_POST_REVIEW_PRODUCT_REPAIR7_BRANCH
        and state.branch_upstream
        == f"origin/{PHASE54_POST_REVIEW_PRODUCT_REPAIR7_BRANCH}"
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_POST_REVIEW_PRODUCT_REPAIR7_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
    product_repair8 = (
        state.branch_oid == PHASE54_POST_REVIEW_PRODUCT_REPAIR8_BASE
        and state.branch_head == PHASE54_POST_REVIEW_PRODUCT_REPAIR8_BRANCH
        and state.branch_upstream
        == f"origin/{PHASE54_POST_REVIEW_PRODUCT_REPAIR8_BRANCH}"
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_POST_REVIEW_PRODUCT_REPAIR8_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
    product_repair9 = (
        state.branch_oid == PHASE54_POST_REVIEW_PRODUCT_REPAIR9_BASE
        and state.branch_head == PHASE54_POST_REVIEW_PRODUCT_REPAIR9_BRANCH
        and state.branch_upstream
        == f"origin/{PHASE54_POST_REVIEW_PRODUCT_REPAIR9_BRANCH}"
        and state.added_paths == frozenset()
        and state.modified_paths == PHASE54_POST_REVIEW_PRODUCT_REPAIR9_MODIFIED_PATHS
        and state.deleted_paths == frozenset()
    )
    return common and (
        original_gate2
        or product_repair1
        or product_repair2
        or product_repair3
        or product_repair4
        or product_repair5
        or product_repair6
        or product_repair7
        or product_repair8
        or product_repair9
    )


def phase54_active_gate2_manifest_is_active() -> bool:
    """Read exact local Git facts and recognize only the active Gate 2 state."""

    try:
        state = _read_phase54_gate2_repository_state()
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return _matches_phase54_active_gate2_manifest(state)
