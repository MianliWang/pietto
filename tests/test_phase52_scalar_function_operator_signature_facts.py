from __future__ import annotations

import ast
import hashlib
import re
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest

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
from pietto.semantic.catalog import BUILTIN_FUNCTIONS


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_REL = "src/pietto/semantic/capability_signatures.py"
SPEC_REL = "docs/spec/phase52-scalar-function-operator-signature-facts-v1.md"
SELF_REL = "tests/test_phase52_scalar_function_operator_signature_facts.py"
CONTEXT_REL = "src/pietto/semantic/capability_contexts.py"
CONTEXT_SPEC_REL = "docs/spec/phase52-expression-stage-clause-capability-facts-v1.md"
CONTEXT_TEST_REL = "tests/test_phase52_expression_stage_clause_capability_facts.py"
FACTS_REL = "src/pietto/semantic/capability_facts.py"
LOOKUP_REL = "src/pietto/semantic/capability_lookup.py"
INVENTORY_REL = "src/pietto/semantic/capability_inventory.py"
SLICE2_TEST_REL = "tests/test_phase52_private_capability_fact_foundation.py"
SLICE3_TEST_REL = "tests/test_phase52_fail_closed_capability_lookup.py"
SLICE4_TEST_REL = (
    "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py"
)
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
AGGREGATE_REL = "src/pietto/semantic/capability_aggregates.py"
SOURCE_PATH = REPO_ROOT / SOURCE_REL
SPEC_PATH = REPO_ROOT / SPEC_REL
SELF_PATH = REPO_ROOT / SELF_REL
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
REPAIR_BASE_HEAD_SHA = "b1d5002fb48dbbb06cc93de2261e2237655e0eab"
PR_REPAIR_GATE2_BRANCH = "dependabot/uv/uv-build-gte-0.11.29-and-lt-0.12.0"
PR_REPAIR_GATE2_HEAD_SHA = "8538e9e612c4a39b93a43f85532bfcb75853f9c1"
PR_REPAIR_GATE2_MAIN_SHA = "522ce4ea193c3b2bbbe88644d77a2410230f42ad"
PR_REPAIR_GATE2_ORIGIN_REF = f"refs/remotes/origin/{PR_REPAIR_GATE2_BRANCH}"

FACTS_SHA256 = "bd68bad4e13a2b945962458fc47359a408d27b1563ba25f5713a8f8099671d21"
LOOKUP_SHA256 = "4d4c2676b3181758f01c95ca312fd0f76cebcb74ac1bcab0deefb15fc04abf26"
INVENTORY_SHA256 = "f11eee2a53fda26057c35be047bfa265c68794ad76054bc5636781f0b5164b26"
PROJECT_PRIVATE_DIGEST = (
    "327ba4f5c12d916d6577cd9510aa2a28df8519dafdc935ae67a6d2f5b2fc4830"
)
TIER2_MANIFEST_BYTES = 18319
TIER2_MANIFEST_FILES = 108
TIER2_MANIFEST_SHA256 = (
    "aea0deb90e0870740b40614fc911ad9483cb3851842aa9a4a9ccecc63baf6f79"
)

SPEC_H2 = (
    "Status And Authority",
    "Private Signature Module And Ordering",
    "Signature Key Encoding And Completeness",
    "Scalar Function Signature Facts",
    "Unary Operator Signature Facts",
    "Binary Operator Signature Facts",
    "Comparison Signature Facts",
    "Null Test Signature Facts",
    "Result Nullability And Conflict Ledger",
    "Evidence Scope And Backend Boundaries",
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
    SLICE2_TEST_REL,
    SLICE3_TEST_REL,
    SLICE4_TEST_REL,
    SELF_REL,
)
ADDED_PATHS = {CONTEXT_REL, CONTEXT_SPEC_REL, CONTEXT_TEST_REL}
SLICE8_MODIFIED_PATHS = {
    SLICE4_TEST_REL,
    SELF_REL,
    CONTEXT_TEST_REL,
    SLICE7_TEST_REL,
}
SLICE8_ADDED_PATHS = {SLICE8_SPEC_REL, SLICE8_TEST_REL}
SLICE9_MODIFIED_PATHS = {
    "docs/plan/phase-52-core-type-system-capability-foundation.md",
    "docs/spec/pietto-active-roadmap-phase51-60-v1.md",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py",
    SELF_REL,
    CONTEXT_TEST_REL,
    SLICE7_TEST_REL,
    SLICE8_TEST_REL,
}
SLICE9_ADDED_PATHS = {SLICE9_SPEC_REL, SLICE9_TEST_REL}

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


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _digest(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(REPO_ROOT).as_posix()):
        relative = path.relative_to(REPO_ROOT).as_posix()
        digest.update(relative.encode("utf-8"))
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


