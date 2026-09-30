"""Complete original-family denominator and independent refinement damages."""

from dataclasses import replace
import json

import pytest

from _pietto_phase68_slice5_cases import CASES, build
from pietto._project.project_execution_source import RetainedSourceRequirement
from pietto._project.project_refinement import TieRefinement, prepare_refinement
from pietto._project.project_refinement_rendering import Expr, Select, render
from pietto._project.project_refinement_verification import (
    verify_native,
    verify_refinement,
)
from pietto._project.project_result_output import prepare_output, source_read_columns


def capabilities(artifact, *, width=1):
    return tuple(
        RetainedSourceRequirement(
            s,
            "explicit-fixture-provider",
            "v1",
            "r1",
            s.namespace,
            "registry",
            "explicit fixture view definition",
            tuple("key" + str(i) for i in range(width)),
            "pietto_query",
            "Fixture declaration only; fresh native admission is separate.",
        )
        for s in artifact.request.sources
    )


def refined(directory, target, case, variant):
    artifact = build(directory, target, case, variant).artifact
    return prepare_refinement(artifact, capabilities(artifact), policy=TieRefinement())


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("case,variant", CASES)
def test_complete_admitted_family_correspondence(tmp_path, target, case, variant):
    outcome = build(tmp_path, target, case, variant)
    if outcome.status == "BLOCKED":
        assert target == "mysql" and (case, variant) in (
            ("V_join_full", "null_keys"),
            ("A_window_groups", "exclude"),
        )
        return
    artifact = outcome.artifact
    assert artifact is not None
    original_sql = artifact.rendered.sql
    query = prepare_refinement(artifact, capabilities(artifact), policy=TieRefinement())
    assert verify_refinement(query) is query.units[-1]
    native = render(query.statement, artifact)
    assert verify_native(native, query) == ()
    assert artifact.rendered.sql is original_sql
    assert tuple(c for _, c in query.erasure) == query.output.columns
    assert all(
        u.original is o for u, o in zip(query.units, query.output.units, strict=True)
    )
    assert tuple(r.source for r in query.sources) == artifact.request.sources


def rewrite_cte(query, position, replacement):
    old = query.statement.ctes[position]
    ctes = tuple(replacement if c is old else c for c in query.statement.ctes)
    units = tuple(
        replace(u, ctes=tuple(replacement if c is old else c for c in u.ctes))
        for u in query.units
    )
    return replace(query, statement=replace(query.statement, ctes=ctes), units=units)


def test_coordinated_native_key_and_witness_damage(tmp_path, monkeypatch):
    query = refined(tmp_path, "postgres", "G_emission_table_bag", "bag")
    first = query.statement.ctes[0]
    assert type(first.query) is Select
    columns = list(first.query.columns)
    name, expression = columns[-1]
    columns[-1] = (name, Expr("cast_integer", (Expr("integer", (9,)),)))
    damaged = rewrite_cte(
        query, 0, replace(first, query=replace(first.query, columns=tuple(columns)))
    )
    # A matching rendered statement and matching witness list do not certify it.
    render(damaged.statement, damaged.original)
    with pytest.raises(ValueError, match="REFINEMENT_NATIVE_RULE_CORRESPONDENCE"):
        verify_refinement(damaged)
    for changed in (
        replace(query, erasure=query.erasure[:-1]),
        replace(query, erasure=query.erasure[::-1]),
        replace(query, sources=()),
        replace(query, units=query.units[::-1] + query.units[:1]),
        replace(query, policy=TieRefinement("caller-chosen-late-policy")),
    ):
        with pytest.raises(ValueError):
            verify_refinement(changed)
    import pietto._project.project_refinement_lowering as builder
    import pietto._project.project_refinement_rendering as renderer

    def forbidden(*args, **kwargs):
        raise AssertionError("verifier called a constructor")

    monkeypatch.setattr(builder, "lower", forbidden)
    monkeypatch.setattr(renderer, "render", forbidden)
    assert verify_refinement(query) is query.units[-1]


