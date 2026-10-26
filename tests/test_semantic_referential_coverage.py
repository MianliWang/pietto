from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice8-referential-coverage-match-simple-full-directional-match-guarantees-v1.md"
)


def test_contract_locks_direction_coverage_bounds_and_handoff() -> None:
    normalized = " ".join(SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "01e3c910ec29f85a4b31e4d1a9dcfa6571d19af1",
        "35f040a8c12d2244d8007dd3b367be67a81344bf",
        "33498869865",
        "A3/M5/D0",
        "UNBOUNDED_BY_ONE != proof that multiple matches exist",
        "target key / FD != referential coverage != existence proof",
        "MATCH_SIMPLE",
        "MATCH_FULL",
        "ZERO_ALLOWED != proof that an unmatched row exists",
        "Phase 62 Slice 9 = NEXT / NOT IMPLEMENTED",
        "Add Phase 62 directional relationship match guarantees",
    ):
        assert evidence in normalized