def _facts(name: str) -> tuple[CapabilityFact, ...]:
    return cast(tuple[CapabilityFact, ...], getattr(capability_signatures, name))


def _all_facts() -> tuple[CapabilityFact, ...]:
    return _facts("_CAPABILITY_SIGNATURE_FACTS")


def _inputs(
    key: CapabilityKey,
) -> tuple[tuple[CapabilityFact, ...], bool, CapabilityReasonCode | None]:
    helper = cast(Any, getattr(capability_signatures, "signature_lookup_inputs"))
    return cast(
        tuple[tuple[CapabilityFact, ...], bool, CapabilityReasonCode | None],
        helper(key),
    )


def _lookup(key: CapabilityKey) -> Found | Absent | Unknown | Conflict:
    facts, complete, reason = _inputs(key)
    return lookup_capability(
        key,
        facts,
        domain_complete=complete,
        unknown_reason=reason,
    )


def _assert_fact(
    fact: CapabilityFact,
    domain: CapabilityDomain,
    subject: str,
    operation: str,
    operands: tuple[str, ...],
) -> None:
    assert fact.key == CapabilityKey(
        domain,
        subject=subject,
        operation=operation,
        operands=operands,
        context="expression",
    )
    assert fact.support is CapabilitySupport.SUPPORTED
    assert fact.disposition.kind is CapabilityDispositionKind.NONE
    assert fact.disposition.owner is None
    assert fact.disposition.reason is None


def _pytest_shape(path: Path) -> tuple[int, int, list[str]]:
    tree = ast.parse(_read(path), filename=path.as_posix())
    tests = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    ]
    item_count = len(tests)
    parametrized: list[str] = []
    for test in tests:
        for decorator in test.decorator_list:
            if (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr == "parametrize"
            ):
                ids = next(
                    keyword.value
                    for keyword in decorator.keywords
                    if keyword.arg == "ids"
                )
                assert isinstance(ids, (ast.Tuple, ast.List))
                item_count += len(ids.elts) - 1
                parametrized.append(test.name)
    return len(tests), item_count, parametrized


def test_private_module_api_and_dependency_shape_is_exact() -> None:
    source = _read(SOURCE_PATH)
    tree = ast.parse(source, filename=SOURCE_REL)
    assert capability_signatures.__all__ == ()
    assert not any(isinstance(node, ast.ClassDef) for node in tree.body)
    imports = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module != "__future__"
    }
    assert imports == {"collections.abc", "pietto.semantic.capability_facts"}
    assert "capability_lookup" not in source
    assert "lookup_capability" not in source
    assert "CapabilityDomain.NULLABILITY" not in source
    for forbidden in ("rglob(", "getenv(", "environ", "open(", "registry", "cache"):
        assert forbidden not in source.lower()
    with pytest.raises(ValueError, match="exact capability key"):
        cast(Any, capability_signatures.signature_lookup_inputs)("comparison")


