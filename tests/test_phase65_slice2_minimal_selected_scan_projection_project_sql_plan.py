"""Real selected scan/projection planning and exact-root corruption controls."""

from pathlib import Path
from copy import copy
from dataclasses import replace

import pytest

from pietto.ast_nodes import LiteralExpr
from pietto.errors import Severity

from pietto._project.project_query_block_ir import build_project_query_block_ir
from pietto._project.project_query_block_ir_verification import (
    build_project_query_block_ir_analysis_bundle,
    verify_project_query_block_ir,
)
from test_phase64_slice3_generic_on_condition_semantics_authority_separation import (
    _completed,
)
from pietto._project.project_sql_plan import (
    ProjectSQLPlan,
    ProjectSQLPlanUnavailable,
    ProjectSQLPlanRefKind,
    ProjectSQLOriginRole,
    ProjectSQLSourceRealizationDemand,
    ProjectSQLExportRepresentationDemand,
    build_project_sql_plan,
    build_project_sql_bindings,
    ProjectSQLBindings,
)
from pietto._project.project_sql_plan_verification import verify_project_sql_plan
from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan


def _source(kind: str = "query", family: str = "postgres") -> str:
    return f"""shape Row:
    id: Int not null
    name: Text nullable
source rows: Row is {family}.table("public.users")
{kind} result:
    from rows
    select:
        label = name
        id
"""


def _roots(path: Path, source: str):
    completed = _completed(path, source)
    snapshot = build_project_query_block_ir(completed)
    verification = verify_project_query_block_ir(snapshot)
    assert verification.verified, verification.issues
    bundle = build_project_query_block_ir_analysis_bundle(verification)
    owners = tuple(o for o in snapshot.owners if o.definition.name == "result")
    assert len(owners) == 1
    return completed, bundle, owners[0]


@pytest.mark.parametrize("kind", ("table", "query"))
@pytest.mark.parametrize("family", ("postgres", "mysql"))
def test_real_minimal_vertical(tmp_path: Path, kind: str, family: str) -> None:
    completed, bundle, selected = _roots(tmp_path, _source(kind, family))
    assert completed.ok, completed.diagnostics
    plan = build_project_sql_plan(completed, bundle, selected)
    assert isinstance(plan, ProjectSQLPlan)
    checked = verify_project_sql_plan(plan, completed, bundle, selected)
    assert checked.verified, checked.issues
    view = inspect_project_sql_plan(checked)
    assert view.plan is plan
    assert view.selected_owner is selected
    assert len(view.sources) == len(view.blocks) == len(view.input_uses) == 1
    assert [p.identity.name for p in view.exports] == ["label", "id"]
    assert len(view.projections) == 2
    assert len(plan.bindings.demands) == 3
    assert len(view.demands) == 8
    assert view.origins
    source, block, use = view.sources[0], view.blocks[0], view.input_uses[0]
    assert [o.kind.value for o in block.operators] == [
        "relation_input",
        "final_projection",
    ]
    assert source.connector is source.declaration.connector
    locator = source.connector.arguments[0]
    assert isinstance(locator, LiteralExpr)
    assert locator.value == "public.users"
    assert source.module.path == source.declaration.span.path == "main.pietto"
    assert use.edge.use.output is source.source.active_output.occurrence
    assert use.producer is source.ref and use.consumer is block.definition
    assert use.dependency.target is source.source.owner
    assert plan.diagnostics is completed.diagnostics
    for i, projection in enumerate(view.projections):
        export = view.exports[i]
        assert projection.export is export.ref
        assert export.field is block.selected.active_properties.relational.fields[i]
        assert export.field.evidence is projection.semantic.field
        (input_port,) = (p for p in view.input_ports if p.ref is projection.input_port)
        assert (
            input_port.field.evidence is projection.semantic.references[0].input_field
        )
        assert export.identity is not input_port.identity
        demand = view.demands[i + 1]
        assert isinstance(demand, ProjectSQLExportRepresentationDemand)
        assert demand.logical_type is export.field.evidence.resolved_type
        assert demand.nullability is export.field.effective_nullability
        assert demand.subject is export.ref and demand.field is export.field
    assert isinstance(view.demands[0], ProjectSQLSourceRealizationDemand)
    assert view.demands[0].source is source


def _graft[T](value: T, /, **changes) -> T:
    result = copy(value)
    for name, changed in changes.items():
        object.__setattr__(result, name, changed)
    return result


