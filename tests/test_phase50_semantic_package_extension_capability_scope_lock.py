from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path
from typing import cast

from _static_audit_helpers import normalized_text as _normalized
from _static_audit_helpers import read_text as _read

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-50-semantic-readiness-consolidation.md"
ROADMAP_PATH = REPO_ROOT / "docs/spec/pietto-roadmap-phase45-60-v1.md"
SPEC_PATH = (
    REPO_ROOT
    / "docs/spec/phase50-semantic-package-extension-capability-scope-lock-v1.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

HISTORICAL_PHASE50_ROW = "| 50 | Import / Module / Export Readiness |"
HISTORICAL_PHASE60_ROW = "| 60 | Completion Audit And Status Lock |"
PHASE50_TITLE = "Post-v0.2 Semantic Readiness Consolidation"
SLICE1_TITLE = "Roadmap Reconciliation And Strategic Scope Lock"

PHASE50_SLICE_NAMES = (
    "Roadmap Reconciliation And Strategic Scope Lock",
    "Post-v0.2 Deferred Inventory And Phase 50-60 Replan",
    "Aggregate / Grouped Project Output-Schema Readiness",
    "Type-System Gap And Capability Readiness",
    "Window-Function Readiness",
    "Import / Module / Export Readiness",
    "Semantic Package Model Readiness",
    "PostgreSQL Extension Capability Readiness",
    "Multi-dialect Capability Ecosystem Readiness",
    "Explain / Public Metadata / Package Integration Boundary",
    "Completion Audit And Status Lock",
)

TENTATIVE_PHASE51_60_TITLES = (
    "Phase 51: Aggregate / Grouped Project Output-Schema Foundation",
    "Phase 52: Core Type-System Capability Foundation",
    "Phase 53: Window Function Syntax And Capability Contract",
    "Phase 54: Import / Module / Export Readiness",
    "Phase 55: Semantic Package Asset Schema",
    "Phase 56: Capability Profile Static Schema And Declared Checking",
    "Phase 57: PostgreSQL Extension Signature-Catalog Readiness",
    "Phase 58: Project Explain / Portability / Public Metadata Readiness",
    "Phase 59: Package Graph And Lineage / Provenance Integration",
    "Phase 60: Multi-dialect Capability Ecosystem Completion Checkpoint",
)

ALLOWED_PHASE50_SLICE1_GATE2_PATHS = {
    "docs/plan/phase-50-semantic-readiness-consolidation.md",
    "docs/spec/pietto-roadmap-phase45-60-v1.md",
    "docs/spec/phase50-semantic-package-extension-capability-scope-lock-v1.md",
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
}

ALLOWED_PHASE50_SLICE2_REPAIR_GATE2_PATHS = {
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
}

ALLOWED_PHASE50_SLICE3_GATE2_PATHS = {
    "docs/plan/phase-50-semantic-readiness-consolidation.md",
    "docs/spec/phase50-aggregate-grouped-project-output-schema-readiness-v1.md",
    "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
}

ALLOWED_PHASE50_SLICE4_GATE2_PATHS = {
    "docs/plan/phase-50-semantic-readiness-consolidation.md",
    "docs/spec/phase50-type-system-gap-capability-readiness-v1.md",
    "tests/test_phase50_type_system_gap_capability_readiness.py",
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
    "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
}

ALLOWED_PHASE50_SLICE5_GATE2_PATHS = {
    "docs/plan/phase-50-semantic-readiness-consolidation.md",
    "docs/spec/phase50-window-function-readiness-v1.md",
    "tests/test_phase50_window_function_readiness.py",
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
    "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
    "tests/test_phase50_type_system_gap_capability_readiness.py",
}

ALLOWED_PHASE50_SLICE6_GATE2_PATHS = {
    "docs/plan/phase-50-semantic-readiness-consolidation.md",
    "docs/spec/phase50-import-module-export-readiness-v1.md",
    "tests/test_phase50_import_module_export_readiness.py",
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
    "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
    "tests/test_phase50_type_system_gap_capability_readiness.py",
    "tests/test_phase50_window_function_readiness.py",
}

ALLOWED_PHASE50_SLICE7_GATE2_PATHS = {
    "docs/plan/phase-50-semantic-readiness-consolidation.md",
    "docs/spec/phase50-semantic-package-model-readiness-v1.md",
    "tests/test_phase50_semantic_package_model_readiness.py",
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
    "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
    "tests/test_phase50_type_system_gap_capability_readiness.py",
    "tests/test_phase50_window_function_readiness.py",
    "tests/test_phase50_import_module_export_readiness.py",
}

ALLOWED_PHASE50_SLICE8_GATE2_PATHS = {
    "docs/plan/phase-50-semantic-readiness-consolidation.md",
    "docs/spec/phase50-postgresql-extension-capability-readiness-v1.md",
    "tests/test_phase50_postgresql_extension_capability_readiness.py",
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
    "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
    "tests/test_phase50_type_system_gap_capability_readiness.py",
    "tests/test_phase50_window_function_readiness.py",
    "tests/test_phase50_import_module_export_readiness.py",
    "tests/test_phase50_semantic_package_model_readiness.py",
}

ALLOWED_PHASE50_SLICE9_GATE2_PATHS = {
    "docs/plan/phase-50-semantic-readiness-consolidation.md",
    "docs/spec/phase50-multi-dialect-capability-ecosystem-readiness-v1.md",
    "tests/test_phase50_multi_dialect_capability_ecosystem_readiness.py",
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
    "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
    "tests/test_phase50_type_system_gap_capability_readiness.py",
    "tests/test_phase50_window_function_readiness.py",
    "tests/test_phase50_import_module_export_readiness.py",
    "tests/test_phase50_semantic_package_model_readiness.py",
    "tests/test_phase50_postgresql_extension_capability_readiness.py",
}

ALLOWED_PHASE50_SLICE10_GATE2_PATHS = {
    "docs/plan/phase-50-semantic-readiness-consolidation.md",
    "docs/spec/phase50-explain-public-metadata-package-integration-boundary-v1.md",
    "tests/test_phase50_explain_public_metadata_package_integration_boundary.py",
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
    "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
    "tests/test_phase50_type_system_gap_capability_readiness.py",
    "tests/test_phase50_window_function_readiness.py",
    "tests/test_phase50_import_module_export_readiness.py",
    "tests/test_phase50_semantic_package_model_readiness.py",
    "tests/test_phase50_postgresql_extension_capability_readiness.py",
    "tests/test_phase50_multi_dialect_capability_ecosystem_readiness.py",
}

ALLOWED_PHASE50_SLICE11_GATE2_PATHS = {
    "docs/plan/phase-50-semantic-readiness-consolidation.md",
    "docs/spec/phase50-completion-audit-and-status-lock-v1.md",
    "tests/test_phase50_completion_audit_and_status_lock.py",
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
    "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
    "tests/test_phase50_type_system_gap_capability_readiness.py",
    "tests/test_phase50_window_function_readiness.py",
    "tests/test_phase50_import_module_export_readiness.py",
    "tests/test_phase50_semantic_package_model_readiness.py",
    "tests/test_phase50_postgresql_extension_capability_readiness.py",
    "tests/test_phase50_multi_dialect_capability_ecosystem_readiness.py",
    "tests/test_phase50_explain_public_metadata_package_integration_boundary.py",
}

PROTECTED_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    "docs/spec/v02-deferred-feature-register-v1.md",
    "src",
    "grammar",
    "scripts",
    ".github",
    "pyproject.toml",
    "uv.lock",
    "tests/fixtures",
    "tests/goldens",
)