def test_signature_family_counts_order_and_combined_tuple_are_exact() -> None:
    scalar = _facts("_SCALAR_FUNCTION_FACTS")
    unary = _facts("_UNARY_OPERATOR_FACTS")
    binary = _facts("_BINARY_OPERATOR_FACTS")
    comparison = _facts("_COMPARISON_FACTS")
    null_test = _facts("_NULL_TEST_FACTS")
    combined = _all_facts()
    assert tuple(map(len, (scalar, unary, binary, comparison, null_test))) == (
        4,
        4,
        21,
        8,
        2,
    )
    assert combined == (*scalar, *unary, *binary, *comparison, *null_test)
    assert len(combined) == len(set(combined)) == 39
    assert tuple(fact.key.domain for fact in combined) == (
        *(CapabilityDomain.SCALAR_FUNCTION for _ in range(4)),
        *(CapabilityDomain.UNARY_OPERATOR for _ in range(4)),
        *(CapabilityDomain.BINARY_OPERATOR for _ in range(21)),
        *(CapabilityDomain.COMPARISON for _ in range(8)),
        *(CapabilityDomain.NULL_TEST for _ in range(2)),
    )


def test_freeze_rejects_exact_duplicates_and_preserves_same_key_distinct_facts() -> (
    None
):
    freeze = cast(Any, getattr(capability_signatures, "_freeze_signatures"))
    fact = _all_facts()[0]
    with pytest.raises(ValueError, match="duplicate"):
        freeze((fact, fact))
    conflicting = replace(fact, support=CapabilitySupport.EXPLICITLY_UNSUPPORTED)
    assert freeze((fact, conflicting)) == (fact, conflicting)


def test_fixed_tail_key_encoding_preserves_identity_arity_result_and_nullability() -> (
    None
):
    for fact in _all_facts():
        key = fact.key
        assert key.subject is not None
        assert len(key.operands) >= 2
        remaining_inputs = key.operands[:-2]
        result_type = key.operands[-2]
        result_nullability = key.operands[-1]
        inputs = (key.subject, *remaining_inputs)
        assert all(inputs)
        assert result_type in {"Int", "Float", "Decimal", "Text", "Bool"}
        assert result_nullability in {"unknown", "non_null", "preserve_operand"}
        assert key.context == "expression"
        assert key.dialect is None
        assert key.extension is None


@pytest.mark.parametrize(
    ("index", "subject", "operation", "operands"),
    (
        (0, "Text", "lower", ("Text", "unknown")),
        (1, "Text", "trim", ("Text", "unknown")),
        (2, "Text", "len", ("Int", "unknown")),
        (3, "Text", "matches", ("Text", "Bool", "unknown")),
    ),
    ids=("lower", "trim", "len", "matches"),
)
def test_scalar_function_fact_is_exact(
    index: int,
    subject: str,
    operation: str,
    operands: tuple[str, ...],
) -> None:
    _assert_fact(
        _facts("_SCALAR_FUNCTION_FACTS")[index],
        CapabilityDomain.SCALAR_FUNCTION,
        subject,
        operation,
        operands,
    )


@pytest.mark.parametrize(
    ("index", "subject", "operation", "operands"),
    (
        (0, "Int", "+", ("Int", "preserve_operand")),
        (1, "Float", "+", ("Float", "preserve_operand")),
        (2, "Int", "-", ("Int", "preserve_operand")),
        (3, "Float", "-", ("Float", "preserve_operand")),
    ),
    ids=("int-plus", "float-plus", "int-minus", "float-minus"),
)
def test_unary_operator_fact_is_exact(
    index: int,
    subject: str,
    operation: str,
    operands: tuple[str, ...],
) -> None:
    _assert_fact(
        _facts("_UNARY_OPERATOR_FACTS")[index],
        CapabilityDomain.UNARY_OPERATOR,
        subject,
        operation,
        operands,
    )


