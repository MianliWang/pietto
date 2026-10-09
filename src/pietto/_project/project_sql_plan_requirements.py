"""Lossless, optional demand reports over an exact current SQL plan request."""

from __future__ import annotations

from pietto._project.project_verification_scope import once

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Never, Any

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

    def portable(self):
        from pietto._project.project_sql_plan_portable import (
            build_project_sql_plan_portable,
        )

        return build_project_sql_plan_portable(
            self.verification.source_verification, report=self.verification
        )

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


@dataclass(frozen=True, slots=True, eq=False)
class CompiledDemandScope:
    definition: object
    stages: tuple
    input_uses: tuple


@dataclass(frozen=True, slots=True, eq=False)
class CompiledDemandOrigin:
    owner: object
    subject: object
    antecedents: tuple
    evidence: object = field(repr=False)
    ref: object
    role: sql.ProjectSQLOriginRole
    provenance: sql.ProjectSQLOriginProvenance
    location: tuple


@dataclass(frozen=True, slots=True, eq=False)
class CompiledDemandEntry:
    position: int
    ref: object
    family: ProjectSQLDemandFamily
    subkind: object
    subject: Any
    scope: CompiledDemandScope
    origin: CompiledDemandOrigin
    role: str


@dataclass(frozen=True, slots=True, eq=False)
class CompiledDemandLink:
    position: int
    kind: ProjectSQLDemandLinkKind
    source: CompiledDemandEntry
    target: CompiledDemandEntry


@dataclass(frozen=True, slots=True, eq=False)
class CompiledRequirementReport:
    verification: object = field(repr=False)
    plan: object = field(repr=False)
    entries: tuple[CompiledDemandEntry, ...]
    links: tuple[CompiledDemandLink, ...]
    by_family: Mapping
    by_subject: Mapping
    by_definition: Mapping
    by_stage: Mapping
    by_input_use: Mapping
    proved: tuple
    enforcement_required: tuple


def _require_compiled_plan(verification):
    from pietto._project.project_sql_plan_verification import (
        CompiledSQLPlanVerification,
        verify_compiled_sql_plan,
    )

    if (
        type(verification) is not CompiledSQLPlanVerification
        or type(verification.plan) is not sql.CompiledSQLPlan
    ):
        raise ValueError("COMPILED_REQUIREMENT_PLAN")
    checked = verify_compiled_sql_plan(verification.plan)
    if (
        checked.completed is not verification.completed
        or checked.selected_owner is not verification.selected_owner
    ):
        raise ValueError("COMPILED_REQUIREMENT_PLAN")
    return verification.plan


@dataclass(frozen=True, slots=True, eq=False)
class CompiledSemanticReference:
    scope: object = field(repr=False)
    kind: str
    position: int


def compiled_semantic_references(scope, records):
    """Resolved reference identities, not source names or source constructors."""
    found = {}

    def retain(pair):
        if pair not in found:
            found[pair] = CompiledSemanticReference(scope, *pair)

    for record in records.values():
        if record.address.kind == "requirement_origin":
            retain(("origin", record.address.position))
            retain(record.get("subject"))
            for pair in record.get("antecedents"):
                retain(pair)
        elif record.address.kind == "requirement":
            retain(("demand", record.address.position))
            retain(record.get("subject"))
            retain(record.get("definition"))
            for pair in (*record.get("stages"), *record.get("uses")):
                retain(pair)
    return MappingProxyType(found)


def compiled_requirement_facts(plan):
    """Read the resolved demand inputs and attach current, freshly derived facts."""

    records, semantic = plan.ir.completed.root.records, plan.semantic_references
    owners = {d.address: d for d in plan.ir.completed.declarations}
    facts = {f.address: f for f in plan.ir.completed.facts}
    operators = {o.record.address: o for o in plan.ir.operators}
    result = []
    for record in records.values():
        if record.address.kind != "requirement":
            continue
        family = F(record.get("family"))
        subkind = next(
            v
            for v in SUBKINDS[family]
            if (None if v is None else v.value) == record.get("subkind")
        )
        origin = records[record.get("origin")]
        pair = record.get("subject")
        role = pair[0]
        if role == "single_match":
            evidence = plan.single_matches[pair[1]].assessment
        elif role == "single_match_proof":
            evidence = plan.single_match_proofs[pair[1]].source
        elif role == "aggregate_risk":
            evidence = plan.aggregate_risks[pair[1]].source
        else:
            # The immutable input contains only references. No range, proof
            # state or old value is accepted as current derived evidence.
            anchors = []
            for address in record.get("anchors"):
                anchor = records[address]
                if address.kind == "slot":
                    anchors.append(facts[anchor.get("literal")])
                elif address in facts:
                    anchors.append(facts[address])
                elif address in operators:
                    anchors.append(operators[address])
                else:
                    anchors.append(anchor)
            evidence = tuple(anchors)
        result.append(
            (
                family,
                subkind,
                semantic[pair],
                owners[origin.get("owner")],
                semantic[record.get("definition")],
                tuple(semantic[p] for p in record.get("stages")),
                tuple(semantic[p] for p in record.get("uses")),
                tuple(semantic[p] for p in origin.get("antecedents")),
                evidence,
                role,
            )
        )
    return tuple(result)


