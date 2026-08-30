"""Private current Project IR operators and exact property-transfer laws."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import cast

from pietto._project.aggregate_grouped_clause_facts import (
    ProjectAggregateGroupedClauseReadinessStatus,
)
from pietto._project.model import ProjectRelationRowSchemaStatus
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleCandidateBucketStatus,
    ProjectModuleFactOccurrenceRole,
    ProjectModuleRelationSemanticFacts,
)
from pietto._project.project_ir import (
    ProjectIRConcreteRelationSubject,
    ProjectIROperatorFlowUseOccurrence,
    ProjectIRPlanNodeOccurrence,
    ProjectIRStructuralStage,
    _declaration_identity,
    _require_exact_tuple,
)
from pietto._project.project_ir_properties import (
    ProjectIRCurrentOutput,
    ProjectIREffectEvidence,
    ProjectIREstimateBoundary,
    ProjectIRPropertyStage,
    ProjectIRProvidedBagMultiplicity,
    ProjectIRProvidedCardinalityUpperBound,
    ProjectIRProvidedClosedBindings,
    ProjectIRProvidedEvaluationPolicy,
    ProjectIRProvidedLocalGrainEvidence,
    ProjectIRProvidedOutputShape,
    ProjectIRProvidedProperty,
    ProjectIRProvidedPropertySlot,
    ProjectIRProvidedRelationOrdering,
    ProjectIRRelationRowOutput,
    ProjectIRRequiredRowShape,
    ProjectIRRowShape,
    ProjectIRScalarFieldOutput,
    ProjectIRStageRowCheckpointKind,
    ProjectIRStageRowShape,
    ProjectIRStageScalarFieldOutput,
    ProjectIRUnavailableProvidedProperty,
    _PROVIDED_PROPERTY_TYPES,
)
from pietto.ast_nodes import LiteralExpr, QueryDef, SourceDef, TableDef
from pietto.semantic.relation_limits import MAX_RELATION_LIMIT

__all__: tuple[str, ...] = ()


class ProjectIRLogicalOperatorKind(StrEnum):
    """The exact current target-independent logical operator sequence."""

    RELATION_INPUT = "relation_input"
    ROW_FILTER = "row_filter"
    GROUP_AGGREGATE = "group_aggregate"
    RESULT_FILTER = "result_filter"
    WINDOW_EVALUATION = "window_evaluation"
    FINAL_PROJECTION = "final_projection"
    RELATION_ORDERING = "relation_ordering"
    LIMIT = "limit"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRLogicalOperatorOccurrence:
    """One current logical operator attached to an existing plan-node occurrence."""

    node: ProjectIRPlanNodeOccurrence
    kind: ProjectIRLogicalOperatorKind
    evidence: ProjectModuleRelationSemanticFacts = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.node) is not ProjectIRPlanNodeOccurrence:
            raise TypeError("Logical operator requires a plan-node occurrence.")
        if type(self.kind) is not ProjectIRLogicalOperatorKind:
            raise TypeError("Logical operator requires an exact current kind.")
        if type(self.evidence) is not ProjectModuleRelationSemanticFacts:
            raise TypeError("Logical operator requires exact semantic evidence.")
        if (
            self.evidence.state.status is not ProjectRelationRowSchemaStatus.CONCRETE
            or _declaration_identity(self.evidence.owner) != self.node.anchor.identity
        ):
            raise ValueError("Logical operator evidence must match its concrete node.")
        if self.kind not in _expected_operator_kinds(self.evidence):
            raise ValueError("Logical operator kind lacks exact current evidence.")


def _expected_operator_kinds(
    evidence: ProjectModuleRelationSemanticFacts,
) -> tuple[ProjectIRLogicalOperatorKind, ...]:
    definition = evidence.owner.definition
    if type(definition) is SourceDef:
        if evidence.resolution is not None:
            raise ValueError("Source relation input cannot carry a resolution.")
        return (ProjectIRLogicalOperatorKind.RELATION_INPUT,)
    if type(definition) not in {TableDef, QueryDef}:
        raise TypeError("Logical operators require a current relation definition.")
    definition = cast(TableDef | QueryDef, definition)
    if evidence.resolution is None:
        raise ValueError("Derived relation input requires exact resolution evidence.")

    kinds: list[ProjectIRLogicalOperatorKind] = [
        ProjectIRLogicalOperatorKind.RELATION_INPUT
    ]
    if definition.where_clause is not None:
        kinds.append(ProjectIRLogicalOperatorKind.ROW_FILTER)
    readiness = evidence.aggregate_grouped_clause_readiness
    if readiness is not None:
        if (
            readiness.status
            is not ProjectAggregateGroupedClauseReadinessStatus.CONCRETE
        ):
            raise ValueError("Concrete group operator requires concrete readiness.")
        kinds.append(ProjectIRLogicalOperatorKind.GROUP_AGGREGATE)
    if definition.satisfying_clause is not None:
        satisfying = tuple(
            item
            for item in evidence.clause_dependencies
            if item.role is ProjectModuleFactOccurrenceRole.SATISFYING
        )
        if any(
            item.status is not ProjectModuleCandidateBucketStatus.CONCRETE
            for item in satisfying
        ):
            raise ValueError("Result filter requires complete concrete evidence.")
        kinds.append(ProjectIRLogicalOperatorKind.RESULT_FILTER)
    if evidence.window_outputs:
        if any(
            item.status is not ProjectModuleCandidateBucketStatus.CONCRETE
            or item.project_fact is None
            for item in evidence.window_outputs
        ):
            raise ValueError("Window operator requires complete concrete evidence.")
        kinds.append(ProjectIRLogicalOperatorKind.WINDOW_EVALUATION)
    if len(evidence.select_facts) != len(definition.select_items):
        raise ValueError("Projection operator requires complete selected outputs.")
    kinds.append(ProjectIRLogicalOperatorKind.FINAL_PROJECTION)
    if definition.order_by_clause is not None:
        kinds.append(ProjectIRLogicalOperatorKind.RELATION_ORDERING)
    if definition.limit_clause is not None:
        expression = definition.limit_clause.expression
        if (
            type(expression) is not LiteralExpr
            or type(expression.value) is not int
            or not 0 <= expression.value <= MAX_RELATION_LIMIT
        ):
            raise ValueError("Limit operator requires a validated static limit.")
        kinds.append(ProjectIRLogicalOperatorKind.LIMIT)
    return tuple(kinds)


def project_ir_preserved_property_slots(
    kind: ProjectIRLogicalOperatorKind,
) -> tuple[ProjectIRProvidedPropertySlot, ...]:
    """Return only properties current semantics prove this operator preserves."""

    if type(kind) is not ProjectIRLogicalOperatorKind:
        raise TypeError("Property preservation requires an exact operator kind.")
    shape = ProjectIRProvidedPropertySlot.OUTPUT_SHAPE
    cardinality = ProjectIRProvidedPropertySlot.CARDINALITY_BOUNDS
    multiplicity = ProjectIRProvidedPropertySlot.MULTIPLICITY
    ordering = ProjectIRProvidedPropertySlot.RELATION_RESULT_ORDERING
    grain = ProjectIRProvidedPropertySlot.LOCAL_GRAIN_EVIDENCE
    bindings = ProjectIRProvidedPropertySlot.FREE_BINDINGS
    if kind is ProjectIRLogicalOperatorKind.ROW_FILTER:
        return (shape, cardinality, multiplicity, ordering, bindings)
    if kind is ProjectIRLogicalOperatorKind.GROUP_AGGREGATE:
        return (bindings,)
    if kind is ProjectIRLogicalOperatorKind.RESULT_FILTER:
        return (shape, cardinality, multiplicity, ordering, grain, bindings)
    if kind is ProjectIRLogicalOperatorKind.WINDOW_EVALUATION:
        return (cardinality, multiplicity, grain, bindings)
    if kind is ProjectIRLogicalOperatorKind.FINAL_PROJECTION:
        return (cardinality, multiplicity, bindings)
    if kind is ProjectIRLogicalOperatorKind.RELATION_ORDERING:
        return (shape, cardinality, multiplicity, bindings)
    if kind is ProjectIRLogicalOperatorKind.LIMIT:
        return (shape, cardinality, multiplicity, ordering, grain, bindings)
    return ()


def project_ir_established_property_slots(
    kind: ProjectIRLogicalOperatorKind,
) -> tuple[ProjectIRProvidedPropertySlot, ...]:
    """Return only positive properties exact current evidence may establish."""

    if type(kind) is not ProjectIRLogicalOperatorKind:
        raise TypeError("Property establishment requires an exact operator kind.")
    shape = ProjectIRProvidedPropertySlot.OUTPUT_SHAPE
    cardinality = ProjectIRProvidedPropertySlot.CARDINALITY_BOUNDS
    multiplicity = ProjectIRProvidedPropertySlot.MULTIPLICITY
    ordering = ProjectIRProvidedPropertySlot.RELATION_RESULT_ORDERING
    grain = ProjectIRProvidedPropertySlot.LOCAL_GRAIN_EVIDENCE
    bindings = ProjectIRProvidedPropertySlot.FREE_BINDINGS
    policy = ProjectIRProvidedPropertySlot.POLICY_EVALUATION
    if kind is ProjectIRLogicalOperatorKind.RELATION_INPUT:
        return (shape, multiplicity, bindings)
    if kind is ProjectIRLogicalOperatorKind.GROUP_AGGREGATE:
        return (shape, multiplicity, grain)
    if kind is ProjectIRLogicalOperatorKind.WINDOW_EVALUATION:
        return (shape, policy)
    if kind is ProjectIRLogicalOperatorKind.FINAL_PROJECTION:
        return (shape,)
    if kind is ProjectIRLogicalOperatorKind.RELATION_ORDERING:
        return (ordering,)
    if kind is ProjectIRLogicalOperatorKind.LIMIT:
        return (cardinality,)
    return ()


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRPreservedPropertyTransfer:
    """One caller-supplied exact property preserved by a current operator."""

    operator: ProjectIRLogicalOperatorOccurrence
    input_property: ProjectIRProvidedProperty
    output_property: ProjectIRProvidedProperty

    def __post_init__(self) -> None:
        _validate_operator(self.operator, label="Preserved transfer")
        _validate_provided_property(
            self.input_property,
            label="Preserved input property",
        )
        _validate_provided_property(
            self.output_property,
            label="Preserved output property",
        )
        if (
            self.input_property.property_slot is not self.output_property.property_slot
            or self.output_property.property_slot
            not in project_ir_preserved_property_slots(self.operator.kind)
            or not _same_property_semantics(
                self.input_property,
                self.output_property,
            )
        ):
            raise ValueError("Operator cannot preserve the supplied exact property.")
        if self.output_property.output.occurrence.producer is not self.operator.node:
            raise ValueError("Preserved output property must be owned by its operator.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIREstablishedPropertyTransfer:
    """One positive property established by exact current operator evidence."""

    operator: ProjectIRLogicalOperatorOccurrence
    output_property: ProjectIRProvidedProperty

    def __post_init__(self) -> None:
        _validate_operator(self.operator, label="Established transfer")
        _validate_provided_property(
            self.output_property,
            label="Established output property",
        )
        if type(self.output_property) is ProjectIRUnavailableProvidedProperty:
            raise TypeError("Positive establishment forbids unavailable evidence.")
        if (
            self.output_property.property_slot
            not in project_ir_established_property_slots(self.operator.kind)
        ):
            raise ValueError("Operator cannot establish the supplied exact property.")
        if self.output_property.output.occurrence.producer is not self.operator.node:
            raise ValueError("Established property must be owned by its operator.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRUnavailablePropertyTransfer:
    """One explicit unknown/not-applicable output without positive inference."""

    operator: ProjectIRLogicalOperatorOccurrence
    output_property: ProjectIRUnavailableProvidedProperty

    def __post_init__(self) -> None:
        _validate_operator(self.operator, label="Unavailable transfer")
        if type(self.output_property) is not ProjectIRUnavailableProvidedProperty:
            raise TypeError("Unavailable transfer requires unavailable evidence.")
        if self.output_property.output.occurrence.producer is not self.operator.node:
            raise ValueError("Unavailable property must be owned by its operator.")


type ProjectIRPropertyTransfer = (
    ProjectIRPreservedPropertyTransfer
    | ProjectIREstablishedPropertyTransfer
    | ProjectIRUnavailablePropertyTransfer
)


def _validate_operator(operator: object, *, label: str) -> None:
    if type(operator) is not ProjectIRLogicalOperatorOccurrence:
        raise TypeError(f"{label} requires an exact logical operator.")


def _validate_provided_property(property_: object, *, label: str) -> None:
    if type(property_) not in _PROVIDED_PROPERTY_TYPES:
        raise TypeError(f"{label} requires an exact provided property.")


def _same_property_semantics(
    input_property: ProjectIRProvidedProperty,
    output_property: ProjectIRProvidedProperty,
) -> bool:
    input_output = input_property.output
    output_output = output_property.output
    if (
        type(input_output) is not type(output_output)
        or input_output.row_shape.evidence is not output_output.row_shape.evidence
    ):
        return False
    if type(input_output) is ProjectIRScalarFieldOutput:
        scalar_output = cast(ProjectIRScalarFieldOutput, output_output)
        if input_output.field != scalar_output.field:
            return False
    if type(input_output) is ProjectIRStageScalarFieldOutput:
        scalar_output = cast(ProjectIRStageScalarFieldOutput, output_output)
        if input_output.field != scalar_output.field:
            return False
    if type(input_property) is ProjectIRProvidedOutputShape:
        return (
            type(output_property) is ProjectIRProvidedOutputShape
            and input_property.output.row_shape == output_property.output.row_shape
        )
    if type(input_property) is ProjectIRProvidedBagMultiplicity:
        return type(output_property) is ProjectIRProvidedBagMultiplicity
    if type(input_property) is ProjectIRProvidedClosedBindings:
        return type(output_property) is ProjectIRProvidedClosedBindings
    if type(input_property) is ProjectIRProvidedRelationOrdering:
        return (
            type(output_property) is ProjectIRProvidedRelationOrdering
            and input_property.items == output_property.items
        )
    if type(input_property) is ProjectIRProvidedLocalGrainEvidence:
        return (
            type(output_property) is ProjectIRProvidedLocalGrainEvidence
            and input_property.occurrences == output_property.occurrences
        )
    if type(input_property) is ProjectIRProvidedCardinalityUpperBound:
        return (
            type(output_property) is ProjectIRProvidedCardinalityUpperBound
            and output_property.upper_bound <= input_property.upper_bound
        )
    if type(input_property) is ProjectIRProvidedEvaluationPolicy:
        return (
            type(output_property) is ProjectIRProvidedEvaluationPolicy
            and input_property.policy == output_property.policy
        )
    return (
        type(input_property) is ProjectIRUnavailableProvidedProperty
        and type(output_property) is ProjectIRUnavailableProvidedProperty
        and input_property.availability is output_property.availability
    )


class ProjectIRRowShapeCompatibilityStatus(StrEnum):
    """Narrow exact row-shape requirement compatibility outcome."""

    SATISFIED = "satisfied"
    NOT_SATISFIED = "not_satisfied"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRRowShapeCompatibility:
    """Pure caller-supplied exact provided-vs-required row-shape proof."""

    provided: ProjectIRProvidedOutputShape
    required: ProjectIRRequiredRowShape
    status: ProjectIRRowShapeCompatibilityStatus = field(init=False)

    def __post_init__(self) -> None:
        if type(self.provided) is not ProjectIRProvidedOutputShape:
            raise TypeError("Row-shape compatibility requires provided shape.")
        if type(self.required) is not ProjectIRRequiredRowShape:
            raise TypeError("Row-shape compatibility requires required shape.")
        output = self.provided.output
        satisfied = (
            type(output) is ProjectIRRelationRowOutput
            and output.row_shape.relation.identity == self.required.authority.target
            and output.row_shape.evidence is self.required.row_shape.evidence
            and output.row_shape == self.required.row_shape
        )
        object.__setattr__(
            self,
            "status",
            (
                ProjectIRRowShapeCompatibilityStatus.SATISFIED
                if satisfied
                else ProjectIRRowShapeCompatibilityStatus.NOT_SATISFIED
            ),
        )

    @property
    def satisfied(self) -> bool:
        return self.status is ProjectIRRowShapeCompatibilityStatus.SATISFIED


_TRANSFER_TYPES = (
    ProjectIRPreservedPropertyTransfer,
    ProjectIREstablishedPropertyTransfer,
    ProjectIRUnavailablePropertyTransfer,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRLogicalOperatorStage:
    """Exact current operator layer over one unchanged property-stage snapshot."""

    property_stage: ProjectIRPropertyStage
    operators: tuple[ProjectIRLogicalOperatorOccurrence, ...] = ()
    transfers: tuple[ProjectIRPropertyTransfer, ...] = ()
    compatibilities: tuple[ProjectIRRowShapeCompatibility, ...] = ()

    def __post_init__(self) -> None:
        if type(self.property_stage) is not ProjectIRPropertyStage:
            raise TypeError("Logical stage requires an exact property stage.")
        _require_exact_tuple(
            self.operators,
            ProjectIRLogicalOperatorOccurrence,
            label="Logical operators",
        )
        _require_exact_tuple(self.transfers, _TRANSFER_TYPES, label="Transfers")
        _require_exact_tuple(
            self.compatibilities,
            ProjectIRRowShapeCompatibility,
            label="Row-shape compatibilities",
        )
        structural = self.property_stage.structural
        if len({operator.node.ref for operator in self.operators}) != len(
            self.operators
        ):
            raise ValueError("One plan node cannot select an operator winner.")
        if tuple(operator.node for operator in self.operators) != structural.nodes:
            raise ValueError(
                "Logical operators must retain every structural node in exact order."
            )
        subjects = tuple(
            item
            for item in structural.subjects
            if type(item) is ProjectIRConcreteRelationSubject
        )
        evidences: list[ProjectModuleRelationSemanticFacts] = []
        for operator in self.operators:
            matches = tuple(
                subject
                for subject in subjects
                if subject.anchor == operator.node.anchor
            )
            if len(matches) != 1 or matches[0].evidence is not operator.evidence:
                raise ValueError(
                    "Logical operator must reuse exact concrete subject authority."
                )
            if not any(item is operator.evidence for item in evidences):
                evidences.append(operator.evidence)
        for evidence in evidences:
            pipeline = tuple(
                item for item in self.operators if item.evidence is evidence
            )
            if tuple(item.kind for item in pipeline) != _expected_operator_kinds(
                evidence
            ):
                raise ValueError("Logical operators must retain exact stage order.")
            subject = next(item for item in subjects if item.evidence is evidence)
            if subject.root is not pipeline[-1].node:
                raise ValueError(
                    "Concrete subject root must be the final logical stage."
                )
        self._validate_dataflow(evidences)
        self._validate_transfers()
        self._validate_compatibilities()

    def _row_output(
        self,
        operator: ProjectIRLogicalOperatorOccurrence,
    ) -> ProjectIRRelationRowOutput:
        matches = tuple(
            output
            for output in self.property_stage.outputs
            if type(output) is ProjectIRRelationRowOutput
            and output.occurrence.producer is operator.node
        )
        if len(matches) != 1:
            raise ValueError(
                "Every logical operator requires one exact relation-row output."
            )
        return matches[0]

    def _validate_operator_row_shape(
        self,
        operator: ProjectIRLogicalOperatorOccurrence,
        output: ProjectIRRelationRowOutput,
    ) -> None:
        definition = operator.evidence.owner.definition
        shape = output.row_shape
        if type(definition) is SourceDef:
            if type(shape) is not ProjectIRRowShape:
                raise ValueError("Source input requires its final semantic row shape.")
            return
        if type(definition) not in {TableDef, QueryDef}:
            raise TypeError("Operator row shape requires a current relation.")
        expected = {
            ProjectIRLogicalOperatorKind.RELATION_INPUT: (
                ProjectIRStageRowCheckpointKind.INPUT
            ),
            ProjectIRLogicalOperatorKind.ROW_FILTER: (
                ProjectIRStageRowCheckpointKind.INPUT
            ),
            ProjectIRLogicalOperatorKind.GROUP_AGGREGATE: (
                ProjectIRStageRowCheckpointKind.BASE_RESULT
            ),
            ProjectIRLogicalOperatorKind.RESULT_FILTER: (
                ProjectIRStageRowCheckpointKind.BASE_RESULT
            ),
            ProjectIRLogicalOperatorKind.WINDOW_EVALUATION: (
                ProjectIRStageRowCheckpointKind.FINAL
            ),
        }.get(operator.kind)
        if expected is None:
            if type(shape) is not ProjectIRRowShape:
                raise ValueError(
                    "Final relation stages require the final semantic row shape."
                )
            return
        if (
            type(shape) is not ProjectIRStageRowShape
            or shape.checkpoint.kind is not expected
        ):
            raise ValueError(
                "Intermediate operator row shape must match its semantic checkpoint."
            )

    def _validate_dataflow(
        self,
        evidences: list[ProjectModuleRelationSemanticFacts],
    ) -> None:
        flow_uses = tuple(
            use
            for use in self.structural.uses
            if type(use) is ProjectIROperatorFlowUseOccurrence
        )
        retained: list[ProjectIROperatorFlowUseOccurrence] = []
        for evidence in evidences:
            pipeline = tuple(
                item for item in self.operators if item.evidence is evidence
            )
            row_outputs = tuple(self._row_output(item) for item in pipeline)
            for operator, output in zip(pipeline, row_outputs, strict=True):
                self._validate_operator_row_shape(operator, output)
            first_incoming = tuple(
                use for use in flow_uses if use.slot.consumer is pipeline[0].node
            )
            if first_incoming:
                raise ValueError(
                    "First logical operator cannot have a flow predecessor."
                )
            for previous, current, previous_output in zip(
                pipeline,
                pipeline[1:],
                row_outputs,
                strict=False,
            ):
                incoming = tuple(
                    use for use in flow_uses if use.slot.consumer is current.node
                )
                if (
                    len(incoming) != 1
                    or incoming[0].output is not previous_output.occurrence
                    or incoming[0].output.producer is not previous.node
                ):
                    raise ValueError(
                        "Logical tuple order and operator-flow topology must agree."
                    )
                retained.append(incoming[0])
        if len(retained) != len(flow_uses) or any(
            not any(use is expected for expected in retained) for use in flow_uses
        ):
            raise ValueError("Operator-flow uses must connect exact adjacent stages.")

    def _validate_transfers(self) -> None:
        provided = self.property_stage.provided
        slot_order = tuple(ProjectIRProvidedPropertySlot)
        keys: list[tuple[int, int, int]] = []
        for transfer in self.transfers:
            if not any(transfer.operator is item for item in self.operators):
                raise ValueError("Transfer requires a retained logical operator.")
            output_property = transfer.output_property
            if not any(output_property is item for item in provided):
                raise ValueError(
                    "Transfer output must be retained by the property stage."
                )
            if type(transfer) is ProjectIRPreservedPropertyTransfer:
                if not any(transfer.input_property is item for item in provided):
                    raise ValueError(
                        "Preserved input must be retained by the property stage."
                    )
                input_output = self._flow_predecessor_output(transfer.operator)
                if (
                    input_output is None
                    or transfer.input_property.output is not input_output
                ):
                    raise ValueError(
                        "Preserved input must come from the exact flow predecessor."
                    )
            keys.append(
                (
                    transfer.operator.node.ref.position,
                    output_property.output.occurrence.ref.position,
                    slot_order.index(output_property.property_slot),
                )
            )
        if len(set(keys)) != len(keys):
            raise ValueError("One exact output property slot cannot select a transfer.")
        if tuple(keys) != tuple(sorted(keys)):
            raise ValueError("Property transfers must retain structural order.")
        if any(
            sum(transfer.output_property is property_ for transfer in self.transfers)
            != 1
            for property_ in provided
        ):
            raise ValueError(
                "Every provided property requires one exact transfer proof."
            )

    def _flow_predecessor_output(
        self,
        operator: ProjectIRLogicalOperatorOccurrence,
    ) -> ProjectIRRelationRowOutput | None:
        incoming = tuple(
            use
            for use in self.structural.uses
            if type(use) is ProjectIROperatorFlowUseOccurrence
            and use.slot.consumer is operator.node
        )
        if not incoming:
            return None
        if len(incoming) != 1:
            raise ValueError("Operator requires one exact flow predecessor.")
        matches = tuple(
            output
            for output in self.property_stage.outputs
            if type(output) is ProjectIRRelationRowOutput
            and output.occurrence is incoming[0].output
        )
        if len(matches) != 1:
            raise ValueError("Flow predecessor requires one exact row output model.")
        return matches[0]

    def _validate_compatibilities(self) -> None:
        provided = self.property_stage.provided
        required = self.property_stage.required
        keys = []
        for compatibility in self.compatibilities:
            if not any(compatibility.provided is item for item in provided):
                raise ValueError("Compatibility requires retained provided authority.")
            if not any(compatibility.required is item for item in required):
                raise ValueError("Compatibility requires retained required authority.")
            keys.append(
                (
                    compatibility.provided.output.occurrence.ref.position,
                    compatibility.required.input_slot.ref.position,
                )
            )
        if len(set(keys)) != len(keys):
            raise ValueError("Row-shape compatibility pairs must be unique.")
        if tuple(keys) != tuple(sorted(keys)):
            raise ValueError("Row-shape compatibilities must retain structural order.")
        if any(
            sum(item.required is requirement for item in self.compatibilities) != 1
            for requirement in required
        ):
            raise ValueError(
                "Every required row shape requires one exact compatibility result."
            )

    @property
    def structural(self) -> ProjectIRStructuralStage:
        return self.property_stage.structural

    @property
    def outputs(self) -> tuple[ProjectIRCurrentOutput, ...]:
        return self.property_stage.outputs

    @property
    def effects(self) -> tuple[ProjectIREffectEvidence, ...]:
        return self.property_stage.effects

    @property
    def estimates(self) -> ProjectIREstimateBoundary:
        return self.property_stage.estimates

    @property
    def free_outer_bindings(self) -> tuple[object, ...]:
        return self.property_stage.free_outer_bindings
