from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
import inspect
from pathlib import Path
from typing import Any, cast

import pytest

import pietto
import pietto._metadata as metadata_package
import pietto._project as project_package
import pietto._project_explain as project_explain_package
import pietto._project_explain.portability_projection as projection_module
import pietto.semantic as semantic_package
import test_phase58_slice3_project_explain_package_requirement_provenance as slice3
import test_phase58_slice4_project_explain_requirement_target_matrix as slice4
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
from pietto._project_explain.portability_projection import (
    ProjectExplainDefiniteGap,
    ProjectExplainPortabilityClassification,
    ProjectExplainPortabilityReason,
    ProjectExplainProjectPortability,
    ProjectExplainRequirementPortability,
    _derive_project_portability,
)
from pietto.semantic.capability_facts import CapabilityDomain, CapabilityKey


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT / "docs/spec/phase58-slice6-project-explain-portability-derivation-v1.md"
)
SOURCE = REPO_ROOT / "src/pietto/_project_explain/portability_projection.py"
PACKAGE_SMOKE = REPO_ROOT / "scripts/package_smoke.py"

CellOutcome = ProjectExplainCheckedStatus | None


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _package_projection(
    root: Path,
    requirement_count: int,
) -> ProjectExplainPackageRequirementProjection:
    keys = tuple(
        CapabilityKey(CapabilityDomain.LOGICAL_TYPE, subject=f"Type{position}")
        for position in range(requirement_count)
    )
    return slice3._projection(
        root,
        project=slice3._requirements("project", "requirements", *keys),
    )


def _target(position: int) -> ProjectExplainEvaluatedTarget:
    profile = slice4._simple_profile(name=f"base-{position}")
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
        checked_evidence=slice4._evidence_for(outcome),
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


def test_exact_vocabularies_fields_immutability_and_private_surface() -> None:
    assert tuple(
        (member.name, member.value)
        for member in ProjectExplainPortabilityClassification
    ) == (
        ("PORTABLE", "portable"),
        ("NOT_PORTABLE", "not_portable"),
        ("INDETERMINATE", "indeterminate"),
    )
    assert tuple(
        (member.name, member.value) for member in ProjectExplainPortabilityReason
    ) == (("NO_EVALUATED_TARGETS", "no-evaluated-targets"),)

    expected_fields = {
        ProjectExplainDefiniteGap: ("target_position", "status"),
        ProjectExplainRequirementPortability: (
            "requirement_position",
            "classification",
            "reason",
            "definite_gaps",
        ),
        ProjectExplainProjectPortability: (
            "classification",
            "reason",
            "requirements_evaluated",
            "requirements",
        ),
    }
    for carrier, expected in expected_fields.items():
        assert is_dataclass(carrier)
        assert tuple(field.name for field in fields(carrier)) == expected
        assert "__dict__" not in cast(Any, carrier).__slots__
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in inspect.signature(cast(Any, carrier)).parameters.values()
        )

    gap = ProjectExplainDefiniteGap(
        target_position=0,
        status=ProjectExplainCheckedStatus.UNSUPPORTED,
    )
    with pytest.raises(FrozenInstanceError):
        gap.target_position = 1  # type: ignore[misc]
    with pytest.raises(TypeError):
        replace(gap, target_position=cast(Any, True))
    with pytest.raises(TypeError):
        ProjectExplainRequirementPortability(
            requirement_position=0,
            classification=cast(Any, "portable"),
            reason=None,
            definite_gaps=(),
        )
    with pytest.raises(TypeError):
        ProjectExplainProjectPortability(
            classification=ProjectExplainPortabilityClassification.PORTABLE,
            reason=None,
            requirements_evaluated=cast(Any, False),
            requirements=(),
        )

    assert project_explain_package.__all__ == projection_module.__all__ == ()
    for public_module in (pietto, project_package, metadata_package, semantic_package):
        for carrier in expected_fields:
            assert not hasattr(public_module, carrier.__name__)


@pytest.mark.parametrize(
    "status",
    (
        ProjectExplainCheckedStatus.SATISFIED,
        ProjectExplainCheckedStatus.UNKNOWN,
        ProjectExplainCheckedStatus.CONFLICT,
    ),
)
def test_definite_gap_status_is_exact(
    status: ProjectExplainCheckedStatus,
) -> None:
    with pytest.raises(ValueError, match="UNSUPPORTED or ABSENT"):
        ProjectExplainDefiniteGap(target_position=0, status=status)


