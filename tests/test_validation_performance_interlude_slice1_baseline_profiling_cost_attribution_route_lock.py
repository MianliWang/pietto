from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/validation-performance-interlude-slice1-baseline-profiling-cost-attribution-route-lock-v1.md"
)
WORKFLOW = REPO_ROOT / ".github/workflows/ci.yml"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _section(document: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert document.count(marker) == 1
    start = document.index(marker) + len(marker)
    end = document.find("\n## ", start)
    return document[start:] if end == -1 else document[start:end]


def test_methodology_and_unoptimized_baseline_are_exact() -> None:
    spec = _read(SPEC)
    authority = _section(spec, "Starting Authority")
    methodology = _section(spec, "Methodology And Environment")
    pytest_baseline = _section(spec, "Collection And Full Pytest Baseline")

    for value in (
        "6a3d5d54ce728b60985718ed7b867721a1680f13",
        "d9469ac3fb715e8b6e689aa7fef9384f0662b3de",
        "33053099675",
        "10326",
    ):
        assert value in authority
    for fact in (
        "CPython 3.13.13",
        "pytest-cov 7.1.0",
        "pytest-xdist 3.8.0",
        "Python test files | 344",
        "normal user uv cache",
        "14 setup errors",
    ):
        assert fact in methodology
    for observation_label in (
        "Collection wall",
        "Full pytest wall",
        "pytest-reported session",
        "Result | 10326 passed",
        "Collection is not a dominant owner",
    ):
        assert observation_label in pytest_baseline
    assert "Hardware-dependent seconds" in methodology
    assert "not test assertions" in methodology


def test_cost_attribution_and_reader_duplication_follow_measurements() -> None:
    spec = _read(SPEC)
    slow = " ".join(_section(spec, "Slow Tests And Dominant Cost").split())
    validator = " ".join(_section(spec, "Validator And Auxiliary Attribution").split())
    readers = " ".join(_section(spec, "Repository Reader Audit").split())

    for observation in (
        "Phase 58 project-explain differential probe",
        "Phase 59 graph differential probe",
        "Interpreter/isolated `python -c` witnesses",
        "Repeated isolated probes, not wheel construction",
    ):
        assert observation in slow
    for observation in (
        "Production Pyright",
        "Test Pyright",
        "pytest with four xdist workers",
        "Pytest is the dominant validator stage",
        "combined Pyright stages are a separate material second owner",
    ):
        assert observation in validator
    for observation in (
        "53 owners scanning repository-controlled",
        "8544 reads of 665 unique paths",
        "7879 reads across 639 repeatedly read paths",
        "1762 parses of 487 unique filenames",
        "1275 parses across 460 repeatedly parsed filenames",
        "344 test files four times",
    ):
        assert observation in readers


def test_index_xdist_rust_and_route_decisions_are_bounded() -> None:
    spec = _read(SPEC)
    index = " ".join(_section(spec, "Repository Test Index Decision").split())
    boundaries = " ".join(_section(spec, "Xdist And Rust Boundaries").split())
    route = " ".join(_section(spec, "Frozen Interlude Route").split())

    assert "`RepositoryTestIndex = PARTIALLY_SUPPORTED`" in index
    assert "do not support building a monolithic index" in index
    assert "smallest shared acquisition" in index

    assert "uv run python scripts/validate.py --timings" in boundaries
    assert "No authoritative local validator or natural CI in Slice 1 uses xdist" in (
        boundaries
    )
    for prerequisite in (
        "shared mutable state",
        "cwd/environment mutation",
        "global caches",
        "package-build isolation",
        "ordering assumptions",
    ):
        assert prerequisite in boundaries
    assert "Rewriting Python tests in Rust is not owned" in boundaries
    assert "Phase 68 ownership" in boundaries

    expected_route = (
        "Baseline Profiling, Cost Attribution, And Route Lock",
        "Differential Probe Runtime Decomposition And Optimization",
        "Repository Reader Acquisition Reuse",
        "Validator Static-Analysis Stage Optimization",
        "Current-Suite Isolation Audit And Xdist Decision",
        "Completion Benchmark And Phase 60 Readiness Assurance",
    )
    assert all(owner in route for owner in expected_route)
    for metric in (
        "at least 25%",
        "at least 60%",
        "at least 30%",
        "at least 20%",
        "at least 15%",
    ):
        assert metric in route


def test_slice1_keeps_ci_serial_and_changes_no_production_surface() -> None:
    workflow = _read(WORKFLOW)
    spec = _read(SPEC)
    locks = " ".join(_section(spec, "Changed-Path And Lifecycle Lock").split())

    serial_command = "uv run python scripts/validate.py --timings"
    assert workflow.count(serial_command) == 1
    assert "--pytest-workers" not in workflow
    assert "--pytest-dist" not in workflow
    assert "--pytest-maxprocesses" not in workflow

    assert "Production, generated, golden, package, version, dependency" in locks
    assert "validator script deltas are zero" in locks
    assert "sole mutable lifecycle reader" in locks
    assert "Phase 59 = COMPLETED" in locks
    assert "Phase 60 = NOT ACTIVATED" in locks
    assert (
        "VALIDATION_PERFORMANCE_INTERLUDE_SLICE2_DIFFERENTIAL_PROBE_RUNTIME_DECOMPOSITION_AND_OPTIMIZATION"
        in locks
    )