@pytest.mark.parametrize(
    ("index", "subject", "operation", "operands"),
    (
        (0, "Int", "+", ("Int", "Int", "unknown")),
        (1, "Int", "+", ("Float", "Float", "unknown")),
        (2, "Float", "+", ("Int", "Float", "unknown")),
        (3, "Float", "+", ("Float", "Float", "unknown")),
        (4, "Decimal", "+", ("Decimal", "Decimal", "unknown")),
        (5, "Decimal", "+", ("Int", "Decimal", "unknown")),
        (6, "Int", "+", ("Decimal", "Decimal", "unknown")),
        (7, "Int", "-", ("Int", "Int", "unknown")),
        (8, "Int", "-", ("Float", "Float", "unknown")),
        (9, "Float", "-", ("Int", "Float", "unknown")),
        (10, "Float", "-", ("Float", "Float", "unknown")),
        (11, "Decimal", "-", ("Decimal", "Decimal", "unknown")),
        (12, "Decimal", "-", ("Int", "Decimal", "unknown")),
        (13, "Int", "-", ("Decimal", "Decimal", "unknown")),
        (14, "Int", "*", ("Int", "Int", "unknown")),
        (15, "Int", "*", ("Float", "Float", "unknown")),
        (16, "Float", "*", ("Int", "Float", "unknown")),
        (17, "Float", "*", ("Float", "Float", "unknown")),
        (18, "Int", "%", ("Int", "Int", "unknown")),
        (19, "Bool", "and", ("Bool", "Bool", "unknown")),
        (20, "Bool", "or", ("Bool", "Bool", "unknown")),
    ),
    ids=(
        "int-add-int",
        "int-add-float",
        "float-add-int",
        "float-add-float",
        "decimal-add-decimal",
        "decimal-add-int",
        "int-add-decimal",
        "int-sub-int",
        "int-sub-float",
        "float-sub-int",
        "float-sub-float",
        "decimal-sub-decimal",
        "decimal-sub-int",
        "int-sub-decimal",
        "int-mul-int",
        "int-mul-float",
        "float-mul-int",
        "float-mul-float",
        "int-mod-int",
        "bool-and-bool",
        "bool-or-bool",
    ),
)
def test_binary_operator_fact_is_exact(
    index: int,
    subject: str,
    operation: str,
    operands: tuple[str, ...],
) -> None:
    _assert_fact(
        _facts("_BINARY_OPERATOR_FACTS")[index],
        CapabilityDomain.BINARY_OPERATOR,
        subject,
        operation,
        operands,
    )


@pytest.mark.parametrize(
    ("index", "subject", "operation", "operands"),
    (
        (0, "Expression", "==", ("Expression", "Bool", "unknown")),
        (1, "Expression", "!=", ("Expression", "Bool", "unknown")),
        (2, "Expression", "<", ("Expression", "Bool", "unknown")),
        (3, "Expression", "<=", ("Expression", "Bool", "unknown")),
        (4, "Expression", ">", ("Expression", "Bool", "unknown")),
        (5, "Expression", ">=", ("Expression", "Bool", "unknown")),
        (6, "Expression", "like", ("Expression", "Bool", "unknown")),
        (
            7,
            "ValueTypeKind.KNOWN",
            "between",
            (
                "ValueTypeKind.KNOWN",
                "ValueTypeKind.KNOWN",
                "Bool",
                "unknown",
            ),
        ),
    ),
    ids=("eq", "ne", "lt", "le", "gt", "ge", "like", "between"),
)
def test_comparison_fact_is_exact(
    index: int,
    subject: str,
    operation: str,
    operands: tuple[str, ...],
) -> None:
    _assert_fact(
        _facts("_COMPARISON_FACTS")[index],
        CapabilityDomain.COMPARISON,
        subject,
        operation,
        operands,
    )


@pytest.mark.parametrize(
    ("index", "operation"),
    ((0, "is null"), (1, "is not null")),
    ids=("is-null", "is-not-null"),
)
def test_null_test_fact_is_exact(index: int, operation: str) -> None:
    _assert_fact(
        _facts("_NULL_TEST_FACTS")[index],
        CapabilityDomain.NULL_TEST,
        "Expression",
        operation,
        ("Bool", "non_null"),
    )


def test_scalar_catalog_excludes_aggregates_connectors_and_user_callables() -> None:
    facts = _facts("_SCALAR_FUNCTION_FACTS")
    assert tuple(BUILTIN_FUNCTIONS) == ("lower", "trim", "len", "matches")
    assert tuple(fact.key.operation for fact in facts) == tuple(BUILTIN_FUNCTIONS)
    excluded = {
        "count",
        "count_distinct",
        "sum",
        "avg",
        "min",
        "max",
        "connector",
        "user_callable",
    }
    assert excluded.isdisjoint({fact.key.operation for fact in facts})


