from __future__ import annotations

import ast
import enum
import hashlib
import re
import subprocess
import tomllib
from collections import Counter
from pathlib import Path
from typing import cast

from _phase54_active_gate2_manifest import (
    phase54_post_slice12_interlude_expected_head,
    phase54_publication_topic_base,
    phase54_post_slice12_interlude_repair_is_active,
    phase54_post_slice12_interlude_dirty_is_active,
    phase54_post_slice12_interlude_expected_added_paths,
    phase54_post_slice12_interlude_expected_allowlist_paths,
    phase54_post_slice12_interlude_expected_modified_paths,
    phase54_publication_clean_topic_is_active,
    phase54_publication_topic_branch,
    PHASE54_ACTIVE_GATE2_ADDED_PATHS,
    PHASE54_ACTIVE_GATE2_BASE,
    PHASE54_ACTIVE_GATE2_MODIFIED_PATHS,
    PHASE54_POST_REVIEW_PRODUCT_REPAIR1_BASE,
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_BASE,
    PHASE54_POST_REVIEW_PRODUCT_REPAIR3_BASE,
    PHASE54_POST_REVIEW_PRODUCT_REPAIR4_BASE,
    PHASE54_POST_REVIEW_PRODUCT_REPAIR5_BASE,
    PHASE54_POST_REVIEW_PRODUCT_REPAIR6_BASE,
    PHASE54_POST_REVIEW_PRODUCT_REPAIR7_BASE,
    PHASE54_POST_REVIEW_PRODUCT_REPAIR8_BASE,
    PHASE54_POST_REVIEW_PRODUCT_REPAIR9_BASE,
    PHASE54_SLICE11_PR_CI_REPAIR_BASE,
    PHASE54_SLICE11_PR_CI_REPAIR_BRANCH,
    PHASE54_SLICE11_PR_CI_REPAIR_MODIFIED_PATHS,
    PHASE54_SLICE12_PR_CI_REPAIR_BASE,
    PHASE54_SLICE12_PR_CI_REPAIR_BRANCH,
    PHASE54_SLICE12_PR_CI_REPAIR_MODIFIED_PATHS,
    PHASE54_SLICE12_MECHANICAL_REPAIR3_BASE,
    PHASE54_SLICE12_MECHANICAL_REPAIR3_BRANCH,
    PHASE54_SLICE12_MECHANICAL_REPAIR3_MODIFIED_PATHS,
    PHASE54_SLICE12_MECHANICAL_REPAIR3_SUBJECT,
    PHASE54_SLICE12_MECHANICAL_REPAIR4_BASE,
    PHASE54_SLICE12_MECHANICAL_REPAIR4_BRANCH,
    PHASE54_SLICE12_MECHANICAL_REPAIR4_MODIFIED_PATHS,
    PHASE54_SLICE12_MECHANICAL_REPAIR4_SUBJECT,
    PHASE54_SLICE12_PRODUCT_REPAIR3_BASE,
    PHASE54_SLICE12_PRODUCT_REPAIR3_BRANCH,
    PHASE54_SLICE12_PRODUCT_REPAIR3_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR10_BASE,
    PHASE54_SLICE12_PRODUCT_REPAIR10_BRANCH,
    PHASE54_SLICE12_PRODUCT_REPAIR10_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR11_BASE,
    PHASE54_SLICE12_PRODUCT_REPAIR11_BRANCH,
    PHASE54_SLICE12_PRODUCT_REPAIR11_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR12_BASE,
    PHASE54_SLICE12_PRODUCT_REPAIR12_BRANCH,
    PHASE54_SLICE12_PRODUCT_REPAIR12_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR13_BASE,
    PHASE54_SLICE12_PRODUCT_REPAIR13_BRANCH,
    PHASE54_SLICE12_PRODUCT_REPAIR13_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR14_BASE,
    PHASE54_SLICE12_PRODUCT_REPAIR14_BRANCH,
    PHASE54_SLICE12_PRODUCT_REPAIR14_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR3_SUBJECT,
    PHASE54_SLICE12_PRODUCT_REPAIR10_SUBJECT,
    PHASE54_SLICE12_PRODUCT_REPAIR11_SUBJECT,
    PHASE54_SLICE12_PRODUCT_REPAIR12_SUBJECT,
    PHASE54_SLICE12_PRODUCT_REPAIR13_SUBJECT,
    PHASE54_SLICE12_PRODUCT_REPAIR14_SUBJECT,
    PHASE54_SLICE11_PYTHON313_REPAIR_BASE,
    PHASE54_SLICE11_PYTHON313_REPAIR_BRANCH,
    PHASE54_SLICE11_PYTHON313_REPAIR_MODIFIED_PATHS,
    PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_BASE,
    PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_BRANCH,
    PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_MODIFIED_PATHS,
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
    phase54_slice11_pr_ci_repair_is_active,
    phase54_slice12_pr_ci_repair_is_active,
    phase54_slice12_mechanical_repair3_clean_topic_is_active,
    phase54_slice12_mechanical_repair3_is_active,
    phase54_slice12_mechanical_repair4_clean_topic_is_active,
    phase54_slice12_mechanical_repair4_is_active,
    phase54_slice12_product_repair3_is_active,
    phase54_slice12_product_repair10_clean_topic_is_active,
    phase54_slice12_product_repair11_clean_topic_is_active,
    phase54_slice12_product_repair12_clean_topic_is_active,
    phase54_slice12_product_repair13_clean_topic_is_active,
    phase54_slice12_product_repair14_clean_topic_is_active,
    phase54_slice12_product_repair10_is_active,
    phase54_slice12_product_repair11_is_active,
    phase54_slice12_product_repair12_is_active,
    phase54_slice12_product_repair13_is_active,
    phase54_slice12_product_repair14_is_active,
    phase54_slice11_python313_repair_is_active,
    phase54_slice11_substantive_recovery_is_active,
)

import pietto.ir as ir_package
import pietto.semantic as semantic_package
import pietto.semantic.capability_windows as capability_windows
import pietto.sql as sql_package
from pietto.ir.model import (
    WindowCallIR,
    WindowFunctionIdentityIR,
    WindowFunctionRoleIR,
    WindowOrderItemIR,
    WindowSpecIR,
)
from pietto.semantic.capability_lookup import Found, Unknown, lookup_capability
from pietto.semantic.capability_facts import CapabilityDomain, CapabilityKey


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_REL = (
    "docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md"
)
SPEC_REL = "docs/spec/phase53-completion-audit-and-status-lock-v1.md"
SELF_REL = "tests/test_phase53_completion_audit_and_status_lock.py"
ROADMAP_REL = "docs/spec/pietto-active-roadmap-phase53-70-v1.md"
SLICE2_STATE_REL = "tests/test_phase53_window_syntax_contextual_grammar_contract.py"
PHASE54_SLICE2_STATE_REL = "tests/_phase54_active_gate2_manifest.py"

