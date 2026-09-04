"""Exact aggregate and window evaluation contexts over a Project IR plan."""

from __future__ import annotations

from dataclasses import dataclass, field

from pietto._project.aggregate_grouped_clause_facts import (
    ProjectAggregateGroupedClauseReadiness,
    ProjectAggregateGroupedClauseReadinessStatus,
)
from pietto._project.let_scope_facts import ProjectRelationLetScopeFacts
from pietto._project.model import ProjectAggregateResultFact
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleRelationSemanticFacts,
    ProjectModuleWindowOutputFact,
)
from pietto._project.module_attribution import ProjectDeclarationOccurrenceIdentity
from pietto._project.project_ir import (
    ProjectIROperatorFlowUseOccurrence,
    ProjectIRPlanNodeOccurrence,
)
from pietto._project.project_ir_composition import ProjectIRProjectPlan
from pietto._project.project_ir_construction import (
    ProjectIRConcreteSingleRelationFragment,
)
from pietto._project.project_ir_operators import (
    ProjectIRLogicalOperatorKind,
    ProjectIRLogicalOperatorOccurrence,
)
from pietto._project.project_ir_properties import (
    ProjectIREffectEvidence,
    ProjectIRProvidedClosedBindings,
    ProjectIRProvidedEvaluationPolicy,
    ProjectIRRelationRowOutput,
    ProjectIRStageRowCheckpoint,
    ProjectIRStageRowCheckpointKind,
    ProjectIRStageRowShape,
    ProjectIRStageScalarFieldOutput,
)
from pietto._project.window_semantics import WindowResultProjectFact
from pietto.ast_nodes import GroupByItem
from pietto.semantic.window_semantics import (
    NamedWindowResolutionFailure,
    ResolvedNamedWindowNamespace,
)

__all__: tuple[str, ...] = ()


def _operator(
    fragment: ProjectIRConcreteSingleRelationFragment,
    kind: ProjectIRLogicalOperatorKind,
) -> ProjectIRLogicalOperatorOccurrence:
    matches = tuple(
        operator
        for operator in fragment.logical_stage.operators
        if operator.kind is kind
    )
    if len(matches) != 1:
        raise ValueError(f"Fragment requires one exact {kind.value} operator.")
    return matches[0]


def _incoming_flow(
    fragment: ProjectIRConcreteSingleRelationFragment,
    operator: ProjectIRLogicalOperatorOccurrence,
) -> ProjectIROperatorFlowUseOccurrence:
    matches = tuple(
        use
        for use in fragment.structural_stage.uses
        if type(use) is ProjectIROperatorFlowUseOccurrence
        and use.slot.consumer is operator.node
    )
    if len(matches) != 1:
        raise ValueError("Evaluation operator requires one exact incoming flow.")
    return matches[0]


def _row_output_for_occurrence(
    fragment: ProjectIRConcreteSingleRelationFragment,
    occurrence: object,
) -> ProjectIRRelationRowOutput:
    matches = tuple(
        output
        for output in fragment.property_stage.outputs
        if type(output) is ProjectIRRelationRowOutput
        and output.occurrence is occurrence
    )
    if len(matches) != 1:
        raise ValueError("Evaluation context requires one exact relation-row output.")
    return matches[0]


def _result_row_output(
    fragment: ProjectIRConcreteSingleRelationFragment,
    operator: ProjectIRLogicalOperatorOccurrence,
) -> ProjectIRRelationRowOutput:
    matches = tuple(
        output
        for output in fragment.property_stage.outputs
        if type(output) is ProjectIRRelationRowOutput
        and output.occurrence.producer is operator.node
    )
    if len(matches) != 1:
        raise ValueError("Evaluation operator requires one exact result row output.")
    return matches[0]


def _closed_bindings(
    fragment: ProjectIRConcreteSingleRelationFragment,
    output: ProjectIRRelationRowOutput,
) -> ProjectIRProvidedClosedBindings:
    matches = tuple(
        property_
        for property_ in fragment.property_stage.provided
        if type(property_) is ProjectIRProvidedClosedBindings
        and property_.output is output
    )
    if len(matches) != 1:
        raise ValueError("Evaluation row requires one exact closed-binding property.")
    return matches[0]