@pytest.fixture(scope="module")
def plans(tmp_path_factory: pytest.TempPathFactory):
    roots = tuple(
        _roots(tmp_path_factory.mktemp("sql-plan"), _source()) for _ in range(2)
    )
    results = tuple(build_project_sql_plan(*r) for r in roots)
    assert all(isinstance(p, ProjectSQLPlan) for p in results)
    return roots, results


@pytest.mark.parametrize(
    "section",
    (
        "sources",
        "blocks",
        "input_uses",
        "source_ports",
        "input_ports",
        "exports",
        "projections",
        "origins",
        "demands",
    ),
)
@pytest.mark.parametrize("change", ("omit", "duplicate", "foreign", "reverse"))
def test_complete_inventory_mutations(plans, section: str, change: str) -> None:
    roots, (plan, foreign) = plans
    original = getattr(plan, section)
    changed = {
        "omit": original[1:],
        "duplicate": (*original, original[0]),
        "foreign": getattr(foreign, section),
        "reverse": tuple(reversed(original))
        if len(original) > 1
        else (*original, original[0]),
    }[change]
    candidate = _graft(plan, **{section: changed})
    checked = verify_project_sql_plan(candidate, *roots[0])
    assert not checked.verified, (section, change)
    with pytest.raises(ValueError, match="VERIFIED"):
        inspect_project_sql_plan(checked)


@pytest.mark.parametrize(
    "mutation",
    (
        "source_declaration",
        "source_connector",
        "source_module",
        "selected_entry",
        "foreign_edge",
        "missing_producer",
        "cycle",
        "wrong_port_owner",
        "source_as_final",
        "foreign_final_identity",
        "equal_final_identity",
        "source_field",
        "projection_evidence",
        "projection_source",
        "projection_input",
        "projection_export",
        "origin_role",
        "origin_cause",
        "origin_evidence",
        "origin_subject",
        "origin_antecedent",
        "demand_subject",
        "demand_type",
        "demand_nullability",
        "demand_origin",
        "demand_source",
        "ref_scope",
        "ref_kind",
        "ref_bool_position",
    ),
)
def test_coherent_looking_field_level_grafts(plans, mutation: str) -> None:
    roots, (plan, foreign) = plans
    sources, blocks, uses = plan.sources, plan.blocks, plan.input_uses
    exports, projections, origins, demands = (
        plan.exports,
        plan.projections,
        plan.origins,
        plan.demands,
    )
    assert isinstance(demands[1], ProjectSQLExportRepresentationDemand)
    assert isinstance(demands[2], ProjectSQLExportRepresentationDemand)
    changes = {
        "source_declaration": (
            "sources",
            (_graft(sources[0], declaration=foreign.sources[0].declaration),),
        ),
        "source_connector": (
            "sources",
            (_graft(sources[0], connector=foreign.sources[0].connector),),
        ),
        "source_module": (
            "sources",
            (_graft(sources[0], module=foreign.sources[0].module),),
        ),
        "selected_entry": (
            "blocks",
            (_graft(blocks[0], selected=foreign.blocks[0].selected),),
        ),
        "foreign_edge": (
            "input_uses",
            (_graft(uses[0], edge=foreign.input_uses[0].edge),),
        ),
        "missing_producer": ("input_uses", (_graft(uses[0], producer=None),)),
        "cycle": ("input_uses", (_graft(uses[0], producer=blocks[0].ref),)),
        "wrong_port_owner": (
            "exports",
            (_graft(exports[0], owner=sources[0].ref), exports[1]),
        ),
        "source_as_final": (
            "exports",
            (_graft(exports[0], identity=plan.source_ports[1].identity), exports[1]),
        ),
        "foreign_final_identity": (
            "exports",
            (_graft(exports[0], identity=foreign.exports[0].identity), exports[1]),
        ),
        "equal_final_identity": (
            "exports",
            (_graft(exports[0], identity=replace(exports[0].identity)), exports[1]),
        ),
        "source_field": (
            "exports",
            (_graft(exports[0], field=plan.source_ports[1].field), exports[1]),
        ),
        "projection_evidence": (
            "projections",
            (
                _graft(projections[0], semantic=foreign.projections[0].semantic),
                projections[1],
            ),
        ),
        "projection_source": (
            "projections",
            (
                _graft(projections[0], source_port=plan.source_ports[0].ref),
                projections[1],
            ),
        ),
        "projection_input": (
            "projections",
            (
                _graft(projections[0], input_port=plan.input_ports[0].ref),
                projections[1],
            ),
        ),
        "projection_export": (
            "projections",
            (_graft(projections[0], export=exports[1].ref), projections[1]),
        ),
        "origin_role": (
            "origins",
            (_graft(origins[0], role=ProjectSQLOriginRole.EXPORT), *origins[1:]),
        ),
        "origin_cause": (
            "origins",
            (_graft(origins[0], cause=foreign.origins[0].cause), *origins[1:]),
        ),
        "origin_evidence": (
            "origins",
            (_graft(origins[0], evidence=foreign.origins[0].evidence), *origins[1:]),
        ),
        "origin_subject": (
            "origins",
            (_graft(origins[0], subject=sources[0].ref), *origins[1:]),
        ),
        "origin_antecedent": (
            "origins",
            (*origins[:2], _graft(origins[2], antecedents=()), *origins[3:]),
        ),
        "demand_subject": (
            "demands",
            (demands[0], _graft(demands[1], subject=exports[1].ref), *demands[2:]),
        ),
        "demand_type": (
            "demands",
            (
                demands[0],
                _graft(demands[1], logical_type=replace(demands[1].logical_type)),
                *demands[2:],
            ),
        ),
        "demand_nullability": (
            "demands",
            (
                demands[0],
                _graft(demands[1], nullability=demands[2].nullability),
                *demands[2:],
            ),
        ),
        "demand_origin": (
            "demands",
            (_graft(demands[0], origin=origins[0].ref), *demands[1:]),
        ),
        "demand_source": (
            "demands",
            (_graft(demands[0], source=foreign.sources[0]), *demands[1:]),
        ),
        "ref_scope": (
            "exports",
            (
                _graft(exports[0], ref=_graft(exports[0].ref, scope=foreign.scope)),
                exports[1],
            ),
        ),
        "ref_kind": (
            "exports",
            (
                _graft(
                    exports[0],
                    ref=_graft(exports[0].ref, kind=ProjectSQLPlanRefKind.INPUT_PORT),
                ),
                exports[1],
            ),
        ),
        "ref_bool_position": (
            "exports",
            (
                _graft(exports[0], ref=_graft(exports[0].ref, position=False)),
                exports[1],
            ),
        ),
    }
    section, value = changes[mutation]
    checked = verify_project_sql_plan(_graft(plan, **{section: value}), *roots[0])
    assert not checked.verified, mutation
    with pytest.raises(ValueError, match="VERIFIED"):
        inspect_project_sql_plan(checked)