def _documents() -> tuple[str, str, str]:
    return (_normalized(PLAN_PATH), _normalized(ROADMAP_PATH), _normalized(SPEC_PATH))


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
    output = _git_output(["status", "--porcelain", "--untracked-files=all"])
    paths: set[str] = set()
    for line in output.splitlines():
        if not line:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", maxsplit=1)[1]
        paths.add(path)
    return paths


def test_plan_roadmap_and_scope_spec_exist_and_lock_slice1_identity() -> None:
    assert PLAN_PATH.is_file()
    assert ROADMAP_PATH.is_file()
    assert SPEC_PATH.is_file()

    plan, roadmap, spec = _documents()
    assert f"# Phase 50 - {PHASE50_TITLE}" in _read(PLAN_PATH)
    assert PHASE50_TITLE in plan
    assert PHASE50_TITLE in roadmap
    assert PHASE50_TITLE in spec
    assert SLICE1_TITLE in plan
    assert SLICE1_TITLE in roadmap
    assert SLICE1_TITLE in spec

    for document in (plan, roadmap, spec):
        assert "docs/spec/static-audit-only" in document
        assert "typed SQL authoring DSL and semantic compiler" in document

    assert "Slice 1 implements no compiler or runtime behavior." in _read(SPEC_PATH)


