"""Normal-source result boundaries and independent supplied-evidence corruption."""

from dataclasses import replace
from pathlib import Path

import pytest

from pietto._project import project_sql_plan_results as result
from pietto.ast_nodes import TableDef, QueryDef
from pietto._project.project_final_outputs import ProjectNonConcreteRelationOrdering
from pietto._project.project_sql_plan import (
    ProjectSQLPlan,
    ProjectSQLPlanUnavailable,
    build_project_sql_plan,
)
from pietto._project.project_sql_plan_verification import verify_project_sql_plan
from pietto._project.project_sql_plan_inspection import inspect_project_sql_plan
from test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan import (
    _roots,
    _graft,
)
from test_phase64_slice3_generic_on_condition_semantics_authority_separation import (
    _source as _join_source,
)


def _source(
    body: str = "    select distinct:\n        value\n",
    *,
    type_name="Int",
    kind="query",
    family="postgres",
) -> str:
    return (
        f"""shape Row:
    value: {type_name} nullable
    hidden: Float nullable
source rows: Row is {family}.table("rows")
{kind} result:
    from rows
"""
        + body
    )


def _product(path: Path, source: str):
    roots = _roots(path, source)
    assert roots[0].ok, roots[0].diagnostics
    plan = build_project_sql_plan(*roots)
    assert isinstance(plan, ProjectSQLPlan), getattr(plan, "blockers", ())
    verification = verify_project_sql_plan(plan, *roots)
    assert verification.verified, verification.issues
    return roots, plan, inspect_project_sql_plan(verification)


@pytest.mark.parametrize("family,kind", [("postgres", "query"), ("mysql", "table")])
@pytest.mark.parametrize(
    "type_name", ["Bool", "Int", "Text", "Date", "Timestamp", "UUID", "Decimal(12, 2)"]
)
def test_visible_equivalence_and_original_type_sources(
    tmp_path, family, kind, type_name
):
    roots, plan, view = _product(
        tmp_path, _source(type_name=type_name, family=family, kind=kind)
    )
    (distinct,) = view.distincts
    (field,) = view.quotient_fields
    semantic = roots[1].root.entries[-1].semantic_entry
    assert isinstance(semantic, result.ProjectCompletedEffectiveOutput)
    source = semantic.row_domain.distinct
    assert source is not None
    assert distinct.source is source
    assert distinct.uniqueness is source.uniqueness and distinct.uniqueness.nulls_equal
    assert field.equivalence is source.equivalence.evidence[0]
    assert field.canonical is plan.exports[0]
    assert [
        stage.kind.value
        for stage in view.result_stages(plan.bindings.definitions[-1].ref)
    ] == ["projection", "distinct"]
    assert len(view.result_ports) == 3
    assert len({field.input, field.output, field.canonical.ref}) == 3
    assert all(port.canonical is plan.exports[0] for port in view.result_ports)
    assert view.result_exports[0].port is field.output
    assert view.result_requirements(plan.bindings.definitions[-1].ref)
    if type_name.startswith("Decimal"):
        assert field.equivalence.decimal is not None
        assert (
            field.equivalence.decimal.precision,
            field.equivalence.decimal.scale,
        ) == (12, 2)


@pytest.mark.parametrize(
    "body",
    [
        "    select:\n        value\n    order by:\n        hidden\n        hidden desc\n    limit 1\n",
        "    let:\n        v = value + 1\n    select:\n        value\n    order by:\n        v\n",
        "    group by:\n        value\n    select:\n        total = count()\n    order by:\n        total\n",
        "    select:\n        w = row_number() window:\n            order by:\n                value\n    order by:\n        w\n",
        "    select distinct:\n        value\n    order by:\n        value + value\n        value desc\n    limit 0\n",
        "    select distinct:\n        constant = 1\n    qualify:\n        row_number() window:\n            order by:\n                hidden\n        <= 2\n",
        "    group by:\n        value\n    select distinct:\n        total = count()\n",
    ],
)
def test_real_result_stage_compositions(tmp_path, body):
    _, plan, view = _product(tmp_path, _source(body))
    assert view.result_boundaries
    assert all(port.identity.name != "hidden" for port in plan.exports)
    if plan.orders:
        order = plan.orders[0]
        for item in plan.order_items:
            assert view.order_uses_for(item.ref)
            assert (
                item.source.item.direction is None
                or item.source.direction.value == item.source.item.direction
            )
            assert item.determination is None or len(item.determination) == 3
        assert order.source.inputs is not None


