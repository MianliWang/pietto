"""Retained aggregate authority, private group/result ports and requirements."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from pietto.ast_nodes import (
    Expression,
    CallExpr,
    SelectItem,
    WindowExpr,
    TableDef,
    QueryDef,
    SatisfyingClause,
)
from pietto.semantic.model import ValueType, SatisfyingResultPredicateInfo
from pietto._project.model import ProjectRowResultRole
from pietto._project.module_catalog import ProjectDeclarationOccurrence
from pietto._project.aggregate_grouped_schema import (
    ProjectAggregateExpressionAnalysis,
    ProjectAggregateSelectedResult,
    ProjectGroupedSelectedResult,
    ProjectGroupKeyFact,
    ProjectAggregateSchemaFacts,
    ProjectGroupedSchemaFacts,
)
from pietto._project.aggregate_grouped_clause_facts import (
    ProjectAggregateGroupedClauseReadiness,
    ProjectAggregateGroupedClauseReadinessStatus,
    ProjectRelationClauseDependencyFact,
    ProjectRelationClauseDependencyKind,
)
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleExpressionReferenceFact,
    ProjectModuleSelectFact,
    ProjectModuleFactOccurrenceRole,
    ProjectModuleCandidateBucketStatus,
)
from pietto._project.project_joined_aggregation import (
    ProjectConcreteJoinedAggregation,
    ProjectJoinedAggregationMode,
    ProjectJoinedGroupKeyOccurrence,
    ProjectJoinedAggregateOccurrence,
    ProjectJoinedStageOutputOccurrence,
    ProjectJoinedSatisfyingAnalysis,
    ProjectJoinedSatisfyingOutputReference,
    ProjectJoinedSatisfyingAggregateReference,
    ProjectJoinedGroupProtection,
    ProjectJoinedAggregateGrainLinkage,
    ProjectJoinedAggregatePairLinkage,
    _SATISFYING_RETENTION_EFFECTS,
)
from pietto._project.project_scalar_references import ProjectScalarReferenceResolution
from pietto._project.project_scalar_namespaces import (
    ProjectConcreteJoinedNamespaceExpression,
    ProjectJoinedNamespaceReferenceResolution,
)
from pietto._project.project_joined_qualify import ProjectConcreteJoinedQualify
from pietto._project.project_final_outputs import ProjectConcreteNoJoinReplay
from pietto._project.project_query_block_ir import (
    ProjectIRConcreteQueryBlockEntry,
    ProjectIRReusedEffectiveOutput,
    ProjectIRReboundExistingOutput,
    ProjectIRCompletedQueryBlockOutput,
    ProjectIRQueryBlockAggregateEvaluationContext,
)
from pietto._project.project_ir_evaluation_context import (
    ProjectIRAggregateEvaluationContext,
)
from pietto._project.project_ir_relational_properties import (
    ProjectIROutputRelationalProperties,
)

if TYPE_CHECKING:
    from pietto._project.project_completed_semantics import (
        ProjectConcreteCompletedSemanticResult,
    )
    from pietto._project.project_sql_plan import ProjectSQLPlanRef, ProjectSQLSymbol
    from pietto._project.project_sql_plan_expressions import ProjectSQLExpressionRole

__all__: tuple[str, ...] = ()

type GroupKey = ProjectGroupKeyFact | ProjectJoinedGroupKeyOccurrence
type Aggregate = ProjectAggregateExpressionAnalysis | ProjectJoinedAggregateOccurrence
type Output = (
    ProjectAggregateSelectedResult
    | ProjectGroupedSelectedResult
    | ProjectJoinedStageOutputOccurrence
)
type ResultKey = GroupKey | SelectItem
type Reference = (
    ProjectModuleExpressionReferenceFact
    | ProjectJoinedNamespaceReferenceResolution
    | ProjectRelationClauseDependencyFact
    | ProjectJoinedSatisfyingOutputReference
    | ProjectJoinedSatisfyingAggregateReference
)
type Risk = (
    ProjectJoinedGroupProtection
    | ProjectJoinedAggregateGrainLinkage
    | ProjectJoinedAggregatePairLinkage
)
type Evidence = (
    ProjectAggregateExpressionAnalysis
    | ProjectConcreteJoinedNamespaceExpression
    | ProjectJoinedSatisfyingAnalysis
    | SatisfyingResultPredicateInfo
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLAggregationAuthority:
    """A local read view; every member is an original retained semantic object."""

    source: ProjectAggregateGroupedClauseReadiness | ProjectConcreteJoinedAggregation
    mode: ProjectJoinedAggregationMode
    context: (
        ProjectIRAggregateEvaluationContext
        | ProjectIRQueryBlockAggregateEvaluationContext
    )
    properties: ProjectIROutputRelationalProperties
    keys: tuple[GroupKey, ...]
    aggregates: tuple[Aggregate, ...]
    key_references: tuple[tuple[Reference, ...], ...]
    argument_references: tuple[tuple[Reference, ...], ...]
    output_keys: tuple[ResultKey, ...]
    outputs: tuple[Output, ...]
    risks: tuple[Risk, ...]
    satisfying: ProjectJoinedSatisfyingAnalysis | SatisfyingResultPredicateInfo | None
    satisfying_references: tuple[Reference, ...]


def authority(
    completed: ProjectConcreteCompletedSemanticResult,
    entry: ProjectIRConcreteQueryBlockEntry,
) -> ProjectSQLAggregationAuthority | None:
    """Read existing products without invoking semantic or IR constructors."""
    definition = entry.owner.definition
    if not isinstance(definition, (TableDef, QueryDef)):
        return None
    source = None
    if isinstance(
        entry, (ProjectIRReusedEffectiveOutput, ProjectIRReboundExistingOutput)
    ):
        facts = entry.semantic_entry.fragment.semantic_facts
        source = facts.aggregate_grouped_clause_readiness
        key_references = facts.group_key_references
        selections = facts.select_facts
        selected_references = tuple(f.references for f in selections)
    elif isinstance(entry, ProjectIRCompletedQueryBlockOutput):
        root = entry.semantic_entry.root
        if isinstance(root, ProjectConcreteJoinedQualify):
            joined = root.window_stage.input_aggregation
            if joined.mode is ProjectJoinedAggregationMode.ABSENT:
                return None
            contexts = entry.aggregate_contexts
            if len(contexts) != 1:
                return None
            properties = tuple(
                p.relational
                for p in entry.row_properties
                if p.output.occurrence.producer is contexts[0].operator.node
            )
            if len(properties) != 1:
                return None
            output_keys = []
            for output in joined.stage_outputs:
                if output.group_key is not None:
                    output_keys.append(output.group_key)
                elif output.aggregate is not None:
                    output_keys.append(output.aggregate.item)
                else:
                    return None
            return ProjectSQLAggregationAuthority(
                source=joined,
                mode=joined.mode,
                context=contexts[0],
                properties=properties[0],
                keys=joined.group_keys,
                aggregates=joined.aggregates,
                key_references=tuple(k.resolutions for k in joined.group_keys),
                argument_references=tuple(
                    ()
                    if a.argument_analysis is None
                    else a.argument_analysis.resolutions
                    for a in joined.aggregates
                ),
                output_keys=tuple(output_keys),
                outputs=joined.stage_outputs,
                risks=(
                    *joined.group_protections,
                    *joined.grain_linkages,
                    *joined.pair_linkages,
                ),
                satisfying=joined.satisfying,
                satisfying_references=()
                if joined.satisfying is None
                else joined.satisfying.references,
            )
        if not isinstance(root, ProjectConcreteNoJoinReplay):
            return None
        source = root.aggregate_readiness
        references = tuple(
            r for r in completed.roots.row_references if r.entry is entry.semantic_entry
        )
        if len(references) != 1:
            return None
        key_references = references[0].groups
        selections = tuple(f.select_fact for f in entry.semantic_entry.fields)
        selected_references = references[0].selections
    else:
        return None
    if (
        source is None
        or source.status is not ProjectAggregateGroupedClauseReadinessStatus.CONCRETE
    ):
        return None
    candidate = source.finalization.candidate
    if not isinstance(
        candidate, (ProjectAggregateSchemaFacts, ProjectGroupedSchemaFacts)
    ):
        return None
    mode = (
        ProjectJoinedAggregationMode.GROUPED
        if isinstance(candidate, ProjectGroupedSchemaFacts)
        else ProjectJoinedAggregationMode.GLOBAL
    )
    groups = (
        candidate.group_keys if isinstance(candidate, ProjectGroupedSchemaFacts) else ()
    )
    selected_keys = {
        id(item): key for item, key in source.finalization.group_projections
    }
    analyses = {id(value.item): value for value in source.finalization.analyses}
    if len(analyses) != len(source.finalization.analyses):
        return None
    results_by_item = {
        id(item): (item, value) for item, value in candidate.selected_results.items()
    }
    aggregates = []
    argument_references = []
    output_keys = []
    outputs = []
    for selection, references in zip(selections, selected_references, strict=True):
        if isinstance(selection.item.expression, WindowExpr):
            continue
        matched = results_by_item.get(id(selection.item))
        if matched is None or matched[0] is not selection.item:
            return None
        result = matched[1]
        outputs.append(result)
        if result.field.result_role is ProjectRowResultRole.AGGREGATE_RESULT:
            analysis = analyses.get(id(selection.item))
            if (
                analysis is None
                or analysis.item is not selection.item
                or analysis.field is not result.field
                or analysis.fact
                is not (
                    result.fact
                    if isinstance(result, ProjectAggregateSelectedResult)
                    else result.aggregate_fact
                )
            ):
                return None
            aggregates.append(analysis)
            argument_references.append(references)
            output_keys.append(selection.item)
        else:
            key = selected_keys.get(id(selection.item))
            if key is None:
                return None
            output_keys.append(key)
    if isinstance(entry, ProjectIRReusedEffectiveOutput):
        contexts = tuple(
            c
            for c in completed.verification.root.evaluation.aggregate_contexts
            if c.fragment is entry.semantic_entry.fragment
        )
        properties = tuple(
            p
            for p in completed.verification.root.base_relational.outputs
            if len(contexts) == 1
            and p.output.occurrence.producer is contexts[0].operator.node
        )
    else:
        contexts = entry.aggregate_contexts
        properties = tuple(
            p.relational
            for p in entry.row_properties
            if len(contexts) == 1
            and p.output.occurrence.producer is contexts[0].operator.node
        )
    if len(contexts) != 1 or len(properties) != 1 or len(key_references) != len(groups):
        return None
    if definition.satisfying_clause is not None and (
        source.satisfying is None or source.occurrence_facts is None
    ):
        return None
    return ProjectSQLAggregationAuthority(
        source=source,
        mode=mode,
        context=contexts[0],
        properties=properties[0],
        keys=groups,
        aggregates=tuple(aggregates),
        key_references=key_references,
        argument_references=tuple(argument_references),
        output_keys=tuple(output_keys),
        outputs=tuple(outputs),
        risks=(),
        satisfying=source.satisfying,
        satisfying_references=tuple(
            f
            for f in source.occurrence_facts or ()
            if f.kind is ProjectRelationClauseDependencyKind.SATISFYING_OUTPUT
        ),
    )


class ProjectSQLAggregateEmptyInput(StrEnum):
    NO_GROUPS = "no_groups"
    ONE_GLOBAL_ROW = "one_global_row"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLAggregation:
    ref: ProjectSQLPlanRef
    block: ProjectSQLPlanRef
    definition: ProjectSQLPlanRef
    authority: ProjectSQLAggregationAuthority
    mode: ProjectJoinedAggregationMode
    keys: tuple[ProjectSQLPlanRef, ...]
    aggregates: tuple[ProjectSQLPlanRef, ...]
    inputs: tuple[ProjectSQLPlanRef, ...]
    results: tuple[ProjectSQLPlanRef, ...]
    empty_input: ProjectSQLAggregateEmptyInput


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLGroupKey:
    ref: ProjectSQLPlanRef
    aggregation: ProjectSQLPlanRef
    position: int
    source: GroupKey
    reference: Reference
    input: ProjectSQLPlanRef
    result: ProjectSQLPlanRef


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLAggregate:
    ref: ProjectSQLPlanRef
    aggregation: ProjectSQLPlanRef
    position: int
    source: Aggregate
    arguments: tuple[ProjectSQLPlanRef, ...]
    result: ProjectSQLPlanRef
    value_type: ValueType


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLAggregateSite:
    ref: ProjectSQLPlanRef
    owner: ProjectDeclarationOccurrence
    block: ProjectSQLPlanRef
    role: ProjectSQLExpressionRole
    ordinal: int
    occurrence: SelectItem | SatisfyingClause
    expression: Expression
    aggregation: ProjectSQLPlanRef
    authority: ProjectSQLAggregationAuthority
    evidence: Evidence
    references: tuple[Reference, ...]


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLResultReference:
    ref: ProjectSQLPlanRef
    site: ProjectSQLAggregateSite
    expression: Expression
    value_type: ValueType
    reference: Reference
    port: ProjectSQLPlanRef
    symbol: ProjectSQLSymbol


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLAggregateArgumentCall:
    """An original transform inside an admitted aggregate argument only."""

    ref: ProjectSQLPlanRef
    site: ProjectSQLAggregateSite
    expression: CallExpr
    value_type: ValueType
    arguments: tuple[ProjectSQLPlanRef, ...]


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLAggregateProjection:
    ref: ProjectSQLPlanRef
    block: ProjectSQLPlanRef
    aggregation: ProjectSQLPlanRef
    semantic: ProjectModuleSelectFact
    source: Output
    input: ProjectSQLPlanRef
    export: ProjectSQLPlanRef


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLAggregateRisk:
    ref: ProjectSQLPlanRef
    aggregation: ProjectSQLPlanRef
    source: Risk


type Witness = (
    ProjectSQLAggregation
    | ProjectSQLGroupKey
    | ProjectSQLAggregate
    | ProjectSQLAggregateProjection
    | ProjectSQLAggregateRisk
)


class ProjectSQLAggregateDemandKind(StrEnum):
    GROUPING_AND_EMPTY_INPUT = "grouping_and_empty_input"
    GROUP_COMPARISON = "group_comparison"
    AGGREGATE_OPERATION = "aggregate_operation"
    RESULT_PROJECTION = "result_projection"
    RETAINED_RISK = "retained_risk"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLAggregateDemand:
    ref: ProjectSQLPlanRef
    kind: ProjectSQLAggregateDemandKind
    witness: Witness
    subject: ProjectSQLPlanRef
    origin: ProjectSQLPlanRef


def argument_evidence(
    source: Aggregate,
) -> (
    ProjectAggregateExpressionAnalysis | ProjectConcreteJoinedNamespaceExpression | None
):
    return (
        source
        if isinstance(source, ProjectAggregateExpressionAnalysis)
        else source.argument_analysis
    )


def result_type(source: Aggregate) -> ValueType:
    return source.result_value_type


def site_types(site: ProjectSQLAggregateSite) -> Mapping[Expression, ValueType]:
    evidence = site.evidence
    if isinstance(evidence, ProjectAggregateExpressionAnalysis):
        return evidence.argument_value_types
    if isinstance(evidence, SatisfyingResultPredicateInfo):
        return evidence.expression_value_types
    return evidence.value_types


def result_key(site: ProjectSQLAggregateSite, reference: Reference) -> ResultKey:
    if isinstance(reference, ProjectJoinedSatisfyingAggregateReference):
        return reference.aggregate.item
    if isinstance(reference, ProjectJoinedSatisfyingOutputReference):
        item = reference.output.item
    elif isinstance(reference, ProjectRelationClauseDependencyFact) and isinstance(
        reference.target_occurrence, SelectItem
    ):
        item = reference.target_occurrence
    else:
        raise ValueError("Satisfying reference requires its retained result target")
    matches = tuple(
        key
        for output, key in zip(
            site.authority.outputs, site.authority.output_keys, strict=True
        )
        if key is item
        or (
            isinstance(output, ProjectJoinedStageOutputOccurrence)
            and output.item is item
        )
        or (
            isinstance(site.authority.source, ProjectAggregateGroupedClauseReadiness)
            and any(
                selected is item and projected_key is key
                for selected, projected_key in site.authority.source.finalization.group_projections
            )
        )
    )
    if len(matches) != 1:
        raise ValueError("Satisfying target is not one exact aggregate-stage output")
    return matches[0]


def satisfying_effects(value: ProjectSQLAggregationAuthority):
    return (
        value.satisfying.retention_effects
        if isinstance(value.satisfying, ProjectJoinedSatisfyingAnalysis)
        else _SATISFYING_RETENTION_EFFECTS
    )


def arguments(source: Aggregate) -> tuple[Expression, ...]:
    call = source.item.expression
    if not isinstance(call, CallExpr):
        raise ValueError("Aggregate authority requires an original direct call")
    return call.arguments


def retained_members_valid(
    value: ProjectSQLAggregationAuthority, owner: ProjectDeclarationOccurrence
) -> bool:
    """Check original collection membership, without rebuilding any computation."""
    for i, (key, references) in enumerate(
        zip(value.keys, value.key_references, strict=True)
    ):
        if not references:
            return False
        first = references[0]
        if isinstance(key, ProjectGroupKeyFact):
            if (
                not isinstance(first, ProjectModuleExpressionReferenceFact)
                or first.owner is not owner
                or first.role is not ProjectModuleFactOccurrenceRole.GROUP_KEY
                or type(first.container_ordinal) is not int
                or first.container_ordinal != i
                or type(first.dependency_ordinal) is not int
                or first.dependency_ordinal != 0
                or first.status is not ProjectModuleCandidateBucketStatus.CONCRETE
            ):
                return False
            if (
                first.input_field is not None
                and first.input_field is not key.input_field
            ):
                return False
        elif (
            type(key.source_ordinal) is not int
            or key.source_ordinal != i
            or not isinstance(value.source, ProjectConcreteJoinedAggregation)
            or key.input_filter is not value.source.input_filter
            or not isinstance(references[-1], ProjectScalarReferenceResolution)
            or references[-1].target is not key.field_semantics.scalar_field
        ):
            return False
    for reference in value.satisfying_references:
        if isinstance(value.source, ProjectConcreteJoinedAggregation):
            if isinstance(reference, ProjectJoinedSatisfyingOutputReference):
                if not any(
                    reference.output is output for output in value.source.stage_outputs
                ):
                    return False
            elif isinstance(reference, ProjectJoinedSatisfyingAggregateReference):
                if not any(
                    reference.aggregate is aggregate
                    for aggregate in value.source.aggregates
                ):
                    return False
            else:
                return False
        else:
            if (
                not isinstance(reference, ProjectRelationClauseDependencyFact)
                or reference.kind
                is not ProjectRelationClauseDependencyKind.SATISFYING_OUTPUT
            ):
                return False
            candidate = value.source.finalization.candidate
            if candidate is None:
                return False
            matched = tuple(
                result
                for item, result in candidate.selected_results.items()
                if item is reference.target_occurrence
            )
            if (
                len(matched) != 1
                or reference.target_field is not matched[0].field
                or reference.aggregate_result_fact
                is not (
                    matched[0].fact
                    if isinstance(matched[0], ProjectAggregateSelectedResult)
                    else matched[0].aggregate_fact
                )
            ):
                return False
    return True
