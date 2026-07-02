from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

from _static_audit_helpers import (
    git_diff_name_only as _git_diff_name_only,
    normalized_text as _normalized,
    read_text as _read,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-39-count-family-implementation-candidate.md"
PHASE37_PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-37-post-v02-aggregate-surface-expansion.md"
)
PHASE38_PLAN_PATH = (
    REPO_ROOT
    / "docs/plan/phase-38-aggregate-semantics-and-type-capability-consolidation.md"
)

PHASE38_ARTIFACT_PATHS = (
    "docs/plan/phase-38-aggregate-semantics-and-type-capability-consolidation.md",
    "docs/spec/phase38-count-family-semantics-contract-v1.md",
    "docs/spec/phase38-type-capability-matrix-contract-v1.md",
    "docs/spec/phase38-boundary-types-capability-contract-v1.md",
    "docs/spec/phase38-distinct-collation-ordering-readiness-v1.md",
    "docs/spec/phase38-binding-filter-post-aggregate-roadmap-v1.md",
    "tests/test_phase38_candidate_decision.py",
    "tests/test_phase38_count_family_semantics_contract.py",
    "tests/test_phase38_type_capability_matrix_contract.py",
    "tests/test_phase38_boundary_types_capability_contract.py",
    "tests/test_phase38_distinct_collation_ordering_readiness.py",
    "tests/test_phase38_binding_filter_post_aggregate_roadmap.py",
    "tests/test_phase38_completion_audit.py",
)

COUNT_FAMILY_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase38-count-family-semantics-contract-v1.md"
)
TYPE_CAPABILITY_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase38-type-capability-matrix-contract-v1.md"
)
DISTINCT_ORDERING_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase38-distinct-collation-ordering-readiness-v1.md"
)
BINDING_ROADMAP_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase38-binding-filter-post-aggregate-roadmap-v1.md"
)