SPEC_TITLE = "Phase 53 Slice 16 Completion Audit And Status Lock v1"
SPEC_H2 = (
    "Purpose And Slice Identity",
    "Status And Completion Authority",
    "Trusted Slice 15 Baseline",
    "Phase 53 Sixteen-slice Route Ledger",
    "Publication And Repair Evidence Ledger",
    "Window Identity Signature And Nullability Closure",
    "PostgreSQL Dialect Closure",
    "Private MySQL Dialect Closure",
    "Window IR And Capability Non-authority Closure",
    "Diagnostic And Behavior Closure",
    "Privacy And Public-surface Closure",
    "Serializer And Metadata Boundary Audit",
    "Generated Golden And Fixture Stability",
    "Package Workflow Dependency And Release Audit",
    "Rust And Remote-package Deferral",
    "Future-owner Audit",
    "Fail-closed Non-owned Boundary Audit",
    "Reader Fixed Point And Test Accounting",
    "Completion Encoding Decision",
    "Gate 2 Pre-completion State",
    "Gate 3 Completion Condition",
    "Post-completion Phase 54–70 Status",
    "Exact Gate 2 Allowlist",
    "Completion Invariants And Drift Locks",
    "Validation And Clean-CI Boundary",
    "Separate Authorization Boundary",
    "Stop Conditions",
)
EXPECTED_TEST_NAMES = (
    "test_slice16_artifacts_title_and_exact_heading_order_are_locked",
    "test_sixteen_row_route_titles_specifications_tests_and_shapes_are_exact",
    "test_slice1_15_publication_lifecycle_evidence_chain_and_next_authorization_are_locked",
    "test_window_identity_signature_nullability_and_capability_closure_is_locked",
    "test_postgresql_window_lowering_dialect_closure_is_locked",
    "test_private_mysql_window_lowering_dialect_closure_is_locked",
    "test_window_ir_privacy_and_capability_non_authority_closure_is_locked",
    "test_diagnostic_inventory_and_fail_closed_ordering_closure_is_locked",
    "test_privacy_public_exports_serializers_and_generated_closure_is_locked",
    "test_phase60_63_69_70_future_owner_boundaries_are_locked",
    "test_package_version_tag_release_and_rust_closure_is_locked",
    "test_generated_golden_fixture_workflow_dependency_stability_is_locked",
    "test_live_compiler_semantic_phase15_project_protected_version_and_tag_locks_are_dirty_safe",
    "test_static_reader_hash_topology_test_inventory_and_validation_manifests_are_locked",
    "test_completion_encoding_gate2_gate3_ci_and_phase54_boundaries_are_locked",
    "test_static_git_helper_and_exact_slice16_dirty_set_are_locked",
)
PHASE53_ROUTE = (
    "Scope, Authority, Phase 53–70 Roadmap, Global Window Keyword, And Activation",
    "Pietto-native Window Syntax And Contextual Grammar Contract",
    "WindowSpec, Extension-compatible WindowFunctionIdentity, And AST Contract",
    "Generic Type-variable, Constraint, And Exact Compatibility Foundation",
    "Nullability Algebra And Signature Result-formula Foundation",
    "Private Window Semantic Carrier, WINDOW Stage, Dependency, And Result Roles",
    "row_number Direct-field MVP",
    "rank / dense_rank And Peer Semantics",
    "percent_rank / cume_dist / ntile",
    "Partition Binding, Multi-key Visibility, And Diagnostics",
    "Window-local Ordering, Direction, Mandatory-order Policy, And Determinism",
    "Generic lag / lead Navigation MVP",
    "Grouped-result Ranking, Aggregate-result Inputs, And Bounded Let Visibility",
    "Multiple Window Outputs, Final-order Alias, Downstream Schema, And Lineage",
    "Window IR, PostgreSQL/private-MySQL Lowering, WINDOW_FUNCTION Facts, And Phase 54–70 Readiness",
    "Completion Audit, Status Lock, Dialect, Privacy, And No-authority Closure",
)
SLICE_SPEC_RELS = (
    "docs/spec/phase53-window-functions-generic-signature-nullability-scope-lock-v1.md",
    "docs/spec/phase53-window-syntax-contextual-grammar-contract-v1.md",
    "docs/spec/phase53-window-spec-function-identity-ast-contract-v1.md",
    "docs/spec/phase53-generic-type-variable-exact-compatibility-contract-v1.md",
    "docs/spec/phase53-nullability-algebra-signature-result-formula-contract-v1.md",
    "docs/spec/phase53-private-window-semantic-carrier-stage-dependency-result-role-contract-v1.md",
    "docs/spec/phase53-row-number-direct-field-mvp-contract-v1.md",
    "docs/spec/phase53-rank-dense-rank-peer-semantics-contract-v1.md",
    "docs/spec/phase53-percent-rank-cume-dist-ntile-contract-v1.md",
    "docs/spec/phase53-partition-binding-multi-key-visibility-diagnostics-contract-v1.md",
    "docs/spec/phase53-window-local-ordering-direction-determinism-contract-v1.md",
    "docs/spec/phase53-lag-lead-navigation-offset-default-nullability-contract-v1.md",
    "docs/spec/phase53-grouped-result-ranking-aggregate-result-inputs-bounded-let-visibility-contract-v1.md",
    "docs/spec/phase53-multiple-window-outputs-final-order-alias-downstream-schema-lineage-contract-v1.md",
    "docs/spec/phase53-window-ir-dual-backend-lowering-window-function-facts-contract-v1.md",
    SPEC_REL,
)
SLICE_TEST_RELS = (
    "tests/test_phase53_window_generic_nullability_foundation_scope_lock.py",
    "tests/test_phase53_window_syntax_contextual_grammar_contract.py",
    "tests/test_phase53_window_spec_function_identity_ast_contract.py",
    "tests/test_phase53_generic_type_variable_exact_compatibility_contract.py",
    "tests/test_phase53_nullability_algebra_signature_result_formula_contract.py",
    "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py",
    "tests/test_phase53_row_number_direct_field_mvp_contract.py",
    "tests/test_phase53_rank_dense_rank_peer_semantics_contract.py",
    "tests/test_phase53_percent_rank_cume_dist_ntile_contract.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
    "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
    "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
    "tests/test_phase53_grouped_result_ranking_aggregate_result_inputs_bounded_let_visibility_contract.py",
    "tests/test_phase53_multiple_window_outputs_final_order_alias_downstream_schema_lineage_contract.py",
    "tests/test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py",
    SELF_REL,
)
SLICE_FUNCTION_COUNTS = (14, 16, 25, 31, 38, 36, 41, 45, 54, 67, 81, 64, 60, 67, 33, 16)
SLICE_ITEM_LEDGER = (
    69,
    70,
    70,
    190,
    145,
    156,
    168,
    279,
    424,
    627,
    834,
    381,
    489,
    507,
    208,
    16,
)

PHASE52_BASE_SHA = "b8029699ccc51bfa500856155b18e666898cb883"
SLICE_PUBLICATION_SHAS = (
    "c309323216fb7e6c52afba060cb188b3bb618d34",
    "86b08e27bbe97589b143dc1043fb0ad743dbf88a",
    "ee0cb021160ead5ea6c0bcc80e569f4fdfef67a3",
    "8485715b17b2dcf3b9f99b84f7ad001bcfab42d5",
    "ea90f3957bcac4d85bd4f8b1938ad0508638f13a",
    "321ec6f80737015648bc1f81b0561fdd34610e92",
    "6c27621a9a0504f704bfba059f9b262c9f5e3e68",
    "f90bd653c3ece47a86a121095f4547783f35197f",
    "c9e04d833e36bdd7cdc521eeb2c5f030aac8a998",
    "54553396f61caefe74b57cd6ed6fa144725a50e4",
    "110e1a6d285675eb8cf7e5ac58e5ac905d856701",
    "d8c58e526f2ff18ad7473c89e63f10cf935e0bb0",
    "933cf2f4ad0aab245feda09462178b90ebf9b7a6",
    "9ff8c97f5d5996b5a27e13bcf45032b825f0a3d5",
    "3c1feab5bc70d407e9e4d7ccd0c5d489eec0ee68",
)
REPAIR_SHAS = (
    "d52a4a80aee1a1708d8fd480f63aa450a1c25eff",
    "0b49cc02dc641472a4f3cc1bdf149b444dade9b2",
    "05114de0effaa3c9fff6ecd0dbb781bd553e91a6",
    "e2441308179d34a6806b61f533d5799b910fbbb0",
)
DEPENDABOT_SHAS = (
    "a5606761c040042d177874253e29c25f2e8e3fff",
    "4ff3c131fba54d83b56f3c50e14f7c2337c1eb52",
)
SLICE16_BASE_HEAD_SHA = "3c1feab5bc70d407e9e4d7ccd0c5d489eec0ee68"
SLICE16_BASE_PARENT_SHA = "9ff8c97f5d5996b5a27e13bcf45032b825f0a3d5"
SLICE16_BASE_TREE_SHA = "ae9b3e5c1fc25e3894c61623cf84583a76ba0556"
SLICE16_BASE_SUBJECT = "Add Phase 53 window IR and dual-backend lowering"
SLICE16_COMMIT_SUBJECT = "Complete Phase 53 status and compatibility audit"
SLICE13_SUBJECT_WITH_PERIOD = "Add Phase 53 grouped-result window inputs."