def test_model_integrity_rejects_inconsistent_hand_construction() -> None:
    gap = ProjectExplainDefiniteGap(
        target_position=1,
        status=ProjectExplainCheckedStatus.ABSENT,
    )
    for classification, gaps in (
        (ProjectExplainPortabilityClassification.PORTABLE, (gap,)),
        (ProjectExplainPortabilityClassification.NOT_PORTABLE, ()),
        (ProjectExplainPortabilityClassification.INDETERMINATE, (gap,)),
    ):
        with pytest.raises(ValueError):
            ProjectExplainRequirementPortability(
                requirement_position=0,
                classification=classification,
                reason=None,
                definite_gaps=gaps,
            )
    with pytest.raises(ValueError, match="strict target order"):
        ProjectExplainRequirementPortability(
            requirement_position=0,
            classification=ProjectExplainPortabilityClassification.NOT_PORTABLE,
            reason=None,
            definite_gaps=(gap, gap),
        )

    portable = ProjectExplainRequirementPortability(
        requirement_position=0,
        classification=ProjectExplainPortabilityClassification.PORTABLE,
        reason=None,
        definite_gaps=(),
    )
    indeterminate = ProjectExplainRequirementPortability(
        requirement_position=1,
        classification=ProjectExplainPortabilityClassification.INDETERMINATE,
        reason=None,
        definite_gaps=(),
    )
    with pytest.raises(ValueError, match="evaluated"):
        ProjectExplainProjectPortability(
            classification=ProjectExplainPortabilityClassification.INDETERMINATE,
            reason=None,
            requirements_evaluated=1,
            requirements=(portable, indeterminate),
        )
    with pytest.raises(ValueError, match="dense and ordered"):
        ProjectExplainProjectPortability(
            classification=ProjectExplainPortabilityClassification.INDETERMINATE,
            reason=None,
            requirements_evaluated=2,
            requirements=(portable, replace(indeterminate, requirement_position=0)),
        )
    with pytest.raises(ValueError, match="aggregate"):
        ProjectExplainProjectPortability(
            classification=ProjectExplainPortabilityClassification.PORTABLE,
            reason=None,
            requirements_evaluated=2,
            requirements=(portable, indeterminate),
        )

    no_targets = ProjectExplainRequirementPortability(
        requirement_position=0,
        classification=ProjectExplainPortabilityClassification.INDETERMINATE,
        reason=ProjectExplainPortabilityReason.NO_EVALUATED_TARGETS,
        definite_gaps=(),
    )
    with pytest.raises(ValueError, match="without a reason"):
        ProjectExplainProjectPortability(
            classification=ProjectExplainPortabilityClassification.INDETERMINATE,
            reason=None,
            requirements_evaluated=1,
            requirements=(no_targets,),
        )
    with pytest.raises(ValueError, match="matching indeterminate rows"):
        ProjectExplainProjectPortability(
            classification=ProjectExplainPortabilityClassification.INDETERMINATE,
            reason=ProjectExplainPortabilityReason.NO_EVALUATED_TARGETS,
            requirements_evaluated=1,
            requirements=(replace(indeterminate, requirement_position=0),),
        )


