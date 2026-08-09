from __future__ import annotations

import ast
import hashlib
import re
import subprocess
import tomllib
from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

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
    PHASE54_SLICE12_PRODUCT_REPAIR3_SUBJECT,
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
import pietto.semantic.capability_contexts as capability_contexts
import pietto.semantic.capability_facts as capability_facts
import pietto.semantic.capability_inventory as capability_inventory
import pietto.semantic.capability_lookup as capability_lookup
import pietto.semantic.capability_signatures as capability_signatures
import pietto.semantic.capability_windows as capability_windows
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
SELF_REL = "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py"
SPEC_REL = "docs/spec/phase52-parity-privacy-cross-phase-readiness-drift-closure-v1.md"
SLICE1_TEST_REL = (
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py"
)
SLICE2_TEST_REL = "tests/test_phase52_private_capability_fact_foundation.py"
SLICE3_TEST_REL = "tests/test_phase52_fail_closed_capability_lookup.py"
SLICE4_TEST_REL = (
    "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py"
)
SLICE5_TEST_REL = "tests/test_phase52_scalar_function_operator_signature_facts.py"
SLICE6_TEST_REL = "tests/test_phase52_expression_stage_clause_capability_facts.py"
SLICE7_TEST_REL = "tests/test_phase52_aggregate_signature_algebra_facts.py"
SLICE9_SPEC_REL = "docs/spec/phase52-completion-audit-and-status-lock-v1.md"
SLICE9_TEST_REL = "tests/test_phase52_completion_audit_and_status_lock.py"

FACTS_REL = "src/pietto/semantic/capability_facts.py"
LOOKUP_REL = "src/pietto/semantic/capability_lookup.py"
INVENTORY_REL = "src/pietto/semantic/capability_inventory.py"
SIGNATURE_REL = "src/pietto/semantic/capability_signatures.py"
CONTEXT_REL = "src/pietto/semantic/capability_contexts.py"
AGGREGATE_REL = "src/pietto/semantic/capability_aggregates.py"
WINDOW_REL = "src/pietto/semantic/capability_windows.py"
MODULE_RELS = (
    FACTS_REL,
    LOOKUP_REL,
    INVENTORY_REL,
    SIGNATURE_REL,
    CONTEXT_REL,
    AGGREGATE_REL,
    WINDOW_REL,
)
MODULE_OBJECTS = (
    capability_facts,
    capability_lookup,
    capability_inventory,
    capability_signatures,
    capability_contexts,
    capability_aggregates,
    capability_windows,
)

GATE2_BASE_HEAD_SHA = "11a0c48941c3c1c650be8d0ec8ddf5201f9525f2"
GATE2_BASE_PARENT_SHA = "7bea69da0465f57580961e4ca4a2c18a84dfb68c"
GATE2_BASE_TREE_SHA = "2953c238f27239d796c9af05543b48c1add2a69d"
CI_REPAIR_BASE_HEAD_SHA = "7a221ffdca91335a526ed12a1059340bda642fdb"
SLICE9_BASE_HEAD_SHA = "36e466535d923f708a0201ae15a5708f06f2b1f8"
MODULE_SHA256 = {
    FACTS_REL: "bd68bad4e13a2b945962458fc47359a408d27b1563ba25f5713a8f8099671d21",
    LOOKUP_REL: "4d4c2676b3181758f01c95ca312fd0f76cebcb74ac1bcab0deefb15fc04abf26",
    INVENTORY_REL: "f11eee2a53fda26057c35be047bfa265c68794ad76054bc5636781f0b5164b26",
    SIGNATURE_REL: "810f347080e0bb7dc674821aa6387c5f7618ac216832194ef19820326eef71d2",
    CONTEXT_REL: "132371eccca00ca9f8722a34f1ea0f540933515e560639ee12e53aee6594c60c",
    AGGREGATE_REL: "d7d69fa4b97924ef5462af9c871a910b73cad43a21431e98a72c8bdab8996c80",
    WINDOW_REL: "c0512933fc284bbc1dec98dab96411ee179d64e7bee005aa798b6fd7dba2024e",
}
SPEC_SHA256 = "7010cd8a39ed389de588d8cd734b136cc87456c3ef5eb324638467d1188fc935"
MODIFIED_TEST_SHA256 = {
    SLICE4_TEST_REL: "d780e57469b9b9006d0674ec02634908440841fa556d8bf3c67ead16fb7e351a",
    SLICE5_TEST_REL: "0cbbf60cc59d7bd0088ad9535ac75a2edfd652167ffe422e0c7461bb240dbd45",
    SLICE6_TEST_REL: "e3c09f570f74dc141a06181bfe79c49725c9fad82c0d7d3087de7b90cca8ede6",
    SLICE7_TEST_REL: "7f8e2c3e94e0babcfeb870c172855715acb13217152633e306d7234c8935d403",
}
WORKFLOW_SHA256 = "4db1c9a49b0af230bae3f088bf84524e210e0afcd6a87250322e5036a69e8d94"
PYPROJECT_SHA256 = "36aa8e1d19a8409e56e0163a465b9608a88c1bffe644165ba49db49bf5ec3d01"
LOCK_SHA256 = "a7d9125995e98a8a74d3664ceae7801cc1f4cce74ec323933da67838be199cea"
COMPILER_DIGEST = "fd4b8fcd41dc66be686880805bb6afaa4ab32efa5ae95159f88ada704ae69a9c"
SEMANTIC_DIGEST = "731e17cc85849c7716abeb08abeda03f72e3e21af183a391107adf96ccab6d70"
PHASE15_SUBSET_DIGEST = (
    "81db265a7bbd290b9c9227733e92dc502f8e8c8f0ff76b4d631651772876550d"
)
PROJECT_PRIVATE_DIGEST = (
    "3c619932e4fd1a4f2b3f12f4801d10c30030e8a6691d7cb63dd86a315b822439"
)

SPEC_H2 = (
    "Status And Authority",
    "Static-only Architecture And Scope",
    "Domain Fact Key And Ownership Inventory",
    "Completeness Schema And Malformed Key Closure",
    "Four-result Lookup And Ordering Parity",
    "Evidence Backend Support And Disposition Parity",
    "Conflict And Omission Ledger",
    "Private Import Export And Consumer Closure",
    "No-authority No-behavior And Source-integrity Closure",
    "Cross-phase Readiness Through Phase 60",
    "Phase 53 Window Handoff",
    "PR Merge-ref And Repository-state Compatibility",
    "Drift-closure And Static-reader Invariants",
    "Slice 8 Validation And Evidence Contract",
    "Lifecycle Gate 3 And Release Boundary",
)
EXPECTED_TEST_NAMES = (
    "test_slice8_artifacts_headings_authority_and_static_only_shape_are_exact",
    "test_all_six_private_module_api_dependency_and_byte_sentinels_are_exact",
    "test_capability_domain_population_and_reservation_matrix_is_exact",
    "test_slice4_7_fact_key_totals_duplicates_and_collisions_are_exact",
    "test_fact_order_domain_ownership_and_combined_inventory_are_deterministic",
    "test_all_populated_completeness_schemas_are_exact",
    "test_canonical_complete_zero_match_and_open_position_absence_are_exact",
    "test_malformed_closed_future_dialect_extension_keys_are_unknown",
    "test_division_and_backend_gap_unknown_reasons_are_exact",
    "test_found_absent_unknown_conflict_precedence_and_duplicate_folding_are_exact",
    "test_each_family_lookup_input_filtering_completeness_and_reason_are_exact",
    "test_conflict_evidence_order_and_count_shape_real_conflict_are_exact",
    "test_canonical_evidence_source_order_paths_references_and_scope_are_exact",
    "test_postgresql_private_mysql_support_lowering_matrix_is_exact",
    "test_support_disposition_owner_reason_and_affirmative_evidence_are_exact",
    "test_winner_free_conflict_and_omission_ledger_is_exact",
    "test_private_import_ast_dynamic_export_and_package_boundary_is_exact",
    "test_no_forbidden_compiler_project_public_serializer_runtime_consumer_exists",
    "test_no_authority_behavior_and_repository_sentinels_are_exact",
    "test_cross_phase_53_60_handoff_matrix_is_exact",
    "test_post60_owner_and_out_of_scope_matrix_is_exact",
    "test_phase53_window_handoff_remains_unpopulated_and_unknown",
    "test_clean_main_synthetic_merge_dirty_and_historical_repository_states_are_exact",
    "test_pr19_pr20_workflow_dependency_package_tag_and_ref_locks_are_exact",
    "test_static_reader_counts_boundary_hash_and_nested_sha_topology_are_exact",
    "test_test_inventory_tier1_selectors_and_compatibility_counts_are_exact",
    "test_tier2_manifest_identity_presence_uniqueness_and_clean_only_classification_are_exact",
    "test_slice8_gate2_gate3_lifecycle_release_and_next_gate_are_exact",
)

SLICE8_MODIFIED_PATHS = {
    SLICE4_TEST_REL,
    SLICE5_TEST_REL,
    SLICE6_TEST_REL,
    SLICE7_TEST_REL,
}
SLICE8_ADDED_PATHS = {SPEC_REL, SELF_REL}
SLICE8_ALLOWLIST_PATHS = SLICE8_MODIFIED_PATHS | SLICE8_ADDED_PATHS
CI_REPAIR_MODIFIED_PATHS = {SELF_REL}
SLICE9_MODIFIED_PATHS = {
    "docs/plan/phase-52-core-type-system-capability-foundation.md",
    "docs/spec/pietto-active-roadmap-phase51-60-v1.md",
    SLICE1_TEST_REL,
    SLICE5_TEST_REL,
    SLICE6_TEST_REL,
    SLICE7_TEST_REL,
    SELF_REL,
}
SLICE9_ADDED_PATHS = {SLICE9_SPEC_REL, SLICE9_TEST_REL}
SLICE9_ALLOWLIST_PATHS = SLICE9_MODIFIED_PATHS | SLICE9_ADDED_PATHS