def test_strict_fd_remains_a_pending_scoped_requirement(tmp_path):
    source = _source(
        "    select distinct:\n        value\n    order by:\n        hidden\n    limit 1\n"
    ).replace(
        "value: Int nullable", "value: Int not null\n    unique by_value on value"
    )
    _, plan, view = _product(tmp_path, source)
    (pending,) = view.hidden_order_requirements
    (item,) = view.order_items
    assert item.value is pending.ref and item.expression is not pending.ref
    assert item.determination is not None and pending.proof is item.determination[1]
    assert pending.value_type is item.source.value_type
    assert pending.determinants and pending.requested and pending.input_images
    assert all(
        use.ports == () and use.requirement is pending.ref
        for use in view.order_uses_for(item.ref)
    )
    with pytest.raises(ValueError, match="scope"):
        view.result_port(pending.scope, pending.ref)
    assert view.hidden_order_requirement(pending.ref) is pending
    assert [port.identity.name for port in plan.exports] == ["value"]


@pytest.mark.parametrize(
    "kind", ["inner", "left", "cross", "right", "full", "semi", "anti"]
)
def test_seven_joins_keep_visible_only_quotient(tmp_path, kind):
    source = (
        _join_source(None if kind == "cross" else "true", kind=kind).replace(
            "select:", "select distinct:"
        )
        + "    limit 0\n"
    )
    _, plan, view = _product(tmp_path, source)
    assert plan.joins and len(view.quotient_fields) == len(plan.exports) == 1


@pytest.mark.parametrize("limit", [None, 0, 1, result.MAX_RELATION_LIMIT])
def test_static_limit_absence_and_bound(tmp_path, limit):
    source = _source("    select:\n        value\n") + (
        "" if limit is None else f"    limit {limit}\n"
    )
    _, plan, view = _product(tmp_path, source)
    assert len(view.limits) == (0 if limit is None else 1)
    if limit is not None:
        assert view.limits[0].value == view.limits[0].row_count_upper_bound == limit
        definition = plan.bindings.definitions[-1].entry.owner.definition
        assert (
            isinstance(definition, (TableDef, QueryDef))
            and definition.limit_clause is not None
        )
        assert view.limits[0].literal is definition.limit_clause.expression


@pytest.mark.parametrize(
    "literal", ["true", "1.5", "-1", "1 + 1", str(result.MAX_RELATION_LIMIT + 1)]
)
def test_invalid_limits_keep_actual_upstream_diagnostics(tmp_path, literal):
    # This normal joined path reaches the existing completed LIMIT diagnostic.
    roots = _roots(tmp_path, _join_source("true") + f"    limit {literal}\n")
    assert not roots[0].ok and any(d.code == "PIE-S2307" for d in roots[0].diagnostics)
    assert isinstance(build_project_sql_plan(*roots), ProjectSQLPlanUnavailable)


@pytest.mark.parametrize("type_name", ["Float", "Any", "Bytes", "Json", "Decimal"])
def test_distinct_domain_negatives_and_nonvisible_float(tmp_path, type_name):
    roots = _roots(tmp_path, _source(type_name=type_name))
    assert not roots[0].ok
    assert [d.code for d in roots[0].diagnostics] == ["PIE-S2339"]
    assert isinstance(build_project_sql_plan(*roots), ProjectSQLPlanUnavailable)
    _, _, view = _product(
        tmp_path / "control",
        _source(
            "    select:\n        value\n    order by:\n        hidden\n    limit 0\n",
            type_name="Float",
        ),
    )
    assert view.orders and not view.distincts


@pytest.mark.parametrize("type_name", ["Float", "Decimal(18, 4)"])
def test_alias_resolution_and_decimal_parent_identity(tmp_path, type_name):
    source = f"type Base = {type_name}\ntype Alias = Base\n" + _source(
        type_name="Alias"
    )
    if type_name == "Float":
        roots = _roots(tmp_path, source)
        assert not roots[0].ok and [d.code for d in roots[0].diagnostics] == [
            "PIE-S2339"
        ]
    else:
        source = (
            source.replace("query result:", "table typed:")
            + "query result:\n    from typed\n    select distinct:\n        value\n"
        )
        _, plan, view = _product(tmp_path, source)
        assert len(view.distincts) == 2
        original, child = view.quotient_fields
        assert original.equivalence.resolution is not None
        assert [
            alias.declared_name for alias in original.equivalence.resolution.alias_chain
        ] == ["Alias", "Base"]
        assert child.equivalence.parents is child.equivalence.selected.type_sources
        assert (
            child.equivalence.decimal_type_expr
            is original.equivalence.decimal_type_expr
        )
        assert child.equivalence.decimal is not None
        assert (
            child.equivalence.decimal.precision == 18
            and child.equivalence.decimal.scale == 4
        )
        assert view.distincts[0].source is not view.distincts[1].source
        assert len(plan.result_exports) == 2


