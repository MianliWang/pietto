"""Refined request/source-vector boundaries; database work is explicit elsewhere."""

from dataclasses import replace

import pytest

from test_phase68_slice6_refinement import capabilities, refined
from pietto._project.project_execution import PostgresAccess, ExecutionLimits
from pietto._project.project_refinement import TieRefinement, prepare_refinement
from pietto._project.project_refinement_enumeration import (
    prepare_refined_execution,
    verify_refined_execution,
)
from _pietto_phase68_slice5_cases import build


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
    assert (
        request.execution.artifact is a.original
        and request.execution.output is a.output
    )
    assert "not-a-live-secret" not in repr(request)


def test_current_pg_range_refusal_prevents_refined_original_authority(tmp_path):
    import _pietto_phase66_sql_emission_probe as probe
    from test_phase66_slice9_admitted_windows_named_frames_qualify_emission import (
        select_body,
    )

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
    from _pietto_phase68_slice6_cases import original
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