DIRECT_TIER1_BYTES = 4860
DIRECT_TIER1_SHA256 = "417a72e2091fdd85e8b1d5f76bc4a21a64e55dbdb1eb87de4318a1b344a67faf"
COMPATIBLE_TIER1_BYTES = 8708
COMPATIBLE_TIER1_SHA256 = (
    "ad36af418104abe3afb21e94e1f64e87762ec2006047151c20ddb7047b25392a"
)
TIER1_OPERAND_BYTES = 5525
TIER1_OPERAND_SHA256 = (
    "2097b7aace8604cb54af6392a9e400543fa7eefac4423f810d8a37451c05d48b"
)
TIER2_MANIFEST_BYTES = 18026
TIER2_MANIFEST_SHA256 = (
    "6ab2027b7c8cb7858fbea2d3902130a4a860e462102ac4e582990f4bcfa501bf"
)

EVIDENCE_SOURCE_COUNTS = {
    CapabilityEvidenceSource.GRAMMAR_AST: 267,
    CapabilityEvidenceSource.SEMANTIC_CATALOG: 87,
    CapabilityEvidenceSource.SEMANTIC_PROCEDURE: 397,
    CapabilityEvidenceSource.SEMANTIC_MODEL: 130,
    CapabilityEvidenceSource.IR: 247,
    CapabilityEvidenceSource.BACKEND: 236,
    CapabilityEvidenceSource.PROJECT: 129,
    CapabilityEvidenceSource.PUBLIC: 18,
    CapabilityEvidenceSource.ROADMAP: 90,
    CapabilityEvidenceSource.TEST: 465,
    CapabilityEvidenceSource.SPEC: 307,
}


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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
        ref, object_name = line.split("\t", maxsplit=1)
        assert ref and re.fullmatch(r"[0-9a-f]{40}", object_name)
        refs.append((ref, object_name))
    return tuple(refs)


def _commit_available_from_batch_output(commit: str, output: str) -> bool:
    assert re.fullmatch(r"[0-9a-f]{40}", commit)
    if output == f"{commit} commit\n":
        return True
    if output == f"{commit} missing\n":
        return False
    raise AssertionError(f"unexpected git object result: {output!r}")


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
    return _commit_available_from_batch_output(commit, result.stdout)


def _historical_objects_available(
    *,
    head_available: bool,
    parent_available: bool,
) -> bool:
    assert head_available == parent_available
    return head_available


def _assert_checkout_ref_shape(
    *,
    branch: str,
    head: str,
    main: str | None,
    origin_main: str | None,
    refs: tuple[tuple[str, str], ...],
    exact_main_refs: bool,
) -> bool:
    if branch == "main":
        assert main == head
        if origin_main is not None:
            assert origin_main == head
        if exact_main_refs:
            assert origin_main == head
            assert refs == (
                ("refs/heads/main", head),
                ("refs/remotes/origin/main", head),
            )
        return False

    if branch == phase54_publication_topic_branch():
        assert phase54_publication_clean_topic_is_active()
        return False

    assert branch == ""
    assert len(refs) == 1
    merge_ref, merge_head = refs[0]
    assert re.fullmatch(r"refs/remotes/pull/[1-9][0-9]*/merge", merge_ref)
    assert merge_head == head
    assert main is None
    assert origin_main is None
    return True


def _synthetic_merge_parents(raw_commit: str) -> tuple[str, str]:
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
    return cast(tuple[str, str], parents)


def _assert_materialized_synthetic_merge(
    *,
    parents: tuple[str, str],
    merge_base: str,
    second_parent_tree: str,
    merge_tree: str,
) -> None:
    assert merge_base == parents[0]
    assert second_parent_tree == merge_tree


def _assert_clean_checkout_refs(
    *,
    branch: str,
    head: str,
    main: str | None,
    origin_main: str | None,
    exact_main_refs: bool = False,
) -> None:
    if phase54_slice12_mechanical_repair4_clean_topic_is_active():
        assert branch == PHASE54_SLICE12_MECHANICAL_REPAIR4_BRANCH
        assert main == origin_main == PHASE54_ACTIVE_GATE2_BASE
        assert tuple(
            _git_output(["rev-list", "--parents", "-n", "1", head]).split()[1:]
        ) == (PHASE54_SLICE12_MECHANICAL_REPAIR4_BASE,)
        assert _git_output(["show", "-s", "--format=%s", head]) == (
            PHASE54_SLICE12_MECHANICAL_REPAIR4_SUBJECT
        )
        return
    if phase54_slice12_mechanical_repair3_clean_topic_is_active():
        assert branch == PHASE54_SLICE12_MECHANICAL_REPAIR3_BRANCH
        assert main == origin_main == PHASE54_ACTIVE_GATE2_BASE
        assert tuple(
            _git_output(["rev-list", "--parents", "-n", "1", head]).split()[1:]
        ) == (PHASE54_SLICE12_MECHANICAL_REPAIR3_BASE,)
        assert _git_output(["show", "-s", "--format=%s", head]) == (
            PHASE54_SLICE12_MECHANICAL_REPAIR3_SUBJECT
        )
        return
    if phase54_slice12_product_repair14_clean_topic_is_active():
        assert branch == PHASE54_SLICE12_PRODUCT_REPAIR14_BRANCH
        assert main == origin_main == PHASE54_ACTIVE_GATE2_BASE
        assert tuple(
            _git_output(["rev-list", "--parents", "-n", "1", head]).split()[1:]
        ) == (PHASE54_SLICE12_PRODUCT_REPAIR14_BASE,)
        assert _git_output(["show", "-s", "--format=%s", head]) == (
            PHASE54_SLICE12_PRODUCT_REPAIR14_SUBJECT
        )
        return
    if phase54_slice12_product_repair13_clean_topic_is_active():
        assert branch == PHASE54_SLICE12_PRODUCT_REPAIR13_BRANCH
        assert main == origin_main == PHASE54_ACTIVE_GATE2_BASE
        assert tuple(
            _git_output(["rev-list", "--parents", "-n", "1", head]).split()[1:]
        ) == (PHASE54_SLICE12_PRODUCT_REPAIR13_BASE,)
        assert _git_output(["show", "-s", "--format=%s", head]) == (
            PHASE54_SLICE12_PRODUCT_REPAIR13_SUBJECT
        )
        return
    if phase54_slice12_product_repair12_clean_topic_is_active():
        assert branch == PHASE54_SLICE12_PRODUCT_REPAIR12_BRANCH
        assert main == origin_main == PHASE54_ACTIVE_GATE2_BASE
        assert tuple(
            _git_output(["rev-list", "--parents", "-n", "1", head]).split()[1:]
        ) == (PHASE54_SLICE12_PRODUCT_REPAIR12_BASE,)
        assert _git_output(["show", "-s", "--format=%s", head]) == (
            PHASE54_SLICE12_PRODUCT_REPAIR12_SUBJECT
        )
        return
    if phase54_slice12_product_repair11_clean_topic_is_active():
        assert branch == PHASE54_SLICE12_PRODUCT_REPAIR11_BRANCH
        assert main == origin_main == PHASE54_ACTIVE_GATE2_BASE
        assert tuple(
            _git_output(["rev-list", "--parents", "-n", "1", head]).split()[1:]
        ) == (PHASE54_SLICE12_PRODUCT_REPAIR11_BASE,)
        assert _git_output(["show", "-s", "--format=%s", head]) == (
            PHASE54_SLICE12_PRODUCT_REPAIR11_SUBJECT
        )
        return
    if phase54_slice12_product_repair10_clean_topic_is_active():
        assert branch == PHASE54_SLICE12_PRODUCT_REPAIR10_BRANCH
        assert main == origin_main == PHASE54_ACTIVE_GATE2_BASE
        assert tuple(
            _git_output(["rev-list", "--parents", "-n", "1", head]).split()[1:]
        ) == (PHASE54_SLICE12_PRODUCT_REPAIR10_BASE,)
        assert _git_output(["show", "-s", "--format=%s", head]) == (
            PHASE54_SLICE12_PRODUCT_REPAIR10_SUBJECT
        )
        return
    if phase54_slice12_product_repair3_clean_topic_is_active():
        assert branch == PHASE54_SLICE12_PRODUCT_REPAIR3_BRANCH
        assert main == origin_main == PHASE54_ACTIVE_GATE2_BASE
        assert tuple(
            _git_output(["rev-list", "--parents", "-n", "1", head]).split()[1:]
        ) == (PHASE54_SLICE12_PRODUCT_REPAIR3_BASE,)
        assert _git_output(["show", "-s", "--format=%s", head]) == (
            PHASE54_SLICE12_PRODUCT_REPAIR3_SUBJECT
        )
        return
    refs = _git_refs()
    synthetic = _assert_checkout_ref_shape(
        branch=branch,
        head=head,
        main=main,
        origin_main=origin_main,
        refs=refs,
        exact_main_refs=exact_main_refs,
    )
    if not synthetic:
        return

    raw_commit = _git_output(["cat-file", "-p", head])
    parents = _synthetic_merge_parents(raw_commit)

    parent_objects_exist = tuple(_git_commit_exists(parent) for parent in parents)
    assert len(set(parent_objects_exist)) == 1
    if all(parent_objects_exist):
        _assert_materialized_synthetic_merge(
            parents=parents,
            merge_base=_git_output(["merge-base", *parents]),
            second_parent_tree=_git_output(["rev-parse", f"{parents[1]}^{{tree}}"]),
            merge_tree=_git_output(["rev-parse", f"{head}^{{tree}}"]),
        )


def _assert_clean_shallow_state(
    *,
    shallow: str,
    status: str,
    staged: str,
) -> None:
    assert shallow == "true"
    assert status == ""
    assert staged == ""


