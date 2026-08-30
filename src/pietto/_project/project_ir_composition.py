"""Canonical composition of Slice 5 relation fragments into one Project DAG."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from pietto._project.model import ProjectSymbolKind
from pietto._project.module_attribution import (
    ProjectDeclarationOccurrenceIdentity,
    ProjectModuleAttributionFactSet,
    ProjectModuleDependencyKind,
    ProjectModuleReferenceOccurrenceIdentity,
    ProjectModuleReferenceRole,
)
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleFactOccurrenceRole,
    ProjectModuleSemanticFactSet,
)
from pietto._project.project_ir import (
    ProjectIRInputSlotOccurrence,
    ProjectIRInputSlotRef,
    ProjectIRPlanNodeOccurrence,
    ProjectIRResolvedRelationAnchor,
    ProjectIRStructuralStage,
    ProjectIRUseOccurrence,
    ProjectIRUseRef,
    _declaration_identity,
)
from pietto._project.project_ir_construction import (
    ProjectIRAllocationState,
    ProjectIRConcreteSingleRelationFragment,
    ProjectIRNonConcreteSingleRelationFragment,
    ProjectIRSingleRelationFragment,
    build_project_ir_single_relation_fragment,
)
from pietto._project.project_ir_operators import (
    ProjectIRLogicalOperatorKind,
    ProjectIRRowShapeCompatibility,
    ProjectIRRowShapeCompatibilityStatus,
)
from pietto._project.project_ir_properties import (
    ProjectIRProvidedOutputShape,
    ProjectIRRelationRowOutput,
    ProjectIRRequiredRowShape,
    ProjectIRRowShape,
    ProjectIRStageRowCheckpointKind,
    ProjectIRStageRowShape,
)

__all__: tuple[str, ...] = ()


def _relation_input_node(
    fragment: ProjectIRConcreteSingleRelationFragment,
) -> ProjectIRPlanNodeOccurrence:
    matches = tuple(
        operator.node
        for operator in fragment.logical_stage.operators
        if operator.kind is ProjectIRLogicalOperatorKind.RELATION_INPUT
    )
    if len(matches) != 1:
        raise ValueError("Concrete consumer requires one Relation Input node.")
    return matches[0]


def _relation_input_output(
    fragment: ProjectIRConcreteSingleRelationFragment,
) -> ProjectIRRelationRowOutput:
    input_node = _relation_input_node(fragment)
    matches = tuple(
        output
        for output in fragment.property_stage.outputs
        if type(output) is ProjectIRRelationRowOutput
        and output.occurrence.producer is input_node
    )
    if len(matches) != 1:
        raise ValueError("Concrete consumer requires one Relation Input row output.")
    return matches[0]


def _root_shape_property(
    fragment: ProjectIRConcreteSingleRelationFragment,
) -> ProjectIRProvidedOutputShape:
    matches = tuple(
        property_
        for property_ in fragment.property_stage.provided
        if type(property_) is ProjectIRProvidedOutputShape
        and property_.output is fragment.root_relation_output
    )
    if len(matches) != 1:
        raise ValueError("Producer root requires one exact provided row shape.")
    return matches[0]


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRCrossRelationEdge:
    """One exact resolved relation-row use across two Slice 5 fragments."""

    producer: ProjectIRConcreteSingleRelationFragment
    consumer: ProjectIRConcreteSingleRelationFragment
    authority: ProjectIRResolvedRelationAnchor
    input_slot: ProjectIRInputSlotOccurrence
    use: ProjectIRUseOccurrence
    provided_row_shape: ProjectIRProvidedOutputShape
    required_row_shape: ProjectIRRequiredRowShape
    compatibility: ProjectIRRowShapeCompatibility

    def __post_init__(self) -> None:
        if (
            type(self.producer) is not ProjectIRConcreteSingleRelationFragment
            or type(self.consumer) is not ProjectIRConcreteSingleRelationFragment
        ):
            raise TypeError("Cross edge requires exact concrete fragments.")
        if type(self.authority) is not ProjectIRResolvedRelationAnchor:
            raise TypeError("Cross edge requires exact resolved relation authority.")
        if type(self.input_slot) is not ProjectIRInputSlotOccurrence:
            raise TypeError("Cross edge requires an exact external input slot.")
        if type(self.use) is not ProjectIRUseOccurrence:
            raise TypeError("Cross edge requires one exact semantic use.")
        input_node = _relation_input_node(self.consumer)
        if (
            self.authority.resolution is not self.consumer.semantic_facts.resolution
            or self.authority.target != self.producer.subject.anchor.identity
            or self.authority.reference.owner != self.consumer.subject.anchor.identity
            or self.input_slot.consumer is not input_node
            or self.input_slot.input_ordinal != 0
            or self.use.output is not self.producer.root_relation_output.occurrence
            or self.use.slot is not self.input_slot
            or self.use.role is not ProjectModuleFactOccurrenceRole.RELATION_INPUT
            or self.use.source_order != 0
            or self.use.anchor is not self.authority
        ):
            raise ValueError("Cross edge must retain exact resolved endpoints.")
        if (
            type(self.provided_row_shape) is not ProjectIRProvidedOutputShape
            or self.provided_row_shape is not _root_shape_property(self.producer)
            or type(self.required_row_shape) is not ProjectIRRequiredRowShape
            or self.required_row_shape.input_slot is not self.input_slot
            or self.required_row_shape.authority is not self.authority
            or self.required_row_shape.row_shape
            is not self.producer.root_relation_output.row_shape
            or type(self.compatibility) is not ProjectIRRowShapeCompatibility
            or self.compatibility.provided is not self.provided_row_shape
            or self.compatibility.required is not self.required_row_shape
            or self.compatibility.status
            is not ProjectIRRowShapeCompatibilityStatus.SATISFIED
        ):
            raise ValueError(
                "Cross edge must retain exact row compatibility authority."
            )
        input_output = _relation_input_output(self.consumer)
        input_shape = input_output.row_shape
        if (
            type(input_shape) is not ProjectIRStageRowShape
            or input_shape.checkpoint.kind is not ProjectIRStageRowCheckpointKind.INPUT
            or input_shape.checkpoint.state is not self.producer.semantic_facts.state
            or self.consumer.semantic_facts.input_state
            is not self.producer.semantic_facts.state
        ):
            raise ValueError("Consumer INPUT must reuse the producer final row state.")


def _same_objects(actual: tuple[object, ...], expected: tuple[object, ...]) -> bool:
    return len(actual) == len(expected) and all(
        item is expected_item
        for item, expected_item in zip(actual, expected, strict=True)
    )


def _require_acyclic(structural: ProjectIRStructuralStage) -> None:
    indegree = {node: 0 for node in structural.nodes}
    successors: dict[ProjectIRPlanNodeOccurrence, list[ProjectIRPlanNodeOccurrence]] = {
        node: [] for node in structural.nodes
    }
    for use in structural.uses:
        producer = use.output.producer
        consumer = use.slot.consumer
        successors[producer].append(consumer)
        indegree[consumer] += 1
    ready = deque(node for node in structural.nodes if indegree[node] == 0)
    visited = 0
    while ready:
        node = ready.popleft()
        visited += 1
        for consumer in successors[node]:
            indegree[consumer] -= 1
            if indegree[consumer] == 0:
                ready.append(consumer)
    if visited != len(structural.nodes):
        raise ValueError("Project IR actual-use graph must be acyclic.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRProjectPlan:
    """Complete canonical Project plan with concrete and non-concrete fragments."""

    semantic_facts: ProjectModuleSemanticFactSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    attribution: ProjectModuleAttributionFactSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    starting_allocation: ProjectIRAllocationState
    ending_allocation: ProjectIRAllocationState
    fragments: tuple[ProjectIRSingleRelationFragment, ...]
    structural_stage: ProjectIRStructuralStage
    cross_relation_edges: tuple[ProjectIRCrossRelationEdge, ...] = ()

    def __post_init__(self) -> None:
        if type(self.semantic_facts) is not ProjectModuleSemanticFactSet:
            raise TypeError("Project plan requires exact semantic-fact authority.")
        if (
            type(self.attribution) is not ProjectModuleAttributionFactSet
            or self.attribution._authority.semantic_facts is not self.semantic_facts
        ):
            raise ValueError("Project plan requires exact attribution root authority.")
        if (
            type(self.starting_allocation) is not ProjectIRAllocationState
            or type(self.ending_allocation) is not ProjectIRAllocationState
            or self.starting_allocation.scope is not self.ending_allocation.scope
            or self.structural_stage.scope is not self.starting_allocation.scope
        ):
            raise ValueError("Project plan requires one exact allocation scope.")
        if type(self.fragments) is not tuple or any(
            type(fragment)
            not in {
                ProjectIRConcreteSingleRelationFragment,
                ProjectIRNonConcreteSingleRelationFragment,
            }
            for fragment in self.fragments
        ):
            raise TypeError("Project plan requires exact Slice 5 fragments.")
        canonical_facts = tuple(
            fact
            for environment in self.semantic_facts.environments
            for fact in environment.relation_facts
        )
        if len(self.fragments) != len(canonical_facts) or any(
            fragment.semantic_facts is not fact
            for fragment, fact in zip(self.fragments, canonical_facts, strict=True)
        ):
            raise ValueError("Project fragments must retain canonical semantic order.")
        if type(self.cross_relation_edges) is not tuple or any(
            type(edge) is not ProjectIRCrossRelationEdge
            for edge in self.cross_relation_edges
        ):
            raise TypeError("Project plan requires exact cross-relation edges.")

        expected_nodes = tuple(
            node
            for fragment in self.fragments
            for node in fragment.structural_stage.nodes
        )
        expected_outputs = tuple(
            output
            for fragment in self.fragments
            for output in fragment.structural_stage.outputs
        )
        expected_slots = (
            *(
                slot
                for fragment in self.fragments
                for slot in fragment.structural_stage.input_slots
            ),
            *(edge.input_slot for edge in self.cross_relation_edges),
        )
        expected_uses = (
            *(
                use
                for fragment in self.fragments
                for use in fragment.structural_stage.uses
            ),
            *(edge.use for edge in self.cross_relation_edges),
        )
        expected_subjects = tuple(
            subject
            for fragment in self.fragments
            for subject in fragment.structural_stage.subjects
        )
        if not (
            _same_objects(self.structural_stage.nodes, expected_nodes)
            and _same_objects(self.structural_stage.outputs, expected_outputs)
            and _same_objects(self.structural_stage.input_slots, expected_slots)
            and _same_objects(self.structural_stage.uses, expected_uses)
            and _same_objects(self.structural_stage.subjects, expected_subjects)
        ):
            raise ValueError(
                "Project structure must reuse exact fragment and edge objects."
            )
        expected_consumers = tuple(
            fragment
            for fragment in self.fragments
            if type(fragment) is ProjectIRConcreteSingleRelationFragment
            and fragment.semantic_facts.owner.identity.declaration_kind
            in {ProjectSymbolKind.TABLE, ProjectSymbolKind.QUERY}
        )
        if len(expected_consumers) != len(self.cross_relation_edges) or any(
            edge.consumer is not consumer
            for edge, consumer in zip(
                self.cross_relation_edges,
                expected_consumers,
                strict=True,
            )
        ):
            raise ValueError(
                "Cross edges must retain canonical concrete-consumer order."
            )
        _require_acyclic(self.structural_stage)

    @property
    def concrete_fragments(
        self,
    ) -> tuple[ProjectIRConcreteSingleRelationFragment, ...]:
        return tuple(
            fragment
            for fragment in self.fragments
            if type(fragment) is ProjectIRConcreteSingleRelationFragment
        )

    @property
    def non_concrete_fragments(
        self,
    ) -> tuple[ProjectIRNonConcreteSingleRelationFragment, ...]:
        return tuple(
            fragment
            for fragment in self.fragments
            if type(fragment) is ProjectIRNonConcreteSingleRelationFragment
        )


def _exact_relation_authority(
    consumer: ProjectIRConcreteSingleRelationFragment,
    attribution: ProjectModuleAttributionFactSet,
) -> ProjectIRResolvedRelationAnchor:
    semantic = consumer.semantic_facts
    resolution = semantic.resolution
    if resolution is None:
        raise ValueError("Concrete derived consumer requires exact resolution.")
    reference = ProjectModuleReferenceOccurrenceIdentity(
        owner=consumer.subject.anchor.identity,
        role=ProjectModuleReferenceRole.RELATION_FROM,
        member_position=0,
    )
    target = _declaration_identity(resolution.target_symbol.target_occurrence)
    dependencies = attribution.find_reference_dependencies(reference)
    matches = tuple(
        dependency
        for dependency in dependencies
        if dependency.kind is ProjectModuleDependencyKind.RELATION_REFERENCE
        and dependency.target_declaration == target
    )
    if len(dependencies) != 1 or len(matches) != 1:
        raise ValueError("Concrete consumer requires one exact relation dependency.")
    return ProjectIRResolvedRelationAnchor(
        resolution=resolution,
        dependency=matches[0],
    )


def build_project_ir_project_plan(
    *,
    semantic_facts: ProjectModuleSemanticFactSet,
    attribution: ProjectModuleAttributionFactSet,
    allocation: ProjectIRAllocationState,
) -> ProjectIRProjectPlan:
    """Compose all retained semantic subjects into one canonical Project DAG."""

    if type(semantic_facts) is not ProjectModuleSemanticFactSet:
        raise TypeError("Project composition requires exact semantic facts.")
    if (
        type(attribution) is not ProjectModuleAttributionFactSet
        or attribution._authority.semantic_facts is not semantic_facts
    ):
        raise ValueError("Project composition requires exact attribution authority.")
    if type(allocation) is not ProjectIRAllocationState:
        raise TypeError("Project composition requires exact allocation state.")

    canonical_facts = tuple(
        fact
        for environment in semantic_facts.environments
        for fact in environment.relation_facts
    )
    fragments: list[ProjectIRSingleRelationFragment] = []
    current_allocation = allocation
    for semantic in canonical_facts:
        fragment = build_project_ir_single_relation_fragment(
            semantic=semantic,
            attribution=attribution,
            allocation=current_allocation,
        )
        fragments.append(fragment)
        current_allocation = fragment.ending_allocation
    fragment_tuple = tuple(fragments)
    fragments_by_identity: dict[
        ProjectDeclarationOccurrenceIdentity,
        ProjectIRSingleRelationFragment,
    ] = {}
    for fragment in fragment_tuple:
        identity = fragment.subject.anchor.identity
        if identity in fragments_by_identity:
            raise ValueError("Project relation subjects must be occurrence-unique.")
        fragments_by_identity[identity] = fragment

    edges: list[ProjectIRCrossRelationEdge] = []
    for fragment in fragment_tuple:
        if type(fragment) is not ProjectIRConcreteSingleRelationFragment or (
            fragment.semantic_facts.owner.identity.declaration_kind
            not in {ProjectSymbolKind.TABLE, ProjectSymbolKind.QUERY}
        ):
            continue
        authority = _exact_relation_authority(fragment, attribution)
        producer = fragments_by_identity.get(authority.target)
        if type(producer) is not ProjectIRConcreteSingleRelationFragment:
            raise ValueError(
                "Concrete consumer requires one concrete producer fragment."
            )
        input_node = _relation_input_node(fragment)
        edge_position = len(edges)
        slot = ProjectIRInputSlotOccurrence(
            ref=ProjectIRInputSlotRef(
                scope=allocation.scope,
                position=current_allocation.next_input_slot_position + edge_position,
            ),
            consumer=input_node,
            input_ordinal=0,
        )
        use = ProjectIRUseOccurrence(
            ref=ProjectIRUseRef(
                scope=allocation.scope,
                position=current_allocation.next_use_position + edge_position,
            ),
            output=producer.root_relation_output.occurrence,
            slot=slot,
            role=ProjectModuleFactOccurrenceRole.RELATION_INPUT,
            source_order=0,
            anchor=authority,
        )
        producer_shape = producer.root_relation_output.row_shape
        if type(producer_shape) is not ProjectIRRowShape:
            raise ValueError(
                "Cross relation producer requires final semantic row shape."
            )
        provided = _root_shape_property(producer)
        required = ProjectIRRequiredRowShape(
            input_slot=slot,
            row_shape=producer_shape,
            authority=authority,
        )
        compatibility = ProjectIRRowShapeCompatibility(
            provided=provided,
            required=required,
        )
        edges.append(
            ProjectIRCrossRelationEdge(
                producer=producer,
                consumer=fragment,
                authority=authority,
                input_slot=slot,
                use=use,
                provided_row_shape=provided,
                required_row_shape=required,
                compatibility=compatibility,
            )
        )

    edge_tuple = tuple(edges)
    ending_allocation = ProjectIRAllocationState(
        scope=allocation.scope,
        next_plan_node_position=current_allocation.next_plan_node_position,
        next_output_value_position=current_allocation.next_output_value_position,
        next_input_slot_position=(
            current_allocation.next_input_slot_position + len(edge_tuple)
        ),
        next_use_position=current_allocation.next_use_position + len(edge_tuple),
    )
    structural = ProjectIRStructuralStage(
        scope=allocation.scope,
        nodes=tuple(
            node
            for fragment in fragment_tuple
            for node in fragment.structural_stage.nodes
        ),
        outputs=tuple(
            output
            for fragment in fragment_tuple
            for output in fragment.structural_stage.outputs
        ),
        input_slots=(
            *(
                slot
                for fragment in fragment_tuple
                for slot in fragment.structural_stage.input_slots
            ),
            *(edge.input_slot for edge in edge_tuple),
        ),
        uses=(
            *(
                use
                for fragment in fragment_tuple
                for use in fragment.structural_stage.uses
            ),
            *(edge.use for edge in edge_tuple),
        ),
        subjects=tuple(
            subject
            for fragment in fragment_tuple
            for subject in fragment.structural_stage.subjects
        ),
    )
    return ProjectIRProjectPlan(
        semantic_facts=semantic_facts,
        attribution=attribution,
        starting_allocation=allocation,
        ending_allocation=ending_allocation,
        fragments=fragment_tuple,
        structural_stage=structural,
        cross_relation_edges=edge_tuple,
    )