WINDOW_FUNCTION_SQL_NAMES = {
    "row_number": "ROW_NUMBER",
    "rank": "RANK",
    "dense_rank": "DENSE_RANK",
    "percent_rank": "PERCENT_RANK",
    "cume_dist": "CUME_DIST",
    "ntile": "NTILE",
    "lag": "LAG",
    "lead": "LEAD",
}
WINDOW_IR_CLASSES = (
    WindowFunctionRoleIR,
    WindowFunctionIdentityIR,
    WindowOrderItemIR,
    WindowSpecIR,
    WindowCallIR,
)
CAPABILITY_WINDOWS_REL = "src/pietto/semantic/capability_windows.py"
CAPABILITY_WINDOWS_SHA256 = (
    "c0512933fc284bbc1dec98dab96411ee179d64e7bee005aa798b6fd7dba2024e"
)
PATH_DIGESTS = {
    "compiler": "f6fd00f2fffb54a21eff61527ee5b8e937d2cbcf4ceb8931ff34802ec785376e",
    "semantic": "731e17cc85849c7716abeb08abeda03f72e3e21af183a391107adf96ccab6d70",
    "phase15": "81db265a7bbd290b9c9227733e92dc502f8e8c8f0ff76b4d631651772876550d",
    "project": "74fd3654b97aa6c824cc76bb7ad673fd1133213a03ab7d9cff9bf003e1ac0251",
}
PROTECTED_SHA256 = {
    ".github/workflows/ci.yml": "4db1c9a49b0af230bae3f088bf84524e210e0afcd6a87250322e5036a69e8d94",
    "pyproject.toml": "36aa8e1d19a8409e56e0163a465b9608a88c1bffe644165ba49db49bf5ec3d01",
    "uv.lock": "a7d9125995e98a8a74d3664ceae7801cc1f4cce74ec323933da67838be199cea",
    ".python-version": "7b55f8e67b5623c4bef3fa691288da9437d79d3aba156de48d481db32ac7d16d",
    "docs/spec/pietto-roadmap-phase45-60-v1.md": "26cc0ae4a68518223d6bf600ad3c4b0b226618aa7ef31b2ae1c25924d2655169",
}
ROADMAP_SHA256 = "67c886a05234d4513d2083a12fc0f95ad550fdd892565a6ef7c52de9631743e3"

SLICE16_ADDED_PATHS = {
    SPEC_REL,
    SELF_REL,
}
SLICE16_MODIFIED_PATHS = {
    PLAN_REL,
    "tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py",
    "tests/test_phase51_completion_audit_and_status_lock.py",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
    "tests/test_phase52_aggregate_signature_algebra_facts.py",
    "tests/test_phase52_completion_audit_and_status_lock.py",
    "tests/test_phase52_expression_stage_clause_capability_facts.py",
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
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
    "tests/test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py",
    "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
    "tests/test_phase53_window_spec_function_identity_ast_contract.py",
    SLICE2_STATE_REL,
}
SLICE16_ALLOWLIST_PATHS = SLICE16_ADDED_PATHS | SLICE16_MODIFIED_PATHS


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _sha256(relative: str) -> str:
    return hashlib.sha256((REPO_ROOT / relative).read_bytes()).hexdigest()


def _headings(relative: str, level: int) -> tuple[str, ...]:
    return tuple(
        match.group(1).strip()
        for match in re.finditer(
            rf"^{'#' * level} (?!#)(.+?)\s*$",
            _read(relative),
            flags=re.MULTILINE,
        )
    )


