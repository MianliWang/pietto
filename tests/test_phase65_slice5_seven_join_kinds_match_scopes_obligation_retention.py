"""Real JOIN planning, contextual tails and exact obligation/proof retention."""

from pathlib import Path
from dataclasses import replace

import pytest

from pietto.ast_nodes import AuthoredJoinKind
from pietto._project import project_sql_plan_expressions as row
from pietto._project import project_sql_plan_joins as joining
from pietto._project.project_sql_plan import (
    ProjectSQLPlan,
    ProjectSQLPlanUnavailable,
    build_project_sql_plan,
)
from pietto._project.project_sql_plan_verification import verify_project_sql_plan
from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan
from pietto._project.project_completed_semantics import (
    with_project_single_match_requests,
)
from pietto._project.project_query_block_ir import build_project_query_block_ir
from pietto._project.project_query_block_ir_verification import (
    verify_project_query_block_ir,
    build_project_query_block_ir_analysis_bundle,
)
from pietto._project.project_single_match import (
    ProjectSingleMatchRequest,
    ProjectSingleMatchScope,
    ProjectSingleMatchState,
)
from test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan import _graft
from test_phase64_slice3_generic_on_condition_semantics_authority_separation import (
    _completed,
    _source as _upstream_source,
)
from test_phase64_slice5_cross_right_full_output_shapes_null_extension_property_transfer import (
    _unique_source,
)
from test_phase64_slice7_single_match_direction_unit_scoped_proof_obligation_warning_diagnostics import (
    _asymmetric_source,
)


def _source(
    kind="inner",
    predicate="lhs.id == r.id",
    *,
    family="postgres",
    owner="query",
    tail=None,
):
    source = (
        _upstream_source(None if kind == "cross" else predicate, kind=kind)
        .replace("postgres.table", family + ".table")
        .replace("query result:", owner + " result:")
    )
    if tail is not None:
        source = source.replace("    select:\n        id = lhs.id\n", tail)
    elif kind not in {"semi", "anti"}:
        source += "        right_id = r.id\n"
    return source


def _roots(path: Path, source: str, requests=None):
    completed = _completed(path, source)
    if requests is not None:
        completed = with_project_single_match_requests(completed, requests(completed))
    snapshot = build_project_query_block_ir(completed)
    checked = verify_project_query_block_ir(snapshot)
    assert checked.verified, checked.issues
    bundle = build_project_query_block_ir_analysis_bundle(checked)
    selected = tuple(o for o in snapshot.owners if o.definition.name == "result")
    assert len(selected) == 1
    return completed, bundle, selected[0]


def _product(path: Path, source: str, requests=None):
    roots = _roots(path, source, requests)
    assert roots[0].ok, roots[0].diagnostics
    plan = build_project_sql_plan(*roots)
    assert isinstance(plan, ProjectSQLPlan), getattr(plan, "blockers", ())
    checked = verify_project_sql_plan(plan, *roots)
    assert checked.verified, checked.issues
    return roots, plan, inspect_project_sql_plan(checked)


def _requests(completed):
    return tuple(
        ProjectSingleMatchRequest(owner=c.use.owner, use=c.use)
        for c in completed.roots.join_conditions.entries
    )


MATCHING = tuple(
    (kind, predicate)
    for kind in ("inner", "left", "right", "full", "semi", "anti")
    for predicate in ("true", "false", "lhs.id == r.id")
) + (("cross", None),)


