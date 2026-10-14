from __future__ import annotations

from pathlib import Path

import _pietto_project_explain_matrix as matrix_helpers
import _pietto_project_explain_requirements as requirement_helpers
from pietto._project_explain.compatibility_matrix_projection import (
    ProjectExplainCheckedStatus,
    ProjectExplainEvaluatedTarget,
    ProjectExplainEvaluationState,
    ProjectExplainMatrixBlocker,
    ProjectExplainMatrixBlockerKind,
    ProjectExplainMatrixCell,
    ProjectExplainMatrixRow,
    ProjectExplainPackageTargetEvaluation,
    ProjectExplainRequirementTargetMatrix,
)
from pietto._project_explain.model import ProjectExplainEvidencePosture
from pietto._project_explain.package_requirement_projection import (
    ProjectExplainPackageRequirementProjection,
)
from pietto.semantic.capability_facts import CapabilityDomain, CapabilityKey


type CellOutcome = ProjectExplainCheckedStatus | None


def _package_projection(
    root: Path,
    requirement_count: int,
) -> ProjectExplainPackageRequirementProjection:
    keys = tuple(
        CapabilityKey(CapabilityDomain.LOGICAL_TYPE, subject=f"Type{position}")
        for position in range(requirement_count)
    )
    return requirement_helpers._projection(
        root,
        project=requirement_helpers._requirements("project", "requirements", *keys),
    )


def _target(position: int) -> ProjectExplainEvaluatedTarget:
    profile = matrix_helpers._simple_profile(name=f"base-{position}")
    return ProjectExplainEvaluatedTarget(
        position=position,
        database_family="PostgreSQL",
        database_release="16",
        base_profile=profile,
        supplied_overlays=(),
        dependency_order=(profile,),
    )


def _evaluation(
    package_position: int,
    target: ProjectExplainEvaluatedTarget,
    state: ProjectExplainEvaluationState,
) -> ProjectExplainPackageTargetEvaluation:
    blockers = (
        (
            ProjectExplainMatrixBlocker(
                kind=(ProjectExplainMatrixBlockerKind.PROFILE_NOT_DECLARED_AVAILABLE),
                selected_profile=target.base_profile,
                bucket_profile=None,
                bucket_occurrences=(),
            ),
        )
        if state is ProjectExplainEvaluationState.BLOCKED
        else ()
    )
    posture = (
        ProjectExplainEvidencePosture.DETERMINISTIC_DERIVATION
        if state is ProjectExplainEvaluationState.CHECKED
        else ProjectExplainEvidencePosture.UNAVAILABLE
    )
    return ProjectExplainPackageTargetEvaluation(
        package_position=package_position,
        target_position=target.position,
        state=state,
        evidence_posture=posture,
        availability=(),
        blockers=blockers,
    )


def _cell(target_position: int, outcome: CellOutcome) -> ProjectExplainMatrixCell:
    if outcome is None:
        return ProjectExplainMatrixCell(
            target_position=target_position,
            state=ProjectExplainEvaluationState.BLOCKED,
            checked_status=None,
            evidence_posture=ProjectExplainEvidencePosture.UNAVAILABLE,
            checked_evidence=None,
        )
    posture = (
        ProjectExplainEvidencePosture.CONFLICTING
        if outcome is ProjectExplainCheckedStatus.CONFLICT
        else (
            ProjectExplainEvidencePosture.UNAVAILABLE
            if outcome is ProjectExplainCheckedStatus.UNKNOWN
            else ProjectExplainEvidencePosture.DETERMINISTIC_DERIVATION
        )
    )
    return ProjectExplainMatrixCell(
        target_position=target_position,
        state=ProjectExplainEvaluationState.CHECKED,
        checked_status=outcome,
        evidence_posture=posture,
        checked_evidence=matrix_helpers._evidence_for(outcome),
    )


def _matrix(
    package_projection: ProjectExplainPackageRequirementProjection,
    rows: tuple[tuple[CellOutcome, ...], ...],
    *,
    target_count: int,
) -> ProjectExplainRequirementTargetMatrix:
    assert len(rows) == len(package_projection.requirements)
    assert all(len(row) == target_count for row in rows)
    targets = tuple(_target(position) for position in range(target_count))
    root_states: list[ProjectExplainEvaluationState] = []
    for target_position in range(target_count):
        outcomes = tuple(row[target_position] for row in rows)
        if any(outcome is None for outcome in outcomes):
            assert all(outcome is None for outcome in outcomes)
            root_states.append(ProjectExplainEvaluationState.BLOCKED)
        else:
            root_states.append(ProjectExplainEvaluationState.CHECKED)
    evaluations = tuple(
        _evaluation(
            package.position,
            target,
            (
                root_states[target.position]
                if package.position == package_projection.root_package_position
                else ProjectExplainEvaluationState.UNDECLARED
            ),
        )
        for package in package_projection.packages
        for target in targets
    )
    return ProjectExplainRequirementTargetMatrix(
        targets=targets,
        package_target_evaluations=evaluations,
        rows=tuple(
            ProjectExplainMatrixRow(
                requirement_position=requirement_position,
                cells=tuple(
                    _cell(target_position, outcome)
                    for target_position, outcome in enumerate(outcomes)
                ),
            )
            for requirement_position, outcomes in enumerate(rows)
        ),
    )
