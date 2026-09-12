"""Private selected static-source and contextual row SQL planning.

Names are presentation. References belong to one immutable planning scope;
semantic fields, producer definitions and input uses remain distinct.
"""

from __future__ import annotations

from pietto._project import project_sql_plan_aggregation as aggregation
from pietto._project import project_sql_plan_windows as windows

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Never, cast
from collections.abc import Mapping
from types import MappingProxyType
from pietto._project import project_sql_plan_expressions as row
from pietto._project.project_scalar_namespaces import ProjectScalarNamespaceStage
from pietto._project.project_scalar_references import ProjectScalarReferenceResolution
from pietto._project.project_join_conditions import (
    ProjectJoinReferenceState,
    ProjectJoinConditionState,
)
from pietto._project import project_sql_plan_joins as joining
from pietto._project.let_scope_facts import ProjectLetScopeFactsStatus
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleLetBindingFact,
    ProjectModuleWhereReferenceRole,
    ProjectModuleSelectExpressionFact,
    ProjectModuleWhereFact,
    ProjectModuleCandidateBucketStatus,
    ProjectModuleExpressionReferenceFact,
    ProjectModuleFactOccurrenceRole,
)
from pietto._project.project_final_outputs import ProjectNoJoinScalarExpression
from pietto._project.project_joined_row_filter import _SQL_ROW_RETENTION_EFFECTS
from pietto._project.model import ProjectRowField
from pietto.semantic.model import ValueType, ValueTypeKind

from pietto._project.model import (
    ProjectResolvedType,
    ProjectRowFieldNullability,
    ProjectSymbolKind,
)
from pietto._project.module_attribution import (
    ProjectModuleRowFieldIdentity,
    ProjectModuleOriginPath,
)
from pietto._project.module_relation_resolution import (
    ProjectResolvedModuleRelationReference,
    ProjectResolvedModuleRelationSymbol,
    ProjectResolvedSetOperand,
)
from pietto._project.project_relationship_uses import ProjectRelationBindingOccurrence
from pietto._project.project_query_block_ir_algebra import (
    ProjectIRJoinInputCorrespondence,
)
from pietto._project.module_carrier import ProjectCompilationMode, ProjectLogicalModule
from pietto._project.module_catalog import ProjectDeclarationOccurrence
from pietto._project.module_semantic_fact_preservation import ProjectModuleSelectFact
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
)
from pietto._project.project_completion import ProjectCompletionDependency
from pietto._project.project_ir_composition import ProjectIRCrossRelationEdge
from pietto._project.project_ir_operators import (
    ProjectIRLogicalOperatorKind,
    ProjectIRLogicalOperatorOccurrence,
)
from pietto._project.project_ir_relational_properties import (
    ProjectIROutputFieldOccurrence,
)
from pietto._project.project_query_block_ir import (
    ProjectIRQueryBlockEntry,
    ProjectIRConcreteQueryBlockEntry,
    ProjectIRCompletedSetOperationOutput,
    ProjectIRQueryBlockRelationInputEdge,
    ProjectIRSetOperandInput,
    _active_output_identities,
    ProjectIRQueryBlockTerminal,
    ProjectIRReusedEffectiveOutput,
    ProjectIRReboundExistingOutput,
    ProjectIRCompletedQueryBlockOutput,
    ProjectIRQueryBlockOperatorOccurrence,
)
from pietto._project.project_query_block_ir_verification import (
    ProjectIRQueryBlockAnalysisBundle,
)
from pietto.ast_nodes import GroupByItem
from pietto.ast_nodes import (
    AuthoredJoinKind,
    JoinOnClause,
    Expression,
    UnaryExpr,
    BinaryExpr,
    ComparisonExpr,
    BetweenExpr,
    IsNullExpr,
    CallExpr,
    DottedNameExpr,
    FromClause,
    LiteralExpr,
    NameExpr,
    QueryDef,
    SelectItem,
    SetRelationDef,
    SetOperand,
    SourceDef,
    TableDef,
    JoinClause,
    LetBinding,
    WhereClause,
    GroupByClause,
    WindowExpr,
    SatisfyingClause,
    NamedWindowDeclaration,
    QualifyClause,
    DistinctClause,
    OrderByClause,
    LimitClause,
)
from pietto.errors import Diagnostic

__all__: tuple[str, ...] = ()


def _one[T](values: tuple[T, ...], label: str) -> T:
    if len(values) != 1:
        raise ValueError(f"ProjectSQLPlan requires one exact {label}.")
    return values[0]


def _require_roots(
    completed: ProjectConcreteCompletedSemanticResult,
    bundle: ProjectIRQueryBlockAnalysisBundle,
    selected: ProjectDeclarationOccurrence,
) -> ProjectIRQueryBlockEntry:
    if (
        type(completed) is not ProjectConcreteCompletedSemanticResult
        or type(bundle) is not ProjectIRQueryBlockAnalysisBundle
    ):
        raise TypeError("ProjectSQLPlan requires exact completed and analysis roots.")
    root = bundle.root
    if (
        completed.semantic_result.compilation_mode
        is not ProjectCompilationMode.EXPLICIT_MODULES
        or not bundle.verification.verified
        or bundle.verification.issues
        or root.completed is not completed
        or completed.roots.semantic_result is not completed.semantic_result
        or completed.roots.verification is not completed.verification
        or completed.roots.completion is not completed.completion
        or completed.roots.effective_outputs is not completed.effective_outputs
        or root.base_plan is not completed.completion.plan
        or root.base_plan is not completed.verification.root.evaluation.project_plan
        or root.join_stage is not completed.verification.root.join_regions
        or completed.effective_outputs.base is not completed.completion
        or root.owners is not completed.effective_outputs.owners
        or root.dependencies is not completed.effective_outputs.dependencies
        or root.schedule is not completed.effective_outputs.schedule
    ):
        raise ValueError("ProjectSQLPlan roots are not continuous.")
    # These checks inspect retained graph products; they do not resolve semantics.
    root.__post_init__()
    bundle.__post_init__()
    if type(selected) is not ProjectDeclarationOccurrence or not any(
        o is selected for o in root.owners
    ):
        raise ValueError("ProjectSQLPlan selected owner is foreign or absent.")
    if selected.identity.declaration_kind not in {
        ProjectSymbolKind.TABLE,
        ProjectSymbolKind.QUERY,
    }:
        raise ValueError("ProjectSQLPlan selection requires TABLE or QUERY.")
    return _one(root.find_owner(selected), "selected entry")


def _closure(
    bundle: ProjectIRQueryBlockAnalysisBundle, selected: ProjectDeclarationOccurrence
) -> tuple[ProjectIRQueryBlockEntry, ...]:
    # Coordinates index already-owned occurrences; every edge checks object identity.
    root = bundle.root
    owners = {(o.module_position, o.declaration_position): o for o in root.owners}
    incoming: dict[tuple[int, int], list[ProjectCompletionDependency]] = {
        k: [] for k in owners
    }
    for dependency in root.dependencies:
        consumer = (
            dependency.consumer.module_position,
            dependency.consumer.declaration_position,
        )
        target = (
            dependency.target.module_position,
            dependency.target.declaration_position,
        )
        if (
            owners.get(consumer) is not dependency.consumer
            or owners.get(target) is not dependency.target
        ):
            raise ValueError("ProjectSQLPlan dependency has foreign endpoints.")
        incoming[consumer].append(dependency)
    pending = [(selected.module_position, selected.declaration_position)]
    entries_by_owner = {_owner_key(e.owner): e for e in root.entries}
    reached: set[tuple[int, int]] = set()
    while pending:
        key = pending.pop()
        if key not in reached:
            reached.add(key)
            pending.extend(
                (d.target.module_position, d.target.declaration_position)
                for d in incoming[key]
            )
            for join in joining.join_images(root, entries_by_owner[key]):
                for image in join.inputs:
                    producer = image.producer
                    if producer is not None:
                        producer_key = _owner_key(producer)
                        if owners.get(producer_key) is not producer:
                            raise ValueError(
                                "JOIN evidence closure has a foreign producer."
                            )
                        pending.append(producer_key)
    return tuple(
        e
        for e in root.entries
        if (e.owner.module_position, e.owner.declaration_position) in reached
    )


class ProjectSQLPlanBlockerKind(StrEnum):
    EXPRESSION_EVIDENCE = "expression_evidence_unavailable"
    CALL_AUTHORITY = "call_authority_unavailable"
    SEMANTIC_RESULT_UNSUCCESSFUL = "semantic_result_unsuccessful"
    ACTIVE_OUTPUT_UNAVAILABLE = "active_output_unavailable"
    STATIC_SOURCE_UNAVAILABLE = "static_source_unavailable"
    JOIN = "join"
    GROUP = "group"
    SATISFYING = "satisfying"
    WINDOW = "window"
    QUALIFY = "qualify"
    DISTINCT = "distinct"
    ORDER = "order"
    LIMIT = "limit"
    SET_OPERATION = "set_operation"
    IR_STAGE = "ir_stage"


