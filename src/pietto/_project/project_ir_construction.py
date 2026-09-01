"""Canonical construction of one private Project IR relation fragment."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

from pietto._project.model import ProjectRelationRowSchemaStatus, ProjectSymbolKind
from pietto._project.module_attribution import (
    ProjectModuleAttributionFactSet,
    ProjectModuleRelationOutputFieldAttribution,
)
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleRelationSemanticFacts,
    ProjectModuleWindowOutputFact,
)
from pietto._project.project_ir import (
    ProjectIRConcreteRelationSubject,
    ProjectIRFieldAnchor,
    ProjectIRInputSlotOccurrence,
    ProjectIRInputSlotRef,
    ProjectIRNonConcreteRelationSubject,
    ProjectIROperatorFlowUseOccurrence,
    ProjectIROutputValueOccurrence,
    ProjectIROutputValueRef,
    ProjectIRPlanNodeOccurrence,
    ProjectIRPlanNodeRef,
    ProjectIRRelationAnchor,
    ProjectIRRelationConstructionState,
    ProjectIRSnapshotScope,
    ProjectIRStageFieldAnchor,
    ProjectIRStructuralStage,
    ProjectIRUseRef,
    _declaration_identity,
    _semantic_facts_have_ambiguity,
)
from pietto._project.project_ir_operators import (
    ProjectIREstablishedPropertyTransfer,
    ProjectIRLogicalOperatorKind,
    ProjectIRLogicalOperatorOccurrence,
    ProjectIRLogicalOperatorStage,
    ProjectIRPreservedPropertyTransfer,
    ProjectIRPropertyTransfer,
    _expected_operator_kinds,
    project_ir_established_property_slots,
    project_ir_preserved_property_slots,
)
from pietto._project.project_ir_properties import (
    ProjectIRCurrentOutput,
    ProjectIRCurrentRowShape,
    ProjectIRDeterminismEvidence,
    ProjectIREffectEvidence,
    ProjectIRErrorBehaviorEvidence,
    ProjectIREstimateBoundary,
    ProjectIREvaluationCountEvidence,
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
    ProjectIRRowField,
    ProjectIRRowShape,
    ProjectIRScalarFieldOutput,
    ProjectIRSideEffectEvidence,
    ProjectIRStageRowCheckpoint,
    ProjectIRStageRowCheckpointKind,
    ProjectIRStageRowField,
    ProjectIRStageRowShape,
    ProjectIRStageScalarFieldOutput,
)
from pietto.ast_nodes import QueryDef, TableDef

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRAllocationState:
    """Explicit next coordinates for one snapshot's four ref domains."""

    scope: ProjectIRSnapshotScope
    next_plan_node_position: int = 0
    next_output_value_position: int = 0
    next_input_slot_position: int = 0
    next_use_position: int = 0

    def __post_init__(self) -> None:
        if type(self.scope) is not ProjectIRSnapshotScope:
            raise TypeError("Project IR allocation requires an exact snapshot scope.")
        for value in (
            self.next_plan_node_position,
            self.next_output_value_position,
            self.next_input_slot_position,
            self.next_use_position,
        ):
            if type(value) is not int or value < 0:
                raise TypeError(
                    "Project IR allocation coordinates must be non-negative integers."
                )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRConcreteSingleRelationFragment:
    """One complete canonical concrete relation fragment."""

    subject: ProjectIRConcreteRelationSubject
    attribution: ProjectModuleAttributionFactSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    starting_allocation: ProjectIRAllocationState
    ending_allocation: ProjectIRAllocationState
    structural_stage: ProjectIRStructuralStage
    property_stage: ProjectIRPropertyStage
    logical_stage: ProjectIRLogicalOperatorStage
    root: ProjectIRPlanNodeOccurrence
    root_relation_output: ProjectIRRelationRowOutput
    final_scalar_outputs: tuple[ProjectIRScalarFieldOutput, ...] = ()

    def __post_init__(self) -> None:
        if type(self.subject) is not ProjectIRConcreteRelationSubject:
            raise TypeError("Concrete fragment requires a concrete subject.")
        _reject_concrete_authored_join(self.subject.evidence)
        if type(self.attribution) is not ProjectModuleAttributionFactSet:
            raise TypeError("Concrete fragment requires exact attribution authority.")
        if not (
            type(self.starting_allocation) is ProjectIRAllocationState
            and type(self.ending_allocation) is ProjectIRAllocationState
            and self.starting_allocation.scope
            is self.ending_allocation.scope
            is self.structural_stage.scope
        ):
            raise ValueError("Concrete fragment requires one exact allocation scope.")
        if (
            type(self.structural_stage) is not ProjectIRStructuralStage
            or type(self.property_stage) is not ProjectIRPropertyStage
            or type(self.logical_stage) is not ProjectIRLogicalOperatorStage
            or self.property_stage.structural is not self.structural_stage
            or self.logical_stage.property_stage is not self.property_stage
        ):
            raise ValueError("Concrete fragment stages must retain exact composition.")
        if (
            type(self.root) is not ProjectIRPlanNodeOccurrence
            or self.root is not self.subject.root
            or self.root_relation_output.occurrence.producer is not self.root
            or not any(
                self.root_relation_output is output
                for output in self.property_stage.outputs
            )
        ):
            raise ValueError("Concrete fragment must expose its exact root output.")
        if type(self.final_scalar_outputs) is not tuple or any(
            type(output) is not ProjectIRScalarFieldOutput
            or not any(output is retained for retained in self.property_stage.outputs)
            for output in self.final_scalar_outputs
        ):
            raise TypeError("Concrete fragment requires exact final scalar outputs.")

    @property
    def semantic_facts(self) -> ProjectModuleRelationSemanticFacts:
        return self.subject.evidence

    @property
    def snapshot_scope(self) -> ProjectIRSnapshotScope:
        return self.structural_stage.scope


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRNonConcreteSingleRelationFragment:
    """One exact non-concrete terminal with zero allocation."""

    subject: ProjectIRNonConcreteRelationSubject
    attribution: ProjectModuleAttributionFactSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    starting_allocation: ProjectIRAllocationState
    ending_allocation: ProjectIRAllocationState
    structural_stage: ProjectIRStructuralStage
    property_stage: ProjectIRPropertyStage
    logical_stage: ProjectIRLogicalOperatorStage
    root: None = field(init=False, default=None)
    root_relation_output: None = field(init=False, default=None)
    final_scalar_outputs: tuple[ProjectIRScalarFieldOutput, ...] = field(
        init=False,
        default=(),
    )

    def __post_init__(self) -> None:
        if type(self.subject) is not ProjectIRNonConcreteRelationSubject:
            raise TypeError("Non-concrete fragment requires an exact terminal.")
        if type(self.attribution) is not ProjectModuleAttributionFactSet:
            raise TypeError(
                "Non-concrete fragment requires exact attribution authority."
            )
        if self.ending_allocation is not self.starting_allocation:
            raise ValueError("Non-concrete fragment must consume zero allocation.")
        if (
            self.structural_stage.scope is not self.starting_allocation.scope
            or self.property_stage.structural is not self.structural_stage
            or self.logical_stage.property_stage is not self.property_stage
            or self.structural_stage.nodes
            or self.structural_stage.outputs
            or self.structural_stage.input_slots
            or self.structural_stage.uses
            or self.logical_stage.operators
            or self.property_stage.provided
            or self.property_stage.required
            or self.property_stage.effects
        ):
            raise ValueError("Non-concrete fragment must retain an empty IR terminal.")

    @property
    def semantic_facts(self) -> ProjectModuleRelationSemanticFacts:
        evidence = self.subject.evidence
        if type(evidence) is not ProjectModuleRelationSemanticFacts:
            raise TypeError("Builder terminal requires semantic-fact evidence.")
        return evidence

    @property
    def snapshot_scope(self) -> ProjectIRSnapshotScope:
        return self.structural_stage.scope