@pytest.mark.parametrize(("kind", "predicate"), MATCHING)
@pytest.mark.parametrize("family", ("postgres", "mysql"))
@pytest.mark.parametrize("owner", ("table", "query"))
def test_seven_kind_matching_and_output_images(
    tmp_path: Path, kind, predicate, family, owner
):
    roots, plan, view = _product(
        tmp_path, _source(kind, predicate, family=family, owner=owner)
    )
    assert len(view.joins) == 1 and len(view.join_inputs) == 2
    join = view.joins[0]
    assert join.kind is AuthoredJoinKind(kind)
    assert len(join.outputs) == (3 if kind in ("semi", "anti") else 6)
    assert join.inputs == tuple(i.ref for i in view.join_inputs)
    assert all(
        i.producer is not None and i.predecessor is None for i in view.join_inputs
    )
    assert all(
        i.source is source
        for i, source in zip(view.join_inputs, join.source.inputs, strict=True)
    )
    before = view.match_context(join.ref).ports
    after = view.join_outputs(join.ref)
    assert len(before) == 6
    assert [p.field.effective_nullability.value for p in before][::3] == [
        "non_null",
        "non_null",
    ]
    expected = {
        "inner": ("non_null", "non_null"),
        "left": ("non_null", "nullable"),
        "cross": ("non_null", "non_null"),
        "right": ("nullable", "non_null"),
        "full": ("nullable", "nullable"),
        "semi": ("non_null",),
        "anti": ("non_null",),
    }[kind]
    assert tuple(p.field.effective_nullability.value for p in after)[::3] == expected
    assert all(
        p.field is field
        for p, field in zip(after, join.source.output.row_shape.fields, strict=True)
    )
    assert all(
        p.ref is not export.ref for p in view.join_ports for export in view.exports
    )
    if kind == "cross":
        assert join.on is None and join.site is None and not join.equalities
        assert join.rows is joining.ProjectSQLJoinRows.CARTESIAN_PAIRS
    else:
        assert join.site is not None and join.on is not None
        expression = view.expression(join.on)
        assert expression.expression is join.source.condition.expression
        assert expression.site is join.site
    for reference in (
        e for e in view.expressions if isinstance(e, row.ProjectSQLMatchReference)
    ):
        assert (
            view.match_context(join.ref).lookup(reference.symbol.ref).ref
            is reference.port
        )
    for port in after:
        with pytest.raises(ValueError, match="scope"):
            view.match_context(join.ref).lookup(port.ref)
    assert plan.diagnostics is roots[0].diagnostics


TAIL = """    let:
        first = lhs.id + 1
        second = first + r.id
    where lhs.allow_any and second > 0
    select:
        computed = second + first
        repeated = second
        again = second
        constant = 1
"""


@pytest.mark.parametrize("kind", ("inner", "left", "right", "full"))
def test_joined_tail_reuses_established_values_and_post_match_nullability(
    tmp_path: Path, kind: str
):
    _, _, view = _product(tmp_path, _source(kind, tail=TAIL))
    assert [block.kind.value for block in view.blocks] == [
        "let",
        "let",
        "where",
        "projection",
    ]
    assert len(view.let_values) == 2 and len(view.filters) == 1
    assert all(
        isinstance(value.site, row.ProjectSQLJoinedSite) for value in view.let_values
    )
    second = view.let_values[1]
    assert len([e for e in view.expressions if e.ref is second.expression]) == 1
    repeated = [view.expression(p.expression) for p in view.projections[1:3]]
    assert all(isinstance(e, row.ProjectSQLJoinedReference) for e in repeated)
    assert isinstance(repeated[0], row.ProjectSQLJoinedReference)
    assert isinstance(repeated[1], row.ProjectSQLJoinedReference)
    assert repeated[0].port is repeated[1].port
    assert view.exports[1].identity is not view.exports[2].identity
    for reference in (
        e for e in view.expressions if isinstance(e, row.ProjectSQLJoinedReference)
    ):
        assert (
            view.stage_context(reference.site.block).lookup(reference.symbol.ref).ref
            is reference.port
        )
    assert tuple(effect.retain_row for effect in view.filters[0].retention_effects) == (
        True,
        False,
        False,
    )


@pytest.mark.parametrize("kind", ("inner", "left", "right", "full", "semi", "anti"))
@pytest.mark.parametrize("refinement", (False, True))
def test_relationship_base_and_refinement_are_separate_from_where(
    tmp_path: Path, kind, refinement
):
    source = _unique_source(
        kind,
        "r.key > 0" if refinement else None,
        via="        via link: l -> r\n" if refinement else "",
    )
    source = source.replace("    select:", "    where lhs.id > 0\n    select:")
    roots, _, view = _product(tmp_path, source, _requests)
    join = view.joins[0]
    assert len(view.relationship_matches) == len(join.equalities) == 1
    assert (join.on is not None) is refinement
    assert len(view.filters) == 1
    assert view.filters[0].predicate is not join.on
    assert len(view.single_matches) == 1
    obligation = view.single_matches[0]
    assert obligation.assessment.state is ProjectSingleMatchState.PROVED
    assert (
        not obligation.downstream_enforcement_required and obligation.diagnostic is None
    )
    assert obligation.assessment is roots[0].single_matches.entries[0]
    assert obligation.source is roots[1].root.requirements[0]
    assert view.obligations_for_join(join.ref) == (obligation,)
    assert view.single_match_proofs


