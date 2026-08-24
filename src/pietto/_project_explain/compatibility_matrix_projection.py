"""Private requirement-by-target compatibility matrix projection."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum

from pietto._project.capability_availability import (
    CapabilityProfileAvailabilityOccurrence,
    CompilerCapabilityProfileAvailabilityAuthority,
)
from pietto._project.capability_checking import (
    CapabilityRequirementCheck,
    CapabilityRequirementStatus,
    PackageCapabilityRequirementsBlocked,
    PackageCapabilityRequirementsChecked,
    PackageCapabilityRequirementsUndeclared,
    SelectedProfileAvailabilityBlocker,
    SelectedProfileAvailabilityBlockerKind,
)
from pietto._project.capability_inspection import (
    CapabilityInspection,
    CapabilityInspectionAvailabilityOccurrence,
    CapabilityInspectionAvailabilityOwnerKind,
    CapabilityInspectionBlocker,
    CapabilityInspectionCell,
    CapabilityInspectionCheck,
    CapabilityInspectionColumn,
    CapabilityInspectionColumnVariant,
    CapabilityInspectionFact,
    CapabilityInspectionFactSet,
    CapabilityInspectionFormat,
    CapabilityInspectionLookup,
    CapabilityInspectionLookupVariant,
    CapabilityInspectionProfile,
    CapabilityInspectionRequirement,
    CapabilityInspectionRequirementDeclaration,
)
from pietto._project.capability_matrix import (
    CapabilityCheckingMatrixCell,
    CapabilityCheckingMatrixRow,
    CapabilityCheckingTargetColumn,
    CapabilityCheckingTargetContext,
    PackageCapabilityCheckingMatrix,
)
from pietto._project.model import ProjectRoot
from pietto._project.package_inspection import PackageInspectionFactSet
from .model import (
    ProjectExplainEvidencePosture,
    ProjectExplainLogicalPath,
    ProjectExplainLogicalPathKind,
)
from .package_requirement_projection import (
    ProjectExplainCapabilityKey,
    ProjectExplainPackageRequirementProjection,
    ProjectExplainRequirementRequest,
    _project_package_requirement_provenance,
)
from pietto.semantic.capability_facts import CapabilityFact, CapabilitySupport
from pietto.semantic.capability_lookup import Absent, Conflict, Found, Unknown
from pietto.semantic.capability_profiles import (
    CapabilityProfileKind,
    CapabilityProfileTargetKind,
    StaticCapabilityProfile,
)

__all__: tuple[str, ...] = ()


class ProjectExplainEvaluationState(StrEnum):
    UNDECLARED = "undeclared"
    BLOCKED = "blocked"
    CHECKED = "checked"


class ProjectExplainCheckedStatus(StrEnum):
    SATISFIED = "satisfied"
    UNSUPPORTED = "unsupported"
    ABSENT = "absent"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"


class ProjectExplainProfileKind(StrEnum):
    BASE = "base"
    OVERLAY = "overlay"


class ProjectExplainProfileTargetKind(StrEnum):
    DATABASE = "database"
    EXTENSION = "extension"


class ProjectExplainAvailabilityOwnerKind(StrEnum):
    COMPILER = "compiler"
    PROJECT = "project"


class ProjectExplainMatrixBlockerKind(StrEnum):
    PROFILE_NOT_DECLARED_AVAILABLE = "profile_not_declared_available"
    PROFILE_AUTHORITY_MISMATCH = "profile_authority_mismatch"


class ProjectExplainLookupVariant(StrEnum):
    FOUND = "found"
    ABSENT = "absent"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"


class ProjectExplainCapabilitySupport(StrEnum):
    SUPPORTED = "supported"
    EXPLICITLY_UNSUPPORTED = "explicitly_unsupported"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainCapabilityProfile:
    namespace: str
    name: str
    profile_release: str
    kind: ProjectExplainProfileKind
    target_kind: ProjectExplainProfileTargetKind
    database_family: str
    target_release: str
    extension_identity: str | None
    extension_release: str | None

    def __post_init__(self) -> None:
        _require_non_empty_text(self.namespace, "profile namespace")
        _require_non_empty_text(self.name, "profile name")
        _require_non_empty_text(self.profile_release, "profile release")
        if type(self.kind) is not ProjectExplainProfileKind:
            raise TypeError("Project Explain profiles require an exact kind.")
        if type(self.target_kind) is not ProjectExplainProfileTargetKind:
            raise TypeError("Project Explain profiles require an exact target kind.")
        _require_non_empty_text(self.database_family, "profile database family")
        _require_non_empty_text(self.target_release, "profile target release")
        if self.extension_identity is not None:
            _require_non_empty_text(
                self.extension_identity,
                "profile extension identity",
            )
        if self.extension_release is not None:
            _require_non_empty_text(
                self.extension_release,
                "profile extension release",
            )
        if self.kind is ProjectExplainProfileKind.BASE:
            if (
                self.target_kind is not ProjectExplainProfileTargetKind.DATABASE
                or self.extension_identity is not None
                or self.extension_release is not None
            ):
                raise ValueError(
                    "BASE profiles require a database target without extension identity."
                )
            return
        if (
            self.target_kind is not ProjectExplainProfileTargetKind.EXTENSION
            or self.extension_identity is None
            or self.extension_release is None
        ):
            raise ValueError(
                "OVERLAY profiles require an extension target and identity."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainEvaluatedTarget:
    position: int
    database_family: str
    database_release: str
    base_profile: ProjectExplainCapabilityProfile
    supplied_overlays: tuple[ProjectExplainCapabilityProfile, ...]
    dependency_order: tuple[ProjectExplainCapabilityProfile, ...]

    def __post_init__(self) -> None:
        _require_position(self.position, "target position")
        _require_non_empty_text(self.database_family, "target database family")
        _require_non_empty_text(self.database_release, "target database release")
        if type(self.base_profile) is not ProjectExplainCapabilityProfile:
            raise TypeError("Evaluated targets require an exact base profile.")
        if (
            self.base_profile.kind is not ProjectExplainProfileKind.BASE
            or self.base_profile.target_kind
            is not ProjectExplainProfileTargetKind.DATABASE
            or self.base_profile.database_family != self.database_family
            or self.base_profile.target_release != self.database_release
        ):
            raise ValueError("Evaluated targets require one matching base profile.")
        _require_exact_tuple(
            self.supplied_overlays,
            ProjectExplainCapabilityProfile,
            "supplied overlays",
        )
        if any(
            profile.kind is not ProjectExplainProfileKind.OVERLAY
            or profile.target_kind is not ProjectExplainProfileTargetKind.EXTENSION
            or profile.database_family != self.database_family
            or profile.target_release != self.database_release
            for profile in self.supplied_overlays
        ):
            raise ValueError("Evaluated target overlays must match the target.")
        _require_exact_tuple(
            self.dependency_order,
            ProjectExplainCapabilityProfile,
            "profile dependency order",
        )
        if (
            not self.dependency_order
            or self.dependency_order[0] != self.base_profile
            or Counter(self.dependency_order[1:]) != Counter(self.supplied_overlays)
        ):
            raise ValueError(
                "Evaluated targets require the exact selected profile dependency order."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainAvailabilityOccurrence:
    owner_kind: ProjectExplainAvailabilityOwnerKind
    owner_position: int
    project_path: ProjectExplainLogicalPath | None
    profile: ProjectExplainCapabilityProfile

    def __post_init__(self) -> None:
        if type(self.owner_kind) is not ProjectExplainAvailabilityOwnerKind:
            raise TypeError("Availability occurrences require an exact owner kind.")
        _require_position(self.owner_position, "availability owner position")
        if type(self.profile) is not ProjectExplainCapabilityProfile:
            raise TypeError("Availability occurrences require an exact profile.")
        if self.owner_kind is ProjectExplainAvailabilityOwnerKind.COMPILER:
            if self.project_path is not None:
                raise ValueError("Compiler availability forbids a project path.")
            return
        if (
            type(self.project_path) is not ProjectExplainLogicalPath
            or self.project_path.kind
            is not ProjectExplainLogicalPathKind.PROJECT_RELATIVE
        ):
            raise ValueError(
                "Project availability requires a project-relative logical path."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainMatrixBlocker:
    kind: ProjectExplainMatrixBlockerKind
    selected_profile: ProjectExplainCapabilityProfile
    bucket_profile: ProjectExplainCapabilityProfile | None
    bucket_occurrences: tuple[ProjectExplainAvailabilityOccurrence, ...]

    def __post_init__(self) -> None:
        if type(self.kind) is not ProjectExplainMatrixBlockerKind:
            raise TypeError("Matrix blockers require an exact kind.")
        if type(self.selected_profile) is not ProjectExplainCapabilityProfile:
            raise TypeError("Matrix blockers require an exact selected profile.")
        if self.bucket_profile is not None and (
            type(self.bucket_profile) is not ProjectExplainCapabilityProfile
        ):
            raise TypeError("Matrix blockers require an exact bucket profile.")
        _require_exact_tuple(
            self.bucket_occurrences,
            ProjectExplainAvailabilityOccurrence,
            "matrix blocker bucket occurrences",
        )
        if self.kind is ProjectExplainMatrixBlockerKind.PROFILE_NOT_DECLARED_AVAILABLE:
            if self.bucket_profile is not None or self.bucket_occurrences:
                raise ValueError("Undeclared-profile blockers forbid bucket evidence.")
            return
        if self.bucket_profile is None or not self.bucket_occurrences:
            raise ValueError(
                "Profile-authority mismatch blockers require bucket evidence."
            )
        if any(
            occurrence.profile != self.bucket_profile
            for occurrence in self.bucket_occurrences
        ):
            raise ValueError(
                "Matrix blocker occurrences must match the bucket profile."
            )
        if _profile_reference(self.selected_profile) != _profile_reference(
            self.bucket_profile
        ):
            raise ValueError("Matrix blocker profiles must share one exact reference.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainPackageTargetEvaluation:
    package_position: int
    target_position: int
    state: ProjectExplainEvaluationState
    evidence_posture: ProjectExplainEvidencePosture
    availability: tuple[ProjectExplainAvailabilityOccurrence, ...]
    blockers: tuple[ProjectExplainMatrixBlocker, ...]

    def __post_init__(self) -> None:
        _require_position(self.package_position, "evaluation package position")
        _require_position(self.target_position, "evaluation target position")
        if type(self.state) is not ProjectExplainEvaluationState:
            raise TypeError("Package-target evaluations require an exact state.")
        if type(self.evidence_posture) is not ProjectExplainEvidencePosture:
            raise TypeError("Package-target evaluations require an exact posture.")
        _require_exact_tuple(
            self.availability,
            ProjectExplainAvailabilityOccurrence,
            "evaluation availability",
        )
        _require_exact_tuple(
            self.blockers,
            ProjectExplainMatrixBlocker,
            "evaluation blockers",
        )
        if self.state is ProjectExplainEvaluationState.UNDECLARED:
            if (
                self.evidence_posture is not ProjectExplainEvidencePosture.UNAVAILABLE
                or self.blockers
            ):
                raise ValueError(
                    "UNDECLARED evaluations require unavailable posture and no blockers."
                )
            return
        if self.state is ProjectExplainEvaluationState.BLOCKED:
            if not self.blockers:
                raise ValueError("BLOCKED evaluations require blockers.")
            expected = (
                ProjectExplainEvidencePosture.CONFLICTING
                if any(
                    blocker.kind
                    is ProjectExplainMatrixBlockerKind.PROFILE_AUTHORITY_MISMATCH
                    for blocker in self.blockers
                )
                else ProjectExplainEvidencePosture.UNAVAILABLE
            )
            if self.evidence_posture is not expected:
                raise ValueError("BLOCKED evaluation posture disagrees with blockers.")
            return
        if (
            self.evidence_posture
            is not ProjectExplainEvidencePosture.DETERMINISTIC_DERIVATION
            or self.blockers
        ):
            raise ValueError(
                "CHECKED evaluations require deterministic posture and no blockers."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainLookupSummary:
    variant: ProjectExplainLookupVariant
    reason: str | None
    supports: tuple[ProjectExplainCapabilitySupport, ...]

    def __post_init__(self) -> None:
        if type(self.variant) is not ProjectExplainLookupVariant:
            raise TypeError("Lookup summaries require an exact variant.")
        if self.reason is not None:
            _require_non_empty_text(self.reason, "lookup reason")
        _require_exact_tuple(
            self.supports,
            ProjectExplainCapabilitySupport,
            "lookup supports",
        )
        if self.variant is ProjectExplainLookupVariant.FOUND:
            if self.reason is not None or len(self.supports) != 1:
                raise ValueError("FOUND lookup summaries require one support.")
            return
        if self.variant is ProjectExplainLookupVariant.ABSENT:
            if self.reason != "no_catalog_entry" or self.supports:
                raise ValueError(
                    "ABSENT lookup summaries require no_catalog_entry and no support."
                )
            return
        if self.variant is ProjectExplainLookupVariant.UNKNOWN:
            if self.reason is None or self.supports:
                raise ValueError("UNKNOWN lookup summaries require one reason.")
            return
        if self.reason != "conflicting_evidence" or len(self.supports) < 2:
            raise ValueError(
                "CONFLICT lookup summaries require ordered conflicting supports."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainCheckedEvidence:
    target_lookup: ProjectExplainLookupSummary
    provider_domain_complete: bool
    provider_unknown_reason: str | None
    provider_lookup: ProjectExplainLookupSummary

    def __post_init__(self) -> None:
        if type(self.target_lookup) is not ProjectExplainLookupSummary:
            raise TypeError("Checked evidence requires an exact target lookup.")
        if type(self.provider_domain_complete) is not bool:
            raise TypeError("Checked evidence completeness must be an exact bool.")
        if self.provider_unknown_reason is not None:
            _require_non_empty_text(
                self.provider_unknown_reason,
                "provider unknown reason",
            )
        if self.provider_domain_complete and self.provider_unknown_reason is not None:
            raise ValueError("Complete provider domains forbid an unknown reason.")
        if type(self.provider_lookup) is not ProjectExplainLookupSummary:
            raise TypeError("Checked evidence requires an exact provider lookup.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainMatrixCell:
    target_position: int
    state: ProjectExplainEvaluationState
    checked_status: ProjectExplainCheckedStatus | None
    evidence_posture: ProjectExplainEvidencePosture
    checked_evidence: ProjectExplainCheckedEvidence | None

    def __post_init__(self) -> None:
        _require_position(self.target_position, "matrix cell target position")
        if type(self.state) is not ProjectExplainEvaluationState:
            raise TypeError("Matrix cells require an exact evaluation state.")
        if type(self.evidence_posture) is not ProjectExplainEvidencePosture:
            raise TypeError("Matrix cells require an exact evidence posture.")
        if self.state is ProjectExplainEvaluationState.UNDECLARED:
            raise ValueError("Requirement rows cannot contain UNDECLARED cells.")
        if self.state is ProjectExplainEvaluationState.BLOCKED:
            if self.checked_status is not None or self.checked_evidence is not None:
                raise ValueError("BLOCKED cells forbid checked status and evidence.")
            if self.evidence_posture not in {
                ProjectExplainEvidencePosture.UNAVAILABLE,
                ProjectExplainEvidencePosture.CONFLICTING,
            }:
                raise ValueError("BLOCKED cells require a blocked evidence posture.")
            return
        if type(self.checked_status) is not ProjectExplainCheckedStatus:
            raise TypeError("CHECKED cells require an exact checked status.")
        if type(self.checked_evidence) is not ProjectExplainCheckedEvidence:
            raise TypeError("CHECKED cells require exact checked evidence.")
        expected_posture = _checked_posture(self.checked_status)
        if self.evidence_posture is not expected_posture:
            raise ValueError("CHECKED cell posture disagrees with its status.")
        if self.checked_status is not _status_from_evidence(self.checked_evidence):
            raise ValueError("CHECKED status disagrees with detached lookup evidence.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainMatrixRow:
    requirement_position: int
    cells: tuple[ProjectExplainMatrixCell, ...]

    def __post_init__(self) -> None:
        _require_position(self.requirement_position, "matrix row requirement position")
        _require_exact_tuple(self.cells, ProjectExplainMatrixCell, "matrix row cells")
        if tuple(cell.target_position for cell in self.cells) != tuple(
            range(len(self.cells))
        ):
            raise ValueError("Matrix row cells must retain dense target order.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainRequirementTargetMatrix:
    targets: tuple[ProjectExplainEvaluatedTarget, ...]
    package_target_evaluations: tuple[ProjectExplainPackageTargetEvaluation, ...]
    rows: tuple[ProjectExplainMatrixRow, ...]

    def __post_init__(self) -> None:
        _require_dense_tuple(self.targets, ProjectExplainEvaluatedTarget, "targets")
        _require_exact_tuple(
            self.package_target_evaluations,
            ProjectExplainPackageTargetEvaluation,
            "package-target evaluations",
        )
        _require_exact_tuple(self.rows, ProjectExplainMatrixRow, "matrix rows")
        if tuple(row.requirement_position for row in self.rows) != tuple(
            range(len(self.rows))
        ):
            raise ValueError(
                "Project Explain matrix row positions must be dense and ordered."
            )
        if not self.targets:
            if self.package_target_evaluations or any(row.cells for row in self.rows):
                raise ValueError(
                    "An empty target denominator requires empty evaluations and cells."
                )
            return
        if not self.package_target_evaluations:
            raise ValueError("A non-empty target denominator requires evaluations.")
        target_count = len(self.targets)
        package_count = self.package_target_evaluations[-1].package_position + 1
        expected_order = tuple(
            (package_position, target_position)
            for package_position in range(package_count)
            for target_position in range(target_count)
        )
        actual_order = tuple(
            (evaluation.package_position, evaluation.target_position)
            for evaluation in self.package_target_evaluations
        )
        if actual_order != expected_order:
            raise ValueError(
                "Package-target evaluations must retain package by target order."
            )
        evaluations_by_target = tuple(
            tuple(
                evaluation
                for evaluation in self.package_target_evaluations
                if evaluation.target_position == target_position
            )
            for target_position in range(target_count)
        )
        for row in self.rows:
            if len(row.cells) != target_count:
                raise ValueError("Matrix rows require one cell per target.")
            for cell, evaluations in zip(
                row.cells,
                evaluations_by_target,
                strict=True,
            ):
                if not any(
                    evaluation.state is cell.state
                    and (
                        cell.state is ProjectExplainEvaluationState.CHECKED
                        or evaluation.evidence_posture is cell.evidence_posture
                    )
                    for evaluation in evaluations
                ):
                    raise ValueError(
                        "Matrix cells require a matching package-target evaluation."
                    )


def _project_requirement_target_matrix(
    package_projection: ProjectExplainPackageRequirementProjection,
    package_facts: PackageInspectionFactSet,
    capability_facts: tuple[CapabilityInspectionFactSet, ...],
) -> ProjectExplainRequirementTargetMatrix:
    """Project one exact non-empty inspected compatibility denominator."""

    if type(package_projection) is not ProjectExplainPackageRequirementProjection:
        raise TypeError("Slice 4 requires an exact Slice 3 projection.")
    expected_projection = _project_package_requirement_provenance(
        package_facts,
        capability_facts,
    )
    if package_projection != expected_projection:
        raise ValueError("Slice 4 requires the same exact Slice 3 projection.")
    if type(capability_facts) is not tuple or any(
        type(facts) is not CapabilityInspectionFactSet for facts in capability_facts
    ):
        raise TypeError("Slice 4 requires an exact capability fact-set tuple.")

    inspections = tuple(_require_inspection(facts) for facts in capability_facts)
    root_inspection = inspections[package_projection.root_package_position]
    root_contexts = root_inspection.matrix.contexts
    if not root_contexts:
        raise ValueError("The non-empty Slice 4 projection requires target contexts.")
    targets = tuple(_project_target(column) for column in root_inspection.targets)

    for inspection in inspections:
        if len(inspection.targets) != len(targets):
            raise ValueError("All package matrices require the same target count.")
        for position, (context, column, target) in enumerate(
            zip(
                inspection.matrix.contexts,
                inspection.targets,
                targets,
                strict=True,
            )
        ):
            if context is not root_contexts[position]:
                raise ValueError(
                    "All package matrices require the same exact target authority."
                )
            if column.position != position or _project_target(column) != target:
                raise ValueError(
                    "All inspected targets must agree with the root target identity."
                )

    evaluations = tuple(
        _project_evaluation(package_position, column, inspection)
        for package_position, inspection in enumerate(inspections)
        for column in inspection.targets
    )
    if len(evaluations) != len(package_projection.packages) * len(targets):
        raise ValueError("Slice 4 requires every package by target evaluation.")

    rows = tuple(
        _project_requirement_row(
            request,
            inspections[request.declared_by],
            evaluations[
                request.declared_by * len(targets) : (request.declared_by + 1)
                * len(targets)
            ],
        )
        for request in package_projection.requirements
    )
    matrix = ProjectExplainRequirementTargetMatrix(
        targets=targets,
        package_target_evaluations=evaluations,
        rows=rows,
    )
    _validate_projection_references(matrix, package_projection)
    return matrix


def _project_empty_requirement_target_matrix(
    package_projection: ProjectExplainPackageRequirementProjection,
) -> ProjectExplainRequirementTargetMatrix:
    """Represent an explicitly empty target denominator without synthetic results."""

    _require_detached_package_projection(package_projection)
    return ProjectExplainRequirementTargetMatrix(
        targets=(),
        package_target_evaluations=(),
        rows=tuple(
            ProjectExplainMatrixRow(
                requirement_position=requirement.position,
                cells=(),
            )
            for requirement in package_projection.requirements
        ),
    )


def _require_inspection(facts: CapabilityInspectionFactSet) -> CapabilityInspection:
    if type(facts) is not CapabilityInspectionFactSet:
        raise TypeError("Slice 4 requires exact capability inspection facts.")
    inspection = facts.inspection
    if (
        inspection is not facts.authority.inspection
        or facts.canonical_bytes is not facts.authority.canonical_bytes
        or type(inspection) is not CapabilityInspection
        or inspection.format is not CapabilityInspectionFormat.CAPABILITY_INSPECTION_V1
        or inspection.matrix is not facts.authority.matrix
        or type(inspection.matrix) is not PackageCapabilityCheckingMatrix
        or type(inspection.targets) is not tuple
        or inspection.target_count != len(inspection.targets)
        or len(inspection.matrix.contexts) != len(inspection.targets)
        or len(inspection.matrix.columns) != len(inspection.targets)
        or type(inspection.requirements) is not tuple
        or inspection.requirement_count != len(inspection.requirements)
        or len(inspection.matrix.rows) != len(inspection.requirements)
    ):
        raise ValueError("Slice 4 rejects grafted capability inspection authority.")
    for position, column in enumerate(inspection.targets):
        _require_column_authority(
            column,
            position,
            inspection.matrix.contexts[position],
            inspection.matrix.columns[position],
        )
    for position, requirement in enumerate(inspection.requirements):
        _require_requirement_authority(
            requirement,
            position,
            inspection.matrix.rows[position],
            inspection.matrix.columns,
        )
    return inspection


def _project_profile(
    profile: CapabilityInspectionProfile,
) -> ProjectExplainCapabilityProfile:
    if type(profile) is not CapabilityInspectionProfile:
        raise TypeError("Slice 4 requires exact inspected profiles.")
    _require_profile_authority(profile)
    return ProjectExplainCapabilityProfile(
        namespace=profile.namespace,
        name=profile.name,
        profile_release=profile.profile_release,
        kind=ProjectExplainProfileKind(profile.kind.value),
        target_kind=ProjectExplainProfileTargetKind(profile.target_kind.value),
        database_family=profile.database_family,
        target_release=profile.target_release,
        extension_identity=profile.extension_identity,
        extension_release=profile.extension_release,
    )


def _project_target(
    column: CapabilityInspectionColumn,
) -> ProjectExplainEvaluatedTarget:
    if type(column) is not CapabilityInspectionColumn:
        raise TypeError("Slice 4 requires exact inspected target columns.")
    return ProjectExplainEvaluatedTarget(
        position=column.position,
        database_family=column.base_profile.database_family,
        database_release=column.base_profile.target_release,
        base_profile=_project_profile(column.base_profile),
        supplied_overlays=tuple(
            _project_profile(profile) for profile in column.supplied_overlays
        ),
        dependency_order=tuple(
            _project_profile(profile) for profile in column.dependency_order
        ),
    )


def _project_availability(
    occurrence: CapabilityInspectionAvailabilityOccurrence,
) -> ProjectExplainAvailabilityOccurrence:
    if type(occurrence) is not CapabilityInspectionAvailabilityOccurrence:
        raise TypeError("Slice 4 requires exact inspected availability.")
    _require_availability_authority(occurrence)
    return ProjectExplainAvailabilityOccurrence(
        owner_kind=ProjectExplainAvailabilityOwnerKind(occurrence.owner_kind.value),
        owner_position=occurrence.owner_position,
        project_path=(
            None
            if occurrence.project_path is None
            else ProjectExplainLogicalPath(
                kind=ProjectExplainLogicalPathKind.PROJECT_RELATIVE,
                value=occurrence.project_path,
            )
        ),
        profile=_project_profile(occurrence.profile),
    )


def _project_blocker(
    blocker: CapabilityInspectionBlocker,
) -> ProjectExplainMatrixBlocker:
    if type(blocker) is not CapabilityInspectionBlocker:
        raise TypeError("Slice 4 requires exact inspected blockers.")
    _require_blocker_authority(blocker)
    return ProjectExplainMatrixBlocker(
        kind=ProjectExplainMatrixBlockerKind(blocker.kind.value),
        selected_profile=_project_profile(blocker.selected_profile),
        bucket_profile=(
            None
            if blocker.bucket_profile is None
            else _project_profile(blocker.bucket_profile)
        ),
        bucket_occurrences=tuple(
            _project_availability(occurrence)
            for occurrence in blocker.bucket_occurrences
        ),
    )


def _project_evaluation(
    package_position: int,
    column: CapabilityInspectionColumn,
    inspection: CapabilityInspection,
) -> ProjectExplainPackageTargetEvaluation:
    blockers = tuple(_project_blocker(blocker) for blocker in column.blockers)
    if column.variant is CapabilityInspectionColumnVariant.UNDECLARED:
        if (
            inspection.requirement_declaration
            is not CapabilityInspectionRequirementDeclaration.UNDECLARED
            or blockers
        ):
            raise ValueError("UNDECLARED targets require undeclared package authority.")
        state = ProjectExplainEvaluationState.UNDECLARED
        posture = ProjectExplainEvidencePosture.UNAVAILABLE
    elif column.variant is CapabilityInspectionColumnVariant.BLOCKED:
        if (
            inspection.requirement_declaration
            is not CapabilityInspectionRequirementDeclaration.DECLARED
            or not blockers
        ):
            raise ValueError("BLOCKED targets require declared blocker authority.")
        state = ProjectExplainEvaluationState.BLOCKED
        posture = (
            ProjectExplainEvidencePosture.CONFLICTING
            if any(
                blocker.kind
                is ProjectExplainMatrixBlockerKind.PROFILE_AUTHORITY_MISMATCH
                for blocker in blockers
            )
            else ProjectExplainEvidencePosture.UNAVAILABLE
        )
    elif column.variant is CapabilityInspectionColumnVariant.CHECKED:
        if (
            inspection.requirement_declaration
            is not CapabilityInspectionRequirementDeclaration.DECLARED
            or blockers
        ):
            raise ValueError("CHECKED targets require declared checked authority.")
        state = ProjectExplainEvaluationState.CHECKED
        posture = ProjectExplainEvidencePosture.DETERMINISTIC_DERIVATION
    else:
        raise ValueError("Slice 4 requires one exact inspected column variant.")
    return ProjectExplainPackageTargetEvaluation(
        package_position=package_position,
        target_position=column.position,
        state=state,
        evidence_posture=posture,
        availability=tuple(
            _project_availability(occurrence) for occurrence in column.availability
        ),
        blockers=blockers,
    )


def _project_lookup(lookup: CapabilityInspectionLookup) -> ProjectExplainLookupSummary:
    if type(lookup) is not CapabilityInspectionLookup:
        raise TypeError("Slice 4 requires exact inspected lookups.")
    _require_lookup_authority(lookup)
    return ProjectExplainLookupSummary(
        variant=ProjectExplainLookupVariant(lookup.variant.value),
        reason=None if lookup.reason is None else lookup.reason.value,
        supports=tuple(_project_support(fact.support) for fact in lookup.facts),
    )


def _project_checked_evidence(
    check: CapabilityInspectionCheck,
) -> ProjectExplainCheckedEvidence:
    if type(check) is not CapabilityInspectionCheck:
        raise TypeError("Slice 4 requires exact inspected checks.")
    _require_check_authority(check)
    return ProjectExplainCheckedEvidence(
        target_lookup=_project_lookup(check.target_lookup),
        provider_domain_complete=check.provider_domain_complete,
        provider_unknown_reason=(
            None
            if check.provider_unknown_reason is None
            else check.provider_unknown_reason.value
        ),
        provider_lookup=_project_lookup(check.provider_lookup),
    )


def _project_requirement_row(
    request: ProjectExplainRequirementRequest,
    inspection: CapabilityInspection,
    evaluations: tuple[ProjectExplainPackageTargetEvaluation, ...],
) -> ProjectExplainMatrixRow:
    if type(request) is not ProjectExplainRequirementRequest:
        raise TypeError("Slice 4 requires exact Slice 3 requirement requests.")
    if (
        inspection.requirement_declaration
        is not CapabilityInspectionRequirementDeclaration.DECLARED
        or inspection.requirement_namespace != request.collection.namespace
        or inspection.requirement_name != request.collection.name
        or request.occurrence_position >= len(inspection.requirements)
    ):
        raise ValueError("Slice 4 requirement collection authority is inconsistent.")
    requirement = inspection.requirements[request.occurrence_position]
    if (
        requirement.position != request.occurrence_position
        or not _key_matches(request.key, requirement)
        or len(requirement.cells) != len(evaluations)
    ):
        raise ValueError("Slice 4 requirement row authority is inconsistent.")
    cells = tuple(
        _project_cell(cell, evaluation)
        for cell, evaluation in zip(
            requirement.cells,
            evaluations,
            strict=True,
        )
    )
    return ProjectExplainMatrixRow(
        requirement_position=request.position,
        cells=cells,
    )


def _project_cell(
    cell: CapabilityInspectionCell,
    evaluation: ProjectExplainPackageTargetEvaluation,
) -> ProjectExplainMatrixCell:
    if (
        type(cell) is not CapabilityInspectionCell
        or cell.column_position != evaluation.target_position
    ):
        raise ValueError("Slice 4 requires exact inspected cell target order.")
    if evaluation.state is ProjectExplainEvaluationState.UNDECLARED:
        raise ValueError("Declared requirement rows cannot use UNDECLARED cells.")
    if evaluation.state is ProjectExplainEvaluationState.BLOCKED:
        if cell.check is not None:
            raise ValueError("BLOCKED inspected cells forbid a checked result.")
        return ProjectExplainMatrixCell(
            target_position=evaluation.target_position,
            state=ProjectExplainEvaluationState.BLOCKED,
            checked_status=None,
            evidence_posture=evaluation.evidence_posture,
            checked_evidence=None,
        )
    if type(cell.check) is not CapabilityInspectionCheck:
        raise ValueError("CHECKED inspected cells require exact checked evidence.")
    status = _project_status(cell.check.status)
    evidence = _project_checked_evidence(cell.check)
    return ProjectExplainMatrixCell(
        target_position=evaluation.target_position,
        state=ProjectExplainEvaluationState.CHECKED,
        checked_status=status,
        evidence_posture=_checked_posture(status),
        checked_evidence=evidence,
    )


def _project_status(status: CapabilityRequirementStatus) -> ProjectExplainCheckedStatus:
    if type(status) is not CapabilityRequirementStatus:
        raise ValueError("Slice 4 requires an exact inspected checked status.")
    return ProjectExplainCheckedStatus(status.value)


def _project_support(support: CapabilitySupport) -> ProjectExplainCapabilitySupport:
    if type(support) is not CapabilitySupport:
        raise ValueError("Slice 4 requires exact inspected capability support.")
    return ProjectExplainCapabilitySupport(support.value)


def _checked_posture(
    status: ProjectExplainCheckedStatus,
) -> ProjectExplainEvidencePosture:
    if status is ProjectExplainCheckedStatus.CONFLICT:
        return ProjectExplainEvidencePosture.CONFLICTING
    if status is ProjectExplainCheckedStatus.UNKNOWN:
        return ProjectExplainEvidencePosture.UNAVAILABLE
    return ProjectExplainEvidencePosture.DETERMINISTIC_DERIVATION


def _status_from_evidence(
    evidence: ProjectExplainCheckedEvidence,
) -> ProjectExplainCheckedStatus:
    target = evidence.target_lookup
    provider = evidence.provider_lookup
    if (
        target.variant is ProjectExplainLookupVariant.CONFLICT
        or provider.variant is ProjectExplainLookupVariant.CONFLICT
    ):
        return ProjectExplainCheckedStatus.CONFLICT
    if any(
        lookup.variant is ProjectExplainLookupVariant.FOUND
        and lookup.supports == (ProjectExplainCapabilitySupport.EXPLICITLY_UNSUPPORTED,)
        for lookup in (target, provider)
    ):
        return ProjectExplainCheckedStatus.UNSUPPORTED
    if provider.variant is ProjectExplainLookupVariant.ABSENT:
        return ProjectExplainCheckedStatus.ABSENT
    if (
        target.variant is ProjectExplainLookupVariant.UNKNOWN
        or provider.variant is ProjectExplainLookupVariant.UNKNOWN
    ):
        return ProjectExplainCheckedStatus.UNKNOWN
    if (
        target.variant is ProjectExplainLookupVariant.FOUND
        and target.supports == (ProjectExplainCapabilitySupport.SUPPORTED,)
        and provider.variant is ProjectExplainLookupVariant.FOUND
        and provider.supports == (ProjectExplainCapabilitySupport.SUPPORTED,)
    ):
        return ProjectExplainCheckedStatus.SATISFIED
    raise ValueError("Detached checked lookup algebra is inconsistent.")


def _validate_projection_references(
    matrix: ProjectExplainRequirementTargetMatrix,
    package_projection: ProjectExplainPackageRequirementProjection,
) -> None:
    target_count = len(matrix.targets)
    if len(matrix.package_target_evaluations) != (
        len(package_projection.packages) * target_count
    ):
        raise ValueError("Matrix package references do not cover every target.")
    for request, row in zip(
        package_projection.requirements,
        matrix.rows,
        strict=True,
    ):
        if row.requirement_position != request.position:
            raise ValueError("Matrix rows must retain exact Slice 3 requirement order.")
        offset = request.declared_by * target_count
        evaluations = matrix.package_target_evaluations[offset : offset + target_count]
        for cell, evaluation in zip(row.cells, evaluations, strict=True):
            if cell.state is not evaluation.state or (
                cell.state is ProjectExplainEvaluationState.BLOCKED
                and cell.evidence_posture is not evaluation.evidence_posture
            ):
                raise ValueError(
                    "Matrix cells must use their declaring package evaluation."
                )


def _require_detached_package_projection(
    projection: ProjectExplainPackageRequirementProjection,
) -> None:
    if type(projection) is not ProjectExplainPackageRequirementProjection:
        raise TypeError("Empty Slice 4 matrices require an exact Slice 3 projection.")
    ProjectExplainPackageRequirementProjection(
        root_package_position=projection.root_package_position,
        packages=projection.packages,
        requirement_collections=projection.requirement_collections,
        requirements=projection.requirements,
    )


def _require_column_authority(
    column: CapabilityInspectionColumn,
    position: int,
    context: CapabilityCheckingTargetContext,
    private_column: CapabilityCheckingTargetColumn,
) -> None:
    if (
        type(column) is not CapabilityInspectionColumn
        or type(context) is not CapabilityCheckingTargetContext
        or type(private_column) is not CapabilityCheckingTargetColumn
        or column.position != position
        or column.column is not private_column
        or private_column.position != position
        or private_column.context is not context
    ):
        raise ValueError("Slice 4 rejects grafted inspected target columns.")
    result = private_column.result
    expected_variant = (
        CapabilityInspectionColumnVariant.UNDECLARED
        if type(result) is PackageCapabilityRequirementsUndeclared
        else (
            CapabilityInspectionColumnVariant.BLOCKED
            if type(result) is PackageCapabilityRequirementsBlocked
            else CapabilityInspectionColumnVariant.CHECKED
        )
    )
    if (
        type(result)
        not in {
            PackageCapabilityRequirementsUndeclared,
            PackageCapabilityRequirementsBlocked,
            PackageCapabilityRequirementsChecked,
        }
        or column.variant is not expected_variant
    ):
        raise ValueError("Slice 4 rejects grafted inspected target state.")
    if (
        type(column.supplied_overlays) is not tuple
        or type(column.dependency_order) is not tuple
        or type(column.availability) is not tuple
        or type(column.blockers) is not tuple
    ):
        raise ValueError("Slice 4 rejects mutable inspected target collections.")

    composition = context.composition
    _require_profile_authority(column.base_profile)
    if column.base_profile.profile is not composition.base:
        raise ValueError("Slice 4 rejects a foreign inspected base profile.")
    for projected, authority in zip(
        column.supplied_overlays,
        composition.overlays,
        strict=True,
    ):
        _require_profile_authority(projected)
        if projected.profile is not authority:
            raise ValueError("Slice 4 rejects foreign inspected supplied overlays.")
    if len(column.supplied_overlays) != len(composition.overlays):
        raise ValueError("Slice 4 rejects grafted inspected supplied overlays.")
    for projected, authority in zip(
        column.dependency_order,
        composition.dependency_order,
        strict=True,
    ):
        _require_profile_authority(projected)
        if projected.profile is not authority:
            raise ValueError("Slice 4 rejects foreign inspected dependency order.")
    if len(column.dependency_order) != len(composition.dependency_order):
        raise ValueError("Slice 4 rejects grafted inspected dependency order.")

    occurrences = context.availability.occurrences
    if len(column.availability) != len(occurrences):
        raise ValueError("Slice 4 rejects grafted inspected availability.")
    for projected, authority in zip(column.availability, occurrences, strict=True):
        _require_availability_authority(projected)
        if projected.occurrence is not authority:
            raise ValueError("Slice 4 rejects foreign inspected availability.")

    private_blockers = (
        result.blockers if type(result) is PackageCapabilityRequirementsBlocked else ()
    )
    if len(column.blockers) != len(private_blockers):
        raise ValueError("Slice 4 rejects grafted inspected blockers.")
    for projected, authority in zip(
        column.blockers,
        private_blockers,
        strict=True,
    ):
        _require_blocker_authority(projected)
        if projected.blocker is not authority:
            raise ValueError("Slice 4 rejects foreign inspected blockers.")


def _require_requirement_authority(
    requirement: CapabilityInspectionRequirement,
    position: int,
    private_row: CapabilityCheckingMatrixRow,
    private_columns: tuple[CapabilityCheckingTargetColumn, ...],
) -> None:
    if (
        type(requirement) is not CapabilityInspectionRequirement
        or type(private_row) is not CapabilityCheckingMatrixRow
        or requirement.position != position
        or requirement.row is not private_row
        or requirement.key.key is not private_row.occurrence.key
        or type(requirement.cells) is not tuple
        or len(requirement.cells) != len(private_row.cells)
        or len(requirement.cells) != len(private_columns)
    ):
        raise ValueError("Slice 4 rejects grafted inspected requirement rows.")
    for target_position, (cell, private_cell, private_column) in enumerate(
        zip(
            requirement.cells,
            private_row.cells,
            private_columns,
            strict=True,
        )
    ):
        if (
            type(cell) is not CapabilityInspectionCell
            or type(private_cell) is not CapabilityCheckingMatrixCell
            or cell.column_position != target_position
            or cell.cell is not private_cell
            or private_cell.column is not private_column
        ):
            raise ValueError("Slice 4 rejects grafted inspected matrix cells.")
        if private_cell.check is None:
            if cell.check is not None:
                raise ValueError("Slice 4 rejects a fabricated inspected check.")
        elif (
            type(cell.check) is not CapabilityInspectionCheck
            or cell.check.check is not private_cell.check
        ):
            raise ValueError("Slice 4 rejects a foreign inspected check.")
        else:
            _require_check_authority(cell.check)


def _require_profile_authority(profile: CapabilityInspectionProfile) -> None:
    if type(profile) is not CapabilityInspectionProfile:
        raise ValueError("Slice 4 requires an exact inspected profile.")
    private = profile.profile
    if (
        type(profile.kind) is not CapabilityProfileKind
        or type(profile.target_kind) is not CapabilityProfileTargetKind
        or type(private) is not StaticCapabilityProfile
        or profile.schema_version is not private.schema_version
        or profile.namespace != private.profile.identity.namespace
        or profile.name != private.profile.identity.name
        or profile.profile_release != private.profile.release
        or profile.kind is not private.kind
        or profile.target_kind is not private.target.kind
        or profile.database_family != private.target.family
        or profile.target_release != private.target.release
        or profile.extension_identity != private.target.extension_identity
        or profile.extension_release != private.target.extension_release
    ):
        raise ValueError("Slice 4 rejects a grafted inspected profile.")


def _require_availability_authority(
    occurrence: CapabilityInspectionAvailabilityOccurrence,
) -> None:
    if type(occurrence) is not CapabilityInspectionAvailabilityOccurrence:
        raise ValueError("Slice 4 requires exact inspected availability.")
    private = occurrence.occurrence
    if (
        type(occurrence.owner_kind) is not CapabilityInspectionAvailabilityOwnerKind
        or type(private) is not CapabilityProfileAvailabilityOccurrence
        or occurrence.owner_position != private.position
        or occurrence.profile.profile is not private.profile
    ):
        raise ValueError("Slice 4 rejects grafted inspected availability.")
    _require_profile_authority(occurrence.profile)
    if private.owner is CompilerCapabilityProfileAvailabilityAuthority.COMPILER:
        if (
            occurrence.owner_kind
            is not CapabilityInspectionAvailabilityOwnerKind.COMPILER
            or occurrence.project_path is not None
        ):
            raise ValueError("Slice 4 rejects grafted compiler availability.")
        return
    if (
        type(private.owner) is not ProjectRoot
        or occurrence.owner_kind
        is not CapabilityInspectionAvailabilityOwnerKind.PROJECT
        or occurrence.project_path != private.owner.path
    ):
        raise ValueError("Slice 4 rejects grafted project availability.")


def _require_blocker_authority(blocker: CapabilityInspectionBlocker) -> None:
    if type(blocker) is not CapabilityInspectionBlocker:
        raise ValueError("Slice 4 requires an exact inspected blocker.")
    private = blocker.blocker
    if (
        type(blocker.kind) is not SelectedProfileAvailabilityBlockerKind
        or type(private) is not SelectedProfileAvailabilityBlocker
        or blocker.kind is not private.kind
        or blocker.selected_profile.profile is not private.profile
    ):
        raise ValueError("Slice 4 rejects a grafted inspected blocker.")
    _require_profile_authority(blocker.selected_profile)
    bucket = private.bucket
    if bucket is None:
        if blocker.bucket_profile is not None or blocker.bucket_occurrences:
            raise ValueError("Slice 4 rejects fabricated blocker bucket evidence.")
        return
    if (
        blocker.bucket_profile is None
        or blocker.bucket_profile.profile is not bucket.profile
        or type(blocker.bucket_occurrences) is not tuple
        or len(blocker.bucket_occurrences) != len(bucket.occurrences)
    ):
        raise ValueError("Slice 4 rejects grafted blocker bucket evidence.")
    _require_profile_authority(blocker.bucket_profile)
    for projected, authority in zip(
        blocker.bucket_occurrences,
        bucket.occurrences,
        strict=True,
    ):
        _require_availability_authority(projected)
        if projected.occurrence is not authority:
            raise ValueError("Slice 4 rejects foreign blocker bucket evidence.")


def _require_check_authority(check: CapabilityInspectionCheck) -> None:
    if type(check) is not CapabilityInspectionCheck:
        raise ValueError("Slice 4 requires an exact inspected check.")
    private = check.check
    if (
        type(private) is not CapabilityRequirementCheck
        or check.status is not private.status
        or check.provider_domain_complete is not private.provider_inputs.domain_complete
        or check.provider_unknown_reason is not private.provider_inputs.unknown_reason
        or check.target_lookup.result is not private.target_result
        or check.provider_lookup.result is not private.provider_result
    ):
        raise ValueError("Slice 4 rejects grafted inspected checked authority.")
    _require_lookup_authority(check.target_lookup)
    _require_lookup_authority(check.provider_lookup)


def _require_lookup_authority(lookup: CapabilityInspectionLookup) -> None:
    if (
        type(lookup) is not CapabilityInspectionLookup
        or type(lookup.variant) is not CapabilityInspectionLookupVariant
        or type(lookup.facts) is not tuple
        or any(type(fact) is not CapabilityInspectionFact for fact in lookup.facts)
    ):
        raise ValueError("Slice 4 rejects malformed inspected lookup evidence.")
    result = lookup.result
    if type(result) is Found:
        valid = (
            lookup.variant is CapabilityInspectionLookupVariant.FOUND
            and lookup.reason is None
            and len(lookup.facts) == 1
            and lookup.facts[0].fact is result.fact
        )
    elif type(result) is Absent:
        valid = (
            lookup.variant is CapabilityInspectionLookupVariant.ABSENT
            and lookup.reason is result.reason
            and not lookup.facts
        )
    elif type(result) is Unknown:
        valid = (
            lookup.variant is CapabilityInspectionLookupVariant.UNKNOWN
            and lookup.reason is result.reason
            and not lookup.facts
        )
    elif type(result) is Conflict:
        valid = (
            lookup.variant is CapabilityInspectionLookupVariant.CONFLICT
            and lookup.reason is result.reason
            and len(lookup.facts) == len(result.evidence)
            and all(
                projected.fact is authority
                for projected, authority in zip(
                    lookup.facts,
                    result.evidence,
                    strict=True,
                )
            )
        )
    else:
        valid = False
    if not valid:
        raise ValueError("Slice 4 rejects grafted inspected lookup evidence.")
    for fact in lookup.facts:
        if (
            type(fact.fact) is not CapabilityFact
            or fact.support is not fact.fact.support
        ):
            raise ValueError("Slice 4 rejects grafted inspected support evidence.")


def _key_matches(
    public: ProjectExplainCapabilityKey,
    private: CapabilityInspectionRequirement,
) -> bool:
    key = private.key
    return (
        public.domain is key.domain
        and public.subject == key.subject
        and public.operation == key.operation
        and public.operands == key.operands
        and public.context == key.context
        and public.dialect == key.dialect
        and public.extension == key.extension
    )


def _profile_reference(
    profile: ProjectExplainCapabilityProfile,
) -> tuple[str, str, str]:
    return profile.namespace, profile.name, profile.profile_release


def _require_non_empty_text(value: object, label: str) -> None:
    if type(value) is not str:
        raise TypeError(f"Project Explain {label} must be exact text.")
    if not value:
        raise ValueError(f"Project Explain {label} must be non-empty.")


def _require_position(value: object, label: str) -> None:
    if type(value) is not int:
        raise TypeError(f"Project Explain {label} must be an exact integer.")
    if value < 0:
        raise ValueError(f"Project Explain {label} must be non-negative.")


def _require_exact_tuple(values: object, item_type: type, label: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"Project Explain {label} must be an exact tuple.")
    if any(type(value) is not item_type for value in values):
        raise TypeError(
            f"Project Explain {label} must contain exact {item_type.__name__} values."
        )


def _require_dense_tuple(values: object, item_type: type, label: str) -> None:
    _require_exact_tuple(values, item_type, label)
    assert type(values) is tuple
    if tuple(value.position for value in values) != tuple(range(len(values))):
        raise ValueError(
            f"Project Explain {label} positions must be dense and ordered."
        )