def _assert_clean_shallow_checkout() -> None:
    _assert_clean_shallow_state(
        shallow=_git_output(["rev-parse", "--is-shallow-repository"]),
        status=_git_output(["status", "--porcelain=v1", "--untracked-files=all"]),
        staged=_git_output(["diff", "--cached", "--name-only"]),
    )
    branch = _git_output(["branch", "--show-current"])
    head = _git_output(["rev-parse", "HEAD"])
    _assert_clean_checkout_refs(
        branch=branch,
        head=head,
        main=_git_optional_ref("refs/heads/main"),
        origin_main=_git_optional_ref("refs/remotes/origin/main"),
        exact_main_refs=True,
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
    ):
        assert branch == "main"
        assert head == main == origin_main == PHASE54_ACTIVE_GATE2_BASE
        return
    dirty = tracked | untracked
    slice13_modified = _slice13_paths("MODIFIED_PATHS")
    slice13_added = _slice13_paths("ADDED_PATHS")
    slice13_allowlist = slice13_modified | slice13_added
    assert dirty in (
        set(),
        SLICE8_ALLOWLIST_PATHS,
        CI_REPAIR_MODIFIED_PATHS,
        SLICE9_ALLOWLIST_PATHS,
        slice13_allowlist,
        set(phase54_post_slice12_interlude_expected_allowlist_paths()),
    )
    if not dirty:
        return

    if phase54_post_slice12_interlude_repair_is_active():
        assert branch == phase54_publication_topic_branch()
        assert tracked == set(phase54_post_slice12_interlude_expected_modified_paths())
        assert untracked == set(phase54_post_slice12_interlude_expected_added_paths())
        assert head == phase54_post_slice12_interlude_expected_head()
        assert main == origin_main == phase54_publication_topic_base()
        return

    assert branch == "main"
    if dirty == slice13_allowlist:
        assert tracked == slice13_modified
        assert untracked == slice13_added
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
        return

    if dirty == SLICE9_ALLOWLIST_PATHS:
        assert tracked == SLICE9_MODIFIED_PATHS
        assert untracked == SLICE9_ADDED_PATHS
        assert head == main == origin_main == SLICE9_BASE_HEAD_SHA
        return

    if phase54_post_slice12_interlude_dirty_is_active():
        assert tracked == set(phase54_post_slice12_interlude_expected_modified_paths())
        assert untracked == set(phase54_post_slice12_interlude_expected_added_paths())
        assert (
            head
            == main
            == origin_main
            == phase54_post_slice12_interlude_expected_head()
        )
        return

    if dirty == SLICE8_ALLOWLIST_PATHS:
        assert tracked == SLICE8_MODIFIED_PATHS
        assert untracked == SLICE8_ADDED_PATHS
        assert head == main == origin_main == GATE2_BASE_HEAD_SHA
        return

    assert tracked == CI_REPAIR_MODIFIED_PATHS
    assert untracked == set()
    assert head == main == origin_main == CI_REPAIR_BASE_HEAD_SHA


