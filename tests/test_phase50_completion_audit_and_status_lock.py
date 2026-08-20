from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-50-semantic-readiness-consolidation.md"
SPEC_PATH = REPO_ROOT / "docs/spec/phase50-completion-audit-and-status-lock-v1.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
SELF_PATH = REPO_ROOT / "tests/test_phase50_completion_audit_and_status_lock.py"

SLICE11_TITLE = "# Phase 50 Slice 11 Completion Audit And Status Lock v1"

SPEC_SECTION_HEADINGS = (
    "Purpose And Slice Identity",
    "Authority And Evidence Hierarchy",
    "Trusted Slice 10 Baseline",
    "Phase 50 Slice Ledger",
    "Phase 50 Artifact Inventory",
    "Historical Allowlist Preservation",
    "Status Vocabulary Audit",
    "Aggregate And Grouped-schema Handoff",
    "Type-system Handoff",
    "Window-function Handoff",
    "Import Module And Export Handoff",
    "Semantic-package Handoff",
    "PostgreSQL-extension Handoff",
    "Multi-dialect Handoff",
    "Explain Public-metadata And Package-integration Handoff",
    "Public Artifact Compatibility Audit",
    "Private Carrier Privacy Audit",
    "No-compiler And No-runtime Audit",
    "Package Version And Release Audit",
    "Protected Surface Audit",
    "Completion Encoding Decision",
    "Gate 2 Pre-completion State",
    "Gate 3 Completion Condition",
    "Post-completion Phase 51–60 Status",
    "Bounded Phase 51 Handoff",
    "Explicit Remaining Deferrals",
    "Separate Authorization Boundary",
    "Stop Conditions",
)

PHASE50_SLICE_LEDGER = (
    (
        "85066d4a7088af82a308ca751763a4e6a10baa52",
        "6d898559aaa244f3e4643488c111480e6933761b",
        "Add Phase 50 readiness consolidation scope lock",
        "29068556545",
        "success",
    ),
    (
        "d35ed9a58d3fc4b81febbea8fa3540707cbcfde0",
        "85066d4a7088af82a308ca751763a4e6a10baa52",
        "Add Phase 50 post-v0.2 readiness inventory",
        "29070541316",
        "failure",
    ),
    (
        "5c66b00d20200d943f0b6e1d0c02813fba18904b",
        "d35ed9a58d3fc4b81febbea8fa3540707cbcfde0",
        "Repair Phase 50 Slice 2 CI compatibility locks",
        "29072890119",
        "success",
    ),
    (
        "7bd50022859a5e3d202c26d67bed1a723388048a",
        "5c66b00d20200d943f0b6e1d0c02813fba18904b",
        "Add Phase 50 aggregate grouped schema readiness",
        "29082580976",
        "success",
    ),
    (
        "aaf30fcd2ec4b19f6d0c23783067c369a11cd27b",
        "7bd50022859a5e3d202c26d67bed1a723388048a",
        "Add Phase 50 type capability readiness",
        "29097916311",
        "success",
    ),
    (
        "d79c5c422cb7f54ae5e5587694e49389536419cb",
        "aaf30fcd2ec4b19f6d0c23783067c369a11cd27b",
        "Add Phase 50 window function readiness",
        "29115612846",
        "success",
    ),
    (
        "7c7f6976dd67ccc4628757f2d857b593f71f5e0f",
        "d79c5c422cb7f54ae5e5587694e49389536419cb",
        "Add Phase 50 import module export readiness",
        "29139545163",
        "success",
    ),
    (
        "a5bc07855a0994343475ba546504e64b16fc7e63",
        "7c7f6976dd67ccc4628757f2d857b593f71f5e0f",
        "Add Phase 50 semantic package model readiness",
        "29141663534",
        "success",
    ),
    (
        "9e2c0f0ddcc2047e35985e6b97daa8bf29979914",
        "a5bc07855a0994343475ba546504e64b16fc7e63",
        "Add Phase 50 PostgreSQL extension capability readiness",
        "29157374991",
        "success",
    ),
    (
        "f886589ac2f64eeb3770c914e7c049e2da105daa",
        "9e2c0f0ddcc2047e35985e6b97daa8bf29979914",
        "Add Phase 50 multi-dialect capability readiness",
        "29170827348",
        "success",
    ),
    (
        "9bc6ed82f3741e3c242981bb88edfb50c73fc586",
        "f886589ac2f64eeb3770c914e7c049e2da105daa",
        "Add Phase 50 explain public metadata boundary",
        "29179160024",
        "success",
    ),
)

