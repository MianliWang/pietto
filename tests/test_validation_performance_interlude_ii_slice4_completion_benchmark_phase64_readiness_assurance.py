from __future__ import annotations

from collections import Counter
import re
from pathlib import Path
import sys

import _pietto_differential_process_acquisition as acquisition


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/validation-performance-interlude-ii-slice4-completion-benchmark-phase64-readiness-assurance-v1.md"
)
SLICE1_SPEC = (
    REPO_ROOT
    / "docs/spec/validation-performance-interlude-ii-slice1-post-phase63-baseline-profiling-cost-attribution-route-lock-v1.md"
)
SLICE2_SPEC = (
    REPO_ROOT
    / "docs/spec/validation-performance-interlude-ii-slice2-differential-probe-process-acquisition-optimization-v1.md"
)
SLICE3_SPEC = (
    REPO_ROOT
    / "docs/spec/validation-performance-interlude-ii-slice3-heavy-file-xdist-scheduling-isolation-decision-v1.md"
)
PHASE63_HANDOFF_SPEC = (
    REPO_ROOT / "docs/spec/phase63-completion-audit-phase64-handoff-v1.md"
)
INTERLUDE_II_SPECS = (SLICE1_SPEC, SLICE2_SPEC, SLICE3_SPEC, SPEC)
VALIDATE_PATH = REPO_ROOT / "scripts/validate.py"
WORKFLOW = REPO_ROOT / ".github/workflows/ci.yml"
GRAMMAR = REPO_ROOT / "grammar/Pietto.g4"
AST_NODES = REPO_ROOT / "src/pietto/ast_nodes.py"
IR_JOINS = REPO_ROOT / "src/pietto/_project/project_ir_joins.py"
PUBLICATION_ROLES = (
    ("0cebaf14031779f4a824f1c44e5f7d65a0f5e782", "33916022012", "success"),
    ("69cf857310491b29822302f17d494293e33ff65b", "33954322616", "success"),
    ("d847132a7276ce94bbb4e9e9386d46d8eaebb914", "33961299369", "failure"),
    ("3e4646de879becc6a93c1502fb033c716d1bf19e", "33961794923", "success"),
    ("4cfed753ae59df4df8cbce351503fe474d42e889", "33991714141", "failure"),
    ("461e5ef59b689b61a1815f039b93331bed3ac576", "33993596747", "success"),
)
JOB_IDS = (
    "101163246179",
    "101163246061",
    "101274743680",
    "101274743571",
    "101293530085",
    "101293529944",
    "101294828478",
    "101294828489",
    "101375009385",
    "101375009458",
    "101380036292",
    "101380036207",
)
COMPARABILITY_LABELS = (
    "MATERIAL_IMPROVEMENT",
    "NO_MATERIAL_CHANGE",
    "MATERIAL_REGRESSION_EXPLAINED",
    "NOT_COMPARABLE",
    "NOT_MEASURED",
)
PHASE64_TRANSFERRED_SUBJECTS = (
    "Generic JOIN over arbitrary completed/effective row sources",
    "Generic authored ON/refinement",
    "CROSS / RIGHT / FULL / SEMI / ANTI JOIN",
    "DISTINCT",
    "UNION / INTERSECT / EXCEPT",
    "Single-match enforcement",
    "`EFFECTIVE_UPSTREAM_JOIN_UNSUPPORTED`",
    "`EFFECTIVE_JOIN_INPUT_REBIND_UNSUPPORTED`",
)
ABSENT_FROM_GRAMMAR = (
    "UNION",
    "INTERSECT",
    "EXCEPT",
    "DISTINCT",
    "CROSS",
    "RIGHT",
    "FULL",
    "SEMI",
    "ANTI",
)
EXPECTED_ADDED_PATHS = (
    "docs/spec/validation-performance-interlude-ii-slice4-completion-benchmark-phase64-readiness-assurance-v1.md",
    "tests/test_validation_performance_interlude_ii_slice4_completion_benchmark_phase64_readiness_assurance.py",
)
EXPECTED_NAMED_MODIFIED_PATHS = (
    "docs/spec/validation-performance-interlude-ii-slice3-heavy-file-xdist-scheduling-isolation-decision-v1.md",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_validation_performance_interlude_ii_slice3_heavy_file_xdist_scheduling_isolation_decision.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
FORBIDDEN_PATH_PREFIXES = (".github/", "src/", "scripts/", "grammar/")
KNOWN_PUBLISHED_HASHES = frozenset(
    {
        "0cebaf14031779f4a824f1c44e5f7d65a0f5e782",
        "1f4d6af00befbac20ec0f639176fc0f9023aedc8",
        "69cf857310491b29822302f17d494293e33ff65b",
        "1fd51b9179c87988a2373ce62a370b65166abeab",
        "d847132a7276ce94bbb4e9e9386d46d8eaebb914",
        "791a5c3121262a79a37178086a0f54c203f9ada3",
        "3e4646de879becc6a93c1502fb033c716d1bf19e",
        "d1d7c039642dd644ee24fbb6ccb6bb133830113c",
        "4cfed753ae59df4df8cbce351503fe474d42e889",
        "f574eeb09283f72f12f8df4f7bdd3dd9b72f0828",
        "461e5ef59b689b61a1815f039b93331bed3ac576",
        "0daaa299e8dacbce4c9c707d4b8706e8e1cea8b9",
        "1ce7f116799989400b42002ae5fe370aae61000f8847e36cc443552a7f6a4644"[:40],
    }
)


def _section(document: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert document.count(marker) == 1
    start = document.index(marker) + len(marker)
    end = document.find("\n## ", start)
    return document[start:] if end == -1 else document[start:end]


def _normalized(heading: str) -> str:
    return " ".join(_section(SPEC.read_text(encoding="utf-8"), heading).split())


def test_starting_authority_and_publication_ledger_are_exact() -> None:
    authority = _normalized("Starting Authority")
    ledger = _normalized("Interlude II Publication Ledger")

    for value in (
        "461e5ef59b689b61a1815f039b93331bed3ac576",
        "0daaa299e8dacbce4c9c707d4b8706e8e1cea8b9",
        "4cfed753ae59df4df8cbce351503fe474d42e889",
        "Publish acquisition completion before releasing its lock",
        "33993596747",
        "101380036207",
        "101380036292",
    ):
        assert value in authority

    for commit, run, _result in PUBLICATION_ROLES:
        assert commit in ledger
        assert run in ledger
    for job in JOB_IDS:
        assert job in ledger
    assert "five-commit first-parent chain" in ledger
    assert "preserved publication evidence, not terminals" in ledger
    assert "neither was amended, squashed, manually rerun, or erased" in ledger


def test_both_failed_heads_are_classified_without_reinterpretation() -> None:
    ledger = _normalized("Interlude II Publication Ledger")

    assert "Slice-2 failed implementation head" in ledger
    assert "Slice-3 failed no-gain publication head" in ledger
    assert "pinned the running interpreter's relocated and installed cell" in ledger
    assert "derives them from `sys.version_info`" in ledger
    assert "not an acquisition-layer semantic failure" in ledger
    assert "11,505 of 11,506 tests passed" in ledger
    assert "released a shared-resource lock before publishing its completion" in ledger
    assert "correctness repair, not a scheduler optimization" in ledger
    assert "11,514 of 11,515 tests passed" in ledger


def test_frozen_slice1_baselines_and_final_benchmark_arithmetic_agree() -> None:
    collection = _normalized("Collection Benchmark")
    serial = _normalized("Serial Full-Suite Benchmark")
    parallel = _normalized("Resource-Aware Benchmark")
    validator = _normalized("Timed Validator Benchmark")

    for baseline in ("2.85s", "1.96s", "157516 KiB", "11487"):
        assert baseline in collection
    for final in ("3.45s", "2.02s", "158284 KiB", "11516"):
        assert final in collection

    for baseline in ("293.94s", "295.08s", "287.36s", "309516 KiB"):
        assert baseline in serial
    assert "**224.825s**" in serial
    assert "**223.57s**" in serial
    assert "8.95% of the midpoint" in serial

    # Medians and percentages must agree with the published runs.
    serial_walls = (234.89, 214.76)
    serial_sessions = (233.59, 213.55)
    serial_wall_median = sum(serial_walls) / 2
    serial_session_median = sum(serial_sessions) / 2
    assert serial_wall_median == 224.825
    assert serial_session_median == 223.57
    assert f"{(293.94 - serial_session_median) / 293.94 * 100:.2f}%" == "23.94%"
    assert f"{(295.08 - serial_wall_median) / 295.08 * 100:.2f}%" == "23.81%"
    assert "−23.94%" in serial
    assert "−23.81%" in serial

    parallel_walls = (88.85, 93.08)
    parallel_sessions = (88.41, 92.64)
    assert sum(parallel_walls) / 2 == 90.965
    assert sum(parallel_sessions) / 2 == 90.525
    assert "**90.965s**" in parallel
    assert "**90.525s**" in parallel
    assert "4.65% of the midpoint" in parallel

    for baseline in ("22.270s", "29.338s", "97.143s", "148.821s"):
        assert baseline in validator
    for final in ("22.058s", "28.044s", "88.635s", "138.826s"):
        assert final in validator


def test_every_comparison_carries_an_admitted_classification() -> None:
    document = SPEC.read_text(encoding="utf-8")
    for label in COMPARABILITY_LABELS:
        assert f"`{label}`" in document
    assert "`POLICY-LEVEL / WORKER-COUNT-DIFFERENT`" in document
    assert "FIXED-SEVEN NOT RUN — CURRENT RESOURCE AUTHORITY LOWER" in document

    serial = _normalized("Serial Full-Suite Benchmark")
    parallel = _normalized("Resource-Aware Benchmark")
    assert "like-for-like comparison" in serial
    assert "conservative because the candidate executes 29 more tests" in serial
    assert "`MATERIAL_REGRESSION_EXPLAINED`" in serial
    assert "process count fell from 109 to 38" in serial
    assert "no exact scheduler or parallel gain is claimed" in parallel
    assert "`NOT_COMPARABLE`" in parallel

    scorecard = _normalized("Completion Scorecard")
    assert "Only the serial row claims an exact wall-time gain" in scorecard
    for area in (
        "Collection/import",
        "Differential process acquisition",
        "Nested CLI/build/install acquisition",
        "Heavy-file xdist scheduling",
        "Acquisition isolation",
        "Production Pyright",
        "Test Pyright",
        "Repository readers",
        "Semantic/IR fixture reuse",
        "Verification traversal",
        "Full serial suite",
        "Resource-aware pytest",
        "Validator total",
    ):
        assert area in scorecard


def test_prior_slice_dispositions_are_preserved_exactly() -> None:
    slice2 = _normalized("Exact Slice-2 Optimization Closure")
    slice3 = _normalized("Exact Slice-3 No-Gain Closure")
    repair = _normalized("Exact Slice-3 Isolation Repair Closure")

    for row in (
        "logical outer requests = 62 -> 62",
        "semantic main() calls = 156 -> 156",
        "outer probe processes = 62 -> 16",
        "nested CLI processes = 78 -> 9 sessions",
        "direct child processes = 109 -> 38",
        "median child wall = 171.460s -> 85.015s",
        "50.42% lower",
        "46.22% lower",
    ):
        assert row in slice2
    assert "No interpreter, seed, relocation cell, installed-wheel cell" in slice2

    assert "NO_GAIN — CURRENT LOADFILE AUTHORITY RETAINED" in slice3
    for row in ("100.14s", "101.94s", "95.89s", "4.24%", "15%", "85.12s"):
        assert row in slice3
    assert "single indivisible fixture setup" in slice3
    assert "retained `loadfile` byte-identically" in slice3

    for row in (
        "completion marker published before lock release",
        "completion and failure rechecked inside both critical sections",
        "10/10 regression runs passed",
        "200 rounds x 8 threads on Python 3.13: zero duplicate production",
        "200 rounds x 8 threads on Python 3.12: zero duplicate production",
    ):
        assert row in repair
    assert "not a scheduler optimization" in repair


def test_mode_partition_correction_is_derived_and_scoped() -> None:
    correction = _normalized("Slice-3 Mode-Count Evidence Correction")

    assert "9 + 5 + 3 = 17" in correction
    assert "mode : checkout 8 + relocated 5 + installed 3 = 16" in correction
    assert "version : running interpreter 9 + other interpreter 7 = 16" in correction
    assert "provenance of the error is the independent version partition" in correction
    assert "`9 cells correct` to `8 cells correct`" in correction
    assert "does not reopen Slice 3" in correction

    # Derive both partitions from the live closed plan.
    plan = acquisition.cell_plan({(3, 13): "python3.13", (3, 12): "python3.12"})
    modes = Counter(cell.mode for cell in plan)
    versions = Counter(cell.version for cell in plan)
    assert modes == Counter({"checkout": 8, "relocated": 5, "installed": 3})
    # The mode partition is interpreter-invariant; the version partition mirrors
    # because Phase-58..61 anchor three requests to the running interpreter.
    current = sys.version_info[:2]
    other = next(v for v in acquisition.SUPPORTED_INTERPRETERS if v != current)
    assert versions == Counter({current: 9, other: 7})
    assert sum(modes.values()) == sum(versions.values()) == len(plan) == 16

    # The impossible triple must survive nowhere as current evidence.
    slice3 = SLICE3_SPEC.read_text(encoding="utf-8")
    assert (
        "| Checkout-mode import origin | inside the checkout | 8 cells correct |"
        in (slice3)
    )
    assert "9 cells correct" not in slice3

    # The correction is confined to the two Slice-3 paths.
    assert "confined to lock ordering" in slice3
    for other in (SLICE1_SPEC, SLICE2_SPEC):
        assert "cells correct" not in other.read_text(encoding="utf-8")


def test_interlude_self_owned_open_is_zero() -> None:
    audit = _normalized("Interlude II Self-Owned-Open Audit")

    assert "Interlude II self-owned-open = 0" in audit
    for owner in (
        "Slice 1 profiling/route lock = CLOSED",
        "Slice 2 differential acquisition = OPTIMIZED / CLOSED",
        "Slice 3 xdist scheduling = NO_GAIN / CLOSED",
        "Slice 3 isolation race = REPAIRED / CLOSED",
        "Slice 3 mode-count evidence typo = CORRECTED / CLOSED",
        "Slice 4 completion benchmark = MEASURED / CLOSED",
        "Slice 4 Phase-64 readiness = READY / CLOSED",
    ):
        assert owner in audit
    assert "No current owner is created from hypothetical hardware" in audit
    assert "provenance, not current open work" in audit

    # No unresolved marker exists in any published Interlude II specification.
    markers = ("TO" + "DO", "FIX" + "ME", "T" + "BD")
    for spec in (SLICE1_SPEC, SLICE2_SPEC, SLICE3_SPEC):
        text = spec.read_text(encoding="utf-8")
        for marker in markers:
            assert marker not in text
    # This Slice names the categories only inside its own census row.
    for marker in markers:
        carrying = [
            line
            for line in SPEC.read_text(encoding="utf-8").splitlines()
            if marker in line
        ]
        assert len(carrying) == 1
        assert carrying[0].startswith("| TO" + "DO / FIX" + "ME / T" + "BD |")
        assert "none exist" in carrying[0]


def test_phase64_transferred_subjects_remain_unimplemented() -> None:
    readiness = _normalized("Phase-64 Readiness")

    for subject in PHASE64_TRANSFERRED_SUBJECTS:
        assert subject in readiness
    assert "`{INNER, LEFT}`" in readiness
    assert "the only matches are the existing `count_distinct` aggregate" in readiness
    assert "22 inherited assets" in readiness
    assert "12 mandatory Phase-64 initiation questions remain unanswered" in readiness
    assert "proposes no Slice count, and freezes no Phase-64 architecture" in readiness
    for line in (
        "prerequisite authority = EXISTS",
        "Interlude block = CLEARED on successful publication",
        "Phase-64 implementation = ABSENT",
        "Phase-64 numbered route = ABSENT",
        "Phase-64 fresh initiation gate = STILL REQUIRED",
    ):
        assert line in readiness

    # Live production still admits only the two authored JOIN kinds.
    ast_source = AST_NODES.read_text(encoding="utf-8")
    ir_source = IR_JOINS.read_text(encoding="utf-8")
    assert 'INNER = "inner"' in ast_source and 'LEFT = "left"' in ast_source
    assert 'INNER = "inner"' in ir_source and 'LEFT = "left"' in ir_source

    grammar = GRAMMAR.read_text(encoding="utf-8")
    assert "(INNER | LEFT) JOIN" in grammar
    for keyword in ABSENT_FROM_GRAMMAR:
        assert not re.search(rf"\b{keyword}\b", grammar)

    handoff = PHASE63_HANDOFF_SPEC.read_text(encoding="utf-8")
    assert "## Phase-64 Mandatory Initiation Questions" in handoff
    assert "## Exact Phase-64 Transfers" in handoff


def test_zero_delta_boundary_and_closure_are_exact() -> None:
    boundary = _normalized("Zero-Delta Boundary")
    closure_section = _section(
        SPEC.read_text(encoding="utf-8"), "Changed-Path And Lifecycle Lock"
    )
    closure = " ".join(closure_section.split())

    for delta in (
        "production delta = 0",
        "grammar/generated delta = 0",
        "validator-policy delta = 0",
        "xdist-policy delta = 0",
        "worker-policy delta = 0",
        "acquisition-layer delta = 0",
        "Phase-64 implementation delta = 0",
    ):
        assert delta in boundary
    assert "remain byte-identical to `461e5ef5...`" in boundary

    assert "`A2/M6/D0`, eight paths" in closure
    added = tuple(
        line[2:] for line in closure_section.splitlines() if line.startswith("A ")
    )
    modified = tuple(
        line[2:] for line in closure_section.splitlines() if line.startswith("M ")
    )
    assert not any(line.startswith("D ") for line in closure_section.splitlines())
    assert added == EXPECTED_ADDED_PATHS
    assert len(modified) == 6
    assert len(set(added) | set(modified)) == 8
    for path in (*added, *modified):
        assert (REPO_ROOT / path).is_file()
        assert not path.startswith(FORBIDDEN_PATH_PREFIXES)
    for path in EXPECTED_NAMED_MODIFIED_PATHS:
        assert path in modified
    lifecycle_documents = tuple(
        path for path in modified if path not in EXPECTED_NAMED_MODIFIED_PATHS
    )
    assert len(lifecycle_documents) == 2
    for path in lifecycle_documents:
        assert path.startswith("docs/")
        assert path.endswith(".md")
        assert not path.startswith("docs/spec/")

    assert "production Python `179` unchanged" in closure
    assert "`427 -> 428`" in closure
    assert "sole current Python inventory owner" in closure
    assert "sole mutable lifecycle-document reader" in closure
    assert "repair batches `1/12`" in closure
    assert "mechanical historical paths `2/12`" in closure
    assert "production mutations `0`" in closure

    # The validator and workflow policy are untouched by this Slice.
    validate_source = VALIDATE_PATH.read_text(encoding="utf-8")
    assert 'dist_mode = args.pytest_dist or "loadfile"' in validate_source
    assert "PYTEST_DIST_CHOICES = (" in validate_source
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert workflow.count("uv run python scripts/validate.py --timings") == 1
    for override in ("--pytest-workers", "--pytest-dist", "--pytest-maxprocesses"):
        assert override not in workflow


def test_completion_lifecycle_requires_no_status_only_commit() -> None:
    closure_section = _section(
        SPEC.read_text(encoding="utf-8"), "Changed-Path And Lifecycle Lock"
    )
    closure = " ".join(closure_section.split())
    answer = _normalized("Answer And Scope")

    assert "without a status-only follow-up commit" in closure
    for line in (
        "Phase 63 = COMPLETED",
        "Validation/Test Performance Optimization Interlude II = COMPLETED",
        "Interlude II Slices 1-4 = COMPLETED / PUBLISHED",
        "Interlude II self-owned-open = 0",
        "Phase 64 = NEXT / NOT IMPLEMENTED",
        "Phase 64 = not ACTIVE",
        "Phase 64 numbered route = absent",
    ):
        assert line in closure_section
    assert "not activated here" in closure
    assert "fresh Phase-64 Product/Phase Initiation Gate v3" in closure

    assert "Interlude II self-owned-open = 0" in answer
    assert "Phase 64 implementation = NOT STARTED" in answer
    assert "implements no optimization" in answer

    # The not-yet-known publication head is absent: every 40-hex token in the
    # immutable contract is a already-published commit or tree.
    document = SPEC.read_text(encoding="utf-8")
    observed = set(re.findall(r"\b[0-9a-f]{40}\b", document))
    assert observed
    assert observed <= KNOWN_PUBLISHED_HASHES

    own_imports = tuple(
        line
        for line in Path(__file__).resolve().read_text(encoding="utf-8").splitlines()
        if line.startswith(("import ", "from "))
    )
    assert own_imports == (
        "from __future__ import annotations",
        "from collections import Counter",
        "import re",
        "from pathlib import Path",
        "import sys",
        "import _pietto_differential_process_acquisition as acquisition",
    )