def _path_source(kind="inner", *, all_unique=False):
    source = _asymmetric_source(target_unique=True, source_unique=all_unique).replace(
        "inner join rhs as r:", kind + " join lhs as r:"
    )
    return source.replace(
        "        from lhs\n    select:",
        "        from lhs\n        via link: l -> r\n        via link: r -> l\n    select:",
    )


def _path_requests(completed):
    condition = completed.roots.join_conditions.entries[0]
    path = condition.effective_use.path
    assert path is not None
    request = ProjectSingleMatchRequest(
        owner=condition.use.owner, use=condition.use, path=path
    )
    return tuple(
        replace(request, scope=ProjectSingleMatchScope.PATH_HOP, hop=step)
        for step in path.steps
    ) + (replace(request, scope=ProjectSingleMatchScope.WHOLE_PATH),)


@pytest.mark.parametrize("kind", ("inner", "left"))
@pytest.mark.parametrize("all_unique", (False, True))
def test_multihop_scope_and_hidden_producer_closure(tmp_path: Path, kind, all_unique):
    roots, plan, view = _product(
        tmp_path, _path_source(kind, all_unique=all_unique), _path_requests
    )
    assert len(view.joins) == 2 and len(view.join_inputs) == 4
    assert len(view.definitions) == 3 and len(view.input_uses) == 2
    assert view.join_inputs[2].predecessor is view.joins[0].ref
    assert view.join_inputs[2].producer is None
    middle = view.join_inputs[1]
    assert middle.producer is not None and middle.binding_use is None
    producer = next(d for d in view.definitions if d.ref is middle.producer)
    assert producer.entry.owner.definition.name == "rhs"
    assert len(view.join_tails[0].fields) == 2 and len(view.joins[-1].outputs) == 3
    assert len(view.relationship_matches) == 2
    first, second = view.relationship_matches
    assert first.source is not second.source and first.guarantee is not second.guarantee
    assert len(view.single_matches) == 3
    assert [len(item.joins) for item in view.single_matches] == [1, 1, 2]
    whole = view.single_matches[-1]
    assert whole.request.scope is ProjectSingleMatchScope.WHOLE_PATH
    assert whole.assessment is roots[0].single_matches.entries[-1]
    assert whole.assessment.state is (
        ProjectSingleMatchState.PROVED
        if all_unique
        else ProjectSingleMatchState.LEGAL_UNPROVED
    )
    assert plan.diagnostics is roots[0].diagnostics


@pytest.mark.parametrize("kind", ("right", "full"))
def test_accumulated_left_has_all_previous_and_current_nulling(
    tmp_path: Path, kind: str
):
    source = _source("left").replace(
        "    select:",
        f"    {kind} join rhs as last:\n        from lhs\n        on r.id == last.id\n    select:",
    )
    _, _, view = _product(tmp_path, source)
    first, second = view.joins
    assert view.join_inputs[2].predecessor is first.ref
    before = view.match_context(second.ref).ports
    after = view.join_outputs(second.ref)
    assert len(after) == 9
    assert [len(p.nulling) for p in before[:6]] == [0, 0, 0, 1, 1, 1]
    assert [len(p.nulling) for p in after[:6]] == [1, 1, 1, 2, 2, 2]
    assert all(p.nulling[-1] is second.source.node.ref for p in after[:6])


def test_named_imported_joined_result_keeps_immediate_exports(tmp_path: Path):
    producer = _source("left", tail=TAIL).replace("query result:", "table joined:")
    (tmp_path / "producer.pietto").write_text(producer + "export:\n    table joined\n")
    (tmp_path / "facade.pietto").write_text(
        'import "producer.pietto":\n    table joined as Public\nexport:\n    table Public\n'
    )
    roots, _, view = _product(
        tmp_path,
        """import "facade.pietto":
    table Public as Input
query result:
    from Input
    let:
        final_value = computed + repeated
    where final_value > 0
    select:
        final = final_value
""",
    )
    assert len(view.joins) == 1 and len(view.filters) == 2
    use = next(use for use in view.input_uses if use.dependency.consumer is roots[2])
    producer_def = next(d for d in view.definitions if d.ref is use.producer)
    assert producer_def.entry.owner.definition.name == "joined"
    assert all(
        any(port.producer_port is export.ref for export in producer_def.exports)
        for port in use.ports
    )
    assert len(use.origin_path.hops) == 2
    assert all(source.module.path == "producer.pietto" for source in view.sources)


@pytest.fixture(scope="module")
def join_plans(tmp_path_factory: pytest.TempPathFactory):
    source = _source("left", tail=TAIL).replace(
        "    let:",
        "    full join rhs as last:\n        from lhs\n        on r.id == last.id\n    let:",
    )
    return tuple(
        _product(tmp_path_factory.mktemp("joined-plan"), source, _requests)
        for _ in range(2)
    )


