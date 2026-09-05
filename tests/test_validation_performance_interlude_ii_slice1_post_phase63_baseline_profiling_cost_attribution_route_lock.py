from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any, cast


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/validation-performance-interlude-ii-slice1-post-phase63-baseline-profiling-cost-attribution-route-lock-v1.md"
)
VALIDATE_PATH = REPO_ROOT / "scripts/validate.py"
WORKFLOW = REPO_ROOT / ".github/workflows/ci.yml"
PRIOR_INTERLUDE_SLICE1_SPEC = (
    REPO_ROOT
    / "docs/spec/validation-performance-interlude-slice1-baseline-profiling-cost-attribution-route-lock-v1.md"
)
PRIOR_INTERLUDE_SLICE6_SPEC = (
    REPO_ROOT
    / "docs/spec/validation-performance-interlude-slice6-completion-benchmark-phase60-readiness-v1.md"
)
PHASE63_COMPLETION_SPEC = (
    REPO_ROOT / "docs/spec/phase63-completion-audit-phase64-handoff-v1.md"
)
EXPECTED_PRINCIPAL_IMPORTS = (
    "from __future__ import annotations",
    "import importlib.util",
    "from pathlib import Path",
    "from types import ModuleType",
    "from typing import Any, cast",
)
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
# The completion specification owns the exact changed-path closure. This
# principal names only its own non-lifecycle paths; the two mutable lifecycle
# documents are proved structurally so they are not duplicated as literals here.
EXPECTED_ADDED_PATHS = (
    "docs/spec/validation-performance-interlude-ii-slice1-post-phase63-baseline-profiling-cost-attribution-route-lock-v1.md",
    "tests/test_validation_performance_interlude_ii_slice1_post_phase63_baseline_profiling_cost_attribution_route_lock.py",
)
EXPECTED_NAMED_MODIFIED_PATHS = (
    "tests/test_active_phase_lifecycle.py",
    "tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py",
)
FORBIDDEN_PATH_PREFIXES = (".github/", "src/", "scripts/", "grammar/")
EXPECTED_ROUTE = (
    (
        "1",
        "Post-Phase-63 Baseline Profiling, Cost Attribution, And Route Lock",
    ),
    ("2", "Differential Probe And Process Acquisition Optimization"),
    ("3", "Heavy-File Xdist Scheduling And Isolation Decision"),
    ("4", "Completion Benchmark And Phase-64 Readiness Assurance"),
)
MEASURED_OWNERS = (
    "build_empty_project_semantic_result",
    "build_project_ir_project_plan",
    "build_project_ir_evaluation_context_stage",
    "verify_project_ir_stage",
    "build_project_ir_join_region",
    "build_project_multifact_analysis",
    "verify_project_phase62",
    "build_project_completion",
    "build_project_joined_row_filters",
    "build_project_joined_aggregations",
    "build_project_joined_window_stages",
    "build_project_joined_qualifies",
    "build_project_effective_output_completion",
    "build_project_completed_semantic_result",
    "build_project_query_block_ir",
    "verify_project_query_block_ir",
    "build_project_query_block_ir_analysis_bundle",
    "build_project_query_block_ir_inspection",
    "_project_query_block_ir_document",
    "evaluate_project_query_block_ir_document",
    "_combined_topology",
    "_derive_reverse_uses",
)
REUSE_CLASSIFICATIONS = (
    "SHAREABLE_POSITIVE",
    "INDEPENDENT_IDENTITY_REQUIRED",
    "MUTATION_ISOLATED",
    "FRESH_SCOPE_REQUIRED",
    "PROCESS_ISOLATED",
    "UNKNOWN",
)
REPETITION_CLASSIFICATIONS = (
    "NORMATIVE_INDEPENDENT_RECOMPUTATION",
    "DUPLICATE_TEST_ACQUISITION",
    "DERIVED_ANALYSIS_RECOMPUTATION",
)
EVIDENCE_LABELS = ("MEASURED", "DERIVED", "INFERRED", "NOT_MEASURED")
COST_CLASSES = ("DOMINANT", "MATERIAL", "MINOR", "NOT_MEASURABLY_MATERIAL")


