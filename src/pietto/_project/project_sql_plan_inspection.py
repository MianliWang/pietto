"""Private, source-bearing, VERIFIED-only immutable SQL plan runtime view."""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Mapping
from types import MappingProxyType
from pietto._project import project_sql_plan_expressions as row
from pietto._project import project_sql_plan_joins as joining

from pietto._project.module_catalog import ProjectDeclarationOccurrence
from pietto._project.project_sql_plan import (
    ProjectSQLPlan,
    ProjectSQLBindings,
    ProjectSQLDefinition,
    ProjectSQLBoundary,
    ProjectSQLSymbol,
    ProjectSQLBlockContext,
    _binding_contexts,
    ProjectSQLPlanScope,
    ProjectSQLPlanRef,
    ProjectSQLSourceBinding,
    ProjectSQLSelectBlock,
    ProjectSQLInputUse,
    ProjectSQLPort,
    ProjectSQLProjection,
    ProjectSQLOrigin,
    ProjectSQLDemand,
)
from pietto._project.project_sql_plan_verification import (
    ProjectSQLPlanVerification,
    ProjectSQLBindingVerification,
    verify_project_sql_bindings,
    verify_project_sql_plan,
)

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLPlanInspection:
    verification: ProjectSQLPlanVerification
    plan: ProjectSQLPlan = field(init=False)
    _contexts: Mapping[ProjectSQLPlanRef, ProjectSQLBlockContext] = field(
        init=False, repr=False
    )
    _stages: Mapping[ProjectSQLPlanRef, row.ProjectSQLStageContext] = field(
        init=False, repr=False
    )
    _expressions: Mapping[ProjectSQLPlanRef, row.ProjectSQLExpression] = field(
        init=False, repr=False
    )
    _matches: Mapping[ProjectSQLPlanRef, joining.ProjectSQLMatchContext] = field(
        init=False, repr=False
    )

    def __post_init__(self) -> None:
        verification = self.verification
        if (
            type(verification) is not ProjectSQLPlanVerification
            or not verification.verified
            or type(verification.plan) is not ProjectSQLPlan
            or verification.plan.scope.completed is not verification.completed
            or verification.plan.scope.analysis_bundle
            is not verification.analysis_bundle
            or verification.plan.scope.selected_owner is not verification.selected_owner
            or not verify_project_sql_plan(
                verification.plan,
                verification.completed,
                verification.analysis_bundle,
                verification.selected_owner,
            ).verified
        ):
            raise ValueError(
                "Runtime inspection requires an exact VERIFIED ProjectSQLPlan."
            )
        object.__setattr__(self, "plan", verification.plan)
        object.__setattr__(
            self,
            "_contexts",
            MappingProxyType(_binding_contexts(verification.plan.bindings)),
        )
        ports = {b.ref: [] for b in self.plan.blocks}
        symbols = {b.ref: [] for b in self.plan.blocks}
        for port in self.plan.stage_ports:
            ports[port.block].append(port)
        for symbol in self.plan.symbols[len(self.plan.bindings.symbols) :]:
            if symbol.scope in symbols:
                symbols[symbol.scope].append(symbol)
        object.__setattr__(
            self,
            "_stages",
            MappingProxyType(
                {
                    b.ref: row.ProjectSQLStageContext(
                        block=b.ref,
                        ports=tuple(ports[b.ref]),
                        symbols=tuple(symbols[b.ref]),
                    )
                    for b in self.plan.blocks
                }
            ),
        )
        object.__setattr__(
            self,
            "_expressions",
            MappingProxyType({e.ref: e for e in self.plan.expressions}),
        )
        match_ports = {j.ref: [] for j in self.plan.joins}
        match_symbols = {j.ref: [] for j in self.plan.joins}
        subjects = set()
        for port in self.plan.join_ports:
            if port.kind is joining.ProjectSQLJoinPortKind.MATCH:
                match_ports[port.block].append(port)
                subjects.add(port.ref)
        for symbol in self.plan.symbols:
            if symbol.subject in subjects:
                match_symbols[symbol.scope].append(symbol)
        object.__setattr__(
            self,
            "_matches",
            MappingProxyType(
                {
                    join.ref: joining.ProjectSQLMatchContext(
                        join=join.ref,
                        ports=tuple(match_ports[join.ref]),
                        symbols=tuple(match_symbols[join.ref]),
                    )
                    for join in self.plan.joins
                }
            ),
        )

    @property
    def expression_sites(self) -> tuple[row.ProjectSQLSite, ...]:
        return self.plan.expression_sites

    @property
    def expressions(self) -> tuple[row.ProjectSQLExpression, ...]:
        return self.plan.expressions

    @property
    def operands(self) -> tuple[row.ProjectSQLExpressionOperand, ...]:
        return self.plan.operands

    @property
    def stage_ports(self) -> tuple[row.ProjectSQLStagePort, ...]:
        return self.plan.stage_ports

    @property
    def let_values(self) -> tuple[row.ProjectSQLLetValue, ...]:
        return self.plan.let_values

    @property
    def filters(self) -> tuple[row.ProjectSQLFilter, ...]:
        return self.plan.filters

    def stage_context(self, ref: ProjectSQLPlanRef) -> row.ProjectSQLStageContext:
        context = self._stages.get(ref)
        if context is None or context.block is not ref:
            raise ValueError("SELECT-block reference does not belong to this plan.")
        return context

    def expression(self, ref: ProjectSQLPlanRef) -> row.ProjectSQLExpression:
        expression = self._expressions.get(ref)
        if expression is None or expression.ref is not ref:
            raise ValueError("Expression reference does not belong to this plan.")
        return expression

    def expressions_for_site(
        self, ref: ProjectSQLPlanRef
    ) -> tuple[row.ProjectSQLExpression, ...]:
        if not any(site.ref is ref for site in self.expression_sites):
            raise ValueError("Expression-site reference does not belong to this plan.")
        return tuple(e for e in self.expressions if e.site.ref is ref)

    def uses_of(
        self, ref: ProjectSQLPlanRef
    ) -> tuple[
        row.ProjectSQLReference
        | row.ProjectSQLJoinedReference
        | row.ProjectSQLMatchReference,
        ...,
    ]:
        if not any(port.ref is ref for port in (*self.stage_ports, *self.join_ports)):
            raise ValueError("Stage-port reference does not belong to this plan.")
        return tuple(
            e
            for e in self.expressions
            if isinstance(
                e,
                (
                    row.ProjectSQLReference,
                    row.ProjectSQLJoinedReference,
                    row.ProjectSQLMatchReference,
                ),
            )
            and e.port is ref
        )

    @property
    def joins(self) -> tuple[joining.ProjectSQLJoin, ...]:
        return self.plan.joins

    @property
    def join_inputs(self) -> tuple[joining.ProjectSQLJoinInput, ...]:
        return self.plan.join_inputs

    @property
    def join_ports(self) -> tuple[joining.ProjectSQLJoinPort, ...]:
        return self.plan.join_ports

    @property
    def relationship_matches(self) -> tuple[joining.ProjectSQLRelationshipMatch, ...]:
        return self.plan.relationship_matches

    @property
    def join_tails(self) -> tuple[joining.ProjectSQLJoinTail, ...]:
        return self.plan.join_tails

    @property
    def single_matches(self) -> tuple[joining.ProjectSQLSingleMatch, ...]:
        return self.plan.single_matches

    @property
    def single_match_proofs(self) -> tuple[joining.ProjectSQLSingleMatchProof, ...]:
        return self.plan.single_match_proofs

    def match_context(self, ref: ProjectSQLPlanRef) -> joining.ProjectSQLMatchContext:
        result = self._matches.get(ref)
        if result is None or result.join is not ref:
            raise ValueError("JOIN reference does not belong to this plan.")
        return result

    def join_outputs(
        self, ref: ProjectSQLPlanRef
    ) -> tuple[joining.ProjectSQLJoinPort, ...]:
        self.match_context(ref)
        return tuple(
            port
            for port in self.join_ports
            if port.block is ref and port.kind is joining.ProjectSQLJoinPortKind.OUTPUT
        )

    def obligations_for_join(
        self, ref: ProjectSQLPlanRef
    ) -> tuple[joining.ProjectSQLSingleMatch, ...]:
        self.match_context(ref)
        return tuple(
            value
            for value in self.single_matches
            if any(ref is join for join in value.joins)
        )

    @property
    def selected_owner(self) -> ProjectDeclarationOccurrence:
        return self.plan.scope.selected_owner

    @property
    def scope(self) -> ProjectSQLPlanScope:
        return self.plan.scope

    @property
    def sources(self) -> tuple[ProjectSQLSourceBinding, ...]:
        return self.plan.sources

    @property
    def blocks(self) -> tuple[ProjectSQLSelectBlock, ...]:
        return self.plan.blocks

    @property
    def input_uses(self) -> tuple[ProjectSQLInputUse, ...]:
        return self.plan.input_uses

    @property
    def source_ports(self) -> tuple[ProjectSQLPort, ...]:
        return self.plan.source_ports

    @property
    def input_ports(self) -> tuple[ProjectSQLPort, ...]:
        return self.plan.input_ports

    @property
    def exports(self) -> tuple[ProjectSQLPort, ...]:
        return self.plan.exports

    @property
    def projections(self) -> tuple[ProjectSQLProjection, ...]:
        return self.plan.projections

    @property
    def origins(self) -> tuple[ProjectSQLOrigin, ...]:
        return self.plan.origins

    @property
    def demands(self) -> tuple[ProjectSQLDemand, ...]:
        return self.plan.demands

    @property
    def definitions(self) -> tuple[ProjectSQLDefinition, ...]:
        return self.plan.bindings.definitions

    @property
    def all_exports(self) -> tuple[ProjectSQLPort, ...]:
        return self.plan.all_exports

    @property
    def intermediate_exports(self) -> tuple[ProjectSQLPort, ...]:
        selected = next(
            d.ref for d in self.definitions if d.entry.owner is self.selected_owner
        )
        return tuple(p for p in self.all_exports if p.owner is not selected)

    @property
    def symbols(self) -> tuple[ProjectSQLSymbol, ...]:
        return self.plan.symbols

    @property
    def boundaries(self) -> tuple[ProjectSQLBoundary, ...]:
        return self.plan.boundaries

    def context(self, scope: ProjectSQLPlanRef) -> ProjectSQLBlockContext:
        context = self._contexts.get(scope)
        if context is None or context.definition.ref is not scope:
            raise ValueError("Definition reference does not belong to this plan.")
        return context

    def projections_for_input(
        self, ref: ProjectSQLPlanRef
    ) -> tuple[ProjectSQLProjection, ...]:
        if not any(port.ref is ref for port in self.input_ports):
            raise ValueError("Input-port reference does not belong to this plan.")
        return tuple(p for p in self.projections if p.input_port is ref)