def test_like_and_matches_backend_ledgers_are_scoped_without_precedence() -> None:
    matches = _facts("_SCALAR_FUNCTION_FACTS")[-1]
    like = _facts("_COMPARISON_FACTS")[-2]
    for fact in (matches, like):
        assert fact.key.dialect is None
        assert fact.key.extension is None
        backends = tuple(
            entry
            for entry in fact.evidence
            if entry.source is CapabilityEvidenceSource.BACKEND
        )
        assert tuple((entry.dialect, entry.backend) for entry in backends) == (
            ("postgresql", "postgresql"),
            ("mysql", "private-mysql"),
        )
    match_backends = tuple(
        entry
        for entry in matches.evidence
        if entry.source is CapabilityEvidenceSource.BACKEND
    )
    assert tuple(entry.reason for entry in match_backends) == (
        None,
        CapabilityReasonCode.DIALECT_LOWERING_GAP,
    )
    like_backends = tuple(
        entry
        for entry in like.evidence
        if entry.source is CapabilityEvidenceSource.BACKEND
    )
    assert all(
        entry.reason is CapabilityReasonCode.DIALECT_LOWERING_GAP
        for entry in like_backends
    )


@pytest.mark.parametrize(
    "key",
    (
        CapabilityKey(
            CapabilityDomain.BINARY_OPERATOR,
            subject="Int",
            operation="/",
            operands=("Int", "Int", "unknown"),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.BINARY_OPERATOR,
            subject="Decimal",
            operation="*",
            operands=("Decimal", "Decimal", "unknown"),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.BINARY_OPERATOR,
            subject="Text",
            operation="+",
            operands=("Text", "Text", "unknown"),
            context="expression",
        ),
    ),
    ids=("division", "decimal-multiply", "text-concatenation"),
)
def test_omitted_operator_family_remains_incomplete(key: CapabilityKey) -> None:
    facts, complete, _ = _inputs(key)
    assert facts is _facts("_BINARY_OPERATOR_FACTS")
    assert complete is False
    assert isinstance(_lookup(key), Unknown)


def test_generic_comparison_and_between_do_not_claim_concrete_pair_compatibility() -> (
    None
):
    concrete = CapabilityKey(
        CapabilityDomain.COMPARISON,
        subject="Int",
        operation="==",
        operands=("Int", "Bool", "unknown"),
        context="expression",
    )
    unknown_child = CapabilityKey(
        CapabilityDomain.COMPARISON,
        subject="ValueTypeKind.KNOWN",
        operation="between",
        operands=(
            "ValueTypeKind.UNKNOWN",
            "ValueTypeKind.KNOWN",
            "Bool",
            "unknown",
        ),
        context="expression",
    )
    for key in (concrete, unknown_child):
        facts, complete, reason = _inputs(key)
        assert facts is _facts("_COMPARISON_FACTS")
        assert complete is False
        assert reason is None
        assert _lookup(key) == Unknown(CapabilityReasonCode.NOT_EVIDENCED)


def test_null_tests_preserve_non_null_bool_and_distinct_three_valued_truth() -> None:
    for fact in _facts("_NULL_TEST_FACTS"):
        assert fact.key.operands == ("Bool", "non_null")
        reasons = {entry.reason for entry in fact.evidence}
        assert CapabilityReasonCode.NULL_LITERAL_NO_CONCRETE_TYPE in reasons
        assert CapabilityReasonCode.SQL_THREE_VALUED_TRUTH in reasons
        assert CapabilityReasonCode.UNKNOWN_NULLABILITY not in reasons
    assert "Null" not in {
        fact.key.subject for fact in _all_facts() if fact.key.subject is not None
    }


