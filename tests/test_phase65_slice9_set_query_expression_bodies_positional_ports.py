"""Normal-source SET body, terminal-port and positional membership verification."""

from pathlib import Path

import pytest

from pietto.ast_nodes import SetRelationDef
from pietto._project.project_query_block_ir import ProjectIRCompletedSetOperationOutput
from pietto._project.project_sql_plan import (
    ProjectSQLPlan,
    ProjectSQLPlanUnavailable,
    build_project_sql_plan,
)
from pietto._project.project_sql_plan_verification import verify_project_sql_plan
from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan
from pietto._project import project_sql_plan_sets as sets
from pietto._project import project_sql_plan_results as results
from test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan import (
    _roots,
    _graft,
)
from test_phase64_slice9_set_operations_explicit_all_distinct_output_identity import (
    _source,
    OPERATIONS,
)


def _product(path: Path, source: str):
    roots = _roots(path, source)
    assert roots[0].ok, roots[0].diagnostics
    plan = build_project_sql_plan(*roots)
    assert isinstance(plan, ProjectSQLPlan), getattr(plan, "blockers", ())
    checked = verify_project_sql_plan(plan, *roots)
    assert checked.verified, checked.issues
    return roots, plan, inspect_project_sql_plan(checked)


@pytest.mark.parametrize("kind,quantifier", OPERATIONS)
@pytest.mark.parametrize("owner_kind", ["table", "query"])
def test_six_direct_nonselect_bodies_have_real_positional_ports(
    tmp_path, kind, quantifier, owner_kind
):
    source = _source(kind, quantifier, replay=False).replace(
        "table combined:", f"{owner_kind} result:"
    )
    roots, plan, view = _product(tmp_path, source)
    (body,) = view.set_bodies
    assert not plan.blocks and not plan.projections and not plan.distincts
    assert isinstance(roots[2].definition, SetRelationDef)
    assert isinstance(body.source, ProjectIRCompletedSetOperationOutput)
    assert body.operation is body.source.semantic_entry.root
    assert body.multiplicity.value == f"{kind}_{quantifier}"
    assert body.requires_equivalence is ((kind, quantifier) != ("union", "all"))
    assert body.full_row_unique is (quantifier == "distinct")
    assert body.fold == "source_order_left_fold"
    assert view.result_stages(body.definition) == (body,)
    assert view.set_body(body.ref) is body
    operands = view.operands_for_set(body.ref)
    assert len(operands) == 2 and len(view.set_columns) == 1
    assert [operand.position for operand in operands] == [0, 1]
    for operand in operands:
        (image,) = view.fields_for_set_operand(operand.ref)
        assert image.position == 0
        assert image.evidence is operand.source.source.fields[0]
        assert image.terminal is view.input_terminals(operand.use.ref)[0]
        assert image.binding is operand.use.ports[0]
    column = view.set_columns[0]
    assert column.semantic is body.source.semantic_entry.fields[0]
    assert column.source is body.operation.columns[0]
    assert column.inputs == tuple(image.ref for image in view.set_inputs)
    assert column.value_inputs == (
        column.inputs[:1] if kind == "except" else column.inputs
    )
    assert [port.identity.name for port in plan.exports] == ["id"]
    assert plan.exports[0].identity.owner.identity is roots[2].identity
    assert plan.exports[0].identity is not operands[0].use.ports[0].identity
    (terminal,) = view.terminal_exports(body.definition)
    assert isinstance(terminal, results.ProjectSQLResultPort)
    assert terminal.ref is column.output and terminal.canonical is plan.exports[0]
    assert terminal.ref is not plan.exports[0].ref
    assert not hasattr(column.semantic, "item") and not hasattr(
        column.semantic, "select_fact"
    )
    assert column.semantic.field.result_role.value == "ordinary_row_value"
    demands = view.set_requirements(body.ref)
    assert (
        bool(
            tuple(
                d for d in demands if d.kind is sets.ProjectSQLSetDemandKind.COMPARISON
            )
        )
        is body.requires_equivalence
    )


@pytest.mark.parametrize("kind,quantifier", OPERATIONS)
def test_outer_select_consumes_set_terminal(tmp_path, kind, quantifier):
    _, plan, view = _product(tmp_path, _source(kind, quantifier))
    body = view.set_bodies[0]
    consumer = plan.bindings.definitions[-1]
    use = next(use for use in plan.input_uses if use.consumer is consumer.ref)
    assert tuple(port.ref for port in view.input_terminals(use.ref)) == body.outputs
    assert [block.kind.value for block in view.result_stages(consumer.ref)] == [
        "projection"
    ]
    assert len(view.result_exports) == 2