def _readable_paths() -> tuple[str, ...]:
    tracked = _git_output(["ls-files"]).splitlines()
    untracked = _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    return tuple(
        sorted(
            path
            for path in {*tracked, *untracked}
            if path and (REPO_ROOT / path).is_file()
        )
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


def _facts(module: object, name: str) -> tuple[CapabilityFact, ...]:
    return cast(tuple[CapabilityFact, ...], getattr(module, name))


def _families() -> tuple[tuple[CapabilityFact, ...], ...]:
    return (
        _facts(capability_inventory, "_CAPABILITY_FACTS"),
        _facts(capability_signatures, "_CAPABILITY_SIGNATURE_FACTS"),
        _facts(capability_contexts, "_CAPABILITY_CONTEXT_FACTS"),
        _facts(capability_aggregates, "_AGGREGATE_CAPABILITY_FACTS"),
        _facts(capability_windows, "_WINDOW_CAPABILITY_FACTS"),
    )


def _all_facts() -> tuple[CapabilityFact, ...]:
    return tuple(fact for family in _families() for fact in family)


def _helper_inputs(
    key: CapabilityKey,
) -> tuple[tuple[CapabilityFact, ...], bool, CapabilityReasonCode | None]:
    if key.domain in {
        CapabilityDomain.LOGICAL_TYPE,
        CapabilityDomain.LITERAL,
        CapabilityDomain.PARAMETER,
    }:
        facts, complete = cast(Any, capability_inventory.inventory_lookup_inputs)(key)
        return facts, complete, None
    if key.domain in {
        CapabilityDomain.SCALAR_FUNCTION,
        CapabilityDomain.UNARY_OPERATOR,
        CapabilityDomain.BINARY_OPERATOR,
        CapabilityDomain.COMPARISON,
        CapabilityDomain.NULL_TEST,
    }:
        return cast(Any, capability_signatures.signature_lookup_inputs)(key)
    if key.domain in {CapabilityDomain.EXPRESSION_STAGE, CapabilityDomain.CLAUSE}:
        return cast(Any, capability_contexts.stage_clause_lookup_inputs)(key)
    if key.domain is CapabilityDomain.AGGREGATE:
        return cast(Any, capability_aggregates.aggregate_lookup_inputs)(key)
    if key.domain is CapabilityDomain.WINDOW_FUNCTION:
        return cast(Any, capability_windows.window_lookup_inputs)(key)
    return (), False, None


def _lookup(key: CapabilityKey) -> Found | Absent | Unknown | Conflict:
    facts, complete, reason = _helper_inputs(key)
    return lookup_capability(
        key,
        facts,
        domain_complete=complete,
        unknown_reason=reason,
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


def _compatible_nodes() -> tuple[tuple[str, ...], tuple[int, ...]]:
    files = (SLICE2_TEST_REL, SLICE3_TEST_REL, SLICE4_TEST_REL)
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


def _backend_records(fact: CapabilityFact) -> tuple[Any, ...]:
    return tuple(
        evidence
        for evidence in fact.evidence
        if evidence.source is CapabilityEvidenceSource.BACKEND
    )


def _dual_backend_facts(
    facts: tuple[CapabilityFact, ...],
) -> tuple[CapabilityFact, ...]:
    expected = {("postgresql", "postgresql"), ("mysql", "private-mysql")}
    return tuple(
        fact
        for fact in facts
        if {(item.dialect, item.backend) for item in _backend_records(fact)} == expected
    )


def test_slice8_artifacts_headings_authority_and_static_only_shape_are_exact() -> None:
    spec = _read(REPO_ROOT / SPEC_REL)
    headings = tuple(
        match.group(1).strip()
        for match in re.finditer(r"^## (?!#)(.+?)\s*$", spec, re.MULTILINE)
    )
    assert headings == SPEC_H2
    assert not re.search(r"\b[0-9a-f]{64}\b", spec)
    for required in (
        "static-only specification and focused-audit work",
        "167 entries / 166 unique\nkeys",
        "28 top-level test functions and 69 pytest items",
        "two added files, four modified test\nfiles, and zero deleted files",
        "Phase 52 remains active and incomplete",
        "Add Phase 52 parity privacy and drift closure",
    ):
        assert required in spec


def test_all_six_private_module_api_dependency_and_byte_sentinels_are_exact() -> None:
    assert tuple(MODULE_SHA256) == MODULE_RELS
    assert tuple(module.__all__ for module in MODULE_OBJECTS) == ((),) * 7
    assert {
        relative: _sha256(REPO_ROOT / relative) for relative in MODULE_RELS
    } == MODULE_SHA256
    for relative in MODULE_RELS:
        tree = ast.parse(_read(REPO_ROOT / relative), filename=relative)
        capability_imports = {
            node.module
            for node in tree.body
            if isinstance(node, ast.ImportFrom)
            and node.module is not None
            and node.module.startswith("pietto.semantic.capability_")
        }
        if relative == FACTS_REL:
            assert capability_imports == set()
        else:
            assert capability_imports == {"pietto.semantic.capability_facts"}


@pytest.mark.parametrize(
    ("domain", "expected_count", "owner"),
    (
        (CapabilityDomain.LOGICAL_TYPE, 25, "slice4"),
        (CapabilityDomain.LITERAL, 13, "slice4"),
        (CapabilityDomain.PARAMETER, 3, "slice4"),
        (CapabilityDomain.SCALAR_FUNCTION, 4, "slice5"),
        (CapabilityDomain.UNARY_OPERATOR, 4, "slice5"),
        (CapabilityDomain.BINARY_OPERATOR, 21, "slice5"),
        (CapabilityDomain.COMPARISON, 8, "slice5"),
        (CapabilityDomain.NULL_TEST, 2, "slice5"),
        (CapabilityDomain.EXPRESSION_STAGE, 7, "slice6"),
        (CapabilityDomain.CLAUSE, 11, "slice6"),
        (CapabilityDomain.AGGREGATE, 69, "slice7"),
        (CapabilityDomain.WINDOW_FUNCTION, 24, "phase53_slice15"),
        (CapabilityDomain.CONVERSION, 0, "post60_reserved"),
        (CapabilityDomain.EXTENSION_SIGNATURE, 0, "phase57_reserved"),
    ),
)
def test_capability_domain_population_and_reservation_matrix_is_exact(
    domain: CapabilityDomain,
    expected_count: int,
    owner: str,
) -> None:
    facts = tuple(fact for fact in _all_facts() if fact.key.domain is domain)
    assert len(facts) == expected_count
    expected_owners = {
        CapabilityDomain.LOGICAL_TYPE: "slice4",
        CapabilityDomain.LITERAL: "slice4",
        CapabilityDomain.PARAMETER: "slice4",
        CapabilityDomain.SCALAR_FUNCTION: "slice5",
        CapabilityDomain.UNARY_OPERATOR: "slice5",
        CapabilityDomain.BINARY_OPERATOR: "slice5",
        CapabilityDomain.COMPARISON: "slice5",
        CapabilityDomain.NULL_TEST: "slice5",
        CapabilityDomain.EXPRESSION_STAGE: "slice6",
        CapabilityDomain.CLAUSE: "slice6",
        CapabilityDomain.AGGREGATE: "slice7",
        CapabilityDomain.WINDOW_FUNCTION: "phase53_slice15",
        CapabilityDomain.CONVERSION: "post60_reserved",
        CapabilityDomain.EXTENSION_SIGNATURE: "phase57_reserved",
    }
    assert expected_owners[domain] == owner
    assert all(fact.key.domain is domain for fact in facts)
    assert not any(
        fact.key.domain is CapabilityDomain.DIALECT_LOWERING for fact in _all_facts()
    )


def test_slice4_7_fact_key_totals_duplicates_and_collisions_are_exact() -> None:
    families = _families()
    assert tuple(
        (len(family), len({fact.key for fact in family})) for family in families
    ) == (
        (41, 41),
        (39, 39),
        (18, 18),
        (69, 68),
        (24, 24),
    )
    facts = _all_facts()
    assert (len(facts), len({fact.key for fact in facts})) == (191, 190)
    assert len(set(facts)) == 191
    repeated = tuple(
        key for key, count in Counter(fact.key for fact in facts).items() if count > 1
    )
    assert len(repeated) == 1
    assert repeated[0] == CapabilityKey(
        CapabilityDomain.AGGREGATE,
        subject="count",
        operation="signature",
        operands=(
            "1",
            "direct_field",
            "Shape",
            "Int",
            "non_null",
            "GROUP",
            "aggregate_result",
        ),
        context="aggregate_signature",
    )
    family_keys = tuple({fact.key for fact in family} for family in families)
    assert all(
        family_keys[left].isdisjoint(family_keys[right])
        for left in range(len(family_keys))
        for right in range(left + 1, len(family_keys))
    )


def test_fact_order_domain_ownership_and_combined_inventory_are_deterministic() -> None:
    inventory, signatures, contexts, aggregates, windows = _families()
    assert _all_facts() == (*inventory, *signatures, *contexts, *aggregates, *windows)
    assert inventory == (
        *_facts(capability_inventory, "_LOGICAL_TYPE_FACTS"),
        *_facts(capability_inventory, "_LITERAL_FACTS"),
        *_facts(capability_inventory, "_PARAMETER_FACTS"),
        *_facts(capability_inventory, "_NULLABILITY_FACTS"),
    )
    assert signatures == (
        *_facts(capability_signatures, "_SCALAR_FUNCTION_FACTS"),
        *_facts(capability_signatures, "_UNARY_OPERATOR_FACTS"),
        *_facts(capability_signatures, "_BINARY_OPERATOR_FACTS"),
        *_facts(capability_signatures, "_COMPARISON_FACTS"),
        *_facts(capability_signatures, "_NULL_TEST_FACTS"),
    )
    assert contexts == (
        *_facts(capability_contexts, "_EXPRESSION_STAGE_FACTS"),
        *_facts(capability_contexts, "_CLAUSE_CAPABILITY_FACTS"),
    )
    assert aggregates == (
        *_facts(capability_aggregates, "_AGGREGATE_SIGNATURE_FACTS"),
        *_facts(capability_aggregates, "_AGGREGATE_ALGEBRA_FACTS"),
    )
    assert windows == (
        *_facts(capability_windows, "_WINDOW_SIGNATURE_FACTS"),
        *_facts(capability_windows, "_WINDOW_LOWERING_FACTS"),
    )


@pytest.mark.parametrize(
    "schema_group",
    (
        "inventory_logical_type",
        "inventory_literal",
        "inventory_parameter",
        "signature_scalar",
        "signature_operators",
        "context_stage",
        "context_clause",
        "aggregate_signature_and_algebra",
    ),
)
def test_all_populated_completeness_schemas_are_exact(schema_group: str) -> None:
    inventory, signatures, contexts, aggregates, _windows = _families()
    if schema_group == "inventory_logical_type":
        keys = tuple(
            fact.key
            for fact in inventory
            if fact.key.domain is CapabilityDomain.LOGICAL_TYPE
        )
        assert keys and all(_helper_inputs(key)[1] for key in keys)
        malformed = replace(keys[-1], operands=("future",))
    elif schema_group == "inventory_literal":
        keys = tuple(
            fact.key
            for fact in inventory
            if fact.key.domain is CapabilityDomain.LITERAL
        )
        assert keys and all(_helper_inputs(key)[1] for key in keys)
        malformed = replace(keys[0], operands=("Int",))
    elif schema_group == "inventory_parameter":
        keys = tuple(
            fact.key
            for fact in inventory
            if fact.key.domain is CapabilityDomain.PARAMETER
        )
        assert keys and all(_helper_inputs(key)[1] for key in keys)
        malformed = replace(keys[0], context="future_context")
    elif schema_group == "signature_scalar":
        keys = tuple(
            fact.key
            for fact in signatures
            if fact.key.domain is CapabilityDomain.SCALAR_FUNCTION
        )
        assert keys and all(_helper_inputs(key)[1] for key in keys)
        assert _helper_inputs(replace(keys[0], operation="future_builtin"))[1]
        malformed = replace(keys[0], operands=("Text", "future_tail"))
    elif schema_group == "signature_operators":
        keys = tuple(
            fact.key
            for fact in signatures
            if fact.key.domain is not CapabilityDomain.SCALAR_FUNCTION
        )
        assert keys and all(_helper_inputs(key)[1] for key in keys)
        malformed = replace(keys[0], operands=("Int", "unknown"))
    elif schema_group == "context_stage":
        keys = tuple(
            fact.key
            for fact in contexts
            if fact.key.domain is CapabilityDomain.EXPRESSION_STAGE
        )
        assert keys and all(_helper_inputs(key)[1] for key in keys)
        malformed = replace(keys[0], operands=("WINDOW",))
    elif schema_group == "context_clause":
        keys = tuple(
            fact.key for fact in contexts if fact.key.domain is CapabilityDomain.CLAUSE
        )
        assert keys and all(_helper_inputs(key)[1] for key in keys)
        malformed = replace(keys[0], operands=("ROW",))
    else:
        assert schema_group == "aggregate_signature_and_algebra"
        keys = tuple(fact.key for fact in aggregates)
        assert keys and all(_helper_inputs(key)[1] for key in keys)
        malformed = replace(keys[0], operands=keys[0].operands[:-1])
    assert _helper_inputs(malformed)[1] is False


def test_canonical_complete_zero_match_and_open_position_absence_are_exact() -> None:
    shape_key = CapabilityKey(
        CapabilityDomain.AGGREGATE,
        subject="count",
        operation="signature",
        operands=(
            "1",
            "direct_field",
            "Shape",
            "Int",
            "non_null",
            "GROUP",
            "aggregate_result",
        ),
        context="aggregate_signature",
    )
    for fact in _all_facts():
        result = _lookup(fact.key)
        if fact.key == shape_key:
            assert isinstance(result, Conflict)
        else:
            assert result == Found(fact)

    absent_keys = (
        CapabilityKey(
            CapabilityDomain.LITERAL,
            subject="integer",
            operation="result",
            operands=("Float", "non_null"),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            subject="FutureBuiltin",
            operation="catalog_membership",
            context="builtin_registry",
        ),
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            subject="future_declaration",
            operation="declaration_kind",
            context="semantic_model",
        ),
        CapabilityKey(
            CapabilityDomain.SCALAR_FUNCTION,
            subject="Text",
            operation="future_builtin",
            operands=("Text", "unknown"),
            context="expression",
        ),
    )
    for key in absent_keys:
        assert _helper_inputs(key)[1] is True
        assert _lookup(key) == Absent(key, CapabilityReasonCode.NO_CATALOG_ENTRY)


def test_malformed_closed_future_dialect_extension_keys_are_unknown() -> None:
    clause = _facts(capability_contexts, "_CLAUSE_CAPABILITY_FACTS")[0].key
    keys = (
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            subject="implicit",
            operation="effective_nullability",
            operands=("future",),
            context="type_expression",
        ),
        CapabilityKey(
            CapabilityDomain.LITERAL,
            subject="integer",
            operation="result",
            operands=("Int",),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.PARAMETER,
            subject="future_parameter",
            operation="declare",
            operands=("name", "TypeExpr"),
            context="callable_declaration",
        ),
        CapabilityKey(
            CapabilityDomain.SCALAR_FUNCTION,
            subject="FutureType",
            operation="lower",
            operands=("Text", "unknown"),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.UNARY_OPERATOR,
            subject="Int",
            operation="+",
            operands=("Int", "PRESERVE_OPERAND"),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.EXPRESSION_STAGE,
            subject="literal_expression",
            operation="observed_stage",
            operands=("WINDOW",),
            context="expression",
        ),
        replace(
            clause,
            operands=(*clause.operands[:2], "future_shape", *clause.operands[3:]),
        ),
        replace(clause, dialect="postgresql"),
        replace(clause, dialect="postgresql", extension="future_extension"),
    )
    assert all(
        _lookup(key) == Unknown(CapabilityReasonCode.NOT_EVIDENCED) for key in keys
    )


def test_division_and_backend_gap_unknown_reasons_are_exact() -> None:
    division = CapabilityKey(
        CapabilityDomain.BINARY_OPERATOR,
        subject="Int",
        operation="/",
        operands=("Int", "Int", "unknown"),
        context="expression",
    )
    matches_mysql = CapabilityKey(
        CapabilityDomain.SCALAR_FUNCTION,
        subject="Text",
        operation="matches",
        operands=("Text", "Bool", "unknown"),
        context="expression",
        dialect="mysql",
    )
    like = CapabilityKey(
        CapabilityDomain.COMPARISON,
        subject="Expression",
        operation="like",
        operands=("Expression", "Bool", "unknown"),
        context="expression",
    )
    assert _lookup(division) == Unknown(CapabilityReasonCode.NO_CURRENT_RESULT_RULE)
    assert _lookup(matches_mysql) == Unknown(CapabilityReasonCode.DIALECT_LOWERING_GAP)
    assert _lookup(replace(like, dialect="postgresql")) == Unknown(
        CapabilityReasonCode.DIALECT_LOWERING_GAP
    )
    assert _lookup(replace(like, dialect="mysql")) == Unknown(
        CapabilityReasonCode.DIALECT_LOWERING_GAP
    )