def test_evidence_order_uniqueness_and_paths_are_exact() -> None:
    source_order = {
        source: index
        for index, source in enumerate(
            (
                CapabilityEvidenceSource.GRAMMAR_AST,
                CapabilityEvidenceSource.SEMANTIC_CATALOG,
                CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                CapabilityEvidenceSource.SEMANTIC_MODEL,
                CapabilityEvidenceSource.IR,
                CapabilityEvidenceSource.BACKEND,
                CapabilityEvidenceSource.PROJECT,
                CapabilityEvidenceSource.PUBLIC,
                CapabilityEvidenceSource.ROADMAP,
                CapabilityEvidenceSource.TEST,
                CapabilityEvidenceSource.SPEC,
            )
        )
    }
    allowed_reasons = {
        None,
        CapabilityReasonCode.UNKNOWN_NULLABILITY,
        CapabilityReasonCode.DIALECT_LOWERING_GAP,
        CapabilityReasonCode.SQL_THREE_VALUED_TRUTH,
        CapabilityReasonCode.NULL_LITERAL_NO_CONCRETE_TYPE,
    }
    for fact in _all_facts():
        evidence = fact.evidence
        assert len(evidence) == len(set(evidence))
        assert tuple(source_order[item.source] for item in evidence) == tuple(
            sorted(source_order[item.source] for item in evidence)
        )
        assert all((REPO_ROOT / item.source_path).is_file() for item in evidence)
        assert all(item.extension is None for item in evidence)
        assert all(item.reason in allowed_reasons for item in evidence)
        assert not any(
            item.source
            in {CapabilityEvidenceSource.PROJECT, CapabilityEvidenceSource.PUBLIC}
            for item in evidence
        )
        backends = tuple(
            item for item in evidence if item.source is CapabilityEvidenceSource.BACKEND
        )
        assert tuple((item.dialect, item.backend) for item in backends) == (
            ("postgresql", "postgresql"),
            ("mysql", "private-mysql"),
        )


def test_signature_completeness_schemas_are_exact() -> None:
    complete_absences = (
        CapabilityKey(
            CapabilityDomain.SCALAR_FUNCTION,
            subject="Text",
            operation="upper",
            operands=("Text", "unknown"),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.UNARY_OPERATOR,
            subject="Int",
            operation="+",
            operands=("Float", "preserve_operand"),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.BINARY_OPERATOR,
            subject="Int",
            operation="+",
            operands=("Int", "Float", "unknown"),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.COMPARISON,
            subject="Expression",
            operation="==",
            operands=("Expression", "Text", "unknown"),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.COMPARISON,
            subject="ValueTypeKind.KNOWN",
            operation="between",
            operands=(
                "ValueTypeKind.KNOWN",
                "ValueTypeKind.KNOWN",
                "Text",
                "unknown",
            ),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.NULL_TEST,
            subject="Expression",
            operation="is null",
            operands=("Text", "non_null"),
            context="expression",
        ),
    )
    assert all(_inputs(key)[1:] == (True, None) for key in complete_absences)
    incomplete = (
        replace(complete_absences[0], dialect="postgresql"),
        replace(
            complete_absences[0],
            dialect="postgresql",
            extension="future",
        ),
        replace(complete_absences[0], subject="text"),
        replace(complete_absences[0], operands=("Bogus", "unknown")),
        replace(
            complete_absences[0],
            operands=("Text", "Bogus", "unknown"),
        ),
        replace(complete_absences[0], operands=("Text",)),
        replace(
            complete_absences[0],
            operands=("Text", "unknown", "Bogus"),
        ),
        replace(complete_absences[1], operands=("Int", "unknown")),
        replace(complete_absences[1], operands=("Bogus", "preserve_operand")),
        replace(complete_absences[1], operands=("int", "preserve_operand")),
        replace(
            complete_absences[1],
            operands=("Int", "preserve_operand", "extra"),
        ),
        replace(complete_absences[2], context="where"),
        replace(complete_absences[2], operands=("Int", "Bogus", "unknown")),
        replace(
            complete_absences[3],
            operands=("Expression", "Bogus", "unknown"),
        ),
        replace(
            complete_absences[4],
            operands=(
                "ValueTypeKind.KNOWN",
                "ValueTypeKind.KNOWN",
                "Bogus",
                "unknown",
            ),
        ),
        replace(complete_absences[5], operands=("Bogus", "non_null")),
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject="Int",
            operation="sum",
            operands=("Int", "unknown"),
            context="expression",
        ),
    )
    assert all(_inputs(key)[1:] == (False, None) for key in incomplete)


