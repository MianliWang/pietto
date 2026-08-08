from __future__ import annotations

import ast
import hashlib
import re
import subprocess
from pathlib import Path

from _phase54_active_gate2_manifest import (
    PHASE54_POST_SLICE12_INTERLUDE_BRANCH,
    phase54_post_slice12_interlude_clean_topic_is_active,
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
)

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_REL = (
    "docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md"
)
SCOPE_REL = (
    "docs/spec/phase53-window-functions-generic-signature-nullability-scope-lock-v1.md"
)
PREDECESSOR_REL = "docs/spec/pietto-active-roadmap-phase51-60-v1.md"
CURRENT_ROADMAP_REL = "docs/spec/pietto-active-roadmap-phase53-70-v1.md"
HISTORICAL_ROADMAP_REL = "docs/spec/pietto-roadmap-phase45-60-v1.md"

PLAN_TITLE = (
    "Phase 53 — Window Functions, Generic Signature Compatibility, And "
    "Nullability Foundation"
)
SCOPE_TITLE = (
    "Phase 53 Slice 1 Window Functions, Generic Signature Compatibility, And "
    "Nullability Foundation Scope Lock v1"
)
ROADMAP_TITLE = "Pietto Active Roadmap Phase 53–70 v1"
PLAN_H2 = (
    "Status And Slice 1 Lifecycle",
    "Trusted Phase 52 Baseline And Controlling Evidence",
    "Phase Identity And Product Scope",
    "Exact Sixteen-slice Route",
    "Slice Objectives Delivery Classes And Ownership",
    "Phase 54–70 Dependency And Readiness Handoff",
    "Window Syntax Identity And Global Keyword Policy",
    "Function Inventory And Behavioral Boundary",
    "Private Catalog And Compiler-authority Boundary",
    "Generic Compatibility Foundation",
    "Nullability Formula Foundation",
    "Phase 64 Exclusion Boundary",
    "Window Stage Dependency Result-role And Lineage Boundary",
    "PostgreSQL And Private-MySQL Evidence Boundary",
    "Public Privacy Compatibility And No-behavior Boundary",
    "Active-roadmap Reconciliation 4 Contract",
    "Phase 53–70 Current-authority Roadmap Contract",
    "Release Train",
    "Rust Migration Track",
    "Slice 1 Exact Gate 2 Scope And Allowlist",
    "Gate Workflow Lifecycle And Activation Conditions",
    "Validation Evidence And Depth-one CI Workflow",
    "Package Version Release And Publication Boundary",
    "Stop Conditions",
    "Slice 2 Pietto-native Window Syntax And Contextual Grammar Contract",
    "Slice 3 WindowSpec, Extension-compatible WindowFunctionIdentity, And AST Contract",
    "Slice 4 Generic Type-variable, Constraint, And Exact Compatibility Foundation",
    "Slice 5 Nullability Algebra And Signature Result-formula Foundation",
    "Slice 6 Private Window Semantic Carrier, WINDOW Stage, Dependency, And Result Roles",
    "Slice 7 row_number Direct-field MVP",
    "Slice 8 rank / dense_rank And Peer Semantics",
    "Slice 9 percent_rank / cume_dist / ntile",
    "Slice 10 Partition Binding, Multi-key Visibility, And Diagnostics",
    "Slice 11 Window-local Ordering, Direction, Mandatory-order Policy, And Determinism",
    "Slice 12 lag / lead Navigation, Offset, Default, And Nullability",
    "Slice 13 — Grouped-result Ranking, Aggregate-result Inputs, And Bounded Let Visibility",
    "Slice 14 — Multiple Window Outputs, Final-order Alias, Downstream Schema, And Lineage",
    "Slice 15 — Window IR, Dual-backend Lowering, And Window-function Facts",
    "Slice 16 — Completion Audit, Status Lock, Dialect, Privacy, And "
    "No-authority Closure",
)
SCOPE_H2 = (
    "Purpose And Slice Identity",
    "Trusted Phase 52 Baseline",
    "Lifecycle And Conditional Activation",
    "Static-only Slice 1 Boundary",
    "Exact Sixteen-slice Route",
    "Phase 54–70 Unique Ownership",
    "Global Window Keyword Policy",
    "Contextual Grammar Boundary",
    "Private Window Function Identity And Catalog Boundary",
    "Exact Eight-function Inventory",
    "Bounded Window Behavior Ownership",
    "Generic Type-variable And Constraint Inventory",
    "Exact Compatibility Overload And Ambiguity Contract",
    "Nullability Formula Inventory",
    "Phase 64 Advanced Type Exclusions",
    "Compiler Authority Capability Facts And Public Privacy Boundary",
    "Window Stage Dependency Result-role And Lineage Readiness",
    "PostgreSQL And Private-MySQL Evidence Separation",
    "Historical Roadmap Preservation",
    "Reconciliation 4 Append-only Contract",
    "Phase 53–70 Current Roadmap Authority",
    "Release Train Boundary",
    "Rust Migration Track",
    "Exact Gate 2 Allowlist And Dirty-state Contract",
    "Validation Depth-one CI And Gate 3 Publication Contract",
    "No Grammar Source Runtime Public Schema Version Or Release Change",
    "Stop Conditions",
)
ROADMAP_H2 = (
    "Status And Current Authority",
    "Predecessor And Append-only Lineage",
    "Lifecycle And Authorization",
    "Phase 53 Scope And Sixteen-slice Route",
    "Phase 54–60 Ownership Route",
    "Phase 61–70 Ownership Route",
    "POST60 Owner-slot Reconciliation",
    "Release Train",
    "Rust Migration Track",
    "Global Window Keyword Policy",
    "Public Compatibility And Non-goals",
    "Validation Publication And Stop Conditions",
)
RECONCILIATION_4_H3 = (
    "### Reconciliation 4 — Phase 52 Completion, Phase 53–70 Current-authority "
    "Handoff, Release, And Rust Route"
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
PHASE_OWNER_ROUTE = (
    (54, "Local Import / Module / Export Foundation"),
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
POST60_OWNERS = (
    ("POST60_ADVANCED_AGGREGATION_GROUPING", ("Phase 65",)),
    ("POST60_ADVANCED_TYPE_NATIVE_MAPPING", ("Phase 64",)),
    ("POST60_ADVANCED_WINDOWS", ("Phase 53", "Phase 60", "Phase 63")),
    ("POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT", ("Phase 62",)),
    ("POST60_PROJECT_IR", ("Phase 61",)),
    ("POST60_MULTI_RELATION_SQL", ("Phase 63",)),
    ("POST60_PUBLIC_PROJECT_SCHEMA_LINEAGE_EXPANSION", ("Phase 70",)),
    ("POST60_ADVANCED_MODULE_PACKAGE_ASSETS", ("Phase 66",)),
    ("POST60_REMOTE_PACKAGE_MANAGER", ("Phase 67",)),
    ("POST60_DEPENDENCY_SOLVER_LOCKFILE", ("Phase 68",)),
    ("POST60_ADDITIONAL_DIALECT_BACKENDS", ("Phase 69",)),
    ("POST60_EXTENSION_LOWERING", ("Phase 69",)),
)
WINDOW_FUNCTION_IDENTITIES = (
    "row_number",
    "rank",
    "dense_rank",
    "percent_rank",
    "cume_dist",
    "ntile",
    "lag",
    "lead",
)
NULLABILITY_FORMS = (
    "NON_NULL",
    "NULLABLE",
    "SAME_AS_ARG(i)",
    "ANY_NULLABLE(args)",
    "ALWAYS_NULLABLE",
    "NULLABLE_IF_DEFAULT_OMITTED",
    "bounded deterministic Boolean composition",
)

PHASE53_BASE_HEAD_SHA = "b8029699ccc51bfa500856155b18e666898cb883"
PHASE53_MODIFIED_PATHS = {
    PREDECESSOR_REL,
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py",
    "tests/test_phase52_completion_audit_and_status_lock.py",
    "tests/test_phase52_aggregate_signature_algebra_facts.py",
    "tests/test_phase52_expression_stage_clause_capability_facts.py",
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
    "tests/test_phase52_scalar_function_operator_signature_facts.py",
}
PHASE53_ADDED_PATHS = {
    PLAN_REL,
    SCOPE_REL,
    CURRENT_ROADMAP_REL,
    "tests/test_phase53_window_generic_nullability_foundation_scope_lock.py",
}
PHASE53_ALLOWLIST_PATHS = PHASE53_MODIFIED_PATHS | PHASE53_ADDED_PATHS
CI_REPAIR_BASE_HEAD_SHA = "c309323216fb7e6c52afba060cb188b3bb618d34"
CI_REPAIR_MODIFIED_PATHS = {
    "tests/test_phase53_window_generic_nullability_foundation_scope_lock.py",
}
SLICE2_BASE_HEAD_SHA = "3c1feab5bc70d407e9e4d7ccd0c5d489eec0ee68"
SLICE2_STATE_REL = "tests/test_phase53_window_syntax_contextual_grammar_contract.py"
PHASE54_SLICE2_BASE_HEAD_SHA = "d8a5e9ab3de70ce30575513c73560c86430eca63"
PHASE54_SLICE4_BASE_HEAD_SHA = "15bae172ee151e370fe59d3bf909d735aee6aa90"
PHASE54_SLICE5_BASE_HEAD_SHA = "0f3c955c5a5fbd8046ef611ad1bef0b636c8be01"
PHASE54_SLICE6_BASE_HEAD_SHA = "c44a4271d9592cb393d2232f127a59d8466cc60a"
PHASE54_SLICE7_BASE_HEAD_SHA = "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16"
PHASE54_SLICE8_BASE_HEAD_SHA = "027b33cafcfd58916a89e299487dad38d24ade6c"
PHASE54_SLICE9_BASE_HEAD_SHA = "0ceb9a476e6592714cdc76845949ba0ae5123eb5"
PHASE54_SLICE2_STATE_REL = "tests/_phase54_active_gate2_manifest.py"

TIER1_EXISTING_NODES = (
    "tests/test_phase51_aggregate_grouped_output_schema_foundation_scope_lock.py::test_artifacts_titles_heading_orders_and_no_behavior_sentence_are_locked",
    "tests/test_phase51_aggregate_grouped_output_schema_foundation_scope_lock.py::test_roadmap_governance_status_axes_and_conditional_authority_are_locked",
    "tests/test_phase51_aggregate_grouped_output_schema_foundation_scope_lock.py::test_phase51_60_normative_route_and_delivery_classes_are_locked",
    "tests/test_phase51_aggregate_grouped_output_schema_foundation_scope_lock.py::test_complete_deferred_owner_matrix_and_post60_register_are_locked",
    "tests/test_phase51_aggregate_grouped_output_schema_foundation_scope_lock.py::test_privacy_readiness_release_and_non_goal_boundaries_are_locked",
    "tests/test_phase51_completion_audit_and_status_lock.py::test_slice12_artifacts_title_and_exact_heading_order_are_locked",
    "tests/test_phase51_completion_audit_and_status_lock.py::test_deferred_owner_phase52_handoff_and_active_roadmap_reconciliation_are_locked",
    "tests/test_phase51_completion_audit_and_status_lock.py::test_completion_encoding_gate2_gate3_and_no_release_boundaries_are_locked",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py::test_phase52_and_deferred_owner_boundaries_are_locked",
    "tests/test_phase52_completion_audit_and_status_lock.py::test_evidence_support_disposition_backend_and_cross_phase_ownership_are_locked",
    "tests/test_phase52_completion_audit_and_status_lock.py::test_phase53_window_handoff_roadmap_reconciliation_and_next_gate_are_locked",
    "tests/test_phase52_completion_audit_and_status_lock.py::test_completion_encoding_gate2_gate3_ci_and_no_release_boundaries_are_locked",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py::test_read_model_first_authority_dimensions_and_non_authority_are_locked",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py::test_lookup_support_disposition_and_private_reason_assignment_are_locked",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py::test_stage_vocabulary_clause_boundary_and_no_solver_are_locked",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py::test_fact_family_responsibilities_are_non_overlapping",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py::test_slice1_no_behavior_public_privacy_and_release_boundaries_are_locked",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py::test_roadmap_reconciliation2_preserves_exact_prefix_and_eof_shape",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py::test_reconciliation2_conditional_lifecycle_and_next_gate_are_locked",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py::test_phase51_compatibility_migrations_preserve_historical_locks",
    "tests/test_phase52_private_capability_fact_foundation.py::test_exact_enum_member_inventories_are_locked",
    "tests/test_phase52_private_capability_fact_foundation.py::test_slice2_spec_locks_read_model_non_authority_and_conflict_preservation",
    "tests/test_phase52_scalar_function_operator_signature_facts.py::test_evidence_order_uniqueness_and_paths_are_exact",
    "tests/test_phase50_completion_audit_and_status_lock.py::test_status_vocabulary_and_readiness_handoffs_are_locked",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py::test_slice2_artifacts_title_identity_and_baseline_are_locked",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py::test_high_value_classifications_are_locked",
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py::test_slice1_historical_scope_and_later_authorization_are_locked",
    "tests/test_phase50_type_system_gap_capability_readiness.py::test_slice4_artifacts_baseline_and_current_status_are_locked",
    "tests/test_phase50_window_function_readiness.py::test_slice5_artifacts_baseline_and_current_status_are_locked",
    "tests/test_phase50_window_function_readiness.py::test_spec_section_order_and_no_behavior_authority_are_locked",
    "tests/test_phase50_window_function_readiness.py::test_exact_initial_catalog_and_deferred_families_are_locked",
    "tests/test_phase50_window_function_readiness.py::test_window_components_partition_order_frame_and_names_are_locked",
    "tests/test_phase50_window_function_readiness.py::test_query_phase_and_clause_placement_are_locked",
    "tests/test_phase50_window_function_readiness.py::test_group_type_nullability_and_capability_prerequisites_are_locked",
    "tests/test_phase50_window_function_readiness.py::test_output_dependency_lineage_and_privacy_boundaries_are_locked",
    "tests/test_phase50_window_function_readiness.py::test_diagnostic_dialect_and_bounded_phase53_handoff_are_locked",
    "tests/test_phase52_aggregate_signature_algebra_facts.py::test_static_test_inventory_and_tier1_selection_are_exact",
    "tests/test_phase52_completion_audit_and_status_lock.py::test_static_reader_hash_topology_test_inventory_and_validation_manifests_are_locked",
    "tests/test_phase52_expression_stage_clause_capability_facts.py::test_static_test_inventory_and_tier1_selection_are_exact",
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py::test_static_reader_counts_boundary_hash_and_nested_sha_topology_are_exact",
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py::test_test_inventory_tier1_selectors_and_compatibility_counts_are_exact",
    "tests/test_phase52_scalar_function_operator_signature_facts.py::test_static_test_inventory_tier1_and_tier2_manifest_are_exact",
)
TIER2_EXTRA_NODES = (
    "tests/test_phase52_scalar_function_operator_signature_facts.py::test_package_version_tags_gate2_dirty_state_and_allowlist_are_exact",
    "tests/test_phase52_expression_stage_clause_capability_facts.py::test_package_version_tags_gate2_dirty_state_and_allowlist_are_exact",
    "tests/test_phase52_aggregate_signature_algebra_facts.py::test_package_version_tags_gate2_dirty_state_and_allowlist_are_exact",
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py::test_no_authority_behavior_and_repository_sentinels_are_exact",
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py::test_clean_main_synthetic_merge_dirty_and_historical_repository_states_are_exact",
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py::test_slice8_gate2_gate3_lifecycle_release_and_next_gate_are_exact",
)


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _headings(relative: str, level: int) -> tuple[str, ...]:
    return tuple(
        match.group(1).strip()
        for match in re.finditer(
            rf"^{'#' * level} (?!#)(.+?)\s*$",
            _read(relative),
            flags=re.MULTILINE,
        )
    )


def _section(relative: str, heading: str) -> str:
    text = _read(relative)
    marker = f"## {heading}\n"
    start = text.index(marker) + len(marker)
    end = text.find("\n## ", start)
    return text[start:] if end < 0 else text[start:end]


def _git_output(args: list[str]) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.rstrip()


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
    lines = result.stdout.splitlines()
    assert len(lines) == 1
    assert lines[0] and lines[0].strip() == lines[0]
    return lines[0]


def _assert_phase53_repository_state() -> None:
    if _phase54_active_gate2_is_active():
        return
    tracked = set(_git_output(["diff", "--name-only"]).splitlines()) - {""}
    name_status = tuple(_git_output(["diff", "--name-status"]).splitlines())
    untracked = set(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    ) - {""}
    cached_name_status = tuple(
        _git_output(["diff", "--cached", "--name-status"]).splitlines()
    )
    assert cached_name_status == ()
    assert name_status == tuple(f"M\t{path}" for path in sorted(tracked))

    branch = _git_output(["branch", "--show-current"])
    head = _git_output(["rev-parse", "HEAD"])
    main = _git_optional_ref("refs/heads/main")
    origin_main = _git_optional_ref("refs/remotes/origin/main")
    dirty = tracked | untracked
    slice2_modified = _literal_string_set(SLICE2_STATE_REL, "MODIFIED_PATHS")
    slice2_added = _literal_string_set(SLICE2_STATE_REL, "ADDED_PATHS")
    slice2_allowlist = slice2_modified | slice2_added
    phase54_added = _literal_string_set(PHASE54_SLICE2_STATE_REL, "ADDED_PATHS")
    phase54_modified = _literal_string_set(
        PHASE54_SLICE2_STATE_REL, "NON_READER_MODIFIED_PATHS"
    ) | _literal_string_set(PHASE54_SLICE2_STATE_REL, "MECHANICAL_READER_PATHS")
    phase54_allowlist = phase54_added | phase54_modified
    assert dirty in (
        set(),
        PHASE53_ALLOWLIST_PATHS,
        CI_REPAIR_MODIFIED_PATHS,
        slice2_allowlist,
        phase54_allowlist,
    )

    if dirty == phase54_allowlist:
        assert tracked == phase54_modified
        assert untracked == phase54_added
        assert branch == "main"
        assert head == main == origin_main
        assert head in {
            PHASE54_SLICE2_BASE_HEAD_SHA,
            PHASE54_SLICE4_BASE_HEAD_SHA,
            PHASE54_SLICE5_BASE_HEAD_SHA,
            PHASE54_SLICE6_BASE_HEAD_SHA,
            PHASE54_SLICE7_BASE_HEAD_SHA,
            PHASE54_SLICE8_BASE_HEAD_SHA,
            PHASE54_SLICE9_BASE_HEAD_SHA,
            "b81843acadb294630db361c09949868d004b1bca",
        }
        return

    if dirty == slice2_allowlist:
        assert tracked == slice2_modified
        assert untracked == slice2_added
        assert branch == "main"
        assert head == main == origin_main == SLICE2_BASE_HEAD_SHA
        return

    if dirty == PHASE53_ALLOWLIST_PATHS:
        assert tracked == PHASE53_MODIFIED_PATHS
        assert untracked == PHASE53_ADDED_PATHS
        assert branch == "main"
        assert head == main == origin_main == PHASE53_BASE_HEAD_SHA
        return

    if dirty == CI_REPAIR_MODIFIED_PATHS:
        assert tracked == CI_REPAIR_MODIFIED_PATHS
        assert untracked == set()
        assert branch == "main"
        assert head == main == origin_main == CI_REPAIR_BASE_HEAD_SHA
        return

    assert dirty == set()
    assert tracked == untracked == set()
    if branch == "main":
        assert main == head
    elif branch == PHASE54_POST_SLICE12_INTERLUDE_BRANCH:
        assert phase54_post_slice12_interlude_clean_topic_is_active()
        return
    else:
        assert branch == ""
    if main is not None:
        assert main == head
    if origin_main is not None:
        assert origin_main == head


def _literal_tuple(relative: str, name: str) -> tuple[str, ...]:
    tree = ast.parse(_read(relative), filename=relative)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            continue
        value = ast.literal_eval(node.value)
        assert isinstance(value, tuple) and all(isinstance(item, str) for item in value)
        return value
    raise AssertionError(name)


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
        value = ast.literal_eval(node.value)
        assert isinstance(value, set) and all(isinstance(item, str) for item in value)
        return value
    raise AssertionError(name)


def test_artifact_titles_heading_orders_and_lifecycle_are_locked() -> None:
    for relative in (PLAN_REL, SCOPE_REL, CURRENT_ROADMAP_REL):
        assert (REPO_ROOT / relative).is_file()
    assert _headings(PLAN_REL, 1) == (PLAN_TITLE,)
    assert _headings(SCOPE_REL, 1) == (SCOPE_TITLE,)
    assert _headings(CURRENT_ROADMAP_REL, 1) == (ROADMAP_TITLE,)
    assert _headings(PLAN_REL, 2) == PLAN_H2
    assert _headings(SCOPE_REL, 2) == SCOPE_H2
    assert _headings(CURRENT_ROADMAP_REL, 2) == ROADMAP_H2
    assert _headings(PLAN_REL, 3) == _headings(SCOPE_REL, 3) == ()
    documents = "\n".join(
        _read(path) for path in (PLAN_REL, SCOPE_REL, CURRENT_ROADMAP_REL)
    )
    for required in (
        "Phase 52 is `COMPLETED`",
        "Phase 53 remains `UNSTARTED`",
        "Phase 53 is `ACTIVE`",
        "Slice 8 remains `UNSTARTED` throughout Gate 2",
        "Slice 9 remains `UNSTARTED` throughout Gate 2",
        "Slice 10 remains\n`UNSTARTED` throughout Gate 2",
        "Slice 11 remains\n`UNSTARTED` throughout Gate 2",
        "persistence is not activation",
        "Phase 53 Slice 1 Gate 3",
        "no automatic implementation authorization",
    ):
        assert required in documents, required


def test_historical_roadmap_and_active_roadmap_prefix_are_locked() -> None:
    assert hashlib.sha256(
        (REPO_ROOT / HISTORICAL_ROADMAP_REL).read_bytes()
    ).hexdigest() == (
        "26cc0ae4a68518223d6bf600ad3c4b0b226618aa7ef31b2ae1c25924d2655169"
    )
    predecessor = (REPO_ROOT / PREDECESSOR_REL).read_bytes()
    assert len(predecessor) > 41661
    assert predecessor[:41661].endswith(b"\n")
    assert hashlib.sha256(predecessor[:41661]).hexdigest() == (
        "cd5a297649a757e49d271b59f817b42a907a3cb28b963bca10556e4c4faca6e7"
    )
    text = predecessor.decode("utf-8")
    assert text.count(RECONCILIATION_4_H3) == 1
    assert predecessor.index(RECONCILIATION_4_H3.encode()) >= 41661


@pytest.mark.parametrize(("number", "title"), tuple(enumerate(PHASE53_ROUTE, start=1)))
def test_exact_phase53_slice_route_is_locked(number: int, title: str) -> None:
    marker = f"{number}. {title}"
    assert marker in _read(PLAN_REL)
    assert marker in _read(SCOPE_REL)
    assert marker in _read(CURRENT_ROADMAP_REL)


@pytest.mark.parametrize(("phase", "title"), PHASE_OWNER_ROUTE)
def test_phase54_70_owner_route_is_locked(phase: int, title: str) -> None:
    marker = f"Phase {phase}: {title}"
    assert marker in _read(PLAN_REL)
    assert marker in _read(SCOPE_REL)
    assert re.search(
        rf"^\| {phase} \| {re.escape(title)} \|",
        _read(CURRENT_ROADMAP_REL),
        flags=re.MULTILINE,
    )


@pytest.mark.parametrize(("slot", "owners"), POST60_OWNERS)
def test_post60_owner_slot_reconciliation_is_locked(
    slot: str, owners: tuple[str, ...]
) -> None:
    section = _section(CURRENT_ROADMAP_REL, "POST60 Owner-slot Reconciliation")
    line = next(line for line in section.splitlines() if slot in line)
    assert all(owner in line for owner in owners)
    assert sum(slot in candidate for candidate in section.splitlines()) == 1


@pytest.mark.parametrize("identity", WINDOW_FUNCTION_IDENTITIES)
def test_window_function_identity_inventory_is_locked(identity: str) -> None:
    section = _section(SCOPE_REL, "Exact Eight-function Inventory")
    assert re.search(rf"^\d+\. `{re.escape(identity)}`$", section, re.MULTILINE)
    assert (
        tuple(re.findall(r"^\d+\. `([a-z_]+)`$", section, flags=re.MULTILINE))
        == WINDOW_FUNCTION_IDENTITIES
    )
    assert "namespace `builtin` and role `WINDOW_FUNCTION`" in section


@pytest.mark.parametrize("formula", NULLABILITY_FORMS)
def test_nullability_formula_inventory_is_locked(formula: str) -> None:
    section = _section(SCOPE_REL, "Nullability Formula Inventory")
    assert formula in section
    assert [section.index(item) for item in NULLABILITY_FORMS] == sorted(
        section.index(item) for item in NULLABILITY_FORMS
    )


def test_global_window_keyword_and_contextual_policy_are_locked() -> None:
    documents = "\n".join(
        _read(path) for path in (PLAN_REL, SCOPE_REL, CURRENT_ROADMAP_REL)
    )
    for required in (
        "exact lowercase `window`",
        "future globally reserved grammar keyword",
        "current case-sensitive lexer",
        "`Window` and `WINDOW` remain identifiers",
        "`over`",
        "`partition`",
        "contextual",
        "function names remain semantic catalog identities",
        "no grammar change in Slice 1",
    ):
        assert required in documents, required


def test_generic_compatibility_and_phase64_exclusions_are_locked() -> None:
    documents = _read(PLAN_REL) + _read(SCOPE_REL) + _read(CURRENT_ROADMAP_REL)
    for required in (
        "type variables such as `T`",
        "exact same-type binding",
        "Scalar",
        "Comparable",
        "Orderable",
        "Numeric",
        "binding-referenced result",
        "optional arguments",
        "ordered overload",
        "fail-closed ambiguity",
        "no implicit coercion",
        "least-upper-bound",
        "Decimal precision fusion",
        "Money/Currency/units",
        "backend-native type mapping",
        "Phase 64",
    ):
        assert required in documents, required


def test_release_train_and_phase60_no_publish_boundary_are_locked() -> None:
    documents = _read(PLAN_REL) + _read(SCOPE_REL) + _read(CURRENT_ROADMAP_REL)
    for required in (
        "Phase 60 Gate 3 must not tag",
        "publish",
        "separate Release 0.1.0 workflow",
        "Release Gate 0/1",
        "Release Gate 2",
        "Release Gate 3",
        "TestPyPI",
        "private preview",
        "v0.2.0 ecosystem beta",
        "not automatic v1.0",
    ):
        assert required in documents, required


def test_rust_migration_track_and_no_big_bang_policy_are_locked() -> None:
    documents = _read(PLAN_REL) + _read(SCOPE_REL) + _read(CURRENT_ROADMAP_REL)
    for required in (
        "big-bang",
        "Maintenance Phase 5",
        "Phase 68",
        "first production Rust component",
        "dependency solver/graph",
        "lineage/dependency algorithms",
        "generic binder/nullability evaluator",
        "IR validation/canonicalization",
        "selected SQL helpers",
        "parser only after grammar stabilization",
        "differential tests",
        "explicit fallback",
        "no silent divergence",
    ):
        assert required in documents, required


def test_static_only_no_behavior_public_schema_and_version_boundaries_are_locked() -> (
    None
):
    documents = _read(PLAN_REL) + _read(SCOPE_REL) + _read(CURRENT_ROADMAP_REL)
    for required in (
        "static-only",
        "no Pietto import",
        "parser execution",
        "no source/runtime behavior",
        "generated",
        "golden",
        "CLI JSON v1",
        "Project JSON v2",
        "Semantic Metadata Artifact v1",
        "public API",
        "0.1.0",
        "tag",
        "release",
        "publish",
        "signing",
        "attestation",
    ):
        assert required in documents, required
    _assert_phase53_repository_state()


def test_reader_migrations_reconciliation4_and_current_authority_are_locked() -> None:
    predecessor = _read(PREDECESSOR_REL)
    current = _read(CURRENT_ROADMAP_REL)
    normalized = " ".join(current.split())
    slice2_plan = " ".join(_read(PLAN_REL).split())
    assert predecessor.count(RECONCILIATION_4_H3) == 1
    assert "sole current roadmap authority" in predecessor + current
    assert "839 tracked files" in normalized
    assert "515 Python files" in normalized
    assert "228 Markdown files" in normalized
    assert "434 test modules" in normalized
    assert "4,178 top-level test functions" in normalized
    assert "6,236 collected items" in normalized
    assert "111 passed, 0 deselected" in normalized
    assert "6,090 passed, 146 deselected" in normalized
    assert "6,236 passed" in normalized
    for required in (
        "841 tracked files",
        "516 Python files",
        "229 Markdown files",
        "435 test modules",
        "4194 top-level test functions",
        "6306 collected items",
        "146 focused passes",
        "6121 passed, 185 deselected",
        "clean-CI projection of 6306 passes",
        "844 tracked files",
        "518 Python files",
        "230 Markdown files",
        "436 test modules",
        "4219 top-level test functions",
        "6376 collected items",
        "202 focused items",
        "6193 passed, 183 deselected",
        "6376 clean-CI passes",
        "847 tracked files",
        "520 Python files",
        "231 Markdown files",
        "437 test modules",
        "4250 top-level test functions",
        "6566 collected items",
        "427 focused",
        "6383 passed, 183 deselected",
        "6566 clean-CI passes",
        "850 tracked files",
        "522 Python files",
        "232 Markdown files",
        "438 test modules",
        "4288 top-level test functions",
        "6711 collected items",
        "607 focused",
        "6528 passed, 183 deselected",
        "6711 clean-CI passes",
        "854 tracked files",
        "525 Python files",
        "233 Markdown files",
        "439 test modules",
        "4324 top-level test functions",
        "6867 collected items",
        "775 focused",
        "6682 passed, 185 deselected",
        "6867 clean-CI passes",
        "857 tracked files",
        "527 Python files",
        "234 Markdown files",
        "440 test modules",
        "4365 top-level test functions",
        "7035 collected items",
        "943 focused items",
        "6850 passed, 185 deselected",
        "7035 clean-CI passes",
        "859 tracked files",
        "528 Python files",
        "235 Markdown files",
        "441 test modules",
        "4410 top-level test functions",
        "7314 collected items",
        "1646 focused items",
        "7553 passed and 185 deselected",
        "7738 passes in each clean-CI Python job",
        "861 tracked files",
        "529 Python files",
        "236 Markdown files",
        "442 test modules",
        "4464 top-level test functions",
        "7738 collected items",
        "2273 focused items",
        "8180 passed and 185 deselected",
        "8365 passes in each clean-CI Python job",
        "864 tracked files",
        "531 Python files",
        "237 Markdown files",
        "443 test modules",
        "4531 top-level test functions",
        "8365 collected items",
        "3107 focused items",
        "9014 passed, 185 deselected",
        "9199 passes in each clean-CI Python job",
        "867 tracked files",
        "533 Python files",
        "238 Markdown files",
        "444 test modules",
        "4612 top-level test functions",
        "9199 collected items",
        "879 tracked files",
        "541 Python files",
        "242 Markdown files",
        "448 test modules",
        "4836 top-level test functions",
        "10784 collected items",
        "4765 focused passes",
        "10599 passed / 185 deselected",
        "881 tracked files",
        "542 Python files",
        "243 Markdown files",
        "449 test modules",
        "4852 top-level test functions",
        "10800 collected items",
        "4781 focused passes",
        "10615 passed / 185 deselected",
    ):
        assert required in slice2_plan, required
    for relative in (
        "tests/test_phase52_aggregate_signature_algebra_facts.py",
        "tests/test_phase52_expression_stage_clause_capability_facts.py",
        "tests/test_phase52_scalar_function_operator_signature_facts.py",
        "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
        "tests/test_phase52_completion_audit_and_status_lock.py",
    ):
        assert "(462, 5339)" in _read(relative)
    for relative in (
        "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
        "tests/test_phase52_completion_audit_and_status_lock.py",
    ):
        assert "(571, 266)" in _read(relative)


def test_gate2_validation_depth_one_gate3_activation_and_stop_conditions_are_locked() -> (
    None
):
    _assert_phase53_repository_state()
    documents = _read(PLAN_REL)
    normalized = documents.replace(",", "")
    for required in (
        "depth-one",
        "9014 passed 185 deselected",
        "9199 passes in each clean-CI Python job",
        "separately authorized Gate 3",
        "one write-mode Ruff invocation",
        "A3/M61/D0",
        "STOP",
    ):
        assert required in normalized, required
    assert 3107 == 834 + 2273
    assert 9199 - 185 == 9014


_SLICE11_READER_MIGRATION_PATHS = (
    "docs/spec/phase53-window-local-ordering-direction-determinism-contract-v1.md",
    "src/pietto/semantic/window_order_analysis.py",
    "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
)
# Phase 53 Slice 13 reader migration.
