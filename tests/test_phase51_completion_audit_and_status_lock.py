from __future__ import annotations

import ast
import hashlib
import inspect
import re
import subprocess
import tomllib
from dataclasses import fields
from pathlib import Path

from _phase54_active_gate2_manifest import (
    phase54_post_slice12_interlude_expected_allowlist_paths,
    phase54_post_slice12_interlude_expected_added_paths,
    PHASE54_POST_REVIEW_PRODUCT_REPAIR1_BASE,
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_BASE,
    PHASE54_POST_REVIEW_PRODUCT_REPAIR3_BASE,
    PHASE54_POST_REVIEW_PRODUCT_REPAIR4_BASE,
    PHASE54_POST_REVIEW_PRODUCT_REPAIR5_BASE,
    PHASE54_POST_REVIEW_PRODUCT_REPAIR6_BASE,
    PHASE54_POST_REVIEW_PRODUCT_REPAIR7_BASE,
    PHASE54_POST_REVIEW_PRODUCT_REPAIR8_BASE,
    PHASE54_POST_REVIEW_PRODUCT_REPAIR9_BASE,
    PHASE54_SLICE11_PR_CI_REPAIR_MODIFIED_PATHS,
    PHASE54_SLICE12_PR_CI_REPAIR_MODIFIED_PATHS,
    PHASE54_SLICE12_MECHANICAL_REPAIR3_MODIFIED_PATHS,
    PHASE54_SLICE12_MECHANICAL_REPAIR4_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR3_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR10_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR11_MODIFIED_PATHS,
    PHASE54_SLICE11_PYTHON313_REPAIR_MODIFIED_PATHS,
    PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_MODIFIED_PATHS,
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
    phase54_slice11_pr_ci_repair_is_active,
    phase54_slice12_pr_ci_repair_is_active,
    phase54_slice12_mechanical_repair3_is_active,
    phase54_slice12_mechanical_repair4_is_active,
    phase54_slice12_product_repair3_is_active,
    phase54_slice12_product_repair10_is_active,
    phase54_slice12_product_repair11_is_active,
    phase54_slice11_python313_repair_is_active,
    phase54_slice11_substantive_recovery_is_active,
)

from pietto._project.aggregate_grouped_clause_facts import (
    ProjectAggregateGroupedClauseReadiness,
    ProjectRelationClauseDependencyFact,
    build_project_aggregate_grouped_clause_readiness,
)
from pietto._project.aggregate_grouped_dependency_lineage import (
    ProjectAggregateGroupedDependencyLineageReadiness,
    build_project_aggregate_grouped_dependency_lineage_readiness,
)
from pietto._project.aggregate_grouped_persistence import (
    ProjectAggregateGroupedPersistenceBundle,
    build_project_aggregate_grouped_persistence,
)
from pietto._project.aggregate_grouped_schema import (
    ProjectAggregateGroupedCandidateAttempt,
    ProjectAggregateGroupedSchemaFinalization,
    ProjectAggregateSchemaFacts,
    ProjectAggregateSelectedResult,
    ProjectGroupedSchemaFacts,
    ProjectGroupedSelectedResult,
    ProjectGroupKeyFact,
    ProjectGroupKeySchemaFacts,
    build_project_aggregate_grouped_schema_finalization,
    build_project_aggregate_schema_facts,
    build_project_grouped_schema_facts,
    build_project_group_key_schema_facts,
)
from pietto._project.model import ProjectAggregateResultFact, ProjectRowField

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-51-aggregate-grouped-output-schema-foundation.md"
)
ACTIVE_ROADMAP_PATH = REPO_ROOT / "docs/spec/pietto-active-roadmap-phase51-60-v1.md"
HISTORICAL_ROADMAP_PATH = REPO_ROOT / "docs/spec/pietto-roadmap-phase45-60-v1.md"
SPEC_PATH = REPO_ROOT / "docs/spec/phase51-completion-audit-and-status-lock-v1.md"
SELF_PATH = REPO_ROOT / "tests/test_phase51_completion_audit_and_status_lock.py"

SPEC_TITLE = "# Phase 51 Slice 12 Completion Audit And Status Lock v1"
SPEC_H2_HEADINGS = (
    "Purpose And Slice Identity",
    "Authority And Evidence Hierarchy",
    "Trusted Slice 11 Baseline",
    "Phase 51 Slice Ledger",
    "Phase 51 Artifact Inventory",
    "Historical Allowlist And Repair Preservation",
    "Final Capability Classification",
    "Result And Schema Foundation Audit",
    "Dependency And Lineage Audit",
    "Private Persistence And Downstream Propagation Audit",
    "Failure And Diagnostic Audit",
    "Public Artifact Compatibility Audit",
    "Private Carrier Privacy Audit",
    "Single-file Compiler IR SQL Runtime And Database Compatibility Audit",
    "Compiler And Project-private Lock Audit",
    "Deferred-owner Audit",
    "Phase 52 Handoff",
    "Package Version And Release Audit",
    "Protected Surface Audit",
    "Completion Encoding Decision",
    "Gate 2 Pre-completion State",
    "Gate 3 Completion Condition",
    "Post-completion Phase 52–60 Status",
    "Active-roadmap Reconciliation",
    "Exact Gate 2 Allowlist",
    "Validation And Clean-CI Boundary",
    "Separate Authorization Boundary",
    "Stop Conditions",
)

PLAN_SLICE11_HEADING = "### Slice 11 Gate 2 Bounded Implementation Status"
PLAN_SLICE12_HEADING = "### Slice 12 Gate 2 Bounded Implementation Status"
PLAN_DISCIPLINE_HEADING = "## Cross-slice Gate Discipline"
ROADMAP_RECONCILIATION_HEADING = (
    "### Reconciliation 1 — Phase 51 Conditional Completion And Phase 52 Handoff"
)
ROADMAP_PREFIX_DIGEST = (
    "2de797d68fd621bf6198cc19f24e07bbb4e101c13683bfa8792614d479af3c75"
)

SLICE12_GATE2_PATHS = {
    "docs/plan/phase-51-aggregate-grouped-output-schema-foundation.md",
    "docs/spec/pietto-active-roadmap-phase51-60-v1.md",
    "docs/spec/phase51-completion-audit-and-status-lock-v1.md",
    "tests/test_phase51_completion_audit_and_status_lock.py",
}
SLICE12_UNTRACKED_PATHS = {
    "docs/spec/phase51-completion-audit-and-status-lock-v1.md",
    "tests/test_phase51_completion_audit_and_status_lock.py",
}

