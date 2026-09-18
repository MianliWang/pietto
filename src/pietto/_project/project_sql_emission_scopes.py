"""Exact definition/use/terminal images, including graphs with later operators."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pietto._project.project_sql_plan import (
    ProjectSQLPlan,
    ProjectSQLPlanRef,
    ProjectSQLPort,
)
from pietto._project.project_sql_plan_results import ProjectSQLResultPort
from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan
from pietto._project.project_sql_plan_verification import verify_project_sql_plan

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class ScopeDefinition:
    original: Any
    terminals: tuple[Any, ...]


@dataclass(frozen=True, slots=True, eq=False)
class TerminalBinding:
    canonical: Any
    terminal: Any
    input_port: Any


@dataclass(frozen=True, slots=True, eq=False)
class ScopeUse:
    original: Any
    producer: ScopeDefinition
    consumer: ScopeDefinition
    bindings: tuple[TerminalBinding, ...]


@dataclass(frozen=True, slots=True, eq=False)
class EmissionLayout:
    verification: Any
    definitions: tuple[ScopeDefinition, ...]
    uses: tuple[ScopeUse, ...]


def build_emission_layout(verification):
    view = inspect_project_sql_plan(verification)
    definitions = tuple(
        ScopeDefinition(d, view.terminal_exports(d.ref)) for d in view.definitions
    )
    by_ref = {d.original.ref: d for d in definitions}
    uses = tuple(
        ScopeUse(
            use,
            by_ref[use.producer],
            by_ref[use.consumer],
            tuple(
                TerminalBinding(canonical, terminal, port)
                for canonical, terminal, port in zip(
                    by_ref[use.producer].original.exports,
                    view.input_terminals(use.ref),
                    use.ports,
                    strict=True,
                )
            ),
        )
        for use in view.input_uses
    )
    return EmissionLayout(verification, definitions, uses)


def verify_emission_layout(layout, verification):
    """Reconstruct terminal images and graph order from the original plan."""
    try:
        plan = verification.plan
        if (
            type(layout) is not EmissionLayout
            or layout.verification is not verification
            or type(plan) is not ProjectSQLPlan
            or not verify_project_sql_plan(
                plan,
                verification.completed,
                verification.analysis_bundle,
                verification.selected_owner,
                literal_policy=verification.literal_policy,
                envelope=verification.envelope,
            ).verified
            or type(layout.definitions) is not tuple
            or type(layout.uses) is not tuple
            or len(layout.definitions) != len(plan.bindings.definitions)
            or len(layout.uses) != len(plan.input_uses)
        ):
            return False
        # Independent of the inspection helper used by construction. Canonical
        # exports and their actual terminal result ports are distinct objects.
        results = {port.ref: port for port in plan.result_ports}
        terminals: dict[ProjectSQLPlanRef, ProjectSQLPort | ProjectSQLResultPort] = {
            port.ref: port for port in plan.source_ports
        }
        for image in plan.result_exports:
            if image.canonical.ref in terminals or image.port not in results:
                return False
            terminals[image.canonical.ref] = results[image.port]
        definitions = {}
        positions = {}
        for i, (image, original) in enumerate(
            zip(layout.definitions, plan.bindings.definitions, strict=True)
        ):
            if (
                type(image) is not ScopeDefinition
                or image.original is not original
                or type(image.terminals) is not tuple
                or len(image.terminals) != len(original.exports)
                or original.ref in definitions
            ):
                return False
            for terminal, canonical in zip(
                image.terminals, original.exports, strict=True
            ):
                if terminal is not terminals[canonical.ref]:
                    return False
            definitions[original.ref] = image
            positions[original.ref] = i
        observed = set()
        for image, original in zip(layout.uses, plan.input_uses, strict=True):
            if (
                type(image) is not ScopeUse
                or image.original is not original
                or original.ref in observed
                or image.producer is not definitions[original.producer]
                or image.consumer is not definitions[original.consumer]
                or positions[original.producer] >= positions[original.consumer]
                or type(image.bindings) is not tuple
                or len(image.bindings) != len(original.ports)
                or len(image.bindings) != len(image.producer.original.exports)
            ):
                return False
            observed.add(original.ref)
            for binding, port, canonical in zip(
                image.bindings,
                original.ports,
                image.producer.original.exports,
                strict=True,
            ):
                if (
                    type(binding) is not TerminalBinding
                    or binding.canonical is not canonical
                    or binding.terminal is not terminals[canonical.ref]
                    or binding.input_port is not port
                    or port.owner is not original.ref
                    or port.producer_port is not canonical.ref
                ):
                    return False
        return True
    except (AttributeError, TypeError, ValueError, IndexError, KeyError):
        return False


def projection_sources(plan):
    """Trace retained field-only port edges for physical-premise applicability."""
    sources = {port.ref: port for port in plan.source_ports}
    for projection in plan.projections:
        if projection.source_port in sources:
            sources[projection.export] = sources[projection.source_port]
    return sources