@pytest.mark.parametrize(
    "projection",
    [
        "        value\n",
        "        constant = 1\n",
        "        value\n        w = row_number() window:\n            order by:\n                value\n",
    ],
)
def test_hidden_and_selected_window_quotient_roles(tmp_path, projection):
    source = _source(
        "    select distinct:\n"
        + projection
        + "    qualify:\n        row_number() window:\n            order by:\n                hidden\n        <= 2\n"
    )
    _, plan, view = _product(tmp_path, source)
    assert plan.windows and any(window.selected is None for window in plan.windows)
    assert [field.canonical.identity.name for field in view.quotient_fields] == [
        port.identity.name for port in plan.exports
    ]
    assert len(view.quotient_fields) == (2 if "w =" in projection else 1)
    assert all(port.canonical is not None for port in view.result_ports)
    assert all(
        port.key not in [window.source for window in plan.windows]
        for port in view.result_ports
    )


@pytest.mark.parametrize("order", ["hidden", "value"])
def test_failed_determination_and_no_inverse_projection(tmp_path, order):
    source = _source(
        f"    select distinct:\n        computed = value + 1\n    order by:\n        {order}\n"
    )
    roots = _roots(tmp_path, source)
    assert not roots[0].ok and [d.code for d in roots[0].diagnostics] == ["PIE-S2340"]
    assert isinstance(build_project_sql_plan(*roots), ProjectSQLPlanUnavailable)
    nullable = _source(
        "    select distinct:\n        value\n    order by:\n        hidden\n"
    ).replace("    hidden:", "    unique maybe on value\n    hidden:")
    roots = _roots(tmp_path / "nullable", nullable)
    assert not roots[0].ok and [d.code for d in roots[0].diagnostics] == ["PIE-S2340"]


def test_ordinary_order_never_captures_backward_select_alias(tmp_path):
    roots = _roots(
        tmp_path,
        _source(
            "    select:\n        renamed = value\n    order by:\n        renamed\n"
        ),
    )
    # Historical completion has no scalar ORDER admission. Its new preparation
    # retains the failed outcome, which cannot be used as positive plan evidence.
    assert roots[0].ok
    result_plan = build_project_sql_plan(*roots)
    assert isinstance(result_plan, ProjectSQLPlanUnavailable)
    assert [b.kind.value for b in result_plan.blockers] == ["order"]
    preparation = roots[0].roots.order_facts[-1].ordering
    assert isinstance(preparation, ProjectNonConcreteRelationOrdering)
    assert preparation.reason.value == "expression_non_concrete"


def test_limit_barrier_and_named_order_scope(tmp_path):
    head = _source(
        "    select:\n        value\n    order by:\n        value\n    limit 1\n",
        kind="table",
    ).replace("table result:", "table bounded:")
    consumer = "query result:\n    from bounded\n    where value > 0\n    select:\n        value\n"
    _, first, view = _product(tmp_path / "after", head + consumer)
    assert [
        [stage.kind.value for stage in view.result_stages(d.ref)]
        for d in view.definitions[1:]
    ] == [["projection", "relation_ordering", "limit"], ["where", "projection"]]
    assert first.bindings.definitions[-1].entry.active_properties.ordering is None
    source = head.replace(
        "    select:", "    where value > 0\n    select:"
    ) + consumer.replace("    where value > 0\n", "")
    _, second, before = _product(tmp_path / "before", source)
    assert [
        [stage.kind.value for stage in before.result_stages(d.ref)]
        for d in before.definitions[1:]
    ] == [["where", "projection", "relation_ordering", "limit"], ["projection"]]
    assert len(first.input_uses) == len(second.input_uses) == 2


def test_global_distinct_keeps_special_origin_and_no_order_broadening(tmp_path):
    _, plan, view = _product(
        tmp_path,
        _source("    select distinct:\n        total = count()\n    limit 0\n"),
    )
    (distinct,) = view.distincts
    assert distinct.global_input and distinct.origin.factor is None
    assert distinct.source.input_domain.kind.value == "global"
    assert plan.aggregations[0].empty_input.value == "one_global_row"
    roots = _roots(
        tmp_path / "order",
        _source(
            "    select distinct:\n        total = count()\n    order by:\n        total\n"
        ),
    )
    assert not roots[0].ok and isinstance(
        build_project_sql_plan(*roots), ProjectSQLPlanUnavailable
    )


