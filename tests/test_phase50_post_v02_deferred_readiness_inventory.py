from __future__ import annotations

import hashlib
import subprocess
import tomllib
from pathlib import Path

from _static_audit_helpers import normalized_text as _normalized
from _static_audit_helpers import read_text as _read
from test_phase54_local_import_module_export_foundation_scope_lock import (
    phase54_slice5_gate2_manifest_is_active as _slice5_gate2,
)

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
HISTORICAL_REGISTER_SHA256 = (
    "72689cf55e00d355b97cf0bebe81d5c6cf6a7c26994783f926966084c0b44a70"
)
HISTORICAL_ROADMAP_PREFIX_SHA256 = (
    "312d13baaa0a34df1b0c9880b85ba889a3e44d8ac0f980d336449acb52394670"
)
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
    normalized_inventory = _normalized(INVENTORY_PATH)
    combined = f"{plan} {normalized_inventory}"

    assert INVENTORY_TITLE in inventory
    assert "Post-v0.2 Deferred Inventory And Phase 50-60 Replan" in combined
    assert "Slice 2 is classificatory and sequencing-only." in inventory
    assert "Slice 2 implements no compiler or runtime behavior." in inventory
    assert SLICE1_BASELINE_SHA in combined
    assert SLICE1_SUBJECT in combined
    assert "29068556545" in combined
    assert "Slice 1" in plan and "completed" in plan
    assert "Slice 2" in plan and "completed" in plan
    assert "Slice 3" in plan and "completed" in plan
    assert "Slice 4" in plan and "completed" in plan
    assert "Phase 50 Slice 5 **Window-Function Readiness** completed" in plan
    assert "Slice 2 is not complete" in normalized_inventory
    assert "effective only after Slice 2 Gate 3" in normalized_inventory
    for required in (
        "5c66b00d20200d943f0b6e1d0c02813fba18904b",
        "29072890119",
        "7bd50022859a5e3d202c26d67bed1a723388048a",
        "29082580976",
        "aaf30fcd2ec4b19f6d0c23783067c369a11cd27b",
        "29097916311",
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
        "Slice 9 completed",
        "Phase 50 Slice 10 **Explain / Public Metadata / Package Integration Boundary** completed",
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
        assert required in plan, required


def test_historical_register_is_byte_preserved_from_slice1() -> None:
    digest = hashlib.sha256(HISTORICAL_REGISTER_PATH.read_bytes()).hexdigest()
    assert digest == HISTORICAL_REGISTER_SHA256

    inventory = _normalized(INVENTORY_PATH)
    assert "historical Phase 29 register remains byte-for-byte unchanged" in inventory
    assert (
        "supersedes the historical register only for current post-v0.2 "
        "classification, not for historical Phase 29 meaning"
    ) in inventory


def test_historical_roadmap_and_additive_route_order_are_locked() -> None:
    current_bytes = ROADMAP_PATH.read_bytes()
    separator = RECONCILIATION_HEADING.encode()
    current_prefix, found_separator, current_suffix = current_bytes.partition(separator)

    assert found_separator == separator
    assert separator not in current_prefix
    assert separator not in current_suffix
    assert (
        hashlib.sha256(current_prefix).hexdigest() == HISTORICAL_ROADMAP_PREFIX_SHA256
    )

    current = current_bytes.decode()
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
    inventory_route = _section(_read(INVENTORY_PATH), INVENTORY_FINAL_HEADING, "##")
    plan_route = _section(_read(PLAN_PATH), PLAN_FINAL_HEADING, "##")
    roadmap_route = _section(_read(ROADMAP_PATH), ROADMAP_FINAL_HEADING, "###")
    documents = (inventory_route, plan_route, roadmap_route)

    for section in documents:
        offsets: list[int] = []
        for title in FINAL_PHASE51_60_TITLES:
            assert section.count(title) == 1, title
            offsets.append(section.index(title))
        assert offsets == sorted(offsets)

        normalized = " ".join(section.split()).lower()
        for required in (
            "finalized active planning route",
            "every later phase requires separate authorization",
            "no automatic phase start",
            "no implementation authorization",
            "evidence-backed append-only replan",
        ):
            assert required in normalized, required

    for historical_route in (inventory_route, roadmap_route):
        assert (
            "effective only after slice 2 gate 3"
            in " ".join(historical_route.split()).lower()
        )
    normalized_plan_route = " ".join(plan_route.split()).lower()
    assert "became effective as active planning" in normalized_plan_route
    assert "additive repair commit" in normalized_plan_route
    assert "exact natural recovery ci success" in normalized_plan_route


def test_later_slices_and_phases_are_not_preclaimed() -> None:
    plan = _normalized(PLAN_PATH)
    docs = " ".join((plan, _normalized(ROADMAP_PATH), _normalized(INVENTORY_PATH)))

    assert "Slice 11 is not complete in Gate 2" in plan
    assert "Phase 50 remains in progress through Gate 2" in plan
    assert (
        "Phase 50 Slice 3 **Aggregate / Grouped Project Output-Schema Readiness** "
        "completed"
    ) in plan
    assert (
        "Phase 50 Slice 4 **Type-System Gap And Capability Readiness** completed"
    ) in plan
    assert "Phase 50 Slice 5 **Window-Function Readiness** completed" in plan
    assert "d79c5c422cb7f54ae5e5587694e49389536419cb" in plan
    assert "29115612846" in plan
    assert "Phase 50 Slice 6 **Import / Module / Export Readiness** completed" in plan
    assert "7c7f6976dd67ccc4628757f2d857b593f71f5e0f" in plan
    assert "29139545163" in plan
    assert "Phase 50 Slice 7 **Semantic Package Model Readiness** completed" in plan
    assert "a5bc07855a0994343475ba546504e64b16fc7e63" in plan
    assert "29141663534" in plan
    assert (
        "Phase 50 Slice 8 **PostgreSQL Extension Capability Readiness** completed"
        in plan
    )
    assert "9e2c0f0ddcc2047e35985e6b97daa8bf29979914" in plan
    assert "29157374991" in plan
    assert "Slice 8 completed" in plan
    assert (
        "Phase 50 Slice 9 **Multi-dialect Capability Ecosystem Readiness** completed"
        in plan
    )
    assert "f886589ac2f64eeb3770c914e7c049e2da105daa" in plan
    assert "29170827348" in plan
    assert "Slice 9 completed" in plan
    assert (
        "Phase 50 Slice 10 **Explain / Public Metadata / Package Integration Boundary** completed"
        in plan
    )
    assert "9bc6ed82f3741e3c242981bb88edfb50c73fc586" in plan
    assert "29179160024" in plan
    assert (
        "Phase 50 Slice 11 **Completion Audit And Status Lock** is the current" in plan
    )
    assert "Slice 11 is not complete in Gate 2" in plan
    assert "Phase 50 remains in progress through Gate 2" in plan
    assert "Phases 51 through 60 remain unstarted and separately authorized" in plan
    assert "Phase 54 remains readiness-only and unstarted" in plan
    assert (
        "Phase 55 remains `READINESS_CONTRACT_ONLY`, readiness-only, and unstarted"
        in plan
    )
    assert "Phase 56 remains unstarted" in plan
    assert (
        "Phase 57 remains `READINESS_CONTRACT_ONLY`, readiness-only, and unstarted"
        in plan
    )
    assert "Phase 58 remains readiness-only and unstarted" in plan
    assert "Phase 60 remains readiness-only and unstarted" in plan
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
    dirty_paths = _dirty_paths()
    assert isinstance(project, dict)
    assert project["version"] == "0.1.0"

    assert _git_output(["tag", "--points-at", "HEAD"]) == ""
    for relative_path in PROTECTED_PATHS:
        if (
            dirty_paths
            in (
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
            and relative_path
            == "tests/test_phase50_semantic_package_extension_capability_scope_lock.py"
        ):
            continue
        assert (_git_output(["diff", "--", relative_path]) == "") or _slice5_gate2(), (
            relative_path
        )

    assert SLICE1_SPEC_PATH.is_file()
    assert SLICE1_TEST_PATH.is_file()
    assert (
        dirty_paths
        in (
            set(),
            ALLOWED_PHASE50_SLICE2_GATE2_PATHS,
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
    ) or _slice5_gate2()