def build_compiled_requirement_report(verification):
    from pietto._project.project_compiled_schema import Address

    plan = _require_compiled_plan(verification)
    records, references = plan.ir.completed.root.records, plan.semantic_references
    entries = []
    for i, (
        family,
        kind,
        subject,
        owner,
        definition,
        stages,
        inputs,
        antecedents,
        evidence,
        role,
    ) in enumerate(compiled_requirement_facts(plan)):
        record = records[Address("requirement", i)]
        described = records[record.get("origin")]
        origin = CompiledDemandOrigin(
            owner,
            references[described.get("subject")],
            antecedents,
            evidence,
            references[("origin", described.address.position)],
            sql.ProjectSQLOriginRole(described.get("role")),
            sql.ProjectSQLOriginProvenance(described.get("provenance")),
            described.get("location"),
        )
        entries.append(
            CompiledDemandEntry(
                i,
                references[("demand", i)],
                family,
                kind,
                subject,
                CompiledDemandScope(definition, stages, inputs),
                origin,
                role,
            )
        )
    entries = tuple(entries)
    links = _compiled_requirement_links(plan, entries)
    return CompiledRequirementReport(
        verification,
        plan,
        entries,
        links,
        _group(tuple(F), entries, lambda e: (e.family,)),
        _group(
            dict.fromkeys(e.subject for e in entries), entries, lambda e: (e.subject,)
        ),
        _group(
            dict.fromkeys(e.scope.definition for e in entries),
            entries,
            lambda e: (e.scope.definition,),
        ),
        _group(
            dict.fromkeys(s for e in entries for s in e.scope.stages),
            entries,
            lambda e: e.scope.stages,
        ),
        _group(
            dict.fromkeys(u for e in entries for u in e.scope.input_uses),
            entries,
            lambda e: e.scope.input_uses,
        ),
        tuple(
            o
            for o in plan.single_matches
            if o.assessment.state is ProjectSingleMatchState.PROVED
        ),
        tuple(o for o in plan.single_matches if o.downstream_enforcement_required),
    )


def _compiled_requirement_links(plan, entries):
    return tuple(
        CompiledDemandLink(
            i,
            ProjectSQLDemandLinkKind(record.get("kind")),
            entries[record.get("source").position],
            entries[record.get("target").position],
        )
        for i, record in enumerate(
            r
            for r in plan.ir.completed.root.records.values()
            if r.address.kind == "requirement_link"
        )
    )


