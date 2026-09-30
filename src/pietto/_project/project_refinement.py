"""Explicit live refinement authority, distinct from an original emission.

An original artifact never acquires different SQL. Source capabilities, the
pre-attempt choice policy, and the full original output remain separate roots.
"""

from dataclasses import dataclass, field
from typing import Any

from pietto._project.project_execution_source import (
    RetainedSourceRequirement,
    requirement_state,
    verify_requirement,
)
from pietto._project.project_result_output import GeneralOutput, prepare_output
from pietto._project.project_refinement_order import Coordinate
from pietto._project.project_refinement_rendering import CTE, Statement

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class TieRefinement:
    """Caller opt-in before any attempt; no mutable chooser or callback."""

    choice: str = "structural_occurrence_ascending"


@dataclass(frozen=True, slots=True, eq=False)
class UnitRefinement:
    original: Any = field(repr=False)
    address: int
    rule: str
    dependencies: tuple[int, ...]
    ctes: tuple[CTE, ...] = field(repr=False)
    terminal: str
    public_names: tuple[str, ...]
    key_names: tuple[str, ...]
    coordinates: tuple[Coordinate, ...]
    order_names: tuple[str, ...]
    order_coordinates: tuple[Coordinate, ...]
    directions: tuple[str, ...]
    capacity: str


@dataclass(frozen=True, slots=True, eq=False)
class RefinedQuery:
    original: Any = field(repr=False)
    output: GeneralOutput = field(repr=False)
    policy: TieRefinement
    sources: tuple[RetainedSourceRequirement, ...] = field(repr=False)
    source_states: tuple = field(repr=False)
    units: tuple[UnitRefinement, ...] = field(repr=False)
    statement: Statement = field(repr=False)
    prefix: str
    erasure: tuple[tuple[int, Any], ...] = field(repr=False)


def verify_sources(requirements, sources, *, family="postgres"):
    """Exact ordered complete collection; repeated uses share their source root."""
    if type(requirements) is not tuple or len(requirements) != len(sources):
        raise ValueError("REFINEMENT_SOURCE_CLOSURE")
    for requirement, source in zip(requirements, sources, strict=True):
        if (
            type(requirement) is not RetainedSourceRequirement
            or requirement.source is not source
        ):
            raise ValueError("REFINEMENT_SOURCE_CORRESPONDENCE")
        verify_requirement(requirement, sources, family=family)
    if len({id(s.source) for s in requirements}) != len(requirements):
        # This set checks live root duplication only; its values never become
        # coordinates, structural addresses, or reopen authority.
        raise ValueError("REFINEMENT_DUPLICATE_SOURCE")


def prepare_refinement(artifact, sources, *, policy, output=None, binding=None):
    from pietto._project.project_refinement_lowering import lower
    from pietto._project.project_refinement_verification import verify_refinement

    if (
        type(policy) is not TieRefinement
        or policy.choice != "structural_occurrence_ascending"
    ):
        raise ValueError("REFINEMENT_POLICY")
    if output is None:
        output = prepare_output(artifact, binding=binding)
    verify_sources(sources, artifact.request.sources, family=artifact.request.family)
    units, statement, prefix = lower(output, sources)
    value = RefinedQuery(
        artifact,
        output,
        policy,
        sources,
        tuple(requirement_state(s) for s in sources),
        units,
        statement,
        prefix,
        tuple((i, c) for i, c in enumerate(output.columns)),
    )
    verify_refinement(value)
    return value
