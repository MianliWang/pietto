"""Private neutral result fields over retained, verified completed output."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pietto._project.model import ProjectResolvedTypeKind
from pietto._project.project_sql_plan import ProjectSQLPlan
from pietto._project.project_query_block_ir import ProjectIRQueryBlockTerminal
from pietto._project.project_sql_plan_verification import (
    ProjectSQLPlanVerification,
    verify_project_sql_plan,
)

__all__: tuple[str, ...] = ()


class ResultError(ValueError):
    """Stable private boundary category; not a public compiler diagnostic."""

    def __init__(self, category: str):
        self.category = category
        super().__init__(category)


@dataclass(frozen=True, slots=True, eq=False)
class ScalarShape:
    declared: Any = field(repr=False)
    canonical: Any = field(repr=False)


@dataclass(frozen=True, slots=True, eq=False)
class ResultField:
    ordinal: int
    label: str
    port: Any = field(repr=False)
    shape: ScalarShape
    nullability: Any = field(repr=False)
    provenance: Any = field(repr=False)


@dataclass(frozen=True, slots=True, eq=False)
class ResultShape:
    """Ordered scalar leaves only. Nested shapes are not admitted yet."""

    fields: tuple[ResultField, ...] = field(repr=False)


@dataclass(frozen=True, slots=True, eq=False)
class PiettoResultContract:
    authority: ProjectSQLPlanVerification = field(repr=False)
    owner: Any = field(repr=False)
    output: Any = field(repr=False)
    shape: ResultShape
    multiplicity: Any = field(repr=False)
    ordering: Any = field(repr=False)


def _neutral(checked):
    if (
        type(checked) is not ProjectSQLPlanVerification
        or type(checked.plan) is not ProjectSQLPlan
    ):
        raise ResultError("ROOT")
    if not verify_project_sql_plan(
        checked.plan,
        checked.completed,
        checked.analysis_bundle,
        checked.selected_owner,
        literal_policy=checked.literal_policy,
        envelope=checked.envelope,
    ).verified:
        raise ResultError("ROOT")
    entries = checked.analysis_bundle.root.find_owner(checked.selected_owner)
    if len(entries) != 1 or isinstance(entries[0], ProjectIRQueryBlockTerminal):
        raise ResultError("ROOT")
    return entries[0]


def build_result_contract(checked: ProjectSQLPlanVerification) -> PiettoResultContract:
    entry = _neutral(checked)
    plan: Any = checked.plan
    leaves = []
    for ordinal, port in enumerate(plan.exports):
        evidence = port.field.evidence
        if evidence.resolved_type.kind in (
            ProjectResolvedTypeKind.UNKNOWN,
            ProjectResolvedTypeKind.SHAPE,
        ):
            raise ResultError("SCALAR_UNAVAILABLE")
        declared = (
            evidence.field_def.type_expr if evidence.field_def is not None else None
        )
        leaves.append(
            ResultField(
                ordinal,
                port.identity.name,
                port,
                ScalarShape(declared, evidence.resolved_type),
                port.field.effective_nullability,
                evidence.provenance,
            )
        )
    contract = PiettoResultContract(
        checked,
        checked.selected_owner,
        entry.active_output,
        ResultShape(tuple(leaves)),
        entry.active_properties.multiplicity,
        entry.active_properties.ordering,
    )
    verify_result_contract(contract, checked)
    return contract


def verify_result_contract(contract, checked) -> None:
    """Compare every retained occurrence to upstream; never rebuild a contract."""
    entry = _neutral(checked)
    if (
        type(contract) is not PiettoResultContract
        or contract.authority is not checked
        or contract.owner is not checked.selected_owner
        or contract.output is not entry.active_output
        or contract.multiplicity is not entry.active_properties.multiplicity
        or contract.ordering is not entry.active_properties.ordering
    ):
        raise ResultError("ROOT")
    if (
        type(contract.shape) is not ResultShape
        or type(contract.shape.fields) is not tuple
    ):
        raise ResultError("FIELD")
    ports = checked.plan.exports
    if len(contract.shape.fields) != len(ports):
        raise ResultError("FIELD")
    for ordinal, (leaf, port) in enumerate(
        zip(contract.shape.fields, ports, strict=True)
    ):
        evidence = port.field.evidence
        declared = (
            evidence.field_def.type_expr if evidence.field_def is not None else None
        )
        if (
            type(leaf) is not ResultField
            or type(leaf.ordinal) is not int
            or leaf.ordinal != ordinal
            or leaf.label != port.identity.name
            or leaf.port is not port
            or type(leaf.shape) is not ScalarShape
            or leaf.shape.declared is not declared
            or leaf.shape.canonical is not evidence.resolved_type
            or evidence.resolved_type.kind
            in (ProjectResolvedTypeKind.UNKNOWN, ProjectResolvedTypeKind.SHAPE)
            or leaf.nullability is not port.field.effective_nullability
            or leaf.provenance is not evidence.provenance
        ):
            raise ResultError("FIELD")