SEMANTIC_AGGREGATES_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"
SEMANTIC_RELATION_SCHEMAS_PATH = REPO_ROOT / "src/pietto/semantic/relation_schemas.py"
SEMANTIC_GROUP_BY_PATH = REPO_ROOT / "src/pietto/semantic/group_by.py"
IR_MODEL_PATH = REPO_ROOT / "src/pietto/ir/model.py"
IR_LOWERING_PATH = REPO_ROOT / "src/pietto/ir/lowering.py"
POSTGRES_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/sql/expressions.py"
MYSQL_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/sql/mysql_expressions.py"
GRAMMAR_PATH = REPO_ROOT / "grammar/Pietto.g4"
PACKAGE_SMOKE_PATH = REPO_ROOT / "scripts/package_smoke.py"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE1_CHANGED_PATHS = {
    "docs/plan/phase-39-count-family-implementation-candidate.md",
    "tests/test_phase39_candidate_decision.py",
}
ALLOWED_SLICE3_CHANGED_PATHS = {
    "docs/plan/phase-39-count-family-implementation-candidate.md",
    "src/pietto/semantic/aggregates.py",
    "src/pietto/sql/expressions.py",
    "src/pietto/sql/mysql_expressions.py",
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
    "tests/test_phase15_relationship_name_ownership_contract.py",
    "tests/test_phase15_semantic_completion_audit.py",
    "tests/test_phase16_completion_audit.py",
    "tests/test_phase16_current_syntax_surface_audit.py",
    "tests/test_phase16_language_direction_audit.py",
    "tests/test_phase16_safety_deferral_sql_portability.py",
    "tests/test_phase21_group_by_hardening_audit.py",
    "tests/test_phase23_count_field_ir.py",
    "tests/test_phase23_count_field_semantics.py",
    "tests/test_phase23_count_field_sql.py",
    "tests/test_phase24_aggregate_expression_arguments_readiness.py",
    "tests/test_phase24_cli_json_output_hardening.py",
    "tests/test_phase24_completion_audit.py",
    "tests/test_phase25_completion_audit.py",
    "tests/test_phase26_aggregate_expression_argument_cli_json_output.py",
    "tests/test_phase26_aggregate_expression_argument_ir.py",
    "tests/test_phase26_aggregate_expression_argument_semantics.py",
    "tests/test_phase26_aggregate_expression_argument_sql.py",
    "tests/test_phase26_completion_audit.py",
    "tests/test_phase26_count_distinct_text_transform_semantics.py",
    "tests/test_phase27_completion_audit.py",
    "tests/test_phase28_completion_audit.py",
    "tests/test_phase28_numeric_literal_aggregate_cli_json_output.py",
    "tests/test_phase28_numeric_literal_aggregate_ir.py",
    "tests/test_phase28_numeric_literal_aggregate_semantics.py",
    "tests/test_phase28_numeric_literal_aggregate_sql.py",
    "tests/test_phase29_completion_audit.py",
    "tests/test_phase30_completion_audit.py",
    "tests/test_phase31_aggregate_result_matrix_hardening.py",
    "tests/test_phase31_numeric_promotion_decimal_boundary.py",
    "tests/test_phase34_candidate_decision.py",
    "tests/test_phase34_completion_audit.py",
    "tests/test_phase34_first_implementation_candidate_decision.py",
    "tests/test_phase34_narrow_join_contract.py",
    "tests/test_phase34_parser_ast_readiness_contract.py",
    "tests/test_phase34_relationship_grain_contract.py",
    "tests/test_phase34_rescope_completion_candidate_decision.py",
    "tests/test_phase34_semantic_readiness_contract.py",
    "tests/test_phase35_completion_audit.py",
    "tests/test_phase35_internal_helper_simplification_candidate_decision.py",
    "tests/test_phase35_safe_simplification_candidate_decision.py",
    "tests/test_phase35_validation_delivery_workflow_polish.py",
    "tests/test_phase36_any_bytes_json_support_posture.py",
    "tests/test_phase36_candidate_decision.py",
    "tests/test_phase36_completion_audit.py",
    "tests/test_phase36_datetime_time_interval_boundary.py",
    "tests/test_phase36_decimal_precision_scale_carrier_mvp_decision.py",
    "tests/test_phase36_enum_support_resolution.py",
    "tests/test_phase36_expanded_scalar_operator_matrix.py",
    "tests/test_phase36_public_surface_stability_hardening.py",
    "tests/test_phase36_rescope_candidate_resolution_matrix.py",
    "tests/test_phase36_status_housekeeping.py",
    "tests/test_phase36_type_alias_domain_refinement_boundary.py",
    "tests/test_phase36_uuid_support_completion.py",
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
    "tests/test_phase39_count_family_boundary_regression_matrix.py",
    "tests/test_phase39_count_expression_mvp_contract.py",
    "tests/test_phase39_count_expression_ir.py",
    "tests/test_phase39_count_expression_cli_json_output.py",
    "tests/test_phase39_count_expression_semantics.py",
    "tests/test_phase39_count_expression_sql.py",
    "tests/test_phase39_completion_audit.py",
    "tests/test_sql_mysql_expressions.py",
    "tests/test_sql_postgres_expressions.py",
}
PHASE40_SLICE3_REPAIR_CHANGED_PATHS = {
    "docs/plan/phase-40-let-binding-model-candidate.md",
    "docs/spec/diagnostics.md",
    "grammar/Pietto.g4",
    "src/pietto/ast_builder.py",
    "src/pietto/ast_nodes.py",
    "src/pietto/generated/Pietto.interp",
    "src/pietto/generated/Pietto.tokens",
    "src/pietto/generated/PiettoLexer.interp",
    "src/pietto/generated/PiettoLexer.py",
    "src/pietto/generated/PiettoLexer.tokens",
    "src/pietto/generated/PiettoParser.py",
    "src/pietto/generated/PiettoVisitor.py",
    "src/pietto/ir/builder.py",
    "src/pietto/ir/lowering.py",
    "src/pietto/semantic/analyzer.py",
    "src/pietto/semantic/expressions.py",
    "src/pietto/semantic/let_bindings.py",
    "src/pietto/semantic/model.py",
    "src/pietto/semantic/relation_schemas.py",
    "tests/test_phase8_completion_audit.py",
    "tests/test_phase9_completion_audit.py",
    "tests/test_phase10_completion_audit.py",
    "tests/test_phase10_dialect_dispatch_design.py",
    "tests/test_phase10_mysql_backend_skeleton.py",
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
    "tests/test_phase17_computed_projection_schema_propagation.py",
    "tests/test_phase17_core_scalar_expression_semantics.py",
    "tests/test_phase17_relation_schema_hardening_completion_audit.py",
    "tests/test_phase17_single_input_qualified_field_binding.py",
    "tests/test_phase19_completion_audit.py",
    "tests/test_phase20_completion_audit.py",
    "tests/test_phase21_group_by_hardening_audit.py",
    "tests/test_phase24_aggregate_expression_arguments_readiness.py",
    "tests/test_phase24_cli_json_output_hardening.py",
    "tests/test_phase24_completion_audit.py",
    "tests/test_phase25_completion_audit.py",
    "tests/test_phase26_completion_audit.py",
    "tests/test_phase26_decimal_scalar_expression_semantics.py",
    "tests/test_phase26_numeric_scalar_expression_semantics.py",
    "tests/test_phase27_completion_audit.py",
    "tests/test_phase27_grouped_order_candidate_decision.py",
    "tests/test_phase28_completion_audit.py",
    "tests/test_phase29_completion_audit.py",
    "tests/test_phase30_completion_audit.py",
    "tests/test_phase31_diagnostic_cli_json_stability.py",
    "tests/test_phase34_candidate_decision.py",
    "tests/test_phase34_completion_audit.py",
    "tests/test_phase34_first_implementation_candidate_decision.py",
    "tests/test_phase34_narrow_join_contract.py",
    "tests/test_phase34_parser_ast_readiness_contract.py",
    "tests/test_phase34_relationship_grain_contract.py",
    "tests/test_phase34_rescope_completion_candidate_decision.py",
    "tests/test_phase34_semantic_readiness_contract.py",
    "tests/test_phase35_completion_audit.py",
    "tests/test_phase35_internal_helper_simplification_candidate_decision.py",
    "tests/test_phase35_safe_simplification_candidate_decision.py",
    "tests/test_phase35_static_audit_helper_simplification.py",
    "tests/test_phase35_validation_delivery_workflow_polish.py",
    "tests/test_phase36_any_bytes_json_support_posture.py",
    "tests/test_phase36_candidate_decision.py",
    "tests/test_phase36_completion_audit.py",
    "tests/test_phase36_datetime_time_interval_boundary.py",
    "tests/test_phase36_decimal_precision_scale_carrier_mvp_decision.py",
    "tests/test_phase36_enum_support_resolution.py",
    "tests/test_phase36_expanded_scalar_operator_matrix.py",
    "tests/test_phase36_public_surface_stability_hardening.py",
    "tests/test_phase36_rescope_candidate_resolution_matrix.py",
    "tests/test_phase36_status_housekeeping.py",
    "tests/test_phase36_type_alias_domain_refinement_boundary.py",
    "tests/test_phase36_uuid_support_completion.py",
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
    "docs/spec/phase40-let-binding-aggregate-interaction-boundary-v1.md",
    "tests/test_phase40_completion_audit.py",
    "tests/test_phase40_let_binding_aggregate_interaction_boundary.py",
    "tests/test_phase40_let_binding_boundary_regression_matrix.py",
    "tests/test_phase40_let_binding_cli_json_metadata.py",
    "tests/test_phase40_let_binding_ir_sql_lowering.py",
    "tests/test_phase40_let_binding_model_candidate.py",
    "tests/test_phase40_let_binding_parser_ast.py",
    "tests/test_phase40_let_binding_row_level_semantics.py",
    "tests/test_phase40_let_binding_semantic_model_ir_readiness.py",
    "tests/test_phase40_let_binding_syntax_scope_contract.py",
}
PHASE41_SLICE1_CARRYOVER_CHANGED_PATHS = {
    "docs/plan/phase-41-decimal-precision-scale-mvp.md",
    "tests/test_phase41_decimal_precision_scale_candidate.py",
}
PHASE41_SLICE2_CHANGED_PATHS = {
    "src/pietto/semantic/analyzer.py",
    "docs/spec/diagnostics.md",
    "tests/test_phase41_decimal_precision_scale_semantic_validation.py",
    "tests/test_phase41_decimal_precision_scale_candidate.py",
    "tests/test_phase30_decimal_precision_scale_contract.py",
    "tests/test_phase31_numeric_promotion_decimal_boundary.py",
    "tests/test_phase36_decimal_precision_scale_carrier_mvp_decision.py",
    "tests/test_phase39_candidate_decision.py",
    "tests/test_phase40_completion_audit.py",
}
PHASE41_SLICE3_CHANGED_PATHS = {
    "src/pietto/semantic/model.py",
    "src/pietto/semantic/analyzer.py",
    "tests/test_phase41_decimal_precision_scale_type_carrier.py",
    "tests/test_phase41_decimal_precision_scale_semantic_validation.py",
    "tests/test_phase41_decimal_precision_scale_candidate.py",
    "tests/test_phase30_decimal_precision_scale_contract.py",
    "tests/test_phase31_numeric_promotion_decimal_boundary.py",
    "tests/test_phase36_decimal_precision_scale_carrier_mvp_decision.py",
    "tests/test_phase39_candidate_decision.py",
    "tests/test_phase40_completion_audit.py",
    "tests/test_phase31_date_timestamp_sql_compatibility.py",
}
PHASE41_SLICE4_CHANGED_PATHS = {
    "tests/test_phase41_decimal_precision_scale_ir_compatibility.py",
    "tests/test_phase41_decimal_precision_scale_candidate.py",
    "tests/test_phase39_candidate_decision.py",
    "tests/test_phase40_completion_audit.py",
}
PHASE41_SLICE5_CHANGED_PATHS = {
    "tests/test_phase41_decimal_precision_scale_aggregate_numeric_boundary.py",
    "tests/test_phase41_decimal_precision_scale_candidate.py",
    "tests/test_phase39_candidate_decision.py",
    "tests/test_phase40_completion_audit.py",
}
PHASE41_SLICE6_CHANGED_PATHS = {
    "tests/test_phase41_decimal_precision_scale_metadata_cli_compatibility.py",
    "tests/test_phase41_decimal_precision_scale_candidate.py",
    "tests/test_phase39_candidate_decision.py",
    "tests/test_phase40_completion_audit.py",
}
PHASE41_SLICE2_REPAIR_HASH_LOCK_CHANGED_PATHS = {
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
}
ALLOWED_PHASE41_SLICE1_REPAIR_CHANGED_PATHS = (
    ALLOWED_SLICE3_CHANGED_PATHS
    | PHASE40_SLICE3_REPAIR_CHANGED_PATHS
    | PHASE41_SLICE1_CARRYOVER_CHANGED_PATHS
    | PHASE41_SLICE2_CHANGED_PATHS
    | PHASE41_SLICE3_CHANGED_PATHS
    | PHASE41_SLICE4_CHANGED_PATHS
    | PHASE41_SLICE5_CHANGED_PATHS
    | PHASE41_SLICE6_CHANGED_PATHS
    | PHASE41_SLICE2_REPAIR_HASH_LOCK_CHANGED_PATHS
)
# Preserve the historical exported name because legacy Phase 37-40 dirty-tree
# guards import it directly; the Phase 41 paths are named Gate 2 carry-over
# files, not original Phase 37/38/39/40 slice files.
ALLOWED_SLICE3_CHANGED_PATHS = ALLOWED_PHASE41_SLICE1_REPAIR_CHANGED_PATHS