def _verify_compiled_requirement_report(report, verification):
    from pietto._project.project_compiled_schema import Address

    plan = _require_compiled_plan(verification)
    if (
        type(report) is not CompiledRequirementReport
        or report.verification is not verification
        or report.plan is not plan
    ):
        raise ValueError("COMPILED_REQUIREMENT_ROOT")
    expected = compiled_requirement_facts(plan)
    if type(report.entries) is not tuple or len(report.entries) != len(expected):
        raise ValueError("COMPILED_REQUIREMENT_INVENTORY")
    for position, (entry, inputs) in enumerate(
        zip(report.entries, expected, strict=True)
    ):
        (
            family,
            kind,
            subject,
            owner,
            definition,
            stages,
            uses,
            antecedents,
            evidence,
            role,
        ) = inputs
        described_origin = plan.ir.completed.root.records[
            plan.ir.completed.root.records[Address("requirement", position)].get(
                "origin"
            )
        ]
        if (
            type(entry) is not CompiledDemandEntry
            or entry.position != position
            or entry.ref is not plan.semantic_references[("demand", position)]
            or entry.family is not family
            or entry.subkind is not kind
            or not any(kind is v for v in SUBKINDS[family])
            or entry.subject is not subject
            or entry.role != role
            or type(entry.scope) is not CompiledDemandScope
            or entry.scope.definition is not definition
            or not _same(entry.scope.stages, stages)
            or not _same(entry.scope.input_uses, uses)
            or type(entry.origin) is not CompiledDemandOrigin
            or entry.origin.owner is not owner
            or entry.origin.subject
            is not plan.semantic_references[described_origin.get("subject")]
            or entry.origin.ref
            is not plan.semantic_references[
                ("origin", described_origin.address.position)
            ]
            or entry.origin.role
            is not sql.ProjectSQLOriginRole(described_origin.get("role"))
            or entry.origin.provenance
            is not sql.ProjectSQLOriginProvenance(described_origin.get("provenance"))
            or entry.origin.location != described_origin.get("location")
            or not _same(entry.origin.antecedents, antecedents)
            or not (
                entry.origin.evidence is evidence
                or type(evidence) is tuple
                and _same(entry.origin.evidence, evidence)
            )
        ):
            raise ValueError("COMPILED_REQUIREMENT_ENTRY")
    expected_links = []
    for record in plan.ir.completed.root.records.values():
        if record.address.kind == "requirement_link":
            expected_links.append(
                (
                    ProjectSQLDemandLinkKind(record.get("kind")),
                    report.entries[record.get("source").position],
                    report.entries[record.get("target").position],
                )
            )
    if type(report.links) is not tuple or len(report.links) != len(expected_links):
        raise ValueError("COMPILED_REQUIREMENT_LINKS")
    for i, (link, (kind, source, target)) in enumerate(
        zip(report.links, expected_links, strict=True)
    ):
        if (
            type(link) is not CompiledDemandLink
            or link.position != i
            or link.kind is not kind
            or link.source is not source
            or link.target is not target
        ):
            raise ValueError("COMPILED_REQUIREMENT_LINKS")
    for index, keys, member_keys in (
        (report.by_family, tuple(F), lambda e: (e.family,)),
        (
            report.by_subject,
            tuple(dict.fromkeys(e.subject for e in report.entries)),
            lambda e: (e.subject,),
        ),
        (
            report.by_definition,
            tuple(dict.fromkeys(e.scope.definition for e in report.entries)),
            lambda e: (e.scope.definition,),
        ),
        (
            report.by_stage,
            tuple(dict.fromkeys(s for e in report.entries for s in e.scope.stages)),
            lambda e: e.scope.stages,
        ),
        (
            report.by_input_use,
            tuple(dict.fromkeys(u for e in report.entries for u in e.scope.input_uses)),
            lambda e: e.scope.input_uses,
        ),
    ):
        if type(index) is not MappingProxyType or not _same(tuple(index), keys):
            raise ValueError("COMPILED_REQUIREMENT_INDEX")
        # One pass: each entry joins the bucket of every distinct member object
        # (by identity) once, in entry order, as the per-key rescan selected it.
        buckets: dict[int, list] = {}
        for e in report.entries:
            for v in dict.fromkeys(map(id, member_keys(e))):
                buckets.setdefault(v, []).append(e)
        for key in keys:
            if not _same(index[key], tuple(buckets.get(id(key), ()))):
                raise ValueError("COMPILED_REQUIREMENT_INDEX")
    if not _same(
        report.proved,
        tuple(
            o
            for o in plan.single_matches
            if o.assessment.state is ProjectSingleMatchState.PROVED
        ),
    ) or not _same(
        report.enforcement_required,
        tuple(o for o in plan.single_matches if o.downstream_enforcement_required),
    ):
        raise ValueError("COMPILED_REQUIREMENT_SUMMARY")
    return report


def verify_compiled_requirement_report(report, verification):
    """The complete requirement-report check; repeated checks of these exact objects inside one top-level call rely on the completed one."""
    once(_verify_compiled_requirement_report, report, verification)
    return report