def test_root_and_selection_are_explicit_and_never_name_resolved(plans) -> None:
    roots, (plan, foreign) = plans
    completed, bundle, owner = roots[0]
    c2, b2, o2 = roots[1]
    for args in (
        (completed, b2, owner),
        (completed, bundle, o2),
        (completed, bundle, replace(owner)),
        (completed, bundle, bundle.root.owners[0]),
    ):
        with pytest.raises((TypeError, ValueError)):
            build_project_sql_plan(*args)
        assert not verify_project_sql_plan(plan, *args).verified
    # Only these calls deliberately violate the selected-owner argument type.
    with pytest.raises(ValueError, match="foreign or absent"):
        build_project_sql_plan(completed, bundle, "result")  # pyright: ignore[reportArgumentType]
    malformed = verify_project_sql_plan(plan, completed, bundle, "result")  # pyright: ignore[reportArgumentType]
    assert not malformed.verified
    assert not verify_project_sql_plan(plan, c2, b2, o2).verified
    fresh_bundle = build_project_query_block_ir_analysis_bundle(
        verify_project_query_block_ir(bundle.root)
    )
    assert not verify_project_sql_plan(plan, completed, fresh_bundle, owner).verified
    with pytest.raises(TypeError, match="closed"):
        ProjectSQLPlan()
    with pytest.raises(ValueError, match="actual blockers"):
        ProjectSQLPlanUnavailable(
            completed=completed, analysis_bundle=bundle, selected_owner=owner
        )
    view = inspect_project_sql_plan(verify_project_sql_plan(plan, *roots[0]))
    with pytest.raises(ValueError, match="belong"):
        view.projections_for_input(foreign.input_ports[0].ref)


