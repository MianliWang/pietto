"""Private, source-bearing, VERIFIED-only immutable SQL plan runtime view."""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Mapping
from types import MappingProxyType
from pietto._project import project_sql_plan_expressions as row
from pietto._project import project_sql_plan_aggregation as aggregation
from pietto._project import project_sql_plan_windows as windows
from pietto._project import project_sql_plan_joins as joining
from pietto._project import project_sql_plan_results as results
from pietto._project import project_sql_plan_sets as sets
from pietto._project import project_sql_plan_literals as literals
from pietto._project import project_sql_plan_requirements as requirements
from pietto._project import project_sql_plan_source_maps as source_maps

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
    _terminals: Mapping[
        ProjectSQLPlanRef, ProjectSQLPort | results.ProjectSQLResultPort
    ] = field(init=False, repr=False)

    def requirements(self) -> requirements.ProjectSQLRequirementInspection:
        report = requirements.build_project_sql_requirement_report(self.verification)
        checked = requirements.verify_project_sql_requirement_report(
            report, self.verification
        )
        return requirements.inspect_project_sql_requirement_report(checked)

    def source_map(self) -> source_maps.ProjectSQLSourceMapInspection:
        product = source_maps.build_project_sql_source_map(self.verification)
        checked = source_maps.verify_project_sql_source_map(product, self.verification)
        return source_maps.inspect_project_sql_source_map(checked)

    def __post_init__(self) -> None:
        verification = self.verification
        if (
            type(verification) is not ProjectSQLPlanVerification
            or not verification.verified
            or type(verification.plan) is not ProjectSQLPlan
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
                "Runtime inspection requires an exact VERIFIED ProjectSQLPlan."
            )
        object.__setattr__(self, "plan", verification.plan)
        object.__setattr__(
            self,
            "_terminals",
            MappingProxyType(results.terminal_index(verification.plan)),
        )
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
    def result_boundaries(self) -> tuple[results.ProjectSQLResultBoundary, ...]:
        return self.plan.result_boundaries

    @property
    def result_ports(self) -> tuple[results.ProjectSQLResultPort, ...]:
        return self.plan.result_ports

    @property
    def distincts(self) -> tuple[results.ProjectSQLDistinct, ...]:
        return self.plan.distincts

    @property
    def quotient_fields(self) -> tuple[results.ProjectSQLQuotientField, ...]:
        return self.plan.quotient_fields

    @property
    def orders(self) -> tuple[results.ProjectSQLOrder, ...]:
        return self.plan.orders

    @property
    def order_items(self) -> tuple[results.ProjectSQLOrderItem, ...]:
        return self.plan.order_items

    @property
    def order_uses(self) -> tuple[results.ProjectSQLOrderUse, ...]:
        return self.plan.order_uses

    @property
    def order_expressions(self) -> tuple[results.ProjectSQLOrderExpression, ...]:
        return self.plan.order_expressions

    @property
    def hidden_order_requirements(
        self,
    ) -> tuple[results.ProjectSQLHiddenOrderRequirement, ...]:
        return self.plan.hidden_order_requirements

    @property
    def limits(self) -> tuple[results.ProjectSQLResultLimit, ...]:
        return self.plan.result_limits

    @property
    def result_exports(self) -> tuple[results.ProjectSQLResultExport, ...]:
        return self.plan.result_exports

    def result_stages(self, definition: ProjectSQLPlanRef):
        self.context(definition)
        bodies = tuple(
            body for body in self.plan.set_bodies if body.definition is definition
        )
        if bodies:
            return bodies
        return (
            *tuple(block for block in self.blocks if block.definition is definition),
            *tuple(
                boundary
                for boundary in self.result_boundaries
                if boundary.definition is definition
            ),
        )

    def terminal_exports(
        self, definition: ProjectSQLPlanRef
    ) -> tuple[ProjectSQLPort | results.ProjectSQLResultPort, ...]:
        context = self.context(definition)
        return tuple(
            self._terminals[canonical.ref] for canonical in context.definition.exports
        )

    def input_terminals(
        self, use: ProjectSQLPlanRef
    ) -> tuple[ProjectSQLPort | results.ProjectSQLResultPort, ...]:
        matches = tuple(item for item in self.input_uses if item.ref is use)
        if len(matches) != 1:
            raise ValueError("Input use does not belong to this plan.")
        return self.terminal_exports(matches[0].producer)

    @property
    def set_bodies(self) -> tuple[sets.ProjectSQLSetBody, ...]:
        return self.plan.set_bodies

    @property
    def set_operands(self) -> tuple[sets.ProjectSQLSetOperand, ...]:
        return self.plan.set_operands

    @property
    def set_inputs(self) -> tuple[sets.ProjectSQLSetInput, ...]:
        return self.plan.set_inputs

    @property
    def set_columns(self) -> tuple[sets.ProjectSQLSetColumn, ...]:
        return self.plan.set_columns

    def set_body(self, ref: ProjectSQLPlanRef) -> sets.ProjectSQLSetBody:
        matches = tuple(body for body in self.set_bodies if body.ref is ref)
        if len(matches) != 1:
            raise ValueError("SET body does not belong to this plan.")
        return matches[0]

    def operands_for_set(
        self, ref: ProjectSQLPlanRef
    ) -> tuple[sets.ProjectSQLSetOperand, ...]:
        self.set_body(ref)
        return tuple(operand for operand in self.set_operands if operand.body is ref)

    def fields_for_set_operand(
        self, ref: ProjectSQLPlanRef
    ) -> tuple[sets.ProjectSQLSetInput, ...]:
        if not any(operand.ref is ref for operand in self.set_operands):
            raise ValueError("SET operand does not belong to this plan.")
        return tuple(field for field in self.set_inputs if field.operand is ref)

    def set_requirements(
        self, ref: ProjectSQLPlanRef
    ) -> tuple[sets.ProjectSQLSetDemand, ...]:
        body = self.set_body(ref)
        context = sets.origin_context(self.plan)
        return tuple(
            demand
            for demand in self.demands
            if isinstance(demand, sets.ProjectSQLSetDemand)
            and sets.origin_parts(demand.witness, context)[0] is body.definition
        )

    def result_port(
        self, scope: ProjectSQLPlanRef, reference: ProjectSQLPlanRef
    ) -> results.ProjectSQLResultPort:
        matches = tuple(
            port
            for port in self.result_ports
            if port.ref is reference and port.boundary is scope
        )
        if len(matches) != 1:
            raise ValueError("Result port is outside this exact result scope.")
        return matches[0]

    def order_uses_for(
        self, item: ProjectSQLPlanRef
    ) -> tuple[results.ProjectSQLOrderUse, ...]:
        if not any(value.ref is item for value in self.order_items):
            raise ValueError("ORDER item reference does not belong to this plan.")
        return tuple(use for use in self.order_uses if use.item is item)

    def hidden_order_requirement(
        self, reference: ProjectSQLPlanRef
    ) -> results.ProjectSQLHiddenOrderRequirement:
        matches = tuple(
            requirement
            for requirement in self.hidden_order_requirements
            if requirement.ref is reference
        )
        if len(matches) != 1:
            raise ValueError("Hidden ORDER requirement does not belong to this plan.")
        return matches[0]

    def result_requirements(
        self, definition: ProjectSQLPlanRef
    ) -> tuple[results.ProjectSQLResultDemand, ...]:
        self.context(definition)
        context = results.origin_context(self.plan)
        return tuple(
            demand
            for demand in self.demands
            if isinstance(demand, results.ProjectSQLResultDemand)
            and results.origin_parts(demand.witness, context)[0] is definition
        )

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

    @property
    def literal_policy(self) -> literals.ProjectSQLLiteralPolicy:
        return self.plan.literal_policy

    @property
    def literal_sites(self) -> tuple[literals.ProjectSQLLiteralSite, ...]:
        return self.plan.literal_sites

    @property
    def literal_slots(self) -> tuple[literals.ProjectSQLLiteralSlot, ...]:
        return self.plan.literal_slots

    @property
    def fixed_envelope(self) -> literals.ProjectSQLFixedEnvelope:
        return self.plan.fixed_envelope

    @property
    def bind_uses(self) -> tuple[literals.ProjectSQLBindUse, ...]:
        return self.plan.bind_uses

    def literal_site(self, ref: ProjectSQLPlanRef) -> literals.ProjectSQLLiteralSite:
        matches = tuple(site for site in self.literal_sites if site.ref is ref)
        if len(matches) != 1:
            raise ValueError("Literal site does not belong to this plan.")
        return matches[0]

    def fixed_value(
        self, slot: ProjectSQLPlanRef
    ) -> literals.ProjectSQLFixedLiteralValue:
        matches = tuple(
            value for value in self.fixed_envelope.values if value.slot.ref is slot
        )
        if len(matches) != 1:
            raise ValueError("Fixed slot does not belong to this plan.")
        return matches[0]

    def literal_value(
        self, expression: ProjectSQLPlanRef
    ) -> row.ProjectSQLLiteral | literals.ProjectSQLFixedLiteralValue:
        """Consume the expression's actual transport; a bind cannot fall back."""
        value = self.expression(expression)
        if type(value) is row.ProjectSQLLiteral:
            return value
        if type(value) is row.ProjectSQLBoundLiteral:
            return self.fixed_value(value.use.slot.ref)
        raise ValueError("Expression is not a literal transport.")

    def uses_for_slot(
        self, slot: ProjectSQLPlanRef
    ) -> tuple[literals.ProjectSQLBindUse, ...]:
        self.fixed_value(slot)
        return tuple(use for use in self.bind_uses if use.slot.ref is slot)

    def literal_requirements(
        self, slot: ProjectSQLPlanRef
    ) -> tuple[literals.ProjectSQLLiteralDemand, ...]:
        self.fixed_value(slot)
        return tuple(
            demand
            for demand in self.demands
            if isinstance(demand, literals.ProjectSQLLiteralDemand)
            and demand.use.slot.ref is slot
        )

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
        | row.ProjectSQLMatchReference
        | aggregation.ProjectSQLResultReference
        | windows.ProjectSQLWindowReference,
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
                    aggregation.ProjectSQLResultReference,
                    windows.ProjectSQLWindowReference,
                ),
            )
            and e.port is ref
        )

    @property
    def windows(self) -> tuple[windows.ProjectSQLWindow, ...]:
        return self.plan.windows

    @property
    def window_uses(self) -> tuple[windows.ProjectSQLWindowUse, ...]:
        return self.plan.window_uses

    @property
    def window_arguments(self) -> tuple[windows.ProjectSQLWindowArgument, ...]:
        return self.plan.window_arguments

    @property
    def window_policies(self) -> tuple[windows.ProjectSQLWindowPolicy, ...]:
        return self.plan.window_policies

    @property
    def window_projections(self) -> tuple[windows.ProjectSQLWindowProjection, ...]:
        return self.plan.window_projections

    @property
    def qualify_sites(self) -> tuple[windows.ProjectSQLQualifySite, ...]:
        return tuple(
            site
            for site in self.expression_sites
            if isinstance(site, windows.ProjectSQLQualifySite)
        )

    def window(self, ref: ProjectSQLPlanRef) -> windows.ProjectSQLWindow:
        matches = tuple(value for value in self.windows if value.ref is ref)
        if len(matches) != 1:
            raise ValueError("Window reference does not belong to this plan.")
        return matches[0]

    def inputs_for_window(
        self, ref: ProjectSQLPlanRef
    ) -> tuple[windows.ProjectSQLWindowUse, ...]:
        self.window(ref)
        return tuple(use for use in self.window_uses if use.window is ref)

    def arguments_for_window(
        self, ref: ProjectSQLPlanRef
    ) -> tuple[windows.ProjectSQLWindowArgument, ...]:
        self.window(ref)
        return tuple(
            argument for argument in self.window_arguments if argument.window is ref
        )

    def policy_for_window(
        self, ref: ProjectSQLPlanRef
    ) -> windows.ProjectSQLWindowPolicy:
        value = self.window(ref)
        return next(
            policy for policy in self.window_policies if policy.ref is value.policy
        )

    def window_requirements(
        self, ref: ProjectSQLPlanRef
    ) -> tuple[windows.ProjectSQLWindowDemand, ...]:
        value = self.window(ref)
        subjects = (
            value.ref,
            *value.uses,
            *value.arguments,
            value.policy,
            *(
                projection.ref
                for projection in self.window_projections
                if projection.window is ref
            ),
        )
        return tuple(
            demand
            for demand in self.demands
            if isinstance(demand, windows.ProjectSQLWindowDemand)
            and any(demand.subject is subject for subject in subjects)
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
    def aggregations(self) -> tuple[aggregation.ProjectSQLAggregation, ...]:
        return self.plan.aggregations

    @property
    def group_keys(self) -> tuple[aggregation.ProjectSQLGroupKey, ...]:
        return self.plan.group_keys

    @property
    def aggregates(self) -> tuple[aggregation.ProjectSQLAggregate, ...]:
        return self.plan.aggregates

    @property
    def aggregate_projections(
        self,
    ) -> tuple[aggregation.ProjectSQLAggregateProjection, ...]:
        return self.plan.aggregate_projections

    @property
    def aggregate_risks(self) -> tuple[aggregation.ProjectSQLAggregateRisk, ...]:
        return self.plan.aggregate_risks

    def aggregation(self, ref: ProjectSQLPlanRef) -> aggregation.ProjectSQLAggregation:
        values = tuple(a for a in self.aggregations if a.ref is ref)
        if len(values) != 1:
            raise ValueError("Aggregation reference does not belong to this plan.")
        return values[0]

    def arguments_for_aggregate(
        self, ref: ProjectSQLPlanRef
    ) -> tuple[row.ProjectSQLExpression, ...]:
        values = tuple(a for a in self.aggregates if a.ref is ref)
        if len(values) != 1:
            raise ValueError("Aggregate reference does not belong to this plan.")
        return tuple(self.expression(argument) for argument in values[0].arguments)

    def satisfying_uses(
        self, ref: ProjectSQLPlanRef
    ) -> tuple[aggregation.ProjectSQLResultReference, ...]:
        self.aggregation(ref)
        return tuple(
            e
            for e in self.expressions
            if isinstance(e, aggregation.ProjectSQLResultReference)
            and e.site.aggregation is ref
        )

    def aggregate_requirements(
        self, ref: ProjectSQLPlanRef
    ) -> tuple[aggregation.ProjectSQLAggregateDemand, ...]:
        self.aggregation(ref)
        return tuple(
            d
            for d in self.demands
            if isinstance(d, aggregation.ProjectSQLAggregateDemand)
            and (d.witness.ref is ref or getattr(d.witness, "aggregation", None) is ref)
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