def _load_validate_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "pietto_interlude_ii_slice1_validate",
        VALIDATE_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _section(document: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert document.count(marker) == 1
    start = document.index(marker) + len(marker)
    end = document.find("\n## ", start)
    return document[start:] if end == -1 else document[start:end]


def _normalized(document: str, heading: str) -> str:
    return " ".join(_section(document, heading).split())


def _table_rows(document: str) -> tuple[tuple[str, ...], ...]:
    return tuple(
        tuple(cell.strip() for cell in line.strip("|").split("|"))
        for line in document.splitlines()
        if line.startswith("| ") and not line.startswith("| ---")
    )


validate = cast(Any, _load_validate_module())


def test_baseline_authority_and_lifecycle_boundary_are_exact() -> None:
    spec = _read(SPEC)
    answer = _normalized(spec, "Answer And Scope")
    authority = _normalized(spec, "Starting Authority")

    for value in (
        "0cebaf14031779f4a824f1c44e5f7d65a0f5e782",
        "1f4d6af00befbac20ec0f639176fc0f9023aedc8",
        "e1590be595f9218341c74a830f611170bfc6092a",
        "Complete Phase 63 joined query blocks",
        "33916022012",
        "`push`, `main`, attempt `1`, `success`",
        "`success` / `success`",
        "`0/0`, clean, clean, empty, none, absent",
        "`0.1.0`",
        "`11487`",
    ):
        assert value in authority
    assert "Documentation is not publication authority" in authority

    assert "Phase 63 is `COMPLETED`" in answer
    assert "Validation/Test Performance Optimization Interlude II is `ACTIVE`" in answer
    assert "Phase 64 is `NEXT / BLOCKED / NOT IMPLEMENTED`" in answer
    assert "no Phase-64 production, route, or Slice exists" in answer
    assert "fresh Product/Phase Initiation Gate after this Interlude closes" in answer

    assert PHASE63_COMPLETION_SPEC.is_file()
    assert PRIOR_INTERLUDE_SLICE1_SPEC.is_file()
    assert PRIOR_INTERLUDE_SLICE6_SPEC.is_file()


def test_slice1_is_profiling_only_with_zero_delta_policy() -> None:
    spec = _read(SPEC)
    answer = _normalized(spec, "Answer And Scope")
    methodology = _normalized(spec, "Methodology And Environment")

    assert "profiling, cost attribution, and route lock only" in answer
    assert "implements no optimization" in answer
    for untouched in (
        "production source",
        "validator script",
        "workflow",
        "xdist policy",
        "Pyright configuration",
        "fixture scope",
        "test selection",
        "assertion",
        "diagnostic",
        "witness matrix",
        "generated artifact",
        "golden fixture",
        "package",
        "dependency",
        "lockfile",
        "version",
    ):
        assert untouched in answer
    assert "No temporary profiler or measurement helper is retained" in answer
    assert "temporary out-of-repository pytest plugin" in methodology
    assert "are not repository artifacts" in methodology
    assert "uv cache was never cleared" in methodology
    assert "Instrumentation was validated on one deliberate known call" in methodology

    assert validate.GATES == EXPECTED_GATES
    assert validate.PYTEST_COMMAND == ("uv", "run", "pytest")
    assert validate.PYTEST_GATE_NAME == "tests"
    assert validate.PYTEST_DIST_CHOICES == ("loadfile", "loadscope")
    assert validate.PYTEST_WORKER_MEMORY_BYTES == 512 * 1024 * 1024
    assert validate.PYTEST_MIN_MEMORY_RESERVE_BYTES == 1024 * 1024 * 1024

    workflow = _read(WORKFLOW)
    assert workflow.count("uv run python scripts/validate.py --timings") == 1
    for override in ("--pytest-workers", "--pytest-dist", "--pytest-maxprocesses"):
        assert override not in workflow


def test_every_required_measurement_category_is_recorded() -> None:
    spec = _read(SPEC)
    measurements = _normalized(spec, "Collection Validator And Serial Measurements")
    environment = _normalized(spec, "Methodology And Environment")

    for fact in (
        "CPython 3.13.13",
        "microsoft-standard-WSL2",
        "uv | 0.11.19",
        "9.1.1 / 3.8.0 / 7.1.0",
        "1.1.411 / 0.16.4",
        "Logical CPUs / process-affinity CPUs | 20 / 20",
        "cgroup CPU quota | absent",
        "cgroup memory limit | absent",
        "Resolved validator workers / `--dist` | `7` / `loadfile`",
        "Tracked files | 883",
        "Production Python files | 179",
        "Python test files | 422",
        "Collected tests | 11487",
        "normal locked user cache, never cleared",
        "not test assertions, portable budgets, or semantic authority",
    ):
        assert fact in environment

    for label in (
        "Collection wall / user / system | 2.85s / 2.48s / 0.20s",
        "Collection maximum RSS | 157516 KiB",
        "Collection result | 11487 tests",
        "Validator external wall / user / system | 148.85s",
        "Serial pytest-reported session | 293.94s",
        "Serial result | 11487 passed",
        "uv run pytest -n 7 --dist=loadfile",
        "11487 passed in 96.65s",
        "| lockfile | 0.008s",
        "| format | 0.038s",
        "| lint | 0.023s",
        "| production typing | 22.270s",
        "| test typing | 29.338s",
        "| tests (`-n 7 --dist=loadfile`) | 97.143s",
        "| total | 148.821s",
        "package smoke",
        "No second identical resource-aware full suite was run",
    ):
        assert label in measurements

    for label in EVIDENCE_LABELS:
        assert f"`{label}`" in " ".join(spec.split())


def test_slow_family_and_construction_attribution_exist() -> None:
    spec = _read(SPEC)
    families = _section(spec, "Slow Family Attribution")
    construction = _section(spec, "Semantic And IR Construction Attribution")
    families_normalized = " ".join(families.split())
    construction_normalized = " ".join(construction.split())

    header, *rows = _table_rows(families)
    assert header == (
        "Family",
        "Visible tests",
        "Cumulative",
        "% serial",
        "Largest single",
        "Dominant phase",
    )
    assert len(rows) >= 12
    assert all(row[5] in {"setup", "call", "teardown"} for row in rows)
    for family in (
        "Phase-58 Slice-16 pure differential compatibility",
        "Phase-62 Slice-15 JOIN differential/metamorphic E2E",
        "Phase-61 Slice-11 Project-IR differential compatibility",
        "Phase-63 Slice-15 query-block IR differential/metamorphic",
        "Phase-63 Slice-12 final-output/completion construction",
        "Repository-wide/static readers",
        "Installed-wheel/package witness",
    ):
        assert family in families_normalized
    assert "241.01s, or 82.0% of the 293.94s session" in families_normalized
    assert "190.89s, or 64.9%" in families_normalized
    assert "Duration alone authorizes no optimization" in families_normalized

    construction_header, *construction_rows = _table_rows(construction)
    assert construction_header == (
        "Owner",
        "Calls",
        "Cumulative wall",
        "Mean",
        "Max",
        "Calling nodes",
        "Distinct input roots",
    )
    assert len(construction_rows) >= len(MEASURED_OWNERS)
    for owner in MEASURED_OWNERS:
        assert f"`{owner}`" in construction_normalized
    assert "eleven files" in construction_normalized
    assert "still yields only 2.65s" in construction_normalized
    assert "0.90% of the 293.94s serial session" in construction_normalized
    assert "not a material cost owner" in construction_normalized
    assert "keyword-only" in construction_normalized


def test_snapshot_reuse_and_verification_classifications_are_complete() -> None:
    spec = _read(SPEC)
    reuse = _section(spec, "Snapshot Reuse Classification")
    verification = _section(spec, "Verification And Derived Analysis Attribution")
    reuse_normalized = " ".join(reuse.split())
    verification_normalized = " ".join(verification.split())

    for classification in REUSE_CLASSIFICATIONS:
        assert f"`{classification}`" in reuse_normalized
    assert "Exactly one cross-module `SHAREABLE_POSITIVE` duplicate" in (
        reuse_normalized
    )
    assert "current reconstruction count is 1" in reuse_normalized
    assert "reusable boundary would be session scope" in reuse_normalized
    assert "Nothing is implemented here" in reuse_normalized

    for classification in REPETITION_CLASSIFICATIONS:
        assert f"`{classification}`" in verification_normalized
    for traversal in (
        "verify_project_ir_stage",
        "verify_project_phase62",
        "verify_project_query_block_ir",
        "_combined_topology",
        "_derive_reverse_uses",
        "build_project_query_block_ir_analysis_bundle",
        "build_project_query_block_ir_inspection",
        "evaluate_project_query_block_ir_document",
    ):
        assert f"`{traversal}`" in verification_normalized
    assert "designed graft resistance, not redundancy" in verification_normalized
    assert "below 0.15s" in verification_normalized
    assert "`NOT_MATERIAL`" in verification_normalized
    assert (
        "Independent verification is not weakened, reduced, or reordered"
        in verification_normalized
    )


def test_subprocess_reader_and_xdist_evidence_exist() -> None:
    spec = _read(SPEC)
    children = _section(spec, "Subprocess Attribution")
    readers = _section(spec, "Repository Reader Audit")
    xdist = _section(spec, "Xdist Posture And Load Balance")
    children_normalized = " ".join(children.split())
    readers_normalized = " ".join(readers.split())
    xdist_normalized = " ".join(xdist.split())

    child_header, *child_rows = _table_rows(children)
    assert child_header == (
        "Child command family (`MEASURED`)",
        "Processes",
        "Cumulative child wall",
        "% child wall",
        "Largest child",
    )
    assert len(child_rows) >= 9
    for family in (
        "Phase-58 project-explain differential probe",
        "Phase-62 JOIN differential probe",
        "Phase-60 window differential probe",
        "Phase-59 graph differential probe",
        "Phase-63 query-block IR differential probe",
        "Phase-61 Project-IR differential probe",
        "Isolated interpreter witnesses",
        "`uv build`",
        "`uv pip install`",
    ):
        assert family in children_normalized
    assert "109 parent-launched child processes" in children_normalized
    assert "169.376s cumulative child wall" in children_normalized
    assert "contained in the parent" in children_normalized
    assert "not additive to it" in children_normalized
    assert "fifth of six probe families" in children_normalized
    assert "is **not** the dominant subprocess owner" in children_normalized
    assert (
        "No interpreter, hash-seed, relocation, or installed-wheel witness is "
        "reduced, merged, or removed" in children_normalized
    )

    for operation in (
        "`Path.read_text`",
        "`Path.read_bytes`",
        "`ast.parse`",
        "`Path.glob`",
        "`Path.rglob`",
    ):
        assert operation in readers_normalized
    assert "like-for-like" in readers_normalized
    assert "601 files (179 production, 422 tests)" in readers_normalized
    assert "has **not** materially regressed" in readers_normalized
    assert "No reader is refactored here" in readers_normalized

    assert "Resolved worker count (`MEASURED`) | 7" in xdist_normalized
    assert "Distribution mode (`MEASURED`) | `loadfile`" in xdist_normalized
    assert "3.03x / 43.2%" in xdist_normalized
    assert "at least 49.96s" in xdist_normalized
    assert "at least 51.4%" in xdist_normalized
    assert "`INFERRED`, not separately measured" in xdist_normalized
    assert (
        "No worker count, memory constant, distribution mode, `--maxprocesses` "
        "bound, or serial fallback is changed in this Slice" in xdist_normalized
    )


def test_ranked_owners_and_route_follow_the_measurements() -> None:
    spec = _read(SPEC)
    ranked = _section(spec, "Ranked Cost Attribution")
    route = _section(spec, "Frozen Interlude II Route")
    ranked_normalized = " ".join(ranked.split())
    route_normalized = " ".join(route.split())

    ranked_header, *ranked_rows = _table_rows(ranked)
    assert ranked_header == (
        "Rank",
        "Cost owner",
        "Measurement",
        "Classification",
    )
    assert len(ranked_rows) == 10
    observed_classes = {row[3].strip("`") for row in ranked_rows}
    assert observed_classes <= {*COST_CLASSES, "NOT_MEASURED"}
    assert any(row[3] == "`DOMINANT`" for row in ranked_rows)
    for owner in (
        "Cross-process differential probes",
        "pytest ordinary in-process work",
        "Test Pyright",
        "Production Pyright",
        "Package smoke",
        "Repository/static readers",
        "Semantic / Project construction",
        "Collection / import",
        "Independent verification / analyses",
        "Other validator gates",
    ):
        assert owner in ranked_normalized
    assert "never added to it" in ranked_normalized
    assert "residual aggregate, not a single owner" in ranked_normalized
    assert "honestly `NOT_MEASURED` locally" in ranked_normalized

    route_header, *route_rows = _table_rows(route)
    assert route_header == (
        "Slice",
        "Independent owner",
        "Evidence and terminal metric",
    )
    assert tuple((row[0], row[1]) for row in route_rows) == EXPECTED_ROUTE
    assert 2 <= len(route_rows) <= 6
    assert route_rows[-1][1] == "Completion Benchmark And Phase-64 Readiness Assurance"
    assert "implement no optimization" in route_rows[0][2]
    for deleted in (
        "**Immutable Semantic/IR Snapshot Fixture Reuse** is deleted",
        "**Verification / Derived-Analysis Traversal Optimization** is deleted",
    ):
        assert deleted in route_normalized
    assert "not reopened by default" in route_normalized
    assert "No production semantic change is authorized" in route_normalized
    assert "close `NO_GAIN`" in route_normalized
    assert "Immutable Semantic/IR Snapshot Fixture Reuse" not in " ".join(
        row[1] for row in route_rows
    )


def test_frozen_laws_preserve_identity_and_differential_assurance() -> None:
    spec = _read(SPEC)
    laws = _normalized(spec, "Frozen Optimization And Assurance Laws")

    for law in (
        "same collected tests, with the Slice-1 count of 11487 as a floor",
        "same assertions, diagnostics, diagnostic codes, and ordering",
        "same interpreter, hash-seed, relocation, source-versus-wheel, and "
        "installed-origin witness matrices",
        "same Python 3.12 and Python 3.13 natural CI jobs",
        "same generated, golden, and package-smoke gates",
        "same semantic identities and object-identity closures",
        "same foreign-root, cross-snapshot-ref, and fresh-scope assurance",
        "same tested serial fallback",
        "reuse the *acquisition* of immutable evidence",
        "never reuse a semantic answer merely because expected values happen to match",
        "positive immutable snapshot -> shareable only after evidence and "
        "identity-safety review",
        "foreign identity snapshot -> remains independently constructed",
        "fresh scope test -> remains fresh",
        "mutation test -> remains isolated",
        "remains process-separated unless an exact environmental distinction is "
        "preserved by a proven batched acquisition",
        "No persistent PASS or result cache may be introduced",
        "lock structure, counts, and policy rather than wall-clock budgets",
    ):
        assert law in laws


def test_exact_closure_and_inventory_transition_are_recorded() -> None:
    spec = _read(SPEC)
    closure = _section(spec, "Changed-Path And Lifecycle Lock")
    closure_normalized = " ".join(closure.split())

    assert "`A2/M4/D0`, six paths" in closure_normalized
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

    assert "production Python `179` unchanged" in closure_normalized
    assert "`422 -> 423`" in closure_normalized
    assert (
        "does not scan the current whole-repository Python inventory"
        in closure_normalized
    )
    assert "sole mutable lifecycle-document reader" in closure_normalized
    assert "reads no mutable lifecycle document" in closure_normalized
    assert "Phase 63 = COMPLETED" in closure
    assert "Validation/Test Performance Optimization Interlude II = ACTIVE" in closure
    assert "Interlude II Slice 1 = COMPLETED / PUBLISHED" in closure
    assert "Phase 64 = NEXT / BLOCKED / NOT IMPLEMENTED" in closure
    assert (
        "VALIDATION_PERFORMANCE_INTERLUDE_II_SLICE2_DIFFERENTIAL_PROBE_AND_PROCESS_ACQUISITION_OPTIMIZATION"
        in closure
    )
    assert "Phase 64 is not ACTIVE" in closure_normalized

    own_imports = tuple(
        line
        for line in _read(Path(__file__).resolve()).splitlines()
        if line.startswith(("import ", "from "))
    )
    assert own_imports == EXPECTED_PRINCIPAL_IMPORTS