SUPPORTED_BODIES = {
    "join": "    from rows\n    cross join other as r:\n        from rows\n    select:\n        id = rows.id\n",
    "where": "    from rows\n    where id > 0\n    select:\n        id\n",
    "let": "    from rows\n    let:\n        x = id\n    select:\n        id\n",
    "scalar": "    from rows\n    select:\n        x = id + 1\n",
    "group": "    from rows\n    group by:\n        id\n    select:\n        id\n        total = count(id)\n    satisfying:\n        total > 0\n",
    "global": "    from rows\n    select:\n        total = count(id)\n",
    "window": "    from rows\n    select:\n        id\n        ranked = row_number() window:\n            order by:\n                id\n    qualify:\n        ranked <= 3\n",
    "order": "    from rows\n    select:\n        id\n    order by:\n        id\n",
    "distinct": "    from rows\n    select distinct:\n        id\n    order by:\n        id\n    limit 2\n",
    "multiple": "    from rows\n    where id > 0\n    select:\n        a = id + 1\n        b = id + 2\n    order by:\n        id + 1\n    limit 2\n",
}

FUTURE_BODIES = {
    "set": "    union all:\n        from rows\n        from other\n",
    "multiple": "    union all:\n        from nested\n        from other\n",
}


@pytest.mark.parametrize(
    ("connector", "codes", "plannable"),
    [
        ('postgres.table("public.users")', (), True),
        ('mysql.table("app.users")', (), True),
        ('postgres.table("")', (), True),
        ('mysql.table("   ")', (), True),
        ('postgres.table("   ")', (), True),
        ('postgres.table(trim("users"))', (), False),
        ('mysql.table("")', ("PIE-S2306",), False),
        ("postgres.table(123)", ("PIE-S2306",), False),
        ('unknown.table("rows")', ("PIE-S2306",), False),
        ("postgres.table(missing)", ("PIE-S2102",), False),
    ],
)
def test_semantic_admission_precedes_static_plan_representation(
    tmp_path: Path, connector: str, codes: tuple[str, ...], plannable: bool
) -> None:
    source = _source().replace('postgres.table("public.users")', connector)
    roots = _roots(tmp_path, source)
    completed = roots[0]
    assert tuple(d.code for d in completed.diagnostics) == codes
    assert completed.ok is (not codes)
    result = build_project_sql_plan(*roots)
    if plannable:
        assert isinstance(result, ProjectSQLPlan)
        assert verify_project_sql_plan(result, *roots).verified
        literal = result.sources[0].connector.arguments[0]
        assert isinstance(literal, LiteralExpr)
        assert source.split(" is ", 1)[1].split("\n", 1)[0] == connector
        view = inspect_project_sql_plan(verify_project_sql_plan(result, *roots))
        assert view.sources[0].connector.arguments[0] is literal
    else:
        assert isinstance(result, ProjectSQLPlanUnavailable)
        if codes:
            assert all(d.severity is Severity.ERROR for d in completed.diagnostics)
            assert any(
                b.kind.value == "semantic_result_unsuccessful" for b in result.blockers
            )
        else:
            assert [b.kind.value for b in result.blockers] == [
                "static_source_unavailable"
            ]
        verification = verify_project_sql_plan(result, *roots)
        assert not verification.verified
        with pytest.raises(ValueError, match="VERIFIED"):
            inspect_project_sql_plan(verification)
    assert result.diagnostics is completed.diagnostics


@pytest.mark.parametrize("separate_module", (False, True))
def test_unrelated_invalid_source_prevents_selected_planning(
    tmp_path: Path, separate_module: bool
) -> None:
    invalid = (
        'shape Bad:\n    id: Int not null\nsource broken: Bad is mysql.table("")\n'
    )
    text = _source()
    if separate_module:
        (tmp_path / "bad.pietto").write_text(invalid)
    else:
        text += invalid
    roots = _roots(tmp_path, text)
    assert not roots[0].ok
    (error,) = roots[0].diagnostics
    assert error.code == "PIE-S2306" and error.severity is Severity.ERROR
    assert error.location.path == ("bad.pietto" if separate_module else "main.pietto")
    result = build_project_sql_plan(*roots)
    assert isinstance(result, ProjectSQLPlanUnavailable)
    assert result.diagnostics is roots[0].diagnostics
    assert [b.kind.value for b in result.blockers] == ["semantic_result_unsuccessful"]


