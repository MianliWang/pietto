"""Private authored row-uniqueness evidence and candidate-key frontier."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from pietto._project.model import (
    ProjectRelationRowSchemaStatus,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectSemanticResult,
    ProjectSymbolKind,
)
from pietto._project.module_attribution import (
    ProjectDeclarationOccurrenceIdentity,
    ProjectModuleAttributionFactSet,
    ProjectModuleRowFieldIdentity,
    ProjectModuleSourceFieldOrigin,
    _declaration_identity,
)
from pietto._project.module_carrier import ProjectCompilationMode
from pietto._project.module_catalog import (
    ProjectDeclarationOccurrence,
    ProjectModuleCatalogSet,
)
from pietto._project.module_resolution import (
    ProjectResolvedModuleSourceShapeReference,
    ProjectTypeSourceResolutionIssue,
    ProjectTypeSourceResolutionIssueStatus,
    ProjectTypeSourceResolutionSet,
)
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleRelationSemanticFacts,
    ProjectModuleSemanticFactSet,
)
from pietto._project.project_relationship_conditions import (
    ProjectExactRowOutputConstraintScope,
    ProjectRelationshipConstraintScopeKind,
)
from pietto.ast_nodes import FieldDef, Node, ShapeDef, SourceDef, UniqueDef
from pietto.errors import Diagnostic, SourceLocation
from pietto.semantic.shapes import check_shape_structures

__all__: tuple[str, ...] = ()

_SHAPE_DIAGNOSTIC_CODES = frozenset({"PIE-S2501", "PIE-S2502", "PIE-S2503"})
_AMBIGUOUS_SOURCE_STATUSES = frozenset(
    {ProjectTypeSourceResolutionIssueStatus.AMBIGUOUS_LOCAL_TYPE_NAME}
)
_BLOCKED_SOURCE_STATUSES = frozenset(
    {
        ProjectTypeSourceResolutionIssueStatus.INCOMPATIBLE_SOURCE_SHAPE_KIND,
        ProjectTypeSourceResolutionIssueStatus.MODULE_GRAPH_CYCLE_BLOCKED,
        ProjectTypeSourceResolutionIssueStatus.MODULE_DIAGNOSTIC_BLOCKED,
    }
)


class ProjectUniqueNullPolicy(StrEnum):
    """Closed Pietto authored UNIQUE NULL policies."""

    NULLS_DISTINCT = "nulls_distinct"
    NULLS_NOT_DISTINCT = "nulls_not_distinct"


class ProjectRowUniquenessStrength(StrEnum):
    """Strict versus standard-equality-only row uniqueness."""

    STRICT = "strict"
    LAX = "lax"


class ProjectConstraintEvidenceOrigin(StrEnum):
    """Closed origins for private constraint evidence."""

    AUTHORED_CONTRACT = "authored_contract"
    CATALOG_CONSTRAINT = "catalog_constraint"
    DERIVED_THEOREM = "derived_theorem"
    RUNTIME_OBSERVATION = "runtime_observation"
    UNVERIFIED_HINT = "unverified_hint"


class ProjectConstraintEvidenceTrust(StrEnum):
    """Closed trust posture independent of enforcement."""

    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"
    CONFLICT = "conflict"


class ProjectConstraintEnforcementPosture(StrEnum):
    """Model, catalog, and runtime enforcement are separate facts."""

    MODEL_CONTRACT = "model_contract"
    CATALOG_ENFORCED = "catalog_enforced"
    RUNTIME_OBSERVED = "runtime_observed"


class ProjectRowKeyConstructionState(StrEnum):
    """Closed availability states for one row-uniqueness application."""

    CONCRETE = "concrete"
    UNKNOWN = "unknown"
    DEFERRED = "deferred"
    BLOCKED = "blocked"
    AMBIGUOUS = "ambiguous"


class ProjectRowKeyFailureReason(StrEnum):
    """Exact reasons for non-concrete source/UNIQUE applications."""

    INVALID_UNIQUE_DECLARATION = "invalid_unique_declaration"
    UNRESOLVED_SOURCE_SHAPE = "unresolved_source_shape"
    AMBIGUOUS_SOURCE_SHAPE = "ambiguous_source_shape"
    BLOCKED_SOURCE_SHAPE = "blocked_source_shape"
    UNKNOWN_SOURCE_ROW = "unknown_source_row"
    DEFERRED_SOURCE_ROW = "deferred_source_row"
    BLOCKED_SOURCE_ROW = "blocked_source_row"
    MISSING_SOURCE_SEMANTIC_AUTHORITY = "missing_source_semantic_authority"
    CONFLICTING_SOURCE_SEMANTIC_AUTHORITY = "conflicting_source_semantic_authority"
    MISSING_DETERMINANT_AUTHORITY = "missing_determinant_authority"
    CONFLICTING_DETERMINANT_AUTHORITY = "conflicting_determinant_authority"


def _require_position(value: object, label: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be an exact non-negative position.")


def _source_resolution_outcome(
    issues: tuple[ProjectTypeSourceResolutionIssue, ...],
) -> tuple[ProjectRowKeyConstructionState, ProjectRowKeyFailureReason]:
    if not issues:
        raise ValueError("Unresolved source Shape requires exact resolution issues.")
    statuses = {issue.status for issue in issues}
    if statuses & _AMBIGUOUS_SOURCE_STATUSES:
        return (
            ProjectRowKeyConstructionState.AMBIGUOUS,
            ProjectRowKeyFailureReason.AMBIGUOUS_SOURCE_SHAPE,
        )
    if statuses & _BLOCKED_SOURCE_STATUSES:
        return (
            ProjectRowKeyConstructionState.BLOCKED,
            ProjectRowKeyFailureReason.BLOCKED_SOURCE_SHAPE,
        )
    return (
        ProjectRowKeyConstructionState.UNKNOWN,
        ProjectRowKeyFailureReason.UNRESOLVED_SOURCE_SHAPE,
    )


def _source_row_outcome(
    status: ProjectRelationRowSchemaStatus,
) -> tuple[ProjectRowKeyConstructionState, ProjectRowKeyFailureReason]:
    outcome = {
        ProjectRelationRowSchemaStatus.UNKNOWN: (
            ProjectRowKeyConstructionState.UNKNOWN,
            ProjectRowKeyFailureReason.UNKNOWN_SOURCE_ROW,
        ),
        ProjectRelationRowSchemaStatus.DEFERRED: (
            ProjectRowKeyConstructionState.DEFERRED,
            ProjectRowKeyFailureReason.DEFERRED_SOURCE_ROW,
        ),
        ProjectRelationRowSchemaStatus.BLOCKED: (
            ProjectRowKeyConstructionState.BLOCKED,
            ProjectRowKeyFailureReason.BLOCKED_SOURCE_ROW,
        ),
    }.get(status)
    if outcome is None:
        raise ValueError("Concrete source rows cannot produce a source-state terminal.")
    return outcome


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectUniqueDeclarationIdentity:
    """Identity of one Shape-owned authored UNIQUE occurrence."""

    shape: ProjectDeclarationOccurrenceIdentity
    shape_item_position: int

    def __post_init__(self) -> None:
        if type(self.shape) is not ProjectDeclarationOccurrenceIdentity or (
            self.shape.identity.declaration_kind is not ProjectSymbolKind.SHAPE
        ):
            raise TypeError("UNIQUE identity requires a Shape occurrence.")
        _require_position(self.shape_item_position, "UNIQUE shape-item position")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectUniqueDeclarationOccurrence:
    """One exact authored UNIQUE plus existing semantic diagnostics."""

    identity: ProjectUniqueDeclarationIdentity
    shape_occurrence: ProjectDeclarationOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    unique: UniqueDef = field(repr=False, compare=False, hash=False)
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        if type(self.identity) is not ProjectUniqueDeclarationIdentity:
            raise TypeError("UNIQUE occurrence requires an exact identity.")
        if type(self.shape_occurrence) is not ProjectDeclarationOccurrence or (
            _declaration_identity(self.shape_occurrence) != self.identity.shape
            or type(self.shape_occurrence.definition) is not ShapeDef
        ):
            raise ValueError("UNIQUE occurrence requires its exact owning Shape.")
        shape = self.shape_occurrence.definition
        if (
            type(self.unique) is not UniqueDef
            or self.identity.shape_item_position >= len(shape.items)
            or shape.items[self.identity.shape_item_position] is not self.unique
        ):
            raise ValueError("UNIQUE occurrence must retain exact shape-item order.")
        if type(self.diagnostics) is not tuple or any(
            type(diagnostic) is not Diagnostic
            or diagnostic.code not in _SHAPE_DIAGNOSTIC_CODES
            for diagnostic in self.diagnostics
        ):
            raise TypeError("UNIQUE diagnostics must retain exact semantic roots.")

    @property
    def admitted(self) -> bool:
        return not self.diagnostics


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectRowUniquenessEvidenceIdentity:
    """Identity of one UNIQUE application to one exact source row output."""

    declaration: ProjectUniqueDeclarationIdentity
    source: ProjectDeclarationOccurrenceIdentity

    def __post_init__(self) -> None:
        if type(self.declaration) is not ProjectUniqueDeclarationIdentity:
            raise TypeError("Evidence identity requires one UNIQUE declaration.")
        if type(self.source) is not ProjectDeclarationOccurrenceIdentity or (
            self.source.identity.declaration_kind is not ProjectSymbolKind.SOURCE
        ):
            raise TypeError("Evidence identity requires one Source occurrence.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectUniqueDeterminantField:
    """One authored-order determinant with exact Shape and source authority."""

    evidence_identity: ProjectRowUniquenessEvidenceIdentity
    determinant_position: int
    field_def: FieldDef = field(repr=False, compare=False, hash=False)
    source_origin: ProjectModuleSourceFieldOrigin
    semantic_field: ProjectRowField = field(repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        if type(self.evidence_identity) is not ProjectRowUniquenessEvidenceIdentity:
            raise TypeError("Determinant requires an evidence identity.")
        _require_position(self.determinant_position, "Determinant position")
        if type(self.field_def) is not FieldDef:
            raise TypeError("Determinant requires an exact Shape field.")
        if type(self.source_origin) is not ProjectModuleSourceFieldOrigin:
            raise TypeError("Determinant requires an exact source-field origin.")
        if type(self.semantic_field) is not ProjectRowField:
            raise TypeError("Determinant requires exact semantic field evidence.")
        if (
            self.source_origin.shape_field.owner
            != self.evidence_identity.declaration.shape
            or self.source_origin.source_field.owner != self.evidence_identity.source
            or self.source_origin.shape_field.name != self.field_def.name
            or self.source_origin.source_field.name != self.field_def.name
            or self.semantic_field.name != self.field_def.name
        ):
            raise ValueError("Determinant field authorities must agree exactly.")

    @property
    def shape_field_identity(self) -> ProjectModuleRowFieldIdentity:
        return self.source_origin.shape_field

    @property
    def source_field_identity(self) -> ProjectModuleRowFieldIdentity:
        return self.source_origin.source_field

    @property
    def nullability(self) -> ProjectRowFieldNullability:
        return self.semantic_field.nullability


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectRowUniquenessEvidence:
    """One trusted authored model premise scoped to one source row output."""

    identity: ProjectRowUniquenessEvidenceIdentity
    declaration: ProjectUniqueDeclarationOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    source_shape_resolution: ProjectResolvedModuleSourceShapeReference = field(
        repr=False,
        compare=False,
        hash=False,
    )
    source_semantic: ProjectModuleRelationSemanticFacts = field(
        repr=False,
        compare=False,
        hash=False,
    )
    scope: ProjectExactRowOutputConstraintScope
    determinants: tuple[ProjectUniqueDeterminantField, ...]
    null_policy: ProjectUniqueNullPolicy
    strength: ProjectRowUniquenessStrength
    origin: ProjectConstraintEvidenceOrigin
    trust: ProjectConstraintEvidenceTrust
    enforcement: ProjectConstraintEnforcementPosture

    def __post_init__(self) -> None:
        if type(self.identity) is not ProjectRowUniquenessEvidenceIdentity:
            raise TypeError("Row uniqueness evidence requires an exact identity.")
        if type(self.declaration) is not ProjectUniqueDeclarationOccurrence or (
            self.declaration.identity != self.identity.declaration
            or not self.declaration.admitted
        ):
            raise ValueError("Row uniqueness evidence requires admitted UNIQUE.")
        if (
            type(self.source_shape_resolution)
            is not ProjectResolvedModuleSourceShapeReference
            or _declaration_identity(self.source_shape_resolution.reference.owner)
            != self.identity.source
            or self.source_shape_resolution.target_symbol.target_occurrence
            is not self.declaration.shape_occurrence
        ):
            raise ValueError("Evidence requires its exact source-to-Shape resolution.")
        source_occurrence = self.source_shape_resolution.reference.owner
        if type(self.source_semantic) is not ProjectModuleRelationSemanticFacts or (
            self.source_semantic.owner is not source_occurrence
            or self.source_semantic.state.status
            is not ProjectRelationRowSchemaStatus.CONCRETE
        ):
            raise ValueError("Evidence requires one concrete source row output.")
        if (
            type(self.scope) is not ProjectExactRowOutputConstraintScope
            or self.scope.owner != self.identity.source
            or self.scope.relation is not self.source_semantic
            or self.scope.kind
            is not ProjectRelationshipConstraintScopeKind.UNCONDITIONAL_ON_EXACT_ROW_OUTPUT
        ):
            raise ValueError("Evidence requires exact unconditional source scope.")
        if type(self.determinants) is not tuple or not self.determinants:
            raise TypeError("Row uniqueness evidence requires determinants.")
        unique = self.declaration.unique
        shape = self.declaration.shape_occurrence.definition
        assert type(shape) is ShapeDef
        schema = self.source_semantic.state.schema
        assert schema is not None
        if len(self.determinants) != len(unique.field_names) or any(
            type(determinant) is not ProjectUniqueDeterminantField
            or determinant.evidence_identity != self.identity
            or determinant.determinant_position != position
            or determinant.field_def.name != unique.field_names[position]
            or determinant.field_def
            is not shape.fields[determinant.shape_field_identity.field_position]
            or schema.fields.get(determinant.source_field_identity.name)
            is not determinant.semantic_field
            for position, determinant in enumerate(self.determinants)
        ):
            raise ValueError("Evidence must retain every exact authored determinant.")
        determinant_ids = tuple(
            determinant.source_field_identity for determinant in self.determinants
        )
        if len(set(determinant_ids)) != len(determinant_ids):
            raise ValueError("Admitted UNIQUE cannot repeat determinant fields.")
        if (
            type(self.null_policy) is not ProjectUniqueNullPolicy
            or self.null_policy is not ProjectUniqueNullPolicy.NULLS_DISTINCT
        ):
            raise ValueError("Current authored UNIQUE uses NULLS_DISTINCT.")
        expected_strength = (
            ProjectRowUniquenessStrength.STRICT
            if all(
                determinant.nullability is ProjectRowFieldNullability.NON_NULL
                for determinant in self.determinants
            )
            else ProjectRowUniquenessStrength.LAX
        )
        if type(self.strength) is not ProjectRowUniquenessStrength or (
            self.strength is not expected_strength
        ):
            raise ValueError("Evidence strength must match exact nullability premises.")
        if (
            type(self.origin) is not ProjectConstraintEvidenceOrigin
            or self.origin is not ProjectConstraintEvidenceOrigin.AUTHORED_CONTRACT
            or type(self.trust) is not ProjectConstraintEvidenceTrust
            or self.trust is not ProjectConstraintEvidenceTrust.TRUSTED
            or type(self.enforcement) is not ProjectConstraintEnforcementPosture
            or self.enforcement
            is not ProjectConstraintEnforcementPosture.MODEL_CONTRACT
        ):
            raise ValueError("Slice 4 constructs only trusted authored model evidence.")

    @property
    def state(self) -> ProjectRowKeyConstructionState:
        return ProjectRowKeyConstructionState.CONCRETE


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectNonConcreteRowUniquenessSubject:
    """One exact failed source/UNIQUE application without partial evidence."""

    source: ProjectDeclarationOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    state: ProjectRowKeyConstructionState
    reason: ProjectRowKeyFailureReason
    identity: ProjectRowUniquenessEvidenceIdentity | None = None
    declaration: ProjectUniqueDeclarationOccurrence | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    source_shape_resolution: ProjectResolvedModuleSourceShapeReference | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    source_semantic: ProjectModuleRelationSemanticFacts | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    diagnostics: tuple[Diagnostic, ...] = ()
    resolution_issues: tuple[ProjectTypeSourceResolutionIssue, ...] = ()

    def __post_init__(self) -> None:
        if type(self.source) is not ProjectDeclarationOccurrence or (
            type(self.source.definition) is not SourceDef
        ):
            raise TypeError("Non-concrete row key requires a Source occurrence.")
        if type(self.state) is not ProjectRowKeyConstructionState or (
            self.state is ProjectRowKeyConstructionState.CONCRETE
        ):
            raise ValueError("Non-concrete row key requires a terminal state.")
        if type(self.reason) is not ProjectRowKeyFailureReason:
            raise TypeError("Non-concrete row key requires an exact reason.")
        if type(self.diagnostics) is not tuple or any(
            type(diagnostic) is not Diagnostic for diagnostic in self.diagnostics
        ):
            raise TypeError("Non-concrete diagnostics must be an exact tuple.")
        if type(self.resolution_issues) is not tuple or any(
            type(issue) is not ProjectTypeSourceResolutionIssue
            for issue in self.resolution_issues
        ):
            raise TypeError("Resolution issues must be an exact tuple.")
        source_identity = _declaration_identity(self.source)
        if self.declaration is None:
            expected_state, expected_reason = _source_resolution_outcome(
                self.resolution_issues
            )
            if (
                self.identity is not None
                or self.source_shape_resolution is not None
                or self.source_semantic is not None
                or self.diagnostics
                or self.state is not expected_state
                or self.reason is not expected_reason
            ):
                raise ValueError("Unresolved source key must retain resolution roots.")
            if any(
                issue.owning_module_path != self.source.identity.module_path
                for issue in self.resolution_issues
            ):
                raise ValueError("Source resolution issues must be module-local.")
            return
        if type(self.declaration) is not ProjectUniqueDeclarationOccurrence or (
            type(self.identity) is not ProjectRowUniquenessEvidenceIdentity
            or self.identity.declaration != self.declaration.identity
            or self.identity.source != source_identity
        ):
            raise ValueError(
                "Failed application requires exact source and UNIQUE identity."
            )
        if (
            type(self.source_shape_resolution)
            is not ProjectResolvedModuleSourceShapeReference
            or self.source_shape_resolution.reference.owner is not self.source
            or self.source_shape_resolution.target_symbol.target_occurrence
            is not self.declaration.shape_occurrence
        ):
            raise ValueError("Failed application requires exact Shape resolution.")
        if self.reason is ProjectRowKeyFailureReason.INVALID_UNIQUE_DECLARATION:
            if (
                self.state is not ProjectRowKeyConstructionState.BLOCKED
                or self.declaration.admitted
                or self.source_semantic is not None
                or self.diagnostics != self.declaration.diagnostics
                or self.resolution_issues
            ):
                raise ValueError(
                    "Invalid UNIQUE application requires exact diagnostics."
                )
            return
        if not self.declaration.admitted or self.diagnostics or self.resolution_issues:
            raise ValueError("Resolved application requires admitted UNIQUE authority.")
        if self.reason in {
            ProjectRowKeyFailureReason.MISSING_SOURCE_SEMANTIC_AUTHORITY,
            ProjectRowKeyFailureReason.CONFLICTING_SOURCE_SEMANTIC_AUTHORITY,
        }:
            expected_state = (
                ProjectRowKeyConstructionState.UNKNOWN
                if self.reason
                is ProjectRowKeyFailureReason.MISSING_SOURCE_SEMANTIC_AUTHORITY
                else ProjectRowKeyConstructionState.AMBIGUOUS
            )
            if self.source_semantic is not None or self.state is not expected_state:
                raise ValueError("Source semantic failure must retain exact state.")
            return
        if type(self.source_semantic) is not ProjectModuleRelationSemanticFacts or (
            self.source_semantic.owner is not self.source
        ):
            raise ValueError("Failed application requires source semantic authority.")
        if self.reason in {
            ProjectRowKeyFailureReason.UNKNOWN_SOURCE_ROW,
            ProjectRowKeyFailureReason.DEFERRED_SOURCE_ROW,
            ProjectRowKeyFailureReason.BLOCKED_SOURCE_ROW,
        }:
            expected_state, expected_reason = _source_row_outcome(
                self.source_semantic.state.status
            )
        elif self.reason is ProjectRowKeyFailureReason.MISSING_DETERMINANT_AUTHORITY:
            expected_state = ProjectRowKeyConstructionState.UNKNOWN
            expected_reason = self.reason
            if (
                self.source_semantic.state.status
                is not ProjectRelationRowSchemaStatus.CONCRETE
            ):
                raise ValueError("Missing determinant requires concrete source rows.")
        elif (
            self.reason is ProjectRowKeyFailureReason.CONFLICTING_DETERMINANT_AUTHORITY
        ):
            expected_state = ProjectRowKeyConstructionState.AMBIGUOUS
            expected_reason = self.reason
            if (
                self.source_semantic.state.status
                is not ProjectRelationRowSchemaStatus.CONCRETE
            ):
                raise ValueError(
                    "Conflicting determinant requires concrete source rows."
                )
        else:
            raise ValueError("Unsupported resolved row-key failure reason.")
        if expected_state is not self.state or expected_reason is not self.reason:
            raise ValueError("Failure reason does not support its construction state.")


type ProjectRowUniquenessSubject = (
    ProjectRowUniquenessEvidence | ProjectNonConcreteRowUniquenessSubject
)


def _subject_source(
    subject: ProjectRowUniquenessSubject,
) -> ProjectDeclarationOccurrence:
    if type(subject) is ProjectRowUniquenessEvidence:
        return subject.source_shape_resolution.reference.owner
    if type(subject) is ProjectNonConcreteRowUniquenessSubject:
        return subject.source
    raise AssertionError("Unhandled row uniqueness subject type.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectCandidateKeyIdentity:
    """One derived determinant/strength fact on one exact row output."""

    owner: ProjectDeclarationOccurrenceIdentity
    determinants: tuple[ProjectModuleRowFieldIdentity, ...]
    strength: ProjectRowUniquenessStrength

    def __post_init__(self) -> None:
        if type(self.owner) is not ProjectDeclarationOccurrenceIdentity or (
            self.owner.identity.declaration_kind is not ProjectSymbolKind.SOURCE
        ):
            raise TypeError("Candidate key requires one source output owner.")
        if (
            type(self.determinants) is not tuple
            or not self.determinants
            or any(
                type(determinant) is not ProjectModuleRowFieldIdentity
                or determinant.owner != self.owner
                for determinant in self.determinants
            )
        ):
            raise TypeError("Candidate key requires exact source fields.")
        positions = tuple(field.field_position for field in self.determinants)
        if len(set(self.determinants)) != len(self.determinants) or any(
            left >= right for left, right in zip(positions, positions[1:], strict=False)
        ):
            raise ValueError("Candidate determinants must follow exact output order.")
        if type(self.strength) is not ProjectRowUniquenessStrength:
            raise TypeError("Candidate key requires exact strength.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectCandidateKeyFact:
    """One non-dominated derived key with every exact supporting evidence."""

    identity: ProjectCandidateKeyIdentity
    supports: tuple[ProjectRowUniquenessEvidence, ...]

    def __post_init__(self) -> None:
        if type(self.identity) is not ProjectCandidateKeyIdentity:
            raise TypeError("Candidate key fact requires an exact identity.")
        if (
            type(self.supports) is not tuple
            or not self.supports
            or any(
                type(support) is not ProjectRowUniquenessEvidence
                or support.identity.source != self.identity.owner
                or support.strength is not self.identity.strength
                or frozenset(
                    determinant.source_field_identity
                    for determinant in support.determinants
                )
                != frozenset(self.identity.determinants)
                for support in self.supports
            )
        ):
            raise ValueError("Candidate key supports must prove its exact fact.")
        if len({support.identity for support in self.supports}) != len(self.supports):
            raise ValueError("Candidate key support occurrences must remain distinct.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectRowKeySet:
    """Complete private UNIQUE applications and candidate-key frontier."""

    semantic_result: ProjectSemanticResult = field(
        repr=False,
        compare=False,
        hash=False,
    )
    shape_diagnostics: tuple[Diagnostic, ...] = ()
    declarations: tuple[ProjectUniqueDeclarationOccurrence, ...] = ()
    subjects: tuple[ProjectRowUniquenessSubject, ...] = ()
    candidate_keys: tuple[ProjectCandidateKeyFact, ...] = ()

    def __post_init__(self) -> None:
        if type(self.semantic_result) is not ProjectSemanticResult or (
            self.semantic_result.compilation_mode
            is not ProjectCompilationMode.EXPLICIT_MODULES
        ):
            raise TypeError("Project row keys require explicit-module semantics.")
        if type(self.shape_diagnostics) is not tuple or any(
            type(diagnostic) is not Diagnostic for diagnostic in self.shape_diagnostics
        ):
            raise TypeError("Shape diagnostics must be an exact tuple.")
        if type(self.declarations) is not tuple or any(
            type(declaration) is not ProjectUniqueDeclarationOccurrence
            for declaration in self.declarations
        ):
            raise TypeError("UNIQUE declarations must be an exact tuple.")
        if type(self.subjects) is not tuple or any(
            type(subject)
            not in {
                ProjectRowUniquenessEvidence,
                ProjectNonConcreteRowUniquenessSubject,
            }
            for subject in self.subjects
        ):
            raise TypeError("Row uniqueness subjects must be an exact typed tuple.")
        if type(self.candidate_keys) is not tuple or any(
            type(candidate) is not ProjectCandidateKeyFact
            for candidate in self.candidate_keys
        ):
            raise TypeError("Candidate keys must be an exact tuple.")
        if any(
            not any(diagnostic is root for root in self.shape_diagnostics)
            for declaration in self.declarations
            for diagnostic in declaration.diagnostics
        ):
            raise ValueError("UNIQUE declarations require exact checker diagnostics.")
        semantic_facts = self.semantic_result.module_semantic_facts
        attribution = self.semantic_result.module_attribution_facts
        resolutions = self.semantic_result.module_type_source_resolutions
        catalogs = self.semantic_result.module_catalogs
        if (
            type(semantic_facts) is not ProjectModuleSemanticFactSet
            or type(attribution) is not ProjectModuleAttributionFactSet
            or type(resolutions) is not ProjectTypeSourceResolutionSet
            or type(catalogs) is not ProjectModuleCatalogSet
        ):
            raise ValueError("Project row keys require exact existing sidecars.")
        declaration_by_identity = {
            declaration.identity: declaration for declaration in self.declarations
        }
        if len(declaration_by_identity) != len(self.declarations):
            raise ValueError("UNIQUE declaration identities must remain distinct.")
        expected_declarations = tuple(
            (occurrence, item_position, item)
            for catalog in catalogs.catalogs
            for occurrence in catalog.occurrences
            if type(occurrence.definition) is ShapeDef
            for item_position, item in enumerate(occurrence.definition.items)
            if type(item) is UniqueDef
        )
        if len(self.declarations) != len(expected_declarations) or any(
            declaration.shape_occurrence is not occurrence
            or declaration.identity.shape_item_position != item_position
            or declaration.unique is not item
            for declaration, (occurrence, item_position, item) in zip(
                self.declarations,
                expected_declarations,
                strict=True,
            )
        ):
            raise ValueError("UNIQUE declarations must retain complete catalog order.")
        source_occurrences = tuple(
            occurrence
            for catalog in catalogs.catalogs
            for occurrence in catalog.occurrences
            if type(occurrence.definition) is SourceDef
            and occurrence.definition.shape_name is not None
        )
        expected_subject_keys: list[
            tuple[
                ProjectDeclarationOccurrence,
                ProjectUniqueDeclarationIdentity | None,
            ]
        ] = []
        for source in source_occurrences:
            source_definition = source.definition
            assert type(source_definition) is SourceDef
            environment_bucket = resolutions.find_module_path(
                source.identity.module_path
            )
            resolution_bucket = (
                ()
                if len(environment_bucket) != 1
                else environment_bucket[0].find_source(source_definition)
            )
            if len(resolution_bucket) != 1:
                expected_subject_keys.append((source, None))
                continue
            target = resolution_bucket[0].target_symbol.target_occurrence
            expected_subject_keys.extend(
                (source, declaration.identity)
                for declaration in self.declarations
                if declaration.shape_occurrence is target
            )
        actual_subject_keys = tuple(
            (
                _subject_source(subject),
                None if subject.identity is None else subject.identity.declaration,
            )
            for subject in self.subjects
        )
        if len(actual_subject_keys) != len(expected_subject_keys) or any(
            actual_source is not expected_source
            or actual_declaration != expected_declaration
            for (actual_source, actual_declaration), (
                expected_source,
                expected_declaration,
            ) in zip(actual_subject_keys, expected_subject_keys, strict=True)
        ):
            raise ValueError("Row uniqueness subjects must retain every application.")
        concrete_identities: set[ProjectRowUniquenessEvidenceIdentity] = set()
        for subject in self.subjects:
            source = _subject_source(subject)
            if not any(source is occurrence for occurrence in source_occurrences):
                raise ValueError("Row uniqueness subject requires exact source roots.")
            if type(subject) is ProjectNonConcreteRowUniquenessSubject:
                if subject.declaration is not None and (
                    declaration_by_identity.get(subject.declaration.identity)
                    is not subject.declaration
                ):
                    raise ValueError(
                        "Failed application requires retained UNIQUE authority."
                    )
                if any(
                    not any(issue is root for root in resolutions.issues)
                    for issue in subject.resolution_issues
                ):
                    raise ValueError(
                        "Failed application requires exact resolution issue roots."
                    )
                if subject.declaration is None:
                    expected_issues = _source_resolution_issues(source, resolutions)
                    if len(subject.resolution_issues) != len(expected_issues) or any(
                        actual is not expected
                        for actual, expected in zip(
                            subject.resolution_issues,
                            expected_issues,
                            strict=True,
                        )
                    ):
                        raise ValueError(
                            "Unresolved source requires complete exact issue roots."
                        )
                if subject.source_shape_resolution is not None:
                    environment_bucket = resolutions.find_module_path(
                        source.identity.module_path
                    )
                    source_definition = source.definition
                    assert type(source_definition) is SourceDef
                    resolution_bucket = (
                        ()
                        if len(environment_bucket) != 1
                        else environment_bucket[0].find_source(source_definition)
                    )
                    if (
                        len(resolution_bucket) != 1
                        or subject.source_shape_resolution is not resolution_bucket[0]
                    ):
                        raise ValueError(
                            "Failed application requires exact Shape resolution roots."
                        )
                if subject.source_semantic is not None:
                    semantic_bucket = semantic_facts.find_owner(source)
                    if (
                        len(semantic_bucket) != 1
                        or subject.source_semantic is not semantic_bucket[0]
                    ):
                        raise ValueError(
                            "Failed application requires exact semantic roots."
                        )
                continue
            if type(subject) is not ProjectRowUniquenessEvidence:
                raise AssertionError("Unhandled row uniqueness subject type.")
            if (
                declaration_by_identity.get(subject.declaration.identity)
                is not subject.declaration
            ):
                raise ValueError("Evidence requires a retained UNIQUE declaration.")
            if subject.identity in concrete_identities:
                raise ValueError("Evidence applications must remain distinct.")
            concrete_identities.add(subject.identity)
            target = subject.source_shape_resolution.target_symbol.target_occurrence
            source_definition = source.definition
            if type(source_definition) is not SourceDef:
                raise ValueError("Evidence source root must retain a SourceDef.")
            environment_bucket = resolutions.find_module_path(
                source.identity.module_path
            )
            resolution_bucket = (
                ()
                if len(environment_bucket) != 1
                else environment_bucket[0].find_source(source_definition)
            )
            semantic_bucket = semantic_facts.find_owner(source)
            if (
                len(resolution_bucket) != 1
                or subject.source_shape_resolution is not resolution_bucket[0]
                or target is not subject.declaration.shape_occurrence
                or len(semantic_bucket) != 1
                or subject.source_semantic is not semantic_bucket[0]
            ):
                raise ValueError("Evidence must retain exact Project root authority.")
            for determinant in subject.determinants:
                origin_bucket = attribution.find_source_field_origin(
                    determinant.source_field_identity
                )
                if (
                    len(origin_bucket) != 1
                    or determinant.source_origin is not origin_bucket[0]
                ):
                    raise ValueError("Determinants require exact attribution roots.")
        expected_candidates = _candidate_frontier(self.evidence)
        if len(self.candidate_keys) != len(expected_candidates) or any(
            supplied.identity != expected.identity
            or len(supplied.supports) != len(expected.supports)
            or any(
                actual is not expected_support
                for actual, expected_support in zip(
                    supplied.supports,
                    expected.supports,
                    strict=True,
                )
            )
            for supplied, expected in zip(
                self.candidate_keys,
                expected_candidates,
                strict=True,
            )
        ):
            raise ValueError("Candidate keys must be the complete direct frontier.")

    @property
    def evidence(self) -> tuple[ProjectRowUniquenessEvidence, ...]:
        return tuple(
            subject
            for subject in self.subjects
            if type(subject) is ProjectRowUniquenessEvidence
        )

    @property
    def non_concrete(
        self,
    ) -> tuple[ProjectNonConcreteRowUniquenessSubject, ...]:
        return tuple(
            subject
            for subject in self.subjects
            if type(subject) is ProjectNonConcreteRowUniquenessSubject
        )


def _location_matches_node(location: SourceLocation, node: Node) -> bool:
    span = node.span
    return (
        location.path == span.path
        and location.line == span.line
        and location.column == span.column
        and location.end_line == span.end_line
        and location.end_column == span.end_column
    )


def _unique_diagnostics(
    shape: ShapeDef,
    unique: UniqueDef,
    diagnostics: tuple[Diagnostic, ...],
) -> tuple[Diagnostic, ...]:
    collision_names = {
        item.name
        for diagnostic in diagnostics
        if diagnostic.code == "PIE-S2501"
        for item in shape.items
        if _location_matches_node(diagnostic.location, item)
    }
    return tuple(
        diagnostic
        for diagnostic in diagnostics
        if _location_matches_node(diagnostic.location, unique)
        or (diagnostic.code == "PIE-S2501" and unique.name in collision_names)
    )


def _source_resolution_issues(
    source: ProjectDeclarationOccurrence,
    resolutions: ProjectTypeSourceResolutionSet,
) -> tuple[ProjectTypeSourceResolutionIssue, ...]:
    definition = source.definition
    assert type(definition) is SourceDef and definition.shape_name is not None
    return tuple(
        issue
        for issue in resolutions.issues
        if issue.owning_module_path == source.identity.module_path
        and (
            (
                issue.source_reference is not None
                and issue.source_reference.owner is source
            )
            or (
                issue.status in (_AMBIGUOUS_SOURCE_STATUSES | _BLOCKED_SOURCE_STATUSES)
                and issue.local_name in {None, definition.shape_name}
            )
        )
    )


def _unresolved_source_terminal(
    source: ProjectDeclarationOccurrence,
    issues: tuple[ProjectTypeSourceResolutionIssue, ...],
) -> ProjectNonConcreteRowUniquenessSubject:
    state, reason = _source_resolution_outcome(issues)
    return ProjectNonConcreteRowUniquenessSubject(
        source=source,
        state=state,
        reason=reason,
        resolution_issues=issues,
    )


def _source_state_terminal(
    *,
    source: ProjectDeclarationOccurrence,
    declaration: ProjectUniqueDeclarationOccurrence,
    resolution: ProjectResolvedModuleSourceShapeReference,
    semantic: ProjectModuleRelationSemanticFacts,
) -> ProjectNonConcreteRowUniquenessSubject:
    state, reason = _source_row_outcome(semantic.state.status)
    identity = ProjectRowUniquenessEvidenceIdentity(
        declaration=declaration.identity,
        source=_declaration_identity(source),
    )
    return ProjectNonConcreteRowUniquenessSubject(
        source=source,
        identity=identity,
        declaration=declaration,
        source_shape_resolution=resolution,
        source_semantic=semantic,
        state=state,
        reason=reason,
    )


def _invalid_unique_terminal(
    *,
    source: ProjectDeclarationOccurrence,
    declaration: ProjectUniqueDeclarationOccurrence,
    resolution: ProjectResolvedModuleSourceShapeReference,
) -> ProjectNonConcreteRowUniquenessSubject:
    return ProjectNonConcreteRowUniquenessSubject(
        source=source,
        identity=ProjectRowUniquenessEvidenceIdentity(
            declaration=declaration.identity,
            source=_declaration_identity(source),
        ),
        declaration=declaration,
        source_shape_resolution=resolution,
        state=ProjectRowKeyConstructionState.BLOCKED,
        reason=ProjectRowKeyFailureReason.INVALID_UNIQUE_DECLARATION,
        diagnostics=declaration.diagnostics,
    )


def _source_semantic_failure(
    *,
    source: ProjectDeclarationOccurrence,
    declaration: ProjectUniqueDeclarationOccurrence,
    resolution: ProjectResolvedModuleSourceShapeReference,
    ambiguous: bool,
) -> ProjectNonConcreteRowUniquenessSubject:
    return ProjectNonConcreteRowUniquenessSubject(
        source=source,
        identity=ProjectRowUniquenessEvidenceIdentity(
            declaration=declaration.identity,
            source=_declaration_identity(source),
        ),
        declaration=declaration,
        source_shape_resolution=resolution,
        state=(
            ProjectRowKeyConstructionState.AMBIGUOUS
            if ambiguous
            else ProjectRowKeyConstructionState.UNKNOWN
        ),
        reason=(
            ProjectRowKeyFailureReason.CONFLICTING_SOURCE_SEMANTIC_AUTHORITY
            if ambiguous
            else ProjectRowKeyFailureReason.MISSING_SOURCE_SEMANTIC_AUTHORITY
        ),
    )


def _determinant_failure(
    *,
    source: ProjectDeclarationOccurrence,
    declaration: ProjectUniqueDeclarationOccurrence,
    resolution: ProjectResolvedModuleSourceShapeReference,
    semantic: ProjectModuleRelationSemanticFacts,
    ambiguous: bool,
) -> ProjectNonConcreteRowUniquenessSubject:
    identity = ProjectRowUniquenessEvidenceIdentity(
        declaration=declaration.identity,
        source=_declaration_identity(source),
    )
    return ProjectNonConcreteRowUniquenessSubject(
        source=source,
        identity=identity,
        declaration=declaration,
        source_shape_resolution=resolution,
        source_semantic=semantic,
        state=(
            ProjectRowKeyConstructionState.AMBIGUOUS
            if ambiguous
            else ProjectRowKeyConstructionState.UNKNOWN
        ),
        reason=(
            ProjectRowKeyFailureReason.CONFLICTING_DETERMINANT_AUTHORITY
            if ambiguous
            else ProjectRowKeyFailureReason.MISSING_DETERMINANT_AUTHORITY
        ),
    )


def _evidence_application(
    *,
    source: ProjectDeclarationOccurrence,
    declaration: ProjectUniqueDeclarationOccurrence,
    resolution: ProjectResolvedModuleSourceShapeReference,
    semantic: ProjectModuleRelationSemanticFacts,
    attribution: ProjectModuleAttributionFactSet,
) -> ProjectRowUniquenessSubject:
    if not declaration.admitted:
        raise ValueError("Concrete evidence builder requires admitted UNIQUE.")
    if semantic.state.status is not ProjectRelationRowSchemaStatus.CONCRETE:
        return _source_state_terminal(
            source=source,
            declaration=declaration,
            resolution=resolution,
            semantic=semantic,
        )
    schema = semantic.state.schema
    assert schema is not None
    shape = declaration.shape_occurrence.definition
    assert type(shape) is ShapeDef
    source_identity = _declaration_identity(source)
    identity = ProjectRowUniquenessEvidenceIdentity(
        declaration=declaration.identity,
        source=source_identity,
    )
    lineage_bucket = attribution.find_row_lineage(source_identity)
    if not lineage_bucket:
        return _determinant_failure(
            source=source,
            declaration=declaration,
            resolution=resolution,
            semantic=semantic,
            ambiguous=False,
        )
    if len(lineage_bucket) != 1:
        return _determinant_failure(
            source=source,
            declaration=declaration,
            resolution=resolution,
            semantic=semantic,
            ambiguous=True,
        )
    lineage = lineage_bucket[0]
    determinants: list[ProjectUniqueDeterminantField] = []
    for determinant_position, field_name in enumerate(declaration.unique.field_names):
        shape_fields = tuple(
            field_def for field_def in shape.fields if field_def.name == field_name
        )
        source_fields = tuple(
            field_lineage.field
            for field_lineage in lineage.fields
            if field_lineage.field.name == field_name
        )
        semantic_field = schema.fields.get(field_name)
        if not shape_fields or not source_fields or semantic_field is None:
            return _determinant_failure(
                source=source,
                declaration=declaration,
                resolution=resolution,
                semantic=semantic,
                ambiguous=False,
            )
        if len(shape_fields) != 1 or len(source_fields) != 1:
            return _determinant_failure(
                source=source,
                declaration=declaration,
                resolution=resolution,
                semantic=semantic,
                ambiguous=True,
            )
        origin_bucket = attribution.find_source_field_origin(source_fields[0])
        if not origin_bucket:
            return _determinant_failure(
                source=source,
                declaration=declaration,
                resolution=resolution,
                semantic=semantic,
                ambiguous=False,
            )
        if len(origin_bucket) != 1:
            return _determinant_failure(
                source=source,
                declaration=declaration,
                resolution=resolution,
                semantic=semantic,
                ambiguous=True,
            )
        determinants.append(
            ProjectUniqueDeterminantField(
                evidence_identity=identity,
                determinant_position=determinant_position,
                field_def=shape_fields[0],
                source_origin=origin_bucket[0],
                semantic_field=semantic_field,
            )
        )
    determinant_tuple = tuple(determinants)
    strength = (
        ProjectRowUniquenessStrength.STRICT
        if all(
            determinant.nullability is ProjectRowFieldNullability.NON_NULL
            for determinant in determinant_tuple
        )
        else ProjectRowUniquenessStrength.LAX
    )
    scope = ProjectExactRowOutputConstraintScope(
        kind=(ProjectRelationshipConstraintScopeKind.UNCONDITIONAL_ON_EXACT_ROW_OUTPUT),
        owner=source_identity,
        relation=semantic,
    )
    return ProjectRowUniquenessEvidence(
        identity=identity,
        declaration=declaration,
        source_shape_resolution=resolution,
        source_semantic=semantic,
        scope=scope,
        determinants=determinant_tuple,
        null_policy=ProjectUniqueNullPolicy.NULLS_DISTINCT,
        strength=strength,
        origin=ProjectConstraintEvidenceOrigin.AUTHORED_CONTRACT,
        trust=ProjectConstraintEvidenceTrust.TRUSTED,
        enforcement=ProjectConstraintEnforcementPosture.MODEL_CONTRACT,
    )


def _normalized_determinants(
    evidence: ProjectRowUniquenessEvidence,
) -> tuple[ProjectModuleRowFieldIdentity, ...]:
    schema = evidence.source_semantic.state.schema
    assert schema is not None
    determinant_by_name = {
        determinant.source_field_identity.name: determinant.source_field_identity
        for determinant in evidence.determinants
    }
    return tuple(
        determinant_by_name[name]
        for name in schema.fields
        if name in determinant_by_name
    )


def _strength_at_least(
    left: ProjectRowUniquenessStrength,
    right: ProjectRowUniquenessStrength,
) -> bool:
    return left is ProjectRowUniquenessStrength.STRICT or left is right


def _dominates(
    left_fields: frozenset[ProjectModuleRowFieldIdentity],
    left_strength: ProjectRowUniquenessStrength,
    right_fields: frozenset[ProjectModuleRowFieldIdentity],
    right_strength: ProjectRowUniquenessStrength,
) -> bool:
    """Return direct uniqueness dominance without FD closure."""

    return left_fields <= right_fields and _strength_at_least(
        left_strength,
        right_strength,
    )


def _candidate_frontier(
    evidence: tuple[ProjectRowUniquenessEvidence, ...],
) -> tuple[ProjectCandidateKeyFact, ...]:
    groups: list[
        tuple[
            ProjectCandidateKeyIdentity,
            list[ProjectRowUniquenessEvidence],
        ]
    ] = []
    group_positions: dict[
        tuple[
            ProjectDeclarationOccurrenceIdentity,
            frozenset[ProjectModuleRowFieldIdentity],
            ProjectRowUniquenessStrength,
        ],
        int,
    ] = {}
    for item in evidence:
        determinants = _normalized_determinants(item)
        determinant_set = frozenset(determinants)
        key = (item.identity.source, determinant_set, item.strength)
        position = group_positions.get(key)
        if position is None:
            group_positions[key] = len(groups)
            groups.append(
                (
                    ProjectCandidateKeyIdentity(
                        owner=item.identity.source,
                        determinants=determinants,
                        strength=item.strength,
                    ),
                    [item],
                )
            )
        else:
            groups[position][1].append(item)
    frontier: list[ProjectCandidateKeyFact] = []
    for position, (identity, supports) in enumerate(groups):
        fields = frozenset(identity.determinants)
        if any(
            other.owner == identity.owner
            and _dominates(
                frozenset(other.determinants),
                other.strength,
                fields,
                identity.strength,
            )
            for other_position, (other, _other_supports) in enumerate(groups)
            if other_position != position
        ):
            continue
        frontier.append(
            ProjectCandidateKeyFact(
                identity=identity,
                supports=tuple(supports),
            )
        )
    return tuple(frontier)


def build_project_row_keys(
    semantic_result: ProjectSemanticResult,
) -> ProjectRowKeySet:
    """Build exact authored source keys from existing Project authority."""

    if type(semantic_result) is not ProjectSemanticResult or (
        semantic_result.compilation_mode is not ProjectCompilationMode.EXPLICIT_MODULES
    ):
        raise TypeError("Project row-key construction requires explicit modules.")
    catalogs = semantic_result.module_catalogs
    resolutions = semantic_result.module_type_source_resolutions
    semantic_facts = semantic_result.module_semantic_facts
    attribution = semantic_result.module_attribution_facts
    if (
        type(catalogs) is not ProjectModuleCatalogSet
        or type(resolutions) is not ProjectTypeSourceResolutionSet
        or type(semantic_facts) is not ProjectModuleSemanticFactSet
        or type(attribution) is not ProjectModuleAttributionFactSet
    ):
        raise ValueError("Project row keys require exact existing sidecars.")

    diagnostics_by_path: dict[str, tuple[Diagnostic, ...]] = {}
    shape_diagnostics: list[Diagnostic] = []
    for module in semantic_result.modules:
        assert module.parsed_input is not None
        diagnostics = tuple(check_shape_structures(module.parsed_input.script))
        diagnostics_by_path[module.path] = diagnostics
        shape_diagnostics.extend(diagnostics)

    declarations: list[ProjectUniqueDeclarationOccurrence] = []
    declarations_by_shape: dict[
        ProjectDeclarationOccurrenceIdentity,
        list[ProjectUniqueDeclarationOccurrence],
    ] = {}
    for catalog in catalogs.catalogs:
        module_diagnostics = diagnostics_by_path[catalog.module_path]
        for occurrence in catalog.occurrences:
            if type(occurrence.definition) is not ShapeDef:
                continue
            shape = occurrence.definition
            shape_identity = _declaration_identity(occurrence)
            for item_position, item in enumerate(shape.items):
                if type(item) is not UniqueDef:
                    continue
                declaration = ProjectUniqueDeclarationOccurrence(
                    identity=ProjectUniqueDeclarationIdentity(
                        shape=shape_identity,
                        shape_item_position=item_position,
                    ),
                    shape_occurrence=occurrence,
                    unique=item,
                    diagnostics=_unique_diagnostics(
                        shape,
                        item,
                        module_diagnostics,
                    ),
                )
                declarations.append(declaration)
                declarations_by_shape.setdefault(shape_identity, []).append(declaration)

    subjects: list[ProjectRowUniquenessSubject] = []
    for catalog in catalogs.catalogs:
        environment_bucket = resolutions.find_module_path(catalog.module_path)
        environment = environment_bucket[0] if len(environment_bucket) == 1 else None
        for source in catalog.occurrences:
            definition = source.definition
            if type(definition) is not SourceDef or definition.shape_name is None:
                continue
            resolution_bucket = (
                () if environment is None else environment.find_source(definition)
            )
            if len(resolution_bucket) != 1:
                issues = _source_resolution_issues(source, resolutions)
                subjects.append(_unresolved_source_terminal(source, issues))
                continue
            resolution = resolution_bucket[0]
            target_shape = resolution.target_symbol.target_occurrence
            shape_declarations = tuple(
                declarations_by_shape.get(_declaration_identity(target_shape), ())
            )
            if not shape_declarations:
                continue
            semantic_bucket = semantic_facts.find_owner(source)
            for declaration in shape_declarations:
                if not declaration.admitted:
                    subjects.append(
                        _invalid_unique_terminal(
                            source=source,
                            declaration=declaration,
                            resolution=resolution,
                        )
                    )
                    continue
                if len(semantic_bucket) != 1:
                    subjects.append(
                        _source_semantic_failure(
                            source=source,
                            declaration=declaration,
                            resolution=resolution,
                            ambiguous=len(semantic_bucket) > 1,
                        )
                    )
                    continue
                subjects.append(
                    _evidence_application(
                        source=source,
                        declaration=declaration,
                        resolution=resolution,
                        semantic=semantic_bucket[0],
                        attribution=attribution,
                    )
                )
    evidence = tuple(
        subject for subject in subjects if type(subject) is ProjectRowUniquenessEvidence
    )
    return ProjectRowKeySet(
        semantic_result=semantic_result,
        shape_diagnostics=tuple(shape_diagnostics),
        declarations=tuple(declarations),
        subjects=tuple(subjects),
        candidate_keys=_candidate_frontier(evidence),
    )