def _non_slice3_repair_diff_paths(diff_output: str) -> set[str]:
    return {
        path
        for path in diff_output.splitlines()
        if path and path not in ALLOWED_SLICE3_CHANGED_PATHS
    }


def _non_slice3_repair_status_paths(status_output: str) -> set[str]:
    return {
        _status_path(line)
        for line in status_output.splitlines()
        if line and _status_path(line) not in ALLOWED_SLICE3_CHANGED_PATHS
    }


FORBIDDEN_DIFF_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    "src",
    "grammar",
    "src/pietto/generated",
    "fixtures",
    "tests/fixtures",
    "scripts",
    ".github/workflows",
    "pyproject.toml",
    "uv.lock",
)

POSITIVE_RELEASE_CLAIMS = (
    "tag created",
    "release created",
    "package release occurred",
    "published package",
    "uploaded package",
    "signing completed",
    "attestation completed",
    "release operation occurred",
)


def _plan() -> str:
    return _normalized(PLAN_PATH)


def _phase38_evidence() -> str:
    return " ".join(
        _normalized(REPO_ROOT / relative_path)
        for relative_path in PHASE38_ARTIFACT_PATHS
    )


def _implementation_evidence() -> str:
    return " ".join(
        _normalized(path)
        for path in (
            PLAN_PATH,
            COUNT_FAMILY_SPEC_PATH,
            TYPE_CAPABILITY_SPEC_PATH,
            DISTINCT_ORDERING_SPEC_PATH,
            BINDING_ROADMAP_SPEC_PATH,
            SEMANTIC_AGGREGATES_PATH,
            SEMANTIC_RELATION_SCHEMAS_PATH,
            SEMANTIC_GROUP_BY_PATH,
            IR_MODEL_PATH,
            IR_LOWERING_PATH,
            POSTGRES_EXPRESSIONS_PATH,
            MYSQL_EXPRESSIONS_PATH,
            GRAMMAR_PATH,
            PACKAGE_SMOKE_PATH,
        )
    )