def inspect_project_sql_plan(
    verification: ProjectSQLPlanVerification,
) -> ProjectSQLPlanInspection:
    return ProjectSQLPlanInspection(verification=verification)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLBindingInspection:
    verification: ProjectSQLBindingVerification
    bindings: ProjectSQLBindings = field(init=False)
    _contexts: Mapping[ProjectSQLPlanRef, ProjectSQLBlockContext] = field(
        init=False, repr=False
    )

    def __post_init__(self) -> None:
        v = self.verification
        if (
            type(v) is not ProjectSQLBindingVerification
            or not v.verified
            or type(v.bindings) is not ProjectSQLBindings
            or not verify_project_sql_bindings(
                v.bindings, v.completed, v.analysis_bundle, v.selected_owner
            ).verified
        ):
            raise ValueError("Binding inspection requires exact VERIFIED bindings.")
        object.__setattr__(self, "bindings", v.bindings)
        object.__setattr__(
            self, "_contexts", MappingProxyType(_binding_contexts(v.bindings))
        )

    @property
    def definitions(self) -> tuple[ProjectSQLDefinition, ...]:
        return self.bindings.definitions

    @property
    def input_uses(self) -> tuple[ProjectSQLInputUse, ...]:
        return self.bindings.input_uses

    @property
    def sources(self) -> tuple[ProjectSQLSourceBinding, ...]:
        return self.bindings.sources

    @property
    def symbols(self) -> tuple[ProjectSQLSymbol, ...]:
        return self.bindings.symbols

    @property
    def origins(self) -> tuple[ProjectSQLOrigin, ...]:
        return self.bindings.origins

    @property
    def demands(self) -> tuple[ProjectSQLDemand, ...]:
        return self.bindings.demands

    @property
    def all_exports(self) -> tuple[ProjectSQLPort, ...]:
        return self.bindings.all_exports

    @property
    def source_ports(self) -> tuple[ProjectSQLPort, ...]:
        return self.bindings.source_ports

    @property
    def input_ports(self) -> tuple[ProjectSQLPort, ...]:
        return self.bindings.input_ports

    @property
    def boundaries(self) -> tuple[ProjectSQLBoundary, ...]:
        return self.bindings.boundaries

    def context(self, scope: ProjectSQLPlanRef) -> ProjectSQLBlockContext:
        context = self._contexts.get(scope)
        if context is None or context.definition.ref is not scope:
            raise ValueError("Definition reference does not belong to these bindings.")
        return context


def inspect_project_sql_bindings(
    verification: ProjectSQLBindingVerification,
) -> ProjectSQLBindingInspection:
    return ProjectSQLBindingInspection(verification=verification)
