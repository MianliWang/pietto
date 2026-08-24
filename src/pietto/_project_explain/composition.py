"""Private Project Explain payload composition and artifact-local references."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .compatibility_matrix_projection import (
    ProjectExplainEvaluationState,
    ProjectExplainRequirementTargetMatrix,
    _require_exact_tuple,
    _require_position,
)
from .extension_catalog_evidence_projection import (
    ProjectExplainExtensionCatalogContextEvidence,
    ProjectExplainExtensionCatalogEvidenceProjection,
    ProjectExplainExtensionRequirementEvidence,
)
from .package_requirement_projection import (
    ProjectExplainPackageRequirementProjection,
    ProjectExplainRequirementRequest,
)
from .portability_projection import (
    ProjectExplainProjectPortability,
    _derive_project_portability,
    _require_projection_alignment,
)

__all__: tuple[str, ...] = ()


class ProjectExplainArtifactReferenceKind(StrEnum):
    PACKAGE = "package"
    REQUIREMENT = "requirement"
    TARGET = "target"
    PACKAGE_TARGET_EVALUATION = "package_target_evaluation"
    MATRIX_CELL = "matrix_cell"
    EXTENSION_CATALOG_CONTEXT = "extension_catalog_context"
    EXTENSION_CATALOG = "extension_catalog"
    EXTENSION_CATALOG_SOURCE = "extension_catalog_source"
    EXTENSION_REQUIREMENT_EVIDENCE = "extension_requirement_evidence"
    REQUIREMENT_PORTABILITY = "requirement_portability"
    PROJECT_PORTABILITY = "project_portability"


_REFERENCE_ARITIES = {
    ProjectExplainArtifactReferenceKind.PACKAGE: 1,
    ProjectExplainArtifactReferenceKind.REQUIREMENT: 1,
    ProjectExplainArtifactReferenceKind.TARGET: 1,
    ProjectExplainArtifactReferenceKind.PACKAGE_TARGET_EVALUATION: 2,
    ProjectExplainArtifactReferenceKind.MATRIX_CELL: 2,
    ProjectExplainArtifactReferenceKind.EXTENSION_CATALOG_CONTEXT: 2,
    ProjectExplainArtifactReferenceKind.EXTENSION_CATALOG: 3,
    ProjectExplainArtifactReferenceKind.EXTENSION_CATALOG_SOURCE: 4,
    ProjectExplainArtifactReferenceKind.EXTENSION_REQUIREMENT_EVIDENCE: 3,
    ProjectExplainArtifactReferenceKind.REQUIREMENT_PORTABILITY: 1,
    ProjectExplainArtifactReferenceKind.PROJECT_PORTABILITY: 0,
}


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainArtifactReference:
    kind: ProjectExplainArtifactReferenceKind
    positions: tuple[int, ...]

    def __post_init__(self) -> None:
        _require_reference_shape(self)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainRequirementTargetExplanation:
    target: ProjectExplainArtifactReference
    evaluation: ProjectExplainArtifactReference
    matrix_cell: ProjectExplainArtifactReference
    extension_evidence: ProjectExplainArtifactReference | None
    source_evidence: tuple[ProjectExplainArtifactReference, ...]

    def __post_init__(self) -> None:
        _require_reference_kind(
            self.target,
            ProjectExplainArtifactReferenceKind.TARGET,
            "target explanation target",
        )
        _require_reference_kind(
            self.evaluation,
            ProjectExplainArtifactReferenceKind.PACKAGE_TARGET_EVALUATION,
            "target explanation evaluation",
        )
        _require_reference_kind(
            self.matrix_cell,
            ProjectExplainArtifactReferenceKind.MATRIX_CELL,
            "target explanation matrix cell",
        )
        if self.extension_evidence is not None:
            _require_reference_kind(
                self.extension_evidence,
                ProjectExplainArtifactReferenceKind.EXTENSION_REQUIREMENT_EVIDENCE,
                "target explanation extension evidence",
            )
        _require_exact_tuple(
            self.source_evidence,
            ProjectExplainArtifactReference,
            "target explanation source evidence",
        )
        for reference in self.source_evidence:
            _require_reference_kind(
                reference,
                ProjectExplainArtifactReferenceKind.EXTENSION_CATALOG_SOURCE,
                "target explanation source evidence",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainRequirementExplanation:
    request: ProjectExplainArtifactReference
    declared_by: ProjectExplainArtifactReference
    requested_by: ProjectExplainArtifactReference
    targets: tuple[ProjectExplainRequirementTargetExplanation, ...]
    portability: ProjectExplainArtifactReference

    def __post_init__(self) -> None:
        _require_reference_kind(
            self.request,
            ProjectExplainArtifactReferenceKind.REQUIREMENT,
            "requirement explanation request",
        )
        _require_reference_kind(
            self.declared_by,
            ProjectExplainArtifactReferenceKind.PACKAGE,
            "requirement explanation declaring package",
        )
        _require_reference_kind(
            self.requested_by,
            ProjectExplainArtifactReferenceKind.PACKAGE,
            "requirement explanation requesting package",
        )
        _require_exact_tuple(
            self.targets,
            ProjectExplainRequirementTargetExplanation,
            "requirement target explanations",
        )
        _require_reference_kind(
            self.portability,
            ProjectExplainArtifactReferenceKind.REQUIREMENT_PORTABILITY,
            "requirement explanation portability",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainPayload:
    package_requirements: ProjectExplainPackageRequirementProjection
    compatibility: ProjectExplainRequirementTargetMatrix
    extension_catalog_evidence: ProjectExplainExtensionCatalogEvidenceProjection
    portability: ProjectExplainProjectPortability
    requirement_explanations: tuple[ProjectExplainRequirementExplanation, ...]

    def __post_init__(self) -> None:
        if (
            type(self.package_requirements)
            is not ProjectExplainPackageRequirementProjection
        ):
            raise TypeError(
                "Project Explain payloads require an exact Slice 3 section."
            )
        if type(self.compatibility) is not ProjectExplainRequirementTargetMatrix:
            raise TypeError(
                "Project Explain payloads require an exact Slice 4 section."
            )
        if (
            type(self.extension_catalog_evidence)
            is not ProjectExplainExtensionCatalogEvidenceProjection
        ):
            raise TypeError(
                "Project Explain payloads require an exact Slice 5 section."
            )
        if type(self.portability) is not ProjectExplainProjectPortability:
            raise TypeError(
                "Project Explain payloads require an exact Slice 6 section."
            )
        _require_exact_tuple(
            self.requirement_explanations,
            ProjectExplainRequirementExplanation,
            "requirement explanations",
        )


def _resolve_project_explain_reference(
    payload: ProjectExplainPayload,
    reference: ProjectExplainArtifactReference,
) -> object:
    """Resolve one exact artifact-local coordinate without semantic fallback."""

    if type(payload) is not ProjectExplainPayload:
        raise TypeError(
            "Reference resolution requires an exact Project Explain payload."
        )
    if type(reference) is not ProjectExplainArtifactReference:
        raise TypeError("Reference resolution requires an exact artifact reference.")
    _require_reference_shape(reference)
    positions = reference.positions
    kind = reference.kind

    if kind is ProjectExplainArtifactReferenceKind.PACKAGE:
        package = _at(payload.package_requirements.packages, positions[0], "package")
        if package.position != positions[0]:
            raise ValueError("Package references require exact position authority.")
        return package
    if kind is ProjectExplainArtifactReferenceKind.REQUIREMENT:
        requirement = _at(
            payload.package_requirements.requirements,
            positions[0],
            "requirement",
        )
        if requirement.position != positions[0]:
            raise ValueError("Requirement references require exact position authority.")
        return requirement
    if kind is ProjectExplainArtifactReferenceKind.TARGET:
        target = _at(payload.compatibility.targets, positions[0], "target")
        if target.position != positions[0]:
            raise ValueError("Target references require exact position authority.")
        return target
    if kind is ProjectExplainArtifactReferenceKind.PACKAGE_TARGET_EVALUATION:
        package_position, target_position = positions
        _at(payload.package_requirements.packages, package_position, "package")
        _at(payload.compatibility.targets, target_position, "target")
        target_count = len(payload.compatibility.targets)
        evaluation = _at(
            payload.compatibility.package_target_evaluations,
            package_position * target_count + target_position,
            "package-target evaluation",
        )
        if (
            evaluation.package_position != package_position
            or evaluation.target_position != target_position
        ):
            raise ValueError(
                "Package-target evaluation references require exact matrix order."
            )
        return evaluation
    if kind is ProjectExplainArtifactReferenceKind.MATRIX_CELL:
        requirement_position, target_position = positions
        row = _at(
            payload.compatibility.rows,
            requirement_position,
            "matrix row",
        )
        cell = _at(row.cells, target_position, "matrix cell")
        if (
            row.requirement_position != requirement_position
            or cell.target_position != target_position
        ):
            raise ValueError("Matrix-cell references require exact matrix order.")
        return cell
    if kind is ProjectExplainArtifactReferenceKind.EXTENSION_CATALOG_CONTEXT:
        return _extension_context(payload, positions[0], positions[1])
    if kind is ProjectExplainArtifactReferenceKind.EXTENSION_CATALOG:
        context = _extension_context(payload, positions[0], positions[1])
        catalog = _at(context.catalogs, positions[2], "extension catalog")
        if catalog.position != positions[2]:
            raise ValueError("Extension catalog references require exact order.")
        return catalog
    if kind is ProjectExplainArtifactReferenceKind.EXTENSION_CATALOG_SOURCE:
        context = _extension_context(payload, positions[0], positions[1])
        catalog = _at(context.catalogs, positions[2], "extension catalog")
        source = _at(
            catalog.source_occurrences,
            positions[3],
            "extension catalog source",
        )
        if catalog.position != positions[2] or source.position != positions[3]:
            raise ValueError("Extension catalog source references require exact order.")
        return source
    if kind is ProjectExplainArtifactReferenceKind.EXTENSION_REQUIREMENT_EVIDENCE:
        context = _extension_context(payload, positions[0], positions[1])
        matches = tuple(
            requirement
            for requirement in context.requirements
            if requirement.requirement_position == positions[2]
        )
        if len(matches) != 1:
            raise ValueError(
                "Extension requirement references require one exact evidence record."
            )
        return matches[0]
    if kind is ProjectExplainArtifactReferenceKind.REQUIREMENT_PORTABILITY:
        portability = _at(
            payload.portability.requirements,
            positions[0],
            "requirement portability",
        )
        if portability.requirement_position != positions[0]:
            raise ValueError("Requirement portability references require exact order.")
        return portability
    if kind is ProjectExplainArtifactReferenceKind.PROJECT_PORTABILITY:
        return payload.portability
    raise ValueError("Unsupported Project Explain artifact reference kind.")


def _compose_project_explain_payload(
    package_requirements: ProjectExplainPackageRequirementProjection,
    compatibility: ProjectExplainRequirementTargetMatrix,
    extension_catalog_evidence: ProjectExplainExtensionCatalogEvidenceProjection,
    portability: ProjectExplainProjectPortability,
) -> ProjectExplainPayload:
    """Compose exact detached sections into one validated in-memory payload."""

    _require_projection_alignment(package_requirements, compatibility)
    if (
        type(extension_catalog_evidence)
        is not ProjectExplainExtensionCatalogEvidenceProjection
    ):
        raise TypeError("Slice 7 requires an exact Slice 5 projection.")
    if type(portability) is not ProjectExplainProjectPortability:
        raise TypeError("Slice 7 requires an exact Slice 6 projection.")
    if portability != _derive_project_portability(
        package_requirements,
        compatibility,
    ):
        raise ValueError("Slice 7 requires the canonical Slice 6 portability result.")
    _validate_extension_cross_section(
        package_requirements,
        compatibility,
        extension_catalog_evidence,
    )
    explanations = tuple(
        _build_requirement_explanation(
            request,
            compatibility,
            extension_catalog_evidence,
        )
        for request in package_requirements.requirements
    )
    payload = ProjectExplainPayload(
        package_requirements=package_requirements,
        compatibility=compatibility,
        extension_catalog_evidence=extension_catalog_evidence,
        portability=portability,
        requirement_explanations=explanations,
    )
    _validate_generated_references(payload)
    return payload


def _build_requirement_explanation(
    request: ProjectExplainRequirementRequest,
    compatibility: ProjectExplainRequirementTargetMatrix,
    extension_catalog_evidence: ProjectExplainExtensionCatalogEvidenceProjection,
) -> ProjectExplainRequirementExplanation:
    target_explanations: list[ProjectExplainRequirementTargetExplanation] = []
    for target in compatibility.targets:
        cell = compatibility.rows[request.position].cells[target.position]
        extension_reference = None
        source_references: tuple[ProjectExplainArtifactReference, ...] = ()
        if (
            request.key.domain.value == "extension_signature"
            and cell.state is ProjectExplainEvaluationState.CHECKED
        ):
            matches = _matching_extension_evidence(
                extension_catalog_evidence,
                request.declared_by,
                target.position,
                request.position,
            )
            if len(matches) != 1:
                raise ValueError(
                    "Checked extension cells require one exact evidence record."
                )
            context, evidence = matches[0]
            extension_reference = ProjectExplainArtifactReference(
                kind=(
                    ProjectExplainArtifactReferenceKind.EXTENSION_REQUIREMENT_EVIDENCE
                ),
                positions=(request.declared_by, target.position, request.position),
            )
            source_references = _source_references(context, evidence)
        target_explanations.append(
            ProjectExplainRequirementTargetExplanation(
                target=ProjectExplainArtifactReference(
                    kind=ProjectExplainArtifactReferenceKind.TARGET,
                    positions=(target.position,),
                ),
                evaluation=ProjectExplainArtifactReference(
                    kind=(
                        ProjectExplainArtifactReferenceKind.PACKAGE_TARGET_EVALUATION
                    ),
                    positions=(request.declared_by, target.position),
                ),
                matrix_cell=ProjectExplainArtifactReference(
                    kind=ProjectExplainArtifactReferenceKind.MATRIX_CELL,
                    positions=(request.position, target.position),
                ),
                extension_evidence=extension_reference,
                source_evidence=source_references,
            )
        )
    return ProjectExplainRequirementExplanation(
        request=ProjectExplainArtifactReference(
            kind=ProjectExplainArtifactReferenceKind.REQUIREMENT,
            positions=(request.position,),
        ),
        declared_by=ProjectExplainArtifactReference(
            kind=ProjectExplainArtifactReferenceKind.PACKAGE,
            positions=(request.declared_by,),
        ),
        requested_by=ProjectExplainArtifactReference(
            kind=ProjectExplainArtifactReferenceKind.PACKAGE,
            positions=(request.requested_by,),
        ),
        targets=tuple(target_explanations),
        portability=ProjectExplainArtifactReference(
            kind=ProjectExplainArtifactReferenceKind.REQUIREMENT_PORTABILITY,
            positions=(request.position,),
        ),
    )


def _validate_extension_cross_section(
    package_requirements: ProjectExplainPackageRequirementProjection,
    compatibility: ProjectExplainRequirementTargetMatrix,
    projection: ProjectExplainExtensionCatalogEvidenceProjection,
) -> None:
    previous_coordinate: tuple[int, int] | None = None
    for context in projection.contexts:
        coordinate = (context.package_position, context.target_position)
        if previous_coordinate is not None and coordinate <= previous_coordinate:
            raise ValueError(
                "Extension catalog contexts must retain package by target order."
            )
        previous_coordinate = coordinate
        _at(
            package_requirements.packages,
            context.package_position,
            "catalog context package",
        )
        _at(
            compatibility.targets,
            context.target_position,
            "catalog context target",
        )
        collections = tuple(
            collection
            for collection in package_requirements.requirement_collections
            if collection.declared_by == context.package_position
            and collection.identity == context.collection
        )
        if len(collections) != 1:
            raise ValueError(
                "Extension catalog contexts require one exact Slice 3 collection."
            )
        if tuple(catalog.position for catalog in context.catalogs) != tuple(
            range(len(context.catalogs))
        ):
            raise ValueError("Extension catalogs must retain dense context order.")
        for catalog in context.catalogs:
            if tuple(source.position for source in catalog.source_occurrences) != tuple(
                range(len(catalog.source_occurrences))
            ):
                raise ValueError(
                    "Extension catalog sources must retain dense occurrence order."
                )
        for evidence in context.requirements:
            request = _at(
                package_requirements.requirements,
                evidence.requirement_position,
                "extension requirement",
            )
            if (
                request.key.domain.value != "extension_signature"
                or request.declared_by != context.package_position
                or request.collection != context.collection
            ):
                raise ValueError(
                    "Extension evidence must name its exact Slice 3 request context."
                )
            cell = compatibility.rows[request.position].cells[context.target_position]
            if cell.state is not ProjectExplainEvaluationState.CHECKED:
                raise ValueError("Non-checked cells forbid extension evidence.")
            if evidence.selected_catalog_position is not None:
                catalog = _at(
                    context.catalogs,
                    evidence.selected_catalog_position,
                    "selected extension catalog",
                )
                if catalog.position != evidence.selected_catalog_position:
                    raise ValueError("Selected catalog positions must retain order.")

    for request in package_requirements.requirements:
        for target in compatibility.targets:
            matches = _matching_extension_evidence(
                projection,
                request.declared_by,
                target.position,
                request.position,
            )
            cell = compatibility.rows[request.position].cells[target.position]
            expected = (
                request.key.domain.value == "extension_signature"
                and cell.state is ProjectExplainEvaluationState.CHECKED
            )
            if expected and len(matches) != 1:
                raise ValueError(
                    "Checked extension cells require complete Slice 5 evidence."
                )
            if not expected and matches:
                raise ValueError(
                    "Blocked or non-extension cells forbid Slice 5 evidence."
                )


def _matching_extension_evidence(
    projection: ProjectExplainExtensionCatalogEvidenceProjection,
    package_position: int,
    target_position: int,
    requirement_position: int,
) -> tuple[
    tuple[
        ProjectExplainExtensionCatalogContextEvidence,
        ProjectExplainExtensionRequirementEvidence,
    ],
    ...,
]:
    # ponytail: linear scans suit local artifacts; index if projection scale matters.
    return tuple(
        (context, evidence)
        for context in projection.contexts
        if context.package_position == package_position
        and context.target_position == target_position
        for evidence in context.requirements
        if evidence.requirement_position == requirement_position
    )


def _source_references(
    context: ProjectExplainExtensionCatalogContextEvidence,
    evidence: ProjectExplainExtensionRequirementEvidence,
) -> tuple[ProjectExplainArtifactReference, ...]:
    source_positions = tuple(
        position
        for entry in (
            (() if evidence.exact_group is None else evidence.exact_group.entries)
            + evidence.unmodeled_blockers
        )
        for position in entry.source_positions
    ) + tuple(
        position
        for claim in (
            () if evidence.completeness is None else evidence.completeness.claims
        )
        for position in claim.source_positions
    )
    if not source_positions:
        return ()
    selected = evidence.selected_catalog_position
    if selected is None:
        raise ValueError("Source evidence requires a selected extension catalog.")
    referenced = frozenset((selected, position) for position in source_positions)
    references = tuple(
        ProjectExplainArtifactReference(
            kind=ProjectExplainArtifactReferenceKind.EXTENSION_CATALOG_SOURCE,
            positions=(
                context.package_position,
                context.target_position,
                catalog.position,
                source.position,
            ),
        )
        for catalog in context.catalogs
        for source in catalog.source_occurrences
        if (catalog.position, source.position) in referenced
    )
    if len(references) != len(referenced):
        raise ValueError("Source evidence must resolve to exact catalog occurrences.")
    return references


def _validate_generated_references(payload: ProjectExplainPayload) -> None:
    for explanation in payload.requirement_explanations:
        for reference in (
            explanation.request,
            explanation.declared_by,
            explanation.requested_by,
            explanation.portability,
        ):
            _resolve_project_explain_reference(payload, reference)
        for target in explanation.targets:
            for reference in (
                target.target,
                target.evaluation,
                target.matrix_cell,
                target.extension_evidence,
                *target.source_evidence,
            ):
                if reference is not None:
                    _resolve_project_explain_reference(payload, reference)
    _resolve_project_explain_reference(
        payload,
        ProjectExplainArtifactReference(
            kind=ProjectExplainArtifactReferenceKind.PROJECT_PORTABILITY,
            positions=(),
        ),
    )


def _extension_context(
    payload: ProjectExplainPayload,
    package_position: int,
    target_position: int,
) -> ProjectExplainExtensionCatalogContextEvidence:
    matches = tuple(
        context
        for context in payload.extension_catalog_evidence.contexts
        if context.package_position == package_position
        and context.target_position == target_position
    )
    if len(matches) != 1:
        raise ValueError("Extension context references require one exact context.")
    return matches[0]


def _require_reference_kind(
    reference: object,
    kind: ProjectExplainArtifactReferenceKind,
    label: str,
) -> None:
    if type(reference) is not ProjectExplainArtifactReference:
        raise TypeError(f"Project Explain {label} must be an exact reference.")
    if reference.kind is not kind:
        raise ValueError(f"Project Explain {label} has the wrong reference kind.")


def _require_reference_shape(reference: ProjectExplainArtifactReference) -> None:
    if type(reference.kind) is not ProjectExplainArtifactReferenceKind:
        raise TypeError("Artifact references require an exact kind.")
    if type(reference.positions) is not tuple:
        raise TypeError("Artifact reference positions must be an exact tuple.")
    for position in reference.positions:
        _require_position(position, "artifact reference position")
    if len(reference.positions) != _REFERENCE_ARITIES[reference.kind]:
        raise ValueError("Artifact reference arity disagrees with its kind.")


def _at[ItemT](
    values: tuple[ItemT, ...],
    position: int,
    label: str,
) -> ItemT:
    if type(values) is not tuple:
        raise TypeError(f"Project Explain {label} values must be an exact tuple.")
    _require_position(position, label)
    if position >= len(values):
        raise ValueError(f"Project Explain {label} position is out of range.")
    return values[position]
