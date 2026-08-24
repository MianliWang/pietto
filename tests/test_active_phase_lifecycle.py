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
    ("Phase 58", "`ACTIVE`"),
    ("Slice 1", "`COMPLETED`"),
    ("Slice 2", "`COMPLETED`"),
    ("Slice 3", "`COMPLETED`"),
    ("Slice 4", "`COMPLETED`"),
    ("Slice 5", "`COMPLETED`"),
    ("Slice 6", "`CURRENT`"),
    ("Slice 7", "`NEXT / UNSTARTED`"),
    ("Next", "`PHASE58_SLICE7_END_TO_END`"),
)
EXPECTED_ROADMAP_STATE = (
    "Phase 58 is active, Slices 1–5 are completed, Slice 6 is current, "
    "and Slice 7 is next / unstarted."
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
    assert "Slice 6 is the current route owner" in normalized
    assert "Live Git and natural exact-head CI own Phase 58 Slice 6 completion" in (
        normalized
    )
    assert "does not authorize Slice 7" in normalized


def test_active_roadmap_current_owner_sentence_is_exact() -> None:
    phase58 = _section(_read(ROADMAP), "Phase 58 route").lstrip()
    assert phase58.startswith(f"{EXPECTED_ROADMAP_STATE}\n")
    assert phase58.count(EXPECTED_ROADMAP_STATE) == 1