def test_found_absent_unknown_conflict_precedence_and_duplicate_folding_are_exact() -> (
    None
):
    fact = _all_facts()[0]
    distinct = replace(fact, support=CapabilitySupport.EXPLICITLY_UNSUPPORTED)
    assert lookup_capability(fact.key, (fact,), domain_complete=True) == Found(fact)
    assert lookup_capability(fact.key, (fact, fact), domain_complete=True) == Found(
        fact
    )
    assert lookup_capability(
        fact.key, (fact, distinct), domain_complete=True
    ) == Conflict(CapabilityReasonCode.CONFLICTING_EVIDENCE, (fact, distinct))
    assert lookup_capability(
        fact.key, (distinct, fact), domain_complete=True
    ) == Conflict(CapabilityReasonCode.CONFLICTING_EVIDENCE, (distinct, fact))
    missing = replace(fact.key, subject="NoCatalogEntry")
    assert lookup_capability(missing, (fact,), domain_complete=True) == Absent(missing)
    assert lookup_capability(
        missing,
        (fact,),
        domain_complete=False,
        unknown_reason=CapabilityReasonCode.NOT_EVIDENCED,
    ) == Unknown(CapabilityReasonCode.NOT_EVIDENCED)
    with pytest.raises(ValueError, match="exact capability facts"):
        lookup_capability(
            fact.key,
            cast(Any, (fact, object())),
            domain_complete=True,
        )


def test_each_family_lookup_input_filtering_completeness_and_reason_are_exact() -> None:
    inventory, signatures, contexts, aggregates, windows = _families()
    expected_by_domain = {
        CapabilityDomain.LOGICAL_TYPE: tuple(
            fact
            for fact in inventory
            if fact.key.domain is CapabilityDomain.LOGICAL_TYPE
        ),
        CapabilityDomain.LITERAL: tuple(
            fact for fact in inventory if fact.key.domain is CapabilityDomain.LITERAL
        ),
        CapabilityDomain.PARAMETER: tuple(
            fact for fact in inventory if fact.key.domain is CapabilityDomain.PARAMETER
        ),
        CapabilityDomain.SCALAR_FUNCTION: _facts(
            capability_signatures, "_SCALAR_FUNCTION_FACTS"
        ),
        CapabilityDomain.UNARY_OPERATOR: _facts(
            capability_signatures, "_UNARY_OPERATOR_FACTS"
        ),
        CapabilityDomain.BINARY_OPERATOR: _facts(
            capability_signatures, "_BINARY_OPERATOR_FACTS"
        ),
        CapabilityDomain.COMPARISON: _facts(capability_signatures, "_COMPARISON_FACTS"),
        CapabilityDomain.NULL_TEST: _facts(capability_signatures, "_NULL_TEST_FACTS"),
        CapabilityDomain.EXPRESSION_STAGE: _facts(
            capability_contexts, "_EXPRESSION_STAGE_FACTS"
        ),
        CapabilityDomain.CLAUSE: _facts(
            capability_contexts, "_CLAUSE_CAPABILITY_FACTS"
        ),
        CapabilityDomain.AGGREGATE: aggregates,
        CapabilityDomain.WINDOW_FUNCTION: windows,
    }
    for domain, expected in expected_by_domain.items():
        key = next(fact.key for fact in _all_facts() if fact.key.domain is domain)
        facts, complete, reason = _helper_inputs(key)
        if domain is CapabilityDomain.AGGREGATE:
            expected = (
                _facts(capability_aggregates, "_AGGREGATE_SIGNATURE_FACTS")
                if key.context == "aggregate_signature"
                else _facts(capability_aggregates, "_AGGREGATE_ALGEBRA_FACTS")
            )
        elif domain is CapabilityDomain.WINDOW_FUNCTION:
            expected = (
                _facts(capability_windows, "_WINDOW_SIGNATURE_FACTS")
                if key.context == "window_signature"
                else _facts(capability_windows, "_WINDOW_LOWERING_FACTS")
            )
        assert facts == expected
        assert complete is True
        assert reason is None

    foreign = CapabilityKey(
        CapabilityDomain.CONVERSION,
        subject="Int",
        operation="convert",
        operands=("Text",),
        context="expression",
    )
    assert _helper_inputs(foreign) == ((), False, None)
    assert cast(Any, capability_inventory.inventory_lookup_inputs)(foreign) == (
        (),
        False,
    )
    assert cast(Any, capability_signatures.signature_lookup_inputs)(foreign) == (
        (),
        False,
        None,
    )
    assert cast(Any, capability_contexts.stage_clause_lookup_inputs)(foreign) == (
        (),
        False,
        None,
    )
    assert cast(Any, capability_aggregates.aggregate_lookup_inputs)(foreign) == (
        (),
        False,
        None,
    )
    assert cast(Any, capability_windows.window_lookup_inputs)(foreign) == (
        (),
        False,
        None,
    )


@pytest.mark.parametrize(
    ("index", "support", "backend_count"),
    (
        (0, CapabilitySupport.SUPPORTED, 0),
        (1, CapabilitySupport.EXPLICITLY_UNSUPPORTED, 2),
    ),
)
def test_conflict_evidence_order_and_count_shape_real_conflict_are_exact(
    index: int,
    support: CapabilitySupport,
    backend_count: int,
) -> None:
    shape_facts = tuple(
        fact
        for fact in _facts(capability_aggregates, "_AGGREGATE_SIGNATURE_FACTS")
        if fact.key.subject == "count" and "Shape" in fact.key.operands
    )
    assert len(shape_facts) == 2
    fact = shape_facts[index]
    assert fact.support is support
    assert fact.disposition.kind is CapabilityDispositionKind.NONE
    assert len(_backend_records(fact)) == backend_count
    if backend_count:
        assert tuple(item.reason for item in _backend_records(fact)) == (
            CapabilityReasonCode.DIALECT_LOWERING_GAP,
            CapabilityReasonCode.DIALECT_LOWERING_GAP,
        )
    assert _lookup(fact.key) == Conflict(
        CapabilityReasonCode.CONFLICTING_EVIDENCE,
        shape_facts,
    )


def test_canonical_evidence_source_order_paths_references_and_scope_are_exact() -> None:
    evidence = tuple(item for fact in _all_facts() for item in fact.evidence)
    assert len(evidence) == 2373
    assert Counter(item.source for item in evidence) == EVIDENCE_SOURCE_COUNTS
    source_order = {
        source: index for index, source in enumerate(CapabilityEvidenceSource)
    }
    for fact in _all_facts():
        indexes = tuple(source_order[item.source] for item in fact.evidence)
        assert indexes == tuple(sorted(indexes))
        backend = _backend_records(fact)
        if len(backend) == 2:
            assert tuple((item.dialect, item.backend) for item in backend) == (
                ("postgresql", "postgresql"),
                ("mysql", "private-mysql"),
            )
    for item in evidence:
        assert (REPO_ROOT / item.source_path).is_file()
        assert item.source_reference.strip() == item.source_reference
        assert item.source_reference
        assert item.extension is None
        if item.source is CapabilityEvidenceSource.BACKEND:
            assert (item.dialect, item.backend) in {
                ("postgresql", "postgresql"),
                ("mysql", "private-mysql"),
            }
        else:
            assert item.dialect is None
            assert item.backend is None


@pytest.mark.parametrize(
    "matrix_case",
    (
        "slice4",
        "slice5",
        "slice6",
        "slice7",
        "combined",
        "positive_supported",
        "matches",
        "like",
        "conflict_and_grouped_unsupported",
    ),
)
def test_postgresql_private_mysql_support_lowering_matrix_is_exact(
    matrix_case: str,
) -> None:
    families = _families()
    dual_by_family = tuple(_dual_backend_facts(family) for family in families)
    if matrix_case in {"slice4", "slice5", "slice6", "slice7"}:
        index = ("slice4", "slice5", "slice6", "slice7").index(matrix_case)
        assert (
            len(dual_by_family[index]),
            sum(len(_backend_records(fact)) for fact in dual_by_family[index]),
        ) == (
            (5, 10),
            (39, 78),
            (6, 12),
            (60, 120),
        )[index]
    elif matrix_case == "combined":
        dual = _dual_backend_facts(_all_facts())
        assert (len(dual), sum(len(_backend_records(fact)) for fact in dual)) == (
            110,
            220,
        )
    elif matrix_case == "positive_supported":
        dual = _dual_backend_facts(_all_facts())
        positive = tuple(
            fact
            for fact in dual
            if fact.support is CapabilitySupport.SUPPORTED
            and all(item.reason is None for item in _backend_records(fact))
        )
        assert len(positive) == 106
    elif matrix_case == "matches":
        fact = next(
            fact
            for fact in _all_facts()
            if fact.key.domain is CapabilityDomain.SCALAR_FUNCTION
            and fact.key.operation == "matches"
        )
        assert fact.support is CapabilitySupport.SUPPORTED
        assert tuple(item.reason for item in _backend_records(fact)) == (
            None,
            CapabilityReasonCode.DIALECT_LOWERING_GAP,
        )
    elif matrix_case == "like":
        fact = next(
            fact
            for fact in _all_facts()
            if fact.key.domain is CapabilityDomain.COMPARISON
            and fact.key.operation == "like"
        )
        assert fact.support is CapabilitySupport.SUPPORTED
        assert tuple(item.reason for item in _backend_records(fact)) == (
            CapabilityReasonCode.DIALECT_LOWERING_GAP,
            CapabilityReasonCode.DIALECT_LOWERING_GAP,
        )
    else:
        assert matrix_case == "conflict_and_grouped_unsupported"
        unsupported = tuple(
            fact
            for fact in _dual_backend_facts(_all_facts())
            if fact.support is CapabilitySupport.EXPLICITLY_UNSUPPORTED
        )
        assert tuple((fact.key.domain, fact.key.subject) for fact in unsupported) == (
            (CapabilityDomain.CLAUSE, "order_by"),
            (CapabilityDomain.AGGREGATE, "count"),
        )
        assert all(len(_backend_records(fact)) == 2 for fact in unsupported)


