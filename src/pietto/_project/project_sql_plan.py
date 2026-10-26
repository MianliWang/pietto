"""Private selected static-source and contextual row SQL planning.

Names are presentation. References belong to one immutable planning scope;
semantic fields, producer definitions and input uses remain distinct.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pietto.semantic.existence_generators import AnyUseInfo, AnyValueInfo
    from pietto._project.project_query_block_ir import (
        CompiledQueryBlockIR,
        CompiledIRReference,
        CompiledIRField,
        CompiledIROperator,
    )
    from pietto._project.project_compiled_schema import Address
    from pietto._project.project_single_match import (
        CompiledSingleMatchRequest,
        CompiledSingleMatchAssessment,
        CompiledSingleMatchProof,
    )


from pietto._project import project_sql_plan_aggregation as aggregation
from pietto._project import project_sql_plan_windows as windows
from pietto._project import project_sql_plan_results as results
from pietto._project import project_sql_plan_sets as sets
from pietto._project import project_sql_plan_values as valuesplan
from pietto._project import project_sql_plan_literals as literals

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Never, cast
from collections.abc import Mapping
from types import MappingProxyType
from pietto._project import project_sql_plan_expressions as row
from pietto._project.existence_values import (
    ProjectAnyField,
    ProjectAnyLetValue,
    ProjectAnyRowBinding,
    ProjectAnyValue,
)
from pietto.ast_nodes import AnyExpr
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
from pietto.semantic.catalog import is_builtin_function_name
from pietto.semantic.aggregates import semantic_aggregate_call_name
from pietto.semantic.expressions import query_parameter_value_type
from pietto._project.query_parameters import reads_header
from pietto.ir.model import SymbolId, SymbolNamespace

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
from pietto._project.project_completion import (
    ProjectCaptureUse,
    ProjectCompletionDependency,
    ProjectExpressionBlockUse,
)
from pietto._project.project_ir_composition import ProjectIRCrossRelationEdge
from pietto._project.project_ir_operators import (
    ProjectIRLogicalOperatorKind,
    ProjectIRLogicalOperatorOccurrence,
)
from pietto._project.project_ir_relational_properties import (
    ProjectIROutputFieldOccurrence,
)
from pietto._project.project_query_block_ir import (
    ProjectIRCaptureStage,
    ProjectIRCaptureUse,
    ProjectIRExpressionBlockUse,
    ProjectIRQueryBlockEntry,
    ProjectIRConcreteQueryBlockEntry,
    ProjectIRCompletedSetOperationOutput,
    ProjectIRCompletedValuesOutput,
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
from pietto import ast_nodes as ast
from pietto.ast_nodes import GroupByItem
from pietto.ast_nodes import (
    AuthoredJoinKind,
    CaptureClause,
    CapturedFieldExpr,
    JoinOnClause,
    Expression,
    UnaryExpr,
    BinaryExpr,
    ComparisonExpr,
    BetweenExpr,
    CastExpr,
    ConditionalExpr,
    IsNullExpr,
    CallExpr,
    DottedNameExpr,
    FromClause,
    LiteralExpr,
    ParameterRefExpr,
    MembershipExpr,
    NameExpr,
    QueryDef,
    RelationExistsExpr,
    RelationScalarExpr,
    RelationMembershipExpr,
    SelectItem,
    SetRelationDef,
    SetOperationBody,
    SetOperand,
    SourceDef,
    TableDef,
    TableFunctionFromClause,
    TableFunctionRelationDef,
    ValuesBody,
    ValuesColumn,
    ValuesRelationDef,
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

_KNOWN_DEFINITIONS = frozenset(
    {
        ast.TypeDef,
        ast.EnumDef,
        ast.ShapeDef,
        ast.ConstraintDef,
        ast.DeriveDef,
        ast.SourceDef,
        ast.TableDef,
        ast.QueryDef,
        ast.SetRelationDef,
        ast.ValuesRelationDef,
        ast.TableFunctionRelationDef,
    }
)


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
    owners = {_owner_key(o): o for o in root.owners}
    incoming: dict[tuple[int, int, int, int], list[ProjectCompletionDependency]] = {
        k: [] for k in owners
    }
    for dependency in root.dependencies:
        consumer = _owner_key(dependency.consumer)
        target = _owner_key(dependency.target)
        if (
            owners.get(consumer) is not dependency.consumer
            or owners.get(target) is not dependency.target
        ):
            raise ValueError("ProjectSQLPlan dependency has foreign endpoints.")
        incoming[consumer].append(dependency)
    # An expression block use reads its whole target block, so the target and
    # every source it reaches belong to the statement, never as an input use.
    reads: dict[tuple[int, int, int, int], list[ProjectIRExpressionBlockUse]] = {
        k: [] for k in owners
    }
    for edge in root.expression_uses:
        consumer = _owner_key(edge.use.consumer)
        target = _owner_key(edge.use.target)
        if (
            owners.get(consumer) is not edge.use.consumer
            or owners.get(target) is not edge.use.target
        ):
            raise ValueError("ProjectSQLPlan expression use has foreign endpoints.")
        reads[consumer].append(edge)
    pending = [_owner_key(selected)]
    entries_by_owner = {_owner_key(e.owner): e for e in root.entries}
    reached: set[tuple[int, int, int, int]] = set()
    while pending:
        key = pending.pop()
        if key not in reached:
            reached.add(key)
            pending.extend(_owner_key(d.target) for d in incoming[key])
            pending.extend(_owner_key(e.use.target) for e in reads[key])
            for join in joining.join_images(entries_by_owner[key]):
                for image in join.inputs:
                    producer = image.producer
                    if producer is not None:
                        producer_key = _owner_key(producer)
                        if owners.get(producer_key) is not producer:
                            raise ValueError(
                                "JOIN evidence closure has a foreign producer."
                            )
                        pending.append(producer_key)
    return tuple(e for e in root.entries if _owner_key(e.owner) in reached)


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
    orderings = results.order_index(completed)
    if not completed.ok:
        add(K.SEMANTIC_RESULT_UNSUCCESSFUL, selected, completed)
    block_reads: dict[int, set[int]] = {}
    for edge in bundle.root.expression_uses:
        block_reads.setdefault(id(edge.use.consumer), set()).add(
            id(edge.use.expression)
        )
    # A captured field read is lowered only through its imaged capture edge.
    captured_reads: dict[int, set[int]] = {}
    for captured in bundle.root.captured_fields:
        captured_reads.setdefault(id(captured.capture.capture.inner), set()).add(
            id(captured.expression)
        )
    for entry in _closure(bundle, selected):
        owner, definition = entry.owner, entry.owner.definition
        if type(definition) not in _KNOWN_DEFINITIONS:
            add(K.IR_STAGE, owner, entry)
            continue
        if isinstance(entry, ProjectIRQueryBlockTerminal):
            add(K.ACTIVE_OUTPUT_UNAVAILABLE, owner, entry)
        if isinstance(definition, SourceDef):
            if _static_connector(definition) is None:
                add(K.STATIC_SOURCE_UNAVAILABLE, owner, entry)
        elif isinstance(definition, SetRelationDef):
            if not isinstance(
                entry,
                (ProjectIRCompletedSetOperationOutput, ProjectIRQueryBlockTerminal),
            ):
                raise ValueError("SET body requires its exact completed SET IR entry")
        elif isinstance(definition, (ValuesRelationDef, TableFunctionRelationDef)):
            if not isinstance(
                entry, (ProjectIRCompletedValuesOutput, ProjectIRQueryBlockTerminal)
            ):
                raise ValueError("VALUES body requires its exact completed IR entry")
        elif isinstance(definition, (TableDef, QueryDef)):
            if joining.joined_tail(entry) is None:
                for clause in definition.join_clauses:
                    add(K.JOIN, owner, entry, clause)
            else:
                for image in joining.join_images(entry):
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
                            if any(
                                isinstance(node, CallExpr)
                                and _callable_symbol(node) is None
                                for node in nodes
                            ):
                                add(K.CALL_AUTHORITY, owner, entry, clause)
                            elif any(
                                type(node)
                                not in {
                                    LiteralExpr,
                                    ParameterRefExpr,
                                    NameExpr,
                                    DottedNameExpr,
                                    WindowExpr,
                                    UnaryExpr,
                                    BinaryExpr,
                                    ComparisonExpr,
                                    IsNullExpr,
                                    BetweenExpr,
                                    ConditionalExpr,
                                    MembershipExpr,
                                    CastExpr,
                                    CallExpr,
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
            if not isinstance(entry, ProjectIRQueryBlockTerminal) and not results.ready(
                entry, orderings
            ):
                add(K.ORDER, owner, entry, definition.order_by_clause)
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
                    ProjectIRLogicalOperatorKind.RELATION_ORDERING,
                    ProjectIRLogicalOperatorKind.LIMIT,
                }:
                    if operator.kind.value != "distinct":
                        add(K.IR_STAGE, owner, entry, operator)
            if not isinstance(entry, ProjectIRQueryBlockTerminal):
                for kind, site in _row_blockers(
                    completed,
                    entry,
                    frozenset(block_reads.get(id(owner), ())),
                    frozenset(captured_reads.get(id(owner), ())),
                ):
                    add(kind, owner, entry, site)
    return tuple(result)


def _row_blockers(completed, entry, block_reads=frozenset(), captured=frozenset()):
    K = ProjectSQLPlanBlockerKind
    authority = row.row_authority(completed, entry)
    definition = entry.owner.definition
    aggregate = aggregation.authority(completed, entry)
    if isinstance(authority, row.ProjectSQLJoinedRowAuthority):
        return (
            *_joined_row_blockers(entry, authority, aggregate is not None, block_reads),
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
    if (
        block_reads
        - frozenset(
            id(value.expression)
            for condition in completed.roots.join_conditions.entries
            if condition.use.owner is entry.owner
            for value in existence_values(condition)
        )
    ) - _site_block_reads(
        site
        for site, _evidence, _references in sites
        if not isinstance(site, LetBinding)
        or any(isinstance(n, AnyExpr) for n in row.scalar_nodes(site.expression))
    ):
        # A block read outside a WHERE or ungrouped SELECT value is not lowered.
        blockers.append((K.EXPRESSION_EVIDENCE, None))
    input_fields = {id(f): f for f in authority.input_schema.fields.values()}
    binding_ordinals = {id(f.binding): i for i, f in enumerate(authority.lets)}
    selection_ordinals = {id(f.item): i for i, f in enumerate(authority.selections)}
    supported = {
        LiteralExpr,
        ParameterRefExpr,
        NameExpr,
        DottedNameExpr,
        UnaryExpr,
        BinaryExpr,
        ComparisonExpr,
        IsNullExpr,
        BetweenExpr,
        ConditionalExpr,
        MembershipExpr,
        CastExpr,
        CallExpr,
    }
    for site, evidence, references in sites:
        nodes = row.scalar_nodes(
            _normalized_scalar_expression(site.expression, evidence)
        )
        admitted_reads = block_reads | frozenset(
            id(value.expression)
            for value in existence_values(evidence)
            if id(value.input.binding.expression) in block_reads
        )
        if any(isinstance(n, CallExpr) and _callable_symbol(n) is None for n in nodes):
            blockers.append((K.CALL_AUTHORITY, site))
        elif any(
            type(n) in _BLOCK_READS
            and (
                (isinstance(site, LetBinding) and type(n) is not AnyExpr)
                or id(n) not in admitted_reads
            )
            for n in nodes
        ) or any(
            type(n) is CapturedFieldExpr
            and (isinstance(site, LetBinding) or id(n) not in captured)
            for n in nodes
        ):
            # A block read needs its own retained expression block use, a
            # captured field its imaged capture edge, and a row let stays a
            # value of its input row only.
            blockers.append((K.EXPRESSION_EVIDENCE, site))
        elif evidence is None or any(
            type(n) not in supported
            and type(n) not in _BLOCK_READS
            and type(n) is not CapturedFieldExpr
            for n in nodes
        ):
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
                n
                for n in outer_scalar_nodes(
                    _normalized_scalar_expression(site.expression, evidence)
                )
                if isinstance(n, (NameExpr, DottedNameExpr))
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
            values = {id(n): (n, v) for n, v in expression_types(evidence).items()}
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
                    or (
                        values[id(n)][1].kind is not ValueTypeKind.KNOWN
                        and not _any_null_predicate(n, evidence)
                    )
                    for n in nodes
                )
                or any(
                    r.status is not ProjectModuleCandidateBucketStatus.CONCRETE
                    for r in references
                )
            ):
                blockers.append((K.EXPRESSION_EVIDENCE, site))
    return (*blockers, *_aggregate_blockers(entry, authority, aggregate))


def _joined_row_blockers(entry, authority, aggregating=False, block_reads=frozenset()):
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
    if (
        block_reads
        - frozenset(
            id(node)
            for use in authority.binding_environment.ledger.uses
            if use.clause.on_clause is not None
            for node in row.scalar_nodes(use.clause.on_clause.expression)
            if isinstance(node, AnyExpr)
        )
    ) - _site_block_reads(
        site
        for site, _evidence, _references in sites
        if not isinstance(site, LetBinding)
        or any(isinstance(n, AnyExpr) for n in row.scalar_nodes(site.expression))
    ):
        result.append((K.EXPRESSION_EVIDENCE, None))
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
            for node in outer_scalar_nodes(
                _normalized_scalar_expression(site.expression, evidence)
            )
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
        kind = _scalar_blocker(
            _normalized_scalar_expression(site.expression, evidence),
            evidence,
            block_reads=frozenset(
                id(value.input.binding.expression)
                for value in existence_values(evidence)
            )
            if isinstance(evidence, row.ProjectJoinedLetValue)
            else block_reads,
        )
        if kind is not None:
            result.append((kind, site))
    return tuple(result)


# Expression nodes that read a whole block through an expression block use.
_BLOCK_READS = frozenset(
    {RelationExistsExpr, RelationScalarExpr, RelationMembershipExpr, AnyExpr}
)


def existence_values(evidence) -> tuple[ProjectAnyValue, ...]:
    """Read checked ANY scopes from the actual site's existing semantic authority."""
    if isinstance(evidence, row.ProjectJoinCondition):
        roots = evidence.environment.existence_values
    elif isinstance(
        evidence,
        (
            ProjectNoJoinScalarExpression,
            row.ProjectConcreteJoinedNamespaceExpression,
            row.ProjectJoinedLetValue,
        ),
    ):
        roots = evidence.existence_values
    elif isinstance(evidence, ProjectModuleLetBindingFact):
        roots = tuple(
            value
            for value in evidence.scope_facts.existence_values
            if value.context is evidence.binding
        )
    else:
        return ()
    values = []
    pending = list(reversed(roots))
    while pending:
        value = pending.pop()
        values.append(value)
        pending.extend(reversed(value.nested))
    return tuple(values)