@pytest.mark.parametrize("distinct", [False, True])
def test_pending_single_match_and_errors_survive_limit_zero(tmp_path, distinct):
    from test_phase65_slice5_seven_join_kinds_match_scopes_obligation_retention import (
        _roots as request_roots,
        _requests,
    )

    source = _join_source("true") + "    limit 0\n"
    if distinct:
        source = source.replace("select:", "select distinct:")
    roots = request_roots(tmp_path, source, _requests)
    assert roots[0].ok
    plan = build_project_sql_plan(*roots)
    assert isinstance(plan, ProjectSQLPlan)
    view = inspect_project_sql_plan(verify_project_sql_plan(plan, *roots))
    assert (
        view.single_matches and view.single_matches[0].downstream_enforcement_required
    )
    assert view.single_matches[0].diagnostic in plan.diagnostics
    assert view.limits[0].value == 0
    bad = source + "query broken:\n    from lhs\n    select:\n        missing\n"
    bad_roots = request_roots(tmp_path / "bad", bad, _requests)
    assert not bad_roots[0].ok
    unavailable = build_project_sql_plan(*bad_roots)
    assert isinstance(unavailable, ProjectSQLPlanUnavailable)
    assert unavailable.diagnostics is bad_roots[0].diagnostics


@pytest.fixture(scope="module")
def rich_plans(tmp_path_factory):
    source = _source("""    select distinct:
        value
        w = row_number() window:
            order by:
                value
    qualify:
        row_number() window:
            order by:
                value
        <= 2
    order by:
        value + value
        hidden desc
        value asc
    limit 1
""").replace("value: Int nullable", "value: Int not null\n    unique by_value on value")
    return tuple(
        _product(tmp_path_factory.mktemp("result-scope"), source) for _ in range(2)
    )


@pytest.mark.parametrize(
    "section",
    [
        "result_boundaries",
        "result_ports",
        "distincts",
        "quotient_fields",
        "orders",
        "order_items",
        "order_expressions",
        "order_uses",
        "hidden_order_requirements",
        "result_limits",
        "result_exports",
    ],
)
@pytest.mark.parametrize("change", ["empty", "duplicate", "foreign", "reverse"])
def test_complete_result_inventories_cannot_verify_vacuously(
    rich_plans, section, change
):
    roots, plan, _ = rich_plans[0]
    foreign = rich_plans[1][1]
    values = getattr(plan, section)
    changed = {
        "empty": (),
        "duplicate": (*values, values[0]),
        "foreign": getattr(foreign, section),
        "reverse": tuple(reversed(values)) if len(values) > 1 else (*values, values[0]),
    }[change]
    checked = verify_project_sql_plan(_graft(plan, **{section: changed}), *roots)
    assert not checked.verified
    with pytest.raises(ValueError, match="VERIFIED"):
        inspect_project_sql_plan(checked)