def test_support_disposition_owner_reason_and_affirmative_evidence_are_exact() -> None:
    facts = _all_facts()
    assert Counter(fact.support for fact in facts) == {
        CapabilitySupport.SUPPORTED: 162,
        CapabilitySupport.EXPLICITLY_UNSUPPORTED: 29,
    }
    assert Counter(fact.disposition.kind for fact in facts) == {
        CapabilityDispositionKind.NONE: 176,
        CapabilityDispositionKind.DEFERRED: 14,
        CapabilityDispositionKind.OUT_OF_SCOPE: 1,
    }
    assert Counter(fact.disposition.owner for fact in facts) == {
        None: 176,
        "POST60_ADVANCED_TYPE_NATIVE_MAPPING": 7,
        "POST60_ADVANCED_AGGREGATION_GROUPING": 7,
        "Pietto charter": 1,
    }
    affirmative_sources = {
        CapabilityEvidenceSource.GRAMMAR_AST,
        CapabilityEvidenceSource.SEMANTIC_CATALOG,
        CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
        CapabilityEvidenceSource.SEMANTIC_MODEL,
        CapabilityEvidenceSource.IR,
        CapabilityEvidenceSource.BACKEND,
        CapabilityEvidenceSource.PROJECT,
        CapabilityEvidenceSource.TEST,
    }
    for fact in facts:
        if fact.disposition.kind is CapabilityDispositionKind.NONE:
            assert fact.disposition.owner is None
            assert fact.disposition.reason is None
        else:
            assert fact.disposition.owner
            assert fact.disposition.reason
        if fact.support is CapabilitySupport.EXPLICITLY_UNSUPPORTED:
            assert any(item.source in affirmative_sources for item in fact.evidence)


def test_winner_free_conflict_and_omission_ledger_is_exact() -> None:
    spec = _read(REPO_ROOT / SPEC_REL)
    ledger = tuple(
        match.group(1) for match in re.finditer(r"^([0-9]+)\. ", spec, re.MULTILINE)
    )
    assert ledger.count("1") >= 2
    for required in (
        "`count(Shape)` remains the single ordered conflict",
        "Generic `LIKE` remains semantically supported with two backend gaps",
        "`matches(Text, Text)` retains positive PostgreSQL",
        "Parsed non-Decimal type arguments remain generally unconsumed",
        "Division has no current result rule",
        "Null literal, unresolved expression, and unknown nullability",
        "Generic comparison produces outer `Bool UNKNOWN`",
        "No-GROUP post-filtering remains rejected",
        "Aggregate semantic recognition does not imply backend renderability",
        "`WINDOW` remains reserved and unpopulated",
        "Malformed-key completeness is regression-locked",
    ):
        assert required in spec
    shape_result = _lookup(
        next(
            fact.key
            for fact in _all_facts()
            if fact.key.subject == "count" and "Shape" in fact.key.operands
        )
    )
    assert isinstance(shape_result, Conflict)


@pytest.mark.parametrize(
    ("relative", "module"),
    (
        (FACTS_REL, capability_facts),
        (LOOKUP_REL, capability_lookup),
        (INVENTORY_REL, capability_inventory),
        (SIGNATURE_REL, capability_signatures),
        (CONTEXT_REL, capability_contexts),
        (AGGREGATE_REL, capability_aggregates),
    ),
)
def test_private_import_ast_dynamic_export_and_package_boundary_is_exact(
    relative: str,
    module: object,
) -> None:
    source = _read(REPO_ROOT / relative)
    tree = ast.parse(source, filename=relative)
    assert getattr(module, "__all__") == ()
    assert not any(isinstance(node, ast.Import) for node in tree.body)
    assert not any(
        isinstance(node, ast.Call)
        and (
            isinstance(node.func, ast.Name)
            and node.func.id == "__import__"
            or isinstance(node.func, ast.Attribute)
            and node.func.attr in {"import_module", "entry_points"}
        )
        for node in ast.walk(tree)
    )
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
        for token in ("registry", "callback", "consumer", "dispatcher")
    )
    assert "capability_" not in _read(REPO_ROOT / "src/pietto/semantic/__init__.py")
    assert "capability_" not in _read(REPO_ROOT / "src/pietto/__init__.py")


def test_no_forbidden_compiler_project_public_serializer_runtime_consumer_exists() -> (
    None
):
    forbidden_names = {
        "inventory_lookup_inputs",
        "signature_lookup_inputs",
        "stage_clause_lookup_inputs",
        "aggregate_lookup_inputs",
        "window_lookup_inputs",
    }
    module_stems = {Path(path).stem for path in MODULE_RELS}
    preservation_rel = "src/pietto/_project/module_semantic_fact_preservation.py"
    for path in (REPO_ROOT / "src/pietto").rglob("*.py"):
        relative = path.relative_to(REPO_ROOT).as_posix()
        if relative in {*MODULE_RELS, preservation_rel} or "generated" in path.parts:
            continue
        source = _read(path)
        assert all(name not in source for name in forbidden_names)
        assert all(f"semantic.{stem}" not in source for stem in module_stems)
    for directory in ("_project", "sql", "metadata"):
        root = REPO_ROOT / "src/pietto" / directory
        if root.exists():
            assert all(
                "capability_" not in _read(path)
                for path in root.rglob("*.py")
                if "generated" not in path.parts
                and path.relative_to(REPO_ROOT).as_posix() != preservation_rel
            )
    preservation_source = _read(REPO_ROOT / preservation_rel)
    assert all(name in preservation_source for name in forbidden_names)
    assert "__all__: tuple[str, ...] = ()" in preservation_source


def test_no_authority_behavior_and_repository_sentinels_are_exact() -> None:
    expected = {
        **MODULE_SHA256,
        ".github/workflows/ci.yml": WORKFLOW_SHA256,
        "pyproject.toml": PYPROJECT_SHA256,
        "uv.lock": LOCK_SHA256,
    }
    assert {
        relative: _sha256(REPO_ROOT / relative) for relative in expected
    } == expected
    tracked = set(_git_output(["diff", "--name-only"]).splitlines()) - {""}
    untracked = set(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    ) - {""}
    dirty = tracked | untracked
    _assert_allowed_dirty_state(
        tracked=tracked,
        untracked=untracked,
        branch=_git_output(["branch", "--show-current"]),
        head=_git_output(["rev-parse", "HEAD"]),
        main=_git_optional_ref("refs/heads/main"),
        origin_main=_git_optional_ref("refs/remotes/origin/main"),
    )
    assert len(SLICE8_ALLOWLIST_PATHS) == 6
    assert CI_REPAIR_MODIFIED_PATHS == {SELF_REL}
    assert sum(path.endswith(".py") for path in SLICE8_ALLOWLIST_PATHS) == 5
    assert sum(path.endswith(".md") for path in SLICE8_ALLOWLIST_PATHS) == 1
    assert set(MODULE_RELS).isdisjoint(dirty)
    workflow = _read(REPO_ROOT / ".github/workflows/ci.yml")
    assert (
        "actions/setup-java@03ad4de0992f5dab5e18fcb136590ce7c4a0ac95 # v5.6.0"
        in workflow
    )
    project = _read(REPO_ROOT / "pyproject.toml")
    lock = _read(REPO_ROOT / "uv.lock")
    assert 'version = "0.1.0"' in project
    assert 'requires = ["uv_build>=0.11.32,<0.12.0"]' in project
    assert "ruff>=0.16.0" in project
    assert 'name = "ruff"\nversion = "0.16.0"' in lock


@pytest.mark.parametrize(
    ("phase", "title", "handoff"),
    (
        (
            53,
            "Window Function Syntax And Capability Contract",
            "no window facts or behavior",
        ),
        (54, "Import / Module / Export Readiness", "no module implementation"),
        (55, "Semantic Package Asset Schema", "no manifest or loader"),
        (
            56,
            "Capability Profile Static Schema And Declared Checking",
            "no profile or checking",
        ),
        (
            57,
            "PostgreSQL Extension Signature-Catalog Readiness",
            "no catalog, signatures, or lowering",
        ),
        (
            58,
            "Project Explain / Portability / Public Metadata Readiness",
            "independent public artifact family",
        ),
        (
            59,
            "Package Graph And Lineage / Provenance Integration",
            "no graph or provenance work",
        ),
        (
            60,
            "Multi-dialect Capability Ecosystem Completion Checkpoint",
            "auditable facts, conflicts, and owners",
        ),
    ),
)
def test_cross_phase_53_60_handoff_matrix_is_exact(
    phase: int,
    title: str,
    handoff: str,
) -> None:
    spec = _read(REPO_ROOT / SPEC_REL)
    row = next(line for line in spec.splitlines() if line.startswith(f"| {phase} |"))
    assert title in row
    assert handoff in row


def test_post60_owner_and_out_of_scope_matrix_is_exact() -> None:
    spec = _read(REPO_ROOT / SPEC_REL)
    owners = (
        "POST60_ADVANCED_AGGREGATION_GROUPING",
        "POST60_ADVANCED_TYPE_NATIVE_MAPPING",
        "POST60_ADVANCED_WINDOWS",
        "POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT",
        "POST60_PROJECT_IR",
        "POST60_MULTI_RELATION_SQL",
        "POST60_PUBLIC_PROJECT_SCHEMA_LINEAGE_EXPANSION",
        "POST60_ADVANCED_MODULE_PACKAGE_ASSETS",
        "POST60_REMOTE_PACKAGE_MANAGER",
        "POST60_DEPENDENCY_SOLVER_LOCKFILE",
        "POST60_ADDITIONAL_DIALECT_BACKENDS",
        "POST60_EXTENSION_LOWERING",
        "OUT_OF_SCOPE_CHARTER",
    )
    for owner in owners:
        assert owner in spec
    actual = {
        fact.disposition.owner
        for fact in _all_facts()
        if fact.disposition.owner is not None
    }
    assert actual == {
        "POST60_ADVANCED_AGGREGATION_GROUPING",
        "POST60_ADVANCED_TYPE_NATIVE_MAPPING",
        "Pietto charter",
    }


