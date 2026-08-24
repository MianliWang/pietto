"""Private conservative requirement and project portability derivation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .compatibility_matrix_projection import (
    ProjectExplainCheckedStatus,
    ProjectExplainEvaluationState,
    ProjectExplainMatrixCell,
    ProjectExplainMatrixRow,
    ProjectExplainRequirementTargetMatrix,
    _require_exact_tuple,
    _require_position,
    _validate_projection_references,
)
from .package_requirement_projection import (
    ProjectExplainPackageRequirementProjection,
)

__all__: tuple[str, ...] = ()


class ProjectExplainPortabilityClassification(StrEnum):
    PORTABLE = "portable"
    NOT_PORTABLE = "not_portable"
    INDETERMINATE = "indeterminate"


class ProjectExplainPortabilityReason(StrEnum):
    NO_EVALUATED_TARGETS = "no-evaluated-targets"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainDefiniteGap:
    target_position: int
    status: ProjectExplainCheckedStatus

    def __post_init__(self) -> None:
        _require_position(self.target_position, "definite gap target position")
        if type(self.status) is not ProjectExplainCheckedStatus:
            raise TypeError("Definite gaps require an exact checked status.")
        if self.status not in {
            ProjectExplainCheckedStatus.UNSUPPORTED,
            ProjectExplainCheckedStatus.ABSENT,
        }:
            raise ValueError("Definite gaps require UNSUPPORTED or ABSENT status.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainRequirementPortability:
    requirement_position: int
    classification: ProjectExplainPortabilityClassification
    reason: ProjectExplainPortabilityReason | None
    definite_gaps: tuple[ProjectExplainDefiniteGap, ...]

    def __post_init__(self) -> None:
        _require_position(
            self.requirement_position,
            "portability requirement position",
        )
        _require_classification(self.classification)
        _require_reason(self.reason)
        _require_exact_tuple(
            self.definite_gaps,
            ProjectExplainDefiniteGap,
            "definite gaps",
        )
        if any(
            left.target_position >= right.target_position
            for left, right in zip(
                self.definite_gaps,
                self.definite_gaps[1:],
            )
        ):
            raise ValueError("Definite gaps must retain strict target order.")
        if self.classification is ProjectExplainPortabilityClassification.PORTABLE:
            if self.reason is not None or self.definite_gaps:
                raise ValueError("PORTABLE requirements forbid reasons and gaps.")
            return
        if self.classification is ProjectExplainPortabilityClassification.NOT_PORTABLE:
            if self.reason is not None or not self.definite_gaps:
                raise ValueError("NOT_PORTABLE requirements require definite gaps.")
            return
        if self.definite_gaps:
            raise ValueError("INDETERMINATE requirements forbid definite gaps.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainProjectPortability:
    classification: ProjectExplainPortabilityClassification
    reason: ProjectExplainPortabilityReason | None
    requirements_evaluated: int
    requirements: tuple[ProjectExplainRequirementPortability, ...]

    def __post_init__(self) -> None:
        _require_classification(self.classification)
        _require_reason(self.reason)
        _require_position(
            self.requirements_evaluated,
            "portability requirements evaluated",
        )
        _require_exact_tuple(
            self.requirements,
            ProjectExplainRequirementPortability,
            "requirement portability results",
        )
        if self.requirements_evaluated != len(self.requirements):
            raise ValueError(
                "Requirements evaluated must equal the requirement result count."
            )
        if tuple(
            requirement.requirement_position for requirement in self.requirements
        ) != tuple(range(len(self.requirements))):
            raise ValueError(
                "Requirement portability positions must be dense and ordered."
            )

        if self.reason is ProjectExplainPortabilityReason.NO_EVALUATED_TARGETS:
            if (
                self.classification
                is not ProjectExplainPortabilityClassification.INDETERMINATE
                or any(
                    requirement.classification
                    is not ProjectExplainPortabilityClassification.INDETERMINATE
                    or requirement.reason
                    is not ProjectExplainPortabilityReason.NO_EVALUATED_TARGETS
                    for requirement in self.requirements
                )
            ):
                raise ValueError(
                    "No-target project results require matching indeterminate rows."
                )
            return

        if any(requirement.reason is not None for requirement in self.requirements):
            raise ValueError(
                "A project without a reason cannot contain reasoned requirements."
            )
        expected = _aggregate_project_classification(self.requirements)
        if self.classification is not expected:
            raise ValueError(
                "Project classification must aggregate requirement results."
            )


def _derive_project_portability(
    package_projection: ProjectExplainPackageRequirementProjection,
    matrix_projection: ProjectExplainRequirementTargetMatrix,
) -> ProjectExplainProjectPortability:
    """Derive conservative portability from exact detached Slice 3 and 4 values."""

    _require_projection_alignment(package_projection, matrix_projection)
    target_count = len(matrix_projection.targets)
    requirements: list[ProjectExplainRequirementPortability] = []
    for request, row in zip(
        package_projection.requirements,
        matrix_projection.rows,
        strict=True,
    ):
        if target_count == 0:
            requirements.append(
                ProjectExplainRequirementPortability(
                    requirement_position=request.position,
                    classification=(
                        ProjectExplainPortabilityClassification.INDETERMINATE
                    ),
                    reason=ProjectExplainPortabilityReason.NO_EVALUATED_TARGETS,
                    definite_gaps=(),
                )
            )
            continue

        definite_gaps: list[ProjectExplainDefiniteGap] = []
        for cell in row.cells:
            status = cell.checked_status
            if cell.state is ProjectExplainEvaluationState.CHECKED and (
                status is ProjectExplainCheckedStatus.UNSUPPORTED
                or status is ProjectExplainCheckedStatus.ABSENT
            ):
                definite_gaps.append(
                    ProjectExplainDefiniteGap(
                        target_position=cell.target_position,
                        status=status,
                    )
                )
        gaps = tuple(definite_gaps)
        if gaps:
            classification = ProjectExplainPortabilityClassification.NOT_PORTABLE
        elif all(
            cell.state is ProjectExplainEvaluationState.CHECKED
            and cell.checked_status is ProjectExplainCheckedStatus.SATISFIED
            for cell in row.cells
        ):
            classification = ProjectExplainPortabilityClassification.PORTABLE
        else:
            classification = ProjectExplainPortabilityClassification.INDETERMINATE
        requirements.append(
            ProjectExplainRequirementPortability(
                requirement_position=request.position,
                classification=classification,
                reason=None,
                definite_gaps=gaps,
            )
        )

    requirement_results = tuple(requirements)
    if target_count == 0:
        classification = ProjectExplainPortabilityClassification.INDETERMINATE
        reason = ProjectExplainPortabilityReason.NO_EVALUATED_TARGETS
    else:
        classification = _aggregate_project_classification(requirement_results)
        reason = None
    return ProjectExplainProjectPortability(
        classification=classification,
        reason=reason,
        requirements_evaluated=len(requirement_results),
        requirements=requirement_results,
    )


def _require_projection_alignment(
    package_projection: ProjectExplainPackageRequirementProjection,
    matrix_projection: ProjectExplainRequirementTargetMatrix,
) -> None:
    if type(package_projection) is not ProjectExplainPackageRequirementProjection:
        raise TypeError("Slice 6 requires an exact Slice 3 projection.")
    if type(matrix_projection) is not ProjectExplainRequirementTargetMatrix:
        raise TypeError("Slice 6 requires an exact Slice 4 matrix.")
    if len(matrix_projection.rows) != len(package_projection.requirements):
        raise ValueError("Slice 6 requires one matrix row per Slice 3 requirement.")
    if tuple(target.position for target in matrix_projection.targets) != tuple(
        range(len(matrix_projection.targets))
    ):
        raise ValueError("Slice 6 requires dense evaluated target order.")
    target_positions = tuple(range(len(matrix_projection.targets)))
    for position, (request, row) in enumerate(
        zip(
            package_projection.requirements,
            matrix_projection.rows,
            strict=True,
        )
    ):
        if (
            type(row) is not ProjectExplainMatrixRow
            or request.position != position
            or row.requirement_position != request.position
        ):
            raise ValueError(
                "Slice 6 matrix rows must retain exact Slice 3 requirement order."
            )
        if tuple(cell.target_position for cell in row.cells) != target_positions or any(
            type(cell) is not ProjectExplainMatrixCell for cell in row.cells
        ):
            raise ValueError("Slice 6 matrix cells must retain exact target order.")
    _validate_projection_references(matrix_projection, package_projection)


def _aggregate_project_classification(
    requirements: tuple[ProjectExplainRequirementPortability, ...],
) -> ProjectExplainPortabilityClassification:
    if any(
        requirement.classification
        is ProjectExplainPortabilityClassification.NOT_PORTABLE
        for requirement in requirements
    ):
        return ProjectExplainPortabilityClassification.NOT_PORTABLE
    if any(
        requirement.classification
        is ProjectExplainPortabilityClassification.INDETERMINATE
        for requirement in requirements
    ):
        return ProjectExplainPortabilityClassification.INDETERMINATE
    return ProjectExplainPortabilityClassification.PORTABLE


def _require_classification(value: object) -> None:
    if type(value) is not ProjectExplainPortabilityClassification:
        raise TypeError("Portability results require an exact classification.")


def _require_reason(value: object | None) -> None:
    if value is not None and type(value) is not ProjectExplainPortabilityReason:
        raise TypeError("Portability results require an exact reason.")