@pytest.mark.parametrize(
    "mutation",
    [
        "hidden_quotient",
        "equivalence",
        "canonical",
        "removed_proof",
        "foreign_proof",
        "order_scope",
        "pending_as_value",
        "pending_as_port",
        "limit_value",
        "limit_bound",
        "bool_bound",
        "bool_ordinal",
        "wrong_predecessor",
        "wrong_operator",
        "input_graft",
        "result_export",
        "origin",
        "demand",
    ],
)
def test_result_field_grafts_fail_closed(rich_plans, mutation):
    roots, plan, _ = rich_plans[0]
    other = rich_plans[1][1]
    field, pending, item, limit = (
        plan.quotient_fields[0],
        plan.hidden_order_requirements[0],
        plan.order_items[1],
        plan.result_limits[0],
    )
    section, position, value = {
        "hidden_quotient": (
            "quotient_fields",
            0,
            _graft(field, input=plan.stage_ports[1].ref),
        ),
        "equivalence": (
            "quotient_fields",
            0,
            _graft(field, equivalence=other.quotient_fields[0].equivalence),
        ),
        "canonical": ("quotient_fields", 0, _graft(field, canonical=plan.exports[1])),
        "removed_proof": ("order_items", 1, _graft(item, determination=None)),
        "foreign_proof": (
            "order_items",
            1,
            _graft(item, determination=other.order_items[1].determination),
        ),
        "order_scope": (
            "order_uses",
            0,
            _graft(plan.order_uses[0], scope=plan.blocks[0].ref),
        ),
        "pending_as_value": ("order_items", 1, _graft(item, value=item.expression)),
        "pending_as_port": (
            "order_uses",
            2,
            _graft(
                plan.order_uses[2], ports=(plan.result_ports[0].ref,), requirement=None
            ),
        ),
        "limit_value": ("result_limits", 0, _graft(limit, value=2)),
        "limit_bound": ("result_limits", 0, _graft(limit, row_count_upper_bound=2)),
        "bool_bound": ("result_limits", 0, _graft(limit, row_count_upper_bound=True)),
        "bool_ordinal": ("order_items", 1, _graft(item, position=True)),
        "wrong_predecessor": (
            "result_boundaries",
            2,
            _graft(
                plan.result_boundaries[2], predecessor=plan.result_boundaries[0].ref
            ),
        ),
        "wrong_operator": (
            "result_boundaries",
            0,
            _graft(
                plan.result_boundaries[0], operator=plan.result_boundaries[1].operator
            ),
        ),
        "input_graft": (
            "hidden_order_requirements",
            0,
            _graft(
                pending, input_images=other.hidden_order_requirements[0].input_images
            ),
        ),
        "result_export": (
            "result_exports",
            0,
            _graft(plan.result_exports[0], port=plan.result_ports[0].ref),
        ),
        "origin": (
            "origins",
            len(plan.origins) - 1,
            _graft(plan.origins[-1], antecedents=()),
        ),
        "demand": (
            "demands",
            len(plan.demands) - 1,
            _graft(plan.demands[-1], witness=other.result_exports[-1]),
        ),
    }[mutation]
    values = list(getattr(plan, section))
    values[position] = value
    candidate = _graft(plan, **{section: tuple(values)})
    assert not verify_project_sql_plan(candidate, *roots).verified
    checked = verify_project_sql_plan(plan, *roots)
    with pytest.raises(ValueError, match="VERIFIED"):
        inspect_project_sql_plan(_graft(checked, plan=candidate))


def test_original_proof_premise_and_type_parent_are_checked(rich_plans, monkeypatch):
    from pietto._project.project_row_keys import ProjectRowUniquenessStrength

    roots, plan, _ = rich_plans[0]
    pending = plan.hidden_order_requirements[0]
    assert pending.proof.closure.witness
    fact = pending.proof.closure.witness[0].fact
    with monkeypatch.context() as patch:
        patch.setattr(type(fact), "__setattr__", object.__setattr__)
        patch.setattr(fact, "strength", ProjectRowUniquenessStrength.LAX)
        assert not verify_project_sql_plan(plan, *roots).verified
    evidence = plan.quotient_fields[0].equivalence
    with monkeypatch.context() as patch:
        patch.setattr(type(evidence), "__setattr__", object.__setattr__)
        patch.setattr(
            evidence, "parents", (rich_plans[1][1].quotient_fields[0].equivalence,)
        )
        assert not verify_project_sql_plan(plan, *roots).verified
    assert verify_project_sql_plan(plan, *roots).verified


def test_missing_preparation_and_derived_copy_are_not_authority(
    rich_plans, monkeypatch
):
    roots, plan, _ = rich_plans[0]
    order = plan.orders[0].source
    derived = replace(order)
    assert derived.inputs is None and order.inputs is not None
    with monkeypatch.context() as patch:
        patch.setattr(type(order), "__setattr__", object.__setattr__)
        patch.setattr(order, "inputs", None)
        assert not verify_project_sql_plan(plan, *roots).verified
        assert isinstance(build_project_sql_plan(*roots), ProjectSQLPlanUnavailable)