def _git_output(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    return result.stdout.rstrip()


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
    if result.returncode == 1:
        assert result.stdout == ""
        return None
    return result.stdout.strip()


def _git_commit_exists(commit: str) -> bool:
    assert re.fullmatch(r"[0-9a-f]{40}", commit)
    result = subprocess.run(
        ["git", "cat-file", "--batch-check=%(objectname) %(objecttype)"],
        cwd=REPO_ROOT,
        check=True,
        input=f"{commit}\n",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    if result.stdout == f"{commit} commit\n":
        return True
    if result.stdout == f"{commit} missing\n":
        return False
    raise AssertionError(f"unexpected git object result: {result.stdout!r}")


def _git_refs() -> tuple[tuple[str, str], ...]:
    output = _git_output(["for-each-ref", "--format=%(refname)%09%(objectname)"])
    if not output:
        return ()
    refs = tuple(tuple(line.split("\t", maxsplit=1)) for line in output.splitlines())
    assert all(
        len(pair) == 2 and pair[0] and re.fullmatch(r"[0-9a-f]{40}", pair[1])
        for pair in refs
    )
    return cast(tuple[tuple[str, str], ...], refs)


def _assert_clean_checkout_refs(
    *,
    branch: str,
    head: str,
    main: str | None,
    origin_main: str | None,
    exact_main_refs: bool = False,
) -> None:
    refs = _git_refs()
    if branch == "main":
        assert head == main
        if origin_main is not None:
            assert head == origin_main
        if exact_main_refs:
            assert refs == (
                ("refs/heads/main", head),
                ("refs/remotes/origin/main", head),
            )
        return

    if branch == PHASE54_SLICE12_PR_CI_REPAIR_BRANCH:
        assert main == origin_main == PHASE54_ACTIVE_GATE2_BASE
        parents = tuple(
            _git_output(["rev-list", "--parents", "-n", "1", "HEAD"]).split()[1:]
        )
        subject = _git_output(["show", "-s", "--format=%s", "HEAD"])
        if head == PHASE54_SLICE12_PR_CI_REPAIR_BASE:
            assert parents == (PHASE54_ACTIVE_GATE2_BASE,)
            assert subject == "Add Phase 54 semantic fact preservation"
        elif head == PHASE54_SLICE12_PRODUCT_REPAIR3_BASE:
            assert parents == (PHASE54_SLICE12_PR_CI_REPAIR_BASE,)
            assert subject == "Fix Phase 54 Slice 12 PR CI topology projection"
        elif phase54_slice12_mechanical_repair4_clean_topic_is_active():
            assert parents == (PHASE54_SLICE12_MECHANICAL_REPAIR4_BASE,)
            assert subject == PHASE54_SLICE12_MECHANICAL_REPAIR4_SUBJECT
        elif phase54_slice12_mechanical_repair3_clean_topic_is_active():
            assert parents == (PHASE54_SLICE12_MECHANICAL_REPAIR3_BASE,)
            assert subject == PHASE54_SLICE12_MECHANICAL_REPAIR3_SUBJECT
        elif phase54_slice12_product_repair14_clean_topic_is_active():
            assert parents == (PHASE54_SLICE12_PRODUCT_REPAIR14_BASE,)
            assert subject == PHASE54_SLICE12_PRODUCT_REPAIR14_SUBJECT
        elif phase54_slice12_product_repair13_clean_topic_is_active():
            assert parents == (PHASE54_SLICE12_PRODUCT_REPAIR13_BASE,)
            assert subject == PHASE54_SLICE12_PRODUCT_REPAIR13_SUBJECT
        elif phase54_slice12_product_repair12_clean_topic_is_active():
            assert parents == (PHASE54_SLICE12_PRODUCT_REPAIR12_BASE,)
            assert subject == PHASE54_SLICE12_PRODUCT_REPAIR12_SUBJECT
        elif phase54_slice12_product_repair11_clean_topic_is_active():
            assert parents == (PHASE54_SLICE12_PRODUCT_REPAIR11_BASE,)
            assert subject == PHASE54_SLICE12_PRODUCT_REPAIR11_SUBJECT
        elif phase54_slice12_product_repair10_clean_topic_is_active():
            assert parents == (PHASE54_SLICE12_PRODUCT_REPAIR10_BASE,)
            assert subject == PHASE54_SLICE12_PRODUCT_REPAIR10_SUBJECT
        else:
            assert parents == (PHASE54_SLICE12_PRODUCT_REPAIR3_BASE,)
            assert subject == PHASE54_SLICE12_PRODUCT_REPAIR3_SUBJECT
        return

    if branch == phase54_publication_topic_branch():
        assert phase54_publication_clean_topic_is_active()
        return

    assert branch == ""
    assert main is None and origin_main is None
    assert len(refs) == 1
    merge_ref, merge_head = refs[0]
    assert re.fullmatch(r"refs/remotes/pull/[1-9][0-9]*/merge", merge_ref)
    assert merge_head == head
    raw = _git_output(["cat-file", "-p", head])
    header, separator, message = raw.partition("\n\n")
    assert separator == "\n\n"
    parents = tuple(
        line.removeprefix("parent ")
        for line in header.splitlines()
        if line.startswith("parent ")
    )
    assert len(parents) == 2 and parents[0] != parents[1]
    assert all(re.fullmatch(r"[0-9a-f]{40}", parent) for parent in parents)
    assert message == f"Merge {parents[1]} into {parents[0]}"
    availability = tuple(_git_commit_exists(parent) for parent in parents)
    assert len(set(availability)) == 1
    if all(availability):
        assert _git_output(["merge-base", *parents]) == parents[0]
        assert _git_output(["rev-parse", f"{parents[1]}^{{tree}}"]) == _git_output(
            ["rev-parse", f"{head}^{{tree}}"]
        )


def _assert_allowed_dirty_state(
    *,
    tracked: set[str],
    untracked: set[str],
    branch: str,
    head: str,
    main: str | None,
    origin_main: str | None,
) -> None:
    if phase54_slice11_python313_repair_is_active():
        assert tracked == set(PHASE54_SLICE11_PYTHON313_REPAIR_MODIFIED_PATHS)
        assert untracked == set()
        assert branch == PHASE54_SLICE11_PYTHON313_REPAIR_BRANCH
        assert head == PHASE54_SLICE11_PYTHON313_REPAIR_BASE
        assert main == origin_main == "b81843acadb294630db361c09949868d004b1bca"
        return
    if phase54_slice11_substantive_recovery_is_active():
        assert tracked == set(PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_MODIFIED_PATHS)
        assert untracked == set()
        assert branch == PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_BRANCH
        assert head == PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_BASE
        assert main == origin_main == "b81843acadb294630db361c09949868d004b1bca"
        return
    if phase54_slice11_pr_ci_repair_is_active():
        assert tracked == set(PHASE54_SLICE11_PR_CI_REPAIR_MODIFIED_PATHS)
        assert untracked == set()
        assert branch == PHASE54_SLICE11_PR_CI_REPAIR_BRANCH
        assert head == PHASE54_SLICE11_PR_CI_REPAIR_BASE
        assert main == origin_main == "b81843acadb294630db361c09949868d004b1bca"
        return
    if phase54_slice12_pr_ci_repair_is_active():
        assert tracked == set(PHASE54_SLICE12_PR_CI_REPAIR_MODIFIED_PATHS)
        assert untracked == set()
        assert branch == PHASE54_SLICE12_PR_CI_REPAIR_BRANCH
        assert head == PHASE54_SLICE12_PR_CI_REPAIR_BASE
        assert main == origin_main == "bc46faff1c9aa71f583ed7d2964b651cc659bc90"
        return
    if phase54_slice12_mechanical_repair4_is_active():
        assert tracked == set(PHASE54_SLICE12_MECHANICAL_REPAIR4_MODIFIED_PATHS)
        assert untracked == set()
        assert branch == PHASE54_SLICE12_MECHANICAL_REPAIR4_BRANCH
        assert head == PHASE54_SLICE12_MECHANICAL_REPAIR4_BASE
        assert main == origin_main == "bc46faff1c9aa71f583ed7d2964b651cc659bc90"
        return
    if phase54_slice12_mechanical_repair3_is_active():
        assert tracked == set(PHASE54_SLICE12_MECHANICAL_REPAIR3_MODIFIED_PATHS)
        assert untracked == set()
        assert branch == PHASE54_SLICE12_MECHANICAL_REPAIR3_BRANCH
        assert head == PHASE54_SLICE12_MECHANICAL_REPAIR3_BASE
        assert main == origin_main == "bc46faff1c9aa71f583ed7d2964b651cc659bc90"
        return
    if phase54_slice12_product_repair14_is_active():
        assert tracked == set(PHASE54_SLICE12_PRODUCT_REPAIR14_MODIFIED_PATHS)
        assert untracked == set()
        assert branch == PHASE54_SLICE12_PRODUCT_REPAIR14_BRANCH
        assert head == PHASE54_SLICE12_PRODUCT_REPAIR14_BASE
        assert main == origin_main == "bc46faff1c9aa71f583ed7d2964b651cc659bc90"
        return
    if phase54_slice12_product_repair13_is_active():
        assert tracked == set(PHASE54_SLICE12_PRODUCT_REPAIR13_MODIFIED_PATHS)
        assert untracked == set()
        assert branch == PHASE54_SLICE12_PRODUCT_REPAIR13_BRANCH
        assert head == PHASE54_SLICE12_PRODUCT_REPAIR13_BASE
        assert main == origin_main == "bc46faff1c9aa71f583ed7d2964b651cc659bc90"
        return
    if phase54_slice12_product_repair12_is_active():
        assert tracked == set(PHASE54_SLICE12_PRODUCT_REPAIR12_MODIFIED_PATHS)
        assert untracked == set()
        assert branch == PHASE54_SLICE12_PRODUCT_REPAIR12_BRANCH
        assert head == PHASE54_SLICE12_PRODUCT_REPAIR12_BASE
        assert main == origin_main == "bc46faff1c9aa71f583ed7d2964b651cc659bc90"
        return
    if phase54_slice12_product_repair11_is_active():
        assert tracked == set(PHASE54_SLICE12_PRODUCT_REPAIR11_MODIFIED_PATHS)
        assert untracked == set()
        assert branch == PHASE54_SLICE12_PRODUCT_REPAIR11_BRANCH
        assert head == PHASE54_SLICE12_PRODUCT_REPAIR11_BASE
        assert main == origin_main == "bc46faff1c9aa71f583ed7d2964b651cc659bc90"
        return
    if phase54_slice12_product_repair10_is_active():
        assert tracked == set(PHASE54_SLICE12_PRODUCT_REPAIR10_MODIFIED_PATHS)
        assert untracked == set()
        assert branch == PHASE54_SLICE12_PRODUCT_REPAIR10_BRANCH
        assert head == PHASE54_SLICE12_PRODUCT_REPAIR10_BASE
        assert main == origin_main == "bc46faff1c9aa71f583ed7d2964b651cc659bc90"
        return
    if phase54_slice12_product_repair3_is_active():
        assert tracked == set(PHASE54_SLICE12_PRODUCT_REPAIR3_MODIFIED_PATHS)
        assert untracked == set()
        assert branch == PHASE54_SLICE12_PRODUCT_REPAIR3_BRANCH
        assert head == PHASE54_SLICE12_PRODUCT_REPAIR3_BASE
        assert main == origin_main == "bc46faff1c9aa71f583ed7d2964b651cc659bc90"
        return
    if (
        _phase54_active_gate2_is_active()
        and tracked == set(PHASE54_ACTIVE_GATE2_MODIFIED_PATHS)
        and untracked == set(PHASE54_ACTIVE_GATE2_ADDED_PATHS)
        and branch == "phase54/slice10-cross-module-relation-row-facts"
        and head
        in {
            PHASE54_POST_REVIEW_PRODUCT_REPAIR1_BASE,
            PHASE54_POST_REVIEW_PRODUCT_REPAIR2_BASE,
            PHASE54_POST_REVIEW_PRODUCT_REPAIR3_BASE,
            PHASE54_POST_REVIEW_PRODUCT_REPAIR4_BASE,
            PHASE54_POST_REVIEW_PRODUCT_REPAIR5_BASE,
            PHASE54_POST_REVIEW_PRODUCT_REPAIR6_BASE,
            PHASE54_POST_REVIEW_PRODUCT_REPAIR7_BASE,
            PHASE54_POST_REVIEW_PRODUCT_REPAIR8_BASE,
            PHASE54_POST_REVIEW_PRODUCT_REPAIR9_BASE,
        }
        and main == origin_main == "fadb1924af057cfc901a1658e117810d699e2358"
    ):
        return
    dirty = tracked | untracked
    phase54_modified = cast(
        set[str],
        _module_literal(PHASE54_SLICE2_STATE_REL, "NON_READER_MODIFIED_PATHS"),
    ) | cast(
        set[str],
        _module_literal(PHASE54_SLICE2_STATE_REL, "MECHANICAL_READER_PATHS"),
    )
    phase54_added = cast(
        set[str], _module_literal(PHASE54_SLICE2_STATE_REL, "ADDED_PATHS")
    )
    phase54_allowlist = phase54_modified | phase54_added
    assert dirty in (
        set(),
        SLICE16_ALLOWLIST_PATHS,
        phase54_allowlist,
        set(phase54_post_slice12_interlude_expected_allowlist_paths()),
    )
    if not dirty:
        assert tracked == untracked == set()
        availability = (
            _git_commit_exists(SLICE16_BASE_HEAD_SHA),
            _git_commit_exists(SLICE16_BASE_PARENT_SHA),
        )
        assert availability[0] or not availability[1]
        if all(availability):
            assert _git_output(["rev-parse", f"{SLICE16_BASE_HEAD_SHA}^"]) == (
                SLICE16_BASE_PARENT_SHA
            )
            assert (
                _git_output(["rev-parse", f"{SLICE16_BASE_HEAD_SHA}^{{tree}}"])
                == SLICE16_BASE_TREE_SHA
            )
            assert (
                _git_output(["show", "-s", "--format=%s", SLICE16_BASE_HEAD_SHA])
                == SLICE16_BASE_SUBJECT
            )
            assert _git_output(["merge-base", head, SLICE16_BASE_HEAD_SHA]) == (
                SLICE16_BASE_HEAD_SHA
            )
            _assert_clean_checkout_refs(
                branch=branch,
                head=head,
                main=main,
                origin_main=origin_main,
            )
        else:
            assert _git_output(["rev-parse", "--is-shallow-repository"]) == "true"
            assert (
                _git_output(["status", "--porcelain=v1", "--untracked-files=all"]) == ""
            )
            assert _git_output(["diff", "--cached", "--name-only"]) == ""
            _assert_clean_checkout_refs(
                branch=branch,
                head=head,
                main=main,
                origin_main=origin_main,
                exact_main_refs=True,
            )
        return
    if dirty == phase54_allowlist:
        assert tracked == phase54_modified
        assert untracked == phase54_added
        assert branch == "main"
        assert head == main == origin_main
        assert head in {
            "d8a5e9ab3de70ce30575513c73560c86430eca63",
            "93f0f591e28a01f32d1698fcd4b8c57d41c6d714",
            "15bae172ee151e370fe59d3bf909d735aee6aa90",
            "0f3c955c5a5fbd8046ef611ad1bef0b636c8be01",
            "c44a4271d9592cb393d2232f127a59d8466cc60a",
            "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16",
            "027b33cafcfd58916a89e299487dad38d24ade6c",
            "0ceb9a476e6592714cdc76845949ba0ae5123eb5",
            "b81843acadb294630db361c09949868d004b1bca",
            "bc46faff1c9aa71f583ed7d2964b651cc659bc90",
            "0bad854253e22347e2aff93e2eabcbe2fda55aed",
            "040ab19c56519c39c56541979c850484f9cc47f0",
        }
        return
    if phase54_post_slice12_interlude_dirty_is_active():
        assert tracked == set(phase54_post_slice12_interlude_expected_modified_paths())
        assert untracked == set(phase54_post_slice12_interlude_expected_added_paths())
        if phase54_post_slice12_interlude_repair_is_active():
            assert branch == phase54_publication_topic_branch()
            assert head == phase54_post_slice12_interlude_expected_head()
            assert main == origin_main == phase54_publication_topic_base()
        else:
            assert branch == "main"
            assert (
                head
                == main
                == origin_main
                == phase54_post_slice12_interlude_expected_head()
            )
        return
    assert tracked == SLICE16_MODIFIED_PATHS
    assert untracked == SLICE16_ADDED_PATHS
    assert branch == "main"
    assert head == main == origin_main == SLICE16_BASE_HEAD_SHA


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


def _project_paths() -> tuple[Path, ...]:
    return tuple(
        path
        for path in (REPO_ROOT / "src/pietto/_project").rglob("*.py")
        if "__pycache__" not in path.parts
    )


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


def _module_literal(relative: str, name: str) -> object:
    tree = ast.parse(_read(relative), filename=relative)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(f"missing literal {name} in {relative}")


def _window_fact_families() -> tuple[int, int]:
    facts = capability_windows._WINDOW_CAPABILITY_FACTS
    signature = tuple(fact for fact in facts if fact.key.operation == "signature")
    lowering = tuple(fact for fact in facts if fact.key.operation == "lowering")
    assert len(facts) == len(signature) + len(lowering)
    return len(signature), len(lowering)


def test_slice16_artifacts_title_and_exact_heading_order_are_locked() -> None:
    assert (REPO_ROOT / SPEC_REL).is_file()
    assert (REPO_ROOT / SELF_REL).is_file()
    assert _headings(SPEC_REL, 1) == (SPEC_TITLE,)
    assert _headings(SPEC_REL, 2) == SPEC_H2
    assert _headings(SPEC_REL, 3) == ()
    assert _headings(PLAN_REL, 3) == ()
    plan_h2 = _headings(PLAN_REL, 2)
    assert plan_h2[-1] == (
        "Slice 16 — Completion Audit, Status Lock, Dialect, Privacy, "
        "And No-authority Closure"
    )
    tests = _top_level_test_functions(SELF_REL)
    assert tests == EXPECTED_TEST_NAMES
    assert len(tests) == 16
    tree = ast.parse(_read(SELF_REL), filename=SELF_REL)
    functions = tuple(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert all(not node.decorator_list for node in functions)


def test_sixteen_row_route_titles_specifications_tests_and_shapes_are_exact() -> None:
    plan = _read(PLAN_REL)
    route_start = plan.index("## Exact Sixteen-slice Route")
    route_end = plan.index("## Slice Objectives", route_start)
    route = tuple(
        match.group(1)
        for match in re.finditer(
            r"^\d+\. (.+)$", plan[route_start:route_end], re.MULTILINE
        )
    )
    assert route == PHASE53_ROUTE
    roadmap = _read(ROADMAP_REL)
    for title in PHASE53_ROUTE:
        assert title in roadmap
    assert len(SLICE_SPEC_RELS) == len(SLICE_TEST_RELS) == 16
    assert all((REPO_ROOT / path).is_file() for path in SLICE_SPEC_RELS)
    assert all((REPO_ROOT / path).is_file() for path in SLICE_TEST_RELS)
    observed_functions = tuple(
        len(_top_level_test_functions(path)) for path in SLICE_TEST_RELS
    )
    assert observed_functions == SLICE_FUNCTION_COUNTS
    assert sum(SLICE_FUNCTION_COUNTS) == 688
    assert len(SLICE_ITEM_LEDGER) == 16
    assert sum(SLICE_ITEM_LEDGER) == 4633
    assert SLICE_ITEM_LEDGER[-1] == 16
    assert 10784 + SLICE_ITEM_LEDGER[-1] == 10800


def test_slice1_15_publication_lifecycle_evidence_chain_and_next_authorization_are_locked() -> (
    None
):
    assert len(SLICE_PUBLICATION_SHAS) == 15
    assert len(set(SLICE_PUBLICATION_SHAS)) == 15
    assert len(REPAIR_SHAS) == 4 and len(DEPENDABOT_SHAS) == 2
    availability = tuple(
        _git_commit_exists(sha)
        for sha in (
            PHASE52_BASE_SHA,
            *SLICE_PUBLICATION_SHAS,
            *REPAIR_SHAS,
            *DEPENDABOT_SHAS,
        )
    )
    assert (
        len(set(availability)) == 1
        or _git_output(["rev-parse", "--is-shallow-repository"]) == "true"
    )
    if all(availability):
        chain = _git_output(
            [
                "log",
                "--first-parent",
                "--format=%H",
                f"{PHASE52_BASE_SHA}..{SLICE16_BASE_HEAD_SHA}",
            ]
        ).splitlines()
        assert len(chain) == 21
        assert set(chain) == (
            set(SLICE_PUBLICATION_SHAS) | set(REPAIR_SHAS) | set(DEPENDABOT_SHAS)
        )
        assert chain[0] == SLICE16_BASE_HEAD_SHA
        assert (
            _git_output(["show", "-s", "--format=%s", SLICE_PUBLICATION_SHAS[12]])
            == SLICE13_SUBJECT_WITH_PERIOD
        )
        assert (
            _git_output(["show", "-s", "--format=%s", SLICE16_BASE_HEAD_SHA])
            == SLICE16_BASE_SUBJECT
        )
    plan = " ".join(_read(PLAN_REL).split())
    spec = " ".join(_read(SPEC_REL).split())
    assert "SLICE16_GATE0_GATE1" in plan
    assert "PHASE54_GATE0_GATE1" in plan and "PHASE54_GATE0_GATE1" in spec
    for phrase in (
        "Slices 1 through 15 are `COMPLETED`",
        "`IMPLEMENTED_UNPUBLISHED`",
        "Phase 54 through Phase 70 remain `UNSTARTED`",
    ):
        assert phrase in plan, phrase
    assert "no deferral is anonymous" in spec


def test_window_identity_signature_nullability_and_capability_closure_is_locked() -> (
    None
):
    assert tuple(WINDOW_FUNCTION_SQL_NAMES) == (
        "row_number",
        "rank",
        "dense_rank",
        "percent_rank",
        "cume_dist",
        "ntile",
        "lag",
        "lead",
    )
    signature_count, lowering_count = _window_fact_families()
    assert (signature_count, lowering_count) == (8, 16)
    facts = capability_windows._WINDOW_CAPABILITY_FACTS
    assert all(fact.key.domain is CapabilityDomain.WINDOW_FUNCTION for fact in facts)
    signature_subjects = tuple(
        fact.key.subject for fact in facts if fact.key.operation == "signature"
    )
    assert signature_subjects == tuple(WINDOW_FUNCTION_SQL_NAMES)
    lowering_dialects = Counter(
        fact.key.dialect for fact in facts if fact.key.operation == "lowering"
    )
    assert lowering_dialects == {"postgresql": 8, "mysql": 8}
    spec = " ".join(_read(SPEC_REL).split())
    for phrase in (
        "`namespace=()`",
        "one exact positive integer literal",
        "one through three bounded arguments",
        "never implies compiler legality or backend lowering",
    ):
        assert phrase in spec, phrase


def test_postgresql_window_lowering_dialect_closure_is_locked() -> None:
    expressions = _read("src/pietto/sql/expressions.py")
    assert "_WINDOW_FUNCTION_NAMES = {" in expressions
    for source_name, sql_name in WINDOW_FUNCTION_SQL_NAMES.items():
        assert f'"{source_name}": "{sql_name}",' in expressions
    assert "OVER (" in expressions
    assert "PARTITION BY " in expressions
    assert "ORDER BY " in expressions
    postgres = _read("src/pietto/sql/postgres.py")
    assert "PIE-B1000" in postgres
    for forbidden in ("QUALIFY", "first_value", "last_value", "nth_value"):
        assert forbidden not in expressions
        assert forbidden not in _read("src/pietto/ir/model.py")
    spec = " ".join(_read(SPEC_REL).split())
    for phrase in (
        "optional `PARTITION BY`",
        "mandatory `ORDER BY`",
        "double-quoted identifiers",
        "grouped underlying-expression lowering",
    ):
        assert phrase in spec, phrase


def test_private_mysql_window_lowering_dialect_closure_is_locked() -> None:
    mysql_expressions = _read("src/pietto/sql/mysql_expressions.py")
    assert "_WINDOW_FUNCTION_NAMES = {" in mysql_expressions
    for source_name, sql_name in WINDOW_FUNCTION_SQL_NAMES.items():
        assert f'"{source_name}": "{sql_name}",' in mysql_expressions
    for forbidden in ("QUALIFY", "first_value", "last_value", "nth_value"):
        assert forbidden not in mysql_expressions
    mysql_render = _read("src/pietto/sql/mysql_render.py")
    assert "`" in mysql_render
    assert "64" in mysql_render and "256" in mysql_render
    mysql = _read("src/pietto/sql/mysql.py")
    assert "PIE-B1000" in mysql
    assert "emit_mysql_sql" not in sql_package.__all__
    assert tuple(sql_package.__all__) == (
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    )
    spec = " ".join(_read(SPEC_REL).split())
    for phrase in (
        "backtick quoting",
        "No public MySQL support promise",
    ):
        assert phrase in spec, phrase


def test_window_ir_privacy_and_capability_non_authority_closure_is_locked() -> None:
    assert issubclass(WindowFunctionRoleIR, enum.Enum)
    for cls in WINDOW_IR_CLASSES:
        if cls is not WindowFunctionRoleIR:
            params = getattr(cls, "__dataclass_params__")
            assert params.frozen
            assert hasattr(cls, "__slots__")
        assert cls.__name__ not in ir_package.__all__
    assert len(ir_package.__all__) == 44
    assert _sha256(CAPABILITY_WINDOWS_REL) == CAPABILITY_WINDOWS_SHA256
    assert capability_windows.__all__ == ()
    key = capability_windows._WINDOW_CAPABILITY_FACTS[0].key
    facts, complete, reason = capability_windows.window_lookup_inputs(key)
    found = lookup_capability(
        key, facts, domain_complete=complete, unknown_reason=reason
    )
    assert isinstance(found, Found)
    absent_key = CapabilityKey(
        CapabilityDomain.WINDOW_FUNCTION,
        subject="median",
        operation="signature",
        operands=(),
        context="window_signature",
    )
    facts, complete, reason = capability_windows.window_lookup_inputs(absent_key)
    absent = lookup_capability(
        absent_key, facts, domain_complete=complete, unknown_reason=reason
    )
    assert isinstance(absent, Unknown)
    forbidden_names = ("window_lookup_inputs", "capability_windows")
    preservation_rel = "src/pietto/_project/module_semantic_fact_preservation.py"
    for path in (REPO_ROOT / "src/pietto").rglob("*.py"):
        relative = path.relative_to(REPO_ROOT).as_posix()
        if (
            relative in {CAPABILITY_WINDOWS_REL, preservation_rel}
            or "generated" in path.parts
        ):
            continue
        source = path.read_text(encoding="utf-8")
        assert all(name not in source for name in forbidden_names), relative
    preservation_source = _read(preservation_rel)
    assert all(name in preservation_source for name in forbidden_names)
    assert "__all__: tuple[str, ...] = ()" in preservation_source


def test_diagnostic_inventory_and_fail_closed_ordering_closure_is_locked() -> None:
    diagnostics = _read("docs/spec/diagnostics.md")
    assert "PIE-I1000" in diagnostics
    assert "PIE-B1000" in diagnostics
    assert "PIE-I1000" in _read("src/pietto/ir/diagnostics.py")
    window_sources = (
        "src/pietto/semantic/window_analysis.py",
        "src/pietto/semantic/window_semantics.py",
        "src/pietto/semantic/window_partition_analysis.py",
        "src/pietto/semantic/window_order_analysis.py",
        "src/pietto/semantic/window_navigation_analysis.py",
        "src/pietto/ir/lowering.py",
        "src/pietto/sql/postgres.py",
        "src/pietto/sql/mysql.py",
    )
    observed = set()
    for relative in window_sources:
        observed.update(re.findall(r"PIE-[A-Z]\d{4}", _read(relative)))
    assert observed == {"PIE-B1000", "PIE-S2103", "PIE-S2104", "PIE-S2312"}
    spec = _read(SPEC_REL)
    for phrase in (
        "renumbers, and rewords no diagnostic code",
        "first-error ordering is unchanged",
        "`PIE-I1000` remains the",
        "`PIE-B1000` remains the",
    ):
        assert phrase in " ".join(spec.split()) or phrase in spec, phrase


def test_privacy_public_exports_serializers_and_generated_closure_is_locked() -> None:
    assert len(semantic_package.__all__) == 11
    export_names = [
        name.lower()
        for name in (
            *ir_package.__all__,
            *semantic_package.__all__,
            *sql_package.__all__,
        )
    ]
    for token in ("window", "partition", "lag", "lead", "ntile", "rank", "cume"):
        assert all(token not in name for name in export_names), token
    top_level = _read("src/pietto/__init__.py")
    assert "window" not in top_level.lower()
    for serializer in (
        "src/pietto/cli_json.py",
        "src/pietto/_project/json_v2.py",
        "src/pietto/_metadata/serializer.py",
    ):
        source = _read(serializer).lower()
        assert "window" not in source, serializer
    generated = tuple(
        path for path in _readable_paths() if path.startswith("src/pietto/generated/")
    )
    assert len(generated) == 8


def test_phase60_63_69_70_future_owner_boundaries_are_locked() -> None:
    roadmap = _read(ROADMAP_REL)
    for phrase in (
        "Phase 60 owns `ROWS`, `RANGE`, evaluation of the `GROUPS` dialect posture",
        "`QUALIFY` remains Phase 63 work",
        "Extension-specific Lowering And Additional Dialect Backend Foundation",
        "Phase 64 exclusively owns Int/Decimal or other promotion",
    )[:4]:
        assert phrase in roadmap, phrase
    assert "Public Schema / Lineage / Attribution Expansion" in roadmap
    spec = _read(SPEC_REL)
    normalized_spec = " ".join(spec.split())
    for phrase in (
        "remain Phase 60",
        "remains Phase 63",
        "remain Phase 69",
        "remains Phase 70",
        "remain Phase 64",
        "No owner is added, renamed, removed, or transferred by Slice 16.",
    ):
        assert phrase in normalized_spec, phrase
    for phrase in (
        "Same-select window-to-window dependencies, nested window calls",
        "not an anonymous deferral",
    ):
        assert phrase in " ".join(_read(SPEC_REL).split()) or phrase in spec, phrase


def test_package_version_tag_release_and_rust_closure_is_locked() -> None:
    metadata = tomllib.loads(_read("pyproject.toml"))
    assert metadata["project"]["version"] == "0.1.0"
    assert metadata["project"]["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
    assert _git_output(["tag", "--list"]) == ""
    assert _git_output(["tag", "--points-at", "HEAD"]) == ""
    tracked = _git_output(["ls-files"]).splitlines()
    assert not any(path.endswith(".rs") for path in tracked)
    assert "Cargo.toml" not in tracked
    normalized_spec = " ".join(_read(SPEC_REL).split())
    for phrase in (
        "no release occurs before the separately authorized post-Phase-60 release route",
        "No v1.0 readiness is claimed",
        "No big-bang Rust rewrite",
        "remote package manager, registry, fetch, install, solver, or lockfile feature",
    ):
        assert phrase in normalized_spec, phrase
    roadmap = " ".join(_read(ROADMAP_REL).split())
    assert "Phase 60 Gate 3 must not tag or publish" in roadmap
    assert "The migration policy forbids a big-bang rewrite" in roadmap


def test_generated_golden_fixture_workflow_dependency_stability_is_locked() -> None:
    paths = _readable_paths()
    goldens = tuple(path for path in paths if path.startswith("tests/fixtures/golden/"))
    assert (
        len(goldens),
        sum(path.endswith(".sql") for path in goldens),
        sum(path.endswith(".json") for path in goldens),
    ) == (37, 32, 5)
    workflows = tuple(path for path in paths if path.startswith(".github/workflows/"))
    assert workflows == (".github/workflows/ci.yml",)
    assert {relative: _sha256(relative) for relative in PROTECTED_SHA256} == (
        PROTECTED_SHA256
    )
    assert _sha256(ROADMAP_REL) == ROADMAP_SHA256
    assert "ruff>=0.16.0" in _read("pyproject.toml")
    assert 'name = "ruff"\nversion = "0.16.0"' in _read("uv.lock")


def test_live_compiler_semantic_phase15_project_protected_version_and_tag_locks_are_dirty_safe() -> (
    None
):
    compiler = _compiler_paths()
    semantic = tuple((REPO_ROOT / "src/pietto/semantic").glob("*.py"))
    phase15 = tuple(
        path
        for path in semantic
        if path.name not in {"analyzer.py", "model.py", "relationship_metadata.py"}
    )
    project = _project_paths()
    assert (len(compiler), len(semantic), len(phase15), len(project)) == (
        108,
        36,
        33,
        33,
    )
    assert {
        "compiler": _digest(compiler),
        "semantic": _digest(semantic),
        "phase15": _digest(phase15),
        "project": _digest(project),
    } == PATH_DIGESTS
    tracked = set(_git_output(["diff", "--name-only"]).splitlines()) - {""}
    untracked = set(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    ) - {""}
    _assert_allowed_dirty_state(
        tracked=tracked,
        untracked=untracked,
        branch=_git_output(["branch", "--show-current"]),
        head=_git_output(["rev-parse", "HEAD"]),
        main=_git_optional_ref("refs/heads/main"),
        origin_main=_git_optional_ref("refs/remotes/origin/main"),
    )


def test_static_reader_hash_topology_test_inventory_and_validation_manifests_are_locked() -> (
    None
):
    readable = _readable_paths()
    assert (
        len(readable),
        sum(path.endswith(".py") for path in readable),
        sum(path.endswith(".md") for path in readable),
    ) == (944, 579, 269)
    test_files = tuple((REPO_ROOT / "tests").glob("test_*.py"))
    top_functions = sum(
        len(_top_level_test_functions(f"tests/{path.name}")) for path in test_files
    )
    assert (len(test_files), top_functions) == (465, 5489)
    for digest, expected in (
        (PATH_DIGESTS["compiler"], 28),
        (PATH_DIGESTS["semantic"], 42),
        (PATH_DIGESTS["phase15"], 17),
        (PATH_DIGESTS["project"], 22),
    ):
        readers = tuple(
            path
            for path in readable
            if digest.encode() in (REPO_ROOT / path).read_bytes()
        )
        assert len(readers) == expected
        assert SELF_REL in readers
    window_readers = tuple(
        path
        for path in readable
        if CAPABILITY_WINDOWS_SHA256.encode() in (REPO_ROOT / path).read_bytes()
    )
    assert len(window_readers) == 6 and SELF_REL in window_readers
    for relative, expected in (
        (".github/workflows/ci.yml", 12),
        ("pyproject.toml", 12),
        ("uv.lock", 13),
    ):
        digest = PROTECTED_SHA256[relative]
        readers = tuple(
            path
            for path in readable
            if digest.encode() in (REPO_ROOT / path).read_bytes()
        )
        assert len(readers) == expected and SELF_REL in readers
    assert 10784 + 16 == 10800
    assert 10800 - 185 == 10615
    assert 4765 + 16 == 4781
    overlay = cast(
        tuple[str, ...],
        _module_literal(
            "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
            "DIRTY_OVERLAY",
        ),
    )
    overlay_payload = ("\n".join(overlay) + "\n").encode("utf-8")
    assert (
        len(overlay),
        len(overlay_payload),
        hashlib.sha256(overlay_payload).hexdigest(),
    ) == (
        185,
        23628,
        "197b591aec962f43b9b9393da99a76ff21c3a36189cc02c7a75dc5a7b85d6b26",
    )
    assert _sha256(SELF_REL) not in _read(SELF_REL)


def test_completion_encoding_gate2_gate3_ci_and_phase54_boundaries_are_locked() -> None:
    spec = _read(SPEC_REL)
    plan = _read(PLAN_REL)
    normalized_spec = " ".join(spec.split())
    normalized_plan = " ".join(plan.split())
    for phrase in (
        "phase53/slice16-completion-audit-status-lock",
        SLICE16_COMMIT_SUBJECT,
        "10800",
        "generated count 8",
        "golden count 37",
        "package smoke PASS",
        "installed CLI `pietto 0.1.0`",
        "PHASE54_GATE0_GATE1",
    ):
        assert phrase in normalized_spec, phrase
    for phrase in (
        "phase53/slice16-completion-audit-status-lock",
        SLICE16_COMMIT_SUBJECT,
        "`10800 passed`",
        "PHASE54_GATE0_GATE1",
    ):
        assert phrase in normalized_plan, phrase
    assert "There is no post-CI status-flip commit" in normalized_spec
    assert plan.count(SLICE16_BASE_SUBJECT) == 1
    assert (
        plan.count(
            "## Slice 16 — Completion Audit, Status Lock, Dialect, Privacy, "
            "And No-authority Closure"
        )
        == 1
    )
    assert _git_output(["diff", "--cached", "--name-status"]) == ""


def test_static_git_helper_and_exact_slice16_dirty_set_are_locked() -> None:
    tree = ast.parse(_read(SELF_REL), filename=SELF_REL)
    subprocess_helpers = tuple(
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and any(
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and isinstance(call.func.value, ast.Name)
            and call.func.value.id == "subprocess"
            and call.func.attr == "run"
            for call in ast.walk(node)
        )
    )
    assert subprocess_helpers == (
        "_git_output",
        "_git_optional_ref",
        "_git_commit_exists",
    )
    assert len(SLICE16_ALLOWLIST_PATHS) == 26
    assert len(SLICE16_MODIFIED_PATHS) == 24
    assert len(SLICE16_ADDED_PATHS) == 2
    assert sum(path.endswith(".py") for path in SLICE16_ALLOWLIST_PATHS) == 24
    assert sum(path.endswith(".md") for path in SLICE16_ALLOWLIST_PATHS) == 2
    state_modified = cast(set[str], _module_literal(SLICE2_STATE_REL, "MODIFIED_PATHS"))
    state_added = cast(set[str], _module_literal(SLICE2_STATE_REL, "ADDED_PATHS"))
    assert state_modified == SLICE16_MODIFIED_PATHS
    assert state_added == SLICE16_ADDED_PATHS
    forbidden_bypasses = (
        "git " + "fetch",
        "--" + "unshallow",
        "pytest." + "skip",
        "pytest." + "xfail",
    )
    assert all(token not in _read(SELF_REL) for token in forbidden_bypasses)
    tracked = set(_git_output(["diff", "--name-only"]).splitlines()) - {""}
    name_status = tuple(_git_output(["diff", "--name-status"]).splitlines())
    untracked = set(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    ) - {""}
    assert _git_output(["diff", "--cached", "--name-status"]) == ""
    _assert_allowed_dirty_state(
        tracked=tracked,
        untracked=untracked,
        branch=_git_output(["branch", "--show-current"]),
        head=_git_output(["rev-parse", "HEAD"]),
        main=_git_optional_ref("refs/heads/main"),
        origin_main=_git_optional_ref("refs/remotes/origin/main"),
    )
    if tracked or untracked:
        if phase54_slice11_python313_repair_is_active():
            expected_modified = set(PHASE54_SLICE11_PYTHON313_REPAIR_MODIFIED_PATHS)
            expected_added = set()
        elif phase54_slice11_substantive_recovery_is_active():
            expected_modified = set(PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_MODIFIED_PATHS)
            expected_added = set()
        elif phase54_slice11_pr_ci_repair_is_active():
            expected_modified = set(PHASE54_SLICE11_PR_CI_REPAIR_MODIFIED_PATHS)
            expected_added = set()
        elif phase54_slice12_pr_ci_repair_is_active():
            expected_modified = set(PHASE54_SLICE12_PR_CI_REPAIR_MODIFIED_PATHS)
            expected_added = set()
        elif phase54_slice12_product_repair3_is_active():
            expected_modified = set(PHASE54_SLICE12_PRODUCT_REPAIR3_MODIFIED_PATHS)
            expected_added = set()
        elif phase54_slice12_mechanical_repair4_is_active():
            expected_modified = set(PHASE54_SLICE12_MECHANICAL_REPAIR4_MODIFIED_PATHS)
            expected_added = set()
        elif phase54_slice12_mechanical_repair3_is_active():
            expected_modified = set(PHASE54_SLICE12_MECHANICAL_REPAIR3_MODIFIED_PATHS)
            expected_added = set()
        elif phase54_slice12_product_repair14_is_active():
            expected_modified = set(PHASE54_SLICE12_PRODUCT_REPAIR14_MODIFIED_PATHS)
            expected_added = set()
        elif phase54_slice12_product_repair13_is_active():
            expected_modified = set(PHASE54_SLICE12_PRODUCT_REPAIR13_MODIFIED_PATHS)
            expected_added = set()
        elif phase54_slice12_product_repair12_is_active():
            expected_modified = set(PHASE54_SLICE12_PRODUCT_REPAIR12_MODIFIED_PATHS)
            expected_added = set()
        elif phase54_slice12_product_repair11_is_active():
            expected_modified = set(PHASE54_SLICE12_PRODUCT_REPAIR11_MODIFIED_PATHS)
            expected_added = set()
        elif phase54_slice12_product_repair10_is_active():
            expected_modified = set(PHASE54_SLICE12_PRODUCT_REPAIR10_MODIFIED_PATHS)
            expected_added = set()
        elif tracked | untracked == set(
            phase54_post_slice12_interlude_expected_modified_paths()
        ) | set(phase54_post_slice12_interlude_expected_added_paths()):
            expected_modified = set(
                phase54_post_slice12_interlude_expected_modified_paths()
            )
            expected_added = set(phase54_post_slice12_interlude_expected_added_paths())
        elif _phase54_active_gate2_is_active() or _git_output(
            ["rev-parse", "HEAD"]
        ) in {
            "d8a5e9ab3de70ce30575513c73560c86430eca63",
            "93f0f591e28a01f32d1698fcd4b8c57d41c6d714",
            "15bae172ee151e370fe59d3bf909d735aee6aa90",
            "0f3c955c5a5fbd8046ef611ad1bef0b636c8be01",
            "c44a4271d9592cb393d2232f127a59d8466cc60a",
            "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16",
            "027b33cafcfd58916a89e299487dad38d24ade6c",
            "0ceb9a476e6592714cdc76845949ba0ae5123eb5",
            "b81843acadb294630db361c09949868d004b1bca",
            "bc46faff1c9aa71f583ed7d2964b651cc659bc90",
            "0bad854253e22347e2aff93e2eabcbe2fda55aed",
            "040ab19c56519c39c56541979c850484f9cc47f0",
        }:
            expected_modified = cast(
                set[str],
                _module_literal(PHASE54_SLICE2_STATE_REL, "NON_READER_MODIFIED_PATHS"),
            ) | cast(
                set[str],
                _module_literal(PHASE54_SLICE2_STATE_REL, "MECHANICAL_READER_PATHS"),
            )
            expected_added = cast(
                set[str],
                _module_literal(PHASE54_SLICE2_STATE_REL, "ADDED_PATHS"),
            )
        else:
            expected_modified = SLICE16_MODIFIED_PATHS
            expected_added = SLICE16_ADDED_PATHS
        assert tracked == expected_modified
        assert untracked == expected_added
        assert name_status == tuple(f"M\t{path}" for path in sorted(expected_modified))
    else:
        assert name_status == ()