def outer_scalar_nodes(expression):
    """The outer row's scalar occurrences, keeping each local ANY scope atomic."""
    values = row.scalar_nodes(expression)
    return row.scalar_nodes(
        expression, tuple(n for n in values if isinstance(n, AnyExpr))
    )


def _any_null_predicate(node, evidence):
    return (
        type(node) is LiteralExpr
        and node.value is None
        and any(value.predicate is node for value in existence_values(evidence))
    )


def expression_types(evidence):
    values = dict(row.evidence_types(evidence))
    for scope in existence_values(evidence):
        values.update(scope.value_types)
    return values


def predicate_expression(site):
    """The canonical predicate-use record of one actual SQL expression site."""
    if isinstance(site, row.ProjectSQLMatchSite):
        return site.evidence.environment.predicate_expression
    if isinstance(site.evidence, aggregation.ProjectAggregateExpressionAnalysis):
        return site.evidence.predicate_expression
    if isinstance(site.evidence, ProjectModuleLetBindingFact):
        from pietto._project.project_query_block_ir_inspection import (
            _predicate_expressions,
        )

        matches = tuple(
            record
            for record in _predicate_expressions(site.ref.scope.analysis_bundle.root)
            if record.owner is site.owner and record.context is site.occurrence
        )
        if len(matches) > 1:
            raise ValueError("LET predicate reads require one exact canonical context.")
        return None if not matches else matches[0]
    if isinstance(
        site.evidence,
        (
            ProjectNoJoinScalarExpression,
            row.ProjectConcreteJoinedNamespaceExpression,
            row.ProjectJoinedLetValue,
        ),
    ):
        return site.evidence.predicate_expression
    return None


def predicate_bindings(site):
    """Exact visible row bindings in input order, without hidden target compression."""
    from pietto._project.project_relationship_uses import project_join_binding_visible

    if isinstance(site, row.ProjectSQLMatchSite):
        environment = site.evidence.environment
        return tuple(
            binding
            for binding in environment.bindings
            if project_join_binding_visible(
                binding,
                environment.ledger.uses[: environment.use.identity.join_position],
            )
        )
    if isinstance(
        site.evidence,
        (row.ProjectConcreteJoinedNamespaceExpression, row.ProjectJoinedLetValue),
    ):
        ledger = site.evidence.namespace.binding_environment.ledger
        return tuple(
            binding
            for binding in ledger.bindings
            if project_join_binding_visible(binding, ledger.uses)
        )
    record = predicate_expression(site)
    if record is None:
        return ()
    bindings = tuple(
        binding
        for arguments in record.argument_bindings
        for binding in arguments
        if not isinstance(binding, ProjectAnyRowBinding)
    )
    if not bindings:
        return ()
    if any(binding is not bindings[0] for binding in bindings):
        raise ValueError(
            "Single-input predicate arguments require the same exact FROM occurrence."
        )
    return (bindings[0],)