@pytest.fixture(scope="module")
def proof_plans(tmp_path_factory: pytest.TempPathFactory):
    return tuple(
        _product(
            tmp_path_factory.mktemp("path-proof-plan"),
            _path_source(all_unique=True),
            _path_requests,
        )
        for _ in range(2)
    )


@pytest.mark.parametrize(
    "section",
    (
        "joins",
        "join_inputs",
        "join_ports",
        "relationship_matches",
        "join_tails",
        "single_matches",
        "single_match_proofs",
    ),
)
@pytest.mark.parametrize("change", ("empty", "omit", "duplicate", "reverse", "foreign"))
def test_every_join_inventory_is_complete(
    join_plans, proof_plans, section: str, change: str
):
    products = (
        proof_plans
        if section in {"relationship_matches", "single_match_proofs"}
        else join_plans
    )
    roots, plan, _ = products[0]
    foreign = products[1][1]
    values = getattr(plan, section)
    assert values
    altered = {
        "empty": (),
        "omit": values[1:],
        "duplicate": (*values, values[0]),
        "reverse": tuple(reversed(values)) if len(values) > 1 else (*values, values[0]),
        "foreign": getattr(foreign, section),
    }[change]
    candidate = _graft(plan, **{section: altered})
    assert not verify_project_sql_plan(candidate, *roots).verified, (section, change)
    checked = verify_project_sql_plan(plan, *roots)
    with pytest.raises(ValueError, match="VERIFIED"):
        inspect_project_sql_plan(_graft(checked, plan=candidate))


@pytest.mark.parametrize(
    "mutation",
    (
        "external_missing",
        "external_internal",
        "internal_missing",
        "internal_external",
        "wrong_input_source",
        "input_order",
        "input_bool",
        "join_kind",
        "join_rows",
        "join_source",
        "join_properties",
        "output_source",
        "output_field",
        "output_nulling",
        "output_old_nulling",
        "match_field",
        "match_post_image",
        "match_symbol",
        "match_scope",
        "site_evidence",
        "tail_field",
        "tail_port",
        "tail_join",
        "tail_source",
        "helper_visible",
        "request",
        "assessment",
        "warning",
        "enforcement",
        "obligation_pair",
        "obligation_boundary",
    ),
)
def test_exact_join_fields_and_scope_corruption(join_plans, mutation: str):
    roots, plan, _ = join_plans[0]
    foreign = join_plans[1][1]

    def changed(section, index, **fields):
        values = getattr(plan, section)
        return _graft(
            plan,
            **{
                section: (
                    *values[:index],
                    _graft(values[index], **fields),
                    *values[index + 1 :],
                )
            },
        )

    match_index = next(
        i
        for i, value in enumerate(plan.expressions)
        if isinstance(value, row.ProjectSQLMatchReference)
    )
    ref = plan.expressions[match_index]
    output_index = next(
        i
        for i, port in enumerate(plan.join_ports)
        if port.block is plan.joins[1].ref
        and port.kind is joining.ProjectSQLJoinPortKind.OUTPUT
        and len(port.nulling) == 2
    )
    post = plan.join_ports[output_index]
    post_symbol = next(symbol for symbol in plan.symbols if symbol.subject is post.ref)
    mutations = {
        "external_missing": lambda: changed("join_inputs", 0, producer=None),
        "external_internal": lambda: changed(
            "join_inputs", 0, producer=None, predecessor=plan.joins[0].ref
        ),
        "internal_missing": lambda: changed("join_inputs", 2, predecessor=None),
        "internal_external": lambda: changed(
            "join_inputs", 2, predecessor=None, producer=plan.join_inputs[0].producer
        ),
        "wrong_input_source": lambda: changed(
            "join_inputs", 0, source=foreign.join_inputs[0].source
        ),
        "input_order": lambda: changed(
            "joins", 0, inputs=tuple(reversed(plan.joins[0].inputs))
        ),
        "input_bool": lambda: changed("join_inputs", 0, ordinal=False),
        "join_kind": lambda: changed("joins", 0, kind=AuthoredJoinKind.INNER),
        "join_rows": lambda: changed(
            "joins", 0, rows=joining.ProjectSQLJoinRows.LEFT_EXISTS
        ),
        "join_source": lambda: changed("joins", 0, source=foreign.joins[0].source),
        "join_properties": lambda: changed(
            "joins", 0, properties=foreign.joins[0].properties
        ),
        "output_source": lambda: changed(
            "join_ports", output_index, source=plan.join_ports[0].ref
        ),
        "output_field": lambda: changed(
            "join_ports", output_index, field=replace(post.field)
        ),
        "output_nulling": lambda: changed("join_ports", output_index, nulling=()),
        "output_old_nulling": lambda: changed(
            "join_ports", output_index, nulling=post.original.nulling_joins
        ),
        "match_field": lambda: changed(
            "join_ports", 0, field=foreign.join_ports[0].field
        ),
        "match_post_image": lambda: changed(
            "expressions", match_index, port=post.ref, symbol=post_symbol
        ),
        "match_symbol": lambda: changed(
            "expressions", match_index, symbol=foreign.expressions[match_index].symbol
        ),
        "match_scope": lambda: changed(
            "expressions", match_index, site=plan.expression_sites[-1]
        ),
        "site_evidence": lambda: changed(
            "expression_sites", 0, evidence=foreign.expression_sites[0].evidence
        ),
        "tail_field": lambda: changed(
            "join_tails", 0, fields=tuple(reversed(plan.join_tails[0].fields))
        ),
        "tail_port": lambda: changed("join_tails", 0, ports=plan.joins[0].outputs),
        "tail_join": lambda: changed("join_tails", 0, join=plan.joins[0].ref),
        "tail_source": lambda: changed(
            "join_tails", 0, source=foreign.join_tails[0].source
        ),
        "helper_visible": lambda: _graft(plan, exports=(*plan.exports, post)),
        "request": lambda: changed(
            "single_matches", 0, request=foreign.single_matches[0].request
        ),
        "assessment": lambda: changed(
            "single_matches", 0, assessment=foreign.single_matches[0].assessment
        ),
        "warning": lambda: changed(
            "single_matches", 0, diagnostic=foreign.single_matches[0].diagnostic
        ),
        "enforcement": lambda: changed(
            "single_matches", 0, downstream_enforcement_required=False
        ),
        "obligation_pair": lambda: changed(
            "single_matches",
            0,
            input_pairs=(tuple(reversed(plan.single_matches[0].input_pairs[0])),),
        ),
        "obligation_boundary": lambda: changed(
            "single_matches", 0, joins=(plan.joins[1].ref,)
        ),
    }
    assert ref.site.role is row.ProjectSQLExpressionRole.MATCH
    assert not verify_project_sql_plan(mutations[mutation](), *roots).verified, mutation


