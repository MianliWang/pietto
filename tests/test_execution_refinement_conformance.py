"""Complete original-family denominator and independent refinement damages."""

from dataclasses import replace
import json

import pytest

from _pietto_execution_rows_cases import CASES, build
from _pietto_execution_refinement import capabilities, refined, rewrite_cte
from pietto._project.project_refinement import TieRefinement, prepare_refinement
from pietto._project.project_refinement_rendering import Expr, Select, render
from pietto._project.project_refinement_verification import (
    verify_native,
    verify_refinement,
)
from pietto._project.project_result_output import prepare_output, source_read_columns


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
    import _pietto_sql_emission as probe

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
    import _pietto_sql_emission as probe

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


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_the_largest_page_charges_the_parameter_limit(tmp_path, target):
    """D70.07: a continuation page binds one value per coordinate wherever its
    predicate reads it and its row count, beside the statement's own; R2
    preparation refuses a statement whose largest page exceeds `parameters`,
    before any page is requested."""
    import _pietto_sql_emission as probe
    from pietto._project.project_refinement_verification import page_syntax

    body = "query result:\n    from rows\n    where id > 5 and id < 9\n    select:\n"
    body += "        id\n"

    def prepared(directory, limits=None):
        item = probe.parameterized_fixture(
            target, body, "bind_safe_literals", limits=limits
        )
        _, outcome = probe.build_case(
            directory, item["source"], item["contract"], item["policy"]
        )
        assert outcome.status == "VERIFIED" and outcome.artifact is not None
        return prepare_refinement(
            outcome.artifact, capabilities(outcome.artifact), policy=TieRefinement()
        )

    query = prepared(tmp_path / "open")
    unit = query.units[-1]
    frontier = (0,) * (len(unit.order_coordinates) + len(unit.coordinates))
    statement, controls = page_syntax(query, frontier, 2)
    largest = len(render(statement, query.original, controls).uses)
    first, controls = page_syntax(query, None, 2)
    assert len(render(first, query.original, controls).uses) == 3 < largest == 12
    prepared(tmp_path / "fits", {"parameters": largest})
    with pytest.raises(ValueError, match="^REFINEMENT_RESOURCE_LIMIT$"):
        prepared(tmp_path / "exceeds", {"parameters": largest - 1})


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
    from _pietto_sql_emission import fixture, build_case

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


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("variant", ("semi", "anti"))
def test_a_tail_any_reads_its_refined_input_as_its_join_did(tmp_path, target, variant):
    """A `[not] any(...)` WHERE (what a last semi or anti JOIN migrates to) is
    the EXISTS of that JOIN's refinement: over the read relation's refined
    input under the read's own alias, with the unit depending on that input."""
    from pietto._project.project_refinement_rendering import Relation

    query = refined(tmp_path, target, "W_join_shapes", variant)
    (position,) = (
        i
        for i, c in enumerate(query.statement.ctes)
        if c.name == query.prefix + "unit0"
    )
    cte = query.statement.ctes[position]
    assert type(cte.query) is Select and type(cte.query.where) is Expr
    where = cte.query.where
    negated = variant == "anti"
    test = where.args[0] if negated else where
    assert (where.kind == "not") is negated and test.kind == "exists"
    (inner,) = test.args
    assert type(inner) is Select and type(inner.source) is Relation
    assert inner.source.name == (query.prefix + "source0",)
    assert query.units[0].dependencies == (-1, -1)
    (source,) = query.original.request.sources
    physical = replace(
        inner, source=Relation((source.namespace, source.name), inner.source.alias)
    )
    renamed = replace(inner, source=replace(inner.source, alias="other"))

    def wrapped(value):
        return Expr("not", (value,)) if negated else value

    for damage in (
        wrapped(Expr("exists", (physical,))),  # the table, not its refined input
        wrapped(Expr("exists", (renamed,))),  # not the read's own alias
        test if negated else Expr("not", (test,)),  # the negation dropped or added
    ):
        damaged = rewrite_cte(
            query, position, replace(cte, query=replace(cte.query, where=damage))
        )
        with pytest.raises(ValueError, match="^REFINEMENT_NATIVE_RULE_CORRESPONDENCE$"):
            verify_refinement(damaged)
    unit = replace(query.units[0], dependencies=(-1,))
    with pytest.raises(ValueError, match="^REFINEMENT_FACT_CORRESPONDENCE$"):
        verify_refinement(replace(query, units=(unit, *query.units[1:])))


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_a_tail_any_observes_the_source_columns_its_test_reads(tmp_path, target):
    import _pietto_sql_emission as probe

    def built(directory, body):
        item = probe.join_witness(target, "query result:\n    from lhs\n" + body)
        _, outcome = probe.build_case(
            directory, item["source"], item["contract"], item["policy"]
        )
        assert outcome.status == "VERIFIED" and outcome.artifact is not None
        return outcome.artifact

    artifact = built(
        tmp_path / "read",
        "    where any(r.key == lhs.id for r in rhs)\n    select:\n        a = lhs.id\n",
    )
    # `rhs` is read only inside `any`: its key column, as an ON would read it.
    assert source_read_columns(prepare_output(artifact))[1] == ("key value",)
    query = prepare_refinement(artifact, capabilities(artifact), policy=TieRefinement())
    (rhs,) = (c for c in query.statement.ctes if c.name == query.prefix + "source1")
    assert rhs.columns == ("key value", query.prefix + "k0", query.prefix + "k1")
    assert verify_native(render(query.statement, artifact), query) == ()
    for name, body in (
        ("or", "    where lhs.id > 1 or any(r.key == lhs.id for r in rhs)\n"),
        ("item", "    select:\n        f = any(r.key == lhs.id for r in rhs)\n"),
    ):
        if name == "or":
            body += "    select:\n        a = lhs.id\n"
        other = built(tmp_path / name, body)
        with pytest.raises(ValueError, match="^REFINEMENT_EXPRESSION_BLOCK_READ$"):
            prepare_refinement(other, capabilities(other), policy=TieRefinement())