@pytest.mark.parametrize("family", tuple(FUTURE_BODIES))
def test_every_future_family_is_a_typed_terminal(tmp_path: Path, family: str) -> None:
    base = (
        _source().split("query result:", 1)[0]
        + 'source other: Row is postgres.table("other")\n'
    )
    if family == "multiple":
        base += "table nested:\n" + FUTURE_BODIES["set"]
    roots = _roots(tmp_path, base + "query result:\n" + FUTURE_BODIES[family])
    assert roots[0].ok, roots[0].diagnostics
    result = build_project_sql_plan(*roots)
    assert isinstance(result, ProjectSQLPlanUnavailable)
    assert result.plan is None and result.blockers
    assert [b.position for b in result.blockers] == list(range(len(result.blockers)))
    if family == "multiple":
        assert [(b.owner.definition.name, b.kind.value) for b in result.blockers] == [
            ("nested", "set_operation"),
            ("result", "set_operation"),
        ]
    else:
        assert all(b.owner is roots[2] for b in result.blockers)
    checked = verify_project_sql_plan(result, *roots)
    assert not checked.verified
    with pytest.raises(ValueError, match="VERIFIED"):
        inspect_project_sql_plan(checked)


def test_selected_closure_distinguishes_unrelated_limitation_and_error(
    tmp_path: Path,
) -> None:
    for error in (False, True):
        # Unknown selected field gives a real ERROR in the unrelated declaration.
        source = (
            _source()
            + "query unrelated:\n"
            + (
                "    from rows\n    select:\n        nope\n"
                if error
                else "    union all:\n        from rows\n        from rows\n"
            )
        )
        roots = _roots(tmp_path / str(error), source)
        assert any(d.severity is Severity.ERROR for d in roots[0].diagnostics) is error
        result = build_project_sql_plan(*roots)
        assert roots[0].ok is not error
        assert result.diagnostics is roots[0].diagnostics
        if error:
            assert isinstance(result, ProjectSQLPlanUnavailable)
            assert [b.kind.value for b in result.blockers] == [
                "semantic_result_unsuccessful"
            ]
        else:
            assert isinstance(result, ProjectSQLPlan)
            assert verify_project_sql_plan(result, *roots).verified


def test_named_limited_producer_and_remaining_transitive_blockers(
    tmp_path: Path,
) -> None:
    source = _source().replace("query result:", "table upstream:")
    source += (
        "table filtered:\n    from upstream\n    select:\n        id\n    limit 2\n"
    )
    source += "query result:\n    from filtered\n    select:\n        id\n"
    roots = _roots(tmp_path, source)
    assert roots[0].ok, roots[0].diagnostics
    result = build_project_sql_plan(*roots)
    assert isinstance(result, ProjectSQLPlan)
    view = inspect_project_sql_plan(verify_project_sql_plan(result, *roots))
    assert len(view.limits) == 1 and view.limits[0].value == 2
    assert view.result_exports
    source = source.replace(
        "    from upstream\n    select:\n        id\n    limit 2\n",
        "    union all:\n        from upstream\n        from upstream\n",
    )
    roots = _roots(tmp_path / "set", source)
    assert roots[0].ok
    unavailable = build_project_sql_plan(*roots)
    assert isinstance(unavailable, ProjectSQLPlanUnavailable)
    assert [(b.owner.definition.name, b.kind.value) for b in unavailable.blockers] == [
        ("filtered", "set_operation")
    ]


def test_concrete_looking_terminal_cannot_bypass_supported_shape(
    plans, tmp_path: Path
) -> None:
    _, (plan, _) = plans
    roots = _roots(
        tmp_path,
        _source().split("query result:")[0]
        + "query result:\n"
        + "    union all:\n        from rows\n        from rows\n",
    )
    assert roots[0].ok, roots[0].diagnostics
    terminal = build_project_sql_plan(*roots)
    assert isinstance(terminal, ProjectSQLPlanUnavailable)
    bindings = build_project_sql_bindings(*roots)
    assert isinstance(bindings, ProjectSQLBindings)
    forged = _graft(plan, scope=bindings.scope, bindings=bindings)
    checked = verify_project_sql_plan(forged, *roots)
    assert [i.value for i in checked.issues] == ["unsupported_shape"]


