from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from pietto._project import project_relationship_match_guarantees as guarantees
from pietto._project.model import ProjectSemanticResult
from pietto.semantic.model import SemanticModel

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice8-referential-coverage-match-simple-full-directional-match-guarantees-v1.md"
)


def test_match_simple_and_full_null_applicability_are_distinct() -> None:
    simple = guarantees.ProjectReferentialMatchPolicy.MATCH_SIMPLE
    full = guarantees.ProjectReferentialMatchPolicy.MATCH_FULL
    assert guarantees.classify_match_applicability(simple, (False, False)) is (
        guarantees.ProjectMatchApplicability.REQUIRES_MATCH
    )
    assert guarantees.classify_match_applicability(simple, (True, False)) is (
        guarantees.ProjectMatchApplicability.NOT_APPLICABLE_SOURCE_NULL
    )
    assert guarantees.classify_match_applicability(full, (True, True)) is (
        guarantees.ProjectMatchApplicability.NULL_REFERENCE_ACCEPTED
    )
    assert guarantees.classify_match_applicability(full, (True, False)) is (
        guarantees.ProjectMatchApplicability.MIXED_NULL_VIOLATION
    )
    assert guarantees.classify_match_applicability(full, (False, False)) is (
        guarantees.ProjectMatchApplicability.REQUIRES_MATCH
    )


def test_private_closed_vocabulary_and_public_boundaries() -> None:
    assert tuple(guarantees.ProjectRelationshipMinimumBound) == (
        guarantees.ProjectRelationshipMinimumBound.ZERO_ALLOWED,
        guarantees.ProjectRelationshipMinimumBound.AT_LEAST_ONE,
    )
    assert tuple(guarantees.ProjectReferentialMatchPolicy) == (
        guarantees.ProjectReferentialMatchPolicy.MATCH_SIMPLE,
        guarantees.ProjectReferentialMatchPolicy.MATCH_FULL,
    )
    assert guarantees.__all__ == ()
    assert "match_guarantees" not in {
        item.name for item in fields(ProjectSemanticResult)
    }
    assert "match_guarantees" not in {item.name for item in fields(SemanticModel)}


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
