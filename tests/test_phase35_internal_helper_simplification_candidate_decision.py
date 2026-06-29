from __future__ import annotations

import tomllib
from pathlib import Path

from _static_audit_helpers import (
    git_diff_name_only as _git_diff_name_only,
    normalized_text as _normalized,
    read_text as _read,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE35_PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-35-developer-experience-and-delivery-pipeline.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

OFFICIAL_PHASE35_TITLE = "Developer Experience And Delivery Pipeline MVP"
UNAPPROVED_PHASE35_TITLE = (
    "Developer Experience, Delivery Pipeline, And Safe Simplification MVP"
)
FORBIDDEN_DIFF_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    "docs/spec/phase-35-safe-simplification-contract-v1.md",
    "tests/_static_audit_helpers.py",
    "tests/test_phase35_safe_simplification_candidate_decision.py",
    "tests/test_phase35_static_audit_helper_simplification.py",
    "tests/test_phase35_validation_delivery_workflow_polish.py",
    "src/pietto/cli.py",
    "src/pietto/cli_json.py",
    "src/pietto/_project",
    "src/pietto/_metadata",
    "src/pietto/metadata",
    "src/pietto/sql",
    "src/pietto/semantic",
    "grammar/Pietto.g4",
    "src/pietto/generated",
    "tests/fixtures",
    "tests/goldens",
    "scripts",
    ".github/workflows/ci.yml",
    "pyproject.toml",
    "uv.lock",
)
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


def test_phase35_title_and_slice5_deferral_decision_are_locked() -> None:
    plan = _normalized(PHASE35_PLAN_PATH)

    assert OFFICIAL_PHASE35_TITLE in plan
    assert UNAPPROVED_PHASE35_TITLE not in plan
    for required in (
        "Phase 35 Slice 5 Internal Helper Simplification Candidate Decision is "
        "the current docs/static-audit-only candidate-decision and "
        "source-refactor deferral slice",
        "Phase 35 Slice 5 Internal Helper Simplification Candidate Decision is "
        "docs/static-audit candidate-decision work only",
        "Slice 5 investigated internal helper simplification candidates",
        "selects no production/internal helper extraction for Phase 35 Slice 5",
        "defer source refactor because all concrete candidates are behavior-adjacent",
    ):
        assert required in plan, required


def test_behavior_adjacent_internal_helper_candidates_are_deferred() -> None:
    plan = _normalized(PHASE35_PLAN_PATH)

    for required in (
        "CLI pipeline helper extraction is deferred because it can affect "
        "stdout/stderr, exit codes, JSON envelopes, diagnostics, and "
        "output-write safety",
        "JSON helper extraction is deferred because it can affect JSON v1, "
        "Project JSON v2, and Semantic Metadata Artifact v1 byte contracts",
        "SQL renderer helper extraction is deferred because it can affect SQL "
        "bytes and backend fail-closed `PIE-B1000` behavior",
        "Semantic helper extraction is deferred because it can affect "
        "accepted/rejected programs and diagnostic code/message/order/span",
        "Metadata builder/serializer/text helper extraction is deferred because "
        "it can affect Semantic Metadata Artifact v1 JSON/text output and "
        "source-location semantics",
    ):
        assert required in plan, required


def test_slice5_records_unchanged_forbidden_behavior_and_release_boundaries() -> None:
    plan = _normalized(PHASE35_PLAN_PATH)

    for required in (
        "Source/compiler behavior, CLI behavior, JSON behavior, SQL behavior, "
        "diagnostics, fixtures, goldens, scripts, workflows, package metadata, "
        "lockfiles, release, tag, publish, upload, signing, and attestation all "
        "remain unchanged",
        "Package version remains `0.1.0`",
        "attestation is performed by Slice 5",
    ):
        assert required in plan, required

    lowered = plan.lower()
    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in lowered, forbidden


def test_slice5_forbidden_surfaces_are_not_modified() -> None:
    diff_output = _git_diff_name_only(REPO_ROOT, FORBIDDEN_DIFF_PATHS)

    assert diff_output == ""


def test_package_version_remains_010() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]

    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert 'version = "0.2.0"' not in _read(PYPROJECT_PATH)