def test_repeated_field_uses_and_unicode_origins(tmp_path: Path) -> None:
    source = (
        _source()
        .replace('"public.users"', '"public.😀\\nusers"')
        .replace("        id\n", "        again = name\n        id\n")
    )
    roots = _roots(tmp_path, source)
    assert roots[0].ok
    plan = build_project_sql_plan(*roots)
    assert isinstance(plan, ProjectSQLPlan)
    view = inspect_project_sql_plan(verify_project_sql_plan(plan, *roots))
    assert len(view.exports) == 3 and len(view.input_ports) == 2
    uses = view.projections_for_input(view.input_ports[1].ref)
    assert len(uses) == 2 and uses[0] is not uses[1]
    assert uses[0].export is not uses[1].export
    unicode_locator = view.sources[0].connector.arguments[0]
    assert isinstance(unicode_locator, LiteralExpr)
    assert unicode_locator.value == "public.😀\nusers"
    assert view.sources[0].connector.span is view.sources[0].declaration.connector.span
    for origin in view.origins:
        assert origin.cause.span.path == "main.pietto"


def test_verifier_and_inspection_never_call_construction(
    plans, monkeypatch: pytest.MonkeyPatch
) -> None:
    import pietto._project.project_sql_plan as planning
    import pietto._project.project_completed_semantics as semantics
    import pietto._project.project_query_block_ir as ir

    roots, (plan, _) = plans

    def forbidden(*args, **kwargs):
        raise AssertionError("construction must not run in a verifier or view")

    monkeypatch.setattr(planning, "build_project_sql_plan", forbidden)
    monkeypatch.setattr(planning, "_blockers", forbidden)
    monkeypatch.setattr(semantics, "build_project_completed_semantic_result", forbidden)
    monkeypatch.setattr(ir, "build_project_query_block_ir", forbidden)
    checked = verify_project_sql_plan(plan, *roots[0])
    assert checked.verified
    assert inspect_project_sql_plan(checked).plan is plan


def test_imported_source_has_current_positive_planning(tmp_path: Path) -> None:
    (tmp_path / "source.pietto").write_text(
        _source().split("query result:", 1)[0] + "export:\n    source rows\n"
    )
    roots = _roots(
        tmp_path,
        'import "source.pietto":\n    source rows\n'
        + "query result:\n    from rows\n    select:\n        id\n",
    )
    assert roots[0].ok, roots[0].diagnostics
    result = build_project_sql_plan(*roots)
    assert isinstance(result, ProjectSQLPlan)
    assert verify_project_sql_plan(result, *roots).verified
    assert result.sources[0].module.path == "source.pietto"
    assert len(result.input_uses[0].origin_path.hops) == 1


def test_inspection_rejects_a_grafted_positive_verification(plans) -> None:
    roots, (plan, foreign) = plans
    checked = verify_project_sql_plan(plan, *roots[0])
    assert checked.verified
    for candidate in (_graft(plan, demands=()), _graft(plan, sources=foreign.sources)):
        forged = _graft(checked, plan=candidate)
        with pytest.raises(ValueError, match="VERIFIED"):
            inspect_project_sql_plan(forged)


def test_completed_semantic_authority_cannot_be_replaced_inside_verified_roots(
    plans,
) -> None:
    roots, (plan, _) = plans
    completed, bundle, owner = roots[0]
    semantic = completed.semantic_result
    object.__setattr__(completed, "semantic_result", roots[1][0].semantic_result)
    try:
        with pytest.raises(ValueError, match="continuous"):
            build_project_sql_plan(completed, bundle, owner)
        assert not verify_project_sql_plan(plan, completed, bundle, owner).verified
    finally:
        object.__setattr__(completed, "semantic_result", semantic)


@pytest.mark.parametrize("family", tuple(SUPPORTED_BODIES))
def test_lifted_row_and_join_families_are_positive(tmp_path: Path, family: str) -> None:
    roots = _roots(
        tmp_path,
        _source().split("query result:", 1)[0]
        + 'source other: Row is postgres.table("other")\n'
        + "query result:\n"
        + SUPPORTED_BODIES[family],
    )
    assert roots[0].ok, roots[0].diagnostics
    result = build_project_sql_plan(*roots)
    assert isinstance(result, ProjectSQLPlan)
    checked = verify_project_sql_plan(result, *roots)
    assert checked.verified, checked.issues
    view = inspect_project_sql_plan(checked)
    assert bool(view.filters) is (family in {"where", "group", "window", "multiple"})
    assert bool(view.aggregations) is (family in {"group", "global"})
    assert bool(view.let_values) is (family == "let")
    assert bool(view.joins) is (family == "join")
    assert bool(view.windows) is (family == "window")
    assert view.expressions and view.exports
