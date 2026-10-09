"""Original match BAG/scope and independently verified native guard programs."""

from dataclasses import replace

import pytest

from _pietto_phase68_slice7_cases import DIRECT, planned, manifest, case_preparation
from pietto._project.project_guard_preparation import prepare_guarded
from pietto._project.project_guard_program import prepare_program, statement_for
from pietto._project.project_guard_rendering import render_guard
from pietto._project.project_guard_verification import (
    verify_program,
    verify_native_guard,
)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("kind", ("guard", "combined", "data"))
def test_complete_original_subjects_and_native_parameter_domains(
    tmp_path, target, kind
):
    body = DIRECT.replace(
        "on lhs.id == r.id", "on lhs.id == r.id and lhs.id > 1 and r.key > 1"
    )
    preparation = prepare_guarded(
        *planned(tmp_path, target, body, copies=2, policy="bind_safe_literals")
    )
    program = prepare_program(preparation)
    assert len(program.subjects) == 2
    assert program.subjects[0].unit is program.subjects[1].unit
    native = render_guard(statement_for(program, kind))
    verify_native_guard(native)
    original_owners = {id(u.owner) for u in native.uses if u.domain == "original"}
    assert len(original_owners) == 2
    if kind != "data":
        assert len({id(u.owner) for u in native.uses if u.domain == "guard"}) == 2
        assert all(u.value == 1 for u in native.uses)
    if target == "mysql":
        assert [u.index for u in native.uses] == list(range(1, len(native.uses) + 1))
    else:
        assert len(native.arguments) == (2 if kind == "data" else 4)
    for changed, code in (
        (replace(native, sql=native.sql + b"; SELECT 1"), "NATIVE_COVERAGE"),
        (replace(native, arguments=native.arguments[:-1]), "NATIVE_ARGUMENTS"),
        (replace(native, uses=native.uses[::-1]), "PARAMETER_CORRESPONDENCE"),
    ):
        with pytest.raises(ValueError, match="^GUARD_%s$" % code):
            verify_native_guard(changed)


def test_complete_request_boundary_rejects_coordinated_scope_damage(tmp_path):
    program = prepare_program(prepare_guarded(*planned(tmp_path, copies=2)))
    for changed, code in (
        (replace(program, subjects=program.subjects[:1]), "DENOMINATOR"),
        (replace(program, subjects=program.subjects[::-1]), "IDENTITY"),
        (
            replace(
                program,
                subjects=(
                    replace(
                        program.subjects[0], inputs=program.subjects[0].inputs[::-1]
                    ),
                    program.subjects[1],
                ),
            ),
            "IDENTITY",
        ),
    ):
        with pytest.raises(ValueError, match="^GUARD_SUBJECT_%s$" % code):
            verify_program(changed)
    with pytest.raises(ValueError, match="^GUARD_SELECTED_SUBJECT_COVERAGE$"):
        render_guard(statement_for(program, "combined", subjects=program.subjects[:1]))


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_shared_status_channel_preserves_case_distinct_public_labels(tmp_path, target):
    body = DIRECT.replace("left_id =", "Key =").replace("right_key =", "key =")
    program = prepare_program(prepare_guarded(*planned(tmp_path, target, body)))
    native = render_guard(statement_for(program, "combined"))
    verify_native_guard(native)
    assert [c.label for c in program.output.columns] == ["Key", "key"]
    assert program.refinement is None


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_refined_guards_keep_whole_subject_and_distinct_control_domain(
    tmp_path, target, monkeypatch
):
    from pietto._project.project_guard_preparation import prepare_guarded_output
    from pietto._project.project_refinement import prepare_refinement, TieRefinement
    from test_phase68_slice6_refinement import capabilities
    from pietto._project import project_guard_lowering as lowering
    from pietto._project import project_guard_rendering as rendering

    prepared = prepare_guarded(*planned(tmp_path, target))
    output = prepare_guarded_output(prepared)
    refined = prepare_refinement(
        prepared.artifact,
        capabilities(prepared.artifact),
        policy=TieRefinement(),
        output=output,
    )
    program = prepare_program(prepared, refinement=refined)
    native = render_guard(statement_for(program, "guard"))
    verify_native_guard(native)
    assert tuple(u.domain for u in native.uses) == ("guard", "guard")
    assert native.arguments == (1, 1)
    assert b"__pietto_r2_source0" in native.sql
    assert b"__pietto_r2_source1" in native.sql

    def forbidden(*args, **kwargs):
        raise AssertionError("independent checker called guard constructor")

    monkeypatch.setattr(lowering, "refined_guard_syntax", forbidden)
    monkeypatch.setattr(rendering, "render_guard", forbidden)
    verify_native_guard(native)
    for damaged, code in (
        (replace(native, sql=native.sql + b" "), "NATIVE_COVERAGE"),
        (replace(native, arguments=(1, 0)), "NATIVE_ARGUMENTS"),
        (replace(native, uses=native.uses[::-1]), "PARAMETER_CORRESPONDENCE"),
    ):
        with pytest.raises(ValueError, match="^GUARD_%s$" % code):
            verify_native_guard(damaged)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("case", manifest(), ids=lambda case: case["name"])