def _git_status() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    return [line for line in result.stdout.splitlines() if line]


def _git_status_for(paths: tuple[str, ...]) -> str:
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all", "--", *paths],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    return result.stdout.strip()


def _status_path(line: str) -> str:
    if len(line) > 2 and line[2] == " ":
        return line[3:]
    return line.split(maxsplit=1)[1]


def _path_matches(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(f"{prefix}/")


def test_phase39_slice1_plan_exists_and_records_trusted_handoff() -> None:
    assert PLAN_PATH.is_file()
    plan = _plan()

    for required in (
        "Phase 39 Slice 1 is Candidate Decision And Implementation Readiness Scope",
        "docs/plan/static-audit/tests-only",
        "implements no behavior change",
        "baseline HEAD: `ee254bc48237a11cb6fb17493d5838a04fdce6d5`",
        "baseline branch: `main`",
        "baseline commit: `Complete Phase 38 aggregate semantics audit`",
        "latest completed phase: Phase 38 Aggregate Semantics And Type Capability Consolidation",
        "package version remains `0.1.0`",
        "no tag/release/publish/upload/signing/attestation is authorized by Slice 1",
    ):
        assert required in plan, required


def test_phase38_artifact_inventory_is_confirmed() -> None:
    for relative_path in PHASE38_ARTIFACT_PATHS:
        assert (REPO_ROOT / relative_path).is_file(), relative_path

    evidence = _phase38_evidence()
    for required in (
        "Phase 38 Slice 7 is Completion Audit And Public Surface Lock",
        "Phase 38 is complete as docs/plan/spec/static-audit and tests-only work",
        "Phase 38 Slice 2 is Count Family Semantics Contract",
        "Phase 38 Slice 3 is Type Capability Matrix Contract",
        "Phase 38 Slice 4 is Any / Json / Bytes / Enum / UUID Capability Boundary",
        "Phase 38 Slice 5 is Distinct / Collation / Ordering Readiness",
        "Phase 38 Slice 6 is Binding / Aggregate Filter / Post-Aggregate Roadmap",
        "`count(expression)`, `count(constant)`, `count(1)`, and `count_if(predicate)`",
        "broad `count_distinct(expression)`",
        "`min/max(expression)`",
        "post-aggregate expression composition, relation-layer IR, subquery lowering",
    ):
        assert required in evidence, required


def test_historical_phase37_phase39_label_is_superseded_without_editing_it() -> None:
    phase37_plan = _normalized(PHASE37_PLAN_PATH)
    phase39_plan = _plan()

    assert (
        "Phase 39: Public Developer Experience And Example Gallery MVP" in phase37_plan
    )
    assert "historical roadmap text only" in phase39_plan
    assert "supersedes that old future label for current work" in phase39_plan
    assert "does not edit locked Phase 37 artifacts" in phase39_plan


def test_candidate_decision_sections_and_allowlist_are_locked() -> None:
    plan = _plan()

    for required in (
        "## Candidate Decision",
        "## Phase 38 Artifact Handoff",
        "## Repo-Derived Implementation Inventory",
        "## Candidate Readiness Matrix",
        "## Future `count(expression)` Candidate Boundary",
        "## Phase 39 Slice Sequence",
        "## Slice 1 Public Surface Constraints",
        "## Validation Plan And Gate 2 Allowlist",
        "Count family implementation candidate and aggregate semantics implementation readiness",
        "Approved Slice 1 Gate 2 file allowlist:",
        "docs/plan/phase-39-count-family-implementation-candidate.md",
        "tests/test_phase39_candidate_decision.py",
        "`/tmp/phase39-slice1-gate2-evidence.txt`",
    ):
        assert required in plan, required


def test_repo_implementation_inventory_is_evidence_backed() -> None:
    evidence = _implementation_evidence()

    for required in (
        "expected_semantic_aggregate_arities",
        "return (0, 1)",
        "def is_supported_count_argument",
        "TypeKind.ENUM",
        'not _is_builtin(value_type, "Any")',
        "deferred_argument_expression_diagnostic",
        "is_supported_semantic_aggregate_argument_expression",
        "Validate the direct aliased no-GROUP aggregate projection shape",
        "project_grouped_schema",
        "class AggregateCallIR",
        "arguments: tuple[ExpressionIR, ...]",
        "class RelationIR",
        "result_predicate: ResultPredicateIR | None = None",
        "_is_valid_aggregate_projection",
        "_aggregate_type_matches_ir",
        'return "COUNT(*)"',
        "PostgreSQL aggregate count expects a direct field argument",
        "MySQL aggregate count expects a direct field argument",
        "primaryExpression",
        "dottedName callSuffix?",
        "installed CLI explain JSON",
    ):
        assert required in evidence, required

    assert "RelationLayerIR" not in _read(IR_MODEL_PATH)


def test_candidate_matrix_keeps_slice1_readiness_only() -> None:
    plan = _plan()

    for required in (
        "| `count(expression)` | Later narrow behavior candidate only.",
        "Best candidate after Phase 38",
        "| `count(1)` / `count(constant)` | Defer.",
        "| `count_if(predicate)` | Defer.",
        "| `count(Enum field)` | Defer/reject for now.",
        "Current `PIE-S2314` fail-closed behavior is intentional",
        "| `count(Any field)` | Reject for now.",
        "`Any` remains opaque/top/deferred",
        "| current `count(Json/Bytes/UUID field)` | Hardening only; no behavior change.",
        "| broad `count_distinct(expression)` | Defer.",
        "equality, distinct compatibility, collation, normalization, serialization",
        "| `min/max(expression)` | Defer.",
        "known concrete orderable result type",
        "| broad `sum/avg(expression)` | Defer.",
        "| aggregate filters | Defer.",
        "| post-aggregate expressions / `RelationLayerIR` | Defer.",
    ):
        assert required in plan, required

    assert "Slice 1 implements `count(expression)`" not in plan
    assert "Slice 1 implements `count_if(predicate)`" not in plan


def test_future_count_expression_boundary_is_narrow_and_not_implemented() -> None:
    plan = _plan()

    for required in (
        "If a later slice separately approves `count(expression)`",
        "direct aliased aggregate projections only",
        "no-GROUP and grouped contexts only",
        "expression must include at least one resolved direct input field leaf",
        "known, concrete, non-`Any`, non-Enum, and non-Unknown",
        "SQL semantics count non-`NULL` expression results",
        "result remains `Int not null`",
        "current `count()` and direct `count(field)` SQL bytes remain compatible",
        "unsupported shapes fail closed before SQL rendering",
        "explicitly excludes `count(1)`, literal-only expressions",
        "projection aliases as aggregate argument leaves",
        "nested aggregates",
        "aggregate composition",
        "runtime/database execution",
    ):
        assert required in plan, required


def test_phase39_slice_sequence_is_locked() -> None:
    plan = _plan()

    for required in (
        "| 1 | Candidate Decision And Implementation Readiness Scope | docs/plan/static-audit/tests-only; no behavior change |",
        "| 2 | Count Expression MVP Contract | docs/spec/static-audit first; no behavior change unless separately approved |",
        "| 3 | Count Expression Semantic MVP | semantic acceptance only for the approved narrow `count(expression)` boundary |",
        "| 4 | Count Expression IR Lowering MVP | IR lowering for the semantically approved `count(expression)` subset |",
        "| 5 | Count Expression SQL Lowering MVP | PostgreSQL/private MySQL lowering for the approved IR subset |",
        "| 6 | Count Expression CLI / JSON / Golden Compatibility | CLI, JSON, fixture, and golden compatibility for the approved behavior |",
        "| 7 | Count Family Boundary Regression Matrix | regression matrix for count-family acceptance and exclusions |",
        "| 8 | Completion Audit And Status Lock | audit/status; no new behavior unless a prior slice separately approved implementation |",
        "Later phases or separately approved slices must handle `count(1)`",
        "`count_if(predicate)`, broad `count_distinct(expression)`, `min/max(expression)`",
        "`RelationLayerIR`",
    ):
        assert required in plan, required


def test_public_surface_and_release_non_authorization_are_locked() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]
    plan = _plan()

    for required in (
        "source/compiler behavior unchanged",
        "grammar and generated parser inventory unchanged",
        "parser and AST behavior unchanged",
        "semantic behavior unchanged",
        "IR behavior unchanged",
        "SQL behavior unchanged",
        "CLI text output unchanged",
        "CLI JSON v1 unchanged",
        "Project JSON v2 unchanged",
        "Semantic Metadata Artifact v1 unchanged",
        "diagnostic envelope unchanged",
        "SQL golden bytes unchanged",
        "fixtures/goldens unchanged",
        "scripts/workflows unchanged",
        "package metadata unchanged",
        "package version remains `0.1.0`",
        "no tag/release/publish/upload/signing/attestation",
    ):
        assert required in plan, required

    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert 'version = "0.2.0"' not in _read(PYPROJECT_PATH)

    lowered_plan = plan.lower()
    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in lowered_plan, forbidden


