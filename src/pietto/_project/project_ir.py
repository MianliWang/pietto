"""Private structural Project IR identities without operator semantics."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from pietto._project.model import (
    ProjectRelationRowSchemaStatus,
    ProjectSymbolKind,
    ProjectSymbolNamespace,
)
from pietto._project.module_attribution import (
    ProjectDeclarationOccurrenceIdentity,
    ProjectModuleDependencyFact,
    ProjectModuleDependencyKind,
    ProjectModuleReferenceOccurrenceIdentity,
    ProjectModuleReferenceRole,
    ProjectModuleRowFieldIdentity,
)
from pietto._project.module_catalog import ProjectDeclarationOccurrence
from pietto._project.module_relation_resolution import (
    ProjectModuleRelationResolutionIssue,
    ProjectModuleRelationResolutionIssueStatus,
    ProjectResolvedModuleRelationReference,
)
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleCandidateBucketStatus,
    ProjectModuleFactOccurrenceRole,
    ProjectModuleRelationSemanticFacts,
)

__all__: tuple[str, ...] = ()

_RELATION_KINDS = frozenset(
    {ProjectSymbolKind.SOURCE, ProjectSymbolKind.TABLE, ProjectSymbolKind.QUERY}
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectIRSnapshotScope:
    """Opaque identity owner for one runtime Project IR snapshot."""

    def __repr__(self) -> str:
        """Avoid leaking the opaque runtime token through object addresses."""

        return "ProjectIRSnapshotScope()"


def _validate_ref(
    scope: object,
    position: object,
    *,
    label: str,
) -> None:
    if type(scope) is not ProjectIRSnapshotScope:
        raise TypeError(f"{label} requires an exact snapshot scope.")
    if type(position) is not int or position < 0:
        raise TypeError(f"{label} position must be a non-negative integer.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRPlanNodeRef:
    """One plan-node occurrence coordinate in one structural snapshot."""

    scope: ProjectIRSnapshotScope
    position: int

    def __post_init__(self) -> None:
        _validate_ref(self.scope, self.position, label="Plan-node ref")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIROutputValueRef:
    """One output-value occurrence coordinate in one structural snapshot."""

    scope: ProjectIRSnapshotScope
    position: int

    def __post_init__(self) -> None:
        _validate_ref(self.scope, self.position, label="Output-value ref")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRUseRef:
    """One relation/value-use occurrence coordinate in one structural snapshot."""

    scope: ProjectIRSnapshotScope
    position: int

    def __post_init__(self) -> None:
        _validate_ref(self.scope, self.position, label="Use ref")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRInputSlotRef:
    """One consumer input-slot occurrence coordinate in one structural snapshot."""

    scope: ProjectIRSnapshotScope
    position: int

    def __post_init__(self) -> None:
        _validate_ref(self.scope, self.position, label="Input-slot ref")


def _declaration_identity(
    occurrence: ProjectDeclarationOccurrence,
) -> ProjectDeclarationOccurrenceIdentity:
    if type(occurrence) is not ProjectDeclarationOccurrence:
        raise TypeError("Declaration identity requires an exact occurrence.")
    return ProjectDeclarationOccurrenceIdentity(
        identity=occurrence.identity,
        module_position=occurrence.module_position,
        declaration_position=occurrence.declaration_position,
    )


def _validate_relation_identity(identity: object, *, label: str) -> None:
    if type(identity) is not ProjectDeclarationOccurrenceIdentity:
        raise TypeError(f"{label} requires a declaration occurrence identity.")
    if (
        identity.identity.namespace is not ProjectSymbolNamespace.RELATION
        or identity.identity.declaration_kind not in _RELATION_KINDS
    ):
        raise ValueError(f"{label} requires a relation declaration.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRRelationAnchor:
    """Exact existing declaration-occurrence anchor for one relation subject."""

    identity: ProjectDeclarationOccurrenceIdentity

    def __post_init__(self) -> None:
        _validate_relation_identity(self.identity, label="Relation anchor")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRResolvedRelationAnchor:
    """Exact relation resolution plus Phase 59 dependency provenance."""

    resolution: ProjectResolvedModuleRelationReference = field(
        repr=False,
        compare=False,
        hash=False,
    )
    dependency: ProjectModuleDependencyFact = field(
        repr=False,
        compare=False,
        hash=False,
    )
    reference: ProjectModuleReferenceOccurrenceIdentity = field(init=False)
    target: ProjectDeclarationOccurrenceIdentity = field(init=False)

    def __post_init__(self) -> None:
        if type(self.resolution) is not ProjectResolvedModuleRelationReference:
            raise TypeError("Resolved relation anchor requires exact resolution.")
        reference = ProjectModuleReferenceOccurrenceIdentity(
            owner=_declaration_identity(self.resolution.reference.owner),
            role=ProjectModuleReferenceRole.RELATION_FROM,
            member_position=0,
        )
        target = _declaration_identity(self.resolution.target_symbol.target_occurrence)
        _validate_relation_identity(target, label="Resolved relation target")
        if (
            type(self.dependency) is not ProjectModuleDependencyFact
            or self.dependency.kind
            is not ProjectModuleDependencyKind.RELATION_REFERENCE
            or self.dependency.reference != reference
            or self.dependency.target_declaration != target
        ):
            raise ValueError(
                "Resolved relation anchor requires exact dependency provenance."
            )
        object.__setattr__(self, "reference", reference)
        object.__setattr__(self, "target", target)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRFieldAnchor:
    """Exact existing Project row-field occurrence anchor."""

    identity: ProjectModuleRowFieldIdentity

    def __post_init__(self) -> None:
        if type(self.identity) is not ProjectModuleRowFieldIdentity:
            raise TypeError("Field anchor requires a row field identity.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRResolvedFieldAnchor:
    """Exact Phase 59 row-field dependency occurrence and provenance."""

    dependency: ProjectModuleDependencyFact = field(
        repr=False,
        compare=False,
        hash=False,
    )
    reference: ProjectModuleReferenceOccurrenceIdentity = field(init=False)
    target: ProjectModuleRowFieldIdentity = field(init=False)

    def __post_init__(self) -> None:
        if (
            type(self.dependency) is not ProjectModuleDependencyFact
            or self.dependency.kind
            is not ProjectModuleDependencyKind.ROW_FIELD_REFERENCE
            or self.dependency.reference.role
            is not ProjectModuleReferenceRole.ROW_FIELD
            or self.dependency.target_row_field is None
        ):
            raise ValueError(
                "Resolved field anchor requires exact dependency provenance."
            )
        object.__setattr__(self, "reference", self.dependency.reference)
        object.__setattr__(self, "target", self.dependency.target_row_field)


type ProjectIROutputAnchor = ProjectIRRelationAnchor | ProjectIRFieldAnchor
type ProjectIRUseAnchor = ProjectIRResolvedRelationAnchor | ProjectIRResolvedFieldAnchor


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRPlanNodeOccurrence:
    """A structural plan-node identity with no logical operator kind."""

    ref: ProjectIRPlanNodeRef
    anchor: ProjectIRRelationAnchor

    def __post_init__(self) -> None:
        if type(self.ref) is not ProjectIRPlanNodeRef:
            raise TypeError("Plan-node occurrence requires a plan-node ref.")
        if type(self.anchor) is not ProjectIRRelationAnchor:
            raise TypeError("Plan-node occurrence requires a relation anchor.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIROutputValueOccurrence:
    """A structural node output with no row/output property semantics."""

    ref: ProjectIROutputValueRef
    producer: ProjectIRPlanNodeOccurrence
    anchor: ProjectIROutputAnchor

    def __post_init__(self) -> None:
        if type(self.ref) is not ProjectIROutputValueRef:
            raise TypeError("Output occurrence requires an output-value ref.")
        if type(self.producer) is not ProjectIRPlanNodeOccurrence:
            raise TypeError("Output occurrence requires a plan-node producer.")
        if self.ref.scope is not self.producer.ref.scope:
            raise ValueError("Output and producer require the same snapshot scope.")
        if type(self.anchor) is ProjectIRRelationAnchor:
            if self.anchor != self.producer.anchor:
                raise ValueError("Relation output must retain its producer anchor.")
        elif type(self.anchor) is ProjectIRFieldAnchor:
            if self.anchor.identity.owner != self.producer.anchor.identity:
                raise ValueError("Field output must belong to its producer relation.")
        else:
            raise TypeError("Output occurrence requires a typed output anchor.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRInputSlotOccurrence:
    """One consumer-owned input ordinal without use-role duplication."""

    ref: ProjectIRInputSlotRef
    consumer: ProjectIRPlanNodeOccurrence
    input_ordinal: int

    def __post_init__(self) -> None:
        if type(self.ref) is not ProjectIRInputSlotRef:
            raise TypeError("Input-slot occurrence requires an input-slot ref.")
        if type(self.consumer) is not ProjectIRPlanNodeOccurrence:
            raise TypeError("Input-slot occurrence requires a plan-node consumer.")
        if self.ref.scope is not self.consumer.ref.scope:
            raise ValueError("Input slot and consumer require the same snapshot scope.")
        if type(self.input_ordinal) is not int or self.input_ordinal < 0:
            raise ValueError("Input-slot ordinal must be a non-negative integer.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRUseOccurrence:
    """Exact producer-output to consumer-slot use occurrence."""

    ref: ProjectIRUseRef
    output: ProjectIROutputValueOccurrence
    slot: ProjectIRInputSlotOccurrence
    role: ProjectModuleFactOccurrenceRole
    source_order: int
    anchor: ProjectIRUseAnchor

    def __post_init__(self) -> None:
        if type(self.ref) is not ProjectIRUseRef:
            raise TypeError("Use occurrence requires a use ref.")
        if type(self.output) is not ProjectIROutputValueOccurrence:
            raise TypeError("Use occurrence requires an output occurrence.")
        if type(self.slot) is not ProjectIRInputSlotOccurrence:
            raise TypeError("Use occurrence requires an input-slot occurrence.")
        if not (self.ref.scope is self.output.ref.scope is self.slot.ref.scope):
            raise ValueError("Use composition requires the same snapshot scope.")
        if type(self.role) is not ProjectModuleFactOccurrenceRole:
            raise TypeError("Use occurrence requires an existing exact role.")
        if type(self.source_order) is not int or self.source_order < 0:
            raise ValueError("Use source order must be a non-negative integer.")
        if type(self.anchor) is ProjectIRResolvedRelationAnchor:
            if self.role is not ProjectModuleFactOccurrenceRole.RELATION_INPUT:
                raise ValueError("Resolved relation use requires RELATION_INPUT role.")
            if (
                type(self.output.anchor) is not ProjectIRRelationAnchor
                or self.anchor.target != self.output.anchor.identity
                or self.anchor.reference.owner != self.slot.consumer.anchor.identity
            ):
                raise ValueError("Resolved relation use must retain exact endpoints.")
        elif type(self.anchor) is ProjectIRResolvedFieldAnchor:
            if self.role is ProjectModuleFactOccurrenceRole.RELATION_INPUT:
                raise ValueError("Field use cannot claim RELATION_INPUT role.")
            if (
                type(self.output.anchor) is not ProjectIRFieldAnchor
                or self.anchor.target != self.output.anchor.identity
                or self.anchor.reference.owner != self.slot.consumer.anchor.identity
            ):
                raise ValueError(
                    "Field use must retain exact endpoints and provenance."
                )
        else:
            raise TypeError("Use occurrence requires a typed semantic anchor.")

    @property
    def input_ordinal(self) -> int:
        """Expose the ordinal owned exactly once by the consumer slot."""

        return self.slot.input_ordinal


class ProjectIRRelationConstructionState(StrEnum):
    """Published structural availability states for one relation subject."""

    CONCRETE = "concrete"
    UNKNOWN = "unknown"
    DEFERRED = "deferred"
    BLOCKED = "blocked"
    AMBIGUOUS = "ambiguous"


type ProjectIRRelationConstructionEvidence = (
    ProjectModuleRelationSemanticFacts | ProjectModuleRelationResolutionIssue
)


def _evidence_matches_anchor(
    anchor: ProjectIRRelationAnchor,
    evidence: ProjectIRRelationConstructionEvidence,
) -> bool:
    if type(evidence) is ProjectModuleRelationSemanticFacts:
        return _declaration_identity(evidence.owner) == anchor.identity
    if type(evidence) is not ProjectModuleRelationResolutionIssue:
        return False
    if evidence.reference is not None and (
        _declaration_identity(evidence.reference.owner) == anchor.identity
    ):
        return True
    return any(
        _declaration_identity(occurrence) == anchor.identity
        for occurrence in evidence.occurrences
    )


def _semantic_facts_have_ambiguity(
    evidence: ProjectModuleRelationSemanticFacts,
) -> bool:
    ambiguous = ProjectModuleCandidateBucketStatus.AMBIGUOUS
    if any(item.status is ambiguous for item in evidence.clause_dependencies):
        return True
    if any(
        reference.status is ambiguous
        for binding in evidence.let_bindings
        for reference in binding.references
    ):
        return True
    return any(
        reference.status is ambiguous
        for selected in evidence.select_facts
        for reference in selected.references
    )


def _evidence_supports_state(
    evidence: ProjectIRRelationConstructionEvidence,
    state: ProjectIRRelationConstructionState,
) -> bool:
    if type(evidence) is ProjectModuleRelationSemanticFacts:
        if state is ProjectIRRelationConstructionState.AMBIGUOUS:
            return _semantic_facts_have_ambiguity(evidence)
        expected = {
            ProjectRelationRowSchemaStatus.UNKNOWN: (
                ProjectIRRelationConstructionState.UNKNOWN
            ),
            ProjectRelationRowSchemaStatus.DEFERRED: (
                ProjectIRRelationConstructionState.DEFERRED
            ),
            ProjectRelationRowSchemaStatus.BLOCKED: (
                ProjectIRRelationConstructionState.BLOCKED
            ),
        }.get(evidence.state.status)
        return state is expected
    return (
        type(evidence) is ProjectModuleRelationResolutionIssue
        and state is ProjectIRRelationConstructionState.AMBIGUOUS
        and evidence.status
        is ProjectModuleRelationResolutionIssueStatus.AMBIGUOUS_LOCAL_RELATION_NAME
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRConcreteRelationSubject:
    """One concrete relation subject and its structural root identity seam."""

    anchor: ProjectIRRelationAnchor
    evidence: ProjectModuleRelationSemanticFacts = field(
        repr=False,
        compare=False,
        hash=False,
    )
    root: ProjectIRPlanNodeOccurrence

    def __post_init__(self) -> None:
        if type(self.anchor) is not ProjectIRRelationAnchor:
            raise TypeError("Concrete subject requires a relation anchor.")
        if type(self.evidence) is not ProjectModuleRelationSemanticFacts:
            raise TypeError("Concrete subject requires exact semantic evidence.")
        if not _evidence_matches_anchor(self.anchor, self.evidence):
            raise ValueError("Concrete evidence does not match its subject anchor.")
        if self.evidence.state.status is not ProjectRelationRowSchemaStatus.CONCRETE:
            raise ValueError("Concrete subject requires concrete semantic evidence.")
        if type(self.root) is not ProjectIRPlanNodeOccurrence:
            raise TypeError("Concrete subject requires a structural root occurrence.")
        if self.root.anchor != self.anchor:
            raise ValueError("Concrete root must retain its subject anchor.")

    @property
    def state(self) -> ProjectIRRelationConstructionState:
        return ProjectIRRelationConstructionState.CONCRETE


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRNonConcreteRelationSubject:
    """One typed terminal with exact evidence and no fake plan root."""

    anchor: ProjectIRRelationAnchor
    state: ProjectIRRelationConstructionState
    evidence: ProjectIRRelationConstructionEvidence = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.anchor) is not ProjectIRRelationAnchor:
            raise TypeError("Non-concrete subject requires a relation anchor.")
        if type(self.state) is not ProjectIRRelationConstructionState:
            raise TypeError("Non-concrete subject requires an exact state.")
        if self.state is ProjectIRRelationConstructionState.CONCRETE:
            raise ValueError("Terminal requires a non-concrete state.")
        if type(self.evidence) not in {
            ProjectModuleRelationSemanticFacts,
            ProjectModuleRelationResolutionIssue,
        }:
            raise TypeError("Terminal requires exact semantic or issue evidence.")
        if not _evidence_matches_anchor(self.anchor, self.evidence):
            raise ValueError("Terminal evidence does not match its subject anchor.")
        if not _evidence_supports_state(self.evidence, self.state):
            raise ValueError("Evidence does not support construction state.")


type ProjectIRRelationSubject = (
    ProjectIRConcreteRelationSubject | ProjectIRNonConcreteRelationSubject
)
type _ProjectIRStructuralOccurrence = (
    ProjectIRPlanNodeOccurrence
    | ProjectIROutputValueOccurrence
    | ProjectIRInputSlotOccurrence
    | ProjectIRUseOccurrence
)


def _require_exact_tuple(
    values: object,
    item_type: type[object] | tuple[type[object], ...],
    *,
    label: str,
) -> None:
    if type(values) is not tuple:
        raise TypeError(f"{label} must be an exact tuple.")
    allowed = item_type if isinstance(item_type, tuple) else (item_type,)
    if any(type(item) not in allowed for item in values):
        raise TypeError(f"{label} contains an invalid carrier.")


def _validate_occurrence_order(
    values: tuple[_ProjectIRStructuralOccurrence, ...],
    scope: ProjectIRSnapshotScope,
    *,
    label: str,
) -> None:
    if any(item.ref.scope is not scope for item in values):
        raise ValueError(f"{label} must use the stage snapshot scope.")
    positions = tuple(item.ref.position for item in values)
    if positions != tuple(range(len(values))):
        raise ValueError(f"{label} coordinates must be unique and ordered.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRStructuralStage:
    """Identity topology and construction subjects before operator semantics."""

    scope: ProjectIRSnapshotScope
    nodes: tuple[ProjectIRPlanNodeOccurrence, ...] = ()
    outputs: tuple[ProjectIROutputValueOccurrence, ...] = ()
    input_slots: tuple[ProjectIRInputSlotOccurrence, ...] = ()
    uses: tuple[ProjectIRUseOccurrence, ...] = ()
    subjects: tuple[ProjectIRRelationSubject, ...] = ()

    def __post_init__(self) -> None:
        if type(self.scope) is not ProjectIRSnapshotScope:
            raise TypeError("Structural stage requires an exact snapshot scope.")
        _require_exact_tuple(
            self.nodes,
            ProjectIRPlanNodeOccurrence,
            label="Plan nodes",
        )
        _require_exact_tuple(
            self.outputs,
            ProjectIROutputValueOccurrence,
            label="Output values",
        )
        _require_exact_tuple(
            self.input_slots,
            ProjectIRInputSlotOccurrence,
            label="Input slots",
        )
        _require_exact_tuple(self.uses, ProjectIRUseOccurrence, label="Uses")
        _require_exact_tuple(
            self.subjects,
            (
                ProjectIRConcreteRelationSubject,
                ProjectIRNonConcreteRelationSubject,
            ),
            label="Relation subjects",
        )
        _validate_occurrence_order(self.nodes, self.scope, label="plan-node")
        _validate_occurrence_order(self.outputs, self.scope, label="Output-value")
        _validate_occurrence_order(self.input_slots, self.scope, label="Input-slot")
        _validate_occurrence_order(self.uses, self.scope, label="Use")
        if tuple(item.source_order for item in self.uses) != tuple(
            range(len(self.uses))
        ):
            raise ValueError("Use source order must be unique and ordered.")
        if any(
            not any(output.producer is node for node in self.nodes)
            for output in self.outputs
        ):
            raise ValueError("Stage outputs require retained producer nodes.")
        if any(
            not any(slot.consumer is node for node in self.nodes)
            for slot in self.input_slots
        ):
            raise ValueError("Stage input slots require retained consumer nodes.")
        if any(
            not any(use.output is output for output in self.outputs)
            or not any(use.slot is slot for slot in self.input_slots)
            for use in self.uses
        ):
            raise ValueError("Stage uses require retained output and slot occurrences.")
        slot_keys = tuple(
            (slot.consumer.ref, slot.input_ordinal) for slot in self.input_slots
        )
        if len(set(slot_keys)) != len(slot_keys):
            raise ValueError("Consumer input ordinals must be unique per node.")
        if len({use.slot.ref for use in self.uses}) != len(self.uses):
            raise ValueError("One input slot cannot select a use winner.")
        subject_keys = tuple(subject.anchor.identity for subject in self.subjects)
        subject_order = tuple(
            (identity.module_position, identity.declaration_position)
            for identity in subject_keys
        )
        if len(set(subject_keys)) != len(subject_keys) or subject_order != tuple(
            sorted(subject_order)
        ):
            raise ValueError("Relation subjects must be unique and source ordered.")
        if any(
            type(subject) is ProjectIRConcreteRelationSubject
            and not any(subject.root is node for node in self.nodes)
            for subject in self.subjects
        ):
            raise ValueError("Concrete subjects require retained structural roots.")

    @property
    def free_outer_bindings(self) -> tuple[object, ...]:
        """Current structural Project IR is closed and project-local."""

        return ()