@pytest.mark.parametrize("kind,quantifier", OPERATIONS)
def test_float_union_all_does_not_invent_equivalence(tmp_path, kind, quantifier):
    source = _source(kind, quantifier, right_type="Float").replace(
        "id: Int not null", "id: Float not null"
    )
    roots = _roots(tmp_path, source)
    if (kind, quantifier) == ("union", "all"):
        assert roots[0].ok
        plan = build_project_sql_plan(*roots)
        assert isinstance(plan, ProjectSQLPlan)
        checked = verify_project_sql_plan(plan, *roots)
        assert checked.verified, checked.issues
        view = inspect_project_sql_plan(checked)
        assert all(
            image.evidence.reason is not None and image.evidence.type_concrete
            for image in view.set_inputs
        )
        assert not any(
            d.kind is sets.ProjectSQLSetDemandKind.COMPARISON
            for d in view.set_requirements(view.set_bodies[0].ref)
        )
    else:
        assert not roots[0].ok and any(
            d.code == "PIE-S2344" for d in roots[0].diagnostics
        )
        assert isinstance(build_project_sql_plan(*roots), ProjectSQLPlanUnavailable)


def test_decimal_parents_cross_set_and_distinct_without_reconstruction(tmp_path):
    from test_phase64_slice10_ir_observation_and_differential import _decimal_source

    _, plan, view = _product(tmp_path, _decimal_source("inherited", tmp_path))
    assert len(view.set_bodies) == 1 and len(plan.distincts) == 2
    evidence = plan.quotient_fields[-1].equivalence
    assert evidence.parents and evidence.parents is evidence.selected.type_sources
    assert evidence.decimal is evidence.parents[0].decimal
    assert all(
        parent is original
        for parent, original in zip(
            evidence.parents, view.set_columns[0].source.inputs, strict=True
        )
    )


@pytest.mark.parametrize("kind,quantifier", OPERATIONS)
def test_multiple_columns_follow_positions_and_first_labels(tmp_path, kind, quantifier):
    source = f"""shape Left:
    id: Int not null
    name: Text nullable
shape Right:
    label: Text not null
    key: Int nullable
source lhs: Left is postgres.table("same_locator")
source rhs: Right is mysql.table("same_locator")
table left_side:
    from lhs
    select:
        first = id
        second = name
table right_side:
    from rhs
    select:
        other = key
        renamed = label
query result:
    {kind} {quantifier}:
        from left_side
        from right_side
"""
    _, plan, view = _product(tmp_path, source)
    assert [port.identity.name for port in plan.exports] == ["first", "second"]
    assert len(view.sources) == 2 and view.sources[0].ref is not view.sources[1].ref
    body = view.set_bodies[0]
    assert len(body.columns) == 2
    for i, column in enumerate(view.set_columns):
        images = [image for image in view.set_inputs if image.position == i]
        assert column.inputs == tuple(image.ref for image in images)
        assert len(column.inputs) == 2
        assert column.semantic.type_sources is column.source.inputs
        assert column.semantic.field.resolved_type is column.source.resolved_type
        assert column.semantic.field.nullability is column.source.nullability
        assert all(
            isinstance(image.terminal, results.ProjectSQLResultPort) for image in images
        )
    assert [field.semantic.field.nullability.value for field in view.set_columns] == {
        "union": ["nullable", "nullable"],
        "intersect": ["non_null", "non_null"],
        "except": ["non_null", "nullable"],
    }[kind]


def test_three_operand_except_and_nested_except_keep_different_graphs(tmp_path):
    prefix = _source(replay=False).split("table combined:")[0]
    flat = (
        prefix
        + "query result:\n    except all:\n        from lhs\n        from rhs\n        from lhs\n"
    )
    nested = (
        prefix
        + "table inner_right:\n    except all:\n        from rhs\n        from lhs\nquery result:\n    except all:\n        from lhs\n        from inner_right\n"
    )
    _, _, flat_view = _product(tmp_path / "flat", flat)
    _, _, nested_view = _product(tmp_path / "nested", nested)
    assert [len(body.operands) for body in flat_view.set_bodies] == [3]
    assert [len(body.operands) for body in nested_view.set_bodies] == [2, 2]
    assert all(
        body.fold == "source_order_left_fold"
        for body in (*flat_view.set_bodies, *nested_view.set_bodies)
    )
    outer = nested_view.set_bodies[-1]
    right = nested_view.operands_for_set(outer.ref)[1]
    assert right.producer is nested_view.set_bodies[0].definition
    assert (
        nested_view.fields_for_set_operand(right.ref)[0].terminal.ref
        is nested_view.set_bodies[0].outputs[0]
    )
    # Retained Phase64 oracle demonstrates the nesting law; no database executes.
    from collections import Counter
    from test_phase64_slice9_set_operations_explicit_all_distinct_output_identity import (
        _bag_apply,
    )

    row = Counter({(1,): 1})
    assert _bag_apply(
        "except", "all", _bag_apply("except", "all", row, row), row
    ) != _bag_apply("except", "all", row, _bag_apply("except", "all", row, row))