@pytest.mark.parametrize(
    "mutation",
    (
        "equality_source",
        "equality_direction",
        "equality_left",
        "authored_order",
        "proof_source",
        "proof_parent",
        "proof_children",
        "proof_boundary",
        "proof_obligation",
    ),
)
def test_relationship_and_proof_images_are_not_replaceable(proof_plans, mutation: str):
    roots, plan, _ = proof_plans[0]
    foreign = proof_plans[1][1]

    def changed(section, index, **fields):
        values = getattr(plan, section)
        return _graft(
            plan,
            **{
                section: (
                    *values[:index],
                    _graft(values[index], **fields),
                    *values[index + 1 :],
                )
            },
        )

    parent_index = next(
        i for i, proof in enumerate(plan.single_match_proofs) if proof.children
    )
    equality = plan.relationship_matches[0]
    mutations = {
        "equality_source": lambda: changed(
            "relationship_matches", 0, source=foreign.relationship_matches[0].source
        ),
        "equality_direction": lambda: changed(
            "relationship_matches", 0, guarantee=plan.relationship_matches[1].guarantee
        ),
        "equality_left": lambda: changed(
            "relationship_matches", 0, left=equality.right
        ),
        "authored_order": lambda: changed(
            "relationship_matches",
            0,
            authored_operands=tuple(reversed(equality.authored_operands)),
        ),
        "proof_source": lambda: changed(
            "single_match_proofs", 0, source=foreign.single_match_proofs[0].source
        ),
        "proof_parent": lambda: changed(
            "single_match_proofs", 0, parent=plan.single_match_proofs[0].ref
        ),
        "proof_children": lambda: changed(
            "single_match_proofs", parent_index, children=()
        ),
        "proof_boundary": lambda: changed(
            "single_match_proofs", 0, joins=(plan.joins[1].ref,)
        ),
        "proof_obligation": lambda: changed(
            "single_match_proofs", 0, obligation=plan.single_matches[-1].ref
        ),
    }
    assert not verify_project_sql_plan(mutations[mutation](), *roots).verified, mutation


