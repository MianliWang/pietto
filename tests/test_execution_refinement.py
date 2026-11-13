"""Refined request/source-vector boundaries; database work is explicit elsewhere."""

from dataclasses import replace
from typing import cast

import pytest

from _pietto_sql_window import select_body
from _pietto_execution_refinement import (
    CLOCK,
    capabilities,
    frontier,
    live_refinement,
    now_project,
    refined,
)
from pietto._project.project_execution import PostgresAccess, ExecutionLimits
from pietto._project.project_refinement import TieRefinement, prepare_refinement
from pietto._project.project_refinement_enumeration import (
    prepare_refined_execution,
    verify_refined_execution,
)
from _pietto_execution_rows_cases import build


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_r2_bound_uses_its_dedicated_physical_int32_source(tmp_path, target):
    from _pietto_execution_source_assurance_cases import (
        R2_BOUND_MAX,
        R2_BOUND_RELATION,
        original,
    )
    from pietto._project.project_sql_emission_rows import field_realization

    artifact = original(tmp_path, target, "R2_bound", "range")
    assert artifact is not None
    source = artifact.request.sources[0]
    (field,) = source.fields[:1]
    realization = field_realization(field)
    assert source.name == R2_BOUND_RELATION
    assert realization is not None and realization.storage == {
        "kind": "pg_int4" if target == "postgres" else "my_int"
    }
    assert realization.domain == {
        "kind": "int_range",
        "min": "1",
        "max": str(R2_BOUND_MAX),
    }


def test_r2_bound_adbc_preserves_int32_source_and_int64_arithmetic(tmp_path):
    from _pietto_execution_source_assurance_cases import original
    from pietto._project.project_execution_reader import bind_native_output
    from pietto._project.project_execution_template import bind_values, prepare_template
    from pietto._project.project_result_binding import ProducerFieldBinding
    from pietto._project.project_result_output import prepare_output

    artifact = original(tmp_path, "postgres", "R2_bound", "range")
    template = prepare_template(artifact)
    binding = bind_values(template, tuple(zip(template.slots, (1, 2), strict=True)))
    output = prepare_output(binding.artifact, binding=binding)
    assert [column.realization.storage["kind"] for column in output.columns] == [
        "pg_int4",
        "pg_int8",
    ]
    producer = bind_native_output(
        output,
        "postgres_adbc",
        tuple(
            {
                "ordinal": column.ordinal,
                "name": column.label,
                "type": kind,
                "metadata": {},
                "nullable": False,
            }
            for column, kind in zip(output.columns, ("int32", "int64"), strict=True)
        ),
    )
    assert [
        cast(ProducerFieldBinding, field).observation.storage
        for field in producer.fields
    ] == [
        "pg_int4",
        "pg_int8",
    ]


def test_two_source_domains_need_complete_ordered_capabilities(tmp_path):
    artifact = build(tmp_path, "postgres", "S_set_forms", "intersect_all").artifact
    supplied = capabilities(artifact)
    assert len(supplied) == 2 and supplied[0].source is not supplied[1].source
    complete = prepare_refinement(artifact, supplied, policy=TieRefinement())
    assert complete.units[-1].rule == "set_intersect_all"
    for damaged in (
        supplied[::-1],
        supplied[:1],
        supplied + supplied[:1],
        (supplied[0], supplied[0]),
    ):
        with pytest.raises(ValueError):
            prepare_refinement(artifact, damaged, policy=TieRefinement())


def test_refined_request_cannot_borrow_an_equal_looking_original_root(tmp_path):
    a = refined(tmp_path / "a", "postgres", "G_emission_table_bag", "bag")
    b = refined(tmp_path / "b", "postgres", "G_emission_table_bag", "bag")
    access = PostgresAccess(
        "127.0.0.1", 5432, "test", "pietto_query", "not-a-live-secret", "disable"
    )
    request = prepare_refined_execution(a, access, limits=ExecutionLimits(batch_rows=2))
    verify_refined_execution(request)
    with pytest.raises(ValueError):
        verify_refined_execution(replace(request, refinement=b))
    with pytest.raises(ValueError):
        verify_refined_execution(
            replace(
                request,
                execution=replace(request.execution, source_requirement=a.sources[0]),
            )
        )
    # A query that reads no `now()` binds no statement time.
    with pytest.raises(ValueError, match="^REFINEMENT_STATEMENT_CLOCK$"):
        verify_refined_execution(replace(request, clock=CLOCK))
    assert (
        request.execution.artifact is a.original
        and request.execution.output is a.output
    )
    assert "not-a-live-secret" not in repr(request)