def test_all_inventory_keys_lookup_as_found() -> None:
    for fact in _all_facts():
        result = _lookup(fact.key)
        assert result == Found(fact)
        assert isinstance(result, Found)
        assert result.fact is fact


def test_complete_schema_zero_match_lookup_is_absent() -> None:
    keys = (
        CapabilityKey(
            CapabilityDomain.SCALAR_FUNCTION,
            subject="Text",
            operation="upper",
            operands=("Text", "unknown"),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.SCALAR_FUNCTION,
            subject="Text",
            operation="lower",
            operands=("Text", "Text", "unknown"),
            context="expression",
        ),
        replace(
            _facts("_UNARY_OPERATOR_FACTS")[0].key,
            operands=("Float", "preserve_operand"),
        ),
        replace(
            _facts("_BINARY_OPERATOR_FACTS")[0].key,
            operands=("Int", "Float", "unknown"),
        ),
        replace(
            _facts("_COMPARISON_FACTS")[0].key,
            operands=("Expression", "Text", "unknown"),
        ),
        replace(
            _facts("_COMPARISON_FACTS")[-1].key,
            operands=(
                "ValueTypeKind.KNOWN",
                "ValueTypeKind.KNOWN",
                "Text",
                "unknown",
            ),
        ),
        replace(_facts("_NULL_TEST_FACTS")[0].key, operands=("Text", "non_null")),
    )
    assert all(_lookup(key) == Absent(key) for key in keys)


def test_incomplete_and_division_lookups_are_unknown_with_exact_reasons() -> None:
    division = CapabilityKey(
        CapabilityDomain.BINARY_OPERATOR,
        subject="Int",
        operation="/",
        operands=("Int", "Int", "unknown"),
        context="expression",
    )
    matches_mysql = replace(
        _facts("_SCALAR_FUNCTION_FACTS")[-1].key,
        dialect="mysql",
    )
    like_postgres = replace(_facts("_COMPARISON_FACTS")[-2].key, dialect="postgresql")
    like_mysql = replace(_facts("_COMPARISON_FACTS")[-2].key, dialect="mysql")
    expected = (
        (division, CapabilityReasonCode.NO_CURRENT_RESULT_RULE),
        (matches_mysql, CapabilityReasonCode.DIALECT_LOWERING_GAP),
        (like_postgres, CapabilityReasonCode.DIALECT_LOWERING_GAP),
        (like_mysql, CapabilityReasonCode.DIALECT_LOWERING_GAP),
    )
    for key, reason in expected:
        _, complete, actual_reason = _inputs(key)
        assert complete is False
        assert actual_reason is reason
        assert _lookup(key) == Unknown(reason)
    malformed = (
        replace(division, subject="Bogus"),
        replace(division, operands=("Bogus", "Int", "unknown")),
        replace(division, operands=("Int", "Bogus", "unknown")),
        replace(division, operands=("Int", "int", "unknown")),
        replace(division, operands=("Int", "Int")),
        replace(division, operands=("Int", "Int", "unknown", "extra")),
        replace(division, context="where"),
        replace(division, dialect="postgresql"),
        replace(division, dialect="postgresql", extension="future"),
        replace(matches_mysql, extension="future"),
        replace(like_postgres, extension="future"),
    )
    for key in malformed:
        _, complete, reason = _inputs(key)
        assert complete is False
        assert reason is None
        assert _lookup(key) == Unknown(CapabilityReasonCode.NOT_EVIDENCED)
    concrete = CapabilityKey(
        CapabilityDomain.COMPARISON,
        subject="Date",
        operation="==",
        operands=("Date", "Bool", "unknown"),
        context="expression",
    )
    assert _inputs(concrete)[1:] == (False, None)
    assert _lookup(concrete) == Unknown(CapabilityReasonCode.NOT_EVIDENCED)


