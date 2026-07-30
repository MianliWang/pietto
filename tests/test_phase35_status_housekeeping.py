from __future__ import annotations

import tomllib
from pathlib import Path

from _static_audit_helpers import (
    normalized_text as _normalized,
    read_text as _read,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
PIETTO_SPEC_PATH = REPO_ROOT / "docs/spec/pietto-v0.9.md"
PHASE35_PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-35-developer-experience-and-delivery-pipeline.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

STATUS_DOCS = (AGENTS_PATH, PIETTO_SPEC_PATH)
STATUS_AND_PLAN_DOCS = (*STATUS_DOCS, PHASE35_PLAN_PATH)

PHASE34_COMPLETION_STATEMENT = (
    "Phase 34 Relationship Grain And Narrow JOIN readiness foundation is "
    "complete as docs/spec/static-audit/status-only work"
)
PHASE35_COMPLETION_STATEMENT = (
    "Phase 35 Developer Experience And Delivery Pipeline MVP is complete"
)
PHASE35_SLICE1_LOCK = (
    "Phase 35 Slice 1 remains complete at `cd6a727989f3ba47ea9e7dcd7c04b6a2a7cb1071`"
)
OFFICIAL_PHASE35_TITLE = "Developer Experience And Delivery Pipeline MVP"
UNAPPROVED_PHASE35_TITLE = (
    "Developer Experience, Delivery Pipeline, And Safe Simplification MVP"
)
SAFE_SIMPLIFICATION_SCOPE = "Safe Simplification remains a scoped discipline"
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


def test_global_status_docs_record_phase35_slice2_housekeeping() -> None:
    for path in STATUS_DOCS:
        status = _normalized(path)

        assert "Phase 34 has not started" not in status, str(path)
        assert PHASE34_COMPLETION_STATEMENT in status, str(path)
        assert (
            "The original behavior MVP remains future implementation deferred" in status
        )
        assert PHASE35_COMPLETION_STATEMENT in status, str(path)
        assert (
            "Phase 35 is active as Developer Experience And Delivery Pipeline MVP"
            not in status
        )
        assert PHASE35_SLICE1_LOCK in status, str(path)
        assert OFFICIAL_PHASE35_TITLE in status, str(path)
        assert UNAPPROVED_PHASE35_TITLE not in status, str(path)
        assert SAFE_SIMPLIFICATION_SCOPE in status, str(path)
        assert "not a roadmap title change" in status, str(path)
        assert "not source-refactor authorization" in status, str(path)
        assert "Package version remains `0.1.0`" in status, str(path)
        assert "No tag/release/publish/upload/signing/attestation occurred" in status


def test_phase35_plan_records_slice2_through_slice6_scope_without_renaming_phase35() -> (
    None
):
    plan = _normalized(PHASE35_PLAN_PATH)

    for required in (
        "Phase 35 Slice 1 Candidate Decision, Inventory, And Safe Simplification "
        "Scope is complete",
        "Phase 35 Slice 2 Status Housekeeping is complete",
        "Phase 35 Slice 3 Static Audit Helper Simplification is complete",
        "Phase 35 Slice 4 Validation And Delivery Workflow Polish is complete",
        "Phase 35 Slice 5 Internal Helper Simplification Candidate Decision is "
        "complete",
        "Phase 35 Slice 6 Completion Audit And Status Lock is complete",
        PHASE35_COMPLETION_STATEMENT,
        "Slice 3 does not extract or centralize `_paths`, `_digest`, "
        "`LOCKED_BOUNDARY_SURFACES`, `FORBIDDEN_DIFF_PATHS`, "
        "`POSITIVE_RELEASE_CLAIMS`, `PHASE34_TESTS`, phase artifact "
        "inventories, status-doc hash-lock constants, or release-claim "
        "constants",
        "Phase 35 Slice 4 Validation And Delivery Workflow Polish is "
        "docs/static-audit delivery guidance work only",
        "`UV_CACHE_DIR=/tmp/...` is the preferred sandbox-local workaround",
        "Sandbox DNS/PyPI failures in `scripts/package_smoke.py` are "
        "environment/network failures",
        "record the raw failure and rerun only `scripts/package_smoke.py` with "
        "network access if available",
        "Gate 2 evidence should be `.txt`, not `.md`",
        "long evidence should be written in small chunks",
        "`scripts/validate.py` remains the authoritative local gate",
        "Generated, golden, and package smoke checks remain separate commands",
        "Phase 35 Slice 5 Internal Helper Simplification Candidate Decision is "
        "docs/static-audit candidate-decision work only",
        "selects no production/internal helper extraction for Phase 35 Slice 5",
        "defer source refactor because all concrete candidates are behavior-adjacent",
        "CLI pipeline helper extraction is deferred",
        "JSON helper extraction is deferred",
        "SQL renderer helper extraction is deferred",
        "Semantic helper extraction is deferred",
        "Metadata builder/serializer/text helper extraction is deferred",
        PHASE34_COMPLETION_STATEMENT,
        PHASE35_COMPLETION_STATEMENT,
        PHASE35_SLICE1_LOCK,
        SAFE_SIMPLIFICATION_SCOPE,
        "not a Phase 35 title change",
        "not a roadmap title change",
        "not source-refactor authorization",
        "Package version remains `0.1.0`",
        "attestation is performed by Slice 2",
        "attestation is performed by Slice 3",
        "attestation is performed by Slice 4",
        "attestation is performed by Slice 5",
        "attestation is performed by Slice 6",
    ):
        assert required in plan, required

    assert OFFICIAL_PHASE35_TITLE in plan
    assert UNAPPROVED_PHASE35_TITLE not in plan


def test_package_version_and_release_boundaries_remain_locked() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]
    combined = " ".join(_normalized(path) for path in STATUS_AND_PLAN_DOCS)

    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert 'version = "0.2.0"' not in _read(PYPROJECT_PATH)

    lowered = combined.lower()
    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in lowered, forbidden