type ProjectIRSingleRelationFragment = (
    ProjectIRConcreteSingleRelationFragment | ProjectIRNonConcreteSingleRelationFragment
)


def _reject_concrete_authored_join(
    semantic: ProjectModuleRelationSemanticFacts,
) -> None:
    definition = semantic.owner.definition
    if (
        type(definition) in {TableDef, QueryDef}
        and cast(TableDef | QueryDef, definition).join_clauses
    ):
        raise ValueError("Authored JOIN cannot construct a concrete relation fragment.")


def _require_exact_attribution_root(
    semantic: ProjectModuleRelationSemanticFacts,
    attribution: ProjectModuleAttributionFactSet,
) -> None:
    if type(semantic) is not ProjectModuleRelationSemanticFacts:
        raise TypeError("Project IR builder requires exact semantic facts.")
    if type(attribution) is not ProjectModuleAttributionFactSet:
        raise TypeError("Project IR builder requires exact attribution authority.")
    matches = attribution._authority.semantic_facts.find_owner(semantic.owner)
    if len(matches) != 1 or matches[0] is not semantic:
        raise ValueError("Project IR builder requires one exact semantic root.")


def _relation_anchor(
    semantic: ProjectModuleRelationSemanticFacts,
) -> ProjectIRRelationAnchor:
    return ProjectIRRelationAnchor(identity=_declaration_identity(semantic.owner))