def _effect(
    fragment: ProjectIRConcreteSingleRelationFragment,
    output: object,
) -> ProjectIREffectEvidence:
    matches = tuple(
        effect for effect in fragment.property_stage.effects if effect.output is output
    )
    if len(matches) != 1:
        raise ValueError("Evaluation output requires one exact effect object.")
    return matches[0]


class ProjectIRGroupedEvaluationContext:
    """Nominal authority seam shared by historical and additive group stages."""

    __slots__ = ()

    @property
    def grouped_operator_node(self) -> ProjectIRPlanNodeOccurrence:
        raise NotImplementedError

    @property
    def grouped_owner(self) -> ProjectDeclarationOccurrenceIdentity:
        raise NotImplementedError

    @property
    def grouped_keys(self) -> tuple[object, ...]:
        raise NotImplementedError


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRAggregateEvaluationContext(ProjectIRGroupedEvaluationContext):
    """Exact semantic and row-stream authority for one group/aggregate stage."""

    fragment: ProjectIRConcreteSingleRelationFragment
    operator: ProjectIRLogicalOperatorOccurrence
    incoming_flow: ProjectIROperatorFlowUseOccurrence
    input_row_output: ProjectIRRelationRowOutput
    result_row_output: ProjectIRRelationRowOutput
    semantic_facts: ProjectModuleRelationSemanticFacts = field(
        repr=False,
        compare=False,
        hash=False,
    )
    readiness: ProjectAggregateGroupedClauseReadiness = field(
        repr=False,
        compare=False,
        hash=False,
    )
    group_keys: tuple[GroupByItem, ...]
    aggregate_results: tuple[ProjectAggregateResultFact, ...]
    let_scope: ProjectRelationLetScopeFacts = field(
        repr=False,
        compare=False,
        hash=False,
    )
    input_closed_bindings: ProjectIRProvidedClosedBindings
    result_closed_bindings: ProjectIRProvidedClosedBindings
    input_effect: ProjectIREffectEvidence
    result_effect: ProjectIREffectEvidence

    def __post_init__(self) -> None:
        if type(self.fragment) is not ProjectIRConcreteSingleRelationFragment:
            raise TypeError("Aggregate context requires one concrete fragment.")
        if (
            type(self.operator) is not ProjectIRLogicalOperatorOccurrence
            or self.operator
            is not _operator(
                self.fragment, ProjectIRLogicalOperatorKind.GROUP_AGGREGATE
            )
            or self.operator.evidence is not self.fragment.semantic_facts
        ):
            raise ValueError("Aggregate context requires the exact group operator.")
        if (
            type(self.incoming_flow) is not ProjectIROperatorFlowUseOccurrence
            or self.incoming_flow is not _incoming_flow(self.fragment, self.operator)
            or self.input_row_output
            is not _row_output_for_occurrence(
                self.fragment,
                self.incoming_flow.output,
            )
            or self.result_row_output
            is not _result_row_output(self.fragment, self.operator)
        ):
            raise ValueError("Aggregate context requires exact flow row authority.")
        if (
            self.semantic_facts is not self.fragment.semantic_facts
            or self.readiness
            is not self.semantic_facts.aggregate_grouped_clause_readiness
            or self.readiness.status
            is not ProjectAggregateGroupedClauseReadinessStatus.CONCRETE
            or self.group_keys is not self.semantic_facts.group_key_occurrences
            or self.aggregate_results is not self.semantic_facts.aggregate_result_facts
            or self.let_scope is not self.semantic_facts.let_scope_facts
        ):
            raise ValueError("Aggregate context requires exact semantic authority.")
        result_shape = self.result_row_output.row_shape
        if (
            type(result_shape) is not ProjectIRStageRowShape
            or result_shape.checkpoint.kind
            is not ProjectIRStageRowCheckpointKind.BASE_RESULT
            or result_shape.checkpoint.state
            is not self.semantic_facts.base_result_state
        ):
            raise ValueError("Aggregate result requires exact BASE_RESULT authority.")
        if (
            self.input_closed_bindings
            is not _closed_bindings(self.fragment, self.input_row_output)
            or self.result_closed_bindings
            is not _closed_bindings(self.fragment, self.result_row_output)
            or self.input_closed_bindings.bindings
            or self.result_closed_bindings.bindings
            or self.input_effect is not _effect(self.fragment, self.input_row_output)
            or self.result_effect is not _effect(self.fragment, self.result_row_output)
        ):
            raise ValueError("Aggregate context must retain closed effect authority.")

    @property
    def grouped_operator_node(self) -> ProjectIRPlanNodeOccurrence:
        return self.operator.node

    @property
    def grouped_owner(self) -> ProjectDeclarationOccurrenceIdentity:
        return self.operator.node.anchor.identity

    @property
    def grouped_keys(self) -> tuple[object, ...]:
        return self.group_keys


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRWindowOperatorEvaluationContext:
    """Exact stream and semantic-base authority for one window stage."""

    fragment: ProjectIRConcreteSingleRelationFragment
    operator: ProjectIRLogicalOperatorOccurrence
    incoming_flow: ProjectIROperatorFlowUseOccurrence
    stream_input_row_output: ProjectIRRelationRowOutput
    semantic_base_checkpoint: ProjectIRStageRowCheckpoint
    result_row_output: ProjectIRRelationRowOutput
    semantic_facts: ProjectModuleRelationSemanticFacts = field(
        repr=False,
        compare=False,
        hash=False,
    )
    let_scope: ProjectRelationLetScopeFacts = field(
        repr=False,
        compare=False,
        hash=False,
    )
    named_window_namespace: (
        ResolvedNamedWindowNamespace | NamedWindowResolutionFailure | None
    ) = field(repr=False, compare=False, hash=False)
    stream_closed_bindings: ProjectIRProvidedClosedBindings
    result_closed_bindings: ProjectIRProvidedClosedBindings
    stream_effect: ProjectIREffectEvidence
    result_effect: ProjectIREffectEvidence

    def __post_init__(self) -> None:
        if type(self.fragment) is not ProjectIRConcreteSingleRelationFragment:
            raise TypeError("Window context requires one concrete fragment.")
        if (
            type(self.operator) is not ProjectIRLogicalOperatorOccurrence
            or self.operator
            is not _operator(
                self.fragment, ProjectIRLogicalOperatorKind.WINDOW_EVALUATION
            )
            or self.operator.evidence is not self.fragment.semantic_facts
        ):
            raise ValueError("Window context requires the exact window operator.")
        if (
            type(self.incoming_flow) is not ProjectIROperatorFlowUseOccurrence
            or self.incoming_flow is not _incoming_flow(self.fragment, self.operator)
            or self.stream_input_row_output
            is not _row_output_for_occurrence(
                self.fragment,
                self.incoming_flow.output,
            )
            or self.result_row_output
            is not _result_row_output(self.fragment, self.operator)
        ):
            raise ValueError("Window context requires exact stream row authority.")
        if (
            self.semantic_facts is not self.fragment.semantic_facts
            or type(self.semantic_base_checkpoint) is not ProjectIRStageRowCheckpoint
            or self.semantic_base_checkpoint.evidence is not self.semantic_facts
            or self.semantic_base_checkpoint.kind
            is not ProjectIRStageRowCheckpointKind.BASE_RESULT
            or self.semantic_base_checkpoint.state
            is not self.semantic_facts.base_result_state
            or self.let_scope is not self.semantic_facts.let_scope_facts
            or self.named_window_namespace
            is not self.semantic_facts.named_window_namespace
        ):
            raise ValueError("Window context requires exact semantic-base authority.")
        stream_shape = self.stream_input_row_output.row_shape
        result_shape = self.result_row_output.row_shape
        if (
            type(stream_shape) is not ProjectIRStageRowShape
            or type(result_shape) is not ProjectIRStageRowShape
            or result_shape.checkpoint.kind is not ProjectIRStageRowCheckpointKind.FINAL
        ):
            raise ValueError("Window context requires exact stage row shapes.")
        if (
            self.stream_closed_bindings
            is not _closed_bindings(self.fragment, self.stream_input_row_output)
            or self.result_closed_bindings
            is not _closed_bindings(self.fragment, self.result_row_output)
            or self.stream_closed_bindings.bindings
            or self.result_closed_bindings.bindings
            or self.stream_effect
            is not _effect(self.fragment, self.stream_input_row_output)
            or self.result_effect is not _effect(self.fragment, self.result_row_output)
        ):
            raise ValueError("Window context must retain closed effect authority.")

    @property
    def stream_matches_semantic_base(self) -> bool:
        shape = self.stream_input_row_output.row_shape
        return (
            type(shape) is ProjectIRStageRowShape
            and shape.checkpoint.state is self.semantic_base_checkpoint.state
        )