def test_current_pg_range_refusal_prevents_refined_original_authority(tmp_path):
    import _pietto_sql_emission as probe

    base = probe.fixture("postgres")
    source = base["source"].split("table result:", 1)[0] + select_body(
        "lead(id, 2147483648)"
    )
    _, result = probe.build_case(tmp_path, source, base["contract"])
    assert result.status == "BLOCKED" and result.artifact is None
    assert [b.detail for b in result.blockers] == [
        "postgres_window_structural_argument_out_of_int32_range"
    ]
    with pytest.raises((ValueError, AttributeError)):
        prepare_refinement(result.artifact, (), policy=TieRefinement())


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_source_generated_bound_values_keep_original_and_page_uses_separate(
    tmp_path, target
):
    from _pietto_execution_source_assurance_cases import original
    from pietto._project.project_execution_template import prepare_template, bind_values
    from pietto._project.project_refinement_verification import verify_native
    from pietto._project.project_refinement_rendering import render
    from pietto._project.project_refinement_verification import page_syntax

    seed = original(tmp_path, target, "R2_bound", "values")
    assert seed is not None
    template = prepare_template(seed)
    assert len(template.slots) == 2
    bindings = [
        bind_values(template, tuple(zip(template.slots, values, strict=True)))
        for values in ((0, 1), (1, 2))
    ]
    for binding in (bindings[0], bindings[1], bindings[0]):
        query = prepare_refinement(
            binding.artifact,
            capabilities(binding.artifact),
            policy=TieRefinement(),
            binding=binding,
        )
        statement, values = page_syntax(query, None, 2)
        native = render(statement, query.original, page_values=values)
        verify_native(native, query, frontier=None, size=2)
        assert {use.domain for use in native.uses} == {"original", "page"}
        assert query.output.binding is binding


NOW_READS = {
    "where": (
        "table snap:\n    from items\n    where stamp <= now()\n"
        "    select:\n        id\n",
        None,
    ),
    "two_reads": (
        "table snap:\n    from items\n    select:\n        id\n"
        "        seen = now()\n        again = now()\n",
        None,
    ),
    "comparison_item": (
        "table snap:\n    from items\n    select:\n        id\n"
        "        late = stamp <= now()\n",
        None,
    ),
    # Original parameters before and after the read keep their text order.
    "parameters": (
        "query snap(low: Int, high: Int):\n    from items\n"
        "    where id > low and stamp <= now() and id < high\n"
        "    select:\n        id\n",
        {"low": 1, "high": 9},
    ),
    "upstream": (
        "query a:\n    from items\n    select:\n        id\n        seen = now()\n"
        "table snap:\n    from a\n    select:\n        id\n        seen\n",
        None,
    ),
}


@pytest.mark.parametrize("shape", NOW_READS)
def test_r2_pages_bind_one_statement_clock_for_every_now_read(tmp_path, shape):
    """Every `now()` read of an R2 page is the one placeholder that binds the
    generation's statement time, on its first page and on a continuation."""
    from pietto._project.project_refinement_rendering import render
    from pietto._project.project_refinement_verification import (
        _placeholders,
        page_syntax,
        verify_native,
    )

    text, parameters = NOW_READS[shape]
    kind = "query" if parameters else "table"
    query = live_refinement(
        now_project(tmp_path / "project", text),
        "snap",
        kind=kind,
        parameters=parameters,
    )
    originals = len(query.original.parameter_uses)
    for start in (None, frontier(query)):
        statement, controls = page_syntax(query, start, 2)
        native = render(statement, query.original, controls, clock=CLOCK)
        index = originals + len(controls) + 1
        sql = native.sql.decode()
        clocks = [u for u in native.uses if u.domain == "clock"]
        assert "statement_timestamp" not in sql
        assert sql.count("CAST($" + str(index) + " AS pg_catalog.timestamp)") == len(
            clocks
        )
        assert clocks and {(u.index, u.owner, u.value) for u in clocks} == {
            (index, 0, CLOCK)
        }
        assert native.arguments[index - 1 :] == (CLOCK,)
        assert native.arguments.count(CLOCK) == 1
        assert len(_placeholders(statement)) == len(native.uses)
        verify_native(native, query, frontier=start, size=2, clock=CLOCK)
        with pytest.raises(ValueError, match="^REFINEMENT_PARAMETER_VALUE$"):
            verify_native(
                native, query, frontier=start, size=2, clock="2026-11-13 10:00:01.0"
            )
        with pytest.raises(ValueError, match="^REFINEMENT_STATEMENT_CLOCK$"):
            verify_native(native, query, frontier=start, size=2)
        with pytest.raises(ValueError, match="^REFINEMENT_STATEMENT_CLOCK$"):
            render(statement, query.original, controls)
        with pytest.raises(ValueError, match="^REFINEMENT_STATEMENT_CLOCK$"):
            render(statement, query.original, controls, _guards=object(), clock=CLOCK)