@pytest.mark.parametrize("kind", ("semi", "anti"))
@pytest.mark.parametrize("clause", ("select", "let", "where", "later_on"))
def test_membership_only_right_cannot_enter_later_value_scopes(
    tmp_path: Path, kind, clause
):
    tail = {
        "select": "    select:\n        id = r.id\n",
        "let": "    let:\n        forbidden = r.id\n    select:\n        id = lhs.id\n",
        "where": "    where r.id > 0\n    select:\n        id = lhs.id\n",
        "later_on": "    inner join rhs as later:\n        from lhs\n        on r.id == later.id\n    select:\n        id = lhs.id\n",
    }[clause]
    roots = _roots(tmp_path, _source(kind, tail=tail))
    assert not roots[0].ok, roots[0].diagnostics
    assert isinstance(build_project_sql_plan(*roots), ProjectSQLPlanUnavailable)


@pytest.mark.parametrize("reuse_identity", (False, True))
def test_repeated_requests_and_unrelated_warning_scopes(
    tmp_path: Path, reuse_identity: bool
):
    source = _source("semi", "true")
    source += "query unused:" + _source("inner", "true").split("query result:", 1)[1]

    def requests(completed):
        first, second = _requests(completed)
        return first, first if reuse_identity else replace(first), second

    roots, _, view = _product(tmp_path, source, requests)
    assert len(roots[0].diagnostics) == (2 if reuse_identity else 3)
    assert len(view.single_matches) == 2
    a, b = view.single_matches
    assert (a.request is b.request) is reuse_identity
    assert (a.assessment is b.assessment) is reuse_identity
    assert a.diagnostic is roots[0].single_matches.entries[0].diagnostic
    assert b.diagnostic is roots[0].single_matches.entries[1].diagnostic
    assert (a.diagnostic is b.diagnostic) is reuse_identity
    assert all(
        o.assessment.state is ProjectSingleMatchState.LEGAL_UNPROVED
        and o.downstream_enforcement_required
        for o in view.single_matches
    )


@pytest.mark.parametrize("invalid", ("cross", "unit", "owner"))
def test_invalid_single_match_blocks_the_project(tmp_path: Path, invalid: str):
    source = _source("cross" if invalid == "cross" else "inner", "true")

    def requests(completed):
        request = _requests(completed)[0]
        if invalid == "unit":
            return (replace(request, unit="distinct_values"),)
        if invalid == "owner":
            return (replace(request, owner=completed.effective_outputs.owners[0]),)
        return (request,)

    roots = _roots(tmp_path, source, requests)
    assert not roots[0].ok and any(d.code == "PIE-S2338" for d in roots[0].diagnostics)
    assert isinstance(build_project_sql_plan(*roots), ProjectSQLPlanUnavailable)


def test_right_limit_proof_does_not_enable_limit_planning(tmp_path: Path):
    from test_phase64_slice7_single_match_direction_unit_scoped_proof_obligation_warning_diagnostics import (
        _limited_source,
    )

    roots = _roots(tmp_path, _limited_source(right_limit=1), _requests)
    assert (
        roots[0].ok
        and roots[0].single_matches.entries[0].state is ProjectSingleMatchState.PROVED
    )
    result = build_project_sql_plan(*roots)
    assert isinstance(result, ProjectSQLPlanUnavailable)
    assert any(blocker.kind.value == "limit" for blocker in result.blockers)


def test_every_join_origin_and_demand_is_mandatory(proof_plans):
    roots, plan, _ = proof_plans[0]
    for section in ("origins", "demands"):
        values = getattr(plan, section)
        indexes = [
            i
            for i, value in enumerate(values)
            if isinstance(value, joining.ProjectSQLJoinDemand)
            or isinstance(
                getattr(value, "evidence", None),
                joining.ProjectSQLJoinWitness.__value__,
            )
        ]
        assert indexes
        for index in indexes:
            omitted = _graft(plan, **{section: (*values[:index], *values[index + 1 :])})
            assert not verify_project_sql_plan(omitted, *roots).verified, (
                section,
                index,
            )
            value = values[index]
            altered = (
                _graft(value, kind=joining.ProjectSQLJoinDemandKind.MATCH_INPUT)
                if section == "demands"
                and value.kind is not joining.ProjectSQLJoinDemandKind.MATCH_INPUT
                else _graft(value, subject=plan.sources[0].ref)
            )
            candidate = _graft(
                plan, **{section: (*values[:index], altered, *values[index + 1 :])}
            )
            assert not verify_project_sql_plan(candidate, *roots).verified


