"""Private extension-catalog evidence projection for Project Explain v1."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from pietto._project.capability_inspection import (
    CapabilityInspectionCheck,
    CapabilityInspectionFactSet,
)
from pietto._project.extension_catalog_inspection import (
    ExtensionCatalogInspection,
    ExtensionCatalogInspectionAggregateEntry,
    ExtensionCatalogInspectionAvailabilityDeclaration,
    ExtensionCatalogInspectionCastEntry,
    ExtensionCatalogInspectionCatalog,
    ExtensionCatalogInspectionCatalogReference,
    ExtensionCatalogInspectionCallableIdentity,
    ExtensionCatalogInspectionCompletenessGroup,
    ExtensionCatalogInspectionExactEntryGroup,
    ExtensionCatalogInspectionFactSet,
    ExtensionCatalogInspectionFormat,
    ExtensionCatalogInspectionLookupScope,
    ExtensionCatalogInspectionNativeTypeEntry,
    ExtensionCatalogInspectionOperatorEntry,
    ExtensionCatalogInspectionOperatorIdentity,
    ExtensionCatalogInspectionProviderOccurrence,
    ExtensionCatalogInspectionScalarFunctionEntry,
    ExtensionCatalogInspectionSelection,
    ExtensionCatalogInspectionTarget,
    ExtensionCatalogInspectionCastIdentity,
    ExtensionCatalogInspectionTypeReference,
)
from pietto._project.extension_signature_provider import (
    ExtensionSignatureProviderContext,
)
from pietto._project.package_inspection import PackageInspectionFactSet
from pietto.semantic.extension_signature_requirements import (
    extension_signature_dialect_family_bridge,
)
from pietto.semantic.model import TypeKind

from .compatibility_matrix_projection import (
    ProjectExplainEvaluationState,
    ProjectExplainMatrixCell,
    ProjectExplainRequirementTargetMatrix,
    _project_empty_requirement_target_matrix,
    _project_requirement_target_matrix,
)
from .model import (
    ProjectExplainEvidencePosture,
    ProjectExplainLogicalPath,
    ProjectExplainLogicalPathKind,
)
from .package_requirement_projection import (
    ProjectExplainPackageRequirementProjection,
    ProjectExplainRequirementCollectionIdentity,
    ProjectExplainRequirementRequest,
    _project_package_requirement_provenance,
)

__all__: tuple[str, ...] = ()

_LOWER_HEX = frozenset("0123456789abcdef")


class ProjectExplainCatalogTypeReferenceKind(StrEnum):
    PIETTO_LOGICAL = "pietto_logical"
    POSTGRES_BUILTIN = "postgres_builtin"
    EXTENSION_NATIVE = "extension_native"


class ProjectExplainCatalogEntryFamily(StrEnum):
    NATIVE_TYPE = "native_type"
    SCALAR_FUNCTION = "scalar_function"
    AGGREGATE = "aggregate"
    OPERATOR = "operator"
    CAST = "cast"


class ProjectExplainPostgreSQLOperatorArity(StrEnum):
    UNARY = "unary"
    BINARY = "binary"


class ProjectExplainCatalogSelectionOutcome(StrEnum):
    UNDECLARED = "undeclared"
    SELECTED = "selected"
    AMBIGUOUS = "ambiguous"
    CONFLICT = "conflict"


class ProjectExplainCatalogAvailabilityOwnerKind(StrEnum):
    COMPILER = "compiler"
    PROJECT = "project"


class ProjectExplainCatalogMatchability(StrEnum):
    EXACT_MATCHABLE = "exact_matchable"
    CATALOGED_UNMODELED = "cataloged_unmodeled"


class ProjectExplainCatalogExposure(StrEnum):
    DIRECT_SQL_SURFACE = "direct_sql_surface"
    IMPLEMENTATION_SUPPORT = "implementation_support"
    UNCLASSIFIED = "unclassified"


class ProjectExplainCatalogExactGroupState(StrEnum):
    UNIQUE = "unique"
    CONSISTENT_DUPLICATE = "consistent_duplicate"
    EVIDENCE_CONFLICT = "evidence_conflict"


class ProjectExplainCatalogCompletenessState(StrEnum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    CONFLICT = "conflict"


class ProjectExplainCatalogCompletenessClaimKind(StrEnum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


class ProjectExplainCatalogUnmodeledReason(StrEnum):
    UNSUPPORTED_TYPE_FORM = "unsupported_type_form"
    DEFAULT_ARGUMENTS = "default_arguments"
    VARIADIC_ARGUMENTS = "variadic_arguments"
    POLYMORPHIC_OR_PSEUDO_TYPE = "polymorphic_or_pseudo_type"
    SET_RETURNING = "set_returning"
    TABLE_OR_COMPOSITE_RETURN = "table_or_composite_return"
    ORDERED_SET_OR_HYPOTHETICAL_SET_AGGREGATE = (
        "ordered_set_or_hypothetical_set_aggregate"
    )
    DIRECT_ARGUMENTS = "direct_arguments"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainExtensionCatalogReference:
    namespace: str
    name: str
    release: str

    def __post_init__(self) -> None:
        _require_text(self.namespace, "catalog namespace")
        _require_text(self.name, "catalog name")
        _require_text(self.release, "catalog release")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainExtensionCatalogTarget:
    database_family: str
    database_release: str
    extension_identity: str
    extension_release: str

    def __post_init__(self) -> None:
        _require_text(self.database_family, "catalog database family")
        _require_text(self.database_release, "catalog database release")
        _require_text(self.extension_identity, "catalog extension identity")
        _require_text(self.extension_release, "catalog extension release")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainExtensionCatalogSourceOccurrence:
    position: int
    source_authority: str
    source_revision: str
    source_locator: ProjectExplainLogicalPath
    curation: str

    def __post_init__(self) -> None:
        _require_position(self.position, "catalog source position")
        _require_text(self.source_authority, "catalog source authority")
        _require_text(self.source_revision, "catalog source revision")
        if (
            type(self.source_locator) is not ProjectExplainLogicalPath
            or self.source_locator.kind
            is not ProjectExplainLogicalPathKind.UPSTREAM_SOURCE_LOCATOR
        ):
            raise ValueError(
                "Catalog sources require an upstream-source logical locator."
            )
        _require_text(self.curation, "catalog source curation")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainExtensionCatalogSummary:
    position: int
    reference: ProjectExplainExtensionCatalogReference
    target: ProjectExplainExtensionCatalogTarget
    content_sha256: str
    canonical_byte_length: int
    source_occurrences: tuple[ProjectExplainExtensionCatalogSourceOccurrence, ...]

    def __post_init__(self) -> None:
        _require_position(self.position, "catalog position")
        if type(self.reference) is not ProjectExplainExtensionCatalogReference:
            raise TypeError("Catalog summaries require an exact reference.")
        if type(self.target) is not ProjectExplainExtensionCatalogTarget:
            raise TypeError("Catalog summaries require an exact target.")
        _require_sha256(self.content_sha256, "catalog content SHA-256")
        if type(self.canonical_byte_length) is not int:
            raise TypeError("Catalog canonical byte length must be an exact integer.")
        if self.canonical_byte_length <= 0:
            raise ValueError("Catalog canonical byte length must be positive.")
        _require_dense_tuple(
            self.source_occurrences,
            ProjectExplainExtensionCatalogSourceOccurrence,
            "catalog source occurrences",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainExtensionCatalogTypeReference:
    kind: ProjectExplainCatalogTypeReferenceKind
    logical_name: str | None
    logical_kind: TypeKind | None
    physical_name: str | None
    extension_identity: str | None

    def __post_init__(self) -> None:
        if type(self.kind) is not ProjectExplainCatalogTypeReferenceKind:
            raise TypeError("Catalog type references require an exact kind.")
        if self.kind is ProjectExplainCatalogTypeReferenceKind.PIETTO_LOGICAL:
            _require_text(self.logical_name, "logical type name")
            if type(self.logical_kind) is not TypeKind:
                raise TypeError("Logical type references require an exact type kind.")
            if self.physical_name is not None or self.extension_identity is not None:
                raise ValueError("Logical type references forbid physical identity.")
            return
        if self.logical_name is not None or self.logical_kind is not None:
            raise ValueError("Physical type references forbid logical identity.")
        _require_text(self.physical_name, "physical type name")
        if self.kind is ProjectExplainCatalogTypeReferenceKind.POSTGRES_BUILTIN:
            if self.extension_identity is not None:
                raise ValueError("PostgreSQL builtins forbid an extension owner.")
            return
        _require_text(self.extension_identity, "native type extension identity")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainExtensionCatalogCallableIdentity:
    sql_name: str
    input_types: tuple[ProjectExplainExtensionCatalogTypeReference, ...]

    def __post_init__(self) -> None:
        _require_text(self.sql_name, "callable SQL name")
        _require_exact_tuple(
            self.input_types,
            ProjectExplainExtensionCatalogTypeReference,
            "callable input types",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainExtensionCatalogOperatorIdentity:
    operator_name: str
    arity: ProjectExplainPostgreSQLOperatorArity
    operand_types: tuple[ProjectExplainExtensionCatalogTypeReference, ...]

    def __post_init__(self) -> None:
        _require_text(self.operator_name, "operator name")
        if type(self.arity) is not ProjectExplainPostgreSQLOperatorArity:
            raise TypeError("Operator identities require an exact arity.")
        _require_exact_tuple(
            self.operand_types,
            ProjectExplainExtensionCatalogTypeReference,
            "operator operand types",
        )
        expected = 1 if self.arity is ProjectExplainPostgreSQLOperatorArity.UNARY else 2
        if len(self.operand_types) != expected:
            raise ValueError("Operator arity must match its operand count.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainExtensionCatalogCastIdentity:
    source_type: ProjectExplainExtensionCatalogTypeReference
    target_type: ProjectExplainExtensionCatalogTypeReference

    def __post_init__(self) -> None:
        if type(self.source_type) is not ProjectExplainExtensionCatalogTypeReference:
            raise TypeError("Cast identities require an exact source type.")
        if type(self.target_type) is not ProjectExplainExtensionCatalogTypeReference:
            raise TypeError("Cast identities require an exact target type.")


type ProjectExplainExtensionCatalogSelectorIdentity = (
    ProjectExplainExtensionCatalogTypeReference
    | ProjectExplainExtensionCatalogCallableIdentity
    | ProjectExplainExtensionCatalogOperatorIdentity
    | ProjectExplainExtensionCatalogCastIdentity
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainExtensionCatalogSelector:
    family: ProjectExplainCatalogEntryFamily
    identity: ProjectExplainExtensionCatalogSelectorIdentity

    def __post_init__(self) -> None:
        if type(self.family) is not ProjectExplainCatalogEntryFamily:
            raise TypeError("Catalog selectors require an exact entry family.")
        expected = {
            ProjectExplainCatalogEntryFamily.NATIVE_TYPE: (
                ProjectExplainExtensionCatalogTypeReference,
            ),
            ProjectExplainCatalogEntryFamily.SCALAR_FUNCTION: (
                ProjectExplainExtensionCatalogCallableIdentity,
            ),
            ProjectExplainCatalogEntryFamily.AGGREGATE: (
                ProjectExplainExtensionCatalogCallableIdentity,
            ),
            ProjectExplainCatalogEntryFamily.OPERATOR: (
                ProjectExplainExtensionCatalogOperatorIdentity,
            ),
            ProjectExplainCatalogEntryFamily.CAST: (
                ProjectExplainExtensionCatalogCastIdentity,
            ),
        }[self.family]
        if type(self.identity) not in expected:
            raise TypeError("Catalog selector family and typed identity disagree.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainExtensionCatalogAvailabilityDeclaration:
    position: int
    owner_kind: ProjectExplainCatalogAvailabilityOwnerKind
    project_path: ProjectExplainLogicalPath | None
    catalog_position: int
    reference: ProjectExplainExtensionCatalogReference
    target: ProjectExplainExtensionCatalogTarget
    content_sha256: str

    def __post_init__(self) -> None:
        _require_position(self.position, "catalog availability position")
        if type(self.owner_kind) is not ProjectExplainCatalogAvailabilityOwnerKind:
            raise TypeError("Catalog availability requires an exact owner kind.")
        if self.owner_kind is ProjectExplainCatalogAvailabilityOwnerKind.COMPILER:
            if self.project_path is not None:
                raise ValueError(
                    "Compiler catalog availability forbids a project path."
                )
        elif (
            type(self.project_path) is not ProjectExplainLogicalPath
            or self.project_path.kind
            is not ProjectExplainLogicalPathKind.PROJECT_RELATIVE
        ):
            raise ValueError(
                "Project catalog availability requires a project-relative path."
            )
        _require_position(self.catalog_position, "available catalog position")
        if type(self.reference) is not ProjectExplainExtensionCatalogReference:
            raise TypeError("Catalog availability requires an exact reference.")
        if type(self.target) is not ProjectExplainExtensionCatalogTarget:
            raise TypeError("Catalog availability requires an exact target.")
        _require_sha256(self.content_sha256, "available catalog content SHA-256")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainExtensionCatalogSelectionCandidate:
    catalog_position: int
    reference: ProjectExplainExtensionCatalogReference
    target: ProjectExplainExtensionCatalogTarget
    content_sha256: str
    declaration_positions: tuple[int, ...]

    def __post_init__(self) -> None:
        _require_position(self.catalog_position, "candidate catalog position")
        if type(self.reference) is not ProjectExplainExtensionCatalogReference:
            raise TypeError("Catalog candidates require an exact reference.")
        if type(self.target) is not ProjectExplainExtensionCatalogTarget:
            raise TypeError("Catalog candidates require an exact target.")
        _require_sha256(self.content_sha256, "candidate catalog content SHA-256")
        _require_positions(self.declaration_positions, "candidate declarations")
        if not self.declaration_positions:
            raise ValueError("Catalog candidates require declarations.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainExtensionCatalogSelection:
    requested_target: ProjectExplainExtensionCatalogTarget
    active_project_path: ProjectExplainLogicalPath | None
    outcome: ProjectExplainCatalogSelectionOutcome
    evidence_posture: ProjectExplainEvidencePosture
    availability: tuple[ProjectExplainExtensionCatalogAvailabilityDeclaration, ...]
    applicable_declaration_positions: tuple[int, ...]
    excluded_project_declaration_positions: tuple[int, ...]
    target_declaration_positions: tuple[int, ...]
    candidates: tuple[ProjectExplainExtensionCatalogSelectionCandidate, ...]
    selected_catalog_position: int | None

    def __post_init__(self) -> None:
        if type(self.requested_target) is not ProjectExplainExtensionCatalogTarget:
            raise TypeError("Catalog selection requires an exact requested target.")
        if self.active_project_path is not None and (
            type(self.active_project_path) is not ProjectExplainLogicalPath
            or self.active_project_path.kind
            is not ProjectExplainLogicalPathKind.PROJECT_RELATIVE
        ):
            raise ValueError("Active project paths must be project-relative.")
        if type(self.outcome) is not ProjectExplainCatalogSelectionOutcome:
            raise TypeError("Catalog selection requires an exact outcome.")
        if type(self.evidence_posture) is not ProjectExplainEvidencePosture:
            raise TypeError("Catalog selection requires an exact evidence posture.")
        _require_dense_tuple(
            self.availability,
            ProjectExplainExtensionCatalogAvailabilityDeclaration,
            "catalog availability declarations",
        )
        for positions, label in (
            (self.applicable_declaration_positions, "applicable declarations"),
            (
                self.excluded_project_declaration_positions,
                "excluded project declarations",
            ),
            (self.target_declaration_positions, "target declarations"),
        ):
            _require_positions(positions, label)
        _require_exact_tuple(
            self.candidates,
            ProjectExplainExtensionCatalogSelectionCandidate,
            "catalog selection candidates",
        )
        expected_posture = {
            ProjectExplainCatalogSelectionOutcome.UNDECLARED: (
                ProjectExplainEvidencePosture.UNAVAILABLE
            ),
            ProjectExplainCatalogSelectionOutcome.SELECTED: (
                ProjectExplainEvidencePosture.DETERMINISTIC_DERIVATION
            ),
            ProjectExplainCatalogSelectionOutcome.AMBIGUOUS: (
                ProjectExplainEvidencePosture.CONFLICTING
            ),
            ProjectExplainCatalogSelectionOutcome.CONFLICT: (
                ProjectExplainEvidencePosture.CONFLICTING
            ),
        }[self.outcome]
        if self.evidence_posture is not expected_posture:
            raise ValueError("Selection posture disagrees with its outcome.")
        if self.outcome is ProjectExplainCatalogSelectionOutcome.UNDECLARED:
            if self.candidates or self.selected_catalog_position is not None:
                raise ValueError("UNDECLARED selection forbids candidates or a winner.")
        elif self.outcome is ProjectExplainCatalogSelectionOutcome.SELECTED:
            if len(self.candidates) != 1 or self.selected_catalog_position is None:
                raise ValueError("SELECTED selection requires one exact catalog.")
            if self.candidates[0].catalog_position != self.selected_catalog_position:
                raise ValueError("SELECTED selection and candidate must agree.")
        elif len(self.candidates) < 2 or self.selected_catalog_position is not None:
            raise ValueError("Ambiguous/conflicting selection forbids a winner.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainExtensionCatalogEntryEvidence:
    entry_position: int
    entry_family: ProjectExplainCatalogEntryFamily
    matchability: ProjectExplainCatalogMatchability
    exposure: ProjectExplainCatalogExposure
    unmodeled_reasons: tuple[ProjectExplainCatalogUnmodeledReason, ...]
    source_positions: tuple[int, ...]

    def __post_init__(self) -> None:
        _require_position(self.entry_position, "catalog entry position")
        if type(self.entry_family) is not ProjectExplainCatalogEntryFamily:
            raise TypeError("Catalog entry evidence requires an exact family.")
        if type(self.matchability) is not ProjectExplainCatalogMatchability:
            raise TypeError("Catalog entry evidence requires exact matchability.")
        if type(self.exposure) is not ProjectExplainCatalogExposure:
            raise TypeError("Catalog entry evidence requires exact exposure.")
        _require_exact_tuple(
            self.unmodeled_reasons,
            ProjectExplainCatalogUnmodeledReason,
            "catalog unmodeled reasons",
        )
        _require_position_tuple(
            self.source_positions,
            "catalog entry source positions",
        )
        if not self.source_positions:
            raise ValueError("Catalog entry evidence requires source positions.")
        if self.matchability is ProjectExplainCatalogMatchability.EXACT_MATCHABLE:
            if self.unmodeled_reasons:
                raise ValueError("Exact-matchable evidence forbids unmodeled reasons.")
        elif not self.unmodeled_reasons:
            raise ValueError("Cataloged-unmodeled evidence requires reasons.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainExtensionCatalogExactGroupEvidence:
    position: int
    state: ProjectExplainCatalogExactGroupState
    entries: tuple[ProjectExplainExtensionCatalogEntryEvidence, ...]

    def __post_init__(self) -> None:
        _require_position(self.position, "exact group position")
        if type(self.state) is not ProjectExplainCatalogExactGroupState:
            raise TypeError("Exact groups require an exact state.")
        _require_exact_tuple(
            self.entries,
            ProjectExplainExtensionCatalogEntryEvidence,
            "exact group entries",
        )
        minimum = 1 if self.state is ProjectExplainCatalogExactGroupState.UNIQUE else 2
        if len(self.entries) < minimum:
            raise ValueError("Exact group state disagrees with its entry count.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainExtensionCatalogCompletenessClaim:
    position: int
    kind: ProjectExplainCatalogCompletenessClaimKind
    source_positions: tuple[int, ...]

    def __post_init__(self) -> None:
        _require_position(self.position, "completeness claim position")
        if type(self.kind) is not ProjectExplainCatalogCompletenessClaimKind:
            raise TypeError("Completeness claims require an exact kind.")
        _require_position_tuple(self.source_positions, "completeness claim sources")
        if not self.source_positions:
            raise ValueError("Completeness claims require source positions.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainExtensionCatalogCompletenessEvidence:
    position: int
    state: ProjectExplainCatalogCompletenessState
    claims: tuple[ProjectExplainExtensionCatalogCompletenessClaim, ...]

    def __post_init__(self) -> None:
        _require_position(self.position, "completeness group position")
        if type(self.state) is not ProjectExplainCatalogCompletenessState:
            raise TypeError("Completeness evidence requires an exact state.")
        _require_exact_tuple(
            self.claims,
            ProjectExplainExtensionCatalogCompletenessClaim,
            "completeness claims",
        )
        positions = tuple(claim.position for claim in self.claims)
        if any(left >= right for left, right in zip(positions, positions[1:])):
            raise ValueError("Completeness claims must retain catalog order.")
        minimum = (
            2 if self.state is ProjectExplainCatalogCompletenessState.CONFLICT else 1
        )
        if len(self.claims) < minimum:
            raise ValueError("Completeness state disagrees with its claims.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainExtensionRequirementEvidence:
    requirement_position: int
    selector: ProjectExplainExtensionCatalogSelector
    bridged_database_family: str
    selection: ProjectExplainExtensionCatalogSelection
    selected_catalog_position: int | None
    exact_group: ProjectExplainExtensionCatalogExactGroupEvidence | None
    unmodeled_blockers: tuple[ProjectExplainExtensionCatalogEntryEvidence, ...]
    completeness: ProjectExplainExtensionCatalogCompletenessEvidence | None

    def __post_init__(self) -> None:
        _require_position(self.requirement_position, "extension requirement position")
        if type(self.selector) is not ProjectExplainExtensionCatalogSelector:
            raise TypeError("Extension evidence requires an exact typed selector.")
        _require_text(self.bridged_database_family, "bridged database family")
        if type(self.selection) is not ProjectExplainExtensionCatalogSelection:
            raise TypeError("Extension evidence requires exact selection evidence.")
        if self.selected_catalog_position is not None:
            _require_position(self.selected_catalog_position, "selected catalog")
        if self.selected_catalog_position != self.selection.selected_catalog_position:
            raise ValueError("Selected catalog references must agree.")
        if self.exact_group is not None and (
            type(self.exact_group)
            is not ProjectExplainExtensionCatalogExactGroupEvidence
        ):
            raise TypeError("Extension evidence requires an exact optional group.")
        _require_exact_tuple(
            self.unmodeled_blockers,
            ProjectExplainExtensionCatalogEntryEvidence,
            "unmodeled blocker evidence",
        )
        if any(
            blocker.matchability
            is not ProjectExplainCatalogMatchability.CATALOGED_UNMODELED
            for blocker in self.unmodeled_blockers
        ):
            raise ValueError("Unmodeled blockers must stay cataloged-unmodeled.")
        if self.completeness is not None and (
            type(self.completeness)
            is not ProjectExplainExtensionCatalogCompletenessEvidence
        ):
            raise TypeError("Extension evidence requires exact completeness evidence.")
        if self.selected_catalog_position is None and (
            self.exact_group is not None
            or self.unmodeled_blockers
            or self.completeness is not None
        ):
            raise ValueError("Catalog-local evidence requires a selected catalog.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainExtensionCatalogContextEvidence:
    package_position: int
    target_position: int
    collection: ProjectExplainRequirementCollectionIdentity
    catalogs: tuple[ProjectExplainExtensionCatalogSummary, ...]
    requirements: tuple[ProjectExplainExtensionRequirementEvidence, ...]

    def __post_init__(self) -> None:
        _require_position(self.package_position, "catalog context package position")
        _require_position(self.target_position, "catalog context target position")
        if type(self.collection) is not ProjectExplainRequirementCollectionIdentity:
            raise TypeError("Catalog contexts require an exact collection identity.")
        _require_dense_tuple(
            self.catalogs,
            ProjectExplainExtensionCatalogSummary,
            "catalog context catalogs",
        )
        _require_exact_tuple(
            self.requirements,
            ProjectExplainExtensionRequirementEvidence,
            "catalog context requirements",
        )
        if not self.requirements:
            raise ValueError("Catalog contexts require extension requirements.")
        positions = tuple(
            requirement.requirement_position for requirement in self.requirements
        )
        if any(left >= right for left, right in zip(positions, positions[1:])):
            raise ValueError("Extension requirements must retain source order.")
        for requirement in self.requirements:
            _validate_context_requirement(self.catalogs, requirement)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExplainExtensionCatalogEvidenceProjection:
    contexts: tuple[ProjectExplainExtensionCatalogContextEvidence, ...]

    def __post_init__(self) -> None:
        _require_exact_tuple(
            self.contexts,
            ProjectExplainExtensionCatalogContextEvidence,
            "extension catalog contexts",
        )
        positions = tuple(
            (context.package_position, context.target_position)
            for context in self.contexts
        )
        if any(left >= right for left, right in zip(positions, positions[1:])):
            raise ValueError("Catalog contexts must retain package by target order.")


def _project_extension_catalog_evidence(
    package_projection: ProjectExplainPackageRequirementProjection,
    matrix_projection: ProjectExplainRequirementTargetMatrix,
    package_facts: PackageInspectionFactSet,
    capability_facts: tuple[CapabilityInspectionFactSet, ...],
    extension_catalog_facts: tuple[ExtensionCatalogInspectionFactSet | None, ...],
) -> ProjectExplainExtensionCatalogEvidenceProjection:
    """Project exact inspected extension evidence without recomputing it."""

    if type(package_projection) is not ProjectExplainPackageRequirementProjection:
        raise TypeError("Slice 5 requires an exact Slice 3 projection.")
    expected_package = _project_package_requirement_provenance(
        package_facts,
        capability_facts,
    )
    if package_projection != expected_package:
        raise ValueError("Slice 5 requires the same exact Slice 3 projection.")
    if type(matrix_projection) is not ProjectExplainRequirementTargetMatrix:
        raise TypeError("Slice 5 requires an exact Slice 4 matrix.")
    if type(extension_catalog_facts) is not tuple:
        raise TypeError("Slice 5 requires an exact catalog fact-set tuple.")
    if not matrix_projection.targets:
        if matrix_projection != _project_empty_requirement_target_matrix(
            package_projection
        ):
            raise ValueError("Slice 5 requires the canonical empty Slice 4 matrix.")
        if extension_catalog_facts != ():
            raise ValueError("An empty target denominator forbids catalog fact slots.")
        return ProjectExplainExtensionCatalogEvidenceProjection(contexts=())

    expected_matrix = _project_requirement_target_matrix(
        package_projection,
        package_facts,
        capability_facts,
    )
    if matrix_projection != expected_matrix:
        raise ValueError("Slice 5 requires the same exact Slice 4 projection.")
    target_count = len(matrix_projection.targets)
    expected_slots = len(package_projection.packages) * target_count
    if len(extension_catalog_facts) != expected_slots:
        raise ValueError("Slice 5 requires one catalog fact slot per package target.")

    requests_by_package = tuple(
        tuple(
            request
            for request in package_projection.requirements
            if request.declared_by == package_position
            and request.key.domain.value == "extension_signature"
        )
        for package_position in range(len(package_projection.packages))
    )
    contexts: list[ProjectExplainExtensionCatalogContextEvidence] = []
    for slot, facts in enumerate(extension_catalog_facts):
        package_position, target_position = divmod(slot, target_count)
        evaluation = matrix_projection.package_target_evaluations[slot]
        requests = requests_by_package[package_position]
        requires_facts = (
            evaluation.state is ProjectExplainEvaluationState.CHECKED and bool(requests)
        )
        if not requires_facts:
            if facts is not None:
                raise ValueError("Non-provider slots require an explicit None fact.")
            continue
        if type(facts) is not ExtensionCatalogInspectionFactSet:
            raise TypeError("Checked extension slots require exact catalog facts.")
        context = (
            capability_facts[package_position]
            .inspection.matrix.contexts[target_position]
            .extension_signature_provider_context
        )
        inspection = _require_catalog_inspection(facts, context)
        contexts.append(
            _project_context(
                package_position,
                target_position,
                requests,
                matrix_projection,
                capability_facts[package_position],
                inspection,
            )
        )
    return ProjectExplainExtensionCatalogEvidenceProjection(contexts=tuple(contexts))


def _require_catalog_inspection(
    facts: ExtensionCatalogInspectionFactSet,
    context: ExtensionSignatureProviderContext | None,
) -> ExtensionCatalogInspection:
    if context is None:
        raise ValueError("Checked extension slots require provider context authority.")
    inspection = facts.inspection
    if (
        inspection is not facts.authority.inspection
        or facts.canonical_bytes is not facts.authority.canonical_bytes
        or type(inspection) is not ExtensionCatalogInspection
        or inspection.format
        is not ExtensionCatalogInspectionFormat.EXTENSION_CATALOG_INSPECTION_V1
        or inspection.context is not context
        or facts.authority.context is not context
        or type(inspection.catalogs) is not tuple
        or type(inspection.provider_occurrences) is not tuple
    ):
        raise ValueError("Slice 5 rejects grafted catalog inspection authority.")
    return inspection


def _project_context(
    package_position: int,
    target_position: int,
    requests: tuple[ProjectExplainRequirementRequest, ...],
    matrix: ProjectExplainRequirementTargetMatrix,
    capability_facts: CapabilityInspectionFactSet,
    inspection: ExtensionCatalogInspection,
) -> ProjectExplainExtensionCatalogContextEvidence:
    if not requests:
        raise ValueError("Catalog contexts require extension requests.")
    collection = requests[0].collection
    if any(request.collection != collection for request in requests) or (
        inspection.requirement_namespace != collection.namespace
        or inspection.requirement_name != collection.name
    ):
        raise ValueError("Slice 5 collection authority is inconsistent.")
    local_positions = tuple(request.occurrence_position for request in requests)
    if (
        tuple(
            occurrence.requirement_position
            for occurrence in inspection.provider_occurrences
        )
        != local_positions
    ):
        raise ValueError("Slice 5 provider occurrences must retain source order.")
    catalogs = tuple(_project_catalog(catalog) for catalog in inspection.catalogs)
    requirements = tuple(
        _project_requirement(
            request,
            target_position,
            matrix,
            capability_facts,
            inspection,
            occurrence,
        )
        for request, occurrence in zip(
            requests,
            inspection.provider_occurrences,
            strict=True,
        )
    )
    return ProjectExplainExtensionCatalogContextEvidence(
        package_position=package_position,
        target_position=target_position,
        collection=collection,
        catalogs=catalogs,
        requirements=requirements,
    )


def _project_catalog(
    catalog: ExtensionCatalogInspectionCatalog,
) -> ProjectExplainExtensionCatalogSummary:
    if type(catalog) is not ExtensionCatalogInspectionCatalog:
        raise TypeError("Slice 5 requires exact inspected catalogs.")
    return ProjectExplainExtensionCatalogSummary(
        position=catalog.position,
        reference=_project_reference(catalog.reference),
        target=_project_target(catalog.target),
        content_sha256=catalog.content_sha256,
        canonical_byte_length=catalog.canonical_byte_length,
        source_occurrences=tuple(
            ProjectExplainExtensionCatalogSourceOccurrence(
                position=source.position,
                source_authority=source.source_authority,
                source_revision=source.source_revision,
                source_locator=ProjectExplainLogicalPath(
                    kind=ProjectExplainLogicalPathKind.UPSTREAM_SOURCE_LOCATOR,
                    value=source.source_locator,
                ),
                curation=source.curation,
            )
            for source in catalog.source_occurrences
        ),
    )


def _project_reference(
    reference: ExtensionCatalogInspectionCatalogReference,
) -> ProjectExplainExtensionCatalogReference:
    if type(reference) is not ExtensionCatalogInspectionCatalogReference:
        raise TypeError("Slice 5 requires an exact inspected catalog reference.")
    return ProjectExplainExtensionCatalogReference(
        namespace=reference.namespace,
        name=reference.name,
        release=reference.release,
    )


def _project_target(
    target: ExtensionCatalogInspectionTarget,
) -> ProjectExplainExtensionCatalogTarget:
    if type(target) is not ExtensionCatalogInspectionTarget:
        raise TypeError("Slice 5 requires an exact inspected catalog target.")
    return ProjectExplainExtensionCatalogTarget(
        database_family=target.database_family,
        database_release=target.database_release,
        extension_identity=target.extension_identity,
        extension_release=target.extension_release,
    )


def _project_type_reference(
    reference: ExtensionCatalogInspectionTypeReference,
) -> ProjectExplainExtensionCatalogTypeReference:
    if type(reference) is not ExtensionCatalogInspectionTypeReference:
        raise TypeError("Slice 5 requires an exact inspected type reference.")
    return ProjectExplainExtensionCatalogTypeReference(
        kind=ProjectExplainCatalogTypeReferenceKind(reference.kind.value),
        logical_name=reference.logical_name,
        logical_kind=reference.logical_kind,
        physical_name=reference.physical_name,
        extension_identity=reference.extension_identity,
    )


def _project_selector(
    scope: ExtensionCatalogInspectionLookupScope,
) -> ProjectExplainExtensionCatalogSelector:
    if type(scope) is not ExtensionCatalogInspectionLookupScope:
        raise TypeError("Slice 5 requires an exact inspected selector scope.")
    family = ProjectExplainCatalogEntryFamily(scope.family.value)
    identity = scope.identity
    if family is ProjectExplainCatalogEntryFamily.NATIVE_TYPE:
        if type(identity) is not ExtensionCatalogInspectionTypeReference:
            raise TypeError("Native selectors require an exact type identity.")
        projected: ProjectExplainExtensionCatalogSelectorIdentity = (
            _project_type_reference(identity)
        )
    elif family in {
        ProjectExplainCatalogEntryFamily.SCALAR_FUNCTION,
        ProjectExplainCatalogEntryFamily.AGGREGATE,
    }:
        if type(identity) is not ExtensionCatalogInspectionCallableIdentity:
            raise TypeError("Callable selectors require an exact identity.")
        projected = ProjectExplainExtensionCatalogCallableIdentity(
            sql_name=identity.sql_name,
            input_types=tuple(
                _project_type_reference(reference) for reference in identity.input_types
            ),
        )
    elif family is ProjectExplainCatalogEntryFamily.OPERATOR:
        if type(identity) is not ExtensionCatalogInspectionOperatorIdentity:
            raise TypeError("Operator selectors require an exact identity.")
        projected = ProjectExplainExtensionCatalogOperatorIdentity(
            operator_name=identity.operator_name,
            arity=ProjectExplainPostgreSQLOperatorArity(identity.arity.value),
            operand_types=tuple(
                _project_type_reference(reference)
                for reference in identity.operand_types
            ),
        )
    else:
        if type(identity) is not ExtensionCatalogInspectionCastIdentity:
            raise TypeError("Cast selectors require an exact identity.")
        projected = ProjectExplainExtensionCatalogCastIdentity(
            source_type=_project_type_reference(identity.source_type),
            target_type=_project_type_reference(identity.target_type),
        )
    return ProjectExplainExtensionCatalogSelector(family=family, identity=projected)


def _project_selection(
    selection: ExtensionCatalogInspectionSelection,
) -> ProjectExplainExtensionCatalogSelection:
    if type(selection) is not ExtensionCatalogInspectionSelection:
        raise TypeError("Slice 5 requires exact inspected selection evidence.")
    outcome = ProjectExplainCatalogSelectionOutcome(selection.outcome.value)
    posture = {
        ProjectExplainCatalogSelectionOutcome.UNDECLARED: (
            ProjectExplainEvidencePosture.UNAVAILABLE
        ),
        ProjectExplainCatalogSelectionOutcome.SELECTED: (
            ProjectExplainEvidencePosture.DETERMINISTIC_DERIVATION
        ),
        ProjectExplainCatalogSelectionOutcome.AMBIGUOUS: (
            ProjectExplainEvidencePosture.CONFLICTING
        ),
        ProjectExplainCatalogSelectionOutcome.CONFLICT: (
            ProjectExplainEvidencePosture.CONFLICTING
        ),
    }[outcome]
    return ProjectExplainExtensionCatalogSelection(
        requested_target=_project_target(selection.requested_target),
        active_project_path=(
            None
            if selection.active_project_path is None
            else ProjectExplainLogicalPath(
                kind=ProjectExplainLogicalPathKind.PROJECT_RELATIVE,
                value=selection.active_project_path,
            )
        ),
        outcome=outcome,
        evidence_posture=posture,
        availability=tuple(
            _project_availability(declaration) for declaration in selection.availability
        ),
        applicable_declaration_positions=selection.applicable_declaration_positions,
        excluded_project_declaration_positions=(
            selection.excluded_project_declaration_positions
        ),
        target_declaration_positions=selection.target_declaration_positions,
        candidates=tuple(
            ProjectExplainExtensionCatalogSelectionCandidate(
                catalog_position=candidate.catalog_position,
                reference=_project_reference(candidate.reference),
                target=_project_target(candidate.target),
                content_sha256=candidate.content_sha256,
                declaration_positions=candidate.declaration_positions,
            )
            for candidate in selection.candidates
        ),
        selected_catalog_position=selection.selected_catalog_position,
    )


def _project_availability(
    declaration: ExtensionCatalogInspectionAvailabilityDeclaration,
) -> ProjectExplainExtensionCatalogAvailabilityDeclaration:
    if type(declaration) is not ExtensionCatalogInspectionAvailabilityDeclaration:
        raise TypeError("Slice 5 requires exact catalog availability declarations.")
    return ProjectExplainExtensionCatalogAvailabilityDeclaration(
        position=declaration.position,
        owner_kind=ProjectExplainCatalogAvailabilityOwnerKind(declaration.owner.value),
        project_path=(
            None
            if declaration.project_path is None
            else ProjectExplainLogicalPath(
                kind=ProjectExplainLogicalPathKind.PROJECT_RELATIVE,
                value=declaration.project_path,
            )
        ),
        catalog_position=declaration.catalog_position,
        reference=_project_reference(declaration.reference),
        target=_project_target(declaration.target),
        content_sha256=declaration.content_sha256,
    )


def _project_requirement(
    request: ProjectExplainRequirementRequest,
    target_position: int,
    matrix: ProjectExplainRequirementTargetMatrix,
    capability_facts: CapabilityInspectionFactSet,
    inspection: ExtensionCatalogInspection,
    occurrence: ExtensionCatalogInspectionProviderOccurrence,
) -> ProjectExplainExtensionRequirementEvidence:
    if request.key.domain.value != "extension_signature":
        raise ValueError("Slice 5 requires EXTENSION_SIGNATURE requests.")
    if occurrence.requirement_position != request.occurrence_position or not (
        _key_matches(request.key, occurrence.key)
    ):
        raise ValueError("Slice 5 provider occurrence authority is inconsistent.")
    bridge = extension_signature_dialect_family_bridge(request.key.dialect)
    if bridge is None or occurrence.bridged_database_family != bridge.database_family:
        raise ValueError("Slice 5 rejects a grafted dialect-family bridge.")
    row = matrix.rows[request.position]
    cell = row.cells[target_position]
    if cell.state is not ProjectExplainEvaluationState.CHECKED:
        raise ValueError("Slice 5 requirement evidence requires a checked cell.")
    private_cell = capability_facts.inspection.requirements[
        request.occurrence_position
    ].cells[target_position]
    if type(private_cell.check) is not CapabilityInspectionCheck:
        raise ValueError("Slice 5 requires exact private checked authority.")
    _require_provider_agreement(request, occurrence, private_cell.check, cell)

    selected = occurrence.selected_catalog_position
    selected_catalog = None if selected is None else inspection.catalogs[selected]
    selector = _project_selector(occurrence.selector_scope)
    exact_group = (
        None
        if occurrence.exact_group_position is None
        else _project_exact_group(
            selected_catalog,
            occurrence.exact_group_position,
            selector,
        )
    )
    blockers = tuple(
        _project_entry(selected_catalog, position)
        for position in occurrence.unmodeled_blocker_entry_positions
    )
    completeness = (
        None
        if occurrence.completeness_group_position is None
        else _project_completeness(
            selected_catalog,
            occurrence.completeness_group_position,
            selector,
        )
    )
    return ProjectExplainExtensionRequirementEvidence(
        requirement_position=request.position,
        selector=selector,
        bridged_database_family=occurrence.bridged_database_family,
        selection=_project_selection(occurrence.selection),
        selected_catalog_position=selected,
        exact_group=exact_group,
        unmodeled_blockers=blockers,
        completeness=completeness,
    )


def _project_exact_group(
    catalog: ExtensionCatalogInspectionCatalog | None,
    position: int,
    selector: ProjectExplainExtensionCatalogSelector,
) -> ProjectExplainExtensionCatalogExactGroupEvidence:
    if catalog is None:
        raise ValueError("Exact group evidence requires a selected catalog.")
    group = catalog.exact_entry_groups[position]
    if type(group) is not ExtensionCatalogInspectionExactEntryGroup:
        raise TypeError("Slice 5 requires an exact inspected entry group.")
    if _project_selector(group.scope) != selector:
        raise ValueError("Exact group scope must match the typed selector.")
    return ProjectExplainExtensionCatalogExactGroupEvidence(
        position=group.position,
        state=ProjectExplainCatalogExactGroupState(group.state.value),
        entries=tuple(
            _project_entry(catalog, entry) for entry in group.entry_positions
        ),
    )


def _project_completeness(
    catalog: ExtensionCatalogInspectionCatalog | None,
    position: int,
    selector: ProjectExplainExtensionCatalogSelector,
) -> ProjectExplainExtensionCatalogCompletenessEvidence:
    if catalog is None:
        raise ValueError("Completeness evidence requires a selected catalog.")
    group = catalog.completeness_groups[position]
    if type(group) is not ExtensionCatalogInspectionCompletenessGroup:
        raise TypeError("Slice 5 requires an exact inspected completeness group.")
    if _project_selector(group.scope) != selector:
        raise ValueError("Completeness scope must match the typed selector.")
    return ProjectExplainExtensionCatalogCompletenessEvidence(
        position=group.position,
        state=ProjectExplainCatalogCompletenessState(group.state.value),
        claims=tuple(
            ProjectExplainExtensionCatalogCompletenessClaim(
                position=claim_position,
                kind=ProjectExplainCatalogCompletenessClaimKind(
                    catalog.completeness_claims[claim_position].kind.value
                ),
                source_positions=(
                    catalog.completeness_claims[claim_position].source_positions
                ),
            )
            for claim_position in group.claim_positions
        ),
    )


def _project_entry(
    catalog: ExtensionCatalogInspectionCatalog | None,
    position: int,
) -> ProjectExplainExtensionCatalogEntryEvidence:
    if catalog is None:
        raise ValueError("Catalog entry evidence requires a selected catalog.")
    entry = catalog.entries[position]
    family = _entry_family(entry)
    evidence = entry.evidence
    return ProjectExplainExtensionCatalogEntryEvidence(
        entry_position=entry.position,
        entry_family=family,
        matchability=ProjectExplainCatalogMatchability(evidence.matchability.value),
        exposure=ProjectExplainCatalogExposure(evidence.exposure.value),
        unmodeled_reasons=tuple(
            ProjectExplainCatalogUnmodeledReason(reason.value)
            for reason in evidence.unmodeled_reasons
        ),
        source_positions=evidence.source_positions,
    )


def _entry_family(entry: object) -> ProjectExplainCatalogEntryFamily:
    mapping = {
        ExtensionCatalogInspectionNativeTypeEntry: (
            ProjectExplainCatalogEntryFamily.NATIVE_TYPE
        ),
        ExtensionCatalogInspectionScalarFunctionEntry: (
            ProjectExplainCatalogEntryFamily.SCALAR_FUNCTION
        ),
        ExtensionCatalogInspectionAggregateEntry: (
            ProjectExplainCatalogEntryFamily.AGGREGATE
        ),
        ExtensionCatalogInspectionOperatorEntry: (
            ProjectExplainCatalogEntryFamily.OPERATOR
        ),
        ExtensionCatalogInspectionCastEntry: ProjectExplainCatalogEntryFamily.CAST,
    }
    family = mapping.get(type(entry))
    if family is None:
        raise TypeError("Slice 5 requires one exact inspected entry family.")
    return family


def _require_provider_agreement(
    request: ProjectExplainRequirementRequest,
    occurrence: ExtensionCatalogInspectionProviderOccurrence,
    private_check: CapabilityInspectionCheck,
    cell: ProjectExplainMatrixCell,
) -> None:
    if type(cell) is not ProjectExplainMatrixCell:
        raise TypeError("Slice 5 requires an exact Slice 4 cell.")
    checked_evidence = cell.checked_evidence
    if checked_evidence is None:
        raise ValueError("Slice 5 requires Slice 4 checked provider evidence.")
    extension_lookup = occurrence.lookup
    capability_lookup = private_check.provider_lookup
    extension_values = (
        extension_lookup.variant.value,
        None if extension_lookup.reason is None else extension_lookup.reason.value,
        tuple(_fact_values(fact) for fact in extension_lookup.facts),
    )
    capability_values = (
        capability_lookup.variant.value,
        None if capability_lookup.reason is None else capability_lookup.reason.value,
        tuple(_fact_values(fact) for fact in capability_lookup.facts),
    )
    public_values = (
        checked_evidence.provider_lookup.variant.value,
        checked_evidence.provider_lookup.reason,
        tuple(support.value for support in checked_evidence.provider_lookup.supports),
    )
    public_projection = (
        extension_values[0],
        extension_values[1],
        tuple(support for _key, support in extension_values[2]),
    )
    if extension_values != capability_values or public_projection != public_values:
        raise ValueError("Slice 5 provider lookup disagrees with Slice 4.")
    extension_inputs = occurrence.provider_inputs
    private_inputs = private_check.check.provider_inputs
    if (
        extension_inputs.domain_complete is not private_inputs.domain_complete
        or extension_inputs.unknown_reason is not private_inputs.unknown_reason
        or extension_inputs.domain_complete
        is not checked_evidence.provider_domain_complete
        or (
            None
            if extension_inputs.unknown_reason is None
            else extension_inputs.unknown_reason.value
        )
        != checked_evidence.provider_unknown_reason
        or not _key_matches(request.key, extension_inputs.key)
        or not _key_matches(request.key, private_inputs.key)
        or tuple(_fact_values(fact) for fact in extension_inputs.facts)
        != tuple(_fact_values(fact) for fact in private_inputs.facts)
    ):
        raise ValueError("Slice 5 provider inputs disagree with Slice 4 authority.")


def _validate_context_requirement(
    catalogs: tuple[ProjectExplainExtensionCatalogSummary, ...],
    requirement: ProjectExplainExtensionRequirementEvidence,
) -> None:
    selection = requirement.selection
    for declaration in selection.availability:
        _require_catalog_reference(
            catalogs,
            declaration.catalog_position,
            declaration.reference,
            declaration.target,
            declaration.content_sha256,
        )
    for candidate in selection.candidates:
        _require_catalog_reference(
            catalogs,
            candidate.catalog_position,
            candidate.reference,
            candidate.target,
            candidate.content_sha256,
        )
        if candidate.target != selection.requested_target:
            raise ValueError("Selection candidates must match the requested target.")
    selected = requirement.selected_catalog_position
    if selected is None:
        return
    if selected >= len(catalogs):
        raise ValueError("Selected catalog position must name a catalog.")
    source_count = len(catalogs[selected].source_occurrences)
    evidence = (
        () if requirement.exact_group is None else requirement.exact_group.entries
    ) + requirement.unmodeled_blockers
    for entry in evidence:
        if any(position >= source_count for position in entry.source_positions):
            raise ValueError("Entry evidence must reference selected catalog sources.")
    if requirement.completeness is not None:
        for claim in requirement.completeness.claims:
            if any(position >= source_count for position in claim.source_positions):
                raise ValueError(
                    "Completeness evidence must reference selected catalog sources."
                )


def _require_catalog_reference(
    catalogs: tuple[ProjectExplainExtensionCatalogSummary, ...],
    position: int,
    reference: ProjectExplainExtensionCatalogReference,
    target: ProjectExplainExtensionCatalogTarget,
    digest: str,
) -> None:
    if position >= len(catalogs):
        raise ValueError("Catalog evidence position must name a catalog.")
    catalog = catalogs[position]
    if (
        catalog.reference != reference
        or catalog.target != target
        or catalog.content_sha256 != digest
    ):
        raise ValueError("Catalog evidence identity is inconsistent.")


def _key_values(value: Any) -> tuple[object, ...]:
    return (
        value.domain,
        value.subject,
        value.operation,
        value.operands,
        value.context,
        value.dialect,
        value.extension,
    )


def _key_matches(public: Any, private: Any) -> bool:
    return _key_values(public) == _key_values(private)


def _fact_values(fact: Any) -> tuple[object, str]:
    return _key_values(fact.key), fact.support.value


def _require_text(value: object, label: str) -> None:
    if type(value) is not str:
        raise TypeError(f"Project Explain {label} must be exact text.")
    if not value:
        raise ValueError(f"Project Explain {label} must be non-empty.")


def _require_position(value: object, label: str) -> None:
    if type(value) is not int:
        raise TypeError(f"Project Explain {label} must be an exact integer.")
    if value < 0:
        raise ValueError(f"Project Explain {label} must be non-negative.")


def _require_positions(values: object, label: str) -> None:
    _require_position_tuple(values, label)
    assert type(values) is tuple
    if any(left >= right for left, right in zip(values, values[1:])):
        raise ValueError(f"Project Explain {label} must retain exact order.")


def _require_position_tuple(values: object, label: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"Project Explain {label} must be an exact tuple.")
    for value in values:
        _require_position(value, label)


def _require_sha256(value: object, label: str) -> None:
    if type(value) is not str:
        raise TypeError(f"Project Explain {label} must be exact text.")
    if len(value) != 64 or any(character not in _LOWER_HEX for character in value):
        raise ValueError(f"Project Explain {label} must be lowercase SHA-256 text.")


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