PHASE52_GATE2_PATHS = {
    "docs/plan/phase-52-core-type-system-capability-foundation.md",
    "docs/spec/phase52-core-type-system-capability-foundation-scope-lock-v1.md",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py",
    "docs/spec/pietto-active-roadmap-phase51-60-v1.md",
    "tests/test_phase51_aggregate_grouped_output_schema_foundation_scope_lock.py",
    "tests/test_phase51_aggregate_only_project_row_schema.py",
    "tests/test_phase51_grouped_aggregate_project_row_schema.py",
    "tests/test_phase51_selected_let_accepted_expression_aggregate.py",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
    "tests/test_phase51_completion_audit_and_status_lock.py",
}
PHASE52_UNTRACKED_PATHS = {
    "docs/plan/phase-52-core-type-system-capability-foundation.md",
    "docs/spec/phase52-core-type-system-capability-foundation-scope-lock-v1.md",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py",
}
SLICE2_BASE_HEAD_SHA = "d8a5e9ab3de70ce30575513c73560c86430eca63"
SLICE4_BASE_HEAD_SHA = "15bae172ee151e370fe59d3bf909d735aee6aa90"
SLICE4_PATH_COUNTS = (138, 2, 140)
SLICE5_BASE_HEAD_SHA = "0f3c955c5a5fbd8046ef611ad1bef0b636c8be01"
SLICE5_PATH_COUNTS = (164, 3, 167)
SLICE6_BASE_HEAD_SHA = "c44a4271d9592cb393d2232f127a59d8466cc60a"
SLICE6_PATH_COUNTS = (57, 4, 61)
SLICE7_BASE_HEAD_SHA = "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16"
SLICE7_PATH_COUNTS = (59, 3, 62)
SLICE8_BASE_HEAD_SHA = "027b33cafcfd58916a89e299487dad38d24ade6c"
SLICE8_PATH_COUNTS = (66, 3, 69)
SLICE9_BASE_HEAD_SHA = "0ceb9a476e6592714cdc76845949ba0ae5123eb5"
SLICE9_PATH_COUNTS = (68, 3, 71)
SLICE2_STATE_REL = "tests/_phase54_active_gate2_manifest.py"

PHASE51_SLICE_ARTIFACTS = (
    (
        "Scope Architecture And Active-roadmap Lock",
        "docs/spec/phase51-aggregate-grouped-output-schema-foundation-scope-lock-v1.md",
        "tests/test_phase51_aggregate_grouped_output_schema_foundation_scope_lock.py",
    ),
    (
        "Private Result-role And Output-identity Foundation",
        "docs/spec/phase51-private-result-role-output-identity-v1.md",
        "tests/test_phase51_private_result_role_output_identity.py",
    ),
    (
        "Group-key Project Row-schema Foundation",
        "docs/spec/phase51-group-key-project-row-schema-foundation-v1.md",
        "tests/test_phase51_group_key_project_row_schema.py",
    ),
    (
        "Aggregate-only Project Row-schema Foundation",
        "docs/spec/phase51-aggregate-only-result-candidate-foundation-v1.md",
        "tests/test_phase51_aggregate_only_project_row_schema.py",
    ),
    (
        "Grouped Aggregate Project Row-schema Foundation",
        "docs/spec/phase51-grouped-key-aggregate-candidate-assembly-v1.md",
        "tests/test_phase51_grouped_aggregate_project_row_schema.py",
    ),
    (
        "Selected-let And Accepted-expression Aggregate Integration",
        "docs/spec/phase51-aggregate-expression-row-let-candidate-integration-v1.md",
        "tests/test_phase51_selected_let_accepted_expression_aggregate.py",
    ),
    (
        "Type Nullability Availability-state And Duplicate Handling",
        "docs/spec/phase51-type-nullability-availability-state-duplicate-handling-v1.md",
        "tests/test_phase51_aggregate_grouped_state_duplicate_hardening.py",
    ),
    (
        "Clause-dependency And Fail-closed Hardening",
        "docs/spec/phase51-aggregate-grouped-clause-dependency-readiness-v1.md",
        "tests/test_phase51_clause_dependency_fail_closed.py",
    ),
    (
        "Origin Provenance Dependency And Lineage Integration",
        "docs/spec/phase51-origin-provenance-dependency-lineage-integration-v1.md",
        "tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py",
    ),
    (
        "Downstream Propagation And Qualification",
        "docs/spec/phase51-downstream-propagation-qualification-v1.md",
        "tests/test_phase51_aggregate_grouped_downstream_propagation.py",
    ),
    (
        "Cross-phase Readiness Privacy And Compatibility Closure",
        "docs/spec/phase51-cross-phase-readiness-privacy-compatibility-closure-v1.md",
        "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
    ),
)

PHASE51_LIFECYCLE_TOKENS = (
    (
        "0946c7d9f81323a1fe4a711014174fd0d48035fc",
        "Add Phase 51 active roadmap and scope lock",
        "29210218630",
        "5430 passed",
    ),
    (
        "ac6f07e2e804a7c6bc661bf444ad16a0170930c6",
        "Add Phase 51 private result role foundation",
        "29214203134",
        "1 failed and 5449 passed",
        "e81fde473d4c4d2c1eee9db032daa0b50be60e82",
        "Fix Phase 51 Slice 2 plan heading lock",
        "29215802595",
        "5450 passed",
    ),
    (
        "882600c797fb885edbfd27ba37d47607c4a5a0db",
        "Add Phase 51 group-key schema foundation",
        "29224454642",
        "5474 passed",
    ),
    (
        "41932133ee6223ff8de90018568bebb6731d90d6",
        "Add Phase 51 aggregate result candidates",
        "29232106422",
        "5541 passed",
    ),
    (
        "300651b2944ca45e31744bfcd269a3b575d0b090",
        "Add Phase 51 grouped candidate assembly",
        "29236828662",
        "5564 passed",
    ),
    (
        "98f96d32cc4af67bb8703398f2116a4e55b56460",
        "Add Phase 51 aggregate expression candidates",
        "29280446165",
        "5616 passed",
    ),
    (
        "122b7efa50f2383badf328803b82ef5ba7fb96f4",
        "Add Phase 51 aggregate state finalization",
        "29288413076",
        "5639 passed",
    ),
    (
        "fa0622331dfe3e11fe6b762c7e0a215794ca3f6c",
        "Add Phase 51 clause dependency readiness",
        "29301595259",
        "5702 passed",
    ),
    (
        "8370045ba686e99273b6b0138378fd09bac0806f",
        "Add Phase 51 origin dependency lineage",
        "29310398020",
        "9908d7f15594cc27d45885613a4a4bf350bea32d",
        "Fix CI matrix interpreter binding",
        "29314629944",
        "5716 passed",
    ),
    (
        "39a58d50b8e5ef420cb637c42124422c1d82911d",
        "Add Phase 51 downstream propagation",
        "29325365925",
        "1 failed and 5731 passed",
        "ed3e79137722443677fc39b1bfe83e209bcb9868",
        "Refresh Phase 51 Slice 9 project lock",
        "29326813216",
        "5732 passed",
    ),
    (
        "5138d28ee2d0a258076a68a6f98c74ce15a93bf8",
        "Add Phase 51 cross-phase closure",
        "29371109641",
        "5739 passed",
    ),
)

PHASE51_FOCUSED_COUNTS = (
    (13, 13),
    (11, 20),
    (14, 24),
    (10, 60),
    (13, 21),
    (12, 61),
    (17, 23),
    (29, 63),
    (12, 14),
    (16, 16),
    (7, 7),
)