def test_phase53_window_handoff_remains_unpopulated_and_unknown() -> None:
    facts = _all_facts()
    assert not any(
        fact.key.domain is CapabilityDomain.EXPRESSION_STAGE
        and "WINDOW" in fact.key.operands
        for fact in facts
    )
    assert not any(
        fact.key.domain is CapabilityDomain.AGGREGATE
        and (
            "window" in (fact.key.context or "").lower()
            or any("window" in operand.lower() for operand in fact.key.operands)
        )
        for fact in facts
    )
    window = CapabilityKey(
        CapabilityDomain.EXPRESSION_STAGE,
        subject="aggregate_dependent_expression",
        operation="observed_stage",
        operands=("WINDOW",),
        context="expression",
    )
    assert _helper_inputs(window)[1] is False
    assert _lookup(window) == Unknown(CapabilityReasonCode.NOT_EVIDENCED)
    window_facts = tuple(
        fact for fact in facts if fact.key.domain is CapabilityDomain.WINDOW_FUNCTION
    )
    assert window_facts == _facts(capability_windows, "_WINDOW_CAPABILITY_FACTS")
    assert len(window_facts) == len({fact.key for fact in window_facts}) == 24
    for key in (window_facts[0].key, window_facts[8].key):
        lookup_facts, complete, reason = _helper_inputs(key)
        assert complete is True
        assert reason is None
        assert key in {fact.key for fact in lookup_facts}
        assert _lookup(key) == Found(
            next(fact for fact in lookup_facts if fact.key == key)
        )
    spec = _read(REPO_ROOT / SPEC_REL)
    assert all(name in spec for name in ("row_number", "rank", "dense_rank"))


def test_clean_main_synthetic_merge_dirty_and_historical_repository_states_are_exact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tracked = set(_git_output(["diff", "--name-only"]).splitlines()) - {""}
    untracked = set(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    ) - {""}
    branch = _git_output(["branch", "--show-current"])
    head = _git_output(["rev-parse", "HEAD"])
    main = _git_optional_ref("refs/heads/main")
    origin_main = _git_optional_ref("refs/remotes/origin/main")
    _assert_allowed_dirty_state(
        tracked=tracked,
        untracked=untracked,
        branch=branch,
        head=head,
        main=main,
        origin_main=origin_main,
    )
    if not (tracked | untracked):
        _assert_clean_checkout_refs(
            branch=branch,
            head=head,
            main=main,
            origin_main=origin_main,
        )
    for relative in (
        SLICE1_TEST_REL,
        SLICE5_TEST_REL,
        SLICE6_TEST_REL,
        SLICE7_TEST_REL,
        SELF_REL,
    ):
        source = _read(REPO_ROOT / relative)
        assert "SLICE9_ALLOWLIST_PATHS" in source
        if relative != SLICE1_TEST_REL:
            assert "_assert_clean_checkout_refs" in source
        if relative not in {SLICE1_TEST_REL, SELF_REL}:
            assert "REPAIR_ALLOWLIST_PATHS" in source
            assert "PR_REPAIR_ALLOWLIST_PATHS" in source

    sample_head = "a" * 40
    other_head = "b" * 40
    with pytest.raises(AssertionError):
        _assert_clean_shallow_state(shallow="false", status="", staged="")
    with pytest.raises(AssertionError):
        _assert_clean_shallow_state(
            shallow="true",
            status=" M unexpected.py",
            staged="",
        )
    with pytest.raises(AssertionError):
        _assert_clean_shallow_state(
            shallow="true",
            status="",
            staged="M\tunexpected.py",
        )
    with pytest.raises(AssertionError):
        _assert_checkout_ref_shape(
            branch="",
            head=sample_head,
            main=None,
            origin_main=None,
            refs=(),
            exact_main_refs=True,
        )
    with pytest.raises(AssertionError):
        _assert_checkout_ref_shape(
            branch="main",
            head=sample_head,
            main=sample_head,
            origin_main=sample_head,
            refs=(
                ("refs/heads/main", sample_head),
                ("refs/heads/unexpected", sample_head),
                ("refs/remotes/origin/main", sample_head),
            ),
            exact_main_refs=True,
        )
    with pytest.raises(AssertionError):
        _assert_checkout_ref_shape(
            branch="",
            head=sample_head,
            main=None,
            origin_main=None,
            refs=(("refs/remotes/pull/0/merge", sample_head),),
            exact_main_refs=True,
        )
    with pytest.raises(AssertionError):
        _synthetic_merge_parents(
            f"tree {sample_head}\nparent {sample_head}\n\nMerge malformed"
        )
    with pytest.raises(AssertionError):
        _synthetic_merge_parents(
            f"tree {sample_head}\nparent {sample_head}\nparent {other_head}"
            f"\n\nMerge {sample_head} into {other_head}"
        )
    with pytest.raises(AssertionError):
        _assert_materialized_synthetic_merge(
            parents=(sample_head, other_head),
            merge_base=other_head,
            second_parent_tree=sample_head,
            merge_tree=sample_head,
        )
    with pytest.raises(AssertionError):
        _assert_materialized_synthetic_merge(
            parents=(sample_head, other_head),
            merge_base=sample_head,
            second_parent_tree=sample_head,
            merge_tree=other_head,
        )
    with pytest.raises(AssertionError):
        _historical_objects_available(
            head_available=True,
            parent_available=False,
        )
    with pytest.raises(AssertionError):
        _commit_available_from_batch_output(sample_head, f"{sample_head} blob\n")
    with pytest.raises(AssertionError):
        _assert_allowed_dirty_state(
            tracked={SLICE4_TEST_REL},
            untracked=set(),
            branch="main",
            head=CI_REPAIR_BASE_HEAD_SHA,
            main=CI_REPAIR_BASE_HEAD_SHA,
            origin_main=CI_REPAIR_BASE_HEAD_SHA,
        )
    with pytest.raises(AssertionError):
        _assert_allowed_dirty_state(
            tracked=SLICE9_MODIFIED_PATHS,
            untracked={"unexpected.txt"},
            branch="main",
            head=SLICE9_BASE_HEAD_SHA,
            main=SLICE9_BASE_HEAD_SHA,
            origin_main=SLICE9_BASE_HEAD_SHA,
        )
    with pytest.raises(AssertionError):
        _assert_allowed_dirty_state(
            tracked=CI_REPAIR_MODIFIED_PATHS,
            untracked={"unexpected.txt"},
            branch="main",
            head=CI_REPAIR_BASE_HEAD_SHA,
            main=CI_REPAIR_BASE_HEAD_SHA,
            origin_main=CI_REPAIR_BASE_HEAD_SHA,
        )

    def fail_git_command(*args: Any, **kwargs: Any) -> Any:
        raise subprocess.CalledProcessError(128, args[0])

    with monkeypatch.context() as scoped:
        scoped.setattr(subprocess, "run", fail_git_command)
        with pytest.raises(subprocess.CalledProcessError):
            _git_commit_exists(GATE2_BASE_HEAD_SHA)


