from __future__ import annotations

import tomllib
from pathlib import Path

from _static_audit_helpers import (
    normalized_text as _normalized,
    read_text as _read,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-41-decimal-precision-scale-mvp.md"
TEST_PATH = REPO_ROOT / "tests/test_phase41_decimal_precision_scale_candidate.py"
SLICE2_TEST_PATH = (
    REPO_ROOT / "tests/test_phase41_decimal_precision_scale_semantic_validation.py"
)
CARRIER_TEST_PATH = (
    REPO_ROOT / "tests/test_phase41_decimal_precision_scale_type_carrier.py"
)
IR_COMPAT_TEST_PATH = (
    REPO_ROOT / "tests/test_phase41_decimal_precision_scale_ir_compatibility.py"
)
AGGREGATE_NUMERIC_BOUNDARY_TEST_PATH = (
    REPO_ROOT
    / "tests/test_phase41_decimal_precision_scale_aggregate_numeric_boundary.py"
)
METADATA_CLI_COMPAT_TEST_PATH = (
    REPO_ROOT
    / "tests/test_phase41_decimal_precision_scale_metadata_cli_compatibility.py"
)
DOCS_READINESS_TEST_PATH = (
    REPO_ROOT / "tests/test_phase41_decimal_precision_scale_docs_readiness.py"
)
COMPLETION_AUDIT_TEST_PATH = (
    REPO_ROOT / "tests/test_phase41_decimal_precision_scale_completion_audit.py"
)
ANALYZER_PATH = REPO_ROOT / "src/pietto/semantic/analyzer.py"
MODEL_PATH = REPO_ROOT / "src/pietto/semantic/model.py"
SEMANTIC_API_PATH = REPO_ROOT / "src/pietto/semantic/__init__.py"
DIAGNOSTICS_PATH = REPO_ROOT / "docs/spec/diagnostics.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
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
PHASE41_SLICE7_CHANGED_PATHS = {
    "docs/plan/phase-41-decimal-precision-scale-mvp.md",
    "docs/spec/v02-deferred-feature-register-v1.md",
    "docs/spec/decimal-precision-scale-contract-v1.md",
    "docs/spec/decimal-precision-scale-metadata-carrier-readiness-v1.md",
    "docs/spec/decimal-precision-scale-carrier-mvp-decision-v1.md",
    "docs/spec/phase36-core-type-resolution-matrix-v1.md",
    "docs/spec/phase38-type-capability-matrix-contract-v1.md",
    "docs/spec/expanded-scalar-operator-matrix-v1.md",
    "tests/test_phase41_decimal_precision_scale_docs_readiness.py",
    "tests/test_phase41_decimal_precision_scale_candidate.py",
    "tests/test_phase29_v02_deferred_feature_register.py",
    "tests/test_phase29_completion_audit.py",
    "tests/test_phase30_decimal_precision_scale_contract.py",
    "tests/test_phase30_candidate_decision.py",
    "tests/test_phase30_completion_audit.py",
    "tests/test_phase36_candidate_decision.py",
    "tests/test_phase36_rescope_candidate_resolution_matrix.py",
    "tests/test_phase36_decimal_precision_scale_carrier_mvp_decision.py",
    "tests/test_phase36_expanded_scalar_operator_matrix.py",
    "tests/test_phase38_type_capability_matrix_contract.py",
    "tests/test_phase38_candidate_decision.py",
    "tests/test_phase39_candidate_decision.py",
    "tests/test_phase40_completion_audit.py",
}
PHASE41_SLICE8_CHANGED_PATHS = {
    "docs/plan/phase-41-decimal-precision-scale-mvp.md",
    "tests/test_phase41_decimal_precision_scale_completion_audit.py",
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


def test_phase41_slice1_plan_exists_and_records_trusted_handoff() -> None:
    assert PLAN_PATH.is_file()
    assert TEST_PATH.is_file()

    plan = _plan()

    for required in (
        "Phase 41 Slice 1 is Candidate Decision And Scope Lock",
        "docs/plan/static-audit/tests-only and implements no behavior change",
        "Phase 41 theme: Decimal precision-scale MVP",
        "baseline HEAD: `0244eb9cdb00a5fa97d9533377a059a2c25757b0`",
        "baseline branch: `main`",
        "baseline commit: `Complete Phase 40 let binding implementation audit`",
        "latest completed phase: Phase 40 Let Binding Model",
        "package version remains `0.1.0`",
        "no tag/release/publish/upload/signing/attestation is authorized by Slice 1",
        "Phase 40 implemented row-level `let:` only",
        "Phase 41 starts from the trusted Phase 40 handoff",
    ):
        assert required in plan, required


def test_phase41_candidate_decision_and_slice_sequence_are_locked() -> None:
    plan = _plan()

    for required in (
        "Minimal fail-closed compiler-internal Decimal precision-scale MVP",
        "Phase 41 is not a docs-only phase",
        "production implementation begins in Slice 2",
        "accept `Decimal(precision, scale)` as a semantic Decimal type form",
        "preserve plain `Decimal` and all current plain Decimal behavior",
        "store validated precision-scale facts in internal compiler type facts",
        "reject invalid precision-scale forms fail-closed",
        "keep SQL expression output unchanged",
        "keep CLI JSON v1 and Semantic Metadata Artifact v1 schemas unchanged",
        "| 1 | Candidate Decision And Scope Lock |",
        "| 2 | Decimal Precision-Scale Semantic Validation |",
        "| 3 | Internal Type Carrier MVP |",
        "| 4 | IR Compatibility Carrier Boundary |",
        "| 5 | Aggregate / Numeric Boundary Hardening |",
        "| 6 | Metadata / CLI JSON / Explain Compatibility |",
        "| 7 | Docs, Deferred Register, And Package Smoke Readiness |",
        "| 8 | Completion Audit And Status Lock |",
    ):
        assert required in plan, required

    for forbidden in (
        "Phase 41 is docs-only",
        "production implementation begins in Slice 3",
        "Slice 1 implements Decimal precision-scale semantics",
    ):
        assert forbidden not in plan


def test_repo_derived_decimal_readiness_and_no_grammar_requirement_are_locked() -> None:
    plan = _plan()

    for required in (
        "`grammar/Pietto.g4` already allows generic type arguments",
        "`TypeExpr` already stores `arguments: tuple[TypeArgument, ...]`",
        "`Decimal(12, 2)` can parse as generic `TypeExpr.arguments`",
        "current semantic resolution ignores those arguments",
        "`ResolvedType` carries only `name`, `kind`, and optional `definition`",
        "`ValueType` carries `resolved_type`, `nullability`, and `kind`",
        "No precision-scale carrier exists in semantic, IR, SQL, CLI JSON, "
        "Project JSON v2, or Semantic Metadata Artifact v1 models",
        "Slice 2 should start in semantic validation and carrier ownership, not "
        "grammar regeneration",
    ):
        assert required in plan, required


def test_decimal_semantic_validation_and_carrier_boundaries_are_locked() -> None:
    analyzer = _read(ANALYZER_PATH)
    model = _read(MODEL_PATH)
    semantic_api = _read(SEMANTIC_API_PATH)
    diagnostics = _read(DIAGNOSTICS_PATH)
    slice2_tests = _read(SLICE2_TEST_PATH)
    carrier_tests = _read(CARRIER_TEST_PATH)
    ir_compat_tests = _read(IR_COMPAT_TEST_PATH)
    aggregate_numeric_boundary_tests = _read(AGGREGATE_NUMERIC_BOUNDARY_TEST_PATH)
    metadata_cli_compat_tests = _read(METADATA_CLI_COMPAT_TEST_PATH)
    docs_readiness_tests = _read(DOCS_READINESS_TEST_PATH)
    completion_audit_tests = _read(COMPLETION_AUDIT_TEST_PATH)

    for required in (
        "_DECIMAL_PRECISION_MAX = 38",
        "def _decimal_precision_scale_fact(",
        "DecimalPrecisionScale",
        'if type_expr.name != "Decimal":',
        "if not arguments:",
        "_propagate_decimal_precision_scale_aliases",
        "PIE-S2004",
    ):
        assert required in analyzer, required

    for required in (
        "class DecimalPrecisionScale:",
        "precision: int",
        "scale: int",
        "decimal_precision_scales: Mapping[TypeExpr, DecimalPrecisionScale]",
        "def decimal_precision_scale_for(",
    ):
        assert required in model, required
    assert "DecimalPrecisionScale" not in semantic_api

    assert "| `PIE-S2004` | Invalid Decimal precision-scale type arguments |" in (
        diagnostics
    )

    for required in (
        "test_valid_decimal_precision_scale_type_arguments_remain_plain_decimal",
        "test_invalid_decimal_precision_scale_type_arguments_fail_closed",
        "test_empty_decimal_arguments_preserve_plain_decimal_compatibility",
        "test_non_decimal_type_arguments_remain_compatibility_surface",
        "test_decimal_precision_scale_validation_adds_internal_carrier_without_sql_output",
    ):
        assert required in slice2_tests, required

    for required in (
        "test_decimal_precision_scale_facts_are_stored_for_supported_type_sites",
        "test_decimal_precision_scale_facts_propagate_through_safe_alias_chains",
        "test_decimal_precision_scale_facts_skip_invalid_plain_empty_and_non_decimal",
        "test_decimal_precision_scale_carrier_does_not_expand_public_output_surfaces",
        "test_decimal_precision_scale_carrier_is_not_exported_from_semantic_api",
    ):
        assert required in carrier_tests, required

    for required in (
        "test_decimal_precision_scale_ir_type_refs_remain_logical_decimal",
        "test_decimal_precision_scale_aggregate_ir_and_sql_remain_unchanged",
        "test_alias_decimal_aggregate_boundary_remains_existing_fail_closed",
        "test_decimal_precision_scale_public_json_and_metadata_shapes_are_unchanged",
        "test_ir_layer_does_not_consume_decimal_precision_scale_carrier",
    ):
        assert required in ir_compat_tests, required

    for required in (
        "test_decimal_precision_scale_direct_aggregates_remain_logical_decimal",
        "test_decimal_precision_scale_aggregate_expressions_preserve_existing_boundary",
        "test_decimal_precision_scale_sql_output_remains_logical_and_unparameterized",
        "test_decimal_precision_scale_alias_aggregate_arguments_remain_fail_closed",
        "test_deferred_decimal_numeric_aggregate_boundaries_remain_s2315",
        "test_deferred_decimal_numeric_scalar_boundaries_remain_fail_closed",
        "test_public_type_surfaces_still_have_no_precision_scale_fields",
    ):
        assert required in aggregate_numeric_boundary_tests, required

    for required in (
        "test_check_json_valid_decimal_precision_scale_keeps_json_v1_shape",
        "test_emit_sql_json_and_output_keep_sql_unparameterized",
        "test_explain_text_keeps_logical_decimal_and_alias_type_labels",
        "test_explain_json_keeps_artifact_v1_logical_decimal_schema",
        "test_semantic_metadata_artifact_json_does_not_serialize_internal_carrier",
        "test_project_json_v2_remains_discovery_only_for_decimal_sources",
        "test_invalid_decimal_precision_scale_check_json_keeps_diagnostic_schema",
    ):
        assert required in metadata_cli_compat_tests, required

    for required in (
        "test_slice7_plan_status_records_completed_slices_without_completion_claim",
        "test_deferred_register_splits_phase41_internal_mvp_from_remaining_work",
        "test_historical_decimal_specs_have_phase41_supersession_notes",
        "test_phase38_and_scalar_matrices_reflect_internal_carrier_only",
        "test_package_smoke_readiness_is_documented_without_script_or_package_changes",
    ):
        assert required in docs_readiness_tests, required

    for required in (
        "test_phase41_final_completion_status_is_locked_in_plan",
        "test_slice1_through_slice8_outcomes_remain_represented",
        "test_completed_decimal_precision_scale_mvp_is_locked",
        "test_public_type_output_and_sql_surfaces_remain_precision_scale_free",
        "test_deferred_inventory_and_future_owners_are_locked",
        "test_package_release_workflow_and_status_boundaries_are_locked",
    ):
        assert required in completion_audit_tests, required


def test_deferred_inventory_impact_is_explicit() -> None:
    plan = _plan()

    for required in (
        "| Decimal precision-scale parse surface | Implemented by Phase 41",
        "| Decimal precision-scale semantic validation | Implemented by Phase 41",
        "| Invalid Decimal precision-scale diagnostics | Implemented by Phase 41 fail-closed",
        "| Decimal precision-scale carrier | Implemented by Phase 41 as private semantic facts",
        "| Alias-chain precision-scale facts | Implemented by Phase 41",
        "| IR compatibility | Implemented by Phase 41 as compatibility proof only",
        "| Aggregate/numeric boundary hardening | Implemented by Phase 41 as tests/static-audit proof only",
        "| CLI JSON / Project JSON v2 / explain / Artifact v1 compatibility | Implemented by Phase 41 as tests/static-audit proof only",
        "| Plain `Decimal` | Unaffected",
        "| Non-Decimal type arguments | Unaffected compatibility surface",
        "| Decimal aggregate precision propagation | Still deferred with named prerequisite",
        "| Decimal literals | Explicitly rejected in Phase 41",
        "| Full Int/Float/Decimal promotion matrix | Explicitly rejected in Phase 41",
        "| Float/Decimal mixing | Explicitly rejected in Phase 41",
        "| Decimal `*` and `/` | Still deferred with named prerequisite",
        "| Cast syntax | Explicitly rejected in Phase 41",
        "| SQL `DECIMAL(p, s)` / `NUMERIC(p, s)` output | Still deferred with named prerequisite",
        "| DDL/native DB metadata | Still deferred with named prerequisite",
        "| Public JSON precision-scale fields | Explicitly rejected in Phase 41",
        "| Metadata/explain precision-scale display | Explicitly rejected in Phase 41",
        "| Broad aggregate features | Unaffected",
    ):
        assert required in plan, required


def test_package_version_release_and_public_status_boundaries_are_locked() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]
    plan = _plan()

    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert 'version = "0.2.0"' not in _read(PYPROJECT_PATH)

    for required in (
        "Slice 1 does not update `README.md`, `AGENTS.md`",
        "`docs/spec/pietto-v0.9.md`, the deferred register, or status-lock files",
        "Status housekeeping remains future dedicated work unless separately approved",
    ):
        assert required in plan, required

    lowered = plan.lower()
    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in lowered, forbidden