@pytest.mark.parametrize(
    "tail", ["row", "group", "global", "window", "hidden_group", "result"]
)
def test_operand_stages_and_output_roles_survive_set(tmp_path, tail):
    prefix = _source(replay=False).split("table combined:")[0]
    bodies = {
        "row": "    let:\n        value = id + 1\n    where value > 0\n    select:\n        output = value\n",
        "group": "    group by:\n        id\n    select:\n        id\n        total = count()\n    satisfying:\n        total > 0\n",
        "hidden_group": "    group by:\n        id\n    select:\n        total = count()\n",
        "global": "    select:\n        total = count()\n",
        "window": "    select:\n        visible = 1\n    qualify:\n        row_number() window:\n            order by:\n                id\n        <= 2\n",
        "result": "    select distinct:\n        id\n    order by:\n        id\n    limit 0\n",
    }
    source = (
        prefix
        + "table operand:\n    from lhs\n"
        + bodies[tail]
        + "query result:\n    union all:\n        from operand\n        from operand\n"
    )
    _, plan, view = _product(tmp_path, source)
    body = view.set_bodies[0]
    pair = view.operands_for_set(body.ref)
    assert (
        len(pair) == 2
        and pair[0].producer is pair[1].producer
        and pair[0].ref is not pair[1].ref
    )
    assert all(
        field.semantic.field.result_role.value == "ordinary_row_value"
        for field in view.set_columns
    )
    assert all(
        isinstance(field.terminal, results.ProjectSQLResultPort)
        and field.terminal.canonical is not None
        for field in view.set_inputs
    )
    if tail == "window":
        assert plan.windows and len(body.outputs) == 1
        assert all(
            isinstance(field.terminal, results.ProjectSQLResultPort)
            and field.terminal.key not in [window.source for window in plan.windows]
            for field in view.set_inputs
        )
    if tail in {"group", "global", "hidden_group"}:
        assert any(
            field.evidence.selected.field.result_role.value == "aggregate_result"
            for field in view.set_inputs
        )
    if tail == "result":
        assert [stage.kind.value for stage in view.result_stages(pair[0].producer)] == [
            "projection",
            "distinct",
            "relation_ordering",
            "limit",
        ]
        assert plan.result_limits[0].value == 0


@pytest.mark.parametrize("consumer", ["row", "join", "group", "window", "distinct"])
def test_named_set_consumers_keep_actual_terminal_and_type_parents(tmp_path, consumer):
    source = _source(replay=False)
    tails = {
        "row": "    let:\n        value = id + 1\n    where value > 0\n    select:\n        value\n",
        "join": "    left join lhs as r:\n        from combined\n        on true\n    select:\n        a = combined.id\n        b = r.id\n",
        "group": "    inner join lhs as r:\n        from combined\n        on true\n    group by:\n        combined.id\n    select:\n        total = count()\n",
        "window": "    select:\n        id\n        w = row_number() window:\n            order by:\n                id\n    qualify:\n        w <= 2\n",
        "distinct": "    select distinct:\n        id\n    order by:\n        id\n    limit 1\n",
    }
    _, plan, view = _product(
        tmp_path, source + "query result:\n    from combined\n" + tails[consumer]
    )
    body = view.set_bodies[0]
    use = next(use for use in view.input_uses if use.producer is body.definition)
    assert tuple(port.ref for port in view.input_terminals(use.ref)) == body.outputs
    assert view.terminal_exports(plan.bindings.definitions[-1].ref)
    if consumer == "group":
        assert plan.aggregations
    if consumer == "window":
        assert plan.windows and plan.filters
    if consumer == "distinct":
        assert plan.distincts and plan.result_limits


