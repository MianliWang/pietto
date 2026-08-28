from __future__ import annotations

from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[1]
ROADMAP = REPO_ROOT / "docs/roadmap.md"
STATUS = REPO_ROOT / "docs/status.md"
SLICE6_SPEC = (
    REPO_ROOT
    / "docs/spec/validation-performance-interlude-slice6-completion-benchmark-phase60-readiness-v1.md"
)
PHASE60_SLICE1_SPEC = (
    REPO_ROOT
    / "docs/spec/phase60-advanced-windows-scope-semantic-laws-route-lock-v1.md"
)
PUBLISHED_INTERLUDE = (
    (
        "cc9884d1f24c9f1a8199fbdf0e20d48533e056d4",
        "ec0d5086f45ef72c49403a718ed45c45a8c44c30",
        "6a3d5d54ce728b60985718ed7b867721a1680f13",
        "33070069266",
        "Establish validation performance baseline",
    ),
    (
        "b6191d790040233a5ad62de7549c36bc0a555d9c",
        "874511592c4eee2b6ef024146b0017c335cd4ab4",
        "cc9884d1f24c9f1a8199fbdf0e20d48533e056d4",
        "33121173872",
        "Optimize differential probe execution",
    ),
    (
        "3f35fd31a1799bb12b8b74108ade64438c85b435",
        "a1a96e1d9a1b2f1ff2692661e773573711475091",
        "b6191d790040233a5ad62de7549c36bc0a555d9c",
        "33139945770",
        "Reuse repository fact acquisition",
    ),
    (
        "333f5ec5b8ef4e2cc1b5f79b108ee1857b1fe842",
        "e7bbd107151db075d63fe1742650eb1fd37dcbd7",
        "3f35fd31a1799bb12b8b74108ade64438c85b435",
        "33146266899",
        "Record static analysis no-gain closure",
    ),
    (
        "df7fe30381aa0c690b132b829627a11e971c0c59",
        "6f9aff8ddcf6e51fc28161ba18b5e1da55816de6",
        "333f5ec5b8ef4e2cc1b5f79b108ee1857b1fe842",
        "33151724681",
        "Adopt resource-aware xdist scheduling",
    ),
)
INTERLUDE_COMPLETION = (
    "e6da1fbe6b18ad88ae3c09568ba1f7d0e76817d1",
    "16d5618006e5c84a202300f0c69ea462dc9d8084",
    "df7fe30381aa0c690b132b829627a11e971c0c59",
    "33155753995",
    "Complete validation performance interlude",
)