def test_no_downstream_resolution_equivalence_or_fd_reconstruction(
    rich_plans, monkeypatch
):
    from pietto._project import project_final_outputs as final
    from pietto._project import project_completed_semantics as completed
    from pietto._project import project_ir_relational_properties as fd
    from pietto._project import module_semantic_fact_preservation as references
    from pietto._project import row_expression_type_facts as types
    from pietto._project import project_row_equivalence as equivalence
    from pietto._project import project_sql_plan as planner
    from pietto.semantic import expressions

    roots, original, _ = rich_plans[0]

    def forbidden(*args, **kwargs):
        raise AssertionError("downstream reconstruction is forbidden")

    for module, names in [
        (
            final,
            [
                "_distinct_ordering",
                "_validate_distinct_order_proofs",
                "_prepare_relation_order_inputs",
                "_no_join_relation_ordering",
                "_analyze_no_join_scalar",
                "strictly_determines_output",
                "infer_row_expression",
            ],
        ),
        (completed, ["_completed_order_facts", "_completed_row_references"]),
        (
            references,
            [
                "_expression_reference_facts",
                "_order_expression_reference_facts",
                "_expression_reference_candidates",
            ],
        ),
        (types, ["build_project_row_expression_value_types"]),
        (fd, ["strictly_determines_output", "strict_output_fd_closure"]),
        (expressions, ["infer_row_expression"]),
    ]:
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    monkeypatch.setattr(equivalence.ProjectRowEquivalence, "__post_init__", forbidden)
    monkeypatch.setattr(
        equivalence.ProjectRowEquivalenceField, "__post_init__", forbidden
    )
    rebuilt = build_project_sql_plan(*roots)
    assert isinstance(rebuilt, ProjectSQLPlan)
    monkeypatch.setattr(result, "build", forbidden)
    monkeypatch.setattr(planner, "build_project_sql_plan", forbidden)
    monkeypatch.setattr(planner, "build_project_sql_bindings", forbidden)
    for plan in (original, rebuilt):
        checked = verify_project_sql_plan(plan, *roots)
        assert checked.verified, checked.issues
        assert inspect_project_sql_plan(checked).hidden_order_requirements


@pytest.mark.parametrize("joined", [False, True])
@pytest.mark.parametrize("distinct", [False, True])
@pytest.mark.parametrize("window", [False, True])
def test_group_and_window_order_use_their_retained_target_carriers(
    tmp_path, joined, distinct, window
):
    if joined:
        source = _join_source("true")
        if window:
            source = source.replace(
                "        id = lhs.id\n",
                "        w = row_number() window:\n            order by:\n                lhs.id\n",
            )
            order = "w"
        else:
            source = source.replace(
                "    select:", "    group by:\n        lhs.id\n    select:"
            ).replace("        id = lhs.id\n", "        total = count()\n")
            order = "total"
    else:
        body = (
            "    select:\n        w = row_number() window:\n            order by:\n                value\n"
            if window
            else "    group by:\n        value\n    select:\n        total = count()\n"
        )
        source, order = _source(body), "w" if window else "total"
    if distinct:
        source = source.replace("    select:", "    select distinct:")
    _, plan, view = _product(
        tmp_path, source + f"    order by:\n        {order}\n        {order} desc\n"
    )
    assert len(view.order_items) == len(view.order_uses) == 2
    assert all(
        not isinstance(item.source.source, result.ProjectNoJoinScalarExpression)
        for item in view.order_items
    )
    assert bool(plan.distincts) is distinct
    assert not view.hidden_order_requirements


def test_rebound_order_and_limit_use_original_to_active_input_correspondence(tmp_path):
    from test_phase65_slice7_windows_named_window_qualify_staging import SOURCES
    from pietto._project.project_query_block_ir import ProjectIRReboundExistingOutput

    source = SOURCES["selected_and_hidden"].replace("query result:", "table upstream:")
    source += "query result:\n    from upstream\n    select:\n        id\n    order by:\n        id\n    limit 1\n"
    roots, plan, view = _product(tmp_path, source)
    entry = plan.bindings.definitions[-1].entry
    assert isinstance(entry, ProjectIRReboundExistingOutput)
    assert roots[0].roots.order_facts[-1].entry is entry.semantic_entry
    assert len(view.order_uses) == 1 and view.order_uses[0].ports
    incoming = next(
        use
        for use in plan.input_uses
        if use.consumer is plan.bindings.definitions[-1].ref
    )
    assert incoming.edge is entry.relation_input
    assert all(
        port.producer_port is export.ref
        for port, export in zip(
            incoming.ports, plan.bindings.definitions[-2].exports, strict=True
        )
    )


def test_imported_reexported_repeated_limited_distinct_definition(tmp_path):
    producer = _source(
        "    select distinct:\n        value\n    order by:\n        value\n    limit 1\n",
        kind="table",
    ).replace("table result:", "table capped:")
    (tmp_path / "producer.pietto").write_text(producer + "export:\n    table capped\n")
    (tmp_path / "facade.pietto").write_text(
        'import "producer.pietto":\n    table capped as public\nexport:\n    table public\n'
    )
    source = """import "facade.pietto":
    table public as chosen
query result:
    from chosen
    cross join chosen as again:
        from chosen
    select distinct:
        first = chosen.value
        second = again.value
    order by:
        chosen.value
    limit 0
"""
    _, plan, view = _product(tmp_path, source)
    assert len(view.distincts) == len(view.limits) == 2
    producer_definition = next(
        d for d in view.definitions if d.entry.owner.definition.name == "capped"
    )
    uses = tuple(
        use for use in plan.input_uses if use.producer is producer_definition.ref
    )
    assert len(uses) == 2 and uses[0].ref is not uses[1].ref
    assert all(len(use.origin_path.hops) == 2 for use in uses)
    assert all(
        use.origin_path.target_occurrence.identity
        is producer_definition.entry.owner.identity
        for use in uses
    )
    assert plan.sources[0].module.path == "producer.pietto"
    assert (
        len(
            tuple(
                boundary
                for boundary in view.result_boundaries
                if boundary.definition is producer_definition.ref
            )
        )
        == 3
    )