def test_a_statement_clock_needs_a_now_read_that_r2_reads(tmp_path):
    """A query without `now()` binds no statement time; a `now()` inside
    another call is SQL R2 does not read, refused as such, never an
    IndexError."""
    from pietto._project.project_refinement_rendering import render
    from pietto._project.project_refinement_verification import (
        page_syntax,
        verify_native,
    )

    project = now_project(
        tmp_path / "project",
        "table plain:\n    from items\n    select:\n        id\n"
        "table day:\n    from items\n    select:\n        id\n"
        "        day = date_of(now())\n",
    )
    plain = live_refinement(project, "plain")
    statement, controls = page_syntax(plain, None, 2)
    with pytest.raises(ValueError, match="^REFINEMENT_STATEMENT_CLOCK$"):
        render(statement, plain.original, controls, clock=CLOCK)
    native = render(statement, plain.original, controls)
    with pytest.raises(ValueError, match="^REFINEMENT_STATEMENT_CLOCK$"):
        verify_native(native, plain, size=2, clock=CLOCK)
    day = live_refinement(project, "day")
    statement, controls = page_syntax(day, None, 2)
    native = render(statement, day.original, controls, clock=CLOCK)
    with pytest.raises(ValueError, match="^REFINEMENT_NATIVE_SQL$"):
        verify_native(native, day, size=2, clock=CLOCK)


def test_each_now_read_charges_the_parameter_limit(tmp_path):
    """D70.07: each `now()` read of the largest page is one more placeholder
    within the contract's `parameters` limit."""
    import json

    from pietto._project.project_refinement_rendering import render
    from pietto._project.project_refinement_verification import page_syntax

    def prepared(directory, parameters=None):
        project = now_project(directory, NOW_READS["two_reads"][0])
        if parameters is not None:
            path = project / "contract.json"
            contract = json.loads(path.read_text(encoding="utf-8"))
            contract["environment"].append(
                {
                    "key": "resource_limits",
                    "scope": "statement",
                    "value": {"parameters": parameters},
                }
            )
            path.write_text(json.dumps(contract), encoding="utf-8")
        return live_refinement(project, "snap")

    query = prepared(tmp_path / "open")
    statement, controls = page_syntax(query, frontier(query), 2)
    largest = len(render(statement, query.original, controls, clock=CLOCK).uses)
    prepared(tmp_path / "fits", largest)
    with pytest.raises(ValueError, match="^REFINEMENT_RESOURCE_LIMIT$"):
        prepared(tmp_path / "exceeds", largest - 1)


@pytest.mark.parametrize(
    ("item", "refusal"),
    (("seen = now()", None), ("day = date_of(now())", "PUBLIC_R2_STATEMENT_SNAPSHOT")),
)
def test_a_compiled_refinement_policy_gets_the_same_now_check(tmp_path, item, refusal):
    """A live template whose compiled policy fixes its refinement is refused,
    last in R2 preparation, for a `now()` read whose SQL R2 does not read."""
    from _pietto_sql_emission import build_case, fixture
    from pietto._project.project_execution_template import (
        bind_values,
        prepare_live_template,
    )
    from pietto._project.project_refinement import (
        compiled_source_requirements,
        prepare_live_r2_refinement,
    )

    base = fixture("postgres")
    source = base["source"].split("table result:", 1)[0]
    source += "table result:\n    from rows\n    select:\n        id\n"
    _checked, result = build_case(
        tmp_path, source + "        " + item + "\n", base["contract"]
    )
    artifact = result.artifact
    refinement = prepare_refinement(
        artifact, capabilities(artifact), policy=TieRefinement()
    )
    template = prepare_live_template(artifact, refinement=refinement)
    binding = bind_values(
        template,
        tuple((s, s.original.site.position.literal.value) for s in template.slots),
    )
    requirements = compiled_source_requirements(binding.artifact)
    if refusal is None:
        # The policy branch issues no witness.
        assert prepare_live_r2_refinement(template, binding, requirements)[1] is None
    else:
        with pytest.raises(ValueError, match="^" + refusal + "$"):
            prepare_live_r2_refinement(template, binding, requirements)