def _final_row_shape(
    semantic: ProjectModuleRelationSemanticFacts,
    attribution: ProjectModuleAttributionFactSet,
    relation: ProjectIRRelationAnchor,
) -> ProjectIRRowShape:
    schema = semantic.state.schema
    if (
        semantic.state.status is not ProjectRelationRowSchemaStatus.CONCRETE
        or schema is None
    ):
        raise ValueError("Final Project IR row shape requires concrete semantics.")
    semantic_fields = tuple(schema.fields.values())
    if semantic.owner.identity.declaration_kind is ProjectSymbolKind.SOURCE:
        identities = tuple(
            origin.source_field
            for origin in attribution.source_field_origins
            if origin.source_field.owner == relation.identity
        )
    else:
        outputs = attribution.find_relation_output_fields(relation.identity)
        if any(
            type(output) is not ProjectModuleRelationOutputFieldAttribution
            or output.relation is not semantic
            for output in outputs
        ):
            raise ValueError("Final output attribution must reuse semantic authority.")
        identities = tuple(output.identity for output in outputs)
    if len(identities) != len(semantic_fields):
        raise ValueError("Final row identity authority must be complete.")
    return ProjectIRRowShape(
        relation=relation,
        evidence=semantic,
        fields=tuple(
            ProjectIRRowField(
                anchor=ProjectIRFieldAnchor(identity=identity),
                evidence=semantic_field,
            )
            for identity, semantic_field in zip(
                identities,
                semantic_fields,
                strict=True,
            )
        ),
    )


def _stage_row_shape(
    semantic: ProjectModuleRelationSemanticFacts,
    relation: ProjectIRRelationAnchor,
    kind: ProjectIRStageRowCheckpointKind,
) -> ProjectIRStageRowShape:
    checkpoint = ProjectIRStageRowCheckpoint(
        relation=relation,
        evidence=semantic,
        kind=kind,
    )
    schema = checkpoint.state.schema
    if (
        checkpoint.state.status is not ProjectRelationRowSchemaStatus.CONCRETE
        or schema is None
    ):
        raise ValueError("Canonical operator requires a concrete row checkpoint.")
    return ProjectIRStageRowShape(
        checkpoint=checkpoint,
        fields=tuple(
            ProjectIRStageRowField(
                checkpoint=checkpoint,
                field_position=position,
                evidence=semantic_field,
            )
            for position, semantic_field in enumerate(schema.fields.values())
        ),
    )


def _row_shape_for_operator(
    semantic: ProjectModuleRelationSemanticFacts,
    kind: ProjectIRLogicalOperatorKind,
    final_shape: ProjectIRRowShape,
    stage_shapes: dict[ProjectIRStageRowCheckpointKind, ProjectIRStageRowShape],
) -> ProjectIRCurrentRowShape:
    if semantic.owner.identity.declaration_kind is ProjectSymbolKind.SOURCE:
        return final_shape
    checkpoint_kind = {
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
    }.get(kind)
    if checkpoint_kind is None:
        return final_shape
    shape = stage_shapes.get(checkpoint_kind)
    if shape is None:
        shape = _stage_row_shape(semantic, final_shape.relation, checkpoint_kind)
        stage_shapes[checkpoint_kind] = shape
    return shape


def _unknown_effect(output: ProjectIRCurrentOutput) -> ProjectIREffectEvidence:
    return ProjectIREffectEvidence(
        output=output,
        determinism=ProjectIRDeterminismEvidence.UNKNOWN,
        error_behavior=ProjectIRErrorBehaviorEvidence.UNKNOWN,
        side_effects=ProjectIRSideEffectEvidence.UNKNOWN,
        evaluation_count=ProjectIREvaluationCountEvidence.UNKNOWN,
    )