def test_no_semantic_or_proof_reconstruction_and_no_verifier_allocation(
    proof_plans, monkeypatch: pytest.MonkeyPatch
):
    from pietto._project import project_scalar_namespaces as namespaces
    from pietto._project import project_single_match as proof
    from pietto._project import project_join_conditions as conditions
    from pietto._project import project_query_block_ir as ir
    from pietto._project import project_sql_plan as planning

    roots, plan, _ = proof_plans[0]

    def forbidden(*args, **kwargs):
        raise AssertionError("Planning/verification cannot reconstruct authority")

    for module, names in (
        (
            namespaces,
            (
                "infer_row_expression",
                "resolve_project_joined_namespace_reference",
                "build_project_joined_let_namespaces",
                "analyze_project_joined_namespace_expression",
            ),
        ),
        (proof, ("_single_boundary_proofs", "_right_proofs")),
        (
            conditions,
            ("build_project_join_conditions", "rebuild_project_join_condition"),
        ),
        (ir, ("build_project_query_block_ir",)),
    ):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    fresh = build_project_sql_plan(*roots)
    assert isinstance(fresh, ProjectSQLPlan)
    for name in ("build_project_sql_plan", "build_project_sql_bindings", "_blockers"):
        monkeypatch.setattr(planning, name, forbidden)
    for cls in (
        joining.ProjectSQLJoin,
        joining.ProjectSQLJoinInput,
        joining.ProjectSQLJoinPort,
        joining.ProjectSQLSingleMatchProof,
        row.ProjectSQLMatchReference,
    ):
        monkeypatch.setattr(cls, "__init__", forbidden)
    checked = verify_project_sql_plan(plan, *roots)
    assert checked.verified, checked.issues
    view = inspect_project_sql_plan(checked)
    assert view.plan is plan and view.obligations_for_join(plan.joins[0].ref)


def test_self_join_same_field_evidence_keeps_distinct_occurrences(tmp_path: Path):
    _, _, view = _product(
        tmp_path,
        _source("inner", tail=TAIL).replace(
            "inner join rhs as r:", "inner join lhs as r:"
        ),
    )
    join = view.joins[0]
    assert view.join_inputs[0].producer is view.join_inputs[1].producer
    match_ports = view.match_context(join.ref).ports
    left, right = match_ports[0], match_ports[3]
    assert left.field is right.field
    assert left.ref is not right.ref and left.key is not right.key
    assert len(view.sources) == 1
    post = view.join_tails[0].fields
    assert post[0].evidence is post[3].evidence
    assert post[0] is not post[3]
    assert isinstance(post[0].source_field, joining.ProjectIRJoinedRowField)
    assert isinstance(post[3].source_field, joining.ProjectIRJoinedRowField)
    assert (
        post[0].source_field.introduction_use
        is not post[3].source_field.introduction_use
    )


def test_imported_joined_producer_can_feed_both_join_sides(tmp_path: Path):
    producer = _source("left").replace("query result:", "table joined:")
    (tmp_path / "producer.pietto").write_text(producer + "export:\n    table joined\n")
    _, _, view = _product(
        tmp_path,
        """import "producer.pietto":
    table joined as Input
query result:
    from Input
    inner join Input as other:
        from Input
        on Input.id == other.id
    where other.right_id is not null
    select:
        left_id = Input.id
        right_id = other.id
""",
    )
    assert len(view.joins) == 2
    left, right = view.join_inputs[-2:]
    assert (
        left.producer is right.producer
        and left.predecessor is right.predecessor is None
    )
    assert left.ports != right.ports
    definition = next(d for d in view.definitions if d.ref is left.producer)
    assert definition.entry.owner.definition.name == "joined"
    assert (
        left.source.use.output
        is right.source.use.output
        is definition.entry.active_output.occurrence
    )


@pytest.mark.parametrize("kind", ("right", "full", "semi", "anti", "cross"))
def test_unsupported_path_combinations_stay_semantic_errors(tmp_path: Path, kind: str):
    roots = _roots(tmp_path, _path_source(kind))
    assert not roots[0].ok
    assert isinstance(build_project_sql_plan(*roots), ProjectSQLPlanUnavailable)