def test_distinct_same_key_facts_lookup_as_conflict_without_precedence() -> None:
    fact = _all_facts()[0]
    conflict = replace(fact, support=CapabilitySupport.EXPLICITLY_UNSUPPORTED)
    result = lookup_capability(
        fact.key,
        (fact, conflict),
        domain_complete=True,
    )
    assert result == Conflict(
        CapabilityReasonCode.CONFLICTING_EVIDENCE,
        (fact, conflict),
    )


def test_no_aggregate_stage_clause_or_window_fact_is_present() -> None:
    forbidden_domains = {
        CapabilityDomain.AGGREGATE,
        CapabilityDomain.CLAUSE,
        CapabilityDomain.EXPRESSION_STAGE,
        CapabilityDomain.WINDOW_FUNCTION,
    }
    assert forbidden_domains.isdisjoint({fact.key.domain for fact in _all_facts()})
    assert not any(
        "window" in value for fact in _all_facts() for value in fact.key.operands
    )
    for domain in forbidden_domains:
        key = CapabilityKey(domain, subject="Expression", context="expression")
        assert _inputs(key) == ((), False, None)


def test_no_compiler_project_public_or_runtime_consumer_exists() -> None:
    preservation_path = (
        REPO_ROOT / "src/pietto/_project/module_semantic_fact_preservation.py"
    )
    for path in (REPO_ROOT / "src/pietto").rglob("*.py"):
        if path in {SOURCE_PATH, preservation_path} or "generated" in path.parts:
            continue
        source = _read(path)
        assert "semantic.capability_signatures" not in source
        assert "signature_lookup_inputs" not in source
    preservation_source = _read(preservation_path)
    assert "semantic.capability_signatures" in preservation_source
    assert "signature_lookup_inputs" in preservation_source
    assert "capability_signatures" not in _read(
        REPO_ROOT / "src/pietto/semantic/__init__.py"
    )
    assert "capability_signatures" not in _read(REPO_ROOT / "src/pietto/__init__.py")


def test_prior_phase52_private_sources_remain_byte_identical() -> None:
    expected = {
        FACTS_REL: FACTS_SHA256,
        LOOKUP_REL: LOOKUP_SHA256,
        INVENTORY_REL: INVENTORY_SHA256,
    }
    assert {
        path: hashlib.sha256((REPO_ROOT / path).read_bytes()).hexdigest()
        for path in expected
    } == expected


def test_slice4_inventory_fact_count_and_completeness_are_unchanged() -> None:
    combined = cast(
        tuple[CapabilityFact, ...],
        getattr(capability_inventory, "_CAPABILITY_FACTS"),
    )
    assert len(combined) == len(set(combined)) == 41
    helper = cast(Any, capability_inventory.inventory_lookup_inputs)
    found_key = combined[0].key
    found_inputs = helper(found_key)
    assert len(found_inputs) == 2
    assert found_inputs[1] is True
    incomplete = CapabilityKey(
        CapabilityDomain.PARAMETER,
        subject="query",
        operation="binding",
        context="runtime",
    )
    assert helper(incomplete)[1] is False


def test_spec_headings_and_required_phrases_are_exact() -> None:
    spec = _read(SPEC_PATH)
    headings = tuple(
        match.group(1).strip()
        for match in re.finditer(r"^## (?!#)(.+?)\s*$", spec, re.MULTILINE)
    )
    assert headings == SPEC_H2
    for required in (
        "exactly 39 unique `CapabilityFact` values",
        "Their zero matches are\n`Unknown`, never inferred `Absent`.",
        "PostgreSQL evidence precedes private MySQL evidence.",
        "No backend winner or semantic\noverride is selected.",
        "Package version remains `0.1.0`.",
        "Phase 52 remains active and incomplete",
        "Add Phase 52 private scalar function and operator facts",
    ):
        assert required in spec