def test_pending_hidden_order_inside_operand_stays_pending(tmp_path):
    source = """shape Row:
    id: Int not null
    hidden: Text nullable
    unique by_id on id
source rows: Row is postgres.table("rows")
table operand:
    from rows
    select distinct:
        id
    order by:
        hidden
    limit 1
query result:
    union all:
        from operand
        from operand
"""
    _, plan, view = _product(tmp_path, source)
    (pending,) = view.hidden_order_requirements
    assert pending.proof.status.value == "proven"
    assert plan.order_items[0].value is pending.ref
    assert all(field.terminal.ref is not pending.ref for field in view.set_inputs)
    assert all(
        isinstance(field.terminal, results.ProjectSQLResultPort)
        and field.terminal.canonical is not None
        and field.terminal.canonical.identity.name == "id"
        for field in view.set_inputs
    )
    assert any(
        isinstance(d, results.ProjectSQLResultDemand) and d.witness is pending
        for d in plan.demands
    )


def test_except_right_membership_retains_warning_and_source_demands(tmp_path):
    from test_phase64_slice3_generic_on_condition_semantics_authority_separation import (
        _source as join_source,
    )
    from test_phase65_slice5_seven_join_kinds_match_scopes_obligation_retention import (
        _roots as requested_roots,
        _requests,
    )

    source = join_source("true").replace("query result:", "table right_side:")
    source += "table left_side:\n    from lhs\n    select:\n        id\n    limit 0\nquery result:\n    except distinct:\n        from left_side\n        from right_side\n"
    roots = requested_roots(tmp_path, source, _requests)
    assert roots[0].ok
    plan = build_project_sql_plan(*roots)
    assert isinstance(plan, ProjectSQLPlan)
    view = inspect_project_sql_plan(verify_project_sql_plan(plan, *roots))
    assert len(view.sources) == 2
    (obligation,) = view.single_matches
    assert (
        obligation.downstream_enforcement_required
        and obligation.diagnostic in plan.diagnostics
    )
    assert plan.diagnostics is roots[0].diagnostics
    column = view.set_columns[0]
    assert column.value_inputs == column.inputs[:1] and len(column.inputs) == 2
    right = view.set_inputs[1]
    from pietto._project.project_sql_plan import ProjectSQLOriginProvenance

    origin = next(origin for origin in view.origins if origin.subject is right.ref)
    assert origin.provenance is ProjectSQLOriginProvenance.MEMBERSHIP
    assert all(
        source.ref in [d.subject for d in plan.bindings.demands]
        for source in view.sources
    )


@pytest.mark.parametrize("position", ["operand", "outer"])
def test_operand_limit_and_outer_limit_have_separate_graphs(tmp_path, position):
    source = _source(replay=False).split("table combined:")[0]
    source += "table operand:\n    from lhs\n    select distinct:\n        id\n" + (
        "    limit 1\n" if position == "operand" else ""
    )
    source += (
        "table combined:\n    union all:\n        from operand\n        from operand\nquery result:\n    from combined\n    select distinct:\n        id\n"
        + ("    limit 1\n" if position == "outer" else "")
    )
    _, plan, view = _product(tmp_path, source)
    assert len(plan.distincts) == 2 and len(view.limits) == 1
    limit = view.limits[0]
    boundary = next(
        boundary
        for boundary in view.result_boundaries
        if boundary.ref is limit.boundary
    )
    owner = next(
        d.entry.owner.definition.name
        for d in view.definitions
        if d.ref is boundary.definition
    )
    assert owner == ("operand" if position == "operand" else "result")


@pytest.fixture(scope="module")
def set_plans(tmp_path_factory):
    source = (
        _source(replay=False)
        .replace(
            "    id: Int not null", "    id: Int not null\n    name: Text nullable"
        )
        .replace(
            "    other: Int nullable",
            "    other: Int nullable\n    label: Text not null",
        )
    )
    source = (
        source.split("table combined:")[0]
        + """table limited:
    from lhs
    select distinct:
        id
        name
    order by:
        id
    limit 1
table difference:
    except distinct:
        from limited
        from rhs
        from rhs
query result:
    union all:
        from difference
        from limited
"""
    )
    return tuple(
        _product(tmp_path_factory.mktemp("set-plan"), source) for _ in range(2)
    )