@pytest.mark.parametrize(
    ("outcomes", "classification", "gaps"),
    (
        (
            (
                ProjectExplainCheckedStatus.SATISFIED,
                ProjectExplainCheckedStatus.SATISFIED,
            ),
            ProjectExplainPortabilityClassification.PORTABLE,
            (),
        ),
        (
            (
                ProjectExplainCheckedStatus.SATISFIED,
                ProjectExplainCheckedStatus.UNSUPPORTED,
            ),
            ProjectExplainPortabilityClassification.NOT_PORTABLE,
            ((1, ProjectExplainCheckedStatus.UNSUPPORTED),),
        ),
        (
            (
                ProjectExplainCheckedStatus.ABSENT,
                ProjectExplainCheckedStatus.SATISFIED,
            ),
            ProjectExplainPortabilityClassification.NOT_PORTABLE,
            ((0, ProjectExplainCheckedStatus.ABSENT),),
        ),
        (
            (
                ProjectExplainCheckedStatus.UNSUPPORTED,
                ProjectExplainCheckedStatus.UNKNOWN,
            ),
            ProjectExplainPortabilityClassification.NOT_PORTABLE,
            ((0, ProjectExplainCheckedStatus.UNSUPPORTED),),
        ),
        (
            (
                ProjectExplainCheckedStatus.ABSENT,
                ProjectExplainCheckedStatus.CONFLICT,
            ),
            ProjectExplainPortabilityClassification.NOT_PORTABLE,
            ((0, ProjectExplainCheckedStatus.ABSENT),),
        ),
        (
            (ProjectExplainCheckedStatus.UNSUPPORTED, None),
            ProjectExplainPortabilityClassification.NOT_PORTABLE,
            ((0, ProjectExplainCheckedStatus.UNSUPPORTED),),
        ),
        (
            (
                ProjectExplainCheckedStatus.UNKNOWN,
                ProjectExplainCheckedStatus.SATISFIED,
            ),
            ProjectExplainPortabilityClassification.INDETERMINATE,
            (),
        ),
        (
            (
                ProjectExplainCheckedStatus.CONFLICT,
                ProjectExplainCheckedStatus.SATISFIED,
            ),
            ProjectExplainPortabilityClassification.INDETERMINATE,
            (),
        ),
        (
            (None, ProjectExplainCheckedStatus.SATISFIED),
            ProjectExplainPortabilityClassification.INDETERMINATE,
            (),
        ),
        (
            (
                ProjectExplainCheckedStatus.UNKNOWN,
                ProjectExplainCheckedStatus.CONFLICT,
            ),
            ProjectExplainPortabilityClassification.INDETERMINATE,
            (),
        ),
        ((), ProjectExplainPortabilityClassification.INDETERMINATE, ()),
    ),
)
def test_requirement_classification_truth_table(
    tmp_path: Path,
    outcomes: tuple[CellOutcome, ...],
    classification: ProjectExplainPortabilityClassification,
    gaps: tuple[tuple[int, ProjectExplainCheckedStatus], ...],
) -> None:
    package_projection = _package_projection(tmp_path, 1)
    matrix = _matrix(
        package_projection,
        (outcomes,),
        target_count=len(outcomes),
    )

    result = _derive_project_portability(package_projection, matrix)
    requirement = result.requirements[0]

    assert requirement.classification is classification
    assert (
        tuple((gap.target_position, gap.status) for gap in requirement.definite_gaps)
        == gaps
    )
    if outcomes:
        assert requirement.reason is None
    else:
        assert (
            requirement.reason is ProjectExplainPortabilityReason.NO_EVALUATED_TARGETS
        )
        assert result.reason is ProjectExplainPortabilityReason.NO_EVALUATED_TARGETS


def test_multiple_definite_gaps_preserve_target_order_and_multiplicity(
    tmp_path: Path,
) -> None:
    package_projection = _package_projection(tmp_path, 1)
    matrix = _matrix(
        package_projection,
        (
            (
                ProjectExplainCheckedStatus.ABSENT,
                ProjectExplainCheckedStatus.UNKNOWN,
                ProjectExplainCheckedStatus.UNSUPPORTED,
                ProjectExplainCheckedStatus.ABSENT,
            ),
        ),
        target_count=4,
    )

    requirement = _derive_project_portability(
        package_projection,
        matrix,
    ).requirements[0]

    assert tuple(
        (gap.target_position, gap.status) for gap in requirement.definite_gaps
    ) == (
        (0, ProjectExplainCheckedStatus.ABSENT),
        (2, ProjectExplainCheckedStatus.UNSUPPORTED),
        (3, ProjectExplainCheckedStatus.ABSENT),
    )


@pytest.mark.parametrize(
    ("rows", "requirement_classes", "project_classification"),
    (
        (
            (
                (ProjectExplainCheckedStatus.SATISFIED,),
                (ProjectExplainCheckedStatus.SATISFIED,),
            ),
            (
                ProjectExplainPortabilityClassification.PORTABLE,
                ProjectExplainPortabilityClassification.PORTABLE,
            ),
            ProjectExplainPortabilityClassification.PORTABLE,
        ),
        (
            (
                (ProjectExplainCheckedStatus.SATISFIED,),
                (ProjectExplainCheckedStatus.UNKNOWN,),
            ),
            (
                ProjectExplainPortabilityClassification.PORTABLE,
                ProjectExplainPortabilityClassification.INDETERMINATE,
            ),
            ProjectExplainPortabilityClassification.INDETERMINATE,
        ),
        (
            (
                (ProjectExplainCheckedStatus.UNKNOWN,),
                (ProjectExplainCheckedStatus.UNSUPPORTED,),
            ),
            (
                ProjectExplainPortabilityClassification.INDETERMINATE,
                ProjectExplainPortabilityClassification.NOT_PORTABLE,
            ),
            ProjectExplainPortabilityClassification.NOT_PORTABLE,
        ),
    ),
)
def test_project_aggregation_precedence_is_exact(
    tmp_path: Path,
    rows: tuple[tuple[CellOutcome, ...], ...],
    requirement_classes: tuple[ProjectExplainPortabilityClassification, ...],
    project_classification: ProjectExplainPortabilityClassification,
) -> None:
    package_projection = _package_projection(tmp_path, len(rows))
    matrix = _matrix(package_projection, rows, target_count=1)

    result = _derive_project_portability(package_projection, matrix)

    assert (
        tuple(requirement.classification for requirement in result.requirements)
        == requirement_classes
    )
    assert result.classification is project_classification
    assert result.reason is None
    assert result.requirements_evaluated == len(rows)


