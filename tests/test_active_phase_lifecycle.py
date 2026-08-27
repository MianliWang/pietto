from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ROADMAP = REPO_ROOT / "docs/roadmap.md"
STATUS = REPO_ROOT / "docs/status.md"

EXPECTED_STATUS = (
    ("Package and CLI", "`0.1.0`"),
    ("Phase 55", "`COMPLETED`"),
    ("Phase 56", "`COMPLETED`"),
    ("Phase 57", "`COMPLETED`"),
    ("Phase 58", "`COMPLETED`"),
    ("Phase 59", "`COMPLETED`"),
    ("Slice 1", "`COMPLETED`"),
    ("Slice 2", "`COMPLETED`"),
    ("Slice 3", "`COMPLETED`"),
    ("Slice 4", "`COMPLETED`"),
    ("Slice 5", "`COMPLETED`"),
    ("Slice 6", "`COMPLETED`"),
    ("Slice 7", "`COMPLETED`"),
    ("Slice 8", "`COMPLETED`"),
    ("Slice 9", "`COMPLETED`"),
    ("Slice 10", "`COMPLETED`"),
    ("Slice 11", "`COMPLETED`"),
    ("Slice 12", "`COMPLETED`"),
    (
        "Validation/Test Performance Optimization Interlude",
        "`ACTIVE`",
    ),
    ("Interlude Slice 1", "`COMPLETED`"),
    ("Interlude Slice 2", "`CURRENT / PUBLICATION CANDIDATE`"),
    ("Interlude Slice 3", "`NEXT / UNSTARTED`"),
    ("Phase 60", "`BLOCKED / NOT ACTIVATED`"),
    (
        "Next",
        "`VALIDATION_PERFORMANCE_INTERLUDE_SLICE3_REPOSITORY_READER_ACQUISITION_REUSE`",
    ),
)
EXPECTED_PHASE58_STATE = "All 17 slices are completed. Phase 58 is complete."
EXPECTED_PHASE59_STATE = (
    "Phase 59 is completed, all 12 Phase 59 Slices are completed, the Validation/\n"
    "Test Performance Optimization Interlude is active with Slice 1 published\n"
    "complete, Slice 2 as its current publication candidate, Slice 3 next /\n"
    "unstarted, and Phase 60 blocked / not activated. The published Phase 59 route\n"
    "has exactly 12 slices."
)
EXPECTED_PHASE59_OWNER = "Local package graph, attribution, provenance, and lineage"
EXPECTED_PHASE58_ROUTE = (
    (
        "1",
        "Architecture/scope/route lock; artifact identity; target denominator; single-file explain compatibility",
    ),
    (
        "2",
        "Public common model and success/failure envelope; logical paths; evidence posture; request/resolution/result vocabulary",
    ),
    (
        "3",
        "Package and requirement provenance projection; `declared_by`/`requested_by`",
    ),
    (
        "4",
        "Public requirement/target compatibility matrix; evaluation states; five checked statuses and reasons",
    ),
    (
        "5",
        "Public extension-catalog evidence projection; catalog coordinate/target/digest; selection; matchability/exposure; bounded provenance",
    ),
    ("6", "Conservative requirement/project portability derivation"),
    (
        "7",
        "Cross-section composition; artifact-local references; integrity; deterministic ordering; authority separation",
    ),
    (
        "8",
        "Public JSON v1 schema; deterministic serialization; success/failure envelopes; privacy and schema-evolution locks",
    ),
    ("9", "Runtime authority architecture and evidence-backed route expansion lock"),
    ("10", "Package-owned capability requirement declaration authority"),
    (
        "11",
        "Project-owned evaluated-target, profile, and catalog-availability authority",
    ),
    ("12", "Package-owned extension-signature typed physical selector authority"),
    ("13", "Project Explain runtime authority builder and zero-context adaptation"),
    (
        "14",
        "`pietto explain --project` text/JSON integration; existing single-file explain zero-delta",
    ),
    (
        "15",
        "Reachability-aware real multi-target E2E plus structural and direct-owner assurance for currently unreachable generic states",
    ),
    (
        "16",
        "Public pure/differential compatibility boundary; goldens; Python 3.12/3.13; hash seed; relocation; installed wheel",
    ),
    (
        "17",
        "Completion audit; Phase 59 handoff; Phase 60/64/67/69 readiness reconciliation",
    ),
)
EXPECTED_PHASE59_ROUTE = (
    ("1", "Graph Domains, Identity Laws, And Route Lock"),
    ("2", "Private Package Graph Model And Snapshot Identity"),
    ("3", "Canonical Package Graph Construction"),
    ("4", "Requirement And Selector Attribution"),
    ("5", "Capability, Catalog, And Typed Negative Evidence Provenance"),
    ("6", "Direct, Transitive, And Why-Not Provenance"),
    ("7", "Package-to-Module Attribution Bridge"),
    ("8", "Semantic And Field-Lineage Integration"),
    (
        "9",
        "Private Graph Integrity, Inspection, Query, And Canonical Pure Boundary",
    ),
    ("10", "Real Multi-Package Provenance And Lineage E2E"),
    ("11", "Differential Compatibility Assurance"),
    ("12", "Completion Audit And Phase 60 Handoff"),
)
EXPECTED_INTERLUDE_ROUTE = (
    ("1", "Baseline Profiling, Cost Attribution, And Route Lock"),
    ("2", "Differential Probe Runtime Decomposition And Optimization"),
    ("3", "Repository Reader Acquisition Reuse"),
    ("4", "Validator Static-Analysis Stage Optimization"),
    ("5", "Current-Suite Isolation Audit And Xdist Decision"),
    ("6", "Completion Benchmark And Phase 60 Readiness Assurance"),
)
EXPECTED_RETAINED_LATER_OWNERS = (
    ("60", "Advanced windows and Phase 51–60 readiness checkpoint"),
    ("61", "Project IR and semantic composition"),
    ("62", "Relationship, JOIN, grain, and fanout-safe semantics"),
    ("63", "Multi-relation SQL, project emit-SQL, and QUALIFY lowering"),
    ("64", "Advanced types, coercion, temporal, Decimal, and native mapping"),
    ("65", "Advanced aggregation and grouping"),
    ("66", "Advanced module and semantic-package assets"),
    ("67", "Remote package manager and trust boundary"),
    ("68", "Dependency solver, canonical lockfile, and first Rust kernel decision"),
    (
        "69",
        "Release-aware PostgreSQL core builtin signature catalog, backend-specific core catalog foundations, generated/multi-source extension catalog assembly, extension-specific lowering, and additional dialect foundations",
    ),
    ("70", "Public schema/lineage expansion and v0.2 release-readiness decision"),
)
EXPECTED_INTERLUDE_SLICE2_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/validation-performance-interlude-slice2-differential-probe-runtime-decomposition-optimization-v1.md",
    "docs/status.md",
    "tests/_pietto_phase59_graph_differential_probe.py",
    "tests/_pietto_project_explain_differential_probe.py",
    "tests/_pietto_project_explain_scenarios.py",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_validation_performance_interlude_slice2_differential_probe_runtime_decomposition_optimization.py",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _section(document: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert document.count(marker) == 1
    start = document.index(marker) + len(marker)
    end = document.find("\n## ", start)
    return document[start:] if end == -1 else document[start:end]