type ProjectSQLBlockedStage = (
    JoinClause
    | JoinOnClause
    | LetBinding
    | WhereClause
    | GroupByClause
    | SatisfyingClause
    | NamedWindowDeclaration
    | QualifyClause
    | SelectItem
    | DistinctClause
    | OrderByClause
    | LimitClause
    | ProjectIRLogicalOperatorOccurrence
    | ProjectIRQueryBlockOperatorOccurrence
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLPlanBlocker:
    position: int
    kind: ProjectSQLPlanBlockerKind
    owner: ProjectDeclarationOccurrence
    evidence: (
        ProjectIRQueryBlockEntry
        | ProjectCompletionDependency
        | ProjectConcreteCompletedSemanticResult
    )
    site: ProjectSQLBlockedStage | None = None


def _operators(
    entry: ProjectIRQueryBlockEntry,
) -> tuple[
    ProjectIRLogicalOperatorOccurrence | ProjectIRQueryBlockOperatorOccurrence, ...
]:
    if isinstance(entry, ProjectIRReusedEffectiveOutput):
        return entry.semantic_entry.fragment.logical_stage.operators
    if isinstance(entry, ProjectIRReboundExistingOutput):
        return entry.rebuilt_fragment.logical_stage.operators
    if isinstance(entry, ProjectIRCompletedQueryBlockOutput):
        return entry.operators
    return ()


def _static_connector(source: SourceDef) -> CallExpr | None:
    call = source.connector
    if (
        type(call) is not CallExpr
        or len(call.arguments) != 1
        or type(call.arguments[0]) is not LiteralExpr
        or type(call.arguments[0].value) is not str
    ):
        return None
    spelling = (
        call.callee.name
        if isinstance(call.callee, NameExpr)
        else ".".join(call.callee.parts)
    )
    return call if spelling in {"postgres.table", "mysql.table"} else None


def _blockers(
    completed: ProjectConcreteCompletedSemanticResult,
    bundle: ProjectIRQueryBlockAnalysisBundle,
    selected: ProjectDeclarationOccurrence,
) -> tuple[ProjectSQLPlanBlocker, ...]:
    result: list[ProjectSQLPlanBlocker] = []

    def add(
        kind: ProjectSQLPlanBlockerKind,
        owner: ProjectDeclarationOccurrence,
        evidence: ProjectIRQueryBlockEntry
        | ProjectCompletionDependency
        | ProjectConcreteCompletedSemanticResult,
        site: ProjectSQLBlockedStage | None = None,
    ) -> None:
        result.append(
            ProjectSQLPlanBlocker(
                position=len(result),
                kind=kind,
                owner=owner,
                evidence=evidence,
                site=site,
            )
        )

    K = ProjectSQLPlanBlockerKind
    if not completed.ok:
        add(K.SEMANTIC_RESULT_UNSUCCESSFUL, selected, completed)
    for entry in _closure(bundle, selected):
        owner, definition = entry.owner, entry.owner.definition
        if isinstance(entry, ProjectIRQueryBlockTerminal):
            add(K.ACTIVE_OUTPUT_UNAVAILABLE, owner, entry)
        if isinstance(definition, SourceDef):
            if _static_connector(definition) is None:
                add(K.STATIC_SOURCE_UNAVAILABLE, owner, entry)
        elif isinstance(definition, SetRelationDef):
            add(K.SET_OPERATION, owner, entry)
        elif isinstance(definition, (TableDef, QueryDef)):
            if joining.joined_tail(entry) is None:
                for clause in definition.join_clauses:
                    add(K.JOIN, owner, entry, clause)
            else:
                for image in joining.join_images(bundle.root, entry):
                    condition = image.condition
                    if condition.expression is not None:
                        blocker = _match_blocker(condition)
                        if blocker is not None:
                            add(blocker, owner, entry, condition.use.clause.on_clause)
            aggregate = (
                aggregation.authority(completed, entry)
                if not isinstance(entry, ProjectIRQueryBlockTerminal)
                else None
            )
            for present, kind in (
                (definition.group_by_clause if aggregate is None else None, K.GROUP),
                (
                    definition.satisfying_clause if aggregate is None else None,
                    K.SATISFYING,
                ),
            ):
                if present:
                    add(kind, owner, entry, present)
            window_view = None
            if not isinstance(entry, ProjectIRQueryBlockTerminal):
                try:
                    window_view = windows.authority(entry)
                    if window_view is not None:
                        for source in windows.sources(window_view):
                            if not windows.ready(source, entry, aggregate):
                                add(K.WINDOW, owner, entry)
                        if window_view.qualify is not None:
                            qualify = window_view.qualify
                            clause = definition.qualify_clause
                            assert clause is not None
                            references = windows.qualifier_references(qualify)
                            terminals = tuple(
                                windows.reference_expression(reference)
                                for reference in references
                            )
                            nodes = row.scalar_nodes(clause.expression, terminals)
                            types = {
                                id(expression): value_type
                                for expression, value_type in windows.qualify_types(
                                    qualify
                                ).items()
                            }
                            if any(isinstance(node, CallExpr) for node in nodes):
                                add(K.CALL_AUTHORITY, owner, entry, clause)
                            elif any(
                                type(node)
                                not in {
                                    LiteralExpr,
                                    NameExpr,
                                    DottedNameExpr,
                                    WindowExpr,
                                    UnaryExpr,
                                    BinaryExpr,
                                    ComparisonExpr,
                                    IsNullExpr,
                                    BetweenExpr,
                                }
                                or id(node) not in types
                                or types[id(node)].kind is not ValueTypeKind.KNOWN
                                for node in nodes
                            ):
                                add(K.EXPRESSION_EVIDENCE, owner, entry, clause)
                            for reference in references:
                                windows.qualify_target(qualify, reference, aggregate)
                except (ValueError, TypeError, AttributeError, KeyError, IndexError):
                    add(K.WINDOW, owner, entry)
            for present, kind in (
                (definition.distinct_clause, K.DISTINCT),
                (definition.order_by_clause, K.ORDER),
                (definition.limit_clause, K.LIMIT),
            ):
                if present:
                    add(kind, owner, entry, present)
            # Capture operator-only stages (e.g. GLOBAL aggregation or inline window).
            for operator in _operators(entry):
                if aggregate is not None and operator.kind in {
                    ProjectIRLogicalOperatorKind.GROUP_AGGREGATE,
                    ProjectIRLogicalOperatorKind.RESULT_FILTER,
                }:
                    continue
                if window_view is not None and operator.kind.value in {
                    "window_evaluation",
                    "qualify",
                }:
                    continue
                if operator.kind not in {
                    ProjectIRLogicalOperatorKind.RELATION_INPUT,
                    ProjectIRLogicalOperatorKind.ROW_FILTER,
                    ProjectIRLogicalOperatorKind.FINAL_PROJECTION,
                }:
                    add(K.IR_STAGE, owner, entry, operator)
            if not isinstance(entry, ProjectIRQueryBlockTerminal):
                for kind, site in _row_blockers(completed, entry):
                    add(kind, owner, entry, site)
    return tuple(result)


def _row_blockers(completed, entry):
    K = ProjectSQLPlanBlockerKind
    authority = row.row_authority(completed, entry)
    definition = entry.owner.definition
    aggregate = aggregation.authority(completed, entry)
    if isinstance(authority, row.ProjectSQLJoinedRowAuthority):
        return (
            *_joined_row_blockers(entry, authority, aggregate is not None),
            *_aggregate_blockers(entry, authority, aggregate),
        )
    if authority is None or authority.let_scope.status not in {
        ProjectLetScopeFactsStatus.ABSENT,
        ProjectLetScopeFactsStatus.CONCRETE,
    }:
        return ((K.EXPRESSION_EVIDENCE, None),)
    if (
        authority.let_scope.definition is not definition
        or authority.let_scope.input_schema is not authority.input_schema
        or any(
            type(fact.binding_ordinal) is not int or fact.binding_ordinal != ordinal
            for ordinal, fact in enumerate(authority.lets)
        )
        or any(
            type(fact.selected_output_ordinal) is not int
            or fact.selected_output_ordinal != ordinal
            for ordinal, fact in enumerate(authority.selections)
        )
    ):
        return ((K.EXPRESSION_EVIDENCE, None),)
    sites: list[
        tuple[
            LetBinding | WhereClause | SelectItem,
            row.ProjectSQLOrdinaryEvidence | None,
            tuple[ProjectModuleExpressionReferenceFact, ...],
        ]
    ] = [(f.binding, f, f.references) for f in authority.lets]
    if definition.where_clause is not None:
        sites.append(
            (definition.where_clause, authority.where, authority.where_references)
        )
    sites.extend(
        (f.item, evidence, refs)
        for f, evidence, refs in zip(
            () if aggregate is not None else authority.selections,
            () if aggregate is not None else authority.selected_evidence,
            () if aggregate is not None else authority.selected_references,
            strict=True,
        )
        if not isinstance(f.item.expression, WindowExpr)
    )
    blockers = []
    input_fields = {id(f): f for f in authority.input_schema.fields.values()}
    binding_ordinals = {id(f.binding): i for i, f in enumerate(authority.lets)}
    selection_ordinals = {id(f.item): i for i, f in enumerate(authority.selections)}
    supported = {
        LiteralExpr,
        NameExpr,
        DottedNameExpr,
        UnaryExpr,
        BinaryExpr,
        ComparisonExpr,
        IsNullExpr,
        BetweenExpr,
    }
    for site, evidence, references in sites:
        nodes = row.scalar_nodes(site.expression)
        if any(isinstance(n, CallExpr) for n in nodes):
            blockers.append((K.CALL_AUTHORITY, site))
        elif evidence is None or any(type(n) not in supported for n in nodes):
            blockers.append((K.EXPRESSION_EVIDENCE, site))
        else:
            if isinstance(site, LetBinding):
                ordinal = binding_ordinals[id(site)]
                role = ProjectModuleFactOccurrenceRole.LET_VALUE
                prefix = authority.let_scope.bindings[:ordinal]
            elif isinstance(site, WhereClause):
                ordinal, role = 0, ProjectModuleWhereReferenceRole.WHERE_VALUE
                prefix = authority.let_scope.bindings
            else:
                ordinal, role = (
                    selection_ordinals[id(site)],
                    ProjectModuleFactOccurrenceRole.SELECT_VALUE,
                )
                prefix = authority.let_scope.bindings
            leaves = tuple(
                n for n in nodes if isinstance(n, (NameExpr, DottedNameExpr))
            )
            references_valid = len(leaves) == len(references) and all(
                r.owner is entry.owner
                and r.expression is leaf
                and r.role is role
                and type(r.container_ordinal) is int
                and r.container_ordinal == ordinal
                and type(r.dependency_ordinal) is int
                and r.dependency_ordinal == i
                and not r.selected_output_candidates
                and all(any(b is p for p in prefix) for b in r.let_candidates)
                and (
                    input_fields.get(id(r.input_field)) is r.input_field
                    if r.input_field is not None
                    else len(r.let_candidates) == 1
                )
                for i, (r, leaf) in enumerate(zip(references, leaves))
            )
            if isinstance(evidence, ProjectModuleLetBindingFact):
                contextual = (
                    evidence.owner is entry.owner
                    and evidence.scope_facts is authority.let_scope
                )
            else:
                contextual = (
                    evidence.owner is entry.owner
                    and evidence.input_schema is authority.input_schema
                    and evidence.let_scope is authority.let_scope
                )
            values = {id(n): (n, v) for n, v in row.evidence_types(evidence).items()}
            if isinstance(evidence, ProjectModuleLetBindingFact):
                contextual = contextual and (
                    evidence.binding_ordinal == ordinal
                    and evidence.value_type
                    is authority.let_scope.value_types.get(evidence.binding.name)
                    and id(site.expression) in values
                    and values[id(site.expression)][1] is evidence.value_type
                )
            if (
                not contextual
                or not references_valid
                or any(
                    id(n) not in values
                    or values[id(n)][0] is not n
                    or values[id(n)][1].kind is not ValueTypeKind.KNOWN
                    for n in nodes
                )
                or any(
                    r.status is not ProjectModuleCandidateBucketStatus.CONCRETE
                    for r in references
                )
            ):
                blockers.append((K.EXPRESSION_EVIDENCE, site))
    return (*blockers, *_aggregate_blockers(entry, authority, aggregate))


def _joined_row_blockers(entry, authority, aggregating=False):
    K = ProjectSQLPlanBlockerKind
    definition = entry.owner.definition
    bindings = () if definition.let_clause is None else definition.let_clause.bindings
    if (
        authority.binding_environment.ledger.owner is not entry.owner
        or authority.namespaces.binding_environment is not authority.binding_environment
        or len(authority.lets) != len(bindings)
        or len(authority.namespaces.binding_namespaces) != len(bindings)
        or len(authority.namespaces.occurrences) != len(bindings)
        or any(
            value.occurrence is not occurrence or occurrence.binding is not binding
            for value, occurrence, binding in zip(
                authority.lets, authority.namespaces.occurrences, bindings
            )
        )
        or len(authority.selections) != len(definition.select_items)
        or (
            not aggregating
            and len(authority.selected_evidence) != len(authority.selections)
        )
        or (
            not aggregating
            and len(authority.selected_references) != len(authority.selections)
        )
        or any(
            fact.item is not item
            for fact, item in zip(authority.selections, definition.select_items)
        )
    ):
        return ((K.EXPRESSION_EVIDENCE, None),)
    if any(
        type(value.occurrence.source_ordinal) is not int
        or value.occurrence.source_ordinal != i
        or type(value.namespace.binding_ordinal) is not int
        or value.namespace.binding_ordinal != i
        or value.namespace is not authority.namespaces.binding_namespaces[i]
        or value.namespace.stage is not ProjectScalarNamespaceStage.LET_BINDING
        or len(value.namespace.let_values) != i
        or any(
            a is not b for a, b in zip(value.namespace.let_values, authority.lets[:i])
        )
        for i, value in enumerate(authority.lets)
    ) or any(
        type(f.selected_output_ordinal) is not int or f.selected_output_ordinal != i
        for i, f in enumerate(authority.selections)
    ):
        return ((K.EXPRESSION_EVIDENCE, None),)
    sites = [
        (value.occurrence.binding, value, value.resolutions) for value in authority.lets
    ]
    if definition.where_clause is not None:
        sites.append(
            (definition.where_clause, authority.where, authority.where_references)
        )
    sites.extend(
        (fact.item, evidence, references)
        for fact, evidence, references in zip(
            () if aggregating else authority.selections,
            () if aggregating else authority.selected_evidence,
            () if aggregating else authority.selected_references,
            strict=True,
        )
        if not isinstance(fact.item.expression, WindowExpr)
    )
    result = []
    for site, evidence, references in sites:
        if evidence is None:
            result.append((K.EXPRESSION_EVIDENCE, site))
            continue
        namespace = evidence.namespace
        if not isinstance(evidence, row.ProjectJoinedLetValue) and (
            namespace is not authority.namespaces.post_let
            or namespace.stage is not ProjectScalarNamespaceStage.POST_LET
            or namespace.binding_ordinal is not None
            or len(namespace.let_values) != len(authority.lets)
            or any(a is not b for a, b in zip(namespace.let_values, authority.lets))
        ):
            result.append((K.EXPRESSION_EVIDENCE, site))
            continue
        leaves = tuple(
            node
            for node in row.scalar_nodes(site.expression)
            if isinstance(node, (NameExpr, DottedNameExpr))
        )
        if (
            namespace.binding_environment is not authority.binding_environment
            or len(leaves) != len(references)
            or any(
                row.reference_expression(reference) is not leaf
                or row.reference_key(reference) is None
                for reference, leaf in zip(references, leaves)
            )
        ):
            result.append((K.EXPRESSION_EVIDENCE, site))
            continue
        references_valid = True
        for resolution in references:
            target = resolution.target
            references_valid &= (
                resolution.reference.environment
                is namespace.binding_environment.scalar_environment
                and target is not None
                and evidence.value_types.get(resolution.reference.expression)
                is target.value_type
            )
            if isinstance(resolution, row.ProjectJoinedLetReferenceResolution):
                references_valid &= resolution.namespace is namespace and any(
                    target is value for value in namespace.let_values
                )
            elif isinstance(resolution, ProjectScalarReferenceResolution):
                references_valid &= (
                    resolution.status is ProjectModuleCandidateBucketStatus.CONCRETE
                    and type(resolution.candidates) is tuple
                    and len(resolution.candidates) == 1
                    and resolution.candidates[0] is target
                    and any(target is field for field in namespace.visible_fields)
                )
            else:
                references_valid = False
        if not references_valid:
            result.append((K.EXPRESSION_EVIDENCE, site))
            continue
        kind = _scalar_blocker(site.expression, evidence)
        if kind is not None:
            result.append((kind, site))
    return tuple(result)


def _aggregate_blockers(entry, rows, aggregate):
    if aggregate is None:
        return ()
    K = ProjectSQLPlanBlockerKind
    if not aggregation.retained_members_valid(aggregate, entry.owner):
        return ((K.EXPRESSION_EVIDENCE, None),)
    definition = entry.owner.definition
    clause = definition.group_by_clause
    expected_keys = () if clause is None else clause.items
    if (
        not aggregate.aggregates
        or len(aggregate.keys) != len(expected_keys)
        or len(aggregate.outputs)
        != sum(
            not isinstance(item.expression, WindowExpr)
            for item in definition.select_items
        )
        or len(aggregate.key_references) != len(aggregate.keys)
        or len(aggregate.argument_references) != len(aggregate.aggregates)
        or (aggregate.mode is aggregation.ProjectJoinedAggregationMode.GROUPED)
        is (clause is None)
        or any(
            key.item is not item
            or not refs
            or row.reference_expression(refs[0]) is not item.key
            for key, item, refs in zip(
                aggregate.keys, expected_keys, aggregate.key_references
            )
        )
    ):
        return ((K.EXPRESSION_EVIDENCE, clause),)
    for source, references in zip(aggregate.aggregates, aggregate.argument_references):
        call = source.item.expression
        if not isinstance(call, CallExpr) or len(call.arguments) > 1:
            return ((K.EXPRESSION_EVIDENCE, source.item),)
        if isinstance(source, aggregation.ProjectAggregateExpressionAnalysis):
            if isinstance(rows, row.ProjectSQLJoinedRowAuthority) or (
                source.definition is not definition
                or source.input_schema is not rows.input_schema
                or source.let_scope is not rows.let_scope
            ):
                return ((K.EXPRESSION_EVIDENCE, source.item),)
        else:
            if (
                type(source.selected_output_ordinal) is not int
                or source.selected_output_ordinal < 0
                or definition.select_items[source.selected_output_ordinal]
                is not source.item
            ):
                return ((K.EXPRESSION_EVIDENCE, source.item),)
        if call.arguments:
            evidence = aggregation.argument_evidence(source)
            if (
                evidence is None
                or _scalar_blocker(call.arguments[0], evidence, source) is not None
            ):
                return ((K.EXPRESSION_EVIDENCE, source.item),)
            leaves = tuple(
                n
                for n in row.scalar_nodes(call.arguments[0])
                if isinstance(n, (NameExpr, DottedNameExpr))
            )
            if len(leaves) != len(references) or any(
                row.reference_expression(r) is not n for r, n in zip(references, leaves)
            ):
                return ((K.EXPRESSION_EVIDENCE, source.item),)
    if definition.satisfying_clause is not None:
        satisfying = aggregate.satisfying
        if (
            satisfying is None
            or aggregate.mode is not aggregation.ProjectJoinedAggregationMode.GROUPED
        ):
            return ((K.SATISFYING, definition.satisfying_clause),)
        values = (
            satisfying.value_types
            if isinstance(satisfying, aggregation.ProjectJoinedSatisfyingAnalysis)
            else satisfying.expression_value_types
        )
        references = aggregate.satisfying_references
        leaves = tuple(row.reference_expression(r) for r in references)
        nodes = row.scalar_nodes(definition.satisfying_clause.expression, leaves)
        expected = tuple(
            n for n in nodes if isinstance(n, (NameExpr, DottedNameExpr, CallExpr))
        )
        if (
            len(expected) != len(leaves)
            or any(a is not b for a, b in zip(expected, leaves))
            or any(
                n not in values or values[n].kind is not ValueTypeKind.KNOWN
                for n in nodes
            )
        ):
            return ((K.EXPRESSION_EVIDENCE, definition.satisfying_clause),)
    return ()


def _match_blocker(condition):
    leaves = tuple(
        node
        for node in row.scalar_nodes(condition.expression)
        if isinstance(node, (NameExpr, DottedNameExpr))
    )
    if (
        condition.ready is not True
        or condition.state is not ProjectJoinConditionState.READY
        or type(condition.use.identity.join_position) is not int
        or len(condition.references) != len(leaves)
        or any(
            type(field.position) is not int or field.position != i
            for i, field in enumerate(condition.environment.fields)
        )
        or any(
            type(reference.position) is not int
            or reference.position != i
            or reference.state is not ProjectJoinReferenceState.RESOLVED
            or reference.expression is not leaf
            or reference.environment is not condition.environment
            or reference.target is None
            or type(reference.candidates) is not tuple
            or len(reference.candidates) != 1
            or reference.candidates[0] is not reference.target
            or condition.value_types.get(leaf) is not reference.target.value_type
            or not any(
                reference.target is field for field in condition.environment.fields
            )
            for i, (reference, leaf) in enumerate(zip(condition.references, leaves))
        )
    ):
        return ProjectSQLPlanBlockerKind.EXPRESSION_EVIDENCE
    return _scalar_blocker(condition.expression, condition)


def _scalar_blocker(expression, evidence, aggregate=None):
    nodes = row.scalar_nodes(expression)
    if any(isinstance(node, CallExpr) for node in nodes) and aggregate is None:
        return ProjectSQLPlanBlockerKind.CALL_AUTHORITY
    if aggregate is not None and (
        aggregation.argument_evidence(aggregate) is not evidence
        or not aggregation.arguments(aggregate)
        or aggregation.arguments(aggregate)[0] is not expression
    ):
        return ProjectSQLPlanBlockerKind.EXPRESSION_EVIDENCE
    supported = {
        LiteralExpr,
        NameExpr,
        DottedNameExpr,
        UnaryExpr,
        BinaryExpr,
        ComparisonExpr,
        IsNullExpr,
        BetweenExpr,
    }
    if aggregate is not None:
        supported.add(CallExpr)
    values = {
        id(node): (node, value) for node, value in row.evidence_types(evidence).items()
    }
    if any(
        type(node) not in supported
        or id(node) not in values
        or values[id(node)][0] is not node
        or values[id(node)][1].kind is not ValueTypeKind.KNOWN
        for node in nodes
    ):
        return ProjectSQLPlanBlockerKind.EXPRESSION_EVIDENCE
    return None


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLPlanUnavailable:
    completed: ProjectConcreteCompletedSemanticResult
    analysis_bundle: ProjectIRQueryBlockAnalysisBundle
    selected_owner: ProjectDeclarationOccurrence
    blockers: tuple[ProjectSQLPlanBlocker, ...] = field(init=False)
    plan: None = field(init=False, default=None)

    def __post_init__(self) -> None:
        _require_roots(self.completed, self.analysis_bundle, self.selected_owner)
        blockers = _blockers(self.completed, self.analysis_bundle, self.selected_owner)
        if not blockers:
            raise ValueError("Unavailable planning requires actual blockers.")
        object.__setattr__(self, "blockers", blockers)

    @property
    def diagnostics(self) -> tuple[Diagnostic, ...]:
        return self.completed.diagnostics


class ProjectSQLPlanRefKind(StrEnum):
    WINDOW = "window"
    WINDOW_USE = "window_use"
    WINDOW_ARGUMENT = "window_argument"
    WINDOW_POLICY = "window_policy"
    WINDOW_PROJECTION = "window_projection"
    AGGREGATION = "aggregation"
    GROUP_KEY = "group_key"
    AGGREGATE = "aggregate"
    AGGREGATE_PROJECTION = "aggregate_projection"
    AGGREGATE_RISK = "aggregate_risk"
    JOIN = "join"
    JOIN_INPUT = "join_input"
    JOIN_PORT = "join_port"
    RELATIONSHIP_MATCH = "relationship_match"
    JOIN_TAIL = "join_tail"
    SINGLE_MATCH = "single_match"
    SINGLE_MATCH_PROOF = "single_match_proof"
    SELECT_BLOCK = "select_block"
    EXPRESSION_SITE = "expression_site"
    EXPRESSION = "expression"
    OPERAND = "operand"
    STAGE_PORT = "stage_port"
    LET_VALUE = "let_value"
    FILTER = "filter"
    DEFINITION = "definition"
    INPUT_USE = "input_use"
    SOURCE_PORT = "source_port"
    INPUT_PORT = "input_port"
    EXPORT = "export"
    PROJECTION = "projection"
    BOUNDARY = "boundary"
    SYMBOL = "symbol"
    ORIGIN = "origin"
    DEMAND = "demand"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLPlanScope:
    completed: ProjectConcreteCompletedSemanticResult
    analysis_bundle: ProjectIRQueryBlockAnalysisBundle
    selected_owner: ProjectDeclarationOccurrence


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLPlanRef:
    scope: ProjectSQLPlanScope
    kind: ProjectSQLPlanRefKind
    position: int


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLPort:
    ref: ProjectSQLPlanRef
    owner: ProjectSQLPlanRef
    field: ProjectIROutputFieldOccurrence
    identity: ProjectModuleRowFieldIdentity
    producer_port: ProjectSQLPlanRef | None = None


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLDefinition:
    """An upstream named value, not an assertion of a SQL SELECT body."""

    ref: ProjectSQLPlanRef
    entry: ProjectIRConcreteQueryBlockEntry
    exports: tuple[ProjectSQLPort, ...]


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLSourceBinding:
    ref: ProjectSQLPlanRef
    source: ProjectIRReusedEffectiveOutput
    module: ProjectLogicalModule
    declaration: SourceDef
    connector: CallExpr


type ProjectSQLInputEdge = (
    ProjectIRCrossRelationEdge
    | ProjectIRQueryBlockRelationInputEdge
    | ProjectIRSetOperandInput
    | ProjectIRJoinInputCorrespondence
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLInputUse:
    ref: ProjectSQLPlanRef
    producer: ProjectSQLPlanRef
    consumer: ProjectSQLPlanRef
    edge: ProjectSQLInputEdge
    dependency: ProjectCompletionDependency
    binding: ProjectResolvedModuleRelationSymbol
    origin_path: ProjectModuleOriginPath
    ports: tuple[ProjectSQLPort, ...]


class ProjectSQLBoundaryReason(StrEnum):
    SOURCE_INPUT = "source_input"
    NAMED_INPUT = "named_input"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLBoundary:
    ref: ProjectSQLPlanRef
    use: ProjectSQLInputUse
    reason: ProjectSQLBoundaryReason


class ProjectSQLSymbolNamespace(StrEnum):
    RELATION_USE = "relation_use"
    FIELD_PORT = "field_port"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLSymbol:
    ref: ProjectSQLPlanRef
    scope: ProjectSQLPlanRef
    namespace: ProjectSQLSymbolNamespace
    position: int
    subject: ProjectSQLPlanRef
    label: str


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLSelectBlock:
    ref: ProjectSQLPlanRef
    definition: ProjectSQLPlanRef
    position: int
    kind: row.ProjectSQLStageKind
    predecessor: ProjectSQLPlanRef
    inputs: tuple[ProjectSQLPlanRef, ...]
    exports: tuple[ProjectSQLPlanRef, ...]
    selected: ProjectIRConcreteQueryBlockEntry
    operators: tuple[
        ProjectIRLogicalOperatorOccurrence | ProjectIRQueryBlockOperatorOccurrence, ...
    ]
    boundary: ProjectSQLBoundary | joining.ProjectSQLJoinTail


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLProjection:
    ref: ProjectSQLPlanRef
    block: ProjectSQLPlanRef
    input_use: ProjectSQLPlanRef | None
    source_port: ProjectSQLPlanRef | None
    input_port: ProjectSQLPlanRef | None
    export: ProjectSQLPlanRef
    semantic: ProjectModuleSelectFact
    symbol: ProjectSQLSymbol | None
    expression: ProjectSQLPlanRef
    site: row.ProjectSQLExpressionSite | row.ProjectSQLJoinedSite


class ProjectSQLOriginRole(StrEnum):
    WINDOW = "window"
    WINDOW_USE = "window_use"
    WINDOW_ARGUMENT = "window_argument"
    WINDOW_POLICY = "window_policy"
    WINDOW_PROJECTION = "window_projection"
    AGGREGATION = "aggregation"
    GROUP_KEY = "group_key"
    AGGREGATE = "aggregate"
    AGGREGATE_PROJECTION = "aggregate_projection"
    AGGREGATE_RISK = "aggregate_risk"
    JOIN = "join"
    JOIN_INPUT = "join_input"
    JOIN_PORT = "join_port"
    RELATIONSHIP_MATCH = "relationship_match"
    JOIN_TAIL = "join_tail"
    SINGLE_MATCH = "single_match"
    SINGLE_MATCH_PROOF = "single_match_proof"
    EXPRESSION_SITE = "expression_site"
    EXPRESSION = "expression"
    OPERAND = "operand"
    STAGE_PORT = "stage_port"
    LET_VALUE = "let_value"
    FILTER = "filter"
    SELECTED_OWNER = "selected_owner"
    DEFINITION = "definition"
    SOURCE_DESCRIPTOR = "source_descriptor"
    INPUT_USE = "input_use"
    SELECT_BLOCK = "select_block"
    SOURCE_PORT = "source_port"
    INPUT_PORT = "input_port"
    STAGE_EXPORT = "stage_export"
    PROJECTION = "projection"
    EXPORT = "export"
    BOUNDARY = "boundary"
    SYMBOL = "symbol"
    DEMAND = "demand"


class ProjectSQLOriginProvenance(StrEnum):
    VALUE = "value"
    MEMBERSHIP = "membership"
    TYPE_PROOF = "type_proof"
    GENERATED_STRUCTURE = "generated_structure"


type ProjectSQLCause = (
    JoinOnClause
    | SourceDef
    | TableDef
    | QueryDef
    | SetRelationDef
    | FromClause
    | JoinClause
    | SetOperand
    | SelectItem
    | LetBinding
    | WhereClause
    | Expression
    | aggregation.SatisfyingClause
    | GroupByItem
)

type ProjectSQLOriginEvidence = (
    windows.Witness
    | windows.Qualify
    | aggregation.Witness
    | aggregation.Evidence
    | aggregation.GroupKey
    | aggregation.Output
    | aggregation.Risk
    | row.ProjectSQLScalarEvidence
    | joining.ProjectSQLJoinWitness
    | ProjectDeclarationOccurrence
    | ProjectIRQueryBlockEntry
    | ProjectCompletionDependency
    | ProjectModuleSelectFact
    | ProjectIROutputFieldOccurrence
    | ProjectModuleLetBindingFact
    | ProjectModuleWhereFact
    | ProjectModuleSelectExpressionFact
    | ProjectNoJoinScalarExpression
    | ValueType
    | ProjectRowField
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLOrigin:
    ref: ProjectSQLPlanRef
    subject: ProjectSQLPlanScope | ProjectSQLPlanRef
    role: ProjectSQLOriginRole
    provenance: ProjectSQLOriginProvenance
    owner: ProjectDeclarationOccurrence
    cause: ProjectSQLCause
    evidence: ProjectSQLOriginEvidence
    antecedents: tuple[ProjectSQLPlanRef, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLSourceRealizationDemand:
    ref: ProjectSQLPlanRef
    subject: ProjectSQLPlanRef
    source: ProjectSQLSourceBinding
    origin: ProjectSQLPlanRef


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLExportRepresentationDemand:
    ref: ProjectSQLPlanRef
    subject: ProjectSQLPlanRef
    field: ProjectIROutputFieldOccurrence
    logical_type: ProjectResolvedType
    nullability: ProjectRowFieldNullability
    origin: ProjectSQLPlanRef


type ProjectSQLDemand = (
    ProjectSQLSourceRealizationDemand
    | ProjectSQLExportRepresentationDemand
    | row.ProjectSQLExpressionDemand
    | row.ProjectSQLStageValueDemand
    | row.ProjectSQLFilterDemand
    | row.ProjectSQLScopeDemand
    | joining.ProjectSQLJoinDemand
    | aggregation.ProjectSQLAggregateDemand
    | windows.ProjectSQLWindowDemand
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False, init=False)
class ProjectSQLBindings:
    scope: ProjectSQLPlanScope
    definitions: tuple[ProjectSQLDefinition, ...]
    sources: tuple[ProjectSQLSourceBinding, ...]
    input_uses: tuple[ProjectSQLInputUse, ...]
    source_ports: tuple[ProjectSQLPort, ...]
    input_ports: tuple[ProjectSQLPort, ...]
    all_exports: tuple[ProjectSQLPort, ...]
    boundaries: tuple[ProjectSQLBoundary, ...]
    symbols: tuple[ProjectSQLSymbol, ...]
    origins: tuple[ProjectSQLOrigin, ...]
    demands: tuple[ProjectSQLDemand, ...]

    def __init__(self) -> Never:
        raise TypeError("SQL bindings are closed; use build_project_sql_bindings.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False, init=False)
class ProjectSQLPlan:
    scope: ProjectSQLPlanScope
    bindings: ProjectSQLBindings
    sources: tuple[ProjectSQLSourceBinding, ...]
    blocks: tuple[ProjectSQLSelectBlock, ...]
    input_uses: tuple[ProjectSQLInputUse, ...]
    source_ports: tuple[ProjectSQLPort, ...]
    input_ports: tuple[ProjectSQLPort, ...]
    all_exports: tuple[ProjectSQLPort, ...]
    exports: tuple[ProjectSQLPort, ...]
    projections: tuple[ProjectSQLProjection, ...]
    boundaries: tuple[ProjectSQLBoundary, ...]
    symbols: tuple[ProjectSQLSymbol, ...]
    origins: tuple[ProjectSQLOrigin, ...]
    demands: tuple[ProjectSQLDemand, ...]
    expression_sites: tuple[row.ProjectSQLSite, ...]
    expressions: tuple[row.ProjectSQLExpression, ...]
    operands: tuple[row.ProjectSQLExpressionOperand, ...]
    stage_ports: tuple[row.ProjectSQLStagePort, ...]
    let_values: tuple[row.ProjectSQLLetValue, ...]
    filters: tuple[row.ProjectSQLFilter, ...]
    joins: tuple[joining.ProjectSQLJoin, ...]
    join_inputs: tuple[joining.ProjectSQLJoinInput, ...]
    join_ports: tuple[joining.ProjectSQLJoinPort, ...]
    relationship_matches: tuple[joining.ProjectSQLRelationshipMatch, ...]
    join_tails: tuple[joining.ProjectSQLJoinTail, ...]
    single_matches: tuple[joining.ProjectSQLSingleMatch, ...]
    single_match_proofs: tuple[joining.ProjectSQLSingleMatchProof, ...]
    aggregations: tuple[aggregation.ProjectSQLAggregation, ...]
    group_keys: tuple[aggregation.ProjectSQLGroupKey, ...]
    aggregates: tuple[aggregation.ProjectSQLAggregate, ...]
    aggregate_projections: tuple[aggregation.ProjectSQLAggregateProjection, ...]
    aggregate_risks: tuple[aggregation.ProjectSQLAggregateRisk, ...]
    windows: tuple[windows.ProjectSQLWindow, ...]
    window_uses: tuple[windows.ProjectSQLWindowUse, ...]
    window_arguments: tuple[windows.ProjectSQLWindowArgument, ...]
    window_policies: tuple[windows.ProjectSQLWindowPolicy, ...]
    window_projections: tuple[windows.ProjectSQLWindowProjection, ...]

    def __init__(self) -> Never:
        raise TypeError("ProjectSQLPlan is closed; use build_project_sql_plan.")

    @property
    def diagnostics(self) -> tuple[Diagnostic, ...]:
        return self.scope.completed.diagnostics


def _owner_key(owner: ProjectDeclarationOccurrence) -> tuple[int, int]:
    return owner.module_position, owner.declaration_position


def _dependency_symbol(
    dependency: ProjectCompletionDependency,
) -> ProjectResolvedModuleRelationSymbol:
    evidence = dependency.evidence
    symbol = (
        evidence.target
        if isinstance(evidence, ProjectRelationBindingOccurrence)
        else evidence.target_symbol
    )
    if symbol is None or symbol.target_occurrence is not dependency.target:
        raise ValueError("Input binding requires an exact resolved target.")
    return symbol


def _dependency_site(
    dependency: ProjectCompletionDependency,
) -> FromClause | JoinClause | SetOperand:
    evidence = dependency.evidence
    if isinstance(evidence, ProjectRelationBindingOccurrence):
        return evidence.site
    if isinstance(evidence, ProjectResolvedSetOperand):
        return evidence.reference.operand
    return evidence.reference.from_clause


def _binding_label(dependency: ProjectCompletionDependency) -> str:
    evidence = dependency.evidence
    return (
        evidence.name
        if isinstance(evidence, ProjectRelationBindingOccurrence)
        else _dependency_symbol(dependency).local_name
    )


def _origin_index(
    scope: ProjectSQLPlanScope,
) -> dict[tuple[str, int, int], ProjectModuleOriginPath]:
    """Index existing complete origin paths; no path construction or name lookup."""
    result: dict[tuple[str, int, int], ProjectModuleOriginPath] = {}
    attribution = scope.analysis_bundle.root.base_plan.attribution
    for origin in attribution.origins:
        if origin.import_occurrence is not None:
            occurrence = origin.import_occurrence
            key = (
                origin.owning_module_path,
                occurrence.module_statement_position,
                occurrence.item_position,
            )
        else:
            assert origin.local_occurrence is not None
            occurrence = origin.local_occurrence
            key = (origin.owning_module_path, -1, occurrence.declaration_position)
        if key in result:
            raise ValueError("Origin occurrence index must not choose a winner.")
        result[key] = origin
    return result


def _binding_origin(
    symbol: ProjectResolvedModuleRelationSymbol,
    index: Mapping[tuple[str, int, int], ProjectModuleOriginPath],
) -> ProjectModuleOriginPath:
    imported = symbol.imported_binding
    key = (
        (
            imported.identity.owning_module_path,
            imported.request.module_statement_position,
            imported.request.item_position,
        )
        if imported is not None
        else (
            symbol.owning_module_path,
            -1,
            symbol.target_occurrence.declaration_position,
        )
    )
    origin = index.get(key)
    if (
        origin is None
        or origin.target_occurrence.identity is not symbol.target_occurrence.identity
    ):
        raise ValueError("Resolved binding requires its retained defining origin path.")
    return origin


def _root_inventory(
    scope: ProjectSQLPlanScope,
) -> tuple[
    tuple[ProjectIRConcreteQueryBlockEntry, ...],
    tuple[ProjectCompletionDependency, ...],
    tuple[ProjectSQLInputEdge, ...],
]:
    """Read exact upstream ledgers/active edges, without allocating plan records."""
    root = scope.analysis_bundle.root
    reached = {
        _owner_key(e.owner): e
        for e in _closure(scope.analysis_bundle, scope.selected_owner)
    }
    entries = tuple(
        reached[_owner_key(o)] for o in root.schedule if _owner_key(o) in reached
    )
    if len(entries) != len(reached) or any(
        isinstance(e, ProjectIRQueryBlockTerminal) for e in entries
    ):
        raise ValueError("Bindings require every exact active upstream entry.")
    concrete = cast(tuple[ProjectIRConcreteQueryBlockEntry, ...], entries)
    dependencies = tuple(
        d for d in root.dependencies if _owner_key(d.consumer) in reached
    )
    historical: dict[tuple[int, int], list[ProjectIRCrossRelationEdge]] = {}
    for edge in root.base_plan.cross_relation_edges:
        historical.setdefault(
            _owner_key(edge.consumer.semantic_facts.owner), []
        ).append(edge)
    by_owner = {_owner_key(e.owner): e for e in concrete}
    per_owner: dict[tuple[int, int], list[ProjectCompletionDependency]] = {}
    for dep in dependencies:
        dep.__post_init__()
        per_owner.setdefault(_owner_key(dep.consumer), []).append(dep)
    images: dict[tuple[tuple[int, int], int], ProjectSQLInputEdge] = {}
    for entry in concrete:
        key = _owner_key(entry.owner)
        deps = per_owner.get(key, ())
        if isinstance(entry.owner.definition, SourceDef):
            if deps:
                raise ValueError("A source definition cannot have relation inputs.")
            continue
        if isinstance(entry, ProjectIRReusedEffectiveOutput):
            edge = _one(tuple(historical.get(key, ())), "historical cross edge")
            if len(deps) != 1 or edge.consumer is not entry.semantic_entry.fragment:
                raise ValueError("Historical consumer requires one exact cross edge.")
            images[(key, deps[0].dependency_ordinal)] = edge
        elif isinstance(entry, ProjectIRCompletedSetOperationOutput):
            if len(deps) != len(entry.operands):
                raise ValueError("Set bindings must retain every operand occurrence.")
            for dep, operand in zip(deps, entry.operands, strict=True):
                if operand.source.resolution is not dep.evidence:
                    raise ValueError(
                        "Set binding lost its original operand resolution."
                    )
                images[(key, dep.dependency_ordinal)] = operand
        elif entry.relation_input is not None:
            if (
                len(deps) != 1
                or entry.relation_input.dependency is not deps[0]
                or entry.relation_input.producer
                is not by_owner[_owner_key(deps[0].target)].active_properties
            ):
                raise ValueError("Rebound input must use its active relation edge.")
            images[(key, deps[0].dependency_ordinal)] = entry.relation_input
        elif joining.joined_tail(entry) is not None:
            joined_images = joining.join_images(root, entry)
            tail = joining.joined_tail(entry)
            assert tail is not None
            visible_bindings = (
                tail.joined_semantics.namespaces.binding_environment.bindings
            )
            external = tuple(
                i for j in joined_images for i in j.inputs if i.producer is not None
            )
            selected: list[ProjectIRJoinInputCorrespondence] = []
            for dep in deps:
                binding = dep.evidence
                if not isinstance(binding, ProjectRelationBindingOccurrence):
                    raise ValueError(
                        "JOIN input requires the original binding occurrence."
                    )
                visible = _one(
                    tuple(v for v in visible_bindings if v.binding is binding),
                    "authored JOIN binding",
                )
                matches = tuple(
                    image
                    for image in external
                    if image.source is visible.introduction_use
                )
                image = _one(matches, "authored JOIN input image")
                if image.producer is not dep.target:
                    raise ValueError("JOIN input image has a different named producer.")
                selected.append(image)
                images[(key, dep.dependency_ordinal)] = image
            # Hidden path hops have real external inputs, but no authored alias/use.
            # They are retained by JOIN input images, never forged dependencies.
            hidden = tuple(
                image
                for image in external
                if not any(image is item for item in selected)
            )
            for image in hidden:
                matches = tuple(j for j in joined_images if j.inputs[1] is image)
                joined = _one(matches, "hidden path input")
                source = joined.source
                from pietto._project.project_ir_joins import (
                    ProjectIRBinaryJoinOccurrence,
                )

                if (
                    not isinstance(source, ProjectIRBinaryJoinOccurrence)
                    or source.path_step is source.use.path.steps[-1]
                ):
                    raise ValueError(
                        "Unbound external input requires a nonterminal path hop."
                    )
            if tuple(
                id(image)
                for image in external
                if any(image is item for item in selected)
            ) != tuple(id(image) for image in selected):
                raise ValueError("Authored JOIN input images lost their order.")
        else:
            raise ValueError("Active input correspondence is unavailable.")
    return (
        concrete,
        dependencies,
        tuple(
            images[(_owner_key(d.consumer), d.dependency_ordinal)] for d in dependencies
        ),
    )


def _field_site(
    entry: ProjectIRConcreteQueryBlockEntry, position: int
) -> SourceDef | TableDef | QueryDef | SetRelationDef | SelectItem:
    definition = entry.owner.definition
    if isinstance(definition, (TableDef, QueryDef)) and len(
        definition.select_items
    ) == len(entry.active_properties.relational.fields):
        return definition.select_items[position]
    if isinstance(definition, (SourceDef, TableDef, QueryDef, SetRelationDef)):
        return definition
    raise ValueError("Only relation definitions own exported fields.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLBlockContext:
    """Invocation-local lookup indexes; labels are never lookup authority."""

    definition: ProjectSQLDefinition
    symbols: Mapping[ProjectSQLPlanRef, ProjectSQLSymbol]
    subjects: Mapping[ProjectSQLPlanRef, ProjectSQLInputUse | ProjectSQLPort]

    def lookup(
        self, reference: ProjectSQLPlanRef
    ) -> ProjectSQLInputUse | ProjectSQLPort:
        symbol = self.symbols.get(reference)
        if (
            symbol is None
            or symbol.ref is not reference
            or symbol.scope is not self.definition.ref
        ):
            raise ValueError("Symbol does not belong to this block scope.")
        subject = self.subjects.get(symbol.subject)
        if subject is None or subject.ref is not symbol.subject:
            raise ValueError("Symbol subject is not a member of this block scope.")
        if type(symbol.namespace) is not ProjectSQLSymbolNamespace or (
            symbol.namespace is ProjectSQLSymbolNamespace.RELATION_USE
        ) is not isinstance(subject, ProjectSQLInputUse):
            raise ValueError("Symbol namespace does not match its subject role.")
        return subject


def _binding_contexts(
    bindings: ProjectSQLBindings,
) -> dict[ProjectSQLPlanRef, ProjectSQLBlockContext]:
    subjects: dict[
        ProjectSQLPlanRef, dict[ProjectSQLPlanRef, ProjectSQLInputUse | ProjectSQLPort]
    ] = {d.ref: {p.ref: p for p in d.exports} for d in bindings.definitions}
    symbols: dict[ProjectSQLPlanRef, dict[ProjectSQLPlanRef, ProjectSQLSymbol]] = {
        d.ref: {} for d in bindings.definitions
    }
    for use in bindings.input_uses:
        bucket = subjects[use.consumer]
        bucket[use.ref] = use
        bucket.update((p.ref, p) for p in use.ports)
    for symbol in bindings.symbols:
        symbols[symbol.scope][symbol.ref] = symbol
    return {
        d.ref: ProjectSQLBlockContext(
            definition=d,
            symbols=MappingProxyType(symbols[d.ref]),
            subjects=MappingProxyType(subjects[d.ref]),
        )
        for d in bindings.definitions
    }


def build_project_sql_bindings(
    completed: ProjectConcreteCompletedSemanticResult,
    analysis_bundle: ProjectIRQueryBlockAnalysisBundle,
    selected_owner: ProjectDeclarationOccurrence,
) -> ProjectSQLBindings | ProjectSQLPlanUnavailable:
    """The real planner's binding seam; binding success never certifies SQL bodies."""
    _require_roots(completed, analysis_bundle, selected_owner)
    prerequisites = {
        ProjectSQLPlanBlockerKind.SEMANTIC_RESULT_UNSUCCESSFUL,
        ProjectSQLPlanBlockerKind.ACTIVE_OUTPUT_UNAVAILABLE,
        ProjectSQLPlanBlockerKind.STATIC_SOURCE_UNAVAILABLE,
    }
    if any(
        b.kind in prerequisites
        for b in _blockers(completed, analysis_bundle, selected_owner)
    ):
        return ProjectSQLPlanUnavailable(
            completed=completed,
            analysis_bundle=analysis_bundle,
            selected_owner=selected_owner,
        )
    scope = ProjectSQLPlanScope(
        completed=completed,
        analysis_bundle=analysis_bundle,
        selected_owner=selected_owner,
    )
    entries, dependencies, edges = _root_inventory(scope)
    K = ProjectSQLPlanRefKind
    counters = {kind: 0 for kind in K}

    def ref(kind: ProjectSQLPlanRefKind) -> ProjectSQLPlanRef:
        value = ProjectSQLPlanRef(scope=scope, kind=kind, position=counters[kind])
        counters[kind] += 1
        return value

    definitions: list[ProjectSQLDefinition] = []
    sources: list[ProjectSQLSourceBinding] = []
    for entry in entries:
        definition_ref = ref(K.DEFINITION)
        is_source = isinstance(entry.owner.definition, SourceDef)
        identities = _active_output_identities(entry.active_output)
        ports = tuple(
            ProjectSQLPort(
                ref=ref(K.SOURCE_PORT if is_source else K.EXPORT),
                owner=definition_ref,
                field=f,
                identity=identity,
            )
            for f, identity in zip(
                entry.active_properties.relational.fields, identities, strict=True
            )
        )
        definitions.append(
            ProjectSQLDefinition(ref=definition_ref, entry=entry, exports=ports)
        )
        if is_source:
            source_def = cast(SourceDef, entry.owner.definition)
            connector = _static_connector(source_def)
            if (
                not isinstance(entry, ProjectIRReusedEffectiveOutput)
                or connector is None
            ):
                raise ValueError("Static source binding lacks exact authority.")
            module = completed.semantic_result.modules[entry.owner.module_position]
            sources.append(
                ProjectSQLSourceBinding(
                    ref=definition_ref,
                    source=entry,
                    module=module,
                    declaration=source_def,
                    connector=connector,
                )
            )
    by_owner = {_owner_key(d.entry.owner): d for d in definitions}
    uses: list[ProjectSQLInputUse] = []
    origin_index = _origin_index(scope)
    for dependency, edge in zip(dependencies, edges, strict=True):
        producer, consumer = (
            by_owner[_owner_key(dependency.target)],
            by_owner[_owner_key(dependency.consumer)],
        )
        if edge.use.output is not producer.entry.active_output.occurrence:
            raise ValueError("Binding must consume the actual active producer output.")
        use_ref = ref(K.INPUT_USE)
        ports = tuple(
            ProjectSQLPort(
                ref=ref(K.INPUT_PORT),
                owner=use_ref,
                field=p.field,
                identity=p.identity,
                producer_port=p.ref,
            )
            for p in producer.exports
        )
        binding = _dependency_symbol(dependency)
        uses.append(
            ProjectSQLInputUse(
                ref=use_ref,
                producer=producer.ref,
                consumer=consumer.ref,
                edge=edge,
                dependency=dependency,
                binding=binding,
                origin_path=_binding_origin(binding, origin_index),
                ports=ports,
            )
        )
    by_ref = {d.ref: d for d in definitions}
    boundaries = tuple(
        ProjectSQLBoundary(
            ref=ref(K.BOUNDARY),
            use=u,
            reason=ProjectSQLBoundaryReason.SOURCE_INPUT
            if isinstance(by_ref[u.producer].entry.owner.definition, SourceDef)
            else ProjectSQLBoundaryReason.NAMED_INPUT,
        )
        for u in uses
    )
    per_consumer: dict[ProjectSQLPlanRef, list[ProjectSQLInputUse]] = {
        d.ref: [] for d in definitions
    }
    for use in uses:
        per_consumer[use.consumer].append(use)
    symbols: list[ProjectSQLSymbol] = []
    for definition in definitions:
        local_uses = per_consumer[definition.ref]
        for i, use in enumerate(local_uses):
            symbols.append(
                ProjectSQLSymbol(
                    ref=ref(K.SYMBOL),
                    scope=definition.ref,
                    namespace=ProjectSQLSymbolNamespace.RELATION_USE,
                    position=i,
                    subject=use.ref,
                    label=_binding_label(use.dependency),
                )
            )
        for i, port in enumerate(
            (*[p for u in local_uses for p in u.ports], *definition.exports)
        ):
            symbols.append(
                ProjectSQLSymbol(
                    ref=ref(K.SYMBOL),
                    scope=definition.ref,
                    namespace=ProjectSQLSymbolNamespace.FIELD_PORT,
                    position=i,
                    subject=port.ref,
                    label=port.identity.name,
                )
            )
    origins: list[ProjectSQLOrigin] = []
    R, P = ProjectSQLOriginRole, ProjectSQLOriginProvenance

    def origin(
        subject: ProjectSQLPlanScope | ProjectSQLPlanRef,
        role: ProjectSQLOriginRole,
        provenance: ProjectSQLOriginProvenance,
        owner: ProjectDeclarationOccurrence,
        cause: ProjectSQLCause,
        evidence: ProjectSQLOriginEvidence,
        antecedents: tuple[ProjectSQLPlanRef, ...] = (),
    ) -> ProjectSQLPlanRef:
        value = ProjectSQLOrigin(
            ref=ref(K.ORIGIN),
            subject=subject,
            role=role,
            provenance=provenance,
            owner=owner,
            cause=cause,
            evidence=evidence,
            antecedents=antecedents,
        )
        origins.append(value)
        return value.ref

    origin(
        scope,
        R.SELECTED_OWNER,
        P.GENERATED_STRUCTURE,
        selected_owner,
        cast(TableDef | QueryDef | SetRelationDef, selected_owner.definition),
        selected_owner,
    )
    for definition in definitions:
        entry = definition.entry
        origin(
            definition.ref,
            R.DEFINITION,
            P.GENERATED_STRUCTURE,
            entry.owner,
            cast(
                SourceDef | TableDef | QueryDef | SetRelationDef, entry.owner.definition
            ),
            entry,
        )
        for i, port in enumerate(definition.exports):
            origin(
                port.ref,
                R.SOURCE_PORT
                if isinstance(entry.owner.definition, SourceDef)
                else R.STAGE_EXPORT,
                P.VALUE,
                entry.owner,
                _field_site(entry, i),
                port.field,
                (definition.ref,),
            )
    for source in sources:
        origin(
            source.ref,
            R.SOURCE_DESCRIPTOR,
            P.GENERATED_STRUCTURE,
            source.source.owner,
            source.declaration,
            source.source.owner,
        )
    input_by_ref = {u.ref: u for u in uses}
    for use in uses:
        dep = use.dependency
        provenance = (
            P.GENERATED_STRUCTURE
            if isinstance(dep.evidence, ProjectResolvedModuleRelationReference)
            else P.MEMBERSHIP
        )
        origin(
            use.ref,
            R.INPUT_USE,
            provenance,
            dep.consumer,
            _dependency_site(dep),
            dep,
            (use.producer,),
        )
        for port in use.ports:
            assert port.producer_port is not None
            origin(
                port.ref,
                R.INPUT_PORT,
                P.VALUE,
                dep.consumer,
                _dependency_site(dep),
                port.field,
                (use.ref, port.producer_port),
            )
    for boundary in boundaries:
        dep = boundary.use.dependency
        origin(
            boundary.ref,
            R.BOUNDARY,
            P.GENERATED_STRUCTURE,
            dep.consumer,
            _dependency_site(dep),
            dep,
            (boundary.use.ref,),
        )
    ports_by_ref = {p.ref: p for d in definitions for p in d.exports} | {
        p.ref: p for u in uses for p in u.ports
    }
    for symbol in symbols:
        owner = by_ref[symbol.scope].entry.owner
        if symbol.namespace is ProjectSQLSymbolNamespace.RELATION_USE:
            dep = input_by_ref[symbol.subject].dependency
            cause, evidence = _dependency_site(dep), dep
        else:
            port = ports_by_ref[symbol.subject]
            cause = (
                _dependency_site(input_by_ref[port.owner].dependency)
                if port.owner in input_by_ref
                else _field_site(by_ref[port.owner].entry, port.field.field_position)
            )
            evidence = port.field
        origin(
            symbol.ref,
            R.SYMBOL,
            P.GENERATED_STRUCTURE,
            owner,
            cause,
            evidence,
            (symbol.subject,),
        )
    demands: list[ProjectSQLDemand] = []
    for source in sources:
        demand_ref = ref(K.DEMAND)
        demand_origin = origin(
            demand_ref,
            R.DEMAND,
            P.GENERATED_STRUCTURE,
            source.source.owner,
            source.declaration,
            source.source.owner,
            (source.ref,),
        )
        demands.append(
            ProjectSQLSourceRealizationDemand(
                ref=demand_ref, subject=source.ref, source=source, origin=demand_origin
            )
        )
    for definition in definitions:
        if isinstance(definition.entry.owner.definition, SourceDef):
            continue
        for i, port in enumerate(definition.exports):
            demand_ref = ref(K.DEMAND)
            demand_origin = origin(
                demand_ref,
                R.DEMAND,
                P.TYPE_PROOF,
                definition.entry.owner,
                _field_site(definition.entry, i),
                port.field,
                (port.ref,),
            )
            demands.append(
                ProjectSQLExportRepresentationDemand(
                    ref=demand_ref,
                    subject=port.ref,
                    field=port.field,
                    logical_type=port.field.evidence.resolved_type,
                    nullability=port.field.effective_nullability,
                    origin=demand_origin,
                )
            )
    bindings = object.__new__(ProjectSQLBindings)
    for name, value in dict(
        scope=scope,
        definitions=tuple(definitions),
        sources=tuple(sources),
        input_uses=tuple(uses),
        source_ports=tuple(
            p
            for d in definitions
            if isinstance(d.entry.owner.definition, SourceDef)
            for p in d.exports
        ),
        input_ports=tuple(p for u in uses for p in u.ports),
        all_exports=tuple(
            p
            for d in definitions
            if not isinstance(d.entry.owner.definition, SourceDef)
            for p in d.exports
        ),
        boundaries=boundaries,
        symbols=tuple(symbols),
        origins=tuple(origins),
        demands=tuple(demands),
    ).items():
        object.__setattr__(bindings, name, value)
    return bindings


def build_project_sql_plan(
    completed: ProjectConcreteCompletedSemanticResult,
    analysis_bundle: ProjectIRQueryBlockAnalysisBundle,
    selected_owner: ProjectDeclarationOccurrence,
) -> ProjectSQLPlan | ProjectSQLPlanUnavailable:
    _require_roots(completed, analysis_bundle, selected_owner)
    if _blockers(completed, analysis_bundle, selected_owner):
        return ProjectSQLPlanUnavailable(
            completed=completed,
            analysis_bundle=analysis_bundle,
            selected_owner=selected_owner,
        )
    bindings = build_project_sql_bindings(completed, analysis_bundle, selected_owner)
    if isinstance(bindings, ProjectSQLPlanUnavailable):
        return bindings
    K, R, P = ProjectSQLPlanRefKind, ProjectSQLOriginRole, ProjectSQLOriginProvenance
    blocks: list[ProjectSQLSelectBlock] = []
    projections: list[ProjectSQLProjection] = []
    sites: list[row.ProjectSQLSite] = []
    expressions: list[row.ProjectSQLExpression] = []
    operands: list[row.ProjectSQLExpressionOperand] = []
    ports: list[row.ProjectSQLStagePort] = []
    lets: list[row.ProjectSQLLetValue] = []
    filters: list[row.ProjectSQLFilter] = []
    symbols = list(bindings.symbols)
    origins = list(bindings.origins)
    demands = list(bindings.demands)
    counters = {K.SYMBOL: len(symbols), K.ORIGIN: len(origins), K.DEMAND: len(demands)}
    boundaries = {b.use.consumer: b for b in bindings.boundaries}
    binding_symbols = {s.subject: s for s in bindings.symbols}
    uses_by_owner = {u.consumer: u for u in bindings.input_uses}
    joins: list[joining.ProjectSQLJoin] = []
    join_inputs: list[joining.ProjectSQLJoinInput] = []
    join_ports: list[joining.ProjectSQLJoinPort] = []
    relationship_matches: list[joining.ProjectSQLRelationshipMatch] = []
    join_tails: list[joining.ProjectSQLJoinTail] = []
    obligations: list[joining.ProjectSQLSingleMatch] = []
    proof_images: list[joining.ProjectSQLSingleMatchProof] = []
    aggregate_stages: list[aggregation.ProjectSQLAggregation] = []
    group_keys: list[aggregation.ProjectSQLGroupKey] = []
    aggregate_values: list[aggregation.ProjectSQLAggregate] = []
    aggregate_projections: list[aggregation.ProjectSQLAggregateProjection] = []
    aggregate_risks: list[aggregation.ProjectSQLAggregateRisk] = []
    window_values: list[windows.ProjectSQLWindow] = []
    window_uses: list[windows.ProjectSQLWindowUse] = []
    window_arguments: list[windows.ProjectSQLWindowArgument] = []
    window_policies: list[windows.ProjectSQLWindowPolicy] = []
    window_projections: list[windows.ProjectSQLWindowProjection] = []
    definitions_by_owner = {id(d.entry.owner): d for d in bindings.definitions}
    uses_by_image = {id(u.edge): u for u in bindings.input_uses}
    joins_by_image = {}
    join_ports_by_ref = {}

    def ref(kind):
        position = counters.get(kind, 0)
        counters[kind] = position + 1
        return ProjectSQLPlanRef(scope=bindings.scope, kind=kind, position=position)

    def stage_port(block, kind, key, source, evidence, local_symbols):
        port = row.ProjectSQLStagePort(
            ref=ref(K.STAGE_PORT),
            block=block,
            kind=kind,
            key=key,
            source=source,
            type_evidence=evidence,
        )
        ports.append(port)
        symbol = ProjectSQLSymbol(
            ref=ref(K.SYMBOL),
            scope=block,
            namespace=ProjectSQLSymbolNamespace.FIELD_PORT,
            position=len(local_symbols),
            subject=port.ref,
            label=row.stage_key_label(key),
        )
        symbols.append(symbol)
        local_symbols[port.ref] = symbol
        return port

    def expression(site, local_ports, local_symbols, stage_context):
        source_expression = (
            site.expression
            if isinstance(site, aggregation.ProjectSQLAggregateSite)
            else site.occurrence.expression
        )
        result_site = (
            isinstance(site, aggregation.ProjectSQLAggregateSite)
            and site.role is row.ProjectSQLExpressionRole.SATISFYING
        )
        qualify_site = isinstance(site, windows.ProjectSQLQualifySite)
        terminals = (
            tuple(row.reference_expression(r) for r in site.references)
            if result_site or qualify_site
            else ()
        )
        terminal_ids = {id(n) for n in terminals}
        nodes = row.scalar_nodes(source_expression, terminals)
        node_refs = {id(n): ref(K.EXPRESSION) for n in nodes}
        if len(node_refs) != len(nodes):
            raise ValueError(
                "One authored expression site must retain distinct tree occurrences."
            )
        types = {id(n): (n, v) for n, v in row.evidence_types(site.evidence).items()}
        references = {id(row.reference_expression(r)): r for r in site.references}
        for node in nodes:
            children = tuple(
                node_refs[id(child)]
                for child in (
                    () if id(node) in terminal_ids else row.scalar_children(node)
                )
            )
            node_ref, value_type = node_refs[id(node)], types[id(node)][1]
            if isinstance(node, LiteralExpr):
                value = row.ProjectSQLLiteral(
                    ref=node_ref, site=site, expression=node, value_type=value_type
                )
            elif (
                isinstance(node, (NameExpr, DottedNameExpr)) or id(node) in terminal_ids
            ):
                reference = references[id(node)]
                if qualify_site:
                    assert isinstance(
                        reference,
                        (
                            windows.ProjectNoJoinQualifyReferenceResolution,
                            windows.ProjectQualifyReferenceResolution,
                            windows.ProjectNoJoinHiddenWindowComputation,
                            windows.ProjectConcreteWindowComputation,
                        ),
                    )
                    key = windows.qualify_target(
                        site.evidence, reference, site.aggregate
                    )
                elif result_site:
                    assert isinstance(site, aggregation.ProjectSQLAggregateSite)
                    key = aggregation.result_key(site, reference)
                else:
                    key = row.reference_key(reference)
                port = local_ports.get(id(key))
                if port is None or port.key is not key:
                    raise ValueError(
                        "Expression reference is outside its exact stage context."
                    )
                symbol = local_symbols[port.ref]
                if stage_context.lookup(symbol.ref) is not port:
                    raise ValueError(
                        "Expression symbol is outside its exact SELECT scope."
                    )
                if qualify_site:
                    value = windows.ProjectSQLWindowReference(
                        ref=node_ref,
                        site=site,
                        expression=node,
                        value_type=value_type,
                        reference=cast(windows.Reference, reference),
                        port=port.ref,
                        symbol=symbol,
                    )
                elif result_site:
                    assert isinstance(site, aggregation.ProjectSQLAggregateSite)
                    value = aggregation.ProjectSQLResultReference(
                        ref=node_ref,
                        site=site,
                        expression=node,
                        value_type=value_type,
                        reference=cast(aggregation.Reference, reference),
                        port=port.ref,
                        symbol=symbol,
                    )
                else:
                    assert isinstance(node, (NameExpr, DottedNameExpr))
                    if isinstance(reference, ProjectModuleExpressionReferenceFact):
                        value = row.ProjectSQLReference(
                            ref=node_ref,
                            site=site,
                            expression=node,
                            value_type=value_type,
                            reference=reference,
                            port=port.ref,
                            symbol=symbol,
                        )
                    elif isinstance(reference, row.ProjectJoinConditionReference):
                        value = row.ProjectSQLMatchReference(
                            ref=node_ref,
                            site=site,
                            expression=node,
                            value_type=value_type,
                            reference=reference,
                            port=port.ref,
                            symbol=symbol,
                        )
                    else:
                        assert isinstance(
                            reference,
                            (
                                row.ProjectJoinedLetReferenceResolution,
                                ProjectScalarReferenceResolution,
                            ),
                        )
                        value = row.ProjectSQLJoinedReference(
                            ref=node_ref,
                            site=site,
                            expression=node,
                            value_type=value_type,
                            reference=reference,
                            port=port.ref,
                            symbol=symbol,
                        )
            elif isinstance(node, CallExpr):
                if (
                    not isinstance(site, aggregation.ProjectSQLAggregateSite)
                    or site.role is not row.ProjectSQLExpressionRole.AGGREGATE_ARGUMENT
                ):
                    raise ValueError(
                        "Scalar calls require retained aggregate argument authority"
                    )
                value = aggregation.ProjectSQLAggregateArgumentCall(
                    ref=node_ref,
                    site=site,
                    expression=node,
                    value_type=value_type,
                    arguments=children,
                )
            elif isinstance(node, UnaryExpr):
                value = row.ProjectSQLUnary(
                    ref=node_ref,
                    site=site,
                    expression=node,
                    value_type=value_type,
                    operand=children[0],
                )
            elif isinstance(node, BinaryExpr):
                value = row.ProjectSQLBinary(
                    ref=node_ref,
                    site=site,
                    expression=node,
                    value_type=value_type,
                    left=children[0],
                    right=children[1],
                )
            elif isinstance(node, ComparisonExpr):
                value = row.ProjectSQLComparison(
                    ref=node_ref,
                    site=site,
                    expression=node,
                    value_type=value_type,
                    left=children[0],
                    right=children[1],
                )
            elif isinstance(node, IsNullExpr):
                value = row.ProjectSQLIsNull(
                    ref=node_ref,
                    site=site,
                    expression=node,
                    value_type=value_type,
                    value=children[0],
                )
            elif isinstance(node, BetweenExpr):
                value = row.ProjectSQLBetween(
                    ref=node_ref,
                    site=site,
                    expression=node,
                    value_type=value_type,
                    value=children[0],
                    lower=children[1],
                    upper=children[2],
                )
            else:
                raise ValueError("Unsupported contextual expression variant.")
            expressions.append(value)
            for position, child in enumerate(children):
                operands.append(
                    row.ProjectSQLExpressionOperand(
                        ref=ref(K.OPERAND),
                        site=site,
                        parent=value.ref,
                        position=position,
                        child=child,
                    )
                )
        return node_refs[id(source_expression)]

    def join_body(definition, authority):
        entry = definition.entry
        images = joining.join_images(analysis_bundle.root, entry)
        local_joins = []
        for position, image in enumerate(images):
            join_ref = ref(K.JOIN)
            local_symbols = {}
            input_values = []
            matching_ports = []
            keys = joining.condition_field_keys(image)
            for ordinal, source in enumerate(image.inputs):
                previous = joining.input_predecessor(source, images[:position])
                producer = (
                    None
                    if source.producer is None
                    else definitions_by_owner[id(source.producer)]
                )
                previous_join = (
                    None if previous is None else joins_by_image[id(previous)]
                )
                if producer is not None:
                    if source.use.output is not producer.entry.active_output.occurrence:
                        raise ValueError(
                            "External JOIN input must use its exact active producer."
                        )
                    upstream_ports = producer.exports
                else:
                    assert previous_join is not None
                    upstream_ports = tuple(
                        join_ports_by_ref[p] for p in previous_join.outputs
                    )
                if len(upstream_ports) != len(source.source_properties.fields):
                    raise ValueError(
                        "JOIN input must preserve every current field image."
                    )
                input_ref = ref(K.JOIN_INPUT)
                local = []
                for index, (port, original, key) in enumerate(
                    zip(
                        upstream_ports,
                        source.source_properties.fields,
                        keys[ordinal],
                        strict=True,
                    )
                ):
                    field = port.field
                    value = joining.ProjectSQLJoinPort(
                        ref=ref(K.JOIN_PORT),
                        block=join_ref,
                        kind=joining.ProjectSQLJoinPortKind.MATCH,
                        position=index,
                        input=input_ref,
                        source=port.ref,
                        original=original,
                        field=field,
                        key=field if key is None else key,
                        nulling=field.nulling_joins
                        if isinstance(field, joining.ProjectIRJoinedRowField)
                        else (),
                    )
                    join_ports.append(value)
                    local.append(value)
                    matching_ports.append(value)
                    join_ports_by_ref[value.ref] = value
                    symbol = ProjectSQLSymbol(
                        ref=ref(K.SYMBOL),
                        scope=join_ref,
                        namespace=ProjectSQLSymbolNamespace.FIELD_PORT,
                        position=len(local_symbols),
                        subject=value.ref,
                        label=field.evidence.name,
                    )
                    local_symbols[value.ref] = symbol
                    symbols.append(symbol)
                bound_use = uses_by_image.get(id(source))
                value = joining.ProjectSQLJoinInput(
                    ref=input_ref,
                    join=join_ref,
                    ordinal=ordinal,
                    source=source,
                    producer=None if producer is None else producer.ref,
                    predecessor=None if previous_join is None else previous_join.ref,
                    binding_use=None if bound_use is None else bound_use.ref,
                    ports=tuple(p.ref for p in local),
                )
                join_inputs.append(value)
                input_values.append(value)
            context = joining.ProjectSQLMatchContext(
                join=join_ref,
                ports=tuple(matching_ports),
                symbols=tuple(local_symbols.values()),
            )
            current_site = None
            on = None
            condition = image.condition
            if condition.expression is not None:
                clause = condition.use.clause.on_clause
                assert clause is not None
                current_site = row.ProjectSQLMatchSite(
                    ref=ref(K.EXPRESSION_SITE),
                    owner=entry.owner,
                    block=join_ref,
                    role=row.ProjectSQLExpressionRole.MATCH,
                    ordinal=condition.use.identity.join_position,
                    occurrence=clause,
                    evidence=condition,
                    references=condition.references,
                )
                sites.append(current_site)
                on = expression(
                    current_site,
                    {id(p.key): p for p in matching_ports},
                    local_symbols,
                    context,
                )
            equalities = []
            for source, guarantee, left, right in joining.base_matches(image):
                correspondence = (
                    source.correspondence
                    if isinstance(source, joining.ProjectIRJoinMatchFieldPair)
                    else source
                )
                left_ref, right_ref = (
                    input_values[0].ports[left],
                    input_values[1].ports[right],
                )
                authored_operands = (
                    (left_ref, right_ref)
                    if correspondence.authored_left.endpoint
                    is guarantee.direction.source
                    else (right_ref, left_ref)
                )
                value = joining.ProjectSQLRelationshipMatch(
                    ref=ref(K.RELATIONSHIP_MATCH),
                    join=join_ref,
                    source=source,
                    guarantee=guarantee,
                    left=left_ref,
                    right=right_ref,
                    authored_operands=authored_operands,
                )
                relationship_matches.append(value)
                equalities.append(value.ref)
            output_ports = []
            original_fields = image.source.output.row_shape.fields
            for index, (field, original) in enumerate(
                zip(image.output.row_shape.fields, original_fields, strict=True)
            ):
                value = joining.ProjectSQLJoinPort(
                    ref=ref(K.JOIN_PORT),
                    block=join_ref,
                    kind=joining.ProjectSQLJoinPortKind.OUTPUT,
                    position=index,
                    input=None,
                    source=matching_ports[index].ref,
                    original=original,
                    field=field,
                    key=field,
                    nulling=field.nulling_joins,
                )
                join_ports.append(value)
                output_ports.append(value)
                join_ports_by_ref[value.ref] = value
                symbol = ProjectSQLSymbol(
                    ref=ref(K.SYMBOL),
                    scope=join_ref,
                    namespace=ProjectSQLSymbolNamespace.FIELD_PORT,
                    position=len(local_symbols),
                    subject=value.ref,
                    label=field.evidence.name,
                )
                local_symbols[value.ref] = symbol
                symbols.append(symbol)
            rows = {
                AuthoredJoinKind.INNER: joining.ProjectSQLJoinRows.MATCHED_PAIRS,
                AuthoredJoinKind.LEFT: joining.ProjectSQLJoinRows.LEFT_PRESERVED,
                AuthoredJoinKind.CROSS: joining.ProjectSQLJoinRows.CARTESIAN_PAIRS,
                AuthoredJoinKind.RIGHT: joining.ProjectSQLJoinRows.RIGHT_PRESERVED,
                AuthoredJoinKind.FULL: joining.ProjectSQLJoinRows.BOTH_PRESERVED,
                AuthoredJoinKind.SEMI: joining.ProjectSQLJoinRows.LEFT_EXISTS,
                AuthoredJoinKind.ANTI: joining.ProjectSQLJoinRows.LEFT_NOT_EXISTS,
            }[image.source.use.kind]
            properties = (
                image.source_properties
                if entry.join_prefix is None
                else _one(
                    tuple(
                        p.relational
                        for p in entry.join_properties
                        if p.output is image.output
                    ),
                    "JOIN properties",
                )
            )
            value = joining.ProjectSQLJoin(
                ref=join_ref,
                definition=definition.ref,
                position=position,
                source=image,
                kind=image.source.use.kind,
                rows=rows,
                inputs=(input_values[0].ref, input_values[1].ref),
                outputs=tuple(p.ref for p in output_ports),
                equalities=tuple(equalities),
                on=on,
                site=current_site,
                properties=properties,
            )
            joins.append(value)
            local_joins.append(value)
            joins_by_image[id(image)] = value
        final = _one(
            tuple(
                join
                for join in local_joins
                if join.source.source.output
                is authority.binding_environment.row_source.final_output
            ),
            "post-JOIN output",
        )
        fields = authority.binding_environment.visible_fields
        images_by_source = {
            id(source): join_ports_by_ref[port]
            for source, port in zip(
                final.source.source.output.row_shape.fields, final.outputs, strict=True
            )
        }
        outputs = tuple(images_by_source[id(field.source_field)] for field in fields)
        tail_source = joining.joined_tail(entry)
        assert tail_source is not None
        boundary = joining.ProjectSQLJoinTail(
            ref=ref(K.JOIN_TAIL),
            definition=definition.ref,
            join=final.ref,
            source=tail_source,
            fields=fields,
            ports=tuple(p.ref for p in outputs),
        )
        join_tails.append(boundary)
        return boundary, [
            (field, port.ref, field.value_type)
            for field, port in zip(fields, outputs, strict=True)
        ]

    for definition in bindings.definitions:
        entry = definition.entry
        authored = entry.owner.definition
        if isinstance(authored, SourceDef):
            continue
        assert isinstance(authored, (TableDef, QueryDef))
        authority = row.row_authority(completed, entry)
        assert authority is not None
        context = authority
        aggregate = aggregation.authority(completed, entry)
        window_view = windows.authority(entry)
        window_by_item = (
            {}
            if window_view is None
            else {id(selected.item): selected for selected in window_view.selected}
        )
        windows_by_source = {}
        aggregate_ref = None
        aggregate_outgoing = []
        window_outgoing = []
        if isinstance(authority, row.ProjectSQLJoinedRowAuthority):
            boundary, carried = join_body(definition, authority)
            use = None
            original_ports = {}
            predecessor = boundary.join
        else:
            use = uses_by_owner[definition.ref]
            boundary = boundaries[definition.ref]
            input_keys = row.input_keys(entry, authority, use.ports)
            original_ports = {
                id(key): port for key, port in zip(input_keys, use.ports, strict=True)
            }
            carried = [
                (key, port.ref, port.field.evidence)
                for key, port in zip(input_keys, use.ports, strict=True)
            ]
            predecessor = use.ref
        stages = [(row.ProjectSQLStageKind.LET, i) for i in range(len(authority.lets))]
        if authored.where_clause is not None:
            stages.append((row.ProjectSQLStageKind.WHERE, 0))
        if aggregate is not None:
            stages.append((row.ProjectSQLStageKind.AGGREGATE, 0))
            if aggregate.satisfying is not None:
                stages.append((row.ProjectSQLStageKind.SATISFYING, 0))
        if window_view is not None:
            stages.append((row.ProjectSQLStageKind.WINDOW, 0))
            if window_view.qualify is not None:
                stages.append((row.ProjectSQLStageKind.QUALIFY, 0))
        stages.append((row.ProjectSQLStageKind.PROJECTION, 0))
        for position, (kind, ordinal) in enumerate(stages):
            block_ref = ref(K.SELECT_BLOCK)
            local_symbols = {}
            local_inputs = tuple(
                stage_port(
                    block_ref,
                    row.ProjectSQLStagePortKind.INPUT,
                    key,
                    source,
                    value_type,
                    local_symbols,
                )
                for key, source, value_type in carried
            )
            local_ports = {id(p.key): p for p in local_inputs}
            stage_context = row.ProjectSQLStageContext(
                block=block_ref,
                ports=local_inputs,
                symbols=tuple(local_symbols.values()),
            )

            def site(role, index, occurrence, evidence, references):
                if isinstance(context, row.ProjectSQLJoinedRowAuthority):
                    result = row.ProjectSQLJoinedSite(
                        ref=ref(K.EXPRESSION_SITE),
                        owner=entry.owner,
                        block=block_ref,
                        role=role,
                        ordinal=index,
                        occurrence=occurrence,
                        namespace=evidence.namespace,
                        evidence=evidence,
                        references=references,
                    )
                else:
                    result = row.ProjectSQLExpressionSite(
                        ref=ref(K.EXPRESSION_SITE),
                        owner=entry.owner,
                        block=block_ref,
                        role=role,
                        ordinal=index,
                        occurrence=occurrence,
                        input_schema=context.input_schema,
                        let_scope=context.let_scope,
                        let_prefix=context.let_scope.bindings[:index]
                        if role is row.ProjectSQLExpressionRole.LET
                        else context.let_scope.bindings,
                        evidence=evidence,
                        references=references,
                    )
                sites.append(result)
                return result

            produced = None
            current_site = None
            if kind is row.ProjectSQLStageKind.LET:
                fact = authority.lets[ordinal]
                current_site = site(
                    row.ProjectSQLExpressionRole.LET,
                    ordinal,
                    fact.occurrence.binding
                    if isinstance(fact, row.ProjectJoinedLetValue)
                    else fact.binding,
                    fact,
                    fact.resolutions
                    if isinstance(fact, row.ProjectJoinedLetValue)
                    else fact.references,
                )
                produced = expression(
                    current_site, local_ports, local_symbols, stage_context
                )
            elif kind is row.ProjectSQLStageKind.WHERE:
                assert authored.where_clause is not None and authority.where is not None
                current_site = site(
                    row.ProjectSQLExpressionRole.WHERE,
                    0,
                    authored.where_clause,
                    authority.where,
                    authority.where_references,
                )
                predicate = expression(
                    current_site, local_ports, local_symbols, stage_context
                )
                filters.append(
                    row.ProjectSQLFilter(
                        ref=ref(K.FILTER),
                        site=current_site,
                        predicate=predicate,
                        retention_effects=_SQL_ROW_RETENTION_EFFECTS,
                    )
                )
            elif kind is row.ProjectSQLStageKind.AGGREGATE:
                assert aggregate is not None
                aggregate_ref = ref(K.AGGREGATION)
                aggregate_outgoing = []
                local_keys = []
                local_aggregates = []
                for index, (key, references) in enumerate(
                    zip(aggregate.keys, aggregate.key_references, strict=True)
                ):
                    reference = references[0]
                    target = row.reference_key(reference)
                    input_port = local_ports.get(id(target))
                    if input_port is None or input_port.key is not target:
                        raise ValueError(
                            "Group key is outside the exact pre-aggregate input"
                        )
                    key_ref = ref(K.GROUP_KEY)
                    value_type = (
                        key.input_field
                        if isinstance(key, aggregation.ProjectGroupKeyFact)
                        else key.value_type
                    )
                    output_port = stage_port(
                        block_ref,
                        row.ProjectSQLStagePortKind.EXPORT,
                        key,
                        key_ref,
                        value_type,
                        local_symbols,
                    )
                    value = aggregation.ProjectSQLGroupKey(
                        ref=key_ref,
                        aggregation=aggregate_ref,
                        position=index,
                        source=key,
                        reference=reference,
                        input=input_port.ref,
                        result=output_port.ref,
                    )
                    group_keys.append(value)
                    local_keys.append(value.ref)
                    aggregate_outgoing.append(output_port)
                for index, (source, references) in enumerate(
                    zip(
                        aggregate.aggregates, aggregate.argument_references, strict=True
                    )
                ):
                    call = source.item.expression
                    assert isinstance(call, CallExpr)
                    arguments = ()
                    if call.arguments:
                        evidence = aggregation.argument_evidence(source)
                        assert evidence is not None
                        current_site = aggregation.ProjectSQLAggregateSite(
                            ref=ref(K.EXPRESSION_SITE),
                            owner=entry.owner,
                            block=block_ref,
                            role=row.ProjectSQLExpressionRole.AGGREGATE_ARGUMENT,
                            ordinal=index,
                            occurrence=source.item,
                            expression=call.arguments[0],
                            aggregation=aggregate_ref,
                            authority=aggregate,
                            evidence=evidence,
                            references=references,
                        )
                        sites.append(current_site)
                        arguments = (
                            expression(
                                current_site, local_ports, local_symbols, stage_context
                            ),
                        )
                    value_ref = ref(K.AGGREGATE)
                    value_type = aggregation.result_type(source)
                    output_port = stage_port(
                        block_ref,
                        row.ProjectSQLStagePortKind.EXPORT,
                        source.item,
                        value_ref,
                        value_type,
                        local_symbols,
                    )
                    value = aggregation.ProjectSQLAggregate(
                        ref=value_ref,
                        aggregation=aggregate_ref,
                        position=index,
                        source=source,
                        arguments=arguments,
                        result=output_port.ref,
                        value_type=value_type,
                    )
                    aggregate_values.append(value)
                    local_aggregates.append(value_ref)
                    aggregate_outgoing.append(output_port)
                aggregate_stages.append(
                    aggregation.ProjectSQLAggregation(
                        ref=aggregate_ref,
                        block=block_ref,
                        definition=definition.ref,
                        authority=aggregate,
                        mode=aggregate.mode,
                        keys=tuple(local_keys),
                        aggregates=tuple(local_aggregates),
                        inputs=tuple(p.ref for p in local_inputs),
                        results=tuple(p.ref for p in aggregate_outgoing),
                        empty_input=aggregation.ProjectSQLAggregateEmptyInput.ONE_GLOBAL_ROW
                        if aggregate.mode
                        is aggregation.ProjectJoinedAggregationMode.GLOBAL
                        else aggregation.ProjectSQLAggregateEmptyInput.NO_GROUPS,
                    )
                )
                aggregate_risks.extend(
                    aggregation.ProjectSQLAggregateRisk(
                        ref=ref(K.AGGREGATE_RISK),
                        aggregation=aggregate_ref,
                        source=source,
                    )
                    for source in aggregate.risks
                )
            elif kind is row.ProjectSQLStageKind.SATISFYING:
                assert (
                    aggregate is not None
                    and aggregate.satisfying is not None
                    and aggregate_ref is not None
                    and authored.satisfying_clause is not None
                )
                current_site = aggregation.ProjectSQLAggregateSite(
                    ref=ref(K.EXPRESSION_SITE),
                    owner=entry.owner,
                    block=block_ref,
                    role=row.ProjectSQLExpressionRole.SATISFYING,
                    ordinal=0,
                    occurrence=authored.satisfying_clause,
                    expression=authored.satisfying_clause.expression,
                    aggregation=aggregate_ref,
                    authority=aggregate,
                    evidence=aggregate.satisfying,
                    references=aggregate.satisfying_references,
                )
                sites.append(current_site)
                predicate = expression(
                    current_site, local_ports, local_symbols, stage_context
                )
                filters.append(
                    row.ProjectSQLFilter(
                        ref=ref(K.FILTER),
                        site=current_site,
                        predicate=predicate,
                        retention_effects=aggregation.satisfying_effects(aggregate),
                    )
                )
            elif kind is row.ProjectSQLStageKind.WINDOW:
                assert window_view is not None
                window_outgoing = [
                    stage_port(
                        block_ref,
                        row.ProjectSQLStagePortKind.EXPORT,
                        port.key,
                        port.ref,
                        port.type_evidence,
                        local_symbols,
                    )
                    for port in local_inputs
                ]
                selected_sources = {
                    id(windows.selected_source(item)): item
                    for item in window_view.selected
                }
                for index, source in enumerate(windows.sources(window_view)):
                    window_ref = ref(K.WINDOW)
                    window_context = windows.input_context(source)
                    uses = []
                    for original in windows.input_uses(source):
                        key = windows.input_target(source, original, aggregate)
                        port = None if key is None else local_ports.get(id(key))
                        if key is not None and (port is None or port.key is not key):
                            raise ValueError(
                                "Window input is outside its pre-window stage"
                            )
                        if isinstance(
                            original, windows.ProjectWindowDependencyOccurrence
                        ):
                            if (
                                original.role
                                is windows.WindowDependencyRole.RELATION_INPUT
                            ):
                                binding = None
                            else:
                                assert isinstance(
                                    original.target,
                                    windows.ProjectJoinedWindowInputBinding,
                                )
                                binding = original.target
                        else:
                            binding = original.binding
                        assert original.expression is not None
                        use_value = windows.ProjectSQLWindowUse(
                            ref=ref(K.WINDOW_USE),
                            window=window_ref,
                            source=original,
                            role=original.role,
                            position=original.global_ordinal,
                            role_position=original.role_ordinal,
                            expression=original.expression,
                            input=None if port is None else port.ref,
                            binding=binding,
                            value_type=windows.use_type(source, original),
                        )
                        window_uses.append(use_value)
                        uses.append(use_value)
                    arguments = []
                    for argument_position, argument in enumerate(
                        windows.effective(source).call.arguments
                    ):
                        matching = tuple(
                            use for use in uses if use.expression is argument
                        )
                        argument_value = windows.ProjectSQLWindowArgument(
                            ref=ref(K.WINDOW_ARGUMENT),
                            window=window_ref,
                            position=argument_position,
                            role=windows.argument_role(source, argument_position),
                            expression=argument,
                            value_type=windows.argument_type(source, argument_position),
                            use=None
                            if not matching
                            else _one(matching, "window argument input").ref,
                        )
                        arguments.append(argument_value.ref)
                        window_arguments.append(argument_value)
                    (
                        _,
                        _,
                        ranking,
                        distribution,
                        bucket_count,
                        navigation,
                        frame_value,
                        modifiers,
                    ) = windows.components(source)
                    ir_operator, ir_policy, ir_effect = windows.ir_evidence(
                        source, entry
                    )
                    partitions, orders, *_ = windows.components(source)
                    policy = windows.ProjectSQLWindowPolicy(
                        ref=ref(K.WINDOW_POLICY),
                        window=window_ref,
                        specification=windows.analysis(source).validated_specification,
                        partitions=partitions,
                        orders=orders,
                        modifiers=modifiers,
                        named_use=windows.analysis(source).resolved_named_use,
                        namespace=window_view.named,
                        ranking=ranking,
                        distribution=distribution,
                        bucket_count=bucket_count,
                        navigation=navigation,
                        frame_value=frame_value,
                        ir_operator=ir_operator,
                        ir_policy=ir_policy,
                        ir_effect=ir_effect,
                    )
                    window_policies.append(policy)
                    result_type = windows.result_type(source)
                    result_port = stage_port(
                        block_ref,
                        row.ProjectSQLStagePortKind.EXPORT,
                        source,
                        window_ref,
                        result_type,
                        local_symbols,
                    )
                    window_outgoing.append(result_port)
                    value = windows.ProjectSQLWindow(
                        ref=window_ref,
                        block=block_ref,
                        definition=definition.ref,
                        position=index,
                        source=source,
                        selected=selected_sources.get(id(source)),
                        authored=windows.authored(source),
                        effective=windows.effective(source),
                        function=windows.effective(source).identity,
                        context=window_context,
                        inputs=tuple(port.ref for port in local_inputs),
                        uses=tuple(use.ref for use in uses),
                        arguments=tuple(arguments),
                        result=result_port.ref,
                        value_type=result_type,
                        policy=policy.ref,
                    )
                    window_values.append(value)
                    windows_by_source[id(source)] = value
            elif kind is row.ProjectSQLStageKind.QUALIFY:
                assert (
                    window_view is not None
                    and window_view.qualify is not None
                    and authored.qualify_clause is not None
                )
                current_site = windows.ProjectSQLQualifySite(
                    ref=ref(K.EXPRESSION_SITE),
                    owner=entry.owner,
                    block=block_ref,
                    role=row.ProjectSQLExpressionRole.QUALIFY,
                    ordinal=0,
                    occurrence=authored.qualify_clause,
                    evidence=window_view.qualify,
                    aggregate=aggregate,
                    references=windows.qualifier_references(window_view.qualify),
                )
                sites.append(current_site)
                predicate = expression(
                    current_site, local_ports, local_symbols, stage_context
                )
                filters.append(
                    row.ProjectSQLFilter(
                        ref=ref(K.FILTER),
                        site=current_site,
                        predicate=predicate,
                        retention_effects=windows.qualify_effects(window_view.qualify),
                    )
                )
            else:
                aggregate_position = 0
                for index, (semantic, export) in enumerate(
                    zip(authority.selections, definition.exports, strict=True)
                ):
                    selected_window = window_by_item.get(id(semantic.item))
                    if selected_window is not None:
                        source = windows.selected_source(selected_window)
                        value = windows_by_source[id(source)]
                        input_port = local_ports[id(source)]
                        window_projections.append(
                            windows.ProjectSQLWindowProjection(
                                ref=ref(K.WINDOW_PROJECTION),
                                window=value.ref,
                                block=block_ref,
                                semantic=semantic,
                                source=selected_window,
                                input=input_port.ref,
                                export=export.ref,
                            )
                        )
                    elif aggregate is not None:
                        assert aggregate_ref is not None
                        source, key = (
                            aggregate.outputs[aggregate_position],
                            aggregate.output_keys[aggregate_position],
                        )
                        aggregate_position += 1
                        input_port = local_ports.get(id(key))
                        if (
                            input_port is None
                            or input_port.key is not key
                            or stage_context.lookup(input_port.ref) is not input_port
                        ):
                            raise ValueError(
                                "Aggregate projection lost its exact result port"
                            )
                        aggregate_projections.append(
                            aggregation.ProjectSQLAggregateProjection(
                                ref=ref(K.AGGREGATE_PROJECTION),
                                block=block_ref,
                                aggregation=aggregate_ref,
                                semantic=semantic,
                                source=source,
                                input=input_port.ref,
                                export=export.ref,
                            )
                        )
                    else:
                        evidence, references = (
                            authority.selected_evidence[index],
                            authority.selected_references[index],
                        )
                        current_site = site(
                            row.ProjectSQLExpressionRole.SELECT,
                            index,
                            semantic.item,
                            evidence,
                            references,
                        )
                        root_expression = expression(
                            current_site, local_ports, local_symbols, stage_context
                        )
                        direct = None
                        if (
                            not isinstance(authority, row.ProjectSQLJoinedRowAuthority)
                            and isinstance(
                                semantic.item.expression, (NameExpr, DottedNameExpr)
                            )
                            and len(references) == 1
                            and isinstance(
                                references[0], ProjectModuleExpressionReferenceFact
                            )
                        ):
                            direct = original_ports.get(id(references[0].input_field))
                        projections.append(
                            ProjectSQLProjection(
                                ref=ref(K.PROJECTION),
                                block=block_ref,
                                input_use=None if use is None else use.ref,
                                source_port=None
                                if direct is None
                                else direct.producer_port,
                                input_port=None if direct is None else direct.ref,
                                export=export.ref,
                                semantic=semantic,
                                symbol=None
                                if direct is None
                                else binding_symbols[direct.ref],
                                expression=root_expression,
                                site=current_site,
                            )
                        )
            if kind is row.ProjectSQLStageKind.PROJECTION:
                exports = tuple(p.ref for p in definition.exports)
            else:
                outgoing = (
                    aggregate_outgoing
                    if kind is row.ProjectSQLStageKind.AGGREGATE
                    else window_outgoing
                    if kind is row.ProjectSQLStageKind.WINDOW
                    else [
                        stage_port(
                            block_ref,
                            row.ProjectSQLStagePortKind.EXPORT,
                            p.key,
                            p.ref,
                            p.type_evidence,
                            local_symbols,
                        )
                        for p in local_inputs
                    ]
                )
                if kind is row.ProjectSQLStageKind.LET:
                    assert produced is not None and current_site is not None
                    fact = authority.lets[ordinal]
                    assert fact.value_type is not None
                    port = stage_port(
                        block_ref,
                        row.ProjectSQLStagePortKind.EXPORT,
                        fact.occurrence
                        if isinstance(fact, row.ProjectJoinedLetValue)
                        else fact.binding,
                        produced,
                        fact.value_type,
                        local_symbols,
                    )
                    outgoing.append(port)
                    assert isinstance(
                        current_site,
                        (row.ProjectSQLExpressionSite, row.ProjectSQLJoinedSite),
                    )
                    lets.append(
                        row.ProjectSQLLetValue(
                            ref=ref(K.LET_VALUE),
                            site=current_site,
                            expression=produced,
                            port=port.ref,
                        )
                    )
                carried = [(p.key, p.ref, p.type_evidence) for p in outgoing]
                exports = tuple(p.ref for p in outgoing)
            blocks.append(
                ProjectSQLSelectBlock(
                    ref=block_ref,
                    definition=definition.ref,
                    position=position,
                    kind=kind,
                    predecessor=predecessor,
                    inputs=tuple(p.ref for p in local_inputs),
                    exports=exports,
                    selected=entry,
                    operators=tuple(
                        operator
                        for operator in _operators(entry)
                        if (
                            position == 0
                            and operator.kind
                            is ProjectIRLogicalOperatorKind.RELATION_INPUT
                        )
                        or (
                            kind is row.ProjectSQLStageKind.WHERE
                            and operator.kind is ProjectIRLogicalOperatorKind.ROW_FILTER
                        )
                        or (
                            kind is row.ProjectSQLStageKind.AGGREGATE
                            and operator.kind
                            is ProjectIRLogicalOperatorKind.GROUP_AGGREGATE
                        )
                        or (
                            kind is row.ProjectSQLStageKind.SATISFYING
                            and operator.kind
                            is ProjectIRLogicalOperatorKind.RESULT_FILTER
                        )
                        or (
                            kind is row.ProjectSQLStageKind.WINDOW
                            and operator.kind.value == "window_evaluation"
                        )
                        or (
                            kind is row.ProjectSQLStageKind.QUALIFY
                            and operator.kind.value == "qualify"
                        )
                        or (
                            kind is row.ProjectSQLStageKind.PROJECTION
                            and operator.kind
                            is ProjectIRLogicalOperatorKind.FINAL_PROJECTION
                        )
                    ),
                    boundary=boundary,
                )
            )
            predecessor = block_ref

    def retained_join(boundary):
        return _one(
            tuple(
                j for j in joins if j.source is boundary or j.source.source is boundary
            ),
            "retained matching boundary",
        )

    for retained in analysis_bundle.root.requirements:
        if (
            retained.owner_entry is None
            or id(retained.owner_entry.owner) not in definitions_by_owner
        ):
            continue
        if (
            definitions_by_owner[id(retained.owner_entry.owner)].entry
            is not retained.owner_entry
        ):
            raise ValueError("Applicable obligation lost its exact owner entry.")
        obligation_ref = ref(K.SINGLE_MATCH)
        boundaries_for_request = tuple(
            retained_join(boundary) for boundary in retained.boundaries
        )
        proof_nodes = []
        pending: list[
            tuple[
                tuple[int, ...],
                tuple[int, ...] | None,
                joining.ProjectIRSingleMatchProofImage,
            ]
        ] = [
            ((i,), None, source)
            for i, source in reversed(tuple(enumerate(retained.proofs)))
        ]
        while pending:
            path, parent_path, source = pending.pop()
            proof_nodes.append((path, parent_path, source))
            pending.extend(
                ((*path, i), path, child)
                for i, child in reversed(tuple(enumerate(source.children)))
            )
        proof_refs = {path: ref(K.SINGLE_MATCH_PROOF) for path, _, _ in proof_nodes}
        for path, parent_path, source in proof_nodes:
            proof_images.append(
                joining.ProjectSQLSingleMatchProof(
                    ref=proof_refs[path],
                    obligation=obligation_ref,
                    parent=None if parent_path is None else proof_refs[parent_path],
                    source=source,
                    joins=tuple(
                        retained_join(boundary).ref for boundary in source.boundaries
                    ),
                    producers=tuple(
                        definitions_by_owner[id(producer.owner)].ref
                        for producer in source.producers
                    ),
                    children=tuple(
                        proof_refs[(*path, i)] for i in range(len(source.children))
                    ),
                )
            )
        assessment = retained.assessment
        obligations.append(
            joining.ProjectSQLSingleMatch(
                ref=obligation_ref,
                source=retained,
                request=assessment.request,
                assessment=assessment,
                joins=tuple(join.ref for join in boundaries_for_request),
                input_pairs=tuple(join.inputs for join in boundaries_for_request),
                proofs=tuple(proof_refs[(i,)] for i in range(len(retained.proofs))),
                diagnostic=assessment.diagnostic,
                downstream_enforcement_required=assessment.downstream_enforcement_required,
            )
        )

    block_by_ref = {b.ref: b for b in blocks}
    expression_by_ref = {e.ref: e for e in expressions}
    port_by_ref = {p.ref: p for p in ports}
    export_by_ref = {p.ref: p for p in bindings.all_exports}
    origin_by_subject = {}
    join_by_ref = {j.ref: j for j in joins}

    def origin(subject, role, provenance, owner, cause, evidence, antecedents=()):
        value = ProjectSQLOrigin(
            ref=ref(K.ORIGIN),
            subject=subject,
            role=role,
            provenance=provenance,
            owner=owner,
            cause=cause,
            evidence=evidence,
            antecedents=antecedents,
        )
        origins.append(value)
        origin_by_subject[subject] = value.ref
        return value.ref

    for block in blocks:
        origin(
            block.ref,
            R.SELECT_BLOCK,
            P.GENERATED_STRUCTURE,
            block.selected.owner,
            block.selected.owner.definition,
            block.selected,
            (block.predecessor, block.boundary.ref)
            if isinstance(block.boundary, joining.ProjectSQLJoinTail)
            else (block.predecessor,),
        )
    for port in ports:
        owner = block_by_ref[port.block].selected.owner
        cause = (
            port.key.binding
            if isinstance(port.key, row.ProjectJoinedLetOccurrence)
            else port.key
            if isinstance(port.key, LetBinding)
            else cast(TableDef | QueryDef, owner.definition).from_clause
        )
        origin(
            port.ref,
            R.STAGE_PORT,
            P.VALUE,
            owner,
            cause,
            port.type_evidence,
            (port.source,),
        )
    for current_site in sites:
        origin(
            current_site.ref,
            R.EXPRESSION_SITE,
            P.TYPE_PROOF,
            current_site.owner,
            current_site.occurrence,
            current_site.evidence,
            join_by_ref[current_site.block].inputs
            if isinstance(current_site, row.ProjectSQLMatchSite)
            else (current_site.block,),
        )
    for value in expressions:
        dependencies = (
            (value.port,)
            if isinstance(
                value,
                (
                    row.ProjectSQLReference,
                    row.ProjectSQLJoinedReference,
                    row.ProjectSQLMatchReference,
                    aggregation.ProjectSQLResultReference,
                    windows.ProjectSQLWindowReference,
                ),
            )
            else ()
        )
        origin(
            value.ref,
            R.EXPRESSION,
            P.VALUE,
            value.site.owner,
            value.expression,
            value.value_type,
            (value.site.ref, *dependencies),
        )
    for operand in operands:
        parent = expression_by_ref[operand.parent]
        origin(
            operand.ref,
            R.OPERAND,
            P.VALUE,
            operand.site.owner,
            parent.expression,
            expression_by_ref[operand.child].value_type,
            (operand.parent, operand.child),
        )
    for value in lets:
        origin(
            value.ref,
            R.LET_VALUE,
            P.VALUE,
            value.site.owner,
            value.site.occurrence,
            value.site.evidence,
            (value.expression, value.port),
        )
    for item in filters:
        origin(
            item.ref,
            R.FILTER,
            P.MEMBERSHIP,
            item.site.owner,
            item.site.occurrence,
            item.site.evidence,
            (item.site.block, item.predicate),
        )
    for projection in projections:
        origin(
            projection.ref,
            R.PROJECTION,
            P.VALUE,
            projection.site.owner,
            projection.semantic.item,
            projection.semantic,
            (projection.expression,),
        )
        export = export_by_ref[projection.export]
        origin(
            export.ref,
            R.EXPORT,
            P.VALUE,
            projection.site.owner,
            projection.semantic.item,
            export.field,
            (projection.ref,),
        )
    for symbol in symbols[len(bindings.symbols) :]:
        if symbol.subject not in port_by_ref:
            continue
        port = port_by_ref[symbol.subject]
        block = block_by_ref[port.block]
        origin(
            symbol.ref,
            R.SYMBOL,
            P.GENERATED_STRUCTURE,
            block.selected.owner,
            block.selected.owner.definition,
            port.type_evidence,
            (port.ref,),
        )

    children_by_parent = {e.ref: [] for e in expressions}
    for operand in operands:
        children_by_parent[operand.parent].append(
            expression_by_ref[operand.child].value_type
        )
    for value in expressions:
        demand_ref = ref(K.DEMAND)
        demand_origin = origin(
            demand_ref,
            R.DEMAND,
            P.TYPE_PROOF,
            value.site.owner,
            value.expression,
            value.value_type,
            (origin_by_subject[value.ref],),
        )
        demands.append(
            row.ProjectSQLExpressionDemand(
                ref=demand_ref,
                subject=value.ref,
                site=value.site,
                expression=value.expression,
                value_type=value.value_type,
                operand_types=tuple(children_by_parent[value.ref]),
                origin=demand_origin,
            )
        )
    for port in ports:
        block = block_by_ref[port.block]
        demand_ref = ref(K.DEMAND)
        demand_origin = origin(
            demand_ref,
            R.DEMAND,
            P.TYPE_PROOF,
            block.selected.owner,
            block.selected.owner.definition,
            port.type_evidence,
            (origin_by_subject[port.ref],),
        )
        demands.append(
            row.ProjectSQLStageValueDemand(
                ref=demand_ref,
                subject=port.ref,
                block=port.block,
                type_evidence=port.type_evidence,
                origin=demand_origin,
            )
        )
    for item in filters:
        value_type = expression_by_ref[item.predicate].value_type
        demand_ref = ref(K.DEMAND)
        demand_origin = origin(
            demand_ref,
            R.DEMAND,
            P.MEMBERSHIP,
            item.site.owner,
            item.site.occurrence,
            item.site.evidence,
            (origin_by_subject[item.ref],),
        )
        demands.append(
            row.ProjectSQLFilterDemand(
                ref=demand_ref,
                subject=item.ref,
                site=item.site,
                value_type=value_type,
                retention_effects=item.retention_effects,
                origin=demand_origin,
            )
        )
    for block in blocks:
        demand_ref = ref(K.DEMAND)
        demand_origin = origin(
            demand_ref,
            R.DEMAND,
            P.GENERATED_STRUCTURE,
            block.selected.owner,
            block.selected.owner.definition,
            block.selected,
            (origin_by_subject[block.ref],),
        )
        demands.append(
            row.ProjectSQLScopeDemand(
                ref=demand_ref,
                subject=block.ref,
                predecessor=block.predecessor,
                inputs=block.inputs,
                exports=block.exports,
                origin=demand_origin,
            )
        )
    join_by_ref = {j.ref: j for j in joins}
    obligation_by_ref = {o.ref: o for o in obligations}
    witnesses = (
        *joins,
        *join_inputs,
        *join_ports,
        *relationship_matches,
        *join_tails,
        *obligations,
        *proof_images,
    )
    for witness in witnesses:
        if isinstance(witness, joining.ProjectSQLJoin):
            kind, role, provenance = (
                joining.ProjectSQLJoinDemandKind.JOIN_ROWS,
                R.JOIN,
                P.MEMBERSHIP,
            )
            owner, cause = (
                witness.source.condition.use.owner,
                witness.source.condition.use.clause,
            )
            antecedents = (
                *witness.inputs,
                *witness.equalities,
                *(() if witness.on is None else (witness.on,)),
            )
        elif isinstance(witness, joining.ProjectSQLJoinInput):
            kind, role, provenance = (
                joining.ProjectSQLJoinDemandKind.MATCH_INPUT,
                R.JOIN_INPUT,
                P.MEMBERSHIP,
            )
            join = join_by_ref[witness.join]
            owner, cause = (
                join.source.condition.use.owner,
                join.source.condition.use.clause,
            )
            antecedents = (
                (witness.producer,)
                if witness.producer is not None
                else (witness.predecessor,)
            )
        elif isinstance(witness, joining.ProjectSQLJoinPort):
            matching = witness.kind is joining.ProjectSQLJoinPortKind.MATCH
            kind = (
                joining.ProjectSQLJoinDemandKind.MATCH_FIELD
                if matching
                else joining.ProjectSQLJoinDemandKind.OUTPUT_FIELD
            )
            role, provenance = R.JOIN_PORT, P.MEMBERSHIP if matching else P.VALUE
            join = join_by_ref[witness.block]
            owner, cause = (
                join.source.condition.use.owner,
                join.source.condition.use.clause,
            )
            antecedents = (
                (witness.source, witness.input)
                if matching
                else (witness.source, witness.block)
            )
        elif isinstance(witness, joining.ProjectSQLRelationshipMatch):
            kind, role, provenance = (
                joining.ProjectSQLJoinDemandKind.RELATIONSHIP_EQUALITY,
                R.RELATIONSHIP_MATCH,
                P.MEMBERSHIP,
            )
            join = join_by_ref[witness.join]
            source = (
                witness.source.correspondence
                if isinstance(witness.source, joining.ProjectIRJoinMatchFieldPair)
                else witness.source
            )
            owner, cause, antecedents = (
                join.source.condition.use.owner,
                source.comparison,
                witness.authored_operands,
            )
        elif isinstance(witness, joining.ProjectSQLJoinTail):
            kind, role, provenance = (
                joining.ProjectSQLJoinDemandKind.POST_MATCH_SCOPE,
                R.JOIN_TAIL,
                P.GENERATED_STRUCTURE,
            )
            owner = join_by_ref[witness.join].source.condition.use.owner
            cause, antecedents = owner.definition, (witness.join, *witness.ports)
        elif isinstance(witness, joining.ProjectSQLSingleMatch):
            kind, role, provenance = (
                joining.ProjectSQLJoinDemandKind.SINGLE_MATCH,
                R.SINGLE_MATCH,
                P.TYPE_PROOF,
            )
            owner, cause, antecedents = (
                witness.request.owner,
                witness.request.use.clause,
                (*witness.joins, *witness.proofs),
            )
        else:
            kind, role, provenance = (
                joining.ProjectSQLJoinDemandKind.PROOF_CONTEXT,
                R.SINGLE_MATCH_PROOF,
                P.TYPE_PROOF,
            )
            obligation = obligation_by_ref[witness.obligation]
            owner, cause = obligation.request.owner, obligation.request.use.clause
            antecedents = (*witness.joins, *witness.producers, *witness.children)
        witness_origin = origin(
            witness.ref, role, provenance, owner, cause, witness, antecedents
        )
        demand_ref = ref(K.DEMAND)
        demand_origin = origin(
            demand_ref, R.DEMAND, provenance, owner, cause, witness, (witness_origin,)
        )
        demands.append(
            joining.ProjectSQLJoinDemand(
                ref=demand_ref,
                subject=witness.ref,
                kind=kind,
                witness=witness,
                origin=demand_origin,
            )
        )
    for symbol in symbols[len(bindings.symbols) :]:
        port = join_ports_by_ref.get(symbol.subject)
        if port is None:
            continue
        join = join_by_ref[port.block]
        origin(
            symbol.ref,
            R.SYMBOL,
            P.GENERATED_STRUCTURE,
            join.source.condition.use.owner,
            join.source.condition.use.clause,
            port,
            (port.ref,),
        )

    aggregate_by_ref = {a.ref: a for a in aggregate_stages}
    for witness in (
        *aggregate_stages,
        *group_keys,
        *aggregate_values,
        *aggregate_projections,
        *aggregate_risks,
    ):
        stage = (
            witness
            if isinstance(witness, aggregation.ProjectSQLAggregation)
            else aggregate_by_ref[witness.aggregation]
        )
        block = block_by_ref[stage.block]
        owner = block.selected.owner
        if isinstance(witness, aggregation.ProjectSQLAggregation):
            kind, role, provenance = (
                aggregation.ProjectSQLAggregateDemandKind.GROUPING_AND_EMPTY_INPUT,
                R.AGGREGATION,
                P.MEMBERSHIP,
            )
            cause, antecedents = owner.definition, (witness.block,)
        elif isinstance(witness, aggregation.ProjectSQLGroupKey):
            kind, role, provenance = (
                aggregation.ProjectSQLAggregateDemandKind.GROUP_COMPARISON,
                R.GROUP_KEY,
                P.VALUE,
            )
            cause, antecedents = (
                witness.source.item,
                (witness.aggregation, witness.input),
            )
        elif isinstance(witness, aggregation.ProjectSQLAggregate):
            kind, role, provenance = (
                aggregation.ProjectSQLAggregateDemandKind.AGGREGATE_OPERATION,
                R.AGGREGATE,
                P.VALUE,
            )
            cause, antecedents = (
                witness.source.item,
                (witness.aggregation, *witness.arguments),
            )
        elif isinstance(witness, aggregation.ProjectSQLAggregateProjection):
            kind, role, provenance = (
                aggregation.ProjectSQLAggregateDemandKind.RESULT_PROJECTION,
                R.AGGREGATE_PROJECTION,
                P.VALUE,
            )
            cause, antecedents = (
                witness.semantic.item,
                (witness.aggregation, witness.input),
            )
        else:
            kind, role, provenance = (
                aggregation.ProjectSQLAggregateDemandKind.RETAINED_RISK,
                R.AGGREGATE_RISK,
                P.TYPE_PROOF,
            )
            cause, antecedents = owner.definition, (witness.aggregation,)
        original = origin(
            witness.ref, role, provenance, owner, cause, witness, antecedents
        )
        demand_ref = ref(K.DEMAND)
        demand_origin = origin(
            demand_ref, R.DEMAND, provenance, owner, cause, witness, (original,)
        )
        demands.append(
            aggregation.ProjectSQLAggregateDemand(
                ref=demand_ref,
                kind=kind,
                witness=witness,
                subject=witness.ref,
                origin=demand_origin,
            )
        )
        if isinstance(witness, aggregation.ProjectSQLAggregateProjection):
            export = export_by_ref[witness.export]
            origin(
                export.ref,
                R.EXPORT,
                P.VALUE,
                owner,
                witness.semantic.item,
                export.field,
                (witness.ref,),
            )

    window_by_ref = {value.ref: value for value in window_values}
    for witness in (
        *window_values,
        *window_uses,
        *window_arguments,
        *window_policies,
        *window_projections,
    ):
        value = (
            witness
            if isinstance(witness, windows.ProjectSQLWindow)
            else window_by_ref[witness.window]
        )
        owner = block_by_ref[value.block].selected.owner
        if isinstance(witness, windows.ProjectSQLWindow):
            kind, role, provenance = (
                windows.ProjectSQLWindowDemandKind.INPUT_BAG_AND_RESULT,
                R.WINDOW,
                P.MEMBERSHIP,
            )
            cause, antecedents = witness.authored, (witness.block, *witness.inputs)
        elif isinstance(witness, windows.ProjectSQLWindowUse):
            kind, role, provenance = (
                windows.ProjectSQLWindowDemandKind.INPUT_USE,
                R.WINDOW_USE,
                P.VALUE,
            )
            cause, antecedents = (
                witness.expression,
                (witness.window,)
                if witness.input is None
                else (witness.window, witness.input),
            )
        elif isinstance(witness, windows.ProjectSQLWindowArgument):
            kind, role, provenance = (
                windows.ProjectSQLWindowDemandKind.ARGUMENT,
                R.WINDOW_ARGUMENT,
                P.VALUE,
            )
            cause, antecedents = (
                witness.expression,
                (witness.window,)
                if witness.use is None
                else (witness.window, witness.use),
            )
        elif isinstance(witness, windows.ProjectSQLWindowPolicy):
            kind, role, provenance = (
                windows.ProjectSQLWindowDemandKind.POLICY,
                R.WINDOW_POLICY,
                P.TYPE_PROOF,
            )
            cause, antecedents = value.authored, (witness.window,)
        else:
            kind, role, provenance = (
                windows.ProjectSQLWindowDemandKind.PROJECTION,
                R.WINDOW_PROJECTION,
                P.VALUE,
            )
            cause, antecedents = witness.semantic.item, (witness.window, witness.input)
        original = origin(
            witness.ref, role, provenance, owner, cause, witness, antecedents
        )
        demand_ref = ref(K.DEMAND)
        demand_origin = origin(
            demand_ref, R.DEMAND, provenance, owner, cause, witness, (original,)
        )
        demands.append(
            windows.ProjectSQLWindowDemand(
                ref=demand_ref,
                subject=witness.ref,
                kind=kind,
                witness=witness,
                origin=demand_origin,
            )
        )
        if isinstance(witness, windows.ProjectSQLWindowProjection):
            origin(
                witness.export,
                R.EXPORT,
                P.VALUE,
                owner,
                witness.semantic.item,
                export_by_ref[witness.export].field,
                (witness.ref,),
            )

    selected = _one(
        tuple(d for d in bindings.definitions if d.entry.owner is selected_owner),
        "selected SQL definition",
    )
    plan = object.__new__(ProjectSQLPlan)
    for name, value in dict(
        scope=bindings.scope,
        bindings=bindings,
        sources=bindings.sources,
        blocks=tuple(blocks),
        input_uses=bindings.input_uses,
        source_ports=bindings.source_ports,
        input_ports=bindings.input_ports,
        all_exports=bindings.all_exports,
        exports=selected.exports,
        projections=tuple(projections),
        boundaries=bindings.boundaries,
        symbols=tuple(symbols),
        origins=tuple(origins),
        demands=tuple(demands),
        expression_sites=tuple(sites),
        expressions=tuple(expressions),
        operands=tuple(operands),
        stage_ports=tuple(ports),
        let_values=tuple(lets),
        filters=tuple(filters),
        joins=tuple(joins),
        join_inputs=tuple(join_inputs),
        join_ports=tuple(join_ports),
        relationship_matches=tuple(relationship_matches),
        join_tails=tuple(join_tails),
        single_matches=tuple(obligations),
        single_match_proofs=tuple(proof_images),
        aggregations=tuple(aggregate_stages),
        group_keys=tuple(group_keys),
        aggregates=tuple(aggregate_values),
        aggregate_projections=tuple(aggregate_projections),
        aggregate_risks=tuple(aggregate_risks),
        windows=tuple(window_values),
        window_uses=tuple(window_uses),
        window_arguments=tuple(window_arguments),
        window_policies=tuple(window_policies),
        window_projections=tuple(window_projections),
    ).items():
        object.__setattr__(plan, name, value)
    return plan
