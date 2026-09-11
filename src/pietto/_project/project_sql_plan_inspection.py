"""Private, source-bearing, VERIFIED-only immutable SQL plan runtime view."""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Mapping
from types import MappingProxyType

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