def _table_rows(document: str) -> tuple[tuple[str, ...], ...]:
    return tuple(
        tuple(cell.strip() for cell in line.strip("|").split("|"))
        for line in document.splitlines()
        if line.startswith("| ") and not line.startswith("| ---")
    )


def test_active_status_table_and_authority_prose_are_exact() -> None:
    status = _read(STATUS)
    assert _table_rows(status)[1:] == EXPECTED_STATUS
    normalized = " ".join(status.split())
    assert "Phase 59 is completed by live Git" in normalized
    assert "Interlude Slice 1 is published complete" in normalized
    assert "Slice 2 is the current publication candidate" in normalized
    assert "natural exact-head CI on the single Slice 2 commit" in normalized
    assert "Repository Reader Acquisition Reuse next" in normalized
    assert "no post-CI status-flip commit is required" in normalized
    assert "performance interlude is active" in normalized
    assert "Phase 60 remains blocked and not activated" in normalized


def test_active_roadmap_current_owner_sentence_and_routes_are_exact() -> None:
    roadmap = _read(ROADMAP)
    phase58 = _section(roadmap, "Phase 58 route").lstrip()
    phase59 = _section(roadmap, "Phase 59 route").lstrip()
    assert phase58.startswith(f"{EXPECTED_PHASE58_STATE}\n")
    assert phase58.count(EXPECTED_PHASE58_STATE) == 1
    assert _table_rows(phase58)[1:] == EXPECTED_PHASE58_ROUTE
    assert phase59.startswith(f"{EXPECTED_PHASE59_STATE}\n")
    assert phase59.count(EXPECTED_PHASE59_STATE) == 1
    assert phase59.count(EXPECTED_PHASE59_OWNER) == 1
    assert _table_rows(phase59)[1:] == EXPECTED_PHASE59_ROUTE

    retained = _section(roadmap, "Retained later ownership")
    assert _table_rows(retained)[1:] == EXPECTED_RETAINED_LATER_OWNERS
    interlude = _section(
        roadmap,
        "Validation/Test Performance Optimization Interlude",
    )
    interlude_normalized = " ".join(interlude.split())
    assert (
        "Phase 59 completion -> Validation/Test Performance Optimization Interlude "
        "-> Phase 60 activation" in interlude_normalized
    )
    assert (
        "evidence-backed optimization of Pietto's test/validation runtime without "
        "weakening validation semantics or deterministic authority"
        in interlude_normalized
    )
    assert _table_rows(interlude)[1:] == EXPECTED_INTERLUDE_ROUTE
    assert "RepositoryTestIndex" not in interlude_normalized
    assert "only partially supported" in interlude_normalized
    assert "Differential Probe Runtime Decomposition And Optimization" in (
        interlude_normalized
    )
    assert "All 18 outer variants, 116 semantic CLI calls" in interlude_normalized
    assert "materially beyond observed noise" in interlude_normalized
    assert "Slice 3 is next / unstarted" in interlude_normalized
    assert (
        "Natural CI and the authoritative local validator remain serial"
        in interlude_normalized
    )
    assert "Phase 60 is `BLOCKED / NOT ACTIVATED`" in interlude_normalized
    assert len(EXPECTED_INTERLUDE_SLICE2_CHANGED_PATHS) == 8
    assert all(
        (REPO_ROOT / path).is_file() for path in EXPECTED_INTERLUDE_SLICE2_CHANGED_PATHS
    )
    assert not any(
        path.startswith((".github/", "src/", "scripts/", "grammar/"))
        for path in EXPECTED_INTERLUDE_SLICE2_CHANGED_PATHS
    )
