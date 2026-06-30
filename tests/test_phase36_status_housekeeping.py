from __future__ import annotations

import tomllib
from pathlib import Path

from _static_audit_helpers import (
    git_diff_name_only as _git_diff_name_only,
    normalized_text as _normalized,
    read_text as _read,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
README_PATH = REPO_ROOT / "README.md"
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
PIETTO_SPEC_PATH = REPO_ROOT / "docs/spec/pietto-v0.9.md"
PHASE36_PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-36-post-v02-core-type-system-expansion.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

STATUS_DOCS = (README_PATH, AGENTS_PATH, PIETTO_SPEC_PATH)

FORBIDDEN_DIFF_PATHS = (
    "grammar/Pietto.g4",
    "src/pietto/generated",
    "src/pietto/cli.py",
    "src/pietto/cli_json.py",
    "src/pietto/semantic",
    "src/pietto/ir",
    "src/pietto/sql",
    "src/pietto/_metadata",
    "src/pietto/_project",
    "tests/fixtures",
    "pyproject.toml",
    "uv.lock",
    ".github",
    "scripts",
    "examples",
)

POSITIVE_PHASE36_COMPLETION_CLAIMS = (
    "Phase 36 is complete.",
    "Phase 36 complete.",
    "Phase 36 Post-v0.2 Core Type System Expansion MVP is complete",
    "Phase 36 is fully complete",
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


def _status(path: Path) -> str:
    return _normalized(path)


def test_status_docs_record_phase36_through_slice10_not_final_completion() -> None:
    for path in STATUS_DOCS:
        status = _status(path)

        assert "Phase 36 Slices 1 through 10 are complete" in status, str(path)
        assert "Phase 36 remains in progress" in status, str(path)
        assert "Slice 12 remains the final completion audit/status lock" in status, str(
            path
        )
        for forbidden in POSITIVE_PHASE36_COMPLETION_CLAIMS:
            assert forbidden not in status, f"{path}: {forbidden}"


def test_status_docs_identify_slice5_as_only_phase36_behavior_change() -> None:
    for path in STATUS_DOCS:
        status = _status(path)

        assert "Slice 5 is the only Phase 36 behavior change so far" in status
        assert "`count(Enum field)`" in status
        assert "`PIE-S2314`" in status
        assert (
            "`count(Enum field)` now fails closed in semantic aggregate "
            "validation with `PIE-S2314`"
        ) in status
        for slice_no in ("3", "4", "6", "7", "8", "9", "10"):
            assert slice_no in status
        assert "no behavior change" in status or "without behavior change" in status


def test_status_docs_lock_phase36_candidate_resolution_posture() -> None:
    for path in STATUS_DOCS:
        status = _status(path)

        for required in (
            "Decimal precision-scale carrier",
            "deferred with exact prerequisites",
            "`limited_frozen`",
            "DateTime, Time, and Interval",
            "unsupported/deferred",
            "Any, Bytes, and Json posture",
            "type alias",
            "domain refinement",
            "expanded scalar/operator matrix",
            "public surface stability",
            "Currency/Money",
            "native DB metadata remain deferred",
        ):
            assert required in status, f"{path}: {required}"


def test_status_docs_lock_public_schema_package_and_release_boundaries() -> None:
    for path in STATUS_DOCS:
        status = _status(path)

        assert (
            "Public schemas and outputs remain unchanged" in status
            or "No public schema/output expansion occurred" in status
        ), str(path)
        for required in (
            "CLI JSON v1",
            "Project JSON v2",
            "Semantic Metadata Artifact v1",
            "diagnostic envelope",
            "SQL golden",
            "fixtures/goldens",
            "workflows",
            "scripts",
            "lockfiles",
            "package metadata",
            "Package version remains `0.1.0`",
            "No tag/release/publish/upload/signing/attestation occurred",
            "source/compiler behavior changes",
            "workflow changes",
            "release operations",
            "public schema changes",
            "generated artifacts",
        ):
            assert required in status, f"{path}: {required}"

        lowered = status.lower()
        for forbidden in POSITIVE_RELEASE_CLAIMS:
            assert forbidden not in lowered, f"{path}: {forbidden}"


def test_agents_gate_workflow_is_current_for_phase36_slice11() -> None:
    agents = _status(AGENTS_PATH)

    for required in (
        "Gate workflow remains",
        "Gate 1 = read-only planning",
        "Gate 2 = implementation + evidence only",
        "must not stage, commit, push, or poll CI",
        "Gate 3 = exact staging, commit, push, and CI `headSha` verification",
    ):
        assert required in agents, required


def test_phase36_plan_records_slice11_status_housekeeping_boundary() -> None:
    plan = _status(PHASE36_PLAN_PATH)

    for required in (
        "Phase 36 Slice 11 selects Option B",
        "docs/status-only housekeeping",
        "updates `README.md`, `AGENTS.md`, and `docs/spec/pietto-v0.9.md`",
        "Phase 36 is complete through Slice 10",
        "does not claim Phase 36 final completion",
        "Slice 12 remains Completion Audit And Status Lock",
        "may update existing audit tests only",
        "No tag/release/publish/upload/signing or attestation",
    ):
        assert required in plan, required


def test_package_version_remains_010() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]

    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert 'version = "0.2.0"' not in _read(PYPROJECT_PATH)


def test_forbidden_implementation_package_and_workflow_surfaces_are_unchanged() -> None:
    diff_output = _git_diff_name_only(REPO_ROOT, FORBIDDEN_DIFF_PATHS)

    assert diff_output == ""