def test_post_maintenance_baseline_is_locked() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "6d898559aaa244f3e4643488c111480e6933761b",
        "Complete Maintenance Phase 4 worker benchmark audit",
        "29059542913",
        "CI / push",
        "completed / success",
        "headSha",
        "0.1.0",
        "no tag at HEAD",
        "no exact-match tag",
    ):
        assert required in spec, required


def test_historical_rows_and_append_only_reconciliation_are_locked() -> None:
    roadmap = _read(ROADMAP_PATH)
    reconciliation_heading = "## Post-maintenance Phase 50 Reconciliation"

    assert roadmap.count(HISTORICAL_PHASE50_ROW) == 1
    assert roadmap.count(HISTORICAL_PHASE60_ROW) == 1
    assert roadmap.count(reconciliation_heading) == 1
    assert roadmap.index(HISTORICAL_PHASE50_ROW) < roadmap.index(reconciliation_heading)
    assert roadmap.index(HISTORICAL_PHASE60_ROW) < roadmap.index(reconciliation_heading)

    normalized = _normalized(ROADMAP_PATH)
    for required in (
        "Historical Maintenance Phase 2 Snapshot",
        "retained as evidence",
        "not deleted",
        "retroactively rewritten",
        "Current Phase 50 Readiness-Consolidation Route",
        "Current Slice 1 Purpose",
        "Eleven-slice Phase 50 Plan",
        "Tentative Phase 51-60 Active Planning Route",
        "Strategic Vocabulary And Safety Boundary",
        "project explain/public metadata",
        "not automatic behavior authorization",
    ):
        assert required in normalized, required


def test_exact_eleven_slice_route_is_present_once_and_in_order() -> None:
    plan = _read(PLAN_PATH)
    route = plan.split("## Eleven-slice Route", maxsplit=1)[1].split(
        "## Cross-slice Gate Discipline", maxsplit=1
    )[0]

    offsets: list[int] = []
    for slice_name in PHASE50_SLICE_NAMES:
        assert route.count(slice_name) == 1, slice_name
        offsets.append(route.index(slice_name))
    assert offsets == sorted(offsets)


def test_slice1_historical_scope_and_later_authorization_are_locked() -> None:
    plan, roadmap, spec = _documents()
    historical_roadmap = roadmap.split(
        "Slice 2 Finalized Phase 51-60 Active Planning Route", maxsplit=1
    )[0]
    historical_slice1_docs = f"{historical_roadmap} {spec}"

    for required in (
        "only the entry documentation slice",
        "Slice 1 is the only current documentation slice",
        "Slices 2 through 11 remain pending",
        "separately authorized",
        "No listed slice automatically authorizes later implementation",
        "Listing Slices 2 through 11 does not start or complete them",
    ):
        assert required in historical_slice1_docs, required

    for current_status in (
        f"Phase 50 Slice 1 **{SLICE1_TITLE}** completed",
        "Phase 50 Slice 2 **Post-v0.2 Deferred Inventory And Phase 50-60 Replan** "
        "completed",
        "Phase 50 Slice 3 **Aggregate / Grouped Project Output-Schema Readiness** "
        "completed",
        "Phase 50 Slice 4 **Type-System Gap And Capability Readiness** completed",
        "aaf30fcd2ec4b19f6d0c23783067c369a11cd27b",
        "29097916311",
        "Phase 50 Slice 5 **Window-Function Readiness** completed",
        "d79c5c422cb7f54ae5e5587694e49389536419cb",
        "29115612846",
        "Phase 50 Slice 6 **Import / Module / Export Readiness** completed",
        "7c7f6976dd67ccc4628757f2d857b593f71f5e0f",
        "29139545163",
        "Phase 50 Slice 7 **Semantic Package Model Readiness** completed",
        "a5bc07855a0994343475ba546504e64b16fc7e63",
        "29141663534",
        "Phase 50 Slice 8 **PostgreSQL Extension Capability Readiness** completed",
        "9e2c0f0ddcc2047e35985e6b97daa8bf29979914",
        "29157374991",
        "Slice 8 completed",
        "Phase 50 Slice 9 **Multi-dialect Capability Ecosystem Readiness** completed",
        "f886589ac2f64eeb3770c914e7c049e2da105daa",
        "29170827348",
        "Phase 50 Slice 10 **Explain / Public Metadata / Package Integration Boundary** "
        "completed",
        "9bc6ed82f3741e3c242981bb88edfb50c73fc586",
        "29179160024",
        "Phase 50 Slice 11 **Completion Audit And Status Lock** is the current",
        "Slice 11 is not complete in Gate 2",
        "Phase 50 remains in progress through Gate 2",
        "Phases 51 through 60 remain unstarted and separately authorized",
        "Phase 53 remains `READINESS_CONTRACT_ONLY`",
        "Phase 54 remains readiness-only and unstarted",
        "Phase 55 remains `READINESS_CONTRACT_ONLY`, readiness-only, and unstarted",
        "Phase 56 remains unstarted",
        "Phase 57 remains `READINESS_CONTRACT_ONLY`, readiness-only, and unstarted",
        "Phase 58 remains readiness-only and unstarted",
        "Phase 60 remains readiness-only and unstarted",
    ):
        assert current_status in plan, current_status

    docs = " ".join((plan, roadmap, spec))

    for forbidden_completion_claim in (
        "Phase 50 is complete after Slice 11 Gate 2",
        "Slices 2 through 11 are complete",
        "Slice 11 is complete",
    ):
        assert forbidden_completion_claim not in docs, forbidden_completion_claim