def _row_properties(
    kind: ProjectIRLogicalOperatorKind,
    output: ProjectIRRelationRowOutput,
    semantic: ProjectModuleRelationSemanticFacts,
    previous: dict[ProjectIRProvidedPropertySlot, ProjectIRProvidedProperty],
) -> dict[ProjectIRProvidedPropertySlot, ProjectIRProvidedProperty]:
    properties: dict[ProjectIRProvidedPropertySlot, ProjectIRProvidedProperty] = {
        ProjectIRProvidedPropertySlot.OUTPUT_SHAPE: ProjectIRProvidedOutputShape(
            output=output
        ),
        ProjectIRProvidedPropertySlot.MULTIPLICITY: (
            ProjectIRProvidedBagMultiplicity(output=output)
        ),
        ProjectIRProvidedPropertySlot.FREE_BINDINGS: (
            ProjectIRProvidedClosedBindings(output=output)
        ),
    }
    preserved = project_ir_preserved_property_slots(kind)
    grain = ProjectIRProvidedPropertySlot.LOCAL_GRAIN_EVIDENCE
    if (
        kind is ProjectIRLogicalOperatorKind.GROUP_AGGREGATE
        and semantic.group_key_occurrences
    ) or (grain in preserved and grain in previous):
        properties[grain] = ProjectIRProvidedLocalGrainEvidence(
            output=output,
            evidence=semantic,
        )
    ordering = ProjectIRProvidedPropertySlot.RELATION_RESULT_ORDERING
    if kind is ProjectIRLogicalOperatorKind.RELATION_ORDERING or (
        ordering in preserved and ordering in previous
    ):
        properties[ordering] = ProjectIRProvidedRelationOrdering(
            output=output,
            evidence=semantic,
        )
    cardinality = ProjectIRProvidedPropertySlot.CARDINALITY_BOUNDS
    if kind is ProjectIRLogicalOperatorKind.LIMIT or (
        cardinality in preserved and cardinality in previous
    ):
        properties[cardinality] = ProjectIRProvidedCardinalityUpperBound(
            output=output,
            evidence=semantic,
        )
    return properties


def _property_transfer(
    operator: ProjectIRLogicalOperatorOccurrence,
    output_property: ProjectIRProvidedProperty,
    previous: dict[ProjectIRProvidedPropertySlot, ProjectIRProvidedProperty],
) -> ProjectIRPropertyTransfer:
    slot = output_property.property_slot
    if slot in project_ir_established_property_slots(operator.kind):
        return ProjectIREstablishedPropertyTransfer(
            operator=operator,
            output_property=output_property,
        )
    if slot in project_ir_preserved_property_slots(operator.kind):
        input_property = previous.get(slot)
        if input_property is None:
            raise ValueError("Preserved property requires exact predecessor authority.")
        return ProjectIRPreservedPropertyTransfer(
            operator=operator,
            input_property=input_property,
            output_property=output_property,
        )
    raise ValueError("Canonical builder cannot prove the supplied property.")


def _construction_state(
    semantic: ProjectModuleRelationSemanticFacts,
) -> ProjectIRRelationConstructionState:
    if _semantic_facts_have_ambiguity(semantic):
        return ProjectIRRelationConstructionState.AMBIGUOUS
    return {
        ProjectRelationRowSchemaStatus.UNKNOWN: ProjectIRRelationConstructionState.UNKNOWN,
        ProjectRelationRowSchemaStatus.DEFERRED: ProjectIRRelationConstructionState.DEFERRED,
        ProjectRelationRowSchemaStatus.BLOCKED: ProjectIRRelationConstructionState.BLOCKED,
    }[semantic.state.status]


def _build_non_concrete_fragment(
    semantic: ProjectModuleRelationSemanticFacts,
    attribution: ProjectModuleAttributionFactSet,
    allocation: ProjectIRAllocationState,
) -> ProjectIRNonConcreteSingleRelationFragment:
    subject = ProjectIRNonConcreteRelationSubject(
        anchor=_relation_anchor(semantic),
        state=_construction_state(semantic),
        evidence=semantic,
    )
    structural = ProjectIRStructuralStage(
        scope=allocation.scope,
        subjects=(subject,),
    )
    property_stage = ProjectIRPropertyStage(
        structural=structural,
        estimates=ProjectIREstimateBoundary(scope=allocation.scope),
    )
    logical = ProjectIRLogicalOperatorStage(property_stage=property_stage)
    return ProjectIRNonConcreteSingleRelationFragment(
        subject=subject,
        attribution=attribution,
        starting_allocation=allocation,
        ending_allocation=allocation,
        structural_stage=structural,
        property_stage=property_stage,
        logical_stage=logical,
    )