EXPECTED_STATUS = (
    ("Package and CLI", "`0.1.0`"),
    ("Phase 55", "`COMPLETED`"),
    ("Phase 56", "`COMPLETED`"),
    ("Phase 57", "`COMPLETED`"),
    ("Phase 58", "`COMPLETED`"),
    ("Phase 59", "`COMPLETED`"),
    ("Validation/Test Performance Optimization Interlude", "`COMPLETED`"),
    ("Phase 60", "`ACTIVE`"),
    ("Slice 1", "`CURRENT`"),
    ("Slice 2", "`NEXT / UNSTARTED`"),
    (
        "Next",
        "`PHASE60_SLICE2_AUTHORED_TO_RESOLVED_WINDOW_AND_FRAME_MODEL_END_TO_END`",
    ),
)
EXPECTED_PHASE58_STATE = "All 17 slices are completed. Phase 58 is complete."
EXPECTED_PHASE59_STATE = (
    "Phase 59 and all 12 Phase 59 Slices are completed. The Validation/Test\n"
    "Performance Optimization Interlude is also completed by successful natural\n"
    "exact-head CI on its Slice 6 commit, which activates Phase 60. The published\n"
    "Phase 59 route has exactly 12 slices."
)
EXPECTED_PHASE59_OWNER = "Local package graph, attribution, provenance, and lineage"
EXPECTED_PHASE60_STATE = (
    "Phase 60 is active, Slice 1 is current, and Slice 2 is next / unstarted. The\n"
    "published route has exactly 13 slices."
)
EXPECTED_PHASE60_OWNER = "Advanced Windows And Phase 51–60 Readiness Checkpoint"
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
    ("4", "Validator Static-Analysis Stage Optimization Investigation"),
    (
        "5",
        "Current-Suite Isolation, Resource-Aware Xdist Scheduling, And CI Parallelism Decision",
    ),
    ("6", "Completion Benchmark And Phase 60 Readiness Assurance"),
)
EXPECTED_PHASE60_ROUTE = (
    ("1", "Scope / Semantic Laws / Route Lock"),
    ("2", "Authored-To-Resolved Window And Frame Model"),
    (
        "3",
        "Structural Legality, Function-Frame Policy, Empty-Frame Classification, And Stage/Nesting Rules",
    ),
    ("4", "ROWS Semantics And Lowering"),
    (
        "5",
        "RANGE Semantics, Direction-Aware Bounds, Structural ORDER BY/Type Seam, And Lowering",
    ),
    ("6", "GROUPS And Peer-Group Semantics And Lowering"),
    ("7", "EXCLUDE Semantics Across All Units"),
    ("8", "Query-Local Named-Window Scope And DAG Inheritance"),
    ("9", "Value/Navigation Modifiers"),
    (
        "10",
        "Capability-Gated Lowering, Lineage, Determinism/Private Inspection, And Semantic-Equivalence Readiness",
    ),
    ("11", "Real Authored Advanced-Window E2E"),
    ("12", "Differential Compatibility"),
    ("13", "Phase 51–60 Completion/Readiness Audit And Phase 61 Handoff"),
)
EXPECTED_RETAINED_LATER_OWNERS = (
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
EXPECTED_INTERLUDE_SLICE6_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/validation-performance-interlude-slice6-completion-benchmark-phase60-readiness-v1.md",
    "docs/status.md",
    "tests/test_active_phase_lifecycle.py",
)
EXPECTED_PHASE60_SLICE1_CHANGED_PATHS = (
    "docs/roadmap.md",
    "docs/spec/phase60-advanced-windows-scope-semantic-laws-route-lock-v1.md",
    "docs/status.md",
    "tests/test_active_phase_lifecycle.py",
    "tests/test_phase60_slice1_advanced_windows_scope_semantic_laws_route_lock.py",
    "tests/test_validation_performance_interlude_slice3_repository_reader_acquisition_reuse.py",
    "tests/test_workflow_lifecycle_validation_efficiency.py",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _git(*arguments: str) -> str:
    result = subprocess.run(
        ("git", *arguments),
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    assert result.stderr == ""
    return result.stdout.strip()


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
    assert (
        "Phase 59 and the Validation/Test Performance Optimization Interlude are "
        "completed by live Git and successful natural exact-head CI" in normalized
    )
    assert "Slice 1 is the current Phase 60 architecture owner" in normalized
    assert "Live Git and natural exact-head CI own Slice 1 completion" in normalized
    assert "no post-CI status-flip commit is required" in normalized
    assert "does not authorize Slice 2" in normalized


def test_active_roadmap_current_owner_sentence_and_routes_are_exact() -> None:
    roadmap = _read(ROADMAP)
    phase58 = _section(roadmap, "Phase 58 route").lstrip()
    phase59 = _section(roadmap, "Phase 59 route").lstrip()
    phase60 = _section(roadmap, "Phase 60 route").lstrip()
    assert phase58.startswith(f"{EXPECTED_PHASE58_STATE}\n")
    assert phase58.count(EXPECTED_PHASE58_STATE) == 1
    assert _table_rows(phase58)[1:] == EXPECTED_PHASE58_ROUTE
    assert phase59.startswith(f"{EXPECTED_PHASE59_STATE}\n")
    assert phase59.count(EXPECTED_PHASE59_STATE) == 1
    assert phase59.count(EXPECTED_PHASE59_OWNER) == 1
    assert _table_rows(phase59)[1:] == EXPECTED_PHASE59_ROUTE
    assert phase60.startswith(f"{EXPECTED_PHASE60_STATE}\n")
    assert phase60.count(EXPECTED_PHASE60_STATE) == 1
    assert phase60.count(EXPECTED_PHASE60_OWNER) == 1
    assert _table_rows(phase60)[1:] == EXPECTED_PHASE60_ROUTE
    assert "phase60-advanced-windows-scope-semantic-laws-route-lock-v1.md" in phase60
    assert "Current public language and SQL behavior remain frame free" in phase60
    assert "Slice 2 remains unimplemented and unauthorized" in phase60

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
    assert "Fresh collection is 2.99s for 10,352 tests" in interlude_normalized
    assert "serial runs have a 135.21s median" in interlude_normalized
    assert "parallel runs have a 74.60s median" in interlude_normalized
    assert "a like-for-like 44.8% reduction" in interlude_normalized
    assert "Interlude self-owned-open = 0" in interlude_normalized
    assert (
        "Successful natural exact-head CI on the single Slice 6 completion commit "
        "completed the Interlude and handed off authority" in interlude_normalized
    )
    assert "Phase 60 is now `ACTIVE`" in interlude_normalized
    assert "Slice 1 is current, and Slice 2 is next / unstarted" in (
        interlude_normalized
    )
    assert len(EXPECTED_INTERLUDE_SLICE6_CHANGED_PATHS) == 4
    assert all(
        (REPO_ROOT / path).is_file() for path in EXPECTED_INTERLUDE_SLICE6_CHANGED_PATHS
    )
    assert not any(
        path.startswith((".github/", "src/", "scripts/", "grammar/"))
        for path in EXPECTED_INTERLUDE_SLICE6_CHANGED_PATHS
    )


def test_published_interlude_chain_matches_git_and_completion_evidence() -> None:
    document = SLICE6_SPEC.read_text(encoding="utf-8")
    for commit, tree, _parent, run_id, subject in PUBLISHED_INTERLUDE:
        for value in (commit, tree, run_id, subject):
            assert value in document

    phase60 = PHASE60_SLICE1_SPEC.read_text(encoding="utf-8")
    (
        completion_commit,
        completion_tree,
        completion_parent,
        completion_run,
        completion_subject,
    ) = INTERLUDE_COMPLETION
    for value in (completion_commit, completion_run, completion_subject):
        assert value in phase60

    if _git("rev-parse", "--is-shallow-repository") == "true":
        return

    for commit, tree, parent, _run_id, subject in PUBLISHED_INTERLUDE:
        assert _git("show", "-s", "--format=%T", commit) == tree
        assert _git("show", "-s", "--format=%P", commit) == parent
        assert _git("show", "-s", "--format=%s", commit) == subject
    assert _git("show", "-s", "--format=%T", completion_commit) == completion_tree
    assert _git("show", "-s", "--format=%P", completion_commit) == completion_parent
    assert _git("show", "-s", "--format=%s", completion_commit) == completion_subject


def test_interlude_scorecard_self_owned_open_and_phase60_handoff_are_exact() -> None:
    document = " ".join(SLICE6_SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "Interlude self-owned-open = 0",
        "2.99s",
        "132.55s",
        "137.86s",
        "135.21s",
        "79.39s",
        "69.80s",
        "74.60s",
        "60.61s, or 44.8%",
        "116 -> 58",
        "2412 -> 483",
        "1661 -> 484",
        "53.13s -> 52.94s / 0.36%",
        "not owned; not adopted",
        "Phase 60 — Advanced Windows And Phase 51–60 Readiness Checkpoint",
        "Phase 60 implementation = NOT STARTED",
    ):
        assert evidence in document

    forbidden_markers = ("TO" + "DO", "FIX" + "ME")
    interlude_specs = tuple(
        sorted(
            (REPO_ROOT / "docs/spec").glob("validation-performance-interlude-slice*.md")
        )
    )
    assert len(interlude_specs) == 6
    assert not any(
        marker in path.read_text(encoding="utf-8")
        for path in interlude_specs
        for marker in forbidden_markers
    )
    assert EXPECTED_PHASE60_OWNER == (
        "Advanced Windows And Phase 51–60 Readiness Checkpoint"
    )
    assert EXPECTED_RETAINED_LATER_OWNERS[0] == (
        "61",
        "Project IR and semantic composition",
    )


def test_phase60_slice1_changed_paths_are_exact() -> None:
    assert len(EXPECTED_PHASE60_SLICE1_CHANGED_PATHS) == 7
    assert all(
        (REPO_ROOT / path).is_file() for path in EXPECTED_PHASE60_SLICE1_CHANGED_PATHS
    )
    assert not any(
        path.startswith((".github/", "src/", "scripts/", "grammar/"))
        for path in EXPECTED_PHASE60_SLICE1_CHANGED_PATHS
    )