def _stage_scalar_output(
    context: ProjectIRWindowOperatorEvaluationContext,
    fact: ProjectModuleWindowOutputFact,
) -> ProjectIRStageScalarFieldOutput:
    matches = tuple(
        output
        for output in context.fragment.property_stage.outputs
        if type(output) is ProjectIRStageScalarFieldOutput
        and output.occurrence.producer is context.operator.node
        and output.field.field_position == fact.selected_output_ordinal
    )
    if len(matches) != 1:
        raise ValueError("Window result requires one exact stage scalar output.")
    return matches[0]


def _evaluation_policy(
    context: ProjectIRWindowOperatorEvaluationContext,
    fact: ProjectModuleWindowOutputFact,
    output: ProjectIRStageScalarFieldOutput,
) -> ProjectIRProvidedEvaluationPolicy:
    matches = tuple(
        property_
        for property_ in context.fragment.property_stage.provided
        if type(property_) is ProjectIRProvidedEvaluationPolicy
        and property_.output is output
        and property_.evidence is fact
    )
    if len(matches) != 1:
        raise ValueError("Window result requires one exact evaluation policy.")
    return matches[0]


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRWindowResultEvaluationContext:
    """Exact semantic, policy, effect, and stage-value authority for one result."""

    operator_context: ProjectIRWindowOperatorEvaluationContext
    window_fact: ProjectModuleWindowOutputFact = field(
        repr=False,
        compare=False,
        hash=False,
    )
    project_fact: WindowResultProjectFact = field(
        repr=False,
        compare=False,
        hash=False,
    )
    stage_scalar_output: ProjectIRStageScalarFieldOutput
    policy: ProjectIRProvidedEvaluationPolicy
    effect: ProjectIREffectEvidence

    def __post_init__(self) -> None:
        if type(self.operator_context) is not ProjectIRWindowOperatorEvaluationContext:
            raise TypeError("Window result requires an exact operator context.")
        semantic = self.operator_context.semantic_facts
        if (
            type(self.window_fact) is not ProjectModuleWindowOutputFact
            or not any(self.window_fact is fact for fact in semantic.window_outputs)
            or self.project_fact is not self.window_fact.project_fact
            or type(self.project_fact) is not WindowResultProjectFact
        ):
            raise ValueError("Window result requires exact semantic project authority.")
        if (
            type(self.stage_scalar_output) is not ProjectIRStageScalarFieldOutput
            or self.stage_scalar_output
            is not _stage_scalar_output(self.operator_context, self.window_fact)
            or self.policy
            is not _evaluation_policy(
                self.operator_context,
                self.window_fact,
                self.stage_scalar_output,
            )
            or self.effect
            is not _effect(self.operator_context.fragment, self.stage_scalar_output)
        ):
            raise ValueError("Window result must retain exact policy/effect authority.")
        ordinal = self.window_fact.selected_output_ordinal
        final_matches = tuple(
            output
            for output in self.operator_context.fragment.final_scalar_outputs
            if output.field.anchor.identity.field_position == ordinal
        )
        if len(final_matches) != 1 or final_matches[0].occurrence is (
            self.stage_scalar_output.occurrence
        ):
            raise ValueError("Window stage value must differ from its final export.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIREvaluationContextStage:
    """Complete canonical evaluation-context projection over one Project plan."""

    project_plan: ProjectIRProjectPlan
    aggregate_contexts: tuple[ProjectIRAggregateEvaluationContext, ...] = ()
    window_operator_contexts: tuple[
        ProjectIRWindowOperatorEvaluationContext,
        ...,
    ] = ()
    window_result_contexts: tuple[ProjectIRWindowResultEvaluationContext, ...] = ()

    def __post_init__(self) -> None:
        if type(self.project_plan) is not ProjectIRProjectPlan:
            raise TypeError("Evaluation stage requires one exact Project plan.")
        if type(self.aggregate_contexts) is not tuple or any(
            type(context) is not ProjectIRAggregateEvaluationContext
            for context in self.aggregate_contexts
        ):
            raise TypeError("Evaluation stage requires exact aggregate contexts.")
        if type(self.window_operator_contexts) is not tuple or any(
            type(context) is not ProjectIRWindowOperatorEvaluationContext
            for context in self.window_operator_contexts
        ):
            raise TypeError("Evaluation stage requires exact window contexts.")
        if type(self.window_result_contexts) is not tuple or any(
            type(context) is not ProjectIRWindowResultEvaluationContext
            for context in self.window_result_contexts
        ):
            raise TypeError("Evaluation stage requires exact window-result contexts.")

        aggregate_operators = tuple(
            (fragment, operator)
            for fragment in self.project_plan.concrete_fragments
            for operator in fragment.logical_stage.operators
            if operator.kind is ProjectIRLogicalOperatorKind.GROUP_AGGREGATE
        )
        if len(self.aggregate_contexts) != len(aggregate_operators) or any(
            context.fragment is not fragment or context.operator is not operator
            for context, (fragment, operator) in zip(
                self.aggregate_contexts,
                aggregate_operators,
                strict=True,
            )
        ):
            raise ValueError("Evaluation stage requires complete aggregate contexts.")

        window_operators = tuple(
            (fragment, operator)
            for fragment in self.project_plan.concrete_fragments
            for operator in fragment.logical_stage.operators
            if operator.kind is ProjectIRLogicalOperatorKind.WINDOW_EVALUATION
        )
        if len(self.window_operator_contexts) != len(window_operators) or any(
            context.fragment is not fragment or context.operator is not operator
            for context, (fragment, operator) in zip(
                self.window_operator_contexts,
                window_operators,
                strict=True,
            )
        ):
            raise ValueError("Evaluation stage requires complete window contexts.")

        expected_results = tuple(
            (context, fact)
            for context in self.window_operator_contexts
            for fact in context.semantic_facts.window_outputs
        )
        if len(self.window_result_contexts) != len(expected_results) or any(
            result.operator_context is not context or result.window_fact is not fact
            for result, (context, fact) in zip(
                self.window_result_contexts,
                expected_results,
                strict=True,
            )
        ):
            raise ValueError(
                "Evaluation stage requires complete window-result contexts."
            )

    @property
    def structural_stage(self):
        return self.project_plan.structural_stage

    @property
    def starting_allocation(self):
        return self.project_plan.starting_allocation

    @property
    def ending_allocation(self):
        return self.project_plan.ending_allocation


def _base_checkpoint(
    fragment: ProjectIRConcreteSingleRelationFragment,
) -> ProjectIRStageRowCheckpoint:
    existing = tuple(
        output.row_shape.checkpoint
        for output in fragment.property_stage.outputs
        if type(output) is ProjectIRRelationRowOutput
        and type(output.row_shape) is ProjectIRStageRowShape
        and output.row_shape.checkpoint.kind
        is ProjectIRStageRowCheckpointKind.BASE_RESULT
    )
    if existing:
        first = existing[0]
        if any(checkpoint is not first for checkpoint in existing[1:]):
            raise ValueError("BASE_RESULT checkpoint authority must be unique.")
        return first
    return ProjectIRStageRowCheckpoint(
        relation=fragment.subject.anchor,
        evidence=fragment.semantic_facts,
        kind=ProjectIRStageRowCheckpointKind.BASE_RESULT,
    )


def _aggregate_context(
    fragment: ProjectIRConcreteSingleRelationFragment,
    operator: ProjectIRLogicalOperatorOccurrence,
) -> ProjectIRAggregateEvaluationContext:
    semantic = fragment.semantic_facts
    flow = _incoming_flow(fragment, operator)
    input_row = _row_output_for_occurrence(fragment, flow.output)
    result_row = _result_row_output(fragment, operator)
    readiness = semantic.aggregate_grouped_clause_readiness
    let_scope = semantic.let_scope_facts
    if readiness is None or let_scope is None:
        raise ValueError("Aggregate context requires exact semantic scope authority.")
    return ProjectIRAggregateEvaluationContext(
        fragment=fragment,
        operator=operator,
        incoming_flow=flow,
        input_row_output=input_row,
        result_row_output=result_row,
        semantic_facts=semantic,
        readiness=readiness,
        group_keys=semantic.group_key_occurrences,
        aggregate_results=semantic.aggregate_result_facts,
        let_scope=let_scope,
        input_closed_bindings=_closed_bindings(fragment, input_row),
        result_closed_bindings=_closed_bindings(fragment, result_row),
        input_effect=_effect(fragment, input_row),
        result_effect=_effect(fragment, result_row),
    )


def _window_operator_context(
    fragment: ProjectIRConcreteSingleRelationFragment,
    operator: ProjectIRLogicalOperatorOccurrence,
) -> ProjectIRWindowOperatorEvaluationContext:
    semantic = fragment.semantic_facts
    flow = _incoming_flow(fragment, operator)
    input_row = _row_output_for_occurrence(fragment, flow.output)
    result_row = _result_row_output(fragment, operator)
    let_scope = semantic.let_scope_facts
    if let_scope is None:
        raise ValueError("Window context requires exact let-scope authority.")
    return ProjectIRWindowOperatorEvaluationContext(
        fragment=fragment,
        operator=operator,
        incoming_flow=flow,
        stream_input_row_output=input_row,
        semantic_base_checkpoint=_base_checkpoint(fragment),
        result_row_output=result_row,
        semantic_facts=semantic,
        let_scope=let_scope,
        named_window_namespace=semantic.named_window_namespace,
        stream_closed_bindings=_closed_bindings(fragment, input_row),
        result_closed_bindings=_closed_bindings(fragment, result_row),
        stream_effect=_effect(fragment, input_row),
        result_effect=_effect(fragment, result_row),
    )


def build_project_ir_evaluation_context_stage(
    project_plan: ProjectIRProjectPlan,
) -> ProjectIREvaluationContextStage:
    """Project exact evaluation contexts without executing or allocating IR."""

    if type(project_plan) is not ProjectIRProjectPlan:
        raise TypeError(
            "Evaluation-context construction requires an exact Project plan."
        )
    aggregate_contexts: list[ProjectIRAggregateEvaluationContext] = []
    window_contexts: list[ProjectIRWindowOperatorEvaluationContext] = []
    result_contexts: list[ProjectIRWindowResultEvaluationContext] = []
    for fragment in project_plan.concrete_fragments:
        for operator in fragment.logical_stage.operators:
            if operator.kind is ProjectIRLogicalOperatorKind.GROUP_AGGREGATE:
                aggregate_contexts.append(_aggregate_context(fragment, operator))
            if operator.kind is not ProjectIRLogicalOperatorKind.WINDOW_EVALUATION:
                continue
            window_context = _window_operator_context(fragment, operator)
            window_contexts.append(window_context)
            for fact in fragment.semantic_facts.window_outputs:
                scalar = _stage_scalar_output(window_context, fact)
                project_fact = fact.project_fact
                if type(project_fact) is not WindowResultProjectFact:
                    raise ValueError(
                        "Concrete window result requires exact project fact."
                    )
                result_contexts.append(
                    ProjectIRWindowResultEvaluationContext(
                        operator_context=window_context,
                        window_fact=fact,
                        project_fact=project_fact,
                        stage_scalar_output=scalar,
                        policy=_evaluation_policy(window_context, fact, scalar),
                        effect=_effect(fragment, scalar),
                    )
                )
    return ProjectIREvaluationContextStage(
        project_plan=project_plan,
        aggregate_contexts=tuple(aggregate_contexts),
        window_operator_contexts=tuple(window_contexts),
        window_result_contexts=tuple(result_contexts),
    )
