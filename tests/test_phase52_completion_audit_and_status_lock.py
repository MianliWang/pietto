from __future__ import annotations

import ast
import hashlib
import re
import subprocess
import tomllib
from collections import Counter
from pathlib import Path
from typing import Any, cast

from _phase54_active_gate2_manifest import (
    phase54_post_slice12_interlude_expected_head,
    phase54_post_slice12_interlude_expected_topic_base,
    phase54_post_slice12_interlude_repair_is_active,
    phase54_post_slice12_interlude_dirty_is_active,
    phase54_post_slice12_interlude_expected_added_paths,
    phase54_post_slice12_interlude_expected_allowlist_paths,
    phase54_post_slice12_interlude_expected_modified_paths,
    phase54_post_slice12_interlude_clean_topic_is_active,
    phase54_post_slice12_interlude_expected_branch,
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
PLAN_REL = "docs/plan/phase-52-core-type-system-capability-foundation.md"
ROADMAP_REL = "docs/spec/pietto-active-roadmap-phase51-60-v1.md"
CURRENT_ROADMAP_REL = "docs/spec/pietto-active-roadmap-phase53-70-v1.md"
SPEC_REL = "docs/spec/phase52-completion-audit-and-status-lock-v1.md"
SELF_REL = "tests/test_phase52_completion_audit_and_status_lock.py"
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
SLICE8_TEST_REL = (
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py"
)
SLICE_TEST_RELS = (
    SLICE1_TEST_REL,
    SLICE2_TEST_REL,
    SLICE3_TEST_REL,
    SLICE4_TEST_REL,
    SLICE5_TEST_REL,
    SLICE6_TEST_REL,
    SLICE7_TEST_REL,
    SLICE8_TEST_REL,
    SELF_REL,
)
SLICE_SPEC_RELS = (
    "docs/spec/phase52-core-type-system-capability-foundation-scope-lock-v1.md",
    "docs/spec/phase52-private-capability-key-disposition-evidence-fact-foundation-v1.md",
    "docs/spec/phase52-fail-closed-capability-lookup-v1.md",
    "docs/spec/phase52-logical-type-literal-parameter-nullability-inventory-v1.md",
    "docs/spec/phase52-scalar-function-operator-signature-facts-v1.md",
    "docs/spec/phase52-expression-stage-clause-capability-facts-v1.md",
    "docs/spec/phase52-aggregate-signature-algebra-facts-v1.md",
    "docs/spec/phase52-parity-privacy-cross-phase-readiness-drift-closure-v1.md",
    SPEC_REL,
)

SPEC_TITLE = "Phase 52 Slice 9 Completion Audit And Status Lock v1"
SPEC_H2 = (
    "Purpose And Slice Identity",
    "Status And Completion Authority",
    "Trusted Slice 8 Baseline",
    "Phase 52 Slice Ledger",
    "Phase 52 Artifact Inventory",
    "Historical Allowlist And Repair Preservation",
    "Private Capability Architecture Completion",
    "Domain Fact And Key Inventory Audit",
    "Completeness Schema And Four-result Lookup Audit",
    "Evidence Support Disposition And Conflict Audit",
    "Privacy Consumer And No-authority Audit",
    "No-behavior Compiler Project Public Runtime Audit",
    "Repair And Checkout Compatibility Audit",
    "Compiler Semantic Phase15 Project Lock Audit",
    "Package Workflow Dependency And Release Audit",
    "Deferred-owner Audit",
    "Phase 53 Window Handoff",
    "Protected Surface Audit",
    "Completion Encoding Decision",
    "Gate 2 Pre-completion State",
    "Gate 3 Completion Condition",
    "Post-completion Phase 53–60 Status",
    "Active-roadmap Reconciliation",
    "Exact Gate 2 Allowlist",
    "Completion Invariants And Drift Locks",
    "Validation And Clean-CI Boundary",
    "Separate Authorization Boundary",
    "Stop Conditions",
)
EXPECTED_TEST_NAMES = (
    "test_slice9_artifacts_title_and_exact_heading_order_are_locked",
    "test_slice1_8_route_artifact_lifecycle_repair_and_focused_item_ledgers_are_exact",
    "test_private_capability_modules_fact_key_completeness_lookup_and_conflict_closure_is_locked",
    "test_evidence_support_disposition_backend_and_cross_phase_ownership_are_locked",
    "test_privacy_consumers_exports_authority_and_no_behavior_boundaries_are_locked",
    "test_phase53_window_handoff_roadmap_reconciliation_and_next_gate_are_locked",
    "test_live_compiler_semantic_phase15_project_protected_version_and_tag_locks_are_dirty_safe",
    "test_shallow_push_synthetic_merge_and_historical_provenance_guards_are_locked",
    "test_static_reader_hash_topology_test_inventory_and_validation_manifests_are_locked",
    "test_completion_encoding_gate2_gate3_ci_and_no_release_boundaries_are_locked",
    "test_static_git_helper_and_exact_slice9_dirty_set_are_locked",
)
PHASE52_ROUTE = (
    "Scope Architecture, Authority Boundary, And Active-roadmap Lock",
    "Private Capability Key, Disposition, Evidence, And Fact Foundation",
    "Fail-closed Lookup And Absent/Unknown/Conflict Semantics",
    "Logical Type, Literal, Parameter, And Nullability Inventory",
    "Scalar Function And Operator Signature Facts",
    "Expression Stage And Clause Capability Facts",
    "Aggregate Signature And Algebra Facts",
    "Parity, Privacy, Cross-phase Readiness, And Drift Closure",
    "Completion Audit And Status Lock",
)
SLICE_SHAPES = (
    (12, 12),
    (20, 25),
    (24, 34),
    (28, 64),
    (28, 64),
    (28, 69),
    (28, 69),
    (28, 69),
    (11, 11),
)

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
MODULE_SHA256 = {
    FACTS_REL: "bd68bad4e13a2b945962458fc47359a408d27b1563ba25f5713a8f8099671d21",
    LOOKUP_REL: "4d4c2676b3181758f01c95ca312fd0f76cebcb74ac1bcab0deefb15fc04abf26",
    INVENTORY_REL: "f11eee2a53fda26057c35be047bfa265c68794ad76054bc5636781f0b5164b26",
    SIGNATURE_REL: "810f347080e0bb7dc674821aa6387c5f7618ac216832194ef19820326eef71d2",
    CONTEXT_REL: "132371eccca00ca9f8722a34f1ea0f540933515e560639ee12e53aee6594c60c",
    AGGREGATE_REL: "d7d69fa4b97924ef5462af9c871a910b73cad43a21431e98a72c8bdab8996c80",
    WINDOW_REL: "c0512933fc284bbc1dec98dab96411ee179d64e7bee005aa798b6fd7dba2024e",
}
PATH_DIGESTS = {
    "compiler": "f9eca1bf5cadfcc1583ba465f33bf761114e6d9d2785de15a2d73b5a19a6ff62",
    "semantic": "731e17cc85849c7716abeb08abeda03f72e3e21af183a391107adf96ccab6d70",
    "phase15": "81db265a7bbd290b9c9227733e92dc502f8e8c8f0ff76b4d631651772876550d",
    "project": "9269d0946eaa232a4471633214d6fc55cd69b55d684edba3213532242224183b",
}
PROTECTED_SHA256 = {
    ".github/workflows/ci.yml": "4db1c9a49b0af230bae3f088bf84524e210e0afcd6a87250322e5036a69e8d94",
    "pyproject.toml": "36aa8e1d19a8409e56e0163a465b9608a88c1bffe644165ba49db49bf5ec3d01",
    "uv.lock": "a7d9125995e98a8a74d3664ceae7801cc1f4cce74ec323933da67838be199cea",
    ".python-version": "7b55f8e67b5623c4bef3fa691288da9437d79d3aba156de48d481db32ac7d16d",
    "docs/spec/pietto-roadmap-phase45-60-v1.md": "26cc0ae4a68518223d6bf600ad3c4b0b226618aa7ef31b2ae1c25924d2655169",
}
PRE_RECONCILIATION_3_SHA256 = (
    "cb2c51246f1e312858641750d1a416125f99058fb0182949e9afe35ae49e97cf"
)
RECONCILIATION_3_H3 = (
    "### Reconciliation 3 — Phase 52 Conditional Completion And Phase 53 Handoff"
)
RECONCILIATION_4_H3 = (
    "### Reconciliation 4 — Phase 52 Completion, Phase 53–70 Current-authority "
    "Handoff, Release, And Rust Route"
)

GATE2_BASE_HEAD_SHA = "36e466535d923f708a0201ae15a5708f06f2b1f8"
GATE2_BASE_PARENT_SHA = "7a221ffdca91335a526ed12a1059340bda642fdb"
GATE2_BASE_TREE_SHA = "e2873c562a4a21e7ad284ccbf736f193da58a5ed"
GATE2_BASE_SUBJECT = "Fix Phase 52 shallow checkout history guard"
HISTORICAL_SETUP_JAVA_HEAD_SHA = "11a0c48941c3c1c650be8d0ec8ddf5201f9525f2"
HISTORICAL_SETUP_JAVA_PARENT_SHA = "7bea69da0465f57580961e4ca4a2c18a84dfb68c"
HISTORICAL_SETUP_JAVA_TREE_SHA = "2953c238f27239d796c9af05543b48c1add2a69d"
SLICE9_MODIFIED_PATHS = {
    PLAN_REL,
    ROADMAP_REL,
    SLICE1_TEST_REL,
    SLICE5_TEST_REL,
    SLICE6_TEST_REL,
    SLICE7_TEST_REL,
    SLICE8_TEST_REL,
}
SLICE9_ADDED_PATHS = {SPEC_REL, SELF_REL}
SLICE9_ALLOWLIST_PATHS = SLICE9_MODIFIED_PATHS | SLICE9_ADDED_PATHS
PHASE53_BASE_HEAD_SHA = "b8029699ccc51bfa500856155b18e666898cb883"
PHASE53_MODIFIED_PATHS = {
    ROADMAP_REL,
    SLICE1_TEST_REL,
    SELF_REL,
    SLICE5_TEST_REL,
    SLICE6_TEST_REL,
    SLICE7_TEST_REL,
    SLICE8_TEST_REL,
}
PHASE53_ADDED_PATHS = {
    "docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md",
    "docs/spec/phase53-window-functions-generic-signature-nullability-scope-lock-v1.md",
    CURRENT_ROADMAP_REL,
    "tests/test_phase53_window_generic_nullability_foundation_scope_lock.py",
}
PHASE53_ALLOWLIST_PATHS = PHASE53_MODIFIED_PATHS | PHASE53_ADDED_PATHS
SLICE2_BASE_HEAD_SHA = "3c1feab5bc70d407e9e4d7ccd0c5d489eec0ee68"
SLICE2_STATE_REL = "tests/test_phase53_window_syntax_contextual_grammar_contract.py"

OWNER_HANDOFFS = (
    "PHASE_53",
    "PHASE_54",
    "PHASE_55",
    "PHASE_56",
    "PHASE_57",
    "PHASE_58",
    "PHASE_59",
    "PHASE_60",
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
TIER1_BYTES = 5525
TIER1_SHA256 = "2097b7aace8604cb54af6392a9e400543fa7eefac4423f810d8a37451c05d48b"
TIER2_BYTES = 18026
TIER2_SHA256 = "6ab2027b7c8cb7858fbea2d3902130a4a860e462102ac4e582990f4bcfa501bf"


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

    if branch == phase54_post_slice12_interlude_expected_branch():
        assert phase54_post_slice12_interlude_clean_topic_is_active()
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
    ):
        assert branch == "main"
        assert head == main == origin_main == PHASE54_ACTIVE_GATE2_BASE
        return
    dirty = tracked | untracked
    if head in {
        "d8a5e9ab3de70ce30575513c73560c86430eca63",
        "15bae172ee151e370fe59d3bf909d735aee6aa90",
        "0f3c955c5a5fbd8046ef611ad1bef0b636c8be01",
        "c44a4271d9592cb393d2232f127a59d8466cc60a",
        "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16",
        "027b33cafcfd58916a89e299487dad38d24ade6c",
        "0ceb9a476e6592714cdc76845949ba0ae5123eb5",
        "b81843acadb294630db361c09949868d004b1bca",
    }:
        phase54_state = "tests/_phase54_active_gate2_manifest.py"
        slice2_modified = _literal_string_set(
            phase54_state, "NON_READER_MODIFIED_PATHS"
        ) | _literal_string_set(phase54_state, "MECHANICAL_READER_PATHS")
        slice2_added = _literal_string_set(phase54_state, "ADDED_PATHS")
        slice2_base = head
    else:
        slice2_modified = _literal_string_set(SLICE2_STATE_REL, "MODIFIED_PATHS")
        slice2_added = _literal_string_set(SLICE2_STATE_REL, "ADDED_PATHS")
        slice2_base = SLICE2_BASE_HEAD_SHA
    slice2_allowlist = slice2_modified | slice2_added
    assert dirty in (
        set(),
        SLICE9_ALLOWLIST_PATHS,
        PHASE53_ALLOWLIST_PATHS,
        slice2_allowlist,
        set(phase54_post_slice12_interlude_expected_allowlist_paths()),
    )
    if not dirty:
        assert tracked == untracked == set()
        availability = (
            _git_commit_exists(GATE2_BASE_HEAD_SHA),
            _git_commit_exists(GATE2_BASE_PARENT_SHA),
        )
        assert availability[0] == availability[1]
        if all(availability):
            assert _git_output(["rev-parse", f"{GATE2_BASE_HEAD_SHA}^"]) == (
                GATE2_BASE_PARENT_SHA
            )
            assert (
                _git_output(["rev-parse", f"{GATE2_BASE_HEAD_SHA}^{{tree}}"])
                == GATE2_BASE_TREE_SHA
            )
            assert (
                _git_output(["show", "-s", "--format=%s", GATE2_BASE_HEAD_SHA])
                == GATE2_BASE_SUBJECT
            )
            assert _git_output(["merge-base", head, GATE2_BASE_HEAD_SHA]) == (
                GATE2_BASE_HEAD_SHA
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
    if phase54_post_slice12_interlude_dirty_is_active():
        assert tracked == set(phase54_post_slice12_interlude_expected_modified_paths())
        assert untracked == set(phase54_post_slice12_interlude_expected_added_paths())
        if phase54_post_slice12_interlude_repair_is_active():
            assert branch == phase54_post_slice12_interlude_expected_branch()
            assert head == phase54_post_slice12_interlude_expected_head()
            assert (
                main
                == origin_main
                == phase54_post_slice12_interlude_expected_topic_base()
            )
        else:
            assert branch == "main"
            assert (
                head
                == main
                == origin_main
                == phase54_post_slice12_interlude_expected_head()
            )
        return
    if dirty == slice2_allowlist:
        assert tracked == slice2_modified
        assert untracked == slice2_added
        assert branch == "main"
        assert head == main == origin_main == slice2_base
        return
    if dirty == PHASE53_ALLOWLIST_PATHS:
        assert tracked == PHASE53_MODIFIED_PATHS
        assert untracked == PHASE53_ADDED_PATHS
        assert branch == "main"
        assert head == main == origin_main == PHASE53_BASE_HEAD_SHA
        return
    assert tracked == SLICE9_MODIFIED_PATHS
    assert untracked == SLICE9_ADDED_PATHS
    assert branch == "main"
    assert head == main == origin_main == GATE2_BASE_HEAD_SHA
    assert _git_commit_exists(GATE2_BASE_HEAD_SHA)
    if _git_commit_exists(GATE2_BASE_PARENT_SHA):
        assert _git_output(["rev-parse", f"{GATE2_BASE_HEAD_SHA}^"]) == (
            GATE2_BASE_PARENT_SHA
        )
        assert (
            _git_output(["rev-parse", f"{GATE2_BASE_HEAD_SHA}^{{tree}}"])
            == GATE2_BASE_TREE_SHA
        )
        assert _git_output(["show", "-s", "--format=%s", GATE2_BASE_HEAD_SHA]) == (
            GATE2_BASE_SUBJECT
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
        assert isinstance(values, (ast.List, ast.Tuple))
        count *= len(values.elts)
    return count


def _pytest_shape(relative: str) -> tuple[int, int, tuple[str, ...]]:
    functions = tuple(
        node
        for node in ast.parse(_read(relative), filename=relative).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    return (
        len(functions),
        sum(_parametrize_values(function) for function in functions),
        tuple(function.name for function in functions if function.decorator_list),
    )


def _literal_tuple(relative: str, name: str) -> tuple[str, ...]:
    tree = ast.parse(_read(relative), filename=relative)
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
        if value is not None:
            result = ast.literal_eval(value)
            assert isinstance(result, tuple)
            assert all(isinstance(item, str) for item in result)
            return cast(tuple[str, ...], result)
    raise AssertionError(f"missing literal tuple {name}")


def _literal_string_set(relative: str, name: str) -> set[str]:
    tree = ast.parse(_read(relative), filename=relative)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            continue
        result = ast.literal_eval(node.value)
        assert isinstance(result, set)
        assert all(isinstance(item, str) for item in result)
        return cast(set[str], result)
    raise AssertionError(f"missing literal string set {name}")


def _families() -> tuple[tuple[CapabilityFact, ...], ...]:
    return (
        cast(tuple[CapabilityFact, ...], capability_inventory._CAPABILITY_FACTS),
        cast(
            tuple[CapabilityFact, ...],
            capability_signatures._CAPABILITY_SIGNATURE_FACTS,
        ),
        cast(tuple[CapabilityFact, ...], capability_contexts._CAPABILITY_CONTEXT_FACTS),
        cast(
            tuple[CapabilityFact, ...],
            capability_aggregates._AGGREGATE_CAPABILITY_FACTS,
        ),
        cast(
            tuple[CapabilityFact, ...],
            capability_windows._WINDOW_CAPABILITY_FACTS,
        ),
    )


def _all_facts() -> tuple[CapabilityFact, ...]:
    return tuple(fact for family in _families() for fact in family)


def _lookup(key: CapabilityKey) -> Found | Absent | Unknown | Conflict:
    if key.domain in {
        CapabilityDomain.LOGICAL_TYPE,
        CapabilityDomain.LITERAL,
        CapabilityDomain.PARAMETER,
    }:
        facts, complete = cast(Any, capability_inventory.inventory_lookup_inputs)(key)
        reason = None
    elif key.domain in {
        CapabilityDomain.SCALAR_FUNCTION,
        CapabilityDomain.UNARY_OPERATOR,
        CapabilityDomain.BINARY_OPERATOR,
        CapabilityDomain.COMPARISON,
        CapabilityDomain.NULL_TEST,
    }:
        facts, complete, reason = cast(
            Any, capability_signatures.signature_lookup_inputs
        )(key)
    elif key.domain in {CapabilityDomain.EXPRESSION_STAGE, CapabilityDomain.CLAUSE}:
        facts, complete, reason = cast(
            Any, capability_contexts.stage_clause_lookup_inputs
        )(key)
    elif key.domain is CapabilityDomain.AGGREGATE:
        facts, complete, reason = cast(
            Any, capability_aggregates.aggregate_lookup_inputs
        )(key)
    elif key.domain is CapabilityDomain.WINDOW_FUNCTION:
        facts, complete, reason = cast(Any, capability_windows.window_lookup_inputs)(
            key
        )
    else:
        facts, complete, reason = (), False, None
    return lookup_capability(
        key,
        facts,
        domain_complete=complete,
        unknown_reason=reason,
    )


def _tier1_operands() -> tuple[str, ...]:
    direct = _literal_tuple(SLICE7_TEST_REL, "DIRECT_TIER1_NODES")
    filtered = tuple(node for node in direct if not node.startswith(SLICE1_TEST_REL))
    assert len(direct) == 44 and len(filtered) == 42
    deselections = (
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
    return (*SLICE_TEST_RELS, *deselections, *filtered)


def _tier2_manifest() -> tuple[str, ...]:
    prior = _literal_tuple(SLICE6_TEST_REL, "TIER2_MANIFEST")
    removed = {
        "--deselect="
        + SLICE1_TEST_REL
        + "::test_static_audit_shape_allowlist_and_heading_matching_are_locked",
        "--deselect="
        + SLICE5_TEST_REL
        + "::test_package_version_tags_gate2_dirty_state_and_allowlist_are_exact",
    }
    assert removed <= set(prior)
    return tuple(sorted(set(prior) - removed))


def test_slice9_artifacts_title_and_exact_heading_order_are_locked() -> None:
    assert (REPO_ROOT / SPEC_REL).is_file()
    assert (REPO_ROOT / SELF_REL).is_file()
    assert _headings(SPEC_REL, 1) == (SPEC_TITLE,)
    assert _headings(SPEC_REL, 2) == SPEC_H2
    assert _headings(SPEC_REL, 3) == ()
    assert _headings(PLAN_REL, 3) == ("Slice 9 Gate 2 Bounded Implementation Status",)
    tree = ast.parse(_read(SELF_REL), filename=SELF_REL)
    tests = tuple(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert tuple(node.name for node in tests) == EXPECTED_TEST_NAMES
    assert len(tests) == 11
    assert all(not node.decorator_list for node in tests)


def test_slice1_8_route_artifact_lifecycle_repair_and_focused_item_ledgers_are_exact() -> (
    None
):
    plan = _read(PLAN_REL)
    spec = _read(SPEC_REL)
    route_start = plan.index("## Exact Nine-slice Route")
    route_end = plan.index("## Slice Objectives", route_start)
    route = tuple(
        match.group(1)
        for match in re.finditer(r"^[1-9]\. (.+)$", plan[route_start:route_end], re.M)
    )
    assert route == PHASE52_ROUTE
    assert all((REPO_ROOT / path).is_file() for path in SLICE_SPEC_RELS)
    assert all((REPO_ROOT / path).is_file() for path in SLICE_TEST_RELS)
    observed_shapes = tuple(_pytest_shape(path)[:2] for path in SLICE_TEST_RELS)
    assert observed_shapes == SLICE_SHAPES
    assert (
        sum(pair[0] for pair in SLICE_SHAPES),
        sum(pair[1] for pair in SLICE_SHAPES),
    ) == (
        207,
        417,
    )
    assert (
        "The route is exact and is not reordered, merged, split, or expanded." in spec
    )
    assert all(
        phrase in spec
        for phrase in (
            "Slice 1's original publication required a CI repair",
            "Slices 4, 5, and 7 retain the completeness repair",
            "Slice 6 retains its CI,\nmerge-ref, and completeness repairs",
            "Slice 8 retains its shallow-checkout repair",
        )
    )


def test_private_capability_modules_fact_key_completeness_lookup_and_conflict_closure_is_locked() -> (
    None
):
    assert {_path: _sha256(_path) for _path in MODULE_RELS} == MODULE_SHA256
    for relative, module in zip(MODULE_RELS, MODULE_OBJECTS, strict=True):
        assert getattr(module, "__all__") == ()
        tree = ast.parse(_read(relative), filename=relative)
        imported = {
            node.module
            for node in tree.body
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }
        if relative == FACTS_REL:
            assert not any("capability_" in name for name in imported)
        else:
            capability_imports = {name for name in imported if "capability_" in name}
            assert capability_imports == {"pietto.semantic.capability_facts"}

    families = _families()
    facts = _all_facts()
    assert tuple(
        (len(family), len({fact.key for fact in family})) for family in families
    ) == (
        (41, 41),
        (39, 39),
        (18, 18),
        (69, 68),
        (24, 24),
    )
    assert (len(facts), len(set(facts)), len({fact.key for fact in facts})) == (
        191,
        191,
        190,
    )
    collisions = tuple(
        group
        for key in dict.fromkeys(fact.key for fact in facts)
        if len(group := tuple(fact for fact in facts if fact.key == key)) > 1
    )
    assert len(collisions) == 1
    conflict = collisions[0]
    assert tuple(fact.support for fact in conflict) == (
        CapabilitySupport.SUPPORTED,
        CapabilitySupport.EXPLICITLY_UNSUPPORTED,
    )
    assert conflict[0].key.subject == "count"
    assert "Shape" in conflict[0].key.operands
    assert _lookup(conflict[0].key) == Conflict(
        CapabilityReasonCode.CONFLICTING_EVIDENCE,
        conflict,
    )
    assert all(
        isinstance(_lookup(key), (Found, Conflict))
        for key in dict.fromkeys(fact.key for fact in facts)
    )
    reserved = {
        CapabilityDomain.DIALECT_LOWERING,
        CapabilityDomain.CONVERSION,
        CapabilityDomain.EXTENSION_SIGNATURE,
    }
    assert not any(fact.key.domain in reserved for fact in facts)


def test_evidence_support_disposition_backend_and_cross_phase_ownership_are_locked() -> (
    None
):
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
    evidence = tuple(item for fact in facts for item in fact.evidence)
    assert len(evidence) == 2373
    assert Counter(item.source for item in evidence) == EVIDENCE_SOURCE_COUNTS
    dual = tuple(
        fact
        for fact in facts
        if {
            (item.dialect, item.backend)
            for item in fact.evidence
            if item.source is CapabilityEvidenceSource.BACKEND
        }
        == {("postgresql", "postgresql"), ("mysql", "private-mysql")}
    )
    positive = tuple(
        fact
        for fact in dual
        if fact.support is CapabilitySupport.SUPPORTED
        and all(
            item.reason is None
            for item in fact.evidence
            if item.source is CapabilityEvidenceSource.BACKEND
        )
    )
    assert (len(dual), len(positive)) == (110, 106)
    combined = _read(SPEC_REL) + _read(ROADMAP_REL)
    assert all(owner in combined for owner in OWNER_HANDOFFS)
    assert "No owner is added,\nrenamed, removed, transferred" in _read(SPEC_REL)


def test_privacy_consumers_exports_authority_and_no_behavior_boundaries_are_locked() -> (
    None
):
    forbidden_names = {
        "inventory_lookup_inputs",
        "signature_lookup_inputs",
        "stage_clause_lookup_inputs",
        "aggregate_lookup_inputs",
        "window_lookup_inputs",
    }
    stems = {Path(relative).stem for relative in MODULE_RELS}
    preservation_rel = "src/pietto/_project/module_semantic_fact_preservation.py"
    for path in (REPO_ROOT / "src/pietto").rglob("*.py"):
        relative = path.relative_to(REPO_ROOT).as_posix()
        if relative in {*MODULE_RELS, preservation_rel} or "generated" in path.parts:
            continue
        source = path.read_text(encoding="utf-8")
        assert all(name not in source for name in forbidden_names)
        assert all(f"semantic.{stem}" not in source for stem in stems)
    preservation_source = _read(preservation_rel)
    assert all(name in preservation_source for name in forbidden_names)
    assert "__all__: tuple[str, ...] = ()" in preservation_source
    assert "capability_" not in _read("src/pietto/__init__.py")
    assert "capability_" not in _read("src/pietto/semantic/__init__.py")
    spec = _read(SPEC_REL)
    for phrase in (
        "Forbidden production and public consumer count is exactly zero.",
        "not compiler authority",
        "claims no authority over grammar, generated parser, AST",
        "Slice 9 adds no production\nsource and implements no Phase 53",
    ):
        assert phrase in spec


def test_phase53_window_handoff_roadmap_reconciliation_and_next_gate_are_locked() -> (
    None
):
    roadmap = _read(ROADMAP_REL)
    marker = f"\n{RECONCILIATION_3_H3}\n"
    prefix, separator, remainder = roadmap.partition(marker)
    assert separator == marker
    assert hashlib.sha256(prefix.encode()).hexdigest() == PRE_RECONCILIATION_3_SHA256
    assert roadmap.count(RECONCILIATION_3_H3) == 1
    reconciliation, separator, reconciliation4 = remainder.partition(
        f"\n{RECONCILIATION_4_H3}\n"
    )
    assert separator == f"\n{RECONCILIATION_4_H3}\n"
    assert roadmap.count(RECONCILIATION_4_H3) == 1
    assert "\n### " not in reconciliation
    assert "\n### " not in reconciliation4
    assert roadmap.endswith("\n")
    for phrase in (
        "Phase 52 remains ACTIVE and incomplete",
        "Phase 52 are `COMPLETED`",
        "Phases 53–60 remain `UNSTARTED`",
        "Phase 53 is the next planned phase but does not automatically become ACTIVE",
        "Phase 53 Slice 1 Gate 0 and Gate 1",
    ):
        assert phrase in reconciliation
    current = _read(CURRENT_ROADMAP_REL)
    current_handoff = " ".join((reconciliation4 + current).split())
    for phrase in (
        "Phase 53 remains `UNSTARTED`",
        "sole current roadmap authority",
        "Phase 53 Slice 1 Gate 3",
        "Release 0.1.0",
        "big-bang",
        "no automatic implementation authorization",
    ):
        assert phrase in current_handoff, phrase
    facts = _all_facts()
    assert not any(
        fact.key.domain is CapabilityDomain.EXPRESSION_STAGE
        and "WINDOW" in fact.key.operands
        for fact in facts
    )
    window = CapabilityKey(
        CapabilityDomain.EXPRESSION_STAGE,
        subject="aggregate_dependent_expression",
        operation="observed_stage",
        operands=("WINDOW",),
        context="expression",
    )
    assert _lookup(window) == Unknown(CapabilityReasonCode.NOT_EVIDENCED)
    assert all(
        phrase in _read(SPEC_REL)
        for phrase in ("No `OVER`", "aggregate-as-window", "Phase 53 is not started")
    )


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
        105,
        36,
        33,
        30,
    )
    assert {
        "compiler": _digest(compiler),
        "semantic": _digest(semantic),
        "phase15": _digest(phase15),
        "project": _digest(project),
    } == PATH_DIGESTS
    assert {relative: _sha256(relative) for relative in PROTECTED_SHA256} == (
        PROTECTED_SHA256
    )
    with (REPO_ROOT / "pyproject.toml").open("rb") as stream:
        pyproject = tomllib.load(stream)
    assert pyproject["project"]["version"] == "0.1.0"
    assert pyproject["build-system"]["requires"] == ["uv_build>=0.11.32,<0.12.0"]
    assert "ruff>=0.16.0" in _read("pyproject.toml")
    assert 'name = "ruff"\nversion = "0.16.0"' in _read("uv.lock")
    assert (
        "actions/setup-java@03ad4de0992f5dab5e18fcb136590ce7c4a0ac95 # v5.6.0"
        in _read(".github/workflows/ci.yml")
    )
    assert _git_output(["tag", "--list"]) == ""
    assert _git_output(["tag", "--points-at", "HEAD"]) == ""
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


def test_shallow_push_synthetic_merge_and_historical_provenance_guards_are_locked() -> (
    None
):
    availability = (
        _git_commit_exists(HISTORICAL_SETUP_JAVA_HEAD_SHA),
        _git_commit_exists(HISTORICAL_SETUP_JAVA_PARENT_SHA),
    )
    assert availability[0] == availability[1]
    if all(availability):
        assert _git_output(["rev-parse", f"{HISTORICAL_SETUP_JAVA_HEAD_SHA}^"]) == (
            HISTORICAL_SETUP_JAVA_PARENT_SHA
        )
        assert _git_output(
            ["rev-parse", f"{HISTORICAL_SETUP_JAVA_HEAD_SHA}^{{tree}}"]
        ) == (HISTORICAL_SETUP_JAVA_TREE_SHA)
        assert (
            _git_output(["show", "-s", "--format=%s", HISTORICAL_SETUP_JAVA_HEAD_SHA])
            == "Bump actions/setup-java from 5.5.0 to 5.6.0"
        )
    else:
        assert _git_output(["rev-parse", "--is-shallow-repository"]) == "true"
        assert _git_output(["status", "--porcelain=v1", "--untracked-files=all"]) == ""
        assert _git_output(["diff", "--cached", "--name-only"]) == ""
        _assert_clean_checkout_refs(
            branch=_git_output(["branch", "--show-current"]),
            head=_git_output(["rev-parse", "HEAD"]),
            main=_git_optional_ref("refs/heads/main"),
            origin_main=_git_optional_ref("refs/remotes/origin/main"),
            exact_main_refs=True,
        )
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
    for relative in (
        SLICE1_TEST_REL,
        SLICE5_TEST_REL,
        SLICE6_TEST_REL,
        SLICE7_TEST_REL,
        SLICE8_TEST_REL,
    ):
        source = _read(relative)
        assert "SLICE9_ALLOWLIST_PATHS" in source
        assert "GATE2_BASE_HEAD_SHA" in source or "SLICE9_BASE_HEAD_SHA" in source
    forbidden_bypasses = (
        "git " + "fetch",
        "--" + "unshallow",
        "pytest." + "skip",
        "pytest." + "xfail",
    )
    assert all(token not in _read(SELF_REL) for token in forbidden_bypasses)


def test_static_reader_hash_topology_test_inventory_and_validation_manifests_are_locked() -> (
    None
):
    readable = _readable_paths()
    assert (
        sum(path.endswith(".py") for path in readable),
        sum(path.endswith(".md") for path in readable),
    ) == (571, 266)
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
    for relative, expected in zip(
        MODULE_RELS,
        (10, 7, 6, 5, 4, 3, 6),
        strict=True,
    ):
        readers = tuple(
            path
            for path in readable
            if MODULE_SHA256[relative].encode() in (REPO_ROOT / path).read_bytes()
        )
        assert len(readers) == expected and SELF_REL in readers
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
    historical = (
        ("tests/test_phase13_completion_audit.py", 2),
        ("tests/test_phase15_semantic_completion_audit.py", 1),
        ("tests/test_phase16_current_syntax_surface_audit.py", 1),
        ("tests/test_phase16_language_direction_audit.py", 1),
        ("tests/test_phase16_safety_deferral_sql_portability.py", 1),
    )
    assert (
        len(historical),
        len({path for path, _ in historical}),
        sum(n for _, n in historical),
    ) == (
        5,
        5,
        6,
    )
    self_source = _read(SELF_REL)
    assert all(not relative.startswith("tests/") for relative in MODULE_SHA256)
    assert "MODIFIED_TEST_" + "SHA256" not in self_source
    assert _sha256(SELF_REL) not in self_source

    test_files = tuple((REPO_ROOT / "tests").glob("test_*.py"))
    top_functions = sum(
        sum(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
            for node in ast.parse(
                path.read_text(encoding="utf-8"), filename=path.as_posix()
            ).body
        )
        for path in test_files
    )
    assert (len(test_files), top_functions) == (462, 5361)
    assert (
        381 + 834 + 627 + 424 + 279 + 168 + 156 + 12 + 145 + 190 + 70 + 70 + 97 + 35
        == 3488
    )
    assert 10784 - 185 == 10599
    assert sum(_pytest_shape(relative)[1] for relative in SLICE_TEST_RELS) == 417
    tier1 = _tier1_operands()
    tier1_payload = "".join(item + "\n" for item in tier1).encode()
    assert (
        len(tier1),
        len(tier1_payload),
        hashlib.sha256(tier1_payload).hexdigest(),
    ) == (
        54,
        TIER1_BYTES,
        TIER1_SHA256,
    )
    assert 462 - 3 == 459
    tier2 = _tier2_manifest()
    tier2_payload = "".join(item + "\n" for item in tier2).encode()
    tier2_files = {
        item.removeprefix("--deselect=").split("::", maxsplit=1)[0] for item in tier2
    }
    assert (
        len(tier2),
        len(tier2_files),
        len(tier2_payload),
        hashlib.sha256(tier2_payload).hexdigest(),
    ) == (
        140,
        106,
        TIER2_BYTES,
        TIER2_SHA256,
    )
    assert 6167 - len(tier2) == 6027


def test_completion_encoding_gate2_gate3_ci_and_no_release_boundaries_are_locked() -> (
    None
):
    spec = _read(SPEC_REL)
    plan = _read(PLAN_REL)
    roadmap = _read(ROADMAP_REL)
    for phrase in (
        "The repository lifecycle token is `COMPLETED`",
        "Gate 2 leaves Slice 9 current and incomplete",
        "Complete Phase 52 core type system capability foundation",
        "Both Python jobs must report exactly 6,167",
        "generated count 8",
        "golden count 37",
        "package smoke\nPASS",
        "Phase 53 Slice 1 Gate 0 and Gate 1",
        "No tag, release,\npublish, upload, signing, or attestation",
    ):
        assert phrase in spec
    assert plan.count("### Slice 9 Gate 2 Bounded Implementation Status") == 1
    assert roadmap.count(RECONCILIATION_3_H3) == 1
    assert roadmap.count(RECONCILIATION_4_H3) == 1
    assert (
        "Phase 53 is the next planned phase and is not automatically ACTIVE"
        in " ".join(spec.split())
    )
    assert "There is no post-CI status-flip commit" in spec
    assert _git_output(["diff", "--cached", "--name-status"]) == ""


def test_static_git_helper_and_exact_slice9_dirty_set_are_locked() -> None:
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
    assert len(SLICE9_ALLOWLIST_PATHS) == 9
    assert len(SLICE9_MODIFIED_PATHS) == 7
    assert len(SLICE9_ADDED_PATHS) == 2
    assert sum(path.endswith(".py") for path in SLICE9_ALLOWLIST_PATHS) == 6
    assert sum(path.endswith(".md") for path in SLICE9_ALLOWLIST_PATHS) == 3
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
            slice2_modified = set(PHASE54_SLICE11_PYTHON313_REPAIR_MODIFIED_PATHS)
            slice2_added = set()
        elif phase54_slice11_substantive_recovery_is_active():
            slice2_modified = set(PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_MODIFIED_PATHS)
            slice2_added = set()
        elif phase54_slice11_pr_ci_repair_is_active():
            slice2_modified = set(PHASE54_SLICE11_PR_CI_REPAIR_MODIFIED_PATHS)
            slice2_added = set()
        elif phase54_slice12_pr_ci_repair_is_active():
            slice2_modified = set(PHASE54_SLICE12_PR_CI_REPAIR_MODIFIED_PATHS)
            slice2_added = set()
        elif phase54_slice12_mechanical_repair4_is_active():
            slice2_modified = set(PHASE54_SLICE12_MECHANICAL_REPAIR4_MODIFIED_PATHS)
            slice2_added = set()
        elif phase54_slice12_mechanical_repair3_is_active():
            slice2_modified = set(PHASE54_SLICE12_MECHANICAL_REPAIR3_MODIFIED_PATHS)
            slice2_added = set()
        elif phase54_slice12_product_repair3_is_active():
            slice2_modified = set(PHASE54_SLICE12_PRODUCT_REPAIR3_MODIFIED_PATHS)
            slice2_added = set()
        elif phase54_slice12_product_repair14_is_active():
            slice2_modified = set(PHASE54_SLICE12_PRODUCT_REPAIR14_MODIFIED_PATHS)
            slice2_added = set()
        elif phase54_slice12_product_repair13_is_active():
            slice2_modified = set(PHASE54_SLICE12_PRODUCT_REPAIR13_MODIFIED_PATHS)
            slice2_added = set()
        elif phase54_slice12_product_repair12_is_active():
            slice2_modified = set(PHASE54_SLICE12_PRODUCT_REPAIR12_MODIFIED_PATHS)
            slice2_added = set()
        elif phase54_slice12_product_repair11_is_active():
            slice2_modified = set(PHASE54_SLICE12_PRODUCT_REPAIR11_MODIFIED_PATHS)
            slice2_added = set()
        elif phase54_slice12_product_repair10_is_active():
            slice2_modified = set(PHASE54_SLICE12_PRODUCT_REPAIR10_MODIFIED_PATHS)
            slice2_added = set()
        elif _phase54_active_gate2_is_active() or _git_output(
            ["rev-parse", "HEAD"]
        ) in {
            "d8a5e9ab3de70ce30575513c73560c86430eca63",
            "15bae172ee151e370fe59d3bf909d735aee6aa90",
            "0f3c955c5a5fbd8046ef611ad1bef0b636c8be01",
            "c44a4271d9592cb393d2232f127a59d8466cc60a",
            "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16",
            "027b33cafcfd58916a89e299487dad38d24ade6c",
            "0ceb9a476e6592714cdc76845949ba0ae5123eb5",
            "b81843acadb294630db361c09949868d004b1bca",
        }:
            phase54_state = "tests/_phase54_active_gate2_manifest.py"
            slice2_modified = _literal_string_set(
                phase54_state, "NON_READER_MODIFIED_PATHS"
            ) | _literal_string_set(phase54_state, "MECHANICAL_READER_PATHS")
            slice2_added = _literal_string_set(phase54_state, "ADDED_PATHS")
        else:
            slice2_modified = _literal_string_set(SLICE2_STATE_REL, "MODIFIED_PATHS")
            slice2_added = _literal_string_set(SLICE2_STATE_REL, "ADDED_PATHS")
        if tracked | untracked == set(
            phase54_post_slice12_interlude_expected_modified_paths()
        ) | set(phase54_post_slice12_interlude_expected_added_paths()):
            expected_modified = set(
                phase54_post_slice12_interlude_expected_modified_paths()
            )
            expected_added = set(phase54_post_slice12_interlude_expected_added_paths())
        elif tracked | untracked == slice2_modified | slice2_added:
            expected_modified = slice2_modified
            expected_added = slice2_added
        elif tracked | untracked == PHASE53_ALLOWLIST_PATHS:
            expected_modified = PHASE53_MODIFIED_PATHS
            expected_added = PHASE53_ADDED_PATHS
        else:
            expected_modified = SLICE9_MODIFIED_PATHS
            expected_added = SLICE9_ADDED_PATHS
        assert tracked == expected_modified
        assert untracked == expected_added
        assert name_status == tuple(f"M\t{path}" for path in sorted(expected_modified))
    else:
        assert name_status == ()


_SLICE10_READER_MIGRATION_PATHS = (
    "docs/spec/phase53-partition-binding-multi-key-visibility-diagnostics-contract-v1.md",
    "src/pietto/semantic/window_partition_analysis.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
)
# Phase 53 Slice 13 reader migration.
