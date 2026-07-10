from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

from _static_audit_helpers import normalized_text as _normalized
from _static_audit_helpers import read_text as _read

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-50-semantic-readiness-consolidation.md"
ROADMAP_PATH = REPO_ROOT / "docs/spec/pietto-roadmap-phase45-60-v1.md"
INVENTORY_PATH = (
    REPO_ROOT / "docs/spec/phase50-post-v02-deferred-readiness-inventory-v1.md"
)
TEST_PATH = REPO_ROOT / "tests/test_phase50_post_v02_deferred_readiness_inventory.py"
HISTORICAL_REGISTER_PATH = REPO_ROOT / "docs/spec/v02-deferred-feature-register-v1.md"
SLICE1_SPEC_PATH = (
    REPO_ROOT
    / "docs/spec/phase50-semantic-package-extension-capability-scope-lock-v1.md"
)
SLICE1_TEST_PATH = (
    REPO_ROOT / "tests/test_phase50_semantic_package_extension_capability_scope_lock.py"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

SLICE1_BASELINE_SHA = "85066d4a7088af82a308ca751763a4e6a10baa52"
SLICE1_SUBJECT = "Add Phase 50 readiness consolidation scope lock"
INVENTORY_TITLE = (
    "# Phase 50 Slice 2 Post-v0.2 Deferred Readiness Inventory And Phase 51-60 Route v1"
)

STATUS_VOCABULARY = (
    "IMPLEMENTED_STABLE",
    "IMPLEMENTED_LIMITED",
    "PRIVATE_FOUNDATION",
    "READINESS_CONTRACT_ONLY",
    "EXPLICITLY_DEFERRED",
    "OUT_OF_SCOPE",
    "NOT_EVIDENCED",
)

FINAL_PHASE51_60_TITLES = (
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

REQUIRED_INVENTORY_SECTIONS = (
    "Purpose And Authority",
    "Trusted Baseline",
    "Historical v0.2 Register Boundary",
    "Status Vocabulary",
    "Evidence Rules",
    "Aggregate And Grouped Schema Inventory",
    "Type-System Inventory",
    "Window-Function Inventory",
    "Project / Module / Package Inventory",
    "Extension And Dialect Capability Inventory",
    "Explain / Metadata / Lineage Inventory",
    "Relationship / Composition Inventory",
    "Runtime / Database / Integration Inventory",
    "Finalized Phase 51-60 Active Planning Route",
    "Cross-phase Prerequisites",
    "Items Outside Phase 51-60",
    "Explicit Non-goals",
    "Version And Release Boundary",
)

INVENTORY_TABLE_SECTIONS = REQUIRED_INVENTORY_SECTIONS[5:13]

ALLOWED_PHASE50_SLICE2_GATE2_PATHS = {
    "docs/plan/phase-50-semantic-readiness-consolidation.md",
    "docs/spec/pietto-roadmap-phase45-60-v1.md",
    "docs/spec/phase50-post-v02-deferred-readiness-inventory-v1.md",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
}

PROTECTED_PATHS = (
    "docs/spec/v02-deferred-feature-register-v1.md",
    "docs/spec/phase50-semantic-package-extension-capability-scope-lock-v1.md",
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    "src",
    "grammar",
    "scripts",
    ".github",
    "pyproject.toml",
    "uv.lock",
    "tests/fixtures",
    "tests/goldens",
    "examples",
)

HISTORICAL_PHASE50_ROW = "| 50 | Import / Module / Export Readiness |"
HISTORICAL_PHASE60_ROW = "| 60 | Completion Audit And Status Lock |"
RECONCILIATION_HEADING = "## Post-maintenance Phase 50 Reconciliation"
TENTATIVE_HEADING = "### Tentative Phase 51-60 Active Planning Route"
ROADMAP_FINAL_HEADING = "### Slice 2 Finalized Phase 51-60 Active Planning Route"
PLAN_FINAL_HEADING = "## Slice 2 Finalized Phase 51-60 Active Planning Route"
INVENTORY_FINAL_HEADING = "## Finalized Phase 51-60 Active Planning Route"


def _git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _git_output(args: list[str]) -> str:
    result = _git(args)
    assert result.stderr == ""
    return result.stdout.rstrip()


def _git_text(args: list[str]) -> str:
    result = _git(args)
    assert result.stderr == ""
    return result.stdout


def _dirty_paths() -> set[str]:
    paths: set[str] = set()
    output = _git_output(["status", "--porcelain", "--untracked-files=all"])
    for line in output.splitlines():
        if not line:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", maxsplit=1)[1]
        paths.add(path)
    return paths


def _section(text: str, heading: str, next_level: str) -> str:
    start = text.index(heading)
    remainder = text[start + len(heading) :]
    next_offset = remainder.find(f"\n{next_level} ")
    if next_offset == -1:
        return remainder
    return remainder[:next_offset]


def _inventory_rows() -> tuple[str, ...]:
    inventory = _read(INVENTORY_PATH)
    rows: list[str] = []
    for section_name in INVENTORY_TABLE_SECTIONS:
        section = _section(inventory, f"## {section_name}", "##")
        for line in section.splitlines():
            if not line.startswith("|"):
                continue
            if "Feature / exact layer" in line:
                continue
            if set(line) <= {"|", "-", " "}:
                continue
            rows.append(line)
    return tuple(rows)


def _row_containing(fragment: str) -> str:
    matches = [row for row in _inventory_rows() if fragment in row]
    assert len(matches) == 1, (fragment, matches)
    return matches[0]


def _assert_status(row: str, expected: str) -> None:
    assert expected in row
    assert sum(token in row for token in STATUS_VOCABULARY) == 1


def test_slice2_artifacts_title_identity_and_baseline_are_locked() -> None:
    for path in (PLAN_PATH, ROADMAP_PATH, INVENTORY_PATH, TEST_PATH):
        assert path.is_file(), path

    inventory = _read(INVENTORY_PATH)
    plan = _normalized(PLAN_PATH)
    combined = f"{plan} {_normalized(INVENTORY_PATH)}"

    assert INVENTORY_TITLE in inventory
    assert "Post-v0.2 Deferred Inventory And Phase 50-60 Replan" in combined
    assert "Slice 2 is classificatory and sequencing-only." in inventory
    assert "Slice 2 implements no compiler or runtime behavior." in inventory
    assert SLICE1_BASELINE_SHA in combined
    assert SLICE1_SUBJECT in combined
    assert "29068556545" in combined
    assert "Slice 1" in plan and "completed" in plan
    assert "Slice 2" in plan and "current" in plan
    assert "Slice 2 is not complete" in combined
    assert "Slice 2 is complete" not in combined
    assert "effective only after Slice 2 Gate 3" in combined


def test_historical_register_is_byte_preserved_from_slice1() -> None:
    baseline = _git_text(
        [
            "show",
            f"{SLICE1_BASELINE_SHA}:docs/spec/v02-deferred-feature-register-v1.md",
        ]
    )
    assert _read(HISTORICAL_REGISTER_PATH) == baseline

    inventory = _normalized(INVENTORY_PATH)
    assert "historical Phase 29 register remains byte-for-byte unchanged" in inventory
    assert (
        "supersedes the historical register only for current post-v0.2 "
        "classification, not for historical Phase 29 meaning"
    ) in inventory


def test_historical_roadmap_and_additive_route_order_are_locked() -> None:
    current = _read(ROADMAP_PATH)
    baseline = _git_text(
        [
            "show",
            f"{SLICE1_BASELINE_SHA}:docs/spec/pietto-roadmap-phase45-60-v1.md",
        ]
    )

    current_prefix = current.split(RECONCILIATION_HEADING, maxsplit=1)[0]
    baseline_prefix = baseline.split(RECONCILIATION_HEADING, maxsplit=1)[0]
    assert current_prefix == baseline_prefix
    assert current.count(HISTORICAL_PHASE50_ROW) == 1
    assert current.count(HISTORICAL_PHASE60_ROW) == 1
    assert current.index(HISTORICAL_PHASE50_ROW) < current.index(RECONCILIATION_HEADING)
    assert current.index(HISTORICAL_PHASE60_ROW) < current.index(RECONCILIATION_HEADING)
    assert TENTATIVE_HEADING in current
    assert ROADMAP_FINAL_HEADING in current
    assert current.index(TENTATIVE_HEADING) < current.index(ROADMAP_FINAL_HEADING)
    assert "project explain/public metadata" in current


def test_status_vocabulary_and_inventory_section_order_are_exact() -> None:
    inventory = _read(INVENTORY_PATH)

    offsets = [
        inventory.index(f"## {section}") for section in REQUIRED_INVENTORY_SECTIONS
    ]
    assert offsets == sorted(offsets)

    vocabulary = _section(inventory, "## Status Vocabulary", "##")
    for token in STATUS_VOCABULARY:
        assert vocabulary.count(f"### {token}") == 1

    for row in _inventory_rows():
        assert sum(token in row for token in STATUS_VOCABULARY) == 1, row


def test_high_value_classifications_are_locked() -> None:
    expected = {
        "Current single-file aggregate surface": "IMPLEMENTED_LIMITED",
        "Narrow field-bearing": "IMPLEMENTED_LIMITED",
        "Selected row-let aggregate/group interactions": "IMPLEMENTED_LIMITED",
        "Phase 47-49 direct, propagated, computed, and let project row facts": (
            "PRIVATE_FOUNDATION"
        ),
        "Aggregate/grouped project output schema": "EXPLICITLY_DEFERRED",
        "UUID": "IMPLEMENTED_LIMITED",
        "Enum": "IMPLEMENTED_LIMITED",
        "Decimal(p,s) semantic validation": "IMPLEMENTED_LIMITED",
        "Private Decimal precision/scale facts": "PRIVATE_FOUNDATION",
        "General window syntax and semantic surface": "EXPLICITLY_DEFERRED",
        "Exact catalog: row_number": "NOT_EVIDENCED",
        "Phase 53 implementation posture": "READINESS_CONTRACT_ONLY",
        "Multi-file project check": "IMPLEMENTED_LIMITED",
        "Semantic package vocabulary and candidate assets": ("READINESS_CONTRACT_ONLY"),
        "Handwritten PostgreSQL backend": "IMPLEMENTED_STABLE",
        "Closed private MySQL backend": "IMPLEMENTED_LIMITED",
        "Single-file": "IMPLEMENTED_STABLE",
        "Project JSON v2 and project-check envelope": "IMPLEMENTED_LIMITED",
        "Project origin/provenance": "PRIVATE_FOUNDATION",
        "Relationship metadata syntax": "IMPLEMENTED_LIMITED",
        "Grain and narrow JOIN contracts": "READINESS_CONTRACT_ONLY",
        "Database execution, connections": "OUT_OF_SCOPE",
    }

    for fragment, status in expected.items():
        _assert_status(_row_containing(fragment), status)


def test_private_readiness_and_bounded_implementation_boundaries_are_explicit() -> None:
    inventory = _normalized(INVENTORY_PATH)

    for required in (
        "Private carriers must never be described as public output",
        "Readiness contracts must never be described as behavior",
        "A bounded implemented surface must not be described as wholly unimplemented",
        "Private foundations are not public output",
        "Readiness contracts are not implemented behavior",
        "Current bounded implementations are not wholly unimplemented",
    ):
        assert required in inventory, required

    for required in (
        "No Project JSON or public API",
        "No public JSON, explain, IR, or SQL",
        "No private carrier serialization",
        "No Project JSON or explain output",
    ):
        assert required in _read(INVENTORY_PATH), required


def test_finalized_phase51_60_route_is_exact_in_all_three_documents() -> None:
    documents = (
        _section(_read(INVENTORY_PATH), INVENTORY_FINAL_HEADING, "##"),
        _section(_read(PLAN_PATH), PLAN_FINAL_HEADING, "##"),
        _section(_read(ROADMAP_PATH), ROADMAP_FINAL_HEADING, "###"),
    )

    for section in documents:
        offsets: list[int] = []
        for title in FINAL_PHASE51_60_TITLES:
            assert section.count(title) == 1, title
            offsets.append(section.index(title))
        assert offsets == sorted(offsets)

        normalized = " ".join(section.split()).lower()
        for required in (
            "finalized active planning route",
            "effective only after slice 2 gate 3",
            "every later phase requires separate authorization",
            "no automatic phase start",
            "no implementation authorization",
            "evidence-backed append-only replan",
        ):
            assert required in normalized, required


def test_later_slices_and_phases_are_not_preclaimed() -> None:
    docs = " ".join(
        (
            _normalized(PLAN_PATH),
            _normalized(ROADMAP_PATH),
            _normalized(INVENTORY_PATH),
        )
    )

    assert "Slices 3 through 11 remain pending" in docs
    assert "Slice 2 is complete" not in docs
    for phase in range(51, 61):
        for forbidden in (
            f"Phase {phase} is complete",
            f"Phase {phase} has started",
            f"Phase {phase} is started",
        ):
            assert forbidden not in docs, forbidden


def test_package_version_tag_protected_paths_and_dirty_set_are_locked() -> None:
    pyproject = tomllib.loads(_read(PYPROJECT_PATH))
    project = pyproject["project"]
    assert isinstance(project, dict)
    assert project["version"] == "0.1.0"

    assert _git_output(["tag", "--points-at", "HEAD"]) == ""
    for relative_path in PROTECTED_PATHS:
        assert _git_output(["diff", "--", relative_path]) == "", relative_path

    assert SLICE1_SPEC_PATH.is_file()
    assert SLICE1_TEST_PATH.is_file()
    assert _dirty_paths() in (set(), ALLOWED_PHASE50_SLICE2_GATE2_PATHS)