@pytest.mark.parametrize(
    "section",
    [
        "set_bodies",
        "set_operands",
        "set_inputs",
        "set_columns",
        "result_ports",
        "result_exports",
    ],
)
@pytest.mark.parametrize("change", ["empty", "duplicate", "reverse", "foreign"])
def test_complete_set_and_terminal_inventories_are_mandatory(
    set_plans, section, change
):
    roots, plan, _ = set_plans[0]
    foreign = set_plans[1][1]
    values = getattr(plan, section)
    changed = {
        "empty": (),
        "duplicate": (*values, values[0]),
        "reverse": tuple(reversed(values)),
        "foreign": getattr(foreign, section),
    }[change]
    checked = verify_project_sql_plan(_graft(plan, **{section: changed}), *roots)
    assert not checked.verified
    with pytest.raises(ValueError, match="VERIFIED"):
        inspect_project_sql_plan(checked)


@pytest.mark.parametrize(
    "mutation",
    [
        "body_owner",
        "kind",
        "quantifier",
        "law",
        "equivalence_flag",
        "uniqueness_flag",
        "fold",
        "property",
        "row_domain",
        "operand_source",
        "operand_use",
        "producer",
        "bool_operand",
        "input_position",
        "input_terminal",
        "input_type",
        "column_source",
        "column_inputs",
        "right_membership",
        "first_identity",
        "value_sources",
        "missing_origin",
        "missing_demand",
    ],
)
def test_field_level_set_grafts_fail_closed(set_plans, mutation):
    from pietto.ast_nodes import SetOperationKind, SetOperationQuantifier
    from pietto._project.project_set_operations import ProjectSetMultiplicityLaw

    roots, plan, _ = set_plans[0]
    foreign = set_plans[1][1]
    body, operand, image, column = (
        plan.set_bodies[0],
        plan.set_operands[0],
        plan.set_inputs[0],
        plan.set_columns[0],
    )
    section, index, value = {
        "body_owner": (
            "set_bodies",
            0,
            _graft(body, definition=plan.bindings.definitions[0].ref),
        ),
        "kind": ("set_bodies", 0, _graft(body, kind=SetOperationKind.UNION)),
        "quantifier": (
            "set_bodies",
            0,
            _graft(body, quantifier=SetOperationQuantifier.ALL),
        ),
        "law": (
            "set_bodies",
            0,
            _graft(body, multiplicity=ProjectSetMultiplicityLaw.UNION_ALL),
        ),
        "equivalence_flag": ("set_bodies", 0, _graft(body, requires_equivalence=1)),
        "uniqueness_flag": ("set_bodies", 0, _graft(body, full_row_unique=False)),
        "fold": ("set_bodies", 0, _graft(body, fold="right")),
        "property": (
            "set_bodies",
            0,
            _graft(body, properties=foreign.set_bodies[0].properties),
        ),
        "row_domain": (
            "set_bodies",
            0,
            _graft(body, row_domain=foreign.set_bodies[0].row_domain),
        ),
        "operand_source": (
            "set_operands",
            0,
            _graft(operand, source=plan.set_operands[1].source),
        ),
        "operand_use": (
            "set_operands",
            0,
            _graft(operand, use=plan.set_operands[1].use),
        ),
        "producer": (
            "set_operands",
            0,
            _graft(operand, producer=plan.set_operands[1].producer),
        ),
        "bool_operand": ("set_operands", 0, _graft(operand, position=False)),
        "input_position": ("set_inputs", 0, _graft(image, position=False)),
        "input_terminal": (
            "set_inputs",
            0,
            _graft(image, terminal=plan.result_ports[0]),
        ),
        "input_type": (
            "set_inputs",
            0,
            _graft(image, evidence=foreign.set_inputs[0].evidence),
        ),
        "column_source": (
            "set_columns",
            0,
            _graft(column, source=plan.set_columns[1].source),
        ),
        "column_inputs": (
            "set_columns",
            0,
            _graft(column, inputs=tuple(reversed(column.inputs))),
        ),
        "right_membership": (
            "set_columns",
            0,
            _graft(column, inputs=column.inputs[:1]),
        ),
        "first_identity": (
            "result_exports",
            2,
            _graft(plan.result_exports[2], canonical=plan.set_operands[0].use.ports[0]),
        ),
        "value_sources": ("set_columns", 0, _graft(column, value_inputs=column.inputs)),
        "missing_origin": (
            "origins",
            len(plan.origins) - 1,
            _graft(plan.origins[-1], antecedents=()),
        ),
        "missing_demand": (
            "demands",
            len(plan.demands) - 1,
            _graft(plan.demands[-1], witness=foreign.set_columns[-1]),
        ),
    }[mutation]
    values = list(getattr(plan, section))
    values[index] = value
    candidate = _graft(plan, **{section: tuple(values)})
    assert not verify_project_sql_plan(candidate, *roots).verified
    stale = _graft(verify_project_sql_plan(plan, *roots), plan=candidate)
    with pytest.raises(ValueError, match="VERIFIED"):
        inspect_project_sql_plan(stale)