def test_set_parent_decimal_evidence_reaches_complete_plan(
    tmp_path,
):
    from test_phase64_slice10_ir_observation_and_differential import _decimal_source

    roots = _roots(tmp_path, _decimal_source("inherited", tmp_path))
    assert roots[0].ok
    semantic = roots[1].root.entries[-1].semantic_entry
    assert isinstance(semantic, result.ProjectCompletedEffectiveOutput)
    distinct = semantic.row_domain.distinct
    assert distinct is not None
    (evidence,) = distinct.equivalence.evidence
    assert evidence.parents is evidence.selected.type_sources and evidence.parents
    assert evidence.decimal is evidence.parents[0].decimal
    plan = build_project_sql_plan(*roots)
    assert isinstance(plan, ProjectSQLPlan)
    view = inspect_project_sql_plan(verify_project_sql_plan(plan, *roots))
    assert view.set_bodies and view.quotient_fields[-1].equivalence is evidence
    assert all(
        parent is original
        for parent, original in zip(
            evidence.parents, view.set_columns[0].source.inputs, strict=True
        )
    )


def test_ordinary_order_preparation_keeps_multiplicity_and_original_types(
    tmp_path, monkeypatch
):
    from pietto._project import project_final_outputs as final

    observed = []
    original = final._order_expression_reference_facts

    def collect(**kwargs):
        references = original(**kwargs)
        observed.append((kwargs["item"].expression, references))
        return references

    monkeypatch.setattr(final, "_order_expression_reference_facts", collect)
    roots, plan, _ = _product(
        tmp_path,
        _source(
            "    select:\n        value\n    order by:\n        value + value\n        hidden\n"
        ),
    )
    order = plan.orders[0].source
    assert len(observed) == len(order.items) == 2
    assert order.inputs is not None and [len(uses) for uses in order.inputs] == [2, 1]
    for item, uses, (expression, references) in zip(
        order.items, order.inputs, observed, strict=True
    ):
        assert item.expression is expression
        assert isinstance(item.source, result.ProjectNoJoinScalarExpression)
        assert item.value_type is item.source.value_types[item.expression]
        assert all(
            use.resolution is reference
            and use.value_type is item.source.value_types[use.expression]
            for use, reference in zip(uses, references, strict=True)
        )
    assert roots[0].roots.order_facts[-1].ordering is order


def test_empty_order_occurrence_ledgers_block_construction(rich_plans, monkeypatch):
    roots, plan, _ = rich_plans[0]
    order = plan.orders[0].source
    with monkeypatch.context() as patch:
        patch.setattr(type(order), "__setattr__", object.__setattr__)
        patch.setattr(order, "inputs", tuple(() for _ in order.items))
        assert isinstance(build_project_sql_plan(*roots), ProjectSQLPlanUnavailable)
        assert not verify_project_sql_plan(plan, *roots).verified


def test_lax_fd_cannot_be_laundered_into_the_original_strict_derivation(
    tmp_path, monkeypatch
):
    from pietto._project.project_row_keys import ProjectRowUniquenessStrength

    source = (
        _source(
            "    select distinct:\n        value\n        lax\n    order by:\n        hidden\n"
        )
        .replace(
            "value: Int nullable", "value: Int not null\n    unique by_value on value"
        )
        .replace(
            "    hidden:",
            "    lax: Int nullable\n    unique by_lax on lax\n    hidden:",
        )
    )
    roots, plan, _ = _product(tmp_path, source)
    pending = plan.hidden_order_requirements[0]
    index = pending.proof.seed.index
    assert index.lax_rules and pending.proof.closure.witness
    lax = index.lax_rules[0].fact
    step = pending.proof.closure.witness[0]
    with monkeypatch.context() as patch:
        patch.setattr(type(lax), "__setattr__", object.__setattr__)
        patch.setattr(type(step), "__setattr__", object.__setattr__)
        patch.setattr(lax, "strength", ProjectRowUniquenessStrength.STRICT)
        patch.setattr(step, "fact", lax)
        assert not verify_project_sql_plan(plan, *roots).verified


