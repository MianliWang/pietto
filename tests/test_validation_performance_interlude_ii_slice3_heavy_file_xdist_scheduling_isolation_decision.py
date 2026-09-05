from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import _pietto_differential_process_acquisition as acquisition
import _pietto_differential_probe_batch as batch


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/validation-performance-interlude-ii-slice3-heavy-file-xdist-scheduling-isolation-decision-v1.md"
)
SLICE1_SPEC = (
    REPO_ROOT
    / "docs/spec/validation-performance-interlude-ii-slice1-post-phase63-baseline-profiling-cost-attribution-route-lock-v1.md"
)
SLICE2_SPEC = (
    REPO_ROOT
    / "docs/spec/validation-performance-interlude-ii-slice2-differential-probe-process-acquisition-optimization-v1.md"
)
PHASE63_COMPLETION_SPEC = (
    REPO_ROOT / "docs/spec/phase63-completion-audit-phase64-handoff-v1.md"
)
VALIDATE_PATH = REPO_ROOT / "scripts/validate.py"
WORKFLOW = REPO_ROOT / ".github/workflows/ci.yml"
EXPECTED_GATES = (
    ("lockfile", ("uv", "lock", "--check")),
    ("format", ("uv", "run", "ruff", "format", "--check", ".")),
    ("lint", ("uv", "run", "ruff", "check", ".")),
    ("production typing", ("uv", "run", "pyright")),
    (
        "test typing",
        ("uv", "run", "pyright", "--project", "pyrightconfig.tests.json"),
    ),
    ("tests", ("uv", "run", "pytest")),
)
SCREENED_MODES = ("loadfile", "loadscope", "load", "worksteal")
EXCLUDED_MODES = ("loadgroup", "each", "no")
TERMINAL_DISPOSITIONS = ("OPTIMIZED", "NO_GAIN")
CUSTOM_SCHEDULER_TOKENS = (
    "pytest_xdist_make_scheduler",
    "xdist_group",
    "DistScheduling",
    "custom scheduler",
)
EXPECTED_ADDED_PATHS = (
    "docs/spec/validation-performance-interlude-ii-slice3-heavy-file-xdist-scheduling-isolation-decision-v1.md",
    "tests/test_validation_performance_interlude_ii_slice3_heavy_file_xdist_scheduling_isolation_decision.py",
)
EXPECTED_NAMED_MODIFIED_PATHS = (
    "tests/test_active_phase_lifecycle.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
FORBIDDEN_PATH_PREFIXES = (".github/", "src/", "scripts/", "grammar/")
RETAINED_BYTE_IDENTICAL = (
    "scripts/validate.py",
    ".github/workflows/ci.yml",
    "tests/_pietto_differential_process_acquisition.py",
    "tests/_pietto_differential_probe_batch.py",
    "tests/_pietto_project_explain_scenarios.py",
    "tests/test_phase58_slice16_pure_differential_compatibility_assurance.py",
    "tests/test_phase59_slice11_differential_compatibility_assurance.py",
    "tests/test_phase60_slice12_differential_compatibility.py",
    "tests/test_phase61_slice11_differential_compatibility.py",
    "tests/test_phase62_slice15_real_authored_e2e_python_differential_metamorphic_join_assurance.py",
    "tests/test_phase63_slice15_inspection_pure_boundary_real_e2e_differential_metamorphic_assurance.py",
)


def _load_validate_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "pietto_interlude_ii_slice3_validate",
        VALIDATE_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _section(document: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert document.count(marker) == 1
    start = document.index(marker) + len(marker)
    end = document.find("\n## ", start)
    return document[start:] if end == -1 else document[start:end]


def _normalized(heading: str) -> str:
    return " ".join(_section(SPEC.read_text(encoding="utf-8"), heading).split())


validate = cast(Any, _load_validate_module())


def test_lifecycle_boundary_and_owned_decision_are_exact() -> None:
    answer = _normalized("Answer And Scope")
    authority = _normalized("Starting Authority And Preserved Slice-2 Lineage")

    assert "Phase 63 is `COMPLETED`" in answer
    assert "Validation/Test Performance Optimization Interlude II is `ACTIVE`" in answer
    assert "Interlude II Slice 4 is `NEXT / NOT IMPLEMENTED`" in answer
    assert "Phase 64 is `NEXT / BLOCKED / NOT IMPLEMENTED`" in answer

    for value in (
        "3e4646de879becc6a93c1502fb033c716d1bf19e",
        "d1d7c039642dd644ee24fbb6ccb6bb133830113c",
        "d847132a7276ce94bbb4e9e9386d46d8eaebb914",
        "33961794923",
        "101294828478",
        "101294828489",
        "791a5c3121262a79a37178086a0f54c203f9ada3",
        "33961299369",
        "101293529944",
        "101293530085",
    ):
        assert value in authority
    assert "never amended, squashed, relabelled, or manually rerun" in authority
    assert "not an acquisition-layer semantic failure" in authority

    for published in (SLICE1_SPEC, SLICE2_SPEC, PHASE63_COMPLETION_SPEC):
        assert published.is_file()


def test_terminal_disposition_is_exactly_one_admitted_value() -> None:
    document = SPEC.read_text(encoding="utf-8")
    disposition = _normalized("Terminal Disposition")
    present = tuple(value for value in TERMINAL_DISPOSITIONS if value in disposition)
    assert len(present) == 1
    assert present[0] == "NO_GAIN"
    assert "NO_GAIN — CURRENT LOADFILE AUTHORITY RETAINED" in disposition
    assert "OPTIMIZED" not in disposition
    assert document.count("`NO_GAIN — CURRENT LOADFILE AUTHORITY RETAINED`") == 1
    assert "would not be proportionate to its maintenance cost" in disposition


def test_every_standard_scheduler_is_screened_or_excluded_with_a_reason() -> None:
    inventory = _normalized("Installed Scheduler Inventory")
    heavy = _normalized("Heavy-Family Screening")
    eleven = _normalized("Eleven-File Screening")

    for mode in (*SCREENED_MODES, *EXCLUDED_MODES):
        assert f"`{mode}`" in inventory
    assert "pytest-xdist 3.8.0" in inventory
    assert "requires a new `xdist_group` marker taxonomy" in inventory
    assert "sends every test to every environment" in inventory
    assert "No scheduler was installed, upgraded, or written" in inventory

    for mode in SCREENED_MODES:
        assert f"`{mode}`" in heavy
        assert f"`{mode}`" in eleven
    assert "62 passed" in heavy
    assert "194 passed" in eleven


def test_baseline_and_candidate_medians_apply_the_fifteen_percent_rule() -> None:
    baseline = _normalized("Post-Slice-2 Loadfile Baseline")
    comparison = _normalized("Formal Full-Suite Comparison")
    tail = _normalized("Heavy-Unit Tail Evidence")

    assert "**100.14s**" in baseline
    assert "11506 passed" in baseline
    assert "exactly 16 acquisition cells from exactly 16 batch executions" in baseline
    assert "97.143s gate" in baseline
    assert "**not** the adoption denominator" in baseline

    for value in (
        "gain(loadscope) = (100.14 - 101.94) / 100.14 = -1.79%",
        "gain(worksteal) = (100.14 - 95.89) / 100.14 = +4.24%",
        "adoption gate = 15%",
        "adoption target = candidate median wall <= 85.12s",
        "Neither candidate meets the gate",
        "Medians govern; the fastest single run is not used",
    ):
        assert value in comparison

    assert "single indivisible *test*" in tail
    assert "40.92s" in tail
    assert "No file-, scope-, or test-level scheduler can split one test" in tail


def test_exact_parity_and_four_worker_portability_are_recorded() -> None:
    parity = _normalized("Exact Parity")
    portability = _normalized("Four-Worker Portability")

    assert "11506" in parity
    assert "0dded3164f95de59a6da403fee0936b3716d92b175d8a5e729ab5a287877351d" in parity
    assert "Skips / xfails / deselections introduced | 0 | 0" in parity
    assert (
        "No test was removed, renamed, skipped, xfailed, deselected or reclassified"
        in parity
    )
    assert "identical pre-principal collection" in parity

    assert "`-n 4`" in portability
    assert "11506 passed" in portability
    assert "still far below the 15% gate" in portability
    assert "no deadlock, no duplicate acquisition and no orphan process" in portability


def test_acquisition_invariants_hold_under_the_candidate_scheduler() -> None:
    invariants = _normalized("Acquisition Invariants Under The Candidate Scheduler")

    for row in (
        "Logical requests | 62 | 62",
        "Process cells | exact live plan, 16 | 16",
        "Batch executions | one per cell | 16 batch children",
        "`uv build` | 1 | 1",
        "`uv pip install` | 1 | 1",
        "Leftover acquisition `.lock` | 0 | 0",
        "Leftover `.pending` | 0 | 0",
        "Unexpected `.failed` | 0 | 0",
        "Orphan batch child or CLI worker | none | none",
    ):
        assert row in invariants
    assert "outside the checkout" in invariants
    assert "no cross-run result reuse and no persistent cache exists" in invariants
    assert "not acquisition locks" in invariants

    # The published Slice-2 acquisition plan is closed authority here.
    two_interpreters = {(3, 13): "python3.13", (3, 12): "python3.12"}
    plan = acquisition.cell_plan(two_interpreters)
    assert len(plan) == 16
    assert sum(len(requests) for requests in plan.values()) == 62
    assert acquisition.FAMILY_ORDER == tuple(batch.FAMILY_MODULES)


def test_no_custom_scheduler_or_policy_change_exists() -> None:
    assert validate.GATES == EXPECTED_GATES
    assert validate.PYTEST_COMMAND == ("uv", "run", "pytest")
    assert validate.PYTEST_DIST_CHOICES == ("loadfile", "loadscope")
    assert validate.PYTEST_WORKER_MEMORY_BYTES == 512 * 1024 * 1024
    assert validate.PYTEST_MIN_MEMORY_RESERVE_BYTES == 1024 * 1024 * 1024

    # The retained default is loadfile, and the serial fallback is unchanged.
    command_source = inspect.getsource(validate._pytest_command)
    assert 'dist_mode = args.pytest_dist or "loadfile"' in command_source
    assert "if worker_count == 1:\n            return PYTEST_COMMAND" in command_source

    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert workflow.count("uv run python scripts/validate.py --timings") == 1
    for override in ("--pytest-workers", "--pytest-dist", "--pytest-maxprocesses"):
        assert override not in workflow

    scheduling_owners = (
        VALIDATE_PATH.read_text(encoding="utf-8")
        + inspect.getsource(acquisition)
        + inspect.getsource(batch)
    )
    for token in CUSTOM_SCHEDULER_TOKENS:
        assert token not in scheduling_owners
    for retained in ("worksteal", "loadgroup"):
        assert retained not in VALIDATE_PATH.read_text(encoding="utf-8")


def test_no_gain_retention_and_closure_are_exact() -> None:
    document = SPEC.read_text(encoding="utf-8")
    answer = _normalized("Answer And Scope")
    disposition = _normalized("Terminal Disposition")
    closure = _section(document, "Changed-Path And Lifecycle Lock")
    normalized_closure = " ".join(closure.split())

    assert "The validator therefore retains `loadfile`" in answer
    assert "Byte-identical retention is required and verified" in disposition
    for path in RETAINED_BYTE_IDENTICAL:
        assert (REPO_ROOT / path).is_file()
    assert (
        'experimental scheduling code, option, or helper is retained "for future use"'
        in (disposition)
    )

    assert "`A2/M4/D0`, six paths" in normalized_closure
    added = tuple(line[2:] for line in closure.splitlines() if line.startswith("A "))
    modified = tuple(line[2:] for line in closure.splitlines() if line.startswith("M "))
    assert not any(line.startswith("D ") for line in closure.splitlines())
    assert added == EXPECTED_ADDED_PATHS
    assert len(modified) == 4
    assert len(set(added) | set(modified)) == 6
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

    assert "production Python `179` unchanged" in normalized_closure
    assert "`426 -> 427`" in normalized_closure
    assert "sole mutable lifecycle-document reader" in normalized_closure
    assert "performs no whole-repository inventory scan" in normalized_closure
    assert "repair batches `0/12`" in normalized_closure
    assert "mechanical closure paths `0/12`" in normalized_closure
    assert "isolation repairs `0`" in normalized_closure
    assert "production mutations `0`" in normalized_closure
    assert "Interlude II Slices 1-3 = COMPLETED / PUBLISHED" in closure
    assert "Interlude II Slice 4 = NEXT / NOT IMPLEMENTED" in closure
    assert "Phase 64 = NEXT / BLOCKED / NOT IMPLEMENTED" in closure
    assert (
        "VALIDATION_PERFORMANCE_INTERLUDE_II_SLICE4_COMPLETION_BENCHMARK_AND_PHASE_64_READINESS_ASSURANCE"
        in closure
    )


def test_isolation_audit_and_measurement_hygiene_are_documented() -> None:
    audit = _normalized("Pre-Mutation Isolation Audit")
    environment = _normalized("Measurement Environment")

    for category in (
        "Module-scoped fixtures",
        "Session-scoped fixtures",
        "Package-scoped fixtures",
        "Class-scoped fixtures",
        "Working-directory changes",
        "Environment changes",
        "Process-global mutation",
        "Fixed filesystem paths",
        "Temporary repository/build targets",
        "pytest basetemp use",
        "Shared acquisition store use",
        "Nested subprocesses",
        "Network or port use",
        "Source/generated/golden writes",
        "Collection-order assumptions",
        "Worker-order assumptions",
    ):
        assert category in audit
    assert "Session-scoped fixtures | 0 | 0 | none exist" in audit
    assert "Collection-order assumptions | 0 | 0 | none" in audit
    assert "no logical observation is recomputed and no writable object is shared" in (
        audit
    )
    assert "No test depends on another test executing first" in audit

    assert "machine-local measured evidence" in environment
    assert "None of these seconds is a portable correctness assertion" in environment
    assert "Live resolved resource worker count | `6`" in environment
    assert "pins `-n 6` explicitly" in environment

    own_imports = tuple(
        line
        for line in Path(__file__).resolve().read_text(encoding="utf-8").splitlines()
        if line.startswith(("import ", "from "))
    )
    assert own_imports == (
        "from __future__ import annotations",
        "import importlib.util",
        "import inspect",
        "from pathlib import Path",
        "from types import ModuleType",
        "from typing import Any, cast",
        "import _pietto_differential_process_acquisition as acquisition",
        "import _pietto_differential_probe_batch as batch",
    )