def test_tentative_phase51_60_route_and_slice2_authority_are_locked() -> None:
    plan = _normalized(PLAN_PATH)
    roadmap = _normalized(ROADMAP_PATH)

    for title in TENTATIVE_PHASE51_60_TITLES:
        assert title in plan, title
        assert title in roadmap, title

    for document in (plan, roadmap):
        for required in (
            "tentative",
            "Slice 2",
            "post-v0.2 deferred inventory",
            "not automatic behavior authorization",
        ):
            assert required in document, required
        assert (
            "finalizes active ordering" in document
            or "finalized active ordering" in document
        )


def test_readiness_ownership_is_complete_without_behavior() -> None:
    docs = " ".join(_documents())

    for required in PHASE50_SLICE_NAMES[2:10]:
        assert required in docs, required

    for required in (
        "Phase 51: Aggregate / Grouped Project Output-Schema Foundation",
        "Phase 57: PostgreSQL Extension Signature-Catalog Readiness",
        "Every Phase 50 slice is readiness-only",
        "No Phase 50 slice authorizes runtime/database execution",
    ):
        assert required in docs, required


def test_static_semantic_package_and_capability_vocabulary_is_locked() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "static, declarative, reviewable bundle of semantic assets",
        "A dialect is a SQL syntax/lowering family",
        "A capability profile is a static declaration of the semantic abilities",
        "An extension profile is a static declared overlay on a base capability profile",
        "PostgreSQL extension capability profile",
        "missing or undeclared capability must fail closed",
        "no best-effort lowering",
        "PostGIS",
        "pgvector",
        "pg_trgm",
        "TimescaleDB",
        "future catalog examples only",
    ):
        assert required in spec, required


def test_phase49_private_carriers_remain_private_and_unconsumed() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "Phase 49 private row schemas",
        "origin/provenance",
        "dependency graphs",
        "multi-hop lineage",
        "does not expose, serialize, rename, widen, or consume",
        "changes neither Project JSON v2 nor public lineage",
        "No private row schema",
        "becomes public",
    ):
        assert required in spec, required


def test_explicit_non_goals_and_runtime_phrase_are_locked() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "runtime behavior",
        "no package manifest",
        "resolver",
        "dependency solver",
        "package graph",
        "catalog",
        "signature schema",
        "lowering",
        "diagnostic",
        "public schema",
        "CLI surface",
        "JSON surface",
        "no runtime package installation",
        "no registry access",
        "no arbitrary package code execution",
        "no plugins",
        "no hooks",
        "no `CREATE EXTENSION`",
        "no database connection",
        "no extension discovery",
        "no database introspection",
        "no schema introspection",
        "no network access",
        "no SQL execution",
        "no package version bump, tag, release, publish, upload, signing, or attestation",
    ):
        assert required in spec, required


def test_protected_surfaces_have_no_diff() -> None:
    for relative_path in PROTECTED_PATHS:
        assert _git_output(["diff", "--", relative_path]) == "", relative_path


def test_package_version_tag_and_dirty_paths_are_locked() -> None:
    pyproject = tomllib.loads(_read(PYPROJECT_PATH))
    project = cast(dict[str, object], pyproject["project"])

    assert project["version"] == "0.1.0"
    assert _git_output(["tag", "--points-at", "HEAD"]) == ""
    assert _dirty_paths() in (
        set(),
        ALLOWED_PHASE50_SLICE1_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE2_REPAIR_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE3_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE4_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE5_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE6_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE7_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE8_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE9_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE10_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE11_GATE2_PATHS,
    )