def test_missing_all_set_demands_and_foreign_lookup_are_rejected(set_plans):
    roots, plan, view = set_plans[0]
    other = set_plans[1][1]
    candidate = _graft(
        plan,
        demands=tuple(
            d for d in plan.demands if not isinstance(d, sets.ProjectSQLSetDemand)
        ),
    )
    assert not verify_project_sql_plan(candidate, *roots).verified
    with pytest.raises(ValueError, match="belong"):
        view.set_body(other.set_bodies[0].ref)
    with pytest.raises(ValueError, match="belong"):
        view.fields_for_set_operand(other.set_operands[0].ref)


def test_no_downstream_semantic_set_type_or_plan_construction(set_plans, monkeypatch):
    from pietto._project import project_set_operations as semantic_sets
    from pietto._project import project_final_outputs as final
    from pietto._project import project_row_equivalence as equality
    from pietto._project import project_ir_relational_properties as properties
    from pietto._project import project_sql_plan as planner
    from pietto._project import project_query_block_ir as ir
    from pietto.semantic import expressions

    roots, original, _ = set_plans[0]

    def forbidden(*args, **kwargs):
        raise AssertionError("downstream construction is forbidden")

    for cls in (
        semantic_sets.ProjectSetInputScope,
        semantic_sets.ProjectSetOperandUse,
        semantic_sets.ProjectSetColumn,
        semantic_sets.ProjectSetOperation,
        final.ProjectCompletedSetOutput,
        final.ProjectCompletedSetOutputField,
        equality.ProjectRowEquivalenceField,
        equality.ProjectRowEquivalenceInput,
    ):
        monkeypatch.setattr(cls, "__post_init__", forbidden)
    monkeypatch.setattr(final.ProjectEffectiveJoinInputAuthority, "validate", forbidden)
    monkeypatch.setattr(
        final.ProjectEffectiveJoinInputAuthority, "field_parts", forbidden
    )
    for module, name in [
        (final, "build_project_effective_output_completion"),
        (ir, "build_project_query_block_ir"),
        (expressions, "infer_row_expression"),
        (properties, "strictly_determines_output"),
    ]:
        monkeypatch.setattr(module, name, forbidden)
    built = build_project_sql_plan(*roots)
    assert isinstance(built, ProjectSQLPlan)
    for module, name in [
        (planner, "build_project_sql_plan"),
        (planner, "build_project_sql_bindings"),
        (sets, "build_body"),
        (results, "build"),
    ]:
        monkeypatch.setattr(module, name, forbidden)
    for cls in (
        sets.ProjectSQLSetBody,
        sets.ProjectSQLSetOperand,
        sets.ProjectSQLSetInput,
        sets.ProjectSQLSetColumn,
        results.ProjectSQLResultPort,
        results.ProjectSQLResultExport,
    ):
        monkeypatch.setattr(cls, "__init__", forbidden)
    for plan in (original, built):
        checked = verify_project_sql_plan(plan, *roots)
        assert checked.verified, checked.issues
        assert inspect_project_sql_plan(checked).set_bodies


def test_imported_reexported_set_self_use_keeps_distinct_occurrences(tmp_path):
    (tmp_path / "a.pietto").write_text(
        _source(replay=False) + "export:\n    table combined\n"
    )
    (tmp_path / "facade.pietto").write_text(
        'import "a.pietto":\n    table combined as Public\nexport:\n    table Public\n'
    )
    source = 'import "facade.pietto":\n    table Public as Alias\nquery result:\n    except distinct:\n        from Alias\n        from Alias\n'
    _, plan, view = _product(tmp_path, source)
    assert len(view.set_bodies) == 2
    outer = view.set_bodies[-1]
    first, second = view.operands_for_set(outer.ref)
    assert first.ref is not second.ref and first.use.ref is not second.use.ref
    assert first.producer is second.producer is view.set_bodies[0].definition
    assert (
        first.use.binding.imported_binding is not None
        and len(first.use.origin_path.hops) == 2
    )
    assert (
        first.use.origin_path.target_occurrence.identity
        is view.set_bodies[0].operation.owner.identity
    )
    assert all(source.module.path == "a.pietto" for source in view.sources)
    assert plan.exports[0].identity.owner.identity is plan.scope.selected_owner.identity


