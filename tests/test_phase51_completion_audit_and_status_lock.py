from __future__ import annotations

import ast
import hashlib
import inspect
import tomllib
from dataclasses import fields
from pathlib import Path

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
        "56339c3e565471c3a95a0f79a05eaf9596d734a173d1936d5df167526508ddac"
    ),
    ".python-version": (
        "7b55f8e67b5623c4bef3fa691288da9437d79d3aba156de48d481db32ac7d16d"
    ),
    "pyproject.toml": (
        "851e706f2cbafb24c48068cdd6fd8a6ada1f93317618000be71db3681c40a1a8"
    ),
    "uv.lock": "12795f072df20fb688b37e484dd4561cd33e34bf601be3cb0fa1f9075eee38a2",
    "docs/spec/pietto-roadmap-phase45-60-v1.md": (
        "26cc0ae4a68518223d6bf600ad3c4b0b226618aa7ef31b2ae1c25924d2655169"
    ),
}
COMPILER_DIGEST = "6cbe7ccfbd84d7b2966964ac91a56e7eeacdc798c3d161da64d61add662b0420"
PROJECT_PRIVATE_DIGEST = (
    "327ba4f5c12d916d6577cd9510aa2a28df8519dafdc935ae67a6d2f5b2fc4830"
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


def test_package_version_remains_current() -> None:
    project = tomllib.loads(_read(REPO_ROOT / "pyproject.toml"))["project"]
    assert isinstance(project, dict)
    assert project["version"] == "0.1.0"


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
