"""Shared refinement fixtures for execution-layer tests."""

from dataclasses import replace

from _pietto_execution_rows_cases import build
from pietto._project.project_execution_source import RetainedSourceRequirement
from pietto._project.project_refinement import TieRefinement, prepare_refinement


def capabilities(artifact, *, width=1):
    return tuple(
        RetainedSourceRequirement(
            source,
            "explicit-fixture-provider",
            "v1",
            "r1",
            source.namespace,
            "registry",
            "explicit fixture view definition",
            tuple("key" + str(index) for index in range(width)),
            "pietto_query",
            "Fixture declaration only; fresh native admission is separate.",
        )
        for source in artifact.request.sources
    )


def refined(directory, target, case, variant):
    artifact = build(directory, target, case, variant).artifact
    return prepare_refinement(artifact, capabilities(artifact), policy=TieRefinement())


def rewrite_cte(query, position, replacement):
    old = query.statement.ctes[position]
    ctes = tuple(replacement if cte is old else cte for cte in query.statement.ctes)
    units = tuple(
        replace(
            unit, ctes=tuple(replacement if cte is old else cte for cte in unit.ctes)
        )
        for unit in query.units
    )
    return replace(query, statement=replace(query.statement, ctes=ctes), units=units)
