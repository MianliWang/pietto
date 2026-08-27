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
    ("Phase 59", "`ACTIVE`"),
    ("Slice 1", "`COMPLETED`"),
    ("Slice 2", "`COMPLETED`"),
    ("Slice 3", "`COMPLETED`"),
    ("Slice 4", "`COMPLETED`"),
    ("Slice 5", "`COMPLETED`"),
    ("Slice 6", "`COMPLETED`"),
    ("Slice 7", "`COMPLETED`"),
    ("Slice 8", "`COMPLETED`"),
    ("Slice 9", "`COMPLETED`"),
    ("Slice 10", "`CURRENT`"),
    ("Slice 11", "`NEXT / UNSTARTED`"),
    (
        "Next",
        "`PHASE59_SLICE11_DIFFERENTIAL_COMPATIBILITY_ASSURANCE_END_TO_END`",
    ),
)
EXPECTED_PHASE58_STATE = "All 17 slices are completed. Phase 58 is complete."
EXPECTED_PHASE59_STATE = (
    "Phase 59 is active, Slices 1–9 are completed, Slice 10 is current, and "
    "Slice 11 is next / unstarted. The published route has exactly 12 slices."
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
    assert (
        "Slice 10 is the current real multi-package provenance and lineage E2E owner"
        in normalized
    )
    assert "Live Git and natural exact-head CI own Phase 59 Slice 10 completion" in (
        normalized
    )
    assert "does not authorize Slice 11" in normalized


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