def test_pr19_pr20_workflow_dependency_package_tag_and_ref_locks_are_exact() -> None:
    historical_objects_available = _historical_objects_available(
        head_available=_git_commit_exists(GATE2_BASE_HEAD_SHA),
        parent_available=_git_commit_exists(GATE2_BASE_PARENT_SHA),
    )
    if historical_objects_available:
        assert _git_output(["rev-parse", f"{GATE2_BASE_HEAD_SHA}^"]) == (
            GATE2_BASE_PARENT_SHA
        )
        assert _git_output(["rev-parse", f"{GATE2_BASE_HEAD_SHA}^{{tree}}"]) == (
            GATE2_BASE_TREE_SHA
        )
        assert _git_output(["show", "-s", "--format=%s", GATE2_BASE_HEAD_SHA]) == (
            "Bump actions/setup-java from 5.5.0 to 5.6.0"
        )
        assert (
            _git_output(["show", "-s", "--format=%s", GATE2_BASE_PARENT_SHA])
            == "Bump ruff from 0.15.21 to 0.15.22"
        )
        if _git_optional_ref("refs/heads/main") is not None:
            assert _git_output(["merge-base", "main", GATE2_BASE_HEAD_SHA]) == (
                GATE2_BASE_HEAD_SHA
            )
    else:
        _assert_clean_shallow_checkout()

    assert _sha256(REPO_ROOT / ".github/workflows/ci.yml") == WORKFLOW_SHA256
    assert _sha256(REPO_ROOT / "pyproject.toml") == PYPROJECT_SHA256
    assert _sha256(REPO_ROOT / "uv.lock") == LOCK_SHA256
    workflow = _read(REPO_ROOT / ".github/workflows/ci.yml")
    assert (
        "actions/setup-java@03ad4de0992f5dab5e18fcb136590ce7c4a0ac95 # v5.6.0"
        in workflow
    )
    assert _git_output(["tag", "--list"]) == ""
    assert _git_output(["tag", "--points-at", "HEAD"]) == ""
    with (REPO_ROOT / "pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream)
    assert project["project"]["version"] == "0.1.0"
    assert project["build-system"]["requires"] == ["uv_build>=0.11.32,<0.12.0"]
    assert "ruff>=0.16.0" in _read(REPO_ROOT / "pyproject.toml")
    assert 'name = "ruff"\nversion = "0.16.0"' in _read(REPO_ROOT / "uv.lock")


def test_static_reader_counts_boundary_hash_and_nested_sha_topology_are_exact() -> None:
    readable = _readable_paths()
    assert (
        sum(path.endswith(".py") for path in readable),
        sum(path.endswith(".md") for path in readable),
    ) == (575, 268)
    compiler_paths = _compiler_paths()
    semantic_paths = tuple((REPO_ROOT / "src/pietto/semantic").glob("*.py"))
    phase15_paths = tuple(
        path
        for path in semantic_paths
        if path.name not in {"analyzer.py", "model.py", "relationship_metadata.py"}
    )
    project_paths = _project_private_paths()
    assert (len(compiler_paths), len(semantic_paths), len(phase15_paths)) == (
        107,
        36,
        33,
    )
    assert len(project_paths) == 32
    assert _digest(compiler_paths) == COMPILER_DIGEST
    assert _digest(semantic_paths) == SEMANTIC_DIGEST
    assert _digest(phase15_paths) == PHASE15_SUBSET_DIGEST
    assert _digest(project_paths) == PROJECT_PRIVATE_DIGEST

    for digest, expected_count in (
        (COMPILER_DIGEST, 28),
        (SEMANTIC_DIGEST, 42),
        (PHASE15_SUBSET_DIGEST, 17),
        (PROJECT_PRIVATE_DIGEST, 22),
    ):
        readers = tuple(
            path
            for path in readable
            if digest.encode("ascii") in (REPO_ROOT / path).read_bytes()
        )
        assert len(readers) == expected_count
        assert SELF_REL in readers

    module_reader_counts = {
        FACTS_REL: 10,
        LOOKUP_REL: 7,
        INVENTORY_REL: 6,
        SIGNATURE_REL: 5,
        CONTEXT_REL: 4,
        AGGREGATE_REL: 3,
        WINDOW_REL: 6,
    }
    for relative, expected_count in module_reader_counts.items():
        readers = tuple(
            path
            for path in readable
            if MODULE_SHA256[relative].encode("ascii")
            in (REPO_ROOT / path).read_bytes()
        )
        assert len(readers) == expected_count
        assert SELF_REL in readers

    for digest, expected_count in (
        (WORKFLOW_SHA256, 12),
        (PYPROJECT_SHA256, 12),
        (LOCK_SHA256, 13),
    ):
        readers = tuple(
            path
            for path in readable
            if digest.encode("ascii") in (REPO_ROOT / path).read_bytes()
        )
        assert len(readers) == expected_count
        assert SELF_REL in readers

    boundary_owners = tuple(
        path
        for path in readable
        if re.search(
            rb'^BOUNDARY_HASH = "[0-9a-f]{64}"$',
            (REPO_ROOT / path).read_bytes(),
            re.MULTILINE,
        )
    )
    assert len(boundary_owners) == 8

    historical_topology = (
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
    assert len(historical_topology) == 5
    assert len({outer for _, outers in historical_topology for outer in outers}) == 4
    assert sum(len(outers) for _, outers in historical_topology) == 6
    for inner, expected_outers in historical_topology:
        inner_sha = _sha256(REPO_ROOT / inner)
        actual = tuple(
            path
            for path in readable
            if inner_sha.encode("ascii") in (REPO_ROOT / path).read_bytes()
        )
        assert actual == (
            *expected_outers,
            "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
            _SLICE10_READER_MIGRATION_PATHS[-1],
            "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
        )

    new_sha_edges = {SPEC_REL: SPEC_SHA256, **MODIFIED_TEST_SHA256}
    assert len(new_sha_edges) == 5
    for inner, expected_sha in new_sha_edges.items():
        assert _sha256(REPO_ROOT / inner) == expected_sha
        actual = tuple(
            path
            for path in readable
            if expected_sha.encode("ascii") in (REPO_ROOT / path).read_bytes()
        )
        expected_readers = (SELF_REL, _SLICE10_READER_MIGRATION_PATHS[-1])
        if inner != SPEC_REL:
            expected_readers = (
                SELF_REL,
                "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
                _SLICE10_READER_MIGRATION_PATHS[-1],
                "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
            )
        assert actual == expected_readers
    assert 6 + len(MODULE_RELS) + len(new_sha_edges) == 18
    self_sha = _sha256(REPO_ROOT / SELF_REL)
    self_readers = tuple(
        path
        for path in readable
        if self_sha.encode("ascii") in (REPO_ROOT / path).read_bytes()
    )
    assert self_readers == (
        "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
        _SLICE10_READER_MIGRATION_PATHS[-1],
        "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
    )
    git_blob_reader = "hash" + "-object"
    assert git_blob_reader not in _read(REPO_ROOT / SELF_REL)


def test_test_inventory_tier1_selectors_and_compatibility_counts_are_exact() -> None:
    function_count, item_count, parametrized, cardinalities = _pytest_shape(
        REPO_ROOT / SELF_REL
    )
    assert (function_count, item_count) == (28, 69)
    assert (
        tuple(
            node.name
            for node in ast.parse(_read(REPO_ROOT / SELF_REL), filename=SELF_REL).body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
        )
        == EXPECTED_TEST_NAMES
    )
    assert parametrized == [
        "test_capability_domain_population_and_reservation_matrix_is_exact",
        "test_all_populated_completeness_schemas_are_exact",
        "test_conflict_evidence_order_and_count_shape_real_conflict_are_exact",
        "test_postgresql_private_mysql_support_lowering_matrix_is_exact",
        "test_private_import_ast_dynamic_export_and_package_boundary_is_exact",
        "test_cross_phase_53_60_handoff_matrix_is_exact",
    ]
    assert cardinalities == [14, 8, 2, 9, 6, 8]

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
    assert (len(test_files), top_level_functions) == (464, 5437)
    assert tuple(
        _pytest_shape(REPO_ROOT / path)[1]
        for path in (
            SLICE1_TEST_REL,
            SLICE2_TEST_REL,
            SLICE3_TEST_REL,
            SLICE4_TEST_REL,
            SLICE5_TEST_REL,
            SLICE6_TEST_REL,
            SLICE7_TEST_REL,
            SELF_REL,
            SLICE9_TEST_REL,
        )
    ) == (12, 25, 34, 64, 64, 69, 69, 69, 11)

    direct = _literal_tuple(REPO_ROOT / SLICE7_TEST_REL, "DIRECT_TIER1_NODES")
    filtered_direct = tuple(
        node for node in direct if not node.startswith(SLICE1_TEST_REL)
    )
    tier1_deselections = (
        "--deselect="
        + SLICE2_TEST_REL
        + "::test_gate2_dirty_untracked_and_index_states_are_exact",
        "--deselect="
        + SLICE3_TEST_REL
        + "::test_gate2_dirty_untracked_and_index_states_are_exact",
        "--deselect="
        + SLICE4_TEST_REL
        + "::test_gate2_dirty_untracked_and_index_states_are_exact",
    )
    assert len(direct) == len(set(direct)) == 44
    operands = (
        SLICE1_TEST_REL,
        SLICE2_TEST_REL,
        SLICE3_TEST_REL,
        SLICE4_TEST_REL,
        SLICE5_TEST_REL,
        SLICE6_TEST_REL,
        SLICE7_TEST_REL,
        SELF_REL,
        SLICE9_TEST_REL,
        *tier1_deselections,
        *filtered_direct,
    )
    operand_payload = "".join(node + "\n" for node in operands).encode("utf-8")
    assert (
        len(operands),
        len(operand_payload),
        hashlib.sha256(operand_payload).hexdigest(),
    ) == (
        54,
        TIER1_OPERAND_BYTES,
        TIER1_OPERAND_SHA256,
    )
    assert sum((12, 25, 34, 64, 64, 69, 69, 69, 11)) + len(filtered_direct) == 459
    assert 464 - len(tier1_deselections) == 461
    assert 6156 + 11 == 6167


def test_tier2_manifest_identity_presence_uniqueness_and_clean_only_classification_are_exact() -> (
    None
):
    prior = _literal_tuple(REPO_ROOT / SLICE6_TEST_REL, "TIER2_MANIFEST")
    removed = {
        "--deselect="
        + SLICE1_TEST_REL
        + "::test_static_audit_shape_allowlist_and_heading_matching_are_locked",
        "--deselect="
        + SLICE5_TEST_REL
        + "::test_package_version_tags_gate2_dirty_state_and_allowlist_are_exact",
    }
    assert removed <= set(prior)
    manifest = tuple(sorted(set(prior) - removed))
    assert len(manifest) == len(set(manifest)) == 140
    payload = "".join(line + "\n" for line in manifest).encode("utf-8")
    files = {
        line.removeprefix("--deselect=").split("::", maxsplit=1)[0] for line in manifest
    }
    assert (len(files), len(payload), hashlib.sha256(payload).hexdigest()) == (
        106,
        TIER2_MANIFEST_BYTES,
        TIER2_MANIFEST_SHA256,
    )
    retained_phase52 = tuple(
        line for line in manifest if line.startswith("--deselect=tests/test_phase52_")
    )
    assert retained_phase52 == (
        "--deselect=tests/test_phase52_fail_closed_capability_lookup.py::test_gate2_dirty_untracked_and_index_states_are_exact",
        "--deselect=tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py::test_gate2_dirty_untracked_and_index_states_are_exact",
        "--deselect=tests/test_phase52_private_capability_fact_foundation.py::test_gate2_dirty_untracked_and_index_states_are_exact",
    )
    classification = {line: "CLEAN_ONLY_DESELECT" for line in manifest}
    assert set(classification.values()) == {"CLEAN_ONLY_DESELECT"}
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
    assert 6167 - len(manifest) == 6027


def test_slice8_gate2_gate3_lifecycle_release_and_next_gate_are_exact() -> None:
    spec = _read(REPO_ROOT / SPEC_REL)
    for required in (
        "Gate 3 requires separate authorization",
        "Add Phase 52 parity privacy and drift closure",
        "6,156 passed tests",
        "generated count 8",
        "golden count 37",
        "package\nsmoke PASS",
        "Ruff `0.15.22`",
        "Phase 52 Slice 9 Gate 0 and Gate 1",
        "Phase 52 remains\nactive and incomplete",
    ):
        assert required in spec
    assert _git_output(["diff", "--cached", "--name-status"]) == ""
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
    assert "No pull request, tag, release, publication, signing, or attestation" in spec


_SLICE10_READER_MIGRATION_PATHS = (
    "docs/spec/phase53-partition-binding-multi-key-visibility-diagnostics-contract-v1.md",
    "src/pietto/semantic/window_partition_analysis.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
)
# Phase 53 Slice 13 reader migration.