EXPECTED_HELPERS = (
    "_read",
    "_normalized",
    "_headings",
    "_git_output",
    "_dirty_paths",
    "_digest",
    "_compiler_digest",
    "_project_private_paths",
    "_top_level_functions",
    "_pytest_inventory",
)
EXPECTED_TESTS = (
    "test_slice12_artifacts_title_and_exact_heading_order_are_locked",
    "test_slice1_11_lifecycle_artifact_and_focused_item_ledgers_are_exact",
    "test_result_schema_carrier_field_orders_and_builder_signatures_are_locked",
    "test_dependency_lineage_persistence_and_downstream_completion_is_locked",
    "test_failure_diagnostic_and_non_concrete_behavior_remains_compatible",
    "test_project_json_public_exports_and_private_serialization_boundaries_are_locked",
    "test_deferred_owner_phase52_handoff_and_active_roadmap_reconciliation_are_locked",
    "test_live_compiler_project_private_protected_version_and_tag_locks_are_dirty_safe",
    "test_historical_allowlists_migrations_and_clean_only_guards_are_accounted",
    "test_completion_encoding_gate2_gate3_and_no_release_boundaries_are_locked",
    "test_static_git_helper_and_exact_slice12_dirty_set_are_locked",
)

BOUNDARY_PATHS = (
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_packaging_smoke.py",
    "tests/test_phase11_validation_entrypoint.py",
    "tests/test_phase12_completion_audit.py",
    "tests/test_phase12_composition_cli_json_goldens.py",
)
PROTECTED_HASHES = {
    ".github/workflows/ci.yml": (
        "4db1c9a49b0af230bae3f088bf84524e210e0afcd6a87250322e5036a69e8d94"
    ),
    ".python-version": (
        "7b55f8e67b5623c4bef3fa691288da9437d79d3aba156de48d481db32ac7d16d"
    ),
    "pyproject.toml": (
        "36aa8e1d19a8409e56e0163a465b9608a88c1bffe644165ba49db49bf5ec3d01"
    ),
    "uv.lock": "a7d9125995e98a8a74d3664ceae7801cc1f4cce74ec323933da67838be199cea",
    "docs/spec/pietto-roadmap-phase45-60-v1.md": (
        "26cc0ae4a68518223d6bf600ad3c4b0b226618aa7ef31b2ae1c25924d2655169"
    ),
}
COMPILER_DIGEST = "f13fe1e2d0e68b4fc1161a18e7f601008efd1873b4a673ff21b89a7130c148d9"
PROJECT_PRIVATE_DIGEST = (
    "06fa9c92bc3f26da8555355138c90e5c19e31d2b9435c2b497291b259deacfba"
)

PROJECT_JSON_V2_KEYS = (
    "schema_version",
    "command",
    "mode",
    "ok",
    "project",
    "inputs",
    "diagnostics",
    "cli_errors",
    "result",
)
PRIVATE_SERIALIZATION_TOKENS = (
    "relation_row_schemas",
    "relation_row_schema_states",
    "relation_let_scope_facts",
    "relation_aggregate_result_facts",
    "relation_row_dependency_graphs",
    "relation_row_lineages",
    "ProjectAggregateGroupedSchemaFinalization",
    "ProjectAggregateGroupedClauseReadiness",
    "ProjectAggregateGroupedDependencyLineageReadiness",
    "ProjectAggregateGroupedPersistenceBundle",
)

DEFERRED_OWNERS = (
    "PHASE_52",
    "PHASE_53",
    "PHASE_54",
    "PHASE_55",
    "PHASE_56",
    "PHASE_57",
    "PHASE_58",
    "PHASE_59",
    "POST60_ADVANCED_AGGREGATION_GROUPING",
    "POST60_ADVANCED_TYPE_NATIVE_MAPPING",
    "POST60_ADVANCED_WINDOWS",
    "POST60_ADVANCED_MODULE_PACKAGE_ASSETS",
    "POST60_REMOTE_PACKAGE_MANAGER",
    "POST60_DEPENDENCY_SOLVER_LOCKFILE",
    "POST60_EXTENSION_LOWERING",
    "POST60_PUBLIC_PROJECT_SCHEMA_LINEAGE_EXPANSION",
    "POST60_PROJECT_IR",
    "POST60_MULTI_RELATION_SQL",
    "POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT",
    "OUT_OF_SCOPE_CHARTER",
)

HISTORICAL_ALLOWLIST_COUNTS = (
    (
        "tests/test_phase51_aggregate_grouped_output_schema_foundation_scope_lock.py",
        "ALLOWED_PHASE51_SLICE1_GATE2_PATHS",
        4,
    ),
    (
        "tests/test_phase51_selected_let_accepted_expression_aggregate.py",
        "EXPECTED_GATE2_PATHS",
        15,
    ),
    (
        "tests/test_phase51_aggregate_grouped_state_duplicate_hardening.py",
        "EXPECTED_GATE2_PATHS",
        16,
    ),
    (
        "tests/test_phase51_clause_dependency_fail_closed.py",
        "EXPECTED_GATE2_PATHS",
        13,
    ),
    (
        "tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py",
        "EXPECTED_GATE2_PATHS",
        15,
    ),
    (
        "tests/test_phase51_aggregate_grouped_downstream_propagation.py",
        "EXPECTED_GATE2_PATHS",
        38,
    ),
    (
        "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
        "EXPECTED_GATE2_PATHS",
        20,
    ),
)