def _normalized_scalar_expression(
    expression: Expression, evidence: object
) -> Expression:
    """Read the checked row expression while keeping its authored site separate."""
    if isinstance(evidence, ProjectModuleLetBindingFact):
        return evidence.scope_facts.binding_expressions[evidence.binding.name]
    if isinstance(evidence, row.ProjectJoinedLetValue):
        return evidence.normalized_expression
    if (
        isinstance(evidence, aggregation.ProjectAggregateExpressionAnalysis)
        and evidence.predicate_expression is not None
    ):
        normalized = evidence.effective_argument
        if normalized is None:
            raise ValueError(
                "Predicate aggregate evidence requires its normalized argument."
            )
        return normalized
    if isinstance(
        evidence,
        (ProjectNoJoinScalarExpression, row.ProjectConcreteJoinedNamespaceExpression),
    ):
        return evidence.normalized_expression
    return expression


def _site_block_reads(sites) -> frozenset[int]:
    """Identities of the block reads written inside the given row value sites."""
    return frozenset(
        id(node)
        for site in sites
        for node in row.scalar_nodes(site.expression)
        if type(node) in _BLOCK_READS
    )


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
        if not isinstance(call, CallExpr) or (
            len(call.arguments) > 1
            and (
                semantic_aggregate_call_name(call) != "string_agg"
                or len(call.arguments) != 2
                or not call.aggregate_order_by
            )
        ):
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
            authored = (
                *call.arguments,
                *(item.expression for item in call.aggregate_order_by),
            )
            if evidence is None or any(
                _scalar_blocker(
                    _normalized_scalar_expression(argument, evidence), evidence, source
                )
                is not None
                for argument in authored
            ):
                return ((K.EXPRESSION_EVIDENCE, source.item),)
            leaves = tuple(
                n
                for argument in authored
                for n in row.scalar_nodes(
                    _normalized_scalar_expression(argument, evidence)
                )
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
        for node in outer_scalar_nodes(condition.expression)
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
    return _scalar_blocker(
        condition.expression,
        condition,
        block_reads=frozenset(
            id(value.input.binding.expression) for value in existence_values(condition)
        ),
    )


def _scalar_blocker(expression, evidence, aggregate=None, block_reads=frozenset()):
    block_reads = block_reads | frozenset(
        id(value.expression)
        for value in existence_values(evidence)
        if id(value.input.binding.expression) in block_reads
    )
    nodes = row.scalar_nodes(expression)
    if aggregate is None and any(
        isinstance(node, CallExpr) and _callable_symbol(node) is None for node in nodes
    ):
        return ProjectSQLPlanBlockerKind.CALL_AUTHORITY
    if aggregate is not None and (
        aggregation.argument_evidence(aggregate) is not evidence
        or not aggregation.arguments(aggregate)
        or not any(
            _normalized_scalar_expression(argument, evidence) is expression
            for argument in (
                *aggregation.arguments(aggregate),
                *(
                    item.expression
                    for item in aggregate.item.expression.aggregate_order_by
                ),
            )
        )
    ):
        return ProjectSQLPlanBlockerKind.EXPRESSION_EVIDENCE
    supported = {
        LiteralExpr,
        ParameterRefExpr,
        NameExpr,
        DottedNameExpr,
        UnaryExpr,
        BinaryExpr,
        ComparisonExpr,
        IsNullExpr,
        BetweenExpr,
        ConditionalExpr,
        MembershipExpr,
        CastExpr,
        CallExpr,
    }
    values = {
        id(node): (node, value) for node, value in expression_types(evidence).items()
    }
    if any(
        (
            type(node) not in supported
            and not (type(node) in _BLOCK_READS and id(node) in block_reads)
        )
        or id(node) not in values
        or values[id(node)][0] is not node
        or (
            values[id(node)][1].kind is not ValueTypeKind.KNOWN
            and not _any_null_predicate(node, evidence)
        )
        for node in nodes
    ):
        return ProjectSQLPlanBlockerKind.EXPRESSION_EVIDENCE
    return None


def _callable_symbol(call: CallExpr) -> SymbolId | None:
    """Return the canonical builtin callable identity, never a callee spelling."""
    if type(call.callee) is not NameExpr or not is_builtin_function_name(
        call.callee.name
    ):
        return None
    return SymbolId(SymbolNamespace.CALLABLE, call.callee.name)


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
    LITERAL_SITE = "literal_site"
    LITERAL_SLOT = "literal_slot"
    FIXED_LITERAL_VALUE = "fixed_literal_value"
    BIND_USE = "bind_use"
    SET_BODY = "set_body"
    SET_OPERAND = "set_operand"
    SET_INPUT = "set_input"
    SET_COLUMN = "set_column"
    VALUES_BODY = "values_body"
    VALUES_COLUMN = "values_column"
    RESULT_BOUNDARY = "result_boundary"
    RESULT_PORT = "result_port"
    DISTINCT = "distinct"
    QUOTIENT_FIELD = "quotient_field"
    ORDER = "relation_order"
    ORDER_ITEM = "order_item"
    ORDER_EXPRESSION = "order_expression"
    ORDER_USE = "order_use"
    HIDDEN_ORDER_REQUIREMENT = "hidden_order_requirement"
    RESULT_LIMIT = "result_limit"
    RESULT_EXPORT = "result_export"
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
    EXPRESSION_BLOCK_USE = "expression_block_use"
    CAPTURE = "capture"
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


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLExpressionBlockUse:
    """ExpressionBlockUseV1 in the plan: one expression occurrence reads one
    whole producer definition. It is never an input use, boundary or port."""

    ref: ProjectSQLPlanRef
    producer: ProjectSQLPlanRef
    consumer: ProjectSQLPlanRef
    edge: ProjectIRExpressionBlockUse

    @property
    def use(self) -> ProjectExpressionBlockUse:
        return self.edge.use

    @property
    def expression(self) -> Expression:
        return self.edge.use.expression


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLCapture:
    """CaptureV1 in the plan: one capture line of ``inner`` reads the current
    row of ``outer`` at the outer's single read of ``inner``.

    ``read`` is that read's expression value, ``block`` its SELECT block and
    ``ports`` the block's stage ports of the captured input's fields, in the
    order of ``edge.fields``. It is never an input use, boundary or port.
    """

    ref: ProjectSQLPlanRef
    inner: ProjectSQLPlanRef
    outer: ProjectSQLPlanRef
    read: ProjectSQLPlanRef
    block: ProjectSQLPlanRef
    ports: tuple[ProjectSQLPlanRef, ...]
    edge: ProjectIRCaptureUse

    @property
    def use(self) -> ProjectCaptureUse:
        return self.edge.capture


def capture_stage_ports(
    edge: ProjectIRCaptureUse, ports: tuple[row.ProjectSQLStagePort, ...]
) -> tuple[row.ProjectSQLStagePort, ...] | None:
    """The read block's stage ports of one capture's outer row fields.

    An unjoined outer body carries its input row first, in input order; a
    joined body carries each visible field keyed by its joined position.
    """
    fields = edge.checkpoint.output.row_shape.fields
    found: list[row.ProjectSQLStagePort] = []
    for position in edge.fields:
        if edge.checkpoint.stage is ProjectIRCaptureStage.INPUT:
            port = ports[position] if 0 <= position < len(ports) else None
            valid = (
                port is not None
                and type(port.key) is ProjectRowField
                and port.key.name == fields[position].evidence.name
            )
        else:
            matches = tuple(
                item
                for item in ports
                if type(item.key) is row.ProjectScalarEnvironmentField
                and item.key.position == position
            )
            port = matches[0] if len(matches) == 1 else None
            key = None if port is None else port.key
            valid = (
                type(key) is row.ProjectScalarEnvironmentField
                and key.evidence is fields[position].evidence
            )
        if (
            not valid
            or port is None
            or port.kind is not row.ProjectSQLStagePortKind.INPUT
        ):
            return None
        found.append(port)
    return tuple(found)


def lateral_capture_ports(
    edge: ProjectIRCaptureUse, left: tuple[joining.ProjectSQLJoinPort, ...]
) -> tuple[ProjectSQLPlanRef, ...] | None:
    """A LATERAL JOIN's left input MATCH ports of one capture's fields.

    The checkpoint row is the JOIN's own output, whose left fields keep the
    left input's positions.
    """
    fields = edge.checkpoint.output.row_shape.fields
    if edge.checkpoint.stage is not ProjectIRCaptureStage.LATERAL:
        return None
    found: list[ProjectSQLPlanRef] = []
    for position in edge.fields:
        if not 0 <= position < len(left):
            return None
        port = left[position]
        if (
            port.kind is not joining.ProjectSQLJoinPortKind.MATCH
            or port.position != position
            or port.field.evidence is not fields[position].evidence
        ):
            return None
        found.append(port.ref)
    return tuple(found)


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
    LITERAL_SITE = "literal_site"
    LITERAL_SLOT = "literal_slot"
    FIXED_LITERAL_VALUE = "fixed_literal_value"
    BIND_USE = "bind_use"
    SET_BODY = "set_body"
    SET_OPERAND = "set_operand"
    SET_INPUT = "set_input"
    SET_COLUMN = "set_column"
    VALUES_BODY = "values_body"
    VALUES_COLUMN = "values_column"
    RESULT_BOUNDARY = "result_boundary"
    RESULT_PORT = "result_port"
    DISTINCT = "distinct"
    QUOTIENT_FIELD = "quotient_field"
    ORDER = "relation_order"
    ORDER_ITEM = "order_item"
    ORDER_EXPRESSION = "order_expression"
    ORDER_USE = "order_use"
    HIDDEN_ORDER_REQUIREMENT = "hidden_order_requirement"
    RESULT_LIMIT = "result_limit"
    RESULT_EXPORT = "result_export"
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
    EXPRESSION_BLOCK_USE = "expression_block_use"
    CAPTURE = "capture"
    SYMBOL = "symbol"
    DEMAND = "demand"


class ProjectSQLOriginProvenance(StrEnum):
    VALUE = "value"
    MEMBERSHIP = "membership"
    TYPE_PROOF = "type_proof"
    GENERATED_STRUCTURE = "generated_structure"


type ProjectSQLCause = (
    SetOperationBody
    | ValuesBody
    | ValuesColumn
    | ValuesRelationDef
    | TableFunctionFromClause
    | TableFunctionRelationDef
    | DistinctClause
    | OrderByClause
    | LimitClause
    | JoinOnClause
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
    | CaptureClause
)

type ProjectSQLOriginEvidence = (
    literals.Witness
    | sets.Witness
    | valuesplan.Witness
    | results.Witness
    | windows.Witness
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
    | ProjectExpressionBlockUse
    | ProjectCaptureUse
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
    literals.ProjectSQLLiteralDemand
    | sets.ProjectSQLSetDemand
    | valuesplan.ProjectSQLValuesDemand
    | results.ProjectSQLResultDemand
    | ProjectSQLSourceRealizationDemand
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
    expression_block_uses: tuple[ProjectSQLExpressionBlockUse, ...]
    symbols: tuple[ProjectSQLSymbol, ...]
    origins: tuple[ProjectSQLOrigin, ...]
    demands: tuple[ProjectSQLDemand, ...]

    def __init__(self) -> Never:
        raise TypeError("SQL bindings are closed; use build_project_sql_bindings.")


# repr=False: a generated repr expands the shared plan graph as a tree.
@dataclass(frozen=True, slots=True, kw_only=True, eq=False, init=False, repr=False)
class ProjectSQLPlan:
    literal_policy: literals.ProjectSQLLiteralPolicy
    parameters: tuple[row.ProjectSQLQueryParameter, ...]
    literal_sites: tuple[literals.ProjectSQLLiteralSite, ...]
    literal_slots: tuple[literals.ProjectSQLLiteralSlot, ...]
    bind_uses: tuple[literals.ProjectSQLBindUse, ...]
    fixed_envelope: literals.ProjectSQLFixedEnvelope
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
    expression_block_uses: tuple[ProjectSQLExpressionBlockUse, ...]
    captures: tuple[ProjectSQLCapture, ...]
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
    result_boundaries: tuple[results.ProjectSQLResultBoundary, ...]
    result_ports: tuple[results.ProjectSQLResultPort, ...]
    distincts: tuple[results.ProjectSQLDistinct, ...]
    quotient_fields: tuple[results.ProjectSQLQuotientField, ...]
    orders: tuple[results.ProjectSQLOrder, ...]
    order_items: tuple[results.ProjectSQLOrderItem, ...]
    order_expressions: tuple[results.ProjectSQLOrderExpression, ...]
    order_uses: tuple[results.ProjectSQLOrderUse, ...]
    hidden_order_requirements: tuple[results.ProjectSQLHiddenOrderRequirement, ...]
    result_limits: tuple[results.ProjectSQLResultLimit, ...]
    result_exports: tuple[results.ProjectSQLResultExport, ...]
    set_bodies: tuple[sets.ProjectSQLSetBody, ...]
    set_operands: tuple[sets.ProjectSQLSetOperand, ...]
    set_inputs: tuple[sets.ProjectSQLSetInput, ...]
    set_columns: tuple[sets.ProjectSQLSetColumn, ...]
    values_bodies: tuple[valuesplan.ProjectSQLValuesBody, ...]
    values_columns: tuple[valuesplan.ProjectSQLValuesColumn, ...]

    def __init__(self) -> Never:
        raise TypeError("ProjectSQLPlan is closed; use build_project_sql_plan.")

    @property
    def diagnostics(self) -> tuple[Diagnostic, ...]:
        return self.scope.completed.diagnostics

    @property
    def existence_generators(self) -> tuple[AnyUseInfo, ...]:
        """The exact authored ANY uses of this plan's retained owner definitions."""
        from pietto._project.project_query_block_ir_inspection import _existence_uses

        owners = tuple(value.entry.owner for value in self.bindings.definitions)
        return tuple(
            use
            for use in _existence_uses(self.scope.analysis_bundle.root)
            if any(owner.definition is use.owner for owner in owners)
        )

    @property
    def scalar_existence_generators(self) -> tuple[AnyValueInfo, ...]:
        """Every retained scalar ANY clone with its explicit original occurrence."""
        owners = tuple(value.entry.owner for value in self.bindings.definitions)
        return tuple(
            use
            for module in self.scope.analysis_bundle.root.completed.semantic_result.modules
            if module.parsed_input is not None
            for use in module.parsed_input.existence_values
            if any(
                owner.identity.module_path == module.path
                and owner.definition is use.owner
                for owner in owners
            )
        )


def _owner_key(owner: ProjectDeclarationOccurrence) -> tuple[int, int, int, int]:
    """Coordinates of one relation-body owner; a relation let has its own.

    A table-function input shares its body's positions and is told apart by
    the last coordinate.
    """

    let_position = -1 if owner.let_position is None else owner.let_position
    function = 0 if owner.table_function is None else 1
    return owner.module_position, owner.declaration_position, let_position, function


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
) -> dict[tuple[str, int, int, int, bool], ProjectModuleOriginPath]:
    """Index existing complete origin paths; no path construction or name lookup."""
    result: dict[tuple[str, int, int, int, bool], ProjectModuleOriginPath] = {}
    attribution = scope.analysis_bundle.root.base_plan.attribution
    for origin in attribution.origins:
        if origin.import_occurrence is not None:
            occurrence = origin.import_occurrence
            key = (
                origin.owning_module_path,
                occurrence.module_statement_position,
                occurrence.item_position,
                -1,
                False,
            )
        else:
            assert origin.local_occurrence is not None
            occurrence = origin.local_occurrence
            key = (
                origin.owning_module_path,
                -1,
                occurrence.declaration_position,
                -1 if occurrence.let_position is None else occurrence.let_position,
                occurrence.table_function,
            )
        if key in result:
            raise ValueError("Origin occurrence index must not choose a winner.")
        result[key] = origin
    return result


def _binding_origin(
    symbol: ProjectResolvedModuleRelationSymbol,
    index: Mapping[tuple[str, int, int, int, bool], ProjectModuleOriginPath],
) -> ProjectModuleOriginPath:
    imported = symbol.imported_binding
    target = symbol.target_occurrence
    key = (
        (
            imported.identity.owning_module_path,
            imported.request.module_statement_position,
            imported.request.item_position,
            -1,
            False,
        )
        if imported is not None
        else (
            symbol.owning_module_path,
            -1,
            target.declaration_position,
            -1 if target.let_position is None else target.let_position,
            target.table_function is not None,
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
    historical: dict[tuple[int, int, int, int], list[ProjectIRCrossRelationEdge]] = {}
    for edge in root.base_plan.cross_relation_edges:
        historical.setdefault(
            _owner_key(edge.consumer.semantic_facts.owner), []
        ).append(edge)
    by_owner = {_owner_key(e.owner): e for e in concrete}
    per_owner: dict[tuple[int, int, int, int], list[ProjectCompletionDependency]] = {}
    for dep in dependencies:
        dep.__post_init__()
        per_owner.setdefault(_owner_key(dep.consumer), []).append(dep)
    images: dict[tuple[tuple[int, int, int, int], int], ProjectSQLInputEdge] = {}
    for entry in concrete:
        key = _owner_key(entry.owner)
        deps = per_owner.get(key, ())
        if isinstance(entry.owner.definition, SourceDef):
            if deps:
                raise ValueError("A source definition cannot have relation inputs.")
            continue
        if isinstance(entry, ProjectIRCompletedValuesOutput):
            if deps:
                raise ValueError("A VALUES definition cannot have relation inputs.")
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
            joined_images = joining.join_images(entry)
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
            # Every external JOIN input has its authored dependency: no JOIN
            # is a relationship path with hidden hops.
            if any(not any(image is item for item in selected) for image in external):
                raise ValueError("Unbound external JOIN input has no authored use.")
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


def _expression_inventory(
    scope: ProjectSQLPlanScope,
) -> tuple[ProjectIRExpressionBlockUse, ...]:
    """Every expression block use whose consumer is in the statement closure."""
    reached = {
        _owner_key(e.owner)
        for e in _closure(scope.analysis_bundle, scope.selected_owner)
    }
    return tuple(
        edge
        for edge in scope.analysis_bundle.root.expression_uses
        if _owner_key(edge.use.consumer) in reached
    )


def _field_site(
    entry: ProjectIRConcreteQueryBlockEntry, position: int
) -> (
    SourceDef
    | TableDef
    | QueryDef
    | SetRelationDef
    | SelectItem
    | ValuesColumn
    | TableFunctionRelationDef
):
    definition = entry.owner.definition
    if isinstance(definition, (TableDef, QueryDef)) and len(
        definition.select_items
    ) == len(entry.active_properties.relational.fields):
        return definition.select_items[position]
    if isinstance(definition, ValuesRelationDef):
        return definition.body.columns[position]
    if isinstance(
        definition,
        (SourceDef, TableDef, QueryDef, SetRelationDef, TableFunctionRelationDef),
    ):
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
    if any(
        type(entry.owner.definition) not in _KNOWN_DEFINITIONS
        for entry in _closure(analysis_bundle, selected_owner)
    ):
        return ProjectSQLPlanUnavailable(
            completed=completed,
            analysis_bundle=analysis_bundle,
            selected_owner=selected_owner,
        )
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
    expression_block_uses: list[ProjectSQLExpressionBlockUse] = []
    for edge in _expression_inventory(scope):
        producer, consumer = (
            by_owner[_owner_key(edge.use.target)],
            by_owner[_owner_key(edge.use.consumer)],
        )
        if (
            edge.producer is not producer.entry
            or edge.consumer is not consumer.entry
            or edge.output is not producer.entry.output
        ):
            raise ValueError("Expression block use must read its active producer.")
        expression_block_uses.append(
            ProjectSQLExpressionBlockUse(
                ref=ref(K.EXPRESSION_BLOCK_USE),
                producer=producer.ref,
                consumer=consumer.ref,
                edge=edge,
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
        cast(
            TableDef | QueryDef | SetRelationDef | ValuesRelationDef,
            selected_owner.definition,
        ),
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
                SourceDef
                | TableDef
                | QueryDef
                | SetRelationDef
                | ValuesRelationDef
                | TableFunctionRelationDef,
                entry.owner.definition,
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
    for block_use in expression_block_uses:
        origin(
            block_use.ref,
            R.EXPRESSION_BLOCK_USE,
            P.GENERATED_STRUCTURE,
            block_use.use.consumer,
            block_use.expression,
            block_use.use,
            (block_use.producer,),
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
        expression_block_uses=tuple(expression_block_uses),
        symbols=tuple(symbols),
        origins=tuple(origins),
        demands=tuple(demands),
    ).items():
        object.__setattr__(bindings, name, value)
    return bindings


def _query_parameters(
    bindings: ProjectSQLBindings, selected_owner: ProjectDeclarationOccurrence
) -> tuple[row.ProjectSQLQueryParameter, ...]:
    """Header parameters of the selected entry query; no input may declare any."""
    for definition in bindings.definitions:
        owner = definition.entry.owner
        if (
            owner is not selected_owner
            and type(owner.definition) is QueryDef
            and owner.definition.parameters
        ):
            raise ValueError("A query with parameters cannot be a relation input.")
    declaration = selected_owner.definition
    if type(declaration) is not QueryDef:
        return ()
    return tuple(
        row.ProjectSQLQueryParameter(
            owner=selected_owner,
            ordinal=ordinal,
            declaration=parameter,
            tag=parameter.type.name,
            value_type=query_parameter_value_type(
                parameter.type.name, parameter.type.nullability
            ),
        )
        for ordinal, parameter in enumerate(declaration.parameters)
    )


def build_project_sql_plan(
    completed: ProjectConcreteCompletedSemanticResult,
    analysis_bundle: ProjectIRQueryBlockAnalysisBundle,
    selected_owner: ProjectDeclarationOccurrence,
    *,
    literal_policy: literals.ProjectSQLLiteralPolicy = literals.ProjectSQLLiteralPolicy.PRESERVE_LITERALS,
) -> ProjectSQLPlan | ProjectSQLPlanUnavailable:
    if type(literal_policy) is not literals.ProjectSQLLiteralPolicy:
        raise TypeError("Literal policy must be an exact ProjectSQLLiteralPolicy.")
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
    query_parameters = _query_parameters(bindings, selected_owner)
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
    block_uses_by_expression = {
        id(u.expression): u for u in bindings.expression_block_uses
    }
    uses_by_image = {id(u.edge): u for u in bindings.input_uses}
    # Every imaged capture of the statement keeps its plan ref in IR order; the
    # record itself is completed at the outer body's read of the let.
    capture_edges = tuple(
        edge
        for edge in analysis_bundle.root.capture_uses
        if id(edge.capture.inner) in definitions_by_owner
        and id(edge.capture.outer) in definitions_by_owner
    )
    captured_by_expression = {
        id(item.expression): item
        for item in analysis_bundle.root.captured_fields
        if any(item.capture is edge for edge in capture_edges)
    }
    captures: list[ProjectSQLCapture] = []
    joins_by_image = {}
    join_ports_by_ref = {}

    def ref(kind):
        position = counters.get(kind, 0)
        counters[kind] = position + 1
        return ProjectSQLPlanRef(scope=bindings.scope, kind=kind, position=position)

    capture_refs = {id(edge): ref(K.CAPTURE) for edge in capture_edges}

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
            else site.evidence.expression
            if isinstance(site, row.ProjectSQLMatchSite)
            else _normalized_scalar_expression(
                site.occurrence.expression, site.evidence
            )
        )
        if source_expression is None:
            raise ValueError("SQL expression site requires its checked expression.")
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
        types = {id(n): (n, v) for n, v in expression_types(site.evidence).items()}
        references = {id(row.reference_expression(r)): r for r in site.references}
        any_values = {
            id(value.expression): value for value in existence_values(site.evidence)
        }
        any_references = {
            id(reference.expression): reference
            for value in any_values.values()
            for reference in value.references
        }
        any_bindings = {id(value.input.binding): value for value in any_values.values()}

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
            elif isinstance(node, ParameterRefExpr):
                if not reads_header(site.owner, selected_owner) or not (
                    0 <= node.ordinal < len(query_parameters)
                ):
                    raise ValueError("Parameter read is outside its entry query.")
                parameter = query_parameters[node.ordinal]
                if (
                    parameter.declaration.name != node.name
                    or value_type != parameter.value_type
                ):
                    raise ValueError("Parameter read lost its declared type.")
                value = row.ProjectSQLParameterRead(
                    ref=node_ref,
                    site=site,
                    expression=node,
                    value_type=value_type,
                    parameter=parameter,
                )
            elif isinstance(node, AnyExpr):
                checked = any_values.get(id(node))
                if (
                    checked is None
                    or checked.expression is not node
                    or checked.diagnostics
                ):
                    raise ValueError("ANY requires its exact checked value.")
                use = block_uses_by_expression.get(id(checked.input.binding.expression))
                if (
                    use is None
                    or use.use.target is not checked.input.binding.target
                    or use.consumer is not definitions_by_owner[id(site.owner)].ref
                ):
                    raise ValueError("ANY requires its exact scheduled producer edge.")
                value = row.ProjectSQLAny(
                    ref=node_ref,
                    site=site,
                    expression=node,
                    value_type=value_type,
                    use=use.ref,
                    predicate=children[0],
                    evidence=checked,
                )
            elif (
                isinstance(node, (NameExpr, DottedNameExpr))
                and id(node) in any_references
            ):
                checked = any_references[id(node)]
                target = checked.target
                local_use = None
                position = None
                outer_port = None
                if isinstance(target, ProjectAnyField) and isinstance(
                    target.binding, ProjectAnyRowBinding
                ):
                    scope = any_bindings.get(id(target.binding))
                    use = block_uses_by_expression.get(id(target.binding.expression))
                    if scope is None or use is None or scope.input.schema is None:
                        raise ValueError("ANY field lost its lexical input occurrence.")
                    candidates = tuple(
                        i
                        for i, field in enumerate(scope.input.schema.fields.values())
                        if field is target.evidence
                    )
                    if len(candidates) != 1:
                        raise ValueError("ANY field requires one exact producer field.")
                    local_use, position = use.ref, candidates[0]
                else:
                    key = (
                        target.source_field
                        if isinstance(target, ProjectAnyField)
                        else target.authority.occurrence
                        if isinstance(target, ProjectAnyLetValue)
                        and isinstance(target.authority, row.ProjectJoinedLetValue)
                        else target.binding
                        if isinstance(target, ProjectAnyLetValue)
                        else None
                    )
                    port = local_ports.get(id(key))
                    if key is None or port is None or port.key is not key:
                        raise ValueError(
                            "ANY capture requires its exact current row port."
                        )
                    outer_port = port.ref
                value = row.ProjectSQLAnyReference(
                    ref=node_ref,
                    site=site,
                    expression=node,
                    value_type=value_type,
                    reference=checked,
                    use=local_use,
                    position=position,
                    port=outer_port,
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
                    if not isinstance(
                        reference,
                        (
                            aggregation.ProjectJoinedSatisfyingAggregateReference,
                            aggregation.ProjectJoinedSatisfyingOutputReference,
                            aggregation.ProjectRelationClauseDependencyFact,
                        ),
                    ):
                        raise ValueError(
                            "Satisfying site requires a retained result reference."
                        )
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
                if isinstance(site, aggregation.ProjectSQLAggregateSite):
                    if site.role is not row.ProjectSQLExpressionRole.AGGREGATE_ARGUMENT:
                        raise ValueError(
                            "Scalar calls require retained aggregate argument authority"
                        )
                    symbol = _callable_symbol(node)
                    if symbol is None:
                        raise ValueError(
                            "Aggregate scalar call lacks canonical authority"
                        )
                    value = aggregation.ProjectSQLAggregateArgumentCall(
                        ref=node_ref,
                        site=site,
                        expression=node,
                        value_type=value_type,
                        callee_symbol=symbol,
                        arguments=children,
                    )
                else:
                    symbol = _callable_symbol(node)
                    if symbol is None:
                        raise ValueError(
                            "Scalar call lacks canonical callable authority"
                        )
                    value = row.ProjectSQLScalarCall(
                        ref=node_ref,
                        site=site,
                        expression=node,
                        value_type=value_type,
                        callee_symbol=symbol,
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
            elif isinstance(node, ConditionalExpr):
                value = row.ProjectSQLConditional(
                    ref=node_ref,
                    site=site,
                    expression=node,
                    value_type=value_type,
                    when_true=children[0],
                    condition=children[1],
                    when_false=children[2],
                )
            elif isinstance(node, MembershipExpr):
                value = row.ProjectSQLMembership(
                    ref=node_ref,
                    site=site,
                    expression=node,
                    value_type=value_type,
                    value=children[0],
                    options=children[1:],
                )
            elif isinstance(
                node, (RelationExistsExpr, RelationScalarExpr, RelationMembershipExpr)
            ):
                block_use = block_uses_by_expression.get(id(node))
                if (
                    block_use is None
                    or block_use.consumer
                    is not definitions_by_owner[id(site.owner)].ref
                ):
                    raise ValueError("Block read lacks its exact expression block use.")
                if isinstance(node, RelationExistsExpr):
                    value = row.ProjectSQLRelationExists(
                        ref=node_ref,
                        site=site,
                        expression=node,
                        value_type=value_type,
                        use=block_use.ref,
                    )
                elif isinstance(node, RelationScalarExpr):
                    value = row.ProjectSQLRelationScalar(
                        ref=node_ref,
                        site=site,
                        expression=node,
                        value_type=value_type,
                        use=block_use.ref,
                    )
                else:
                    value = row.ProjectSQLRelationMembership(
                        ref=node_ref,
                        site=site,
                        expression=node,
                        value_type=value_type,
                        value=children[0],
                        use=block_use.ref,
                    )
                for edge in capture_edges:
                    if edge.checkpoint.read is not block_use.edge:
                        continue
                    found = capture_stage_ports(edge, stage_context.ports)
                    if found is None:
                        raise ValueError("Capture read lacks its outer row ports.")
                    captures.append(
                        ProjectSQLCapture(
                            ref=capture_refs[id(edge)],
                            inner=definitions_by_owner[id(edge.capture.inner)].ref,
                            outer=definitions_by_owner[id(edge.capture.outer)].ref,
                            read=node_ref,
                            block=site.block,
                            ports=tuple(port.ref for port in found),
                            edge=edge,
                        )
                    )
            elif isinstance(node, CapturedFieldExpr):
                captured = captured_by_expression.get(id(node))
                if (
                    captured is None
                    or captured.capture.capture.inner is not site.owner
                    or captured.capture.capture.ordinal != node.ordinal
                ):
                    raise ValueError("Captured field read lacks its capture edge.")
                value = row.ProjectSQLCapturedField(
                    ref=node_ref,
                    site=site,
                    expression=node,
                    value_type=value_type,
                    capture=capture_refs[id(captured.capture)],
                    position=captured.position,
                )
            elif isinstance(node, CastExpr):
                value = row.ProjectSQLCast(
                    ref=node_ref,
                    site=site,
                    expression=node,
                    value_type=value_type,
                    value=children[0],
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
        images = joining.join_images(entry)
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
            # A right input that executes a capturing let completes its capture
            # records with this JOIN's left input ports (LATERAL).
            for edge in capture_edges:
                if edge.checkpoint.read is not image.inputs[1]:
                    continue
                found = lateral_capture_ports(
                    edge, tuple(join_ports_by_ref[p] for p in input_values[0].ports)
                )
                if found is None:
                    raise ValueError("LATERAL capture lacks its left input ports.")
                captures.append(
                    ProjectSQLCapture(
                        ref=capture_refs[id(edge)],
                        inner=definitions_by_owner[id(edge.capture.inner)].ref,
                        outer=definitions_by_owner[id(edge.capture.outer)].ref,
                        read=input_values[1].ref,
                        block=join_ref,
                        ports=found,
                        edge=edge,
                    )
                )
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
                # No authored JOIN matches by relationship equalities.
                equalities=(),
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
        if isinstance(
            authored,
            (SourceDef, SetRelationDef, ValuesRelationDef, TableFunctionRelationDef),
        ):
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
                aggregate_site_ordinal = 0
                for index, (source, references) in enumerate(
                    zip(
                        aggregate.aggregates, aggregate.argument_references, strict=True
                    )
                ):
                    call = source.item.expression
                    assert isinstance(call, CallExpr)
                    arguments = []
                    order_by = []
                    authored_children = (
                        *(call.arguments),
                        *(item.expression for item in call.aggregate_order_by),
                    )
                    reference_position = 0
                    for child_position, child in enumerate(authored_children):
                        evidence = aggregation.argument_evidence(source)
                        assert evidence is not None
                        normalized_child = _normalized_scalar_expression(
                            child, evidence
                        )
                        leaves = tuple(
                            node
                            for node in row.scalar_nodes(normalized_child)
                            if isinstance(node, (NameExpr, DottedNameExpr))
                        )
                        child_references = references[
                            reference_position : reference_position + len(leaves)
                        ]
                        if len(child_references) != len(leaves) or any(
                            row.reference_expression(reference) is not leaf
                            for reference, leaf in zip(
                                child_references, leaves, strict=True
                            )
                        ):
                            raise ValueError("Aggregate child references drift.")
                        reference_position += len(leaves)
                        current_site = aggregation.ProjectSQLAggregateSite(
                            ref=ref(K.EXPRESSION_SITE),
                            owner=entry.owner,
                            block=block_ref,
                            role=row.ProjectSQLExpressionRole.AGGREGATE_ARGUMENT,
                            ordinal=aggregate_site_ordinal,
                            occurrence=source.item,
                            expression=normalized_child,
                            aggregation=aggregate_ref,
                            authority=aggregate,
                            evidence=evidence,
                            references=child_references,
                        )
                        sites.append(current_site)
                        aggregate_site_ordinal += 1
                        child_ref = expression(
                            current_site, local_ports, local_symbols, stage_context
                        )
                        if child_position < len(call.arguments):
                            arguments.append(child_ref)
                        else:
                            order_by.append(child_ref)
                    if reference_position != len(references):
                        raise ValueError("Aggregate references have no authored child.")
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
                        arguments=tuple(arguments),
                        order_by=tuple(order_by),
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
                        parameter = None
                        if isinstance(argument, ParameterRefExpr):
                            if not 0 <= argument.ordinal < len(query_parameters) or (
                                query_parameters[argument.ordinal].declaration.name
                                != argument.name
                            ):
                                raise ValueError(
                                    "Parameter read is outside its entry query."
                                )
                            parameter = query_parameters[argument.ordinal]
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
                            parameter=parameter,
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
            (value.use,)
            if isinstance(value, row.ProjectSQLAnyReference) and value.use is not None
            else (value.port,)
            if isinstance(value, row.ProjectSQLAnyReference) and value.port is not None
            else (value.port,)
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
            else (value.use,)
            if isinstance(
                value,
                (
                    row.ProjectSQLAny,
                    row.ProjectSQLRelationExists,
                    row.ProjectSQLRelationScalar,
                    row.ProjectSQLRelationMembership,
                ),
            )
            else (value.capture,)
            if isinstance(value, row.ProjectSQLCapturedField)
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
    if len(captures) != len(capture_edges):
        raise ValueError("Every imaged capture needs its single outer read.")
    for capture in sorted(captures, key=lambda item: item.ref.position):
        origin(
            capture.ref,
            R.CAPTURE,
            P.GENERATED_STRUCTURE,
            capture.use.inner,
            capture.use.clause,
            capture.use,
            (capture.read, *capture.ports),
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
                (witness.aggregation, *witness.arguments, *witness.order_by),
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
        parameters=query_parameters,
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
        expression_block_uses=bindings.expression_block_uses,
        captures=tuple(sorted(captures, key=lambda item: item.ref.position)),
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
        relationship_matches=(),
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
    result_collections = results.build(plan, ref)
    for name, value in result_collections.items():
        object.__setattr__(plan, name, value)
    result_context = results.origin_context(plan)
    owners_by_definition = {d.ref: d.entry.owner for d in bindings.definitions}
    for name, witnesses in result_collections.items():
        if name.startswith(("set_", "values_")):
            continue
        for witness in witnesses:
            definition_ref, cause, antecedents, demand_kind, provenance = (
                results.origin_parts(witness, result_context)
            )
            owner = owners_by_definition[definition_ref]
            role = R(witness.ref.kind.value)
            original = origin(
                witness.ref, role, provenance, owner, cause, witness, antecedents
            )
            demand_ref = ref(K.DEMAND)
            demand_origin = origin(
                demand_ref, R.DEMAND, provenance, owner, cause, witness, (original,)
            )
            demands.append(
                results.ProjectSQLResultDemand(
                    ref=demand_ref,
                    subject=witness.ref,
                    kind=demand_kind,
                    witness=witness,
                    origin=demand_origin,
                )
            )
    set_context = sets.origin_context(plan)
    for witness in (
        *plan.set_bodies,
        *plan.set_operands,
        *plan.set_inputs,
        *plan.set_columns,
    ):
        definition_ref, cause, antecedents, provenance, kinds = sets.origin_parts(
            witness, set_context
        )
        owner = owners_by_definition[definition_ref]
        original = origin(
            witness.ref,
            R(witness.ref.kind.value),
            provenance,
            owner,
            cause,
            witness,
            antecedents,
        )
        for kind in kinds:
            demand_ref = ref(K.DEMAND)
            demand_origin = origin(
                demand_ref, R.DEMAND, P.TYPE_PROOF, owner, cause, witness, (original,)
            )
            demands.append(
                sets.ProjectSQLSetDemand(
                    ref=demand_ref,
                    subject=witness.ref,
                    kind=kind,
                    witness=witness,
                    origin=demand_origin,
                )
            )
    values_context = {body.ref: body for body in plan.values_bodies}
    for witness in (*plan.values_bodies, *plan.values_columns):
        definition_ref, cause, antecedents, provenance, kinds = valuesplan.origin_parts(
            witness, values_context
        )
        owner = owners_by_definition[definition_ref]
        original = origin(
            witness.ref,
            R(witness.ref.kind.value),
            provenance,
            owner,
            cause,
            witness,
            antecedents,
        )
        for kind in kinds:
            demand_ref = ref(K.DEMAND)
            demand_origin = origin(
                demand_ref, R.DEMAND, P.TYPE_PROOF, owner, cause, witness, (original,)
            )
            demands.append(
                valuesplan.ProjectSQLValuesDemand(
                    ref=demand_ref,
                    subject=witness.ref,
                    kind=kind,
                    witness=witness,
                    origin=demand_origin,
                )
            )
    object.__setattr__(plan, "origins", tuple(origins))
    object.__setattr__(plan, "demands", tuple(demands))
    for name, collection in literals.build(plan, literal_policy, ref).items():
        object.__setattr__(plan, name, collection)
    for witness in (
        *plan.literal_sites,
        *plan.literal_slots,
        *plan.fixed_envelope.values,
        *plan.bind_uses,
    ):
        literal_site, antecedents, provenance = literals.origin_parts(witness)
        origin(
            witness.ref,
            R(witness.ref.kind.value),
            provenance,
            literal_site.position.owner,
            literal_site.position.literal,
            witness,
            antecedents,
        )
    contexts = literals.context_index(plan)
    for use, value in zip(plan.bind_uses, plan.fixed_envelope.values, strict=True):
        demand_ref = ref(K.DEMAND)
        literal_site = use.slot.site
        demand_origin = origin(
            demand_ref,
            R.DEMAND,
            P.TYPE_PROOF,
            literal_site.position.owner,
            literal_site.position.literal,
            use,
            (
                origin_by_subject[use.ref],
                origin_by_subject[use.slot.ref],
                origin_by_subject[value.ref],
            ),
        )
        demands.append(
            literals.ProjectSQLLiteralDemand(
                ref=demand_ref,
                subject=use.ref,
                use=use,
                value=value,
                contexts=literals.demand_contexts(literal_site, contexts),
                requirements=tuple(literals.ProjectSQLLiteralRequirement),
                origin=demand_origin,
            )
        )
    object.__setattr__(plan, "origins", tuple(origins))
    object.__setattr__(plan, "demands", tuple(demands))
    return plan


@dataclass(frozen=True, slots=True, eq=False)
class CompiledPortIdentity:
    name: str


@dataclass(frozen=True, slots=True, eq=False)
class CompiledSQLPort:
    ref: CompiledIRReference
    owner: object
    field: CompiledIRField = field(repr=False)
    identity: CompiledPortIdentity

    producer_port: CompiledIRReference | None = None

    @property
    def nulling(self):
        return self.field.fact.nulling


@dataclass(frozen=True, slots=True, eq=False)
class CompiledSQLDefinition:
    ref: CompiledIRReference
    entry: CompiledIROperator = field(repr=False)
    exports: tuple[CompiledSQLPort, ...]


@dataclass(frozen=True, slots=True, eq=False)
class CompiledSQLSource:
    ref: CompiledIRReference
    source: CompiledIROperator = field(repr=False)


@dataclass(frozen=True, slots=True, eq=False)
class CompiledLiteralPosition:
    owner: object = field(repr=False)
    role: literals.ProjectSQLLiteralRole
    literal: row.CompiledExpressionPrimitive = field(repr=False)
    expression: object
    ancestry: tuple


@dataclass(frozen=True, slots=True, eq=False)
class CompiledLiteralSite:
    ref: CompiledIRReference
    position: CompiledLiteralPosition
    disposition: literals.ProjectSQLLiteralDisposition
    reason: literals.ProjectSQLLiteralReason | None


@dataclass(frozen=True, slots=True, eq=False)
class CompiledLiteralSlot:
    ref: CompiledIRReference
    site: CompiledLiteralSite
    tag: literals.ProjectSQLLiteralTag


@dataclass(frozen=True, slots=True, eq=False)
class CompiledBindUse:
    slot: CompiledLiteralSlot
    expression: object


@dataclass(frozen=True, slots=True, eq=False)
class CompiledFixedValue:
    slot: CompiledLiteralSlot
    tag: literals.ProjectSQLLiteralTag
    value: object = field(repr=False)


@dataclass(frozen=True, slots=True, eq=False)
class CompiledFixedEnvelope:
    values: tuple[CompiledFixedValue, ...] = field(repr=False)


@dataclass(frozen=True, slots=True, eq=False)
class CompiledExpressionSyntax:
    """Closed source-free expression spelling needed by SQL rendering."""

    operator: str | None
    negated: bool = False


@dataclass(frozen=True, slots=True, eq=False)
class CompiledExpressionIdentity:
    """Reconstructed canonical identity for one compiled expression occurrence."""

    ref: CompiledIRReference
    value_type: ValueType
    expression: CompiledExpressionSyntax
    callee_symbol: SymbolId | None = None


@dataclass(frozen=True, slots=True, eq=False)
class CompiledSQLSingleMatch:
    ref: CompiledIRReference
    request: CompiledSingleMatchRequest = field(repr=False)
    assessment: CompiledSingleMatchAssessment = field(repr=False)
    joins: tuple[CompiledIRReference, ...]
    input_pairs: tuple[tuple[CompiledIRReference, ...], ...]
    proofs: tuple[CompiledIRReference, ...]
    downstream_enforcement_required: bool


@dataclass(frozen=True, slots=True, eq=False)
class CompiledSQLSingleMatchProof:
    ref: CompiledIRReference
    obligation: CompiledIRReference
    parent: CompiledIRReference | None
    source: CompiledSingleMatchProof = field(repr=False)
    joins: tuple[CompiledIRReference, ...]
    children: tuple[CompiledIRReference, ...]


@dataclass(frozen=True, slots=True, eq=False)
class CompiledSQLAggregateRisk:
    ref: CompiledIRReference
    aggregation: CompiledIRReference
    source: object = field(repr=False)


@dataclass(frozen=True, slots=True, eq=False)
class CompiledSQLPlan:
    ir: CompiledQueryBlockIR = field(repr=False)
    scope: object = field(repr=False)
    references: Mapping[Address, CompiledIRReference] = field(repr=False)
    definitions: tuple[CompiledSQLDefinition, ...]
    sources: tuple[CompiledSQLSource, ...]
    ports: Mapping[Address, CompiledSQLPort] = field(repr=False)
    exports: tuple[CompiledSQLPort, ...]
    expressions: Mapping[Address, row.CompiledPlanValue] = field(repr=False)
    expression_identities: Mapping[Address, CompiledExpressionIdentity] = field(
        repr=False
    )
    literal_policy: literals.ProjectSQLLiteralPolicy
    literal_sites: tuple[CompiledLiteralSite, ...]
    literal_slots: tuple[CompiledLiteralSlot, ...]
    fixed_envelope: CompiledFixedEnvelope = field(repr=False)
    parameter_uses: tuple = field(repr=False)
    single_matches: tuple[CompiledSQLSingleMatch, ...] = ()
    single_match_proofs: tuple[CompiledSQLSingleMatchProof, ...] = ()
    all_single_matches: tuple[CompiledSQLSingleMatch, ...] = ()
    all_single_match_proofs: tuple[CompiledSQLSingleMatchProof, ...] = ()
    aggregate_evidence: tuple = ()
    aggregate_risks: tuple = ()
    window_policies: tuple = ()
    semantic_references: Mapping = field(default_factory=dict, repr=False)
    parameters: tuple = ()


def build_compiled_sql_plan(ir):
    """Plan the resolved branch; no source-only planning roots are manufactured."""
    from types import MappingProxyType
    from pietto._project.project_compiled_schema import Address, CompiledError
    from pietto._project.project_query_block_ir_verification import (
        verify_compiled_query_block_ir,
    )
    from pietto._project.project_sql_emission_parameters import allocate_uses, PHYSICAL

    verify_compiled_query_block_ir(ir)
    completed, refs = ir.completed, ir.references
    records = completed.root.records
    from pietto._project.project_compiled_schema import selected_relations

    active = selected_relations(records, records[completed.root.description.query])
    facts = {f.address: f for f in completed.facts}
    declarations = {d.address: d for d in completed.declarations}
    ports = {}
    for operator in ir.operators:
        for f in operator.fields:
            address = Address(f.ref.kind, f.ref.position)
            ports[address] = CompiledSQLPort(
                f.ref, operator.ref, f, CompiledPortIdentity(f.evidence.name)
            )
    definitions = tuple(
        CompiledSQLDefinition(
            o.ref,
            o,
            tuple(ports[Address(f.ref.kind, f.ref.position)] for f in o.fields),
        )
        for o in ir.operators
    )
    source_bindings = tuple(
        CompiledSQLSource(o.ref, o)
        for o in ir.operators
        if o.kind == "source" and o.record.address in active
    )
    primitives = {}
    for address, fact in facts.items():
        if address.kind in ("literal", "operation", "read"):
            primitives[address] = row.CompiledExpressionPrimitive(
                fact.value,
                None if fact.operator is None else fact.operator[1],
                fact.operator == ("null_test", "is_not_null"),
            )
    for address in records:
        if address.kind in ("null_literal", "parameter_read"):
            primitives[address] = row.CompiledExpressionPrimitive(None, None, False)
    query_parameters = {
        r.address: row.CompiledQueryParameter(
            r.get("ordinal"), r.get("label"), r.get("tag"), r.get("nullable")
        )
        for r in records.values()
        if r.address.kind == "parameter"
    }
    identities = {}
    for address, fact in facts.items():
        if address.kind != "operation" or fact.operator is None:
            continue
        role, token = fact.operator
        if type(role) is not str or type(token) is not str:
            raise CompiledError("COMPILED_PLAN_OPERATOR")
        identities[address] = CompiledExpressionIdentity(
            refs[address],
            fact.value_type,
            CompiledExpressionSyntax(
                token,
                (role, token)
                in {("membership", "not_in"), ("null_test", "is_not_null")},
            ),
            (
                SymbolId(SymbolNamespace.CALLABLE, token)
                if role == "scalar_call"
                else None
            ),
        )
    sites = {}
    for record in records.values():
        if record.address.kind != "site":
            continue
        literals_here = tuple(
            r
            for r in records.values()
            if r.address.kind in ("literal", "null_literal")
            and r.get("site") == record.address
        )
        if len(literals_here) != 1:
            raise CompiledError("COMPILED_PLAN_SITE")
        literal = literals_here[0]
        sites[record.address] = CompiledLiteralSite(
            refs[record.address],
            CompiledLiteralPosition(
                declarations[record.get("owner")],
                literals.ProjectSQLLiteralRole(record.get("role")),
                primitives[literal.address],
                refs[literal.address],
                record.get("ancestry"),
            ),
            literals.ProjectSQLLiteralDisposition(record.get("disposition")),
            None
            if record.get("reason") is None
            else literals.ProjectSQLLiteralReason(record.get("reason")),
        )
    slots, literal_slots = {}, {}
    for record in records.values():
        if record.address.kind == "slot":
            slot = CompiledLiteralSlot(
                refs[record.address],
                sites[record.get("site")],
                literals.ProjectSQLLiteralTag(record.get("tag")),
            )
            slots[record.address] = slot
            literal_slots[record.get("literal")] = slot
    expressions = {}
    for address, primitive in primitives.items():
        fact = facts[address]
        arguments = (
            refs[address],
            fact.value_type,
            primitive,
            tuple(refs[a] for a in fact.operands),
        )
        if address in literal_slots:
            expressions[address] = row.CompiledBoundLiteral(
                *arguments, CompiledBindUse(literal_slots[address], refs[address])
            )
        elif address.kind == "parameter_read":
            expressions[address] = row.CompiledParameterRead(
                *arguments, query_parameters[records[address].get("parameter")]
            )
        elif address.kind in ("literal", "null_literal"):
            expressions[address] = row.CompiledLiteral(*arguments)
        else:
            expressions[address] = row.CompiledPlanValue(*arguments)
    family = records[Address("target", 0)].get("family")
    occurrences = []
    native_records = tuple(
        r for r in records.values() if r.address.kind == "native_use"
    )
    for record in native_records:
        owner = records[record.get("slot")]
        if owner.address.kind == "parameter_read":
            read = expressions[owner.address]
            occurrences.append((read, PHYSICAL[family][read.parameter.tag]))
            continue
        expression = expressions[owner.get("literal")]
        occurrences.append((expression, PHYSICAL[family][owner.get("tag")]))
    native = allocate_uses(family, tuple(occurrences), len(occurrences))
    for actual, described in zip(native, native_records, strict=True):
        if (actual.ordinal, actual.server_index, actual.physical_type) != (
            described.get("ordinal"),
            described.get("index"),
            described.get("physical"),
        ):
            raise CompiledError("COMPILED_PLAN_USES")
    envelope = CompiledFixedEnvelope(
        tuple(
            CompiledFixedValue(slot, slot.tag, slot.site.position.literal.value)
            for slot in slots.values()
        )
    )
    from pietto._project.project_single_match import assess_compiled_requests
    from pietto._project.project_query_block_ir import CompiledIRReference

    obligations, proof_images = [], []
    for position, assessment in enumerate(assess_compiled_requests(ir)):
        obligation_ref = CompiledIRReference(ir.scope, "single_match", position)
        proof_nodes = []
        pending: list[
            tuple[tuple[int, ...], tuple[int, ...] | None, CompiledSingleMatchProof]
        ] = [
            ((i,), None, proof)
            for i, proof in reversed(tuple(enumerate(assessment.proofs)))
        ]
        while pending:
            path, parent, proof = pending.pop()
            proof_nodes.append((path, parent, proof))
            pending.extend(
                ((*path, i), path, child)
                for i, child in reversed(tuple(enumerate(proof.children)))
            )
        proof_refs = {
            path: CompiledIRReference(
                ir.scope, "single_match_proof", len(proof_images) + i
            )
            for i, (path, _, _) in enumerate(proof_nodes)
        }
        for path, parent, proof in proof_nodes:
            proof_images.append(
                CompiledSQLSingleMatchProof(
                    proof_refs[path],
                    obligation_ref,
                    None if parent is None else proof_refs[parent],
                    proof,
                    tuple(refs[a] for a in proof.boundaries),
                    tuple(proof_refs[(*path, i)] for i in range(len(proof.children))),
                )
            )
        obligations.append(
            CompiledSQLSingleMatch(
                obligation_ref,
                assessment.request,
                assessment,
                tuple(refs[a] for a in assessment.joins),
                tuple(tuple(refs[a] for a in pair) for pair in assessment.input_pairs),
                tuple(proof_refs[(i,)] for i in range(len(assessment.proofs))),
                assessment.downstream_enforcement_required,
            )
        )
    from pietto._project.project_joined_aggregation import (
        build_compiled_aggregate_evidence,
    )

    aggregate_evidence = build_compiled_aggregate_evidence(ir)
    aggregate_risks = []
    for evidence in aggregate_evidence:
        for risk in evidence.risks:
            aggregate_risks.append(
                CompiledSQLAggregateRisk(
                    CompiledIRReference(
                        ir.scope, "aggregate_risk", len(aggregate_risks)
                    ),
                    evidence.stage.ref,
                    risk,
                )
            )
    from pietto._project.project_sql_plan_requirements import (
        compiled_semantic_references,
    )

    entry = records[completed.root.description.query]
    return CompiledSQLPlan(
        ir,
        ir.scope,
        refs,
        definitions,
        source_bindings,
        MappingProxyType(ports),
        tuple(ports[p] for p in entry.get("exports")),
        MappingProxyType(expressions),
        MappingProxyType(identities),
        literals.ProjectSQLLiteralPolicy(
            records[Address("policy", 0)].get("literal_policy")
        ),
        tuple(sites.values()),
        tuple(slots.values()),
        envelope,
        native,
        single_matches=tuple(
            o
            for o in obligations
            if any(Address(j.kind, j.position) in active for j in o.joins)
        ),
        single_match_proofs=tuple(
            p
            for p in proof_images
            if any(Address(j.kind, j.position) in active for j in p.joins)
        ),
        all_single_matches=tuple(obligations),
        all_single_match_proofs=tuple(proof_images),
        aggregate_evidence=aggregate_evidence,
        aggregate_risks=tuple(aggregate_risks),
        window_policies=windows.compiled_window_policies(ir, primitives),
        semantic_references=compiled_semantic_references(ir.scope, records),
        parameters=tuple(query_parameters.values()),
    )