def test_forbidden_surfaces_are_documented_and_unchanged_or_untracked() -> None:
    plan = _plan()

    for required in (
        "`README.md`",
        "`AGENTS.md`",
        "`docs/spec/pietto-v0.9.md`",
        "`src/`",
        "`grammar/`",
        "`src/pietto/generated/`",
        "`fixtures/`",
        "`tests/fixtures/`",
        "`scripts/`",
        "`.github/workflows/`",
        "`pyproject.toml`",
        "`uv.lock`",
    ):
        assert required in plan, required

    diff_paths = set(
        filter(
            None,
            _git_diff_name_only(REPO_ROOT, FORBIDDEN_DIFF_PATHS).splitlines(),
        )
    )
    status_paths = {
        _status_path(line)
        for line in _git_status_for(FORBIDDEN_DIFF_PATHS).splitlines()
        if line
    }

    assert diff_paths <= ALLOWED_SLICE3_CHANGED_PATHS
    assert status_paths <= ALLOWED_SLICE3_CHANGED_PATHS


def test_changed_set_is_current_slice_allowlist_or_clean_ci_checkout() -> None:
    status_paths = {_status_path(line) for line in _git_status()}

    # Accept both clean CI checkout and dirty Gate 2 working trees.
    assert status_paths <= ALLOWED_SLICE3_CHANGED_PATHS

    for forbidden in FORBIDDEN_DIFF_PATHS:
        assert not any(
            _path_matches(path, forbidden) and path not in ALLOWED_SLICE3_CHANGED_PATHS
            for path in status_paths
        )
