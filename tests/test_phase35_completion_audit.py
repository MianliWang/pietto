from __future__ import annotations

# Phase 54 Slice 4 mechanical reader-closure identity refresh.

import tomllib
from pathlib import Path

from _static_audit_helpers import (
    git_diff_name_only as _git_diff_name_only,
    normalized_text as _normalized,
    read_text as _read,
)
from test_phase39_candidate_decision import (
    _non_slice3_repair_diff_paths,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
PIETTO_SPEC_PATH = REPO_ROOT / "docs/spec/pietto-v0.9.md"
PHASE35_PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-35-developer-experience-and-delivery-pipeline.md"
)
PHASE35_SAFE_SIMPLIFICATION_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase-35-safe-simplification-contract-v1.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

STATUS_DOCS = (AGENTS_PATH, PIETTO_SPEC_PATH)
PHASE35_DOCS = (*STATUS_DOCS, PHASE35_PLAN_PATH)

OFFICIAL_PHASE35_TITLE = "Developer Experience And Delivery Pipeline MVP"
UNAPPROVED_PHASE35_TITLE = (
    "Developer Experience, Delivery Pipeline, And Safe Simplification MVP"
)
PHASE35_COMPLETION_STATEMENT = (
    "Phase 35 Developer Experience And Delivery Pipeline MVP is complete"
)
SLICE1_LOCK = "cd6a727989f3ba47ea9e7dcd7c04b6a2a7cb1071"
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
PHASE35_ARTIFACTS = (
    "docs/plan/phase-35-developer-experience-and-delivery-pipeline.md",
    "docs/spec/phase-35-safe-simplification-contract-v1.md",
    "tests/_static_audit_helpers.py",
    "tests/test_phase35_safe_simplification_candidate_decision.py",
    "tests/test_phase35_status_housekeeping.py",
    "tests/test_phase35_static_audit_helper_simplification.py",
    "tests/test_phase35_validation_delivery_workflow_polish.py",
    "tests/test_phase35_internal_helper_simplification_candidate_decision.py",
    "tests/test_phase35_completion_audit.py",
)
FORBIDDEN_DIFF_PATHS = (
    "docs/spec/phase-35-safe-simplification-contract-v1.md",
    "tests/_static_audit_helpers.py",
    "tests/test_phase35_safe_simplification_candidate_decision.py",
    "tests/test_phase35_static_audit_helper_simplification.py",
    "grammar/Pietto.g4",
    "src/pietto/generated",
    "src/pietto/ast_nodes.py",
    "src/pietto/ast_builder.py",
    "src/pietto/parser_api.py",
    "src/pietto/semantic",
    "src/pietto/ir",
    "src/pietto/sql",
    "src/pietto/cli.py",
    "src/pietto/cli_json.py",
    "src/pietto/_project",
    "src/pietto/_metadata",
    "src/pietto/metadata",
    "tests/fixtures",
    "tests/goldens",
    "scripts",
    ".github/workflows/ci.yml",
    "pyproject.toml",
    "uv.lock",
)


def test_phase35_completion_artifact_inventory_and_title_are_locked() -> None:
    plan = _normalized(PHASE35_PLAN_PATH)

    for relative_path in PHASE35_ARTIFACTS:
        assert (REPO_ROOT / relative_path).is_file(), relative_path

    assert OFFICIAL_PHASE35_TITLE in plan
    assert UNAPPROVED_PHASE35_TITLE not in plan
    for required in (
        "Phase 35 Slice 1 Candidate Decision, Inventory, And Safe "
        "Simplification Scope is complete",
        "Phase 35 Slice 2 Status Housekeeping is complete",
        "Phase 35 Slice 3 Static Audit Helper Simplification is complete",
        "Phase 35 Slice 4 Validation And Delivery Workflow Polish is complete",
        "Phase 35 Slice 5 Internal Helper Simplification Candidate Decision is complete",
        "Phase 35 Slice 6 Completion Audit And Status Lock is complete",
        PHASE35_COMPLETION_STATEMENT,
        SLICE1_LOCK,
    ):
        assert required in plan, required


def test_global_status_docs_record_phase35_completion() -> None:
    for path in STATUS_DOCS:
        status = _normalized(path)

        assert PHASE35_COMPLETION_STATEMENT in status, str(path)
        assert (
            "Phase 35 is active as Developer Experience And Delivery Pipeline MVP"
            not in (status)
        )
        assert f"Phase 35 Slice 1 remains complete at `{SLICE1_LOCK}`" in status
        assert "Slices 2 through 6 complete status housekeeping" in status
        assert "tests-only static-audit helper simplification" in status
        assert "validation/delivery workflow polish" in status
        assert "internal helper simplification candidate deferral" in status
        assert "completion audit/status lock work" in status
        assert "Safe Simplification remains a scoped discipline" in status
        assert "not a roadmap title change" in status
        assert "not source-refactor authorization" in status
        assert "Package version remains `0.1.0`" in status
        assert "No tag/release/publish/upload/signing/attestation occurred" in status


def test_phase35_completion_preserves_no_behavior_change_boundaries() -> None:
    combined = " ".join(_normalized(path) for path in PHASE35_DOCS)

    for required in (
        "no source/compiler behavior",
        "parser/AST behavior",
        "semantic behavior",
        "IR/SQL behavior",
        "CLI behavior",
        "JSON v1",
        "Project JSON v2",
        "Semantic Metadata Artifact v1",
        "JOIN/grain behavior",
        "project source selection",
        "multi-file semantic behavior",
        "runtime/database behavior",
        "schema introspection",
        "graph/ERD/AI export",
        "fixture/golden/script/workflow/package metadata/lockfile/dependency",
        "package version",
        "release-operation behavior",
    ):
        assert required in combined, required


def test_phase35_forbidden_surfaces_are_not_modified() -> None:
    diff_output = _git_diff_name_only(REPO_ROOT, FORBIDDEN_DIFF_PATHS)

    assert _non_slice3_repair_diff_paths(diff_output) == set()


def test_package_version_and_release_boundaries_remain_locked() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]
    combined = " ".join(_normalized(path) for path in PHASE35_DOCS)

    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert 'version = "0.2.0"' not in _read(PYPROJECT_PATH)
    assert "Package version remains `0.1.0`" in combined
    assert "No tag/release/publish/upload/signing/attestation occurred" in combined
    assert "attestation is performed by Slice 6" in combined

    lowered = combined.lower()
    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in lowered, forbidden
