"""Phase 64 Slice 1 product gate, source audit, architecture and route-lock principal."""

from __future__ import annotations

from pietto._project.project_bag_null_oracle import (
    ProjectBagNullEntry,
    ProjectBagNullEqualityCorrespondence,
    ProjectBagNullJoinKind,
    ProjectBagNullJoinSpecification,
    ProjectBagNullRow,
    ProjectFiniteBag,
    evaluate_project_bag_null_join,
    project_bag_int,
)

# Historical facts: exact member sets frozen at the immutable baseline only.
# Historical facts: member presence frozen at the immutable baseline only.
# Durable laws: existing members must survive every future legal extension.


def _bag(*rows: tuple[int, ...]) -> ProjectFiniteBag:
    return ProjectFiniteBag(
        entries=tuple(
            ProjectBagNullEntry(
                row=ProjectBagNullRow(
                    values=tuple(project_bag_int(value) for value in row)
                ),
                multiplicity=1,
            )
            for row in rows
        )
    )


def _join(
    kind: ProjectBagNullJoinKind,
    left: ProjectFiniteBag,
    right: ProjectFiniteBag,
    *,
    left_width: int,
    right_width: int,
    pairs: tuple[tuple[int, int], ...],
) -> ProjectFiniteBag:
    return evaluate_project_bag_null_join(
        ProjectBagNullJoinSpecification(
            kind=kind,
            left_width=left_width,
            right_width=right_width,
            correspondences=tuple(
                ProjectBagNullEqualityCorrespondence(
                    left_position=left_position,
                    right_position=right_position,
                )
                for left_position, right_position in pairs
            ),
        ),
        left,
        right,
    )


def _total(bag: ProjectFiniteBag) -> int:
    return sum(entry.multiplicity for entry in bag.entries)


def test_stepwise_whole_path_and_required_hop_multiplicities_are_reproduced() -> None:
    """Reproduce C01 through the existing bounded BAG/NULL oracle."""

    a = _bag((1,))
    b = _bag((1, 10), (1, 11))
    empty_c = ProjectFiniteBag(entries=())

    a_left_b = _join(
        ProjectBagNullJoinKind.LEFT,
        a,
        b,
        left_width=1,
        right_width=2,
        pairs=((0, 0),),
    )
    assert _total(a_left_b) == 2

    stepwise = _join(
        ProjectBagNullJoinKind.LEFT,
        a_left_b,
        empty_c,
        left_width=3,
        right_width=2,
        pairs=((2, 0),),
    )
    required = _join(
        ProjectBagNullJoinKind.INNER,
        a_left_b,
        empty_c,
        left_width=3,
        right_width=2,
        pairs=((2, 0),),
    )
    b_inner_c = _join(
        ProjectBagNullJoinKind.INNER,
        b,
        empty_c,
        left_width=2,
        right_width=2,
        pairs=((1, 0),),
    )
    whole_path = _join(
        ProjectBagNullJoinKind.LEFT,
        a,
        b_inner_c,
        left_width=1,
        right_width=4,
        pairs=((0, 0),),
    )

    assert (_total(stepwise), _total(whole_path), _total(required)) == (2, 1, 0)