def compiled_requirement_rule(plan, entry, *, generated_scopes):
    """Attribute compiled inputs using the original emission owners' rule tables."""
    from pietto._project import project_sql_emission_aggregation as aggregate_rules
    from pietto._project import project_sql_emission_windows as window_rules
    from pietto._project import project_sql_emission_results as result_rules
    from pietto._project.project_compiled_schema import Address

    if type(plan) is not sql.CompiledSQLPlan or type(entry) is not CompiledDemandEntry:
        raise ValueError("COMPILED_REQUIREMENT_RULE_INPUT")
    family = entry.family
    if family is F.FILTER:
        return "R06"
    if family is F.AGGREGATE:
        return aggregate_rules.DEMAND_RULES.get(entry.role, "R12")
    if family is F.WINDOW:
        return window_rules.DEMAND_RULES.get(entry.role, "R14")
    if family is F.RESULT:
        return result_rules.DEMAND_RULES.get(entry.role, "R02")
    if family is F.SET:
        return "R22"
    if family is F.LITERAL:
        return "R04"
    if family is F.EXPRESSION:
        records = plan.ir.completed.root.records
        described = records[Address("requirement", entry.position)]
        anchors = tuple(
            records[a]
            for a in described.get("anchors")
            if a.kind in ("literal", "read", "operation")
        )
        rules = []
        for record in anchors:
            if record.address.kind == "operation":
                role, token = record.get("operator")
                if role == "binary":
                    rules.append("R06" if token in ("and", "or") else "R05")
                    continue
                if role in ("comparison", "null_test"):
                    rules.append("R05")
                    continue
            rules.append("R01" if record.address.kind == "read" else "R04")
        if len(set(rules)) != 1:
            raise ValueError("COMPILED_REQUIREMENT_EXPRESSION_ANCHOR")
        return rules[0]
    if family is F.SCOPE:
        return "R03" if generated_scopes else "R01"
    return "R01" if family is F.SOURCE else "R02"


