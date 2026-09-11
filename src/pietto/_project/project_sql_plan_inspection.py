"""Private, source-bearing, VERIFIED-only immutable SQL plan runtime view."""

from __future__ import annotations

from dataclasses import dataclass, field

from pietto._project.module_catalog import ProjectDeclarationOccurrence
from pietto._project.project_sql_plan import (
    ProjectSQLPlan,
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
    verify_project_sql_plan,
)

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLPlanInspection:
    verification: ProjectSQLPlanVerification
    plan: ProjectSQLPlan = field(init=False)

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