def test_actual_native_bytes_and_parameter_occurrences_are_checked(tmp_path):
    query = refined(tmp_path, "mysql", "T_row_direct", "query_bind")
    native = render(query.statement, query.original)
    verify_native(native, query)
    assert native.uses and len(native.uses) == len(native.arguments)
    assert tuple(u.index for u in native.uses) == tuple(range(1, len(native.uses) + 1))
    assert all(u.original is not None for u in native.uses)
    damages = (
        replace(native, sql=native.sql + b"; SELECT 1"),
        replace(native, uses=native.uses[:-1]),
        replace(native, arguments=native.arguments[:-1]),
        replace(
            native, uses=(replace(native.uses[0], original=None), *native.uses[1:])
        ),
        replace(native, uses=(replace(native.uses[0], index=True), *native.uses[1:])),
    )
    for damaged in damages:
        with pytest.raises(ValueError):
            verify_native(damaged, query)


def test_source_read_observation_does_not_require_unused_columns(tmp_path):
    import _pietto_phase66_sql_emission_probe as probe

    item = probe.fixture("postgres")
    header = item["source"].split("table result:", 1)[0]
    _, outcome = probe.build_case(
        tmp_path,
        header + "table result:\n    from rows\n    select:\n        id\n",
        item["contract"],
    )
    assert outcome.status == "VERIFIED"
    output = prepare_output(outcome.artifact)
    read = output.columns[0].source_field.column
    assert source_read_columns(output) == ((read,),)
    query = prepare_refinement(
        outcome.artifact, capabilities(outcome.artifact), policy=TieRefinement()
    )
    assert len(query.statement.ctes[0].columns) == 3


def test_internal_columns_charge_the_existing_resource_limit(tmp_path):
    import _pietto_phase66_sql_emission_probe as probe

    item = probe.fixture("postgres", "G_emission_table_bag", "bag")
    contract = json.loads(item["contract"])
    contract["environment"].append(
        {"key": "resource_limits", "scope": "statement", "value": {"columns": 6}}
    )
    _, outcome = probe.build_case(tmp_path, item["source"], json.dumps(contract))
    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    original = outcome.artifact.rendered.sql
    with pytest.raises(ValueError, match="REFINEMENT_RESOURCE_LIMIT"):
        prepare_refinement(
            outcome.artifact, capabilities(outcome.artifact), policy=TieRefinement()
        )
    assert outcome.artifact.rendered.sql is original


def test_mysql_nullable_join_input_retains_bijective_materialization(tmp_path):
    query = refined(tmp_path, "mysql", "W_join_values", "left_marker")
    positions = [i for i, c in enumerate(query.statement.ctes) if "nullable" in c.name]
    assert positions
    for position in positions:
        cte = query.statement.ctes[position]
        assert isinstance(cte.query, Select) and cte.query.distinct
        damaged = rewrite_cte(
            query, position, replace(cte, query=replace(cte.query, distinct=False))
        )
        with pytest.raises(ValueError):
            verify_refinement(damaged)


def test_mysql_internal_case_collision_preserves_exact_public_columns(tmp_path):
    query = refined(tmp_path, "mysql", "O_named_later", "two_facades")
    assert [c.label for c in query.output.columns][1:3] == ["Key", "key"]
    assert [n for n, _ in query.statement.query.columns][1:3] == ["Key", "key"]
    assert all(
        len({n.casefold() for n in c.columns}) == len(c.columns)
        for c in query.statement.ctes
    )
    assert query.units[-1].public_names[1:3] == (
        query.prefix + "v1",
        query.prefix + "v2",
    )
    old = query.units[-1]
    with pytest.raises(ValueError):
        verify_refinement(
            replace(
                query,
                units=query.units[:-1]
                + (
                    replace(
                        old, public_names=tuple(c.label for c in query.output.columns)
                    ),
                ),
            )
        )


def test_mysql_internal_prefix_avoids_case_folded_physical_names(tmp_path):
    from _pietto_phase66_sql_emission_probe import fixture, build_case

    base = fixture("mysql")
    assert "order.id" in base["contract"]
    _, result = build_case(
        tmp_path, base["source"], base["contract"].replace("order.id", "__PIETTO_R2_k0")
    )
    assert result.artifact is not None
    query = prepare_refinement(
        result.artifact, capabilities(result.artifact), policy=TieRefinement()
    )
    assert query.prefix == "__pietto_r2_1_"
    verify_refinement(query)