FINALIZED_PHASE51_60_ROUTE = (
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

STATUS_TOKENS = (
    "IMPLEMENTED_STABLE",
    "IMPLEMENTED_LIMITED",
    "PRIVATE_FOUNDATION",
    "READINESS_CONTRACT_ONLY",
    "EXPLICITLY_DEFERRED",
    "OUT_OF_SCOPE",
    "NOT_EVIDENCED",
)

PRIVATE_CARRIERS = (
    "relation_row_schemas",
    "relation_row_schema_states",
    "relation_let_scope_facts",
    "relation_row_dependency_graphs",
    "relation_row_lineages",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_slice11_artifacts_title_and_exact_heading_order_are_locked() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()
    assert SELF_PATH.is_file()

    spec = _read(SPEC_PATH)
    assert spec.startswith(f"{SLICE11_TITLE}\n")
    assert (
        tuple(
            line.removeprefix("## ")
            for line in spec.splitlines()
            if line.startswith("## ")
        )
        == SPEC_SECTION_HEADINGS
    )
    assert "Slice 11 implements no compiler or runtime behavior." in spec


def test_slice1_10_documented_commit_ci_ledger_is_locked() -> None:
    spec = _normalized(SPEC_PATH)
    for index, (commit, parent, subject, run_id, conclusion) in enumerate(
        PHASE50_SLICE_LEDGER
    ):
        for required in (commit, parent, subject, run_id, conclusion):
            assert required in spec, required
        if index:
            assert parent == PHASE50_SLICE_LEDGER[index - 1][0]

    assert "Slice 2 original CI failure" in spec
    assert "additive two-test repair" in spec


def test_status_vocabulary_and_readiness_handoffs_are_locked() -> None:
    docs = f"{_normalized(PLAN_PATH)} {_normalized(SPEC_PATH)}"
    for token in STATUS_TOKENS:
        assert token in docs, token
    for required in (
        "Aggregate And Grouped-schema Handoff",
        "Type-system Handoff",
        "Window-function Handoff",
        "Import Module And Export Handoff",
        "Semantic-package Handoff",
        "PostgreSQL-extension Handoff",
        "Multi-dialect Handoff",
        "Explain Public-metadata And Package-integration Handoff",
        "Phase 53 remains `READINESS_CONTRACT_ONLY`",
        "Phase 55 remains `READINESS_CONTRACT_ONLY`",
        "Phase 57 remains `READINESS_CONTRACT_ONLY`",
        "Phase 58 remains a readiness and privacy boundary",
        "Phase 60 remains a readiness-only ecosystem checkpoint",
    ):
        assert required in docs, required


def test_public_artifacts_and_private_carriers_remain_compatible() -> None:
    spec = _normalized(SPEC_PATH)
    for required in (
        "CLI JSON v1, Semantic Metadata Artifact v1, and Project JSON v2 remain unchanged.",
        "The bounded single-file `pietto explain FILE` surface remains unchanged.",
        "PostgreSQL remains the bounded public SQL backend",
        "MySQL remains the bounded private backend",
        "No private fact becomes public by being named as a future input.",
        "private and unserialized",
        "receive no fabricated value or winner",
    ):
        assert required in spec, required
    for carrier in PRIVATE_CARRIERS:
        assert carrier in spec, carrier


def test_completion_encoding_gate2_and_gate3_statuses_are_locked() -> None:
    docs = f"{_normalized(PLAN_PATH)} {_normalized(SPEC_PATH)}"
    condition = (
        "Phase 50 is complete only after Slice 11 Gate 3 commit, one normal "
        "push to main, and exact natural CI success for the push run whose "
        "headSha exactly matches the Slice 11 commit."
    )
    for required in (
        "conditional single-commit completion plus exact Gate 3 natural-CI evidence",
        "Slice 11 is current but incomplete in Gate 2",
        "Phase 50 remains in progress through Gate 2",
        condition,
        "No post-CI repository status-flip commit is planned or required.",
    ):
        assert required in docs, required

    for forbidden in (
        "Slice 11 Gate 3 natural CI succeeded",
        "Slice 11 commit has been pushed",
        "Phase 50 is complete after Slice 11 Gate 2",
        "Gate 3 natural CI has already succeeded",
    ):
        assert forbidden not in docs, forbidden


def test_phase51_60_route_remains_unstarted_and_separately_authorized() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)
    for route_item in FINALIZED_PHASE51_60_ROUTE:
        assert route_item in plan, route_item
    for required in (
        "Phases 51 through 60 remain unstarted and separately authorized",
        "Phase 51 does not start merely because Phase 50 completes",
        "Every later phase requires separate authorization",
        "This completion authorizes no Phase 51–60 implementation.",
    ):
        assert required in spec, required

    for phase in range(51, 61):
        for forbidden in (
            f"Phase {phase} has started",
            f"Phase {phase} is started",
            f"Phase {phase} is complete",
        ):
            assert forbidden not in spec, forbidden


def test_no_compiler_runtime_release_or_later_phase_behavior_is_claimed() -> None:
    spec = _normalized(SPEC_PATH)
    for required in (
        "Phase 50 implements no compiler or runtime behavior.",
        "Slice 11 implements no compiler or runtime behavior.",
        "adds no grammar, parser, generated artifact, AST, semantic analysis",
        "adds no production behavior or public surface",
        "Package version remains `0.1.0`.",
        "Phase 50 performs no package version change, tag, release, publish, upload, signing, or attestation.",
        "No route listing, handoff, completion statement, or future artifact name automatically starts or implements later work.",
    ):
        assert required in spec, required


def test_package_version_remains_010() -> None:
    project = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))["project"]
    assert project["version"] == "0.1.0"