CLEAN_ONLY_GUARDS = (
    (
        "tests/test_phase51_private_result_role_output_identity.py",
        "test_forbidden_compiler_dependency_and_lineage_surfaces_have_no_diff",
    ),
    (
        "tests/test_phase51_group_key_project_row_schema.py",
        "test_forbidden_existing_project_compiler_and_public_surfaces_have_no_diff",
    ),
    (
        "tests/test_phase51_aggregate_only_project_row_schema.py",
        "test_forbidden_existing_project_compiler_and_public_surfaces_have_no_diff",
    ),
    (
        "tests/test_phase51_grouped_aggregate_project_row_schema.py",
        "test_forbidden_existing_project_compiler_and_public_surfaces_have_no_diff",
    ),
    (
        "tests/test_phase51_selected_let_accepted_expression_aggregate.py",
        "test_plan_contract_versions_protected_boundaries_and_exact_dirty_set",
    ),
    (
        "tests/test_phase51_aggregate_grouped_state_duplicate_hardening.py",
        "test_slice7_documentation_exact_allowlist_and_protected_boundaries",
    ),
    (
        "tests/test_phase51_clause_dependency_fail_closed.py",
        "test_slice8_documentation_exact_allowlist_dirty_and_protected_boundaries",
    ),
    (
        "tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py",
        "test_slice9_documentation_allowlist_hash_and_protected_boundaries",
    ),
    (
        "tests/test_phase51_aggregate_grouped_downstream_propagation.py",
        "test_slice10_documentation_allowlist_hashes_and_protected_boundaries",
    ),
    (
        "tests/test_phase47_downstream_readiness_hardening.py",
        "test_phase47_slice9_package_version_and_dirty_paths_are_locked",
    ),
    (
        "tests/test_phase48_upstream_non_concrete_schema_propagation.py",
        "test_phase48_slice7_package_version_and_dirty_paths_are_locked",
    ),
    (
        "tests/test_phase48_query_to_query_multi_hop_propagation.py",
        "test_phase48_slice5_package_version_and_dirty_paths_are_locked",
    ),
    (
        "tests/test_phase49_computed_alias_project_row_schema_mvp.py",
        "test_slice4_keeps_forbidden_project_files_untouched",
    ),
    (
        "tests/test_phase49_computed_alias_project_row_schema_mvp.py",
        "test_phase49_slice4_package_version_and_dirty_paths_are_locked",
    ),
    (
        "tests/test_phase49_computed_alias_origin_provenance_privacy.py",
        "test_slice5_forbidden_project_files_are_untouched",
    ),
    (
        "tests/test_phase49_computed_alias_origin_provenance_privacy.py",
        "test_slice5_package_version_and_dirty_paths_are_locked",
    ),
    (
        "tests/test_phase49_private_row_level_dependency_graph_scaffold.py",
        "test_slice9_forbidden_files_have_no_diff",
    ),
    (
        "tests/test_phase49_private_row_level_dependency_graph_scaffold.py",
        "test_slice9_package_version_and_dirty_paths_are_locked",
    ),
    (
        "tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py",
        "test_slice10_forbidden_files_have_no_diff",
    ),
    (
        "tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py",
        "test_slice10_package_version_and_dirty_paths_are_locked",
    ),
    (
        "tests/test_phase49_computed_let_multi_hop_row_lineage.py",
        "test_slice11_forbidden_files_source_boundaries_version_and_dirty_paths",
    ),
    (
        "tests/test_phase49_unknown_deferred_diagnostic_ordering_hardening.py",
        "test_slice12_forbidden_files_package_version_and_dirty_paths_are_locked",
    ),
    (
        "tests/test_phase49_let_visibility_order_shadowing_hardening.py",
        "test_slice8_forbidden_files_have_no_diff",
    ),
    (
        "tests/test_phase49_let_visibility_order_shadowing_hardening.py",
        "test_slice8_package_version_and_dirty_paths_are_locked",
    ),
    (
        "tests/test_phase49_selected_let_derived_output_schema.py",
        "test_slice7_forbidden_files_remain_unchanged",
    ),
    (
        "tests/test_phase49_selected_let_derived_output_schema.py",
        "test_slice7_package_version_and_dirty_paths_are_locked",
    ),
    (
        "tests/test_phase51_aggregate_grouped_output_schema_foundation_scope_lock.py",
        "test_historical_roadmap_package_tag_goldens_protected_diffs_and_dirty_set",
    ),
    (
        "tests/test_phase49_compatibility_privacy_hash_lock_readiness.py",
        "test_slice13_package_version_and_dirty_paths_are_locked",
    ),
    (
        "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
        "test_slice11_contract_plan_allowlist_and_protected_boundaries_are_locked",
    ),
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def _headings(path: Path, level: int) -> tuple[str, ...]:
    prefix = f"{'#' * level} "
    return tuple(
        line.removeprefix(prefix)
        for line in _read(path).splitlines()
        if line.startswith(prefix) and not line.startswith(f"{prefix}#")
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


def _dirty_paths() -> set[str]:
    paths: set[str] = set()
    for line in _git_output(
        ["status", "--short", "--untracked-files=all"]
    ).splitlines():
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", maxsplit=1)[1]
        paths.add(path)
    return paths


def _digest(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        digest.update(relative_path.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _compiler_digest() -> tuple[int, str]:
    paths = [REPO_ROOT / "Makefile", REPO_ROOT / "grammar/Pietto.g4"]
    paths.extend(
        path
        for path in (REPO_ROOT / "src/pietto").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )
    ordered_paths = tuple(
        sorted(paths, key=lambda path: path.relative_to(REPO_ROOT).as_posix())
    )
    return len(ordered_paths), _digest(ordered_paths)


def _project_private_paths() -> tuple[Path, ...]:
    return tuple(
        sorted(
            (
                path
                for path in (REPO_ROOT / "src/pietto/_project").rglob("*")
                if path.is_file()
                and "__pycache__" not in path.parts
                and path.suffix != ".pyc"
            ),
            key=lambda path: path.relative_to(REPO_ROOT).as_posix(),
        )
    )


def _top_level_functions(path: Path) -> tuple[str, ...]:
    tree = ast.parse(_read(path), filename=path.as_posix())
    return tuple(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )


def _pytest_inventory(paths: tuple[Path, ...]) -> tuple[int, int]:
    function_count = 0
    item_count = 0
    for path in paths:
        tree = ast.parse(_read(path), filename=path.as_posix())
        named_parameter_counts = {
            node.targets[0].id: len(node.value.elts)
            for node in tree.body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, (ast.List, ast.Set, ast.Tuple))
        }
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not node.name.startswith("test_"):
                continue
            function_count += 1
            expansion = 1
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                if not isinstance(decorator.func, ast.Attribute):
                    continue
                if decorator.func.attr != "parametrize":
                    continue
                assert len(decorator.args) >= 2
                values = decorator.args[1]
                if isinstance(values, ast.Name):
                    expansion *= named_parameter_counts[values.id]
                else:
                    assert isinstance(values, (ast.List, ast.Set, ast.Tuple))
                    expansion *= len(values.elts)
            item_count += expansion
    return function_count, item_count


def test_slice12_artifacts_title_and_exact_heading_order_are_locked() -> None:
    assert PLAN_PATH.is_file()
    assert ACTIVE_ROADMAP_PATH.is_file()
    assert SPEC_PATH.is_file()
    assert SELF_PATH.is_file()
    assert _read(SPEC_PATH).startswith(f"{SPEC_TITLE}\n")
    assert _headings(SPEC_PATH, 2) == SPEC_H2_HEADINGS

    plan_headings = _headings(PLAN_PATH, 3)
    assert plan_headings.count(PLAN_SLICE12_HEADING.removeprefix("### ")) == 1
    plan_lines = _read(PLAN_PATH).splitlines()
    assert plan_lines.index(PLAN_SLICE11_HEADING) < plan_lines.index(
        PLAN_SLICE12_HEADING
    )
    assert plan_lines.index(PLAN_SLICE12_HEADING) < plan_lines.index(
        PLAN_DISCIPLINE_HEADING
    )
    assert _read(ACTIVE_ROADMAP_PATH).count(ROADMAP_RECONCILIATION_HEADING) == 1

    contract = _read(SPEC_PATH)
    for relative_path in SLICE12_GATE2_PATHS:
        assert f"`{relative_path}`" in contract


def test_slice1_11_lifecycle_artifact_and_focused_item_ledgers_are_exact() -> None:
    contract = _normalized(SPEC_PATH)
    assert len(PHASE51_SLICE_ARTIFACTS) == 11
    assert len(PHASE51_LIFECYCLE_TOKENS) == 11
    assert len(PHASE51_FOCUSED_COUNTS) == 11

    for artifact, lifecycle, focused_counts in zip(
        PHASE51_SLICE_ARTIFACTS,
        PHASE51_LIFECYCLE_TOKENS,
        PHASE51_FOCUSED_COUNTS,
        strict=True,
    ):
        title, spec_path, test_path = artifact
        assert (REPO_ROOT / spec_path).is_file(), spec_path
        assert (REPO_ROOT / test_path).is_file(), test_path
        for required in (title, spec_path, test_path, *lifecycle):
            assert required in contract, required
        assert _pytest_inventory((REPO_ROOT / test_path,)) == focused_counts

    assert tuple(
        sum(counts[index] for counts in PHASE51_FOCUSED_COUNTS) for index in (0, 1)
    ) == (154, 322)


def test_result_schema_carrier_field_orders_and_builder_signatures_are_locked() -> None:
    carrier_fields = (
        (
            ProjectRowField,
            (
                "name",
                "resolved_type",
                "nullability",
                "field_def",
                "provenance",
                "result_role",
            ),
        ),
        (
            ProjectAggregateResultFact,
            ("function", "output_name", "grouped", "argument_count", "location"),
        ),
        (
            ProjectGroupKeyFact,
            ("item", "effective_expression", "field_identity", "input_field"),
        ),
        (ProjectGroupKeySchemaFacts, ("group_keys", "selected_fields")),
        (ProjectAggregateSelectedResult, ("field", "fact")),
        (ProjectAggregateSchemaFacts, ("selected_results",)),
        (ProjectGroupedSelectedResult, ("field", "aggregate_fact")),
        (ProjectGroupedSchemaFacts, ("group_keys", "selected_results")),
        (ProjectAggregateGroupedCandidateAttempt, ("facts", "failure_reason")),
        (
            ProjectAggregateGroupedSchemaFinalization,
            ("state", "aggregate_result_facts"),
        ),
        (
            ProjectRelationClauseDependencyFact,
            (
                "kind",
                "source_occurrence",
                "target_occurrence",
                "target_field",
                "aggregate_result_fact",
            ),
        ),
        (
            ProjectAggregateGroupedClauseReadiness,
            (
                "definition",
                "finalization",
                "status",
                "reason",
                "dependency_facts",
                "limit_present",
            ),
        ),
        (
            ProjectAggregateGroupedDependencyLineageReadiness,
            ("definition", "clause_readiness", "dependency_graph", "lineage"),
        ),
        (
            ProjectAggregateGroupedPersistenceBundle,
            (
                "definition",
                "let_scope_facts",
                "dependency_lineage_readiness",
                "state",
                "aggregate_result_facts",
            ),
        ),
    )
    for carrier, expected_fields in carrier_fields:
        assert tuple(field.name for field in fields(carrier)) == expected_fields

    builder_signatures = (
        (
            build_project_group_key_schema_facts,
            ("definition", "input_schema", "upstream_symbol", "fallback_path"),
        ),
        (
            build_project_aggregate_schema_facts,
            ("definition", "input_schema", "upstream_symbol", "fallback_path"),
        ),
        (
            build_project_grouped_schema_facts,
            ("definition", "input_schema", "upstream_symbol", "fallback_path"),
        ),
        (
            build_project_aggregate_grouped_schema_finalization,
            (
                "definition",
                "input_schema",
                "upstream_symbol",
                "fallback_path",
                "let_scope_facts",
            ),
        ),
        (
            build_project_aggregate_grouped_clause_readiness,
            (
                "definition",
                "input_schema",
                "upstream_symbol",
                "fallback_path",
                "let_scope_facts",
            ),
        ),
        (
            build_project_aggregate_grouped_dependency_lineage_readiness,
            (
                "definition",
                "input_schema",
                "upstream_symbol",
                "upstream_lineage",
                "fallback_path",
                "let_scope_facts",
            ),
        ),
        (
            build_project_aggregate_grouped_persistence,
            (
                "definition",
                "input_schema",
                "upstream_symbol",
                "upstream_lineage",
                "fallback_path",
            ),
        ),
    )
    for builder, expected_parameters in builder_signatures:
        signature = inspect.signature(builder)
        assert tuple(signature.parameters) == expected_parameters
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in signature.parameters.values()
        )


def test_dependency_lineage_persistence_and_downstream_completion_is_locked() -> None:
    slice10_path = (
        REPO_ROOT / "tests/test_phase51_aggregate_grouped_downstream_propagation.py"
    )
    slice10_functions = set(_top_level_functions(slice10_path))
    assert {
        "test_persistence_bundle_is_frozen_atomic_and_retains_one_slice9_result",
        "test_production_calls_slice9_readiness_once_per_eligible_definition",
        "test_aggregate_only_schema_facts_graph_and_lineage_are_persisted_atomically",
        "test_selected_let_and_field_bearing_expression_aggregates_use_one_canonical_fact_set",
        "test_one_hop_downstream_uses_bare_and_immediate_qualified_outputs_only",
        "test_multi_hop_table_query_chain_activates_after_complete_upstream_persistence",
        "test_non_concrete_results_persist_atomically_and_do_not_activate_downstream",
    } <= slice10_functions

    persistence = _read(
        REPO_ROOT / "src/pietto/_project/aggregate_grouped_persistence.py"
    )
    model = _read(REPO_ROOT / "src/pietto/_project/model.py")
    assert (
        persistence.count(
            "build_project_aggregate_grouped_dependency_lineage_readiness("
        )
        == 1
    )
    assert persistence.count("build_project_relation_let_scope_facts(") == 1
    assert persistence.count("let_scope_facts=let_scope_facts") == 2
    assert (
        model.count("persistence = build_project_aggregate_grouped_persistence(") == 1
    )
    assert (
        "Validate one complete local bundle, then publish every aligned map." in model
    )
    for map_name in (
        "relation_row_schemas",
        "relation_row_schema_states",
        "relation_let_scope_facts",
        "relation_aggregate_result_facts",
        "relation_window_result_facts",
        "relation_row_dependency_graphs",
        "relation_row_lineages",
    ):
        assert f"{map_name}[definition]" in model
    assert model.count("completed.add(definition)") == 4


def test_failure_diagnostic_and_non_concrete_behavior_remains_compatible() -> None:
    slice10_functions = set(
        _top_level_functions(
            REPO_ROOT / "tests/test_phase51_aggregate_grouped_downstream_propagation.py"
        )
    )
    assert {
        "test_one_hop_downstream_uses_bare_and_immediate_qualified_outputs_only",
        "test_non_concrete_results_persist_atomically_and_do_not_activate_downstream",
        "test_duplicate_unknown_invalid_unresolved_and_cycle_outcomes_remain_atomic",
        "test_pure_grouping_persists_helper_deferred_reason_with_empty_payloads",
    } <= slice10_functions
    slice11_functions = set(
        _top_level_functions(
            REPO_ROOT
            / "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py"
        )
    )
    assert (
        "test_mixed_aggregate_grouped_diagnostic_order_and_non_concrete_suppression_are_exact"
        in slice11_functions
    )

    contract = _normalized(SPEC_PATH)
    for required in (
        "pure grouping",
        "duplicate output",
        "UNKNOWN",
        "DEFERRED",
        "BLOCKED",
        "PIE-S2102",
        "PIE-S2301",
        "PIE-S2302",
        "no new code or message",
    ):
        assert required in contract, required


def test_project_json_public_exports_and_private_serialization_boundaries_are_locked() -> (
    None
):
    slice11_functions = set(
        _top_level_functions(
            REPO_ROOT
            / "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py"
        )
    )
    assert (
        "test_current_aggregate_grouped_private_facts_remain_unserialized_and_unexported"
        in slice11_functions
    )

    serializer = _read(REPO_ROOT / "src/pietto/_project/json_v2.py")
    key_positions = tuple(serializer.index(f'"{key}":') for key in PROJECT_JSON_V2_KEYS)
    assert key_positions == tuple(sorted(key_positions))
    assert all(token not in serializer for token in PRIVATE_SERIALIZATION_TOKENS)

    public_init = ast.parse(_read(REPO_ROOT / "src/pietto/__init__.py"))
    assert len(public_init.body) == 1
    assert isinstance(public_init.body[0], ast.Expr)
    for relative_path in (
        "src/pietto/_project/__init__.py",
        "src/pietto/_project/aggregate_grouped_clause_facts.py",
        "src/pietto/_project/aggregate_grouped_dependency_lineage.py",
        "src/pietto/_project/aggregate_grouped_persistence.py",
    ):
        assert "__all__" in _read(REPO_ROOT / relative_path)
        assert "= ()" in _read(REPO_ROOT / relative_path)

    contract = _normalized(SPEC_PATH)
    for required in (
        "Project JSON v2",
        "CLI JSON v1",
        "Semantic Metadata Artifact v1",
        "private and unserialized",
        "public Python API",
    ):
        assert required in contract, required


def test_deferred_owner_phase52_handoff_and_active_roadmap_reconciliation_are_locked() -> (
    None
):
    contract = _normalized(SPEC_PATH)
    for owner in DEFERRED_OWNERS:
        assert owner in contract, owner
    assert "Phase 52–60 remain UNSTARTED" in contract
    assert "Phase 52 Slice 1 Gate 0 and Gate 1" in contract

    roadmap = _read(ACTIVE_ROADMAP_PATH)
    marker = f"\n{ROADMAP_RECONCILIATION_HEADING}"
    assert roadmap.count(marker) == 1
    prefix, separator, reconciliation = roadmap.partition(marker)
    assert separator == marker
    assert hashlib.sha256(prefix.encode()).hexdigest() == ROADMAP_PREFIX_DIGEST
    assert "No reconciliation entries exist. This is the initial base route." in prefix
    reconciliation = " ".join(reconciliation.split())
    for required in (
        "previous entry is the initial base route",
        "5138d28ee2d0a258076a68a6f98c74ce15a93bf8",
        "29371109641",
        "old and new Phase 51 names, routes, exact 12-slice count, owners, and "
        "delivery classes are identical",
        "Owner additions, owner removals, and owner transfers are all none",
        "Before activation, Phase 51 remains ACTIVE and incomplete",
        "Activation requires the exact Slice 12 commit",
        "After and only after activation, Phase 51 is COMPLETED",
        "No deferral becomes anonymous",
        "Phase 52 Slice 1 Gate 0 and Gate 1",
    ):
        assert required in reconciliation, required


def test_live_compiler_project_private_protected_version_and_tag_locks_are_dirty_safe() -> (
    None
):
    compiler_count, compiler_digest = _compiler_digest()
    assert (compiler_count, compiler_digest) == (108, COMPILER_DIGEST)
    for relative_path in BOUNDARY_PATHS:
        boundary_values = re.findall(
            r'^BOUNDARY_HASH = "([0-9a-f]{64})"$',
            _read(REPO_ROOT / relative_path),
            flags=re.MULTILINE,
        )
        assert boundary_values == [COMPILER_DIGEST]

    project_paths = _project_private_paths()
    assert len(project_paths) == 33
    assert _digest(project_paths) == PROJECT_PRIVATE_DIGEST
    phase33 = _read(REPO_ROOT / "tests/test_phase33_completion_audit.py")
    assert (
        f'"project_private": (\n        "src/pietto/_project",\n'
        f'        33,\n        "{PROJECT_PRIVATE_DIGEST}",\n    ),'
    ) in phase33

    for relative_path, expected_hash in PROTECTED_HASHES.items():
        assert (
            hashlib.sha256((REPO_ROOT / relative_path).read_bytes()).hexdigest()
            == expected_hash
        )
    pyproject = tomllib.loads(_read(REPO_ROOT / "pyproject.toml"))
    project = pyproject["project"]
    assert isinstance(project, dict)
    assert project["version"] == "0.1.0"
    assert _git_output(["tag", "--points-at", "HEAD"]) == ""


def test_historical_allowlists_migrations_and_clean_only_guards_are_accounted() -> None:
    contract = _normalized(SPEC_PATH)
    for historical_entry in (
        "Slice 1, 4 paths",
        "Slice 2, 13 paths",
        "Slice 2 additive repair, 1 path",
        "Slice 3, 13 paths",
        "Slice 4, 14 paths",
        "Slice 5, 13 paths",
        "Slice 6, 15 paths",
        "Slice 7, 16 paths",
        "Slice 8, 13 paths",
        "Slice 9, 15 paths",
        "interpreter-integrity repair after Slice 9 changed exactly",
        "Slice 10, 38 paths",
        "Slice 10 static-lock repair, 1 path",
        "Slice 11, 20 paths",
    ):
        assert historical_entry in contract, historical_entry

    for relative_path, assignment_name, expected_count in HISTORICAL_ALLOWLIST_COUNTS:
        tree = ast.parse(_read(REPO_ROOT / relative_path), filename=relative_path)
        assignments = tuple(
            node
            for node in tree.body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == assignment_name
        )
        assert len(assignments) == 1
        value = assignments[0].value
        assert isinstance(value, ast.Set)
        assert len(value.elts) == expected_count

    migrations = (
        (
            "tests/test_phase47_downstream_readiness_hardening.py",
            "test_phase50_aggregate_projection_schema_" + "remains_absent",
            "test_aggregate_projection_schema_is_" + "concrete_with_persisted_fact",
        ),
        (
            "tests/test_phase48_upstream_non_concrete_schema_propagation.py",
            "test_computed_alias_concrete_while_aggregate_grouped_" + "stay_deferred",
            "test_computed_alias_and_aggregate_are_concrete_while_pure_"
            + "grouping_stays_deferred",
        ),
        (
            "tests/test_phase48_query_to_query_multi_hop_propagation.py",
            "test_computed_alias_concrete_but_let_aggregate_grouped_surfaces_"
            + "defer",
            "test_computed_alias_let_and_aggregate_are_concrete_while_pure_"
            + "grouping_stays_deferred",
        ),
        (
            "tests/test_phase49_computed_alias_project_row_schema_mvp.py",
            "test_unknown_null_division_and_aggregate_surfaces_remain_"
            + "non_concrete",
            "test_unknown_null_division_stay_non_concrete_while_aggregate_is_"
            + "concrete",
        ),
        (
            "tests/test_phase49_computed_alias_origin_provenance_privacy.py",
            "test_let_aggregate_and_grouped_outputs_remain_out_of_" + "scope",
            "test_let_and_aggregate_outputs_are_concrete_while_pure_grouping_"
            + "stays_deferred",
        ),
        (
            "tests/test_phase49_computed_let_multi_hop_row_lineage.py",
            "test_non_concrete_and_aggregate_grouped_lineage_remains_" + "empty",
            "test_non_concrete_lineage_is_empty_while_grouped_aggregate_"
            + "lineage_is_concrete",
        ),
        (
            "tests/test_phase49_let_visibility_order_shadowing_hardening.py",
            "test_project_grouped_selected_let_output_schema_remains_" + "deferred",
            "test_invalid_grouped_selected_let_output_schema_is_" + "unknown",
        ),
        (
            "tests/test_phase49_selected_let_derived_output_schema.py",
            "test_upstream_non_concrete_and_grouped_outputs_remain_" + "non_concrete",
            "test_unresolved_upstream_is_blocked_and_invalid_grouped_let_"
            + "output_is_unknown",
        ),
        (
            "tests/test_phase49_unknown_deferred_diagnostic_ordering_hardening.py",
            "test_grouped_aggregate_schema_remains_deferred_without_public_"
            + "diagnostics",
            "test_grouped_aggregate_schema_graph_and_lineage_are_concrete_"
            + "without_public_diagnostics",
        ),
        (
            "tests/test_phase51_private_result_role_output_identity.py",
            "test_aggregate_and_grouped_relations_remain_deferred_without_" + "facts",
            "test_aggregate_and_grouped_relations_are_concrete_with_persisted_"
            + "facts",
        ),
        (
            "tests/test_phase51_group_key_project_row_schema.py",
            "test_pure_and_mixed_grouped_production_states_remain_" + "deferred",
            "test_pure_grouping_stays_deferred_while_grouped_aggregate_is_"
            + "concrete",
        ),
        (
            "tests/test_phase51_aggregate_only_project_row_schema.py",
            "test_production_remains_deferred_unpersisted_private_and_"
            + "unserialized",
            "test_aggregate_and_grouped_outputs_are_persisted_private_and_"
            + "unserialized",
        ),
        (
            "tests/test_phase51_grouped_aggregate_project_row_schema.py",
            "test_production_remains_deferred_private_unpersisted_and_"
            + "unserialized",
            "test_aggregate_grouped_outputs_are_concrete_private_persisted_and_"
            + "unserialized",
        ),
        (
            "tests/test_phase51_selected_let_accepted_expression_aggregate.py",
            "test_expression_and_row_let_relations_remain_production_deferred_"
            + "private_and_unpersisted",
            "test_expression_and_row_let_aggregate_relations_are_concrete_"
            + "private_and_persisted",
        ),
        (
            "tests/test_phase51_aggregate_grouped_state_duplicate_hardening.py",
            "test_production_remains_deferred_unpersisted_private_and_"
            + "downstream_inactive",
            "test_aggregate_grouped_production_is_persisted_private_and_"
            + "downstream_active",
        ),
        (
            "tests/test_phase51_clause_dependency_fail_closed.py",
            "test_production_state_dependency_lineage_and_downstream_remain_"
            + "inactive",
            "test_aggregate_grouped_production_persists_graph_lineage_and_"
            + "activates_downstream",
        ),
        (
            "tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py",
            "test_production_state_dependency_lineage_and_downstream_remain_"
            + "inactive",
            "test_origin_dependency_lineage_production_is_persisted_and_"
            + "downstream_active",
        ),
    )
    assert len(migrations) == 17

    definitions_by_name: dict[str, list[str]] = {}
    for path in sorted((REPO_ROOT / "tests").rglob("*.py")):
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        for function_name in _top_level_functions(path):
            definitions_by_name.setdefault(function_name, []).append(relative_path)
    live_text_paths = tuple(
        path
        for root in (REPO_ROOT / "tests", REPO_ROOT / "docs")
        for path in root.rglob("*")
        if path.is_file() and path.suffix in {".py", ".md"}
    )
    for relative_path, old_name, new_name in migrations:
        target_names = _top_level_functions(REPO_ROOT / relative_path)
        assert old_name not in target_names
        assert target_names.count(new_name) == 1
        assert definitions_by_name.get(old_name, []) == []
        assert definitions_by_name.get(new_name) == [relative_path]
        assert all(old_name not in _read(path) for path in live_text_paths)

    assert len(CLEAN_ONLY_GUARDS) == 29
    for relative_path, function_name in CLEAN_ONLY_GUARDS:
        assert function_name in _top_level_functions(REPO_ROOT / relative_path)

    phase51_paths = tuple(
        REPO_ROOT / artifact[2] for artifact in PHASE51_SLICE_ARTIFACTS
    )
    assert _pytest_inventory((*phase51_paths, SELF_PATH)) == (165, 333)
    assert _top_level_functions(SELF_PATH) == (*EXPECTED_HELPERS, *EXPECTED_TESTS)


def test_completion_encoding_gate2_gate3_and_no_release_boundaries_are_locked() -> None:
    docs = " ".join(
        (
            _normalized(PLAN_PATH),
            _normalized(SPEC_PATH),
            _normalized(ACTIVE_ROADMAP_PATH),
        )
    )
    for required in (
        "conditional single-commit completion plus exact Gate 3 natural-CI evidence",
        "Phase 51 remains ACTIVE and incomplete",
        "Phase 52–60 remain UNSTARTED",
        "499 passed, 29 deselected",
        "5750 passed",
        "No post-CI repository status-flip commit is planned or required.",
        "Phase 52 Slice 1 Gate 0 and Gate 1",
        "Package version remains `0.1.0`.",
    ):
        assert required in docs, required
    for release_action in (
        "package-version change",
        "tag",
        "release",
        "publish",
        "upload",
        "signing",
        "attestation",
    ):
        assert release_action in _normalized(SPEC_PATH), release_action
    for forbidden in (
        "Slice 12 Gate 3 natural CI succeeded",
        "Slice 12 commit has been pushed",
        "Phase 51 is complete after Slice 12 Gate 2",
        "Phase 52 is ACTIVE",
    ):
        assert forbidden not in docs, forbidden


def test_static_git_helper_and_exact_slice12_dirty_set_are_locked() -> None:
    tree = ast.parse(_read(SELF_PATH), filename=SELF_PATH.as_posix())
    subprocess_calls = tuple(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "subprocess"
        and node.func.attr == "run"
    )
    assert len(subprocess_calls) == 1
    call = subprocess_calls[0]
    assert len(call.args) == 1
    command = call.args[0]
    assert isinstance(command, ast.List)
    assert len(command.elts) == 2
    first, second = command.elts
    assert isinstance(first, ast.Constant) and first.value == "git"
    assert isinstance(second, ast.Starred)
    assert isinstance(second.value, ast.Name) and second.value.id == "args"
    keywords = {keyword.arg: keyword.value for keyword in call.keywords}
    assert set(keywords) == {"cwd", "check", "text", "stdout", "stderr"}
    assert isinstance(keywords["cwd"], ast.Name)
    assert keywords["cwd"].id == "REPO_ROOT"
    for name in ("check", "text"):
        value = keywords[name]
        assert isinstance(value, ast.Constant) and value.value is True
    for name in ("stdout", "stderr"):
        value = keywords[name]
        assert isinstance(value, ast.Attribute)
        assert isinstance(value.value, ast.Name)
        assert value.value.id == "subprocess"
        assert value.attr == "PIPE"

    helper = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_git_output"
    )
    returns = tuple(node for node in ast.walk(helper) if isinstance(node, ast.Return))
    assert len(returns) == 1
    return_value = returns[0].value
    assert isinstance(return_value, ast.Call)
    assert isinstance(return_value.func, ast.Attribute)
    assert return_value.func.attr == "rstrip"
    assert return_value.args == []

    approved_git_calls = {
        ("status", "--short", "--untracked-files=all"),
        ("tag", "--points-at", "HEAD"),
        ("ls-files", "--others", "--exclude-standard"),
        ("diff", "--name-only"),
        ("diff", "--cached", "--name-status"),
        ("diff", "--check"),
        ("rev-parse", "HEAD"),
    }
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "_git_output":
            continue
        assert len(node.args) == 1
        argument = node.args[0]
        assert isinstance(argument, ast.List)
        values: list[str] = []
        for element in argument.elts:
            assert isinstance(element, ast.Constant)
            assert isinstance(element.value, str)
            values.append(element.value)
        assert tuple(values) in approved_git_calls

    slice2_tree = ast.parse(_read(REPO_ROOT / SLICE2_STATE_REL))
    slice2_sets = {
        node.targets[0].id: set(ast.literal_eval(node.value))
        for node in slice2_tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id
        in {
            "ADDED_PATHS",
            "NON_READER_MODIFIED_PATHS",
            "MECHANICAL_READER_PATHS",
        }
    }
    assert set(slice2_sets) == {
        "ADDED_PATHS",
        "NON_READER_MODIFIED_PATHS",
        "MECHANICAL_READER_PATHS",
    }
    slice2_modified = (
        slice2_sets["NON_READER_MODIFIED_PATHS"]
        | slice2_sets["MECHANICAL_READER_PATHS"]
    )
    slice2_added = slice2_sets["ADDED_PATHS"]
    dirty_paths = _dirty_paths()
    assert dirty_paths in (
        set(),
        SLICE12_GATE2_PATHS,
        PHASE52_GATE2_PATHS,
        slice2_modified | slice2_added,
        set(phase54_post_slice12_interlude_expected_allowlist_paths()),
        set(PHASE54_SLICE11_PR_CI_REPAIR_MODIFIED_PATHS),
        set(PHASE54_SLICE12_PR_CI_REPAIR_MODIFIED_PATHS),
        set(PHASE54_SLICE12_MECHANICAL_REPAIR4_MODIFIED_PATHS),
        set(PHASE54_SLICE12_MECHANICAL_REPAIR3_MODIFIED_PATHS),
        set(PHASE54_SLICE12_PRODUCT_REPAIR3_MODIFIED_PATHS),
        set(PHASE54_SLICE12_PRODUCT_REPAIR10_MODIFIED_PATHS),
        set(PHASE54_SLICE12_PRODUCT_REPAIR11_MODIFIED_PATHS),
        set(PHASE54_SLICE11_PYTHON313_REPAIR_MODIFIED_PATHS),
        set(PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_MODIFIED_PATHS),
    )
    untracked_paths = set(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    )
    assert untracked_paths in (
        set(),
        SLICE12_UNTRACKED_PATHS,
        PHASE52_UNTRACKED_PATHS,
        slice2_added,
        set(phase54_post_slice12_interlude_expected_added_paths()),
    )
    if dirty_paths == set(PHASE54_SLICE11_PYTHON313_REPAIR_MODIFIED_PATHS):
        assert phase54_slice11_python313_repair_is_active()
        assert untracked_paths == set()
    elif dirty_paths == set(PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_MODIFIED_PATHS):
        assert phase54_slice11_substantive_recovery_is_active()
    elif dirty_paths == set(PHASE54_SLICE12_PR_CI_REPAIR_MODIFIED_PATHS):
        assert phase54_slice12_pr_ci_repair_is_active()
        assert untracked_paths == set()
    elif dirty_paths == set(PHASE54_SLICE12_MECHANICAL_REPAIR4_MODIFIED_PATHS):
        assert phase54_slice12_mechanical_repair4_is_active()
        assert untracked_paths == set()
    elif dirty_paths == set(PHASE54_SLICE12_MECHANICAL_REPAIR3_MODIFIED_PATHS):
        assert phase54_slice12_mechanical_repair3_is_active()
        assert untracked_paths == set()
    elif dirty_paths == set(PHASE54_SLICE12_PRODUCT_REPAIR3_MODIFIED_PATHS):
        assert phase54_slice12_product_repair3_is_active()
        assert untracked_paths == set()
    elif dirty_paths == set(PHASE54_SLICE12_PRODUCT_REPAIR10_MODIFIED_PATHS):
        assert phase54_slice12_product_repair10_is_active()
        assert untracked_paths == set()
    elif dirty_paths == set(PHASE54_SLICE12_PRODUCT_REPAIR11_MODIFIED_PATHS):
        assert phase54_slice12_product_repair11_is_active()
        assert untracked_paths == set()
    elif dirty_paths == set(PHASE54_SLICE11_PR_CI_REPAIR_MODIFIED_PATHS):
        assert phase54_slice11_pr_ci_repair_is_active()
        assert untracked_paths == set()
    elif dirty_paths == slice2_modified | slice2_added:
        assert untracked_paths == slice2_added
        assert set(_git_output(["diff", "--name-only"]).splitlines()) == (
            slice2_modified
        )
        path_counts = (
            len(slice2_modified),
            len(slice2_added),
            len(slice2_modified | slice2_added),
        )
        expected_head = SLICE2_BASE_HEAD_SHA
        if path_counts == SLICE4_PATH_COUNTS:
            expected_head = SLICE4_BASE_HEAD_SHA
        elif path_counts == SLICE5_PATH_COUNTS:
            expected_head = SLICE5_BASE_HEAD_SHA
        elif path_counts == SLICE6_PATH_COUNTS:
            expected_head = SLICE6_BASE_HEAD_SHA
        elif path_counts == SLICE7_PATH_COUNTS:
            expected_head = SLICE7_BASE_HEAD_SHA
        elif path_counts == SLICE8_PATH_COUNTS:
            expected_head = SLICE8_BASE_HEAD_SHA
        elif path_counts == SLICE9_PATH_COUNTS:
            expected_head = SLICE9_BASE_HEAD_SHA
        if _phase54_active_gate2_is_active():
            active_head = _git_output(["rev-parse", "HEAD"])
            assert active_head in {
                "b81843acadb294630db361c09949868d004b1bca",
                "bc46faff1c9aa71f583ed7d2964b651cc659bc90",
                "0bad854253e22347e2aff93e2eabcbe2fda55aed",
                "040ab19c56519c39c56541979c850484f9cc47f0",
                "93f0f591e28a01f32d1698fcd4b8c57d41c6d714",
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
            expected_head = active_head
        assert _git_output(["rev-parse", "HEAD"]) == expected_head
    assert _git_output(["diff", "--cached", "--name-status"]) == ""
    assert _git_output(["diff", "--check"]) == ""


_SLICE10_READER_MIGRATION_PATHS = (
    "docs/spec/phase53-partition-binding-multi-key-visibility-diagnostics-contract-v1.md",
    "src/pietto/semantic/window_partition_analysis.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
)
# Phase 53 Slice 13 reader migration.