def build_project_ir_single_relation_fragment(
    *,
    semantic: ProjectModuleRelationSemanticFacts,
    attribution: ProjectModuleAttributionFactSet,
    allocation: ProjectIRAllocationState,
) -> ProjectIRSingleRelationFragment:
    """Build exactly one canonical relation fragment from existing authority."""

    _require_exact_attribution_root(semantic, attribution)
    if type(allocation) is not ProjectIRAllocationState:
        raise TypeError("Project IR builder requires exact allocation state.")
    if semantic.state.status is ProjectRelationRowSchemaStatus.CONCRETE:
        _reject_concrete_authored_join(semantic)
    if semantic.state.status is not ProjectRelationRowSchemaStatus.CONCRETE:
        return _build_non_concrete_fragment(semantic, attribution, allocation)

    relation = _relation_anchor(semantic)
    final_shape = _final_row_shape(semantic, attribution, relation)
    kinds = _expected_operator_kinds(semantic)
    nodes = tuple(
        ProjectIRPlanNodeOccurrence(
            ref=ProjectIRPlanNodeRef(
                scope=allocation.scope,
                position=allocation.next_plan_node_position + position,
            ),
            anchor=relation,
        )
        for position in range(len(kinds))
    )
    operators = tuple(
        ProjectIRLogicalOperatorOccurrence(
            node=node,
            kind=kind,
            evidence=semantic,
        )
        for node, kind in zip(nodes, kinds, strict=True)
    )

    next_output = allocation.next_output_value_position
    occurrences: list[ProjectIROutputValueOccurrence] = []
    output_models: list[ProjectIRCurrentOutput] = []
    outputs_by_operator: list[tuple[ProjectIRCurrentOutput, ...]] = []
    row_outputs: list[ProjectIRRelationRowOutput] = []
    final_scalars: list[ProjectIRScalarFieldOutput] = []
    window_facts_by_output: dict[int, ProjectModuleWindowOutputFact] = {}
    stage_shapes: dict[ProjectIRStageRowCheckpointKind, ProjectIRStageRowShape] = {}

    for operator in operators:
        row_shape = _row_shape_for_operator(
            semantic,
            operator.kind,
            final_shape,
            stage_shapes,
        )
        row_occurrence = ProjectIROutputValueOccurrence(
            ref=ProjectIROutputValueRef(
                scope=allocation.scope,
                position=next_output,
            ),
            producer=operator.node,
            anchor=relation,
        )
        next_output += 1
        row_output = ProjectIRRelationRowOutput(
            occurrence=row_occurrence,
            row_shape=row_shape,
        )
        owned: list[ProjectIRCurrentOutput] = [row_output]
        occurrences.append(row_occurrence)
        output_models.append(row_output)
        row_outputs.append(row_output)

        if operator.kind is ProjectIRLogicalOperatorKind.WINDOW_EVALUATION:
            if type(row_shape) is not ProjectIRStageRowShape:
                raise ValueError("Window operator requires its exact stage row shape.")
            for window_fact in semantic.window_outputs:
                field_position = window_fact.selected_output_ordinal
                if field_position >= len(row_shape.fields):
                    raise ValueError("Window stage field authority must be complete.")
                stage_field = row_shape.fields[field_position]
                scalar_occurrence = ProjectIROutputValueOccurrence(
                    ref=ProjectIROutputValueRef(
                        scope=allocation.scope,
                        position=next_output,
                    ),
                    producer=operator.node,
                    anchor=ProjectIRStageFieldAnchor(
                        producer=operator.node,
                        field_position=field_position,
                    ),
                )
                next_output += 1
                scalar_output = ProjectIRStageScalarFieldOutput(
                    occurrence=scalar_occurrence,
                    row_shape=row_shape,
                    field=stage_field,
                )
                occurrences.append(scalar_occurrence)
                output_models.append(scalar_output)
                owned.append(scalar_output)
                window_facts_by_output[scalar_occurrence.ref.position] = window_fact

        if operator.kind is ProjectIRLogicalOperatorKind.FINAL_PROJECTION:
            for final_field in final_shape.fields:
                scalar_occurrence = ProjectIROutputValueOccurrence(
                    ref=ProjectIROutputValueRef(
                        scope=allocation.scope,
                        position=next_output,
                    ),
                    producer=operator.node,
                    anchor=final_field.anchor,
                )
                next_output += 1
                scalar_output = ProjectIRScalarFieldOutput(
                    occurrence=scalar_occurrence,
                    row_shape=final_shape,
                    field=final_field,
                )
                occurrences.append(scalar_occurrence)
                output_models.append(scalar_output)
                owned.append(scalar_output)
                final_scalars.append(scalar_output)
        outputs_by_operator.append(tuple(owned))

    slots = tuple(
        ProjectIRInputSlotOccurrence(
            ref=ProjectIRInputSlotRef(
                scope=allocation.scope,
                position=allocation.next_input_slot_position + position,
            ),
            consumer=node,
            input_ordinal=0,
        )
        for position, node in enumerate(nodes[1:])
    )
    flow_uses = tuple(
        ProjectIROperatorFlowUseOccurrence(
            ref=ProjectIRUseRef(
                scope=allocation.scope,
                position=allocation.next_use_position + position,
            ),
            output=row_output.occurrence,
            slot=slot,
        )
        for position, (row_output, slot) in enumerate(
            zip(row_outputs, slots, strict=False)
        )
    )
    subject = ProjectIRConcreteRelationSubject(
        anchor=relation,
        evidence=semantic,
        root=nodes[-1],
    )
    structural = ProjectIRStructuralStage(
        scope=allocation.scope,
        nodes=nodes,
        outputs=tuple(occurrences),
        input_slots=slots,
        uses=flow_uses,
        subjects=(subject,),
    )

    provided: list[ProjectIRProvidedProperty] = []
    transfers: list[ProjectIRPropertyTransfer] = []
    effects: list[ProjectIREffectEvidence] = []
    previous_row_properties: dict[
        ProjectIRProvidedPropertySlot,
        ProjectIRProvidedProperty,
    ] = {}
    for operator, owned_outputs in zip(operators, outputs_by_operator, strict=True):
        row_output = owned_outputs[0]
        if type(row_output) is not ProjectIRRelationRowOutput:
            raise AssertionError("operator row output lost first position")
        current_row_properties = _row_properties(
            operator.kind,
            row_output,
            semantic,
            previous_row_properties,
        )
        for slot in ProjectIRProvidedPropertySlot:
            property_ = current_row_properties.get(slot)
            if property_ is None:
                continue
            provided.append(property_)
            transfers.append(
                _property_transfer(operator, property_, previous_row_properties)
            )
        effects.append(_unknown_effect(row_output))

        for scalar_output in owned_outputs[1:]:
            shape_property = ProjectIRProvidedOutputShape(output=scalar_output)
            provided.append(shape_property)
            transfers.append(
                _property_transfer(operator, shape_property, previous_row_properties)
            )
            if type(scalar_output) is ProjectIRStageScalarFieldOutput:
                window_fact = window_facts_by_output.get(
                    scalar_output.occurrence.ref.position
                )
                if window_fact is None:
                    raise ValueError("Stage scalar requires exact window authority.")
                policy = ProjectIRProvidedEvaluationPolicy(
                    output=scalar_output,
                    evidence=window_fact,
                )
                provided.append(policy)
                transfers.append(
                    _property_transfer(operator, policy, previous_row_properties)
                )
            effects.append(_unknown_effect(scalar_output))
        previous_row_properties = current_row_properties

    property_stage = ProjectIRPropertyStage(
        structural=structural,
        estimates=ProjectIREstimateBoundary(scope=allocation.scope),
        outputs=tuple(output_models),
        provided=tuple(provided),
        effects=tuple(effects),
    )
    logical = ProjectIRLogicalOperatorStage(
        property_stage=property_stage,
        operators=operators,
        transfers=tuple(transfers),
    )
    ending_allocation = ProjectIRAllocationState(
        scope=allocation.scope,
        next_plan_node_position=allocation.next_plan_node_position + len(nodes),
        next_output_value_position=next_output,
        next_input_slot_position=allocation.next_input_slot_position + len(slots),
        next_use_position=allocation.next_use_position + len(flow_uses),
    )
    return ProjectIRConcreteSingleRelationFragment(
        subject=subject,
        attribution=attribution,
        starting_allocation=allocation,
        ending_allocation=ending_allocation,
        structural_stage=structural,
        property_stage=property_stage,
        logical_stage=logical,
        root=nodes[-1],
        root_relation_output=row_outputs[-1],
        final_scalar_outputs=tuple(final_scalars),
    )