@pytest.mark.parametrize("site", ("on", "select"))
def test_missing_call_evidence_is_a_planning_limitation_after_join(
    tmp_path: Path, site: str
):
    source = (
        _source("inner", 'len("x") > 0')
        if site == "on"
        else _source("inner", tail='    select:\n        label = trim("value")\n')
    )
    roots = _roots(tmp_path, source)
    assert roots[0].ok, roots[0].diagnostics
    plan = build_project_sql_plan(*roots)
    assert isinstance(plan, ProjectSQLPlanUnavailable)
    assert any(
        blocker.kind.value == "call_authority_unavailable" for blocker in plan.blockers
    )


@pytest.mark.parametrize(
    "mutation",
    (
        "let_ordinal",
        "prefix_ordinal",
        "on_ordinal",
        "match_field_ordinal",
        "select_ordinal",
    ),
)
def test_bool_ordinals_cannot_replace_join_context_metadata(join_plans, mutation: str):
    roots, plan, _ = join_plans[0]
    let = plan.let_values[0].site.evidence
    on = plan.joins[0].source.condition.references[0]
    targets = {
        "let_ordinal": (let.occurrence, "source_ordinal"),
        "prefix_ordinal": (let.namespace, "binding_ordinal"),
        "on_ordinal": (on, "position"),
        "match_field_ordinal": (on.environment.fields[0], "position"),
        "select_ordinal": (plan.projections[0].semantic, "selected_output_ordinal"),
    }
    target, field = targets[mutation]
    original = getattr(target, field)
    assert type(original) is int and original == 0
    checked = verify_project_sql_plan(plan, *roots)
    assert checked.verified
    object.__setattr__(target, field, False)
    try:
        assert isinstance(build_project_sql_plan(*roots), ProjectSQLPlanUnavailable)
        assert not verify_project_sql_plan(plan, *roots).verified
        with pytest.raises(ValueError, match="VERIFIED"):
            inspect_project_sql_plan(checked)
    finally:
        object.__setattr__(target, field, original)


@pytest.mark.parametrize("mutation", ("stage", "prefix", "reference_environment"))
def test_joined_post_namespace_must_be_its_actual_context(join_plans, mutation: str):
    from pietto._project.project_scalar_namespaces import ProjectScalarNamespaceStage

    roots, plan, _ = join_plans[0]
    site = plan.filters[0].site
    if mutation == "reference_environment":
        target = site.references[0].reference
        field = "environment"
        replacement = (
            join_plans[1][1].filters[0].site.references[0].reference.environment
        )
    else:
        target = site.namespace
        field = "stage" if mutation == "stage" else "let_values"
        replacement = (
            ProjectScalarNamespaceStage.POST_JOIN_INPUT if mutation == "stage" else ()
        )
    original = getattr(target, field)
    object.__setattr__(target, field, replacement)
    try:
        assert isinstance(build_project_sql_plan(*roots), ProjectSQLPlanUnavailable)
        assert not verify_project_sql_plan(plan, *roots).verified
    finally:
        object.__setattr__(target, field, original)


def test_right_global_proof_keeps_unsupported_producer_boundary(tmp_path: Path):
    from test_phase64_slice4_effective_output_join_first_generic_vertical_closure import (
        _tail_source,
    )

    source, _ = _tail_source("global")
    source += "query result:\n    from lhs\n    semi join upstream as r:\n        from lhs\n        on true\n    select:\n        id = lhs.id\n"

    def request(completed):
        return (_requests(completed)[-1],)

    roots = _roots(tmp_path, source, request)
    assert (
        roots[0].ok
        and roots[0].single_matches.entries[0].state is ProjectSingleMatchState.PROVED
    )
    result = build_project_sql_plan(*roots)
    assert isinstance(result, ProjectSQLPlanUnavailable)
    assert any(
        blocker.owner.definition.name == "upstream" for blocker in result.blockers
    )


@pytest.mark.parametrize("mutation", ("state", "candidates", "ready"))
def test_matching_authority_status_and_candidates_remain_coherent(
    join_plans, mutation: str
):
    from pietto._project.project_join_conditions import ProjectJoinReferenceState

    roots, plan, _ = join_plans[0]
    condition = plan.joins[0].source.condition
    reference = condition.references[0]
    target, field, replacement = {
        "state": (reference, "state", ProjectJoinReferenceState.UNKNOWN),
        "candidates": (reference, "candidates", ()),
        "ready": (condition, "ready", False),
    }[mutation]
    original = getattr(target, field)
    object.__setattr__(target, field, replacement)
    try:
        assert isinstance(build_project_sql_plan(*roots), ProjectSQLPlanUnavailable)
        assert not verify_project_sql_plan(plan, *roots).verified
    finally:
        object.__setattr__(target, field, original)