def verify_compiled_requirement_inputs(records):
    """Validate the closed resolved graph before any derived report exists."""
    from pietto._project.project_compiled_verification import need
    from pietto._project.project_compiled_schema import MAX_RECORDS

    kinds = {kind.value for kind in sql.ProjectSQLPlanRefKind} | {"scope"}
    roles = {v.value for v in sql.ProjectSQLOriginRole}
    provenances = {v.value for v in sql.ProjectSQLOriginProvenance}
    origins = tuple(
        r for r in records.values() if r.address.kind == "requirement_origin"
    )
    demands = tuple(r for r in records.values() if r.address.kind == "requirement")
    need(bool(origins) and bool(demands), "REQUIREMENT_INPUT_INVENTORY")

    def reference(value: tuple[str, int]):
        need(
            type(value) is tuple
            and len(value) == 2
            and type(value[0]) is str
            and value[0] in kinds
            and type(value[1]) is int
            and 0 <= value[1] < MAX_RECORDS,
            "REQUIREMENT_REFERENCE",
        )
        if value[0] == "scope":
            need(value[1] == 0, "REQUIREMENT_SCOPE")
        if value[0] == "origin":
            need(value[1] < len(origins), "REQUIREMENT_ORIGIN_REFERENCE")
        if value[0] == "demand":
            need(value[1] < len(demands), "REQUIREMENT_DEMAND_REFERENCE")

    subjects = {}
    for origin in origins:
        reference(origin.get("subject"))
        need(
            origin.get("role") in roles and origin.get("provenance") in provenances,
            "REQUIREMENT_ORIGIN_KIND",
        )
        owner = records[origin.get("owner")]
        need(owner.address.kind == "declaration", "REQUIREMENT_ORIGIN_OWNER")
        location = origin.get("location")
        need(
            type(location) is tuple
            and len(location) == 5
            and (location[0] is None or type(location[0]) is str)
            and all(type(i) is int and i >= 1 for i in location[1:])
            and location[1:3] <= location[3:5],
            "REQUIREMENT_LOCATION",
        )
        need(type(origin.get("antecedents")) is tuple, "REQUIREMENT_ANTECEDENTS")
        for pair in origin.get("antecedents"):
            reference(pair)
        subjects.setdefault(origin.get("subject"), []).append(origin)
    for i, demand in enumerate(demands):
        try:
            family = F(demand.get("family"))
        except (ValueError, TypeError):
            raise ValueError("COMPILED_REQUIREMENT_FAMILY") from None
        need(
            any(
                (None if value is None else value.value) == demand.get("subkind")
                for value in SUBKINDS[family]
            ),
            "REQUIREMENT_SUBKIND",
        )
        for pair in (
            demand.get("subject"),
            demand.get("definition"),
            *demand.get("stages"),
            *demand.get("uses"),
        ):
            reference(pair)
            need(pair in subjects, "REQUIREMENT_SUBJECT_CLOSURE")
        need(
            demand.get("definition")[0] == "definition"
            and all(p[0] == "input_use" for p in demand.get("uses")),
            "REQUIREMENT_CONTEXT",
        )
        origin = records[demand.get("origin")]
        need(
            origin.address.kind == "requirement_origin"
            and origin.get("subject") == ("demand", i)
            and origin.get("role") == "demand",
            "REQUIREMENT_DEMAND_ORIGIN",
        )
        need(
            type(demand.get("anchors")) is tuple
            and all(a in records for a in demand.get("anchors")),
            "REQUIREMENT_ANCHORS",
        )
        role = demand.get("subject")[0]
        expected = {
            "expression": F.EXPRESSION,
            "stage_port": F.STAGE_VALUE,
            "filter": F.FILTER,
            "select_block": F.SCOPE,
            "bind_use": F.LITERAL,
            "aggregation": F.AGGREGATE,
            "group_key": F.AGGREGATE,
            "aggregate": F.AGGREGATE,
            "aggregate_projection": F.AGGREGATE,
            "aggregate_risk": F.AGGREGATE,
            "window": F.WINDOW,
            "window_use": F.WINDOW,
            "window_argument": F.WINDOW,
            "window_policy": F.WINDOW,
            "window_projection": F.WINDOW,
            "join": F.JOIN,
            "join_input": F.JOIN,
            "join_port": F.JOIN,
            "relationship_match": F.JOIN,
            "join_tail": F.JOIN,
            "single_match": F.JOIN,
            "single_match_proof": F.JOIN,
            "result_boundary": F.RESULT,
            "result_port": F.RESULT,
            "distinct": F.RESULT,
            "quotient_field": F.RESULT,
            "relation_order": F.RESULT,
            "order_item": F.RESULT,
            "order_expression": F.RESULT,
            "order_use": F.RESULT,
            "hidden_order_requirement": F.RESULT,
            "result_limit": F.RESULT,
            "result_export": F.RESULT,
            "set_body": F.SET,
            "set_operand": F.SET,
            "set_input": F.SET,
            "set_column": F.SET,
            "definition": F.SOURCE,
            "export": F.EXPORT,
        }
        need(expected.get(role) is family, "REQUIREMENT_SUBJECT_FAMILY")
    for link in (r for r in records.values() if r.address.kind == "requirement_link"):
        source, target = records[link.get("source")], records[link.get("target")]
        need(
            source.address.kind == target.address.kind == "requirement",
            "REQUIREMENT_LINK_REFERENCE",
        )
        kind = link.get("kind")
        if kind == ProjectSQLDemandLinkKind.LITERAL_CONTEXT.value:
            need(source.get("family") == F.LITERAL.value, "REQUIREMENT_LITERAL_LINK")
        elif kind == ProjectSQLDemandLinkKind.PROOF_ROOT.value:
            need(
                source.get("subject")[0] == "single_match"
                and target.get("subject")[0] == "single_match_proof",
                "REQUIREMENT_PROOF_ROOT",
            )
        elif kind == ProjectSQLDemandLinkKind.PROOF_CHILD.value:
            need(
                source.get("subject")[0]
                == target.get("subject")[0]
                == "single_match_proof",
                "REQUIREMENT_PROOF_CHILD",
            )
        else:
            raise ValueError("COMPILED_REQUIREMENT_LINK_KIND")


def verify_compiled_semantic_references(plan):
    from pietto._project.project_compiled_verification import need

    records = plan.ir.completed.root.records
    expected = {}
    for record in records.values():
        if record.address.kind == "requirement_origin":
            pairs = (
                ("origin", record.address.position),
                record.get("subject"),
                *record.get("antecedents"),
            )
        elif record.address.kind == "requirement":
            pairs = (
                ("demand", record.address.position),
                record.get("subject"),
                record.get("definition"),
                *record.get("stages"),
                *record.get("uses"),
            )
        else:
            continue
        expected.update((pair, None) for pair in pairs)
    need(
        type(plan.semantic_references) is MappingProxyType
        and tuple(plan.semantic_references) == tuple(expected),
        "PLAN_SEMANTIC_REFERENCE_INVENTORY",
    )
    for pair, reference in plan.semantic_references.items():
        need(
            type(reference) is CompiledSemanticReference
            and reference.scope is plan.scope
            and (reference.kind, reference.position) == pair,
            "PLAN_SEMANTIC_REFERENCE",
        )
