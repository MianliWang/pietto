"""Lossless, optional demand reports over an exact current SQL plan request."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Never

from pietto._project import project_sql_plan as sql
from pietto._project import project_sql_plan_expressions as row
from pietto._project import project_sql_plan_joins as joins
from pietto._project import project_sql_plan_aggregation as aggregation
from pietto._project import project_sql_plan_windows as windows
from pietto._project import project_sql_plan_results as results
from pietto._project import project_sql_plan_sets as sets
from pietto._project import project_sql_plan_literals as literals
from pietto._project.project_sql_plan_verification import (
    ProjectSQLPlanVerification,
    verify_project_sql_plan,
)
from pietto._project.project_single_match import ProjectSingleMatchState
from pietto._project.module_catalog import ProjectDeclarationOccurrence
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
)
from pietto._project.project_query_block_ir_verification import (
    ProjectIRQueryBlockAnalysisBundle,
)
from pietto.errors import Diagnostic

__all__: tuple[str, ...] = ()


class ProjectSQLDemandFamily(StrEnum):
    SOURCE = "source_realization"
    EXPORT = "export_representation"
    EXPRESSION = "expression"
    STAGE_VALUE = "stage_value"
    FILTER = "filter"
    SCOPE = "scope"
    JOIN = "join"
    AGGREGATE = "aggregation"
    WINDOW = "window"
    RESULT = "result"
    SET = "set"
    LITERAL = "fixed_literal_transport"


F = ProjectSQLDemandFamily
DEMAND_FAMILIES = MappingProxyType(
    {
        sql.ProjectSQLSourceRealizationDemand: F.SOURCE,
        sql.ProjectSQLExportRepresentationDemand: F.EXPORT,
        row.ProjectSQLExpressionDemand: F.EXPRESSION,
        row.ProjectSQLStageValueDemand: F.STAGE_VALUE,
        row.ProjectSQLFilterDemand: F.FILTER,
        row.ProjectSQLScopeDemand: F.SCOPE,
        joins.ProjectSQLJoinDemand: F.JOIN,
        aggregation.ProjectSQLAggregateDemand: F.AGGREGATE,
        windows.ProjectSQLWindowDemand: F.WINDOW,
        results.ProjectSQLResultDemand: F.RESULT,
        sets.ProjectSQLSetDemand: F.SET,
        literals.ProjectSQLLiteralDemand: F.LITERAL,
    }
)

type ProjectSQLDemandSubkind = (
    row.ProjectSQLExpressionRole
    | row.ProjectSQLStageKind
    | row.ProjectSQLStagePortKind
    | joins.ProjectSQLJoinDemandKind
    | aggregation.ProjectSQLAggregateDemandKind
    | windows.ProjectSQLWindowDemandKind
    | results.ProjectSQLResultDemandKind
    | sets.ProjectSQLSetDemandKind
    | literals.ProjectSQLLiteralTag
    | None
)

# An added producer variant/member requires a report rule, not a catch-all bucket.
SUBKINDS: Mapping[ProjectSQLDemandFamily, tuple[ProjectSQLDemandSubkind, ...]] = (
    MappingProxyType(
        {
            F.SOURCE: (None,),
            F.EXPORT: (None,),
            F.EXPRESSION: (
                row.ProjectSQLExpressionRole.MATCH,
                row.ProjectSQLExpressionRole.LET,
                row.ProjectSQLExpressionRole.WHERE,
                row.ProjectSQLExpressionRole.SELECT,
                row.ProjectSQLExpressionRole.AGGREGATE_ARGUMENT,
                row.ProjectSQLExpressionRole.SATISFYING,
                row.ProjectSQLExpressionRole.QUALIFY,
            ),
            F.STAGE_VALUE: (
                row.ProjectSQLStagePortKind.INPUT,
                row.ProjectSQLStagePortKind.EXPORT,
            ),
            F.FILTER: (
                row.ProjectSQLExpressionRole.WHERE,
                row.ProjectSQLExpressionRole.SATISFYING,
                row.ProjectSQLExpressionRole.QUALIFY,
            ),
            F.SCOPE: (
                row.ProjectSQLStageKind.LET,
                row.ProjectSQLStageKind.WHERE,
                row.ProjectSQLStageKind.PROJECTION,
                row.ProjectSQLStageKind.AGGREGATE,
                row.ProjectSQLStageKind.SATISFYING,
                row.ProjectSQLStageKind.WINDOW,
                row.ProjectSQLStageKind.QUALIFY,
            ),
            F.JOIN: (
                joins.ProjectSQLJoinDemandKind.JOIN_ROWS,
                joins.ProjectSQLJoinDemandKind.MATCH_INPUT,
                joins.ProjectSQLJoinDemandKind.MATCH_FIELD,
                joins.ProjectSQLJoinDemandKind.OUTPUT_FIELD,
                joins.ProjectSQLJoinDemandKind.RELATIONSHIP_EQUALITY,
                joins.ProjectSQLJoinDemandKind.POST_MATCH_SCOPE,
                joins.ProjectSQLJoinDemandKind.SINGLE_MATCH,
                joins.ProjectSQLJoinDemandKind.PROOF_CONTEXT,
            ),
            F.AGGREGATE: (
                aggregation.ProjectSQLAggregateDemandKind.GROUPING_AND_EMPTY_INPUT,
                aggregation.ProjectSQLAggregateDemandKind.GROUP_COMPARISON,
                aggregation.ProjectSQLAggregateDemandKind.AGGREGATE_OPERATION,
                aggregation.ProjectSQLAggregateDemandKind.RESULT_PROJECTION,
                aggregation.ProjectSQLAggregateDemandKind.RETAINED_RISK,
            ),
            F.WINDOW: (
                windows.ProjectSQLWindowDemandKind.INPUT_BAG_AND_RESULT,
                windows.ProjectSQLWindowDemandKind.INPUT_USE,
                windows.ProjectSQLWindowDemandKind.ARGUMENT,
                windows.ProjectSQLWindowDemandKind.POLICY,
                windows.ProjectSQLWindowDemandKind.PROJECTION,
            ),
            F.RESULT: (
                results.ProjectSQLResultDemandKind.BOUNDARY,
                results.ProjectSQLResultDemandKind.PORT,
                results.ProjectSQLResultDemandKind.DISTINCT,
                results.ProjectSQLResultDemandKind.COMPARISON,
                results.ProjectSQLResultDemandKind.ORDER,
                results.ProjectSQLResultDemandKind.ORDER_ITEM,
                results.ProjectSQLResultDemandKind.EXPRESSION,
                results.ProjectSQLResultDemandKind.USE,
                results.ProjectSQLResultDemandKind.HIDDEN,
                results.ProjectSQLResultDemandKind.LIMIT,
                results.ProjectSQLResultDemandKind.EXPORT,
            ),
            F.SET: (
                sets.ProjectSQLSetDemandKind.OPERATION,
                sets.ProjectSQLSetDemandKind.PROPERTIES,
                sets.ProjectSQLSetDemandKind.COMPARISON,
                sets.ProjectSQLSetDemandKind.OPERAND,
                sets.ProjectSQLSetDemandKind.INPUT,
                sets.ProjectSQLSetDemandKind.COLUMN,
            ),
            F.LITERAL: (
                literals.ProjectSQLLiteralTag.BOOL,
                literals.ProjectSQLLiteralTag.INT,
                literals.ProjectSQLLiteralTag.TEXT,
                literals.ProjectSQLLiteralTag.FLOAT,
            ),
        }
    )
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLDemandScope:
    definition: sql.ProjectSQLPlanRef
    stages: tuple[sql.ProjectSQLPlanRef, ...]
    # Enclosing input context, not value lineage or a transitive demand copy.
    input_uses: tuple[sql.ProjectSQLPlanRef, ...]


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLDemandEntry:
    position: int
    ref: sql.ProjectSQLPlanRef
    demand: sql.ProjectSQLDemand
    family: ProjectSQLDemandFamily
    subkind: ProjectSQLDemandSubkind
    subject: sql.ProjectSQLPlanRef
    scope: ProjectSQLDemandScope
    origin: sql.ProjectSQLOrigin

    @property
    def origin_owner(self) -> ProjectDeclarationOccurrence:
        return self.origin.owner

    @property
    def literal_requirements(self) -> tuple[literals.ProjectSQLLiteralRequirement, ...]:
        return (
            self.demand.requirements
            if type(self.demand) is literals.ProjectSQLLiteralDemand
            else ()
        )


class ProjectSQLDemandLinkKind(StrEnum):
    LITERAL_CONTEXT = "literal_ancestor_context"
    PROOF_ROOT = "single_match_root_proof"
    PROOF_CHILD = "single_match_child_proof"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLDemandLink:
    position: int
    kind: ProjectSQLDemandLinkKind
    source: ProjectSQLDemandEntry
    target: ProjectSQLDemandEntry


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLSingleMatchReport:
    original: joins.ProjectSQLSingleMatch
    entry: ProjectSQLDemandEntry
    proof_entries: tuple[ProjectSQLDemandEntry, ...]
    state: ProjectSingleMatchState
    enforcement_required: bool
    diagnostic: Diagnostic | None


class ProjectSQLRealizationPosture(StrEnum):
    PENDING = "pending_lowering_realization"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLHiddenOrderReport:
    original: results.ProjectSQLHiddenOrderRequirement
    entry: ProjectSQLDemandEntry
    posture: ProjectSQLRealizationPosture


class ProjectSQLAggregateEvidenceKind(StrEnum):
    GROUP_PROTECTION = "group_protection"
    GRAIN_LINKAGE = "grain_linkage"
    PAIR_LINKAGE = "pair_linkage"


RISK_KINDS = MappingProxyType(
    {
        aggregation.ProjectJoinedGroupProtection: ProjectSQLAggregateEvidenceKind.GROUP_PROTECTION,
        aggregation.ProjectJoinedAggregateGrainLinkage: ProjectSQLAggregateEvidenceKind.GRAIN_LINKAGE,
        aggregation.ProjectJoinedAggregatePairLinkage: ProjectSQLAggregateEvidenceKind.PAIR_LINKAGE,
    }
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLAggregateEvidenceReport:
    original: aggregation.ProjectSQLAggregateRisk
    entry: ProjectSQLDemandEntry
    kind: ProjectSQLAggregateEvidenceKind
    # No synthesized verdict: determinations/comparisons/structural posture stay
    # in original.source with their exact typed status and premises.


class ProjectSQLReportTargetPosture(StrEnum):
    NOT_ASSESSED = "not_assessed"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLDemandFamilyReport:
    family: ProjectSQLDemandFamily
    entries: tuple[ProjectSQLDemandEntry, ...]


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLRequirementSummary:
    demand_count: int
    families: tuple[ProjectSQLDemandFamilyReport, ...]
    original_proved: tuple[ProjectSQLSingleMatchReport, ...]
    enforcement_required: tuple[ProjectSQLSingleMatchReport, ...]
    pending_realizations: tuple[ProjectSQLHiddenOrderReport, ...]
    aggregate_evidence: tuple[ProjectSQLAggregateEvidenceReport, ...]
    target: ProjectSQLReportTargetPosture


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLRequirementIndexes:
    by_ref: Mapping[sql.ProjectSQLPlanRef, ProjectSQLDemandEntry]
    by_subject: Mapping[sql.ProjectSQLPlanRef, tuple[ProjectSQLDemandEntry, ...]]
    by_definition: Mapping[sql.ProjectSQLPlanRef, tuple[ProjectSQLDemandEntry, ...]]
    by_stage: Mapping[sql.ProjectSQLPlanRef, tuple[ProjectSQLDemandEntry, ...]]
    by_input_use: Mapping[sql.ProjectSQLPlanRef, tuple[ProjectSQLDemandEntry, ...]]
    by_family: Mapping[ProjectSQLDemandFamily, tuple[ProjectSQLDemandEntry, ...]]
    originals: Mapping[int, tuple[object, tuple[ProjectSQLDemandEntry, ...]]]
    outgoing: Mapping[sql.ProjectSQLPlanRef, tuple[ProjectSQLDemandLink, ...]]
    incoming: Mapping[sql.ProjectSQLPlanRef, tuple[ProjectSQLDemandLink, ...]]


@dataclass(frozen=True, slots=True, kw_only=True, eq=False, init=False)
class ProjectSQLRequirementReport:
    source_verification: ProjectSQLPlanVerification
    plan: sql.ProjectSQLPlan
    completed: ProjectConcreteCompletedSemanticResult
    analysis_bundle: ProjectIRQueryBlockAnalysisBundle
    selected_owner: ProjectDeclarationOccurrence
    literal_policy: literals.ProjectSQLLiteralPolicy
    envelope: literals.ProjectSQLFixedEnvelope
    diagnostics: tuple[Diagnostic, ...]
    input_uses: tuple[sql.ProjectSQLInputUse, ...]
    entries: tuple[ProjectSQLDemandEntry, ...]
    links: tuple[ProjectSQLDemandLink, ...]
    single_matches: tuple[ProjectSQLSingleMatchReport, ...]
    hidden_realizations: tuple[ProjectSQLHiddenOrderReport, ...]
    aggregate_evidence: tuple[ProjectSQLAggregateEvidenceReport, ...]
    indexes: ProjectSQLRequirementIndexes
    summary: ProjectSQLRequirementSummary

    def __init__(self) -> Never:
        raise TypeError(
            "Requirement reports are closed; use build_project_sql_requirement_report."
        )


def _require_plan(verification: ProjectSQLPlanVerification) -> sql.ProjectSQLPlan:
    try:
        if (
            type(verification) is not ProjectSQLPlanVerification
            or not verification.verified
            or type(verification.plan) is not sql.ProjectSQLPlan
            or not verify_project_sql_plan(
                verification.plan,
                verification.completed,
                verification.analysis_bundle,
                verification.selected_owner,
                literal_policy=verification.literal_policy,
                envelope=verification.envelope,
            ).verified
            or verification.envelope is not verification.plan.fixed_envelope
            or verification.literal_policy is not verification.plan.literal_policy
        ):
            raise ValueError(
                "Requirement reports require an exact current VERIFIED plan request."
            )
        return verification.plan
    except (AttributeError, KeyError, IndexError, TypeError) as error:
        raise ValueError(
            "Requirement reports require an exact current VERIFIED plan request."
        ) from error


def context_index(plan: sql.ProjectSQLPlan):
    """Pure indexes of existing node membership, not demand classification.

    Stages include actual block/JOIN/result/SET scopes and their retained
    aggregate/window operators. Their query facets deliberately overlap.
    """
    inputs = {d.ref: [] for d in plan.bindings.definitions}
    for use in plan.input_uses:
        inputs[use.consumer].append(use.ref)
    inputs = {ref: tuple(values) for ref, values in inputs.items()}
    owners = {id(d.entry.owner): d.ref for d in plan.bindings.definitions}
    nodes = {}
    contexts = {}
    stages = []

    def put(value, definition, stage_refs=(), input_refs=None):
        nodes[value.ref] = value
        contexts[value.ref] = ProjectSQLDemandScope(
            definition=definition,
            stages=stage_refs,
            input_uses=inputs[definition] if input_refs is None else input_refs,
        )

    def inherit(values, parent):
        for value in values:
            nodes[value.ref] = value
            contexts[value.ref] = contexts[getattr(value, parent)]

    for definition in plan.bindings.definitions:
        put(definition, definition.ref)
    for value in (*plan.source_ports, *plan.all_exports):
        put(value, value.owner)
    for use in plan.input_uses:
        put(use, use.consumer, input_refs=(use.ref,))
        for port in use.ports:
            put(port, use.consumer, input_refs=(use.ref,))
    for stage in (
        *plan.blocks,
        *plan.joins,
        *plan.join_tails,
        *plan.result_boundaries,
        *plan.set_bodies,
    ):
        put(stage, stage.definition, (stage.ref,))
        stages.append(stage.ref)
    for stage in (*plan.aggregations, *plan.windows):
        put(stage, stage.definition, (stage.block, stage.ref))
        stages.append(stage.ref)
    for site in plan.expression_sites:
        context = contexts[site.block]
        extra = (
            (site.aggregation,)
            if isinstance(site, aggregation.ProjectSQLAggregateSite)
            else ()
        )
        put(site, context.definition, (*context.stages, *extra))
    for expression in plan.expressions:
        nodes[expression.ref] = expression
        contexts[expression.ref] = contexts[expression.site.ref]
    inherit(plan.stage_ports, "block")
    for value in (*plan.operands, *plan.let_values, *plan.filters, *plan.projections):
        nodes[value.ref] = value
        contexts[value.ref] = contexts[value.site.ref]
    for value in plan.join_inputs:
        context = contexts[value.join]
        put(
            value,
            context.definition,
            context.stages,
            () if value.binding_use is None else (value.binding_use,),
        )
    inherit(plan.join_ports, "block")
    inherit(plan.relationship_matches, "join")
    for value in plan.single_matches:
        put(value, owners[id(value.request.owner)], value.joins)
    for value in plan.single_match_proofs:
        context = contexts[value.obligation]
        put(value, context.definition, value.joins)
    for values in (plan.group_keys, plan.aggregates, plan.aggregate_risks):
        inherit(values, "aggregation")
    for value in plan.aggregate_projections:
        context = contexts[value.aggregation]
        put(value, context.definition, (value.block, value.aggregation))
    for values in (plan.window_uses, plan.window_arguments, plan.window_policies):
        inherit(values, "window")
    for value in plan.window_projections:
        context = contexts[value.window]
        put(value, context.definition, (value.block, value.window))
    for value in plan.result_ports:
        put(value, value.definition, contexts[value.boundary].stages)
    for values in (plan.distincts, plan.orders, plan.result_limits):
        inherit(values, "boundary")
    inherit(plan.quotient_fields, "distinct")
    inherit(plan.order_items, "ordering")
    for values in (
        plan.order_expressions,
        plan.order_uses,
        plan.hidden_order_requirements,
    ):
        inherit(values, "item")
    for value in plan.result_exports:
        put(value, value.definition, contexts[value.port].stages)
    for value in plan.set_operands:
        context = contexts[value.body]
        put(value, context.definition, context.stages, (value.use.ref,))
    inherit(plan.set_inputs, "operand")
    inherit(plan.set_columns, "body")
    for site in plan.literal_sites:
        context = contexts[site.position.context_ref]
        put(site, context.definition, context.stages, context.input_uses)
    for value in plan.literal_slots:
        nodes[value.ref] = value
        contexts[value.ref] = contexts[value.site.ref]
    for value in (*plan.fixed_envelope.values, *plan.bind_uses):
        nodes[value.ref] = value
        contexts[value.ref] = contexts[value.slot.ref]
    return nodes, contexts, tuple(stages)


def classify(demand, nodes):
    """Builder classifier; layer2 checks the closed taxonomy independently."""
    family = DEMAND_FAMILIES.get(type(demand))
    if family is None:
        raise ValueError("Unhandled SQL demand variant.")
    if family in (F.EXPRESSION, F.FILTER):
        kind = demand.site.role
    elif family in (F.STAGE_VALUE, F.SCOPE):
        kind = nodes[demand.subject].kind
    elif family is F.LITERAL:
        kind = demand.use.slot.tag
    elif family in (F.SOURCE, F.EXPORT):
        kind = None
    else:
        kind = demand.kind
    if not any(kind is admitted for admitted in SUBKINDS[family]):
        raise ValueError("Unhandled SQL demand subkind.")
    return family, kind


def _group(domain, values, keys):
    """Ordered exact membership; a facet contains each flat entry at most once."""
    groups = {key: [] for key in domain}
    for value in values:
        for key in dict.fromkeys(keys(value)):
            groups[key].append(value)
    return MappingProxyType({key: tuple(items) for key, items in groups.items()})


def index_members(plan, entries, links, matches, hidden, risks, contexts, stages):
    """Pure index utility, shared after layer2 validates all supplied records."""
    original_buckets = {}

    def add(original, members):
        bucket = original_buckets.setdefault(id(original), (original, {}))
        for member in members:
            bucket[1].setdefault(member.ref, member)

    for value in matches:
        original = value.original
        members = (value.entry, *value.proof_entries)
        for source in (
            original,
            original.source,
            original.request,
            original.assessment,
        ):
            add(source, members)
        for entry in value.proof_entries:
            proof = entry.demand.witness
            for source in (proof, proof.source, proof.source.source):
                add(source, (entry,))
    for value in hidden:
        for source in (value.original, value.original.source, value.original.proof):
            add(source, (value.entry,))
    for value in risks:
        for source in (value.original, value.original.source):
            add(source, (value.entry,))
    for entry in entries:
        if type(entry.demand) is literals.ProjectSQLLiteralDemand:
            demand = entry.demand
            for source in (
                demand.use,
                demand.use.slot,
                demand.use.slot.site,
                demand.value,
            ):
                add(source, (entry,))
    # Membership order is the authoritative flat order, including overlaps.
    originals = {
        key: (source, tuple(sorted(values.values(), key=lambda e: e.position)))
        for key, (source, values) in original_buckets.items()
    }
    return ProjectSQLRequirementIndexes(
        by_ref=MappingProxyType({e.ref: e for e in entries}),
        by_subject=_group(contexts, entries, lambda e: (e.subject,)),
        by_definition=_group(
            (d.ref for d in plan.bindings.definitions),
            entries,
            lambda e: (e.scope.definition,),
        ),
        by_stage=_group(stages, entries, lambda e: e.scope.stages),
        by_input_use=_group(
            (u.ref for u in plan.input_uses), entries, lambda e: e.scope.input_uses
        ),
        by_family=_group(tuple(F), entries, lambda e: (e.family,)),
        originals=MappingProxyType(originals),
        outgoing=_group(
            (e.ref for e in entries), links, lambda edge: (edge.source.ref,)
        ),
        incoming=_group(
            (e.ref for e in entries), links, lambda edge: (edge.target.ref,)
        ),
    )


def build_summary(entries, matches, hidden, risks, indexes):
    return ProjectSQLRequirementSummary(
        demand_count=len(entries),
        families=tuple(
            ProjectSQLDemandFamilyReport(
                family=family, entries=indexes.by_family[family]
            )
            for family in F
        ),
        original_proved=tuple(
            value for value in matches if value.state is ProjectSingleMatchState.PROVED
        ),
        enforcement_required=tuple(
            value for value in matches if value.enforcement_required
        ),
        pending_realizations=hidden,
        aggregate_evidence=risks,
        target=ProjectSQLReportTargetPosture.NOT_ASSESSED,
    )


def _build_report(
    verification: ProjectSQLPlanVerification,
) -> ProjectSQLRequirementReport:
    plan = _require_plan(verification)
    nodes, contexts, stages = context_index(plan)
    origins = {origin.ref: origin for origin in plan.origins}
    entries = []
    for position, demand in enumerate(plan.demands):
        family, subkind = classify(demand, nodes)
        entries.append(
            ProjectSQLDemandEntry(
                position=position,
                ref=demand.ref,
                demand=demand,
                family=family,
                subkind=subkind,
                subject=demand.subject,
                scope=contexts[demand.subject],
                origin=origins[demand.origin],
            )
        )
    entries = tuple(entries)
    by_ref = {e.ref: e for e in entries}
    by_witness = {e.subject: e for e in entries if e.family is F.JOIN}
    link_items = []

    def link(kind, source, target):
        link_items.append(
            ProjectSQLDemandLink(
                position=len(link_items), kind=kind, source=source, target=target
            )
        )

    proofs = {value.ref: [] for value in plan.single_matches}
    for entry in entries:
        demand = entry.demand
        if type(demand) is literals.ProjectSQLLiteralDemand:
            for context in demand.contexts:
                link(
                    ProjectSQLDemandLinkKind.LITERAL_CONTEXT, entry, by_ref[context.ref]
                )
        elif type(demand) is joins.ProjectSQLJoinDemand:
            if type(demand.witness) is joins.ProjectSQLSingleMatch:
                for ref in demand.witness.proofs:
                    link(ProjectSQLDemandLinkKind.PROOF_ROOT, entry, by_witness[ref])
            elif type(demand.witness) is joins.ProjectSQLSingleMatchProof:
                proofs[demand.witness.obligation].append(entry)
                for ref in demand.witness.children:
                    link(ProjectSQLDemandLinkKind.PROOF_CHILD, entry, by_witness[ref])
    matches = []
    for original in plan.single_matches:
        if type(
            original.assessment.state
        ) is not ProjectSingleMatchState or original.assessment.state not in (
            ProjectSingleMatchState.PROVED,
            ProjectSingleMatchState.LEGAL_UNPROVED,
        ):
            raise ValueError(
                "Requirement reports reject INVALID single-match evidence."
            )
        matches.append(
            ProjectSQLSingleMatchReport(
                original=original,
                entry=by_witness[original.ref],
                proof_entries=tuple(proofs[original.ref]),
                state=original.assessment.state,
                enforcement_required=original.downstream_enforcement_required,
                diagnostic=original.diagnostic,
            )
        )
    hidden_entries = {
        e.subject: e
        for e in entries
        if e.family is F.RESULT
        and e.subkind is results.ProjectSQLResultDemandKind.HIDDEN
    }
    risk_entries = {
        e.subject: e
        for e in entries
        if e.family is F.AGGREGATE
        and e.subkind is aggregation.ProjectSQLAggregateDemandKind.RETAINED_RISK
    }
    hidden = tuple(
        ProjectSQLHiddenOrderReport(
            original=value,
            entry=hidden_entries[value.ref],
            posture=ProjectSQLRealizationPosture.PENDING,
        )
        for value in plan.hidden_order_requirements
    )
    risks = tuple(
        ProjectSQLAggregateEvidenceReport(
            original=value,
            entry=risk_entries[value.ref],
            kind=RISK_KINDS[type(value.source)],
        )
        for value in plan.aggregate_risks
    )
    matches, links = tuple(matches), tuple(link_items)
    indexes = index_members(
        plan, entries, links, matches, hidden, risks, contexts, stages
    )
    report = object.__new__(ProjectSQLRequirementReport)
    for name, value in dict(
        source_verification=verification,
        plan=plan,
        completed=verification.completed,
        analysis_bundle=verification.analysis_bundle,
        selected_owner=verification.selected_owner,
        literal_policy=verification.literal_policy,
        envelope=plan.fixed_envelope,
        diagnostics=plan.diagnostics,
        input_uses=plan.input_uses,
        entries=entries,
        links=links,
        single_matches=matches,
        hidden_realizations=hidden,
        aggregate_evidence=risks,
        indexes=indexes,
        summary=build_summary(entries, matches, hidden, risks, indexes),
    ).items():
        object.__setattr__(report, name, value)
    return report


def build_project_sql_requirement_report(
    verification: ProjectSQLPlanVerification,
) -> ProjectSQLRequirementReport:
    try:
        return _build_report(verification)
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        raise ValueError(
            "Requirement report construction requires complete current plan evidence."
        ) from None


class ProjectSQLRequirementIssue(StrEnum):
    PLAN = "plan_request"
    ROOTS = "report_roots"
    ENTRIES = "demand_entries"
    LINKS = "related_demand_links"
    OBLIGATIONS = "single_match_evidence"
    REALIZATIONS = "hidden_realizations"
    RISKS = "aggregate_evidence"
    INDEXES = "report_indexes"
    SUMMARY = "report_summary"
    STRUCTURE = "report_structure"


def _same(actual, expected):
    return (
        type(actual) is tuple
        and len(actual) == len(expected)
        and all(a is b for a, b in zip(actual, expected, strict=True))
    )


def _same_index(actual, expected, *, single=False, originals=False):
    if type(actual) is not MappingProxyType or len(actual) != len(expected):
        return False
    for (key, value), (wanted, items) in zip(
        actual.items(), expected.items(), strict=True
    ):
        if originals:
            if (
                type(key) is not int
                or key != wanted
                or type(value) is not tuple
                or len(value) != 2
                or value[0] is not items[0]
                or not _same(value[1], items[1])
            ):
                return False
        elif key is not wanted or (
            value is not items if single else not _same(value, items)
        ):
            return False
    return True


def _verify_report(report, verification):
    Issue = ProjectSQLRequirementIssue
    try:
        plan = _require_plan(verification)
    except (AttributeError, KeyError, IndexError, TypeError, ValueError):
        return (Issue.PLAN,)
    if type(report) is not ProjectSQLRequirementReport:
        return (Issue.STRUCTURE,)
    if (
        report.source_verification is not verification
        or report.plan is not plan
        or report.completed is not verification.completed
        or report.analysis_bundle is not verification.analysis_bundle
        or report.selected_owner is not verification.selected_owner
        or report.literal_policy is not verification.literal_policy
        or report.envelope is not verification.envelope
        or report.diagnostics is not plan.diagnostics
        or report.input_uses is not plan.input_uses
    ):
        return (Issue.ROOTS,)
    nodes, contexts, stages = context_index(plan)
    origins = {o.ref: o for o in plan.origins}
    if type(report.entries) is not tuple or len(report.entries) != len(plan.demands):
        return (Issue.ENTRIES,)
    for i, (entry, demand) in enumerate(zip(report.entries, plan.demands, strict=True)):
        family = DEMAND_FAMILIES.get(type(demand))
        if family is None:
            return (Issue.ENTRIES,)
        # Independently read the actual carrier, never the builder classifier.
        if isinstance(
            demand, (row.ProjectSQLExpressionDemand, row.ProjectSQLFilterDemand)
        ):
            kind = demand.site.role
        elif isinstance(
            demand,
            (
                row.ProjectSQLStageValueDemand,
                row.ProjectSQLScopeDemand,
            ),
        ):
            kind = nodes[demand.subject].kind
        elif type(demand) is literals.ProjectSQLLiteralDemand:
            kind = demand.use.slot.tag
        elif isinstance(
            demand,
            (
                sql.ProjectSQLSourceRealizationDemand,
                sql.ProjectSQLExportRepresentationDemand,
            ),
        ):
            kind = None
        elif isinstance(
            demand,
            (
                joins.ProjectSQLJoinDemand,
                aggregation.ProjectSQLAggregateDemand,
                windows.ProjectSQLWindowDemand,
                results.ProjectSQLResultDemand,
                sets.ProjectSQLSetDemand,
            ),
        ):
            kind = demand.kind
        else:
            return (Issue.ENTRIES,)
        scope = contexts[demand.subject]
        if (
            type(entry) is not ProjectSQLDemandEntry
            or type(entry.position) is not int
            or entry.position != i
            or entry.ref is not demand.ref
            or entry.demand is not demand
            or entry.subject is not demand.subject
            or entry.family is not family
            or entry.subkind is not kind
            or not any(kind is value for value in SUBKINDS[family])
            or entry.origin is not origins[demand.origin]
            or type(entry.scope) is not ProjectSQLDemandScope
            or entry.scope.definition is not scope.definition
            or not _same(entry.scope.stages, scope.stages)
            or not _same(entry.scope.input_uses, scope.input_uses)
        ):
            return (Issue.ENTRIES,)
    by_ref = {e.ref: e for e in report.entries}
    join_entries = {
        e.subject: e
        for e in report.entries
        if type(e.demand) is joins.ProjectSQLJoinDemand
    }
    expected_links = []
    proof_entries = {value.ref: [] for value in plan.single_matches}
    for entry in report.entries:
        demand = entry.demand
        if type(demand) is literals.ProjectSQLLiteralDemand:
            expected_links.extend(
                (ProjectSQLDemandLinkKind.LITERAL_CONTEXT, entry, by_ref[d.ref])
                for d in demand.contexts
            )
        elif type(demand) is joins.ProjectSQLJoinDemand:
            witness = demand.witness
            if type(witness) is joins.ProjectSQLSingleMatch:
                expected_links.extend(
                    (ProjectSQLDemandLinkKind.PROOF_ROOT, entry, join_entries[ref])
                    for ref in witness.proofs
                )
            elif type(witness) is joins.ProjectSQLSingleMatchProof:
                proof_entries[witness.obligation].append(entry)
                expected_links.extend(
                    (ProjectSQLDemandLinkKind.PROOF_CHILD, entry, join_entries[ref])
                    for ref in witness.children
                )
    if type(report.links) is not tuple or len(report.links) != len(expected_links):
        return (Issue.LINKS,)
    for i, (link, expected) in enumerate(
        zip(report.links, expected_links, strict=True)
    ):
        if (
            type(link) is not ProjectSQLDemandLink
            or type(link.position) is not int
            or link.position != i
            or link.kind is not expected[0]
            or link.source is not expected[1]
            or link.target is not expected[2]
        ):
            return (Issue.LINKS,)
    if type(report.single_matches) is not tuple or len(report.single_matches) != len(
        plan.single_matches
    ):
        return (Issue.OBLIGATIONS,)
    for record, original in zip(
        report.single_matches, plan.single_matches, strict=True
    ):
        if (
            type(record) is not ProjectSQLSingleMatchReport
            or record.original is not original
            or record.entry is not join_entries[original.ref]
            or not _same(record.proof_entries, proof_entries[original.ref])
            or record.state is not original.assessment.state
            or type(record.state) is not ProjectSingleMatchState
            or record.state
            not in (
                ProjectSingleMatchState.PROVED,
                ProjectSingleMatchState.LEGAL_UNPROVED,
            )
            or record.enforcement_required
            is not original.downstream_enforcement_required
            or record.diagnostic is not original.diagnostic
        ):
            return (Issue.OBLIGATIONS,)
    hidden = {
        e.subject: e
        for e in report.entries
        if e.family is F.RESULT
        and e.subkind is results.ProjectSQLResultDemandKind.HIDDEN
    }
    risks = {
        e.subject: e
        for e in report.entries
        if e.family is F.AGGREGATE
        and e.subkind is aggregation.ProjectSQLAggregateDemandKind.RETAINED_RISK
    }
    if type(report.hidden_realizations) is not tuple or len(
        report.hidden_realizations
    ) != len(plan.hidden_order_requirements):
        return (Issue.REALIZATIONS,)
    for record, original in zip(
        report.hidden_realizations, plan.hidden_order_requirements, strict=True
    ):
        if (
            type(record) is not ProjectSQLHiddenOrderReport
            or record.original is not original
            or record.entry is not hidden[original.ref]
            or record.posture is not ProjectSQLRealizationPosture.PENDING
        ):
            return (Issue.REALIZATIONS,)
    if type(report.aggregate_evidence) is not tuple or len(
        report.aggregate_evidence
    ) != len(plan.aggregate_risks):
        return (Issue.RISKS,)
    for record, original in zip(
        report.aggregate_evidence, plan.aggregate_risks, strict=True
    ):
        kind = RISK_KINDS.get(type(original.source))
        if (
            kind is None
            or type(record) is not ProjectSQLAggregateEvidenceReport
            or record.original is not original
            or record.entry is not risks[original.ref]
            or record.kind is not kind
        ):
            return (Issue.RISKS,)
    expected_indexes = index_members(
        plan,
        report.entries,
        report.links,
        report.single_matches,
        report.hidden_realizations,
        report.aggregate_evidence,
        contexts,
        stages,
    )
    if type(report.indexes) is not ProjectSQLRequirementIndexes:
        return (Issue.INDEXES,)
    for name in ProjectSQLRequirementIndexes.__dataclass_fields__:
        if not _same_index(
            getattr(report.indexes, name),
            getattr(expected_indexes, name),
            single=name == "by_ref",
            originals=name == "originals",
        ):
            return (Issue.INDEXES,)
    summary = report.summary
    if (
        type(summary) is not ProjectSQLRequirementSummary
        or type(summary.demand_count) is not int
        or summary.demand_count != len(plan.demands)
        or type(summary.families) is not tuple
        or len(summary.families) != len(F)
        or not _same(
            summary.original_proved,
            tuple(
                value
                for value in report.single_matches
                if value.state is ProjectSingleMatchState.PROVED
            ),
        )
        or not _same(
            summary.enforcement_required,
            tuple(
                value for value in report.single_matches if value.enforcement_required
            ),
        )
        or not _same(summary.pending_realizations, report.hidden_realizations)
        or not _same(summary.aggregate_evidence, report.aggregate_evidence)
        or summary.target is not ProjectSQLReportTargetPosture.NOT_ASSESSED
    ):
        return (Issue.SUMMARY,)
    for group, family in zip(summary.families, F, strict=True):
        if (
            type(group) is not ProjectSQLDemandFamilyReport
            or group.family is not family
            or not _same(group.entries, expected_indexes.by_family[family])
        ):
            return (Issue.SUMMARY,)
    return ()


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLRequirementVerification:
    report: ProjectSQLRequirementReport
    source_verification: ProjectSQLPlanVerification
    issues: tuple[ProjectSQLRequirementIssue, ...] = field(init=False)

    def __post_init__(self) -> None:
        try:
            issues = _verify_report(self.report, self.source_verification)
        except (AttributeError, KeyError, IndexError, TypeError, ValueError):
            issues = (ProjectSQLRequirementIssue.STRUCTURE,)
        object.__setattr__(self, "issues", issues)

    @property
    def verified(self) -> bool:
        return not self.issues


def verify_project_sql_requirement_report(
    report: ProjectSQLRequirementReport, source_verification: ProjectSQLPlanVerification
) -> ProjectSQLRequirementVerification:
    return ProjectSQLRequirementVerification(
        report=report, source_verification=source_verification
    )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLRequirementInspection:
    verification: ProjectSQLRequirementVerification
    report: ProjectSQLRequirementReport = field(init=False)

    def __post_init__(self) -> None:
        checked = self.verification
        try:
            valid = (
                type(checked) is ProjectSQLRequirementVerification
                and checked.verified
                and verify_project_sql_requirement_report(
                    checked.report, checked.source_verification
                ).verified
            )
        except (AttributeError, IndexError, KeyError, TypeError, ValueError):
            valid = False
        if not valid:
            raise ValueError(
                "Requirement inspection requires an exact current VERIFIED report."
            )
        object.__setattr__(self, "report", checked.report)

    @property
    def entries(self) -> tuple[ProjectSQLDemandEntry, ...]:
        return self.report.entries

    @property
    def summary(self) -> ProjectSQLRequirementSummary:
        return self.report.summary

    @property
    def diagnostics(self) -> tuple[Diagnostic, ...]:
        return self.report.diagnostics

    def entry(self, ref: sql.ProjectSQLPlanRef) -> ProjectSQLDemandEntry:
        if type(ref) is not sql.ProjectSQLPlanRef:
            raise ValueError("Demand reference does not belong to this report.")
        value = self.report.indexes.by_ref.get(ref)
        if value is None:
            raise ValueError("Demand reference does not belong to this report.")
        return value

    def _query(self, index, ref):
        if (
            type(ref) not in (sql.ProjectSQLPlanRef, ProjectSQLDemandFamily)
            or ref not in index
        ):
            raise ValueError("Reference has no owned role in this report query.")
        return index[ref]

    def for_subject(
        self, ref: sql.ProjectSQLPlanRef
    ) -> tuple[ProjectSQLDemandEntry, ...]:
        return self._query(self.report.indexes.by_subject, ref)

    def for_definition(
        self, ref: sql.ProjectSQLPlanRef
    ) -> tuple[ProjectSQLDemandEntry, ...]:
        return self._query(self.report.indexes.by_definition, ref)

    def for_stage(
        self, ref: sql.ProjectSQLPlanRef
    ) -> tuple[ProjectSQLDemandEntry, ...]:
        return self._query(self.report.indexes.by_stage, ref)

    def for_input_use(
        self, ref: sql.ProjectSQLPlanRef
    ) -> tuple[ProjectSQLDemandEntry, ...]:
        return self._query(self.report.indexes.by_input_use, ref)

    def for_family(
        self, family: ProjectSQLDemandFamily
    ) -> tuple[ProjectSQLDemandEntry, ...]:
        if type(family) is not ProjectSQLDemandFamily:
            raise ValueError("Demand family must be an exact report family.")
        return self._query(self.report.indexes.by_family, family)

    def for_requirement(self, original: object) -> tuple[ProjectSQLDemandEntry, ...]:
        value = self.report.indexes.originals.get(id(original))
        if value is None or value[0] is not original:
            raise ValueError("Original requirement does not belong to this report.")
        return value[1]

    def related(self, ref: sql.ProjectSQLPlanRef) -> tuple[ProjectSQLDemandLink, ...]:
        self.entry(ref)
        return self.report.indexes.outgoing[ref]

    def referring(self, ref: sql.ProjectSQLPlanRef) -> tuple[ProjectSQLDemandLink, ...]:
        self.entry(ref)
        return self.report.indexes.incoming[ref]


def inspect_project_sql_requirement_report(
    verification: ProjectSQLRequirementVerification,
) -> ProjectSQLRequirementInspection:
    return ProjectSQLRequirementInspection(verification=verification)