def test_decimal_set_join_distinct_and_nested_set_keep_all_parents(tmp_path):
    source = _source(right_type="Decimal(10, 2)", replay=False).replace(
        "id: Int not null", "id: Decimal(10, 2) nullable"
    )
    source += "table joined:\n    from combined\n    inner join combined as r:\n        from combined\n        on true\n    select distinct:\n        price = combined.id\nquery result:\n    union distinct:\n        from joined\n        from joined\n"
    _, plan, view = _product(tmp_path, source)
    assert len(view.set_bodies) == 2 and len(plan.distincts) == 1 and plan.joins
    evidence = plan.quotient_fields[0].equivalence
    assert evidence.parents and evidence.decimal is not None
    assert (evidence.decimal.precision, evidence.decimal.scale) == (10, 2)
    assert all(parent.decimal is not None for parent in evidence.parents)
    assert all(image.evidence.parents for image in view.set_inputs[-2:])


@pytest.mark.parametrize("grouped", [False, True])
def test_direct_set_aggregation_keeps_upstream_rejection_and_authored_bridge(
    grouped, tmp_path
):
    body = (
        "    group by:\n        id\n" if grouped else ""
    ) + "    select:\n        total = count()\n"
    source = _source(replay=False) + "query result:\n    from combined\n" + body
    roots = _roots(tmp_path / "direct", source)
    assert not roots[0].ok and any(d.code == "PIE-S2333" for d in roots[0].diagnostics)
    assert isinstance(build_project_sql_plan(*roots), ProjectSQLPlanUnavailable)
    source = source.replace(
        "query result:\n    from combined\n",
        "table bridge:\n    from combined\n    select:\n        id\nquery result:\n    from bridge\n",
    )
    _, plan, view = _product(tmp_path / "bridge", source)
    assert plan.aggregations and view.set_bodies


@pytest.mark.parametrize(
    "scenario,code",
    [
        ("quantifier", "PIE-S2341"),
        ("arity", "PIE-S2341"),
        ("width", "PIE-S2342"),
        ("type", "PIE-S2343"),
        ("first_missing", "PIE-S2301"),
        ("later_missing", "PIE-S2301"),
    ],
)
def test_real_invalid_set_inputs_never_publish_partial_bodies(tmp_path, scenario, code):
    source = _source(replay=False)
    if scenario == "quantifier":
        source = _source(quantifier="", replay=False)
    elif scenario == "arity":
        source = _source(operands=("lhs",), replay=False)
    elif scenario == "width":
        source = source.replace(
            "other: Int nullable", "other: Int nullable\n    extra: Int nullable"
        )
    elif scenario == "type":
        source = _source(right_type="Float", replay=False)
    elif scenario == "first_missing":
        source = _source(operands=("missing", "rhs"), replay=False)
    else:
        source = _source(operands=("lhs", "missing"), replay=False)
    roots = _roots(tmp_path, source.replace("table combined:", "query result:"))
    assert not roots[0].ok and any(d.code == code for d in roots[0].diagnostics)
    value = build_project_sql_plan(*roots)
    assert isinstance(value, ProjectSQLPlanUnavailable) and value.plan is None


def test_cycle_and_unrelated_error_still_block_healthy_set_selection(tmp_path):
    source = (
        _source(replay=False).replace("table combined:", "query result:")
        + """table a:
    union all:
        from b
        from lhs
table b:
    from a
    select:
        id
"""
    )
    roots = _roots(tmp_path, source)
    assert not roots[0].ok and any(d.code == "PIE-S2302" for d in roots[0].diagnostics)
    selected = next(entry for entry in roots[1].root.entries if entry.owner is roots[2])
    assert isinstance(selected, ProjectIRCompletedSetOperationOutput)
    value = build_project_sql_plan(*roots)
    assert isinstance(value, ProjectSQLPlanUnavailable)
    assert [b.kind.value for b in value.blockers] == ["semantic_result_unsuccessful"]


