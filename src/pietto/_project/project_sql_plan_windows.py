"""Window computations, original input bindings and post-window predicate values."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from pietto.ast_nodes import (
    Expression,
    WindowExpr,
    SelectItem,
    LetBinding,
    TableDef,
    QueryDef,
    QualifyClause,
)
from pietto._window_identity import WindowFunctionIdentity
from pietto.semantic.model import ValueType, ValueTypeKind
from pietto.semantic.window_semantics import (
    WindowExpressionAnalysis,
    WindowPartitionFieldBinding,
    WindowOrderFieldBinding,
    WindowComputationAnalysis,
    ValidatedWindowSpecification,
    ResolvedWindowFunctionModifiers,
    ResolvedNamedWindowUse,
    ResolvedNamedWindowNamespace,
    RankingAdvancePolicy,
    DistributionWindowPolicy,
    NavigationWindowSemanticFact,
    NavigationWindowComputation,
    FrameValueWindowSemanticFact,
    FrameValueWindowComputation,
)
from pietto.semantic.window_input_analysis import (
    WindowInputBinding,
    WindowInputOriginKind,
)
from pietto._project.module_catalog import ProjectDeclarationOccurrence
from pietto._project.model import ProjectRowField, ProjectRowResultRole
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleWindowOutputFact,
    ProjectModuleSelectFact,
    ProjectModuleRelationSemanticFacts,
    ProjectModuleCandidateBucketStatus,
    _projection_output_name,
)
from pietto._project.window_semantics import (
    WindowDependencyOccurrence,
    WindowDependencyRole,
    WindowComputationInput,
    retained_window_computation_input,
    window_dependency_sources,
)
from pietto._project.project_final_outputs import (
    ProjectConcreteNoJoinReplay,
    ProjectNoJoinHiddenWindowComputation,
    ProjectNoJoinHiddenWindowInputUse,
    ProjectNoJoinWindowInput,
    ProjectNoJoinQualify,
    ProjectNoJoinQualifyReferenceResolution,
)
from pietto._project.project_joined_windows import (
    ProjectConcreteWindowComputation,
    ProjectSelectedWindowResultBinding,
    ProjectJoinedWindowInputBinding,
    ProjectJoinedWindowInputNamespace,
    ProjectWindowDependencyOccurrence,
)
from pietto._project.project_joined_qualify import (
    ProjectConcreteJoinedQualify,
    ProjectQualifyReferenceResolution,
)
from pietto._project.project_query_block_ir import (
    ProjectIRReusedEffectiveOutput,
    ProjectIRReboundExistingOutput,
    ProjectIRCompletedQueryBlockOutput,
    ProjectIRQueryBlockWindowPolicy,
    ProjectIRQueryBlockRowOutput,
    ProjectIRQueryBlockWindowEvidence,
    ProjectIRQueryBlockEffectEvidence,
    ProjectIRQueryBlockOperatorOccurrence,
)
from pietto._project.project_ir_properties import (
    ProjectIRProvidedEvaluationPolicy,
    ProjectIREffectEvidence,
)
from pietto._project.project_ir_operators import ProjectIRLogicalOperatorOccurrence
from pietto._project import project_sql_plan_aggregation as aggregation

if TYPE_CHECKING:
    from pietto._project.project_sql_plan import ProjectSQLPlanRef, ProjectSQLSymbol
    from pietto._project.project_sql_plan_expressions import ProjectSQLExpressionRole

__all__: tuple[str, ...] = ()

type Source = (
    ProjectModuleWindowOutputFact
    | ProjectConcreteWindowComputation
    | ProjectNoJoinHiddenWindowComputation
)
type Selected = ProjectModuleWindowOutputFact | ProjectSelectedWindowResultBinding
type Analysis = WindowExpressionAnalysis | WindowComputationAnalysis
type InputContext = (
    WindowComputationInput
    | ProjectNoJoinWindowInput
    | ProjectJoinedWindowInputNamespace
)
type InputUse = (
    WindowDependencyOccurrence
    | ProjectWindowDependencyOccurrence
    | ProjectNoJoinHiddenWindowInputUse
)
type Qualify = ProjectNoJoinQualify | ProjectConcreteJoinedQualify
type Reference = (
    ProjectNoJoinQualifyReferenceResolution
    | ProjectQualifyReferenceResolution
    | ProjectNoJoinHiddenWindowComputation
    | ProjectConcreteWindowComputation
)
type Navigation = NavigationWindowSemanticFact | NavigationWindowComputation
type FrameValue = FrameValueWindowSemanticFact | FrameValueWindowComputation


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLWindowAuthority:
    root: (
        ProjectModuleRelationSemanticFacts
        | ProjectConcreteNoJoinReplay
        | ProjectConcreteJoinedQualify
    )
    selected: tuple[Selected, ...]
    hidden: tuple[
        ProjectNoJoinHiddenWindowComputation | ProjectConcreteWindowComputation, ...
    ]
    named: ResolvedNamedWindowNamespace | None
    qualify: Qualify | None


def authority(entry) -> ProjectSQLWindowAuthority | None:
    if isinstance(
        entry, (ProjectIRReusedEffectiveOutput, ProjectIRReboundExistingOutput)
    ):
        root = entry.semantic_entry.fragment.semantic_facts
        selected, hidden, named, qualify = (
            root.window_outputs,
            (),
            root.named_window_namespace,
            None,
        )
    elif isinstance(entry, ProjectIRCompletedQueryBlockOutput):
        root = entry.semantic_entry.root
        if isinstance(root, ProjectConcreteNoJoinReplay):
            selected, hidden, named = (
                root.window_outputs,
                root.qualify.hidden_attempts,
                root.semantic_facts.named_window_namespace,
            )
            qualify = root.qualify if root.qualify.clause is not None else None
        elif isinstance(root, ProjectConcreteJoinedQualify):
            selected, hidden, named = (
                root.window_stage.selected_results,
                root.hidden_computations,
                root.window_stage.named_namespace,
            )
            qualify = root if root.qualify_clause is not None else None
        else:
            return None
    else:
        return None
    if not selected and not hidden and qualify is None:
        return None
    if named is not None and not isinstance(named, ResolvedNamedWindowNamespace):
        raise ValueError("Windows require a successful original named namespace")
    return ProjectSQLWindowAuthority(
        root=root, selected=selected, hidden=hidden, named=named, qualify=qualify
    )


def selected_source(value: Selected) -> Source:
    return (
        value.computation
        if isinstance(value, ProjectSelectedWindowResultBinding)
        else value
    )


def sources(value: ProjectSQLWindowAuthority) -> tuple[Source, ...]:
    return (*(selected_source(item) for item in value.selected), *value.hidden)


def analysis(source: Source) -> Analysis:
    result = source.analysis
    if not isinstance(result, (WindowExpressionAnalysis, WindowComputationAnalysis)):
        raise ValueError("Window computation requires its retained successful analysis")
    return result


def effective(source: Source) -> WindowExpr:
    result = analysis(source)
    return (
        result.semantic_fact.expression
        if isinstance(result, WindowExpressionAnalysis)
        else result.expression
    )


def authored(source: Source) -> WindowExpr:
    return analysis(source).authored_expression


def project_targets_valid(
    context: WindowComputationInput | ProjectNoJoinWindowInput,
) -> bool:
    """Check a supplied association, without looking up an expression or choosing a target."""
    if isinstance(context, WindowComputationInput):
        schema, targets, definition = (
            context.project_schema,
            context.project_targets,
            context.definition,
        )
    else:
        schema, targets, definition = (
            context.input_schema,
            context.targets,
            context.owner.definition,
        )
    if (
        schema is None
        or not isinstance(definition, (TableDef, QueryDef))
        or type(targets) is not tuple
        or len(targets) != len(context.scope.bindings)
    ):
        return False
    fields = {id(field): field for field in schema.fields.values()}
    lets = (
        {}
        if definition.let_clause is None
        else {id(binding): binding for binding in definition.let_clause.bindings}
    )
    selected = {id(item): item for item in definition.select_items}
    for binding, target in zip(context.scope.bindings, targets, strict=True):
        if binding.origin is WindowInputOriginKind.UPSTREAM_FIELD:
            if (
                not isinstance(target, ProjectRowField)
                or fields.get(id(target)) is not target
                or target.name != binding.target_name
            ):
                return False
        elif binding.origin is WindowInputOriginKind.LET_BINDING:
            if (
                not isinstance(target, LetBinding)
                or lets.get(id(target)) is not target
                or target.name != binding.target_name
            ):
                return False
        elif (
            not isinstance(target, SelectItem)
            or selected.get(id(target)) is not target
            or isinstance(target.expression, WindowExpr)
            or _projection_output_name(target) != binding.target_name
        ):
            return False
    return True


def input_context(source: Source) -> InputContext:
    if isinstance(source, ProjectModuleWindowOutputFact):
        fact = source.project_fact
        if (
            source.status is not ProjectModuleCandidateBucketStatus.CONCRETE
            or fact is None
            or fact is not source.retained_project_fact
        ):
            raise ValueError("Selected window has no concrete original project fact")
        result = retained_window_computation_input(fact)
        if (
            result is None
            or result.project_schema is None
            or result.item is not source.item
            or result.definition is not source.owner.definition
        ):
            raise ValueError("Selected window lost its original input bindings")
        if not project_targets_valid(result):
            raise ValueError(
                "Selected window Project correspondence is incomplete or foreign"
            )
        return result
    if isinstance(source, ProjectNoJoinHiddenWindowComputation):
        if (
            source.input_context is None
            or source.input_uses is None
            or source.input_context.scope is not source.scope
        ):
            raise ValueError("Hidden window lost construction-time input preparation")
        if not project_targets_valid(source.input_context):
            raise ValueError(
                "Hidden window Project correspondence is incomplete or foreign"
            )
        return source.input_context
    return source.input_namespace


def input_uses(source: Source) -> tuple[InputUse, ...]:
    input_context(source)
    if isinstance(source, ProjectModuleWindowOutputFact):
        assert source.project_fact is not None
        return source.project_fact.dependency_occurrences
    if isinstance(source, ProjectNoJoinHiddenWindowComputation):
        assert source.input_uses is not None
        return source.input_uses
    return source.dependencies


def joined_target(binding: ProjectJoinedWindowInputBinding):
    if binding.stage_output is not None:
        output = binding.stage_output
        if output.group_key is not None:
            return output.group_key
        if output.aggregate is None:
            raise ValueError("Window group input lost its aggregate output")
        return output.aggregate.item
    if binding.let_value is not None:
        return binding.let_value.occurrence
    if binding.joined_field is None:
        raise ValueError("Window row input lost its exact joined field")
    return binding.joined_field.scalar_field


def group_target(target, aggregate):
    if (
        aggregate is not None
        and isinstance(target, SelectItem)
        and isinstance(
            aggregate.source, aggregation.ProjectAggregateGroupedClauseReadiness
        )
    ):
        for item, key in aggregate.source.finalization.group_projections:
            if item is target:
                return key
    return target


def input_target(source: Source, use: InputUse, aggregate):
    if use.role is WindowDependencyRole.RELATION_INPUT:
        return None
    if isinstance(use, WindowDependencyOccurrence):
        context = input_context(source)
        if (
            not isinstance(context, WindowComputationInput)
            or use.computation is not context
            or use.binding is None
        ):
            raise ValueError("Selected window use lost its original binding context")
        matched = tuple(
            target
            for binding, target in zip(
                context.scope.bindings, context.project_targets, strict=True
            )
            if binding is use.binding
        )
        if len(matched) != 1:
            raise ValueError("Window binding is not an exact retained member")
        target = matched[0]
    elif isinstance(use, ProjectNoJoinHiddenWindowInputUse):
        if (
            use.context is not input_context(source)
            or use.hidden is not authored(source)
            or use.binding is None
            or use.target is None
        ):
            raise ValueError("Hidden window use lost its preparation result")
        context = use.context
        matches = tuple(
            target
            for binding, target in zip(
                context.scope.bindings, context.targets, strict=True
            )
            if binding is use.binding
        )
        if len(matches) != 1 or matches[0] is not use.target:
            raise ValueError(
                "Hidden input lost its exact Project target correspondence"
            )
        target = use.target
    else:
        if not isinstance(use.target, ProjectJoinedWindowInputBinding):
            raise ValueError("Joined field use requires an original input binding")
        target = joined_target(use.target)
    return group_target(target, aggregate)


def result_type(source: Source) -> ValueType:
    value = analysis(source)
    result = (
        value.semantic_fact.result
        if isinstance(value, WindowExpressionAnalysis)
        else value.result
    )
    if result.value_type is None or result.value_type.kind is not ValueTypeKind.KNOWN:
        raise ValueError("Window result requires its original concrete type")
    return result.value_type


def components(source: Source):
    value = analysis(source)
    if isinstance(value, WindowExpressionAnalysis):
        navigation, frame_value = value.navigation_fact, value.frame_value_fact
        return (
            value.partition_binding_fact.bindings,
            value.order_binding_fact.bindings,
            None if value.ranking_fact is None else value.ranking_fact.advance_policy,
            None
            if value.distribution_fact is None
            else value.distribution_fact.distribution_policy,
            None
            if value.distribution_fact is None
            else value.distribution_fact.bucket_count,
            navigation,
            frame_value,
            navigation.modifiers
            if navigation is not None
            else frame_value.modifiers
            if frame_value is not None
            else None,
        )
    return (
        value.partition_bindings,
        value.order_bindings,
        value.ranking_advance_policy,
        value.distribution_policy,
        value.bucket_count,
        value.navigation,
        value.frame_value,
        value.modifiers,
    )


def use_type(source: Source, use: InputUse) -> ValueType | None:
    partitions, orders, _, _, _, navigation, frame_value, _ = components(source)
    role = use.role
    if role is WindowDependencyRole.RELATION_INPUT:
        return None
    if role is WindowDependencyRole.WINDOW_PARTITION:
        return partitions[use.role_ordinal].value_type
    if role is WindowDependencyRole.WINDOW_ORDER:
        return orders[use.role_ordinal].value_type
    if role is WindowDependencyRole.WINDOW_DEFAULT:
        if navigation is None:
            raise ValueError("Window default lost its navigation authority")
        return navigation.default_fact.value_type
    value = navigation if navigation is not None else frame_value
    if value is None:
        raise ValueError("Window argument lost its specialized type")
    return value.value_type


def ready(source: Source, entry, aggregate) -> bool:
    """Validate the new transport prerequisite; old IR validity does not imply it."""
    context = input_context(source)
    original_analysis = analysis(source)
    result_type(source)
    ir_evidence(source, entry)
    expected = window_dependency_sources(effective(source))
    uses = input_uses(source)
    if len(uses) != len(expected):
        return False
    if isinstance(source, ProjectNoJoinHiddenWindowComputation):
        if (
            not isinstance(entry, ProjectIRCompletedQueryBlockOutput)
            or not isinstance(entry.semantic_entry.root, ProjectConcreteNoJoinReplay)
            or not isinstance(context, ProjectNoJoinWindowInput)
            or context.owner is not entry.owner
            or context.scope is not entry.semantic_entry.root.window_scope
            or context.input_schema is not entry.semantic_entry.root.input_schema
            or context.let_scope is not entry.semantic_entry.root.let_scope
            or context.base_schema is not entry.semantic_entry.root.base_state.schema
        ):
            return False
    if isinstance(source, ProjectModuleWindowOutputFact):
        if not isinstance(context, WindowComputationInput):
            return False
        if isinstance(entry, ProjectIRCompletedQueryBlockOutput):
            if not isinstance(entry.semantic_entry.root, ProjectConcreteNoJoinReplay):
                return False
            schema = entry.semantic_entry.root.input_schema
        else:
            state = entry.semantic_entry.fragment.semantic_facts.input_state
            if state is None:
                return False
            schema = state.schema
        if context.project_schema is not schema:
            return False
    ordinals = {}
    for position, (use, (role, expression)) in enumerate(
        zip(uses, expected, strict=True)
    ):
        ordinal = ordinals.get(role, 0)
        ordinals[role] = ordinal + 1
        if (
            use.role is not role
            or use.expression is not expression
            or type(use.global_ordinal) is not int
            or use.global_ordinal != position
            or type(use.role_ordinal) is not int
            or use.role_ordinal != ordinal
        ):
            return False
        if isinstance(use, WindowDependencyOccurrence):
            if (
                not isinstance(context, WindowComputationInput)
                or use.computation is not context
                or context.analysis is not original_analysis
            ):
                return False
            binding = use.binding
            expected_role = (
                None
                if binding is None
                else {
                    WindowInputOriginKind.GROUP_KEY: ProjectRowResultRole.GROUP_KEY,
                    WindowInputOriginKind.AGGREGATE_RESULT: ProjectRowResultRole.AGGREGATE_RESULT,
                }.get(binding.origin)
            )
            if use.target_result_role is not expected_role:
                return False
            members = context.scope.bindings
        elif isinstance(use, ProjectNoJoinHiddenWindowInputUse):
            if (
                not isinstance(context, ProjectNoJoinWindowInput)
                or not isinstance(source, ProjectNoJoinHiddenWindowComputation)
                or use.context is not context
                or use.hidden is not source.expression
            ):
                return False
            binding, members = use.binding, context.scope.bindings
        else:
            if (
                not isinstance(source, ProjectConcreteWindowComputation)
                or not isinstance(context, ProjectJoinedWindowInputNamespace)
                or use.site is not source.site
            ):
                return False
            binding = (
                use.target
                if isinstance(use.target, ProjectJoinedWindowInputBinding)
                else None
            )
            members = context.bindings
        if role is WindowDependencyRole.RELATION_INPUT:
            if binding is not None:
                return False
        elif (
            binding is None
            or not any(binding is member for member in members)
            or binding.value_type != use_type(source, use)
            or input_target(source, use, aggregate) is None
        ):
            return False
    return True


def ir_evidence(source: Source, entry):
    """Read the original operator, stage-result policy and unknown effects."""
    if isinstance(entry, ProjectIRCompletedQueryBlockOutput):
        operators = entry.operators
        policies = tuple(
            policy for policy in entry.window_policies if policy.evidence is source
        )
        effects = entry.effects
    else:
        fragment = (
            entry.rebuilt_fragment
            if isinstance(entry, ProjectIRReboundExistingOutput)
            else entry.semantic_entry.fragment
        )
        operators = fragment.logical_stage.operators
        policies = tuple(
            policy
            for policy in fragment.property_stage.provided
            if isinstance(policy, ProjectIRProvidedEvaluationPolicy)
            and policy.evidence is source
            and any(
                operator.kind.value == "window_evaluation"
                and policy.output.occurrence.producer is operator.node
                for operator in operators
            )
        )
        effects = fragment.property_stage.effects
    window_operators = tuple(
        operator for operator in operators if operator.kind.value == "window_evaluation"
    )
    if len(window_operators) != 1 or len(policies) > 1:
        raise ValueError(
            "Window computation lost its original IR operator or result policy"
        )
    operator = window_operators[0]
    policy = policies[0] if policies else None
    if policy is None:
        if (
            not isinstance(operator, ProjectIRQueryBlockOperatorOccurrence)
            or not isinstance(operator.evidence, ProjectIRQueryBlockWindowEvidence)
            or not any(source is hidden for hidden in operator.evidence.hidden)
        ):
            raise ValueError(
                "Only an original hidden computation has no IR scalar policy"
            )
        matched = tuple(
            effect
            for effect in effects
            if isinstance(effect.output, ProjectIRQueryBlockRowOutput)
            and effect.output.occurrence.producer is operator.node
        )
    else:
        matched = tuple(effect for effect in effects if effect.output is policy.output)
    if len(matched) != 1:
        raise ValueError(
            "Window computation requires its exact original effect evidence"
        )
    return operator, policy, matched[0]


def qualifier_references(value: Qualify) -> tuple[Reference, ...]:
    references = value.references
    hidden = (
        value.hidden_attempts
        if isinstance(value, ProjectNoJoinQualify)
        else value.hidden_computations
    )
    indexed: dict[int, Reference] = {
        id(reference.expression): reference for reference in references
    }
    indexed.update({id(authored(item)): item for item in hidden})
    clause = (
        value.clause
        if isinstance(value, ProjectNoJoinQualify)
        else value.qualify_clause
    )
    if clause is None:
        return ()
    from pietto._project.project_joined_qualify import _qualify_operands

    return tuple(
        indexed[id(expression)] for expression in _qualify_operands(clause.expression)
    )


def reference_expression(reference: Reference) -> Expression:
    if isinstance(reference, ProjectConcreteWindowComputation):
        return reference.site.expression
    return reference.expression


def qualify_target(value: Qualify, reference: Reference, aggregate):
    if isinstance(
        reference,
        (ProjectNoJoinHiddenWindowComputation, ProjectConcreteWindowComputation),
    ):
        return reference
    target = reference.target
    if (
        reference.status is not ProjectModuleCandidateBucketStatus.CONCRETE
        or target is None
        or len(reference.candidates) != 1
        or reference.candidates[0] is not target
    ):
        raise ValueError("QUALIFY requires its original unambiguous candidate")
    if isinstance(target, WindowInputBinding):
        if (
            not isinstance(value, ProjectNoJoinQualify)
            or not isinstance(reference, ProjectNoJoinQualifyReferenceResolution)
            or value.input_context is None
            or reference.scope is not value.scope
        ):
            raise ValueError("QUALIFY has no original Project input correspondence")
        context = value.input_context
        if (
            context.scope is not value.scope
            or context.owner is not value.owner
            or not project_targets_valid(context)
        ):
            raise ValueError("QUALIFY lost its original Project input context")
        matches = tuple(
            key
            for binding, key in zip(
                context.scope.bindings, context.targets, strict=True
            )
            if binding is target
        )
        if len(matches) != 1:
            raise ValueError("QUALIFY target must belong to the exact input scope")
        return group_target(matches[0], aggregate)
    if isinstance(target, ProjectJoinedWindowInputBinding):
        return joined_target(target)
    return selected_source(target)


def qualify_types(value: Qualify):
    if isinstance(value, ProjectNoJoinQualify):
        if value.predicate is None:
            raise ValueError("Authored QUALIFY requires its predicate evidence")
        return value.predicate.value_types
    return value.value_types


def qualify_effects(value: Qualify):
    if isinstance(value, ProjectNoJoinQualify):
        if value.predicate is None:
            raise ValueError("Authored QUALIFY requires its predicate evidence")
        return value.predicate.retention_effects
    return value.retention_effects


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLWindow:
    ref: ProjectSQLPlanRef
    block: ProjectSQLPlanRef
    definition: ProjectSQLPlanRef
    position: int
    source: Source
    selected: Selected | None
    authored: WindowExpr
    effective: WindowExpr
    function: WindowFunctionIdentity
    context: InputContext
    inputs: tuple[ProjectSQLPlanRef, ...]
    uses: tuple[ProjectSQLPlanRef, ...]
    arguments: tuple[ProjectSQLPlanRef, ...]
    result: ProjectSQLPlanRef
    value_type: ValueType
    policy: ProjectSQLPlanRef


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLWindowUse:
    ref: ProjectSQLPlanRef
    window: ProjectSQLPlanRef
    source: InputUse
    role: WindowDependencyRole
    position: int
    role_position: int
    expression: Expression
    input: ProjectSQLPlanRef | None
    binding: WindowInputBinding | ProjectJoinedWindowInputBinding | None
    value_type: ValueType | None


class ProjectSQLWindowArgumentRole(StrEnum):
    VALUE = "value"
    DEFAULT = "default"
    OFFSET = "offset"
    BUCKET = "bucket"
    POSITION = "position"


def argument_role(source: Source, position: int) -> ProjectSQLWindowArgumentRole:
    kind = effective(source).identity.name
    R = ProjectSQLWindowArgumentRole
    return (
        R.BUCKET
        if kind == "ntile"
        else R.VALUE
        if position == 0
        else R.DEFAULT
        if position == 2
        else R.POSITION
        if kind == "nth_value"
        else R.OFFSET
    )


def argument_type(source: Source, position: int):
    _, _, _, _, _, navigation, frame_value, _ = components(source)
    if (
        position == 0
        and (value := navigation if navigation is not None else frame_value) is not None
    ):
        return value.value_type
    return (
        navigation.default_fact.value_type
        if position == 2 and navigation is not None
        else None
    )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLWindowArgument:
    ref: ProjectSQLPlanRef
    window: ProjectSQLPlanRef
    position: int
    role: ProjectSQLWindowArgumentRole
    expression: Expression
    value_type: ValueType | None
    use: ProjectSQLPlanRef | None


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLWindowPolicy:
    ref: ProjectSQLPlanRef
    window: ProjectSQLPlanRef
    specification: ValidatedWindowSpecification
    partitions: tuple[WindowPartitionFieldBinding, ...]
    orders: tuple[WindowOrderFieldBinding, ...]
    modifiers: ResolvedWindowFunctionModifiers | None
    named_use: ResolvedNamedWindowUse | None
    namespace: ResolvedNamedWindowNamespace | None
    ranking: RankingAdvancePolicy | None
    distribution: DistributionWindowPolicy | None
    bucket_count: int | None
    navigation: Navigation | None
    frame_value: FrameValue | None

    ir_operator: (
        ProjectIRLogicalOperatorOccurrence | ProjectIRQueryBlockOperatorOccurrence
    )
    ir_policy: (
        ProjectIRProvidedEvaluationPolicy | ProjectIRQueryBlockWindowPolicy | None
    )
    ir_effect: ProjectIREffectEvidence | ProjectIRQueryBlockEffectEvidence


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLQualifySite:
    ref: ProjectSQLPlanRef
    owner: ProjectDeclarationOccurrence
    block: ProjectSQLPlanRef
    role: ProjectSQLExpressionRole
    ordinal: int
    occurrence: QualifyClause
    evidence: Qualify
    aggregate: aggregation.ProjectSQLAggregationAuthority | None
    references: tuple[Reference, ...]


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLWindowReference:
    ref: ProjectSQLPlanRef
    site: ProjectSQLQualifySite
    expression: Expression
    value_type: ValueType
    reference: Reference
    port: ProjectSQLPlanRef
    symbol: ProjectSQLSymbol


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLWindowProjection:
    ref: ProjectSQLPlanRef
    window: ProjectSQLPlanRef
    block: ProjectSQLPlanRef
    semantic: ProjectModuleSelectFact
    source: Selected
    input: ProjectSQLPlanRef
    export: ProjectSQLPlanRef


class ProjectSQLWindowDemandKind(StrEnum):
    INPUT_BAG_AND_RESULT = "input_bag_and_result"
    INPUT_USE = "input_use"
    ARGUMENT = "argument"
    POLICY = "frame_modifiers_named_components"
    PROJECTION = "result_projection"


type Witness = (
    ProjectSQLWindow
    | ProjectSQLWindowUse
    | ProjectSQLWindowArgument
    | ProjectSQLWindowPolicy
    | ProjectSQLWindowProjection
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLWindowDemand:
    ref: ProjectSQLPlanRef
    subject: ProjectSQLPlanRef
    kind: ProjectSQLWindowDemandKind
    witness: Witness
    origin: ProjectSQLPlanRef