def test_joined_order_cannot_capture_a_foreign_equal_position(tmp_path, monkeypatch):
    source = _join_source("true") + "    order by:\n        lhs.id\n"
    roots, plan, _ = _product(tmp_path / "own", source)
    _, other, _ = _product(tmp_path / "other", source)
    use, foreign = plan.order_uses[0].source, other.order_uses[0].source
    resolution = use.resolution
    with monkeypatch.context() as patch:
        patch.setattr(type(resolution), "__setattr__", object.__setattr__)
        patch.setattr(type(use), "__setattr__", object.__setattr__)
        patch.setattr(resolution, "target", foreign.target)
        patch.setattr(use, "target", foreign.target)
        patch.setattr(use, "determination_target", foreign.determination_target)
        assert not verify_project_sql_plan(plan, *roots).verified


@pytest.mark.parametrize("hidden", [False, True])
def test_repeated_visible_images_and_order_items_keep_all_occurrences(tmp_path, hidden):
    key = "hidden" if hidden else "value"
    source = _source(
        f"    select distinct:\n        first = value\n        second = value\n    order by:\n        {key}\n        {key} desc\n"
    ).replace(
        "value: Int nullable", "value: Int not null\n    unique by_value on value"
    )
    _, plan, view = _product(tmp_path, source)
    assert (
        len(view.quotient_fields) == len(view.order_items) == len(view.order_uses) == 2
    )
    assert view.order_uses[0].ref is not view.order_uses[1].ref
    if hidden:
        assert len(view.hidden_order_requirements) == 2
        assert all(
            len(requirement.determinants) == 1
            and len(requirement.determinants[0][1]) == 2
            for requirement in view.hidden_order_requirements
        )
    else:
        assert all(len(use.ports) == 2 for use in view.order_uses)
    assert plan.exports[0].identity is not plan.exports[1].identity


def test_finite_float_literal_and_computed_decimal_keep_upstream_outcomes(tmp_path):
    for name, source in [
        ("float", _source("    select distinct:\n        finite = 1.5\n")),
        (
            "decimal",
            _source(
                "    select distinct:\n        changed = value + value\n",
                type_name="Decimal(10, 2)",
            ),
        ),
    ]:
        roots = _roots(tmp_path / name, source)
        assert not roots[0].ok and [d.code for d in roots[0].diagnostics] == [
            "PIE-S2339"
        ]
        assert isinstance(build_project_sql_plan(*roots), ProjectSQLPlanUnavailable)


@pytest.mark.parametrize(
    "coordinate",
    [
        "scalar_target",
        "canonical_identity",
        "active_field",
        "selected_field",
        "fd_field",
        "fd_index",
    ],
)
def test_bool_never_replaces_an_original_result_coordinate(
    tmp_path, coordinate, monkeypatch
):
    if coordinate == "scalar_target":
        source = (
            _join_source("true").replace(
                "        id = lhs.id\n", "        constant = 1\n"
            )
            + "    order by:\n        lhs.id\n"
        )
    else:
        source = _source(
            "    select distinct:\n        value\n    order by:\n        hidden\n"
        ).replace(
            "value: Int nullable", "value: Int not null\n    unique by_value on value"
        )
    roots, plan, _ = _product(tmp_path, source)
    if coordinate == "scalar_target":
        target, attribute = plan.order_uses[0].source.target, "position"
    elif coordinate == "canonical_identity":
        target, attribute = plan.exports[0].identity, "field_position"
    elif coordinate == "active_field":
        target, attribute = plan.exports[0].field, "field_position"
    elif coordinate == "selected_field":
        target, attribute = (
            plan.distincts[0].source.fields[0],
            "selected_output_ordinal",
        )
    elif coordinate == "fd_field":
        target, attribute = (
            plan.hidden_order_requirements[0].properties.fields[0],
            "field_position",
        )
    else:
        target, attribute = (
            plan.hidden_order_requirements[0].proof.seed.index,
            "positions",
        )
    with monkeypatch.context() as patch:
        patch.setattr(type(target), "__setattr__", object.__setattr__)
        if coordinate == "fd_index":
            index = plan.hidden_order_requirements[0].proof.seed.index
            altered = dict(index.positions)
            altered[index.universe[0]] = False
        else:
            assert getattr(target, attribute) == 0
            altered = False
        patch.setattr(target, attribute, altered)
        assert not verify_project_sql_plan(plan, *roots).verified