def test_every_campaign_fixture_has_complete_original_contract_and_guard(
    tmp_path, target, case
):
    if target == "mysql" and case["options"].get("postgres_only"):
        # The original target boundary remains a refusal, not a new skip.
        with pytest.raises(ValueError, match="^GUARD_PREPARATION_BLOCKED$"):
            case_preparation(tmp_path, target, case)
        return
    from pietto._project.project_guard_preparation import GuardPreparationError

    try:
        preparation = case_preparation(tmp_path, target, case)
    except GuardPreparationError as error:
        pytest.fail(
            str(error)
            + ": "
            + ", ".join(b.code + "/" + b.detail for b in error.blockers),
            pytrace=False,
        )
    program = prepare_program(preparation)
    assert len(program.subjects) == len(case["states"])
    from pietto._project.project_guard_program import pure_static_proofs

    for subject, state in zip(program.subjects, case["states"], strict=True):
        assert bool(pure_static_proofs(program, subject)) is (state == "STATIC")
    dynamic = tuple(s for s in program.subjects if not pure_static_proofs(program, s))
    native = render_guard(statement_for(program, "combined" if dynamic else "data"))
    verify_native_guard(native)
    assert native.statement.subjects == dynamic
    if case["options"].get("refined"):
        from pietto._project.project_guard_preparation import prepare_guarded_output
        from pietto._project.project_refinement import prepare_refinement, TieRefinement
        from test_phase68_slice6_refinement import capabilities

        query = prepare_refinement(
            preparation.artifact,
            capabilities(preparation.artifact),
            policy=TieRefinement(),
            output=prepare_guarded_output(preparation),
        )
        refined_program = prepare_program(preparation, refinement=query)
        verify_native_guard(render_guard(statement_for(refined_program, "guard")))


def test_multi_hop_checker_rejects_complete_coordinated_grafts_without_builder(
    tmp_path, monkeypatch
):
    from _pietto_phase68_slice7_cases import PATH
    from pietto._project.project_guard_preparation import verify_preparation
    from pietto._project import project_guard_program as program_builder

    a = prepare_program(
        prepare_guarded(*planned(tmp_path / "a", body=PATH, link=True, scope="whole"))
    )
    b = prepare_program(
        prepare_guarded(*planned(tmp_path / "b", body=PATH, link=True, scope="whole"))
    )
    native = render_guard(statement_for(a, "combined"))
    assert len(a.subjects) == 2
    damages = (
        replace(a, subjects=a.subjects[:1]),
        replace(a, subjects=a.subjects + a.subjects[:1]),
        replace(a, subjects=a.subjects[::-1]),
        replace(
            a,
            subjects=(
                replace(a.subjects[0], inputs=a.subjects[0].inputs[::-1]),
                a.subjects[1],
            ),
        ),
        replace(a, subjects=(b.subjects[0], a.subjects[1])),
        replace(
            a, subjects=(replace(a.subjects[0], unit=a.subjects[1].unit), a.subjects[1])
        ),
    )
    codes = ("DENOMINATOR", "DENOMINATOR", *("IDENTITY",) * 4)
    for damage, code in zip(damages, codes, strict=True):
        with pytest.raises(ValueError, match="^GUARD_SUBJECT_%s$" % code):
            verify_program(damage)
    unit = a.subjects[0].unit
    altered = replace(
        unit,
        inputs=(
            replace(unit.inputs[0], original=b.subjects[0].inputs[0].original),
            unit.inputs[1],
        ),
    )
    artifact = a.preparation.artifact
    from pietto._project.project_sql_emission_ast import SQLJoinQuery

    assert type(artifact.ast) is SQLJoinQuery
    broken = replace(
        artifact,
        ast=replace(
            artifact.ast,
            units=tuple(altered if u is unit else u for u in artifact.ast.units),
        ),
    )
    with pytest.raises(ValueError, match="^GUARD_PREPARATION_STRUCTURE$"):
        verify_preparation(replace(a.preparation, artifact=broken))

    def forbidden(*args, **kwargs):
        raise AssertionError("independent verifier called JOIN builder")

    import pietto._project.project_guard_lowering as guard_builder

    monkeypatch.setattr(guard_builder, "original_fragments", forbidden)
    verify_native_guard(native)
    monkeypatch.setattr(
        program_builder, "pure_static_proofs", lambda *args: (object(),)
    )
    with pytest.raises(ValueError, match="^GUARD_SELECTED_SUBJECT_COVERAGE$"):
        render_guard(statement_for(a, "data"))