def test_zero_requirements_respects_the_explicit_target_denominator(
    tmp_path: Path,
) -> None:
    package_projection = _package_projection(tmp_path, 0)
    non_empty = _derive_project_portability(
        package_projection,
        _matrix(package_projection, (), target_count=1),
    )
    empty = _derive_project_portability(
        package_projection,
        _matrix(package_projection, (), target_count=0),
    )

    assert non_empty.classification is ProjectExplainPortabilityClassification.PORTABLE
    assert non_empty.reason is None
    assert non_empty.requirements_evaluated == 0
    assert non_empty.requirements == ()
    assert empty.classification is ProjectExplainPortabilityClassification.INDETERMINATE
    assert empty.reason is ProjectExplainPortabilityReason.NO_EVALUATED_TARGETS
    assert empty.requirements_evaluated == 0
    assert empty.requirements == ()


def test_slice3_slice4_alignment_and_malformed_order_fail_closed(
    tmp_path: Path,
) -> None:
    package_projection = _package_projection(tmp_path, 1)
    matrix = _matrix(
        package_projection,
        (
            (
                ProjectExplainCheckedStatus.SATISFIED,
                ProjectExplainCheckedStatus.SATISFIED,
            ),
        ),
        target_count=2,
    )
    with pytest.raises(TypeError, match="Slice 3"):
        _derive_project_portability(cast(Any, object()), matrix)
    with pytest.raises(TypeError, match="Slice 4"):
        _derive_project_portability(package_projection, cast(Any, object()))
    with pytest.raises(ValueError, match="one matrix row"):
        _derive_project_portability(_package_projection(tmp_path / "empty", 0), matrix)

    row = matrix.rows[0]
    original_requirement_position = row.requirement_position
    object.__setattr__(row, "requirement_position", 1)
    try:
        with pytest.raises(ValueError, match="Slice 3 requirement order"):
            _derive_project_portability(package_projection, matrix)
    finally:
        object.__setattr__(row, "requirement_position", original_requirement_position)

    original_cells = row.cells
    object.__setattr__(row, "cells", tuple(reversed(row.cells)))
    try:
        with pytest.raises(ValueError, match="exact target order"):
            _derive_project_portability(package_projection, matrix)
    finally:
        object.__setattr__(row, "cells", original_cells)

    target = matrix.targets[0]
    original_target_position = target.position
    object.__setattr__(target, "position", 1)
    try:
        with pytest.raises(ValueError, match="dense evaluated target order"):
            _derive_project_portability(package_projection, matrix)
    finally:
        object.__setattr__(target, "position", original_target_position)


def test_source_has_no_slice5_ranking_scoring_output_or_runtime_dependency() -> None:
    source = _read(SOURCE)
    for forbidden in (
        "extension_catalog",
        "ProjectExplainExtensionCatalog",
        "ranking",
        "recommend",
        "percentage",
        "score",
        "BEST_TARGET",
        "WORST_TARGET",
        "ProjectExplainPayload",
        "CrossSectionReference",
        "import json",
        "serialize",
        "render_",
        "argparse",
        "pathlib",
        "import os",
        "open(",
        "requests",
        "socket",
    ):
        assert forbidden not in source
    assert tuple(inspect.signature(_derive_project_portability).parameters) == (
        "package_projection",
        "matrix_projection",
    )


def test_spec_handoff_and_installed_private_module_contract_are_exact() -> None:
    document = _read(SPEC)
    normalized = " ".join(document.split())
    for required in (
        "PHASE58_SLICE6_SELF_OWNED_OPEN = 0",
        "ProjectExplainRequirementTargetMatrix",
        "NO_EVALUATED_TARGETS",
        "zero requirements is `PORTABLE`",
        "Slice 5 remains explanatory catalog evidence",
        "Slice 7 remains `UNSTARTED / NOT AUTHORIZED`",
    ):
        assert required in normalized

    package_smoke = _read(PACKAGE_SMOKE)
    for required in (
        'f"{prefix}/_project_explain/portability_projection.py"',
        '"installed private project explain portability projection import"',
        "import pietto._project_explain.portability_projection",
    ):
        assert required in package_smoke