@pytest.mark.parametrize(
    "coordinate", ["operand", "slot", "dependency", "column", "output", "type_input"]
)
def test_original_set_ordinals_are_strict_integers(set_plans, monkeypatch, coordinate):
    roots, plan, _ = set_plans[0]
    operand = plan.set_operands[0]
    target, member = {
        "operand": (operand.source.source.resolution.reference, "operand_ordinal"),
        "slot": (operand.source.use.slot, "input_ordinal"),
        "dependency": (operand.source.source.dependency, "dependency_ordinal"),
        "column": (plan.set_columns[0].source, "position"),
        "output": (plan.set_columns[0].semantic, "output_position"),
        "type_input": (plan.set_inputs[0].evidence.selected, "field_position"),
    }[coordinate]
    with monkeypatch.context() as patch:
        patch.setattr(type(target), "__setattr__", object.__setattr__)
        assert getattr(target, member) == 0
        patch.setattr(target, member, False)
        assert not verify_project_sql_plan(plan, *roots).verified


def test_original_type_parent_null_and_scope_grafts_are_invalid(set_plans, monkeypatch):
    from pietto._project.model import ProjectRowFieldNullability

    roots, plan, _ = set_plans[0]
    other = set_plans[1][1]
    evidence = plan.set_inputs[0].evidence
    column = plan.set_columns[0].source
    scope = plan.set_bodies[0].operation.scope
    for target, member, changed in [
        (evidence, "parents", (other.set_inputs[0].evidence,)),
        (column, "nullability", ProjectRowFieldNullability.NULLABLE),
        (scope, "available", tuple(reversed(scope.available))),
    ]:
        with monkeypatch.context() as patch:
            patch.setattr(type(target), "__setattr__", object.__setattr__)
            patch.setattr(target, member, changed)
            assert not verify_project_sql_plan(plan, *roots).verified


@pytest.mark.parametrize("domain", ["alias", "enum", "bytes", "json", "any"])
def test_set_type_identity_uses_original_domain_evidence(tmp_path, domain):
    prefix = {
        "alias": "type Base = Int\ntype Alias = Base\n",
        "enum": "enum Status:\n    active\n",
    }.get(domain, "")
    spelling = {
        "alias": "Alias",
        "enum": "Status",
        "bytes": "Bytes",
        "json": "Json",
        "any": "Any",
    }[domain]
    quantifier = "distinct" if domain in {"alias", "enum"} else "all"
    source = prefix + _source(
        "union", quantifier, right_type=spelling, replay=False
    ).replace("id: Int not null", f"id: {spelling} not null").replace(
        "table combined:", "query result:"
    )
    _, plan, view = _product(tmp_path, source)
    evidence = view.set_inputs[0].evidence
    assert evidence.resolution is not None
    if domain == "alias":
        assert [item.declared_name for item in evidence.resolution.alias_chain] == [
            "Alias",
            "Base",
        ]
    if domain == "enum":
        assert evidence.selected.field.resolved_type.kind.value == "enum"
    if domain in {"bytes", "json", "any"}:
        assert evidence.type_concrete and evidence.reason is not None
        assert not plan.set_bodies[0].requires_equivalence


def test_equal_spelling_nominal_types_do_not_create_a_set_type(tmp_path):
    for module in ("a", "b"):
        (tmp_path / f"{module}.pietto").write_text(
            f'enum Status:\n    active\nshape Row:\n    id: Status nullable\nsource rows: Row is postgres.table("{module}")\nexport:\n    source rows\n'
        )
    source = 'import "a.pietto":\n    source rows as Left\nimport "b.pietto":\n    source rows as Right\nquery result:\n    union all:\n        from Left\n        from Right\n'
    roots = _roots(tmp_path, source)
    assert not roots[0].ok and any(d.code == "PIE-S2343" for d in roots[0].diagnostics)
    assert isinstance(build_project_sql_plan(*roots), ProjectSQLPlanUnavailable)


def test_zero_first_operand_keeps_its_label_and_all_membership(tmp_path):
    source = _source(replay=False).split("table combined:")[0]
    source += "table empty:\n    from lhs\n    select:\n        first_label = id\n    limit 0\nquery result:\n    union all:\n        from empty\n        from rhs\n"
    _, plan, view = _product(tmp_path, source)
    assert [port.identity.name for port in plan.exports] == ["first_label"]
    assert (
        len(view.set_operands) == 2
        and len(view.sources) == 2
        and view.limits[0].value == 0
    )
    image = view.set_inputs[0]
    assert isinstance(image.terminal, results.ProjectSQLResultPort)
    boundary = next(
        boundary
        for boundary in view.result_boundaries
        if boundary.ref is image.terminal.boundary
    )
    assert boundary.kind.value == "limit"
