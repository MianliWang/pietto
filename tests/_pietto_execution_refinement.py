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


# One valid statement time, as a recovery records and every R2 page binds it.
CLOCK = "2026-11-13 10:00:00.123456"


def now_project(directory, text):
    """`write_temporal_example` (fields id, label, stamp, opt) plus `text`."""
    import _pietto_execution_api as api

    project = api.write_temporal_example(directory)
    main = project / "main.pietto"
    main.write_text(main.read_text(encoding="utf-8") + text, encoding="utf-8")
    return project


def live_refinement(project, name, *, kind="table", parameters=None):
    """The R2 refinement of one live PostgreSQL query with its literal values
    and ``parameters``, built without preparation's last first-page check."""
    import pietto.execution as execution
    from pietto._project.project_execution_template import bind_values, named_values
    from pietto._project.project_public_r2_proposal import retained_requirements
    from pietto._project.project_refinement import _prepare_refinement

    query = execution.compile_query(
        project,
        module="main.pietto",
        kind=kind,
        name=name,
        dialect="postgres",
        emission_contract="contract.json",
    )
    template = query._template
    binding = bind_values(
        template,
        tuple((s, s.original.site.position.literal.value) for s in template.slots),
        named_values(template, parameters),
    )
    inputs = tuple(
        execution.R2SourceInput(
            s.namespace,
            s.name,
            "provider",
            "v1",
            "r1",
            s.namespace,
            "registry",
            "SELECT 1",
            ("id",),
            "pietto_query",
            "retained",
        )
        for s in binding.artifact.request.sources
    )
    return _prepare_refinement(
        binding.artifact,
        retained_requirements(binding.artifact, inputs),
        policy=TieRefinement(),
        output=None,
        binding=binding,
    )


def frontier(query):
    """A valid continuation frontier: 7, or the nearest bound, per coordinate."""
    from pietto._project.project_refinement_verification import _page_coordinates

    return tuple(
        max(int(d["min"]), min(int(d["max"]), 7))
        for d in (dict(c.domain) for c in _page_coordinates(query))
    )
